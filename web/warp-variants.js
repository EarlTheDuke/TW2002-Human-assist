/* cockpit-warp-clips-per-hull-v1. Ten procedural warp pictures per hull.

   Each picture is 1.5–3 seconds. The hull is the NOTE 126 mesh, imported
   from /static/hull-meshes.mjs (buildHullFaces, projectFace, hullMarkup)
   by web/warp-hull.mjs. This file names the camera, the star field, and
   the exit, and draws the star layer. No network.

   window.TW2KWarpClipSource is an optional hook. This file does not set it.
   A pre-rendered clip or a live generator assigns it later:

     window.TW2KWarpClipSource = {
       resolve(chosen) {
         // chosen: {id, hull, kind, duration_ms, webm, mp4, poster, playback}
         // playback === "move" only when the ship actually warped.
         // A paint or a still leaves playback unset: return null then.
         // return null to keep the procedural SVG for this variant
         // return a file to replace that one variant:
         //   {kind: "file", webm, mp4, poster, duration_ms}
         // webm/mp4 may be a path under /static/media/, a site path
         // starting with "/", or an http(s), blob, or data URL.
       }
     };

   The cockpit calls resolve(chosen) once per play, before it paints.
   A throw or a non-object result keeps the procedural picture.
*/
(function () {
  // NOTE 146. Ten pictures. Camera, starfield, plume, and exit flash all differ.
  // Glow colors are the same accents as the ship panel. No filmed art.
  var STYLES = [
    { n: "01", style: "streak", camera: "side", stars: "streaks", exit: "jump", yaw: 1.35, pitch: 0.18, fit: 1.15, duration_ms: 1600, glow: "#9fffff", plume: 12, streak: 0, flash: "#f4ffff" },
    { n: "02", style: "chase", camera: "chase", stars: "streaks", exit: "fade", yaw: 0.28, pitch: 0.48, fit: 1.1, duration_ms: 1800, glow: "#5dffc8", plume: 22, streak: 14, flash: "#d9fff2" },
    { n: "03", style: "headon", camera: "headon", stars: "tunnel", exit: "flash", yaw: -1.35, pitch: 0.2, fit: 1, duration_ms: 2100, glow: "#ffb15a", plume: 16, streak: -16, flash: "#ffe2c2" },
    { n: "04", style: "top", camera: "top", stars: "sparse", exit: "fade", yaw: 0.45, pitch: 1.05, fit: 0.92, duration_ms: 2400, glow: "#c5c8ff", plume: 34, streak: 8, flash: "#eceeff" },
    { n: "05", style: "side", camera: "side", stars: "nebula", exit: "fold", yaw: 1.75, pitch: 0.1, fit: 1.12, duration_ms: 2700, glow: "#ff77ff", plume: 20, streak: -10, flash: "#ffd6ff" },
    { n: "06", style: "gate", camera: "gate", stars: "gate", exit: "gate", yaw: 0.62, pitch: 0.22, fit: 1.02, duration_ms: 1500, glow: "#ffe566", plume: 10, streak: 22, flash: "#fff6c8" },
    { n: "07", style: "headon", camera: "headon", stars: "sparse", exit: "fade", yaw: -1.2, pitch: 0.28, fit: 0.96, duration_ms: 1900, glow: "#7af0ff", plume: 30, streak: -22, flash: "#dffbff" },
    { n: "08", style: "top", camera: "top", stars: "streaks", exit: "flash", yaw: 0.85, pitch: 1.12, fit: 0.88, duration_ms: 2300, glow: "#ff8844", plume: 18, streak: 18, flash: "#ffd2b8" },
    { n: "09", style: "side", camera: "side", stars: "tunnel", exit: "fade", yaw: 2.05, pitch: 0.26, fit: 1.08, duration_ms: 2600, glow: "#ff6d8a", plume: 26, streak: -6, flash: "#ffd5de" },
    { n: "10", style: "chase", camera: "chase", stars: "nebula", exit: "flash", yaw: 0.5, pitch: 0.34, fit: 1.12, duration_ms: 3000, glow: "#7aa2ff", plume: 38, streak: 4, flash: "#dce6ff" }
  ];

  function hashId(id) {
    var h = 2166136261;
    var text = String(id || "");
    for (var i = 0; i < text.length; i++) {
      h ^= text.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }

  function makeRng(seed) {
    var s = seed % 233280;
    return function () {
      s = (s * 9301 + 49297) % 233280;
      return s / 233280;
    };
  }

  function lookup(id) {
    var match = /^[a-z0-9_]+\.([a-z]+)\.(\d{2})$/.exec(String(id || ""));
    if (!match) return null;
    for (var i = 0; i < STYLES.length; i++) {
      if (STYLES[i].n === match[2] && STYLES[i].style === match[1]) return STYLES[i];
    }
    return null;
  }

  function glowOf(id) {
    var style = lookup(id);
    return (style && style.glow) || "#b9dcff";
  }

  function stars(id, kind) {
    var rnd = makeRng(hashId(id));
    var glow = glowOf(id);
    var body = "";
    var i;
    // A soft wash in this clip's engine color, so ten pictures do not share one sky.
    body += '<ellipse data-testid="warp-wash" cx="200" cy="130" rx="168" ry="96" fill="' + glow + '" opacity="0.09"/>';
    if (kind === "tunnel") {
      body += '<ellipse cx="200" cy="130" rx="10" ry="6" fill="' + glow + '" opacity="0.55"/>';
      for (i = 0; i < 9; i++) {
        var rx = 16 + i * 20 + rnd() * 5;
        var ry = 8 + i * 11 + rnd() * 3;
        body += '<ellipse cx="200" cy="130" rx="' + rx.toFixed(1) + '" ry="' + ry.toFixed(1)
          + '" fill="none" stroke="' + glow + '" stroke-width="' + (i % 3 === 0 ? "1.8" : "1.1")
          + '" opacity="' + (0.22 + rnd() * 0.4).toFixed(2) + '"/>';
      }
      for (i = 0; i < 18; i++) {
        var ang = rnd() * Math.PI * 2;
        var inner = 28 + rnd() * 20;
        var outer = inner + 36 + rnd() * 70;
        body += '<line x1="' + (200 + Math.cos(ang) * inner).toFixed(1) + '" y1="' + (130 + Math.sin(ang) * inner * 0.58).toFixed(1)
          + '" x2="' + (200 + Math.cos(ang) * outer).toFixed(1) + '" y2="' + (130 + Math.sin(ang) * outer * 0.58).toFixed(1)
          + '" stroke="' + glow + '" stroke-width="0.9" opacity="' + (0.25 + rnd() * 0.4).toFixed(2) + '"/>';
      }
      return '<g class="warp-stars" data-testid="warp-stars" data-stars="tunnel">' + body + "</g>";
    }
    if (kind === "nebula") {
      var tints = ["#24306a", "#3a2060", "#12324a", "#2a3a28"];
      for (i = 0; i < 4; i++) {
        body += '<ellipse cx="' + (70 + rnd() * 250).toFixed(1) + '" cy="' + (36 + rnd() * 180).toFixed(1)
          + '" rx="' + (58 + rnd() * 78).toFixed(1) + '" ry="' + (28 + rnd() * 40).toFixed(1)
          + '" fill="' + tints[i] + '" opacity="' + (0.34 + rnd() * 0.28).toFixed(2) + '"/>';
      }
      body += '<ellipse cx="' + (120 + rnd() * 140).toFixed(1) + '" cy="' + (70 + rnd() * 90).toFixed(1)
        + '" rx="' + (70 + rnd() * 40).toFixed(1) + '" ry="' + (36 + rnd() * 24).toFixed(1)
        + '" fill="' + glow + '" opacity="' + (0.16 + rnd() * 0.12).toFixed(2) + '"/>';
      return '<g class="warp-stars" data-testid="warp-stars" data-stars="nebula">' + body + "</g>";
    }
    if (kind === "sparse") {
      for (i = 0; i < 22; i++) {
        var big = i % 7 === 0;
        body += '<circle cx="' + (rnd() * 380 + 10).toFixed(1) + '" cy="' + (rnd() * 240 + 10).toFixed(1)
          + '" r="' + (big ? (2.2 + rnd() * 1.4) : (0.7 + rnd() * 1.1)).toFixed(2)
          + '" fill="' + (big ? glow : "#d5e8ff") + '" opacity="' + (0.4 + rnd() * 0.5).toFixed(2) + '"/>';
      }
      return '<g class="warp-stars" data-testid="warp-stars" data-stars="sparse">' + body + "</g>";
    }
    if (kind === "gate") {
      body += '<rect x="108" y="38" width="184" height="184" fill="none" stroke="' + glow + '" stroke-width="4.2" opacity="0.95"/>';
      body += '<rect x="124" y="54" width="152" height="152" fill="none" stroke="#e7f7ff" stroke-width="1.6" opacity="0.8"/>';
      for (i = 0; i < 7; i++) {
        var gy = 64 + i * 20 + rnd() * 4;
        body += '<line x1="132" y1="' + gy.toFixed(1) + '" x2="268" y2="' + (gy + rnd() * 4 - 2).toFixed(1)
          + '" stroke="' + glow + '" stroke-width="1.3" opacity="' + (0.28 + rnd() * 0.45).toFixed(2) + '"/>';
      }
      return '<g class="warp-stars" data-testid="warp-stars" data-stars="gate">' + body + "</g>";
    }
    var style = lookup(id) || {};
    var tilt = (Number(style.streak) || 0) * Math.PI / 180;
    var ox = 200 + Math.cos(tilt) * 36;
    var oy = 130 + Math.sin(tilt) * 22;
    for (i = 0; i < 42; i++) {
      var ang2 = rnd() * Math.PI * 2;
      var near = 8 + rnd() * 28;
      var far = near + 48 + rnd() * 130;
      var x1 = ox + Math.cos(ang2) * near;
      var y1 = oy + Math.sin(ang2) * near * 0.55;
      var x2 = ox + Math.cos(ang2) * far;
      var y2 = oy + Math.sin(ang2) * far * 0.55;
      body += '<line x1="' + x1.toFixed(1) + '" y1="' + y1.toFixed(1) + '" x2="' + x2.toFixed(1) + '" y2="' + y2.toFixed(1)
        + '" stroke="' + glow + '" stroke-width="' + (0.7 + rnd() * 1.3).toFixed(2)
        + '" opacity="' + (0.32 + rnd() * 0.55).toFixed(2) + '"/>';
    }
    return '<g class="streaks" data-testid="warp-streaks" data-stars="streaks">' + body + "</g>";
  }

  // The cockpit draws from this bag so a warp does not repeat the clip just played.
  // Pass a rnd() in tests. Math.random is the page.
  function drawBag(ids, lastId, rnd) {
    var random = typeof rnd === "function" ? rnd : Math.random;
    var bag = ids.slice();
    var i;
    var j;
    var swap;
    for (i = bag.length - 1; i > 0; i--) {
      j = Math.floor(random() * (i + 1));
      swap = bag[i];
      bag[i] = bag[j];
      bag[j] = swap;
    }
    if (bag.length > 1 && bag[bag.length - 1] === lastId) {
      j = Math.floor(random() * (bag.length - 1));
      swap = bag[bag.length - 1];
      bag[bag.length - 1] = bag[j];
      bag[j] = swap;
    }
    return bag;
  }

  function takeId(ids, state, rnd) {
    var bag = state && state.bag ? state.bag.slice() : [];
    var last = state && state.last ? String(state.last) : "";
    var list = (ids || []).map(function (id) { return String(id); });
    var same = bag.length > 0 && bag.every(function (id) { return list.indexOf(id) >= 0; });
    if (!same) bag = drawBag(list, last, rnd);
    var id = bag.pop();
    if (id === last && bag.length) {
      bag.unshift(id);
      id = bag.pop();
    }
    return { id: id, bag: bag, last: id || last };
  }

  window.TW2KWarpVariants = {
    styles: STYLES,
    lookup: lookup,
    stars: stars,
    drawBag: drawBag,
    takeId: takeId
  };
})();
