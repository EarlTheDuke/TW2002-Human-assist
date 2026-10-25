# Cockpit ship-stage stills — inbound map

Docs only. This sheet lists which planning files on `feature/grokbot-player` @ `8ccb7c6f` (#389) already point at the [stills inventory](stills/README.md) (#344). It does not stamp Pass. It adds no PNG. It leaves every other sheet as this tip left it. #372 updates the inventory row for `p1b-batch3-guns`. #373 refreshes the batch-4 readiness note. #374 refreshes the batch-3 readiness note. #375 refreshes the batch-5 readiness note. #377 refreshes the P2 readiness note and adds body links to the inventory. That sheet already had a dedicated link (#366). #379 (`863e4eb2`) refreshed this map through #377. #380 (`5c719360`) records the inventory row `p1b-batch4-dish` as product in flight, not measured, no PNG. Pass is not stamped. #381 (`9d4c972f`) refreshes the fleet order onto `5c719360`. Guns stay Landed+Pass. Star Master and Constellation stay the live dish cut, in flight. Batch 5 waits behind the dish Pass. P2 stays gated. #382 (`436bfc47`) refreshes the lagging tip sheets onto `9d4c972f`: COMMANDER_NEXT, the sheet index, the four-hull build, P2 wire, and P3 layout. That refresh also recorded #379 through #381 on this map. It adds no link and no directory. Does not stamp Pass. Adds no PNG. #383 (`2c097f6a`) refreshes the batch-4 readiness note onto `436bfc47`. The dish stays product in flight, not measured, no PNG. Pass is not stamped. Guns stay Landed+Pass (#370 on product #363). Both dish meshes stay `fleet-glass-v1`. Batch 5 waits behind the dish Pass. P2 stays gated. That note already had a dedicated link. #383 adds no link and no directory. #384 (`1ff9bef6`) refreshes the P2 readiness note onto `2c097f6a`. Guns stay Landed+Pass (#363, `5ebec08f`; Pass #370, `223dacfa`). Star Master and Constellation stay the live dish cut, in flight on `fleet-glass-v1`. The dish row stays product in flight, not measured, no PNG. Pass is not stamped. The brick waits behind the dish Pass. P2 stays gated. Guns Pass alone does not open the wire. Dish Pass is still required before P2 product. That note already had a dedicated link (#366). #384 adds further inventory links in the body. Those stay on the Readiness line. #384 adds no directory. This note does not stamp Pass and does not open the wire. #385 (`0dd332dd`) refreshes this map through #384. It adds no link and no directory. Does not stamp Pass. Adds no PNG. #386 (`3ee4e23d`) refreshes the fleet order onto `0dd332dd`. Guns stay Landed+Pass (#370 on product #363). Star Master and Constellation stay the live dish cut. Batch 5 waits behind the dish Pass. P2 stays gated. That sheet already had a dedicated link. #386 adds no link and no directory. #387 (`3114c994`) lands Star Master and Constellation on the SVG path (`buildHullFaces` / `projectFace`). Those two leave `fleet-glass-v1`. Star Master is 183 faces. Constellation is 311 faces. Measured stills are in [p1b-batch4-dish](stills/p1b-batch4-dish/). Pass is not stamped. #388 (`1ee63b98`) records the inventory row `p1b-batch4-dish` as product landed. Pass is not stamped. The product sheet and the inventory already had dedicated links. #387 and #388 add no directory. #389 (`8ccb7c6f`) refreshes the batch-5 readiness note onto `1ee63b98`. Tholian Sentinel and Interdictor Cruiser stay on `fleet-glass-v1` and wait behind the dish Pass. The brick product has not started. That note already had a dedicated link. #389 adds no link and no directory. The live cut stays the dish. This note does not stamp Pass and does not open the wire. None of those adds a directory. The counts below stay the counts surveyed through #371.

The inventory table has eight directories. The new row is [p1-merchant-imperial](stills/p1-merchant-imperial/) (#357): Merchant Cruiser and Imperial StarShip. That row is a TBD scaffold. It holds a placeholder README and no PNG.

Scan rule: a hit is the literal string `stills/README.md` under `docs/plans/`. A dedicated pointer is a markdown link to that file. A mention is the same string inside tip history, with no such link. Each sheet is listed once. A readiness, acceptance, contract, or product-stills sheet is listed under that role. P1 acceptance is listed under P1.

## P0

- [P0 pack](cockpit-ship-stage-p0.md) — dedicated link.
- [Render decision](cockpit-ship-stage-p0-render.md) — dedicated link.
- [Silhouette bible](cockpit-ship-stage-p0-silhouette-bible.md) — dedicated link.
- [FX state machine](cockpit-ship-stage-p0-fx.md) — dedicated link (#365). No stills directory.

## P1

- [P1 acceptance](cockpit-ship-stage-p1-acceptance.md) — dedicated link, directory [p1-merchant-imperial](stills/p1-merchant-imperial/) (#358). TBD scaffold, no PNG.
- [P1 spike](cockpit-ship-stage-p1-spike.md) — dedicated link to the same directory (#358). TBD scaffold, no PNG.
- [P1 pass](cockpit-ship-stage-p1-pass.md) — dedicated link, directory [p1-merchant-imperial](stills/p1-merchant-imperial/) (#360). TBD scaffold, no PNG.
- [p1-merchant-imperial README](stills/p1-merchant-imperial/README.md) — points at the index with a relative link (`../README.md`). The file does not contain the literal string `stills/README.md`. Placeholder README, no PNG.

## P1b

- [Fleet order](cockpit-ship-stage-p1b-fleet-order.md) — dedicated link (#356), directory [p1-merchant-imperial](stills/p1-merchant-imperial/) (#361). That directory stays a TBD scaffold, no PNG. #381 (`9d4c972f`) refreshes this sheet onto `5c719360`. The live cut is the batch-4 dish, in flight. The inventory row `p1b-batch4-dish` is product in flight, not measured, no PNG. Pass is not stamped. Guns stay Landed+Pass. Batch 5 waits behind the dish Pass. P2 stays gated. This sheet does not stamp Pass. #386 (`3ee4e23d`) refreshes this sheet onto `0dd332dd` (#385). #387 landed Star Master and Constellation on the SVG path. They leave `fleet-glass-v1`. #388 records the inventory row as product landed. Pass is not stamped. #389 keeps Tholian Sentinel and Interdictor Cruiser behind the dish Pass, on `fleet-glass-v1`. The live cut stays the dish. P2 stays gated. This sheet does not stamp Pass.
- [Four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) — dedicated link, and a second link in the sheet body. Tip history on the same sheet also names the path. #382 (`436bfc47`) refreshes this sheet onto `9d4c972f` (#381). The dedicated links stay. This refresh adds no link and does not stamp Pass. The surveyed tip on this sheet moves to `8ccb7c6f` (#389). That move adds no link and does not stamp Pass.
- [Scout and Freighter frames](cockpit-ship-stage-p1b-scout-freighter.md) — dedicated link, directory `p1b-scout-freighter`.
- [BattleShip and FlagShip frames](cockpit-ship-stage-p1b-battleship-flagship.md) — dedicated link, directory `p1b-battleship-flagship`.
- [Escape Pod and T'Khasi frames](cockpit-ship-stage-p1b-batch1-escape-orion.md) — dedicated link, directory `p1b-batch1-escape-orion`.

## P2

- [P2 wire](cockpit-ship-stage-p2-wire.md) — dedicated link (#369). No stills directory owns P2. Tip history on the same sheet also names the path. #382 (`436bfc47`) refreshes the surveyed tip to `9d4c972f` (#381). P2 stays gated. This refresh adds no link and does not open the wire. The surveyed tip on this sheet moves to `8ccb7c6f` (#389). P2 stays gated. That move adds no link and does not open the wire.

## P3

- [P3 layout](cockpit-ship-stage-p3-layout.md) — dedicated link (#368). No stills directory owns P3. Tip history on the same sheet also names the path. #382 (`436bfc47`) refreshes the surveyed tip to `9d4c972f` (#381). P3 stays closed. This refresh adds no link and does not open the layout PR. The surveyed tip on this sheet moves to `8ccb7c6f` (#389). P3 stays closed. That move adds no link and does not open the layout PR.

## Readiness

- [Batch 1 readiness](cockpit-ship-stage-p1b-batch1-readiness.md) — dedicated link, directory `p1b-batch1-escape-orion` (#365).
- [Batch 3 readiness](cockpit-ship-stage-p1b-batch3-readiness.md) — dedicated link, directory `p1b-batch3-guns`. #374 (`63326660`) records the guns as landed and Pass. Star Master and Constellation are the live dish cut. Does not stamp Pass.
- [Batch 4 readiness](cockpit-ship-stage-p1b-batch4-readiness.md) — dedicated link, directory `p1b-batch4-dish`. #373 (`30b9e7fa`) names Star Master and Constellation the live cut. That product is in flight. Does not stamp Pass. #383 (`2c097f6a`) refreshes this note onto `436bfc47` (#382). #380 records the dish row as product in flight, not measured, no PNG. Guns stay Landed+Pass (#370 on product #363). On this tip both meshes stay `fleet-glass-v1`. Batch 5 waits behind the dish Pass. P2 stays gated. This note does not stamp Pass. The dedicated link was already on this line. #383 adds no link. #387 (`3114c994`) landed those meshes on the SVG path. They leave `fleet-glass-v1`. #388 (`1ee63b98`) records the dish row as product landed. Pass is not stamped.
- [Batch 5 readiness](cockpit-ship-stage-p1b-batch5-readiness.md) — dedicated link, directory `p1b-batch5-brick`. #375 (`d389d683`) records the guns Pass and names Star Master and Constellation the live cut ahead. Tholian Sentinel and Interdictor Cruiser wait behind the batch-4 Pass. The brick product has not started. Does not stamp Pass. #389 (`8ccb7c6f`) refreshes this note onto `1ee63b98` (#388). Star Master and Constellation are product landed on the SVG path. They left `fleet-glass-v1`. Pass is not stamped. Tholian Sentinel and Interdictor Cruiser stay on `fleet-glass-v1` and wait behind the dish Pass. The brick product has not started. This note does not stamp Pass.
- [P2 readiness](cockpit-ship-stage-p2-readiness.md) — dedicated link (#366). No stills directory owns P2. #377 (`3e9d2909`) refreshes this note onto `6d80ef5b`. #384 (`1ff9bef6`) refreshes this note onto `2c097f6a` (#383). Guns stay Landed+Pass (#363, `5ebec08f`; Pass #370, `223dacfa`). Star Master and Constellation stay the live dish cut, in flight on `fleet-glass-v1`. #380 records `p1b-batch4-dish` as product in flight, not measured, no PNG. Pass is not stamped. The brick waits behind the dish Pass. P2 stays gated. Guns Pass alone does not open the wire. Dish Pass is still required before P2 product. Body links name the inventory. This note does not stamp Pass and does not open the wire. #387, #388, and #389 do not open the wire.

## Acceptance

- [Scout and Freighter acceptance](cockpit-ship-stage-p1b-scout-freighter-acceptance.md) — dedicated link, directory `p1b-scout-freighter`.
- [BattleShip and FlagShip acceptance](cockpit-ship-stage-p1b-battleship-flagship-acceptance.md) — dedicated link, directory `p1b-battleship-flagship`.
- [Batch 1 acceptance](cockpit-ship-stage-p1b-batch1-acceptance.md) — dedicated link, directory `p1b-batch1-escape-orion`.
- [Batch 2 haulers acceptance](cockpit-ship-stage-p1b-batch2-haulers-acceptance.md) — dedicated link, directory `p1b-batch2-haulers`.
- [Batch 3 acceptance](cockpit-ship-stage-p1b-batch3-acceptance.md) — dedicated link, directory `p1b-batch3-guns` (#364). Pass stamped (#370) on product #363 (`5ebec08f`). The Pass paragraph also names the inventory path. Not a candidate.
- [Batch 4 acceptance](cockpit-ship-stage-p1b-batch4-acceptance.md) — dedicated link, directory `p1b-batch4-dish` (#364).
- [Batch 5 acceptance](cockpit-ship-stage-p1b-batch5-acceptance.md) — dedicated link, directory `p1b-batch5-brick` (#364).

## Contracts

- [Next hulls](cockpit-ship-stage-p1b-next-hulls.md) — dedicated link. Mesh contract for Scout Marauder, Merchant Freighter, BattleShip, and Corporate FlagShip.
- [Batch 1 remainder](cockpit-ship-stage-p1b-batch1-remainder.md) — dedicated link, directory `p1b-batch1-escape-orion`.
- [Batch 2 haulers](cockpit-ship-stage-p1b-batch2-haulers.md) — dedicated link, directory `p1b-batch2-haulers`.
- [Batch 3 guns](cockpit-ship-stage-p1b-batch3.md) — dedicated link, directory `p1b-batch3-guns` (#367). The product-scaffold sentence on this sheet says the scaffold ships no PNG.
- [Batch 4 dish and X](cockpit-ship-stage-p1b-batch4.md) — dedicated link, directory `p1b-batch4-dish` (#367).
- [Batch 5 brick and hoops](cockpit-ship-stage-p1b-batch5.md) — dedicated link, directory `p1b-batch5-brick` (#367).

## Product stills

- [Batch 2 haulers product](cockpit-ship-stage-p1b-batch2-haulers-product.md) — dedicated link, directory `p1b-batch2-haulers`.
- [Batch 3 guns product](cockpit-ship-stage-p1b-batch3-guns-product.md) — dedicated link, directory `p1b-batch3-guns`. Measured product (#363, `5ebec08f`). PNGs are in that directory. The directory README still calls that directory a scaffold with no PNG. #372 (`d063a95a`) records the inventory row as measured product: Missile Frigate 283 faces, Havoc GunStar 261 faces, PNGs in the directory, Pass on the batch-3 acceptance (#370).
- [Batch 4 dish product](cockpit-ship-stage-p1b-batch4-dish-product.md) — dedicated link. #380 (`5c719360`) records the inventory row `p1b-batch4-dish` as product in flight, not measured, no PNG. Pass is not stamped. Star Master and Constellation stay on `fleet-glass-v1`. #387 (`3114c994`) landed those two on the SVG path. They leave `fleet-glass-v1`. Star Master is 183 faces. Constellation is 311 faces. PNGs are in that directory. #388 (`1ee63b98`) records the inventory row as product landed. Pass is not stamped.
- [Batch 5 brick product](cockpit-ship-stage-p1b-batch5-brick-product.md) — dedicated link. Scaffold. No PNG.

## Other

- [Sheet index](cockpit-ship-stage-INDEX.md) — dedicated finder link to the inventory. The finder row says eight directories, including `p1-merchant-imperial` (#362). The inventory table on this tip has eight. #382 (`436bfc47`) refreshes this finder onto `9d4c972f` (#381). The finder still counts eight directories. This refresh adds no link. The surveyed tip on this finder moves to `8ccb7c6f` (#389). The finder still counts eight directories. That move adds no link.

Mention only. The literal string appears in the shared tip-history paragraph. This sheet has no markdown link to the inventory. #382 (`436bfc47`) refreshes that paragraph onto `9d4c972f` (#381). This refresh moves that paragraph onto `8ccb7c6f` (#389). The string stays inside tip history:

- [COMMANDER_NEXT](COMMANDER_NEXT.md)

## Candidates

Ship-stage sheets that lacked `stills/README.md` on the #358 map are listed in the role sections above. #377 added further inventory links on P2 readiness. That sheet already sits under Readiness. Its new body links stay on that line. #379 recorded that. #380 changes the `p1b-batch4-dish` inventory row and adds no link. #381 refreshes the fleet order, which already sits under P1b, and adds no link. #382 refreshes COMMANDER_NEXT, the sheet index, the four-hull build, P2 wire, and P3 layout. Those sheets already sit in the sections above. #382 adds no link. #383 refreshes batch-4 readiness, which already sits under Readiness, and adds no link. #384 refreshes P2 readiness, which already sits under Readiness. #384 adds further inventory links in the body. Those stay on that line. #384 adds no sheet. #385 refreshes this map, which is this sheet, and adds no link. #386 refreshes the fleet order, which already sits under P1b, and adds no link. #387 lands the dish product and adds PNGs in `p1b-batch4-dish`. That directory already sits on the product-stills line. #387 adds no sheet. #388 records the dish inventory row as product landed and adds no link. #389 refreshes batch-5 readiness, which already sits under Readiness, and adds no link.

Also scanned, and left off this list: [fighter marker math](cockpit-ship-stage-marker-math.md) records the 100:1 count and names no stills directory.

Counted on this tip: 37 sheets carry a markdown link to `stills/README.md`. One more sheet contains the string only inside tip history. 38 files under `docs/plans/` contain the literal string. The P1 directory README is the extra relative link above. Rechecked after #382, #383, and #384. None of those adds a file. #384 adds body links on the P2 readiness sheet, which is already one of the 37. Rechecked after #385, #386, #387, #388, and #389. None of those adds a file. #387 adds PNGs in `p1b-batch4-dish`, which is already one of the eight directories. #388 records that row as product landed and adds no file. #389 refreshes batch-5 readiness, which is already one of the 37. The counts stay the counts surveyed through #371.
