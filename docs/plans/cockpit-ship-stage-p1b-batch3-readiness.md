# P1b batch-3 readiness — Missile Frigate and Havoc GunStar

The stills inventory is [stills/README.md](stills/README.md) (#344), directory [p1b-batch3-guns](stills/p1b-batch3-guns/).

Gate status only. Docs only. Branch tip: `feature/grokbot-player` @ `6df3b11c` (#332). #332 refreshed the four-hull tip to `a1f95e30`. #337 (`d211b4e9`) opened the [batch 3 guns product](cockpit-ship-stage-p1b-batch3-guns-product.md) stills scaffold and the [p1b-batch3-guns](stills/p1b-batch3-guns/) directory. This note does not move the recorded tip. This note records that the batch-2 Pass cleared the gate. Missile Frigate and Havoc GunStar are the live product cut. Meshes stay as this tip left them. This note does not stamp Pass.

Sticky order stays P1 SVG, then P1b, then P2, then P3. Finder: [cockpit-ship-stage-INDEX.md](cockpit-ship-stage-INDEX.md). Standing queue: [COMMANDER_NEXT.md](COMMANDER_NEXT.md). Product order: [four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) (#219).

## Landed

Batch 2, CargoTran, Colonial Transport, and the Taurean Mule, has landed.

- Product meshes landed in #312 (`51acad6f`) on the shared SVG path in `web/hull-meshes.js` (`buildHullFaces` / `projectFace`). Those three left `fleet-glass-v1`. Measured stills: [batch 2 haulers](cockpit-ship-stage-p1b-batch2-haulers-product.md).
- Pass stamped on the [batch 2 acceptance](cockpit-ship-stage-p1b-batch2-haulers-acceptance.md) (#315, `fcbf2621`).
- The [four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) records that batch-2 Pass.

WebGL stays closed. The [P1 pass](cockpit-ship-stage-p1-pass.md) (#220, `04d83e5e`) closed the off-ramp, and the batch-2 Pass left it closed.

## Live cut

Missile Frigate (`missile_frigate`) and Havoc GunStar (`havoc_gunstar`) are the live product cut on the shared SVG path. That cut holds `web/hull-meshes.js`. Read-test: [batch 3 acceptance](cockpit-ship-stage-p1b-batch3-acceptance.md) (#235, `390e6a99`). Looks: [batch 3 guns](cockpit-ship-stage-p1b-batch3.md) (#208, `d91b8e78`). Product stills scaffold: [batch 3 guns product](cockpit-ship-stage-p1b-batch3-guns-product.md) (#337, `d211b4e9`). Stills directory: [p1b-batch3-guns](stills/p1b-batch3-guns/). The scaffold does not stamp Pass. One cut at a time. Finish this cut, then take the next.

The BattleShip stays the cut-2 mesh. This cut re-shots it. It does not recut that wedge.

## Batch-3 gate

Batch-2 Pass #315 (`fcbf2621`) on product #312 (`51acad6f`) cleared the gate. The next P1b product cut is the gun wave: Missile Frigate and Havoc GunStar.

The acceptance sheet already exists: [batch 3 acceptance](cockpit-ship-stage-p1b-batch3-acceptance.md) (#235, `390e6a99`). The mesh contract is [batch 3 guns](cockpit-ship-stage-p1b-batch3.md) (#208, `d91b8e78`). The product stills scaffold is [batch 3 guns product](cockpit-ship-stage-p1b-batch3-guns-product.md) (#337, `d211b4e9`). The stills directory is [p1b-batch3-guns](stills/p1b-batch3-guns/). Product order is the [four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) (#219, `017d206e`). This note does not replace any of those sheets, and it does not stamp Pass. The scaffold ships no PNG. Measured cells on that sheet stay awaiting product.

Those two faces edit `web/hull-meshes.js` on the shared SVG path (`buildHullFaces` / `projectFace`). Batch 2 has merged, so the product PR starts from that merge. Until that product lands, both stay on `fleet-glass-v1`. WebGL stays the closed off-ramp.

P2 stays gated behind the remaining P1b Passes. P3 stays gated behind those Passes and P2. This note does not open the wire and does not open the layout.

Batches 4 and 5 follow this cut, one cut at a time. Their acceptance sheets are already the read-tests. This gate leaves those product cuts waiting behind batch 3.
