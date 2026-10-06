# Galactic Bank and the good-trader tax

`BANK_MODE` `tw2002` | `legacy`. Legacy is the engine before this slice: no bank verbs, no daily tax, credits on hand stay with a destroyed ship.

## Rules

| # | Rule | Mark | Constant | Test |
| --- | --- | --- | --- | --- |
| gb1 | Bank verbs only at StarDock, alive, in the ship. A pod may bank | CONFIRMED EIS | — | `test_gb1_stardock_only` |
| gb2 | One personal account. No corp account | CONFIRMED EIS, Gypsy | `Player.bank_balance` | `test_gb2_personal_account` |
| gb3 | `bank_deposit {amount}` moves ship credits into the account at once | CONFIRMED EIS | — | `test_gb3_deposit` |
| gb4 | Account cap 500,000. Bible 100,000 is the alt | SOURCE-CONFLICT | `BANK_MAX_BALANCE` 500000 | `test_gb4_cap` |
| gb5 | Over cap or over cash is refused, with the room in the message | UNVERIFIED | `BANK_OVERCAP` refuse | `test_gb5_refuse_over_cap` |
| gb6 | Amount is an integer >= 1 | DERIVED | — | `test_gb6_amount` |
| gb7 | `bank_withdraw {amount}` to ship credits. No fee | UNVERIFIED fee | `BANK_WITHDRAW_FEE` 0 | `test_gb7_withdraw` |
| gb8 | `bank_transfer {to_player, amount}` takes ship credits | SOURCE-CONFLICT | `BANK_TRANSFER_SOURCE` cash | `test_gb8_transfer_from_cash` |
| gb9 | Any other non-eliminated trader, including corpmates. Recipient room is respected | UNVERIFIED | `BANK_TRANSFER_CORPMATES` True, `BANK_TRANSFER_RESPECTS_CAP` True | `test_gb9_recipient` |
| gb10 | No interest | CONFIRMED Iago, S1 | `BANK_INTEREST_PCT` 0 | `test_gb10_no_interest` |
| gb11 | Bank verbs cost 0 turns | UNVERIFIED | `BANK_TURN_COST` 0 | `test_gb11_no_turn` |
| gb12 | The balance survives ship loss, capture, tribute, and tows | CONFIRMED EIS | — | `test_gb12_balance_survives` |
| gb13 | On a tw2002 ship loss, credits on hand go to 0 | UNVERIFIED | `DEATH_CREDITS_ON_HAND` lost | `test_gb13_cash_lost_on_death` |
| gb14 | A player ship-kill of a real hull pays the cash to the killer. A Ferrengi kill pays the Ferrengi. Other losses sink | UNVERIFIED amount | `DEATH_CREDITS_TO_KILLER` player_ship_kill, `DEATH_CREDITS_RECOVER_PCT` 100, `DEATH_CREDITS_FERRENGI` to_ferrengi | `test_gb14_who_receives` |
| gb15 | A capture loses cash the same way as a destroy | DERIVED | `CAPTURE_CREDITS` as_destroy | `test_gb15_capture` |
| gb16 | Death events hide the credit numbers from witnesses | DERIVED | — | `test_gb16_death_fog` |
| gb17 | Tax applies at alignment >= 0 | SOURCE-CONFLICT | `TAX_MIN_ALIGNMENT` 0 | `test_gb17_alignment_floor` |
| gb18 | Taxed only above 100,000 on hand | SOURCE-CONFLICT | `TAX_THRESHOLD` 100000 | `test_gb18_threshold` |
| gb19 | Tax is 5% of all cash on hand, floored | SOURCE-CONFLICT | `TAX_RATE_PCT` 5, `TAX_ROUNDING` floor | `test_gb19_rate` |
| gb20 | Bank balances and treasuries are not taxed | CONFIRMED glossary | — | `test_gb20_cash_only` |
| gb21 | Alignment +floor(tax / 1500). No experience | CONFIRMED rate; UNVERIFIED exp | `TAX_CREDITS_PER_ALIGN` 1500, `TAX_EXP` 0 | `test_gb21_align` |
| gb22 | A tax that would grant 32,000 alignment grants none | SOURCE-CONFLICT | `TAX_ALIGN_AWARD_MAX` 31999, `TAX_ALIGN_OVERFLOW` none | `test_gb22_overflow` |
| gb23 | Once per day, last step of the day tick, after overnight cash | DERIVED mapping | `TAX_WHEN` day_tick | `test_gb23_when` |
| gb24 | The tax leaves the economy | CONFIRMED glossary | `TAX_TO` sink | `test_gb24_sink` |
| gb25 | `TAX_COLLECTED` is actor-only | DERIVED | — | `test_gb25_event` |
| gb26 | Net worth includes the balance. Economic victory still uses cash on hand | DERIVED | `BANK_IN_NET_WORTH` True | `test_gb26_net_worth` |
| gb27 | Own observation always shows balance, room, and tomorrow's tax | DERIVED | `BANK_BALANCE_VIEW` always | `test_gb27_own_view` |
| gb28 | Rivals never see a balance, a tax, or death credits | DERIVED | — | `test_gb28_fog` |
| gb29 | Bots deposit spare cash only while already at StarDock | DERIVED | `BOT_BANK_POLICY` tax_and_death, `BOT_BANK_FLOAT` 30000, `BOT_BANK_DETOUR_HOPS` 0 | `test_gb29_bot_deposit` |
| gb30 | At StarDock, bots withdraw the shortfall before a buy | DERIVED | — | `test_gb30_bot_withdraw` |
| gb31 | Bots do not transfer and do not detour to dodge the tax | DERIVED | `BOT_BANK_TRANSFER` False | `test_gb31_bot_no_transfer` |
| gb32 | One prompt line, only when the mode is on | DERIVED | — | `test_gb32_prompt` |

## Source conflicts

- gb4: TWGS account cap 500,000. Bible and Iago say 100,000. TWGS wins.
- gb8: EIS transfer spends ship credits. Bible says the money leaves your account. EIS wins.
- gb17: Glossary taxes alignment 0 or more. Bible and Iago say positive only. TWGS wins.
- gb18: Glossary and MBBS tax cash over 100,000. Bible and Iago say 50,000. TWGS wins.
- gb19: Glossary and MBBS take 5% of the whole amount. Bible and Iago say 10%. TWGS wins.
- gb22: Glossary pays no alignment when one tax would grant 32,000 or more. REV says the boundary value. TWGS wins.

## Deliberate differences

The tax runs at the day tick, because the engine has no logins. The balance is on the trader's own status at all times. One amount per verb. The displayed-versus-actual tax quirk is not copied. Bank verbs cost no turns. Net worth counts the balance. Economic victory still counts cash on hand. A Ferrengi kill pays the lost cash to the Ferrengi ship. A captured pilot loses his cash to the capturer. Bots bank only when they are already at StarDock.
