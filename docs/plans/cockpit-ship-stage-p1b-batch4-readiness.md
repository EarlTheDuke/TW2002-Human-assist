# P1b batch-4 readiness — Star Master and Constellation

The stills inventory is [stills/README.md](stills/README.md) (#344), directory [p1b-batch4-dish](stills/p1b-batch4-dish/). #388 (`1ee63b98`) records that directory as product landed and measured: Star Master 183 faces, Constellation 311 faces, PNGs in that directory. That inventory row does not stamp Pass.

Gate status only. Docs only. Branch tip: `feature/grokbot-player` @ `8ccb7c6f` (#389). #389 (`8ccb7c6f`) refreshed [batch-5 readiness](cockpit-ship-stage-p1b-batch5-readiness.md) onto parent `1ee63b98` (#388). That note does not stamp the dish Pass and does not start the brick product. #388 records the [stills inventory](stills/README.md) dish row as product landed and measured. #387 (`3114c994`) landed Star Master and Constellation on the shared SVG path (`buildHullFaces` / `projectFace`). Those two left `fleet-glass-v1`. #387 does not stamp Pass. #372 (`d063a95a`) records the guns row measured and Pass. This note records the dish Pass. The stamp lives on [batch 4 acceptance](cockpit-ship-stage-p1b-batch4-acceptance.md). This note does not edit the stills inventory, the batch-5 readiness sheet, or `web/hull-meshes.js`.

Sticky order stays P1 SVG, then P1b, then P2, then P3. Finder: [cockpit-ship-stage-INDEX.md](cockpit-ship-stage-INDEX.md). Standing queue: [COMMANDER_NEXT.md](COMMANDER_NEXT.md). Product order: [four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) (#219). Fleet sequence: [fleet order](cockpit-ship-stage-p1b-fleet-order.md) (#196, `281680c5`), refreshed in #386 (`3ee4e23d`) onto `0dd332dd` (#385).

## Landed

Cuts through the dish wave have landed and passed.

- Cut 1, Scout Marauder and Merchant Freighter, landed in #238 (`54051577`). Pass (#244, `f057cac7`).
- Cut 2, BattleShip and Corporate FlagShip, landed in #268 (`b0e96881`). Pass (#271, `8a13628c`).
- Batch 1, Escape Pod and T'Khasi Orion, landed in #293 (`186aaf85`). Pass (#296, `efcb49ee`).
- Batch 2, CargoTran, Colonial Transport, and Taurean Mule, landed in #312 (`51acad6f`). Pass (#315, `fcbf2621`).
- Batch 3, Missile Frigate and Havoc GunStar, landed in #363 (`5ebec08f`) on the shared SVG path. Pass (#370, `223dacfa`) on [batch 3 acceptance](cockpit-ship-stage-p1b-batch3-acceptance.md). The [stills inventory](stills/README.md) (#372, `d063a95a`) records [p1b-batch3-guns](stills/p1b-batch3-guns/) as measured and Pass: Missile Frigate 283 faces, Havoc GunStar 261 faces, PNGs in that directory.
- Batch 4, Star Master and Constellation, landed in #387 (`3114c994`) on the shared SVG path. Pass is stamped on [batch 4 acceptance](cockpit-ship-stage-p1b-batch4-acceptance.md), on the parent path of tip `8ccb7c6f` (#389). Star Master is 183 faces / 29 accent, radius 44.1, hash `7c79af13cc74372b`. Constellation is 311 faces / 91 accent, radius 64.0, hash `787b41d482d6501a`. `web/hull-meshes.js` is 14,991 bytes gzipped (level 9), under 40 KB. Measured stills: [batch 4 dish product](cockpit-ship-stage-p1b-batch4-dish-product.md). Stills directory: [p1b-batch4-dish](stills/p1b-batch4-dish/) (66 PNGs). The [stills inventory](stills/README.md) (#388, `1ee63b98`) records that directory as product landed and measured. The Corporate FlagShip stays the cut-2 mesh (210 faces). This wave re-shot it. It did not recut that tower.

WebGL stays closed. The [P1 pass](cockpit-ship-stage-p1-pass.md) (#220, `04d83e5e`) closed the off-ramp, and those Pass stamps left it closed.

## Cut ahead

Batch 5, Tholian Sentinel (`tholian_sentinel`) and Interdictor Cruiser (`interdictor_cruiser`), is unblocked for product sequencing. The dish Pass is the gate that wave was waiting on. Those two stay on `fleet-glass-v1` until their own product PR. This note does not start that product and does not edit [batch-5 readiness](cockpit-ship-stage-p1b-batch5-readiness.md). One cut at a time. P2 stays behind the brick Pass. Sticky order is this Pass, then batch 5, then P2.

## Batch-4 gate

The batch-4 dish and X is Star Master (`star_master`) and Constellation (`constellation`), judged with the Corporate FlagShip re-shot. The FlagShip mesh already landed in cut 2. This wave did not recut that tower. Product: [batch 4 dish product](cockpit-ship-stage-p1b-batch4-dish-product.md) (#387, `3114c994`). Stills directory: [p1b-batch4-dish](stills/p1b-batch4-dish/).

The acceptance sheet stamps Pass: [batch 4 acceptance](cockpit-ship-stage-p1b-batch4-acceptance.md). The mesh contract is [batch 4 dish and X](cockpit-ship-stage-p1b-batch4.md) (#212, `d39a3ab7`). The measurement sheet is [batch 4 dish product](cockpit-ship-stage-p1b-batch4-dish-product.md) (#387, `3114c994`). The stills directory is [p1b-batch4-dish](stills/p1b-batch4-dish/). This note does not replace any of those sheets. The stamp lives on the acceptance sheet. This readiness note records it.

Batch-3 Pass #370 (`223dacfa`) on product #363 (`5ebec08f`) cleared the guns. Batch-4 product #387 (`3114c994`) and the acceptance Pass on tip `8ccb7c6f` (#389) clear this gate. Star Master and Constellation faces landed through `buildHullFaces` / `projectFace`. WebGL stays the closed off-ramp.

[Fleet order](cockpit-ship-stage-p1b-fleet-order.md) (#196, `281680c5`), refreshed in #386 (`3ee4e23d`) onto `0dd332dd` (#385), names this cut as batch 4: Star Master, Constellation, Corporate FlagShip, after the guns and before the brick and hoops. That refresh recorded the dish in flight. This note does not edit that sheet. [Four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) keeps the same sequence and is not edited here. P2 FX and the left-viewport retirement stay gated behind the batch-5 Pass. P3 layout stays gated behind that Pass and P2. This note does not open the wire and does not open the layout PR.

Batch 5 follows this dish and X, one cut at a time. Its acceptance sheet is already the read-test. This Pass unblocks that product sequence. This gate does not open the brick product.
