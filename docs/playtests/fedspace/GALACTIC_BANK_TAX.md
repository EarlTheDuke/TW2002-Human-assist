# Galactic Bank and the good-trader tax

`BANK_MODE` `tw2002` | `legacy`. Legacy is the engine before this slice: no bank verbs, no daily tax, credits on hand stay with a destroyed ship.

## Rules

| # | Rule | Mark | Constant | Test |
| --- | --- | --- | --- | --- |
| gb1 | Bank verbs only at StarDock, alive, in the ship. A pod may bank | CONFIRMED EIS | — | `test_gb1_only_at_stardock`, `test_gb12_balance_survives_and_guard` |
| gb2 | One personal account. No corp account | CONFIRMED EIS, Gypsy | `Player.bank_balance` | `test_gb2_personal_account` |
| gb3 | `bank_deposit {amount}` moves ship credits into the account at once | CONFIRMED EIS | — | `test_gb3_deposit_and_gb6_amount` |
| gb4 | Account cap 500,000. Bible 100,000 is the alt | SOURCE-CONFLICT | `BANK_MAX_BALANCE` 500000 | `test_gb4_gb5_cap_is_refused`, `test_gb5_refuse_message_and_variants` |
| gb5 | Over cap or over cash is refused, with the room in the message | UNVERIFIED | `BANK_OVERCAP` refuse | `test_gb5_refuse_message_and_variants` |
| gb6 | Amount is an integer >= 1 | DERIVED | — | `test_gb3_deposit_and_gb6_amount` |
| gb7 | `bank_withdraw {amount}` to ship credits. No fee | UNVERIFIED fee | `BANK_WITHDRAW_FEE` 0 | `test_gb7_withdraw_and_net_worth_holds` |
| gb8 | `bank_transfer {to_player, amount}` takes ship credits | SOURCE-CONFLICT | `BANK_TRANSFER_SOURCE` cash | `test_gb8_transfer_from_cash_and_unknown_id`, `test_gb9_recipients` |
| gb9 | Any other non-eliminated trader, including corpmates. Recipient room is respected | UNVERIFIED | `BANK_TRANSFER_CORPMATES` True, `BANK_TRANSFER_RESPECTS_CAP` True, `BANK_SHOW_RECIPIENT_ROOM` True | `test_gb9_recipients` |
| gb10 | No interest | CONFIRMED Iago, S1 | `BANK_INTEREST_PCT` 0 | `test_gb10_no_interest` |
| gb11 | Bank verbs cost 0 turns | UNVERIFIED | `BANK_TURN_COST` 0 | `test_gb11_no_turn_at_the_cap` |
| gb12 | The balance survives ship loss, capture, tribute, and tows | CONFIRMED EIS | — | `test_gb12_balance_survives_and_guard`, `test_gb13_cash_lost_balance_kept` |
| gb13 | On a tw2002 ship loss, credits on hand go to 0 | UNVERIFIED | `DEATH_CREDITS_ON_HAND` lost | `test_gb13_cash_lost_balance_kept`, `test_gb13_kept_variant_and_legacy_death` |
| gb14 | A player ship-kill of a real hull pays the cash to the killer. A Ferrengi kill pays the Ferrengi. Other losses sink | UNVERIFIED amount | `DEATH_CREDITS_TO_KILLER` player_ship_kill, `DEATH_CREDITS_RECOVER_PCT` 100, `DEATH_CREDITS_FERRENGI` to_ferrengi | `test_gb14_who_receives`, `test_pod_kill_pays_the_killer_nothing` |
| gb15 | A capture loses cash the same way as a destroy | DERIVED | `CAPTURE_CREDITS` as_destroy | `test_gb15_capture` |
| gb16 | Death events hide the credit numbers from witnesses | DERIVED | — | `test_gb16_death_fog` |
| gb17 | Tax applies at alignment >= 0 | SOURCE-CONFLICT | `TAX_MIN_ALIGNMENT` 0 | `test_gb17_gb19_tax_table`, `test_gb18_and_gb21_and_gb22` |
| gb18 | Taxed only above 100,000 on hand | SOURCE-CONFLICT | `TAX_THRESHOLD` 100000 | `test_gb18_and_gb21_and_gb22` |
| gb19 | Tax is 5% of all cash on hand, floored | SOURCE-CONFLICT | `TAX_RATE_PCT` 5, `TAX_ROUNDING` floor | `test_gb17_gb19_tax_table` |
| gb20 | Bank balances and treasuries are not taxed | CONFIRMED glossary | — | `test_gb20_cash_only` |
| gb21 | Alignment +floor(tax / 1500). No experience | CONFIRMED rate; UNVERIFIED exp | `TAX_CREDITS_PER_ALIGN` 1500, `TAX_EXP` 0 | `test_gb18_and_gb21_and_gb22` |
| gb22 | A tax that would grant 32,000 alignment grants none | SOURCE-CONFLICT | `TAX_ALIGN_AWARD_MAX` 31999, `TAX_ALIGN_OVERFLOW` none | `test_gb18_and_gb21_and_gb22` |
| gb23 | Once per day, last step of the day tick, after overnight cash | DERIVED mapping | `TAX_WHEN` day_tick | `test_gb23_tax_is_last_and_gb24_sinks` |
| gb24 | The tax leaves the economy | CONFIRMED glossary | `TAX_TO` sink | `test_gb23_tax_is_last_and_gb24_sinks` |
| gb25 | `TAX_COLLECTED` is actor-only | DERIVED | — | `test_gb25_and_gb28_fog` |
| gb26 | Net worth includes the balance. Economic victory still uses cash on hand | DERIVED | `BANK_IN_NET_WORTH` True | `test_gb7_withdraw_and_net_worth_holds`, `test_gb26_economic_victory_uses_cash` |
| gb27 | Own observation always shows balance, room, and tomorrow's tax | DERIVED | `BANK_BALANCE_VIEW` always | `test_gb27_own_view` |
| gb28 | Rivals never see a balance, a tax, or death credits | DERIVED | — | `test_gb16_death_fog`, `test_gb25_and_gb28_fog` |
| gb29 | Bots deposit spare cash only while already at StarDock, once per visit, keeping the float or the next hull | DERIVED | `BOT_BANK_POLICY` tax_and_death, `BOT_BANK_FLOAT` 30000, `BOT_BANK_DETOUR_HOPS` 0 | `test_gb29_gb31_bot` |
| gb30 | At StarDock, bots withdraw the exact shortfall before a hull buy, including a pod's replacement | DERIVED | — | `test_gb29_gb31_bot` |
| gb31 | Bots do not transfer and do not detour to dodge the tax | DERIVED | `BOT_BANK_TRANSFER` False | `test_gb29_gb31_bot` |
| gb32 | One prompt line, only when the mode is on | DERIVED | — | `test_gb32_prompt_and_legacy` |

## Source conflicts

- gb4: TWGS account cap 500,000. Bible and Iago say 100,000. TWGS wins.
- gb8: EIS transfer spends ship credits. Bible says the money leaves your account. EIS wins.
- gb17: Glossary taxes alignment 0 or more. Bible and Iago say positive only. TWGS wins.
- gb18: Glossary and MBBS tax cash over 100,000. Bible and Iago say 50,000. TWGS wins.
- gb19: Glossary and MBBS take 5% of the whole amount. Bible and Iago say 10%. TWGS wins.
- gb22: Glossary pays no alignment when one tax would grant 32,000 or more. REV says the boundary value. TWGS wins.

## Planted bugs

pb1–pb25 are the inverses of the rule tests above (deposit off StarDock, cap ignored, clip, over-withdraw, transfer that does not credit, transfer to self or the dead, room ignored, interest, a turn charge, tax on evil, tax at 100,000, tax on the excess, tax on the balance, tax twice, alignment per 150, tax before the day tick, balance wiped on a pod, cash kept on a tw2002 death, killer paid for a pod or a mine, legacy death also zeroing cash, net worth dropping on a deposit, a rival seeing the balance, a max the handler refuses, a bot depositing away from StarDock). The tests assert the correct side. The stubs were not left in the tree.

## Deliberate differences

The tax runs at the day tick, because the engine has no logins. The balance is on the trader's own status at all times. One amount per verb. The displayed-versus-actual tax quirk is not copied. Bank verbs cost no turns. Net worth counts the balance. Economic victory still counts cash on hand. A Ferrengi kill pays the lost cash to the Ferrengi ship. A captured pilot loses his cash to the capturer. Bots bank only when they are already at StarDock.

## Scenario lab

`scripts/bank_tax_scenario_lab.py` prints `bank_tax_scenario_lab: PASS`. Blue deposits 500,000 (600,000 refused, room 500,000), then the day tick takes 25,000 tax and +16 alignment. Midnight still grants +1 alignment first, so a seat who started at 0 ends at 17. Red starts at -2 so the midnight +1 leaves them evil, and 2,000,000 is not taxed. A Merchant Cruiser pod pays the killer the cash on hand and leaves the balance; withdrawing it at StarDock buys a hull. A second hit while already in the pod is Ship Destroyed and pays the killer nothing. A transfer of 50,000 into an account that is already full is refused.

## Match check

Scripted 10-day N3,N3,N2,N2,N1,H. Legacy is the before column (no deposits, no tax). Seed 250925 legacy net worth matches the port-upgrade run: N3-P1 745,255, H-P6 619,312, N2-P4 547,351, N1-P5 425,700, N2-P3 337,339, N3-P2 246,986. Tw2002, same seed, rejected 0, exceptions 0: N3-P1 709,193 (bank 500,000, tax 0), N2-P4 569,961 (bank 311,985), N3-P2 503,631 (bank 353,137), H-P6 396,076 (bank 0, tax 58,867, +36 align), N1-P5 378,787 (bank 168,098), N2-P3 365,365 (bank 149,214). No deaths. The N seats banked, so the tax missed them; the lower net worth is the trades they skipped while the cash sat in the account. H is the heuristic and does not bank, so the tax hit the cash it carried.

Seed 424242 legacy: N3-P2 616,259, N3-P1 600,421, H-P6 504,625, N2-P3 469,904, N2-P4 397,182, N1-P5 342,336. Tw2002 rejected 0, exceptions 0: N3-P1 715,418 (bank 500,000), N2-P3 547,145 (bank 305,796), N2-P4 491,475 (bank 283,992), N3-P2 288,266 (bank 145,428), N1-P5 7,975 (1 death, 18,000 credits lost, killer recovered 0), H-P6 7,975 (3 deaths, 18,000 credits lost). The two poor seats died with the cash still on the ship.

30-day seed 250925, same six seats, tw2002: day 30, rejected 0, exceptions 0, save/load identical. N3-P1 1,970,163 (bank 500,000, tax 618,246, recovered 965,210, 0 deaths, battleship). N2-P4 1,358,382 (bank 500,000, 8 deaths). N2-P3 1,271,641 (bank 500,000, 5 deaths). N1-P5 1,206,575 (bank 500,000, tax 21,999, 0 deaths). N3-P2 745,224 (bank 500,000, tax 60,467, 6 deaths). H-P6 7,975 (bank 0, tax 199,507, 6 deaths, scout). SeatBrain fills the account and still pays tax on whatever cash is left on the ship at midnight. The heuristic never deposits, so the tax and the lost cash took it back to a scout.

The shipped bot does not deposit while StarDock still sells the next genesis torpedo, so a 10-day seat that is still building keeps its cash and the older net-worth bars stay put. The figures above were measured before that hold.

## QC (slice 56, Grok Bot, 2026-10-06)

Reviewed 57dec11 rule by rule (legal list against handler, hidden information). Fixes:

- A refused bank verb now says which side is empty: "no credits on hand", "account full", "nothing in the account", "every account is full".
- Deposit capacity is a parameter. The transfer max is the best recipient's room, so the legal max is never one the handler refuses.
- StarDock balance-view alt in the observation.
- Eliminated traders cannot bank and are not offered as transfer recipients.
- pb21: DEATH_MODE legacy under BANK_MODE tw2002 keeps the x0.75 path and pays the killer nothing. No test caught this plant before QC, because the slice's legacy-death test inherited DEATH_CREDITS_ON_HAND "kept".
- Bot policy: the genesis hold stays. QC first removed it, because the keep already covers the next planned purchase and the 10-day totals rose (seed 250925: 1.87M to 2.92M). Without the hold, though, an N2 seat banks its colonist money, and three tests fail: `test_seat_bot_s4::test_record_then_replay_with_fresh_brain`, `test_class0_terra_qc_v1::test_n2_solo_tw2002_keeps_colonising` and `test_seat_bot_n2::test_n2_day10_beats_n1_and_keeps_organics`. The hold is restored, and this is an open call for Ben.

Planted bugs: spec variants 30/30 caught. Without the QC tests, the slice's tests missed pb4, pb20, pb21, pb23b and pb24. Of 23 QC plants, 19 are caught; the other 4 are equivalent mutants. Tests: `tests/test_galactic_bank_tax_qc5657.py`.

Legacy: the pin 9b607d3dae940c0b1a69f6d7 is the same on Linux (box) and Windows (Ven suite). The 10-day 6-seat digest outside the suite is 221826d9bd9a6a6c85668224, unchanged.

Scenario lab: PASS on the QC tree.

10-day scripted N3,N3,N2,N2,N1,H, QC tree, BOT_CORP_POLICY off, rejected 0, exceptions 0:

| Seed | Legacy total (f1496a3) | QC tree total | Seats |
| --- | --- | --- | --- |
| 250925 | 2,919,443 | 1,871,215 | N3-P1 783,190, N2-P4 555,175, N3-P2 196,480, N1-P5 168,592 (1 death), N2-P3 159,803 (1 death), H-P6 7,975 (3 deaths) |
| 424242 | 2,899,689 | 1,626,702 | N3-P1 645,037 (bank 164,005), N2-P4 462,512 (bank 196,107), N2-P3 323,415 (bank 106,053), N3-P2 179,788, N1-P5 7,975 (2 deaths), H-P6 7,975 (3 deaths) |

These equal the slice's own bank runs. The drop against legacy comes from cash lost at a tw2002 death, the tax on cash carried, and the hold, which keeps building seats from banking.

30-day headless (seed 250925, six seats, engine at QC 23cccd9). With stress injections (p 0.02: random legal deposit, withdraw and transfer, plus a max+1 retry that must be refused): day 30, 0 invariant problems, 0 exceptions. 32 taxes took 766,208 in total. Credits and balances stayed at or above 0, and every balance stayed under the cap. Balances moved only on bank verbs, never at the tick. Each tax was greater than 0 and no more than the cash on hand. Save/load was identical 27 times; the other 2 differed only in the set order of `known_sectors`, which is pre-existing. The 5 bot rejects are a stress artefact: an injected deposit filled the room just before the bot's stale deposit.

Open calls for Ben: the genesis hold; seats broke from day 1 (a 20,000 start is below the 30,000 float, and the cash goes at the first death); H never banks; a corbomite kill pays the corbomite owner, while an attacker killed by return fire pays nobody. Decided in slice 64 (cl11, cl12): return fire pays the defender, and a corbomite kill pays a living owner.
