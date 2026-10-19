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

## NOTE 95 (2026-10-19): the seat on V311_PROFILE

The table above is the NOTE 56 run with the cockpit block on and the profile off.
These rows are the cockpit-only seat on a test server with V311_PROFILE=v311
(seed 250925, 10 days, port 9181). The seat still used only its four routes.
A row is a decision the routes do not carry, so the seat guessed.

| Decision | Turns | What the seat needed | Where the cockpit has it | Original TW2002 screen |
| --- | ---: | --- | --- | --- |
| Pick a port pair before docking | 413 | The price at a port you are not docked at | Computer R port report: class and stock, no price. The price is on the port table only while docked. | Computer R (CIM port report) also lists class, amount and percent, not the price |
| Guess a price from the port report | 413 | How a port's stock moves its price | Not shown. Rules and Help prints base prices only. The seat uses: a full port sells cheap, an empty port pays well. | Not shown either. Players learn it from the port screen over time |
| Know whether the last move worked | 360 | The engine verdict for the action just posted | The POST answer says accepted. The verdict is in status last_result and in the log line, as the cockpit result line reads it. | The original prints the outcome right after the command |
| How many cargo holds to buy | 167 | What the next few holds cost in total | The StarDock form shows the next hold's price and the most you can afford, not how the price rises per hold. The seat buys 5 at a time and reads the credits. | The StarDock Hardware Emporium quotes the hold price and how many you can afford before you choose |
| What price to offer on the trade form | 133 | How far the port will move on price | Not shown. A counter offer appears only inside a log line ('counter N'). The seat offers 92% on a buy and 103% on a sale. | The original port haggles in its own prompts and says 'We'll buy them for N' |
| Warp into a sector the cockpit has not described | 6 | Mines, fighters and NavHaz in the next sector | The adjacent row lists them only after a scan. This seat cannot afford a scanner on the v3.11 stake, so it learns a sector from the event after it enters. | The original also hides mines and fighters until a scanner or a hit |
| Answer a fighter challenge or a Ferrengi | 1 | Whether attacking would win | The challenge shows the enemy fighter count. The seat compares it to its own fighters and prefers pay or retreat. | The original shows the fighter count and your own fighters on the same screen |

Breaks the seat client now handles, still from those four routes: it lifts off the
home world before warp or trade, waits out HTTP 429 on the live action route and
reads the cockpit again instead of replaying a stale post, drops a plotted course
the route refused, and does not warp back into a sector it retreated from or one
an event already named for mines or NavHaz.

The scripted Terra run (terra-citadel.json) moves the Terra colonist pool onto
the home world. The class M level-1 form, read from citadel_next_build on the
same observation, asks for 1,000,000 colonists. The pool plus the home start
does not reach that, so the build does not start. That figure is on the route;
it is a stake the seat cannot meet, not a missing field and not an engine change.
