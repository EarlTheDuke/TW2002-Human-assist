"""P1 spike: Merchant and Imperial silhouettes, 100:1 escorts, accent at shields 0."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MESHES = ROOT / "web" / "hull-meshes.js"
JS = ROOT / "web" / "redesign.js"
CSS = ROOT / "web" / "redesign.css"

# Point hashes of the hulls that stay on fleet-glass (detail "bridge", engines 2).
# Merchant, Imperial, Scout, Freighter, BattleShip, Corporate FlagShip,
# Escape Pod, T'Khasi Orion, CargoTran, Colonial Transport, and Taurean Mule
# are cut on the spike path and are not in this table. The hauler pins live in
# test_cockpit_ship_stage_p1b_batch2_haulers.py.
FLEET_GLASS = {
    "missile_frigate": ("135", "eed600b7b1126d27"),
    "havoc_gunstar": ("147", "a1abdd87ac67f243"),
    "star_master": ("127", "694a795927c02cbe"),
    "constellation": ("183", "f1a9a05ad8ba5fcc"),
    "tholian_sentinel": ("135", "92b22194c83653fb"),
    "interdictor_cruiser": ("189", "d3f56821c8a71966"),
}


def _report() -> dict:
    script = r"""
import crypto from "node:crypto";
import fs from "node:fs";
import zlib from "node:zlib";
import api from "./web/hull-meshes.mjs";

function hashPts(faces) {
  const body = JSON.stringify(faces.map((f) => f.pts.map((p) => p.map((n) => Math.round(n * 1000) / 1000))));
  return crypto.createHash("sha256").update(body).digest("hex").slice(0, 16);
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
    const bx = world[2][0] - world[0][0], by = world[2][1] - world[0][1];
    const nz = ax * by - ay * bx;
    const len = Math.hypot(ay * (world[2][2] - world[0][2]) - az * by, az * bx - ax * (world[2][2] - world[0][2]), nz) || 1;
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
function clearance(cls, accent, engines, detail, markers, fit) {
  const faces = api.buildHullFaces({ class: cls, transwarp: {} }, { accent, detail, engines, name: cls });
  const slots = api.escortSlots(markers, faces, fit, 0.82, 0.5);
  const Rb = api.hullRadius(faces);
  const grid = maskOf(faces, 0.82, 0.5, fit);
  let under = 0, overlap = 0, clipped = 0;
  for (const slot of slots) {
    if (Math.hypot(slot.x, slot.y, slot.z) < Rb - 1e-6) under += 1;
    const w = rotPoint([slot.x * fit, slot.y * fit, slot.z * fit], 0.82, 0.5);
    const s = 900 / (430 - w[2]);
    const x = 200 + w[0] * s, y = 124 - w[1] * s;
    const box = [x - 3.1, y - 4, x + 3.1, y + 4];
    if (box[0] < 0 || box[2] > 400 || box[1] < 0 || box[3] > 260) clipped += 1;
    const top = Math.max(0, Math.floor(box[1])), bot = Math.min(259, Math.ceil(box[3]));
    const left = Math.max(0, Math.floor(box[0])), right = Math.min(399, Math.ceil(box[2]));
    let hit = false;
    for (let yy = top; yy <= bot && !hit; yy++) for (let xx = left; xx <= right; xx++) if (grid[yy * 400 + xx]) { hit = true; break; }
    if (hit) overlap += 1;
  }
  let minX = 1e9, maxX = -1e9;
  for (const face of faces) for (const p of face.pts) { if (p[0] < minX) minX = p[0]; if (p[0] > maxX) maxX = p[0]; }
  return { faces: faces.length, accent: faces.filter((f) => f.accent).length, len: Math.round((maxX - minX) * 10) / 10,
    got: slots.length, under, overlap, clipped, accent1: meanFill(faces, (f) => f.accent, 1),
    body1: meanFill(faces, (f) => !f.accent && !f.emissive, 1) };
}
const raw = fs.readFileSync("web/hull-meshes.js");
const others = {};
for (const hull of __HULLS__) {
  const faces = api.buildHullFaces({ class: hull, transwarp: {} }, { accent: "#7aa2ff", detail: "bridge", engines: 2, name: hull });
  others[hull] = { faces: faces.length, hash: hashPts(faces) };
}
const report = {
  gzip: zlib.gzipSync(raw, { level: 9 }).length,
  version: api.version,
  look: api.look,
  merchant: clearance("merchant_cruiser", "#7aa2ff", 2, "pods bridge", 25, 1.12),
  imperial25: clearance("imperial_starship", "#ffe9a0", 4, "bridge nacelles", 25, 0.84),
  imperial500: clearance("imperial_starship", "#ffe9a0", 4, "bridge nacelles", 500, 0.76),
  imperial1000: clearance("imperial_starship", "#ffe9a0", 4, "bridge nacelles", 1000, 0.72),
  none: clearance("merchant_cruiser", "#7aa2ff", 2, "pods bridge", 0, 1.12),
  one: clearance("scout_marauder", "#5dffc8", 2, "bridge", 1, 1.12),
  others,
};
console.log(JSON.stringify(report));
""".replace("__HULLS__", json.dumps(list(FLEET_GLASS)))
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return json.loads(proc.stdout)


def test_mesh_stays_under_the_gzip_budget() -> None:
    report = _report()
    assert report["gzip"] < 40 * 1024
    assert report["version"] == "ship-view-full-v1"
    assert report["look"] == "fleet-glass-v1"


def test_spike_hulls_keep_class_accent_when_shields_are_empty() -> None:
    report = _report()
    mer = report["merchant"]
    imp = report["imperial25"]
    assert mer["faces"] == 217 and mer["accent"] > 8
    assert imp["faces"] == 311 and imp["accent"] > 8
    assert imp["len"] > mer["len"]
    mr, mg, mb = mer["accent1"]
    assert mb > mr and mb > mg
    ir, ig, ib = imp["accent1"]
    assert ir > ig > ib and ir > 160
    for row in (mer, imp):
        br, bg, bb = row["body1"]
        assert br < 90 and br < bb + 20 and br <= bg + 15


def test_fleet_glass_hulls_keep_their_points() -> None:
    report = _report()
    for hull, (faces, digest) in FLEET_GLASS.items():
        got = report["others"][hull]
        assert got["faces"] == int(faces), hull
        assert got["hash"] == digest, hull


def test_markers_orbit_outside_the_hull() -> None:
    report = _report()
    assert report["none"]["got"] == 0
    assert report["one"]["got"] == 1
    assert report["merchant"]["got"] == 25
    assert report["imperial25"]["got"] == 25
    assert report["imperial500"]["got"] == 500
    assert report["imperial1000"]["got"] == 1000
    for key in ("merchant", "imperial25", "imperial500", "imperial1000", "one"):
        row = report[key]
        assert row["under"] == 0 and row["overlap"] == 0 and row["clipped"] == 0, (key, row)


def test_outline_is_not_tied_to_a_webgl_probe() -> None:
    js = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    assert "FIGHTER_EXACT_CAP" not in js
    assert "fighterClusters" not in js
    assert 'getContext("webgl"' not in js
    assert "each marker = 100 fighters" in js
    assert "Math.ceil(count / 100)" in js
    assert "missing mesh module" in js
    assert "body.cu-seat #shipSvg .hull-float{animation:none}" in css
    assert "var LOFT = " in MESHES.read_text(encoding="utf-8")
