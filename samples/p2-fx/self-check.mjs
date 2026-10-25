/**
 * Node check for the P2 FX sample. Does not start the cockpit and does not
 * touch the hull source. WebGL stays off.
 */
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

const here = path.dirname(url.fileURLToPath(import.meta.url));
const root = path.resolve(here, "../..");
const modelSrc = fs.readFileSync(path.join(here, "fx-model.js"), "utf8");
const model = new Function("globalThis", `${modelSrc}\nreturn globalThis.P2FXModel;`)(globalThis);
const { FIGHTER_CASES, HULL_CLASS, HULL_SPEC, TIMING, markerCount, shotState, swatchOpacity } = model;
const failures = [];

function check(name, ok, detail) {
  if (!ok) failures.push(`${name}: ${detail}`);
  else console.log(`ok ${name}${detail ? ` — ${detail}` : ""}`);
}

const expected = { 0: 0, 1: 1, 50: 1, 99: 1, 100: 1, 101: 2, 250: 3, 1000: 10 };
for (const [bay, markers] of Object.entries(expected)) {
  const got = markerCount(Number(bay));
  check(`markers ${bay}`, got === markers, `got ${got}, want ${markers}`);
}

check("age 0", swatchOpacity(0) === 1, String(swatchOpacity(0)));
check("age 8s", swatchOpacity(TIMING.viewportAgeMs) === 0, String(swatchOpacity(TIMING.viewportAgeMs)));
check("age 6.4s", Math.abs(swatchOpacity(6400) - 0.2) < 1e-6, swatchOpacity(6400).toFixed(4));

for (const shot of ["fighters-0", "fighters-50", "fighters-100", "fighters-250", "fighters-1000", "mine-armid", "warp", "land-M", "land-U", "battle", "viewport-aged"]) {
  check(`shot ${shot}`, shotState(shot) != null, "");
}
check("unknown shot", shotState("nope") == null, "");
check("land-M class", shotState("land-H").planet === "H", "");

const sampleJs = fs.readFileSync(path.join(here, "sample.js"), "utf8");
const sampleHtml = fs.readFileSync(path.join(here, "index.html"), "utf8");
check(
  "no webgl context",
  !/getContext\(\s*["']webgl/.test(sampleJs + sampleHtml) && !/from\s+["']three["']/.test(sampleJs),
  "",
);
check("does not import cockpit", !/redesign\.js|hull-meshes\.mjs/.test(sampleJs), "");
check("loads hull script", sampleJs.includes("hull-meshes.js"), "");

const meshPath = path.join(root, "web/hull-meshes.js");
const meshSrc = fs.readFileSync(meshPath, "utf8");
const run = new Function("globalThis", `${meshSrc}\nreturn globalThis.TW2KHullMeshes;`);
const api = run(globalThis);
const ship = { class: HULL_CLASS, shields: 320, shield_cap: 400, fighters: 50, transwarp: { fitted: false } };
const faces = api.buildHullFaces(ship, HULL_SPEC);
const radius = api.hullRadius(faces);
check("faces", faces.length > 50, String(faces.length));
check("radius", radius > 40 && radius < 160, radius.toFixed(2));

function time(fn) {
  fn();
  const samples = [];
  for (let i = 0; i < 9; i++) {
    const t0 = performance.now();
    fn();
    samples.push(performance.now() - t0);
  }
  samples.sort((a, b) => a - b);
  return { median: samples[4], max: samples[8] };
}

api.escortSlots(10, faces, TIMING.fit, TIMING.yaw, TIMING.pitch);
api.projectFace(faces[0], TIMING.yaw, TIMING.pitch, TIMING.fit, TIMING.ox, TIMING.oy, 0, 1);

const rows = [];
for (const fighters of FIGHTER_CASES) {
  const asked = markerCount(fighters);
  const bake = time(() => api.escortSlots(asked, faces, TIMING.fit, TIMING.yaw, TIMING.pitch));
  const placed = asked < 1 ? 0 : api.escortSlots(asked, faces, TIMING.fit, TIMING.yaw, TIMING.pitch).length;
  rows.push({ fighters, markers: asked, placed, bake });
  check(`placed ${fighters}`, placed === asked, `${placed}/${asked} bake ${bake.median.toFixed(2)} ms`);
}

const project = time(() => {
  for (let i = 0; i < faces.length; i++) api.projectFace(faces[i], TIMING.yaw, TIMING.pitch, TIMING.fit, TIMING.ox, TIMING.oy, 0, 1);
});
const bake1000 = time(() => api.escortSlots(1000, faces, TIMING.stressFit, TIMING.yaw, TIMING.pitch));
const placed1000 = api.escortSlots(1000, faces, TIMING.stressFit, TIMING.yaw, TIMING.pitch).length;
check("1000 markers placed", placed1000 === 1000, `${placed1000} in ${bake1000.median.toFixed(2)} ms at fit ${TIMING.stressFit}`);

const perf = {
  hull: HULL_CLASS,
  faces: faces.length,
  radius: Number(radius.toFixed(2)),
  fit: TIMING.fit,
  engine: `node ${process.version}`,
  project,
  rows,
  markers1000: { asked: 1000, placed: placed1000, fit: TIMING.stressFit, bake: bake1000 },
  webgl: false,
};
fs.writeFileSync(path.join(here, "perf-node.json"), `${JSON.stringify(perf, null, 2)}\n`);
console.log(`wrote perf-node.json faces=${faces.length} radius=${radius.toFixed(2)} project=${project.median.toFixed(2)}ms`);

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}
