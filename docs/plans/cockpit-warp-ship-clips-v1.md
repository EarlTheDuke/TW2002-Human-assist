# cockpit-warp-ship-clips-v1

COMMANDER NOTE 80. The redesign warp scene plays a clip for the hull the player is flying. No engine change, so no new switch. `COCKPIT_LAYOUT` stays legacy unless the page is asked for the redesign. `/bot` (`web/bot.html`, `web/bot.js`, `web/bot-parity.js`) is not edited.

## What the original shows

Trade Wars 2002 does not animate a warp. A successful move is a new sector listing in text. The v3 help and the player manual (https://electraphysics.com/documents/tradewarsmanual.pdf) describe ANSI pictures only on the shipyard Examine Ship Specs screen, top and front, drawn by Drew Markham. The museum timeline says the same pass included cinema scenes (https://wiki.classictw.com/index.php/TradeWars_Timeline_Data). Those frames are not in this repo. Whether any cinema frame was a per-hull warp is **UNVERIFIED**. The pictures are copyright Martech / EIS and are not traced here. See `docs/plans/cockpit-ship-view-v1.md` for the licence notes on the ANSI art and the EIS wallpaper.

## What plays today

On this cockpit the warp scene is the viewport. A real move (a warp that changes sector, or an autopilot that completes at least one hop) resolves to the clip `warp.out` in `web/media/manifest.json`. That clip is one generic exterior: the same footage for a cruiser, a gunstar, and the escape pod. A refused warp emits `warp_blocked` and does not use `warp.out`. Plotting a course does not move the ship. Events already in the log at connect are history and do not start a clip.

## What this slice does

`web/media/warp-clips.json` maps each current hull, including `escape_pod`, to a list of clips. The redesign page loads that file and, on a real move only, plays one entry at random for `observation.ship.class`. A hull with an empty list, or a hull that is not in the file, falls back to today's `warp.out`.

Until a filmed clip exists, every hull has one SVG sequence, about 2 seconds: the NOTE 77 silhouette (same `shipBody` as the ship panel) streaks into a star field and shrinks toward the jump. `prefers-reduced-motion: reduce`, and the viewport Stills mode, hold that frame still. Viewport Off stays dark. The sequence is generated in the page. There is no new runtime dependency and no new video file.

The real-move events are still handed to `TW2KMedia.onEvents`. When the hull scene played, that call sets `hullPlayed` so the generic `warp.out` does not start as well. A refused warp and a course plot stay out of the batch.

The diff stays in the redesign viewport (`web/redesign.html`, `web/redesign.js`, `web/redesign.css`) plus the manifest. The deck grid is untouched.

## Adding about 10 filmed clips per hull

Paths are relative to `web/media/`. One hull can list up to about 10 clips. The player already picks one of the list at random, so a new file is only a new object.

```
web/media/clips/warp/<hull>/01.webm
web/media/clips/warp/<hull>/01.mp4
web/media/clips/warp/<hull>/01.webp
```

`<hull>` is the `ShipClass` value (`merchant_cruiser`, `escape_pod`, …). The numbers run `01` through `10`. Append the entry and leave the svg row in the list, or remove the svg row when the filmed set should be the only choice:

```json
{
  "id": "merchant_cruiser.02",
  "kind": "file",
  "webm": "clips/warp/merchant_cruiser/02.webm",
  "mp4": "clips/warp/merchant_cruiser/02.mp4",
  "poster": "clips/warp/merchant_cruiser/02.webp",
  "duration_ms": 2000,
  "bytes": 180000
}
```

Length is 1.8–2.4 seconds, aimed at 2.0. `duration_ms` must match the file. Size budget: webm at or under 250 KB (hard cap 400 KB), poster at or under 80 KB. Ten clips on all 17 hulls at the hard cap is about 68 MB; the 250 KB aim keeps the set near 42 MB. The existing `warp.out` variants are about 175 KB for 3–4 seconds, which is the scale to copy. A missing file, or a hull with no rows, plays `warp.out` (`fallback_clip` in the manifest).

Reduced motion and Stills use `poster` when the chosen row is a file. A file row with no poster holds the SVG still of the current hull instead.

## Generating a clip on the fly

The svg row is that generator: `kind: "svg"` draws the current hull from the NOTE 77 art at the moment of the jump, so a new ship class needs a manifest row and a `SHIPS` entry, not a rendered file. Recording that 2 second sequence to the file names above can be done later without a new library. Calling out to a video model is not part of this slice.

## Where the files are now

The player reads `web/warp-video/<hull>/01.webm` through `10.webm`, not `web/media/clips/warp/`. Names, clip 11, and the live-gen slot (`manifest.json` → `generated.clips`) are in `docs/plans/cockpit-warp-clip-library-v1.md`. A refused warp still does not play.
