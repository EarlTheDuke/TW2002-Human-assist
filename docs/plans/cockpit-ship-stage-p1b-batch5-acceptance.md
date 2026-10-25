# P1b acceptance — Tholian Sentinel and Interdictor Cruiser

Read-test for the batch-5 brick and hoops wave. Docs only. Tip surveyed: `feature/grokbot-player` @ `390e6a99`.

Taken from these sheets, which this file does not replace:

- [Batch 5 brick and hoops](cockpit-ship-stage-p1b-batch5.md) — the mesh contract for this wave. Armor slabs, hoops, accents, and the numbered checks live there.
- [Four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) — product order. Cuts 1 and 2, then the batches ahead of this wave. This sheet is the brick and hoops wave.
- [Fleet order](cockpit-ship-stage-p1b-fleet-order.md) — [batch 5](cockpit-ship-stage-p1b-fleet-order.md#batch-5--brick-and-hoops). Tholian Sentinel, Interdictor Cruiser.
- [P1 acceptance](cockpit-ship-stage-p1-acceptance.md) — the Pass / Fail / Hold-WebGL shape this wave mirrors.
- [P1 pass](cockpit-ship-stage-p1-pass.md) — the bar Merchant Cruiser and Imperial StarShip already cleared. WebGL stays the closed off-ramp.
- [Fighter marker math](cockpit-ship-stage-marker-math.md) — the shared 100:1 count.

Scope is Tholian Sentinel (`tholian_sentinel`, kit `armor`) and Interdictor Cruiser (`interdictor_cruiser`, kit `hoop`). [Fleet order](cockpit-ship-stage-p1b-fleet-order.md#batch-5--brick-and-hoops) names this cut as batch 5. Two hulls, on purpose. The Colonial Transport mesh is the hauler wave. The Constellation mesh is fleet-order batch 4. This sheet re-shots those two hulls. It does not recut them. One shared mesh, shaded SVG, through `buildHullFaces` / `projectFace`. Looks stay on the batch-5 contract. Section token stays `box` on the Sentinel and on the Interdictor. This wave adds no fourth section. The hoops are kit, not a section. Merchant Cruiser and Imperial StarShip stay as the P1 pass left them. Scout Marauder, Merchant Freighter, BattleShip, and Corporate FlagShip are the four-hull cuts. Escape Pod and T'Khasi Orion are the batch-1 remainder. CargoTran, Colonial Transport, and Taurean Mule are the hauler wave. Missile Frigate, Havoc GunStar, and the BattleShip re-shot are the gun wave. Star Master, Constellation, and Corporate FlagShip are fleet-order batch 4. The FlagShip's tower contract already landed in the four-hull wave. This sheet does not restate their looks and does not accept those cuts. Every other hull stays on `fleet-glass-v1`.

The panel spelling is Tholian Sentinel and Interdictor Cruiser. `SHIP_SPECS_TW2002` spells both `display_name` values the same way. The mesh keeps those names.

The [P1 pass](cockpit-ship-stage-p1-pass.md) already cleared this bar for the Merchant and the Imperial, on the shared SVG path (`#215`, `9d29349a`). Gzip there is 8,673 bytes (level 9). Drift at 500 markers and a static frame at 1,000 markers both held 16 ms. Hold-WebGL stays closed unless this wave fails one of the same three off-ramps.

Cover the name plate for every read below. Look at the current ~140px panel and at a hero crop about 55% of the deck. The crop is a read of the mesh. The layout split stays P3.

The held three-quarter pose is yaw `0.82`, pitch `0.5`, which `shipPose` already uses when motion is held ([FX sheet](cockpit-ship-stage-p0-fx.md)). Head-on is the warp clip camera `headon`.

## Launch

Product for this wave waits until the four-hull cuts have passed and the earlier batches ahead in fleet order have passed. This sheet is the read-test checklist only. It is not the launch.

Four-hull cuts, in [build order](cockpit-ship-stage-p1b-four-hull-build.md#build-order):

1. Scout Marauder and Merchant Freighter ([cut 1 acceptance](cockpit-ship-stage-p1b-scout-freighter-acceptance.md)).
2. BattleShip and Corporate FlagShip ([cut 2 acceptance](cockpit-ship-stage-p1b-battleship-flagship-acceptance.md)).

Earlier batches ahead of batch 5 in [fleet order](cockpit-ship-stage-p1b-fleet-order.md):

- Batch 1. Scout Marauder and Merchant Freighter are cut 1 above. The rest of that batch is the [batch-1 remainder](cockpit-ship-stage-p1b-batch1-remainder.md): Escape Pod and T'Khasi Orion ([batch 1 acceptance](cockpit-ship-stage-p1b-batch1-acceptance.md)).
- Batch 2. CargoTran, Colonial Transport, and Taurean Mule ([hauler contract](cockpit-ship-stage-p1b-batch2-haulers.md), [batch 2 acceptance](cockpit-ship-stage-p1b-batch2-haulers-acceptance.md)).
- Batch 3. Missile Frigate, BattleShip, and Havoc GunStar ([gun contract](cockpit-ship-stage-p1b-batch3.md), [batch 3 acceptance](cockpit-ship-stage-p1b-batch3-acceptance.md)). The BattleShip mesh is cut 2 above.
- Batch 4. Star Master, Constellation, and Corporate FlagShip ([fleet-order batch 4](cockpit-ship-stage-p1b-fleet-order.md#batch-4--dish-x-and-the-other-capital)). The FlagShip mesh is cut 2 above. Batch 4 is still the gate, so the dish, the X, and the tower are on screen together before a hoop is cut.

The [brick and hoops contract](cockpit-ship-stage-p1b-batch5.md#implement-after-the-spike-and-the-earlier-p1b-batches) names the same wait: the P1 spike, the batch-1 remainder, the four-hull wave, the hauler wave, the gun wave, and fleet-order batch 4. The [P1 pass](cockpit-ship-stage-p1-pass.md) is already in. The Colonial's cabin has to be on screen before the brick is cut. The Constellation's X has to be on screen before the hoops are cut. The Star Master's dish has to be on screen so a hoop is not drawn as a plate. An ordinary marker ring has to have shipped, which it has once the spike's ring is on screen. The spike's throwaway 1,000 has to be measured before this hull's real 1,000 is the pass. All of those cuts edit `web/hull-meshes.js`. Opening this wave while any of them is still in flight thrashes that file.

Build order inside that later PR is Tholian Sentinel, then Interdictor Cruiser. The brick goes first so the merged Colonial has its pair on screen and the slabs are locked as a short square before any ring is cut. The hoops are second, so they can be judged against the merged Constellation, and so the 1,000-marker drift is recorded on a hull whose silhouette is already those hoops. Stop. Do not recut the Colonial. Do not recut the Constellation. Do not start a third silhouette in this pass. Do not go back for the Escape Pod or the T'Khasi Orion. Ferrengi hulls stay out.

## Three-quarter

Pose: yaw `0.82`, pitch `0.5`. Repeat at shields 0 and shields full, at both sizes. The numbered checks are the batch-5 three-quarter lists for these two hulls. Repeat the Sentinel once in a frame that also shows the merged Colonial. Repeat the Interdictor once in a frame that also shows the merged Constellation.

Tholian Sentinel. A fortress. Section `box`. The shortest, bluntest body in the fleet. Armor slabs sit on both flanks, outside the loft, and they make the head-on view nearly square. The nose is a stub. Nothing on the outline suggests speed. No belly tanks. No cabin row as the main shape. Two engines sit low in the tail, inside the beam, inside the slab line. They do not stick out past the slabs, and they do not stick up past the brick. Kit: `armor`. `SHIPS` sets `detail` to `"bridge"`. The `bridge` token is the shared canopy, and it stays shorter than the slabs. Do not grow a second signature beside the plating. A holo scanner does not grow the Star Master's mast. One genesis does not add a door. Fifty mines do not add a launcher. Odds of 1.0 do not add a gun. The 4:1 corp-planet defense at `THOLIAN_CORP_DEFENSE_ODDS` (4.0) does not add a kit. A short row of lit ports stays the shared box material. Port glass stays the shared cool white mixed with the accent. It does not become the tell. A reader calls it a plated block and does not call it fast. Twenty-five markers are the Merchant's escort count on a much smaller body, and they do not replace the square. This is the hull the Colonial's cabin must stay distinct from. Canards fail, because that is the Scout. A wedge nose fails, because that is a trader. A tall box with tanks and a cabin row fails, because that is the Colonial. A broad cheek face fails, because that is the Freighter. A long flat deck with a girder fails, because that is the CargoTran. A ring around the brick fails, because that is the Interdictor.

Interdictor Cruiser. The barge. Section `box`. A heavy body inside two hoops. The hoops are larger than the hull and are the first shape from the side, from above, and head-on. Head-on is a ring with a body in the hole. The hole is empty. Nothing else in the fleet wears a hoop. Four engines sit in the tail, inside the hoops, in a low row on the body. They do not trail past the hoops, and they do not form an X. Kit: `hoop`. `SHIPS` sets `detail` to `"ring bridge"`. The `ring` token is not a second kit. Today's loft already skips the eight-box nose ring when `PARTS` is `hoop`. Keep that skip. Do not grow a nose collar, and do not grow a third hoop. The `bridge` token is the shared canopy, inside the body, shorter than the hoops. A holo scanner does not grow the Star Master's mast. A plate in the hole is that dish and fails. Two hundred mines do not add a launcher. Twenty genesis torpedoes do not add a row of doors. Photons stay 0, so the dorsal missile pair does not appear. Odds of 1.2 do not add prongs. `COMBAT_INTERDICT_HULLS` names this cruiser. The hold is the two hoops. A reader calls it a ship inside rings, and does not call it an X of engines or a dish on a stick. A full bay is 1,000 markers, orbiting outside the hoops. The cloud does not fill the hole, and it does not replace the rings. This is the hull the spike's throwaway 1,000-marker ring was standing in for. The pass is this mesh, not that stand-in. An X of nacelles trailing past the tail fails, because that is the Constellation. A filled disc fails, because that is the Star Master's plate. A long castle and a square of four bells fails, because that is the Imperial. A tower rectangle on the centerline fails, because that is the FlagShip. A plated brick with no hoop fails, because that is the Sentinel. A short port row a box loft already paints stays subordinate. It is not a cabin, and it is not the signature.

Neither hull is on `SHIP_TW_CHART_RANGE`. The chart prints no hop ceiling for these keys. The pass pose is idle cyan-white cones. A fitted TransWarp drive (`ship.transwarp.fitted`) turns that cone magenta and nothing else. A drive recolor is the inherited rule, and it is not a signature of this wave.

With the name covered, a reader says plated block for the Sentinel and ship inside rings for the Interdictor. Inside this wave the pair is a short plated brick versus a body inside two hoops.

The [wave read](cockpit-ship-stage-p1b-batch5.md#wave-read-test) is the subset this wave can get wrong while cutting the two new faces, with the Colonial and the Constellation already on screen from earlier batches.

| Pair | What keeps them apart |
| --- | --- |
| Tholian / Colonial | A short plated brick, nearly square, with no belly tanks and no cabin row as the main shape, versus a tall cabin box and two belly tanks. The Colonial is re-shot. |
| Tholian / Scout | A blunt brick versus a long needle and canards. The index tie at 125 does not move either silhouette. |
| Tholian / Freighter | A nearly square plated face versus a short broad cheek face. |
| Tholian / CargoTran | A short brick versus a long flat deck and a dorsal girder. |
| Tholian / Interdictor | A plated brick versus a body inside two hoops. Same section token. Different kit. |
| Constellation / Interdictor | An X of four nacelles versus two hoops. The Constellation is re-shot. |
| Interdictor / Star Master | Two open hoops around a body versus a dish, a plate on a mast. The Star Master is not recut. No plate grows in the hole. |
| Interdictor / Imperial | Hoops larger than the body, with 1,000 markers outside them, versus a long castle and four bells. The Imperial's throwaway 1,000-ring is the stand-in the spike already measured. It is not this pass. The Imperial is not recut. |
| Interdictor / FlagShip | A ring with a body in the hole versus a tower rectangle on the centerline. The FlagShip is not recut. |

## Head-on

One existing clip per hull. Side camera and head-on camera. The kit still reads in both. A part that only exists in the three-quarter view is not a signature. `holdWarp` still pauses a frame. The head-on camera is the warp clip camera `headon`. The numbered checks are the batch-5 head-on lists.

Tholian Sentinel. The face is nearly square. The slabs are the sides of that square. The nose is a stub in the middle of the square. It is not a broad cheek face and not a tall cabin. Two engine mouths sit low, inside the square, not past the slabs. The frame shows no belly tanks, no hoop, no dish, no X of nacelles, and no canards. Markers clear the slabs.

Interdictor Cruiser. A ring with a body in the hole. The rims are `#ff5cab`. The hole is empty. The hole is not a filled plate, not a third prong, and not a marker. Four engine mouths sit on the body, inside the ring. An X of four nacelles fails, because that is the Constellation. A square of bells fails, because that is the Imperial. The frame shows no dish on a mast, no tower rectangle, and no nearly square armor brick. Markers clear the outer rim.

## Re-shots

Reads of meshes that have already landed. This wave does not edit those faces.

Colonial Transport. The mesh stays the one the hauler wave lands. Kit: `cargo` (the belly tanks). Section `box`. Accent `#7dff7d` on the stripe and the tank rims, including at shields 0. Port glass is a warm white so the green stripe stays the accent. The numbered checks are the batch-5 [Colonial re-shot list](cockpit-ship-stage-p1b-batch5.md#colonial-transport--re-shot-not-a-new-mesh). Same pose, sizes, and shield pair as the hauler sheet. Name plate covered. Once beside the Sentinel, at ~140px and at the hero crop. The flank still reads as a tall box, high for its length, with a cabin row. Two belly tanks still break the underside. Beside the Sentinel, the slabs stay on the Sentinel. This hull does not grow them. The Sentinel's mint does not replace `#7dff7d`. The cap is 2 markers. Markers sit outside the top of the box and outside the tanks. The ring stays the sphere the hauler wave set. This wave does not recut the Colonial, and it does not borrow its tanks onto the brick. The `colonial_transport` pin does not move.

Constellation. The mesh stays the one fleet-order batch 4 lands. Kit: `quad`. Accent `#d0d6ff` on the nacelles and the stripe, including at shields 0. The numbered checks are the batch-5 [Constellation re-shot list](cockpit-ship-stage-p1b-batch5.md#constellation--re-shot-not-a-new-mesh). Same pose and the same two sizes as batch 4. Name plate covered. Repeat at shields 0 and at shields full, once beside the Interdictor. Head-on is an X of four nacelles, and little else. The nacelles trail past the tail. Two hoops around the body fail, because that is the Interdictor. Beside the Interdictor, the X stays on this hull and the hoops stay on that one. The frame shows no castle, no dish, and no prongs. The X, not the fuselage, sets the sphere. The cap is 50 markers. Markers sit outside the arms. This wave does not recut the X. The `constellation` pin does not move.

Star Master stays the batch-4 mesh. The dish stays a plate on a mast. No plate grows in the Interdictor's hole. Corporate FlagShip stays the cut-2 mesh. Imperial StarShip stays the mesh the P1 pass left. Do not pass the Interdictor by reshooting the Imperial's throwaway 1,000-ring. The Merchant stays at 217 faces and the Imperial at 311.

## Accent

Dark blue-grey metal on both hulls. The accent is a stripe, a canopy edge, and the kit. Canopy glass is a cool white mixed with the accent. Idle engines are a short cyan-white cone. A fitted TransWarp drive (`ship.transwarp.fitted`) turns that cone magenta and nothing else. Neither hull is on `SHIP_TW_CHART_RANGE`. The pass pose is idle cyan-white cones. A drive recolor is the inherited rule, and it is not a signature of this wave.

| | Tholian Sentinel | Interdictor Cruiser |
| --- | --- | --- |
| Accent | `#62f0c8` | `#ff5cab` |
| Kit | `armor` (slab faces and stripe) | `hoop` (both rims and stripe) |
| Shields full | Mint on the slab faces and the stripe. The fuselage between the slabs stays dark metal, so the plating reads as two flanks and the body does not become a mint block. | Pink on both hoop rims and the stripe. The holes stay open and the body stays dark metal, so head-on reads as a ring with a body in the hole, not as a pink wedge and not as a filled disc. |
| Shields 0 | Bubble absent. Scars may show. The slab faces and the stripe are still `#62f0c8`. | Bubble absent. Scars may show. The rims and the stripe are still `#ff5cab`. |

A full red body fails at either shield value. A full mint body on the Sentinel fails. A full pink body on the Interdictor fails. A filled disc on the Interdictor fails. Empty shields are scars and a missing bubble. The class accent stays that colour. The 4,000 shield cap is the same number on both hulls. It does not paint the Sentinel mint, and it does not paint the Interdictor pink. Colonial green is `#7dff7d`, and it stays on the Colonial's stripe and tank rims. Constellation `#d0d6ff` stays on the nacelles and the stripe. The Interdictor's cones are not those nacelles, and they are not a second accent on the hoops. Gold is the Imperial's accent. Magenta on a tower is the FlagShip. Neither colour appears on these rims.

## Marker ring

The count is the [marker-math](cockpit-ship-stage-marker-math.md) sheet. Visual markers are `max(1, ceil(n / 100))` when `n ≥ 1`. `n < 1` draws nothing. Each marker stands for 100 fighters. The last marker may be a partial hundred. It gets no numeral of its own. The stat block keeps today's words and order, and the exact bay. The visible legend is `each marker = 100 fighters`. Corner clusters and `FIGHTER_EXACT_CAP` stay retired, as the P1 pass left them. The count is the onboard bay, not fighters per attack.

One chevron dart, fill `#ff2a2a`, stroke `#ff8888`. The dart is a marker, not a second ship mesh.

The ring sits outside the hull body. Innermost world radius is the bounding sphere of every face, kit included, plus a gap. On this three-quarter view, and in the head-on clip, no marker's screen box intersects the hull silhouette. Markers yaw with the hull and read as escorts. The Interdictor's ring is outside the hoops, not in the hole and not on the skin.

Fighter caps do not move on these two. The live roster changes a hold grant on the Interdictor. The picture stays the contract size either way. Radius 56, the `fighterSlots` start P1 measured inside the Merchant and the Imperial, stays retired. On these two hulls the kit sets the sphere: the slabs for the Sentinel, the hoops for the Interdictor.

`ceil(100 / 100)` is 1, so a full hundred is still one marker. The formula has no silent cap. The 25-marker, 500-marker, and 1,000-marker cases stay the measurements on the P1 pass. This wave shows its own caps. Marker clouds here are 25 and 1,000. The Colonial's 2 and the Constellation's 50 are already on the merged hulls. The clearance problem on the Sentinel is the brick. The clearance problem on the Interdictor is the hoops and the 1,000-marker count together.

Tholian Sentinel. The fighter cap is 2,500 on both rosters, so the escort count at the cap is 25 on both. The grant is 10 holds against a ceiling of 50. The brick does not shrink to the grant and does not swell to the ceiling. Shields stay 4,000. Mines 50, genesis 1, photons 0. Fighters per attack stay 800, which would draw 8 darts. The checklist uses the bay. The sphere includes the loft, both armor slabs, the stub nose, the canopy, and both engines. The slabs set the beam. A length-only radius leaves markers in the slab silhouette. Twenty-five markers is the count the Merchant spike already drew, on this hull's sphere. Do not borrow the Merchant radius (~93). Do not borrow the Imperial radius (~121). A borrowed capital ring leaves the fortress in a hole. Ticks on the brick fail. The grouping fix in the render memo is not the remedy here. The cloud is 25.

| Fighters `n` | Markers | What the ring shows |
| --- | --- | --- |
| 0 | 0 | No darts. |
| 1–99 | 1 | One dart. A partial hundred. No numeral on the dart. |
| 100 | 1 | Still one dart. `ceil(100 / 100)` is 1. No numeral. |
| 101–200 | 2 | The second dart is a partial hundred until 200. No numeral. |
| 2,400 | 24 | Twenty-four darts. |
| 2,401–2,499 | 25 | Already 25. The last dart is a partial hundred. No numeral. |
| 2,500 | 25 | Cap, both rosters. An exact two thousand five hundred. The twenty-fifth dart is a full hundred and still carries no numeral. Screenshot case. Outside the slabs. |

Interdictor Cruiser. The fighter cap is 100,000 on both rosters, so the escort count at the cap is 1,000 on both. The live grant is 10 holds against a base grant of 20 and a ceiling of 40. The picture does not shrink to match that grant, and the body does not swell to the ceiling. Shields stay 4,000. Mines 200, genesis 20, photons 0. Fighters per attack stay 15,000, which would draw 150 darts. The checklist uses the bay. The sphere includes the loft, both hoops, the canopy, and the four engines. The hoops set the radius, after they have grown past today's glass. The render memo measures today's glass at AABB 136×75×75, bounding radius ~108. Fleet order says ~108 is a floor, not the radius to ship. The mesh pass grows both hoops until they are larger than the hull and the first shape in every camera, both rims `#ff5cab`, both open, and then remeasures. Do not ship ~108. A ring sized to the fuselage clips the hoops and fails. A ring left at the measured ~108 clips the grown hoops and fails. A marker in the hole reads as cargo, or as a filled dish, and fails. A marker on the skin fails. Do not start the ring at `fighterSlots` radius 56. That start is inside the body. Do not borrow the Imperial radius (~121) from the stand-in. One thousand markers is the stress case. Do not cap the formula.

This is the 1,000-marker case. The spike pass list draws a throwaway 1,000-marker ring on the Imperial and records one static frame at 1,000. This hull is that later case. The count is the onboard bay on the Interdictor. The pass is 1,000 markers outside these hoops. Do not pass the hull by reshooting the Imperial's stand-in, and do not leave the 1,000 on the castle. Record the drift frame time at 1,000 on this hull, the one whose hoops are real. Reuse the marker grouping the spike recorded for that throwaway ring: one group moved by a transform, or one canvas layer for markers only. A naive per-frame DOM write of 1,000 nodes can miss a phone frame even when the hull is cheap. If 1,000 separate SVG paths miss the frame, that grouping is the fix. It is not a silent change to `ceil(n / 100)`, and it is not three.js, unless the render memo's off-ramp conditions are already met.

| Fighters `n` | Markers | What the ring shows |
| --- | --- | --- |
| 0 | 0 | No darts. |
| 1–99 | 1 | One dart. A partial hundred. No numeral on the dart. |
| 100 | 1 | Still one dart. `ceil(100 / 100)` is 1. No numeral. |
| 101–200 | 2 | The second dart is a partial hundred until 200. No numeral. |
| 50,000 | 500 | The Imperial cap. This bay does not stop there. |
| 99,900 | 999 | Nine hundred ninety-nine darts. |
| 99,901–99,999 | 1,000 | Already 1,000. The last dart is a partial hundred. No numeral. |
| 100,000 | 1,000 | Cap, both rosters. An exact hundred thousand. The thousandth dart is a full hundred and still carries no numeral. Screenshot case. Outside the hoops. None in the hole. None on the skin. |

## CU-seat and reduced motion

`prefers-reduced-motion`, a phone (`max-width: 700px`), and `body.cu-seat` hold the canonical still. That still is the three-quarter pose above. No loop on those three. The turn is not blocked. Marker-math keeps the same stills: the count in the table is drawn, and the orbit does not run.

On the Interdictor those stills draw the 1,000 count and they do not loop. Live idle is the orbit those stills do not run. The drift measurement is that orbit. The stills still have to show 1,000 darts outside the hoops.

## Rest of the pass list

The four-hull build's per-hull acceptance is the bar, on top of the render memo lines the P1 pass already cleared for the Merchant and the Imperial:

- Read at ~140px and at a hero crop about 55% of the deck. Name plate covered. Three-quarter and head-on. Shields 0 and shields full. A reader names the job.
- Markers 100:1, outside the hull, as above. On the Interdictor, outside the hoops.
- Shields empty keeps the accent, as above.
- Gzip. `web/hull-meshes.js` stays under 40 KB gzipped. The budget is cumulative across cuts. P1 left the file at 8,673 bytes gzipped (level 9). Cuts 1 and 2, the batch-1 remainder, the hauler wave, the gun wave, and fleet-order batch 4 add their faces on that same file before this wave. This wave adds the Sentinel and the Interdictor. Record the new gzip size and the face counts with the wave. The cumulative file still sits under 40 KB. `tests/test_cockpit_ship_stage_p1.py` already asserts `gzip < 40 * 1024`.
- Frame time. The recorded bar stays the P1 pass: a drift of 500 markers and a static frame of 1,000 markers, both under 16 ms. This wave's own clouds are 25 and 1,000. Record the drift frame time at 1,000 on the Interdictor, and reuse the spike's throwaway grouping. A miss of that 16 ms bar is the off-ramp below. When 1,000 separate SVG paths miss the frame, the fix is one group updated by a transform, or one canvas layer for markers only. The count stays `ceil(n / 100)`. Three.js waits for Hold-WebGL.
- Tests, in the same change as the faces. `tests/test_cockpit_ship_stage_p1.py` pins a `fleet-glass-v1` face count for `tholian_sentinel` and `interdictor_cruiser` in `FLEET_GLASS` (`test_other_fifteen_hulls_keep_fleet_glass_points`). Those two pins update with this wave. Pins for hulls this wave does not cut stay. The Merchant stays at 217 faces and the Imperial at 311. Cut 1, cut 2, the batch-1 remainder, the hauler wave, the gun wave, and fleet-order batch 4 move their own pins when those cuts land. This wave does not move them again. The Colonial re-shot does not move the `colonial_transport` pin. The Constellation re-shot does not move the `constellation` pin. The 200-cap legend stays retired: `each marker = 100 fighters` remains the assertion in that file and in `tests/test_ship_view_visual_v1.py`. No engine change, no new action, no new event field.
- Side clip, `holdWarp`, phone still, reduced-motion still, `body.cu-seat` still, legend `each marker = 100 fighters`, and the exact bay on the stat line.
- Screenshots of both new hulls, shields empty and shields full, name covered, at ~140px and at the hero crop, plus the cap-marker cases (Sentinel at 25, Interdictor at 1,000). The Colonial beside the Sentinel. The Constellation beside the Interdictor. The Interdictor stills show 1,000 darts outside the hoops. Do not pass this wave by reshooting the Imperial's throwaway 1,000. No third silhouette in this pass.

## Files the product PR may touch

After the four-hull cuts and the earlier batches ahead in fleet order have merged and passed. The file boundary is already in the P0 pack, the render memo, the four-hull build, and the batch-5 contract. This checklist adds no paths.

May touch:

- `web/hull-meshes.js`, for `tholian_sentinel` and `interdictor_cruiser` faces. Faces land there only, so a clip that calls `buildHullFaces` picks them up. Merchant Cruiser and Imperial StarShip faces stay as the P1 pass left them. Scout Marauder, Merchant Freighter, BattleShip, and Corporate FlagShip faces stay as cuts 1 and 2 left them. Escape Pod, T'Khasi Orion, CargoTran, Colonial Transport, Taurean Mule, Missile Frigate, Havoc GunStar, Star Master, and Constellation faces stay as those earlier batches left them.
- The tests named above, in the same change.

Leave alone. Use these lists as written:

- [Batch 5, Out of scope](cockpit-ship-stage-p1b-batch5.md#out-of-scope). The P1 spike hulls, including the Imperial, except that the throwaway 1,000-ring on the Imperial is the measurement this wave replaces with the real Interdictor ring. The batch-1 remainder. The four-hull wave. The hauler wave, except the Colonial re-shot named above. The gun wave. Fleet-order batch 4, except the Constellation re-shot named above. Ferrengi hulls.
- [P0, Out of scope](cockpit-ship-stage-p0.md). Ferrengi hulls. New engine events, new `EVENT_FACTS` keys, and new actions. Copying or tracing EIS, Markham, or ANSI ship art.
- [Render memo, What this spike is not](cockpit-ship-stage-p0-render.md). A new engine field. A new event. A change to warp-clip JSON cameras. A layout split (that is P3). A deletion of `#viewport` (that is P2). A trace of any classic outline.
- Every hull this wave does not cut. A second hull file. A second renderer, unless the block below is Hold-WebGL. A recut of the Colonial, the Constellation, the Star Master, the FlagShip, or the Imperial to help a pair shot.
- `COMMANDER_NEXT.md`, `GAP_MAP.md`, the sheet index, and the other ship-stage sheets.

## Commander decision

Reply with one of these three. Pass means every item in this sheet holds. Hold-WebGL means one of the same three off-ramp conditions on the [P1 acceptance](cockpit-ship-stage-p1-acceptance.md) is true for this wave. Any other miss is Fail.

The P1 pass left Hold-WebGL closed. Reopening it takes one of the three off-ramps below. This wave does not reopen it on its own.

### Pass

Both hulls pass the three-quarter and head-on reads, at ~140px and at the hero crop, at shields 0 and shields full. The Sentinel reads as the fortress (`armor`). The Interdictor reads as the barge (`hoop`). They stay apart from each other, from the Colonial the hauler wave puts on screen, and from the Constellation fleet-order batch 4 puts on screen. The Colonial re-shot and the Constellation re-shot pass, and those faces stay where the earlier cuts put them. The marker rows match the formula, including the Sentinel at 25 and the Interdictor at 1,000, and no marker box cuts the silhouette. No marker sits in the Interdictor's hole or on the skin. Shields empty keeps `#62f0c8` and `#ff5cab`. CU-seat, reduced motion, and the phone still stay on the canonical still, and the Interdictor still draws 1,000 darts. The drift frame time at 1,000 is recorded on the Interdictor. The cumulative mesh file is under 40 KB gzipped, with face counts recorded. The named tests move in the same change. Stay on the shared SVG (`buildHullFaces` / `projectFace`). WebGL stays the closed off-ramp. Every other hull waits.

### Fail

A pass item is missed, and none of the three off-ramp conditions are true. This wave has not cleared the bar. Tholian Sentinel, Interdictor Cruiser, and the other hulls still on `fleet-glass-v1` stay there. The next edit stays on `buildHullFaces` / `projectFace`. A missed pair shot is a miss on the new hull. Colonial faces stay as the hauler wave left them. Constellation faces stay as batch 4 left them. Imperial faces stay as the P1 pass left them. A missed 1,000-marker frame uses the group transform or the markers-only canvas layer from the render memo. The count stays `max(1, ceil(n / 100))` when `n ≥ 1`. Hold-WebGL stays closed. The four-hull cuts and the earlier batches, once merged, stay merged.

### Hold-WebGL

Closed. It opens only after this art pass, and only when this wave fails one of the same three off-ramps:

- The Tholian Sentinel and the Interdictor Cruiser still fail the read test at hero size.
- Drift of the Imperial plus 500 markers, or a static frame of 1,000 markers, cannot hold a 16 ms update on a mid laptop and a phone-class CPU.
- A planet disc and a warp camera cannot be expressed in the SVG the clips already animate.

That spike consumes the face list from `buildHullFaces`. It does not introduce a second hull file. Warp clips stay SVG until their own note. A miss that is not one of those three is Fail, and the next edit stays on the shared SVG.
