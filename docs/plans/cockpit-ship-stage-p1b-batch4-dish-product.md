# P1b — Star Master and Constellation

Parent: [batch 4 dish and X](cockpit-ship-stage-p1b-batch4.md). Read-test: [batch 4 acceptance](cockpit-ship-stage-p1b-batch4-acceptance.md). Gate: [batch 4 readiness](cockpit-ship-stage-p1b-batch4-readiness.md) (#334). Stills directory: [p1b-batch4-dish](stills/p1b-batch4-dish/). Same path as the [P1 spike](cockpit-ship-stage-p1-spike.md) and the cuts already on `feature/grokbot-player`: `buildHullFaces` / `projectFace` in `web/hull-meshes.js`. No three.js. WebGL stays off.

This sheet is the product stills skeleton for Star Master (`star_master`) and Constellation (`constellation`). It follows the shape of the [gun stills scaffold](cockpit-ship-stage-p1b-batch3-guns-product.md) and the [hauler stills](cockpit-ship-stage-p1b-batch2-haulers-product.md). It does not stamp Pass. It does not record a face count, a raw byte size, or a gzip size. Every measured cell below is **TBD / awaiting product**. The later product wave, after the batch-3 guns acceptance is stamped Pass, fills those cells and drops the PNGs into `docs/plans/stills/p1b-batch4-dish/`. This scaffold ships no PNG. It does not invent a pixel size for a frame that has not been shot.

Opened on `feature/grokbot-player` @ `d211b4e9` (#337). This note does not move that tip.

Star Master and Constellation are the two new meshes. Build order inside that later PR is Star Master, then Constellation. The Corporate FlagShip stays the cut-2 mesh. This wave re-shots it. The Imperial stays the mesh the P1 pass left. This wave re-shots it beside the dish and beside the X. Merchant Cruiser, Scout Marauder, Merchant Freighter, BattleShip, Escape Pod, T'Khasi Orion, CargoTran, Colonial Transport, and Taurean Mule stay on the faces they already had. Missile Frigate and Havoc GunStar are the batch-3 cut ahead of this wave. Tholian Sentinel and Interdictor Cruiser stay on `fleet-glass-v1`. Until the batch-3 Pass, Star Master and Constellation stay on `fleet-glass-v1` too.

Panel names stay `Star Master` and `Constellation`. The chart spells the second hull Constilation. The FAQ spells the first Starmaster. The mesh keeps the panel spelling. `SHIP_SPECS_TW2002["corporate_flagship"]["display_name"]` is `Corporate Flagship`. The panel spells the second word `FlagShip`. The mesh keeps the panel spelling. Section token stays `round` on the Star Master, the Constellation, and the FlagShip. `SHIPS` sets `kind` to `"arrow"` on the Star Master and `"delta"` on the Constellation. Those tokens are the flat panel outline. They do not change the loft section. Kit is `mast` plus `dish` on the Star Master, and `quad` on the Constellation. The FlagShip re-shot keeps `tower`. `SHIPS` sets Star Master `detail` to `"dish bridge"` and Constellation `detail` to `"nacelles bridge"`. The `bridge` token is the shared canopy. On the Star Master the `dish` token is this kit. On the Constellation the `nacelles` token stays off when `PARTS` is `quad`. The quad wins.

Marker counts use `max(1, ceil(n / 100))` when `n ≥ 1`. Star Master cap 5,000 is 50 markers on both rosters. Constellation cap 5,000 is 50 markers on both rosters. A bay of 100 is still one marker. A partial last hundred has no numeral. The legend stays `each marker = 100 fighters`. Those counts are the contract formula. Placement, overlap, and clip counts in the tables below are awaiting product.

Contract accent is `#9ad7ff` on the Star Master plate and the stripe. The mast and the fuselage stay dark metal. Contract accent is `#d0d6ff` on the Constellation nacelles and the stripe. The fuselage stays dark metal. The FlagShip re-shot keeps `#ff77ff` on the tower's upper step and the stripe. Measured RGB averages are awaiting product.

## Faces and size

Fill this table from the mesh the product wave lands. Leave a cell TBD when that wave did not measure it.

| Hull | Faces | Accent faces | Bounding radius | Span (x × y × z) |
| --- | --- | --- | --- | --- |
| Star Master | TBD | TBD | TBD | TBD |
| Constellation | TBD | TBD | TBD | TBD |

The Star Master reads as a mid combat hull whose whole job is a dish: a modest arrow, a mast, one plate wider than the beam. The Constellation reads as a mid combat hull with four nacelles in an X: a slim body, the X trailing past the tail. Measured spans and radii wait on the product wave. Prior-wave face counts stay on the sheets that measured them. This table does not copy those figures.

Panel fit stays the inherited rule: phone static `0.72`, 80 or more markers `0.76`, Imperial `0.84`, other hulls `1.12`. Both new caps are 50 markers. The product wave records the fit each still actually used. This scaffold does not choose a new fit.

## Gzip

`web/hull-meshes.js` raw size is **TBD / awaiting product**. Gzip (level 9) is **TBD / awaiting product**. Budget is 40 KB gzipped. The cumulative file after this wave still has to sit under that budget. The FlagShip faces stay as cut 2 left them. This wave adds the Star Master and the Constellation when the product PR lands. This scaffold does not record either byte count.

## Stills

Canonical pose is yaw `0.82`, pitch `0.5`. Head-on is clip camera `headon`. Side is clip camera `side`. The hauler stills sheet records those clip cameras as head-on yaw `-1.35` pitch `0.2`, and side yaw `1.35` pitch `0.18`. Match that pose. Shields full draw the bubble. Shields empty drop the bubble, draw the scar strokes, and run damage `1` through `projectFace`. Accent faces skip that wash. No name plate is drawn.

`#shipSvg` shows this viewBox at `max-height: 140px`. The hero crop is the same viewBox at about 55% of the deck. Phone, `prefers-reduced-motion`, and `body.cu-seat` hold this pose and do not loop. The phone still uses fit `0.72`. Exact pixel width and height of each PNG are **TBD / awaiting product**.

Each row is a file the product wave adds under `docs/plans/stills/p1b-batch4-dish/`. Status stays `awaiting product` until that PNG exists. This scaffold does not embed an image for a file that is not in the tree.

### Star Master

| File | Shot | Status |
| --- | --- | --- |
| `sm-3q-full-140.png` | Three-quarter, shields full, 50 markers, ~140px | awaiting product |
| `sm-3q-empty-140.png` | Three-quarter, shields 0, 50 markers, ~140px | awaiting product |
| `sm-3q-full.png` | Three-quarter, shields full, 50 markers | awaiting product |
| `sm-3q-empty.png` | Three-quarter, shields 0, 50 markers | awaiting product |
| `sm-head.png` | Head-on, shields full. One plate on a stick, wider than the beam. Two mouths low, inside the beam | awaiting product |
| `sm-head-empty.png` | Head-on, shields 0. Plate and stripe still `#9ad7ff`. Mast stays dark | awaiting product |
| `sm-side.png` | Side clip. The plate breaks the top edge. The circle reads as a plate on a stick | awaiting product |
| `sm-3q-full-hero.png` | Hero crop, shields full, 50 markers | awaiting product |
| `sm-3q-empty-hero.png` | Hero crop, shields 0, 50 markers | awaiting product |
| `sm-phone.png` | Phone fit `0.72`, same pose, cap bay | awaiting product |

Pass pose for the Star Master is idle cyan-white cones. Neither new hull is on `SHIP_TW_CHART_RANGE`. A fitted drive recolor is the inherited rule. It is not a signature of the dish. This scaffold does not reserve a Star Master TransWarp still. A fitted holo scanner does not add a second plate. This scaffold does not reserve a second-mast still.

### Constellation

| File | Shot | Status |
| --- | --- | --- |
| `con-3q-full-140.png` | Three-quarter, shields full, 50 markers, ~140px | awaiting product |
| `con-3q-empty-140.png` | Three-quarter, shields 0, 50 markers, ~140px | awaiting product |
| `con-3q-full.png` | Three-quarter, shields full, 50 markers | awaiting product |
| `con-3q-empty.png` | Three-quarter, shields 0, 50 markers | awaiting product |
| `con-head.png` | Head-on, shields full. An X and little else. Four mouths off the centerline | awaiting product |
| `con-head-empty.png` | Head-on, shields 0. Nacelles and stripe still `#d0d6ff`. Fuselage stays dark | awaiting product |
| `con-side.png` | Side clip. Four nacelles trail past the tail. The gap between the arms is empty | awaiting product |
| `con-3q-full-hero.png` | Hero crop, shields full, 50 markers | awaiting product |
| `con-3q-empty-hero.png` | Hero crop, shields 0, 50 markers | awaiting product |
| `con-phone.png` | Phone fit `0.72`, same pose, cap bay | awaiting product |

Pass pose for the Constellation is idle cyan-white cones. A fitted drive recolor is the inherited rule. It is not a signature of the X. This scaffold does not reserve a Constellation TransWarp still. A fitted density scanner does not grow a plate. This scaffold does not reserve a dish still on this hull.

## Dish and X tells

Cover the name plate. The product wave confirms these reads on the stills above and on the pair frames below, at ~140px and at the hero crop, shields 0 and shields full. Status stays `awaiting product`. Numbered checks stay on the [batch-4 contract](cockpit-ship-stage-p1b-batch4.md). This table is the stills slot for those checks. It does not record a span.

| Tell | Where it has to read | Status |
| --- | --- | --- |
| Star Master: one plate on one mast, wider than the beam. The top view is a circle on a stick | `sm-3q-full.png`, `sm-3q-empty.png`, `sm-head.png`, `sm-side.png`, hero and ~140px | awaiting product |
| Star Master: two engines sit low, inside the beam, under the dish line | `sm-head.png`, `sm-side.png` | awaiting product |
| Star Master: plate and stripe stay `#9ad7ff` at shields 0. The mast stays dark metal | `sm-3q-empty.png`, `sm-head-empty.png` | awaiting product |
| Star Master: markers sit outside the plate. None ring the mast | Cap 50 on the Star Master marker table | awaiting product |
| Constellation: four nacelles in an X trail past the tail. The gap between the arms is empty | `con-3q-full.png`, `con-3q-empty.png`, `con-head.png`, `con-side.png`, hero and ~140px | awaiting product |
| Constellation: four mouths sit off the centerline. The X is the larger cross | `con-head.png`, `con-head-empty.png` | awaiting product |
| Constellation: nacelles and stripe stay `#d0d6ff` at shields 0. The fuselage stays dark metal | `con-3q-empty.png`, `con-head-empty.png` | awaiting product |
| Constellation: markers sit outside the nacelle tips. None sit in the crook | Cap 50 on the Constellation marker table | awaiting product |
| Pair: a plate on a mast versus an X of four nacelles | `pair-sm-con-3q-140.png`, `pair-sm-con-3q-hero.png` | awaiting product |
| Pair: a dish versus a tower versus a long castle | Star Master beside the FlagShip, and Star Master beside the Imperial | awaiting product |
| Pair: an X versus a square of bells | Constellation beside the Imperial | awaiting product |
| Pair: an X versus a tower rectangle | Constellation beside the FlagShip | awaiting product |

## FlagShip TransWarp

The FlagShip is on `SHIP_TW_CHART_RANGE` (28 hops). The new hulls are not. Star Master and Constellation pass on idle cyan-white cones. With a drive fitted, the FlagShip cones are magenta and the upper step stays flat `#ff77ff`. With no drive fitted, the cones stay cyan-white and the upper step stays `#ff77ff`. The tower is painted metal. It is not an emissive lamp. The product wave fills both columns from the pair stills below. This scaffold does not sample a pixel.

| Drive | Cones | Upper step | Still | Measured cone RGB | Measured step RGB |
| --- | --- | --- | --- | --- | --- |
| Off | Idle cyan-white | `#ff77ff` | `pair-sm-fs-3q-140.png`, `pair-fs-imp-3q-140.png` | TBD | TBD |
| On | Magenta | `#ff77ff` | `pair-sm-fs-3q-tw-140.png`, `pair-fs-imp-3q-tw-140.png` | TBD | TBD |
| Off, shields 0 | Idle cyan-white | `#ff77ff` | `pair-sm-fs-3q-empty-140.png`, `pair-fs-imp-3q-empty-140.png` | TBD | TBD |
| On, shields 0 | Magenta | `#ff77ff` | `pair-sm-fs-3q-empty-tw-140.png`, `pair-fs-imp-3q-empty-tw-140.png` | TBD | TBD |

## Imperial and FlagShip re-shots

Reads of meshes that have already landed. This wave does not recut them. Pair frames go in the same stills directory. Each file is awaiting product. Name plate covered. Repeat at ~140px and at the hero crop, shields full and shields 0. The FlagShip cap on these frames is 200 markers, already on the merged hull. The new hulls are at 50.

Star Master beside the FlagShip. The tower stays a block. The plate stays a dish. One frame with the FlagShip drive off, and one with it on.

| File | Shot | Status |
| --- | --- | --- |
| `pair-sm-fs-3q-140.png` | Star Master and FlagShip, three-quarter, shields full, TransWarp off, ~140px. Star Master at 50. FlagShip at 200 | awaiting product |
| `pair-sm-fs-3q-tw-140.png` | Same pair, shields full, FlagShip TransWarp on. Upper step still `#ff77ff` | awaiting product |
| `pair-sm-fs-3q-empty-140.png` | Same pair, shields 0, TransWarp off. Plate still `#9ad7ff`. Upper step still `#ff77ff` | awaiting product |
| `pair-sm-fs-3q-empty-tw-140.png` | Same pair, shields 0, FlagShip TransWarp on. Upper step still `#ff77ff` | awaiting product |
| `pair-sm-fs-head-140.png` | Same pair, head-on, shields full, TransWarp off | awaiting product |
| `pair-sm-fs-head-tw-140.png` | Same pair, head-on, shields full, FlagShip TransWarp on | awaiting product |
| `pair-sm-fs-side-140.png` | Same pair, side clip, shields full, TransWarp off | awaiting product |
| `pair-sm-fs-3q-hero.png` | Same pair, hero crop, shields full, TransWarp off | awaiting product |

FlagShip beside the Imperial. The castle stays long. The tower stays a block amidships. Same drive pair.

| File | Shot | Status |
| --- | --- | --- |
| `pair-fs-imp-3q-140.png` | FlagShip and Imperial, three-quarter, shields full, TransWarp off, ~140px. FlagShip at 200 | awaiting product |
| `pair-fs-imp-3q-tw-140.png` | Same pair, shields full, FlagShip TransWarp on. Upper step still `#ff77ff` | awaiting product |
| `pair-fs-imp-3q-empty-140.png` | Same pair, shields 0, TransWarp off | awaiting product |
| `pair-fs-imp-3q-empty-tw-140.png` | Same pair, shields 0, FlagShip TransWarp on | awaiting product |
| `pair-fs-imp-head-140.png` | Same pair, head-on, shields full, TransWarp off | awaiting product |
| `pair-fs-imp-head-tw-140.png` | Same pair, head-on, shields full, FlagShip TransWarp on | awaiting product |
| `pair-fs-imp-side-140.png` | Same pair, side clip, shields full, TransWarp off | awaiting product |
| `pair-fs-imp-3q-hero.png` | Same pair, hero crop, shields full, TransWarp off | awaiting product |

Star Master beside the Imperial. The castle stays long and the bells stay a square. The plate stays a dish. Gold stays the Imperial accent.

| File | Shot | Status |
| --- | --- | --- |
| `pair-sm-imp-3q-140.png` | Star Master and Imperial, three-quarter, shields full, ~140px. Star Master at 50 | awaiting product |
| `pair-sm-imp-3q-empty-140.png` | Same pair, shields 0. Plate still `#9ad7ff` | awaiting product |
| `pair-sm-imp-head-140.png` | Same pair, head-on, shields full | awaiting product |
| `pair-sm-imp-side-140.png` | Same pair, side clip, shields full | awaiting product |
| `pair-sm-imp-3q-hero.png` | Same pair, hero crop, shields full | awaiting product |

Constellation beside the Imperial. The arms stay an X. The bells stay a square on the Imperial.

| File | Shot | Status |
| --- | --- | --- |
| `pair-con-imp-3q-140.png` | Constellation and Imperial, three-quarter, shields full, ~140px. Constellation at 50 | awaiting product |
| `pair-con-imp-3q-empty-140.png` | Same pair, shields 0. Nacelles still `#d0d6ff` | awaiting product |
| `pair-con-imp-head-140.png` | Same pair, head-on, shields full | awaiting product |
| `pair-con-imp-side-140.png` | Same pair, side clip, shields full | awaiting product |
| `pair-con-imp-3q-hero.png` | Same pair, hero crop, shields full | awaiting product |

Star Master beside the Constellation. A plate on a mast versus an X of four nacelles.

| File | Shot | Status |
| --- | --- | --- |
| `pair-sm-con-3q-140.png` | Star Master and Constellation, three-quarter, shields full, ~140px. Each at 50 | awaiting product |
| `pair-sm-con-3q-empty-140.png` | Same pair, shields 0. Plate still `#9ad7ff`. Nacelles still `#d0d6ff` | awaiting product |
| `pair-sm-con-head-140.png` | Same pair, head-on, shields full | awaiting product |
| `pair-sm-con-side-140.png` | Same pair, side clip, shields full | awaiting product |
| `pair-sm-con-3q-hero.png` | Same pair, hero crop, shields full | awaiting product |

FlagShip beside the Constellation. An X versus a tower rectangle on the centerline. The drive pair for the tower is the Star Master frames and the Imperial frames.

| File | Shot | Status |
| --- | --- | --- |
| `pair-fs-con-3q-140.png` | FlagShip and Constellation, three-quarter, shields full, TransWarp off, ~140px | awaiting product |
| `pair-fs-con-3q-empty-140.png` | Same pair, shields 0, TransWarp off. Upper step still `#ff77ff`. Nacelles still `#d0d6ff` | awaiting product |
| `pair-fs-con-3q-hero.png` | Same pair, hero crop, shields full, TransWarp off | awaiting product |

Face counts for the Imperial and the FlagShip are not remeasured here. The product wave confirms the earlier pins did not move, then leaves those counts on the sheets that recorded them. This table does not invent a replacement count.

The [wave read](cockpit-ship-stage-p1b-batch4.md#wave-read-test) names more pairs. This scaffold reserves re-shot frames for the FlagShip and the Imperial beside the dish and beside the X, and for the dish beside the X.

## Markers

`escortSlots` at the canonical pose, the phone fit, head-on, and the side clip. Every placed slot is outside the bounding sphere, kit included. Screen boxes do not hit the silhouette and do not clip the 400×260 frame. **Placed** and **Under / overlap / clipped** are awaiting product. The marker column is the contract formula, not a placement measurement.

The tables are the 100:1 count. A bay of 100 is one marker. The cap of 5,000 on each new hull is 50 markers.

Star Master. Cap 5,000 is 50 markers. The plate sets the top of the sphere. A ring sized to the fuselage clips the dish from the side and fails. Markers orbit outside the plate. Fighters per attack stay 1,000. The checklist uses the bay. Do not borrow the FlagShip radius.

| Case | Markers (formula) | Placed | Under / overlap / clipped |
| --- | --- | --- | --- |
| Bay 0 | 0 | TBD | TBD |
| Bay 1–99 | 1 | TBD | TBD |
| Bay 100 | 1 | TBD | TBD |
| Bay 101–200 | 2 | TBD | TBD |
| Bay 4,900 | 49 | TBD | TBD |
| Bay 4,901–4,999 | 50 | TBD | TBD |
| Bay 5,000 (cap, both rosters) | 50 | TBD | TBD |

Constellation. Cap 5,000 is 50 markers. The nacelle tips set the tail and the beam of the sphere. A ring that clears the slim body and clips an arm fails. A marker in the crook fails. Fighters per attack stay 2,000. The checklist uses the bay. Do not borrow the Imperial radius.

| Case | Markers (formula) | Placed | Under / overlap / clipped |
| --- | --- | --- | --- |
| Bay 0 | 0 | TBD | TBD |
| Bay 1–99 | 1 | TBD | TBD |
| Bay 100 | 1 | TBD | TBD |
| Bay 101–200 | 2 | TBD | TBD |
| Bay 4,900 | 49 | TBD | TBD |
| Bay 4,901–4,999 | 50 | TBD | TBD |
| Bay 5,000 (cap, both rosters) | 50 | TBD | TBD |

Corporate FlagShip re-shot. Cap stays 200 on the merged hull. Placement on this wave's pair frames is awaiting product. This sheet does not publish a new radius.

| Case | Markers (formula) | Placed | Under / overlap / clipped |
| --- | --- | --- | --- |
| Bay 20,000 (re-shot, both rosters) | 200 | TBD | TBD |

Checked poses, once the product wave runs: canonical yaw `0.82` pitch `0.5`, phone fit `0.72`, head-on, and the side clip. Clearance counts at those poses are TBD.

## Frame time

Node bench, same shape as the hauler sheet: one `drawShipFrame`-shaped update, project every face, build the point string, project each marker. Nine samples after four warmups. Median / max. Slot bake is the cost when the bay changes, not part of the frame. Every time below is **TBD / awaiting product**. The bar stays 16 ms. A miss of that bar is the acceptance off-ramp. This scaffold does not record a sample.

| Frame | Fit | Markers | Bake | JS frame |
| --- | --- | --- | --- | --- |
| Star Master, canonical | 1.12 | 50 | TBD | TBD |
| Constellation, canonical | 1.12 | 50 | TBD | TBD |
| Imperial, drift-shaped | 0.76 | 500 | TBD | TBD |
| Imperial, static-shaped | 0.72 | 1,000 | TBD | TBD |

The 500-marker and 1,000-marker rows are the inherited P1 bar, re-run on the file this wave ships. They are not a new Imperial mesh.

## Shields 0 and shields full

Accent fill, averaged over the same cameras at damage 0 and damage 1, is awaiting product. A fitted TransWarp drive on the FlagShip is awaiting the same average. Contract colours below are the pass colours. They are not a sampled RGB.

Empty shields leave scars and a missing bubble. The class accent stays. A full red body fails. A full body painted `#9ad7ff` fails on the Star Master. A full body painted `#d0d6ff` fails on the Constellation.

| Hull | Shields | Drive | Contract accent | Accent RGB | Body RGB | Idle plume | Fitted plume |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Star Master | full | idle | `#9ad7ff` plate and stripe. Mast and fuselage dark metal | TBD | TBD | TBD | TBD |
| Star Master | 0 | idle | Same `#9ad7ff`. Mast stays dark. Bubble absent | TBD | TBD | TBD | TBD |
| Constellation | full | idle | `#d0d6ff` nacelles and stripe. Fuselage dark metal | TBD | TBD | TBD | TBD |
| Constellation | 0 | idle | Same `#d0d6ff`. Fuselage stays dark. Bubble absent | TBD | TBD | TBD | TBD |
| Corporate FlagShip (re-shot) | full | off | `#ff77ff` upper step and stripe. Painted metal | TBD | TBD | TBD | TBD |
| Corporate FlagShip (re-shot) | full | on | Upper step stays `#ff77ff`. Cones magenta | TBD | TBD | TBD | TBD |
| Corporate FlagShip (re-shot) | 0 | off | Upper step and stripe still `#ff77ff`. Bubble absent | TBD | TBD | TBD | TBD |
| Corporate FlagShip (re-shot) | 0 | on | Upper step stays `#ff77ff`. Cones magenta. Bubble absent | TBD | TBD | TBD | TBD |
| Imperial StarShip (re-shot) | 0 and full | as the P1 mesh left it | Gold stays the Imperial accent | TBD | TBD | TBD | TBD |

The product wave replaces each TBD with the measured average, or leaves the cell TBD if that camera was not sampled. Flat metal on the accent faces stays `accent` set and `emissive` clear. Gold stays on the Imperial. Magenta on the FlagShip is the cones only. The plate stays `#9ad7ff`. The nacelles stay `#d0d6ff`.
