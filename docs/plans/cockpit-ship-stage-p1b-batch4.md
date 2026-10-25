# Batch 4 dish, X, and the other capital — ship stage P1b

Parents: [P0 pack](cockpit-ship-stage-p0.md), [silhouette bible](cockpit-ship-stage-p0-silhouette-bible.md), [render decision](cockpit-ship-stage-p0-render.md), [four-hull wave](cockpit-ship-stage-p1b-next-hulls.md), [hauler wave](cockpit-ship-stage-p1b-batch2-haulers.md), [gun wave](cockpit-ship-stage-p1b-batch3.md), [fleet order](cockpit-ship-stage-p1b-fleet-order.md).

Docs only. This sheet does not change `web/*`, the engine, or tests. Classic top-and-front ANSI for every hull stays **UNVERIFIED**. Do not open, trace, or approximate EIS prints, EIS wallpaper, or Drew Markham ANSI. Looks below are invented from the public role numbers on `SHIP_SPECS_TW2002` and `SHIP_ROSTER_LIVE_TABLE` in `src/tw2k/engine/constants.py`, and from the one-paragraph pictures already in the bible. This sheet is the mesh contract for the dish and the X after the guns in [cockpit-ship-stage-p1b-batch3.md](cockpit-ship-stage-p1b-batch3.md), so a follow-on does not turn the plate into the Interdictor's hoop or the FlagShip's tower, and does not turn the X into the Imperial's square of bells or the Havoc's prongs.

## Implement after the spike, the four, the haulers, and the guns

Do not start these meshes until all four of these have landed:

1. The Merchant Cruiser and Imperial StarShip spike has merged and passed the render memo's pass list (read test, accent at zero shields, 100:1 markers, clip cameras, size).
2. The four-hull wave has merged and passed the same bar: Scout Marauder, Merchant Freighter, BattleShip, Corporate FlagShip.
3. The hauler wave has merged and passed the same bar: CargoTran, Colonial Transport, Taurean Mule.
4. The gun wave has merged and passed the same bar: Missile Frigate, Havoc GunStar, and the BattleShip re-shot.

Fleet order names this cut as its batch 4: Star Master, Constellation, Corporate FlagShip. The FlagShip mesh contract already landed in the four-hull wave. This sheet does not rewrite it and does not recut that tower. The new meshes are the two hulls in that batch that have no contract yet. The gate is the stricter one. The FlagShip's tower and the Imperial's castle have to be on screen before the dish is cut. The Imperial's square of bells and the Havoc's prongs have to be on screen before the X is cut. The gun-wave kits have to be on screen so the dish stays a plate on a mast, and the X stays four nacelles.

Build the two hulls below on the same `buildHullFaces` / `projectFace` path, in the order at the bottom, and stop there. Every other player hull stays on `fleet-glass-v1` until these two pass the same bar, judged with the merged FlagShip and the merged Imperial. If the spike misses the bar and opens the WebGL off-ramp, these silhouettes still apply. The renderer does not get to redesign them.

Shared rules, inherited from the four-hull sheet, the hauler sheet, and the gun sheet:

- Dark blue-grey metal. The accent is a stripe, a canopy edge, and the kit. Canopy glass is a cool white mixed with the accent. Idle engines are a short cyan-white cone. A fitted TransWarp drive (`ship.transwarp.fitted`) turns that cone magenta and nothing else. Neither new hull is on `SHIP_TW_CHART_RANGE`. Their pass pose is idle cyan-white cones. A drive recolor is the inherited rule, and it is not a signature of the dish or the X. The FlagShip is on that chart. Its re-shot keeps the drive pair, and the tower stays paint.
- Empty shields leave scars and a missing bubble. The class accent stays. A full red body fails. A full body painted `#9ad7ff` fails on the Star Master. A full body painted `#d0d6ff` fails on the Constellation.
- Fighter markers: `n < 1 → 0`, else `max(1, ceil(n / 100))`. Fill `#ff2a2a`, stroke `#ff8888`. One dart is 100 fighters. A bay of 1–99 is one marker, a partial hundred, and that dart gets no numeral. A bay of 100 is still one marker. The stat line keeps the exact bay. The legend is `each marker = 100 fighters`. The count is the onboard bay, not fighters per attack. Markers yaw with the hull. They are escorts, not corner ticks.
- The ring's innermost world radius is the bounding sphere of every face, including the kit named for that hull, plus a gap. On the canonical three-quarter pose and in the head-on clip, no marker's screen box intersects the hull silhouette.
- Canonical three-quarter is yaw `0.82`, pitch `0.5` (the held pose). Head-on is the warp clip camera `headon`. The side clip camera still has to show the same kit.
- The signature part has to read with the name plate covered, at about 140px tall and at a hero crop about 55% of the deck. A part that only exists in one of those views is not a signature.
- Kit names are the `PARTS` keys already in the bible (`mast` plus `dish`, and `quad`). Where the current `detail` string names a different part, that token is called out on the hull. Do not grow a second signature.
- Section tokens stay the ones the loft already uses: `round` on the Star Master, the Constellation, and the FlagShip. This wave adds no fourth section. `SHIPS` sets `kind` to `"arrow"` on the Star Master and `"delta"` on the Constellation. Those tokens are the flat panel outline. They do not change the loft section. A hex wedge is the BattleShip.
- The picture follows the job, not the hold grant. Where the live roster changes the grant, the entry says so. Fighter caps do not move on these hulls. Shields, photons, and mines stay on the base spec.

## Why these hulls

The gun wave locks the missiles, the turrets, and the prongs. Fleet order's next batch is the dish, the X, and the other capital. Two of the three still need a mesh contract. The third, the Corporate FlagShip, is the tower the four-hull wave already specified, and this wave re-shots it.

Trading index is the published formula `(hold ceiling / turns per warp) × 10`, rounded to the nearest integer. `OldBBS_TW2002V8.faq.txt` prints the same figures. It is a role number, not a picture. The FAQ prints TI 283 on the Corporate Flagship, TI 267 on the Constellation, TI 250 on the Merchant Cruiser, TI 243 on the Starmaster, and TI 200 on the Battleship. The Merchant sits between the dish and the X on that list. The picture follows the plate, the nacelles, and the tower.

| Hull | Key | Turns per warp | Hold ceiling | Index | This wave |
| --- | --- | --- | --- | --- | --- |
| Corporate FlagShip | `corporate_flagship` | 3 | 85 | 283 | re-shot, contract already landed |
| Constellation | `constellation` | 3 | 80 | 267 | new mesh |
| Merchant Cruiser | `merchant_cruiser` | 3 | 75 | 250 | P1 spike |
| Star Master | `star_master` | 3 | 73 | 243 | new mesh |
| BattleShip | `battleship` | 4 | 80 | 200 | batch 3, already contracted |

The Interdictor Cruiser is the hoop barge (ceiling 40, 15 turns per warp, index 27) and stays in fleet-order batch 5, with the Tholian Sentinel. Escape Pod and T'Khasi Orion are still uncontracted, and fleet order places them in batch 1 beside the Scout. This sheet does not go back for them. The plate has to be a circle on a stick before a hoop exists. That does not pull the Interdictor into this cut.

| Order | Key | Panel name | Why it is in this wave |
| --- | --- | --- | --- |
| 1 | `star_master` | Star Master | Mid combat hull. 61,300 credits, 3 turns per warp, ceiling 73, 5,000 fighters, 2,000 shields, odds 1.4, index 243. The dish, wider than the beam. Holo scanner allowed. The plate is the hull. It is on the ship when no scanner is fitted. |
| 2 | `constellation` | Constellation | Mid combat hull. 72,500 credits, 3 turns per warp, ceiling 80, 5,000 fighters, 750 shields, odds 1.4, index 267. Four nacelles in an X. `SCANNER_BY_HULL` is density for this key. No dish grows to explain that. |

`SHIP_SPECS_TW2002` `display_name` is `Star Master` and `Constellation`. The panel spells them the same way. The chart spells the second hull Constilation. The FAQ spells the first Starmaster. The mesh keeps the panel spelling. Do not rename either hull.

The FAQ's note on the Starmaster is that it was an excellent ship on v1.03 and that in V2 it is not good enough at anything. The FAQ's note on the Constellation is that it is a questionable day-to-day trader, that it does not fare well next to the Battleship, and that it has no holoscanner. `Slice-10_Slice_War_Manual.txt` says the Star Master has the scanners the Constellation lacks, and that it gives away holds and transporter range. None of those notes adds a part. The dish is the plate. The X is the four nacelles. The Battleship comparison does not grow a turret pair. The scanner note does not move the plate onto the Constellation.

## Star Master — `star_master`

### Role read

Cover the name plate. At 140px and at the hero crop the ship reads as a mid combat hull whose whole job is a dish: a modest arrow, a mast, one plate wider than the beam. A reader calls it a ship with a dish. The plate is the signature from the three-quarter pose, from head-on, from the top, and from the side clip. The top view is a circle on a stick. Fifty markers are a real escort, and they do not replace the plate. This is the hull the FlagShip's tower and the Imperial's castle must stay distinct from.

### Numbers

Base row, then the live roster where a field moves. Turns per warp are 3 on both. Odds are 1.4 on both. Shields stay 2,000. Mines 50, genesis 5, photons 0. Fighters per attack stay 1,000, and that figure is not the marker count. A full bay is 5,000 fighters, which is 50 markers. Two engines. `SCANNER_BY_HULL["star_master"]` is `holo`. Not on `SHIP_TW_CHART_RANGE`. Transporter range on `SHIP_TRANSPORT_RANGE` is 3. Range does not add a door, and it does not add a second plate.

| | Cost | Grant holds | Hold ceiling | Fighters | Markers at cap |
| --- | --- | --- | --- | --- | --- |
| Base `SHIP_SPECS_TW2002` | 61,300 | 30 | 73 | 5,000 | 50 |
| Live `SHIP_ROSTER_LIVE_TABLE` | 61,300 | 20 | 73 | 5,000 | 50 |

The live grant is 20 holds against a base grant of 30 and a ceiling of 73. The picture does not shrink to match the live grant and does not swell to the ceiling. The fighter cap does not move, so the escort count at the cap is 50 on both rosters. `SHIP_ROSTER.md` records a price SOURCE-CONFLICT with the Bible narrative and OldBBS, both 48,000. The included 30 is the OldBBS basic hold. The yard figure in `SHIP_SPECS_TW2002` and `SHIP_ROSTER_LIVE_TABLE` is 61,300. `OldBBS_TW2002V8.faq.txt` prints 61,500 under the TI 243 heading. The price does not change the dish.

The shield cap of 2,000 matches the Imperial StarShip. That shared number does not grow a castle. Fifty mines and five genesis do not add a launcher or a torpedo door. Photons stay 0. Odds of 1.4 do not add a turret.

### Silhouette

Section `round`. A modest arrow. A mast stands on the mid-body, and one dish sits on that mast. The dish is a plate, wider than the fuselage beam, so the top view is a circle on a stick. That circle is a plate. It is not a hoop around the body. The plate is the whole job. It reads at 140px from the side, from above, and in the three-quarter pose.

The plate is the hull. It is on the ship when no scanner is fitted. A fitted holo scanner does not add a second plate, a numeral, or a second mast. The scanner path that draws a small plate on other hulls already skips `star_master`. Keep that skip.

Two engines sit low in the tail, inside the beam, under the dish line. They do not stick up past the plate and they do not stick out past the fuselage.

Kit: `mast` and `dish`. `SHIPS` sets `detail` to `"dish bridge"`. The `dish` token is this kit. It is not a second plate beside the `PARTS` dish. The `bridge` token is the shared canopy, and it stays shorter than the mast. Do not grow a second signature beside the plate.

Today's `PARTS` mast is a box 1.6 long, 16 tall, and 1.6 thick, centered at mid x-2 and mid sy+10. The plate on that mast is lofted with sz 11 and sz 8 at mid sy+18. The Star Master mid station is `[14, 10, 14]`, so the hull's mid sz is 14 and the plate's wider sz is 11. The plate sits inside the beam. The `dish` detail draws a second plate at mid sy+8, lofted with sz 12 and sz 9, still inside that beam. The mesh pass replaces both with one plate on one mast, and that plate is wider than the beam. A plate whose wider sz sits inside the mid station sz fails, because the circle has collapsed into the arrow.

Distinct from the Corporate FlagShip: the FlagShip wears a stepped command block, a rectangle on the centerline, taller than the hull is deep. This signature is a plate on a stick. The FlagShip is re-shot from the four-hull wave. Do not recut it to help this comparison. Distinct from the Imperial StarShip: the Imperial is a long castle, longer than it is tall, with four bells in a square. This hull has no keep and no square. Distinct from the Interdictor Cruiser: the Interdictor's hoops wrap a heavy body and are the first shape in every camera. This circle does not wrap the body. The Interdictor is batch 5. Do not borrow its washer. Distinct from the Havoc GunStar: the Havoc's guns are two prongs ahead of a short nose. This nose is one nose, and the signature is dorsal. Distinct from the Constellation: the Constellation's tell is an X of four nacelles at the tail. This tail is two engines under a plate. Distinct from the Scout Marauder: the Scout is the long needle with canards. This arrow is the modest one, and the blades are not the job.

The outline carries no hoop, no tower, no castle, no X of nacelles, no prongs, no turret pair, no canards, and no keel as deep as the Merchant's. A holo scanner does not grow a second mast.

### Accent

`#9ad7ff` on the plate and the stripe. The mast and the fuselage stay dark metal, so the signature reads as a plate on a stick. At shields 0 the plate and the stripe are still `#9ad7ff`, and the mast is still dark. Engine cones stay cyan-white unless a drive is fitted, and then only the cones change. Magenta on a tower is the FlagShip. Gold is the Imperial. Neither colour appears on this plate.

### Three-quarter checklist

Pose: yaw `0.82`, pitch `0.5`. Name plate covered. Repeat at shields 0 and at shields full, at about 140px and at the hero crop. Repeat once in a frame that also shows the merged FlagShip, and once in a frame that also shows the merged Imperial.

1. One plate breaks the top edge and is wider than the beam. The top view is one circle on one stick.
2. The circle is a plate. A hoop around the body fails, because that is the Interdictor. A stepped block fails, because that is the FlagShip. A long castle fails, because that is the Imperial.
3. The body is a modest arrow. Canards fail, because that is the Scout. A split prow fails, because that is the Havoc. An X of nacelles fails, because that is the Constellation.
4. Beside the FlagShip, the tower stays a block and this plate stays a dish. Beside the Imperial, the castle stays long and the bells stay a square.
5. The plate and the stripe are `#9ad7ff` at shields 0. The mast stays dark metal.
6. Every marker sits outside the plate. No marker rings the mast. No marker screen-box intersects the silhouette.

### Head-on checklist

Clip camera `headon`. Same shield pair, same two sizes.

1. One plate on a stick is the high point, and the plate is wider than the beam.
2. The plate is one plate. A second plate fails. A rectangle the height of a tower fails, because that is the FlagShip.
3. Two engine mouths sit low, inside the beam, under the dish.
4. The frame shows no hoop, no X of nacelles, no square of four bells, no prongs, and no castle.
5. Markers clear the plate. No marker screen-box intersects the silhouette.

### Marker clearance

| Bay | Markers |
| --- | --- |
| 0 | 0 |
| 1–99 | 1 |
| 100 | 1 |
| 101–200 | 2 |
| 4,900 | 49 |
| 4,901–4,999 | 50 |
| 5,000 (cap, both rosters) | 50 |

A bay of 1–99 is one marker, a partial hundred, with no numeral. From 4,901 through 4,999 the count is already 50 and the last dart is a partial hundred, so it gets no numeral. The cap is an exact five thousand. The fiftieth dart is a full hundred and still carries no numeral. Fighters per attack of 1,000 would draw 10 darts. The checklist uses the bay.

The sphere includes the loft, the mast, the one plate, the canopy, and both engines. The plate sets the top of the sphere. A ring sized to the fuselage clips the dish from the side and fails. Markers orbit outside the plate. They do not ring the mast as if the dish were the Interdictor's hoop. Fifty markers is the same count the Frigate contract already requires, on this hull's sphere, between the 25 the Merchant spike records and the 500 the Imperial spike records. Do not borrow the FlagShip radius. Do not cap the formula. The grouping fix in the render memo is the remedy, if one is needed.

## Constellation — `constellation`

### Role read

Cover the name plate. The ship reads as a mid combat hull with four nacelles in an X: a slim body, the X in every camera that can see the tail, four engines, fifty escorts at a full bay. A reader calls it a ship with an X. The X is the signature from the three-quarter pose, from head-on, and from the side clip. Fifty markers do not fill the crook. This is the hull the Imperial's square of bells must stay distinct from, and the hull that must not grow the Star Master's dish.

### Numbers

Base row and the live roster match on every field this picture uses. Turns per warp are 3. Odds are 1.4. Shields stay 750. Mines 25, genesis 2, photons 0. Fighters per attack stay 2,000, and that figure is not the marker count. A full bay is 5,000 fighters, which is 50 markers. Four engines. `SCANNER_BY_HULL["constellation"]` is `density`. Not on `SHIP_TW_CHART_RANGE`. Transporter range on `SHIP_TRANSPORT_RANGE` is 6. Range does not add a dish or a door.

| | Cost | Grant holds | Hold ceiling | Fighters | Markers at cap |
| --- | --- | --- | --- | --- | --- |
| Base `SHIP_SPECS_TW2002` | 72,500 | 20 | 80 | 5,000 | 50 |
| Live `SHIP_ROSTER_LIVE_TABLE` | 72,500 | 20 | 80 | 5,000 | 50 |

The grant is 20 holds against a ceiling of 80. The bible's line is the same pair: 20 holds, yard cap 80. The body does not shrink to the grant and does not swell to the ceiling. The fighter cap does not move, so the escort count at the cap is 50 on both rosters. `SHIP_ROSTER.md` records a price SOURCE-CONFLICT with the narrative and OldBBS 40,500. The included 20 is the OldBBS basic hold. The yard figure in `SHIP_SPECS_TW2002` is 72,500. The FAQ prints the same 72,500 under the TI 267 heading. The price does not change the X. The chart spelling Constilation does not rename the hull.

The shield cap of 750 matches the BattleShip. That shared number does not grow a turret pair. Twenty-five mines and two genesis do not add a launcher or a torpedo door. Photons stay 0, so the outline has no dorsal missile pair. Odds of 1.4 do not add a gun fairing. A density scanner does not grow the Star Master's mast.

### Silhouette

Section `round`. A slim body. Four nacelles sit in an X and trail past the tail. They are the silhouette from the side, the top, and head-on. Head-on is that X and little else. The gap between the arms is empty.

Four engine mouths sit off the centerline. The quad is the larger cross, and the sphere uses that cross. The mouths are not a square of bells. A row of mouths with no X behind it fails, because the nacelles are the tell.

Kit: `quad`. `SHIPS` sets `detail` to `"nacelles bridge"`. The `nacelles` token is the path that grows the Imperial's four bells, and that path already stays off when `PARTS` is `quad`. The quad wins. Do not also grow that bell path. The `bridge` token is the shared canopy, and it stays inside the slim body, shorter than the arms. A density scanner does not grow a plate. The scanner path that draws a dish when `ship.scanner` is set stays off this key. Do not grow a second signature beside the X.

Today's quad runs from mid x-4 through tail x-16, at ±(mid sy+8) and ±(mid sz+8). On this loft the mid station is `[10, 11, 17]` and the tail station is `[-60, 6, 10]`, so the arms sit at y ±19 and z ±25, and the tips sit at x=-76. Keep the tips past the tail station, and keep the arms outside the mid sz of 17 and the mid sy of 11. A tip that ends on the tail station fails, because the X has collapsed into the fuselage. The sphere uses those tips.

Distinct from the Imperial StarShip: the Imperial's four bells make a square, and a castle runs the spine. This head-on view is an X, and the spine stays bare. The Imperial is re-shot beside the FlagShip. Do not recut its bells to help this comparison. Distinct from the Star Master: the Star Master's circle is a plate on a mast, wider than the beam, dorsal. This hull has no mast. Distinct from the BattleShip: the BattleShip is a wide hex wedge with a turret pair. This body is slim, the section stays `round`, and the tell is the X at the tail. The FAQ's comparison does not move the turrets. Distinct from the Havoc GunStar: the Havoc's guns run ahead of the nose as two prongs with a gap. This nose is one nose, and the X is aft. Distinct from the Corporate FlagShip: the FlagShip's head-on tell is a rectangle on the centerline and three bells in a low row. This head-on tell is an X. Distinct from the Interdictor: two hoops around a body are a later wave. An X is not a ring.

The outline carries no dish, no hoop, no castle, no tower, no prongs, no turret pair, and no dorsal missile pair.

### Accent

`#d0d6ff` on the nacelles and the stripe. The fuselage stays dark metal, so head-on reads as an X, not as a pale wedge. At shields 0 the nacelles and the stripe are still `#d0d6ff`. Engine cones stay cyan-white unless a drive is fitted, and then only the cones change. Gold is the Imperial's accent. Magenta on a tower is the FlagShip. The Star Master's `#9ad7ff` stays on its plate. None of those colours appears on these arms.

### Three-quarter checklist

Same pose, sizes, and shield pair as the Star Master. Repeat once in a frame that also shows the merged Imperial, and once in a frame that also shows the Star Master.

1. Four nacelles in an X break the outline and trail past the tail.
2. The body is slim. A wide hex wedge with a turret pair fails, because that is the BattleShip. A dish on a mast fails, because that is the Star Master. A castle with a square of bells fails, because that is the Imperial.
3. Beside the Imperial, these arms stay an X. The bells stay a square on the Imperial.
4. The nacelles and the stripe are `#d0d6ff` at shields 0. The fuselage stays dark metal.
5. A fitted density scanner does not grow a plate. The frame shows no dish, no prongs, and no tower.
6. Markers sit outside the nacelle tips. No marker sits in the crook of the X. No marker screen-box intersects the silhouette.

### Head-on checklist

Same shield pair, same two sizes.

1. An X and little else. The four arms are `#d0d6ff`.
2. The arms are nacelles. A square of four bells fails, because that is the Imperial. Two prongs with a gap fail, because that is the Havoc. A plate on a stick fails, because that is the Star Master.
3. Four engine mouths sit off the centerline. The X is the larger cross around them. A row of mouths with no X fails.
4. The frame shows no castle, no tower rectangle, no hoop, and no dish.
5. Markers clear the arm tips. No marker screen-box intersects the silhouette.

### Marker clearance

| Bay | Markers |
| --- | --- |
| 0 | 0 |
| 1–99 | 1 |
| 100 | 1 |
| 101–200 | 2 |
| 4,900 | 49 |
| 4,901–4,999 | 50 |
| 5,000 (cap, both rosters) | 50 |

A bay of 1–99 is one marker, a partial hundred, with no numeral. From 4,901 through 4,999 the count is already 50 and the last dart is a partial hundred, so it gets no numeral. The cap is an exact five thousand. The fiftieth dart is a full hundred and still carries no numeral. Fighters per attack of 2,000 would draw 20 darts. The checklist uses the bay.

The sphere includes the loft, the four nacelles, the canopy, and the four engines. The nacelle tips set the tail and the beam of the sphere. A ring that clears the slim body and clips an arm fails. A marker in the crook reads as a fifth arm and fails. Fifty markers is the same count the Star Master contract requires, on this hull's cross. Do not borrow the Imperial radius. Do not cap the formula. The grouping fix in the render memo is the remedy, if one is needed.

## Corporate FlagShip — re-shot, not a new mesh

The mesh contract is [Corporate FlagShip](cockpit-ship-stage-p1b-next-hulls.md#corporate-flagship--corporate_flagship) in the four-hull wave. This wave does not recut it, does not invent a second step, and does not edit that sheet. The lines below are the re-shot, so the dish and the X have their capital on screen. Fleet order places this hull in batch 4 beside them. The tower already has a contract.

`SHIP_SPECS_TW2002["corporate_flagship"]["display_name"]` is `Corporate Flagship`. The panel and the bible spell the second word `FlagShip`. The mesh keeps the panel spelling. Do not rename the hull.

### Role read

Cover the name plate. The ship still reads as a corp liner: a hull with a stepped command block standing amidships, taller than the hull is deep, three engines in a low row, two hundred escorts at a full bay. The tower is the signature. The Star Master's dish and the Constellation's X are other hulls. The Imperial's castle is the other capital.

### Numbers

Turns per warp are 3. Odds are 1.2. Shields stay 1,500. Mines 100, genesis 10, photons 0. Three engines. `corp_only` is true. That is a yard gate, not a paint scheme. `SHIP_TW_CHART_RANGE` prints 28 hops. It is one of the three chart TransWarp hulls, with the Imperial StarShip (50) and the Havoc GunStar (16). The fighter cap does not move.

| | Cost | Grant holds | Hold ceiling | Fighters | Markers at cap |
| --- | --- | --- | --- | --- | --- |
| Base `SHIP_SPECS_TW2002` | 163,500 | 85 | 85 | 20,000 | 200 |
| Live `SHIP_ROSTER_LIVE_TABLE` | 163,500 | 20 | 85 | 20,000 | 200 |

The live grant is 20 holds against a ceiling of 85. The tower does not shrink. Photons stay 0. The re-shot still has no dish and no X.

### Silhouette

Section `round`. Kit: `tower`. Accent `#ff77ff` on the tower's upper step and the stripe. At shields 0 the upper step and the stripe are still `#ff77ff`. The tower is painted metal. It is not an emissive lamp. When `ship.transwarp.fitted` is set, the engine cones go magenta and the tower stays the flat accent. Idle cones, with no drive fitted, stay cyan-white. Three engines sit in a low horizontal row, inside the beam. They are not an X, and they are not a square of bells. The four-hull checklist is the pass list. This wave adds the pair shots below.

Fleet order records today's upper tower box near y=37, on a mid station whose sy is 16. The re-shot does not move that top.

### Three-quarter checklist

Same pose, sizes, and shield pair as the four-hull sheet. Name plate covered. Repeat at about 140px and at the hero crop, once beside the Star Master and once beside the Imperial. Repeat once with a fitted TransWarp drive and once without. Repeat once beside the Constellation.

1. The tower breaks the top edge and is taller than the hull is deep.
2. The step reads as a command block amidships. A dish on a mast fails, because that is the Star Master. A long castle fails, because that is the Imperial. An X at the tail fails, because that is the Constellation.
3. Beside the Star Master, the plate stays on the Star Master. This hull does not grow a dish.
4. Beside the Imperial, the castle stays long. This tower stays a block amidships.
5. With a drive fitted, the cones are magenta and the upper step is still flat `#ff77ff`.
6. With shields at 0, the upper step and the stripe are still `#ff77ff`. Markers sit outside the top of the tower. No marker screen-box intersects the silhouette.

### Head-on checklist

Same drive pair and shield pair.

1. A rectangle on the centerline, taller than the hull.
2. Three engine mouths sit in a low row, inside the beam. An X fails, because that is the Constellation. A square of four bells fails, because that is the Imperial.
3. The frame shows no dish, no hoop, and no plate wider than the beam.
4. Markers clear the top of the tower. No marker screen-box intersects the silhouette.

### Marker clearance

| Bay | Markers |
| --- | --- |
| 0 | 0 |
| 1–99 | 1 |
| 100 | 1 |
| 101–200 | 2 |
| 19,900 | 199 |
| 19,901–19,999 | 200 |
| 20,000 (cap, both rosters) | 200 |

A bay of 1–99 is one marker, a partial hundred, with no numeral. From 19,901 through 19,999 the count is already 200 and the last dart is a partial hundred, so it gets no numeral. The cap is an exact twenty thousand. The two-hundredth dart is a full hundred and still carries no numeral. The checklist uses the bay.

The sphere includes the loft, both tower steps, and the three engines. The upper step sets the top of the sphere. A ring that clears the liner and clips the tower fails. Two hundred markers is the count the four-hull contract already requires, inside the 500 the Imperial spike already drew. Do not cap the formula. The grouping fix in the render memo is the remedy, if one is needed.

## Wave read test

Cover the name plate. These pairs have to stay apart at 140px and at the hero crop, on the three-quarter pose and head-on. The bible's full-fleet table still applies. This is the subset this wave can get wrong while cutting the two new faces, with the FlagShip, the Imperial, the BattleShip, and the Havoc already on screen from earlier waves.

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

## Build order

Star Master, then Constellation. The dish goes first so the merged FlagShip tower and the merged Imperial castle have their pair on screen, and the plate is locked wider than the beam before the X is cut. The X is second, so it can be judged against that plate, against the Imperial's square of bells, and against the merged Havoc's prongs. Stop. Do not recut the FlagShip. Do not start the Tholian Sentinel or the Interdictor Cruiser.

Done when both new hulls pass their checklists, the FlagShip and Imperial re-shots pass, the wave read test passes, and the inherited P1 bar holds (legend, exact bay on the stat line, side clip, phone still, reduced-motion still, `body.cu-seat` still, mesh module still under 40 KB gzipped). Show the two the way the gun wave shows its set, shields empty and shields full. The new hulls' pass pose is idle cyan-white cones. Show the FlagShip once with a fitted TransWarp drive and once without. Marker clouds in this wave are 50 and 50, and the FlagShip's 200 is already on the merged hull. The clearance problem is the kit, not the count.

## Out of scope

The P1 spike hulls, except the Imperial re-shot named above. The four-hull wave (Scout Marauder, Merchant Freighter, BattleShip, Corporate FlagShip), except the FlagShip re-shot named above. The hauler wave (CargoTran, Colonial Transport, Taurean Mule). The gun wave (Missile Frigate, BattleShip, Havoc GunStar). Escape Pod and T'Khasi Orion. Tholian Sentinel and Interdictor Cruiser. Ferrengi hulls. Any edit under `web/`, any engine change, any test change, and any rewrite of `COMMANDER_NEXT.md`, `GAP_MAP.md`, `cockpit-ship-stage-INDEX.md`, `cockpit-ship-stage-marker-math.md`, `cockpit-ship-stage-p0.md`, `cockpit-ship-stage-p0-silhouette-bible.md`, `cockpit-ship-stage-p0-render.md`, `cockpit-ship-stage-p0-fx.md`, `cockpit-ship-stage-p1-acceptance.md`, `cockpit-ship-stage-p1b-next-hulls.md`, `cockpit-ship-stage-p1b-batch2-haulers.md`, `cockpit-ship-stage-p1b-batch3.md`, `cockpit-ship-stage-p1b-fleet-order.md`, `cockpit-ship-stage-p2-wire.md`, or `cockpit-ship-stage-p3-layout.md`. New events, new actions, and a layout split. Copying or tracing EIS, Markham, or ANSI ship art.
