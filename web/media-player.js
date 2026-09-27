/* TW2K media player — V2 viewport clips + the v1 still HUD.
 *
 * Three pieces: resolver (web/media-resolver.js), renderer (viewport poster /
 * two video layers, or the CU still HUD), and settings (live/stills/off live
 * on the viewport; this file only honours reduced-motion and mode=cu).
 * window.TW2KMedia keeps onEvents, onEvent, hide, playEntry.
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
      '  <video id="mediaHudVideo" muted playsinline aria-hidden="true"></video>',
      '  <div id="mediaHudCaption" class="media-hud-caption"></div>',
      '  <button type="button" id="mediaHudDismiss" class="media-hud-dismiss" data-testid="media-hud-dismiss" aria-label="Dismiss">×</button>',
      "</div>",
    ].join("");
    document.body.appendChild(root);
    document.getElementById("mediaHudDismiss").addEventListener("click", hide);
    root.addEventListener("click", (ev) => { if (ev.target === root) hide(); });
    return root;
  }

  function hide() {
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
    if (state.hideTimer) clearTimeout(state.hideTimer);
    state.hideTimer = null;
    state.playing = null;
    if (window.TW2KViewport && typeof window.TW2KViewport.setEventCaption === "function") window.TW2KViewport.setEventCaption(null);
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
    vid.hidden = true;
    if (!state.reduced && entry.clip) {
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
    if (state.hideTimer) clearTimeout(state.hideTimer);
    state.hideTimer = setTimeout(hide, duration);
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
    // Two video layers exist for real clips (crossfade). Placeholder stills never
    // attach a src, and reduced motion never creates the elements at all.
    if (!reduce.matches) {
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

  function showViewport(meta, item) {
    const layer = ensureClipLayer();
    if (!layer || !meta.still) return false;
    const img = layer.querySelector("img");
    img.src = BASE + meta.still;
    layer.hidden = false;
    layer.classList.toggle("is-still", !meta.webm && !meta.mp4);
    layer.classList.toggle("is-live", !!(meta.webm || meta.mp4));
    const caption = meta.caption.replace("{sector_id}", item.sector_id != null ? String(item.sector_id) : "");
    if (window.TW2KViewport && typeof window.TW2KViewport.setEventCaption === "function") window.TW2KViewport.setEventCaption(caption);
    const videos = layer.querySelectorAll("video");
    if ((meta.webm || meta.mp4) && videos.length && !reduce.matches) {
      const idle = [...videos].find((v) => v.hidden) || videos[0];
      videos.forEach((v) => { if (v !== idle) { try { v.pause(); } catch (_) {} v.hidden = true; } });
      idle.hidden = false;
      idle.src = BASE + (meta.webm || meta.mp4);
      idle.play().catch(() => {});
    }
    arm(meta.duration);
    return true;
  }

  function arm(ms) {
    if (state.hideTimer) clearTimeout(state.hideTimer);
    const cap = Math.min(ms || 2400, 5000);
    state.hideTimer = setTimeout(() => {
      const session = state.session;
      const next = session ? session.finish(Date.now()) : null;
      if (next) playResolved(next);
      else hide();
    }, cap);
  }

  function playResolved(key, item) {
    const meta = clipMeta(key);
    if (!meta) return;
    state.playing = key;
    const row = item || { sector_id: null };
    const useViewport = !CU && document.getElementById("vpScreen") && !(window.TW2KViewport && window.TW2KViewport.state && window.TW2KViewport.state().cu);
    if (useViewport && showViewport(meta, row)) return;
    playEntry({ still: meta.still, caption: meta.caption.replace("{sector_id}", row.sector_id != null ? String(row.sector_id) : "") }, key);
  }

  function onEvents(list, obs) {
    if (!Array.isArray(list) || !list.length) return;
    if (obs) state.obs = obs;
    const newest = list[list.length - 1];
    if (!newest || typeof newest.seq !== "number") return;
    const fresh = list.filter((ev) => ev && typeof ev.seq === "number" && ev.seq > state.lastSeq);
    if (!fresh.length) return;
    const v2 = state.manifest && state.manifest.version >= 2 && R;
    if (!v2) { onEvent(newest); return; }
    state.lastSeq = Math.max(state.lastSeq, newest.seq);
    if (state.visit_sector == null && state.obs && state.obs.sector) state.visit_sector = state.obs.sector.id;
    if (!state.session) state.session = R.createSession(state.manifest);
    const view = state.obs || { self_id: null, sector: {} };
    const items = R.resolve(fresh, view, state, state.manifest);
    const hidden = typeof document !== "undefined" && document.hidden;
    const step = state.session.consider(items, Date.now(), { hidden, maxSeq: state.lastSeq });
    if (hidden) return;
    if (step.playing && (step.playing !== state.playing || step.preempted)) {
      const item = items.find((x) => x.clip_key === step.playing) || { sector_id: null };
      playResolved(step.playing, item);
      return;
    }
    // No viewport clip for this batch: keep the v1 still HUD (and its dismiss
    // button) on the newest row, which is what the default cockpit already shows.
    if (!step.playing) {
      const show = [...fresh].reverse().find((ev) => ev.kind !== "agent_thought" && ev.kind !== "llm_usage");
      if (show) playEntry(resolveKind(show.kind), show.kind);
    }
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
    } catch (_) { /* optional */ }
  }

  if (CU) document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") hide(); });

  window.TW2KMedia = {
    loadManifest, onEvent, onEvents, playEntry, hide, ensureHud,
    skipClip: hide,
    ready: () => !!state.ready,
    _prime: (opts) => {
      opts = opts || {};
      if (opts.lastSeq != null) state.lastSeq = opts.lastSeq;
      if (opts.visit_sector != null) state.visit_sector = opts.visit_sector;
      if (opts.docked_in_visit != null) state.docked_in_visit = !!opts.docked_in_visit;
      state.playing = null;
      state.session = state.manifest && R ? R.createSession(state.manifest) : null;
    },
    _state: () => ({ lastSeq: state.lastSeq, playing: state.playing, visit_sector: state.visit_sector }),
  };
  loadManifest();
})();
