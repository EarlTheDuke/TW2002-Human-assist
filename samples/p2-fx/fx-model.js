(function (root) {
  "use strict";
/**
 * P2 FX research model. The cockpit does not import this file.
 * WebGL stays off. The P2 gate stays closed behind the batch-5 brick Pass.
 *
 * Marker rule, from the ship-stage pack: n < 1 draws nothing; otherwise
 * max(1, ceil(n / 100)). Each marker stands for 100 fighters.
 */

const HULL_CLASS = "merchant_cruiser";

const HULL_SPEC = {
  name: "Merchant Cruiser",
  kind: "arrow",
  len: 148,
  beam: 52,
  engines: 2,
  accent: "#7aa2ff",
  detail: "pods bridge",
};

const FIGHTER_DART = "M0,-3.4 L2.5,2.3 L0,0.55 L-2.5,2.3 Z";

const FIGHTER_CASES = [0, 50, 100, 250, 1000];

const TIMING = {
  orbitRadPerSec: 0.7,
  mineDropMs: 900,
  mineHoldMs: 1600,
  warpMs: 2000,
  warpCapture: 0.4,
  landFadeMs: 400,
  liftoffMs: 700,
  battleMs: 450,
  battleCapture: 0.5,
  viewportAgeMs: 8000,
  parkedScale: 0.45,
  landingPitchAdd: 0.08,
  yaw: 0.82,
  pitch: 0.5,
  fit: 1.12,
  stressFit: 0.72,
  ox: 200,
  oy: 124,
};

const PLANETS = {
  M: { name: "Earth", limb: "#0c3a6e", body: "#1a6b3a", band: "#f4fbff", kind: "earth" },
  K: { name: "Desert", limb: "#6a3a14", body: "#c47a2a", band: "#e7c48a", kind: "desert" },
  H: { name: "Volcanic", limb: "#2a1210", body: "#3a1814", band: "#ff4a1a", kind: "volcanic" },
  O: { name: "Oceanic", limb: "#063e44", body: "#0a6e78", band: "#b8fff2", kind: "ocean" },
  L: { name: "Mountainous", limb: "#3a3e48", body: "#6e7380", band: "#e8eef5", kind: "mountain" },
  C: { name: "Glacial", limb: "#4e86a8", body: "#d7f4ff", band: "#7eb8d4", kind: "glacial" },
  U: { name: "Gaseous", limb: "#3a2048", body: "#6a3a78", band: "#c9a24a", kind: "gas" },
};

/** Pictures the left viewport loses. Swatches fade across viewportAgeMs. */
const VIEWPORT_ROWS = [
  { id: "stars", swatch: "#9eb6d8", label: "#vpStars · sector_deep", tell: "idle" },
  { id: "fedspace", swatch: "#3a6ea5", label: "sector_fedspace", tell: "idle" },
  { id: "nebula", swatch: "#6a3a78", label: "sector_nebula", tell: "idle" },
  { id: "hazard", swatch: "#c45a2a", label: "sector_hazard", tell: "idle" },
  { id: "warp", swatch: "#d7f4ff", label: "#warpClip · move_warp", tell: "warp" },
  { id: "port", swatch: "#e0b15a", label: "sector_port_* · docked_port", tell: "port" },
  { id: "stardock", swatch: "#d7e4f5", label: "sector_stardock", tell: "port" },
  { id: "planet", swatch: "#1a6b3a", label: "planet_land · class stills", tell: "land" },
  { id: "mine", swatch: "#c47a2a", label: "combat_mine", tell: "mine" },
  { id: "combat", swatch: "#ff7a2a", label: "combat_alert · hit · incoming · miss · photon", tell: "battle" },
];

function markerCount(n) {
  const count = Math.max(0, Math.floor(Number(n) || 0));
  if (count < 1) return 0;
  return Math.max(1, Math.ceil(count / 100));
}

function ageUnit(clockMs, ageMs = TIMING.viewportAgeMs) {
  const t = Math.max(0, Number(clockMs) || 0) / ageMs;
  if (t <= 0) return 0;
  if (t >= 1) return 1;
  return t;
}

function swatchOpacity(clockMs) {
  return 1 - ageUnit(clockMs);
}

function shotState(name) {
  const base = {
    fighters: 50,
    tell: "idle",
    mineKind: "armid",
    mineQty: 8,
    planet: "M",
    phase: 1,
    clock: 0,
    motion: "still",
  };
  if (!name) return null;
  if (name === "bench") return { ...base, fighters: 1000, tell: "idle", bench: true };
  if (name.startsWith("fighters-")) {
    return { ...base, fighters: Number(name.slice("fighters-".length)), tell: "idle" };
  }
  if (name === "mine-armid") return { ...base, tell: "mine", mineKind: "armid", phase: 1 };
  if (name === "mine-limpet") return { ...base, tell: "mine", mineKind: "limpet", phase: 1 };
  if (name === "warp") return { ...base, tell: "warp", phase: TIMING.warpCapture, fighters: 250 };
  if (name.startsWith("land-")) {
    const planet = name.slice("land-".length);
    if (!PLANETS[planet]) return null;
    return { ...base, tell: "land", planet, phase: 1 };
  }
  if (name === "battle") return { ...base, tell: "battle", phase: TIMING.battleCapture, fighters: 250 };
  if (name === "viewport-fresh") return { ...base, tell: "idle", clock: 0, fighters: 50 };
  if (name === "viewport-aged") return { ...base, tell: "idle", clock: 6400, fighters: 50 };
  if (name === "viewport-gone") return { ...base, tell: "idle", clock: TIMING.viewportAgeMs, fighters: 50 };
  return null;
}

const STILL_SHOTS = [
  "fighters-0",
  "fighters-50",
  "fighters-100",
  "fighters-250",
  "fighters-1000",
  "mine-armid",
  "mine-limpet",
  "warp",
  "land-M",
  "land-K",
  "land-H",
  "land-O",
  "land-L",
  "land-C",
  "land-U",
  "battle",
  "viewport-fresh",
  "viewport-aged",
  "viewport-gone",
];

  root.P2FXModel = {
    HULL_CLASS: HULL_CLASS,
    HULL_SPEC: HULL_SPEC,
    FIGHTER_DART: FIGHTER_DART,
    FIGHTER_CASES: FIGHTER_CASES,
    TIMING: TIMING,
    PLANETS: PLANETS,
    VIEWPORT_ROWS: VIEWPORT_ROWS,
    markerCount: markerCount,
    ageUnit: ageUnit,
    swatchOpacity: swatchOpacity,
    shotState: shotState,
    STILL_SHOTS: STILL_SHOTS
  };
})(typeof globalThis !== "undefined" ? globalThis : this);
