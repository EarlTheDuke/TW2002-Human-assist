# P1b acceptance — Escape Pod and T'Khasi Orion

Read-test for the batch-1 remainder, the cut after the four-hull wave. Docs only. Tip surveyed: `feature/grokbot-player` @ `36c271a5`.

Taken from these sheets, which this file does not replace:

- [Batch 1 remainder](cockpit-ship-stage-p1b-batch1-remainder.md) — the mesh contract (#216) for [Escape Pod](cockpit-ship-stage-p1b-batch1-remainder.md#escape-pod--escape_pod) and [T'Khasi Orion](cockpit-ship-stage-p1b-batch1-remainder.md#tkhasi-orion--tkhasi_orion). The Scout re-shot is [on that sheet](cockpit-ship-stage-p1b-batch1-remainder.md#scout-marauder--re-shot-not-a-new-mesh).
- [Four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) — product order. This sheet is step 3, after Scout Marauder + Merchant Freighter and after BattleShip + Corporate FlagShip.
- [Marker math](cockpit-ship-stage-marker-math.md) — the shared 100:1 count.
- [P1 pass](cockpit-ship-stage-p1-pass.md) — the cleared bar. WebGL stays closed.
- [P1 acceptance](cockpit-ship-stage-p1-acceptance.md) — Pass / Fail / Hold-WebGL, and the off-ramps this cut inherits.
- [Cut 1 acceptance](cockpit-ship-stage-p1b-scout-freighter-acceptance.md) — the same shape on Scout Marauder and Merchant Freighter.
- [Cut 2 acceptance](cockpit-ship-stage-p1b-battleship-flagship-acceptance.md) — the same shape on BattleShip and Corporate FlagShip. This cut starts after that product PR merges.

Scope is Escape Pod (`escape_pod`) and T'Khasi Orion (`tkhasi_orion`). One shared mesh, shaded SVG, through `buildHullFaces` / `projectFace`. Faces land in `web/hull-meshes.js`. Looks stay on the batch-1 remainder contract. Merchant Cruiser and Imperial StarShip already cleared the bar. Scout Marauder and Merchant Freighter are cut 1, and BattleShip and Corporate FlagShip are cut 2, on this same bar. This sheet does not restate their looks and does not accept those cuts. The Scout on screen for the re-shot is the mesh cut 1 lands. The other nine hulls stay on `fleet-glass-v1`.

The panel spelling is Escape Pod and T'Khasi Orion. `POD_SPEC["display_name"]` is `Escape Pod`. `SHIP_SPECS_TW2002["tkhasi_orion"]["display_name"]` is `T'Khasi Orion`. The mesh keeps those spellings.

Cover the name plate for every read below. Look at the current ~140px panel and at a hero crop about 55% of the deck. The crop is a read of the mesh. The layout split stays P3.

The held three-quarter pose is yaw `0.82`, pitch `0.5`, which `shipPose` already uses when motion is held ([FX sheet](cockpit-ship-stage-p0-fx.md)). Head-on is the warp clip camera `headon`.

## Launch

The product PR for these two meshes waits until both of these product PRs have merged:

1. Scout Marauder and Merchant Freighter.
2. BattleShip and Corporate FlagShip.

Those cuts edit `web/hull-meshes.js`, and this cut edits it too. Opening the Escape Pod and T'Khasi faces while either product PR is still in flight thrashes that file. The [four-hull build](cockpit-ship-stage-p1b-four-hull-build.md#build-order) is one cut at a time: finish the cut, then take the next. Cut 2 starts from the merge of cut 1. This remainder starts from the merge of cut 2. This sheet is the gate for that later PR. It is not the launch.

## Bar

Same bar as the four-hull cuts, from the [four-hull per-hull acceptance](cockpit-ship-stage-p1b-four-hull-build.md#per-hull-acceptance). The [P1 pass](cockpit-ship-stage-p1-pass.md) is the cleared bar this cut inherits. WebGL stays closed.

- Read at ~140px, and at a hero crop about 55% of the deck. Name plate covered. Three-quarter pose yaw `0.82`, pitch `0.5`, and the head-on clip. A reader names the job.
- Markers 100:1, outside the hull. `n < 1` draws nothing. Otherwise `max(1, ceil(n / 100))`. Innermost world radius is the bounding sphere of every face, kit included, plus a gap. No marker screen-box intersects the silhouette.
- Shields empty keeps the accent. The bubble is absent. Scars may show. The class accent stays that colour. A full red body fails.
- Gzip budget. `web/hull-meshes.js` stays under 40 KB gzipped. The budget is cumulative across cuts. Record face counts with the cut.
- Tests. Ship-view tests that assert the 200-cap legend, and a test that pins a `fleet-glass-v1` face count or AABB for a hull in the cut, update in that same change. No engine change, no new action, no new event field.

The rest of the P1 pass list still applies: side clip, `holdWarp`, phone still, reduced-motion still, `body.cu-seat` still, legend `each marker = 100 fighters`, and the exact bay on the stat line.

The numbered checklists in the batch-1 remainder are the pass list for the two looks, and for the Scout re-shot. The lines below are the read a commander judges. They do not add a part.

## Three-quarter

Pose: yaw `0.82`, pitch `0.5`. Repeat at shields 0 and shields full, at both sizes. Repeat once in a frame that also shows the merged Scout.

Escape Pod. A lifeboat. Section `round`. A short capsule, almost as tall as it is long, one round port on the nose, two stub fins large next to the body, one engine inside the fin span. The fins break the side outline, including at ~140px. The port shows on the nose. Kit: `fins`. `detail` stays an empty string. A reader calls it a pod. One marker is not a fleet, so the capsule carries the job.

T'Khasi Orion. An alien fast hull. Section `round`. Swept plates leave the nose and run back past the tail, so the planform is a crescent. Two engines sit inside the plate span. The crescent is one pair. Kit: `swept`. The `wings` token in `detail` does not grow a second pair. A reader calls it a crescent. Eight markers do not replace the plates.

With the name covered, the pair inside this cut is two stub fins on a short capsule versus plates that run past the tail. Beside the merged Scout, the pod stays the short finned capsule and the T'Khasi stays the crescent. The Scout stays the long needle with canards. Those rows, plus the pod against the Merchant and the Freighter, and the T'Khasi against those two, are the [wave read](cockpit-ship-stage-p1b-batch1-remainder.md#wave-read-test) this cut can judge. The Merchant and the Freighter stay as their cuts left them. An X of nacelles is the Constellation, and two prongs ahead of the nose are the Havoc. Both are later cuts. Neither grows on the T'Khasi.

Section token stays `round` on the pod, the T'Khasi, and the Scout. This cut adds no fourth section.

## Head-on

One existing clip per hull. Side camera and head-on camera. The kit still reads in both. A part that only exists in the three-quarter view is not a signature. `holdWarp` still pauses a frame.

Escape Pod. One round port is the face, `#55ffff`. Two stub fins are the side masses, large next to a short body. One engine mouth sits low, inside the fins. A canard pair, a crescent, a cheek plate, a keel, a tower, or a dish fails the frame.

T'Khasi Orion. Two plate tips are the widest points. The body between them is a thin core. The tips wear `#ff6d8a` on the edge. Two engine mouths sit low, inside the plate span. A thin cross with canard blades, a round port as the face, stub fins, a cheek plate, a tower, a dish, an X of nacelles, or a split prow fails the frame.

## Scout re-shot

The mesh stays the Scout Marauder cut 1 lands. This cut leaves those faces where cut 1 put them, and it leaves the canards where that cut put them. The re-shot is a read, so the pod and the T'Khasi have their pair on screen. Same pose, sizes, and shield pair. Once beside the pod, and once beside the T'Khasi, at ~140px and at the hero crop. The numbered checks are the remainder's [re-shot list](cockpit-ship-stage-p1b-batch1-remainder.md#scout-marauder--re-shot-not-a-new-mesh).

The canards still break the nose outline. The body still reads as a line. The tail fins still show, and they are smaller than the canards. Beside the pod, the hull stays the long needle. Beside the T'Khasi, the blades stay canards near the nose. Accent `#5dffc8` at shields 0.

## Accent

Dark blue-grey metal on both hulls. The accent is a stripe, a canopy edge, and the kit, not a tint that replaces the metal. On the pod the port is the glass, and it carries the cyan. The fins and the capsule stay dark metal. On the T'Khasi the plate bodies stay dark metal and the edges carry the accent. Idle engines are a short cyan-white cone. A fitted TransWarp drive (`ship.transwarp.fitted`) turns that cone magenta and nothing else. Neither hull is on `SHIP_TW_CHART_RANGE`. The pass pose is idle cyan-white cones. A drive recolor is the inherited rule, and it is not a signature of this cut.

| | Escape Pod | T'Khasi Orion |
| --- | --- | --- |
| Accent | `#55ffff` | `#ff6d8a` |
| Kit | `fins` | `swept` |
| Shields full | Cyan on the nose port. A stripe, where the shared stripe is drawn, is the same cyan. | Plate edges and stripe `#ff6d8a` |
| Shields 0 | Bubble absent. Scars may show. The port is still `#55ffff`. | Bubble absent. Scars may show. The edges and the stripe are still `#ff6d8a`. |

A full red body fails at either shield value. A full cyan body on the pod fails. A full body in `#ff6d8a` on the T'Khasi fails. Empty shields are scars and a missing bubble. The class accent stays that colour. Mint `#5dffc8` is the Scout. It stays on the Scout.

## Marker ring

The count is the [marker-math](cockpit-ship-stage-marker-math.md#formula) formula. `n < 1` draws nothing. Otherwise `max(1, ceil(n / 100))`. Each marker stands for 100 fighters. The last marker may be a partial hundred. It gets no numeral of its own. The stat block keeps today's words and order, and the exact bay. The visible legend is `each marker = 100 fighters`. The count is the onboard bay, not fighters per attack.

One chevron dart, fill `#ff2a2a`, stroke `#ff8888`. The dart is a marker, not a second ship mesh. Markers yaw with the hull and read as escorts.

The ring sits outside the hull body. Innermost world radius is the bounding sphere of every face, kit included, plus a gap. On the three-quarter pose and in the head-on clip, no marker's screen box intersects the hull silhouette.

Escape Pod. The sphere includes the loft, both fins, the nose port, and the one engine. The fins set the sides. The capsule, once it is almost as tall as it is long, sets the top. A ring that clears the capsule and clips a fin fails. A borrowed Merchant ring (~93) or the old `fighterSlots` start of 56 leaves the lifeboat in a hole and fails. Cap is 50 fighters, 1 marker, on both rosters. There is no second marker on this hull. Fighters per attack of 10 is still that one dart.

T'Khasi Orion. The sphere includes the loft, both plates, the canopy, and both engines. The plates set the beam, and the run past the tail sets the stern. A ring sized to the tube clips a plate and fails. Cap is 750 fighters, 8 markers, on both rosters. The spec and the live table both store 750. A printed 760 does not add a ninth dart. Fighters per attack of 250 would draw 3 darts. The checklist uses the bay. Eight markers is a handful of darts on the plate sphere. The formula has no silent cap. The grouping fix in the render memo is the remedy if one is needed.

The Scout re-shot keeps the cut-1 caps: base 150 is 2 markers, live 250 is 3. Both last darts are partial hundreds and get no numeral. The ring radius does not change between those caps. This cut repeats the pair shots. It leaves the Scout's ring where cut 1 put it.

| Fighters `n` | Markers | What the ring shows |
| --- | --- | --- |
| 0 | 0 | No darts. |
| 1–49 | 1 | One dart. A partial hundred. No numeral. |
| 50 | 1 | Escape Pod cap, both rosters. Still one dart. Screenshot case. Outside the fins and the port. |

| Fighters `n` | Markers | What the ring shows |
| --- | --- | --- |
| 0 | 0 | No darts. |
| 1–99 | 1 | One dart. A partial hundred. No numeral. |
| 100 | 1 | Still one dart. `ceil(100 / 100)` is 1. |
| 101–200 | 2 | The second dart is a partial hundred until 200. No numeral. |
| 701–749 | 8 | Already 8. The last dart is a partial hundred. No numeral. |
| 750 | 8 | T'Khasi cap, both rosters. The eighth dart is a partial hundred. No numeral. Screenshot case. Outside the plate tips. |

## CU-seat and reduced motion

`prefers-reduced-motion`, a phone (`max-width: 700px`), and `body.cu-seat` hold the canonical still. That still is the three-quarter pose above. No loop on those three. The turn is not blocked. A still draws the marker count and holds the pose. Marker-math keeps the same stills: the count in the table is drawn, and the orbit does not run.

## Rest of the pass list

- `web/hull-meshes.js` under 40 KB gzipped, cumulative with the P1 faces, cut 1, and cut 2. The [P1 pass](cockpit-ship-stage-p1-pass.md) recorded 8,673 bytes gzipped (level 9) before those later faces. Record this cut's face counts and the gzip size of the module after the faces land. The cumulative file stays under 40 KB. `tests/test_cockpit_ship_stage_p1.py` already asserts `gzip < 40 * 1024`.
- Screenshots of both new hulls, name covered, at ~140px and at the hero crop, shields empty and shields full, plus the 1-marker and 8-marker cases. The Scout re-shot beside each, at marker caps 2 and 3. Side camera and head-on camera. `holdWarp` still pauses a frame. The hauler wave waits for these screenshots.
- When 1,000 separate SVG paths miss the frame, the fix is one group updated by a transform, or one canvas layer for markers only. The count stays `ceil(n / 100)`. Three.js waits for Hold-WebGL below. This cut's caps are 1 and 8. They do not replace the P1 measurement of a drift frame at 500 markers and a static frame at 1,000.

## Files the product PR may touch

After cut 1 and cut 2 have merged. This checklist adds no paths of its own.

May touch:

- `web/hull-meshes.js`, for `escape_pod` and `tkhasi_orion` faces. Faces land there only, so a clip that calls `buildHullFaces` picks them up.
- The ship-view test that still pins a `fleet-glass-v1` face count for those two keys, in the same change. That pin is `FLEET_GLASS` in `tests/test_cockpit_ship_stage_p1.py` (`test_other_fifteen_hulls_keep_fleet_glass_points`). Pins this cut does not own stay as the merged tip left them. Merchant stays at 217 faces and Imperial at 311. The 200-cap legend stays `each marker = 100 fighters` in that file and in `tests/test_ship_view_visual_v1.py`. Those assertions already moved with the P1 spike. Update them in this change only if this cut breaks them. No engine change, no new action, no new event field.

Leave alone:

- Scout Marauder, Merchant Freighter, BattleShip, Corporate FlagShip, Merchant Cruiser, and Imperial StarShip faces.
- The other nine hulls. A second hull file. A second renderer, unless the block below is Hold-WebGL.
- The hauler wave and every later batch. Each starts from the merge of the cut ahead of it.
- [P0, Out of scope](cockpit-ship-stage-p0.md). Ferrengi hulls. New engine events, new `EVENT_FACTS` keys, and new actions. Copying or tracing EIS, Markham, or ANSI ship art.
- [Render memo, What this spike is not](cockpit-ship-stage-p0-render.md). A new engine field. A new event. A change to warp-clip JSON cameras. A layout split (that is P3). A deletion of `#viewport` (that is P2). A trace of any classic outline.
- `COMMANDER_NEXT.md`, `GAP_MAP.md`, the sheet index, and the other ship-stage sheets.

## Commander decision

Reply with one of these three. Pass means every item on the bar above holds, including the batch-1 remainder checklists for these two hulls and the Scout re-shot. Hold-WebGL means one off-ramp condition on the P1 acceptance is true for this cut. Any other miss is Fail.

Hold-WebGL stays closed. The [P1 pass](cockpit-ship-stage-p1-pass.md) closed it. This cut does not reopen it on its own.

### Pass

Both hulls pass the three-quarter and head-on reads, at ~140px and at the hero crop, at shields 0 and shields full. The Escape Pod reads as the lifeboat: stub fins, and a round port that is still `#55ffff` at shields 0. The T'Khasi reads as the crescent: plate edges that are still `#ff6d8a` at shields 0. They stay apart from each other and from the Scout re-shot. Marker rows match the formula, including the pod at 1 and the T'Khasi at 8, and no marker box cuts the silhouette. CU-seat, reduced motion, and the phone still stay on the canonical still. The cumulative gzip size is under 40 KB, and the face counts are recorded. The fleet-glass pins for these two keys moved in that same change. Stay on the shared SVG (`buildHullFaces` / `projectFace`). WebGL stays the closed off-ramp. The other nine wait.

### Fail

A pass item is missed, and none of the three off-ramp conditions are true. This cut has not cleared the bar. Escape Pod and T'Khasi Orion stay on `fleet-glass-v1` until a later change on the same path passes. The next edit stays on `buildHullFaces` / `projectFace`. The count stays `max(1, ceil(n / 100))` when `n ≥ 1`. Cut 1 and cut 2, once merged, stay merged.

### Hold-WebGL

Stays closed unless this cut fails one of the same three off-ramps as [P1 acceptance](cockpit-ship-stage-p1-acceptance.md#hold-webgl):

- The read still fails at hero size. On this cut, that is the Escape Pod and the T'Khasi Orion.
- Drift of the Imperial plus 500 markers, or a static frame of 1,000 markers, cannot hold a 16 ms update on a mid laptop and a phone-class CPU.
- A planet disc and a warp camera cannot be expressed in the SVG the clips already animate.

Open a WebGL spike only after this art pass, and only when one of those is true. That spike consumes the face list from `buildHullFaces`. It does not introduce a second hull file. Warp clips stay SVG until their own note.
