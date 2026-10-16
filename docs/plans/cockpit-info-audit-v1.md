# Cockpit information audit v1

NOTE 45. Compared with the original TW2002 sector display, port report, computer, V, I, planet and citadel screens, the corporation menu, StarDock, and the log. A richer map is already on the main screen. Showing more than the original is fine. A gap is P1 when a human decision cannot be made from the cockpit.

## Gap table

| info | where the original shows it | where we show it | fix |
| --- | --- | --- | --- |
| Sector, fed or uncharted, port and class, traders, ships, fighters, mines, beacon, warps | Main sector display | `#sectorText` | shown |
| Planet class on that line | Main sector display, after the name | Was the name only, though the seat view already had `class` | P1, fixed: `Name (M)` on the sector line |
| Empty holds, fighters of max, shields of max | Ship stats (I) | The bars had the fraction. I listed only the current count | P1, fixed: I says `12 of 20`, `Empty holds`, fighters of cap, shields of cap |
| Daily production on your planet | Planet screen, per product | The card printed it only when the sector brief carried `production`. The owner list already had it | P1, fixed: the card uses `owned_planets` production when the brief has none |
| Port buy/sell, room or stock, percent, price, on board | Port screen and CIM | Port table, and Computer R | shown |
| Density, warps, NavHaz, anomaly next door | Density scanner | Scan result, one line per adjacent sector | shown |
| Holo ships, fighters, planets, port | Holo scanner | Holo lines on the scan result | shown |
| Day, turns, credits, bank, net worth, rank, experience, alignment, tax | V and the header | V, and the top bar for credits, turns, experience | shown |
| Gear, including zeros | I | I lists each gear line | shown |
| Citadel cost before confirm | Planet command | Build citadel confirm | shown |
| Corp members, ticker, credits | Corporate menu | T | shown |
| StarDock prices and ship chart | StarDock and the docs | Z Rules and Help, and `GET /harness/v1/{seat}/reference` | shown, this slice |
| Current-sector NavHaz | Not on the original main display; the scanner shows the neighbors | `nav_hazard_pct` is on the sector view when it is above 0, and the sector line does not print it | P2 follow-up: print it on the sector line when the view has it |
| Avoid-list contents | Computer avoid screen | Computer O opens the form. The saved list is not printed before you type | P2 follow-up: show the current avoid list on that form |
| Experience rank table | Docs / scoring | V shows rank and experience. The points-to-rank ladder is not on the reference | P2 follow-up: add the rank ladder from the engine table, with the file cited |
| Class-M colonist trend sentence | Planet screen | On `owned_planets` only when the class-M switch is on. The card does not print `colonists_text` | P3 follow-up: one line on your class-M card when that field is present |
| 3D map | Not in the original | Out. The 2D map stays | not this slice |

## Rules and Help

Z opens Rules and Help. The same pages are `GET /harness/v1/{seat}/reference` for the bot seat, with the seat token. Sections: rules, scoring and net worth, ship stats, StarDock prices. Each section names the source file. The numbers are read from `ship_specs()` and the price helpers in `src/tw2k/engine/constants.py`. The old `GET /harness/v1/rules` prompt is unchanged.

## Colonist long-haul (candidate for the gameplay suite)

Move about 1000 colonists onto one product on a target planet. Cockpit only. Script it from `C:\Users\sugar\tw2002_reference\gameplay_test\`.

1. Sit in sector 1. The Terra line shows the pool and free holds. Press Load colonists (Terra). Take a quantity up to the free holds and the pool. Read the colonist hold on the ship panel. It rises. Empty holds on I fall by the same number.
2. Leave StarDock. Warp buttons show the next sector and the turn cost. The top bar and V show turns left. Computer, then F, plots a longer path. A plotted course does not move until ENGAGE.
3. In the target sector, the planet line shows the name and the class. Land. The confirm names the owner. Your own planet says Your planet.
4. The planet card shows colonists, product on the planet, and per day for fuel ore, organics, and equipment. That per-day line is the production figure from the owner list.
5. Press N, Colonists, and leave the holds. The card count for that product rises. The ship colonist hold falls. I empty holds rise.
6. Lift off with Q. Repeat 1 through 5 until that product's colonist count is about 1000.
7. A second planet: the card says transporter range, or No transporter (buy one). Buy transporter and Use transporter move colonists without the holds. If there is no transporter, haul them the same way as steps 1 through 5.

Success checks:

- The target product's colonist count is within 50 of 1000.
- V still shows turns left and credits, and each result line shows turns spent and the credit change.
- Each trip shows the colonist hold full on the way out and empty after the drop. I empty holds agree.
- Terra's pool, on the Terra line, drops by the number loaded.
- The source planet's card drops by the number taken, when the haul starts on a planet instead of Terra.

No step above is missing from the cockpit. The P2 and P3 rows are not required for this haul.
