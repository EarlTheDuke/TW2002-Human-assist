# P1b acceptance — CargoTran, Colonial Transport, and Taurean Mule

Read-test for the batch-2 hauler wave. Docs only. Tip surveyed: `feature/grokbot-player` @ `d575a9e6`.

Taken from these sheets, which this file does not replace:

- [Batch 2 haulers](cockpit-ship-stage-p1b-batch2-haulers.md) — the mesh contract for this wave. Spine, belly tanks, saddle, accents, and the numbered checks live there.
- [Four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) — product order. Cut 1 is Scout Marauder and Merchant Freighter. Cut 2 is BattleShip and Corporate FlagShip. This wave waits until both have passed.
- [P1 acceptance](cockpit-ship-stage-p1-acceptance.md) — the Pass / Fail / Hold-WebGL shape this wave mirrors.
- [P1 pass](cockpit-ship-stage-p1-pass.md) — the bar Merchant Cruiser and Imperial StarShip already cleared. WebGL stays the closed off-ramp.
- [Fighter marker math](cockpit-ship-stage-marker-math.md) — the shared 100:1 count.

Scope is CargoTran (`cargotran`, kit `spine`), Colonial Transport (`colonial_transport`, kit `cargo`, the belly tanks), and Taurean Mule (`taurean_mule`, kit `saddle`). [Fleet order](cockpit-ship-stage-p1b-fleet-order.md) names these three as batch 2 and judges the trio together. One shared mesh, shaded SVG, through `buildHullFaces` / `projectFace`. Looks stay on the batch-2 contract. Section token stays `box`. Merchant Cruiser and Imperial StarShip stay as the P1 pass left them. Scout Marauder, Merchant Freighter, BattleShip, and Corporate FlagShip are the four-hull wave. This sheet does not restate their looks and does not accept those cuts. Every other hull stays on `fleet-glass-v1`.

The [P1 pass](cockpit-ship-stage-p1-pass.md) already cleared this bar for the Merchant and the Imperial, on the shared SVG path (`#215`, `9d29349a`). Gzip there is 8,673 bytes (level 9). Drift at 500 markers and a static frame at 1,000 markers both held 16 ms. Hold-WebGL stays closed unless this wave fails one of the same three off-ramps.

Cover the name plate for every read below. Look at the current ~140px panel and at a hero crop about 55% of the deck. The crop is a read of the mesh. The layout split stays P3.

The held three-quarter pose is yaw `0.82`, pitch `0.5`, which `shipPose` already uses when motion is held ([FX sheet](cockpit-ship-stage-p0-fx.md)). Head-on is the warp clip camera `headon`.

## Launch

Product for this wave waits until the four-hull wave has merged and passed. Cut 1 is Scout Marauder and Merchant Freighter ([cut 1 acceptance](cockpit-ship-stage-p1b-scout-freighter-acceptance.md)). Cut 2 is BattleShip and Corporate FlagShip ([cut 2 acceptance](cockpit-ship-stage-p1b-battleship-flagship-acceptance.md)). The [P1 pass](cockpit-ship-stage-p1-pass.md) is already in. The [hauler contract](cockpit-ship-stage-p1b-batch2-haulers.md#implement-after-p1-merges-and-after-the-four-hull-wave) names the same gate: the Freighter's cheeks have to be on screen before the spine, the cabin, and the saddle are cut. Both cuts edit `web/hull-meshes.js`. Opening this wave while either cut is still in flight thrashes that file. This sheet is the read-test checklist for the later product PR. It is not the launch.

Build order inside that later PR is CargoTran, then Colonial Transport, then Taurean Mule. The trio is judged together. The [batch-1 remainder](cockpit-ship-stage-p1b-batch1-remainder.md) (Escape Pod, T'Khasi Orion) is its own cut on the [four-hull build](cockpit-ship-stage-p1b-four-hull-build.md#build-order). This sheet does not accept that cut.

## Three-quarter

Pose: yaw `0.82`, pitch `0.5`. Repeat at shields 0 and shields full, at both sizes. The numbered checks are the batch-2 three-quarter lists for these three hulls.

CargoTran. A bulk hauler. Section `box`, and flat. A long low deck, longer than the Merchant Freighter, with a girder on its back. The girder is a ridge, taller than the deck skin and narrower than the beam. It runs most of the length and stands proud. Two engines sit low in the tail, inside the beam, under the line of the spine. Kit: `spine`. The `pods` detail token on `SHIPS` is sausage vocabulary. The signature stays the spine. A reader says cargo ship. Four markers are not a fleet, so the girder carries the job. Against the Freighter, the pair is a long dorsal girder versus short cheeks and a broad face. Against the Merchant the P1 pass already cleared, the pair is a flat deck versus a deep keel and shoulder pods. A short broad face fails. A deep underside keel fails. A cabin-port row as the tell fails. A local hump with rear panniers fails.

Colonial Transport. A slow colonist. Section `box`, and tall. A fat box, high for its length, a row of warm-white cabin ports along the flank, two belly tanks under the box. The tanks are rounder and lower than a keel, and they break the underside. Two engines sit in the tail, inside the box width, above the tank line, and they stay smaller than the tanks. Kit: `cargo` (the belly tanks). The tanks hang under the hull. A reader says a transport full of people, unwilling to turn. Two markers are not a fleet. Against the Freighter, the pair is a tall cabin box versus a short wide face. Against the Merchant, belly tanks under a box versus one keel on an arrow. Against the CargoTran, a tall cabin versus a long spine. The Tholian Sentinel is a later wave: a short plated brick, with no belly tanks and no cabin row as the main shape. This box does not pick up those slabs.

Taurean Mule. A beast of burden. Section `box`, and low. A saddle: the hull stays close to the centerline, one cargo pack sits on the back as a local hump amidships, and two panniers hang at the rear corners. The hump stops short of the nose and the tail. The panniers sit aft, lower than the pack, and they break the tail outline. Two engines sit between the panniers and stay inside that span. Kit: `saddle`. The panniers belong to the saddle. A reader says mule. Three markers do not replace the pack. Against the Freighter, the pair is a hump and rear panniers versus cheek tanks. Against the Merchant, a dorsal pack versus a ventral keel. Against the CargoTran, a local hump versus a full-length girder. Against the Colonial, a low saddle versus a tall cabin. A tall cabin fails. A short face as wide as the ship is long fails. A girder the length of the deck fails. A deep keel fails.

With the name covered, a reader says cargo ship for the CargoTran, colonist transport for the Colonial, and mule for the Mule. Inside this wave the trio is a long girder versus a tall cabin with belly tanks versus a low saddle.

The [wave read](cockpit-ship-stage-p1b-batch2-haulers.md#wave-read-test) is the subset this wave can get wrong while cutting the three faces, with the Merchant and the Freighter already on screen from earlier waves.

| Pair | What keeps them apart |
| --- | --- |
| CargoTran / Merchant Freighter | A long dorsal girder versus short cheeks and a broad face. |
| CargoTran / Merchant Cruiser | A girder on a flat deck versus a deep keel and shoulder pods. |
| Colonial / Merchant Freighter | A tall cabin box versus a short wide face. |
| Colonial / Merchant Cruiser | Belly tanks under a box versus one keel on an arrow. |
| Colonial / CargoTran | Tall cabin box versus long spine. |
| Mule / Merchant Freighter | A hump and rear panniers versus cheek tanks. |
| Mule / Merchant Cruiser | A dorsal pack versus a ventral keel. |
| Mule / CargoTran | A local hump versus a full-length girder. |
| Mule / Colonial | A low saddle versus a tall cabin. |
| Colonial / Tholian Sentinel | A tall cabin with belly tanks and a port row versus a short plated brick. The Sentinel is not in this wave. The cabin must not pick up its slabs. |

## Head-on

One existing clip per hull. Side camera and head-on camera. The kit still reads in both. A part that only exists in the three-quarter view is not a signature. `holdWarp` still pauses a frame. The head-on camera is the warp clip camera `headon`. The numbered checks are the batch-2 head-on lists.

CargoTran. A low face. A narrow ridge on the centerline is the high point. The ridge is a girder. Two engine mouths sit low, inside the beam. A cheek-tank pair, a deep keel under the nose, or a shoulder-pod pair fails the frame.

Colonial Transport. A tall face. Height beats beam. Two tank bodies sit under the box and are the low outer masses. Two engine mouths sit inside that span, above the tanks. A short wide cheek plate, a thin wedge with one keel, or a nearly square armor brick fails the frame.

Taurean Mule. A low face with one bump on the centerline. The bump is a pack, wider than a girder and shorter than a cabin stack. Two engine mouths sit low, inside the beam. The panniers, when the tail is in frame, are the outer rear masses and they wear `#d7b48a`. A shoulder-pod pair, a belly-tank pair under a tall box, or a cheek plate that sets the whole beam fails the frame.

## Accent

Dark blue-grey metal on all three hulls. The accent is a stripe, a canopy edge, and the kit. Canopy glass is a cool white mixed with the accent. Port glass on the CargoTran is a dim warm white, so it stays off the yellow. Port glass on the Colonial is a warm white, and the port row reads as cabins at ~140px. The Mule's flank stays quiet. A cabin-port row on the Mule is the Colonial's tell. Idle engines are a short cyan-white cone. A fitted TransWarp drive (`ship.transwarp.fitted`) turns that cone magenta and nothing else. None of these three is on `SHIP_TW_CHART_RANGE`. The pass pose is idle cyan-white cones. A drive recolor is the inherited rule. It is not a signature of this wave.

| | CargoTran | Colonial Transport | Taurean Mule |
| --- | --- | --- | --- |
| Accent | `#ffe566` | `#7dff7d` | `#d7b48a` |
| Kit | `spine` (top edge and stripe) | `cargo` (belly-tank rims and stripe) | `saddle` (panniers and stripe) |
| Shields full | Yellow on the spine's top edge and the stripe. The deck and the girder sides stay dark metal. | Green on the belly-tank rims and the stripe. The tank bodies and the cabin stay dark metal. | Tan on the panniers and the stripe. The pack stays darker metal. |
| Shields 0 | Bubble absent. Scars may show. The edge and the stripe are still `#ffe566`. | Bubble absent. Scars may show. The rims and the stripe are still `#7dff7d`. Port glass stays warm white. | Bubble absent. Scars may show. The panniers and the stripe are still `#d7b48a`. The pack stays dark. |

A full red body fails at either shield value. Empty shields are scars and a missing bubble. The class accent stays that colour.

## Marker ring

The count is the [marker-math](cockpit-ship-stage-marker-math.md) sheet. Visual markers are `max(1, ceil(n / 100))` when `n ≥ 1`. `n < 1` draws nothing. Each marker stands for 100 fighters. The last marker may be a partial hundred. It gets no numeral of its own. The stat block keeps today's words and order, and the exact bay. The visible legend is `each marker = 100 fighters`. Corner clusters and `FIGHTER_EXACT_CAP` stay retired, as the P1 pass left them.

One chevron dart, fill `#ff2a2a`, stroke `#ff8888`. The dart is a marker, not a second ship mesh.

The ring sits outside the hull body. Innermost world radius is the bounding sphere of every face, kit included, plus a gap. On this three-quarter view, and in the head-on clip, no marker's screen box intersects the hull silhouette. Markers yaw with the hull and read as escorts.

Fighter caps do not move on these three. The live roster changes a hold grant on the CargoTran and the Mule. The picture stays the contract size either way. Radius 56, the `fighterSlots` start P1 measured inside the Merchant and the Imperial, stays retired. On these three hulls the kit sets the sphere: the girder for the CargoTran, the belly tanks and the cabin for the Colonial, the hump and the panniers for the Mule.

`ceil(100 / 100)` is 1, so a full hundred is still one marker. The formula has no silent cap. The 25-marker, 500-marker, and 1,000-marker cases stay the measurements on the P1 pass. This wave shows its own caps. Marker clouds here are 4, 2, and 3. The clearance problem is the kit.

CargoTran. The fighter cap is 400 on both rosters, so the escort count at the cap is 4 on both. The live grant is 50 holds against a ceiling of 125. The deck does not shrink to that grant. The sphere includes the loft, the spine, and both engines. The girder sets the top of the sphere. A ring sized from the deck alone clips the spine and fails.

| Fighters `n` | Markers | What the ring shows |
| --- | --- | --- |
| 0 | 0 | No darts. |
| 1–100 | 1 | One dart. A partial hundred through 99. At 100, still one dart. No numeral on the dart. |
| 101–200 | 2 | The second dart is a partial hundred until 200. No numeral. |
| 201–300 | 3 | The third dart is a partial hundred until 300. No numeral. |
| 400 | 4 | Cap, both rosters. An exact four hundred. The fourth dart carries no numeral. |

Colonial Transport. The fighter cap is 200 on both rosters, so the escort count at the cap is 2 on both. The grant is 50 holds against a ceiling of 250. The box does not shrink to the grant and does not swell to the ceiling. Fighters per attack stay 100, which would draw one dart. The checklist uses the bay. The sphere includes the loft, both belly tanks, and both engines. The tanks set the bottom of the sphere and the cabin sets the top. A ring sized from the box sides clips a tank and fails. Two markers on a wide ring around a tall box is the right picture.

| Fighters `n` | Markers | What the ring shows |
| --- | --- | --- |
| 0 | 0 | No darts. |
| 1–100 | 1 | One dart. A partial hundred through 99. At 100, still one dart. No numeral on the dart. |
| 101–199 | 2 | The second dart is a partial hundred. No numeral. |
| 200 | 2 | Cap, both rosters. An exact two hundred. |

Taurean Mule. The fighter cap is 300 on both rosters, so the escort count at the cap is 3 on both. The live grant is 50 holds against a base grant of 40, ceiling 150 either way. The pack does not grow to match the live grant. The sphere includes the loft, the pack, both panniers, and both engines. The hump sets the top. The panniers set the tail corners. A ring that clears the low hull and clips the hump, or clears the hump and clips a pannier from above, fails.

| Fighters `n` | Markers | What the ring shows |
| --- | --- | --- |
| 0 | 0 | No darts. |
| 1–100 | 1 | One dart. A partial hundred through 99. At 100, still one dart. No numeral on the dart. |
| 101–200 | 2 | The second dart is a partial hundred until 200. No numeral. |
| 201–299 | 3 | The third dart is a partial hundred. No numeral. |
| 300 | 3 | Cap, both rosters. An exact three hundred. The third dart carries no numeral. |

## CU-seat and reduced motion

`prefers-reduced-motion`, a phone (`max-width: 700px`), and `body.cu-seat` hold the canonical still. That still is the three-quarter pose above. No loop on those three. The turn is not blocked. Marker-math keeps the same stills: the count in the table is drawn, and the orbit does not run.

## Rest of the pass list

The four-hull build's per-hull acceptance is the bar, on top of the render memo lines the P1 pass already cleared for the Merchant and the Imperial:

- Read at ~140px and at a hero crop about 55% of the deck. Name plate covered. Three-quarter and head-on. Shields 0 and shields full. A reader names the job.
- Markers 100:1, outside the hull, as above.
- Shields empty keeps the accent, as above.
- Gzip. `web/hull-meshes.js` stays under 40 KB gzipped. The budget is cumulative across cuts. P1 left the file at 8,673 bytes gzipped (level 9). Cuts 1 and 2 add the Scout, the Freighter, the BattleShip, and the FlagShip on that same file before this wave. This wave adds the three haulers. Record the new gzip size and the face counts with the wave. The cumulative file still sits under 40 KB. `tests/test_cockpit_ship_stage_p1.py` already asserts `gzip < 40 * 1024`.
- Frame time. The recorded bar stays the P1 pass: a drift of 500 markers and a static frame of 1,000 markers, both under 16 ms. This wave's own clouds are 4, 2, and 3. A miss of that 16 ms bar is the off-ramp below. When 1,000 separate SVG paths miss the frame, the fix is one group updated by a transform, or one canvas layer for markers only. The count stays `ceil(n / 100)`. Three.js waits for Hold-WebGL.
- Tests, in the same change as the faces. `tests/test_cockpit_ship_stage_p1.py` pins a `fleet-glass-v1` face count for `cargotran`, `colonial_transport`, and `taurean_mule` in `FLEET_GLASS` (`test_other_fifteen_hulls_keep_fleet_glass_points`). Those three pins update with this wave. Pins for hulls this wave does not cut stay. The Merchant stays at 217 faces and the Imperial at 311. Cuts 1 and 2 move their own four pins when those cuts land. This wave does not move them again. The 200-cap legend stays retired: `each marker = 100 fighters` remains the assertion in that file and in `tests/test_ship_view_visual_v1.py`. No engine change, no new action, no new event field.
- Side clip, `holdWarp`, phone still, reduced-motion still, `body.cu-seat` still, legend `each marker = 100 fighters`, and the exact bay on the stat line.
- Screenshots of the three hulls, shields empty and shields full, name covered, at ~140px and at the hero crop, plus the cap-marker cases (CargoTran at 4, Colonial at 2, Mule at 3), before any further hull leaves `fleet-glass-v1`.

## Files the product PR may touch

After cut 1 and cut 2 have merged and passed. The file boundary is already in the P0 pack, the render memo, the four-hull build, and the batch-2 contract. This checklist adds no paths.

May touch:

- `web/hull-meshes.js`, for `cargotran`, `colonial_transport`, and `taurean_mule` faces. Faces land there only, so a clip that calls `buildHullFaces` picks them up. Merchant Cruiser and Imperial StarShip faces stay as the P1 pass left them. Scout Marauder, Merchant Freighter, BattleShip, and Corporate FlagShip faces stay as cuts 1 and 2 left them.
- The tests named above, in the same change.

Leave alone. Use these lists as written:

- [Batch 2, Out of scope](cockpit-ship-stage-p1b-batch2-haulers.md#out-of-scope). The P1 spike hulls. The four-hull wave. The batch-1 remainder. The other player hulls, including the Tholian Sentinel and the Interdictor Cruiser. Ferrengi hulls.
- [P0, Out of scope](cockpit-ship-stage-p0.md). Ferrengi hulls. New engine events, new `EVENT_FACTS` keys, and new actions. Copying or tracing EIS, Markham, or ANSI ship art.
- [Render memo, What this spike is not](cockpit-ship-stage-p0-render.md). A new engine field. A new event. A change to warp-clip JSON cameras. A layout split (that is P3). A deletion of `#viewport` (that is P2). A trace of any classic outline.
- Every hull this wave does not cut. A second hull file. A second renderer, unless the block below is Hold-WebGL.
- Batches 3, 4, and 5 on the [fleet order](cockpit-ship-stage-p1b-fleet-order.md). Each starts after this wave has passed.
- `COMMANDER_NEXT.md`, `GAP_MAP.md`, the sheet index, and the other ship-stage sheets.

## Commander decision

Reply with one of these three. Pass means every item in this sheet holds. Hold-WebGL means one of the same three off-ramp conditions on the [P1 acceptance](cockpit-ship-stage-p1-acceptance.md) is true for this wave. Any other miss is Fail.

The P1 pass left Hold-WebGL closed. Reopening it takes one of the three off-ramps below. This wave does not reopen it on its own.

**Pass.** The CargoTran, Colonial Transport, and Taurean Mule read-test passed on PR #312 (squash `51acad6f`, product head `bb0223e6`), on the parent path of tip `feature/grokbot-player` @ `9b1dc5a3`. Meshes, stills, and tests landed. Shared SVG path (`buildHullFaces` / `projectFace`). Markers are `max(1, ceil(n / 100))` when `n ≥ 1`. CargoTran (`cargotran`) is kit `spine`, accent `#ffe566`, 212 faces / 28 accent, 4 markers at cap 400, span 170.1 × 22.8 × 25.6. Colonial Transport (`colonial_transport`) is kit `cargo`, accent `#7dff7d`, 251 faces / 51 accent, 2 markers at cap 200, span 89.7 × 53.8 × 42.0. Taurean Mule (`taurean_mule`) is kit `saddle`, accent `#d7b48a`, 209 faces / 47 accent, 3 markers at cap 300, span 100.0 × 27.9 × 36.6. `web/hull-meshes.js` is 12,659 bytes gzipped (level 9), under 40 KB. Stills: `docs/plans/stills/p1b-batch2-haulers/`. Measurement sheet: `docs/plans/cockpit-ship-stage-p1b-batch2-haulers-product.md`. Ship-stage tests: 26 passed (including new hauler pins; prior hull pins unchanged). WebGL stays off. Earlier hulls unchanged. Section token `box`. The `pods` detail does not grow shoulder pods or Freighter cheeks.

### Pass

All three hulls pass the three-quarter and head-on reads, at ~140px and at the hero crop, at shields 0 and shields full. The CargoTran reads as the long bulk hauler (spine). The Colonial reads as the tall colonist (belly tanks). The Mule reads as the beast of burden (saddle). They stay apart from each other, and each stays apart from the Merchant the P1 pass already cleared and from the Freighter the four-hull wave puts on screen. The marker rows match the formula, including CargoTran at 4, Colonial at 2, and Mule at 3, and no marker box cuts the silhouette. Shields empty keeps `#ffe566`, `#7dff7d`, and `#d7b48a`. CU-seat, reduced motion, and the phone still stay on the canonical still. The cumulative mesh file is under 40 KB gzipped, with face counts recorded. The named tests move in the same change. Stay on the shared SVG (`buildHullFaces` / `projectFace`). WebGL stays the closed off-ramp. Every other hull waits.

### Fail

A pass item is missed, and none of the three off-ramp conditions are true. This wave has not cleared the bar. CargoTran, Colonial Transport, Taurean Mule, and the other hulls still on `fleet-glass-v1` stay there. The next edit stays on `buildHullFaces` / `projectFace`. A missed 1,000-marker frame uses the group transform or the markers-only canvas layer from the render memo. The count stays `max(1, ceil(n / 100))` when `n ≥ 1`. Hold-WebGL stays closed. Cut 1 and cut 2, once merged, stay merged.

### Hold-WebGL

Closed. It opens only after this art pass, and only when this wave fails one of the same three off-ramps:

- The CargoTran, the Colonial Transport, and the Taurean Mule still fail the read test at hero size.
- Drift of the Imperial plus 500 markers, or a static frame of 1,000 markers, cannot hold a 16 ms update on a mid laptop and a phone-class CPU.
- A planet disc and a warp camera cannot be expressed in the SVG the clips already animate.

That spike consumes the face list from `buildHullFaces`. It does not introduce a second hull file. Warp clips stay SVG until their own note. A miss that is not one of those three is Fail, and the next edit stays on the shared SVG.
