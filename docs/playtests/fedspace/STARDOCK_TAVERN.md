# Lost Trader's Tavern and the Underground

Slice 62. TWGS 3.11 is the default. MBBS breaks a tie. `TAVERN_MODE` legacy does not write the dock log, the tavern block, or any of these verbs.

## Not built

Tri-Cron (the jackpot game). Underground name change. The Singles Bar. The Library. The Cineplex. Illegal goods. Live bar chat (the conversation table holds it). Prices do not grow with the date.

## Decisions

D1 password is seeded from the game seed (not the published TWGS line). D2 alignment ceiling 199. D3 wrong passwords: 4th mugged, 5th experience halved, 6th murdered. D4 Tri-Cron unbuilt. D5 name change unbuilt. D6 trace 3,000, password 2,000, drink and food 20, curse 1 turn. D7 code bots do not use the Tavern. D8 free-text boards stay on for LLM seats, shown as quoted data.

## Rules

| Id | Rule | Tag | Constant | Test |
| --- | --- | --- | --- | --- |
| tv1 | Mode tw2002 or legacy | OURS | `TAVERN_MODE` | `test_tv1_legacy_hides_the_tavern` |
| tv2 | StarDock, alive, aboard, not landed. 0 turns except the curse | CONFIRMED / DERIVED | `TAVERN_TURN_COST` 0 | `test_tv2_guard` |
| tv3 | One announcement, 100 credits, replaces the last | CONFIRMED | `TAVERN_ANNOUNCE_COST` 100, `TAVERN_TEXT_MAX` 160, `TAVERN_ANNOUNCE_SIGNED` | `test_tv3_announcement` |
| tv4 | Conversation, last 20 kept, last 10 shown | CONFIRMED / OURS | `TAVERN_TALK_COST` 0, `TAVERN_CONVERSATION_KEEP` 20, `TAVERN_CONVERSATION_SHOW` 10 | `test_tv4_conversation` |
| tv5 | Anonymous graffiti, last 10 kept, last 5 shown | CONFIRMED / OURS | `TAVERN_GRAFFITI_COST` 0, `TAVERN_WALL_KEEP` 10, `TAVERN_WALL_SHOW` 5 | `test_tv5_graffiti_has_no_author` |
| tv6 | Drink or food, 20 credits, no effect, flat prices | UNVERIFIED | `TAVERN_DRINK_COST` 20, `TAVERN_FOOD_COST` 20, `TAVERN_PRICE_SCALING` flat | `test_tv6_drink_and_food` |
| tv7 | Grimy topics, else a free shrug | CONFIRMED | `GRIMY_TOPICS` | `test_tv7_shrug` |
| tv8 | Trace names one port the current ship docked at | SOURCE-CONFLICT | `GRIMY_TRACE_PORTS` 1, `GRIMY_TRACE_COST` 3000, `GRIMY_TRACE_PICK` hashed, `GRIMY_CHARGE_ON_MISS` False, `GRIMY_TRACE_LIES` False | `test_tv8_trace_one_port` |
| tv9 | Dock log on the current hull, max 10, new hull empty | DERIVED | `GRIMY_DOCK_LOG_MAX` 10, `GRIMY_DOCK_ACTIONS` | `test_tv9_dock_log` |
| tv10 | Password from the seed, 2,000 credits, once | OURS / UNVERIFIED | `UG_PASSWORD_SOURCE` seeded, `GRIMY_PASSWORD_COST` 2000 | `test_tv10_password` |
| tv11 | Tri-Cron tip is the fixed lie "2-3-1" | CONFIRMED | — | `test_tv11_tricron_tip` |
| tv12 | Lore lines, no hidden facts | OURS | `GRIMY_LORE` | `test_tv12_lore` |
| tv13 | Curse −1/−1 once a day, 1 turn | SOURCE-CONFLICT | `GRIMY_CURSES_PER_DAY` 1, `GRIMY_CURSE_TURNS` 1, `GRIMY_RUDE_MARKUP_PCT` 0 | `test_tv13_curse_once` |
| tv14 | Enter at alignment 199 or lower for the rest of the day | SOURCE-CONFLICT | `UG_MAX_ALIGNMENT` 199, `UG_PASSWORD_MATCH` loose, `UG_VERB_VISIBILITY` known | `test_tv14_entry` |
| tv15 | 4th mug, 5th half experience, 6th murder, counter resets next day | SOURCE-CONFLICT | `UG_MUG_AT` 4, `UG_EXP_HALVE_AT` 5, `UG_MURDER_AT` 6, `UG_MURDER_POD` False, `UG_MURDER_COUNTS_DEATH` True | `test_tv15_wrong_password_ladder` |
| tv16 | Hit contract, 1 alignment per 250 credits, cash on hand, not the police list | CONFIRMED | `UG_CONTRACT_MIN` 1000, `UG_CREDITS_PER_ALIGN` 250, `UG_CONTRACT_SELF` True | `test_tv16_contract` |
| tv17 | Real ship destroyed by a player pays the killer. A pod pays nothing | UNVERIFIED | `UG_CONTRACT_PAYOUT_ON` ship_destroyed, `UG_CONTRACT_ON_ELIMINATION` sink | `test_tv17_earn_and_claim` |
| tv18 | Inside, totals only, posters hidden | UNVERIFIED | `UG_SHOW_CONTRACTS` totals | `test_tv18_posters_hidden` |
| tv19 | Name change not built | CONFIRMED it exists | `UG_NAME_CHANGE` False | `test_tv19_name_change_unbuilt` |
| tv20 | Tri-Cron not built | CONFIRMED it exists | `TAVERN_TRICRON` off | `test_tv20_tricron_unbuilt` |
| tv21 | Singles Bar, Library, Cineplex, illegal goods not built | CONFIRMED they exist | — | `test_tv21_other_buildings_unbuilt` |
| tv22 | Tavern block at StarDock only | OURS | — | `test_tv22_block_only_at_stardock` |
| tv23 | Legal list matches the handler | DERIVED | — | `test_tv23_legal_matches_handler` |
| tv24 | Password, traces and contracts stay off other seats | CONFIRMED / OURS | — | `test_tv24_password_stays_private` |
| tv25 | One prompt paragraph, numbers from K | OURS | — | `test_tv25_prompt_paragraph` |
| tv26 | Code bots do not use the Tavern | OURS | `BOT_TAVERN_POLICY` off | `test_tv26_bots_skip_the_tavern` |
| tv27 | No random draw | OURS | — | `test_tv27_no_rng` |
| tv28 | Save and load, omitted at defaults | OURS | — | `test_tv28_save_load` |
| tv29 | Attempts and the curse are day stamps | CONFIRMED | — | `test_tv29_day_stamp` |
| tv30 | An eliminated trader is not a target, and the pending pool sinks | DERIVED | — | `test_tv30_elimination` |
| tv31 | This file, the gap map, and the police cross-reference | OURS | — | — |
| tv32 | A legal action is accepted | OURS | — | `test_tv23_legal_matches_handler` |

## Source conflicts

tv8 `GRIMY_TRACE_PORTS` 1 (v3 reports one port) against the older "some ports". tv13 `GRIMY_CURSES_PER_DAY` 1 (v3 daily flag) against unlimited macros. tv14 `UG_MAX_ALIGNMENT` 199 (TWGS) against 100 (MBBS). tv15 the ladder 4 / 5 / 6 (MBBS sequence, and TWFAQ's 6th kill).

## Unverified

`TAVERN_TURN_COST`, `TAVERN_TEXT_MAX`, `TAVERN_ANNOUNCE_SIGNED`, `TAVERN_TALK_COST`, `TAVERN_GRAFFITI_COST`, `TAVERN_DRINK_COST`, `TAVERN_FOOD_COST`, `TAVERN_PRICE_SCALING`, `GRIMY_TRACE_COST`, `GRIMY_TRACE_PICK`, `GRIMY_CHARGE_ON_MISS`, `GRIMY_TRACE_LIES`, `GRIMY_DOCK_LOG_MAX`, `GRIMY_DOCK_ACTIONS`, `GRIMY_PASSWORD_COST`, `GRIMY_CURSE_TURNS`, `GRIMY_RUDE_MARKUP_PCT`, `UG_PASSWORD_MATCH`, `UG_MURDER_POD`, `UG_MURDER_COUNTS_DEATH`, `UG_CONTRACT_MIN`, `UG_CONTRACT_PAYOUT_ON`, `UG_CONTRACT_ON_ELIMINATION`, `UG_SHOW_CONTRACTS`.

## Ours

`UG_PASSWORD_SOURCE` seeded. `UG_VERB_VISIBILITY` known. `TAVERN_CONVERSATION_KEEP` 20 and `SHOW` 10. `TAVERN_WALL_KEEP` 10 and `SHOW` 5. `UG_NAME_CHANGE` false. `TAVERN_TRICRON` off. `BOT_TAVERN_POLICY` off.

## Planted bugs

| Bug | Test |
| --- | --- |
| pb1 a Tavern verb is legal away from StarDock | `test_tv2_guard` |
| pb2 the announcement is free, or two notices stay up | `test_tv3_announcement` |
| pb3 announcement text is not capped | `test_pb3_announcement_capped` |
| pb4 a graffiti event names the author | `test_tv5_graffiti_has_no_author` |
| pb5 the conversation grows past 20 | `test_pb5_conversation_capped` |
| pb6 a trace returns the current sector | `test_tv8_trace_one_port` |
| pb7 a trace returns every port | `test_tv8_trace_one_port` |
| pb8 a trace charges when the hull never docked | `test_tv8_miss_is_free` |
| pb9 the trace draw uses universe.rng | `test_tv27_no_rng` |
| pb10 the dock log is written under legacy, or kept on a new hull | `test_tv9_dock_log` |
| pb11 the password is in another seat's observation or a public event | `test_tv24_password_stays_private` |
| pb12 the password match is case-sensitive | `test_tv14_entry` |
| pb13 a second curse the same day, or experience below 0 | `test_tv13_curse_once` |
| pb14 Underground entry at alignment 200 | `test_tv14_entry` |
| pb15 the attempt counter does not reset | `test_tv29_day_stamp` |
| pb16 a mugging takes the bank | `test_tv15_wrong_password_ladder` |
| pb17 murder on the 5th try, or through the pod, or experience not zeroed | `test_tv15_wrong_password_ladder` |
| pb18 contract alignment is 1 per 1,000 | `test_tv16_contract` |
| pb19 a pod kill pays the contract | `test_tv17_earn_and_claim` |
| pb20 a killer claims without entering | `test_tv17_earn_and_claim` |
| pb21 posters are shown | `test_tv18_posters_hidden` |
| pb22 underground_enter is listed before the seat knows or has tried | `test_tv14_entry` |
| pb23 legacy shows the block or the verbs | `test_tv1_legacy_hides_the_tavern` |
| pb24 a code bot emits a Tavern verb | `test_tv26_bots_skip_the_tavern` |
| pb25 the paragraph is in the legacy prompt, or its numbers are hard-coded | `test_tv25_prompt_paragraph` |
| pb26 Underground contracts are paid by claim_reward | `test_pb26_contracts_are_not_police_rewards` |

## Matches

Not run yet.
