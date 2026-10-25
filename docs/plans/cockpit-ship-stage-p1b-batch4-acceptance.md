# P1b acceptance — Star Master, Constellation, and Corporate FlagShip

Read-test for the batch-4 dish and X wave. Docs only. Tip surveyed: `feature/grokbot-player` @ `d01d56a5`.

Stills for this sheet are listed in the [stills inventory](stills/README.md) (#344) under [p1b-batch4-dish](stills/p1b-batch4-dish/).

Taken from these sheets, which this file does not replace:

- [Batch 4](cockpit-ship-stage-p1b-batch4.md) — the mesh contract for this wave. Dish, X, the FlagShip re-shot, accents, and the numbered checks live there.
- [Fleet order](cockpit-ship-stage-p1b-fleet-order.md) — product order. This sheet is batch 4.
- [Four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) — cuts 1 and 2. This wave waits until both have passed, and until the batches ahead of it in fleet order have passed.
- [P1 acceptance](cockpit-ship-stage-p1-acceptance.md) — the Pass / Fail / Hold-WebGL shape this wave mirrors.
- [P1 pass](cockpit-ship-stage-p1-pass.md) — the bar Merchant Cruiser and Imperial StarShip already cleared. WebGL stays the closed off-ramp.
- [Fighter marker math](cockpit-ship-stage-marker-math.md) — the shared 100:1 count.

Scope is Star Master (`star_master`, kit `mast` and `dish`), Constellation (`constellation`, kit `quad`), and the Corporate FlagShip re-shot (`corporate_flagship`, kit `tower`). [Fleet order](cockpit-ship-stage-p1b-fleet-order.md) names these three as batch 4 and judges them together. The new meshes are the Star Master and the Constellation. The FlagShip mesh contract already landed in the four-hull wave. This sheet does not rewrite it and does not recut that tower. One shared mesh, shaded SVG, through `buildHullFaces` / `projectFace`. Looks stay on the batch-4 contract. Section token stays `round` on the Star Master, the Constellation, and the FlagShip. `SHIPS` sets `kind` to `"arrow"` on the Star Master and `"delta"` on the Constellation. Those tokens are the flat panel outline. They do not change the loft section. This wave adds no fourth section. A hex wedge is the BattleShip.

Merchant Cruiser and Imperial StarShip stay as the P1 pass left them. Scout Marauder, Merchant Freighter, BattleShip, and Corporate FlagShip are the four-hull wave. Escape Pod and T'Khasi Orion are the batch-1 remainder. CargoTran, Colonial Transport, and Taurean Mule are the hauler wave. Missile Frigate, Havoc GunStar, and the BattleShip re-shot are the gun wave. This sheet does not restate their looks and does not accept those cuts. Tholian Sentinel and Interdictor Cruiser stay on `fleet-glass-v1`.

The panel spelling is Star Master and Constellation. `SHIP_SPECS_TW2002` `display_name` is `Star Master` and `Constellation`. The chart spells the second hull Constilation. The FAQ spells the first Starmaster. The mesh keeps the panel spelling. `SHIP_SPECS_TW2002["corporate_flagship"]["display_name"]` is `Corporate Flagship`. The panel and the bible spell the second word `FlagShip`. The mesh keeps the panel spelling. Do not rename any of the three.

The [P1 pass](cockpit-ship-stage-p1-pass.md) already cleared this bar for the Merchant and the Imperial, on the shared SVG path (`#215`, `9d29349a`). Gzip there is 8,673 bytes (level 9). Drift at 500 markers and a static frame at 1,000 markers both held 16 ms. Hold-WebGL stays closed unless this wave fails one of the same three off-ramps.

Cover the name plate for every read below. Look at the current ~140px panel and at a hero crop about 55% of the deck. The crop is a read of the mesh. The layout split stays P3.

The held three-quarter pose is yaw `0.82`, pitch `0.5`, which `shipPose` already uses when motion is held ([FX sheet](cockpit-ship-stage-p0-fx.md)). Head-on is the warp clip camera `headon`.

## Launch

Product for this wave waits until the four-hull cuts and the earlier batches ahead in fleet order have passed.

Product stills scaffold: [batch 4 dish product](cockpit-ship-stage-p1b-batch4-dish-product.md) (#339, `c01ebb2f`). Stills directory: [p1b-batch4-dish](stills/p1b-batch4-dish/). The scaffold does not stamp Pass. It ships no PNGs. Measured cells stay TBD until product.

1. The P1 spike has merged and passed: Merchant Cruiser and Imperial StarShip ([P1 pass](cockpit-ship-stage-p1-pass.md)).
2. Cut 1 has merged and passed: Scout Marauder and Merchant Freighter ([cut 1 acceptance](cockpit-ship-stage-p1b-scout-freighter-acceptance.md)).
3. Cut 2 has merged and passed: BattleShip and Corporate FlagShip ([cut 2 acceptance](cockpit-ship-stage-p1b-battleship-flagship-acceptance.md)).
4. The batch-1 remainder has merged and passed: Escape Pod and T'Khasi Orion ([batch-1 acceptance](cockpit-ship-stage-p1b-batch1-acceptance.md)).
5. The hauler wave has merged and passed: CargoTran, Colonial Transport, and Taurean Mule ([hauler acceptance](cockpit-ship-stage-p1b-batch2-haulers-acceptance.md)).
6. The gun wave has merged and passed: Missile Frigate, Havoc GunStar, and the BattleShip re-shot ([gun contract](cockpit-ship-stage-p1b-batch3.md)).

The [batch-4 contract](cockpit-ship-stage-p1b-batch4.md#implement-after-the-spike-the-four-the-haulers-and-the-guns) names the same gate. The FlagShip's tower and the Imperial's castle have to be on screen before the dish is cut. The Imperial's square of bells and the Havoc's prongs have to be on screen before the X is cut. The gun-wave kits have to be on screen so the dish stays a plate on a mast, and the X stays four nacelles. Those cuts edit `web/hull-meshes.js`. Opening this wave while any of them is still in flight thrashes that file. This sheet is the read-test checklist for the later product PR. It is not the launch.

Build order inside that later PR is Star Master, then Constellation. The dish goes first so the merged FlagShip tower and the merged Imperial castle have their pair on screen, and the plate is locked wider than the beam before the X is cut. The X is second, so it can be judged against that plate, against the Imperial's square of bells, and against the merged Havoc's prongs. Stop. Do not recut the FlagShip. Do not start the Tholian Sentinel or the Interdictor Cruiser.

## Three-quarter

Pose: yaw `0.82`, pitch `0.5`. Repeat at shields 0 and shields full, at both sizes. The numbered checks are the batch-4 three-quarter lists for these three hulls.

Star Master. A mid combat hull whose whole job is a dish. Section `round`. A modest arrow, a mast on the mid-body, one plate on that mast. The plate is wider than the fuselage beam, so the top view is a circle on a stick. That circle is a plate. It does not wrap the body. The plate breaks the top edge from the side, from above, and in this pose. Two engines sit low in the tail, inside the beam, under the dish line. They do not stick up past the plate and they do not stick out past the fuselage. Kit: `mast` and `dish`. `SHIPS` sets `detail` to `"dish bridge"`. The `dish` token is this kit. It is not a second plate beside the `PARTS` dish. The `bridge` token is the shared canopy, and it stays shorter than the mast. The plate is on the ship when no scanner is fitted. A fitted holo scanner does not add a second plate, a numeral, or a second mast. The scanner path that draws a small plate on other hulls already skips `star_master`. Keep that skip. A reader says a ship with a dish. Fifty markers are a real escort, and they do not replace the plate. A hoop around the body fails, because that is the Interdictor. A stepped block fails, because that is the FlagShip. A long castle fails, because that is the Imperial. Canards fail, because that is the Scout. A split prow fails, because that is the Havoc. An X of nacelles fails, because that is the Constellation. A plate whose wider span sits inside the mid-station beam fails, because the circle has collapsed into the arrow.

Constellation. A mid combat hull with four nacelles in an X. Section `round`. A slim body. Four nacelles sit in an X and trail past the tail. They are the silhouette from the side, the top, and head-on. The gap between the arms is empty. Four engine mouths sit off the centerline. The quad is the larger cross. Kit: `quad`. `SHIPS` sets `detail` to `"nacelles bridge"`. The `nacelles` token is the path that grows the Imperial's four bells, and that path already stays off when `PARTS` is `quad`. The quad wins. Do not also grow that bell path. The `bridge` token is the shared canopy, and it stays inside the slim body, shorter than the arms. A density scanner does not grow a plate. The scanner path that draws a dish when `ship.scanner` is set stays off this key. A reader says a ship with an X. Fifty markers do not fill the crook. A wide hex wedge with a turret pair fails, because that is the BattleShip. A dish on a mast fails, because that is the Star Master. A castle with a square of bells fails, because that is the Imperial. Prongs ahead of the nose fail, because that is the Havoc. A tower rectangle fails, because that is the FlagShip. A tip that ends on the tail station fails, because the X has collapsed into the fuselage.

Corporate FlagShip. A re-shot, not a new mesh. The contract is the [four-hull FlagShip](cockpit-ship-stage-p1b-next-hulls.md#corporate-flagship--corporate_flagship). This wave does not recut it, does not invent a second step, and does not edit that sheet. Section `round`. Kit: `tower`. A corp liner: a stepped command block standing amidships, taller than the hull is deep, three engines in a low row. The tower is the signature. Two hundred escorts at a full bay do not replace it. `corp_only` is a yard gate, not a paint scheme. Repeat once beside the Star Master, once beside the Imperial, and once beside the Constellation. Repeat once with `ship.transwarp.fitted` set and once without. Fitted, the engine cones are magenta and the upper step stays flat `#ff77ff`. Idle cones stay cyan-white. The tower is painted metal. It is not an emissive lamp. A dish on a mast fails, because that is the Star Master. A long castle fails, because that is the Imperial. An X at the tail fails, because that is the Constellation. The re-shot does not move the tower top.

With the name covered, a reader says dish for the Star Master, X for the Constellation, and capital for the FlagShip. Inside this wave the trio is a plate on a stick versus four nacelles versus a tower amidships. The Imperial stays the long castle the P1 pass already cleared. The BattleShip and the Havoc stay the gun wave. The Interdictor stays batch 5.

The [wave read](cockpit-ship-stage-p1b-batch4.md#wave-read-test) is the subset this wave can get wrong while cutting the two new faces, with the FlagShip, the Imperial, the BattleShip, and the Havoc already on screen from earlier waves.

| Pair | What keeps them apart |
| --- | --- |
| FlagShip / Imperial / Star Master | Tall tower versus long castle versus a dish. Both capitals are re-shot. The dish is the new mesh. |
| Star Master / Constellation | A plate on a mast, wider than the beam, versus an X of four nacelles. |
| Star Master / Interdictor | A circle on a stick versus hoops around a body. The Interdictor is not in this wave. No hoop grows on the mast. |
| Star Master / Havoc | A dorsal plate versus prongs ahead of the nose. The Havoc is not recut. No mast grows on the Havoc. |
| Constellation / Imperial | An X of nacelles versus a square of bells and a castle. |
| Constellation / BattleShip | An X on a slim round body versus a turret pair on a wide hex wedge. The BattleShip is not recut. |
| Constellation / Havoc | Nacelles trailing past the tail versus prongs ahead of the nose. |
| Constellation / FlagShip | An X versus a tower rectangle on the centerline. The FlagShip is re-shot, not recut. |
| Constellation / Interdictor | An X of engines versus two hoops. The Interdictor waits in batch 5. No hoop grows on the X. |

## Head-on

One existing clip per hull. Side camera and head-on camera. The kit still reads in both. A part that only exists in the three-quarter view is not a signature. `holdWarp` still pauses a frame. The head-on camera is the warp clip camera `headon`. The numbered checks are the batch-4 head-on lists.

Star Master. One plate on a stick is the high point, and the plate is wider than the beam. The plate is one plate. Two engine mouths sit low, inside the beam, under the dish. A second plate fails. A rectangle the height of a tower fails, because that is the FlagShip. A hoop, an X of nacelles, a square of four bells, a pair of prongs, or a castle fails the frame.

Constellation. An X and little else. The four arms wear `#d0d6ff`. Four engine mouths sit off the centerline. The X is the larger cross around them. A row of mouths with no X fails. A square of four bells fails, because that is the Imperial. Two prongs with a gap fail, because that is the Havoc. A plate on a stick fails, because that is the Star Master. A castle, a tower rectangle, a hoop, or a dish fails the frame.

Corporate FlagShip. A rectangle on the centerline, taller than the hull. Three engine mouths sit in a low row, inside the beam. An X fails, because that is the Constellation. A square of four bells fails, because that is the Imperial. The frame shows no dish, no hoop, and no plate wider than the beam. The same drive pair as the three-quarter read: fitted cones go magenta, and the upper step stays the flat accent.

## Accent

Dark blue-grey metal on all three hulls. The accent is a stripe, a canopy edge, and the kit. Canopy glass is a cool white mixed with the accent. Idle engines are a short cyan-white cone. A fitted TransWarp drive (`ship.transwarp.fitted`) turns that cone magenta and nothing else. Neither new hull is on `SHIP_TW_CHART_RANGE`. Their pass pose is idle cyan-white cones. A drive recolor is the inherited rule, and it is not a signature of the dish or the X. The FlagShip is on that chart (28 hops), with the Imperial StarShip (50) and the Havoc GunStar (16). Its re-shot keeps the drive pair, and the tower stays paint.

| | Star Master | Constellation | Corporate FlagShip |
| --- | --- | --- | --- |
| Accent | `#9ad7ff` | `#d0d6ff` | `#ff77ff` |
| Kit | `mast` and `dish` (plate and stripe) | `quad` (nacelles and stripe) | `tower` (upper step and stripe) |
| Shields full | `#9ad7ff` on the plate and the stripe. The mast and the fuselage stay dark metal. | `#d0d6ff` on the nacelles and the stripe. The fuselage stays dark metal. | `#ff77ff` on the tower's upper step and the stripe. Painted metal. The tower is not an emissive lamp. |
| Shields 0 | Bubble absent. Scars may show. The plate and the stripe are still `#9ad7ff`. The mast stays dark. | Bubble absent. Scars may show. The nacelles and the stripe are still `#d0d6ff`. The fuselage stays dark metal. | Bubble absent. Scars may show. The upper step and the stripe are still `#ff77ff`. With a drive fitted, the cones are magenta and the upper step is still flat `#ff77ff`. |

A full red body fails at either shield value. A full body painted `#9ad7ff` fails on the Star Master. A full body painted `#d0d6ff` fails on the Constellation. Empty shields are scars and a missing bubble. The class accent stays that colour. Magenta on a tower is the FlagShip. Gold is the Imperial. The Star Master's `#9ad7ff` stays on its plate. None of those colours appears on the Constellation's arms, and neither gold nor the plate's `#9ad7ff` appears on the FlagShip's tower.

## Marker ring

The count is the [marker-math](cockpit-ship-stage-marker-math.md) sheet. Visual markers are `max(1, ceil(n / 100))` when `n ≥ 1`. `n < 1` draws nothing. Each marker stands for 100 fighters. The last marker may be a partial hundred. It gets no numeral of its own. The stat block keeps today's words and order, and the exact bay. The visible legend is `each marker = 100 fighters`. The count is the onboard bay, not fighters per attack. Corner clusters and `FIGHTER_EXACT_CAP` stay retired, as the P1 pass left them.

One chevron dart, fill `#ff2a2a`, stroke `#ff8888`. The dart is a marker, not a second ship mesh.

The ring sits outside the hull body. Innermost world radius is the bounding sphere of every face, kit included, plus a gap. On this three-quarter view, and in the head-on clip, no marker's screen box intersects the hull silhouette. Markers yaw with the hull and read as escorts.

Fighter caps do not move on these three. The live roster changes a hold grant on the Star Master and the FlagShip. The picture stays the contract size either way. Radius 56, the `fighterSlots` start P1 measured inside the Merchant and the Imperial, stays retired. On these three hulls the kit sets the sphere: the plate for the Star Master, the nacelle tips for the Constellation, the upper tower step for the FlagShip.

`ceil(100 / 100)` is 1, so a full hundred is still one marker. The formula has no silent cap. The 25-marker, 500-marker, and 1,000-marker cases stay the measurements on the P1 pass. This wave shows its own caps. Marker clouds on the new hulls are 50 and 50. The FlagShip's 200 is already on the merged hull, inside the 500 the Imperial spike already drew. The clearance problem is the kit, not the count.

Star Master. The fighter cap is 5,000 on both rosters, so the escort count at the cap is 50 on both. The live grant is 20 holds against a base grant of 30 and a ceiling of 73. The picture does not shrink to the live grant and does not swell to the ceiling. Shields stay 2,000. That shared number with the Imperial does not grow a castle. Fighters per attack stay 1,000, which would draw 10 darts. The checklist uses the bay. The sphere includes the loft, the mast, the one plate, the canopy, and both engines. The plate sets the top of the sphere. A ring sized to the fuselage clips the dish from the side and fails. Markers orbit outside the plate. They do not ring the mast as if the dish were the Interdictor's hoop. Do not borrow the FlagShip radius. Do not cap the formula.

| Fighters `n` | Markers | What the ring shows |
| --- | --- | --- |
| 0 | 0 | No darts. |
| 1–99 | 1 | One dart. A partial hundred. No numeral. |
| 100 | 1 | Still one dart. `ceil(100 / 100)` is 1. |
| 101–200 | 2 | The second dart is a partial hundred until 200. No numeral. |
| 4,900 | 49 | Forty-nine darts. |
| 4,901–4,999 | 50 | Already 50. The last dart is a partial hundred. No numeral. |
| 5,000 | 50 | Cap, both rosters. An exact five thousand. The fiftieth dart is a full hundred and still carries no numeral. |

Constellation. The fighter cap is 5,000 on both rosters, so the escort count at the cap is 50 on both. The grant is 20 holds against a ceiling of 80 on both rosters. The body does not shrink to the grant and does not swell to the ceiling. Shields stay 750. That shared number with the BattleShip does not grow a turret pair. Fighters per attack stay 2,000, which would draw 20 darts. The checklist uses the bay. The sphere includes the loft, the four nacelles, the canopy, and the four engines. The nacelle tips set the tail and the beam of the sphere. A ring that clears the slim body and clips an arm fails. A marker in the crook reads as a fifth arm and fails. Do not borrow the Imperial radius. Do not cap the formula.

| Fighters `n` | Markers | What the ring shows |
| --- | --- | --- |
| 0 | 0 | No darts. |
| 1–99 | 1 | One dart. A partial hundred. No numeral. |
| 100 | 1 | Still one dart. `ceil(100 / 100)` is 1. |
| 101–200 | 2 | The second dart is a partial hundred until 200. No numeral. |
| 4,900 | 49 | Forty-nine darts. |
| 4,901–4,999 | 50 | Already 50. The last dart is a partial hundred. No numeral. |
| 5,000 | 50 | Cap, both rosters. An exact five thousand. The fiftieth dart is a full hundred and still carries no numeral. |

Corporate FlagShip. The fighter cap is 20,000 on both rosters, so the escort count at the cap is 200 on both. The live grant is 20 holds against a ceiling of 85. The tower does not shrink. The checklist uses the bay. The sphere includes the loft, both tower steps, and the three engines. The upper step sets the top of the sphere. A ring that clears the liner and clips the tower fails. Two hundred markers is the count the four-hull contract already requires. This wave repeats that cloud on the re-shot. It does not move the ring cut 2 lands. Do not cap the formula.

| Fighters `n` | Markers | What the ring shows |
| --- | --- | --- |
| 0 | 0 | No darts. |
| 1–99 | 1 | One dart. A partial hundred. No numeral. |
| 100 | 1 | Still one dart. `ceil(100 / 100)` is 1. |
| 101–200 | 2 | The second dart is a partial hundred until 200. No numeral. |
| 19,900 | 199 | One hundred ninety-nine darts. |
| 19,901–19,999 | 200 | Already 200. The last dart is a partial hundred. No numeral. |
| 20,000 | 200 | Cap, both rosters. An exact twenty thousand. The two-hundredth dart is a full hundred and still carries no numeral. |

## CU-seat and reduced motion

`prefers-reduced-motion`, a phone (`max-width: 700px`), and `body.cu-seat` hold the canonical still. That still is the three-quarter pose above. No loop on those three. The turn is not blocked. Marker-math keeps the same stills: the count in the table is drawn, and the orbit does not run.

## Rest of the pass list

The four-hull build's per-hull acceptance is the bar, on top of the render memo lines the P1 pass already cleared for the Merchant and the Imperial:

- Read at ~140px and at a hero crop about 55% of the deck. Name plate covered. Three-quarter and head-on. Shields 0 and shields full. A reader names the job.
- Markers 100:1, outside the hull, as above.
- Shields empty keeps the accent, as above.
- Gzip. `web/hull-meshes.js` stays under 40 KB gzipped. The budget is cumulative across cuts. P1 left the file at 8,673 bytes gzipped (level 9). Cuts 1 and 2, the batch-1 remainder, the hauler wave, and the gun wave add their faces on that same file before this wave. This wave adds the Star Master and the Constellation. The FlagShip faces stay as cut 2 left them. Record the new gzip size and the face counts with the wave. The cumulative file still sits under 40 KB. `tests/test_cockpit_ship_stage_p1.py` already asserts `gzip < 40 * 1024`.
- Frame time. The recorded bar stays the P1 pass: a drift of 500 markers and a static frame of 1,000 markers, both under 16 ms. This wave's own clouds are 50 and 50, and the FlagShip's 200 is already on the merged hull. A miss of that 16 ms bar is the off-ramp below. When 1,000 separate SVG paths miss the frame, the fix is one group updated by a transform, or one canvas layer for markers only. The count stays `ceil(n / 100)`. Three.js waits for Hold-WebGL.
- Tests, in the same change as the faces. `tests/test_cockpit_ship_stage_p1.py` pins a `fleet-glass-v1` face count for `star_master` and `constellation` in `FLEET_GLASS` (`test_other_fifteen_hulls_keep_fleet_glass_points`). Those two pins update with this wave. Pins for hulls this wave does not cut stay. The Merchant stays at 217 faces and the Imperial at 311. Cut 2 moves the `corporate_flagship` pin when that cut lands. This wave does not move it again. The 200-cap legend stays retired: `each marker = 100 fighters` remains the assertion in that file and in `tests/test_ship_view_visual_v1.py`. No engine change, no new action, no new event field.
- Side clip, `holdWarp`, phone still, reduced-motion still, `body.cu-seat` still, legend `each marker = 100 fighters`, and the exact bay on the stat line.
- Screenshots of the two new hulls, shields empty and shields full, name covered, at ~140px and at the hero crop, plus the cap-marker cases (Star Master at 50, Constellation at 50). The new hulls' pass pose is idle cyan-white cones. The FlagShip re-shot once with a fitted TransWarp drive and once without, beside the Star Master and beside the Imperial, at the 200-marker cap already on the merged hull. The Imperial re-shot keeps the castle and the square of bells. Before Tholian Sentinel and Interdictor Cruiser leave `fleet-glass-v1`.

## Files the product PR may touch

After the four-hull cuts and the earlier batches ahead in fleet order have merged and passed. The file boundary is already in the P0 pack, the render memo, the four-hull build, and the batch-4 contract. This checklist adds no paths.

May touch:

- `web/hull-meshes.js`, for `star_master` and `constellation` faces. Faces land there only, so a clip that calls `buildHullFaces` picks them up. Merchant Cruiser and Imperial StarShip faces stay as the P1 pass left them. Scout Marauder, Merchant Freighter, BattleShip, and Corporate FlagShip faces stay as cuts 1 and 2 left them. The FlagShip re-shot does not edit those faces.
- The tests named above, in the same change.

Leave alone. Use these lists as written:

- [Batch 4, Out of scope](cockpit-ship-stage-p1b-batch4.md#out-of-scope). The P1 spike hulls, except the Imperial re-shot named above. The four-hull wave, except the FlagShip re-shot named above. The hauler wave. The gun wave. Escape Pod and T'Khasi Orion. Tholian Sentinel and Interdictor Cruiser. Ferrengi hulls.
- [P0, Out of scope](cockpit-ship-stage-p0.md). Ferrengi hulls. New engine events, new `EVENT_FACTS` keys, and new actions. Copying or tracing EIS, Markham, or ANSI ship art.
- [Render memo, What this spike is not](cockpit-ship-stage-p0-render.md). A new engine field. A new event. A change to warp-clip JSON cameras. A layout split (that is P3). A deletion of `#viewport` (that is P2). A trace of any classic outline.
- Every hull this wave does not cut. A second hull file. A second renderer, unless the block below is Hold-WebGL.
- Batch 5 on the [fleet order](cockpit-ship-stage-p1b-fleet-order.md). It starts after this wave has passed.
- `COMMANDER_NEXT.md`, `GAP_MAP.md`, the sheet index, and the other ship-stage sheets.

## Commander decision

Reply with one of these three. Pass means every item in this sheet holds. Hold-WebGL means one of the same three off-ramp conditions on the [P1 acceptance](cockpit-ship-stage-p1-acceptance.md) is true for this wave. Any other miss is Fail.

The P1 pass left Hold-WebGL closed. Reopening it takes one of the three off-ramps below. This wave does not reopen it on its own.

**Pass.** The Star Master and Constellation read-test passed on PR #387 (`3114c994`), on the parent path of tip `feature/grokbot-player` @ `8ccb7c6f` (#389). Meshes, stills, and tests landed. Shared SVG path (`buildHullFaces` / `projectFace`). Markers are `max(1, ceil(n / 100))` when `n ≥ 1`. Star Master (`star_master`) is kit `mast` and `dish`, accent `#9ad7ff`, 183 faces / 29 accent, radius 44.1, one 16-gon plate, two engines, 50 markers at cap 5,000, hash `7c79af13cc74372b`. Constellation (`constellation`) is kit `quad`, accent `#d0d6ff`, 311 faces / 91 accent, radius 64.0, four nacelles in an X, no dish, 50 markers at cap 5,000, hash `787b41d482d6501a`. `web/hull-meshes.js` is 14,991 bytes gzipped (level 9), under 40 KB. Stills: `docs/plans/stills/p1b-batch4-dish/` (66 PNGs), listed in the stills inventory `docs/plans/stills/README.md` (#388, `1ee63b98`). Measurement sheet: `docs/plans/cockpit-ship-stage-p1b-batch4-dish-product.md`. Frame rows on that sheet sit under 16 ms. Ship-stage mesh tests: 36 passed (dish pins included; prior hull pins unchanged). WebGL stays off. Earlier hulls unchanged. Section token `round` on both. Corporate FlagShip stays 210 faces (re-shot, not recut). Imperial stays 311. Batch 5 (Tholian Sentinel and Interdictor Cruiser) is unblocked for product sequencing. P2 stays closed behind that brick cut. Sticky order remains this Pass, then batch 5, then P2.

### Pass

All three hulls pass the three-quarter and head-on reads, at ~140px and at the hero crop, at shields 0 and shields full. The Star Master reads as the dish (a plate on a mast, wider than the beam). The Constellation reads as the X (four nacelles). The FlagShip still reads as the tower, and it stays flat `#ff77ff` with a fitted drive and at shields 0. They stay apart from each other, and each stays apart from the Imperial the P1 pass already cleared and from the BattleShip and the Havoc the gun wave puts on screen. The marker rows match the formula, including Star Master at 50, Constellation at 50, and FlagShip at 200, and no marker box cuts the silhouette. Shields empty keeps `#9ad7ff`, `#d0d6ff`, and `#ff77ff`. CU-seat, reduced motion, and the phone still stay on the canonical still. The cumulative mesh file is under 40 KB gzipped, with face counts recorded. The named tests move in the same change. Stay on the shared SVG (`buildHullFaces` / `projectFace`). WebGL stays the closed off-ramp. Tholian Sentinel and Interdictor Cruiser wait.

### Fail

A pass item is missed, and none of the three off-ramp conditions are true. This wave has not cleared the bar. Star Master, Constellation, and the other hulls still on `fleet-glass-v1` stay there. The FlagShip faces stay as cut 2 left them. The next edit stays on `buildHullFaces` / `projectFace`. A missed 1,000-marker frame uses the group transform or the markers-only canvas layer from the render memo. The count stays `max(1, ceil(n / 100))` when `n ≥ 1`. Hold-WebGL stays closed. The four-hull cuts and the earlier batches, once merged, stay merged.

### Hold-WebGL

Closed. It opens only after this art pass, and only when this wave fails one of the same three off-ramps:

- The Star Master and the Constellation still fail the read test at hero size.
- Drift of the Imperial plus 500 markers, or a static frame of 1,000 markers, cannot hold a 16 ms update on a mid laptop and a phone-class CPU.
- A planet disc and a warp camera cannot be expressed in the SVG the clips already animate.

That spike consumes the face list from `buildHullFaces`. It does not introduce a second hull file. Warp clips stay SVG until their own note. A miss that is not one of those three is Fail, and the next edit stays on the shared SVG. The silhouettes in the batch-4 contract still apply.
