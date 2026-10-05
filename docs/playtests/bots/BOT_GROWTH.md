# Bot growth and fixes

Slice `bot-growth-and-fixes-v1`. Trigger: Commander's scripted 10-day match
(`C:\Users\sugar\qc_bridge\match_report_20261004.md`).

## What changed

- Rich N2/N3 seats (fogged credits past `RICH_CREDITS` / `DEFENSE_CASH_GATE`) buy a
  tougher hull from the StarDock legal list, then shields and fighters, before
  hauling millions through Ferrengi space.
- N2/N3 raise `target_planets` above 2 from fogged cash the same way N3 already did.
- Sectors where the seat has seen Ferrengi are remembered in scratchpad
  (`hot_sectors`). Under-armed rich seats prefer other warps.
- Genesis refused for "sector already holds 5 planets" warps out instead of stalling.
- Coeff-1 organics (K/U) cannot surplus-feed: skip the labor reshuffle, skip them
  as organics-import targets, and only park a tiny organics crew on unload. That
  restores the trade turns that let N2 beat N1 under the 26/56/102 price table.
- HeuristicAgent: builds on escape-pods QC (pod trade-in, fighter buy capped at
  hull room, `WAIT` when short of warp turns). Adds deterministic seed, no
  immediate reverse-warp, and least-visited preference so the 203<->270 loop dies.

## Third death (tw2002 pods)

Default `DEATH_MODE = "tw2002"` (see `docs/playtests/combat/DEATH_ESCAPE_PODS.md`).
A ship loss becomes an escape pod when the hull has a pod and the seat has used
fewer than `PODS_PER_DAY` (2) pods today. The **third loss in the same day** is
Ship Destroyed (`#SD#`): out of turns until midnight, then a free Scout Marauder
at StarDock. There is **no permanent elimination** unless
`GameConfig.elimination_deaths` is set. Legacy mode (`DEATH_MODE = "legacy"`)
still eliminates at `MAX_DEATHS_BEFORE_ELIM = 3`. Defence buying and Ferrengi
`hot_sectors` avoidance are how rich seats stay under the two-pod budget.

## N1 colonist ferrying

N1 acceptance (`test_seat_bot_n1.py` / `prove_n1_day`) checks day-1 StarDock at
100k, empty-shelf day-1 profit 0 at 20k, ABA <= 2, rejected 0. It does **not**
require a trade count. In the 6-seat match N1 spends most turns ferrying because
that is the N1 ladder (citadel colonists, `feed_organics=False`). Not a bug
against the acceptance bar; left unchanged.

## Sixth planet refused

When `deploy_genesis` is illegal with reason `sector already holds 5 planets`,
every brain that carries a torpedo warps to another exit (same path as FedSpace /
too-close). Covered by `test_sixth_planet_refused_warps_away`.

## Deliberate differences

- Combat-hull preference order is a chosen default from fogged `max_fighters` on
  the roster constants (already used by the seat for CargoTran turns).
- Hot-sector memory is seat-local scratchpad, not shared intel.
- HeuristicAgent is kept in the scripted match but made deterministic and
  non-looping; it is still a weak baseline.

## Plants

Each mutation was restored before the suite.

| plant | where | caught by |
| --- | --- | --- |
| `_combat_hull_option` returns None | `seat_brain.py` | `test_rich_n3_buys_tougher_hull` |
| `_buy_defense` returns None | `seat_brain.py` | `test_rich_n3_buys_shields_when_hull_is_already_tough` |
| `target_planets` forced to 2 | `seat_brain.py` | `test_rich_n2_raises_target_planets_above_two` |
| hot-sector filter removed | `seat_brain.py` | `test_hot_ferrengi_sector_is_avoided_when_naked` |
| 5-planet leave skipped | `seat_brain.py` | `test_sixth_planet_refused_warps_away` |
| coeff-1 dead-world skip removed | `seat_brain.py` | `test_coeff1_organics_rebalance_is_skipped` |
| heuristic reverse + out-of-turns | `heuristic.py` | `test_heuristic_avoids_reverse_and_out_of_turns` |
| `PODS_PER_DAY = 99` | `constants.py` | `test_third_loss_in_a_day_is_ship_destroyed` |
