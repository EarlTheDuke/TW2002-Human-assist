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
    ["C", "Computer", null, 1], ["I", "Ship Info", null, 1], [".", "Wait", "wait", 1],
    ["T", "Corporate Menu", "corp_create", 0], ["R", "Release Beacon", "launch_beacon", 0],
    ["X", "Transporter Pad", "ship_transport", 0], ["W", "Tow SpaceCraft", "tow_engage", 0],
  ];
  const CKEYS = [
    ["F", "Course Plotter", "plot_course"], ["P", "Fire Photon Missile", "photon_missile"],
    ["R", "Port Report", null], ["K", "Your Known Universe", null], ["A", "Make Announcement", "broadcast"],
    ["Q", "Exit Computer", null],
  ];
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
  let S = null, plotted = null, inComputer = false, sceneTable = null;
  if (params.get("token")) {
    params.delete("token");
    const q = params.toString();
    history.replaceState(null, "", location.pathname + (q ? "?" + q : ""));
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
    if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : (data.message || text.slice(0, 180) || String(r.status)));
    return data;
  }
  const LA = (k) => ((S && S.legal_actions) || []).find((a) => a.kind === k);
  const legal = (k) => !!(LA(k) || {}).legal;
  function log(html) {
    const d = document.createElement("div");
    d.innerHTML = html;
    $("log").prepend(d);
    while ($("log").children.length > 40) $("log").lastChild.remove();
  }
  function setResult(text, bad) {
    const el = $("lastResult");
    el.textContent = text || "";
    el.className = bad ? "bad" : "";
  }
  function landedPlanet() {
    if (!S || S.planet_landed == null) return null;
    const id = Number(S.planet_landed);
    return (S.sector.planets || []).find((p) => Number(p.id) === id)
      || (S.owned_planets || []).find((p) => Number(p.id) === id)
      || { id, name: "planet " + id };
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
  function sectorText() {
    const s = S.sector;
    const landed = landedPlanet();
    let t = '<span class="g">Sector  </span><span class="y">:</span> <span class="c">' + s.id + "</span> <span class=\"g\">in</span> <span class=\"c\">" + (s.is_fedspace ? "The Federation" : "uncharted space") + ".</span>\n";
    if (s.port) t += '<span class="g">Ports   </span><span class="y">:</span> <span class="c">' + esc(s.port.name) + '</span><span class="y">,</span> <span class="g">Class</span> <span class="c">' + s.port.class_id + '</span> <span class="w">(</span><span class="m">' + esc(s.port.code) + "</span><span class=\"w\">)</span>\n";
    (s.planets || []).forEach((p) => { t += '<span class="g">Planets </span><span class="y">:</span> <span class="c">' + esc(p.name) + "</span>\n"; });
    (s.occupants || []).forEach((o) => {
      const id = typeof o === "string" ? o : (o.id || "");
      if (id === S.self_id) return;
      const knownTrader = (S.others || []).find((row) => row.id === id) || (typeof o === "object" ? o : null);
      const name = knownTrader && knownTrader.name ? knownTrader.name : id;
      const hull = knownTrader && knownTrader.ship_class ? String(knownTrader.ship_class).replaceAll("_", " ") : "";
      t += '<span class="g">Traders </span><span class="y">:</span> <span class="c">' + esc(name + (hull ? " in a " + hull : "")) + "</span>\n";
    });
    if (s.fighter_group) {
      const yours = s.fighter_group.owner_id === S.self_id ? " yours" : "";
      t += '<span class="g">Fighters</span><span class="y">:</span> <span class="c">' + fmt(s.fighter_group.count) + yours + "</span>\n";
    }
    t += '<span class="g">Warps to Sector(s) </span><span class="y">:</span> ' + (s.warps_out || []).map((w) => known(w) ? '<span class="c">' + w + "</span>" : '<span class="r">(' + w + ")</span>").join(" - ");
    if (landed) t += '\n<span class="y">You are LANDED on ' + esc(landed.name) + "</span>";
    $("sectorText").innerHTML = t;
  }
  function bfs(a, b) {
    const W = S.known_warps || {};
    const prev = { [a]: null };
    const q = [a];
    while (q.length) {
      const c = q.shift();
      if (c === b) break;
      (W[c] || W[String(c)] || []).forEach((n) => { if (!(n in prev)) { prev[n] = c; q.push(n); } });
    }
    if (!(b in prev)) return [];
    const p = [];
    for (let c = b; c != null; c = prev[c]) p.unshift(+c);
    return p;
  }
  function map() {
    const svg = $("map");
    const ks = S.known_sectors || [];
    const pos = {};
    ks.forEach((k) => { pos[k.id] = k; });
    const here = pos[S.sector.id] || { x: 0, y: 0, id: S.sector.id };
    if (!pos[S.sector.id]) pos[S.sector.id] = here;
    const nodes = Object.values(pos);
    const ds = nodes.map((k) => Math.hypot((k.x || 0) - (here.x || 0), (k.y || 0) - (here.y || 0))).sort((a, b) => a - b);
    const maxd = Math.max(1, ds[ds.length - 1] || 1);
    const P = (k) => {
      const dx = (k.x || 0) - (here.x || 0), dy = (k.y || 0) - (here.y || 0), d = Math.hypot(dx, dy);
      if (!d) return [0, 0];
      const r = 265 * Math.sqrt(d / maxd);
      return [dx / d * r, dy / d * r];
    };
    let h = "";
    const seen = new Set();
    const route = new Set((plotted && plotted.path) || []);
    Object.entries(S.known_warps || {}).forEach(([a, bs]) => (bs || []).forEach((b) => {
      if (!pos[a] || !pos[b]) return;
      const key = [a, b].sort().join();
      if (seen.has(key)) return;
      seen.add(key);
      const [x1, y1] = P(pos[a]), [x2, y2] = P(pos[b]);
      h += '<line class="lane' + (route.has(+a) && route.has(+b) ? " route" : "") + '" x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 + '"/>';
    }));
    nodes.forEach((k) => {
      const [x, y] = P(k);
      const adj = (S.sector.warps_out || []).includes(k.id);
      const cls = ["node", k.id === S.sector.id ? "here" : "", adj ? "adj" : "", k.port ? "port" : "", plotted && plotted.target === k.id ? "tgt" : ""].join(" ");
      h += '<g class="' + cls + '" data-id="' + k.id + '"><circle cx="' + x + '" cy="' + y + '" r="' + (k.id === S.sector.id ? 11 : adj ? 9 : 6) + '"/><text x="' + (x + 11) + '" y="' + (y + 4) + '">' + k.id + "</text></g>";
    });
    svg.innerHTML = h;
    svg.querySelectorAll(".node").forEach((n) => n.addEventListener("click", () => go(+n.dataset.id)));
    const row = $("warps");
    row.innerHTML = '<span class="g">Warps:</span> ';
    (S.sector.warps_out || []).forEach((w, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = (i + 1) + ":" + w;
      b.disabled = !legal("warp") || !state.awaiting;
      b.addEventListener("click", () => act("warp", { target: w }, "M — warp to " + w));
      row.appendChild(b);
    });
    if (plotted) {
      const eng = document.createElement("button");
      eng.type = "button";
      eng.className = "eng";
      eng.textContent = "ENGAGE → " + plotted.target;
      eng.addEventListener("click", engage);
      const cancel = document.createElement("button");
      cancel.type = "button";
      cancel.textContent = "✕";
      cancel.addEventListener("click", () => { plotted = null; map(); });
      row.appendChild(eng);
      row.appendChild(cancel);
    }
  }
  function go(id) {
    if (!S || id === S.sector.id) return;
    if ((S.sector.warps_out || []).includes(id)) return act("warp", { target: id }, "M — warp to " + id);
    plotted = { target: id, path: bfs(S.sector.id, id) };
    act("plot_course", { target: id, execute: false }, "C·F — plot course to " + id);
    log('<span class="y">Route plotted to ' + id + ". Press ENTER to fly it.</span>");
    map();
  }
  function engage() {
    if (!plotted) return;
    const t = plotted.target;
    plotted = null;
    act("plot_course", { target: t, execute: true }, "Autopilot engaged → " + t);
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
    $("shipStats").innerHTML = bar("Fighters", sh.fighters, sh.fighter_cap, "#ff5555") + bar("Shields", sh.shields, sh.shield_cap, "#55ffff") + bar("Holds", used, sh.holds, "#ffff55");
    $("holds").innerHTML = Object.entries(COM).map(([k, row]) => '<div class="hold"><b>' + row[0] + "</b><br>" + fmt((sh.cargo || {})[k]) + "</div>").join("");
    const root = $("viewport");
    if (root && window.TW2KViewport) window.TW2KViewport.update(S);
  }

  function tradeWhy(commodity, stock, ship, side) {
    const name = (COM[commodity] || [commodity])[0];
    const onboard = Number((ship.cargo || {})[commodity] || 0);
    const used = Object.values(ship.cargo || {}).reduce((sum, n) => sum + Number(n || 0), 0);
    if (side === "buy" && !(Number(stock.current) > 0)) return "This port has no " + name + " to sell right now";
    if (side === "sell" && onboard <= 0) return "You have no " + name + " on board";
    if (side === "sell" && !(Number(stock.current) > 0)) return "This port is not buying " + name + " today";
    if (side === "buy" && used >= Number(ship.holds || 0)) return "No empty holds";
    if (side === "buy" && stock.price && S.credits < Number(stock.price)) return "Not enough credits";
    return "Nothing to trade";
  }
  function plainReason(text) {
    if (!state.awaiting) return "Waiting for your turn.";
    return String(text || "not available here")
      .replace(/pool=fuel_ore/g, "fuel ore")
      .replace(/pool=organics/g, "organics")
      .replace(/pool=equipment/g, "equipment")
      .replace(/buy_equip/g, "buy gear")
      .replace(/_/g, " ");
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
    const box = $("here");
    box.innerHTML = "";
    const s = S.sector, sh = S.ship || {};
    const landed = landedPlanet();
    if (landed) box.appendChild(button("<kbd>Q</kbd>Lift off", () => act("liftoff", {}, "Q — lift off")));
    if (s.port && !landed) {
      const table = document.createElement("table");
      table.className = "porttbl";
      table.innerHTML = "<tr><th>Items</th><th>Status</th><th>Trading</th><th>Price</th><th>OnBoard</th><th></th></tr>";
      Object.entries(s.port.stock || {}).forEach(([k, v]) => {
        const meta = COM[k] || [k, "#fff"];
        const side = v.side === "buys_from_player" ? "sell" : "buy";
        const mx = maxBy("trade", k, side);
        const tr = document.createElement("tr");
        tr.innerHTML = "<td style=\"color:" + meta[1] + "\">" + esc(meta[0]) + "</td><td>" + (side === "sell" ? "Buying" : "Selling") + "</td><td class=\"c\">" + fmt(v.current) + "</td><td class=\"y\">" + (v.price ?? "") + "</td><td class=\"w\">" + (sh.cargo[k] || 0) + "</td><td></td>";
        if (mx > 0 && legal("trade") && state.awaiting) {
          const b = document.createElement("button");
          b.type = "button";
          b.className = "tbtn " + side;
          b.textContent = (side === "sell" ? "SELL " : "BUY ") + mx;
          b.addEventListener("click", () => act("trade", { side, commodity: k, qty: mx }, "P — " + side + " " + mx + " " + meta[0]));
          tr.lastChild.appendChild(b);
        } else {
          tr.lastChild.textContent = tradeWhy(k, v, sh, side);
        }
        table.appendChild(tr);
      });
      box.appendChild(table);
      if (!legal("trade")) {
        const why = document.createElement("div");
        why.className = "dk";
        why.textContent = "";
        box.appendChild(why);
      }
    }
    if (!landed) (s.planets || []).forEach((p) => {
      box.appendChild(button("<kbd>L</kbd>Land on " + esc(p.name), () => act("land_planet", { planet_id: p.id }, "L — land on " + p.name)));
    });
    if (Number(s.id) === 1 || (s.port && /stardock/i.test(String(s.port.name || "")))) {
      if (legal("buy_equip")) box.appendChild(button("StarDock: buy gear", () => openForm("buy_equip")));
      if (legal("buy_ship")) box.appendChild(button("Shipyards", () => openForm("buy_ship")));
      if (legal("bank_deposit")) box.appendChild(button("Bank", () => openForm("bank_deposit")));
    }
    const slot = document.createElement("div");
    slot.id = "formSlot";
    box.appendChild(slot);
  }
  function openForm(kind) {
    const a = LA(kind) || { params: {} };
    if (!a.legal) { setResult(plainReason(a.reason || kind + " is not available"), true); return; }
    const slot = $("formSlot");
    if (!slot) return;
    slot.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "frm";
    const title = document.createElement("div");
    title.className = "y";
    title.textContent = kind.replaceAll("_", " ").toUpperCase();
    wrap.appendChild(title);
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
          o.textContent = o.value;
          input.appendChild(o);
        });
      } else if (spec.type === "bool") {
        input = document.createElement("input");
        input.type = "checkbox";
      } else {
        input = document.createElement("input");
        input.type = spec.type === "int" ? "number" : "text";
        if (spec.min != null) input.min = spec.min;
      }
      input.dataset.n = name;
      input.dataset.t = spec.type;
      label.appendChild(input);
      wrap.appendChild(label);
      fields.push(input);
    });
    wrap.appendChild(button("CONFIRM", () => {
      const args = {};
      fields.forEach((el) => {
        const t = el.dataset.t;
        let v = t === "bool" ? el.checked : el.value;
        if (t === "int") v = Number(v);
        if (v !== "" && v !== null) args[el.dataset.n] = v;
      });
      slot.innerHTML = "";
      act(kind, args, kind.replaceAll("_", " "));
    }));
    wrap.appendChild(button("ESC", () => { slot.innerHTML = ""; }));
    slot.appendChild(wrap);
  }

  function keys() {
    const bar = $("keys");
    bar.innerHTML = "";
    KEYS.filter((row) => row[3]).forEach(([k, label, kind]) => {
      const b = document.createElement("button");
      b.type = "button";
      b.dataset.key = k;
      const off = kind && !legal(kind);
      b.className = off ? "off" : "on";
      b.disabled = !state.awaiting || state.busy;
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
  function key(k) {
    const m = $("menu");
    if (k === "Escape") { m.hidden = true; inComputer = false; return; }
    if (k === "Enter") { if (plotted) engage(); return; }
    if (inComputer) {
      inComputer = false; m.hidden = true;
      const c = CKEYS.find((x) => x[0] === k);
      if (!c) return;
      if (k === "F") { const t = prompt("Course plotter — destination sector?"); if (t) go(+t); return; }
      if (c[2]) return openForm(c[2]);
      return;
    }
    if (k === "?" || k === "C") {
      m.hidden = false;
      inComputer = k === "C";
      const list = k === "C" ? CKEYS : KEYS;
      m.innerHTML = '<div class="y">' + (k === "C" ? "Computer command" : "Main menu") + "</div>" +
        list.map(([kk, l]) => '<div class="row"><kbd>&lt;' + kk + "&gt;</kbd> <span class=\"c\">" + l + "</span></div>").join("") +
        '<br><span class="dk">Esc to close</span>';
      return;
    }
    if (k === "Q" && landedPlanet()) return act("liftoff", {}, "Q — lift off");
    if (k === "D") { render(); return; }
    if (k === "I") { $("ship").scrollIntoView({ behavior: "smooth" }); return; }
    const hit = KEYS.find((x) => x[0] === k);
    if (!hit) return;
    if (hit[2] && !legal(hit[2])) { setResult(hit[1] + ": " + plainReason((LA(hit[2]) || {}).reason), true); return; }
    if (k === "M") {
      const w = S.sector.warps_out || [];
      if (w.length === 1) return go(w[0]);
      const t = prompt("Move to which sector? (" + w.join(" - ") + ")");
      if (t) go(+t);
      return;
    }
    if (k === "P") return openForm("trade");
    if (k === "L") {
      const p = (S.sector.planets || [])[0];
      if (p) return act("land_planet", { planet_id: p.id }, "L — land");
      return;
    }
    if (k === ".") return act("wait", {}, "wait one turn");
    if (k === "S") return act("scan", {}, "S — long range scan");
    if (hit[2]) return openForm(hit[2]);
  }

  async function act(kind, args, label) {
    if (!state.awaiting || state.busy) { setResult("Waiting for your turn.", true); return; }
    state.busy = true;
    keys();
    const creditsBefore = S ? S.credits : 0;
    const turnsBefore = S ? S.turns_remaining : 0;
    try {
      await api("/" + state.seat + "/action", { method: "POST", body: JSON.stringify({ turn_seq: state.turnSeq, action: { kind, args: args || {} } }) });
      state.awaiting = false;
      await refresh();
      const spent = Math.max(0, turnsBefore - (S ? S.turns_remaining : turnsBefore));
      const delta = (S ? S.credits : creditsBefore) - creditsBefore;
      setResult("ok — " + (label || kind) + ". Turns spent " + spent + ". Credits " + (delta >= 0 ? "+" : "") + fmt(delta) + ".", false);
      $("err").hidden = true;
    } catch (e) {
      setResult("refused: " + plainReason(e.message || e) + ". Turns spent 0.", true);
      $("err").hidden = false;
      $("err").textContent = String(e.message || e);
    } finally {
      state.busy = false;
      keys();
    }
  }

  async function fetchEvents() {
    const r = await api("/" + state.seat + "/events?since=" + state.eventsSince + "&limit=100");
    if (state.mediaHistoryUntil == null) state.mediaHistoryUntil = typeof r.latest_seq === "number" ? r.latest_seq : 0;
    const catchingUp = !state.mediaCaughtUp && state.eventsSince < state.mediaHistoryUntil;
    const fresh = r.events || [];
    if (fresh.length) state.eventsSince = r.next_since;
    else state.mediaCaughtUp = true;
    if (window.TW2KMedia && fresh.length) {
      const hist = catchingUp ? fresh.filter((ev) => ev.seq <= state.mediaHistoryUntil) : [];
      const live = catchingUp ? fresh.filter((ev) => ev.seq > state.mediaHistoryUntil) : fresh;
      if (hist.length) window.TW2KMedia.onEvents(hist, S, { history: true });
      if (live.length) window.TW2KMedia.onEvents(live, S);
    }
  }

  function render() {
    const sec = S.sector || {};
    $("pSector").textContent = sec.id ?? "-";
    $("tl").textContent = fmt(S.turns_remaining);
    $("turns").textContent = fmt(S.turns_remaining) + "/" + fmt(S.turns_per_day);
    $("credits").textContent = fmt(S.credits) + " cr";
    $("sbDay").textContent = String(S.day);
    $("maxDays").textContent = String(S.max_days);
    $("nw").textContent = fmt(S.net_worth);
    $("rank").textContent = S.rank || "";
    const al = $("align");
    al.textContent = fmt(S.alignment) + " " + (S.alignment_label || "");
    al.className = S.alignment < 0 ? "r" : S.alignment > 0 ? "c" : "w";
    const chip = $("waitchip");
    chip.textContent = state.awaiting ? "YOUR MOVE" : "Other commanders moving";
    chip.className = "chip" + (state.awaiting ? "" : " idle");
    document.querySelector("[data-testid=prompt-line]").textContent = "Command [TL=" + fmt(S.turns_remaining) + "] (?=Help) :";
    paintScene();
    sectorText();
    map();
    paintShip();
    here();
    keys();
  }

  async function refresh() {
    const st = await api("/" + state.seat + "/observation?wait_s=0&peek=1&format=both");
    state.awaiting = !!st.awaiting_input;
    state.turnSeq = st.turn_seq ?? state.turnSeq;
    if (st.video_custom === true && window.TW2KMedia && window.TW2KMedia.setVideoCustom) window.TW2KMedia.setVideoCustom(true);
    if (st.observation) { S = st.observation; render(); }
    await fetchEvents();
    keys();
  }
  async function connect() {
    state.seat = $("seatSelect").value.toUpperCase();
    state.token = $("tokenInput").value.trim();
    $("err").hidden = true;
    try {
      state.connected = true;
      await refresh();
    } catch (e) {
      state.connected = false;
      $("err").hidden = false;
      $("err").textContent = String(e.message || e);
    }
  }
  $("connectBtn").addEventListener("click", connect);
  document.addEventListener("keydown", (ev) => {
    const tag = (ev.target && ev.target.tagName) || "";
    if (/^(INPUT|SELECT|TEXTAREA)$/.test(tag) || ev.ctrlKey || ev.metaKey || ev.altKey) return;
    if (ev.key === "Enter") { ev.preventDefault(); key("Enter"); return; }
    if (ev.key === "Escape") { ev.preventDefault(); key("Escape"); return; }
    if (ev.key === "?") { ev.preventDefault(); key("?"); return; }
    if (ev.key === ".") { ev.preventDefault(); key("."); return; }
    if (ev.key.length === 1) { ev.preventDefault(); key(ev.key.toUpperCase()); }
  });
  if (state.token) connect();
  setInterval(() => { if (state.connected && !state.busy) refresh().catch((e) => { $("err").hidden = false; $("err").textContent = String(e.message || e); }); }, 2000);
})();
