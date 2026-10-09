# Bots use the tavern

Slice 67. `BOTS_TAVERN_MODE` is `tw2002` or `legacy`. The engine switch stays `TAVERN_MODE`. Legacy seats do not ask Grimy and do not enter the Underground.

N2, N3, and H may ask. N1 does not.

A trace (`grimy_ask` topic `trader`) happens only while the seat is hunting a rival or choosing a trade lane, at most once each 10 days, only when the credits left after the price stay at or above 20,000, and only when the buy keeps tavern spend under 2% of trading profit so far. A seat that is due and cannot afford the trace says a free word instead. A good seat does not buy the Underground password. An evil seat buys it only when cash on hand is more than twice the password price, then enters. The password is not written into the thought.

## Bars

Rejected 0/0. Save identical. Tavern spend stays under 2% of that seat's trading profit over 30 days. No seat goes broke from a tavern buy. Each N3 seat uses the tavern at least once in a 10-day match.

Seed 250925, 10 days, digest `1551f49e`, 370s, rejected 0/0, save identical, tavern spend 0. Both N3 seats, both N2 seats, and H each said one free word. N1 did not. Profit on that day-10 was still under the line for a paid trace on the weaker seats, and the first visit used the free word, so nobody paid.

Seed 250925, 30 days, digest `f7598cee`, 1085s, rejected 0/0, save identical, ferrengi 263000, tavern spend 0. Kinds were free words only. No paid trace, no password, no Underground entry. P3 and P6 ended at 0 credits after deaths. The bank broke flag is 0 on every seat, and neither of those seats paid for a visit.

| Seat | tavern_talk | spend | realized profit | credits | deaths | broke |
| --- | --- | --- | --- | --- | --- | --- |
| N3-P1 | 3 | 0 | 2,783,081 | 608,704 | 0 | 0 |
| N3-P2 | 2 | 0 | 135,260 | 72,990 | 0 | 0 |
| N2-P3 | 3 | 0 | 246,882 | 0 | 23 | 0 |
| N2-P4 | 1 | 0 | 102,873 | 70,786 | 0 | 0 |
| N1-P5 | 0 | 0 | 835,673 | 169,608 | 3 | 0 |
| H-P6 | 3 | 0 | 845,079 | 0 | 5 | 0 |

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

Re-break on `2d40199` caught pb1 through pb17. Each named test failed, and the source was restored.
