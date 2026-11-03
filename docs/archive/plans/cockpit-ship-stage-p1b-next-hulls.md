# Next hulls — ship stage P1b

Parents: [P0 pack](cockpit-ship-stage-p0.md), [silhouette bible](cockpit-ship-stage-p0-silhouette-bible.md), [render decision](cockpit-ship-stage-p0-render.md).

The stills inventory is [stills/README.md](stills/README.md) (#344).

Docs only. This sheet does not change `web/*`, the engine, or tests. Classic top-and-front ANSI for every hull stays **UNVERIFIED**. Do not open, trace, or approximate EIS prints, EIS wallpaper, or Drew Markham ANSI. Looks below are invented from the public role numbers on `SHIP_SPECS_TW2002` and `SHIP_ROSTER_LIVE_TABLE` in `src/tw2k/engine/constants.py`. The one-paragraph picture in the bible still stands. This sheet is the mesh contract for the next four, so a follow-on does not invent a keel, a tower, or a turret while cutting faces.

## Implement after P1 merges

Do not start these meshes until the Merchant Cruiser and Imperial StarShip spike has merged and passed the render memo's pass list (read test, accent at zero shields, 100:1 markers, clip cameras, size). Build the four hulls below on the same `buildHullFaces` / `projectFace` path, in the order at the bottom, and stop there. The other eleven hulls stay on `fleet-glass-v1` until these four pass the same bar. If the spike misses the bar and opens the WebGL off-ramp, these silhouettes still apply. The renderer does not get to redesign them.

Shared rules, inherited:

- Dark blue-grey metal. The accent is a stripe, a canopy edge, and the kit. Canopy glass is a cool white mixed with the accent, except where a hull below names a different port glass. Idle engines are a short cyan-white cone. A fitted TransWarp drive (`ship.transwarp.fitted`) turns that cone magenta and nothing else.
- Empty shields leave scars and a missing bubble. The class accent stays. A full red body fails.
- Fighter markers: `n < 1 → 0`, else `max(1, ceil(n / 100))`. Fill `#ff2a2a`, stroke `#ff8888`. One dart is 100 fighters. A partial last hundred gets no numeral. The stat line keeps the exact bay. The legend is `each marker = 100 fighters`. Markers yaw with the hull. They are escorts, not corner ticks.
- The ring's innermost world radius is the bounding sphere of every face, including the kit named for that hull, plus a gap. On the canonical three-quarter pose and in the head-on clip, no marker's screen box intersects the hull silhouette.
- Canonical three-quarter is yaw `0.82`, pitch `0.5` (the held pose). Head-on is the warp clip camera `headon`. The side clip camera still has to show the same kit. P1's clip rule is the bar this wave inherits.
- The signature part has to read with the name plate covered, at about 140px tall and at a hero crop about 55% of the deck. A part that only exists in one of those views is not a signature.
- Kit names are the `PARTS` keys already in the bible (`canards`, `tower`, `turrets`, `cheeks`). Where the current `detail` string on a hull names a different part, that token is the sausage vocabulary. The `PARTS` kit wins. Do not grow a second signature.
- Section tokens stay the ones the loft already uses: `round`, `hex`, `box`. This wave adds no fourth section.
- The picture follows the job, not the hold grant. Where the live roster changes the grant or the fighter cap, the entry says so. Shields, photons, and mines stay on the base spec.

## Why these four

P1 teaches one trader (keel and shoulder pods) and one capital (long castle, four bells). The next wave has to lock four other jobs before the rest of the fleet is cut, and it has to be hulls a player actually flies.

There is no Destroyer class. `ShipClass` and `SHIP_SPECS_TW2002` have no destroyer key. BattleShip is the gun platform that fills that slot.

| Order | Key | Panel name | Why it is in this wave |
| --- | --- | --- | --- |
| 1 | `scout_marauder` | Scout Marauder | Cheapest chart hull (15,950), 2 turns per warp, offensive odds 2.0 (the highest on the chart). The fast thin ship. In this wave for the needle, not for its trading index. |
| 2 | `merchant_freighter` | Merchant Freighter | The day-one trader out of the starter. 33,400 credits, 2 turns per warp, hold ceiling 65, odds 0.8, trading index 325. Cheaper and faster than the Merchant Cruiser (41,300, 3 turns per warp, index 250). Its cheeks are the pair the spike's keel must stay distinct from. |
| 3 | `battleship` | BattleShip | Gun platform. 4 turns per warp, 10,000 fighters, 750 shields, odds 1.6, no photons, trading index 200. Broader than the Merchant, shorter than the Imperial. In this wave for the turret pair. |
| 4 | `corporate_flagship` | Corporate FlagShip | Corp capital. 20,000 fighters, 1,500 shields, corp-only, TransWarp chart ceiling 28, trading index 283. The tower is the part a mesh pass will turn into a castle if nobody writes it down. |

`SHIP_SPECS_TW2002["corporate_flagship"]["display_name"]` is `Corporate Flagship`. The panel and the bible spell the second word `FlagShip`. The mesh keeps the panel spelling. Do not rename the hull.

Trading index here is the published formula `(hold ceiling / turns per warp) × 10`, rounded to the nearest integer. `OldBBS_TW2002V8.faq.txt` prints the same figures. It is a role number, not a picture.

| Hull | Turns per warp | Hold ceiling | Index | Wave |
| --- | --- | --- | --- | --- |
| Colonial Transport | 6 | 250 | 417 | later |
| Imperial StarShip | 4 | 150 | 375 | P1 |
| Taurean Mule | 4 | 150 | 375 | later |
| Merchant Freighter | 2 | 65 | 325 | P1b |
| CargoTran | 4 | 125 | 313 | later |
| Corporate FlagShip | 3 | 85 | 283 | P1b |
| Merchant Cruiser | 3 | 75 | 250 | P1 |
| BattleShip | 4 | 80 | 200 | P1b |
| Scout Marauder | 2 | 25 | 125 | P1b |

Colonial Transport has the highest index and is the slow colonist. It waits. The Imperial is the spike. The Mule ties the Imperial and is the alien hauler. It waits. The freighter is the high-traffic trader in this set. `Slice-10_Slice_War_Manual.txt` names it as the usual first buy out of a Merchant Cruiser: cheap enough on day one, and fast enough at 2 turns per warp that the higher-index hulls do not replace it early. CargoTran sits one step down the index (313). The seat brain buys a CargoTran before the first genesis. The FAQ's own note on that hull is that a player might capture one, and that buying one is hard to justify. Its spine is a later wave. The trader this wave still needs, next to the spike's keel, is the freighter's broad face.

Missile Frigate (photon boat, 100,800 credits) and Havoc GunStar (shield tank, the third chart TransWarp hull) are real warships. BattleShip already covers the gun platform, so they wait. The FlagShip is the corp capital the same FAQ names for uncommissioned CEOs, and it is the tower.

## Scout Marauder — `scout_marauder`

### Role read

Cover the name plate. At 140px and at the hero crop the ship reads as a fast needle. The job is speed: longest length-to-beam in the fleet, a wisp of escorts, no cargo belly. A reader calls it a scout. The canards are the signature from the three-quarter pose, from head-on, and from the side clip.

### Numbers

Base row, then the live roster where a field moves. Turns per warp are 2 on both. Odds are 2.0 on both. Shields stay 100. Mines, genesis, and photons stay 0. Two engines.

| | Cost | Grant holds | Hold ceiling | Fighters | Markers at cap |
| --- | --- | --- | --- | --- | --- |
| Base `SHIP_SPECS_TW2002` | 15,950 | 25 | 25 | 150 | 2 |
| Live `SHIP_ROSTER_LIVE_TABLE` | 15,950 | 10 | 25 | 250 | 3 |

The live grant is 10 holds against a ceiling of 25. The picture does not shrink to match that grant. The fighter cap does change the escort count, so both caps are in the checklist. This hull is not on `SHIP_TW_CHART_RANGE`.

### Silhouette

Section `round`. A long thin body, canards near the nose, small fins at the tail, almost no beam. A top view is a line with two small blades. Each canard span is several times the body's beam, so the blades still read at 140px. The tail fins are smaller than the canards. Two engines, small, clustered on the centerline, inside the canard span. Head-on is a thin cross. Kit: `canards`. The `bridge` detail token is the shared canopy, and it stays shorter than the canards.

The outline carries no pods, no deep keel, no dish, no dorsal missile, and no tower. Odds of 2.0 do not add gun fairings. The speed is the length-to-beam, not a glow.

### Accent

`#5dffc8` on the canard edges, the tail-fin edge, and the stripe. Metal stays dark. The canopy mixes cool white with that mint. At shields 0 the stripe and the canard edges are still `#5dffc8`. Engine cones stay cyan-white. A fitted drive, if one is aboard, recolours the cones only.

### Three-quarter checklist

Pose: yaw `0.82`, pitch `0.5`. Name plate covered. Repeat at shields 0 and at shields full, at about 140px and at the hero crop.

1. The canards break the nose outline.
2. The tail fins show, and they are smaller than the canards.
3. The body reads as a line. It does not read as a wedge, a box, or a liner.
4. The accent on the canards and the stripe is `#5dffc8` at shields 0.
5. Every marker sits outside the canards and the fins. No marker screen-box intersects the silhouette.

### Head-on checklist

Clip camera `headon`. Same shield pair, same two sizes.

1. The body is a thin cross.
2. Two canard tips, one each side, are the widest points. They are blades, not cheek tanks.
3. Two small engine mouths sit inside that span.
4. The frame shows no tower, no turret pair, no square of bells, and no hoop.
5. Markers clear the canard tips. No marker screen-box intersects the silhouette.

### Marker clearance

| Bay | Markers |
| --- | --- |
| 0 | 0 |
| 1–100 | 1 |
| 150 (base cap) | 2 |
| 250 (live cap) | 3 |

The second marker at 150, and the third at 250, are partial hundreds. They get no numeral. The sphere includes the loft, both canards, both tail fins, and both engines. The canards set the beam. A ring sized from the tube alone clips them and fails. Pass both caps. The ring radius does not change between them. Only the count does.

## Merchant Freighter — `merchant_freighter`

### Role read

Cover the name plate. The ship reads as a fast wide trader: a short body, a broad cargo face, two large engines, a handful of escorts. A reader calls it a freighter. The cheeks are the signature. Three markers are not a fleet, so the face has to carry the job. This is the trader the spike's Merchant must stay distinct from.

### Numbers

Base row, then the live roster where a field moves. Turns per warp are 2 on both. Odds are 0.8 on both. Shields stay 500. Mines 2, genesis 2, photons 0. Two engines.

| | Cost | Grant holds | Hold ceiling | Fighters | Markers at cap |
| --- | --- | --- | --- | --- | --- |
| Base `SHIP_SPECS_TW2002` | 33,400 | 65 | 65 | 300 | 3 |
| Live `SHIP_ROSTER_LIVE_TABLE` | 33,400 | 30 | 65 | 300 | 3 |

The live grant is 30 holds against a ceiling of 65. The fighter cap does not move, so the escort count at the cap is 3 on both rosters. The cheeks stay the same size either way. This hull is not on `SHIP_TW_CHART_RANGE`.

### Silhouette

Section `box`, and flat. Overall length and overall width are close: the head-on face is almost as wide as the ship is long. Cheek tanks are that width. Two large engines sit inside the cheek outline, one each side, and they do not stick out past the cheeks. The cheeks are the cargo. The engines are the speed, and they stay inside the face.

Kit: `cheeks`. The `pods` detail token is not a second pair of Merchant shoulder pods. The `bridge` token is the shared canopy. Because the section is box, a short row of lit ports runs the flank. Port glass is a dim warm white so it does not compete with the cyan accent.

The outline carries no dorsal spine, no tower, no turrets, and no keel as deep as the Merchant's. A tall cabin box is the Colonial Transport. A long deck with a girder is the CargoTran. Neither part is available to borrow.

### Accent

`#7af0ff` on the cheek rims and the stripe. The cheek bodies are dark metal. At shields 0 the rims and the stripe are still `#7af0ff`. Engine cones stay cyan-white unless a drive is fitted, and then only the cones change.

### Three-quarter checklist

Same pose, sizes, and shield pair as the Scout.

1. Cheek tanks break both sides of a short body.
2. The body is short. A long deck fails, because that is the CargoTran.
3. No dorsal girder and no deep keel.
4. The cheek rims and the stripe are `#7af0ff` at shields 0.
5. Markers sit outside the cheeks. No marker screen-box intersects the silhouette.

### Head-on checklist

1. A broad face. The cheeks are the outer silhouette, almost as wide as the ship is long in the other view.
2. Two large engine mouths sit inside the cheeks.
3. The face is not a thin cross, and it is not a wedge with a keel underneath.
4. Markers clear the cheek tanks. No marker screen-box intersects the silhouette.

### Marker clearance

| Bay | Markers |
| --- | --- |
| 0 | 0 |
| 1–100 | 1 |
| 101–200 | 2 |
| 300 (cap, both rosters) | 3 |

The cap is an exact three hundred. A bay under the cap still uses the formula, and a partial last marker still gets no numeral. The sphere includes the loft, both cheeks, and both engines. The cheeks set the beam. A ring sized from the centerline loft lands on the cheeks and fails.

## BattleShip — `battleship`

### Role read

Cover the name plate. The ship reads as a gun platform: a wide short wedge, two turrets whose barrels break the top edge, a hundred escorts at a full bay. A reader calls it a warship. The turrets are the signature. The length is not. There is no Destroyer hull to draw instead.

### Numbers

Base row, then the live roster where a field moves. Turns per warp are 4 on both. Odds are 1.6 on both. Shields stay 750. Mines 25, genesis 1, photons 0. Three engines.

| | Cost | Grant holds | Hold ceiling | Fighters | Markers at cap |
| --- | --- | --- | --- | --- | --- |
| Base `SHIP_SPECS_TW2002` | 88,500 | 80 | 80 | 10,000 | 100 |
| Live `SHIP_ROSTER_LIVE_TABLE` | 88,500 | 16 | 80 | 10,000 | 100 |

The live grant is 16 holds against a ceiling of 80. The fighter cap does not move. Photons stay 0, so the silhouette has no missile bodies. This hull is not on `SHIP_TW_CHART_RANGE`.

### Silhouette

Section `hex`. A wide hex wedge, short for its beam. Broader than the Merchant, shorter than the Imperial. Two turrets stand on the dorsal face, far enough apart to read as a pair. Their barrels break the top edge from the side, from above, and in the three-quarter pose, including at 140px. The barrels are thinner than the Missile Frigate's dorsal missiles, and they sit on turret bodies, not on a rail along the spine. Turret bodies are dark metal.

Three engines sit in a low horizontal row in the tail, inside the hex width, below the turret line. They do not grow taller than the barrels. Kit: `turrets`. The `guns` detail token means these turrets. Do not also grow the Imperial forward-barrel path.

The outline carries no split prow, no castle, no tower, and no dorsal missile pair. A split prow is the Havoc GunStar. Two long missiles are the Missile Frigate.

### Accent

`#c5c8ff` on the turret barrels and the stripe. At shields 0 the barrels and the stripe are still `#c5c8ff`. Engine cones stay cyan-white unless a drive is fitted, and then only the cones change.

### Three-quarter checklist

Same pose, sizes, and shield pair as the Scout.

1. The turret barrels break the top edge. A pair reads, even when one turret sits slightly behind the other.
2. The hex shoulders read as a wide wedge, short for that beam.
3. The barrels are a turret pair. They are not two missiles on a dorsal rail, and they are not a split prow.
4. The barrels and the stripe are `#c5c8ff` at shields 0.
5. Markers sit outside the barrel tips and the hex beam. No marker screen-box intersects the silhouette.

### Head-on checklist

1. A wide hex face.
2. Two barrel tips above the hull, left and right. They are the high points.
3. Three engine mouths in a low row, inside the hex width.
4. The frame shows no prongs ahead of the nose, no tall centerline rectangle, and no square of four bells.
5. Markers clear the barrel tips. No marker screen-box intersects the silhouette.

### Marker clearance

| Bay | Markers |
| --- | --- |
| 0 | 0 |
| 1–100 | 1 |
| 10,000 (cap, both rosters) | 100 |

The cap is an exact hundred. The sphere includes the loft, both turret bodies, both barrels, and the three engines. The barrels set the top of the sphere. A ring that clears the hex and clips a barrel fails. One hundred markers is under the 500-marker case P1 records. A late frame does not change the count formula. The grouping fix in the render memo is the remedy, if one is needed.

## Corporate FlagShip — `corporate_flagship`

### Role read

Cover the name plate. The ship reads as a corp liner: a hull with a stepped command block standing amidships, taller than the hull is deep, and a cloud of escorts large enough to say the ship carries a fleet. A reader calls it a capital. The tower is the signature. It has to stay a tower when the Imperial's castle is on the screen next to it. Two hundred markers do not replace the tower.

### Numbers

Base row, then the live roster where a field moves. Turns per warp are 3 on both. Odds are 1.2 on both. Shields stay 1,500. Mines 100, genesis 10, photons 0. Three engines. `corp_only` is true. That is a yard gate, not a paint scheme. No crest and no lettering.

| | Cost | Grant holds | Hold ceiling | Fighters | Markers at cap |
| --- | --- | --- | --- | --- | --- |
| Base `SHIP_SPECS_TW2002` | 163,500 | 85 | 85 | 20,000 | 200 |
| Live `SHIP_ROSTER_LIVE_TABLE` | 163,500 | 20 | 85 | 20,000 | 200 |

The live grant is 20 holds against a ceiling of 85. The fighter cap does not move. The tower does not shrink to match the smaller grant. `SHIP_TW_CHART_RANGE` prints 28 hops for this hull. It is one of the three chart TransWarp hulls, with the Imperial StarShip (50) and the Havoc GunStar (16).

### Silhouette

Section `round`. A liner, ordinary beam, with a tower amidships. The tower is a stepped command block: a lower step and a smaller upper step. Its height, from the hull top to the top of the upper step, is greater than the hull's depth. The upper step is a block, wide enough to read as a rectangle head-on at 140px. It is not a stick, and it is not a dish.

The Imperial castle is the other way up: longer than it is tall, with a second step near the nose, and four bells in a square. This tower sits amidships. It does not run forward into a keep. Three engines sit in a low horizontal row at the stern, narrower than the hull beam, under the tower. Head-on they are a low line. They are not an X, and they are not a square.

Kit: `tower`. The `pods` detail token does not grow Merchant shoulder pods. The `bridge` token is the shared canopy, and it stays shorter than the tower. The outline carries no hoop, no dish, no forward barrel pair, and no cheek tanks. Mine capacity does not add launcher doors. The job on the screen is the capital, not a minelayer.

### Accent

`#ff77ff` on the tower's upper step and the stripe. The tower is painted metal. It is not an emissive lamp. At shields 0 the upper step and the stripe are still `#ff77ff`. When `ship.transwarp.fitted` is set, the engine cones go magenta and the tower stays the flat accent. Idle cones, with no drive fitted, stay cyan-white. Gold is the Imperial's accent. It does not appear on this hull.

### Three-quarter checklist

Same pose, sizes, and shield pair as the Scout. Repeat once with a fitted TransWarp drive and once without.

1. The tower breaks the top edge and is taller than the hull is deep.
2. The step reads as a command block amidships. It does not read as a long castle running toward the nose, and it does not read as a mast with a dish.
3. With a drive fitted, the cones are magenta and the upper step is still flat `#ff77ff`.
4. With shields at 0, the upper step and the stripe are still `#ff77ff`.
5. Markers sit outside the top of the tower. No marker screen-box intersects the silhouette.

### Head-on checklist

Same drive pair and shield pair.

1. A rectangle on the centerline, taller than the hull.
2. Three engine mouths in a low row, inside the beam.
3. The frame shows no X of engines, no square of four bells, no hoop, and no cheek tanks.
4. Markers clear the top of the tower. No marker screen-box intersects the silhouette.

### Marker clearance

| Bay | Markers |
| --- | --- |
| 0 | 0 |
| 1–100 | 1 |
| 20,000 (cap, both rosters) | 200 |

The cap is an exact two hundred. Two hundred is this wave's largest cloud, and it is under the 500-marker case P1 records. Do not cap the formula. The sphere includes the loft, both tower steps, and the three engines. The upper step sets the top of the sphere. A ring that clears the liner and clips the tower fails.

## Wave read test

Cover the name plate. These pairs have to stay apart at 140px and at the hero crop, on the three-quarter pose and head-on. The bible's full-fleet table still applies. This is the subset this wave can get wrong while cutting faces.

| Pair | What keeps them apart |
| --- | --- |
| Scout / Merchant | A needle and canards versus a keel and shoulder pods. |
| Scout / Freighter | A long thin cross versus a short broad face. |
| Freighter / Merchant | Wide cheeks versus a deep keel. |
| Freighter / CargoTran | Short cheeks versus a long dorsal spine. The spine is not in this wave. |
| FlagShip / Imperial | A tall tower amidships and three bells in a row versus a long castle and four bells in a square. |
| FlagShip / Star Master | A stepped block versus a dish on a mast. |
| BattleShip / Havoc | Turrets on a hex wedge versus a split prow. |
| BattleShip / Frigate | Turret barrels versus two dorsal missiles larger than the canopy. |
| BattleShip / FlagShip | A wide short wedge with a turret pair versus a liner with a tower. |

## Build order

Scout Marauder, then Merchant Freighter, then BattleShip, then Corporate FlagShip. The first cloud is two or three markers on a needle, which is the case where a fat ring swallows the ship. The freighter is next so the spike's Merchant has its pair on screen. The BattleShip is the hundred-marker gun platform. The FlagShip is last: its tower has to stay distinct from the Imperial castle, and 200 markers is the largest escort cloud in the wave.

Done when all four pass their checklists, the wave read test, and the inherited P1 bar (legend, exact bay on the stat line, side clip, phone still, reduced-motion still, `body.cu-seat` still, mesh module still under 40 KB gzipped). Show the four the way P1 shows the spike, shields empty and shields full, before any further hull leaves `fleet-glass-v1`.

## Out of scope

The other eleven player hulls. Ferrengi hulls. Any edit under `web/`, any engine change, any test change, and any rewrite of `COMMANDER_NEXT.md`, `GAP_MAP.md`, or `gap-map-refresh-v6`. New events, new actions, and a layout split. Copying or tracing EIS, Markham, or ANSI ship art.
