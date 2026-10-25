# Batch 2 haulers — ship stage P1b

Parents: [P0 pack](cockpit-ship-stage-p0.md), [silhouette bible](cockpit-ship-stage-p0-silhouette-bible.md), [render decision](cockpit-ship-stage-p0-render.md), [four-hull wave](cockpit-ship-stage-p1b-next-hulls.md), [fleet order](cockpit-ship-stage-p1b-fleet-order.md).

Stills for this sheet are listed in the [stills inventory](stills/README.md) (#344) under [p1b-batch2-haulers](stills/p1b-batch2-haulers/).

Docs only. This sheet does not change `web/*`, the engine, or tests. Classic top-and-front ANSI for every hull stays **UNVERIFIED**. Do not open, trace, or approximate EIS prints, EIS wallpaper, or Drew Markham ANSI. Looks below are invented from the public role numbers on `SHIP_SPECS_TW2002` and `SHIP_ROSTER_LIVE_TABLE` in `src/tw2k/engine/constants.py`, and from the one-paragraph pictures already in the bible. This sheet is the mesh contract for the hauler wave after the four in [cockpit-ship-stage-p1b-next-hulls.md](cockpit-ship-stage-p1b-next-hulls.md), so a follow-on does not turn the spine, the cabin, or the saddle back into the Freighter's cheeks or the Merchant's keel.

## Implement after P1 merges and after the four-hull wave

Do not start these meshes until both of these have landed:

1. The Merchant Cruiser and Imperial StarShip spike has merged and passed the render memo's pass list (read test, accent at zero shields, 100:1 markers, clip cameras, size).
2. The four-hull wave has merged and passed the same bar: Scout Marauder, Merchant Freighter, BattleShip, Corporate FlagShip.

Fleet order already names these three as its batch 2. This sheet is the mesh contract that wave uses, and the gate is the stricter one. The Freighter's cheeks have to be on screen before the spine, the cabin box, and the saddle are cut. Those are the shapes the Freighter checklist refuses to borrow.

Build the three hulls below on the same `buildHullFaces` / `projectFace` path, in the order at the bottom, and stop there. Every other player hull stays on `fleet-glass-v1` until these three pass the same bar. If the spike misses the bar and opens the WebGL off-ramp, these silhouettes still apply. The renderer does not get to redesign them.

Shared rules, inherited from the four-hull sheet:

- Dark blue-grey metal. The accent is a stripe, a canopy edge, and the kit. Canopy glass is a cool white mixed with the accent, except where a hull below names a different port glass. Idle engines are a short cyan-white cone. A fitted TransWarp drive (`ship.transwarp.fitted`) turns that cone magenta and nothing else. None of these three is on `SHIP_TW_CHART_RANGE`. The pass pose is idle cyan-white cones. A drive recolor is the inherited rule, and it is not a signature of this wave.
- Empty shields leave scars and a missing bubble. The class accent stays. A full red body fails.
- Fighter markers: `n < 1 → 0`, else `max(1, ceil(n / 100))`. Fill `#ff2a2a`, stroke `#ff8888`. One dart is 100 fighters. A bay of 1–99 is one marker, a partial hundred, and that dart gets no numeral. A bay of 100 is still one marker. The stat line keeps the exact bay. The legend is `each marker = 100 fighters`. The count is the onboard bay, not fighters per attack. Markers yaw with the hull. They are escorts, not corner ticks.
- The ring's innermost world radius is the bounding sphere of every face, including the kit named for that hull, plus a gap. On the canonical three-quarter pose and in the head-on clip, no marker's screen box intersects the hull silhouette.
- Canonical three-quarter is yaw `0.82`, pitch `0.5` (the held pose). Head-on is the warp clip camera `headon`. The side clip camera still has to show the same kit.
- The signature part has to read with the name plate covered, at about 140px tall and at a hero crop about 55% of the deck. A part that only exists in one of those views is not a signature.
- Kit names are the `PARTS` keys already in the bible (`spine`, `cargo`, `saddle`). `SHIPS` in `web/redesign.js` sets `detail` to `"pods"` on all three. That token is the sausage vocabulary. The `PARTS` kit wins. Do not grow Merchant shoulder pods, and do not grow a second signature.
- Section token stays `box`. This wave adds no fourth section.
- The picture follows the job, not the hold grant. Where the live roster changes the grant, the entry says so. Fighter caps do not move on these three. Shields, photons, and mines stay on the base spec.

## Why these three

The four-hull wave locks the day-one trader (Merchant Freighter, index 325, cheeks) next to the spike's Merchant Cruiser (index 250, keel and shoulder pods). The haulers still waiting are the three hold ships whose jobs are cargo, colonists, and a beast of burden.

Trading index is the published formula `(hold ceiling / turns per warp) × 10`, rounded to the nearest integer. `OldBBS_TW2002V8.faq.txt` prints the same figures. It is a role number, not a picture. The FAQ titles the 313 row "Cargo Transport". The panel, `SHIPS`, and `display_name` spell that hull `CargoTran`. Same ship. The FAQ also warns that "CT" (Colonial Transport) gets confused with a cargo transport. The cabin box and the spine stay different hulls.

| Hull | Key | Turns per warp | Hold ceiling | Index | This wave |
| --- | --- | --- | --- | --- | --- |
| Colonial Transport | `colonial_transport` | 6 | 250 | 417 | yes |
| Taurean Mule | `taurean_mule` | 4 | 150 | 375 | yes |
| Merchant Freighter | `merchant_freighter` | 2 | 65 | 325 | four-hull wave |
| CargoTran | `cargotran` | 4 | 125 | 313 | yes |
| Merchant Cruiser | `merchant_cruiser` | 3 | 75 | 250 | P1 spike |

The third early hauler past the Freighter is the Taurean Mule. `SHIP_SPECS_TW2002` has that key, `display_name` `Taurean Mule`, ceiling 150, 4 turns per warp, odds 0.5, index 375. The wave is these three. There is no missing hauler key to leave blank.

The Imperial StarShip ties the Mule at 375 and is the spike, a combat capital. The Interdictor Cruiser is the hoop barge (ceiling 40, 15 turns per warp, index 27, 100,000 fighters) and stays in fleet-order batch 5. The T'Khasi Orion (ceiling 60, odds 1.1) is the alien fast hull, not a hauler. None of those three is a substitute for the Mule.

| Order | Key | Panel name | Why it is in this wave |
| --- | --- | --- | --- |
| 1 | `cargotran` | CargoTran | Bulk hauler. 51,950 credits, 4 turns per warp, ceiling 125, odds 0.8, index 313. The long dorsal spine the Freighter checklist already refuses to borrow. The seat brain buys this hull by name. The FAQ's note is that a player might capture one, and that buying one is hard to justify next to the Mule. The picture is still the spine. |
| 2 | `colonial_transport` | Colonial Transport | Slow colonist. 63,600 credits, 6 turns per warp, ceiling 250, 200 fighters, odds 0.6, index 417 (the highest on the chart). The tall cabin. `SCANNER_BY_HULL` is `None` for this key. No dish grows to explain that. |
| 3 | `taurean_mule` | Taurean Mule | Alien hauler. Yard price 63,600, the same figure as the Colonial. 4 turns per warp, ceiling 150, 300 fighters, odds 0.5 (the worst on the chart), index 375. The saddle. `SHIP_ROSTER.md` records a price SOURCE-CONFLICT with the narrative and OldBBS 53,600. The yard figure in `SHIP_SPECS_TW2002` is 63,600. The price does not change the hump. |

`Slice-10_Slice_War_Manual.txt` names the Merchant Freighter as the hull worth selling the Cruiser for on day one. That hull is the four-hull wave. This wave is the next three haulers: the spine, the cabin, and the saddle.

## CargoTran — `cargotran`

### Role read

Cover the name plate. At 140px and at the hero crop the ship reads as a bulk hauler: a long low deck with a girder on its back, two engines, a handful of escorts. A reader calls it a cargo ship. The spine is the signature from the three-quarter pose, from head-on, and from the side clip. Four markers are not a fleet, so the girder has to carry the job. This is the long deck the Freighter must stay distinct from, and it is not the Merchant's keel.

### Numbers

Base row, then the live roster where a field moves. Turns per warp are 4 on both. Odds are 0.8 on both. Shields stay 1,000. Mines 1, genesis 2, photons 0. Fighters per attack stay 125, and that figure is not the marker count. Two engines. Holo scanner allowed. Not on `SHIP_TW_CHART_RANGE`. Transporter range on `SHIP_TRANSPORT_RANGE` is 5. Range does not add a dish or a door.

| | Cost | Grant holds | Hold ceiling | Fighters | Markers at cap |
| --- | --- | --- | --- | --- | --- |
| Base `SHIP_SPECS_TW2002` | 51,950 | 75 | 125 | 400 | 4 |
| Live `SHIP_ROSTER_LIVE_TABLE` | 51,950 | 50 | 125 | 400 | 4 |

The live grant is 50 holds against a ceiling of 125. The picture does not shrink to match that grant. The fighter cap does not move, so the escort count at the cap is 4 on both rosters.

### Silhouette

Section `box`, and flat. A long deck. Longer than the Merchant Freighter, lower than the Colonial Transport. A cargo spine runs most of the length and stands proud of the deck, so the side view is a low hull with a girder on its back. The girder is a ridge, taller than the deck skin and narrower than the beam. It is not a tower, and it is not a castle running toward the nose.

Two engines sit low in the tail, inside the beam, under the line of the spine. They do not stick up past the girder and they do not stick out past the deck.

Kit: `spine`. The `pods` detail token is sausage vocabulary. It does not grow shoulder pods or the Freighter's cheeks. The shared canopy stays shorter than the girder. A box section may keep a short row of lit ports. Port glass is a dim warm white so it does not compete with the yellow accent. Passenger ports are not the tell. A reader who names the ports has a Colonial, and the spine failed.

Distinct from the Merchant Freighter: the Freighter is short, and its cheeks make a face almost as wide as the ship is long. This deck is long, and the signature is on the back, not on the cheeks. Distinct from the Merchant Cruiser: the Cruiser is a medium arrow with a keel deep enough to break the underside and two shoulder pods. This hull has no keel of that depth and no shoulder pods. The cargo is the girder.

The outline carries no belly-tank pair, no saddle hump, no turret, and no dish. One mine does not add a launcher door. Odds of 0.8 do not add gun fairings.

### Accent

`#ffe566` on the spine's top edge and the stripe. The deck and the sides of the girder stay dark metal, so the signature reads as a line along the back. At shields 0 the edge and the stripe are still `#ffe566`. Engine cones stay cyan-white unless a drive is fitted, and then only the cones change.

### Three-quarter checklist

Pose: yaw `0.82`, pitch `0.5`. Name plate covered. Repeat at shields 0 and at shields full, at about 140px and at the hero crop.

1. A girder breaks the top edge along most of the length.
2. The body is long and low. A short broad face fails, because that is the Merchant Freighter. A deep underside keel fails, because that is the Merchant Cruiser.
3. No cabin-port row as the tell, no belly-tank pair, and no local hump with rear panniers.
4. The spine edge and the stripe are `#ffe566` at shields 0.
5. Every marker sits outside the girder. No marker screen-box intersects the silhouette.

### Head-on checklist

Clip camera `headon`. Same shield pair, same two sizes.

1. A low face. A narrow ridge on the centerline is the high point.
2. The ridge is a girder. It is not a tall cabin stack and not a rectangle the height of a tower.
3. Two engine mouths sit low, inside the beam.
4. The frame shows no cheek tanks, no deep keel under the nose, and no shoulder pods.
5. Markers clear the top of the girder. No marker screen-box intersects the silhouette.

### Marker clearance

| Bay | Markers |
| --- | --- |
| 0 | 0 |
| 1–99 | 1 |
| 100 | 1 |
| 101–200 | 2 |
| 201–300 | 3 |
| 400 (cap, both rosters) | 4 |

A bay of 1–99 is one marker, a partial hundred, with no numeral. The cap is an exact four hundred, so the fourth dart is a full hundred and still carries no numeral. The sphere includes the loft, the spine, and both engines. The girder sets the top of the sphere. A ring sized from the deck alone clips the spine and fails.

## Colonial Transport — `colonial_transport`

### Role read

Cover the name plate. The ship reads as a slow colonist: a fat box, tall for its length, two tanks under the belly, a row of cabin ports, two engines, and a thin escort. A reader calls it a transport full of people, and calls it unwilling to turn. The cabin and the belly tanks are the signature. Two markers are not a fleet. This is not the Freighter's wide face and not the Merchant's arrow.

### Numbers

Base row and the live roster match on every field this picture uses. Turns per warp are 6. Odds are 0.6. Shields stay 500. Mines 0, genesis 5, photons 0. Fighters per attack stay 100. A full bay is still 200 fighters, which is 2 markers. Two engines. `SCANNER_BY_HULL["colonial_transport"]` is `None`. Not on `SHIP_TW_CHART_RANGE`. Transporter range on `SHIP_TRANSPORT_RANGE` is 7. Range does not add a dish.

| | Cost | Grant holds | Hold ceiling | Fighters | Markers at cap |
| --- | --- | --- | --- | --- | --- |
| Base `SHIP_SPECS_TW2002` | 63,600 | 50 | 250 | 200 | 2 |
| Live `SHIP_ROSTER_LIVE_TABLE` | 63,600 | 50 | 250 | 200 | 2 |

The grant is 50 holds against a ceiling of 250. The box does not shrink to the grant and does not swell to the ceiling. The fighter cap does not move.

### Silhouette

Section `box`, and tall. Overall height is the point: a cabin block whose flank is high for the length, with a short row of ports along that flank. Two belly tanks hang under the box and break the underside from the side and from the three-quarter pose. They are rounder and lower than a keel. They are not shoulder pods, and they are not cheek tanks beside the nose.

Two engines sit in the tail, inside the box width, above the tank line. They stay smaller than the tanks. Head-on the tanks are the low outer masses and the engines sit inboard of them.

Kit: `cargo` (the belly tanks). The `pods` detail token is sausage vocabulary. It does not grow a second pair. The tanks are `cargo` only, and they hang under the hull. They are not the Merchant's shoulder pods. The shared canopy stays inside the cabin block. Port glass is a warm white so the green stripe stays the accent. The port row is long enough to read as cabins at 140px. It is not a gun deck.

Distinct from the Merchant Freighter: the Freighter is short and very wide, cheeks as the head-on face, no tall box. This hull is tall, and the cargo is underneath. Distinct from the Merchant Cruiser: the Cruiser is an arrow of ordinary length with a single deep keel and two pods up on the shoulders. This hull is a box, the tanks are a pair under the belly, and nothing on the outline is a wedge. Distinct from the CargoTran: the CargoTran is long and flat with a dorsal girder. This box is the tall one, and its cargo hangs below.

The outline carries no dorsal spine, no saddle hump, no turret, and no dish. No scanner on the hull means no mast. The Tholian Sentinel is the other box, and it is short, blunt, and plated, with no belly tanks and no cabin row as the main shape. That brick is a later wave. Do not borrow its slabs.

### Accent

`#7dff7d` on the stripe and the belly-tank rims. The tank bodies and the cabin stay dark metal. At shields 0 the rims and the stripe are still `#7dff7d`. Port glass stays warm white at shields 0, so a red damage wash does not repaint the cabins green and does not replace the stripe. Engine cones stay cyan-white unless a drive is fitted, and then only the cones change.

### Three-quarter checklist

Same pose, sizes, and shield pair as the CargoTran.

1. The flank reads as a tall box, high for its length.
2. Two belly tanks break the underside.
3. A row of warm-white ports shows along the flank. The row is cabins. It is not a gun line and not a green glow.
4. The tank rims and the stripe are `#7dff7d` at shields 0.
5. Markers sit outside the top of the box and outside the tanks. No marker screen-box intersects the silhouette.

### Head-on checklist

1. A tall face. Height beats beam.
2. Two tank bodies sit under the box and are the low outer masses.
3. Two engine mouths sit inside that span, above the tanks.
4. The face is not a short wide cheek plate, not a thin wedge with one keel, and not a nearly square armor brick.
5. Markers clear the box top and the tanks. No marker screen-box intersects the silhouette.

### Marker clearance

| Bay | Markers |
| --- | --- |
| 0 | 0 |
| 1–99 | 1 |
| 100 | 1 |
| 101–199 | 2 |
| 200 (cap, both rosters) | 2 |

A bay of 1–99 is one marker. The second dart, from 101 through 199, is a partial hundred and gets no numeral. The cap is an exact two hundred. Fighters per attack of 100 would draw one dart. The checklist uses the bay. The sphere includes the loft, both belly tanks, and both engines. The tanks set the bottom of the sphere and the cabin sets the top. A ring sized from the box sides clips a tank and fails. Two markers on a wide ring around a tall box is the right picture.

## Taurean Mule — `taurean_mule`

### Role read

Cover the name plate. The ship reads as a beast of burden: a low hull, a raised pack on the back, two panniers at the rear, two engines, a few escorts. A reader calls it a mule. The hump is the side signature. The panniers are the tail signature and the accent. Three markers do not replace the pack. This is not a Fed freighter and not the starter arrow.

### Numbers

Base row, then the live roster where a field moves. Turns per warp are 4 on both. Odds are 0.5 on both. Shields stay 600. Mines 0, genesis 1, photons 0. Fighters per attack stay 150, and that figure is not the marker count. Two engines. Holo scanner allowed. Not on `SHIP_TW_CHART_RANGE`. Transporter range on `SHIP_TRANSPORT_RANGE` is 5. Range does not add a dish.

| | Cost | Grant holds | Hold ceiling | Fighters | Markers at cap |
| --- | --- | --- | --- | --- | --- |
| Base `SHIP_SPECS_TW2002` | 63,600 | 40 | 150 | 300 | 3 |
| Live `SHIP_ROSTER_LIVE_TABLE` | 63,600 | 50 | 150 | 300 | 3 |

The live grant is 50 holds against a base grant of 40, ceiling 150 either way. The pack does not grow to match the live grant. The fighter cap does not move, so the escort count at the cap is 3 on both rosters. The yard cost stays 63,600.

### Silhouette

Section `box`, and low. A saddle: the hull stays close to the centerline, a cargo pack sits on the back as one hump, and two panniers hang at the rear corners. The hump is local. It occupies the mid-body. It does not run the length of the deck. The panniers sit aft, lower than the pack, and they break the tail outline from the side, from above, and in the three-quarter pose.

Two engines sit between the panniers, low, and they do not stick out past the panniers. Head-on the pack is a bump on the centerline, and the panniers read as two rear masses once the three-quarter pose shows the tail. They are smaller than the Freighter's cheek tanks and they sit at the stern, not amidships.

Kit: `saddle`. The `pods` detail token is sausage vocabulary. The panniers belong to `saddle`, not to a second pod pair, and they are not Merchant shoulder pods or Colonial belly tanks. The pack is darker metal. The panniers take the accent. The shared canopy stays lower than the hump. A cabin-port row would make this the Colonial. Keep the flank quiet.

Distinct from the Merchant Freighter: the Freighter's cargo is a pair of cheeks that set a broad face almost as wide as the ship is long, on a short body. The Mule's cargo is a hump plus rear panniers, and the body stays low without becoming that face. Distinct from the Merchant Cruiser: the Cruiser's tell is a ventral keel and shoulder pods on an arrow. The Mule's tell is dorsal, and the extra volumes are at the tail. Distinct from the CargoTran: the CargoTran's girder runs the deck. This hump stops. Distinct from the Colonial: the Colonial is a tall cabin with tanks underneath. This hull is the low one.

The outline carries no full-length spine, no tall cabin, no cheek plate, no keel of Merchant depth, no crescent, and no dish. A holo scanner does not grow the Star Master's mast. Odds of 0.5 do not add gun fairings.

### Accent

`#d7b48a` on the panniers and the stripe. The pack stays darker metal, so the hump reads as shape and the panniers carry the accent. At shields 0 the panniers and the stripe are still `#d7b48a`, and the pack is still dark. Engine cones stay cyan-white unless a drive is fitted, and then only the cones change.

### Three-quarter checklist

Same pose, sizes, and shield pair as the CargoTran.

1. The pack's hump breaks the top edge amidships, and it stops short of the nose and the tail.
2. Two rear panniers break the tail corners.
3. The body stays low. A tall cabin fails, because that is the Colonial. A short face as wide as the ship is long fails, because that is the Freighter. A girder the length of the deck fails, because that is the CargoTran. A deep keel fails, because that is the Merchant.
4. The panniers and the stripe are `#d7b48a` at shields 0. The pack stays dark metal.
5. Markers sit outside the hump and the panniers. No marker screen-box intersects the silhouette.

### Head-on checklist

1. A low face with one bump on the centerline.
2. The bump is a pack, wider than a girder and shorter than a cabin stack.
3. Two engine mouths sit low, inside the beam. The panniers, when the tail is in frame, are the outer rear masses and they wear `#d7b48a`.
4. The frame shows no shoulder pods, no belly-tank pair under a tall box, and no cheek plate that sets the whole beam.
5. Markers clear the hump and the pannier corners. No marker screen-box intersects the silhouette.

### Marker clearance

| Bay | Markers |
| --- | --- |
| 0 | 0 |
| 1–99 | 1 |
| 100 | 1 |
| 101–200 | 2 |
| 300 (cap, both rosters) | 3 |

A bay of 1–99 is one marker, a partial hundred, with no numeral. The cap is an exact three hundred. The sphere includes the loft, the pack, both panniers, and both engines. The hump sets the top. The panniers set the tail corners. A ring that clears the low hull and clips the hump, or clears the hump and clips a pannier from above, fails.

## Wave read test

Cover the name plate. These pairs have to stay apart at 140px and at the hero crop, on the three-quarter pose and head-on. The bible's full-fleet table still applies. This is the subset this wave can get wrong while cutting the three faces, with the Merchant and the Freighter already on screen from earlier waves.

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

## Build order

CargoTran, then Colonial Transport, then Taurean Mule. The spine goes first so the Freighter from the four-hull wave has its pair on screen. The cabin is next, so the girder does not grow ports and call itself a colonist. The saddle is last: the hump has to stay local once both the girder and the cabin exist.

Done when all three pass their checklists, the wave read test, and the inherited P1 bar (legend, exact bay on the stat line, side clip, phone still, reduced-motion still, `body.cu-seat` still, mesh module still under 40 KB gzipped). Show the three the way the four-hull wave shows its set, shields empty and shields full, before any further hull leaves `fleet-glass-v1`. Marker clouds in this wave are 4, 2, and 3. The clearance problem is the kit, not the count.

## Out of scope

The P1 spike hulls. The four-hull wave (Scout Marauder, Merchant Freighter, BattleShip, Corporate FlagShip). The other player hulls, including the Tholian Sentinel and the Interdictor Cruiser. Ferrengi hulls. Any edit under `web/`, any engine change, any test change, and any rewrite of `COMMANDER_NEXT.md`, `GAP_MAP.md`, `cockpit-ship-stage-p0.md`, `cockpit-ship-stage-p1b-next-hulls.md`, `cockpit-ship-stage-p1b-fleet-order.md`, or the P2 and P3 sheets. New events, new actions, and a layout split. Copying or tracing EIS, Markham, or ANSI ship art.
