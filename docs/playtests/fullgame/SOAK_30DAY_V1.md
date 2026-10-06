# SOAK_30DAY_V1 - 30-day invariant soak (code bots) + late-game speed-up

Seats N3,N3,N2,N2,N1,H (scripts/run_scripted_match.py), 30 days, PYTHONHASHSEED=0, default modes (all *_MODE = tw2002).
Soak harness: a wrapper around `run_match` that checks invariants after every action and day tick (cheap checks every step, a full universe walk every 3000 steps and at every day tick), then saves at day 15 and replays 5 days from the save. Code: origin e63e827 plus the harness's save.py; the soak itself changed no engine code.

Invariants checked: negative credits/cargo/turns/mines/fighters/navhaz/ship fields/port fields/planet stockpiles, cargo over holds, turns out of range, one sector per player, player in own sector's occupants, occupant/sector mismatch, duplicate occupants, ship id twice / shared ship objects, parked ships (owner, sector, fleet id), tow/lock pairs (towee present, engaged lock in the same sector, target locked twice, no lock under legacy), drive values and drives on non-TW hulls, planet sector mismatch, limpet targets, Ferrengi (in FedSpace, bad sector, negative fields), engine exceptions in apply_action and tick_day.

## Soak results

| | seed 250925 | seed 777 |
|---|---|---|
| actions | 31,439 | 34,912 |
| full checks | 68 | 69 |
| invariant violations | 0 | 0 |
| seat exceptions | 0 | 0 |
| engine rejects | 0 | 0 |
| validate rejects | 0 | 0 |
| forced_done | 0 | 0 |
| deaths | P3 x3 | P4 x2, P5 x2 |
| net worth P1..P6 | 2,267,134 / 1,846,573 / 1,349,326 / 1,505,353 / 918,732 / 120,467 | 2,118,721 / 2,174,073 / 2,347,155 / 1,225,549 / 1,659,867 / 169,344 |
| save at day 15: save_universe -> load_universe | identical | identical |
| save round-trip bytes / state | identical / identical | identical / identical |
| 5-day replay from save (entries) | 4,792 | 5,177 |
| wall time (s), whole run | 5590 | 6326 |

Result: 0 violations, 0 seat exceptions, 0 engine or validate rejects, 0 forced turns in both runs; save/load through `save_universe`/`load_universe` is identical.

Findings (not fixed here, no gameplay effect in this soak):

- A bare `Universe.model_dump()` round-trip is NOT a full save: `Universe._rng` and `_firsts_seen` are pydantic PrivateAttrs and are not dumped (replay from a bare dump diverges, with or without re-seeding the RNG). The real save path (`save_universe`/`load_universe`) carries them and replays identically.
- `known_sectors` (a set) comes back in a different iteration order after a round-trip; harmless (nothing iterates it order-sensitively).
- `test_ship_hardware_v2_qc::test_free_port_skips_reserved_live_range` depends on which local ports are free (env-dependent).
- The run gets much slower per day as the game goes on (next section).

## Late-game slowdown

Per-day wall time in the soak (seconds per day tick, original code):

- seed 250925: 30, 41, 52, 64, 74, 90, 84, 90, 115, 149, 143, 186, 168, 166, 182, 183, 171, 181, 184, 194, 202, 216, 239, 293, 327, 437, 460, 468
- seed 777: 40, 65, 60, 77, 108, 117, 126, 141, 141, 180, 185, 164, 166, 182, 194, 200, 207, 220, 221, 213, 249, 300, 396, 469, 479, 446, 302, 317

Profile, first 8 days, seed 250925 (cProfile, 9,619 steps, 1,112 s): `build_observation` 641 s cumulative; inside it `_event_visible_to` was called 115.9 million times (348 s) because every observation rescanned the whole event feed twice (rival last-seen and orphaned planets) and the feed grows all game; function-local `from . import constants` in the hot path cost another ~45 s; `apply_action` spent 59 s tottime rebuilding `result.event_seqs` by scanning the whole feed after every action. The rest is the seat bots (`seat_brain._distances_from`, `_nav_graph`), which is bot cost, not engine cost.

## Fix (pure performance, no behaviour change)

- `engine/observation.py`: an append-only index of the event feed, built incrementally (`_FeedIndex`: positions of located events and of PLANET_ORPHANED). Per viewer it keeps (`_SeenIndex`) each rival's newest event split into three lists: always-visible, cloak-trail (WARP/RETREAT/AUTOPILOT/CLOAK_ON/CLOAK_OFF/NAVHAZ_HIT/ATOMIC_DETONATOR, visible only while the actor is not cloaked under tw2002 hardware) and live (corp/alliance events whose visibility can change later, re-checked with `_event_visible_to` on every read). `_rival_last_seen` and `_orphan_former_owners` read the index instead of the whole feed. The index is keyed by the feed list object and is rebuilt if the feed is replaced, truncated or its tail changes (save/load, tests), and per viewer it is rebuilt if HARDWARE_MODE or PLANET_TRADE_FEED changes. `_event_visible_to` was split into the cloak gate + `_event_visible_base`, and the constants import moved to module level.
- `engine/runner.py`: `_seqs_after(events, before_seq)` walks back from the feed tail (seqs are strictly increasing because `Universe.emit` is the only writer) instead of filtering the whole feed.
- Part 2 (found by profiling days 26-30 of the part-1 code: `_action_hint` was 235 s of 979 s, 43 ms per observation, because the per-turn death-history hint scanned the whole feed for SHIP_DESTROYED events of the viewer once the viewer had died): the feed index also records SHIP_DESTROYED positions and `_deaths_of(universe, player_id)` filters only those by victim (oldest first, same list as before).
- Test: `tests/test_feed_index_v1.py` (randomised property test against the old full scans while cloaks, corps, alliances, HARDWARE_MODE and PLANET_TRADE_FEED change; death-history list equal to the full scan; feed replaced/truncated is re-indexed; each new event is classified once; `_seqs_after` equals the full filter). The test catches all 4 hand-made mutants of part 1 and all 3 of part 2.

## Identical results (same-seed digests)

Digest harness (`run_match` with every observation JSON, every action + result, end-of-day universe state, the match result and the final event feed hashed into a per-day sha256). `legacy` = every *_MODE flipped to legacy (on 04a61be that includes FED_OUTPOST_MODE; on 086972d all modes then present).

| code | mode | seed | days | base digest | fix digest | per-day digests |
|---|---|---|---|---|---|---|
| 086972d | tw2002 | 250925 | 30 | f42225d933cc0ec8 | f42225d933cc0ec8 | identical (29/29) |
| 086972d | tw2002 | 777 | 30 | 6e1ff6a92793f3d7 | 6e1ff6a92793f3d7 | identical (29/29) |
| 086972d | legacy | 250925 | 30 | 5d4e9d12de05af9e | 5d4e9d12de05af9e | identical (29/29) |
| 086972d, parts 1+2 | tw2002 | 250925 | 30 | f42225d933cc0ec8 | f42225d933cc0ec8 | identical (29/29) |
| 086972d, parts 1+2 | tw2002 | 777 | 30 | 6e1ff6a92793f3d7 | 6e1ff6a92793f3d7 | identical (29/29) |
| 086972d, parts 1+2 | legacy | 250925 | 30 | 5d4e9d12de05af9e | 5d4e9d12de05af9e | identical (29/29) |
| 04a61be, part 1 | tw2002 | 250925 | 10 | 860381ddaabfb096 | 860381ddaabfb096 | identical (9/9) |
| 04a61be, part 1 | tw2002 | 777 | 10 | fb4058d4ce99c599 | fb4058d4ce99c599 | identical (9/9) |
| 04a61be, part 1 | legacy | 250925 | 10 | 7acf3cb766ed25a2 | 7acf3cb766ed25a2 | identical (9/9) |
| 04a61be, part 1 | legacy | 777 | 10 | 27cf4d620c9f67a3 | 27cf4d620c9f67a3 | identical (9/9) |
| 04a61be, parts 1+2 | tw2002 | 250925 | 10 | 860381ddaabfb096 | 860381ddaabfb096 | identical (9/9) |
| 04a61be, parts 1+2 | legacy | 250925 | 10 | 7acf3cb766ed25a2 | 7acf3cb766ed25a2 | identical (9/9) |

Rows marked 086972d use the pre-04a61be base (its 30-day baselines were already running when origin moved); the 04a61be rows are the code this lands on, with FED_OUTPOST_MODE flipped together with every other mode in the legacy runs.

## Timing before/after

Same harness, same box (8 vCPU, shared with the other runs, so absolute numbers are inflated for both columns), seconds per day tick.

| run | days 1-5 avg before / after (s) | days 25-29 avg before / after (s) | 30-day total before / after (s) |
|---|---|---|---|
| tw2002 250925 | 38 / 44 | 445 / 68 | 7391 / 1959 (3.8x) |
| tw2002 777 | 37 / 44 | 487 / 73 | 7497 / 1969 (3.8x) |
| legacy 250925 | 23 / 21 | 343 / 36 | 4940 / 1144 (4.3x) |

'after' = parts 1+2 (the pushed code). Before, the per-day cost grew roughly with the length of the event feed; after, late days cost about what mid-game days do, and what remains is mostly the seat bots' own route planning (`seat_brain._distances_from`, `_nav_graph`, `port_report`). Runs overlapped with up to 10 others on the box, so single days are noisy (both columns); the before runs were also the ones running longest under that load.

**tw2002, seed 250925, 30 days**

| day | before (s) | part 1 (s) | parts 1+2 (s) |
|---|---|---|---|
| 1 | 16 | 12 | 18 |
| 2 | 27 | 18 | 34 |
| 3 | 37 | 22 | 50 |
| 4 | 52 | 31 | 59 |
| 5 | 56 | 31 | 57 |
| 6 | 40 | 23 | 42 |
| 7 | 85 | 45 | 79 |
| 8 | 99 | 46 | 70 |
| 9 | 113 | 49 | 74 |
| 10 | 125 | 50 | 76 |
| 11 | 136 | 54 | 76 |
| 12 | 150 | 55 | 91 |
| 13 | 136 | 48 | 69 |
| 14 | 172 | 57 | 81 |
| 15 | 185 | 61 | 85 |
| 16 | 500 | 61 | 80 |
| 17 | 449 | 61 | 80 |
| 18 | 420 | 62 | 81 |
| 19 | 454 | 68 | 93 |
| 20 | 275 | 47 | 55 |
| 21 | 464 | 69 | 77 |
| 22 | 379 | 58 | 60 |
| 23 | 382 | 58 | 64 |
| 24 | 415 | 188 | 70 |
| 25 | 474 | 132 | 75 |
| 26 | 440 | 115 | 73 |
| 27 | 427 | 112 | 60 |
| 28 | 427 | 117 | 63 |
| 29 | 455 | 124 | 68 |
| total | 7391 | 1875 | 1959 |

**tw2002, seed 777, 30 days**

| day | before (s) | part 1 (s) | parts 1+2 (s) |
|---|---|---|---|
| 1 | 19 | 13 | 25 |
| 2 | 27 | 17 | 32 |
| 3 | 40 | 25 | 53 |
| 4 | 46 | 26 | 47 |
| 5 | 56 | 30 | 60 |
| 6 | 74 | 40 | 69 |
| 7 | 91 | 45 | 72 |
| 8 | 91 | 41 | 61 |
| 9 | 121 | 52 | 79 |
| 10 | 127 | 52 | 73 |
| 11 | 117 | 46 | 67 |
| 12 | 124 | 46 | 74 |
| 13 | 135 | 51 | 69 |
| 14 | 149 | 52 | 73 |
| 15 | 161 | 56 | 74 |
| 16 | 400 | 59 | 73 |
| 17 | 350 | 60 | 75 |
| 18 | 387 | 65 | 77 |
| 19 | 387 | 66 | 76 |
| 20 | 412 | 66 | 76 |
| 21 | 394 | 69 | 76 |
| 22 | 430 | 68 | 74 |
| 23 | 453 | 70 | 75 |
| 24 | 472 | 235 | 75 |
| 25 | 517 | 132 | 75 |
| 26 | 474 | 131 | 78 |
| 27 | 471 | 129 | 70 |
| 28 | 478 | 131 | 67 |
| 29 | 495 | 153 | 73 |
| total | 7497 | 2028 | 1969 |

**legacy, seed 250925, 30 days**

| day | before (s) | part 1 (s) | parts 1+2 (s) |
|---|---|---|---|
| 1 | 11 | 8 | 13 |
| 2 | 17 | 10 | 16 |
| 3 | 24 | 13 | 21 |
| 4 | 28 | 14 | 23 |
| 5 | 37 | 18 | 34 |
| 6 | 45 | 19 | 30 |
| 7 | 52 | 22 | 33 |
| 8 | 51 | 22 | 32 |
| 9 | 63 | 26 | 38 |
| 10 | 74 | 27 | 40 |
| 11 | 80 | 28 | 41 |
| 12 | 83 | 29 | 42 |
| 13 | 89 | 32 | 50 |
| 14 | 102 | 33 | 44 |
| 15 | 110 | 33 | 59 |
| 16 | 117 | 38 | 56 |
| 17 | 122 | 37 | 46 |
| 18 | 139 | 45 | 51 |
| 19 | 162 | 50 | 51 |
| 20 | 430 | 54 | 55 |
| 21 | 359 | 53 | 54 |
| 22 | 413 | 59 | 57 |
| 23 | 320 | 48 | 45 |
| 24 | 299 | 38 | 33 |
| 25 | 328 | 48 | 35 |
| 26 | 334 | 45 | 36 |
| 27 | 344 | 43 | 35 |
| 28 | 376 | 46 | 38 |
| 29 | 329 | 47 | 35 |
| total | 4940 | 983 | 1144 |

Original soak harness, seed 250925 (invariant checks on): whole run 5,590 s before, 4,028 s with an earlier draft of the observation change (last day 468 s before, 158 s after); identical results.

