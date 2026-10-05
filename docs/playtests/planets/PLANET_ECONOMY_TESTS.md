# Planet economy tests

Slice `planet-economy-hardening-v1`. The first planet-limits tests (`tests/test_planet_economy_limits_v1.py`) let five holes through. The new tests are in `tests/test_planet_economy_hardening_v1.py`. Every one runs the real engine (`apply_action`, `legal_actions`, `tick_day`, `build_observation`) on a class M, K and U world.

No rule changed in this slice. The caps stay the handbook numbers (`PLANET_MAX_COLONISTS`, `PLANET_MAX_STOCK` in `constants.py`, source `S1_planet_handbook_v1.01.html`, CONFIRMED in the limits slice). The only src change is the seat brain in `src/tw2k/agents/seat_brain.py`.

## What each test protects

| test | what it protects | planted bug it catches |
| --- | --- | --- |
| `test_dump_colonists_stops_at_the_cap` | A colonist dump onto a full M, K or U world is refused with `planet colonist cap is N`. Cargo, population, credits, turns and the event log stay put. | (a) M1 the colonist-cap check deleted from `dump_planet_cargo` in `runner.py`. |
| `test_dump_colonists_one_past_the_room_is_refused_and_the_room_is_taken` | With 3 colonists of room, a dump of 4 is refused and a dump of 3 fills the world to the cap exactly. | M12 the dump check off by one (`>=`). Also M1. |
| `test_assign_from_ship_stops_at_the_cap` | A ship-to-pool assign onto a full M, K or U world is refused the same way. | (b) M2 the colonist-cap check deleted from `assign_colonists` in `runner.py`. |
| `test_assign_from_ship_one_past_the_room_is_refused_and_the_room_is_taken` | Room 3: assign 4 refused, assign 3 fills the world exactly. | M2. |
| `test_a_full_world_still_moves_colonists_between_pools_and_back_to_the_ship` | The cap is only on colonists coming from the ship. Pool-to-pool, pool-to-ship and dumping fuel on a full world still work. | M11 the assign check widened to every move into a pool. |
| `test_dump_legal_max_is_the_remaining_room` | The dump legal list offers `min(aboard, room)` colonists; a full world drops colonists from the list and, with nothing else aboard, says `planet is at its class cap`. | (c) M3 `dump_max` ignoring the colonist room; M13 zero-room colonists kept in the list. |
| `test_dump_legal_list_keeps_other_cargo_when_colonists_are_full` | A full colonist pool does not hide fuel in the dump list. | M13. |
| `test_assign_legal_max_is_the_remaining_room` | The assign legal list offers `min(aboard, room)` from the ship; a full world drops `ship` from the choices and the max. | (d) M4 `ship_room` ignoring the room. |
| `test_assign_list_offers_only_the_pools_when_the_colonists_sit_in_a_pool` | A full world with the colonists in a product pool still lists that pool, not the ship. | M4. |
| `test_over_cap_world_is_not_shrunk` | One `tick_day` on a world over its colonist and stock caps leaves every colonist pool, fuel and equipment exactly as they were; organics lose only the normal burn. | (e) M6 stock room going negative, M10 production clamping stock to the cap, M18 growth ignoring the cap, M19 growth clamping an over-cap population to the cap. |
| `test_over_cap_world_stays_put_over_several_days` | Three day ticks with plenty of organics: an over-cap population stays the same. | (e) M19, M18. |
| `test_full_world_is_not_an_unload_landing` | After the landed legal list shows no ship room, the N2 ladder does not land on that world to unload (M, K, U). | M7 the brain fix reverted. |
| `test_a_world_with_room_is_still_an_unload_landing` | The same setup with 500 colonists of room still lands to unload, so the fix does not just switch landing off. | Guard against an over-wide fix. |
| `test_the_ladder_does_not_ferry_colonists_to_a_full_home` | One hop away with colonists aboard, the ladder plots no "ferry colonists home" to a full home, and does plot it when there is room. | M16 the ferry plot left in. |
| `test_a_world_that_gets_room_again_is_forgotten_as_full` | When the legal list shows room again, the world leaves the full list. | M15 the brain never forgetting a full world. |
| `test_the_full_world_note_survives_a_memory_round_trip` | The full-world note is kept in the seat memory dump. | M17 the note dropped from the dump. |
| `test_stock_is_priced_at_the_published_base` (limits file) | Stock uses the published base: fuel 179, organics 389, equipment 719. | M8 the stock price flattened to 179 for every good. |
| `test_handbook_numbers_are_the_caps`, `test_sixth_planet_is_refused_and_pays_nothing`, `test_transwarp_into_a_full_sector_stays_put` (limits file) | The cap table is the handbook; a sixth planet in a sector is refused by genesis and by transwarp. | M9 `PLANETS_PER_SECTOR_CAP = 6` (all three fail); M14 class U cap 3000 edited to 3500. |

## The brain fix

On seed 250925 the home world (planet 32) is class U, cap 3000 colonists. Before the fix the N2 ladder landed on it 413 times in the day-10 replay after it was full, and kept plotting "ferry colonists home".

`SeatBrain` now notes a world as full when it is landed there with colonists aboard and the fogged legal list has no `ship` in `assign_colonists.from` or a ship max of 0. It forgets the note when the legal list shows room again. The note is kept in the seat memory dump. For a full world:

* `_land_home` does not land just to unload colonists. Citadel, organics delivery, stock loading and unsellable-goods landings still happen.
* The "ferry colonists home" plot is skipped when the home world is full.
* `_colonists_needed` is 0 for a full home, so the ladder stops buying colonists for it.

Only the landed legal list is read. No hidden number and no cap table is used by the brain.

The second and third points go a little past "do not queue the land step". With the land step alone the ladder still bought colonists and flew them home without landing, so it did not carry on trading (N1 627,737, N2 612,323 on seed 250925, the same 15,414 gap as before).

## N2 against N1, day 10 (fogged replay, `prove_growth_replay`, rejected 0 on every run)

| seed | N1 before | N2 before | N1 after | N2 after | N2 - N1 after |
| --- | --- | --- | --- | --- | --- |
| 250925 | 631,873 | 616,459 | 3,991,509 | 3,976,330 | -15,179 |
| 20260925 | 665,018 | 2,221,042 | 665,018 | 2,221,042 | +1,556,024 |
| 230923 | 706,531 | 5,995,548 | 706,531 | 5,995,548 | +5,289,017 |
| 99 | 806,309 | 3,905,412 | 806,309 | 3,905,412 | +3,099,103 |
| 31 | 741,206 | 3,342,509 | 741,206 | 3,342,509 | +2,601,303 |

"Before" is HEAD 9204776. Only seed 250925 moves, because only that seed has a full home world in the window. The fix takes the home landings from 413 to 63 for both brains (the 63 are the unloads before the world fills) and trades from about 67 to about 460, so both brains gain about 3.36 million.

## Deliberate tolerance (seed 250925)

N2 is still 15,179 behind N1 on seed 250925 after the fix (3,976,330 against 3,991,509, 0.38 percent). Commander's decision: `test_n2_day10_beats_n1_and_keeps_organics` keeps the strict "N2 beats N1" rule on seeds 20260925, 230923, 99 and 31, and on seed 250925 only it requires N2 >= 0.99 x N1. The organics check (held zero planets) and rejected 0 are unchanged.

The cause, measured from the action logs and end state of the two replays: the fix takes the full-world loss away from both brains equally, so what is left is the N2 organics rule. N2 spends 2 extra turns moving idle colonists to the organics pool ("class U needs 750", then "needs 49") and splits its ship unloads between organics and fuel ore. At day 10 planet 32 has 2,264 fuel workers and 633 organics workers under N1, 1,405 and 1,544 under N2. On this class U world organics hit 0 under both brains anyway (zero planet 32 for both), so the organics workers add nothing. Credits are 3,643,691 (N1) against 3,638,357 (N2), a 5,334 gap from two fewer trades (460 against 458), and fuel stock on planet 32 is 147 against 92 units, 55 x 179 = 9,845 of planet value. 5,334 + 9,845 = 15,179. Planet 33 is identical under both brains.

Closing the gap means changing the N2 organics rule for class U worlds, which is outside this slice. Tracked for the bot-growth-and-fixes slice.

The jump of both brains on seed 250925 from about 0.63 million to about 3.99 million (table above) is the replay trading instead of landing. Whether millions at day 10 is the right scale belongs to economy-calibration-v1, not to this slice.

Proof the tolerance is not lazy: with the brain fix reverted (land to unload on a full world again) or with N2's result cut by 3 percent on seed 250925, the test fails. See the last rows of the planted-bug table.

## Planted bugs

Run in a separate worktree, each bug put back after its run. Caught means at least one test in the two planet-economy test files failed.

| bug | caught | by |
| --- | --- | --- |
| M1 dump handler colonist cap removed | yes | `test_dump_colonists_stops_at_the_cap` |
| M2 assign handler (ship to pool) colonist cap removed | yes | `test_assign_from_ship_stops_at_the_cap` |
| M3 dump legal list ignores colonist room | yes | `test_dump_legal_max_is_the_remaining_room` |
| M4 assign legal list ignores room (`ship_room`) | yes | `test_assign_legal_max_is_the_remaining_room`, old `test_class_u_unload_stops_at_3000` |
| M5 `planet_colonist_room` without `max(0, ...)` | no | Equivalent bug: growth only runs when growth > 0 and the list and handlers already treat a negative room as no room, so nothing a player can see changes. Replaced by M19. |
| M6 `planet_stock_room` without `max(0, ...)` | yes | `test_over_cap_world_is_not_shrunk` |
| M7 brain fix reverted | yes | `test_full_world_is_not_an_unload_landing` |
| M8 stock price flattened | yes | `test_stock_is_priced_at_the_published_base` |
| M9 sector cap of 6 | yes | `test_handbook_numbers_are_the_caps`, `test_sixth_planet_is_refused_and_pays_nothing`, `test_transwarp_into_a_full_sector_stays_put` |
| M10 production clamps over-cap stock to the cap | yes | `test_over_cap_world_is_not_shrunk`, old `test_legacy_mode_still_grows_past_the_cap` |
| M11 assign cap blocks pool-to-pool moves | yes | `test_a_full_world_still_moves_colonists_between_pools_and_back_to_the_ship` |
| M12 dump cap off by one | yes | `test_dump_colonists_one_past_the_room_is_refused_and_the_room_is_taken` |
| M13 dump legal list keeps zero-room colonists | yes | `test_dump_legal_max_is_the_remaining_room` |
| M14 class U cap 3000 to 3500 | yes | `test_handbook_numbers_are_the_caps` |
| M15 brain never forgets a full world | yes | `test_a_world_that_gets_room_again_is_forgotten_as_full` |
| M16 ferry plot to a full home left in | yes | `test_the_ladder_does_not_ferry_colonists_to_a_full_home` |
| M17 full-world note dropped from the memory dump | yes | `test_the_full_world_note_survives_a_memory_round_trip` |
| M18 growth ignores the cap | yes | `test_over_cap_world_is_not_shrunk`, old `test_production_and_growth_stop_at_the_cap` |
| M19 growth clamps an over-cap population to the cap | yes | `test_over_cap_world_is_not_shrunk` |

18 of 19 caught; the one miss (M5) changes no behaviour.

Tolerance check, run against `test_n2_day10_beats_n1_and_keeps_organics` with the 1% rule in place:

| bug | test result | seed 250925 N1 / N2 |
| --- | --- | --- |
| T1 land-step fix reverted (M7) | fails (caught) | 3,559,118 / 2,011,593 |
| T2 whole brain fix reverted (`seat_brain.py` at 9204776) | fails (caught) | 631,873 / 616,459 (97.6%) |
| T3 N2 net worth cut 3% on 250925 | fails (caught) | 3,991,509 / 3,857,040 |
| T4 control: N2 cut 0.5% on 250925 | passes, as it should (inside 1%) | |
