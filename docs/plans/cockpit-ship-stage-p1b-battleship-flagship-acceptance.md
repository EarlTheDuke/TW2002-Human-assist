# P1b acceptance — BattleShip and Corporate FlagShip

Read-test for cut 2. Docs only. Tip surveyed: `feature/grokbot-player` @ `22c8a144`.

Taken from these sheets, which this file does not replace:

- [Four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) — product order. Cut 1 is Scout Marauder and Merchant Freighter. This sheet is cut 2.
- [Next hulls](cockpit-ship-stage-p1b-next-hulls.md) — mesh contract for [BattleShip](cockpit-ship-stage-p1b-next-hulls.md#battleship--battleship) and [Corporate FlagShip](cockpit-ship-stage-p1b-next-hulls.md#corporate-flagship--corporate_flagship).
- [Marker math](cockpit-ship-stage-marker-math.md) — shared 100:1 count.
- [P1 pass](cockpit-ship-stage-p1-pass.md) — the cleared bar. WebGL stays closed.
- [P1 acceptance](cockpit-ship-stage-p1-acceptance.md) — Pass / Fail / Hold-WebGL, and the off-ramps this cut inherits.

Scope is BattleShip and Corporate FlagShip. One shared mesh, shaded SVG, through `buildHullFaces` / `projectFace`. Faces land in `web/hull-meshes.js`. Scout Marauder and Merchant Freighter are cut 1, on this same bar. This sheet does not restate their looks and does not accept that cut. Merchant Cruiser and Imperial StarShip already cleared the bar. The other eleven hulls stay on `fleet-glass-v1`.

The panel spelling is BattleShip and Corporate FlagShip. `SHIP_SPECS_TW2002["corporate_flagship"]["display_name"]` is `Corporate Flagship`. The mesh keeps the panel spelling.

Cover the name plate for every read below. Look at the current ~140px panel and at a hero crop about 55% of the deck. The crop is a read of the mesh. The layout split stays P3.

The held three-quarter pose is yaw `0.82`, pitch `0.5`, which `shipPose` already uses when motion is held ([FX sheet](cockpit-ship-stage-p0-fx.md)). Head-on is the warp clip camera `headon`.

## Launch

The product PR for these two meshes waits until the Scout Marauder and Merchant Freighter product PR has merged. Both cuts edit `web/hull-meshes.js`. Opening this cut while cut 1 is still in flight thrashes that file. The [four-hull build](cockpit-ship-stage-p1b-four-hull-build.md#build-order) is one cut at a time: finish the cut, then take the next. Cut 2 starts from the merge of cut 1. This sheet is the gate for that later PR. It is not the launch.

## Bar

Same bar as Scout Marauder and Merchant Freighter, from the [four-hull per-hull acceptance](cockpit-ship-stage-p1b-four-hull-build.md#per-hull-acceptance). The [P1 pass](cockpit-ship-stage-p1-pass.md) is the cleared bar this cut inherits. WebGL stays closed.

- Read at ~140px, and at a hero crop about 55% of the deck. Name plate covered. Three-quarter pose yaw `0.82`, pitch `0.5`, and the head-on clip. A reader names the job.
- Markers 100:1, outside the hull. `n < 1` draws nothing. Otherwise `max(1, ceil(n / 100))`. Innermost world radius is the bounding sphere of every face, kit included, plus a gap. No marker screen-box intersects the silhouette.
- Shields empty keeps the accent. The bubble is absent. Scars may show. The class accent stays that colour. A full red body fails.
- Gzip budget. `web/hull-meshes.js` stays under 40 KB gzipped. The budget is cumulative across cuts. Record face counts with the cut.
- Tests. Ship-view tests that assert the 200-cap legend, and a test that pins a `fleet-glass-v1` face count or AABB for a hull in the cut, update in that same change. No engine change, no new action, no new event field.

The rest of the P1 pass list still applies: side clip, `holdWarp`, phone still, reduced-motion still, `body.cu-seat` still, legend `each marker = 100 fighters`, and the exact bay on the stat line.

The numbered checklists in the next-hulls contract are the pass list for the two looks. The lines below are the read a commander judges. They do not add a part.

## Three-quarter

Pose: yaw `0.82`, pitch `0.5`. Repeat at shields 0 and shields full, at both sizes.

BattleShip. A gun platform. A wide hex wedge, short for its beam, broader than the Merchant and shorter than the Imperial. Two turrets on the dorsal face. Their barrels break the top edge, including at ~140px. The barrels are the signature. The length is not. Kit: `turrets`. Section `hex`. A reader calls it a warship. There is no Destroyer hull to draw instead.

Corporate FlagShip. A corp liner. A stepped command block amidships, a lower step and a smaller upper step, taller than the hull is deep. The tower is the signature. It stays a tower when the Imperial's castle is on screen beside it. Kit: `tower`. Section `round`. A reader calls it a capital. Two hundred markers do not replace the tower.

With the name covered, the pair test is a wide short wedge with a turret pair versus a liner with a tower. The FlagShip against the Imperial, already on screen, is a tall tower amidships and three bells in a row versus a long castle and four bells in a square. Those two rows are the [wave read](cockpit-ship-stage-p1b-next-hulls.md#wave-read-test) this cut can judge. BattleShip against the Havoc, and the FlagShip against the Star Master, stay on the later re-shot sheets.

Repeat the FlagShip once with `ship.transwarp.fitted` set and once without. Fitted, the engine cones are magenta and the upper step stays flat `#ff77ff`. Idle cones stay cyan-white.

## Head-on

One existing clip per hull. Side camera and head-on camera. The kit still reads in both. A part that only exists in the three-quarter view is not a signature. `holdWarp` still pauses a frame.

BattleShip. A wide hex face. Two barrel tips above the hull, left and right. They are the high points. Three engine mouths in a low row, inside the hex width.

Corporate FlagShip. A rectangle on the centerline, taller than the hull. Three engine mouths in a low row, inside the beam. The same drive pair as the three-quarter read: fitted cones go magenta, and the upper step stays the flat accent.

## Accent

Dark blue-grey metal on both hulls. The accent is a stripe and the kit, not a tint that replaces the metal. `corp_only` on the FlagShip is a yard gate. It adds no crest and no lettering.

| | BattleShip | Corporate FlagShip |
| --- | --- | --- |
| Accent | `#c5c8ff` | `#ff77ff` |
| Kit | `turrets` | `tower` |
| Shields full | Barrels and stripe `#c5c8ff` | Upper step and stripe `#ff77ff`. Painted metal. The tower is not an emissive lamp. |
| Shields 0 | Bubble absent. Scars may show. The barrels and the stripe are still `#c5c8ff`. | Bubble absent. Scars may show. The upper step and the stripe are still `#ff77ff`. |

A full red body fails at either shield value. Empty shields are scars and a missing bubble. The class accent stays that colour. Gold is the Imperial's accent. It does not appear on the FlagShip. A fitted TransWarp drive changes the FlagShip's cones and nothing else.

## Marker ring

The count is the [marker-math](cockpit-ship-stage-marker-math.md#formula) formula. `n < 1` draws nothing. Otherwise `max(1, ceil(n / 100))`. Each marker stands for 100 fighters. The last marker may be a partial hundred. It gets no numeral of its own. The stat block keeps today's words and order, and the exact bay. The visible legend is `each marker = 100 fighters`.

One chevron dart, fill `#ff2a2a`, stroke `#ff8888`. The dart is a marker, not a second ship mesh. Markers yaw with the hull and read as escorts.

The ring sits outside the hull body. Innermost world radius is the bounding sphere of every face, kit included, plus a gap. On the three-quarter pose and in the head-on clip, no marker's screen box intersects the hull silhouette.

BattleShip. The sphere includes the loft, both turret bodies, both barrels, and the three engines. The barrels set the top of the sphere. A ring that clears the hex and clips a barrel fails. Cap is 10,000 fighters, 100 markers, on both rosters.

Corporate FlagShip. The sphere includes the loft, both tower steps, and the three engines. The upper step sets the top of the sphere. A ring that clears the liner and clips the tower fails. Cap is 20,000 fighters, 200 markers, on both rosters. Two hundred is this wave's largest cloud, and it is under the 500-marker case the P1 pass records. The formula has no silent cap.

| Fighters `n` | Markers | What the ring shows |
| --- | --- | --- |
| 0 | 0 | No darts. |
| 1–100 | 1 | One dart. `ceil(100 / 100)` is 1. |
| 101 | 2 | First bay that draws two. |
| 10,000 | 100 | BattleShip cap. Screenshot case. Outside the barrel tips. |
| 20,000 | 200 | FlagShip cap. Screenshot case. Outside the top of the tower. |

## CU-seat and reduced motion

`prefers-reduced-motion`, a phone (`max-width: 700px`), and `body.cu-seat` hold the canonical still. That still is the three-quarter pose above. No loop on those three. The turn is not blocked. A still draws the marker count and holds the pose.

## Rest of the pass list

- `web/hull-meshes.js` under 40 KB gzipped, cumulative with the P1 faces and with cut 1. The [P1 pass](cockpit-ship-stage-p1-pass.md) recorded 8,673 bytes gzipped (level 9) before those later faces. Record this cut's face counts and the gzip size of the module after the faces land.
- Screenshots of both hulls, name covered, at ~140px and at the hero crop, shields empty and shields full, plus the 100-marker and 200-marker cases. FlagShip once with a fitted TransWarp drive and once without. Side camera and head-on camera. `holdWarp` still pauses a frame.
- When 1,000 separate SVG paths miss the frame, the fix is one group updated by a transform, or one canvas layer for markers only. The count stays `ceil(n / 100)`. Three.js waits for Hold-WebGL below. This cut's caps are 100 and 200. They do not replace the P1 measurement of a drift frame at 500 markers and a static frame at 1,000.

## Files the product PR may touch

After cut 1 has merged. This checklist adds no paths of its own.

May touch:

- `web/hull-meshes.js`, for `battleship` and `corporate_flagship` faces. Faces land there only, so a clip that calls `buildHullFaces` picks them up.
- The ship-view test that still pins a `fleet-glass-v1` face count for those two keys, in the same change. That pin is `FLEET_GLASS` in `tests/test_cockpit_ship_stage_p1.py`. The 200-cap legend tests already moved with the P1 spike. Update them in this change only if this cut breaks them. No engine change, no new action, no new event field.

Leave alone:

- Scout Marauder, Merchant Freighter, Merchant Cruiser, and Imperial StarShip faces.
- The other eleven hulls. A second hull file. A second renderer, unless the block below is Hold-WebGL.
- Batch 3's BattleShip re-shot and batch 4's FlagShip re-shot. Those sheets keep the pair shots. This cut does not recut either mesh to serve them.
- [P0, Out of scope](cockpit-ship-stage-p0.md). Ferrengi hulls. New engine events, new `EVENT_FACTS` keys, and new actions. Copying or tracing EIS, Markham, or ANSI ship art.
- [Render memo, What this spike is not](cockpit-ship-stage-p0-render.md). A new engine field. A new event. A change to warp-clip JSON cameras. A layout split (that is P3). A deletion of `#viewport` (that is P2). A trace of any classic outline.
- `COMMANDER_NEXT.md`, `GAP_MAP.md`, the sheet index, and the other ship-stage sheets.

## Commander decision

Reply with one of these three. Pass means every item on the bar above holds, including the next-hulls checklists for these two hulls. Hold-WebGL means one off-ramp condition on the P1 acceptance is true for this cut. Any other miss is Fail.

Hold-WebGL stays closed. The [P1 pass](cockpit-ship-stage-p1-pass.md) closed it. This cut does not reopen it on its own.

### Pass

Both hulls pass the three-quarter and head-on reads, at ~140px and at the hero crop, at shields 0 and shields full. The FlagShip tower stays a tower beside the Imperial castle, and it stays flat `#ff77ff` with a fitted drive and at shields 0. The BattleShip barrels break the top edge and the ring clears them. Marker rows match the formula, and no marker box cuts the silhouette. CU-seat, reduced motion, and the phone still stay on the canonical still. The cumulative gzip size is under 40 KB, and the face counts are recorded. The fleet-glass pins for these two keys moved in that same change. Stay on the shared SVG (`buildHullFaces` / `projectFace`). WebGL stays the closed off-ramp. The other eleven wait.

### Fail

A pass item is missed, and none of the three off-ramp conditions are true. This cut has not cleared the bar. BattleShip and Corporate FlagShip stay on `fleet-glass-v1` until a later change on the same path passes. The next edit stays on `buildHullFaces` / `projectFace`. The count stays `max(1, ceil(n / 100))` when `n ≥ 1`. Cut 1, once merged, stays merged.

### Hold-WebGL

Stays closed unless this cut fails one of the same three off-ramps as [P1 acceptance](cockpit-ship-stage-p1-acceptance.md#hold-webgl):

- The read still fails at hero size. On this cut, that is the BattleShip and the Corporate FlagShip.
- Drift of the Imperial plus 500 markers, or a static frame of 1,000 markers, cannot hold a 16 ms update on a mid laptop and a phone-class CPU.
- A planet disc and a warp camera cannot be expressed in the SVG the clips already animate.

Open a WebGL spike only after this art pass, and only when one of those is true. That spike consumes the face list from `buildHullFaces`. It does not introduce a second hull file. Warp clips stay SVG until their own note.
