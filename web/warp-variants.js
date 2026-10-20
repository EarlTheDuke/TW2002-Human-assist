/* cockpit-warp-clips-per-hull-v1. Ten procedural warp pictures per hull.

   Each picture is 1.5–3 seconds. The hull is the NOTE 126 mesh, imported
   from /static/hull-meshes.mjs (buildHullFaces, projectFace, hullMarkup)
   by web/warp-hull.mjs. This file names the camera, the star field, and
   the exit, and draws the star layer. No network.

   window.TW2KWarpClipSource is an optional hook. This file does not set it.
   A pre-rendered clip or a live generator assigns it later:

     window.TW2KWarpClipSource = {
       resolve(chosen) {
         // chosen: {id, hull, kind, duration_ms, webm, mp4, poster}
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
  var STYLES = [
    { n: "01", style: "streak", camera: "side", stars: "streaks", exit: "jump", yaw: 1.35, pitch: 0.18, fit: 0.92, duration_ms: 1600 },
    { n: "02", style: "chase", camera: "chase", stars: "streaks", exit: "fade", yaw: 0.28, pitch: 0.48, fit: 0.84, duration_ms: 1800 },
    { n: "03", style: "headon", camera: "headon", stars: "tunnel", exit: "flash", yaw: -1.35, pitch: 0.2, fit: 0.76, duration_ms: 2100 },
    { n: "04", style: "top", camera: "top", stars: "sparse", exit: "fade", yaw: 0.45, pitch: 1.05, fit: 0.7, duration_ms: 2400 },
    { n: "05", style: "side", camera: "side", stars: "nebula", exit: "fold", yaw: 1.75, pitch: 0.1, fit: 0.9, duration_ms: 2700 },
    { n: "06", style: "gate", camera: "gate", stars: "gate", exit: "gate", yaw: 0.62, pitch: 0.22, fit: 0.78, duration_ms: 1500 },
    { n: "07", style: "headon", camera: "headon", stars: "sparse", exit: "fade", yaw: -1.2, pitch: 0.28, fit: 0.74, duration_ms: 1900 },
    { n: "08", style: "top", camera: "top", stars: "streaks", exit: "flash", yaw: 0.85, pitch: 1.12, fit: 0.66, duration_ms: 2300 },
    { n: "09", style: "side", camera: "side", stars: "tunnel", exit: "fade", yaw: 2.05, pitch: 0.26, fit: 0.88, duration_ms: 2600 },
    { n: "10", style: "chase", camera: "chase", stars: "nebula", exit: "flash", yaw: 0.5, pitch: 0.34, fit: 0.86, duration_ms: 3000 }
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

  function stars(id, kind) {
    var rnd = makeRng(hashId(id));
    var body = "";
    var i;
    if (kind === "tunnel") {
      for (i = 0; i < 7; i++) {
        var rx = 18 + i * 22 + rnd() * 6;
        var ry = 10 + i * 12 + rnd() * 4;
        body += '<ellipse cx="200" cy="130" rx="' + rx.toFixed(1) + '" ry="' + ry.toFixed(1)
          + '" fill="none" stroke="#9ecbff" stroke-width="1.2" opacity="' + (0.18 + rnd() * 0.35).toFixed(2) + '"/>';
      }
      return '<g class="warp-stars" data-testid="warp-stars" data-stars="tunnel">' + body + "</g>";
    }
    if (kind === "nebula") {
      var tints = ["#24306a", "#3a2060", "#12324a", "#2a3a28"];
      for (i = 0; i < 4; i++) {
        body += '<ellipse cx="' + (80 + rnd() * 240).toFixed(1) + '" cy="' + (40 + rnd() * 180).toFixed(1)
          + '" rx="' + (50 + rnd() * 70).toFixed(1) + '" ry="' + (24 + rnd() * 36).toFixed(1)
          + '" fill="' + tints[i] + '" opacity="' + (0.28 + rnd() * 0.25).toFixed(2) + '"/>';
      }
      return '<g class="warp-stars" data-testid="warp-stars" data-stars="nebula">' + body + "</g>";
    }
    if (kind === "sparse") {
      for (i = 0; i < 16; i++) {
        body += '<circle cx="' + (rnd() * 380 + 10).toFixed(1) + '" cy="' + (rnd() * 240 + 10).toFixed(1)
          + '" r="' + (0.6 + rnd() * 1.3).toFixed(2) + '" fill="#d5e8ff" opacity="' + (0.35 + rnd() * 0.5).toFixed(2) + '"/>';
      }
      return '<g class="warp-stars" data-testid="warp-stars" data-stars="sparse">' + body + "</g>";
    }
    if (kind === "gate") {
      body += '<rect x="118" y="46" width="164" height="168" fill="none" stroke="#e7f7ff" stroke-width="3.2" opacity="0.92"/>';
      body += '<rect x="132" y="60" width="136" height="140" fill="none" stroke="#7eb6ff" stroke-width="1.5" opacity="0.75"/>';
      for (i = 0; i < 5; i++) {
        var gy = 72 + i * 22 + rnd() * 6;
        body += '<line x1="140" y1="' + gy.toFixed(1) + '" x2="260" y2="' + (gy + rnd() * 4 - 2).toFixed(1)
          + '" stroke="#b7e4ff" stroke-width="1.1" opacity="' + (0.28 + rnd() * 0.4).toFixed(2) + '"/>';
      }
      return '<g class="warp-stars" data-testid="warp-stars" data-stars="gate">' + body + "</g>";
    }
    for (i = 0; i < 36; i++) {
      var y = rnd() * 244 + 8;
      var x = rnd() * 300 + 8;
      var w = 18 + rnd() * 70;
      body += '<line x1="' + x.toFixed(1) + '" y1="' + y.toFixed(1) + '" x2="' + (x + w).toFixed(1) + '" y2="' + y.toFixed(1)
        + '" stroke="#b9dcff" stroke-width="' + (0.6 + rnd() * 1.1).toFixed(2) + '" opacity="' + (0.28 + rnd() * 0.55).toFixed(2) + '"/>';
    }
    return '<g class="streaks" data-testid="warp-streaks" data-stars="streaks">' + body + "</g>";
  }

  window.TW2KWarpVariants = {
    styles: STYLES,
    lookup: lookup,
    stars: stars
  };
})();
