# Cockpit seat v3: the gaps after cockpit-gaps-v1

Each row is one gap the cockpit-only seat found in the v2 run10. "v2" is the
number of turns it needed the missing piece then (cockpit-ai-seat-v2/run10.json);
"v3" is the count in this run, with the cockpit block on (COCKPIT_FIELDS_MODE=tw2002).
A gap marked "not in original" is one the original TW2002 never prints either, so the
cockpit adds no hint and the seat keeps its guess there.

| Decision | v2 | v3 | Status | Where the cockpit has it now | Original TW2002 screen |
| --- | ---: | ---: | --- | --- | --- |
| Pick a port pair before docking | 308 | 0 | closed | Computer R lists this seat's own last-seen price per product with the day, at ports it docked at (cockpit.port_notes), next to the original status, amount and % of max. | Computer R (CIM port report) also lists class, amount and percent, not the price |
| Guess a price from the port report | 308 | 276 | not in original | Not printed: the original never shows a stock-to-price rule (REPORT2.md line 32 'Prices fall as the port fills'). Rules and Help lists it as not shown in the original. The seat still guesses for a port it never docked at. | Not shown either. Players learn it from the port screen over time |
| How many cargo holds to buy | 31 | 0 | closed | The StarDock holds form shows the next-hold price, how many you can afford and, once an amount is typed, the total before CONFIRM (cockpit.hold_quote). | The StarDock Hardware Emporium quotes the hold price and how many you can afford before you choose |
| Plan a route back | 0 | 0 | same as original | Computer K lists warps for visited sectors only, as the original's CIM warp data. | Same in the original: CIM warp data covers explored sectors only |
| Know whether the last move worked | 651 | 0 | closed | The verdict field under the command keys: OK or REFUSED, the reason, turns spent and the credits change (cockpit.verdict). It survives a reload. | The original prints the outcome right after the command |
| What price to offer on the trade form | 366 | 366 | not in original | The trade form shows the port's quote, each counter and how the haggle ended. The accept band is not printed, as in the original. The seat still offers 92% on a buy and 103% on a sale. | The original port haggles in its own prompts and says 'We'll buy them for N' |
| Answer a port's counter offer | 0 | 0 | closed | The trade form shows the counter and the next offer (cockpit.haggle). | The original port prompt prints its counter price |
| Answer a fighter challenge or a Ferrengi | 0 | 0 | same as original | The challenge shows the enemy fighters and your own, as the original. | The original shows the fighter count and your own fighters on the same screen |
