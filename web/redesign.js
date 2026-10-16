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
    ["V", "Game Status"], ["G", "Show Deployed Fighters"], ["B", "Self Destruct"],
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
  const SHIPS = {
    escape_pod: { name: "Escape Pod", len: 60, w: 40, pods: 0, eng: 1 },
    merchant_cruiser: { name: "Merchant Cruiser", len: 190, w: 70, pods: 2, eng: 2 },
    scout_marauder: { name: "Scout Marauder", len: 150, w: 44, pods: 0, eng: 2 },
    missile_frigate: { name: "Missile Frigate", len: 200, w: 60, pods: 1, eng: 2 },
    battleship: { name: "BattleShip", len: 250, w: 96, pods: 2, eng: 3 },
    corporate_flagship: { name: "Corporate FlagShip", len: 260, w: 100, pods: 3, eng: 3 },
    colonial_transport: { name: "Colonial Transport", len: 240, w: 110, pods: 5, eng: 2 },
    cargotran: { name: "CargoTran", len: 240, w: 110, pods: 6, eng: 2 },
    merchant_freighter: { name: "Merchant Freighter", len: 220, w: 96, pods: 4, eng: 2 },
    imperial_starship: { name: "Imperial StarShip", len: 290, w: 110, pods: 3, eng: 4 },
    havoc_gunstar: { name: "Havoc GunStar", len: 200, w: 90, pods: 1, eng: 3 },
    interdictor_cruiser: { name: "Interdictor Cruiser", len: 280, w: 120, pods: 4, eng: 4 },
  };
  const params = new URLSearchParams(location.search);
  const state = {
    seat: (params.get("seat") || "P2").toUpperCase(),
    token: params.get("token") || "",
    connected: false, awaiting: false, busy: false, turnSeq: 0,
    eventsSince: 0, mediaHistoryUntil: null, mediaCaughtUp: false,
  };
  let S = null, plotted = null, courseEvent = null, ignorePlotSeq = 0, mapSig = "", inComputer = false, sceneTable = null, openFormKind = null, formFocus = "", pending = null, heldLabel = "", waitStreak = 0, alertedSeq = 0;
  function rememberAlert(seq) {
    alertedSeq = seq;
    try { localStorage.setItem("tw2k-alert-" + (state.seat || ""), String(seq)); } catch (e) { /* keep the page count */ }
  }
  const streamLog = [];
  const streamSeen = new Set();
  const tokenKey = "tw2k-token-" + state.seat;
  if (params.get("token")) {
    try { sessionStorage.setItem(tokenKey, params.get("token")); } catch (e) { /* the address still has it this once */ }
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
      if (!ev || (ev.seq || 0) <= seq) return;
      if (!best || (ev.seq || 0) >= (best.seq || 0)) best = ev;
    });
    return best;
  }
  function plainEvent(ev) {
    const facts = (ev && ev.facts) || {};
    if (ev && ev.kind === "combat" && facts.vs === "planet" && facts.planet_fighters_lost != null) return siegeSentence(facts);
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
      const d = document.createElement("div");
      d.dataset.seq = String(ev.seq || 0);
      d.textContent = plainEvent(ev);
      box.appendChild(d);
    });
    box.scrollTop = 0;
  }
  function setResult(text, bad) {
    const el = $("lastResult");
    el.textContent = text || "";
    el.className = bad ? "bad" : "";
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

  function shipSvg(sh, d) {
    const cx = 200, cy = 135, L = d.len, W = d.w, x0 = cx - L / 2, x1 = cx + L / 2;
    let g = "";
    const sp = sh.shield_cap ? sh.shields / sh.shield_cap : 0;
    if (sp > 0) g += '<ellipse cx="' + cx + '" cy="' + cy + '" rx="' + (L / 2 + 28) + '" ry="' + (W / 2 + 40) + '" fill="none" stroke="#55ffff" stroke-width="' + (1 + sp * 3) + '" opacity="' + (0.25 + sp * 0.6) + '" stroke-dasharray="6 4"/>';
    const n = sh.fighters ? Math.min(48, Math.round(Math.log10(sh.fighters + 1) * 10)) : 0;
    let seed = sh.fighters || 1;
    const rnd = () => (seed = (seed * 9301 + 49297) % 233280) / 233280;
    for (let i = 0; i < n; i++) {
      const a = rnd() * 6.283, rad = L / 2 + 36 + rnd() * 22;
      g += '<path d="M0,-3 L2.5,3 L-2.5,3Z" fill="#ff5555" transform="translate(' + (cx + Math.cos(a) * rad) + "," + (cy + Math.sin(a) * rad * 0.55) + ") rotate(" + (a * 57) + ')" opacity=".85"/>';
    }
    const tw = sh.transwarp && sh.transwarp.fitted;
    for (let i = 0; i < d.eng; i++) {
      const y = cy - W / 3 + (i + 0.5) * (W * 0.66 / d.eng);
      g += '<rect x="' + (x0 - 14) + '" y="' + (y - 5) + '" width="16" height="10" fill="#555"/><rect x="' + (x0 - 28) + '" y="' + (y - 3) + '" width="14" height="6" fill="' + (tw ? "#ff55ff" : "#55ffff") + '"/>';
    }
    g += '<path d="M' + x0 + "," + (cy - W / 2) + " L" + (x1 - W * 0.6) + "," + (cy - W / 2) + " L" + x1 + "," + cy + " L" + (x1 - W * 0.6) + "," + (cy + W / 2) + " L" + x0 + "," + (cy + W / 2) + ' Z" fill="#0b0b2a" stroke="#5555ff" stroke-width="2"/>';
    const holds = Math.min(sh.holds || 0, 80);
    const cols = Math.max(1, Math.ceil(holds / (W > 80 ? 6 : 4)));
    const rows = Math.max(1, Math.ceil(holds / cols));
    const gw = (L - W * 0.6 - 20) / cols, gh = (W - 14) / rows;
    const fill = [];
    Object.entries(sh.cargo || {}).forEach(([k, v]) => { for (let i = 0; i < v && fill.length < holds; i++) fill.push((COM[k] || ["", "#111"])[1]); });
    for (let i = 0; i < holds; i++) {
      const c = i % cols, rr = Math.floor(i / cols);
      g += '<rect x="' + (x0 + 10 + c * gw) + '" y="' + (cy - W / 2 + 7 + rr * gh) + '" width="' + (gw - 1.5) + '" height="' + (gh - 1.5) + '" fill="' + (fill[i] || "#111") + '"/>';
    }
    if (sh.scanner) g += '<path d="M' + cx + "," + (cy - W / 2) + " l-12,-18 a14,14 0 0 0 24,0 z" + '" fill="#00aa00" stroke="#55ff55"/>';
    return g;
  }
  function fighterPips(have, cap) {
    const n = 12;
    let on = cap > 0 ? Math.round(n * Math.min(1, have / cap)) : 0;
    if (have > 0 && on < 1) on = 1;
    let html = "";
    for (let i = 0; i < n; i++) html += '<i class="' + (i < on ? "on" : "") + '"></i>';
    $("fighterRow").innerHTML = html;
  }

  const known = (id) => !!((S.known_warps || {})[id] || (S.known_warps || {})[String(id)]);
  function outOfTurns() {
    return !!(S && Number(S.turns_remaining) <= 0);
  }
  function noTurnsLine() {
    return "No turns left today. Day " + (Number(S.day) + 1) + " starts when the other traders finish.";
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
  let dayNote = false;
  function shipsHere() {
    const s = (S && S.sector) || {};
    const rows = [];
    (s.ferrengi || []).forEach((f) => rows.push({ id: f.id, name: f.name, owner: "Ferrengi", fighters: f.fighters }));
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
    let line = "";
    if (before > 0) line += "planet shields " + fmt(before) + " -> " + fmt(after) + ", ";
    line += "reaction and defending fighters killed " + fmt(facts.planet_fighters_lost || 0) + "; you lost " + fmt(facts.attacker_losses || 0) + " fighters, " + fmt(remain) + " remain";
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
  function shipChoiceLabel(id) {
    const ship = shipsHere().find((row) => String(row.id) === String(id));
    if (ship) return ship.name + ", " + ship.owner + (ship.fighters == null ? "" : ", " + fmt(ship.fighters) + " fighters");
    const roster = ((S && S.other_players) || []).find((row) => row.id === id);
    if (roster) {
      const bits = [roster.name || id];
      if (roster.ship_class) bits.push(hullPhrase(roster.ship_class));
      if (roster.fighters != null) bits.push(fmt(roster.fighters) + " fighters");
      if (roster.shields != null) bits.push(fmt(roster.shields) + " shields");
      return bits.join(", ");
    }
    return String(id).replaceAll("_", " ");
  }
  function overnightTax() {
    let best = null;
    streamLog.concat((S && S.recent_events) || []).forEach((ev) => {
      if (!ev || ev.kind !== "tax_collected") return;
      if (ev.actor_id && S && ev.actor_id !== S.self_id) return;
      if (!best || (ev.seq || 0) >= (best.seq || 0)) best = ev;
    });
    if (!best) return "";
    const facts = best.facts || {};
    if (facts.tax == null) return "";
    if ((best.seq || 0) !== taxSeenSeq) {
      taxSeenSeq = best.seq || 0;
      taxFresh = true;
    }
    if (!taxFresh) return "";
    return "Overnight Federation tax " + fmt(facts.tax) + " cr, alignment +" + fmt(facts.align_gain || 0) + ".";
  }
  function lastTaxLine() {
    let best = null;
    streamLog.concat((S && S.recent_events) || []).forEach((ev) => {
      if (!ev || ev.kind !== "tax_collected") return;
      if (ev.actor_id && S && ev.actor_id !== S.self_id) return;
      if (!best || (ev.seq || 0) >= (best.seq || 0)) best = ev;
    });
    const facts = (best && best.facts) || {};
    if (facts.tax == null) return "";
    return "Overnight Federation tax " + fmt(facts.tax) + " cr, alignment +" + fmt(facts.align_gain || 0) + ".";
  }
  function sectorText() {
    const s = S.sector;
    const landed = landedPlanet();
    let t = '<span class="g">Sector  </span><span class="y">:</span> <span class="c">' + s.id + "</span> <span class=\"g\">in</span> <span class=\"c\">" + (s.is_fedspace ? "The Federation" : "uncharted space") + ".</span>\n";
    if (s.port) t += '<span class="g">Ports   </span><span class="y">:</span> <span class="c">' + esc(s.port.name) + '</span><span class="y">,</span> <span class="g">Class</span> <span class="c">' + s.port.class_id + '</span> <span class="w">(</span><span class="m">' + esc(s.port.code) + "</span><span class=\"w\">)</span>\n";
    (s.planets || []).forEach((p) => { t += '<span class="g">Planets </span><span class="y">:</span> <span class="c">' + esc(p.name) + "</span>\n"; });
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
  function map() {
    syncPlot();
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
    let html = "";
    const seen = new Set();
    Object.entries(warps).forEach(([from, tos]) => (tos || []).forEach((to) => {
      const a = Number(from), b = Number(to);
      if (!pos[a] || !pos[b]) return;
      const key = [a, b].sort().join();
      if (seen.has(key)) return;
      seen.add(key);
      html += '<line class="lane" x1="' + pos[a][0] + '" y1="' + pos[a][1] + '" x2="' + pos[b][0] + '" y2="' + pos[b][1] + '"/>';
    }));
    (S.sector.warps_out || []).forEach((w) => {
      const b = Number(w);
      if (!pos[hereId] || !pos[b]) return;
      const key = [hereId, b].sort().join();
      if (seen.has(key)) return;
      seen.add(key);
      const unk = known[b] && known[b].unexplored;
      html += '<line class="lane' + (unk ? " unk" : "") + (oneWay(b) ? " oneway" : "") + '" x1="0" y1="0" x2="' + pos[b][0] + '" y2="' + pos[b][1] + '"/>';
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
      let lx = at[0] + 12, ly = at[1] + 4;
      for (let n = 0; n < 6 && labels.some((p) => Math.hypot(p[0] - lx, p[1] - ly) < 18); n++) ly += 16;
      labels.push([lx, ly]);
      const adj = (S.sector.warps_out || []).map(Number).includes(id);
      const cls = ["node", id === hereId ? "here" : "", adj ? "adj" : "", k.unexplored ? "unk" : "", k.port ? "port" : "", plotted && plotted.target === id ? "tgt" : ""].join(" ");
      html += '<g class="' + cls + '" data-id="' + id + '"><circle cx="' + at[0] + '" cy="' + at[1] + '" r="' + (id === hereId ? 11 : adj ? 9 : 6) + '"/><text x="' + lx + '" y="' + ly + '">' + id + "</text></g>";
    });
    svg.innerHTML = html;
    svg.setAttribute("data-route", serverPath.join(","));
    svg.querySelectorAll(".node").forEach((n) => n.addEventListener("click", () => go(+n.dataset.id)));
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
    if (plotted && path.length > 1) {
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
    if (!S || Number(id) === Number(S.sector.id)) return;
    if ((S.sector.warps_out || []).map(Number).includes(Number(id))) {
      if (S.planet_landed != null) { setResult("Lift off first", true); return; }
      return act("warp", { target: id }, "warp to " + id);
    }
    act("plot_course", { target: id, execute: false }, "plot course to " + id);
  }
  function engage() {
    if (!plotted) return;
    if (S && S.planet_landed != null) { setResult("Lift off first", true); return; }
    const hopCost = Number((((LA("plot_course") || {}).params || {}).execute || {}).first_hop_turns || 0);
    const left = Number((S && S.turns_remaining) || 0);
    if (hopCost > left) { setResult("REFUSED — first hop unaffordable (need " + hopCost + " turns, have " + left + ").", true); return; }
    act("plot_course", { target: plotted.target, execute: true }, "engage course to " + plotted.target);
  }

  function paintShip() {
    const sh = S.ship || {};
    const def = SHIPS[sh.class] || { name: String(sh.class || "ship").replaceAll("_", " "), len: 200, w: 80, pods: 2, eng: 2 };
    $("shipName").textContent = def.name.toUpperCase();
    $("shipCls").textContent = String(sh.class || "ship").replaceAll("_", " ");
    $("shipSvg").innerHTML = shipSvg(sh, def);
    fighterPips(sh.fighters || 0, sh.fighter_cap || 0);
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
  function button(label, fn, extra) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "verb";
    b.innerHTML = label;
    if (extra) Object.assign(b, extra);
    b.addEventListener("click", fn);
    return b;
  }
  function here() {
    const saved = {};
    const restore = openFormKind;
    if (restore) {
      const active = document.activeElement;
      if (active && active.dataset && active.dataset.n) formFocus = active.dataset.n;
      document.querySelectorAll("#formSlot [data-n]").forEach((el) => {
        saved[el.dataset.n] = el.dataset.t === "bool" ? el.checked : el.value;
      });
    }
    const box = $("here");
    box.innerHTML = "";
    const s = S.sector, sh = S.ship || {};
    const landed = landedPlanet();
    if (landed) {
      const card = document.createElement("div");
      card.className = "planet";
      const owner = landed.owner_id === S.self_id ? (S.self_name || "you")
        : (((S.other_players || []).find((r) => r.id === landed.owner_id) || {}).name || (landed.owner_id || "unowned"));
      let body = '<div class="y">' + esc(landed.name || "planet") + "</div>";
      body += '<div>Class <span class="c">' + esc(landed.class || "?") + '</span>  Owner <span class="c">' + esc(owner) + "</span></div>";
      const building = landed.citadel_target && Number(landed.citadel_target) > Number(landed.citadel_level || 0);
      body += '<div>Citadel <span class="c">' + (building ? "building toward " + landed.citadel_target : "level " + (landed.citadel_level || 0)) + "</span>";
      if (building && landed.citadel_complete_day) body += '  ready day <span class="y">' + landed.citadel_complete_day + "</span>";
      body += '  Fighters <span class="c">' + fmt(landed.fighters || 0) + '</span>  Shields <span class="c">' + fmt(landed.shields || 0) + "</span></div>";
      ["fuel_ore", "organics", "equipment"].forEach((k) => {
        const meta = COM[k] || [k, "#fff"];
        const cols = (landed.colonists || {})[k] || 0;
        const stock = (landed.stockpile || {})[k] || 0;
        const made = landed.production ? (landed.production[k] || 0) : null;
        body += '<div style="color:' + meta[1] + '">' + esc(meta[0]) + '</div><div class="c">Colonists ' + fmt(cols) + "  On planet " + fmt(stock) + (made == null ? "" : "  " + fmt(made) + " per day") + "</div>";
      });
      body += '<div data-quasar="now">Quasar sector ' + (landed.quasar_sector_pct || 0) + "%, atmosphere " + (landed.quasar_atm_pct || 0) + "%</div>";
      body += '<div data-reaction="pct">Military reaction ' + fmt(landed.military_reaction_pct || 0) + "%</div>";
      if (landed.treasury != null) body += '<div data-treasury="balance">Treasury ' + fmt(landed.treasury) + " cr</div>";
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
      table.innerHTML = "<tr><th>Items</th><th>Status</th><th>Trading</th><th>Price</th><th>OnBoard</th><th></th></tr>";
      Object.entries(stockRows).forEach(([k, v]) => {
        const meta = COM[k] || [k, "#fff"];
        const side = v.side === "buys_from_player" ? "sell" : "buy";
        const mx = maxBy("trade", k, side);
        const room = Math.max(0, Number(v.max || 0) - Number(v.current || 0));
        const trading = side === "sell" ? room : Number(v.current || 0);
        const status = side === "sell" ? "Buying, room " + fmt(room) : "Selling " + fmt(v.current) + "/" + fmt(v.max);
        const tr = document.createElement("tr");
        tr.innerHTML = "<td style=\"color:" + meta[1] + "\">" + esc(meta[0]) + "</td><td>" + status + "</td><td class=\"c\">" + fmt(trading) + "</td><td class=\"y\">" + (v.price ?? "") + "</td><td class=\"w\">" + (sh.cargo[k] || 0) + "</td><td></td>";
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
          if (tr.children[3]) tr.children[3].classList.add("dim");
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
      if (legal("buy_equip")) box.appendChild(button("StarDock: buy gear", () => openForm("buy_equip")));
      box.appendChild(button("Load colonists (Terra)", () => terraForm()));
      if (legal("buy_ship")) box.appendChild(button("Shipyards", () => openForm("buy_ship")));
      if (legal("bank_deposit") || legal("bank_withdraw")) box.appendChild(button("Bank", () => bankForm()));
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
      if (Array.isArray(spec.choices)) {
        input = document.createElement("select");
        spec.choices.forEach((choice) => {
          const o = document.createElement("option");
          o.value = typeof choice === "object" ? (choice.id ?? "") : choice;
          o.textContent = kind === "attack" && name === "target" ? shipChoiceLabel(String(o.value))
            : (kind === "buy_equip" && name === "item" ? gearName(o.value)
            : (kind === "ship_transport" && name === "ship_id" ? shipTransportLabel(o.value) : o.value));
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
      if (kind === "launch_beacon" && !String(args.message || "").trim()) { setResult("Type a beacon message first.", true); return; }
      if (kind === "buy_equip" && args.qty == null) { setResult("How many? Type a number.", true); return; }
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
    wrap.addEventListener("keydown", (ev) => {
      if (ev.key !== "Enter") return;
      ev.preventDefault();
      ev.stopPropagation();
      submit();
    });
    if (kind === "trade") {
      const listed = ((a.params.unit_price || {}).listed_by) || {};
      const sideEl = fields.find((el) => el.dataset.n === "side");
      const comEl = fields.find((el) => el.dataset.n === "commodity");
      const priceEl = fields.find((el) => el.dataset.n === "unit_price");
      const pair = () => {
        const side = sideEl && sideEl.value;
        const com = comEl && comEl.value;
        const direct = (listed[com] || {})[side];
        if (direct) return [side, com, direct];
        for (const [name, sides] of Object.entries(listed)) {
          if (sides && sides[side]) return [side, name, sides[side]];
        }
        for (const [name, sides] of Object.entries(listed)) {
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
      const paint = () => {
        const key = item ? item.value : "";
        const hull = HULL[key] || {};
        const name = (SHIPS[key] && SHIPS[key].name) || String(key).replaceAll("_", " ");
        const net = nets[key];
        const full = spare[key];
        const trading = !deal || deal.checked;
        const price = trading ? net : full;
        const gear = (hull.photons ? "photons" : "no photons") + ", " + (hull.tw ? "TransWarp" : "no TransWarp");
        note.textContent = name + ": " + (price == null ? "" : fmt(price) + " cr. ")
          + "Holds " + fmt(hull.holds || 0) + ", fighters " + fmt(hull.fighters || 0) + ", shields " + fmt(hull.shields || 0)
          + ", " + (hull.tpw || "?") + " turns per warp, " + gear + ". "
          + (trading ? "Trade-in sells your ship" + (credit ? " for " + fmt(credit) + " cr" : "") + " and you fly the new one."
            : "You stay aboard. The new ship waits at StarDock.");
      };
      if (item) item.addEventListener("change", paint);
      if (deal) deal.addEventListener("change", paint);
      paint();
      wrap.appendChild(note);
    }
    slot.appendChild(wrap);
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
  function reasonButton(kind, label, onLegal) {
    const a = LA(kind) || { legal: false, reason: kind + " is not available" };
    const b = document.createElement("button");
    b.type = "button";
    b.className = "verb";
    b.dataset.kind = kind;
    if (!a.legal) b.classList.add("dim");
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
    wrap.addEventListener("keydown", (ev) => { if (ev.key !== "Enter") return; ev.preventDefault(); ev.stopPropagation(); submit(); });
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
    wrap.addEventListener("keydown", (ev) => { if (ev.key !== "Enter") return; ev.preventDefault(); ev.stopPropagation(); submit(); });
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
    wrap.addEventListener("keydown", (ev) => { if (ev.key !== "Enter") return; ev.preventDefault(); ev.stopPropagation(); submit(); });
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
      if (leave.value === "" || !Number.isFinite(want) || want < 0) { setResult("Type how many to leave.", true); return; }
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
    wrap.addEventListener("keydown", (ev) => {
      if (ev.key !== "Enter") return;
      ev.preventDefault();
      ev.stopPropagation();
      submit();
    });
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
        if (!n) { setResult("How many? Type a number.", true); return; }
        openFormKind = null;
        slot.innerHTML = "";
        act("deploy_mines", { kind: kind.value, qty: n }, "deploy mines");
      };
      wrap.appendChild(button("CONFIRM", submit));
      wrap.addEventListener("keydown", (ev) => {
        if (ev.key !== "Enter") return;
        ev.preventDefault();
        ev.stopPropagation();
        submit();
      });
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
        if (!n) { setResult("How many? Type a number.", true); return; }
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
        if (!n) { setResult("How many? Type a number.", true); return; }
        openFormKind = null;
        slot.innerHTML = "";
        act("terra_colonists", { mode: mode.value, qty: n }, mode.value + " colonists");
      };
      wrap.appendChild(button("CONFIRM", submit));
      wrap.addEventListener("keydown", (ev) => { if (ev.key !== "Enter") return; ev.preventDefault(); ev.stopPropagation(); submit(); });
      qty.focus();
      qty.select();
    }
    wrap.appendChild(button("ESC", () => { openFormKind = null; slot.innerHTML = ""; }));
    slot.appendChild(wrap);
  }
  function bankForm(saved) {
    const dep = LA("bank_deposit") || { params: {}, legal: false, reason: "" };
    const wd = LA("bank_withdraw") || { params: {}, legal: false, reason: "" };
    const slot = $("formSlot");
    if (!slot) return;
    openFormKind = "bank";
    const balance = Number((dep.params || {}).balance || (wd.params || {}).balance || (S && S.bank_balance) || 0);
    const room = Number((dep.params || {}).room || 0);
    const depMax = Number((dep.params || {}).max_amount || 0);
    const wdMax = Number((wd.params || {}).max_amount || 0);
    slot.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "frm";
    wrap.dataset.screen = "bank";
    wrap.innerHTML = '<div class="y">BANK</div><div class="c">Balance ' + fmt(balance) + " cr. Room " + fmt(room) + " cr.</div>";
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
    const fill = () => { amount.value = side.value === "withdraw" ? wdMax : depMax; };
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
    const submit = () => {
      const n = Number(amount.value);
      if (!n) { setResult("Type an amount.", true); return; }
      const which = side.value === "withdraw" ? wd : dep;
      if (!which.legal) { setResult(plainReason(which.reason), true); return; }
      openFormKind = null;
      slot.innerHTML = "";
      act(side.value === "withdraw" ? "bank_withdraw" : "bank_deposit", { amount: n }, side.value);
    };
    wrap.appendChild(button("CONFIRM", submit));
    wrap.appendChild(button("ESC", () => { openFormKind = null; slot.innerHTML = ""; }));
    wrap.addEventListener("keydown", (ev) => {
      if (ev.key !== "Enter") return;
      ev.preventDefault();
      ev.stopPropagation();
      submit();
    });
    slot.appendChild(wrap);
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
    wrap.innerHTML = '<div class="y">TREASURY</div><div class="c" data-treasury="form">Treasury ' + fmt(planet.treasury || 0) + " cr.</div>";
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
    wrap.addEventListener("keydown", (ev) => { if (ev.key !== "Enter") return; ev.preventDefault(); ev.stopPropagation(); submit(); });
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
      openFormKind = null;
      slot.innerHTML = "";
      act(pick.value, { planet_id: planet.id, pct: Number(pct.value) }, "set quasar");
    };
    wrap.appendChild(button("CONFIRM", submit));
    wrap.appendChild(button("ESC", () => { openFormKind = null; slot.innerHTML = ""; }));
    wrap.addEventListener("keydown", (ev) => { if (ev.key !== "Enter") return; ev.preventDefault(); ev.stopPropagation(); submit(); });
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
    wrap.addEventListener("keydown", (ev) => { if (ev.key !== "Enter") return; ev.preventDefault(); ev.stopPropagation(); submit(); });
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
      + row("Holds", fmt(sh.holds))
      + row("Fighters", fmt(sh.fighters))
      + row("Shields", fmt(sh.shields))
      + row("Turns per warp", hop === "" ? "" : String(hop))
      + '<div class="y">Gear</div>'
      + gear.map(([label, n]) => row(label, n)).join("")
      + '<br><span class="dk">Esc to close</span>';
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
      if (gap > 0) gaps.push(name + " " + fmt(gap) + " short");
    });
    const dayWord = days === 1 ? "1 day" : fmt(days) + " days";
    let note;
    if (building) {
      const readyDay = planet.citadel_complete_day || ((String(a.reason || "").match(/done day (\d+)/) || [])[1] || "");
      note = "Citadel L" + (target || level) + " is being built" + (readyDay ? ", ready day " + readyDay : "") + ".";
    } else {
      note = "Citadel level " + level + ". Fuel ore " + fmt(next.fuel_ore || next.credits || 0) + " (have " + fmt(have("fuel_have", "fuel_ore")) + "). Organics " + fmt(next.organics || 0) + " (have " + fmt(have("organics_have", "organics")) + "). Equipment " + fmt(next.equipment || 0) + " (have " + fmt(have("equipment_have", "equipment")) + "). Colonists " + fmt(next.colonists || 0) + " (have " + fmt(next.colonists_have != null ? next.colonists_have : cols) + "). " + dayWord + "." + ready + (gaps.length ? " " + gaps.join(", ") + "." : "");
    }
    if (!a.legal) {
      confirmWords("Build citadel", note);
      const btn = $("dangerOk");
      if (btn) { btn.textContent = "CONFIRM"; btn.classList.add("dim"); }
      return;
    }
    confirmWords("Build citadel", note, () => act("build_citadel", { planet_id: planet.id }, "build citadel"));
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
    const onPlanet = !!landedPlanet();
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
  function gameStatus() {
    const stats = S.daily_stats || {};
    const lines = [
      ["Day", S.day + " of " + S.max_days],
      ["Turns", fmt(S.turns_remaining) + " / " + fmt(S.turns_per_day)],
      ["Credits", fmt(S.credits) + " cr"],
      ["Bank", S.bank_balance == null ? "none" : fmt(S.bank_balance) + " cr"],
      ["Net worth", fmt(S.net_worth) + " cr"],
      ["Rank", S.rank || ""],
      ["Experience", fmt(S.experience)],
      ["Alignment", fmt(S.alignment) + " " + (S.alignment_label || "")],
      ["Overnight tax", lastTaxLine() || "none yet"],
      ["Tax due tomorrow", S.tax_due_tomorrow == null ? "none" : fmt(S.tax_due_tomorrow) + " cr"],
      ["Planets", fmt((S.owned_planets || []).length)],
      ["Known ports", fmt((S.known_ports || []).length)],
      ["Known sectors", fmt(Object.keys(S.known_warps || {}).length)],
    ];
    Object.entries(stats).forEach(([k, v]) => lines.push([k.replaceAll("_", " "), fmt(v)]));
    overlay("Game Status", lines.map(([k, v]) => '<div class="row"><span class="g">' + esc(k) + '</span> <span class="c">' + esc(v) + "</span></div>").join(""));
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
      Object.entries(inputs).forEach(([name, el]) => {
        values[name] = el.type === "number" ? Number(el.value) : String(el.value || "").trim();
      });
      if (fields.some((field) => field.required !== false && !values[field.n])) { setResult("Fill in the form.", true); return; }
      openFormKind = null;
      slot.innerHTML = "";
      submit(values);
    };
    wrap.appendChild(button("CONFIRM", go));
    wrap.appendChild(button("ESC", () => { openFormKind = null; slot.innerHTML = ""; }));
    wrap.addEventListener("keydown", (ev) => {
      if (ev.key !== "Enter") return;
      ev.preventDefault();
      ev.stopPropagation();
      go();
    });
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
    if (targets.length) fields.push({ n: "target", label: "target", required: false, choices: targets.map((id) => ({ value: id, label: id })) });
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
      { n: "target", label: "target", choices: targets.map((id) => ({ value: id, label: id })) },
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
      { n: "target_id", label: "target", choices: targets.map((id) => ({ value: id, label: id })) },
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
      confirmWords("Tri-Cron", "Ante " + fmt(ante) + " cr. " + rounds + " rounds.", () => act("tricron", {}, "tricron"));
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
    wrap.addEventListener("keydown", (ev) => {
      if (ev.key !== "Enter") return;
      ev.preventDefault();
      ev.stopPropagation();
      go();
    });
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
    wrap.addEventListener("keydown", (ev) => {
      if (ev.key !== "Enter") return;
      ev.preventDefault();
      ev.stopPropagation();
      go();
    });
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
      o.textContent = named ? named.name : id;
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
    wrap.addEventListener("keydown", (ev) => {
      if (ev.key !== "Enter") return;
      ev.preventDefault();
      ev.stopPropagation();
      go();
    });
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
      o.textContent = named ? named.name : id;
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
      if (!target.value || !n) { setResult("Pick a mate and an amount.", true); return; }
      openFormKind = null;
      slot.innerHTML = "";
      act("corp_transfer", { target: target.value, item: item.value, qty: n, direction: direction.value }, "transfer");
    };
    wrap.appendChild(button("CONFIRM", go));
    wrap.appendChild(button("ESC", () => { openFormKind = null; slot.innerHTML = ""; }));
    wrap.addEventListener("keydown", (ev) => {
      if (ev.key !== "Enter") return;
      ev.preventDefault();
      ev.stopPropagation();
      go();
    });
    slot.appendChild(wrap);
    qty.focus();
    qty.select();
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
      const id = ((((a.params || {}).target || {}).choices) || [])[0];
      if (!id) { setResult("Invite: no trader to invite", true); return; }
      const named = ((a.params || {}).targets || []).find((row) => row.player_id === id);
      confirmWords("Invite", "Invite " + esc(named ? named.name : id) + "?", () => act("corp_invite", { target: id }, "invite"));
    });
    add("corp_join", "Join", () => joinForm());
    add("corp_leave", "Leave", (a) => {
      const line = (a.params || {}).dissolves
        ? "Leave the corporation? You are the C.E.O., so it dissolves."
        : "Leave the corporation?";
      confirmWords("Leave", line, () => act("corp_leave", {}, "leave"));
    });
    add("corp_memo", "Memo", () => memoForm());
    add("corp_deposit", "Deposit credits", () => {});
    add("corp_withdraw", "Withdraw credits", () => {});
    add("corp_set_password", "Set password", () => passwordForm());
    add("corp_drop", "Drop member", (a) => dropForm(a));
    const ceo = button("Transfer C.E.O.", () => setResult("Handing the C.E.O. seat to another member is not in this game.", true));
    ceo.dataset.kind = "transfer_ceo";
    box.appendChild(ceo);
    add("corp_transfer", "Give or take", (a) => transferForm(a));
    add("ship_set_corporate", "Make ship corporate", () => act("ship_set_corporate", {}, "corporate"));
    add("ship_set_personal", "Make ship personal", () => act("ship_set_personal", {}, "personal"));
    add("propose_alliance", "Propose alliance", (a) => {
      const id = ((((a.params || {}).target || {}).choices) || [])[0];
      if (!id) { setResult("Propose alliance: no other commander", true); return; }
      confirmWords("Propose alliance", "Propose an alliance to " + esc(id) + "?", () => act("propose_alliance", { target: id }, "propose"));
    });
    add("accept_alliance", "Accept alliance", (a) => {
      const id = ((((a.params || {}).alliance_id || {}).choices) || [])[0];
      if (!id) { setResult("Accept alliance: no alliance proposal pending for you", true); return; }
      confirmWords("Accept alliance", "Accept alliance " + esc(id) + "?", () => act("accept_alliance", { alliance_id: id }, "accept"));
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
  function avoidForm(saved) {
    const a = LA("avoid");
    if (!a) { setResult("Avoid sectors: Avoid sectors is not in this game.", true); return; }
    if (!a.legal) { setResult("Avoid sectors: " + plainReason(a.reason), true); return; }
    dockForm("avoid", "AVOID SECTORS", "Type a sector the computer should not plot through, or 0 to clear the list.", [
      { n: "sector", label: "Sector", type: "number", min: 0, value: "2" },
    ], saved, (values) => act("avoid", { sector: values.sector }, "avoid"));
  }
  function jettisonForm(saved) {
    const choices = ((((LA("jettison") || {}).params || {}).commodity || {}).choices) || [];
    dockForm("jettison", "JETTISON CARGO", "Dumping colonists costs a good trader 1 alignment each, up to 250 a day. A trader who is not good pays no alignment. Other cargo is dumped into space and is gone.", [
      { n: "commodity", label: "Cargo", choices: choices.map((name) => ({ value: name, label: (COM[name] || [name])[0] })) },
      { n: "qty", label: "Quantity", type: "number", min: 1, value: "1" },
    ], saved, (values) => act("jettison", { commodity: values.commodity, qty: values.qty }, "jettison"));
  }
  function confirmWords(title, line, onYes) {
    const m = $("menu");
    m.hidden = false;
    inComputer = false;
    m.dataset.screen = title;
    m.innerHTML = '<div class="y">' + title + "</div><div>" + line + '</div><button type="button" id="dangerOk">' + (onYes ? "CONFIRM" : "OK") + '</button><br><span class="dk">Esc to close</span>';
    $("dangerOk").addEventListener("click", () => { m.hidden = true; if (onYes) onYes(); else setResult(line, true); });
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
  function key(k) {
    const m = $("menu");
    if (outOfTurns() && !["Escape", "?", "D", "C", "I", "V", "G", "Y"].includes(k)) { setResult(noTurnsLine(), true); return; }
    if (k === "Escape") {
      m.hidden = true; inComputer = false; openFormKind = null; formFocus = "";
      const slot = $("formSlot"); if (slot) slot.innerHTML = "";
      return;
    }
    if (k === "Enter") { if (plotted) engage(); return; }
    if (inComputer) {
      inComputer = false;
      const c = CKEYS.find((x) => x[0] === k);
      if (!c) { m.hidden = true; setResult("That is not a computer command.", true); return; }
      if (k === "Q") { m.hidden = true; return; }
      if (k === "F") { m.hidden = true; askSector((n) => go(n)); return; }
      if (k === "R") return portReport();
      if (k === "K") return knownUniverse();
      if (k === "O") { m.hidden = true; return avoidForm(); }
      m.hidden = true;
      if (c[2]) return openForm(c[2]);
      return;
    }
    if (k === "?" || k === "C") {
      m.hidden = false;
      inComputer = k === "C";
      const list = k === "C" ? CKEYS : MENU_KEYS;
      m.innerHTML = '<div class="y">' + (k === "C" ? "Computer command" : "Main menu") + "</div>" +
        list.map(([kk, l]) => '<div class="row"><kbd>&lt;' + kk + "&gt;</kbd> <span class=\"c\">" + l + "</span></div>").join("") +
        '<br><span class="dk">Esc to close</span>';
      return;
    }
    if (landedPlanet() && (k === "Q" || PLANET_KEYS.some((row) => row[0] === k))) return planetAct(k);
    if (landedPlanet() && SPACE_OFF.includes(k)) { setResult("Lift off first", true); return; }
    if (k === "D") { render(); return; }
    if (k === "I") { shipInfo(); return; }
    if (k === "V") return gameStatus();
    if (k === "Y") return readMail();
    if (k === "F" && !landedPlanet()) return fighterForm();
    if (k === "H" && !landedPlanet()) return mineForm();
    if (k === "G") return showFighters();
    if (k === "B" && landedPlanet()) return citadelForm();
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
    if (k === "L") {
      const p = (S.sector.planets || [])[0];
      if (!p) return;
      return confirmWords("Land", landLine(p), () => act("land_planet", { planet_id: p.id }, "land on " + p.name));
    }
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
  async function act(kind, args, label) {
    taxFresh = false;
    dayNote = false;
    if (kind === "bank") { setResult("That command was not accepted.", true); return; }
    if (kind !== "wait") waitStreak = 0;
    if (state.busy || !state.awaiting) {
      if (outOfTurns()) { setResult(noTurnsLine(), true); return; }
      if (pending && pending.kind === kind) {
        setResult(capFirst((label || kind) + " will run when your turn comes."), true);
        return;
      }
      pending = { kind, args, label };
      heldLabel = label || kind;
      setResult(capFirst((label || kind) + " will run when your turn comes."), true);
      return;
    }
    pending = null;
    state.busy = true;
    keys();
    const creditsBefore = S ? S.credits : 0;
    const turnsBefore = S ? S.turns_remaining : 0;
    try {
      const before = state.eventsSince;
      await api("/" + state.seat + "/action", { method: "POST", body: JSON.stringify({ turn_seq: state.turnSeq, action: { kind, args: args || {} } }) });
      state.awaiting = false;
      await refresh();
      const spent = Math.max(0, turnsBefore - (S ? S.turns_remaining : turnsBefore));
      const delta = (S ? S.credits : creditsBefore) - creditsBefore;
      const tail = ". Turns spent " + spent + ". Credits " + (delta >= 0 ? "+" : "") + fmt(delta) + ".";
      if (kind === "wait") { if (!dayNote) setResult("You wait" + tail, false); $("err").hidden = true; return; }
      const ev = latestAfter(before - 1);
      const raw = ev && ev.summary ? String(ev.summary) : "";
      const counter = /counter (\d+)/i.exec(raw);
      const retry = { side: (args || {}).side, commodity: (args || {}).commodity, qty: (args || {}).qty };
      if (kind === "trade" && counter) {
        setResult("The port counters at " + fmt(counter[1]) + " cr. Enter that price, or try another." + tail, true);
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
          if (row && row.kind === "combat" && (row.seq || 0) > before - 1) combat = row;
        });
        let mine = null;
        let back = null;
        streamLog.concat((S && S.recent_events) || []).forEach((row) => {
          if (!row || row.kind !== "combat" || (row.seq || 0) <= before - 1) return;
          const facts = row.facts || {};
          if (facts.attacker === S.self_id || row.actor_id === S.self_id) mine = row;
          if (facts.defender === S.self_id && facts.exchange_kind === "ferrengi_vs_ship") back = row;
        });
        const facts = (mine && mine.facts) || (combat && combat.facts) || {};
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
          body = body.replace(/[.\s]+$/, "") + ". " + siegeLosses(facts);
          if (delta < 0) body += ". Credits on board lost: " + fmt(-delta) + " cr";
        }
      }
      if (kind === "set_military_reaction" && args && args.pct != null) body = body + " to " + fmt(args.pct) + "%";
      if (!dayNote && bad) {
        setResult((/trade failed|lost patience/i.test(raw) ? "FAILED" : "REFUSED") + " — " + body + tail, true);
        if (kind === "trade") openForm("trade", retry);
      } else if (!dayNote) setResult("ok — " + body + tail, false);
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
    }
  }

  async function fetchEvents() {
    const r = await api("/" + state.seat + "/events?since=" + state.eventsSince + "&limit=100&course=1");
    if (state.mediaHistoryUntil == null) state.mediaHistoryUntil = typeof r.latest_seq === "number" ? r.latest_seq : 0;
    const catchingUp = !state.mediaCaughtUp && state.eventsSince < state.mediaHistoryUntil;
    const fresh = r.events || [];
    if (fresh.length) state.eventsSince = r.next_since;
    else state.mediaCaughtUp = true;
    noteCourse(fresh);
    if (S) paintLog();
    if (fresh.some((ev) => ev.kind === "autopilot")) { mapSig = ""; map(); }
    if (window.TW2KMedia && fresh.length) {
      const hist = catchingUp ? fresh.filter((ev) => ev.seq <= state.mediaHistoryUntil) : [];
      const live = catchingUp ? fresh.filter((ev) => ev.seq > state.mediaHistoryUntil) : fresh;
      if (hist.length) window.TW2KMedia.onEvents(hist, S, { history: true });
      if (live.length) window.TW2KMedia.onEvents(live, S);
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
    if (!best || (best.seq || 0) <= alertedSeq) {
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
      if (notice.kind === "mine_detonated") setResult("Your mines hit " + traderName(facts.victim) + " in sector " + (notice.sector_id || "") + " for " + fmt(facts.damage || 0) + " damage.", true);
      else if (notice.kind === "combat" && facts.planet_fighters_lost != null) setResult(traderName(notice.actor_id) + " attacked " + (facts.planet_name || "your planet") + ": the planet lost " + fmt(facts.planet_fighters_lost) + " fighters and " + fmt(facts.planet_shields_lost || 0) + " shields.", true);
      else if (notice.kind === "combat") setResult("Your fighters fought in sector " + (notice.sector_id || "") + ".", true);
      else setResult("Someone landed on your planet" + (facts.seized ? " and took it." : "."), true);
      return;
    }
    rememberAlert(best.seq);
    const facts = best.facts || {};
    if (facts.shield_losses != null) {
      setResult(traderName(facts.attacker) + " attacked you in " + (best.sector_id || "") + ": you lost " + fmt(facts.shield_losses) + " shields, " + fmt(facts.defender_losses || 0) + " fighters (" + fmt(facts.defender_s || 0) + " shields left).", true);
    } else {
      const who = facts.attacker || "someone";
      const lost = facts.defender_losses;
      setResult("You were attacked by " + who + (lost == null ? "." : ". You lost " + lost + "."), true);
    }
  }
  function render() {
    const dayNow = Number(S.day);
    if (seenDay != null && dayNow !== seenDay) {
      taxFresh = true;
      dayNote = true;
      const tax = overnightTax();
      let fell = "";
      streamLog.concat(S.recent_events || []).forEach((ev) => {
        if (!ev || (ev.seq || 0) <= fellSeenSeq) return;
        if (/fell back/i.test(ev.summary || "")) { fell = plainWords(ev.summary); fellSeenSeq = ev.seq || fellSeenSeq; }
      });
      setResult("Day " + dayNow + ". Turns refilled to " + fmt(S.turns_remaining) + "." + (tax ? " " + tax : "") + (fell ? " " + fell : ""), false);
    }
    seenDay = dayNow;
    const sec = S.sector || {};
    $("pSector").textContent = sec.id ?? "-";
    $("tl").textContent = fmt(S.turns_remaining);
    $("turns").textContent = fmt(S.turns_remaining) + "/" + fmt(S.turns_per_day);
    $("credits").textContent = fmt(S.credits) + " cr";
    $("sbDay").textContent = String(S.day);
    $("xp").textContent = fmt(S.experience);
    $("maxDays").textContent = String(S.max_days);
    $("nw").textContent = fmt(S.net_worth);
    $("rank").textContent = S.rank || "";
    const al = $("align");
    al.textContent = fmt(S.alignment) + " " + (S.alignment_label || "");
    al.className = S.alignment < 0 ? "r" : S.alignment > 0 ? "c" : "w";
    const chip = $("waitchip");
    chip.textContent = outOfTurns() ? "NO TURNS" : (state.awaiting ? "YOUR MOVE" : "WAITING");
    chip.className = "chip" + (state.awaiting && !outOfTurns() ? "" : " idle");
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
    if (st.video_custom === true && window.TW2KMedia && window.TW2KMedia.setVideoCustom) window.TW2KMedia.setVideoCustom(true);
    if (st.observation) { S = st.observation; render(); }
    await fetchEvents();
    keys();
    if (!state.busy && state.awaiting && pending) flushPending();
    else if (!state.busy) clearStaleWait();
  }
  async function connect() {
    state.seat = $("seatSelect").value.toUpperCase();
    state.token = $("tokenInput").value.trim();
    try { alertedSeq = Number(localStorage.getItem("tw2k-alert-" + state.seat) || 0); } catch (e) { alertedSeq = 0; }
    $("err").hidden = true;
    try {
      state.connected = true;
      await refresh();
      const sign = document.querySelector(".sign-in");
      if (sign) sign.hidden = true;
    } catch (e) {
      state.connected = false;
      $("err").hidden = false;
      $("err").textContent = String(e.message || e);
    }
  }
  $("connectBtn").addEventListener("click", connect);
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
    serverWaits() { return Number(state.waitStreak || 0); },
    resetWaits() { waitStreak = 0; state.waitStreak = 0; },
  };
  if (state.token) connect();
  setInterval(() => { if (state.connected && !state.busy) refresh().catch((e) => { $("err").hidden = false; $("err").textContent = String(e.message || e); }); }, 2000);
})();
