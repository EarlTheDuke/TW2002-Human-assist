# P1 acceptance — Merchant Cruiser and Imperial StarShip

Read-test for the in-flight spike. Docs only. Tip surveyed: `feature/grokbot-player` @ `4ad12856`.

Taken from these sheets, which this file does not replace:

- [P0 pack](cockpit-ship-stage-p0.md) — sticky fighter rule, P1 done-when, out of scope.
- [Render decision](cockpit-ship-stage-p0-render.md) — pass list, off-ramp, what the spike is not.
- [Silhouette bible](cockpit-ship-stage-p0-silhouette-bible.md) — the two looks, the dart, the pair test.
- [Sheet index](cockpit-ship-stage-INDEX.md) — P1 is this spike. SVG path (`buildHullFaces` / `projectFace`). WebGL only if the spike fails the read test.

Scope is Merchant Cruiser and Imperial StarShip. One shared mesh, shaded SVG, through `buildHullFaces` / `projectFace`. The other fifteen stay on `fleet-glass-v1`.

Cover the name plate for every read below. Look at the current ~140px panel and at a hero crop about 55% of the deck. The crop is a read of the mesh. The layout split stays P3.

The held three-quarter pose is yaw `0.82`, pitch `0.5`, which `shipPose` already uses when motion is held ([FX sheet](cockpit-ship-stage-p0-fx.md)).

## Three-quarter

Pose: yaw `0.82`, pitch `0.5`. Repeat at shields 0 and shields full, at both sizes.

Merchant Cruiser. A medium arrow. Blunt wedge nose, canopy just aft of the nose, a keel deep enough to break the underside, two shoulder pods that say cargo. Length is ordinary. The keel and the pods are the tell: a trader with a belly and a bit of fight. This is the hull the fleet-glass sausage has to stop resembling (four loft stations, AABB about 162×32×64).

Imperial StarShip. The longest hull in the fleet. A stepped castle on the spine: a keep, longer than it is tall, with a second step near the nose. Four engine bells, a ventral keel, and two forward barrels that stay smaller than the Frigate's missiles. The castle and the four bells both read from this pose. Gold stays on the castle and the stripe. Top view, the castle's step is the bright accent mass.

With the name covered, a reader says trader for the Merchant and capital for the Imperial. The pair test is keel-and-pods versus a long stepped castle and four bells.

## Head-on

One existing clip per hull. Side camera and head-on camera. The kit still reads in both. A part that only exists in the three-quarter view is not a signature. `holdWarp` still pauses a frame.

Merchant. The keel and the shoulder pods still read, so the head-on view is still the trader.

Imperial. Head-on, the four bells make a square. The castle still reads as a keep, and the gold is still on that castle.

## Accent

Dark blue-grey metal on both hulls. The accent is a stripe, a canopy edge, and the kit, not a tint that replaces the metal.

| | Merchant Cruiser | Imperial StarShip |
| --- | --- | --- |
| Accent | `#7aa2ff` | `#ffe9a0` |
| Kit | `keel`, plus `pods` and `bridge` | `castle`, plus `nacelles` for the four bells |
| Shields full | Blue stripe and blue kit | Gold castle and gold stripe |
| Shields 0 | Bubble absent. Scars may show. The blue stripe is still blue. | Bubble absent. Scars may show. The gold is still gold. |

A full red body fails at either shield value. Empty shields are scars and a missing bubble. The class accent stays that colour.

## Marker ring

Visual markers are `max(1, ceil(n / 100))` when `n ≥ 1`. `n < 1` draws nothing. Each marker stands for 100 fighters. The last marker may be a partial hundred. It gets no numeral of its own. The stat block keeps today's words and order, and the exact bay. The visible legend is `each marker = 100 fighters`. Corner clusters and `FIGHTER_EXACT_CAP` retire.

One chevron dart, fill `#ff2a2a`, stroke `#ff8888`. The dart is a marker, not a second ship mesh.

The ring sits outside the hull body. Innermost world radius is the bounding sphere of every face, kit included, plus a gap. On this three-quarter view, no marker's screen box intersects the hull silhouette. Markers yaw with the hull and read as escorts. Today's `fighterSlots` start at radius 56, inside the Merchant (bounding radius about 93) and the Imperial (about 121). Ticks on the hull fail this read.

| Fighters `n` | Markers | What the ring shows |
| --- | --- | --- |
| 0 | 0 | No darts. |
| 1–99 | 1 | One dart. A partial hundred. No numeral on the dart. |
| 100 | 1 | Still one dart. `ceil(100 / 100)` is 1. The bible bucket is 1–100 → 1. |
| 1,000 | 10 | Ten darts on that same outside ring. |
| 2,500 | 25 | Merchant cap. Screenshot case. |
| 50,000 | 500 | Imperial cap. Orbit outside the bells and the castle. Screenshot case. |
| 100,000, drawn on the Imperial | 1,000 | Throwaway ring standing in for the later Interdictor. Measure it. The formula has no silent cap. |

30 fighters is the render memo's worked example of one marker. It falls in the 1–99 row.

## CU-seat and reduced motion

`prefers-reduced-motion`, a phone (`max-width: 700px`), and `body.cu-seat` hold the canonical still. That still is the three-quarter pose above. No loop on those three. The turn is not blocked.

## Rest of the pass list

The render memo's "Pass, all of these" still includes:

- `web/hull-meshes.js` under 40 KB gzipped. Record face counts, the millisecond cost of one drift frame at 500 markers, and one static frame at 1,000 markers.
- When 1,000 separate SVG paths miss the frame, the fix is one group updated by a transform, or one canvas layer for markers only. The count stays `ceil(n / 100)`. Three.js waits for Hold-WebGL below.
- Screenshots of both hulls, shields empty and shields full, plus the 25-marker and 500-marker cases, before the other 15 leave `fleet-glass-v1`.

## Files the product PR may touch

The spike's file boundary is already in the P0 pack and the render memo. This checklist adds no paths.

May touch:

- `web/hull-meshes.js`, for these two hulls' faces. The render memo: faces land there only, so a clip that calls `buildHullFaces` picks them up.
- Ship-view tests that assert the 200-cap legend, in the same change (P0 P1 done-when). No engine change, no new action, no new event field.

Leave alone. Use these lists as written:

- [P0, Out of scope](cockpit-ship-stage-p0.md). Ferrengi hulls. New engine events, new `EVENT_FACTS` keys, and new actions. Copying or tracing EIS, Markham, or ANSI ship art. The ban in that section on editing `web/hull-meshes.js` is the planning pack's own PR. The spike's permission to edit that file is the faces line above, and that line only.
- [Render memo, What this spike is not](cockpit-ship-stage-p0-render.md). A new engine field. A new event. A change to warp-clip JSON cameras. A layout split (that is P3). A deletion of `#viewport` (that is P2). A trace of any classic outline.
- The other 15 hulls. A second hull file. A second renderer, unless the block below is Hold-WebGL.

## Commander decision

Reply with one of these three. Pass means every item under the render memo's "Pass, all of these" holds. Hold-WebGL means one off-ramp condition in that memo is true. Any other miss is Fail.

### Pass

Both hulls pass the three-quarter and head-on reads, at ~140px and at the hero crop, at shields 0 and shields full. The marker rows match the formula, and no marker box cuts the silhouette. CU-seat, reduced motion, and the phone still stay on the canonical still. The mesh budget and the recorded frame times are in. Stay on the shared SVG (`buildHullFaces` / `projectFace`). WebGL stays the closed off-ramp. The other 15 wait for the screenshots named above.

### Fail

A pass item is missed, and none of the three off-ramp conditions are true. This spike has not cleared the bar. The other 15 stay on `fleet-glass-v1`. The next edit stays on `buildHullFaces` / `projectFace`. A missed 1,000-marker frame uses the group transform or the markers-only canvas layer from the render memo. The count stays `max(1, ceil(n / 100))` when `n ≥ 1`.

### Hold-WebGL

Open a WebGL spike only after this art pass, and only when one of these is true:

- The Merchant and the Imperial still fail the read test at hero size.
- Drift of the Imperial plus 500 markers, or a static frame of 1,000 markers, cannot hold a 16 ms update on a mid laptop and a phone-class CPU.
- A planet disc and a warp camera cannot be expressed in the SVG the clips already animate.

That spike consumes the face list from `buildHullFaces`. It does not introduce a second hull file. Warp clips stay SVG until their own note.
