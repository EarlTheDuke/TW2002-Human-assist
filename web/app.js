/* TW2K-AI spectator UI.
 *
 * Connects to /ws, consumes {type:"init"|"snapshot"|"event"} messages,
 * and renders the galaxy, player cards, event feed, and transmissions.
 */

(function () {
  "use strict";

  // ----------------- Global state -----------------
  const state = {
    sectors: new Map(),        // id -> {id, warps, warps_dir, x, y, port, has_planets, is_fedspace}
    bounds: null,              // {minX, minY, maxX, maxY}
    players: new Map(),        // id -> player object
    planets: new Map(),        // id -> planet object (when known)
    alliances: [],             // alliance objects
    events: [],                // retained recent event objects
    messages: [],              // hails / broadcasts
    combatFlashes: [],         // [{sector_id, t, kind}]
    hailBubbles: [],           // [{actor, sector_id, text, t}]
    day: 0,
    tick: 0,
    maxDays: 30,
    status: "connecting",
    speed: 1,
    finished: false,
    winner_id: null,
    win_reason: "",
    selectedSectorId: null,
    selectedPlayerId: null,
    recentWarp: [],            // [{from,to,t}]
    filters: {
      combat: true, trade: true, move: true, thought: true, system: true, diplomacy: true,
    },
    replay: {
      mode: "live",            // "live" | "scrub"
      cursorIndex: -1,         // event index when scrubbing (-1 = live)
    },
  };

  const MAX_EVENTS = 600;
  const MAX_MESSAGES = 200;
  const MAX_RECENT_WARPS = 30;
  const RECENT_WARP_MS = 3500;
  const COMBAT_FLASH_MS = 2200;
  const HAIL_BUBBLE_MS = 4500;

  // ----------------- DOM refs ------------------
  const svg = document.getElementById("galaxy");
  const sectorTip = document.getElementById("sectorTip");
  const playersPanel = document.getElementById("panelPlayers") || document.getElementById("playersPanel");
  const messageFeed = document.getElementById("messageFeed");
  const eventFeed = document.getElementById("eventFeed");
  const statusDot = document.getElementById("statusDot");
  const statusLabel = document.getElementById("statusLabel");
  const dayLabel = document.getElementById("dayLabel");
  const tickLabel = document.getElementById("tickLabel");
  const pauseBtn = document.getElementById("pauseBtn");
  const restartBtn = document.getElementById("restartBtn");
  const gameOverModal = document.getElementById("gameOverModal");
  const gameOverSummary = document.getElementById("gameOverSummary");
  const modalClose = document.getElementById("modalClose");

  // ----------------- WebSocket ---------------------

  let ws;
  function connect() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${proto}//${location.host}/ws`);
    ws.onopen = () => {
      setStatus("connected", "online");
    };
    ws.onclose = () => {
      setStatus("disconnected", "offline");
      setTimeout(connect, 1500);
    };
    ws.onerror = () => {};
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        handleMessage(msg);
      } catch (e) {
        console.warn("Bad WS payload", ev.data);
      }
    };
  }

  function setStatus(dotClass, label) {
    statusDot.className = "status-dot " + dotClass;
    statusLabel.textContent = label;
  }

  // ----------------- Message handler ---------------

  function handleMessage(msg) {
    switch (msg.type) {
      case "init":
        onInit(msg);
        break;
      case "snapshot":
        onSnapshot(msg.snapshot);
        break;
      case "event":
        onEvent(msg);
        break;
      case "error":
        pushEvent({
          kind: "system_error",
          summary: msg.message,
          day: state.day,
          tick: state.tick,
        });
        break;
      default:
        break;
    }
    render();
  }

  function onInit(msg) {
    state.sectors.clear();
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const s of msg.sectors) {
      state.sectors.set(s.id, s);
      if (s.x < minX) minX = s.x;
      if (s.y < minY) minY = s.y;
      if (s.x > maxX) maxX = s.x;
      if (s.y > maxY) maxY = s.y;
    }
    state.bounds = { minX, minY, maxX, maxY };
    state.maxDays = msg.max_days || state.maxDays;
    state.players.clear();
    for (const p of msg.players) state.players.set(p.id, p);
    state.events = [];
    state.messages = [];
    state.recentWarp = [];
    state.day = 0;
    state.tick = 0;
    state.finished = false;
    state.winner_id = null;
    state.win_reason = null;
    if (gameOverModal) gameOverModal.hidden = true;
    renderEvents();
    renderMessages();
    buildMap();
  }

  function onSnapshot(snap) {
    if (!snap) return;
    if (snap.day) state.day = snap.day;
    if (snap.tick) state.tick = snap.tick;
    if (snap.status) state.status = snap.status;
    if (snap.speed) state.speed = snap.speed;
    if (snap.finished) state.finished = true;
    if (snap.winner_id) state.winner_id = snap.winner_id;
    if (snap.win_reason) state.win_reason = snap.win_reason;
    if (Array.isArray(snap.players)) {
      for (const p of snap.players) {
        const cur = state.players.get(p.id) || {};
        state.players.set(p.id, Object.assign({}, cur, p));
      }
    }
    if (Array.isArray(snap.planets)) {
      state.planets.clear();
      for (const pl of snap.planets) state.planets.set(pl.id, pl);
    }
    if (Array.isArray(snap.alliances)) {
      state.alliances = snap.alliances;
    }
  }

  function onEvent(msg) {
    const ev = msg.event;
    const patch = msg.state_patch || {};

    if (patch.player) {
      const existing = state.players.get(patch.player.id) || {};
      state.players.set(patch.player.id, Object.assign({}, existing, patch.player));
    }
    if (patch.day) state.day = patch.day;
    if (patch.finished) {
      state.finished = true;
      state.winner_id = patch.winner_id;
      state.win_reason = patch.win_reason;
    }
    if (ev.tick) state.tick = ev.tick;
    if (ev.day) state.day = ev.day;

    // Track warps for animation
    if (ev.kind === "warp" && ev.payload && ev.payload.from && ev.payload.to) {
      state.recentWarp.push({ from: ev.payload.from, to: ev.payload.to, t: Date.now(), actor: ev.actor_id });
      if (state.recentWarp.length > MAX_RECENT_WARPS) state.recentWarp.shift();
    }
    // Combat flash triggers
    if (ev.kind === "combat" || ev.kind === "ship_destroyed" || ev.kind === "mine_detonated"
        || ev.kind === "atomic_detonation" || ev.kind === "photon_hit" || ev.kind === "photon_fired"
        || ev.kind === "fed_response" || ev.kind === "port_destroyed") {
      const sec = (ev.payload && (ev.payload.sector || ev.payload.sector_id)) || sectorFromActor(ev.actor_id);
      if (sec) {
        state.combatFlashes.push({ sector_id: sec, t: Date.now(), kind: ev.kind });
        if (state.combatFlashes.length > 40) state.combatFlashes.shift();
      }
    }
    // Messages + hail bubbles
    if (ev.kind === "hail" || ev.kind === "broadcast") {
      state.messages.push({
        from: ev.actor_id,
        target: ev.payload && ev.payload.target,
        kind: ev.kind,
        message: ev.payload && ev.payload.message,
        day: ev.day,
        tick: ev.tick,
      });
      if (state.messages.length > MAX_MESSAGES) state.messages.shift();
      const sec = sectorFromActor(ev.actor_id);
      if (sec) {
        state.hailBubbles.push({
          actor: ev.actor_id,
          sector_id: sec,
          text: (ev.payload && ev.payload.message) || "",
          t: Date.now(),
        });
        if (state.hailBubbles.length > 12) state.hailBubbles.shift();
      }
    }

    pushEvent(ev);
    if (ev.kind === "game_over") {
      showGameOver(ev);
    }
  }

  function sectorFromActor(actorId) {
    if (!actorId) return null;
    const p = state.players.get(actorId);
    return p ? p.sector_id : null;
  }

  function pushEvent(ev) {
    state.events.push(ev);
    if (state.events.length > MAX_EVENTS) state.events.shift();
  }

  // ----------------- Galaxy map --------------------
  //
  // We use a single SVG with pan/zoom. Build once on init; update dynamic layers each render.

  const svgNS = "http://www.w3.org/2000/svg";
  let viewBoxState = { x: -600, y: -600, w: 1200, h: 1200 };

  function buildMap() {
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    if (state.sectors.size === 0) return;
    const b = state.bounds;
    const pad = 30;
    viewBoxState = {
      x: b.minX - pad,
      y: b.minY - pad,
      w: (b.maxX - b.minX) + 2 * pad,
      h: (b.maxY - b.minY) + 2 * pad,
    };
    updateViewBox();

    // Defs with arrowhead markers for warp arrows
    const defs = document.createElementNS(svgNS, "defs");
    defs.innerHTML = `
      <marker id="warp-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#3a4c82" opacity="0.55"/>
      </marker>
      <marker id="warp-arrow-oneway" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#e8b85a" opacity="0.85"/>
      </marker>
    `;
    svg.appendChild(defs);

    // Layer groups
    const warpsLayer = document.createElementNS(svgNS, "g");
    warpsLayer.setAttribute("id", "warps-layer");
    const sectorsLayer = document.createElementNS(svgNS, "g");
    sectorsLayer.setAttribute("id", "sectors-layer");
    const shipsLayer = document.createElementNS(svgNS, "g");
    shipsLayer.setAttribute("id", "ships-layer");
    const recentLayer = document.createElementNS(svgNS, "g");
    recentLayer.setAttribute("id", "recent-layer");
    const fxLayer = document.createElementNS(svgNS, "g");
    fxLayer.setAttribute("id", "fx-layer");
    svg.appendChild(warpsLayer);
    svg.appendChild(recentLayer);
    svg.appendChild(sectorsLayer);
    svg.appendChild(fxLayer);
    svg.appendChild(shipsLayer);

    // Build warps. Show one-way warps (asymmetric) with directional arrows,
    // two-way warps as simple lines.
    const drawn = new Set();
    for (const s of state.sectors.values()) {
      for (const w of s.warps) {
        const other = state.sectors.get(w);
        if (!other) continue;
        const reverse = other.warps && other.warps.includes(s.id);
        const key = reverse ? [Math.min(s.id, w), Math.max(s.id, w)].join("-") : `${s.id}->${w}`;
        if (drawn.has(key)) continue;
        drawn.add(key);
        const line = document.createElementNS(svgNS, "line");
        // Shorten slightly so arrow isn't buried
        const dx = other.x - s.x, dy = other.y - s.y;
        const len = Math.sqrt(dx * dx + dy * dy) || 1;
        const shrink = 3.5;
        line.setAttribute("x1", s.x + (dx / len) * shrink);
        line.setAttribute("y1", s.y + (dy / len) * shrink);
        line.setAttribute("x2", other.x - (dx / len) * shrink);
        line.setAttribute("y2", other.y - (dy / len) * shrink);
        if (reverse) {
          line.setAttribute("class", "warp");
        } else {
          line.setAttribute("class", "warp oneway");
          line.setAttribute("marker-end", "url(#warp-arrow-oneway)");
        }
        warpsLayer.appendChild(line);
      }
    }

    // Sectors
    for (const s of state.sectors.values()) {
      const g = document.createElementNS(svgNS, "g");
      g.setAttribute("data-id", s.id);
      const c = document.createElementNS(svgNS, "circle");
      c.setAttribute("cx", s.x);
      c.setAttribute("cy", s.y);
      c.setAttribute("r", s.id === 1 ? 4 : (s.port ? 2.5 : 1.5));
      let cls = "sector-node";
      if (s.id === 1) cls += " stardock";
      else if (s.is_fedspace) cls += " fed";
      else if (s.port) cls += " port";
      if (s.has_planets) cls += " has-planet";
      c.setAttribute("class", cls);
      g.appendChild(c);

      g.addEventListener("mouseenter", (e) => showSectorTip(s, e));
      g.addEventListener("mouseleave", hideSectorTip);
      g.addEventListener("click", () => {
        state.selectedSectorId = s.id;
        render();
      });
      sectorsLayer.appendChild(g);
    }

    enablePanZoom();
  }

  function updateViewBox() {
    svg.setAttribute("viewBox", `${viewBoxState.x} ${viewBoxState.y} ${viewBoxState.w} ${viewBoxState.h}`);
  }

  function enablePanZoom() {
    let dragging = false;
    let lastX = 0, lastY = 0;
    svg.addEventListener("mousedown", (e) => {
      dragging = true;
      lastX = e.clientX;
      lastY = e.clientY;
    });
    window.addEventListener("mouseup", () => { dragging = false; });
    window.addEventListener("mousemove", (e) => {
      if (!dragging) return;
      const rect = svg.getBoundingClientRect();
      const scale = viewBoxState.w / rect.width;
      viewBoxState.x -= (e.clientX - lastX) * scale;
      viewBoxState.y -= (e.clientY - lastY) * scale;
      lastX = e.clientX;
      lastY = e.clientY;
      updateViewBox();
    });
    svg.addEventListener("wheel", (e) => {
      e.preventDefault();
      const rect = svg.getBoundingClientRect();
      const mx = viewBoxState.x + ((e.clientX - rect.left) / rect.width) * viewBoxState.w;
      const my = viewBoxState.y + ((e.clientY - rect.top) / rect.height) * viewBoxState.h;
      const factor = e.deltaY > 0 ? 1.2 : 0.82;
      viewBoxState.w *= factor;
      viewBoxState.h *= factor;
      viewBoxState.x = mx - ((e.clientX - rect.left) / rect.width) * viewBoxState.w;
      viewBoxState.y = my - ((e.clientY - rect.top) / rect.height) * viewBoxState.h;
      updateViewBox();
    }, { passive: false });
  }

  function showSectorTip(s, e) {
    const parts = [`<strong>Sector ${s.id}</strong>`];
    if (s.id === 1) parts.push("StarDock · Federation HQ");
    else if (s.is_fedspace) parts.push("FedSpace (protected)");
    if (s.port && s.port !== "STARDOCK") parts.push(`Port <strong>${s.port}</strong>${s.port_name ? " · " + s.port_name : ""}`);
    if (s.has_planets) {
      const planetsHere = Array.from(state.planets.values()).filter((pl) => pl.sector_id === s.id);
      if (planetsHere.length) {
        for (const pl of planetsHere) {
          const owner = pl.owner_id ? state.players.get(pl.owner_id) : null;
          const ownerLabel = owner ? ` · ${owner.name}` : (pl.owner_id ? ` · p${pl.owner_id}` : "");
          const citLevel = pl.citadel_level || 0;
          const citPart = citLevel > 0
            ? ` · Citadel L${citLevel}`
            : (pl.citadel_target ? ` · Citadel L${pl.citadel_target} (building D${pl.citadel_complete_day})` : "");
          parts.push(`Planet ${esc(pl.name || pl.id)} [${pl.class || pl.planet_class || "?"}]${ownerLabel}${citPart}`);
        }
      } else {
        parts.push("Has planets");
      }
    }
    // Directional warp hints
    if (s.warps_dir && Array.isArray(s.warps_dir)) {
      const bits = s.warps_dir.map((w) => w.two_way ? `${w.to}↔` : `${w.to}↛`);
      parts.push(`Warps → ${bits.join(", ")}`);
    } else {
      parts.push(`Warps → ${s.warps.join(", ")}`);
    }
    const occ = [];
    for (const p of state.players.values()) {
      if (p.sector_id === s.id) {
        const rk = p.rank ? ` [${p.rank}]` : "";
        occ.push(p.name + rk);
      }
    }
    if (occ.length) parts.push(`Here: ${occ.join(", ")}`);
    sectorTip.innerHTML = parts.join("<br/>");
    sectorTip.hidden = false;
    const rect = svg.getBoundingClientRect();
    const tipX = Math.min(e.clientX - rect.left + 12, rect.width - 260);
    const tipY = Math.min(e.clientY - rect.top + 12, rect.height - 120);
    sectorTip.style.left = tipX + "px";
    sectorTip.style.top = tipY + "px";
  }
  function hideSectorTip() { sectorTip.hidden = true; }

  function renderDynamicMap() {
    if (state.sectors.size === 0) return;
    const shipsLayer = document.getElementById("ships-layer");
    const recentLayer = document.getElementById("recent-layer");
    const fxLayer = document.getElementById("fx-layer");
    if (!shipsLayer || !recentLayer) return;
    while (shipsLayer.firstChild) shipsLayer.removeChild(shipsLayer.firstChild);
    while (recentLayer.firstChild) recentLayer.removeChild(recentLayer.firstChild);
    if (fxLayer) while (fxLayer.firstChild) fxLayer.removeChild(fxLayer.firstChild);

    // Recent warp trails (directional)
    const now = Date.now();
    state.recentWarp = state.recentWarp.filter((w) => now - w.t < RECENT_WARP_MS);
    for (const w of state.recentWarp) {
      const from = state.sectors.get(w.from);
      const to = state.sectors.get(w.to);
      if (!from || !to) continue;
      const age = (now - w.t) / RECENT_WARP_MS;
      const opacity = Math.max(0.15, 1 - age);
      const line = document.createElementNS(svgNS, "line");
      const dx = to.x - from.x, dy = to.y - from.y;
      const len = Math.sqrt(dx * dx + dy * dy) || 1;
      const shrink = 4;
      line.setAttribute("x1", from.x + (dx / len) * shrink);
      line.setAttribute("y1", from.y + (dy / len) * shrink);
      line.setAttribute("x2", to.x - (dx / len) * shrink);
      line.setAttribute("y2", to.y - (dy / len) * shrink);
      const actor = state.players.get(w.actor);
      const color = actor ? actor.color : "#6ee7ff";
      line.setAttribute("stroke", color);
      line.setAttribute("stroke-width", "1.8");
      line.setAttribute("stroke-linecap", "round");
      line.setAttribute("opacity", opacity.toFixed(2));
      line.setAttribute("marker-end", "url(#warp-arrow-oneway)");
      recentLayer.appendChild(line);
    }

    // Combat flashes
    state.combatFlashes = state.combatFlashes.filter((f) => now - f.t < COMBAT_FLASH_MS);
    if (fxLayer) {
      for (const f of state.combatFlashes) {
        const sec = state.sectors.get(f.sector_id);
        if (!sec) continue;
        const age = (now - f.t) / COMBAT_FLASH_MS;
        const radius = 5 + 14 * age;
        const opacity = Math.max(0, 1 - age);
        const ring = document.createElementNS(svgNS, "circle");
        ring.setAttribute("cx", sec.x);
        ring.setAttribute("cy", sec.y);
        ring.setAttribute("r", radius.toFixed(1));
        ring.setAttribute("fill", "none");
        const color = f.kind === "atomic_detonation" || f.kind === "port_destroyed"
          ? "#ff5c7a"
          : (f.kind === "photon_fired" || f.kind === "photon_hit" ? "#f0c04a" : "#ff7a8c");
        ring.setAttribute("stroke", color);
        ring.setAttribute("stroke-width", "1.3");
        ring.setAttribute("opacity", opacity.toFixed(2));
        ring.setAttribute("class", "combat-flash");
        fxLayer.appendChild(ring);
      }

      // Hail bubbles
      state.hailBubbles = state.hailBubbles.filter((b) => now - b.t < HAIL_BUBBLE_MS);
      const bubbleCounts = new Map();
      for (const b of state.hailBubbles) {
        const sec = state.sectors.get(b.sector_id);
        if (!sec) continue;
        const age = (now - b.t) / HAIL_BUBBLE_MS;
        const opacity = Math.max(0, 1 - age);
        const stack = bubbleCounts.get(b.sector_id) || 0;
        bubbleCounts.set(b.sector_id, stack + 1);
        const yoff = -10 - stack * 7;
        const actor = state.players.get(b.actor);
        const color = actor ? actor.color : "#7ee7ff";
        const text = (b.text || "").slice(0, 40);
        const g = document.createElementNS(svgNS, "g");
        g.setAttribute("class", "hail-bubble");
        g.setAttribute("opacity", opacity.toFixed(2));
        const width = Math.min(140, Math.max(28, text.length * 2.1));
        const rect = document.createElementNS(svgNS, "rect");
        rect.setAttribute("x", sec.x - width / 2);
        rect.setAttribute("y", sec.y + yoff - 5);
        rect.setAttribute("width", width);
        rect.setAttribute("height", 7);
        rect.setAttribute("rx", 2);
        rect.setAttribute("fill", "#0c1426");
        rect.setAttribute("stroke", color);
        rect.setAttribute("stroke-width", "0.3");
        g.appendChild(rect);
        const tx = document.createElementNS(svgNS, "text");
        tx.setAttribute("x", sec.x);
        tx.setAttribute("y", sec.y + yoff);
        tx.setAttribute("text-anchor", "middle");
        tx.setAttribute("fill", color);
        tx.setAttribute("font-size", "3");
        tx.setAttribute("font-family", "Inter,system-ui,sans-serif");
        tx.textContent = text;
        g.appendChild(tx);
        fxLayer.appendChild(g);
      }
    }

    // Occupancy highlights + ship markers
    for (const p of state.players.values()) {
      if (!p.alive) continue;
      const s = state.sectors.get(p.sector_id);
      if (!s) continue;
      const dot = document.createElementNS(svgNS, "circle");
      dot.setAttribute("cx", s.x);
      dot.setAttribute("cy", s.y);
      dot.setAttribute("r", 3.5);
      dot.setAttribute("class", "ship-marker");
      dot.setAttribute("fill", p.color || "#6ee7ff");
      dot.setAttribute("stroke", "#0a0f1c");
      dot.setAttribute("stroke-width", "0.5");
      const title = document.createElementNS(svgNS, "title");
      const rk = p.rank ? ` [${p.rank}]` : "";
      title.textContent = `${p.name}${rk} (${p.ship}) @ sector ${p.sector_id}`;
      dot.appendChild(title);
      shipsLayer.appendChild(dot);

      const ring = document.createElementNS(svgNS, "circle");
      ring.setAttribute("cx", s.x);
      ring.setAttribute("cy", s.y);
      ring.setAttribute("r", 6);
      ring.setAttribute("fill", "none");
      ring.setAttribute("stroke", p.color || "#6ee7ff");
      ring.setAttribute("stroke-width", "0.4");
      ring.setAttribute("opacity", "0.5");
      shipsLayer.appendChild(ring);
    }
  }

  // ----------------- Players ------------------------

  function renderPlayers() {
    const container = playersPanel;
    if (!container) return;
    let header = container.querySelector(".panel-header");
    if (!header) {
      header = document.createElement("div");
      header.className = "panel-header";
      header.innerHTML = `
        <h2>Commanders <span class='muted' id='playerCountLabel'></span></h2>
        <div class="header-right">
          <button class="collapse-btn" data-collapse="players" title="Collapse commanders">▾</button>
        </div>
      `;
      container.appendChild(header);
    }
    const countLabel = container.querySelector("#playerCountLabel");
    const alive = Array.from(state.players.values()).filter((p) => p.alive);
    if (countLabel) countLabel.textContent = `${alive.length}/${state.players.size}`;

    let body = container.querySelector(".panel-body");
    if (!body) {
      body = document.createElement("div");
      body.className = "panel-body";
      container.appendChild(body);
    }
    let grid = body.querySelector(".players-grid");
    if (!grid) {
      grid = document.createElement("div");
      grid.className = "players-grid";
      body.appendChild(grid);
    }

    // Re-render simple; 2-4 players is cheap
    grid.innerHTML = "";
    for (const p of state.players.values()) {
      const card = document.createElement("div");
      card.className = "player-card" + (p.alive ? "" : " dead")
        + (state.selectedPlayerId === p.id ? " selected" : "");
      card.dataset.pid = p.id;
      card.style.setProperty("--player-color", p.color || "#6ee7ff");
      const netWorth = fmt(p.net_worth || p.credits || 0);
      const cargoSegs = cargoBar(p);
      const cargoLabel = cargoBreakdown(p);
      const turnsLabel = (p.turns_today != null && p.turns_per_day)
        ? `${p.turns_today}/${p.turns_per_day}`
        : "—";
      const alignLabel = p.alignment_label || "neutral";
      const rankLabel = p.rank || "Civilian";
      const alignValue = (p.alignment != null) ? `${p.alignment} <span class="muted">(${alignLabel})</span>` : alignLabel;
      const photon = p.photon_missiles || 0;
      const probes = p.ether_probes || 0;
      const mines = (p.atomic_mines || 0);
      const extraEquip = [];
      if (photon) extraEquip.push(`<span class="equip-chip">⟡ ${photon} photon</span>`);
      if (probes) extraEquip.push(`<span class="equip-chip">◌ ${probes} probe</span>`);
      if (mines) extraEquip.push(`<span class="equip-chip danger">☢ ${mines} atomic</span>`);
      if (p.photon_disabled_ticks > 0) extraEquip.push(`<span class="equip-chip danger">DISABLED ${p.photon_disabled_ticks}t</span>`);
      const deaths = p.deaths || 0;
      const maxDeaths = p.max_deaths || 3;
      const corpInfo = p.corp_ticker
        ? `<span class="player-tag corp-tag" style="color:${p.color}">${esc(p.corp_ticker)}</span>`
        : "";
      const allianceTags = (p.alliances || []).map((allianceId) => {
        const alliance = state.alliances.find((a) => a.id === allianceId);
        if (!alliance) return `<span class="alliance-chip" title="pending">⚭ ${esc(allianceId)}</span>`;
        const partnerIds = (alliance.member_ids || []).filter((m) => m !== p.id);
        const partnerNames = partnerIds.map((mid) => {
          const partner = state.players.get(mid);
          return partner ? partner.name : mid;
        });
        const label = partnerNames.length ? partnerNames.join(",") : allianceId;
        const tag = alliance.active ? "⚭" : "⋯";
        return `<span class="alliance-chip${alliance.active ? "" : " pending"}" title="${esc(alliance.active ? "NAP active" : "proposed")}">${tag} ${esc(label.slice(0, 12))}</span>`;
      }).join("");
      card.innerHTML = `
        <div class="player-header">
          <div class="player-name">${esc(p.name)}<span class="rank-chip">${esc(rankLabel)}</span></div>
          <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
            <span class="player-tag">${p.kind || "?"}</span>
            ${corpInfo}
            ${p.alive ? "" : '<span class="player-tag" style="color:var(--danger); border-color:var(--danger)">KIA</span>'}
          </div>
        </div>
        <div class="player-stats">
          <div class="stat"><span class="k">Credits</span><span class="v">${fmt(p.credits || 0)}</span></div>
          <div class="stat"><span class="k">Net Worth</span><span class="v">${netWorth}</span></div>
          <div class="stat"><span class="k">Ship</span><span class="v">${shipShort(p.ship)}</span></div>
          <div class="stat"><span class="k">Sector</span><span class="v">${p.sector_id || "—"}</span></div>
          <div class="stat"><span class="k">Fighters</span><span class="v">${fmt(p.fighters || 0)}</span></div>
          <div class="stat"><span class="k">Shields</span><span class="v">${fmt(p.shields || 0)}</span></div>
          <div class="stat"><span class="k">Align</span><span class="v">${alignValue}</span></div>
          <div class="stat"><span class="k">XP</span><span class="v">${fmt(p.experience || 0)}</span></div>
          <div class="stat"><span class="k">Turns</span><span class="v">${turnsLabel}</span></div>
          <div class="stat"><span class="k">Lives</span><span class="v">${Math.max(0, maxDeaths - deaths)}/${maxDeaths}</span></div>
        </div>
        <div class="cargo-bar" title="Cargo holds">${cargoSegs}</div>
        <div class="cargo-legend">${cargoLabel}</div>
        ${extraEquip.length ? `<div class="equip-row">${extraEquip.join("")}</div>` : ""}
        ${allianceTags ? `<div class="alliance-row">${allianceTags}</div>` : ""}
        ${p.scratchpad ? `<div class="thought" title="Agent scratchpad">${esc(p.scratchpad).slice(0, 400)}</div>` : ""}
      `;
      grid.appendChild(card);
    }
  }

  function cargoBreakdown(p) {
    const holds = p.holds || 20;
    const cargo = p.cargo || {};
    const fo = cargo.fuel_ore || 0;
    const org = cargo.organics || 0;
    const eq = cargo.equipment || 0;
    const col = cargo.colonists || 0;
    const used = fo + org + eq + col;
    const items = [
      `<span class="cargo-item"><i class="cargo-dot fuel_ore"></i>FO ${fo}</span>`,
      `<span class="cargo-item"><i class="cargo-dot organics"></i>Org ${org}</span>`,
      `<span class="cargo-item"><i class="cargo-dot equipment"></i>Eq ${eq}</span>`,
    ];
    if (col > 0) items.push(`<span class="cargo-item"><i class="cargo-dot colonists"></i>Col ${col}</span>`);
    items.push(`<span class="cargo-item cargo-total">Holds ${used}/${holds}</span>`);
    return items.join("");
  }

  function cargoBar(p) {
    const holds = p.holds || 20;
    const cargo = p.cargo || {};
    const used = (cargo.fuel_ore || 0) + (cargo.organics || 0) + (cargo.equipment || 0) + (cargo.colonists || 0);
    const free = Math.max(0, holds - used);
    const segs = [];
    function seg(cls, val) {
      if (val <= 0) return;
      const pct = (val / holds) * 100;
      segs.push(`<div class="cargo-seg ${cls}" style="width:${pct.toFixed(1)}%"></div>`);
    }
    seg("fuel_ore", cargo.fuel_ore || 0);
    seg("organics", cargo.organics || 0);
    seg("equipment", cargo.equipment || 0);
    seg("empty", free);
    return segs.join("");
  }

  function shipShort(s) {
    if (!s) return "—";
    return String(s).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()).replace(/ship/i, "Ship");
  }

  // ----------------- Events ------------------------

  function renderEvents() {
    eventFeed.innerHTML = "";
    // If scrubbing, only render up to cursorIndex
    let source = state.events;
    if (state.replay.mode === "scrub" && state.replay.cursorIndex >= 0) {
      source = state.events.slice(0, state.replay.cursorIndex + 1);
    }
    const ordered = source.slice(-180);
    for (const ev of ordered) {
      if (!eventPassesFilter(ev)) continue;
      const li = document.createElement("li");
      const actor = ev.actor_id ? state.players.get(ev.actor_id) : null;
      const color = actor ? actor.color : "#8794b4";
      li.style.setProperty("--player-color", color);
      const kindClass = kindCategoryClass(ev.kind);
      li.innerHTML = `
        <span class="time">D${ev.day || 0}·${ev.tick || 0}</span>
        <span class="kind ${kindClass}">${escKind(ev.kind)}</span>
        <span class="msg">${esc(ev.summary || "")}</span>
      `;
      eventFeed.appendChild(li);
    }
    eventFeed.scrollTop = eventFeed.scrollHeight;
    renderScrubber();
  }

  function kindCategoryClass(kind) {
    if (!kind) return "system";
    if (kind.includes("combat") || kind === "mine_detonated" || kind === "ship_destroyed" || kind === "fed_response"
        || kind === "atomic_detonation" || kind === "port_destroyed" || kind === "photon_fired" || kind === "photon_hit"
        || kind === "ferrengi_attack" || kind === "player_eliminated") return "combat";
    if (kind === "trade" || kind === "trade_failed" || kind === "buy_ship" || kind === "buy_equip"
        || kind === "corp_deposit" || kind === "corp_withdraw") return "trade";
    if (kind === "warp" || kind === "warp_blocked" || kind === "scan" || kind === "probe"
        || kind === "autopilot" || kind === "ferrengi_move" || kind === "limpet_report") return "warp";
    if (kind === "agent_thought") return "thought";
    if (kind === "hail" || kind === "broadcast" || kind === "corp_memo"
        || kind === "alliance_proposed" || kind === "alliance_formed" || kind === "alliance_broken"
        || kind === "assign_colonists" || kind === "build_citadel" || kind === "citadel_complete"
        || kind === "genesis_deployed") return "diplomacy";
    if (kind === "game_over" || kind === "game_start") return kind;
    return "system";
  }

  function eventPassesFilter(ev) {
    const f = state.filters;
    const cat = kindCategoryClass(ev.kind);
    if (cat === "combat" && !f.combat) return false;
    if (cat === "trade" && !f.trade) return false;
    if (cat === "warp" && !f.move) return false;
    if (cat === "thought" && !f.thought) return false;
    if (cat === "system" && !f.system) return false;
    if (cat === "diplomacy" && !f.diplomacy) return false;
    return true;
  }

  // ----------------- Replay scrubber ---------------

  function renderScrubber() {
    const scrub = document.getElementById("replayScrub");
    const label = document.getElementById("replayLabel");
    const liveBtn = document.getElementById("replayLive");
    if (!scrub || !label) return;
    const total = Math.max(0, state.events.length - 1);
    scrub.max = String(total);
    if (state.replay.mode === "live") {
      scrub.value = String(total);
      label.textContent = "live";
      label.classList.remove("scrubbing");
      if (liveBtn) liveBtn.classList.add("active");
    } else {
      const idx = Math.min(state.replay.cursorIndex, total);
      scrub.value = String(Math.max(0, idx));
      const ev = state.events[idx];
      if (ev) label.textContent = `D${ev.day || 0}·${ev.tick || 0} (${idx + 1}/${total + 1})`;
      else label.textContent = "scrubbing";
      label.classList.add("scrubbing");
      if (liveBtn) liveBtn.classList.remove("active");
    }
  }

  function setupScrubber() {
    const scrub = document.getElementById("replayScrub");
    const liveBtn = document.getElementById("replayLive");
    if (!scrub) return;
    scrub.addEventListener("input", () => {
      state.replay.mode = "scrub";
      state.replay.cursorIndex = parseInt(scrub.value, 10) || 0;
      render();
    });
    if (liveBtn) {
      liveBtn.addEventListener("click", () => {
        state.replay.mode = "live";
        state.replay.cursorIndex = -1;
        render();
      });
    }
  }

  function escKind(k) { return String(k || "").replace(/_/g, " "); }

  // ----------------- Messaging ---------------------

  function renderMessages() {
    messageFeed.innerHTML = "";
    for (const m of state.messages.slice(-100)) {
      const from = state.players.get(m.from);
      const to = m.target ? state.players.get(m.target) : null;
      const d = document.createElement("div");
      d.className = "message";
      d.style.setProperty("--player-color", from ? from.color : "#6ee7ff");
      const time = `D${m.day || 0}·${m.tick || 0}`;
      const prefix = m.kind === "broadcast" ? "📡 BROADCAST" : `→ ${to ? to.name : m.target}`;
      d.innerHTML = `
        <span class="time">${time}</span>
        <span class="from">${from ? esc(from.name) : esc(m.from)}</span>
        <span class="to">${prefix}</span><br/>
        <span class="body">${esc(m.message || "")}</span>
      `;
      messageFeed.appendChild(d);
    }
    messageFeed.scrollTop = messageFeed.scrollHeight;
  }

  // ----------------- Top bar state -----------------

  function renderHeader() {
    dayLabel.textContent = `Day ${state.day}/${state.maxDays}`;
    tickLabel.textContent = `Tick ${state.tick}`;
    const mapHeader = document.querySelector(".map-panel .panel-header h2");
    if (mapHeader && state.sectors.size > 0) {
      mapHeader.innerHTML = `Galaxy <span class="muted">· ${state.sectors.size} sectors</span>`;
    }
    if (state.finished) setStatus("finished", "match complete");
    else if (state.status === "running") setStatus("running", "live");
    else if (state.status === "paused") setStatus("paused", "paused");
    else if (state.status === "error") setStatus("error", "error");
    else setStatus("running", state.status || "waiting");
  }

  // ----------------- Game over ---------------------

  function showGameOver(ev) {
    const winner = state.winner_id ? state.players.get(state.winner_id) : null;
    const reason = state.win_reason || (ev && ev.payload && ev.payload.reason) || "unknown";
    gameOverSummary.innerHTML = winner
      ? `<strong style="color:${winner.color}">${esc(winner.name)}</strong> wins by <em>${esc(reason)}</em>.<br/>Final net worth: ${fmt(winner.net_worth || winner.credits || 0)} credits.`
      : `The match has ended (${esc(reason)}).`;
    gameOverModal.hidden = false;
  }

  // ----------------- Helpers ------------------------

  function fmt(n) {
    if (n == null) return "—";
    const abs = Math.abs(n);
    if (abs >= 1_000_000_000) return (n / 1e9).toFixed(2) + "B";
    if (abs >= 1_000_000) return (n / 1e6).toFixed(2) + "M";
    if (abs >= 10_000) return (n / 1e3).toFixed(1) + "k";
    return String(Math.round(n));
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  // ----------------- Main render -------------------

  let rafPending = false;
  function render() {
    if (rafPending) return;
    rafPending = true;
    requestAnimationFrame(() => {
      rafPending = false;
      renderHeader();
      renderDynamicMap();
      renderPlayers();
      renderEvents();
      renderMessages();
    });
  }

  // Animate the warp trail fade even without events
  setInterval(renderDynamicMap, 400);

  // ----------------- Control events -----------------

  pauseBtn.addEventListener("click", async () => {
    const endpoint = state.status === "paused" ? "/control/resume" : "/control/pause";
    const r = await fetch(endpoint, { method: "POST" });
    const data = await r.json();
    state.status = data.status || state.status;
    pauseBtn.textContent = state.status === "paused" ? "▶" : "⏸";
    render();
  });
  document.querySelectorAll(".speed-group button").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const mult = parseFloat(btn.dataset.speed);
      await fetch("/control/speed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ multiplier: mult }),
      });
      document.querySelectorAll(".speed-group button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
    });
  });
  restartBtn.addEventListener("click", async () => {
    if (!confirm("Start a new match? Current match will be discarded.")) return;
    const newSeed = Math.floor(Math.random() * 1_000_000);
    state.events.length = 0;
    state.messages.length = 0;
    state.recentWarp.length = 0;
    state.finished = false;
    state.winner_id = null;
    gameOverModal.hidden = true;
    await fetch("/control/restart", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seed: newSeed }),
    });
  });
  modalClose.addEventListener("click", () => { gameOverModal.hidden = true; });

  document.querySelectorAll(".filter-group input").forEach((el) => {
    el.addEventListener("change", () => {
      state.filters[el.dataset.filter] = el.checked;
      render();
    });
  });

  // ----------------- Layout: resize / collapse / shortcuts (Phase 1) ------

  const LAYOUT_KEY = "tw2k:layout:v1";

  function loadLayout() {
    try {
      const raw = localStorage.getItem(LAYOUT_KEY);
      if (!raw) return {};
      return JSON.parse(raw) || {};
    } catch (_e) { return {}; }
  }
  function saveLayout(patch) {
    try {
      const cur = loadLayout();
      localStorage.setItem(LAYOUT_KEY, JSON.stringify(Object.assign(cur, patch)));
    } catch (_e) { /* quota / disabled storage */ }
  }

  function applyLayout(cfg) {
    const layout = document.getElementById("layout");
    if (!layout) return;
    const left = document.getElementById("colLeft");
    const right = document.getElementById("colRight");
    if (cfg.rightWidthPx != null && right) {
      right.style.flex = `0 0 ${clamp(cfg.rightWidthPx, 240, 900)}px`;
    }
    const mapPanel = document.getElementById("panelMap");
    const eventsPanel = document.getElementById("panelEvents");
    if (mapPanel && cfg.mapFlex != null) mapPanel.style.flex = `${cfg.mapFlex} 1 0`;
    if (eventsPanel && cfg.eventsFlex != null) eventsPanel.style.flex = `${cfg.eventsFlex} 1 0`;
    const playersPanelEl = document.getElementById("panelPlayers");
    const messagesPanel = document.getElementById("panelMessages");
    if (playersPanelEl && cfg.playersFlex != null) playersPanelEl.style.flex = `${cfg.playersFlex} 1 0`;
    if (messagesPanel && cfg.messagesFlex != null) messagesPanel.style.flex = `${cfg.messagesFlex} 1 0`;

    const collapsed = cfg.collapsed || {};
    document.querySelectorAll(".panel[data-panel]").forEach((panel) => {
      const key = panel.dataset.panel;
      panel.classList.toggle("collapsed", !!collapsed[key]);
    });
  }

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  function resetLayout() {
    try { localStorage.removeItem(LAYOUT_KEY); } catch (_e) {}
    // clear inline styles that we previously set
    ["colLeft","colRight","panelMap","panelEvents","panelPlayers","panelMessages"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.style.flex = "";
    });
    document.querySelectorAll(".panel.collapsed").forEach((p) => p.classList.remove("collapsed"));
  }

  function initResizers() {
    document.querySelectorAll(".resize-handle").forEach((handle) => {
      handle.addEventListener("pointerdown", (e) => startResize(e, handle));
    });
  }

  function startResize(e, handle) {
    e.preventDefault();
    handle.setPointerCapture(e.pointerId);
    handle.classList.add("dragging");
    const kind = handle.dataset.resize;
    const horizontal = handle.classList.contains("resize-horizontal");
    const startX = e.clientX;
    const startY = e.clientY;

    // Capture adjacent panels' initial sizes
    const prev = handle.previousElementSibling;
    const next = handle.nextElementSibling;
    const prevRect = prev ? prev.getBoundingClientRect() : null;
    const nextRect = next ? next.getBoundingClientRect() : null;

    function onMove(ev) {
      if (kind === "left-right") {
        const delta = ev.clientX - startX;
        const right = document.getElementById("colRight");
        if (!right) return;
        const rightStart = right.getBoundingClientRect().width;
        const newWidth = clamp(rightStart - delta, 240, 900);
        right.style.flex = `0 0 ${newWidth}px`;
        saveLayout({ rightWidthPx: newWidth });
        return;
      }
      if (!prev || !next || !prevRect || !nextRect) return;
      if (horizontal) {
        const total = prevRect.height + nextRect.height;
        if (total < 50) return;
        const newPrev = clamp(prevRect.height + (ev.clientY - startY), 44, total - 44);
        const newNext = total - newPrev;
        const ratio = newPrev / newNext;
        prev.style.flex = `${ratio.toFixed(3)} 1 0`;
        next.style.flex = `1 1 0`;
        if (kind === "map-events") {
          saveLayout({ mapFlex: +ratio.toFixed(3), eventsFlex: 1 });
        } else if (kind === "players-messages") {
          saveLayout({ playersFlex: +ratio.toFixed(3), messagesFlex: 1 });
        }
      }
    }
    function onUp() {
      handle.classList.remove("dragging");
      try { handle.releasePointerCapture(e.pointerId); } catch (_e) {}
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", onUp);
    }
    document.addEventListener("pointermove", onMove);
    document.addEventListener("pointerup", onUp);
  }

  function togglePanel(key) {
    const panel = document.querySelector(`.panel[data-panel="${key}"]`);
    if (!panel) return;
    panel.classList.toggle("collapsed");
    const cfg = loadLayout();
    const collapsed = Object.assign({}, cfg.collapsed || {});
    collapsed[key] = panel.classList.contains("collapsed");
    saveLayout({ collapsed });
  }

  function initCollapseButtons() {
    // Use event delegation: static buttons exist in HTML, players-panel
    // button is injected by renderPlayers().
    document.addEventListener("click", (e) => {
      const btn = e.target.closest(".collapse-btn");
      if (!btn) return;
      togglePanel(btn.dataset.collapse);
    });
  }

  function toggleFullscreenMap(force) {
    const layout = document.getElementById("layout");
    if (!layout) return;
    const next = force != null ? force : !layout.classList.contains("fullscreen-map");
    layout.classList.toggle("fullscreen-map", next);
    saveLayout({ fullscreenMap: next });
  }

  function toggleShortcutsToast() {
    const toast = document.getElementById("shortcutsToast");
    if (!toast) return;
    toast.hidden = !toast.hidden;
  }

  function initShortcuts() {
    document.addEventListener("keydown", (e) => {
      // Don't hijack typing in inputs
      const tag = (e.target && e.target.tagName) || "";
      if (tag === "INPUT" || tag === "TEXTAREA" || e.target.isContentEditable) return;

      if (e.code === "Space" && !e.repeat) {
        e.preventDefault();
        if (pauseBtn) pauseBtn.click();
        return;
      }
      if (e.key === "Escape") {
        const layout = document.getElementById("layout");
        if (layout && layout.classList.contains("fullscreen-map")) {
          toggleFullscreenMap(false);
          return;
        }
        if (gameOverModal && !gameOverModal.hidden) {
          gameOverModal.hidden = true;
          return;
        }
        const toast = document.getElementById("shortcutsToast");
        if (toast && !toast.hidden) toast.hidden = true;
        return;
      }
      if (e.key === "f" || e.key === "F") {
        e.preventDefault();
        toggleFullscreenMap();
        return;
      }
      if (e.key === "?" || (e.shiftKey && e.key === "/")) {
        e.preventDefault();
        toggleShortcutsToast();
        return;
      }
      if (e.key === "r" || e.key === "R") {
        if (e.ctrlKey || e.metaKey || e.altKey) return; // don't catch reload
        e.preventDefault();
        resetLayout();
        return;
      }
      if (/^[1-9]$/.test(e.key)) {
        const idx = parseInt(e.key, 10) - 1;
        const players = Array.from(state.players.values());
        const p = players[idx];
        if (!p) return;
        // Phase 3 will follow-camera; for now: select + flash the card.
        state.selectedPlayerId = p.id;
        const card = document.querySelector(`.player-card[data-pid="${p.id}"]`);
        if (card) {
          card.classList.add("flash");
          setTimeout(() => card.classList.remove("flash"), 700);
        }
      }
    });
  }

  function initLayout() {
    const cfg = loadLayout();
    applyLayout(cfg);
    if (cfg.fullscreenMap) toggleFullscreenMap(true);
    initResizers();
    initCollapseButtons();
    initShortcuts();
  }

  // Kick off
  initLayout();
  setupScrubber();
  connect();
  render();
})();
