# P1 spike — Merchant Cruiser and Imperial StarShip

Parent: [cockpit-ship-stage-p0.md](cockpit-ship-stage-p0.md). Renderer stayed on the shared SVG loft. No three.js.

The stills inventory [stills/README.md](stills/README.md) (#344) lists [p1-merchant-imperial](stills/p1-merchant-imperial/) for the Merchant Cruiser and the Imperial StarShip (TBD scaffold, no PNG, does not stamp Pass).

Measured on the spike in `web/hull-meshes.js` (`ship-view-full-v1`, look `fleet-glass-v1`). The other 15 hulls still take the fleet-glass loft.

## Faces and size

| Hull | Faces | Accent faces | Bounding radius | Span (x × y × z) |
| --- | --- | --- | --- | --- |
| Merchant Cruiser | 217 | 41 | 79.0 | 142.6 × 37.0 × 61.5 |
| Imperial StarShip | 311 | 71 | 116.9 | 216.5 × 57.3 × 51.1 |

`web/hull-meshes.js` is 31,075 bytes raw and **8,673 bytes gzipped** (level 9). Budget is 40 KB gzipped.

Stock loadouts: the Imperial is the longest hull (216.5). The Scout Marauder, still fleet-glass, is 201.6 and thinner. Merchant length is 142.6, with the keel and shoulder pods.

Panel fit (`shipFit`): phone static is 0.72. 80 or more markers use 0.76. The Imperial under that uses 0.84 so the bells stay in the 400×260 view. Other hulls stay at 1.12.

## Markers

`escortSlots` bake, canonical yaw 0.82 pitch 0.5. Every slot is outside the bounding sphere. An independent silhouette raster found 0 screen-box hits and 0 clipped boxes.

| Case | Fit | Markers asked | Placed | Bake |
| --- | --- | --- | --- | --- |
| Merchant, 0 | 1.12 | 0 | 0 | 0.1 ms |
| Merchant, 1 | 1.12 | 1 | 1 | 3.1 ms |
| Merchant, 25 | 1.12 | 25 | 25 | 3.1 ms |
| Imperial, 25 | 0.84 | 25 | 25 | 2.9 ms |
| Imperial, 500 | 0.76 | 500 | 500 | 6.3 ms |
| Imperial, 1,000 | 0.72 | 1,000 | 1,000 | 7.5 ms |
| Imperial, 1,000 | 0.76 | 1,000 | 1,000 | 6.0 ms |

## Frame time

Headless Chrome on this VM, one `drawShipFrame`-shaped update of the Imperial (project every face, write polygon attributes, reorder, project each marker, set its transform), then one forced layout. Nine samples after the scene existed. Median / max:

| Frame | Fit | Markers | JS only | JS + layout |
| --- | --- | --- | --- | --- |
| Drift (yaw spin, pitch wobble) | 0.76 | 500 | 2.7 / 8.4 ms | 4.3 / 7.3 ms |
| Static canonical | 0.72 | 1,000 | 2.4 / 7.5 ms | 6.4 / 8.3 ms |
| Static canonical | 0.76 | 1,000 | — | 6.5 / 8.1 ms |

Both sit under the 16 ms bar on this machine, so the markers stay individual SVG paths. Slot bake is not part of the per-frame number; it runs when the bay changes.

## Shields 0

Accent faces skip the damage wash. Visible accent averages, damage 0 and damage 1, were the same: Merchant `[99, 131, 206]` (blue), Imperial `[202, 184, 126]` (gold). Non-accent body at damage 1 averaged Merchant `[46, 58, 74]` and Imperial `[44, 54, 69]`. Scars draw. The bubble is absent at zero shields.
