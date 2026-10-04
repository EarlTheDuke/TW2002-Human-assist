# Planet economy limits

Measured on the engine before this slice, then the three changes the task named. Seeds are the day-10 seat-brain path (SeatBrain, 1000 sectors, 20,000 credits, planets on, Ferrengi off).

## Before: planet stock share of day-10 net worth

Stock is units times the live commodity base. Net worth is `full_net_worth`.

| seed | day | net worth | planet stock | stock share | planet assets | worlds |
| --- | --- | --- | --- | --- | --- | --- |
| 250925 | 10 | 7255106 | 161552 | 2.2% | 178522 | 1 |
| 20260925 | 10 | 7283009 | 111245 | 1.5% | 170455 | 2 |
| 230923 | 10 | 8176663 | 177459 | 2.2% | 258319 | 2 |
| 99 | 10 | 6290432 | 142969 | 2.3% | 185149 | 1 |
| 31 | 10 | 8532299 | 142969 | 1.7% | 165149 | 1 |

The millions in those scores are the rest of the seat (credits, cargo, ship). Planet stock is about 2 percent at day 10, because a genesis world is still young. The caps below do not bite that stock in ten days. Class U population does stop at 3,000, which a seeded world can reach inside the window.

## Lab table

Source files: `S1_planet_handbook_v1.01.html`, `cabal_strategy_site/glossary.html`, `classictw_museum_wiki/tw-attac_TW2002_v3_revision_history_to_v3.11.html`, `Gypsy_Big_Dummies_Guide.html`, `GAP_MAP.md` rows 6.1-6.8.

| rule | original | ours before | mark | this slice |
| --- | --- | --- | --- | --- |
| Stock in the score | A mobile planet sells its goods to the port it sits on. The revision history calls that feature "100% Planetary Trading". The glossary says you park under a buy port and sell the goods. Neither line states a credit price. | Units times `COMMODITY_BASE_PRICE` | CONFIRMED as a sell. The unit price is a chosen default. | Keep the published base (fuel 179, organics 389, equipment 719 while the scale switch is tw2002). Do not use the haggled port bid. That bid moves with hidden MCIC. The sell verb itself is not added. |
| Max colonists | Handbook column, same number on every product row of a class: M 30000, K 40000, L 40000, O 200000, C 100000, H 100000, U 3000 | No population cap. Growth is 5% when organics stock is above 0 | CONFIRMED | Clamp growth so the total stops at that number. Do not shrink a world that is already over. |
| Max stock | Handbook "Max on Planet": M 100000/100000/100000, K 200000/50000/10000, L 200000/200000/200000, O 100000/1000000/50000, C 20000/50000/10000, H 1000000/10000/100000, U 10000/10000/10000 (fuel, organics, equipment) | No stock cap | CONFIRMED | Stop production and dumps at that number. Do not shrink stock that is already over. |
| Bell curve | Production peaks at half the max population. Colonists multiply below 50% and die off above. | Flat 5% growth, production = workers times coefficient / 100 | CONFIRMED, not applied | Documented only. The cap still means something without the curve: growth and production stop at the handbook totals. |
| Five planets in a sector | Gypsy: "The Maximum number of Planets per sector: 5" | No cap | CONFIRMED | Genesis and planet transwarp refuse a sixth. A refusal does not spend the torpedo, credits, fuel, or a turn. |
| Nightly collisions | Bible mentions unstable planetary mass. Gap map marks it UNVERIFIED | Not implemented | UNVERIFIED | Not implemented. |
| Genesis starts empty | Handbook: a new planet starts with no colonists | 2500 colonists and 25 organics | CONFIRMED, different on purpose | Left as it is. The seed is under every class cap, including U at 3000. |
| Production ratios | Handbook colonists-per-unit, for example M 3/7/13 | `PLANET_PROD_COEFF` units per 100 colonists, a different matrix | CONFIRMED, different | Left as it is. |
| Class-table citadel costs | Handbook section VII | `CITADEL_COST_MODE` stays "credits" | CONFIRMED, switch stays dark | Not flipped. |
| Genesis class by crowding | One hint file | Fixed `PLANET_CLASS_WEIGHTS` | UNVERIFIED | Not implemented. |
| Scanner fog for planet fighters | Owner and fighters only via a planet scanner or landing | Shown on the observation | CONFIRMED, missing | Not this slice. |

## Switch

`PLANET_ECONOMY_MODE` defaults to `tw2002`. `legacy` keeps uncapped colonists, uncapped stock, and no five-planet limit. The stock unit price does not follow that switch. It follows `ECONOMY_SCALE_MODE`, which is the previous valuation.

## Not changed

Ships, combat, ports, the 2500 genesis seed, the production matrix, the value-tax dividend, and citadel costs. Floors stay 145k, ferry 40%, rejected 0, and the 85% bar.

Class U holds 3,000 colonists. On seed 250925 the N2 home world is class U. It reached the cap, and the ladder kept flying there to land and lift off (414 times in the day-10 replay) instead of trading. Rejected stays 0 because the legal list now publishes the remaining room and a 0 max is not the whole hold. The score does not. On that seed N2 finishes at 616459 and N1 at 631873. With the class U cap lifted, the same replay is N2 2947603 against N1 715833, which is the old N2 result. The other four seeds still have N2 ahead, rejected 0, and the same starved worlds. The 145k, ferry 40%, and 85% bars were not moved. The brain's prices and ferry rule were not retuned.

## Planted bugs

Each one was put in, the matching test failed, and the original bytes were put back.

1. `planet_stock_unit_price` returned 18. The price test expected 179 and failed.
2. Production added the whole amount and ignored the stock room. Fuel stock went to 100060 against a cap of 100000.
3. `sector_has_planet_room` returned True for every count. The sixth planet deployed.
4. A refused deploy added a genesis torpedo. The ship went from 1 to 2 with no new planet.

## After

The same five replays on the capped engine match the before table to the credit. Day-10 stock on these seeds never reached a class cap, and none of these worlds were held at the class U population cap in a way that moved the score. The seat brain was not retuned. The 145k, ferry 40%, rejected 0, and 85% bars were left where they are.
