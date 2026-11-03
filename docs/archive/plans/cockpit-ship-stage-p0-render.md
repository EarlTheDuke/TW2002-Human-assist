# Render decision — ship stage (P0)

Parent: [cockpit-ship-stage-p0.md](cockpit-ship-stage-p0.md).

The inventory of product stills scaffolds under this SVG path decision is [stills/README.md](stills/README.md) (#344).

## Recommendation

Keep one shared mesh, drawn as shaded SVG, and spend the revamp on silhouette, materials, fighter placement, and stage size. Do not move the fleet to three.js or raw WebGL for this revamp. WebGL is the off-ramp if the spike below misses the bar, and that off-ramp still consumes `buildHullFaces` so the warp clips do not grow a second hull.

## What is actually slow and what is actually ugly

`web/hull-meshes.js` is 21,713 bytes, 6,127 bytes gzipped. It already builds faces, sorts them, and shades them in `projectFace` (key light, fill, rim, emissive pulse, shield damage). `web/redesign.js` is the whole cockpit at about 91 KB gzipped, not a renderer budget. The solid path probes WebGL, discards the context, and paints polygons into `#shipSvg`. A missing WebGL context falls back to the NOTE 77 outline even though the outline is also SVG.

Measured on this tip, `buildHullFaces` for a stock loadout:

| Hull | Faces | AABB (x×y×z) | Bounding radius |
| --- | --- | --- | --- |
| Merchant Cruiser | 153 | 162×32×64 | ~93 |
| Imperial StarShip | 241 | 219×51×66 | ~121 |
| Interdictor Cruiser | 215 | 136×75×75 | ~108 |

The Merchant is long, flat, and smooth. That is an art problem. `fighterSlots` starts at radius 56, inside every radius in that table. That is a placement problem. Zero shields run the red wash in `projectFace`. That is a material problem. `#shipSvg` tops out near 140px. That is a layout problem, owned by P3. None of these four are a missing GPU.

The warp library is 17 hulls times 10 SVG variants in `web/media/warp-clips.json`. Cameras, exits, and star fields are CSS on `#warpSvg`. `warp-hull.mjs` imports the same face builder. A second renderer means either the clip and the hero diverge, or 170 clips get rewritten.

NOTE 94 measured a pinned three.js build at about 150 KB gzipped before any hull, against a 300 KB ship-view budget. That figure is the one this pack uses. Half the budget would be gone before the Merchant's keel exists.

## Options

### A. Richer SVG lofts on the current path

More stations, a section that matches the bible (round, hex, box), and kit large enough for the top and head-on cameras. Same `buildHullFaces`, `projectFace`, and `markup` the clips call.

Pros. A few kilobytes today, room under 300 KB for a much denser mesh (a 12-station, 12-sided hull is still a few hundred quads, not a film asset). No shader compile, no context loss when a phone backgrounds the tab. CU screenshots stay DOM. The clip and the panel cannot drift apart. Mobile and reduced-motion already have a still pose.

Cons. Painter's algorithm and per-frame point strings. Fine at a few hundred faces. The risk is the marker count, not the hull: an Interdictor bay is 1,000 darts. A naive per-frame DOM write of 1,000 nodes can miss a phone frame even when the hull is cheap. SVG will not buy normal maps or a real atmosphere.

### B. three.js or raw WebGL for the fleet

Pros. Lights, a ground disc, and a large marker cloud get cheaper once the scene is instanced. A hero camera can move without rewriting point strings.

Cons. About 150 KB gzipped before geometry, plus the context the probe already knows how to lose. CU and software-GL seats screenshot a canvas, which varies by GPU. The warp clips stay SVG unless they move too. Moving them throws out the CSS camera grammar and the `holdWarp` pause path. A Three port of the current four-station loft still looks like the screenshot. The budget is then spent and the art pass is still unpaid.

### C. Hybrid

WebGL for the hero stage, SVG for the clips, both reading `buildHullFaces`.

Pros. The hero can grow post effects later. Clips keep working.

Cons. Two projectors to keep in sync (tone, accent, damage, TransWarp magenta, shield bubble). Two code paths for every bible change. The 300 KB budget still pays the library. CU would be looking at a canvas for the thing the seat is supposed to read. This is the right shape for the off-ramp, and the wrong first build.

## Why A, for this revamp

The quality bar is "what ship is that, without the label, including at zero shields, with escorts outside the body." A meets it if the bible is followed. B and C meet it only after the same art pass, at extra cost, and they split the clip pipeline the cockpit already shares.

P1 also stops treating a failed WebGL probe as a reason to draw the NOTE 77 outline. The outline stays when `TW2KHullMeshes` is missing. That is a cockpit condition, not an engine change.

## Off-ramp

Open a WebGL spike only if, after the art pass below, one of these is true:

- The Merchant and the Imperial still fail the read test at hero size.
- Drift of the Imperial plus 500 markers, or a static frame of 1,000 markers, cannot hold a 16 ms update on a mid laptop and a phone-class CPU.
- A planet disc and a warp camera cannot be expressed in the SVG the clips already animate.

If that spike happens, it consumes the face list from `buildHullFaces`. It does not introduce a second hull file. Warp clips stay SVG until their own note.

## Spike, before the other 15 hulls

Two hulls: Merchant Cruiser and Imperial StarShip. They are the pair in the attached view and the pair a player meets as the starter and the capital. Faces land in `web/hull-meshes.js` only, so a clip that calls `buildHullFaces` picks them up.

Pass, all of these:

1. Name plate covered. At ~140px and at a crop about 55% of the deck, a reader says trader for the Merchant and capital for the Imperial. The keel-and-pods versus castle-and-four-bells test in the bible.
2. Shields 0 and shields full. The accent stays `#7aa2ff` on the Merchant and `#ffe9a0` on the Imperial. Scars are allowed. A full red body is not.
3. Markers. 0 fighters → 0 marks. 30 → 1. 2,500 → 25. 50,000 → 500. A throwaway 1,000-marker ring on the Imperial, standing in for the later Interdictor. Canonical view: no marker screen-box intersects the hull. The ring is outside the bounding sphere.
4. One existing clip per hull, side camera and head-on camera. The kit still reads. `holdWarp` still pauses a frame.
5. Phone still, reduced-motion still, and `body.cu-seat` canonical still. No loop on those three.
6. Size. The mesh module under 40 KB gzipped. Record face counts and the millisecond cost of one drift frame at 500 markers and one static frame at 1,000. If 1,000 separate SVG paths miss the frame, the fix is one group updated by a transform, or one canvas layer for markers only. It is not a silent change to `ceil(n/100)`, and it is not three.js, unless the off-ramp conditions above are met.
7. Stat block unchanged in words and order. Legend is `each marker = 100 fighters`.

Ben sees screenshots of the two hulls, shields empty and shields full, plus the 25-marker and 500-marker cases, before the other 15 leave `fleet-glass-v1`.

## What this spike is not

A new engine field. A new event. A change to warp-clip JSON cameras. A layout split (that is P3). A deletion of `#viewport` (that is P2). A trace of any classic outline.
