# Preflight 3

NOTE 124. Played on `c41b933` in the redesign cockpit. The v3.11 games used open test ports 8038 and 8039 (`free_port`, not a protected port). Seed 66066, 1,000 sectors, one seat. Ferrengi were off so the session could finish. The first v3.11 game used the real 300 credit start and 90 second days, and it ended after day 3. A second v3.11 game used a 100,000 credit test override only so 180 fighters could be bought. The profile-off pass used the same cockpit with `V311_PROFILE` unset.

One clear bug was fixed: after the game ended, the day countdown kept counting day 4. `tests/test_cockpit_preflight3_v1.py`: 1 passed. No engine change. `/bot` was not edited.

## v3.11

| Item | Result | What the screen said |
| --- | --- | --- |
| Start and land | Pass | Sector 771, uncharted space. "You are LANDED on Tester's Home." Class M, claimed by Tester, your home planet. Colonists (1000s) 45 (45,000 people), 65 (65,000), 81 (81,000). |
| Lift off | Pass | "ok — lifted off. Turns spent 1. Credits +0." |
| Day clock, while the game is running | Pass | "250/250 (full) Day 1 ends in 01:22; turns refill at dawn." Later: "Day 2 dawns. Turns come back a little at a time; you have 247 of 250. Last night: no tax." Then the same sentence for day 3 and day 4. |
| Trade | Pass | Wolf-771, class 2 (BSB): bought 8 organics at 35 cr (280 cr). Kestrel-13, class 4 (SSB): bought 1 fuel ore at 18 cr. StarDock fighters 203 cr each. |
| Prices | Pass | Port report and the trade table stayed in the tens and low hundreds: fuel 18 and 36, organics 25, 35 and 61, equipment 125, 134 and 138. Not the old 155-plus blow-up. |
| Full ports | Pass | A selling side at its cap read "Selling 4,096/4,096" and "Selling 3,038/3,038". The port report read "Fuel Ore Selling 4,095 (100%) 18 cr" after that one unit was bought. A buying side with room read "Buying, room 3,753" and "Organics: port buys, but your holds have none". No buying side was at its cap, so "port is full, it will not buy more today" did not come up. |
| StarDock | Pass | Sector 1, The Federation. "Sol-1 StarDock, Class 9 (STARDOCK)". Terra is there and cannot be claimed. |
| Warp, real move only | Pass | A plotted course "771 > 980 > 727 > 1, 3 hops, 9 turns" did not play a clip (warp plays stayed 0). Engage Express then said "Autopilot: arrived at 1 (3 hops, 9 turns)." The clip was `merchant_cruiser.headon.07` on the Merchant Cruiser. An earlier single hop 771 to 13 played `merchant_cruiser.top.08`. |
| Computer | Pass | Computer command, port report, ship catalog, and planetary specs all opened. The computer says: "Under v3.11, turns come back a little at a time all day. The day rolls on the clock, not when everyone is out of turns." |
| Planet classes | Pass | Class M Earth, 3/7/13 colonists per unit, max colonists 30000, citadel L1 through L6 with the handbook goods. Class K and class L follow it. |
| Manual | Pass | `/manual` answered 200. The page title is "Player manual - Trade Wars 2002" and the rules table marks this game Profile v3.11. |
| Fighters past 200 | Pass | Started at 30, one triangle each. Bought 180 fighters for 36,540 cr. The ship then read "Merchant Cruiser, 210 fighters" and "Fighters 210/2,500". 105 triangles in 4 clusters (54, 52, 52, 52). The caption says "each triangle = 2 fighters." 105 times 2 is 210. |
| Layout | Pass | Hide took the viewport off the deck. Move up put the ship first. Larger map stepped the map to Large. Reset layout put the order back to viewport, nav, ship, here, log, and showed the viewport again. |
| End label | Pass | "GAME OVER - time ran out after day 3. Decided by experience: 1st Tester 7. You finished 1st of 1." The day number capped at 3/3. |
| Day clock after the end | Fail, then fixed | With the game already over, the header still said "Day 4 ends in 00:20; turns refill at dawn" beside the GAME OVER panel. The countdown now hides, and the header stays 3/3. |

## Profile off

Same cockpit, profile unset, port 8038.

| Item | Result | What the screen said |
| --- | --- | --- |
| Start | Pass | Sector 1, Sol-1 StarDock. Not landed. Credits 19,000. Turns 250/250. Day 1/15. No "Day N ends in" line. |
| Fighters | Pass | 20 fighters, 20 triangles, no cluster. |
| Warp | Pass | "ok — warped 1 to 97. Turns spent 3. Credits +0." Clip `merchant_cruiser.streak.01`. |
| Empty port | Pass | Polaris-97, class 5 (SBS). "Fuel Ore: port has 0 of 4,007 to sell today (refills ~5%/day)." Organics buying, room 4,345, price 82. Equipment "port has 0 of 2,998 to sell today." Prices 38, 82 and 101. |

## Shots

- `preflight-3/v311-game-over.png` — the day-4 countdown beside GAME OVER
- `preflight-3/v311-game-over-fixed.png` — countdown gone, day 3/3
- `preflight-3/v311-ship-moved.png` — 210 fighters, clusters, layout menu, viewport hidden
- `preflight-3/v311-fighters-210.png` — StarDock class 9 and the buy result
- `preflight-3/v311-manual.png` — manual rules table, profile v3.11
- `preflight-3/legacy-warp.png` — profile off, 19,000 cr, empty port, no day countdown
