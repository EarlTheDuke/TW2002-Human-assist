/* warp-video-clips-v1. Plays a captured webm for the hull you are flying.

   Loaded only by the redesign cockpit (web/redesign.html). /bot does not
   include this file. Until the manifest arrives, resolve() returns null
   and the live SVG scene plays.

   window.TW2KWarpClipSource.resolve(chosen) is the NOTE 127 hook.
   chosen.playback === "move" only when the cockpit is playing a real
   warp. A paint probe leaves playback unset, so resolve returns null
   and the procedural picture stays.

   web/warp-video/manifest.json lists the captured files. Its generated
   slot is where a later AI clip is dropped: a row with a non-empty webm
   replaces the captured file for that id.
*/
(function () {
  var empty = { version: 1, hulls: {}, generated: { clips: [] } };
  var manifest = null;

  function clipPath(webm) {
    var text = String(webm || "");
    if (!text) return "";
    if (/^(https?:|blob:|data:)/i.test(text) || text.charAt(0) === "/") return text;
    return "/static/warp-video/" + text.replace(/^\/+/, "");
  }

  function generatedHit(id) {
    var clips = (manifest && manifest.generated && manifest.generated.clips) || [];
    var i;
    for (i = 0; i < clips.length; i++) {
      var row = clips[i];
      if (row && row.id === id && row.webm) return row;
    }
    return null;
  }

  function capturedHit(chosen, id) {
    var hull = chosen.hull || String(id).split(".")[0];
    var rows = (manifest && manifest.hulls && manifest.hulls[hull]) || [];
    var i;
    for (i = 0; i < rows.length; i++) {
      var row = rows[i];
      if (row && row.id === id && row.webm) return row;
    }
    return null;
  }

  function resolve(chosen) {
    if (!manifest || !chosen || chosen.playback !== "move") return null;
    var id = String(chosen.id || "");
    if (!id) return null;
    var gen = generatedHit(id);
    if (gen) {
      var file = { kind: "file", webm: clipPath(gen.webm) };
      if (gen.poster) file.poster = clipPath(gen.poster);
      if (gen.duration_ms) file.duration_ms = gen.duration_ms;
      return file;
    }
    var cap = capturedHit(chosen, id);
    if (!cap) return null;
    var hit = { kind: "file", webm: clipPath(cap.webm) };
    if (cap.poster) hit.poster = clipPath(cap.poster);
    return hit;
  }

  var ready = new Promise(function (done) {
    fetch("/static/warp-video/manifest.json", { cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error(String(r.status))); })
      .then(function (data) {
        manifest = data && typeof data === "object" ? data : empty;
        done(manifest);
      })
      .catch(function () {
        manifest = empty;
        done(manifest);
      });
  });

  window.TW2KWarpClipSource = {
    resolve: resolve,
    ready: ready,
    catalog: function () { return manifest; }
  };
})();
