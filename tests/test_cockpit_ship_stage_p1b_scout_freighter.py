"""P1b: Scout Marauder and Merchant Freighter on the shared SVG mesh."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MESHES = ROOT / "web" / "hull-meshes.js"


def _report() -> dict:
    script = r"""
import api from "./web/hull-meshes.mjs";

function build(cls, accent, engines, detail, tw) {
  return api.buildHullFaces(
    { class: cls, transwarp: { fitted: !!tw } },
    { accent, detail, engines, name: cls }
  );
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
function maxAbs(faces, pred, axis) {
  let m = 0;
  for (const face of faces) for (const p of face.pts) if (pred(p)) m = Math.max(m, Math.abs(p[axis]));
  return Math.round(m * 10) / 10;
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
const scout = build("scout_marauder", "#5dffc8", 2, "bridge", false);
const scoutTw = build("scout_marauder", "#5dffc8", 2, "bridge", true);
const fr = build("merchant_freighter", "#7af0ff", 2, "pods bridge", false);
const frTw = build("merchant_freighter", "#7af0ff", 2, "pods bridge", true);
const mer = build("merchant_cruiser", "#7aa2ff", 2, "pods bridge", false);
const imp = build("imperial_starship", "#ffe9a0", 4, "bridge nacelles", false);
const cams = {
  three: [0.82, 0.5, 1.12],
  phone: [0.82, 0.5, 0.72],
  head: [-1.35, 0.2, 1],
  side: [1.35, 0.18, 1.15],
};
function rings(faces) {
  const out = {};
  for (const [name, [yaw, pitch, fit]] of Object.entries(cams)) {
    out[name] = {};
    for (const n of [0, 1, 2, 3]) out[name][n] = clearance(faces, n, fit, yaw, pitch);
  }
  return out;
}
let blade = 0;
for (const face of scout) for (const p of face.pts) if (Math.abs(p[2]) > 18 && Math.abs(p[1]) > 4) blade += 1;
let ports = 0;
for (const face of fr) if (face.emissive) {
  const z = Math.max(...face.pts.map((p) => Math.abs(p[2])));
  if (z > 40) ports += 1;
}
const report = {
  scout: {
    faces: scout.length,
    accent: scout.filter((f) => f.accent).length,
    span: spanOf(scout),
    accent0: meanFill(scout, (f) => f.accent, 0),
    accent1: meanFill(scout, (f) => f.accent, 1),
    body1: meanFill(scout, (f) => !f.accent && !f.emissive, 1),
    emit0: meanFill(scout, (f) => f.emissive, 0),
    noseZ: maxAbs(scout, (p) => p[0] > 36, 2),
    tailZ: maxAbs(scout, (p) => p[0] < -30 && Math.abs(p[1]) < 5, 2),
    engineZ: maxAbs(scout.filter((f) => f.emissive), () => true, 2),
    rings: rings(scout),
    frame: screenBox(scout, 0.82, 0.5, 1.12),
    head: extremes(scout, -1.35, 0.2, 1),
    headSil: sil(scout, -1.35, 0.2, 1),
    blade,
  },
  scoutTw: {
    accent1: meanFill(scoutTw, (f) => f.accent, 1),
    emit0: meanFill(scoutTw, (f) => f.emissive, 0),
  },
  fr: {
    faces: fr.length,
    accent: fr.filter((f) => f.accent).length,
    span: spanOf(fr),
    accent0: meanFill(fr, (f) => f.accent, 0),
    accent1: meanFill(fr, (f) => f.accent, 1),
    body1: meanFill(fr, (f) => !f.accent && !f.emissive, 1),
    emit0: meanFill(fr, (f) => f.emissive, 0),
    engineZ: maxAbs(fr.filter((f) => f.emissive && Math.abs(f.pts[0][0]) > 20), () => true, 2),
    ports,
    rings: rings(fr),
    frame: screenBox(fr, 0.82, 0.5, 1.12),
    head: extremes(fr, -1.35, 0.2, 1),
    headSil: sil(fr, -1.35, 0.2, 1),
  },
  frTw: {
    accent1: meanFill(frTw, (f) => f.accent, 1),
    emit0: meanFill(frTw, (f) => f.emissive, 0),
  },
  mer: spanOf(mer),
  imp: { faces: imp.length, span: spanOf(imp) },
  merFaces: mer.length,
};
console.log(JSON.stringify(report));
"""
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return json.loads(proc.stdout)


def _markers(n: int) -> int:
    if n < 1:
        return 0
    return max(1, -(-n // 100))


def test_mesh_budget_and_shared_path() -> None:
    import gzip

    raw = MESHES.read_text(encoding="utf-8")
    assert len(gzip.compress(raw.encode(), 9)) < 40 * 1024
    assert "function buildHullFaces" in raw
    assert "function projectFace" in raw
    assert "scoutSpike" in raw and "freighterSpike" in raw
    assert "from \"three\"" not in raw
    assert "getContext(\"webgl\"" not in raw
    assert "fleet-glass-v1" in raw
    report = _report()
    assert report["merFaces"] == 217
    assert report["imp"]["faces"] == 311
    assert report["scout"]["faces"] == 201
    assert report["fr"]["faces"] == 251
    assert report["scout"]["accent"] > 12
    assert report["fr"]["accent"] > 12


def test_silhouettes_read_as_needle_and_wide_freighter() -> None:
    report = _report()
    scout = report["scout"]["span"]
    fr = report["fr"]["span"]
    mer = report["mer"]
    imp = report["imp"]["span"]
    assert imp["size"][0] > scout["size"][0] > mer["size"][0] > fr["size"][0]
    assert scout["size"][0] > scout["size"][2] * 2
    assert scout["size"][1] < 24
    assert report["scout"]["noseZ"] > 28
    assert report["scout"]["tailZ"] < 12
    assert report["scout"]["noseZ"] > report["scout"]["tailZ"] * 2.5
    assert report["scout"]["engineZ"] < 10
    assert report["scout"]["blade"] == 0
    assert fr["size"][2] > fr["size"][0] * 0.9
    assert fr["size"][1] < 20
    assert fr["min"][1] > -12
    assert mer["min"][1] < -18
    assert report["fr"]["engineZ"] < fr["size"][2] / 2 - 8
    assert report["fr"]["ports"] >= 6
    for row in (report["scout"], report["fr"]):
        left, top, right, bottom = row["frame"]
        assert 8 < left < right < 392, row["frame"]
        assert 8 < top < bottom < 252, row["frame"]


def test_head_on_kit_is_the_signature() -> None:
    report = _report()
    scout = report["scout"]["head"]
    for side in (scout["left"], scout["right"]):
        assert abs(side[2]) > 24
        assert abs(side[1]) < 4
    assert scout["top"][1] > 10 and abs(scout["top"][2]) < 2
    assert scout["bottom"][1] > -10
    fr = report["fr"]["head"]
    for side in (fr["left"], fr["right"]):
        assert abs(side[2]) > 40
    assert report["fr"]["headSil"]["w"] > report["fr"]["headSil"]["h"] * 3
    assert report["scout"]["headSil"]["w"] > report["scout"]["headSil"]["h"]


def test_empty_shields_keep_the_class_accent() -> None:
    report = _report()
    scout = report["scout"]
    fr = report["fr"]
    assert scout["accent0"] == scout["accent1"] == report["scoutTw"]["accent1"]
    assert fr["accent0"] == fr["accent1"] == report["frTw"]["accent1"]
    sr, sg, sb = scout["accent1"]
    assert sg > sb > sr and sg > 170
    fr_r, fr_g, fr_b = fr["accent1"]
    assert fr_b > 170 and fr_g > 170 and fr_r < 140 and fr_b + 20 >= fr_g
    for row in (scout, fr):
        br, bg, bb = row["body1"]
        assert br < 90 and br <= bg + 15 and br < bb + 20
    er, eg, eb = scout["emit0"]
    assert eg >= er and eb >= er
    tr, tg, tb = report["scoutTw"]["emit0"]
    assert tr > tg and tb > tg
    fr_er, fr_eg, fr_eb = fr["emit0"]
    assert fr_eg >= fr_er - 10 and fr_eb >= fr_er - 10
    wr, wg, wb = report["frTw"]["emit0"]
    assert wr > wg and wb > wg


def test_markers_stay_outside_at_both_caps() -> None:
    assert _markers(0) == 0
    assert _markers(1) == 1
    assert _markers(100) == 1
    assert _markers(101) == 2
    assert _markers(150) == 2
    assert _markers(250) == 3
    assert _markers(300) == 3
    report = _report()
    for hull in (report["scout"], report["fr"]):
        for cam, rings in hull["rings"].items():
            for count, row in rings.items():
                assert row["got"] == int(count), (cam, count, row)
                assert row["under"] == 0 and row["overlap"] == 0 and row["clipped"] == 0, (cam, count, row)
