# v311-profile-v1 (COMMANDER NOTE 57, kill cash from NOTE 59)

`V311_PROFILE` is one switch in `src/tw2k/engine/constants.py`. Default `"legacy"`. Set to `"v311"`, it turns on the RULINGS_v311.md rulings for items 1-6, the Addendum A kill rule (NOTE 59) and every MASTER_PLAN switch marked yes ("yes", "yes, after check", "yes, Ben confirm", "yes for AI-seat games"). Nothing is flipped by default; the bank pin `9b607d3dae940c0b1a69f6d7` and the 10-day digests `24863a3d` / `98a47c8a` stay with the profile off.

It is its own switch. `TW2002_LIVE_PROFILE` stays as it is (MASTER_PLAN: "build a v3.11 profile from the yes list instead"); turning the live profile on does not turn `v311_profile()` on. The code list is `K.V311_PROFILE_HELPERS`, and `tests/test_v311_rulings_v1.py::test_profile_sets_exactly_the_documented_set` checks that this file, that dict, and the helpers agree: with only `V311_PROFILE` on, every helper below returns True and every other helper in `tests/test_tw2002_live_profile_v1.py` HELPERS returns False.

Sources: `C:\Users\sugar\tw2002_reference\RULINGS_v311.md` (s1-s7 and Addendum A) and `C:\Users\sugar\tw2002_reference\MASTER_PLAN.md` ("Engine switches still defaulting to legacy").

## The switch set (96 helpers)

Row 84 is still reserved for NOTE 75 and is not in this table yet. NOTE 78 uses rows 85-89. NOTE 86 uses rows 105-107.

| # | switch | helper | why it is on | MASTER_PLAN note |
|---|---|---|---|---|
| 1 | `STARTING_PACKAGE_MODE` | `starting_package_live` | RULINGS s2: "Merchant Cruiser, 300 credits, 30 fighters, 20 holds, 0 shields, 250 turns/day, plus a free class M start planet" (MASTER_PLAN hold, ruled by NOTE 57) | - |
| 2 | `CITADEL_DAYS_MODE` | `citadel_days_live` | RULINGS s3: L1..L6 days per class, "CITADEL_DAYS_MODE=live and CITADEL_BUILD_TIME_SCALE=1.0" (raw days ignore the scale) (MASTER_PLAN hold, ruled by NOTE 57) | - |
| 3 | `CITADEL_COST_MODE` | `citadel_fidelity_rules` | RULINGS s3 "class commodity table (no credits)"; MASTER_PLAN yes, after check. Checked: CITADEL_FIDELITY_MODE tw2002 (default) already charges class goods with no credits; the switch stays "credits" because "class" takes the hidden path that consumes colonists | - |
| 4 | `SHIP_ROSTER_MODE` | `ship_roster_live` | RULINGS s4: the 17-hull v3.34b shipyard catalog, "load the full table above" (MASTER_PLAN hold, ruled by NOTE 57) | - |
| 5 | `TURN_REGEN_MODE` | `turn_regen_live` | RULINGS s5: "turns come back hourly, pro-rated ... capped at the daily allowance; no midnight full refill" (MASTER_PLAN hold, ruled by NOTE 57) | - |
| 6 | `LIVE_PACE_MODE` | `live_pace` | RULINGS s5: "TURN_REGEN_MODE=live + LIVE_PACE_MODE=live" (MASTER_PLAN hold, ruled by NOTE 57) | - |
| 7 | `OFFENSIVE_CLASH_MODE` | `offensive_clash_held` | RULINGS s6: 1:1, "1.25 x (the ship's MAX fighters + MAX shields), or all they have if fewer" (MASTER_PLAN hold; the wave cap is now coded) | - |
| 8 | `TAX_RULE_MODE` | `tax_v311` | RULINGS s7: 10% of cash on hand at 50,000 or more, alignment above 0, once per day, +1 alignment per 1,500 (new switch, NOTE 57 item 6) | - |
| 9 | `FEDSPACE_DEPLOY_MODE` | `fedspace_deploy_live` | MASTER_PLAN yes | seen twice in live v3.34b (REPORT2 s4, s9) |
| 10 | `PORT_CLASS_MAP_MODE` | `port_class_live` | MASTER_PLAN yes | original class numbers (cabal twgs.html, Bible; GAP 2.2); class 7/8 caveat while StarDock is id 8 |
| 11 | `HAGGLE_WINDOW_MODE` | `haggle_window_live` | MASTER_PLAN yes | flip with HAGGLE_LIVE_MODE; older written band, superseded by the live bands |
| 12 | `OWN_PLANET_TURN_MODE` | `own_planet_turn_live` | MASTER_PLAN yes | REPORT2 s6: land/lift off on own planet 0 turns |
| 13 | `TRADE_IN_MODE` | `trade_in_live` | MASTER_PLAN yes | 90% receipts seen live (REPORT2 s4); EIS ShipyardMenu trade-in |
| 14 | `HARDWARE_PRICE_MODE` | `hardware_price_live` | MASTER_PLAN yes | live shop card (REPORT2 s4); v3.11 prices are sysop-set, no CONFIRMED doc price (GAP 4) |
| 15 | `PLANET_SHIELD_ACTIVE_MODE` | `planet_shields_active` | MASTER_PLAN yes | S1 s V: shields are the Level 5 system |
| 16 | `GENESIS_SCORE_MODE` | `genesis_score_fair` | MASTER_PLAN yes (fair) | scoring fix only; original ranks by exp |
| 17 | `ACTION_RESULT_MODE` | `action_result_report` | MASTER_PLAN yes for AI-seat games (report) | API shape only; the AI seat needs ok/rejected/turns_spent |
| 18 | `ASSIGN_POOL_FIX_MODE` | `assign_pool_fix_live` | MASTER_PLAN yes | bug fix (to=colonists lands in fuel_ore) |
| 19 | `HOLD_RULES_MODE` | `hold_rules_live` | MASTER_PLAN yes | wording only |
| 20 | `PLANET_NW_MODE` | `planet_nw_live` | MASTER_PLAN yes | score display only |
| 21 | `PORT_PRICE_MODE` | `port_price_live` | MASTER_PLAN yes | cabal formulas/economy MCIC + experience (GAP 2.3) |
| 22 | `PORT_REGEN_MODE` | `port_regen_live` | MASTER_PLAN yes | REV v3.05 standard 5%/day |
| 23 | `SHOP_PRICE_MODE` | `shop_price_live` | MASTER_PLAN yes | cabal formulas hold cost; fighter/shield wave (GAP 2.11 conflict noted) |
| 24 | `GENESIS_START_MODE` | `genesis_start_live` | MASTER_PLAN yes | S1: new planet has no colonists and usually no product (GAP 6.5); Terra form exists |
| 25 | `TERRA_COLONIST_MODE` | `terra_colonist_live` | MASTER_PLAN yes | REPORT2 s6/s11: 30,000 pool, 1 group per hold, 750/day; flip with CLASS_M |
| 26 | `PLANET_PROD_MODE` | `planet_prod_live` | MASTER_PLAN yes | S1 colonists-per-unit table (GAP 6.4) |
| 27 | `CITADEL_PERK_MODE` | `citadel_perk_live` | MASTER_PLAN yes | S1 s V L2 and L5 |
| 28 | `EXP_SCORE_MODE` | `exp_score_live` | MASTER_PLAN yes, Ben confirm | original ranks by experience (GAP 12.5); changes who wins a match |
| 29 | `DEATH_POD_MODE` | `death_pod_live` | MASTER_PLAN yes | REPORT2 s8 pod loadout |
| 30 | `PORT_ATTACK_MODE` | `port_attack_live` | MASTER_PLAN yes | EIS Tactical (GAP 2.15); only class 6 barrage measured |
| 31 | `HAGGLE_LIVE_MODE` | `haggle_live` | MASTER_PLAN yes | REPORT2 s3 bands; button tests already run with it |
| 32 | `DISCOVERY_EXP_MODE` | `discovery_exp_live` | MASTER_PLAN yes | REPORT2 s1/s7 +1 exp first dock |
| 33 | `FED_SHIPS_MODE` | `fed_ships_live` | MASTER_PLAN yes | Bible/Iago Fed captains; REPORT2 s11 (placement was that game's) |
| 34 | `DETECT_GEAR_MODE` | `detect_gear_live` | MASTER_PLAN yes | REPORT2 s4 prices |
| 35 | `AVOID_MODE` | `avoid_live` | MASTER_PLAN yes | REPORT2 s8; EIS computer avoids |
| 36 | `OWN_PLANET_FIGHTER_MODE` | `own_planet_fighter_live` | MASTER_PLAN yes | usability: owner lands on own planet during a challenge; not pinned by a source |
| 37 | `RANK_DISPLAY_MODE` | `rank_display_live` | MASTER_PLAN yes (exp) | goes with EXP_SCORE_MODE |
| 38 | `API_ARGS_MODE` | `api_args_live` | MASTER_PLAN yes for AI-seat games | API hardening only |
| 39 | `PLANET_COLONIST_CAP_MODE` | `planet_colonist_cap_live` | MASTER_PLAN yes | otherwise class U L3 can never start (S1 s VII) |
| 40 | `LANDED_STATE_MODE` | `landed_state_live` | MASTER_PLAN yes | correctness: lift off before warp/trade |
| 41 | `PLANET_DIVIDEND_PAY_MODE` | `planet_dividend_off` | MASTER_PLAN yes (off) | dividend is not in the original (GAP 6.13); Ben approved fidelity-first |
| 42 | `PLANET_VALUE_SCORE_MODE` | `planet_value_scored` | MASTER_PLAN yes (experience) | goes with EXP_SCORE_MODE |
| 43 | `PLANET_SCANNER_MODE` | `planet_scanner_live` | MASTER_PLAN yes | EIS HardwareMenu; 30,000 live (GAP 4.13); flip with SCANNER_FOG |
| 44 | `SCANNER_FOG_MODE` | `scanner_fog_live` | MASTER_PLAN yes | EIS HardwareMenu (GAP 6.1) |
| 45 | `CITADEL_PARK_MODE` | `citadel_park_live` | MASTER_PLAN yes | Bible, EIS CitadelMenu (GAP 6.9) |
| 46 | `RADIO_CHANNEL_MODE` | `radio_channel_live` | MASTER_PLAN yes | Bible (GAP 13.2) |
| 47 | `DAILY_STATS_MODE` | `daily_stats_live` | MASTER_PLAN yes | V screen counts (REPORT2 s1) |
| 48 | `FEDCOMM_MODE` | `fedcomm_live` | MASTER_PLAN yes | Gypsy (GAP 13.6) |
| 49 | `CORP_RANK_MODE` | `corp_rank_live` | MASTER_PLAN yes | EIS CorporateMenu (GAP 10.11) |
| 50 | `CLASS_M_FIDELITY_MODE` | `class_m_fidelity_live` | MASTER_PLAN yes (Ben NOTE 19) | Ben's NOTE 19 ruling: colonists in thousands; confirm (later notes still call production ratios Ben's call) |
| 51 | `PORT_STOCK_FIDELITY_MODE` | `port_stock_fidelity_live` | MASTER_PLAN yes | live v3.34b stock; button tests already run with it |
| 52 | `SHIP_EXIT_MODE` | `ship_exit_on` | MASTER_PLAN yes | jettison and self-destruct are original commands (cabal pods.html) |
| 53 | `RIVAL_STRENGTH_MODE` | `rival_strength_live` | MASTER_PLAN yes | attack prompt shows target strength (fidelity_spotcheck_d5; wording UNVERIFIED) |
| 54 | `PLANET_LANDING_COMBAT_MODE` | `planet_landing_combat_on` | MASTER_PLAN yes | S1 s IX: invaders fight shields, reaction wave, defenders; legacy seizes for free |
| 55 | `OWNER_HAZARD_NOTICE_MODE` | `owner_hazard_notice_on` | MASTER_PLAN yes | Bible fighter reports (GAP 13.4, UNVERIFIED) |
| 56 | `SHIP_FLEE_MODE` | `ship_flee_published` | MASTER_PLAN yes | cabal fleeing.html 1.25 rule (GAP 5.9) |
| 57 | `PLANET_SHIELD_MODE` | `planet_shield_l5` | MASTER_PLAN yes | S1 s V L5 |
| 58 | `FERRENGI_ENGAGE_MODE` | `ferrengi_engage_on` | MASTER_PLAN yes | GAP 8.2 behaviour; tribute amounts UNVERIFIED |
| 59 | `SIEGE_REPORT_MODE` | `siege_report_on` | MASTER_PLAN yes | S1 s IX visible order of events |
| 60 | `PLANET_GROWTH_MODE` | `planet_growth_tw2002` | MASTER_PLAN yes | S1 half-cap growth/die-off; no upkeep |
| 61 | `KILL_CASH_MODE` | `kill_cash_held` | RULINGS Addendum A (live v3.34b, T1 and T6): "in normal play the killer gets nothing from a logged-off victim, and the victim's on-hand cash is destroyed". The 100% "credits worth" pay showed only for cash set in the sysop editor (T2-T5). Holds salvage stays ("salvaged these cargo holds: 7 empty") | NOTE 57 ADDENDUM replaces the old hold |
| 62 | `POD_CASH_MODE` | `pod_cash_live` | RULINGS Addendum A: "In every trial the victim's cash was gone and the pod held 25 credits." New switch (NOTE 59): after a kill by another player the pod holds `POD_CASH_CREDITS` (25) | - |
| 63 | `YARD_STATS_MODE` | `yard_stats_on` | RULINGS s4 (the yard shows the s4 roster figures). New switch (NOTE 60): the buy_ship params carry `stats_by`, the server figures of every hull (name, cost, holds of max holds, fighters, shields, turns per warp, odds, photons, TransWarp) for the roster in play | - |
| 64 | `CITADEL_TABLE_FIX_MODE` | `citadel_table_fix_live` | S1 section VII, class U row "Colo 3000 3000 8000 6000 8000 6000" (TWFAQ_20PLANET.txt agrees). New switch (NOTE 64 ADDENDUM): a class U citadel level 3 asks for 8,000 colonists (`CITADEL_S1_COLONISTS`); the stored `CITADEL_CLASS_COSTS` keeps 5,000 for legacy | - |
| 65 | `HOME_PLANET_MODE` | `home_planet_live` | REVISION.TXT 1558 (no new planet in an occupied sector) and the new-character transcript (Fuel Ore 45 / Organics 65 / Equipment 81 thousand). New switch (NOTE 66): the home planet is outside FedSpace, the player starts landed on it, and the 191,000 start is that split. Legacy stays in the start sector with the colonists unassigned | - |
| 66 | `CLASS_M_NW_MODE` | `class_m_nw_units` | S1 class M population is counted in thousands (Ben NOTE 19; `CLASS_M_PEOPLE_PER_THOUSAND`). `COLONIST_PRICE` is that handbook unit. A class M planet's net worth divides stored people by 1,000. The growth-dividend basis stays per person. | - |
| 67 | `CLASS_M_DROP_MODE` | `class_m_drop_units` | Terra live packs 1,000 people in a hold (`terra-colonists-v1`). Class M stores people. A drop of one hold adds 1,000 people; loading those people back uses one hold. Legacy Terra (one colonist per hold) is one handbook thousand, so the planet gains 1,000 people. | - |
| 68 | `CLASS_M_GENESIS_MODE` | `class_m_genesis_units` | `GENESIS_SEED_COLONISTS` (2,500) is the handbook founding population, sized for an L1 of 1,000. On a class M planet that stores people the seed is 2,500,000. The scale runs only while the seed is still placed. `GENESIS_START_MODE` (row 24, S1 / GAP 6.5) leaves a new planet empty, and that empty start wins when both are on. | - |
| 69 | `CORP_EXP_PENALTY_MODE` | `corp_exp_penalty_taken` | Hekate's TWGS table (`Misc_Alignment_changes_how_to_lower_twgs.txt`): experience 102 ended at 1, so the event names the experience taken. `"legacy"` keeps the formula in the summary and the `loss` field. `"taken"` reports what the floor removed. The experience math is the same. Stored default stays `"legacy"` | - |
| 70 | `CORP_LEAVER_DEPLOYMENTS` | `corp_leaver_to_ceo` | Live TWGS v3.34b: a member who leaves keeps no corporate fighters; they stay with the corp under the C.E.O. (`"to_ceo"`). The corp ticker stays. Personal deployments and limpets stay. A C.E.O. who leaves still dissolves the corp and rogues off-sector fighters. Stored default stays `"legacy"` | - |
| 71 | `CORP_ALIGNMENT_RULE` | `corp_join_check` | EIS Corporate menu, Join: the same alignment as the C.E.O. `"join_check"` refuses a join when the signs conflict. Alignment 0 fits either side. A member who later drifts is not ousted. The Extern experience penalty still runs. Stored default stays `"mixed"`; V311 selects `"join_check"` | - |
| 72 | `MIXED_CORP_EXP_RULE` | `mixed_corp_least_extreme` | Cabal `formulas.html`: Experience Loss = MIN(ABS(lowest_alignment), highest_alignment) / 4. Live tests agree. Stored default stays `"highest_good"`; V311 selects `"least_extreme"`. `MIXED_CORP_EXP_FLOOR` stays 1 | - |
| 73 | `ALIEN_COMBAT_FIX_MODE` | `alien_combat_fix_live` | NOTE 71: alien fighters trade 1:1 and shields soak first, so shields absorbed never exceed the volley or the shields held. Legacy keeps the odds formula | - |
| 74 | `HAGGLE_COUNTER_MODE` | `haggle_counter_live` | NOTE 71: a port counter keeps the seat's turn open (up to 4 rounds) and only a final refusal ends the trade. Empty holds and cargo on board are checked before credits. An offer past the counter can still be taken | - |
| 75 | `BOT_HAZARD_MEMORY_MODE` | `bot_hazard_memory_live` | NOTE 71: a bot's flee and route pick never choose Ferrengal, or a sector where it took mines or met hostile fighters that day, unless no other warp exists | - |
| 76 | `TRADE_IN_PARTS_MODE` | `trade_in_parts_live` | NOTE 73: the yard credits the old ship part by part (hull, holds, drive, computer, fighters, shields, scanner) at 90 percent, one credit less when that tenth is exact. `TRADE_IN_MODE` stays the surplus gate. Legacy stays a fraction of the sticker, and a pod still counts as a Scout | - |
| 77 | `TRADER_RANK_LIST_MODE` | `trader_rank_list_live` | NOTE 73: the observation lists every trader by experience (rank, name, title, experience, corp, ship, alive) and the end rule. No credits, net worth, or location | - |
| 78 | `NW_ESTIMATE_MODE` | `nw_estimate_live` | NOTE 73: extra holds at their trade-in value, cargo at what the seat paid, sector fighters at the fighter rate. It does not change the experience winner | - |
| 79 | `SEAT_IDLE_START_MODE` | `seat_idle_start_live` | NOTE 73: a seat's short idle clock starts when its client first connects. Before that there is no auto-WAIT | - |
| 80 | `BOT_DIPLOMACY_MODE` | `bot_diplomacy_live` | NOTE 73: a code bot accepts or declines an alliance on its next turn, and answers a hail with one canned line. `ALLIANCE_MODE` stays legacy | - |
| 81 | `DAY_ROLL_CLOCK_MODE` | `day_roll_clock_live` | NOTE 74: with the regen clock on, the day rolls when the mark passes even while an external seat holds the turn, and the next mark is the old mark plus the day length. Stored default stays legacy. Self-hosted beta games set the switch live | - |
| 82 | `PORT_BUY_PRICE_ANCHOR_MODE` | `port_buy_price_anchor_on` | D25-1 (NOTE 69): a buying port's live anchor is the hungry quote. `PORT_STOCK_FIDELITY` opens buyers at current 0, and the full-hold curve `(1.45 - 0.70*frac) / 0.75` then quotes about 1.93x (`38/73/102` become roughly fuel 51-87, organics 97-169, equipment 134-241). Live v3.34b day 1 is fuel 34.9-40.65, organics 62-75, equipment 100.7-105, and the price eases only a few percent as the port fills (StarDock equipment 105 at 51% remaining, about 100.8 at 37%). MCIC and the haggle window stay on top. The sell side is unchanged | - |
| 83 | `START_COLONIST_NW_MODE` | `start_colonist_nw_live` | NOTE 75: free start colonists still on the home planet are left out of net worth. The count falls first when they leave or die, and never goes below 0. Colonists bought at Terra, hauled in, or grown still count. Experience rank and production are unchanged. Stored default stays legacy | - |
| 85 | `TREASURY_CAP_MODE` | `treasury_cap_live` | PLN-r (NOTE 78): S1 treasury cap is 999,999,999,999,999. The stored cap stays 10,000,000. Interest, the deposit refusal, the legal room and the cockpit room line all read `planet_treasury_cap()` | - |
| 86 | `COURSE_MAX_MODE` | `course_max_live` | MOV-g (NOTE 78): a plotted course longer than 45 hops is refused. The 45 is UNVERIFIED for TWGS 3.11 (Big_Bang.html option B shapes the map; it is not confirmed as the plot limit). Legacy still searches 60 hops and the rules line still says 10 | - |
| 87 | `BIG_BANG_DENSITY_MODE` | `big_bang_density_live` | MOV-h, MOV-i (NOTE 78): a new universe puts ports in about 40% of the deep sectors (the clone uses 65%) and planets in up to 20% (the clone uses 3%). Sectors 2-10 get no decorative Fed ports. Sol, Terra, StarDock (sector 1) and the Class 0 sectors chosen on the clone layout stay | - |
| 88 | `ONE_WAY_SHARE_MODE` | `one_way_share_live` | MOV-f (NOTE 78): when the game settings do not set `one_way_fraction`, the bang uses 0.03. A setting that sets it, including a beta game, keeps that value. The stored default stays 0.15 | - |
| 89 | `ATOMIC_DETONATOR_MODE` | `atomic_detonator_live` | SD-l (NOTE 78): the atomic detonator is the planet killer (colonists first, then the planet). The clone's port-nuke atomic mine is not sold and cannot be deployed. `ATOMIC_MINES_PORT_NUKE` stays True | - |
| 90 | `PHOTON_FOLLOW_DAMP_MODE` | `photon_follow_damp_live` | NOTE 79 SD-o. A photon into the next sector already shuts mines and fighters for the wave, and damps the quasar for the shooter and anyone already in that sector. Live also damps the quasar for a ship that enters while the wave is up. S1: citadel L5 with 200 shields still fires. Stored default stays legacy. Rows 83-89 are left open | - |
| 93 | `DEATH_DELAY_MODE` | `death_delay_live` | NOTE 79 CMB-n. S7 #16: `GameConfig.death_delay` of 0 or unset lets the pod fly. A number keeps that pod out until that many midnights pass. Blowing the pod up during the sentence adds the same number again. Stored default stays legacy, so the setting is ignored. The TEDIT maximum is not printed (UNVERIFIED). A flying pod that is destroyed does not start a new sentence (UNVERIFIED; the paragraph only adds days while the pilot is knocked out) | - |
| 94 | `BUST_CLEAR_MODE` | `bust_record_clear_live` | NOTE 82 TRD-k. REV v3.05: TEDIT sets how often Extern clears bust records. It defaults to nightly ("Clear Busts Every : 1 Days" in the cabal editor sample) and can be every 28th day. Stored default stays legacy, which still clears every Extern. Live reads `GameConfig.bust_clear_days`: 1 or 7. REPORT.md is on Ben's PC (UNVERIFIED). Rows 83-93 are left open | - |
| 96 | `SHIP_CHART_CAP_MODE` | `ship_chart_cap_live` | NOTE 82 SD-e. Mines, genesis and photons already follow the Bible ship chart on `SHIP_SPECS_TW2002` (`equip_room`). Cloaks are already 5 for any ship (`CLOAK_MAX`). Live adds the Bible probe cap of 25. Legacy leaves probes uncapped. The pod uses the same 25 (UNVERIFIED; the chart has no probe column) | - |
| 97 | `CORP_PLANET_DISBAND_MODE` | `corp_planet_disband_v306` | NOTE 82 PLN-q. Today's rule stays `CORP_DISBAND_PLANETS` `owner_keeps`. Live is REV v3.06: planets in the C.E.O.'s sector become his, and the rest are unclaimed. The older constant `v306` still selects that path. Unclaimed is the existing orphan, not a fighter-style rogue owner | - |
| 105 | `SPECIAL_HULL_RULES_MODE` | `special_hull_rules_on` | NOTE 86 CMB-m: a living Interdictor Cruiser holds every other ship in its sector (warp, TransWarp, combat flee, fighter retreat, Ferrengi-encounter flee), and a Tholian Sentinel defending a planet of its own corp fights at 4:1. Both need `ship_roster_live`. Stored default stays legacy | row 104 CMB-l was already the stored default |
| 106 | `FERRENGI_GRUDGE_MODE` | `ferrengi_grudge_on` | NOTE 86 FER-c: the Ferrengi that was attacked remembers that trader and hops toward them. A neighbour bands into a sector where the target has more fighters than this ship and another Ferrengi is already there or one hop away. The strong-target cutoff is UNVERIFIED. Stored default stays legacy | - |
| 107 | `FERRENGI_PACE_MODE` | `ferrengi_pace_on` | NOTE 86 FER-d: each living Ferrengi has a 1-in-20 chance to hop every 30 seconds (`FERRENGI_MOVE_ONE_IN`, `FERRENGI_MOVE_INTERVAL_S`). Regeneration stays one 20% step per day (`FERRENGI_REGEN_PCT`). The once-a-day hunt still makes the attack. Stored default stays legacy | row 108 SD-q was already the stored default |

Rows 95 and 98 were already done on this tip, so they are not helpers. Row 95, Class 0 price change and FedSpace tows and clean-up, already run in `tick_day`: `fighter_unit_price`, `shield_unit_price` and `hold_day_base` move with the day; `fed.run_tows` tows ships; `class0.extern_sweep` clears MSL and Class 0 fighters and mines; `hardware.tick_navhaz` clears FedSpace NavHaz. Row 98, the C.E.O. leaving, already dissolves the corp and rogues fighters outside his sector (`corp.handle_corp_leave`, `corp.disband`).

Rows 91 and 92 were already done on this tip, so they are not helpers. Row 91, player-kill experience, already uses `COMBAT_EXP_DIVISOR` (`opposite` 15, `same` 35, `neutral` 25) and `KILL_EXP_SHARE` 0.10 (`victory.combat_rewards`, `victory.kill_rewards`). The cabal page prints one experience formula for MBBS and Gold, and says the sector-fighter experience is the same as MBBS. A separate classic experience table is not printed. Row 92, armid mines, already detonates `count // 2` of them (`hardware.armid_detonation_hits`) at `ARMID_DAMAGE_TW2002` (20), or 30 when the live shop card is on (`armid_hit_damage`). CMB-c is a plan only (`docs/plans/ship-odds-exchange-v1.md`), not a helper.

NOTE 86 reserved rows 104-108. CMB-l (104) and SD-q (108) already run with the stored defaults, so this slice does not add `FED_RESPONSE_MODE` or `FED_COMMISSION_MODE`. FedSpace protection is `protect_fedspace_attack` (`src/tw2k/engine/fed.py`) called from `_handle_attack`. Commission is `handle_apply_commission` and `is_commissioned`, and an evil ISS is repossessed by `check_iss_repo_on_move`.

`DEATH_CREDITS_ON_HAND` is `"lost"` by default already (Addendum A: "DEATH_CREDITS_ON_HAND = \"lost\": CONFIRMED (victim keeps none of it)"). The profile keeps it as it is and reads no helper for it; `test_defaults_stay_legacy` and the Addendum A kill test pin it.

Mode values under the profile: `rank_display()` returns `"exp"`, `planet_value_score_mode()` returns `"experience"`, `genesis_score_fair()` and `action_result_report()` return True. `corp_alignment_rule()` returns `"join_check"` and `mixed_corp_exp_rule()` returns `"least_extreme"`. Stored values stay `"legacy"` (`CORP_ALIGNMENT_RULE` stays `"mixed"`, `MIXED_CORP_EXP_RULE` stays `"highest_good"`, `CORP_LEAVER_DEPLOYMENTS` stays `"legacy"`, `CORP_EXP_PENALTY_MODE` stays `"legacy"`).

## Left as they are

MASTER_PLAN no, no-op, or hold, with no ruling in NOTE 57. The profile does not touch them.

| switch | MASTER_PLAN | why |
|---|---|---|
| `PORT_OPEN_STOCK_MODE` | no | superseded by `PORT_STOCK_FIDELITY_MODE` |
| `TRADE_TURN_MODE`, `WARP_COST_MODE` | no-op | rule already on |
| `ALIGNMENT_MODE`, `RANK_TITLES_MODE`, `COMBAT_ODDS_MODE`, `CORP_RULES_V2_MODE`, `COCKPIT_PARITY_MODE` | no-op | legacy and live are the same |
| `PLANET_CLASS_MODE` | no | v3.11 genesis class is random |
| `BANK_LIVE_MODE` | no | v3.11 docs give the ~500,000 cap |
| `SEAT_DEADLINE_MODE`, `ASYNC_DAY_MODE` | no | match infrastructure |
| `ALLIANCE_MODE` | no | not in the original |
| `PLANET_REALTIME_PROD_MODE` | no | original produces at the nightly Extern |
| `UNIVERSE_TOPOLOGY_MODE` | no (for now) | code bots trap in dead ends |
| `GOLD_ALIEN_MODE` | no | Gold add-on |
| `AI_COCKPIT_SEAT_MODE` | no | test-only |
| `COCKPIT_FIELDS_MODE` | not in MASTER_PLAN | NOTE 56 harness block; Ben decides |
| `TW2002_LIVE_PROFILE` | no (as is) | turns on the no rows above |

## What the rulings changed in code

- Item 1 (s2): already built. `opening_loadout` gives 300 / 250 / 30, the Merchant Cruiser has 20 holds and 0 shields, and `grant_starting_planet` gives a class M planet. Tested.
- Item 2 (s3): already built. `CITADEL_CLASS_COSTS` raw days match the s3 table for all seven classes; `citadel_build_days` uses them as-is under `citadel_days_live()` (scale 1.0). Cost is the class goods, no credits, through `CITADEL_FIDELITY_MODE` tw2002. Note: with `CLASS_M_FIDELITY_MODE` on, a class M level needs colonists x1,000 (L1 1,000,000); other classes keep the S1 counts (U L1 3,000). Class M ratios are Ben's call (NOTE 41 item 10).
- Item 3 (s4): `SHIP_ROSTER_LIVE_TABLE` overlays cost, initial holds, max holds, max fighters, turns per warp and offensive odds for all 16 hulls; `ship_cost` reads it; the escape pod under the switch is 14,446 | 1-5 | 50 | 6 | 0.8 (still never sold).
- Item 4 (s5): `recover_turns` (the scheduler's clock) now goes through `refresh_offline_turns` (the action clock) when turn regen is live. Before, both paid the same seconds, and `recover_turns` floored each call, so calls a fraction of a second apart paid nothing. Under live pace with turn regen, a day rolls no sooner than `TURN_REGEN_DAY_SECONDS` after the last one, so a spent seat earns its allowance back first.
- Item 5 (s6): `combat._offensive_wave_tw2002` replaces the partial path. Wave = min(stack, ceil(1.25 x (max fighters + max shields))). At 1:1 it cancels shields first, then fighters. A wave larger than the ship's shields plus fighters destroys the ship. The rest of the stack stays as the sector's fighters. No random draw.
- Item 6 (s7): `TAX_RULE_MODE` (`"legacy"` | `"v311"`) and `tax_terms()`. Legacy is 5% over 100,000 at alignment 0 or more. v311 is 10% over 49,999 at alignment 1 or more. The bank, the prompt, the rules text and the bot tax-keep logic all read `tax_terms()`. Still collected once at the day tick.
- Item 7 (s1, replaced by Addendum A in NOTE 59): `kill_cash_held()` reads `V311_PROFILE`, so a kill under the profile pays the killer 0 and `bank.on_ship_lost` destroys the victim's cash on hand. `combat._destroy_ship_tw2002` then gives the pod `POD_CASH_CREDITS` (25) under `pod_cash_live()` when another player made the kill. `corpships.apply_furb` still salvages the holds ((holds + 3) // 3, so 7 from a 20-hold Merchant Cruiser). Addendum A Q6(b) was already true and is pinned by tests: a ship entering a non-corp player's fighters is challenged, the answers are attack, pay toll (toll fighters only, "if applicable"), retreat and surrender, other verbs are refused, the day tick sends it back, and the fighter exchange is 1:1 for a Merchant Cruiser.

- Soak fix (MASTER_PLAN DAY-g stall): with turn regen live, `_is_day_done` treats a seat short of a warp as done until its turns pool back. Before, a seat offered one returned turn spent it on a wait, and every code bot waited out each day from day 2.

## Day length and the shipyard (NOTE 60, v311-daylen-and-yard-v1)

- Day length: one value, `K.TURN_REGEN_DAY_SECONDS` (default 86,400). A game sets it with the `TW2K_TURN_REGEN_DAY_SECONDS` env, `tw2k serve --day-seconds N`, or the `GameConfig.turn_regen_day_seconds` field (also `turn_regen_day_seconds` in the `/control/restart` body). `K.parse_day_seconds` accepts 10 to 604,800 seconds and refuses anything else with "day length must be ..." (the CLI exits 2, restart answers 400). `MatchRunner._apply_day_length` sets it at game start, logs "turn regen day length N s (game setting/default)", and puts the old value back when the game ends. The roll gap, the trickle (`refresh_offline_turns`) and the planets.py day math all read it. Unset, the field is left out of the stored config, so old saves and dumps are byte-identical.
- No day-2 stall: under the v3.11 clock (`live_pace` and `starting_package_live` and `turn_regen_live`) the day rolls on the clock. Day 1 starts when the game starts, and each day lasts the day length whoever still has turns. The trickle keeps paying every scheduler pass, and the pass after a clock roll is 0.05 s (the old 1 s pause was longer than a turn on a short day). Legacy and the old live-pace path are unchanged.
- The harness observation gains `turn_clock` when turn regen is live: `server_now`, `day_seconds`, `turns_per_hour`, `seconds_per_turn`, `next_turn_at` / `next_turn_in_s` (null with a full allowance) and `next_day_at` / `next_day_in_s`, all from the server. The redesign cockpit uses it for the out-of-turns line ("No turns left. Next turn in about 9 s (7:57:43 PM). Day 2 starts at 8:07:30 PM.") and the day-roll line ("Day 2. Turns come back about 360 an hour; you have 0 of 60."). Without it the cockpit keeps the old lines.
- Shipyard: `yard_stats_on()` (`YARD_STATS_MODE`, row 63) adds `stats_by` to the buy_ship `ship_class` params: the name, cost, trade-in, holds of max holds, fighters, shields, turns per warp, odds, photons and TransWarp of every hull, for the roster in play. The redesign yard lists every hull with its price, greys the ones the seat cannot buy with the reason, and paints the chosen hull from `stats_by`. The cockpit's `HULL` table is kept only as the fallback when `stats_by` is missing.

## Soak

`docs/playtests/v311-profile-v1/README.md`: seed 250925, 10 days, port 8020, rejected 0 and exceptions 0 on every seat, 2,253 regen turns per seat, taxes 5,384 / 16,096 / 0 / 0, all citadels L0 (the bots have no citadel step), and the day-2 stall found and fixed.

## Buying-port anchors (NOTE 69, v311-port-buy-price-v1)

D25-1 (seed 41) showed day-1 buy quotes under the profile at fuel 51-87, organics 97-169, equipment 134-241 (StarDock fuel 86, equipment 185). Live v3.34b day 1 is fuel 34.9-40.65, organics 62-75, equipment 100.7-105. The cause is the two slices reading "full" the opposite way. `port_price_live()` hits `PORT_PRICE_LIVE_BUY_FULL` (`38` / `73` / `102`) only when `current / maximum` is 1, because it divides by `PORT_PRICE_BUY_FULL_MULT` (0.75). `port_stock_fidelity_live()` opens a buying port at current 0, so the same formula quotes `1.45 / 0.75`, about 1.93 times the anchor. MCIC from -100 to -1 then spreads that into the D25-1 ranges. The legacy path (anchor switch off, `PORT_PRICE_MODE` live) still does this, and the tests pin it.

`PORT_BUY_PRICE_ANCHOR_MODE` stays `"legacy"`. The profile turns `port_buy_price_anchor_on()` on without writing the stored flag. With it on, remaining demand prices the buy: a hungry port (current 0) pays the anchor times MCIC times experience, and `PORT_BUY_FILL_EASE` (0.25) eases the quote as the hold fills. From 51% remaining demand to 37% the quote drops about 4% (live StarDock equipment 105 to about 100.8). StarDock's buy rows use that same curve. The sell side still hits the full-port screen anchors (fuel 16, organics 35, equipment 36 at MCIC 50) and was left alone. The haggle window still reads the listed quote.

## Universe and planet gaps (NOTE 78, v311-universe-planet-gaps-v1)

Five switches, stored default `"legacy"`. The profile turns the helpers on and does not write the stored flags. Rows 83 and 84 stay free for NOTE 75.

- Treasury. `planet_treasury_cap()` is 10,000,000 until `treasury_cap_live()`. Then it is the S1 figure 999,999,999,999,999. Interest, the deposit handler, the legal deposit room and the redesign cockpit room line ("Room N of CAP cr") all read that helper. The room and capacity keys are added to `deposit_treasury` only while the helper is on.
- Course. Legacy still searches `PLOT_COURSE_MAX_DEPTH * 6` (60) hops, and the rules line still says 10. Live refuses a shortest path longer than 45 hops with "plotted course is longer than 45 hops". The 45 is marked UNVERIFIED for 3.11. Source: Big_Bang.html option B.
- Densities. Live generation still draws the clone ports and planets on the main rng, records the Class 0 sectors that layout would pick, then replaces the fill from a side rng: about 40% ports, up to 20% planets, and no decorative Fed ports in sectors 2-10. StarDock stays sector 1. Terra's pool is unchanged. Class 0 is installed in the sectors the clone layout chose, so a density-only flip does not move Alpha Centauri or Rylos. A one-way flip can, because the lanes moved.
- One-way share. `one_way_fraction_for` returns 0.03 only when the helper is on and `one_way_fraction` was not set on the game config. An explicit setting, including 0.15, is kept.
- Detonator. `atomic_detonator_live()` makes `atomic_mines_sold()` false. The port-nuke mine is not sold and deploy is refused. The detonator path is unchanged: colonists first (a detonator set while colonists remain destroys the ship; `planet_destroy` clears them), then the planet. `ATOMIC_MINES_PORT_NUKE` stays True.
