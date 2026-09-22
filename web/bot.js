/* Grok Bot cockpit - drives /harness/v1 for computer-use / hosted URL play.
 *
 * Parity S2: every panel is a pure render of the authoritative Observation
 * (peeked between turns via ?peek=1) plus the fogged /events stream. No game
 * truth is derived client-side; arithmetic here only formats numbers the
 * server already sent. Elements carry data-obs="<Observation key>" so tests
 * can prove every key has a home.
 */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const els = {
    banner: $("turnBanner"),
    err: $("err"),
    main: $("main"),
    scoreboard: $("scoreboard"),
    eventsFooter: $("eventsFooter"),
    seat: $("seatSelect"),
    token: $("tokenInput"),
    connect: $("connectBtn"),
    poll: $("pollBtn"),
    whose: $("whoseTurn"),
    warps: $("warpBtns"),
    sell: $("sellBtn"),
    buy: $("buyBtn"),
    last: $("lastResult"),
    lastJson: $("lastResultJson"),
    hint: $("hint"),
    failures: $("failures"),
    goals: $("goals"),
    scratchpad: $("scratchpad"),
    operatorDirective: $("operatorDirective"),
    rawObs: $("rawObs"),
    log: $("log"),
    eventLog: $("eventLog"),
    eventsMeta: $("eventsMeta"),
    eventFilters: $("eventFilters"),
  };

  const state = {
    seat: localStorage.getItem("tw2k_bot_seat") || "P3",
    token: localStorage.getItem("tw2k_bot_token") || "",
    turnSeq: null,
    awaiting: false,
    obs: null,
    obsIsPeek: false,
    busy: false,
    connected: false,
    current: null,
    clockSkew: 0,
    matchStatus: "",
    day: null,
    tick: null,
    lastResult: null,
    lastAction: null,
    watchGen: 0,
    tickTimer: null,
    events: [],          // fogged EventViews from /events, ascending seq
    eventsSince: 0,
    eventFilter: "all",
    lastSeenSeq: 0,      // for the "new since your last turn" highlight
    legal: {},           // S3: kind -> LegalAction from the Observation
    openVerb: null,
    openPrefill: null,
  };

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const nowS = () => Date.now() / 1000 + state.clockSkew;
  const fmt = (n) => (n === null || n === undefined || n === "" ? "-" : Number(n).toLocaleString());
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const COMMODITIES = ["fuel_ore", "organics", "equipment"];
  const SHORT = { fuel_ore: "Fuel", organics: "Org", equipment: "Equip", colonists: "Colonists" };

  // ---------------------------------------------------------------- seat
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
    params.delete("token");
    const q = params.toString();
    history.replaceState(null, "", location.pathname + (q ? "?" + q : ""));
  }

  // ---------------------------------------------------------------- infra
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
    const d = typeof detail === "string" ? detail : JSON.stringify(detail || "");
    if (status === 401 || /unauthorized|invalid.?token|forbidden/i.test(d)) return "Auth failed (401). Re-paste the seat token and Connect.";
    if (status === 409 && /stale_turn/.test(d)) return "Stale turn_seq. The turn moved on; wait for YOUR TURN.";
    if (status === 409 && /not_awaiting/.test(d)) return "Not your turn yet.";
    if (status === 409) return `Conflict: ${d}`;
    if (status === 408 || status === 504 || /timeout/i.test(d)) return "Timeout waiting on harness. Refresh; match may be on another seat.";
    return `${status} ${d}`.trim();
  }
  function headers() {
    return { Authorization: `Bearer ${state.token}`, "Content-Type": "application/json" };
  }
  async function api(path, opts = {}) {
    let r;
    try {
      r = await fetch(`/harness/v1${path}`, { ...opts, headers: { ...headers(), ...(opts.headers || {}) } });
    } catch (net) {
      throw new Error("Network error talking to harness (is the host up?)");
    }
    const text = await r.text();
    let data;
    try { data = text ? JSON.parse(text) : {}; } catch { data = { raw: text }; }
    if (!r.ok) throw new Error(classifyError(r.status, data.detail || data.code || data.message || text.slice(0, 200)));
    return data;
  }

  // ---------------------------------------------------------------- banner
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
    return `${Math.max(0, Math.round(ct.deadline_at - nowS()))}s`;
  }
  function renderIdleBanner() {
    if (state.busy || state.awaiting) return;
    if (state.matchStatus === "finished" || state.matchStatus === "error") return;
    const ct = state.current;
    const cd = countdownText(ct);
    setBanner("idle", `WAITING  day=${state.day ?? "-"} tick=${state.tick ?? "-"}`, `${describeCurrent(ct)}${cd ? "  ·  " + cd : ""}`);
    if (els.whose) els.whose.textContent = `${describeCurrent(ct)}${cd ? "\ndeadline in " + cd : ""}${state.obsIsPeek ? "\n(panels show a live peek of your seat)" : ""}`;
  }
  function startTicker() {
    if (state.tickTimer) clearInterval(state.tickTimer);
    state.tickTimer = setInterval(renderIdleBanner, 1000);
  }

  // ---------------------------------------------------------------- helpers
  function setText(id, v) { const el = $(id); if (el) el.textContent = v === null || v === undefined || v === "" ? "-" : String(v); }
  function kv(el, pairs) {
    el.innerHTML = "";
    for (const [k, v] of pairs) {
      const a = document.createElement("span"); a.className = "k"; a.textContent = k;
      const b = document.createElement("span"); b.className = "v"; b.textContent = v === null || v === undefined || v === "" ? "-" : String(v);
      el.appendChild(a); el.appendChild(b);
    }
  }
  function rows(el, items, render, emptyText) {
    el.innerHTML = "";
    if (!items || !items.length) {
      const d = document.createElement("div"); d.className = "row"; d.innerHTML = `<span class="m">${esc(emptyText || "none")}</span>`;
      el.appendChild(d);
      return;
    }
    for (const it of items) el.appendChild(render(it));
  }
  function row(title, metas, cls) {
    const d = document.createElement("div");
    d.className = `row${cls ? " " + cls : ""}`;
    const t = document.createElement("span"); t.className = "t"; t.textContent = title; d.appendChild(t);
    for (const m of metas.filter((x) => x !== null && x !== undefined && x !== "")) {
      const s = document.createElement("span"); s.className = "m"; s.textContent = m; d.appendChild(s);
    }
    return d;
  }
  function tbody(tableId) { const t = $(tableId); const b = t.querySelector("tbody"); b.innerHTML = ""; return b; }
  function td(tr, text, cls) { const c = document.createElement("td"); if (cls) c.className = cls; c.textContent = text; tr.appendChild(c); return c; }
  function emptyRow(b, cols, text) { const tr = document.createElement("tr"); tr.className = "empty"; const c = document.createElement("td"); c.colSpan = cols; c.textContent = text; tr.appendChild(c); b.appendChild(tr); }
  const sideWord = (side) => (side === "buys_from_player" ? "BUYS" : side === "sells_to_player" ? "SELLS" : side === "not_traded" ? "no trade" : "-");

  // ---------------------------------------------------------------- panels
  function renderScoreboard(obs) {
    setText("sbName", `${obs.self_name || ""} (${obs.self_id || ""})`);
    setText("sbDay", obs.day); setText("sbMaxDays", obs.max_days); setText("sbTick", obs.tick);
    setText("sbTurns", obs.turns_remaining); setText("sbTpd", obs.turns_per_day);
    setText("sbCredits", fmt(obs.credits)); setText("sbNetWorth", fmt(obs.net_worth));
    setText("sbRank", obs.rank); setText("sbXp", fmt(obs.experience));
    setText("sbAlignLabel", obs.alignment_label); setText("sbAlign", obs.alignment);
    setText("sbDeaths", obs.deaths); setText("sbMaxDeaths", obs.max_deaths);
    setText("sbAlive", obs.alive === false ? "DESTROYED" : "");
    setText("sbCorp", obs.corp_ticker || "none");
    setText("sbLanded", obs.planet_landed === null || obs.planet_landed === undefined ? "in space" : `planet ${obs.planet_landed}`);
    setText("sbFinished", obs.finished ? "finished" : "");
    els.scoreboard.hidden = false;
  }

  function renderHere(obs) {
    const s = obs.sector || {};
    setText("hereId", s.id);
    $("hereFed").hidden = !s.is_fedspace;
    kv($("hereFacts"), [
      ["Warps out", `${(s.warps_out || []).join(", ") || "-"}  (${s.warps_count ?? (s.warps_out || []).length})`],
      ["FedSpace", s.is_fedspace ? "yes - no PvP, StarDock is sector 1" : "no"],
    ]);
    const occ = (s.occupants || []).filter((o) => o !== obs.self_id);
    const chips = $("hereOccupants"); chips.innerHTML = "";
    if (!occ.length) chips.innerHTML = `<span class="chip static">nobody else here</span>`;
    for (const o of occ) { const c = document.createElement("span"); c.className = "chip static"; c.textContent = o; chips.appendChild(c); }
    const def = [];
    if (s.fighter_group) def.push(["Fighters", `${fmt(s.fighter_group.count)} (${s.fighter_group.mode}) owner ${s.fighter_group.owner_id}`]);
    for (const m of s.mines || []) def.push([`Mines (${m.kind})`, `${fmt(m.count)} owner ${m.owner}`]);
    if (!def.length) def.push(["Defenses", "none seen"]);
    kv($("hereDefenses"), def);
    rows($("herePlanets"), s.planets || [], (p) => row(`${p.name} [${p.class}]`, [
      `id ${p.id}`, p.owner_id ? `owner ${p.owner_id}` : "unowned", `citadel L${p.citadel_level}`,
      p.fighters ? `${fmt(p.fighters)} fighters` : null, p.colonists_total ? `${fmt(p.colonists_total)} colonists` : null,
    ]), "no planets here");
    rows($("hereFerrengi"), s.ferrengi || [], (f) => row(f.name || f.id, [`aggression ${f.aggression}`, `${fmt(f.fighters)} fighters`], "bad"), "none");
  }

  function renderPort(obs) {
    const s = obs.sector || {};
    const port = s.port;
    const cargo = (obs.ship && obs.ship.cargo) || {};
    const b = tbody("portTape");
    if (!port) {
      setText("portCode", "none");
      kv($("portMeta"), []);
      $("portNone").hidden = false;
      $("portTape").hidden = true;
      return;
    }
    $("portNone").hidden = true;
    $("portTape").hidden = false;
    setText("portCode", port.code);
    kv($("portMeta"), [["Name", port.name], ["Class", port.class_id], ["Buys", (port.buys || []).join(", ") || "-"], ["Sells", (port.sells || []).join(", ") || "-"]]);
    const stock = port.stock || {};
    let any = false;
    for (const c of COMMODITIES) {
      const st = stock[c];
      if (!st) continue;
      any = true;
      const tr = document.createElement("tr");
      tr.className = st.side === "buys_from_player" ? "buys" : st.side === "sells_to_player" ? "sells" : "empty";
      tr.setAttribute("data-testid", `port-row-${c}`);
      td(tr, c);
      td(tr, sideWord(st.side));
      td(tr, st.price === null || st.price === undefined ? "-" : `${fmt(st.price)} cr`, "num");
      td(tr, `${fmt(st.current)} / ${fmt(st.max)}`, "num");
      td(tr, fmt(cargo[c] || 0), "num");
      b.appendChild(tr);
    }
    if (!any) emptyRow(b, 5, port.class_id === 8 || /stardock/i.test(port.name || "") ? "StarDock: ships and equipment (S4 verbs)" : "no commodity stock reported");
  }

  function renderAdjacent(obs) {
    rows($("adjacentStrip"), obs.adjacent || [], (a) => row(`Sector ${a.id}`, [
      a.port ? `port ${a.port}` : "no port", a.known ? "known" : "unexplored",
      a.fighter_count ? `${fmt(a.fighter_count)} fighters (${a.fighter_owner || "?"})` : null,
      a.mines ? `${fmt(a.mines)} mines` : null, a.has_planets ? "planets" : null,
      (a.occupants || []).length ? `occupants ${(a.occupants || []).join(", ")}` : null,
    ], a.known ? "" : "stale"), "no warps out");
    for (const [i, d] of [...$("adjacentStrip").children].entries()) {
      const a = (obs.adjacent || [])[i];
      if (a) d.setAttribute("data-testid", `adjacent-${a.id}`);
    }
  }

  function renderKnownWarps(obs) {
    const kw = obs.known_warps || {};
    const ids = Object.keys(kw).map(Number).sort((a, b) => a - b);
    setText("knownWarpsCount", `${ids.length} sectors`);
    const el = $("knownWarpsList");
    el.textContent = ids.length
      ? ids.map((sid) => `${sid} → ${(kw[String(sid)] || []).join(",")}`).join("   |   ")
      : "no map memory yet - scan or warp";
  }

  function renderShip(obs) {
    const sh = obs.ship || {};
    setText("shipClass", sh.class);
    kv($("shipLoadout"), [
      ["Holds", `${fmt(sh.holds)}  (${fmt(sh.cargo_free)} free)`],
      ["Fighters", `${fmt(sh.fighters)} / ${fmt(sh.fighter_cap)}`],
      ["Shields", `${fmt(sh.shields)} / ${fmt(sh.shield_cap)}`],
      ["Mines", Object.entries(sh.mines || {}).filter(([, n]) => n).map(([k, n]) => `${k} ${n}`).join(", ") || "none"],
      ["Genesis", sh.genesis], ["Photons", sh.photon_missiles], ["Probes", sh.ether_probes],
      ["Fighters offline", sh.photon_disabled_ticks ? `${sh.photon_disabled_ticks} ticks` : "no"],
    ]);
    const b = tbody("cargoTable");
    const cargo = sh.cargo || {};
    const avg = sh.cargo_cost_avg || {};
    const val = sh.cargo_value_at_cost || {};
    let any = false;
    for (const c of [...COMMODITIES, "colonists"]) {
      const q = cargo[c] || 0;
      if (!q) continue;
      any = true;
      const tr = document.createElement("tr");
      tr.setAttribute("data-testid", `cargo-row-${c}`);
      td(tr, c); td(tr, fmt(q), "num"); td(tr, avg[c] !== undefined ? `${fmt(avg[c])} cr` : "-", "num"); td(tr, val[c] !== undefined ? `${fmt(val[c])} cr` : "-", "num");
      b.appendChild(tr);
    }
    if (!any) emptyRow(b, 4, "holds empty");
  }

  function renderKnownPorts(obs) {
    const kp = obs.known_ports || [];
    setText("knownPortsCount", kp.length);
    const b = tbody("knownPortsTable");
    if (!kp.length) { emptyRow(b, 6, "no ports visited yet"); return; }
    const sorted = [...kp].sort((x, y) => (x.age_days ?? 999) - (y.age_days ?? 999) || x.sector_id - y.sector_id);
    for (const p of sorted) {
      const tr = document.createElement("tr");
      tr.setAttribute("data-testid", `known-port-${p.sector_id}`);
      if ((p.age_days ?? 0) > 2) tr.className = "stale";
      td(tr, p.sector_id === (obs.sector || {}).id ? `${p.sector_id} (here)` : String(p.sector_id));
      td(tr, p.class || "?");
      td(tr, p.age_days === undefined ? "-" : p.age_days === 0 ? "today" : `${p.age_days}d`);
      for (const c of COMMODITIES) {
        const st = (p.stock || {})[c];
        if (!st) { td(tr, "-", "num"); continue; }
        const side = st.side === "buys_from_player" ? "B" : st.side === "sells_to_player" ? "S" : "";
        td(tr, `${side}${side ? " " : ""}${st.price !== undefined ? fmt(st.price) : "?"}`, "num").title = `${sideWord(st.side)} · stock ${fmt(st.current)}/${fmt(st.max)}`;
      }
      b.appendChild(tr);
    }
  }

  function renderTrade(obs) {
    const ts = obs.trade_summary || {};
    kv($("tradeSummary"), [
      ["Trades", `${fmt(ts.total_trades)} (${fmt(ts.sells)} sells)`],
      ["Realized P&L", `${fmt(ts.total_profit_cr)} cr`],
      ["Avg margin", ts.avg_margin_pct !== undefined ? `${ts.avg_margin_pct}%` : "-"],
      ["Haggle wins", ts.haggle_win_rate_pct !== undefined ? `${ts.haggle_win_rate_pct}%` : "-"],
      ["Best", ts.best_pair ? `${ts.best_pair.commodity} ${fmt(ts.best_pair.total_profit_cr)} cr` : "-"],
      ["Worst", ts.worst_pair ? `${ts.worst_pair.commodity} ${fmt(ts.worst_pair.total_profit_cr)} cr` : "-"],
    ]);
    const b = tbody("tradeLog");
    const tl = obs.trade_log || [];
    if (!tl.length) { emptyRow(b, 6, "no trades yet"); return; }
    for (const t of [...tl].reverse().slice(0, 25)) {
      const tr = document.createElement("tr");
      td(tr, `${t.day}.${t.tick}`); td(tr, String(t.sector_id)); td(tr, `${t.side} ${t.qty} ${SHORT[t.commodity] || t.commodity}`);
      td(tr, fmt(t.unit), "num"); td(tr, fmt(t.total), "num");
      const pl = td(tr, t.realized_profit === null || t.realized_profit === undefined ? "-" : `${t.realized_profit >= 0 ? "+" : ""}${fmt(t.realized_profit)}`, "num");
      if (t.realized_profit > 0) pl.style.color = "var(--go)"; else if (t.realized_profit < 0) pl.style.color = "var(--danger)";
      b.appendChild(tr);
    }
  }

  function renderCommanders(obs) {
    rows($("rivals"), obs.rivals || [], (r) => row(`${r.name} (${r.id})`, [
      r.alive ? null : "ELIMINATED", `NW ${fmt(r.net_worth)}`, r.ship_class, r.corp_ticker ? `corp ${r.corp_ticker}` : null,
      r.last_seen_sector !== undefined ? `last seen sector ${r.last_seen_sector} day ${r.last_seen_day}` : "location unknown",
      r.deaths ? `${r.deaths} deaths` : null,
    ], r.alive ? "" : "stale"), "no rivals");
    rows($("otherPlayers"), (obs.other_players || []).filter((o) => o.is_corpmate), (o) => row(`Corpmate ${o.name}`, [
      `sector ${o.sector_id}`, `${fmt(o.credits)} cr`, o.ship_class, `${fmt(o.fighters)} fighters`,
    ]), "no corpmates");
  }

  function renderPlanets(obs) {
    rows($("ownedPlanets"), obs.owned_planets || [], (p) => row(`${p.name} [${p.class}]`, [
      `sector ${p.sector_id}`, `citadel L${p.citadel_level}${p.citadel_target > p.citadel_level ? ` → L${p.citadel_target} day ${p.citadel_complete_day}` : ""}`,
      `${fmt(p.fighters)} fighters`, `${fmt(p.shields)} shields`,
    ]), "you own no planets");
    rows($("orphanedPlanets"), obs.orphaned_planets || [], (p) => row(`${p.name} [${p.class}]`, [
      `sector ${p.sector_id}`, `citadel L${p.citadel_level}`, `${fmt(p.fighters)} fighters`, `was ${p.former_owner_id}`,
    ]), "none known");
  }

  function renderComms(obs) {
    const inbox = obs.inbox || [];
    setText("inboxCount", inbox.length);
    rows($("inbox"), [...inbox].reverse().slice(0, 20), (m) => row(`${m.kind || "msg"} from ${m.from}`, [
      m.day !== undefined ? `day ${m.day}${m.tick !== undefined ? "." + m.tick : ""}` : null, m.ticker ? `[${m.ticker}]` : null, m.message,
    ]), "inbox empty");
    rows($("alliances"), obs.alliances || [], (a) => row(`Alliance ${a.id}`, [
      a.active ? "active" : "proposed", `members ${(a.members || []).join(", ")}`, `by ${a.proposed_by}`, a.formed_day !== undefined && a.formed_day !== null ? `day ${a.formed_day}` : null,
    ]), "no alliances");
    const c = obs.corp;
    kv($("corp"), c ? [
      ["Corp", `${c.name} [${c.ticker}]`], ["CEO", c.ceo_id], ["Members", (c.members || []).join(", ")],
      ["Treasury", `${fmt(c.treasury)} cr (your share ${fmt(c.treasury_share)})`], ["Planets", (c.planet_ids || []).length],
    ] : [["Corp", "none"]]);
  }

  function renderIntel(obs) {
    rows($("limpets"), obs.limpets_owned || [], (l) => row(`Limpet on ${l.target_name || l.target_id}`, [
      l.current_sector !== null && l.current_sector !== undefined ? `now in sector ${l.current_sector}` : null, `placed day ${l.placed_day}`,
    ]), "no limpets attached");
    rows($("probeLog"), obs.probe_log || [], (p) => row(`Sector ${p.sector_id}`, [
      p.port_code ? `port ${p.port_code}` : "no port", p.day !== undefined ? `day ${p.day}` : null,
      p.fighters_count ? `${fmt(p.fighters_count)} fighters` : null, (p.occupants || []).length ? `occupants ${p.occupants.join(", ")}` : null,
    ]), "no probes launched");
  }

  function renderAdvisor(obs) {
    els.hint.textContent = obs.action_hint || "(no hint)";
    rows(els.failures, obs.recent_failures || [], (f) => row(`${f.target_label}`, [`${f.count}× failed`, `last day ${f.last_day}.${f.last_tick}`, f.last_summary], "bad"), "no repeated failures");
    const g = obs.goals || {};
    kv(els.goals, [["Short", g.short], ["Medium", g.medium], ["Long", g.long]]);
    els.scratchpad.textContent = obs.scratchpad || "(empty)";
    els.operatorDirective.textContent = obs.operator_directive ? `Operator directive: ${obs.operator_directive}` : "";
    els.rawObs.textContent = JSON.stringify(obs, null, 2);
  }

  // ---------------------------------------------------------------- legality (S3)
  // Everything below reads state.legal = { kind: LegalAction } straight from the
  // Observation. No rule lives here: if the engine says a verb is blocked we show
  // the button disabled with the engine's reason; if it says legal we offer the
  // engine's own parameter envelope (choices / min / max / listed prices).
  const S3_VERBS = ["warp", "scan", "wait", "trade", "plot_course", "probe"];
  function legalOf(kind) { return (state.legal && state.legal[kind]) || { kind, legal: false, reason: "no legality data", params: {} }; }
  function canUse(kind) { return state.awaiting && !state.busy && !!legalOf(kind).legal; }

  function renderVerbPad(obs) {
    state.legal = {};
    for (const la of obs.legal_actions || []) state.legal[la.kind] = la;
    const reasons = [];
    $("verbPad").querySelectorAll("button[data-verb]").forEach((btn) => {
      const kind = btn.getAttribute("data-verb");
      const la = legalOf(kind);
      btn.setAttribute("data-legal", la.legal ? "true" : "false");
      btn.setAttribute("data-detail", la.detail || "");
      if (la.legal) { btn.removeAttribute("data-reason"); btn.title = `${kind} · ${la.turn_cost || 0} turn(s)`; }
      else { btn.setAttribute("data-reason", la.reason || "not legal now"); btn.title = la.reason || "not legal now"; reasons.push(`${kind.toUpperCase()}: ${la.reason || "not legal now"}`); }
      btn.disabled = !canUse(kind);
      btn.classList.toggle("selected", state.openVerb === kind);
    });
    // Warp chips are the warp verb's form; gate them from legal_actions.warp.
    const warp = legalOf("warp");
    const warps = (warp.params && warp.params.target && warp.params.target.choices) || [];
    const warpKey = warps.join(",");
    if (els.warps.getAttribute("data-warp-key") !== warpKey) {
      els.warps.innerHTML = "";
      warps.forEach((w) => {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = `WARP ${w}`;
        b.setAttribute("data-testid", `warp-${w}`);
        b.setAttribute("data-target", String(w));
        b.addEventListener("click", () => { if (canUse("warp")) submit({ kind: "warp", args: { target: Number(w) }, thought: `Grok Bot: warp to ${w}` }); });
        els.warps.appendChild(b);
      });
      els.warps.setAttribute("data-warp-key", warpKey);
    }
    els.warps.querySelectorAll("button").forEach((b) => {
      b.disabled = !canUse("warp");
      if (!warp.legal) b.setAttribute("data-reason", warp.reason || ""); else b.removeAttribute("data-reason");
    });
    if (!warp.legal && warp.reason && !warps.length) reasons.push(`WARP: ${warp.reason}`);

    // Quick trade shortcuts: prefilled forms, gated by the trade envelope.
    const trade = legalOf("trade");
    const tp = trade.params || {};
    const sellChoices = (tp.commodity && tp.commodity.sell_choices) || [];
    const buyChoices = (tp.commodity && tp.commodity.buy_choices) || [];
    els.sell.hidden = !(trade.legal && sellChoices.length);
    els.buy.hidden = !(trade.legal && buyChoices.length);
    if (!els.sell.hidden) { const c = sellChoices[0]; els.sell.textContent = `SELL ${SHORT[c] || c}`; els.sell.onclick = () => openVerb("trade", { side: "sell", commodity: c }); }
    if (!els.buy.hidden) { const c = buyChoices[0]; els.buy.textContent = `BUY ${SHORT[c] || c}`; els.buy.onclick = () => openVerb("trade", { side: "buy", commodity: c }); }
    els.sell.disabled = !canUse("trade"); els.buy.disabled = !canUse("trade");

    rows($("verbReasons"), reasons, (r) => row(r, [], "stale"), state.awaiting ? "all shown verbs are legal now" : "waiting for your turn - buttons enable when the scheduler reaches you");
    // Coarse / S4 verbs: visible, disabled, with the engine's reason.
    const more = $("moreVerbs"); more.innerHTML = "";
    for (const la of obs.legal_actions || []) {
      if (S3_VERBS.includes(la.kind)) continue;
      const c = document.createElement("button");
      c.type = "button"; c.className = "chip"; c.disabled = true;
      c.setAttribute("data-testid", `verb-${la.kind}`);
      c.setAttribute("data-legal", la.legal ? "true" : "false");
      c.setAttribute("data-reason", la.legal ? "form arrives in S4" : (la.reason || "not legal now"));
      c.title = c.getAttribute("data-reason");
      c.textContent = `${la.kind}${la.legal ? " ✓" : ""}`;
      more.appendChild(c);
    }
    // Keep an open form stable across polls: only rebuild when the engine's
    // envelope for that verb changed (otherwise typed values and CU refs would
    // be wiped every 1.5 s). Enabled/disabled state is refreshed separately.
    if (state.openVerb) {
      const env = JSON.stringify(legalOf(state.openVerb));
      if (env !== state.openVerbEnvelope) renderVerbForm(state.openVerb, state.openPrefill || {});
      else { const go = $("verbForm").querySelector("button.primary"); if (go) go.disabled = !canUse(state.openVerb); }
    }
  }

  function setActionsEnabled(on) {
    $("verbPad").querySelectorAll("button[data-verb]").forEach((btn) => { btn.disabled = !on || !legalOf(btn.getAttribute("data-verb")).legal; });
    els.sell.disabled = !on || !legalOf("trade").legal;
    els.buy.disabled = !on || !legalOf("trade").legal;
    els.warps.querySelectorAll("button").forEach((b) => { b.disabled = !on || !legalOf("warp").legal; });
    const go = $("verbForm").querySelector("button.primary");
    if (go) go.disabled = !on;
  }

  function openVerb(kind, prefill) {
    state.openVerb = kind;
    state.openPrefill = prefill || {};
    renderVerbForm(kind, state.openPrefill);
    $("verbPad").querySelectorAll("button[data-verb]").forEach((b) => b.classList.toggle("selected", b.getAttribute("data-verb") === kind));
  }
  function closeVerb() { state.openVerb = null; state.openPrefill = null; state.openVerbEnvelope = null; const f = $("verbForm"); f.hidden = true; f.innerHTML = ""; $("verbPad").querySelectorAll("button").forEach((b) => b.classList.remove("selected")); }

  function field(labelText, inputEl, testid) {
    const l = document.createElement("label");
    l.textContent = labelText;
    inputEl.setAttribute("data-testid", testid);
    l.appendChild(inputEl);
    return l;
  }
  function selectEl(name, choices, value) {
    const s = document.createElement("select"); s.name = name;
    for (const c of choices) { const o = document.createElement("option"); o.value = String(c); o.textContent = String(c); s.appendChild(o); }
    if (value !== undefined && value !== null) s.value = String(value);
    return s;
  }
  function numberEl(name, { min, max, value, placeholder }) {
    const i = document.createElement("input"); i.type = "number"; i.name = name; i.inputMode = "numeric";
    if (min !== undefined) i.min = String(min); if (max !== undefined) i.max = String(max);
    if (value !== undefined && value !== null) i.value = String(value); if (placeholder) i.placeholder = placeholder;
    return i;
  }

  function renderVerbForm(kind, prefill) {
    const f = $("verbForm");
    const la = legalOf(kind);
    const p = la.params || {};
    state.openVerbEnvelope = JSON.stringify(la);
    f.innerHTML = ""; f.hidden = false; f.setAttribute("data-verb", kind);
    const h = document.createElement("h3"); h.textContent = `${kind.replace("_", " ").toUpperCase()} · ${la.turn_cost || 0} turn(s)${la.legal ? "" : " · " + (la.reason || "not legal now")}`; f.appendChild(h);
    const preview = document.createElement("div"); preview.className = "preview"; preview.setAttribute("data-testid", "verb-preview");
    const buttons = document.createElement("div"); buttons.className = "buttons";
    const go = document.createElement("button"); go.type = "submit"; go.className = "primary"; go.setAttribute("data-testid", "verb-submit"); go.textContent = "CONFIRM";
    const cancel = document.createElement("button"); cancel.type = "button"; cancel.setAttribute("data-testid", "verb-cancel"); cancel.textContent = "Cancel"; cancel.onclick = closeVerb;
    buttons.appendChild(go); buttons.appendChild(cancel);
    let build = () => null;   // -> action or null; sets preview text

    if (kind === "trade") {
      const sides = (p.side && p.side.choices) || ["buy", "sell"];
      const buyC = (p.commodity && p.commodity.buy_choices) || [];
      const sellC = (p.commodity && p.commodity.sell_choices) || [];
      const maxBy = (p.qty && p.qty.max_by) || {};
      const listedBy = (p.unit_price && p.unit_price.listed_by) || {};
      const radios = document.createElement("div"); radios.className = "radios";
      let side = prefill.side || (sellC.length && !buyC.length ? "sell" : "buy");
      for (const s of sides) {
        const l = document.createElement("label"); const r = document.createElement("input"); r.type = "radio"; r.name = "side"; r.value = s; r.checked = s === side;
        r.setAttribute("data-testid", `trade-side-${s}`); r.disabled = s === "buy" ? !buyC.length : !sellC.length;
        l.appendChild(r); l.appendChild(document.createTextNode(s.toUpperCase())); radios.appendChild(l);
      }
      const sideWrap = document.createElement("label"); sideWrap.textContent = "Side"; sideWrap.appendChild(radios); f.appendChild(sideWrap);
      const commSel = selectEl("commodity", side === "buy" ? buyC : sellC, prefill.commodity);
      f.appendChild(field("Commodity", commSel, "trade-commodity"));
      const qty = numberEl("qty", { min: 1 }); f.appendChild(field("Quantity", qty, "trade-qty"));
      const price = numberEl("unit_price", {}); f.appendChild(field("Your price per unit (optional haggle; blank = list)", price, "trade-price"));
      const maxBtn = document.createElement("button"); maxBtn.type = "button"; maxBtn.textContent = "MAX"; maxBtn.setAttribute("data-testid", "trade-max");
      const sync = () => {
        const c = commSel.value; const mx = ((maxBy[c] || {})[side]) ?? 0; const listed = ((listedBy[c] || {})[side]);
        qty.max = String(mx); if (!qty.value || Number(qty.value) > mx) qty.value = String(mx);
        price.placeholder = listed !== undefined ? `list ${listed}` : "";
        const q = Number(qty.value) || 0; const unit = Number(price.value) || listed || 0;
        const basis = ((state.obs && state.obs.ship && state.obs.ship.cargo_cost_avg) || {})[c];
        let txt = `${side.toUpperCase()} ${q} ${c} @ ${unit} = ${fmt(q * unit)} cr (engine cap ${mx}; list ${listed ?? "?"})`;
        if (side === "sell" && basis !== undefined) txt += ` · cost basis ${basis} → est. ${fmt((unit - basis) * q)} cr`;
        if (price.value && listed !== undefined) { const off = side === "buy" ? (listed - unit) / listed : (unit - listed) / listed; if (off > 0) txt += ` · haggle ${Math.round(off * 100)}% off list - rejected asks settle at list price`; }
        preview.textContent = txt; preview.classList.toggle("warn", q <= 0 || q > mx);
      };
      radios.addEventListener("change", (e) => { side = e.target.value; const opts = side === "buy" ? buyC : sellC; commSel.innerHTML = ""; for (const c of opts) { const o = document.createElement("option"); o.value = c; o.textContent = c; commSel.appendChild(o); } qty.value = ""; sync(); });
      commSel.addEventListener("change", () => { qty.value = ""; sync(); }); qty.addEventListener("input", sync); price.addEventListener("input", sync);
      maxBtn.onclick = () => { qty.value = qty.max; sync(); };
      buttons.insertBefore(maxBtn, cancel);
      build = () => { const q = Number(qty.value) || 0; if (q <= 0 || q > Number(qty.max)) return null; const a = { kind: "trade", args: { commodity: commSel.value, qty: q, side }, thought: `Grok Bot: ${side} ${q} ${commSel.value}` }; if (price.value) a.args.unit_price = Number(price.value); return a; };
      sync();
    } else if (kind === "plot_course") {
      const suggested = (p.target && p.target.suggested) || [];
      const target = numberEl("target", { min: 1, value: prefill.target }); f.appendChild(field("Target sector", target, "plot-target"));
      const known = selectEl("known", ["(known sectors)", ...suggested]); f.appendChild(field("Pick from known space", known, "plot-known"));
      known.addEventListener("change", () => { if (known.selectedIndex > 0) { target.value = known.value; sync(); } });
      const exec = document.createElement("input"); exec.type = "checkbox"; exec.checked = true; exec.setAttribute("data-testid", "plot-execute");
      const execWrap = document.createElement("label"); execWrap.className = "radios"; const el2 = document.createElement("label"); el2.appendChild(exec); el2.appendChild(document.createTextNode("Execute (fly the route now, one warp cost per hop)")); execWrap.appendChild(el2); f.appendChild(execWrap);
      const sync = () => { const t = Number(target.value) || 0; const kw = (state.obs && state.obs.known_warps) || {}; const hops = t ? bfsKnown(kw, (state.obs.sector || {}).id, t) : null; preview.textContent = t ? `Route ${state.obs.sector.id} → ${t}: ${hops === null ? "not through known space (engine may still find one)" : hops + " hop(s) through known warps"}${exec.checked ? " · executes" : " · plan only (0 turns)"}` : "enter a target sector"; };
      target.addEventListener("input", sync); exec.addEventListener("change", sync); sync();
      build = () => { const t = Number(target.value) || 0; return t > 0 ? { kind: "plot_course", args: { target: t, execute: exec.checked }, thought: `Grok Bot: plot to ${t}` } : null; };
    } else if (kind === "probe") {
      const target = numberEl("target", { min: (p.target && p.target.min) || 1, max: p.target && p.target.max, value: prefill.target }); f.appendChild(field("Sector to probe", target, "probe-target"));
      const sync = () => { const t = Number(target.value) || 0; preview.textContent = t ? `Probe sector ${t} (uses 1 of ${(state.obs.ship || {}).ether_probes ?? "?"} probes, ${la.turn_cost} turn)` : "enter a sector id"; };
      target.addEventListener("input", sync); sync();
      build = () => { const t = Number(target.value) || 0; return t > 0 ? { kind: "probe", args: { target: t }, thought: `Grok Bot: probe ${t}` } : null; };
    } else if (kind === "scan") {
      const tiers = (p.tier && p.tier.choices) || ["basic"];
      const tier = selectEl("tier", tiers, "basic"); f.appendChild(field("Scan tier", tier, "scan-tier"));
      preview.textContent = `Scan ${tier.value} from sector ${(state.obs.sector || {}).id} (${la.turn_cost} turn)`;
      tier.addEventListener("change", () => { preview.textContent = `Scan ${tier.value} (${la.turn_cost} turn)`; });
      build = () => ({ kind: "scan", args: tier.value === "basic" ? {} : { tier: tier.value }, thought: `Grok Bot: scan ${tier.value}` });
    } else if (kind === "wait") {
      preview.textContent = `Pass this turn (${la.turn_cost} turn)`;
      build = () => ({ kind: "wait", args: {}, thought: "Grok Bot: wait" });
    } else if (kind === "warp") {
      preview.textContent = `Tap a WARP chip above (${la.turn_cost} turns per warp). Legal targets: ${((p.target || {}).choices || []).join(", ") || "none"}`;
      build = () => null;
    }
    f.appendChild(preview); f.appendChild(buttons);
    go.disabled = !canUse(kind);
    f.onsubmit = (ev) => { ev.preventDefault(); if (!canUse(kind)) return; const a = build(); if (!a) { preview.classList.add("warn"); return; } closeVerb(); submit(a); };
  }

  // Presentation-only BFS over the seat's OWN known_warps (memory the server sent) to
  // label a plot preview; the engine decides the real route.
  function bfsKnown(kw, src, dst) {
    if (!src || !dst) return null; if (src === dst) return 0;
    const seen = new Set([src]); let frontier = [src]; let d = 0;
    while (frontier.length && d < 60) {
      d += 1; const next = [];
      for (const s of frontier) for (const n of kw[String(s)] || []) { if (n === dst) return d; if (!seen.has(n)) { seen.add(n); next.push(n); } }
      frontier = next;
    }
    return null;
  }

  function renderControls(obs) { renderVerbPad(obs); }

  function renderObservation(obs, isPeek) {
    state.obs = obs;
    state.obsIsPeek = !!isPeek;
    renderScoreboard(obs);
    renderHere(obs);
    renderPort(obs);
    renderAdjacent(obs);
    renderKnownWarps(obs);
    renderShip(obs);
    renderKnownPorts(obs);
    renderTrade(obs);
    renderCommanders(obs);
    renderPlanets(obs);
    renderComms(obs);
    renderIntel(obs);
    renderAdvisor(obs);
    renderControls(obs);
    els.main.hidden = false;
    els.eventsFooter.hidden = false;
  }

  // ---------------------------------------------------------------- last result (English first)
  function describeAction(a) {
    if (!a) return "action";
    const g = a.args || {};
    switch (a.kind) {
      case "warp": return `WARP to ${g.target}`;
      case "trade": return `${String(g.side || "").toUpperCase()} ${g.qty} ${g.commodity}${g.unit_price ? ` @ ${g.unit_price}` : ""}`;
      case "scan": return "SCAN";
      case "wait": return "WAIT";
      default: return `${String(a.kind || "").toUpperCase()} ${Object.entries(g).map(([k, v]) => `${k}=${v}`).join(" ")}`.trim();
    }
  }
  function renderLastResult() {
    const lr = state.lastResult;
    if (!lr) { els.last.textContent = "-"; els.last.className = "result"; els.lastJson.textContent = ""; return; }
    const what = describeAction(state.lastAction);
    // Prefer the engine's own event summaries for this action (from the fogged stream).
    const seqs = new Set(lr.event_seqs || []);
    const mine = state.events.filter((e) => seqs.has(e.seq) && !["agent_thought", "llm_usage"].includes(e.kind)).map((e) => e.summary);
    let text;
    if (lr.ok) text = `${what} — ok${mine.length ? ": " + mine.join(" · ") : ""}`;
    else text = `${what} — FAILED: ${lr.error || "rejected"}`;
    els.last.textContent = `turn ${lr.turn_seq}: ${text}`;
    els.last.className = `result ${lr.ok ? "good" : "bad"}`;
    els.lastJson.textContent = JSON.stringify(lr, null, 2);
  }

  // ---------------------------------------------------------------- events (fogged stream)
  const KIND_GROUP = {
    warp: "move", warp_blocked: "move", autopilot: "move", scan: "move", probe: "move", ferrengi_move: "move",
    trade: "trade", trade_failed: "trade", buy_ship: "trade", buy_equip: "trade", planet_tax_payout: "trade",
    combat: "combat", ship_destroyed: "combat", player_eliminated: "combat", mine_detonated: "combat", photon_fired: "combat",
    photon_hit: "combat", atomic_detonation: "combat", port_destroyed: "combat", deploy_fighters: "combat", deploy_mines: "combat",
    ferrengi_attack: "combat", ferrengi_spawn: "combat", fed_response: "combat",
    hail: "comms", broadcast: "comms", corp_memo: "comms", corp_create: "comms", corp_invite: "comms", corp_join: "comms",
    corp_leave: "comms", corp_deposit: "comms", corp_withdraw: "comms", alliance_proposed: "comms", alliance_formed: "comms", alliance_broken: "comms",
    land_planet: "planet", liftoff: "planet", genesis_deployed: "planet", assign_colonists: "planet", planet_cargo_transfer: "planet",
    build_citadel: "planet", citadel_complete: "planet", planet_claimed: "planet", planet_orphaned: "planet",
  };
  function groupOf(kind) { return KIND_GROUP[kind] || "system"; }
  function factsText(e) {
    const f = e.facts || {};
    const keys = Object.keys(f);
    if (!keys.length) return "";
    return keys.map((k) => `${k}=${Array.isArray(f[k]) ? f[k].join("/") : f[k]}`).join("  ");
  }
  async function fetchEvents() {
    try {
      const r = await api(`/${state.seat}/events?since=${state.eventsSince}&limit=300`);
      if (r.events && r.events.length) {
        state.events.push(...r.events);
        if (state.events.length > 600) state.events = state.events.slice(-600);
        state.eventsSince = r.next_since;
      }
      els.eventsMeta.textContent = `${state.events.length} visible events · latest seq ${r.latest_seq}`;
      renderEvents();
      renderLastResult();
    } catch (e) {
      els.eventsMeta.textContent = `events: ${e.message || e}`;
    }
  }
  function renderEvents() {
    const filter = state.eventFilter;
    const list = state.events.filter((e) => filter === "all" || groupOf(e.kind) === filter).slice(-200).reverse();
    els.eventLog.innerHTML = "";
    for (const e of list) {
      const d = document.createElement("div");
      const g = groupOf(e.kind);
      d.className = `ev${e.actor_id === state.seat ? " mine" : ""}${g === "combat" ? " combat" : ""}${e.seq > state.lastSeenSeq ? " new" : ""}`;
      d.setAttribute("data-testid", `event-${e.seq}`);
      d.setAttribute("data-kind", e.kind);
      const when = document.createElement("span"); when.className = "when"; when.textContent = `D${e.day}·${e.tick}`;
      const kind = document.createElement("span"); kind.className = "kind"; kind.textContent = e.kind;
      const text = document.createElement("span");
      text.textContent = e.summary || "";
      const ft = factsText(e);
      if (ft) { const m = document.createElement("span"); m.className = "m"; m.style.marginLeft = "8px"; m.style.color = "var(--muted)"; m.textContent = ft; text.appendChild(m); }
      d.appendChild(when); d.appendChild(kind); d.appendChild(text);
      els.eventLog.appendChild(d);
    }
  }
  els.eventFilters.addEventListener("click", (ev) => {
    const btn = ev.target.closest("[data-filter]");
    if (!btn) return;
    state.eventFilter = btn.getAttribute("data-filter");
    els.eventFilters.querySelectorAll(".chip").forEach((c) => c.classList.toggle("on", c === btn));
    renderEvents();
  });

  // ---------------------------------------------------------------- status loop
  function applyStatus(st) {
    if (typeof st.server_time === "number") state.clockSkew = st.server_time - Date.now() / 1000;
    state.matchStatus = st.match_status || "";
    state.day = st.day; state.tick = st.tick;
    state.current = st.current_turn || null;
    if (st.last_result) state.lastResult = st.last_result;
    const wasAwaiting = state.awaiting;
    state.awaiting = !!st.awaiting_input;
    state.turnSeq = st.turn_seq ?? state.turnSeq;

    if (st.observation) renderObservation(st.observation, !!st.peek);

    if (state.matchStatus === "finished" || state.matchStatus === "error") {
      setBanner("dead", `MATCH ${state.matchStatus.toUpperCase()}`);
      setActionsEnabled(false);
      renderLastResult();
      return;
    }
    if (state.busy) { setBanner("busy", "SUBMITTING…"); return; }

    if (state.awaiting) {
      const flash = !wasAwaiting;
      setBanner("turn", `YOUR TURN  seq=${state.turnSeq}  day=${state.day}`,
        state.current && state.current.deadline_at ? `respond within ${countdownText(state.current)}` : "", flash);
      if (els.whose) els.whose.textContent = `${state.seat} (you) - act now`;
      if (flash) { log(`YOUR TURN (seq ${state.turnSeq})`); state.lastSeenSeq = state.eventsSince; }
      if (state.obs) renderControls(state.obs);
    } else {
      renderIdleBanner();
      if (state.obs) renderControls(state.obs); else setActionsEnabled(false);
      if (wasAwaiting) log(`turn ${state.turnSeq} closed; waiting on ${describeCurrent(state.current)}`);
    }
    renderLastResult();
    els.main.hidden = !state.obs;
  }

  // One-shot: status + observation (peek if not our turn) + events.
  async function refresh() {
    if (!state.token) return;
    try {
      const r = await api(`/${state.seat}/observation?wait_s=0&peek=1&format=json`);
      setErr("");
      applyStatus(r);
      await fetchEvents();
    } catch (e) {
      setErr(String(e.message || e));
      setBanner("dead", "ERROR");
      setActionsEnabled(false);
    }
  }

  // Long-poll loop. Not our turn: block up to 20 s for the turn, and take a
  // peek when the poll returns so panels stay fresh. Our turn: status every 1.5 s.
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
          const r = await api(`/${state.seat}/observation?wait_s=20&peek=1&format=json`);
          if (gen !== state.watchGen) return;
          setErr("");
          applyStatus(r);
          await fetchEvents();
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

  // ---------------------------------------------------------------- submit
  async function submit(action) {
    if (!state.awaiting || state.busy) return;
    state.busy = true;
    setActionsEnabled(false);
    setBanner("busy", "SUBMITTING…");
    setErr("");
    try {
      const seq = state.turnSeq;
      await api(`/${state.seat}/action`, { method: "POST", body: JSON.stringify({ turn_seq: seq, action }) });
      state.lastAction = action;
      log(`${describeAction(action)} posted (seq ${seq})`);
      state.awaiting = false;
      state.busy = false;
      closeVerb();
      await sleep(150);
      await refresh();
    } catch (e) {
      setErr(String(e.message || e));
      log(`FAIL ${e.message || e}`);
      setBanner("dead", "ACTION FAILED");
    } finally {
      state.busy = false;
    }
  }

  // ---------------------------------------------------------------- wiring
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
    state.events = [];
    state.eventsSince = 0;
    state.watchGen += 1;
    setErr("");
    log(`connected as ${state.seat}`);
    startTicker();
    refresh().then(() => watchLoop(state.watchGen));
  });
  els.poll.addEventListener("click", () => { setErr(""); refresh(); });
  // Verb pad: SCAN / WAIT submit straight away (no parameters); the rest open a form.
  $("verbPad").querySelectorAll("button[data-verb]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const kind = btn.getAttribute("data-verb");
      if (!canUse(kind)) return;
      if (kind === "wait") return submit({ kind: "wait", args: {}, thought: "Grok Bot: wait" });
      if (kind === "scan") return submit({ kind: "scan", args: {}, thought: "Grok Bot: scan" });
      openVerb(kind, {});
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
