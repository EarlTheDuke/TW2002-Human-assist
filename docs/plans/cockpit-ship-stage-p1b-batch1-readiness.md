# P1b batch-1 readiness — Escape Pod and T'Khasi Orion

Gate status only. Docs only. Branch tip: `feature/grokbot-player` @ `1c3fd84b` (#252). #252 moved the finder tip to `b95e4219`. This note records the wait for the next P1b product cut. Meshes stay as this tip left them.

Sticky order stays P1 SVG, then P1b, then P2, then P3. Finder: [cockpit-ship-stage-INDEX.md](cockpit-ship-stage-INDEX.md). Standing queue: [COMMANDER_NEXT.md](COMMANDER_NEXT.md). Product order: [four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) (#219).

## Landed

Cut 1, Scout Marauder and Merchant Freighter, has landed.

- Product meshes landed in #238 (`54051577`) on the shared SVG path in `web/hull-meshes.js` (`buildHullFaces` / `projectFace`). Measured stills: [Scout and Freighter](cockpit-ship-stage-p1b-scout-freighter.md).
- Pass stamped on the [Scout and Freighter acceptance](cockpit-ship-stage-p1b-scout-freighter-acceptance.md) (#244, `f057cac7`).
- #246 (`f7176883`) recorded that Cut 1 Pass on the four-hull build order.

WebGL stays closed. The [P1 pass](cockpit-ship-stage-p1-pass.md) (#220, `04d83e5e`) closed the off-ramp, and the Cut 1 Pass left it closed.

## Live cut

BattleShip and Corporate FlagShip are the live product cut (cut 2). That cut holds `web/hull-meshes.js`. Read-test: [cut 2 acceptance](cockpit-ship-stage-p1b-battleship-flagship-acceptance.md) (#227, `d8ff7447`). Looks: [next hulls](cockpit-ship-stage-p1b-next-hulls.md). One cut at a time. Finish cut 2, then take the next.

## Batch-1 gate

The next P1b product cut after BattleShip and Corporate FlagShip is the batch-1 remainder: Escape Pod (`escape_pod`) and T'Khasi Orion (`tkhasi_orion`).

The acceptance sheet already exists: [batch 1 acceptance](cockpit-ship-stage-p1b-batch1-acceptance.md) (#230, `1b226a70`). The mesh contract is [batch 1 remainder](cockpit-ship-stage-p1b-batch1-remainder.md) (#216, `3765f609`). This note does not replace either sheet.

Batch-1 product waits behind cut 2 on that same shared SVG path. Escape Pod and T'Khasi Orion faces edit `web/hull-meshes.js`, and cut 2 edits it too. The product PR for those two hulls starts from the merge of cut 2. Until that merge, both stay on `fleet-glass-v1`. When the product PR opens, faces land through `buildHullFaces` / `projectFace`. WebGL stays the closed off-ramp.

Batches 2–5 follow this remainder, one cut at a time. Their acceptance sheets are already the read-tests. This gate leaves those product cuts waiting behind batch 1.
