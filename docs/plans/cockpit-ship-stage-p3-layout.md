# P3 layout — ship stage beside the nav map

Parent: [cockpit-ship-stage-p0.md](cockpit-ship-stage-p0.md). FX move that this split follows: [P2 wire](cockpit-ship-stage-p2-wire.md). Renderer: [render memo](cockpit-ship-stage-p0-render.md).

Planning only. This file does not change the engine, the redesign cockpit, the hull meshes, or the warp clips. Tip surveyed: `feature/grokbot-player` @ `4e025f15` (#319). #319 (`4e025f15`) refreshed the P2 wire tip onto `22476c94`. #318 (`22476c94`) refreshed the four-hull tip onto `d5dae78e`. #317 (`d5dae78e`) refreshed COMMANDER_NEXT through #316 onto `2113bc26`. #316 (`2113bc26`) moved the INDEX tip to `fcbf2621`. #315 (`fcbf2621`) stamped batch-2 Pass on product #312 (`51acad6f`). #314 (`9b1dc5a3`) refreshed the four-hull tip onto `ad19c488`. #313 (`ad19c488`) refreshed the prior P3 layout tip onto `51acad6f`. #312 (`51acad6f`) landed batch-2 haulers product on the SVG path. #310 (`6605bc88`) moved the INDEX tip to `a69c7a6c`. #311 (`a69c7a6c`) refreshed COMMANDER_NEXT through #309 onto `55ce45b5`. #309 (`55ce45b5`) refreshed P2 readiness onto `5ff288f9`. #308 (`5ff288f9`) refreshed the four-hull tip to `b767c1ac`. #307 (`b767c1ac`) refreshed the prior P3 layout tip to `a7e2de1e`. #306 (`a7e2de1e`) moved the INDEX tip to `d945b6fa`. #305 (`d945b6fa`) refreshed the four-hull tip to `76d44fa7`. #304 (`76d44fa7`) refreshed COMMANDER_NEXT through #303 (mailbox tip `05aba977`). #303 (`05aba977`) refreshed P2 readiness onto `b494b8dd`. #302 (`b494b8dd`) moved the INDEX tip to `51c37a61`. #301 (`51c37a61`) refreshed the four-hull tip to `836cd492`. #300 (`836cd492`) refreshed the prior P3 layout tip to `f91733b5`. #299 (`f91733b5`) moved the INDEX tip to `e2a4a131`. #298 (`e2a4a131`) refreshed COMMANDER_NEXT through #297 (mailbox tip `5c6548f0`). #297 (`5c6548f0`) refreshed P2 readiness onto `2e213c36`. #295 (`2e213c36`) refreshed the four-hull tip to `efcb49ee`. #296 (`efcb49ee`) stamped batch-1 Pass on product #293 (`186aaf85`). #291 (`595a1654`) refreshed the prior P3 layout tip to `860264d0`. #292 (`860264d0`) refreshed COMMANDER_NEXT through #290 (mailbox tip `8fb0c5af`). #290 (`8fb0c5af`) refreshed the four-hull tip to `dad09964`. #289 (`dad09964`) refreshed P2 readiness onto `6a8edd87`. #288 (`6a8edd87`) moved the INDEX tip to `4f94110a`. #287 (`4f94110a`) refreshed the four-hull tip to `f7a9a82e`. #286 (`f7a9a82e`) refreshed the prior P3 layout tip to `484e9fb9`. #271 (`8a13628c`) stamped Cut 2 Pass on product #268 (`b0e96881`). Cut 1 Pass landed (#246 / #244 / #238). Batch-2 haulers product has landed (#312, `51acad6f`) on the SVG path. #315 (`fcbf2621`) stamped batch-2 Pass on product #312 (`51acad6f`). Batch-1 Pass stays #296 on product #293 (`186aaf85`). P2 stays behind the remaining P1b Passes. P3 product stays gated behind the remaining P1b Passes and P2. The batch-2 Pass (#315) does not open the layout PR. The batch-1 Pass (#296) does not open the layout PR. The cut-2 Pass does not open the layout PR. #319 does not open it. WebGL stays closed.

Sticky order stays P1 SVG, then P1b, then P2, then P3. P3 product code stays closed on this tip. It waits behind the remaining P1b Passes and behind P2. Batch-2 Pass is stamped (#315 on product #312, `51acad6f`). Batch-2 haulers product landed on the SVG path (#312, `51acad6f`). Batch-1 Pass stays #296 on product #293 (`186aaf85`). The landings above do not open the layout PR. #319 refreshed the P2 wire tip onto `22476c94` and does not open it. #315 stamped batch-2 Pass on product #312 (`51acad6f`) and does not open it. #296 stamped batch-1 Pass on product #293 (`186aaf85`) and does not open it. The P1 SVG spike has already passed (#215, `9d29349a`). Cut 2 Pass is already stamped (#271 on product #268). Batch-1 Pass is already stamped (#296 on product #293, `186aaf85`). Start the product PR only after the remaining P1b passes and P2 have merged, from that later tip on `feature/grokbot-player`. The stage is still the shared SVG in `#shipSvg` (`viewBox="0 0 400 260"`). If a cut opened the WebGL off-ramp in the render memo, stop. Do not lay a second renderer into this grid.

No new engine field, no new `EVENT_FACTS` key, no new action, no new event. No EIS, Markham, or ANSI tracing.

## What the grid is on this tip

`#deck` in `web/redesign.css`:

```css
grid-template-columns: 1.15fr 1fr 0.95fr;
grid-template-rows: minmax(0, 1.35fr) minmax(110px, 0.7fr);
grid-template-areas: "view nav ship" "here here term";
```

The three top tracks sum to 3.1. The left viewport is about 37% (`view`), the map is the middle track at about 32% (`nav`), and the ship is the right track at about 31% (`ship`). HERE (`#context`, grid area `here`) spans the first two bottom cells. COMMS (`#term`, grid area `term`) is the bottom-right cell.

`web/layout.js` copies that geometry. `PANELS` is viewport, nav, ship, context, term. `DEFAULT_COLS` is `[1.15, 1, 0.95]`. `SLOTS` is three top cells plus a bottom span of 2. Two column splitters are created: `splitter-col-0` ("Resize viewport and nav") and `splitter-col-1` ("Resize nav and ship"). `placeSplitters` hides them when the computed column count is under 3. `wideQ` is `(min-width: 1101px)`. A saved deck lives at `tw2k-deck-v1:<gameId>:<seat>`.

Below 1101px the stylesheet replaces the areas:

```css
@media (max-width: 1100px) {
  #deck { grid-template-columns: 1fr 1fr; grid-template-areas: "view nav" "ship here" "term term"; }
}
@media (max-width: 700px) {
  #deck { display: block; }
  #vpScreen { height: 120px; }
  #nav { max-height: 200px; }
}
```

At 700px and under, document order is the stack: `#viewport`, `#nav`, `#ship`, `#context`, `#term`.

`#shipSvg` is `flex: 0 0 auto`, `aspect-ratio: 400/260`, `max-height: 140px`. Three more caps sit on top of that:

| Query | Cap |
| --- | --- |
| `(max-height: 820px) and (min-height: 781px) and (min-width: 701px)` | `max-height: 124px; height: 124px` (the 1280×800 cargo-row comment) |
| `(min-height: 900px)` | `max-height: 164px` |
| `(max-height: 780px)` | `max-height: 34%` |
| `(max-width: 700px)` | `max-height: 210px`, and `.hull-float` animation off |

`.panel` is `position: relative`. `#ship` is set to `overflow: hidden` and later to `overflow: auto`; the later rule wins. `#fighterRow`, `#shipStats`, and `#holds` are `flex: 0 0 auto`.

P2 leaves this template in place on purpose. It removes `#viewport`, parks the sector report in `#sectorReport` on grid area `view`, and puts `#stageFx` (with `#warpClip` inside it) beside `#shipSvg` inside `#ship`. P3 is the change that deletes area `view` and the 140px cap. P3 stays behind the remaining P1b product passes and P2. Do not start the product PR.

## Target grid

Desktop is `min-width: 1101px`, the same query `layout.js` treats as wide. Default deck only: `data-deck="default"`, no map boost, no inline `gridTemplateColumns`.

Top row is two tracks. Ship on the left, map on the right. HERE and COMMS stay on the second row, ship column and map column. The map is not under the ship.

```css
#deck {
  grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr);
  grid-template-rows: minmax(0, 1.35fr) minmax(110px, 0.7fr);
  grid-template-areas:
    "ship nav"
    "here term";
}
```

`1.5fr` / `1fr` is 60% / 40% of the row. 60% is the top of the P0 ship band (55–60%). The map takes the rest of that row, 40%. A two-track row cannot be 58% and 35% at the same time without a blank third track. A blank track is the old viewport column. Do not add one. `justify-content` stays the initial value so the two tracks fill the row.

`DEFAULT_COLS` in `web/layout.js` becomes `[1.5, 1]`, the same ratio, so the first splitter drag and a map boost do not jump off the stylesheet. `DEFAULT_ROWS` stays `[1.35, 0.7]`.

Measure the border boxes against the deck content box (`#deck.clientWidth` minus the 8px of horizontal padding on each side):

- `#ship` width is in `[0.55, 0.60]` of that content box.
- `#nav` width is in `[0.35, 0.42]` of that content box. 40% passes. A later override of 35% also passes. A 50/50 top row fails.
- `#ship` is left of `#nav`, and their tops are within 2px.
- Computed `grid-template-areas` names `ship` and `nav` on the first row. It does not name `view`.
- No third panel sits in the top row.

If Ben has named a different split by the time the product PR opens, his numbers replace `1.5fr` and `1fr`, and they replace `DEFAULT_COLS`. Map-under-ship is still an explicit override. It is not a reading of this default.

The bottom row is one cell each. HERE loses the span of 2 (today it is about 69% of the width). It becomes the ship column, about 60%. COMMS leaves the old 31% right cell and becomes the map column, about 40%. Do not restore `"here here"` by spanning HERE under the map.

## What moves, what stays

| Piece | P3 |
| --- | --- |
| `#ship` | Grid area `ship`, left track. In the document, first panel inside `#deck`, so a phone stack leads with the hero. |
| `#nav` (`#map`, `#mapTools`, `#course`, `#warps`) | Grid area `nav`, right track. Second in the document. Click behavior stays the `go(id)` already in `web/redesign.js`: an id in `S.sector.warps_out` calls `act("warp", { target: id })`; any other sector calls `loadCourse(id)`. A drag still suppresses the click (`bindMapPointer`). `#warps` buttons still warp. Zoom, Center, Enlarge (`#nav.enlarged` is `position: fixed; inset: 0`) stay. Map `viewBox="-300 -300 600 600"` stays. |
| `#context` / `#here` | Grid area `here`, under the ship. Verbs stay in `#here`. |
| `#term` | Grid area `term`, under the map. COMMS and LOG stay. |
| `#sectorReport` / `#sectorText` | Leaves grid area `view`. Sits in `#context`, after the HERE heading and before `#here`, in ordinary flow. The id stays `sectorText`, the class stays `ansi`, and `sectorText()` in `web/redesign.js` stays the writer. |
| `#shipStage` | New wrapper inside `#ship`, after the ship heading, around `#shipSvg` and `#stageFx`. `position: relative; flex: 1 1 auto; min-height: 0`. This is the box the mesh fills. |
| `#stageFx`, `#warpClip`, Live / Stills / Off | Stay the nodes P2 mounted. The overlay's containing block becomes `#shipStage`, so an `inset: 0` clip covers the picture and not `#shipStats` or `#holds`. Test ids stay: `warp-clip`, `warp-svg`, `warp-skip`, `viewport-mode-live`, `viewport-mode-stills`, `viewport-mode-off`. `data-mode` stays on the host P2 chose. |
| `#cmdline`, `#keys`, `#menu`, `#layoutMenu`, `#err` | Stay. |

`#fighterRow`, then `#shipStats`, then `#holds` stay in that order, as siblings after `#shipStage`, still `flex: 0 0 auto`. Words and order inside the stat block stay whatever `paintShip` writes. The legend stays on the fighter row.

## `#shipSvg` size

The SVG element grows. The coordinate system does not. Leave `viewBox="0 0 400 260"`. Leave `preserveAspectRatio` at the SVG default (`xMidYMid meet`) so the hull does not stretch. Leave `data-fit` (`1.12` drift, `0.72` static) alone. Filling the stage is the element box getting the free space in `#ship`. A hull that still looks small inside the viewBox is an art pass, not a layout pass.

Delete these caps from `web/redesign.css`. They are the postage-stamp rules:

- `#shipSvg` `max-height: 140px` and `flex: 0 0 auto`
- the 124px rule at `(max-height: 820px) and (min-height: 781px) and (min-width: 701px)`
- `max-height: 164px` at `(min-height: 900px)`
- `max-height: 34%` at `(max-height: 780px)`
- `max-height: 210px` at `(max-width: 700px)`

Desktop and the 701–1100 band:

```css
#ship { display: flex; flex-direction: column; overflow: hidden; min-height: 0; }
#shipStage { position: relative; flex: 1 1 auto; min-height: 0; display: flex; }
#shipSvg {
  width: 100%;
  height: 100%;
  flex: 1 1 auto;
  min-height: 0;
  max-height: none;
  aspect-ratio: auto;
}
#stageFx { position: absolute; inset: 0; }
```

Drop the second `#ship { overflow: auto }` so the picture cannot scroll out from under the stats. At a tuned font (`--cockpit-font` up to 24px) the stat block may scroll inside `#shipStats` / `#holds`. The stage keeps `min-height: 0` and may shrink. It does not go back to a 140px ceiling.

`cursor: grab`, `touch-action: pan-y`, and `.is-drag` stay, so the existing yaw/pitch drag still works on the bigger picture.

Checks, default 15px font, default deck:

- 1600×1000: `#shipSvg` border height is greater than 164 (the old tall cap). `#holds` lies fully inside `#ship`.
- 1280×800: `#holds` lies fully inside `#ship`. This is the window the 124px rule was papering over. The stats win if the free space is tight. There is still no `max-height` at or under 164px for `min-width: 701px`.

## Phone and the 700px edge

`max-width: 700px` includes 700. `min-width: 701px` is the other side. Check both.

| Viewport | Layout |
| --- | --- |
| 390×844 and 700×800 | `#deck` stays `display: block; overflow: auto`. Stack order is `#ship`, `#nav`, `#context`, `#term`. |
| 701×800 and 1100×800 | Two equal columns. Areas `"ship nav" "here term"`. The 55–60 band is not required. The map is still beside the ship, not under it. |
| 1101 and up (1280×800, 1600×1000) | The `1.5fr` / `1fr` hero. Splitters show. |

Phone picture, inside the same `max-width: 700px` query:

```css
#shipSvg { width: 100%; height: auto; flex: 0 0 auto; max-height: 46vh; aspect-ratio: 400 / 260; }
#nav { max-height: 200px; }
```

46vh on an 844px phone is about 388px, which is past the old 210px phone cap and well past 140px. The deck already scrolls. `#nav.enlarged` still covers the screen. Delete `#vpScreen { height: 120px }` in that query; the node is gone after P2.

The `max-width: 1100px` map-boost rules (`body[data-map-boost]` raising `#nav` max-height) stay. They do not name the viewport. On a wide deck, map boost still adds `mapBoost * 1.15` to the nav track through `boostedCols`. With `DEFAULT_COLS` of `[1.5, 1]` and boost 3, the nav track becomes `4.45` against `1.5`, about 75% of the row, which still clears the existing "map wider than half the deck" check.

## Custom layout leftovers

`web/layout.js` is the viewport column that CSS will not age out by itself. P2 does not edit this file. P3 does.

- `PANELS` / `ORDER`: `ship`, `nav`, `context`, `term`. Drop `viewport`. Four rows in the layout menu. The checkbox test id `show-viewport` goes away with the row.
- `SLOTS`: `{ col: 1, row: 1 }` ship, `{ col: 2, row: 1 }` nav, `{ col: 1, row: 2 }` context, `{ col: 2, row: 2 }` term. No `span: 2`.
- One column splitter, index 0, label "Resize ship and nav", test id `splitter-col-0`. Delete `splitter-col-1`. `placeSplitters` treats a column count under 2 as "hide", not under 3.
- `clampTracks` already returns null when the saved `cols` length differs from `DEFAULT_COLS`. A stored 3-track array therefore falls back to the stylesheet. A stored `order` or `hidden` entry of `viewport` is dropped because it is not in `ORDER`. Font, zoom, `mapBoost`, and the other panel ids survive. Do not bump `v`. Do not wipe `tw2k-deck-v1` on load.
- Reset still clears inline `gridTemplateColumns` and returns the stylesheet.

`navSlot()` keeps adding boost to whichever column `nav` occupies. With nav in slot column 2, "Larger map" widens the right track.

## CU seat and reduced-motion stills

P3 does not add a motion path. The hero gets bigger, and the stills stay still.

Keep, and do not loosen:

```css
@media (prefers-reduced-motion: reduce) { #shipSvg .hull-float { animation: none; } }
@media (max-width: 700px) { #shipSvg .hull-float { animation: none; } }
```

Add the same `animation: none` for `body.cu-seat #shipSvg .hull-float` and for `#shipSvg[data-motion="still"] .hull-float` and `#shipSvg[data-motion="static"] .hull-float`. On this tip `.hull-float` runs a 9px bob whenever the two queries above miss, and `shipMotion()` does not look at `body.cu-seat`. P2 holds the JS drift and the transients for that class. The CSS bob is independent of `data-motion`. Gate it. Leave `@keyframes ship-float` and the 7.2s duration as they are for a live desktop seat.

Leave `#map .pulse` alone. Leave the `#warpClip` reduced-motion rule alone. It is id-scoped and follows the node P2 reparented. Do not add an entrance animation on `#shipStage`.

`body.cu-seat` already forces `min-height: 48px` and `min-width: 48px` on `#waitchip`, `#warps button`, `#here button`, `button.verb`, `a.manual-link`, and `#connectBtn`. Keep those. Extend the same 48px minimum to the controls that now sit on the hero and the map chrome: `#warpSkip`, `[data-vp-mode]`, `#mapTools button`, `#course button`. The column splitter stays the 8px gap. Widening that hit target to 48px would open a gutter between the ship and the map. Map node circles stay the radii `map()` already writes.

`?mode=cu` still only adds `cu-seat`. Phone width still returns `static` from `shipMotion()` (`max-width: 700px`). Do not edit `shipMotion` or `warpMotion` in this PR if P2 already pointed them at the new mode host. A CSS-only gate is enough.

## Tests the product PR updates

These two still assume five panels and a `view` area. Retarget them in the same change. Do not put `#viewport` back to make them pass.

- `tests/test_cockpit_dashboard_custom_v1.py`. `PANELS` includes `viewport`. `_boxes` reads `#viewport` and asserts `"view" in fresh["areas"]`. The phone stack asserts y-order `viewport, nav, ship, context, term`. `show-viewport` hides `#viewport`. The wide case drags `splitter-col-1`. After this layout, areas contain `ship` and `nav` and do not contain `view`. The stack y-order is `ship, nav, context, term`. The only column splitter is `splitter-col-0`. Inline columns on a default deck stay `""`.
- `tests/test_cockpit_custom_layout_v1.py`. `_labels` requires five `.layout-row` nodes. The phone case unchecks `show-viewport` and waits for `#viewport` to hide. The menu has four rows. Moving the ship is a no-op when ship is already the first panel and already left of nav; the existing `ship.x < nav.x` check still holds.

Leave these alone. They read `/bot` or `/bot2`, or they read `#sectorText` and its data attributes, which this move keeps:

- `tests/test_video_cockpit_v1.py` (`web/bot.html`)
- the `#sectorText` files listed in the P2 wire (`test_terra_and_planet_ownership_v1`, `test_cockpit_redesign_fix2_v1`, `test_cockpit_redesign_gate_v1`, `test_cockpit_redesign_nav_v1`, `test_cockpit_combat_clarity_v1`, `test_cockpit_deep_d1_fix_v1`, `test_cockpit_fullpass_fix2_v1`, `test_cockpit_gameplay_visible_v1`, `test_cockpit_hazards_fix_v1`, `test_cockpit_hazards_scans_v1`, `test_cockpit_info_audit_v1`, `test_cockpit_note45_polish_v1`, `test_cockpit_note51_polish_v1`, `test_cockpit_note97_v1`)
- `scripts/ai_cockpit/runner.py`, which also reads `#sectorText`

If P2 already edited either layout test, keep that edit and only change assertions that still require area `view`, three top-row tracks, `splitter-col-1`, or a max-height at or under 164px.

## Ordered checklist for the product Cur

Files this product PR may edit: `web/redesign.css`, `web/redesign.html` (order, `#shipStage`, where `#sectorReport` sits), `web/layout.js`, and the two layout tests above. It does not edit `web/redesign.js`, `web/hull-meshes.js`, `web/media/warp-clips.json`, `web/bot.html`, `web/bot2.html`, `web/viewport.js`, or `src/tw2k/**`.

1. Branch from `feature/grokbot-player` after the remaining P1b product passes and P2 have merged. Order is P1 SVG, then P1b, then P2, then P3. The P1 spike has already passed. Confirm `#viewport` is gone, `#sectorText` still resolves, `#stageFx` and `#warpClip` live under `#ship`, and `TW2KHullMeshes` is still the shared SVG path. If a cut opened the WebGL off-ramp, stop.
2. Set the desktop areas and tracks in the target-grid section. Point `DEFAULT_COLS`, `SLOTS`, `PANELS`, and the single column splitter at that grid. Confirm a default 1101px-wide deck measures inside the ship and nav bands, with the map on the right.
3. Wrap `#shipSvg` and `#stageFx` in `#shipStage`. Remove the 140 / 124 / 164 / 34% / 210 caps. Let the SVG fill `#shipStage` with `max-height: none` and `aspect-ratio: auto` above 700px. Keep the viewBox. On `max-width: 700px`, cap the picture at `46vh` and stack ship, nav, HERE, COMMS. At 701–1100px use equal columns and areas `"ship nav" "here term"`.
4. Move `#sectorReport` into `#context` in normal flow. Keep `sectorText()` and every selector it writes (`#sectorText`, `[data-port-class]`, `[data-planet="class"]`, `[data-mines="sector"]`, `[data-navhaz=here]`, `[data-beacon=here]`, `[data-terra=row]`). Delete `#vpScreen { height: 120px }` and any `#deck` rule that still names area `view`.
5. Gate `.hull-float` for `body.cu-seat` and for `data-motion` of `still` or `static`. Add the 48px minimum on `#warpSkip`, `[data-vp-mode]`, `#mapTools button`, and `#course button`. Leave the existing cu-seat minima in place.
6. Update the two layout tests named above. Leave the sector-report tests and `test_video_cockpit_v1.py` unchanged.

Done when the P0 P3 list is true on `/bot?layout=redesign`, and these checks are true with it:

- At 1280×800 and at 1600×1000, default deck, ship is 55–60% of the deck content box, nav is 35–42% and on the right, tops align, and the areas string has no `view`.
- At 1600×1000, `#shipSvg` is taller than 164px and `#holds` is inside `#ship`. At 1280×800, `#holds` is inside `#ship`.
- At 390×844 and at 700×800 the deck is `display: block` and `#ship` is the first panel. At 1100×800 the map is beside the ship.
- An adjacent map node still calls `act("warp")`. A non-adjacent node still calls `loadCourse`. Enlarge still covers the screen.
- `#sectorText` and the data attributes in step 4 still resolve. The LANDED line is still the string `sectorText()` writes.
- `prefers-reduced-motion`, `max-width: 700px`, and `body.cu-seat` leave `.hull-float` with `animation: none`. The cu-seat buttons named above are at least 48px. The turn is not blocked.
- A saved 3-track `cols` array does not throw and does not restore a `view` column. Reset returns the stylesheet grid.

## Leave untouched

The engine, `EVENT_FACTS`, and actions. `web/hull-meshes.js` and `buildHullFaces` / `projectFace`. P2's FX state function, `isRealMove`, `playWarpClips`, `showWarpClip`, and the combat / port / planet / mine paints. `#sectorText` selectors and `sectorText()`. `web/bot.html`, `web/bot2.html`, and `tests/test_video_cockpit_v1.py`. Warp-clip JSON and the CSS camera grammar on `#warpClip`. A second renderer. Ferrengi hull art. Copying or tracing EIS, Markham, or ANSI. `docs/plans/COMMANDER_NEXT.md` and `docs/plans/GAP_MAP.md`.
