/* Grok Bot cockpit - drives /harness/v1 for computer-use / hosted URL play. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const els = {
    banner: $("turnBanner"),
    err: $("err"),
    main: $("main"),
    seat: $("seatSelect"),
    token: $("tokenInput"),
    connect: $("connectBtn"),
    poll: $("pollBtn"),
    credits: $("vCredits"),
    sector: $("vSector"),
    turns: $("vTurns"),
    dayTick: $("vDayTick"),
    free: $("vFree"),
    ship: $("vShip"),
    rivals: $("rivals"),
    port: $("portLine"),
    hint: $("hint"),
    warps: $("warpBtns"),
    sell: $("sellBtn"),
    buy: $("buyBtn"),
    last: $("lastResult"),
    log: $("log"),
    whose: $("whoseTurn"),
  };

  const state = {
    seat: localStorage.getItem("tw2k_bot_seat") || "P3",
    token: localStorage.getItem("tw2k_bot_token") || "",
    turnSeq: null,
    awaiting: false,
    obs: null,
    busy: false,
    connected: false,
    // Phase D: scheduler view + countdown.
    current: null,        // current_turn from /status: {player_id,name,kind,deadline_at,...}
    clockSkew: 0,         // server_time - Date.now()/1000
    matchStatus: "",
    day: null,
    tick: null,
    lastResult: null,
    watchGen: 0,          // bump to cancel an in-flight watch loop (reconnect)
    tickTimer: null,
  };

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const nowS = () => Date.now() / 1000 + state.clockSkew;

  // The dropdown ships with the canonical P3-P5 names, but any seat id from the
  // URL / localStorage must be selectable, otherwise Connect silently falls
  // back to the first option (observed with ?seat=P2 during Phase D).
  function ensureSeatOption(seat) {
    const s = String(seat || "").toUpperCase();
    if (!s) return;
    if (![...els.seat.options].some((o) => o.value === s)) {
      const o = document.createElement("option");
      o.value = s;
      o.textContent = s;
      els.seat.appendChild(o);
    }
    els.seat.value = s;
  }

  ensureSeatOption(state.seat);
  if (state.token) els.token.value = state.token;

  const params = new URLSearchParams(location.search);
  if (params.get("seat")) {
    state.seat = params.get("seat").toUpperCase();
    ensureSeatOption(state.seat);
  }
  if (params.get("token")) {
    state.token = params.get("token");
    els.token.value = state.token;
    // Strip token from URL bar after capture (stay on ?seat=).
    params.delete("token");
    const q = params.toString();
    history.replaceState(null, "", location.pathname + (q ? "?" + q : ""));
  }

  function log(msg) {
    const line = document.createElement("div");
    line.textContent = `${new Date().toLocaleTimeString()}  ${msg}`;
    els.log.prepend(line);
  }

  function setErr(msg) {
    const t = msg || "";
    els.err.textContent = t;
    els.err.classList.toggle("visible", !!t);
  }

  function classifyError(status, detail) {
    const d = String(detail || "");
    if (status === 401 || /unauthorized|invalid.?token|forbidden/i.test(d)) {
      return "Auth failed (401). Re-paste the seat token and Connect.";
    }
    if (status === 409 || /stale|turn_seq|sequence/i.test(d)) {
      return "Stale turn_seq. Wait for YOUR TURN, then try again (Refresh).";
    }
    if (status === 408 || status === 504 || /timeout/i.test(d)) {
      return "Timeout waiting on harness. Refresh; match may be on another seat.";
    }
    return `${status} ${d}`.trim();
  }

  function headers() {
    return { Authorization: `Bearer ${state.token}`, "Content-Type": "application/json" };
  }

  async function api(path, opts = {}) {
    let r;
    try {
      r = await fetch(`/harness/v1${path}`, {
        ...opts,
        headers: { ...headers(), ...(opts.headers || {}) },
      });
    } catch (net) {
      throw new Error("Network error talking to harness (is the host up?)");
    }
    const text = await r.text();
    let data;
    try { data = text ? JSON.parse(text) : {}; } catch { data = { raw: text }; }
    if (!r.ok) {
      const detail = data.detail || data.code || data.message || text.slice(0, 200);
      throw new Error(classifyError(r.status, detail));
    }
    return data;
  }

  function setBanner(mode, text, sub, flash) {
    els.banner.className = `banner ${mode}${flash ? " flash" : ""}`;
    els.banner.textContent = text;
    if (sub) {
      const who = document.createElement("span");
      who.className = "who";
      who.textContent = sub;
      els.banner.appendChild(who);
    }
  }

  function describeCurrent(ct) {
    if (!ct || !ct.player_id) return "scheduler idle";
    const kind = ct.kind || "?";
    const who = `${ct.player_id} ${ct.name || ""}`.trim();
    if (ct.player_id === state.seat) return `${who} (you)`;
    let s = `${who} (${kind})`;
    if (kind === "external") s += ct.attended === false ? " - no bot attached" : " - bot attached";
    return s;
  }

  function countdownText(ct) {
    if (!ct || !ct.deadline_at) return "";
    const rem = Math.max(0, Math.round(ct.deadline_at - nowS()));
    return `${rem}s`;
  }

  // Re-render the WAITING banner every second so the countdown moves between polls.
  function renderIdleBanner() {
    if (state.busy || state.awaiting) return;
    if (state.matchStatus === "finished" || state.matchStatus === "error") return;
    const ct = state.current;
    const cd = countdownText(ct);
    const head = `WAITING  day=${state.day ?? "-"} tick=${state.tick ?? "-"}`;
    const sub = `${describeCurrent(ct)}${cd ? "  ·  " + cd : ""}`;
    setBanner("idle", head, sub);
    if (els.whose) els.whose.textContent = `${describeCurrent(ct)}${cd ? "\ndeadline in " + cd : ""}`;
  }

  function startTicker() {
    if (state.tickTimer) clearInterval(state.tickTimer);
    state.tickTimer = setInterval(renderIdleBanner, 1000);
  }

  function setActionsEnabled(on) {
    document.querySelectorAll("#actionBtns [data-kind]").forEach((btn) => {
      btn.disabled = !on;
    });
    els.sell.disabled = !on;
    els.buy.disabled = !on;
    els.warps.querySelectorAll("button").forEach((b) => { b.disabled = !on; });
  }

  function render(obs, meta) {
    state.obs = obs;
    const sector = obs.sector || {};
    const ship = obs.ship || {};
    const port = sector.port || null;
    els.credits.textContent = Number(obs.credits || 0).toLocaleString();
    els.sector.textContent = String(sector.id ?? "-");
    els.turns.textContent = String(obs.turns_remaining ?? "-");
    els.dayTick.textContent = `${obs.day ?? "-"} / ${obs.tick ?? "-"}`;
    els.free.textContent = String(ship.cargo_free ?? "-");
    els.ship.textContent = ship.class || "-";
    if (port) {
      els.port.textContent = `buys=${(port.buys || []).join(",") || "-"}  sells=${(port.sells || []).join(",") || "-"}  code=${port.code || "?"}`;
    } else {
      els.port.textContent = "No port in this sector";
    }
    els.hint.textContent = obs.action_hint || "(no hint)";

    const rivals = obs.rivals || obs.other_players || [];
    if (els.rivals) {
      if (Array.isArray(rivals) && rivals.length) {
        els.rivals.textContent = "Rivals: " + rivals.map((r) => {
          if (typeof r === "string") return r;
          return `${r.id || r.name || "?"}@${r.sector ?? "?"}`;
        }).join(" | ");
      } else {
        els.rivals.textContent = "";
      }
    }

    const warps = sector.warps_out || [];
    const canAct = state.awaiting && !state.busy;
    // Phase D P1: only rebuild the warp buttons when the warp list changes.
    // Recreating them on every poll replaced the DOM node under a
    // computer-use click between "snapshot" and "click", so clicks missed.
    const warpKey = warps.join(",");
    if (els.warps.getAttribute("data-warp-key") !== warpKey) {
      els.warps.innerHTML = "";
      warps.forEach((w) => {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = `WARP ${w}`;
        b.setAttribute("data-testid", `warp-${w}`);
        b.setAttribute("data-target", String(w));
        b.addEventListener("click", () => submit({ kind: "warp", args: { target: Number(w) }, thought: `Grok Bot: warp to ${w}` }));
        els.warps.appendChild(b);
      });
      els.warps.setAttribute("data-warp-key", warpKey);
    }
    els.warps.querySelectorAll("button").forEach((b) => { b.disabled = !canAct; });

    const cargo = ship.cargo || {};
    const buys = (port && port.buys) || [];
    const sells = (port && port.sells) || [];
    let canSell = null;
    for (const c of buys) {
      if ((cargo[c] || 0) > 0) { canSell = { c, q: cargo[c] }; break; }
    }
    els.sell.hidden = !canSell;
    els.sell.disabled = !canAct;
    els.sell.onclick = () => {
      if (!canSell || !canAct) return;
      submit({ kind: "trade", args: { commodity: canSell.c, qty: canSell.q, side: "sell" }, thought: `Grok Bot: sell ${canSell.q} ${canSell.c}` });
    };
    const free = ship.cargo_free || 0;
    els.buy.hidden = !(sells.length && free > 0 && (obs.credits || 0) > 500);
    els.buy.disabled = !canAct;
    els.buy.onclick = () => {
      if (!canAct) return;
      const c = sells[0];
      const q = Math.min(free, 15);
      submit({ kind: "trade", args: { commodity: c, qty: q, side: "buy" }, thought: `Grok Bot: buy ${q} ${c}` });
    };

    setActionsEnabled(canAct);

    if (meta && meta.last_result) {
      els.last.textContent = typeof meta.last_result === "string"
        ? meta.last_result
        : JSON.stringify(meta.last_result);
    }
  }

  // Apply a /status or /observation payload (both carry the same status fields).
  function applyStatus(st) {
    if (typeof st.server_time === "number") state.clockSkew = st.server_time - Date.now() / 1000;
    state.matchStatus = st.match_status || "";
    state.day = st.day; state.tick = st.tick;
    state.current = st.current_turn || null;
    state.lastResult = st.last_result || state.lastResult;
    const wasAwaiting = state.awaiting;
    state.awaiting = !!st.awaiting_input;
    state.turnSeq = st.turn_seq ?? state.turnSeq;

    if (state.matchStatus === "finished" || state.matchStatus === "error") {
      setBanner("dead", `MATCH ${state.matchStatus.toUpperCase()}`);
      setActionsEnabled(false);
      return;
    }
    if (state.busy) { setBanner("busy", "SUBMITTING…"); return; }

    if (state.awaiting) {
      const flash = !wasAwaiting;
      setBanner("turn", `YOUR TURN  seq=${state.turnSeq}  day=${state.day}`,
        state.current && state.current.deadline_at ? `respond within ${countdownText(state.current)}` : "", flash);
      if (els.whose) els.whose.textContent = `${state.seat} (you) - act now`;
      if (flash) log(`YOUR TURN (seq ${state.turnSeq})`);
      if (st.observation) render(st.observation, { last_result: state.lastResult });
      else if (state.obs) render(state.obs, { last_result: state.lastResult });
    } else {
      renderIdleBanner();
      if (state.obs) render(state.obs, { last_result: state.lastResult });
      else setActionsEnabled(false);
      if (wasAwaiting) log(`turn ${state.turnSeq} closed; waiting on ${describeCurrent(state.current)}`);
    }
    els.main.hidden = false;
  }

  // One-shot status fetch (Refresh button + fallback).
  async function refresh() {
    if (!state.token) return;
    try {
      const st = await api(`/${state.seat}/status`);
      setErr("");
      if (st.awaiting_input && !state.obs) {
        const r = await api(`/${state.seat}/observation?wait_s=0&format=json`);
        applyStatus(r);
      } else {
        applyStatus(st);
      }
    } catch (e) {
      setErr(String(e.message || e));
      setBanner("dead", "ERROR");
      setActionsEnabled(false);
    }
  }

  // Phase D: long-poll loop. While it's someone else's turn we block on
  // /observation?wait_s=20 so YOUR TURN flips the moment the scheduler reaches
  // this seat (no reload, no 2.5s polling). While it IS our turn we re-check
  // status every 1.5s so an expired turn (timeout) is noticed promptly.
  async function watchLoop(gen) {
    while (state.connected && gen === state.watchGen) {
      if (state.busy) { await sleep(250); continue; }
      try {
        if (state.awaiting) {
          const st = await api(`/${state.seat}/status`);
          if (gen !== state.watchGen) return;
          applyStatus(st);
          await sleep(1500);
        } else {
          const r = await api(`/${state.seat}/observation?wait_s=20&format=json`);
          if (gen !== state.watchGen) return;
          setErr("");
          applyStatus(r);
        }
      } catch (e) {
        if (gen !== state.watchGen) return;
        setErr(String(e.message || e));
        setBanner("dead", "ERROR - retrying");
        setActionsEnabled(false);
        await sleep(3000);
      }
    }
  }

  async function submit(action) {
    if (!state.awaiting || state.busy) return;
    state.busy = true;
    setActionsEnabled(false);
    setBanner("busy", "SUBMITTING…");
    setErr("");
    try {
      const seq = state.turnSeq;
      await api(`/${state.seat}/action`, {
        method: "POST",
        body: JSON.stringify({ turn_seq: seq, action }),
      });
      log(`${action.kind} posted (seq ${seq})`);
      state.awaiting = false;
      state.busy = false;
      await refresh();
    } catch (e) {
      setErr(String(e.message || e));
      log(`FAIL ${e.message || e}`);
      setBanner("dead", "ACTION FAILED");
    } finally {
      state.busy = false;
    }
  }

  els.connect.addEventListener("click", () => {
    state.seat = els.seat.value.toUpperCase();
    state.token = els.token.value.trim();
    if (!state.token) {
      setErr("Paste the harness bearer token first.");
      setBanner("idle", "PASTE TOKEN + CONNECT");
      return;
    }
    localStorage.setItem("tw2k_bot_seat", state.seat);
    localStorage.setItem("tw2k_bot_token", state.token);
    els.poll.disabled = false;
    state.connected = true;
    state.obs = null;
    state.awaiting = false;
    state.watchGen += 1;
    setErr("");
    log(`connected as ${state.seat}`);
    startTicker();
    refresh().then(() => watchLoop(state.watchGen));
  });
  els.poll.addEventListener("click", () => { setErr(""); refresh(); });

  document.querySelectorAll("#actionBtns [data-kind]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const kind = btn.getAttribute("data-kind");
      submit({ kind, args: {}, thought: `Grok Bot: ${kind}` });
    });
  });

  if (state.token) {
    els.poll.disabled = false;
    els.connect.click();
  } else {
    setBanner("idle", "PASTE TOKEN + CONNECT");
    setActionsEnabled(false);
  }
})();