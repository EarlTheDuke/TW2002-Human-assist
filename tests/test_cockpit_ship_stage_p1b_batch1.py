"""P1b batch-1 remainder: Escape Pod and T'Khasi Orion on the shared SVG mesh."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MESHES = ROOT / "web" / "hull-meshes.js"


def _report() -> dict:
    script = r"""
import crypto from "node:crypto";
import api from "./web/hull-meshes.mjs";

function build(cls, accent, engines, detail, tw) {
  return api.buildHullFaces(
    { class: cls, transwarp: { fitted: !!tw } },
    { accent, detail, engines, name: cls }
  );
}
function hashPts(faces) {
  const body = JSON.stringify(faces.map((f) => f.pts.map((p) => p.map((n) => Math.round(n * 1000) / 1000))));
  return crypto.createHash("sha256").update(body).digest("hex").slice(0, 16);
}
function spanOf(faces) {
  const min = [1e9, 1e9, 1e9], max = [-1e9, -1e9, -1e9];
  for (const face of faces) for (const p of face.pts) {
    for (let i = 0; i < 3; i++) {
      if (p[i] < min[i]) min[i] = p[i];
      if (p[i] > max[i]) max[i] = p[i];
    }
  }
  return {
    min: min.map((v) => Math.round(v * 10) / 10),
    max: max.map((v) => Math.round(v * 10) / 10),
    size: max.map((v, i) => Math.round((v - min[i]) * 10) / 10),
    r: Math.round(api.hullRadius(faces) * 10) / 10,
  };
}
function meanFill(faces, pred, damage) {
  const acc = [0, 0, 0];
  let n = 0;
  const yaws = [0.82, 1.35, -1.35, 0.2, 2.4];
  const pitches = [0.5, 0.18, 0.2, 0.9, 0.35];
  for (let k = 0; k < yaws.length; k++) {
    for (const face of faces) {
      if (!pred(face)) continue;
      const cam = api.projectFace(face, yaws[k], pitches[k], 1, 200, 124, damage, 1);
      if (!cam) continue;
      const m = cam.fill.match(/rgb\((\d+),(\d+),(\d+)\)/);
      if (!m) continue;
      acc[0] += Number(m[1]); acc[1] += Number(m[2]); acc[2] += Number(m[3]); n += 1;
    }
  }
  return n ? acc.map((v) => Math.round(v / n)) : null;
}
function rotPoint(p, yaw, pitch) {
  const cy = Math.cos(yaw), sy = Math.sin(yaw);
  const x1 = p[0] * cy + p[2] * sy;
  const z1 = -p[0] * sy + p[2] * cy;
  const cp = Math.cos(pitch), sp = Math.sin(pitch);
  return [x1, p[1] * cp - z1 * sp, p[1] * sp + z1 * cp];
}
function maskOf(faces, yaw, pitch, fit) {
  const W = 400, H = 260, grid = new Uint8Array(W * H);
  for (const face of faces) {
    const world = face.pts.map((p) => rotPoint([p[0] * fit, p[1] * fit, p[2] * fit], yaw, pitch));
    const ax = world[1][0] - world[0][0], ay = world[1][1] - world[0][1], az = world[1][2] - world[0][2];
    const bx = world[2][0] - world[0][0], by = world[2][1] - world[0][1], bz = world[2][2] - world[0][2];
    const nz = ax * by - ay * bx;
    const len = Math.hypot(ay * bz - az * by, az * bx - ax * bz, nz) || 1;
    if (nz / len <= 0.035) continue;
    const poly = world.map((p) => { const s = 900 / (430 - p[2]); return [200 + p[0] * s, 124 - p[1] * s]; });
    let minY = H, maxY = 0;
    for (const pt of poly) { if (pt[1] < minY) minY = pt[1]; if (pt[1] > maxY) maxY = pt[1]; }
    minY = Math.max(0, Math.floor(minY)); maxY = Math.min(H - 1, Math.ceil(maxY));
    for (let y = minY; y <= maxY; y++) {
      const xs = [];
      for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
        const y0 = poly[j][1], y1 = poly[i][1];
        if ((y0 <= y && y1 > y) || (y1 <= y && y0 > y)) {
          const t = (y - y0) / ((y1 - y0) || 1e-9);
          xs.push(poly[j][0] + t * (poly[i][0] - poly[j][0]));
        }
      }
      xs.sort((a, b) => a - b);
      for (let k = 0; k + 1 < xs.length; k += 2) {
        const x0 = Math.max(0, Math.floor(xs[k])), x1 = Math.min(W - 1, Math.ceil(xs[k + 1]));
        for (let x = x0; x <= x1; x++) grid[y * W + x] = 1;
      }
    }
  }
  return grid;
}
function clearance(faces, markers, fit, yaw, pitch) {
  const slots = api.escortSlots(markers, faces, fit, yaw, pitch);
  const Rb = api.hullRadius(faces);
  const grid = maskOf(faces, yaw, pitch, fit);
  let under = 0, overlap = 0, clipped = 0;
  for (const slot of slots) {
    if (Math.hypot(slot.x, slot.y, slot.z) < Rb - 1e-6) under += 1;
    const w = rotPoint([slot.x * fit, slot.y * fit, slot.z * fit], yaw, pitch);
    const s = 900 / (430 - w[2]);
    const x = 200 + w[0] * s, y = 124 - w[1] * s;
    const box = [x - 3.1, y - 4, x + 3.1, y + 4];
    if (box[0] < 4 || box[2] > 396 || box[1] < 4 || box[3] > 256) clipped += 1;
    const top = Math.max(0, Math.floor(box[1])), bot = Math.min(259, Math.ceil(box[3]));
    const left = Math.max(0, Math.floor(box[0])), right = Math.min(399, Math.ceil(box[2]));
    let hit = false;
    for (let yy = top; yy <= bot && !hit; yy++) for (let xx = left; xx <= right; xx++) if (grid[yy * 400 + xx]) { hit = true; break; }
    if (hit) overlap += 1;
  }
  return { got: slots.length, under, overlap, clipped };
}
function project(p, yaw, pitch, fit) {
  const w = rotPoint([p[0] * fit, p[1] * fit, p[2] * fit], yaw, pitch);
  const s = 900 / (430 - w[2]);
  return [200 + w[0] * s, 124 - w[1] * s];
}
function screenBox(faces, yaw, pitch, fit) {
  let minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
  for (const face of faces) for (const p of face.pts) {
    const s = project(p, yaw, pitch, fit);
    if (s[0] < minX) minX = s[0]; if (s[0] > maxX) maxX = s[0];
    if (s[1] < minY) minY = s[1]; if (s[1] > maxY) maxY = s[1];
  }
  return [Math.round(minX), Math.round(minY), Math.round(maxX), Math.round(maxY)];
}
function extremes(faces, yaw, pitch, fit) {
  let left = null, right = null, top = null, bottom = null;
  for (const face of faces) for (const p of face.pts) {
    const s = project(p, yaw, pitch, fit);
    if (!left || s[0] < left.s[0]) left = { p, s };
    if (!right || s[0] > right.s[0]) right = { p, s };
    if (!top || s[1] < top.s[1]) top = { p, s };
    if (!bottom || s[1] > bottom.s[1]) bottom = { p, s };
  }
  const pack = (hit) => hit.p.map((v) => Math.round(v * 10) / 10);
  return { left: pack(left), right: pack(right), top: pack(top), bottom: pack(bottom) };
}
function sil(faces, yaw, pitch, fit) {
  const grid = maskOf(faces, yaw, pitch, fit);
  let minX = 400, maxX = 0, minY = 260, maxY = 0;
  for (let y = 0; y < 260; y++) for (let x = 0; x < 400; x++) if (grid[y * 400 + x]) {
    if (x < minX) minX = x; if (x > maxX) maxX = x;
    if (y < minY) minY = y; if (y > maxY) maxY = y;
  }
  return { w: maxX - minX, h: maxY - minY };
}
function engineRows(faces) {
  const bins = [];
  for (const face of faces) if (face.emissive) {
    let y = 0, z = 0;
    for (const p of face.pts) { y += p[1]; z += p[2]; }
    y /= face.pts.length; z /= face.pts.length;
    let bin = null;
    for (const item of bins) if (Math.abs(item.z - z) < 4.5 && Math.abs(item.y - y) < 6) bin = item;
    if (!bin) { bin = { z, y, n: 0 }; bins.push(bin); }
    bin.n += 1;
  }
  return bins.map((bin) => ({ z: Math.round(bin.z * 10) / 10, y: Math.round(bin.y * 10) / 10, n: bin.n }));
}
const cams = {
  three: [0.82, 0.5, 1.12],
  phone: [0.82, 0.5, 0.72],
  head: [-1.35, 0.2, 1],
  side: [1.35, 0.18, 1.15],
};
function rings(faces, counts) {
  const out = {};
  for (const [name, [yaw, pitch, fit]] of Object.entries(cams)) {
    out[name] = {};
    for (const n of counts) out[name][n] = clearance(faces, n, fit, yaw, pitch);
  }
  return out;
}
const pod = build("escape_pod", "#55ffff", 1, "", false);
const podTw = build("escape_pod", "#55ffff", 1, "", true);
const orion = build("tkhasi_orion", "#ff6d8a", 2, "wings bridge", false);
const orionBridge = build("tkhasi_orion", "#ff6d8a", 2, "bridge", false);
const orionWings = build("tkhasi_orion", "#ff6d8a", 2, "wings", false);
const orionBare = build("tkhasi_orion", "#ff6d8a", 2, "", false);
const orionTw = build("tkhasi_orion", "#ff6d8a", 2, "wings bridge", true);
const scout = build("scout_marauder", "#5dffc8", 2, "bridge", false);
const fr = build("merchant_freighter", "#7af0ff", 2, "pods bridge", false);
const mer = build("merchant_cruiser", "#7aa2ff", 2, "pods bridge", false);
const imp = build("imperial_starship", "#ffe9a0", 4, "bridge nacelles", false);
const bs = build("battleship", "#c5c8ff", 3, "bridge guns", false);
const flag = build("corporate_flagship", "#ff77ff", 3, "bridge pods", false);
let podFin = 1e9, accentWide = 0;
for (const face of pod) for (const p of face.pts) {
  if (Math.abs(p[2]) > 48 && p[0] < podFin) podFin = p[0];
  if (face.accent && Math.abs(p[2]) > 20) accentWide += 1;
}
let wideMin = 1e9, tubeMin = 1e9, fwd = 0, tipAccent = 0;
for (const face of orion) for (const p of face.pts) {
  if (Math.abs(p[2]) > 20 && p[0] < wideMin) wideMin = p[0];
  if (!face.emissive && Math.abs(p[2]) < 3.2 && p[0] < tubeMin) tubeMin = p[0];
  if (p[0] > 24 && Math.abs(p[2]) > 12) fwd += 1;
  if (face.accent && Math.abs(p[2]) > 30) tipAccent += 1;
}
const report = {
  pod: {
    faces: pod.length,
    accent: pod.filter((f) => f.accent).length,
    accentEmit: pod.filter((f) => f.accent && f.emissive).length,
    span: spanOf(pod),
    accent0: meanFill(pod, (f) => f.accent, 0),
    accent1: meanFill(pod, (f) => f.accent, 1),
    body1: meanFill(pod, (f) => !f.accent && !f.emissive, 1),
    emit0: meanFill(pod, (f) => f.emissive, 0),
    engines: engineRows(pod),
    finX: Math.round(podFin * 10) / 10,
    accentWide,
    rings: rings(pod, [0, 1]),
    frame: screenBox(pod, 0.82, 0.5, 1.12),
    head: extremes(pod, -1.35, 0.2, 1),
    side: extremes(pod, 1.35, 0.18, 1.15),
    headSil: sil(pod, -1.35, 0.2, 1),
  },
  podTw: {
    accent1: meanFill(podTw, (f) => f.accent, 1),
    emit0: meanFill(podTw, (f) => f.emissive, 0),
  },
  orion: {
    faces: orion.length,
    accent: orion.filter((f) => f.accent).length,
    accentEmit: orion.filter((f) => f.accent && f.emissive).length,
    span: spanOf(orion),
    accent0: meanFill(orion, (f) => f.accent, 0),
    accent1: meanFill(orion, (f) => f.accent, 1),
    body1: meanFill(orion, (f) => !f.accent && !f.emissive, 1),
    emit0: meanFill(orion, (f) => f.emissive, 0),
    engines: engineRows(orion),
    wideMin: Math.round(wideMin * 10) / 10,
    tubeMin: Math.round(tubeMin * 10) / 10,
    fwd,
    tipAccent,
    wingsSame: hashPts(orion) === hashPts(orionBridge) && hashPts(orion) === hashPts(orionWings) && hashPts(orion) === hashPts(orionBare),
    rings: rings(orion, [0, 1, 8]),
    frame: screenBox(orion, 0.82, 0.5, 1.12),
    head: extremes(orion, -1.35, 0.2, 1),
    side: extremes(orion, 1.35, 0.18, 1.15),
    headSil: sil(orion, -1.35, 0.2, 1),
  },
  orionTw: {
    accent1: meanFill(orionTw, (f) => f.accent, 1),
    emit0: meanFill(orionTw, (f) => f.emissive, 0),
  },
  scout: { faces: scout.length, span: spanOf(scout), rings: rings(scout, [2, 3]) },
  fr: fr.length,
  mer: mer.length,
  imp: imp.length,
  bs: bs.length,
  flag: flag.length,
};
console.log(JSON.stringify(report));
"""
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
        timeout=90,
    )
    return json.loads(proc.stdout)


def _markers(n: int) -> int:
    if n < 1:
        return 0
    return max(1, -(-n // 100))


def test_mesh_budget_and_prior_faces() -> None:
    import gzip

    raw = MESHES.read_text(encoding="utf-8")
    assert len(gzip.compress(raw.encode(), 9)) < 40 * 1024
    assert "function buildHullFaces" in raw
    assert "function projectFace" in raw
    assert "podSpike" in raw and "orionSpike" in raw
    assert "from \"three\"" not in raw
    assert "getContext(\"webgl\"" not in raw
    assert "fleet-glass-v1" in raw
    report = _report()
    assert report["mer"] == 217
    assert report["imp"] == 311
    assert report["scout"]["faces"] == 201
    assert report["fr"] == 251
    assert report["bs"] == 226
    assert report["flag"] == 210
    assert report["pod"]["faces"] == 98
    assert report["orion"]["faces"] == 167
    assert report["pod"]["accent"] == 11
    assert report["orion"]["accent"] == 15
    assert report["pod"]["accentEmit"] == 0
    assert report["orion"]["accentEmit"] == 0


def test_pod_reads_as_a_short_finned_capsule() -> None:
    report = _report()
    pod = report["pod"]
    span = pod["span"]
    scout = report["scout"]["span"]
    assert span["size"][1] > span["size"][0] * 0.9
    assert span["size"][0] < scout["size"][0] * 0.6
    assert span["size"][2] > span["size"][0]
    assert span["size"][1] > scout["size"][1] * 2
    assert pod["finX"] > span["min"][0] + 12
    assert pod["accentWide"] == 0
    assert len(pod["engines"]) == 1
    engine = pod["engines"][0]
    assert engine["y"] < -8 and abs(engine["z"]) < 3
    assert abs(engine["z"]) < span["size"][2] / 2 - 20
    for side in (pod["head"]["left"], pod["head"]["right"], pod["side"]["left"], pod["side"]["right"]):
        assert abs(side[2]) > 50
        assert abs(side[1]) < 8
    assert pod["head"]["top"][1] > 28 and abs(pod["head"]["top"][2]) < 6
    assert pod["side"]["top"][1] > 28 and abs(pod["side"]["top"][2]) < 6
    assert pod["headSil"]["h"] > 50 and pod["headSil"]["w"] > pod["headSil"]["h"]
    left, top, right, bottom = pod["frame"]
    assert 8 < left < right < 392, pod["frame"]
    assert 8 < top < bottom < 252, pod["frame"]


def test_orion_is_one_crescent_past_the_tail() -> None:
    report = _report()
    orion = report["orion"]
    span = orion["span"]
    scout = report["scout"]["span"]
    assert orion["wingsSame"] is True
    assert orion["fwd"] == 0
    assert orion["tipAccent"] > 0
    assert span["size"][2] >= 64
    assert span["max"][2] >= 32
    assert span["size"][1] < 20
    assert span["size"][0] < scout["size"][0]
    assert span["size"][2] > scout["size"][2]
    assert orion["wideMin"] < orion["tubeMin"] - 16
    assert len(orion["engines"]) == 2
    for engine in orion["engines"]:
        assert engine["y"] < 0
        assert 6 < abs(engine["z"]) < span["max"][2] - 8
    for side in (orion["head"]["left"], orion["head"]["right"]):
        assert abs(side[2]) > 30
        assert side[0] < 0
    assert orion["head"]["top"][1] < 12
    for side in (orion["side"]["left"], orion["side"]["right"]):
        assert abs(side[2]) > 30
    assert orion["headSil"]["w"] > orion["headSil"]["h"] * 2
    left, top, right, bottom = orion["frame"]
    assert 8 < left < right < 392, orion["frame"]
    assert 8 < top < bottom < 252, orion["frame"]


def test_empty_shields_keep_the_class_accent() -> None:
    report = _report()
    pod = report["pod"]
    orion = report["orion"]
    assert pod["accent0"] == pod["accent1"] == report["podTw"]["accent1"]
    assert orion["accent0"] == orion["accent1"] == report["orionTw"]["accent1"]
    pr, pg, pb = pod["accent1"]
    assert pg > 170 and pb > 170 and pr < 140 and abs(pg - pb) < 30
    rr, rg, rb = orion["accent1"]
    assert rr > 160 and rr > rb > rg
    for row in (pod, orion):
        br, bg, bb = row["body1"]
        assert br < 90 and br <= bg + 15 and br < bb + 20
    er, eg, eb = pod["emit0"]
    assert eg >= er and eb >= er
    tr, tg, tb = report["podTw"]["emit0"]
    assert tr > tg and tb > tg
    fer, feg, feb = orion["emit0"]
    assert feg >= fer - 10 and feb >= fer - 10
    wr, wg, wb = report["orionTw"]["emit0"]
    assert wr > wg and wb > wg


def test_markers_clear_the_fins_and_the_plates() -> None:
    assert _markers(0) == 0
    assert _markers(1) == 1
    assert _markers(50) == 1
    assert _markers(100) == 1
    assert _markers(101) == 2
    assert _markers(150) == 2
    assert _markers(250) == 3
    assert _markers(700) == 7
    assert _markers(749) == 8
    assert _markers(750) == 8
    report = _report()
    for hull in (report["pod"], report["orion"], report["scout"]):
        for cam, rings in hull["rings"].items():
            for count, row in rings.items():
                assert row["got"] == int(count), (cam, count, row)
                assert row["under"] == 0 and row["overlap"] == 0 and row["clipped"] == 0, (cam, count, row)
