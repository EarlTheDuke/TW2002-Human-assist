# Port price model

The quote for one unit is the base price, times how full the port is, times that commodity's hidden MCIC, times the player's experience. Haggling, turn cost, regen, and the credit scale of the base prices stay as they are.

## Original rule

**Stock percent.** Cabal `economy2.html` says the product count on a port is the trading percent. On a port that is selling, 0 product is 0 percent and it cannot sell. On a port that is buying, 0 product is 100 percent and it will buy up to its maximum. `haggling.html` says the port's offer drops when the trading percent is low. CONFIRMED. Sources: `docs/reference/tw2002/cabal_strategy_site/economy2.html`, `docs/reference/tw2002/cabal_strategy_site/haggling.html`.

**MCIC.** Maximum change in cost, one hidden number per commodity, from -100 to 100. A positive number means the port sells that product. A negative number means it buys. Further from zero, a sell port charges more and a buy port pays more. Closer to zero, buying is cheaper and selling pays less. 50 or -50 is called average. A port a player creates always sells at 50 and buys at -60. The player never sees the number. Only TEDIT does. CONFIRMED. Sources: `economy2.html`, `glossary.html` (the glossary points back at economy 2), `haggling.html`.

**How far one MCIC point moves the quote.** The equipment planet-trade chart in `economy2.html` offers 3,733,821 credits at -30 and 4,563,959 at -65, for 32,760 holds. That is about 0.55 percent of the -50 offer per point. Planet trades do not move with experience. CONFIRMED for that chart. Using the same percent on a ship quote is UNVERIFIED. There is no ship-offer formula in the library.

**Experience.** If the trade is not a planet trade, the offer depends on MCIC and the player's experience. More experience makes buying cheaper and selling pay more, up to about 1,000. The chart's averages at a +50 sell port, 250 holds of equipment, go from 11,760 credits at 0 experience to 9,097 at 1,000 (about 22.6 percent off). At a -50 buy port they go from 32,405 to 34,646 (about 6.9 percent more). Past 1,000 the samples wander and do not keep improving. Alignment does not change the offer. A planet trade does not change with experience. CONFIRMED. Source: `economy2.html`. The samples are not a straight line. Drawing a straight line between the 0 and 1,000 endpoints is UNVERIFIED.

**Productivity.** The TEDIT value F, G, or H is units per day. Capacity in holds is 10 times that value. The maximum value is 3,276 in MBBS (32,760 holds) and 6,553 in Gold (65,530 holds). CONFIRMED. Source: `economy2.html`. SOURCE-CONFLICT on the cap. We keep the MBBS number.

## What this slice does

Each commodity on a port gets an MCIC and a productivity, rolled once from the game seed and the sector. The same seed rolls the same numbers. The roll does not use the universe generator's main random stream, so sector links and starting stock stay put. Selling commodities roll 1 to 100. Buying commodities roll -100 to -1. Productivity rolls 1 to 3,276. The bang distribution is UNVERIFIED. The source never says how often each MCIC appears.

An old save that has no MCIC loads. A missing sell value is 50. A missing buy value is -60. SOURCE-CONFLICT: the page also calls -50 the average buy. The only number it assigns as a default for a buy port is -60, so that is the constant.

The price functions take the player's experience. 0 experience and the default MCIC reproduce the previous stock curve, so the base prices stay 18, 25, and 36. Experience fades in on a straight line and stops at 1,000. A higher experience never raises what the player pays and never lowers what the port pays. A federal port still quotes the base price.

Productivity is the daily refill. See `TURNS_REGEN.md`. It does not change the quote.

## Deliberate differences

- **Sell-port stock direction.** In the original, a selling port's trading percent rises with the product on hand, and the offer rises with that percent, so a full sell port charges more. This game already does the opposite: a full port is cheaper on both the buy and the sell quote, and an empty one is dearer. The slice tests require that direction, and the base scale stays. We did not flip it.
- **Straight experience line.** The chart wiggles. We use the two endpoints only.
- **0.55 percent per MCIC point on ship quotes.** Measured on planet trades.
- **Uniform MCIC roll**, not a published bang table.
- **Missing buy MCIC is -60**, not the -50 average.
- **Productivity cap is the MBBS 3,276.** Gold's 6,553 is not used.
- **Productivity does not change the quote.** It is the daily regen amount. See `TURNS_REGEN.md`.
- **Class 0 quotes the base price.** The original moves class 0 prices at midnight. Not this slice.
- **The 0-to-1 `port.experience` familiarity counter is not the discount.** It still goes up by 0.05 after a trade and still does not change the quote. The discount reads `player.experience`, which is the score in the Cabal chart.
- **Same-port round trip.** No port class both buys and sells one commodity, same as before. Buying and then selling the same good at that port cannot pay more than it cost.
- **Haggling.** A counter past the hidden limit does not trade. See `HAGGLE.md`.
