# Warp clips

Ten short pictures per hull. The redesign cockpit plays one at random when the ship actually moves. The hull in the picture is the cockpit ship-view mesh for the class you are flying.

See `docs/plans/cockpit-warp-clip-library-v1.md` for the full rules. Short version:

| Path | Role |
|---|---|
| `../media/warp-clips.json` | The ids each hull can roll |
| `../warp-variants.js` | Camera, stars, plume, length |
| `<hull>/01.webm` … `10.webm` | Captured picture. `<hull>` is the `ShipClass` value |
| `manifest.json` | Duration, bytes, and `generated.clips` |
| `generated/<hull>/NN.webm` | Optional later file. A non-empty `generated.clips` row replaces that id |

Id shape: `merchant_cruiser.streak.01`. Numbers run `01` through `10`.

Clip 11 is a new row in `warp-clips.json`. A generated file for an id that is already in the list goes in `generated/` and `manifest.json` → `generated.clips`. Leave `playback` alone: the player only asks for a file when the move succeeded.

```
PYTHONPATH=src python scripts/render_warp_videos.py --only merchant_cruiser:11
```
