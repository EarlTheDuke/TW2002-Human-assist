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
  };

  const state = {
    seat: localStorage.getItem("tw2k_bot_seat") || "P3",
    token: localStorage.getItem("tw2k_bot_token") || "",
    turnSeq: null,
    awaiting: false,
    obs: null,
    timer: null,
    busy: false,
    connected: false,
  };

  els.seat.value = state.seat;
  if (state.token) els.token.value = state.token;

  const params = new URLSearchParams(location.search);
  if (params.get("seat")) {
    state.seat = params.get("seat").toUpperCase();
    els.seat.value = state.seat;
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

  function setBanner(mode, text) {
    els.banner.className = `banner ${mode}`;
    els.banner.textContent = text;
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

    els.warps.innerHTML = "";
    const warps = sector.warps_out || [];
    const canAct = state.awaiting && !state.busy;
    warps.forEach((w) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = `WARP ${w}`;
      b.disabled = !canAct;
      b.addEventListener("click", () => submit({ kind: "warp", args: { target: Number(w) }, thought: `Grok Bot: warp to ${w}` }));
      els.warps.appendChild(b);
    });

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

  async function refresh() {
    if (!state.token) return;
    try {
      const st = await api(`/${state.seat}/status`);
      setErr("");
      state.awaiting = !!st.awaiting_input;
      state.turnSeq = st.turn_seq;
      if (st.match_status === "finished" || st.match_status === "error") {
        setBanner("dead", `MATCH ${String(st.match_status).toUpperCase()}`);
        setActionsEnabled(false);
        return;
      }
      if (state.busy) {
        setBanner("busy", "SUBMITTING…");
      } else if (state.awaiting) {
        setBanner("turn", `YOUR TURN  seq=${st.turn_seq}  day=${st.day}`);
        const r = await api(`/${state.seat}/observation?wait_s=2&format=json`);
        if (r.observation) render(r.observation, { last_result: st.last_result });
        state.turnSeq = r.turn_seq ?? state.turnSeq;
      } else {
        setBanner("idle", `WAITING  day=${st.day} tick=${st.tick}`);
        if (state.obs) render(state.obs, { last_result: st.last_result });
        else setActionsEnabled(false);
      }
      els.main.hidden = false;
    } catch (e) {
      setErr(String(e.message || e));
      setBanner("dead", "ERROR");
      setActionsEnabled(false);
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
    if (state.timer) clearInterval(state.timer);
    setErr("");
    refresh();
    state.timer = setInterval(refresh, 2500);
    log(`connected as ${state.seat}`);
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