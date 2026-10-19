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
