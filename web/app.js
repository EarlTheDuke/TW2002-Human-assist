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
    followPlayerId: null,      // map camera locks on this player when set
    hoverSectorId: null,       // transient; highlights a sector neighborhood while hovering
    reverseWarps: new Map(),   // id -> Set(ids that warp TO id). Built in buildMap.
    drawer: { kind: null, id: null }, // kind = "player" | "sector" | null
    history: new Map(),        // pid -> [{seq, day, credits, net_worth, fighters, ...}]
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
  const mapControls = document.getElementById("mapControls");
  const mapZoomReadout = document.getElementById("mapZoomReadout");
  const miniMap = document.getElementById("miniMap");
  const miniMapSvg = document.getElementById("miniMapSvg");
  const detailDrawer = document.getElementById("detailDrawer");
  const drawerBody = document.getElementById("drawerBody");
  const drawerTitle = document.getElementById("drawerTitle");
  const drawerFollowBtn = document.getElementById("drawerFollowBtn");
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
    // Planet delta — created or mutated by genesis / assign / citadel events.
    // Merge into state.planets so the commander-card Planets block, the map
    // sector tooltips, and the drawer all see it on the NEXT render tick
    // without needing a page reload.
    if (patch.planet) {
      const prev = state.planets.get(patch.planet.id) || {};
      state.planets.set(patch.planet.id, Object.assign({}, prev, patch.planet));
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
  // Full-galaxy extent ("fit" target). Populated by buildMap().
  let galaxyExtent = { x: -600, y: -600, w: 1200, h: 1200 };
  // Mini-map visibility (persisted to localStorage). Defaults to visible.
  let miniMapVisible = true;

  function buildMap() {
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    if (state.sectors.size === 0) return;
    const b = state.bounds;
    const pad = 30;
    galaxyExtent = {
      x: b.minX - pad,
      y: b.minY - pad,
      w: (b.maxX - b.minX) + 2 * pad,
      h: (b.maxY - b.minY) + 2 * pad,
    };
    viewBoxState = { ...galaxyExtent };
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
    // two-way warps as simple lines. Each line is tagged with data-a/data-b
    // so focus highlighting can pick out warps touching a given sector in O(1).
    // Also build the reverse-warp index (who warps TO each sector) so
    // applyFocusHighlight() can show "warps IN" as well as "warps OUT".
    state.reverseWarps.clear();
    for (const s of state.sectors.values()) {
      for (const w of s.warps || []) {
        if (!state.reverseWarps.has(w)) state.reverseWarps.set(w, new Set());
        state.reverseWarps.get(w).add(s.id);
      }
    }
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
        line.setAttribute("data-a", s.id);
        line.setAttribute("data-b", w);
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

      g.addEventListener("mouseenter", (e) => {
        showSectorTip(s, e);
        state.hoverSectorId = s.id;
        applyFocusHighlight();
      });
      g.addEventListener("mouseleave", () => {
        hideSectorTip();
        if (state.hoverSectorId === s.id) {
          state.hoverSectorId = null;
          applyFocusHighlight();
        }
      });
      g.addEventListener("click", (e) => {
        e.stopPropagation();
        // Toggle: clicking the already-selected sector clears focus.
        if (state.selectedSectorId === s.id && state.drawer.kind === "sector") {
          state.selectedSectorId = null;
          closeDrawer();
          applyFocusHighlight();
          return;
        }
        state.selectedSectorId = s.id;
        openDrawer("sector", s.id);
      });
      sectorsLayer.appendChild(g);
    }

    enablePanZoom();
    buildMiniMap();
    updateViewBox();
    applyFocusHighlight();
  }

  // Apply focus classes so the map visually isolates one sector's
  // neighborhood from the 1,500-edge background spaghetti. Called whenever
  // selection or hover changes. An explicit selection (click) beats hover;
  // hover only highlights when no sector is selected.
  function applyFocusHighlight() {
    if (!svg) return;
    const fid = state.selectedSectorId != null ? state.selectedSectorId : state.hoverSectorId;
    if (fid == null) {
      svg.classList.remove("has-focus");
      svg.querySelectorAll(
        ".focused-self, .focused-neighbor, .focused-warp, .unfocused"
      ).forEach((el) => {
        el.classList.remove("focused-self", "focused-neighbor", "focused-warp", "unfocused");
      });
      return;
    }
    svg.classList.add("has-focus");
    const sector = state.sectors.get(fid);
    const neighbors = new Set();
    if (sector && sector.warps) for (const w of sector.warps) neighbors.add(w);
    const rev = state.reverseWarps.get(fid);
    if (rev) for (const w of rev) neighbors.add(w);

    svg.querySelectorAll("#sectors-layer [data-id]").forEach((g) => {
      const id = Number(g.getAttribute("data-id"));
      g.classList.remove("focused-self", "focused-neighbor", "unfocused");
      if (id === fid) g.classList.add("focused-self");
      else if (neighbors.has(id)) g.classList.add("focused-neighbor");
      else g.classList.add("unfocused");
    });
    svg.querySelectorAll("#warps-layer line.warp").forEach((ln) => {
      const a = Number(ln.getAttribute("data-a"));
      const b = Number(ln.getAttribute("data-b"));
      if (a === fid || b === fid) ln.classList.add("focused-warp");
      else ln.classList.remove("focused-warp");
    });
  }

  // Return a zoom ratio in [0, +inf) where 1.0 = full galaxy visible.
  // Smaller numbers = zoomed OUT (wider view than galaxy), larger = zoomed IN.
  function currentZoom() {
    if (!galaxyExtent.w || !viewBoxState.w) return 1;
    return galaxyExtent.w / viewBoxState.w;
  }

  function updateLODClasses() {
    if (!svg) return;
    const z = currentZoom();
    svg.classList.remove("zoom-far", "zoom-mid", "zoom-near");
    if (z < 0.75) svg.classList.add("zoom-far");
    else if (z < 2.2) svg.classList.add("zoom-mid");
    else svg.classList.add("zoom-near");
  }

  function updateZoomReadout() {
    if (!mapZoomReadout) return;
    const pct = Math.round(currentZoom() * 100);
    mapZoomReadout.textContent = `${pct}%`;
  }

  function updateMiniViewport() {
    if (!miniMapSvg) return;
    const rect = miniMapSvg.querySelector(".mini-viewport");
    if (!rect) return;
    rect.setAttribute("x", viewBoxState.x);
    rect.setAttribute("y", viewBoxState.y);
    rect.setAttribute("width", viewBoxState.w);
    rect.setAttribute("height", viewBoxState.h);
  }

  function updateViewBox() {
    svg.setAttribute("viewBox", `${viewBoxState.x} ${viewBoxState.y} ${viewBoxState.w} ${viewBoxState.h}`);
    updateLODClasses();
    updateZoomReadout();
    updateMiniViewport();
  }

  function fitGalaxy() {
    viewBoxState = { ...galaxyExtent };
    updateViewBox();
  }

  function zoomBy(factor, cx, cy) {
    // Clamp so we can't zoom past useful limits.
    const minW = galaxyExtent.w * 0.08;   // 12.5x zoom-in max
    const maxW = galaxyExtent.w * 3;      // 3x zoom-out max
    const newW = Math.max(minW, Math.min(maxW, viewBoxState.w * factor));
    const realFactor = newW / viewBoxState.w;
    if (cx == null) cx = viewBoxState.x + viewBoxState.w / 2;
    if (cy == null) cy = viewBoxState.y + viewBoxState.h / 2;
    viewBoxState.w *= realFactor;
    viewBoxState.h *= realFactor;
    viewBoxState.x = cx - (cx - viewBoxState.x) * realFactor;
    viewBoxState.y = cy - (cy - viewBoxState.y) * realFactor;
    updateViewBox();
  }

  function buildMiniMap() {
    if (!miniMapSvg) return;
    while (miniMapSvg.firstChild) miniMapSvg.removeChild(miniMapSvg.firstChild);
    miniMapSvg.setAttribute(
      "viewBox",
      `${galaxyExtent.x} ${galaxyExtent.y} ${galaxyExtent.w} ${galaxyExtent.h}`
    );
    // Static sector dots (no warps — keep it clean).
    const dots = document.createElementNS(svgNS, "g");
    for (const s of state.sectors.values()) {
      const c = document.createElementNS(svgNS, "circle");
      c.setAttribute("cx", s.x);
      c.setAttribute("cy", s.y);
      c.setAttribute("r", s.id === 1 ? 6 : (s.port ? 3.5 : 2.2));
      let cls = "mini-sector";
      if (s.id === 1) cls += " stardock";
      else if (s.port) cls += " port";
      c.setAttribute("class", cls);
      dots.appendChild(c);
    }
    miniMapSvg.appendChild(dots);
    // Dynamic ship + viewport group (refreshed each render).
    const shipsG = document.createElementNS(svgNS, "g");
    shipsG.setAttribute("id", "mini-ships-layer");
    miniMapSvg.appendChild(shipsG);
    const vp = document.createElementNS(svgNS, "rect");
    vp.setAttribute("class", "mini-viewport");
    miniMapSvg.appendChild(vp);
    updateMiniViewport();

    // Click-to-center: recenter viewBox at click point in galaxy coords.
    miniMapSvg.onclick = (e) => {
      const rect = miniMapSvg.getBoundingClientRect();
      const gx = galaxyExtent.x + ((e.clientX - rect.left) / rect.width) * galaxyExtent.w;
      const gy = galaxyExtent.y + ((e.clientY - rect.top) / rect.height) * galaxyExtent.h;
      viewBoxState.x = gx - viewBoxState.w / 2;
      viewBoxState.y = gy - viewBoxState.h / 2;
      updateViewBox();
    };
  }

  function refreshMiniShips() {
    if (!miniMapSvg) return;
    const layer = miniMapSvg.querySelector("#mini-ships-layer");
    if (!layer) return;
    while (layer.firstChild) layer.removeChild(layer.firstChild);
    for (const p of state.players.values()) {
      if (!p.alive) continue;
      const s = state.sectors.get(p.sector_id);
      if (!s) continue;
      const c = document.createElementNS(svgNS, "circle");
      c.setAttribute("cx", s.x);
      c.setAttribute("cy", s.y);
      c.setAttribute("r", 4.5);
      c.setAttribute("fill", p.color || "#6ee7ff");
      c.setAttribute("stroke", "#0a0f1c");
      c.setAttribute("stroke-width", "0.6");
      c.setAttribute("class", "mini-ship");
      layer.appendChild(c);
    }
  }

  function setMiniMapVisible(visible) {
    miniMapVisible = !!visible;
    if (miniMap) miniMap.classList.toggle("hidden", !miniMapVisible);
    try { localStorage.setItem("tw2k:map:mini", miniMapVisible ? "1" : "0"); } catch {}
  }

  function initMapControls() {
    if (!mapControls) return;
    mapControls.addEventListener("click", (e) => {
      const btn = e.target.closest(".map-btn");
      if (!btn) return;
      const action = btn.dataset.mapAction;
      if (action === "zoom-in") zoomBy(0.8);
      else if (action === "zoom-out") zoomBy(1.25);
      else if (action === "fit") fitGalaxy();
      else if (action === "toggle-mini") setMiniMapVisible(!miniMapVisible);
    });
    // Restore persisted mini-map visibility.
    try {
      const saved = localStorage.getItem("tw2k:map:mini");
      if (saved === "0") setMiniMapVisible(false);
    } catch {}
  }

  function enablePanZoom() {
    let dragging = false;
    let didDrag = false;
    let lastX = 0, lastY = 0;
    let downX = 0, downY = 0;
    svg.addEventListener("mousedown", (e) => {
      dragging = true;
      didDrag = false;
      lastX = downX = e.clientX;
      lastY = downY = e.clientY;
    });
    window.addEventListener("mouseup", () => { dragging = false; });
    // Click on the SVG background (not a sector — sector clicks stopPropagation)
    // clears focus. We only treat a true tap as a click: if the pointer moved
    // more than 4px between down and up, it was a pan, not a click.
    svg.addEventListener("click", (e) => {
      if (didDrag) return;
      if (state.selectedSectorId != null) {
        state.selectedSectorId = null;
        if (state.drawer.kind === "sector") closeDrawer();
        else applyFocusHighlight();
      }
    });
    window.addEventListener("mousemove", (e) => {
      if (!dragging) return;
      if (Math.abs(e.clientX - downX) + Math.abs(e.clientY - downY) > 4) didDrag = true;
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
      const minW = galaxyExtent.w * 0.08;
      const maxW = galaxyExtent.w * 3;
      const targetW = Math.max(minW, Math.min(maxW, viewBoxState.w * factor));
      const realFactor = targetW / viewBoxState.w;
      viewBoxState.w *= realFactor;
      viewBoxState.h *= realFactor;
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
    refreshMiniShips();
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

      // Follow-camera indicator ring (Phase 3).
      if (state.followPlayerId === p.id) {
        const followRing = document.createElementNS(svgNS, "circle");
        followRing.setAttribute("cx", s.x);
        followRing.setAttribute("cy", s.y);
        followRing.setAttribute("r", 9);
        followRing.setAttribute("class", "ship-follow-ring");
        shipsLayer.appendChild(followRing);
      }
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
          <button class="mini-btn" id="cardsCollapseAll" title="Collapse all commander cards">⇡ All</button>
          <button class="mini-btn" id="cardsExpandAll" title="Expand all commander cards">⇣ All</button>
          <button class="collapse-btn" data-collapse="players" title="Collapse commanders">▾</button>
        </div>
      `;
      container.appendChild(header);
      // Wire up the bulk toggles once. Writing to localStorage and then
      // calling renderPlayers() rebuilds every <details> with the correct
      // open state, so the UI and persistence stay in sync.
      header.querySelector("#cardsCollapseAll")?.addEventListener("click", () => {
        const ids = Array.from(state.players.keys()).join(",");
        localStorage.setItem("tw2k_collapsed_cards", ids);
        renderPlayers();
      });
      header.querySelector("#cardsExpandAll")?.addEventListener("click", () => {
        localStorage.setItem("tw2k_collapsed_cards", "");
        renderPlayers();
      });
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
    // Per-card collapse state lives in localStorage keyed by player id.
    // Absence of the key -> card starts open (default). Spectators can
    // collapse cards they don't care about and the choice survives refresh.
    const collapsedIds = new Set(
      (localStorage.getItem("tw2k_collapsed_cards") || "").split(",").filter(Boolean)
    );
    for (const p of state.players.values()) {
      const card = document.createElement("details");
      card.className = "player-card" + (p.alive ? "" : " dead")
        + (state.selectedPlayerId === p.id ? " selected" : "");
      card.dataset.pid = p.id;
      if (!collapsedIds.has(p.id)) card.open = true;
      card.style.setProperty("--player-color", p.color || "#6ee7ff");
      // Net worth = ship assets + planets owned. We show a tooltip
      // with the breakdown so spectators can see "this commander's 40k
      // is 10k cash + 5k cargo + 25k in Citadel investment" at a glance.
      const totalNet = p.net_worth || p.credits || 0;
      const shipNet = p.net_worth_ship != null ? p.net_worth_ship : totalNet;
      const planetNet = Math.max(0, totalNet - shipNet);
      const netWorthTitle = planetNet > 0
        ? `ship ${fmt(shipNet)} cr + planets ${fmt(planetNet)} cr`
        : `ship-side only (no owned planets)`;
      const netWorthSuffix = planetNet > 0
        ? ` <span class="net-worth-planet" title="${netWorthTitle}">+${fmt(planetNet)}p</span>`
        : "";
      const netWorth = `<span title="${netWorthTitle}">${fmt(totalNet)}</span>${netWorthSuffix}`;
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
      // Compact summary shown both in collapsed and expanded states.
      // Must be the first child of <details> for native click-to-toggle.
      // Mini-stats give at-a-glance comparison across 4 cards without
      // needing to expand everything.
      const shipShortLabel = shipShort(p.ship);
      const sectorLabel = p.sector_id != null ? p.sector_id : "—";
      const planetCount = Array.from(state.planets.values()).filter((pl) => pl.owner_id === p.id).length;
      const planetChip = planetCount > 0
        ? `<span class="pc-sum-chip" title="${planetCount} owned planet(s)">🪐 ${planetCount}</span>`
        : "";
      const summaryHtml = `
        <summary class="player-card-summary" title="click to collapse/expand ${esc(p.name)}">
          <span class="pc-sum-main">
            <span class="pc-sum-name">${esc(p.name)}</span>
            <span class="rank-chip">${esc(rankLabel)}</span>
            ${p.alive ? "" : '<span class="player-tag" style="color:var(--danger); border-color:var(--danger)">KIA</span>'}
          </span>
          <span class="pc-sum-stats">
            <span class="pc-sum-chip" title="credits on hand">💰 ${fmt(p.credits || 0)}</span>
            <span class="pc-sum-chip" title="total net worth (ship + planets)">📈 ${fmt(totalNet)}</span>
            <span class="pc-sum-chip" title="${esc(p.ship || "—")}">🛸 ${esc(shipShortLabel)}</span>
            <span class="pc-sum-chip" title="current sector">📍 s${sectorLabel}</span>
            ${planetChip}
          </span>
        </summary>
      `;

      card.innerHTML = `
        ${summaryHtml}
        <div class="player-card-body">
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
            <div class="stat" title="Ports this commander has visited and has intel on"><span class="k">Ports Seen</span><span class="v">${fmt(p.known_ports_count || 0)}</span></div>
          </div>
          <div class="cargo-bar" title="Cargo holds">${cargoSegs}</div>
          <div class="cargo-legend">${cargoLabel}</div>
          ${extraEquip.length ? `<div class="equip-row">${extraEquip.join("")}</div>` : ""}
          ${allianceTags ? `<div class="alliance-row">${allianceTags}</div>` : ""}
          ${renderGoalsBlock(p)}
          ${renderPlanetsBlock(p)}
          ${renderTradesBlock(p)}
          ${renderSparklineRow(p.id, p.color)}
          ${p.scratchpad ? `<div class="thought" title="Agent scratchpad">${esc(p.scratchpad).slice(0, 400)}</div>` : ""}
        </div>
      `;
      // Persist collapse state on toggle. Delegating to 'toggle' event
      // because details/summary fires it natively, and this survives
      // re-renders since the event handler is re-bound each frame.
      card.addEventListener("toggle", () => {
        const ids = new Set(
          (localStorage.getItem("tw2k_collapsed_cards") || "").split(",").filter(Boolean)
        );
        if (card.open) ids.delete(p.id);
        else ids.add(p.id);
        localStorage.setItem("tw2k_collapsed_cards", Array.from(ids).join(","));
      });
      grid.appendChild(card);
    }
  }

  function cargoBreakdown(p) {
    const holds = p.holds || 20;
    const cargo = p.cargo || {};
    const costs = p.cargo_cost_avg || {};
    const fo = cargo.fuel_ore || 0;
    const org = cargo.organics || 0;
    const eq = cargo.equipment || 0;
    const col = cargo.colonists || 0;
    const tag = (name, qty) => {
      const avg = costs[name];
      return qty > 0 && avg ? ` <span class="cargo-basis" title="avg paid ${avg} cr/unit">@${avg}</span>` : "";
    };
    const used = fo + org + eq + col;
    const items = [
      `<span class="cargo-item"><i class="cargo-dot fuel_ore"></i>FO ${fo}${tag("fuel_ore", fo)}</span>`,
      `<span class="cargo-item"><i class="cargo-dot organics"></i>Org ${org}${tag("organics", org)}</span>`,
      `<span class="cargo-item"><i class="cargo-dot equipment"></i>Eq ${eq}${tag("equipment", eq)}</span>`,
    ];
    if (col > 0) items.push(`<span class="cargo-item"><i class="cargo-dot colonists"></i>Col ${col}${tag("colonists", col)}</span>`);
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

  function renderGoalsBlock(p) {
    const s = (p.goal_short || "").trim();
    const m = (p.goal_medium || "").trim();
    const l = (p.goal_long || "").trim();
    if (!s && !m && !l) return "";
    const line = (label, text, cls) => {
      if (!text) return "";
      const short = text.length > 110 ? text.slice(0, 108) + "…" : text;
      return `<div class="goal-line ${cls}" title="${esc(text)}"><span class="goal-chip">${label}</span><span class="goal-text">${esc(short)}</span></div>`;
    };
    return `
      <details class="player-goals" open>
        <summary>Goals</summary>
        ${line("S", s, "short")}
        ${line("M", m, "medium")}
        ${line("L", l, "long")}
      </details>
    `;
  }

  function renderPlanetsBlock(p) {
    // Filter the universe-wide planets list down to what this commander owns.
    // We ALWAYS render the block so spectators can see the planet slot on the
    // card — the placeholder state doubles as a teaching tool (shows the
    // 25k-credit gate to Genesis and how close the commander is).
    const owned = Array.from(state.planets.values()).filter((pl) => pl.owner_id === p.id);
    if (!owned.length) {
      const genesisCount = p.genesis || 0;
      const credits = p.credits || 0;
      const GENESIS_COST = 25000;
      let status;
      if (genesisCount > 0) {
        status = `<span class="planet-empty-hint">${genesisCount} Genesis torpedo loaded — warp deep (3+ hops from StarDock) and deploy</span>`;
      } else if (credits >= GENESIS_COST) {
        status = `<span class="planet-empty-hint">Can afford Genesis torpedo (25k cr) at StarDock — ${fmt(credits)} credits on hand</span>`;
      } else {
        const needed = GENESIS_COST - credits;
        status = `<span class="planet-empty-hint">Grinding to 25k cr for first Genesis — ${fmt(needed)} cr short</span>`;
      }
      return `
        <details class="commander-planets empty" open>
          <summary>Planets (0)</summary>
          <div class="planet-empty">${status}</div>
        </details>
      `;
    }

    // Sort by citadel level desc, then by planet id — makes the biggest
    // investment show first and is stable across ticks.
    owned.sort((a, b) => (b.citadel_level || 0) - (a.citadel_level || 0) || a.id - b.id);

    const commAbbrev = { fuel_ore: "FO", organics: "Org", equipment: "Eq", colonists: "Col" };
    const totalIdle = owned.reduce((acc, pl) => acc + ((pl.colonists && pl.colonists.colonists) || 0), 0);
    const totalCitadels = owned.reduce((acc, pl) => acc + (pl.citadel_level || 0), 0);

    // Citadel tier table mirrors engine K.CITADEL_TIER_COST (1..6).
    // Kept in sync with constants.py so the UI can show "next tier costs X".
    // [credits, colonists, days_to_build, perks]
    const CITADEL_TIERS = [
      { cr:   5000, col:  1000, days: 1, perk: "Basic fortifications" },
      { cr:  10000, col:  2000, days: 1, perk: "Quasar Cannons — free planet fighters + shields" },
      { cr:  20000, col:  4000, days: 2, perk: "Transwarp emissions damping" },
      { cr:  40000, col:  8000, days: 2, perk: "Genesis torpedoes manufactured on-site" },
      { cr:  80000, col: 16000, days: 3, perk: "Planetary Interdictor — blocks hostile warps" },
      { cr: 160000, col: 32000, days: 4, perk: "MAX — full fortress" },
    ];

    const rows = owned.map((pl) => {
      const col = pl.colonists || {};
      const stock = pl.stockpile || {};
      const idle = col.colonists || 0;
      const level = pl.citadel_level || 0;
      const target = pl.citadel_target || 0;
      const inProgress = target > level;
      const totalCol = (col.fuel_ore || 0) + (col.organics || 0) + (col.equipment || 0) + idle;

      // --- Citadel chip header ---
      const citadelLabel = inProgress ? `L${level} → L${target}` : `L${level}`;
      const citadelCls = inProgress ? "citadel-chip building" : "citadel-chip";
      const citadelTitle = inProgress
        ? (pl.citadel_complete_day != null
            ? `upgrading to L${target}, completes day ${pl.citadel_complete_day}`
            : `upgrading to L${target}`)
        : (level > 0 ? `Citadel L${level} built` : "no citadel");

      // --- Per-tier ladder: show each L1..L6 with cost/status ---
      const ladderCells = CITADEL_TIERS.map((t, i) => {
        const tierNum = i + 1;
        let state = "future";
        if (tierNum <= level) state = "done";
        else if (tierNum === target && inProgress) state = "building";
        else if (tierNum === level + 1) state = "next";
        return `<span class="citadel-tier ${state}" title="L${tierNum}: ${t.cr.toLocaleString()}cr + ${t.col.toLocaleString()} col, ${t.days}d — ${esc(t.perk)}">L${tierNum}</span>`;
      }).join("");

      // --- Next-tier cost hint (if still upgradable and not already building) ---
      let nextTierHint = "";
      if (level < 6 && !inProgress) {
        const next = CITADEL_TIERS[level];
        nextTierHint = `<div class="planet-next-tier" title="cost + build time for next citadel level">
          <span class="nt-label">Next L${level + 1}:</span>
          <span class="nt-cost">${fmt(next.cr)}cr + ${fmt(next.col)} col · ${next.days}d</span>
          <span class="nt-perk">${esc(next.perk)}</span>
        </div>`;
      } else if (inProgress && pl.citadel_complete_day != null) {
        const daysLeft = Math.max(0, pl.citadel_complete_day - (state.day || 1));
        nextTierHint = `<div class="planet-next-tier building-hint" title="citadel construction in progress">
          <span class="nt-label">Building L${target}:</span>
          <span class="nt-cost">ETA day ${pl.citadel_complete_day}${daysLeft > 0 ? ` (${daysLeft}d left)` : " (completing)"}</span>
        </div>`;
      }

      // --- Colonist pools: ALL four (fuel_ore, organics, equipment, idle) always shown ---
      const assignedPools = ["fuel_ore", "organics", "equipment"].map((c) => {
        const n = col[c] || 0;
        const pct = totalCol > 0 ? Math.round((n / totalCol) * 100) : 0;
        return `<span class="planet-pool" title="${n} colonists producing ${c} (${pct}% of total)">
          <i class="cargo-dot ${c}"></i>${commAbbrev[c]} ${fmt(n)}
        </span>`;
      }).join("");

      // --- Stockpile: ALL three commodities always shown, zeros muted ---
      const stockCells = ["fuel_ore", "organics", "equipment"].map((c) => {
        const n = stock[c] || 0;
        const cls = n > 0 ? "planet-stock" : "planet-stock zero";
        return `<span class="${cls}" title="${n} ${c} stockpiled on planet"><i class="cargo-dot ${c}"></i>${commAbbrev[c]} ${fmt(n)}</span>`;
      }).join("");

      // --- Defense / economy line — always rendered with all three stats ---
      const defenseRow = `<div class="planet-defense">
        <span class="planet-def" title="planet defensive fighters">✈ ${fmt(pl.fighters || 0)}</span>
        <span class="planet-def" title="planet shields">◈ ${fmt(pl.shields || 0)}</span>
        <span class="planet-def" title="planet treasury (credits held by planet, usable for citadel builds)">¢ ${fmt(pl.treasury || 0)}</span>
        <span class="planet-def" title="total population (productive + idle)">👥 ${fmt(totalCol)}</span>
      </div>`;

      const classTag = pl.class ? `<span class="planet-class" title="class ${pl.class}">${esc(pl.class)}</span>` : "";

      return `
        <li class="planet-row">
          <div class="planet-header">
            <span class="planet-name" title="${esc(pl.name)}">${esc(pl.name)}</span>
            ${classTag}
            <span class="planet-sector" title="sector ${pl.sector_id}">s${pl.sector_id}</span>
            <span class="${citadelCls}" title="${esc(citadelTitle)}">${citadelLabel}</span>
          </div>
          <div class="citadel-ladder" title="Citadel tiers — done / building / next / future">
            ${ladderCells}
          </div>
          ${nextTierHint}
          <div class="planet-pools">
            <span class="planet-idle" title="idle colonists waiting to be assigned to production or citadel build">💤 ${fmt(idle)} idle</span>
            ${assignedPools}
          </div>
          <div class="planet-stocks" title="commodity stockpile produced on-planet (available for citadel build, planet trade, or ferry)">${stockCells}</div>
          ${defenseRow}
        </li>
      `;
    }).join("");

    const summary = `Planets (${owned.length}) · ${totalCitadels} Cit · ${fmt(totalIdle)} idle`;
    return `
      <details class="commander-planets" open>
        <summary>${summary}</summary>
        <ul class="planet-list">${rows}</ul>
      </details>
    `;
  }

  function renderTradesBlock(p) {
    const trades = p.recent_trades || [];
    if (!trades.length) return "";
    const commAbbrev = { fuel_ore: "FO", organics: "Org", equipment: "Eq", colonists: "Col" };
    const rows = trades.slice(-3).reverse().map((t) => {
      const side = t.side === "sell" ? "▲" : "▼";
      const comm = commAbbrev[t.commodity] || t.commodity;
      const prof = t.realized_profit;
      let profTag = "";
      if (t.side === "sell" && prof != null) {
        const cls = prof >= 0 ? "positive" : "negative";
        const sign = prof >= 0 ? "+" : "";
        profTag = `<span class="trade-profit ${cls}">${sign}${fmt(prof)}</span>`;
      }
      const dayTick = `<span class="trade-when">d${t.day}·t${t.tick}</span>`;
      const sideCls = t.side === "sell" ? "sell" : "buy";
      const body = `<span class="trade-side ${sideCls}">${side} ${t.qty}${comm}</span><span class="trade-price">@${t.unit}</span>`;
      const sector = t.sector_id ? `<span class="trade-sector">s${t.sector_id}</span>` : "";
      return `<li class="trade-row">${dayTick}${sector}${body}${profTag}</li>`;
    }).join("");
    return `
      <details class="recent-trades">
        <summary>Recent trades (${trades.length})</summary>
        <ul class="trade-list">${rows}</ul>
      </details>
    `;
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
      renderDrawer();
      updateFollowCamera();
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
      if (e.key === "Escape" || e.code === "Escape") {
        const layout = document.getElementById("layout");
        if (layout && layout.classList.contains("fullscreen-map")) {
          e.preventDefault();
          toggleFullscreenMap(false);
          return;
        }
        if (detailDrawer && !detailDrawer.hidden && state.drawer.kind) {
          e.preventDefault();
          setFollow(null);
          closeDrawer();
          return;
        }
        if (gameOverModal && !gameOverModal.hidden) {
          e.preventDefault();
          gameOverModal.hidden = true;
          return;
        }
        const toast = document.getElementById("shortcutsToast");
        if (toast && !toast.hidden) {
          e.preventDefault();
          toast.hidden = true;
        }
        return;
      }
      if (e.key === "f" || e.key === "F") {
        e.preventDefault();
        toggleFullscreenMap();
        return;
      }
      // Map zoom shortcuts
      if (e.key === "+" || e.key === "=") {
        e.preventDefault();
        zoomBy(0.8);
        return;
      }
      if (e.key === "-" || e.key === "_") {
        e.preventDefault();
        zoomBy(1.25);
        return;
      }
      if (e.key === "0") {
        e.preventDefault();
        fitGalaxy();
        return;
      }
      if (e.key === "m" || e.key === "M") {
        e.preventDefault();
        setMiniMapVisible(!miniMapVisible);
        return;
      }
      if (
        e.key === "?" ||
        e.key === "/" ||
        (e.shiftKey && e.key === "/") ||
        (e.shiftKey && e.code === "Slash") ||
        (e.code === "Slash" && e.shiftKey) ||
        e.code === "Slash"
      ) {
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
        e.preventDefault();
        openDrawer("player", p.id);
        setFollow(p.id);
        const card = document.querySelector(`.player-card[data-pid="${p.id}"]`);
        if (card) {
          card.classList.add("flash");
          setTimeout(() => card.classList.remove("flash"), 700);
        }
      }
    });
  }

  // ------------- History + sparklines (Phase 4) -------------

  const SPARK_METRICS = [
    { key: "credits",    label: "cr",   color: "var(--accent)" },
    { key: "net_worth",  label: "net",  color: "#ffd166" },
    { key: "fighters",   label: "fgt",  color: "#ff6e6e" },
  ];

  async function fetchHistory() {
    try {
      const r = await fetch("/history?limit=120");
      if (!r.ok) return;
      const data = await r.json();
      if (data && data.samples) {
        state.history.clear();
        for (const [pid, samples] of Object.entries(data.samples)) {
          state.history.set(pid, samples);
        }
        // Re-render affected surfaces so sparklines update in place.
        renderPlayers();
        renderDrawer();
      }
    } catch (e) {
      // Non-fatal; just try again on the next tick.
    }
  }

  function sparklineSvg(series, color, width = 72, height = 18) {
    if (!series || series.length < 2) {
      return `<svg class="spark" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><text x="4" y="12" fill="var(--text-faint)" font-size="9">—</text></svg>`;
    }
    const lo = Math.min(...series);
    const hi = Math.max(...series);
    const span = (hi - lo) || 1;
    const step = width / (series.length - 1);
    const pts = series.map((v, i) => {
      const x = (i * step).toFixed(1);
      const y = (height - 1 - ((v - lo) / span) * (height - 2)).toFixed(1);
      return `${x},${y}`;
    }).join(" ");
    const last = series[series.length - 1];
    const dx = (width - 1).toFixed(1);
    const dy = (height - 1 - ((last - lo) / span) * (height - 2)).toFixed(1);
    return `<svg class="spark" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <polyline fill="none" stroke="${color}" stroke-width="1.2" points="${pts}" />
      <circle cx="${dx}" cy="${dy}" r="1.6" fill="${color}" />
    </svg>`;
  }

  function renderSparklineRow(pid) {
    const samples = state.history.get(pid);
    if (!samples || samples.length < 2) {
      return `<div class="spark-row spark-row-empty" title="history will appear after the first round">
        <span class="spark-label muted">history</span>
      </div>`;
    }
    const parts = SPARK_METRICS.map((m) => {
      const series = samples.map((s) => Number(s[m.key] || 0));
      return `<span class="spark-cell" title="${m.label}: ${fmt(series[0])} → ${fmt(series[series.length - 1])}">
        <span class="spark-label" style="color:${m.color}">${m.label}</span>
        ${sparklineSvg(series, m.color)}
      </span>`;
    }).join("");
    return `<div class="spark-row">${parts}</div>`;
  }

  // ------------- Detail drawer + follow camera (Phase 3) -------------

  function openDrawer(kind, id) {
    state.drawer = { kind, id };
    if (kind === "player") state.selectedPlayerId = id;
    else if (kind === "sector") state.selectedSectorId = id;
    if (detailDrawer) detailDrawer.hidden = false;
    renderDrawer();
    applyFocusHighlight();
  }

  function closeDrawer() {
    state.drawer = { kind: null, id: null };
    state.selectedSectorId = null;
    if (detailDrawer) detailDrawer.hidden = true;
    applyFocusHighlight();
  }

  function setFollow(playerId) {
    state.followPlayerId = playerId;
    updateFollowCamera(true);
    if (drawerFollowBtn) drawerFollowBtn.classList.toggle("active", state.followPlayerId != null);
  }

  function toggleFollow() {
    if (state.drawer.kind !== "player") return;
    setFollow(state.followPlayerId === state.drawer.id ? null : state.drawer.id);
  }

  // Recenter the viewBox on the followed player. Only pans when the player
  // is outside the visible area (or a margin), so gentle moves don't jitter.
  let _lastFollowSector = null;
  function updateFollowCamera(forceCenter) {
    if (!state.followPlayerId) { _lastFollowSector = null; return; }
    const p = state.players.get(state.followPlayerId);
    if (!p || !p.alive) return;
    const s = state.sectors.get(p.sector_id);
    if (!s) return;
    // If forced or the followed player changed sector, recenter.
    const changedSector = _lastFollowSector !== p.sector_id;
    if (!forceCenter && !changedSector) {
      // Also recenter if the player drifted outside a safety margin of the view.
      const margin = 0.15;
      const minX = viewBoxState.x + viewBoxState.w * margin;
      const maxX = viewBoxState.x + viewBoxState.w * (1 - margin);
      const minY = viewBoxState.y + viewBoxState.h * margin;
      const maxY = viewBoxState.y + viewBoxState.h * (1 - margin);
      if (s.x >= minX && s.x <= maxX && s.y >= minY && s.y <= maxY) return;
    }
    _lastFollowSector = p.sector_id;
    viewBoxState.x = s.x - viewBoxState.w / 2;
    viewBoxState.y = s.y - viewBoxState.h / 2;
    updateViewBox();
  }

  function renderDrawer() {
    if (!drawerBody) return;
    const { kind, id } = state.drawer;
    if (!kind) {
      if (detailDrawer) detailDrawer.hidden = true;
      if (drawerFollowBtn) drawerFollowBtn.style.display = "none";
      return;
    }
    if (detailDrawer) detailDrawer.hidden = false;
    if (kind === "player") {
      if (drawerFollowBtn) {
        drawerFollowBtn.style.display = "";
        drawerFollowBtn.classList.toggle("active", state.followPlayerId === id);
      }
      renderPlayerDrawer(id);
    } else if (kind === "sector") {
      if (drawerFollowBtn) drawerFollowBtn.style.display = "none";
      renderSectorDrawer(id);
    }
  }

  function renderPlayerDrawer(playerId) {
    const p = state.players.get(playerId);
    if (!p) { drawerBody.innerHTML = "<em>Player not found.</em>"; return; }
    if (drawerTitle) {
      const rk = p.rank ? ` · ${p.rank}` : "";
      drawerTitle.textContent = `${p.name}${rk}`;
      drawerTitle.style.color = p.color || "";
    }
    const fo = p.cargo?.fuel_ore || 0;
    const org = p.cargo?.organics || 0;
    const eq = p.cargo?.equipment || 0;
    const photon = p.photon_torpedoes || 0;
    const probes = p.probes || 0;
    const mines = p.atomic_mines || 0;
    const deaths = p.deaths || 0;
    const sec = state.sectors.get(p.sector_id);
    const secPort = sec && sec.port ? sec.port : "—";
    const allianceInfo = (() => {
      if (!p.alliance_id) return "none";
      const a = state.alliances ? state.alliances.get(p.alliance_id) : null;
      if (!a) return `pending (${esc(p.alliance_id)})`;
      return `${a.active ? "NAP" : "proposed"} with ${esc(a.partner_name || p.alliance_id)}`;
    })();

    drawerBody.innerHTML = `
      <div class="drawer-section">
        <h3>Vitals</h3>
        <div class="drawer-stat-grid">
          <span class="k">Kind</span><span class="v">${esc(p.kind || "?")}</span>
          <span class="k">Ship</span><span class="v">${esc(p.ship || "?")}</span>
          <span class="k">Alive</span><span class="v">${p.alive ? "yes" : "KIA"}</span>
          <span class="k">Sector</span><span class="v">${p.sector_id || "—"}${secPort !== "—" ? ` (Port ${esc(secPort)})` : ""}</span>
          <span class="k">Credits</span><span class="v">${fmt(p.credits || 0)}</span>
          <span class="k">Net Worth</span><span class="v">${fmt(p.net_worth || p.credits || 0)}</span>
          <span class="k">Experience</span><span class="v">${fmt(p.experience || 0)}</span>
          <span class="k">Alignment</span><span class="v">${p.alignment != null ? p.alignment : "—"}</span>
          <span class="k">Turns</span><span class="v">${fmt(p.turns || 0)}/${fmt(p.turns_max || p.turns || 0)}</span>
          <span class="k">Deaths</span><span class="v">${deaths}</span>
        </div>
        ${renderSparklineRow(p.id)}
      </div>
      <div class="drawer-section">
        <h3>Ship loadout</h3>
        <div class="drawer-stat-grid">
          <span class="k">Fighters</span><span class="v">${fmt(p.fighters || 0)}</span>
          <span class="k">Shields</span><span class="v">${fmt(p.shields || 0)}</span>
          <span class="k">Holds</span><span class="v">${fmt(p.holds || 0)}</span>
          <span class="k">Fuel Ore</span><span class="v">${fmt(fo)}</span>
          <span class="k">Organics</span><span class="v">${fmt(org)}</span>
          <span class="k">Equipment</span><span class="v">${fmt(eq)}</span>
          <span class="k">Photon</span><span class="v">${fmt(photon)}</span>
          <span class="k">Probes</span><span class="v">${fmt(probes)}</span>
          <span class="k">Atomic mines</span><span class="v">${fmt(mines)}</span>
        </div>
      </div>
      <div class="drawer-section">
        <h3>Diplomacy</h3>
        <div>Corporation: ${p.corp_ticker ? `<strong style="color:${p.color}">${esc(p.corp_ticker)}</strong>` : "none"}</div>
        <div>Alliance: ${allianceInfo}</div>
      </div>
      <div class="drawer-section">
        <h3>Press <kbd>◎ Follow</kbd> above</h3>
        <div>Camera will lock on ${esc(p.name)} and pan with every warp.</div>
      </div>
    `;
  }

  function renderSectorDrawer(sectorId) {
    const s = state.sectors.get(sectorId);
    if (!s) { drawerBody.innerHTML = "<em>Sector not found.</em>"; return; }
    if (drawerTitle) {
      drawerTitle.textContent = `Sector ${s.id}${s.id === 1 ? " · StarDock" : ""}`;
      drawerTitle.style.color = "";
    }
    const planetsHere = Array.from(state.planets.values()).filter((pl) => pl.sector_id === s.id);
    const occupants = [];
    for (const p of state.players.values()) {
      if (p.sector_id === s.id) {
        const rk = p.rank ? ` [${p.rank}]` : "";
        const aliveMark = p.alive ? "" : " †";
        occupants.push(`<li><span style="color:${p.color || "inherit"}">${esc(p.name)}</span>${rk}${aliveMark} (${esc(p.ship || "?")})</li>`);
      }
    }

    // Warps OUT — sectors this one leads to. Keep two-way/one-way indicators.
    const warpsOut = (s.warps_dir && Array.isArray(s.warps_dir))
      ? s.warps_dir.map((w) => ({ to: w.to, twoWay: !!w.two_way }))
      : (s.warps || []).map((w) => ({ to: w, twoWay: true }));
    // Warps IN — sectors that reach THIS one but it doesn't reach back. Only
    // one-way inbound is interesting; bidirectional already shown in Out.
    const reverseIds = state.reverseWarps.get(s.id) || new Set();
    const outSet = new Set(warpsOut.map((w) => w.to));
    const warpsInOnly = [];
    for (const rid of reverseIds) {
      if (!outSet.has(rid)) warpsInOnly.push(rid);
    }

    // Per-neighbor 1-line summary: tells you at a glance whether warping there
    // lands you on a port, planet, or a ship. Makes "reading the graph" fast.
    const neighborSummary = (nid) => {
      const ns = state.sectors.get(nid);
      const bits = [];
      if (!ns) return "<em>unknown</em>";
      if (ns.id === 1) bits.push(`<span class="pill pill-stardock">StarDock</span>`);
      else if (ns.is_fedspace) bits.push(`<span class="pill pill-fed">FedSpace</span>`);
      if (ns.port && ns.port !== "STARDOCK") bits.push(`<span class="pill pill-port">${esc(ns.port)}</span>`);
      if (ns.has_planets) bits.push(`<span class="pill pill-planet">planet</span>`);
      const shipsHere = [];
      for (const p of state.players.values()) {
        if (p.sector_id === nid && p.alive) {
          shipsHere.push(`<span style="color:${p.color || "inherit"}">${esc(p.name)}</span>`);
        }
      }
      if (shipsHere.length) bits.push(shipsHere.join(", "));
      return bits.length ? bits.join(" ") : `<span class="muted">empty</span>`;
    };

    const warpOutHtml = warpsOut.length
      ? `<ul class="drawer-list warp-list">${warpsOut.map((w) => {
          const arrow = w.twoWay ? "↔" : "↛";
          return `<li>${arrow} <a class="sector-link" data-sector="${w.to}">sector ${w.to}</a> · ${neighborSummary(w.to)}</li>`;
        }).join("")}</ul>`
      : "<em>none</em>";
    const warpInHtml = warpsInOnly.length
      ? `<ul class="drawer-list warp-list">${warpsInOnly.map((nid) =>
          `<li>↞ <a class="sector-link" data-sector="${nid}">sector ${nid}</a> · ${neighborSummary(nid)}</li>`
        ).join("")}</ul>`
      : "";

    const portLine = s.port && s.port !== "STARDOCK"
      ? `<div>Class ${esc(s.port)}${s.port_name ? ` · ${esc(s.port_name)}` : ""}</div>`
      : (s.id === 1 ? "<div>StarDock — Federation HQ</div>" : "<em>No port.</em>");
    const planetHtml = planetsHere.length
      ? `<ul class="drawer-list">${planetsHere.map((pl) => {
          const owner = pl.owner_id ? state.players.get(pl.owner_id) : null;
          const ownerLabel = owner ? `<span style="color:${owner.color}">${esc(owner.name)}</span>` : (pl.owner_id ? esc(pl.owner_id) : "unowned");
          const cit = pl.citadel_level
            ? `Citadel L${pl.citadel_level}`
            : (pl.citadel_target ? `Citadel L${pl.citadel_target} (D${pl.citadel_complete_day})` : "—");
          return `<li><strong>${esc(pl.name || pl.id)}</strong> [${esc(pl.class || pl.planet_class || "?")}] · ${ownerLabel}<br/><span class="muted">${cit}</span></li>`;
        }).join("")}</ul>`
      : "<em>No planets.</em>";
    drawerBody.innerHTML = `
      <div class="drawer-section">
        <h3>Port</h3>
        ${portLine}
      </div>
      <div class="drawer-section">
        <h3>Planets</h3>
        ${planetHtml}
      </div>
      <div class="drawer-section">
        <h3>Warps out (${warpsOut.length})</h3>
        ${warpOutHtml}
      </div>
      ${warpsInOnly.length ? `
      <div class="drawer-section">
        <h3>Warps in — one-way only (${warpsInOnly.length})</h3>
        ${warpInHtml}
      </div>` : ""}
      <div class="drawer-section">
        <h3>Ships here (${occupants.length})</h3>
        ${occupants.length ? `<ul class="drawer-list">${occupants.join("")}</ul>` : "<em>Empty.</em>"}
      </div>
    `;
  }

  function initDrawer() {
    if (!detailDrawer) return;
    detailDrawer.addEventListener("click", (e) => {
      // Walk-the-graph: clicking a sector ID anywhere in the drawer
      // recenters the drawer (and map focus) on that sector.
      const link = e.target.closest(".sector-link[data-sector]");
      if (link) {
        e.preventDefault();
        const sid = Number(link.getAttribute("data-sector"));
        if (!Number.isNaN(sid) && state.sectors.has(sid)) {
          openDrawer("sector", sid);
          // Also pan the map to show the newly-focused sector if it's offscreen.
          const ns = state.sectors.get(sid);
          if (ns) {
            const pad = viewBoxState.w * 0.2;
            const onScreen = ns.x >= viewBoxState.x + pad
              && ns.x <= viewBoxState.x + viewBoxState.w - pad
              && ns.y >= viewBoxState.y + pad
              && ns.y <= viewBoxState.y + viewBoxState.h - pad;
            if (!onScreen) {
              viewBoxState.x = ns.x - viewBoxState.w / 2;
              viewBoxState.y = ns.y - viewBoxState.h / 2;
              updateViewBox();
            }
          }
        }
        return;
      }
      const btn = e.target.closest("[data-drawer-action]");
      if (!btn) return;
      const action = btn.dataset.drawerAction;
      if (action === "close") {
        setFollow(null);
        closeDrawer();
      } else if (action === "toggle-follow") {
        toggleFollow();
      }
    });
    // Make player cards open the drawer on click. We use delegation off the
    // players panel so we don't have to re-wire after every renderPlayers().
    const playersPanelEl = document.getElementById("panelPlayers");
    if (playersPanelEl) {
      playersPanelEl.addEventListener("click", (e) => {
        // Summary clicks are reserved for native collapse/expand — don't
        // also fire the drawer. Clicking anywhere in the body (stats,
        // cargo bar, planets block, etc.) still opens the drawer and
        // follows the commander, keeping the old shortcut.
        if (e.target.closest("summary.player-card-summary")) return;
        const card = e.target.closest(".player-card[data-pid]");
        if (!card) return;
        const pid = card.dataset.pid;
        if (!pid) return;
        openDrawer("player", pid);
        setFollow(pid);
      });
    }
  }

  function initLayout() {
    const cfg = loadLayout();
    applyLayout(cfg);
    if (cfg.fullscreenMap) toggleFullscreenMap(true);
    initResizers();
    initCollapseButtons();
    initShortcuts();
    initMapControls();
    initDrawer();
    initHelpButton();
  }

  function initHelpButton() {
    const btn = document.getElementById("helpBtn");
    if (!btn) return;
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      toggleShortcutsToast();
    });
  }

  // Kick off
  initLayout();
  setupScrubber();
  connect();
  render();
  // Phase 4: prime the history buffer + poll for updates.
  fetchHistory();
  setInterval(fetchHistory, 4000);
})();
