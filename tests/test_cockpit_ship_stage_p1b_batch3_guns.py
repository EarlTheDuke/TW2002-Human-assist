"""P1b batch 3: Missile Frigate and Havoc GunStar on the shared SVG mesh."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MESHES = ROOT / "web" / "hull-meshes.js"

# Point hashes of the two gun lofts. Other hull pins stay where their cuts left them.
GUNS = {
    "missile_frigate": (283, 111, "5b1033913c531839"),
    "havoc_gunstar": (261, 47, "37adf9e9ec450286"),
}


def _report() -> dict:
    script = r"""
import crypto from "node:crypto";
import api from "./web/hull-meshes.mjs";

function build(cls, accent, engines, detail, extra) {
  const ship = Object.assign({ class: cls, transwarp: { fitted: !!(extra && extra.tw) } }, extra || {});
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
function project(p, yaw, pitch, fit) {
  const w = rotPoint([p[0] * fit, p[1] * fit, p[2] * fit], yaw, pitch);
  const s = 900 / (430 - w[2]);
  return [200 + w[0] * s, 124 - w[1] * s];
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
function screenBox(faces, yaw, pitch, fit) {
  let minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
  for (const face of faces) for (const p of face.pts) {
    const q = project(p, yaw, pitch, fit);
    if (q[0] < minX) minX = q[0]; if (q[0] > maxX) maxX = q[0];
    if (q[1] < minY) minY = q[1]; if (q[1] > maxY) maxY = q[1];
  }
  return [Math.round(minX), Math.round(minY), Math.round(maxX), Math.round(maxY)];
}
function engines(faces) {
  const clusters = [];
  for (const face of faces) {
    if (!face.emissive) continue;
    const c = centroid(face);
    if (c[0] > -30) continue;
    let hit = null;
    for (const group of clusters) {
      if (Math.abs(c[2] - group.z / group.n) < 3.2) { hit = group; break; }
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
function notch(faces, markers, yaw, pitch, fit) {
  const slots = api.escortSlots(markers, faces, fit, yaw, pitch);
  const tips = [];
  for (const face of faces) for (const p of face.pts) {
    if (p[0] > 48 && Math.abs(p[2]) > 4) tips.push(project(p, yaw, pitch, fit));
  }
  const mid = tips.reduce((sum, q) => sum + q[0], 0) / tips.length;
  const left = tips.filter((q) => q[0] < mid);
  const right = tips.filter((q) => q[0] >= mid);
  const innerL = Math.max.apply(null, left.map((q) => q[0]));
  const innerR = Math.min.apply(null, right.map((q) => q[0]));
  const y0 = Math.min.apply(null, tips.map((q) => q[1]));
  const y1 = Math.max.apply(null, tips.map((q) => q[1]));
  let inside = 0;
  for (const slot of slots) {
    const q = project([slot.x, slot.y, slot.z], yaw, pitch, fit);
    if (q[0] > innerL + 1.5 && q[0] < innerR - 1.5 && q[1] >= y0 && q[1] <= y1) inside += 1;
  }
  return { gap: Math.round((innerR - innerL) * 10) / 10, inside };
}
function tailEmit(faces) {
  const picked = faces.filter((face) => {
    if (!face.emissive) return false;
    return centroid(face)[0] < -40;
  });
  return meanFill(picked, () => true, 0);
}
const cams = {
  three: [0.82, 0.5, 1.12],
  phone: [0.82, 0.5, 0.72],
  panel: [0.82, 0.5, 0.76],
  head: [-1.35, 0.2, 1],
  side: [1.35, 0.18, 1.15],
};
function sameDetail(cls, accent, engines) {
  const base = hashPts(build(cls, accent, engines, cls === "missile_frigate" ? "rails bridge" : "guns bridge"));
  const details = ["rails bridge", "bridge", "rails", "guns", "guns bridge", "", "pods"];
  for (const detail of details) {
    if (hashPts(build(cls, accent, engines, detail)) !== base) return false;
    if (hashPts(build(cls, accent, engines === 2 ? 4 : 2, detail, { photon_missiles: 10, scanner: "holo" })) !== base) return false;
  }
  return true;
}
const fr = build("missile_frigate", "#ffb15a", 2, "rails bridge");
const hv = build("havoc_gunstar", "#ff8844", 3, "guns bridge");
const frTw = build("missile_frigate", "#ffb15a", 2, "rails bridge", { tw: true });
const hvTw = build("havoc_gunstar", "#ff8844", 3, "guns bridge", { tw: true });
const imp = build("imperial_starship", "#ffe9a0", 4, "bridge nacelles");
const bs = build("battleship", "#c5c8ff", 3, "bridge guns");
const frMissile = fr.filter((f) => f.accent && f.rgb[1] >= 120 && centroid(f)[1] > 9);
const frNose = fr.filter((f) => f.accent && f.rgb[1] < 120);
const frCanopy = fr.filter((f) => !f.accent && !f.emissive && f.rgb[0] > 200 && f.rgb[2] > 180);
const frRail = fr.filter((f) => !f.accent && !f.emissive && centroid(f)[1] > 6 && centroid(f)[1] < 8.6 && Math.abs(centroid(f)[2]) > 4);
let noseX = -1e9, missileX = -1e9;
for (const face of fr) for (const p of face.pts) {
  if (Math.abs(p[2]) < 3.2 && p[1] < 7 && p[0] > noseX) noseX = p[0];
  if (p[1] > 10 && p[0] > missileX) missileX = p[0];
}
let bodyX = -1e9, tipX = -1e9;
for (const face of hv) for (const p of face.pts) {
  if (Math.abs(p[2]) < 4.5 && p[0] > bodyX) bodyX = p[0];
  if (Math.abs(p[2]) > 5 && p[0] > tipX) tipX = p[0];
}
const bsBarrel = bs.filter((f) => f.accent && centroid(f)[1] > 16);
function rings(faces, counts) {
  const out = {};
  for (const [name, spec] of Object.entries(cams)) {
    out[name] = {};
    for (const n of counts) out[name][String(n)] = clearance(faces, n, spec[2], spec[0], spec[1]);
  }
  return out;
}
const prior = {
  merchant_cruiser: build("merchant_cruiser", "#7aa2ff", 2, "pods bridge").length,
  imperial_starship: imp.length,
  scout_marauder: build("scout_marauder", "#5dffc8", 2, "bridge").length,
  merchant_freighter: build("merchant_freighter", "#7af0ff", 2, "pods bridge").length,
  battleship: bs.length,
  corporate_flagship: build("corporate_flagship", "#ff77ff", 3, "bridge pods").length,
  escape_pod: build("escape_pod", "#55ffff", 1, "").length,
  tkhasi_orion: build("tkhasi_orion", "#ff6d8a", 2, "wings bridge").length,
  cargotran: build("cargotran", "#ffe566", 2, "pods").length,
  colonial_transport: build("colonial_transport", "#7dff7d", 2, "pods").length,
  taurean_mule: build("taurean_mule", "#d7b48a", 2, "pods").length,
};
const report = {
  fr: {
    faces: fr.length,
    accent: fr.filter((f) => f.accent).length,
    accentEmit: fr.filter((f) => f.accent && f.emissive).length,
    hash: hashPts(fr),
    same: sameDetail("missile_frigate", "#ffb15a", 2),
    span: spanOf(fr),
    missile: spanOf(frMissile),
    nose: spanOf(frNose),
    canopy: spanOf(frCanopy),
    rail: spanOf(frRail),
    noseX: Math.round(noseX * 10) / 10,
    missileX: Math.round(missileX * 10) / 10,
    accent0: meanFill(fr, (f) => f.accent, 0),
    accent1: meanFill(fr, (f) => f.accent, 1),
    body1: meanFill(fr, (f) => !f.accent && !f.emissive, 1),
    noseFill: meanFill(frNose, () => true, 1),
    bodyFill: meanFill(frMissile, () => true, 1),
    tail0: tailEmit(fr),
    tailTw: tailEmit(frTw),
    engines: engines(fr),
    rings: rings(fr, [0, 1, 50, 100]),
    frame: screenBox(fr, 0.82, 0.5, 1.12),
  },
  hv: {
    faces: hv.length,
    accent: hv.filter((f) => f.accent).length,
    accentEmit: hv.filter((f) => f.accent && f.emissive).length,
    hash: hashPts(hv),
    same: sameDetail("havoc_gunstar", "#ff8844", 3),
    span: spanOf(hv),
    bodyX: Math.round(bodyX * 10) / 10,
    tipX: Math.round(tipX * 10) / 10,
    accent0: meanFill(hv, (f) => f.accent, 0),
    accent1: meanFill(hv, (f) => f.accent, 1),
    accentTw: meanFill(hvTw, (f) => f.accent, 1),
    body1: meanFill(hv, (f) => !f.accent && !f.emissive, 1),
    tail0: tailEmit(hv),
    tailTw: tailEmit(hvTw),
    engines: engines(hv),
    rings: rings(hv, [0, 1, 100]),
    frame: screenBox(hv, 0.82, 0.5, 1.12),
    notch: {
      three: notch(hv, 100, 0.82, 0.5, 1.12),
      head: notch(hv, 100, -1.35, 0.2, 1),
      side: notch(hv, 100, 1.35, 0.18, 1.15),
    },
  },
  prior,
  imp: spanOf(imp),
  bs: spanOf(bs),
  barrel: spanOf(bsBarrel),
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
    assert "frigateSpike" in raw and "havocSpike" in raw
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
    }
    for key, (faces, accent, digest) in GUNS.items():
        row = report["fr"] if key == "missile_frigate" else report["hv"]
        assert row["faces"] == faces, key
        assert row["accent"] == accent, key
        assert row["hash"] == digest, key
        assert row["accentEmit"] == 0
        assert row["same"] is True


def test_frigate_is_a_long_slim_photon_boat() -> None:
    report = _report()
    fr = report["fr"]
    span = fr["span"]["size"]
    imp = report["imp"]["size"]
    bs = report["bs"]["size"]
    assert span[0] < imp[0]
    assert span[0] > bs[0]
    assert span[2] < bs[2] * 0.4
    assert fr["noseX"] > fr["missileX"] + 12
    assert fr["missile"]["size"][0] > fr["canopy"]["size"][0] * 2
    assert fr["missile"]["size"][1] > fr["canopy"]["size"][1]
    assert fr["missile"]["size"][1] > report["barrel"]["size"][1] * 2
    assert fr["rail"]["size"][1] < 4
    assert fr["rail"]["size"][0] < span[0] * 0.55
    assert len(fr["engines"]) == 2
    assert all(item["y"] < 0 for item in fr["engines"])
    assert max(abs(item["z"]) for item in fr["engines"]) < span[2] / 2
    left, top, right, bottom = fr["frame"]
    assert 8 < left < right < 392, fr["frame"]
    assert 8 < top < bottom < 252, fr["frame"]


def test_havoc_is_a_short_split_prow() -> None:
    report = _report()
    hv = report["hv"]
    span = hv["span"]["size"]
    bs = report["bs"]["size"]
    imp = report["imp"]["size"]
    assert hv["tipX"] > hv["bodyX"] + 20
    assert span[0] < imp[0]
    assert span[2] < bs[2] - 40
    assert span[1] < bs[1]
    assert len(hv["engines"]) == 3
    assert all(item["y"] < 0 for item in hv["engines"])
    assert max(abs(item["z"]) for item in hv["engines"]) < span[2] / 2
    for cam, row in hv["notch"].items():
        assert row["gap"] > 8, (cam, row)
        assert row["inside"] == 0, (cam, row)
    left, top, right, bottom = hv["frame"]
    assert 8 < left < right < 392, hv["frame"]
    assert 8 < top < bottom < 252, hv["frame"]


def test_empty_shields_keep_the_gun_accents() -> None:
    report = _report()
    fr, hv = report["fr"], report["hv"]
    assert fr["accent0"] == fr["accent1"]
    assert hv["accent0"] == hv["accent1"] == hv["accentTw"]
    for row in (fr, hv):
        br, bg, bb = row["body1"]
        assert br < 90 and br <= bg + 15 and br < bb + 20
        er, eg, eb = row["tail0"]
        assert eg >= er - 8 and eb >= er - 8
        tr, tg, tb = row["tailTw"]
        assert tr > tg and tb > tg
    nr, ng, nb = fr["noseFill"]
    br, bg, bb = fr["bodyFill"]
    assert ng < bg - 40 and nb < bb - 30 and nr > 160
    hr, hg, hb = hv["accent1"]
    assert hr > 160 and hr > hg and hg > hb


def test_markers_clear_the_missiles_and_the_prongs() -> None:
    assert _markers(0) == 0
    assert _markers(1) == 1
    assert _markers(99) == 1
    assert _markers(100) == 1
    assert _markers(101) == 2
    assert _markers(4900) == 49
    assert _markers(4901) == 50
    assert _markers(5000) == 50
    assert _markers(9900) == 99
    assert _markers(9901) == 100
    assert _markers(10000) == 100
    report = _report()
    expect = {
        "fr": {"0": 0, "1": 1, "50": 50, "100": 100},
        "hv": {"0": 0, "1": 1, "100": 100},
    }
    for key, counts in expect.items():
        rings = report[key]["rings"]
        for cam, rows in rings.items():
            for count, row in rows.items():
                assert row["got"] == counts[count], (key, cam, count, row)
                assert row["under"] == 0 and row["overlap"] == 0 and row["clipped"] == 0, (key, cam, count, row)
