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

`LLM_HINT_CORP_MIN_CREDITS` 50000. `LLM_LEGAL_HINTS` args. `LLM_LEGAL_HINT_MAX_CHOICES` 6. `LLM_PROMPT_GROWTH_MAX_PCT` 8. `LLM_OBS_GROWTH_MAX_PCT` 10. `LLM_UNDOCUMENTED_VERBS` empty.

## Legacy pin

Recorded on c35b9b3 before `LLM_PARITY_MODE` exists. 3-day N3,N2,N1,H seed 250925. Golden `9b607d3dae940c0b1a69f6d7`. The flip list starts with `LLM_PARITY_MODE` and includes the newer modes. Both notice flags are False.

Verb inventory and line inventory are filled as the prompt text lands. No paid API call.

## Fixture lab (seed 60, 500 sectors)

`scripts/llm_prompt_fixture_lab.py`. Full prompt 41488 chars legacy, 41679 parity (0.46%, under 8%). Minimal prompt 15663 legacy, 16076 parity, and shorter than full. Observation median growth 3.8% (under 10%).

| Fixture | Legacy obs | Parity obs | Growth |
| --- | ---: | ---: | ---: |
| f1 ten hops from StarDock, 250,000 credits | 7900 | 8203 | 3.8% |
| f2 at StarDock, 300,000 credits | 9190 | 9678 | 5.3% |
| f3 at StarDock, over the tax threshold | 9139 | 9627 | 5.3% |
| f4 invite in the inbox | 9717 | 9777 | 0.6% |
| f5 C.E.O. with a mate in the sector | 10286 | 10580 | 2.9% |
| f6 port, owned planet, upgrade affordable | 9812 | 10256 | 4.5% |
| f7 alien in the sector | 8327 | 8467 | 1.7% |
| f8 the f1 seat with the minimal prompt | 7122 | 7231 | 1.5% |

Parity checklist: no `500k cr at StarDock`, no `corp_deposit`, no `corp_withdraw`, no `shared treasury`. f1 parity hint names `plot_course` execute and does not say warp back. f4 hint does not copy the password. Legacy keeps the 500k line, the warp-back hint, and a compact legal list with no `args` key. Token estimate is chars/4: full parity prompt about 10,420 tokens.

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

## Planted-bug tests

These names are the ones a re-break has to fail. The re-break itself is still to do on the final commit.

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
