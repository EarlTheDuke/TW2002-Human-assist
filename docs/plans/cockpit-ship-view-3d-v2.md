# cockpit-ship-view-3d-v2

COMMANDER NOTE 94. A 3D-look ship in the redesign cockpit only. No engine change, so no new switch and no helper row. `COCKPIT_LAYOUT` stays legacy unless the page is the redesign. `/bot` (`web/bot.html`, `web/bot.js`, `web/bot-parity.js`) is not edited.

## What was already on the tip

NOTE 77 (`web/redesign.js`, the `shipBody` outline) draws a flat silhouette per hull with one red triangle per fighter up to 200. NOTE 80 plays that same silhouette in the warp scene. Neither is a shaded model. This slice replaces the picture the player sees. The outline function stays as the fallback.

## Why layered SVG, not three.js

Both options in the note were tried against the budget and the panel we already have. A pinned three.js build is about 150 KB gzipped before any hull is added, and it would paint into a second canvas beside `#shipSvg`. The warp scene is an SVG too. A software mesh of a few dozen faces, shaded in the same SVG, is the picture that holds 60 fps on a mid laptop: each frame only rewrites point strings, there is no shader compile and no context to lose, and the gzipped mesh code is a few kilobytes, under the 300 KB ship-view budget. The same `buildHullFaces` / `shipSolidMarkup` path draws the ship that jumps in the NOTE 80 clip.

The shapes are ours. The classic ANSI top and front views are still **UNVERIFIED** and not licensed to trace. Role comes from the public spec tables already cited in `docs/plans/cockpit-ship-view-v1.md`: the Scout is the thin fast hull, the Freighter and the haulers are bulky, the Imperial StarShip is the large armed hull, the Escape Pod is the small lifeboat.

## What the picture does

Each of the 17 hulls is an eight-sided loft plus the parts its role needs (pods, bridge, wings, nacelles, guns, rails, dish, ring, engines). A light from the upper front shades the faces. The group still drifts with `ship-float`. While the page is wide and motion is allowed, the mesh yaws slowly and the red triangles orbit in perspective. Dragging the picture turns it. `prefers-reduced-motion: reduce` stops the drift and the orbit and holds a three-quarter view. A phone (max-width 700px) gets that same still, drawn at 0.72 scale. If `webgl` cannot be created, the panel paints the NOTE 77 outline instead, fighters included, and the stats block is not touched.

Fighter grouping is the NOTE 77 rule: one triangle up to 200, then `ceil(fighters / 200)` fighters per triangle, legend `each triangle = N fighters` only when that scale is above 1. The stat lines under the picture are the same builder as before.

## Where the diff sits

`web/redesign.js` (the mesh, the ship-view paint, and the warp body), `#shipSvg` rules in `web/redesign.css`. The deck grid from NOTE 81 is left alone.
