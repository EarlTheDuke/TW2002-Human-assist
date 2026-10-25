# Cockpit ship stage — P0 exploration pack

Planning only. This pack does not change the engine, the redesign cockpit, the hull meshes, or the warp clips. Tip surveyed: `feature/grokbot-player` @ `ec4bc50` (`List in-use Ferrengi hulls on Libram key C`).

The stills inventory is [stills/README.md](stills/README.md) (#344).

Ben can override any recommended default in the decision list at the bottom. The fighter-count rule is the one default this pack treats as already decided.

## Sheets

| Sheet | What Ben is reacting to |
| --- | --- |
| [Silhouette bible](cockpit-ship-stage-p0-silhouette-bible.md) | Original look for all 17 player hulls, plus the fighter marker. |
| [P1b next hulls](cockpit-ship-stage-p1b-next-hulls.md) | Mesh contract for Scout Marauder, Merchant Freighter, BattleShip, and Corporate FlagShip. Implement after the spike merges. |
| [FX state machine](cockpit-ship-stage-p0-fx.md) | Idle, warp, port, planet, mine, combat. Triggers are events that exist today. |
| [Render decision](cockpit-ship-stage-p0-render.md) | Stay on the shared SVG mesh. Spike Merchant Cruiser and Imperial StarShip before the fleet. |
| Sticky, below | One paragraph for `COMMANDER_NEXT` or an improvement list. |

## What the picture is today

The solid Merchant Cruiser in the attached view is `fleet-glass-v1` (`web/hull-meshes.js`, `look: "fleet-glass-v1"`). Each hull is four loft stations skinned as an 8-sided tube, plus one role part. The Merchant measures 153 faces and an AABB of about 162×32×64. That is a smooth sausage. The WebGL call in `shipSolidOn()` (`web/redesign.js`) only probes `getContext("webgl")` and then throws the context away. Solid mode still writes SVG polygons through `projectFace`.

The same frame shows Shields `0/400`. Under 35% shields, `drawShipFrame` sets damage and `projectFace` darkens the hull and pushes the red channel up. At zero shields the class colour is gone and the hull is one red body. A quality bar that needs the job to read without the name label cannot depend on a full shield bar.

Fighters use `FIGHTER_EXACT_CAP = 200`. At or under 200, one red triangle is one fighter. Above that, `scale = ceil(n / 200)`, the triangle count is `ceil(n / scale)`, and those triangles pack into at most four corner clusters. `fighterSlots` starts its orbit at radius 56. The Merchant's bounding radius is about 93, the Imperial StarShip's about 121, so the inner ticks sit inside the body. The screenshot matches that: ticks on the hull, clusters as a fallback only past 200.

The left `#viewport` (`web/redesign.html`) holds `#vpStars`, `#sceneStill`, `#warpClip`, and `#sectorText`. Warp cinema for a real move is `playWarpClips` → `showWarpClip`, driven by `web/media/warp-clips.json` (17 hulls, 10 SVG variants each) and the same `buildHullFaces`. `web/viewport.js` draws no canvas when `?mode=cu`.

The deck is still `grid-template-areas: "view nav ship" / "here here term"` with columns `1.15fr 1fr 0.95fr` (`web/redesign.css`). The ship is the right-hand column. `#shipSvg` is capped around 140px tall (164px only when the window is at least 900px tall). A hero that stays under that cap will still look like a postage stamp after the mesh improves.

`#sectorText` is the ANSI sector report (port class, planets, traders, mines, warps, LANDED). Tests and the CU seat read it. Aging out the viewport does not delete that report.

## Sticky rules already set

- Visual fighter markers = `max(1, ceil(n / 100))` when `n ≥ 1`. `n = 0` draws nothing. Each marker stands for 100 fighters. Markers orbit outside the hull body.
- The left viewport is aged out. Warp, port, planet-land, mine, and combat tells move onto the ship stage.
- Layout default, open to override: ship about 55–60% left-center, Nav map about 35% on the right. Map-under-ship is the option this pack does not recommend.
- Classic ANSI outlines stay **UNVERIFIED**. No EIS or Markham trace. The bible invents looks from the public role numbers in `SHIP_SPECS_TW2002` / `POD_SPEC`.

## Phased build

Product code starts only after Ben reacts to this pack. None of it is in this PR.

### P1 — Hero meshes and 100:1 fighters

Build the two spike hulls in [the render memo](cockpit-ship-stage-p0-render.md) to the bible, on the existing `buildHullFaces` / `projectFace` path. Roll the other 15 only after those two pass the bar. Order and batch cuts for those 15: [fleet order](cockpit-ship-stage-p1b-fleet-order.md).

Done when:

- Merchant Cruiser and Imperial StarShip match their bible entries at the current ~140px panel and at a hero crop about 55% of the deck.
- With the name plate covered, a reader can tell trader from capital. With shields at 0, the class accent is still that colour.
- Marker count follows the sticky formula, including 25 at 2,500, 500 at 50,000, and a measured 1,000-marker case for the later Interdictor. No marker's screen box intersects the hull silhouette on the canonical three-quarter view.
- The visible legend reads `each marker = 100 fighters`. The stat block keeps today's words and order, and the exact bay. Corner clusters and `FIGHTER_EXACT_CAP` retire.
- A warp clip for each spike hull still calls `buildHullFaces`, and the side and head-on cameras still read as that hull.
- `prefers-reduced-motion`, a phone (`max-width: 700px`), and `body.cu-seat` hold the canonical still. The turn is not blocked.
- `web/hull-meshes.js` stays under 40 KB gzipped (the ship-view budget cited in NOTE 94 is 300 KB). Frame time for the drift pose is recorded at 500 and at 1,000 markers.
- Ship-view tests that assert the 200-cap legend are updated in the same change. No engine change, no new action, no new event field.

After that spike merges, the next meshes are the four hulls in [P1b](cockpit-ship-stage-p1b-next-hulls.md). They are not part of this spike.

### P2 — FX onto the stage, then remove the viewport

Depends on P1 for the two spike hulls so the new states are not playing the red sausage. The FX sheet lists every trigger. Wiring those triggers is cockpit work. It does not add engine fields. The product checklist, with the symbols to call and the nodes to move, is [P2 wire](cockpit-ship-stage-p2-wire.md). Product code waits until the P1 Merchant Cruiser and Imperial StarShip spike has merged.

Done when:

- The six states in the FX sheet run from the events named there.
- Warp variants play on the ship stage. `#warpClip` is no longer a child of `#viewport`.
- `#viewport` has no player-facing job. Stars, scene stills, and the dock/combat/warp videos in that pane are retired.
- Every fact `#sectorText` shows today is still on screen. Existing selectors (`#sectorText`, `[data-port-class]`, `[data-planet="class"]`, `[data-mines="sector"]`) keep working, or the same change updates the tests that read them (`test_cockpit_note45`, `test_cockpit_note51`, `test_cockpit_note97`, `test_cockpit_redesign_nav`, and the redesign gate).
- Live / stills / off still mean animate, canonical still, and no FX loop. Reduced motion and `?mode=cu` stay on the still. Skip still dismisses a clip. A clip never blocks the turn.
- `test_video_cockpit_v1.py` currently asserts `id="viewport"` inside the page. That assertion is updated in the same change that removes the node.

### P3 — Layout split

Tracks, caps, and the viewport-column leftovers: [P3 layout](cockpit-ship-stage-p3-layout.md).

Done when:

- The top of `#deck` is the ship stage at 55–60% and `#nav` at about 35%, side by side. HERE and COMMS stay. The map is not under the ship.
- `#shipSvg` is no longer capped at 140px. The mesh fills the stage. Stats and holds stay readable in today's order.
- Adjacent-sector click still warps, and a far click still plots a course.
- Checked at a phone width, at 700px, and on a desktop deck. `body.cu-seat` controls stay at least 48px.
- If Ben has overridden the split by then, the override wins over the numbers in this pack.

## Paste into COMMANDER_NEXT

Ship stage becomes the hero of the redesign cockpit. Replace the fleet-glass sausage (four-station loft, empty shields painting the hull one red body, fighter ticks stuck on the hull) with original per-class silhouettes that read the job without the name label. Fighter markers are `max(1, ceil(n/100))` when n≥1, each marker standing for 100 fighters, orbiting outside the hull. Age out the left viewport (stars, warp clip, scene stills) and play warp, port, planet-land, mine, and combat on the ship stage, keeping the sector report. Layout: ship about 55–60% left-center, Nav map about 35% on the right. Stay on the shared SVG mesh the warp clips already use, unless the Merchant Cruiser and Imperial StarShip spike misses that bar.

## Decisions, with the default this pack recommends

| Topic | Default | Override is cheap |
| --- | --- | --- |
| Renderer | Shared SVG lofts, richer stations and kit. Three.js stays the off-ramp. | Yes, if the spike misses the bar. |
| Who is in the spike | Merchant Cruiser and Imperial StarShip. | A different pair still needs one common trader and one capital. |
| Empty shields | Scars and a dim bubble. Class accent stays. | A red damage wash can return as a flash during combat only. |
| Marker legend | `each marker = 100 fighters`. Exact bay stays on the stat line. The last marker may be a partial hundred and is not given its own numeral. | Label the remainder on the marker if the round hundred feels like a lie at low counts. |
| Orbit clearance | Outside the bounding sphere, and no screen-box overlap on the canonical view. | A tighter ring that still clears the silhouette. |
| Transwarp as warp FX | P2 plays `ship_transwarp` and `planet_transwarp` with the warp state. Today `isRealMove` ignores both. | Leave Transwarp as an instant sector change until a later note. |
| Sector report | Moves with the viewport removal. Same selectors if possible. | A new node, if the tests move with it. |
| Layout | 55–60% ship, ~35% map, side by side. | Any split Ben names. Map-under-ship needs an explicit override. |
| WebGL probe | P1 stops using a failed probe as the reason to fall back to the NOTE 77 outline. The outline remains the fallback when the mesh module is missing. | Keep the probe if a no-WebGL machine must stay on the flat outline. |

## Out of scope

Ferrengi hulls. They are not player `ShipClass` values. New engine events, new `EVENT_FACTS` keys, and new actions. Copying or tracing EIS, Markham, or ANSI ship art. Editing `web/redesign.js`, `web/redesign.html`, `web/redesign.css`, `web/hull-meshes.js`, warp clips, or engine code in this PR.
