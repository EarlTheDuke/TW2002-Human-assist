/* TW2K media player — fogged-event stills/clips for /bot. CU-safe: non-blocking HUD. */
(function () {
  "use strict";
  const BASE = "/static/media/";
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

  const state = { manifest: null, lastSeq: 0, hideTimer: null, reduced: false };

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
      '  <video id="mediaHudVideo" muted playsinline></video>',
      '  <div id="mediaHudCaption" class="media-hud-caption"></div>',
      '  <button type="button" id="mediaHudDismiss" class="media-hud-dismiss" data-testid="media-hud-dismiss" aria-label="Dismiss">×</button>',
      "</div>",
    ].join("");
    document.body.appendChild(root);
    document.getElementById("mediaHudDismiss").addEventListener("click", hide);
    root.addEventListener("click", (ev) => { if (ev.target === root) hide(); });
    document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") hide(); });
    return root;
  }

  function hide() {
    const root = document.getElementById("mediaHud");
    if (!root) return;
    root.hidden = true;
    root.classList.remove("show");
    const v = document.getElementById("mediaHudVideo");
    if (v) { try { v.pause(); v.removeAttribute("src"); v.load(); } catch (_) {} }
    if (state.hideTimer) clearTimeout(state.hideTimer);
  }

  function resolve(kind) {
    const m = state.manifest;
    if (!m) return null;
    const entry = (m.kinds && m.kinds[kind]) || (m.groups && m.groups[KIND_GROUP[kind] || "system"]) || null;
    return entry;
  }

  function playEntry(entry, kind) {
    if (!entry) return;
    state.reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const root = ensureHud();
    const img = document.getElementById("mediaHudStill");
    const vid = document.getElementById("mediaHudVideo");
    const cap = document.getElementById("mediaHudCaption");
    const duration = (state.manifest.defaults && state.manifest.defaults.duration_ms) || 2400;
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

  async function loadManifest() {
    try {
      const r = await fetch(BASE + "manifest.json", { cache: "no-store" });
      if (!r.ok) return;
      state.manifest = await r.json();
    } catch (_) { /* optional */ }
  }

  function onEvent(ev) {
    if (!ev || typeof ev.seq !== "number") return;
    if (ev.seq <= state.lastSeq) return;
    state.lastSeq = ev.seq;
    // Skip noisy meta kinds by default
    if (ev.kind === "agent_thought" || ev.kind === "llm_usage") return;
    playEntry(resolve(ev.kind), ev.kind);
  }

  function onEvents(list) {
    if (!Array.isArray(list) || !list.length) return;
    const newest = list[list.length - 1];
    onEvent(newest);
  }

  window.TW2KMedia = { loadManifest, onEvent, onEvents, playEntry, hide, ensureHud };
  loadManifest();
})();