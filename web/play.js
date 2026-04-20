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
    } catch (err) {
      console.error("refreshObservation failed", err);
    }
  }

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
      buildArgs: (v) => ({ to: parseInt(v.to, 10) }),
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
      buildArgs: (v) => ({ to: parseInt(v.to, 10) }),
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
      buildArgs: (v) => ({ to: v.to_player, message: v.message }),
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
  };

  const copilotState = {
    mode: "advisory",
    pendingPlan: null,
    activeTask: null,
    orders: [],
    seenMessageIds: new Set(),
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
    copilotState.mode = mode;
    copilotEls.modePill.textContent = `mode: ${mode}`;
    document
      .querySelectorAll(".mode-btn")
      .forEach((b) => b.classList.toggle("is-active", b.dataset.mode === mode));
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
