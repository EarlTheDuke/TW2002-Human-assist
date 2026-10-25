# P1b batch-4 readiness — Star Master and Constellation

The stills inventory is [stills/README.md](stills/README.md) (#344), directory [p1b-batch4-dish](stills/p1b-batch4-dish/). #380 (`5c719360`) records that directory as product in flight, not measured, no PNG. Pass is not stamped.

Gate status only. Docs only. Branch tip: `feature/grokbot-player` @ `436bfc47` (#382). #382 refreshed the ship-stage tip sheets onto parent `9d4c972f` (#381). #381 refreshed [fleet order](cockpit-ship-stage-p1b-fleet-order.md) onto parent `5c719360` (#380) so fleet order matches this cut: guns Landed+Pass, dish in flight, Pass not stamped. #380 records the [stills inventory](stills/README.md) dish row as product in flight, not measured, no PNG. #372 (`d063a95a`) records the guns row measured and Pass. #339 (`c01ebb2f`) opened the [batch 4 dish product](cockpit-ship-stage-p1b-batch4-dish-product.md) stills scaffold and the [p1b-batch4-dish](stills/p1b-batch4-dish/) directory. This note does not move the recorded tip. This note records that the batch-3 Pass cleared the guns. Star Master and Constellation are the live product cut. That product is in flight. On this tip those two meshes are still `fleet-glass-v1`. This note does not stamp Pass.

Sticky order stays P1 SVG, then P1b, then P2, then P3. Finder: [cockpit-ship-stage-INDEX.md](cockpit-ship-stage-INDEX.md). Standing queue: [COMMANDER_NEXT.md](COMMANDER_NEXT.md). Product order: [four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) (#219). Fleet sequence: [fleet order](cockpit-ship-stage-p1b-fleet-order.md) (#196, `281680c5`), refreshed in #381 (`9d4c972f`).

## Landed

Cuts through the gun wave have landed and passed.

- Cut 1, Scout Marauder and Merchant Freighter, landed in #238 (`54051577`). Pass (#244, `f057cac7`).
- Cut 2, BattleShip and Corporate FlagShip, landed in #268 (`b0e96881`). Pass (#271, `8a13628c`).
- Batch 1, Escape Pod and T'Khasi Orion, landed in #293 (`186aaf85`). Pass (#296, `efcb49ee`).
- Batch 2, CargoTran, Colonial Transport, and Taurean Mule, landed in #312 (`51acad6f`). Pass (#315, `fcbf2621`).
- Batch 3, Missile Frigate and Havoc GunStar, landed in #363 (`5ebec08f`) on the shared SVG path. Pass (#370, `223dacfa`) on [batch 3 acceptance](cockpit-ship-stage-p1b-batch3-acceptance.md). The [stills inventory](stills/README.md) (#372, `d063a95a`) records [p1b-batch3-guns](stills/p1b-batch3-guns/) as measured and Pass: Missile Frigate 283 faces, Havoc GunStar 261 faces, PNGs in that directory.

WebGL stays closed. The [P1 pass](cockpit-ship-stage-p1-pass.md) (#220, `04d83e5e`) closed the off-ramp, and those Pass stamps left it closed.

## Cut ahead

Star Master (`star_master`) and Constellation (`constellation`) are the live product cut (batch 4). That cut is the sole editor of `web/hull-meshes.js` this wave. The dish product is in flight. On this tip both meshes are still `fleet-glass-v1`. They leave that look when the product PR lands. The next Pass waits on measured product. Read-test: [batch 4 acceptance](cockpit-ship-stage-p1b-batch4-acceptance.md) (#236, `3798d2aa`). Looks: [batch 4 dish and X](cockpit-ship-stage-p1b-batch4.md) (#212, `d39a3ab7`). Product stills scaffold: [batch 4 dish product](cockpit-ship-stage-p1b-batch4-dish-product.md) (#339, `c01ebb2f`). Stills directory: [p1b-batch4-dish](stills/p1b-batch4-dish/). The scaffold does not stamp Pass. The [stills inventory](stills/README.md) (#380, `5c719360`) records that directory as product in flight, not measured, no PNG. Pass is not stamped. One cut at a time. Finish this cut, then take the next.

## Batch-4 gate

The batch-4 dish and X is Star Master (`star_master`) and Constellation (`constellation`), judged with the Corporate FlagShip re-shot. The FlagShip mesh already landed in cut 2. This wave does not recut that tower. Product stills scaffold: [batch 4 dish product](cockpit-ship-stage-p1b-batch4-dish-product.md) (#339, `c01ebb2f`). Stills directory: [p1b-batch4-dish](stills/p1b-batch4-dish/). The scaffold does not stamp Pass.

The acceptance sheet already exists: [batch 4 acceptance](cockpit-ship-stage-p1b-batch4-acceptance.md) (#236, `3798d2aa`). The mesh contract is [batch 4 dish and X](cockpit-ship-stage-p1b-batch4.md) (#212, `d39a3ab7`). The product stills scaffold is [batch 4 dish product](cockpit-ship-stage-p1b-batch4-dish-product.md) (#339, `c01ebb2f`). The stills directory is [p1b-batch4-dish](stills/p1b-batch4-dish/). This note does not replace any of those sheets, and it does not stamp Pass. The scaffold ships no PNG. Measured cells on that sheet stay awaiting product. The next Pass waits on measured product.

Batch-3 Pass #370 (`223dacfa`) on product #363 (`5ebec08f`) cleared the guns. This gate waits only on the batch-4 product and its own Pass. Star Master and Constellation faces are the sole edit of `web/hull-meshes.js` this wave. The dish product is in flight. On this tip both stay on `fleet-glass-v1` until that product PR lands. When it lands, faces land through `buildHullFaces` / `projectFace`. Build order inside that PR is Star Master, then Constellation. WebGL stays the closed off-ramp.

[Fleet order](cockpit-ship-stage-p1b-fleet-order.md) (#196, `281680c5`), refreshed in #381 (`9d4c972f`), names this cut as batch 4: Star Master, Constellation, Corporate FlagShip, after the guns and before the brick and hoops. That refresh records guns Landed+Pass and this cut in flight. Pass is not stamped. [Four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) keeps that same sequence. P2 FX and the left-viewport retirement stay gated behind the remaining P1b Pass stamps. P3 layout stays gated behind those Passes and P2. This note does not open the wire and does not open the layout PR.

Batch 5 follows this dish and X, one cut at a time. Its acceptance sheet is already the read-test. This gate leaves that product cut waiting behind the dish Pass.
