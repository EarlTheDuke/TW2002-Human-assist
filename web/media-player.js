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
    visit_sector: null, docked_in_visit: false, session: null, playing: null, clipToken: 0,
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

  function stopVideo(v) {
    state.clipToken += 1;
    v.onerror = null;
    delete v.dataset.fell;
    v.querySelectorAll("source").forEach((s) => { s.onerror = null; });
    try { v.pause(); } catch (_) {}
    v.removeAttribute("src");
    v.querySelectorAll("source").forEach((s) => s.remove());
    try { v.load(); } catch (_) {}
    v.hidden = true;
  }

  function clearVisuals() {
    const root = document.getElementById("mediaHud");
    if (root) {
      root.hidden = true;
      root.classList.remove("show");
      const v = document.getElementById("mediaHudVideo");
      if (v) stopVideo(v);
    }
    const clip = document.getElementById("vpClip");
    if (clip) {
      clip.hidden = true;
      clip.classList.remove("is-still", "is-live");
      clip.querySelectorAll("video").forEach(stopVideo);
    }
    const vp = document.getElementById("viewport");
    if (vp) vp.classList.remove("is-baked-frame");
    clearTimer();
    state.playing = null;
    if (window.TW2KViewport && typeof window.TW2KViewport.setEventCaption === "function") window.TW2KViewport.setEventCaption(null);
  }

  // User dismiss from the HUD (×, a failed still). Drops the playing clip and
  // anything waiting so the next poll cannot redraw it.
  function hide() {
    if (state.playing) bump("skips");
    if (state.session && typeof state.session.stop === "function") state.session.stop();
    clearVisuals();
  }
  // Skip (button, click, Esc). Death ends only the death clip; the chained
  // escape pod then plays. A later Skip ends the pod. Any other clip clears
  // the queue, which is what Skip did before.
  function skipClip() {
    const waiting = state.session && typeof state.session.state === "function" ? state.session.state().waiting : null;
    if (state.playing === "self.ship_destroyed" && waiting === "self.escape_pod") {
      bump("skips");
      onClipEnded();
      return;
    }
    hide();
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

  function approvedBy(variant) {
    const who = variant && variant.provenance && variant.provenance.approved_by;
    return typeof who === "string" && who.trim() ? who : "";
  }

  // An approved take plays. Otherwise the first variant, which is the stand-in.
  function pickVariant(variants) {
    const list = variants || [];
    for (let i = 0; i < list.length; i++) if (approvedBy(list[i])) return list[i];
    return list[0] || {};
  }

  function clipMeta(key) {
    const c = state.manifest && state.manifest.clips && state.manifest.clips[key];
    if (!c) return null;
    const variant = pickVariant(c.variants);
    const fallback = (state.manifest.defaults && state.manifest.defaults.duration_ms) || 2400;
    return {
      key, caption: c.caption || key,
      still: c.fallback_still || variant.poster || "",
      poster: variant.poster || c.fallback_still || "",
      webm: variant.webm || "", mp4: variant.mp4 || "",
      duration: variant.duration_ms || fallback,
      bakedFrame: !!variant.baked_frame,
      overlay: !!c.overlay,
    };
  }

  function addLiveVideos(layer) {
    // Stills, Off, and reduced motion never create these, so a poster cannot
    // pick up a video src. Switching Stills -> Live adds them on the next clip.
    if (reduce.matches || viewportMode() !== "live" || layer.querySelector("video")) return;
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

  function ensureClipLayer() {
    let layer = document.getElementById("vpClip");
    if (layer) { addLiveVideos(layer); return layer; }
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
    addLiveVideos(layer);
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
    const vp = document.getElementById("viewport");
    const showBaked = !stills && !!(meta.bakedFrame && (meta.webm || meta.mp4));
    if (vp) vp.classList.toggle("is-baked-frame", showBaked);
    const videos = layer.querySelectorAll("video");
    videos.forEach(stopVideo);
    if (!stills && (meta.webm || meta.mp4) && videos.length) {
      const idle = videos[0];
      const token = ++state.clipToken;
      delete idle.dataset.fell;
      idle.hidden = false;
      const sources = [];
      if (meta.webm) {
        const s = document.createElement("source");
        s.src = BASE + meta.webm;
        s.type = "video/webm";
        idle.appendChild(s);
        sources.push(s);
      }
      if (meta.mp4) {
        const s = document.createElement("source");
        s.src = BASE + meta.mp4;
        s.type = "video/mp4";
        idle.appendChild(s);
        sources.push(s);
      }
      const fail = () => {
        if (token !== state.clipToken || idle.dataset.fell) return;
        idle.dataset.fell = "1";
        idle.hidden = true;
        bump("poster-fallbacks");
      };
      // A <source> error does not fire on the video element. The last source
      // failing means WebM and MP4 are both gone, so the still shows at once.
      if (sources.length) sources[sources.length - 1].onerror = fail;
      idle.onerror = fail;
      try { idle.load(); } catch (_) {}
      idle.play().catch((err) => {
        if (token !== state.clipToken) return;
        if (err && err.name === "AbortError") return;
        if (idle.error || idle.networkState === 3) fail();
      });
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
    if (meta.overlay) {
      const layer = document.getElementById("vpClip");
      if (layer) layer.hidden = true;
      playEntry({ still: meta.still, caption: sectorCaption(meta, row) }, key);
      arm(meta.duration);
      bump("plays");
      return;
    }
    if (showViewport(meta, row)) {
      bump("plays");
      if (viewportMode() === "live" && !meta.webm && !meta.mp4) bump("stills");
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
      layer.querySelectorAll("video").forEach(stopVideo);
      const vp = document.getElementById("viewport");
      if (vp) vp.classList.remove("is-baked-frame");
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
      if (!r.ok) {
        state.manifestFailed = true;
        state.pendingEvents = null;
        return;
      }
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

  if (CU) document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") skipClip(); });

  const COUNTER_KEY = "tw2k.media.counters";
  const COUNTER_NAMES = ["plays", "skips", "preemptions", "stale-drops", "poster-fallbacks", "stills"];
  const MEMORY_CAP = 12 * 1024 * 1024;
  const PILOT_CAP = 3500000;
  const FIRST_LOAD_CAP = 150 * 1024;
  const preload = {
    skipped: "", bytes: 0, clipBytes: 0, beforeInteractive: 0,
    done: false, urls: 0, capped: false,
  };

  function memoryCap() {
    const n = Number(window.__TW2K_PRELOAD_CAP);
    return Number.isFinite(n) && n >= 0 ? n : MEMORY_CAP;
  }

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
      const variant = pickVariant(clip.variants);
      const poster = (variant.poster && String(variant.poster).endsWith(".webp")) ? variant.poster : "";
      if (!poster || seen.has(poster)) continue;
      seen.add(poster);
      out.push(BASE + poster);
    }
    return out;
  }
  // The take the player will actually play: approved webm, else the stand-in.
  function selectedClipUrls() {
    const clips = (state.manifest && state.manifest.clips) || {};
    const seen = new Set();
    const out = [];
    for (const clip of Object.values(clips)) {
      if (typeof clip.priority !== "number" || clip.priority > 2) continue;
      const path = pickVariant(clip.variants).webm || "";
      if (!path || seen.has(path)) continue;
      seen.add(path);
      out.push(BASE + path);
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
  function overCap(extra, clip) {
    const cap = memoryCap();
    if (preload.bytes >= cap || preload.bytes + extra > cap) return true;
    if (clip && (preload.clipBytes >= PILOT_CAP || preload.clipBytes + extra > PILOT_CAP)) return true;
    const early = document.readyState === "loading";
    if (early && (preload.beforeInteractive >= FIRST_LOAD_CAP || preload.beforeInteractive + extra > FIRST_LOAD_CAP)) return true;
    return false;
  }
  async function keepBlob(url, clip) {
    if (overCap(0, clip)) { preload.capped = true; return false; }
    try {
      const r = await fetch(url);
      if (!r.ok) return true;
      const len = Number(r.headers.get("content-length"));
      if (Number.isFinite(len) && len > 0 && overCap(len, clip)) {
        preload.capped = true;
        try { if (r.body && r.body.cancel) await r.body.cancel(); } catch (_) {}
        return false;
      }
      const blob = await r.blob();
      if (overCap(blob.size, clip)) { preload.capped = true; return false; }
      preload.bytes += blob.size;
      if (clip) preload.clipBytes += blob.size;
      if (document.readyState === "loading") preload.beforeInteractive += blob.size;
      return true;
    } catch (_) {
      return true;
    }
  }
  async function preloadPosters() {
    const reason = preloadSkipReason();
    if (reason) { preload.skipped = reason; preload.done = true; renderCounters(); return; }
    const mode = viewportMode();
    const posters = mode === "off" ? [] : posterUrls();
    const clips = mode === "live" ? selectedClipUrls() : [];
    if (!posters.length && !clips.length) {
      preload.skipped = mode === "off" ? "off" : "";
      preload.done = true;
      renderCounters();
      return;
    }
    preload.urls = posters.length + clips.length;
    for (const url of posters) {
      if (!(await keepBlob(url, false))) break;
    }
    if (!preload.capped) {
      for (const url of clips) {
        if (!(await keepBlob(url, true))) break;
      }
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
    skipClip,
    ready: () => !!state.ready,
    preloadState: () => ({
      skipped: preload.skipped, bytes: preload.bytes, clipBytes: preload.clipBytes,
      beforeInteractive: preload.beforeInteractive, done: preload.done, urls: preload.urls, capped: preload.capped,
    }),
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
      waiting: state.session && state.session.state ? state.session.state().waiting || null : null,
      pending: state.pendingEvents ? state.pendingEvents.length : 0,
    }),
  };
  renderCounters();
  loadManifest().then(() => schedulePreload());
})();
