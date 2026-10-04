# Economy scale

Do not change a number from this note. The original trade pays much more per hold than our 18 / 25 / 36 bases, and several of our ships cost several times the 2007 Bible chart. Moving only one of those would change how many round trips a starter needs to buy a ship. The measured tables are from `scripts/economy_scale_report.py`.

## Lab table

**2.5 Price scale vs ship cost.** A sell port at MCIC 50, 100 percent stock, zero experience, no haggle, asks 12,190 credits for 250 holds of equipment (48.76 a hold). A buy port at MCIC -50 on the same terms offers 31,910 (127.64 a hold). Source: `docs/reference/tw2002/cabal_strategy_site/economy2.html`, the 100 percent charts. An earlier table on that same page averages the sell side at 11,760 and the buy side at 32,405 for MCIC 50 and -50. SOURCE-CONFLICT between those two tables. Both are about the GAP_MAP figures of 47 and 130. Our bases are `COMMODITY_BASE_PRICE` fuel 18, organics 25, equipment 36. The report prints our quote beside the 100 percent chart.

**2.10 Class 0 hold price.** Cost = (B * H) + ((I * H) * (H - 1)) / 2. I is always 20. B is a daily value tracked from 151 to 249. CONFIRMED. Source: `docs/reference/tw2002/cabal_strategy_site/formulas.html`. The Bible chart also prints a single "cost to max holds" beside each ship. Our price is a flat `base_hold_cost` on `SHIP_SPECS`, 500 to 2000 per hold, with no daily B and no +20 each hold.

**2.11 Fighter and shield prices.** Fighters: price = (160 + 40) + sin(day / 87 * 2 * pi) * 40, so the wave runs 160 to 239. The note says the max is actually 239. CONFIRMED as that note. Source: `docs/reference/tw2002/stardock_manuals_and_text_docs/Misc_FigShieldPrices.txt`. A v1.03d note of about 110 to 234 on a 30-day cycle is the SOURCE-CONFLICT already in GAP_MAP. Shields are said to move the other way. No single shield unit price is in the saved files. UNVERIFIED. Ours: `FIGHTER_COST` = 50, and shields are 10 in `_handle_buy_equip`.

**1.10 Port density.** Big Bang sample: "40% Port Density" and "95% Built Port Density". CONFIRMED. Source: `docs/reference/tw2002/classictw_docs_wiki/Big_Bang.html`. Ours: `PORT_SPAWN_PROBABILITY` = 0.65 on sectors past FedSpace, plus the Federal ports. The report measures nearest buy/sell pair distance at 0.65 and at 0.40 on 20 seeds. It does not leave the constant changed.

## What a round trip means here

Fresh stock means the port is at 100 percent, which is the assumption written on the economy2 charts. A typical quote uses experience 0, MCIC 50 on a commodity the port sells, and MCIC -50 on a commodity the port buys. A best quote uses experience 1000, MCIC 1 on a sell, and MCIC -100 on a buy, still at 100 percent stock. Profit per hold per round trip is the best one-way spread plus the best spread back. Class 7 buys everything, so it has no round trip.

## Measured

At 100 percent stock, experience 0, MCIC 50 / -50, our spread against the 100 percent chart is 10.23 times smaller on fuel (2 credits a hold versus 20.46), 14.33 times on organics (3 versus 42.99), and 19.72 times on equipment (4 versus 78.88). The best typical round trip in our classes is 7 credits a hold. The chart's equipment leg plus organics leg is 121.87. That ratio is 17.41. Four pairs tie at 7: BSB/SBS, BSB/BBS, SSB/SBS, SSB/BBS. The best quote, experience 1000 and the extreme legal MCIC, reaches 39 on those pairs.

A 20-hold starter on the chart needs 16.9 round trips for a Merchant Cruiser and 36.3 for a Battle Ship. On our prices the same ships take 295 and 6,286 trips. Merchant Cruiser cost already matches the Bible at 41,300. Battle Ship is 9.94 times the Bible, Merchant Freighter 10.48, Imperial StarShip 12.98. CargoTran is 0.84 of the Bible, so ours is cheaper. Missile Frigate and Colonial Transport are within 1 percent.

Nearest buy/sell partner, 20 seeds from 250925, default universe size, planets and Ferrengi off so only the spawn rate moves: mean distance 1.26 hops at 65 percent and 1.59 at 40 percent. The closest pair on every map is 1 hop either way.

## Choices

- **A.** Multiply `COMMODITY_BASE_PRICE` by about 17.41 (fuel 18 becomes about 313, organics 25 about 435, equipment 36 about 627). Leave `SHIP_SPECS` costs. One multiplier cannot hit the three commodity ratios 10.23, 14.33, and 19.72 at once, because our stock curve is not the original curve. The round-trip count for a cruiser falls from 295 to about 17. A Battle Ship stays 880,000 credits, so it still takes about 360 trips against the Bible's 36.
- **B.** Set each `SHIP_SPECS` `cost` to the Bible ship-cost column (Battle Ship 88,500, Freighter 33,400, Havoc 79,000, Flagship 163,500, Imperial 339,000, Scout 15,950, CargoTran 51,950). Leave the bases. Profit per hold stays 7, so the cruiser is still 295 trips against the chart's 17. War stays cheap because `FIGHTER_COST` stays 50.
- **C.** Do A and B together, and in the same slice replace `FIGHTER_COST` = 50 with the 160 to 239 day wave, and replace flat `base_hold_cost` with the hold formula (I = 20, B in 151 to 249). Shields stay open: the saved files have no unit price. A 20-hold starter then needs about 17 trips for a cruiser and about 36 for a Battle Ship, which is the chart.

**Recommend C.** A alone leaves our big ships about ten times too far away. B alone leaves every ship about seventeen times too far away. C is the one that keeps ship price divided by profit per hold on the original scale. Port density is a separate knob: 40 percent adds about a third of a hop, which is not the break. What has to be redone later, not here: the seed 250925 seat-brain bench, the recorded trade quotes, and the trade fuzz, because those pin today's bases and today's ship costs.

## Known effects

Day-1 empty ports and the seed 31 bench stay as written in `TURNS_REGEN.md`. This note does not retune the brain.
