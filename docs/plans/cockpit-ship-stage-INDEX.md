# Cockpit ship stage — sheet index

Finder for the ship-stage planning pack. Docs only. Tip: `feature/grokbot-player` @ `6f82b735`. COMMANDER_NEXT just landed through #243 (#245). #251 refreshed COMMANDER_NEXT through #250. #252 moved the tip to `b95e4219`. #253 refreshed the four-hull tip to `1c3fd84b`. #254 moved the tip to `336883dc`. #255 added batch-1 readiness (gated behind cut 2). #256 moved the tip to `7c30c78d` (and added the batch-1 readiness pointer). #257 refreshed COMMANDER_NEXT through #255. #258 refreshed the four-hull tip to `9ad2c989`. #259 moved the tip to `6b54bec5`. #260 refreshed P2 readiness onto `6b54bec5`. #261 moved the tip to `489c44e3`. #262 refreshed COMMANDER_NEXT through #261. #263 refreshed the four-hull tip to `d1b53755`. #264 refreshed the P3 layout tip to `d1b53755`. #265 moved the tip to `1487293d`. #266 refreshed P2 readiness onto `e9b1e292`. #267 refreshed COMMANDER_NEXT through #268 (mailbox tip `498d3bf4`). #268 delivered the Cut 2 product (BattleShip and Corporate FlagShip) at `b0e96881`. Stills: `docs/plans/stills/p1b-battleship-flagship/`. Sheet: `docs/plans/cockpit-ship-stage-p1b-battleship-flagship.md`. #269 moved the tip to `498d3bf4` and pointed Cut 2 stills at #268. #270 refreshed the four-hull tip to `59f14ab0` (cut-2 product landed). #271 recorded the Cut 2 Pass stamp for BattleShip and Corporate FlagShip (product #268). #273 moved the tip to `8a13628c`. #272 refreshed the P3 layout tip to `2f750ae3`. #274 refreshed COMMANDER_NEXT through #272 (mailbox tip `638a61b5`). #275 refreshed the four-hull tip to `f1f94c2c`. #276 refreshed P2 readiness onto `33db4140`. #277 moved the tip to `7864c720`. #278 refreshed the four-hull tip to `1f2fa374`.

## Product order

P1 Merchant Cruiser + Imperial StarShip spike (in flight) → P1b batches → P2 FX product → P3 layout product.

SVG path (`buildHullFaces` / `projectFace`). WebGL only if the P1 spike fails the read test.

P1 is the spike named in the P0 pack and the render memo. Open the sheet below that matches the cut you are on.

## P1

- [P1 acceptance](cockpit-ship-stage-p1-acceptance.md) — Pass / Fail / Hold-WebGL read-test for the Merchant Cruiser and Imperial StarShip SVG spike. Pass stamp for that spike (#222).
- [P1 spike](cockpit-ship-stage-p1-spike.md) — Merchant Cruiser and Imperial StarShip SVG passed (#215).
- [P1 pass](cockpit-ship-stage-p1-pass.md) — Pass on all nine acceptance bullets; WebGL stays closed (#220).

## P0

- [P0 pack](cockpit-ship-stage-p0.md) — Parent: today's picture, sticky rules, phased done-when, and the defaults Ben can override.
- [Render decision](cockpit-ship-stage-p0-render.md) — Stay on one shared shaded SVG mesh; three.js or raw WebGL is the off-ramp if the spike misses the read bar.
- [FX state machine](cockpit-ship-stage-p0-fx.md) — Idle, warp, port, planet, mine, and combat: pictures, precedence, and the events that already start them.
- [Silhouette bible](cockpit-ship-stage-p0-silhouette-bible.md) — Invented look for all 17 player hulls and the 100:1 fighter dart. Classic ANSI stays unverified.
- [Fighter marker math](cockpit-ship-stage-marker-math.md) — Shared 100:1 count: none at `n = 0`; otherwise `max(1, ceil(n / 100))`, each marker standing for 100 fighters.

## P1b

- [Four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) — Product build order after the P1 pass: Scout Marauder and Merchant Freighter, then BattleShip and Corporate FlagShip, then later batches (#219).
- [Cut 1 acceptance](cockpit-ship-stage-p1b-scout-freighter-acceptance.md) — Pass / Fail / Hold-WebGL read-test for cut 1 Scout Marauder + Merchant Freighter (#226). Pass stamp for that cut (#244).
- [Scout and Freighter stills](cockpit-ship-stage-p1b-scout-freighter.md) — Measured faces, markers, and frame times for the needle and the freighter.
- [Cut 2 acceptance](cockpit-ship-stage-p1b-battleship-flagship-acceptance.md) — Pass / Fail / Hold-WebGL for BattleShip + Corporate FlagShip (#227). Pass stamp for that cut (#271 / product #268, `b0e96881`).
- [BattleShip and FlagShip stills](cockpit-ship-stage-p1b-battleship-flagship.md) — Cut 2 product landed (#268, `b0e96881`). Stills under `docs/plans/stills/p1b-battleship-flagship/`.
- [Batch 1 acceptance](cockpit-ship-stage-p1b-batch1-acceptance.md) — Pass / Fail / Hold-WebGL read-test for Escape Pod + T'Khasi Orion (#230).
- [Batch 2 haulers acceptance](cockpit-ship-stage-p1b-batch2-haulers-acceptance.md) — Pass / Fail / Hold-WebGL for CargoTran + Colonial Transport + Taurean Mule (#232).
- [Batch 3 guns acceptance](cockpit-ship-stage-p1b-batch3-acceptance.md) — Pass / Fail / Hold-WebGL for Missile Frigate + Havoc GunStar (#235).
- [Batch 4 dish/X acceptance](cockpit-ship-stage-p1b-batch4-acceptance.md) — Pass / Fail / Hold-WebGL for Star Master + Constellation (+ FlagShip re-shot) (#236).
- [Batch 5 brick and hoops acceptance](cockpit-ship-stage-p1b-batch5-acceptance.md) — Pass / Fail / Hold-WebGL for Tholian Sentinel + Interdictor Cruiser (#240).
- [Fleet order](cockpit-ship-stage-p1b-fleet-order.md) — Batch sequence for the other 15 player hulls, one batch at a time, after the spike merges.
- [Next hulls](cockpit-ship-stage-p1b-next-hulls.md) — Mesh contract for Scout Marauder, Merchant Freighter, BattleShip, and Corporate FlagShip.
- [Batch 1 readiness](cockpit-ship-stage-p1b-batch1-readiness.md) — Gate status only: Escape Pod and T'Khasi Orion stay behind the live cut 2 (#255).
- [Batch 1 remainder](cockpit-ship-stage-p1b-batch1-remainder.md) — Escape Pod and T'Khasi Orion; Scout re-shot.
- [Batch 2 haulers](cockpit-ship-stage-p1b-batch2-haulers.md) — Mesh contract for CargoTran, Colonial Transport, and Taurean Mule, after that four-hull wave.
- [Batch 3 guns](cockpit-ship-stage-p1b-batch3.md) — Gun wave: Missile Frigate and Havoc GunStar; BattleShip re-shot.
- [Batch 4 dish and X](cockpit-ship-stage-p1b-batch4.md) — Star Master and Constellation; FlagShip re-shot.
- [Batch 5 brick and hoops](cockpit-ship-stage-p1b-batch5.md) — Tholian Sentinel and Interdictor Cruiser.

## P2

- [P2 readiness](cockpit-ship-stage-p2-readiness.md) — Gate status only: P2 FX and the left viewport stay behind the cut-2 product pass and the remaining P1b product passes (#241). Refreshed onto `f7176883` (#248).
- [P2 wire](cockpit-ship-stage-p2-wire.md) — Product checklist that plays the six FX states on the ship stage and retires the left viewport.

## P3

- [P3 layout](cockpit-ship-stage-p3-layout.md) — Product checklist for ship about 55–60% on the left, the nav map about 35% on the right, and dropping the 140px `#shipSvg` cap. Refreshed onto `62766208` (#250).

## COMMS

Related cockpit hygiene, outside this pack. COMMS readers start at [comms-feed-v1.md](comms-feed-v1.md): the card is player channels only, and trade failures stay on the LOG.
