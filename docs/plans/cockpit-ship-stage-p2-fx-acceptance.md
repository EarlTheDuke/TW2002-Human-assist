# P2 FX acceptance — ship stage

Commander read-test for the in-flight P2 FX product wire. Docs only. This sheet records the bar. It does not stamp Pass. It does not implement the wire. WebGL stays off.

Tip surveyed: `feature/grokbot-player` @ `d5c1720b` (#417). #417 (`d5c1720b`) refreshed [P3 readiness](cockpit-ship-stage-p3-readiness.md) onto `8a88f671` (#416). The P3 gate stays closed. This sheet does not edit that note. #416 (`8a88f671`) records the P2 wire gate OPEN on [P2 readiness](cockpit-ship-stage-p2-readiness.md). Commander call. The product wire Cur is in flight separately. The wire product has not landed. This sheet is the read Ben uses when that product lands. It is not the launch.

Sources this file does not replace:

- [P2 wire](cockpit-ship-stage-p2-wire.md) — the product checklist. Events, precedence, nodes, and the files the product PR may edit live there.
- [FX sheet](cockpit-ship-stage-p0-fx.md) — the six states and the pictures.
- [P0 pack](cockpit-ship-stage-p0.md) — the P2 done-when list.
- [P2 FX sample](cockpit-ship-stage-p2-fx-sample.md) (#404, `fe296f55`) — research stills of the Merchant tells. The cockpit does not load `samples/p2-fx/`. Those PNGs do not pass this sheet.
- [Marker math](cockpit-ship-stage-marker-math.md) — the shared 100:1 count.
- [P2 readiness](cockpit-ship-stage-p2-readiness.md) — gate OPEN. This sheet does not edit that note.

## Where to look

Look on `/bot?layout=redesign` after the product PR, or at stills shot from that stage. Cover the name plate. The held pose is yaw `0.82`, pitch `0.5`, the pose `shipPose` already uses when motion is held.

The #404 sample stills under `samples/p2-fx/stills/` are the research picture of the tell language on the landed Merchant Cruiser (217 faces, radius 79.03, drawn through `buildHullFaces` / `projectFace`). Use them to recognise the tell. Pass is the same tell on the cockpit stage, on the hull the seat is flying. A sample PNG is not the product still.

P3 owns the 55–60% stage and the end of the `#shipSvg` 140px cap. This read uses the stage the wire leaves. A panel that is still capped is not a miss on this sheet. Variant A (ship `1.5fr` / map `1fr`) waits with the P3 gate.

The seat filter is the wire's filter. A row plays for `ev.actor_id === S.self_id` unless the combat row also names this seat as victim. A history batch paints the resting observation and does not replay the transient.

## Stamp

Not recorded. The wire has not landed. Every look below is the bar. None of them is checked.

## Six states

Precedence when two want the same moment: combat, then warp, then mine-deploy, then planet-land, then port, then idle. States do not stack. Skip dismisses the current transient. Nothing blocks the turn.

| Moment | What the stage shows |
| --- | --- |
| Warp that also detonates mines | The warp, then the short combat flash. The mine-drop meshes stay off that turn. |
| Land that shares a planet fight | The combat flash, then the surface disc. |
| Arrive in a sector with a port | The warp owns the flight. The bay is the held picture after it. |
| Leave that sector | The warp. The gantry is not the flight. |
| `deploy_mines` of kind `armid` or `limpet` | The mine drop, then idle. |
| Atomic mine, event `atomic_detonation` | The combat streak. No sitting mine meshes. |
| `trade` | The bay stays. Opening the trade form does not change FX state. |
| Connect, history batch | Resting observation. No replay. |
| Skip | The current transient is gone. The turn continues. |

`warp_blocked` stays a refusal on the result line. No flight. `ship_transwarp_fuse` is the destroy flash and then the pod. `fed_tow`, `ship_transport`, `planet_transport`, and `deploy_fighters` stay off the stage.

## Fighter markers

The count is the [marker-math](cockpit-ship-stage-marker-math.md) sheet. `n < 1` draws nothing. Otherwise the count is `max(1, ceil(n / 100))`. Each marker stands for 100 fighters. The last marker may be a partial hundred and has no numeral of its own. The bay stays on the readout. The legend is `each marker = 100 fighters`.

One chevron dart, fill `#ff2a2a`, stroke `#ff8888`. The dart is a marker, not a second ship mesh. On the three-quarter still and in the head-on clip, no marker's screen box intersects the hull silhouette. Markers sit outside the hull body, kit included.

The #404 sample measured these bays on the Merchant. They are the read set. Any other bay uses the same formula.

| Bay | Markers | What to see |
| --- | --- | --- |
| 0 | 0 | No darts. Sample still `fighters-0.png`. |
| 50 | 1 | One dart. A partial hundred. No numeral. Sample still `fighters-50.png`. |
| 100 | 1 | Still one dart. `ceil(100 / 100)` is 1. Sample still `fighters-100.png`. |
| 250 | 3 | Three darts. Sample still `fighters-250.png`. |
| 1,000 | 10 | Ten darts, outside the silhouette. Sample still `fighters-1000.png`. |

Live idle orbits the markers. Stills, reduced motion, the phone width (`max-width: 700px`), and `body.cu-seat` draw the count and hold the pose. The orbit does not run on those four.

A ring that favors one side of the canonical view holds when every dart still clears the hull. The sample's open note was that small counts cluster on the upper right, and that ten markers still favor that side. Clearance is the bar. A dart on the skin fails.

## Mine

Event `deploy_mines` for this seat, kind `armid` or `limpet`. Draw `min(qty, 6)` meshes and one numeral for the real `qty`. Armid is a spiked ball. Limpet is a flat disc. Both are dim hazard amber, `#e0b15a` on `#8a5a18`, distinct from the red dart. They sit aft of the hull and clear of the silhouette.

The sample's qty-8 still is the picture: six meshes plus the numeral 8. Stills `mine-armid.png` and `mine-limpet.png`. The drop runs 900 ms. The product hold after that is 1,600 ms, then idle. The sample holds the dropped frame until Skip so a still can be inspected. On the cockpit, the dropped frame shows the meshes and the numeral, and idle returns after the hold.

A mine that reads as part of the hull fails. The sample notes that a sibling group aft of the bells can cross the shield ellipse, and that the product cut chooses whether those faces are depth-sorted. Crossing the ellipse holds when the mines still read aft and clear of the hull.

Kind atomic emits `atomic_detonation` (`qty`, `port_destroyed`). That picture is the battle streak. `deploy_atomic` on a planet is a different verb and stays off this drop.

## Landing

Event `land_planet` for this seat, and only along the path that already sets `surface = true`: the result matches landed and does not match repelled. A refused landing and a planet repel stay in the starfield, with no disc. `seized: true` still lands. Liftoff (`liftoff`, fact `planet_id`) clears the surface, climbs back, and returns to idle. Liftoff does not also warp.

A disc sits behind the hull. Gear-down raises the nose. The sample adds 0.08 to pitch and draws two struts. The disc fades in over 400 ms. Liftoff climbs back over 700 ms. Class colours are the FX sheet. H and C have no still in the manifest. MVP uses these colours and does not wait on bitmaps. An unknown class uses the idle starfield.

| Class | Name | What the disc shows |
| --- | --- | --- |
| M | Earth | Blue limb `#0c3a6e`, green `#1a6b3a`, white cloud band. Terra uses this disc with no claim chrome. Sample still `land-M.png`. |
| K | Desert | Amber `#c47a2a` over rust `#6a3a14`. Sample still `land-K.png`. |
| H | Volcanic | Basalt `#2a1210` with lava cracks `#ff4a1a`. Sample still `land-H.png`. |
| O | Oceanic | Teal water `#0a6e78`, bright rim `#b8fff2`, no continents. Sample still `land-O.png`. |
| L | Mountainous | Grey-violet rock `#6e7380`, snow `#e8eef5`. Sample still `land-L.png`. |
| C | Glacial | Ice `#d7f4ff` over cold blue `#7eb8d4`. Sample still `land-C.png`. |
| U | Gaseous | Banded amber `#c9a24a` and mauve `#6a3a78`. The hull dips into the cloud. The sample dips 10 px. There is no ground line. Sample still `land-U.png`. |

On the gear-down still, markers still clear the silhouette. The sample rebakes slots at the raised pitch and does not re-test drift yaw. This read is the still.

The FX sheet asks for dark engines on the surface. The sample leaves the bells bright, because darkening them is a change to `projectFace`. The wire leaves `web/hull-meshes.js` alone. Bright bells on the land still hold. A projector change is outside this Pass.

## Warp

A real move for this seat plays on the stage. Already live: event `warp` with `facts.from !== facts.to`, and event `autopilot` with `facts.executed` and `facts.hops_done >= 1`. The wire adds `ship_transwarp` (`from !== to`), `planet_transwarp` (`from_sector !== to_sector`), and `retreat` (`from !== to`). `warp_blocked` and `ship_transwarp_fuse` stay out.

`#warpClip` is a descendant of `#ship`, inside `#stageFx`, with the same ids and test ids. `window.__tw2kWarp.hold` still pauses a frame, and the paused frame shows the `buildHullFaces` hull. Cameras stay `side`, `chase`, `headon`, `top`, `gate`. Stars stay `streaks`, `tunnel`, `nebula`, `sparse`, `gate`. Exits stay `jump`, `fade`, `flash`, `fold`, `gate`. Linger stays `WARP_LINGER_MS` (4000). Skip still calls `skipWarp`. The clip returns without awaiting the turn.

The sample's warp still is phase 0.4 of a 2,000 ms cool-white streak (`warp.png`). Fighter markers park at scale 0.45 for the middle of the clip and ease back at the end. The FX sheet's bar is the same idea: markers scaled down or parked so they are not fighting the camera, then the idle pose in the new sector. Every parked marker stays inside the stage frame. The sample notes that scale 0.45 can sit near the top edge of the 400×260 frame. A marker cut by the frame edge fails the warp still.

TransWarp magenta stays `ship.transwarp.fitted` on the hull, not a property of the clip. The Merchant in the sample has no drive fitted, so that plume stays cool white. A fitted drive on the product stage turns the cone magenta and leaves the rest of the tell alone.

## Battle

One language. A white-orange streak across the stage, then the post-combat observation. The sample runs the streak for 450 ms, brightest at the halfway peak (`battle.png`). The shield ellipse flares with that peak when shields were lost. Markers pulse when fighters were lost. The sample pulse peaks at scale 1.35. A still of the peak shows the streak, the flare when shields were lost, and the larger darts when fighters were lost. An exchange with no shield loss and no fighter loss is the streak alone.

Then the hull settles on the post-combat observation. Scars show when shields are under 35% (`shieldRead` `low`). A successful siege then enters the landing disc. A planet repel stays in the starfield. `ship_destroyed` for this seat ends on `paintShipView` of `escape_pod`. The flash does not draw a second hull.

The same streak covers the combat rows the wire names: `combat` (including `vs === "fighter_sector"` and `exchange_kind` `port` / `special_port`), `photon_fired`, `photon_hit`, `mine_detonated`, `atomic_detonation`, `ferrengi_attack`, and `ferrengi_encounter` when this seat is the actor or the victim. A mine detonation is this streak. It is not the drop. A distinct photon bolt is later. Port combat is not a seventh state.

## Port bay

There is no dock event. After a real move, a new observation with `sector.port` holds the bay. Nose slightly up, engines at idle, a plain gantry of two original uprights behind the ship. The sample does not draw the uprights. Pass requires them on the stage. Trade letters stay on the sector report. The stage does not paint BBS versus SSB.

StarDock is the port name matching `/stardock/i`, or sector id 1. The class digit does not make StarDock. `PortClass.STARDOCK` is 8. `stardock_class_label()` can show 9. Follow the name or sector 1.

| Where | Backdrop |
| --- | --- |
| StarDock, by name or sector 1 | Cool white bay `#d7e4f5`, darker pit `#1c2430`. |
| Class 0 | Blue-grey bay `#24344a` on `#121820`. |
| Classes 1–7 and class 9 | One work bay `#3a3428`, warm lamps `#e0b15a`. |

## Idle and the left pane

Idle is the rest after refresh and after every transient ends. `paintShipView` repaints from the observation. Stars are `starfield()` inside `#shipSvg` (`data-testid` `starfield-far`, `starfield-near`). The shield bubble reads `shields / shield_cap`. Empty shields keep the class accent.

`#stageFx` is a sibling of `#shipSvg` inside `#ship`. Transients render there. A transient drawn only inside `#shipSvg` is wiped on the next observation paint, and that fails.

The left viewport has no player-facing job. On the redesign document these nodes are absent: `#viewport`, `#vpScreen`, `#vpStars`, `#sceneStill`, `#vpClip`, `#vpCaption`, `#vpSkip`, `.scan`, `#sceneTag`. The `viewport.js` script tag is gone from `redesign.html`. The file stays. `/bot` and `/bot2` still have their own viewports.

The sample ages a swatch list over 8 seconds (`viewport-aged.png` at 6.4 s, `viewport-gone.png` at 8 s) and keeps a struck label so the still can show the age-out. Pass on the cockpit is the nodes gone. The sector report is the text that remains. It is not that swatch list.

`#sectorText` still resolves, inside a report pane on grid area `view`. The report is readable on its own and does not overlay the hull. These still resolve: `[data-port-class]`, `[data-planet="class"]`, `[data-mines="sector"]`, `[data-navhaz=here]`, `[data-beacon=here]`, `[data-terra=row]`, and the LANDED line `sectorText()` writes. `data-mines="armid"` and `data-mines="limpet"` stay the ship stat bars. `data-mines="form"` stays the mines form.

Live, Stills, and Off sit on `#ship` and still mean animate, canonical still, and no transient. Reduced motion and `?mode=cu` hold the still. One skip on the stage dismisses the current transient.

## What holds without a new picture

These are true on the landed wire, and they are not extra art:

- Each of the six states runs from the event or observation the wire names, for this seat, on the live batch only.
- Merchant and Imperial clips still call `buildHullFaces`. The other hulls are whatever P1b left them. This read does not recut a mesh.
- No new engine field, no new `EVENT_FACTS` key, no new action, no new event.
- `web/hull-meshes.js`, `web/media/warp-clips.json`, `web/bot.html`, `web/bot2.html`, `web/viewport.js`, and `web/media-player.js` stay as the wire left them. Prefer them byte-identical.
- WebGL stays off. A cut that opens the WebGL off-ramp stops this read.

The wire names the redesign tests the product PR updates, and the `#sectorText` tests it leaves alone. This read does not restate that list. Commander looks at the stage.

## Later, and not a miss

Per-class bay dressing. A buy-ship beat. Genesis flash. Citadel geometry. A persistent mine hint in idle. Deploy-fighters as drop language. A different camera per `exchange_kind`. A photon drawn as its own bolt. Quasar or interdict shake. Fedspace tint, navhaz shimmer, cloak dim. File clips (`kind: "file"`). A second renderer. Ferrengi hull art. Copying or tracing EIS, Markham, or ANSI. The P3 layout split. `COMMANDER_NEXT.md` and `GAP_MAP.md`.

## Files this sheet adds

This checklist adds no product paths. The wire already names the files the product PR may edit: `web/redesign.html`, `web/redesign.js`, `web/redesign.css`, and the redesign tests that assert `scene-still` or that `#warpClip` sits inside `#viewport`.

## Commander decision

Reply after the product wire has landed and these looks have been read on the stage or on stills shot from it. Pass means every look in this sheet holds. Any missed look is Fail. Hold-WebGL stays closed. Opening the WebGL off-ramp stops the wire. It is not a third stamp on this sheet.

This file does not contain a Pass sentence. The product Cur is in flight. #404 does not pass the wire. #417 does not pass the wire. The P3 gate stays closed until this read is stamped on the landed product.
