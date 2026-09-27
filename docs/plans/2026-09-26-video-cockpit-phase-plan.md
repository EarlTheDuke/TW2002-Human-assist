# TW2K "Viewport" cockpit: phase plan (planning only)

**Date:** 2026-09-26 PT. **Author:** Grok Bot for Ben. **Status:** PLAN ONLY. No code, no clips generated, no money spent.
**Repo read:** `EarlTheDuke/TW2002-Human-assist` (branches `feature/clip-library` @ `220e88a`, `feature/grokbot-player` @ `5b2f879`, `main`).
**Companion doc:** `PRODUCTION_PLAN.md` (how the clips get made, tools, prices, the hybrid generation model).

---

## 0. Goal in one paragraph

Turn the middle of `/bot` into a **viewport**: a window looking out of your ship into space. By default it plays a quiet ambient loop (a starfield, or a view of the current sector). When the seat's own fogged events come in, it plays a short clip: docking at a port, warping out, trading hits in a fight, being attacked. Start with the actions that happen most (**dock, warp, combat**), prove the pattern, then add StarDock, planets/Genesis, landing and liftoff, ship purchase, death and escape pod, and so on. The viewport is **decoration on top of the source of truth**. It never blocks, slows, or hides a turn, it never shows something the seat isn't allowed to know, and humans, LLM seats, and computer-use (CU) seats all keep the same text and `data-testid` controls.

## 1. What already exists (build on it, don't replace it)

| Asset | Where | What it gives us |
|---|---|---|
| Clip-library plan ML0–ML4 | `docs/plans/2026-09-26-clip-library.md` (clip-library) | Hard rules (fog-safe, CU-safe, reduced motion, no secrets), manifest v1 schema, lookup order `kinds[kind] → groups[group] → none`. ML3 (clips) and ML4 (docs + reduced-motion/CU checklist) are still open. **This plan is the ML3+ follow-on.** |
| `web/media/manifest.json` v1 | clip-library | 19 kinds + 6 groups, each with a `still` and optionally a `clip`, `defaults.duration_ms=2400`, `muted:true`. |
| 16 stills | `web/media/stills/*.png` | 1280×720. **Note: they are really JFIF/JPEG bytes saved with a `.png` extension** (checked with ffprobe and the magic bytes). Browsers don't care, but the production pipeline should name files by their real format. |
| 16 prompt files | `web/media/prompts/*.txt` | One-line style prompts ("dark navy + amber lights, no readable text, no logos, 16:9"). This is the seed of the art bible. |
| `web/media-player.js` (115 lines) | clip-library | Non-blocking HUD overlay (`#mediaHud`, `data-testid="media-hud"`), Esc/click to dismiss, reduced motion means still only, `KIND_GROUP` map, fixed `setTimeout(hide, duration)`. **Limits:** plays only the **newest** event in a poll batch, no priorities or queue, no actor check (a witnessed rival's `trade` plays the same as yours), no ambient layer, no preload, and a single `<video>` with `src` swapping. |
| `scripts/media_validate_manifest.py` | clip-library | Checks that every manifest path exists. Extend it; don't fork it. |
| `mode=cu` one-screen layout | `feature/grokbot-player` (`web/bot.html` `#cuScreen`, `bot.js` ~L1064/1199/1227, `bot.css` ~L235–298) | 1280×800 grid (400px / 440px / flex columns). Top stats; left sector/warps/port/map; middle `#cuToast` + verbs + keyboard + **`#cuMediaSlot`** (the HUD is re-parented here, max-height 250px); right ship/goal/last 5 events/turn card. Test: `tests/test_cockpit_cu_g2.py`. |
| Grok Bot plays by screen G1–G7 | `docs/plans/2026-09-26-grokbot-plays-by-screen.md` | CU seats read screenshots. Motion in the screenshot is noise and costs tokens and time. Pilot G5 is ready to launch, so **the viewport must not disturb the G2 layout or its tests.** |

### Engine facts that shape the design (verified in source)

- **There is no `dock` verb.** `ActionKind` (`src/tw2k/engine/actions.py`) has 34 verbs: `warp, trade, scan, deploy_fighters, deploy_mines, attack, land_planet, liftoff, assign_colonists, load_planet_cargo, dump_planet_cargo, build_citadel, deploy_genesis, claim_planet, plot_course, photon_missile, deploy_atomic, query_limpets, probe, corp_deposit, corp_withdraw, corp_memo, propose_alliance, accept_alliance, break_alliance, buy_ship, buy_equip, corp_create, corp_invite, corp_join, corp_leave, hail, broadcast, wait`. So "docking" has to be **derived** from the first `trade` / `trade_failed` event in a sector since the last `warp`. Haggling happens inside `trade` (price/`note`).
- **Event kinds** (`EventKind` in `models.py`) include `warp, warp_blocked, autopilot, trade, trade_failed, combat, ship_destroyed, player_eliminated, ferrengi_attack, mine_detonated, photon_fired, photon_hit, atomic_detonation, port_destroyed, land_planet, liftoff, genesis_deployed, build_citadel, citadel_complete, planet_claimed, buy_ship, buy_equip, scan, probe, hail, broadcast, day_tick, game_over`, and more.
- **Fog:** the `/events` rows `/bot` gets are `event_view()` (seq, day, tick, kind, actor_id, actor_kind, sector_id, summary, whitelisted `facts`). They are filtered by `_event_visible_to()`: `_PUBLIC_EVENTS` (e.g. `planet_claimed`, `port_destroyed`, `atomic_detonation`, `ferrengi_spawn`, `player_eliminated`) are visible to everyone **even when they happen far away**. `_ACTOR_ONLY_EVENTS` include `scan, probe, buy_ship, buy_equip, warp_blocked, trade_failed, autopilot, photon_fired`. Everything else is "witnessed" (the actor plus anyone in the sector).
  - **Rule:** the viewport shows only things that happen **at the seat's own ship** (`actor_id == self`, or `facts.victim/defender == self`, or witnessed in the seat's current sector). Public events elsewhere never get a first-person window clip. At most they get a caption on the event ticker.
- **Combat facts** (`EVENT_FACTS[COMBAT]`): `exchange_kind` (`ship_vs_ship` / `ferrengi_vs_ship`) or `vs: fighter_sector`, `attacker, defender, attacker_f, attacker_s, defender_f, defender_s, attacker_losses, defender_losses, sector_claimed`. **Ship-vs-ship payloads carry post-fight fighters/shields but no losses**, so client-side "hit vs miss" is ambiguous. Phase 2 adds a tiny engine fact (see §5.3).
- `ship_destroyed` facts: `victim, reason, deaths, death_sector, killer_id`. The summary says "ejected to StarDock", so an **escape pod** clip is legitimate.
- `PortClass`: FED(0), BSS…BBB (1–7), STARDOCK(8). Planet classes M,K,L,O,H,U,C. 10 ship classes.

## 2. Hard rules (inherit ML rules and add a few)

1. **Never block a turn.** The media layer is only fed by the event poll (`fetchEvents` → `TW2KMedia.onEvents`). It never sits on the action POST path, never `await`s video, never disables a button, never takes focus. A clip that fails to load degrades silently to its poster or to nothing.
2. **Fog-safe.** Only fogged `/events` plus the seat's own Observation. No spectator `/state`. Clip selection may only use `facts` that `event_view` already exposes. Variants must never encode hidden info (e.g. a "rival's ship class" variant is allowed only if `other_players[].ship_class` is visible to this seat right now).
3. **Skippable.** Click, Esc, or the "Skip" button stops the clip and goes back to ambient. Global setting: `Viewport: Live / Stills / Off`, plus `Sound: Off (default) / On`.
4. **Reduced motion:** `prefers-reduced-motion: reduce` or the setting `Stills` means poster frames only (crossfade ≤150 ms or instant), no autoplay, no ambient motion.
5. **Photosensitivity:** no clip may have more than 3 flashes in any 1 second (WCAG 2.3.1). This is a review-checklist item for combat and warp.
6. **CU-safe:** in `mode=cu` the default is **Stills** (see §7). No change to any existing `data-testid` or to the G2 1280×800 viewport assertions.
7. **Text stays the truth.** Every clip has a caption, and the event log and result toast always update whether media plays or not.

## 3. Target layout (default `/bot`, non-CU)

```
+----------------------------------------------------------------------------------+
| status bar: turn / deadline | credits | net worth | turns | day | seat           |
+-------------------+-------------------------------------------+------------------+
| Sector + warps    |            VIEWPORT (16:9)                | Ship / cargo     |
| Port tape         |  ambient loop  <- event clip -> ambient   | Events (last N)  |
| Known-space map   |  caption strip: "Docked at 1234 (BBS)"    | Turn card        |
|                   |  [Skip] [Live|Stills|Off] [Sound]         |                  |
|                   +-------------------------------------------+                  |
|                   | verbs pad + result toast (unchanged ids)  |                  |
+-------------------+-------------------------------------------+------------------+
```

- The viewport is a `<section id="viewport" data-testid="viewport" aria-label="Viewport" role="img">` with **two stacked `<video>` layers** (`ambient`, `event`) plus an `<img>` poster layer and a caption `<div aria-live="polite">`. It reuses the `#mediaHud` markup concepts, but it lives in the layout instead of floating over it. The existing `#mediaHud` stays as a fallback for pages without a viewport (and for `cu`).
- Optional **cockpit-frame overlay**: a transparent PNG/SVG frame per hull family (window struts, dash glow) drawn by CSS over the video. This makes "your ship" visible without re-rendering every clip per ship class. It's a big lever for the production matrix (see PRODUCTION_PLAN §6).
- Size: the center column is about 560–720px wide at 1280–1440 viewports. Render and encode at 960×540 (16:9) with a 640×360 rendition for narrow screens.

## 4. Event → clip mapping design

### 4.1 Manifest v2 (backward compatible with v1)

`web/media/manifest.json` gets `"version": 2`. The v1 `kinds`/`groups` blocks stay and are still what the old HUD reads. New top-level blocks:

```json
{
  "version": 2,
  "defaults": { "duration_ms": 2400, "fit": "cover", "muted": true,
                "max_queue": 1, "stale_ms": 4000, "crossfade_ms": 150 },
  "ambient": {
    "deep_space": { "variants": [
      { "id": "amb_deep_a", "webm": "clips/amb_deep_a.7c1e.webm", "mp4": "clips/amb_deep_a.7c1e.mp4",
        "poster": "posters/amb_deep_a.7c1e.webp", "duration_ms": 8000, "loop": true, "bytes": 820000 } ] },
    "fedspace":   { "variants": [ ... ], "when": { "sector.fed": true } },
    "port_near":  { "variants": [ ... ], "when": { "sector.port": "present" } }
  },
  "clips": {
    "dock.port": {
      "priority": 2, "cooldown_ms": 0, "caption": "Docking at {sector_id}",
      "fallback_still": "stills/trade_port.png", "preload": "eager",
      "variants": [
        { "id": "dock_port_std_a", "tags": { "station": "std", "hull": "*" }, "weight": 1,
          "webm": "clips/dock_port_std_a.1b9f.webm", "mp4": "clips/dock_port_std_a.1b9f.mp4",
          "poster": "posters/dock_port_std_a.1b9f.webp", "duration_ms": 3200, "bytes": 310000,
          "provenance": { "tool": "grok-imagine-video-1.5", "shot_id": "S-DOCK-01", "take": 3, "approved_by": "ben", "approved_at": "..." } }
      ]
    },
    "warp.out":         { "priority": 2, "...": "..." },
    "combat.hit":       { "priority": 1, "...": "..." },
    "combat.miss":      { "priority": 1, "...": "..." },
    "combat.incoming":  { "priority": 0, "...": "..." },
    "combat.witnessed": { "priority": 3, "...": "..." }
  },
  "triggers": [
    { "kind": "trade",          "rule": "self && first_in_visit",           "clip": "dock.port" },
    { "kind": "trade_failed",   "rule": "self && first_in_visit",           "clip": "dock.port" },
    { "kind": "warp",           "rule": "self",                             "clip": "warp.out" },
    { "kind": "autopilot",      "rule": "self",                             "clip": "warp.out", "coalesce": "warp" },
    { "kind": "combat",         "rule": "self_attacker && outcome_hit",     "clip": "combat.hit" },
    { "kind": "combat",         "rule": "self_attacker && !outcome_hit",    "clip": "combat.miss" },
    { "kind": "combat",         "rule": "self_defender",                    "clip": "combat.incoming" },
    { "kind": "ferrengi_attack","rule": "self_victim",                      "clip": "combat.incoming" },
    { "kind": "combat",         "rule": "witnessed_in_my_sector",           "clip": "combat.witnessed" }
  ],
  "groups": { "...v1...": {} },
  "kinds":  { "...v1...": {} }
}
```

- **`rule`** is a small fixed set of **named predicates** built into `media-player.js`, like `self`, `self_attacker`, `self_defender`, `self_victim`, `first_in_visit`, `outcome_hit`, `witnessed_in_my_sector`, joined with `&&` and `!`. There's no `eval`. Unknown predicate names make the validator fail.
- **Variant selection:** filter by `tags` against the context (`station` from the port class via a lookup table, `hull` from `obs.ship.class` → hull family, `planet` class, `faction` of the opponent when visible). Most-specific match wins, `*` is a wildcard, ties are broken by weighted random with a **no-immediate-repeat** rule (last variant per key is remembered in `sessionStorage`).
- **Fallback chain per play:** exact variant → key's wildcard variant → `fallback_still` (poster with a slow CSS push-in, "Ken Burns" 1.03× scale over the duration) → v1 `kinds[kind]` still → caption only.
- **File naming:** `<key_with_underscores>_<variant>.<contenthash8>.<ext>`. The hash makes URLs immutable, so they can be cached forever.
- **Validator** (`scripts/media_validate_manifest.py` extended): paths exist; every clip key referenced by a trigger exists; predicates are known; `bytes` and `duration_ms` match the real files (ffprobe); posters exist; the size budget in §6 holds; no trigger references an event kind outside `EventKind`; no trigger targets a public-only kind with a first-person clip.

### 4.2 Derived signals (client-side, from fog-legal data only)

| Signal | Derivation |
|---|---|
| `self` | `ev.actor_id === obs.self_id` |
| `first_in_visit` | the player keeps `visitSector`, reset on every self `warp`/`autopilot` arrival. The first self `trade`/`trade_failed` with `ev.sector_id === visitSector` fires docking. Later trades in the same visit don't. |
| `self_defender` / `self_victim` | `facts.defender === self` / `facts.victim === self` |
| `witnessed_in_my_sector` | `ev.actor_id !== self && ev.sector_id === obs.sector.id` |
| `outcome_hit` | Phase 2: `facts.defender_losses > facts.attacker_losses` when present (fighter-sector clashes already have both). For ship-vs-ship, use the new `outcome` fact (§5.3). Until then: treat as `hit` if `facts.defender_f` dropped compared with the same defender's last visible `other_players[]` / `sector.occupants` fighter count, else `miss`. Unknown means `combat.hit` (neutral "exchange" footage works for both in the pilot). |
| `station` | `PortClass`: 1–7 → `std` (split into `small`/`large` later if the art wants it), 0 → `fed`, 8 → `stardock` |
| `hull` | 10 ship classes → 4 families: `hauler` (merchant_cruiser, merchant_freighter, cargotran, colonial_transport), `light` (scout_marauder, missile_frigate), `heavy` (battleship, havoc_gunstar), `capital` (corporate_flagship, imperial_starship) |

### 4.3 Priority and queueing when events come fast

The event poll often returns several rows at once (e.g. autopilot hops, or a trade burst). Rules:

1. **Classify** each new row (seq > lastSeq, in order) into a trigger. Rows with no trigger are ignored by the viewport; the log still shows them.
2. **Priority classes:** `P0` threat to self (incoming fire, own ship destroyed); `P1` your combat result; `P2` your movement/docking/StarDock/planet action; `P3` witnessed in your sector; `P4` ambient change. Public elsewhere-events never enter the queue.
3. **Coalesce inside a batch:** multiple `warp` rows (autopilot) become **one** `warp.out`; the last hop decides the arrival ambient. Multiple combat rounds become the worst outcome for self (incoming > miss > hit). Multiple trades at one port become one dock.
4. **Queue length 1.** At most one clip plays and one waits. A new item with **higher priority** preempts the playing clip (150 ms crossfade). **Equal or lower priority** replaces the waiting slot (latest wins) and never interrupts.
5. **Staleness:** drop a waiting item if it is older than `stale_ms` (4 s), or if a newer self action seq has already been posted (the player has moved on). Clips must never lag behind the game.
6. **Duration cap:** event clips are 2–4 s (hard cap 5 s). After the clip, crossfade back to ambient. Ambient switches (sector type change) wait until no event clip is playing.
7. **Cooldown per key** (optional, e.g. `combat.witnessed` 10 s) so a slugfest in your sector doesn't spam.
8. **Tab hidden** (`document.hidden`): skip all event clips and just keep `lastSeq` current. Nothing replays when you come back.

### 4.4 Settings and accessibility

- `localStorage["tw2k.viewport"] = live|stills|off` (default `live`; `stills` if `prefers-reduced-motion`; `stills` in `mode=cu`). `?viewport=` URL param overrides for testing.
- Sound: off by default. If turned on, it's a single `<audio>` bus at a low volume, with SFX only, no voices. Clips ship **silent** (audio muxed separately, optional).
- Captions: always shown in the caption strip (and `aria-live="polite"`). The `<video>` gets `aria-hidden="true"` because the caption carries the meaning.
- Skip: button `data-testid="viewport-skip"`, Esc, or a click on the viewport. None of them steal focus from the verb pad.

### 4.5 Formats, sizes, preload, caching

- **Formats:** WebM (VP9, `yuv420p`, no audio) first, MP4 (H.264 High, `+faststart`) as fallback, chosen via `<source type>`. Posters are WebP (JPEG fallback), taken from the first frame (the ambient loop's frame 0 equals its last frame).
- **Renditions:** 960×540 @ 24 fps (default) and 640×360 (narrow screens or `saveData`). No 1080p. The viewport never needs it.
- **Size targets:** event clip of 3 s at 540p ≤ 350 KB (roughly 900 kbps). Ambient loop of 8 s ≤ 900 KB. Poster ≤ 60 KB.
- **Preload:** posters for all P0–P2 keys load eagerly after first paint. After that, `requestIdleCallback` fetches the **pilot set** of clips (§6 budget) into blob URLs with a memory cap of 12 MB, LRU. Everything else is `preload="none"` and gets fetched on first use, showing the poster until `canplay`. Respect `navigator.connection.saveData` (posters only).
- **HTTP caching:** hashed filenames plus `Cache-Control: public, max-age=31536000, immutable` for `/static/media/clips|posters/*`. That needs a small StaticFiles header tweak, flagged as a code item in Phase 4. `manifest.json` stays `no-store` (as today) or short max-age.

## 5. Phases, milestones, done criteria

Every phase follows the repo's existing working rules: its own branch/PR, tests plus `ruff` clean, no change to the running match, fog rules intact, docs matching what shipped.

### Phase V0 — Spec lock and fixtures (no UI change)
- Manifest v2 JSON Schema (`web/media/manifest.schema.json`) and the extended validator.
- **Event fixtures:** record `/events` batches from a real local match (seed 250925) covering: a single warp, an autopilot burst, a trade burst at one port, trade_failed, self attack (win and lose), being attacked by a Ferrengi, witnessed combat in-sector, and a public far-away `port_destroyed`.
- A pure trigger resolver spec (input: batch plus minimal obs; output: an ordered list of `{clip_key, priority}`) written as a table of expected outcomes.
- **Done when:** the schema validates v1 and v2 examples; the fixture table is reviewed by Ben; the validator rejects bad predicates and missing files; no runtime code has changed.

### Phase V1 — Viewport shell and ambient (stills first, no generated video)
- Add the viewport section to the default `/bot` layout (not `cu`). Ambient uses an existing still (`move_warp.png` or a new starfield still) with a CSS slow drift, or a **procedural canvas starfield** (cheap, zero assets, and it doubles as the reduced-motion-off fallback).
- Settings control (Live/Stills/Off, Sound), skip button, caption strip.
- **Done when:**
  - The Playwright screenshot of the default `/bot` at 1440×900 shows the viewport, and all pre-existing `data-testid`s are still present and visible (diffed against a list captured before the change).
  - `tests/test_cockpit_cu_g2.py` passes unchanged. `mode=cu` shows no viewport section.
  - Action round-trip time (click to toast) with the viewport on is within ±5% of viewport off, measured over 50 scripted actions on `:8032`.
  - With `prefers-reduced-motion` emulated, there's no animation (computed style check, no running `<video>`).

### Phase V2 — Event engine with placeholder media (prove the pattern for $0)
- Rewrite `media-player.js` into three pieces: a resolver (triggers, predicates, coalesce, priority, queue), a renderer (two video layers plus poster and caption), and settings. Keep the `window.TW2KMedia` API (`onEvents`, `onEvent`, `hide`, `playEntry`) for compatibility.
- The first three keys are wired with **placeholder "clips"**: existing stills with a CSS push-in plus a tint pulse (`dock.port` ← `trade_port.png`, `warp.out` ← `move_warp.png`, `combat.*` ← `combat_alert.png`/`combat_photon.png`).
- **Engine micro-change (separate small PR, optional but recommended):** add `attacker_losses`, `defender_losses`, and `outcome` (`"hit" | "miss" | "destroyed"` from the attacker's point of view) to the ship-vs-ship and ferrengi-vs-ship `COMBAT` payloads, and whitelist them in `EVENT_FACTS[COMBAT]`. These are facts both parties already witness, so fog doesn't change. Add a pytest.
- **Done when:**
  - The resolver unit test (Node `--test` or pytest driving a headless page) passes every V0 fixture row: autopilot burst → exactly 1 `warp.out`; 5 trades at one port → exactly 1 `dock.port`; incoming fire preempts a playing dock clip; witnessed combat → `combat.witnessed` only when in the same sector; the far-away public `port_destroyed` → no viewport clip; `trade` by another seat in your sector → no dock clip.
  - A live local match with 1 human seat and 2 LLM seats for 30 minutes shows no JS errors, and the viewport never stays on an event more than 5 s after the last event.
  - Timing again within ±5% of viewport-off.

### Phase V3 — Pilot clips: dock, warp, combat (first real video)
- Produce the **pilot set** following PRODUCTION_PLAN §5–§10: 2 ambient loops, 3 `dock.port`, 3 `warp.out`, 2 `combat.hit`, 2 `combat.miss`, 2 `combat.incoming` = **14 clips**.
- Swap them into manifest v2 with provenance. Posters generated. Old stills stay as `fallback_still`.
- **Done when:**
  - All 14 have passed the review checklist (PRODUCTION_PLAN §9) and are listed with `approved_by`.
  - The validator is green, including size budgets. Total pilot payload ≤ 6 MB (both formats) and ≤ 3.5 MB for the formats a single browser downloads.
  - A 20-minute playtest by Ben (human seat) produces a short "feel" note: clips read correctly, nothing felt laggy, and the skip, stills, and off settings work.
  - Chrome, Firefox, and Safari (or WebKit via Playwright) each play the WebM/MP4 fallback correctly.

### Phase V4 — Hardening: preload, caching, telemetry, CU options
- Immutable cache headers for hashed media. Idle preload with a memory cap. `saveData` handling.
- Client-only counters in `sessionStorage` (plays, skips, preemptions, stale-drops, poster-fallbacks) shown in the Raw drawer. No server telemetry needed.
- `mode=cu` options wired (see §7). Docs for ML4: player guide section and CU checklist.
- **Done when:**
  - Performance budget (§6) met on a throttled profile (4× CPU slowdown, "Fast 3G" for the first load).
  - A second page load plays pilot clips from cache (the network tab shows 0 bytes for clips).
  - The CU checklist passes: `mode=cu` default shows stills, the G2 test is green, and a CU screenshot contains no motion blur or half-faded frames. The CU agent time-per-action is unchanged versus viewport off in a 10-action dry run.

### Phase V5 — Expansion wave A: StarDock and weapons
Keys: `dock.stardock` (docking at sector 1 / PortClass 8), `stardock.buy_ship` (reveal of the new hull, variants per hull family, fog-safe because it's your own purchase), `stardock.buy_equip`, `weapon.photon_fired`, `weapon.photon_hit` (self target → P0), `hazard.mine_detonated` (victim self → P0).
**Done when:** each new key has ≥1 approved variant plus fixture rows, and the validator and perf budget are still green.

### Phase V6 — Expansion wave B: planets
Keys: `planet.land` and `planet.liftoff` (variants by planet class M/K/L/O/H/U/C, grouped into 3–4 looks), `planet.genesis` (a torpedo blooms into a new world; the class is in `genesis_deployed.facts.class`), `planet.citadel_build` / `planet.citadel_complete`, `planet.claim` (self only; the public far-away claim is caption only). Ambient `orbit_<look>` while `planet_landed` is set.
**Done when:** as V5, plus the ambient switches correctly on land/liftoff in a fixture replay.

### Phase V7 — Expansion wave C: death, pod, endgame, comms
Keys: `self.ship_destroyed` (P0), `self.escape_pod` (plays right after, "ejected to StarDock"), `self.eliminated`, `ferrengi.spawn_witnessed` (only if in-sector), `comms.hail` (a HUD overlay instead of full-frame video), `match.game_over`.
**Done when:** as V5. The death → pod sequence plays as a chained pair and can't be preempted by lower priorities.

### Phase V8 (optional, gated) — Live custom moments (hybrid queue)
The server-side background generation queue from PRODUCTION_PLAN §6.2–6.3 (placeholder immediately, swap the custom clip in only if it lands before the next action, otherwise it goes to a post-turn reel). Only after V4, behind `TW2K_VIDEO_CUSTOM=1`, with a per-match cost cap.
**Done when:** the PRODUCTION_PLAN §6.4 acceptance list passes on a local match. The cap is enforced by test, and a gameplay timing test shows zero change.

## 6. Performance budget

| Metric | Budget |
|---|---|
| Added latency on action POST → toast | 0 by design. Measured ≤ +5% vs viewport off. |
| Main-thread work per event (resolve + swap) | ≤ 4 ms p95 |
| Concurrent decoding videos | ≤ 2 (ambient paused/hidden while an event clip plays, or ambient poster frozen) |
| First load extra bytes before interactive | ≤ 150 KB (posters of ambient + P0–P2 keys, lazy after first paint) |
| Idle preload (pilot set, one format) | ≤ 3.5 MB; memory cap 12 MB of blobs |
| Per event clip file | ≤ 350 KB at 540p / 3 s; hard cap 600 KB |
| Ambient loop | ≤ 900 KB / 8 s |
| CPU while ambient plays (mid laptop) | ≤ 10% of one core; pause ambient when tab hidden or viewport off-screen (`IntersectionObserver`) |
| Layout shift | 0 (fixed 16:9 aspect box) |

## 7. `mode=cu` (computer-use agents)

- **Default `viewport=stills`:** `#cuMediaSlot` (already in G2) shows the **poster frame** of the resolved clip plus its caption, updated per event, with no animation or crossfade (instant swap). That keeps screenshots deterministic and cheap.
- `?viewport=off` hides the slot (the G2 layout reserves the space, so there's no reflow). `?viewport=live` is allowed for demos but documented as "not for scored CU play".
- The poster carries **no information that isn't in text**. The toast, last-5 events, and turn card remain the authoritative inputs for the agent.
- LLM/API seats never load `/bot`, so nothing changes for them. Headless harness seats aren't affected.
- Test: extend `tests/test_cockpit_cu_g2.py` (or a sibling) to assert that the viewport isn't playing video in `cu`, all G2 fields are still inside 1280×800, and the `cu-media` slot keeps its height.

## 8. Testing matrix

| Layer | Test |
|---|---|
| Manifest | Validator in CI: schema, files, hashes/bytes/duration via ffprobe, size budget, known predicates, known EventKinds, no first-person trigger on public-only kinds. |
| Resolver | Fixture-table unit tests (V0 fixtures), including burst/coalesce/preempt/stale/cooldown/fog cases. |
| Engine | pytest for the new `outcome`/losses combat facts, plus the fog tests that already exist (`test_parity_*`) still green. |
| UI | Playwright: default layout screenshot, `data-testid` inventory unchanged, reduced-motion emulation, Live/Stills/Off, skip via Esc/click/button, `mode=cu` G2 test. |
| Perf | Scripted 50-action run on `:8032` comparing viewport off/live. Chrome trace for main-thread cost. Throttled first-load check. |
| Browser | Chromium, Firefox, WebKit playback of WebM + MP4 fallback. |
| Human | Ben's 20-min feel playtest per wave. A CU dry run of 10 actions per wave. |

## 9. Open questions for Ben

1. Ambient: a procedural canvas starfield (free, crisp, tiny) or generated video loops (prettier, costs money and bytes)? The recommendation is to start procedural in V1 and switch to generated loops in V3.
2. Should the cockpit-frame overlay per hull family exist? It lets one clip serve all 10 ship classes.
3. OK to land the small engine change adding combat `outcome` and losses to ship-vs-ship payloads?
4. Sound: ship it at all in V3, or wait until V7?
