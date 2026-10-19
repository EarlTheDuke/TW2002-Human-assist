/* Winning cockpit, wired to the real harness. /bot stays the old page unless this layout is on. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const fmt = (n) => Number(n || 0).toLocaleString("en-US");
  const esc = (s) => String(s ?? "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  const COM = { fuel_ore: ["Fuel Ore", "#ffff55"], organics: ["Organics", "#55ff55"], equipment: ["Equipment", "#55ffff"], colonists: ["Colonists", "#ffffff"] };
  const KEYS = [
    ["M", "Move", "warp", 1], ["P", "Port & Trade", "trade", 1], ["L", "Land", "land_planet", 1],
    ["D", "Re-Display", null, 1], ["S", "Long Range Scan", "scan", 1], ["A", "Attack", "attack", 1],
    ["F", "Take/Leave Fighters", "deploy_fighters", 1], ["H", "Handle Mines", "deploy_mines", 1],
    ["U", "Use Genesis", "deploy_genesis", 1], ["E", "Ether Probe", "probe", 1],
    ["C", "Computer", null, 1], ["I", "Ship Info", null, 1], ["Y", "Read Mail", null, 1], [".", "Wait", "wait", 1],
    ["T", "Corporate Menu", "corp_create", 0], ["R", "Release Beacon", "launch_beacon", 0],
    ["X", "Transporter Pad", "ship_transport", 0], ["W", "Tow SpaceCraft", "tow_engage", 0],
  ];
  const MENU_KEYS = KEYS.concat([
    ["V", "Game Status"], ["Z", "Rules and Help"], ["G", "Show Deployed Fighters"], ["B", "Self Destruct"],
    ["J", "Jettison Cargo"], ["Q", "Quit"],
  ]);
  const PLANET_KEYS = [
    ["T", "Take product", "load_planet_cargo"], ["V", "Leave product", "dump_planet_cargo"],
    ["N", "Colonists", "assign_colonists"], ["F", "Stock fighters", "deposit_planet_defense"],
    ["G", "Take fighters", "withdraw_planet_defense"], ["B", "Build citadel", "build_citadel"],
  ];
  const SPACE_OFF = ["M", "P", "L", "S", "A", "H", "U", "E"];
  const CKEYS = [
    ["F", "Course Plotter", "plot_course"], ["P", "Fire Photon Missile", "photon_missile"],
    ["R", "Port Report", null], ["K", "Your Known Universe", null], ["A", "Make Announcement", "broadcast"],
    ["O", "Avoid sectors", null],
    ["L", "Trader Rankings", null],
    ["Q", "Exit Computer", null],
  ];
  const HULL = {
    merchant_cruiser: { holds: 20, fighters: 2500, shields: 400, tpw: 3, photons: false, tw: false },
    scout_marauder: { holds: 25, fighters: 150, shields: 100, tpw: 2, photons: false, tw: false },
    missile_frigate: { holds: 40, fighters: 5000, shields: 400, tpw: 3, photons: true, tw: false },
    battleship: { holds: 80, fighters: 10000, shields: 750, tpw: 4, photons: false, tw: false },
    corporate_flagship: { holds: 85, fighters: 20000, shields: 1500, tpw: 3, photons: false, tw: true },
    colonial_transport: { holds: 50, fighters: 200, shields: 500, tpw: 6, photons: false, tw: false },
    cargotran: { holds: 75, fighters: 400, shields: 1000, tpw: 4, photons: false, tw: false },
    merchant_freighter: { holds: 65, fighters: 300, shields: 500, tpw: 2, photons: false, tw: false },
    havoc_gunstar: { holds: 50, fighters: 10000, shields: 3000, tpw: 3, photons: false, tw: true },
    imperial_starship: { holds: 150, fighters: 50000, shields: 2000, tpw: 4, photons: true, tw: true },
  };
  // cockpit-ship-view-v1. The ANSI top/front pictures in the shipyard are copyright
  // Martech / EIS (Drew Markham) and the EIS wallpaper licence forbids derivatives.
  // These outlines are ours. Role comes from the public spec tables. The classic
  // silhouette of each hull is UNVERIFIED. Names already on the panel stay as they were.
  const FIGHTER_EXACT_CAP = 200;
  const SHIPS = {
    escape_pod: { name: "Escape Pod", kind: "pod", len: 70, beam: 34, engines: 1, accent: "#55ffff", detail: "" },
    merchant_cruiser: { name: "Merchant Cruiser", kind: "arrow", len: 148, beam: 52, engines: 2, accent: "#7aa2ff", detail: "pods bridge" },
    scout_marauder: { name: "Scout Marauder", kind: "needle", len: 128, beam: 28, engines: 2, accent: "#5dffc8", detail: "bridge" },
    missile_frigate: { name: "Missile Frigate", kind: "arrow", len: 154, beam: 44, engines: 2, accent: "#ffb15a", detail: "rails bridge" },
    battleship: { name: "BattleShip", kind: "delta", len: 160, beam: 68, engines: 3, accent: "#c5c8ff", detail: "bridge guns" },
    corporate_flagship: { name: "Corporate FlagShip", kind: "flag", len: 164, beam: 62, engines: 3, accent: "#ff77ff", detail: "bridge pods" },
    colonial_transport: { name: "Colonial Transport", kind: "barge", len: 162, beam: 76, engines: 2, accent: "#7dff7d", detail: "pods" },
    cargotran: { name: "CargoTran", kind: "barge", len: 168, beam: 70, engines: 2, accent: "#ffe566", detail: "pods" },
    merchant_freighter: { name: "Merchant Freighter", kind: "arrow", len: 156, beam: 58, engines: 2, accent: "#7af0ff", detail: "pods bridge" },
    imperial_starship: { name: "Imperial StarShip", kind: "capital", len: 172, beam: 70, engines: 4, accent: "#ffe9a0", detail: "bridge nacelles" },
    havoc_gunstar: { name: "Havoc GunStar", kind: "gun", len: 150, beam: 56, engines: 3, accent: "#ff8844", detail: "guns bridge" },
    star_master: { name: "Star Master", kind: "arrow", len: 144, beam: 46, engines: 2, accent: "#9ad7ff", detail: "dish bridge" },
    constellation: { name: "Constellation", kind: "delta", len: 156, beam: 64, engines: 4, accent: "#d0d6ff", detail: "nacelles bridge" },
    tkhasi_orion: { name: "T'Khasi Orion", kind: "needle", len: 146, beam: 40, engines: 2, accent: "#ff6d8a", detail: "wings bridge" },
    tholian_sentinel: { name: "Tholian Sentinel", kind: "sentinel", len: 138, beam: 78, engines: 2, accent: "#62f0c8", detail: "bridge" },
    taurean_mule: { name: "Taurean Mule", kind: "barge", len: 160, beam: 68, engines: 2, accent: "#d7b48a", detail: "pods" },
    interdictor_cruiser: { name: "Interdictor Cruiser", kind: "block", len: 170, beam: 74, engines: 4, accent: "#ff5cab", detail: "ring bridge" },
  };
  const HULL_NORM = {
    arrow: [[1, 0], [0.55, -0.42], [0.05, -0.95], [-0.55, -0.78], [-0.92, -0.35], [-0.72, 0], [-0.92, 0.35], [-0.55, 0.78], [0.05, 0.95], [0.55, 0.42]],
    needle: [[1, 0], [0.15, -0.45], [-0.75, -0.7], [-1, -0.22], [-0.82, 0], [-1, 0.22], [-0.75, 0.7], [0.15, 0.45]],
    delta: [[1, 0], [0.2, -1], [-1, -0.42], [-0.62, 0], [-1, 0.42], [0.2, 1]],
    barge: [[0.78, 0], [0.62, -0.62], [-0.82, -1], [-1, -0.55], [-1, 0.55], [-0.82, 1], [0.62, 0.62]],
    flag: [[1, 0], [0.48, -0.38], [0.05, -1], [-0.7, -0.88], [-1, -0.4], [-0.78, 0], [-1, 0.4], [-0.7, 0.88], [0.05, 1], [0.48, 0.38]],
    gun: [[0.72, -0.12], [1, -0.38], [0.42, -1], [-0.78, -0.72], [-1, -0.28], [-0.8, 0], [-1, 0.28], [-0.78, 0.72], [0.42, 1], [1, 0.38], [0.72, 0.12], [0.58, 0]],
    capital: [[1, 0], [0.7, -0.35], [0.25, -1], [-0.35, -0.92], [-1, -0.48], [-0.7, 0], [-1, 0.48], [-0.35, 0.92], [0.25, 1], [0.7, 0.35]],
    sentinel: [[0.62, 0], [0.4, -0.78], [-0.15, -1], [-1, -0.62], [-0.72, 0], [-1, 0.62], [-0.15, 1], [0.4, 0.78]],
    block: [[0.88, 0], [0.7, -0.48], [0.2, -0.82], [-0.65, -1], [-1, -0.58], [-1, 0.58], [-0.65, 1], [0.2, 0.82], [0.7, 0.48]],
  };
  function fragmentToken() {
    const raw = String(location.hash || "").replace(/^#/, "");
    if (!raw) return "";
    return new URLSearchParams(raw).get("token") || "";
  }
  const params = new URLSearchParams(location.search);
  const state = {
    seat: (params.get("seat") || "P2").toUpperCase(),
    token: params.get("token") || fragmentToken() || "",
    connected: false, awaiting: false, busy: false, turnSeq: 0, canEnd: false, gameName: "",
    eventsSince: 0, mediaHistoryUntil: null, mediaCaughtUp: false,
  };
  // cockpit-gaps-v1: the server's cockpit block (verdict, haggle, port notes, hold quote).
  // Null unless COCKPIT_FIELDS_MODE is on, so the legacy cockpit is unchanged.
  let CK = null;
  // v311-daylen-and-yard-v1: the server's turn clock (next turn, next day). Null unless turn regen
  // is live, so the legacy lines are unchanged.
  let TC = null;
  // NOTE 65 item 0. The server's starting-credits sentence. Empty until the first refresh.
  // NOTE 93. The server's turns-per-day sentence. Empty until the first refresh.
  let SC = "";
  let TD = "";
  let S = null, plotted = null, courseEvent = null, ignorePlotSeq = 0, mapSig = "", inComputer = false, sceneTable = null, openFormKind = null, formFocus = "", pending = null, heldLabel = "", waitStreak = 0, alertedSeq = 0, noticeLine = "", noticeSeq = 0, surface = false, surfaceTurn = 0, pendingPlanetKey = "";
  let courseCard = null, cameFrom = null, mapEnlarged = false, mapSuppressClick = false;
  const mapView = { k: 1, x: 0, y: 0 };
  const mapPointers = new Map();
  let mapPtr = null, mapPinch = null, mapDownNode = null;
  function rememberAlert(seq) {
    alertedSeq = seq;
    try { localStorage.setItem("tw2k-alert-" + (state.seat || ""), String(seq)); } catch (e) { /* keep the page count */ }
  }
  const streamLog = [];
  const streamSeen = new Set();
  const tokenKey = "tw2k-token-" + state.seat;
  if (params.get("token") || fragmentToken()) {
    try { sessionStorage.setItem(tokenKey, state.token); } catch (e) { /* the address still has it this once */ }
    params.delete("token");
    const q = params.toString();
    history.replaceState(null, "", location.pathname + (q ? "?" + q : ""));
  } else if (!state.token) {
    try { state.token = sessionStorage.getItem(tokenKey) || ""; } catch (e) { state.token = ""; }
  }
  $("seatSelect").value = state.seat;
  if (state.token) $("tokenInput").value = state.token;

  function headers() {
    const h = { "Content-Type": "application/json", "X-TW2K-Seat": state.seat };
    if (state.token) h.Authorization = "Bearer " + state.token;
    return h;
  }
  async function api(path, opts) {
    const r = await fetch("/harness/v1" + path, Object.assign({ credentials: "same-origin", headers: headers() }, opts || {}));
    const text = await r.text();
    let data = {};
    try { data = text ? JSON.parse(text) : {}; } catch (e) { data = {}; }
    if (!r.ok) {
      const raw = typeof data.detail === "string" ? data.detail : (data.message || text.slice(0, 180) || String(r.status));
      if (Array.isArray(data.detail) || /validation error|input should be/i.test(String(raw))) {
        throw new Error("That command was not accepted.");
      }
      if (/missing bearer token/i.test(String(raw))) {
        throw new Error("This seat needs its join link. Open it from the lobby, or use Re-open my seat in the browser you joined from.");
      }
      throw new Error(raw);
    }
    return data;
  }
  const LA = (k) => ((S && S.legal_actions) || []).find((a) => a.kind === k);
  const legal = (k) => !!(LA(k) || {}).legal;
  function courseSentence(ev) {
    const facts = ev && ev.facts;
    const path = facts && Array.isArray(facts.path) ? facts.path.map(Number) : [];
    if (!path.length) return "";
    const target = Number(facts.target);
    const start = Number(ev.sector_id);
    const origin = start && start !== target && path[0] !== start ? start : null;
    const full = origin ? [origin].concat(path) : path.slice();
    if (target && full[full.length - 1] !== target) full.push(target);
    const hops = path.length;
    const hopCost = Number((((LA("plot_course") || {}).params || {}).execute || {}).first_hop_turns || (LA("warp") || {}).turn_cost || 0);
    return "plotted course " + full.join(" > ") + ", " + hops + " hops" + (hopCost ? ", " + (hops * hopCost) + " turns" : "");
  }
  function dropSeat(text) {
    const name = S && S.self_name;
    if (!name) return text;
    const escaped = String(name).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return String(text).replace(new RegExp("\\b" + escaped + "\\s+", "gi"), "");
  }
  function capFirst(text) {
    const s = String(text || "");
    return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
  }
  function shownSentence(text, ev) {
    let s = String(text || "");
    if (/plotted course/i.test(s)) {
      const nice = courseSentence(ev || courseEvent);
      if (nice) s = s.replace(/plotted course[\s\S]*$/i, nice);
    }
    const nouns = { beacon: "beacons", fighter: "fighters", shield: "shields", probe: "probes", hold: "holds", mine: "mines", torpedo: "torpedoes", missile: "missiles" };
    s = s.replace(/\b(\d+)\s+((?:[A-Za-z]+\s+)?)(beacon|fighter|shield|probe|hold|mine|torpedo|missile)\b/gi, (m, n, mid, word) => {
      if (Number(n) === 1) return m;
      return n + " " + mid + nouns[word.toLowerCase()];
    });
    s = s.replace(/(\d{4,})\s*cr\b/gi, (m, n) => Number(n).toLocaleString("en-US") + " cr");
    s = s.replace(/(\d+)cr\b/gi, (m, n) => Number(n).toLocaleString("en-US") + " cr");
    s = s.replace(/\b1 days\b/g, "1 day");
    s = s.replace(/\b1 ((?:[A-Za-z]+ )?)fighters\b/gi, "1 $1fighter");
    s = s.replace(/\b1 shields\b/gi, "1 shield");
    if (/ferrengi/i.test(s)) s = s.replace(/\s+/g, " ");
    s = s.replace(/\b1 holds\b/g, "1 cargo hold");
    s = s.replace(/\b(\d[\d,]*) holds\b/g, (m, n) => n + " cargo holds");
    s = s.replace(/mines in sector \d+: avoid this sector\?\s*\(autopilot stops here\)/gi, "Mines are in this sector. Computer, then O, adds it to the avoid list");
    return s.replace(/\.\.+/g, ".").trim();
  }
  function plainWords(text) {
    let s = dropSeat(String(text || "").replace(/^\[[^\]]+\]\s*/, ""));
    s = s.replace(/pool=fuel_ore/g, "fuel ore").replace(/pool=organics/g, "organics").replace(/pool=equipment/g, "equipment");
    s = s.replace(/buy_equip/g, "buy gear").replace(/_/g, " ");
    s = s.replace(/no photon missiles loaded \(buy gear photon missiles at StarDock\)/gi, () => {
      const cls = (S && S.ship && S.ship.class) || "";
      if (cls === "missile_frigate" || cls === "imperial_starship") return "No photon missiles on board. Buy them at StarDock.";
      if (cls) return "This ship cannot carry photon missiles. A Missile Frigate or an Imperial StarShip can.";
      return "No photon missiles on board. Buy them at StarDock.";
    });
    s = s.replace(/no long range scanner \(buy gear density scanner or holo scanner at StarDock\)/gi, "Buy a density scanner or a holo scanner at StarDock.");
    s = s.replace(/no genesis torpedoes loaded \(buy gear genesis at StarDock\)/gi, "No Genesis torpedoes on board. Buy them at StarDock.");
    s = s.replace(/quantity must be positive/gi, "Type how many.");
    s = s.replace(/fighters per attack must be 1\.\.(\d+)/gi, "fighters per attack must be 1 to $1");
    s = s.replace(/\b(withdrew [\d,]+ (?:fighters|shields)) on /gi, "$1 from ");
    s = s.replace(/insufficient credits \((\d+) < (\d+)\)/gi, (m, have, need) => "not enough credits: you need " + fmt(need) + " cr, you have " + fmt(have) + " cr");
    s = s.replace(/\binvalid action:\s*/gi, "").replace(/\btrade failed:\s*/gi, "");
    s = dropSeat(s);
    if (/validation error|input should be/i.test(s)) return "That command was not accepted.";
    return shownSentence(s);
  }
  function creditLine(kind, args, text) {
    const m = /insufficient credits \((\d+) < (\d+)\)/i.exec(String(text || ""));
    if (!m || kind !== "buy_equip" || !args || !args.item) return "";
    const name = String(args.item).replace(/_/g, " ");
    return "not enough credits: " + fmt(args.qty || 0) + " " + name + " cost " + fmt(m[2]) + " cr, you have " + fmt(m[1]) + " cr";
  }
  function latestAfter(seq) {
    let best = null;
    streamLog.concat((S && S.recent_events) || []).forEach((ev) => {
      if (!ev || ev.kind === "cockpit_note" || (ev.seq || 0) <= seq) return;
      if (!best || (ev.seq || 0) >= (best.seq || 0)) best = ev;
    });
    return best;
  }
  function plainEvent(ev) {
    const facts = (ev && ev.facts) || {};
    if (ev && ev.kind === "mine_detonated" && S && ev.actor_id === S.self_id && facts.victim && facts.victim !== S.self_id) {
      return "Your mines hit " + traderName(facts.victim) + " in sector " + (ev.sector_id || "") + " for " + fmt(facts.damage || 0) + " damage.";
    }
    if (ev && ev.kind === "ferrengi_encounter") {
      const boarded = boardingSentence(ev);
      if (boarded) return boarded;
    }
    if (ev && ev.kind === "ferrengi_tribute") return tributePaid(ev);
    if (ev && ev.kind === "combat" && (eventFacts(ev).exchange_kind === "ship_vs_ship" || /shields and \d+ fighters/i.test(ev.summary || ""))) {
      const said = fightSentence(ev);
      if (said) return said;
    }
    if (ev && ev.kind === "combat" && facts.vs === "planet" && facts.planet_fighters_lost != null) {
      const twin = streamLog.concat((S && S.recent_events) || []).some((row) => {
        return row && row !== ev && /planetary defenses repelled/i.test(row.summary || "");
      });
      if (twin) return "";
      return siegeSentence(facts);
    }
    const text = ev && (ev.summary || ev.kind) || "";
    const shown = shownSentence(String(text).replace(/_/g, " "), ev);
    if (/planetary defenses repelled landing/i.test(shown)) {
      let combat = null;
      streamLog.concat((S && S.recent_events) || []).forEach((row) => {
        const rowFacts = (row && row.facts) || {};
        if (row && row.kind === "combat" && rowFacts.vs === "planet" && rowFacts.planet_fighters_lost != null) combat = row;
      });
      if (combat) return siegeSentence(combat.facts);
    }
    return shown;
  }
  function paintLog() {
    const rows = [];
    const seen = new Set();
    streamLog.concat((S && S.recent_events) || []).forEach((ev) => {
      if (!ev || seen.has(ev.seq)) return;
      seen.add(ev.seq);
      rows.push(ev);
    });
    rows.sort((a, b) => (b.seq || 0) - (a.seq || 0));
    const box = $("log");
    box.innerHTML = "";
    rows.slice(0, 40).forEach((ev) => {
      const line = plainEvent(ev);
      if (!line) return;
      const d = document.createElement("div");
      d.dataset.seq = String(ev.seq || 0);
      d.textContent = line;
      box.appendChild(d);
    });
    box.scrollTop = 0;
  }
  let noteFrac = 0;
  function rememberLine(sentence) {
    let maxReal = 0;
    streamLog.concat((S && S.recent_events) || []).forEach((row) => {
      if (!row || row.kind === "cockpit_note") return;
      if ((row.seq || 0) > maxReal) maxReal = row.seq || 0;
    });
    noteFrac += 1;
    streamLog.push({ seq: maxReal + noteFrac / 1000000, kind: "cockpit_note", summary: sentence });
    paintLog();
  }
  function setResult(text, bad) {
    const el = $("lastResult");
    el.textContent = text || "";
    el.className = bad ? "bad" : "";
  }
  function verdictAction(v) {
    const a = v.args || {};
    const name = (COM[a.commodity] || [a.commodity])[0];
    if (v.kind === "warp") return "warp to " + a.target;
    if (v.kind === "trade") return (a.side || "trade") + " " + fmt(a.qty) + " " + (name || "") + (a.unit_price != null ? " at " + fmt(a.unit_price) + " cr" : "");
    if (v.kind === "buy_equip") return "buy " + fmt(a.qty) + " " + gearName(a.item);
    if (v.kind === "plot_course") return "plot course to " + a.target;
    return String(v.kind || "").replaceAll("_", " ");
  }
  function paintVerdict() {
    // cockpit-gaps-v1 item 1: the engine verdict as its own field, read from the server, so a reload keeps it.
    // Original: the outcome prints right after the command (transcript.txt 2432-2433, 2454, 2470, 9241).
    const el = $("verdict");
    if (!el) return;
    const v = CK && CK.verdict;
    if (!v) { el.hidden = true; el.textContent = ""; return; }
    const delta = Number(v.credits_change || 0);
    const turns = v.turns_spent == null ? "the day ended" : fmt(v.turns_spent) + " turn" + (Number(v.turns_spent) === 1 ? "" : "s") + " spent, " + fmt(v.turns_left) + " left";
    const hg = v.haggle || {};
    const why = v.ok ? "" : " — " + (hg.outcome === "countered" && hg.counter != null
      ? "the port countered at " + fmt(hg.counter) + " cr each"
      : plainWords(String(v.reason || "refused")));
    el.hidden = false;
    el.dataset.ok = v.ok ? "true" : "false";
    el.dataset.kind = v.kind || "";
    el.dataset.turn = String(v.turn_seq || 0);
    el.className = v.ok ? "verdict ok" : "verdict bad";
    el.textContent = "Last action: " + verdictAction(v) + ". " + (v.ok ? "OK" : "REFUSED") + why + ". " + capFirst(turns) + ". Credits " + (delta >= 0 ? "+" : "") + fmt(delta) + ".";
    releaseTradeFocus(v);
  }
  let tradeFocusSeq = null;
  function releaseTradeFocus(v) {
    if (!v || v.kind !== "trade") return;
    const seq = Number(v.turn_seq || 0);
    if (tradeFocusSeq === seq) return;
    tradeFocusSeq = seq;
    const slot = $("formSlot");
    if (slot) {
      openFormKind = null;
      formFocus = "";
      slot.innerHTML = "";
    }
    const active = document.activeElement;
    if (active && active.blur) active.blur();
  }
  function onSurface() {
    return !!landedPlanet() || surface;
  }
  function landedPlanet() {
    if (!S || S.planet_landed == null) return null;
    const id = Number(S.planet_landed);
    const brief = (S.sector.planets || []).find((p) => Number(p.id) === id);
    const owned = (S.owned_planets || []).find((p) => Number(p.id) === id);
    if (!brief && !owned) return { id, name: "planet " + id };
    return Object.assign({}, owned || {}, brief || {}, {
      production: (owned && owned.production) || null,
      stockpile: (brief && brief.stockpile) || (owned && owned.stockpile) || {},
      colonists: (brief && brief.colonists) || (owned && owned.colonists) || {},
    });
  }

  function paintScene() {
    const img = $("sceneStill");
    if (!img || !S) return;
    const ship = S.ship || {};
    let key = "sector_deep";
    if (ship.class === "escape_pod") key = "in_pod";
    else if (S.planet_landed != null) {
      const owned = (S.owned_planets || []).some((p) => Number(p.id) === Number(S.planet_landed));
      key = owned ? "planet_own" : "planet_foreign";
    } else {
      const sector = S.sector || {};
      const port = sector.port;
      if (port && /stardock/i.test(String(port.name || ""))) key = "sector_stardock";
      else if (sector.terra) key = "sector_terra";
      else if (port && port.class_id != null) key = "sector_port_" + port.class_id;
      else if (sector.is_fedspace) key = "sector_fedspace";
      else if (Number(sector.id) === 1) key = "sector_stardock";
    }
    const draw = (table) => {
      let current = key;
      const seen = new Set();
      let file = "";
      while (current && current !== "canvas" && !seen.has(current)) {
        seen.add(current);
        const entry = table[current];
        if (!entry) { current = String(current).indexOf("sector_port_") === 0 ? "docked_port" : "sector_deep"; continue; }
        if (entry.file) { file = entry.file; break; }
        current = entry.fallback || "canvas";
      }
      if (!file) { img.hidden = true; return; }
      img.alt = key;
      img.hidden = false;
      img.src = "/static/media/" + file;
    };
    if (sceneTable) { draw(sceneTable); return; }
    fetch("/static/media/manifest.json").then((r) => r.json()).then((data) => {
      sceneTable = data.keys || {};
      draw(sceneTable);
    }).catch(() => { img.hidden = true; });
  }

  function fighterPlan(n) {
    const count = Math.max(0, Math.floor(Number(n) || 0));
    if (count <= FIGHTER_EXACT_CAP) return { fighters: count, triangles: count, scale: 1 };
    const scale = Math.ceil(count / FIGHTER_EXACT_CAP);
    return { fighters: count, triangles: Math.ceil(count / scale), scale: scale };
  }
  function poly(points, fill, stroke, width, opacity) {
    const p = points.map((xy) => xy[0].toFixed(1) + "," + xy[1].toFixed(1)).join(" ");
    const op = opacity == null ? "" : ' opacity="' + opacity + '"';
    const st = stroke ? ' stroke="' + stroke + '" stroke-width="' + (width || 1) + '"' : "";
    return '<polygon points="' + p + '" fill="' + fill + '"' + st + op + "/>";
  }
  function hullOutline(def) {
    const norm = HULL_NORM[def.kind] || HULL_NORM.arrow;
    return norm.map((p) => [p[0] * def.len * 0.5, p[1] * def.beam * 0.5]);
  }
  function starfield() {
    let seed = 77;
    const rnd = () => (seed = (seed * 9301 + 49297) % 233280) / 233280;
    let g = "";
    for (let i = 0; i < 46; i++) {
      const x = (rnd() * 388 + 6).toFixed(1);
      const y = (rnd() * 246 + 6).toFixed(1);
      const r = (rnd() * 1.05 + 0.35).toFixed(2);
      g += '<circle cx="' + x + '" cy="' + y + '" r="' + r + '" fill="#d5e4ff" opacity="' + (0.28 + rnd() * 0.55).toFixed(2) + '"/>';
    }
    return g;
  }
  function fighterMarks(triangles) {
    if (!triangles) return "";
    const cx = 200, cy = 124;
    let html = "";
    let placed = 0;
    let ring = 0;
    while (placed < triangles && ring < 6) {
      const rx = Math.min(168, 126 + ring * 16);
      const ry = Math.min(102, 80 + ring * 10);
      const room = Math.max(12, Math.floor((2 * Math.PI * ((rx + ry) / 2)) / 6.4));
      const use = ring >= 3 ? triangles - placed : Math.min(room, triangles - placed);
      for (let i = 0; i < use; i++) {
        const a = -Math.PI / 2 + ((i + 0.5) / use) * Math.PI * 2;
        const x = cx + Math.cos(a) * rx;
        const y = cy + Math.sin(a) * ry;
        const rot = (a * 180 / Math.PI + 90).toFixed(1);
        html += '<path class="fighter" data-testid="fighter-triangle" d="M0,-3.1 L2.35,2.45 L-2.35,2.45 Z" fill="#ff2a2a" stroke="#ff8888" stroke-width="0.4" transform="translate(' + x.toFixed(1) + " " + y.toFixed(1) + ") rotate(" + rot + ')"/>';
      }
      placed += use;
      ring += 1;
    }
    return html;
  }
  function shipBody(sh, def) {
    const accent = def.accent || "#7aa2ff";
    const detail = new Set(String(def.detail || "").split(" ").filter(Boolean));
    const tw = !!(sh.transwarp && sh.transwarp.fitted);
    if (def.kind === "pod") {
      return '<ellipse cx="4" cy="10" rx="36" ry="16" fill="#000" opacity="0.45"/>'
        + '<ellipse cx="0" cy="0" rx="30" ry="15" fill="#102433" stroke="' + accent + '" stroke-width="1.6"/>'
        + '<ellipse cx="-6" cy="-4" rx="16" ry="7" fill="#1b4558"/>'
        + '<circle cx="8" cy="0" r="6.5" fill="#071018" stroke="' + accent + '" stroke-width="1.2"/>'
        + '<circle cx="8" cy="-1" r="2.4" fill="' + accent + '" opacity="0.8"/>'
        + '<rect x="-42" y="-3" width="12" height="6" rx="1" fill="#243044"/>'
        + '<rect x="-50" y="-1.6" width="9" height="3.2" fill="#bff"/>';
    }
    const outline = hullOutline(def);
    const thick = outline.map((p) => [p[0] + 7, p[1] + 11]);
    const top = outline.map((p) => [p[0] * 0.56 - 3, p[1] * 0.4 - 7]);
    const gloss = outline.map((p) => [p[0] * 0.26 - 1, p[1] * 0.16 - 11]);
    let g = '<ellipse cx="4" cy="18" rx="' + (def.len * 0.42).toFixed(1) + '" ry="12" fill="#000" opacity="0.4"/>';
    if (detail.has("nacelles")) {
      const tail = -def.len * 0.32;
      const span = def.len * 0.46;
      g += '<rect x="' + tail.toFixed(1) + '" y="-24" width="' + span.toFixed(1) + '" height="5" rx="2" fill="#0c1424" stroke="' + accent + '"/>';
      g += '<rect x="' + tail.toFixed(1) + '" y="19" width="' + span.toFixed(1) + '" height="5" rx="2" fill="#0c1424" stroke="' + accent + '"/>';
    }
    if (detail.has("wings")) {
      g += poly([[18, -6], [-8, -30], [-24, -8]], "#10182e", accent, 1.1);
      g += poly([[18, 6], [-8, 30], [-24, 8]], "#10182e", accent, 1.1);
    }
    g += poly(thick, "#050814", "#152038", 1);
    g += poly(outline, "#121a30", accent, 1.5);
    g += poly(top, "#2a3d68", null, 0);
    g += poly(gloss, "#ffffff", null, 0, 0.22);
    if (detail.has("pods")) {
      const y = Math.max(16, def.beam * 0.36);
      g += '<ellipse cx="-6" cy="' + (-y).toFixed(1) + '" rx="18" ry="6.5" fill="#0c1428" stroke="' + accent + '" stroke-width="1"/>';
      g += '<ellipse cx="-6" cy="' + y.toFixed(1) + '" rx="18" ry="6.5" fill="#0c1428" stroke="' + accent + '" stroke-width="1"/>';
    }
    if (detail.has("rails")) {
      g += '<rect x="-12" y="-18" width="34" height="3.5" fill="#3a2a16" stroke="' + accent + '" stroke-width="0.8"/>';
      g += '<rect x="-2" y="-21" width="8" height="3" fill="' + accent + '"/>';
      g += '<rect x="10" y="-21" width="8" height="3" fill="' + accent + '"/>';
    }
    if (detail.has("guns")) {
      g += '<rect x="' + (def.len * 0.28).toFixed(1) + '" y="-9" width="20" height="2.6" fill="' + accent + '"/>';
      g += '<rect x="' + (def.len * 0.28).toFixed(1) + '" y="6.4" width="20" height="2.6" fill="' + accent + '"/>';
    }
    if (detail.has("ring")) {
      g += '<ellipse cx="' + (def.len * 0.42).toFixed(1) + '" cy="0" rx="8" ry="' + (def.beam * 0.34).toFixed(1) + '" fill="none" stroke="' + accent + '" stroke-width="2"/>';
    }
    if (detail.has("dish")) {
      g += '<ellipse cx="-2" cy="-16" rx="8" ry="4.5" fill="none" stroke="' + accent + '" stroke-width="1.3"/>';
      g += '<line x1="-2" y1="-12" x2="-2" y2="-6" stroke="' + accent + '" stroke-width="1.2"/>';
    }
    if (detail.has("bridge")) {
      g += poly([[-4, -5], [12, -3.2], [16, 0], [12, 3.2], [-4, 5], [-10, 3], [-10, -3]], "#182848", accent, 1);
      g += '<ellipse cx="8" cy="0" rx="3.6" ry="2.2" fill="#d8fbff" opacity="0.8"/>';
    }
    const windows = def.kind === "barge" ? 6 : 4;
    for (let i = 0; i < windows; i++) {
      g += '<rect x="' + (-18 + i * 7) + '" y="-1.3" width="3.2" height="2" fill="' + accent + '" opacity="0.75"/>';
    }
    const tail = Math.min.apply(null, outline.map((p) => p[0]));
    const glow = tw ? "#ff55ff" : "#9fffff";
    const core = tw ? "#ffe6ff" : "#f4ffff";
    const n = Math.max(1, def.engines || 1);
    for (let i = 0; i < n; i++) {
      const y = (i - (n - 1) / 2) * (n > 3 ? 8 : 11);
      g += '<rect x="' + (tail - 14).toFixed(1) + '" y="' + (y - 3.2).toFixed(1) + '" width="13" height="6.4" rx="1" fill="#243044"/>';
      g += '<rect x="' + (tail - 20).toFixed(1) + '" y="' + (y - 1.6).toFixed(1) + '" width="7" height="3.2" fill="' + glow + '"/>';
      g += '<ellipse cx="' + (tail - 22).toFixed(1) + '" cy="' + y.toFixed(1) + '" rx="5" ry="1.8" fill="' + core + '" opacity="0.9"/>';
    }
    const cap = Number(sh.shield_cap) || 0;
    const have = Number(sh.shields) || 0;
    if (have > 0 && cap > 0) {
      const sp = Math.min(1, have / cap);
      g += '<ellipse cx="0" cy="2" rx="' + Math.max(40, def.len * 0.58).toFixed(1) + '" ry="' + Math.max(22, def.beam * 0.7).toFixed(1) + '" fill="none" stroke="#55ffff" stroke-width="' + (1 + sp * 2).toFixed(1) + '" opacity="' + (0.28 + sp * 0.4).toFixed(2) + '" stroke-dasharray="5 4"/>';
    }
    return g;
  }
  function paintShipView(sh, def) {
    const plan = fighterPlan(sh.fighters);
    const svg = $("shipSvg");
    svg.setAttribute("data-hull", sh.class || "ship");
    svg.setAttribute("data-kind", def.kind || "arrow");
    svg.setAttribute("data-fighters", String(plan.fighters));
    svg.setAttribute("data-triangles", String(plan.triangles));
    svg.setAttribute("data-scale", String(plan.scale));
    svg.setAttribute("aria-label", def.name + ", " + fmt(plan.fighters) + " fighters");
    svg.innerHTML = starfield()
      + '<g class="hull-float" data-testid="ship-hull">'
      + '<g data-testid="ship-body" transform="translate(200 124)">' + shipBody(sh, def) + "</g>"
      + fighterMarks(plan.triangles)
      + "</g>";
    const row = $("fighterRow");
    if (plan.scale > 1) {
      const word = plan.scale === 1 ? "fighter" : "fighters";
      row.innerHTML = '<span class="fighter-legend" data-testid="fighter-legend">each triangle = ' + plan.scale + " " + word + "</span>";
    } else {
      row.innerHTML = "";
    }
  }

  // cockpit-warp-ship-clips-v1. Classic per-hull warp cinema is UNVERIFIED and not
  // free to trace. Each hull's sequence is drawn from our own silhouette above.
  // A hull with no rows in web/media/warp-clips.json falls back to warp.out.
  let warpManifest = null;
  let warpManifestPromise = null;
  let warpPlays = 0;
  let warpTimer = 0;
  function ensureWarpManifest() {
    if (warpManifest) return Promise.resolve(warpManifest);
    if (!warpManifestPromise) {
      warpManifestPromise = fetch("/static/media/warp-clips.json", { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
        .then((data) => { warpManifest = data || { hulls: {} }; return warpManifest; })
        .catch(() => { warpManifest = { hulls: {}, fallback_clip: "warp.out", duration_ms: 2000 }; return warpManifest; });
    }
    return warpManifestPromise;
  }
  function chooseWarpClip(hull, rnd) {
    const table = (warpManifest && warpManifest.hulls) || {};
    const list = Array.isArray(table[hull]) ? table[hull].filter((row) => row && row.id) : [];
    if (!list.length) {
      return {
        fallback: true,
        id: (warpManifest && warpManifest.fallback_clip) || "warp.out",
        hull: hull || "",
        kind: "fallback",
      };
    }
    let roll = typeof rnd === "function" ? Number(rnd()) : Math.random();
    if (!Number.isFinite(roll)) roll = 0;
    if (roll < 0) roll = 0;
    if (roll >= 1) roll = 0.999999;
    const clip = list[Math.floor(roll * list.length)];
    return {
      fallback: false,
      id: String(clip.id),
      hull: hull,
      kind: clip.kind || "svg",
      duration_ms: clip.duration_ms,
      webm: clip.webm || "",
      mp4: clip.mp4 || "",
      poster: clip.poster || "",
    };
  }
  function warpMotion() {
    const reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const mode = ($("viewport") && $("viewport").getAttribute("data-mode")) || "live";
    if (mode === "off") return "off";
    if (reduce || mode === "stills") return "still";
    return "play";
  }
  function warpStars() {
    let seed = 80;
    const rnd = () => (seed = (seed * 9301 + 49297) % 233280) / 233280;
    let lines = "";
    for (let i = 0; i < 42; i++) {
      const y = rnd() * 244 + 8;
      const x = rnd() * 340 + 8;
      const w = 16 + rnd() * 78;
      lines += '<line x1="' + x.toFixed(1) + '" y1="' + y.toFixed(1) + '" x2="' + (x + w).toFixed(1) + '" y2="' + y.toFixed(1)
        + '" stroke="#b9dcff" stroke-width="' + (0.6 + rnd() * 1.1).toFixed(2) + '" opacity="' + (0.28 + rnd() * 0.55).toFixed(2) + '"/>';
    }
    return '<g class="streaks" data-testid="warp-streaks">' + lines + "</g>";
  }
  function showWarpClip(chosen) {
    const root = $("warpClip");
    const svg = $("warpSvg");
    const video = $("warpVideo");
    if (!root || !svg) return;
    const motion = warpMotion();
    if (motion === "off") { root.hidden = true; return; }
    const sh = (S && S.ship) || {};
    const def = SHIPS[chosen.hull] || SHIPS[sh.class] || { name: chosen.hull || "ship", kind: "arrow", len: 150, beam: 48, engines: 2, accent: "#7aa2ff", detail: "bridge" };
    const ms = Number(chosen.duration_ms) || Number(warpManifest && warpManifest.duration_ms) || 2000;
    const file = chosen.kind === "file" && (chosen.webm || chosen.mp4);
    root.hidden = false;
    root.setAttribute("data-hull", chosen.hull);
    root.setAttribute("data-clip", chosen.id);
    root.setAttribute("data-kind", file ? "file" : "svg");
    root.setAttribute("data-motion", motion);
    root.classList.toggle("is-still", motion !== "play");
    svg.hidden = false;
    svg.innerHTML = warpStars()
      + '<g class="warp-ship" data-testid="warp-ship"><g data-testid="warp-body" transform="translate(200 130)">'
      + shipBody(sh, def) + "</g></g>";
    if (video) {
      video.hidden = true;
      video.onerror = null;
      try { video.pause(); } catch (e) { /* no file yet */ }
      video.removeAttribute("src");
      if (file && motion === "play") {
        video.hidden = false;
        svg.hidden = true;
        video.src = "/static/media/" + (chosen.webm || chosen.mp4);
        video.play().catch(() => { video.hidden = true; svg.hidden = false; });
        video.onerror = () => { video.hidden = true; svg.hidden = false; };
      }
    }
    const generic = document.getElementById("vpClip");
    if (generic) generic.hidden = true;
    warpPlays += 1;
    root.setAttribute("data-plays", String(warpPlays));
    if (warpTimer) clearTimeout(warpTimer);
    warpTimer = setTimeout(() => {
      root.hidden = true;
      if (video) { try { video.pause(); } catch (e) { /* already quiet */ } }
    }, ms);
  }
  function holdWarp(atMs) {
    const root = $("warpClip");
    if (!root || root.hidden) return 0;
    if (warpTimer) { clearTimeout(warpTimer); warpTimer = 0; }
    const anims = root.getAnimations({ subtree: true });
    anims.forEach((anim) => {
      if (atMs != null) { try { anim.currentTime = atMs; } catch (e) { /* stay on this frame */ } }
      anim.pause();
    });
    return anims.length;
  }
  function isRealMove(ev) {
    if (!ev || !S || ev.actor_id !== S.self_id) return false;
    if (ev.kind === "warp") {
      const f = ev.facts || {};
      const from = f.from != null ? Number(f.from) : Number(ev.sector_id);
      const to = f.to != null ? Number(f.to) : (f.target != null ? Number(f.target) : NaN);
      return to !== from;
    }
    if (ev.kind === "autopilot") {
      const f = ev.facts || {};
      return !!f.executed && Number(f.hops_done || 0) >= 1;
    }
    return false;
  }
  async function playWarpClips(live) {
    if (!live || !live.some(isRealMove)) return false;
    await ensureWarpManifest();
    const hull = String((S && S.ship && S.ship.class) || "");
    const chosen = chooseWarpClip(hull);
    if (chosen.fallback) return false;
    showWarpClip(chosen);
    return true;
  }

  const known = (id) => !!((S.known_warps || {})[id] || (S.known_warps || {})[String(id)]);
  function outOfTurns() {
    return !!(S && Number(S.turns_remaining) <= 0);
  }
  function clockTime(epoch) {
    const short = TC && Number(TC.day_seconds) < 3600;
    return new Date(Number(epoch) * 1000).toLocaleTimeString([], short
      ? { hour: "numeric", minute: "2-digit", second: "2-digit" } : { hour: "numeric", minute: "2-digit" });
  }
  function inWords(seconds) {
    const s = Math.max(0, Number(seconds) || 0);
    if (s < 90) return Math.max(1, Math.round(s)) + " s";
    if (s < 5400) return Math.round(s / 60) + " min";
    return (s / 3600).toFixed(1).replace(/\.0$/, "") + " h";
  }
  let dayDeadline = null;
  let turnDeadline = null;
  let seatDeadline = null;
  function clockRemain(total) {
    let s = Math.max(0, Math.round(Number(total) || 0));
    const h = Math.floor(s / 3600);
    s -= h * 3600;
    const m = Math.floor(s / 60);
    const sec = s - m * 60;
    const pad = (n) => String(n).padStart(2, "0");
    return h > 0 ? h + ":" + pad(m) + ":" + pad(sec) : pad(m) + ":" + pad(sec);
  }
  function everyWords(seconds) {
    const s = Number(seconds) || 0;
    if (s < 90) return String(Math.round(s * 10) / 10).replace(/\.0$/, "") + " s";
    return String(Math.round(s / 6) / 10).replace(/\.0$/, "") + " min";
  }
  function leftOf(deadline) {
    if (deadline == null) return null;
    return Math.max(0, (deadline - performance.now()) / 1000);
  }
  function syncClocks() {
    dayDeadline = TC && TC.next_day_in_s != null ? performance.now() + Number(TC.next_day_in_s) * 1000 : null;
    turnDeadline = TC && TC.next_turn_in_s != null ? performance.now() + Number(TC.next_turn_in_s) * 1000 : null;
  }
  function turnFace() {
    const left = fmt(S.turns_remaining);
    const cap = fmt(S.turns_per_day);
    if (!TC || TC.seconds_per_turn == null) return left + "/" + cap;
    if (Number(S.turns_remaining) >= Number(S.turns_per_day)) return left + "/" + cap + " (full)";
    const next = leftOf(turnDeadline);
    const nextText = next == null ? "" : ", next in " + (next < 90 ? Math.max(1, Math.round(next)) + " s" : everyWords(next));
    return left + "/" + cap + " (+1 every " + everyWords(TC.seconds_per_turn) + nextText + ")";
  }
  function syncSeatTimer(st) {
    // NOTE 93. The server's seat deadline, counted down here. Amber under 30 s.
    if (!state.awaiting || !st || st.deadline_at == null || st.server_time == null) {
      seatDeadline = null;
      return;
    }
    const left = Number(st.deadline_at) - Number(st.server_time);
    seatDeadline = Number.isFinite(left) ? performance.now() + Math.max(0, left) * 1000 : null;
  }
  function paintSeatTimer() {
    const el = $("seatTimer");
    if (!el) return;
    if (!state.awaiting || seatDeadline == null) {
      el.hidden = true;
      el.textContent = "";
      el.className = "seat-timer";
      return;
    }
    const left = Math.max(0, Math.ceil((seatDeadline - performance.now()) / 1000));
    el.hidden = false;
    el.textContent = "auto-WAIT " + left + "s";
    el.className = "seat-timer" + (left < 30 ? " amber" : "");
  }
  function paintClocks() {
    const day = $("dayClock");
    if (day) {
      const left = leftOf(dayDeadline);
      day.textContent = left == null ? "" : ", next day in " + clockRemain(left);
    }
    if (S && $("turns")) $("turns").textContent = turnFace();
    paintSeatTimer();
    const stat = $("turnsStat");
    if (stat) {
      stat.title = TC
        ? "Under v3.11, turns come back a little at a time all day. The day rolls on the clock, not when everyone is out of turns."
        : "Turns left today";
    }
  }
  function noTurnsLine() {
    if (TC) {
      // NOTE 60 item 4: turns come back on the server's clock and the day starts at a clock time.
      let line = "No turns left.";
      if (TC.next_turn_in_s != null) line += " Next turn in about " + inWords(TC.next_turn_in_s) + " (" + clockTime(TC.next_turn_at) + ").";
      if (TC.next_day_at != null) line += " Day " + (Number(S.day) + 1) + " starts at " + clockTime(TC.next_day_at) + ".";
      return line;
    }
    return "No turns left today. Day " + (Number(S.day) + 1) + " starts when the other traders finish.";
  }
  function yardName(key, stats) {
    const s = (stats || {})[key];
    return (s && s.name) || (SHIPS[key] && SHIPS[key].name) || String(key).replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }
  function gearOptions(sel, spec) {
    // Every priced item, including the ones this seat cannot afford. Grey those.
    const prices = spec.unit_price_by || {};
    const open = new Set(spec.choices || []);
    const credits = Number((S && S.credits) || 0);
    const keys = Object.keys(prices).length ? Object.keys(prices) : (spec.choices || []);
    let picked = false;
    keys.forEach((key) => {
      const o = document.createElement("option");
      o.value = key;
      const price = prices[key];
      const name = gearName(key);
      // textContent stays the gear's name. Earlier cockpit tests read that.
      // The label is what the list shows: price, and why a row is grey.
      let shown = name + (price == null ? "" : " - " + fmt(price) + " cr");
      o.textContent = name;
      if (!open.has(key)) {
        o.disabled = true;
        shown += " (need " + fmt(price) + " cr, have " + fmt(credits) + ")";
      } else if (!picked) {
        o.selected = true;
        picked = true;
      }
      o.label = shown;
      sel.appendChild(o);
    });
  }
  function yardOptions(sel, spec) {
    // NOTE 60 item 6: the whole catalog with prices, as the original "?" list; ships you cannot buy are grey.
    const nets = spec.net_cost_by || {};
    const stats = spec.stats_by || {};
    const blocked = spec.blocked_by || {};
    const open = new Set(spec.choices || []);
    const keys = Object.keys(nets).length ? Object.keys(nets) : (spec.choices || []);
    let picked = false;
    keys.forEach((key) => {
      const o = document.createElement("option");
      o.value = key;
      const s = stats[key];
      const price = s ? fmt(s.cost) + " cr" : (nets[key] != null ? "net " + fmt(nets[key]) + " cr" : "");
      o.textContent = yardName(key, stats) + (price ? " - " + price : "");
      if (!open.has(key)) {
        o.disabled = true;
        o.textContent += " (" + plainWords(blocked[key] || "not for sale to you") + ")";
      } else if (!picked) {
        o.selected = true;
        picked = true;
      }
      sel.appendChild(o);
    });
  }
  function hullPhrase(raw) {
    const key = String(raw || "");
    const name = (SHIPS[key] && SHIPS[key].name) || key.replaceAll("_", " ");
    if (!name) return "";
    return (/^[aeiou]/i.test(name) ? "an " : "a ") + name;
  }
  function gearName(key) {
    const names = {
      armid_mines: "Armid Mines", limpet_mines: "Limpet Mines", mine_disruptor: "Mine Disruptor",
      marker_beacon: "Marker Beacon", psychic_probe: "Psychic Probe", atomic_detonator: "Atomic Detonator",
      atomic_mines: "Atomic Mines", corbomite: "Corbomite",
      photon_missiles: "Photon Missiles", ether_probes: "Ether Probes", genesis_torpedoes: "Genesis Torpedoes",
      genesis: "Genesis Torpedo", cloak: "Cloaking Device", cloaking_device: "Cloaking Device",
      density_scanner: "Density Scanner", holo_scanner: "Holographic Scanner",
      density: "Density Scanner", holo: "Holographic Scanner",
      fighters: "Fighters", shields: "Shields", holds: "Holds",
    };
    return names[key] || String(key || "").replaceAll("_", " ");
  }
  let seenDay = null;
  let taxFresh = true;
  let taxSeenSeq = -1;
  let fellSeenSeq = 0;
  let dayNote = false, dawnLine = "", justActed = false;
  function withDawn(line) {
    if (!(dayNote && dawnLine)) return line;
    const dawn = dawnLine;
    dawnLine = "";
    dayNote = false;
    return String(line || "").replace(/\s+$/, "") + " " + dawn;
  }
  function ferrengiName(name) {
    return String(name || "").replace(/_([A-Za-z0-9]+)/g, " $1").replace(/\s+/g, " ").trim();
  }
  function shipsHere() {
    const s = (S && S.sector) || {};
    const rows = [];
    (s.ferrengi || []).forEach((f) => rows.push({ id: f.id, name: ferrengiName(f.name), owner: "Ferrengi", fighters: f.fighters }));
    (s.aliens || []).forEach((a) => rows.push({ id: a.id, name: a.ship_name || a.name, owner: a.name || "alien", fighters: a.fighters }));
    (s.federals || []).forEach((f) => rows.push({ id: f.name, name: f.name, owner: f.title || "Federation", fighters: null }));
    (s.unmanned_ships || []).forEach((u) => rows.push({ id: u.ship_id || u.id, name: u.name || String(u.hull || "ship").replaceAll("_", " "), owner: u.owner_name || u.owner_id || "unmanned", fighters: u.fighters }));
    return rows;
  }
  function shipTransportLabel(id) {
    const fleet = (((S || {}).fleet || {}).ships || []).find((row) => String(row.ship_id) === String(id));
    if (!fleet) return String(id);
    const name = fleet.name || String(fleet.hull || "ship").replaceAll("_", " ");
    return name + " in sector " + fleet.sector_id;
  }
  function claimSuffix(p) {
    const owned = ((S && S.owned_planets) || []).find((row) => Number(row.id) === Number(p.id));
    const ownerId = p.owner_id != null && p.owner_id !== "" ? p.owner_id : (owned ? S.self_id : null);
    let line = "";
    if (ownerId && ownerId === S.self_id) line = ". Claimed by: " + (S.self_name || "you") + " (you)";
    else if (ownerId) line = ". Claimed by: " + traderName(ownerId);
    else if (Object.prototype.hasOwnProperty.call(p, "owner_id")) line = ". Unclaimed";
    const origin = (owned && owned.origin) || p.origin;
    if (ownerId === S.self_id && origin === "other") line += ". Your home planet";
    return line;
  }
  function traderName(id) {
    if (!id) return "someone";
    if (S && id === S.self_id) return S.self_name || "you";
    const row = ((S && S.other_players) || []).find((r) => r.id === id);
    return (row && row.name) || id;
  }
  function landLine(p) {
    const known = p.fighters != null || p.shields != null;
    const garrison = known ? "Fighters " + fmt(p.fighters || 0) + ", shields " + fmt(p.shields || 0) + "." : "Fighters and shields are not on this scan.";
    if (!p.owner_id || p.owner_id === S.self_id) return "Your planet. " + garrison;
    const holds = traderName(p.owner_id) + " holds this planet. " + garrison;
    if (Number(p.citadel_level || 0) >= 2) return holds + " This planet has a Combat Control computer: its fighters and shields will fight your landing.";
    if (known) return holds + " Its fighters will fight your landing.";
    return holds + " Landing claims it when those fighters are not defending. A defended planet is fought first only when that switch is on.";
  }
  function siegeLosses(facts) {
    const after = Number(facts.defender_s || 0);
    const before = after + Number(facts.planet_shields_lost || 0);
    const remain = facts.attacker_f != null ? Number(facts.attacker_f) : Number(((S && S.ship) || {}).fighters || 0);
    const theirs = fmt(facts.planet_fighters_lost || 0);
    const mine = fmt(facts.attacker_losses || 0);
    let line = "";
    if (before > 0) line += "Planet shields " + fmt(before) + " -> " + fmt(after) + ". ";
    line += "You killed " + theirs + " of the planet's fighters. The planet's reaction and defending fighters killed " + mine + " of your fighters, " + fmt(remain) + " remain";
    return line;
  }
  function siegeSentence(facts) {
    return "Landing repelled: " + siegeLosses(facts);
  }
  function fighterChallengeOpen() {
    const sector = (S && S.sector) || {};
    const challenge = S && S.fighter_challenge;
    if (challenge && (challenge.sector_id == null || Number(challenge.sector_id) === Number(sector.id))) return true;
    const group = sector.fighter_group;
    return !!(group && group.owner_id && group.owner_id !== S.self_id && Number(group.count || 0) > 0);
  }
  function challengeLine() {
    if (!fighterChallengeOpen()) return "";
    const opts = [];
    if (legal("attack")) opts.push("attack");
    if (legal("retreat")) opts.push("retreat");
    if (legal("pay_toll")) opts.push("pay the toll");
    if (legal("surrender")) opts.push("surrender");
    return opts.length ? "Answer the fighters first: " + opts.join(", ") : "";
  }
  function codeBotSuffix(id) {
    const ids = (S && S.code_bots) || [];
    return ids.indexOf(String(id)) >= 0 ? " (code bot)" : "";
  }
  function shipChoiceLabel(id) {
    const ship = shipsHere().find((row) => String(row.id) === String(id));
    if (ship) return (ship.owner === "Ferrengi" ? ferrengiName(ship.name) : ship.name) + ", " + ship.owner + (ship.fighters == null ? "" : ", " + fmt(ship.fighters) + " fighters") + codeBotSuffix(id);
    const roster = ((S && S.other_players) || []).find((row) => row.id === id);
    if (roster) {
      const bits = [roster.name || id];
      if (roster.ship_class) bits.push(hullPhrase(roster.ship_class));
      if (roster.fighters != null) bits.push(fmt(roster.fighters) + " fighters");
      if (roster.shields != null) bits.push(fmt(roster.shields) + " shields");
      return bits.join(", ") + codeBotSuffix(id);
    }
    return String(id).replaceAll("_", " ") + codeBotSuffix(id);
  }
  function newestTax() {
    let best = null;
    streamLog.concat((S && S.recent_events) || []).forEach((ev) => {
      if (!ev || ev.kind !== "tax_collected") return;
      if (ev.actor_id && S && ev.actor_id !== S.self_id) return;
      if (!best || (ev.seq || 0) >= (best.seq || 0)) best = ev;
    });
    const facts = (best && best.facts) || {};
    if (!best || facts.tax == null) return null;
    return best;
  }
  let taxTerms = null;
  async function loadTaxTerms() {
    if (taxTerms) return taxTerms;
    try {
      const data = await api("/" + state.seat + "/reference");
      const tax = data && data.tax;
      if (tax && tax.rate_pct != null && tax.over != null) {
        taxTerms = { rate: Number(tax.rate_pct), over: Number(tax.over) };
      }
    } catch (err) {
      taxTerms = null;
    }
    return taxTerms;
  }
  function taxRulePhrase() {
    if (!taxTerms) return "the dawn tax is taken from the cash on your ship; the bank is not taxed";
    return taxTerms.rate + "% of the cash on your ship when it is over " + fmt(taxTerms.over) + " at dawn; the bank is not taxed";
  }
  function taxSentence(ev) {
    const facts = (ev && ev.facts) || {};
    return "Overnight Federation tax for the night before day " + ev.day + ": " + fmt(facts.tax) + " cr, alignment +" + fmt(facts.align_gain || 0) + ".";
  }
  function overnightTax() {
    const best = newestTax();
    if (!best || Number(best.day) !== Number(S && S.day)) return "";
    if ((best.seq || 0) !== taxSeenSeq) {
      taxSeenSeq = best.seq || 0;
      taxFresh = true;
    }
    if (!taxFresh) return "";
    return taxSentence(best);
  }
  function lastTaxLine() {
    const best = newestTax();
    const today = Number(S && S.day);
    if (!best) return today > 1 ? "Last night: no tax" : "";
    if (Number(best.day) === today) return taxSentence(best);
    return taxSentence(best) + " Last night: no tax";
  }
  function sectorText() {
    const s = S.sector;
    const landed = landedPlanet();
    let t = '<span class="g">Sector  </span><span class="y">:</span> <span class="c">' + s.id + "</span> <span class=\"g\">in</span> <span class=\"c\">" + (s.is_fedspace ? "The Federation" : "uncharted space") + ".</span>\n";
    if (s.port) t += '<span class="g">Ports   </span><span class="y">:</span> <span class="c">' + esc(s.port.name) + '</span><span class="y">,</span> <span class="g">Class</span> <span class="c">' + s.port.class_id + '</span> <span class="w">(</span><span class="m">' + esc(s.port.code) + "</span><span class=\"w\">)</span>\n";
    (s.planets || []).forEach((p) => {
      const cls = p.class ? "(" + p.class + ") " : "";
      t += '<span class="g">Planets </span><span class="y">:</span> <span class="c" data-planet="class">' + esc(cls + (p.name || "planet") + claimSuffix(p)) + "</span>\n";
    });
    if (s.terra) {
      const pool = s.terra.colonists_available != null ? s.terra.colonists_available : 0;
      t += '<span class="g">Planets </span><span class="y">:</span> <span class="c" data-planet="class" data-terra="row">(M) Terra (colonist source, cannot be claimed). Colonists ' + fmt(pool) + "</span>\n";
    }
    if (Number(s.nav_hazard_pct) > 0) {
      t += '<span class="g">NavHaz  </span><span class="y">:</span> <span class="c" data-navhaz="here">' + fmt(s.nav_hazard_pct) + "%</span>\n";
    }
    shipsHere().forEach((ship) => {
      const fig = ship.fighters == null ? "" : ", " + fmt(ship.fighters) + " fighters";
      t += '<span class="g">Ships   </span><span class="y">:</span> <span class="c">' + esc(ship.name + ", " + ship.owner + fig) + "</span>\n";
    });
    (s.occupants || []).forEach((o) => {
      const id = typeof o === "string" ? o : (o.id || "");
      if (id === S.self_id) return;
      const roster = S.other_players || S.others || [];
      const knownTrader = roster.find((row) => row.id === id) || (typeof o === "object" ? o : null);
      const name = knownTrader && knownTrader.name ? knownTrader.name : id;
      const hull = knownTrader && knownTrader.ship_class ? hullPhrase(knownTrader.ship_class) : "";
      const strength = [];
      if (knownTrader && knownTrader.fighters != null) strength.push(fmt(knownTrader.fighters) + " fighters");
      if (knownTrader && knownTrader.shields != null) strength.push(fmt(knownTrader.shields) + " shields");
      t += '<span class="g">Traders </span><span class="y">:</span> <span class="c">' + esc(name + (hull ? " in " + hull : "") + (strength.length ? " (" + strength.join(", ") + ")" : "")) + "</span>\n";
    });
    if (s.fighter_group) {
      const yours = s.fighter_group.owner_id === S.self_id ? " yours" : "";
      const who = traderName(s.fighter_group.owner_id);
      t += '<span class="g">Fighters</span><span class="y">:</span> <span class="c">' + fmt(s.fighter_group.count) + " " + esc(s.fighter_group.mode || "") + yours + " (belong to " + esc(who) + ")</span>\n";
    }
    const mineBits = [];
    (s.mines || []).forEach((row) => {
      const kind = String(row.kind || "");
      if (kind !== "armid" && kind !== "limpet") return;
      const who = traderName(row.owner_id || row.owner);
      mineBits.push(kind + " " + fmt(row.count || 0) + " (belong to " + (who === "personal" || who === "corporate" || who === "rogue" ? "someone" : who) + ")");
    });
    if (mineBits.length) t += '<span class="g">Mines   </span><span class="y">:</span> <span class="c" data-mines="sector">' + esc(mineBits.join(", ")) + "</span>\n";
    if (s.beacon) t += '<span class="g">Beacon  </span><span class="y">:</span> <span class="c" data-beacon="here">' + esc(s.beacon) + "</span>\n";
    t += '<span class="g">Warps to Sector(s) </span><span class="y">:</span> ' + (s.warps_out || []).map((w) => known(w) ? '<span class="c">' + w + "</span>" : '<span class="r">(' + w + ")</span>").join(" - ");
    if (landed) t += '\n<span class="y">You are LANDED on ' + esc(landed.name) + "</span>";
    $("sectorText").innerHTML = t;
  }
  function noteCourse(events) {
    (events || []).forEach((ev) => {
      if (ev.seq != null && !streamSeen.has(ev.seq)) { streamSeen.add(ev.seq); streamLog.push(ev); }
      if (S && ev.kind === "warp" && ev.actor_id === S.self_id) {
        const hopped = ev.facts || {};
        if (hopped.from != null && hopped.to != null && Number(hopped.to) !== Number(hopped.from)) cameFrom = Number(hopped.from);
      }
      if (ev.kind !== "autopilot") return;
      if (!courseEvent || (ev.seq || 0) >= (courseEvent.seq || 0)) courseEvent = ev;
    });
  }
  function syncPlot() {
    const list = ((S && S.recent_events) || []).slice();
    if (courseEvent) list.push(courseEvent);
    let best = null;
    list.forEach((ev) => {
      if (!ev || ev.kind !== "autopilot") return;
      if (!best || (ev.seq || 0) >= (best.seq || 0)) best = ev;
    });
    if (!best || (best.seq || 0) <= ignorePlotSeq) return;
    const facts = best.facts || {};
    if (facts.executed) { plotted = null; return; }
    const path = Array.isArray(facts.path) ? facts.path.map(Number) : [];
    const here = Number(S.sector.id);
    const start = Number(best.sector_id);
    if (!path.length || (here !== start && !path.includes(here))) { plotted = null; return; }
    const draw = here === start || !path.includes(here) ? [here].concat(path) : path.slice(path.indexOf(here));
    plotted = { target: Number(facts.target), path: draw, server: path, seq: best.seq || 0 };
  }
  function mapMetrics() {
    const rect = $("map").getBoundingClientRect();
    const fit = Math.min(rect.width || 300, rect.height || 300) / 600;
    const unit = (fit || 1) * (mapView.k || 1);
    return { font: 20 / unit, hit: 13 / unit };
  }
  function applyMapView() {
    const svg = $("map");
    const g = document.getElementById("mapWorld");
    if (!g) return;
    g.setAttribute("transform", "translate(" + mapView.x + " " + mapView.y + ") scale(" + mapView.k + ")");
    const m = mapMetrics();
    svg.style.setProperty("--map-font", m.font + "px");
    g.querySelectorAll("circle.hit").forEach((c) => c.setAttribute("r", m.hit));
  }
  function arrowHead(x1, y1, x2, y2, from, to) {
    const dx = x2 - x1, dy = y2 - y1;
    const len = Math.hypot(dx, dy) || 1;
    const ux = dx / len, uy = dy / len;
    const tipx = x2 - ux * 16, tipy = y2 - uy * 16;
    const px = -uy * 6, py = ux * 6;
    const bx = tipx - ux * 12, by = tipy - uy * 12;
    return '<polygon class="arrowhead" data-from="' + from + '" data-to="' + to + '" points="' + tipx + "," + tipy + " " + (bx + px) + "," + (by + py) + " " + (bx - px) + "," + (by - py) + '"/>';
  }
  function laneOneWay(from, to) {
    const back = (S.known_warps || {})[String(to)];
    if (!back) return false;
    return !back.map(Number).includes(Number(from));
  }
  function zoomMap(factor, clientX, clientY) {
    const svg = $("map");
    const rect = svg.getBoundingClientRect();
    const cx = clientX == null ? rect.left + rect.width / 2 : clientX;
    const cy = clientY == null ? rect.top + rect.height / 2 : clientY;
    const k0 = mapView.k;
    const k1 = Math.min(8, Math.max(0.4, k0 * factor));
    const vx = ((cx - rect.left) / (rect.width || 1)) * 600 - 300;
    const vy = ((cy - rect.top) / (rect.height || 1)) * 600 - 300;
    const wx = (vx - mapView.x) / k0;
    const wy = (vy - mapView.y) / k0;
    mapView.k = k1;
    mapView.x = vx - wx * k1;
    mapView.y = vy - wy * k1;
    applyMapView();
  }
  function toggleEnlarge(on) {
    mapEnlarged = on != null ? !!on : !mapEnlarged;
    $("nav").classList.toggle("enlarged", mapEnlarged);
    const b = $("mapEnlarge");
    if (b) b.setAttribute("aria-pressed", mapEnlarged ? "true" : "false");
    mapSig = "";
    if (S) map();
  }
  function bindMapPointer(svg) {
    if (svg.dataset.bound) return;
    svg.dataset.bound = "1";
    svg.addEventListener("wheel", (ev) => { ev.preventDefault(); zoomMap(ev.deltaY < 0 ? 1.15 : 1 / 1.15, ev.clientX, ev.clientY); }, { passive: false });
    svg.addEventListener("pointerdown", (ev) => {
      if (ev.button != null && ev.button !== 0) return;
      mapPointers.set(ev.pointerId, { x: ev.clientX, y: ev.clientY });
      if (mapPointers.size === 1) {
        mapPtr = { x: ev.clientX, y: ev.clientY, ox: mapView.x, oy: mapView.y, moved: false };
        mapDownNode = ev.target.closest ? ev.target.closest(".node") : null;
      } else if (mapPointers.size >= 2) mapPinch = { dist: pinchDist(), k: mapView.k };
    });
    svg.addEventListener("pointermove", (ev) => {
      if (!mapPointers.has(ev.pointerId)) return;
      mapPointers.set(ev.pointerId, { x: ev.clientX, y: ev.clientY });
      if (mapPointers.size >= 2 && mapPinch) {
        const dist = pinchDist() || mapPinch.dist;
        mapView.k = Math.min(8, Math.max(0.4, mapPinch.k * (dist / mapPinch.dist)));
        applyMapView();
        return;
      }
      if (!mapPtr) return;
      const dx = ev.clientX - mapPtr.x, dy = ev.clientY - mapPtr.y;
      if (Math.hypot(dx, dy) > 5) mapPtr.moved = true;
      const rect = svg.getBoundingClientRect();
      const scale = 600 / (rect.width || 600);
      mapView.x = mapPtr.ox + dx * scale;
      mapView.y = mapPtr.oy + dy * scale;
      applyMapView();
    });
    svg.addEventListener("pointerup", endPointer);
    svg.addEventListener("pointercancel", endPointer);
    svg.addEventListener("click", () => {
      const node = mapDownNode;
      mapDownNode = null;
      if (mapSuppressClick) { mapSuppressClick = false; return; }
      if (!node) return;
      go(+node.dataset.id);
    });
    function endPointer(ev) {
      const moved = mapPtr && mapPtr.moved && mapPointers.size === 1;
      mapPointers.delete(ev.pointerId);
      if (mapPointers.size < 2) mapPinch = null;
      if (!mapPointers.size) {
        if (moved) mapSuppressClick = true;
        mapPtr = null;
      }
    }
    function pinchDist() {
      const pts = [...mapPointers.values()];
      if (pts.length < 2) return 0;
      return Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y) || 1;
    }
  }
  function oneWaySentence(card) {
    const here = Number(card.from);
    const incoming = [...new Set((card.one_way || []).filter((e) => Number(e.to) === here).map((e) => Number(e.from)))].sort((a, b) => a - b);
    if (cameFrom && incoming.includes(cameFrom)) {
      incoming.splice(incoming.indexOf(cameFrom), 1);
      incoming.unshift(cameFrom);
    }
    if (!incoming.length || Number(card.hops) <= 1) return "";
    return incoming.slice(0, 3).map((pick) => here + " -> " + pick + " is one-way (" + pick + " -> " + here + " only), so the shortest way back is " + card.hops + " hops.").join(" ");
  }
  async function loadCourse(target) {
    const row = await api("/" + state.seat + "/route?target=" + encodeURIComponent(target));
    if (!row || row.ok === false) { setResult("REFUSED — " + plainWords((row && row.error) || "no route"), true); return; }
    row.note = oneWaySentence(row);
    courseCard = row;
    const hops = (row.path || []).map(Number);
    const full = [Number(row.from)].concat(hops);
    const turns = Number(row.total_turns || 0);
    const sentence = "plotted course " + full.join(" > ") + ", " + hops.length + " hops" + (turns ? ", " + turns + " turns" : "");
    rememberLine(sentence);
    mapSig = "";
    await refresh();
    setResult(sentence);
  }
  function paintCourse() {
    const box = $("course");
    if (!box) return;
    if (!courseCard || !S) { box.hidden = true; box.innerHTML = ""; return; }
    const here = Number(S.sector.id);
    const hops = (courseCard.path || []).map(Number);
    const on = here === Number(courseCard.from) || hops.includes(here);
    box.hidden = false;
    if (!on) {
      box.innerHTML = '<div data-testid="off-course">Off course - re-plot to ' + courseCard.target + '?</div><button type="button" data-testid="replot">Re-plot</button>';
      box.querySelector("[data-testid=replot]").addEventListener("click", () => loadCourse(courseCard.target));
      return;
    }
    const full = [Number(courseCard.from)].concat(hops);
    let html = '<div data-testid="course-line">Course to ' + courseCard.target + ": " + full.join(" > ") + ". " + hops.length + " hops, " + Number(courseCard.total_turns || 0) + " turns.</div>";
    if (courseCard.note) html += '<div data-testid="one-way-note">' + esc(courseCard.note) + "</div>";
    if (courseCard.avoiding && courseCard.avoiding.length) html += '<button type="button" data-testid="avoid-link">Avoiding: ' + courseCard.avoiding.join(", ") + "</button>";
    const hopCost = Number(courseCard.turns_per_hop || 0);
    const left = Number((S && S.turns_remaining) || 0);
    const grey = hopCost > left ? " dim" : "";
    html += '<button type="button" class="eng' + grey + '" data-testid="engage">Engage Express</button><button type="button" data-testid="course-cancel">Cancel</button>';
    box.innerHTML = html;
    box.querySelector("[data-testid=engage]").addEventListener("click", engage);
    box.querySelector("[data-testid=course-cancel]").addEventListener("click", () => { courseCard = null; mapSig = ""; map(); });
    const avoid = box.querySelector("[data-testid=avoid-link]");
    if (avoid) avoid.addEventListener("click", () => avoidForm());
  }
  function map() {
    syncPlot();
    if (courseCard && S) {
      const here = Number(S.sector.id);
      const hops = (courseCard.path || []).map(Number);
      if (here === Number(courseCard.from) || hops.includes(here)) {
        const draw = here === Number(courseCard.from) ? [here].concat(hops) : hops.slice(hops.indexOf(here));
        plotted = { target: Number(courseCard.target), path: draw, server: hops, seq: (plotted && plotted.seq) || 0, free: true };
      }
    }
    paintCourse();
    const svg = $("map");
    const hereId = Number(S.sector.id);
    const path = (plotted && plotted.path) || [];
    const serverPath = (plotted && plotted.server) || [];
    const cost = Number((LA("warp") || {}).turn_cost || 0);
    const oneWays = (S.sector.warps_out || []).filter((w) => oneWay(w));
    const sig = JSON.stringify([hereId, serverPath, plotted && plotted.target, S.sector.warps_out, oneWays, (S.known_sectors || []).map((k) => k.id), state.awaiting, state.busy, cost, S.planet_landed]);
    if (sig === mapSig && svg.childElementCount) return;
    mapSig = sig;
    const known = {};
    (S.known_sectors || []).forEach((k) => { known[Number(k.id)] = k; });
    if (!known[hereId]) known[hereId] = { id: hereId, port: S.sector.port };
    path.forEach((id) => { if (!known[id]) known[id] = { id: id }; });
    (S.sector.warps_out || []).forEach((w) => {
      const id = Number(w);
      if (!known[id]) known[id] = { id: id, unexplored: true };
    });
    const warps = S.known_warps || {};
    const dist = {};
    dist[hereId] = 0;
    const queue = [hereId];
    while (queue.length) {
      const current = queue.shift();
      (warps[current] || warps[String(current)] || []).forEach((next) => {
        const id = Number(next);
        if (dist[id] == null) { dist[id] = dist[current] + 1; queue.push(id); }
      });
    }
    path.forEach((id, i) => { if (dist[id] == null) dist[id] = i; });
    (S.sector.warps_out || []).forEach((w) => { const id = Number(w); if (dist[id] == null) dist[id] = 1; });
    const children = {};
    const seenNode = new Set([hereId]);
    const walk = [hereId];
    while (walk.length) {
      const current = walk.shift();
      const nexts = (warps[current] || warps[String(current)] || []).map(Number);
      if (current === hereId) (S.sector.warps_out || []).forEach((w) => { if (!nexts.includes(Number(w))) nexts.push(Number(w)); });
      nexts.forEach((id) => {
        if (!known[id] || seenNode.has(id)) return;
        seenNode.add(id);
        (children[current] = children[current] || []).push(id);
        walk.push(id);
      });
    }
    Object.keys(known).forEach((id) => {
      const n = Number(id);
      if (seenNode.has(n)) return;
      seenNode.add(n);
      (children[hereId] = children[hereId] || []).push(n);
    });
    const pos = {};
    pos[hereId] = [0, 0];
    (function place(id, a0, a1, depth) {
      const kids = (children[id] || []).slice().sort((a, b) => a - b);
      if (!kids.length) return;
      const span = a1 - a0;
      kids.forEach((kid, i) => {
        const t0 = a0 + (span * i) / kids.length;
        const t1 = a0 + (span * (i + 1)) / kids.length;
        let mid = (t0 + t1) / 2;
        if (kids.length === 1) mid += depth % 2 === 0 ? 0.7 : -0.7;
        const radius = Math.min(240, 62 + depth * 38);
        pos[kid] = [Math.cos(mid) * radius, Math.sin(mid) * radius];
        place(kid, t0, t1, depth + 1);
      });
    })(hereId, -Math.PI, Math.PI, 1);
    path.forEach((id, i) => {
      if (!i) { pos[id] = [0, 0]; return; }
      const t = i / Math.max(1, path.length - 1);
      const angle = -2.4 + t * 2.2;
      pos[id] = [Math.cos(angle) * (55 + t * 170), Math.sin(angle) * (55 + t * 150)];
    });
    const ids = Object.keys(pos).map(Number).filter((id) => id !== hereId);
    const edges = [];
    Object.entries(warps).forEach(([from, tos]) => (tos || []).forEach((to) => {
      const a = Number(from), b = Number(to);
      if (pos[a] && pos[b]) edges.push([a, b]);
    }));
    (S.sector.warps_out || []).forEach((w) => { if (pos[Number(w)]) edges.push([hereId, Number(w)]); });
    for (let pass = 0; pass < 5; pass++) {
      edges.forEach(([a, b]) => {
        const ax = pos[a], bx = pos[b];
        ids.forEach((id) => {
          if (id === a || id === b) return;
          const p = pos[id];
          const dx = bx[0] - ax[0], dy = bx[1] - ax[1];
          const len2 = dx * dx + dy * dy || 1;
          let t = ((p[0] - ax[0]) * dx + (p[1] - ax[1]) * dy) / len2;
          if (t < 0.12 || t > 0.88) return;
          const x = ax[0] + t * dx, y = ax[1] + t * dy;
          const gap = Math.hypot(p[0] - x, p[1] - y);
          if (gap > 22) return;
          const nx = -dy, ny = dx;
          const nlen = Math.hypot(nx, ny) || 1;
          pos[id] = [p[0] + (nx / nlen) * (28 - gap), p[1] + (ny / nlen) * (28 - gap)];
        });
      });
    }
    const metrics = mapMetrics();
    const minDist = metrics.hit * 2.4;
    for (let pass = 0; pass < 14; pass++) {
      for (let i = 0; i < ids.length; i++) {
        for (let j = i + 1; j < ids.length; j++) {
          const a = pos[ids[i]], b = pos[ids[j]];
          const dx = b[0] - a[0], dy = b[1] - a[1];
          const dist = Math.hypot(dx, dy) || 0.01;
          if (dist >= minDist) continue;
          const push = (minDist - dist) / 2;
          const ux = dx / dist, uy = dy / dist;
          a[0] -= ux * push; a[1] -= uy * push;
          b[0] += ux * push; b[1] += uy * push;
        }
      }
    }
    let html = '<g id="mapWorld">';
    const seen = new Set();
    function addLane(a, b, extra) {
      if (!pos[a] || !pos[b]) return;
      const one = laneOneWay(a, b) && !laneOneWay(b, a);
      const other = laneOneWay(b, a) && !laneOneWay(a, b);
      const key = one || other ? "d" + a + ">" + b : "u" + [a, b].sort().join();
      if (seen.has(key) || (other && seen.has("d" + b + ">" + a))) return;
      seen.add(key);
      const x1 = pos[a][0], y1 = pos[a][1], x2 = pos[b][0], y2 = pos[b][1];
      let cls = "lane" + (extra || "");
      let arrow = "";
      let from = a, to = b;
      if (one) { cls += " oneway"; arrow = arrowHead(x1, y1, x2, y2, a, b); }
      else if (other) { cls += " oneway"; arrow = arrowHead(x2, y2, x1, y1, b, a); from = b; to = a; }
      html += '<line class="' + cls + '" data-from="' + from + '" data-to="' + to + '" x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 + '"/>' + arrow;
    }
    Object.entries(warps).forEach(([from, tos]) => (tos || []).forEach((to) => addLane(Number(from), Number(to), "")));
    (S.sector.warps_out || []).forEach((w) => {
      const b = Number(w);
      const unk = known[b] && known[b].unexplored ? " unk" : "";
      addLane(hereId, b, unk);
    });
    for (let i = 1; i < path.length; i++) {
      const a = pos[path[i - 1]], b = pos[path[i]];
      if (!a || !b) continue;
      html += '<line class="lane route" x1="' + a[0] + '" y1="' + a[1] + '" x2="' + b[0] + '" y2="' + b[1] + '"/>';
    }
    const labels = [];
    Object.values(known).forEach((k) => {
      const id = Number(k.id);
      const at = pos[id] || [0, 0];
      const gap = metrics.font;
      let lx = at[0] + gap * 0.55, ly = at[1] + gap * 0.25;
      for (let n = 0; n < 8 && labels.some((p) => Math.hypot(p[0] - lx, p[1] - ly) < gap); n++) ly += gap * 0.85;
      labels.push([lx, ly]);
      const adj = (S.sector.warps_out || []).map(Number).includes(id);
      const cls = ["node", id === hereId ? "here" : "", adj ? "adj" : "", k.unexplored ? "unk" : "", k.port ? "port" : "", plotted && plotted.target === id ? "tgt" : ""].join(" ");
      const r = id === hereId ? 11 : adj ? 9 : 6;
      html += '<g class="' + cls + '" data-id="' + id + '"><circle cx="' + at[0] + '" cy="' + at[1] + '" r="' + r + '"/><circle class="hit" cx="' + at[0] + '" cy="' + at[1] + '" r="' + metrics.hit + '"/><text x="' + lx + '" y="' + ly + '" font-size="' + metrics.font + '">' + id + "</text></g>";
    });
    html += "</g>";
    svg.innerHTML = html;
    applyMapView();
    bindMapPointer(svg);
    svg.setAttribute("data-route", serverPath.join(","));
    const row = $("warps");
    row.innerHTML = '<span class="g">Warps:</span> ';
    (S.sector.warps_out || []).forEach((w, i) => {
      const b = document.createElement("button");
      b.type = "button";
      const way = oneWay(w);
      b.textContent = (i + 1) + ":" + w + (cost ? " (" + cost + "t)" : "") + (way ? " one-way" : "");
      if (way) b.className = "oneway";
      const turnsLeft = Number((S && S.turns_remaining) || 0);
      const hop = Number(cost || 0);
      if (hop > turnsLeft) b.classList.add("dim");
      b.disabled = state.busy;
      b.addEventListener("click", () => {
        if (S.planet_landed != null) { setResult("Lift off first", true); return; }
        if (hop > Number((S && S.turns_remaining) || 0)) {
          setResult("Move: out of turns (" + (S.turns_remaining || 0) + " left, needs " + hop + ")", true);
          return;
        }
        if (!legal("warp")) { setResult("Move: " + plainReason((LA("warp") || {}).reason), true); return; }
        act("warp", { target: w }, "warp to " + w);
      });
      row.appendChild(b);
    });
    if (!courseCard && plotted && path.length > 1) {
      const hops = serverPath.length;
      const hopCost = Number((((LA("plot_course") || {}).params || {}).execute || {}).first_hop_turns || cost || 0);
      const eng = document.createElement("button");
      eng.type = "button";
      eng.className = "eng";
      eng.textContent = "ENGAGE  " + hops + " hops, " + (hops * hopCost) + " turns";
      if (hopCost > Number((S && S.turns_remaining) || 0)) eng.classList.add("dim");
      eng.addEventListener("click", engage);
      const cancel = document.createElement("button");
      cancel.type = "button";
      cancel.textContent = "✕";
      cancel.addEventListener("click", () => { ignorePlotSeq = plotted.seq || ignorePlotSeq; plotted = null; mapSig = ""; map(); });
      row.appendChild(eng);
      row.appendChild(cancel);
    }
  }
  function oneWay(id) {
    const back = (S.known_warps || {})[String(id)];
    if (!back) return false;
    return !back.map(Number).includes(Number(S.sector.id));
  }
  function go(id) {
    if (mapSuppressClick) return;
    if (!S || Number(id) === Number(S.sector.id)) return;
    if ((S.sector.warps_out || []).map(Number).includes(Number(id))) {
      if (S.planet_landed != null) { setResult("Lift off first", true); return; }
      return act("warp", { target: id }, "warp to " + id);
    }
    loadCourse(id);
  }
  function engage() {
    const target = courseCard ? courseCard.target : (plotted && plotted.target);
    if (target == null) return;
    if (S && S.planet_landed != null) { setResult("REFUSED — Lift off first", true); return; }
    const hopCost = Number((courseCard && courseCard.turns_per_hop) || (((LA("plot_course") || {}).params || {}).execute || {}).first_hop_turns || 0);
    const left = Number((S && S.turns_remaining) || 0);
    if (hopCost > left) { setResult("REFUSED — first hop unaffordable (need " + hopCost + " turns, have " + left + ").", true); return; }
    act("plot_course", { target: target, execute: true }, "engage course to " + target);
  }

  function paintShip() {
    const sh = S.ship || {};
    const def = SHIPS[sh.class] || { name: String(sh.class || "ship").replaceAll("_", " "), kind: "arrow", len: 150, beam: 48, engines: 2, accent: "#7aa2ff", detail: "bridge" };
    $("shipName").textContent = def.name.toUpperCase();
    $("shipCls").textContent = String(sh.class || "ship").replaceAll("_", " ");
    paintShipView(sh, def);
    const used = Object.values(sh.cargo || {}).reduce((a, b) => a + Number(b || 0), 0);
    const bar = (k, v, c, col) => '<div class="bar"><span>' + k + '</span><span class="t"><span class="f" style="width:' + (c ? Math.min(100, v / c * 100) : 0) + "%;background:" + col + '"></span></span><span class="w">' + fmt(v) + '<span class="dk">/' + fmt(c) + "</span></span></div>";
    const mines = sh.mines || {};
    const mineRow = (name, n) => '<div class="bar" data-mines="' + name + '"><span>' + name + ' mines</span><span class="w">' + fmt(n) + "</span></div>";
    const limpets = Number((((LA("remove_limpet") || {}).params || {}).attached) || 0);
    const tow = (sh.tow || {}).target;
    const towText = tow ? "Towing " + (tow.name || String(tow.hull || tow.kind || "a ship").replaceAll("_", " ")) : "Towing nothing";
    const countRow = (key, label, n) => '<div class="bar" data-gear="' + key + '"><span>' + label + '</span><span class="w">' + fmt(n) + "</span></div>";
    $("shipStats").innerHTML = bar("Fighters", sh.fighters, sh.fighter_cap, "#ff5555") + bar("Shields", sh.shields, sh.shield_cap, "#55ffff") + bar("Holds", used, sh.holds, "#ffff55")
      + mineRow("armid", Number(mines.armid || 0)) + mineRow("limpet", Number(mines.limpet || 0))
      + countRow("cloaks", "Cloaks", Number(sh.cloaks || 0))
      + countRow("disruptors", "Disruptors", Number(sh.mine_disruptors || 0))
      + '<div class="bar" data-gear="limpet"' + (limpets ? "" : " hidden") + '><span class="r">Limpet attached</span><span class="w">' + fmt(limpets) + "</span></div>"
      + '<div class="bar" data-gear="tow"><span>' + esc(towText) + "</span></div>";
    const carried = [
      ["atomic", "Atomic mines", Number(mines.atomic || 0)],
      ["ether", "Ether probes", Number(sh.ether_probes || 0)],
      ["genesis", "Genesis", Number(sh.genesis || 0)],
      ["photons", "Photons", Number(sh.photon_missiles || 0)],
      ["corbomite", "Corbomite", Number(sh.corbomite || 0)],
      ["beacons", "Beacons", Number(sh.marker_beacons || 0)],
      ["psychic", "Psychic probe", Number(sh.psychic_probe || 0)],
      ["detonator", "Atomic detonator", Number(sh.atomic_detonators || 0)],
    ];
    carried.forEach(([key, label, n]) => { if (n) $("shipStats").insertAdjacentHTML("beforeend", countRow(key, label, n)); });
    if (sh.scanner) $("shipStats").insertAdjacentHTML("beforeend", '<div class="bar" data-gear="scanner"><span>Scanner</span><span class="w">' + esc(gearName(sh.scanner)) + "</span></div>");
    const paid = sh.cargo_cost_avg || {};
    $("holds").innerHTML = Object.entries(COM).map(([k, row]) => {
      const avg = paid[k];
      const price = avg ? '<div class="dk" data-paid="' + k + '">paid ' + fmt(avg) + " cr</div>" : "";
      return '<div class="hold"><b>' + row[0] + "</b><br>" + fmt((sh.cargo || {})[k]) + price + "</div>";
    }).join("");
    const root = $("viewport");
    if (root && window.TW2KViewport) window.TW2KViewport.update(S);
  }

  function tradeWhy(commodity, stock, ship, side) {
    const name = (COM[commodity] || [commodity])[0];
    const server = ((((LA("trade") || {}).params || {}).why) || {})[commodity];
    if (server) return server;
    const onboard = Number((ship.cargo || {})[commodity] || 0);
    const used = Object.values(ship.cargo || {}).reduce((sum, n) => sum + Number(n || 0), 0);
    const cur = Number(stock.current || 0);
    const max = Number(stock.max || 0);
    const room = Math.max(0, max - cur);
    if (side === "buy" && cur <= 0) return name + ": port has 0 of " + fmt(max) + " to sell today (refills ~5%/day)";
    if (side === "sell" && onboard <= 0) return name + ": port buys, but you have none on board";
    if (side === "sell" && room <= 0) return name + ": port is full, it will not buy more today";
    if (side === "buy" && used >= Number(ship.holds || 0)) return name + ": no empty holds";
    if (side === "buy" && stock.price && S.credits < Number(stock.price)) return name + ": not enough credits for 1 unit (" + fmt(stock.price) + " cr)";
    return "Nothing to trade";
  }
  function plainReason(text) {
    if (!state.awaiting) return outOfTurns() ? noTurnsLine() : "Waiting for your turn.";
    return plainWords(text || "not available here");
  }
  function maxBy(kind, commodity, side) {
    const p = (LA(kind) || {}).params || {};
    return (((p.qty || {}).max_by || {})[commodity] || {})[side] || 0;
  }
  function reveal(el) {
    if (!el) return;
    try { el.scrollIntoView({ block: "center", inline: "nearest" }); } catch (e) { /* keep the form */ }
    const focus = el.querySelector("input, select, textarea, button");
    if (focus && focus.focus) {
      try { focus.focus(); } catch (e) { /* a hidden panel */ }
    }
  }
  function button(label, fn, extra) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "verb";
    b.innerHTML = label;
    if (extra) Object.assign(b, extra);
    b.addEventListener("click", fn);
    return b;
  }
  function keepTouched(saved, touched) {
    document.querySelectorAll("#formSlot [data-n]").forEach((el) => {
      const name = el.dataset.n;
      if (!touched.has(name) || !(name in saved)) return;
      el.dataset.touched = "1";
      if (el.type === "checkbox") { el.checked = !!saved[name]; return; }
      const want = String(saved[name]);
      if (el.value === want) return;
      if (el.tagName === "SELECT" && !Array.from(el.options).some((o) => o.value === want)) return;
      el.value = want;
      if (el.tagName !== "SELECT") el.dispatchEvent(new Event("input", { bubbles: true }));
    });
  }
  function markTouched(ev) {
    const el = ev.target;
    if (el && el.dataset && el.dataset.n && el.closest && el.closest("#formSlot")) el.dataset.touched = "1";
  }
  function here() {
    const saved = {};
    const touched = new Set();
    let restore = openFormKind;
    if (onSurface() && (restore === "fighters" || restore === "mines")) {
      openFormKind = null;
      restore = null;
    }
    if (restore) {
      const active = document.activeElement;
      if (active && active.dataset && active.dataset.n) formFocus = active.dataset.n;
      document.querySelectorAll("#formSlot [data-n]").forEach((el) => {
        saved[el.dataset.n] = el.dataset.t === "bool" ? el.checked : el.value;
        if (el.dataset.touched) touched.add(el.dataset.n);
      });
    }
    const box = $("here");
    box.innerHTML = "";
    const s = S.sector, sh = S.ship || {};
    const landed = landedPlanet();
    if (landed) {
      const card = document.createElement("div");
      card.className = "planet";
      const yours = landed.owner_id === S.self_id;
      const claim = !landed.owner_id ? "Unclaimed"
        : (yours ? "Claimed by: " + (S.self_name || "you") + " (you)" : "Claimed by: " + traderName(landed.owner_id));
      const home = yours && landed.origin === "other" ? " Your home planet" : "";
      let body = '<div class="y">' + esc(landed.name || "planet") + "</div>";
      body += '<div data-claim="owner">Class <span class="c">' + esc(landed.class || "?") + "</span>  " + esc(claim + home) + "</div>";
      const building = landed.citadel_target && Number(landed.citadel_target) > Number(landed.citadel_level || 0);
      body += '<div data-citadel="level">Citadel <span class="c">' + (building ? "building toward " + landed.citadel_target : "level " + (landed.citadel_level || 0)) + "</span>";
      if (building && landed.citadel_complete_day) body += '  ready day <span class="y">' + landed.citadel_complete_day + "</span>";
      body += '  Fighters <span class="c">' + fmt(landed.fighters || 0) + '</span>  Shields <span class="c">' + fmt(landed.shields || 0) + "</span></div>";
      const perks = [[1, "Treasury"], [2, "Combat Control Computer"], [3, "Quasar cannon"], [4, "Planet TransWarp"], [5, "Planetary shields"], [6, "Interdictor"]];
      const unlocked = perks.filter((row) => row[0] <= Number(landed.citadel_level || 0)).map((row) => row[1]);
      if (unlocked.length) body += '<div data-perk="now">' + esc(unlocked.join(". ")) + ".</div>";
      const owned = landed.id != null && landed.owner_id === S.self_id
        ? (S.owned_planets || []).find((row) => row.id === landed.id)
        : null;
      let production = landed.production;
      if (!production && owned && owned.production) production = owned.production;
      ["fuel_ore", "organics", "equipment"].forEach((k) => {
        const meta = COM[k] || [k, "#fff"];
        const cols = (landed.colonists || {})[k] || 0;
        const stock = (landed.stockpile || {})[k] || 0;
        const made = production ? (production[k] || 0) : null;
        let shown = made;
        let why = "";
        if (k === "organics" && made != null) {
          const eat = Number((owned && owned.organics_consumption_per_day) || 0);
          if (eat > 0 && Number(stock) + Number(made) > 0) {
            const burned = Math.min(eat, Number(stock) + Number(made));
            shown = Math.max(0, Number(made) - burned);
            if (burned > 0 && shown !== Number(made)) why = ", colonists eat " + fmt(burned);
          }
        }
        body += '<div style="color:' + meta[1] + '" data-day="' + k + '">' + esc(meta[0]) + '</div><div class="c">Colonists ' + fmt(cols) + "  On planet " + fmt(stock) + (shown == null ? "" : "  " + fmt(shown) + " per day" + why) + "</div>";
      });
      if (owned && owned.fighters_per_day != null) body += '<div data-day="fighters">Fighters</div><div class="c">' + fmt(owned.fighters_per_day) + " per day</div>";
      const trend = (owned && owned.colonists_text) || landed.colonists_text;
      if (trend) body += '<div data-colonists="trend">' + esc(trend) + "</div>";
      body += '<div data-quasar="now">Quasar sector ' + (landed.quasar_sector_pct || 0) + "%, atmosphere " + (landed.quasar_atm_pct || 0) + "%</div>";
      body += '<div data-reaction="pct">Military reaction ' + fmt(landed.military_reaction_pct || 0) + "%</div>";
      if (landed.treasury != null) {
        const dep = LA("deposit_treasury");
        const room = dep && dep.params ? dep.params.room : null;
        const cap = dep && dep.params ? dep.params.capacity : null;
        let treasuryLine = "Treasury " + fmt(landed.treasury) + " cr";
        if (room != null && cap) treasuryLine += ". Room " + fmt(room) + " of " + fmt(cap) + " cr";
        body += '<div data-treasury="balance">' + treasuryLine + "</div>";
      }
      const planetFuel = Number((landed.stockpile || {}).fuel_ore || 0);
      body += '<div data-range="transporter">Planet fuel ' + fmt(planetFuel) + " ore. " + (landed.has_transporter ? "Transporter range " + fmt(Math.floor(planetFuel / 10)) + " sectors at 10 ore each." : "No transporter (buy one).") + "</div>";
      card.innerHTML = body;
      box.appendChild(card);
      box.appendChild(button("<kbd>Q</kbd>Lift off", () => act("liftoff", {}, "lift off")));
      PLANET_KEYS.filter((row) => row[2]).forEach(([k, label, kind]) => {
        box.appendChild(button("<kbd>" + k + "</kbd>" + label, () => planetAct(k)));
      });
      const pid = landed.id;
      box.appendChild(reasonButton("deposit_treasury", "Treasury deposit", () => treasuryForm("deposit")));
      box.appendChild(reasonButton("withdraw_treasury", "Treasury withdraw", () => treasuryForm("withdraw")));
      box.appendChild(reasonButton("set_quasar_sector", "Quasar sector", () => quasarForm("set_quasar_sector")));
      box.appendChild(reasonButton("set_quasar_atm", "Quasar atmosphere", () => quasarForm("set_quasar_atm")));
      box.appendChild(reasonButton("planet_transwarp", "Planet TransWarp", () => jumpForm("planet_transwarp")));
      box.appendChild(reasonButton("planet_buy_transporter", "Buy transporter", () => confirmWords("Buy transporter", "Buy a transporter for 50,000 cr?", () => act("planet_buy_transporter", { planet_id: pid }, "buy transporter"))));
      box.appendChild(reasonButton("planet_transport", "Use transporter", () => jumpForm("planet_transport")));
      box.appendChild(reasonButton("claim_planet", "Claim planet", () => act("claim_planet", { planet_id: pid }, "claim planet")));
      box.appendChild(reasonButton("planet_destroy", "Destroy planet", () => confirmWords("Destroy planet", "Destroy " + (landed.name || "this planet") + "? This cannot be undone.", () => act("planet_destroy", { planet_id: pid }, "destroy planet"))));
    }
    const mail = (S.inbox || []).filter((row) => row && (row.message || row.text));
    if (mail.length) {
      const line = document.createElement("div");
      line.className = "y";
      line.dataset.mail = "unread";
      line.textContent = "Mail: " + mail.length + " unread. " + (mail[0].message || mail[0].text);
      box.appendChild(line);
    }
    const stockRows = (s.port && s.port.stock) || {};
    if (s.port && !landed && Object.keys(stockRows).length) {
      const cap = document.createElement("div");
      cap.className = "c";
      cap.dataset.port = "code";
      cap.textContent = "Port " + (s.port.name || "") + " " + (s.port.code || "");
      box.appendChild(cap);
      const table = document.createElement("table");
      table.className = "porttbl";
      // cockpit-gaps-v1 item 3: the original commerce table header is 'Items Status Trading % of max OnBoard'
      // (transcript.txt 2441). The % column shows only with the cockpit block on.
      table.innerHTML = CK
        ? "<tr><th>Items</th><th>Status</th><th>Trading</th><th>% of max</th><th>Price</th><th>OnBoard</th><th></th></tr>"
        : "<tr><th>Items</th><th>Status</th><th>Trading</th><th>Price</th><th>OnBoard</th><th></th></tr>";
      Object.entries(stockRows).forEach(([k, v]) => {
        const meta = COM[k] || [k, "#fff"];
        const side = v.side === "buys_from_player" ? "sell" : "buy";
        const mx = maxBy("trade", k, side);
        const room = Math.max(0, Number(v.max || 0) - Number(v.current || 0));
        const trading = side === "sell" ? room : Number(v.current || 0);
        const status = side === "sell" ? "Buying, room " + fmt(room) : "Selling " + fmt(v.current) + "/" + fmt(v.max);
        const tr = document.createElement("tr");
        const pctCell = CK ? "<td class=\"pct\" data-pct=\"" + k + "\">" + (Number(v.max) > 0 ? Math.round(100 * trading / Number(v.max)) : 0) + "%</td>" : "";
        tr.innerHTML = "<td style=\"color:" + meta[1] + "\">" + esc(meta[0]) + "</td><td>" + status + "</td><td class=\"c\">" + fmt(trading) + "</td>" + pctCell + "<td class=\"y\">" + (v.price ?? "") + "</td><td class=\"w\">" + (sh.cargo[k] || 0) + "</td><td></td>";
        if (mx > 0 && legal("trade") && state.awaiting) {
          const b = document.createElement("button");
          b.type = "button";
          b.className = "tbtn " + side;
          b.textContent = (side === "sell" ? "SELL " : "BUY ") + mx;
          b.addEventListener("click", () => act("trade", { side, commodity: k, qty: mx }, side + " " + mx + " " + meta[0]));
          tr.lastChild.appendChild(b);
        } else {
          const why = mx > 0 && legal("trade") && !state.awaiting ? "Waiting for your turn." : tradeWhy(k, v, sh, side);
          tr.lastChild.textContent = why;
          const priceCell = tr.children[CK ? 4 : 3];
          if (priceCell) priceCell.classList.add("dim");
          tr.addEventListener("click", () => setResult(why, true));
        }
        table.appendChild(tr);
      });
      box.appendChild(table);
    }
    const ships = shipsHere();
    if (!landed && ships.length) {
      const line = document.createElement("div");
      line.className = "c";
      line.dataset.ships = "here";
      line.textContent = ships.map((ship) => ship.name + ", " + ship.owner + (ship.fighters == null ? "" : ", " + fmt(ship.fighters) + " fighters")).join(" / ");
      box.appendChild(line);
    }
    const taxLine = overnightTax();
    if (taxLine) {
      const tax = document.createElement("div");
      tax.className = "y";
      tax.dataset.tax = "overnight";
      tax.textContent = taxLine;
      box.appendChild(tax);
    }
    if (!landed) (s.planets || []).forEach((p) => {
      box.appendChild(button("<kbd>L</kbd>Land on " + esc(p.name), () => {
        confirmWords("Land", landLine(p), () => act("land_planet", { planet_id: p.id }, "land on " + p.name));
      }));
    });
    if (Number(s.id) === 1 || (s.port && /stardock/i.test(String(s.port.name || "")))) {
      // NOTE 71. The three StarDock buttons stay in this order. One that
      // cannot be used is grey, with its reason, and is never removed.
      box.appendChild(reasonButton("buy_equip", "StarDock: buy gear", () => openForm("buy_equip")));
      const terra = LA("terra_colonists") || {};
      const terraBtn = button("Load colonists (Terra)", () => {
        if (!terra.legal) { setResult(plainReason(terra.reason || "Terra colonists unavailable here"), true); return; }
        terraForm();
      });
      if (!terra.legal) {
        terraBtn.disabled = true;
        terraBtn.classList.add("dim");
        terraBtn.title = plainReason(terra.reason || "Terra colonists unavailable here");
      }
      box.appendChild(terraBtn);
      box.appendChild(reasonButton("buy_ship", "Shipyards", () => openForm("buy_ship")));
      const bankLegal = legal("bank_deposit") || legal("bank_withdraw");
      const bankWhy = plainReason((LA("bank_deposit") || {}).reason || (LA("bank_withdraw") || {}).reason || "the bank is not open");
      const bankBtn = document.createElement("button");
      bankBtn.type = "button";
      bankBtn.className = "verb";
      bankBtn.dataset.kind = "bank";
      bankBtn.textContent = "Bank";
      if (!bankLegal) {
        bankBtn.classList.add("dim");
        bankBtn.title = bankWhy;
        bankBtn.addEventListener("click", () => setResult("Bank: " + bankWhy, true));
      } else bankBtn.addEventListener("click", () => bankForm());
      box.appendChild(bankBtn);
      box.appendChild(dockBox());
    }
    box.appendChild(spaceBox());
    box.appendChild(defenseBox());
    const slot = document.createElement("div");
    slot.id = "formSlot";
    box.appendChild(slot);
    if (restore === "bank") bankForm(saved);
    else if (restore === "fighters") fighterForm(saved);
    else     if (restore === "mines") mineForm(saved);
    else if (restore === "reaction") reactionForm(saved);
    else if (restore === "disruptor") disruptorForm(saved);
    else if (restore === "transwarp") transwarpForm(saved);
    else if (restore === "terra") terraForm(saved);
    else if (restore === "treasury") treasuryForm(saved && saved.side, saved);
    else if (restore === "quasar") quasarForm(saved && saved.kind, saved);
    else if (restore === "jump") jumpForm(saved && saved.kind, saved);
    else if (restore === "memo") memoForm(saved);
    else if (restore === "corpPassword") passwordForm(saved);
    else if (restore === "join") joinForm(saved);
    else if (restore === "drop") dropForm(null, saved);
    else if (restore === "transfer") transferForm(null, saved);
    else if (restore === "tavernText") tavernText(saved && saved.which, saved);
    else if (restore === "tavernOrder") tavernOrder(saved);
    else if (restore === "grimyAsk") grimyAsk(saved);
    else if (restore === "ugEnter") ugEnter(saved);
    else if (restore === "ugContract") ugContract(saved);
    else if (restore === "postReward") postReward(saved);
    else if (restore === "shipPassword") shipPassword(saved);
    else if (restore === "sellShip") sellShip(saved);
    else if (restore === "bankWire") bankWire(saved);
    else if (restore === "rob") robForm(saved);
    else if (restore === "steal") stealForm(saved);
    else if (restore === "portUpgrade") upgradeForm(saved);
    else if (restore === "portBuild") buildForm(saved);
    else if (restore === "planetTrade") tradeForm(saved);
    else if (restore === "atomic") atomicForm(saved);
    else if (restore === "avoid") avoidForm(saved);
    else if (restore === "hail") hailForm(saved);
    else if (restore === "jettison") jettisonForm(saved);
    else if (restore) openForm(restore, saved);
    if (restore && touched.size) keepTouched(saved, touched);
  }
  function openForm(kind, saved) {
    if (kind === "bank") { bankForm(saved); return; }
    if (kind === "fighters") { fighterForm(saved); return; }
    if (kind === "mines") { mineForm(saved); return; }
    const a = LA(kind) || { params: {} };
    if (!a.legal && !saved) { setResult(plainReason(a.reason || kind + " is not available"), true); openFormKind = null; return; }
    const slot = $("formSlot");
    if (!slot) return;
    openFormKind = kind;
    slot.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "frm";
    const title = document.createElement("div");
    title.className = "y";
    title.textContent = kind.replaceAll("_", " ").toUpperCase();
    wrap.appendChild(title);
    const preview = formPreview(kind);
    if (preview) {
      const line = document.createElement("div");
      line.className = "c";
      line.textContent = preview;
      wrap.appendChild(line);
    }
    const fields = [];
    Object.entries(a.params || {}).forEach(([name, spec]) => {
      if (!spec || typeof spec !== "object" || !spec.type) return;
      const label = document.createElement("label");
      label.appendChild(document.createTextNode(name + " "));
      let input;
      if (Array.isArray(spec.choices) && kind === "buy_ship" && name === "ship_class") {
        input = document.createElement("select");
        yardOptions(input, spec);
      } else if (Array.isArray(spec.choices) && kind === "buy_equip" && name === "item") {
        input = document.createElement("select");
        gearOptions(input, spec);
      } else if (Array.isArray(spec.choices)) {
        input = document.createElement("select");
        spec.choices.forEach((choice) => {
          const o = document.createElement("option");
          o.value = typeof choice === "object" ? (choice.id ?? "") : choice;
          o.textContent = kind === "attack" && name === "target" ? shipChoiceLabel(String(o.value))
            : (kind === "buy_equip" && name === "item" ? gearName(o.value)
            : (kind === "ship_transport" && name === "ship_id" ? shipTransportLabel(o.value) : String(o.value) + codeBotSuffix(o.value)));
          if (kind === "deposit_planet_defense" && name === "kind" && o.value === "shields" && Number((landedPlanet() || {}).citadel_level || 0) < 5) {
            o.disabled = true;
            o.textContent = "shields (needs a Level 5 citadel)";
          }
          input.appendChild(o);
        });
        if (kind === "deposit_planet_defense" && name === "kind" && Number((landedPlanet() || {}).citadel_level || 0) < 5 && !Array.from(input.options).some((o) => o.value === "shields")) {
          const missing = document.createElement("option");
          missing.value = "shields";
          missing.disabled = true;
          missing.textContent = "shields (needs a Level 5 citadel)";
          input.appendChild(missing);
        }
      } else if (spec.type === "bool") {
        input = document.createElement("input");
        input.type = "checkbox";
        if (spec.default) input.checked = true;
      } else if (spec.type === "int" && /pct|percent/i.test(name)) {
        input = document.createElement("input");
        input.type = "range";
        input.min = spec.min != null ? spec.min : 0;
        input.max = spec.max != null ? spec.max : 100;
        input.value = spec.default != null ? spec.default : input.max;
        const read = document.createElement("b");
        read.className = "y";
        read.textContent = input.value + "%";
        input.addEventListener("input", () => { read.textContent = input.value + "%"; });
        label.appendChild(read);
      } else {
        input = document.createElement("input");
        input.type = spec.type === "int" ? "number" : "text";
        if (spec.min != null) input.min = spec.min;
        if (kind === "attack" && name === "qty") {
          const aboard = Number(((S || {}).ship || {}).fighters || 0);
          const cap = spec.max != null ? Math.min(Number(spec.max), aboard) : aboard;
          input.max = String(cap);
          input.dataset.cap = String(cap);
          if (!(saved && saved[name] != null && saved[name] !== "")) input.value = String(cap);
          input.min = "1";
          label.childNodes[0].textContent = "fighters (1 to " + fmt(cap) + ") ";
        }
      }
      input.dataset.n = name;
      input.dataset.t = spec.type;
      if (spec.required) input.dataset.req = "1";
      if (saved && saved[name] != null && saved[name] !== "") {
        if (spec.type === "bool") input.checked = !!saved[name];
        else input.value = saved[name];
        const read = label.querySelector("b");
        if (read && input.type === "range") read.textContent = input.value + "%";
      }
      label.appendChild(input);
      wrap.appendChild(label);
      fields.push(input);
    });
    if (kind === "assign_colonists") {
      const fromEl = fields.find((el) => el.dataset.n === "from");
      const toEl = fields.find((el) => el.dataset.n === "to");
      const qtyEl = fields.find((el) => el.dataset.n === "qty");
      const maxBy = (((a.params || {}).qty || {}).max_by) || {};
      const syncColonists = () => {
        if (fromEl && toEl) {
          Array.from(toEl.options).forEach((option) => { option.disabled = option.value === fromEl.value; });
          if (toEl.selectedOptions[0] && toEl.selectedOptions[0].disabled) {
            const open = Array.from(toEl.options).find((option) => !option.disabled);
            if (open) toEl.value = open.value;
          }
        }
        if (qtyEl && fromEl) {
          qtyEl.max = String(Number(maxBy[fromEl.value] || 1));
          if (qtyEl.value === "") qtyEl.value = qtyEl.max;
        }
      };
      if (fromEl) fromEl.addEventListener("change", () => { if (qtyEl) qtyEl.value = ""; syncColonists(); });
      syncColonists();
    }
    if (kind === "dump_planet_cargo") {
      const comEl = fields.find((el) => el.dataset.n === "commodity");
      const qtyEl = fields.find((el) => el.dataset.n === "qty");
      const maxBy = (((a.params || {}).qty || {}).max_by) || {};
      const fillDump = () => {
        if (!qtyEl || !comEl) return;
        const cap = Number(maxBy[comEl.value] || 0);
        if (cap > 0) qtyEl.max = String(cap);
        if (qtyEl.value === "" || Number(qtyEl.value) <= 0) qtyEl.value = cap > 0 ? String(cap) : "";
      };
      if (comEl) comEl.addEventListener("change", () => { if (qtyEl) qtyEl.value = ""; fillDump(); });
      fillDump();
    }
    const submit = () => {
      const args = {};
      fields.forEach((el) => {
        const t = el.dataset.t;
        if (t === "bool") { args[el.dataset.n] = el.checked; return; }
        if (el.value === "") return;
        args[el.dataset.n] = t === "int" ? Number(el.value) : el.value;
      });
      if (kind === "attack" && args.qty != null) {
        const box = fields.find((el) => el.dataset.n === "qty");
        const cap = Number((box && box.dataset.cap) || args.qty);
        args.qty = Math.max(1, Math.min(cap, Number(args.qty)));
      }
      if (kind === "deposit_planet_defense" && args.kind === "shields" && Number((landedPlanet() || {}).citadel_level || 0) < 5) {
        setResult("Planetary shields need a Level 5 citadel.", true);
        return;
      }
      if (kind === "assign_colonists" && args.from && args.from === args.to) {
        setResult("Move colonists to a different product.", true);
        return;
      }
      if (kind === "dump_planet_cargo" && !(Number(args.qty) > 0)) {
        setResult("Type an amount.", true);
        return;
      }
      if (kind === "launch_beacon" && !String(args.message || "").trim()) { setResult("Type a beacon message first.", true); return; }
      const blank = fields.find((el) => el.tagName === "INPUT" && el.dataset.t === "int" && el.dataset.req && el.value === "");
      if (blank) {
        setResult(/^(qty|amount|units|count|credits)$/.test(blank.dataset.n) ? "Type an amount." : "Type a number for " + blank.dataset.n.replaceAll("_", " ") + ".", true);
        return;
      }
      if (kind === "buy_ship") {
        const posted = Object.assign({}, args);
        openFormKind = null;
        formFocus = "";
        slot.innerHTML = "";
        yardConfirm(posted, a);
        return;
      }
      openFormKind = null;
      formFocus = "";
      slot.innerHTML = "";
      act(kind, args, kind.replaceAll("_", " "));
    };
    if (kind === "attack") {
      const note = (((a.params || {}).target || {}).note) || "";
      const feds = (((a.params || {}).target || {}).federals) || [];
      if (note || feds.length) {
        const warn = document.createElement("div");
        warn.className = "r";
        warn.dataset.fed = "warn";
        warn.textContent = note || "Attacking a Federal ship pods you. The ship is indestructible.";
        wrap.appendChild(warn);
      }
    }
    wrap.appendChild(button("CONFIRM", submit));
    wrap.appendChild(button("ESC", () => { openFormKind = null; formFocus = ""; slot.innerHTML = ""; }));
    wrap.addEventListener("keydown", (ev) => formKey(ev, submit));
    if (kind === "trade") {
      const listed = ((a.params.unit_price || {}).listed_by) || {};
      const sideEl = fields.find((el) => el.dataset.n === "side");
      const comEl = fields.find((el) => el.dataset.n === "commodity");
      const priceEl = fields.find((el) => el.dataset.n === "unit_price");
      const offered = comEl ? Array.from(comEl.options).map((o) => o.value) : [];
      const tradable = (name) => !offered.length || offered.includes(name);
      const pair = () => {
        const side = sideEl && sideEl.value;
        const com = comEl && comEl.value;
        const direct = (listed[com] || {})[side];
        if (direct) return [side, com, direct];
        for (const [name, sides] of Object.entries(listed)) {
          if (tradable(name) && sides && sides[side]) return [side, name, sides[side]];
        }
        for (const [name, sides] of Object.entries(listed)) {
          if (!tradable(name)) continue;
          const picked = Object.entries(sides || {}).find((row) => row[1]);
          if (picked) return [picked[0], name, picked[1]];
        }
        return null;
      };
      const hint = document.createElement("div");
      hint.className = "c";
      hint.dataset.list = "price";
      const paintHint = () => {
        const side = sideEl && sideEl.value;
        const com = comEl && comEl.value;
        const list = (listed[com] || {})[side];
        hint.textContent = list ? "list " + fmt(list) + " cr" : "";
      };
      const fill = () => {
        if (priceEl && priceEl.value === "") {
          const side = sideEl && sideEl.value;
          const com = comEl && comEl.value;
          const direct = (listed[com] || {})[side];
          if (direct) priceEl.value = direct;
          else {
            const found = pair();
            if (found) {
              if (sideEl) sideEl.value = found[0];
              if (comEl) comEl.value = found[1];
              priceEl.value = found[2];
            }
          }
        }
        paintHint();
      };
      if (sideEl) sideEl.addEventListener("change", () => { if (priceEl) priceEl.value = ""; fill(); });
      if (comEl) comEl.addEventListener("change", () => { if (priceEl) priceEl.value = ""; fill(); });
      fill();
      wrap.appendChild(hint);
      const qtyEl = fields.find((el) => el.dataset.n === "qty");
      if (CK) haggleLines(wrap, listed, sideEl, comEl, qtyEl, priceEl, saved);
      const capNote = document.createElement("div");
      capNote.className = "c";
      capNote.dataset.trade = "cap";
      const capQty = () => {
        if (!qtyEl) return;
        const side = sideEl && sideEl.value;
        const com = comEl && comEl.value;
        const ship = (S && S.ship) || {};
        const cargo = ship.cargo || {};
        const holds = Number(ship.holds || 0);
        const used = Object.values(cargo).reduce((sum, n) => sum + Number(n || 0), 0);
        const empty = Math.max(0, holds - used);
        const carried = Number(cargo[com] || 0);
        const price = Number((listed[com] || {})[side] || 0);
        const afford = price > 0 ? Math.floor(Number((S && S.credits) || 0) / price) : empty;
        const name = (COM[com] || [com || "cargo"])[0];
        let cap = side === "sell" ? carried : Math.min(empty, Number.isFinite(afford) ? afford : empty);
        if (cap < 0) cap = 0;
        const typed = Number(qtyEl.value);
        if (qtyEl.value !== "" && Number.isFinite(typed) && typed > cap) {
          qtyEl.value = String(cap);
          capNote.textContent = side === "sell"
            ? "You only have " + fmt(carried) + " " + name + " in your holds."
            : (empty <= afford ? "You only have " + fmt(empty) + " empty holds." : "You can afford " + fmt(afford) + ".");
        } else capNote.textContent = "";
      };
      if (qtyEl) qtyEl.addEventListener("input", capQty);
      if (sideEl) sideEl.addEventListener("change", capQty);
      if (comEl) comEl.addEventListener("change", capQty);
      wrap.appendChild(capNote);
    }
    if (kind === "buy_equip") {
      const prices = ((a.params.item || {}).unit_price_by) || {};
      const maxes = ((a.params.qty || {}).max_by) || {};
      const item = fields.find((el) => el.dataset.n === "item");
      const note = document.createElement("div");
      note.className = "c";
      note.dataset.gear = "price";
      const paint = () => {
        const key = item ? item.value : "";
        const price = prices[key];
        const mx = maxes[key];
        note.textContent = gearName(key) + ": " + fmt(price) + " cr each, up to " + fmt(mx);
      };
      if (item) item.addEventListener("change", paint);
      paint();
      wrap.appendChild(note);
      holdTotalLine(wrap, item, fields.find((el) => el.dataset.n === "qty"));
    }
    if (kind === "buy_ship") {
      const nets = ((a.params.ship_class || {}).net_cost_by) || {};
      const spare = ((a.params.trade_in || {}).spare_cost_by) || {};
      const credit = (a.params.ship_class || {}).trade_in;
      const item = fields.find((el) => el.dataset.n === "ship_class");
      const deal = fields.find((el) => el.dataset.n === "trade_in");
      const note = document.createElement("div");
      note.className = "c";
      note.dataset.yard = "deal";
      const stats = (a.params.ship_class || {}).stats_by || {};
      const paint = () => {
        const key = item ? item.value : "";
        // NOTE 60 item 5: the server's ship list. HULL is only the fallback when the server sends no figures.
        const s = stats[key];
        const hull = s ? { holds: s.holds, max_holds: s.max_holds, fighters: s.max_fighters, shields: s.max_shields,
          tpw: s.turns_per_warp, photons: s.photons, tw: s.transwarp, odds: s.offensive_odds } : (HULL[key] || {});
        const name = yardName(key, stats);
        const net = nets[key];
        const full = spare[key];
        const trading = !deal || deal.checked;
        const price = trading ? net : full;
        const gear = (hull.photons ? "photons" : "no photons") + ", " + (hull.tw ? "TransWarp" : "no TransWarp");
        const holds = hull.max_holds != null && hull.max_holds !== hull.holds
          ? fmt(hull.holds || 0) + " of " + fmt(hull.max_holds) : fmt(hull.holds || 0);
        const cost = price == null ? "" : Number(price) < 0 ? "you get " + fmt(-Number(price)) + " cr back. " : fmt(price) + " cr. ";
        note.textContent = name + ": " + cost
          + "Holds " + holds + ", fighters " + fmt(hull.fighters || 0) + ", shields " + fmt(hull.shields || 0)
          + ", " + (hull.tpw || "?") + " turns per warp" + (hull.odds != null ? ", odds " + hull.odds : "") + ", " + gear + ". "
          + (trading ? "Trade-in sells your ship" + (credit ? " for " + fmt(credit) + " cr" : "") + " and you fly the new one."
            : "You stay aboard. The new ship waits at StarDock.");
      };
      if (item) item.addEventListener("change", paint);
      if (deal) deal.addEventListener("change", paint);
      paint();
      wrap.appendChild(note);
      const rec = (a.params.ship_class || {}).trade_in_parts;
      if (rec) {
        const receipt = document.createElement("div");
        receipt.className = "c";
        receipt.dataset.yard = "receipt";
        const mine = (S && S.ship && S.ship.class) || "";
        const oldName = yardName(mine, stats);
        const bits = ["Hull " + fmt(rec.hull), "Holds " + fmt(rec.holds)];
        if (Number(rec.drive)) bits.push("Drive " + fmt(rec.drive));
        if (Number(rec.computer)) bits.push("Computer " + fmt(rec.computer));
        if (Number(rec.fighter_count)) bits.push("Fighters " + fmt(rec.fighters));
        if (Number(rec.shield_count)) bits.push("Shields " + fmt(rec.shields));
        if (Number(rec.scanner)) bits.push("Scanner " + fmt(rec.scanner));
        const lost = [];
        if (Number(rec.hold_count)) lost.push(fmt(rec.hold_count) + " holds");
        if (Number(rec.fighter_count)) lost.push(fmt(rec.fighter_count) + " fighters");
        receipt.textContent = "We'll give you " + fmt(rec.total) + " for your " + oldName + ": " + bits.join(", ") + "."
          + (lost.length ? " Your " + lost.join(" and ") + " go with the old ship." : "");
        wrap.appendChild(receipt);
      }
    }
    slot.appendChild(wrap);
    reveal(wrap);
    if (saved && formFocus) {
      const again = slot.querySelector('[data-n="' + formFocus + '"]');
      if (again) again.focus();
    } else {
      const first = fields.find((el) => el.tagName === "INPUT" && (el.type === "number" || el.type === "text"))
        || fields.find((el) => el.type !== "checkbox");
      if (first) {
        first.focus();
        if (first.type === "number" || first.type === "text") first.select();
      }
    }
  }
  function haggleLines(wrap, listed, sideEl, comEl, qtyEl, priceEl, saved) {
    // cockpit-gaps-v1 item 2. Original haggle (transcript.txt 2456-2470): "We'll sell them for 317 credits.",
    // offer 280, "We'll sell them for 309 credits.", ... "Very well, we'll take that offer." A failed haggle
    // ends the trade (REPORT2.md lines 20, 25-31). The original never prints its accept band, so none is shown.
    const quote = document.createElement("div");
    quote.className = "haggle";
    quote.dataset.haggle = "quote";
    const counter = document.createElement("div");
    counter.className = "haggle";
    counter.dataset.haggle = "counter";
    const ended = document.createElement("div");
    ended.className = "haggle";
    ended.dataset.haggle = "ended";
    const verb = (side) => (side === "sell" ? "We'll buy them for " : "We'll sell them for ");
    const pendingFor = (side, com) => {
      const h = CK && CK.haggle;
      return h && h.side === side && h.commodity === com ? h : null;
    };
    const paint = () => {
      const side = sideEl && sideEl.value;
      const com = comEl && comEl.value;
      const qty = Math.max(0, Number((qtyEl && qtyEl.value) || 0));
      const list = Number((listed[com] || {})[side] || 0);
      const h = pendingFor(side, com);
      quote.textContent = list && qty ? verb(side) + fmt(list * qty) + " credits (" + fmt(qty) + " at " + fmt(list) + " cr)." : "";
      counter.hidden = !h;
      counter.textContent = h && qty
        ? "Port counters: " + verb(side).toLowerCase() + fmt(h.counter * qty) + " credits (" + fmt(h.counter) + " each). Your offer?"
        : "";
    };
    const v = CK && CK.verdict;
    const last = v && v.kind === "trade" ? v.haggle : null;
    if (last) {
      const name = (COM[last.commodity] || [last.commodity])[0];
      if (last.outcome === "taken") ended.textContent = "Last haggle: the port took your offer, " + fmt(last.qty) + " " + name + " for " + fmt(last.paid_total) + " credits.";
      else if (last.outcome === "countered") ended.textContent = "Last haggle: countered at " + fmt(last.counter) + " cr each. Offer again or leave.";
      else if (last.outcome === "ended") ended.textContent = "Last haggle: refused, the trade ended (" + plainWords(String(v.reason || "")) + "). Dock again to trade.";
      else ended.textContent = "Last trade refused: " + plainWords(String(v.reason || "")) + ".";
      ended.dataset.outcome = last.outcome;
      if (last.outcome !== "taken") ended.classList.add("bad");
    } else ended.hidden = true;
    const h = pendingFor(sideEl && sideEl.value, comEl && comEl.value);
    if (h && priceEl && !(saved && saved.unit_price != null && saved.unit_price !== "")) priceEl.value = String(h.next_offer);
    const offer = () => {
      const pend = pendingFor(sideEl && sideEl.value, comEl && comEl.value);
      if (pend && priceEl) priceEl.value = String(pend.next_offer);
    };
    [sideEl, comEl, qtyEl].forEach((el) => el && el.addEventListener("input", paint));
    [sideEl, comEl].forEach((el) => el && el.addEventListener("change", () => { offer(); paint(); }));
    const accept = document.createElement("button");
    accept.type = "button";
    accept.textContent = "Accept";
    accept.dataset.haggle = "accept";
    accept.addEventListener("click", () => {
      offer();
      const confirm = Array.from(wrap.querySelectorAll("button")).find((b) => (b.textContent || "").trim() === "CONFIRM");
      if (confirm) confirm.click();
    });
    const syncAccept = () => { accept.hidden = counter.hidden; };
    [sideEl, comEl, qtyEl].forEach((el) => el && el.addEventListener("input", syncAccept));
    [sideEl, comEl].forEach((el) => el && el.addEventListener("change", syncAccept));
    paint();
    syncAccept();
    wrap.appendChild(quote);
    wrap.appendChild(counter);
    wrap.appendChild(accept);
    wrap.appendChild(ended);
  }
  function holdTotalLine(wrap, item, qtyEl) {
    // cockpit-gaps-v1 item 5. Original StarDock: "A  Cargo holds : 550 credits / next hold 14" (transcript.txt 4174)
    // and, once an amount is typed, "The cost for 10 more holds is 6,410 credits." (4186) before you confirm.
    const hq = CK && CK.hold_quote;
    if (!hq) return;
    const line = document.createElement("div");
    line.className = "haggle";
    line.dataset.gear = "hold-total";
    const paint = () => {
      if (!item || item.value !== "holds") { line.hidden = true; return; }
      line.hidden = false;
      const qty = Number((qtyEl && qtyEl.value) || 0);
      const head = "Cargo holds: " + fmt(hq.next_price) + " credits / next hold. You can buy " + fmt(hq.afford) + ". You have " + fmt(hq.holds) + " of " + fmt(hq.max_holds) + ".";
      const total = qty > 0 ? (hq.totals || {})[String(qty)] : null;
      if (qty > 0 && total == null) line.textContent = head + " You cannot afford " + fmt(qty) + " more holds.";
      else line.textContent = head + (total != null ? " The cost for " + fmt(qty) + " more hold" + (qty === 1 ? "" : "s") + " is " + fmt(total) + " credits." : "");
    };
    if (item) item.addEventListener("change", paint);
    if (qtyEl) qtyEl.addEventListener("input", paint);
    paint();
    wrap.appendChild(line);
  }
  function formKey(ev, submit) {
    // NOTE 71. Enter on a select picks the option and never submits. Enter
    // submits only from the last input or from the submit button.
    if (ev.key !== "Enter") return;
    const t = ev.target;
    if (!t) return;
    if (t.tagName === "SELECT" || t.tagName === "TEXTAREA") return;
    if (t.tagName === "BUTTON") {
      const label = (t.textContent || "").trim().toUpperCase();
      if (label === "ESC" || label === "NO" || label === "CANCEL") return;
      ev.preventDefault();
      ev.stopPropagation();
      submit();
      return;
    }
    if (t.tagName !== "INPUT") return;
    const type = (t.type || "").toLowerCase();
    if (type === "checkbox" || type === "radio" || type === "button" || type === "hidden") return;
    const wrap = t.closest(".frm");
    if (!wrap) return;
    const inputs = Array.from(wrap.querySelectorAll("input")).filter((el) => {
      const kind = (el.type || "").toLowerCase();
      return kind !== "checkbox" && kind !== "radio" && kind !== "hidden" && kind !== "button" && !el.disabled;
    });
    const last = inputs[inputs.length - 1];
    if (last && t !== last) {
      ev.preventDefault();
      const i = inputs.indexOf(t);
      if (i >= 0 && inputs[i + 1]) inputs[i + 1].focus();
      return;
    }
    ev.preventDefault();
    ev.stopPropagation();
    submit();
  }
  function reasonButton(kind, label, onLegal) {
    const a = LA(kind) || { legal: false, reason: kind + " is not available" };
    const b = document.createElement("button");
    b.type = "button";
    b.className = "verb";
    b.dataset.kind = kind;
    if (!a.legal) {
      b.classList.add("dim");
      b.title = plainReason(a.reason);
    }
    b.textContent = label;
    b.addEventListener("click", () => {
      if (!a.legal) { setResult(label + ": " + plainReason(a.reason), true); return; }
      onLegal(a);
    });
    return b;
  }
  function defenseBox() {
    const box = document.createElement("div");
    box.className = "encounter";
    box.dataset.screen = "defense";
    const group = (S.sector || {}).fighter_group;
    const line = document.createElement("div");
    line.className = "c";
    line.dataset.fighters = "here";
    if (group && group.owner_id !== S.self_id) {
      const toll = ((LA("pay_toll") || {}).params || {}).amount;
      line.textContent = "Hostile fighters: " + fmt(group.count) + " " + (group.mode || "") + ", belong to " + traderName(group.owner_id)
        + (toll != null ? ". Toll " + fmt(toll) + " cr." : ".");
    } else if (group) {
      line.textContent = "Your fighters here: " + fmt(group.count) + " " + (group.mode || "") + ".";
    } else {
      line.textContent = "No fighters deployed in this sector.";
    }
    box.appendChild(line);
    box.appendChild(reasonButton("pay_toll", "Pay toll", () => act("pay_toll", {}, "pay toll")));
    box.appendChild(reasonButton("retreat", "Retreat", () => act("retreat", {}, "retreat")));
    box.appendChild(reasonButton("surrender", "Surrender", () => act("surrender", {}, "surrender")));
    box.appendChild(reasonButton("attack", "Attack", () => openForm("attack")));
    box.appendChild(reasonButton("set_military_reaction", "Set reaction", () => reactionForm()));
    box.appendChild(reasonButton("cloak", "Cloak", () => act("cloak", {}, "cloak")));
    box.appendChild(reasonButton("fire_disruptor", "Disruptor", () => disruptorForm()));
    box.appendChild(reasonButton("query_limpets", "Query limpets", () => act("query_limpets", {}, "query limpets")));
    box.appendChild(reasonButton("remove_limpet", "Remove limpet", () => act("remove_limpet", {}, "remove limpet")));
    box.appendChild(reasonButton("tow_release", "Release tow", () => act("tow_release", {}, "release tow")));
    box.appendChild(reasonButton("ship_transwarp", "TransWarp", () => transwarpForm()));
    return box;
  }
  function reactionForm(saved) {
    const slot = $("formSlot");
    if (!slot) return;
    openFormKind = "reaction";
    const a = LA("set_military_reaction") || { params: {} };
    const planets = ((a.params || {}).planet_id || {}).choices || [];
    slot.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "frm";
    wrap.dataset.screen = "reaction";
    wrap.innerHTML = '<div class="y">REACTION</div><div class="c">How hard should the planet fight back, from 0 to 100?</div>';
    const pct = document.createElement("input");
    pct.type = "number";
    pct.min = "0";
    pct.max = "100";
    pct.dataset.n = "pct";
    pct.value = saved && saved.pct != null && saved.pct !== "" ? saved.pct : "0";
    const label = document.createElement("label");
    label.appendChild(document.createTextNode("percent "));
    label.appendChild(pct);
    wrap.appendChild(label);
    const submit = () => {
      const n = Number(pct.value);
      if (pct.value === "" || n < 0 || n > 100) { setResult("Type a percent from 0 to 100.", true); return; }
      openFormKind = null;
      slot.innerHTML = "";
      act("set_military_reaction", { planet_id: planets[0], pct: n }, "set reaction");
    };
    wrap.appendChild(button("CONFIRM", submit));
    wrap.appendChild(button("ESC", () => { openFormKind = null; slot.innerHTML = ""; }));
    wrap.addEventListener("keydown", (ev) => formKey(ev, submit));
    slot.appendChild(wrap);
    pct.focus();
    pct.select();
  }
  function disruptorForm(saved) {
    const slot = $("formSlot");
    if (!slot) return;
    openFormKind = "disruptor";
    const choices = ((((LA("fire_disruptor") || {}).params || {}).target || {}).choices) || [];
    slot.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "frm";
    wrap.dataset.screen = "disruptor";
    wrap.innerHTML = '<div class="y">DISRUPTOR</div><div class="c">Disruptors on board: ' + fmt(Number((S.ship || {}).mine_disruptors || 0)) + ". Pick an adjacent sector.</div>";
    const target = document.createElement("select");
    target.dataset.n = "target";
    choices.forEach((id) => {
      const o = document.createElement("option");
      o.value = String(id);
      o.textContent = String(id);
      target.appendChild(o);
    });
    if (saved && saved.target) target.value = String(saved.target);
    const label = document.createElement("label");
    label.appendChild(document.createTextNode("sector "));
    label.appendChild(target);
    wrap.appendChild(label);
    const submit = () => {
      openFormKind = null;
      slot.innerHTML = "";
      act("fire_disruptor", { target: Number(target.value) }, "fire disruptor");
    };
    wrap.appendChild(button("CONFIRM", submit));
    wrap.appendChild(button("ESC", () => { openFormKind = null; slot.innerHTML = ""; }));
    wrap.addEventListener("keydown", (ev) => formKey(ev, submit));
    slot.appendChild(wrap);
  }
  function transwarpForm(saved) {
    const slot = $("formSlot");
    if (!slot) return;
    openFormKind = "transwarp";
    const spec = (((LA("ship_transwarp") || {}).params || {}).sector_id) || {};
    const choices = spec.choices || [];
    const ore = spec.ore_by || {};
    slot.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "frm";
    wrap.dataset.screen = "transwarp";
    wrap.innerHTML = '<div class="y">TRANSWARP</div>';
    const cost = document.createElement("div");
    cost.className = "c";
    cost.dataset.ore = "cost";
    const target = document.createElement("select");
    target.dataset.n = "sector_id";
    choices.forEach((id) => {
      const o = document.createElement("option");
      o.value = String(id);
      o.textContent = String(id);
      target.appendChild(o);
    });
    if (saved && saved.sector_id) target.value = String(saved.sector_id);
    const paint = () => {
      const n = ore[target.value];
      cost.textContent = n != null ? "Fuel cost " + fmt(n) + " ore." : "Pick a locked sector.";
    };
    target.addEventListener("change", paint);
    paint();
    const label = document.createElement("label");
    label.appendChild(document.createTextNode("sector "));
    label.appendChild(target);
    wrap.appendChild(label);
    wrap.appendChild(cost);
    const submit = () => {
      openFormKind = null;
      slot.innerHTML = "";
      act("ship_transwarp", { sector_id: Number(target.value) }, "transwarp");
    };
    wrap.appendChild(button("CONFIRM", submit));
    wrap.appendChild(button("ESC", () => { openFormKind = null; slot.innerHTML = ""; }));
    wrap.addEventListener("keydown", (ev) => formKey(ev, submit));
    slot.appendChild(wrap);
  }
  function yoursHere() {
    const group = (S.sector || {}).fighter_group;
    if (!group || group.owner_id !== S.self_id) return { count: 0, mode: "" };
    return { count: Number(group.count || 0), mode: group.mode || "" };
  }
  function fighterForm(saved) {
    const slot = $("formSlot");
    if (!slot) return;
    openFormKind = "fighters";
    const here = yoursHere();
    const sh = S.ship || {};
    const aboard = Number(sh.fighters || 0);
    const cap = Number(sh.fighter_cap || 0);
    const modes = ((((LA("deploy_fighters") || {}).params || {}).mode || {}).choices) || ["defensive", "offensive", "toll"];
    slot.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "frm";
    wrap.dataset.screen = "fighters";
    wrap.innerHTML = '<div class="y">FIGHTERS</div><div class="c">In this sector: ' + fmt(here.count) + " yours. On board: " + fmt(aboard) + ". This ship holds up to " + fmt(cap) + ".</div>";
    const leave = document.createElement("input");
    leave.type = "number";
    leave.min = "0";
    leave.dataset.n = "leave";
    leave.value = saved && saved.leave != null && saved.leave !== "" ? saved.leave : String(here.count);
    const mode = document.createElement("select");
    mode.dataset.n = "mode";
    modes.forEach((name) => {
      const o = document.createElement("option");
      o.value = name;
      o.textContent = name;
      mode.appendChild(o);
    });
    if (saved && saved.mode) mode.value = saved.mode;
    else if (here.mode) mode.value = here.mode;
    const leaveLabel = document.createElement("label");
    leaveLabel.appendChild(document.createTextNode("leave in sector "));
    leaveLabel.appendChild(leave);
    const modeLabel = document.createElement("label");
    modeLabel.appendChild(document.createTextNode("mode "));
    modeLabel.appendChild(mode);
    wrap.appendChild(leaveLabel);
    wrap.appendChild(modeLabel);
    const submit = () => {
      const want = Number(leave.value);
      if (leave.value === "" || !Number.isFinite(want) || want < 0) { setResult("Type an amount.", true); return; }
      const have = yoursHere().count;
      const onShip = Number((S.ship || {}).fighters || 0);
      const room = Math.max(0, cap - onShip);
      if (want === have) {
        if (mode.value && mode.value !== yoursHere().mode && onShip > 0 && legal("deploy_fighters")) {
          openFormKind = null;
          slot.innerHTML = "";
          act("deploy_fighters", { qty: 1, mode: mode.value }, "set fighter mode");
          return;
        }
        setResult("That many are already in this sector.", true);
        return;
      }
      openFormKind = null;
      slot.innerHTML = "";
      if (want > have) {
        const diff = want - have;
        if (diff > onShip) { setResult("You only have " + fmt(onShip) + " fighters on board.", true); return; }
        if (!legal("deploy_fighters")) { setResult(plainReason((LA("deploy_fighters") || {}).reason), true); return; }
        act("deploy_fighters", { qty: diff, mode: mode.value }, "leave fighters");
        return;
      }
      let diff = have - want;
      if (diff > room) {
        if (room <= 0) { setResult("This ship holds " + fmt(cap) + " fighters.", true); return; }
        diff = room;
      }
      if (!legal("recall_deployed")) { setResult(plainReason((LA("recall_deployed") || {}).reason), true); return; }
      act("recall_deployed", { what: "fighters", qty: diff }, "take fighters");
    };
    wrap.appendChild(button("CONFIRM", submit));
    wrap.appendChild(button("ESC", () => { openFormKind = null; slot.innerHTML = ""; }));
    wrap.addEventListener("keydown", (ev) => formKey(ev, submit));
    slot.appendChild(wrap);
    const again = (saved && formFocus && wrap.querySelector('[data-n="' + formFocus + '"]')) || leave;
    again.focus();
    if (again.type === "number" || again.type === "text") again.select();
  }
  function mineCounts() {
    const aboard = (S.ship || {}).mines || {};
    const on = { armid: Number(aboard.armid || 0), limpet: Number(aboard.limpet || 0) };
    const here = { armid: 0, limpet: 0 };
    ((S.sector || {}).mines || []).forEach((row) => {
      const owner = row.owner || row.owner_id;
      if (owner !== S.self_id || here[row.kind] == null) return;
      here[row.kind] += Number(row.count || 0);
    });
    return { on, here };
  }
  function mineForm(saved) {
    const slot = $("formSlot");
    if (!slot) return;
    openFormKind = "mines";
    const counts = mineCounts();
    const a = LA("deploy_mines") || { params: {}, legal: false, reason: "" };
    slot.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "frm";
    wrap.dataset.screen = "mines";
    wrap.innerHTML = '<div class="y">MINES</div><div class="c" data-mines="form">On board: armid ' + fmt(counts.on.armid) + ", limpet " + fmt(counts.on.limpet)
      + ". In this sector: armid " + fmt(counts.here.armid) + ", limpet " + fmt(counts.here.limpet) + ".</div>";
    let qty = null;
    if (a.legal) {
      const kinds = ((a.params.kind || {}).choices) || [];
      const kind = document.createElement("select");
      kind.dataset.n = "kind";
      kinds.forEach((name) => {
        const o = document.createElement("option");
        o.value = name;
        o.textContent = name;
        kind.appendChild(o);
      });
      if (saved && saved.kind) kind.value = saved.kind;
      qty = document.createElement("input");
      qty.type = "number";
      qty.min = "1";
      qty.dataset.n = "qty";
      if (saved && saved.qty != null && saved.qty !== "") qty.value = saved.qty;
      const kindLabel = document.createElement("label");
      kindLabel.appendChild(document.createTextNode("kind "));
      kindLabel.appendChild(kind);
      const qtyLabel = document.createElement("label");
      qtyLabel.appendChild(document.createTextNode("qty "));
      qtyLabel.appendChild(qty);
      wrap.appendChild(kindLabel);
      wrap.appendChild(qtyLabel);
      const submit = () => {
        const n = Number(qty.value);
        if (!n) { setResult("Type an amount.", true); return; }
        openFormKind = null;
        slot.innerHTML = "";
        act("deploy_mines", { kind: kind.value, qty: n }, "deploy mines");
      };
      wrap.appendChild(button("CONFIRM", submit));
      wrap.addEventListener("keydown", (ev) => formKey(ev, submit));
    } else {
      const why = document.createElement("div");
      why.textContent = plainReason(a.reason);
      wrap.appendChild(why);
    }
    const recall = LA("recall_deployed") || { params: {} };
    const pickupKinds = (((recall.params || {}).kind || {}).choices) || [];
    if (pickupKinds.length) {
      const pickKind = document.createElement("select");
      pickKind.dataset.n = "pickup_kind";
      pickupKinds.forEach((name) => {
        const o = document.createElement("option");
        o.value = name;
        o.textContent = name;
        pickKind.appendChild(o);
      });
      const pickQty = document.createElement("input");
      pickQty.type = "number";
      pickQty.min = "1";
      pickQty.dataset.n = "pickup";
      const maxes = ((recall.params || {}).qty || {}).max_by || {};
      const fillPick = () => { pickQty.max = String(maxes[pickKind.value] || counts.here[pickKind.value] || 1); pickQty.value = pickQty.max; };
      pickKind.addEventListener("change", fillPick);
      fillPick();
      const pickLabel = document.createElement("label");
      pickLabel.appendChild(document.createTextNode("pick up "));
      pickLabel.appendChild(pickKind);
      pickLabel.appendChild(pickQty);
      wrap.appendChild(pickLabel);
      wrap.appendChild(button("PICK UP", () => {
        const n = Number(pickQty.value);
        if (!n) { setResult("Type an amount.", true); return; }
        if (!recall.legal) { setResult(plainReason(recall.reason), true); return; }
        openFormKind = null;
        slot.innerHTML = "";
        act("recall_deployed", { what: "mines", kind: pickKind.value, qty: n }, "pick up mines");
      }));
    }
    wrap.appendChild(button("ESC", () => { openFormKind = null; slot.innerHTML = ""; }));
    slot.appendChild(wrap);
    if (qty) { qty.focus(); qty.select(); }
  }
  function terraForm(saved) {
    const slot = $("formSlot");
    if (!slot) return;
    openFormKind = "terra";
    const a = LA("terra_colonists") || { params: {}, legal: false, reason: "Terra colonists unavailable here" };
    const pool = Number(a.params.pool || 0);
    const cap = Number(a.params.max || 0);
    const maxBy = ((a.params.qty || {}).max_by) || {};
    slot.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "frm";
    wrap.dataset.screen = "terra";
    wrap.innerHTML = '<div class="y">TERRA</div><div class="c" data-terra="pool">Terra holds ' + fmt(pool) + " of " + fmt(cap) + " colonists. Free holds " + fmt(Number(((S.ship || {}).holds || 0) - Object.values((S.ship || {}).cargo || {}).reduce((sum, n) => sum + Number(n || 0), 0))) + ".</div>";
    if (!a.legal) {
      const why = document.createElement("div");
      why.textContent = plainReason(a.reason);
      wrap.appendChild(why);
    } else {
      const mode = document.createElement("select");
      mode.dataset.n = "mode";
      ((a.params.mode || {}).choices || []).forEach((name) => {
        const o = document.createElement("option");
        o.value = name;
        o.textContent = name;
        mode.appendChild(o);
      });
      if (saved && saved.mode) mode.value = saved.mode;
      const qty = document.createElement("input");
      qty.type = "number";
      qty.min = "1";
      qty.dataset.n = "qty";
      const fill = () => { qty.max = String(maxBy[mode.value] || 1); if (!(saved && saved.qty)) qty.value = qty.max; };
      mode.addEventListener("change", fill);
      fill();
      if (saved && saved.qty) qty.value = saved.qty;
      const modeLabel = document.createElement("label");
      modeLabel.appendChild(document.createTextNode("take or leave "));
      modeLabel.appendChild(mode);
      const qtyLabel = document.createElement("label");
      qtyLabel.appendChild(document.createTextNode("holds "));
      qtyLabel.appendChild(qty);
      wrap.appendChild(modeLabel);
      wrap.appendChild(qtyLabel);
      const submit = () => {
        const n = Number(qty.value);
        if (!n) { setResult("Type an amount.", true); return; }
        openFormKind = null;
        slot.innerHTML = "";
        act("terra_colonists", { mode: mode.value, qty: n }, mode.value + " colonists");
      };
      wrap.appendChild(button("CONFIRM", submit));
      wrap.addEventListener("keydown", (ev) => formKey(ev, submit));
      qty.focus();
      qty.select();
    }
    wrap.appendChild(button("ESC", () => { openFormKind = null; slot.innerHTML = ""; }));
    slot.appendChild(wrap);
    reveal(wrap);
  }
  function bankForm(saved) {
    const dep = LA("bank_deposit") || { params: {}, legal: false, reason: "" };
    const wd = LA("bank_withdraw") || { params: {}, legal: false, reason: "" };
    const slot = $("formSlot");
    if (!slot) return;
    openFormKind = "bank";
    const balance = Number((dep.params || {}).balance || (wd.params || {}).balance || (S && S.bank_balance) || 0);
    const room = Number((dep.params || {}).room || 0);
    const capacity = Number((dep.params || {}).capacity || (wd.params || {}).capacity || 0);
    const depMax = Number((dep.params || {}).max_amount || 0);
    const wdMax = Number((wd.params || {}).max_amount || 0);
    slot.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "frm";
    wrap.dataset.screen = "bank";
    wrap.innerHTML = '<div class="y">BANK</div><div class="c">Balance ' + fmt(balance) + " cr. Room " + fmt(room) + (capacity ? " of " + fmt(capacity) : "") + " cr.</div>";
    const side = document.createElement("select");
    side.dataset.n = "side";
    [["deposit", "Deposit", dep.legal], ["withdraw", "Withdraw", wd.legal]].forEach(([value, label, ok]) => {
      const o = document.createElement("option");
      o.value = value;
      o.textContent = label;
      o.disabled = !ok;
      side.appendChild(o);
    });
    if (saved && (saved.side === "deposit" || saved.side === "withdraw")) side.value = saved.side;
    else if (dep.legal) side.value = "deposit";
    else if (wd.legal) side.value = "withdraw";
    const amount = document.createElement("input");
    amount.type = "number";
    amount.min = "1";
    amount.dataset.n = "amount";
    const fill = () => { amount.value = side.value === "withdraw" ? "" : (depMax ? String(depMax) : ""); };
    side.addEventListener("change", fill);
    if (saved && saved.amount != null && saved.amount !== "") amount.value = saved.amount;
    else fill();
    const sideLabel = document.createElement("label");
    sideLabel.appendChild(document.createTextNode("side "));
    sideLabel.appendChild(side);
    const amtLabel = document.createElement("label");
    amtLabel.appendChild(document.createTextNode("amount "));
    amtLabel.appendChild(amount);
    wrap.appendChild(sideLabel);
    wrap.appendChild(amtLabel);
    const submit = async () => {
      const n = Number(amount.value);
      if (!n) { setResult("Type an amount.", true); return; }
      const which = side.value === "withdraw" ? wd : dep;
      if (!which.legal) { setResult(plainReason(which.reason), true); return; }
      const post = () => {
        openFormKind = null;
        slot.innerHTML = "";
        act(side.value === "withdraw" ? "bank_withdraw" : "bank_deposit", { amount: n }, side.value);
      };
      if (side.value === "withdraw") {
        await loadTaxTerms();
        if (taxTerms && Number((S && S.credits) || 0) + n > taxTerms.over) {
          confirmWords("Withdraw", "Withdraw " + fmt(n) + " cr? The dawn tax takes " + taxTerms.rate + "% of the cash on your ship when it is over " + fmt(taxTerms.over) + ".", post);
          return;
        }
      }
      post();
    };
    wrap.appendChild(button("CONFIRM", submit));
    wrap.appendChild(button("ESC", () => { openFormKind = null; slot.innerHTML = ""; }));
    wrap.addEventListener("keydown", (ev) => formKey(ev, submit));
    slot.appendChild(wrap);
    reveal(wrap);
    const focusName = (saved && formFocus) || "amount";
    const again = wrap.querySelector('[data-n="' + focusName + '"]') || amount;
    again.focus();
    if (again.type === "number" || again.type === "text") again.select();
  }
  function treasuryForm(side, saved) {
    const slot = $("formSlot");
    const planet = landedPlanet();
    if (!slot || !planet) return;
    openFormKind = "treasury";
    const which = (saved && saved.side) || side || "deposit";
    const action = LA(which === "withdraw" ? "withdraw_treasury" : "deposit_treasury") || { params: {} };
    const max = Number(((action.params || {}).amount || {}).max || 1);
    slot.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "frm";
    wrap.dataset.screen = "treasury";
    const deposit = LA("deposit_treasury") || { params: {} };
    const room = (deposit.params || {}).room;
    const capacity = (deposit.params || {}).capacity;
    let treasuryLine = "Treasury " + fmt(planet.treasury || 0) + " cr.";
    if (room != null && capacity) treasuryLine += " Room " + fmt(room) + " of " + fmt(capacity) + " cr.";
    wrap.innerHTML = '<div class="y">TREASURY</div><div class="c" data-treasury="form">' + treasuryLine + "</div>";
    const pick = document.createElement("select");
    pick.dataset.n = "side";
    [["deposit", "Deposit"], ["withdraw", "Withdraw"]].forEach(([value, label]) => {
      const o = document.createElement("option");
      o.value = value;
      o.textContent = label;
      pick.appendChild(o);
    });
    pick.value = which === "withdraw" ? "withdraw" : "deposit";
    const amount = document.createElement("input");
    amount.type = "number";
    amount.min = "1";
    amount.max = String(max);
    amount.dataset.n = "amount";
    amount.value = (saved && saved.amount) || String(max);
    wrap.appendChild(pick);
    wrap.appendChild(amount);
    const submit = () => {
      const kind = pick.value === "withdraw" ? "withdraw_treasury" : "deposit_treasury";
      const n = Number(amount.value);
      if (!n) { setResult("Type an amount.", true); return; }
      openFormKind = null;
      slot.innerHTML = "";
      act(kind, { planet_id: planet.id, amount: n }, pick.value);
    };
    wrap.appendChild(button("CONFIRM", submit));
    wrap.appendChild(button("ESC", () => { openFormKind = null; slot.innerHTML = ""; }));
    wrap.addEventListener("keydown", (ev) => formKey(ev, submit));
    slot.appendChild(wrap);
    amount.focus();
    amount.select();
  }
  function quasarForm(kind, saved) {
    const slot = $("formSlot");
    const planet = landedPlanet();
    if (!slot || !planet) return;
    openFormKind = "quasar";
    const which = (saved && saved.kind) || kind || "set_quasar_sector";
    const now = which === "set_quasar_atm" ? (planet.quasar_atm_pct || 0) : (planet.quasar_sector_pct || 0);
    slot.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "frm";
    wrap.dataset.screen = "quasar";
    wrap.innerHTML = '<div class="y">QUASAR</div><div class="c">Now ' + now + "%.</div>";
    const pick = document.createElement("select");
    pick.dataset.n = "kind";
    [["set_quasar_sector", "Sector"], ["set_quasar_atm", "Atmosphere"]].forEach(([value, label]) => {
      const o = document.createElement("option");
      o.value = value;
      o.textContent = label;
      pick.appendChild(o);
    });
    pick.value = which;
    const pct = document.createElement("input");
    pct.type = "number";
    pct.min = "0";
    pct.max = "100";
    pct.dataset.n = "pct";
    pct.value = (saved && saved.pct != null && saved.pct !== "") ? saved.pct : String(now);
    wrap.appendChild(pick);
    wrap.appendChild(pct);
    const submit = () => {
      const n = Number(pct.value);
      if (pct.value === "" || n < 0 || n > 100) { setResult("Type a percent from 0 to 100.", true); return; }
      openFormKind = null;
      slot.innerHTML = "";
      act(pick.value, { planet_id: planet.id, pct: n }, "set quasar");
    };
    wrap.appendChild(button("CONFIRM", submit));
    wrap.appendChild(button("ESC", () => { openFormKind = null; slot.innerHTML = ""; }));
    wrap.addEventListener("keydown", (ev) => formKey(ev, submit));
    slot.appendChild(wrap);
    pct.focus();
    pct.select();
  }
  function jumpForm(kind, saved) {
    const slot = $("formSlot");
    const planet = landedPlanet();
    if (!slot || !planet) return;
    openFormKind = "jump";
    const which = (saved && saved.kind) || kind || "planet_transwarp";
    const fuel = Number((planet.stockpile || {}).fuel_ore || 0);
    const note = which === "planet_transport"
      ? "10 fuel ore per sector. Range " + fmt(Math.floor(fuel / 10)) + " sectors. 50,000 cr plus 25,000 cr for each hop after the first."
      : "Fuel cost 400 ore per sector.";
    slot.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "frm";
    wrap.dataset.screen = "jump";
    wrap.innerHTML = '<div class="y">' + (which === "planet_transport" ? "TRANSPORTER" : "PLANET TRANSWARP") + '</div><div class="c" data-fuel="jump">' + note + "</div>";
    const pick = document.createElement("select");
    pick.dataset.n = "kind";
    [["planet_transwarp", "Planet TransWarp"], ["planet_transport", "Use transporter"]].forEach(([value, label]) => {
      const o = document.createElement("option");
      o.value = value;
      o.textContent = label;
      pick.appendChild(o);
    });
    pick.value = which;
    const dest = document.createElement("input");
    dest.type = "number";
    dest.min = "1";
    dest.dataset.n = "dest";
    dest.value = (saved && saved.dest) || "";
    wrap.appendChild(pick);
    wrap.appendChild(dest);
    const submit = () => {
      const n = Number(dest.value);
      if (!n) { setResult("Type a destination sector.", true); return; }
      const posted = pick.value;
      openFormKind = null;
      slot.innerHTML = "";
      act(posted, { planet_id: planet.id, dest_sector: n }, posted);
    };
    wrap.appendChild(button("CONFIRM", submit));
    wrap.appendChild(button("ESC", () => { openFormKind = null; slot.innerHTML = ""; }));
    wrap.addEventListener("keydown", (ev) => formKey(ev, submit));
    slot.appendChild(wrap);
    dest.focus();
  }
  function formPreview(kind) {
    const planet = landedPlanet();
    if (!planet || planet.citadel_level == null && planet.quasar_sector_pct == null) return "";
    if (/quasar/i.test(kind)) return "Now: sector " + (planet.quasar_sector_pct || 0) + "%, atmosphere " + (planet.quasar_atm_pct || 0) + "%. Citadel level " + (planet.citadel_level || 0) + ".";
    if (/citadel|build/i.test(kind)) return "Citadel level " + (planet.citadel_level || 0) + (planet.citadel_target ? ", building toward " + planet.citadel_target : "") + ".";
    return "";
  }
  function usedHolds(sh) {
    const cap = Number((sh && sh.holds) || 0);
    if (sh && sh.cargo_free != null) return Math.max(0, cap - Number(sh.cargo_free));
    return Object.values((sh && sh.cargo) || {}).reduce((sum, n) => sum + Number(n || 0), 0);
  }
  function shipInfo() {
    const sh = S.ship || {};
    const def = SHIPS[sh.class] || { name: String(sh.class || "ship").replaceAll("_", " ") };
    const hop = (LA("warp") || {}).turn_cost || (((LA("plot_course") || {}).params || {}).execute || {}).first_hop_turns || "";
    const mines = sh.mines || {};
    const gear = [
      ["Scanner", sh.scanner ? gearName(sh.scanner) : "none"],
      ["Genesis", fmt(sh.genesis || 0)],
      ["Ether probes", fmt(sh.ether_probes || 0)],
      ["Photons", fmt(sh.photon_missiles || 0)],
      ["Cloaks", fmt(sh.cloaks || 0)],
      ["Disruptors", fmt(sh.mine_disruptors || 0)],
      ["Beacons", fmt(sh.marker_beacons || 0)],
      ["Corbomite", fmt(sh.corbomite || 0)],
      ["Psychic probe", fmt(sh.psychic_probe || 0)],
      ["Atomic detonators", fmt(sh.atomic_detonators || 0)],
      ["Atomic mines", fmt(mines.atomic || 0)],
      ["Armid mines", fmt(mines.armid || 0)],
      ["Limpet mines", fmt(mines.limpet || 0)],
    ];
    if (sh.transwarp && sh.transwarp.fitted) gear.push(["Transwarp", String(sh.transwarp.fitted)]);
    const row = (k, v) => '<div class="row"><span class="g">' + k + '</span> <span class="c">' + esc(v) + "</span></div>";
    const m = $("menu");
    m.hidden = false;
    m.dataset.screen = "ship-info";
    m.innerHTML = '<div class="y">Ship information</div>'
      + row("Name", def.name)
      + row("Commander", S.self_name || "")
      + row("Class", String(sh.class || "").replaceAll("_", " "))
      + row("Holds", fmt(usedHolds(sh)) + " of " + fmt(sh.holds))
      + row("Empty holds", fmt(Math.max(0, Number(sh.holds || 0) - usedHolds(sh))))
      + row("Fighters", fmt(sh.fighters) + " of " + fmt(sh.fighter_cap || 0))
      + row("Shields", fmt(sh.shields) + " of " + fmt(sh.shield_cap || 0))
      + row("Turns per warp", hop === "" ? "" : String(hop))
      + '<div class="y">Gear</div>'
      + gear.map(([label, n]) => row(label, n)).join("")
      + '<br><span class="dk">Esc to close</span>';
  }
  async function rulesPanel() {
    const m = $("menu");
    m.hidden = false;
    m.dataset.screen = "rules";
    const manual = $("manualLink");
    const manualHref = manual ? manual.getAttribute("href") : "/manual";
    const manualLink = '<div class="row"><a id="rulesManual" href="' + manualHref + '" target="_blank" rel="noopener">Player manual</a></div>';
    m.innerHTML = '<div class="y">Rules and Help</div>' + manualLink + '<div class="c">Loading.</div>';
    try {
      const data = await api("/" + state.seat + "/reference");
      const blocks = (data.sections || []).map((section) => {
        let body = '<div class="y">' + esc(section.title || "") + "</div>";
        if (section.body) body += '<div class="row">' + esc(section.body) + "</div>";
        (section.rows || []).forEach((row) => {
          if (row.cost != null) {
            let line = esc(row.name) + " " + fmt(row.cost) + " cr, holds " + fmt(row.holds);
            if (row.max_holds != null) line += ", max holds " + fmt(row.max_holds);
            line += ", fighters " + fmt(row.max_fighters) + ", shields " + fmt(row.max_shields) + ", " + fmt(row.turns_per_warp) + " turns per warp";
            if (row.offensive_odds != null) line += ", offensive odds " + row.offensive_odds;
            if (row.fighters_per_attack != null) line += ", " + fmt(row.fighters_per_attack) + " fighters per attack";
            if (row.max_mines != null) line += ", mines " + fmt(row.max_mines);
            if (row.max_photons != null) line += ", photons " + fmt(row.max_photons);
            if (row.max_genesis != null) line += ", genesis " + fmt(row.max_genesis);
            body += '<div class="row" data-ship="' + esc(row.id) + '">' + line + "</div>";
          } else if (row.price != null) {
            body += '<div class="row" data-price="' + esc(row.name) + '">' + esc(row.name) + " " + fmt(row.price) + " cr</div>";
          } else if (row.good) {
            const evil = row.evil && row.evil !== row.good ? ", or " + row.evil + " below zero alignment" : "";
            body += '<div class="row" data-rank="' + esc(String(row.experience)) + '">' + fmt(row.experience) + " experience: " + esc(row.good) + esc(evil) + "</div>";
          }
        });
        return body;
      }).join("");
      m.innerHTML = '<div class="y">Rules and Help</div>' + manualLink + blocks + '<br><span class="dk">Esc to close</span>';
    } catch (e) {
      m.innerHTML = '<div class="y">Rules and Help</div>' + manualLink + '<div class="r">' + esc(e.message || e) + "</div>";
    }
  }

  function citadelForm() {
    const a = LA("build_citadel") || { legal: false, reason: "", params: {} };
    const next = (a.params || {}).next || {};
    const planet = landedPlanet() || {};
    const stock = planet.stockpile || {};
    const cols = Object.values(planet.colonists || {}).reduce((n, v) => n + Number(v || 0), 0);
    const level = next.level || (Number(planet.citadel_level || 0) + 1);
    const target = Number(planet.citadel_target || 0);
    const now = Number(planet.citadel_level || 0);
    const building = target > now || /under construction/i.test(a.reason || "");
    const days = Number(next.days || 0);
    const ready = days ? " Ready day " + (Number(S.day || 0) + days) + "." : "";
    const have = (key, stockKey) => next[key] != null ? next[key] : stock[stockKey] || 0;
    const gaps = [];
    [["fuel ore", next.fuel_ore, have("fuel_have", "fuel_ore")], ["organics", next.organics, have("organics_have", "organics")], ["equipment", next.equipment, have("equipment_have", "equipment")], ["colonists", next.colonists, have("colonists_have", "colonists")]].forEach(([name, need, got]) => {
      const gap = Number(need || 0) - Number(name === "colonists" && next.colonists_have == null ? cols : got || 0);
      if (gap > 0) gaps.push(name + " " + fmt(gap));
    });
    const dayWord = days === 1 ? "1 day" : fmt(days) + " days";
    let note;
    if (building) {
      const readyDay = planet.citadel_complete_day || ((String(a.reason || "").match(/done day (\d+)/) || [])[1] || "");
      note = "Citadel L" + (target || level) + " is being built" + (readyDay ? ", ready day " + readyDay : "") + ".";
    } else {
      note = "Citadel level " + level + ". Fuel ore " + fmt(next.fuel_ore || next.credits || 0) + " (have " + fmt(have("fuel_have", "fuel_ore")) + "). Organics " + fmt(next.organics || 0) + " (have " + fmt(have("organics_have", "organics")) + "). Equipment " + fmt(next.equipment || 0) + " (have " + fmt(have("equipment_have", "equipment")) + "). Colonists " + fmt(next.colonists || 0) + " (have " + fmt(next.colonists_have != null ? next.colonists_have : cols) + "). " + dayWord + "." + ready + (gaps.length ? " Short: " + gaps.join(", ") + "." : "");
    }
    if (!a.legal) {
      confirmWords("Build citadel", note);
      const btn = $("dangerOk");
      if (btn) { btn.textContent = "CONFIRM"; btn.classList.add("dim"); }
      return;
    }
    confirmWords("Build citadel", note, () => act("build_citadel", { planet_id: planet.id }, "build citadel"));
  }
  async function planetKey(k) {
    if (!landedPlanet()) await refresh();
    if (k === "B") return citadelForm();
    return planetAct(k);
  }
  function planetAct(k) {
    if (k === "Q") return act("liftoff", {}, "lift off");
    if (k === "B") return citadelForm();
    const row = PLANET_KEYS.find((x) => x[0] === k);
    if (!row) return;
    if (!legal(row[2])) { setResult(row[1] + ": " + plainReason((LA(row[2]) || {}).reason), true); return; }
    const pid = landedPlanet();
    openForm(row[2]);
    if (pid && $("formSlot")) {
      const field = $("formSlot").querySelector('[data-n="planet_id"]');
      if (field && !field.value) field.value = String(pid.id);
    }
  }
  function keys() {
    const bar = $("keys");
    bar.innerHTML = "";
    const onPlanet = onSurface();
    if (onPlanet) {
      const q = document.createElement("button");
      q.type = "button";
      q.dataset.key = "Q";
      q.className = legal("liftoff") ? "on" : "off";
      q.disabled = state.busy;
      q.innerHTML = "<kbd>Q</kbd>Lift off";
      q.addEventListener("click", () => planetAct("Q"));
      bar.appendChild(q);
      PLANET_KEYS.forEach(([k, label, kind]) => {
        const b = document.createElement("button");
        b.type = "button";
        b.dataset.key = k;
        b.className = legal(kind) ? "on" : "off";
        b.disabled = state.busy;
        b.innerHTML = "<kbd>" + k + "</kbd>" + label;
        b.addEventListener("click", () => planetAct(k));
        bar.appendChild(b);
      });
    }
    KEYS.filter((row) => row[3]).forEach(([k, label, kind]) => {
      if (onPlanet && (k === "F" || PLANET_KEYS.some((row) => row[0] === k))) return;
      const b = document.createElement("button");
      b.type = "button";
      b.dataset.key = k;
      const off = outOfTurns() || (kind && !legal(kind)) || (onPlanet && SPACE_OFF.includes(k));
      b.className = off ? "off" : "on";
      b.disabled = state.busy;
      if (kind === "wait") b.setAttribute("data-testid", "action-wait");
      b.innerHTML = "<kbd>" + k + "</kbd>" + label;
      b.addEventListener("click", () => key(k));
      bar.appendChild(b);
    });
    const help = document.createElement("button");
    help.type = "button";
    help.dataset.key = "?";
    help.innerHTML = "<kbd>?</kbd>All";
    help.addEventListener("click", () => key("?"));
    bar.appendChild(help);
  }
  function askSector(done) {
    const m = $("menu");
    m.hidden = false;
    m.dataset.screen = "ask-sector";
    inComputer = false;
    m.innerHTML = '<div class="y">What is the destination sector?</div><input id="sectorAsk" /> <button type="button" id="sectorGo">ENTER</button><br><span class="dk">Esc to close</span>';
    const input = $("sectorAsk");
    const go = () => {
      const n = Number(input.value);
      m.hidden = true;
      if (n) done(n);
    };
    $("sectorGo").addEventListener("click", go);
    input.addEventListener("keydown", (ev) => {
      ev.stopPropagation();
      if (ev.key === "Escape") { ev.preventDefault(); m.hidden = true; return; }
      if (ev.key === "Enter") { ev.preventDefault(); go(); }
    });
    input.focus();
  }
  function newestSummary() {
    let best = null;
    streamLog.concat((S && S.recent_events) || []).forEach((ev) => {
      if (!ev || !ev.summary) return;
      if (!best || (ev.seq || 0) >= (best.seq || 0)) best = ev;
    });
    return best ? String(best.summary) : "";
  }
  function readMail() {
    const rows = (S.inbox || []).filter((row) => row && (row.message || row.text));
    if (!rows.length) { setResult("No mail.", true); return; }
    const body = rows.map((row) => '<div class="row" data-mail="letter"><span class="y">' + esc(row.from_name || row.from || "someone") + "</span> " + esc(row.message || row.text) + "</div>").join("");
    overlay("Mail", body);
  }
  function overlay(title, body) {
    const m = $("menu");
    m.hidden = false;
    inComputer = false;
    m.dataset.screen = title;
    m.innerHTML = '<div class="y">' + title + "</div>" + body + '<br><span class="dk">Esc to close</span>';
  }
  function portReport() {
    const rows = (S.known_ports || []).slice();
    const here = (S.sector || {}).port;
    const id = Number((S.sector || {}).id);
    if (here && !rows.some((row) => Number(row.sector_id) === id)) {
      rows.unshift({ sector_id: id, class: here.code, name: here.name, stock: here.stock, last_seen_day: S.day });
    }
    if (!rows.length) { setResult("No ports in your computer yet.", true); return; }
    if (CK) { overlay("Port Report", rows.map(cockpitPortRow).join("")); return; }
    const body = rows.map((row) => {
      const stock = row.stock || {};
      const lines = Object.entries(stock).map(([name, item]) => {
        const label = (COM[name] || [name])[0];
        const side = item.side === "buys_from_player" ? "buys" : item.side === "sells_to_player" ? "sells" : "holds";
        return label + " " + side + " " + fmt(item.price) + " cr";
      }).join(", ");
      const hereId = Number((S.sector || {}).id);
      const docked = Number(row.sector_id) === hereId || Object.values(stock).some((item) => item && (item.side === "buys_from_player" || item.side === "sells_to_player"));
      if (!docked) {
        const word = row.last_seen_day == null ? "not visited" : "not docked";
        return '<div class="row" data-port="report"><span class="c">' + row.sector_id + "</span> class " + esc(row.class || row.name || "") + " " + word + "</div>";
      }
      const detailed = Object.entries(stock).map(([name, item]) => {
        const label = (COM[name] || [name])[0];
        const buying = item.side === "buys_from_player";
        const side = buying ? "Buying" : item.side === "sells_to_player" ? "Selling" : "Holds";
        const amount = buying ? Math.max(0, Number(item.max || 0) - Number(item.current || 0)) : Number(item.current || 0);
        const pct = item.max ? " (" + Math.round(100 * amount / Number(item.max)) + "%)" : "";
        return label + " " + side + " " + fmt(amount) + pct + " " + fmt(item.price) + " cr";
      }).join(", ");
      const seen = row.last_seen_day != null ? " day " + row.last_seen_day : "";
      return '<div class="row" data-port="report"><span class="c">' + row.sector_id + "</span> class " + esc(row.class || row.name || "") + esc(seen) + "<br>" + esc(detailed || lines) + "</div>";
    }).join("");
    overlay("Port Report", body);
  }
  function cockpitPortRow(row) {
    // cockpit-gaps-v1 item 3. The original Computer R port report lists each item, its status, the units
    // traded and what % of max that is (transcript.txt 1141-1150). It never lists a price, so the price here
    // is this seat's own note from its last dock (the original player keeps notes: S3 bible ~3186-3188).
    const sid = String(row.sector_id);
    const notes = ((CK && CK.port_notes) || {})[sid] || {};
    const stock = row.stock || {};
    const code = String(row.class || "");
    const names = ["fuel_ore", "organics", "equipment"];
    const lettered = /^[BS]{3}$/.test(code);
    const items = names.filter((name) => stock[name] || notes[name]).map((name) => {
      const item = stock[name] || {};
      const note = notes[name];
      const letter = lettered ? code[names.indexOf(name)] : "";
      const buying = item.side ? item.side === "buys_from_player" : (letter ? letter === "B" : (note && note.side === "buys"));
      const top = Number(item.max || 0);
      const amount = buying ? Math.max(0, top - Number(item.current || 0)) : Number(item.current || 0);
      const pct = top > 0 ? Math.round(100 * amount / top) : null;
      const seen = note ? "last seen " + fmt(note.price) + " cr on day " + note.day + " when you docked" : "no price: not docked here";
      return '<div class="row" data-port-item="' + esc(sid + ":" + name) + '">' + esc((COM[name] || [name])[0])
        + " " + (buying ? "Buying" : "Selling") + " " + (item.current == null ? "?" : fmt(amount))
        + (pct == null ? "" : " " + pct + "% of max") + ", " + esc(seen) + "</div>";
    }).join("");
    const age = row.age_days != null ? ", report " + fmt(row.age_days) + " day" + (Number(row.age_days) === 1 ? "" : "s") + " old" : "";
    return '<div class="row" data-port="report" data-sector="' + esc(sid) + '"><span class="c">' + esc(sid) + "</span> class "
      + esc(code || row.name || "") + esc(age) + (items || '<div class="row dk">No items listed.</div>') + "</div>";
  }
  function knownUniverse() {
    const map = Object.assign({}, S.known_warps || {});
    const id = String((S.sector || {}).id ?? "");
    if (id && !map[id]) map[id] = (S.sector || {}).warps_out || [];
    const ids = Object.keys(map);
    if (!ids.length) { setResult("No sectors in your computer yet.", true); return; }
    const explored = ((S.known_sectors || []).filter((row) => row.warps_known).length) || ids.length;
    let universeSize = Number(S.universe_size || 0);
    if (!universeSize) {
      const hit = streamLog.concat((S && S.recent_events) || []).map((ev) => (ev && ev.summary) || "").join(" ").match(/(\d+)-sector galaxy/);
      if (hit) universeSize = Number(hit[1]);
    }
    const pct = universeSize ? Math.round(100 * explored / universeSize) : 0;
    const body = ids.sort((a, b) => Number(a) - Number(b)).map((sid) => {
      const hops = map[sid] || [];
      return '<div class="row"><span class="c">' + sid + "</span> warps " + hops.join(", ") + "</div>";
    }).join("");
    const sectorWord = explored === 1 ? "sector" : "sectors";
    overlay("Known Universe", '<div class="row">You have explored ' + fmt(explored) + " " + sectorWord + (universeSize ? ", " + pct + "% of the universe" : "") + ".</div>" + body);
  }
  async function gameStatus() {
    await loadTaxTerms();
    const stats = S.daily_stats || {};
    const lines = [
      ["Day", S.day + " of " + S.max_days],
      ["Turns", fmt(S.turns_remaining) + " / " + fmt(S.turns_per_day)],
      ["Credits", fmt(S.credits) + " cr"],
      ["Bank", S.bank_balance == null ? "none" : fmt(S.bank_balance) + " cr"],
      ["Net worth (estimate)", fmt(S.net_worth) + " cr"],
      ["Rank", (S.rank || "") + (S.experience != null ? " (experience " + fmt(S.experience) + ")" : "")],
      ["Experience", fmt(S.experience)],
      ["Alignment", fmt(S.alignment) + " " + (S.alignment_label || "")],
      ["Overnight tax", lastTaxLine() || "none yet"],
      ["Tax due tomorrow", S.tax_due_tomorrow == null ? "none" : fmt(S.tax_due_tomorrow) + " cr (" + taxRulePhrase() + ")"],
      ["Planets", fmt((S.owned_planets || []).length)],
      ["Known ports", fmt((S.known_ports || []).length)],
      ["Known sectors", fmt(Object.keys(S.known_warps || {}).length)],
    ];
    Object.entries(stats).forEach(([k, v]) => lines.push([k.replaceAll("_", " "), fmt(v)]));
    netWorthLines().forEach((pair) => lines.push(pair));
    if (S.end_rule) lines.push(["How this game ends", S.end_rule]);
    if (S.nw_note) lines.push(["Net worth estimate", S.nw_note]);
    const rows = lines.map(([k, v]) => '<div class="row"><span class="g">' + esc(k) + '</span> <span class="c">' + esc(v) + "</span></div>").join("");
    const note = '<div class="row" data-worth="note">' + esc(worthNote()) + "</div>";
    const info = SC ? '<div class="row" data-game-info="credits"><span class="c">' + esc(SC) + "</span></div>" : "";
    const turnsInfo = TD ? '<div class="row" data-game-info="turns"><span class="c">' + esc(TD) + "</span></div>" : "";
    overlay("Game Status", rows + note + info + turnsInfo);
  }
  function worthNote() {
    // NOTE 71 sentence; under NOTE 73's estimate switch the engine sends what it now counts.
    return "Under v3.11 rules you are ranked by experience; net worth is this game's estimate. "
      + ((S && S.nw_note) || "Bought holds and fighters left in sectors are not counted.");
  }
  function netWorthLines() {
    const ship = (S && S.ship) || {};
    const cargo = ship.cargo || {};
    const base = { fuel_ore: 26, organics: 56, equipment: 102, colonists: 10 };
    const lines = [
      ["Cash", fmt(S.credits) + " cr"],
      ["Bank", S.bank_balance == null ? "none" : fmt(S.bank_balance) + " cr"],
    ];
    Object.keys(base).forEach((key) => {
      const n = Number(cargo[key] || 0);
      if (!n) return;
      const name = (COM[key] || [key])[0];
      lines.push([name, fmt(n) + " at " + fmt(base[key]) + " cr"]);
    });
    lines.push(["Hull", "half the shipyard price"]);
    lines.push(["Carried fighters", fmt(ship.fighters || 0)]);
    lines.push(["Carried shields", fmt(ship.shields || 0)]);
    (S.owned_planets || []).forEach((p) => {
      const col = Number(p.colonists_total || 0);
      const goods = Object.entries(p.stockpile || {}).filter((pair) => Number(pair[1]) > 0)
        .map((pair) => ((COM[pair[0]] || [pair[0]])[0]) + " " + fmt(pair[1])).join(", ") || "none";
      lines.push([
        p.name || "Planet",
        "colonists " + fmt(col) + " x 10 = " + fmt(col * 10) + " cr; goods " + goods
          + "; defences " + fmt(p.fighters || 0) + " fighters, " + fmt(p.shields || 0) + " shields",
      ]);
    });
    lines.push(["Engine net worth", fmt(S.net_worth) + " cr"]);
    return lines;
  }
  function netWorthPage() {
    const rows = netWorthLines().map(([k, v]) => '<div class="row"><span class="g">' + esc(k) + '</span> <span class="c">' + esc(v) + "</span></div>").join("");
    const note = '<div class="row" data-worth="note">' + esc(worthNote()) + "</div>";
    overlay("Net worth (estimate)", rows + note);
  }
  function deployedHoldings() {
    const rows = {};
    const touch = (sector) => {
      const id = Number(sector);
      if (!id) return null;
      if (!rows[id]) rows[id] = { fighters: 0, mode: "", mines: {} };
      return rows[id];
    };
    const seen = new Set();
    streamLog.concat((S && S.recent_events) || []).forEach((ev) => {
      if (!ev || ev.actor_id !== S.self_id || seen.has(ev.seq)) return;
      seen.add(ev.seq);
      const row = touch(ev.sector_id);
      if (!row) return;
      const facts = ev.facts || {};
      const qty = Number(facts.qty || 0);
      if (ev.kind === "deploy_fighters") {
        row.fighters += qty;
        if (facts.mode) row.mode = facts.mode;
      } else if (ev.kind === "deploy_mines") {
        const kind = facts.kind || "mines";
        row.mines[kind] = (row.mines[kind] || 0) + qty;
      } else if (ev.kind === "recall_deployed") {
        if (facts.what === "fighters") row.fighters -= qty;
        else if (facts.kind) row.mines[facts.kind] = (row.mines[facts.kind] || 0) - qty;
      }
    });
    const group = (S.sector || {}).fighter_group;
    if (group && group.owner_id === S.self_id) {
      const row = touch(S.sector.id);
      if (row) {
        row.fighters = Number(group.count || 0);
        if (group.mode) row.mode = group.mode;
      }
    }
    return rows;
  }
  function showFighters() {
    const lines = [];
    const held = deployedHoldings();
    Object.keys(held).map(Number).sort((a, b) => a - b).forEach((id) => {
      const row = held[id];
      const bits = [];
      if (row.fighters > 0) bits.push(fmt(row.fighters) + " " + (row.mode || "") + " fighters");
      Object.entries(row.mines).forEach(([kind, n]) => {
        if (n > 0) bits.push(fmt(n) + " " + String(kind).replaceAll("_", " ") + (n === 1 ? " mine" : " mines"));
      });
      if (bits.length) lines.push("Sector " + id + ": " + bits.join(", "));
    });
    if (!lines.length) lines.push("No deployed fighters.");
    (S.owned_planets || []).forEach((p) => {
      if (Number(p.fighters) > 0) lines.push(esc(p.name || "planet") + ": " + fmt(p.fighters));
    });
    lines.push("On your ship: " + fmt((S.ship || {}).fighters || 0));
    overlay("Deployed Fighters", lines.map((line) => '<div class="row">' + line + "</div>").join(""));
  }
  function dockForm(kind, title, note, fields, saved, submit) {
    const slot = $("formSlot");
    if (!slot) return;
    openFormKind = kind;
    slot.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "frm";
    wrap.dataset.screen = kind;
    wrap.innerHTML = '<div class="y">' + title + "</div>";
    if (note) {
      const line = document.createElement("div");
      line.className = "c";
      line.dataset.price = "dock";
      line.textContent = note;
      wrap.appendChild(line);
    }
    const inputs = {};
    fields.forEach((field) => {
      const el = field.choices ? document.createElement("select") : document.createElement("input");
      if (field.choices) {
        field.choices.forEach((choice) => {
          const o = document.createElement("option");
          o.value = choice.value;
          o.textContent = choice.label;
          el.appendChild(o);
        });
      } else {
        el.type = field.type || "text";
        if (field.min != null) el.min = String(field.min);
        if (field.max != null) el.max = String(field.max);
      }
      el.dataset.n = field.n;
      if (saved && saved[field.n] != null && saved[field.n] !== "") el.value = saved[field.n];
      else if (field.value != null) el.value = String(field.value);
      inputs[field.n] = el;
      const label = document.createElement("label");
      label.appendChild(document.createTextNode((field.label || field.n) + " "));
      label.appendChild(el);
      wrap.appendChild(label);
    });
    const go = () => {
      const values = {};
      let missing = false;
      let noAmount = false;
      fields.forEach((field) => {
        const el = inputs[field.n];
        const raw = String(el.value == null ? "" : el.value).trim();
        values[field.n] = el.type === "number" ? (raw === "" ? "" : Number(raw)) : raw;
        if (field.required !== false && raw === "") {
          missing = true;
          if (/^(qty|amount|units)$/.test(field.n)) noAmount = true;
        }
      });
      if (noAmount) { setResult("Type an amount.", true); return; }
      if (missing) { setResult("Fill in the form.", true); return; }
      openFormKind = null;
      slot.innerHTML = "";
      submit(values);
    };
    wrap.appendChild(button("CONFIRM", go));
    wrap.appendChild(button("ESC", () => { openFormKind = null; slot.innerHTML = ""; }));
    wrap.addEventListener("keydown", (ev) => formKey(ev, go));
    slot.appendChild(wrap);
    const first = wrap.querySelector('input[type="number"], input[type="text"]') || wrap.querySelector("select");
    if (first) {
      first.focus();
      if (first.select) first.select();
    }
  }
  function tavernText(which, saved) {
    const kind = which || (saved && saved.which) || "tavern_talk";
    const a = LA(kind) || { legal: false, reason: "", params: {} };
    if (!a.legal && !saved) { setResult(plainReason(a.reason), true); return; }
    const cost = Number((a.params || {}).cost || 0);
    const titles = { tavern_announce: "ANNOUNCE", tavern_talk: "TALK", tavern_graffiti: "GRAFFITI" };
    dockForm("tavernText", titles[kind] || "TAVERN", cost ? "This costs " + fmt(cost) + " cr." : "This is free.", [
      { n: "which", label: "which", choices: [{ value: kind, label: titles[kind] || kind }] },
      { n: "text", label: "text", type: "text" },
    ], Object.assign({ which: kind }, saved || {}), (values) => act(values.which || kind, { text: values.text }, kind));
  }
  function tavernOrder(saved) {
    const a = LA("tavern_order") || { legal: false, reason: "", params: {} };
    if (!a.legal && !saved) { setResult("Order: " + plainReason(a.reason), true); return; }
    const costs = (a.params || {}).cost_by || {};
    dockForm("tavernOrder", "ORDER", "Drink " + fmt(costs.drink || 0) + " cr. Food " + fmt(costs.food || 0) + " cr.", [
      { n: "item", label: "item", choices: [{ value: "drink", label: "drink" }, { value: "food", label: "food" }] },
    ], saved, (values) => act("tavern_order", { item: values.item }, "order"));
  }
  function grimyAsk(saved) {
    const a = LA("grimy_ask") || { legal: false, reason: "", params: {} };
    if (!a.legal && !saved) { setResult("Ask Grimy: " + plainReason(a.reason), true); return; }
    const topics = (((a.params || {}).topic || {}).choices) || [];
    const targets = (((a.params || {}).target || {}).choices) || [];
    const costs = (a.params || {}).cost_by || {};
    const fields = [{ n: "topic", label: "topic", choices: topics.map((topic) => ({ value: topic, label: topic })) }];
    if (targets.length) fields.push({ n: "target", label: "target", required: false, choices: targets.map((id) => ({ value: id, label: commanderName(id) })) });
    const note = "A trader trace costs " + fmt(costs.trader || 0) + " cr. Underground or mafia costs " + fmt(costs.underground || costs.mafia || 0) + " cr.";
    dockForm("grimyAsk", "ASK GRIMY", note, fields, saved, (values) => {
      const args = { topic: values.topic };
      if (values.topic === "trader" && values.target) args.target = values.target;
      act("grimy_ask", args, "ask");
    });
  }
  function ugEnter(saved) {
    const a = LA("underground_enter") || { legal: false, reason: "" };
    if (!a.legal && !saved) { setResult("Enter underground: " + plainReason(a.reason), true); return; }
    dockForm("ugEnter", "UNDERGROUND", "The Underground asks for its password.", [
      { n: "password", label: "password", type: "text" },
    ], saved, (values) => act("underground_enter", { password: values.password }, "enter"));
  }
  function ugContract(saved) {
    const a = LA("underground_contract") || { legal: false, reason: "", params: {} };
    if (!a.legal && !saved) { setResult("Contract: " + plainReason(a.reason), true); return; }
    const params = a.params || {};
    const targets = ((params.target || {}).choices) || [];
    const min = Number((params.amount || {}).min || 0);
    dockForm("ugContract", "CONTRACT", "At least " + fmt(min) + " cr. " + fmt(params.credits_per_align || 0) + " cr per alignment point.", [
      { n: "target", label: "target", choices: targets.map((id) => ({ value: id, label: commanderName(id) })) },
      { n: "amount", label: "amount", type: "number", min: min },
    ], saved, (values) => act("underground_contract", { target: values.target, amount: Number(values.amount) }, "contract"));
  }
  function postReward(saved) {
    const a = LA("post_reward") || { legal: false, reason: "", params: {} };
    if (!a.legal && !saved) { setResult("Post a reward: " + plainReason(a.reason), true); return; }
    const params = a.params || {};
    const targets = ((params.target_id || {}).choices) || [];
    const min = Number((params.amount || {}).min || 0);
    dockForm("postReward", "POST A REWARD", "At least " + fmt(min) + " cr.", [
      { n: "target_id", label: "target", choices: targets.map((id) => ({ value: id, label: commanderName(id) })) },
      { n: "amount", label: "amount", type: "number", min: min },
    ], saved, (values) => act("post_reward", { target_id: values.target_id, amount: Number(values.amount) }, "reward"));
  }
  function shipPassword(saved) {
    const a = LA("ship_set_password") || { legal: false, reason: "" };
    if (!a.legal && !saved) { setResult("Ship password: " + plainReason(a.reason), true); return; }
    dockForm("shipPassword", "SHIP PASSWORD", "A corp mate needs this word to board the ship.", [
      { n: "password", label: "password", type: "text" },
    ], saved, (values) => act("ship_set_password", { password: values.password }, "password"));
  }
  function sellShip(saved) {
    const a = LA("sell_ship") || { legal: false, reason: "", params: {} };
    if (!a.legal && !saved) { setResult("Sell a spare ship: " + plainReason(a.reason), true); return; }
    const spec = (a.params || {}).ship_id || {};
    const credits = spec.credit_by || {};
    const choices = (spec.choices || []).map((id) => ({ value: String(id), label: "ship " + id + " for " + fmt(credits[String(id)] || 0) + " cr" }));
    const first = choices[0];
    dockForm("sellShip", "SELL A SPARE", first ? "You get " + fmt(credits[first.value] || 0) + " cr." : "", [
      { n: "ship_id", label: "ship", choices: choices },
    ], saved, (values) => act("sell_ship", { ship_id: Number(values.ship_id) }, "sell"));
  }
  function bankWire(saved) {
    const a = LA("bank_transfer") || { legal: false, reason: "", params: {} };
    if (!a.legal && !saved) { setResult("Bank transfer: " + plainReason(a.reason), true); return; }
    const people = (a.params || {}).recipients || [];
    dockForm("bankWire", "BANK TRANSFER", "Up to " + fmt((a.params || {}).max_amount || 0) + " cr from the credits you hold.", [
      { n: "to_player", label: "to", choices: people.map((row) => ({ value: row.player_id, label: row.name + " up to " + fmt(row.max_amount) + " cr" })) },
      { n: "amount", label: "amount", type: "number", min: 1 },
    ], saved, (values) => act("bank_transfer", { to_player: values.to_player, amount: Number(values.amount) }, "transfer"));
  }
  function dockBox() {
    const box = document.createElement("div");
    box.className = "encounter";
    box.dataset.screen = "stardock";
    const title = document.createElement("div");
    title.className = "y";
    title.textContent = "StarDock";
    box.appendChild(title);
    const add = (kind, label, onLegal) => box.appendChild(reasonButton(kind, label, onLegal));
    add("tavern_order", "Order", () => tavernOrder());
    add("tavern_talk", "Talk", () => tavernText("tavern_talk"));
    add("tavern_announce", "Announce", () => tavernText("tavern_announce"));
    add("tavern_graffiti", "Graffiti", () => tavernText("tavern_graffiti"));
    add("grimy_ask", "Ask Grimy", () => grimyAsk());
    add("grimy_curse", "Curse", (a) => confirmWords("Curse", "This spends " + fmt(a.turn_cost || 1) + " turn.", () => act("grimy_curse", {}, "curse")));
    add("underground_enter", "Enter underground", () => ugEnter());
    add("underground_contract", "Contract", () => ugContract());
    add("underground_claim", "Claim underground", (a) => confirmWords("Claim underground", "Claim " + fmt((a.params || {}).pending || 0) + " cr?", () => act("underground_claim", {}, "claim")));
    add("cineplex", "Cineplex", (a) => {
      const cost = Number((a.params || {}).cost || 0);
      const line = cost ? "The picture costs " + fmt(cost) + " cr. It has no secrets." : "The picture is free. It has no secrets.";
      confirmWords("Cineplex", line, () => act("cineplex", {}, "cineplex"));
    });
    add("tricron", "Tri-Cron", (a) => {
      const ante = Number((a.params || {}).ante || 0);
      const rounds = Number((a.params || {}).rounds || 0);
      const pot = (S && S.tavern && S.tavern.tricron && S.tavern.tricron.jackpot) || 0;
      confirmWords("Tri-Cron", "Ante " + fmt(ante) + " cr. " + rounds + " rounds. Pays 2:1." + (pot ? " Jackpot " + fmt(pot) + " cr." : ""), () => act("tricron", {}, "tricron"));
    });
    add("apply_commission", "Federal commission", () => confirmWords("Federal commission", "Apply for a Federal commission? You can take it once.", () => act("apply_commission", {}, "commission")));
    add("post_reward", "Post a reward", () => postReward());
    add("claim_reward", "Claim a reward", () => act("claim_reward", {}, "reward"));
    add("ship_set_password", "Ship password", () => shipPassword());
    add("sell_ship", "Sell a spare ship", () => sellShip());
    add("bank_transfer", "Transfer credits", () => bankWire());
    return box;
  }
  function corpField(kind, title, note, field, saved, submit) {
    const slot = $("formSlot");
    if (!slot) return;
    openFormKind = kind;
    const menu = $("menu");
    if (menu) menu.hidden = true;
    slot.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "frm";
    wrap.dataset.screen = kind;
    wrap.innerHTML = '<div class="y">' + title + "</div>" + (note ? '<div class="c">' + note + "</div>" : "");
    const input = document.createElement("input");
    input.type = "text";
    input.dataset.n = field;
    if (saved && saved[field]) input.value = saved[field];
    const label = document.createElement("label");
    label.appendChild(document.createTextNode(field + " "));
    label.appendChild(input);
    wrap.appendChild(label);
    const go = () => {
      const value = String(input.value || "").trim();
      if (!value) { setResult("Type the " + field + ".", true); return; }
      openFormKind = null;
      slot.innerHTML = "";
      submit(value);
    };
    wrap.appendChild(button("CONFIRM", go));
    wrap.appendChild(button("ESC", () => { openFormKind = null; slot.innerHTML = ""; }));
    wrap.addEventListener("keydown", (ev) => formKey(ev, go));
    slot.appendChild(wrap);
    input.focus();
    input.select();
  }
  function memoForm(saved) {
    const a = LA("corp_memo") || { legal: false, reason: "" };
    if (!a.legal && !saved) { setResult("Memo: " + plainReason(a.reason), true); return; }
    corpField("memo", "MEMO", "This goes to the corporation.", "message", saved, (message) => act("corp_memo", { message }, "memo"));
  }
  function passwordForm(saved) {
    const a = LA("corp_set_password") || { legal: false, reason: "" };
    if (!a.legal && !saved) { setResult("Set password: " + plainReason(a.reason), true); return; }
    corpField("corpPassword", "PASSWORD", "The corporation asks for this when someone joins.", "password", saved, (password) => act("corp_set_password", { password }, "password"));
  }
  function joinForm(saved) {
    const a = LA("corp_join") || { legal: false, reason: "", params: {} };
    const slot = $("formSlot");
    if (!slot) return;
    if (!a.legal && !saved) { setResult("Join: " + plainReason(a.reason), true); return; }
    openFormKind = "join";
    const menu = $("menu");
    if (menu) menu.hidden = true;
    slot.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "frm";
    wrap.dataset.screen = "join";
    wrap.innerHTML = '<div class="y">JOIN</div><div class="c">The corporation asks for its password.</div>';
    const ticker = document.createElement("select");
    ticker.dataset.n = "ticker";
    ((((a.params || {}).ticker || {}).choices) || []).forEach((id) => {
      const o = document.createElement("option");
      o.value = id;
      o.textContent = id;
      ticker.appendChild(o);
    });
    if (saved && saved.ticker) ticker.value = saved.ticker;
    const password = document.createElement("input");
    password.type = "text";
    password.dataset.n = "password";
    if (saved && saved.password) password.value = saved.password;
    const tickerLabel = document.createElement("label");
    tickerLabel.appendChild(document.createTextNode("ticker "));
    tickerLabel.appendChild(ticker);
    const passwordLabel = document.createElement("label");
    passwordLabel.appendChild(document.createTextNode("password "));
    passwordLabel.appendChild(password);
    wrap.appendChild(tickerLabel);
    wrap.appendChild(passwordLabel);
    const go = () => {
      const word = String(password.value || "").trim();
      if (!ticker.value || !word) { setResult("Type the password.", true); return; }
      openFormKind = null;
      slot.innerHTML = "";
      act("corp_join", { ticker: ticker.value, password: word }, "join");
    };
    wrap.appendChild(button("CONFIRM", go));
    wrap.appendChild(button("ESC", () => { openFormKind = null; slot.innerHTML = ""; }));
    wrap.addEventListener("keydown", (ev) => formKey(ev, go));
    slot.appendChild(wrap);
    password.focus();
    password.select();
  }
  function dropForm(a, saved) {
    const spec = a || LA("corp_drop") || { legal: false, reason: "", params: {} };
    const slot = $("formSlot");
    if (!slot) return;
    if (!spec.legal && !saved) { setResult("Drop member: " + plainReason(spec.reason), true); return; }
    openFormKind = "drop";
    const menu = $("menu");
    if (menu) menu.hidden = true;
    slot.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "frm";
    wrap.dataset.screen = "drop";
    wrap.innerHTML = '<div class="y">DROP MEMBER</div>';
    const target = document.createElement("select");
    target.dataset.n = "target";
    const members = ((spec.params || {}).members) || [];
    ((((spec.params || {}).target || {}).choices) || []).forEach((id) => {
      const o = document.createElement("option");
      o.value = id;
      const named = members.find((row) => row.player_id === id);
      o.textContent = named ? named.name : commanderName(id);
      target.appendChild(o);
    });
    if (saved && saved.target) target.value = saved.target;
    const label = document.createElement("label");
    label.appendChild(document.createTextNode("member "));
    label.appendChild(target);
    wrap.appendChild(label);
    const go = () => {
      if (!target.value) { setResult("Pick a member.", true); return; }
      openFormKind = null;
      slot.innerHTML = "";
      act("corp_drop", { target: target.value }, "drop");
    };
    wrap.appendChild(button("CONFIRM", go));
    wrap.appendChild(button("ESC", () => { openFormKind = null; slot.innerHTML = ""; }));
    wrap.addEventListener("keydown", (ev) => formKey(ev, go));
    slot.appendChild(wrap);
  }
  function transferForm(a, saved) {
    const spec = a || LA("corp_transfer") || { legal: false, reason: "", params: {} };
    const slot = $("formSlot");
    if (!slot) return;
    if (!spec.legal && !saved) { setResult("Give or take: " + plainReason(spec.reason), true); return; }
    openFormKind = "transfer";
    const menu = $("menu");
    if (menu) menu.hidden = true;
    const params = spec.params || {};
    slot.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "frm";
    wrap.dataset.screen = "transfer";
    wrap.innerHTML = '<div class="y">GIVE OR TAKE</div><div class="c">A mate in this sector. This does not hand over the C.E.O. seat.</div>';
    const target = document.createElement("select");
    target.dataset.n = "target";
    ((params.target || {}).choices || []).forEach((id) => {
      const o = document.createElement("option");
      o.value = id;
      const named = (params.partners || []).find((row) => row.player_id === id);
      o.textContent = named ? named.name : commanderName(id);
      target.appendChild(o);
    });
    const item = document.createElement("select");
    item.dataset.n = "item";
    ["credits", "fighters", "shields", "armid_mines", "limpet_mines"].forEach((name) => {
      const o = document.createElement("option");
      o.value = name;
      o.textContent = name.replaceAll("_", " ");
      item.appendChild(o);
    });
    const direction = document.createElement("select");
    direction.dataset.n = "direction";
    ["give", "take"].forEach((name) => {
      const o = document.createElement("option");
      o.value = name;
      o.textContent = name;
      direction.appendChild(o);
    });
    const qty = document.createElement("input");
    qty.type = "number";
    qty.min = "1";
    qty.dataset.n = "qty";
    qty.value = "1";
    if (saved) {
      if (saved.target) target.value = saved.target;
      if (saved.item) item.value = saved.item;
      if (saved.direction) direction.value = saved.direction;
      if (saved.qty) qty.value = saved.qty;
    }
    [["mate ", target], ["item ", item], ["direction ", direction], ["qty ", qty]].forEach(([name, el]) => {
      const label = document.createElement("label");
      label.appendChild(document.createTextNode(name));
      label.appendChild(el);
      wrap.appendChild(label);
    });
    const go = () => {
      const n = Number(qty.value);
      if (!target.value) { setResult("Pick a mate.", true); return; }
      if (!n) { setResult("Type an amount.", true); return; }
      openFormKind = null;
      slot.innerHTML = "";
      act("corp_transfer", { target: target.value, item: item.value, qty: n, direction: direction.value }, "transfer");
    };
    wrap.appendChild(button("CONFIRM", go));
    wrap.appendChild(button("ESC", () => { openFormKind = null; slot.innerHTML = ""; }));
    wrap.addEventListener("keydown", (ev) => formKey(ev, go));
    slot.appendChild(wrap);
    qty.focus();
    qty.select();
  }
  function commanderName(id) {
    const row = ((S && S.other_players) || []).find((item) => item.id === id);
    if (row && row.name) return row.name;
    const member = (((S && S.corp) || {}).members || []).find((item) => item.id === id);
    return (member && member.name) || id;
  }
  function allianceCommander(id) {
    const row = ((S && S.alliances) || []).find((item) => item.id === id);
    if (!row) return id;
    const other = (row.members || []).find((m) => m !== S.self_id) || row.proposed_by;
    return commanderName(other);
  }
  function commanderPick(title, line, ids, onPick, labelFor) {
    const m = $("menu");
    m.hidden = false;
    inComputer = false;
    m.dataset.screen = title;
    const nameOf = labelFor || commanderName;
    const options = ids.map((id) => '<option value="' + esc(id) + '">' + esc(nameOf(id)) + "</option>").join("");
    m.innerHTML = '<div class="y">' + esc(title) + "</div><div>" + esc(line) + "</div>"
      + '<label>Commander <select id="commanderPick" data-player-pick="1">' + options + "</select></label> "
      + '<button type="button" id="dangerOk">CONFIRM</button><br><span class="dk">Esc to close</span>';
    $("dangerOk").addEventListener("click", () => {
      const id = $("commanderPick").value;
      m.hidden = true;
      onPick(id);
    });
  }
  function corpMenu() {
    const c = S.corp || {};
    const m = $("menu");
    m.hidden = false;
    inComputer = false;
    m.dataset.screen = "Corporate Menu";
    const members = (c.members || []).map((row) => {
      return '<div class="row" data-member="' + esc(row.id) + '">' + esc(row.name) + (row.ceo ? " C.E.O." : "") + " " + fmt(row.credits) + " cr</div>";
    }).join("");
    const total = (c.members || []).reduce((sum, row) => sum + Number(row.credits || 0), 0);
    m.innerHTML = '<div class="y" data-corp="ticker">' + esc(c.ticker || "") + " " + esc(c.name || "") + "</div>"
      + members
      + '<div data-corp="credits">Member credits ' + fmt(total) + " cr</div>"
      + '<div id="corpBtns"></div><br><span class="dk">Esc to close</span>';
    const box = document.getElementById("corpBtns");
    const add = (kind, label, onLegal) => box.appendChild(reasonButton(kind, label, onLegal));
    add("corp_invite", "Invite", (a) => {
      const ids = ((((a.params || {}).target || {}).choices) || []);
      if (!ids.length) { setResult("Invite: no trader to invite", true); return; }
      commanderPick("Invite", "Invite a commander", ids, (id) => {
        confirmWords("Invite", "Invite " + esc(commanderName(id)) + "?", () => act("corp_invite", { target: id }, "invite"));
      });
    });
    add("corp_join", "Join", () => joinForm());
    add("corp_leave", "Leave", (a) => {
      const line = (a.params || {}).dissolves
        ? "Leave the corporation? You are the C.E.O., so it dissolves."
        : "Leave the corporation?";
      confirmWords("Leave", line, () => act("corp_leave", {}, "leave"));
    });
    add("corp_memo", "Memo", () => memoForm());
    if ((LA("corp_deposit") || {}).legal) {
      add("corp_deposit", "Deposit credits", (a) => {
        const max = Number((((a.params || {}).amount || {}).max) || (S && S.credits) || 0);
        dockForm("corpDeposit", "DEPOSIT CREDITS", "Up to " + fmt(max) + " cr.", [
          { n: "amount", label: "amount", type: "number", min: 1 },
        ], null, (values) => act("corp_deposit", { amount: Number(values.amount) }, "deposit"));
      });
    }
    if ((LA("corp_withdraw") || {}).legal) {
      add("corp_withdraw", "Withdraw credits", (a) => {
        const max = Number((((a.params || {}).amount || {}).max) || 0);
        dockForm("corpWithdraw", "WITHDRAW CREDITS", "Up to " + fmt(max) + " cr.", [
          { n: "amount", label: "amount", type: "number", min: 1 },
        ], null, (values) => act("corp_withdraw", { amount: Number(values.amount) }, "withdraw"));
      });
    }
    add("corp_set_password", "Set password", () => passwordForm());
    add("corp_drop", "Drop member", (a) => dropForm(a));
    const ceo = button("Transfer C.E.O.", () => setResult("Handing the C.E.O. seat to another member is not in this game.", true));
    ceo.dataset.kind = "transfer_ceo";
    box.appendChild(ceo);
    add("corp_transfer", "Give or take", (a) => transferForm(a));
    add("ship_set_corporate", "Make ship corporate", () => act("ship_set_corporate", {}, "corporate"));
    add("ship_set_personal", "Make ship personal", () => act("ship_set_personal", {}, "personal"));
    add("propose_alliance", "Propose alliance", (a) => {
      const ids = ((((a.params || {}).target || {}).choices) || []);
      if (!ids.length) { setResult("Propose alliance: no other commander", true); return; }
      commanderPick("Propose alliance", "Propose an alliance to", ids, (id) => {
        confirmWords("Propose alliance", "Propose an alliance to " + esc(commanderName(id)) + "?", () => act("propose_alliance", { target: id }, "propose"));
      });
    });
    add("accept_alliance", "Accept alliance", (a) => {
      const ids = ((((a.params || {}).alliance_id || {}).choices) || []);
      if (!ids.length) { setResult("Accept alliance: no alliance proposal pending for you", true); return; }
      commanderPick("Accept alliance", "Accept an alliance with", ids, (id) => {
        act("accept_alliance", { alliance_id: id }, "accept");
      }, allianceCommander);
    });
    add("break_alliance", "Break alliance", (a) => {
      const id = ((((a.params || {}).alliance_id || {}).choices) || [])[0];
      if (!id) { setResult("Break alliance: you are in no alliance", true); return; }
      confirmWords("Break alliance", "Break alliance " + esc(id) + "?", () => act("break_alliance", { alliance_id: id }, "break"));
    });
  }
  function spaceBox() {
    const box = document.createElement("div");
    box.className = "encounter";
    box.dataset.screen = "space";
    if ((S.sector || {}).port) {
      box.appendChild(reasonButton("rob", "Rob this port", () => robForm()));
      box.appendChild(reasonButton("steal", "Steal cargo", () => stealForm()));
      box.appendChild(reasonButton("port_upgrade", "Upgrade this port", () => upgradeForm()));
      box.appendChild(reasonButton("planet_trade", "Planet trade", () => tradeForm()));
    }
    box.appendChild(reasonButton("port_build", "Build a port", () => buildForm()));
    box.appendChild(reasonButton("deploy_atomic", "Atomic detonator", () => atomicForm()));
    box.appendChild(reasonButton("hail", "Hail one player", () => hailForm()));
    return box;
  }
  function robForm(saved) {
    const max = Number((((LA("rob") || {}).params || {}).amount || {}).max || 1);
    dockForm("rob", "ROB THIS PORT", "About 1 chance in 50 of a bust. Alignment must be -100 or lower. This vault allows up to " + fmt(max) + " cr.", [
      { n: "amount", label: "Credits", type: "number", min: 1, value: "1" },
    ], saved, (values) => act("rob", { amount: values.amount }, "rob"));
  }
  function stealForm(saved) {
    const choices = ((((LA("steal") || {}).params || {}).commodity || {}).choices) || [];
    dockForm("steal", "STEAL CARGO", "About 1 chance in 50 of a bust. You can take only what is on the shelf and what your holds can carry.", [
      { n: "commodity", label: "Cargo", choices: choices.map((name) => ({ value: name, label: (COM[name] || [name])[0] })) },
      { n: "qty", label: "Quantity", type: "number", min: 1, value: "1" },
    ], saved, (values) => act("steal", { commodity: values.commodity, qty: values.qty }, "steal"));
  }
  function upgradeForm(saved) {
    const rows = ((LA("port_upgrade") || {}).params || {}).commodities || {};
    const choices = Object.entries(rows).filter((pair) => Number(pair[1].max_units) >= 1);
    const note = choices.map((pair) => (COM[pair[0]] || [pair[0]])[0] + " " + fmt(pair[1].unit_cost) + " cr a unit, " + fmt(pair[1].holds_per_unit) + " holds").join(". ") + ".";
    dockForm("portUpgrade", "UPGRADE THIS PORT", note, [
      { n: "commodity", label: "Commodity", choices: choices.map((pair) => ({ value: pair[0], label: (COM[pair[0]] || [pair[0]])[0] })) },
      { n: "units", label: "Units", type: "number", min: 1, value: "1" },
    ], saved, (values) => act("port_upgrade", { commodity: values.commodity, units: values.units }, "upgrade"));
  }
  function buildForm(saved) {
    const params = (LA("port_build") || {}).params || {};
    const classes = params.classes || {};
    const planets = params.planets || [];
    const note = Object.entries(classes).map((pair) => pair[0] + " " + fmt(pair[1].cost) + " cr, " + pair[1].days + " days").join(". ") + ".";
    dockForm("portBuild", "BUILD A PORT", note, [
      { n: "port_class", label: "Class", choices: Object.keys(classes).map((code) => ({ value: code, label: code + " " + fmt(classes[code].cost) + " cr" })) },
      { n: "planet_id", label: "Planet", choices: planets.map((row) => ({ value: String(row.planet_id), label: row.name })) },
    ], saved, (values) => act("port_build", { port_class: values.port_class, planet_id: Number(values.planet_id) }, "build a port"));
  }
  function tradeForm(saved) {
    const planets = ((LA("planet_trade") || {}).params || {}).planets || [];
    const first = planets[0] || { sellable: {}, quote: {}, name: "This planet" };
    const goods = Object.keys(first.sellable || {});
    const commodity = goods[0];
    const quote = commodity ? (first.quote || {})[commodity] : null;
    const note = (first.name || "This planet") + (commodity ? " can sell " + (COM[commodity] || [commodity])[0] + " for " + fmt(quote) + " cr at the quote." : " has nothing this port is buying.") + " One counter only. A greedy one is refused.";
    dockForm("planetTrade", "PLANET TRADE", note, [
      { n: "planet_id", label: "Planet", choices: planets.map((row) => ({ value: String(row.planet_id), label: row.name })) },
      { n: "commodity", label: "Commodity", choices: goods.map((name) => ({ value: name, label: (COM[name] || [name])[0] })) },
      { n: "qty", label: "Quantity", type: "number", min: 1, value: "1" },
    ], saved, (values) => act("planet_trade", { planet_id: Number(values.planet_id), commodity: values.commodity, qty: values.qty }, "planet trade"));
  }
  function atomicForm(saved) {
    const params = (LA("deploy_atomic") || {}).params || {};
    const ids = ((params.planet_id || {}).choices) || [];
    const note = "Detonators aboard: " + fmt(params.detonators_aboard) + ". " + (params.note || "colonists still alive disarm it and the blast destroys YOUR ship") + (params.colonists_alive ? " Colonists are still alive." : " No colonists are alive, so the planet is destroyed.");
    dockForm("atomic", "ATOMIC DETONATOR", note, [
      { n: "planet_id", label: "Planet", choices: ids.map((id) => ({ value: String(id), label: "Planet " + id })) },
    ], saved, (values) => act("deploy_atomic", { planet_id: Number(values.planet_id) }, "atomic detonator"));
  }
  function hailForm(saved) {
    const ids = ((((LA("hail") || {}).params || {}).target || {}).choices) || [];
    const labelFor = (id) => {
      const row = (S.other_players || []).find((item) => item.id === id);
      return (row && row.name) || id;
    };
    dockForm("hail", "HAIL ONE PLAYER", "This goes only to " + (ids[0] ? labelFor(ids[0]) : "that player") + ", not the whole sector.", [
      { n: "target", label: "Player", choices: ids.map((id) => ({ value: id, label: labelFor(id) })) },
      { n: "message", label: "Message", type: "text", value: "Hello" },
    ], saved, (values) => act("hail", { target: values.target, message: values.message }, "hail"));
  }
  function galaxySize() {
    let size = Number(S && S.universe_size || 0);
    if (!size) {
      const hit = streamLog.concat((S && S.recent_events) || []).map((ev) => (ev && ev.summary) || "").join(" ").match(/(\d+)-sector galaxy/);
      if (hit) size = Number(hit[1]);
    }
    return size;
  }
  function avoidedNames() {
    const listed = (S && S.avoid_prompt) || "";
    const match = /Avoided sectors:\s*([^.]*)/i.exec(listed);
    return match ? match[1].trim() : "";
  }
  function avoidIds(text) {
    return String(text || "").split(",").map((part) => part.trim()).filter(Boolean);
  }
  function avoidSentence(sector, prior) {
    if (Number(sector) === 0) return "Avoid list cleared. Avoided sectors: none.";
    const names = avoidedNames();
    const id = fmt(sector);
    const had = avoidIds(prior).includes(id);
    const verb = had ? " is already on the avoid list" : " added to the avoid list";
    return "Sector " + id + verb + (names ? " (avoided: " + names + ")" : "");
  }
  function avoidForm(saved) {
    const a = LA("avoid");
    if (!a) { setResult("Avoid sectors: Avoid sectors is not in this game.", true); return; }
    if (!a.legal) { setResult("Avoid sectors: " + plainReason(a.reason), true); return; }
    const listed = (S && S.avoid_prompt) || "Avoided sectors: none.";
    const size = galaxySize();
    dockForm("avoid", "AVOID SECTORS", listed + " Type a sector the computer should not plot through, or 0 to clear the list.", [
      { n: "sector", label: "Sector", type: "number", min: 0, max: size || null, value: "2" },
    ], saved, (values) => {
      const sector = Number(values.sector);
      const cap = galaxySize();
      if (sector !== 0 && cap && (sector < 1 || sector > cap)) {
        setResult("REFUSED — there is no sector " + fmt(sector) + ". Turns spent 0. Credits +0.", true);
        return;
      }
      act("avoid", { sector: values.sector }, "avoid");
    });
  }
  function jettisonForm(saved) {
    const choices = ((((LA("jettison") || {}).params || {}).commodity || {}).choices) || [];
    dockForm("jettison", "JETTISON CARGO", "Dumping colonists costs a good trader 1 alignment each, up to 250 a day. A trader who is not good pays no alignment. Other cargo is dumped into space and is gone.", [
      { n: "commodity", label: "Cargo", choices: choices.map((name) => ({ value: name, label: (COM[name] || [name])[0] })) },
      { n: "qty", label: "Quantity", type: "number", min: 1, value: "1" },
    ], saved, (values) => act("jettison", { commodity: values.commodity, qty: values.qty }, "jettison"));
  }
  function yardConfirm(args, action) {
    const params = (action && action.params) || {};
    const shipParams = params.ship_class || {};
    const stats = shipParams.stats_by || {};
    const nets = shipParams.net_cost_by || {};
    const spare = (params.trade_in || {}).spare_cost_by || {};
    const key = args.ship_class;
    const s = stats[key] || HULL[key] || {};
    const ship = (S && S.ship) || {};
    const fromH = Number(ship.holds || 0);
    const toH = Number(s.max_holds != null ? s.max_holds : (s.holds || 0));
    const fromF = Number(ship.fighters || 0);
    const toF = Number(s.max_fighters != null ? s.max_fighters : (s.fighters || 0));
    const fromS = Number(ship.shields || 0);
    const toS = Number(s.max_shields != null ? s.max_shields : (s.shields || 0));
    const net = Number(nets[key]);
    const credit = Number(shipParams.trade_in || 0);
    const price = spare[key] != null ? Number(spare[key]) : null;
    const money = net < 0 ? "You get " + fmt(-net) + " cr back" : "The cost is " + fmt(net) + " cr";
    const holds = toH < fromH
      ? "drop from " + fmt(fromH) + " holds to " + fmt(toH)
      : (toH > fromH ? "go from " + fmt(fromH) + " holds to " + fmt(toH) : "keep " + fmt(fromH) + " holds");
    const gear = (name, from, to) => {
      if (to === from) return "";
      return (to > from ? ", gain " : ", lose ") + fmt(Math.abs(to - from)) + " " + name;
    };
    const deal = "Trade-in " + fmt(credit) + " cr"
      + (price == null ? "" : ", the new ship is " + fmt(price) + " cr")
      + ", net " + fmt(net) + " cr. ";
    const line = "Want to buy it? " + deal + money + " and " + holds + gear("fighters", fromF, toF) + gear("shields", fromS, toS) + ".";
    const m = $("menu");
    m.hidden = false;
    inComputer = false;
    m.dataset.screen = "Want to buy it?";
    m.innerHTML = '<div class="y">Want to buy it?</div><div data-yard="confirm">' + esc(line) + '</div>'
      + '<button type="button" id="dangerOk">Yes</button> <button type="button" id="dangerNo">No</button>';
    $("dangerOk").addEventListener("click", () => { m.hidden = true; act("buy_ship", args, "buy ship"); });
    $("dangerNo").addEventListener("click", () => { m.hidden = true; setResult("You leave with nothing.", false); });
  }
  function confirmWords(title, line, onYes) {
    const m = $("menu");
    m.hidden = false;
    inComputer = false;
    m.dataset.screen = title;
    m.innerHTML = '<div class="y">' + title + "</div><div>" + line + '</div><button type="button" id="dangerOk">' + (onYes ? "CONFIRM" : "OK") + '</button><br><span class="dk">Esc to close</span>';
    $("dangerOk").addEventListener("click", () => { m.hidden = true; if (onYes) onYes(); else setResult(line, true); });
    reveal(m);
  }
  function askWait() {
    const server = Number(state.waitStreak || 0);
    if (server >= 3) {
      confirmWords("Wait", "One more Wait ends your day (" + fmt(S.turns_remaining) + " turns left). Continue?", () => {
        waitStreak += 1;
        act("wait", {}, "wait one turn");
      });
      return;
    }
    waitStreak += 1;
    act("wait", {}, "wait one turn");
  }
  function scanAsk() {
    if (!legal("scan")) { setResult(plainReason((LA("scan") || {}).reason), true); return; }
    const tiers = ((((LA("scan") || {}).params || {}).tier || {}).choices) || [];
    if (tiers.length <= 1) return act("scan", tiers[0] ? { tier: tiers[0] } : {}, "scan");
    openForm("scan");
  }
  function landKey() {
    const planets = ((S.sector || {}).planets || []).slice();
    const terraHere = Number((S.sector || {}).id) === 1 || !!((S.sector || {}).terra);
    if (!planets.length && !terraHere) return;
    if (planets.length === 1 && !terraHere) {
      const p = planets[0];
      return confirmWords("Land", landLine(p), () => act("land_planet", { planet_id: p.id }, "land on " + p.name));
    }
    const m = $("menu");
    m.hidden = false;
    m.dataset.screen = "land";
    m.innerHTML = '<div class="y">Land</div>';
    planets.forEach((p) => {
      m.appendChild(button(esc(p.name || "planet"), () => {
        m.hidden = true;
        confirmWords("Land", landLine(p), () => act("land_planet", { planet_id: p.id }, "land on " + p.name));
      }));
    });
    if (terraHere) {
      const terra = LA("terra_colonists") || {};
      const b = button("Terra (1 turn, take or leave colonists)", () => {
        m.hidden = true;
        if (!terra.legal) { setResult(plainReason(terra.reason || "Terra colonists unavailable here"), true); return; }
        terraForm();
      });
      if (!terra.legal) b.disabled = true;
      m.appendChild(b);
    }
    reveal(m);
  }
  function traderRankings() {
    const rows = (S && S.trader_rankings) || [];
    const m = $("menu");
    m.hidden = false;
    m.dataset.screen = "rankings";
    let mode = "titles";
    const paint = () => {
      const head = '<div class="y">Trader Rankings</div><button type="button" id="rankToggle">'
        + (mode === "titles" ? "Values" : "Titles") + "</button>";
      const body = rows.map((row) => {
        const mid = mode === "titles" ? esc(row.title || "") : fmt(row.experience) + " experience";
        const corp = row.corp ? " [" + esc(row.corp) + "]" : "";
        return '<div class="row" data-rank-row="' + esc(String(row.rank)) + '">' + esc(String(row.rank)) + ". "
          + esc(row.name) + " — " + mid + corp + " " + esc(String(row.ship || "").replaceAll("_", " "))
          + (row.alive ? "" : " (dead)") + "</div>";
      }).join("") || '<div class="row">No traders listed.</div>';
      m.innerHTML = head + body + '<br><span class="dk">Esc to close</span>';
      const btn = $("rankToggle");
      if (btn) btn.addEventListener("click", () => { mode = mode === "titles" ? "values" : "titles"; paint(); });
    };
    paint();
  }
  function gameId() {
    return ((location.pathname || "").match(/\/g\/([^/]+)/) || [])[1] || "";
  }
  function showEndPanel(text) {
    const m = $("menu");
    if (!m || m.dataset.screen === "game-over") return;
    m.hidden = false;
    m.dataset.screen = "game-over";
    m.innerHTML = '<div class="y" data-game-over="panel">' + esc(text) + "</div>";
  }
  async function refreshCreator() {
    const gid = gameId();
    state.canEnd = false;
    state.gameName = "";
    if (!gid) return;
    try {
      const r = await fetch("/api/games/" + encodeURIComponent(gid) + "/creator", { credentials: "same-origin" });
      if (!r.ok) return;
      const data = await r.json();
      state.gameName = data.name || "";
      state.canEnd = !!(data.creator && data.status === "running" && data.seat && data.seat === state.seat);
    } catch (e) { state.canEnd = false; }
  }
  function askEndGame() {
    const gid = gameId();
    if (!gid || !state.canEnd) return;
    const name = state.gameName || "this game";
    confirmWords("End game for everyone", "End " + name + " for everyone? This stops the game.", () => {
      fetch("/games/" + encodeURIComponent(gid) + "/end", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirm: true }),
      }).then((r) => {
        if (!r.ok) throw new Error("The game did not end.");
        state.canEnd = false;
        return refresh();
      }).catch((e) => setResult(String(e.message || e), true));
    });
  }
  function menuHtml(which) {
    const list = which === "C" ? CKEYS : MENU_KEYS;
    const clockNote = TC
      ? '<div class="row">Under v3.11, turns come back a little at a time all day. The day rolls on the clock, not when everyone is out of turns.</div>'
      : "";
    const endRow = which === "?" && state.canEnd
      ? '<div class="row"><button type="button" id="endForEveryone" data-testid="end-for-everyone">End game for everyone</button></div>'
      : "";
    return '<div class="y">' + (which === "C" ? "Computer command" : "Main menu") + "</div>" + clockNote +
      list.map(([kk, l]) => '<div class="row"><kbd>&lt;' + kk + "&gt;</kbd> <span class=\"c\">" + l + "</span></div>").join("") +
      endRow + '<br><span class="dk">Esc to close</span>';
  }
  function wireEnd() {
    const btn = $("endForEveryone");
    if (btn) btn.addEventListener("click", askEndGame);
  }
  function key(k) {
    const m = $("menu");
    if (outOfTurns() && !["Escape", "?", "D", "C", "I", "V", "G", "Y", "Z"].includes(k)) { setResult(noTurnsLine(), true); return; }
    if (k === "Escape") {
      const menuOpen = !m.hidden;
      m.hidden = true; inComputer = false; openFormKind = null; formFocus = "";
      const slot = $("formSlot"); if (slot) slot.innerHTML = "";
      if (!menuOpen && mapEnlarged) toggleEnlarge(false);
      return;
    }
    if (state.busy && (k === "F" || k === "Q" || PLANET_KEYS.some((row) => row[0] === k))) {
      pendingPlanetKey = k;
      return;
    }
    if (k === "Enter") { if (courseCard || plotted) engage(); return; }
    if (inComputer) {
      inComputer = false;
      const c = CKEYS.find((x) => x[0] === k);
      if (!c) { m.hidden = true; setResult("That is not a computer command.", true); return; }
      if (k === "Q") { m.hidden = true; return; }
      if (k === "F") { m.hidden = true; askSector((n) => go(n)); return; }
      if (k === "R") return portReport();
      if (k === "K") return knownUniverse();
      if (k === "O") { m.hidden = true; return avoidForm(); }
      if (k === "L") return traderRankings();
      m.hidden = true;
      if (c[2]) return openForm(c[2]);
      return;
    }
    if (k === "?" || k === "C") {
      m.hidden = false;
      inComputer = k === "C";
      m.dataset.screen = k === "C" ? "computer" : "main";
      m.innerHTML = menuHtml(k);
      wireEnd();
      if (k === "?") {
        refreshCreator().then(() => {
          if (m.hidden || inComputer || m.dataset.screen !== "main") return;
          m.innerHTML = menuHtml("?");
          wireEnd();
        });
      }
      return;
    }
    if (onSurface() && (k === "Q" || PLANET_KEYS.some((row) => row[0] === k))) { planetKey(k); return; }
    if (onSurface() && SPACE_OFF.includes(k)) { setResult("Lift off first", true); return; }
    if (k === "D") { render(); return; }
    if (k === "I") { shipInfo(); return; }
    if (k === "Z") { rulesPanel(); return; }
    if (k === "V") return gameStatus();
    if (k === "Y") return readMail();
    if (k === "F" && !onSurface()) return fighterForm();
    if (k === "H" && !onSurface()) return mineForm();
    if (k === "G") return showFighters();
    if (k === "B" && onSurface()) return citadelForm();
    if (k === "B") {
      const gone = LA("self_destruct");
      if (!gone) return confirmWords("Self Destruct", "Self-destruct is not in this game. Your ship stays.");
      if (!gone.legal) return confirmWords("Self Destruct", plainReason(gone.reason));
      return confirmWords("Self Destruct", "You lose half your experience and half your alignment. The ship is gone. You are out for the rest of today and all of tomorrow.", () => act("self_destruct", {}, "self-destruct"));
    }
    if (k === "J") {
      const dump = LA("jettison");
      if (!dump) return confirmWords("Jettison Cargo", "Jettison is not in this game. Sell the cargo, or leave it on a planet.");
      if (!dump.legal) return setResult("Jettison Cargo: " + plainReason(dump.reason), true);
      return jettisonForm();
    }
    if (k === "Q") return confirmWords("Quit", "Quit is not in this game. You are still in the cockpit.");
    if (k === "T" && (S.corp || {}).ticker) return corpMenu();
    const hit = KEYS.find((x) => x[0] === k);
    if (!hit) return;
    if (hit[2] && !legal(hit[2])) {
      if (k === "P") {
        const stock = ((S.sector || {}).port || {}).stock || {};
        const lines = Object.entries(stock).map(([name, row]) => tradeWhy(name, row, S.ship || {}, row.side === "buys_from_player" ? "sell" : "buy")).filter(Boolean);
        setResult(lines.join(" ") || plainReason((LA("trade") || {}).reason), true);
        return;
      }
      const raw = (LA(hit[2]) || {}).reason || "";
      const nice = /answer the fighters first/i.test(raw) ? challengeLine() : plainWords(raw);
      if (/No Genesis torpedoes|No photon missiles|Buy a density scanner|Type how many|answer the fighters first/i.test(nice)) setResult(nice, true);
      else setResult(hit[1] + ": " + plainReason(raw), true);
      return;
    }
    if (k === "M") {
      const w = S.sector.warps_out || [];
      if (w.length === 1) return go(w[0]);
      askSector((n) => go(n));
      return;
    }
    if (k === "P") return openForm("trade");
    if (k === "L") return landKey();
    if (k === ".") return askWait();
    if (k === "S") return scanAsk();
    if (hit[2]) return openForm(hit[2]);
  }

  function flushPending() {
    if (!state.awaiting || state.busy || !pending) return;
    const job = pending;
    pending = null;
    act(job.kind, job.args, job.label);
  }
  function clearStaleWait() {
    const el = $("lastResult");
    if (!state.awaiting || pending || !el) return;
      if (/Waiting for your turn/.test(el.textContent || "")) setResult("Your move. Press " + (heldLabel || "the command") + " again.", false);
  }
  function eventFacts(ev) {
    return (ev && (ev.facts || ev.payload)) || {};
  }
  function fightCount(value) {
    return fmt(Number(String(value == null ? 0 : value).replace(/,/g, "")));
  }
  function fightSentence(ev) {
    const summary = String((ev && ev.summary) || "");
    const sent = /:\s*(.+?) sent ([\d,]+) fighters?, lost ([\d,]+);\s*(.+?) lost ([\d,]+) shields? and ([\d,]+) fighters?/i.exec(summary);
    const facts = eventFacts(ev);
    if (!sent && facts.exchange_kind !== "ship_vs_ship") return "";
    const youAttacked = facts.attacker === (S && S.self_id) || (ev.actor_id === (S && S.self_id) && facts.defender !== (S && S.self_id));
    const mineF = youAttacked ? (facts.attacker_losses != null ? facts.attacker_losses : (sent && sent[3])) : (facts.defender_losses != null ? facts.defender_losses : (sent && sent[6]));
    const mineS = youAttacked ? 0 : (sent ? sent[5] : (facts.shield_losses || 0));
    const theirName = ferrengiName(youAttacked ? (sent && sent[4]) : (sent && sent[1]));
    const theirF = youAttacked ? (facts.defender_losses != null ? facts.defender_losses : (sent && sent[6])) : (facts.attacker_losses != null ? facts.attacker_losses : (sent && sent[3]));
    const theirS = youAttacked ? (sent ? sent[5] : 0) : 0;
    if (mineF == null || !theirName) return "";
    const ship = (S && S.ship) || {};
    const leftF = youAttacked ? (facts.attacker_f != null ? facts.attacker_f : ship.fighters) : (facts.defender_f != null ? facts.defender_f : ship.fighters);
    const leftS = youAttacked ? (facts.attacker_s != null ? facts.attacker_s : ship.shields) : (facts.defender_s != null ? facts.defender_s : ship.shields);
    const countPhrase = (value, one, many) => {
      const num = Number(String(value == null ? 0 : value).replace(/,/g, ""));
      return fightCount(value) + " " + (Math.abs(num) === 1 ? one : many);
    };
    const leftNum = Number(String(leftF == null ? 0 : leftF).replace(/,/g, ""));
    const remain = fightCount(leftF) + (Math.abs(leftNum) === 1 ? " fighter remains" : " fighters remain");
    const theirs = theirName + " lost " + countPhrase(theirF, "fighter", "fighters") + " and " + countPhrase(theirS, "shield", "shields");
    if (youAttacked) return "You lost " + countPhrase(mineF, "fighter", "fighters") + " and " + countPhrase(mineS, "shield", "shields") + ", " + remain + ". " + theirs;
    const sector = ev.sector_id || ((/Combat in (\d+)/.exec(summary) || [])[1] || "");
    return theirName + " attacked you in " + sector + ": you lost " + countPhrase(mineF, "fighter", "fighters") + " and " + countPhrase(mineS, "shield", "shields") + " (" + countPhrase(leftF, "fighter", "fighters") + " and " + countPhrase(leftS, "shield", "shields") + " left). " + theirs;
  }
  function boardingSentence(ev) {
    const summary = String((ev && ev.summary) || "");
    const match = /\*\* Ferrengi Fighter Attack! \*\* (.+) boards (.+) in (\d+): flee, attack or surrender/i.exec(summary);
    if (!match) return "";
    const figs = eventFacts(ev).ferr_fighters;
    const count = figs == null ? "" : " (" + fmt(figs) + " fighters)";
    return "** Ferrengi Fighter Attack! ** " + ferrengiName(match[1]) + count + " boards " + match[2] + " in " + match[3] + ": flee, attack or surrender (surrender costs 5 cargo holds and all your cargo; with empty holds, 5 cargo holds and 10% of the credits on board)";
  }
  function tributePaid(ev) {
    const summary = String((ev && ev.summary) || "");
    const match = /^(.+?) surrendered tribute to (.+?):/.exec(summary);
    const who = match ? match[1] : "You";
    const ferr = ferrengiName(match ? match[2] : "the Ferrengi");
    const facts = eventFacts(ev);
    const bits = [];
    const cargo = facts.cargo;
    if (cargo && typeof cargo === "object") {
      Object.entries(cargo).forEach(([key, qty]) => {
        if (Number(qty) > 0) bits.push(fmt(qty) + " " + String(key).replaceAll("_", " "));
      });
    }
    const holds = Number(facts.holds_stolen || 0);
    const credits = Number(facts.credits || 0);
    if (holds) bits.push(fmt(holds) + (holds === 1 ? " cargo hold" : " cargo holds"));
    if (credits) bits.push(fmt(credits) + " cr");
    return who + " paid tribute to " + ferr + ": " + (bits.join(" and ") || "nothing") + ".";
  }
  function ignoredTributeLine(afterSeq) {
    let row = null;
    streamLog.concat((S && S.recent_events) || []).forEach((ev) => {
      if (!ev || ev.kind !== "ferrengi_tribute" || (ev.seq || 0) <= afterSeq) return;
      row = ev;
    });
    if (!row) return "";
    const paid = tributePaid(row);
    const ferr = (paid.match(/to (.+?):/) || [])[1] || "the Ferrengi";
    const took = paid.split(":").slice(1).join(":").replace(/\.\s*$/, "").trim();
    return "You ignored the " + ferr + ": it took " + (took || "tribute");
  }
  function destroyedExtra(afterSeq) {
    let line = "";
    streamLog.concat((S && S.recent_events) || []).forEach((row) => {
      if (!row || (row.seq || 0) <= afterSeq) return;
      const summary = String(row.summary || "");
      if (/ship destroyed/i.test(summary) && line.indexOf("ship destroyed") < 0) line = plainWords(summary);
      const lost = eventFacts(row).credits_lost;
      if (lost && line.indexOf("Credits on board lost") < 0) line += (line ? ". " : "") + "Credits on board lost: " + fmt(lost) + " cr";
    });
    return line;
  }
  function shipLossSides(afterSeq) {
    const sides = { mine: false, other: false };
    streamLog.concat((S && S.recent_events) || []).forEach((row) => {
      if (!row || (row.seq || 0) <= afterSeq || (row.kind !== "ship_destroyed" && row.kind !== "ship_captured")) return;
      const facts = eventFacts(row);
      const who = row.kind === "ship_captured" ? facts.former_owner : facts.victim;
      if (who && who === (S && S.self_id)) sides.mine = true;
      else if (who) sides.other = true;
    });
    return sides;
  }
  function showIncoming() {
    if (state.busy || !state.awaiting || !S) return;
    let best = null;
    streamLog.concat((S && S.recent_events) || []).forEach((row) => {
      if (!row || row.kind !== "combat" || (row.seq || 0) <= (state.seenFight || 0)) return;
      const facts = eventFacts(row);
      if (facts.defender === S.self_id && facts.attacker !== S.self_id && row.actor_id !== S.self_id && (!best || (row.seq || 0) >= best.seq)) best = row;
    });
    if (!best) return;
    state.seenFight = best.seq || 0;
    let line = fightSentence(best);
    const extra = destroyedExtra((best.seq || 1) - 1);
    if (extra && line.indexOf("ship destroyed") < 0) line = (line ? line + ". " : "") + extra;
    if (line) setResult(line, /ship destroyed/i.test(line));
  }
  async function act(kind, args, label) {
    taxFresh = false;
    dayNote = false;
    if (kind === "bank") { setResult("That command was not accepted.", true); return; }
    if (kind !== "wait") waitStreak = 0;
    if (state.busy || !state.awaiting) {
      if (outOfTurns()) { setResult(noTurnsLine(), true); return; }
      if (pending && pending.kind === kind && JSON.stringify(pending.args || {}) === JSON.stringify(args || {})) {
        setResult(capFirst((label || kind) + " will run when your turn comes."), true);
        return;
      }
      const dropped = pending ? (pending.label || pending.kind) : "";
      pending = { kind, args, label };
      heldLabel = label || kind;
      setResult(capFirst((label || kind) + " will run when your turn comes.") + (dropped ? " This replaces your queued " + dropped + "." : ""), true);
      return;
    }
    pending = null;
    state.busy = true;
    keys();
    const creditsBefore = S ? S.credits : 0;
    const turnsBefore = S ? S.turns_remaining : 0;
    try {
      const before = state.eventsSince;
      const avoidBefore = avoidedNames();
      let maxSeq = 0;
      streamLog.concat((S && S.recent_events) || []).forEach((row) => {
        if (!row || row.kind === "cockpit_note") return;
        if ((row.seq || 0) > maxSeq) maxSeq = row.seq || 0;
      });
      const resp = await api("/" + state.seat + "/action", { method: "POST", body: JSON.stringify({ turn_seq: state.turnSeq, action: { kind, args: args || {} } }) });
      state.awaiting = false;
      justActed = true;
      await refresh();
      let spent = Math.max(0, turnsBefore - (S ? S.turns_remaining : turnsBefore));
      let cameBack = 0;
      const gross = resp && resp.result ? resp.result.turns_spent : null;
      if (gross != null) {
        cameBack = Math.max(0, Number(gross) - spent);
        spent = Number(gross);
      }
      if (kind === "plot_course" && args && args.execute) {
        finishCourse(args, resp, spent);
        $("err").hidden = true;
        return;
      }
      const delta = (S ? S.credits : creditsBefore) - creditsBefore;
      const tail = ". Turns spent " + spent + (cameBack ? ", " + cameBack + " came back" : "") + ". Credits " + (delta >= 0 ? "+" : "") + fmt(delta) + ".";
      if (kind === "wait") {
        let line = "You wait" + tail;
        if (noticeSeq > before && noticeLine && line.indexOf(noticeLine) < 0) line += " " + noticeLine;
        const ignored = ignoredTributeLine(before - 1);
        if (ignored && line.indexOf(ignored) < 0) line += " " + ignored;
        setResult(withDawn(line), noticeSeq > before || !!ignored);
        $("err").hidden = true;
        return;
      }
      if (kind === "avoid") {
        const newer = latestAfter(maxSeq);
        const fresh = newer && newer.summary ? String(newer.summary) : "";
        if (/invalid sector|needs a sector/i.test(fresh)) {
          setResult(withDawn("REFUSED — there is no sector " + fmt((args || {}).sector) + tail), true);
          $("err").hidden = true;
          return;
        }
        const sentence = avoidSentence((args || {}).sector, avoidBefore).replace(/[.\s]+$/, "");
        rememberLine(sentence + ".");
        setResult(withDawn("ok — " + sentence + tail), false);
        $("err").hidden = true;
        return;
      }
      const ev = latestAfter(before - 1);
      const raw = ev && ev.summary ? String(ev.summary) : "";
      const counter = /counter (\d+)/i.exec(raw);
      const retry = { side: (args || {}).side, commodity: (args || {}).commodity, qty: (args || {}).qty };
      if (kind === "trade" && counter) {
        setResult("The port counters at " + fmt(counter[1]) + " cr. Enter that price, or try another" + tail, true);
        openForm("trade", Object.assign({}, retry, { unit_price: counter[1] }));
        $("err").hidden = true;
        return;
      }
      const bad = /invalid action|trade failed|lost patience|refused|cannot |not enough|insufficient/i.test(raw);
      const special = creditLine(kind, args, raw);
      let body = (special || plainWords(raw) || label || kind).replace(/[.\s]+$/, "");
      if (kind === "scan") {
        const rows = ((S && S.adjacent) || []).map((row) => {
          const bits = ["Sector " + row.id + " ==> " + fmt(row.density) + " Warps : " + fmt(row.warps) + " NavHaz : " + fmt(row.navhaz) + "% Anom : " + (row.anomaly ? "Yes" : "No")];
          const seen = row.seen || {};
          if (args && args.tier === "holo" && (seen.port || seen.traders || seen.planets || seen.fighters || seen.mines || (seen.ferrengi || []).length)) {
            if (seen.port) bits.push("Port " + (seen.port.name || "") + " " + (seen.port.code || ""));
            (seen.ferrengi || []).forEach((ship) => bits.push("Ships " + (ship.name || ship.id) + " " + fmt(ship.fighters) + " fighters"));
            (seen.traders || []).forEach((tr) => bits.push((tr.name || tr.id) + " " + fmt(tr.fighters) + " fighters"));
            if (seen.fighters) bits.push("Fighters " + fmt(seen.fighters.count) + " belong to " + traderName(seen.fighters.owner_id));
            (seen.mines || []).forEach((m) => bits.push((m.kind || "mines") + " " + fmt(m.count)));
            (seen.planets || []).forEach((pl) => bits.push("Planet " + (pl.name || pl.id)));
          }
          return bits.join(", ");
        });
        if (rows.length) body = body + ". " + rows.join("; ");
      }
      if (kind === "warp") {
        const seen = new Set();
        let mines = "";
        let lost = "";
        let avoid = "";
        let hit = false;
        streamLog.concat((S && S.recent_events) || []).forEach((row) => {
          if (!row || seen.has(row.seq)) return;
          if (row.seq) seen.add(row.seq);
          if ((row.seq || 0) <= before - 1) return;
          const facts = row.facts || {};
          if (row.kind === "mine_detonated") {
            mines = fmt(facts.hits || 0) + " mines hit for " + fmt(facts.damage || 0);
            hit = true;
          }
          if (row.kind === "combat" && (facts.vs === "fighter_sector" || facts.exchange_kind === "offensive_clash")) {
            hit = true;
            if (facts.attacker_losses != null) {
              const n = Number(facts.attacker_losses);
              lost = "You lost " + fmt(n) + " fighter" + (n === 1 ? "" : "s") + ", " + fmt(((S && S.ship) || {}).fighters || 0) + " remain";
            }
          }
          if (row.kind === "hazard_avoid_prompt") avoid = "Mines are in this sector. Computer, then O, adds it to the avoid list";
        });
        if (/adds it to the avoid list|avoid this sector/i.test(body)) {
          body = body
            .replace(/Mines are in this sector\. Computer, then O, adds it to the avoid list\.?/gi, "")
            .replace(/mines in sector \d+: avoid this sector\?\s*\(autopilot stops here\)\.?/gi, "")
            .replace(/^[.\s]+|[.\s]+$/g, "");
          if (!avoid) avoid = "Mines are in this sector. Computer, then O, adds it to the avoid list";
        }
        const bits = [body];
        if (hit) {
          if (mines) bits.push(mines);
          bits.push("Shields " + fmt(((S && S.ship) || {}).shields || 0));
          bits.push(lost || ("Fighters " + fmt(((S && S.ship) || {}).fighters || 0) + " remain"));
        }
        if (avoid) bits.push(avoid);
        const ferrengiChoices = /ferrengi/i.test(body) && /flee, attack or surrender/i.test(body);
        const challenge = ferrengiChoices ? "" : challengeLine();
        if (challenge) bits.push(challenge);
        body = bits.filter(Boolean).join(". ");
      }
      if (kind === "buy_ship" && args && args.trade_in === false) body = body + ". The new ship is in orbit. Press X to board it";
      if (kind === "attack") {
        let combat = null;
        streamLog.concat((S && S.recent_events) || []).forEach((row) => {
          if (row && row.kind === "combat" && (row.seq || 0) > before - 1 && (!combat || (row.seq || 0) >= combat.seq)) combat = row;
        });
        let mine = null;
        let back = null;
        streamLog.concat((S && S.recent_events) || []).forEach((row) => {
          if (!row || row.kind !== "combat" || (row.seq || 0) <= before - 1) return;
          const facts = eventFacts(row);
          if ((facts.attacker === S.self_id || row.actor_id === S.self_id) && (!mine || (row.seq || 0) >= mine.seq)) mine = row;
          if (facts.defender === S.self_id && facts.exchange_kind === "ferrengi_vs_ship" && (!back || (row.seq || 0) >= back.seq)) back = row;
        });
        const facts = eventFacts(mine || combat);
        if (back && mine) {
          const lost = Number((mine.facts || {}).attacker_losses || 0);
          const sent = (mine.facts || {}).sent != null ? Number(mine.facts.sent) : lost;
          const backFacts = back.facts || {};
          let who = ((((S && S.sector) || {}).ferrengi || []).find((ship) => ship.id === backFacts.attacker) || {}).name;
          if (!who) {
            const named = streamLog.concat((S && S.recent_events) || []).find((row) => {
              return row && (row.seq || 0) > before - 1 && /Ferrengi .+ attacks/i.test(row.summary || "");
            });
            const match = named && /Ferrengi (.+?) attacks/i.exec(named.summary || "");
            who = match && match[1];
          }
          body = body + ". You sent " + fmt(sent) + " and lost " + fmt(lost) + " fighter" + (lost === 1 ? "" : "s") + ". " + (who || "The Ferrengi") + " struck back: you lost " + fmt(backFacts.defender_losses || 0) + " fighters and " + fmt(backFacts.shield_losses || 0) + " shields";
        } else if ((facts.exchange_kind === "ship_vs_ship" || /shields and \d+ fighters/i.test((mine || combat || {}).summary || "")) && fightSentence(mine || combat)) {
          body = fightSentence(mine || combat);
          const extra = destroyedExtra(before - 1);
          if (extra && body.indexOf("ship destroyed") < 0) body += ". " + extra;
          if (mine && mine.seq) state.seenFight = Math.max(state.seenFight || 0, mine.seq);
        } else if (facts.attacker_losses != null) {
          const lost = Number(facts.attacker_losses);
          const remain = Number(((S && S.ship) || {}).fighters || 0);
          body = body + ". You lost " + fmt(lost) + " fighter" + (lost === 1 ? "" : "s") + ", " + fmt(remain) + " remain";
        }
      }
      if (kind === "land_planet") {
        let combat = null;
        streamLog.concat((S && S.recent_events) || []).forEach((row) => {
          const facts = (row && row.facts) || {};
          if (row && row.kind === "combat" && facts.vs === "planet" && (row.seq || 0) > before - 1) combat = row;
        });
        const facts = (combat && combat.facts) || {};
        if (facts.planet_fighters_lost != null && /repelled/i.test(raw)) body = siegeSentence(facts);
        else if (facts.planet_fighters_lost != null && /ship destroyed/i.test(body)) {
          body = body.replace(/[.\s]+$/, "") + ". " + capFirst(siegeLosses(facts));
        }
      }
      if (noticeSeq > before && noticeLine && body.indexOf(noticeLine) < 0) body += ". " + noticeLine;
      const boarded = streamLog.concat((S && S.recent_events) || []).map(boardingSentence).filter(Boolean).pop();
      if (boarded && /Ferrengi Fighter Attack/i.test(body)) body = body.replace(/\*\* Ferrengi Fighter Attack! \*\*[\s\S]*?flee, attack or surrender/i, boarded);
      const answered = kind === "retreat" || kind === "surrender" || kind === "hail" || kind === "broadcast" || kind === "radio";
      const ignored = answered ? "" : ignoredTributeLine(before - 1);
      if (ignored && body.indexOf("You ignored") < 0) body += ". " + ignored;
      const losers = shipLossSides(before - 1);
      if (/ship destroyed/i.test(body) && !/Credits on board lost/i.test(body) && (losers.mine || !losers.other)) {
        if (delta < 0) body += ". Credits on board lost: " + fmt(-delta) + " cr";
        else if (delta > 0) body += ". Credits on board lost: " + fmt(delta) + " cr";
      }
      if (/ship destroyed/i.test(body)) {
        const had = new Set(avoidIds(avoidBefore));
        avoidIds(avoidedNames()).filter((id) => !had.has(id)).forEach((id) => {
          const line = "Sector " + id + " is now on your avoid list";
          if (body.indexOf(line) < 0) body += ". " + line;
          rememberLine(line + ".");
        });
      }
      if (kind === "set_military_reaction" && args && args.pct != null) body = body + " to " + fmt(args.pct) + "%";
      if (kind === "assign_colonists" || kind === "load_planet_cargo" || kind === "dump_planet_cargo" || kind === "build_citadel") {
        const pid = Number((args && args.planet_id) || (S && S.planet_landed) || 0);
        const found = ((S && S.sector && S.sector.planets) || []).find((row) => Number(row.id) === pid)
          || ((S && S.owned_planets) || []).find((row) => Number(row.id) === pid);
        if (found) {
          const who = found.owner_id === S.self_id ? "yours" : (found.owner_id ? traderName(found.owner_id) : "unclaimed");
          let verb = body;
          if (kind === "assign_colonists") {
            verb = "moved " + fmt((args || {}).qty || 0) + " colonists " + String((args || {}).from || "").replaceAll("_", " ") + " -> " + String((args || {}).to || "").replaceAll("_", " ");
          }
          body = "Planet #" + found.id + " " + (found.name || "") + " (" + who + "): " + verb;
        }
      }
      if (kind === "liftoff") surface = false;
      if (kind === "land_planet" && /landed/i.test(body) && !/repelled/i.test(body)) {
        surface = true;
        surfaceTurn = state.turnSeq;
      }
      if (bad) {
        setResult(withDawn((/trade failed|lost patience/i.test(raw) ? "FAILED" : "REFUSED") + " — " + body + tail), true);
        if (kind === "trade") openForm("trade", retry);
      } else setResult(withDawn("ok — " + body + tail), false);
      $("err").hidden = true;
    } catch (e) {
      setResult("REFUSED — " + plainWords(e.message || e) + ". Turns spent 0.", true);
      $("err").hidden = false;
      $("err").textContent = String(e.message || e);
    } finally {
      state.busy = false;
      keys();
      if (state.awaiting && pending) flushPending();
      else clearStaleWait();
      paintAttackAlert();
      const follow = pendingPlanetKey;
      pendingPlanetKey = "";
      if (follow && surface) planetKey(follow);
    }
  }

  function clipEvents(list) {
    return (list || []).filter((ev) => {
      if (!ev || !S || ev.actor_id !== S.self_id) return true;
      if (ev.kind === "warp") {
        const f = ev.facts || {};
        const from = f.from != null ? Number(f.from) : Number(ev.sector_id);
        const to = f.to != null ? Number(f.to) : (f.target != null ? Number(f.target) : NaN);
        return to !== from;
      }
      if (ev.kind === "autopilot") {
        const f = ev.facts || {};
        return !!f.executed && Number(f.hops_done || 0) >= 1;
      }
      return true;
    });
  }
  function finishCourse(args, resp, spent) {
    const target = Number(args.target);
    const here = S ? Number(S.sector.id) : 0;
    let ev = null;
    streamLog.concat((S && S.recent_events) || []).forEach((row) => {
      if (!row || row.kind !== "autopilot" || row.actor_id !== (S && S.self_id)) return;
      if (!ev || (row.seq || 0) >= (ev.seq || 0)) ev = row;
    });
    const facts = (ev && ev.facts) || {};
    const hopsDone = Number(facts.hops_done || 0);
    const planned = Array.isArray(facts.path) && facts.path.length ? facts.path.length : (courseCard && Number(courseCard.target) === target ? Number(courseCard.hops) : hopsDone);
    const per = courseCard && courseCard.turns_per_hop ? Number(courseCard.turns_per_hop) : 0;
    const result = resp && resp.result;
    if (result && result.ok === false && hopsDone < 1) {
      setResult("REFUSED — " + plainWords(result.error || resp.reason || "refused"), true);
      return;
    }
    if (hopsDone >= 1 && here === target && (!planned || hopsDone >= planned)) {
      const used = per ? hopsDone * per : spent;
      setResult(withDawn("Autopilot: arrived at " + target + " (" + hopsDone + " hops, " + used + " turns)."), false);
      courseCard = null;
      mapSig = "";
      map();
      return;
    }
    const why = plainWords((result && result.error) || (ev && ev.summary) || "stopped");
    setResult("Autopilot stopped at " + here + " after " + hopsDone + " of " + planned + " hops: " + why, true);
    if (courseCard) {
      const rest = (courseCard.path || []).map(Number);
      const at = rest.indexOf(here);
      const left = at >= 0 ? rest.slice(at + 1) : rest;
      courseCard = Object.assign({}, courseCard, { from: here, path: left, hops: left.length, total_turns: left.length * Number(courseCard.turns_per_hop || 0) });
    }
    mapSig = "";
    map();
  }
  async function fetchEvents() {
    const r = await api("/" + state.seat + "/events?since=" + state.eventsSince + "&limit=100&course=1");
    if (state.mediaHistoryUntil == null) state.mediaHistoryUntil = typeof r.latest_seq === "number" ? r.latest_seq : 0;
    const catchingUp = !state.mediaCaughtUp && state.eventsSince < state.mediaHistoryUntil;
    const fresh = r.events || [];
    if (fresh.length) state.eventsSince = r.next_since;
    else state.mediaCaughtUp = true;
    noteCourse(fresh);
    if (S) { paintLog(); paintAttackAlert(); }
    if (fresh.some((ev) => ev.kind === "autopilot")) { mapSig = ""; map(); }
    const hist = catchingUp ? fresh.filter((ev) => ev.seq <= state.mediaHistoryUntil) : [];
    const live = catchingUp ? fresh.filter((ev) => ev.seq > state.mediaHistoryUntil) : fresh;
    const playedHull = await playWarpClips(live);
    if (window.TW2KMedia && fresh.length) {
      if (hist.length) window.TW2KMedia.onEvents(clipEvents(hist), S, { history: true });
      const liveMedia = clipEvents(live).filter((ev) => {
        if (!ev) return false;
        if (ev.kind === "warp_blocked" || ev.kind === "plot_course") return false;
        return true;
      });
      // The hull scene already played. The real-move events still go to onEvents
      // so a listener sees the batch. hullPlayed tells the player not to start warp.out as well.
      if (liveMedia.length) window.TW2KMedia.onEvents(liveMedia, S, playedHull ? { hullPlayed: true } : undefined);
    }
  }

  function paintAttackAlert() {
    if (!S) return;
    let best = null;
    streamLog.concat(S.recent_events || []).forEach((ev) => {
      if (!ev || ev.kind !== "combat" || ev.actor_id === S.self_id) return;
      const facts = ev.facts || {};
      if (facts.defender !== S.self_id && facts.victim !== S.self_id) return;
      if (!best || (ev.seq || 0) >= (best.seq || 0)) best = ev;
    });
    let ownSeq = 0;
    streamLog.concat(S.recent_events || []).forEach((ev) => {
      if (!ev || ev.kind !== "combat") return;
      const row = eventFacts(ev);
      if (row.attacker === S.self_id || ev.actor_id === S.self_id) ownSeq = Math.max(ownSeq, ev.seq || 0);
    });
    if (!best || (best.seq || 0) <= alertedSeq || (best.seq || 0) <= ownSeq) {
      let notice = null;
      streamLog.concat(S.recent_events || []).forEach((ev) => {
        if (!ev || (ev.seq || 0) <= alertedSeq) return;
        if (ev.kind === "mine_detonated" && ev.actor_id === S.self_id && (ev.facts || {}).victim && (ev.facts || {}).victim !== S.self_id) notice = ev;
        if (ev.kind === "land_planet" && (ev.facts || {}).former_owner === S.self_id) notice = ev;
        if (ev.kind === "combat" && (ev.facts || {}).defender_owner === S.self_id && ev.actor_id !== S.self_id) notice = ev;
      });
      if (!notice) return;
      rememberAlert(notice.seq);
      const facts = notice.facts || {};
      if (notice.kind === "mine_detonated") {
        noticeLine = "Your mines hit " + traderName(facts.victim) + " in sector " + (notice.sector_id || "") + " for " + fmt(facts.damage || 0) + " damage.";
        noticeSeq = notice.seq || 0;
        setResult(noticeLine, true);
      }
      else if (notice.kind === "combat" && facts.planet_fighters_lost != null) setResult(traderName(notice.actor_id) + " attacked " + (facts.planet_name || "your planet") + ": the planet lost " + fmt(facts.planet_fighters_lost) + " fighters and " + fmt(facts.planet_shields_lost || 0) + " shields.", true);
      else if (notice.kind === "combat") setResult("Your fighters fought in sector " + (notice.sector_id || "") + ".", true);
      else setResult("Someone landed on your planet" + (facts.seized ? " and took it." : "."), true);
      return;
    }
    rememberAlert(best.seq);
    const facts = eventFacts(best);
    const said = fightSentence(best);
    if (said && (facts.exchange_kind === "ship_vs_ship" || /shields and \d+ fighters/i.test(best.summary || ""))) {
      let line = said;
      const extra = destroyedExtra((best.seq || 1) - 1);
      if (extra && line.indexOf("ship destroyed") < 0) line += ". " + extra;
      setResult(line, /ship destroyed/i.test(line));
      if (best.seq) state.seenFight = Math.max(state.seenFight || 0, best.seq);
      return;
    }
    if (facts.shield_losses != null) {
      setResult(traderName(facts.attacker) + " attacked you in " + (best.sector_id || "") + ": you lost " + fmt(facts.shield_losses) + " shields, " + fmt(facts.defender_losses || 0) + " fighters (" + fmt(facts.defender_s || 0) + " shields left).", true);
    } else {
      const who = facts.attacker || "someone";
      const lost = facts.defender_losses;
      setResult("You were attacked by " + who + (lost == null ? "." : ". You lost " + lost + "."), true);
    }
  }
  function render() {
    if (S && S.planet_landed != null) {
      surface = true;
      surfaceTurn = state.turnSeq;
    } else if (state.awaiting && surface && state.turnSeq > surfaceTurn) surface = false;
    const dayNow = Number(S.day);
    if (seenDay != null && dayNow !== seenDay) {
      taxFresh = true;
      const tax = overnightTax();
      let fell = "";
      streamLog.concat(S.recent_events || []).forEach((ev) => {
        if (!ev || (ev.seq || 0) <= fellSeenSeq) return;
        if (/fell back/i.test(ev.summary || "")) { fell = plainWords(ev.summary); fellSeenSeq = ev.seq || fellSeenSeq; }
      });
      // NOTE 60 item 7: under the v3.11 clock no turns are refilled at the roll; they come back hourly.
      const roll = TC
        ? "Day " + dayNow + " dawns. Turns come back a little at a time; you have "
          + fmt(S.turns_remaining) + " of " + fmt(S.turns_per_day) + "."
        : "Day " + dayNow + ". Turns refilled to " + fmt(S.turns_remaining) + ".";
      const quiet = tax ? "" : (dayNow > 1 ? " Last night: no tax." : "");
      dawnLine = roll + (tax ? " " + tax : "") + quiet + (fell ? " " + fell : "");
      const prior = (($("lastResult") && $("lastResult").textContent) || "").trim();
      if (state.busy) {
        dayNote = true;
      } else if (justActed && prior && prior.indexOf(dawnLine) < 0) {
        setResult(prior + " " + dawnLine, false);
        dawnLine = "";
        justActed = false;
      } else {
        setResult(dawnLine, false);
        dawnLine = "";
        justActed = false;
      }
    }
    seenDay = dayNow;
    const sec = S.sector || {};
    $("pSector").textContent = sec.id ?? "-";
    $("tl").textContent = fmt(S.turns_remaining);
    $("turns").textContent = turnFace();
    paintClocks();
    $("credits").textContent = fmt(S.credits) + " cr";
    const over = state.gameOver || (Number(S.max_days) > 0 && Number(S.day) > Number(S.max_days));
    $("sbDay").textContent = String(over && Number(S.max_days) > 0 ? Math.min(Number(S.day), Number(S.max_days)) : S.day);
    $("xp").textContent = fmt(S.experience);
    $("maxDays").textContent = String(S.max_days);
    paintVerdict();
    $("nw").textContent = fmt(S.net_worth);
    $("rank").textContent = S.rank || "";
    const al = $("align");
    al.textContent = fmt(S.alignment) + " " + (S.alignment_label || "");
    al.className = S.alignment < 0 ? "r" : S.alignment > 0 ? "c" : "w";
    const chip = $("waitchip");
    chip.textContent = over ? "GAME OVER" : outOfTurns() ? "NO TURNS" : (state.awaiting ? "YOUR MOVE" : "WAITING");
    if (over && S.game_over_panel) showEndPanel(S.game_over_panel);
    chip.className = "chip" + (state.awaiting && !outOfTurns() && !over ? "" : " idle");
    document.querySelector("[data-testid=prompt-line]").textContent = "Command [TL=" + fmt(S.turns_remaining) + "] (?=Help) :";
    paintScene();
    paintLog();
    paintAttackAlert();
    sectorText();
    map();
    paintShip();
    here();
    keys();
  }

  async function refresh() {
    const st = await api("/" + state.seat + "/observation?wait_s=0&peek=1&format=both");
    state.awaiting = !!st.awaiting_input;
    if (state.holdAwait) state.awaiting = false;
    if (typeof st.wait_streak === "number") state.waitStreak = st.wait_streak;
    state.turnSeq = st.turn_seq ?? state.turnSeq;
    state.gameOver = !!st.game_over;
    CK = st.cockpit || null;
    TC = st.turn_clock || null;
    syncClocks();
    SC = st.starting_credits_line || "";
    TD = st.turns_per_day_line || "";
    syncSeatTimer(st);
    if (st.video_custom === true && window.TW2KMedia && window.TW2KMedia.setVideoCustom) window.TW2KMedia.setVideoCustom(true);
    const dayBefore = S ? Number(S.day) : null;
    if (st.observation) { S = st.observation; render(); }
    if (!state.busy && S && dayBefore != null && Number(S.day) === dayBefore) justActed = false;
    await fetchEvents();
    keys();
    if (!state.busy && state.awaiting && pending) flushPending();
    else if (!state.busy) clearStaleWait();
    showIncoming();
  }
  function rememberSeat() {
    if (!state.token) return;
    const gid = ((location.pathname || "").match(/\/g\/([^/]+)/) || [])[1] || "";
    if (!gid) return;
    try {
      const raw = localStorage.getItem("tw2k-my-seats");
      const rows = raw ? JSON.parse(raw) : [];
      const next = (Array.isArray(rows) ? rows : []).filter((r) => !(r && r.gid === gid && r.seat === state.seat));
      next.push({ gid: gid, seat: state.seat, token: state.token });
      localStorage.setItem("tw2k-my-seats", JSON.stringify(next));
    } catch (e) { /* this browser keeps no seat list */ }
  }
  async function connect() {
    state.seat = $("seatSelect").value.toUpperCase();
    state.token = $("tokenInput").value.trim();
    try { alertedSeq = Number(localStorage.getItem("tw2k-alert-" + state.seat) || 0); } catch (e) { alertedSeq = 0; }
    $("err").hidden = true;
    try {
      state.connected = true;
      await refresh();
      await refreshCreator();
      rememberSeat();
      const sign = document.querySelector(".sign-in");
      if (sign) sign.hidden = true;
    } catch (e) {
      state.connected = false;
      $("err").hidden = false;
      $("err").textContent = String(e.message || e);
    }
  }
  $("connectBtn").addEventListener("click", connect);
  const nwBtn = $("nwBtn");
  if (nwBtn) nwBtn.addEventListener("click", () => { if (S) netWorthPage(); });
  document.addEventListener("focusin", (ev) => {
    const t = ev.target;
    if (!t || t.tagName !== "INPUT") return;
    if (!t.closest || !t.closest(".frm")) return;
    const type = (t.type || "").toLowerCase();
    if (type !== "number" && type !== "text") return;
    try { t.select(); } catch (e) { /* a number input can refuse select in some browsers */ }
  });
  // Number inputs often ignore select(), so the first typed character would
  // append to the prefill (83 typed onto 83 became 8383). Replace it instead.
  document.addEventListener("keydown", (ev) => {
    const t = ev.target;
    if (!t || t.tagName !== "INPUT" || !t.closest || !t.closest(".frm")) return;
    if (t.dataset.touched || t.value === "") return;
    const type = (t.type || "").toLowerCase();
    if (type !== "number" && type !== "text") return;
    if (ev.key.length !== 1 || ev.ctrlKey || ev.metaKey || ev.altKey) return;
    t.value = "";
  }, true);
  document.addEventListener("input", markTouched, true);
  document.addEventListener("change", markTouched, true);
  document.addEventListener("keydown", (ev) => {
    const tag = (ev.target && ev.target.tagName) || "";
    if (ev.key === "Escape") { ev.preventDefault(); key("Escape"); return; }
    if (/^(INPUT|SELECT|TEXTAREA)$/.test(tag) || ev.ctrlKey || ev.metaKey || ev.altKey) return;
    if (ev.key === "Enter") { ev.preventDefault(); key("Enter"); return; }
    if (ev.key === "?") { ev.preventDefault(); key("?"); return; }
    if (ev.key === ".") { ev.preventDefault(); key("."); return; }
    if (ev.key.length === 1) { ev.preventDefault(); key(ev.key.toUpperCase()); }
  });
  window.__tw2kTest = {
    setAwaiting(flag) {
      state.awaiting = !!flag;
      state.holdAwait = !flag;
      if (flag) pending = null;
      if (S) render();
    },
    release() {
      state.holdAwait = false;
      state.awaiting = true;
      if (pending) flushPending();
    },
    serverWaits() { return Number(state.waitStreak || 0); },
    resetWaits() { waitStreak = 0; state.waitStreak = 0; },
    do(kind, args) { return act(kind, args || {}, kind); },
  };
  window.__tw2kWarp = {
    ready() { return !!(warpManifest && warpManifest.hulls && warpManifest.hulls.merchant_cruiser); },
    hulls() { return Object.keys((warpManifest && warpManifest.hulls) || {}); },
    pick(hull, rnd) { return chooseWarpClip(hull, rnd); },
    setList(hull, list) {
      if (!warpManifest) return false;
      if (!warpManifest.hulls) warpManifest.hulls = {};
      warpManifest.hulls[hull] = list;
      return true;
    },
    hold(ms) { return holdWarp(ms); },
    state() {
      const root = $("warpClip");
      return {
        plays: warpPlays,
        hidden: !root || root.hidden,
        hull: root ? root.getAttribute("data-hull") : "",
        clip: root ? root.getAttribute("data-clip") : "",
        kind: root ? root.getAttribute("data-kind") : "",
        motion: root ? root.getAttribute("data-motion") : "",
      };
    },
  };
  ensureWarpManifest();
  $("mapZoomIn").addEventListener("click", () => zoomMap(1.25));
  $("mapZoomOut").addEventListener("click", () => zoomMap(1 / 1.25));
  $("mapCenter").addEventListener("click", () => { mapView.x = 0; mapView.y = 0; applyMapView(); });
  $("mapEnlarge").addEventListener("click", () => toggleEnlarge());
  if (window.ResizeObserver) {
    let mapBox = "";
    new ResizeObserver(() => {
      const rect = $("map").getBoundingClientRect();
      const box = Math.round(rect.width) + "x" + Math.round(rect.height);
      if (!box || box === mapBox) return;
      mapBox = box;
      mapSig = "";
      if (S) map();
    }).observe($("map"));
  }
  if (state.token || params.get("mode") === "cu") connect();
  setInterval(() => { if (state.connected && !state.busy) refresh().catch((e) => { $("err").hidden = false; $("err").textContent = String(e.message || e); }); }, 2000);
  setInterval(() => { if (S) paintClocks(); }, 1000);
})();
