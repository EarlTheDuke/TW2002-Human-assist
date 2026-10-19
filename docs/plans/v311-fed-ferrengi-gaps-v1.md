# v311-fed-ferrengi-gaps-v1 (COMMANDER NOTE 86)

Three new switches, each stored as `"legacy"` and turned on by `V311_PROFILE` or `TW2002_LIVE_PROFILE`. Rows 105-107 in `docs/plans/v311-profile-v1.md`. Rows 104 and 108 were already the stored default and were not given a new switch.

## Already on the tip

- CMB-l FedSpace attack. `protect_fedspace_attack` in `src/tw2k/engine/fed.py` drops alignment by 200, summons Zyrain, and pods the attacker. `_handle_attack` calls it when the sector is FedSpace and `fedspace_protects` the target. No `FED_RESPONSE_MODE`.
- SD-q commission. `handle_apply_commission` accepts alignment from 500 up to 1,000 and sets it to 1,000. `is_commissioned` is alignment at least 1,000. `check_iss_repo_on_move` repossesses an evil ISS (alignment below 0) after a warp, a retreat, or a TransWarp. No `FED_COMMISSION_MODE`.

## CMB-m `SPECIAL_HULL_RULES_MODE`

`special_hull_rules_on()` is also false unless `ship_roster_live()`.

A living player in an Interdictor Cruiser holds every other living ship in that sector: warp (`WARP_BLOCKED`, no turn spent), TransWarp, a fighter-challenge retreat, a flee from a Ferrengi encounter, and a combat flee. The Interdictor itself can leave. Corp mates are held. An unmanned parked Interdictor is UNVERIFIED and does not hold. A cloaked Interdictor still holds; whether a cloak should hide the well is UNVERIFIED.

The existing rule that the attacker being an Interdictor blocks a flee (`COMBAT_INTERDICT_HULLS`) stays on even when this switch is off.

A Tholian Sentinel that is the defender, and that shares `corp_ticker` with a planet in the sector, defends at `THOLIAN_CORP_DEFENSE_ODDS` (4). Its attack odds stay the hull chart (1). Landing and TransWarp bans beyond "cannot warp out" are not added. Cabal says an Interdictor does not block a retreat (GAP 5.10); this NOTE asks for the docs-wiki hold, and that is what the switch does.

## FER-c `FERRENGI_GRUDGE_MODE`

The global `universe.ferrengi_grudges` set is unchanged, so a profile-off game still grudges the way it did. With the switch on, the attacked ship also stores that trader on `FerrengiShip.grudges` (omitted from a save while empty). The next hop prefers a step that shortens the distance to the nearest remembered trader outside FedSpace. If there is no such hop, a neighbour bands into a sector where a living trader has more fighters than this Ferrengi and another Ferrengi is already in that sector or one hop out. The fighter cutoff and the "already grouped" test are UNVERIFIED; the Bible says they travel in groups and hold a grudge, and no FERRSPEC file is in the repo.

## FER-d `FERRENGI_PACE_MODE`

`FERRENGI_MOVE_ONE_IN` is 20 and `FERRENGI_MOVE_INTERVAL_S` is 30 (cabal twgs.html moveCh, classictw v3.00: the chance is once per 30 seconds). The live server spends elapsed wall seconds in `_credit_live_turns`. `tick_day` spends whatever is left of `TURN_REGEN_DAY_SECONDS` so a scripted day is one full day and a live day is not counted twice. Regeneration stays the existing once-a-day `FERRENGI_REGEN_PCT` of 0.20. Pace steps only relocate. The once-a-day hunt still makes the attack, so a Ferrengi does not strike on every hop. Whether a real Ferrengi would attack the moment it enters is UNVERIFIED.

With the switch off, the once-a-day 0.6 move roll is unchanged and the pace clock is never read.
