# P1b batch-4 readiness — Star Master and Constellation

Gate status only. Docs only. Branch tip: `feature/grokbot-player` @ `46529081` (#333). #333 landed the [batch-3 readiness](cockpit-ship-stage-p1b-batch3-readiness.md) note on parent `6df3b11c` (#332). #332 refreshed the four-hull tip to `a1f95e30`. This note records the wait for the dish and the X. Meshes stay as this tip left them. This note does not stamp Pass.

Sticky order stays P1 SVG, then P1b, then P2, then P3. Finder: [cockpit-ship-stage-INDEX.md](cockpit-ship-stage-INDEX.md). Standing queue: [COMMANDER_NEXT.md](COMMANDER_NEXT.md). Product order: [four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) (#219). Fleet sequence: [fleet order](cockpit-ship-stage-p1b-fleet-order.md) (#196, `281680c5`).

## Landed

Cuts through the hauler wave have landed and passed.

- Cut 1, Scout Marauder and Merchant Freighter, landed in #238 (`54051577`). Pass (#244, `f057cac7`).
- Cut 2, BattleShip and Corporate FlagShip, landed in #268 (`b0e96881`). Pass (#271, `8a13628c`).
- Batch 1, Escape Pod and T'Khasi Orion, landed in #293 (`186aaf85`). Pass (#296, `efcb49ee`).
- Batch 2, CargoTran, Colonial Transport, and Taurean Mule, landed in #312 (`51acad6f`). Pass (#315, `fcbf2621`).

WebGL stays closed. The [P1 pass](cockpit-ship-stage-p1-pass.md) (#220, `04d83e5e`) closed the off-ramp, and those Pass stamps left it closed.

## Cut ahead

Missile Frigate and Havoc GunStar are the live product cut (batch 3). That cut holds `web/hull-meshes.js`. Gate: [batch 3 readiness](cockpit-ship-stage-p1b-batch3-readiness.md) (#333, `46529081`). Read-test: [batch 3 acceptance](cockpit-ship-stage-p1b-batch3-acceptance.md) (#235, `390e6a99`). Looks: [batch 3 guns](cockpit-ship-stage-p1b-batch3.md) (#208, `d91b8e78`). Those two hulls have not landed on this tip, and that acceptance is not stamped Pass. One cut at a time. Finish the guns, including the Pass stamp, then take the next.

## Batch-4 gate

The next P1b product cut after Missile Frigate and Havoc GunStar is the batch-4 dish and X: Star Master (`star_master`) and Constellation (`constellation`), judged with the Corporate FlagShip re-shot. The FlagShip mesh already landed in cut 2. This wave does not recut that tower.

The acceptance sheet already exists: [batch 4 acceptance](cockpit-ship-stage-p1b-batch4-acceptance.md) (#236, `3798d2aa`). The mesh contract is [batch 4 dish and X](cockpit-ship-stage-p1b-batch4.md) (#212, `d39a3ab7`). This note does not replace either sheet. It does not stamp Pass.

Batch-4 product waits until the batch-3 guns (Missile Frigate and Havoc GunStar) product lands and that acceptance is stamped Pass. Star Master and Constellation faces edit `web/hull-meshes.js`, and the gun wave edits it too. The product PR for those two hulls starts from the merge of batch 3, after the Pass stamp. Until that Pass, both stay on `fleet-glass-v1`. When the product PR opens, faces land through `buildHullFaces` / `projectFace`. Build order inside that later PR is Star Master, then Constellation. WebGL stays the closed off-ramp.

[Fleet order](cockpit-ship-stage-p1b-fleet-order.md) names this cut as batch 4: Star Master, Constellation, Corporate FlagShip, after the guns and before the brick and hoops. [Four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) keeps that same sequence after the hauler Pass. P2 FX and the left-viewport retirement stay gated behind the remaining P1b Pass stamps. P3 layout stays gated behind those Passes and P2. This note does not open the wire and does not open the layout PR.

Batch 5 follows this dish and X, one cut at a time. Its acceptance sheet is already the read-test. This gate leaves that product cut waiting behind batch 4.
