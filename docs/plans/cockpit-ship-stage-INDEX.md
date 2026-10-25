# Cockpit ship stage — sheet index

Finder for the ship-stage planning pack. Docs only. Tip: `feature/grokbot-player` @ `61422328`. The mailbox tip moved with #230 and #232; COMMANDER_NEXT may lag until its own refresh.

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
- [Cut 1 acceptance](cockpit-ship-stage-p1b-scout-freighter-acceptance.md) — Pass / Fail / Hold-WebGL read-test for cut 1 Scout Marauder + Merchant Freighter (#226).
- [Cut 2 acceptance](cockpit-ship-stage-p1b-battleship-flagship-acceptance.md) — Pass / Fail / Hold-WebGL for BattleShip + Corporate FlagShip (#227).
- [Batch 1 acceptance](cockpit-ship-stage-p1b-batch1-acceptance.md) — Pass / Fail / Hold-WebGL read-test for Escape Pod + T'Khasi Orion (#230).
- [Batch 2 haulers acceptance](cockpit-ship-stage-p1b-batch2-haulers-acceptance.md) — Pass / Fail / Hold-WebGL for CargoTran + Colonial Transport + Taurean Mule (#232).
- [Fleet order](cockpit-ship-stage-p1b-fleet-order.md) — Batch sequence for the other 15 player hulls, one batch at a time, after the spike merges.
- [Next hulls](cockpit-ship-stage-p1b-next-hulls.md) — Mesh contract for Scout Marauder, Merchant Freighter, BattleShip, and Corporate FlagShip.
- [Batch 1 remainder](cockpit-ship-stage-p1b-batch1-remainder.md) — Escape Pod and T'Khasi Orion; Scout re-shot.
- [Batch 2 haulers](cockpit-ship-stage-p1b-batch2-haulers.md) — Mesh contract for CargoTran, Colonial Transport, and Taurean Mule, after that four-hull wave.
- [Batch 3 guns](cockpit-ship-stage-p1b-batch3.md) — Gun wave: Missile Frigate and Havoc GunStar; BattleShip re-shot.
- [Batch 4 dish and X](cockpit-ship-stage-p1b-batch4.md) — Star Master and Constellation; FlagShip re-shot.
- [Batch 5 brick and hoops](cockpit-ship-stage-p1b-batch5.md) — Tholian Sentinel and Interdictor Cruiser.

## P2

- [P2 wire](cockpit-ship-stage-p2-wire.md) — Product checklist that plays the six FX states on the ship stage and retires the left viewport.

## P3

- [P3 layout](cockpit-ship-stage-p3-layout.md) — Product checklist for ship about 55–60% on the left, the nav map about 35% on the right, and dropping the 140px `#shipSvg` cap.

## COMMS

Related cockpit hygiene, outside this pack. COMMS readers start at [comms-feed-v1.md](comms-feed-v1.md): the card is player channels only, and trade failures stay on the LOG.
