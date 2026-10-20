/* cockpit-warp-clips-per-hull-v1. Shared hull mesh for the ship panel and the warp clips.

   This file is the NOTE 118 mesh (source "note118"). Track G NOTE 126
   (track-g-note126) replaces this file, or assigns window.TW2KHullMesh
   again before the cockpit script runs, when that module is on the branch.
   Either way the object has this shape:

     source: string                         "note118" today, "note126" later
     lofts:  { [shipClass]: number[][] }    section rings [x, sy, sz]
     buildFaces(ship, def) -> Face[]        ship.class, shields, transwarp; def.accent, detail, engines
     project(face, yaw, pitch, fit, ox, oy) -> {points, fill, opacity, depth} | null

   Callers use only this object. They do not read the loft tables themselves
   except through lofts, which the ship panel uses to know a hull has a mesh.
*/
(function () {
  const LOFT = {
    escape_pod: [[30, 12, 14], [8, 16, 18], [-8, 14, 16], [-28, 9, 11]],
    merchant_cruiser: [[72, 8, 11], [24, 12, 16], [-16, 11, 15], [-58, 7, 10]],
    scout_marauder: [[86, 4.2, 5], [36, 5.4, 6.2], [-8, 5.6, 6.6], [-62, 3.6, 4.4]],
    missile_frigate: [[76, 6, 9], [24, 10, 13], [-20, 9, 12], [-64, 6, 8]],
    battleship: [[64, 9, 26], [10, 13, 34], [-28, 11, 22], [-60, 8, 14]],
    corporate_flagship: [[72, 11, 16], [18, 16, 24], [-22, 15, 22], [-66, 10, 15]],
    colonial_transport: [[38, 18, 26], [4, 22, 32], [-30, 20, 30], [-60, 14, 22]],
    cargotran: [[46, 15, 22], [2, 18, 26], [-36, 17, 25], [-74, 12, 18]],
    merchant_freighter: [[34, 22, 34], [4, 28, 42], [-22, 26, 40], [-46, 18, 30]],
    imperial_starship: [[90, 14, 20], [28, 20, 28], [-16, 18, 26], [-80, 12, 18]],
    havoc_gunstar: [[62, 9, 16], [14, 13, 22], [-22, 12, 18], [-54, 9, 13]],
    star_master: [[62, 7, 10], [16, 11, 15], [-18, 10, 14], [-52, 7, 10]],
    constellation: [[66, 8, 16], [14, 12, 22], [-26, 11, 18], [-62, 8, 12]],
    tkhasi_orion: [[78, 4, 6], [22, 7, 10], [-14, 8, 11], [-56, 5, 7]],
    tholian_sentinel: [[30, 16, 32], [0, 20, 40], [-24, 16, 30], [-46, 11, 18]],
    taurean_mule: [[34, 18, 24], [-2, 22, 30], [-30, 20, 28], [-62, 15, 22]],
    interdictor_cruiser: [[48, 16, 24], [8, 20, 30], [-26, 19, 28], [-66, 14, 20]],
  };

  function mixRgb(a, b, t) {
    return a.map((v, i) => Math.round(v + (b[i] - v) * t));
  }
  function parseHex(hex) {
    const raw = String(hex || "#7aa2ff").replace("#", "");
    const full = raw.length === 3 ? raw.replace(/./g, (ch) => ch + ch) : raw;
    const n = parseInt(full, 16);
    const rgb = Number.isFinite(n) ? n : 0x7aa2ff;
    return [(rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255];
  }
  function vsub(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
  function vdot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
  function vcross(a, b) {
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  }
  function vlen(a) { return Math.hypot(a[0], a[1], a[2]); }
  function vnorm(a) {
    const len = vlen(a) || 1;
    return [a[0] / len, a[1] / len, a[2] / len];
  }
  function rotPoint(p, yaw, pitch) {
    const cy = Math.cos(yaw);
    const sy = Math.sin(yaw);
    const x1 = p[0] * cy + p[2] * sy;
    const z1 = -p[0] * sy + p[2] * cy;
    const cp = Math.cos(pitch);
    const sp = Math.sin(pitch);
    return [x1, p[1] * cp - z1 * sp, p[1] * sp + z1 * cp];
  }
  function pushFace(faces, pts, rgb, opacity, emissive, ref) {
    const e1 = vsub(pts[1], pts[0]);
    const e2 = vsub(pts[2], pts[0]);
    const raw = vcross(e1, e2);
    if (vlen(raw) < 0.08) return;
    const mid = [0, 0, 0];
    pts.forEach((p) => { mid[0] += p[0]; mid[1] += p[1]; mid[2] += p[2]; });
    mid[0] /= pts.length;
    mid[1] /= pts.length;
    mid[2] /= pts.length;
    const origin = ref || [0, mid[1], mid[2]];
    const ordered = vdot(raw, vsub(mid, origin)) < 0 ? pts.slice().reverse() : pts.slice();
    faces.push({ pts: ordered, rgb: rgb, opacity: opacity == null ? 1 : opacity, emissive: !!emissive });
  }
  function octagon(x, sy, sz, dy, dz) {
    const pts = [];
    for (let i = 0; i < 8; i++) {
      const t = (i + 0.5) * Math.PI / 4;
      pts.push([x, dy + Math.cos(t) * sy, dz + Math.sin(t) * sz]);
    }
    return pts;
  }
  function loftAt(faces, sections, dy, dz, rgb, opacity, emissive) {
    const rings = sections.map((s) => octagon(s[0], s[1], s[2], dy, dz));
    for (let i = 0; i < rings.length - 1; i++) {
      const a = rings[i];
      const b = rings[i + 1];
      const cx = (sections[i][0] + sections[i + 1][0]) / 2;
      for (let k = 0; k < 8; k++) {
        const k2 = (k + 1) % 8;
        pushFace(faces, [a[k], a[k2], b[k2], b[k]], rgb, opacity, emissive, [cx, dy, dz]);
      }
    }
    pushFace(faces, rings[0], rgb, opacity, emissive, [sections[0][0] - 4, dy, dz]);
    const last = sections.length - 1;
    pushFace(faces, rings[last], rgb, opacity, emissive, [sections[last][0] + 4, dy, dz]);
  }
  function boxAt(faces, x, y, z, sx, sy, sz, rgb, opacity, emissive) {
    const hx = sx / 2;
    const hy = sy / 2;
    const hz = sz / 2;
    const p = [
      [x - hx, y - hy, z - hz], [x + hx, y - hy, z - hz], [x + hx, y + hy, z - hz], [x - hx, y + hy, z - hz],
      [x - hx, y - hy, z + hz], [x + hx, y - hy, z + hz], [x + hx, y + hy, z + hz], [x - hx, y + hy, z + hz],
    ];
    [[0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [2, 6, 7, 3], [0, 3, 7, 4], [1, 5, 6, 2]].forEach((quad) => {
      pushFace(faces, quad.map((i) => p[i]), rgb, opacity, emissive, [x, y, z]);
    });
  }
  function buildHullFaces(sh, def) {
    const sections = LOFT[sh.class] || LOFT.merchant_cruiser;
    const accent = parseHex(def.accent || "#7aa2ff");
    const hull = mixRgb([18, 28, 52], accent, 0.62);
    const metal = mixRgb([32, 42, 64], accent, 0.4);
    const glass = mixRgb([220, 248, 255], accent, 0.22);
    const tw = !!(sh.transwarp && sh.transwarp.fitted);
    const glow = tw ? [255, 110, 255] : [190, 255, 255];
    const faces = [];
    loftAt(faces, sections, 0, 0, hull, 1, false);
    const nose = sections[0];
    const mid = sections[1];
    const tail = sections[sections.length - 1];
    const detail = new Set(String(def.detail || "").split(" ").filter(Boolean));
    if (detail.has("bridge")) {
      loftAt(faces, [
        [mid[0] + 12, 2.6, 3.4],
        [mid[0], 3.8, 4.6],
        [mid[0] - 14, 2.2, 2.8],
      ], mid[1] + 1.2, 0, glass, 1, false);
    }
    if (detail.has("pods")) {
      const z = mid[2] + 8;
      [-1, 1].forEach((sign) => {
        loftAt(faces, [
          [mid[0] + 16, 7, 7],
          [mid[0] - 12, 8.5, 8.5],
          [tail[0] + 8, 5.5, 5.5],
        ], -6, sign * z, metal, 1, false);
      });
    }
    if (detail.has("wings")) {
      [-1, 1].forEach((sign) => {
        loftAt(faces, [
          [mid[0] + 8, 1.1, 16],
          [tail[0] + 16, 0.7, 4],
        ], 0, sign * (mid[2] + 1), metal, 1, false);
      });
    }
    if (detail.has("nacelles")) {
      [-1, 1].forEach((sign) => {
        loftAt(faces, [
          [mid[0] - 4, 2.5, 2.5],
          [tail[0] - 2, 3.2, 3.2],
          [tail[0] - 24, 2, 2],
        ], -mid[1] * 0.4, sign * (mid[2] + 6), accent, 1, false);
      });
      if ((def.engines || 1) >= 4) {
        [-1, 1].forEach((sign) => {
          loftAt(faces, [
            [mid[0] - 2, 2.1, 2.1],
            [tail[0], 2.8, 2.8],
            [tail[0] - 22, 1.7, 1.7],
          ], mid[1] * 0.55, sign * (mid[2] + 4), accent, 1, false);
        });
      }
    }
    if (detail.has("guns") || sh.class === "imperial_starship") {
      [-1, 1].forEach((sign) => {
        boxAt(faces, nose[0] + 6, nose[1] * 0.2, sign * (nose[2] * 0.35 + 5), 22, 1.6, 1.6, accent, 1, false);
      });
    }
    if (detail.has("rails")) {
      boxAt(faces, (nose[0] + mid[0]) / 2, mid[1] + 1.2, 0, Math.abs(nose[0] - mid[0]), 1.8, 3.2, accent, 1, false);
    }
    if (detail.has("dish")) {
      loftAt(faces, [[mid[0] + 1, 1.2, 8], [mid[0] - 2, 0.7, 6.5]], mid[1] + 9, 0, accent, 1, false);
      boxAt(faces, mid[0], mid[1] + 5, 0, 1.4, 8, 1.4, metal, 1, false);
    }
    if (detail.has("ring")) {
      const radY = nose[1] + 11;
      const radZ = nose[2] + 8;
      for (let i = 0; i < 8; i++) {
        const a = (i / 8) * Math.PI * 2;
        boxAt(faces, nose[0] - 4, Math.cos(a) * radY, Math.sin(a) * radZ, 6, 3.2, 3.2, accent, 1, false);
      }
    }
    const engines = Math.max(1, def.engines || 1);
    for (let i = 0; i < engines; i++) {
      const z = (i - (engines - 1) / 2) * (engines > 3 ? 8 : 12);
      boxAt(faces, tail[0] - 4, -2, z, 8, 4.6, 4.6, metal, 1, false);
      boxAt(faces, tail[0] - 12, -2, z, 8, 2.2, 2.2, glow, 0.95, true);
    }
    return faces;
  }
  function cameraFace(face, yaw, pitch, fit, ox, oy) {
    const world = face.pts.map((p) => rotPoint([p[0] * fit, p[1] * fit, p[2] * fit], yaw, pitch));
    const raw = vcross(vsub(world[1], world[0]), vsub(world[2], world[0]));
    const n = vnorm(raw);
    if (n[2] <= 0.04) return null;
    const light = vnorm([-0.28, 0.84, 0.46]);
    const nd = Math.max(0, vdot(n, light));
    const spec = face.emissive ? 0.15 : Math.pow(nd, 10) * 0.45;
    const amount = face.emissive ? 0.78 + 0.22 * nd : 0.22 + 0.8 * nd;
    const fill = "rgb(" + face.rgb.map((c) => Math.max(0, Math.min(255, Math.round(c * amount + 255 * spec)))).join(",") + ")";
    const depth = world.reduce((sum, p) => sum + p[2], 0) / world.length;
    const pts = world.map((p) => {
      const s = 900 / (430 - p[2]);
      return [ox + p[0] * s, oy - p[1] * s];
    });
    return {
      points: pts.map((p) => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" "),
      fill: fill,
      opacity: face.opacity.toFixed(2),
      depth: depth,
    };
  }
  window.TW2KHullMesh = {
    source: "note118",
    lofts: LOFT,
    buildFaces: buildHullFaces,
    project: cameraFace,
  };
})();
