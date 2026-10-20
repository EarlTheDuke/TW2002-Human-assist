/* Warp scenes use the NOTE 126 meshes.
   import { buildHullFaces, projectFace, hullMarkup } from "/static/hull-meshes.mjs"
   If that module fails to load, the NOTE 118 file fills the same three calls.
*/
const root = globalThis;

function use126(api) {
  root.TW2KWarpHull = {
    source: "note126",
    buildHullFaces: api.buildHullFaces,
    projectFace: api.projectFace,
    hullMarkup: api.hullMarkup,
  };
}

function use118(old) {
  root.TW2KWarpHull = {
    source: "note118",
    buildHullFaces: function (ship, def) { return old.buildFaces(ship, def); },
    projectFace: function (face, yaw, pitch, fit, ox, oy) { return old.project(face, yaw, pitch, fit, ox, oy); },
    hullMarkup: function (ship, def, yaw, pitch, fit, ox, oy) {
      const drawn = [];
      old.buildFaces(ship, def).forEach(function (face) {
        const cam = old.project(face, yaw, pitch, fit || 1, ox, oy);
        if (cam) drawn.push(cam);
      });
      drawn.sort(function (a, b) { return a.depth - b.depth; });
      return drawn.map(function (cam) {
        return '<polygon points="' + cam.points + '" fill="' + cam.fill + '" opacity="' + cam.opacity + '"/>';
      }).join("");
    },
  };
}

try {
  const api = await import("/static/hull-meshes.mjs");
  if (!api.buildHullFaces || !api.projectFace || !api.hullMarkup) throw new Error("hull-meshes.mjs");
  use126(api);
} catch (err) {
  await new Promise(function (resolve, reject) {
    const script = document.createElement("script");
    script.src = "/static/hull-mesh.js";
    script.onload = function () { resolve(); };
    script.onerror = function () { reject(err); };
    document.head.appendChild(script);
  });
  if (!root.TW2KHullMesh || !root.TW2KHullMesh.buildFaces) throw err;
  use118(root.TW2KHullMesh);
}
