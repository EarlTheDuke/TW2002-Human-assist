# Silhouette bible — player hulls (P0)

Parent: [cockpit-ship-stage-p0.md](cockpit-ship-stage-p0.md).

These looks are invented for this cockpit. The classic top-and-front ANSI pair for each hull is **UNVERIFIED** and is not a reference. Do not open, trace, or approximate EIS prints, EIS wallpaper, or Drew Markham ANSI. Role numbers are `SHIP_SPECS_TW2002` and `POD_SPEC` in `src/tw2k/engine/constants.py`. When `ship_roster_live()` is on, `SHIP_ROSTER_LIVE_TABLE` replaces cost, grant holds, hold ceiling, max fighters, turns per warp, and odds. Shields, photons, and mines stay on the base spec. Turns per warp match across the two tables. Where the grant or the fighter cap differs, the entry says so. The picture follows the job (fast, hauler, capital, fortress), not the grant. Accent hexes are the ones already on `SHIPS` in `web/redesign.js`, so the name plate and the hull stay the same colour. Kit names line up with `PARTS` / `detail` in `web/hull-meshes.js` so a later mesh pass can grow those parts instead of inventing a second vocabulary.

The current mesh is the thing this bible replaces as a picture. It is four loft stations, an 8-sided skin, and one small role part. On the Merchant that is 153 faces, an AABB of about 162×32×64, and a bounding radius of about 93. `fighterSlots` starts at radius 56, which is inside that body. Empty shields (`shields / shield_cap < 0.35`) run the hull through the red damage wash in `projectFace`. The attached solid view is that wash on a sausage, with ticks on the hull.

Shared material, every hull:

- Dark blue-grey metal. The accent is a stripe, a canopy edge, and the kit, not a tint that replaces the metal.
- Canopy glass is a cool white mixed with the accent. Box hulls keep a short row of lit ports.
- Idle engines are a short cyan-white cone. A fitted TransWarp drive (`ship.transwarp.fitted`) turns that cone magenta, which the panel already does.
- Shields are the existing glow plus the dashed bubble, sized from `shields / shield_cap`. At zero the bubble is absent, scars may show, and the accent stripe is still the class colour.
- One job-sized part has to read with the name plate covered, at about 140px tall and at a hero crop. Top and head-on cameras in the warp clips have to keep that part. A part that only exists in the three-quarter view is not a signature.

## Fighter markers

One chevron dart, fill `#ff2a2a`, stroke `#ff8888`, the colours the triangles already use. The dart is a marker, not a second ship mesh.

Count, for onboard fighters `n`:

| Bay | Markers |
| --- | --- |
| 0 | 0 |
| 1–100 | 1 |
| 101–200 | 2 |
| 2,500 (Merchant cap) | 25 |
| 50,000 (Imperial cap) | 500 |
| 100,000 (Interdictor cap) | 1,000 |
| Escape Pod, any fighters (cap 50) | 1 |

Formula: `n < 1 → 0`, else `max(1, ceil(n / 100))`. Each marker stands for 100 fighters. The last marker may be a partial hundred. It does not get its own numeral. The stat line keeps the exact bay. The legend is `each marker = 100 fighters`. Corner clusters retire.

The ring sits outside the hull body. Innermost world radius is the bounding sphere of every face, including hoops, wings, dish, and prongs, plus a gap. On the canonical three-quarter view, no marker's screen box intersects the hull silhouette. The Interdictor's ring is outside the hoops. Markers yaw with the hull so they read as escorts. They are not HUD ticks glued to the SVG corners.

A 1,000-marker Interdictor is the stress case. The render memo says how to measure it. The count formula does not get a silent cap.

## Hulls

### escape_pod — Escape Pod

Lifeboat, not sold. 6 turns per warp, 5 holds, 50 fighters, 50 shields, one engine.

A short capsule, almost as tall as it is long, with a single round port on the nose and two stub fins that are large next to the body. One engine. There is no bay, no gun, and no tower, so it cannot be mistaken for a trader that has been scaled down. The fins are the silhouette from the side. The round port is the silhouette head-on.

Accent `#55ffff`. Kit: `fins`. Metal stays dark. The port glass carries the cyan.

### merchant_cruiser — Merchant Cruiser

Starter trader. 3 turns per warp, 20 holds (yard cap 75), 2,500 fighters, 400 shields, two engines. Spike hull.

A medium arrow. Blunt wedge nose, canopy just aft of the nose, a keel deep enough to break the underside in a side camera, and two shoulder pods that say cargo without turning the ship into a barge. Length is ordinary. The keel and the pods are the tell: a trader with a belly and a bit of fight, not a needle and not a capital. At zero shields the blue stripe is still blue.

Accent `#7aa2ff`. Kit: `keel`, plus `pods` and `bridge` from the detail string. This is the hull the attached screenshot has to stop resembling.

### scout_marauder — Scout Marauder

Fast thin trader. 2 turns per warp, hold ceiling 25, 100 shields, no mines, no genesis. The base table caps fighters at 150. The live roster caps them at 250. Either way the escort cloud is a few markers. Two engines.

The longest, thinnest hull in the fleet. Canards near the nose, small fins at the tail, almost no beam. A top view is a line with two small blades. It has no pods and no keel deep enough to read as cargo. The speed is the length-to-beam, not a glow effect.

Accent `#5dffc8`. Kit: `canards`.

### missile_frigate — Missile Frigate

Photon boat. 3 turns per warp, 5,000 fighters, 400 shields, up to 10 photons. The live roster grants 12 holds against a ceiling of 60. Two engines.

A slim hull whose silhouette is two long dorsal missiles and a rail, noses forward, clearly proud of the fuselage. The missiles are larger than the canopy. No other hull wears a dorsal missile pair. Cheek gun barrels on the Imperial are a different kit and stay smaller than these bodies.

Accent `#ffb15a`. Kit: `missiles`, plus `rails`. The missile noses are a hotter amber than the hull stripe.

### battleship — BattleShip

Gun platform. 4 turns per warp, hold ceiling 80, 10,000 fighters, 750 shields, offensive odds 1.6, no photons. Three engines.

A wide hex wedge, short for its beam. Two turrets stand high enough that their barrels break the top edge from the side and from above. It is broader than the Merchant and shorter than the Imperial. The turrets, not the length, are the job.

Accent `#c5c8ff`. Section: hex. Kit: `turrets`.

### corporate_flagship — Corporate FlagShip

Corp capital. 3 turns per warp, hold ceiling 85, 20,000 fighters, 1,500 shields, TransWarp hull. Three engines.

A liner with a tower amidships taller than the hull is deep. Side view reads as a hull with a block standing on it. The tower is a stepped command block, not the Imperial castle and not a mast. Head-on, the tower is a rectangle on the centerline, with no X of engines and no hoop.

Accent `#ff77ff`. Kit: `tower`. TransWarp, when fitted, is magenta in the engines only. The tower stays the magenta accent, not a second glow source.

### colonial_transport — Colonial Transport

Slow colonist ship. 6 turns per warp, 50 holds (yard cap 250), 200 fighters, odds 0.6. Two engines.

A fat box, tall for its length, with two belly tanks and a row of cabin ports along the flank. No gun breaks the outline. It should look unwilling to turn. Distinct from the CargoTran, which is long and flat, and from the Freighter, which is short and wide.

Accent `#7dff7d`. Section: box. Kit: `cargo` (the belly tanks). Port glass is a warm white so the green stripe stays the accent.

### cargotran — CargoTran

Bulk hauler. 4 turns per warp, hold ceiling 125, 400 fighters, 1,000 shields. Two engines.

A long flat deck. A cargo spine runs the full length and stands proud of the deck, so the side view is a low hull with a girder on its back. Flatter than the Colonial, longer than the Freighter, no passenger ports as the main tell.

Accent `#ffe566`. Section: box. Kit: `spine`.

### merchant_freighter — Merchant Freighter

Fast freighter. 2 turns per warp, hold ceiling 65, 300 fighters. Two engines.

Short and very wide. Cheek tanks make the head-on view a broad face, almost as wide as it is long. Two large engines for the speed, cheeks for the cargo. No spine, no tall box, no keel as deep as the Merchant's.

Accent `#7af0ff`. Kit: `cheeks`.

### imperial_starship — Imperial StarShip

The capital. 4 turns per warp, hold ceiling 150, 50,000 fighters, 2,000 shields, up to 5 photons, TransWarp, alignment-gated, unique. Four engines. Spike hull.

The longest hull in the fleet. A stepped castle on the spine, four engine bells in a square, a ventral keel, and two forward barrels that stay smaller than the Frigate's missiles. The castle reads as a keep, not the corporate tower: it is longer than it is tall, with a second step near the nose. Head-on, the four bells make a square. Top view, the castle's step is the bright accent mass. Gold stays on the castle and the stripe. At zero shields that gold is still gold.

Accent `#ffe9a0`. Kit: `castle`, plus `nacelles` for the four bells. 500 markers orbit outside the bells and the castle.

### havoc_gunstar — Havoc GunStar

Shield tank and gunship. 3 turns per warp, hold ceiling 50, 10,000 fighters, 3,000 shields, TransWarp. Three engines.

A short body with a split prow. Two prongs run ahead of the nose and are the silhouette from the side, the top, and head-on, where they are two bright tips with a gap between them. No turret pair, so it is not the BattleShip. The prongs are the guns.

Accent `#ff8844`. Section: hex. Kit: `prongs`.

### star_master — Star Master

Mid combat hull. 3 turns per warp, hold ceiling 73, 5,000 fighters, 2,000 shields. Two engines.

A modest arrow with a mast and a dish wider than the beam. The top view has a circle on a stick. That circle is a plate, not a hoop around the body, so it cannot be read as the Interdictor. The dish is the whole job.

Accent `#9ad7ff`. Kit: `mast` and `dish`.

### constellation — Constellation

Mid combat hull. 3 turns per warp, 20 holds (yard cap 80), 5,000 fighters, 750 shields. Four engines. The panel name stays Constellation.

A slim body with four nacelles in an X. Head-on is that X and little else. No castle, no dish, no prongs. The X is the tell in every camera that can see the tail.

Accent `#d0d6ff`. Kit: `quad`.

### tkhasi_orion — T'Khasi Orion

Alien fast hull. 2 turns per warp, hold ceiling 60, 750 fighters, 750 shields. Two engines.

Swept plates that leave the nose and run back past the tail, so the planform is a crescent. Not a Fed wedge, not a needle with canards, not a box. No keel and no tower. The crescent, unbroken by a dorsal gadget, is the alien tell.

Accent `#ff6d8a`. Kit: `swept`.

### tholian_sentinel — Tholian Sentinel

Fortress. 4 turns per warp, 10 holds (yard cap 50), 2,500 fighters, 4,000 shields. Two engines.

The shortest, bluntest brick. Armor slabs on both flanks make the head-on view nearly square. The nose is a stub. Nothing on the outline suggests speed. Distinct from the Colonial box because it is short and plated, with no belly tanks and no cabin row as the main shape.

Accent `#62f0c8`. Section: box. Kit: `armor`.

### taurean_mule — Taurean Mule

Alien hauler. 4 turns per warp, hold ceiling 150, 300 fighters, odds 0.5. Two engines.

A saddle: a low hull, a raised cargo pack on the back, and two rear panniers. It should read as a beast of burden. Not a Fed box, not a spine barge, not a crescent. The pack's hump is the side silhouette.

Accent `#d7b48a`. Section: box. Kit: `saddle`. The panniers take the accent. The pack is darker metal.

### interdictor_cruiser — Interdictor Cruiser

The barge. 15 turns per warp, hold ceiling 40, 100,000 fighters, 4,000 shields, up to 200 mines. Four engines.

A heavy body inside two hoops. The hoops are larger than the hull and are the first shape in every camera. Head-on is a ring with a body in the hole. Nothing else wears a hoop. The Star Master's dish is a plate on a mast and must stay that way. Fighter markers orbit outside the hoops, not in the hole and not on the skin. A full bay is 1,000 markers.

Accent `#ff5cab`. Kit: `hoop`.

## Read test, applied to the set

Cover the name plate. These pairs have to stay apart at hero size and at 140px:

| Pair | What keeps them apart |
| --- | --- |
| Merchant / Imperial | Keel and shoulder pods versus a long stepped castle and four bells. |
| Merchant / Freighter | Deep keel versus wide cheeks and a short body. |
| Scout / T'Khasi | Needle and canards versus a crescent. |
| Colonial / CargoTran / Mule | Tall cabin box versus long spine versus saddle hump. |
| BattleShip / Havoc | Turrets on a wedge versus a split prow. |
| FlagShip / Imperial / Star Master | Tall tower versus long castle versus a dish. |
| Constellation / Interdictor | An X of engines versus two hoops. |
| Escape Pod / Scout | A finned capsule versus a long needle. |

## P1b wave — next four after the spike

The one-paragraph entries above stay the picture for all 17 hulls. The mesh contract for the next four, after Merchant Cruiser and Imperial StarShip, is [cockpit-ship-stage-p1b-next-hulls.md](cockpit-ship-stage-p1b-next-hulls.md).

| Key | Panel name | Job the mesh has to show |
| --- | --- | --- |
| `scout_marauder` | Scout Marauder | Fast needle. Canards. |
| `merchant_freighter` | Merchant Freighter | Wide fast trader. Cheeks. |
| `battleship` | BattleShip | Gun platform. Hex wedge, turret pair. |
| `corporate_flagship` | Corporate FlagShip | Corp liner. Stepped tower. |

There is no Destroyer class on `SHIP_SPECS_TW2002` or `ShipClass`. BattleShip is that gun platform. The freighter is the day-one trader out of the starter (trading index 325, 2 turns per warp, cheaper than the cruiser). Colonial Transport scores higher (417) and waits. CargoTran waits with it. Each P1b entry has the role read, the silhouette, the accent, and the canonical three-quarter plus head-on checklist for the 100:1 marker ring.

Implement those four after the Merchant and Imperial spike merges and passes the render memo. This wave does not start product code.
