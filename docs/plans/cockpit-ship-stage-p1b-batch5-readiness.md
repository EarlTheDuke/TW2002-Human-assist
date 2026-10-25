# P1b batch-5 readiness — Tholian Sentinel and Interdictor Cruiser

Gate status only. Docs only. Branch tip: `feature/grokbot-player` @ `1ce16326` (#334). #334 landed the [batch-4 readiness](cockpit-ship-stage-p1b-batch4-readiness.md) note on parent `46529081` (#333). #333 landed the [batch-3 readiness](cockpit-ship-stage-p1b-batch3-readiness.md) note on parent `6df3b11c` (#332). This note records the wait for the brick and the hoops. Meshes stay as this tip left them. This note does not stamp Pass.

Sticky order stays P1 SVG, then P1b, then P2, then P3. Finder: [cockpit-ship-stage-INDEX.md](cockpit-ship-stage-INDEX.md). Standing queue: [COMMANDER_NEXT.md](COMMANDER_NEXT.md). Product order: [four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) (#219). Fleet sequence: [fleet order](cockpit-ship-stage-p1b-fleet-order.md) (#196, `281680c5`).

## Landed

Cuts through the hauler wave have landed and passed.

- Cut 1, Scout Marauder and Merchant Freighter, landed in #238 (`54051577`). Pass (#244, `f057cac7`).
- Cut 2, BattleShip and Corporate FlagShip, landed in #268 (`b0e96881`). Pass (#271, `8a13628c`).
- Batch 1, Escape Pod and T'Khasi Orion, landed in #293 (`186aaf85`). Pass (#296, `efcb49ee`).
- Batch 2, CargoTran, Colonial Transport, and Taurean Mule, landed in #312 (`51acad6f`). Pass (#315, `fcbf2621`).

WebGL stays closed. The [P1 pass](cockpit-ship-stage-p1-pass.md) (#220, `04d83e5e`) closed the off-ramp, and those Pass stamps left it closed.

## Cuts ahead

Missile Frigate and Havoc GunStar are the live product cut (batch 3). That cut holds `web/hull-meshes.js`. Prior gate: [batch 3 readiness](cockpit-ship-stage-p1b-batch3-readiness.md) (#333, `46529081`). Read-test: [batch 3 acceptance](cockpit-ship-stage-p1b-batch3-acceptance.md) (#235, `390e6a99`). Looks: [batch 3 guns](cockpit-ship-stage-p1b-batch3.md) (#208, `d91b8e78`). Those two hulls have not landed on this tip, and that acceptance is not stamped Pass.

Star Master and Constellation are the product cut after the guns (batch 4). Prior gate: [batch 4 readiness](cockpit-ship-stage-p1b-batch4-readiness.md) (#334, `1ce16326`). Read-test: [batch 4 acceptance](cockpit-ship-stage-p1b-batch4-acceptance.md) (#236, `3798d2aa`). Looks: [batch 4 dish and X](cockpit-ship-stage-p1b-batch4.md) (#212, `d39a3ab7`). Those two hulls have not landed on this tip, and that acceptance is not stamped Pass. One cut at a time. Finish the guns, including the Pass stamp, then the dish and the X, including the Pass stamp, then take the brick and the hoops.

## Batch-5 gate

Batch 5 waits until the batch-3 guns (Missile Frigate and Havoc GunStar) product lands and that acceptance is stamped Pass, and until the batch-4 dish and X (Star Master and Constellation) product lands and that acceptance is stamped Pass. The next P1b product cut after those two Pass stamps is the batch-5 brick and hoops: Tholian Sentinel (`tholian_sentinel`) and Interdictor Cruiser (`interdictor_cruiser`).

The acceptance sheet already exists: [batch 5 acceptance](cockpit-ship-stage-p1b-batch5-acceptance.md) (#240, `c10935eb`). The mesh contract is [batch 5 brick and hoops](cockpit-ship-stage-p1b-batch5.md) (#214, `73c7269a`). This note does not replace either sheet. It does not stamp Pass.

Tholian Sentinel and Interdictor Cruiser faces edit `web/hull-meshes.js`, and the gun wave and the dish-and-X wave edit it too. The product PR for those two hulls starts from the merge of batch 4, after the batch-3 Pass and the batch-4 Pass. Until both of those Pass stamps, both stay on `fleet-glass-v1`. When the product PR opens, faces land through `buildHullFaces` / `projectFace`. Build order inside that later PR is Tholian Sentinel, then Interdictor Cruiser. WebGL stays the closed off-ramp.

[Fleet order](cockpit-ship-stage-p1b-fleet-order.md#batch-5--brick-and-hoops) names this cut as batch 5: Tholian Sentinel, Interdictor Cruiser, after the guns and after the dish and the X. [Four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) keeps that same sequence after the hauler Pass. P2 FX and the left-viewport retirement stay gated behind the remaining P1b Pass stamps. P3 layout stays gated behind those Passes and P2. This note does not open the wire and does not open the layout PR.
