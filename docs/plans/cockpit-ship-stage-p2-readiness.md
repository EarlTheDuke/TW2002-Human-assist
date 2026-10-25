# P2 readiness — ship stage

Gate status only. Docs only. Branch tip: `feature/grokbot-player` @ `6b54bec5` (#258). #258 refreshed the four-hull tip to `9ad2c989`. #257 refreshed COMMANDER_NEXT through #255. #256 (`cf8ec830`) moved the finder tip to `7c30c78d` and pointed at batch-1 readiness. #255 (`7c30c78d`) gated batch-1 readiness behind the live cut 2. Cut 1 Pass landed (#246 / #244 / #238). BattleShip and Corporate FlagShip remain the live product cut. P2 stays behind that cut-2 pass and the remaining P1b product. WebGL stays closed.

Sticky order stays P1 SVG, then P1b, then P2, then P3. Finder: [cockpit-ship-stage-INDEX.md](cockpit-ship-stage-INDEX.md). Standing queue: [COMMANDER_NEXT.md](COMMANDER_NEXT.md). The P2 product checklist on this tip is [cockpit-ship-stage-p2-wire.md](cockpit-ship-stage-p2-wire.md) (#195). `docs/plans/` has that wire checklist. It does not contain `cockpit-ship-stage-p2.md`.

Triggers, pictures, and the viewport move stay on the wire and in the [P0 pack](cockpit-ship-stage-p0.md). This note adds none of them.

## Acceptance sheets on the tip

P1b read-tests for cuts 1–2 and batches 1–5 are on the tip. #237 listed batch 3 and batch 4 on the INDEX. #242 listed the batch-5 acceptance (#240, `c10935eb`). The sheets are the read-tests. Meshes still ahead of this tip stay on the product queue.

- Cut 1, Scout Marauder and Merchant Freighter — [acceptance](cockpit-ship-stage-p1b-scout-freighter-acceptance.md) (#226, `36b9059d`). Pass (#244, `f057cac7`). Product meshes landed in #238 (`54051577`). Measured stills: [Scout and Freighter](cockpit-ship-stage-p1b-scout-freighter.md).
- Cut 2, BattleShip and Corporate FlagShip — [acceptance](cockpit-ship-stage-p1b-battleship-flagship-acceptance.md) (#227, `d8ff7447`).
- Batch 1, Escape Pod and T'Khasi Orion — [acceptance](cockpit-ship-stage-p1b-batch1-acceptance.md) (#230, `1b226a70`).
- Batch 2, CargoTran, Colonial Transport, and Taurean Mule — [acceptance](cockpit-ship-stage-p1b-batch2-haulers-acceptance.md) (#232, `61422328`).
- Batch 3, Missile Frigate and Havoc GunStar — [acceptance](cockpit-ship-stage-p1b-batch3-acceptance.md) (#235, `390e6a99`).
- Batch 4, Star Master and Constellation, plus the FlagShip re-shot — [acceptance](cockpit-ship-stage-p1b-batch4-acceptance.md) (#236, `3798d2aa`).
- Batch 5, Tholian Sentinel and Interdictor Cruiser — [acceptance](cockpit-ship-stage-p1b-batch5-acceptance.md) (#240, `c10935eb`). Contract: [batch 5](cockpit-ship-stage-p1b-batch5.md).

INDEX rows: cuts 1–2 in #228 (`d575a9e6`), batches 1–2 in #233 (`d01d56a5`), batches 3–4 in #237 (`0eeadf5d`), batch 5 in #242 (`0ab0084f`). #238 added the Scout and Freighter stills row on that finder. #243 (`a335998e`) moved the finder tip to `f057cac7` and noted the Scout and Freighter Pass (#244).

## Product in flight

Cut 1 product landed in #238 (`54051577`). The Scout and Freighter acceptance is Pass (#244, `f057cac7`). Scout Marauder and Merchant Freighter are on the shared SVG path in `web/hull-meshes.js` (`buildHullFaces` / `projectFace`). WebGL stays closed.

BattleShip and Corporate FlagShip remain the live product cut. COMMANDER_NEXT next-Dev item 1 names that cut, just relaunched. The [Scout and Freighter](cockpit-ship-stage-p1b-scout-freighter.md) note leaves both on `fleet-glass-v1` until cut 2 lands. Order: [four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) (#219). #246 (`f7176883`) recorded the Cut 1 Pass on that order. #258 (`6b54bec5`) refreshed that order's tip to `9ad2c989`. Looks: [next hulls](cockpit-ship-stage-p1b-next-hulls.md). The batch-1 remainder and batches 2–5 follow, one cut at a time. #255 (`7c30c78d`) gated [batch-1 readiness](cockpit-ship-stage-p1b-batch1-readiness.md) behind that cut. Escape Pod and T'Khasi Orion stay on `fleet-glass-v1` until cut 2 merges. That gate does not open batch-1 product.

The P1 SVG spike has passed (#215, `9d29349a`). Pass record: [P1 pass](cockpit-ship-stage-p1-pass.md) (#220). Stamp: [P1 acceptance](cockpit-ship-stage-p1-acceptance.md) (#222).

## P2 gate

P2 FX and the left-viewport retirement stay behind the cut-2 product pass (BattleShip and Corporate FlagShip), and behind the remaining P1b product in the standing order. The cut-1 Pass (#244) does not open the wire. #255 (`7c30c78d`) gated batch-1 readiness behind cut 2. That gate does not open the wire. The acceptance sheets above are the read-tests. Landing them does not open the wire. COMMANDER_NEXT next-Dev item 3 starts the P2 product PR after that read bar, from the wire checklist, on `feature/grokbot-player`. WebGL stays closed.

The wire checklist still records its original wait, the P1 spike. The order to follow is the standing one: P1 SVG, then the P1b product passes, then P2, then P3 ([P3 layout](cockpit-ship-stage-p3-layout.md)). A cut that opens the WebGL off-ramp stops P2, which the wire already requires.
