# cockpit-warp-clip-library-v1

Ten short warp pictures for every flyable hull, including the escape pod. A real move plays one at random for the hull you are flying. The picture is that hull's cockpit mesh (`web/hull-meshes.js`), not a generic ship and not licensed Trade Wars art.

NOTE 80, NOTE 111, and NOTE 146 already listed ten procedural pictures per hull. NOTE 135 recorded them, but the files that played were 400×260 at 10 fps, and the recorder never passed the plume color or the camera move. The cockpit prefers that file on a real move, so the jump looked thin. This slice keeps the same ten ids and re-records them at 800×520, 16 fps, with the plume, the camera, and a starfield in that clip's own color.

`/bot` is not edited. `mode=cu` still defaults to a still in `#cuMediaSlot`. The redesign viewport is the only page that plays these files.

## What plays

`web/media/warp-clips.json` lists the ten ids for each `ShipClass`. The redesign page loads that file and, on a real move only, picks one id for `observation.ship.class`. The next jump for that seat is a different id. The pick stays in the page.

A real move is a self `warp` whose sector changes, or a self `autopilot` that finishes at least one hop. A refused warp, a plotted course, a cancelled move, and events already in the log at connect do not play a clip. Viewport Off stays dark. Stills and `prefers-reduced-motion: reduce` hold one SVG frame and do not start the video.

`web/warp-video.js` resolves the chosen id to a file only when `chosen.playback === "move"`. A paint probe leaves playback unset, so the live SVG stays. When the file plays, `hullPlayed` still stops the generic `warp.out` from starting as well. A hull with no rows falls back to `warp.out`.

## Files

Paths under `web/warp-video/` are served as `/static/warp-video/...`.

```
web/media/warp-clips.json                 which ids each hull can roll
web/warp-variants.js                      camera, stars, plume, duration
web/warp-video/<hull>/01.webm … 10.webm   captured picture of that scene
web/warp-video/manifest.json              bytes, duration, and the live-gen slot
web/warp-video/generated/<hull>/NN.webm   drop a generated file here (optional)
```

`<hull>` is the `ShipClass` value (`merchant_cruiser`, `escape_pod`, …). The id is `<hull>.<style>.NN` with `NN` from `01` to `10`. The first id is still `<hull>.streak.01`.

Each captured file is silent VP9, 800×520, 16 fps, 1.5–3.0 seconds, at or under 300 KB. Only the clip that was picked is fetched. The other hulls stay on disk.

Record again with:

```
PYTHONPATH=src python scripts/render_warp_videos.py
PYTHONPATH=src python scripts/render_warp_videos.py --only merchant_cruiser:03
```

The stage is `scripts/warp_video_stage.html`. It paints the same mesh and the same style row the cockpit uses.

## Adding clip 11

The roll is the list in `web/media/warp-clips.json`. An eleventh row is another pick. Two ways to add one:

**A procedural picture.** Append a style in `web/warp-variants.js` (`n`, `style`, `camera`, `stars`, `exit`, `yaw`, `pitch`, `fit`, `duration_ms`, `glow`, `plume`, `streak`, `flash`). Append a matching row on each hull you want in `web/media/warp-clips.json`, id `<hull>.<style>.11`, `kind` `"svg"`. Then record it:

```
PYTHONPATH=src python scripts/render_warp_videos.py --only merchant_cruiser:11
```

**A file only, for one hull.** Append a row and do not add a style. The picker will offer it. Point `webm` at a path the player can fetch. A path under `web/media/` is relative (`clips/warp/merchant_cruiser/11.webm` becomes `/static/media/clips/warp/merchant_cruiser/11.webm`). A path that starts with `/` or `http` is used as written.

```json
{
  "id": "merchant_cruiser.live.11",
  "kind": "file",
  "duration_ms": 2000,
  "webm": "/static/warp-video/generated/merchant_cruiser/11.webm",
  "poster": "/static/warp-video/generated/merchant_cruiser/11.webp"
}
```

`duration_ms` should match the file. Keep it between 1.5 and 3 seconds. A poster is what Stills would use when the row is a file; without one, Stills holds the SVG of the current hull.

## Live-generated video

Do not replace `window.TW2KWarpClipSource` unless the new function delegates to the previous one. The built-in resolver already prefers a generated file over the capture.

`web/warp-video/manifest.json` → `generated.clips` is the drop slot. A row with a non-empty `webm` replaces the captured file for that **existing** id. It does not add an eleventh roll by itself. An empty `webm` is ignored.

```json
{
  "id": "merchant_cruiser.streak.01",
  "webm": "generated/merchant_cruiser/01.webm",
  "poster": "generated/merchant_cruiser/01.webp",
  "duration_ms": 2000
}
```

Paths are relative to `/static/warp-video/` unless they start with `/` or `http`. The cockpit calls `resolve(chosen)` once per play. `chosen` is `{id, hull, kind, duration_ms, webm, mp4, poster, playback}`. Return `null` to keep the procedural picture. Return `{kind: "file", webm, mp4, poster, duration_ms}` to play that file instead. Return `null` when `playback` is not `"move"`, so a paint or a still does not start a video.

A generator can also assign the hook directly:

```js
var previous = window.TW2KWarpClipSource;
window.TW2KWarpClipSource = {
  ready: previous && previous.ready,
  catalog: previous && previous.catalog,
  resolve(chosen) {
    if (!chosen || chosen.playback !== "move") return null;
    var clip = lookupLiveClip(chosen.hull, chosen.id); // your cache
    if (clip) return { kind: "file", webm: clip.webm, poster: clip.poster, duration_ms: clip.duration_ms };
    return previous && previous.resolve ? previous.resolve(chosen) : null;
  }
};
```

Gameplay never waits on a generator. If the file 404s, the player drops back to the procedural SVG for that jump.
