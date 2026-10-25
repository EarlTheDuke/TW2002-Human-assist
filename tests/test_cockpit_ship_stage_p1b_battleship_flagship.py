"""P1b: BattleShip and Corporate FlagShip on the shared SVG mesh."""

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
function highSides(faces, yCut) {
  let neg = -1e9, pos = -1e9;
  for (const face of faces) for (const p of face.pts) if (p[1] > yCut) {
    if (p[2] < -8) neg = Math.max(neg, p[1]);
    if (p[2] > 8) pos = Math.max(pos, p[1]);
  }
  return [Math.round(neg * 10) / 10, Math.round(pos * 10) / 10];
}
function kitFlags(faces, yCut, zCut) {
  let accent = 0, bad = 0, emit = 0;
  for (const face of faces) {
    let hit = false;
    for (const p of face.pts) if (p[1] > yCut && Math.abs(p[2]) <= zCut + 0.01) hit = true;
    if (!hit) continue;
    accent += 1;
    if (!face.accent || face.emissive) bad += 1;
    if (face.emissive) emit += 1;
  }
  return { accent, bad, emit };
}
function towerRise(faces) {
  let top = -1e9, hi = -1e9, lo = 1e9;
  for (const face of faces) for (const p of face.pts) {
    if (p[1] > top) top = p[1];
    const tower = p[1] > 12 && Math.abs(p[2]) < 13 && p[0] > -18 && p[0] < 16;
    const engine = p[0] < -50;
    const canopy = p[0] > 22 && p[1] > 8 && Math.abs(p[2]) < 6;
    if (tower || engine || canopy) continue;
    if (p[1] > hi) hi = p[1];
    if (p[1] < lo) lo = p[1];
  }
  return {
    top: Math.round(top * 10) / 10,
    skin: Math.round(hi * 10) / 10,
    depth: Math.round((hi - lo) * 10) / 10,
    rise: Math.round((top - hi) * 10) / 10,
  };
}
const bs = build("battleship", "#c5c8ff", 3, "bridge guns", false);
const bsTw = build("battleship", "#c5c8ff", 3, "bridge guns", true);
const flag = build("corporate_flagship", "#ff77ff", 3, "bridge pods", false);
const flagTw = build("corporate_flagship", "#ff77ff", 3, "bridge pods", true);
const mer = build("merchant_cruiser", "#7aa2ff", 2, "pods bridge", false);
const imp = build("imperial_starship", "#ffe9a0", 4, "bridge nacelles", false);
const scout = build("scout_marauder", "#5dffc8", 2, "bridge", false);
const fr = build("merchant_freighter", "#7af0ff", 2, "pods bridge", false);
const cams = {
  three: [0.82, 0.5, 1.12],
  panel: [0.82, 0.5, 0.76],
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
let noseWide = 0;
for (const face of bs) for (const p of face.pts) if (p[0] > 46 && Math.abs(p[2]) > 18) noseWide += 1;
const report = {
  bs: {
    faces: bs.length,
    accent: bs.filter((f) => f.accent).length,
    accentEmit: bs.filter((f) => f.accent && f.emissive).length,
    span: spanOf(bs),
    accent0: meanFill(bs, (f) => f.accent, 0),
    accent1: meanFill(bs, (f) => f.accent, 1),
    body1: meanFill(bs, (f) => !f.accent && !f.emissive, 1),
    emit0: meanFill(bs, (f) => f.emissive, 0),
    engines: engineRows(bs),
    barrels: highSides(bs, 16),
    barrelKit: kitFlags(bs, 19, 20),
    noseWide,
    rings: rings(bs, [0, 1, 100]),
    frame: screenBox(bs, 0.82, 0.5, 1.12),
    head: extremes(bs, -1.35, 0.2, 1),
    side: extremes(bs, 1.35, 0.18, 1.15),
    headSil: sil(bs, -1.35, 0.2, 1),
  },
  bsTw: {
    accent1: meanFill(bsTw, (f) => f.accent, 1),
    emit0: meanFill(bsTw, (f) => f.emissive, 0),
  },
  flag: {
    faces: flag.length,
    accent: flag.filter((f) => f.accent).length,
    accentEmit: flag.filter((f) => f.accent && f.emissive).length,
    span: spanOf(flag),
    accent0: meanFill(flag, (f) => f.accent, 0),
    accent1: meanFill(flag, (f) => f.accent, 1),
    body1: meanFill(flag, (f) => !f.accent && !f.emissive, 1),
    emit0: meanFill(flag, (f) => f.emissive, 0),
    engines: engineRows(flag),
    tower: kitFlags(flag, 28, 9),
    rise: towerRise(flag),
    rings: rings(flag, [0, 1, 200]),
    frame: screenBox(flag, 0.82, 0.5, 1.12),
    head: extremes(flag, -1.35, 0.2, 1),
    side: extremes(flag, 1.35, 0.18, 1.15),
    headSil: sil(flag, -1.35, 0.2, 1),
  },
  flagTw: {
    accent1: meanFill(flagTw, (f) => f.accent, 1),
    emit0: meanFill(flagTw, (f) => f.emissive, 0),
  },
  mer: { faces: mer.length, span: spanOf(mer) },
  imp: { faces: imp.length, span: spanOf(imp), engines: engineRows(imp).length },
  scout: scout.length,
  fr: fr.length,
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


def test_mesh_budget_and_shared_path() -> None:
    import gzip

    raw = MESHES.read_text(encoding="utf-8")
    assert len(gzip.compress(raw.encode(), 9)) < 40 * 1024
    assert "function buildHullFaces" in raw
    assert "function projectFace" in raw
    assert "battleshipSpike" in raw and "flagshipSpike" in raw
    assert "from \"three\"" not in raw
    assert "getContext(\"webgl\"" not in raw
    assert "fleet-glass-v1" in raw
    report = _report()
    assert report["mer"]["faces"] == 217
    assert report["imp"]["faces"] == 311
    assert report["scout"] == 201
    assert report["fr"] == 251
    assert report["bs"]["faces"] == 226
    assert report["flag"]["faces"] == 210
    assert report["bs"]["accent"] == 13
    assert report["flag"]["accent"] == 7
    assert report["bs"]["accentEmit"] == 0
    assert report["flag"]["accentEmit"] == 0


def test_silhouettes_are_a_wide_wedge_and_a_tower() -> None:
    report = _report()
    bs = report["bs"]["span"]
    flag = report["flag"]["span"]
    mer = report["mer"]["span"]
    imp = report["imp"]["span"]
    assert bs["size"][0] < imp["size"][0]
    assert bs["size"][2] > mer["size"][2]
    assert bs["size"][0] < bs["size"][2] * 1.6
    assert flag["size"][0] < imp["size"][0]
    assert flag["size"][2] < bs["size"][2] - 20
    assert flag["size"][0] > bs["size"][0]
    rise = report["flag"]["rise"]
    assert rise["rise"] > rise["depth"]
    assert rise["rise"] > 18
    assert rise["top"] > 30
    assert report["bs"]["noseWide"] == 0
    assert report["bs"]["barrels"][0] > 18 and report["bs"]["barrels"][1] > 18
    assert report["bs"]["barrelKit"]["accent"] > 0 and report["bs"]["barrelKit"]["bad"] == 0
    assert report["flag"]["tower"]["accent"] > 0 and report["flag"]["tower"]["bad"] == 0
    for row in (report["bs"], report["flag"]):
        left, top, right, bottom = row["frame"]
        assert 8 < left < right < 392, row["frame"]
        assert 8 < top < bottom < 252, row["frame"]
    for hull in (report["bs"], report["flag"]):
        rows = hull["engines"]
        assert len(rows) == 3, rows
        assert all(item["y"] < 0 for item in rows)
        assert max(abs(item["z"]) for item in rows) < hull["span"]["size"][2] / 2 - 4
    assert report["imp"]["engines"] == 4


def test_head_on_kit_is_the_signature() -> None:
    report = _report()
    bs = report["bs"]["head"]
    for side in (bs["left"], bs["right"]):
        assert abs(side[2]) > 30
        assert abs(side[1]) < 8
    assert bs["top"][1] > 16 and abs(bs["top"][2]) > 10
    assert report["bs"]["headSil"]["w"] > report["bs"]["headSil"]["h"] * 2
    side = report["bs"]["side"]
    assert side["top"][1] > 16 and abs(side["top"][2]) > 10
    flag = report["flag"]["head"]
    assert flag["top"][1] > 28 and abs(flag["top"][2]) < 10
    assert abs(flag["left"][2]) > 16
    assert abs(flag["top"][0]) < 16
    side_flag = report["flag"]["side"]
    assert side_flag["top"][1] > 28 and abs(side_flag["top"][2]) < 10


def test_empty_shields_keep_the_class_accent() -> None:
    report = _report()
    bs = report["bs"]
    flag = report["flag"]
    assert bs["accent0"] == bs["accent1"] == report["bsTw"]["accent1"]
    assert flag["accent0"] == flag["accent1"] == report["flagTw"]["accent1"]
    br, bg, bb = bs["accent1"]
    assert bb > br and bb > bg and br > 140 and bg > 140
    fr, fg, fb = flag["accent1"]
    assert fr > 180 and fb > 180 and fg < 140 and abs(fr - fb) < 30
    for row in (bs, flag):
        body_r, body_g, body_b = row["body1"]
        assert body_r < 90 and body_r <= body_g + 15 and body_r < body_b + 20
    er, eg, eb = bs["emit0"]
    assert eg >= er and eb >= er
    tr, tg, tb = report["bsTw"]["emit0"]
    assert tr > tg and tb > tg
    fer, feg, feb = flag["emit0"]
    assert feg >= fer - 10 and feb >= fer - 10
    wr, wg, wb = report["flagTw"]["emit0"]
    assert wr > wg and wb > wg
    assert fg < fb


def test_markers_clear_the_barrels_and_the_tower() -> None:
    assert _markers(0) == 0
    assert _markers(1) == 1
    assert _markers(100) == 1
    assert _markers(101) == 2
    assert _markers(10000) == 100
    assert _markers(20000) == 200
    report = _report()
    for hull in (report["bs"], report["flag"]):
        for cam, rings in hull["rings"].items():
            for count, row in rings.items():
                assert row["got"] == int(count), (cam, count, row)
                assert row["under"] == 0 and row["overlap"] == 0 and row["clipped"] == 0, (cam, count, row)
