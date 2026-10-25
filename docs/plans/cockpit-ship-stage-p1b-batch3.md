# Batch 3 guns — ship stage P1b

Parents: [P0 pack](cockpit-ship-stage-p0.md), [silhouette bible](cockpit-ship-stage-p0-silhouette-bible.md), [render decision](cockpit-ship-stage-p0-render.md), [four-hull wave](cockpit-ship-stage-p1b-next-hulls.md), [hauler wave](cockpit-ship-stage-p1b-batch2-haulers.md), [fleet order](cockpit-ship-stage-p1b-fleet-order.md).

Docs only. This sheet does not change `web/*`, the engine, or tests. Classic top-and-front ANSI for every hull stays **UNVERIFIED**. Do not open, trace, or approximate EIS prints, EIS wallpaper, or Drew Markham ANSI. Looks below are invented from the public role numbers on `SHIP_SPECS_TW2002` and `SHIP_ROSTER_LIVE_TABLE` in `src/tw2k/engine/constants.py`, and from the one-paragraph pictures already in the bible. This sheet is the mesh contract for the gun wave after the three in [cockpit-ship-stage-p1b-batch2-haulers.md](cockpit-ship-stage-p1b-batch2-haulers.md), so a follow-on does not turn the dorsal missiles into the Imperial's cheek barrels or the CargoTran's girder, and does not turn the split prow into the BattleShip's turret pair.

## Implement after the spike, the four, and the three haulers

Do not start these meshes until all three of these have landed:

1. The Merchant Cruiser and Imperial StarShip spike has merged and passed the render memo's pass list (read test, accent at zero shields, 100:1 markers, clip cameras, size).
2. The four-hull wave has merged and passed the same bar: Scout Marauder, Merchant Freighter, BattleShip, Corporate FlagShip.
3. The hauler wave has merged and passed the same bar: CargoTran, Colonial Transport, Taurean Mule.

Fleet order names this cut as its batch 3: Missile Frigate, BattleShip, Havoc GunStar. The BattleShip mesh contract already landed in the four-hull wave. This sheet does not rewrite it and does not recut that wedge. The new meshes are the two hulls in that batch that have no contract yet. The gate is the stricter one. The Imperial's forward barrels have to be on screen before the Frigate's missiles are cut, and the BattleShip's turrets have to be on screen before the Havoc's prongs are cut. The hauler kits have to be on screen so the Frigate's rail stays a track under two missiles, and the Havoc's short body stays a split prow.

Build the two hulls below on the same `buildHullFaces` / `projectFace` path, in the order at the bottom, and stop there. Every other player hull stays on `fleet-glass-v1` until these two pass the same bar, judged with the merged BattleShip and the merged Imperial. If the spike misses the bar and opens the WebGL off-ramp, these silhouettes still apply. The renderer does not get to redesign them.

Shared rules, inherited from the four-hull sheet and the hauler sheet:

- Dark blue-grey metal. The accent is a stripe, a canopy edge, and the kit. Canopy glass is a cool white mixed with the accent. Idle engines are a short cyan-white cone. A fitted TransWarp drive (`ship.transwarp.fitted`) turns that cone magenta and nothing else. The Frigate is not on `SHIP_TW_CHART_RANGE`. Its pass pose is idle cyan-white cones. A drive recolor is the inherited rule, and it is not a signature of the Frigate. The Havoc is on that chart. Its pass pose includes the drive pair, and the prongs stay paint.
- Empty shields leave scars and a missing bubble. The class accent stays. A full red body fails. A full amber body on the Frigate fails. A full orange body on the Havoc fails.
- Fighter markers: `n < 1 → 0`, else `max(1, ceil(n / 100))`. Fill `#ff2a2a`, stroke `#ff8888`. One dart is 100 fighters. A bay of 1–99 is one marker, a partial hundred, and that dart gets no numeral. A bay of 100 is still one marker. The stat line keeps the exact bay. The legend is `each marker = 100 fighters`. The count is the onboard bay, not fighters per attack. Markers yaw with the hull. They are escorts, not corner ticks.
- The ring's innermost world radius is the bounding sphere of every face, including the kit named for that hull, plus a gap. On the canonical three-quarter pose and in the head-on clip, no marker's screen box intersects the hull silhouette.
- Canonical three-quarter is yaw `0.82`, pitch `0.5` (the held pose). Head-on is the warp clip camera `headon`. The side clip camera still has to show the same kit.
- The signature part has to read with the name plate covered, at about 140px tall and at a hero crop about 55% of the deck. A part that only exists in one of those views is not a signature.
- Kit names are the `PARTS` keys already in the bible (`missiles` plus `rails`, and `prongs`). Where the current `detail` string names a different part, that token is called out on the hull. Do not grow a second signature.
- Section tokens stay the ones the loft already uses: `round` on the Frigate, `hex` on the Havoc and the BattleShip. This wave adds no fourth section.
- The picture follows the job, not the hold grant. Where the live roster changes the grant, the entry says so. Fighter caps do not move on these hulls. Shields, photons, and mines stay on the base spec.

## Why these hulls

The hauler wave locks the spine, the cabin, and the saddle. Fleet order's next batch is the guns. Two of the three still need a mesh contract. The third, the BattleShip, is the gun platform the four-hull wave already specified, and this wave re-shots it.

Trading index is the published formula `(hold ceiling / turns per warp) × 10`, rounded to the nearest integer. `OldBBS_TW2002V8.faq.txt` prints the same figures. It is a role number, not a picture. The FAQ prints TI 200 on the Battleship and, under that same heading, the Missile Frigate. It prints TI 167 on the Havoc Gunstar. The picture follows the photons, the turret pair, and the split prow.

| Hull | Key | Turns per warp | Hold ceiling | Index | This wave |
| --- | --- | --- | --- | --- | --- |
| Missile Frigate | `missile_frigate` | 3 | 60 | 200 | new mesh |
| BattleShip | `battleship` | 4 | 80 | 200 | re-shot, contract already landed |
| Havoc GunStar | `havoc_gunstar` | 3 | 50 | 167 | new mesh |
| Star Master | `star_master` | 3 | 73 | 243 | fleet-order batch 4 |
| Constellation | `constellation` | 3 | 80 | 267 | fleet-order batch 4 |

Star Master (243) and Constellation (267) score above this wave and stay in fleet-order batch 4, with the Corporate FlagShip, so the dish, the X, and the tower are judged together. The tower already has a contract. That does not pull the dish or the X into this cut. Escape Pod and T'Khasi Orion are still uncontracted, and fleet order places them in batch 1 beside the Scout. This sheet does not go back for them.

| Order | Key | Panel name | Why it is in this wave |
| --- | --- | --- | --- |
| 1 | `missile_frigate` | Missile Frigate | Photon boat. 100,800 credits, 3 turns per warp, ceiling 60, 5,000 fighters, odds 1.3, 10 photons, index 200. Two dorsal missiles larger than the canopy, and larger than the Imperial's forward barrels. `SCANNER_BY_HULL` is `None` for this key. No dish grows to explain that. |
| 2 | `havoc_gunstar` | Havoc GunStar | Shield tank and gunship. 79,000 credits, 3 turns per warp, ceiling 50, 10,000 fighters, 3,000 shields, odds 1.2, index 167. The split prow. `SHIP_TW_CHART_RANGE` prints 16 hops. It is the third chart TransWarp hull, with the Imperial StarShip (50) and the Corporate FlagShip (28). |

`SHIP_SPECS_TW2002["havoc_gunstar"]["display_name"]` is `Havoc Gunstar`. The panel and the bible spell it `Havoc GunStar`. The mesh keeps the panel spelling. Do not rename the hull.

There is no Destroyer class. BattleShip remains the gun platform, already contracted. The FAQ's note on the Frigate is that the attraction is photons, and that the hull itself launches no genesis. The FAQ's note on the Havoc is that it is the TransWarp hull a trader can buy without a commission and without a corporation, and that 50 holds make it a poor trader. Neither note adds a part. Photons are the dorsal pair. The shield tank is the role, and the silhouette is the prongs.

## Missile Frigate — `missile_frigate`

### Role read

Cover the name plate. At 140px and at the hero crop the ship reads as a photon boat: a long slim hull with two dorsal missiles and a rail, noses forward, proud of the fuselage, larger than the canopy. A reader calls it a missile ship. The missiles are the signature from the three-quarter pose, from head-on, and from the side clip. Fifty markers are a real escort, and they do not replace the pair. This is the hull the Imperial's forward barrels must stay smaller than.

### Numbers

Base row, then the live roster where a field moves. Turns per warp are 3 on both. Odds are 1.3 on both. Shields stay 400. Mines 5, genesis 0, photons 10. Fighters per attack stay 3,000, and that figure is not the marker count. A full bay is 5,000 fighters, which is 50 markers. Two engines. `SCANNER_BY_HULL["missile_frigate"]` is `None`. Not on `SHIP_TW_CHART_RANGE`. Transporter range on `SHIP_TRANSPORT_RANGE` is 2. Range does not add a dish or a door.

| | Cost | Grant holds | Hold ceiling | Fighters | Markers at cap |
| --- | --- | --- | --- | --- | --- |
| Base `SHIP_SPECS_TW2002` | 100,800 | 40 | 60 | 5,000 | 50 |
| Live `SHIP_ROSTER_LIVE_TABLE` | 100,800 | 12 | 60 | 5,000 | 50 |

The live grant is 12 holds against a ceiling of 60. The picture does not shrink to match that grant. The fighter cap does not move, so the escort count at the cap is 50 on both rosters. `SHIP_ROSTER.md` records a price SOURCE-CONFLICT with OldBBS 28,800. The yard figure in `SHIP_SPECS_TW2002` is 100,800. The price does not change the missiles.

### Silhouette

Section `round`. A long slim body, ordinary in plan, slimmer than the BattleShip and shorter than the Imperial. Two long dorsal missiles sit on a rail, noses forward, clearly proud of the fuselage. Each missile body is larger than the canopy. The pair reads at 140px from the side, from above, and in the three-quarter pose. The rail is a thin track under the pair. It is how the missiles sit. It is not a cargo ridge.

The missiles are the hull. They are on the ship when `photon_missiles` is 0. A loaded count of 10 does not add a third body, a row of ten bodies, or a numeral on the pair. Genesis stays 0. The FAQ's line that this hull launches no genesis means no torpedo door. Five mines do not add a launcher.

Two engines sit low in the tail, inside the beam, under the missile line. They do not stick up past the missiles and they do not stick out past the fuselage.

Kit: `missiles`, plus `rails`. `SHIPS` sets `detail` to `"rails bridge"`. The rail belongs to this kit. The `bridge` token is the shared canopy, and it stays shorter than the missiles. Do not grow a second signature beside the pair.

Today's `PARTS` missile is a box 36 long and 2.4 thick on the mid station, plus a nose cap 5 long, so the noses stay near mid-body while the loft nose is at x=86. That pair loses to the canopy. The mesh pass replaces it. The bodies stand proud, noses forward, and they read larger than the canopy at both sizes.

Distinct from the Imperial StarShip: the Imperial wears a long castle, four bells in a square, and two forward barrels on the cheeks. Those barrels stay smaller than these missile bodies. Re-shot the Imperial beside this hull. Distinct from the BattleShip: the BattleShip's barrels are thinner, they sit on turret bodies, and the hull under them is a wide hex wedge. This pair sits on a rail along a slim spine. Distinct from the Havoc GunStar: the Havoc's guns run ahead of the nose as two prongs with a gap. This nose is one nose. Distinct from the CargoTran: the CargoTran's tell is a girder the length of a flat deck. A reader who names a cargo girder has a CargoTran, and the missiles failed. Distinct from the Scout Marauder: the Scout is a needle with canards and no dorsal weapon. Distinct from the Merchant Freighter: the Freighter is short, and its cheeks set a broad face. This hull is slim, and the cargo is not the face.

The outline carries no split prow, no turret pair, no castle, no tower, no cheek tanks, no canards, no dish, and no keel as deep as the Merchant's. Odds of 1.3 do not add a second gun fairing.

### Accent

`#ffb15a` on the missile bodies, the rail edge, and the stripe. The missile noses are a hotter amber than `#ffb15a`. The fuselage stays dark metal, so the pair reads as two bodies and the rail stays a track. At shields 0 the bodies, the rail edge, and the stripe are still `#ffb15a`, and the noses are still the hotter amber. Engine cones stay cyan-white unless a drive is fitted, and then only the cones change.

### Three-quarter checklist

Pose: yaw `0.82`, pitch `0.5`. Name plate covered. Repeat at shields 0 and at shields full, at about 140px and at the hero crop. Repeat once in a frame that also shows the merged Imperial.

1. Two dorsal missiles break the top edge, noses forward, each body larger than the canopy.
2. A rail shows under the pair, and it reads as a track. A cargo girder the length of a flat deck fails, because that is the CargoTran.
3. The body is long and slim. A wide hex wedge fails, because that is the BattleShip. A split prow fails, because that is the Havoc. Canards fail, because that is the Scout. A broad cheek face fails, because that is the Freighter.
4. Beside the Imperial, these bodies are larger than its forward barrels. The Imperial still has its castle and its square of bells.
5. The missile bodies, the rail edge, and the stripe are `#ffb15a` at shields 0. The noses are a hotter amber.
6. Every marker sits outside the missiles. No marker screen-box intersects the silhouette.

### Head-on checklist

Clip camera `headon`. Same shield pair, same two sizes.

1. Two missile bodies sit above a slim fuselage. They are the high points, and they are larger than the canopy.
2. The nose is one nose. Two prongs with a gap fail, because that is the Havoc.
3. Two engine mouths sit low, inside the beam, under the missile line.
4. The frame shows no turret pair, no castle, no tower, no cheek tanks, no canards, and no square of four bells.
5. Markers clear the missiles. No marker screen-box intersects the silhouette.

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

A bay of 1–99 is one marker, a partial hundred, with no numeral. From 4,901 through 4,999 the count is already 50 and the last dart is a partial hundred, so it gets no numeral. The cap is an exact five thousand. The fiftieth dart is a full hundred and still carries no numeral. Fighters per attack of 3,000 would draw 30 darts. The checklist uses the bay.

The sphere includes the loft, both missiles, the rail, the canopy, and both engines. The missiles set the top of the sphere. A ring sized to the fuselage clips them from the side and fails. Fifty markers sit between the 25 the Merchant spike records and the 500 the Imperial spike records. A late frame does not change the count formula. The grouping fix in the render memo is the remedy, if one is needed.

## Havoc GunStar — `havoc_gunstar`

### Role read

Cover the name plate. The ship reads as a shield tank and a gunship: a short body, a split prow, two prongs ahead of the nose, three engines, and a hundred escorts at a full bay. A reader calls it a warship with a forked nose. The prongs are the signature from the three-quarter pose, from head-on, and from the side clip. Head-on they are two bright tips with a gap. A hundred markers do not replace the gap. This is the hull the BattleShip's turrets must stay distinct from.

### Numbers

Base row, then the live roster where a field moves. Turns per warp are 3 on both. Odds are 1.2 on both. Shields stay 3,000. Mines 5, genesis 1, photons 0. Fighters per attack stay 1,000, and that figure is not the marker count. A full bay is 10,000 fighters, which is 100 markers. Three engines. Holo scanner allowed. `SHIP_TW_CHART_RANGE` prints 16 hops. Transporter range on `SHIP_TRANSPORT_RANGE` is 6. Range does not add a dish or a door.

| | Cost | Grant holds | Hold ceiling | Fighters | Markers at cap |
| --- | --- | --- | --- | --- | --- |
| Base `SHIP_SPECS_TW2002` | 79,000 | 50 | 50 | 10,000 | 100 |
| Live `SHIP_ROSTER_LIVE_TABLE` | 79,000 | 12 | 50 | 10,000 | 100 |

The live grant is 12 holds against a ceiling of 50. The picture does not shrink to match that grant. The fighter cap does not move, so the escort count at the cap is 100 on both rosters. The yard cost stays 79,000.

### Silhouette

Section `hex`. A short body. Two prongs run ahead of the loft nose and are the silhouette from the side, the top, and head-on. Head-on is two bright tips with a gap between them. The gap is empty. The prongs are the guns. There is no turret pair, so a reader does not call it the BattleShip.

Three engines sit in a low horizontal row in the tail, inside the hex width, behind the prong line. They do not grow past the prong tips. They are not an X, and they are not a square of bells.

Kit: `prongs`. `SHIPS` sets `detail` to `"guns bridge"`. The `guns` token is sausage vocabulary on this hull. It is the path that grows the Imperial's forward barrels. The prongs win. Do not also grow that barrel path. The `bridge` token is the shared canopy, and it stays shorter than the prongs. A holo scanner does not grow the Star Master's mast. One genesis does not add a door. Five mines do not add a launcher. Odds of 1.2 do not add a turret.

Today's prong tip station is at nose x+26, past the loft nose. Keep the tips past the loft nose. The sphere uses those tips. A tip that ends on the loft nose fails, because the split prow has collapsed into a single nose.

Distinct from the BattleShip: the BattleShip is a wide hex wedge, short for its beam, with two turrets whose barrels break the top edge. This hull's guns are forward, and nothing on the back is a turret pair. The BattleShip is re-shot from the four-hull wave. Do not recut it to help this comparison. Distinct from the Missile Frigate: the Frigate's guns are two dorsal missiles on a rail, larger than the canopy, on one nose. This head-on view is a gap. Distinct from the Imperial StarShip: the Imperial is the long castle with four bells and small forward barrels. These prongs are the whole silhouette, and they run ahead of a short body. Distinct from the Merchant Freighter: the Freighter is short and very wide, and its cheeks are a cargo face. This hull is short, and the width that matters is the gap between two prongs. Distinct from the Corporate FlagShip: the FlagShip's head-on tell is a rectangle on the centerline. This head-on tell is a gap. Distinct from the Scout: the Scout is the long needle with canards. This body is the short one.

The outline carries no dorsal missile pair, no turret pair, no castle, no tower, no dish, no cheek plate, no X of nacelles, and no hoop. The shield tank is the 3,000 shield cap. It does not paint the body orange, and it does not grow a second bubble colour.

### Accent

`#ff8844` on the prong tips and the stripe. The prong shafts and the hull stay dark metal, so head-on reads as two bright tips with a gap, not as an orange wedge. At shields 0 the tips and the stripe are still `#ff8844`. When `ship.transwarp.fitted` is set, the engine cones go magenta and the tips stay the flat accent. Idle cones, with no drive fitted, stay cyan-white. Gold is the Imperial's accent. Magenta on a tower is the FlagShip. Neither colour appears on these prongs.

### Three-quarter checklist

Same pose, sizes, and shield pair as the Frigate. Repeat once with a fitted TransWarp drive and once without. Repeat once in a frame that also shows the merged BattleShip.

1. Two prongs run ahead of the nose and break the outline from the side and from above.
2. The body is short. A wide wedge with a turret pair on the back fails, because that is the BattleShip. Two dorsal missiles larger than the canopy fail, because that is the Frigate.
3. Beside the BattleShip, the turrets stay on the BattleShip and the prongs stay on this hull.
4. With a drive fitted, the cones are magenta and the prong tips are still flat `#ff8844`.
5. With shields at 0, the prong tips and the stripe are still `#ff8844`.
6. Markers sit outside the prong tips. No marker sits in the gap. No marker screen-box intersects the silhouette.

### Head-on checklist

Same drive pair and shield pair.

1. Two bright tips with a gap between them. The tips are `#ff8844`.
2. The gap is empty. A third prong, a turret barrel, or a marker in the gap fails.
3. Three engine mouths sit in a low row, inside the hex, behind the prongs.
4. The frame shows no dorsal missile pair, no tall centerline rectangle, no square of four bells, no broad cheek face, and no dish.
5. Markers clear the prong tips. No marker screen-box intersects the silhouette.

### Marker clearance

| Bay | Markers |
| --- | --- |
| 0 | 0 |
| 1–99 | 1 |
| 100 | 1 |
| 101–200 | 2 |
| 9,900 | 99 |
| 9,901–9,999 | 100 |
| 10,000 (cap, both rosters) | 100 |

A bay of 1–99 is one marker, a partial hundred, with no numeral. From 9,901 through 9,999 the count is already 100 and the last dart is a partial hundred, so it gets no numeral. The cap is an exact ten thousand. The hundredth dart is a full hundred and still carries no numeral. Fighters per attack of 1,000 would draw 10 darts. The checklist uses the bay.

The sphere includes the loft, both prongs, the canopy, and the three engines. The prong tips set the nose of the sphere. A ring that clears the hex and clips a tip fails. A marker in the gap reads as a third prong and fails. One hundred markers is the same count the BattleShip contract already requires, on this hull's sphere, and it is under the 500-marker case P1 records. Do not borrow the BattleShip radius. Do not cap the formula. The grouping fix in the render memo is the remedy, if one is needed.

## BattleShip — re-shot, not a new mesh

The mesh contract is [BattleShip](cockpit-ship-stage-p1b-next-hulls.md#battleship--battleship) in the four-hull wave. This wave does not recut it, does not invent a second turret, and does not edit that sheet. The lines below are the re-shot, so the Frigate and the Havoc have their pair on screen.

### Role read

Cover the name plate. The ship still reads as a gun platform: a wide hex wedge, short for its beam, two turrets whose barrels break the top edge, a hundred escorts at a full bay. The turrets are the signature. The Frigate's missiles and the Havoc's prongs are other hulls.

### Numbers

Turns per warp are 4. Odds are 1.6. Shields stay 750. Mines 25, genesis 1, photons 0. Three engines. Not on `SHIP_TW_CHART_RANGE`. The fighter cap does not move.

| | Cost | Grant holds | Hold ceiling | Fighters | Markers at cap |
| --- | --- | --- | --- | --- | --- |
| Base `SHIP_SPECS_TW2002` | 88,500 | 80 | 80 | 10,000 | 100 |
| Live `SHIP_ROSTER_LIVE_TABLE` | 88,500 | 16 | 80 | 10,000 | 100 |

The live grant is 16 holds against a ceiling of 80. The wedge does not shrink. Photons stay 0, so the re-shot still has no missile bodies.

### Silhouette

Section `hex`. Kit: `turrets`. Accent `#c5c8ff` on the turret barrels and the stripe. At shields 0 the barrels and the stripe are still `#c5c8ff`. The barrels are thinner than the Frigate's dorsal missiles, and they sit on turret bodies, not on a rail. The outline still carries no split prow. Broader than the Merchant, shorter than the Imperial. The four-hull checklist is the pass list. This wave adds the pair shots in the read test below.

### Re-shot checklist

Same pose, sizes, and shield pair as the four-hull sheet. Name plate covered. Repeat at about 140px and at the hero crop, once beside the Frigate and once beside the Havoc.

1. The turret barrels break the top edge. A pair reads.
2. The hex shoulders read as a wide wedge, short for that beam.
3. Beside the Frigate, these barrels stay a turret pair, smaller than that hull's dorsal missiles.
4. Beside the Havoc, the guns stay on the back. No prongs grow ahead of this nose.
5. The barrels and the stripe are `#c5c8ff` at shields 0.
6. Markers sit outside the barrel tips and the hex beam. The cap is 100. No marker screen-box intersects the silhouette.

## Wave read test

Cover the name plate. These pairs have to stay apart at 140px and at the hero crop, on the three-quarter pose and head-on. The bible's full-fleet table still applies. This is the subset this wave can get wrong while cutting the two new faces, with the BattleShip, the Imperial, the Freighter, and the CargoTran already on screen from earlier waves.

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

## Build order

Missile Frigate, then Havoc GunStar. The photon boat goes first so the merged Imperial has its pair on screen and the missiles are locked larger than those forward barrels. The split prow is second, so it can be judged against the merged BattleShip and against the missiles just cut. Stop. Do not recut the BattleShip. Do not start the Star Master or the Constellation in this pass.

Done when both new hulls pass their checklists, the BattleShip and Imperial re-shots pass, the wave read test passes, and the inherited P1 bar holds (legend, exact bay on the stat line, side clip, phone still, reduced-motion still, `body.cu-seat` still, mesh module still under 40 KB gzipped). Show the two the way the hauler wave shows its set, shields empty and shields full. Show the Havoc once with a fitted TransWarp drive and once without. Marker clouds in this wave are 50 and 100, and the BattleShip's 100 is already on the merged hull. The clearance problem is the kit, not the count.

## Out of scope

The P1 spike hulls, except the Imperial re-shot named above. The four-hull wave (Scout Marauder, Merchant Freighter, BattleShip, Corporate FlagShip), except the BattleShip re-shot named above. The hauler wave (CargoTran, Colonial Transport, Taurean Mule). Escape Pod and T'Khasi Orion. Star Master, Constellation, Tholian Sentinel, and Interdictor Cruiser. Ferrengi hulls. Any edit under `web/`, any engine change, any test change, and any rewrite of `COMMANDER_NEXT.md`, `GAP_MAP.md`, `cockpit-ship-stage-p0.md`, `cockpit-ship-stage-p0-silhouette-bible.md`, `cockpit-ship-stage-p0-render.md`, `cockpit-ship-stage-p0-fx.md`, `cockpit-ship-stage-p1b-next-hulls.md`, `cockpit-ship-stage-p1b-batch2-haulers.md`, `cockpit-ship-stage-p1b-fleet-order.md`, `cockpit-ship-stage-p2-wire.md`, or `cockpit-ship-stage-p3-layout.md`. New events, new actions, and a layout split. Copying or tracing EIS, Markham, or ANSI ship art.
