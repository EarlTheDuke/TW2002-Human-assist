# gap-map-refresh-v6

Plan only. Every October row, regraded at `60b17fef` (branch `track-g-note108`, cut from `feature/grokbot-player`). v5 graded the same 171 ids at `f969cee`. This pass does not add a switch. Helper row 164 stays unused.

A row is Match when the original rule is what a normal game does now. Match-behind-flag means the original rule is coded and the named switch stays off until `V311_PROFILE` is `v311`, unless the profile section says that helper is left out on purpose. Partial means part of the rule is in. Different means a normal game still does something else. Missing means this pass found no handler. Ben-decision is a number Ben has not chosen. Class M colonists and a random StarDock stay there.

`docs/plans/GAP_MAP.md` is the October 3 baseline refreshed to `62961c5`. Its own header says those counts are the October picture. v5 already replaced that picture. This file replaces v5. Grades below are from the tip code, not from that October table.

## Counts

| Grade | v5 | v6 |
|---|---|---|
| Match | 50 | 72 |
| Match-behind-flag | 17 | 86 |
| Partial | 53 | 10 |
| Different | 38 | 1 |
| Missing | 11 | 0 |
| Ben-decision | 2 | 2 |
| Total | 171 | 171 |

NOTE 163 moved five rows that were still Partial. 6.7 and 9.2 are Match. 6.11, 9.5, and 13.4 are Match-behind-flag. The new switch is `BOUNTY_GOOD_MODE` row 187. Row 181 is NavPoints (`NAVPOINT_MODE`, NOTE 159). NOTE 162 uses rows 182-186 and moves 21 more rows. 14.1 is Match-behind-flag through `CIM_MODE` row 186. NOTE 164 moves 8.1 and 12.6 from Partial to Match-behind-flag. The ship switch and the fighter-report switch sit on 6.11 and 13.4 and do not grade those rows again.
NOTE 177 moved five more Partial rows. 5.14, 5.20, and 9.8 were already the original and are Match. 6.10 (`PLANET_BLOW_ALIGN_MODE` row 214) and 10.1 (`CFS_CEO_USE_MODE` row 213) are Match-behind-flag after the rulings in `V311_SOURCE_CONFLICTS.md`. 8.1 is counted once, under NOTE 164's `FERRENGI_ODDS_MODE`.
NOTE 178 moved two Different rows to Partial. 5.7: the tw2002 exchange already in the code is the S4/S6 Safety Rating model (chosen count, per-attack cap, hull odds, shields first, flee); only the exact loss split is unprinted. 14.6: the instant credits win is off under `ECON_WIN_MODE` row 215; alliances and play_to_day_cap stay. 11.11 stays Partial: bubbles are Gold-only (S1). 12.3 (real-time movement) stays Different: the game is turn-based by design and no speed table is printed. 12.4 stays Partial: every nightly job the sources name (MSL sweep and level-2 cap, tows, cloak fails, corp penalty, colonist trim, break-in alignment) is already in `tick_day`; no further job is printed. 2.5 is an economy call, not a source call.

## What moved

The v5 "no switch at all" list now has a switch on this tip: planet scanner, scanner fog, citadel perks, citadel parking, the good-trader tax, radio, daily stats, FedComm, gold aliens, and corporation rankings. Gold aliens are coded and off, and the profile leaves `GOLD_ALIEN_MODE` out on purpose. Density, one-way lanes, the 45-hop plot cap, Class 0 hold prices, the treasury cap, Ferrengi pace and grudges, and the planet-bust experience loop moved in NOTEs 78 through 102. Player-kill experience (`COMBAT_EXP_DIVISOR` 15/35/25) and the ether-probe route are already what a normal game does, so those rows are Match. Corp member transfers of credits, fighters, shields, and mines are in `corp.handle_corp_transfer`. Holds and the corp treasury are `CORP_CARGO_TREASURY_MODE` row 183, NOTE 162.

## Diff, v5 to v6

Only rows whose grade changed. Evidence is `file:function`.

| Row | v5 | v6 | Evidence |
|---|---|---|---|
| 1.2 | Different | Match-behind-flag | `ONE_WAY_SHARE_MODE` row 88, NOTE 78. Extra two-way lanes are `TWO_WAY_WARP_MODE` row 178, NOTE 157. `constants.one_way_fraction_for`, `constants.two_way_edge_target` |
| 1.3 | Different | Match-behind-flag | `COURSE_MAX_MODE` row 86, NOTE 78. `constants.plot_course_hop_limit`, `runner._handle_plot_course`. 45 is UNVERIFIED |
| 1.9 | Partial | Match-behind-flag | `FERRENGAL_QUASAR_MODE` row 102, NOTE 85. `runner._apply_ferrengal_quasar` |
| 1.10 | Different | Match-behind-flag | `BIG_BANG_DENSITY_MODE` row 87, NOTE 78. `universe.generate_universe` |
| 1.11 | Different | Match-behind-flag | same switch. `universe._seed_planets` |
| 1.18 | Different | Match-behind-flag | same switch. `universe._place_decorative_fed_ports` |
| 2.2 | Different | Match-behind-flag | `PORT_CLASS_MAP_MODE` row 10 and `PORT_CLASS_NUMBER_FIX_MODE` row 142, NOTE 98. Class 8 stays the StarDock id |
| 2.6 | Partial | Match-behind-flag | `HAGGLE_LIVE_MODE` row 31. `economy.haggle_bound` |
| 2.9 | Different | Match-behind-flag | `PORT_STOCK_FIDELITY_MODE` row 51. `universe._make_port`, `economy.regenerate_ports` |
| 2.10 | Different | Match-behind-flag | `CLASS0_HOLD_FORMULA_MODE` row 109, NOTE 87. `constants.class0_hold_formula_live` |
| 2.14 | Partial | Match-behind-flag | `BUST_CLEAR_MODE` row 94, NOTE 82. `rob_steal.busts_clear_this_extern` |
| 3.1 | Partial | Match-behind-flag | `SHIP_ROSTER_MODE` row 4. `constants.ship_specs` |
| 3.2 | Partial | Match | stored Merchant Cruiser already matches `SHIP_ROSTER_LIVE_TABLE` on cost, holds, fighters, turns, odds. `constants.ship_specs` |
| 3.3 | Different | Match-behind-flag | `SHIP_ROSTER_MODE`. Scout fighters 250 and initial holds 10. `constants.ship_specs` |
| 3.4 | Partial | Match-behind-flag | `SHIP_ROSTER_MODE`. Frigate initial holds 12. `constants.ship_specs` |
| 3.5 | Different | Match-behind-flag | `SHIP_ROSTER_MODE`. Battleship initial holds 16. Both tables price it at 88,500. `constants.ship_specs` |
| 3.6 | Partial | Match-behind-flag | `SHIP_ROSTER_MODE`. Flagship initial holds 20. `constants.ship_specs` |
| 3.7 | Different | Match | stored Colonial Transport already matches the live six-field tuple. `constants.ship_specs` |
| 3.8 | Different | Match-behind-flag | `SHIP_ROSTER_MODE`. CargoTran initial holds 50. `constants.ship_specs` |
| 3.9 | Different | Match-behind-flag | `SHIP_ROSTER_MODE`. Freighter initial holds 30. `constants.ship_specs` |
| 3.10 | Partial | Match-behind-flag | `SHIP_ROSTER_MODE` for initial holds 12. Ship TransWarp is already `SHIP_TW_MODE` tw2002 via `constants.ship_tw_on` |
| 3.17 | Partial | Match-behind-flag | `TRADE_IN_MODE` row 13 and `TRADE_IN_PARTS_MODE` row 76. `constants.ship_cost` |
| 4.2 | Partial | Match-behind-flag | `ATOMIC_DETONATOR_MODE` row 89, NOTE 78. `runner._handle_deploy_atomic` |
| 4.6 | Different | Match | the probe walks a route and dies at hostile fighters. `scanners.handle_probe`. `PROBE_MAX_HOPS` is 45 |
| 4.8 | Different | Partial | price is `HARDWARE_PRICE_MODE` row 14. Detonation is already `hardware.armid_detonation_hits` (profile row 92, no helper) |
| 4.10 | Different | Partial | frigate and ISS already carry the photon cap in `SHIP_SPECS_TW2002`. A follower's quasar damp is `PHOTON_FOLLOW_DAMP_MODE` row 90, NOTE 79. A full sector shutdown is not in |
| 4.11 | Different | Match | a density scan needs the bought device. `scanners.scan_reason`. Profile row 100 unused |
| 4.12 | Different | Match | a holo scan needs the bought device. `scanners.scan_reason`. Profile row 103 unused |
| 4.13 | Missing | Match-behind-flag | `PLANET_SCANNER_MODE` row 43. `runner._buy_planet_scanner`, `observation._planet_brief` |
| 4.17 | Partial | Match-behind-flag | `SHIP_CHART_CAP_MODE` row 96, NOTE 82. Probe cap 25. Other chart caps are already on `SHIP_SPECS_TW2002` |
| 5.3 | Different | Match | armids already detonate `count // 2` at 20, or 30 on the live shop card. `hardware.armid_detonation_hits`. Profile row 92 |
| 5.4 | Different | Match-behind-flag | `OFFENSIVE_CLASH_MODE` row 7. `combat.offensive_wave_size` |
| 5.10 | Partial | Match-behind-flag | `SPECIAL_HULL_RULES_MODE` row 105, NOTE 86. `combat.hull_interdict_reason`. Needs `ship_roster_live` |
| 5.12 | Partial | Match-behind-flag | `DEATH_POD_MODE` row 29. `combat._strip_ship` |
| 5.13 | Different | Match-behind-flag | `DEATH_DELAY_MODE` row 93, NOTE 79. `runner.tick_day` |
| 5.19 | Match | Match-behind-flag | `PLANET_LANDING_COMBAT_MODE` row 54. Legacy seizes a defended planet. `constants.planet_landing_combat_on` |
| 6.1 | Missing | Match-behind-flag | `SCANNER_FOG_MODE` row 44. `observation._planet_brief` |
| 6.9 | Missing | Match-behind-flag | `CITADEL_PARK_MODE` row 45. `fleet.citadel_home` |
| 6.11 | Different | Match-behind-flag | planets stay `CORP_PLANET_DISBAND_MODE` row 97, NOTE 82. Parked ships in the C.E.O.'s sector are `CORP_SHIP_DISBAND_MODE` row 201, NOTE 164. `corpships.on_corp_extinct` |
| 6.12 | Different | Partial | destroy experience 50 is already `constants.xp_award`. Alignment stays `PLANET_DESTROY_ALIGNMENT_TW2002` = 1. No switch for that conflict |
| 6.14 | Different | Match-behind-flag | `CITADEL_PERK_MODE` row 27. `runner._handle_set_military_reaction` |
| 7.5 | Different | Match-behind-flag | `TREASURY_CAP_MODE` row 85, NOTE 78. `runner._handle_deposit_treasury` |
| 8.2 | Different | Match-behind-flag | `FERRENGI_ENGAGE_MODE` row 58. `constants.ferrengi_engage_on` |
| 8.3 | Different | Match-behind-flag | `FERRENGI_PACE_MODE` row 107 and `FERRENGI_GRUDGE_MODE` row 106, NOTE 86. `runner.tick_day` |
| 8.4 | Partial | Match-behind-flag | `FERRENGI_REWARD_MODE` row 101, NOTE 85. `combat._grant_ferrengi_kill` |
| 8.7 | Partial | Match-behind-flag | `FED_SHIPS_MODE` row 33. `fed.place_fed_starships` |
| 8.9 | Missing | Match-behind-flag | `GOLD_ALIEN_MODE`. `alien.note_gold_grudge`. Not in `V311_PROFILE_HELPERS`. The profile doc leaves it off (Gold add-on) |
| 9.3 | Different | Match | `COMBAT_EXP_DIVISOR` opposite 15 / same 35 / neutral 25 and `KILL_EXP_SHARE` 0.10. `victory.combat_rewards`, `victory.kill_rewards`. Profile row 91, no helper |
| 9.7 | Missing | Match-behind-flag | `CITADEL_PERK_MODE` row 27. L2 and L5 are the coded perk set. `constants.citadel_perk_live` |
| 9.9 | Partial | Match-behind-flag | `MIXED_CORP_EXP_RULE` row 72. `corp.mixed_loss` |
| 10.3 | Match | Match-behind-flag | `CORP_ALIGNMENT_RULE` row 71. Stored value stays mixed. `corp._join_block` |
| 10.10 | Partial | Match | a C.E.O. who leaves already dissolves the corp. `corp.handle_corp_leave`, `corp.disband`. Profile row 98, no helper |
| 10.11 | Missing | Match-behind-flag | `CORP_RANK_MODE` row 49. `observation.build_observation` |
| 11.1 | Partial | Match-behind-flag | `HARDWARE_PRICE_MODE` row 14. `constants.hardware_price_live` |
| 11.2 | Partial | Match-behind-flag | `SHIP_ROSTER_MODE` row 4 and `TRADE_IN_MODE` row 13. `constants.ship_specs` |
| 11.6 | Missing | Match-behind-flag | `TAX_RULE_MODE` row 8. `bank.collect_daily_tax` |
| 11.10 | Partial | Match-behind-flag | `SPECIAL_PORT_DEFENCE_MODE` row 146, NOTE 102. `runner._attack_special_port`, `runner._rebuild_special_ports`. Fighter budgets UNVERIFIED |
| 12.5 | Different | Match-behind-flag | `EXP_SCORE_MODE` row 28. `victory.check_victory` |
| 12.7 | Missing | Match-behind-flag | `DAILY_STATS_MODE` row 47. `observation.build_observation` |
| 13.2 | Missing | Match-behind-flag | `RADIO_CHANNEL_MODE` row 46. `runner._handle_radio` |
| 13.5 | Different | Match | the report is the route, and the probe dies on hostile fighters. `scanners.handle_probe` |
| 13.6 | Missing | Match-behind-flag | `FEDCOMM_MODE` row 48. `class0.extern_sweep` |
| 14.3 | Different | Match-behind-flag | `PLANET_BUST_EXP_MODE` row 149, NOTE 102. `legality.planet_destroy_reason`. Genesis 25 plus destroy 50 |

## Still open

These rows are still Partial, Different, or Missing, and no switch names the remaining original rule. Ranked by how a 30-day, mostly-bot game would feel them. Size is the slice, not the calendar. A row marked NOTE 104 would have to touch `src/tw2k/engine/universe.py`, `src/tw2k/engine/economy.py`, `src/tw2k/engine/constants.py`, or the lobby (`src/tw2k/public/lobby.py`, `pages.py`, `worker.py`, `src/tw2k/server/runner.py`). This pass does not edit those files. Row 164 is not the place to start one of them.

| Rank | Row | Grade | Size | Why it still shows | Files | NOTE 104 |
|---|---|---|---|---|---|---|
| 1 | 2.5 | Match-behind-flag | L | Ruled R3 A: ports quote the economy2 chart (`ECONOMY_SCALE_MODE`, price scale) and ships the Bible chart; no source welds them. Port maximums are the printed 950 to 2,720 (`PORT_MAX_STOCK_MODE` row 223), so a pair drains as in economy3 | `economy.port_sell_price`, `universe._make_port` | test_port_max_stock_v1.py |
| 2 | 5.7 | Partial | L | NOTE 178: the Safety Rating model is coded; the exact loss split is unprinted. CMB-c is a plan doc only | `combat._resolve_ship_attack_tw2002` | |
| 3 | 12.3 | Different | L | Movement is still by turns. `DAY_ROLL_CLOCK_MODE` rolls the day. `PLANET_REALTIME_PROD_MODE` is left off because the original produces at Extern | `runner.apply_action`, `constants.day_roll_clock_live` | constants.py, server runner, lobby |
| 6 | 12.4 | Partial | M | Busts, tows, sweeps, and NavHaz already run in `runner.tick_day`. Collisions and special-port rebuilds are `PLANET_COLLISION_MODE` and `SPECIAL_PORT_DEFENCE_MODE`. The jobs past that list have no switch | `runner.tick_day` | |
| 11 | 1.15 | Partial | S | A tow fires at 99 fighters (`FED_TOW_FIGHTER_LIMIT` 98). The Bible line is 50. No switch | `fed.run_tows` | constants.py |
| 23 | 11.11 | Partial | S | Density, one-way share, and the 30 percent two-way lanes are flagged (rows 87, 88, and 178). Bubbles, the course-length generator, and the Gold options are not | `universe.generate_universe` | universe.py |
| 35 | 14.6 | Partial | L | NOTE 178: no instant credits win under `ECON_WIN_MODE` row 215. Alliances and play_to_day_cap stay | several | |

Rows that are Partial only because a named switch stays off are Match-behind-flag above, not in this list. `12.4` stays here for the jobs that still have no name.

## Profile check

Ran on `60b17fef`. `v311_profile` in `constants.py` returns true only when the module global `V311_PROFILE` equals `"v311"`. It does not read the environment. `V311_PROFILE=1 python3 -c "import tw2k.engine.constants as K; print(K.v311_profile())"` printed `False` and left the global at `"legacy"`.

The check that matches the code set `K.V311_PROFILE = "v311"` after import and called every helper in `V311_PROFILE_HELPERS`. All 114 returned true. None returned false.

`docs/plans/v311-profile-v1.md` heading is "114 helpers". That matches the dict. `tests/test_tw2002_live_profile_v1.py` `HELPERS` has 123 names (`assert len(names) == 123`). This pass does not edit either file.

Helpers in the test tuple that stay false when only `V311_PROFILE` is `v311`:

- `ai_cockpit_seat_on` (`AI_COCKPIT_SEAT_MODE`)
- `alignment_live` (`ALIGNMENT_MODE`)
- `alliance_live` (`ALLIANCE_MODE`)
- `async_day_live` (`ASYNC_DAY_MODE`)
- `bank_live` (`BANK_LIVE_MODE`)
- `cockpit_fields_on` (`COCKPIT_FIELDS_MODE`)
- `cockpit_parity_live` (`COCKPIT_PARITY_MODE`)
- `combat_odds_live` (`COMBAT_ODDS_MODE`)
- `corp_rules_v2_live` (`CORP_RULES_V2_MODE`)
- `gold_alien_live` (`GOLD_ALIEN_MODE`)
- `planet_class_live` (`PLANET_CLASS_MODE`)
- `planet_realtime_prod` (`PLANET_REALTIME_PROD_MODE`)
- `rank_titles_live` (`RANK_TITLES_MODE`)
- `seat_deadline_live` (`SEAT_DEADLINE_MODE`)
- `trade_turn_live` (`TRADE_TURN_MODE`)
- `universe_topology_live` (`UNIVERSE_TOPOLOGY_MODE`)
- `warp_cost_live` (`WARP_COST_MODE`)

`gold_alien_live` and `universe_topology_live` turn on for `tw2002_live_profile`, not for `v311_profile`. The profile doc's "Left as they are" table already says both stay out.

Helpers in `V311_PROFILE_HELPERS` that are not in the test tuple: `action_result_report`, `citadel_fidelity_rules`, `corp_exp_penalty_taken`, `corp_join_check`, `corp_leaver_to_ceo`, `day_roll_clock_live`, `genesis_score_fair`, `mixed_corp_least_extreme`.

`*_MODE` and `*_RULE` symbols that exist in `tw2k.engine.constants` and are not the switch named by any `V311_PROFILE_HELPERS` entry (74). Not fixed.

`AI_COCKPIT_SEAT_MODE`, `ALIEN_FLEE_RULE`, `ALIEN_KILL_EXP_RULE`, `ALIEN_MODE`, `ALIGNMENT_MODE`, `ALLIANCE_MODE`, `ASYNC_DAY_MODE`, `BANK_LIVE_MODE`, `BANK_MODE`, `BOTS_BANK_MODE`, `BOTS_DEPLOY_MODE`, `BOTS_TAVERN_MODE`, `BOTS_WAR_MODE`, `BUY_RESERVE_MODE`, `CAPTURE_MODE`, `CAPTURE_RULE`, `CFS_CEO_RULE`, `CITADEL_FIDELITY_MODE`, `CLASS0_EXTERN_PLANET_RULE`, `CLASS0_MODE`, `COCKPIT_FIELDS_MODE`, `COCKPIT_PARITY_MODE`, `COMBAT_FRAMING_MODE`, `COMBAT_MODE`, `COMBAT_ODDS_MODE`, `COMBAT_SCANNER_MODE`, `CORPSHIP_MODE`, `CORP_BOTS_MODE`, `CORP_BREAKIN_RULE`, `CORP_FIX_MODE`, `CORP_MODE`, `CORP_RULES_V2_MODE`, `DEATH_MODE`, `ECONOMY_SCALE_MODE`, `FED_MODE`, `FED_OUTPOST_MODE`, `FERRENGI_MODE`, `FLEET_MODE`, `GENESIS_HULL_MODE`, `GOLD_ALIEN_MODE`, `HARDWARE_MODE`, `HUNT_MODE`, `H_RECOVERY_MODE`, `INFO_MODE`, `ISS_REPO_MODE`, `LLM_PARITY_MODE`, `LLM_PLANET_NUDGE_MODE`, `LLM_QUASAR_NUDGE_MODE`, `LOBBY_AI_SEAT_MODE`, `MINE_OVERFLOW_MODE`, `NET_WORTH_MODE`, `PLANET_CLASS_MODE`, `PLANET_DIVIDEND_MODE`, `PLANET_ECONOMY_MODE`, `PLANET_REALTIME_PROD_MODE`, `PLANET_TRADE_MODE`, `PORT_OPEN_STOCK_MODE`, `PORT_UPGRADE_MODE`, `RANK_MODE`, `RANK_TITLES_MODE`, `REWARD_TARGET_RULE`, `ROB_MODE`, `ROGUE_KEEP_MODE`, `SEAT_DEADLINE_MODE`, `SECTOR_FIGHTER_MODE`, `SHIELD_PRICE_MODE`, `SHIP_TW_MODE`, `SLOW_HULL_HINT_MODE`, `STARDOCK_EXTRA_MODE`, `TAVERN_MODE`, `TOW_MODE`, `TRADE_TURN_MODE`, `UNIVERSE_TOPOLOGY_MODE`, `WARP_COST_MODE`.

Most of those are stored defaults that are already tw2002, or switches the profile doc lists under "Left as they are". `CITADEL_FIDELITY_MODE` is read by `citadel_fidelity_rules`, which is in the helper dict under `CITADEL_COST_MODE`, so the fidelity symbol itself is not the cited switch. `GOLD_ALIEN_MODE` is the one the old missing-row list cares about: the helper exists and the v3.11 profile does not turn it on.

## Every row

1.1 Match. Default universe is 1000 sectors. `models.GameConfig` reads `constants.DEFAULT_UNIVERSE_SIZE`. `universe.generate_universe`.
1.2 Match-behind-flag `ONE_WAY_SHARE_MODE` row 88, NOTE 78, and `TWO_WAY_WARP_MODE` row 178, NOTE 157. About 3 percent one-way when the game does not set `one_way_fraction`. Legacy one-way stays 0.15. Extra two-way lanes are 30 percent of the sector count. Legacy stays average 2.7. `constants.one_way_fraction_for`, `constants.two_way_edge_target`.
1.3 Match-behind-flag `COURSE_MAX_MODE` row 86, NOTE 78. A plotted course longer than 45 hops is refused. The 45 is UNVERIFIED. Legacy still searches 60. `constants.plot_course_hop_limit`, `runner._handle_plot_course`.
1.4 Match. FedSpace is sectors 1 through 10. `constants.FEDSPACE_SECTORS`. `fed.protect_fedspace_attack`.
1.5 Ben-decision. StarDock stays in sector 1. `constants.STARDOCK_SECTOR`.
1.6 Partial. Terra exists while class 0 is on. Colonist packing stays behind `TERRA_COLONIST_MODE` row 25 and `COLONIST_UNITS_MODE` row 116. `class0.handle_terra_colonists`.
1.7 Match. Class 0 ports are on. `CLASS0_MODE` is tw2002. `class0.place_class0_ports`.
1.8 Match-behind-flag `FEDERATION_HALL_MODE` row 182, NOTE 162. Bank, tavern, shipyard, and hardware stay on. Federation Hall and the hardware shop screen stay off until the switch is on. `constants.federation_hall_live`.
1.9 Match-behind-flag `FERRENGAL_QUASAR_MODE` row 102, NOTE 85. Mines and fighters are already placed. The quasar shot stays off. `ferrengi.place_ferrengal`, `runner._apply_ferrengal_quasar`.
1.10 Match-behind-flag `BIG_BANG_DENSITY_MODE` row 87, NOTE 78. Ports in about 40 percent of deep sectors. Legacy stays about 65 percent. `universe.generate_universe`.
1.11 Match-behind-flag `BIG_BANG_DENSITY_MODE` row 87, NOTE 78. Planets up to 20 percent. Legacy `planet_spawn_probability` stays 0.03. `universe._seed_planets`.
1.12 Match. A sector holds at most 5 planets. `constants.sector_has_planet_room` while `planet_limits_on` (stored `PLANET_ECONOMY_MODE` tw2002).
1.13 Match-behind-flag `UNIVERSE_TOPOLOGY_MODE`. Dead ends, traps, tunnels, and one bubble. The profile leaves this off. `universe._add_tunnels`, `universe._cut_one_bubble`.
1.14 Match. FedSpace keeps 5 ships per sector and tows the rest. `fed.run_tows`.
1.15 Partial. Feds tow a ship with 99 or more fighters. The Bible says 50. `constants.FED_TOW_FIGHTER_LIMIT`, `fed.run_tows`. No switch.
1.16 Match. A good trader with under 1000 experience is already safe in FedSpace. `victory.is_fedsafe`, `constants.FEDSAFE_MAX_EXPERIENCE`.
1.17 Match. The nightly Extern sweep runs. `class0.extern_sweep` from `runner.tick_day`.
1.18 Match-behind-flag `BIG_BANG_DENSITY_MODE` row 87, NOTE 78. Sectors 2 through 10 get no decorative federal ports when the switch is on. `universe._place_decorative_fed_ports`.
1.19 Match. Sector caps are 5000 fighters, 30000 with a planet, and 99 mines. `constants.sector_fighter_cap`, `constants.SECTOR_MINE_CAP`.
1.20 Match. You can pick your fighters and mines back up. `corp.handle_deploy_fighters`, `corp.handle_deploy_mines`.
2.1 Match. Three trade goods. `economy.execute_trade`.
2.2 Match-behind-flag `PORT_CLASS_MAP_MODE` row 10 and `PORT_CLASS_NUMBER_FIX_MODE` row 142, NOTE 98. Class 7 displays as SSS. Class 8 stays the StarDock id. Class 9 stays the built SSS port. `constants.port_class_live`.
2.3 Match-behind-flag `PORT_PRICE_MODE` row 21. The original price curve is coded and off. `economy.port_sell_price`.
2.4 Match. Each port has its own MCIC and productivity. `economy._stored_mcic`.
2.5 Match-behind-flag. R3 A: two printed lists, ports on the economy2 chart and ships on the Bible chart; no source prints one scale, so none is invented. The playtest 3 note that 1-hop pairs barely deplete came from port maximums of 2,500 to 4,500; `PORT_MAX_STOCK_MODE` row 223 uses the printed 950 to 2,720 (Bible Tarsus, economy2, economy3 "1,500 ... roughly average"). `economy.port_sell_price`, `universe._make_port`.
2.6 Match-behind-flag `HAGGLE_LIVE_MODE` row 31. The live window is coded and off. `HAGGLE_COUNTER_MODE` row 74 and `HAGGLE_EXP_MODE` row 110 sit beside it. The cabal product table is `HAGGLE_TABLE_MODE` row 175, NOTE 150, and stays off. Equipment at MCIC -20 is 110.2 percent on that table, not the straight line. `economy.haggle_bound`, `economy.haggle_experience`.
2.7 Match. The first trade in a sector costs a turn. Later trades there do not. `economy.trade_turn_cost`.
2.8 Match-behind-flag `PORT_REGEN_MODE` row 22. Five percent restock is coded and off. `economy.regenerate_ports`.
2.9 Match-behind-flag `PORT_STOCK_FIDELITY_MODE` row 51. Opening the day on the live stock curve is coded and off. `universe._make_port`.
2.10 Match-behind-flag `CLASS0_HOLD_FORMULA_MODE` row 109, NOTE 87. The cabal hold total is coded and off. `constants.class0_hold_formula_live`.
2.11 Match-behind-flag `SHOP_PRICE_MODE` row 23. The hold and fighter price waves are coded and off. `constants.shop_price_live`.
2.12 Match. Robbing a port is on. `rob_steal.handle_rob`.
2.13 Match. Stealing from a port is on. `rob_steal.handle_steal`.
2.14 Match-behind-flag `BUST_CLEAR_MODE` row 94, NOTE 82. Clearing can be every Extern or every 7 days. Legacy still clears every Extern. `rob_steal.busts_clear_this_extern`, `rob_steal.clear_all_busts`.
2.15 Partial. Blowing a port is behind `PORT_ATTACK_MODE` row 30 and `PORT_ATTACK_ALL_CLASSES_MODE` row 138, NOTE 98. Classes 0-5 and 7-9 still have no measured rating. `runner._handle_port_attack`.
2.16 Match. Building and upgrading a port is on. `constants.port_upgrade_on`.
2.17 Match-behind-flag `DETECT_GEAR_MODE` row 34. The psychic probe price peek is coded and off. `constants.detect_gear_live`.
2.18 Match. StarDock trading is on. `economy.execute_trade`.
3.1 Match-behind-flag `SHIP_ROSTER_MODE` row 4. The v3.34b six-field catalog is coded and off. `constants.ship_specs`.
3.2 Match. Merchant Cruiser cost, holds, max holds, fighters, turns, and odds already match `SHIP_ROSTER_LIVE_TABLE`. `constants.ship_specs`.
3.3 Match-behind-flag `SHIP_ROSTER_MODE` row 4. Scout max fighters become 250 and initial holds 10. Legacy fighters stay 150. `constants.ship_specs`.
3.4 Match-behind-flag `SHIP_ROSTER_MODE` row 4. Missile frigate initial holds become 12. `constants.ship_specs`.
3.5 Match-behind-flag `SHIP_ROSTER_MODE` row 4. Battleship initial holds become 16. The sticker is 88,500 in both tables. `constants.ship_specs`.
3.6 Match-behind-flag `SHIP_ROSTER_MODE` row 4. Corporate flagship initial holds become 20. `constants.ship_specs`.
3.7 Match. Colonial Transport already matches the live six-field tuple. `constants.ship_specs`.
3.8 Match-behind-flag `SHIP_ROSTER_MODE` row 4. CargoTran initial holds become 50. `constants.ship_specs`.
3.9 Match-behind-flag `SHIP_ROSTER_MODE` row 4. Merchant freighter initial holds become 30. `constants.ship_specs`.
3.10 Match-behind-flag `SHIP_ROSTER_MODE` row 4. Havoc initial holds become 12. Ship TransWarp is already on via `SHIP_TW_MODE`. `constants.ship_tw_on`.
3.11 Match-behind-flag `SHIP_ROSTER_MODE` row 4. The live ISS price is 329,000 and stays off. `constants.ship_cost`.
3.12 Match-behind-flag `SHIP_ROSTER_MODE` row 4. Star Master, Constellation, T'Khasi Orion, and Taurean Mule are in the live table. `constants.ship_specs`.
3.13 Match-behind-flag `SHIP_ROSTER_MODE` row 4. The Tholian Sentinel is in the live table. `constants.ship_specs`.
3.14 Match-behind-flag `SHIP_ROSTER_MODE` row 4. The Interdictor Cruiser is in the live table. `constants.ship_specs`.
3.15 Match. A normal game uses `SHIP_SPECS_TW2002` while `ECONOMY_SCALE_MODE` is tw2002. `equip_room` caps mines, genesis, photons, fighters, shields, and holds. Fighters per attack are on that chart. Ether probes stay `SHIP_CHART_CAP_MODE` row 96. `constants.equip_room`, `constants.ship_specs`.
3.16 Match. Combat odds are already the chart. `COMBAT_ODDS_MODE` stays off and changes nothing (profile no-op). `combat.combat_odds_of`.
3.17 Match-behind-flag `TRADE_IN_MODE` row 13. Live trade-in is 90 percent and stays off. Legacy stays 25 percent. Itemised parts are `TRADE_IN_PARTS_MODE` row 76. `constants.trade_in_live`.
3.18 Match. A player can own more than one ship. `constants.fleet_on`.
3.19 Match. Empty ships can be captured. `CAPTURE_MODE` is tw2002. `constants.capture_on`.
3.20 Match. Alignment of 1,000 is commissioned. Police HQ raises 500 through 999 to 1,000. An evil ISS is repossessed on the move. `victory.is_commissioned`, `fed.handle_apply_commission`, `fed.check_iss_repo_on_move`.
4.1 Partial. Genesis works. The empty start is `GENESIS_START_MODE` row 24. A typed name is `GENESIS_NAME_MODE` row 120. Price sources still disagree. `runner` genesis deploy.
4.2 Match-behind-flag `ATOMIC_DETONATOR_MODE` row 89, NOTE 78. The detonator is the planet killer. The port-nuke atomic mine is not sold when the switch is on. `runner._handle_deploy_atomic`.
4.3 Match. Marker beacons are on. `runner._handle_buy_equip`.
4.4 Match. Corbomite is on. `combat` corbomite fire.
4.5 Match. Cloaks are on. `constants.hardware_tw2002`.
4.6 Match. An ether probe walks the route up to `PROBE_MAX_HOPS` (45) and dies at the first hostile fighters. `scanners.handle_probe`. The owner's name on that notice is `PROBE_SHOOTDOWN_MODE` row 99, NOTE 85, and stays off.
4.7 Match. Mine disruptors are on. `hardware` disruptor path.
4.8 Partial. Armid detonation is the stored half-count at 20 damage (`hardware.armid_detonation_hits`, profile row 92). The shop price moves only under `HARDWARE_PRICE_MODE` row 14. `constants.armid_hit_damage`.
4.9 Match. Limpets attach and can be queried. Removal at StarDock costs 1,250 while hardware is tw2002. `hardware.handle_remove_limpet`, `constants.LIMPET_REMOVAL_COST`.
4.10 Match-behind-flag `PHOTON_LIMPET_MODE` row 174, NOTE 148. The wave decloaks, damps a quasar, and holds mines and fighters. A limpet during that wave stays off until the switch is on. The interdictor still holds, matching S1. Duration stays 1 second. `runner` photon handler.
4.11 Match. Density info needs a bought scanner. `scanners.scan_reason`, `runner._buy_scanner`.
4.12 Match. Holo info needs a bought scanner. `scanners.scan_reason`, `runner._handle_scan`.
4.13 Match-behind-flag `PLANET_SCANNER_MODE` row 43. Shielded planets stay visible until the scanner is on. `observation._planet_brief`, `runner._buy_planet_scanner`.
4.14 Match-behind-flag `DETECT_GEAR_MODE` row 34. Same probe as 2.17. `constants.detect_gear_live`.
4.15 Match. Ship TransWarp is on. `SHIP_TW_MODE` is tw2002. `constants.ship_tw_on`.
4.16 Match. `SHIP_TRANSPORT_RANGE` is the Bible chart. The ISS stays 10, not the MBBS prose 15. `fleet.transport_range`, `fleet.handle_ship_transport`.
4.17 Match-behind-flag `SHIP_CHART_CAP_MODE` row 96, NOTE 82. Mines, genesis, and photons already follow the chart. Live adds the probe cap of 25. `constants.ship_chart_cap_live`.
5.1 Match. Entry order is NavHaz, limpet, armids, sector quasar, then fighters. `runner._apply_sector_hazards`.
5.2 Match. NavHaz damages on the percent, and FedSpace clears it at night. `hardware.navhaz_pct`, `hardware.tick_navhaz`.
5.3 Match. Armid damage is the stored half detonation. `hardware.armid_detonation_hits`. Profile row 92, no helper.
5.4 Match-behind-flag `OFFENSIVE_CLASH_MODE` row 7. The 1.25 wave cap is coded and off. `combat.offensive_wave_size`.
5.5 Match. Defensive fighters challenge an entering ship. `combat.open_challenge`.
5.6 Match. The toll is 5 credits per fighter, paid to pass, and collected by picking the fighters up in that sector. `constants.SECTOR_TOLL_CREDITS_PER_FIGHTER`, `runner._handle_pay_toll`, `runner._handle_recall_deployed`.
5.7 Partial. The tw2002 exchange is the S4/S6 Safety Rating model. The exact loss split is not printed. `combat._resolve_ship_attack_tw2002`. No switch. CMB-c is docs only.
5.8 Match. A ship can send only its charted fighters in one attack. `combat.attack_cap`.
5.9 Match. Retreat is a verb and a flee spends extra turns. The published 1.25 line is `SHIP_FLEE_MODE` row 56. `combat._flee`.
5.10 Match-behind-flag `SPECIAL_HULL_RULES_MODE` row 105, NOTE 86. An Interdictor holds other ships, and a Tholian defending its corp planet fights at 4:1. Both need the roster switch. `combat.hull_interdict_reason`.
5.11 Match. Surrender is a verb. `combat` challenge settle.
5.12 Match-behind-flag `DEATH_POD_MODE` row 29. A destroyed ship becomes a pod. The clean loadout stays off. `combat._strip_ship`, `combat._destroy_ship_tw2002`.
5.13 Match-behind-flag `DEATH_DELAY_MODE` row 93, NOTE 79. A pod can be locked out for N midnights. Legacy ignores the setting. Two pods a day and out-until-midnight are the stored death path. `REENTRY_FIGHTERS_MODE` row 180, NOTE 158, stocks the free Scout. `runner.tick_day`, `combat._destroy_ship_tw2002`.
5.14 Match. NOTE 177: Built. A pod costs `POD_EXP_LOSS` 10% experience and no alignment; Ship Destroyed costs `SD_EXP_LOSS` and `SD_ALIGN_LOSS` 50% of both (cabal pods.html). `combat._destroy_ship_tw2002`.
5.15 Match. Furbing another ship's holds is on. `combat._destroy_ship`.
5.17 Match. Corbomite and disruptors fire in combat. `combat._resolve_ship_attack_tw2002`.
5.18 Match-behind-flag `PHOTON_FOLLOW_DAMP_MODE` row 90. A follower who enters the wave is damped when that switch is on. Decloak and the quasar damp are already in the wave. The limpet is `PHOTON_LIMPET_MODE` row 174, NOTE 148. The interdictor still holds, matching S1.
5.19 Match-behind-flag `PLANET_LANDING_COMBAT_MODE` row 54. Landing on a defended planet is a fight only when the switch is on. A normal game still seizes. `constants.planet_landing_combat_on`.
5.20 Match. NOTE 177: Built. Attacking a fedsafe trader in FedSpace summons Captain Zyrain and pods the attacker (`fed.protect_fedspace_attack`, `FED_PROTECT_PUNISH` pod, stored `FED_MODE` tw2002); attacking a Federal costs 10 alignment and the pod. Evil traders are not protected (`victory.is_fedsafe`).
6.1 Match-behind-flag `SCANNER_FOG_MODE` row 44. Planet fighters and shields stay hidden until the planet scanner is on. `observation._planet_brief`.
6.2 Partial. Citadel costs follow the class table that is on (`CITADEL_COST_MODE` via `citadel_fidelity_rules`, already true). Build days are `CITADEL_DAYS_MODE` row 2. The class M level-1 colonist figure is Ben's choice (6.3). `constants.citadel_fidelity_rules`.
6.3 Ben-decision. Class M population cap stays 30,000 until Ben chooses. The die-off rule is behind `PLANET_PROD_MODE` row 26. `constants.planet_prod_live`.
6.4 Match-behind-flag `PLANET_PROD_MODE` row 26. Fuel from colonists divided by 3, and the 5 percent die-off. `constants.planet_prod_live`.
6.5 Match-behind-flag `GENESIS_START_MODE` row 24. A new planet starts empty. `constants.genesis_start_live`.
6.6 Match. Five planets per sector, same as 1.12. The overload collision is a separate nightly job, `PLANET_COLLISION_MODE` row 148, NOTE 102, and stays off. `constants.sector_has_planet_room`, `runner._planet_collisions`.
6.7 Match. A Genesis launch rolls a class from `PLANET_CLASS_WEIGHTS` when the torpedo commits. A requested class is ignored. `PLANET_CLASS_MODE` stays off the profile because it would limit the roll to M and U, and v3.11 class is random. The crowding weights are one note with no numbers, so they are not applied. `runner._handle_deploy_genesis`.
6.8 Match. Planetary trading is on. `PLANET_TRADE_MODE` is tw2002. `constants.planet_trade_on`.
6.9 Match-behind-flag `CITADEL_PARK_MODE` row 45. Overnight parking inside a citadel is coded and off. `fleet.citadel_home`.
6.10 Match-behind-flag. NOTE 177: Ruled: Bible. Colonists, then the planet; +50 experience. `PLANET_BLOW_ALIGN_MODE` (row 214) takes 50 alignment for the blow (Bible S3 "50 points down"); legacy keeps the cabal -1. Killing a trader on it is `PLANET_ZDY_MODE` (NOTE 143). Colonist-kill alignment is still unprinted.
6.11 Match-behind-flag. `CORP_PLANET_DISBAND_MODE` row 97 and `SPECIAL_HULL_RULES_MODE` row 105 are the planet split and the Tholian 4:1. NOTE 163 graded the row on those two. `CORP_SHIP_DISBAND_MODE` row 201, NOTE 164, is the ship sentence in the same v3.06 revision: a parked ship in the living C.E.O.'s sector becomes that C.E.O.'s, and a parked ship outside it stays defunct. That switch does not grade the row a second time. `corp.disband`, `corpships.on_corp_extinct`.
6.12 Match. The stored blow is +50 experience and −1 alignment. The create-and-destroy loop is 14.3, behind `PLANET_BUST_EXP_MODE`. `constants.xp_award`, `constants.PLANET_DESTROY_ALIGNMENT_TW2002`.
6.13 Match-behind-flag `PLANET_DIVIDEND_PAY_MODE` row 41. Turning it off stops the growth dividend. The profile selects off. `constants.planet_dividend_off`.
6.14 Match-behind-flag `CITADEL_PERK_MODE` row 27. L2 and L5 perk lines are coded and off. `runner._handle_set_military_reaction`.
7.2 Match-behind-flag `CITADEL_DAYS_MODE` row 2. Build days can use the slower scale. `constants.citadel_days_live`.
7.3 Match. A finished level still grants fighters and shields. `planets._complete_citadels`.
7.4 Match. Atmospheric quasar factor stays the MBBS times 2. A shieldless landing's second shot is `QUASAR_ATM_ORDER_MODE` (NOTE 143). `runner._handle_land_planet`.
7.5 Match-behind-flag `TREASURY_CAP_MODE` row 85, NOTE 78. The S1 cap is coded. The stored cap stays 10,000,000. `runner._handle_deposit_treasury`.
8.1 Match-behind-flag. Hull counts and the approximate FERRSPEC odds stay the stored table. `FERRENGI_ODDS_MODE` row 200, NOTE 164, reads the Bible chart: 1.2 / 1.4 / 1.4, an Assault Trader volley of 2,000, and a holo scanner on that hull. It stays off. `FERRENGI_ATTACK_MODE` row 173, NOTE 148, is still the one-volley gate and still uses the FERRSPEC 1,000 while the odds switch is off. `constants.ferrengi_odds_for_hull`, `combat._resolve_ferrengi_chart_attack`.
8.2 Match-behind-flag `FERRENGI_ENGAGE_MODE` row 58. The engage path is coded and off. Tribute amounts are UNVERIFIED. `constants.ferrengi_engage_on`.
8.3 Match-behind-flag `FERRENGI_PACE_MODE` row 107 and `FERRENGI_GRUDGE_MODE` row 106, NOTE 86. Movement chance and the grudge hop are coded and off. `runner.tick_day`.
8.4 Match-behind-flag `FERRENGI_REWARD_MODE` row 101, NOTE 85. The bounty is already paid. Live alignment and experience by hull stay off. `combat._grant_ferrengi_kill`.
8.6 Match. Alien traders other than Ferrengi are on. `ALIEN_MODE` is tw2002. `alien.alien_day_step`.
8.7 Match-behind-flag `FED_SHIPS_MODE` row 33. The live federal ship table is coded and off. `fed.place_fed_starships`.
8.8 Match. Aliens and Feds already refuse a sector that holds fighters. Ferrengi already ignore fighters and take mine hits. `alien._fighter_blocked`, `fed._fed_blocked`, `ferrengi._apply_mines_to_ferrengi`.
8.9 Match-behind-flag `GOLD_ALIEN_MODE`. Gold-mode aliens are coded and off. The v3.11 profile does not turn `gold_alien_live` on. `alien.note_gold_grudge`.
9.1 Match-behind-flag `STARTING_PACKAGE_MODE` row 1. The clean start package is coded and off. `runner.grant_starting_planet`.
9.2 Match. A trade pays 1, the first dock pays 1, midnight pays 1 experience and 1 alignment, genesis pays 25, destroying a port pays 50, and a kill pays 10 percent of the victim's experience. Those are `XP_AWARDS_TW2002` while `RANK_MODE` is tw2002. An alien's own experience is not printed, so a Ferrengi kill does not pay half of one. `runner._handle_trade`, `runner.tick_day`, `victory.kill_rewards`.
9.3 Match. Experience from a player kill uses `COMBAT_EXP_DIVISOR` 15/35/25 and `KILL_EXP_SHARE` 0.10. `victory.combat_rewards`, `victory.kill_rewards`. Profile row 91.
9.4 Match. Alignment already moves by the fighters lost times the other alignment, divided by 5000. `constants.COMBAT_ALIGN_DIVISOR`, `victory.combat_rewards`.
9.5 Match-behind-flag `BOUNTY_GOOD_MODE` row 187, NOTE 163. A bounty on a good trader costs 1 alignment per 250 credits and no experience. A reward on an evil trader, the tax, jettison, genesis, a port blow, a corp break-in, a port upgrade, the underground contract, and cursing the Grimy Trader are already in. A line the sources do not name was not added. `fed.handle_post_reward`.
9.6 Match. Rank titles are already the original ladders, and traders are ordered by experience. `RANK_TITLES_MODE` is a no-op. NOTE 158 added no second switch. `victory.rank_for`.
9.7 Match-behind-flag `CITADEL_PERK_MODE` row 27. The L2 and L5 perk set is coded and off. A wider good-trader versus evil-trader chart was not found as a second switch. `constants.citadel_perk_live`.
9.8 Match. NOTE 177: Built. Port prices improve with experience up to `PORT_PRICE_EXPERIENCE_CAP` (`economy._experience_span`). Rob max `ROB_CREDIT_FACTOR` exp x 6 and steal max exp / `STEAL_HOLD_DIVISOR` 21, which is (3 / RobFactor) and (30 x StealFactor) at the TWGS default 50% / 70% (cabal formulas.html, modern manual twgs-settings). `rob_steal.max_rob_credits`.
9.9 Match-behind-flag `MIXED_CORP_EXP_RULE` row 72. The cabal least-extreme loss is selected by the profile and stays off in the stored value. `corp.mixed_loss`.
10.1 Match-behind-flag. NOTE 177: Ruled. `corp_create` at the StarDock; no source prints a charter cost, so `CORP_CREATE_COST` 0 stays. Only the C.E.O. buys a FlagShip (`CFS_CEO_RULE` purchase) and, with `CFS_CEO_USE_MODE` (row 213), only the C.E.O. boards one (Gypsy: "Only C.E.O.'s can use Corporate Flagships"). `corpships.board_block`.
10.2 Match-behind-flag `CORP_ALIGNMENT_RULE` row 71. The invite, the password, and the C.E.O. approval are in. The sign-agreement check stays off until the profile selects `join_check`. `corp._join_block`, `corp.handle_corp_join`.
10.3 Match-behind-flag `CORP_ALIGNMENT_RULE` row 71. The profile join check refuses a sign conflict. The stored value stays mixed, so a normal game does not. `corp._join_block`.
10.4 Match. The stored join path uses `CORP_MAX_MEMBERS` 5. `GameConfig.corp_max_members` default 2 is the legacy `CORP_MODE` path only. `corp._join_block`, `corp.handle_corp_join`.
10.5 Match. The C.E.O. can drop a member. `corp.handle_corp_drop`.
10.6 Match-behind-flag `CORP_CARGO_TREASURY_MODE` row 183, NOTE 162. Credits, fighters, shields, armids, and limpets already move. Fuel ore, organics, equipment, colonists, and the corporation treasury stay refused until the switch is on. `corp.handle_corp_transfer`, `runner._handle_corp_deposit`.
10.7 Match. The corp screen lists each planet's sector, name, population, fuel, organics, and equipment production, stock, fighters, citadel, shields, and credits, and each member's sector, planet flag, fighters, shields, mines, and credits. `corp.member_block`.
10.8 Match. A corp memo exists. `corp` memo path on `CORP_MODE` tw2002.
10.9 Match. Fighters and mines can be personal or corporate. A corporate hull is password protected and a corp mate can board it. `CORPSHIP_MODE` is tw2002. `corpships.password_block`, `corpships.board_block`.
10.10 Match. A C.E.O. leaving dissolves the corp and rogues fighters outside his sector. `corp.handle_corp_leave`, `corp.disband`. Profile row 98.
10.11 Match-behind-flag `CORP_RANK_MODE` row 49. The corporation ranking screen is coded and off. The trader list is `TRADER_RANK_LIST_MODE`, ordered by experience. NOTE 158 added no second screen. `observation.build_observation`.
10.12 Match-behind-flag `ALLIANCE_MODE` row left out of the profile (not in the original). Alliances are coded and off. `constants.alliance_live`.
11.1 Match-behind-flag `HARDWARE_PRICE_MODE` row 14. The live shop card is coded and off. `constants.hardware_price_live`.
11.2 Match-behind-flag `SHIP_ROSTER_MODE` row 4 and `TRADE_IN_MODE` row 13. The yard and the 90 percent trade-in stay off. `constants.ship_specs`.
11.3 Match. Police HQ can grant a commission. `victory.is_commissioned`.
11.4 Match. A killed player can carry a bounty. `constants.REWARD_TARGET_RULE`.
11.5 Match. The galactic bank is on. `BANK_MODE` is tw2002. `bank.collect_daily_tax`.
11.6 Match-behind-flag `TAX_RULE_MODE` row 8. Ten percent of cash on hand at 50,000 or more, alignment above 0, once per day. `bank.collect_daily_tax`.
11.7 Match-behind-flag `UG_NAME_MODE` row 184, NOTE 162. The door, the password, and hit contracts are in. A total unknown can buy a new name when the switch is on. A higher experience has no printed price. `tavern.handle_rename`.
11.8 Match. The tavern is on. `TAVERN_MODE` is tw2002. `constants.tavern_on`.
11.9 Match-behind-flag `FED_HUNT_MODE` row 185, NOTE 162. Feds tow, and they answer some crimes. An evil ship that meets a Federal is destroyed when the switch is on. A sector with no Federal is left alone. `fed.hunt_evil_meeting_federal`.
11.10 Match-behind-flag `SPECIAL_PORT_DEFENCE_MODE` row 146, NOTE 102. StarDock and Class 0 take 248,000 fighters, then 890,000, and the Feds rebuild in 14 days. Numbers UNVERIFIED. `runner._rebuild_special_ports`.
11.11 Partial. Density, the one-way share, and the 30 percent two-way lanes are `BIG_BANG_DENSITY_MODE`, `ONE_WAY_SHARE_MODE`, and `TWO_WAY_WARP_MODE`. Not the whole original screen. Bubbles are Gold-only (S1), so v3.11 needs none. `universe.generate_universe`.
12.1 Match. Turns per day are a game setting. `models.GameConfig`.
12.2 Match-behind-flag `TURN_REGEN_MODE` row 5. Turns can come back across 24 hours. `LIVE_PACE_MODE` row 6 goes with it. `constants.turn_regen_live`.
12.3 Different. Movement is still by turns, not by the clock. `DAY_ROLL_CLOCK_MODE` row 81 rolls the day while a seat holds the turn. Planet goods can accrue on `PLANET_REALTIME_PROD_MODE`, which the profile leaves off. `runner.apply_action`.
12.4 Partial. `runner.tick_day` runs retreats, Ferrengi, corp penalty, the Class 0 sweep, Terra regen, empty-ship repossession, Fed tows, port regen, bust clearing, photon waves, cloak fails, NavHaz, alien hops, planet production, citadels, treasury, and tax. Collisions and special-port rebuilds stay behind `PLANET_COLLISION_MODE` and `SPECIAL_PORT_DEFENCE_MODE`. `INACTIVE_USER_MODE` row 177, NOTE 151, deletes a disconnected human after 30 quiet wall-clock days in a game that was generated with the switch on, and stays off. A connected seat and an AI cockpit seat stay. `INACTIVITY_TIMEOUT_MODE` row 178 sleeps a quiet lobby game after 14,400 seconds and stays off. Not every original nightly job is named.
12.5 Match-behind-flag `EXP_SCORE_MODE` row 28. A normal game still ends on net worth. Experience ranking is coded and off. The day cap, the last player standing, the credit bar, and a creator end have no printed v3.11 number. NOTE 158 left them. `victory.check_victory`.
12.6 Match-behind-flag. The v3.11 sample prints tournament mode off and unlimited times blown up. `TIMES_BLOWN_MODE` row 202, NOTE 164, says so on the legacy destroy line when elimination is off, and stays off. The later lockout was not added. `DEATH_DELAY_MODE` is the timeout. `combat._legacy_destroy_summary`.
12.7 Match-behind-flag `DAILY_STATS_MODE` row 47. The daily stats screen is coded and off. `observation.build_observation`.
13.1 Match-behind-flag `MAIL_MODE` row 161, NOTE 103, and `COMMS_V311_MODE` row 176, NOTE 142. A hail flashes for about 10 seconds, and mail waits for an offline trader. The same-sector hail is the comms switch. `runner._handle_hail`.
13.2 Match-behind-flag `RADIO_CHANNEL_MODE` row 46. Radio channels are coded and off. `runner._handle_radio`.
13.3 Match-behind-flag `MAIL_MODE` row 161, NOTE 103. Stored mail and the New Mail line stay off until the switch is on. `runner._handle_hail`.
13.4 Match-behind-flag. `OWNER_HAZARD_NOTICE_MODE` row 55 and `SIEGE_REPORT_MODE` row 59 tell the owner about a landing, a fighter hit, a mine, and a siege. NOTE 163 graded the row on those two. `FIGHTER_REPORT_MODE` row 203, NOTE 164, is a separate list of sectors where that trader owns fighters, omitting a count of 0. It is not an observation field, and it does not grade the row a second time. `observation._event_visible_base`, `combat.fighter_report`.
13.5 Match. An ether-probe report is the route it walked, and it names the sector where fighters destroyed it. `scanners.handle_probe`.
13.6 Match-behind-flag `FEDCOMM_MODE` row 48. The FedComm notice is coded and off. `class0.extern_sweep`.
14.1 Match-behind-flag `CIM_MODE` row 186, NOTE 162, and `NAVPOINT_MODE` row 181, NOTE 159. The course plotter and avoids (`AVOID_MODE` row 35) are in. NavPoints are four named slots, Terra and StarDock, set, list, clear, and a course. CIM lists explored sectors and ports, hides a port behind hostile fighters, and plots a path. Backtrack, quick stats, and find route are not that whole menu. `v311_buildable.handle_cim`, `navpoints.menu_rows`.
14.2 Match. Towing is on. `TOW_MODE` is tw2002. `constants.tow_on`.
14.3 Match-behind-flag `PLANET_BUST_EXP_MODE` row 149, NOTE 102. The owner may destroy the planet they created for 75 experience (genesis 25 plus destroy 50). `legality.planet_destroy_reason`.
14.4 Match. An unmanned ship can still hold fighters. While `V311_PROFILE` is on, `observation` game status leaves those fighters out of the V-screen total. Legacy still counts them. No switch was added for that display. Profile GAP 14.4 note.
14.5 Match-behind-flag `EVIL_TRADE_LOOP_MODE` row 166, NOTE 115. A negative-alignment seat steals, dumps, and beams, or robs and beams, when the profile is on. `constants.evil_trade_loop_live`.
14.6 Partial. The instant credits win is off under `ECON_WIN_MODE` row 215 (NOTE 178). Alliances and play_to_day_cap stay. `victory._check_victory`.

There is no row 5.16, 7.1, or 8.5. That is the same 171 ids as v5.
