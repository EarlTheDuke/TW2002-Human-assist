# cockpit-warp-variants-v1

COMMANDER NOTE 111. The redesign warp scene plays one of ten pictures for the hull you are flying. No engine change, so no new switch. Helper row 167 was not used. `/bot` is not edited. The pictures stay behind the redesign layout.

## What plays

`web/media/warp-clips.json` lists ten svg rows for every hull, including the escape pod. The id is `<hull>.<style>.01` through `<hull>.<style>.10`. The first row is still `<hull>.streak.01`, so a caller that asks for the first entry gets the same id as before.

Each picture uses the shaded hull from the ship panel (`buildHullFaces` and `cameraFace`). The ten pictures change three things:

- Camera: a side pass, a chase view, head-on toward the viewer, or top-down.
- Stars: streaks, a tunnel of rings, a nebula tint, or a sparse deep field.
- Exit: the original jump, a flash, a fold, a fade, or a gate. NOTE 127 sets each picture between 1.5 and 3 seconds.

The star layer is seeded from the clip id, so the same id always draws the same frame. `web/warp-variants.js` holds that table and the star drawing. It is one script tag on the redesign page. There is no new library and no video file. The manifest and that script are each under 60 KB.

NOTE 146 gives each of those ten pictures its own engine plume. The color and the length sit on the style row (`glow`, `plume`), the star streaks tilt by `streak`, and a flash exit uses `flash` for the burst. The colors are the ship panel's own accents. The plume is drawn by the same mesh as the panel, only when the clip asks for it, so the ship view itself stays put. A real move still picks one id at random and will not play that id twice in a row. Viewport Off, Stills, and Skip are unchanged.

## When it plays

A real move (a warp that changes sector, or an autopilot that finishes at least one hop) picks one id at random for this seat. The next jump for that seat is a different id, including across a run of fifty jumps. The pick stays in the page. It is not sent to the server.

A refused warp and a plotted course do not play a clip. A hull missing from the file still falls back to `warp.out`. When a hull clip does play, `hullPlayed` still stops `warp.out` from starting as well.

`prefers-reduced-motion: reduce` and the viewport Stills mode hold one still frame. Viewport Off stays dark.

On the 1280x720 run the page built a jump in 2.2 ms. Laying out that frame took 0.4 ms. Both are under 16 ms.

## The older warp test

`tests/test_cockpit_warp_ship_clips_v1.py` used to require the played id to be exactly `<hull>.streak.01`, which was the only row. That check now accepts any id for the hull. The call that asks for the first row still expects `<hull>.streak.01`.
