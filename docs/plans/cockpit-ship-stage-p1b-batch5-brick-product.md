# P1b — Tholian Sentinel and Interdictor Cruiser

Parent: [batch 5 brick and hoops](cockpit-ship-stage-p1b-batch5.md). Read-test: [batch 5 acceptance](cockpit-ship-stage-p1b-batch5-acceptance.md). Gate: [batch 5 readiness](cockpit-ship-stage-p1b-batch5-readiness.md) (#335). Stills directory: [p1b-batch5-brick](stills/p1b-batch5-brick/). Same path as the [P1 spike](cockpit-ship-stage-p1-spike.md) and the cuts already on `feature/grokbot-player`: `buildHullFaces` / `projectFace` in `web/hull-meshes.js`. No three.js. WebGL stays off.

This sheet is the product stills skeleton for Tholian Sentinel (`tholian_sentinel`) and Interdictor Cruiser (`interdictor_cruiser`). It follows the shape of the [hauler stills](cockpit-ship-stage-p1b-batch2-haulers-product.md). It does not stamp Pass. It does not record a face count, a raw byte size, or a gzip size. Every measured cell below is **TBD / awaiting product**. A later product Cur fills those cells and drops the PNGs into `docs/plans/stills/p1b-batch5-brick/` after batch 3 (Missile Frigate and Havoc GunStar) and batch 4 (Star Master and Constellation) have passed. Until those Pass stamps, both hulls stay on `fleet-glass-v1`. This scaffold ships no PNG. It does not invent a pixel size for a frame that has not been shot.

Opened on `feature/grokbot-player` @ `e3250783` (#338). This note does not move that tip.

Tholian Sentinel and Interdictor Cruiser are the two new meshes. The Colonial Transport stays the hauler mesh. This wave re-shots it beside the Sentinel. The Constellation stays the batch-4 mesh. This wave re-shots it beside the Interdictor. Merchant Cruiser, Imperial StarShip, Scout Marauder, Merchant Freighter, BattleShip, Corporate FlagShip, Escape Pod, T'Khasi Orion, CargoTran, Taurean Mule, Missile Frigate, Havoc GunStar, and Star Master stay on the faces they already had. The other hulls stay on `fleet-glass-v1`.

Panel names stay `Tholian Sentinel` and `Interdictor Cruiser`. `SHIP_SPECS_TW2002` spells both `display_name` values the same way. The mesh keeps those names. Section token stays `box` on the Sentinel and on the Interdictor. This wave adds no fourth section. The hoops are kit, not a section. Kit is `armor` on the Sentinel and `hoop` on the Interdictor. `SHIPS` sets Sentinel `detail` to `"bridge"` and Interdictor `detail` to `"ring bridge"`. The `bridge` token is the shared canopy. On the Interdictor the `ring` token is not a second kit. Build order inside the later product PR is Tholian Sentinel, then Interdictor Cruiser.

Marker counts use `max(1, ceil(n / 100))` when `n ≥ 1`. Tholian Sentinel cap 2,500 is 25 markers on both rosters. Interdictor Cruiser cap 100,000 is 1,000 markers on both rosters. Bay 50 is one marker, a partial hundred, and that dart gets no numeral. Bay 100 is still one marker. The hundred is exact, and the dart still gets no numeral. A partial last hundred has no numeral. The legend stays `each marker = 100 fighters`. Those counts are the contract formula. Placement, overlap, and clip counts in the tables below are awaiting product.

Contract accent is `#62f0c8` on the Sentinel slab faces and the stripe. The fuselage between the slabs stays dark metal. Contract accent is `#ff5cab` on both Interdictor hoop rims and the stripe. The holes stay open and the body stays dark metal. The Colonial re-shot keeps `#7dff7d` on the stripe and the tank rims. The Constellation re-shot keeps `#d0d6ff` on the nacelles and the stripe. Measured RGB averages are awaiting product.

Neither hull is on `SHIP_TW_CHART_RANGE`. The pass pose is idle cyan-white cones. A fitted TransWarp drive (`ship.transwarp.fitted`) turns that cone magenta and nothing else. A drive recolor is the inherited rule, and it is not a signature of this wave. This scaffold does not reserve a TransWarp still for either hull.

## Faces and size

Fill this table from the mesh the product Cur lands. Leave a cell TBD when that wave did not measure it.

| Hull | Faces | Accent faces | Bounding radius | Span (x × y × z) |
| --- | --- | --- | --- | --- |
| Tholian Sentinel | TBD | TBD | TBD | TBD |
| Interdictor Cruiser | TBD | TBD | TBD | TBD |

`web/hull-meshes.js` raw size is **TBD / awaiting product**. Gzip (level 9) is **TBD / awaiting product**. Budget is 40 KB gzipped. The cumulative file after this wave still has to sit under that budget. This scaffold does not record either byte count.

The Sentinel reads as a fortress: the shortest, bluntest brick, armor slabs on both flanks, a head-on view nearly square, a stub nose. The Interdictor reads as the barge: a heavy body inside two hoops, the hoops larger than the hull and the first shape in every camera, head-on a ring with a body in the hole. Measured spans and radii wait on the product Cur. Prior-wave face counts stay on the sheets that measured them. This table does not copy those figures. Fleet order's ~108 on today's Interdictor glass is a floor in the contract, not a radius this sheet records.

Panel fit stays the inherited rule: phone static `0.72`, 80 or more markers `0.76`, Imperial `0.84`, other hulls `1.12`. The Sentinel cap is 25 markers. The Interdictor cap is 1,000. The product Cur records the fit each still actually used. This scaffold does not choose a new fit.

## Stills

Canonical pose is yaw `0.82`, pitch `0.5`. Head-on is clip camera `headon`. Side is clip camera `side`. The hauler stills sheet records those clip cameras as head-on yaw `-1.35` pitch `0.2`, and side yaw `1.35` pitch `0.18`. Match that pose. Shields full draw the bubble. Shields empty drop the bubble, draw the scar strokes, and run damage `1` through `projectFace`. Accent faces skip that wash. No name plate is drawn.

`#shipSvg` shows this viewBox at `max-height: 140px`. The hero crop is the same viewBox at about 55% of the deck. Phone, `prefers-reduced-motion`, and `body.cu-seat` hold this pose and do not loop. The phone still uses fit `0.72`. On the Interdictor those stills draw the 1,000 count. Exact pixel width and height of each PNG are **TBD / awaiting product**.

Each row is a file the product Cur adds under `docs/plans/stills/p1b-batch5-brick/`. Status stays `awaiting product` until that PNG exists. This scaffold does not embed an image for a file that is not in the tree.

### Tholian Sentinel

| File | Shot | Status |
| --- | --- | --- |
| `ts-3q-full-140.png` | Three-quarter, shields full, 25 markers, ~140px. Slabs break both flanks | awaiting product |
| `ts-3q-empty-140.png` | Three-quarter, shields 0, 25 markers, ~140px. Slabs and stripe still `#62f0c8` | awaiting product |
| `ts-3q-full.png` | Three-quarter, shields full, 25 markers | awaiting product |
| `ts-3q-empty.png` | Three-quarter, shields 0, 25 markers | awaiting product |
| `ts-head.png` | Head-on, shields full. Nearly square. Slabs are the sides. Stub nose. Two mouths low, inside the square | awaiting product |
| `ts-head-empty.png` | Head-on, shields 0. Slab faces and stripe still `#62f0c8` | awaiting product |
| `ts-side.png` | Side clip. Short blunt brick. Slabs on both flanks. No belly tanks. No cabin row as the main shape | awaiting product |
| `ts-3q-full-hero.png` | Hero crop, shields full, 25 markers | awaiting product |
| `ts-3q-empty-hero.png` | Hero crop, shields 0, 25 markers | awaiting product |
| `ts-phone.png` | Phone fit `0.72`, same pose, cap bay | awaiting product |

### Interdictor Cruiser

| File | Shot | Status |
| --- | --- | --- |
| `ic-3q-full-140.png` | Three-quarter, shields full, 1,000 markers outside the hoops, ~140px | awaiting product |
| `ic-3q-empty-140.png` | Three-quarter, shields 0, 1,000 markers, ~140px. Rims and stripe still `#ff5cab` | awaiting product |
| `ic-3q-full.png` | Three-quarter, shields full, 1,000 markers outside the hoops | awaiting product |
| `ic-3q-empty.png` | Three-quarter, shields 0, 1,000 markers outside the hoops | awaiting product |
| `ic-head.png` | Head-on, shields full. A ring with a body in the hole. Rims `#ff5cab`. The hole is empty | awaiting product |
| `ic-head-empty.png` | Head-on, shields 0. Rims and stripe still `#ff5cab`. Hole still empty | awaiting product |
| `ic-side.png` | Side clip. Two hoops larger than the body, first shape. Four mouths on the body, inside the hoops | awaiting product |
| `ic-3q-full-hero.png` | Hero crop, shields full, 1,000 markers outside the hoops | awaiting product |
| `ic-3q-empty-hero.png` | Hero crop, shields 0, 1,000 markers outside the hoops | awaiting product |
| `ic-phone.png` | Phone fit `0.72`, same pose, 1,000 darts, no loop | awaiting product |

## Brick and hoops tells

Cover the name plate. The product Cur writes the read from the stills above, at ~140px and at the hero crop, shields 0 and shields full, three-quarter and head-on. This scaffold does not claim a read. A part that only exists in one of those views is not a signature.

| Tell | Contract | Stills read |
| --- | --- | --- |
| Sentinel brick | Short blunt brick. Armor slabs on both flanks. Head-on nearly square, slabs as the sides of that square. Stub nose. Two mouths low, inside the square, inside the slab line. `#62f0c8` on the slab faces and the stripe. Fuselage between the slabs stays dark metal. | TBD |
| Sentinel misses | A full mint body fails. A full red body fails. Canards fail. A wedge nose fails. Belly tanks and a cabin row as the main shape fail. A hoop around the brick fails. | TBD |
| Interdictor hoops | Two hoops larger than the body, first shape from the side, from above, and head-on. Head-on is a ring with a body in the hole. The hole is empty. Both rims `#ff5cab`. Body stays dark metal. Four mouths on the body, inside the ring. | TBD |
| Interdictor misses | A full pink body fails. A full red body fails. A filled disc fails. An X of nacelles fails. A marker in the hole fails. A marker on the skin fails. | TBD |
| Markers | Sentinel cap is 25 darts outside the slabs. Interdictor cap is 1,000 darts outside the hoops. Bay 50 is one dart. Bay 100 is still one dart. | TBD |

## Colonial and Constellation re-shots

Reads of meshes that have already landed. This wave does not recut them. Pair frames go in the same stills directory. Each file is awaiting product. Name plate covered. Repeat at ~140px and at the hero crop, shields full and shields 0.

Colonial Transport beside the Sentinel. The flank still reads as a tall box, high for its length, with a cabin row. Two belly tanks still break the underside. Accent stays `#7dff7d` on the stripe and the tank rims, including at shields 0. The cap is 2 markers. The slabs stay on the Sentinel.

| File | Shot | Status |
| --- | --- | --- |
| `pair-ts-col-3q-140.png` | Sentinel and Colonial, three-quarter, shields full, ~140px. Sentinel at 25 markers. Colonial at 2 | awaiting product |
| `pair-ts-col-3q-empty-140.png` | Same pair, shields 0. Colonial rims still `#7dff7d`. Sentinel slabs still `#62f0c8` | awaiting product |
| `pair-ts-col-head-140.png` | Same pair, head-on, shields full | awaiting product |
| `pair-ts-col-side-140.png` | Same pair, side clip, shields full | awaiting product |
| `pair-ts-col-3q-hero.png` | Same pair, hero crop, shields full | awaiting product |

Constellation beside the Interdictor. Head-on is an X of four nacelles, and little else. The nacelles trail past the tail. Accent stays `#d0d6ff` on the nacelles and the stripe, including at shields 0. The cap is 50 markers. The hoops stay on the Interdictor. The Interdictor frame in the pair still shows 1,000 darts outside the hoops.

| File | Shot | Status |
| --- | --- | --- |
| `pair-ic-con-3q-140.png` | Interdictor and Constellation, three-quarter, shields full, ~140px. Interdictor at 1,000 markers. Constellation at 50 | awaiting product |
| `pair-ic-con-3q-empty-140.png` | Same pair, shields 0. Constellation nacelles still `#d0d6ff`. Interdictor rims still `#ff5cab` | awaiting product |
| `pair-ic-con-head-140.png` | Same pair, head-on, shields full. X versus a ring with a body in the hole | awaiting product |
| `pair-ic-con-side-140.png` | Same pair, side clip, shields full | awaiting product |
| `pair-ic-con-3q-hero.png` | Same pair, hero crop, shields full | awaiting product |

Face counts for the Colonial and the Constellation are not remeasured here. The product Cur confirms the earlier pins did not move, then leaves those counts on the sheets that recorded them. This table does not invent a replacement count.

The [wave read](cockpit-ship-stage-p1b-batch5.md#wave-read-test) names more pairs. This scaffold reserves re-shot frames for the Colonial beside the Sentinel, and for the Constellation beside the Interdictor.

## Markers

`escortSlots` at the canonical pose, the phone fit, head-on, and the side clip. Every placed slot is outside the bounding sphere, kit included. Screen boxes do not hit the silhouette and do not clip the 400×260 frame. **Placed** and **Under / overlap / clipped** are awaiting product. The marker column is the contract formula, not a placement measurement.

Bay 50 and bay 100 are the shared rows on both new hulls. Bay 50 is one dart, a partial hundred, with no numeral. Bay 100 is still one dart. `ceil(100 / 100)` is 1. No numeral. Bays 1–49 and 51–99 match bay 50.

Tholian Sentinel. Cap 2,500 is 25 markers. The slabs set the beam. A length-only radius leaves markers in the slab silhouette. Fighters per attack stay 800. The checklist uses the bay.

| Case | Markers (formula) | Placed | Under / overlap / clipped |
| --- | --- | --- | --- |
| Bay 0 | 0 | TBD | TBD |
| Bay 50 | 1 | TBD | TBD |
| Bay 100 | 1 | TBD | TBD |
| Bay 101–200 | 2 | TBD | TBD |
| Bay 2,400 | 24 | TBD | TBD |
| Bay 2,401–2,499 | 25 | TBD | TBD |
| Bay 2,500 (cap, both rosters) | 25 | TBD | TBD |

Interdictor Cruiser. Cap 100,000 is 1,000 markers. The hoops set the radius, after they have grown until they are the first shape. A marker in the hole fails. A marker on the skin fails. Fighters per attack stay 15,000. The checklist uses the bay. 50,000 is the Imperial cap and draws 500. This bay does not stop there.

| Case | Markers (formula) | Placed | Under / overlap / clipped |
| --- | --- | --- | --- |
| Bay 0 | 0 | TBD | TBD |
| Bay 50 | 1 | TBD | TBD |
| Bay 100 | 1 | TBD | TBD |
| Bay 101–200 | 2 | TBD | TBD |
| Bay 50,000 | 500 | TBD | TBD |
| Bay 99,900 | 999 | TBD | TBD |
| Bay 99,901–99,999 | 1,000 | TBD | TBD |
| Bay 100,000 (cap, both rosters) | 1,000 | TBD | TBD |

Colonial and Constellation re-shots. Caps stay 2 and 50 on the merged hulls. Placement on this wave's pair frames is awaiting product. This sheet does not publish a new radius.

| Case | Markers (formula) | Placed | Under / overlap / clipped |
| --- | --- | --- | --- |
| Colonial, bay 200 (re-shot) | 2 | TBD | TBD |
| Constellation, bay 5,000 (re-shot) | 50 | TBD | TBD |

Checked poses, once the product Cur runs: canonical yaw `0.82` pitch `0.5`, phone fit `0.72`, head-on, and the side clip. Clearance counts at those poses are TBD.

## Frame time

Node bench, same shape as the hauler sheet: one `drawShipFrame`-shaped update, project every face, build the point string, project each marker. Nine samples after four warmups. Median / max. Slot bake is the cost when the bay changes, not part of the frame. Every time below is **TBD / awaiting product**. The bar stays 16 ms. A miss of that bar is the acceptance off-ramp. This scaffold does not record a sample.

| Frame | Fit | Markers | Bake | JS frame |
| --- | --- | --- | --- | --- |
| Tholian Sentinel, canonical | 1.12 | 25 | TBD | TBD |
| Interdictor Cruiser, canonical | 1.12 | 1,000 | TBD | TBD |
| Interdictor Cruiser, drift | 0.76 | 1,000 | TBD | TBD |
| Imperial, drift-shaped | 0.76 | 500 | TBD | TBD |
| Imperial, static-shaped | 0.72 | 1,000 | TBD | TBD |

The Interdictor drift row is this wave's 1,000 on the real hoops. The 500-marker and 1,000-marker Imperial rows are the inherited P1 bar, re-run on the file this wave ships. They are not a new Imperial mesh, and they are not a pass of the Interdictor. When 1,000 separate SVG paths miss the frame, the fix is the spike's grouping: one group moved by a transform, or one canvas layer for markers only. The count stays `ceil(n / 100)`.

## Shields 0 and shields full

Accent fill, averaged over the same cameras at damage 0 and damage 1, is awaiting product. Contract colours below are the pass colours. They are not a sampled RGB.

Empty shields leave scars and a missing bubble. The class accent stays. A full red body fails. A full mint body on the Sentinel fails. A full pink body on the Interdictor fails. A filled disc on the Interdictor fails.

| Hull | Shields | Drive | Contract accent | Accent RGB | Body RGB | Idle plume | Fitted plume |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Tholian Sentinel | full | idle | `#62f0c8` slab faces and stripe. Fuselage dark metal | TBD | TBD | TBD | TBD |
| Tholian Sentinel | 0 | idle | Same `#62f0c8`. Bubble absent | TBD | TBD | TBD | TBD |
| Interdictor Cruiser | full | idle | `#ff5cab` both rims and stripe. Holes open. Body dark metal | TBD | TBD | TBD | TBD |
| Interdictor Cruiser | 0 | idle | Same `#ff5cab`. Bubble absent. Hole empty | TBD | TBD | TBD | TBD |
| Colonial Transport (re-shot) | 0 and full | idle | `#7dff7d` stripe and tank rims | TBD | TBD | TBD | TBD |
| Constellation (re-shot) | 0 and full | idle | `#d0d6ff` nacelles and stripe | TBD | TBD | TBD | TBD |

The product Cur replaces each TBD with the measured average, or leaves the cell TBD if that camera was not sampled. Flat metal on the accent faces stays `accent` set and `emissive` clear. The pass pose is idle cyan-white cones. A fitted drive recolours the cones only, and this scaffold does not reserve a still for that recolor. Colonial green stays on the Colonial. Constellation `#d0d6ff` stays on the nacelles. Gold is the Imperial's accent. Magenta on a tower is the FlagShip. Neither colour appears on these rims.
