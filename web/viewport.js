/* TW2K viewport (video cockpit V1): a window out of your ship on the default /bot.
 *
 * Ambient = procedural canvas starfield (no assets, no generated video), seeded
 * by the seat's own sector id; a per-hull cockpit frame is drawn by CSS on top.
 * Decoration only: it reads the seat's own Observation (sector, port, ship
 * class), never blocks a turn, never takes focus, and never runs in mode=cu.
 * Modes: live (animated) / stills (one static frame) / off; reduced motion
 * forces stills. Event clips arrive in V2 - Skip already returns to ambient.
 */
(function () {
  "use strict";
  const params = new URLSearchParams(location.search);
  const CU = params.get("mode") === "cu";
  const KEY = "tw2k.viewport";
  const MODES = ["live", "stills", "off"];
  // 10 ship classes -> 4 frame families (phase plan section 4.2).
  const HULL = {
    merchant_cruiser: "hauler", merchant_freighter: "hauler", cargotran: "hauler", colonial_transport: "hauler",
    scout_marauder: "light", missile_frigate: "light", battleship: "heavy", havoc_gunstar: "heavy",
    corporate_flagship: "capital", imperial_starship: "capital",
  };
  const reduce = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : { matches: false };
  const st = { mode: "live", sector: null, fed: false, port: null, hull: "hauler", animating: false, raf: 0,
    stars: [], seed: 1, onScreen: true, frames: 0, ambientCaption: "Deep space", event: null };

  const noop = { update() {}, skip() {}, setMode() {}, state: () => ({ mode: "off", animating: false, cu: true }) };
  if (CU) { window.TW2KViewport = noop; return; }

  const $ = (id) => document.getElementById(id);
  const root = $("viewport");
  if (!root) { window.TW2KViewport = noop; return; }
  const screen = $("vpScreen");
  const canvas = $("vpStars");
  const caption = $("vpCaption");
  const ctx = canvas.getContext("2d");

  function hash(n) { let x = (Number(n) || 1) * 2654435761; x ^= x >>> 16; return (x >>> 0) || 1; }
  function rng(seed) { let s = seed >>> 0 || 1; return () => (s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296; }

  function initialMode() {
    const q = params.get("viewport");
    const saved = localStorage.getItem(KEY);
    let m = MODES.includes(q) ? q : MODES.includes(saved) ? saved : "live";
    if (reduce.matches && m === "live") m = "stills";  // reduced motion: poster frames only
    return m;
  }

  function size() {
    const r = screen.getBoundingClientRect();
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const w = Math.max(1, Math.round(r.width * dpr)), h = Math.max(1, Math.round(r.height * dpr));
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; reseed(); }
  }

  function reseed() {
    const r = rng(st.seed);
    st.stars = Array.from({ length: 170 }, () => ({ x: r(), y: r(), z: 0.15 + r() * 0.85, tw: r() * 6.283 }));
  }

  function draw(t) {
    const w = canvas.width, h = canvas.height;
    const hue = st.fed ? 215 : (st.seed % 360);
    const g = ctx.createRadialGradient(w * 0.7, h * 0.35, 0, w * 0.5, h * 0.5, Math.max(w, h) * 0.8);
    g.addColorStop(0, `hsl(${hue} 45% 14%)`);
    g.addColorStop(1, "#02040a");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);
    const drift = t * 0.000012;
    for (const s of st.stars) {
      const x = (((s.x - drift * s.z) % 1) + 1) % 1 * w;
      const y = s.y * h;
      const a = 0.35 + 0.65 * s.z * (0.8 + 0.2 * Math.sin(t * 0.002 + s.tw));
      ctx.fillStyle = `rgba(230,238,255,${a.toFixed(3)})`;
      const r = Math.max(0.6, s.z * 1.8) * (w / 900);
      ctx.fillRect(x, y, r, r);
    }
    if (st.port) {  // a distant station when this sector has a port
      const cx = w * 0.72, cy = h * 0.42, rr = h * 0.07;
      ctx.strokeStyle = "rgba(245,165,36,0.85)";
      ctx.lineWidth = Math.max(1, h * 0.006);
      ctx.beginPath(); ctx.ellipse(cx, cy, rr * 1.8, rr * 0.6, -0.2, 0, Math.PI * 2); ctx.stroke();
      ctx.fillStyle = "rgba(110,231,255,0.9)";
      ctx.beginPath(); ctx.arc(cx, cy, rr * 0.45, 0, Math.PI * 2); ctx.fill();
    }
  }

  function loop(ts) {
    st.frames += 1;
    if (st.frames % 2 === 0) draw(ts);  // ~30 fps is plenty for a slow drift
    st.raf = requestAnimationFrame(loop);
  }
  function stop() { if (st.raf) cancelAnimationFrame(st.raf); st.raf = 0; st.animating = false; }
  function apply() {
    root.setAttribute("data-mode", st.mode);
    root.setAttribute("data-hull", st.hull);
    screen.hidden = st.mode === "off";
    document.querySelectorAll("#viewport [data-vp-mode]").forEach((b) => b.setAttribute("aria-pressed", b.getAttribute("data-vp-mode") === st.mode ? "true" : "false"));
    if (st.mode === "off") { stop(); return; }
    size();
    const live = st.mode === "live" && !reduce.matches && !document.hidden && st.onScreen;
    if (!live) { stop(); draw(0); return; }
    if (!st.animating) { st.animating = true; st.raf = requestAnimationFrame(loop); }
  }

  function setCaption() {
    caption.textContent = st.event ? st.event.caption : st.ambientCaption;
  }

  function update(obs) {
    if (!obs) return;
    const s = obs.sector || {};
    const port = s.port ? (s.port.code || s.port.name || "port") : null;
    st.hull = HULL[(obs.ship || {}).class] || "hauler";
    if (s.id !== st.sector) {
      st.sector = s.id; st.fed = !!s.is_fedspace; st.port = port;
      st.seed = hash(s.id);
      reseed();
    }
    st.ambientCaption = `Sector ${s.id ?? "-"}${st.fed ? " · FedSpace" : ""}${port ? ` · port ${port}` : " · deep space"}`;
    setCaption();
    apply();
  }

  function skip() {
    st.event = null;  // V2: stops the event clip; V1 has only ambient
    setCaption();
  }

  function setMode(m) {
    if (!MODES.includes(m)) return;
    st.mode = reduce.matches && m === "live" ? "stills" : m;
    localStorage.setItem(KEY, m);
    apply();
  }

  $("vpSkip").addEventListener("click", (ev) => { skip(); ev.currentTarget.blur(); });
  screen.addEventListener("click", skip);
  document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") skip(); });
  document.querySelectorAll("#viewport [data-vp-mode]").forEach((b) => b.addEventListener("click", (ev) => {
    setMode(b.getAttribute("data-vp-mode")); ev.currentTarget.blur();
  }));
  document.addEventListener("visibilitychange", apply);
  if (reduce.addEventListener) reduce.addEventListener("change", () => setMode(st.mode));
  if (window.IntersectionObserver) {
    new IntersectionObserver((entries) => { st.onScreen = entries.some((e) => e.isIntersecting); apply(); }).observe(root);
  }
  if (window.ResizeObserver) new ResizeObserver(() => { if (st.mode !== "off") { size(); if (!st.animating) draw(0); } }).observe(screen);

  st.mode = initialMode();
  reseed();
  apply();
  window.TW2KViewport = {
    update, skip, setMode,
    state: () => ({ mode: st.mode, animating: st.animating, sector: st.sector, hull: st.hull, caption: caption.textContent,
      reducedMotion: !!reduce.matches, cu: false }),
  };
})();
