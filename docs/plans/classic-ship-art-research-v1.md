# Classic ship art, research only (NOTE 97, CLASSIC SHIP ART)

This note records what the v3.11 sources say about ship pictures, and the
licence status of those pictures. No art is copied into this repository.

## What the sources say exists

The v3.11 shipyard help (`docs/reference/tw2002/eis_tw2002_v3_docs/ShipyardMenu.html`,
the line that begins "Here you can see") tells the player that the shipyard
shows, for ANSI users only, a picture of each ship, both a top view and a
front view, plus the ship's statistics.

The same sentence is in the soft-docs dump
`docs/reference/tw2002/stardock_manuals_and_text_docs/Someguy_TWINSTR.txt`
(the "Here you can see" line near the shipyard section).

The ClassicTW timeline (`docs/reference/tw2002/classictw_timeline.txt`) says
Drew Markham created the ship images and the cinema scenes for TradeWars v2.
Those images belong to the EIS / Gary Martin era of the game. They are not
released under a licence this project can reuse.

## What this repository already has

The cockpit draws its own small SVG outlines in `web/redesign.js`
(`SHIP_ART`). Those outlines were drawn for this project. They are not the
EIS pictures, and they stay.

## What was not done

- No EIS, ANSI, or Drew Markham image was copied, traced, or converted.
- No new image file was added.
- The shipyard screen was not changed to show a picture.

A live TWGS session could confirm whether a current server still sends the
ANSI pictures, and under what terminal setting. That check is queued in
`docs/plans/live-twgs-test-queue-v1.md` only if a later note needs the bytes.
This note does not need them: the decision is to keep our own outlines.
