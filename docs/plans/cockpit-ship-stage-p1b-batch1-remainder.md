# Batch 1 remainder — ship stage P1b

Parents: [P0 pack](cockpit-ship-stage-p0.md), [silhouette bible](cockpit-ship-stage-p0-silhouette-bible.md), [render decision](cockpit-ship-stage-p0-render.md), [four-hull wave](cockpit-ship-stage-p1b-next-hulls.md), [fleet order](cockpit-ship-stage-p1b-fleet-order.md).

Docs only. This sheet does not change `web/*`, the engine, or tests. Classic top-and-front ANSI for every hull stays **UNVERIFIED**. Do not open, trace, or approximate EIS prints, EIS wallpaper, or Drew Markham ANSI. Looks below are invented from the public role numbers on `POD_SPEC`, `SHIP_SPECS_TW2002`, and `SHIP_ROSTER_LIVE_TABLE` in `src/tw2k/engine/constants.py`, and from the one-paragraph pictures already in the bible. The pod's live row is `SHIP_ROSTER_LIVE_POD`, not a key on the live table. This sheet is the mesh contract for the two fleet-order batch-1 hulls that still have no contract after the four in [cockpit-ship-stage-p1b-next-hulls.md](cockpit-ship-stage-p1b-next-hulls.md), so a follow-on does not turn the stub fins into canards or the crescent into a second needle.

## Implement after the spike and the four-hull wave

Do not start these meshes until both of these have landed:

1. The Merchant Cruiser and Imperial StarShip spike has merged and passed the render memo's pass list (read test, accent at zero shields, 100:1 markers, clip cameras, size).
2. The four-hull wave has merged and passed the same bar: Scout Marauder, Merchant Freighter, BattleShip, Corporate FlagShip.

Fleet order names this cut as the rest of its batch 1. Escape Pod and T'Khasi Orion sit with the Scout. The Scout mesh contract already landed in the four-hull wave. This sheet does not rewrite it and does not recut that needle. The new meshes are the two hulls in that batch that have no contract yet. The Scout's canards have to be on screen before the stub fins and the crescent are cut. Those are the shapes the Scout checklist refuses to borrow.

The [hauler wave](cockpit-ship-stage-p1b-batch2-haulers.md) and the [gun wave](cockpit-ship-stage-p1b-batch3.md) are later in fleet order. Their contracts already exist. This sheet does not wait for those meshes, and it does not pull the spine, the cabin, the saddle, the missiles, or the prongs into this cut.

Build the two hulls below on the same `buildHullFaces` / `projectFace` path, in the order at the bottom, and stop there. Every other player hull stays on `fleet-glass-v1` until these two pass the same bar, judged with the merged Scout. If the spike misses the bar and opens the WebGL off-ramp, these silhouettes still apply. The renderer does not get to redesign them.

Shared rules, inherited from the four-hull sheet:

- Dark blue-grey metal. The accent is a stripe, a canopy edge, and the kit. Canopy glass is a cool white mixed with the accent, except where a hull below names a different port glass. Idle engines are a short cyan-white cone. A fitted TransWarp drive (`ship.transwarp.fitted`) turns that cone magenta and nothing else. Neither hull is on `SHIP_TW_CHART_RANGE`. The pass pose is idle cyan-white cones. A drive recolor is the inherited rule, and it is not a signature of this wave.
- Empty shields leave scars and a missing bubble. The class accent stays. A full red body fails. A full cyan body on the pod fails. A full body in `#ff6d8a` on the T'Khasi fails.
- Fighter markers: `n < 1 → 0`, else `max(1, ceil(n / 100))`. Fill `#ff2a2a`, stroke `#ff8888`. One dart is 100 fighters. A bay of 1–99 is one marker, a partial hundred, and that dart gets no numeral. A bay of 100 is still one marker. The stat line keeps the exact bay. The legend is `each marker = 100 fighters`. The count is the onboard bay, not fighters per attack. Markers yaw with the hull. They are escorts, not corner ticks.
- The ring's innermost world radius is the bounding sphere of every face, including the kit named for that hull, plus a gap. On the canonical three-quarter pose and in the head-on clip, no marker's screen box intersects the hull silhouette.
- Canonical three-quarter is yaw `0.82`, pitch `0.5` (the held pose). Head-on is the warp clip camera `headon`. The side clip camera still has to show the same kit.
- The signature part has to read with the name plate covered, at about 140px tall and at a hero crop about 55% of the deck. A part that only exists in one of those views is not a signature.
- Kit names are the `PARTS` keys already in the bible (`fins`, and `swept`). Where the current `detail` string names a different part, that token is called out on the hull. Do not grow a second signature.
- Section token stays `round` on the pod, the T'Khasi, and the Scout. This wave adds no fourth section.
- The picture follows the job, not the hold grant. Where the live roster changes the grant or the ceiling, the entry says so. Fighter caps do not move on these two. Shields, photons, and mines stay on the base spec.

## Why these hulls

Fleet order's batch 1 is Scout Marauder, Escape Pod, Merchant Freighter, T'Khasi Orion. The four-hull wave locked the needle and the freighter, and it also locked the BattleShip and the FlagShip, which fleet order places later. Two hulls in batch 1 still need a mesh contract. The third, the Scout, is the needle this wave re-shots. The Freighter stays on its four-hull contract and is not recut here.

Trading index is the published formula `(hold ceiling / turns per warp) × 10`, rounded to the nearest integer. `OldBBS_TW2002V8.faq.txt` prints the same figures. It is a role number, not a picture. The FAQ prints TI 8 on the Escape Pod and TI 300 on the T'Khasi Orion. TI 8 is the live ceiling, 5 holds at 6 turns per warp. `POD_SPEC` stores a base ceiling of 50, and 50 / 6 × 10 rounds to 83. The capsule does not grow to chase 83. The FAQ prints TI 125 on the Scout and TI 325 on the Merchant Freighter. The picture follows the lifeboat and the crescent.

| Hull | Key | Turns per warp | Hold ceiling | Index | This wave |
| --- | --- | --- | --- | --- | --- |
| Escape Pod | `escape_pod` | 6 | 5 live, 50 base | 8 live, 83 base | new mesh |
| Scout Marauder | `scout_marauder` | 2 | 25 | 125 | re-shot, contract already landed |
| T'Khasi Orion | `tkhasi_orion` | 2 | 60 | 300 | new mesh |
| Merchant Freighter | `merchant_freighter` | 2 | 65 | 325 | four-hull wave |
| CargoTran | `cargotran` | 4 | 125 | 313 | fleet-order batch 2, later |

The FAQ's note on the pod is that the craft comes free when a ship is destroyed, the Scout excepted, and that five holds are not a reason to trade with it. The FAQ's note on the T'Khasi is that the hull is a poor trade next to the Freighter: the same 2 turns per warp, five fewer holds, and no holoscanner. Neither note adds a part. The Freighter's cheeks already have a contract. This wave does not recut them.

| Order | Key | Panel name | Why it is in this wave |
| --- | --- | --- | --- |
| 1 | `escape_pod` | Escape Pod | Lifeboat, not sold. 6 turns per warp, 50 fighters, 50 shields, one engine. Odds 0.6 on `POD_SPEC` and 0.8 on the live pod. One marker. Two stub fins and one round nose port. `SCANNER_BY_HULL` is `None` for this key. No dish grows to explain the FAQ's density-scanner sentence. |
| 2 | `tkhasi_orion` | T'Khasi Orion | Alien fast hull, borrowed from specialty so the Scout's pair lands with the Scout. 42,500 credits on the base spec, 2 turns per warp, ceiling 60, 750 fighters, 750 shields, odds 1.1, index 300. The crescent. `SCANNER_BY_HULL` is density. No mast grows to explain that. |

`POD_SPEC["display_name"]` is `Escape Pod`. The key is not in `SHIP_SPECS_TW2002`. `ship_cost` returns 0, and the yard never sells the hull. `SHIP_SPECS_TW2002["tkhasi_orion"]["display_name"]` is `T'Khasi Orion`. The panel spells it the same way. Do not rename either hull.

## Escape Pod — `escape_pod`

### Role read

Cover the name plate. At 140px and at the hero crop the ship reads as a lifeboat: a short capsule, almost as tall as it is long, one round port on the nose, two stub fins large next to the body, one engine. A reader calls it a pod. The fins are the signature from the side and from the three-quarter pose. The round port is the signature head-on, and it still shows on the nose in the three-quarter pose. One marker is not a fleet, so the capsule has to carry the job. This is the hull the Scout's needle must stay distinct from.

### Numbers

Base row, then the live roster where a field moves. Turns per warp are 6 on both. Odds are 0.6 on `POD_SPEC` and 0.8 on `SHIP_ROSTER_LIVE_POD`. Shields stay 50. Mines 0, genesis 0, photons 0. Fighters per attack stay 10, and that figure is not the marker count. A full bay is 50 fighters, which is 1 marker. One engine. `SCANNER_BY_HULL["escape_pod"]` is `None`. Not on `SHIP_TW_CHART_RANGE`. Transporter range on `SHIP_TRANSPORT_RANGE` is 0. Range does not add a dish or a door.

| | Cost | Grant holds | Hold ceiling | Fighters | Markers at cap |
| --- | --- | --- | --- | --- | --- |
| Base `POD_SPEC` | 0 | 5 | 50 | 50 | 1 |
| Live `SHIP_ROSTER_LIVE_POD` | 14,446 | 1 | 5 | 50 | 1 |

The bible's 5 holds are the fresh loadout on `POD_SPEC` and the live ceiling. The base ceiling is 50. The live grant is 1 hold against that ceiling of 5. The capsule does not shrink to the live ceiling and does not swell to the base ceiling. The fighter cap does not move, so the escort count at the cap is 1 on both rosters. The live cost cell is the catalog figure `hull_spec` copies when the live roster is on. `ship_cost` still returns 0. The FAQ prints the price as n/a. The price does not change the fins. `SHIP_ROSTER.md` records the chart pod as price 0, 5 holds, 50 fighters, 50 shields, 6 turns per warp, odds 0.6.

### Silhouette

Section `round`. A short capsule, almost as tall as it is long. One round port sits on the nose and is the head-on face. Two stub fins sit large next to the body and are the side silhouette. They break the outline from the side, from above, and in the three-quarter pose, including at 140px. They are stubby. They do not run the length of a needle, and they do not sweep past the tail.

One engine sits low in the tail, on the centerline, inside the fin span. It does not stick up past the capsule and it does not stick out past the fins.

Kit: `fins`. `SHIPS` sets `detail` to an empty string, `engines` to 1, and `accent` to `#55ffff`. The empty detail string stays empty. Do not add `bridge`. The shared canopy is the wrong glass. The port is the glass, and it carries the cyan. The fins stay dark metal, so they read as shape and the port reads as the face. A third fin, dorsal or otherwise, fails. The accent belongs on the port.

Today's loft runs from x=34 to x=−40 with sy/sz up to 20, so the body is about twice as long as it is tall. The bible's proportion replaces that loft. Today's `fins` kit draws two side plates at `zOut` 16, inside a mid-station sz of 20, plus one dorsal fin in the accent whose tip sits 10 above the mid-station sy. Those side plates lose to the capsule, and the dorsal fin steals the cyan. Today's port is a glass bulb on stations at x=10 and x=16, short of the nose station at x=34. The mesh pass replaces all three: a capsule almost as tall as it is long, two stub fins outside the beam, one round port on the nose.

Distinct from the Scout Marauder: the Scout is the longest, thinnest hull in the fleet, with canards near the nose and small tail fins. This body is short, and the fins are the side silhouette rather than a smaller tail. Re-shot the Scout beside this hull. Distinct from the T'Khasi Orion: the T'Khasi's plates leave the nose and run past the tail as a crescent. These fins stop. Distinct from the Merchant Cruiser: the Cruiser is a medium arrow with a deep keel and shoulder pods. This hull has no keel and no pods. Distinct from the Merchant Freighter: the Freighter is short, and its cheeks set a broad face. This face is a round port. The Freighter is not recut.

The outline carries no canards, no crescent, no cargo bay, no gun, no tower, no cheek tanks, no dish, and no keel. Odds of 0.6, and the live odds of 0.8, do not add gun fairings. The pod is not a trader that has been scaled down.

### Accent

`#55ffff` on the nose port. The fins and the capsule stay dark metal. A stripe, where the shared stripe is drawn, is the same cyan, and it does not repaint the metal. At shields 0 the port is still `#55ffff`, and the metal is still dark. A full cyan body fails. Engine cones stay cyan-white unless a drive is fitted, and then only the cone changes. Mint `#5dffc8` is the Scout's accent. It does not appear on this port.

### Three-quarter checklist

Pose: yaw `0.82`, pitch `0.5`. Name plate covered. Repeat at shields 0 and at shields full, at about 140px and at the hero crop. Repeat once in a frame that also shows the merged Scout.

1. Two stub fins break the side outline and are large next to a short body.
2. The body is a capsule, almost as tall as it is long. A long needle fails, because that is the Scout. A crescent that runs past the tail fails, because that is the T'Khasi. A broad cheek face fails, because that is the Freighter. A deep keel fails, because that is the Merchant.
3. One round port shows on the nose. The port is `#55ffff`. The metal stays dark.
4. One engine sits inside the fin span. A second engine fails.
5. The port is `#55ffff` at shields 0. A full cyan body fails.
6. The marker sits outside the fins and the port. No marker screen-box intersects the silhouette.

### Head-on checklist

Clip camera `headon`. Same shield pair, same two sizes.

1. One round port is the face. It is `#55ffff`. The body reads as a short capsule, tall for its length.
2. Two stub fins are the side masses, large next to the body. They are not canards on a needle, and they are not swept plates.
3. One engine mouth sits low, inside the fins.
4. The frame shows no canard pair, no crescent, no cheek plate, no keel, no tower, and no dish.
5. The marker clears the fins and the port. No marker screen-box intersects the silhouette.

### Marker clearance

| Bay | Markers |
| --- | --- |
| 0 | 0 |
| 1–49 | 1 |
| 50 (cap, both rosters) | 1 |

A bay of 1–49 is one marker, a partial hundred, with no numeral. The cap is 50, still inside that first hundred. The only dart is a partial hundred and still carries no numeral. There is no second marker on this hull. The bible's row for the pod is the same count: any fighters, cap 50, one marker. Fighters per attack of 10 would still be one dart. The checklist uses the bay.

The sphere includes the loft, both fins, the nose port, and the one engine. The fins set the sides. The capsule, once it is almost as tall as it is long, sets the top. Remeasure after those fins exist. Do not reuse the Merchant radius (~93) or the old `fighterSlots` start of 56. A borrowed Merchant ring leaves the lifeboat in a hole. A ring that clears the capsule and clips a fin fails.

## T'Khasi Orion — `tkhasi_orion`

### Role read

Cover the name plate. The ship reads as an alien fast hull: swept plates leave the nose and run back past the tail, so the planform is a crescent, with two engines and a handful of escorts. A reader calls it a crescent. The crescent is the signature from the three-quarter pose, from head-on, and from the side clip. Eight markers do not replace the plates. This is the hull the Scout's canards must stay distinct from.

### Numbers

Base row, then the live roster where a field moves. Turns per warp are 2 on both. Odds are 1.1 on both. Shields stay 750. Mines 5, genesis 1, photons 0. Fighters per attack stay 250, and that figure is not the marker count. A full bay is 750 fighters, which is 8 markers. Two engines. `SCANNER_BY_HULL["tkhasi_orion"]` is density. Not on `SHIP_TW_CHART_RANGE`. Transporter range on `SHIP_TRANSPORT_RANGE` is 3. Range does not add a dish or a door.

| | Cost | Grant holds | Hold ceiling | Fighters | Markers at cap |
| --- | --- | --- | --- | --- | --- |
| Base `SHIP_SPECS_TW2002` | 42,500 | 30 | 60 | 750 | 8 |
| Live `SHIP_ROSTER_LIVE_TABLE` | 42,250 | 30 | 60 | 750 | 8 |

The live grant is 30 holds against a ceiling of 60, the same grant and the same ceiling as the base row. The plates do not shrink to the grant. The fighter cap does not move, so the escort count at the cap is 8 on both rosters. The live cost is 42,250, which is the figure the FAQ prints. The yard figure in `SHIP_SPECS_TW2002` is 42,500. `SHIP_ROSTER.md` records a price SOURCE-CONFLICT with the narrative and OldBBS 36,000. The price does not change the crescent. The FAQ's shipstats column prints 760 fighters on this hull. The spec and the live table both store 750. The mesh uses 750, which is 8 markers. The FAQ figure does not add a ninth dart.

### Silhouette

Section `round`. Swept plates leave the nose and run back past the tail. The planform is a crescent. The plates are the beam, and they are the first shape from the side, from above, and head-on. The crescent is one pair. It is unbroken by a dorsal gadget. No second blade sits near the nose.

Two engines sit low in the tail, inside the plate span, behind the line of the plates. They do not stick out past the plate tips. They are not an X, and they are not a square of bells.

Kit: `swept`. `SHIPS` sets `detail` to `"wings bridge"` and `engines` to 2. The `wings` token is sausage vocabulary. It does not grow a second pair, and it does not grow the Scout's canards. The `bridge` token is the shared canopy, and it stays inside the crescent, shorter than the plates. A density scanner does not grow the Star Master's mast. One genesis does not add a door. Five mines do not add a launcher. Odds of 1.1 do not add gun fairings.

Today's loft runs from x=90 to x=−70 with sz about 6, the same thin family as the Scout's tube. Today's `swept` kit calls `wing` twice. The long pair uses `zOut` 32 against that sz of about 6, and its trailing root is the tail station plus 4, which is short of the tail. The drawn tip sits further forward still. The plate does not leave the nose, and it does not run past the tail. The second call is an accent pair at `zOut` 14, from near the nose to the mid station. That pair reads as canards. The `wings` detail token grows a third pair. The mesh pass replaces all three with one crescent. `zOut` 32 is the floor of the beam, not a license to keep the short root. The sphere is the plates, including the run past the tail.

Distinct from the Scout Marauder: the Scout is a needle with canards near the nose and small tail fins. This planform is a crescent, and nothing on it is a canard. The Scout is re-shot from the four-hull wave. Do not recut it to help this comparison. Distinct from the Escape Pod: the pod is a short capsule with two stub fins and a round port. These plates are the length of the ship and past it. Distinct from the Merchant Cruiser: the Cruiser is a Fed wedge with a keel and shoulder pods. This hull has no keel. Distinct from the Merchant Freighter: the Freighter's beam is a pair of cheeks on a short body. This beam is a crescent. The Freighter is not recut. Distinct from the Constellation: the Constellation's tell is an X of four nacelles. These are two plates. That X is a later wave. Distinct from the Havoc GunStar: the Havoc's guns run ahead of the nose as two prongs with a gap. This nose is the root of the crescent, and the plates run aft.

The outline carries no canards, no stub-fin capsule, no keel, no tower, no dish, no dorsal missile, no turret pair, no split prow, and no hoop.

### Accent

`#ff6d8a` on the plate edges and the stripe. The plate bodies and the hull stay dark metal, so the crescent reads as shape and the edges carry the accent. At shields 0 the edges and the stripe are still `#ff6d8a`. A full body in that hex fails. Engine cones stay cyan-white unless a drive is fitted, and then only the cones change. Mint is the Scout. Cyan on a round port is the pod. Neither colour appears on these plates.

### Three-quarter checklist

Same pose, sizes, and shield pair as the pod. Repeat once in a frame that also shows the merged Scout.

1. Swept plates leave the nose and run back past the tail. The planform reads as a crescent.
2. The crescent is one pair. A second blade near the nose fails, because that is the Scout's canards. Two stub fins on a short capsule fail, because that is the pod.
3. Beside the Scout, the canards stay on the Scout and the crescent stays on this hull.
4. The plate edges and the stripe are `#ff6d8a` at shields 0. The plate bodies stay dark metal.
5. No mast, no dish, no keel, and no X of nacelles.
6. Markers sit outside the plate tips. No marker screen-box intersects the silhouette.

### Head-on checklist

Same shield pair, same two sizes.

1. Two plate tips are the widest points. The body between them is a thin core. The tips wear `#ff6d8a` on the edge.
2. The plates are one crescent seen on edge. A thin cross with small canard blades fails, because that is the Scout. A round port as the face fails, because that is the pod.
3. Two engine mouths sit low, inside the plate span.
4. The frame shows no canard pair, no stub fins, no cheek plate, no tower, no dish, no X of nacelles, and no split prow.
5. Markers clear the plate tips. No marker screen-box intersects the silhouette.

### Marker clearance

| Bay | Markers |
| --- | --- |
| 0 | 0 |
| 1–99 | 1 |
| 100 | 1 |
| 101–200 | 2 |
| 700 | 7 |
| 701–749 | 8 |
| 750 (cap, both rosters) | 8 |

A bay of 1–99 is one marker, a partial hundred, with no numeral. From 701 through 749 the count is already 8 and the last dart is a partial hundred, so it gets no numeral. The cap is 750, not an exact hundred. The eighth dart is a partial hundred and still carries no numeral. Fighters per attack of 250 would draw 3 darts. The checklist uses the bay.

The sphere includes the loft, both plates, the canopy, and both engines. The plates set the beam and the run past the tail sets the stern. A ring sized to the tube clips a plate and fails. Do not borrow the Scout's length-dominated ring and pull it in to this fuselage. Eight markers is a handful of darts on the plate sphere. Do not cap the formula. The grouping fix in the render memo is the remedy, if one is needed.

## Scout Marauder — re-shot, not a new mesh

The mesh contract is [Scout Marauder](cockpit-ship-stage-p1b-next-hulls.md#scout-marauder--scout_marauder) in the four-hull wave. This wave does not recut it, does not move the canards, and does not edit that sheet. The lines below are the re-shot, so the pod and the T'Khasi have their pair on screen.

### Role read

Cover the name plate. The ship still reads as a fast needle. Longest, thinnest hull in the fleet. Canards near the nose, small tail fins, a wisp of escorts. The canards are the signature. The pod's stub fins and the T'Khasi's crescent are other hulls.

### Numbers

Turns per warp are 2. Odds are 2.0. Shields stay 100. Mines 0, genesis 0, photons 0. Two engines. Not on `SHIP_TW_CHART_RANGE`. `SCANNER_BY_HULL` is density. Transporter range is 0. The fighter cap is the one that moves.

| | Cost | Grant holds | Hold ceiling | Fighters | Markers at cap |
| --- | --- | --- | --- | --- | --- |
| Base `SHIP_SPECS_TW2002` | 15,950 | 25 | 25 | 150 | 2 |
| Live `SHIP_ROSTER_LIVE_TABLE` | 15,950 | 10 | 25 | 250 | 3 |

The live grant is 10 holds against a ceiling of 25. The needle does not shrink. Show both caps. The second marker at 150, and the third at 250, are partial hundreds. They get no numeral. The ring radius does not change between the caps. Only the count does.

### Silhouette

Section `round`. Kit: `canards`. Accent `#5dffc8` on the canard edges, the tail-fin edge, and the stripe. At shields 0 the stripe and the canard edges are still `#5dffc8`. The tail fins stay smaller than the canards. Today's glass `LOFT` stations run from x=98 to x=−82 with sy/sz under 6, and the canard `zOut` is 18. The bounding sphere is length-dominated. Keep that sphere. A ring pulled in to the beam clips the canards. The four-hull checklist is the pass list. This wave adds the pair shots in the read test below.

### Re-shot checklist

Same pose, sizes, and shield pair as the four-hull sheet. Name plate covered. Repeat at about 140px and at the hero crop, once beside the pod and once beside the T'Khasi. Repeat the marker caps at 2 and at 3.

1. The canards break the nose outline. The body reads as a line.
2. The tail fins show, and they are smaller than the canards.
3. Beside the pod, this hull stays the long needle. No stub fins grow into the side silhouette of a capsule, and no round cyan port becomes the face.
4. Beside the T'Khasi, the blades stay canards near the nose. No crescent runs past this tail.
5. The canard edges and the stripe are `#5dffc8` at shields 0.
6. Markers sit outside the canards and the fins. The base cap is 2. The live cap is 3. No marker screen-box intersects the silhouette.

## Wave read test

Cover the name plate. These pairs have to stay apart at 140px and at the hero crop, on the three-quarter pose and head-on. The bible's full-fleet table still applies. This is the subset this wave can get wrong while cutting the two new faces, with the Scout already on screen from the four-hull wave.

| Pair | What keeps them apart |
| --- | --- |
| Escape Pod / Scout | A short finned capsule and a round nose port versus a long needle and canards. The Scout is re-shot. |
| Scout / T'Khasi | Canards on a needle versus a crescent that leaves the nose and runs past the tail. The Scout is re-shot. |
| Escape Pod / T'Khasi | Two stub fins on a short capsule versus swept plates. A fin that stretches into a crescent fails. A plate that collapses into a stub fin fails. |
| Escape Pod / Merchant | A capsule with no keel versus a medium arrow, a deep keel, and shoulder pods. The Merchant is not recut. |
| Escape Pod / Freighter | A round port and stub fins versus a short broad cheek face. The Freighter is not recut. |
| T'Khasi / Freighter | A crescent versus cheeks, on the same 2 turns per warp. The picture is the plates. The Freighter is not recut. |
| T'Khasi / Merchant | A crescent versus a Fed wedge and a keel. |
| T'Khasi / Constellation | Two swept plates versus an X of four nacelles. The Constellation is not in this wave. No X grows on the T'Khasi. |
| T'Khasi / Havoc | A crescent running aft versus two prongs ahead of a short nose. The Havoc is a later wave. No prongs grow on the T'Khasi. |
| Escape Pod / Colonial | A capsule and a round port versus a tall cabin box and a port row. The Colonial is a later wave. The pod must not grow cabins. |

## Build order

Escape Pod, then T'Khasi Orion. The lifeboat goes first so the merged Scout has its pair on screen, and so the one marker is locked outside the fins instead of inside a borrowed Merchant ring. The crescent is second, so it can be judged against that Scout and against the capsule just cut. The plates have to run past the tail once the stub fins exist, so a fin does not stretch into a crescent and a plate does not shrink into a canard. Stop. Do not recut the Scout. Do not recut the Freighter. Do not start the hauler wave or the gun wave in this pass.

Done when both new hulls pass their checklists, the Scout re-shot passes at marker caps 2 and 3, the wave read test passes, and the inherited P1 bar holds (legend, exact bay on the stat line, side clip, phone still, reduced-motion still, `body.cu-seat` still, mesh module still under 40 KB gzipped). Show the two the way the hauler wave shows its set, shields empty and shields full. Marker clouds in this wave are 1 and 8, and the Scout's 2 and 3 are already on the merged hull. The clearance problem is the kit, not the count.

## Out of scope

The P1 spike hulls. The four-hull wave (Scout Marauder, Merchant Freighter, BattleShip, Corporate FlagShip), except the Scout re-shot named above. The hauler wave (CargoTran, Colonial Transport, Taurean Mule). The gun wave (Missile Frigate, Havoc GunStar, and the BattleShip re-shot already written). Star Master, Constellation, Tholian Sentinel, and Interdictor Cruiser. Ferrengi hulls. Any edit under `web/`, any engine change, any test change, and any rewrite of `COMMANDER_NEXT.md`, `GAP_MAP.md`, `cockpit-ship-stage-INDEX.md`, `cockpit-ship-stage-p0.md`, `cockpit-ship-stage-p0-silhouette-bible.md`, `cockpit-ship-stage-p0-render.md`, `cockpit-ship-stage-p0-fx.md`, `cockpit-ship-stage-marker-math.md`, `cockpit-ship-stage-p1-acceptance.md`, `cockpit-ship-stage-p1b-next-hulls.md`, `cockpit-ship-stage-p1b-batch2-haulers.md`, `cockpit-ship-stage-p1b-batch3.md`, `cockpit-ship-stage-p1b-fleet-order.md`, `cockpit-ship-stage-p2-wire.md`, or `cockpit-ship-stage-p3-layout.md`. New events, new actions, and a layout split. Copying or tracing EIS, Markham, or ANSI ship art.
