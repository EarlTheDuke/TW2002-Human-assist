# P1b acceptance — Scout Marauder and Merchant Freighter

Read-test for the product cut. Docs only. Tip surveyed: `feature/grokbot-player` @ `3a688977`.

Taken from these sheets, which this file does not replace:

- [P1 acceptance](cockpit-ship-stage-p1-acceptance.md) — the Pass / Fail / Hold-WebGL shape this cut mirrors.
- [P1 pass](cockpit-ship-stage-p1-pass.md) — the bar Merchant Cruiser and Imperial StarShip already cleared. WebGL stays the closed off-ramp.
- [Next hulls](cockpit-ship-stage-p1b-next-hulls.md) — the mesh contract for this pair. Canards, cheeks, accents, and the numbered checks live there.
- [Four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) — product order. This sheet is cut 1. BattleShip and Corporate FlagShip are cut 2.
- [Fighter marker math](cockpit-ship-stage-marker-math.md) — the shared 100:1 count.

Scope is Scout Marauder (`scout_marauder`) and Merchant Freighter (`merchant_freighter`). One shared mesh, shaded SVG, through `buildHullFaces` / `projectFace`. Looks stay on the next-hulls contract. Merchant Cruiser and Imperial StarShip stay as the P1 pass left them. BattleShip, Corporate FlagShip, and the other hulls stay on `fleet-glass-v1`.

The [P1 pass](cockpit-ship-stage-p1-pass.md) already cleared this bar for the Merchant and the Imperial, on the shared SVG path (`#215`, `9d29349a`). Gzip there is 8,673 bytes (level 9). Drift at 500 markers and a static frame at 1,000 markers both held 16 ms. Hold-WebGL stays closed unless this cut fails one of the same three off-ramps.

Cover the name plate for every read below. Look at the current ~140px panel and at a hero crop about 55% of the deck. The crop is a read of the mesh. The layout split stays P3.

The held three-quarter pose is yaw `0.82`, pitch `0.5`, which `shipPose` already uses when motion is held ([FX sheet](cockpit-ship-stage-p0-fx.md)).

## Three-quarter

Pose: yaw `0.82`, pitch `0.5`. Repeat at shields 0 and shields full, at both sizes. The numbered checks are the next-hulls three-quarter lists for these two hulls.

Scout Marauder. A fast needle. Section `round`. The longest length-to-beam in the fleet, canards near the nose, small fins at the tail, almost no beam. The canards break the nose outline. The tail fins show, and they are smaller than the canards. The body reads as a line. Kit: `canards`. A reader says scout. Against the Merchant the P1 pass already cleared, the pair is needle-and-canards versus keel-and-pods.

Merchant Freighter. A fast wide trader. Section `box`, and flat. A short body, a broad cargo face, two large engines inside the cheek outline. The cheeks break both sides. Kit: `cheeks`. A reader says freighter. Against that same Merchant, the pair is wide cheeks versus a deep keel. A long deck fails this read. That deck is the CargoTran, and the CargoTran is a later cut.

With the name covered, a reader says scout for the Scout and freighter for the Freighter. Inside this cut the pair is a long thin cross versus a short broad face.

## Head-on

One existing clip per hull. Side camera and head-on camera. The kit still reads in both. A part that only exists in the three-quarter view is not a signature. `holdWarp` still pauses a frame. The head-on camera is the warp clip camera `headon`. The numbered checks are the next-hulls head-on lists.

Scout. The body is a thin cross. Two canard tips, one each side, are the widest points. Two small engine mouths sit inside that span. A tower, a turret pair, a square of bells, or a hoop fails the frame.

Freighter. A broad face. The cheeks are the outer silhouette, almost as wide as the ship is long in the other view. Two large engine mouths sit inside the cheeks. The face stays a freighter when the Scout's thin cross is on the screen next to it, and when the Merchant's keel is on the screen next to it.

## Accent

Dark blue-grey metal on both hulls. The accent is a stripe, a canopy edge, and the kit. Canopy glass is a cool white mixed with the accent. Port glass on the Freighter is a dim warm white. The cyan stays on the cheek rims and the stripe. Idle engines are a short cyan-white cone. A fitted TransWarp drive (`ship.transwarp.fitted`) turns that cone magenta and nothing else. Neither hull is on `SHIP_TW_CHART_RANGE`.

| | Scout Marauder | Merchant Freighter |
| --- | --- | --- |
| Accent | `#5dffc8` | `#7af0ff` |
| Kit | `canards` (edges, tail-fin edge, stripe) | `cheeks` (rims and stripe) |
| Shields full | Mint on the canard edges, the tail-fin edge, and the stripe | Cyan on the cheek rims and the stripe |
| Shields 0 | Bubble absent. Scars may show. The mint is still `#5dffc8`. | Bubble absent. Scars may show. The cyan is still `#7af0ff`. |

A full red body fails at either shield value. Empty shields are scars and a missing bubble. The class accent stays that colour.

## Marker ring

The count is the [marker-math](cockpit-ship-stage-marker-math.md) sheet. Visual markers are `max(1, ceil(n / 100))` when `n ≥ 1`. `n < 1` draws nothing. Each marker stands for 100 fighters. The last marker may be a partial hundred. It gets no numeral of its own. The stat block keeps today's words and order, and the exact bay. The visible legend is `each marker = 100 fighters`. Corner clusters and `FIGHTER_EXACT_CAP` stay retired, as the P1 pass left them.

One chevron dart, fill `#ff2a2a`, stroke `#ff8888`. The dart is a marker, not a second ship mesh.

The ring sits outside the hull body. Innermost world radius is the bounding sphere of every face, kit included, plus a gap. On this three-quarter view, and in the head-on clip, no marker's screen box intersects the hull silhouette. Markers yaw with the hull and read as escorts.

The Scout's canards set the beam. A ring sized from the tube clips them and fails. The sphere includes the loft, both canards, both tail fins, and both engines. The Freighter's cheeks set the beam. A ring sized from the centerline loft lands on the cheeks and fails. The sphere includes the loft, both cheeks, and both engines. Ticks on the hull fail this read. Radius 56, the `fighterSlots` start P1 measured inside the Merchant and the Imperial, stays retired. On these two hulls the kit sets the sphere: canards for the Scout, cheeks for the Freighter.

`ceil(100 / 100)` is 1, so a full hundred is still one marker. The formula has no silent cap. The 25-marker, 500-marker, and 1,000-marker cases stay the measurements on the P1 pass. This cut shows its own caps.

Scout. The live roster moves the fighter cap. Base `SHIP_SPECS_TW2002` is 150 fighters. Live `SHIP_ROSTER_LIVE_TABLE` is 250. Pass both caps. The ring radius does not change between them. Only the count does. Marker-math calls this the one cap that moves a count between tables.

| Fighters `n` | Markers | What the ring shows |
| --- | --- | --- |
| 0 | 0 | No darts. |
| 1–100 | 1 | One dart. A partial hundred through 99. At 100, still one dart. No numeral on the dart. |
| 150 | 2 | Base cap. The second dart is a partial hundred. No numeral. |
| 250 | 3 | Live cap. The third dart is a partial hundred. No numeral. |

Freighter. The fighter cap is 300 on both rosters, so the escort count at the cap is 3 on both. The live grant is 30 holds against a ceiling of 65. The cheeks stay the size on the next-hulls contract either way.

| Fighters `n` | Markers | What the ring shows |
| --- | --- | --- |
| 0 | 0 | No darts. |
| 1–100 | 1 | One dart. A partial hundred through 99. At 100, still one dart. |
| 101–200 | 2 | The second dart is a partial hundred until 200. No numeral. |
| 300 | 3 | Cap, both rosters. An exact three hundred. |

## CU-seat and reduced motion

`prefers-reduced-motion`, a phone (`max-width: 700px`), and `body.cu-seat` hold the canonical still. That still is the three-quarter pose above. No loop on those three. The turn is not blocked. Marker-math keeps the same stills: the count in the table is drawn, and the orbit does not run.

## Rest of the pass list

The four-hull build's per-hull acceptance is the bar, on top of the render memo lines the P1 pass already cleared for the Merchant and the Imperial:

- Read at ~140px and at a hero crop about 55% of the deck. Name plate covered. Three-quarter and head-on. Shields 0 and shields full. A reader names the job.
- Markers 100:1, outside the hull, as above.
- Shields empty keeps the accent, as above.
- Gzip. `web/hull-meshes.js` stays under 40 KB gzipped. The budget is cumulative across cuts. P1 left the file at 8,673 bytes gzipped (level 9). This cut adds the Scout and the Freighter on that same file. Record the new gzip size and the face counts with the cut. The cumulative file still sits under 40 KB. `tests/test_cockpit_ship_stage_p1.py` already asserts `gzip < 40 * 1024`.
- Frame time. The recorded bar stays the P1 pass: a drift of 500 markers and a static frame of 1,000 markers, both under 16 ms. This cut's own clouds are 2 and 3 markers. A miss of that 16 ms bar is the off-ramp below. When 1,000 separate SVG paths miss the frame, the fix is one group updated by a transform, or one canvas layer for markers only. The count stays `ceil(n / 100)`. Three.js waits for Hold-WebGL.
- Tests, in the same change as the faces. `tests/test_cockpit_ship_stage_p1.py` pins a `fleet-glass-v1` face count for `scout_marauder` and `merchant_freighter` in `FLEET_GLASS` (`test_other_fifteen_hulls_keep_fleet_glass_points`). Those two pins update with this cut. The other thirteen pins stay. The Merchant stays at 217 faces and the Imperial at 311. The 200-cap legend stays retired: `each marker = 100 fighters` remains the assertion in that file and in `tests/test_ship_view_visual_v1.py`. No engine change, no new action, no new event field.
- Side clip, `holdWarp`, phone still, reduced-motion still, `body.cu-seat` still, legend `each marker = 100 fighters`, and the exact bay on the stat line.
- Screenshots of both hulls, shields empty and shields full, name covered, at ~140px and at the hero crop, plus the cap-marker cases (Scout at 2 and at 3, Freighter at 3), before BattleShip and Corporate FlagShip leave `fleet-glass-v1`.

## Files the product PR may touch

The file boundary is already in the P0 pack, the render memo, and the four-hull build. This checklist adds no paths.

May touch:

- `web/hull-meshes.js`, for these two hulls' faces. Cut 1 holds that file. Faces land there only, so a clip that calls `buildHullFaces` picks them up. Merchant Cruiser and Imperial StarShip faces stay as the P1 pass left them.
- The tests named above, in the same change.

Leave alone. Use these lists as written:

- [P0, Out of scope](cockpit-ship-stage-p0.md). Ferrengi hulls. New engine events, new `EVENT_FACTS` keys, and new actions. Copying or tracing EIS, Markham, or ANSI ship art.
- [Render memo, What this spike is not](cockpit-ship-stage-p0-render.md). A new engine field. A new event. A change to warp-clip JSON cameras. A layout split (that is P3). A deletion of `#viewport` (that is P2). A trace of any classic outline.
- BattleShip, Corporate FlagShip, and every other hull still on `fleet-glass-v1`. A second hull file. A second renderer, unless the block below is Hold-WebGL.
- Cuts 2, 3, and 4 on the [four-hull build](cockpit-ship-stage-p1b-four-hull-build.md). Each starts from the merge of the cut ahead of it.

## Commander decision

Reply with one of these three. Pass means every item in this sheet holds. Hold-WebGL means one of the same three off-ramp conditions on the [P1 acceptance](cockpit-ship-stage-p1-acceptance.md) is true for this cut. Any other miss is Fail.

The P1 pass left Hold-WebGL closed. Reopening it takes one of the three off-ramps below.

**Pass.** The Scout Marauder and Merchant Freighter read-test passed on PR #238 (`54051577`), on the parent path of tip `feature/grokbot-player` @ `0ab0084f`. Meshes, stills, and tests landed. WebGL stays off. `web/hull-meshes.js` is 9,933 bytes gzipped (level 9). BattleShip, Corporate FlagShip, and the other hulls stay on `fleet-glass-v1`.

### Pass

Both hulls pass the three-quarter and head-on reads, at ~140px and at the hero crop, at shields 0 and shields full. The Scout reads as the needle (canards). The Freighter reads as the wide trader (cheeks). They stay apart from each other, and each stays apart from the Merchant the P1 pass already cleared. The marker rows match the formula, including Scout at 2 and at 3 and Freighter at 3, and no marker box cuts the silhouette. Shields empty keeps `#5dffc8` and `#7af0ff`. CU-seat, reduced motion, and the phone still stay on the canonical still. The cumulative mesh file is under 40 KB gzipped, with face counts recorded. The named tests move in the same change. Stay on the shared SVG (`buildHullFaces` / `projectFace`). WebGL stays the closed off-ramp. BattleShip and Corporate FlagShip wait for the screenshots named above.

### Fail

A pass item is missed, and none of the three off-ramp conditions are true. This cut has not cleared the bar. BattleShip, Corporate FlagShip, and the other hulls stay on `fleet-glass-v1`. The next edit stays on `buildHullFaces` / `projectFace`. A missed 1,000-marker frame uses the group transform or the markers-only canvas layer from the render memo. The count stays `max(1, ceil(n / 100))` when `n ≥ 1`. Hold-WebGL stays closed.

### Hold-WebGL

Closed. It opens only after this art pass, and only when this cut fails one of the same three off-ramps:

- The Scout and the Freighter still fail the read test at hero size.
- Drift of the Imperial plus 500 markers, or a static frame of 1,000 markers, cannot hold a 16 ms update on a mid laptop and a phone-class CPU.
- A planet disc and a warp camera cannot be expressed in the SVG the clips already animate.

That spike consumes the face list from `buildHullFaces`. It does not introduce a second hull file. Warp clips stay SVG until their own note. A miss that is not one of those three is Fail, and the next edit stays on the shared SVG.
