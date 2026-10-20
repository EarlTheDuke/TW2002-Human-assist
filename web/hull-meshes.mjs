/* ESM surface for Track H. The mesh data lives in hull-meshes.js so the
   cockpit can load it as a classic script before redesign.js. */
const api = await loadMeshes();

async function loadMeshes() {
  if (globalThis.TW2KHullMeshes && globalThis.TW2KHullMeshes.buildHullFaces) return globalThis.TW2KHullMeshes;
  if (typeof document === "undefined") {
    const fs = await import("node:fs");
    const url = await import("node:url");
    const path = url.fileURLToPath(new URL("./hull-meshes.js", import.meta.url));
    const src = fs.readFileSync(path, "utf8");
    const run = new Function("globalThis", src + "\nreturn globalThis.TW2KHullMeshes;");
    return run(globalThis);
  }
  await new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = new URL("./hull-meshes.js", import.meta.url).href;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("hull-meshes.js"));
    document.head.appendChild(script);
  });
  return globalThis.TW2KHullMeshes;
}

export const version = api.version;
export const loft = api.loft;
export const hullIds = api.ids;
export const hasHull = api.hasModel;
export const buildHullFaces = api.buildHullFaces;
export const projectFace = api.projectFace;
export const hullMarkup = api.markup;
export default api;
