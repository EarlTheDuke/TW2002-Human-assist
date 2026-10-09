# Bots use the tavern

Slice 67. `BOTS_TAVERN_MODE` is `tw2002` or `legacy`. The engine switch stays `TAVERN_MODE`. Legacy seats do not ask Grimy and do not enter the Underground.

N2, N3, and H may ask. N1 does not.

A trace (`grimy_ask` topic `trader`) happens only while the seat is hunting a rival or choosing a trade lane, at most once each 10 days, only when the credits left after the price stay at or above 20,000, and only when the buy keeps tavern spend under 2% of trading profit so far. Lifetime trading profit is summed from sell events because trade_summary only covers the last 50 sells. When income fits but the ship purse is thin, the seat withdraws the shortfall from the bank and does not burn the visit on a free word. A free word is only for a visit whose paid trace would break the 2% spend bar, and it uses its own day stamp so it does not block a later paid ask. A good seat does not buy the Underground password. An evil seat buys it only when cash on hand is more than twice the password price, then enters. The password is not written into the thought.

## Bars

Rejected 0/0. Save identical. Tavern spend stays under 2% of that seat's trading profit over 30 days. No seat goes broke from a tavern buy. Each N3 seat uses the tavern at least once in a 10-day match.

Seed 250925, 10 days, digest `74436df2`, rejected 0/0, save identical. N3-P1 asked Grimy once and said one free word; spend 3,000 (0.39% of 772,146 profit). N3-P2 said one free word (profit 120,885 still under the paid line). N2-P3, N2-P4, and H each said one free word. N1 did not.

Seed 250925, 30 days, digest fd9f23bb, rejected 0/0, save identical, ferrengi 335163. N3-P1 paid 9,000 across 3 Grimy asks (0.30% of 2,995,880 profit) and said one free word. N3-P2 said 2 free words (profit 130,105 stayed under the paid line). N2 and H used free words only. N1 did not. No seat spent tavern cash into broke.

| Seat | grimy_ask | tavern_talk | spend | realized profit | spend % |
| --- | --- | --- | --- | --- | --- |
| N3-P1 | 3 | 1 | 9,000 | 2,995,880 | 0.30 |
| N3-P2 | 0 | 2 | 0 | 130,105 | 0 |
| N2-P3 | 0 | 2 | 0 | 178,216 | 0 |
| N2-P4 | 0 | 3 | 0 | 103,923 | 0 |
| N1-P5 | 0 | 0 | 0 | 1,044,348 | 0 |
| H-P6 | 0 | 2 | 0 | 578,202 | 0 |

Seed 4242, 10 days, digest 2072faf0, rejected 0/0, save identical. N3-P1 paid 3,000 (0.59%) and talked once. N3-P2 talked once. N2-P3 and H each paid 3,000. N1 did not.

Seed 4242, 30 days, digest 87410f69, rejected 0/0, save identical. N3-P1 spend 6,000 (0.40%). N3-P2 free words only. N2-P3 spend 6,000 (0.26%). H spend 6,000 (0.60%). N1 none. All under 2%.

## Planted bugs

| Bug | Test |
| --- | --- |
| pb1 legacy still asks | `test_bt1_mode` |
| pb2 N1 asks | `test_bt2_skill` |
| pb3 a trace with no hunt and no lane | `test_bt3_reason` |
| pb4 a trace that leaves the seat broke | `test_bt4_broke` |
| pb5 a second trace the same day | `test_bt5_once` |
| pb6 a trace inside the 10-day gap | `test_bt6_gap` |
| pb7 a good seat buys the password | `test_bt7_alignment` |
| pb8 cash equal to twice the price still joins | `test_bt8_cash` |
| pb9 the password is in the thought | `test_bt9_thought` |
| pb10 an N3 with a rival does not trace | `test_bt10_n3_traces` |
| pb11 the reserve is ignored | `test_bt11_reserve` |
| pb12 N2 traces with no lane | `test_bt12_n2_picks_a_lane` |
| pb13 a known password is bought again | `test_bt13_known_password` |
| pb14 the entered word is in the thought | `test_bt14_enter_hides_the_word` |
| pb15 the note omits the mode or the spend bar | `test_bt15_docs` |
| pb16 a trace at exactly 2% of profit still goes through | `test_bt16_trace_fits_income` |
| pb17 a free word is held until day 8 | `test_bt17_early_day_still_says_a_word` |
| pb18 income fits but a thin purse does not withdraw | `test_bt18_withdraws_for_a_trace` |
| pb19 a thin purse with an empty bank still talks | `test_bt19_waits_when_the_bank_is_empty` |
| pb20 a free word blocks a later paid trace | `test_bt20_free_word_does_not_block_a_trace` |

Re-break on `2d40199` caught pb1 through pb17. Each named test failed, and the source was restored. pb18 through pb20 land with the bank-withdraw, free-word gap split, and lifetime income fix and are re-broken on that tip.
