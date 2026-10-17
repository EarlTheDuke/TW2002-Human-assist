# v311-profile-v1 soak (COMMANDER NOTE 57 item 9)

`python scripts/v311_soak.py --seed 250925 --days 10 --day-seconds 60 --size 1000`

The real app runs in the script's own process on a free port in 8020-8030 (8020 here) and plays one match: seed 250925, 1,000 sectors, 10 days, Ferrengi and planets on, four code bots (the server's heuristic seats P1-P4). `V311_PROFILE = "v311"` is set only in that process; the stored default stays `legacy`.

Clock: RULINGS s5 gives turns back over 24 real hours. The script sets `TURN_REGEN_DAY_SECONDS` to 60, so one game day is 60 s of the turn clock (one "hour" is 2.5 s), and the live-pace day roll follows it. Everything else runs at normal speed. Day 1 rolls as soon as every seat has spent its 250 opening turns (there is no earlier day mark), so day 1 has no regen.

## Result (after the fix below)

`soak_250925.json`, `soak_250925.md`. 542.6 s wall clock, days 1-10 played (status finished, day 11 reached).

| seat | credits | net worth | ship | actions ok | rejected | regen turns | taxes paid | deaths | citadel |
|---|---|---|---|---|---|---|---|---|---|
| P1 | 15,723 | 2,214,779 | Merchant Cruiser | 1,400 | 0 | 2,253 | 5,384 | 0 | class M L0 |
| P2 | 34,735 | 2,085,223 | Merchant Cruiser | 1,401 | 0 | 2,253 | 16,096 | 0 | class M L0 |
| P3 | 0 | 1,935,697 | escape pod | 1,494 | 0 | 2,253 | 0 | 1 | class M L0 |
| P4 | 26,560 | 2,085,836 | Merchant Cruiser | 1,439 | 0 | 2,253 | 0 | 0 | class M L0 |

- Rejected 0 on every seat. Exceptions 0 (apply_action wrapper plus every log record with an exception).
- Turn regen: exactly 250 per seat on each of days 2-10 (251 on day 9 from the carried fraction), 2,253 in all. No midnight refill; the cap held.
- Tax (RULINGS s7, 10% at 50,000 or more, good alignment): P2 paid 5,248 / 5,246 / 5,602 on days 5-7, P1 paid 5,384 on day 9. Each seat paid at most once a day.
- Citadels: none started. The heuristic bot has no citadel step. Also, under the profile `CLASS_M_FIDELITY_MODE` makes a class M L1 need 1,000,000 colonists, and the free start planet has 191,000, so no seat could start L1 without hauling colonists. Class M ratios are Ben's call (NOTE 41 item 10).
- Offensive waves: 0. No seat left offensive fighters, so the RULINGS s6 wave did not come up in play. `tests/test_v311_rulings_v1.py::test_s6_offensive_wave_cap` covers it.
- Net worth: about 1.94 million at the start for every seat. Under the profile the free class M planet's 191,000 colonists count in net worth. The profile ranks by experience (`EXP_SCORE_MODE`, `PLANET_VALUE_SCORE_MODE` experience), and experience ends at 541-572.
- P3 lost its Merchant Cruiser on day 10 and ends in an escape pod with 0 credits on hand. This script does not record the cause.

## The stall (MASTER_PLAN DAY-g, "code bots stall by day 2")

`soak_250925_before_fix.json`, `soak_250925_before_fix.md`: the same command before the fix. Rejected 0 and exceptions 0, but from day 2 every bot spent about 246 of its 250 daily turns on `wait` (2,222 waits for P3 in 10 days), and credits stayed between 9,405 and 23,054.

Where and why: a 3-day diagnostic run that logged each wait's reason gave one reason for all 486-488 waits per seat: "Not enough turns left for a warp; waiting for tomorrow." With hourly regen, turns come back one at a time. The scheduler's day-done check (`_is_day_done` in src/tw2k/server/runner.py) kept a seat active while it had 1 turn, because a trade costs 1. The heuristic bot could not warp with 1 turn (a warp costs 3), so it waited, and the wait spent the turn that had just come back. Turns never pooled to 3, so no seat warped again.

Fix (small): with turn regen live, a seat short of a warp counts as done for now, and acts again once the clock has given back enough turns. With turn regen off, the old check is unchanged. After the fix the same seed has 0 waits, 390-419 trades per seat, and 2 seats paying tax. `tests/test_v311_rulings_v1.py::test_s5_a_seat_short_of_a_warp_rests_until_turns_pool` covers it.

Two more turn-clock fixes landed with item 4, before either soak: the scheduler's `recover_turns` and `apply_action`'s `refresh_offline_turns` used to both pay the same seconds, and `recover_turns` floored each call, so calls a fraction of a second apart paid nothing. Both now share one clock. Under live pace with turn regen, a day also rolls no sooner than `TURN_REGEN_DAY_SECONDS` after the last one.
