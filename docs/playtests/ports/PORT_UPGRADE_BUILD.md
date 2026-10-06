# Port upgrade and build

`PORT_UPGRADE_MODE` `tw2002` | `legacy`. Legacy is the engine before this slice: no `port_upgrade`, no `port_build`, no construction day tick, no prompt line.

Letter codes, not repo class numbers. The repo's class 1 is BSS; TW's class 1 is BBS.

## Rules

| # | Rule | Mark | Constant | Test |
| --- | --- | --- | --- | --- |
| pu1 | `port_upgrade {commodity, units}` only in a sector that has a port | CONFIRMED EIS | — | `test_pu1_offered_only_at_a_port` |
| pu2 | Commodity ports only. StarDock and class 0 are not upgradable | UNVERIFIED | `PORT_UPGRADE_SPECIAL` False | `test_pu2_specials_refused` |
| pu3 | Any of the three commodities, buy or sell | CONFIRMED EIS | — | `test_pu3_any_commodity` |
| pu4 | Unit cost 250 / 500 / 900 | CONFIRMED CF, IAGO, CE2 | `PORT_UPGRADE_UNIT_COST` | `test_pu4_unit_cost` |
| pu5 | One unit is +1 productivity and +10 holds | CONFIRMED CE2 | `PORT_UPGRADE_HOLDS_PER_UNIT` 10 | `test_pu5_holds_and_productivity` |
| pu6 | Cap 32,760 holds (TWGS). Gold 65,530 is the alt | SOURCE-CONFLICT | `PORT_UPGRADE_MAX_HOLDS` 32760 | `test_pu6_cap` |
| pu7 | Units past the cap or the credits are refused, not clipped | DERIVED | — | `test_pu7_refuses_over_room` |
| pu8 | Credits leave the economy. They are not added to the port | UNVERIFIED | `PORT_UPGRADE_CREDITS_TO_PORT` False | `test_pu8_credits_are_a_sink` |
| pu9 | Exp 0.1 / 0.2 / 0.3 and align 0.05 / 0.1 / 0.15, always positive | CONFIRMED CF | `PORT_UPGRADE_EXP_PER_UNIT`, `PORT_UPGRADE_ALIGN_PER_UNIT` | `test_pu9_exp_align` |
| pu10 | Fractional exp and align carry on the player | UNVERIFIED | `PORT_UPGRADE_FRACTION` carry | `test_pu10_carry` |
| pu11 | Capacity grows. Current stock does not | CONFIRMED CE2 | — | `test_pu11_stock_unchanged` |
| pu12 | No planet is required to upgrade | SOURCE-CONFLICT | `PORT_UPGRADE_NEEDS_PLANET` False | `test_pu12_no_planet` |
| pu13 | A port under construction cannot be upgraded | CONFIRMED REV | — | `test_pu13_construction_refuses_upgrade` |
| pu14 | Turn cost follows the port visit (1 then 0) | UNVERIFIED | `PORT_UPGRADE_TURN_COST` visit | `test_pu14_visit_turn` |
| pu15 | Landed, pod, bust, and a dead trader are refused | UNVERIFIED | `PORT_UPGRADE_BUST_BLOCKS` True | `test_pu15_guards` |
| pu16 | `port_build` only in a sector with no port and no radiation | CONFIRMED EIS | — | `test_pu16_empty_sector` |
| pu17 | Materials come from the trader's planet or his corp's | SOURCE-CONFLICT | `PORT_BUILD_NEEDS_PLANET` True, `PORT_BUILD_PLANET_WHO` owner_or_corp | `test_pu17_planet` |
| pu18 | Classes BBS BSB SBB SSB SBS BSS SSS BBB. SSS exists only for built ports | DERIVED | `PORT_BUILD_ALLOW_SSS` True | `test_pu18_classes` |
| pu19 | Credits paid up front, no refund | UNVERIFIED | `PORT_BUILD_COST` | `test_pu19_cost` |
| pu20 | Days 6, 7, 8, 5, 4, 3, 2, 10 | CONFIRMED IAGO + CF | `PORT_BUILD_DAYS` | `test_pu20_days` |
| pu21 | Daily ore / organics / equipment by class | UNVERIFIED | `PORT_BUILD_DAILY_MATERIALS` | `test_pu21_materials` |
| pu22 | A short day pauses. Nothing is taken | UNVERIFIED | `PORT_BUILD_STALL` pause | `test_pu22_stall` |
| pu23 | Under construction the port does not trade, rob, steal, planet-trade, or upgrade | UNVERIFIED | `PORT_BUILD_DOCKS_OPEN` False | `test_pu23_docks_closed` |
| pu24 | Opens at productivity 10, maximum 100, MCIC 50 / -60 | UNVERIFIED start stock and MCIC | `PORT_BUILD_START_PRODUCTIVITY` 10 | `test_pu24_opens` |
| pu25 | Creation exp and align on completion, whatever the alignment | CONFIRMED CF values | `PORT_BUILD_REWARD`, `PORT_BUILD_REWARD_WHEN` complete | `test_pu25_reward` |
| pu26 | Cap is the bang count times 100/95. A cleared destruction frees a slot | DERIVED mapping | `PORT_BUILD_INITIAL_BUILT_PCT` 95 | `test_pu26_cap` |
| pu27 | Radiation lasts 1 day. FedSpace and StarDock never take a build | SOURCE-CONFLICT | `PORT_BUILD_RADIATION_DAYS` 1, `PORT_BUILD_FEDSPACE` False | `test_pu27_radiation` |
| pu28 | Bots upgrade a buying port when a held planet's lot does not fit | DERIVED | `BOT_PORT_UPGRADE_POLICY` planet_room | `test_pu28_bot_upgrade` |
| pu29 | Bots do not order new ports | DERIVED | `BOT_PORT_BUILD_POLICY` off | `test_pu29_bot_build_off` |
| pu30 | One prompt line, only when the mode is on | DERIVED | — | `test_pu30_prompt` |

## Source conflicts

- pu6: TWGS and MBBS cap holds at 32,760. REV Gold says 65,530. TWGS wins.
- pu12: IAGO v1.03d says an upgrade needs a planet. EIS and CE1 do not. TWGS wins.
- pu17: EIS requires a planet to start a build. IAGO v1.03d does not for the order. TWGS wins.
- pu27: TWGS radiation is 1 day. IAGO describes 14. TWGS wins.

## Deliberate differences

Capacity and productivity are separate fields here. An upgrade raises both. One commodity per action. Upgrade credits are a sink. A port under construction does not trade. Built ports have no owner. SSS exists only for ports this slice builds.
