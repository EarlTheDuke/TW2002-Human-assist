/* TW2K media player — V2 viewport clips + the v1 still HUD.
 *
 * Three pieces: resolver (web/media-resolver.js), renderer (viewport poster /
 * two video layers, or the CU still HUD), and settings (live/stills/off live
 * on the viewport; this file only honours reduced-motion and mode=cu).
 * window.TW2KMedia keeps onEvents, onEvent, hide, playEntry.
 *
 * Viewport mode (TW2KViewport.state().mode), not this file's own setting:
 *   live   — poster push-in, or a video when the variant has one
 *   stills — poster frame only: no vp-push / tint, never a video src
 *   off    — no viewport clip and no caption change. A resolved clip is not
 *            copied onto the v1 HUD either. Events that resolve to no clip
 *            still use the v1 HUD, except in Off (and CU Off), so the default
 *            cockpit's dismiss button stays available in Live.
 *   cu     — no viewport (it is hidden). The still goes in the CU slot.
 * The first events batch after connect is history: lastSeq and visit/dock
 * advance, and nothing plays. Later batches can play.
 */
(function () {
  "use strict";
  const BASE = "/static/media/";
  const R = window.TW2KMediaResolver;
  const CU = new URLSearchParams(location.search).get("mode") === "cu";
  const KIND_GROUP = {
    warp: "move", warp_blocked: "move", autopilot: "move", scan: "move", probe: "move", ferrengi_move: "move",
    trade: "trade", trade_failed: "trade", buy_ship: "trade", buy_equip: "trade", planet_tax_payout: "trade",
    combat: "combat", ship_destroyed: "combat", player_eliminated: "combat", mine_detonated: "combat", photon_fired: "combat",
    photon_hit: "combat", atomic_detonation: "combat", port_destroyed: "combat", deploy_fighters: "combat", deploy_mines: "combat",
    ferrengi_attack: "combat", ferrengi_spawn: "combat", fed_response: "combat",
    hail: "comms", broadcast: "comms", corp_memo: "comms", corp_create: "comms", corp_invite: "comms", corp_join: "comms",
    corp_leave: "comms", corp_deposit: "comms", corp_withdraw: "comms", alliance_proposed: "comms", alliance_formed: "comms", alliance_broken: "comms",
    land_planet: "planet", liftoff: "planet", genesis_deployed: "planet", assign_colonists: "planet", planet_cargo_transfer: "planet",
    build_citadel: "planet", citadel_complete: "planet", planet_claimed: "planet", planet_orphaned: "planet",
  };
  const reduce = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : { matches: false };
  const state = {
    manifest: null, lastSeq: 0, hideTimer: null, reduced: false, obs: null,
    visit_sector: null, docked_in_visit: false, session: null, playing: null,
  };

  function ensureHud() {
    let root = document.getElementById("mediaHud");
    if (root) return root;
    root = document.createElement("div");
    root.id = "mediaHud";
    root.className = "media-hud";
    root.setAttribute("data-testid", "media-hud");
    root.hidden = true;
    root.innerHTML = [
      '<div class="media-hud-inner">',
      '  <img id="mediaHudStill" alt="" />',
      CU ? "" : '  <video id="mediaHudVideo" muted playsinline aria-hidden="true"></video>',
      '  <div id="mediaHudCaption" class="media-hud-caption"></div>',
      '  <button type="button" id="mediaHudDismiss" class="media-hud-dismiss" data-testid="media-hud-dismiss" aria-label="Dismiss">×</button>',
      "</div>",
    ].join("");
    document.body.appendChild(root);
    document.getElementById("mediaHudDismiss").addEventListener("click", hide);
    root.addEventListener("click", (ev) => { if (ev.target === root) hide(); });
    return root;
  }

  function viewportMode() {
    const vp = window.TW2KViewport;
    if (!vp || typeof vp.state !== "function") return CU ? "cu" : "live";
    const st = vp.state() || {};
    if (st.cu) return "cu";
    return st.mode || "live";
  }

  // CU keeps the renderer on the HUD ("cu"). The URL picks stills (default),
  // off (slot stays, nothing plays), or live (demo only; still a poster here).
  function cuSetting() {
    if (!CU) return "";
    const vp = window.TW2KViewport;
    const st = vp && typeof vp.state === "function" ? (vp.state() || {}) : {};
    return st.mode || "stills";
  }

  function clearTimer() {
    if (state.hideTimer) clearTimeout(state.hideTimer);
    state.hideTimer = null;
  }

  function clearVisuals() {
    const root = document.getElementById("mediaHud");
    if (root) {
      root.hidden = true;
      root.classList.remove("show");
      const v = document.getElementById("mediaHudVideo");
      if (v) { try { v.pause(); v.removeAttribute("src"); v.load(); } catch (_) {} }
    }
    const clip = document.getElementById("vpClip");
    if (clip) {
      clip.hidden = true;
      clip.classList.remove("is-still", "is-live");
      clip.querySelectorAll("video").forEach((v) => { try { v.pause(); v.removeAttribute("src"); } catch (_) {} });
    }
    clearTimer();
    state.playing = null;
    if (window.TW2KViewport && typeof window.TW2KViewport.setEventCaption === "function") window.TW2KViewport.setEventCaption(null);
  }

  // User dismiss (Skip, Esc, HUD ×). Drops the playing clip and anything waiting
  // so the next poll cannot redraw it.
  function hide() {
    if (state.playing) bump("skips");
    if (state.session && typeof state.session.stop === "function") state.session.stop();
    clearVisuals();
  }

  function resolveKind(kind) {
    const m = state.manifest;
    if (!m) return null;
    return (m.kinds && m.kinds[kind]) || (m.groups && m.groups[KIND_GROUP[kind] || "system"]) || null;
  }

  function playEntry(entry, kind) {
    if (!entry) return;
    state.reduced = !!reduce.matches;
    const root = ensureHud();
    const img = document.getElementById("mediaHudStill");
    const vid = document.getElementById("mediaHudVideo");
    const cap = document.getElementById("mediaHudCaption");
    const duration = (state.manifest && state.manifest.defaults && state.manifest.defaults.duration_ms) || 2400;
    cap.textContent = entry.caption || kind || "";
    img.hidden = true;
    if (vid) vid.hidden = true;
    if (!state.reduced && entry.clip && vid) {
      vid.muted = true;
      vid.src = BASE + entry.clip;
      vid.hidden = false;
      vid.play().catch(() => {});
    } else if (entry.still) {
      img.src = BASE + entry.still;
      img.hidden = false;
      img.onerror = () => { hide(); };
    } else {
      return;
    }
    root.hidden = false;
    requestAnimationFrame(() => root.classList.add("show"));
    clearTimer();
    state.hideTimer = setTimeout(onClipEnded, duration);
  }

  function clipMeta(key) {
    const c = state.manifest && state.manifest.clips && state.manifest.clips[key];
    if (!c) return null;
    const variant = (c.variants && c.variants[0]) || {};
    return {
      key, caption: c.caption || key, still: variant.poster || c.fallback_still || "",
      webm: variant.webm || "", mp4: variant.mp4 || "", duration: variant.duration_ms || (state.manifest.defaults && state.manifest.defaults.duration_ms) || 2400,
    };
  }

  function ensureClipLayer() {
    let layer = document.getElementById("vpClip");
    if (layer) return layer;
    const screen = document.getElementById("vpScreen");
    if (!screen) return null;
    layer = document.createElement("div");
    layer.id = "vpClip";
    layer.className = "vp-clip";
    layer.setAttribute("data-testid", "viewport-clip");
    layer.hidden = true;
    const img = document.createElement("img");
    img.alt = "";
    img.setAttribute("data-testid", "viewport-clip-still");
    layer.appendChild(img);
    // Two video layers exist for a Live clip that has webm/mp4. Stills, Off, and
    // reduced motion never create them, so a poster cannot pick up a video src.
    if (!reduce.matches && viewportMode() === "live") {
      for (const name of ["a", "b"]) {
        const v = document.createElement("video");
        v.className = name === "a" ? "vp-video vp-video-a" : "vp-video vp-video-b";
        v.muted = true;
        v.playsInline = true;
        v.setAttribute("aria-hidden", "true");
        v.hidden = true;
        layer.appendChild(v);
      }
    }
    screen.appendChild(layer);
    return layer;
  }

  function sectorCaption(meta, item) {
    const sector = item && item.sector_id != null ? String(item.sector_id) : "";
    return (meta.caption || "").replace("{sector_id}", sector);
  }

  function hideHudOnly() {
    const root = document.getElementById("mediaHud");
    if (!root) return;
    root.hidden = true;
    root.classList.remove("show");
    const v = document.getElementById("mediaHudVideo");
    if (v) { try { v.pause(); v.removeAttribute("src"); v.load(); } catch (_) {} }
  }

  function showViewport(meta, item) {
    const mode = viewportMode();
    if (mode === "off" || mode === "cu") return false;
    hideHudOnly();
    const layer = ensureClipLayer();
    if (!layer || !meta.still) return false;
    const stills = mode === "stills" || reduce.matches;
    const img = layer.querySelector("img");
    img.src = BASE + meta.still;
    layer.hidden = false;
    layer.classList.toggle("is-still", !stills && !meta.webm && !meta.mp4);
    layer.classList.toggle("is-live", !stills && !!(meta.webm || meta.mp4));
    if (window.TW2KViewport && typeof window.TW2KViewport.setEventCaption === "function") {
      window.TW2KViewport.setEventCaption(sectorCaption(meta, item));
    }
    const videos = layer.querySelectorAll("video");
    videos.forEach((v) => { try { v.pause(); v.removeAttribute("src"); } catch (_) {} v.hidden = true; });
    if (!stills && (meta.webm || meta.mp4) && videos.length) {
      const idle = videos[0];
      idle.hidden = false;
      idle.src = BASE + (meta.webm || meta.mp4);
      idle.play().catch(() => {});
    }
    arm(meta.duration);
    return true;
  }

  function onClipEnded() {
    clearTimer();
    const before = state.session && state.session.state ? state.session.state().staleDrops || 0 : 0;
    const next = state.session && typeof state.session.finish === "function" ? state.session.finish(Date.now()) : null;
    const after = state.session && state.session.state ? state.session.state().staleDrops || 0 : 0;
    if (after > before) bump("stale-drops", after - before);
    if (next) playResolved(next);
    else clearVisuals();
  }

  function arm(ms) {
    clearTimer();
    const cap = Math.min(ms || 2400, 5000);
    state.hideTimer = setTimeout(onClipEnded, cap);
  }

  function playResolved(item) {
    const key = item && item.clip_key ? item.clip_key : item;
    const row = item && item.clip_key ? item : { sector_id: null };
    const meta = clipMeta(key);
    if (!meta) return;
    if (viewportMode() === "off" || cuSetting() === "off") {
      if (state.session && typeof state.session.stop === "function") state.session.stop();
      clearVisuals();
      return;
    }
    state.playing = key;
    if (showViewport(meta, row)) {
      bump("plays");
      if (viewportMode() === "live" && !meta.webm && !meta.mp4) bump("poster-fallbacks");
      return;
    }
    playEntry({ still: meta.still, caption: sectorCaption(meta, row) }, key);
    bump("plays");
  }

  function onMode(mode) {
    if (mode === "off") hide();
    else if (mode === "stills") {
      const layer = document.getElementById("vpClip");
      if (!layer) return;
      layer.classList.remove("is-still", "is-live");
      layer.querySelectorAll("video").forEach((v) => { try { v.pause(); v.removeAttribute("src"); } catch (_) {} v.hidden = true; });
    }
  }

  function onEvents(list, obs, opts) {
    opts = opts || {};
    if (!Array.isArray(list) || !list.length) return;
    if (obs) state.obs = obs;
    const newest = list[list.length - 1];
    if (!newest || typeof newest.seq !== "number") return;
    const fresh = list.filter((ev) => ev && typeof ev.seq === "number" && ev.seq > state.lastSeq);
    if (!fresh.length) return;
    const v2 = state.manifest && state.manifest.version >= 2 && R;
    // No manifest yet: keep history and live events in one queue (history first)
    // so a live clip cannot play ahead of the backlog. A failed fetch clears it.
    if (!state.manifest) {
      if (state.manifestFailed) return;
      if (!state.pendingEvents) state.pendingEvents = [];
      for (const ev of fresh) {
        state.pendingEvents.push({ ev, history: !!opts.history });
        if (state.pendingEvents.length > 400) state.pendingEvents.shift();
      }
      if (opts.history) {
        state.lastSeq = Math.max(state.lastSeq, newest.seq);
        if (state.visit_sector == null && state.obs && state.obs.sector) state.visit_sector = state.obs.sector.id;
        if (R) R.resolve(fresh, state.obs || { self_id: null, sector: {} }, state, null);
      }
      return;
    }
    // History is the batch already in the log at connect. Advance the cursor
    // and visit/dock memory. Do not start a clip or the v1 HUD.
    if (opts.history) {
      state.lastSeq = Math.max(state.lastSeq, newest.seq);
      if (state.visit_sector == null && state.obs && state.obs.sector) state.visit_sector = state.obs.sector.id;
      if (R) {
        const view = state.obs || { self_id: null, sector: {} };
        R.resolve(fresh, view, state, state.manifest);
        if (!state.session) state.session = R.createSession(state.manifest);
      }
      return;
    }
    if (!v2) { onEvent(newest); return; }
    state.lastSeq = Math.max(state.lastSeq, newest.seq);
    if (state.visit_sector == null && state.obs && state.obs.sector) state.visit_sector = state.obs.sector.id;
    if (!state.session) state.session = R.createSession(state.manifest);
    const view = state.obs || { self_id: null, sector: {} };
    const items = R.resolve(fresh, view, state, state.manifest);
    const hidden = typeof document !== "undefined" && document.hidden;
    const selfSeqs = fresh.filter((ev) => ev.actor_id === view.self_id && ev.kind !== "agent_thought" && ev.kind !== "llm_usage").map((ev) => ev.seq);
    const postedSeq = selfSeqs.length ? Math.max(...selfSeqs) : undefined;
    const step = state.session.consider(items, Date.now(), {
      hidden, maxSeq: state.lastSeq, postedSeq, recordCooldown: viewportMode() !== "off" && cuSetting() !== "off",
    });
    if (step.staleDropped) bump("stale-drops", step.staleDropped);
    if (step.preempted) bump("preemptions");
    if (hidden) return;
    if (step.started && step.item) { playResolved(step.item); return; }
    // No clip started. Off stays quiet. CU still uses the slot. The default
    // layout plays the still inside the viewport so it cannot cover the ship.
    if (!step.playing && viewportMode() !== "off" && cuSetting() !== "off") {
      const show = [...fresh].reverse().find((ev) => ev.kind !== "agent_thought" && ev.kind !== "llm_usage");
      if (show) showFallback(resolveKind(show.kind), show.kind);
    }
  }

  function showFallback(entry, kind) {
    if (viewportMode() === "cu") { playEntry(entry, kind); return; }
    if (!entry || !entry.still) return;
    hideHudOnly();
    const layer = ensureClipLayer();
    if (!layer) return;
    const stills = viewportMode() === "stills" || reduce.matches;
    const img = layer.querySelector("img");
    img.src = BASE + entry.still;
    layer.hidden = false;
    layer.classList.toggle("is-still", !stills);
    layer.classList.remove("is-live");
    if (window.TW2KViewport && typeof window.TW2KViewport.setEventCaption === "function") {
      window.TW2KViewport.setEventCaption(entry.caption || kind || "");
    }
    arm((state.manifest && state.manifest.defaults && state.manifest.defaults.duration_ms) || 2400);
  }

  function onEvent(ev) {
    if (!ev || typeof ev.seq !== "number" || ev.seq <= state.lastSeq) return;
    if (ev.kind === "agent_thought" || ev.kind === "llm_usage") { state.lastSeq = ev.seq; return; }
    if (state.manifest && state.manifest.version >= 2 && R) { onEvents([ev], state.obs); return; }
    state.lastSeq = ev.seq;
    playEntry(resolveKind(ev.kind), ev.kind);
  }

  async function loadManifest() {
    try {
      const r = await fetch(BASE + "manifest.json", { cache: "no-store" });
      if (!r.ok) return;
      state.manifest = await r.json();
      state.ready = true;
      const queued = state.pendingEvents || [];
      state.pendingEvents = null;
      if (R && queued.length) {
        const hist = queued.filter((row) => row.history).map((row) => row.ev);
        const live = queued.filter((row) => !row.history).map((row) => row.ev);
        if (hist.length) R.resolve(hist, state.obs || { self_id: null, sector: {} }, state, state.manifest);
        if (!state.session) state.session = R.createSession(state.manifest);
        if (live.length) onEvents(live, state.obs);
      }
    } catch (_) {
      state.manifestFailed = true;
      state.pendingEvents = null;
    }
  }

  if (CU) document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") hide(); });

  const COUNTER_KEY = "tw2k.media.counters";
  const COUNTER_NAMES = ["plays", "skips", "preemptions", "stale-drops", "poster-fallbacks"];
  const PRELOAD_CAP = 12 * 1024 * 1024;
  const FIRST_LOAD_CAP = 150 * 1024;
  const preload = { skipped: "", bytes: 0, beforeInteractive: 0, done: false, urls: 0 };

  function readCounters() {
    try { return JSON.parse(sessionStorage.getItem(COUNTER_KEY)) || {}; } catch (_) { return {}; }
  }
  function renderCounters() {
    const el = document.getElementById("mediaCounters");
    if (!el) return;
    const c = readCounters();
    el.textContent = COUNTER_NAMES.map((n) => `${n} ${c[n] || 0}`).join("  ");
  }
  function bump(name, n) {
    const c = readCounters();
    c[name] = (c[name] || 0) + (n || 1);
    try { sessionStorage.setItem(COUNTER_KEY, JSON.stringify(c)); } catch (_) {}
    renderCounters();
  }

  function posterUrls() {
    const clips = (state.manifest && state.manifest.clips) || {};
    const seen = new Set();
    const out = [];
    for (const clip of Object.values(clips)) {
      if (typeof clip.priority !== "number" || clip.priority > 2) continue;
      const poster = clip.fallback_still || (clip.variants && clip.variants[0] && clip.variants[0].poster);
      if (!poster || seen.has(poster)) continue;
      seen.add(poster);
      out.push(BASE + poster);
    }
    return out;
  }
  function preloadSkipReason() {
    if (CU || viewportMode() === "cu") return "cu";
    if (reduce.matches) return "reduce";
    const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if (conn && conn.saveData) return "saveData";
    return "";
  }
  async function preloadPosters() {
    const reason = preloadSkipReason();
    if (reason) { preload.skipped = reason; preload.done = true; renderCounters(); return; }
    const urls = posterUrls();
    preload.urls = urls.length;
    for (const url of urls) {
      if (preload.bytes >= PRELOAD_CAP) break;
      if (document.readyState === "loading" && preload.beforeInteractive >= FIRST_LOAD_CAP) break;
      try {
        const r = await fetch(url);
        if (!r.ok) continue;
        const blob = await r.blob();
        if (preload.bytes + blob.size > PRELOAD_CAP) break;
        if (document.readyState === "loading" && preload.beforeInteractive + blob.size > FIRST_LOAD_CAP) break;
        preload.bytes += blob.size;
        if (document.readyState === "loading") preload.beforeInteractive += blob.size;
        const img = new Image();
        img.src = URL.createObjectURL(blob);
      } catch (_) {}
    }
    preload.done = true;
  }
  function schedulePreload() {
    const run = () => { void preloadPosters(); };
    const kick = () => {
      if (window.requestIdleCallback) requestIdleCallback(run, { timeout: 1500 });
      else setTimeout(run, 50);
    };
    if (document.readyState === "complete") kick();
    else window.addEventListener("load", kick, { once: true });
  }

  window.TW2KMedia = {
    loadManifest, onEvent, onEvents, playEntry, hide, ensureHud, onMode,
    skipClip: hide,
    ready: () => !!state.ready,
    preloadState: () => ({ skipped: preload.skipped, bytes: preload.bytes, beforeInteractive: preload.beforeInteractive, done: preload.done, urls: preload.urls }),
    benchSwap: (n) => {
      if (!R || !state.manifest) return { p95: 999, max: 999, n: 0 };
      const samples = [];
      const obs = state.obs || { self_id: "P2", sector: { id: 19 } };
      const batch = [];
      for (let i = 0; i < 6; i++) batch.push({ seq: 1000 + i, kind: "warp", actor_id: obs.self_id || "P2", sector_id: 19, summary: "warp", facts: { from: 18, to: 19 } });
      const cap = document.getElementById("vpCaption") || document.getElementById("mediaHudCaption");
      const img = document.querySelector("#vpClip img") || document.getElementById("mediaHudStill");
      const prevCap = cap ? cap.textContent : null;
      const prevSwap = img ? img.getAttribute("data-swap") : null;
      const count = n || 40;
      for (let i = 0; i < count; i++) {
        const t0 = performance.now();
        const items = R.resolve(batch, obs, { visit_sector: 19, docked_in_visit: false }, state.manifest);
        if (cap && items[0]) cap.textContent = items[0].clip_key;
        if (img && items[0]) img.setAttribute("data-swap", items[0].clip_key);
        samples.push(performance.now() - t0);
      }
      if (cap && prevCap != null) cap.textContent = prevCap;
      if (img) {
        if (prevSwap == null) img.removeAttribute("data-swap");
        else img.setAttribute("data-swap", prevSwap);
      }
      samples.sort((a, b) => a - b);
      const idx = Math.min(samples.length - 1, Math.max(0, Math.ceil(samples.length * 0.95) - 1));
      return { p95: samples[idx], max: samples[samples.length - 1], n: samples.length };
    },
    _prime: (opts) => {
      opts = opts || {};
      if (opts.lastSeq != null) state.lastSeq = opts.lastSeq;
      if (opts.visit_sector != null) state.visit_sector = opts.visit_sector;
      if (opts.docked_in_visit != null) state.docked_in_visit = !!opts.docked_in_visit;
      state.playing = null;
      state.session = state.manifest && R ? R.createSession(state.manifest) : null;
    },
    _state: () => ({
      lastSeq: state.lastSeq, playing: state.playing, visit_sector: state.visit_sector,
      playedKeys: state.session && state.session.state ? state.session.state().playedKeys || [] : [],
      pending: state.pendingEvents ? state.pendingEvents.length : 0,
    }),
  };
  renderCounters();
  loadManifest().then(() => schedulePreload());
})();
