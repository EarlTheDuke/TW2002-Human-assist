# Bots, the bank, and cash lost at death

`BOTS_BANK_MODE` `tw2002` | `legacy`. Legacy is the bot at 4627c0b. This slice does not change a bank rule, a tax rule, or what a death does to credits. It changes how SeatBrain and the heuristic spend and store the money the engine already allows.

Sources: the EIS bank menu (a nest egg brings you back after a ship loss), the EIS StarDock menu (personal accounts, corporate funds in citadels), MBBS (about 50,000 in the bank for a rainy day), Iago (emergency cash, then 100,000; no interest), the Cabal economy notes (drop the day's cash at the bank; do not carry a fortune), and the engine doc for the galactic bank. TWGS 3.11 is the default. MBBS breaks a tie.

## Rules

| # | Rule | Mark | Constant | Test |
| --- | --- | --- | --- | --- |
| bb1 | The mode is on. Legacy SeatBrain, H, memory, and reports stay byte-identical | OURS | `BOTS_BANK_MODE` tw2002, `BOT_BANK_POLICY` reserve | `test_bb1_mode` |
| bb2 | At StarDock a purchase may use cash plus the bank, minus the nest egg. Away from StarDock only cash on hand counts | STRATEGY | — | `test_bb2_purse` |
| bb3 | A StarDock buy that costs more than the cash withdraws the exact shortfall, then buys. At most 3 withdraws a visit | STRATEGY | `BOT_BANK_MAX_WITHDRAWS_PER_VISIT` 3 | `test_bb3_withdraw_the_shortfall` |
| bb4 | The genesis hold is not used. Legacy and policy `tax_and_death` keep it | STRATEGY | — | `test_bb4_no_genesis_hold` |
| bb5 | Leaving StarDock the seat carries trade capital plus planned off-dock spends, capped at 150,000 | STRATEGY | `BOT_BANK_MIN_FLOAT` 5000, `BOT_BANK_CAPITAL_PER_HOLD` 250, `BOT_BANK_AWAY_CAP` 150000, `BOT_BANK_TOLL_BUDGET` 2000 | `test_bb5_away_reserve` |
| bb6 | The nest egg stages with net worth: 10,000, then 50,000, then 100,000. A normal withdraw does not spend it | STRATEGY | `BOT_BANK_NEST_EGG_STAGES` | `test_bb6_nest_egg` |
| bb7 | After this visit's StarDock buys, spare cash is deposited on the way out or at the end of the day | STRATEGY | `BOT_BANK_EOD_TURNS` 5 | `test_bb7_deposit` |
| bb8 | Day 1 deposits at most 10,000, and only when the opening trade still has its capital | DERIVED | `BOT_BANK_DAY1_DEPOSIT` 10000 | `test_bb8_day1_cap` |
| bb9 | A recent loss, a pod or Scout, not FedSafe, a nearby threat, or under 50 fighters halves the cash carried out | STRATEGY | `BOT_BANK_RISK_DAYS` 3, `BOT_BANK_RISK_HOPS` 3, `BOT_BANK_RISK_FIGHTERS` 50 | `test_bb9_risk` |
| bb10 | A good trader does not leave StarDock, or end the day there, over the tax line unless today's off-dock buy needs it. An evil trader is not taxed | STRATEGY | `TAX_THRESHOLD`, `TAX_MIN_ALIGNMENT` | `test_bb10_tax_line` |
| bb11 | With 150,000 spare and StarDock within 3 extra hops, detour once a day. Not while hauling a planned sale | STRATEGY | `BOT_BANK_DETOUR_HOPS` 3, `BOT_BANK_DETOUR_CASH` 150000, `BOT_BANK_DETOURS_PER_DAY` 1 | `test_bb11_detour` |
| bb12 | Overflow into an owned citadel only when the bank account is full. One deposit per landing | CONFIRMED | `BOT_TREASURY_POLICY` overflow | `test_bb12_treasury` |
| bb13 | At StarDock in a pod or the free Scout, withdraw for the recovery hull before buying the Scout | CONFIRMED | — | `test_bb13_recovery` |
| bb14 | H deposits spare cash once a visit and withdraws for its pod replacement. Legacy H does not bank | STRATEGY | `BOT_BANK_H` True | `test_bb14_h_banks` |
| bb15 | Planet targets use the purse, not the cash left after a deposit. A torpedo is bought on the visit that deploys it | STRATEGY | — | `test_bb15_genesis_on_the_deploy_visit` |
| bb16 | Colonist and citadel cash survive a deposit, at StarDock from the purse and elsewhere in the away reserve | DERIVED | — | `test_bb16_n2_colonist_budget_survives_deposit` |
| bb17 | Corp pooling and the tax shield run before the bank step. The bank does not transfer | CONFIRMED | `BOT_BANK_TRANSFER` False | `test_bb17_corp_before_bank` |
| bb18 | No deposit and withdraw of the same credits in one visit unless a buy sits between them. At most 8 bank verbs a day | OURS | `BOT_BANK_MAX_VERBS_PER_DAY` 8 | `test_bb18_no_ping_pong` |
| bb19 | Every bank or treasury amount a bot sends is inside the legal maximum | OURS | — | `test_bb19_legal_amounts` |
| bb20 | The planner reads only that seat's observation | CONFIRMED | — | `test_bb20_fog` |
| bb21 | No random draw. New memory keys are omitted at their defaults and survive save and load. Legacy persists nothing new | OURS | — | `test_bb21_memory` |
| bb22 | `--bank-report` counts deposits, withdraws by purpose, treasury, detours, nest egg, cash carried out, credits lost at death, tax, broke days, and recovery lag | OURS | `BOT_BANK_BROKE_LINE` 10000 | `test_bb22_report` |
| bb23 | Policy `tax_and_death` keeps the old hold, the 30,000 float, and a silent H | OURS | `BOT_BANK_POLICY` | `test_bb23_tax_and_death` |
| bb24 | The scenario lab prints PASS | OURS | — | `test_bb24_lab` |
| bb25 | The bank doc's open calls point here | OURS | — | `test_bb25_docs` |
| bb26 | Findings F1 through F7 are kept. No engine change | OURS | — | `test_bb26_findings_kept` |
| bb27 | After a recovery spend, the next deposit rebuilds the nest egg first | STRATEGY | — | `test_bb27_rebuild_the_nest_egg` |
| bb28 | An evil seat uses the same nest egg and away reserve, and has no tax line | STRATEGY | — | `test_bb28_evil` |
| bb29 | The LLM seat is not told anything new and is not driven by this policy | OURS | — | `test_bb29_llm_untouched` |
| bb30 | A 5-day six-seat run under `reserve` emits only legal bank verbs | OURS | — | `test_bb30_five_day_rejects` |

## Decisions

Built on the spec defaults. D8 stays open and is not built.

| # | Choice | Default used |
| --- | --- | --- |
| D1 | Replace the genesis hold with the StarDock purse | replace |
| D2 | Away reserve is holds times 250 plus planned off-dock spends, cap 150,000 | that reserve |
| D3 | Detour up to 3 extra hops when 150,000 or more is spare | 3 hops |
| D4 | Citadel treasury only after the 500,000 account is full | overflow |
| D5 | Nest egg 10,000, then 50,000, then 100,000 | those stages |
| D6 | H banks | on |
| D7 | Day-1 deposit cap 10,000 | 10,000 |
| D8 | Credits when return fire kills the attacker, and a corbomite-kill payout | still open, not this slice |

## Findings

Kept. None of these is an engine change.

| # | What the sources and the engine say | Why it stays |
| --- | --- | --- |
| F1 | The bank has no minimum, float, or fee. The 30,000 figure is the bot's old keep | The bank is unchanged. The bot's keep moves to the away reserve |
| F2 | StarDock only, personal accounts, cap 500,000, no interest, transfer from cash, tax on good traders over 100,000 | Already the engine. The 100,000 cap conflict stays recorded on the bank slice |
| F3 | Cash on hand lost at a ship loss is unverified. The balance surviving is confirmed | Kept. It is why the bot banks |
| F4 | The old note said bots withdraw for ships, hardware, and fighters. The code withdraws only for a CargoTran | Bot policy, fixed by the shortfall withdraw |
| F5 | The pod buy runs before the bank step, so a pod at StarDock buys a Scout and never withdraws | Bot policy, the bank step moves ahead of that buy |
| F6 | Citadel treasury cap is 10,000,000 here. One source prints a much larger cap. Interest is 2 percent | Kept. Earlier call, not a bank rule |
| F7 | No code bot uses a citadel treasury | Bot policy, the overflow rule |

## Constants

`BOTS_BANK_MODE` tw2002. `bots_bank_on()` is that mode and the bank mode both on. `BOT_BANK_POLICY` reserve under the new mode. `tax_and_death` is the slice 56 bot. `off` never banks.

`BOT_BANK_MAX_WITHDRAWS_PER_VISIT` 3. `BOT_BANK_MIN_FLOAT` 5000. `BOT_BANK_CAPITAL_PER_HOLD` 250. `BOT_BANK_TOLL_BUDGET` 2000. `BOT_BANK_AWAY_CAP` 150000. `BOT_BANK_NEST_EGG_STAGES` (0, 10000), (150000, 50000), (500000, 100000). `BOT_BANK_EOD_TURNS` 5. `BOT_BANK_DAY1_DEPOSIT` 10000. `BOT_BANK_RISK_DAYS` 3. `BOT_BANK_RISK_HOPS` 3. `BOT_BANK_RISK_FIGHTERS` 50. `BOT_BANK_DETOUR_HOPS` stays 0 for the old bot. `BOT_BANK_DETOUR_HOPS_ON` 3. `BOT_BANK_DETOUR_CASH` 150000. `BOT_BANK_DETOURS_PER_DAY` 1. `BOT_TREASURY_POLICY` overflow. `BOT_BANK_H` on. `BOT_BANK_MAX_VERBS_PER_DAY` 8. `BOT_BANK_BROKE_LINE` 10000. `BOT_BANK_TRANSFER` stays false. `BOT_BANK_FLOAT` 30000 stays for the legacy policy.

## Legacy pin

Recorded before any bot reads `BOTS_BANK_MODE`. 3-day N3,N2,N1,H seed 250925. Golden `9b607d3dae940c0b1a69f6d7`. The flip list starts with `BOTS_BANK_MODE` and includes `LLM_PLANET_NUDGE_MODE` and `LLM_PARITY_MODE` plus the older modes. `LLM_ROUTE_NOTICE`, `LLM_NEW_DAY_GOAL_NOTICE`, and `LLM_SELL_FIRST` are set false. The parity pin kept the same golden after `BOTS_BANK_MODE` was added to its flip list. The 10-day six-seat digest is measured outside the suite.

## Before

Measured on e511652. `BOTS_BANK_MODE` exists and nothing reads it, so this is the slice 60 bot. Seed 250925, 10 days, seats N3,N3,N2,N2,N1,H. Rejected 0/0. Exceptions 0. The net-worth table matches the parity match digest `cd91bf36`.

| Seat | Net worth | Ship | Deaths | Bank balance | Deposited | Withdrew | Tax | Credits lost at death |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| N3-P1 | 648,074 | cargotran | 0 | 0 | 0 | 0 | 34,403 | 0 |
| N2-P3 | 314,875 | cargotran | 0 | 46,227 | 46,227 | 0 | 0 | 0 |
| N1-P5 | 217,288 | cargotran | 0 | 0 | 0 | 0 | 0 | 0 |
| N3-P2 | 188,773 | merchant_cruiser | 0 | 0 | 0 | 0 | 0 | 0 |
| N2-P4 | 138,940 | merchant_cruiser | 0 | 0 | 0 | 0 | 0 | 0 |
| H-P6 | 7,975 | scout_marauder | 3 | 0 | 0 | 0 | 41,121 | 238,988 |

H never deposited. One N2 deposited once and never withdrew. Seed 4242, same seats, rejected 0/0, exceptions 0. The net-worth table matches the parity match digest `7ad15bc9`.

| Seat | Net worth | Ship | Deaths | Bank balance | Deposited | Withdrew | Tax | Credits lost at death |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| N1-P5 | 476,782 | merchant_cruiser | 0 | 0 | 0 | 0 | 39,198 | 0 |
| N2-P3 | 461,882 | cargotran | 0 | 144,872 | 144,872 | 0 | 0 | 0 |
| N3-P1 | 460,723 | cargotran | 0 | 0 | 0 | 0 | 7,591 | 0 |
| N3-P2 | 216,931 | cargotran | 0 | 0 | 0 | 0 | 0 | 0 |
| N2-P4 | 154,737 | merchant_cruiser | 0 | 0 | 0 | 0 | 0 | 0 |
| H-P6 | 7,975 | scout_marauder | 3 | 0 | 0 | 0 | 13,145 | 205,410 |

H again never banked, lost the cash at the third death, and finished in a Scout at 7,975. The earlier bank-slice totals that motivated the slice stay in the galactic bank note: seed 250925 fell from 2,919,443 with no bank to 1,871,215, and seed 424242 from 2,899,689 to 1,626,702.

## Seat brain

`BOT_BANK_POLICY` default is now `reserve`. Legacy mode, and policy `tax_and_death`, keep the old float and the genesis hold. Under reserve, a StarDock visit withdraws the CargoTran or genesis shortfall from the bank without spending the nest egg, then deposits cash above the away reserve. A pod withdraws for the replacement hull before it buys a Scout. The planet target counts cash plus the bank minus the nest egg.

The three bars that broke when the hold was removed now pass: `test_record_then_replay_with_fresh_brain`, `test_n2_solo_tw2002_keeps_colonising`, `test_n2_day10_beats_n1_and_keeps_organics`. Seed 250925 N2 in the growth replay: 2 genesis worlds, net worth 441,475, planet 32 still the held zero. H does not bank yet.

## Planted bugs

Each row is the bug that will be planted, and the test that must fail. Not re-broken yet. That happens on the final commit.

| Bug | Test |
| --- | --- |
| pb1 withdraw sends the whole balance | `test_pb1_withdraw_is_the_shortfall` |
| pb2 a bank verb away from StarDock | `test_pb2_no_bank_verb_off_the_dock` |
| pb3 deposit, then withdraw the same credits for a buy | `test_pb3_no_ping_pong_around_a_buy` |
| pb4 the genesis hold still blocks deposits | `test_pb4_genesis_hold_is_off` |
| pb5 the away reserve omits the citadel step | `test_pb5_citadel_cash_is_in_the_reserve` |
| pb6 a buy withdraws the nest egg | `test_pb6_nest_egg_stays` |
| pb7 a pod buys a Scout before the bank step | `test_pb7_pod_withdraws_before_the_scout` |
| pb8 recovery withdraws the whole balance | `test_pb8_recovery_is_the_hull_cost` |
| pb9 day-1 deposit over 10,000 | `test_pb9_day1_deposit_cap` |
| pb10 risk flags raise the cap | `test_pb10_risk_halves_the_cap` |
| pb11 tax line on an evil seat, or a good seat ends at StarDock over the line | `test_pb11_tax_line` |
| pb12 a second detour, or six hops off the plan | `test_pb12_one_short_detour` |
| pb13 treasury deposit on a bare planet or a rival planet | `test_pb13_treasury_needs_an_owned_citadel` |
| pb14 treasury deposit while the bank has room | `test_pb14_overflow_waits_for_a_full_bank` |
| pb15 H banks while the mode is legacy | `test_pb15_legacy_h_does_not_bank` |
| pb16 H never withdraws for the pod hull | `test_pb16_h_withdraws_for_the_pod` |
| pb17 the daily verb cap does not reset | `test_pb17_verb_cap_resets` |
| pb18 a pending buy is lost on save and load | `test_pb18_pending_buy_survives_save` |
| pb19 the bank step runs before the corp tax shield | `test_pb19_corp_shield_runs_first` |
| pb20 planet targets read cash on hand only | `test_pb20_targets_use_the_purse` |
| pb21 the planner reads another seat's balance | `test_pb21_no_rival_balance` |
| pb22 the planner draws a random number | `test_pb22_no_rng` |
| pb23 legacy uses the new reserve | `test_pb23_legacy_keeps_the_float` |
| pb24 a torpedo is carried overnight with no deploy planned | `test_pb24_no_spare_torpedo_overnight` |
| pb25 the report files a recovery withdraw as a hull buy and drops credits lost | `test_pb25_report_names_recovery_and_losses` |

## After, on b4ae22e

Policy `reserve`. Rejected 0/0 and the save matched on every run. Citadel deposits and detours showed up only on the 30-day runs, after a bank account filled.

10-day seed 250925, digest `16ad8833`, total 1,809,848. N3-P1 766,412 (bank 397,499, tax 15,708). N2-P3 387,649 (bank 50,000). N1-P5 281,031 (bank 50,000). N3-P2 163,396 (bank 15,865). N2-P4 161,357 (bank 15,435). H-P6 50,003, 2 deaths, lost 33,576, bank 42,028, Scout from day 5.

10-day seed 424242, digest `6ca2c5b9`, total 1,725,233. N3-P1 782,515 (bank 452,997). N2-P3 613,939 (bank 267,794). N2-P4 174,906 (bank 38,131). N3-P2 127,923 (bank 15,387). N1-P5 17,975, 2 deaths, bank 10,000, Scout from day 1. H-P6 7,975, 4 deaths, bank 0, broke 9 days. The before column for this slice used seed 4242, not 424242.

30-day seed 250925, digest `b15d65a0`, total 6,280,129. N3-P1 2,823,128 (bank full at 500,000, treasury 797,982, tax 301,070, 9 detours). N2-P3 1,520,218 (treasury 317,135, 4 deaths, 1 detour). N1-P5 892,662 (5 deaths). N3-P2 523,588. N2-P4 470,530, ended in a Scout. H-P6 still 50,003.

30-day seed 424242, digest `0bc512d4`, total 4,605,090. N3-P1 2,458,682 (bank full, treasury 336,390, tax 428,874, 17 detours). N2-P3 1,276,834 (10 deaths, lost 524,200, treasury 78,907). N2-P4 611,932. N3-P2 231,692. N1-P5 stayed 17,975. H-P6 stayed 7,975 with broke 29 days and no deposit.

S7 is not met. H at day 10 is 50,003 on seed 250925 and 7,975 on seed 424242. The 10,000 nest egg on N1-P5 cannot buy a CargoTran.

## Spare citadel and no detour, 10 days

Same seats, policy reserve. Spare sets `BOT_TREASURY_POLICY` to `spare`. No-detour sets `BOT_BANK_DETOUR_HOPS_ON` to 0.

Seed 250925 spare, digest `e64c952b`, total 1,787,645. N3-P1 733,903. N2-P3 389,968 and a 3-credit citadel deposit. N1-P5 278,818. N3-P2 173,596. N2-P4 161,357. H-P6 50,003. Overflow on this seed was 1,809,848 with no citadel deposit.

Seed 250925 with the detour off matches overflow exactly: digest `16ad8833`, total 1,809,848. The overflow 10-day took 0 detours.

Seed 424242 spare matches overflow exactly: digest `6ca2c5b9`, total 1,725,233, treasury 0. That overflow 10-day also took 0 detours, so turning the detour off does not change it either. The detours in the 30-day overflow runs were 9 on seed 250925 and 17 on seed 424242.
