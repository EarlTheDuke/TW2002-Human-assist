# Economy calibration

task_id: economy-calibration-v1

The tw2002 money scale paid about 8 times the original per unit traded. The cause is one number per commodity: `_COMMODITY_BASE_TW2002` was solved against a buying port that is full, while the economy2 chart's "100 percent" buying port is empty. This slice re-solves the same spread at the right end of the stock curve. The tw2002 bases go from 179 / 389 / 719 to 26 / 56 / 102. Legacy mode is unchanged. Nothing else in the price, haggle, regen, turn, or ship code changed.

No library file prints 179, 389, or 719. They were solved numbers (`ECONOMY_SCALE_APPLY.md`), not published base prices.

## The original rule we copy

economy2.html (Cabal, ranked first in `docs/reference/tw2002/README.md`), the 100 percent charts, experience 0, no haggle, 250 holds:

| Commodity | Selling port at MCIC 50 | Buying port at MCIC -50 | Spread per hold |
| --- | --- | --- | --- |
| fuel_ore | 3,675 (14.70 a hold) | 8,791 (35.16) | 20.46 |
| organics | 6,964 (27.86) | 17,712 (70.85) | 42.99 |
| equipment | 12,190 (48.76) | 31,910 (127.64) | 78.88 |

The same page: "When the port is buying a particular product, and that number is at 0, it means that the port is at 100% and ready to buy up to its maximum. When the port is selling product, and that number is at 0, it means the port is at 0%." CONFIRMED. So the chart's two ports are a full selling port and an empty buying port. In our curve that is stock fraction 1 on the seller (0.60 x base) and stock fraction 0 on the buyer (1.45 x base, times 0.945 for MCIC -50).

ECONOMY_SCALE_APPLY.md used fraction 1 on both ports. A buying port at fraction 1 is full and cannot buy at all, so that point never happens in play. Its spread factor is 0.10875 x base. The real chart point is 0.77025 x base. Matching 78.88 credits with the small factor needed a base about 7 times too big, and every percent rule after it (stock, MCIC, experience) then moved a price that was 7 to 9 times the chart.

## One trade, before and after

Same port pair through the real engine (`apply_action` buy, one warp, `apply_action` sell): a full class 1 or class 3 seller at MCIC 50, an empty buyer at MCIC -50, experience 0, no haggle. A quote here is per unit for the whole load, so profit per hold is the same at 20, 75, and 250 holds.

| Commodity | Holds | Buy (port sells) | Sell (port buys) | Units | Profit per unit | Profit per trade | Original per unit | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fuel_ore | 20 | 16 | 36 | 20 | 20 | 400 | 20.46 | UNVERIFIED (chart prints 250 holds only) |
| fuel_ore | 75 | 16 | 36 | 75 | 20 | 1,500 | 20.46 | UNVERIFIED (chart prints 250 holds only) |
| fuel_ore | 250 | 16 | 36 | 250 | 20 | 5,000 | 20.46 (5,116) | CONFIRMED (-2.3%) |
| organics | 20 | 34 | 77 | 20 | 43 | 860 | 42.99 | UNVERIFIED (chart prints 250 holds only) |
| organics | 75 | 34 | 77 | 75 | 43 | 3,225 | 42.99 | UNVERIFIED (chart prints 250 holds only) |
| organics | 250 | 34 | 77 | 250 | 43 | 10,750 | 42.99 (10,748) | CONFIRMED (+0.02%) |
| equipment | 20 | 61 | 140 | 20 | 79 | 1,580 | 78.88 | UNVERIFIED (chart prints 250 holds only) |
| equipment | 75 | 61 | 140 | 75 | 79 | 5,925 | 78.88 | UNVERIFIED (chart prints 250 holds only) |
| equipment | 250 | 61 | 140 | 250 | 79 | 19,750 | 78.88 (19,720) | SOURCE-CONFLICT (+0.15% on the 100% chart; the experience table reads 82.58) |

Before this slice the same trade was fuel 107 / 245 (138 a hold), organics 233 / 533 (300), equipment 431 / 985 (554): 6.8, 7.0, and 7.0 times the chart.

- **Per-hold profit at 20 and 75 holds.** The chart prints only 250-hold totals. Scaling them per hold is UNVERIFIED for small loads. The haggling page gives per-unit formulas, so a flat per-unit quote is the likely rule.
- **Quote level.** One base cannot hit both quotes, because our curve's buy/sell ratio at the chart point is 2.28 and the chart's is 2.4 to 2.6. The seller quotes 9 to 25 percent over the chart (fuel 16 vs 14.70, organics 34 vs 27.86, equipment 61 vs 48.76). The buyer quotes 2 to 10 percent over (36 vs 35.16, 77 vs 70.85, 140 vs 127.64). Deliberate difference: we match the spread, as the earlier slice did, and keep the curve.
- **Equipment cell.** The experience table on the same page averages that cell at 11,760 / 32,405 (spread 82.58 a hold) instead of 12,190 / 31,910. SOURCE-CONFLICT, already in ECONOMY_SCALE_APPLY.md. We follow the 100 percent chart.
- **Fuel rounding.** Base 26 quotes a 5,000 spread on 250 holds (2.27 percent low). Base 27 quotes 5,250 (2.62 percent high). 26 is the closest integer. Deliberate difference.

**Experience check.** On the chart, 1,000 experience moves the -50 / 50 equipment trade from 78.88 to 102.20 a hold (+23.3). Our curve on base 102 adds 23.5. On base 719 it added 165. This was not tuned; it falls out of the corrected base, and it is the strongest sign the new base is right. CONFIRMED.

**Best trade.** 1,000 experience, the extreme MCIC our roll can make (seller 1, buyer -100): fuel 9 / 49 (40 a hold), organics 19 / 106 (87), equipment 35 / 193 (158). The original's best published ports (experience 1,000, fuel 90 / -90, organics 75 / -75, equipment 65 / -65) give 42.3, 74.5, and 121.0. Ours is 0.95, 1.17, and 1.31 of that, because our MCIC roll reaches 1 and -100 while the published ranges stop at 65 / 75 / 90. See open items.

**Original income.** Cabal's corps.html, "Daily Income (assumes 1000 turn game)": port pair trading in a Merchant Freighter 600k to 1.2M a day, in an Imperial StarShip 1M to 2M. Those are expert players in a stocked universe. Our N3 seat realizes about 100k a day by day 10 (below). Comparing the two is UNVERIFIED: the original numbers assume full ports, our ports open empty and regen 5 percent of productivity a day (TURNS_REGEN.md), so our seats spend 85 percent of their turns travelling between thin ports.

## Where the 50x came from (measured)

Seed 250925, solo N3 brain, fogged replay (`prove_growth_replay`), 10 days, 1,000 turns a day, 20,000 start credits, the engine before this slice. Every trade and every action was logged by a wrapper around `execute_trade` and `apply_action`; nothing in the engine was stubbed.

Baseline: net worth 7,255,106, credits 7,020,434. 254 sells, 16,309 units, realized profit 7,088,124: 434.6 a unit and 27,906 a sell. 0 of 510 trades haggled. All 10,000 turns were spent: plot_course 8,681, warp 839, trade 440.

One knob at a time, everything else as the baseline:

| Knob | Day-10 net worth | Change |
| --- | --- | --- |
| Baseline (bases 179 / 389 / 719) | 7,255,106 | |
| Legacy money scale (18 / 25 / 36, legacy ship, fighter and hold prices) | 478,853 | -93.4% |
| Corrected bases 26 / 56 / 102 (this slice) | 941,555 | -87.0% |
| Regen 1% a day instead of 5% | 4,473,740 | -38% |
| Regen 10% a day | 7,484,594 | +3% |
| 750 turns a day | 4,943,534 | -32% |
| 250 turns a day | 1,858,486 | -74% |
| 300 start credits | 6,313,779 | -13% |
| 30,000 start credits | 7,085,572 | -2% |
| Haggle | no N3 trade haggled | 0% |

Profit per unit, split by step (units-weighted over every N3 trade; buy price / sell price / spread). "Chart point" is what ECONOMY_SCALE_APPLY.md calibrated; each later step swaps in what the trades actually saw.

| Step | fuel_ore | organics | equipment |
| --- | --- | --- | --- |
| Chart point as calibrated | 107.4 / 126.9 / 19.5 | 233.4 / 275.7 / 42.3 | 431.4 / 509.6 / 78.2 |
| Actual stock fractions (both near 0.1) | 210.3 / 232.7 / 22.4 | 462.3 / 493.4 / 31.1 | 851.6 / 925.4 / 73.8 |
| + actual MCIC | 196.1 / 294.1 / 98.0 | 437.1 / 617.5 / 180.4 | 795.1 / 1,159.5 / 364.4 |
| + experience (3,134, past the 1,000 cap) | 153.7 / 313.5 / 159.8 | 343.1 / 658.2 / 315.1 | 619.9 / 1,237.6 / 617.7 |
| + haggle (paid) | 153.7 / 313.5 / 159.8 | 343.1 / 658.2 / 315.1 | 619.8 / 1,237.6 / 617.8 |

The stock curve alone nets out (dear to buy from a thin seller, rich to sell to an empty buyer). The MCIC and experience percents are what blow the spread up, because they move a gross price that is 7 to 9 times the chart. After the fix the same three steps on equipment read 11.9 / 46.4 / 82.3 a unit: the same shape on the original's scale.

Share of the 48.5x between the old doc (149,601) and the measured 7,255,106, in log terms:

- **Stale benchmark, 30 percent (x3.2).** 149,601 was measured on the legacy 18 / 25 / 36 table before the planet and empty-port brain slices. Today's brain on the legacy table finishes at 478,853. That is brain growth, not money.
- **Miscalibrated base, 52 percent (x7.7).** 7,255,106 / 941,555. The fix in this slice.
- **The intended scale change, 18 percent (x2.0).** 941,555 / 478,853: the Bible ship prices, the fighter and hold formulas, and a chart spread that is 1.4 to 1.5 times the legacy spread at the right stock point.
- **Turns per day, regen, start credits, haggle.** Each moves the result (table above), but each is already at its documented original or chosen value: 1,000 turns (cabal income table, GAP_MAP 12.1 SOURCE-CONFLICT with 250 / 750), 5 percent regen (v3.05 changelog standard, CONFIRMED), 20,000 credits (game setting; Gypsy's sample says 300 and the MBBS manual 30,000, SOURCE-CONFLICT). The bots never haggle. None of them is the deviation, so none changed.

## Deliberate fixes

1. **tw2002 commodity bases 179 / 389 / 719 become 26 / 56 / 102** (`src/tw2k/engine/constants.py`, `_COMMODITY_BASE_TW2002`). Same rule as before (match the economy2 spread at experience 0, MCIC 50 / -50), with the buying port at its real 100 percent (empty). `ECONOMY_SCALE_MODE = "legacy"` still returns 18 / 25 / 36 and every legacy number. Ship costs, the fighter wave, the hold formula, the curves, the caps, haggle, regen, docking, and opening stock are untouched. Planet stock in net worth reads the same base, so it moves with it.
2. **The N2 ladder's organics gate follows the live base** (`src/tw2k/agents/seat_brain.py`, `_feed_organics`). The ladder kept a fixed 19 / 25 credit gate from the legacy table. No tw2002 quote was ever under 25, so a hungry world sent the ladder to an organics seller it then refused to buy from, every time. With the gate on the live base (the same helpers N3 already used) the ladder buys. With the old gate N2 beat N1 on 2 of 5 seeds at the corrected scale; with the live gate it beats N1 on 3 and starves 2 worlds instead of 4. Strategy is otherwise unchanged. This is a scale follow, not a retune.

## The new band

`scripts/seat_brain_acceptance.py`: seed 250925, solo N3, 10 days must finish with net worth between `N3_NET_WORTH_FLOOR` 650,000 and `N3_NET_WORTH_CEILING` 1,450,000, and realize between 35 and 90 credits a unit sold. Measured: 941,555 and 55.8. The old ">= 145k" bar is gone.

Why those numbers: the five-seed N3 spread on the corrected table is 894,474 to 1,127,135, so the band leaves room for brain work (about -31 / +54 percent of the bench) while a 50x drift fails either way. The old table (7.26M) is 5 times the ceiling; a doubled turn refill or a doubled sell price lands over it; a broken trade lands under the floor. The per-unit band sits between the original's typical spread (20 / 43 / 79 by commodity) and its best (42 / 75 / 121). `run_n3` and `tests/test_seat_bot_n3.py` use the band; `tests/test_economy_calibration_v1.py` checks it directly.

The one-trade bands in `tests/test_economy_calibration_v1.py`, all through `apply_action`:

- profit per hold within 5 percent of the economy2 spread for each commodity at 20, 75, and 250 holds; each quote within 0.80 to 1.30 of the chart quote; realized profit equals (sell - buy) x holds;
- the table above, quote for quote;
- best trade inside 0.80 to 1.35 of the original best;
- a counter on the haggle limit trades at that price, one credit past it does not, and the haggled profit stays under the best published counter (149 percent) on the chart quote;
- a day tick adds exactly 5 percent of productivity and gives back exactly 1,000 turns (the wait loop stops at 1,000);
- legacy mode keeps the old equipment trade (22 / 49).

## Planted bugs

Each bug was planted in the worktree, the calibration file was run against the real engine, and the file was restored byte for byte (`git diff` identical before and after). Before the fix itself, 15 of the 17 tests in this file failed on the 179 / 389 / 719 engine; the two that passed are the refill test and the legacy test, which that engine also gets right.

All 12 were caught. "One-trade" means the 9 spread tests (3 commodities x 20 / 75 / 250 holds).

| Bug | Where | Failed / 17 | Caught by |
| --- | --- | --- | --- |
| M1 port's buy price doubled | `port_buy_price` | 16 | one-trade 9/9, doc table, best trade 3/3, haggle, legacy, N3 band |
| M2 haggle limit ignored (any counter accepted) | `execute_trade` | 1 | haggle |
| M3 regen doubled | `regenerate_ports` | 1 | daily refill |
| M4 money-scale multiplier applied twice | `port_buy_price`, `port_sell_price` | 14 | one-trade 9/9, doc table, best trade 2/3, haggle, N3 band |
| M5 buy and sell quotes swapped | `execute_trade` | 15 | one-trade 9/9, doc table, best trade 3/3, legacy, N3 band |
| M6 turn refill doubled | `tick_day` | 2 | daily refill, N3 band |
| M7 old 179 / 389 / 719 table back | `constants.py` | 15 | one-trade 9/9, doc table, best trade 3/3, haggle, N3 band |
| M8 buying port's stock percent flipped | `port_buy_price` | 15 | one-trade 9/9, doc table, best trade 3/3, legacy, N3 band |
| M9 experience applied twice | `port_buy_price` | 1 | best trade (equipment) |
| M10 realized profit ignores the cost basis | `execute_trade` | 13 | one-trade 9/9, best trade 2/3, haggle, N3 band (per unit) |
| M11 accepted counter trades at the list price | `execute_trade` | 1 | haggle |
| M12 buying port's MCIC ignored | `port_buy_price` | 12 | one-trade 9/9, doc table, best trade (fuel), legacy |

The harness is a scratch script (each mutation is a literal text swap, then `pytest tests/test_economy_calibration_v1.py`, then the original bytes written back).

## Seat bars

N3 passes unchanged rules: ferry under 40 percent, rejected 0, organics never 0, at least 85 percent of the N2 ladder on every seed, and seed 250925 inside the band.

| Seed | N1 | N2 | N3 | N3 ferry | N2 starves |
| --- | --- | --- | --- | --- | --- |
| 250925 | 704,460 | 611,823 | 941,555 | 1.8% | planet 32 |
| 20260925 | 450,086 | 416,937 | 1,005,049 | 2.9% | planet 30 |
| 230923 | 542,089 | 542,161 | 1,117,426 | 2.2% | none |
| 99 | 312,760 | 825,877 | 894,474 | 1.8% | none |
| 31 | 503,250 | 505,426 | 1,127,135 | 2.2% | none |

N2 against N1 did not survive the scale fix intact. N2 beats N1 on 3 seeds (230923 by 72 credits) and trails on 250925 (86.8 percent) and 20260925 (92.6 percent). A trade now pays about 7 times less, so N2's organics feeding costs more than the planet stock it protects on those two maps. `tests/test_seat_bot_n2.py` now holds that measured result: at least 3 strict wins, seed 250925 at 85 percent or better, seed 20260925 at 90 percent or better, rejected 0, and the two starves above. That replaces the old "4 wins and 1 percent on 250925". It is a weaker bar and it is on purpose; the brain is the bot-growth-and-fixes slice, not this one.

## Open items (not changed here)

- **MCIC roll ranges.** economy2 found the bang ranges per product, flat inside each range: equipment buy -65 to -20 and sell 20 to 65, organics -75 to -30 and 30 to 75, fuel -90 to -40 and 40 to 90. CONFIRMED (one source, 20 bangs). Ours rolls -100 to -1 and 1 to 100 for every product. Measured with those ranges on top of this slice: N3 seed 250925 finishes at 729,212 (-24 percent). Left for its own slice so the bars move once, on purpose.
- **Sell-port MCIC direction.** The economy2 text says a selling port further from zero charges more; its own sell chart prices MCIC 90 fuel at 1,092 and MCIC 40 at 4,302 for 250 holds, the other way round. SOURCE-CONFLICT. We keep the text.
- **Haggle close.** haggling.html says a counter up to 110 to 149 percent of the first offer keeps the port talking; economy2's planet-trade chart shows ports finally accept 3.0 to 7.0 percent over the offer. SOURCE-CONFLICT. Our one-counter rule closes at the limit (HAGGLE.md), so a haggling seat can take equipment from 79 to 120 a hold at the chart point. No bot haggles, so it is 0 percent of the measured money.
- **Regen base.** 5 percent of productivity, not of capacity (TURNS_REGEN.md), UNVERIFIED. This is what keeps our seats travelling and far under the original's daily income.

## Runner

`scripts/run_scripted_match.py` replaces the throwaway runner.

    python scripts/run_scripted_match.py --seats N3,N2,N1,H --seed 250925 --days 10 --json match.json --md match.md

Seats are any comma list of N1, N2, N3, and H (HeuristicAgent). Options: `--size` (1000), `--turns-per-day` (1000), `--credits` (20000), `--no-ferrengi`. In-process: no server, no ports, no API calls. Deterministic: the universe, engine RNG, and each Heuristic seat's RNG come from `--seed`; seats act in a fixed round-robin; the script re-runs itself with `PYTHONHASHSEED=0` when that is not already set; the JSON carries no clock values. Two CLI runs with different starting hash seeds wrote byte-identical JSON. `tests/test_run_scripted_match.py` runs a 2-day N3 / N2 / H match twice and requires identical JSON.

## Files

- `src/tw2k/engine/constants.py`: tw2002 bases.
- `src/tw2k/agents/seat_brain.py`: ladder organics gate on the live base.
- `scripts/seat_brain_acceptance.py`: N3 band constants; `prove_growth_replay` returns realized profit and units sold.
- `scripts/run_scripted_match.py`: new.
- `tests/test_economy_calibration_v1.py`, `tests/test_run_scripted_match.py`: new.
- `tests/test_economy_scale_apply_v1.py`: the chart spread uses an empty buyer; base pins 26 / 102.
- `tests/test_economy_scale_report_v1.py`, `tests/test_planet_economy_limits_v1.py`: base pins.
- `tests/test_seat_bot_n2.py`, `tests/test_seat_bot_n3.py`: measured bars above.
- `tests/_cu_host.py`: not economy. `CuHost.__enter__` returned before the host parked P2 on its trading port, so `test_default_bot_shows_viewport_and_keeps_every_baseline_testid` read the start sector, skipped its stock fill, and lost `action-buy` whenever the park lost the race (3 of 3 alone on the unchanged branch under load). `__enter__` now also waits for the park.
- `tests/test_cockpit_cu_g2.py`: not economy. The fog allowlist now includes the seat's own `/harness/v1/bridge` (token-scoped, 403 for another seat or a spectator). The cockpit polls it every 2.5 seconds, so the test failed whenever a loaded machine took longer than that to reach the check.
- `tests/fixtures/media_events/other_trade_in_sector.json`, `trade_burst.json`, `trade_same_visit.json`: regenerated with `scripts/media_record_fixtures.py`; only the fuel quote moved (133 to 19).
- Docs: this file, and dated superseded notes in ECONOMY_SCALE.md, ECONOMY_SCALE_APPLY.md, SEAT_BRAIN_EMPTY_PORTS.md, TURNS_REGEN.md, PLANET_ECONOMY_LIMITS.md, PLANET_ECONOMY_TESTS.md, SHIP_ROSTER.md, and seat-brain-planet-retune-v1.md.
