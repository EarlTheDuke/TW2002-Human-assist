# Ship towing + Type 2 TransWarp (slice 51, ship-tow-transwarp2-v1)

Status: built behind `K.TOW_MODE` (`"tw2002"` default, `"legacy"` = the post-slice-50 game, pinned).
Code: `src/tw2k/engine/tow.py` (locks, cost, move, break rules, Extern hold, Type 2 shelf, views),
hooks in `runner.py` (`_handle_warp`, `_try_interdict`, `plot_course`, `apply_action`, `tick_day`),
`ship_transwarp.py` (Type 1 drop / Type 2 tow jump), `fleet.py` (Extern hold), `combat.py` (tower death),
`legality.py`, `observation.py`, `prompts.py`, `seat_brain.py` (`_extern_tow`), `web/bot.js`, `web/app.js`.
Tests: `tests/test_ship_tow_v1.py` (+ `test_parity_s4` / `test_parity_s6` verb counts).

## Rules table

| Row | Rule (short) | Status | Source pick | Test |
|---|---|---|---|---|
| tt1 | `Ship.tow_lock` on the tower hull; one lock per hull, one per target; omitted from saves when None | done | cabal tips #4 one-at-a-time | `test_tt1_one_lock_per_target_and_no_chains` |
| tt2 | Any manned hull except `TOW_EXCLUDED_HULLS={"escape_pod"}` tows; no size limit | done (pod UNVERIFIED) | Slice towing stories | `test_tt3_refusals_..._pod_...`, `test_tt6_tow_cost_table...` (IC towed) |
| tt3 | Own unmanned ship in the same sector that you could transport onto; FedSpace OK; fighters aboard `"allow"` | done (SOURCE-CONFLICT: Gypsy TWGS vs Slice v2, TWGS kept) | Gypsy, EIS Navigate | `test_tt3_tow_own_parked_hull_for_zero_turns`, `test_tt3_refusals_...`, `test_tt3_cfs_after_corp_leave_refused`, `test_tt3_unmanned_with_fighters_allow_and_refuse` |
| tt4 | Manned trader: visible, 0 ship fighters, outside FedSpace, not towed / towing, no challenge / Ferrengi encounter; `TOW_MANNED` any/corp_ally/off | done (chain + encounter UNVERIFIED) | MBBS, Iago, Slice | `test_tt4_manned_trader_fighters_fedspace_cloak_switches` |
| tt5 | `tow_engage {target}` / `tow_release {}`; 0 turns; challenge refusal | done (0 turns UNVERIFIED) | EIS Navigate toggle | `test_tt3_tow_own_parked_hull_for_zero_turns`, `test_tt5_fighter_challenge_blocks_engage` |
| tt6 | Cost per sector = tower TPW + 2 x towee TPW, tower only; out of turns refused and hidden | done | Slice turn table, docs wiki | `test_tt6_tow_cost_table_charged_to_the_tower_only` (16/8/11/34), `test_tt6_manned_towee_turns_unchanged...`, `test_tt6_out_of_turns_refused_and_hidden` |
| tt7 | Tower runs the whole `_handle_warp` path; towee follows only if the tower arrived alive | done | EIS Navigate / Gypsy | `test_tt6_manned_towee_turns_unchanged_and_arrives_with_the_tower`, `test_tt9_...` |
| tt8 | Towee takes no entry hazard (NavHaz, mines, limpets, quasar, fighters, toll, photons) | done | EIS Navigate, MBBS, docs wiki photon note | `test_tt8_towee_takes_no_entry_hazard` |
| tt9 | Tower destroyed / podded -> lock gone, towee stays | done | REV, MBBS, EIS | `test_tt9_tower_destroyed_on_entry_leaves_the_towee` |
| tt10 | Interdictor hold charges the tow cost, lock stays | done | Slice (34 turns) | `test_tt10_interdictor_hold_charges_the_tow_cost_and_keeps_the_lock` |
| tt11 | Breaks: land, port, dock, attack (Pre-Lock `"keep"` alt), type1, towee moved, towee gone, fedspace, fed tow, retreat (drop/drag), tower death | done ((f),(i),(j), Police-as-dock UNVERIFIED) | REV 02/28/97 over cabal Pre-Lock | `test_tt11_*`, `test_tt11a_tt13_landing_releases...`, `test_tt11g_towee_sold...`, `test_tt11h_...`, `test_tt11j_retreat_drop_vs_drag`, `test_tt23_...` |
| tt12 | Lock is hull-bound across ship_transport (`"keep_hull"`), dormant while the pilot is away; released when apart | done (UNVERIFIED v2 trick) | Slice "Towing ships with fighters" | `test_tt12_ship_transport_out_leaves_a_dormant_lock_that_resumes`, `test_tt12_dormant_lock_released_when_apart` |
| tt13 | Planet transporter never carries a towee (landing releases first) | done | OldFAQ #6 | `test_tt11a_tt13_landing_releases_so_planet_transport_never_carries_a_towee` |
| tt14 | Towee that cloaks after the lock stays in tow and cloaked | done | cabal tips #1 | `test_tt14_towee_cloaking_after_lock_stays_in_tow_and_cloaked` |
| tt15 | Limpets on the towee follow it; no new limpet on entry | done | fl19 | `test_tt15_limpet_on_towee_follows_it`, `test_tt8_...` |
| tt16 | `transwarp_type2` 20,000 / `transwarp_upgrade` 9,000 at StarDock, TW hulls only | done (TEDIT prices; OldFAQ v2 80k/40k recorded) | cabal twgs.html, docs wiki | `test_tt16_type2_buy_upgrade_and_refusals` |
| tt17 | Type 1 with lock releases (`type1_transwarp`) and jumps alone; legal list `drops_tow` | done | EIS Navigate / HardwareMenu, TWINSTR, Gypsy | `test_tt17_type1_with_lock_drops_the_tow_and_jumps_alone` |
| tt18 | Type 2 without lock == slice 48 Type 1 | done | - | `test_tt18_type2_without_lock_is_type1` |
| tt19 | Type 2 tow jump: 6 ore/hop from the tower, tow cost once (`"tpw"`) / x hops; short ore refuses whole jump; commission lock into FedSpace; manned towee arrived_by_transwarp | done (manned arrived flag UNVERIFIED) | docs wiki, OldFAQ #1 | `test_tt19_*` (4 tests) |
| tt20 | Blind tow jump allowed; fuse -> towee stays (`"destroyed"` alt) | done (UNVERIFIED) | REV | `test_tt20_blind_tow_density0_and_fuse_stays_or_destroyed` |
| tt21 | `ship.transwarp` gains tow_capable / tow_ore_per_hop / max_tow_hops_now for type2 | done | OldFAQ #1 | `test_tt21_observation_type2_block_and_rival_sees_nothing` |
| tt22 | Extern hold: owner aboard a fedsafe manned tower, same sector, lock engaged, not landed -> no repossession; `EXTERN_TOW_HOLD` | done (mapping UNVERIFIED) | cabal tips #4, docs wiki Extern #3 | `test_tt22_extern_hold_keeps_a_locked_spare_overnight`, `test_tt22_extern_hold_fails_without_every_condition`. Decided in slice 64 (cl2): a current corp mate holds too |
| tt23 | run_tows after the hold; Fed tow of the tower releases, ship survived; lock persists to next day; fleet repo_at_extern/extern_hold | done | - | `test_tt23_fed_tow_of_the_tower_releases_but_the_ship_survived`, `test_tt22_extern_hold_keeps...` |
| tt24 | Shipyard "Still Interested" hold not modelled | deliberate | - | - |
| tt25 | Ferrengi treat the tower as any trader; tribute from the tower first; never the unmanned towee | done | slice 49 / 50 | `test_tt25_ferrengi_tribute_from_the_tower_then_release`, slice 50 fl25 tests |
| tt26 | Feds never touch an unmanned towee; Fed tows unchanged apart from tt23 | done | fl25 | `test_tt23_...`, slice 50 fl25 tests |
| tt27 | No universe.rng draws; generator digests unchanged | done | - | `test_tt27_tow_draws_no_rng`, `test_tow_legacy_is_unchanged` |
| tt28 | Type 2 valued like Type 1 at 20,000; towed hull counted once | done | - | `test_tt28_net_worth_counts_type2_like_type1_and_the_towed_hull_once` |
| tt29 | Own-seat `ship.tow`, `in_tow_by`, fleet `in_tow`/`extern_hold`; events to tower + towee + witnesses + spectator | done | - | `test_tt29_events_visible_to_tower_towee_and_witnesses_only`, `test_tt21_...` |
| tt30 | Prompt paragraph under tw2002 only | done | - | `test_tt30_prompt_paragraph_only_under_tw2002` |
| tt31 | Spectator: towee slides after the tower on TOWED, feed lines for engage/release/hold | partial (see differences) | - | manual |
| tt32 | Capture / furbing / corp ships / citadel exchange out of scope | deferred | - | - |

Legal list == handler: `test_legal_list_matches_handler_for_every_advertised_tow_target`.
Bots: `test_bot_locks_its_spare_at_day_end_and_releases_next_morning`, `test_bot_tow_policy_off_and_legacy_no_op`.

## TOW_MODE pin

`K.TOW_MODE = "legacy"` is the post-slice-50 game: no lock, no verbs (handlers answer unsupported), no
`tow_cost` warp param, no Type 2 items, slice 48 TransWarp, every unmanned FedSpace ship repossessed, no
tow observation keys / events / rng draws, prompts unchanged. `test_tow_legacy_is_unchanged` compares
`TOW_LEGACY_GOLDEN` (observation + prompt digests for every seat over a scripted run plus a 3-day tick_day
state digest, seats N3,N2,N1,H) recorded on the slice-50 follow-up commit; slice 48 / 50 legacy pins stay green.

## Bots

`K.BOT_TOW_POLICY = "extern_hold_only"`: the seat brain (N1-N3) only uses tow to keep its own unmanned ship
in FedSpace over Extern (engage at day end beside a `repo_at_extern` ship when it is fedsafe, release next
morning). Bots never tow traders, never buy Type 2. The H heuristic is not tow-aware in this slice.
Day-10 scripted tow use is expected to be about 0.

## Deliberate differences

From the spec:
- "Logged in during Extern" = owner aboard the manned tower, same sector, lock engaged when tick_day runs;
  "fedsafe" = ship fighters <= `FED_TOW_FIGHTER_LIMIT` (alignment only with `TOW_EXTERN_REQUIRE_GOOD`).
- Only the owner can tow / hold his unmanned ships: no corp ships, passwords or corp-mate holds.
- The "Still Interested" shipyard hold over Extern is not modelled.
- tow_engage / tow_release cost 0 turns; escape pods cannot tow; tow chains refused; a target with an open
  challenge / Ferrengi encounter cannot be locked (UNVERIFIED, named constants where switchable).
- Retreat / flee drops the tow by default (`TOW_ON_RETREAT="drop"`, "drag" alternate).
- Lock is hull-bound across ship_transport (`TOW_LOCK_ON_XPORT="keep_hull"`, "release" alternate).
- Pre-Lock is off (`TOW_ON_ATTACK="release"`, REV 02/28/97); "keep" alternate.
- Blind fuse leaves the towee at origin (`TOW_FUSE_TOWEE="stays"`); a manned towee of a TransWarp tow cannot retreat.
- Police HQ verbs at StarDock count as "dock" (`TOW_DOCK_VERBS`).
- Type 2 / upgrade at TEDIT prices 20,000 / 9,000 (not OldFAQ v2 80,000 / 40,000).
- Ferrengi ships cannot be towed (capture deferred); Ferrengi and Feds ignore unmanned towees.
- Bots `extern_hold_only`; ~0 scripted tow use.
- StarDock stays sector 1, so the tips #4 hold happens in FedSpace sector 1.

Added in the build:
- H (heuristic.py) is not tow-aware (left alone so the slice-47 heuristic work is not disturbed); only the
  seat brain runs the Extern hold play.
- Spectator tractor line is approximated: the towee icon slides after the tower on TOWED and the feed shows
  engage / release (with reason) / Extern hold; there is no persistent drawn beam or lock badge.
- Tower death is handled where the hull dies (`combat._destroy_ship_tw2002`, which turns the same Ship
  object into a pod): the lock is released there with reason "tower_destroyed". Any other separation found
  overnight (Fed tow, retreat, flee) is cleaned up by `tow.sweep` after the overnight steps.
- A dormant lock is only possible on a parked tower (pilot transported away) or when the owner boards the
  towee hull; dormant locks never move, never hold at Extern and are released as soon as tower and towee
  are found apart.
- Capture interplay (MBBS addendum #6) is not wired in this slice; slice 52 (ship-capture-v1) wires it on top.

## Planted bugs

38 plants covering all 23 spec bug classes, each planted into a copy of the slice and run against
`tests/test_ship_tow_v1.py` (script `qc_bridge\tow_artifacts\plants_tow.py`, results `plants_final.json`):
**38 / 38 caught**. First pass 29 / 38; the 9 misses were defended twice in the code (landing release both in
the action check and the after-action fallback; legal-list warp choices emptied by the tow check and again by the
toll block; Type 2 shelf gated in both the offer and the buy; Extern hold conditions also enforced by the overnight
sweep) or had no manned / dormant / Class 0 case in the tests. Tests added: manned towee takes no entry hazard,
dormant lock still blocks a second lock, Type 2 refused at a Class 0 port, Extern hold why_not for away / landed,
landing releases so planet_transport never carries a towee; multi-anchor plants knock out every copy of a guard.

## Checks (slice 51 build)

- TOW_MODE pin: `TOW_LEGACY_GOLDEN = cd31a464aee62f982a038546` recorded on 5968646 (origin, slice-50 follow-up, no
  TOW_MODE) and matched by this slice with TOW_MODE flipped to legacy. All-legacy pins unchanged
  (N3,N2,N1,H `00135a9202e44a0e085ce978`; 6 seats `8e1a3a968cef4347d2558a64`); FLEET_MODE + TOW_MODE flipped
  = the slice-50 FLEET-only digest `b9a52b96095f12c7c453151b` (checked on d632aae + follow-up, before the e4a166b rebase; the all-legacy pins run in the suite).
- Scripted match `--seats N3,N3,N2,N2,N1,H --seed 250925 --days 10` (`qc_bridge\tow_artifacts\tow_match.py`):

| Seat | before (5968646) | after (slice 51) |
|---|---|---|
| P1 N3 | 636,759 | 636,759 |
| P2 N3 | 342,314 | 342,314 |
| P3 N2 | 128,173 | 128,173 |
| P4 N2 | 272,058 | 272,058 |
| P5 N1 | 345,875 | 345,875 |
| P6 H | 65,211 | 65,211 |

  Tow engages 0, tow warps 0, tow turns 0, Type 2 buys 0 / upgrades 0, Type 2 tow jumps 0, tow ore 0, Extern holds
  0, Extern repos 0, releases 0, rejected 0, seat exceptions 0, forced stops 0. Expected: under
  `BOT_TOW_POLICY = extern_hold_only` the bots only lock a spare they left in FedSpace, and no seat buys a spare in
  this 10-day run, so the tow code never triggers. The bot play itself is covered by
  `test_bot_locks_its_spare_at_day_end_and_releases_next_morning`.
- Not run in this pass: the spec's (d) tow scenario lab script (its four numbers are covered by unit tests: tt6 turn
  table, tt22 Extern hold over nights, tt19 Type 2 tow jump 24 ore / 16 turns into armid mines, tt17 Type 1 drop) and
  the (e) 30-day headless invariant run.
