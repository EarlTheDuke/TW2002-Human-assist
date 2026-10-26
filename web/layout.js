/* cockpit-dashboard-custom-v1, extended by cockpit-custom-layout-v1.
 *
 * Trade Wars 2002 has no panel dashboard. A classic resizable client is
 * UNVERIFIED. With nothing saved, the stylesheet grid is left alone.
 * Font and zoom stay the controls from that first slice. This file does
 * not add a second pair.
 */
(function () {
  "use strict";
  const PANELS = [
    ["sectorReport", "Sector report"],
    ["nav", "Nav computer"],
    ["ship", "Ship"],
    ["context", "Here"],
    ["term", "Comms"],
  ];
  const ORDER = PANELS.map((row) => row[0]);
  const SLOTS = [
    { col: 1, row: 1 },
    { col: 2, row: 1 },
    { col: 3, row: 1 },
    { col: 1, row: 2, span: 2 },
    { col: 3, row: 2 },
  ];
  const DEFAULT_COLS = [1.15, 1, 0.95];
  const DEFAULT_ROWS = [1.35, 0.7];
  const deck = document.getElementById("deck");
  const menu = document.getElementById("layoutMenu");
  const list = document.getElementById("layoutList");
  const openBtn = document.getElementById("layoutOpen");
  if (!deck || !menu || !list || !openBtn) return;

  const wideQ = window.matchMedia("(min-width: 1101px)");
  const params = new URLSearchParams(location.search);
  let state = blank();
  let dragId = "";
  let menuDrag = false;

  function blank() {
    return { v: 1, order: ORDER.slice(), hidden: [], cols: null, rows: null, font: null, zoom: 1, mapBoost: 0 };
  }
  function gameId() {
    const match = (location.pathname || "").match(/\/g\/([^/]+)/);
    return match ? decodeURIComponent(match[1]) : "lobby";
  }
  function seatId() {
    const fromUrl = params.get("seat");
    const select = document.getElementById("seatSelect");
    return String(fromUrl || (select && select.value) || "P2").toUpperCase();
  }
  function storageKey() {
    return "tw2k-deck-v1:" + gameId() + ":" + seatId();
  }
  function wide() { return !!wideQ.matches; }
  function sameOrder(order) {
    return Array.isArray(order) && order.length === ORDER.length && ORDER.every((id, i) => order[i] === id);
  }
  function near(list, base) {
    return Array.isArray(list) && list.length === base.length && list.every((n, i) => Math.abs(Number(n) - base[i]) < 0.02);
  }
  function isBlank(data) {
    return sameOrder(data.order) && !data.hidden.length && !data.cols && !data.rows && !data.font && data.zoom === 1 && !data.mapBoost;
  }
  function clampTracks(value, base) {
    if (!Array.isArray(value) || value.length !== base.length) return null;
    const nums = value.map(Number);
    if (nums.some((n) => !Number.isFinite(n) || n < 0.25 || n > 6)) return null;
    return near(nums, base) ? null : nums;
  }
  function sanitize(data) {
    const next = blank();
    if (!data || data.v !== 1) return next;
    const incoming = Array.isArray(data.order) ? data.order.map((id) => (id === "viewport" ? "sectorReport" : id)) : [];
    const order = incoming.filter((id) => ORDER.indexOf(id) >= 0);
    ORDER.forEach((id) => { if (order.indexOf(id) < 0) order.push(id); });
    next.order = order.slice(0, ORDER.length);
    const hidden = Array.isArray(data.hidden) ? data.hidden.map((id) => (id === "viewport" ? "sectorReport" : id)) : [];
    next.hidden = ORDER.filter((id) => hidden.indexOf(id) >= 0);
    if (next.hidden.length >= ORDER.length) next.hidden = next.hidden.slice(0, ORDER.length - 1);
    next.cols = clampTracks(data.cols, DEFAULT_COLS);
    next.rows = clampTracks(data.rows, DEFAULT_ROWS);
    const font = Number(data.font);
    next.font = Number.isFinite(font) && font >= 12 && font <= 24 ? Math.round(font) : null;
    const zoom = Math.round(Number(data.zoom) * 10) / 10;
    next.zoom = Number.isFinite(zoom) && zoom >= 0.8 && zoom <= 1.5 ? zoom : 1;
    const boost = Number(data.mapBoost);
    next.mapBoost = Number.isFinite(boost) ? Math.max(0, Math.min(4, Math.round(boost))) : 0;
    return next;
  }
  function read() {
    try {
      const raw = localStorage.getItem(storageKey());
      if (!raw) return blank();
      return sanitize(JSON.parse(raw));
    } catch (e) {
      return blank();
    }
  }
  function write() {
    try {
      if (isBlank(state)) localStorage.removeItem(storageKey());
      else localStorage.setItem(storageKey(), JSON.stringify(state));
    } catch (e) { /* this browser keeps no layout */ }
    document.body.setAttribute("data-deck", isBlank(state) ? "default" : "custom");
  }

  function tracks(custom, fallback) {
    return (custom || fallback).slice();
  }
  function navSlot() {
    const navIndex = state.order.indexOf("nav");
    return SLOTS[navIndex >= 0 ? navIndex : 1];
  }
  function boostedCols(cols) {
    if (!state.mapBoost) return cols;
    const base = (cols || DEFAULT_COLS).slice();
    const slot = navSlot();
    const start = slot.col - 1;
    const span = slot.span || 1;
    for (let i = 0; i < span && start + i < base.length; i += 1) base[start + i] += state.mapBoost * 1.15;
    return base;
  }
  function boostedRows(rows) {
    if (!state.mapBoost) return rows;
    const base = (rows || DEFAULT_ROWS).slice();
    const idx = navSlot().row === 2 ? 1 : 0;
    base[idx] += state.mapBoost * 0.9;
    return base;
  }
  function apply() {
    const useGrid = wide();
    const customOrder = useGrid && !sameOrder(state.order);
    state.order.forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.hidden = state.hidden.indexOf(id) >= 0;
      if (!customOrder) {
        el.style.gridColumn = "";
        el.style.gridRow = "";
        return;
      }
      const slot = SLOTS[state.order.indexOf(id)];
      el.style.gridColumn = slot.span ? slot.col + " / span " + slot.span : String(slot.col);
      el.style.gridRow = String(slot.row);
    });
    const colTracks = useGrid ? boostedCols(state.cols) : null;
    const rowTracks = useGrid ? boostedRows(state.rows) : null;
    if (useGrid && (state.cols || state.mapBoost) && colTracks) deck.style.gridTemplateColumns = colTracks.map((n) => n.toFixed(4) + "fr").join(" ");
    else deck.style.gridTemplateColumns = "";
    if (useGrid && (state.rows || state.mapBoost) && rowTracks) {
      deck.style.gridTemplateRows = "minmax(0," + rowTracks[0].toFixed(4) + "fr) minmax(80px," + rowTracks[1].toFixed(4) + "fr)";
    } else deck.style.gridTemplateRows = "";
    document.body.setAttribute("data-map-boost", String(state.mapBoost || 0));
    if (state.font) {
      document.body.classList.add("deck-tuned");
      document.body.style.setProperty("--cockpit-font", state.font + "px");
    } else {
      document.body.classList.remove("deck-tuned");
      document.body.style.removeProperty("--cockpit-font");
    }
    if (state.zoom !== 1) document.body.style.zoom = String(state.zoom);
    else document.body.style.zoom = "";
    document.body.setAttribute("data-deck", isBlank(state) ? "default" : "custom");
    placeSplitters();
    refreshPanelMenus();
    if (!menuDrag) paintMenu();
  }

  function placeSplitters() {
    const nodes = deck.querySelectorAll(".splitter");
    if (!wide()) {
      nodes.forEach((node) => { node.hidden = true; });
      return;
    }
    const cols = getComputedStyle(deck).gridTemplateColumns.split(" ").map(parseFloat);
    const rows = getComputedStyle(deck).gridTemplateRows.split(" ").map(parseFloat);
    if (cols.length < 3 || rows.length < 2 || cols.some((n) => !Number.isFinite(n))) {
      nodes.forEach((node) => { node.hidden = true; });
      return;
    }
    const pad = 8;
    const gap = 8;
    let x = pad;
    cols.forEach((width, index) => {
      const node = deck.querySelector('.splitter[data-axis="col"][data-index="' + index + '"]');
      if (node && index < cols.length - 1) {
        node.hidden = false;
        node.style.left = (x + width) + "px";
        node.style.top = pad + "px";
        node.style.width = gap + "px";
        node.style.height = rows[0] + "px";
      }
      x += width + gap;
    });
    const row = deck.querySelector('.splitter[data-axis="row"][data-index="0"]');
    if (row) {
      row.hidden = false;
      row.style.left = pad + "px";
      row.style.top = (pad + rows[0]) + "px";
      row.style.height = gap + "px";
      row.style.width = Math.max(40, deck.clientWidth - pad * 2) + "px";
    }
  }

  function nudge(axis, index, deltaPx) {
    if (!wide()) return;
    const rect = deck.getBoundingClientRect();
    const base = axis === "col" ? tracks(state.cols, DEFAULT_COLS) : tracks(state.rows, DEFAULT_ROWS);
    const sum = base.reduce((total, n) => total + n, 0);
    const gaps = 8 * (base.length - 1);
    const pad = 16;
    const size = Math.max(200, (axis === "col" ? rect.width : rect.height) - pad - gaps);
    const px = base.map((n) => n / sum * size);
    const pair = px[index] + px[index + 1];
    const nextPx = px.slice();
    const low = Math.max(110, Math.min(pair - 110, px[index] + deltaPx));
    nextPx[index] = low;
    nextPx[index + 1] = pair - low;
    const next = nextPx.map((n) => n / nextPx.reduce((total, item) => total + item, 0) * sum);
    if (axis === "col") state.cols = near(next, DEFAULT_COLS) ? null : next;
    else state.rows = near(next, DEFAULT_ROWS) ? null : next;
    write();
    apply();
  }

  function splitter(axis, index, label) {
    const node = document.createElement("button");
    node.type = "button";
    node.className = "splitter " + (axis === "col" ? "v" : "h");
    node.dataset.axis = axis;
    node.dataset.index = String(index);
    node.dataset.testid = "splitter-" + axis + "-" + index;
    node.setAttribute("aria-label", label);
    node.hidden = true;
    let start = 0;
    let dragging = false;
    node.addEventListener("pointerdown", (ev) => {
      if (!wide() || ev.button > 0) return;
      dragging = true;
      start = axis === "col" ? ev.clientX : ev.clientY;
      try { node.setPointerCapture(ev.pointerId); } catch (e) { /* a synthetic pointer still moves */ }
      ev.preventDefault();
    });
    function endDrag() { dragging = false; }
    node.addEventListener("pointerup", endDrag);
    node.addEventListener("pointercancel", endDrag);
    node.addEventListener("pointermove", (ev) => {
      if (!dragging) return;
      const point = axis === "col" ? ev.clientX : ev.clientY;
      const delta = point - start;
      if (Math.abs(delta) < 1) return;
      start = point;
      nudge(axis, index, delta);
    });
    node.addEventListener("keydown", (ev) => {
      const step = ev.shiftKey ? 48 : 24;
      let delta = 0;
      if (axis === "col" && (ev.key === "ArrowRight" || ev.key === "ArrowLeft")) delta = ev.key === "ArrowRight" ? step : -step;
      if (axis === "row" && (ev.key === "ArrowDown" || ev.key === "ArrowUp")) delta = ev.key === "ArrowDown" ? step : -step;
      if (!delta) return;
      ev.preventDefault();
      ev.stopPropagation();
      nudge(axis, index, delta);
    });
    node.addEventListener("click", (ev) => { if (dragging) ev.preventDefault(); });
    deck.appendChild(node);
    return node;
  }

  splitter("col", 0, "Resize viewport and nav");
  splitter("col", 1, "Resize nav and ship");
  splitter("row", 0, "Resize the top and bottom rows");

  function move(id, dir) {
    if (!wide()) return;
    const index = state.order.indexOf(id);
    const next = index + dir;
    if (index < 0 || next < 0 || next >= state.order.length) return;
    const order = state.order.slice();
    const swap = order[index];
    order[index] = order[next];
    order[next] = swap;
    state.order = order;
    write();
    apply();
  }
  function toggle(id, show) {
    const hidden = state.hidden.filter((item) => item !== id);
    if (!show) hidden.push(id);
    if (hidden.length >= ORDER.length) return;
    state.hidden = hidden;
    write();
    apply();
  }
  function setFont(delta) {
    const base = wide() ? 15 : 12;
    const current = state.font || base;
    const next = Math.max(12, Math.min(24, current + delta));
    state.font = next === base ? null : next;
    write();
    apply();
  }
  function setZoom(delta) {
    const next = Math.round((state.zoom + delta) * 10) / 10;
    state.zoom = Math.max(0.8, Math.min(1.5, next));
    write();
    apply();
  }
  function setMap(delta) {
    state.mapBoost = Math.max(0, Math.min(4, (state.mapBoost || 0) + delta));
    write();
    apply();
  }
  const MAP_WORDS = ["Default", "Large", "Larger", "Huge", "Maximum"];
  function reset() {
    state = blank();
    try { localStorage.removeItem(storageKey()); } catch (e) { /* already clear */ }
    apply();
  }

  function paintMenu() {
    const fontRead = document.querySelector("[data-testid=font-readout]");
    const zoomRead = document.querySelector("[data-testid=zoom-readout]");
    const mapRead = document.querySelector("[data-testid=map-size]");
    if (fontRead) fontRead.textContent = state.font ? state.font + "px" : "Default";
    if (zoomRead) zoomRead.textContent = Math.round(state.zoom * 100) + "%";
    if (mapRead) mapRead.textContent = MAP_WORDS[state.mapBoost] || "Default";
    const canMove = wide();
    const lastVisible = state.hidden.length >= ORDER.length - 1;
    list.innerHTML = "";
    state.order.forEach((id, index) => {
      const name = (PANELS.find((row) => row[0] === id) || [id, id])[1];
      const row = document.createElement("div");
      row.className = "layout-row";
      row.dataset.panel = id;
      row.draggable = canMove;
      const shown = state.hidden.indexOf(id) < 0;
      row.innerHTML = '<button type="button" class="grip" data-grip="' + id + '" aria-label="Drag ' + name + '"' + (canMove ? "" : " hidden") + '>↕</button>'
        + '<label><input type="checkbox" data-testid="show-' + id + '"' + (shown ? " checked" : "") + '> ' + name + '</label>'
        + '<span class="layout-actions">'
        + '<button type="button" data-move="-1" data-testid="up-' + id + '"' + (canMove ? "" : " hidden") + (index === 0 ? " disabled" : "") + '>Move up</button>'
        + '<button type="button" data-move="1" data-testid="down-' + id + '"' + (canMove ? "" : " hidden") + (index === state.order.length - 1 ? " disabled" : "") + '>Move down</button>'
        + '<button type="button" data-testid="hide-' + id + '"' + (!shown || lastVisible ? " disabled" : "") + '>Hide</button>'
        + '<button type="button" data-testid="show-panel-' + id + '"' + (shown ? " disabled" : "") + '>Show</button>'
        + '</span>';
      row.querySelector("input").addEventListener("change", (ev) => toggle(id, ev.target.checked));
      row.querySelector("[data-testid=hide-" + id + "]").addEventListener("click", () => toggle(id, false));
      row.querySelector("[data-testid=show-panel-" + id + "]").addEventListener("click", () => toggle(id, true));
      row.querySelectorAll("[data-move]").forEach((button) => {
        button.addEventListener("click", () => move(id, Number(button.dataset.move)));
      });
      row.addEventListener("dragstart", (ev) => {
        dragId = id;
        if (ev.dataTransfer) ev.dataTransfer.setData("text/plain", id);
      });
      row.addEventListener("dragover", (ev) => { if (canMove) ev.preventDefault(); });
      row.addEventListener("drop", (ev) => {
        ev.preventDefault();
        const from = dragId || (ev.dataTransfer && ev.dataTransfer.getData("text/plain"));
        if (!from || from === id) return;
        const order = state.order.slice();
        const a = order.indexOf(from);
        const b = order.indexOf(id);
        if (a < 0 || b < 0) return;
        order.splice(a, 1);
        order.splice(b, 0, from);
        state.order = order;
        dragId = "";
        write();
        apply();
      });
      const grip = row.querySelector("[data-grip]");
      grip.addEventListener("pointerdown", (ev) => {
        if (!canMove) return;
        try { grip.setPointerCapture(ev.pointerId); } catch (err) { /* the row still accepts a drop */ }
        dragId = id;
        menuDrag = true;
        ev.preventDefault();
      });
      grip.addEventListener("pointerup", () => { menuDrag = false; paintMenu(); });
      grip.addEventListener("pointercancel", () => { menuDrag = false; paintMenu(); });
      grip.addEventListener("pointermove", (ev) => {
        if (!menuDrag || dragId !== id) return;
        const hit = document.elementFromPoint(ev.clientX, ev.clientY);
        const other = hit && hit.closest ? hit.closest(".layout-row") : null;
        if (!other || other.dataset.panel === id) return;
        const order = state.order.slice();
        const a = order.indexOf(id);
        const b = order.indexOf(other.dataset.panel);
        if (a < 0 || b < 0) return;
        order.splice(a, 1);
        order.splice(b, 0, id);
        state.order = order;
        write();
        apply();
        state.order.forEach((pid) => {
          const node = list.querySelector('.layout-row[data-panel="' + pid + '"]');
          if (node) list.appendChild(node);
        });
      });
      list.appendChild(row);
    });
  }

  function refreshPanelMenus() {
    const canMove = wide();
    const lastVisible = state.hidden.length >= ORDER.length - 1;
    PANELS.forEach((row) => {
      const id = row[0];
      const pop = document.querySelector('[data-testid="panel-menu-pop-' + id + '"]');
      const opener = document.querySelector('[data-testid="panel-menu-' + id + '"]');
      if (!pop) return;
      const shown = state.hidden.indexOf(id) < 0;
      const index = state.order.indexOf(id);
      const panel = document.getElementById(id);
      if (!shown) pop.hidden = true;
      if (opener) opener.hidden = !shown;
      pop.querySelector('[data-cmd="up"]').disabled = !canMove || index <= 0;
      pop.querySelector('[data-cmd="down"]').disabled = !canMove || index >= state.order.length - 1;
      pop.querySelector('[data-cmd="hide"]').disabled = !shown || lastVisible;
      pop.querySelector('[data-cmd="show"]').disabled = shown;
      const larger = pop.querySelector('[data-cmd="larger"]');
      const smaller = pop.querySelector('[data-cmd="smaller"]');
      if (larger) larger.disabled = state.mapBoost >= 4;
      if (smaller) smaller.disabled = !state.mapBoost;
      if (panel && panel.hidden) pop.hidden = true;
    });
    const larger = document.querySelector("[data-testid=map-larger]");
    const smaller = document.querySelector("[data-testid=map-smaller]");
    if (larger) larger.disabled = state.mapBoost >= 4;
    if (smaller) smaller.disabled = !state.mapBoost;
  }

  function placePop(button, pop) {
    const rect = button.getBoundingClientRect();
    pop.style.top = Math.max(4, Math.min(rect.bottom + 2, window.innerHeight - 180)) + "px";
    pop.style.left = Math.max(4, Math.min(rect.left, window.innerWidth - 168)) + "px";
  }

  function closePops(except) {
    document.querySelectorAll(".panel-menu").forEach((pop) => {
      if (pop !== except) pop.hidden = true;
    });
  }

  function mountPanelMenus() {
    PANELS.forEach((row) => {
      const id = row[0];
      const name = row[1];
      const panel = document.getElementById(id);
      if (!panel || panel.querySelector("[data-testid=panel-menu-" + id + "]")) return;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "panel-menu-open";
      button.dataset.testid = "panel-menu-" + id;
      button.textContent = "Panel";
      button.setAttribute("aria-haspopup", "menu");
      button.setAttribute("aria-label", name + " panel");
      const pop = document.createElement("div");
      pop.className = "panel-menu";
      pop.hidden = true;
      pop.dataset.testid = "panel-menu-pop-" + id;
      pop.setAttribute("role", "menu");
      pop.setAttribute("aria-label", name);
      const items = [
        ["up", "Move up"],
        ["down", "Move down"],
        ["hide", "Hide"],
        ["show", "Show"],
      ];
      if (id === "nav") items.push(["larger", "Larger map"], ["smaller", "Smaller map"]);
      items.forEach((item) => {
        const cmd = document.createElement("button");
        cmd.type = "button";
        cmd.dataset.cmd = item[0];
        cmd.textContent = item[1];
        cmd.setAttribute("role", "menuitem");
        pop.appendChild(cmd);
      });
      shieldKeys(button);
      shieldKeys(pop);
      pop.addEventListener("click", (ev) => {
        const cmd = ev.target && ev.target.closest ? ev.target.closest("[data-cmd]") : null;
        if (!cmd || cmd.disabled) return;
        ev.stopPropagation();
        if (cmd.dataset.cmd === "up") move(id, -1);
        else if (cmd.dataset.cmd === "down") move(id, 1);
        else if (cmd.dataset.cmd === "hide") toggle(id, false);
        else if (cmd.dataset.cmd === "show") toggle(id, true);
        else if (cmd.dataset.cmd === "larger") setMap(1);
        else if (cmd.dataset.cmd === "smaller") setMap(-1);
      });
      button.addEventListener("click", (ev) => {
        ev.stopPropagation();
        ev.preventDefault();
        const open = pop.hidden;
        closePops();
        pop.hidden = !open;
        if (!pop.hidden) placePop(button, pop);
      });
      panel.appendChild(button);
      document.body.appendChild(pop);
    });
  }

  function openMenu() { menu.hidden = false; paintMenu(); }
  function closeMenu() { menu.hidden = true; }
  openBtn.addEventListener("click", (ev) => { ev.stopPropagation(); menu.hidden ? openMenu() : closeMenu(); });
  document.querySelector("[data-testid=layout-close]").addEventListener("click", closeMenu);
  document.querySelector("[data-testid=layout-reset]").addEventListener("click", reset);
  document.querySelector("[data-testid=font-dec]").addEventListener("click", () => setFont(-1));
  document.querySelector("[data-testid=font-inc]").addEventListener("click", () => setFont(1));
  document.querySelector("[data-testid=zoom-dec]").addEventListener("click", () => setZoom(-0.1));
  document.querySelector("[data-testid=zoom-inc]").addEventListener("click", () => setZoom(0.1));
  const mapLarger = document.querySelector("[data-testid=map-larger]");
  const mapSmaller = document.querySelector("[data-testid=map-smaller]");
  if (mapLarger) mapLarger.addEventListener("click", () => setMap(1));
  if (mapSmaller) mapSmaller.addEventListener("click", () => setMap(-1));
  function shieldKeys(node) {
    node.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") return;
      ev.stopPropagation();
    });
  }
  shieldKeys(menu);
  document.addEventListener("keydown", (ev) => {
    if (ev.key !== "Escape") return;
    const openPop = document.querySelector(".panel-menu:not([hidden])");
    if (openPop) {
      openPop.hidden = true;
      ev.preventDefault();
      ev.stopPropagation();
      return;
    }
    if (!menu.hidden) {
      ev.preventDefault();
      ev.stopPropagation();
      closeMenu();
    }
  }, true);
  document.addEventListener("click", (ev) => {
    const target = ev.target;
    if (target && target.closest && (target.closest(".panel-menu") || target.closest(".panel-menu-open"))) return;
    closePops();
  });
  const seatSelect = document.getElementById("seatSelect");
  if (seatSelect) seatSelect.addEventListener("change", () => { state = read(); apply(); });
  window.addEventListener("resize", () => apply());
  if (window.ResizeObserver) new ResizeObserver(() => placeSplitters()).observe(deck);
  if (wideQ.addEventListener) wideQ.addEventListener("change", () => apply());

  mountPanelMenus();
  state = read();
  apply();
  window.__tw2kLayout = {
    key: storageKey,
    state: () => JSON.parse(JSON.stringify(state)),
    reset: reset,
  };
})();
