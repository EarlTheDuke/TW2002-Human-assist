/* ship-view-full-v1. Shared hull meshes for the redesign ship panel and the warp clips.
   Our own lofts. No copied ANSI, no traced cinema.
   Classic page: window.TW2KHullMeshes
   Module: import { buildHullFaces } from "/static/hull-meshes.mjs"
*/
(function (root) {
  "use strict";
  var LOFT = {
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
    interdictor_cruiser: [[48, 16, 24], [8, 20, 30], [-26, 19, 28], [-66, 14, 20]]
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
    imperial_starship: "keel",
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
  function pushFace(faces, pts, rgb, opacity, emissive, ref) {
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
    faces.push({ pts: ordered, rgb: rgb, opacity: opacity == null ? 1 : opacity, emissive: !!emissive });
  }
  function octagon(x, sy, sz, dy, dz) {
    var pts = [];
    var i;
    for (i = 0; i < 8; i++) {
      var t = (i + 0.5) * Math.PI / 4;
      pts.push([x, dy + Math.cos(t) * sy, dz + Math.sin(t) * sz]);
    }
    return pts;
  }
  function loftAt(faces, sections, dy, dz, rgb, opacity, emissive) {
    var rings = sections.map(function (s) { return octagon(s[0], s[1], s[2], dy, dz); });
    var i;
    for (i = 0; i < rings.length - 1; i++) {
      var a = rings[i];
      var b = rings[i + 1];
      var cx = (sections[i][0] + sections[i + 1][0]) / 2;
      var k;
      for (k = 0; k < 8; k++) {
        var k2 = (k + 1) % 8;
        pushFace(faces, [a[k], a[k2], b[k2], b[k]], rgb, opacity, emissive, [cx, dy, dz]);
      }
    }
    pushFace(faces, rings[0], rgb, opacity, emissive, [sections[0][0] - 4, dy, dz]);
    var last = sections.length - 1;
    pushFace(faces, rings[last], rgb, opacity, emissive, [sections[last][0] + 4, dy, dz]);
  }
  function boxAt(faces, x, y, z, sx, sy, sz, rgb, opacity, emissive) {
    var hx = sx / 2;
    var hy = sy / 2;
    var hz = sz / 2;
    var p = [
      [x - hx, y - hy, z - hz], [x + hx, y - hy, z - hz], [x + hx, y + hy, z - hz], [x - hx, y + hy, z - hz],
      [x - hx, y - hy, z + hz], [x + hx, y - hy, z + hz], [x + hx, y + hy, z + hz], [x - hx, y + hy, z + hz]
    ];
    [[0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [2, 6, 7, 3], [0, 3, 7, 4], [1, 5, 6, 2]].forEach(function (quad) {
      pushFace(faces, quad.map(function (i) { return p[i]; }), rgb, opacity, emissive, [x, y, z]);
    });
  }
  function classParts(faces, cls, nose, mid, tail, accent, metal) {
    var part = PARTS[cls] || "";
    if (part === "fins") {
      [-1, 1].forEach(function (sign) {
        loftAt(faces, [[mid[0] + 4, 0.8, 10], [tail[0] + 2, 0.5, 3]], 0, sign * 6, metal, 1, false);
      });
    } else if (part === "canards") {
      [-1, 1].forEach(function (sign) {
        loftAt(faces, [[nose[0] - 8, 0.5, 9], [nose[0] - 22, 0.35, 2]], 1.2, sign * 3, accent, 1, false);
      });
    } else if (part === "missiles") {
      [-1, 1].forEach(function (sign) {
        boxAt(faces, mid[0], mid[1] + 6, sign * 5, 28, 2.2, 2.2, accent, 1, false);
        boxAt(faces, mid[0] + 8, mid[1] + 6, sign * 5, 4, 2.6, 2.6, [255, 196, 120], 1, false);
      });
    } else if (part === "turrets") {
      [-1, 1].forEach(function (sign) {
        boxAt(faces, mid[0] + sign * 6, mid[1] + 4, sign * 8, 8, 5, 8, metal, 1, false);
        boxAt(faces, mid[0] + 10 + sign * 4, mid[1] + 6, sign * 8, 14, 1.4, 1.4, accent, 1, false);
      });
    } else if (part === "tower") {
      boxAt(faces, mid[0], mid[1] + 10, 0, 10, 14, 8, metal, 1, false);
      boxAt(faces, mid[0] + 2, mid[1] + 16, 0, 6, 4, 5, accent, 1, false);
    } else if (part === "cargo") {
      [-1, 1].forEach(function (sign) {
        loftAt(faces, [[mid[0] + 10, 9, 9], [mid[0] - 18, 10, 10], [tail[0] + 6, 7, 7]], -2, sign * (mid[2] + 6), metal, 1, false);
      });
    } else if (part === "spine") {
      boxAt(faces, (nose[0] + tail[0]) / 2, 2, 0, Math.abs(nose[0] - tail[0]) * 0.7, 6, mid[2] * 1.3, metal, 1, false);
    } else if (part === "cheeks") {
      [-1, 1].forEach(function (sign) {
        loftAt(faces, [[mid[0] + 8, 12, 8], [mid[0] - 10, 14, 10]], -4, sign * (mid[2] * 0.55), metal, 1, false);
      });
    } else if (part === "prongs") {
      [-1, 1].forEach(function (sign) {
        loftAt(faces, [[nose[0] + 16, 2.2, 2.2], [nose[0] - 6, 3.2, 3.2]], nose[1] * 0.15, sign * (nose[2] + 6), accent, 1, false);
      });
    } else if (part === "mast") {
      boxAt(faces, mid[0] - 4, mid[1] + 8, 0, 1.4, 12, 1.4, metal, 1, false);
      loftAt(faces, [[mid[0] - 2, 1.1, 7], [mid[0] - 8, 0.6, 5]], mid[1] + 14, 0, accent, 1, false);
    } else if (part === "quad") {
      [[1, 1], [1, -1], [-1, 1], [-1, -1]].forEach(function (s) {
        loftAt(faces, [[mid[0] - 6, 2.2, 2.2], [tail[0] - 4, 2.6, 2.6]], s[0] * 6, s[1] * (mid[2] + 4), accent, 1, false);
      });
    } else if (part === "swept") {
      [-1, 1].forEach(function (sign) {
        loftAt(faces, [[nose[0] - 18, 0.7, 18], [tail[0] + 8, 0.4, 3]], 0, sign * 4, metal, 1, false);
      });
    } else if (part === "armor") {
      [-1, 1].forEach(function (sign) {
        boxAt(faces, mid[0], 0, sign * (mid[2] + 4), 22, mid[1] * 1.4, 6, metal, 1, false);
      });
    } else if (part === "saddle") {
      boxAt(faces, mid[0], mid[1] + 6, 0, 24, 6, 16, metal, 1, false);
      [-1, 1].forEach(function (sign) {
        boxAt(faces, tail[0] + 8, -2, sign * 8, 16, 5, 6, accent, 1, false);
      });
    } else if (part === "hoop") {
      var i;
      for (i = 0; i < 10; i++) {
        var a = (i / 10) * Math.PI * 2;
        boxAt(faces, mid[0] - 6, Math.cos(a) * (mid[1] + 12), Math.sin(a) * (mid[2] + 8), 5, 2.6, 2.6, accent, 1, false);
      }
    } else if (part === "keel") {
      boxAt(faces, mid[0], -mid[1] - 2, 0, Math.abs(nose[0] - tail[0]) * 0.45, 3, 4, metal, 1, false);
    }
  }
  function buildHullFaces(sh, def) {
    var ship = sh || {};
    var spec = def || {};
    var sections = LOFT[ship.class] || LOFT.merchant_cruiser;
    var accent = parseHex(spec.accent || "#7aa2ff");
    var hull = mixRgb([18, 28, 52], accent, 0.62);
    var metal = mixRgb([32, 42, 64], accent, 0.4);
    var glass = mixRgb([220, 248, 255], accent, 0.22);
    var tw = !!(ship.transwarp && ship.transwarp.fitted);
    var glow = tw ? [255, 110, 255] : [190, 255, 255];
    var faces = [];
    loftAt(faces, sections, 0, 0, hull, 1, false);
    var nose = sections[0];
    var mid = sections[1];
    var tail = sections[sections.length - 1];
    var detail = {};
    String(spec.detail || "").split(" ").forEach(function (bit) { if (bit) detail[bit] = true; });
    if (detail.bridge) {
      loftAt(faces, [
        [mid[0] + 12, 2.6, 3.4],
        [mid[0], 3.8, 4.6],
        [mid[0] - 14, 2.2, 2.8]
      ], mid[1] + 1.2, 0, glass, 1, false);
    }
    if (detail.pods) {
      var z = mid[2] + 8;
      [-1, 1].forEach(function (sign) {
        loftAt(faces, [
          [mid[0] + 16, 7, 7],
          [mid[0] - 12, 8.5, 8.5],
          [tail[0] + 8, 5.5, 5.5]
        ], -6, sign * z, metal, 1, false);
      });
    }
    if (detail.wings) {
      [-1, 1].forEach(function (sign) {
        loftAt(faces, [
          [mid[0] + 8, 1.1, 16],
          [tail[0] + 16, 0.7, 4]
        ], 0, sign * (mid[2] + 1), metal, 1, false);
      });
    }
    if (detail.nacelles) {
      [-1, 1].forEach(function (sign) {
        loftAt(faces, [
          [mid[0] - 4, 2.5, 2.5],
          [tail[0] - 2, 3.2, 3.2],
          [tail[0] - 24, 2, 2]
        ], -mid[1] * 0.4, sign * (mid[2] + 6), accent, 1, false);
      });
      if ((spec.engines || 1) >= 4) {
        [-1, 1].forEach(function (sign) {
          loftAt(faces, [
            [mid[0] - 2, 2.1, 2.1],
            [tail[0], 2.8, 2.8],
            [tail[0] - 22, 1.7, 1.7]
          ], mid[1] * 0.55, sign * (mid[2] + 4), accent, 1, false);
        });
      }
    }
    if (detail.guns || ship.class === "imperial_starship") {
      [-1, 1].forEach(function (sign) {
        boxAt(faces, nose[0] + 6, nose[1] * 0.2, sign * (nose[2] * 0.35 + 5), 22, 1.6, 1.6, accent, 1, false);
      });
    }
    if (detail.rails) {
      boxAt(faces, (nose[0] + mid[0]) / 2, mid[1] + 1.2, 0, Math.abs(nose[0] - mid[0]), 1.8, 3.2, accent, 1, false);
    }
    if (detail.dish) {
      loftAt(faces, [[mid[0] + 1, 1.2, 8], [mid[0] - 2, 0.7, 6.5]], mid[1] + 9, 0, accent, 1, false);
      boxAt(faces, mid[0], mid[1] + 5, 0, 1.4, 8, 1.4, metal, 1, false);
    }
    if (detail.ring) {
      var radY = nose[1] + 11;
      var radZ = nose[2] + 8;
      var i;
      for (i = 0; i < 8; i++) {
        var a = (i / 8) * Math.PI * 2;
        boxAt(faces, nose[0] - 4, Math.cos(a) * radY, Math.sin(a) * radZ, 6, 3.2, 3.2, accent, 1, false);
      }
    }
    classParts(faces, ship.class, nose, mid, tail, accent, metal);
    var engines = Math.max(1, spec.engines || 1);
    var e;
    for (e = 0; e < engines; e++) {
      var ez = (e - (engines - 1) / 2) * (engines > 3 ? 8 : 12);
      boxAt(faces, tail[0] - 4, -2, ez, 8, 4.6, 4.6, metal, 1, false);
      boxAt(faces, tail[0] - 12, -2, ez, 8, 2.2, 2.2, glow, 0.95, true);
    }
    return faces;
  }
  function projectFace(face, yaw, pitch, fit, ox, oy, damage) {
    var scale = fit || 1;
    var world = face.pts.map(function (p) { return rotPoint([p[0] * scale, p[1] * scale, p[2] * scale], yaw, pitch); });
    var raw = vcross(vsub(world[1], world[0]), vsub(world[2], world[0]));
    var n = vnorm(raw);
    if (n[2] <= 0.04) return null;
    var light = vnorm([-0.28, 0.84, 0.46]);
    var nd = Math.max(0, vdot(n, light));
    var spec = face.emissive ? 0.15 : Math.pow(nd, 10) * 0.45;
    var amount = face.emissive ? 0.78 + 0.22 * nd : 0.22 + 0.8 * nd;
    var burn = Math.max(0, Math.min(1, Number(damage) || 0));
    var fill = "rgb(" + face.rgb.map(function (c, i) {
      var lit = Math.round(c * amount + 255 * spec);
      var dark = Math.round(lit * (1 - burn * 0.62));
      if (i === 0) dark = Math.min(255, dark + Math.round(burn * 110));
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
      var cam = projectFace(face, yaw, pitch, fit, ox, oy, 0);
      if (cam) drawn.push(cam);
    });
    drawn.sort(function (a, b) { return a.depth - b.depth; });
    return drawn.map(function (cam) {
      return '<polygon points="' + cam.points + '" fill="' + cam.fill + '" opacity="' + cam.opacity + '"/>';
    }).join("");
  }
  var api = {
    version: "ship-view-full-v1",
    loft: LOFT,
    ids: function () { return Object.keys(LOFT); },
    hasModel: function (hull) { return Array.isArray(LOFT[hull]) && LOFT[hull].length >= 2; },
    buildHullFaces: buildHullFaces,
    projectFace: projectFace,
    markup: markup
  };
  root.TW2KHullMeshes = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
