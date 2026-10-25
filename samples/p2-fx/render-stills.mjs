/**
 * Headless stills for the P2 FX sample. One Chrome, DevTools protocol,
 * capture after data-ready="1". Skips when Chrome is missing.
 * WebGL stays off. The cockpit is not started.
 */
import { spawn } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import url from "node:url";

const here = path.dirname(url.fileURLToPath(import.meta.url));
const model = new Function(
  "globalThis",
  `${fs.readFileSync(path.join(here, "fx-model.js"), "utf8")}\nreturn globalThis.P2FXModel;`,
)(globalThis);
const { STILL_SHOTS, markerCount, shotState } = model;
const stillsDir = path.join(here, "stills");
const chromeBins = ["/usr/bin/google-chrome-stable", "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"];
const chromeBin = chromeBins.find((bin) => fs.existsSync(bin));

if (!chromeBin) {
  console.log("no headless chrome on this machine; stills skipped");
  process.exit(0);
}

fs.mkdirSync(stillsDir, { recursive: true });
const profile = fs.mkdtempSync(path.join("/tmp", "p2fx-chrome-"));
const port = 9340;
const chrome = spawn(chromeBin, [
  "--headless=new",
  "--no-sandbox",
  "--disable-gpu",
  "--disable-dev-shm-usage",
  "--hide-scrollbars",
  "--force-device-scale-factor=1",
  `--remote-debugging-port=${port}`,
  `--user-data-dir=${profile}`,
  "--window-size=1080,700",
  "about:blank",
], { stdio: "ignore" });

function get(pathname) {
  return new Promise((resolve, reject) => {
    const req = http.get({ host: "127.0.0.1", port, path: pathname }, (res) => {
      let data = "";
      res.on("data", (chunk) => { data += chunk; });
      res.on("end", () => resolve(data));
    });
    req.on("error", reject);
  });
}

async function waitPage() {
  for (let i = 0; i < 80; i++) {
    try {
      const list = JSON.parse(await get("/json/list"));
      const page = list.find((target) => target.type === "page" && target.webSocketDebuggerUrl);
      if (page) return page;
    } catch { /* chrome still booting */ }
    await new Promise((resolve) => setTimeout(resolve, 80));
  }
  throw new Error("chrome devtools port did not open");
}

function pageUrl(shot) {
  const file = url.pathToFileURL(path.join(here, "index.html"));
  file.searchParams.set("shot", shot);
  return file.href;
}

const failures = [];
let ws;

try {
  const page = await waitPage();
  ws = new WebSocket(page.webSocketDebuggerUrl);
  let nextId = 0;
  const pending = new Map();
  function send(method, params = {}) {
    const id = ++nextId;
    return new Promise((resolve, reject) => {
      pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });
  }
  ws.addEventListener("message", (ev) => {
    const msg = JSON.parse(ev.data);
    if (!msg.id || !pending.has(msg.id)) return;
    const job = pending.get(msg.id);
    pending.delete(msg.id);
    if (msg.error) job.reject(new Error(JSON.stringify(msg.error)));
    else job.resolve(msg.result);
  });
  await new Promise((resolve) => ws.addEventListener("open", resolve));
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Emulation.setDeviceMetricsOverride", {
    width: 1080,
    height: 700,
    deviceScaleFactor: 1,
    mobile: false,
  });

  async function readState() {
    const result = await send("Runtime.evaluate", {
      expression: `({
        ready: document.querySelector("#stageSvg")?.getAttribute("data-ready"),
        markers: document.querySelector("#stageSvg")?.getAttribute("data-markers"),
        placed: document.querySelector("#stageSvg")?.getAttribute("data-placed"),
        tell: document.querySelector("#stageSvg")?.getAttribute("data-tell"),
        planet: document.querySelector("#stageSvg")?.getAttribute("data-planet"),
        mine: document.querySelector("#stageSvg")?.getAttribute("data-mine-kind"),
        clock: document.querySelector("#stageSvg")?.getAttribute("data-clock"),
        triangles: document.querySelectorAll("[data-testid=fighter-triangle]").length,
        polys: document.querySelectorAll("#stageSvg polygon").length,
        rows: document.querySelectorAll("#viewportList li").length,
        gone: document.querySelectorAll("#viewportList li.gone").length,
        webgl: document.querySelector("#stageSvg")?.getAttribute("data-webgl"),
        bench: document.querySelector("#bench")?.textContent || ""
      })`,
      returnByValue: true,
    });
    return result.result.value;
  }

  async function openShot(shot) {
    await send("Page.navigate", { url: pageUrl(shot) });
    let state = null;
    for (let i = 0; i < 50; i++) {
      state = await readState();
      if (state && state.ready === "1") return state;
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    throw new Error(`not ready: ${JSON.stringify(state)}`);
  }

  for (const shot of [...STILL_SHOTS, "bench"]) {
    const state = await openShot(shot);
    const spec = shotState(shot);
    const want = markerCount(spec.fighters);
    if (state.webgl !== "off" || Number(state.markers) !== want || state.tell !== spec.tell || state.triangles !== want) {
      failures.push(`${shot} state ${JSON.stringify(state)} want markers ${want} tell ${spec.tell}`);
    }
    if (shot === "bench") {
      fs.writeFileSync(path.join(here, "perf-browser.json"), `${JSON.stringify(JSON.parse(state.bench), null, 2)}\n`);
      const parsed = JSON.parse(state.bench);
      console.log(`browser project ${parsed.project.median.toFixed(2)} ms · 10-marker bake ${parsed.bake10.median.toFixed(2)} ms · 1000-marker bake ${parsed.bake1000.median.toFixed(2)} ms placed ${parsed.placed1000}`);
      continue;
    }
    if (shot === "viewport-gone" && state.gone !== 10) failures.push(`${shot} gone rows ${state.gone}`);
    if (shot.startsWith("land-") && state.planet !== spec.planet) failures.push(`${shot} planet ${state.planet}`);
    if (shot.startsWith("mine-") && state.mine !== spec.mineKind) failures.push(`${shot} mine ${state.mine}`);
    const png = await send("Page.captureScreenshot", { format: "png" });
    const dest = path.join(stillsDir, `${shot}.png`);
    fs.writeFileSync(dest, Buffer.from(png.data, "base64"));
    const size = fs.statSync(dest).size;
    if (size < 8000) failures.push(`${shot} png ${size} bytes`);
    console.log(`still ${shot} markers=${state.markers} placed=${state.placed} tell=${state.tell} polys=${state.polys} ${size} bytes`);
  }
} catch (err) {
  failures.push(String(err && err.stack ? err.stack : err));
} finally {
  if (ws) ws.close();
  chrome.kill("SIGKILL");
  await new Promise((resolve) => setTimeout(resolve, 200));
  try {
    fs.rmSync(profile, { recursive: true, force: true, maxRetries: 3, retryDelay: 50 });
  } catch (err) {
    console.log(`left chrome profile in place: ${err.message}`);
  }
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}
