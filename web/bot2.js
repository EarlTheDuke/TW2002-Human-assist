/* Redesigned helm. Same harness, same scene stills and clips. /bot is a different page. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const params = new URLSearchParams(location.search);
  const state = {
    seat: (params.get("seat") || "P2").toUpperCase(),
    token: params.get("token") || "",
    connected: false,
    awaiting: false,
    busy: false,
    turnSeq: 0,
    obs: null,
    legal: [],
    eventsSince: 0,
    mediaHistoryUntil: null,
    mediaCaughtUp: false,
  };
  const TOP = [
    ["W", "warp", "Warp"],
    ["P", "trade", "Port"],
    ["S", "scan", "Scan"],
    ["L", "land", "Land"],
    ["D", "deploy_fighters", "Deploy"],
    ["A", "attack", "Attack"],
    ["H", "hail", "Hail"],
    ["C", "plot_course", "Computer"],
    ["T", "ship_transwarp", "Transwarp"],
    ["E", "wait", "End"],
  ];
  const HULL = {
    scout_marauder: "light", missile_frigate: "light",
    battleship: "heavy", havoc_gunstar: "heavy",
    corporate_flagship: "capital", imperial_starship: "capital",
    escape_pod: "pod",
  };
  const CARGO = [
    ["fuel_ore", "Fuel ore", "fuel"],
    ["organics", "Organics", "org"],
    ["equipment", "Equipment", "equip"],
    ["colonists", "Colonists", "col"],
  ];

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
    try { data = text ? JSON.parse(text) : {}; } catch (e) { data = { raw: text }; }
    if (!r.ok) throw new Error(data.detail || data.message || text.slice(0, 180) || String(r.status));
    return data;
  }
  function num(n) { return Number(n || 0).toLocaleString("en-US"); }
  function legalOf(kind) { return state.legal.find((row) => row.kind === kind) || null; }

  function paintScene(obs) {
    const img = $("sceneStill");
    if (!img || !obs) return;
    const ship = obs.ship || {};
    let key = "sector_deep";
    if (ship.class === "escape_pod") key = "in_pod";
    else if (obs.planet_landed != null) {
      const owned = (obs.owned_planets || []).some((p) => Number(p.id) === Number(obs.planet_landed));
      key = owned ? "planet_own" : "planet_foreign";
    } else {
      const sector = obs.sector || {};
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
        if (!entry) {
          current = String(current).startsWith("sector_port_") ? "docked_port" : "sector_deep";
          continue;
        }
        if (entry.file) { file = entry.file; break; }
        current = entry.fallback || "canvas";
      }
      if (!file) { img.hidden = true; return; }
      img.alt = key;
      img.hidden = false;
      img.src = "/static/media/" + file;
    };
    if (paintScene.table) { draw(paintScene.table); return; }
    fetch("/static/media/manifest.json").then((r) => r.json()).then((data) => {
      paintScene.table = data.keys || {};
      draw(paintScene.table);
    }).catch(() => { img.hidden = true; });
  }

  function shipSvg(family) {
    const bodies = {
      light: '<path d="M24 72 H150 L214 64 L150 56 H24 Z"/><path d="M150 56 L228 64 L150 72"/><rect x="48" y="60" width="22" height="8"/>',
      heavy: '<path d="M16 86 H140 L206 64 L140 42 H16 Z"/><path d="M60 42 V26 H118 V42 M60 86 V102 H118 V86"/><rect x="36" y="58" width="28" height="12"/>',
      capital: '<path d="M12 90 H120 L196 64 L120 38 H12 Z"/><path d="M36 38 V18 H88 V38 M36 90 V110 H88 V90"/><path d="M140 52 H188 M140 76 H188"/><rect x="28" y="56" width="34" height="16"/>',
      pod: '<ellipse cx="78" cy="64" rx="46" ry="26"/><path d="M110 64 H150"/><circle cx="70" cy="64" r="8"/>',
      hauler: '<path d="M14 88 H150 L198 64 L150 40 H14 Z"/><path d="M30 40 V24 H130 V40 M30 88 V104 H130 V88"/><rect x="40" y="54" width="36" height="20"/><path d="M186 58 H222 M186 70 H222" stroke="#ffff55"/>',
    };
    return '<svg viewBox="0 0 240 140" role="img" aria-label="Ship"><g fill="none" stroke="#55ffff" stroke-width="2">' +
      (bodies[family] || bodies.hauler) + "</g></svg>";
  }
  function fighterRow(have, cap) {
    const n = 12;
    let on = cap > 0 ? Math.round(n * Math.min(1, have / cap)) : 0;
    if (have > 0 && on < 1) on = 1;
    let html = '<span class="fighters" data-testid="fighter-row">';
    for (let i = 0; i < n; i++) html += '<i class="' + (i < on ? "on" : "") + '"></i>';
    return html + "</span>";
  }
  function paintShip(obs) {
    const ship = (obs && obs.ship) || {};
    const family = HULL[ship.class] || (ship.class === "escape_pod" ? "pod" : "hauler");
    $("shipClass").textContent = ship.class ? String(ship.class).replaceAll("_", " ") : "—";
    const root = $("viewport");
    if (root) root.setAttribute("data-hull", family === "pod" ? "light" : family);
    $("shipArt").innerHTML = shipSvg(family) + fighterRow(ship.fighters || 0, ship.fighter_cap || 0);
    const mines = ship.mines || {};
    const mineCount = Object.values(mines).reduce((s, n) => s + Number(n || 0), 0);
    const tw = ship.transwarp || {};
    const rows = [
      ["Fighters", num(ship.fighters) + " / " + num(ship.fighter_cap)],
      ["Shields", num(ship.shields) + " / " + num(ship.shield_cap)],
      ["Holds", num(Object.values(ship.cargo || {}).reduce((s, n) => s + Number(n || 0), 0)) + " / " + num(ship.holds)],
      ["Mines", num(mineCount)],
      ["Genesis", num(ship.genesis)],
      ["Probes", num(ship.ether_probes)],
      ["Photons", num(ship.photon_missiles)],
      ["Scanner", ship.scanner || "none"],
      ["Transwarp", tw.fitted || "none"],
    ];
    $("gear").innerHTML = rows.map((row) => "<dt>" + row[0] + "</dt><dd>" + row[1] + "</dd>").join("");
    const cargo = ship.cargo || {};
    $("holds").innerHTML = CARGO.map((row) =>
      '<div class="hold ' + row[2] + '"><b>' + row[1] + "</b><br>" + num(cargo[row[0]]) + "</div>"
    ).join("");
  }

  function paintHere(obs) {
    const sector = (obs && obs.sector) || {};
    document.querySelector("[data-testid=here-line]").textContent = "Warps";
    const row = $("warpRow");
    row.innerHTML = "";
    const warp = legalOf("warp");
    (sector.warps_out || []).forEach((sid, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = (i + 1) + ":" + sid;
      b.disabled = !(warp && warp.legal) || !state.awaiting;
      b.onclick = () => submit({ kind: "warp", args: { target: sid } });
      row.appendChild(b);
    });
  }

  function paintStatus(obs) {
    if (!obs) return;
    document.querySelector("[data-testid=status-line]").textContent =
      (obs.self_name || state.seat) +
      "   Sector " + ((obs.sector || {}).id ?? "—") +
      "   Turns " + num(obs.turns_remaining) +
      "   Credits " + num(obs.credits) +
      "   Align " + num(obs.alignment) +
      "   Exp " + num(obs.experience) +
      "   Day " + num(obs.day) +
      (obs.planet_landed != null ? "   Landed " + obs.planet_landed : "");
    document.querySelector("[data-testid=prompt-line]").textContent =
      "Command [TL=" + num(obs.turns_remaining) + "] (?=Help) :";
  }

  function fieldsOf(la) {
    const out = [];
    for (const [name, spec] of Object.entries(la.params || {})) {
      if (!spec || typeof spec !== "object" || !spec.type) continue;
      out.push({ name, spec });
    }
    return out;
  }
  function closeForm() { const f = $("prompt"); f.hidden = true; f.innerHTML = ""; }
  function openForm(kind) {
    const la = legalOf(kind);
    const form = $("prompt");
    form.innerHTML = "";
    form.hidden = false;
    const fields = la ? fieldsOf(la) : [];
    if (!fields.length) { submit({ kind, args: {} }); return; }
    fields.forEach((field) => {
      const label = document.createElement("label");
      label.textContent = field.name.replaceAll("_", " ");
      const spec = field.spec;
      let input;
      if (Array.isArray(spec.choices)) {
        input = document.createElement("select");
        spec.choices.forEach((choice) => {
          const o = document.createElement("option");
          o.value = choice;
          o.textContent = choice;
          input.appendChild(o);
        });
      } else {
        input = document.createElement("input");
        input.type = spec.type === "int" ? "number" : "text";
        if (spec.min != null) input.min = spec.min;
        if (spec.max != null) input.max = spec.max;
      }
      input.name = field.name;
      label.appendChild(input);
      form.appendChild(label);
    });
    const go = document.createElement("button");
    go.type = "submit";
    go.textContent = "Send";
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.textContent = "Cancel";
    cancel.onclick = closeForm;
    form.appendChild(go);
    form.appendChild(cancel);
    form.onsubmit = (ev) => {
      ev.preventDefault();
      const args = {};
      fields.forEach((field) => {
        const el = form.querySelector("[name=" + field.name + "]");
        if (!el || el.value === "") return;
        args[field.name] = field.spec.type === "int" ? Number(el.value) : el.value;
      });
      submit({ kind, args });
    };
  }

  function landKind() {
    if (state.obs && state.obs.planet_landed != null) return "liftoff";
    return "land_planet";
  }
  function paintKeys() {
    const bar = $("keys");
    bar.innerHTML = "";
    TOP.forEach((row) => {
      const kind = row[0] === "L" ? landKind() : row[1];
      const la = legalOf(kind);
      const b = document.createElement("button");
      b.type = "button";
      b.dataset.key = row[0];
      b.textContent = "<" + row[0] + "> " + (row[0] === "L" && kind === "liftoff" ? "Lift" : row[2]);
      b.disabled = !(la && la.legal) || !state.awaiting || state.busy;
      b.onclick = () => openForm(kind);
      bar.appendChild(b);
    });
    const help = document.createElement("button");
    help.type = "button";
    help.dataset.key = "?";
    help.textContent = "<?> More";
    help.onclick = () => { $("more").hidden = !$("more").hidden; };
    bar.appendChild(help);
    const more = $("more");
    more.innerHTML = "";
    const shown = new Set(TOP.map((row) => row[1]).concat(["land_planet", "liftoff"]));
    state.legal.filter((la) => la.legal && !shown.has(la.kind)).forEach((la) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = la.kind.replaceAll("_", " ");
      b.disabled = !state.awaiting || state.busy;
      b.onclick = () => openForm(la.kind);
      more.appendChild(b);
    });
  }

  async function submit(action) {
    if (!state.awaiting || state.busy) return;
    state.busy = true;
    paintKeys();
    try {
      await api("/" + state.seat + "/action", {
        method: "POST",
        body: JSON.stringify({ turn_seq: state.turnSeq, action }),
      });
      closeForm();
      $("err").textContent = "";
      state.awaiting = false;
    } catch (e) {
      $("err").textContent = String(e.message || e);
    } finally {
      state.busy = false;
      await refresh();
    }
  }

  async function fetchEvents(obs) {
    const r = await api("/" + state.seat + "/events?since=" + state.eventsSince + "&limit=300");
    if (state.mediaHistoryUntil == null) state.mediaHistoryUntil = typeof r.latest_seq === "number" ? r.latest_seq : 0;
    const catchingUp = !state.mediaCaughtUp && state.eventsSince < state.mediaHistoryUntil;
    const fresh = r.events || [];
    if (fresh.length) state.eventsSince = r.next_since;
    else state.mediaCaughtUp = true;
    if (window.TW2KMedia && fresh.length) {
      const hist = catchingUp ? fresh.filter((ev) => ev.seq <= state.mediaHistoryUntil) : [];
      const live = catchingUp ? fresh.filter((ev) => ev.seq > state.mediaHistoryUntil) : fresh;
      if (hist.length) window.TW2KMedia.onEvents(hist, obs, { history: true });
      if (live.length) window.TW2KMedia.onEvents(live, obs);
    }
    const tape = $("tape");
    fresh.slice(-6).forEach((ev) => {
      const line = document.createElement("div");
      line.textContent = (ev.kind || "note") + (ev.message ? "  " + ev.message : "");
      tape.prepend(line);
    });
    while (tape.children.length > 6) tape.removeChild(tape.lastChild);
  }

  function render(obs) {
    state.obs = obs;
    state.legal = obs.legal_actions || [];
    paintStatus(obs);
    paintHere(obs);
    paintShip(obs);
    paintScene(obs);
    paintKeys();
    if (window.TW2KViewport) window.TW2KViewport.update(obs);
  }

  async function refresh() {
    const st = await api("/" + state.seat + "/observation?wait_s=0&peek=1&format=both");
    state.awaiting = !!st.awaiting_input;
    state.turnSeq = st.turn_seq ?? state.turnSeq;
    if (st.video_custom === true && window.TW2KMedia && window.TW2KMedia.setVideoCustom) window.TW2KMedia.setVideoCustom(true);
    if (st.observation) render(st.observation);
    await fetchEvents(st.observation || state.obs);
    paintKeys();
  }

  async function connect() {
    state.seat = $("seatSelect").value.toUpperCase();
    state.token = $("tokenInput").value.trim();
    $("err").textContent = "";
    try {
      state.connected = true;
      await refresh();
    } catch (e) {
      state.connected = false;
      $("err").textContent = String(e.message || e);
    }
  }
  $("connectBtn").addEventListener("click", connect);
  document.addEventListener("keydown", (ev) => {
    const tag = (ev.target && ev.target.tagName) || "";
    if (/^(INPUT|SELECT|TEXTAREA)$/.test(tag) || ev.ctrlKey || ev.metaKey || ev.altKey) return;
    const key = ev.key.toUpperCase();
    const button = document.querySelector("#keys button[data-key='" + (ev.key === "?" ? "?" : key) + "']");
    if (!button || button.disabled) return;
    ev.preventDefault();
    button.click();
  });
  if (state.token) connect();
  setInterval(() => { if (state.connected && !state.busy) refresh().catch((e) => { $("err").textContent = String(e.message || e); }); }, 2000);
})();
