# P2 FX sample

Standalone research page for the ship-stage tells. The cockpit does not load this directory. WebGL stays off. The P2 gate stays closed behind the batch-5 brick Pass.

Open `index.html` in a browser. The page reads `web/hull-meshes.js` and draws the landed Merchant Cruiser. Fighter presets are 0, 50, 100, 250, and 1000. Tells are mine, warp, land (planet class), and battle. The left list is the viewport pictures aging out over 8 seconds.

```bash
node samples/p2-fx/self-check.mjs
node samples/p2-fx/render-stills.mjs
```

Stills land in `samples/p2-fx/stills/`. The write-up is `docs/plans/cockpit-ship-stage-p2-fx-sample.md`.
