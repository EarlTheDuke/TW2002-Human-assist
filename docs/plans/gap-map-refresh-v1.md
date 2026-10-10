# gap-map-refresh-v1

Refresh of `C:\Users\sugar\tw2002_reference\GAP_MAP.md` (2026-10-03, 171 rows) against origin tip `62961c5`. Docs only. No default was changed. Line numbers are from that tip.

The 2026-10-03 tables stay in `docs/plans/GAP_MAP.md` as the baseline. Where this note and those tables disagree, this note wins. Sections 1-14 of the old map were not re-typed row by row. Every row that a later slice built, and every live-game row Commander asked for, was re-read in the code. Rows the old map already marked, and that no slice since October 3 has touched, keep that old status. Their line numbers may have moved.

Tw2002 on a mode flag is the current default for the flags named below. Legacy is the old behavior, kept for the pin.

## Plain words

The copy is much closer to Trade Wars than the October 3 map says. Bank, tavern, citadels, corporations, class 0 ports, and dock-once trading are in. The holes that still change a game are: ports open empty, a brand-new planet can be scored at about 308,000 credits, the action API says "yes" before the game has actually done the move, and the starting pocket (turns, credits, fighters, free planet) is still the bot-friendly one, not the real 250 / 300 / 30.

## Rows whose status moved

| Old row | Was | Now | Flag | Where |
|---|---|---|---|---|
| 1.6 Terra colonists | Different (no Terra) | Partial | `CLASS0_MODE` `constants.py:1553` | `class0.py` sells Terra colonists at `TERRA_COLONIST_PRICE = 0` (`constants.py:1563`). Net worth still prices each colonist at `COLONIST_PRICE` 10 (`constants.py:1097`). Live TWGS: free, 1,000 per hold. Purchase matches. Scoring does not. |
| 1.7 Class 0 ports | Missing | Partial | `CLASS0_MODE` | Alpha Centauri and Rylos exist in `class0.py`. |
| 1.8 StarDock services | Partial | Partial | `BANK_MODE` `:2098`, `TAVERN_MODE` `:2169`, `STARDOCK_EXTRA_MODE` `:2289`, `FED_MODE` `:1796` | Bank, tavern, underground, Tri-Cron (`tricron.py`), Cineplex (`cineplex.py`), and Police are in. Singles bar and the library are not. |
| 1.16 Fed protection | Different | Partial | `FED_MODE` `:1796` | `fed.py`. Deploying fighters inside FedSpace is still not the live "lose 10% of fighters and holds" rule. |
| 2.7 Trade turn cost | Different (3 per trade) | Match | `PORT_DOCK_TURN_COST = 1` `:101` | `trade_turn_cost` (`economy.py:103`) charges 1 on the first deal of a visit and 0 after that. A failed haggle that returns "the port lost patience" still spends `PORT_HAGGLE_FAIL_TURNS` 1 (`runner.py:822`). Keep that. It matches the original. |
| 2.9 Ports open empty | Different | Different | `PORT_START_STOCK_PERCENT = 0` `:99` | `universe.py:207` sets `current = maximum * 0`. The 35-95% draw is still consumed so later sectors do not move (`universe.py:206`) but it is not used as stock. Live Big Bang opens at 100%. |
| 2.10 Hold price | Different (flat) | Partial | `ECONOMY_SCALE_MODE` `:10` | `hold_next_price` (`constants.py:738`) is `hold_day_base(day) + 20 * holds_already`. Day 0 base is 151, so the 21st hold is 551. Live day 1 was 550 at 20 holds (`550 + 20 * (holds - 20)`). Same slope. The daily base still cycles 151 to 249. |
| 2.11 Fighter and shield prices | Different (50 / 10) | Partial | `ECONOMY_SCALE_MODE`, `SHIELD_PRICE_MODE = "mirror"` `:1566` | `fighter_unit_price` (`constants.py:712`) is the 160-239 wave. `class0.shield_unit_price` is the opposite wave, also 160-239. Live day 1 was fighters 188 and shields 161. Same band, not the same day's pair. `FIGHTER_COST = 50` (`:290`) remains the legacy and no-day net-worth value. |
| 2.12 Rob | Missing | Partial | `ROB_MODE` `:1332` | `rob_steal.py`. Classic vs MBBS factor is still SOURCE-CONFLICT. Live play never saw rob at alignment -4. |
| 2.13 Steal | Missing | Partial | `ROB_MODE` | Same module. |
| 2.16 Build or upgrade a port | Missing | Partial | `PORT_UPGRADE_MODE` `:2027` | `port_build.py`. |
| 3.17 Trade-in | Different (25%) | Different | none | `trade_in_credit` (`constants.py:610`) is 25% of the hull price. Live pod trade-in was itemised at 90% of each component. |
| 3.18 Several ships | Missing | Partial | `FLEET_MODE` `:1867` | `fleet.py`. |
| 3.19 Capture | Missing | Partial | `CAPTURE_MODE` `:1898` | `capture.py`. Tow lock is wired to `TOW_MODE`. |
| 3.20 Commission / ISS | Different | Partial | `FED_MODE`, `ISS_REPO_MODE` `:1805` | Commission and repossession exist. The 500 vs 2000 alignment gate is still a conflict. |
| 4.5 Cloak | Missing | Partial | `HARDWARE_MODE` `:1352` | `hardware.py`. Prices below are still the old cheap table. |
| 4.7 Mine disruptor | Missing | Partial | `HARDWARE_MODE` | `hardware.py`. |
| 4.11 Density scanner | Different | Partial | `INFO_MODE` `:1130` | `scanners.py`. Live density scanner costs 2,000 and scans cost 0 turns. Ours still charges `TURN_COST["scan"]` 1 and does not sell that hardware at 2,000. |
| 4.15 Ship TransWarp | Missing | Partial | `SHIP_TW_MODE` `:1844` | `ship_transwarp.py`. |
| 4.16 Ship transporter | Missing | Partial | `FLEET_MODE` | `fleet.py`. |
| 5.4 Sector fighters | Different | Partial | `SECTOR_FIGHTER_MODE` `:1023` | Rules exist. Wave math may still differ from formulas.html. |
| 5.12 Escape pod | Different | Partial | `DEATH_MODE` `:1111` | Pod path exists. A pod's trade-in credit is 25% of a Scout (`constants.py:617`), not the live itemised 90%. |
| 5.19 Planet landing combat | Match | Partial | `CITADEL_FIDELITY_MODE` `:811` | Fighters do not defend until citadel level 2 when fidelity is on (`runner.py` `_planet_fighters_defend`). |
| 6.2 Class-table citadel cost | Partial (table dark) | Partial | `CITADEL_FIDELITY_MODE = "tw2002"` | Tw2002 spends class-table goods and does not consume colonists (`citadel_fidelity_rules`, `constants.py:927`). `CITADEL_COST_MODE` stays `"credits"` (`:806`) and is not the path used while fidelity is on. S1 class M level 1 is 1,000 colonists. The live v3.34b screen said 1,000,000. SOURCE-CONFLICT. Slice 71 followed S1. `CITADEL_BUILD_TIME_SCALE = 0.25` (`:813`) turns the live 4 days into 1. |
| 6.5 Genesis seed | Different | Partial | `CITADEL_FIDELITY_MODE` | Fidelity puts the leftover seed colonists on the fuel-ore pool and stocks the level-1 goods (`runner.py:2098`). Legacy still seeds an idle pool. |
| 6.8 Planetary trading | Missing | Partial | `PLANET_TRADE_MODE` `:1999` | `planet_trade.py`. Fidelity holds back the next citadel's goods. |
| 8.1 Ferrengi ships | Different | Partial | `FERRENGI_MODE` `:1466` | `ferrengi.py`. |
| 8.6 Alien traders | Missing | Partial | `ALIEN_MODE` `:2391` | `alien.py`. |
| 9.1 Starting package | Different | Different | none | `STARTING_TURNS_PER_DAY` 1000 (`:238`), `STARTING_CREDITS` 20,000 (`:235`), `STARTING_FIGHTERS` 20 (`:236`). Live: 250, 300, 30, plus a free class M planet. No flag. |
| 10.1 Create a corp | Partial | Partial | `CORP_MODE` `:2303` | Live cost and size are already the tw2002 numbers: `CORP_CREATE_COST = 0` (`:2308`), `CORP_MAX_MEMBERS = 5` (`:2316`). The old `CORP_FORMATION_COST` 500,000 (`:1534`) and `CORP_MAX_MEMBERS_DEFAULT` 2 (`:1535`) remain for legacy. CEO-leaves-and-fighters-go-rogue is only partly the same rule. |
| 11.5 Galactic Bank | Missing | Partial | `BANK_MODE` `:2098` | `bank.py`. Cap `BANK_MAX_BALANCE` 500,000. Interest `BANK_INTEREST_PCT` 0. Live cap was not reached. |
| 11.6 Good-trader tax | Missing | Partial | `BANK_MODE` | `tax_on` (`bank.py:41`). Alignment below `TAX_MIN_ALIGNMENT` 0, or cash at or under `TAX_THRESHOLD` 100,000, pays nothing. Otherwise `TAX_RATE_PCT` 5 of the whole cash pile, not of the amount over the line (`constants.py:2117`). SOURCE-CONFLICT with Bible 10% over 50,000. Live hint: pirates are not taxed. A brand-new 20,000-credit trader is exempt in this code. |
| 11.7 Underground | Missing | Partial | `TAVERN_MODE` | `tavern.py`. |
| 11.8 Tavern | Missing | Partial | `TAVERN_MODE`, `STARDOCK_EXTRA_MODE` | Tavern, Grimy, Tri-Cron, Cineplex. Some prices disagree with the live session and were left unchanged. |
| 12.1 Turns per day | Match (called 1000 a match) | Different | none | Live Big Bang default is 250. Clone 1000 is a deliberate bot default, not a match. `constants.py:238`. |
| 12.2 Turn recovery | Different | Different | none | `tick_day` still refills the day in one step. Live recovery is about 250/24 turns per wall-clock hour, capped at 250. |
| 14.2 Towing | Missing | Partial | `TOW_MODE` `:1967` | `tow.py`. |

Warp cost is not the flat `TURN_COST["warp"]` of 2. `_warp_cost_for` (`runner.py:503`) uses the hull's `turns_per_warp`. The Merchant Cruiser is 3 (`SHIP_SPECS_TW2002`, `constants.py:348`), which matches the live plotter. Other hulls still disagree (BattleShip live 4, Colonial Transport live 6).

## New rows from the live TWGS game

Source: `C:\Users\sugar\tw2002_reference\live_twgs\REPORT.md` (day 1 through day 3, 8-9 Oct 2026). These are live observations on TWGS 2.20b / TW2002 v3.34b, Big Bang defaults. Where they disagree with S1, the row is SOURCE-CONFLICT. The clone column is tip `62961c5`.

| Item | Live note | Ours at 62961c5 | Status |
|---|---|---|---|
| Move turn cost | 3 turns on a Merchant Cruiser (ship TPW). 8 hops = 24 turns. | Hull TPW. Merchant Cruiser is 3. | Match for the starter hull. Partial for the roster. |
| Dock and deals | Dock 1 turn. Buy and sell deals in that visit are free. | `trade_turn_cost` does that. | Match |
| Failed haggle | A wild bid ends the trade. Docking again costs another turn. | "the port lost patience" spends 1 turn and does not fill the trade (`runner.py:822`). | Match on the turn. The window is still Different (below). |
| Day length and start | 250 turns, 300 credits, 30 fighters, 20 holds, Merchant Cruiser, free class M planet (~191,000 colonists). | 1000 / 20,000 / 20 / 20. No free planet. | Different |
| Turn refill | Not a midnight reset. About 10 to 11 turns per wall-clock hour, capped at 250. Day 2 login: 56 left became 109 after recovering 83. | Full refill inside `tick_day`. | Different |
| Port stock at start | 100% of max. Sizes seen about 1,090-2,860. | Opens at 0% (`PORT_START_STOCK_PERCENT`). Max is 3,000 plus a -500..1500 roll. | Different |
| Port regen | About 5% of max per day, continuous. StarDock fuel 1,640 to 1,689 in 7.5 hours. | `regenerate_ports` (`economy.py:242`) adds `round(productivity * 0.05)` once per day tick. Not 5% of max, and not continuous. | Partial |
| Port margins | Sell prices near the old base at full stock (fuel ~16, org ~19-35, equip ~36) and they rise as stock falls. Buy ports pay about 2x (org ~73, equip ~101-103). | Bases are 26 / 56 / 102 under `ECONOMY_SCALE_MODE` (`constants.py:23`). The October 3 curve (buy capped near 1.45x of 18/25/36) is no longer the live formula. A full-stock quote was not re-simulated here. | Different until a numbered quote is pinned |
| Price drift | About 0.5-1% against you per deal. | MCIC curve exists (`PORT_MCIC_*`, `constants.py:107`). | Partial |
| Haggle window | Accepted sells about +3% to +8%. Accepted buys about -3% to -8%. About 85% of the ask is the "taken seriously" line. Over ~130%, or several insults, ends the trade. | `PORT_HAGGLE_MIN_PCT` 110 to `PORT_HAGGLE_MAX_PCT` 149 (`constants.py:126`). That chart is a different window. | Different |
| Exp | New port +1, good trade +1, great trade +2. Warps give 0. | `XP_AWARDS` still pays for warps on the old map's row. Not re-counted in this pass. | Partial |
| Fighter, shield, hold prices | Day 1: fighters 188, shields 161. Day 2: 190 and 159. Holds: `550 + 20 * (holds - 20)`, and the same slope below 20 holds. | Wave 160-239, and the hold slope above. | Partial |
| Terra colonists | Free. 1 hold = 1,000 colonists. Terra had 30,000 on day 1. Costs 1 turn. | Purchase price 0. Net worth still uses 10 each. | Partial |
| Class M level-1 citadel | Screen text: 1,000,000 colonists, 300 fuel, 200 org, 250 equip, 4 days, 0 credits. Not built. | S1 table in `CITADEL_CLASS_COSTS["M"]` (`constants.py:817`) is 1,000 colonists and the same goods. Days scale to 1. | SOURCE-CONFLICT on the colonist count. Goods match S1 and the screen. |
| Port class numbers | 1 BBS, 2 BSB, 3 SBB, 4 SSB, 6 BSS, 7 SSS, 8 BBB, 9 StarDock, 0 Sol. Class 5 not seen. | `PORT_CLASS_TRADES` (`constants.py:68`): 1 BSS, 6 BBS, 7 BBB, 8 StarDock, 9 SSS (built ports only), 0 nothing. | Different for 1, 6, 7, 8, and 0 |
| StarDock sector | Random (this game: 351). Sector 1 is Sol, a class 0 port, plus Terra. StarDock port buys all three goods. | `STARDOCK_SECTOR = 1` (`:93`). StarDock trades nothing (`class 8`). | Different. Sector 1 as StarDock is deliberate for bots. |
| FedSpace ports | Sectors 2, 6, and 8 held normal class 3, 1, and 4 ports. | FedSpace 1-10 can hold class 0 "Federal" ports that trade nothing (`FED_OUTPOST_MODE`). | Different |
| Hardware | Genesis 20,000. Armid 1,000 and "up to 30" damage. Limpet 10,000. Atomic detonator 15,000. Ether probe 3,000. Density scanner 2,000. | `GENESIS_TORPEDO_COST` 25,000 (`:773`). `ARMID_MINE_COST` 100 and `ARMID_DAMAGE` 100 (`:768`). `LIMPET_MINE_COST` 250. | Different |
| Ships | Bible chart confirmed, except ISS at 329,000 not 339,000. Scout fighters 250. | `SHIP_COST_TW2002` (`:293`) has ISS 339,000 and Scout max fighters 150 (`:358`). | Partial |
| Corp | Create is free, 0 turns, max 5. The only member leaving kills the corp and corporate fighters go rogue. | Create cost 0 and max 5 under `CORP_MODE`. | Partial |
| Death and trade-in | Escape pod. Exp loss. Placed at StarDock. Turns and credits kept. Pod trade-in was 90% of each part (16,829). | `DEATH_MODE` pod path. Trade-in is 25%. `DEATH_CREDITS_ON_HAND = "lost"` (`:2110`) disagrees with "credits kept". | Different |
| Bank | Deposit and withdraw free. No interest seen over 9.5 hours. 22,000 left for a midnight check that this note did not wait for. | Interest 0. Cap 500,000. | Partial |
| Tax | Not observed. Grimy hint: "They never tax a pirate." | 5% of all cash when alignment >= 0 and cash > 100,000. | Partial. See game 5. |
| Ranks | Promotions roughly double: Private around 2-3 exp, then 4, 8, 16, 32. | `RANK_MODE` exists (`:1268`). Thresholds were not re-read against that ladder. | Different until re-read |
| Planet landing | Land plus liftoff on your own planet cost 1 turn total, taken on liftoff. | `TURN_COST` land 3 and liftoff 1. | Different |
| FedSpace deploy | Fighters dropped in FedSpace are annihilated. Lose 10% of fighters and 10% of holds. | Not that rule. | Different |
| Cineplex / singles bar / library | Cineplex 100 credits, flavor. Singles bar takes about one third of cash. Library is lore. | Cineplex is flavor (`STARDOCK_EXTRA_MODE`). Singles bar and library are missing. | Partial |
| Not tested live | Combat vs Ferrengi, rob/steal threshold, citadel actually built, genesis used, bank cap, overnight interest. | | |

## Live seat findings

| Item | What happened | Now | Status |
|---|---|---|---|
| Idle colonists hoarded for citadels | Game 4. Seats piled an idle colonist pool to pay citadels. | Slice 71. Fidelity puts landed colonists on the fuel-ore pool and does not spend them. Default is on. | Partial (fixed when `CITADEL_FIDELITY_MODE` is tw2002) |
| Planets with 0 shields all game | Game 4. All 22 owned planets stayed at 0 shields. | Citadel level 5 perk text still says planetary shields are not in this game (`CITADEL_PERK`, `constants.py:906`). `CITADEL_GIFT_SHIELDS_PER_LEVEL = 0` (`:878`). | Missing |
| LLM bots not arming quasar cannons | They did not buy the quasar ore. | `LLM_QUASAR_NUDGE_MODE = "on"` (`constants.py:2472`), slice 70. The nudge is a prompt, not a forced buy. Quasar still needs citadel level 3. | Partial |
| Planet reminder | Commander asked what to watch on game 5. | `LLM_PLANET_NUDGE_MODE = "tw2002"` (`constants.py:2470`). | Check, not a new gap |

What to watch on game 5, which Commander runs. Do not start another game. Does the planet reminder make an LLM seat buy a planet, and does the quasar reminder make an LLM seat arm a cannon once a citadel is level 3?

## Game 5 findings (Commander note 3, 2026-10-10)

Ben asked for these on the gap map. Each one was checked at `62961c5`.

| # | What game 5 showed | Code | Status |
|---|---|---|---|
| 1 | Ports start near empty (about 3-500 units against a max around 3,000-4,000) and a seat's own trades move the price hard. Real game: 100% stock, about 5% regen per day. | `PORT_START_STOCK_PERCENT = 0` (`constants.py:99`, `universe.py:207`). Regen is `round(productivity * PORT_REGEN_PER_DAY)` once per day (`economy.py:250`), and `PORT_REGEN_PER_DAY` is 0.05. | Different. This is the empty-port bug. |
| 2 | The daily 5% cash tax under tw2002 bank mode makes a new trader's cash shrink. | `tax_on` (`bank.py:41`) charges 5% of the whole pile only when alignment >= 0 and cash > 100,000. A trader at the 20,000 start is exempt. Crossing 100,000 pays 5% of everything, which drops them back under the line. Live play never measured this tax. Bible says 10% over 50,000. SOURCE-CONFLICT. | Partial. The shrink a player feels just over 100,000 is real. A shrink below 100,000 is not this function. |
| 3 | Net worth values a Genesis planet at about 308,000, so spamming planets pays the score. | Fidelity copies level-1 goods onto the new planet (`runner.py:2108`). `_planet_asset_value` (`victory.py:167`) prices that stock at the tw2002 base. Class U level 1 is 1,200 fuel, 400 org, 2,500 equip (`constants.py:866`): `1200*26 + 400*56 + 2500*102 = 308,600`. The 2,500 seed colonists add another 25,000 at 10 each. Real TW2002 has no net-worth score (`GAP_MAP` 12.5). | Different. Ours-only score, and the seed goods make it reward planet spam. |
| 4 | The API returns `accepted: true` when the engine then rejects the action. The real result shows up only in `recent_events`. | Harness `POST /{player_id}/action` returns `{"accepted": True, ...}` after one `asyncio.sleep(0)` (`harness.py:486`). That means the action was queued, not that the engine said ok. | Different. AI seats cannot trust the HTTP body. |
| 5 | `plot_course` with execute flies the whole route as one action, and only the first hop's cost is shown. | `_handle_plot_course` (`runner.py:2708`) walks every hop, adds each hop's turns inside the loop, then returns `turns_spent=0` so the outer call does not add them again (`runner.py:2817`). The legality check shows the first hop only (`runner.py:2751`). Real autopilot charges hops times TPW and says so. | Partial. Turns are spent. The result hides them. |
| 6 | Citadel level 1 still asks for 3,000 colonists plus goods, and ship trade-in is 25% against the real 90%. The note guessed `CITADEL_FIDELITY_MODE` was off. | The flag is `"tw2002"` (`constants.py:811`). Class U's S1 row is 3,000 colonists plus 1,200 / 400 / 2,500 goods. That is the screen. The off path is 5,000 credits and 1,000 colonists (`CITADEL_TIER_COST[0]`), not 3,000. Trade-in is 25% (`constants.py:610`). Live class M screen said 1,000,000 colonists. SOURCE-CONFLICT with S1's 1,000. | Partial on the citadel (flag is on; the 3,000 is class U). Different on trade-in. |
| 7 | `POST /P7/hold` is not a Trade Wars command. | `harness.py:490`. It keeps the scheduler on that seat. It is an AI helper. | Ours-only. Keep. |
| 8 | A failed haggle costs a turn, as in the original. | `PORT_HAGGLE_FAIL_TURNS = 1`. | Match. Keep. Do not "fix" this. |

## Ranked list for slices 73+

Impact is how much a 30-day bot game feels different from the original. Size is S (a constant and a flag), M (one system), L (several systems). Every slice stays behind its own flag. Legacy stays the current behavior so the pin `9b607d3dae940c0b1a69f6d7` does not move. Do not flip a default until Ben says so.

| Rank | Slice | Rows | Impact | Size | Why first |
|---|---|---|---|---|---|
| 1 | `port-open-full-v1` | 2.9, game 5 #1, live port stock | High | S | Ports open at 0%, so the board is empty on day 1 and one trader drains it. Live opens at 100% and regens about 5% of max per day. |
| 2 | `genesis-score-v1` | game 5 #3, 6.5, 12.5 | High | S | A class U genesis planet scores about 308,600 in goods that the torpedo just created. Planet spam wins a day-cap game. |
| 3 | `action-result-v1` | game 5 #4 and #5 | High | S | `accepted: true` means queued. `plot_course` execute spends the hops and then reports 0 turns. Seats cannot see a reject or a route cost. |
| 4 | `starting-package-v1` | 9.1, 12.1, 12.2, live start | High | M | 250 turns, 300 credits, 30 fighters, a free class M planet, and hourly turn recovery. This changes every bot. Flag default stays today's package. |
| 5 | `port-class-map-v1` | live class table, 1.5, StarDock trades | High | M | Classes 1, 6, 7, 8, and 0 do not match v3.34b. StarDock should buy goods. Sector 1 as StarDock stays until Ben says to hide it. |
| 6 | `trade-in-90-v1` | 3.17, 5.12, game 5 #6 | High | S | Yard pays 25% of the hull. Live paid about 90% of each part. |
| 7 | `haggle-window-v1` | 2.6, live haggle | Med | M | Keep the failed-haggle turn. Change the window toward the live +3% to +8% / -3% to -8% band, with a hard end. |
| 8 | `hardware-price-v1` | 4.x live prices | Med | S | Armid 1,000 / 30 damage, limpet 10,000, genesis 20,000, ether 3,000. Ours is 100 / 100, 250, 25,000, 5,000. |
| 9 | `citadel-days-v1` | 6.2, live citadel | Med | S | Needs a Ben choice. S1 says class M level 1 is 1,000 colonists. The live screen said 1,000,000. Days are scaled by 0.25 (4 becomes 1). Do not guess the colonist number. |
| 10 | `planet-shields-v1` | game 4 shields, citadel L5 | Med | M | The perk still says shields are not in the game, so every planet stays at 0. |
| 11 | `cash-tax-v1` | 11.6, game 5 #2 | Med | S | Tax 5% of all cash over 100,000, which yanks a trader back under the line. Confirm the Bible vs TWGS rate before changing it. |
| 12 | `fedspace-deploy-v1` | live FedSpace deploy | Med | S | Dropping fighters in FedSpace should cost 10% of fighters and holds, not a quiet alignment hit. |
| 13 | `own-planet-turn-v1` | live land/liftoff | Low | S | Own-planet land plus liftoff is 1 turn total. Ours is 3 + 1. |
| 14 | `stardock-sector-v1` | 1.5 | Low | M | Random StarDock and Sol in sector 1. Deliberate today. Decision, not a silent change. |

Kept on purpose, no slice: failed haggle spends a turn (game 5 #8). `POST /hold` stays (game 5 #7). Alliances, the day-cap win, and sector 1 as StarDock stay until Ben says otherwise.

Later, after these: 3d-map-research-v1 is plan only (Commander note 4). Not before the first fidelity slices.
