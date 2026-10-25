"""P1b batch 5: Tholian Sentinel and Interdictor Cruiser on the shared SVG mesh."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MESHES = ROOT / "web" / "hull-meshes.js"

# Point hashes of the brick and the hoops. Other hull pins stay where their cuts left them.
BRICK = {
    "tholian_sentinel": (169, 23, "7650706109f94fb1"),
    "interdictor_cruiser": (341, 123, "c3d45f327a3c6564"),
}


def _report() -> dict:
    script = r"""
import crypto from "node:crypto";
import api from "./web/hull-meshes.mjs";

function build(cls, accent, engines, detail, extra) {
  const ship = Object.assign({ class: cls, transwarp: { fitted: !!(extra && extra.tw) }, scanner: extra && extra.scanner, photon_missiles: extra && extra.photons }, extra || {});
  return api.buildHullFaces(ship, { accent, detail, engines, name: cls });
}
function hashPts(faces) {
  const body = JSON.stringify(faces.map((f) => f.pts.map((p) => p.map((n) => Math.round(n * 1000) / 1000))));
  return crypto.createHash("sha256").update(body).digest("hex").slice(0, 16);
}
function centroid(face) {
  const c = [0, 0, 0];
  for (const p of face.pts) { c[0] += p[0]; c[1] += p[1]; c[2] += p[2]; }
  return c.map((v) => v / face.pts.length);
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
function clearance(faces, markers, fit, yaw, pitch, outer) {
  const slots = api.escortSlots(markers, faces, fit, yaw, pitch);
  const Rb = api.hullRadius(faces);
  const grid = maskOf(faces, yaw, pitch, fit);
  let under = 0, overlap = 0, clipped = 0, hole = 0;
  for (const slot of slots) {
    if (Math.hypot(slot.x, slot.y, slot.z) < Rb - 1e-6) under += 1;
    if (outer && Math.hypot(slot.y, slot.z) < outer) hole += 1;
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
  return { got: slots.length, under, overlap, clipped, hole };
}
function engines(faces, xMax) {
  const clusters = [];
  for (const face of faces) {
    if (!face.emissive) continue;
    const c = centroid(face);
    if (c[0] > xMax) continue;
    let hit = null;
    for (const group of clusters) {
      if (Math.hypot(c[1] - group.y / group.n, c[2] - group.z / group.n) < 2.4) { hit = group; break; }
    }
    if (!hit) {
      hit = { y: 0, z: 0, n: 0 };
      clusters.push(hit);
    }
    hit.y += c[1]; hit.z += c[2]; hit.n += 1;
  }
  return clusters.map((b) => ({
    y: Math.round(b.y / b.n * 10) / 10,
    z: Math.round(b.z / b.n * 10) / 10,
  }));
}
function tailEmit(faces) {
  const picked = faces.filter((face) => face.emissive && centroid(face)[0] < -15);
  return meanFill(picked, () => true, 0);
}
function sameDetail(cls, accent, engines, baseDetail) {
  const base = hashPts(build(cls, accent, engines, baseDetail));
  const details = [baseDetail, "bridge", "ring", "ring bridge", "dish", "armor", "hoop", ""];
  for (const detail of details) {
    if (hashPts(build(cls, accent, engines === 2 ? 4 : 2, detail, { scanner: "holo", photons: 10 })) !== base) return false;
  }
  return true;
}
const cams = {
  ts: { three: [0.82, 0.5, 1.12], phone: [0.82, 0.5, 0.72], head: [-1.35, 0.2, 1], side: [1.35, 0.18, 1.15] },
  ic: { three: [0.82, 0.5, 0.4], phone: [0.82, 0.5, 0.4], head: [-1.35, 0.2, 0.4], side: [1.35, 0.18, 0.4] },
};
function rings(faces, spec, counts, outer) {
  const out = {};
  for (const [name, cam] of Object.entries(spec)) {
    out[name] = {};
    for (const n of counts) out[name][String(n)] = clearance(faces, n, cam[2], cam[0], cam[1], outer);
  }
  return out;
}
const ts = build("tholian_sentinel", "#62f0c8", 2, "bridge");
const ic = build("interdictor_cruiser", "#ff5cab", 4, "ring bridge");
const tsTw = build("tholian_sentinel", "#62f0c8", 2, "bridge", { tw: true });
const icTw = build("interdictor_cruiser", "#ff5cab", 4, "ring bridge", { tw: true });
const col = build("colonial_transport", "#7dff7d", 2, "pods");
const con = build("constellation", "#d0d6ff", 4, "nacelles bridge");
let bodyCyl = 0;
for (const face of ic) {
  if (face.accent || face.emissive) continue;
  for (const p of face.pts) bodyCyl = Math.max(bodyCyl, Math.hypot(p[1], p[2]));
}
const prior = {
  merchant_cruiser: build("merchant_cruiser", "#7aa2ff", 2, "pods bridge").length,
  imperial_starship: build("imperial_starship", "#ffe9a0", 4, "bridge nacelles").length,
  scout_marauder: build("scout_marauder", "#5dffc8", 2, "bridge").length,
  merchant_freighter: build("merchant_freighter", "#7af0ff", 2, "pods bridge").length,
  battleship: build("battleship", "#c5c8ff", 3, "bridge guns").length,
  corporate_flagship: build("corporate_flagship", "#ff77ff", 3, "bridge pods").length,
  escape_pod: build("escape_pod", "#55ffff", 1, "").length,
  tkhasi_orion: build("tkhasi_orion", "#ff6d8a", 2, "wings bridge").length,
  cargotran: build("cargotran", "#ffe566", 2, "pods").length,
  colonial_transport: col.length,
  taurean_mule: build("taurean_mule", "#d7b48a", 2, "pods").length,
  missile_frigate: build("missile_frigate", "#ffb15a", 2, "rails bridge").length,
  havoc_gunstar: build("havoc_gunstar", "#ff8844", 3, "guns bridge").length,
  star_master: build("star_master", "#9ad7ff", 2, "dish bridge").length,
  constellation: con.length,
};
const report = {
  ts: {
    faces: ts.length,
    accent: ts.filter((f) => f.accent).length,
    accentEmit: ts.filter((f) => f.accent && f.emissive).length,
    hash: hashPts(ts),
    same: sameDetail("tholian_sentinel", "#62f0c8", 2, "bridge"),
    span: spanOf(ts),
    engines: engines(ts, -10),
    accent0: meanFill(ts, (f) => f.accent, 0),
    accent1: meanFill(ts, (f) => f.accent, 1),
    body1: meanFill(ts, (f) => !f.accent && !f.emissive, 1),
    tail0: tailEmit(ts),
    tailTw: tailEmit(tsTw),
    rings: rings(ts, cams.ts, [0, 1, 2, 24, 25], 0),
  },
  ic: {
    faces: ic.length,
    accent: ic.filter((f) => f.accent).length,
    accentEmit: ic.filter((f) => f.accent && f.emissive).length,
    hash: hashPts(ic),
    same: sameDetail("interdictor_cruiser", "#ff5cab", 4, "ring bridge"),
    span: spanOf(ic),
    bodyCyl: Math.round(bodyCyl * 10) / 10,
    engines: engines(ic, -20),
    accent0: meanFill(ic, (f) => f.accent, 0),
    accent1: meanFill(ic, (f) => f.accent, 1),
    body1: meanFill(ic, (f) => !f.accent && !f.emissive, 1),
    tail0: tailEmit(ic),
    tailTw: tailEmit(icTw),
    rings: rings(ic, cams.ic, [0, 1, 2, 500, 999, 1000], 112),
  },
  col: { faces: col.length, hash: hashPts(col) },
  con: { faces: con.length, hash: hashPts(con) },
  prior,
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
    assert "sentinelSpike" in raw and "interdictorSpike" in raw
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
        "cargotran": 212,
        "colonial_transport": 251,
        "taurean_mule": 209,
        "missile_frigate": 283,
        "havoc_gunstar": 261,
        "star_master": 183,
        "constellation": 311,
    }
    assert report["col"]["faces"] == 251
    assert report["con"]["faces"] == 311
    for key, (faces, accent, digest) in BRICK.items():
        row = report["ts"] if key == "tholian_sentinel" else report["ic"]
        assert row["faces"] == faces, key
        assert row["accent"] == accent, key
        assert row["hash"] == digest, key
        assert row["accentEmit"] == 0
        assert row["same"] is True


def test_sentinel_is_a_short_square_brick() -> None:
    report = _report()
    ts = report["ts"]
    span = ts["span"]["size"]
    col = report["prior"]["colonial_transport"]
    assert col == 251
    assert span[0] < 60
    assert abs(span[1] - span[2]) < 1
    assert span[1] > 24
    assert ts["span"]["r"] < 40
    assert len(ts["engines"]) == 2
    assert all(item["y"] < -4 for item in ts["engines"])
    assert max(abs(item["z"]) for item in ts["engines"]) < span[2] / 2


def test_interdictor_hoops_set_the_radius() -> None:
    report = _report()
    ic = report["ic"]
    span = ic["span"]["size"]
    assert ic["span"]["r"] > 112
    assert span[1] > span[0] * 2
    assert span[2] > span[0] * 2
    assert ic["bodyCyl"] < 20
    assert len(ic["engines"]) == 4
    assert len({item["y"] for item in ic["engines"]}) == 1
    assert all(item["y"] < 0 for item in ic["engines"])
    assert max(abs(item["z"]) for item in ic["engines"]) < 12
    ys = [item["y"] for item in ic["engines"]]
    assert max(ys) - min(ys) < 0.2


def test_empty_shields_keep_the_mint_and_the_pink() -> None:
    report = _report()
    ts, ic = report["ts"], report["ic"]
    assert ts["accent0"] == ts["accent1"]
    assert ic["accent0"] == ic["accent1"]
    for row in (ts, ic):
        br, bg, bb = row["body1"]
        assert br < 90 and br <= bg + 15 and br < bb + 20
        er, eg, eb = row["tail0"]
        assert eg >= er - 8 and eb >= er - 8
        tr, tg, tb = row["tailTw"]
        assert tr > tg and tb > tg
    sr, sg, sb = ts["accent1"]
    assert sg > sb > sr and sg > 160
    cr, cg, cb = ic["accent1"]
    assert cr > cb > cg and cr > 160


def test_markers_clear_the_slabs_and_the_hoops() -> None:
    assert _markers(0) == 0
    assert _markers(1) == 1
    assert _markers(50) == 1
    assert _markers(99) == 1
    assert _markers(100) == 1
    assert _markers(101) == 2
    assert _markers(2400) == 24
    assert _markers(2401) == 25
    assert _markers(2499) == 25
    assert _markers(2500) == 25
    assert _markers(50000) == 500
    assert _markers(99900) == 999
    assert _markers(99901) == 1000
    assert _markers(99999) == 1000
    assert _markers(100000) == 1000
    report = _report()
    for key in ("ts", "ic"):
        rings = report[key]["rings"]
        for cam, rows in rings.items():
            for count, row in rows.items():
                assert row["got"] == int(count), (key, cam, count, row)
                assert row["under"] == 0 and row["overlap"] == 0 and row["clipped"] == 0, (key, cam, count, row)
                if key == "ic" and int(count) > 0:
                    assert row["hole"] == 0, (cam, count, row)
