# Batch 5 brick and hoops — ship stage P1b

Parents: [P0 pack](cockpit-ship-stage-p0.md), [silhouette bible](cockpit-ship-stage-p0-silhouette-bible.md), [render decision](cockpit-ship-stage-p0-render.md), [marker math](cockpit-ship-stage-marker-math.md), [P1 acceptance](cockpit-ship-stage-p1-acceptance.md), [four-hull wave](cockpit-ship-stage-p1b-next-hulls.md), [hauler wave](cockpit-ship-stage-p1b-batch2-haulers.md), [gun wave](cockpit-ship-stage-p1b-batch3.md), [fleet order](cockpit-ship-stage-p1b-fleet-order.md).

Stills for this sheet are listed in the [stills inventory](stills/README.md) (#344) under [p1b-batch5-brick](stills/p1b-batch5-brick/).

Docs only. This sheet does not change `web/*`, the engine, or tests. Classic top-and-front ANSI for every hull stays **UNVERIFIED**. Do not open, trace, or approximate EIS prints, EIS wallpaper, or Drew Markham ANSI. Looks below are invented from the public role numbers on `SHIP_SPECS_TW2002` and `SHIP_ROSTER_LIVE_TABLE` in `src/tw2k/engine/constants.py`, and from the one-paragraph pictures already in the bible. This sheet is the mesh contract for the specialty wave after the guns in [cockpit-ship-stage-p1b-batch3.md](cockpit-ship-stage-p1b-batch3.md), so a follow-on does not turn the armor slabs into the Colonial's cabin, and does not turn the two hoops into the Constellation's X or the Star Master's dish.

Product stills scaffold: [batch 5 brick product](cockpit-ship-stage-p1b-batch5-brick-product.md) (#340, `75997134`). Stills directory: [p1b-batch5-brick](stills/p1b-batch5-brick/). The scaffold does not stamp Pass. It ships no PNGs. Measured cells stay TBD until product.

## Implement after the spike and the earlier P1b batches

Do not start these meshes until all of these have landed and passed the read bar:

1. The Merchant Cruiser and Imperial StarShip spike has merged and passed the render memo's pass list (read test, accent at zero shields, 100:1 markers, clip cameras, size). That pass list includes the throwaway 1,000-marker ring on the Imperial, standing in for the later Interdictor, and a recorded static frame at 1,000. The acceptance sheet names the same row. This wave does not recut that stand-in.
2. The batch 1 remainder has merged and passed the same bar: Escape Pod, T'Khasi Orion. Scout Marauder and Merchant Freighter sit in the four-hull wave, not in this remainder.
3. The four-hull wave has merged and passed the same bar: Scout Marauder, Merchant Freighter, BattleShip, Corporate FlagShip.
4. The hauler wave has merged and passed the same bar: CargoTran, Colonial Transport, Taurean Mule.
5. The gun wave has merged and passed the same bar: Missile Frigate, Havoc GunStar, judged with the BattleShip from the four-hull wave.
6. Fleet-order batch 4 has merged and passed the same bar: Star Master, Constellation, Corporate FlagShip. The FlagShip's tower contract already landed in the four-hull wave. Batch 4 is still the gate, so the dish, the X, and the tower are on screen together before a hoop is cut.

Fleet order names this cut as its batch 5: Tholian Sentinel, Interdictor Cruiser. Two hulls, on purpose. The Interdictor's full bay is 1,000 markers outside a hoop that is larger than the body. That measurement is the Cur. A third new silhouette in the same PR would hide a frame miss inside an art miss.

The gate is the stricter one. The Colonial's cabin has to be on screen before the brick is cut. The Constellation's X has to be on screen before the hoops are cut. The Star Master's dish has to be on screen so a hoop is not drawn as a plate. An ordinary marker ring has to have shipped, which it has once the spike's ring is on screen, before the brick and the hoops are cut. The spike's throwaway 1,000 has to be measured before this hull's real 1,000 is the pass.

Build the two hulls below on the same `buildHullFaces` / `projectFace` path, in the order at the bottom, and stop there. Every other player hull stays on `fleet-glass-v1` until these two pass the same bar, judged with the merged Colonial and the merged Constellation. If the spike misses the bar and opens the WebGL off-ramp, these silhouettes still apply. The renderer does not get to redesign them. The off-ramp still consumes `buildHullFaces`. It does not add a second hull file, and it does not get a head start by meshing these two.

Shared rules, inherited from the four-hull sheet, the hauler sheet, and the gun sheet:

- Dark blue-grey metal. The accent is a stripe, a canopy edge, and the kit. Canopy glass is a cool white mixed with the accent. Idle engines are a short cyan-white cone. A fitted TransWarp drive (`ship.transwarp.fitted`) turns that cone magenta and nothing else. Neither hull is on `SHIP_TW_CHART_RANGE`. The chart prints no hop ceiling for these keys. The pass pose is idle cyan-white cones. A drive recolor is the inherited rule, and it is not a signature of this wave.
- Empty shields leave scars and a missing bubble. The class accent stays. A full red body fails. A full mint body on the Sentinel fails. A full pink body on the Interdictor fails.
- Fighter markers: `n < 1 → 0`, else `max(1, ceil(n / 100))`. Fill `#ff2a2a`, stroke `#ff8888`. One dart is 100 fighters. A bay of 1–99 is one marker, a partial hundred, and that dart gets no numeral. A bay of 100 is still one marker. The stat line keeps the exact bay. The legend is `each marker = 100 fighters`. The count is the onboard bay, not fighters per attack. Markers yaw with the hull. They are escorts, not corner ticks. The count formula does not gain a silent cap.
- The ring's innermost world radius is the bounding sphere of every face, including the kit named for that hull, plus a gap. On the canonical three-quarter pose and in the head-on clip, no marker's screen box intersects the hull silhouette. The Interdictor's ring is outside the hoops, not in the hole and not on the skin.
- Canonical three-quarter is yaw `0.82`, pitch `0.5` (the held pose). Head-on is the warp clip camera `headon`. The side clip camera still has to show the same kit.
- The signature part has to read with the name plate covered, at about 140px tall and at a hero crop about 55% of the deck. A part that only exists in one of those views is not a signature.
- Kit names are the `PARTS` keys already in the bible (`armor`, and `hoop`). Where the current `detail` string names a different part, that token is called out on the hull. Do not grow a second signature.
- Section tokens stay the ones the loft already uses: `box` on the Sentinel and on the Interdictor. This wave adds no fourth section. The hoops are kit, not a section.
- The picture follows the job, not the hold grant. Where the live roster changes the grant, the entry says so. Fighter caps do not move on these hulls. Shields, photons, and mines stay on the base spec.

## Why these hulls

Fleet order's specialty group is the crescent, the brick, and the hoops. The crescent shipped in batch 1 beside the Scout. The brick and the hoops wait until an ordinary ring has shipped, and they wait until the pairs they can be mistaken for are already on screen. This wave is those two. No third silhouette.

Trading index is the published formula `(hold ceiling / turns per warp) × 10`, rounded to the nearest integer. `OldBBS_TW2002V8.faq.txt` prints the same figures. It is a role number, not a picture. The Sentinel ties the Scout at 125 and stays a brick. The Interdictor is the hoop barge at 27, the figure the hauler sheet already records, and the hoops do not shrink to match it.

| Hull | Key | Turns per warp | Hold ceiling | Index | This wave |
| --- | --- | --- | --- | --- | --- |
| Interdictor Cruiser | `interdictor_cruiser` | 15 | 40 | 27 | new mesh |
| Tholian Sentinel | `tholian_sentinel` | 4 | 50 | 125 | new mesh |
| Scout Marauder | `scout_marauder` | 2 | 25 | 125 | batch 1, already the needle |
| Star Master | `star_master` | 3 | 73 | 243 | fleet-order batch 4 |
| Constellation | `constellation` | 3 | 80 | 267 | fleet-order batch 4, re-shot |
| Colonial Transport | `colonial_transport` | 6 | 250 | 417 | hauler wave, re-shot |

Star Master (243) and Constellation (267) stay in fleet-order batch 4, with the Corporate FlagShip, so the dish, the X, and the tower are judged together before this cut. The Colonial (417) already has a contract. That does not pull its cabin into the brick. Escape Pod and T'Khasi Orion are the batch 1 remainder. This sheet does not go back for them, and it does not recut them.

| Order | Key | Panel name | Why it is in this wave |
| --- | --- | --- | --- |
| 1 | `tholian_sentinel` | Tholian Sentinel | Fortress. 47,500 credits, 4 turns per warp, ceiling 50, 2,500 fighters, 4,000 shields, odds 1.0, index 125. The shortest, bluntest brick. Armor slabs make the head-on view nearly square. `SCANNER_BY_HULL` is holo. No dish grows to explain that. Not on `SHIP_TW_CHART_RANGE`. |
| 2 | `interdictor_cruiser` | Interdictor Cruiser | The barge. 539,000 credits, 15 turns per warp, ceiling 40, 100,000 fighters, 4,000 shields, odds 1.2, index 27. A heavy body inside two hoops. The full bay is the 1,000-marker case the spike only stood in for. `SCANNER_BY_HULL` is holo. Not on `SHIP_TW_CHART_RANGE`. |

`SHIP_SPECS_TW2002` spells both `display_name` values the way the panel spells them: `Tholian Sentinel` and `Interdictor Cruiser`. The mesh keeps those names. Do not rename either hull.

Offensive odds of 1.0 on the Sentinel, and the corp-planet defense at `THOLIAN_CORP_DEFENSE_ODDS` (4.0) when the special hull rules are on, do not add a kit, a second colour, or a tower. The fortress is the brick. Odds of 1.2 on the Interdictor do not add prongs. `COMBAT_INTERDICT_HULLS` names this cruiser. The hold is the two hoops. A generator mast, a third ring, and a nose collar are other parts. Fifty mines and one genesis on the Sentinel, and 200 mines and 20 genesis on the Interdictor, do not add a launcher or a row of doors. Photons stay 0 on both, so neither hull grows the Frigate's dorsal pair.

## Tholian Sentinel — `tholian_sentinel`

### Role read

Cover the name plate. At 140px and at the hero crop the ship reads as a fortress: the shortest, bluntest brick, armor slabs on both flanks, a head-on view nearly square, a stub nose. A reader calls it a plated block and does not call it fast. The slabs are the signature from the three-quarter pose, from head-on, and from the side clip. Twenty-five markers are the Merchant's escort count on a much smaller body, and they do not replace the square. This is the hull the Colonial's cabin must stay distinct from.

### Numbers

Base row and the live roster match on every field this picture uses. Turns per warp are 4. Odds are 1.0. Shields stay 4,000. Mines 50, genesis 1, photons 0. Fighters per attack stay 800, and that figure is not the marker count. A full bay is 2,500 fighters, which is 25 markers. Two engines. `SCANNER_BY_HULL["tholian_sentinel"]` is holo. Not on `SHIP_TW_CHART_RANGE`. Transporter range on `SHIP_TRANSPORT_RANGE` is 3. Range does not add a dish or a door.

| | Cost | Grant holds | Hold ceiling | Fighters | Markers at cap |
| --- | --- | --- | --- | --- | --- |
| Base `SHIP_SPECS_TW2002` | 47,500 | 10 | 50 | 2,500 | 25 |
| Live `SHIP_ROSTER_LIVE_TABLE` | 47,500 | 10 | 50 | 2,500 | 25 |

The grant is 10 holds against a ceiling of 50. The brick does not shrink to the grant and does not swell to the ceiling. The fighter cap does not move, so the escort count at the cap is 25 on both rosters. The yard cost stays 47,500. The 4,000 shield cap is the same number the Interdictor carries. It does not paint this body mint, and it does not grow a second bubble colour.

### Silhouette

Section `box`. The shortest, bluntest body in the fleet. Today's `LOFT` stations run from x=22 to x=−44, and sz reaches 36. Armor slabs sit on both flanks, outside that loft, and they make the head-on view nearly square. The nose is a stub. Nothing on the outline suggests speed. No belly tanks. No cabin row as the main shape.

A box loft already paints a short row of lit ports. On this hull that row stays short and stays the shared box material. It is not the Colonial's flank of cabins. Port glass stays the shared cool white mixed with the accent. It does not become the tell.

Two engines sit low in the tail, inside the beam, inside the slab line. They do not stick out past the slabs, and they do not stick up past the brick. Engines past the flanks would suggest speed, and this outline does not.

Kit: `armor`. `SHIPS` sets `detail` to `"bridge"`. The `bridge` token is the shared canopy, and it stays shorter than the slabs. Do not grow a second signature beside the plating. A holo scanner does not grow the Star Master's mast. One genesis does not add a door. Fifty mines do not add a launcher. Odds of 1.0 do not add a gun. The 4:1 corp-planet defense does not add a kit.

Today's armor is two metal slabs, 28 long, about 30 tall, and 8 thick, set outside the loft, plus a nose plug. The slabs are dark metal, so the mint is only the stripe and the square does not read. The mesh pass replaces that read. The slabs are the flanks, they carry `#62f0c8`, and head-on is nearly square. The nose plug stays a stub. It does not become a wedge, a castle, or a prow.

Distinct from the Colonial Transport: the Colonial is a fat box, tall for its length, with two belly tanks and a cabin row as the signature. This hull is short and plated. The Colonial is re-shot from the hauler wave. Do not recut it, and do not borrow its tanks. Distinct from the Scout Marauder: the index tie at 125 is a role number. The Scout is the long needle with canards. This body is the short one, and it has no canards. Distinct from the Merchant Freighter: the Freighter is short and very wide, and its cheeks set a broad face. This head-on view is nearly square, and the width is armor, not cargo cheeks. Distinct from the CargoTran: the CargoTran is a long flat deck with a girder. This brick has no dorsal spine. Distinct from the Interdictor Cruiser: both are `box`, and both carry 4,000 shields. This outline has no hoop. A ring around the brick fails, because that is the barge.

The outline carries no belly tanks, no cabin row as the main shape, no canards, no cheek tanks, no girder, no turret pair, no prongs, no dish, no tower, no castle, and no hoop. A borrowed Imperial radius (~121) or Merchant radius (~93) leaves the fortress in a hole. Use the sphere of this brick.

### Accent

`#62f0c8` on the slab faces and the stripe. The fuselage between the slabs stays dark metal, so the plating reads as two flanks and the body does not become a mint block. At shields 0 the slab faces and the stripe are still `#62f0c8`. Engine cones stay cyan-white unless a drive is fitted, and then only the cones change. Colonial green is `#7dff7d`, and it stays on the Colonial's stripe and tank rims. That green does not replace this mint.

### Three-quarter checklist

Pose: yaw `0.82`, pitch `0.5`. Name plate covered. Repeat at shields 0 and at shields full, at about 140px and at the hero crop. Repeat once in a frame that also shows the merged Colonial.

1. Armor slabs break both flanks. The body reads as a short blunt brick.
2. The nose is a stub. Canards fail, because that is the Scout. A wedge nose fails, because that is a trader.
3. No belly tanks and no cabin row as the main shape. A tall box with tanks and a port row fails, because that is the Colonial.
4. Beside the Colonial, the tanks and the cabin stay on the Colonial and the slabs stay on this hull.
5. The slab faces and the stripe are `#62f0c8` at shields 0. A full mint body fails. A full red body fails.
6. Every marker sits outside the slabs. No marker screen-box intersects the silhouette.

### Head-on checklist

Clip camera `headon`. Same shield pair, same two sizes.

1. The face is nearly square. The slabs are the sides of that square.
2. The nose is a stub in the middle of the square. It is not a broad cheek face and not a tall cabin.
3. Two engine mouths sit low, inside the square, not past the slabs.
4. The frame shows no belly tanks, no hoop, no dish, no X of nacelles, and no canards.
5. Markers clear the slabs. No marker screen-box intersects the silhouette.

### Marker clearance

| Bay | Markers |
| --- | --- |
| 0 | 0 |
| 1–99 | 1 |
| 100 | 1 |
| 101–200 | 2 |
| 2,400 | 24 |
| 2,401–2,499 | 25 |
| 2,500 (cap, both rosters) | 25 |

A bay of 1–99 is one marker, a partial hundred, with no numeral. From 2,401 through 2,499 the count is already 25 and the last dart is a partial hundred, so it gets no numeral. The cap is an exact two thousand five hundred. The twenty-fifth dart is a full hundred and still carries no numeral. Fighters per attack of 800 would draw 8 darts. The checklist uses the bay.

The sphere includes the loft, both armor slabs, the stub nose, the canopy, and both engines. The slabs set the beam. A length-only radius leaves markers in the slab silhouette. Twenty-five markers is the count the Merchant spike already drew, on this hull's sphere. Do not borrow the Merchant radius (~93). Do not borrow the Imperial radius (~121). A borrowed capital ring leaves the fortress in a hole. Today's `fighterSlots` start at radius 56, inside the body. Ticks on the brick fail. The grouping fix in the render memo is not the remedy here. The cloud is 25. The clearance problem is the brick.

## Interdictor Cruiser — `interdictor_cruiser`

### Role read

Cover the name plate. The ship reads as the barge: a heavy body inside two hoops. The hoops are larger than the hull and are the first shape in every camera. Head-on is a ring with a body in the hole. A reader calls it a ship inside rings, and does not call it an X of engines or a dish on a stick. A full bay is 1,000 markers, orbiting outside the hoops. The cloud does not fill the hole, and it does not replace the rings. This is the hull the spike's throwaway 1,000-marker ring was standing in for. The pass is this mesh, not that stand-in.

### Numbers

Base row, then the live roster where a field moves. Turns per warp are 15 on both. Odds are 1.2 on both. Shields stay 4,000. Mines 200, genesis 20, photons 0. Fighters per attack stay 15,000, and that figure is not the marker count. A full bay is 100,000 fighters, which is 1,000 markers. Four engines. `SCANNER_BY_HULL["interdictor_cruiser"]` is holo. Not on `SHIP_TW_CHART_RANGE`. Transporter range on `SHIP_TRANSPORT_RANGE` is 20. Range does not add a dish or a door.

| | Cost | Grant holds | Hold ceiling | Fighters | Markers at cap |
| --- | --- | --- | --- | --- | --- |
| Base `SHIP_SPECS_TW2002` | 539,000 | 20 | 40 | 100,000 | 1,000 |
| Live `SHIP_ROSTER_LIVE_TABLE` | 539,000 | 10 | 40 | 100,000 | 1,000 |

The live grant is 10 holds against a base grant of 20 and a ceiling of 40. The picture does not shrink to match that grant, and the body does not swell to the ceiling. The fighter cap does not move, so the escort count at the cap is 1,000 on both rosters. The yard cost stays 539,000. The 4,000 shield cap matches the Sentinel and does not paint this body pink.

### Silhouette

Section `box`. A heavy body inside two hoops. The hoops are larger than the hull and are the first shape from the side, from above, and head-on. Head-on is a ring with a body in the hole. The hole is empty. Nothing else in the fleet wears a hoop.

Four engines sit in the tail, inside the hoops, in a low row on the body. They do not trail past the hoops, and they do not form an X. An X of nacelles is the Constellation. Engines outside the rings make that X and fail.

Kit: `hoop`. `SHIPS` sets `detail` to `"ring bridge"`. The `ring` token is not a second kit. Today's loft already skips the eight-box nose ring when `PARTS` is `hoop`. Keep that skip. Do not grow a nose collar, and do not grow a third hoop. The `bridge` token is the shared canopy, inside the body, shorter than the hoops. A holo scanner does not grow the Star Master's mast. A plate in the hole is that dish and fails. Two hundred mines do not add a launcher. Twenty genesis torpedoes do not add a row of doors. Photons stay 0, so the dorsal missile pair does not appear. Odds of 1.2 do not add prongs.

Today's hoops are two washers on the mid station `[6, 18, 28]`. Inner radius is `max(18, 28) + 3 = 31`. Outer radius is 37.5. They sit at x=16 and x=−10. The aft washer is slightly smaller and it is metal, so one hoop can disappear into the hull. Body stations run from x=42 to x=−72, longer than the hoop span. The render memo measures this glass at 215 faces, AABB 136×75×75, bounding radius ~108, against the Merchant's 162×32×64 (~93) and the Imperial's 219×51×66 (~121). The 75 in that box is the current hoop diameter. Fleet order says ~108 is a floor, not the radius to ship, because the bible hoops grow until they are larger than the hull and the first shape in every camera. The mesh pass grows both hoops until that is true, both rims `#ff5cab`, both open, and then remeasures. Do not ship ~108. Do not start the ring at `fighterSlots` radius 56. That start is inside the body.

Distinct from the Constellation: the Constellation's head-on tell is an X of four nacelles, and the nacelles trail past the tail. This head-on tell is a ring with a body in the hole. The Constellation is re-shot from batch 4. Do not recut the X. Distinct from the Star Master: the dish is a plate on a mast, wider than that hull's beam, and the top view is a circle on a stick. These hoops go around the body. They are rings, not a filled plate, and they have no mast. The Star Master is not recut. Distinct from the Imperial StarShip: the Imperial is the long castle and a square of four bells. The spike drew 1,000 markers outside those bells as a throwaway. This hull's 1,000 markers orbit outside the hoops. Do not pass this mesh by reshooting the Imperial. Distinct from the Corporate FlagShip: the FlagShip's head-on tell is a rectangle on the centerline. This head-on tell is a hole. Distinct from the Tholian Sentinel: the Sentinel is the short plated brick, nearly square, with no ring. A brick with slabs and no hoops is that fortress.

The outline carries no X of nacelles, no dish, no mast, no castle, no tower, no turret pair, no prongs, no dorsal missiles, and no armor slabs as the main shape. The short port row a box loft already paints stays subordinate. It is not a cabin, and it is not the signature.

### Accent

`#ff5cab` on both hoop rims and the stripe. The holes stay open and the body stays dark metal, so head-on reads as a ring with a body in the hole, not as a pink wedge and not as a filled disc. At shields 0 the rims and the stripe are still `#ff5cab`. Engine cones stay cyan-white unless a drive is fitted, and then only the cones change. The cones are not the Constellation's `#d0d6ff` nacelles, and they are not a second accent on the hoops. Gold is the Imperial's accent. Magenta on a tower is the FlagShip. Neither colour appears on these rims.

### Three-quarter checklist

Same pose, sizes, and shield pair as the Sentinel. Repeat once in a frame that also shows the merged Constellation.

1. Two hoops break the outline from the side and from above. They are larger than the body, and they are the first shape.
2. The body sits inside the hoops. A wide X of nacelles trailing past the tail fails, because that is the Constellation.
3. Beside the Constellation, the X stays on the Constellation and the hoops stay on this hull.
4. The hoop rims and the stripe are `#ff5cab` at shields 0. A full pink body fails. A filled disc fails, because that is the Star Master's plate.
5. No mast, no castle, and no armor brick as the main shape.
6. Markers sit outside the hoops. None sit in the hole and none sit on the skin. No marker screen-box intersects the silhouette.

### Head-on checklist

Same shield pair.

1. A ring with a body in the hole. The rims are `#ff5cab`. The hole is empty.
2. The hole is not a filled plate, not a third prong, and not a marker.
3. Four engine mouths sit on the body, inside the ring. An X of four nacelles fails, because that is the Constellation. A square of bells fails, because that is the Imperial.
4. The frame shows no dish on a mast, no tower rectangle, and no nearly square armor brick.
5. Markers clear the outer rim. No marker screen-box intersects the silhouette.

### Marker clearance

This is the 1,000-marker case. The render memo's spike pass list draws a throwaway 1,000-marker ring on the Imperial, standing in for the later Interdictor, and records one static frame at 1,000. The acceptance sheet names that row in the marker table: 100,000 fighters, drawn on the Imperial, 1,000 markers, a throwaway ring, measure it, and the formula has no silent cap. Marker math repeats the same case and points at fleet order, which states it as 1,000 markers at 100,000 fighters. This hull is that later case. The count is the onboard bay on the Interdictor. The pass is 1,000 markers outside these hoops. Do not pass the hull by reshooting the Imperial's stand-in, and do not leave the 1,000 on the castle.

Record the drift frame time at 1,000 on this hull, the one whose hoops are real. The spike's recorded 1,000 is a static frame on the Imperial. This wave adds the drift time on the real rings. Reuse the marker grouping the spike recorded for that throwaway ring: one group moved by a transform, or one canvas layer for markers only. A naive per-frame DOM write of 1,000 nodes can miss a phone frame even when the hull is cheap. If 1,000 separate SVG paths miss the frame, that grouping is the fix. It is not a silent change to `ceil(n / 100)`, and it is not three.js, unless the render memo's off-ramp conditions are already met. The count formula does not gain a silent cap.

Phone still, reduced-motion still, and `body.cu-seat` still hold the pose. They draw the 1,000 count and they do not loop. Live idle is the orbit those stills do not run. The drift measurement is that orbit. The stills still have to show 1,000 darts outside the hoops.

| Bay | Markers |
| --- | --- |
| 0 | 0 |
| 1–99 | 1 |
| 100 | 1 |
| 101–200 | 2 |
| 50,000 | 500 |
| 99,900 | 999 |
| 99,901–99,999 | 1,000 |
| 100,000 (cap, both rosters) | 1,000 |

A bay of 1–99 is one marker, a partial hundred, with no numeral. A bay of 100 is still one marker. 50,000 is the Imperial cap and draws 500. This bay does not stop there. From 99,901 through 99,999 the count is already 1,000 and the last dart is a partial hundred, so it gets no numeral. The cap is an exact hundred thousand. The thousandth dart is a full hundred and still carries no numeral. Fighters per attack of 15,000 would draw 150 darts. The checklist uses the bay.

The sphere includes the loft, both hoops, the canopy, and the four engines. The hoops set the radius, after they have grown past today's glass. A ring sized to the fuselage clips the hoops and fails. A ring left at the measured ~108 clips the grown hoops and fails. A marker in the hole reads as cargo, or as a filled dish, and fails. A marker on the skin fails. One thousand markers is the stress case. Do not cap the formula. Do not borrow the Imperial radius (~121) from the stand-in. The clearance problem is the hoops and the count together.

## Colonial Transport — re-shot, not a new mesh

The mesh contract is [Colonial Transport](cockpit-ship-stage-p1b-batch2-haulers.md#colonial-transport--colonial_transport) in the hauler wave. This wave does not recut it, does not borrow its tanks onto the brick, and does not edit that sheet. The lines below are the re-shot, so the Sentinel has its pair on screen.

### Role read

Cover the name plate. The ship still reads as a slow colonist: a fat box, tall for its length, two belly tanks, a row of cabin ports. The cabin and the tanks are the signature. The Sentinel's slabs are the other hull.

### Numbers

Base row and the live roster match. Turns per warp are 6. Odds are 0.6. Shields stay 500. Mines 0, genesis 5, photons 0. Two engines. The fighter cap does not move.

| | Cost | Grant holds | Hold ceiling | Fighters | Markers at cap |
| --- | --- | --- | --- | --- | --- |
| Base `SHIP_SPECS_TW2002` | 63,600 | 50 | 250 | 200 | 2 |
| Live `SHIP_ROSTER_LIVE_TABLE` | 63,600 | 50 | 250 | 200 | 2 |

The grant is 50 holds against a ceiling of 250. The box does not shrink. The hauler checklist is the pass list. This wave adds the pair shot below.

### Silhouette

Section `box`. Kit: `cargo` (the belly tanks). Accent `#7dff7d` on the stripe and the tank rims. Port glass is a warm white so the green stripe stays the accent. At shields 0 the rims and the stripe are still `#7dff7d`. The outline still carries no armor slabs as the main shape. The Sentinel is the short plated brick. Do not move those slabs onto this cabin.

### Re-shot checklist

Same pose, sizes, and shield pair as the hauler sheet. Name plate covered. Repeat at about 140px and at the hero crop, once beside the Sentinel.

1. The flank reads as a tall box, high for its length, with a cabin row.
2. Two belly tanks break the underside.
3. Beside the Sentinel, the slabs stay on the Sentinel. This hull does not grow them.
4. The tank rims and the stripe are `#7dff7d` at shields 0. The Sentinel's mint does not replace them.
5. Markers sit outside the top of the box and outside the tanks. The cap is 2. No marker screen-box intersects the silhouette.

## Constellation — re-shot, not a new mesh

The mesh contract is fleet-order batch 4, from the bible entry [constellation — Constellation](cockpit-ship-stage-p0-silhouette-bible.md#constellation--constellation) and the fleet-order entry [Constellation](cockpit-ship-stage-p1b-fleet-order.md#12-constellation--mid--batch-4). This sheet does not write that contract, does not recut the X, and does not edit those sheets. The lines below are the re-shot, so the hoops have their pair on screen.

### Role read

Cover the name plate. The ship still reads as a mid combat hull with four nacelles in an X. Head-on is that X and little else. The Interdictor's hoops are the other hull.

### Numbers

Base row and the live roster match on every field this picture uses. Turns per warp are 3. Odds are 1.4. Shields stay 750. Mines 25, genesis 2, photons 0. Fighters per attack stay 2,000, and that figure is not the marker count. A full bay is 5,000 fighters, which is 50 markers. Four engines. Not on `SHIP_TW_CHART_RANGE`. The fighter cap does not move.

| | Cost | Grant holds | Hold ceiling | Fighters | Markers at cap |
| --- | --- | --- | --- | --- | --- |
| Base `SHIP_SPECS_TW2002` | 72,500 | 20 | 80 | 5,000 | 50 |
| Live `SHIP_ROSTER_LIVE_TABLE` | 72,500 | 20 | 80 | 5,000 | 50 |

The grant is 20 holds against a ceiling of 80. The X does not shrink. The batch 4 checklist is the pass list. This wave adds the pair shot below.

### Silhouette

Kit: `quad`. Accent `#d0d6ff` on the nacelles and the stripe. At shields 0 the nacelles and the stripe are still `#d0d6ff`. Head-on is the X and little else. The nacelles trail past the tail. The X, not the fuselage, sets the sphere. No castle, no dish, no prongs, and no hoop around the body. Markers sit outside the arms. The cap is 50.

### Re-shot checklist

Same pose and the same two sizes as batch 4. Name plate covered. Repeat at shields 0 and at shields full, once beside the Interdictor.

1. Head-on is an X of four nacelles, and little else.
2. The nacelles trail past the tail. Two hoops around the body fail, because that is the Interdictor.
3. Beside the Interdictor, the X stays on this hull and the hoops stay on that one.
4. The frame shows no castle, no dish, and no prongs.
5. The nacelles and the stripe are `#d0d6ff` at shields 0.
6. Markers sit outside the arms. The cap is 50. No marker screen-box intersects the silhouette.

## Wave read test

Cover the name plate. These pairs have to stay apart at 140px and at the hero crop, on the three-quarter pose and head-on. The bible's full-fleet table still applies. This is the subset this wave can get wrong while cutting the two new faces, with the Colonial and the Constellation already on screen from earlier batches.

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

## Build order

Tholian Sentinel, then Interdictor Cruiser. The brick goes first so the merged Colonial has its pair on screen and the slabs are locked as a short square before any ring is cut. The hoops are second, so they can be judged against the merged Constellation, and so the 1,000-marker drift is recorded on a hull whose silhouette is already those hoops. Stop. Do not recut the Colonial. Do not recut the Constellation. Do not start a third silhouette in this pass. Do not go back for the Escape Pod or the T'Khasi Orion.

Done when both new hulls pass their checklists, the Colonial and Constellation re-shots pass, the wave read test passes, and the inherited P1 bar holds (legend, exact bay on the stat line, side clip, phone still, reduced-motion still, `body.cu-seat` still, mesh module still under 40 KB gzipped). Show the two the way the gun wave shows its set, shields empty and shields full. Marker clouds in this wave are 25 and 1,000. The Colonial's 2 and the Constellation's 50 are already on the merged hulls. The clearance problem on the Sentinel is the brick. The clearance problem on the Interdictor is the hoops and the 1,000-marker count together. Record the drift frame time at 1,000 on the Interdictor. Reuse the spike's throwaway grouping. Do not cap the formula.

## Out of scope

The P1 spike hulls, including the Imperial, except that the throwaway 1,000-ring on the Imperial is the measurement this wave replaces with the real Interdictor ring. The batch 1 remainder (Escape Pod, T'Khasi Orion). The four-hull wave (Scout Marauder, Merchant Freighter, BattleShip, Corporate FlagShip). The hauler wave (CargoTran, Colonial Transport, Taurean Mule), except the Colonial re-shot named above. The gun wave (Missile Frigate, Havoc GunStar, and the BattleShip re-shot already specified). Fleet-order batch 4 (Star Master, Constellation, Corporate FlagShip), except the Constellation re-shot named above. Ferrengi hulls. Any edit under `web/`, any engine change, any test change, and any rewrite of `COMMANDER_NEXT.md`, `GAP_MAP.md`, `cockpit-ship-stage-INDEX.md`, `cockpit-ship-stage-p0.md`, `cockpit-ship-stage-p0-silhouette-bible.md`, `cockpit-ship-stage-p0-render.md`, `cockpit-ship-stage-p0-fx.md`, `cockpit-ship-stage-marker-math.md`, `cockpit-ship-stage-p1-acceptance.md`, `cockpit-ship-stage-p1b-next-hulls.md`, `cockpit-ship-stage-p1b-batch2-haulers.md`, `cockpit-ship-stage-p1b-batch3.md`, `cockpit-ship-stage-p1b-fleet-order.md`, `cockpit-ship-stage-p2-wire.md`, or `cockpit-ship-stage-p3-layout.md`. New events, new actions, and a layout split. Copying or tracing EIS, Markham, or ANSI ship art.
