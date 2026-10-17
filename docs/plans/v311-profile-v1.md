# v311-profile-v1 (COMMANDER NOTE 57)

`V311_PROFILE` is one switch in `src/tw2k/engine/constants.py`. Default `"legacy"`. Set to `"v311"`, it turns on the RULINGS_v311.md rulings for items 1-6 and every MASTER_PLAN switch marked yes ("yes", "yes, after check", "yes, Ben confirm", "yes for AI-seat games"). Nothing is flipped by default; the bank pin `9b607d3dae940c0b1a69f6d7` and the 10-day digests `24863a3d` / `98a47c8a` stay with the profile off.

It is its own switch. `TW2002_LIVE_PROFILE` stays as it is (MASTER_PLAN: "build a v3.11 profile from the yes list instead"); turning the live profile on does not turn `v311_profile()` on. The code list is `K.V311_PROFILE_HELPERS`, and `tests/test_v311_rulings_v1.py::test_profile_sets_exactly_the_documented_set` checks that this file, that dict, and the helpers agree: with only `V311_PROFILE` on, every helper below returns True and every other helper in `tests/test_tw2002_live_profile_v1.py` HELPERS returns False.

Sources: `C:\Users\sugar\tw2002_reference\RULINGS_v311.md` (s1-s7) and `C:\Users\sugar\tw2002_reference\MASTER_PLAN.md` ("Engine switches still defaulting to legacy").

## The switch set (60 helpers)

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

Mode values under the profile: `rank_display()` returns `"exp"`, `planet_value_score_mode()` returns `"experience"`, `genesis_score_fair()` and `action_result_report()` return True. Stored values stay `"legacy"`.

## Left as they are

MASTER_PLAN no, no-op, or hold, with no ruling in NOTE 57. The profile does not touch them.

| switch | MASTER_PLAN | why |
|---|---|---|
| `KILL_CASH_MODE` | hold | NOTE 57 item 7, RULINGS s1: the killer's percentage is not stated in any source. Stays legacy and is not in the profile. |
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
- Item 7 (s1): `kill_cash_held()` does not read `V311_PROFILE`.

- Soak fix (MASTER_PLAN DAY-g stall): with turn regen live, `_is_day_done` treats a seat short of a warp as done until its turns pool back. Before, a seat offered one returned turn spent it on a wait, and every code bot waited out each day from day 2.

## Soak

`docs/playtests/v311-profile-v1/README.md`: seed 250925, 10 days, port 8020, rejected 0 and exceptions 0 on every seat, 2,253 regen turns per seat, taxes 5,384 / 16,096 / 0 / 0, all citadels L0 (the bots have no citadel step), and the day-2 stall found and fixed.
