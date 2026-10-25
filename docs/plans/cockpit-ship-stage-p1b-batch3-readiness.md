# P1b batch-3 readiness — Missile Frigate and Havoc GunStar

The stills inventory is [stills/README.md](stills/README.md) (#344), directory [p1b-batch3-guns](stills/p1b-batch3-guns/). #372 (`d063a95a`) records that directory measured and Pass.

Gate status only. Docs only. Branch tip: `feature/grokbot-player` @ `30b9e7fa` (#373). #373 refreshed the [batch-4 readiness](cockpit-ship-stage-p1b-batch4-readiness.md) on parent `d063a95a` (#372). #372 records [p1b-batch3-guns](stills/p1b-batch3-guns/) measured and Pass on the stills inventory. #337 (`d211b4e9`) opened the [batch 3 guns product](cockpit-ship-stage-p1b-batch3-guns-product.md) stills scaffold and the [p1b-batch3-guns](stills/p1b-batch3-guns/) directory. This note does not move the recorded tip. This note records that the batch-3 Pass cleared the guns. Star Master and Constellation are the live product cut. The gun wave no longer holds the sole `web/hull-meshes.js` editor slot. Meshes stay as this tip left them. This note does not stamp Pass.

Sticky order stays P1 SVG, then P1b, then P2, then P3. Finder: [cockpit-ship-stage-INDEX.md](cockpit-ship-stage-INDEX.md). Standing queue: [COMMANDER_NEXT.md](COMMANDER_NEXT.md). Product order: [four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) (#219).

## Landed

Batch 3, Missile Frigate and Havoc GunStar, has landed.

- Product meshes landed in #363 (`5ebec08f`) on the shared SVG path in `web/hull-meshes.js` (`buildHullFaces` / `projectFace`). Those two left `fleet-glass-v1`. Missile Frigate is 283 faces. Havoc GunStar is 261 faces. Measured stills: [batch 3 guns product](cockpit-ship-stage-p1b-batch3-guns-product.md). Stills directory: [p1b-batch3-guns](stills/p1b-batch3-guns/).
- Pass stamped on the [batch 3 acceptance](cockpit-ship-stage-p1b-batch3-acceptance.md) (#370, `223dacfa`).
- The [stills inventory](stills/README.md) (#372, `d063a95a`) records [p1b-batch3-guns](stills/p1b-batch3-guns/) as measured and Pass. PNGs are in that directory.

The BattleShip stays the cut-2 mesh. The gun wave re-shot it. It did not recut that wedge.

Batch 2, CargoTran, Colonial Transport, and the Taurean Mule, has landed.

- Product meshes landed in #312 (`51acad6f`) on the shared SVG path in `web/hull-meshes.js` (`buildHullFaces` / `projectFace`). Those three left `fleet-glass-v1`. Measured stills: [batch 2 haulers](cockpit-ship-stage-p1b-batch2-haulers-product.md).
- Pass stamped on the [batch 2 acceptance](cockpit-ship-stage-p1b-batch2-haulers-acceptance.md) (#315, `fcbf2621`).
- The [four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) records that batch-2 Pass.

WebGL stays closed. The [P1 pass](cockpit-ship-stage-p1-pass.md) (#220, `04d83e5e`) closed the off-ramp, and the batch-3 Pass left it closed.

## Live cut

Star Master (`star_master`) and Constellation (`constellation`) are the live product cut on the shared SVG path. That cut is the sole editor of `web/hull-meshes.js` this wave. The dish product is in flight. On this tip both meshes are still `fleet-glass-v1`. They leave that look when the product PR lands. Read-test: [batch 4 acceptance](cockpit-ship-stage-p1b-batch4-acceptance.md) (#236, `3798d2aa`). Looks: [batch 4 dish and X](cockpit-ship-stage-p1b-batch4.md) (#212, `d39a3ab7`). Product stills scaffold: [batch 4 dish product](cockpit-ship-stage-p1b-batch4-dish-product.md) (#339, `c01ebb2f`). Stills directory: [p1b-batch4-dish](stills/p1b-batch4-dish/). Gate: [batch 4 readiness](cockpit-ship-stage-p1b-batch4-readiness.md) (#373, `30b9e7fa`). The scaffold does not stamp Pass. One cut at a time. Finish this cut, then take the next.

The Corporate FlagShip stays the cut-2 mesh. This cut re-shots it. It does not recut that tower.

## Batch-3 gate

Batch-3 product #363 (`5ebec08f`) and Pass #370 (`223dacfa`) cleared this gate. The next gate is the batch-4 dish: Star Master and Constellation.

The acceptance sheet already exists: [batch 3 acceptance](cockpit-ship-stage-p1b-batch3-acceptance.md) (#235, `390e6a99`). The mesh contract is [batch 3 guns](cockpit-ship-stage-p1b-batch3.md) (#208, `d91b8e78`). The product stills are [batch 3 guns product](cockpit-ship-stage-p1b-batch3-guns-product.md) (#363, `5ebec08f`). The stills directory is [p1b-batch3-guns](stills/p1b-batch3-guns/). Product order is the [four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) (#219, `017d206e`). This note does not replace any of those sheets, and it does not stamp Pass. The [stills inventory](stills/README.md) (#372, `d063a95a`) records that directory measured and Pass.

The next gate is [batch 4 readiness](cockpit-ship-stage-p1b-batch4-readiness.md), opened in #334 (`1ce16326`) and refreshed in #373 (`30b9e7fa`). Star Master and Constellation faces are the sole edit of `web/hull-meshes.js` this wave. The gun wave no longer holds that slot. The dish product is in flight. On this tip both stay on `fleet-glass-v1` until that product PR lands. When it lands, faces land through `buildHullFaces` / `projectFace`. Build order inside that PR is Star Master, then Constellation. The dish acceptance sheet already exists: [batch 4 acceptance](cockpit-ship-stage-p1b-batch4-acceptance.md) (#236, `3798d2aa`). The mesh contract is [batch 4 dish and X](cockpit-ship-stage-p1b-batch4.md) (#212, `d39a3ab7`). The product stills scaffold is [batch 4 dish product](cockpit-ship-stage-p1b-batch4-dish-product.md) (#339, `c01ebb2f`). The stills directory is [p1b-batch4-dish](stills/p1b-batch4-dish/). The scaffold ships no PNG. Measured cells on that sheet stay awaiting product. This note does not replace any of those sheets, and it does not stamp Pass. WebGL stays the closed off-ramp.

P2 stays gated behind the remaining P1b Passes. P3 stays gated behind those Passes and P2. This note does not open the wire and does not open the layout.

Batch 5 follows the dish, one cut at a time. Its acceptance sheet is already the read-test. This gate leaves that product cut waiting behind batch 4.
