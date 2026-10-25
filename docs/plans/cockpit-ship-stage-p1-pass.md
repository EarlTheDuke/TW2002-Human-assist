# P1 pass — Merchant Cruiser and Imperial StarShip

Record of the read. Parent: [P1 acceptance](cockpit-ship-stage-p1-acceptance.md). Measurements: [P1 spike](cockpit-ship-stage-p1-spike.md). Merged product: [#215](https://github.com/EarlTheDuke/TW2002-Human-assist/pull/215) (`9d29349a`). Sheets read at `feature/grokbot-player` @ `3765f609`.

The stills inventory is [stills/README.md](stills/README.md) (#344), directory [p1-merchant-imperial](stills/p1-merchant-imperial/) (TBD scaffold, no PNG, does not stamp Pass).

Docs only. The renderer stayed on the shared SVG loft (`buildHullFaces` / `projectFace`). This sheet does not change `web/*`, the engine, tests, `COMMANDER_NEXT`, `GAP_MAP`, the sheet index, or the other ship-stage sheets.

**Pass.** All nine acceptance bullets hold. WebGL stays the closed off-ramp.

## The nine

Five are the acceptance reads: three-quarter, head-on, accent, marker ring, and the CU-seat still. The other four are the render memo lines that sheet still requires: the legend and stat block, gzip and frame time, the 1,000-path clause, and the screenshots.

1. **Three-quarter.** Yaw `0.82`, pitch `0.5`. Name covered, at ~140px and at a hero crop about 55% of the deck, at shields 0 and shields full. The Merchant reads as the trader (keel and shoulder pods). The Imperial reads as the capital (long stepped castle and four bells). **Pass.**
2. **Head-on.** One existing clip per hull, side camera and head-on camera. The Merchant's keel and pods still read. The Imperial's four bells make a square, the castle still reads as a keep, and the gold stays on that castle. `holdWarp` still pauses a frame. **Pass.**
3. **Accent.** Merchant `#7aa2ff` on the keel, the pods, and the bridge. Imperial `#ffe9a0` on the castle and the stripe. Shields 0: the bubble is absent, scars may show, and the class colour stays. The spike sheet's accent averages match that pair: Merchant blue `[99, 131, 206]`, Imperial gold `[202, 184, 126]`, the same at damage 0 and damage 1. **Pass.**
4. **Marker ring.** `n < 1` draws nothing; otherwise `max(1, ceil(n / 100))`. The spike placed 0, 1, 25, 500, and the throwaway 1,000 on the Imperial (the later Interdictor's stand-in). Every slot sat outside the bounding sphere. The silhouette raster found 0 screen-box hits and 0 clipped boxes. **Pass.**
5. **Legend and stat block.** The visible legend is `each marker = 100 fighters`. The stat block keeps today's words, order, and the exact bay. Corner clusters and `FIGHTER_EXACT_CAP` are retired. #215 updated the ship-view tests that asserted the 200-cap legend in that same change. That PR reports `tests/test_cockpit_ship_stage_p1.py` and `tests/test_ship_view_visual_v1.py` passed (8 tests). No engine change, no new action, no new event field. **Pass.**
6. **CU-seat and reduced motion.** `prefers-reduced-motion`, a phone (`max-width: 700px`), and `body.cu-seat` hold the canonical still. No loop on those three. The turn is not blocked. **Pass.**
7. **Size.** `web/hull-meshes.js` is 8,673 bytes gzipped (level 9), about 8.7 KB, under the 40 KB budget. Face counts are recorded: Merchant Cruiser 217 (41 accent), Imperial StarShip 311 (71 accent). Drift at 500 markers and a static frame at 1,000 are recorded below. **Pass.**
8. **1,000 paths.** The drift frame and the static frame both held 16 ms, so the markers stayed individual SVG paths. The count stayed `ceil(n / 100)`. Three.js stayed closed. **Pass.**
9. **Screenshots.** #215 carries both hulls, shields empty and shields full, the 25-marker and 500-marker cases, and the side and head-on clip cameras. The name plate is absent. The hero row is about 600×390 and the small row is 215×140. The screenshot gate for the other 15 is met. **Pass.**

## Gzip and frame time

As reported on the spike sheet and on #215. Gzip is about 8.7 KB (8,673 bytes, level 9).

Headless Chrome on the spike VM, Imperial, one `drawShipFrame`-shaped update plus a forced layout. Median / max. Slot bake is not in these numbers.

| Frame | Fit | Markers | JS + layout |
| --- | --- | --- | --- |
| Drift (yaw spin, pitch wobble) | 0.76 | 500 | 4.3 / 7.3 ms |
| Static canonical | 0.72 | 1,000 | 6.4 / 8.3 ms |
| Static canonical | 0.76 | 1,000 | 6.5 / 8.1 ms |

Drift and both static frames sit under 16 ms.

## Product next

P1b mesh builds, on the same SVG path. The four-hull wave is [next hulls](cockpit-ship-stage-p1b-next-hulls.md).

1. Scout Marauder and Merchant Freighter. In flight.
2. Then BattleShip and Corporate FlagShip.
3. Then the batch-1 remainder: Escape Pod and T'Khasi Orion ([batch 1 remainder](cockpit-ship-stage-p1b-batch1-remainder.md)).
4. Then haulers, guns, dish and X, and brick and hoops, in [fleet order](cockpit-ship-stage-p1b-fleet-order.md).

## Hold-WebGL

Closed. It opens only if a later P1b read fails an off-ramp condition on the acceptance sheet: the read still fails at hero size, a drift of 500 markers or a static frame of 1,000 markers cannot hold 16 ms, or a planet disc and a warp camera cannot be expressed in the SVG the clips already animate. A fleet batch stays on `buildHullFaces` / `projectFace`.
