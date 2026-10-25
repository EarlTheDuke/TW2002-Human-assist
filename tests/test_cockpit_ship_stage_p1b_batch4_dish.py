"""P1b batch 4: Star Master and Constellation on the shared SVG mesh."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MESHES = ROOT / "web" / "hull-meshes.js"

# Point hashes of the dish and the X. Other hull pins stay where their cuts left them.
DISH = {
    "star_master": (183, 29, "7c79af13cc74372b"),
    "constellation": (311, 91, "787b41d482d6501a"),
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
  let under = 0, overlap = 0, clipped = 0, crook = 0, mast = 0;
  for (const slot of slots) {
    if (Math.hypot(slot.x, slot.y, slot.z) < Rb - 1e-6) under += 1;
    if (slot.x < 8 && slot.x > -60 && Math.hypot(slot.y, slot.z) < 14) crook += 1;
    if (slot.y < 26 && Math.hypot(slot.x, slot.z) < 20) mast += 1;
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
  return { got: slots.length, under, overlap, clipped, crook, mast };
}
function engines(faces) {
  const clusters = [];
  for (const face of faces) {
    if (!face.emissive) continue;
    const c = centroid(face);
    let hit = null;
    for (const group of clusters) {
      if (Math.hypot(c[1] - group.y / group.n, c[2] - group.z / group.n) < 3.2) { hit = group; break; }
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
  const picked = faces.filter((face) => face.emissive && centroid(face)[0] < -20);
  return meanFill(picked, () => true, 0);
}
function sameDetail(cls, accent, engines, baseDetail) {
  const base = hashPts(build(cls, accent, engines, baseDetail));
  const details = [baseDetail, "bridge", "dish", "dish bridge", "nacelles", "nacelles bridge", "quad", "", "pods"];
  for (const detail of details) {
    if (hashPts(build(cls, accent, engines, detail)) !== base) return false;
    if (hashPts(build(cls, accent, engines === 2 ? 4 : 2, detail, { photon_missiles: 10, scanner: cls === "constellation" ? "density" : "holo" })) !== base) return false;
  }
  return true;
}
const cams = {
  three: [0.82, 0.5, 1.12],
  phone: [0.82, 0.5, 0.72],
  head: [-1.35, 0.2, 1],
  side: [1.35, 0.18, 1.15],
};
function rings(faces, counts) {
  const out = {};
  for (const [name, spec] of Object.entries(cams)) {
    out[name] = {};
    for (const n of counts) out[name][String(n)] = clearance(faces, n, spec[2], spec[0], spec[1]);
  }
  return out;
}
const sm = build("star_master", "#9ad7ff", 2, "dish bridge");
const con = build("constellation", "#d0d6ff", 4, "nacelles bridge");
const smTw = build("star_master", "#9ad7ff", 2, "dish bridge", { tw: true });
const conTw = build("constellation", "#d0d6ff", 4, "nacelles bridge", { tw: true });
const fs = build("corporate_flagship", "#ff77ff", 3, "bridge pods");
const fsTw = build("corporate_flagship", "#ff77ff", 3, "bridge pods", { tw: true });
const imp = build("imperial_starship", "#ffe9a0", 4, "bridge nacelles");
const bs = build("battleship", "#c5c8ff", 3, "bridge guns");
const hv = build("havoc_gunstar", "#ff8844", 3, "guns bridge");
const plate = sm.filter((f) => f.accent && centroid(f)[1] > 16);
const mast = sm.filter((f) => !f.accent && !f.emissive && centroid(f)[1] > 10 && Math.abs(centroid(f)[2]) < 2 && centroid(f)[1] < 26);
let bodyZ = 0, bodyY = 0, globalY = -1e9, accentY = -1e9;
for (const face of sm) for (const p of face.pts) {
  if (p[1] > globalY) globalY = p[1];
  if (face.accent && p[1] > accentY) accentY = p[1];
}
for (const face of sm) {
  if (face.accent || face.emissive) continue;
  const c = centroid(face);
  if (c[1] > 8 || Math.abs(c[2]) > 8) continue;
  for (const p of face.pts) {
    bodyZ = Math.max(bodyZ, Math.abs(p[2]));
    bodyY = Math.max(bodyY, p[1]);
  }
}
let noseX = -1e9, tipX = 1e9, arm = 0, bodyArm = 0, dish = 0;
for (const face of con) {
  const c = centroid(face);
  if (face.accent && c[1] > 22 && Math.abs(c[2]) < 4) dish += 1;
  for (const p of face.pts) {
    if (!face.accent && !face.emissive && Math.abs(p[2]) < 4 && Math.abs(p[1]) < 5 && p[0] > noseX) noseX = p[0];
    if (face.accent && p[0] < tipX) tipX = p[0];
    if (face.accent) arm = Math.max(arm, Math.hypot(p[1], p[2]));
    if (!face.accent && !face.emissive && Math.abs(c[1]) < 6) bodyArm = Math.max(bodyArm, Math.abs(p[2]), Math.abs(p[1]));
  }
}
const prior = {
  merchant_cruiser: build("merchant_cruiser", "#7aa2ff", 2, "pods bridge").length,
  imperial_starship: imp.length,
  scout_marauder: build("scout_marauder", "#5dffc8", 2, "bridge").length,
  merchant_freighter: build("merchant_freighter", "#7af0ff", 2, "pods bridge").length,
  battleship: bs.length,
  corporate_flagship: fs.length,
  escape_pod: build("escape_pod", "#55ffff", 1, "").length,
  tkhasi_orion: build("tkhasi_orion", "#ff6d8a", 2, "wings bridge").length,
  cargotran: build("cargotran", "#ffe566", 2, "pods").length,
  colonial_transport: build("colonial_transport", "#7dff7d", 2, "pods").length,
  taurean_mule: build("taurean_mule", "#d7b48a", 2, "pods").length,
  missile_frigate: build("missile_frigate", "#ffb15a", 2, "rails bridge").length,
  havoc_gunstar: hv.length,
};
const report = {
  sm: {
    faces: sm.length,
    accent: sm.filter((f) => f.accent).length,
    accentEmit: sm.filter((f) => f.accent && f.emissive).length,
    hash: hashPts(sm),
    same: sameDetail("star_master", "#9ad7ff", 2, "dish bridge"),
    span: spanOf(sm),
    plate: spanOf(plate),
    mast: spanOf(mast),
    mastN: mast.length,
    bodyZ: Math.round(bodyZ * 10) / 10,
    bodyY: Math.round(bodyY * 10) / 10,
    globalY: Math.round(globalY * 10) / 10,
    accentY: Math.round(accentY * 10) / 10,
    engines: engines(sm),
    accent0: meanFill(sm, (f) => f.accent, 0),
    accent1: meanFill(sm, (f) => f.accent, 1),
    body1: meanFill(sm, (f) => !f.accent && !f.emissive, 1),
    tail0: tailEmit(sm),
    tailTw: tailEmit(smTw),
    rings: rings(sm, [0, 1, 50]),
  },
  con: {
    faces: con.length,
    accent: con.filter((f) => f.accent).length,
    accentEmit: con.filter((f) => f.accent && f.emissive).length,
    hash: hashPts(con),
    same: sameDetail("constellation", "#d0d6ff", 4, "nacelles bridge"),
    span: spanOf(con),
    noseX: Math.round(noseX * 10) / 10,
    tipX: Math.round(tipX * 10) / 10,
    arm: Math.round(arm * 10) / 10,
    bodyArm: Math.round(bodyArm * 10) / 10,
    dish,
    engines: engines(con),
    accent0: meanFill(con, (f) => f.accent, 0),
    accent1: meanFill(con, (f) => f.accent, 1),
    body1: meanFill(con, (f) => !f.accent && !f.emissive, 1),
    tail0: tailEmit(con),
    tailTw: tailEmit(conTw),
    rings: rings(con, [0, 1, 50]),
  },
  prior,
  fs: { faces: fs.length, span: spanOf(fs), accent0: meanFill(fs, (f) => f.accent, 0), accentTw: meanFill(fsTw, (f) => f.accent, 1), tail0: tailEmit(fs), tailTw: tailEmit(fsTw), hash: hashPts(fs) },
  imp: { faces: imp.length, span: spanOf(imp), hash: hashPts(imp) },
  bs: spanOf(bs),
  hv: spanOf(hv),
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
    assert "starMasterSpike" in raw and "constellationSpike" in raw
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
    }
    assert report["fs"]["faces"] == 210
    assert report["imp"]["faces"] == 311
    for key, (faces, accent, digest) in DISH.items():
        row = report["sm"] if key == "star_master" else report["con"]
        assert row["faces"] == faces, key
        assert row["accent"] == accent, key
        assert row["hash"] == digest, key
        assert row["accentEmit"] == 0
        assert row["same"] is True


def test_star_master_is_a_plate_on_a_stick() -> None:
    report = _report()
    sm = report["sm"]
    plate = sm["plate"]["size"]
    assert plate[0] == plate[2] == 44
    assert plate[1] < 2
    assert plate[2] > sm["bodyZ"] * 2
    assert sm["accentY"] == sm["globalY"]
    assert sm["globalY"] > sm["bodyY"] + 12
    assert sm["mastN"] >= 6
    assert sm["mast"]["size"][0] < 3 and sm["mast"]["size"][2] < 3
    assert sm["span"]["size"][1] < report["fs"]["span"]["size"][1]
    assert sm["span"]["size"][0] < report["imp"]["span"]["size"][0]
    assert len(sm["engines"]) == 2
    assert all(item["y"] < 0 for item in sm["engines"])
    assert max(abs(item["z"]) for item in sm["engines"]) < sm["bodyZ"]


def test_constellation_is_an_x_past_the_tail() -> None:
    report = _report()
    con = report["con"]
    span = con["span"]["size"]
    assert con["tipX"] < -50
    assert con["noseX"] > con["tipX"] + 80
    assert con["arm"] > con["bodyArm"] + 10
    assert con["dish"] == 0
    assert span[0] < report["imp"]["span"]["size"][0]
    assert span[2] < report["bs"]["size"][2] - 30
    assert span[1] < report["fs"]["span"]["size"][1]
    assert len(con["engines"]) == 4
    assert all(abs(item["y"]) > 8 and abs(item["z"]) > 8 for item in con["engines"])
    assert max(abs(item["y"]) for item in con["engines"]) < con["arm"]
    assert max(abs(item["z"]) for item in con["engines"]) < con["arm"]


def test_empty_shields_keep_the_dish_and_the_x() -> None:
    report = _report()
    sm, con = report["sm"], report["con"]
    assert sm["accent0"] == sm["accent1"]
    assert con["accent0"] == con["accent1"]
    for row in (sm, con):
        br, bg, bb = row["body1"]
        assert br < 90 and br <= bg + 15 and br < bb + 20
        er, eg, eb = row["tail0"]
        assert eg >= er - 8 and eb >= er - 8
        tr, tg, tb = row["tailTw"]
        assert tr > tg and tb > tg
    sr, sg, sb = sm["accent1"]
    assert sb > sg > sr and sb > 160
    cr, cg, cb = con["accent1"]
    assert cb > cg > cr and cb > 160
    fr, fg, fb = report["fs"]["accent0"]
    assert fr == fb and fr > fg + 40
    assert report["fs"]["accentTw"] == report["fs"]["accent0"]
    er, eg, eb = report["fs"]["tail0"]
    assert eg >= er - 8 and eb >= er - 8
    tr, tg, tb = report["fs"]["tailTw"]
    assert tr > tg and tb > tg


def test_markers_clear_the_plate_and_the_nacelles() -> None:
    assert _markers(0) == 0
    assert _markers(1) == 1
    assert _markers(99) == 1
    assert _markers(100) == 1
    assert _markers(101) == 2
    assert _markers(4900) == 49
    assert _markers(4901) == 50
    assert _markers(4999) == 50
    assert _markers(5000) == 50
    report = _report()
    for key in ("sm", "con"):
        rings = report[key]["rings"]
        for cam, rows in rings.items():
            for count, row in rows.items():
                assert row["got"] == int(count), (key, cam, count, row)
                assert row["under"] == 0 and row["overlap"] == 0 and row["clipped"] == 0, (key, cam, count, row)
            assert rows["50"]["crook"] == 0, (key, cam)
        if key == "sm":
            for cam, rows in rings.items():
                assert rows["50"]["mast"] == 0, cam
