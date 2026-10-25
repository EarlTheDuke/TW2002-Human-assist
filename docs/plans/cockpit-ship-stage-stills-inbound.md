# Cockpit ship-stage stills — inbound map

Docs only. This sheet lists which planning files on `feature/grokbot-player` @ `d389d683` (#375) already point at the [stills inventory](stills/README.md) (#344). It does not stamp Pass. It adds no PNG. It leaves every other sheet as this tip left it. #372 updates the inventory row for `p1b-batch3-guns`. #373 refreshes the batch-4 readiness note. #374 refreshes the batch-3 readiness note. #375 refreshes the batch-5 readiness note. None of those adds a directory. The counts below stay the counts surveyed through #371.

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

- [Fleet order](cockpit-ship-stage-p1b-fleet-order.md) — dedicated link (#356), directory [p1-merchant-imperial](stills/p1-merchant-imperial/) (#361). TBD scaffold, no PNG.
- [Four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) — dedicated link, and a second link in the sheet body. Tip history on the same sheet also names the path.
- [Scout and Freighter frames](cockpit-ship-stage-p1b-scout-freighter.md) — dedicated link, directory `p1b-scout-freighter`.
- [BattleShip and FlagShip frames](cockpit-ship-stage-p1b-battleship-flagship.md) — dedicated link, directory `p1b-battleship-flagship`.
- [Escape Pod and T'Khasi frames](cockpit-ship-stage-p1b-batch1-escape-orion.md) — dedicated link, directory `p1b-batch1-escape-orion`.

## P2

- [P2 wire](cockpit-ship-stage-p2-wire.md) — dedicated link (#369). No stills directory owns P2. Tip history on the same sheet also names the path.

## P3

- [P3 layout](cockpit-ship-stage-p3-layout.md) — dedicated link (#368). No stills directory owns P3. Tip history on the same sheet also names the path.

## Readiness

- [Batch 1 readiness](cockpit-ship-stage-p1b-batch1-readiness.md) — dedicated link, directory `p1b-batch1-escape-orion` (#365).
- [Batch 3 readiness](cockpit-ship-stage-p1b-batch3-readiness.md) — dedicated link, directory `p1b-batch3-guns`. #374 (`63326660`) records the guns as landed and Pass. Star Master and Constellation are the live dish cut. Does not stamp Pass.
- [Batch 4 readiness](cockpit-ship-stage-p1b-batch4-readiness.md) — dedicated link, directory `p1b-batch4-dish`. #373 (`30b9e7fa`) names Star Master and Constellation the live cut. That product is in flight. Does not stamp Pass.
- [Batch 5 readiness](cockpit-ship-stage-p1b-batch5-readiness.md) — dedicated link, directory `p1b-batch5-brick`. #375 (`d389d683`) records the guns Pass and names Star Master and Constellation the live cut ahead. Tholian Sentinel and Interdictor Cruiser wait behind the batch-4 Pass. The brick product has not started. Does not stamp Pass.
- [P2 readiness](cockpit-ship-stage-p2-readiness.md) — dedicated link (#366). No stills directory owns P2.

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
- [Batch 4 dish product](cockpit-ship-stage-p1b-batch4-dish-product.md) — dedicated link. Scaffold. No PNG.
- [Batch 5 brick product](cockpit-ship-stage-p1b-batch5-brick-product.md) — dedicated link. Scaffold. No PNG.

## Other

- [Sheet index](cockpit-ship-stage-INDEX.md) — dedicated finder link to the inventory. The finder row says eight directories, including `p1-merchant-imperial` (#362). The inventory table on this tip has eight.

Mention only. The literal string appears in the shared tip-history paragraph. This sheet has no markdown link to the inventory:

- [COMMANDER_NEXT](COMMANDER_NEXT.md)

## Candidates

Ship-stage sheets that lacked `stills/README.md` on the #358 map are listed in the role sections above.

Also scanned, and left off this list: [fighter marker math](cockpit-ship-stage-marker-math.md) records the 100:1 count and names no stills directory.

Counted on this tip: 37 sheets carry a markdown link to `stills/README.md`. One more sheet contains the string only inside tip history. 38 files under `docs/plans/` contain the literal string. The P1 directory README is the extra relative link above.
