# gap-map-refresh-v6

Plan only. Every October row, regraded at `60b17fef` (branch `track-g-note108`, cut from `feature/grokbot-player`). v5 graded the same 171 ids at `f969cee`. This pass does not add a switch. Helper row 164 stays unused.

A row is Match when the original rule is what a normal game does now. Match-behind-flag means the original rule is coded and the named switch stays off until `V311_PROFILE` is `v311`, unless the profile section says that helper is left out on purpose. Partial means part of the rule is in. Different means a normal game still does something else. Missing means this pass found no handler. Ben-decision is a number Ben has not chosen. Class M colonists stay a stored rule. Random StarDock is Match-behind-flag on `STARDOCK_LOCATION_MODE` row 236 (Ben approved the Commander recommendation 2026-10-24).

`docs/plans/GAP_MAP.md` is the October 3 baseline refreshed to `62961c5`. Its own header says those counts are the October picture. v5 already replaced that picture. This file replaces v5. Grades below are from the tip code, not from that October table.

## Counts

| Grade | v5 | v6 |
|---|---|---|
| Match | 50 | 75 |
| Match-behind-flag | 17 | 95 |
| Partial | 53 | 1 |
| Different | 38 | 0 |
| Missing | 11 | 0 |
| Ben-decision | 2 | 0 |
| Total | 171 | 171 |

Pointer check: 2.17 and 4.14 stay Match-behind-flag on `DETECT_GEAR_MODE`. The 4.16 chart is `constants.transport_range`. The 5.15 hold transfer is `corpships.apply_furb`. Corbomite on 5.17 is `hardware.apply_corbomite`. The disruptor is `hardware.handle_fire_disruptor`.

NOTE 163 moved five rows that were still Partial. 6.7 and 9.2 are Match. 6.11, 9.5, and 13.4 are Match-behind-flag. The new switch is `BOUNTY_GOOD_MODE` row 187. Row 181 is NavPoints (`NAVPOINT_MODE`, NOTE 159). NOTE 162 uses rows 182-186 and moves 21 more rows. 14.1 is Match-behind-flag through `CIM_MODE` row 186. NOTE 164 moves 8.1 and 12.6 from Partial to Match-behind-flag. The ship switch and the fighter-report switch sit on 6.11 and 13.4 and do not grade those rows again.
NOTE 177 moved five more Partial rows. At that note, 5.14, 5.20, and 9.8 were graded Match, and 6.10 (`PLANET_BLOW_ALIGN_MODE` row 214) and 10.1 were graded Match-behind-flag. 8.1 is counted once, under NOTE 164's `FERRENGI_ODDS_MODE`. The adoption paragraph below is the current grade for 5.14, 5.20, and 10.1.
NOTE 178 recorded 5.7 as the printed expected value, 14.6 with the credit finish off, 11.11 as bubbles Gold-only, and 12.3 as Different because movement is by turns. R12 A grades 12.3 Match. R14 A keeps the credit finish. 12.4 is Match-behind-flag: the printed Extern and midnight jobs are in `runner.tick_day`, and the ones a normal game does not run stay on switches that already exist. 2.5 is R3 A, Match-behind-flag.
GAP 1.15 moved from Partial to Match-behind-flag. The switch was already `FED_TOW_LIMIT_MODE` row 168 (NOTE 117). Bible 50 when on. Gypsy 98 stored when off. No new switch.
The level 6 interdictor damp is `PHOTON_INTERDICT_DAMP_MODE` row 234 and stays off. The interdictor piece itself is Match-behind-flag. Duration stays 1 day-tick. The FedSpace photon card is `PHOTON_CLOAK_SETTINGS_MODE` row 230.
R1–R14 are adopted from the suggested reply in `V311_RULINGS_FOR_BEN.md`. 1.6, 4.1, 6.2, 10.1, and 12.3 are Match. 5.14 and 5.20 moved to Match-behind-flag. 6.3 is the handbook curve from #183 and stays Match-behind-flag. 2.15 stays Partial; the confirmed samples stay Match-behind-flag. 1.5 left Ben-decision for Match-behind-flag on `STARDOCK_LOCATION_MODE` row 236. Ben approved the Commander recommendation 2026-10-24. No Ben-decision row remains. Partial remains 2.15.
The every-row list before this pass was 75 Match and 92 Match-behind-flag. Headers that said 76 and 91 were one swap off that list. 4.8 leaves Partial and is counted once, as Match-behind-flag. Detonation is Match and is not a second row. The shop unit price is `HARDWARE_PRICE_MODE` row 14. No third price was added. 12.4 leaves Partial and is counted once, as Match-behind-flag. No new switch was added. Partial is now 2.15. 4.10 stays Match-behind-flag in this list. Its duration is still three printed seconds (cabal and the modern manual 1, Gypsy 10, GameA 20) and was not given a switch.

## What moved

GAP 3.15 moved from Match to Match-behind-flag on `SHIP_CAPACITY_MODE` row 229. A stored game keeps unlimited mines, genesis, and photons, and a TransWarp jump with no printed hop ceiling. Holds stay on the tw2002 roster. The ship transporter stays `SHIP_TRANSPORT_RANGE`.

GAP 1.5 moved from Ben-decision to Match-behind-flag on `STARDOCK_LOCATION_MODE` row 236. A stored game keeps StarDock in sector 1. Under `V311_PROFILE=v311`, generation places it in a random ordinary sector. Terra stays sector 1. FedSpace is sectors 1-10 plus that sector.

The v5 "no switch at all" list now has a switch on this tip: planet scanner, scanner fog, citadel perks, citadel parking, the good-trader tax, radio, daily stats, FedComm, gold aliens, and corporation rankings. Gold aliens are coded and off, and the profile leaves `GOLD_ALIEN_MODE` out on purpose. Density, one-way lanes, the 45-hop plot cap, Class 0 hold prices, the treasury cap, Ferrengi pace and grudges, and the planet-bust experience loop moved in NOTEs 78 through 102. Player-kill experience (`COMBAT_EXP_DIVISOR` 15/35/25) and the ether-probe route are already what a normal game does, so those rows are Match. Corp member transfers of credits, fighters, shields, and mines are in `corp.handle_corp_transfer`. Holds and the corp treasury are `CORP_CARGO_TREASURY_MODE` row 183, NOTE 162.

## Diff, v5 to v6

Only rows whose grade changed. Evidence is `file:function`.

| Row | v5 | v6 | Evidence |
|---|---|---|---|
| 1.2 | Different | Match-behind-flag | `ONE_WAY_SHARE_MODE` row 88, NOTE 78. Extra two-way lanes are `TWO_WAY_WARP_MODE` row 178, NOTE 157. `constants.one_way_fraction_for`, `constants.two_way_edge_target` |
| 1.3 | Different | Match-behind-flag | `COURSE_MAX_MODE` row 86, NOTE 78. `constants.plot_course_hop_limit`, `runner._handle_plot_course`, `runner.query_route`. GameA TWSTATS is 20. Unset live default stays the published sample 45 (NOTE 96) |
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
| 4.8 | Different | Match-behind-flag | detonation is Match: stored half-count at 20 (`hardware.armid_detonation_hits`, profile row 92). Shop unit price is this grade on `HARDWARE_PRICE_MODE` row 14: stored `ARMID_MINE_COST` 100, live `ARMID_MINE_COST_LIVE` 1,000. Bible prints no unit price. Cabal $4,000 is the TEDIT sample, not a third price |
| 4.10 | Different | Match-behind-flag | frigate and ISS already carry the photon cap in `SHIP_SPECS_TW2002`. A follower's quasar damp is `PHOTON_FOLLOW_DAMP_MODE` row 90, NOTE 79. Limpet attach is `PHOTON_LIMPET_MODE` row 174. The level 6 interdictor damp is `PHOTON_INTERDICT_DAMP_MODE` row 234. The FedSpace card is `PHOTON_CLOAK_SETTINGS_MODE` row 230. Duration stays 1 day-tick: cabal and the modern manual print 1 second, Gypsy prints 10, GameA prints 20. No duration switch |
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
| 11.1 | Partial | Match-behind-flag | `HARDWARE_PRICE_MODE` row 14. Ship TransWarp 50,000 / 80,000 / 10,000 (stored 12,500 / 20,000 / 9,000 stay). Photon 40,000 (stored 12,000 stays). Atomic detonators stay off this switch. SOURCE-CONFLICT. `constants.hardware_price_live` | Ven 2026-10-24 GameA TWSTATS prints Type I TWarp=50,000 cr, Type II TWarp=80,000 cr, TWarp Upgrade=10,000 cr, Citadel Transport Unit=50,000 cr, and Citadel Transport Upgrade=25,000 cr. Citadel labels already match the planet transporter. The capture note marked those five DIFFERENT and queued.
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
| 2 | 5.7 | Match | L | The exchange is the printed expected value: sent x own odds / target odds removes shields then fighters (S3 Scout 2:1 kills 500 with 250, S2 1:1 loses 1,000 for 1,000, S7 fighters-to-use). S7: random factors unknown, so none. Tests pin it | `combat._resolve_ship_attack_tw2002` | test_combat_exchange_sources_v1.py |
| 23 | 11.11 | Match-behind-flag | S | Density, one-way share, 30 percent two-way lanes (rows 87, 88, 178) and the 95 percent initial starports (`BIG_BANG_BUILT_MODE` row 221). Course length 45 holds (test). Bubbles and Gold options are Gold-only (S1), so v3.11 has none | `universe.generate_universe` | universe.py |
| 35 | 14.6 | Match-behind-flag | L | R14 A. Alliances stay off under `ALLIANCE_OFF_MODE` row 222. The planet bonus stays off under `PLANET_DIVIDEND_PAY_MODE`. The day cap and the 100,000,000 credit finish stay. `ECON_WIN_MODE` is not selected by the profile | several | test_alliance_off_v1.py |

Rows that are Partial only because a named switch stays off are Match-behind-flag above, not in this list. 12.4 left this list: the printed Extern and midnight jobs are in `runner.tick_day`, and collisions, special-port rebuilds, inactive deletion, and the lobby timeout stay on switches that already exist. 1.15 left this list: `FED_TOW_LIMIT_MODE` row 168 tows above 50 when the profile is on. Stored Gypsy stays 98. 2.5 left this list: R3 A, Match-behind-flag. 12.3 left this list: R12 A, turns stay, Match.

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
1.3 Match-behind-flag `COURSE_MAX_MODE` row 86, NOTE 78. When the switch or the v311 profile is on, a computer plot longer than the game's Maximum Course Length is refused and a plot of that length succeeds. `GameConfig.max_course_length` is that setting. Unset, the published sample `V311_COURSE_MAX_HOPS` (45) is used. Ven GameA TWSTATS is 20 (`GAMEA_COURSE_MAX_HOPS`, NOTE 96, n96-course-max). The live refusal number and the TEDIT min/max are still unread. Legacy still searches 60. `constants.plot_course_hop_limit`, `runner._handle_plot_course`, `runner.query_route`.
1.4 Match. FedSpace is sectors 1 through 10. `constants.FEDSPACE_SECTORS`. `fed.protect_fedspace_attack`.
1.5 Match-behind-flag `STARDOCK_LOCATION_MODE` row 236. Ben approved the Commander recommendation 2026-10-24. Off, StarDock stays in sector 1 (`constants.STARDOCK_SECTOR`). On, generation places that port in a random ordinary sector. Terra stays sector 1. The draw skips FedSpace 1-10, Alpha Centauri, Rylos, Ferrengal, and any other reserved special port. FedSpace is sectors 1-10 plus that sector. `constants.stardock_location_live`, `universe._maybe_place_random_stardock`, `constants.fedspace_sectors_of`.
1.6 Match. R1 A. A normal game opens Terra at `TERRA_MAX_COLONISTS` 100,000 with one person per hold. Regen stays `TERRA_REGEN_PER_DAY` 750 and a load stays `TERRA_LOAD_TURNS` 1. `TERRA_COLONIST_MODE` row 25 is unchanged: live still opens at 30,000 with 1,000 per hold, and the profile still selects that later screen. `class0.handle_terra_colonists`.
1.7 Match. Class 0 ports are on. `CLASS0_MODE` is tw2002. `class0.place_class0_ports`.
1.8 Match-behind-flag `FEDERATION_HALL_MODE` row 182, NOTE 162, and `STARDOCK_DOORS_MODE` row 233, NOTE 129. Bank, tavern, shipyard, and hardware stay on. Federation Hall and the hardware shop screen stay off until the switch is on. NOTE 129: Class 0 shields at 131 a point are `SHIELD_POINT_MODE` row 225. A drink at 80 and food at 24 are `TAVERN_BAR_PRICE_MODE` row 226. Cineplex show 1 at 100 is `CINEPLEX_PRICE_MODE` row 227. Fighters at 218 that day stay on the 160-239 wave (UNVERIFIED, may be stock-dependent). The live where-to list adds the Libram Universitatus. B is not on that list and opens the singles bar. Key C lists Ferrengi hulls present in the game and takes no charge. Keys A and B stay empty lines. The bar prints the capture's exit lines and takes no credits. The unnamed 47-credit drop stays deferred. `constants.federation_hall_live`, `constants.shield_point_live`, `constants.stardock_doors_live`.
1.9 Match-behind-flag `FERRENGAL_QUASAR_MODE` row 102, NOTE 85. Mines and fighters are already placed. The quasar shot stays off. `ferrengi.place_ferrengal`, `runner._apply_ferrengal_quasar`.
1.10 Match-behind-flag `BIG_BANG_DENSITY_MODE` row 87, NOTE 78. Ports in about 40 percent of deep sectors. Legacy stays about 65 percent. `universe.generate_universe`.
1.11 Match-behind-flag `BIG_BANG_DENSITY_MODE` row 87, NOTE 78. Planets up to 20 percent. Legacy `planet_spawn_probability` stays 0.03. `universe._seed_planets`.
1.12 Match. A sector holds at most 5 planets. `constants.sector_has_planet_room` while `planet_limits_on` (stored `PLANET_ECONOMY_MODE` tw2002).
1.13 Match-behind-flag `UNIVERSE_TOPOLOGY_MODE`. Dead ends, traps, tunnels, and one bubble. The profile leaves this off. `universe._add_tunnels`, `universe._cut_one_bubble`.
1.14 Match. FedSpace keeps 5 ships per sector and tows the rest. `fed.run_tows`.
1.15 Match-behind-flag `FED_TOW_LIMIT_MODE` row 168, NOTE 117, R2 A. Bible more than 50 when on. Gypsy 98 stored when off (`FED_TOW_FIGHTER_LIMIT`). `constants.fed_tow_fighter_limit`, `fed.run_tows`.
1.16 Match. A good trader with under 1000 experience is already safe in FedSpace. `victory.is_fedsafe`, `constants.FEDSAFE_MAX_EXPERIENCE`.
1.17 Match. The nightly Extern sweep runs. `class0.extern_sweep` from `runner.tick_day`.
1.18 Match-behind-flag `BIG_BANG_DENSITY_MODE` row 87, NOTE 78. Sectors 2 through 10 get no decorative federal ports when the switch is on. `universe._place_decorative_fed_ports`.
1.19 Match. Sector caps are 5000 fighters, 30000 with a planet, and 99 mines. `constants.sector_fighter_cap`, `constants.SECTOR_MINE_CAP`.
1.20 Match. You can pick your fighters and mines back up. `corp.handle_deploy_fighters`, `corp.handle_deploy_mines`.
2.1 Match. Three trade goods. `economy.execute_trade`.
2.2 Match-behind-flag `PORT_CLASS_MAP_MODE` row 10 and `PORT_CLASS_NUMBER_FIX_MODE` row 142, NOTE 98. Class 7 displays as SSS. Class 8 stays the StarDock id. Class 9 stays the built SSS port. `constants.port_class_live`.
2.3 Match-behind-flag `PORT_PRICE_MODE` row 21. The original price curve is coded and off. `economy.port_sell_price`.
2.4 Match. Each port has its own MCIC and productivity. `economy._stored_mcic`.
2.5 Match-behind-flag. R3 A: two printed lists, ports on the economy2 chart and ships on the Bible chart; no source prints one scale, so none is invented. The playtest 3 note that 1-hop pairs barely deplete came from port maximums of 2,500 to 4,500; `PORT_MAX_STOCK_MODE` row 223 uses the printed 950 to 2,720 (Bible Tarsus, economy2, economy3 "1,500 ... roughly average"). NOTE 129 (19 Oct 2026) recorded day-1 quotes that differ from the chart anchors: fuel sell 11 and buy 27, organics sell 31 and buy 66 at 94 percent, equipment sell 56. MCIC was not printed, equipment buying was not quoted, and the anchors stay the chart. `docs/playtests/twgs-live/price-scale.txt`. `economy.port_sell_price`, `universe._make_port`.
2.6 Match-behind-flag `HAGGLE_LIVE_MODE` row 31. The live window is coded and off. `HAGGLE_COUNTER_MODE` row 74 and `HAGGLE_EXP_MODE` row 110 sit beside it. The cabal product table is `HAGGLE_TABLE_MODE` row 175, NOTE 150, and stays off. Equipment at MCIC -20 is 110.2 percent on that table, not the straight line. `economy.haggle_bound`, `economy.haggle_experience`.
2.7 Match. The first trade of a visit costs 1 turn. Later trades while `port_visit_sector_id` is that sector cost 0. The visit ends when the player leaves the sector. The October 3 "3 per trade" line is stale, and `TRADE_TURN_MODE` names the same rule, so stored games stay on 1 then 0. `docs/playtests/ports/TURNS_REGEN.md`. `economy.trade_turn_cost`.
2.8 Match-behind-flag `PORT_REGEN_MODE` row 22. Five percent restock is coded and off. `economy.regenerate_ports`.
2.9 Match-behind-flag `PORT_STOCK_FIDELITY_MODE` row 51. Opening the day on the live stock curve is coded and off. `universe._make_port`.
2.10 Match-behind-flag `CLASS0_HOLD_FORMULA_MODE` row 109, NOTE 87. The cabal hold total is coded and off. `constants.class0_hold_formula_live`.
2.11 Match-behind-flag `SHOP_PRICE_MODE` row 23. The hold and fighter price waves are coded and off. `constants.shop_price_live`.
2.12 Match. Robbing a port is on. `rob_steal.handle_rob`.
2.13 Match. Stealing from a port is on. `rob_steal.handle_steal`.
2.14 Match-behind-flag `BUST_CLEAR_MODE` row 94, NOTE 82. Clearing can be every Extern or every 7 days. Legacy still clears every Extern. `rob_steal.busts_clear_this_extern`, `rob_steal.clear_all_busts`.
2.15 Partial. Confirmed samples are Match-behind-flag. Blowing a port is behind `PORT_ATTACK_MODE` row 30 and `PORT_ATTACK_ALL_CLASSES_MODE` row 138, NOTE 98. Ven GameA 2026-10-24 samples (`docs/playtests/twgs-live/gap215-port-attack-2026-10-24.md`) are the class fallbacks when the attack flag is on: confirmed lasers class 1 337, class 4 1419, class 6 598, class 7 1121, with the measured defs. DEF_ONLY classes 2, 3, and 5 have a def sample and no laser. A captured port name uses that port's def. Lasers for classes 2, 3, 5, and non-Fed 8 are still open, and def still varies per port, so the row stays Partial. `runner._handle_port_attack`.
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
3.15 Match-behind-flag `SHIP_CAPACITY_MODE` row 229. Off, mines, genesis, and photons stay unlimited and a TransWarp jump is still ore divided by 3. On, the Bible/MBBS chart caps those three, and a jump stops at the printed hop range (Corporate FlagShip 28, Imperial StarShip 50, Havoc Gunstar 16). Holds stay `max_holds` on the tw2002 roster. The ship transporter stays `SHIP_TRANSPORT_RANGE`. Ether probes stay `SHIP_CHART_CAP_MODE` row 96. `constants.ship_capacity_live`, `constants.equip_room`, `ship_transwarp.handle_ship_transwarp`.
3.16 Match. Combat odds are already the chart. `COMBAT_ODDS_MODE` stays off and changes nothing (profile no-op). `combat.combat_odds_of`.
3.17 Match-behind-flag `TRADE_IN_MODE` row 13. Live trade-in is 90 percent and stays off. Legacy stays 25 percent. Itemised parts are `TRADE_IN_PARTS_MODE` row 76. `constants.trade_in_live`.
3.18 Match. A player can own more than one ship. `constants.fleet_on`.
3.19 Match. Empty ships can be captured. `CAPTURE_MODE` is tw2002. `constants.capture_on`.
3.20 Match. Alignment of 1,000 is commissioned. Police HQ raises 500 through 999 to 1,000. An evil ISS is repossessed on the move. `victory.is_commissioned`, `fed.handle_apply_commission`, `fed.check_iss_repo_on_move`.
4.1 Match. R4 A. `GENESIS_TORPEDO_COST` is 25,000. A normal game charges that. The empty start is `GENESIS_START_MODE` row 24. A typed name is `GENESIS_NAME_MODE` row 120. `GENESIS_TORPEDO_COST_LIVE` 20,000 stays on the hardware card and is not the adopted price. `runner` genesis deploy.
4.2 Match-behind-flag `ATOMIC_DETONATOR_MODE` row 89, NOTE 78. The detonator is the planet killer. The port-nuke atomic mine is not sold when the switch is on. `runner._handle_deploy_atomic`.
4.3 Match. Marker beacons are on. `runner._handle_buy_equip`.
4.4 Match. Corbomite is on. `combat` corbomite fire.
4.5 Match. Cloaks are on. `CLOAK_FAIL_RATE` 0.03 is GameA `Cloak Fail Percent=3%` (`docs/playtests/twgs-live/twstats-costs-ven.txt`) and stays the stored rate. `constants.hardware_tw2002`.
4.6 Match. An ether probe walks the route up to `PROBE_MAX_HOPS` (45) and dies at the first hostile fighters. `scanners.handle_probe`. The owner's name on that notice is `PROBE_SHOOTDOWN_MODE` row 99, NOTE 85, and stays off.
4.7 Match. Mine disruptors are on. `hardware` disruptor path.
4.8 Match-behind-flag. Counted once. Detonation is Match: stored half-count at 20 (`hardware.armid_detonation_hits`, profile row 92). Shop unit price is this grade on `HARDWARE_PRICE_MODE` row 14. Stored `ARMID_MINE_COST` is 100. The live card `ARMID_MINE_COST_LIVE` is 1,000 (`armid_mine_cost`). The Bible (S3 Hardware Emporium) prints no Armid unit price: half the mines, 20 damage, sector cap sysop-configurable. Cabal `twgs.html` General Editor Three prints $4,000 in the same TEDIT sample as Genesis $80,000. That sample is not a third price. Ven GameA TWSTATS prints `Armid Mine=1,000 cr`, already on this card (`docs/playtests/twgs-live/twstats-costs-ven.txt`). `constants.armid_hit_damage`.
4.9 Match. Limpets attach and can be queried. Stored removal is 1,250 (`LIMPET_REMOVAL_COST`, cabal TEDIT). Live GameA is 5,000 behind `hardware_price_live` via `limpet_removal_cost` (SOURCE-CONFLICT, Ven 2026-10-24). Same fee at StarDock and Class 0. `hardware.handle_remove_limpet`.
4.10 Match-behind-flag `PHOTON_LIMPET_MODE` row 174, NOTE 148. The level 6 interdictor damp is Match-behind-flag `PHOTON_INTERDICT_DAMP_MODE` row 234: legacy still holds, matching S1, and on, the hold fails open for the wave, matching HardwareMenu. The wave decloaks, damps a quasar, and holds mines and fighters. A limpet during that wave stays off until the limpet switch is on. GameA FedSpace Photons=False, Photons Disable Players=True, and Multiple Photons=False are `PHOTON_CLOAK_SETTINGS_MODE` row 230 and stay off in a stored game. Duration stays 1 day-tick. GameA `Photon Missile Duration=20 Sec` is DIFFERENT and deferred (cabal `twgs.html` and the modern manual print 1 second, Gypsy prints 10 seconds, no realtime clock). Those three seconds were not collapsed. No duration switch was added. Price SOURCE-CONFLICT: stored `PHOTON_MISSILE_COST` 12,000. Live GameA TWSTATS `Photon Missile=40,000 cr` is `photon_missile_cost` on `hardware_price_live` (Ven 2026-10-24). Cabal sample is 160,000. DIFFERENT on the stored card. `runner` photon handler, `runner._try_interdict`.
4.11 Match. Density info needs a bought scanner. `scanners.scan_reason`, `runner._buy_scanner`.
4.12 Match. Holo info needs a bought scanner. `scanners.scan_reason`, `runner._handle_scan`.
4.13 Match-behind-flag `PLANET_SCANNER_MODE` row 43 (`planet_scanner_live`). Shielded planets stay visible until the scanner is on. EIS HardwareMenu: owner and fighters of a planet with no shields. `runner._buy_planet_scanner`. `observation._planet_brief` (~1990) adds fighters when shields are 0. A shielded planet stays dark.
4.14 Match-behind-flag `DETECT_GEAR_MODE` row 34. Same probe as 2.17. `constants.detect_gear_live`.
4.15 Match. Ship TransWarp is on. `SHIP_TW_MODE` is tw2002. Price SOURCE-CONFLICT: stored cabal samples `SHIP_TW_TYPE1_COST` 12,500, `SHIP_TW_TYPE2_COST` 20,000, and `SHIP_TW_UPGRADE_COST` 9,000 stay. Live GameA TWSTATS `Type I TWarp=50,000 cr`, `Type II TWarp=80,000 cr`, `TWarp Upgrade=10,000 cr` is `ship_tw_type1_cost` / `ship_tw_type2_cost` / `ship_tw_upgrade_cost` on `hardware_price_live` (Ven 2026-10-24). Citadel Transport Unit 50,000 and Upgrade 25,000 already match `PLANET_TRANSPORTER_COST_FIRST` / `PLANET_TRANSPORTER_COST_EXTRA`. No shop switch. `constants.ship_tw_on`. The capture note marked the stored-versus-printed prices DIFFERENT and queued; the live card is the quote path.
4.16 Match. `SHIP_TRANSPORT_RANGE` is the Bible chart. The ISS stays 10, not the MBBS prose 15. `fleet.transport_range`, `fleet.handle_ship_transport`.
4.17 Match-behind-flag `SHIP_CHART_CAP_MODE` row 96, NOTE 82. Live adds the ether-probe cap of 25. Mines, genesis, and photons are `SHIP_CAPACITY_MODE` row 229, not this switch. Cloaks stay 5. `constants.ship_chart_cap_live`.
5.1 Match. Entry order is NavHaz, limpet, armids, sector quasar, then fighters. `runner._apply_sector_hazards`.
5.2 Match. NavHaz damages on the percent, and FedSpace clears it at night. `hardware.navhaz_pct`, `hardware.tick_navhaz`.
5.3 Match. Armid damage is the stored half detonation. `hardware.armid_detonation_hits`. Profile row 92, no helper.
5.4 Match-behind-flag `OFFENSIVE_CLASH_MODE` row 7. The 1.25 wave cap is coded and off. `combat.offensive_wave_size`.
5.5 Match. Defensive fighters challenge an entering ship. `combat.open_challenge`.
5.6 Match. The toll is 5 credits per fighter, paid to pass, and collected by picking the fighters up in that sector. `constants.SECTOR_TOLL_CREDITS_PER_FIGHTER`, `runner._handle_pay_toll`, `runner._handle_recall_deployed`.
5.7 Match. The tw2002 exchange is the S4/S6 Safety Rating model and the printed expected value (S3 Scout Marauder, S2 1:1 example, S7 capture formula). No source prints a random term (S7 "unable to determine the random factors"), so the loss split is the expected value under every profile. No switch; `tests/test_combat_exchange_sources_v1.py` pins the printed examples. `combat._resolve_ship_attack_tw2002`.
5.8 Match. A ship can send only its charted fighters in one attack. `combat.attack_cap`.
5.9 Match. Retreat is a verb and a flee spends extra turns. The published 1.25 line is `SHIP_FLEE_MODE` row 56. `combat._flee`.
5.10 Match-behind-flag `SPECIAL_HULL_RULES_MODE` row 105, NOTE 86. An Interdictor holds other ships, and a Tholian defending its corp planet fights at 4:1. Both need the roster switch. `combat.hull_interdict_reason`.
5.11 Match. Surrender is a verb. `combat` challenge settle.
5.12 Match-behind-flag `DEATH_POD_MODE` row 29. A destroyed ship becomes a pod. The clean loadout stays off. `combat._strip_ship`, `combat._destroy_ship_tw2002`.
5.13 Match-behind-flag `DEATH_DELAY_MODE` row 93, NOTE 79. TWGS v3 Death Delay is Yes/No, not S7's N midnights. Past Deaths Per Day (default 0) the pilot waits until the next day. Legacy ignores the setting. Two pods a day and out-until-midnight are the stored death path. `REENTRY_FIGHTERS_MODE` row 180, NOTE 158, stocks the free Scout. `runner.tick_day`, `combat._destroy_ship_tw2002`.
5.14 Match-behind-flag. R5 B. A pod still costs `POD_EXP_LOSS` 10% experience and no alignment. A Ship Destroyed that is not the button still costs `SD_EXP_LOSS` and `SD_ALIGN_LOSS`, half of each. Self-destruct is `SELF_DESTRUCT_PENALTY_MODE` row 235: half the experience, a negative alignment cut in half, a non-negative alignment left alone, and the sit-out (today and tomorrow). Off, the button still uses the ship-destroyed half of either sign. `combat._destroy_ship_tw2002`, `ship_exit.handle_self_destruct`.
5.15 Match. Furbing another ship's holds is on. `combat._destroy_ship`.
5.17 Match. Corbomite and disruptors fire in combat. `combat._resolve_ship_attack_tw2002`.
5.18 Match-behind-flag `PHOTON_FOLLOW_DAMP_MODE` row 90. A follower who enters the wave is damped when that switch is on. Decloak and the quasar damp are already in the wave. The limpet is `PHOTON_LIMPET_MODE` row 174, NOTE 148. The level 6 interdictor during that wave is `PHOTON_INTERDICT_DAMP_MODE` row 234: legacy still holds, matching S1.
5.19 Match-behind-flag `PLANET_LANDING_COMBAT_MODE` row 54. Landing on a defended planet is a fight only when the switch is on. A normal game still seizes. `constants.planet_landing_combat_on`.
5.20 Match-behind-flag. R6 A. `FEDSAFE_FIGHTER_CAP_MODE` row 167. More than 50 fighters removes FedSpace protection. 50 is still safe. Attacking a fedsafe trader in FedSpace summons Captain Zyrain and pods the attacker (`fed.protect_fedspace_attack`, `FED_PROTECT_PUNISH` pod, stored `FED_MODE` tw2002). Attacking a Federal costs 10 alignment and the pod. Evil traders are not protected (`victory.is_fedsafe`). Off, fighter count does not matter.
6.1 Match-behind-flag `SCANNER_FOG_MODE` row 44 (`scanner_fog_live`). Planet fighters and shields stay hidden until the planet scanner is on. `observation._planet_brief` (~2007) pops owner, fighters, and shields unless the viewer has landed. A bought planet scanner restores owner and fighters only when shields are 0.
6.2 Match. R7 A. Class M level 1 in `CITADEL_CLASS_COSTS` is the printed 1,000 colonists, 300 fuel, 200 organics, 250 equipment, and 4 days. A normal game uses that table. `CLASS_M_FIDELITY_MODE` still multiplies class M colonists by 1,000 when the profile is on. This adoption did not flip that switch. Build days are `CITADEL_DAYS_MODE` row 2. `constants.citadel_fidelity_rules`.
6.3 Match-behind-flag. The handbook curve is on the tip (#183). Printed maximums are `PLANET_MAX_COLONISTS` and `PLANET_MAX_STOCK`. `PLANET_ECONOMY_MODE` tw2002 caps stock and total colonists and does not replace the day tick. `V311_PROFILE`, `PLANET_PROD_MODE` live, and `PLANET_GROWTH_MODE` tw2002 turn the curve on (`planet_handbook_on`): each product pool peaks at half its printed maximum and produces 0 at that maximum. A pool below half grows about 5 percent and a pool above half dies about 5 percent. S1 prints no percent. `planets._worked`, `tests/test_planet_handbook_curve_v1.py`.
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
8.1 Match-behind-flag. R8 A. Hull counts and the approximate FERRSPEC odds stay the stored table. `FERRENGI_ODDS_MODE` row 200, NOTE 164, reads the Bible chart: 1.2 / 1.4 / 1.4, an Assault Trader volley of 2,000, and a holo scanner on that hull. It stays off. `FERRENGI_ATTACK_MODE` row 173, NOTE 148, is still the one-volley gate and still uses the FERRSPEC 1,000 while the odds switch is off. `constants.ferrengi_odds_for_hull`, `combat._resolve_ferrengi_chart_attack`.
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
9.8 Match. R9 B. Port prices improve with experience up to `PORT_PRICE_EXPERIENCE_CAP` (`economy._experience_span`). Rob max `ROB_CREDIT_FACTOR` exp x 6 and steal max exp / `STEAL_HOLD_DIVISOR` 21, which is (3 / RobFactor) and (30 x StealFactor) at the TWGS default 50% / 70% (cabal formulas.html, modern manual twgs-settings). `rob_steal.max_rob_credits`.
9.9 Match-behind-flag `MIXED_CORP_EXP_RULE` row 72. The cabal least-extreme loss is selected by the profile and stays off in the stored value. `corp.mixed_loss`.
10.1 Match. R10 A. `corp_create` at the StarDock; no source prints a charter cost, so `CORP_CREATE_COST` 0 stays. Only the C.E.O. buys a FlagShip (`CFS_CEO_RULE` purchase). A member may board one. `CFS_CEO_USE_MODE` still blocks that boarding when set to v311 by itself, and the profile does not select it. `corpships.board_block`.
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
11.1 Match-behind-flag `HARDWARE_PRICE_MODE` row 14. The live shop card is coded and off. Ship TransWarp Type I 50,000, Type II 80,000, and the upgrade 10,000 are on that card (stored 12,500, 20,000, and 9,000 stay). Photon missile 40,000 is on that card (stored 12,000 stays). Atomic detonators stay off this switch. SOURCE-CONFLICT. `constants.hardware_price_live`. Ven 2026-10-24 GameA TWSTATS prints Type I TWarp=50,000 cr, Type II TWarp=80,000 cr, TWarp Upgrade=10,000 cr, Citadel Transport Unit=50,000 cr, and Citadel Transport Upgrade=25,000 cr. Citadel labels already match the planet transporter. The capture note marked those five DIFFERENT and queued.
11.2 Match-behind-flag `SHIP_ROSTER_MODE` row 4 and `TRADE_IN_MODE` row 13. The yard and the 90 percent trade-in stay off. `constants.ship_specs`.
11.3 Match. Police HQ can grant a commission. `victory.is_commissioned`.
11.4 Match. A killed player can carry a bounty. `constants.REWARD_TARGET_RULE`.
11.5 Match. The galactic bank is on. `BANK_MODE` is tw2002. `bank.collect_daily_tax`.
11.6 Match-behind-flag `TAX_RULE_MODE` row 8. Ten percent of cash on hand at 50,000 or more, alignment above 0, once per day. `bank.collect_daily_tax`.
11.7 Match-behind-flag `UG_NAME_MODE` row 184, NOTE 162. The door, the password, and hit contracts are in. NOTE 129 (`name-change.txt`): a total unknown at 1 experience can buy a new name for 100 credits when the switch is on. A higher experience has no printed price. The Underground menu sold no goods. `UG_NAME_CHANGE` stays false. `tavern.handle_rename`.
11.8 Match. The tavern is on. `TAVERN_MODE` is tw2002. Announcement 100 already matches. Drink 80 and food 24 are `TAVERN_BAR_PRICE_MODE` and stay off, so the stored prices stay 20. One Tri-Cron match is Match-behind-flag `TRICRON_MODE` row 231, NOTE 129. It follows `tricron.txt` when the switch is on: ante 100, 10 rounds, payback 2 to 1, jackpot 5,000. Stored default stays legacy. `constants.tavern_on`, `tavern.handle_tricron`.
11.9 Match-behind-flag `FED_HUNT_MODE` row 185, NOTE 162. Feds tow, and they answer some crimes. An evil ship that meets a Federal is destroyed when the switch is on. A sector with no Federal is left alone. `fed.hunt_evil_meeting_federal`.
11.10 Match-behind-flag `SPECIAL_PORT_DEFENCE_MODE` row 146, NOTE 102. StarDock and Class 0 take 248,000 fighters, then 890,000, and the Feds rebuild in 14 days. Numbers UNVERIFIED. `runner._rebuild_special_ports`.
11.11 Match-behind-flag. Density, the one-way share, the 30 percent two-way lanes and the 95 percent initial starports are `BIG_BANG_DENSITY_MODE`, `ONE_WAY_SHARE_MODE`, `TWO_WAY_WARP_MODE` and `BIG_BANG_BUILT_MODE` (Big_Bang.html C 40%, D 95%). The B course length 45 is checked by test. Bubbles are Gold-only (S1), so v3.11 needs none (R11 A). `universe.generate_universe`.
12.1 Match. Turns per day are a game setting. `models.GameConfig`.
12.2 Match-behind-flag `TURN_REGEN_MODE` row 5. Turns can come back across 24 hours. `LIVE_PACE_MODE` row 6 goes with it. `constants.turn_regen_live`.
12.3 Match. R12 A. Ships spend turns. `DAY_ROLL_CLOCK_MODE` row 81 rolls the day while a seat holds the turn. Planets produce when the day changes. `PLANET_REALTIME_PROD_MODE` stays off the profile. No speed table was added. `runner.apply_action`.
12.4 Match-behind-flag. The printed lists are cabal `glossary.html` Extern and Midnight, the docs-wiki Glossary numbered Extern list (1–17) and Midnight list (1–5), cabal `twgs.html` (inactive user 30, inactivity timeout 14,400), the MBBS manual (nightly Fed tow, 2 pods per day), and Gypsy (tow when Extern runs). `runner.tick_day` runs the corp penalty and the corp-break-in reset, the Class 0 sweep, Terra regen, empty-ship repossession (a tow lock is kept), Fed tows, port regen, bust clearing, photon waves, cloak fails, NavHaz, alien hops, planet production, citadels, port construction, treasury, and tax. The day number resets the Grimy curse, colonist jettison, Underground password attempts, and the 2-pod count. Class 0 and StarDock prices follow the day. A living trader gains the midnight experience and alignment. A death delay counts down. Collisions stay `PLANET_COLLISION_MODE`. Class 0 and Class 9 rebuilds stay `SPECIAL_PORT_DEFENCE_MODE`. `INACTIVE_USER_MODE` row 177 and `INACTIVITY_TIMEOUT_MODE` row 178 stay off. MSL citadels stay `CLASS0_EXTERN_PLANET_RULE` keep: the wiki prints a drop to level 2, and t21 already took TWGS keep. NavHaz outside FedSpace stays `NAVHAZ_DISPERSION_PER_DAY` 3: cabal `twgs.html` prints 100 percent, and the hardware note already took the MBBS 3 percent. v3.06 fixed maintenance deletes that turned assets rogue, and Iago 47 keeps the corporation when a C.E.O. is deleted for non-play, so that sentence was not a new switch. No new switch.
12.5 Match-behind-flag `EXP_SCORE_MODE` row 28. A normal game still ends on net worth. Experience ranking is coded and off. The day cap, the last player standing, the credit bar, and a creator end have no printed v3.11 number. NOTE 158 left them. `victory.check_victory`.
12.6 Match-behind-flag. R13 A. The v3.11 sample prints tournament mode off and unlimited times blown up. `TIMES_BLOWN_MODE` row 202, NOTE 164, says so on the legacy destroy line when elimination is off, and stays off. The later lockout was not added. `DEATH_DELAY_MODE` is the timeout. `combat._legacy_destroy_summary`.
12.7 Match-behind-flag `DAILY_STATS_MODE` row 47. The daily stats screen is coded and off. `observation.build_observation`.
13.1 Match-behind-flag `MAIL_MODE` row 161, NOTE 103, and `COMMS_V311_MODE` row 176, NOTE 142. A hail flashes for about 10 seconds, and mail waits for an offline trader. The same-sector hail is the comms switch. `runner._handle_hail`.
13.2 Match-behind-flag `RADIO_CHANNEL_MODE` row 46. Radio channels are coded and off. `runner._handle_radio`.
13.3 Match-behind-flag `MAIL_MODE` row 161, NOTE 103. Stored mail and the New Mail line stay off until the switch is on. `runner._handle_hail`.
13.4 Match-behind-flag. `OWNER_HAZARD_NOTICE_MODE` row 55 and `SIEGE_REPORT_MODE` row 59 tell the owner about a landing, a fighter hit, a mine, and a siege. NOTE 163 graded the row on those two. `FIGHTER_REPORT_MODE` row 203, NOTE 164, is a separate list of sectors where that trader owns fighters, omitting a count of 0. It is not an observation field, and it does not grade the row a second time. `observation._event_visible_base`, `combat.fighter_report`.
13.5 Match. An ether-probe report is the route it walked, and it names the sector where fighters destroyed it. `scanners.handle_probe`.
13.6 Match-behind-flag `FEDCOMM_MODE` row 48. The FedComm notice is coded and off. `class0.extern_sweep`.
14.1 Match-behind-flag `CIM_MODE` row 186, NOTE 162, and `NAVPOINT_MODE` row 181, NOTE 159. The course plotter and avoids (`AVOID_MODE` row 35) are in. NavPoints are four named slots, Terra and StarDock, set, list, clear, and a course. CIM lists explored sectors and ports, hides a port behind hostile fighters, and plots a path. NOTE 110 / NOTE 129: Computer B is Begin Self Destruct when ship exit is on (`computer-b.txt`). N aborts. Y reuses `handle_self_destruct`. `<` stays the previous-sector key. No new row. Backtrack, quick stats, and find route are not that whole menu. `v311_buildable.handle_cim`, `navpoints.menu_rows`.
14.2 Match. Towing is on. `TOW_MODE` is tw2002. `constants.tow_on`.
14.3 Match-behind-flag `PLANET_BUST_EXP_MODE` row 149, NOTE 102. The owner may destroy the planet they created for 75 experience (genesis 25 plus destroy 50). `legality.planet_destroy_reason`.
14.4 Match. An unmanned ship can still hold fighters. While `V311_PROFILE` is on, `observation` game status leaves those fighters out of the V-screen total. Legacy still counts them. No switch was added for that display. Profile GAP 14.4 note.
14.5 Match-behind-flag `EVIL_TRADE_LOOP_MODE` row 166, NOTE 115. A negative-alignment seat steals, dumps, and beams, or robs and beams, when the profile is on. `constants.evil_trade_loop_live`.
14.6 Match-behind-flag. R14 A. Alliances are off under `ALLIANCE_OFF_MODE` row 222: the Bible calls corporate treaties "by no means binding and are not enforced". The planet bonus stays off under `PLANET_DIVIDEND_PAY_MODE`. The day cap and the 100,000,000 credit finish stay. `ECON_WIN_MODE` is not selected by the profile. `victory._check_victory`, `legality`, `runner._handle_propose_alliance`.

There is no row 5.16, 7.1, or 8.5. That is the same 171 ids as v5.
