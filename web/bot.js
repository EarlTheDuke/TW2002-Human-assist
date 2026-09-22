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
  const sideWord = (side) => (side === "buys_from_player" ? "BUYS" : side === "sells_to_player" ? "SELLS" : "-");

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
      tr.className = st.side === "buys_from_player" ? "buys" : "sells";
      tr.setAttribute("data-testid", `port-row-${c}`);
      td(tr, c);
      td(tr, sideWord(st.side));
      td(tr, `${fmt(st.price)} cr`, "num");
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

  // Warp / trade controls (S3 will replace the fixed trade shapes with a real form).
  function renderControls(obs) {
    const sector = obs.sector || {};
    const ship = obs.ship || {};
    const port = sector.port || null;
    const warps = sector.warps_out || [];
    const canAct = state.awaiting && !state.busy;
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
    for (const c of buys) if ((cargo[c] || 0) > 0) { canSell = { c, q: cargo[c] }; break; }
    els.sell.hidden = !canSell;
    els.sell.textContent = canSell ? `SELL ${canSell.q} ${SHORT[canSell.c] || canSell.c}` : "SELL";
    els.sell.onclick = () => { if (canSell && state.awaiting && !state.busy) submit({ kind: "trade", args: { commodity: canSell.c, qty: canSell.q, side: "sell" }, thought: `Grok Bot: sell ${canSell.q} ${canSell.c}` }); };
    const free = ship.cargo_free || 0;
    const canBuy = sells.length && free > 0 && (obs.credits || 0) > 500;
    els.buy.hidden = !canBuy;
    if (canBuy) els.buy.textContent = `BUY ${Math.min(free, 15)} ${SHORT[sells[0]] || sells[0]}`;
    els.buy.onclick = () => { if (canBuy && state.awaiting && !state.busy) submit({ kind: "trade", args: { commodity: sells[0], qty: Math.min(free, 15), side: "buy" }, thought: `Grok Bot: buy ${sells[0]}` }); };
    setActionsEnabled(canAct);
  }
  function setActionsEnabled(on) {
    document.querySelectorAll("#actionBtns [data-kind]").forEach((btn) => { btn.disabled = !on; });
    els.sell.disabled = !on;
    els.buy.disabled = !on;
    els.warps.querySelectorAll("button").forEach((b) => { b.disabled = !on; });
  }

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
