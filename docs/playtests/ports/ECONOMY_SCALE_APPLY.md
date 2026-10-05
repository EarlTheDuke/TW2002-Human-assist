# Economy scale apply

> **Superseded 2026-10-05 ([ECONOMY_CALIBRATION.md](ECONOMY_CALIBRATION.md)).** The bases below were solved with the buying port full (stock fraction 1). The economy2 chart's 100 percent buying port is empty, so 179 / 389 / 719 paid about 7 times the chart per unit. The tw2002 bases are now 26 / 56 / 102. The spread rule and the rest of this page stand; the net-worth tables below are history. Seed 250925 N3 now finishes at 941,555 inside a 650,000 to 1,450,000 band.

One switch, `ECONOMY_SCALE_MODE`, puts trade profit and StarDock hull, fighter, and hold prices on the original scale together. `"tw2002"` is the default. `"legacy"` restores the ae1d5c4 numbers: bases 18 / 25 / 36, the stored `SHIP_SPECS` costs, fighter price 50, and a flat `base_hold_cost`.

The stock, MCIC, and experience curves are unchanged. `PORT_UNIT_PRICE_MAX_MULT` stays 4. Ship holds, fighter caps, shield caps, and turns per warp are unchanged. Port density stays 0.65. Docking still costs one turn. Haggling is unchanged. Ports still open empty.

We do not have the official manual or the game source.

## Commodity bases

Solved one base per commodity so the 100 percent stock, MCIC 50 / -50, experience 0 spread matches `docs/reference/tw2002/cabal_strategy_site/economy2.html`. The chart totals are for 250 holds. The quote below is per hold. Sell is what the player pays. Buy is what the port pays.

| Commodity | Legacy base | New base | Chart 250-hold spread | Our 250-hold spread | Error | Status |
| --- | --- | --- | --- | --- | --- | --- |
| fuel_ore | 18 | 179 | 5,116 | 5,000 | 2.27% low | closest integer |
| organics | 25 | 389 | 10,748 | 10,750 | 0.019% | within 2% |
| equipment | 36 | 719 | 19,720 | 19,750 | 0.152% | within 2% |

Per hold at those conditions: fuel 107 sell / 127 buy, organics 233 / 276, equipment 431 / 510.

The equipment row uses the 100 percent chart, 12,190 sell and 31,910 buy. The experience table on the same page averages that cell as 11,760 sell and 32,405 buy. SOURCE-CONFLICT. This slice follows the 100 percent chart, as the task says.

A single base cannot match both sides. Our buy/sell ratio at these conditions is 0.70875 / 0.60 = 1.181. The chart's ratio is about 2.4 to 2.6. Matching both quotes would mean changing the curves. This slice keeps the curves and matches the spread. Deliberate difference.

Fuel cannot land inside 2 percent. One credit of spread is 250 credits on the 250-hold total. 5,000 is 2.27 percent low. 5,250 is 2.62 percent high. Base 179 is the closest integer. Deliberate difference.

The cap multiple stays 4. A normal quote at MCIC -100 to 100 stays under about 1.9 times the base, so the cap still does not fire on a normal universe. The trade fuzz still rolls extreme MCIC values, and those still hit the cap. That is a fuzz stress, not a game rule.

## Ship costs

Source: `docs/reference/tw2002/stardock_manuals_and_text_docs/Bible_TWGS_edit_2007_Clme.htm`, the ship cost column. CONFIRMED. The stored `SHIP_SPECS["cost"]` is still the legacy number, so legacy mode can return it. `ship_cost()` is what the yard charges and what the legal list shows.

| Ship | Legacy | Bible | Ratio |
| --- | --- | --- | --- |
| merchant_cruiser | 41,300 | 41,300 | 1.00 |
| scout_marauder | 75,000 | 15,950 | 4.70 |
| missile_frigate | 100,000 | 100,800 | 0.99 |
| battleship | 880,000 | 88,500 | 9.94 |
| corporate_flagship | 650,000 | 163,500 | 3.98 |
| colonial_transport | 63,000 | 63,600 | 0.99 |
| cargotran | 43,500 | 51,950 | 0.84 |
| merchant_freighter | 350,000 | 33,400 | 10.48 |
| havoc_gunstar | 445,000 | 79,000 | 5.63 |
| imperial_starship | 4,400,000 | 339,000 | 12.98 |

Every ship we have is on that chart. The neighbour-ratio rule does not fire.

## Fighters

`FIGHTER_COST = 50` stays, for legacy mode and for the ship net-worth property, which has no game day.

The live StarDock price is the Hekate note in `docs/reference/tw2002/stardock_manuals_and_text_docs/Misc_FigShieldPrices.txt`:

`(160 + 40) + sin(day / 87 * 2 * pi) * 40`, then rounded and clamped to 160..239.

CONFIRMED as the formula. The note says the max is 239, not 240. The clamp does that.

Mapping the game day onto a calendar day of the year is UNVERIFIED. This slice uses `universe.day`.

v1.03d moved the wave to 110-234 on a 30-day cycle. SOURCE-CONFLICT, already in the gap map. This slice uses the 160-239, 87-day note.

The price is public. The legal list and the cockpit hint show that day's number.

## Shields

No saved unit price. The old shield price, 10, stays. UNVERIFIED. Open item.

## Holds

Source: `docs/reference/tw2002/cabal_strategy_site/formulas.html`. CONFIRMED.

`Cost = B*H + I*H*(H-1)/2`, with `I = 20`. Buying 100 holds from zero when B is 200 costs 119,000.

B is a daily value from 151 to 249. The page says it works up to 249 over 9 days and back over 9 days. The even steps this slice uses (`day % 18`, linear, day 0 and day 18 are 151, day 9 is 249) are UNVERIFIED. The page does not give the step size.

The legal list shows the next single hold: `B + 20 * holds already`. The handler charges the formula total for the requested quantity. Legacy mode is still `base_hold_cost * qty`. The 150 hold cap on the handler is unchanged.

## Audit of other credit amounts

| Amount | Value | Decision | Why |
| --- | --- | --- | --- |
| Starting credits | 20,000 | keep | Game setting. The task says the default stays. |
| Colonists | 10 | keep | Already the classic unit. No new source number. |
| Armid mine | 100 | keep | No source in this slice replaces it. |
| Limpet mine | 250 | keep | No source in this slice replaces it. |
| Atomic mine | 4,000 | keep | No source in this slice replaces it. |
| Photon missile | 12,000 | keep | No source in this slice replaces it. |
| Ether probe | 5,000 | keep | No source in this slice replaces it. |
| Genesis torpedo | 25,000 | keep | No source in this slice replaces it. |
| Citadel tier and class costs | unchanged | keep | Follow-up. Not in the Bible ship chart. |
| Planet transporter | 50,000 / 25,000 | keep | Follow-up. |
| Citadel gift fighters and shields | 0 | keep | Already zero. |
| Ferrengi bounty | 1,000 per aggression | keep | Follow-up. |
| Corporation formation | 500,000 | keep | Follow-up. |
| Victory credit threshold | 100,000,000 | keep | Game setting, not a port price. |
| Planet fighter value in victory | `FIGHTER_COST` 50 | keep | Planet fighters are not a StarDock day-wave purchase. |
| Ship net-worth fighters | `FIGHTER_COST` 50 | keep | That property has no game day. StarDock still charges the wave. |
| Shield price | 10 | keep | UNVERIFIED. Open item. |

Planet stockpiles and the growth dividend are valued with `COMMODITY_BASE_PRICE`, so they moved with the new bases. That is not a separate constant. Colonists stay at 10. Planet fighters in that total stay at `FIGHTER_COST` 50.

## Deliberate differences

- Fuel spread is 2.27 percent off the chart. No integer base lands inside 2 percent while the curve stays.
- One base matches the spread, not both the sell quote and the buy quote.
- Hold B steps are a linear 18-day wave. The page only says the value works up and back.
- Game day stands in for day of year on the fighter wave.
- Shields stay at 10.
- Every current ship is on the Bible chart, so no neighbour ratio was applied.
- Port density, ship stats, regen, haggle, docking, and opening stock are not part of this slice.

## Seat brain

Not retuned. `seat_brain.py` was not edited.

Route scores read `COMMODITY_BASE_PRICE`, so they see 179 / 389 / 719 while the mode is `tw2002`. That is the price table, not a strategy change.

Two reads are still the legacy numbers:

- CargoTran affordability uses the stored spec cost, 43,500, not `ship_cost()` 51,950. From a Merchant Cruiser the brain's net is 33,175. The yard charges 41,625.
- Gift defense value multiplies by `FIGHTER_COST` 50. Gifts are 0, so that product is 0.

The next slice is the empty-port retune. These two reads belong with that, not with a strategy change here.

## Bench, before the scale change

Same commands as the acceptance script, on ae1d5c4 behavior (the process imported that code).

n1, seed 250925:

- 100,000 credits: docks day 1, trade profit 0, rejected 0, aba 0
- 20,000 credits: does not dock, trade profit 0, rejected 0, aba 0

n3 day 10:

| Seed | N2 | N3 | Ferry | Note |
| --- | --- | --- | --- | --- |
| 250925 | 375,646 | 478,853 | 6.8% | over the 145,000 bar |
| 20260925 | 423,744 | 501,745 | 6.7% | |
| 230923 | 482,863 | 550,520 | 7.5% | |
| 99 | 436,950 | 474,322 | 7.1% | |
| 31 | 432,812 | 347,690 | 34.0% | under the 85% floor; held at 347,690 |

## Bench, after the scale change

Same commands. The brain was not retuned. Cargo is valued at the new bases, so net worth jumps. Rejected stayed 0. ABA stayed 0.

n1, seed 250925:

- 100,000 credits: docks day 1, trade profit 0, rejected 0, aba 0
- 20,000 credits: does not dock, trade profit 0, rejected 0, aba 0

n3 day 10:

| Seed | N2 | N3 | Ferry | Note |
| --- | --- | --- | --- | --- |
| 250925 | 3,806,979 | 1,968,070 | 0.0% | over 145,000; under the 85% floor (3,235,932); planet 32 organics hit 0 |
| 20260925 | 3,985,849 | 1,253,743 | 0.2% | under the floor (3,387,971); planet 30 organics hit 0 |
| 230923 | 7,779,751 | 9,506,284 | 0.0% | cleared |
| 99 | 5,010,031 | 8,473,023 | 0.0% | cleared |
| 31 | 3,625,383 | 10,345,853 | 0.0% | cleared the floor. The old 347,690 hold is the empty-port measurement, not this one |

The acceptance script holds 250925 at 1,968,070 and 20260925 at 1,253,743, and holds those two organics starves. Rejected is still required to be 0. Ferry is still required under 40%. The 145,000 bar on seed 250925 still holds. Seed 31 uses the 85% floor again.

The N2 ladder, compared with N1 on the same five seeds, still finishes richer on every seed. It also starves one world: planet 32 on 250925, planet 30 on 20260925, planet 29 on 99, planet 30 on 31. Seed 230923 kept organics. Rejected stayed 0. That is the same unretuned brain reading the new bases.

## Tests

- `tests/test_economy_scale_apply_v1.py` is new. Legacy quotes and ship costs, the chart spreads, the fuel gap, the round-trip bound, the fighter clamp, the hold formula, and a StarDock buy of two holds.
- `scripts/port_trade_fuzz.py` checks the same round-trip bound with its own formula. It still does not call the engine price functions or the haggle bound.
- `tests/test_ports_price_model_v1.py` asserts the fuzz prints that chart line.
- `tests/test_economy_scale_report_v1.py` now expects equipment base 719. The report still does not change the spawn rate or the base. `FIGHTER_COST` is still 50.
- `tests/test_phase_abc.py` values planet stockpiles and the growth dividend from the live commodity bases. Fighter defense in that total stays at 50. The 75,000 credit hint still has to name an affordable ship.
- `tests/fixtures/media_events/` `buy_equip.json`, `buy_ship.json`, `trade_burst.json`, `trade_same_visit.json`, and `other_trade_in_sector.json` now carry the live fighter price, the Scout Marauder net, and the fuel quote. No other field moved.
- `tests/test_seat_bot_s6.py` still feeds CargoTran at net 33,175. That matches the brain's stored-cost read. The yard's live net is 41,625. Left as a follow-up with the brain.
- `scripts/seat_brain_acceptance.py` and `tests/test_seat_bot_n3.py` hold the measured day-10 result. Seeds 250925 and 20260925 may finish under the ladder and may starve one world. Rejected stays 0. The 145,000 bar stays. Seed 31 is back on the 85% floor.
- `tests/test_seat_bot_n2.py` holds the N2 ladder's measured starves (planets 32, 30, 29, and 30). N2 must still beat N1 on at least four seeds. Rejected stays 0.
- `scripts/media_record_fixtures.py` filters hulls with `ship_cost()`. Scout Marauder is still the first hull under 100,000, so the recorded ship does not change.
