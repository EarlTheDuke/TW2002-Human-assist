# Seat brain on empty ports

> **Update 2026-10-05 ([ECONOMY_CALIBRATION.md](ECONOMY_CALIBRATION.md)).** The 145000 bar is gone. Seed 250925 N3 must now finish between 650,000 and 1,450,000 and realize 35 to 90 a unit. The multi-million numbers below were on the 179 / 389 / 719 table.

task_id: seat-brain-empty-ports-v1

Ports open at 0 stock and refill only at the day tick. CONFIRMED. Source: `docs/playtests/ports/TURNS_REGEN.md` (ports-turns-regen-v1). A selling port adds `round(productivity * 0.05)` of each commodity, held inside 0 to max. A buying port can take goods on day 1. No game rule, price, haggle, or port number changed in this slice.

The brain reads stock only from ports it has already seen (`known_ports`) and from the legal trade list. It does not read productivity, MCIC, or the haggle limit.

## Before

Unretuned brain, `ECONOMY_SCALE_MODE=tw2002` already on. Remeasured 2026-10-04 morning. Same shape as the scale-slice after bench.

```
python scripts/seat_brain_acceptance.py n1 --seeds 250925 --credits 100000,20000
python scripts/seat_brain_acceptance.py n3 --seeds 250925,20260925,230923,99,31
```

n1, seed 250925:

| start | day-1 dock | trade profit | aba | rejected | end sector |
| --- | --- | --- | --- | --- | --- |
| 100000 | yes (24 turns left) | 0 | 0/259 | 0 | 717 |
| 20000 | no | 0 | 0/318 | 0 | 559 |

Day 1 with empty selling shelves: the brain explores. It does not sit still. One wait does not refill a shelf. The day tick refills when the turn clock runs out. Trade profit stays 0 because there is nothing to buy until then. aba stays 0 and the engine rejects nothing.

n3, day 10. The 85 percent floor is 0.85 of that seed's N2 ladder. The 145000 bar, the 40 percent ferry cap, and rejected 0 were not lowered.

| seed | N2 | N3 | 85 percent floor | ferry | organics | planets at 0 |
| --- | --- | --- | --- | --- | --- | --- |
| 250925 | 3806979 | 1968070 | 3235932 | 0.0% | 0 | 32 |
| 20260925 | 3985849 | 1253743 | 3387971 | 0.2% | 0 | 30 |
| 230923 | 7779751 | 9506284 | 6612788 | 0.0% | 25 | none |
| 99 | 5010031 | 8473023 | 4258526 | 0.0% | 25 | none |
| 31 | 3625383 | 10345853 | 3081575 | 0.0% | 25 | none |

Seed 31 clears the floor. The 347690 figure in the task is the pre-scale measurement. Seeds 250925 and 20260925 sit under the floor because they never buy organics: the old gate required a quote at or under 25, and a full-shelf organics quote on this scale is about 233. Those two holds stay until a new measurement clears them. They are not loosened.

## What the brain does now

Only `src/tw2k/agents/seat_brain.py`.

- A buy with qty 0 is skipped. A positive qty on the legal list is stock the seat can see this turn, even when a remembered port still says 0. A sell of carried goods is still taken. `_best_buy_pair` ignores a seller with no stock and still pairs a buyer.
- A failed buy stays banned by the existing failure path. The brain does not loop on it.
- The allocator buys organics at the live scale. Cheap is `round(19 * base / 25)` (296 at base 389). A must-buy has to be at or under the live organics base (389). A chart-full organics quote of 233 is under both. The ladder (allocator off) keeps the old 19 and 25 gates, so its day-10 numbers stay the bar.
- CargoTran net is `ship_cost("cargotran")` minus 25 percent of `ship_cost` of the current hull. From a Merchant Cruiser that is 51950 - 10325 = 41625. The old brain used the stored hull cost and a net of 33175. StarDock still uses the legal list's `net_cost_by` when that list is present, and it still refuses a hull the seat cannot pay for.
- Gift math multiplies by `fighter_unit_price(day)` (160 to 239; day 0 is 200). Gifts are 0, so the product is 0. `FIGHTER_COST` is not imported here. Net-worth fighters stay at 50 in `models.py`.

## After

Same commands, retuned brain. n1 is unchanged. n3 passed. Ferry stayed under 40 percent. Seed 250925 stayed over 145000. Rejected stayed 0. Every seed cleared 85 percent of the same N2 ladder as the before table. Organics never hit 0.

n1, seed 250925:

| start | day-1 dock | trade profit | aba | rejected | end sector |
| --- | --- | --- | --- | --- | --- |
| 100000 | yes (24 turns left) | 0 | 0/259 | 0 | 717 |
| 20000 | no | 0 | 0/318 | 0 | 559 |

Day 1 still explores. Profit stays 0 because the shelves are empty until the day tick. aba stays 0. The engine rejects nothing.

n3, day 10. The N2 column matches the before bench. The ladder was not moved.

| seed | N2 | N3 | 85 percent floor | ferry | min organics | planets at 0 |
| --- | --- | --- | --- | --- | --- | --- |
| 250925 | 3806979 | 8795955 | 3235932 | 0.3% | 9 | none |
| 20260925 | 3985849 | 9325339 | 3387971 | 0.1% | 19 | none |
| 230923 | 7779751 | 9694117 | 6612788 | 0.0% | 25 | none |
| 99 | 5010031 | 8372357 | 4258526 | 0.0% | 9 | none |
| 31 | 3625383 | 10531006 | 3081575 | 0.0% | 9 | none |

Seed 31 finishes at 10,531,006, over the floor. The two seeds that sat under the floor now clear it. The net-worth holds (1,968,070 and 1,253,743) and the N3 starve holds (planet 32 and planet 30) are removed. The 145000 bar, the 40 percent ferry cap, rejected 0, and the 85 percent floor are unchanged.

The N2 ladder still starves planet 32 on seed 250925, planet 30 on seed 20260925, planet 29 on seed 99, and planet 30 on seed 31. Seed 230923 stays clean. Those pins stay. The allocator is what clears them.

CargoTran net from a Merchant Cruiser is 41625. The old brain used 33175. A hull the seat cannot pay for is not sent. Gift math uses the 160 to 239 fighter wave. Gifts are 0, so that product is 0. Net-worth fighters stay at 50.
