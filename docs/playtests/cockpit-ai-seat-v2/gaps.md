# Cockpit seat v2: gaps found in the 10-day run

Each row is one decision the cockpit-only seat made during run10, and what it
needed that a human at the original TW2002 screen would have had. The count is
the number of turns where the seat needed it. Rows come from the run report
(`run10.json`, `gaps`), written while the seat played.

| Decision | Turns | What the seat needed | Where the cockpit has it | Original TW2002 screen |
| --- | ---: | --- | --- | --- |
| Know whether the last move worked | 651 | The engine verdict for the action just posted | The POST answer says accepted. The verdict is in status last_result and in the log line, as the cockpit result line reads it. | The original prints the outcome right after the command |
| What price to offer on the trade form | 366 | How far the port will move on price | Not shown. A counter offer appears only inside a log line ('counter N'). The seat offers 92% on a buy and 103% on a sale. | The original port haggles in its own prompts and says 'We'll buy them for N' |
| Pick a port pair before docking | 308 | The price at a port you are not docked at | Computer R port report: class and stock, no price. The price is on the port table only while docked. | Computer R (CIM port report) also lists class, amount and percent, not the price |
| Guess a price from the port report | 308 | How a port's stock moves its price | Not shown. Rules and Help prints base prices only. The seat uses: a full port sells cheap, an empty port pays well. | Not shown either. Players learn it from the port screen over time |
| How many cargo holds to buy | 31 | What the next few holds cost in total | The StarDock form shows the next hold's price and the most you can afford, not how the price rises per hold. The seat buys 5 at a time and reads the credits. | The StarDock Hardware Emporium quotes the hold price and how many you can afford before you choose |

These listed gaps did not come up in this run: `one_way`, `counter_in_log`, `challenge_strength`.
