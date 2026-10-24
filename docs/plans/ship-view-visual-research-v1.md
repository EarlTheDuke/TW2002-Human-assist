# Ship view visual research (fleet glass)

Research for a cockpit ship picture that is easier to look at than the NOTE 77 / 94 / 116 / 118 / 126 passes, without throwing away the stat block those passes already got right. No engine change. `/bot` is not part of this pass. No EIS, ANSI, or Drew Markham picture is copied, traced, or converted.

Builds on:

- `docs/plans/cockpit-ship-view-v1.md` (NOTE 77, 116, 118, 126)
- `docs/plans/cockpit-ship-view-3d-v2.md` (NOTE 94)
- `docs/plans/classic-ship-art-research-v1.md` (NOTE 97)
- `docs/plans/2026-09-29-cockpit-design.md` (the numbers stay readable; the picture is the ship)
- `docs/playtests/ships/SHIP_ROSTER.md` (public role and caps)

## What the original looks like

Trade Wars 2002 on the command screen is a column of numbers. Sector, port letters, holds, fighters, shields, turns, credits. The picture is not there. The v3 help and the player notes put the pictures in one place: Federation Shipyards, **Examine Ship Specs**. That screen is the on-board computer list, and for ANSI users it adds a picture of each ship, top view and front view.

Local copy of that sentence: `docs/reference/tw2002/stardock_manuals_and_text_docs/Someguy_TWINSTR.txt` (the `<E> Examine Ship Specs` lines). The same claim is recorded in `docs/plans/cockpit-ship-view-v1.md` from the EIS v3 help (`ShipyardMenu.html`) and the player manual. With ANSI off, the game substitutes text.

The pictures themselves are not in this repo. The museum page `docs/reference/tw2002/classictw_museum_wiki/Application_TradeWars_2002_v1.html` names Drew Markham (Videon) next to the v1 ANSI files. NOTE 77 and NOTE 97 already record the timeline claim that Markham drew the ship images and the cinema scenes for v2, and the MobyGames credit. The per-hull pixel outlines are still **UNVERIFIED** here. This pass did not pull those files, and it does not need them.

What the public tables do confirm is role, not outline. From `docs/playtests/ships/SHIP_ROSTER.md` and the caps already cited in NOTE 77:

| Hull | Role the numbers support | Shape language we invented |
| --- | --- | --- |
| Merchant Cruiser | Starter. Balanced holds, fighters, shields. | Arrow fuselage, side tanks, cockpit. |
| Scout Marauder | Fast (2 turns per warp), small bay, thin trader. | Long needle, canards, small aft fins. |
| Missile Frigate | Photon boat. | Rails and dorsal missiles. |
| BattleShip | Heavy gun platform, wide combat odds. | Broad wedge, two turrets. |
| Corporate FlagShip | Corp capital, huge bay, TransWarp hull. | Tall bridge tower. |
| Colonial Transport | Slow hauler (6 turns per warp), colonist ship. | Fat box, belly tanks. |
| CargoTran | Bulk hauler, long and shielded. | Long deck, cargo spine. |
| Merchant Freighter | Fast freighter (2 turns per warp). | Short, very wide cheeks. |
| Havoc GunStar | Shield tank, TransWarp, gunship. | Split prow. |
| Imperial StarShip | The capital. 50,000 fighters, photons, TransWarp. | Long hull, castle, four bells. |
| Star Master | Mid combat hull. | Mast and dish. |
| Constellation | Mid combat hull. Chart spelling is Constilation. | Four nacelles in an X. |
| T'Khasi Orion | Alien fast hull (2 turns per warp). | Swept plates, not a Fed wedge. |
| Tholian Sentinel | Fortress. 4,000 shields, blunt defender. | Short armored brick. |
| Taurean Mule | Alien hauler, low odds, large holds. | Saddle tanks. |
| Interdictor Cruiser | The barge. 15 turns per warp, 100,000 fighters. | Double ring around a heavy body. |
| Escape Pod | Lifeboat. Not sold. | Capsule and fins. Not a speck. |

Ferrengi hulls are on the chart and are not player `ShipClass` values. They are out of this picture.

The theme around those pictures, from the game we can actually read, is a 16-color ANSI terminal: black field, cyan, green, yellow, magenta, red, white. The shipyard picture is a technical top-and-front pair above a wall of statistics. It is not a film frame. Players remember the silhouette and the numbers together. Colour, exact outline, and the top-versus-front pair for each hull stay **UNVERIFIED**.

## Licence

Closed, same as NOTE 77 and NOTE 97.

- Trade Wars 2002 for DOS is copyright Martech. EIS has owned the game since 2000. The ANSI ship images and the cinema scenes are not released under a licence this project can reuse.
- The EIS wallpaper set is Creative Commons Attribution-NonCommercial-NoDerivs 3.0: display and distribute with credit, no modifications, no use in a new design. That is not a licence to trace ships into this cockpit.
- The Classic Series prints are sold by EIS, including sheets that use the original ANSI design language (a fleet banner, the T'Khasi Orion, the Colonial Transport). Not used.

No ANSI file, print, wallpaper, or screenshot was copied, traced, or converted for this pass.

## Recommendation

**B. Our own look.** Not option A.

Option A would be theme-inspired art that still traces the Markham top and front views. We do not have a licence, we do not have the pixels in tree, and the outlines are unverified. A "close enough" trace is still a copy. A is closed.

Option B is the geometry this project already owns (`web/hull-meshes.js`, drawn for these pages), pushed harder so each hull reads at the size the ship panel actually is (about 140 CSS pixels tall on a desktop deck). The inspiration we are allowed to use is the public role table and the terminal palette, not the rasters.

Why not a new three.js scene: NOTE 94 measured it. A pinned three.js build is about 150 KB gzipped before any hull, it would paint a second canvas beside `#shipSvg`, and the warp clips share `buildHullFaces`. The ship-view budget stays a software mesh in the same SVG. This pass spends that budget on contrast, silhouette, and the space behind the hull.

## What "fleet glass" means

The picture is still the shared mesh. `window.TW2KHullMeshes.version` stays `ship-view-full-v1` so the warp clip and the panel keep one face list.

- Each class keeps its own loft. Cross-section is round (liners and needles), hex (warships), or box (haulers and the Tholian brick), so two hulls do not share a sausage.
- Role parts are large enough to survive the small panel: plates for wings (a lofted wing reads as another sausage), a washer ring for the Interdictor, prongs, turrets, a tower, a dish, belly tanks.
- A light from the upper front, a cool fill, and a rim on the silhouette. Engine cones are emissive and pulse while the hull is turning. TransWarp still shifts that glow to magenta.
- A dorsal stripe in the hull accent, a glass canopy where the class has a bridge, lit ports on the box hulls.
- Two star layers, a nebula, and a crescent, parallax with the yaw. The group still bobs (`ship-float`). Drag still yaws. Pause still freezes. `prefers-reduced-motion: reduce` and a phone still hold the three-quarter view.
- Shields stay a glow plus the dashed bubble, sized from `shields / shield_cap`. Under 35% the hull still takes the low-shield look.
- The name and class stay on the plate. A third line appears only when a loadout is actually fitted (TransWarp, scanner, photons, genesis, cloaks), so an empty ship does not grow a blank row.
- The stat lines under the picture stay in the same order: Fighters, Shields, Holds, armid mines, limpet mines, Cloaks, Disruptors, then the tow line. A TransWarp row is added after that tow line when a drive is fitted. Cargo holds stay in their own row.

The picture is redrawn from the observation whenever the cockpit refreshes. Hull, fighter count, shields, TransWarp, a fitted scanner, and photons on board are part of that paint, so a buy or a loss shows up on the next refresh. Hiding, showing, and resizing the ship panel still works. The layout store is untouched.

## Fighter triangles

Unchanged math from NOTE 77 / NOTE 118. The count on the stat line is the real bay. The picture matches it.

- Up to 200 fighters: one red triangle each. No cluster label. The line under the picture says "One red triangle is one fighter."
- Above 200: `scale = ceil(fighters / 200)`, `triangles = ceil(fighters / scale)`. 2,000 fighters are 200 triangles at "each triangle = 10 fighters". The legend text stays that sentence.
- Those triangles pack into at most four corner clusters (fewer if there are fewer triangles than four). The triangles are split as evenly as the count allows. The last triangle carries the remainder `fighters - scale * (triangles - 1)` when the scale does not divide the bay. Each cluster prints the fighters its triangles stand for. The four numbers add up to the real total.
- The panel states that rule on the fighter line, next to the legend: "Counts add to the bay." The four corner numbers are the clusters. The full formula (scale, triangle count, at most four corners) is the tooltip on that line and `data-cluster-rule` on `#shipSvg`.

## Where the diff sits

`docs/plans/ship-view-visual-research-v1.md`, `web/hull-meshes.js`, the ship-view paint in `web/redesign.js`, `#shipSvg` rules in `web/redesign.css` and `web/ship-view-plan.css`. Warp clips keep calling the same `buildHullFaces`. `/bot` is not edited.
