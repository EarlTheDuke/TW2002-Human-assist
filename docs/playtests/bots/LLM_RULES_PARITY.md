# LLM rules parity

`LLM_PARITY_MODE` `tw2002` | `legacy`. Legacy is the prompt and the observation text at c35b9b3. This slice does not change a game rule. It changes what an LLM seat is told so the text matches the engine.

Sources: the EIS menus, the MBBS FlagShip line, Iago on who buys a FlagShip, and the engine docs for corps, the bank, port upgrades, corp ships, aliens, and bots. TWGS 3.11 is the default.

## Rules

| # | Rule | Mark | Constant | Test |
| --- | --- | --- | --- | --- |
| lp1 | The mode is on. Legacy prompt, observation, and user turn stay byte-identical | OURS | `LLM_PARITY_MODE` tw2002 | `test_lp1_mode` |
| lp2 | Mode sentences are built from constants at call time | OURS | — | `test_lp2_source` |
| lp3 | Corp create is free in any sector. The FlagShip row says C.E.O. only when that rule is on | CONFIRMED | `CORP_CREATE_COST`, `CFS_CEO_RULE` | `test_lp3_corp` |
| lp4 | Deposit, withdraw, and a shared treasury are not advertised while the treasury is off | CONFIRMED | `CORP_TREASURY` off | `test_lp4_treasury` |
| lp5 | Corp hints use the real cost and do not copy a password into the hint | CONFIRMED | `LLM_HINT_CORP_MIN_CREDITS` 50000 | `test_lp5_hints` |
| lp6 | `plot_course` is documented with `execute` true | CONFIRMED | `PLOT_COURSE_MAX_DEPTH` | `test_lp6_plot` |
| lp7 | The StarDock hint names that same plot syntax | OURS | — | `test_lp7_stardock` |
| lp8 | Bank deposit, withdraw, and transfer are named with their arguments | CONFIRMED | `BANK_MAX_BALANCE` | `test_lp8_bank` |
| lp9 | Port upgrade and port build are named with their arguments | CONFIRMED | — | `test_lp9_ports` |
| lp10 | Corp password, invite, join, leave, drop, and transfer are named | CONFIRMED | `CORP_BREAKIN_PER_DAY` | `test_lp10_corp_verbs` |
| lp11 | Corp-ship personal, corporate, and password verbs are named | CONFIRMED | — | `test_lp11_corpship` |
| lp12 | An alien attack target uses the format the engine ships | CONFIRMED | — | `test_lp12_alien` |
| lp13 | Every legal verb in the fixture set is named, with its required arguments | OURS | `LLM_UNDOCUMENTED_VERBS` empty | `test_lp13_coverage` |
| lp14 | The compact legal list adds short argument hints. No password. Lists cap at 6 | OURS | `LLM_LEGAL_HINTS` args, `LLM_LEGAL_HINT_MAX_CHOICES` 6 | `test_lp14_hints` |
| lp15 | Every JSON example in the parity prompt is legal when that verb is legal | OURS | — | `test_lp15_examples` |
| lp16 | Acceptance requires the handler arguments for the new verbs | OURS | — | `test_lp16_required` |
| lp17 | The minimal prompt gets the same verb lines and stays shorter than the full prompt | OURS | — | `test_lp17_minimal` |
| lp18 | The full prompt grows at most 8 percent. Observation median grows at most 10 percent | OURS | `LLM_PROMPT_GROWTH_MAX_PCT` 8, `LLM_OBS_GROWTH_MAX_PCT` 10 | `test_lp18_size` |
| lp19 | A rule sentence is not repeated between the base text and a mode note | OURS | — | `test_lp19_once` |
| lp20 | Every base line that names a mode cost or verb is rendered from the constants or listed as mode-neutral | OURS | — | `test_lp20_sweep` |
| lp21 | Route and new-day notices keep their behaviour. Legacy with both notices off is byte-identical | OURS | `LLM_ROUTE_NOTICE`, `LLM_NEW_DAY_GOAL_NOTICE` | `test_lp21_notices` |
| lp22 | Hints do not add fogged facts, and they do not print a corp password | CONFIRMED | — | `test_lp22_fog` |
| lp23 | Parity on and off play the same scripted actions | OURS | — | `test_lp23_stream` |
| lp24 | A block is shown only while its mode is on | OURS | — | `test_lp24_gating` |
| lp25 | The text depends only on the constants and the observation | OURS | — | `test_lp25_determinism` |
| lp26 | An offline text reader uses only the rendered prompt | OURS | — | `test_lp26_reader` |
| lp27 | The fixture lab writes prompt, observation, and the contradiction checklist | OURS | — | `test_lp27_lab` |
| lp28 | A live paid smoke is not run unless Ben asks | OURS | — | — |
| lp29 | The legacy pin hashes the prompt and a 3-day scripted run with the notices off | OURS | — | `test_llm_parity_legacy_is_unchanged` |
| lp30 | GAP 15 names this slice | OURS | — | `test_lp30_docs` |

## Constants

`LLM_PARITY_MODE` tw2002. `LLM_HINT_CORP_MIN_CREDITS` 50000. `LLM_LEGAL_HINTS` args. `LLM_LEGAL_HINT_MAX_CHOICES` 6. `LLM_PROMPT_GROWTH_MAX_PCT` 8. `LLM_OBS_GROWTH_MAX_PCT` 10. `LLM_UNDOCUMENTED_VERBS` empty. `LLM_SELL_FIRST` on. `LLM_PLANET_NUDGE_MODE` tw2002. `LLM_PLANET_NUDGE_CREDITS` 50000.

`LLM_LEGAL_HINT_KEYS`: `target`, `ship_class`, `item`, `commodity`, `direction`, `ticker`, `corps`, `partners`, `planet_id`, `qty`, `units`, `amount`, `mode`, `kind`, `port_class`, `to_player`, `side`, `ownership`, `execute`. `password` is not in that list.

## Legacy pin

Recorded on c35b9b3 before `LLM_PARITY_MODE` exists. 3-day N3,N2,N1,H seed 250925. Golden `9b607d3dae940c0b1a69f6d7`. The flip list starts with `LLM_PLANET_NUDGE_MODE` and `LLM_PARITY_MODE` and includes the newer modes. Both notice flags are False. No paid API call.

## Verb inventory

Handler args are the keys the handler reads. `REQUIRED_ARGS` is what `seat_acceptance` demands before the engine sees the action. A base verb is in the legal list with no newer mode switch.

| Verb | Mode | Handler args | REQUIRED_ARGS | Named in the parity prompt |
| --- | --- | --- | --- | --- |
| `warp` | base | target | target | yes |
| `trade` | base | commodity, qty, side, unit_price | commodity, qty, side | yes |
| `scan` | base | tier | - | yes |
| `deploy_fighters` | base | qty, mode | qty, mode | yes |
| `deploy_mines` | base | qty, kind | kind, qty | yes |
| `attack` | base | target | target | yes |
| `land_planet` | base | planet_id | planet_id | yes |
| `liftoff` | base | - | - | yes |
| `assign_colonists` | base | planet_id, qty, from, to | planet_id, from, to, qty | yes |
| `load_planet_cargo` | base | planet_id, commodity, qty | planet_id, commodity, qty | yes |
| `dump_planet_cargo` | base | planet_id, commodity, qty | planet_id, commodity, qty | yes |
| `build_citadel` | base | planet_id | planet_id | yes |
| `deploy_genesis` | base | - | - | yes |
| `claim_planet` | base | - | - | yes |
| `plot_course` | base | target, execute | target, execute | yes |
| `photon_missile` | HARDWARE_MODE | target | target | yes |
| `cloak` | HARDWARE_MODE | - | - | yes |
| `fire_disruptor` | HARDWARE_MODE | target | target | yes |
| `remove_limpet` | HARDWARE_MODE | - | - | yes |
| `launch_beacon` | HARDWARE_MODE | message | message | yes |
| `terra_colonists` | HARDWARE_MODE | mode, qty | mode, qty | yes |
| `deploy_atomic` | HARDWARE_MODE | planet_id | planet_id | yes |
| `query_limpets` | HARDWARE_MODE | - | - | yes |
| `probe` | HARDWARE_MODE | target | target | yes |
| `corp_deposit` | CORP_TREASURY (line hidden while off) | amount | amount | no |
| `corp_withdraw` | CORP_TREASURY (line hidden while off) | amount | amount | no |
| `corp_memo` | base | message | message | yes |
| `propose_alliance` | base | target, terms | target | yes |
| `accept_alliance` | base | alliance_id | alliance_id | yes |
| `break_alliance` | base | alliance_id | alliance_id | yes |
| `buy_ship` | base | ship_class | ship_class | yes |
| `buy_equip` | base | item, qty | item, qty | yes |
| `corp_create` | base | ticker, name | ticker | yes |
| `corp_invite` | base | target | target | yes |
| `corp_join` | base | ticker | ticker | yes |
| `corp_leave` | base | - | - | yes |
| `corp_set_password` | CORP_MODE | password | password | yes |
| `corp_drop` | CORP_MODE | target | target | yes |
| `corp_transfer` | CORP_MODE | direction, target, item, qty | target, item, qty, direction | yes |
| `hail` | base | target, message | target, message | yes |
| `broadcast` | base | message | message | yes |
| `wait` | base | - | - | yes |
| `deposit_planet_defense` | base | planet_id | - | yes |
| `withdraw_planet_defense` | base | planet_id | - | yes |
| `set_military_reaction` | base | planet_id, pct | - | yes |
| `deposit_treasury` | base | - | - | yes |
| `withdraw_treasury` | base | - | - | yes |
| `set_quasar_sector` | base | planet_id, pct | - | yes |
| `set_quasar_atm` | base | planet_id, pct | - | yes |
| `planet_transwarp` | base | planet_id, dest_sector | - | yes |
| `planet_buy_transporter` | base | planet_id | - | yes |
| `planet_transport` | base | planet_id, dest_sector | - | yes |
| `planet_destroy` | base | planet_id | - | yes |
| `recall_deployed` | base | what, qty, kind | - | yes |
| `surrender` | base | - | - | yes |
| `retreat` | base | - | - | yes |
| `pay_toll` | base | - | - | yes |
| `rob` | ROB_MODE | amount | - | yes |
| `steal` | ROB_MODE | commodity, qty | - | yes |
| `apply_commission` | FED_MODE | - | - | yes |
| `post_reward` | FED_MODE | target_id, target, amount | - | yes |
| `claim_reward` | FED_MODE | - | - | yes |
| `ship_transwarp` | SHIP_TW_MODE | sector_id, target | - | yes |
| `sell_ship` | FLEET_MODE | ship_id | - | yes |
| `ship_transport` | FLEET_MODE | ship_id | - | yes |
| `tow_engage` | TOW_MODE | target, password | - | yes |
| `tow_release` | TOW_MODE | - | - | yes |
| `planet_trade` | PLANET_TRADE_MODE | planet_id, commodity, qty, offer | planet_id, commodity, qty | yes |
| `ship_set_corporate` | CORPSHIP_MODE | - | - | yes |
| `ship_set_personal` | CORPSHIP_MODE | - | - | yes |
| `ship_set_password` | CORPSHIP_MODE | password | password | yes |
| `port_upgrade` | PORT_UPGRADE_MODE | commodity, units | commodity, units | yes |
| `port_build` | PORT_UPGRADE_MODE | port_class, planet_id, name | planet_id, port_class | yes |
| `bank_deposit` | BANK_MODE | amount | amount | yes |
| `bank_withdraw` | BANK_MODE | amount | amount | yes |
| `bank_transfer` | BANK_MODE | to_player, amount | to_player, amount | yes |

74 of 76 verbs are named in the parity prompt. `corp_deposit` and `corp_withdraw` stay out while `CORP_TREASURY` is off. They remain in `REQUIRED_ARGS` for a treasury-on game. `LLM_UNDOCUMENTED_VERBS` is empty.

## Line inventory

Each row is a base-prompt line the parity text rewrites. The number comes from the constant, not a literal.

| Old line | Parity line | Constant |
| --- | --- | --- |
| StarDock is where `buy_ship`, `buy_equip`, and `corp_create` work | StarDock is where `buy_ship` and `buy_equip` work. `corp_create` is free in any sector | `CORP_CREATE_COST` 0 |
| corporate_flagship (CORP MEMBER ONLY) | corporate_flagship (C.E.O. ONLY) | `CFS_CEO_RULE` purchase, and only while corp bots are on |
| shared treasury makes ferrying trivial | a mate in the same sector can hand you credits | `CORP_TREASURY` off |
| `plot_course {"target":<sector_id>}` up to 10 warps | `plot_course {"target":<sector_id>,"execute":true}`. `execute` false only previews | `PLOT_COURSE_MAX_DEPTH` |
| `corp_create` 500k cr at StarDock | free in any sector, then `corp_set_password` | `CORP_CREATE_COST`, `CORPSHIP_PASSWORD_MAX_LEN` |
| `corp_join {"ticker":"XYZ"}` | `corp_join` with ticker and password. One wrong password a day | `CORP_BREAKIN_PER_DAY` |
| `corp_deposit` / `corp_withdraw` and the equal treasury share | those lines are gone | `CORP_TREASURY` off |
| Corp benefits: shared treasury, FlagShip for members | mates do not shoot each other; the member pays for a citadel; only the C.E.O. buys the FlagShip | `CORP_TREASURY` off, `CFS_CEO_RULE` |
| Corp list includes deposit and withdraw | list is create, set_password, invite, join, leave, drop, transfer, memo | `CORP_TREASURY` off |
| CORPORATE SHIPS note with no call shape | `ship_set_corporate {}`, `ship_set_personal {}`, `ship_set_password` length 1 to 8 | `CORPSHIP_PASSWORD_MAX_LEN` |
| Port note with no call shape | `port_upgrade` commodity and units, prices 250 / 500 / 900, 10 holds | `PORT_UPGRADE_UNIT_COST`, `PORT_UPGRADE_HOLDS_PER_UNIT` |
| Bank note with no call shape | `bank_deposit`, `bank_withdraw`, `bank_transfer` at StarDock, cap 500,000 | `BANK_MAX_BALANCE` |
| Corporations cost line from the old note | free in any sector, cap 5, ownership personal or corporate, C.E.O. leaving dissolves it | `CORP_CREATE_COST` 0, `CORP_TURN_COST` 0, `CORP_MAX_MEMBERS` 5 |
| no alien attack line | `attack {"target":"alien:<n>","qty":N}`, alignment share 0.5 | `ALIEN_KILL_ALIGN_SHARE` |

## Fixture lab (seed 60, 500 sectors)

`scripts/llm_prompt_fixture_lab.py`. Checklist PASS on this tip. Full prompt 41450 chars legacy, 41783 parity (0.80%, under 8%). Chars/4 is about 10,363 tokens legacy and 10,446 parity. Minimal prompt 15663 legacy, 16218 parity, and shorter than full. Observation median growth 3.8% (under 10%).

| Fixture | Legacy obs | Parity obs | Growth |
| --- | ---: | ---: | ---: |
| f1 ten hops from StarDock, 250,000 credits | 7917 | 8220 | 3.8% |
| f2 at StarDock, 300,000 credits | 9207 | 9805 | 6.5% |
| f3 at StarDock, over the tax threshold | 9156 | 9754 | 6.5% |
| f4 invite in the inbox | 9717 | 9777 | 0.6% |
| f5 C.E.O. with a mate in the sector | 10286 | 10580 | 2.9% |
| f6 port, owned planet, upgrade affordable | 9812 | 10256 | 4.5% |
| f7 alien in the sector | 8327 | 8467 | 1.7% |
| f8 the f1 seat with the minimal prompt | 7122 | 7231 | 1.5% |

Parity checklist: no `500k cr at StarDock`, no `corp_deposit`, no `corp_withdraw`, no `shared treasury`. f1 parity hint names `plot_course` execute and does not say warp back. f4 hint does not copy the password. Legacy keeps the 500k line, the warp-back hint, and a compact legal list with no `args` key.

## 10-day scripted, seed 250925

Seats N3,N3,N2,N2,N1,H. Parity on and parity off wrote the same table and the same action digest `cd91bf36`. Rejected 0/0. Exceptions 0. Wall about 327s on and 372s off.

| Seat | Net worth | Ship | Deaths |
| --- | ---: | --- | ---: |
| N3-P1 | 648,074 | cargotran | 0 |
| N2-P3 | 314,875 | cargotran | 0 |
| N1-P5 | 217,288 | cargotran | 0 |
| N3-P2 | 188,773 | merchant_cruiser | 0 |
| N2-P4 | 138,940 | merchant_cruiser | 0 |
| H-P6 | 7,975 | scout_marauder | 3 |

## 10-day scripted, seed 4242

Parity on and parity off wrote the same file. Action digest `7ad15bc9`. Rejected 0/0. Exceptions 0. Wall about 259s on and 270s off.

| Seat | Net worth | Ship | Deaths |
| --- | ---: | --- | ---: |
| N1-P5 | 476,782 | merchant_cruiser | 0 |
| N2-P3 | 461,882 | cargotran | 0 |
| N3-P1 | 460,723 | cargotran | 0 |
| N3-P2 | 216,931 | cargotran | 0 |
| N2-P4 | 154,737 | merchant_cruiser | 0 |
| H-P6 | 7,975 | scout_marauder | 3 |

## Sell-first and the first planet

`LLM_SELL_FIRST` (default on) puts a SELL HERE line at the top of the turn notices when this port's bid covers the cargo's cost, and clears the short goal. Two round trips on the same pair while still holding cargo and with no trade in between show `you are looping: sell here or plot_course to a buyer`. A bid under cost, an empty hold, one trip, or a trade in the window stays quiet.

`LLM_PLANET_NUDGE_MODE` default tw2002. Legacy keeps `update only on real strategy shifts` and the old S2 line. On, the long-goal clause is dropped, S2 tells a seat with no planet to buy genesis and terra_colonists and not to wait for a credit target, and a seat with no planet, no torpedo, and at least 50,000 credits gets a FIRST PLANET notice (buy at StarDock, otherwise plot_course to sector 1). A planet owner gets neither. When buy_equip is legal the compact args list every affordable item. Code bots are unchanged.

## Planted-bug tests

Re-broke pb1 through pb26 on this tree. Each named test failed, and the source was restored.

| Bug | Test |
| --- | --- |
| pb1 minimal prompt still says 500k at StarDock | `test_pb1_minimal_prompt_drops_the_500k_line` |
| pb2 deposit and withdraw stay in the corp list | `test_pb2_treasury_off_drops_deposit_and_withdraw` |
| pb3 join hint omits the password key | `test_pb3_and_pb4_invite_hint_names_the_password_key_and_not_the_secret` |
| pb4 join hint copies the real password | `test_pb3_and_pb4_invite_hint_names_the_password_key_and_not_the_secret` |
| pb5 hint A fires at 0 credits | `test_pb5_hint_a_stays_quiet_below_the_credit_threshold` |
| pb6 plot_course omits execute | `test_pb6_plot_course_line_includes_execute` |
| pb7 StarDock hint says warp back | fixture lab f1 |
| pb8 route notice and the prompt disagree | `test_lp7_route_notice_shares_the_plot_syntax` |
| pb9 bank_transfer uses target | `test_pb9_pb10_pb11_examples_use_the_handler_names` |
| pb10 port_upgrade uses qty | `test_pb9_pb10_pb11_examples_use_the_handler_names` |
| pb11 direction is send/receive | `test_pb9_pb10_pb11_examples_use_the_handler_names` |
| pb12 text snapshots a constant at import | `test_pb12_and_pb13_numbers_follow_the_constants` |
| pb13 a literal 25000 instead of the constant | `test_pb12_and_pb13_numbers_follow_the_constants` |
| pb14 bank block while the bank is legacy | `test_lp14_bank_block_hides_when_the_bank_is_legacy` |
| pb15 FlagShip says C.E.O. only while bots are legacy | `test_lp15_flagship_row_stays_member_only_when_bots_are_legacy` |
| pb16 compact hints include a blocked verb | `test_lp14_compact_hints_cap_choices_and_skip_secrets` |
| pb17 compact hints leak the password | `test_lp14_compact_hints_cap_choices_and_skip_secrets` |
| pb18 compact hints list 40 choices | `test_lp14_compact_hints_cap_choices_and_skip_secrets` |
| pb19 legacy compact legal gains args | `test_lp14_compact_hints_cap_choices_and_skip_secrets` |
| pb20 transfer without direction passes | `test_pb20_a_transfer_without_direction_is_rejected` |
| pb21 required args reject the brain's transfer | `test_pb21_the_brain_transfer_shape_passes_acceptance` |
| pb22 alien attack format guessed | `test_pb22_alien_attack_format_matches_the_engine` |
| pb23 a duplicated long sentence | `test_pb23_parity_prompt_does_not_repeat_a_long_sentence` |
| pb24 a rival planet stock in the hint | `test_pb24_a_rival_planet_stock_stays_out_of_the_hint` |
| pb25 the legacy pin leaves the route notice on | `test_pb25_the_legacy_pin_turns_the_route_notice_off` |
| pb26 prompt growth over the budget | `test_pb26_prompt_growth_stays_inside_the_budget` |

## 30-day scripted, seed 250925

Parity on and parity off wrote the same file. Action digest `87b76392`. Rejected 0/0. Exceptions 0. Day-15 save/load identical. Corps N3P is P1+P2 and N2P is P3+P4, 12 transfers, hostile 0, corporate deployments 0. Wall 1188s on and 1225s off.

| Seat | Net worth | Ship | Deaths |
| --- | ---: | --- | ---: |
| N3-P1 | 2,059,640 | battleship | 0 |
| N2-P3 | 875,547 | scout_marauder | 15 |
| N3-P2 | 650,104 | cargotran | 0 |
| N1-P5 | 550,249 | scout_marauder | 13 |
| N2-P4 | 436,720 | scout_marauder | 1 |
| H-P6 | 7,975 | scout_marauder | 6 |

## Text reader from the f1 start, 10-day

Seats N3,N3,N2,N2,N1,R. R starts 10 hops from StarDock with 250,000 credits, outside FedSpace. Parity reaches StarDock and is in a cargotran on day 1. Legacy is still in the merchant cruiser on day 1 and never plots.

Seed 250925 parity on, digest `2dd804fa`, rejected 0/0. Reader kinds: buy_ship 6, plot_course 167, port_upgrade 55, trade 92, warp 1032, wait 3. Day 1 ship cargotran, net worth 28,035.

| Seat | Net worth | Ship | Deaths |
| --- | ---: | --- | ---: |
| N3-P1 | 809,208 | battleship | 0 |
| N3-P2 | 187,958 | merchant_cruiser | 0 |
| N1-P5 | 180,000 | scout_marauder | 1 |
| N2-P3 | 175,543 | scout_marauder | 1 |
| N2-P4 | 137,651 | merchant_cruiser | 0 |
| R-P6 | 28,003 | cargotran | 0 |

Seed 250925 parity off, digest `36ce6f78`. Reader kinds: trade 203, warp 2997, wait 9. No plot_course and no buy_ship. Day 1 still merchant_cruiser. The reader was rejected 183 times, all "Port does not have enough stock".

| Seat | Net worth | Ship | Deaths |
| --- | ---: | --- | ---: |
| N3-P1 | 546,178 | battleship | 0 |
| N2-P3 | 387,243 | cargotran | 0 |
| N3-P2 | 212,842 | merchant_cruiser | 0 |
| N1-P5 | 180,697 | scout_marauder | 1 |
| R-P6 | 180,257 | merchant_cruiser | 0 |
| N2-P4 | 123,183 | merchant_cruiser | 0 |

Seed 4242 parity on, digest `784380cf`, rejected 0/0. Reader kinds: buy_ship 6, plot_course 310, warp 2186, wait 2. Day 1 ship cargotran, net worth 41,535.

| Seat | Net worth | Ship | Deaths |
| --- | ---: | --- | ---: |
| N3-P1 | 518,830 | cargotran | 0 |
| N1-P5 | 439,773 | cargotran | 0 |
| N2-P3 | 287,890 | cargotran | 1 |
| N2-P4 | 197,475 | merchant_cruiser | 0 |
| N3-P2 | 132,105 | cargotran | 0 |
| R-P6 | 41,535 | cargotran | 0 |

Seed 4242 parity off, digest `63d9dd5c`, rejected 0/0. Reader kinds: trade 20, warp 3330, wait 9. Day 1 still merchant_cruiser, net worth 272,650.

| Seat | Net worth | Ship | Deaths |
| --- | ---: | --- | ---: |
| N3-P1 | 468,195 | battleship | 0 |
| N1-P5 | 464,312 | merchant_cruiser | 0 |
| N2-P3 | 421,439 | cargotran | 0 |
| R-P6 | 180,311 | merchant_cruiser | 0 |
| N3-P2 | 178,565 | merchant_cruiser | 0 |
| N2-P4 | 123,653 | merchant_cruiser | 0 |

The earlier FedSpace start (20,000 credits) did not buy a hull. Parity on digest `6df92949` ended at 22,650 still in a merchant cruiser. Parity off digest `5a2cc40a` ended at 42,650.

## Text reader, 30-day, seed 250925, f1 start, parity on

Digest `9d04c4a1`. Rejected 0/0. Exceptions 0. Invariant violations 0. Day-15 save/load identical. No crash. The reader was a cargotran from day 1 (net worth 28,035) and stayed there until day 24, then died once and finished in an escape pod at 0. Corps N3P is P1+P2 and N2P is P3+P4, 17 transfers, hostile 0. Reader kinds: buy_ship 6, plot_course 465, port_upgrade 55, trade 168, warp 2913, wait 35.

| Seat | Net worth | Ship | Deaths |
| --- | ---: | --- | ---: |
| N3-P1 | 2,294,843 | battleship | 0 |
| N3-P2 | 772,496 | cargotran | 0 |
| N2-P3 | 734,232 | scout_marauder | 10 |
| N2-P4 | 482,360 | cargotran | 0 |
| N1-P5 | 259,938 | scout_marauder | 12 |
| R-P6 | 0 | escape_pod | 1 |
