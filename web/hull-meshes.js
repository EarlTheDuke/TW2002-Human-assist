/* ship-view-full-v1. Shared hull meshes for the redesign ship panel and the warp clips.
   Fleet-glass pass: our own lofts and plates. No copied ANSI, no traced cinema.
   P1 spike: merchant_cruiser and imperial_starship use richer stations and kit
   on this same face list.    P1b adds scout_marauder, merchant_freighter,
   battleship, corporate_flagship, escape_pod, and tkhasi_orion on that
   same path. The other hulls stay fleet-glass-v1.
   Classic page: window.TW2KHullMeshes
   Module: import { buildHullFaces } from "/static/hull-meshes.mjs"
*/
(function (root) {
  "use strict";
  var LOFT = {
    escape_pod: [[34, 13, 15], [6, 18, 20], [-14, 16, 18], [-40, 11, 13]],
    merchant_cruiser: [[76, 7, 11], [18, 12, 17], [-22, 11, 15], [-64, 6, 9]],
    scout_marauder: [[98, 3.4, 4.2], [36, 4.6, 5.4], [-18, 4.2, 5], [-82, 2.6, 3.2]],
    missile_frigate: [[86, 5.5, 8], [20, 9, 12], [-26, 8, 11], [-72, 5, 7]],
    battleship: [[62, 8, 20], [6, 13, 30], [-26, 12, 24], [-58, 7, 14]],
    corporate_flagship: [[74, 10, 15], [14, 16, 22], [-24, 15, 20], [-68, 9, 13]],
    colonial_transport: [[32, 16, 26], [2, 22, 34], [-22, 22, 34], [-54, 15, 24]],
    cargotran: [[44, 13, 20], [4, 17, 28], [-30, 17, 28], [-80, 11, 18]],
    merchant_freighter: [[30, 20, 32], [2, 26, 40], [-18, 25, 38], [-44, 17, 28]],
    imperial_starship: [[96, 11, 16], [26, 17, 24], [-22, 15, 21], [-90, 9, 13]],
    havoc_gunstar: [[52, 7, 12], [8, 11, 18], [-20, 10, 15], [-52, 7, 11]],
    star_master: [[68, 6, 9], [14, 10, 14], [-20, 9, 13], [-56, 6, 9]],
    constellation: [[64, 7, 13], [10, 11, 17], [-24, 10, 15], [-60, 6, 10]],
    tkhasi_orion: [[90, 3.6, 4.6], [16, 5.2, 6.4], [-22, 4.8, 6], [-70, 3, 3.8]],
    tholian_sentinel: [[22, 16, 28], [-2, 22, 36], [-22, 20, 32], [-44, 13, 20]],
    taurean_mule: [[36, 15, 22], [-2, 21, 30], [-28, 19, 28], [-62, 13, 20]],
    interdictor_cruiser: [[42, 13, 20], [6, 18, 28], [-28, 18, 28], [-72, 12, 18]]
  };
  var SHAPE = {
    escape_pod: "round",
    merchant_cruiser: "round",
    scout_marauder: "round",
    missile_frigate: "round",
    battleship: "hex",
    corporate_flagship: "round",
    colonial_transport: "box",
    cargotran: "box",
    merchant_freighter: "box",
    imperial_starship: "round",
    havoc_gunstar: "hex",
    star_master: "round",
    constellation: "round",
    tkhasi_orion: "round",
    tholian_sentinel: "box",
    taurean_mule: "box",
    interdictor_cruiser: "box"
  };
  var PARTS = {
    escape_pod: "fins",
    merchant_cruiser: "keel",
    scout_marauder: "canards",
    missile_frigate: "missiles",
    battleship: "turrets",
    corporate_flagship: "tower",
    colonial_transport: "cargo",
    cargotran: "spine",
    merchant_freighter: "cheeks",
    imperial_starship: "castle",
    havoc_gunstar: "prongs",
    star_master: "mast",
    constellation: "quad",
    tkhasi_orion: "swept",
    tholian_sentinel: "armor",
    taurean_mule: "saddle",
    interdictor_cruiser: "hoop"
  };

  function mixRgb(a, b, t) {
    return a.map(function (v, i) { return Math.round(v + (b[i] - v) * t); });
  }
  function parseHex(hex) {
    var raw = String(hex || "#7aa2ff").replace("#", "");
    var full = raw.length === 3 ? raw.replace(/./g, function (ch) { return ch + ch; }) : raw;
    var n = parseInt(full, 16);
    var rgb = Number.isFinite(n) ? n : 0x7aa2ff;
    return [(rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255];
  }
  function vsub(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
  function vdot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
  function vcross(a, b) {
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  }
  function vlen(a) { return Math.hypot(a[0], a[1], a[2]); }
  function vnorm(a) {
    var len = vlen(a) || 1;
    return [a[0] / len, a[1] / len, a[2] / len];
  }
  function rotPoint(p, yaw, pitch) {
    var cy = Math.cos(yaw);
    var sy = Math.sin(yaw);
    var x1 = p[0] * cy + p[2] * sy;
    var z1 = -p[0] * sy + p[2] * cy;
    var cp = Math.cos(pitch);
    var sp = Math.sin(pitch);
    return [x1, p[1] * cp - z1 * sp, p[1] * sp + z1 * cp];
  }
  function pushFace(faces, pts, rgb, opacity, emissive, ref, accent) {
    var e1 = vsub(pts[1], pts[0]);
    var e2 = vsub(pts[2], pts[0]);
    var raw = vcross(e1, e2);
    if (vlen(raw) < 0.08) return;
    var mid = [0, 0, 0];
    pts.forEach(function (p) { mid[0] += p[0]; mid[1] += p[1]; mid[2] += p[2]; });
    mid[0] /= pts.length;
    mid[1] /= pts.length;
    mid[2] /= pts.length;
    var origin = ref || [0, mid[1], mid[2]];
    var ordered = vdot(raw, vsub(mid, origin)) < 0 ? pts.slice().reverse() : pts.slice();
    faces.push({ pts: ordered, rgb: rgb, opacity: opacity == null ? 1 : opacity, emissive: !!emissive, accent: !!accent });
  }
  function octagon(x, sy, sz, dy, dz, shape) {
    var pts = [];
    var i;
    for (i = 0; i < 8; i++) {
      var t = (i + 0.5) * Math.PI / 4;
      var cy = Math.cos(t);
      var cz = Math.sin(t);
      if (shape === "box") {
        var m = Math.max(Math.abs(cy), Math.abs(cz)) || 1;
        cy = cy / m * 0.78 + Math.cos(t) * 0.22;
        cz = cz / m * 0.78 + Math.sin(t) * 0.22;
      } else if (shape === "hex") {
        cy *= 0.58 + 0.42 * Math.abs(Math.sin(t));
      } else if (shape === "wedge") {
        if (cy < 0) cy *= 0.52;
        cy *= 0.84;
        cz *= 0.94;
      }
      pts.push([x, dy + cy * sy, dz + cz * sz]);
    }
    return pts;
  }
  function loftAt(faces, sections, dy, dz, rgb, opacity, emissive, shape, accent) {
    var rings = sections.map(function (s) { return octagon(s[0], s[1], s[2], dy, dz, shape || "round"); });
    var i;
    for (i = 0; i < rings.length - 1; i++) {
      var a = rings[i];
      var b = rings[i + 1];
      var cx = (sections[i][0] + sections[i + 1][0]) / 2;
      var k;
      for (k = 0; k < 8; k++) {
        var k2 = (k + 1) % 8;
        pushFace(faces, [a[k], a[k2], b[k2], b[k]], rgb, opacity, emissive, [cx, dy, dz], accent);
      }
    }
    pushFace(faces, rings[0], rgb, opacity, emissive, [sections[0][0] - 4, dy, dz], accent);
    var last = sections.length - 1;
    pushFace(faces, rings[last], rgb, opacity, emissive, [sections[last][0] + 4, dy, dz], accent);
  }
  function boxAt(faces, x, y, z, sx, sy, sz, rgb, opacity, emissive, accent) {
    var hx = sx / 2;
    var hy = sy / 2;
    var hz = sz / 2;
    var p = [
      [x - hx, y - hy, z - hz], [x + hx, y - hy, z - hz], [x + hx, y + hy, z - hz], [x - hx, y + hy, z - hz],
      [x - hx, y - hy, z + hz], [x + hx, y - hy, z + hz], [x + hx, y + hy, z + hz], [x - hx, y + hy, z + hz]
    ];
    [[0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [2, 6, 7, 3], [0, 3, 7, 4], [1, 5, 6, 2]].forEach(function (quad) {
      pushFace(faces, quad.map(function (i) { return p[i]; }), rgb, opacity, emissive, [x, y, z], accent);
    });
  }
  function shade(rgb, t) {
    return rgb.map(function (c) { return Math.max(0, Math.min(255, Math.round(c * t))); });
  }
  function wing(faces, sign, xLead, xTrail, zIn, zOut, y, rgb) {
    var s = sign < 0 ? -1 : 1;
    var span = Math.abs(xLead - xTrail) || 1;
    var tipLead = xLead - span * 0.46;
    var tipTrail = xTrail + span * 0.06;
    var top = [
      [xLead, y + 0.85, s * zIn],
      [tipLead, y + 0.35, s * zOut],
      [tipTrail, y + 0.28, s * zOut],
      [xTrail, y + 0.7, s * zIn * 0.92]
    ];
    var bot = [
      [xLead, y - 0.85, s * zIn],
      [xTrail, y - 0.7, s * zIn * 0.92],
      [tipTrail, y - 0.28, s * zOut],
      [tipLead, y - 0.35, s * zOut]
    ];
    var cx = (xLead + xTrail) / 2;
    var cz = s * (zIn + zOut) / 2;
    pushFace(faces, top, rgb, 1, false, [cx, y, cz]);
    pushFace(faces, bot, shade(rgb, 0.62), 1, false, [cx, y, cz]);
    pushFace(faces, [top[0], top[1], bot[1], bot[0]], mixRgb(rgb, [255, 255, 255], 0.28), 1, false, [cx, y, cz]);
  }
  function fin(faces, xLead, xTrail, yBase, yTip, rgb) {
    var fore = [
      [xLead, yBase, 0.55],
      [xLead + (xTrail - xLead) * 0.28, yTip, 0.22],
      [xTrail, yBase + (yTip - yBase) * 0.22, 0.22],
      [xTrail, yBase, 0.48]
    ];
    var cx = (xLead + xTrail) / 2;
    var cy = (yBase + yTip) / 2;
    pushFace(faces, fore, rgb, 1, false, [cx, cy, 0]);
    var aft = fore.map(function (p) { return [p[0], p[1], -p[2]]; }).reverse();
    pushFace(faces, aft, shade(rgb, 0.7), 1, false, [cx, cy, 0]);
  }
  function stripe(faces, x0, x1, y, halfZ, rgb) {
    pushFace(faces, [
      [x0, y, -halfZ],
      [x1, y, -halfZ],
      [x1, y, halfZ],
      [x0, y, halfZ]
    ], rgb, 1, false, [(x0 + x1) / 2, y - 4, 0], true);
  }
  function lamp(faces, x, y, z, sx, sy, rgb, outward) {
    var o = outward < 0 ? -1 : 1;
    pushFace(faces, [
      [x - sx, y - sy, z],
      [x + sx, y - sy, z],
      [x + sx, y + sy, z],
      [x - sx, y + sy, z]
    ], rgb, 1, true, [x, y, z - o * 3]);
  }
  function washer(faces, x, radIn, radOut, segs, rgb, thick) {
    var i;
    var dark = shade(rgb, 0.7);
    for (i = 0; i < segs; i++) {
      var a0 = (i / segs) * Math.PI * 2;
      var a1 = ((i + 1) / segs) * Math.PI * 2;
      var p = function (a, r, t) { return [x + t, Math.cos(a) * r, Math.sin(a) * r]; };
      var ref = [x, 0, 0];
      pushFace(faces, [p(a0, radIn, thick), p(a0, radOut, thick), p(a1, radOut, thick), p(a1, radIn, thick)], rgb, 1, false, ref);
      pushFace(faces, [p(a0, radIn, -thick), p(a1, radIn, -thick), p(a1, radOut, -thick), p(a0, radOut, -thick)], dark, 1, false, ref);
      pushFace(faces, [p(a0, radOut, thick), p(a0, radOut, -thick), p(a1, radOut, -thick), p(a1, radOut, thick)], mixRgb(rgb, [255, 255, 255], 0.18), 1, false, ref);
    }
  }
  function classParts(faces, cls, nose, mid, tail, accent, metal) {
    var part = PARTS[cls] || "";
    if (part === "fins") {
      [-1, 1].forEach(function (sign) {
        wing(faces, sign, mid[0] + 2, tail[0] + 2, 3, 16, -1, metal);
      });
      fin(faces, mid[0], tail[0] + 4, mid[1] * 0.2, mid[1] + 10, accent);
    } else if (part === "canards") {
      [-1, 1].forEach(function (sign) {
        wing(faces, sign, nose[0] - 6, nose[0] - 34, 1.4, 18, 0.6, accent);
        wing(faces, sign, mid[0] - 8, tail[0] + 8, 1.6, 12, -0.8, metal);
      });
      fin(faces, mid[0] + 4, tail[0] + 10, 1, 9, accent);
    } else if (part === "missiles") {
      [-1, 1].forEach(function (sign) {
        boxAt(faces, mid[0] + 2, mid[1] + 5.5, sign * (mid[2] * 0.45 + 3), 36, 2.4, 2.4, accent, 1, false);
        boxAt(faces, mid[0] + 16, mid[1] + 5.5, sign * (mid[2] * 0.45 + 3), 5, 2.8, 2.8, [255, 210, 140], 1, false);
      });
    } else if (part === "turrets") {
      [-1, 1].forEach(function (sign) {
        boxAt(faces, mid[0] + sign * 8, mid[1] + 3, sign * 6, 12, 7, 10, metal, 1, false);
        boxAt(faces, nose[0] - 4, mid[1] + 6, sign * 6, 22, 1.8, 1.8, accent, 1, false);
      });
      [-1, 1].forEach(function (sign) {
        wing(faces, sign, nose[0] - 10, tail[0] + 8, mid[2] * 0.15, mid[2] + 8, -2, shade(metal, 0.9));
      });
    } else if (part === "tower") {
      boxAt(faces, mid[0] - 2, mid[1] + 8, 0, 14, 16, 10, metal, 1, false);
      boxAt(faces, mid[0] + 2, mid[1] + 18, 0, 8, 6, 6, accent, 1, false);
      fin(faces, mid[0] - 8, tail[0] + 6, mid[1] + 2, mid[1] + 16, accent);
    } else if (part === "cargo") {
      [-1, 1].forEach(function (sign) {
        loftAt(faces, [[mid[0] + 12, 11, 11], [mid[0] - 16, 13, 13], [tail[0] + 8, 8, 8]], -6, sign * (mid[2] * 0.72), metal, 1, false, "round");
      });
    } else if (part === "spine") {
      boxAt(faces, (nose[0] + tail[0]) / 2, mid[1] * 0.15, 0, Math.abs(nose[0] - tail[0]) * 0.78, 5, mid[2] * 1.15, metal, 1, false);
    } else if (part === "cheeks") {
      [-1, 1].forEach(function (sign) {
        loftAt(faces, [[mid[0] + 10, 14, 10], [mid[0] - 8, 16, 12], [tail[0] + 6, 10, 8]], -6, sign * (mid[2] * 0.62), metal, 1, false, "box");
      });
    } else if (part === "prongs") {
      [-1, 1].forEach(function (sign) {
        loftAt(faces, [[nose[0] + 26, 2.4, 2.4], [nose[0] + 4, 3.6, 3.6], [nose[0] - 22, 1.8, 1.8]], nose[1] * 0.2, sign * (nose[2] + 7), accent, 1, false, "round");
      });
    } else if (part === "mast") {
      boxAt(faces, mid[0] - 2, mid[1] + 10, 0, 1.6, 16, 1.6, metal, 1, false);
      loftAt(faces, [[mid[0], 0.9, 11], [mid[0] - 3, 0.45, 8]], mid[1] + 18, 0, accent, 1, false, "round");
    } else if (part === "quad") {
      [[1, 1], [1, -1], [-1, 1], [-1, -1]].forEach(function (s) {
        loftAt(faces, [[mid[0] - 4, 2.6, 2.6], [tail[0] - 2, 3.1, 3.1], [tail[0] - 16, 1.8, 1.8]], s[0] * (mid[1] + 8), s[1] * (mid[2] + 8), accent, 1, false, "round");
      });
    } else if (part === "swept") {
      [-1, 1].forEach(function (sign) {
        wing(faces, sign, nose[0] - 8, tail[0] + 4, 2, 32, 0, metal);
        wing(faces, sign, nose[0] - 18, mid[0], 1, 14, 2.2, accent);
      });
    } else if (part === "armor") {
      [-1, 1].forEach(function (sign) {
        boxAt(faces, mid[0], 1, sign * (mid[2] + 3), 28, mid[1] * 1.35, 8, metal, 1, false);
      });
      boxAt(faces, nose[0] - 6, mid[1] * 0.2, 0, 10, mid[1] * 1.1, mid[2] * 0.8, shade(metal, 0.85), 1, false);
    } else if (part === "saddle") {
      boxAt(faces, mid[0], mid[1] + 5, 0, 30, 8, mid[2] * 0.9, metal, 1, false);
      [-1, 1].forEach(function (sign) {
        boxAt(faces, tail[0] + 10, -1, sign * (mid[2] * 0.45), 18, 6, 8, accent, 1, false);
      });
    } else if (part === "hoop") {
      var inner = Math.max(mid[1], mid[2]) + 3;
      var outer = inner + 6.5;
      washer(faces, mid[0] + 10, inner, outer, 12, accent, 1.35);
      washer(faces, mid[0] - 16, inner * 0.92, outer * 0.92, 12, metal, 1.15);
    } else if (part === "castle") {
      boxAt(faces, mid[0] + 6, mid[1] + 5, 0, 34, 8, 9, metal, 1, false);
      boxAt(faces, mid[0] + 14, mid[1] + 11, 0, 14, 6, 6, accent, 1, false);
      fin(faces, mid[0] - 4, tail[0] + 8, mid[1], mid[1] + 14, accent);
      boxAt(faces, mid[0], -mid[1] - 1.5, 0, Math.abs(nose[0] - tail[0]) * 0.42, 3.2, 4.5, metal, 1, false);
    } else if (part === "keel") {
      boxAt(faces, mid[0], -mid[1] - 2.2, 0, Math.abs(nose[0] - tail[0]) * 0.5, 3.4, 4.2, metal, 1, false);
    }
  }
  function engineAt(faces, x, y, z, metal, glow, hot, glen, gthick, sheath) {
    boxAt(faces, x, y, z, 8, 4.8, 4.8, metal, 1, false);
    var mouth = x - 3.6;
    loftAt(faces, [
      [mouth, 0.55, 0.55],
      [mouth - glen * 0.5, gthick * 0.95, 1.45],
      [mouth - glen, 0.28, 0.32]
    ], y, z, hot, 0.98, true, "round");
    if (sheath) {
      loftAt(faces, [
        [mouth + 0.4, 0.95, 1.15],
        [mouth - glen * 0.72, gthick * 1.35, 2.5]
      ], y, z, glow, 0.4, true, "round");
    }
  }
  function plumeOf(spec, tw) {
    var glow = spec.glow ? parseHex(spec.glow) : (tw ? [255, 110, 255] : [190, 255, 255]);
    var hot = mixRgb(glow, [255, 255, 255], 0.62);
    var glen = 16;
    var gthick = 2.8;
    var asked = Number(spec.plume);
    if (asked > 0) {
      glen = asked;
      gthick = Math.max(1.6, Math.min(4.2, 1.4 + asked * 0.05));
    }
    return { glow: glow, hot: hot, glen: glen, gthick: gthick };
  }
  // Flat blade. Body stays metal. Leading edge and tip are the accent, so a
  // shield wash cannot repaint the kit.
  function canard(faces, sign, xLead, xTrail, zIn, zOut, y, metal, accent, sweep) {
    var s = sign < 0 ? -1 : 1;
    var span = Math.abs(xLead - xTrail) || 1;
    var tipLead = xLead - span * (sweep == null ? 0.36 : sweep);
    var tipTrail = xTrail + span * 0.04;
    var thick = 1.7;
    var zTip = s * zOut;
    var zRoot = s * zIn;
    var top = [
      [xLead, y + thick, zRoot],
      [tipLead, y + thick * 0.7, zTip],
      [tipTrail, y + thick * 0.52, zTip * 0.94],
      [xTrail, y + thick * 0.8, s * Math.max(zIn * 0.8, 1.2)]
    ];
    var bot = [
      [xLead, y - thick * 0.85, zRoot],
      [xTrail, y - thick * 0.62, s * Math.max(zIn * 0.8, 1.2)],
      [tipTrail, y - thick * 0.4, zTip * 0.94],
      [tipLead, y - thick * 0.55, zTip]
    ];
    var ref = [(xLead + tipLead) / 2, y, s * (zIn + zOut) / 2];
    pushFace(faces, top, metal, 1, false, ref);
    pushFace(faces, bot, shade(metal, 0.56), 1, false, ref);
    pushFace(faces, [top[0], top[1], bot[3], bot[0]], accent, 1, false, ref, true);
    pushFace(faces, [top[1], top[2], bot[2], bot[3]], accent, 1, false, ref, true);
    pushFace(faces, [top[2], top[3], bot[1], bot[2]], shade(metal, 0.7), 1, false, ref);
    pushFace(faces, [top[3], top[0], bot[0], bot[1]], shade(metal, 0.78), 1, false, ref);
  }
  function knife(faces, xLead, xTrail, yBase, yTip, metal, accent) {
    var rise = yTip - yBase;
    var fore = [
      [xLead, yBase, 0.72],
      [xLead + (xTrail - xLead) * 0.22, yTip, 0.26],
      [xTrail, yBase + rise * 0.18, 0.26],
      [xTrail, yBase, 0.6]
    ];
    var ref = [(xLead + xTrail) / 2, (yBase + yTip) / 2, 0];
    var aft = fore.map(function (p) { return [p[0], p[1], -p[2]]; });
    pushFace(faces, fore, metal, 1, false, ref);
    pushFace(faces, [aft[0], aft[3], aft[2], aft[1]], shade(metal, 0.64), 1, false, ref);
    pushFace(faces, [fore[0], fore[1], [fore[1][0], fore[1][1], -fore[1][2]], [fore[0][0], fore[0][1], -fore[0][2]]], accent, 1, false, ref, true);
    pushFace(faces, [fore[1], fore[2], [fore[2][0], fore[2][1], -fore[2][2]], [fore[1][0], fore[1][1], -fore[1][2]]], accent, 1, false, ref, true);
  }
  function bell(faces, x, y, z, metal, plume, scale) {
    var sc = scale || 1;
    var glen = plume.glen * (sc < 1 ? sc : 1);
    var gt = plume.gthick * sc;
    var mouth = x - 1.15 * sc;
    boxAt(faces, x + 2.4 * sc, y, z, 6.4 * sc, 3.5 * sc, 3.5 * sc, metal, 1, false);
    loftAt(faces, [
      [x + 5.5 * sc, 0.85 * sc, 0.85 * sc],
      [x + 4.7 * sc, 1.45 * sc, 1.45 * sc]
    ], y, z, [8, 12, 18], 1, false, "round");
    loftAt(faces, [
      [mouth, 0.5 * sc, 0.5 * sc],
      [mouth - glen * 0.4, gt * 0.7, gt * 0.92],
      [mouth - glen, 0.15 * sc, 0.17 * sc]
    ], y, z, plume.hot, 0.98, true, "round");
    loftAt(faces, [
      [mouth + 0.2 * sc, 0.95 * sc, 1.05 * sc],
      [mouth - glen * 0.48, gt * 1.02, gt * 1.28]
    ], y, z, plume.glow, 0.4, true, "round");
  }
  function merchantSpike(faces, hull, metal, accent, glass, plume) {
    var sections = [[64, 5.4, 10.2], [46, 8.4, 15.2], [24, 9.2, 16.4], [2, 8.4, 14.8], [-20, 7.2, 12.4], [-40, 5.6, 9.2], [-58, 4.0, 6.4]];
    loftAt(faces, sections, 0, 0, hull, 1, false, "wedge");
    var tail = sections[sections.length - 1];
    boxAt(faces, -6, -15.5, 0, 72, 18, 5.6, metal, 1, false);
    boxAt(faces, -8, -8.6, 0, 54, 2.4, 7.2, accent, 1, false, true);
    [-1, 1].forEach(function (sign) {
      loftAt(faces, [[22, 6.8, 6.8], [2, 8.4, 8.4], [-22, 5.6, 5.6]], 3.2, sign * 23, metal, 1, false, "round");
      boxAt(faces, 0, 3.2, sign * 23, 16, 2.4, 15.5, accent, 1, false, true);
      boxAt(faces, 6, 1.4, sign * 15.6, 46, 3.4, 1.5, accent, 1, false, true);
    });
    loftAt(faces, [[54, 2.6, 4.2], [44, 4.2, 6.0], [34, 2.4, 3.6]], 8.6, 0, glass, 1, false, "round");
    loftAt(faces, [[56, 1.3, 5.2], [40, 1.5, 6.6]], 7.4, 0, accent, 1, false, "round", true);
    stripe(faces, 36, -46, 9.6, 3.1, accent);
    [-1, 1].forEach(function (sign) {
      engineAt(faces, tail[0] - 1, -2.4, sign * 7.5, metal, plume.glow, plume.hot, plume.glen, plume.gthick, true);
    });
  }
  function imperialSpike(faces, hull, metal, accent, glass, plume) {
    var sections = [[100, 4.6, 7.6], [76, 7.6, 12.4], [48, 9.8, 15.4], [16, 10.8, 16.6], [-16, 9.8, 14.8], [-48, 8.2, 12.2], [-78, 6.4, 9.4], [-98, 4.6, 6.8]];
    loftAt(faces, sections, 0, 0, hull, 1, false, "round");
    boxAt(faces, -10, -12.4, 0, 84, 6.4, 4.6, metal, 1, false);
    boxAt(faces, 18, 17.2, 0, 74, 11, 12, metal, 1, false);
    boxAt(faces, 46, 28.2, 0, 40, 11, 8.4, accent, 1, false, true);
    stripe(faces, 68, -72, 11.6, 3.2, accent);
    [-1, 1].forEach(function (sign) {
      boxAt(faces, 92, 2.2, sign * 9, 20, 1.7, 1.7, metal, 1, false);
      boxAt(faces, 100, 2.2, sign * 9, 5, 2.2, 2.2, accent, 1, false, true);
      boxAt(faces, 20, 12.2, sign * 16.2, 58, 2.6, 1.4, accent, 1, false, true);
    });
    loftAt(faces, [[58, 2.2, 3.4], [46, 3.4, 4.8], [34, 2.0, 2.8]], 22, 0, glass, 1, false, "round");
    [[1, 1], [1, -1], [-1, 1], [-1, -1]].forEach(function (s) {
      var y = s[0] * 17;
      var z = s[1] * 19;
      loftAt(faces, [[-84, 4.4, 4.4], [-94, 6.6, 6.6], [-104, 3.4, 3.4]], y, z, metal, 1, false, "round");
      loftAt(faces, [[-98, 1.6, 1.6], [-108, 3.4, 3.4], [-114, 0.4, 0.4]], y, z, plume.hot, 0.96, true, "round");
      loftAt(faces, [[-102, 6.9, 6.9], [-106, 7.1, 7.1]], y, z, accent, 1, false, "round", true);
    });
  }
  function scoutSpike(faces, hull, metal, accent, glass, plume) {
    var sections = [
      [92, 1.05, 1.25],
      [70, 1.85, 2.15],
      [46, 2.25, 2.55],
      [18, 2.45, 2.75],
      [-8, 2.25, 2.55],
      [-32, 1.95, 2.25],
      [-54, 1.55, 1.8],
      [-74, 1.05, 1.25]
    ];
    loftAt(faces, sections, 0, 0, hull, 1, false, "round");
    [-1, 1].forEach(function (sign) {
      canard(faces, sign, 78, 40, 1.9, 32, 0.2, metal, accent, 0.16);
      canard(faces, sign, -36, -66, 1.3, 8.4, -0.35, metal, accent, 0.42);
    });
    knife(faces, -34, -68, 1.9, 13.6, metal, accent);
    knife(faces, -42, -64, -1.15, -6.4, metal, accent);
    loftAt(faces, [[62, 0.95, 1.25], [50, 1.5, 1.85], [40, 0.85, 1.1]], 2.35, 0, glass, 1, false, "round");
    loftAt(faces, [[64, 0.38, 1.05], [46, 0.46, 1.3]], 2.15, 0, accent, 1, false, "round", true);
    stripe(faces, 66, -60, 2.75, 0.42, accent);
    [-1, 1].forEach(function (sign) {
      bell(faces, -78, -1.55, sign * 3.6, metal, plume, 0.5);
    });
  }
  function freighterSpike(faces, hull, metal, accent, glass, plume) {
    var sections = [
      [42, 4.2, 8.6],
      [24, 5.4, 10.8],
      [6, 6.0, 12.2],
      [-12, 5.6, 11.4],
      [-28, 4.6, 9.2],
      [-42, 3.4, 6.8]
    ];
    loftAt(faces, sections, 0, 0, hull, 1, false, "box");
    [-1, 1].forEach(function (sign) {
      boxAt(faces, 2, 6.55, sign * 22, 50, 1.25, 26, metal, 1, false);
      loftAt(faces, [
        [16, 4.4, 6.6],
        [0, 5.8, 8.4],
        [-16, 5.4, 7.8],
        [-32, 3.8, 5.6]
      ], -1.5, sign * 39, metal, 1, false, "box");
      boxAt(faces, -8, -0.8, sign * 47.4, 40, 8.2, 1.5, accent, 1, false, true);
      boxAt(faces, -8, 4.7, sign * 42.6, 38, 1.1, 6.8, accent, 1, false, true);
    });
    loftAt(faces, [[22, 1.7, 2.6], [12, 2.7, 3.8], [2, 1.45, 2.1]], 6.35, 0, glass, 1, false, "round");
    loftAt(faces, [[24, 0.65, 2.2], [10, 0.8, 2.9]], 5.9, 0, accent, 1, false, "round", true);
    stripe(faces, 28, -30, 7.35, 1.45, accent);
    var win = [176, 154, 126];
    var i;
    for (i = 0; i < 3; i++) {
      lamp(faces, 6 - i * 11, 1.15, 48.9, 1.7, 1.15, win, 1);
      lamp(faces, 6 - i * 11, 1.15, -48.9, 1.7, 1.15, win, -1);
    }
    [-1, 1].forEach(function (sign) {
      bell(faces, -38, -2.3, sign * 23, metal, plume, 1.62);
    });
  }
  // Wide short hex wedge. Turret bodies are dark metal. Barrels and the
  // dorsal stripe carry the class accent. Three bells sit low in the tail.
  function battleshipSpike(faces, hull, metal, accent, glass, plume) {
    var sections = [
      [50, 4.4, 16],
      [32, 6.2, 30],
      [10, 7.4, 44],
      [-8, 7.0, 42],
      [-26, 5.8, 30],
      [-44, 4.6, 22]
    ];
    loftAt(faces, sections, 0, 0, hull, 1, false, "hex");
    [-1, 1].forEach(function (sign) {
      boxAt(faces, 4, 8.4, sign * 16, 16, 12.4, 12, metal, 1, false);
      boxAt(faces, 8, 16.0, sign * 16, 10, 4.8, 8.4, metal, 1, false);
      boxAt(faces, 18, 19.3, sign * 16, 24, 1.7, 1.7, accent, 1, false, true);
    });
    loftAt(faces, [[36, 1.5, 2.3], [26, 2.3, 3.2], [18, 1.35, 1.9]], 6.2, 0, glass, 1, false, "round");
    stripe(faces, 34, -30, 6.4, 3.2, accent);
    [-20, 0, 20].forEach(function (z) {
      bell(faces, -46, -8.2, z, metal, plume, 1.15);
    });
  }
  // Round liner. A stepped tower amidships, upper step in the class accent
  // as flat metal. Three bells in a low row, inside the beam.
  function flagshipSpike(faces, hull, metal, accent, glass, plume) {
    var sections = [
      [62, 5.2, 12],
      [40, 6.8, 18],
      [16, 7.6, 23],
      [-4, 7.8, 24],
      [-24, 7.2, 22],
      [-42, 6.2, 18],
      [-58, 4.8, 14]
    ];
    loftAt(faces, sections, 0, 0, hull, 1, false, "round");
    boxAt(faces, -2, 12.2, 0, 28, 16.2, 24, metal, 1, false);
    boxAt(faces, -2, 26.8, 0, 16, 13.6, 16, accent, 1, false, true);
    loftAt(faces, [[40, 1.7, 2.5], [30, 2.6, 3.6], [20, 1.5, 2.1]], 8.2, 0, glass, 1, false, "round");
    stripe(faces, 46, -40, 8.6, 2.6, accent);
    [-8, 0, 8].forEach(function (z) {
      bell(faces, -60, -7.8, z, metal, plume, 1.05);
    });
  }
  // Short side plate. The body stays dark metal, including the edges, so the
  // plate reads as shape and does not take the class accent.
  function stubFin(faces, sign, xLead, xTrail, zIn, zOut, y, metal) {
    var s = sign < 0 ? -1 : 1;
    var span = Math.abs(xLead - xTrail) || 1;
    var tipLead = xLead - span * 0.12;
    var tipTrail = xTrail + span * 0.02;
    var thick = 4.6;
    var zTip = s * zOut;
    var zRoot = s * zIn;
    var top = [
      [xLead, y + thick, zRoot],
      [tipLead, y + thick * 0.75, zTip],
      [tipTrail, y + thick * 0.58, zTip * 0.97],
      [xTrail, y + thick * 0.85, s * Math.max(zIn * 0.9, 1.2)]
    ];
    var bot = [
      [xLead, y - thick, zRoot],
      [xTrail, y - thick * 0.82, s * Math.max(zIn * 0.9, 1.2)],
      [tipTrail, y - thick * 0.48, zTip * 0.97],
      [tipLead, y - thick * 0.64, zTip]
    ];
    var ref = [(xLead + tipLead) / 2, y, s * (zIn + zOut) / 2];
    pushFace(faces, top, metal, 1, false, ref);
    pushFace(faces, bot, shade(metal, 0.55), 1, false, ref);
    pushFace(faces, [top[0], top[1], bot[3], bot[0]], shade(metal, 0.84), 1, false, ref);
    pushFace(faces, [top[1], top[2], bot[2], bot[3]], shade(metal, 0.7), 1, false, ref);
    pushFace(faces, [top[2], top[3], bot[1], bot[2]], shade(metal, 0.62), 1, false, ref);
    pushFace(faces, [top[3], top[0], bot[0], bot[1]], shade(metal, 0.76), 1, false, ref);
  }
  // One swept plate. The body stays metal. The leading edge and the tip
  // carry the accent. The tip sits aft of the trailing root, past the tail.
  function crescent(faces, sign, noseX, tailX, zIn, zOut, y, metal, accent) {
    var s = sign < 0 ? -1 : 1;
    var span = Math.abs(noseX - tailX) || 1;
    var tipLead = noseX - span * 0.56;
    var tipTrail = tailX - span * 0.2;
    var rootT = 2.3;
    var tipT = 3.6;
    var drop = 2.8;
    var zTip = s * zOut;
    var zRoot = s * zIn;
    var top = [
      [noseX, y + rootT, zRoot],
      [tipLead, y - drop * 0.35 + tipT, zTip],
      [tipTrail, y - drop + tipT * 0.4, zTip * 0.9],
      [tailX, y + rootT * 0.65, zRoot * 1.25]
    ];
    var bot = [
      [noseX, y - rootT * 0.75, zRoot],
      [tailX, y - rootT * 0.45, zRoot * 1.25],
      [tipTrail, y - drop - tipT * 0.45, zTip * 0.9],
      [tipLead, y - drop * 0.35 - tipT * 0.5, zTip]
    ];
    var ref = [(noseX + tipTrail) / 2, y - drop, s * (zIn + zOut) / 2];
    pushFace(faces, top, metal, 1, false, ref);
    pushFace(faces, bot, shade(metal, 0.54), 1, false, ref);
    pushFace(faces, [top[0], top[1], bot[3], bot[0]], accent, 1, false, ref, true);
    pushFace(faces, [top[1], top[2], bot[2], bot[3]], accent, 1, false, ref, true);
    pushFace(faces, [top[2], top[3], bot[1], bot[2]], shade(metal, 0.66), 1, false, ref);
    pushFace(faces, [top[3], top[0], bot[0], bot[1]], shade(metal, 0.76), 1, false, ref);
  }
  // Lifeboat. A short round capsule, almost as tall as it is long. Two stub
  // fins sit outside the beam. One round port on the nose carries the cyan.
  // One bell sits low on the centerline, inside the fin span.
  function podSpike(faces, hull, metal, accent, glass, plume) {
    var sections = [
      [26, 20, 20],
      [13, 32, 32],
      [0, 38, 38],
      [-13, 32, 32],
      [-26, 18, 18]
    ];
    loftAt(faces, sections, 0, 0, hull, 1, false, "round");
    [-1, 1].forEach(function (sign) {
      stubFin(faces, sign, 4, -12, 24, 64, -1.5, metal);
    });
    loftAt(faces, [
      [34.6, 14.8, 14.8],
      [24.2, 16.4, 16.4]
    ], 1.4, 0, accent, 1, false, "round", true);
    stripe(faces, 8, -14, 36.2, 2.1, accent);
    bell(faces, -28, -16, 0, metal, plume, 0.48);
  }
  // Alien fast hull. One pair of swept plates leaves the nose and runs past
  // the tail. Plate bodies stay metal; the edges carry the accent. The
  // `wings` token does not grow a second pair. The canopy stays inside the
  // crescent. Two bells sit low, inside the plate span.
  function orionSpike(faces, hull, metal, accent, glass, plume) {
    var sections = [
      [44, 2.2, 2.6],
      [24, 3.2, 3.6],
      [6, 3.6, 4.0],
      [-14, 3.2, 3.6],
      [-30, 2.4, 2.8],
      [-40, 1.6, 1.9]
    ];
    loftAt(faces, sections, 0, 0, hull, 1, false, "round");
    [-1, 1].forEach(function (sign) {
      crescent(faces, sign, 40, -54, 3.1, 36, 0.5, metal, accent);
    });
    loftAt(faces, [[20, 1.2, 1.55], [8, 1.8, 2.2], [-2, 1.05, 1.35]], 4.0, 0, glass, 1, false, "round");
    loftAt(faces, [[22, 0.45, 1.2], [6, 0.52, 1.45]], 3.7, 0, accent, 1, false, "round", true);
    stripe(faces, 28, -32, 4.15, 0.6, accent);
    [-1, 1].forEach(function (sign) {
      bell(faces, -44, -4.4, sign * 11, metal, plume, 0.7);
    });
  }
  function spikeAccent(ship, spec) {
    if (spec && spec.accent) return parseHex(spec.accent);
    if (ship.class === "imperial_starship") return parseHex("#ffe9a0");
    if (ship.class === "scout_marauder") return parseHex("#5dffc8");
    if (ship.class === "merchant_freighter") return parseHex("#7af0ff");
    if (ship.class === "battleship") return parseHex("#c5c8ff");
    if (ship.class === "corporate_flagship") return parseHex("#ff77ff");
    if (ship.class === "escape_pod") return parseHex("#55ffff");
    if (ship.class === "tkhasi_orion") return parseHex("#ff6d8a");
    return parseHex("#7aa2ff");
  }
  function buildSpikeFaces(ship, spec) {
    var accent = spikeAccent(ship, spec);
    var hull = [26, 33, 48];
    var metal = [38, 46, 62];
    var glass = mixRgb([236, 246, 255], accent, 0.18);
    var tw = !!(ship.transwarp && ship.transwarp.fitted);
    var plume = plumeOf(spec, tw);
    var faces = [];
    if (ship.class === "imperial_starship") imperialSpike(faces, hull, metal, accent, glass, plume);
    else if (ship.class === "scout_marauder") scoutSpike(faces, hull, metal, accent, glass, plume);
    else if (ship.class === "merchant_freighter") freighterSpike(faces, hull, metal, accent, glass, plume);
    else if (ship.class === "battleship") battleshipSpike(faces, hull, metal, accent, glass, plume);
    else if (ship.class === "corporate_flagship") flagshipSpike(faces, hull, metal, accent, glass, plume);
    else if (ship.class === "escape_pod") podSpike(faces, hull, metal, accent, glass, plume);
    else if (ship.class === "tkhasi_orion") orionSpike(faces, hull, metal, accent, glass, plume);
    else merchantSpike(faces, hull, metal, accent, glass, plume);
    return faces;
  }
  function buildHullFaces(sh, def) {
    var ship = sh || {};
    var spec = def || {};
    if (ship.class === "merchant_cruiser" || ship.class === "imperial_starship" || ship.class === "scout_marauder" || ship.class === "merchant_freighter" || ship.class === "battleship" || ship.class === "corporate_flagship" || ship.class === "escape_pod" || ship.class === "tkhasi_orion") return buildSpikeFaces(ship, spec);
    var sections = LOFT[ship.class] || LOFT.merchant_cruiser;
    var shape = SHAPE[ship.class] || "round";
    var accent = parseHex(spec.accent || "#7aa2ff");
    var hull = mixRgb([12, 18, 34], accent, 0.7);
    var metal = mixRgb([26, 34, 52], accent, 0.46);
    var glass = mixRgb([232, 248, 255], accent, 0.16);
    var tw = !!(ship.transwarp && ship.transwarp.fitted);
    var glow = spec.glow ? parseHex(spec.glow) : (tw ? [255, 110, 255] : [190, 255, 255]);
    var hot = mixRgb(glow, [255, 255, 255], 0.62);
    var glen = 16;
    var gthick = 2.8;
    var asked = Number(spec.plume);
    if (asked > 0) {
      glen = asked;
      gthick = Math.max(1.6, Math.min(4.2, 1.4 + asked * 0.05));
    }
    var faces = [];
    loftAt(faces, sections, 0, 0, hull, 1, false, shape);
    var nose = sections[0];
    var mid = sections[1];
    var tail = sections[sections.length - 1];
    var detail = {};
    String(spec.detail || "").split(" ").forEach(function (bit) { if (bit) detail[bit] = true; });
    stripe(faces, nose[0] - 8, tail[0] + 6, mid[1] + 0.9, 1.35, accent);
    if (detail.bridge) {
      loftAt(faces, [
        [mid[0] + 16, 2.4, 3.2],
        [mid[0] + 2, 3.8, 4.8],
        [mid[0] - 14, 2.1, 2.8]
      ], mid[1] + 0.6, 0, glass, 1, false, "round");
    } else if (ship.class !== "escape_pod") {
      loftAt(faces, [
        [mid[0] + 8, 2.2, 2.8],
        [mid[0] - 2, 3.2, 3.8],
        [mid[0] - 12, 1.8, 2.2]
      ], mid[1] + 0.4, 0, glass, 1, false, "round");
    } else {
      loftAt(faces, [[10, 4.2, 4.2], [16, 1.4, 1.4]], 3, 0, glass, 1, false, "round");
    }
    if (shape === "box") {
      var win = mixRgb(glass, [255, 244, 210], 0.45);
      var i;
      for (i = 0; i < 3; i++) {
        var wx = mid[0] + 8 - i * 12;
        lamp(faces, wx, mid[1] * 0.35, mid[2] + 1.4, 1.6, 1.1, win, 1);
        lamp(faces, wx, mid[1] * 0.35, -mid[2] - 1.4, 1.6, 1.1, win, -1);
      }
    }
    if (detail.pods) {
      var z = mid[2] + 7;
      [-1, 1].forEach(function (sign) {
        loftAt(faces, [
          [mid[0] + 14, 7, 7],
          [mid[0] - 10, 8.5, 8.5],
          [tail[0] + 6, 5.5, 5.5]
        ], -5, sign * z, metal, 1, false, "round");
      });
    }
    if (detail.wings) {
      [-1, 1].forEach(function (sign) {
        wing(faces, sign, mid[0] + 6, tail[0] + 12, mid[2] * 0.2, mid[2] + 14, 0, metal);
      });
    }
    if (detail.nacelles && PARTS[ship.class] !== "quad") {
      [-1, 1].forEach(function (sign) {
        loftAt(faces, [
          [mid[0] - 2, 2.8, 2.8],
          [tail[0] - 2, 3.4, 3.4],
          [tail[0] - 22, 2.1, 2.1]
        ], -mid[1] * 0.35, sign * (mid[2] + 6), accent, 1, false, "round");
      });
      if ((spec.engines || 1) >= 4) {
        [-1, 1].forEach(function (sign) {
          loftAt(faces, [
            [mid[0], 2.3, 2.3],
            [tail[0] + 2, 3, 3],
            [tail[0] - 20, 1.8, 1.8]
          ], mid[1] * 0.5, sign * (mid[2] + 5), accent, 1, false, "round");
        });
      }
    }
    if ((detail.guns || ship.class === "imperial_starship") && ship.class !== "battleship") {
      [-1, 1].forEach(function (sign) {
        boxAt(faces, nose[0] - 2, nose[1] * 0.15, sign * (nose[2] * 0.35 + 4), 26, 1.7, 1.7, accent, 1, false);
      });
    }
    if (detail.rails) {
      boxAt(faces, (nose[0] + mid[0]) / 2, mid[1] + 2.4, 0, Math.abs(nose[0] - mid[0]) * 0.7, 1.6, 3.4, accent, 1, false);
    }
    if (detail.dish) {
      loftAt(faces, [[mid[0] + 2, 1.1, 12], [mid[0] - 2, 0.55, 9]], mid[1] + 8, 0, accent, 1, false, "round");
      boxAt(faces, mid[0], mid[1] + 4, 0, 1.5, 8, 1.5, metal, 1, false);
    }
    if (detail.ring && PARTS[ship.class] !== "hoop") {
      var radY = nose[1] + 11;
      var radZ = nose[2] + 8;
      var r;
      for (r = 0; r < 8; r++) {
        var a = (r / 8) * Math.PI * 2;
        boxAt(faces, nose[0] - 4, Math.cos(a) * radY, Math.sin(a) * radZ, 6, 3.2, 3.2, accent, 1, false);
      }
    }
    if (Number(ship.photon_missiles) > 0 && !detail.rails) {
      [-1, 1].forEach(function (sign) {
        boxAt(faces, mid[0] + 6, mid[1] + 3.4, sign * 3.5, 18, 1.6, 1.6, [255, 196, 120], 1, false);
      });
    }
    if (ship.scanner && !detail.dish && ship.class !== "star_master") {
      loftAt(faces, [[mid[0] + 1, 0.7, 6.5], [mid[0] - 2, 0.35, 5]], mid[1] + 7, 0, accent, 1, false, "round");
      boxAt(faces, mid[0], mid[1] + 3.5, 0, 1.2, 6, 1.2, metal, 1, false);
    }
    classParts(faces, ship.class, nose, mid, tail, accent, metal);
    var engines = Math.max(1, spec.engines || 1);
    var sheath = engines <= 2;
    var e;
    for (e = 0; e < engines; e++) {
      var ez = (e - (engines - 1) / 2) * (engines > 3 ? 9 : 13);
      engineAt(faces, tail[0] - 2, -1.5, ez, metal, glow, hot, glen, gthick, sheath);
    }
    return faces;
  }
  function projectFace(face, yaw, pitch, fit, ox, oy, damage, pulse) {
    var scale = fit || 1;
    var world = face.pts.map(function (p) { return rotPoint([p[0] * scale, p[1] * scale, p[2] * scale], yaw, pitch); });
    var raw = vcross(vsub(world[1], world[0]), vsub(world[2], world[0]));
    var n = vnorm(raw);
    if (n[2] <= 0.035) return null;
    var key = vnorm([-0.48, 0.72, 0.5]);
    var fillL = vnorm([0.55, -0.22, 0.42]);
    var nd = Math.max(0, vdot(n, key));
    var fd = Math.max(0, vdot(n, fillL));
    var rim = Math.pow(1 - Math.max(0, Math.min(1, n[2])), 1.85);
    var beat = pulse == null || !isFinite(Number(pulse)) ? 1 : Number(pulse);
    var spec = face.emissive ? 0.22 : Math.pow(nd, 22) * 0.78;
    var amount = face.emissive ? (0.86 + 0.14 * nd) : (0.14 + 0.8 * nd + 0.16 * fd);
    if (face.emissive) amount *= 0.74 + 0.26 * beat;
    var burn = face.accent ? 0 : Math.max(0, Math.min(1, Number(damage) || 0));
    var fill = "rgb(" + face.rgb.map(function (c, i) {
      var lit = face.accent ? c * (0.62 + 0.38 * nd) : (c * amount + 255 * spec);
      if (!face.emissive && !face.accent) lit += rim * (i === 2 ? 78 : i === 1 ? 52 : 28);
      var dark = Math.round(lit * (1 - burn * 0.2));
      return Math.max(0, Math.min(255, dark));
    }).join(",") + ")";
    var depth = world.reduce(function (sum, p) { return sum + p[2]; }, 0) / world.length;
    var pts = world.map(function (p) {
      var s = 900 / (430 - p[2]);
      return [ox + p[0] * s, oy - p[1] * s];
    });
    return {
      points: pts.map(function (p) { return p[0].toFixed(1) + "," + p[1].toFixed(1); }).join(" "),
      fill: fill,
      opacity: Number(face.opacity).toFixed(2),
      depth: depth
    };
  }
  function markup(sh, def, yaw, pitch, fit, ox, oy) {
    var drawn = [];
    buildHullFaces(sh, def).forEach(function (face) {
      var cam = projectFace(face, yaw, pitch, fit, ox, oy, 0, 1);
      if (cam) drawn.push(cam);
    });
    drawn.sort(function (a, b) { return a.depth - b.depth; });
    return drawn.map(function (cam) {
      return '<polygon points="' + cam.points + '" fill="' + cam.fill + '" opacity="' + cam.opacity + '"/>';
    }).join("");
  }
  function hullRadius(faces) {
    var r = 0;
    var i, k, p, d;
    for (i = 0; i < faces.length; i++) {
      for (k = 0; k < faces[i].pts.length; k++) {
        p = faces[i].pts[k];
        d = Math.hypot(p[0], p[1], p[2]);
        if (d > r) r = d;
      }
    }
    return r;
  }
  function projectWorld(p, yaw, pitch, fit) {
    var w = rotPoint([p[0] * fit, p[1] * fit, p[2] * fit], yaw, pitch);
    var s = 900 / (430 - w[2]);
    return [200 + w[0] * s, 124 - w[1] * s, w[2]];
  }
  function silhouetteMask(faces, yaw, pitch, fit) {
    var W = 400;
    var H = 260;
    var grid = new Uint8Array(W * H);
    var f, world, raw, n, poly, minY, maxY, y, xs, i, j, y0, y1, t, k, x0, x1, x;
    for (f = 0; f < faces.length; f++) {
      world = faces[f].pts.map(function (p) { return rotPoint([p[0] * fit, p[1] * fit, p[2] * fit], yaw, pitch); });
      raw = vcross(vsub(world[1], world[0]), vsub(world[2], world[0]));
      n = vnorm(raw);
      if (n[2] <= 0.035) continue;
      poly = world.map(function (p) {
        var s = 900 / (430 - p[2]);
        return [200 + p[0] * s, 124 - p[1] * s];
      });
      minY = H;
      maxY = 0;
      for (i = 0; i < poly.length; i++) {
        if (poly[i][1] < minY) minY = poly[i][1];
        if (poly[i][1] > maxY) maxY = poly[i][1];
      }
      minY = Math.max(0, Math.floor(minY));
      maxY = Math.min(H - 1, Math.ceil(maxY));
      for (y = minY; y <= maxY; y++) {
        xs = [];
        for (i = 0, j = poly.length - 1; i < poly.length; j = i++) {
          y0 = poly[j][1];
          y1 = poly[i][1];
          if ((y0 <= y && y1 > y) || (y1 <= y && y0 > y)) {
            t = (y - y0) / ((y1 - y0) || 1e-9);
            xs.push(poly[j][0] + t * (poly[i][0] - poly[j][0]));
          }
        }
        xs.sort(function (a, b) { return a - b; });
        for (k = 0; k + 1 < xs.length; k += 2) {
          x0 = Math.max(0, Math.floor(xs[k]));
          x1 = Math.min(W - 1, Math.ceil(xs[k + 1]));
          for (x = x0; x <= x1; x++) grid[y * W + x] = 1;
        }
      }
    }
    return grid;
  }
  function boxHitsMask(grid, x0, y0, x1, y1) {
    var W = 400;
    var H = 260;
    var y, x, yy, xx;
    var top = Math.max(0, Math.floor(y0));
    var bot = Math.min(H - 1, Math.ceil(y1));
    var left = Math.max(0, Math.floor(x0));
    var right = Math.min(W - 1, Math.ceil(x1));
    if (top > bot || left > right) return false;
    for (y = top; y <= bot; y++) {
      yy = y * W;
      for (x = left; x <= right; x++) if (grid[yy + x]) return true;
    }
    return false;
  }
  function tooClose(grid, x, y, sep) {
    var cell = 8;
    var reach = Math.max(1, Math.ceil(sep / cell));
    var gx = Math.floor(x / cell);
    var gy = Math.floor(y / cell);
    var ix, iy, bucket, k, p;
    for (ix = gx - reach; ix <= gx + reach; ix++) {
      for (iy = gy - reach; iy <= gy + reach; iy++) {
        bucket = grid[ix + "," + iy];
        if (!bucket) continue;
        for (k = 0; k < bucket.length; k++) {
          p = bucket[k];
          if ((p[0] - x) * (p[0] - x) + (p[1] - y) * (p[1] - y) < sep * sep) return true;
        }
      }
    }
    return false;
  }
  function remember(grid, x, y) {
    var key = Math.floor(x / 8) + "," + Math.floor(y / 8);
    if (!grid[key]) grid[key] = [];
    grid[key].push([x, y]);
  }
  // Escorts on shells outside the hull bounding sphere. Screen boxes are tested
  // against the canonical (or caller-supplied) camera so a marker does not sit on the silhouette.
  function escortSlots(n, faces, fit, yaw, pitch) {
    var count = Math.max(0, Math.floor(Number(n) || 0));
    if (count < 1 || !faces || !faces.length) return [];
    var scale = fit > 0 ? fit : 1;
    var camY = yaw == null ? 0.82 : yaw;
    var camP = pitch == null ? 0.5 : pitch;
    var Rb = hullRadius(faces);
    var mask = silhouetteMask(faces, camY, camP, scale);
    var halfW = 3.1;
    var halfH = 4.0;
    var seps = count >= 800 ? [3.1, 2.2, 0] : count >= 80 ? [4.8, 3.4, 2.2, 0] : [12, 8, 5];
    var slots = [];
    var near = {};
    var pass, sep, ring, rad, tilt, room, i, a, ct, st, cy, sy, p, q, box, guard;
    for (pass = 0; pass < seps.length && slots.length < count; pass++) {
      sep = seps[pass];
      for (ring = 0; ring < 22 && slots.length < count; ring++) {
        rad = Rb + 10 + ring * 5.5;
        tilt = (ring * 0.71) % Math.PI;
        room = Math.max(20, Math.floor((2 * Math.PI * rad) / (sep > 0 ? sep + 2.2 : 3.2)));
        ct = Math.cos(tilt);
        st = Math.sin(tilt);
        for (i = 0; i < room && slots.length < count; i++) {
          a = 0.85 + ((i + 0.5) / room) * Math.PI * 2 + ring * 0.19;
          cy = Math.cos(a);
          sy = Math.sin(a);
          p = [sy * rad, cy * ct * rad, cy * st * rad];
          q = projectWorld(p, camY, camP, scale);
          box = [q[0] - halfW, q[1] - halfH, q[0] + halfW, q[1] + halfH];
          guard = pass < seps.length - 1;
          if (guard && (box[0] < 4 || box[2] > 396 || box[1] < 4 || box[3] > 256)) continue;
          if (boxHitsMask(mask, box[0], box[1], box[2], box[3])) continue;
          var floorSep = sep > 0 ? sep : 1.8;
          if (tooClose(near, q[0], q[1], floorSep)) continue;
          remember(near, q[0], q[1]);
          slots.push({ x: p[0], y: p[1], z: p[2], a: a, r: rad });
        }
      }
    }
    return slots;
  }
  var api = {
    version: "ship-view-full-v1",
    look: "fleet-glass-v1",
    loft: LOFT,
    ids: function () { return Object.keys(LOFT); },
    hasModel: function (hull) { return Array.isArray(LOFT[hull]) && LOFT[hull].length >= 2; },
    buildHullFaces: buildHullFaces,
    projectFace: projectFace,
    markup: markup,
    hullRadius: hullRadius,
    escortSlots: escortSlots
  };
  root.TW2KHullMeshes = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
