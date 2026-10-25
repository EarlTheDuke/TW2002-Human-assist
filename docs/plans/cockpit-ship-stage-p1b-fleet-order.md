# Fleet order — the other 15 player hulls (P1b)

Parent: [P0 pack](cockpit-ship-stage-p0.md). Looks: [silhouette bible](cockpit-ship-stage-p0-silhouette-bible.md). Path: [render decision](cockpit-ship-stage-p0-render.md).

The stills inventory is [stills/README.md](stills/README.md) (#344).

Planning only. Surveyed `feature/grokbot-player` @ `8a31f30` (#194). Refreshed onto `1f3b36f9` (#406). #406 records the [stills inventory](stills/README.md) [p1b-batch5-brick](stills/p1b-batch5-brick/) row as measured and Pass. #405 (`1b27c879`) stamps that Pass on product #402 (`0bf683e3`). Tholian Sentinel and Interdictor Cruiser are Landed+Pass. Those two left `fleet-glass-v1`. Tholian Sentinel is 169 faces, hash `7650706109f94fb1`. Interdictor Cruiser is 341 faces, hash `c3d45f327a3c6564`. Gzip is about 16 KB. 30 PNGs are in that directory. [Batch-5 readiness](cockpit-ship-stage-p1b-batch5-readiness.md) records the same Pass. This sheet does not edit that note. Sticky next is the P2 wire product. That product is next. #404 (`fe296f55`) is a standalone P2 FX sample. Research only. It does not replace the product wire. It does not open the wire. #403 (`ba92e845`) is a P3 layout research mock. Samples only. The P3 gate stays closed. P3 stays behind P2. #390 (`2907e80b`) stamps the batch-4 dish Pass on product #387 (`3114c994`). This sheet does not change the engine, the cockpit, the meshes, or the warp clips. This sheet does not stamp Pass and does not open the wire.

Batch 3 guns, Missile Frigate and Havoc GunStar, are Landed+Pass. Product #363 (`5ebec08f`). Pass #370 (`223dacfa`). Those two left `fleet-glass-v1`. Batch 4, Star Master and Constellation, landed on the SVG path in #387 (`3114c994`). Those two left `fleet-glass-v1`. Star Master is 183 faces. Constellation is 311 faces. Pass is #390 (`2907e80b`) on [batch 4 acceptance](cockpit-ship-stage-p1b-batch4-acceptance.md). #387 leaves Corporate FlagShip at 210 faces, Imperial StarShip at 311, BattleShip at 226, and Havoc GunStar at 261. The [stills inventory](stills/README.md) (#393, `b136f08d`) records [p1b-batch4-dish](stills/p1b-batch4-dish/) as measured and Pass. #394 (`36d75ef8`) notes that on the inbound map. Batch 5, Tholian Sentinel and Interdictor Cruiser, is Landed+Pass. Product #402 (`0bf683e3`). Pass #405 (`1b27c879`) on [batch 5 acceptance](cockpit-ship-stage-p1b-batch5-acceptance.md). Those two left `fleet-glass-v1`. Tholian Sentinel is 169 faces, hash `7650706109f94fb1`. Interdictor Cruiser is 341 faces, hash `c3d45f327a3c6564`. Gzip is about 16 KB. The [stills inventory](stills/README.md) (#406, `1f3b36f9`) records [p1b-batch5-brick](stills/p1b-batch5-brick/) as measured and Pass, with 30 PNGs. Sticky next is the P2 wire product. That product is next. #404 (`fe296f55`) is a P2 FX sample, research only, and does not replace the product wire. P2 FX and the `#viewport` retirement are that wire. The P2 wire gate stays closed until Commander opens it. P3 layout stays behind P2. The P3 gate stays closed.

Merchant Cruiser and Imperial StarShip are the P1 spike. They are not in the 15. Stills directory: [`stills/p1-merchant-imperial/`](stills/p1-merchant-imperial/). TBD scaffold. No PNG. The scaffold does not stamp Pass. The roster below is the other player `ShipClass` values in `src/tw2k/engine/models.py`, in the order a product Cur should take them. Role numbers are `SHIP_SPECS_TW2002` and `POD_SPEC` in `src/tw2k/engine/constants.py`. Marker count is the sticky formula: `n < 1 → 0`, else `max(1, ceil(n / 100))`. Accent hexes are the `SHIPS` entries in `web/redesign.js`, already recorded in the bible. The picture follows the job, not the live-roster grant. The only fighter cap that moves a marker count is the Scout (base 150 → 2 markers, live 250 → 3).

Bible anchors use the heading slug. The heading text is `### <id> — <panel name>`.

## Gate

Do not start P1b product code until the P1 spike PR is merged. That spike builds Merchant Cruiser and Imperial StarShip on `buildHullFaces` / `projectFace` to the bar in the render memo, including the throwaway 1,000-marker ring.

Stay on the shared SVG path unless that spike failed the bar. A fleet batch does not open three.js or raw WebGL. If the spike missed the bar, stop. The off-ramp in the render memo is the next decision. It still consumes `buildHullFaces`, it does not add a second hull file, and it does not get a head start by meshing the next trader.

One batch at a time, in the order below. Every batch edits `web/hull-meshes.js`, and the 40 KB gzip budget is cumulative. The next batch rebases onto the merged one. Ferrengi hulls stay out. No engine field, no new event, no viewport removal, no layout split. Batch 3 has landed and passed. Batch 4 has landed and passed. Batch 5 has landed and passed. Sticky next is the P2 wire product. That product is next. P3 stays behind P2. The P3 gate stays closed. The P2 wire stays closed until Commander opens it.

## Why this group order

Work starter/trader, then mid, then capital, then specialty. Batch 1 borrows the T'Khasi from specialty so the Scout's pair lands with the Scout. Batch 4 borrows the last two mid hulls so the tower, the dish, and the X land together. The batch table is the sequence. The group label is why the hull sits there.

| Group | Hulls | Why this group, in this place |
| --- | --- | --- |
| Starter / trader | Scout Marauder, Escape Pod, Merchant Freighter, CargoTran, Colonial Transport, Taurean Mule | A seat sits in these before it can buy a capital, and they are the pairs that would otherwise all read as the Merchant. |
| Mid | Missile Frigate, BattleShip, Havoc GunStar, Star Master, Constellation | One loud kit each, on a body the spike already shaded, at 50 or 100 markers. |
| Capital | Corporate FlagShip | The only remaining hull a reader will call a capital. It has to be a tower once the Imperial's castle is on screen. |
| Specialty | T'Khasi Orion, Tholian Sentinel, Interdictor Cruiser | Crescent, brick, and hoops. The brick and the hoops wait until an ordinary ring has shipped. The crescent ships in batch 1 beside the Scout. |

## Batches

Shared bar, every hull in the batch:

- Matches its bible entry at the current ~140px panel and at a hero crop about 55% of the deck.
- Name plate covered: a reader names the job in this sheet. Shields at 0 and shields full: the accent hex is still that colour. Scars are allowed. A full red body is not.
- Markers: 0 fighters → 0 marks, a bay of 1–100 → 1 mark, and the cap count in this sheet. Legend stays `each marker = 100 fighters`. The stat block keeps today's words, order, and exact bay.
- Canonical three-quarter (yaw `0.82`, pitch `0.5`): no marker screen-box intersects the silhouette. Innermost world radius is the bounding sphere of every face, kit included, plus a gap.
- One existing warp clip, side camera and head-on camera. The kit still reads. `holdWarp` still pauses a frame.
- Phone still, reduced-motion still, and `body.cu-seat` canonical still. No loop on those three.
- Faces land in `web/hull-meshes.js` only, so a clip that calls `buildHullFaces` picks them up. The module stays under 40 KB gzipped.
- No engine change, no new action, no new event field. A test that pins a `fleet-glass-v1` face count or AABB for a hull in the batch is updated in that batch.
- The PR carries name-covered shots at both sizes, shields empty, shields full, and the cap-marker case.

### Batch 1 — needle, pod, freighter, crescent

Scout Marauder, Escape Pod, Merchant Freighter, T'Khasi Orion.

Done when the shared bar holds for all four, and a covered-name reader separates these pairs at both sizes: Escape Pod / Scout (finned capsule versus long needle), Scout / T'Khasi (needle and canards versus crescent), Merchant / Freighter (deep keel versus wide cheeks and a short body). Scout markers are shown at 2 and at 3. The Merchant from the spike is re-shot next to the Freighter.

### Batch 2 — the three haulers

CargoTran, Colonial Transport, Taurean Mule.

Done when the shared bar holds for all three, and a covered-name reader separates Colonial / CargoTran / Mule (tall cabin box versus long spine versus saddle hump) at both sizes. The trio is judged together in this batch.

### Batch 3 — guns

Missile Frigate, BattleShip, Havoc GunStar.

Done when the shared bar holds for all three, and a covered-name reader separates BattleShip / Havoc (turrets on a wide wedge versus a split prow) at both sizes. The Frigate reads as a photon boat: two dorsal missiles larger than the canopy. The Imperial from the spike is re-shot so those missiles stay larger than its forward barrels. Cap markers: Frigate 50, BattleShip 100, Havoc 100.

Missile Frigate and Havoc GunStar landed in #363 (`5ebec08f`) on the SVG path. Those two left `fleet-glass-v1`. Pass is #370 (`223dacfa`). Stills: [`cockpit-ship-stage-p1b-batch3-guns-product.md`](cockpit-ship-stage-p1b-batch3-guns-product.md) (#337, `d211b4e9`), directory [`stills/p1b-batch3-guns/`](stills/p1b-batch3-guns/). This sheet does not stamp Pass. It does not change this batch's place or the gate above.

### Batch 4 — dish, X, and the other capital

Star Master, Constellation, Corporate FlagShip.

Done when the shared bar holds for all three, and a covered-name reader separates FlagShip / Imperial / Star Master (tall tower versus long castle versus a dish) at both sizes. The Constellation reads as an X of four nacelles, with no castle, no dish, and no prongs. Cap markers: Star Master 50, Constellation 50, FlagShip 200. The Imperial is re-shot beside the tower.

Star Master and Constellation landed in #387 (`3114c994`) on the SVG path (`buildHullFaces` / `projectFace`). Those two left `fleet-glass-v1`. Star Master is 183 faces. Constellation is 311 faces. Corporate FlagShip stays 210 faces, Imperial StarShip stays 311, BattleShip stays 226, and Havoc GunStar stays 261. #387 re-shots the tower, the castle, the wedge, and the prongs. It does not recut those faces. The [stills inventory](stills/README.md) (#393, `b136f08d`) records [`stills/p1b-batch4-dish/`](stills/p1b-batch4-dish/) as measured and Pass. #394 (`36d75ef8`) notes that on the inbound map. Pass is #390 (`2907e80b`) on [batch 4 acceptance](cockpit-ship-stage-p1b-batch4-acceptance.md). Product sheet: [`cockpit-ship-stage-p1b-batch4-dish-product.md`](cockpit-ship-stage-p1b-batch4-dish-product.md) (#387, `3114c994`). It does not change this batch's place or the gate above. The Corporate FlagShip stays the cut-2 mesh. This cut re-shots that tower. This sheet does not stamp Pass.

### Batch 5 — brick and hoops

Tholian Sentinel, Interdictor Cruiser. Two hulls, on purpose. The Interdictor's full bay is 1,000 markers outside a hoop that is larger than the body. That measurement is the Cur. A third new silhouette in the same PR would hide a frame miss inside an art miss.

Done when the shared bar holds for both, and a covered-name reader separates Tholian / Colonial (short plated brick versus tall cabin box) and Constellation / Interdictor (an X of engines versus two hoops) at both sizes. Colonial and Constellation are re-shot from their merged batches. Interdictor markers: 1,000 at 100,000 fighters, orbiting outside the hoops. Reuse the marker grouping the spike recorded for the throwaway 1,000-ring (one group moved by a transform, or one canvas layer for markers only). The count formula does not gain a silent cap. Record the drift frame time at 1,000 on this hull, the one whose hoops are real.

Tholian Sentinel and Interdictor Cruiser landed in #402 (`0bf683e3`) on the SVG path (`buildHullFaces` / `projectFace`). Those two left `fleet-glass-v1`. Tholian Sentinel is 169 faces, hash `7650706109f94fb1`. Interdictor Cruiser is 341 faces, hash `c3d45f327a3c6564`. Gzip is about 16 KB (16,343 bytes, level 9), under 40 KB. 30 PNGs are in [`stills/p1b-batch5-brick/`](stills/p1b-batch5-brick/). Pass is #405 (`1b27c879`) on [batch 5 acceptance](cockpit-ship-stage-p1b-batch5-acceptance.md). The [stills inventory](stills/README.md) (#406, `1f3b36f9`) records that directory as measured and Pass. [Batch-5 readiness](cockpit-ship-stage-p1b-batch5-readiness.md) records the same Pass. This sheet does not edit that note. #396 (`90065381`) recorded this cut in flight on [P2 readiness](cockpit-ship-stage-p2-readiness.md). This sheet does not edit that note. Product sheet: [`cockpit-ship-stage-p1b-batch5-brick-product.md`](cockpit-ship-stage-p1b-batch5-brick-product.md) (#402, `0bf683e3`). That sheet records the faces and does not stamp Pass. Sticky next is the P2 wire product. That product is next. #404 (`fe296f55`) is a P2 FX sample. Research only. It does not replace the product wire. #403 (`ba92e845`) is a P3 layout research mock. Samples only. The P3 gate stays closed. P3 stays behind P2. This Pass does not open the wire and does not open the layout. It does not change this batch's place or the gate above. This sheet does not stamp Pass.

## Per hull

Panel names match the bible and `SHIPS`. The yard's `display_name` spells Flagship and Gunstar as one word; the panel names below are the ones the picture uses.

### 1. Scout Marauder — starter / trader — batch 1

Bible: [`scout_marauder — Scout Marauder`](cockpit-ship-stage-p0-silhouette-bible.md#scout_marauder--scout-marauder). Accent `#5dffc8`. Kit `canards`.

Read, name covered: a fast needle. Longest, thinnest hull in the fleet. Canards near the nose, small tail fins, no cargo pods and no deep keel.

AABB: unusual. Today's glass `LOFT` stations run from x=98 to x=−82 with sy/sz under 6, and the canard `zOut` is 18 (`web/hull-meshes.js`). The bible keeps that length-to-beam. The bounding sphere is length-dominated, so the ring sits far off the fuselage. Keep that sphere. A ring pulled in to the beam clips the canards in the top camera. Cap markers are 2 (base 150 fighters) and 3 (live 250). Show both. Either cloud is a handful of darts on a wide ring.

### 2. Escape Pod — starter / trader — batch 1

Bible: [`escape_pod — Escape Pod`](cockpit-ship-stage-p0-silhouette-bible.md#escape_pod--escape-pod). Accent `#55ffff`. Kit `fins`. The cyan lives on the port glass. Metal stays dark.

Read, name covered: a lifeboat. Short capsule, one round nose port, two stub fins large next to the body, one engine. No bay, no gun, no tower.

AABB: unusual. The bible makes it almost as tall as it is long, with the fins as the side silhouette and the round port as the head-on silhouette. Remeasure the sphere after those fins exist. Do not reuse the Merchant radius (~93) or the old `fighterSlots` start of 56. Cap is 50 fighters, so the ring is a single marker, outside the fins.

### 3. Merchant Freighter — starter / trader — batch 1

Bible: [`merchant_freighter — Merchant Freighter`](cockpit-ship-stage-p0-silhouette-bible.md#merchant_freighter--merchant-freighter). Accent `#7af0ff`. Kit `cheeks`.

Read, name covered: a fast freighter. Short and very wide. Cheek tanks make the head-on view a broad face. Two large engines. No spine, no tall cabin box, no keel as deep as the Merchant's.

AABB: unusual. The bible's head-on face is almost as wide as the ship is long. Today's `LOFT` sz already reaches 40 on stations only 74 long (x=30 to x=−44), and the cheeks sit outside that. The cheeks set the beam. A length-only radius leaves markers in the cheek silhouette. Cap is 300 fighters → 3 markers.

### 4. T'Khasi Orion — specialty — batch 1

Bible: [`tkhasi_orion — T'Khasi Orion`](cockpit-ship-stage-p0-silhouette-bible.md#tkhasi_orion--tkhasi-orion). Accent `#ff6d8a`. Kit `swept`.

Read, name covered: an alien fast hull. Swept plates leave the nose and run back past the tail, so the planform is a crescent. No keel and no tower. The crescent is unbroken by a dorsal gadget.

AABB: unusual. The plates set the beam and run past the tail. Today's swept wings use `zOut` 32 against a station sz of about 6. The sphere is the plates. Markers yaw with the hull and stay outside the plate tips. Cap is 750 fighters → 8 markers.

### 5. CargoTran — starter / trader — batch 2

Bible: [`cargotran — CargoTran`](cockpit-ship-stage-p0-silhouette-bible.md#cargotran--cargotran). Accent `#ffe566`. Section box. Kit `spine`.

Read, name covered: a bulk hauler. Long flat deck, a cargo spine the full length standing proud, so the side view is a low hull with a girder on its back. Flatter than the Colonial, longer than the Freighter. Passenger ports are not the tell.

AABB: ordinary long-low body, Merchant's family. The spine is a dorsal ridge along most of the length, and the ring has to clear that ridge on the side camera. Cap is 400 fighters → 4 markers.

### 6. Colonial Transport — starter / trader — batch 2

Bible: [`colonial_transport — Colonial Transport`](cockpit-ship-stage-p0-silhouette-bible.md#colonial_transport--colonial-transport). Accent `#7dff7d`. Section box. Kit `cargo` (belly tanks). Port glass is a warm white so the green stripe stays the accent.

Read, name covered: a slow colonist ship. A fat box, tall for its length, two belly tanks, a row of cabin ports along the flank. No gun breaks the outline.

AABB: unusual. Height and the belly tanks dominate, where the Merchant's measured body is 162×32×64. The sphere includes the tanks hanging under the box. Cap is 200 fighters → 2 markers. A wide empty ring around a tall box is the right picture. Pulling it in to the loft clips the tanks.

### 7. Taurean Mule — starter / trader — batch 2

Bible: [`taurean_mule — Taurean Mule`](cockpit-ship-stage-p0-silhouette-bible.md#taurean_mule--taurean-mule). Accent `#d7b48a`. Section box. Kit `saddle`. The panniers take the accent. The pack is darker metal.

Read, name covered: a beast of burden. Low hull, a raised cargo pack, two rear panniers. The pack's hump is the side silhouette.

AABB: unusual. The hump sets the top and the panniers set the tail corners. The sphere includes both, or markers sit on the hump in the side camera and on the panniers from above. Cap is 300 fighters → 3 markers.

### 8. Missile Frigate — mid — batch 3

Bible: [`missile_frigate — Missile Frigate`](cockpit-ship-stage-p0-silhouette-bible.md#missile_frigate--missile-frigate). Accent `#ffb15a`. Kit `missiles`, plus `rails`. Missile noses are a hotter amber than the hull stripe.

Read, name covered: a photon boat. Two long dorsal missiles and a rail, noses forward, proud of the fuselage, larger than the canopy. Cheek barrels on the Imperial stay smaller than these bodies.

AABB: a long slim body, ordinary in plan. The missiles set the top of the volume. A ring sized to the fuselage clips them from the side. Cap is 5,000 fighters → 50 markers, between the 25 and the 500 the spike already showed. The live grant of 12 holds does not change the picture.

### 9. BattleShip — mid — batch 3

Bible: [`battleship — BattleShip`](cockpit-ship-stage-p0-silhouette-bible.md#battleship--battleship). Accent `#c5c8ff`. Section hex. Kit `turrets`. #387 (`3114c994`) re-shots this wedge and leaves the face count at 226.

Read, name covered: a gun platform. A wide hex wedge, short for its beam, two turrets whose barrels break the top edge from the side and from above. Broader than the Merchant and shorter than the Imperial. The turrets are the job.

AABB: unusual. Beam and turret height drive the sphere more than length. Today's `LOFT` sz reaches 30 on stations from x=62 to x=−58. Include the turret barrels. Cap is 10,000 fighters → 100 markers.

### 10. Havoc GunStar — mid — batch 3

Bible: [`havoc_gunstar — Havoc GunStar`](cockpit-ship-stage-p0-silhouette-bible.md#havoc_gunstar--havoc-gunstar). Accent `#ff8844`. Section hex. Kit `prongs`. #387 (`3114c994`) re-shots these prongs and leaves the face count at 261.

Read, name covered: a shield tank and gunship. Short body, split prow. Two prongs run ahead of the nose and are the silhouette from the side, the top, and head-on (two bright tips with a gap). No turret pair.

AABB: unusual. The nose of the volume is the prong tips, past the loft nose. Today's prong tip station is at nose x+26. Markers stay outside those tips. A marker in the gap reads as a third prong. Cap is 10,000 fighters → 100 markers.

### 11. Star Master — mid — batch 4

Bible: [`star_master — Star Master`](cockpit-ship-stage-p0-silhouette-bible.md#star_master--star-master). Accent `#9ad7ff`. Kit `mast` and `dish`. Landed in #387 (`3114c994`) on the SVG path. 183 faces. Left `fleet-glass-v1`. Pass is #390 (`2907e80b`).

Read, name covered: a mid combat hull whose whole job is a dish. Modest arrow, a mast, a dish wider than the beam. The top view is a circle on a stick. That circle is a plate, not a hoop around the body.

AABB: unusual. The plate, not the fuselage beam, sets the top radius. Markers orbit outside the plate. They do not ring the mast as if the dish were the Interdictor's hoop. Cap is 5,000 fighters → 50 markers.

### 12. Constellation — mid — batch 4

Bible: [`constellation — Constellation`](cockpit-ship-stage-p0-silhouette-bible.md#constellation--constellation). Accent `#d0d6ff`. Kit `quad`. Panel name stays Constellation. Landed in #387 (`3114c994`) on the SVG path. 311 faces. Left `fleet-glass-v1`. Pass is #390 (`2907e80b`).

Read, name covered: a mid combat hull with four nacelles in an X. Head-on is that X and little else. No castle, no dish, no prongs.

AABB: unusual. The X, not the fuselage, sets y and z, and the nacelles trail past the tail. Head-on, markers sit outside the arms. Cap is 5,000 fighters → 50 markers. Four engines already sit off the centerline. The quad kit is the larger cross, and the sphere uses that cross.

### 13. Corporate FlagShip — capital — batch 4

Bible: [`corporate_flagship — Corporate FlagShip`](cockpit-ship-stage-p0-silhouette-bible.md#corporate_flagship--corporate-flagship). Accent `#ff77ff`. Kit `tower`. TransWarp, when fitted, is magenta in the engines only. The tower stays the magenta accent, not a second glow source. #387 (`3114c994`) re-shots this tower and leaves the face count at 210.

Read, name covered: a corp capital. A liner with a tower amidships taller than the hull is deep. The tower is a stepped command block. Head-on it is a rectangle on the centerline, with no square of engine bells and no hoop.

AABB: unusual. The tower sets the height. Today's upper tower box tops out near y=37 (mid-station sy is 16, and the stacked boxes add the rest). The side silhouette is taller than a length-only sphere suggests, so the screen-box test is the one that catches a marker in the tower. Cap is 20,000 fighters → 200 markers, inside the 500 the Imperial spike already drew.

### 14. Tholian Sentinel — specialty — batch 5

Bible: [`tholian_sentinel — Tholian Sentinel`](cockpit-ship-stage-p0-silhouette-bible.md#tholian_sentinel--tholian-sentinel). Accent `#62f0c8`. Section box. Kit `armor`. Landed in #402 (`0bf683e3`) on the SVG path. 169 faces. Hash `7650706109f94fb1`. Left `fleet-glass-v1`. Pass is #405 (`1b27c879`).

Read, name covered: a fortress. The shortest, bluntest brick. Armor slabs on both flanks make the head-on view nearly square. The nose is a stub. Nothing on the outline suggests speed. No belly tanks and no cabin row as the main shape.

AABB: unusual. Short, and square once the slabs are on. Today's `LOFT` sz reaches 36 on stations from x=22 to x=−44, and the armor slabs sit outside that. Use the sphere of that brick. Leave the Imperial radius (~121) and the Merchant radius (~93) on those hulls. A borrowed capital ring leaves the fortress in a hole. Cap is 2,500 fighters → 25 markers, the Merchant's count on a much smaller body.

### 15. Interdictor Cruiser — specialty — batch 5

Bible: [`interdictor_cruiser — Interdictor Cruiser`](cockpit-ship-stage-p0-silhouette-bible.md#interdictor_cruiser--interdictor-cruiser). Accent `#ff5cab`. Kit `hoop`. Landed in #402 (`0bf683e3`) on the SVG path. 341 faces. Hash `c3d45f327a3c6564`. Left `fleet-glass-v1`. Pass is #405 (`1b27c879`).

Read, name covered: the barge. A heavy body inside two hoops. The hoops are larger than the hull and are the first shape in every camera. Head-on is a ring with a body in the hole. The Star Master's dish stays a plate on a mast.

AABB: unusual, and it is the one hull already measured. The render memo records today's glass at 136×75×75, bounding radius ~108, against the Merchant's 162×32×64 (~93) and the Imperial's 219×51×66 (~121). `fighterSlots` still starts at radius 56, inside that body. The bible hoops grow until they are the first shape, so ~108 is a floor, not the radius to ship. Remeasure after the hoops are larger than the hull. Markers orbit outside the hoops, not in the hole and not on the skin. Cap is 100,000 fighters → 1,000 markers. That count is the stress case the spike only stood in for.

## What this sheet does not decide

P2 FX wiring and the removal of `#viewport`. P3's layout split. A new engine field. Any Ferrengi picture. Copying or tracing EIS, Markham, or ANSI ship art. Sticky order stays the P2 wire product, then P3. Batch 5 is Landed+Pass. The brick Pass does not open the wire. The dish Pass does not open the wire. The guns Pass does not open the wire. The P2 wire gate stays closed until Commander opens it. #405 (`1b27c879`) does not open the wire and does not open the layout. #406 (`1f3b36f9`) records the stills and does not open the wire. #404 (`fe296f55`) is research only and does not replace the product wire. #403 (`ba92e845`) does not open the layout. The P3 gate stays closed. P3 stays behind P2. #393 (`b136f08d`), #394 (`36d75ef8`), #395 (`b4848cdb`), and #396 (`90065381`) do not open the wire and do not open the layout. This sheet does not stamp Pass.

The spike's pass list (gzip budget, legend wording, reduced-motion still, CU still) stays in force for every batch above. Where this sheet names a different pair or a different cap count, that pair and that count are the ones the batch has to show.
