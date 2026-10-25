# P1b acceptance — Missile Frigate and Havoc GunStar

Read-test for the batch-3 gun wave. Docs only. Tip surveyed: `feature/grokbot-player` @ `61422328`.

Taken from these sheets, which this file does not replace:

- [Batch 3 guns](cockpit-ship-stage-p1b-batch3.md) — the mesh contract for this wave. Missiles, rails, prongs, accents, and the numbered checks live there.
- [Four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) — product order. Cuts 1 and 2, then the batches ahead of this wave. This sheet is the gun wave.
- [Fleet order](cockpit-ship-stage-p1b-fleet-order.md) — batch 3. Missile Frigate, BattleShip, Havoc GunStar. The BattleShip mesh is cut 2.
- [P1 acceptance](cockpit-ship-stage-p1-acceptance.md) — the Pass / Fail / Hold-WebGL shape this wave mirrors.
- [P1 pass](cockpit-ship-stage-p1-pass.md) — the bar Merchant Cruiser and Imperial StarShip already cleared. WebGL stays the closed off-ramp.
- [Fighter marker math](cockpit-ship-stage-marker-math.md) — the shared 100:1 count.

Scope is Missile Frigate (`missile_frigate`, kit `missiles` plus `rails`) and Havoc GunStar (`havoc_gunstar`, kit `prongs`). [Fleet order](cockpit-ship-stage-p1b-fleet-order.md) names this cut as batch 3, with the BattleShip. The BattleShip contract already landed in the four-hull wave. This sheet re-shots that hull. It does not recut it. One shared mesh, shaded SVG, through `buildHullFaces` / `projectFace`. Looks stay on the batch-3 contract. Section token stays `round` on the Frigate and `hex` on the Havoc. The BattleShip stays `hex`. This wave adds no fourth section. Merchant Cruiser and Imperial StarShip stay as the P1 pass left them. Scout Marauder, Merchant Freighter, BattleShip, and Corporate FlagShip are the four-hull cuts. Escape Pod and T'Khasi Orion are the batch-1 remainder. CargoTran, Colonial Transport, and Taurean Mule are the hauler wave. This sheet does not restate their looks and does not accept those cuts. Every other hull stays on `fleet-glass-v1`.

The panel spelling is Missile Frigate and Havoc GunStar. `SHIP_SPECS_TW2002["havoc_gunstar"]["display_name"]` is `Havoc Gunstar`. The mesh keeps the panel spelling.

The [P1 pass](cockpit-ship-stage-p1-pass.md) already cleared this bar for the Merchant and the Imperial, on the shared SVG path (`#215`, `9d29349a`). Gzip there is 8,673 bytes (level 9). Drift at 500 markers and a static frame at 1,000 markers both held 16 ms. Hold-WebGL stays closed unless this wave fails one of the same three off-ramps.

Cover the name plate for every read below. Look at the current ~140px panel and at a hero crop about 55% of the deck. The crop is a read of the mesh. The layout split stays P3.

The held three-quarter pose is yaw `0.82`, pitch `0.5`, which `shipPose` already uses when motion is held ([FX sheet](cockpit-ship-stage-p0-fx.md)). Head-on is the warp clip camera `headon`.

## Launch

Product for this wave waits until the four-hull cuts have passed and the earlier batches ahead in fleet order have passed. This sheet is the read-test checklist only. It is not the launch.

Four-hull cuts, in [build order](cockpit-ship-stage-p1b-four-hull-build.md#build-order):

1. Scout Marauder and Merchant Freighter ([cut 1 acceptance](cockpit-ship-stage-p1b-scout-freighter-acceptance.md)).
2. BattleShip and Corporate FlagShip ([cut 2 acceptance](cockpit-ship-stage-p1b-battleship-flagship-acceptance.md)).

Earlier batches ahead of batch 3 in [fleet order](cockpit-ship-stage-p1b-fleet-order.md):

- Batch 1. Scout Marauder and Merchant Freighter are cut 1 above. The rest of that batch is the [batch-1 remainder](cockpit-ship-stage-p1b-batch1-remainder.md): Escape Pod and T'Khasi Orion ([batch 1 acceptance](cockpit-ship-stage-p1b-batch1-acceptance.md)).
- Batch 2. CargoTran, Colonial Transport, and Taurean Mule ([hauler contract](cockpit-ship-stage-p1b-batch2-haulers.md), [batch 2 acceptance](cockpit-ship-stage-p1b-batch2-haulers-acceptance.md)).

The [gun contract](cockpit-ship-stage-p1b-batch3.md#implement-after-the-spike-the-four-and-the-three-haulers) names the same wait for the P1 spike, the four, and the three haulers. The [P1 pass](cockpit-ship-stage-p1-pass.md) is already in. Fleet order also places batch 1 ahead of this wave, so the Escape Pod and the T'Khasi pass with that batch before these faces open. All of those cuts edit `web/hull-meshes.js`. Opening this wave while any of them is still in flight thrashes that file.

Build order inside that later PR is Missile Frigate, then Havoc GunStar. The photon boat goes first so the merged Imperial has its pair on screen and the missiles are locked larger than those forward barrels. The split prow is second, so it can be judged against the merged BattleShip and against the missiles just cut. Stop. Do not recut the BattleShip. Do not start the Star Master or the Constellation in this pass. Batches 4 and 5 start after this wave has passed.

## Three-quarter

Pose: yaw `0.82`, pitch `0.5`. Repeat at shields 0 and shields full, at both sizes. The numbered checks are the batch-3 three-quarter lists for these two hulls. Repeat the Frigate once in a frame that also shows the merged Imperial. Repeat the Havoc once with a fitted TransWarp drive and once without, and once in a frame that also shows the merged BattleShip.

Missile Frigate. A photon boat. Section `round`. A long slim body, ordinary in plan, slimmer than the BattleShip and shorter than the Imperial. Two long dorsal missiles sit on a rail, noses forward, proud of the fuselage. Each missile body is larger than the canopy. The rail is a thin track under the pair. It is how the missiles sit. Two engines sit low in the tail, inside the beam, under the missile line. They do not stick up past the missiles and they do not stick out past the fuselage. Kit: `missiles`, plus `rails`. `SHIPS` sets `detail` to `"rails bridge"`. The rail belongs to this kit. The `bridge` token is the shared canopy, and it stays shorter than the missiles. The missiles are on the ship when `photon_missiles` is 0. A loaded count of 10 does not add a third body, a row of ten bodies, or a numeral on the pair. Genesis stays 0, so there is no torpedo door. Five mines do not add a launcher. A reader says missile ship. Fifty markers are a real escort, and they do not replace the pair. This is the hull the Imperial's forward barrels must stay smaller than. A wide hex wedge fails, because that is the BattleShip. A split prow fails, because that is the Havoc. Canards fail, because that is the Scout. A broad cheek face fails, because that is the Freighter. A cargo girder the length of a flat deck fails, because that is the CargoTran. A pair that loses to the canopy fails.

Havoc GunStar. A shield tank and a gunship. Section `hex`. A short body. Two prongs run ahead of the loft nose and are the silhouette from the side, the top, and head-on. Head-on they are two bright tips with a gap. The gap is empty. The prongs are the guns. Three engines sit in a low horizontal row in the tail, inside the hex width, behind the prong line. They do not grow past the prong tips. Kit: `prongs`. `SHIPS` sets `detail` to `"guns bridge"`. The `guns` token is sausage vocabulary on this hull. It is the path that grows the Imperial's forward barrels. The prongs win. Do not also grow that barrel path. The `bridge` token is the shared canopy, and it stays shorter than the prongs. A holo scanner does not grow the Star Master's mast. One genesis does not add a door. Five mines do not add a launcher. Odds of 1.2 do not add a turret. A reader says a warship with a forked nose. A hundred markers do not replace the gap. This is the hull the BattleShip's turrets must stay distinct from. A tip that ends on the loft nose fails, because the split prow has collapsed into a single nose. A wide wedge with a turret pair on the back fails, because that is the BattleShip. Two dorsal missiles larger than the canopy fail, because that is the Frigate.

`SHIP_TW_CHART_RANGE` prints 16 hops on the Havoc. It is the third chart TransWarp hull, with the Imperial StarShip (50) and the Corporate FlagShip (28). With a drive fitted, the cones are magenta and the prong tips are still flat `#ff8844`. Idle cones, with no drive fitted, stay cyan-white. The Frigate is not on that chart. Its pass pose is idle cyan-white cones. A drive recolor is the inherited rule, and it is not a signature of the Frigate.

With the name covered, a reader says missile ship for the Frigate and warship with a forked nose for the Havoc. Inside this wave the pair is one nose and a dorsal pair versus two prongs with a gap.

The [wave read](cockpit-ship-stage-p1b-batch3.md#wave-read-test) is the subset this wave can get wrong while cutting the two new faces, with the BattleShip, the Imperial, the Freighter, and the CargoTran already on screen from earlier waves.

| Pair | What keeps them apart |
| --- | --- |
| Frigate / Imperial | Two dorsal missiles, each larger than the canopy and larger than the Imperial's forward barrels, versus a long castle and four bells. The Imperial is re-shot. |
| Frigate / BattleShip | Missiles on a rail along a slim spine versus thinner barrels on a turret pair, on a wide hex wedge. |
| Frigate / Havoc | One nose and a dorsal pair versus two prongs with a gap. |
| Frigate / CargoTran | Two missile bodies on a thin rail versus a cargo girder the length of a flat deck. |
| Frigate / Scout | A photon boat versus a needle and canards. |
| Havoc / BattleShip | A split prow versus turrets on a wide wedge. |
| Havoc / Imperial | Prongs ahead of a short body versus a long castle and a square of bells. |
| Havoc / Freighter | Two prong tips and a gap versus a short broad cheek face. |
| Havoc / FlagShip | A gap between prongs versus a tower rectangle on the centerline. The FlagShip is not recut. |
| Havoc / Star Master | Prongs versus a dish on a mast. The Star Master is not in this wave. No mast grows on the Havoc. |

## Head-on

One existing clip per hull. Side camera and head-on camera. The kit still reads in both. A part that only exists in the three-quarter view is not a signature. `holdWarp` still pauses a frame. The head-on camera is the warp clip camera `headon`. The numbered checks are the batch-3 head-on lists.

Missile Frigate. Two missile bodies sit above a slim fuselage. They are the high points, and they are larger than the canopy. The nose is one nose. Two engine mouths sit low, inside the beam, under the missile line. A split prow, a turret pair, a castle, a tower, cheek tanks, canards, or a square of four bells fails the frame.

Havoc GunStar. Two bright tips with a gap between them. The tips are `#ff8844`. The gap is empty. Three engine mouths sit in a low row, inside the hex, behind the prongs. The same drive pair as the three-quarter read: fitted cones go magenta, and the tips stay the flat accent. A third prong, a turret barrel, a marker in the gap, a dorsal missile pair, a tall centerline rectangle, a square of four bells, a broad cheek face, or a dish fails the frame.

## Re-shots

Reads of meshes that have already landed. This wave does not edit those faces.

BattleShip. The mesh stays the one cut 2 lands. Kit: `turrets`. Section `hex`. Accent `#c5c8ff` on the turret barrels and the stripe, including at shields 0. The numbered checks are the batch-3 [re-shot list](cockpit-ship-stage-p1b-batch3.md#re-shot-checklist). Same pose, sizes, and shield pair. Name plate covered. Once beside the Frigate, and once beside the Havoc, at ~140px and at the hero crop. The turret barrels still break the top edge. A pair still reads. The hex shoulders still read as a wide wedge, short for that beam. Beside the Frigate, these barrels stay a turret pair, thinner than that hull's dorsal missiles, and they sit on turret bodies. Beside the Havoc, the guns stay on the back. No prongs grow ahead of this nose. Photons stay 0, so the re-shot still has no missile bodies. The cap is 100 markers. Markers sit outside the barrel tips and the hex beam. The ring stays the sphere cut 2 set. This wave does not invent a second turret, and it does not borrow that radius for the Havoc.

Imperial StarShip. The mesh stays the one the P1 pass left. Beside the Frigate, the castle and the square of four bells still read, and the forward barrels stay smaller than the Frigate's missile bodies. Gold stays the Imperial's accent. It does not appear on the Frigate or the Havoc. This wave does not edit those faces. The Merchant stays at 217 faces and the Imperial at 311.

## Accent

Dark blue-grey metal on both hulls. The accent is a stripe, a canopy edge, and the kit. Canopy glass is a cool white mixed with the accent. Idle engines are a short cyan-white cone. A fitted TransWarp drive (`ship.transwarp.fitted`) turns that cone magenta and nothing else. On the Havoc the prongs stay paint. On the Frigate a drive recolor is the inherited rule, and it is not a signature.

| | Missile Frigate | Havoc GunStar |
| --- | --- | --- |
| Accent | `#ffb15a` | `#ff8844` |
| Kit | `missiles`, plus `rails` (bodies, rail edge, stripe) | `prongs` (tips and stripe) |
| Shields full | Amber on the missile bodies, the rail edge, and the stripe. The noses are a hotter amber than `#ffb15a`. The fuselage stays dark metal. | Orange on the prong tips and the stripe. The prong shafts and the hull stay dark metal, so head-on reads as two bright tips with a gap. |
| Shields 0 | Bubble absent. Scars may show. The bodies, the rail edge, and the stripe are still `#ffb15a`. The noses are still the hotter amber. | Bubble absent. Scars may show. The tips and the stripe are still `#ff8844`. |

A full red body fails at either shield value. A full amber body on the Frigate fails. A full orange body on the Havoc fails. Empty shields are scars and a missing bubble. The class accent stays that colour. With a drive fitted, the Havoc's cones are magenta and the prong tips are still flat `#ff8844`. Gold is the Imperial's accent. Magenta on a tower is the FlagShip. Neither colour appears on these prongs. The BattleShip re-shot keeps `#c5c8ff` on its barrels and its stripe.

## Marker ring

The count is the [marker-math](cockpit-ship-stage-marker-math.md) sheet. Visual markers are `max(1, ceil(n / 100))` when `n ≥ 1`. `n < 1` draws nothing. Each marker stands for 100 fighters. The last marker may be a partial hundred. It gets no numeral of its own. The stat block keeps today's words and order, and the exact bay. The visible legend is `each marker = 100 fighters`. Corner clusters and `FIGHTER_EXACT_CAP` stay retired, as the P1 pass left them. The count is the onboard bay, not fighters per attack.

One chevron dart, fill `#ff2a2a`, stroke `#ff8888`. The dart is a marker, not a second ship mesh.

The ring sits outside the hull body. Innermost world radius is the bounding sphere of every face, kit included, plus a gap. On this three-quarter view, and in the head-on clip, no marker's screen box intersects the hull silhouette. Markers yaw with the hull and read as escorts.

Fighter caps do not move on these two. The live roster changes a hold grant on both. The picture stays the contract size either way. Radius 56, the `fighterSlots` start P1 measured inside the Merchant and the Imperial, stays retired. On these two hulls the kit sets the sphere: the missiles for the Frigate, the prong tips for the Havoc.

`ceil(100 / 100)` is 1, so a full hundred is still one marker. The formula has no silent cap. The 25-marker, 500-marker, and 1,000-marker cases stay the measurements on the P1 pass. This wave shows its own caps. Marker clouds here are 50 and 100. The BattleShip's 100 is already on the merged hull. The clearance problem is the kit, not the count.

Missile Frigate. The fighter cap is 5,000 on both rosters, so the escort count at the cap is 50 on both. The live grant is 12 holds against a ceiling of 60. The missiles do not shrink to that grant. Fighters per attack stay 3,000, which would draw 30 darts. The checklist uses the bay. The sphere includes the loft, both missiles, the rail, the canopy, and both engines. The missiles set the top of the sphere. A ring sized to the fuselage clips them from the side and fails. Fifty markers sit between the 25 the Merchant spike records and the 500 the Imperial spike records.

| Fighters `n` | Markers | What the ring shows |
| --- | --- | --- |
| 0 | 0 | No darts. |
| 1–99 | 1 | One dart. A partial hundred. No numeral on the dart. |
| 100 | 1 | Still one dart. `ceil(100 / 100)` is 1. No numeral. |
| 101–200 | 2 | The second dart is a partial hundred until 200. No numeral. |
| 4,900 | 49 | Forty-nine darts. |
| 4,901–4,999 | 50 | Already 50. The last dart is a partial hundred. No numeral. |
| 5,000 | 50 | Cap, both rosters. An exact five thousand. The fiftieth dart is a full hundred and still carries no numeral. Screenshot case. Outside the missiles. |

Havoc GunStar. The fighter cap is 10,000 on both rosters, so the escort count at the cap is 100 on both. The live grant is 12 holds against a ceiling of 50. The prongs do not shrink to that grant. Fighters per attack stay 1,000, which would draw 10 darts. The checklist uses the bay. The sphere includes the loft, both prongs, the canopy, and the three engines. The prong tips set the nose of the sphere. A ring that clears the hex and clips a tip fails. A marker in the gap reads as a third prong and fails. One hundred markers is the same count the BattleShip contract already requires, on this hull's sphere, and it is under the 500-marker case P1 records. Do not borrow the BattleShip radius. Do not cap the formula.

| Fighters `n` | Markers | What the ring shows |
| --- | --- | --- |
| 0 | 0 | No darts. |
| 1–99 | 1 | One dart. A partial hundred. No numeral on the dart. |
| 100 | 1 | Still one dart. `ceil(100 / 100)` is 1. No numeral. |
| 101–200 | 2 | The second dart is a partial hundred until 200. No numeral. |
| 9,900 | 99 | Ninety-nine darts. |
| 9,901–9,999 | 100 | Already 100. The last dart is a partial hundred. No numeral. |
| 10,000 | 100 | Cap, both rosters. An exact ten thousand. The hundredth dart is a full hundred and still carries no numeral. Screenshot case. Outside the prong tips. No dart in the gap. |

## CU-seat and reduced motion

`prefers-reduced-motion`, a phone (`max-width: 700px`), and `body.cu-seat` hold the canonical still. That still is the three-quarter pose above. No loop on those three. The turn is not blocked. Marker-math keeps the same stills: the count in the table is drawn, and the orbit does not run.

## Rest of the pass list

The four-hull build's per-hull acceptance is the bar, on top of the render memo lines the P1 pass already cleared for the Merchant and the Imperial:

- Read at ~140px and at a hero crop about 55% of the deck. Name plate covered. Three-quarter and head-on. Shields 0 and shields full. A reader names the job. The Havoc drive pair is in that read: fitted cones magenta, tips still `#ff8844`.
- Markers 100:1, outside the hull, as above.
- Shields empty keeps the accent, as above.
- Gzip. `web/hull-meshes.js` stays under 40 KB gzipped. The budget is cumulative across cuts. P1 left the file at 8,673 bytes gzipped (level 9). Cuts 1 and 2, the batch-1 remainder, and the hauler wave add their faces on that same file before this wave. This wave adds the Frigate and the Havoc. Record the new gzip size and the face counts with the wave. The cumulative file still sits under 40 KB. `tests/test_cockpit_ship_stage_p1.py` already asserts `gzip < 40 * 1024`.
- Frame time. The recorded bar stays the P1 pass: a drift of 500 markers and a static frame of 1,000 markers, both under 16 ms. This wave's own clouds are 50 and 100. A miss of that 16 ms bar is the off-ramp below. When 1,000 separate SVG paths miss the frame, the fix is one group updated by a transform, or one canvas layer for markers only. The count stays `ceil(n / 100)`. Three.js waits for Hold-WebGL.
- Tests, in the same change as the faces. `tests/test_cockpit_ship_stage_p1.py` pins a `fleet-glass-v1` face count for `missile_frigate` and `havoc_gunstar` in `FLEET_GLASS` (`test_other_fifteen_hulls_keep_fleet_glass_points`). Those two pins update with this wave. Pins for hulls this wave does not cut stay. The Merchant stays at 217 faces and the Imperial at 311. Cut 1, cut 2, the batch-1 remainder, and the hauler wave move their own pins when those cuts land. This wave does not move them again. The BattleShip re-shot does not move the `battleship` pin. The 200-cap legend stays retired: `each marker = 100 fighters` remains the assertion in that file and in `tests/test_ship_view_visual_v1.py`. No engine change, no new action, no new event field.
- Side clip, `holdWarp`, phone still, reduced-motion still, `body.cu-seat` still, legend `each marker = 100 fighters`, and the exact bay on the stat line.
- Screenshots of both new hulls, shields empty and shields full, name covered, at ~140px and at the hero crop, plus the cap-marker cases (Frigate at 50, Havoc at 100). The Havoc once with a fitted TransWarp drive and once without. The Imperial beside the Frigate. The BattleShip beside the Frigate and beside the Havoc. Before Star Master, Constellation, or any further hull leaves `fleet-glass-v1`.

## Files the product PR may touch

After the four-hull cuts and the earlier batches ahead in fleet order have merged and passed. The file boundary is already in the P0 pack, the render memo, the four-hull build, and the batch-3 contract. This checklist adds no paths.

May touch:

- `web/hull-meshes.js`, for `missile_frigate` and `havoc_gunstar` faces. Faces land there only, so a clip that calls `buildHullFaces` picks them up. Merchant Cruiser and Imperial StarShip faces stay as the P1 pass left them. Scout Marauder, Merchant Freighter, BattleShip, and Corporate FlagShip faces stay as cuts 1 and 2 left them. Escape Pod, T'Khasi Orion, CargoTran, Colonial Transport, and Taurean Mule faces stay as those earlier batches left them.
- The tests named above, in the same change.

Leave alone. Use these lists as written:

- [Batch 3, Out of scope](cockpit-ship-stage-p1b-batch3.md#out-of-scope). The P1 spike hulls, except the Imperial re-shot named above. The four-hull wave, except the BattleShip re-shot named above. The hauler wave. Escape Pod and T'Khasi Orion. Star Master, Constellation, Tholian Sentinel, and Interdictor Cruiser. Ferrengi hulls.
- [P0, Out of scope](cockpit-ship-stage-p0.md). Ferrengi hulls. New engine events, new `EVENT_FACTS` keys, and new actions. Copying or tracing EIS, Markham, or ANSI ship art.
- [Render memo, What this spike is not](cockpit-ship-stage-p0-render.md). A new engine field. A new event. A change to warp-clip JSON cameras. A layout split (that is P3). A deletion of `#viewport` (that is P2). A trace of any classic outline.
- Every hull this wave does not cut. A second hull file. A second renderer, unless the block below is Hold-WebGL. A recut of the BattleShip or the Imperial to help a pair shot.
- Batches 4 and 5 on the [fleet order](cockpit-ship-stage-p1b-fleet-order.md). Each starts after this wave has passed.
- `COMMANDER_NEXT.md`, `GAP_MAP.md`, the sheet index, and the other ship-stage sheets.

## Commander decision

Reply with one of these three. Pass means every item in this sheet holds. Hold-WebGL means one of the same three off-ramp conditions on the [P1 acceptance](cockpit-ship-stage-p1-acceptance.md) is true for this wave. Any other miss is Fail.

The P1 pass left Hold-WebGL closed. Reopening it takes one of the three off-ramps below. This wave does not reopen it on its own.

### Pass

Both hulls pass the three-quarter and head-on reads, at ~140px and at the hero crop, at shields 0 and shields full. The Frigate reads as the photon boat (`missiles` plus `rails`). The Havoc reads as the shield tank and gunship (`prongs`). They stay apart from each other, and each stays apart from the Imperial the P1 pass already cleared and from the BattleShip the four-hull wave puts on screen. The BattleShip re-shot and the Imperial re-shot pass, and those faces stay where the earlier cuts put them. The marker rows match the formula, including the Frigate at 50 and the Havoc at 100, and no marker box cuts the silhouette. No marker sits in the Havoc's gap. Shields empty keeps `#ffb15a` and `#ff8844`. A fitted drive on the Havoc turns the cones magenta and leaves the tips `#ff8844`. CU-seat, reduced motion, and the phone still stay on the canonical still. The cumulative mesh file is under 40 KB gzipped, with face counts recorded. The named tests move in the same change. Stay on the shared SVG (`buildHullFaces` / `projectFace`). WebGL stays the closed off-ramp. Every other hull waits.

### Fail

A pass item is missed, and none of the three off-ramp conditions are true. This wave has not cleared the bar. Missile Frigate, Havoc GunStar, and the other hulls still on `fleet-glass-v1` stay there. The next edit stays on `buildHullFaces` / `projectFace`. A missed pair shot is a miss on the new hull. BattleShip faces stay as cut 2 left them. Imperial faces stay as the P1 pass left them. A missed 1,000-marker frame uses the group transform or the markers-only canvas layer from the render memo. The count stays `max(1, ceil(n / 100))` when `n ≥ 1`. Hold-WebGL stays closed. The four-hull cuts, the batch-1 remainder, and the hauler wave, once merged, stay merged.

### Hold-WebGL

Closed. It opens only after this art pass, and only when this wave fails one of the same three off-ramps:

- The Missile Frigate and the Havoc GunStar still fail the read test at hero size.
- Drift of the Imperial plus 500 markers, or a static frame of 1,000 markers, cannot hold a 16 ms update on a mid laptop and a phone-class CPU.
- A planet disc and a warp camera cannot be expressed in the SVG the clips already animate.

That spike consumes the face list from `buildHullFaces`. It does not introduce a second hull file. Warp clips stay SVG until their own note. A miss that is not one of those three is Fail, and the next edit stays on the shared SVG.
