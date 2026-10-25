# Cockpit ship-stage stills — inbound map

Docs only. This sheet lists which planning files on `feature/grokbot-player` @ `5549cc94` (#357) already point at the [stills inventory](stills/README.md) (#344). It does not stamp Pass. It adds no PNG. It leaves every other sheet as this tip left it.

The inventory table has eight directories. The new row is [p1-merchant-imperial](stills/p1-merchant-imperial/) (#357): Merchant Cruiser and Imperial StarShip. That row is a TBD scaffold. It holds a placeholder README and no PNG.

Scan rule: a hit is the literal string `stills/README.md` under `docs/plans/`. A dedicated pointer is a markdown link to that file. A mention is the same string inside tip history, with no such link. Each sheet is listed once. A readiness, acceptance, contract, or product-stills sheet is listed under that role. P1 acceptance is listed under P1.

## P0

- [P0 pack](cockpit-ship-stage-p0.md) — dedicated link.
- [Render decision](cockpit-ship-stage-p0-render.md) — dedicated link.
- [Silhouette bible](cockpit-ship-stage-p0-silhouette-bible.md) — dedicated link.

## P1

- [P1 acceptance](cockpit-ship-stage-p1-acceptance.md) — dedicated link.
- [P1 spike](cockpit-ship-stage-p1-spike.md) — dedicated link. The linked sentence still says the inventory lists no directory for the Merchant Cruiser or the Imperial StarShip, and no P1 stills. The inventory row for [p1-merchant-imperial](stills/p1-merchant-imperial/) is on this tip (#357).
- [p1-merchant-imperial README](stills/p1-merchant-imperial/README.md) — points at the index with a relative link (`../README.md`). The file does not contain the literal string `stills/README.md`. Placeholder README, no PNG.

## P1b

- [Fleet order](cockpit-ship-stage-p1b-fleet-order.md) — dedicated link (#356).
- [Four-hull build](cockpit-ship-stage-p1b-four-hull-build.md) — dedicated link, and a second link in the sheet body. Tip history on the same sheet also names the path.
- [Scout and Freighter frames](cockpit-ship-stage-p1b-scout-freighter.md) — dedicated link, directory `p1b-scout-freighter`.
- [BattleShip and FlagShip frames](cockpit-ship-stage-p1b-battleship-flagship.md) — dedicated link, directory `p1b-battleship-flagship`.
- [Escape Pod and T'Khasi frames](cockpit-ship-stage-p1b-batch1-escape-orion.md) — dedicated link, directory `p1b-batch1-escape-orion`.

## Readiness

- [Batch 3 readiness](cockpit-ship-stage-p1b-batch3-readiness.md) — dedicated link, directory `p1b-batch3-guns`.
- [Batch 4 readiness](cockpit-ship-stage-p1b-batch4-readiness.md) — dedicated link, directory `p1b-batch4-dish`.
- [Batch 5 readiness](cockpit-ship-stage-p1b-batch5-readiness.md) — dedicated link, directory `p1b-batch5-brick`.

## Acceptance

- [Scout and Freighter acceptance](cockpit-ship-stage-p1b-scout-freighter-acceptance.md) — dedicated link, directory `p1b-scout-freighter`.
- [BattleShip and FlagShip acceptance](cockpit-ship-stage-p1b-battleship-flagship-acceptance.md) — dedicated link, directory `p1b-battleship-flagship`.
- [Batch 1 acceptance](cockpit-ship-stage-p1b-batch1-acceptance.md) — dedicated link, directory `p1b-batch1-escape-orion`.
- [Batch 2 haulers acceptance](cockpit-ship-stage-p1b-batch2-haulers-acceptance.md) — dedicated link, directory `p1b-batch2-haulers`.

## Contracts

- [Next hulls](cockpit-ship-stage-p1b-next-hulls.md) — dedicated link. Mesh contract for Scout Marauder, Merchant Freighter, BattleShip, and Corporate FlagShip.
- [Batch 1 remainder](cockpit-ship-stage-p1b-batch1-remainder.md) — dedicated link, directory `p1b-batch1-escape-orion`.
- [Batch 2 haulers](cockpit-ship-stage-p1b-batch2-haulers.md) — dedicated link, directory `p1b-batch2-haulers`.

## Product stills

- [Batch 2 haulers product](cockpit-ship-stage-p1b-batch2-haulers-product.md) — dedicated link, directory `p1b-batch2-haulers`.
- [Batch 3 guns product](cockpit-ship-stage-p1b-batch3-guns-product.md) — dedicated link. Scaffold. No PNG.
- [Batch 4 dish product](cockpit-ship-stage-p1b-batch4-dish-product.md) — dedicated link. Scaffold. No PNG.
- [Batch 5 brick product](cockpit-ship-stage-p1b-batch5-brick-product.md) — dedicated link. Scaffold. No PNG.

## Other

- [Sheet index](cockpit-ship-stage-INDEX.md) — dedicated finder link to the inventory. The finder row still says seven directories. The inventory table on this tip has eight, including `p1-merchant-imperial`.

Mention only. The literal string appears in the shared tip-history paragraph. These sheets have no markdown link to the inventory:

- [COMMANDER_NEXT](COMMANDER_NEXT.md)
- [P2 wire](cockpit-ship-stage-p2-wire.md)
- [P3 layout](cockpit-ship-stage-p3-layout.md)

## Candidates

These sheets contain no `stills/README.md` string. This map leaves them as they are.

- Acceptance: [batch 3](cockpit-ship-stage-p1b-batch3-acceptance.md), [batch 4](cockpit-ship-stage-p1b-batch4-acceptance.md), [batch 5](cockpit-ship-stage-p1b-batch5-acceptance.md). Each already links its stills directory and its product scaffold. Batch 1 and batch 2 acceptance link the inventory.
- Contracts: [batch 3 guns](cockpit-ship-stage-p1b-batch3.md), [batch 4 dish and X](cockpit-ship-stage-p1b-batch4.md), [batch 5 brick and hoops](cockpit-ship-stage-p1b-batch5.md). Each already links its stills directory. The batch-2 contract and the next-hulls contract link the inventory.
- Readiness: [batch 1 readiness](cockpit-ship-stage-p1b-batch1-readiness.md). Batch 3, 4, and 5 readiness link the inventory. [P2 readiness](cockpit-ship-stage-p2-readiness.md) names measured stills sheets and does not name the inventory. The P2 wire's only hits are the tip-history paragraph above.
- P1: [P1 pass](cockpit-ship-stage-p1-pass.md). P1 acceptance and the P1 spike link the inventory. The new directory is `p1-merchant-imperial`.
- P0: [FX state machine](cockpit-ship-stage-p0-fx.md). The P0 pack, the render decision, and the silhouette bible link the inventory.

Also scanned, and left off this list: [fighter marker math](cockpit-ship-stage-marker-math.md) records the 100:1 count and names no stills directory.

Counted on this tip: 25 sheets carry a markdown link to `stills/README.md`. Three more sheets contain the string only inside tip history. 28 files under `docs/plans/` contain the literal string. The P1 directory README is the extra relative link above.
