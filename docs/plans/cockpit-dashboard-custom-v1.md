# cockpit-dashboard-custom-v1

COMMANDER NOTE 81. The redesign cockpit can be resized, shown, hidden, and rearranged, with a font size and a zoom, saved in this browser. No engine change, so no new switch. `COCKPIT_LAYOUT` stays legacy unless the page is asked for the redesign. `/bot` (`web/bot.html`, `web/bot.js`, `web/bot-parity.js`) is not edited.

## What the original shows

Trade Wars 2002 is a text screen. The command prompt, the sector listing, and the computer menus are one column, not a set of panels. Nothing in the v3 help or the player manual (https://electraphysics.com/documents/tradewarsmanual.pdf) describes a resizable dashboard. A classic client with draggable panels is **UNVERIFIED**. This slice customizes the redesign cockpit we already draw.

## Default

With nothing saved, the deck is the stylesheet grid: `view nav ship` on the first row and `here here term` on the second, gap 8px, columns `1.15fr 1fr 0.95fr`, rows `minmax(0, 1.35fr) minmax(110px, 0.7fr)`. No inline grid template, no font override, zoom 1. Splitters sit in the existing gaps, so the panel boxes are the same pixels as before this slice. Below 1101px the stylesheet's own breakpoints stay in charge. At 390px the deck stays the stacked block list; only show and hide apply there, plus font and zoom.

## What is saved

`localStorage` key `tw2k-deck-v1:<game>:<seat>`. `<game>` is the `/g/<id>` path segment, or `lobby` on the harness. `<seat>` is the seat in the query string. Another seat, or another game, keeps its own layout.

The value is `{v:1, order, hidden, cols, rows, font, zoom}`. `cols` and `rows` are track weights, or null when they are still the default. `font` is null or a pixel size from 12 to 24. `zoom` is 1, or 0.8–1.5 in steps of 0.1. Reset deletes the key and clears the inline styles.

The Layout button sits in the cockpit header, next to Manual, outside every panel. Hiding Viewport, or hiding every panel the menu will allow, still leaves that button on screen. Reset is inside the menu the button opens. From 1367px to 1680px the header gaps draw in so the button stays on the first row and the header stays the same height. A saved font may wrap the header onto a second line; with nothing saved, the header height is unchanged and the deck boxes stay put.

The menu lists the five panels: Viewport, Nav computer, Ship, Here, Subspace log. Each row can be hidden, dragged, or moved with Up and Down. Those moves swap grid slots on a wide screen. Font and zoom are in the same menu. A focused splitter moves with the arrow keys; mouse and touch drag it.

The ship picture and the warp scene stay inside their panels. Hiding Ship or Viewport hides that panel; Reset brings it back.
