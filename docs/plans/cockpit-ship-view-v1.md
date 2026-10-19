# cockpit-ship-view-v1

COMMANDER NOTE 77. Research first, then a ship view on the redesign cockpit only. No engine change, so no new switch. `COCKPIT_LAYOUT` stays legacy unless the page is asked for the redesign. `/bot` (`web/bot.html`, `web/bot.js`, `web/bot-parity.js`) is not edited.

## What the original shows

Trade Wars 2002 is a text game. The ship you are flying is a column of numbers, not a picture, on the command screen. The pictures live in one place: the Federation Shipyards, **Examine Ship Specs**. The v3 help says that screen is the same specification list as the on-board computer, and that it "includes (for ANSI users only) a picture of each ship, both top and front view."

- Local copy: `docs/reference/tw2002/eis_tw2002_v3_docs/ShipyardMenu.html` (EIS v3 help, classictw.com/2002v3Docs).
- Same sentence in `docs/reference/tw2002/stardock_manuals_and_text_docs/Someguy_TWINSTR.txt` and `Gypsy_Big_Dummies_Guide.html`.
- The player manual repeats it: https://electraphysics.com/documents/tradewarsmanual.pdf (copyright 1990–2000 Epic Interactive Strategy; Gary Martin, Mary Ann Martin, John Pritchett). With ANSI off, the game substitutes text.
- Public spec sheets are tables, not drawings. The Bible chart (https://www.thestardock.com/files/manuals/Trade_Wars_2002_Bible.htm) and `docs/playtests/ships/SHIP_ROSTER.md` list price, holds, fighters, shields, turns per warp, and odds. A captured text block for the Merchant Cruiser is at http://burrowowl.net/2009/11/ships_you_dont_want_in_tradewars_2002/ — still numbers, no silhouette.
- The ANSI files for v2 are indexed by the TradeWars Museum (http://wiki.classictw.com/index.php/TradeWars_2002_v2_ANSI_Files) but are not in this repo. The museum timeline says Gary Martin asked Drew Markham to draw the ANSI ship images and the cinema scenes during v2 (https://wiki.classictw.com/index.php/TradeWars_Timeline_Data). MobyGames credits Markham for the ANSI art (https://www.mobygames.com/game/3340/trade-wars-2002/). The per-hull pixel shapes are not reprinted in any file we have. **UNVERIFIED** against the actual ANSI screens.

Role, from those public tables, is what we can confirm: the Scout Marauder is the small fast hull, the Colonial Transport and CargoTran are the bulky haulers, the BattleShip and Imperial StarShip are the heavy hulls, the Havoc GunStar is the gunship, the Interdictor is the slow heavy fighter barge, and the Escape Pod is the lifeboat (not sold; `POD_SPEC` in `src/tw2k/engine/constants.py`). Colour, exact outline, and the top-versus-front pair for each hull are **UNVERIFIED**.

## Licence

The ANSI pictures are not free to copy. Trade Wars 2002 for DOS is copyright Martech Software; EIS has owned the game since 2000 (`docs/reference/tw2002/library_notes.md`). The v3 help pages are marked EIS. The Classic Series prints on http://eisonline.classictw.com/store/prints/ are "design elements drawn from the original ANSI graphics," sold by EIS, including a fleet banner of the classic ships and separate sheets for the T'Khasi Orion and the Colonial Transport. The EIS wallpaper set (https://eisonline.classictw.com/store/wallpaper/) is Creative Commons Attribution-NonCommercial-NoDerivs 3.0: display and distribute with credit, no modifications, no use in a new design. That is not a licence to trace the ships into this cockpit.

## What we draw, and why

Our own SVG, one outline per hull in the current `ShipClass` roster plus the Escape Pod. No new runtime dependency. The shapes follow the public role (small scout, split-prow gunship, wide hauler, blunt sentinel, capsule pod) and are not tracings of the Markham ANSI or the EIS prints. A top face, a darker underside, a bridge, and engine glow are there so the hull reads as a solid ship in space rather than a flat icon. Engine glow turns magenta when the observation says a TransWarp drive is fitted. A dashed cyan bubble appears only while shields are above zero. Neither of those adds a line to the stat block.

The roster drawn here is the 16 keys on `ShipClass` plus `escape_pod`: Merchant Cruiser, Scout Marauder, Missile Frigate, BattleShip, Corporate FlagShip, Colonial Transport, CargoTran, Merchant Freighter, Havoc GunStar, Imperial StarShip, Star Master, Constellation, T'Khasi Orion, Tholian Sentinel, Taurean Mule, Interdictor Cruiser, Escape Pod. Names already on the panel are unchanged, including BattleShip, Corporate FlagShip, CargoTran, Havoc GunStar, and Imperial StarShip.

## Fighters

The old panel painted at most 48 red marks from a log of the fighter count, plus 12 pips for how full the bay was. That is not the count. This view paints one small red triangle per fighter, up to 200. Above 200 the triangles are grouped: the scale is the smallest whole number such that the triangle count is at most 200 (`ceil(fighters / 200)`), and the number of triangles is `ceil(fighters / scale)`. Two thousand fighters are 200 triangles at "each triangle = 10 fighters". The legend is that sentence, and it is shown only when the scale is above 1. The stat line keeps the exact number, same words and order as before: Fighters, Shields, Holds, armid mines, limpet mines, Cloaks, Disruptors, then the tow line, then whatever gear is actually aboard.

The picture is redrawn from the observation whenever the cockpit refreshes, so a fighter buy, a loss, or a new hull shows up on the next paint. The hull group floats. `prefers-reduced-motion: reduce` sets that animation to none. The drawing stays inside the ship panel, including at 390 px wide.

## Where the diff sits

`#ship` in `web/redesign.html`, the ship-view functions in `web/redesign.js`, and the `#shipSvg` rules in `web/redesign.css`. The deck grid is left for NOTE 81. The I-key "Ship information" text is the same list it was.

# NOTE 116 — cockpit-ship-view-plan-v1

COMMANDER NOTE 116. Research, then a plan, plus a small prototype on the redesign cockpit only. No engine change, so no new switch and no helper row. `COCKPIT_LAYOUT` stays legacy unless the page is the redesign. `/bot` (`web/bot.html`, `web/bot.js`, `web/bot-parity.js`) is not edited. The NOTE 77 record above is unchanged in meaning: this section is the later plan Ben asked for.

PR #48 (NOTE 113, custom layout) is still open, so this slice does not edit `web/layout.js`, `web/redesign.html`, or `web/redesign.css`. The prototype stylesheet is `web/ship-view-plan.css`, attached from `web/redesign.js`.

## What Ben asked for

Keep the stat lines that are already easy to read. Add a ship picture that is visually striking, one for each hull. The picture may be the original Trade Wars 2002 ship art, or our own ship floating in space. Red triangles around the hull must match the fighter count: one triangle per fighter up to a cap, then neat clusters that print a count when the bay is large. The warp clips from NOTE 111 should later use the same art.

## Options

1. **Copy or trace the original ANSI pictures.** The shipyard help says ANSI users see a top view and a front view of each hull. `docs/plans/classic-ship-art-research-v1.md` records the licence. Drew Markham drew those images and the cinema scenes for EIS / Gary Martin. They are not released under a licence this project can reuse. The EIS wallpaper set is Creative Commons Attribution-NonCommercial-NoDerivs 3.0: display and distribute with credit, no modifications, and no use in a new design. That is not a licence to trace the ships into this cockpit. The Classic Series prints are sold by EIS. This option is closed.

2. **Keep our own shaded meshes, and group the fighters into counted clusters.** NOTE 77 drew an outline per hull. NOTE 94 replaced the picture the player sees with a lofted mesh in the same SVG (`LOFT` and `buildHullFaces` in `web/redesign.js`), one red triangle per fighter up to 200, then a single legend `each triangle = N fighters`. The stat block was not touched. This option keeps that mesh and that legend, and on the prototype hulls packs the scaled triangles into at most four clusters, one in each corner of the picture, so the counts stay readable when the panel is short. Each cluster prints the number of fighters it stands for. The counts add up to the real fighter total. Under the cap there is still one triangle per fighter and no cluster label.

3. **A full WebGL scene (three.js or similar).** NOTE 94 measured this and left it. A pinned three.js build is about 150 KB gzipped before any hull is added, it would paint a second canvas beside `#shipSvg`, and the warp scene is already an SVG that shares `shipSolidMarkup`. The mesh code stays a few kilobytes, under the 300 KB ship-view budget. A second renderer would also make the later warp-clip match harder.

## Recommendation

Option 2. The art is the geometry already in `web/redesign.js` (`SHIPS`, `HULL_NORM`, `LOFT`), drawn for this project from the public role of each hull (small scout, bulky hauler, lifeboat). It is not a tracing of the Markham ANSI or the EIS prints. Colour and the classic outline of each hull stay **UNVERIFIED**.

The prototype paints three hulls this way: Merchant Cruiser, Scout Marauder, and Escape Pod. The other hulls keep the NOTE 77 rings and the NOTE 94 mesh until a follow-up extends the clusters. The readable stat lines stay the same words and order: Fighters, Shields, Holds, armid mines, limpet mines, Cloaks, Disruptors, then the tow line.

The NOTE 77 legend stays, including on a clustered hull, so the older ship-view tests still see `each triangle = N fighters`. The cluster counts are the extra line Ben asked for. A later note can drop the single legend once every hull uses clusters.

## Art source and licence

- **Source:** original SVG geometry in `web/redesign.js`. No image file was added. No EIS, ANSI, or Drew Markham picture was copied, traced, or converted.
- **Licence:** our own work, the same decision recorded in `docs/plans/classic-ship-art-research-v1.md` and in the NOTE 77 licence section above.
- **Not used:** Martech / EIS copyright in the ANSI ship images; EIS wallpaper CC BY-NC-ND 3.0 (no derivatives, no new design).

## Warp clips

NOTE 111 (`web/warp-variants.js`, `web/media/warp-clips.json`, the warp block in `web/redesign.js`) already paints the warp body with `shipSolidMarkup` when the solid mesh is on. Those clips are on PR #43, which is not merged here, and this note does not edit them. When that work is on the tip, the clips should keep using this same mesh so the ship in the warp matches the ship in the panel. They should not switch to the ANSI pictures.

## Where this diff sits

`web/redesign.js` (cluster packing on the three hulls, and a stylesheet tag) and `web/ship-view-plan.css`. The layout files from NOTE 113 are left alone.

# NOTE 118 — ship-view-all-hulls-v1

COMMANDER NOTE 118. The NOTE 116 picture now covers every hull in `ShipClass`, including the Escape Pod. No engine change, so no new switch and no helper row. `COCKPIT_LAYOUT` stays legacy unless the page is the redesign. `/bot` is not edited. No EIS, ANSI, or Drew Markham picture is copied or traced. The meshes stay the ones in `LOFT` / `buildHullFaces`.

Above 200 fighters, every hull packs the same triangles into at most four corner clusters and prints the fighter count on each cluster. The counts add up to the bay. The stat lines and the legend `each triangle = N fighters` stay as they were. Under the cap there is still one triangle per fighter and no cluster label.

The ship panel from NOTE 113 can be hidden, shown, and resized (the map can be made larger, and the column splitter can move). While the panel is hidden the clusters keep their last places. When it is on screen again, or when the panel changes size, they sit in the corners of the picture, inside the drawing, and they do not pile up on the hull. On a wide deck the column stays wide enough to read the legend and the four counts, so enlarging the map and moving the splitter does not crush the picture into a one-letter strip.

A warp clip from NOTE 111 paints the hull that is flying, with `buildHullFaces` — the same mesh as the ship panel. The camera still comes from the clip. The clip does not switch to the ANSI pictures.
