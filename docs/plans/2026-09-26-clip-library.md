# Clip / stills library for `/bot` (presentation layer) — 2026-09-26

**Author:** Commander. **Ben:** go-ahead 2026-09-25 evening PT.  
**North star:** Fogged events on `/bot` can play a short still or clip for atmosphere, while **text + `data-testid` remain the source of truth** for humans and computer use. Never replace Observation panels with video-only UX.

**Not this track:** Replacing `/bot` with the USS Enterprise Three.js app (`EarlTheDuke/uss-enterprise-ncc-1701`). That repo is inspiration / optional clip source only.

## Architecture

```
Fogged event (kind)  -->  media/manifest.json lookup
                              |
                              +--> still (png/webp)  --> <img> flash / crossfade
                              +--> clip  (webm/mp4) --> <video> (muted default, optional SFX later)
                              |
                         always also: event log row + last-result text
```

- Assets live under `web/media/` and are served as `/static/media/...` (existing StaticFiles mount of `web/`).
- Catalog is `web/media/manifest.json` (kind → asset, with group fallbacks).
- Player is `web/media-player.js`, loaded by `bot.html`. It must degrade to no-op if assets missing.
- Generation tools: prompt pack + `scripts/media_validate_manifest.py` + Commander `GenerateImage` for stills; video is a later hook (xAI/browser) into `web/media/clips/`.

## Hard rules

1. **Fog-safe:** only map kinds the seat already sees in `/events` / `recent_events`. No god-state cinematic of unseen sectors.
2. **CU-safe:** never hide warp/verb buttons behind a modal video; player is a non-blocking HUD layer; Esc / click dismisses.
3. **Reduced motion:** honor `prefers-reduced-motion: reduce` → still only, or skip animation.
4. **No secrets in media paths.**

## Manifest schema

```json
{
  "version": 1,
  "defaults": { "duration_ms": 2200, "fit": "cover" },
  "groups": {
    "move": { "still": "stills/move_warp.png", "caption": "Warp" }
  },
  "kinds": {
    "warp": { "still": "stills/move_warp.png", "caption": "Warping" },
    "trade": { "still": "stills/trade_port.png", "caption": "Trade" }
  }
}
```

Lookup order: `kinds[kind]` → `groups[groupOf(kind)]` → none.

## Slices

| Id | Deliverable |
|----|-------------|
| **ML0** | Scaffold: folders, manifest, prompts, validate script, plan, mailbox | **done** |
| **ML1** | Generate first stills batch into `web/media/stills/` + fill manifest paths | **done** (16 stills) |
| **ML2** | Wire `media-player.js` + `bot.html`/`bot.js`/`bot.css` HUD; play on new fogged events | **done** |
| **ML3** | Optional: pull 2–3 short WebMs from Enterprise clip editor *or* external video API into `clips/`; manifest `clip` fields |
| **ML4** | Docs in player guide + handoff; reduced-motion / CU checklist test |

## Commander tools needed (checklist)

- [x] Plan + manifest schema  
- [x] Prompt pack per kind/group  
- [x] Validate script  
- [x] Image gen batch (GenerateImage → copy into `web/media/stills/`) — 16/16 2026-09-25  
- [x] `/bot` player wiring (media-player.js + bot.html/js/css)  
- [ ] Video ingest path (documented; API when available)

## Acceptance

On a live `/bot` seat, when a `warp` event appears in the footer, a short still flashes without blocking SCAN/WAIT; with CSS reduced-motion, only a brief caption or nothing plays; computer-use selectors unchanged.
