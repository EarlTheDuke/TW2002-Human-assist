/**
 * Standalone P2 FX sample. Draws the landed Merchant Cruiser from
 * web/hull-meshes.js (buildHullFaces / projectFace / escortSlots).
 * Classic script so the page opens from disk. Not loaded by the cockpit.
 * WebGL stays off.
 */
const {
  FIGHTER_DART,
  HULL_CLASS,
  HULL_SPEC,
  PLANETS,
  TIMING,
  VIEWPORT_ROWS,
  ageUnit,
  markerCount,
  shotState,
  swatchOpacity,
} = globalThis.P2FXModel;

const OX = TIMING.ox;
const OY = TIMING.oy;
const SAMPLE_BASE = new URL("./", document.currentScript && document.currentScript.src || location.href);

const $ = (id) => document.getElementById(id);
const svg = $("stageSvg");

const state = {
  fighters: 50,
  tell: "idle",
  mineKind: "armid",
  mineQty: 8,
  planet: "M",
  phase: 1,
  clock: 0,
  motion: "live",
  spin: 0,
  lastT: null,
  playing: null,
};

let api = null;
let faces = [];
let radius = 0;
let slots = [];
let slotKey = "";

function loadMeshes() {
  if (globalThis.TW2KHullMeshes && globalThis.TW2KHullMeshes.buildHullFaces) {
    return Promise.resolve(globalThis.TW2KHullMeshes);
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = new URL("../../web/hull-meshes.js", SAMPLE_BASE).href;
    script.onload = () => {
      if (globalThis.TW2KHullMeshes && globalThis.TW2KHullMeshes.buildHullFaces) resolve(globalThis.TW2KHullMeshes);
      else reject(new Error("TW2KHullMeshes missing"));
    };
    script.onerror = () => reject(new Error("hull-meshes.js failed to load"));
    document.head.appendChild(script);
  });
}

function rotPoint(p, yaw, pitch) {
  const cy = Math.cos(yaw);
  const sy = Math.sin(yaw);
  const x1 = p[0] * cy + p[2] * sy;
  const z1 = -p[0] * sy + p[2] * cy;
  const cp = Math.cos(pitch);
  const sp = Math.sin(pitch);
  return [x1, p[1] * cp - z1 * sp, p[1] * sp + z1 * cp];
}

function project(p, yaw, pitch, fit) {
  const w = rotPoint([p[0] * fit, p[1] * fit, p[2] * fit], yaw, pitch);
  const s = 900 / (430 - w[2]);
  return { x: OX + w[0] * s, y: OY - w[1] * s, z: w[2], s };
}

function pose() {
  const land = state.tell === "land" ? TIMING.landingPitchAdd * Math.max(0, Math.min(1, state.phase)) : 0;
  return { yaw: TIMING.yaw, pitch: TIMING.pitch + land, fit: TIMING.fit };
}

function shipRecord() {
  return {
    class: HULL_CLASS,
    shields: 320,
    shield_cap: 400,
    fighters: state.fighters,
    transwarp: { fitted: false },
  };
}

function ensureSlots() {
  const cam = pose();
  const markers = markerCount(state.fighters);
  const key = [markers, cam.fit, cam.yaw.toFixed(3), cam.pitch.toFixed(3), faces.length].join("|");
  if (key === slotKey) return;
  slotKey = key;
  const t0 = performance.now();
  slots = markers < 1 ? [] : api.escortSlots(markers, faces, cam.fit, cam.yaw, cam.pitch);
  state.lastBakeMs = performance.now() - t0;
}

function starfield() {
  let seed = 77;
  const rnd = () => (seed = (seed * 9301 + 49297) % 233280) / 233280;
  let html = "";
  const ink = ["#9eb6d8", "#d5e4ff", "#f0e2b0", "#c9fff2"];
  for (let i = 0; i < 42; i++) {
    const x = (rnd() * 388 + 6).toFixed(1);
    const y = (rnd() * 246 + 6).toFixed(1);
    const r = (rnd() * 0.9 + 0.25).toFixed(2);
    html += `<circle cx="${x}" cy="${y}" r="${r}" fill="${ink[i % ink.length]}" opacity="${(0.28 + rnd() * 0.45).toFixed(2)}"/>`;
  }
  return html;
}

function paintHull(cam, pulse) {
  const drawn = [];
  for (let i = 0; i < faces.length; i++) {
    const face = api.projectFace(faces[i], cam.yaw, cam.pitch, cam.fit, OX, OY, 0, pulse);
    if (face) drawn.push(face);
  }
  drawn.sort((a, b) => a.depth - b.depth);
  return drawn.map((camFace) => {
    return `<polygon points="${camFace.points}" fill="${camFace.fill}" opacity="${camFace.opacity}" stroke="rgba(6,10,20,0.35)" stroke-width="0.45" stroke-linejoin="round"/>`;
  }).join("");
}

function paintMarkers(cam, spin, scaleMul) {
  const back = [];
  const front = [];
  for (let i = 0; i < slots.length; i++) {
    const slot = slots[i];
    const cs = Math.cos(spin);
    const sn = Math.sin(spin);
    const x0 = slot.x * cs + slot.z * sn;
    const z0 = -slot.x * sn + slot.z * cs;
    const y0 = slot.y;
    const rad = Math.hypot(x0, z0) || 1;
    const here = project([x0, y0, z0], cam.yaw, cam.pitch, cam.fit);
    const ahead = project([x0 - (z0 / rad) * 8, y0, z0 + (x0 / rad) * 8], cam.yaw, cam.pitch, cam.fit);
    const rot = Math.atan2(ahead.y - here.y, ahead.x - here.x) * 180 / Math.PI + 90;
    const scale = Math.max(0.55, Math.min(1.15, here.s / 2.15)) * scaleMul;
    const path = `<path data-testid="fighter-triangle" d="${FIGHTER_DART}" fill="#ff2a2a" stroke="#ff8888" stroke-width="0.4" transform="translate(${here.x.toFixed(1)} ${here.y.toFixed(1)}) rotate(${rot.toFixed(1)}) scale(${scale.toFixed(2)})"/>`;
    (here.z >= 0 ? front : back).push(path);
  }
  return { back: back.join(""), front: front.join("") };
}

function mineWorld(i, count, phase) {
  const spread = (i - (count - 1) / 2) * 7;
  // Aft of the bells, lifted so the drop stays inside the 400x260 frame.
  const end = [-64, 16 - (i % 2) * 7, spread];
  const start = [-28, 10, spread * 0.35];
  const t = Math.max(0, Math.min(1, phase));
  return [
    start[0] + (end[0] - start[0]) * t,
    start[1] + (end[1] - start[1]) * t,
    start[2] + (end[2] - start[2]) * t,
  ];
}

function paintMines(cam) {
  if (state.tell !== "mine") return { body: "", label: "" };
  const shown = Math.min(Math.max(1, Math.floor(state.mineQty) || 1), 6);
  const parts = [];
  let sx = 0;
  let sy = 0;
  let n = 0;
  for (let i = 0; i < shown; i++) {
    const p = mineWorld(i, shown, state.phase);
    const c = project(p, cam.yaw, cam.pitch, cam.fit);
    sx += c.x;
    sy += c.y;
    n += 1;
    if (state.mineKind === "limpet") {
      const ring = [];
      for (let k = 0; k < 10; k++) {
        const a = (k / 10) * Math.PI * 2;
        const q = project([p[0] + Math.cos(a) * 3.6, p[1], p[2] + Math.sin(a) * 3.6], cam.yaw, cam.pitch, cam.fit);
        ring.push(`${q.x.toFixed(1)},${q.y.toFixed(1)}`);
      }
      parts.push(`<polygon data-testid="mine-limpet" points="${ring.join(" ")}" fill="#8a5a18" stroke="#e0b15a" stroke-width="0.7" opacity="0.95"/>`);
    } else {
      let spikes = "";
      for (let k = 0; k < 8; k++) {
        const a = (k / 8) * Math.PI * 2;
        const q = project([
          p[0] + Math.cos(a) * 4.2,
          p[1] + Math.sin(a) * 4.2,
          p[2],
        ], cam.yaw, cam.pitch, cam.fit);
        spikes += `<line x1="${c.x.toFixed(1)}" y1="${c.y.toFixed(1)}" x2="${q.x.toFixed(1)}" y2="${q.y.toFixed(1)}" stroke="#e0b15a" stroke-width="0.8"/>`;
      }
      parts.push(`<g data-testid="mine-armid">${spikes}<circle cx="${c.x.toFixed(1)}" cy="${c.y.toFixed(1)}" r="2.5" fill="#8a5a18" stroke="#e0b15a" stroke-width="0.6"/></g>`);
    }
  }
  const labelY = Math.min(246, Math.max(14, sy / n - 16));
  const label = n
    ? `<text data-testid="mine-qty" x="${(sx / n).toFixed(1)}" y="${labelY.toFixed(1)}" text-anchor="middle" fill="#e0b15a" font-size="11" font-family="ui-sans-serif, system-ui, sans-serif">${state.mineQty} ${state.mineKind}</text>`
    : "";
  return { body: parts.join(""), label };
}

function planetDisc() {
  if (state.tell !== "land") return { html: "", opacity: "0" };
  const planet = PLANETS[state.planet] || PLANETS.M;
  const fade = Math.max(0, Math.min(1, state.phase));
  const cx = 158;
  const cy = 156;
  const r = 78;
  let extra = "";
  if (planet.kind === "earth") {
    extra = `<ellipse cx="${cx - 8}" cy="${cy - 6}" rx="34" ry="16" fill="${planet.body}" opacity="0.95"/><ellipse cx="${cx + 6}" cy="${cy + 10}" rx="46" ry="9" fill="${planet.band}" opacity="0.8"/>`;
  } else if (planet.kind === "desert") {
    extra = `<ellipse cx="${cx}" cy="${cy + 8}" rx="50" ry="10" fill="${planet.band}" opacity="0.55"/>`;
  } else if (planet.kind === "volcanic") {
    extra = `<path d="M${cx - 52} ${cy - 8} L${cx - 36} ${cy + 14} L${cx - 22} ${cy - 2}" fill="none" stroke="${planet.band}" stroke-width="2.2"/><path d="M${cx - 44} ${cy + 16} L${cx - 28} ${cy + 28}" fill="none" stroke="${planet.band}" stroke-width="1.6"/>`;
  } else if (planet.kind === "ocean") {
    extra = `<circle cx="${cx}" cy="${cy}" r="${r - 6}" fill="none" stroke="${planet.band}" stroke-width="3" opacity="0.85"/>`;
  } else if (planet.kind === "mountain") {
    extra = `<ellipse cx="${cx}" cy="${cy - 28}" rx="36" ry="14" fill="${planet.band}" opacity="0.9"/>`;
  } else if (planet.kind === "glacial") {
    extra = `<ellipse cx="${cx - 10}" cy="${cy + 4}" rx="28" ry="12" fill="#ffffff" opacity="0.55"/>`;
  } else if (planet.kind === "gas") {
    extra = `<ellipse cx="${cx}" cy="${cy - 24}" rx="70" ry="8" fill="${planet.band}" opacity="0.85"/><ellipse cx="${cx}" cy="${cy}" rx="74" ry="7" fill="${planet.limb}" opacity="0.9"/><ellipse cx="${cx}" cy="${cy + 22}" rx="64" ry="8" fill="${planet.band}" opacity="0.7"/>`;
  }
  return {
    html: `<g data-planet="${state.planet}">
      <circle cx="${cx}" cy="${cy}" r="${r}" fill="${planet.limb}"/>
      <circle cx="${cx}" cy="${cy}" r="${r - 10}" fill="${planet.body}"/>
      ${extra}
    </g>`,
    opacity: fade.toFixed(2),
  };
}

function warpStreaks() {
  if (state.tell !== "warp") return { html: "", opacity: "0" };
  const phase = state.phase;
  const fadeIn = Math.max(0, Math.min(1, phase / 0.15));
  const fadeOut = Math.max(0, Math.min(1, (1 - phase) / 0.15));
  const opacity = Math.min(fadeIn, fadeOut, 1);
  let lines = "";
  for (let i = 0; i < 16; i++) {
    const y = 16 + i * 14.5;
    const x = ((i * 37) % 80) + phase * 70;
    lines += `<line x1="${x.toFixed(1)}" y1="${y}" x2="${(x + 54).toFixed(1)}" y2="${y - 2}" stroke="#d7f4ff" stroke-width="${i % 4 === 0 ? 1.4 : 0.7}" opacity="${(0.35 + (i % 3) * 0.15).toFixed(2)}"/>`;
  }
  return { html: lines, opacity: opacity.toFixed(2) };
}

function shieldFlare(cam) {
  const battle = state.tell === "battle";
  const pulse = battle ? Math.sin(Math.max(0, Math.min(1, state.phase)) * Math.PI) : 0;
  const frac = 320 / 400;
  const opacity = battle ? (0.25 + pulse * 0.7).toFixed(2) : (0.18 + frac * 0.25).toFixed(2);
  const width = battle ? (1.4 + pulse * 2.4).toFixed(1) : (1 + frac * 1.4).toFixed(1);
  return `<ellipse data-testid="shield-bubble" cx="${OX}" cy="${OY}" rx="${(78 * cam.fit).toFixed(1)}" ry="${(46 * cam.fit).toFixed(1)}" fill="none" stroke="#b8fbff" stroke-width="${width}" stroke-dasharray="5 4" opacity="${opacity}"/>`;
}

function battleStreak() {
  if (state.tell !== "battle") return "";
  const amp = Math.sin(Math.max(0, Math.min(1, state.phase)) * Math.PI);
  return `<g data-testid="battle-streak" opacity="${amp.toFixed(2)}">
    <line x1="36" y1="48" x2="364" y2="214" stroke="#ff7a2a" stroke-width="7" stroke-linecap="round"/>
    <line x1="36" y1="48" x2="364" y2="214" stroke="#fff6e8" stroke-width="2.2" stroke-linecap="round"/>
  </g>`;
}

function landingGear(cam) {
  if (state.tell !== "land") return "";
  const pairs = [
    [[-6, -14, -8], [-6, -24, -8]],
    [[16, -14, 8], [16, -24, 8]],
  ];
  return pairs.map((pair) => {
    const a = project(pair[0], cam.yaw, cam.pitch, cam.fit);
    const b = project(pair[1], cam.yaw, cam.pitch, cam.fit);
    return `<line data-testid="landing-gear" x1="${a.x.toFixed(1)}" y1="${a.y.toFixed(1)}" x2="${b.x.toFixed(1)}" y2="${b.y.toFixed(1)}" stroke="#c5d4ea" stroke-width="1.4" stroke-linecap="round"/>`;
  }).join("");
}

function markerScale() {
  if (state.tell === "warp") {
    const tucked = Math.max(0, Math.min(1, state.phase / 0.2));
    const release = Math.max(0, Math.min(1, (state.phase - 0.8) / 0.2));
    const park = TIMING.parkedScale + (1 - TIMING.parkedScale) * release;
    return 1 - tucked * (1 - park);
  }
  if (state.tell === "battle") {
    return 1 + 0.35 * Math.sin(Math.max(0, Math.min(1, state.phase)) * Math.PI);
  }
  return 1;
}

function paint() {
  ensureSlots();
  const cam = pose();
  const pulse = state.tell === "land" ? 0.15 : 1;
  const spin = state.motion === "live" && state.tell === "idle" ? state.spin : 0;
  const markers = paintMarkers(cam, spin, markerScale());
  const mines = paintMines(cam);
  const disc = planetDisc();
  const streaks = warpStreaks();
  const gasDip = state.tell === "land" && (PLANETS[state.planet] || {}).kind === "gas" && state.phase > 0;
  const dip = gasDip ? "translate(0 10)" : "";
  if (!svg.dataset.stars) {
    svg.querySelector("[data-testid=starfield]").innerHTML = starfield();
    svg.dataset.stars = "1";
  }
  const discNode = svg.querySelector("[data-testid=planet-disc]");
  discNode.innerHTML = disc.html;
  discNode.setAttribute("opacity", disc.opacity);
  discNode.setAttribute("clip-path", "url(#planetClip)");
  const streakNode = svg.querySelector("[data-testid=warp-streaks]");
  streakNode.innerHTML = streaks.html;
  streakNode.setAttribute("opacity", streaks.opacity);
  svg.querySelector("[data-testid=fighter-back]").innerHTML = markers.back;
  svg.querySelector("[data-testid=ship-body]").innerHTML = paintHull(cam, pulse);
  svg.querySelector("[data-testid=landing-gear]").innerHTML = landingGear(cam);
  svg.querySelector("[data-testid=shield-flare]").innerHTML = shieldFlare(cam);
  svg.querySelector("[data-testid=mines]").innerHTML = mines.body;
  svg.querySelector("[data-testid=fighter-front]").innerHTML = markers.front;
  svg.querySelector("[data-testid=battle-streak]").innerHTML = battleStreak();
  svg.querySelector("[data-testid=mine-label]").innerHTML = mines.label;
  ["fighter-back", "ship-body", "landing-gear", "shield-flare", "fighter-front"].forEach((id) => {
    svg.querySelector(`[data-testid=${id}]`).setAttribute("transform", dip);
  });
  const markersAsked = markerCount(state.fighters);
  svg.setAttribute("data-hull", HULL_CLASS);
  svg.setAttribute("data-fighters", String(Math.max(0, Math.floor(Number(state.fighters) || 0))));
  svg.setAttribute("data-markers", String(markersAsked));
  svg.setAttribute("data-placed", String(slots.length));
  svg.setAttribute("data-tell", state.tell);
  svg.setAttribute("data-planet", state.tell === "land" ? state.planet : "");
  svg.setAttribute("data-mine-kind", state.tell === "mine" ? state.mineKind : "");
  svg.setAttribute("data-clock", String(state.clock));
  svg.setAttribute("data-faces", String(faces.length));
  svg.setAttribute("data-radius", radius.toFixed(1));
  svg.setAttribute("data-marker-rule", "n<1 none; else max(1, ceil(n/100)); each marker = 100 fighters");
  svg.setAttribute("data-webgl", "off");
  paintViewport();
  paintReadout(markersAsked);
}

function swatchGraphic(row) {
  const c = row.swatch;
  if (row.id === "warp") {
    return `<svg viewBox="0 0 44 22"><line x1="4" y1="6" x2="30" y2="6" stroke="${c}" stroke-width="1.2"/><line x1="8" y1="12" x2="40" y2="11" stroke="${c}" stroke-width="1.2"/><line x1="2" y1="17" x2="24" y2="16" stroke="${c}" stroke-width="1.2"/></svg>`;
  }
  if (row.id === "planet" || row.id === "stardock") {
    return `<svg viewBox="0 0 44 22"><circle cx="14" cy="11" r="7" fill="${c}"/></svg>`;
  }
  if (row.id === "mine") {
    return `<svg viewBox="0 0 44 22"><circle cx="16" cy="11" r="3" fill="${c}"/><line x1="16" y1="5" x2="16" y2="17" stroke="${c}" stroke-width="1"/><line x1="10" y1="11" x2="22" y2="11" stroke="${c}" stroke-width="1"/></svg>`;
  }
  if (row.id === "combat") {
    return `<svg viewBox="0 0 44 22"><line x1="6" y1="4" x2="36" y2="18" stroke="${c}" stroke-width="2"/></svg>`;
  }
  return `<svg viewBox="0 0 44 22"><circle cx="8" cy="6" r="1" fill="${c}"/><circle cx="18" cy="14" r="1.2" fill="${c}"/><circle cx="30" cy="8" r="0.8" fill="${c}"/></svg>`;
}

function paintViewport() {
  const list = $("viewportList");
  const unit = ageUnit(state.clock);
  const opacity = swatchOpacity(state.clock);
  const html = VIEWPORT_ROWS.map((row) => {
    const gone = unit >= 1;
    const age = (Math.max(0, state.clock) / 1000).toFixed(1);
    const status = gone ? "aged out" : `${age}s`;
    return `<li class="${gone ? "gone" : ""}" data-viewport="${row.id}" data-age="${unit.toFixed(3)}">
      <span class="swatch" style="opacity:${opacity.toFixed(3)}">${swatchGraphic(row)}</span>
      <span class="label">${row.label}</span>
      <span class="age">${status}</span>
    </li>`;
  }).join("");
  if (list.dataset.html !== html) {
    list.dataset.html = html;
    list.innerHTML = html;
  }
}

function paintReadout(markersAsked) {
  const partial = state.fighters > 0 && state.fighters % 100 !== 0;
  const planet = state.tell === "land" ? ` · ${state.planet} ${PLANETS[state.planet].name}` : "";
  const mine = state.tell === "mine"
    ? ` · ${state.mineKind} qty ${state.mineQty}, drawn ${Math.min(state.mineQty, 6)}`
    : "";
  $("readout").innerHTML = `<b>${HULL_SPEC.name}</b> · bay ${state.fighters} · markers ${markersAsked} (placed ${slots.length}) · each marker = 100 fighters${partial ? " · last marker is a partial hundred" : ""}${planet}${mine} · viewport ${(state.clock / 1000).toFixed(1)}s / ${(TIMING.viewportAgeMs / 1000).toFixed(0)}s · faces ${faces.length} · radius ${radius.toFixed(1)}`;
  document.querySelectorAll("[data-fighters]").forEach((btn) => {
    btn.setAttribute("aria-pressed", String(Number(btn.dataset.fighters) === Number(state.fighters) && state.tell === "idle"));
  });
  document.querySelectorAll("[data-tell]").forEach((btn) => {
    btn.setAttribute("aria-pressed", String(btn.dataset.tell === state.tell));
  });
  $("motion").setAttribute("aria-pressed", state.motion === "live" ? "true" : "false");
  $("motion").textContent = state.motion === "live" ? "Live orbit" : "Still";
  $("fighterInput").value = String(state.fighters);
  $("clock").value = String(state.clock);
  $("mineKind").value = state.mineKind;
  $("mineQty").value = String(state.mineQty);
  $("planet").value = state.planet;
}

function applyFighters(n) {
  state.fighters = Math.max(0, Math.floor(Number(n) || 0));
  slotKey = "";
}

function setTell(tell) {
  state.playing = null;
  state.tell = tell;
  state.phase = tell === "warp" ? TIMING.warpCapture : tell === "battle" ? TIMING.battleCapture : 1;
  slotKey = "";
}

function playTell() {
  const dur = {
    mine: TIMING.mineDropMs,
    warp: TIMING.warpMs,
    land: TIMING.landFadeMs,
    battle: TIMING.battleMs,
  }[state.tell];
  if (!dur) return;
  state.playing = { from: 0, to: 1, dur, started: performance.now(), after: "hold" };
}

function playLiftoff() {
  if (state.tell !== "land") setTell("land");
  state.phase = 1;
  state.playing = { from: 1, to: 0, dur: TIMING.liftoffMs, started: performance.now(), after: "idle" };
}

function loop(now) {
  if (state.playing) {
    const t = Math.max(0, Math.min(1, (now - state.playing.started) / state.playing.dur));
    state.phase = state.playing.from + (state.playing.to - state.playing.from) * t;
    if (t >= 1) {
      const after = state.playing.after;
      state.playing = null;
      if (after === "idle") {
        state.tell = "idle";
        state.phase = 1;
        slotKey = "";
      } else if (state.tell === "warp") state.phase = TIMING.warpCapture;
      else if (state.tell === "battle") state.phase = TIMING.battleCapture;
      else state.phase = 1;
    }
  } else if (state.motion === "live" && state.tell === "idle") {
    if (state.lastT != null) {
      const dt = Math.min(0.05, Math.max(0, (now - state.lastT) / 1000));
      state.spin += dt * TIMING.orbitRadPerSec;
    }
    state.lastT = now;
  }
  paint();
  if (state.playing || (state.motion === "live" && state.tell === "idle" && !shotMode)) {
    requestAnimationFrame(loop);
  }
}

function kick() {
  paint();
  if (!shotMode && (state.playing || (state.motion === "live" && state.tell === "idle"))) {
    state.lastT = null;
    requestAnimationFrame(loop);
  }
}

function median(samples) {
  const copy = samples.slice().sort((a, b) => a - b);
  return copy[Math.floor(copy.length / 2)];
}

function bench() {
  const fit = TIMING.fit;
  const yaw = TIMING.yaw;
  const pitch = TIMING.pitch;
  const time = (fn) => {
    const samples = [];
    fn();
    for (let i = 0; i < 9; i++) {
      const t0 = performance.now();
      fn();
      samples.push(performance.now() - t0);
    }
    samples.sort((a, b) => a - b);
    return { median: samples[4], max: samples[8] };
  };
  const project = time(() => {
    for (let i = 0; i < faces.length; i++) api.projectFace(faces[i], yaw, pitch, fit, OX, OY, 0, 1);
  });
  const bake10 = time(() => api.escortSlots(10, faces, fit, yaw, pitch));
  const bake1000 = time(() => api.escortSlots(1000, faces, TIMING.stressFit, yaw, pitch));
  const placed1000 = api.escortSlots(1000, faces, TIMING.stressFit, yaw, pitch).length;
  return {
    faces: faces.length,
    radius: Number(radius.toFixed(2)),
    project,
    bake10,
    bake1000,
    placed1000,
    engine: "browser",
  };
}

function fillPlanets() {
  const select = $("planet");
  select.innerHTML = Object.entries(PLANETS).map(([key, planet]) => {
    return `<option value="${key}">${key} ${planet.name}</option>`;
  }).join("");
}

function bind() {
  document.body.addEventListener("click", (ev) => {
    const fighter = ev.target.closest("[data-fighters]");
    if (fighter) {
      applyFighters(fighter.dataset.fighters);
      setTell("idle");
      kick();
      return;
    }
    const tell = ev.target.closest("[data-tell]");
    if (tell) {
      setTell(tell.dataset.tell);
      kick();
      return;
    }
    const clock = ev.target.closest("[data-clock]");
    if (clock) {
      state.clock = Number(clock.dataset.clock);
      paint();
    }
  });
  $("fighterInput").addEventListener("change", () => {
    applyFighters($("fighterInput").value);
    kick();
  });
  $("mineKind").addEventListener("change", () => {
    state.mineKind = $("mineKind").value;
    if (state.tell === "mine") paint();
  });
  $("mineQty").addEventListener("change", () => {
    state.mineQty = Math.max(1, Math.floor(Number($("mineQty").value) || 1));
    if (state.tell === "mine") paint();
  });
  $("planet").addEventListener("change", () => {
    state.planet = $("planet").value;
    if (state.tell !== "land") setTell("land");
    kick();
  });
  $("clock").addEventListener("input", () => {
    state.clock = Number($("clock").value);
    paint();
  });
  $("motion").addEventListener("click", () => {
    state.motion = state.motion === "live" ? "still" : "live";
    state.spin = 0;
    kick();
  });
  $("play").addEventListener("click", () => {
    playTell();
    kick();
  });
  $("liftoff").addEventListener("click", () => {
    playLiftoff();
    kick();
  });
  $("skip").addEventListener("click", () => {
    setTell("idle");
    kick();
  });
}

let shotMode = false;

async function main() {
  fillPlanets();
  bind();
  api = await loadMeshes();
  faces = api.buildHullFaces(shipRecord(), HULL_SPEC);
  radius = api.hullRadius(faces);
  const shot = shotState(new URLSearchParams(location.search).get("shot"));
  if (shot) {
    shotMode = true;
    state.fighters = shot.fighters;
    state.tell = shot.tell;
    state.mineKind = shot.mineKind;
    state.mineQty = shot.mineQty;
    state.planet = shot.planet;
    state.phase = shot.phase;
    state.clock = shot.clock;
    state.motion = "still";
  }
  paint();
  const numbers = bench();
  $("perf").textContent = `perf · project ${numbers.project.median.toFixed(2)} ms median · 10-marker bake ${numbers.bake10.median.toFixed(2)} ms · 1000-marker bake ${numbers.bake1000.median.toFixed(2)} ms (${numbers.placed1000} placed at fit ${TIMING.stressFit})`;
  svg.setAttribute("data-ready", "1");
  const benchNode = document.createElement("pre");
  benchNode.id = "bench";
  benchNode.hidden = true;
  benchNode.textContent = JSON.stringify(numbers);
  document.body.appendChild(benchNode);
  if (!shotMode && state.motion === "live") requestAnimationFrame(loop);
  globalThis.P2FX = { markerCount, state, bench, TIMING, numbers };
}

main().catch((err) => {
  $("readout").textContent = String(err && err.message ? err.message : err);
});
