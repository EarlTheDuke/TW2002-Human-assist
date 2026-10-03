# Port haggling

The port names a first offer. The player may take it, or name a counter. Each hidden MCIC allows one maximum counter, about 110 to 149 percent of that first offer. A counter past the maximum does not trade. A counter at or under it trades at the counter. A good accepted counter also earns experience, and that award is capped.

## Original rule

**First offer and one maximum counter.** Cabal `haggling.html` says that for each MCIC, and for each product, there is a fixed percentage over the port's first offer that the port will still haggle. The percentage is the same at 100 percent trading and at 1 percent. Past that percentage the port tells you to get lost, and the turn is used for nothing. The worst equipment buying port takes 110 percent. The best take almost 135 percent. The best ore ports take 149 percent. The player is not shown the MCIC. Only TEDIT is. CONFIRMED. Source: `docs/reference/tw2002/cabal_strategy_site/haggling.html`. GAP_MAP row 2.6.

**The tables are not one straight line.** The same page prints lookup tables and says the numbers are almost linear, with enough quirks that no simple formula matches every row. A fuel row at MCIC -90 is 149.4 percent. An equipment row at MCIC -20 is 110.2 percent. CONFIRMED that the tables exist and are not perfectly linear. Fitting them with one line is UNVERIFIED.

**Later rounds.** After the first counter is accepted, the port makes another offer. The page tells the player to split the difference, then close near the port's last offer. CONFIRMED as a description of play. This slice does not copy those later rounds.

**A wasted counter spends the turn you already used to dock.** The page says the turn is used for nothing. GAP_MAP row 2.7 says docking costs 1 turn and further trades at that port cost no extra turns. CONFIRMED as the original's turn. This slice does not change the 3 turns a successful trade already costs here.

**Experience.** The task states that a good accepted counter earns experience. The library's haggle page does not print the amount, and it does not print a cap. The amount and the cap below are UNVERIFIED.

**Buying from the port.** The tables are about a counter over a port's offer when the port is buying (the player is selling, including planet trades). A mirror limit under the offer when the player is buying is not in that page. UNVERIFIED.

## What this slice does

The old roll is gone. That roll was `max(0, 1 - 4 x gap)`, and a miss still traded at the list price.

The room is one line. At MCIC 0 the room is 110 percent. At an MCIC 100 points from zero it is 149 percent. Farther MCICs stay at 149 percent. The two ends and the span are the constants `PORT_HAGGLE_MIN_PCT`, `PORT_HAGGLE_MAX_PCT`, and `PORT_HAGGLE_MCIC_SPAN`.

When the player is selling, the counter may go up to that percent of the first offer, rounded to a credit. When the player is buying, the counter may go down by the same extra percent. A counter on the limit is accepted and the trade uses that price. One credit past it fails. The trade does not happen. Credits, stock, and holds stay put. The player may try again. The only words on the failure are `the port lost patience`. The limit is not in that sentence.

Omitting the counter, or naming a price that is not better for the player than the first offer, trades at the first offer. Seat bots that never haggle still trade.

A counter that is accepted and is better than the first offer adds experience. The added amount is the credit gap, and it stops at `PORT_HAGGLE_XP_CAP` (10). The ordinary 1 point for any successful trade is unchanged. A failed counter adds none.

The same port and the same MCIC always produce the same limit. There is no roll.

## Deliberate differences

- **One line instead of the lookup tables.** The page says no simple formula fits. The task asks for one range, about 110 to 149 percent, kept as constants.
- **One range for every product.** The page's best equipment port is about 135 percent, not 149. Ore is the product that reaches 149. We use that full published range for every product.
- **Buying from the port uses the same extra percent under the offer.** The tables only cover selling to the port.
- **One counter, then done.** The original keeps talking after an accepted opener. A counter at or under the limit here closes at that price.
- **A failed counter spends 1 turn, not 3.** That is the original's wasted turn. A successful trade still costs 3. Row 2.7 is not this slice.
- **Experience from a good counter stops at 10.** The library does not print this number.
