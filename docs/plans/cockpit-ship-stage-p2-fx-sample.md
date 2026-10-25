# P2 FX sample — Merchant Cruiser

Research sample only. The page is `samples/p2-fx/index.html`. The cockpit does not load it. WebGL stays off. This note does not stamp Pass and does not open the P2 gate.

Surveyed on `feature/grokbot-player` @ `0bf683e3` (#402), the batch-5 brick meshes. The sample reads `web/hull-meshes.js` and draws the landed Merchant Cruiser through `buildHullFaces`, `projectFace`, and `escortSlots`. It does not edit that file. On this tip the Merchant is 217 faces and bounding radius 79.03. The hoop-hole spacing added for the Interdictor stays off this hull: that test runs only when the yz cylinder is wider than 80.

Open the file in a browser. Presets are fighter bays 0, 50, 100, 250, and 1000. Tell buttons are Mine, Warp, Land, and Battle. Play runs the timed transient. Skip returns to idle. Live orbit spins the markers at 0.7 rad/s. Still holds yaw 0.82 and pitch 0.5, the canonical pose. Shot URLs (`?shot=fighters-250` and the other names under `samples/p2-fx/stills/`) force Still.

## Markers

`n < 1` draws nothing. Otherwise the count is `max(1, ceil(n / 100))`. Each marker stands for 100 fighters. The last marker may be a partial hundred and has no numeral of its own. The bay stays on the readout. The legend is `each marker = 100 fighters`.

| Bay | Markers asked | Placed | Node bake, median |
| --- | --- | --- | --- |
| 0 | 0 | 0 | 0.00 ms |
| 50 | 1 | 1 | 4.40 ms |
| 100 | 1 | 1 | 0.77 ms |
| 250 | 3 | 3 | 0.62 ms |
| 1,000 | 10 | 10 | 0.70 ms |

The 4.40 ms row is the first silhouette raster in that node run. The later 1-marker bake is 0.77 ms. All five bays placed every marker outside the canonical silhouette. Stills: `samples/p2-fx/stills/fighters-0.png` through `fighters-1000.png`.

A separate probe asked for 1,000 markers at fit 0.72, the stress fit from the P1 spike. That is not the 1,000-fighter bay. Node placed 1,000 in 3.51 ms median (6.02 ms max). Headless Chrome placed 1,000 in 2.0 ms median (2.9 ms max). Numbers are in `samples/p2-fx/perf-node.json` and `samples/p2-fx/perf-browser.json`.

## Tells

All of these sit in the stage SVG with the hull. States replace one another. Nothing blocks the turn.

**Mine.** Qty 8 draws 6 meshes, `min(qty, 6)`, plus one amber numeral for the real qty. Armid is a spiked ball. Limpet is a flat disc. Both are hazard amber, `#e0b15a` on `#8a5a18`, aft of the bells. The drop runs 900 ms. The product hold after that is 1,600 ms, then idle. The sample holds the dropped frame until Skip so the still can be inspected. Stills: `mine-armid.png`, `mine-limpet.png`.

**Warp.** Cool white streaks cross the stage for 2,000 ms. The still is phase 0.4. Fighter markers park at scale 0.45 for the middle of the clip and ease back at the end. The Merchant in this sample has no TransWarp drive fitted, so the plume stays cool white. Still: `warp.png`.

**Landing.** A disc sits behind the hull. Gear-down adds 0.08 to pitch and draws two struts. The disc fades in over 400 ms. Liftoff climbs back over 700 ms and returns to idle. Class colours follow the FX sheet: M Earth, K Desert, H Volcanic, O Oceanic, L Mountainous, C Glacial, U Gaseous. U is banded, and the hull dips 10px into the cloud. Unknown classes are not in the select. Stills: `land-M.png` through `land-U.png`.

**Battle.** One white-orange streak across the stage, 450 ms, brightest at the halfway peak. The shield ellipse flares with that sine. Markers pulse up to scale 1.35 at the same peak. The still is the peak. Still: `battle.png`.

## Left viewport aging

The left list is the pictures the viewport loses: stars, fedspace, nebula, hazard, warp clip, port, StarDock, planet stills, mine still, combat stills. Swatch opacity is `1 - clock / 8000`. At 6.4 s the swatches are at 0.2 (`viewport-aged.png`). At 8 s the swatch is gone and the label reads `aged out` (`viewport-gone.png`). The ship stage keeps the tell. The list is not the sector report.

## Perf

Headless Chrome on this machine, one project of all 217 faces: 0.30 ms median. A 10-marker slot bake: 0.60 ms median. Chrome's timer on that run stepped coarsely. The node figures above are the finer bake samples. Both sit under a 16 ms frame for these counts. The sample draws each marker as its own SVG path, the same choice the P1 spike kept.

## Open questions for the real P2 cut

- The port gantry is on the FX sheet and in the aging list. This sample does not draw the two uprights.
- Small marker counts clear the hull and then cluster on the upper right of the canonical view. Ten markers still favor that side. A full ring may want a different first-shell distribution.
- `projectFace` keeps emissive faces near three quarters of their brightness even at pulse 0. The land stills leave the bells bright. Dark engines need a projector change, which this sample does not make.
- Mines are a sibling group aft of the bells. They can cross the shield ellipse. The product cut has to decide whether they are depth-sorted faces.
- Parked warp markers at scale 0.45 can sit near the top edge of the 400×260 frame.
- Landing rebakes slots at the raised pitch. Drift yaw is not re-tested against the silhouette. Stills hold the canonical camera.
- The mesh module exports `projectFace` and `escortSlots`, not a point projector. The sample repeats the stage camera (origin 200,124, `900 / (430 - z)`). One exported projector would keep FX and the hull on the same math.
- At 8 s the sample keeps a struck label so the still can show the age-out. The product cut should remove the viewport nodes.
- A history batch must not replay FX. This page has no event feed.
- Atomic detonation stays the battle streak, not the mine drop. It is not played here.

## What this sample leaves alone

No edit to the cockpit, the hull meshes, `COMMANDER_NEXT`, the sheet index, readiness, the fleet order, the stills inventory, or the P2 and P3 sheets. No Pass stamp. The P2 gate stays closed. WebGL stays off.
