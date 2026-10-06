# Port upgrade and build

`PORT_UPGRADE_MODE` `tw2002` | `legacy`. Legacy is the engine before this slice: no `port_upgrade`, no `port_build`, no construction day tick, no prompt line.

Letter codes, not repo class numbers. The repo's class 1 is BSS; TW's class 1 is BBS.

## Rules

| # | Rule | Mark | Constant | Test |
| --- | --- | --- | --- | --- |
| pu1 | `port_upgrade {commodity, units}` only in a sector that has a port | CONFIRMED EIS | — | `test_pu1_offered_only_at_a_port` |
| pu2 | Commodity ports only. StarDock and class 0 are not upgradable | UNVERIFIED | `PORT_UPGRADE_SPECIAL` False | `test_pu2_specials_refused` |
| pu3 | Any of the three commodities, buy or sell | CONFIRMED EIS | — | `test_pu11_sell_stock_unchanged_and_buy_room_grows`, `test_pu14_visit_turn` |
| pu4 | Unit cost 250 / 500 / 900 | CONFIRMED CF, IAGO, CE2 | `PORT_UPGRADE_UNIT_COST` | `test_pu4_pu5_cost_holds_and_productivity` |
| pu5 | One unit is +1 productivity and +10 holds | CONFIRMED CE2 | `PORT_UPGRADE_HOLDS_PER_UNIT` 10 | `test_pu4_pu5_cost_holds_and_productivity` |
| pu6 | Cap 32,760 holds (TWGS). Gold 65,530 is the alt | SOURCE-CONFLICT | `PORT_UPGRADE_MAX_HOLDS` 32760 | `test_pu6_cap_and_over_room_is_refused` |
| pu7 | Units past the cap or the credits are refused, not clipped | DERIVED | — | `test_pu6_cap_and_over_room_is_refused`, `test_legal_max_units_matches_the_handler` |
| pu8 | Credits leave the economy. They are not added to the port | UNVERIFIED | `PORT_UPGRADE_CREDITS_TO_PORT` False | `test_pu4_pu5_cost_holds_and_productivity` |
| pu9 | Exp 0.1 / 0.2 / 0.3 and align 0.05 / 0.1 / 0.15, always positive | CONFIRMED CF | `PORT_UPGRADE_EXP_PER_UNIT`, `PORT_UPGRADE_ALIGN_PER_UNIT` | `test_pu9_pu10_exp_align_carry_even_when_red` |
| pu10 | Fractional exp and align carry on the player | UNVERIFIED | `PORT_UPGRADE_FRACTION` carry | `test_pu9_pu10_exp_align_carry_even_when_red` |
| pu11 | Capacity grows. Current stock does not | CONFIRMED CE2 | — | `test_pu11_sell_stock_unchanged_and_buy_room_grows` |
| pu12 | No planet is required to upgrade | SOURCE-CONFLICT | `PORT_UPGRADE_NEEDS_PLANET` False | `test_pu4_pu5_cost_holds_and_productivity` |
| pu13 | A port under construction cannot be upgraded | CONFIRMED REV | — | `test_pu23_construction_docks_are_closed` |
| pu14 | Turn cost follows the port visit (1 then 0) | UNVERIFIED | `PORT_UPGRADE_TURN_COST` visit | `test_pu14_visit_turn` |
| pu15 | Landed, pod, bust, and a dead trader are refused | UNVERIFIED | `PORT_UPGRADE_BUST_BLOCKS` True | `test_pu15_guards` |
| pu16 | `port_build` only in a sector with no port and no radiation | CONFIRMED EIS | — | `test_pu16_pu18_pu19_pu20_build_sss` |
| pu17 | Materials come from the trader's planet or his corp's | SOURCE-CONFLICT | `PORT_BUILD_NEEDS_PLANET` True, `PORT_BUILD_PLANET_WHO` owner_or_corp | `test_pu17_rival_planet_reads_like_a_missing_one` |
| pu18 | Classes BBS BSB SBB SSB SBS BSS SSS BBB. SSS exists only for built ports | DERIVED | `PORT_BUILD_ALLOW_SSS` True | `test_pu16_pu18_pu19_pu20_build_sss` |
| pu19 | Credits paid up front, no refund | UNVERIFIED | `PORT_BUILD_COST` | `test_pu16_pu18_pu19_pu20_build_sss` |
| pu20 | Days 6, 7, 8, 5, 4, 3, 2, 10 | CONFIRMED IAGO + CF | `PORT_BUILD_DAYS` | `test_pu16_pu18_pu19_pu20_build_sss` |
| pu21 | Daily ore / organics / equipment by class | UNVERIFIED | `PORT_BUILD_DAILY_MATERIALS` | `test_pu21_pu22_pu24_pu25_construction_day_tick` |
| pu22 | A short day pauses. Nothing is taken | UNVERIFIED | `PORT_BUILD_STALL` pause | `test_pu21_pu22_pu24_pu25_construction_day_tick` |
| pu23 | Under construction the port does not trade, rob, steal, planet-trade, or upgrade | UNVERIFIED | `PORT_BUILD_DOCKS_OPEN` False | `test_pu23_construction_docks_are_closed` |
| pu24 | Opens at productivity 10, maximum 100, MCIC 50 / -60 | UNVERIFIED start stock and MCIC | `PORT_BUILD_START_PRODUCTIVITY` 10 | `test_pu21_pu22_pu24_pu25_construction_day_tick` |
| pu25 | Creation exp and align on completion, whatever the alignment | CONFIRMED CF values | `PORT_BUILD_REWARD`, `PORT_BUILD_REWARD_WHEN` complete | `test_pu21_pu22_pu24_pu25_construction_day_tick` |
| pu26 | Cap is the bang count times 100/95. A cleared destruction frees a slot | DERIVED mapping | `PORT_BUILD_INITIAL_BUILT_PCT` 95 | `test_pu26_cap_frees_when_a_port_is_cleared` |
| pu27 | Radiation lasts 1 day. FedSpace and StarDock never take a build | SOURCE-CONFLICT | `PORT_BUILD_RADIATION_DAYS` 1, `PORT_BUILD_FEDSPACE` False | `test_pu27_radiation_and_fedspace` |
| pu28 | Bots upgrade a buying port when a held planet's lot does not fit | DERIVED | `BOT_PORT_UPGRADE_POLICY` planet_room | `test_pu28_bot_upgrades_a_buying_port_only` |
| pu29 | Bots do not order new ports | DERIVED | `BOT_PORT_BUILD_POLICY` off | `test_pu29_bot_does_not_build` |
| pu30 | One prompt line, only when the mode is on | DERIVED | — | `test_pu30_prompt_line_only_when_on` |

## Source conflicts

- pu6: TWGS and MBBS cap holds at 32,760. REV Gold says 65,530. TWGS wins.
- pu12: IAGO v1.03d says an upgrade needs a planet. EIS and CE1 do not. TWGS wins.
- pu17: EIS requires a planet to start a build. IAGO v1.03d does not for the order. TWGS wins.
- pu27: TWGS radiation is 1 day. IAGO describes 14. TWGS wins.

## Deliberate differences

Capacity and productivity are separate fields here. An upgrade raises both. One commodity per action. Upgrade credits are a sink. A port under construction does not trade. Built ports have no owner. SSS exists only for ports this slice builds.

## Match check

`scripts/run_scripted_match.py --seats N3,N3,N2,N2,N1,H --days 10`, Ferrengi on. `PORT_UPGRADE_MODE` legacy and tw2002. Rejected 0/0, exceptions 0, port builds 0, invariant violations 0 (no stock above 32,760). Both seeds were identical across the two modes: no seat upgraded a port.

The bot only upgrades when a held planet's organics or equipment lot is bigger than the port's room, credits stay above 50,000, and one quote of that lot beats the unit cost. These matches never met that test, so net worth did not move.

Seed 250925:

| Seat | Net worth | Planet trades | Trade credits | Exp | Align |
| --- | --- | --- | --- | --- | --- |
| N3-P1 | 745,255 | 5 | 8,982 | +1,915 | +39 |
| H-P6 | 619,312 | 0 | 0 | +2,162 | +7 |
| N2-P4 | 547,351 | 1 | 1,630 | +1,327 | +49 |
| N1-P5 | 425,700 | 2 | 7,227 | +2,398 | +29 |
| N2-P3 | 337,339 | 1 | 990 | +987 | +29 |
| N3-P2 | 246,986 | 0 | 0 | +923 | +29 |

Seed 424242: N3-P2 616,259 (1 trade, 1,512cr), N3-P1 600,421 (2 trades, 2,911cr), H-P6 504,625, N2-P3 469,904, N2-P4 397,182, N1-P5 342,336. Planet trades only on the two N3 seats. Upgrades 0.

`scripts/port_upgrade_scenario_lab.py` (the focused case the 10-day matches did not hit): 300 equipment units cost 270,000, granted +90 exp and +45 align, and raised capacity by 3,000. The same visit then sold 6,000 equipment off the planet and spent no second turn. SSS ordered on day 1, progressed on day 2, stalled on day 3 with the planet short, and opened on day 4 at productivity 10. The completion event paid +7 exp and +4 align (midnight also adds +1/+1). An order at the port cap was refused. A build on the day a port was destroyed was refused, and the same sector accepted an order the next day.

30-day headless, seed 42, 2 heuristics: finished with no crash, day 31, 72,589 events, 0 engine failures.
