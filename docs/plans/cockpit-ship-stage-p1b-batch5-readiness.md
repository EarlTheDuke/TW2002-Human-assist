# P1b batch-5 readiness — Tholian Sentinel and Interdictor Cruiser

The stills inventory is [stills/README.md](stills/README.md) (#344), directory [p1b-batch5-brick](stills/p1b-batch5-brick/).

Gate status only. Docs only. Branch tip: `feature/grokbot-player` @ `30b9e7fa` (#373). #373 refreshed the [batch-4 readiness](cockpit-ship-stage-p1b-batch4-readiness.md) note on parent `d063a95a` (#372). #372 refreshed the [stills inventory](stills/README.md) so the batch-3 guns row is measured and Pass, on parent `e82c958b` (#371). #340 (`75997134`) opened the [batch 5 brick product](cockpit-ship-stage-p1b-batch5-brick-product.md) stills scaffold and the [p1b-batch5-brick](stills/p1b-batch5-brick/) directory. This note does not move the recorded tip. This note records that the batch-3 Pass cleared the guns. Star Master and Constellation are the live product cut ahead. That product is in flight. On this tip those two meshes are still `fleet-glass-v1`. Tholian Sentinel and Interdictor Cruiser wait behind the batch-4 Pass. This note does not stamp Pass.

Sticky order stays P1 SVG, then P1b, then P2, then P3. Finder: [cockpit-ship-stage-INDEX.md](cockpit-ship-stage-INDEX.md). Standing queue: [COMMANDER_NEXT.md](COMMANDER_NEXT.md). Product order: [four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) (#219). Fleet sequence: [fleet order](cockpit-ship-stage-p1b-fleet-order.md) (#196, `281680c5`).

## Landed

Cuts through the gun wave have landed and passed.

- Cut 1, Scout Marauder and Merchant Freighter, landed in #238 (`54051577`). Pass (#244, `f057cac7`).
- Cut 2, BattleShip and Corporate FlagShip, landed in #268 (`b0e96881`). Pass (#271, `8a13628c`).
- Batch 1, Escape Pod and T'Khasi Orion, landed in #293 (`186aaf85`). Pass (#296, `efcb49ee`).
- Batch 2, CargoTran, Colonial Transport, and Taurean Mule, landed in #312 (`51acad6f`). Pass (#315, `fcbf2621`).
- Batch 3, Missile Frigate and Havoc GunStar, landed in #363 (`5ebec08f`) on the shared SVG path. Pass (#370, `223dacfa`) on [batch 3 acceptance](cockpit-ship-stage-p1b-batch3-acceptance.md). The [stills inventory](stills/README.md) (#372, `d063a95a`) records [p1b-batch3-guns](stills/p1b-batch3-guns/) as measured and Pass: Missile Frigate 283 faces, Havoc GunStar 261 faces, PNGs in that directory.

WebGL stays closed. The [P1 pass](cockpit-ship-stage-p1-pass.md) (#220, `04d83e5e`) closed the off-ramp, and those Pass stamps left it closed.

## Cuts ahead

Star Master (`star_master`) and Constellation (`constellation`) are the live product cut (batch 4). That product is in flight. On this tip both meshes are still `fleet-glass-v1`. They leave that look when the product PR lands. The next Pass waits on measured product. Prior gate: [batch 4 readiness](cockpit-ship-stage-p1b-batch4-readiness.md) (#373, `30b9e7fa`). Read-test: [batch 4 acceptance](cockpit-ship-stage-p1b-batch4-acceptance.md) (#236, `3798d2aa`). Looks: [batch 4 dish and X](cockpit-ship-stage-p1b-batch4.md) (#212, `d39a3ab7`). Product stills scaffold: [batch 4 dish product](cockpit-ship-stage-p1b-batch4-dish-product.md) (#339, `c01ebb2f`). Stills directory: [p1b-batch4-dish](stills/p1b-batch4-dish/). The scaffold does not stamp Pass. The [stills inventory](stills/README.md) still lists that directory as a TBD scaffold with no PNG. One cut at a time. Finish the dish and the X, including the Pass stamp, then take the brick and the hoops.

## Batch-5 gate

Batch-3 Pass #370 (`223dacfa`) on product #363 (`5ebec08f`) cleared the guns. Batch 5 waits until the batch-4 dish and X (Star Master and Constellation) product lands and that acceptance is stamped Pass. Batch-4 Pass is not stamped. The next P1b product cut after that Pass is the batch-5 brick and hoops: Tholian Sentinel (`tholian_sentinel`) and Interdictor Cruiser (`interdictor_cruiser`). The brick product has not started. Product stills scaffold: [batch 5 brick product](cockpit-ship-stage-p1b-batch5-brick-product.md) (#340, `75997134`). Stills directory: [p1b-batch5-brick](stills/p1b-batch5-brick/). The scaffold does not stamp Pass.

The acceptance sheet already exists: [batch 5 acceptance](cockpit-ship-stage-p1b-batch5-acceptance.md) (#240, `c10935eb`). The mesh contract is [batch 5 brick and hoops](cockpit-ship-stage-p1b-batch5.md) (#214, `73c7269a`). The product stills scaffold is [batch 5 brick product](cockpit-ship-stage-p1b-batch5-brick-product.md) (#340, `75997134`). The stills directory is [p1b-batch5-brick](stills/p1b-batch5-brick/). This note does not replace any of those sheets, and it does not stamp Pass. The scaffold ships no PNG. Measured cells on that sheet stay awaiting product.

The dish-and-X wave is the sole editor of `web/hull-meshes.js` this wave. Tholian Sentinel and Interdictor Cruiser faces edit that file in a later PR. That product PR starts from the merge of batch 4, after the batch-4 Pass. Until that Pass, both stay on `fleet-glass-v1`. When the product PR opens, faces land through `buildHullFaces` / `projectFace`. Build order inside that later PR is Tholian Sentinel, then Interdictor Cruiser. WebGL stays the closed off-ramp.

[Fleet order](cockpit-ship-stage-p1b-fleet-order.md#batch-5--brick-and-hoops) names this cut as batch 5: Tholian Sentinel, Interdictor Cruiser, after the guns and after the dish and the X. [Four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) keeps that same sequence. P2 FX and the left-viewport retirement stay gated behind the remaining P1b Pass stamps. P3 layout stays gated behind those Passes and P2. This note does not open the wire and does not open the layout PR.
