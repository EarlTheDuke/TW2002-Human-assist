"""P1b batch 2: CargoTran, Colonial Transport, and Taurean Mule on the shared SVG mesh."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MESHES = ROOT / "web" / "hull-meshes.js"

# Point hashes of the three hauler lofts. Other hull pins stay where their cuts left them.
HAULERS = {
    "cargotran": (212, 28, "bc3414793b3998f3"),
    "colonial_transport": (251, 51, "7f83c52861a478ef"),
    "taurean_mule": (209, 47, "0a7e2e77c1d42c64"),
}


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
function extremes(faces, yaw, pitch, fit) {
  let left = null, right = null, top = null, bottom = null;
  for (const face of faces) for (const p of face.pts) {
    const w = rotPoint([p[0] * fit, p[1] * fit, p[2] * fit], yaw, pitch);
    const s = 900 / (430 - w[2]);
    const q = [200 + w[0] * s, 124 - w[1] * s];
    if (!left || q[0] < left.q[0]) left = { p, q };
    if (!right || q[0] > right.q[0]) right = { p, q };
    if (!top || q[1] < top.q[1]) top = { p, q };
    if (!bottom || q[1] > bottom.q[1]) bottom = { p, q };
  }
  const pack = (hit) => hit.p.map((v) => Math.round(v * 10) / 10);
  return { left: pack(left), right: pack(right), top: pack(top), bottom: pack(bottom) };
}
function screenBox(faces, yaw, pitch, fit) {
  let minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
  for (const face of faces) for (const p of face.pts) {
    const w = rotPoint([p[0] * fit, p[1] * fit, p[2] * fit], yaw, pitch);
    const s = 900 / (430 - w[2]);
    const x = 200 + w[0] * s, y = 124 - w[1] * s;
    if (x < minX) minX = x; if (x > maxX) maxX = x;
    if (y < minY) minY = y; if (y > maxY) maxY = y;
  }
  return [Math.round(minX), Math.round(minY), Math.round(maxX), Math.round(maxY)];
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
function tailEmit(faces) {
  const picked = faces.filter((face) => {
    if (!face.emissive) return false;
    let x = 0;
    for (const p of face.pts) x += p[0];
    return x / face.pts.length < -30;
  });
  return meanFill(picked, () => true, 0);
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
function pack(cls, accent, counts) {
  const faces = build(cls, accent, 2, "pods", false);
  const bare = build(cls, accent, 2, "", false);
  const bridge = build(cls, accent, 2, "bridge", false);
  const tw = build(cls, accent, 2, "pods", true);
  let shoulder = 0, lowOuter = 0, aftOuter = 0;
  for (const face of faces) for (const p of face.pts) {
    if (p[1] > 2 && Math.abs(p[2]) > 18) shoulder += 1;
    if (p[1] < -12 && Math.abs(p[2]) > 16) lowOuter += 1;
    if (p[0] < -20 && Math.abs(p[2]) > 12) aftOuter += 1;
  }
  return {
    faces: faces.length,
    accent: faces.filter((f) => f.accent).length,
    accentEmit: faces.filter((f) => f.accent && f.emissive).length,
    hash: hashPts(faces),
    podsSame: hashPts(faces) === hashPts(bare) && hashPts(faces) === hashPts(bridge),
    span: spanOf(faces),
    accent0: meanFill(faces, (f) => f.accent, 0),
    accent1: meanFill(faces, (f) => f.accent, 1),
    body1: meanFill(faces, (f) => !f.accent && !f.emissive, 1),
    tail0: tailEmit(faces),
    tailTw: tailEmit(tw),
    accentTw: meanFill(tw, (f) => f.accent, 1),
    shoulder, lowOuter, aftOuter,
    rings: rings(faces, counts),
    frame: screenBox(faces, 0.82, 0.5, 1.12),
    head: extremes(faces, -1.35, 0.2, 1),
    side: extremes(faces, 1.35, 0.18, 1.15),
    headSil: sil(faces, -1.35, 0.2, 1),
  };
}
const ct = pack("cargotran", "#ffe566", [0, 1, 4]);
const col = pack("colonial_transport", "#7dff7d", [0, 1, 2]);
const mule = pack("taurean_mule", "#d7b48a", [0, 1, 3]);
const prior = {
  merchant_cruiser: build("merchant_cruiser", "#7aa2ff", 2, "pods bridge", false).length,
  imperial_starship: build("imperial_starship", "#ffe9a0", 4, "bridge nacelles", false).length,
  scout_marauder: build("scout_marauder", "#5dffc8", 2, "bridge", false).length,
  merchant_freighter: build("merchant_freighter", "#7af0ff", 2, "pods bridge", false).length,
  battleship: build("battleship", "#c5c8ff", 3, "bridge guns", false).length,
  corporate_flagship: build("corporate_flagship", "#ff77ff", 3, "bridge pods", false).length,
  escape_pod: build("escape_pod", "#55ffff", 1, "", false).length,
  tkhasi_orion: build("tkhasi_orion", "#ff6d8a", 2, "wings bridge", false).length,
};
const fr = build("merchant_freighter", "#7af0ff", 2, "pods bridge", false);
console.log(JSON.stringify({ ct, col, mule, prior, fr: spanOf(fr) }));
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
    assert "cargotranSpike" in raw and "colonialSpike" in raw and "muleSpike" in raw
    assert 'from "three"' not in raw
    assert 'getContext("webgl"' not in raw
    assert "fleet-glass-v1" in raw
    report = _report()
    assert report["prior"] == {
        "merchant_cruiser": 217,
        "imperial_starship": 311,
        "scout_marauder": 201,
        "merchant_freighter": 251,
        "battleship": 226,
        "corporate_flagship": 210,
        "escape_pod": 98,
        "tkhasi_orion": 167,
    }
    for key, (faces, accent, digest) in HAULERS.items():
        row = {"cargotran": report["ct"], "colonial_transport": report["col"], "taurean_mule": report["mule"]}[key]
        assert row["faces"] == faces, key
        assert row["accent"] == accent, key
        assert row["hash"] == digest, key
        assert row["accentEmit"] == 0
        assert row["podsSame"] is True


def test_cargotran_is_a_long_spine() -> None:
    report = _report()
    ct = report["ct"]
    span = ct["span"]
    fr = report["fr"]["size"]
    col = report["col"]["span"]["size"]
    assert span["size"][0] > fr[0] + 40
    assert span["size"][2] < fr[2] * 0.4
    assert span["size"][1] < col[1] * 0.55
    assert span["min"][1] > -12
    assert ct["shoulder"] == 0
    assert ct["lowOuter"] == 0
    assert abs(ct["head"]["top"][2]) < 3 and ct["head"]["top"][1] > 14
    assert abs(ct["side"]["top"][2]) < 3 and ct["side"]["top"][1] > 14
    assert ct["headSil"]["w"] > ct["headSil"]["h"]
    assert ct["headSil"]["h"] < report["col"]["headSil"]["h"]
    left, top, right, bottom = ct["frame"]
    assert 8 < left < right < 392, ct["frame"]
    assert 8 < top < bottom < 252, ct["frame"]


def test_colonial_is_a_tall_cabin_with_belly_tanks() -> None:
    report = _report()
    col = report["col"]
    span = col["span"]
    fr = report["fr"]["size"]
    assert span["size"][1] > span["size"][2]
    assert span["size"][1] > fr[1] * 2.5
    assert span["size"][0] < report["ct"]["span"]["size"][0] * 0.7
    assert col["shoulder"] == 0
    assert col["lowOuter"] > 20
    for side in (col["head"]["left"], col["head"]["right"]):
        assert abs(side[2]) > 16 and side[1] < -15
    assert col["head"]["bottom"][1] < -24
    assert col["head"]["top"][1] > 14 and abs(col["head"]["top"][2]) < 8
    assert col["headSil"]["h"] > col["headSil"]["w"]
    left, top, right, bottom = col["frame"]
    assert 8 < left < right < 392, col["frame"]
    assert 8 < top < bottom < 252, col["frame"]


def test_mule_is_a_low_saddle() -> None:
    report = _report()
    mule = report["mule"]
    span = mule["span"]
    fr = report["fr"]["size"]
    col = report["col"]["span"]["size"]
    assert span["size"][1] < col[1] * 0.65
    assert span["size"][2] < span["size"][0]
    assert span["size"][2] < fr[2] * 0.5
    assert span["min"][1] > -12
    assert mule["shoulder"] == 0
    assert mule["aftOuter"] > 10
    assert mule["lowOuter"] == 0
    assert abs(mule["head"]["top"][2]) < 6 and mule["head"]["top"][1] > 16
    assert abs(mule["side"]["top"][0]) < 24 and mule["side"]["top"][1] > 16
    assert mule["headSil"]["h"] < report["col"]["headSil"]["h"]
    assert mule["headSil"]["w"] > mule["headSil"]["h"]
    for side in (mule["head"]["left"], mule["side"]["left"], mule["side"]["bottom"]):
        assert side[0] < -20 and abs(side[2]) > 12
    left, top, right, bottom = mule["frame"]
    assert 8 < left < right < 392, mule["frame"]
    assert 8 < top < bottom < 252, mule["frame"]


def test_empty_shields_keep_the_hauler_accents() -> None:
    report = _report()
    ct, col, mule = report["ct"], report["col"], report["mule"]
    for row in (ct, col, mule):
        assert row["accent0"] == row["accent1"] == row["accentTw"]
        br, bg, bb = row["body1"]
        assert br < 90 and br <= bg + 15 and br < bb + 20
        er, eg, eb = row["tail0"]
        assert eg >= er - 8 and eb >= er - 8
        tr, tg, tb = row["tailTw"]
        assert tr > tg and tb > tg
    cr, cg, cb = ct["accent1"]
    assert cr > 180 and cg > 150 and cb < 120 and cr > cb and cg > cb
    gr, gg, gb = col["accent1"]
    assert gg > 170 and gg > gr + 40 and gg > gb + 40
    mr, mg, mb = mule["accent1"]
    assert mr > mg > mb and mr > 150 and mb > 80


def test_markers_clear_the_hauler_kits() -> None:
    assert _markers(0) == 0
    assert _markers(1) == 1
    assert _markers(99) == 1
    assert _markers(100) == 1
    assert _markers(101) == 2
    assert _markers(200) == 2
    assert _markers(300) == 3
    assert _markers(400) == 4
    report = _report()
    for hull in (report["ct"], report["col"], report["mule"]):
        for cam, rings in hull["rings"].items():
            for count, row in rings.items():
                assert row["got"] == int(count), (cam, count, row)
                assert row["under"] == 0 and row["overlap"] == 0 and row["clipped"] == 0, (cam, count, row)
