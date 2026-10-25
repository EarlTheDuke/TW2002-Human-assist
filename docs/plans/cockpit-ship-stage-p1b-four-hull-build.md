# Four-hull build — ship stage P1b

Parents: [P1 acceptance](cockpit-ship-stage-p1-acceptance.md), [P1 spike](cockpit-ship-stage-p1-spike.md), [next hulls](cockpit-ship-stage-p1b-next-hulls.md), [fleet order](cockpit-ship-stage-p1b-fleet-order.md).

Docs only. Tip: `feature/grokbot-player` @ `484e9fb9` (#285). P1 SVG spike passed (#215). This sheet is the product build order after that pass. Looks stay on the contracts already on this tip. #285 (`484e9fb9`) refreshed COMMANDER_NEXT through #284 (mailbox tip `a2f4d3a4`). #284 (`a2f4d3a4`) moved the INDEX tip to `d5062f20`. #283 (`d5062f20`) refreshed P2 readiness onto `ad131075`. #282 (`ad131075`) refreshed the four-hull tip to `09f5318b`. #281 (`09f5318b`) moved the INDEX tip to `41d260cf`. #279 (`41d260cf`) refreshed COMMANDER_NEXT through #280 (mailbox tip `7f6449bd`). #280 (`7f6449bd`) refreshed the P3 layout tip to `6f82b735`. #278 (`6f82b735`) refreshed the four-hull tip to `1f2fa374`. #277 (`1f2fa374`) moved the INDEX tip to `7864c720`. #276 (`7864c720`) refreshed P2 readiness onto `33db4140`. #275 (`33db4140`) refreshed the four-hull tip to `f1f94c2c`. #274 (`f1f94c2c`) refreshed COMMANDER_NEXT through #272 (mailbox tip `638a61b5`). #271 stamped Cut 2 Pass on product #268 (`b0e96881`). #270 refreshed the four-hull tip to `59f14ab0`. #264 refreshed the P3 layout tip to `d1b53755`. #265 (`e9b1e292`) moved the INDEX tip to `1487293d`. #266 refreshed P2 readiness onto `e9b1e292`. #268 landed cut 2 product (BattleShip and Corporate FlagShip). #267 refreshed COMMANDER_NEXT through #268. #269 (`59f14ab0`) moved the INDEX tip to `498d3bf4`. #263 refreshed the four-hull tip to `d1b53755`. #259 (`2b4f3c87`) moved the INDEX tip to `6b54bec5`. #260 refreshed P2 readiness onto `6b54bec5`. #261 (`8f88dc0a`) moved the INDEX tip to `489c44e3`. #262 refreshed COMMANDER_NEXT through #261. #258 refreshed the four-hull tip to `9ad2c989`. #256 (`cf8ec830`) moved the INDEX tip to `7c30c78d` and pointed at batch-1 readiness. #257 refreshed COMMANDER_NEXT through #255. #255 recorded batch-1 readiness: Escape Pod and T'Khasi Orion wait behind cut 2. #254 moved the INDEX tip to `336883dc`. #253 refreshed the four-hull tip to `1c3fd84b`. #252 moved the INDEX tip to `b95e4219`. #251 (`dbbee178`) refreshed COMMANDER_NEXT through #250. #250 refreshed the P3 layout tip to `62766208`. #249 moved the INDEX tip to `62766208`. #248 refreshed P2 readiness onto `f7176883`. Cut 1 Pass stays recorded (#246 / #244 / #238). Cut 2 product landed in #268 (`b0e96881`). Cut 2 Pass stamped in #271 (`8a13628c`). Escape Pod and T'Khasi Orion are the product cut in flight.

## Build order

Cut 1 (Scout Marauder and Merchant Freighter) product landed in #238 (`54051577`). Acceptance is Pass via #244 (`f057cac7`). Cut 2 (BattleShip and Corporate FlagShip) product landed in #268 (`b0e96881`). Acceptance is Pass via #271 (`8a13628c`). Escape Pod and T'Khasi Orion are the product cut in flight. One cut at a time. Finish the cut, then take the next.

1. Scout Marauder and Merchant Freighter. Landed in #238 (`54051577`). Acceptance Pass via #244 (`f057cac7`). Looks: [next hulls](cockpit-ship-stage-p1b-next-hulls.md).
2. BattleShip and Corporate FlagShip. Same contract. Product landed in #268 (`b0e96881`). Acceptance Pass via #271 (`8a13628c`).
3. Batch-1 remainder: Escape Pod and T'Khasi Orion. In flight, from the merge of cut 2. Looks: [batch 1 remainder](cockpit-ship-stage-p1b-batch1-remainder.md).
4. Then, per [fleet order](cockpit-ship-stage-p1b-fleet-order.md): haulers ([batch 2](cockpit-ship-stage-p1b-batch2-haulers.md)), guns ([batch 3](cockpit-ship-stage-p1b-batch3.md)), dish and X ([batch 4](cockpit-ship-stage-p1b-batch4.md)), brick and hoops ([batch 5](cockpit-ship-stage-p1b-batch5.md)).

The next-hulls sheet still lists Scout, then Freighter, then BattleShip, then FlagShip as one wave of looks. Product splits that wave into cuts 1 and 2. BattleShip and FlagShip landed in cut 2 (#268). Acceptance is Pass via #271. The gun wave and the dish-and-X wave keep them as the re-shots those sheets already name.

## Path

Shared path only: `buildHullFaces` / `projectFace`. Faces land in `web/hull-meshes.js`. WebGL stays Hold. The P1 pass left the acceptance sheet's off-ramp closed.

## Per-hull acceptance

Every hull in the cut, mirrored from [P1 acceptance](cockpit-ship-stage-p1-acceptance.md). The signature part is the one on that hull's contract.

- Read at ~140px, and at a hero crop about 55% of the deck. Name plate covered. Three-quarter pose yaw `0.82`, pitch `0.5`, and the head-on clip. A reader names the job.
- Markers 100:1, outside the hull. `n < 1` draws nothing. Otherwise `max(1, ceil(n / 100))`. Innermost world radius is the bounding sphere of every face, kit included, plus a gap. No marker screen-box intersects the silhouette.
- Shields empty keeps the accent. The bubble is absent. Scars may show. The class accent stays that colour. A full red body fails.
- Gzip budget. `web/hull-meshes.js` stays under 40 KB gzipped. The budget is cumulative across cuts. Record face counts with the cut.
- Tests. Ship-view tests that assert the 200-cap legend, and a test that pins a `fleet-glass-v1` face count or AABB for a hull in the cut, update in that same change. No engine change, no new action, no new event field.

The rest of the P1 pass list still applies: side clip, `holdWarp`, phone still, reduced-motion still, `body.cu-seat` still, legend `each marker = 100 fighters`, and the exact bay on the stat line.

## File ownership

One product Cur at a time on `web/hull-meshes.js`. Cut 1 merged in #238. Cut 2 merged in #268. The batch-1 remainder holds that file. Every later cut starts from the merge of the Cur ahead of it.

## Contracts already on tip

- [Next hulls](cockpit-ship-stage-p1b-next-hulls.md) — Scout Marauder, Merchant Freighter, BattleShip, Corporate FlagShip.
- [Batch 1 remainder](cockpit-ship-stage-p1b-batch1-remainder.md) — Escape Pod, T'Khasi Orion.
- [Batch 2 haulers](cockpit-ship-stage-p1b-batch2-haulers.md) — CargoTran, Colonial Transport, Taurean Mule.
- [Batch 3 guns](cockpit-ship-stage-p1b-batch3.md) — Missile Frigate, Havoc GunStar; BattleShip re-shot.
- [Batch 4 dish and X](cockpit-ship-stage-p1b-batch4.md) — Star Master, Constellation; FlagShip re-shot.
- [Batch 5 brick and hoops](cockpit-ship-stage-p1b-batch5.md) — Tholian Sentinel, Interdictor Cruiser.
- [Fleet order](cockpit-ship-stage-p1b-fleet-order.md) — batch sequence for the cuts after the four-hull wave.
