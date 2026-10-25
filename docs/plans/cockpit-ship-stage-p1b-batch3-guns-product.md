# P1b — Missile Frigate and Havoc GunStar

Parent: [batch 3 guns](cockpit-ship-stage-p1b-batch3.md). Read-test: [batch 3 acceptance](cockpit-ship-stage-p1b-batch3-acceptance.md). Gate: [batch 3 readiness](cockpit-ship-stage-p1b-batch3-readiness.md) (#333). Stills directory: [p1b-batch3-guns](stills/p1b-batch3-guns/). Same path as the [P1 spike](cockpit-ship-stage-p1-spike.md) and the cuts already on `feature/grokbot-player`: `buildHullFaces` / `projectFace` in `web/hull-meshes.js`. No three.js. WebGL stays off.

This sheet is the product stills skeleton for Missile Frigate (`missile_frigate`) and Havoc GunStar (`havoc_gunstar`). It follows the shape of the [hauler stills](cockpit-ship-stage-p1b-batch2-haulers-product.md). It does not stamp Pass. It does not record a face count, a raw byte size, or a gzip size. Every measured cell below is **TBD / awaiting product**. The in-flight product wave fills those cells and drops the PNGs into `docs/plans/stills/p1b-batch3-guns/`. This scaffold ships no PNG. It does not invent a pixel size for a frame that has not been shot.

Opened on `feature/grokbot-player` @ `d07d7492` (#336). This note does not move that tip.

Missile Frigate and Havoc GunStar are the two new meshes. The BattleShip stays the cut-2 mesh. This wave re-shots it. The Imperial stays the mesh the P1 pass left. This wave re-shots it beside the Frigate. Merchant Cruiser, Scout Marauder, Merchant Freighter, Corporate FlagShip, Escape Pod, T'Khasi Orion, CargoTran, Colonial Transport, and Taurean Mule stay on the faces they already had. The other hulls stay on `fleet-glass-v1`.

Panel names stay `Missile Frigate` and `Havoc GunStar`. `SHIP_SPECS_TW2002["havoc_gunstar"]["display_name"]` is `Havoc Gunstar`. The mesh keeps the panel spelling. Section token stays `round` on the Frigate and `hex` on the Havoc. The BattleShip stays `hex`. Kit is `missiles` plus `rails` on the Frigate, and `prongs` on the Havoc. `SHIPS` sets Frigate `detail` to `"rails bridge"` and Havoc `detail` to `"guns bridge"`. The `bridge` token is the shared canopy. On the Havoc the `guns` token does not grow the Imperial barrel path. The prongs win.

Marker counts use `max(1, ceil(n / 100))` when `n ≥ 1`. Missile Frigate cap 5,000 is 50 markers on both rosters. Havoc GunStar cap 10,000 is 100 markers on both rosters. A partial last hundred has no numeral. The legend stays `each marker = 100 fighters`. Those counts are the contract formula. Placement, overlap, and clip counts in the tables below are awaiting product.

Contract accent is `#ffb15a` on the Frigate missile bodies, the rail edge, and the stripe. The noses are a hotter amber than `#ffb15a`. Contract accent is `#ff8844` on the Havoc prong tips and the stripe. The BattleShip re-shot keeps `#c5c8ff` on the turret barrels and the stripe. Measured RGB averages are awaiting product.

## Faces and size

Fill this table from the mesh the product wave lands. Leave a cell TBD when that wave did not measure it.

| Hull | Faces | Accent faces | Bounding radius | Span (x × y × z) |
| --- | --- | --- | --- | --- |
| Missile Frigate | TBD | TBD | TBD | TBD |
| Havoc GunStar | TBD | TBD | TBD | TBD |

`web/hull-meshes.js` raw size is **TBD / awaiting product**. Gzip (level 9) is **TBD / awaiting product**. Budget is 40 KB gzipped. The cumulative file after this wave still has to sit under that budget. This scaffold does not record either byte count.

The Frigate reads as a photon boat: a long slim body, two dorsal missiles on a rail, noses forward, each body larger than the canopy. The Havoc reads as a shield tank and a gunship: a short body, two prongs ahead of the nose, a gap between the tips. Measured spans and radii wait on the product wave. Prior-wave face counts stay on the sheets that measured them. This table does not copy those figures.

Panel fit stays the inherited rule: phone static `0.72`, 80 or more markers `0.76`, Imperial `0.84`, other hulls `1.12`. The Frigate cap is 50 markers. The Havoc cap is 100. The product wave records the fit each still actually used. This scaffold does not choose a new fit.

## Stills

Canonical pose is yaw `0.82`, pitch `0.5`. Head-on is clip camera `headon`. Side is clip camera `side`. The hauler stills sheet records those clip cameras as head-on yaw `-1.35` pitch `0.2`, and side yaw `1.35` pitch `0.18`. Match that pose. Shields full draw the bubble. Shields empty drop the bubble, draw the scar strokes, and run damage `1` through `projectFace`. Accent faces skip that wash. No name plate is drawn.

`#shipSvg` shows this viewBox at `max-height: 140px`. The hero crop is the same viewBox at about 55% of the deck. Phone, `prefers-reduced-motion`, and `body.cu-seat` hold this pose and do not loop. The phone still uses fit `0.72`. Exact pixel width and height of each PNG are **TBD / awaiting product**.

Each row is a file the product wave adds under `docs/plans/stills/p1b-batch3-guns/`. Status stays `awaiting product` until that PNG exists. This scaffold does not embed an image for a file that is not in the tree.

### Missile Frigate

| File | Shot | Status |
| --- | --- | --- |
| `mf-3q-full-140.png` | Three-quarter, shields full, 50 markers, ~140px | awaiting product |
| `mf-3q-empty-140.png` | Three-quarter, shields 0, 50 markers, ~140px | awaiting product |
| `mf-3q-full.png` | Three-quarter, shields full, 50 markers | awaiting product |
| `mf-3q-empty.png` | Three-quarter, shields 0, 50 markers | awaiting product |
| `mf-head.png` | Head-on, shields full. One nose. Two missile bodies above a slim fuselage | awaiting product |
| `mf-head-empty.png` | Head-on, shields 0. Bodies, rail edge, and stripe still `#ffb15a` | awaiting product |
| `mf-side.png` | Side clip. Rail reads as a track under the pair | awaiting product |
| `mf-3q-full-hero.png` | Hero crop, shields full, 50 markers | awaiting product |
| `mf-3q-empty-hero.png` | Hero crop, shields 0, 50 markers | awaiting product |
| `mf-phone.png` | Phone fit `0.72`, same pose, cap bay | awaiting product |

Pass pose for the Frigate is idle cyan-white cones. A fitted drive recolor is the inherited rule. It is not a signature of this hull. This scaffold does not reserve a Frigate TransWarp still.

### Havoc GunStar

Shields 0 and shields full, and TransWarp off and on, are separate slots. Drive off is the idle cyan-white cone. Drive on is `ship.transwarp.fitted`: cones go magenta, prong tips stay flat `#ff8844`.

| File | Shot | Status |
| --- | --- | --- |
| `hv-3q-full-140.png` | Three-quarter, shields full, TransWarp off, 100 markers, ~140px | awaiting product |
| `hv-3q-empty-140.png` | Three-quarter, shields 0, TransWarp off, 100 markers, ~140px | awaiting product |
| `hv-3q-tw-140.png` | Three-quarter, shields full, TransWarp on, 100 markers, ~140px | awaiting product |
| `hv-3q-full.png` | Three-quarter, shields full, TransWarp off, 100 markers | awaiting product |
| `hv-3q-empty.png` | Three-quarter, shields 0, TransWarp off, 100 markers | awaiting product |
| `hv-3q-tw.png` | Three-quarter, shields full, TransWarp on, 100 markers | awaiting product |
| `hv-3q-empty-tw.png` | Three-quarter, shields 0, TransWarp on, 100 markers | awaiting product |
| `hv-head.png` | Head-on, shields full, TransWarp off. Two bright tips and an empty gap | awaiting product |
| `hv-head-empty.png` | Head-on, shields 0, TransWarp off. Tips still `#ff8844` | awaiting product |
| `hv-head-tw.png` | Head-on, shields full, TransWarp on. Tips still `#ff8844` | awaiting product |
| `hv-side.png` | Side clip. Prongs run ahead of the nose | awaiting product |
| `hv-3q-full-hero.png` | Hero crop, shields full, TransWarp off, 100 markers | awaiting product |
| `hv-3q-empty-hero.png` | Hero crop, shields 0, TransWarp off, 100 markers | awaiting product |
| `hv-3q-tw-hero.png` | Hero crop, shields full, TransWarp on, 100 markers | awaiting product |
| `hv-phone.png` | Phone fit `0.72`, same pose, cap bay, TransWarp off | awaiting product |

## Havoc TransWarp

`SHIP_TW_CHART_RANGE` prints 16 hops on the Havoc. With a drive fitted, the cones are magenta and the prong tips stay `#ff8844`. With no drive fitted, the cones stay cyan-white and the tips stay `#ff8844`. The product wave fills both columns from the stills above. This scaffold does not sample a pixel.

| Drive | Cones | Prong tips | Still | Measured cone RGB | Measured tip RGB |
| --- | --- | --- | --- | --- | --- |
| Off | Idle cyan-white | `#ff8844` | `hv-3q-full.png`, `hv-head.png` | TBD | TBD |
| On | Magenta | `#ff8844` | `hv-3q-tw.png`, `hv-head-tw.png` | TBD | TBD |
| Off, shields 0 | Idle cyan-white | `#ff8844` | `hv-3q-empty.png`, `hv-head-empty.png` | TBD | TBD |
| On, shields 0 | Magenta | `#ff8844` | `hv-3q-empty-tw.png` | TBD | TBD |

The Frigate is not on that chart. Its pass pose stays the idle cones in the Frigate table.

## Imperial and BattleShip re-shots

Reads of meshes that have already landed. This wave does not recut them. Pair frames go in the same stills directory. Each file is awaiting product. Name plate covered. Repeat at ~140px and at the hero crop, shields full and shields 0.

Imperial beside the Frigate. The castle and the square of four bells still read. The Imperial forward barrels stay smaller than the Frigate missile bodies. Gold stays the Imperial accent.

| File | Shot | Status |
| --- | --- | --- |
| `pair-mf-imp-3q-140.png` | Frigate and Imperial, three-quarter, shields full, ~140px. Frigate at 50 markers | awaiting product |
| `pair-mf-imp-3q-empty-140.png` | Same pair, shields 0 | awaiting product |
| `pair-mf-imp-head-140.png` | Same pair, head-on, shields full | awaiting product |
| `pair-mf-imp-side-140.png` | Same pair, side clip, shields full | awaiting product |
| `pair-mf-imp-3q-hero.png` | Same pair, hero crop, shields full | awaiting product |

BattleShip beside the Frigate. Turret barrels stay a pair on the wide hex wedge, thinner than the Frigate missiles, sitting on turret bodies. Photons stay 0, so the BattleShip frame has no missile bodies. Cap on the BattleShip is 100 markers.

| File | Shot | Status |
| --- | --- | --- |
| `pair-mf-bs-3q-140.png` | Frigate and BattleShip, three-quarter, shields full, ~140px | awaiting product |
| `pair-mf-bs-3q-empty-140.png` | Same pair, shields 0. BattleShip barrels still `#c5c8ff` | awaiting product |
| `pair-mf-bs-head-140.png` | Same pair, head-on, shields full | awaiting product |
| `pair-mf-bs-side-140.png` | Same pair, side clip, shields full | awaiting product |
| `pair-mf-bs-3q-hero.png` | Same pair, hero crop, shields full | awaiting product |

BattleShip beside the Havoc. Guns stay on the BattleShip's back. No prongs grow ahead of the BattleShip nose. The Havoc gap stays empty. One frame with the Havoc drive off, and one with it on.

| File | Shot | Status |
| --- | --- | --- |
| `pair-hv-bs-3q-140.png` | Havoc and BattleShip, three-quarter, shields full, TransWarp off, ~140px | awaiting product |
| `pair-hv-bs-3q-tw-140.png` | Same pair, shields full, Havoc TransWarp on. Tips still `#ff8844` | awaiting product |
| `pair-hv-bs-3q-empty-140.png` | Same pair, shields 0, TransWarp off | awaiting product |
| `pair-hv-bs-head-140.png` | Same pair, head-on, shields full, TransWarp off | awaiting product |
| `pair-hv-bs-head-tw-140.png` | Same pair, head-on, shields full, Havoc TransWarp on | awaiting product |
| `pair-hv-bs-side-140.png` | Same pair, side clip, shields full, TransWarp off | awaiting product |
| `pair-hv-bs-3q-hero.png` | Same pair, hero crop, shields full, TransWarp off | awaiting product |

Face counts for the Imperial and the BattleShip are not remeasured here. The product wave confirms the earlier pins did not move, then leaves those counts on the sheets that recorded them. This table does not invent a replacement count.

The [wave read](cockpit-ship-stage-p1b-batch3.md#wave-read-test) names more pairs. This scaffold reserves re-shot frames for the Imperial beside the Frigate, and for the BattleShip beside the Frigate and beside the Havoc.

## Markers

`escortSlots` at the canonical pose, the phone fit, head-on, and the side clip. Every placed slot is outside the bounding sphere, kit included. Screen boxes do not hit the silhouette and do not clip the 400×260 frame. **Placed** and **Under / overlap / clipped** are awaiting product. The marker column is the contract formula, not a placement measurement.

Missile Frigate. Cap 5,000 is 50 markers. The missiles set the top of the sphere. A ring sized to the fuselage clips them from the side and fails. Fighters per attack stay 3,000. The checklist uses the bay.

| Case | Markers (formula) | Placed | Under / overlap / clipped |
| --- | --- | --- | --- |
| Bay 0 | 0 | TBD | TBD |
| Bay 1–99 | 1 | TBD | TBD |
| Bay 100 | 1 | TBD | TBD |
| Bay 101–200 | 2 | TBD | TBD |
| Bay 4,900 | 49 | TBD | TBD |
| Bay 4,901–4,999 | 50 | TBD | TBD |
| Bay 5,000 (cap, both rosters) | 50 | TBD | TBD |

Havoc GunStar. Cap 10,000 is 100 markers. The prong tips set the nose of the sphere. A marker in the gap fails. Do not borrow the BattleShip radius. Fighters per attack stay 1,000. The checklist uses the bay.

| Case | Markers (formula) | Placed | Under / overlap / clipped |
| --- | --- | --- | --- |
| Bay 0 | 0 | TBD | TBD |
| Bay 1–99 | 1 | TBD | TBD |
| Bay 100 | 1 | TBD | TBD |
| Bay 101–200 | 2 | TBD | TBD |
| Bay 9,900 | 99 | TBD | TBD |
| Bay 9,901–9,999 | 100 | TBD | TBD |
| Bay 10,000 (cap, both rosters) | 100 | TBD | TBD |

BattleShip re-shot. Cap stays 100 on the merged hull. Placement on this wave's pair frames is awaiting product. This sheet does not publish a new radius.

| Case | Markers (formula) | Placed | Under / overlap / clipped |
| --- | --- | --- | --- |
| Bay 10,000 (re-shot, both rosters) | 100 | TBD | TBD |

Checked poses, once the product wave runs: canonical yaw `0.82` pitch `0.5`, phone fit `0.72`, head-on, and the side clip. Clearance counts at those poses are TBD.

## Frame time

Node bench, same shape as the hauler sheet: one `drawShipFrame`-shaped update, project every face, build the point string, project each marker. Nine samples after four warmups. Median / max. Slot bake is the cost when the bay changes, not part of the frame. Every time below is **TBD / awaiting product**. The bar stays 16 ms. A miss of that bar is the acceptance off-ramp. This scaffold does not record a sample.

| Frame | Fit | Markers | Bake | JS frame |
| --- | --- | --- | --- | --- |
| Missile Frigate, canonical | 1.12 | 50 | TBD | TBD |
| Havoc GunStar, canonical, TransWarp off | 1.12 | 100 | TBD | TBD |
| Havoc GunStar, canonical, TransWarp on | 1.12 | 100 | TBD | TBD |
| Imperial, drift-shaped | 0.76 | 500 | TBD | TBD |
| Imperial, static-shaped | 0.72 | 1,000 | TBD | TBD |

The 500-marker and 1,000-marker rows are the inherited P1 bar, re-run on the file this wave ships. They are not a new Imperial mesh.

## Shields 0 and shields full

Accent fill, averaged over the same cameras at damage 0 and damage 1, is awaiting product. A fitted TransWarp drive on the Havoc is awaiting the same average. Contract colours below are the pass colours. They are not a sampled RGB.

Empty shields leave scars and a missing bubble. The class accent stays. A full red body fails. A full amber body on the Frigate fails. A full orange body on the Havoc fails.

| Hull | Shields | Drive | Contract accent | Accent RGB | Body RGB | Idle plume | Fitted plume |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Missile Frigate | full | idle | `#ffb15a` bodies, rail edge, stripe. Noses hotter amber. Fuselage dark metal | TBD | TBD | TBD | TBD |
| Missile Frigate | 0 | idle | Same `#ffb15a` and hotter noses. Bubble absent | TBD | TBD | TBD | TBD |
| Havoc GunStar | full | off | `#ff8844` tips and stripe. Shafts dark metal | TBD | TBD | TBD | TBD |
| Havoc GunStar | full | on | Tips stay `#ff8844`. Cones magenta | TBD | TBD | TBD | TBD |
| Havoc GunStar | 0 | off | Tips and stripe still `#ff8844`. Bubble absent | TBD | TBD | TBD | TBD |
| Havoc GunStar | 0 | on | Tips stay `#ff8844`. Cones magenta. Bubble absent | TBD | TBD | TBD | TBD |
| BattleShip (re-shot) | 0 and full | idle | `#c5c8ff` barrels and stripe | TBD | TBD | TBD | TBD |
| Imperial StarShip (re-shot) | 0 and full | as the P1 mesh left it | Gold stays the Imperial accent | TBD | TBD | TBD | TBD |

The product wave replaces each TBD with the measured average, or leaves the cell TBD if that camera was not sampled. Flat metal on the accent faces stays `accent` set and `emissive` clear. Gold does not appear on the Frigate or the Havoc. Magenta on a tower is the FlagShip. Magenta on the Havoc is the cones only.
