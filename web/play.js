/* TW2K-AI cockpit (Phase H1).
 *
 * Controls one HUMAN slot in a live match. Pulls state from:
 *   * GET /api/match/humans        - which slots can I fly?
 *   * GET /api/human/observation   - current obs for this slot
 *   * GET /state                   - match-level status/day/tick
 *   * WS  /ws                      - live event stream
 *
 * Submits actions via POST /api/human/action. Everything the
 * autonomous LLM sees is visible — the "Copilot's view" panel
 * dumps the raw Observation JSON so the player can learn exactly
 * what an AI would be reasoning over.
 *
 * No framework; matches the existing spectator app.js pattern.
 */

(function () {
  "use strict";

  // ---------------- URL param + bound player id ----------------

  const urlParams = new URLSearchParams(window.location.search);
  let playerId = (urlParams.get("player") || "").toUpperCase();

  // ---------------- DOM refs ----------------
  const $ = (id) => document.getElementById(id);
  const qs = (sel) => document.querySelector(sel);

  const els = {
    cockpit: $("cockpit"),
    chooser: $("slotChooser"),
    chooserList: $("slotChooserList"),
    noHuman: $("noHuman"),
    statusDot: $("statusDot"),
    statusLabel: $("statusLabel"),
    dayLabel: $("dayLabel"),
    tickLabel: $("tickLabel"),
    turn: $("turnIndicator"),
    cockpitSub: $("cockpitSub"),
    sectorCurrent: $("sectorCurrent"),
    sectorPort: $("sectorPort"),
    sectorOccupants: $("sectorOccupants"),
    sectorPlanets: $("sectorPlanets"),
    sectorSummary: $("sectorSummary"),
    adjacentList: $("adjacentList"),
    knownWarps: $("knownWarps"),
    knownWarpsCount: $("knownWarpsCount"),
    vCredits: $("vCredits"),
    vNetWorth: $("vNetWorth"),
    vTurns: $("vTurns"),
    vDay: $("vDay"),
    vAlign: $("vAlign"),
    vRank: $("vRank"),
    commanderBadge: $("commanderBadge"),
    cargoList: $("cargoList"),
    cargoFree: $("cargoFree"),
    failuresList: $("failuresList"),
    failuresMuted: $("failuresMuted"),
    knownPorts: $("knownPorts"),
    actionForm: $("actionForm"),
    actionTitle: $("actionTitle"),
    actionFields: $("actionFields"),
    actionHint: $("actionHint"),
    actionSubmit: $("actionSubmitBtn"),
    actionCancel: $("actionCancelBtn"),
    actionBtns: document.querySelectorAll("[data-action-kind]"),
    submitStatus: $("submitStatus"),
    rawObs: $("rawObservation"),
    events: $("cockpitEvents"),
    shortcutsToast: $("shortcutsToast"),
  };

  // ---------------- Runtime state ----------------
  const state = {
    observation: null,
    matchStatus: "unknown",
    day: null,
    tick: null,
    currentAction: null,
    submitting: false,
    myTurn: false,
    eventHistory: [],   // last ~50 events for this page
    wsConnected: false,
  };

  const EVENT_MAX = 80;

  // ---------------- Helpers ----------------
  function fmtCr(n) {
    if (n === null || n === undefined) return "—";
    return (+n).toLocaleString() + " cr";
  }
  function classifyActor(ev) {
    // Use the new Phase-H0 actor_kind where present; otherwise fall
    // back to "engine" / "system".
    if (ev.actor_kind) return ev.actor_kind;
    if (!ev.actor_id) return "engine";
    return "unknown";
  }
  function setStatusDot(label, color) {
    els.statusLabel.textContent = label;
    els.statusDot.style.background = color;
  }
  function setTurnIndicator(mode, text) {
    els.turn.className = "pill turn-indicator " + mode;
    els.turn.textContent = text;
  }

  // ---------------- Slot resolution ----------------
  async function resolveSlot() {
    let data;
    try {
      const r = await fetch("/api/match/humans");
      data = await r.json();
    } catch (err) {
      setStatusDot("disconnected", "#ff5d6e");
      return;
    }
    state.matchStatus = data.status || "unknown";
    state.day = data.day;
    state.tick = data.tick;
    if (state.day !== undefined) els.dayLabel.textContent = `Day ${state.day}`;
    if (state.tick !== undefined) els.tickLabel.textContent = `Tick ${state.tick}`;

    const humans = data.humans || [];
    if (humans.length === 0) {
      els.noHuman.hidden = false;
      els.cockpit.hidden = true;
      return;
    }

    if (!playerId) {
      if (humans.length === 1) {
        playerId = humans[0].player_id;
      } else {
        renderChooser(humans);
        return;
      }
    }

    const selected = humans.find((h) => h.player_id === playerId);
    if (!selected) {
      renderChooser(humans);
      return;
    }

    els.cockpit.hidden = false;
    els.chooser.hidden = true;
    els.noHuman.hidden = true;
    els.commanderBadge.textContent = `${selected.player_id} · ${selected.name}`;
    els.cockpitSub.textContent = `Flying ${selected.name} (${selected.player_id})`;
    // Seed myTurn from the server's authoritative flag — any
    // HUMAN_TURN_START event that fired before the WS connected is
    // otherwise invisible to the page. Poll the flag once here; the
    // WS handler keeps it fresh afterwards.
    if (selected.awaiting_input) {
      state.myTurn = true;
    }
    await refreshObservation();
    setStatusDot("ready", "#79ffb0");
  }

  function renderChooser(humans) {
    els.chooser.hidden = false;
    els.cockpit.hidden = true;
    els.noHuman.hidden = true;
    els.chooserList.innerHTML = "";
    humans.forEach((h) => {
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = `/play?player=${encodeURIComponent(h.player_id)}`;
      a.innerHTML = `<strong>${h.player_id}</strong> · ${h.name} <span class="muted">(sector ${h.sector_id}, turns ${h.turns_today}/${h.turns_per_day})</span>`;
      li.appendChild(a);
      els.chooserList.appendChild(li);
    });
  }

  // ---------------- Observation refresh ----------------
  async function refreshObservation() {
    if (!playerId) return;
    try {
      const r = await fetch(
        `/api/human/observation?player_id=${encodeURIComponent(playerId)}`
      );
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        els.submitStatus.className = "submit-status err";
        els.submitStatus.textContent = `observation error: ${r.status} ${body.detail || ""}`;
        return;
      }
      const obs = await r.json();
      state.observation = obs;
      renderObservation(obs);
      // H6.4 — keep the economy panel in sync with the observation.
      // `refreshEconomy` is cheap (two JSON fetches) and the dashboard
      // only materialises inside a collapsed <details>, so running it
      // on every observation refresh is fine.
      refreshEconomy();
    } catch (err) {
      console.error("refreshObservation failed", err);
    }
  }

  // ---------------- H6.4 economy dashboards ----------------
  const ecoEls = {
    panel: document.getElementById("economyPanel"),
    badge: document.getElementById("economyBadge"),
    routes: document.getElementById("economyRoutes"),
    heatmapBody: document.getElementById("economyHeatmapBody"),
  };

  async function refreshEconomy() {
    if (!playerId || !ecoEls.panel) return;
    try {
      const [pricesRes, routesRes] = await Promise.all([
        fetch(`/api/economy/prices?player_id=${encodeURIComponent(playerId)}`),
        fetch(
          `/api/economy/routes?player_id=${encodeURIComponent(playerId)}&max_routes=5`
        ),
      ]);
      const prices = pricesRes.ok ? await pricesRes.json() : null;
      const routes = routesRes.ok ? await routesRes.json() : null;
      renderEconomy(prices, routes);
    } catch (err) {
      /* non-fatal — panel just stays stale */
    }
  }

  function renderEconomy(prices, routes) {
    if (!ecoEls.panel) return;
    const portCount = prices && Array.isArray(prices.ports) ? prices.ports.length : 0;
    const routeList = (routes && Array.isArray(routes.routes)) ? routes.routes : [];
    if (ecoEls.badge) {
      if (portCount > 0) {
        ecoEls.badge.hidden = false;
        ecoEls.badge.textContent = `${portCount} port${portCount === 1 ? "" : "s"} · ${routeList.length} route${routeList.length === 1 ? "" : "s"}`;
      } else {
        ecoEls.badge.hidden = true;
      }
    }

    // Routes
    if (ecoEls.routes) {
      ecoEls.routes.innerHTML = "";
      if (routeList.length === 0) {
        const li = document.createElement("li");
        li.className = "economy-empty";
        li.textContent = portCount < 2
          ? "Scout a second port to unlock route suggestions."
          : "No profitable round-trips between your known ports yet.";
        ecoEls.routes.appendChild(li);
      } else {
        routeList.forEach((r, i) => {
          const li = document.createElement("li");
          const rank = document.createElement("span");
          rank.className = "eco-rank";
          rank.textContent = `#${i + 1}`;
          const route = document.createElement("span");
          route.className = "eco-route";
          route.textContent = `s${r.from_sector} → s${r.to_sector} · ${r.commodity}`;
          const ppt = document.createElement("span");
          ppt.className = "eco-ppt";
          ppt.textContent = `+${Math.round(r.profit_per_turn)}/turn`;
          const detail = document.createElement("span");
          detail.className = "eco-route-detail";
          detail.textContent =
            `buy ${r.buy_price}c · sell ${r.sell_price}c · ` +
            `${r.qty} holds · ${r.turns} turns · +${r.profit_per_trip.toLocaleString()} / trip`;
          li.appendChild(rank);
          li.appendChild(route);
          li.appendChild(ppt);
          li.appendChild(detail);
          li.title = `Click to plot course to sector ${r.from_sector}`;
          li.addEventListener("click", () => {
            openActionForm("plot_course", { to: r.from_sector });
          });
          ecoEls.routes.appendChild(li);
        });
      }
    }

    // Heatmap
    if (ecoEls.heatmapBody) {
      ecoEls.heatmapBody.innerHTML = "";
      const commodities = ["fuel_ore", "organics", "equipment"];
      const ports = prices && Array.isArray(prices.ports) ? prices.ports : [];
      ports.forEach((p) => {
        const tr = document.createElement("tr");
        if (typeof p.age_days === "number" && p.age_days > 3) {
          tr.className = "eco-stale";
          tr.title = `Last scouted ${p.age_days}d ago — data may be stale.`;
        }
        const td0 = document.createElement("td");
        td0.textContent = `s${p.sector_id}`;
        const td1 = document.createElement("td");
        td1.textContent = p.class || "?";
        tr.appendChild(td0);
        tr.appendChild(td1);
        commodities.forEach((c) => {
          const td = document.createElement("td");
          const cell = p.prices ? p.prices[c] : null;
          if (!cell) {
            td.innerHTML = `<span class="eco-cell eco-none">—</span>`;
          } else {
            const cls = cell.side === "sell" ? "eco-sell" : "eco-buy";
            const pctStr = Number.isFinite(cell.pct) ? `${Math.round(cell.pct * 100)}%` : "";
            td.innerHTML =
              `<span class="eco-cell ${cls}" title="${cell.side === "sell" ? "Port sells" : "Port buys"} · stock ${pctStr}">` +
              `${cell.price}c</span>`;
          }
          tr.appendChild(td);
        });
        ecoEls.heatmapBody.appendChild(tr);
      });
    }
  }

  window.__tw2kEconomy = { refresh: refreshEconomy, render: renderEconomy };

  function renderObservation(obs) {
    // Header pills
    els.dayLabel.textContent = `Day ${obs.day}`;
    els.tickLabel.textContent = `Tick ${obs.tick}`;

    // Sector detail
    const sec = obs.sector || {};
    els.sectorCurrent.textContent = sec.id ?? "—";
    els.sectorPort.textContent = sec.port
      ? `${sec.port.class || sec.port.code || "?"}${sec.port.name ? " · " + sec.port.name : ""}`
      : "none";
    const occ = (sec.occupants || []).filter((x) => x !== obs.self_id);
    els.sectorOccupants.textContent =
      occ.length === 0 ? "you alone" : `${occ.length} other(s): ${occ.join(", ")}`;
    els.sectorPlanets.textContent = (sec.planet_ids || []).length
      ? (sec.planet_ids || []).join(", ")
      : "none";
    els.sectorSummary.textContent = `s${sec.id ?? "?"} · ${obs.self_name}`;

    // Adjacent warps
    els.adjacentList.innerHTML = "";
    (obs.adjacent || []).forEach((adj) => {
      const li = document.createElement("li");
      li.dataset.sid = adj.id;
      let label = `→ ${adj.id}`;
      if (adj.port) {
        const cls = adj.port.class || adj.port.code || "?";
        label += `<span class="adj-port">${cls}</span>`;
      }
      if (adj.one_way) label += `<span class="adj-oneway">⊘ 1-way</span>`;
      li.innerHTML = label;
      li.title = `Click to warp to ${adj.id}`;
      li.addEventListener("click", () => openActionForm("warp", { to: adj.id }));
      els.adjacentList.appendChild(li);
    });

    // Known warps graph (last ~30)
    els.knownWarps.innerHTML = "";
    const kw = obs.known_warps || {};
    const entries = Object.entries(kw).sort((a, b) => (+a[0]) - (+b[0]));
    els.knownWarpsCount.textContent = `(${entries.length} sectors)`;
    entries.slice(-30).forEach(([sid, warps]) => {
      const d = document.createElement("div");
      const cls = +sid === sec.id ? "warp-cur" : "";
      d.innerHTML = `<span class="${cls}">s${sid}</span> → ${warps.join(", ")}`;
      els.knownWarps.appendChild(d);
    });

    // Vitals
    els.vCredits.textContent = fmtCr(obs.credits);
    els.vNetWorth.textContent = fmtCr(obs.net_worth);
    els.vTurns.textContent = `${obs.turns_per_day - obs.turns_remaining}/${obs.turns_per_day}`;
    els.vDay.textContent = `${obs.day} / ${obs.max_days}`;
    els.vAlign.textContent = `${obs.alignment} ${obs.alignment_label || ""}`.trim();
    els.vRank.textContent = obs.rank || "Civilian";

    // Cargo
    els.cargoList.innerHTML = "";
    const ship = obs.ship || {};
    els.cargoFree.textContent = `(${ship.cargo_used || 0}/${ship.holds || 0} used, ${ship.cargo_free || 0} free)`;
    Object.entries(ship.cargo || {}).forEach(([commodity, qty]) => {
      if (!qty) return;
      const avg = (ship.cargo_cost_avg || ship.cargo_cost || {})[commodity];
      const li = document.createElement("li");
      li.innerHTML = `<span>${commodity}</span><span>${qty}${avg ? ` @ ${Math.round(avg)}` : ""}</span>`;
      els.cargoList.appendChild(li);
    });
    if (!els.cargoList.children.length) {
      const li = document.createElement("li");
      li.innerHTML = `<span class="muted">(empty holds)</span><span></span>`;
      els.cargoList.appendChild(li);
    }

    // Recent failures
    els.failuresList.innerHTML = "";
    const failures = obs.recent_failures || [];
    els.failuresMuted.textContent = failures.length ? `(${failures.length})` : "(none)";
    failures.forEach((f) => {
      const li = document.createElement("li");
      const tgt = f.target !== undefined && f.target !== null ? ` ${f.target}` : "";
      li.innerHTML = `<span>${f.kind}${tgt}</span><span class="fail-count">x${f.count}</span>`;
      els.failuresList.appendChild(li);
    });
    if (!failures.length) {
      const li = document.createElement("li");
      li.innerHTML = `<span class="muted">none recently</span><span></span>`;
      els.failuresList.appendChild(li);
    }

    // Known ports
    els.knownPorts.innerHTML = "";
    const ports = obs.known_ports || [];
    ports.slice(-30).forEach((p) => {
      const li = document.createElement("li");
      const hops = p.hops_from_here !== undefined ? ` (${p.hops_from_here}h)` : "";
      li.innerHTML = `<span><span class="port-sid">s${p.sector_id}</span>${p.class || p.code || "?"}</span><span>${hops}</span>`;
      els.knownPorts.appendChild(li);
    });
    if (!ports.length) {
      const li = document.createElement("li");
      li.innerHTML = `<span class="muted">no ports scanned yet</span><span></span>`;
      els.knownPorts.appendChild(li);
    }

    // Raw observation JSON for the Copilot's view panel
    try {
      els.rawObs.textContent = JSON.stringify(obs, null, 2);
    } catch (err) {
      els.rawObs.textContent = "(failed to stringify)";
    }

    // Turn indicator — if turns_remaining > 0 in the current observation
    // we can still technically submit. The authoritative signal is the
    // HUMAN_TURN_START event; refreshing after that fires sets the flag.
    if (state.myTurn) {
      setTurnIndicator("your-turn", "YOUR MOVE");
      setButtonsEnabled(true);
    } else {
      setTurnIndicator("waiting", "waiting for scheduler…");
      setButtonsEnabled(false);
    }
  }

  function setButtonsEnabled(on) {
    els.actionBtns.forEach((b) => {
      b.disabled = !on;
    });
    els.actionSubmit.disabled = !on || state.submitting;
  }

  // ---------------- Action form builder ----------------
  // Each action kind maps engine-side; this is pure UI-side input shape.
  const ACTION_SPECS = {
    "warp": {
      kind: "warp",
      title: "Warp",
      fields: [
        { key: "to", label: "Target sector", type: "number", required: true, hint: "Must be in adjacent warps" },
      ],
      hint: "Move one hop. Costs per-ship turns_per_warp.",
      buildArgs: (v) => ({ target: parseInt(v.to, 10) }),
    },
    "scan": {
      kind: "scan",
      title: "Scan",
      fields: [], // scans the current sector by default
      hint: "Scan current sector (reveals warps + port stock). Costs 1 turn.",
      buildArgs: () => ({}),
    },
    "probe": {
      kind: "probe",
      title: "Probe",
      fields: [
        { key: "to", label: "Target sector", type: "number", required: true, hint: "Any sector, doesn't need to be adjacent" },
      ],
      hint: "Launch ether probe. Consumes 1 probe from inventory.",
      buildArgs: (v) => ({ target: parseInt(v.to, 10) }),
    },
    "trade-buy": {
      kind: "trade",
      title: "Buy at port",
      fields: [
        { key: "commodity", label: "Commodity", type: "select", options: ["fuel_ore", "organics", "equipment"], required: true },
        { key: "qty", label: "Quantity", type: "number", required: true },
        { key: "haggle", label: "Haggle %", type: "number", hint: "0 = pay list; negative % tries to pay less" },
      ],
      hint: "Current sector must have a port that SELLS the commodity.",
      buildArgs: (v) => ({
        side: "buy",
        commodity: v.commodity,
        qty: parseInt(v.qty, 10),
        haggle_pct: v.haggle !== "" ? parseFloat(v.haggle) : 0,
      }),
    },
    "trade-sell": {
      kind: "trade",
      title: "Sell at port",
      fields: [
        { key: "commodity", label: "Commodity", type: "select", options: ["fuel_ore", "organics", "equipment"], required: true },
        { key: "qty", label: "Quantity", type: "number", required: true },
        { key: "haggle", label: "Haggle %", type: "number", hint: "0 = list; positive % tries to get more" },
      ],
      hint: "Current sector must have a port that BUYS the commodity.",
      buildArgs: (v) => ({
        side: "sell",
        commodity: v.commodity,
        qty: parseInt(v.qty, 10),
        haggle_pct: v.haggle !== "" ? parseFloat(v.haggle) : 0,
      }),
    },
    "wait": {
      kind: "wait",
      title: "Wait",
      fields: [],
      hint: "Skip this turn. Useful if you're out of useful moves.",
      buildArgs: () => ({}),
    },
    "land": {
      kind: "land_planet",
      title: "Land on planet",
      fields: [
        { key: "planet_id", label: "Planet id", type: "number", required: true },
      ],
      hint: "Current sector must contain the specified planet.",
      buildArgs: (v) => ({ planet_id: parseInt(v.planet_id, 10) }),
    },
    "liftoff": {
      kind: "liftoff",
      title: "Lift off",
      fields: [],
      hint: "Return to your sector from the planet surface.",
      buildArgs: () => ({}),
    },
    "hail": {
      kind: "hail",
      title: "Hail a player",
      fields: [
        { key: "to_player", label: "Target player", type: "text", required: true, hint: "e.g. P1" },
        { key: "message", label: "Message", type: "text", required: true },
      ],
      hint: "Private message to one player (they must be in range).",
      buildArgs: (v) => ({ target: v.to_player, message: v.message }),
    },
    "broadcast": {
      kind: "broadcast",
      title: "Broadcast to galaxy",
      fields: [
        { key: "message", label: "Message", type: "text", required: true },
      ],
      hint: "Seen by everyone. No reply.",
      buildArgs: (v) => ({ message: v.message }),
    },
  };

  function openActionForm(actionKey, presets) {
    const spec = ACTION_SPECS[actionKey];
    if (!spec) return;
    state.currentAction = actionKey;
    els.actionForm.hidden = false;
    els.actionTitle.textContent = spec.title;
    els.actionHint.textContent = spec.hint || "";
    els.actionFields.innerHTML = "";
    spec.fields.forEach((f) => {
      const label = document.createElement("label");
      const span = document.createElement("span");
      span.textContent = f.label;
      label.appendChild(span);
      let input;
      if (f.type === "select") {
        input = document.createElement("select");
        (f.options || []).forEach((opt) => {
          const o = document.createElement("option");
          o.value = opt;
          o.textContent = opt;
          input.appendChild(o);
        });
      } else {
        input = document.createElement("input");
        input.type = f.type || "text";
      }
      input.name = f.key;
      input.dataset.required = !!f.required;
      if (presets && presets[f.key] !== undefined) input.value = presets[f.key];
      if (f.hint) input.title = f.hint;
      label.appendChild(input);
      els.actionFields.appendChild(label);
    });
    // Auto-focus first field
    const first = els.actionFields.querySelector("input, select");
    if (first) first.focus();

    // Visual highlight on the chosen button
    els.actionBtns.forEach((b) =>
      b.classList.toggle("active", b.dataset.actionKind === actionKey)
    );
  }

  function closeActionForm() {
    els.actionForm.hidden = true;
    state.currentAction = null;
    els.actionBtns.forEach((b) => b.classList.remove("active"));
  }

  function collectFormValues() {
    const out = {};
    els.actionFields.querySelectorAll("input, select").forEach((el) => {
      out[el.name] = el.value;
    });
    return out;
  }

  async function submitAction(ev) {
    if (ev) ev.preventDefault();
    if (!state.currentAction || state.submitting) return;
    const spec = ACTION_SPECS[state.currentAction];
    const values = collectFormValues();

    for (const f of spec.fields) {
      if (f.required && !values[f.key]) {
        els.submitStatus.className = "submit-status err";
        els.submitStatus.textContent = `${f.label} is required`;
        return;
      }
    }

    let args;
    try {
      args = spec.buildArgs(values);
    } catch (err) {
      els.submitStatus.className = "submit-status err";
      els.submitStatus.textContent = `form error: ${err.message}`;
      return;
    }

    const body = {
      player_id: playerId,
      action: { kind: spec.kind, args },
    };

    state.submitting = true;
    els.actionSubmit.disabled = true;
    els.submitStatus.className = "submit-status pending";
    els.submitStatus.textContent = `submitting ${spec.kind} …`;
    try {
      const r = await fetch("/api/human/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        els.submitStatus.className = "submit-status err";
        els.submitStatus.textContent = `HTTP ${r.status}: ${data.detail || "unknown error"}`;
      } else {
        els.submitStatus.className = "submit-status ok";
        els.submitStatus.textContent = `queued ${spec.kind} (pending=${data.pending})`;
        closeActionForm();
        // Optimistically flip to "waiting" — the scheduler will ack
        // via the next HUMAN_TURN_START.
        state.myTurn = false;
        setTurnIndicator("waiting", "action dispatched …");
        setButtonsEnabled(false);
      }
    } catch (err) {
      els.submitStatus.className = "submit-status err";
      els.submitStatus.textContent = `network error: ${err.message}`;
    } finally {
      state.submitting = false;
      els.actionSubmit.disabled = !state.myTurn;
    }
  }

  // ---------------- Event ticker ----------------
  function appendEvent(ev) {
    state.eventHistory.push(ev);
    if (state.eventHistory.length > EVENT_MAX) state.eventHistory.shift();
    const li = document.createElement("li");
    const kind = (ev.actor_kind || "").toLowerCase();
    const actorClass = kind ? `ev-actor ev-actor-${kind}` : "ev-actor ev-actor-engine";
    const actor = ev.actor_id || (kind || "engine");
    const time = `D${ev.day || 0}·t${ev.tick || 0}`;
    const kindPart = ev.kind || "";
    const summary = ev.summary || "";
    const hl = ev.actor_id === playerId ? " ev-highlight" : "";
    li.className = hl;
    li.innerHTML = `<span class="ev-time">${time}</span><span class="${actorClass}">${actor}</span><span class="ev-kind"><strong>${kindPart}</strong> ${summary || ""}</span>`;
    els.events.appendChild(li);
    while (els.events.children.length > EVENT_MAX) {
      els.events.removeChild(els.events.firstChild);
    }
    els.events.scrollTop = els.events.scrollHeight;
  }

  function handleEvent(ev) {
    appendEvent(ev);
    if (ev.kind === "day_tick") {
      els.dayLabel.textContent = `Day ${ev.day}`;
    }
    if (ev.kind === "human_turn_start" && ev.actor_id === playerId) {
      state.myTurn = true;
      setTurnIndicator("your-turn", "YOUR MOVE");
      // Refresh observation now that it's our turn and act on it.
      refreshObservation();
    }
    // Any action we submitted produces events attributed to us — keep
    // them highlighted but don't flip myTurn; the scheduler will
    // re-emit HUMAN_TURN_START on our next turn.
  }

  // ---------------- WebSocket ----------------
  function connectWS() {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${proto}//${window.location.host}/ws`;
    let ws;
    try {
      ws = new WebSocket(url);
    } catch (err) {
      console.error("WS construction failed", err);
      setStatusDot("ws error", "#ff5d6e");
      return;
    }
    ws.onopen = () => {
      state.wsConnected = true;
      setStatusDot("connected", "#79ffb0");
    };
    ws.onmessage = (m) => {
      try {
        const msg = JSON.parse(m.data);
        if (msg.type === "event" && msg.event) {
          handleEvent(msg.event);
        } else if (msg.type === "snapshot" && msg.snapshot) {
          if (msg.snapshot.day !== undefined) {
            state.day = msg.snapshot.day;
            els.dayLabel.textContent = `Day ${msg.snapshot.day}`;
          }
        } else if (msg.type === "copilot_chat") {
          handleCopilotWsEvent(msg);
        }
      } catch (err) {
        /* ignore malformed */
      }
    };
    ws.onclose = () => {
      state.wsConnected = false;
      setStatusDot("reconnecting …", "#ffb36e");
      setTimeout(connectWS, 1500);
    };
    ws.onerror = () => {
      setStatusDot("ws error", "#ff5d6e");
    };
  }

  // ---------------- Keyboard shortcuts ----------------
  function handleKey(ev) {
    // Skip when typing in form fields.
    const tag = (ev.target && ev.target.tagName) || "";
    if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") {
      if (ev.key === "Escape") {
        // Esc in the copilot chat input cancels the active plan/task
        // even while focused in the text field — matches the UI hint.
        if (ev.target === copilotEls.chatInput) {
          cancelAny("human_cancel");
          return;
        }
        closeActionForm();
      }
      return;
    }
    if (ev.key === "Escape") {
      closeActionForm();
      // Also kill any in-flight copilot plan/task so Esc is a universal
      // "stop whatever you were doing" chord (per exit-criterion §12).
      if (copilotState.pendingPlan || copilotState.activeTask) {
        cancelAny("human_cancel");
      }
      return;
    }
    if (ev.key === "?") {
      els.shortcutsToast.hidden = !els.shortcutsToast.hidden;
      return;
    }
    if (ev.key === "/") {
      // Focus the copilot chat input, like many dev tools.
      ev.preventDefault();
      if (copilotEls.chatInput) copilotEls.chatInput.focus();
      return;
    }
    if (ev.key === "Enter" && copilotState.pendingPlan) {
      ev.preventDefault();
      confirmPending();
      return;
    }
    if (ev.key === "F5") {
      ev.preventDefault();
      refreshObservation();
      return;
    }
    const map = {
      w: "warp",
      s: "scan",
      p: "probe",
      b: "trade-buy",
      l: "trade-sell",
      ".": "wait",
    };
    const key = ev.key.toLowerCase();
    if (map[key] && !state.submitting && state.myTurn) {
      ev.preventDefault();
      openActionForm(map[key]);
    }
  }

  // ---------------- Copilot (H2) ----------------

  const copilotEls = {
    modeRow: $("copilotModeRow"),
    modePill: $("copilotModePill"),
    planPreview: $("copilotPlanPreview"),
    planTitle: $("copilotPlanTitle"),
    planThought: $("copilotPlanThought"),
    planSteps: $("copilotPlanSteps"),
    confirmBtn: $("copilotConfirmBtn"),
    cancelPlanBtn: $("copilotCancelPlanBtn"),
    taskBanner: $("copilotTaskBanner"),
    taskSummary: $("copilotTaskSummary"),
    cancelTaskBtn: $("copilotCancelTaskBtn"),
    chat: $("copilotChat"),
    chatForm: $("copilotChatForm"),
    chatInput: $("copilotChatInput"),
    ordersCount: $("copilotOrdersCount"),
    ordersList: $("copilotOrdersList"),
    orderForm: $("copilotOrderForm"),
    orderKind: $("copilotOrderKind"),
    orderValue: $("copilotOrderValue"),
    // H4
    escalation: $("copilotEscalation"),
    escalationTitle: $("copilotEscalationTitle"),
    escalationReason: $("copilotEscalationReason"),
    escalationDismiss: $("copilotEscalationDismiss"),
    ttsBtn: $("ttsToggleBtn"),
    // H5
    voiceLangSelect: $("voiceLangSelect"),
    whatif: $("copilotWhatIf"),
    whatifOneLiner: $("copilotWhatIfOneLiner"),
    whatifWarnings: $("copilotWhatIfWarnings"),
    memoryChip: $("copilotMemoryChip"),
    memoryPrefs: $("copilotMemoryPrefs"),
    memoryRules: $("copilotMemoryRules"),
    memoryFavs: $("copilotMemoryFavs"),
    memoryForm: $("copilotMemoryForm"),
    memoryKey: $("copilotMemoryKey"),
    memoryValue: $("copilotMemoryValue"),
  };

  const copilotState = {
    mode: "advisory",
    pendingPlan: null,
    activeTask: null,
    orders: [],
    seenMessageIds: new Set(),
    // H5.1 — memory snapshot mirror for the right-panel details.
    memory: {
      summary: "empty",
      preferences: {},
      learned_rules: [],
      favorite_sectors: [],
      stats: {},
    },
    // H5.4 — last what-if preview for the pending plan.
    whatif: null,
  };

  function renderChatMessage(msg) {
    if (!msg || !msg.id) return;
    if (copilotState.seenMessageIds.has(msg.id)) return;
    copilotState.seenMessageIds.add(msg.id);

    const li = document.createElement("div");
    li.className = `chat-msg role-${msg.role} kind-${msg.kind || "speak"}`;
    const role = document.createElement("span");
    role.className = "chat-role";
    role.textContent = msg.role;
    const body = document.createElement("span");
    body.className = "chat-body";
    body.textContent = " " + (msg.text || "");
    li.appendChild(role);
    li.appendChild(body);
    const thought = msg.payload && msg.payload.thought;
    if (thought) {
      const t = document.createElement("span");
      t.className = "chat-thought";
      t.textContent = thought;
      li.appendChild(t);
    }
    copilotEls.chat.appendChild(li);
    copilotEls.chat.scrollTop = copilotEls.chat.scrollHeight;
  }

  function renderPendingPlan(pp) {
    copilotState.pendingPlan = pp;
    if (!pp) {
      copilotEls.planPreview.hidden = true;
      copilotEls.planSteps.innerHTML = "";
      renderWhatIf(null);
      return;
    }
    copilotEls.planPreview.hidden = false;
    const isTask = !!pp.task_kind;
    copilotEls.planTitle.textContent = isTask
      ? `Autopilot proposal: ${pp.task_kind}`
      : `Pending plan (${(pp.plan || []).length} steps)`;
    copilotEls.planThought.textContent = pp.thought || "";
    copilotEls.planSteps.innerHTML = "";
    if (isTask) {
      const li = document.createElement("li");
      li.textContent = `${pp.task_kind} ${JSON.stringify(pp.task_params || {})}`;
      copilotEls.planSteps.appendChild(li);
    } else {
      (pp.plan || []).forEach((c) => {
        const li = document.createElement("li");
        li.textContent = `${c.name}(${JSON.stringify(c.arguments || {})})`;
        copilotEls.planSteps.appendChild(li);
      });
    }
    fetchWhatIf();
  }

  // H5.4 — what-if predicted outcome ---------------------------------
  function renderWhatIf(wi) {
    copilotState.whatif = wi;
    if (!copilotEls.whatif) return;
    if (!wi || !wi.pending) {
      copilotEls.whatif.hidden = true;
      if (copilotEls.whatifOneLiner) copilotEls.whatifOneLiner.textContent = "";
      if (copilotEls.whatifWarnings) copilotEls.whatifWarnings.innerHTML = "";
      return;
    }
    copilotEls.whatif.hidden = false;
    const one = wi.one_liner || "";
    if (copilotEls.whatifOneLiner) {
      copilotEls.whatifOneLiner.textContent = one;
      copilotEls.whatifOneLiner.classList.toggle(
        "is-positive",
        typeof wi.credit_delta === "number" && wi.credit_delta > 0
      );
      copilotEls.whatifOneLiner.classList.toggle(
        "is-negative",
        typeof wi.credit_delta === "number" && wi.credit_delta < 0
      );
    }
    if (copilotEls.whatifWarnings) {
      copilotEls.whatifWarnings.innerHTML = "";
      (wi.warnings || []).forEach((w) => {
        const li = document.createElement("li");
        li.textContent = w;
        copilotEls.whatifWarnings.appendChild(li);
      });
    }
  }

  async function fetchWhatIf() {
    if (!playerId) return;
    try {
      const r = await fetch(
        `/api/copilot/whatif?player_id=${encodeURIComponent(playerId)}`
      );
      if (!r.ok) return;
      const wi = await r.json();
      renderWhatIf(wi);
    } catch (err) {
      /* non-fatal; preview stays empty */
    }
  }

  // H5.1 — memory panel ---------------------------------------------
  function renderMemory(m) {
    copilotState.memory = m || copilotState.memory;
    const mem = copilotState.memory;
    if (copilotEls.memoryChip) {
      copilotEls.memoryChip.textContent = mem.summary || "empty";
    }
    if (copilotEls.memoryPrefs) {
      copilotEls.memoryPrefs.innerHTML = "";
      Object.entries(mem.preferences || {}).forEach(([k, v]) => {
        const li = document.createElement("li");
        const key = document.createElement("span");
        key.className = "mem-key";
        key.textContent = k;
        const eq = document.createTextNode(" = ");
        const val = document.createElement("span");
        val.className = "mem-val";
        val.textContent = v;
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "mem-forget";
        btn.textContent = "forget";
        btn.title = `Forget ${k}`;
        btn.addEventListener("click", () => memoryForget(k));
        li.appendChild(key);
        li.appendChild(eq);
        li.appendChild(val);
        li.appendChild(btn);
        copilotEls.memoryPrefs.appendChild(li);
      });
    }
    if (copilotEls.memoryRules) {
      copilotEls.memoryRules.innerHTML = "";
      (mem.learned_rules || []).forEach((r) => {
        const li = document.createElement("li");
        li.textContent = r;
        copilotEls.memoryRules.appendChild(li);
      });
    }
    if (copilotEls.memoryFavs) {
      copilotEls.memoryFavs.innerHTML = "";
      (mem.favorite_sectors || []).slice(-16).forEach((sid) => {
        const s = document.createElement("span");
        s.className = "fav-chip";
        s.textContent = `#${sid}`;
        copilotEls.memoryFavs.appendChild(s);
      });
    }
  }

  async function memoryRemember(key, value) {
    if (!playerId || !key || !value) return;
    try {
      const r = await fetch("/api/copilot/memory/remember", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_id: playerId, key, value }),
      });
      if (r.ok) {
        const j = await r.json();
        renderMemory(j.memory || null);
      }
    } catch (err) {
      console.error("remember failed", err);
    }
  }

  async function memoryForget(key) {
    if (!playerId || !key) return;
    try {
      const r = await fetch("/api/copilot/memory/forget", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_id: playerId, key }),
      });
      if (r.ok) {
        const j = await r.json();
        renderMemory(j.memory || null);
      }
    } catch (err) {
      console.error("forget failed", err);
    }
  }

  function renderActiveTask(task) {
    copilotState.activeTask = task;
    if (!task) {
      copilotEls.taskBanner.hidden = true;
      return;
    }
    copilotEls.taskBanner.hidden = false;
    const iter = task.iterations || 0;
    copilotEls.taskSummary.textContent =
      `autopilot: ${task.kind} ${JSON.stringify(task.params || {})} — ` +
      `iter ${iter}` + (task.last_action ? ` · last ${task.last_action}` : "");
  }

  function renderOrders(orders) {
    copilotState.orders = orders || [];
    copilotEls.ordersCount.textContent =
      copilotState.orders.length ? `(${copilotState.orders.length})` : "";
    copilotEls.ordersList.innerHTML = "";
    copilotState.orders.forEach((o) => {
      const li = document.createElement("li");
      const label = document.createElement("span");
      label.textContent = o.description || `${o.kind} ${JSON.stringify(o.params || {})}`;
      const btn = document.createElement("button");
      btn.className = "remove-order";
      btn.type = "button";
      btn.textContent = "✕";
      btn.title = "Remove order";
      btn.addEventListener("click", () => removeOrder(o.id));
      li.appendChild(label);
      li.appendChild(btn);
      copilotEls.ordersList.appendChild(li);
    });
  }

  function setCopilotMode(mode) {
    const prev = copilotState.mode;
    copilotState.mode = mode;
    copilotEls.modePill.textContent = `mode: ${mode}`;
    document
      .querySelectorAll(".mode-btn")
      .forEach((b) => b.classList.toggle("is-active", b.dataset.mode === mode));
    // H4: keep the always-on interrupt listener aligned with Autopilot.
    if (typeof syncInterruptListenerToMode === "function") {
      syncInterruptListenerToMode(mode);
    }
    // H4: probe safety on the one-shot endpoint when the user *enters*
    // autopilot so the escalation banner raises even if no TaskAgent is
    // running yet. Leaving autopilot clears it.
    if (prev !== mode && typeof pollSafetyForMode === "function") {
      pollSafetyForMode(mode);
    }
  }

  async function fetchCopilotState() {
    if (!playerId) return;
    try {
      const r = await fetch(
        `/api/copilot/state?player_id=${encodeURIComponent(playerId)}`
      );
      if (!r.ok) return;
      const s = await r.json();
      setCopilotMode(s.mode || "advisory");
      (s.chat || []).forEach(renderChatMessage);
      renderPendingPlan(s.pending_plan || null);
      renderActiveTask(s.active_task || null);
      renderOrders(s.standing_orders || []);
      if (s.memory) renderMemory(s.memory);
      if (s.whatif) {
        renderWhatIf({ pending: true, ...s.whatif });
      }
    } catch (err) {
      /* ignore */
    }
  }

  async function sendChat(text) {
    if (!text || !playerId) return;
    try {
      await fetch("/api/copilot/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_id: playerId, message: text }),
      });
    } catch (err) {
      console.error("chat failed", err);
    }
  }

  async function changeMode(mode) {
    try {
      const r = await fetch("/api/copilot/mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_id: playerId, mode }),
      });
      if (r.ok) setCopilotMode(mode);
    } catch (err) {
      console.error("mode change failed", err);
    }
  }

  async function confirmPending() {
    const pp = copilotState.pendingPlan;
    if (!pp) return;
    try {
      await fetch("/api/copilot/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_id: playerId, plan_id: pp.id }),
      });
      renderPendingPlan(null);
    } catch (err) {
      console.error("confirm failed", err);
    }
  }

  async function cancelAny(reason) {
    try {
      await fetch("/api/copilot/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_id: playerId, reason: reason || "human_cancel" }),
      });
    } catch (err) {
      console.error("cancel failed", err);
    }
  }

  async function addOrder() {
    const kind = copilotEls.orderKind.value;
    const raw = (copilotEls.orderValue.value || "").trim();
    if (!raw) return;
    let params = {};
    if (kind === "min_credit_reserve") {
      const n = parseInt(raw, 10);
      if (isNaN(n)) return;
      params = { credits: n };
    } else if (kind === "no_warp_to_sectors") {
      params = {
        sectors: raw
          .split(",")
          .map((s) => parseInt(s.trim(), 10))
          .filter((n) => !isNaN(n)),
      };
    } else if (kind === "max_haggle_delta_pct") {
      const n = parseFloat(raw);
      if (isNaN(n)) return;
      params = { pct: n };
    }
    const order = {
      id: `u-${Date.now().toString(36)}`,
      kind,
      params,
      description: "",
      active: true,
    };
    try {
      const r = await fetch("/api/copilot/standing-orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_id: playerId, order }),
      });
      if (r.ok) {
        const s = await r.json();
        renderOrders(s.orders || []);
        copilotEls.orderValue.value = "";
      }
    } catch (err) {
      console.error("add order failed", err);
    }
  }

  async function removeOrder(orderId) {
    try {
      const r = await fetch(
        `/api/copilot/standing-orders?player_id=${encodeURIComponent(
          playerId
        )}&order_id=${encodeURIComponent(orderId)}`,
        { method: "DELETE" }
      );
      if (r.ok) {
        const s = await r.json();
        renderOrders(s.orders || []);
      }
    } catch (err) {
      console.error("remove order failed", err);
    }
  }

  function handleCopilotWsEvent(msg) {
    if (msg.type !== "copilot_chat") return;
    if (msg.player_id && playerId && msg.player_id !== playerId) return;
    const m = msg.message;
    renderChatMessage(m);
    if (!m || !m.kind) return;
    // H4: TTS + escalation banner
    if (typeof maybeSpeakMessage === "function") maybeSpeakMessage(m);
    if (m.kind === "escalation" && typeof showEscalation === "function") {
      showEscalation({
        title: "Autopilot paused",
        reason: (m.payload && m.payload.reason) || m.text || "",
      });
    }
    if (m.kind === "plan_preview" && m.payload) {
      renderPendingPlan({
        id: m.payload.plan_id,
        plan: m.payload.plan,
        thought: m.payload.thought || "",
      });
    } else if (m.kind === "task_preview" && m.payload) {
      renderPendingPlan({
        id: m.payload.plan_id,
        task_kind: m.payload.task_kind,
        task_params: m.payload.task_params || {},
        plan: [],
      });
    } else if (m.kind === "plan_cancelled" || m.kind === "confirm_rejected") {
      renderPendingPlan(null);
    } else if (m.kind === "task_started" && m.payload && m.payload.task) {
      renderPendingPlan(null);
      renderActiveTask(m.payload.task);
    } else if (m.kind === "task_progress" && m.payload) {
      renderActiveTask({
        kind: (copilotState.activeTask && copilotState.activeTask.kind) || "autopilot",
        params: (copilotState.activeTask && copilotState.activeTask.params) || {},
        iterations: m.payload.iter,
        last_action: m.payload.last_action || m.payload.tool,
      });
    } else if (m.kind === "task_finished") {
      renderActiveTask(null);
    } else if (m.kind === "mode_change") {
      // state endpoint is authoritative; just re-fetch.
      fetchCopilotState();
    } else if (
      m.kind === "standing_order_added" ||
      m.kind === "standing_order_removed"
    ) {
      fetchCopilotState();
    } else if (m.kind === "memory_update") {
      // H5.1 — refresh memory chip + prefs list whenever the session
      // logs a remember/forget. Cheap endpoint; avoids re-broadcasting
      // the whole snapshot for every keystroke.
      fetchMemorySnapshot();
    }
  }

  async function fetchMemorySnapshot() {
    if (!playerId) return;
    try {
      const r = await fetch(
        `/api/copilot/memory?player_id=${encodeURIComponent(playerId)}`
      );
      if (r.ok) renderMemory(await r.json());
    } catch (err) {
      /* ignore */
    }
  }

  function wireCopilot() {
    copilotEls.chatForm.addEventListener("submit", (ev) => {
      ev.preventDefault();
      const text = copilotEls.chatInput.value.trim();
      if (!text) return;
      copilotEls.chatInput.value = "";
      sendChat(text);
    });
    document.querySelectorAll(".mode-btn").forEach((btn) => {
      btn.addEventListener("click", () => changeMode(btn.dataset.mode));
    });
    copilotEls.confirmBtn.addEventListener("click", confirmPending);
    copilotEls.cancelPlanBtn.addEventListener("click", () => cancelAny("plan_cancel"));
    copilotEls.cancelTaskBtn.addEventListener("click", () => cancelAny("task_cancel"));
    copilotEls.orderForm.addEventListener("submit", (ev) => {
      ev.preventDefault();
      addOrder();
    });
    // H5.1 — memory form (remember key = value).
    if (copilotEls.memoryForm) {
      copilotEls.memoryForm.addEventListener("submit", (ev) => {
        ev.preventDefault();
        const k = (copilotEls.memoryKey.value || "").trim();
        const v = (copilotEls.memoryValue.value || "").trim();
        if (!k || !v) return;
        memoryRemember(k, v);
        copilotEls.memoryKey.value = "";
        copilotEls.memoryValue.value = "";
      });
    }
    // H5.3 — voice language selector. Persists in localStorage and
    // applies to both the PTT `SpeechRecognition.lang` AND the
    // `SpeechSynthesisUtterance.lang` so input and output stay aligned.
    if (copilotEls.voiceLangSelect) {
      const saved = _loadVoiceLang();
      if (saved) copilotEls.voiceLangSelect.value = saved;
      applyVoiceLang(copilotEls.voiceLangSelect.value);
      copilotEls.voiceLangSelect.addEventListener("change", () => {
        _saveVoiceLang(copilotEls.voiceLangSelect.value);
        applyVoiceLang(copilotEls.voiceLangSelect.value);
      });
    }
  }

  // ---------------- Voice input / Push-to-talk (H3) ----------------
  //
  // Browser Web Speech API is sufficient for the MVP — no Pipecat, no
  // server-side STT. On browsers without support (Firefox, some Safari
  // versions) the button renders as a disabled "no mic" indicator and
  // the text form still works, so the feature degrades gracefully.

  const pttEls = {
    btn: $("pttBtn"),
    status: $("pttStatus"),
    state: $("pttState"),
    partial: $("pttPartial"),
  };

  const voiceState = {
    supported: false,
    recognition: null,
    listening: false,
    interim: "",
    final: "",
    lastError: null,
    // When listening started via a held Space key. We distinguish so
    // release-to-submit only fires if the start was a keydown (matches
    // the "walkie-talkie" UX — tap-to-toggle via button is also OK).
    startedFromKey: false,
  };

  function _speechCtor() {
    return window.SpeechRecognition || window.webkitSpeechRecognition || null;
  }

  // H5.3 — voice language -------------------------------------------------
  // BCP-47 tag (e.g. "en-US", "ja-JP"). Persisted in localStorage so it
  // survives reloads. Applied to BOTH SpeechRecognition.lang AND
  // SpeechSynthesisUtterance.lang.
  const VOICE_LANG_KEY = "tw2k.voice.lang";
  function _loadVoiceLang() {
    try {
      return window.localStorage.getItem(VOICE_LANG_KEY) || "";
    } catch {
      return "";
    }
  }
  function _saveVoiceLang(lang) {
    try {
      window.localStorage.setItem(VOICE_LANG_KEY, lang);
    } catch {
      /* ignore */
    }
  }
  function applyVoiceLang(lang) {
    if (!lang) return;
    if (voiceState && voiceState.recognition) {
      try {
        voiceState.recognition.lang = lang;
      } catch {
        /* ignore */
      }
    }
    if (interruptState && interruptState.recognition) {
      try {
        interruptState.recognition.lang = lang;
      } catch {
        /* ignore */
      }
    }
    if (ttsState) {
      ttsState.lang = lang;
    }
  }

  function initVoice() {
    const Ctor = _speechCtor();
    if (!pttEls.btn) return;
    if (!Ctor) {
      voiceState.supported = false;
      pttEls.btn.classList.add("is-unsupported");
      pttEls.btn.disabled = true;
      pttEls.btn.title =
        "Voice input requires a Chromium-based browser (Chrome/Edge). Keyboard + text still work.";
      const lbl = pttEls.btn.querySelector(".ptt-label");
      if (lbl) lbl.textContent = "No mic";
      return;
    }
    voiceState.supported = true;
    const rec = new Ctor();
    rec.continuous = false;
    rec.interimResults = true;
    // H5.3 — honour the saved voice language if any, else default to the
    // browser language if it's English, else fall back to en-US.
    const savedLang = _loadVoiceLang();
    rec.lang =
      savedLang ||
      ((navigator.language || "en-US").startsWith("en")
        ? navigator.language || "en-US"
        : "en-US");
    rec.maxAlternatives = 1;
    rec.onstart = () => {
      voiceState.listening = true;
      voiceState.interim = "";
      voiceState.final = "";
      voiceState.lastError = null;
      pttEls.btn.classList.add("is-listening");
      pttEls.btn.setAttribute("aria-pressed", "true");
      pttEls.status.hidden = false;
      pttEls.state.textContent = "listening";
      pttEls.state.className = "ptt-state is-listening";
      pttEls.partial.textContent = "";
    };
    rec.onerror = (ev) => {
      voiceState.lastError = ev.error || "error";
      pttEls.state.textContent = `error: ${voiceState.lastError}`;
      pttEls.state.className = "ptt-state is-error";
      // no-speech / aborted are benign — user released quickly.
      if (["no-speech", "aborted"].includes(voiceState.lastError)) {
        return;
      }
    };
    rec.onresult = (ev) => {
      let interim = "";
      let final = "";
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const r = ev.results[i];
        const transcript = r[0] && r[0].transcript ? r[0].transcript : "";
        if (r.isFinal) final += transcript;
        else interim += transcript;
      }
      if (final) voiceState.final += final;
      voiceState.interim = interim;
      pttEls.partial.textContent = voiceState.final + (interim ? " …" + interim : "");
    };
    rec.onend = () => {
      voiceState.listening = false;
      pttEls.btn.classList.remove("is-listening");
      pttEls.btn.setAttribute("aria-pressed", "false");
      const combined = normalizeVoiceTranscript(
        (voiceState.final + " " + voiceState.interim).trim()
      );
      if (combined) {
        pttEls.state.textContent = "sent";
        pttEls.state.className = "ptt-state";
        pttEls.partial.textContent = combined;
        sendChat(combined);
        // Auto-hide the status pill after a beat so it doesn't linger.
        setTimeout(() => {
          if (!voiceState.listening) {
            pttEls.status.hidden = true;
            pttEls.partial.textContent = "";
          }
        }, 2200);
      } else if (voiceState.lastError) {
        // Keep the error visible for a moment, then reset.
        setTimeout(() => {
          if (!voiceState.listening) {
            pttEls.status.hidden = true;
            pttEls.state.textContent = "idle";
            pttEls.state.className = "ptt-state";
          }
        }, 2500);
      } else {
        pttEls.status.hidden = true;
      }
    };
    voiceState.recognition = rec;
  }

  function startListening({ fromKey = false } = {}) {
    if (!voiceState.supported || voiceState.listening) return;
    voiceState.startedFromKey = fromKey;
    voiceState.final = "";
    voiceState.interim = "";
    try {
      voiceState.recognition.start();
    } catch (err) {
      // start() throws if already started; ignore.
    }
  }

  function stopListening() {
    if (!voiceState.supported || !voiceState.listening) return;
    try {
      voiceState.recognition.stop();
    } catch (err) {
      /* ignore */
    }
  }

  function toggleListening() {
    if (voiceState.listening) stopListening();
    else startListening({ fromKey: false });
  }

  // Grammar / normalization — cheap phonetic fixups for sector numbers
  // and commodity names so "eight seventy four" -> "874", "fuel ore"
  // -> "fuel_ore". Extend opportunistically; we favour recall over
  // precision because the ChatAgent can still understand raw English.
  const _NUMBER_WORDS = {
    zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5,
    six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
    eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15,
    sixteen: 16, seventeen: 17, eighteen: 18, nineteen: 19,
    twenty: 20, thirty: 30, forty: 40, fifty: 50,
    sixty: 60, seventy: 70, eighty: 80, ninety: 90,
    hundred: 100, thousand: 1000,
  };

  function normalizeVoiceTranscript(raw) {
    if (!raw) return raw;
    let s = String(raw).toLowerCase().trim();
    // Commodity aliases.
    s = s.replace(/\bfuel\s+ore\b/g, "fuel_ore");
    s = s.replace(/\bequipment\b/g, "equipment");
    s = s.replace(/\borganics?\b/g, "organics");
    // Number-word collapse for small counts. This is intentionally a
    // lightweight pass — if the user says "874" the STT usually emits
    // the digits directly anyway. We handle the common spoken forms.
    s = s.replace(
      /\b(zero|one|two|three|four|five|six|seven|eight|nine)\s+(hundred)(\s+(and\s+)?(\w+(\s+\w+)?))?\b/g,
      (_m, h, _hundred, _r3, _r4, rest) => {
        const hundreds = _NUMBER_WORDS[h] * 100;
        let tail = 0;
        if (rest) {
          const parts = rest.trim().split(/\s+/);
          for (const p of parts) {
            if (p in _NUMBER_WORDS) tail += _NUMBER_WORDS[p];
          }
        }
        return String(hundreds + tail);
      }
    );
    // Two-word compounds like "eight seventy four" -> "874".
    s = s.replace(
      /\b(one|two|three|four|five|six|seven|eight|nine)\s+(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)\s+(one|two|three|four|five|six|seven|eight|nine)\b/g,
      (_m, a, b, c) => String(_NUMBER_WORDS[a] * 100 + _NUMBER_WORDS[b] + _NUMBER_WORDS[c])
    );
    // "sector eight seventy four" or "to eight seventy four" — collapse
    // trailing digit-digit pairs too.
    s = s.replace(
      /\b(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)\s+(one|two|three|four|five|six|seven|eight|nine)\b/g,
      (_m, b, c) => String(_NUMBER_WORDS[b] + _NUMBER_WORDS[c])
    );
    s = s.replace(/\s{2,}/g, " ").trim();
    return s;
  }

  function wirePtt() {
    if (pttEls.btn) {
      pttEls.btn.addEventListener("click", toggleListening);
      pttEls.btn.addEventListener("keydown", (ev) => {
        // Space while button is focused acts like PTT hold.
        if (ev.key === " " || ev.code === "Space") {
          ev.preventDefault();
          startListening({ fromKey: true });
        }
      });
      pttEls.btn.addEventListener("keyup", (ev) => {
        if (ev.key === " " || ev.code === "Space") {
          ev.preventDefault();
          stopListening();
        }
      });
    }
  }

  // Expose for tests + console debugging.
  window.__tw2kVoice = {
    state: voiceState,
    startListening,
    stopListening,
    toggleListening,
    normalize: normalizeVoiceTranscript,
  };

  // ---------------- Voice OUTPUT / TTS (H4) ----------------
  //
  // Browser `speechSynthesis` is our free MVP. Off by default so the
  // cockpit doesn't surprise anyone with noise on first load. User
  // preference persists in localStorage.
  //
  // Messages routed through speakCopilot() pass a de-dup + min-gap
  // filter so rapid-fire task_progress events don't overlap each
  // other — only one utterance plays at a time and very-short
  // messages can be coalesced.

  const TTS_STORAGE_KEY = "tw2k.tts.enabled";

  const ttsState = {
    supported: "speechSynthesis" in window,
    enabled: false,
    lastUtteranceTs: 0,
    lastText: "",
    voice: null,
    // H5.3 — BCP-47 language tag the selector + recognition are aligned
    // to. Picked up lazily by _pickVoice / speakCopilot.
    lang: "",
    // Kinds that are worth speaking. "plan_step" and very high-frequency
    // task_progress messages are filtered out — they're noise for voice.
    speakKinds: new Set([
      "speak",
      "clarify",
      "escalation",
      "task_started",
      "task_finished",
      "task_idle",
      "standing_order_block",
      "confirm_rejected",
      "advisory",
    ]),
    // Critical kinds bypass all filters and get spoken urgently.
    urgentKinds: new Set(["escalation"]),
  };

  function _loadTtsPref() {
    try {
      const v = localStorage.getItem(TTS_STORAGE_KEY);
      ttsState.enabled = v === "1";
    } catch (_e) {
      ttsState.enabled = false;
    }
  }

  function _saveTtsPref() {
    try {
      localStorage.setItem(TTS_STORAGE_KEY, ttsState.enabled ? "1" : "0");
    } catch (_e) {
      /* ignore */
    }
  }

  function setTtsEnabled(on) {
    ttsState.enabled = Boolean(on);
    _saveTtsPref();
    _renderTtsButton();
    if (!ttsState.enabled) {
      try {
        window.speechSynthesis.cancel();
      } catch (_e) {
        /* ignore */
      }
    }
  }

  function _renderTtsButton() {
    if (!copilotEls.ttsBtn) return;
    copilotEls.ttsBtn.classList.toggle("is-on", ttsState.enabled);
    copilotEls.ttsBtn.setAttribute("aria-pressed", ttsState.enabled ? "true" : "false");
    const lbl = copilotEls.ttsBtn.querySelector(".tts-label");
    const icon = copilotEls.ttsBtn.querySelector(".tts-icon");
    if (lbl) lbl.textContent = ttsState.enabled ? "Voice" : "Mute";
    if (icon) icon.textContent = ttsState.enabled ? "🔊" : "🔈";
    if (!ttsState.supported) {
      copilotEls.ttsBtn.disabled = true;
      copilotEls.ttsBtn.title = "Browser has no speechSynthesis — TTS disabled.";
      if (lbl) lbl.textContent = "No TTS";
    }
  }

  function _pickVoice() {
    if (!ttsState.supported) return null;
    const voices = window.speechSynthesis.getVoices() || [];
    if (!voices.length) return null;
    // H5.3 — if a language has been explicitly chosen, always honour it.
    // Prefer an exact BCP-47 match, else a base-language match (e.g.
    // "ja" out of "ja-JP"), else a local voice, else the first voice.
    const want = (ttsState.lang || "").toLowerCase();
    if (want) {
      const base = want.split("-")[0];
      const exact = voices.find((v) => v.lang && v.lang.toLowerCase() === want);
      if (exact) return exact;
      const partial = voices.find(
        (v) => v.lang && v.lang.toLowerCase().startsWith(base)
      );
      if (partial) return partial;
    }
    if (ttsState.voice) return ttsState.voice;
    ttsState.voice =
      voices.find((v) => v.lang && v.lang.toLowerCase().startsWith("en") && v.localService) ||
      voices.find((v) => v.lang && v.lang.toLowerCase().startsWith("en")) ||
      voices[0];
    return ttsState.voice;
  }

  function speakCopilot(text, { urgent = false } = {}) {
    if (!ttsState.supported || !ttsState.enabled) return;
    const now = Date.now();
    const clean = String(text || "").trim();
    if (!clean) return;
    // De-dup identical text within 2.5s.
    if (!urgent && clean === ttsState.lastText && now - ttsState.lastUtteranceTs < 2500) {
      return;
    }
    try {
      if (urgent) window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(clean);
      u.rate = urgent ? 1.05 : 1.0;
      u.pitch = urgent ? 1.1 : 1.0;
      u.volume = 1.0;
      const v = _pickVoice();
      if (v) u.voice = v;
      if (ttsState.lang) u.lang = ttsState.lang;
      u.onstart = () => {
        if (copilotEls.ttsBtn) copilotEls.ttsBtn.classList.add("is-speaking");
      };
      u.onend = u.onerror = () => {
        if (copilotEls.ttsBtn) copilotEls.ttsBtn.classList.remove("is-speaking");
      };
      window.speechSynthesis.speak(u);
      ttsState.lastText = clean;
      ttsState.lastUtteranceTs = now;
    } catch (_e) {
      /* ignore */
    }
  }

  function maybeSpeakMessage(msg) {
    if (!msg || !ttsState.enabled) return;
    const role = msg.role;
    const kind = msg.kind || "speak";
    const urgent = ttsState.urgentKinds.has(kind);
    if (!urgent) {
      if (role !== "copilot" && role !== "system") return;
      if (!ttsState.speakKinds.has(kind)) return;
    }
    const text = String(msg.text || "").replace(/\s+/g, " ").trim();
    // Trim obvious prefixes like arrows that read poorly.
    const cleaned = text
      .replace(/^→\s*/, "")
      .replace(/^\?\s*/, "")
      .replace(/\(.*?\)/g, "")
      .trim();
    if (!cleaned) return;
    speakCopilot(cleaned, { urgent });
  }

  function wireTts() {
    _loadTtsPref();
    _renderTtsButton();
    if (!copilotEls.ttsBtn) return;
    copilotEls.ttsBtn.addEventListener("click", () => setTtsEnabled(!ttsState.enabled));
    // Some browsers load voices asynchronously.
    if (ttsState.supported && typeof window.speechSynthesis.addEventListener === "function") {
      window.speechSynthesis.addEventListener("voiceschanged", () => {
        ttsState.voice = null;
        _pickVoice();
      });
    }
  }

  window.__tw2kTts = { state: ttsState, speak: speakCopilot, setEnabled: setTtsEnabled };

  // H5.1 / H5.4 — memory + what-if debug hooks for Playwright + console.
  window.__tw2kMem = {
    state: () => copilotState.memory,
    remember: memoryRemember,
    forget: memoryForget,
    refresh: fetchMemorySnapshot,
  };
  window.__tw2kWhatIf = {
    state: () => copilotState.whatif,
    refresh: fetchWhatIf,
    render: renderWhatIf,
  };
  // H5.3 — voice language helper.
  window.__tw2kVoiceLang = {
    get: _loadVoiceLang,
    set: (lang) => {
      _saveVoiceLang(lang);
      applyVoiceLang(lang);
    },
  };

  // ---------------- Autopilot always-on listener + interrupt words (H4) ----------------
  //
  // In autopilot mode we keep a SECOND SpeechRecognition instance
  // open in continuous mode so the human can yell "stop" / "hold" /
  // "pause" and have the copilot cancel immediately. This is a
  // parallel channel to the PTT recogniser — browsers allow at most
  // one at a time, so we pause the interrupt listener while PTT is
  // active.

  const INTERRUPT_WORDS = [
    "stop",
    "hold",
    "hold on",
    "pause",
    "cancel",
    "abort",
    "halt",
    "belay",
  ];
  const INTERRUPT_RE = new RegExp(
    "\\b(" + INTERRUPT_WORDS.map((w) => w.replace(/\s+/g, "\\s+")).join("|") + ")\\b",
    "i"
  );

  const interruptState = {
    supported: false,
    recognition: null,
    active: false,
    shouldBeActive: false,
    lastHit: 0,
  };

  function initInterruptListener() {
    const Ctor = _speechCtor();
    if (!Ctor) {
      interruptState.supported = false;
      return;
    }
    interruptState.supported = true;
    const rec = new Ctor();
    rec.continuous = true;
    rec.interimResults = true;
    // H5.3 — align interrupt listener to the chosen voice language.
    const interruptLang = _loadVoiceLang();
    rec.lang =
      interruptLang ||
      ((navigator.language || "en-US").startsWith("en")
        ? navigator.language || "en-US"
        : "en-US");
    rec.onstart = () => {
      interruptState.active = true;
      if (pttEls.btn && !voiceState.listening) pttEls.btn.classList.add("is-interrupt-listen");
    };
    rec.onerror = (ev) => {
      // "no-speech" / "aborted" in continuous mode are normal when the
      // user hasn't spoken — the onend handler will restart us.
      if (ev.error === "not-allowed" || ev.error === "service-not-allowed") {
        interruptState.supported = false;
        interruptState.shouldBeActive = false;
      }
    };
    rec.onresult = (ev) => {
      let text = "";
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        text += ev.results[i][0] ? ev.results[i][0].transcript || "" : "";
      }
      const lower = text.toLowerCase();
      if (!lower) return;
      if (INTERRUPT_RE.test(lower)) {
        const now = Date.now();
        if (now - interruptState.lastHit < 2500) return; // debounce
        interruptState.lastHit = now;
        cancelAny("voice_interrupt");
        speakCopilot("Stopping.", { urgent: true });
        try {
          // Clear partial transcript so we don't re-trigger.
          rec.stop();
        } catch (_e) {
          /* ignore */
        }
      }
    };
    rec.onend = () => {
      interruptState.active = false;
      if (pttEls.btn) pttEls.btn.classList.remove("is-interrupt-listen");
      if (interruptState.shouldBeActive && !voiceState.listening) {
        try {
          rec.start();
        } catch (_e) {
          /* ignore */
        }
      }
    };
    interruptState.recognition = rec;
  }

  function startInterruptListening() {
    if (!interruptState.supported || !interruptState.recognition) return;
    interruptState.shouldBeActive = true;
    if (voiceState.listening) return; // PTT has the mic; will resume later
    try {
      interruptState.recognition.start();
    } catch (_e) {
      /* already running */
    }
  }

  function stopInterruptListening() {
    interruptState.shouldBeActive = false;
    if (!interruptState.recognition) return;
    try {
      interruptState.recognition.stop();
    } catch (_e) {
      /* ignore */
    }
  }

  function syncInterruptListenerToMode(mode) {
    if (mode === "autopilot") startInterruptListening();
    else stopInterruptListening();
  }

  window.__tw2kInterrupt = {
    state: interruptState,
    start: startInterruptListening,
    stop: stopInterruptListening,
    test: (s) => INTERRUPT_RE.test(String(s || "").toLowerCase()),
  };

  // ---------------- Escalation banner (H4) ----------------

  function showEscalation({ title, reason }) {
    if (!copilotEls.escalation) return;
    copilotEls.escalation.hidden = false;
    copilotEls.escalationTitle.textContent = title || "Autopilot paused";
    copilotEls.escalationReason.textContent = reason || "";
  }

  function hideEscalation() {
    if (!copilotEls.escalation) return;
    copilotEls.escalation.hidden = true;
  }

  async function pollSafetyForMode(mode) {
    if (!playerId) return;
    if (mode !== "autopilot") {
      hideEscalation();
      return;
    }
    try {
      const r = await fetch(
        `/api/copilot/safety?player_id=${encodeURIComponent(playerId)}`
      );
      if (!r.ok) return;
      const sig = await r.json();
      if (sig.level === "critical" || sig.level === "warning") {
        showEscalation({
          title: sig.level === "critical" ? "Autopilot paused" : "Autopilot warning",
          reason: sig.reason || "",
        });
        if (sig.level === "critical") {
          speakCopilot(`Warning. ${sig.reason}`, { urgent: true });
        }
      } else {
        hideEscalation();
      }
    } catch (_e) {
      /* ignore */
    }
  }

  // ---------------- Wiring ----------------
  function wire() {
    els.actionBtns.forEach((btn) => {
      btn.addEventListener("click", () => openActionForm(btn.dataset.actionKind));
    });
    els.actionCancel.addEventListener("click", closeActionForm);
    els.actionForm.addEventListener("submit", submitAction);
    $("refreshBtn").addEventListener("click", refreshObservation);
    $("helpBtn").addEventListener("click", () => {
      els.shortcutsToast.hidden = !els.shortcutsToast.hidden;
    });
    document.addEventListener("keydown", handleKey);
    wireCopilot();
    initVoice();
    wirePtt();
    // H4 — voice output + interrupt listener + escalation dismiss.
    wireTts();
    initInterruptListener();
    if (copilotEls.escalationDismiss) {
      copilotEls.escalationDismiss.addEventListener("click", hideEscalation);
    }
    // Global Space = push-to-talk hold, as long as no input is focused
    // and the action form is not open. We use keyup/keydown at the
    // document level so the user can hold Space from anywhere on the
    // cockpit, not just while the button is focused.
    let _spaceActive = false;
    document.addEventListener("keydown", (ev) => {
      if (ev.repeat) return;
      if (!(ev.key === " " || ev.code === "Space")) return;
      const tag = (ev.target && ev.target.tagName) || "";
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
      if (els.actionForm && !els.actionForm.hidden) return;
      if (!voiceState.supported) return;
      ev.preventDefault();
      _spaceActive = true;
      startListening({ fromKey: true });
    });
    document.addEventListener("keyup", (ev) => {
      if (!(ev.key === " " || ev.code === "Space")) return;
      if (!_spaceActive) return;
      _spaceActive = false;
      ev.preventDefault();
      stopListening();
    });
  }

  // ---------------- Init ----------------
  async function init() {
    wire();
    setStatusDot("loading…", "#8794b4");
    setTurnIndicator("waiting", "loading …");
    setButtonsEnabled(false);
    await resolveSlot();
    connectWS();
    // H2: fetch copilot session state once bound.
    if (playerId) await fetchCopilotState();
    // Poll /state every 5s as a keepalive fallback (WS is authoritative)
    setInterval(async () => {
      try {
        const r = await fetch("/state");
        const s = await r.json();
        if (s.day !== undefined) els.dayLabel.textContent = `Day ${s.day}`;
        if (s.tick !== undefined) els.tickLabel.textContent = `Tick ${s.tick}`;
      } catch (err) {
        /* ignore */
      }
    }, 5000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
