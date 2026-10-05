# FedSpace police (FED_MODE)

Federation starships, Extern tows, Police HQ (commission / rewards / Ten Most Wanted), and evil-ISS repossession.

Switch: `K.FED_MODE` (`tw2002` default; `legacy` = pre-slice byte-identical). Sub-switches: `K.FED_PROTECT_PUNISH` (`pod` | `refuse`), `K.ISS_REPO_MODE` (`twgs` | `mbbs`), `K.FED_TOW_DEST` (`random` | `msl`), `K.REWARD_TARGET_RULE` (`any_red` | `listed`), `K.FED_BLOCKED_BY_MINES` (False), `K.COMMISSION_ONCE` (True), `K.FED_TOW_FIGHTER_LIMIT` (98), `K.FED_SHIPS_PER_SECTOR` (5).

Sources under `C:\Users\sugar\tw2002_reference\` (GAP_MAP shorthand): Bible, BibleV1, TEDIT, REV, Iago, Slice, MBBS, Gypsy, TWFAQ, cabal, docs wiki, EIS, MM. Target TWGS 3.11; MBBS tie-breaker. Marks: CONFIRMED / SOURCE-CONFLICT / UNVERIFIED.

**Legacy (`FED_MODE = "legacy"`):** no Federals (`Universe.federals` stays `[]`), no tows, no Police HQ verbs (handlers: "unsupported action"), no ISS repossession, attack on fedsafe in FedSpace = refuse + `FED_RESPONSE` + -200, `fedspace_protects` as today, no new observation keys. No new draws from `universe.rng` or the generator rng in either mode (fed/tow rngs are string-seeded). Pin: `test_fed_legacy_is_unchanged`.

## Rules table

| # | rule | original | mark and source | this slice (FED_MODE tw2002) | test |
| --- | --- | --- | --- | --- | --- |
| **Federals** | | | | | |
| f1 | Three Feds | Zyrain, Nelson, Clausewitz; indestructible. | CONFIRMED: docs wiki Feds.html; Iago; Bible density; MBBS. | `Universe.federals`: list of `Federal(name, title, sector_id, density, home_sector)`. Legacy `[]`. | `test_f1_three_feds` |
| f2 | Density | Nelson 462, Zyrain 489, Clausewitz 512. | CONFIRMED: cabal formulas; Iago; MBBS. | Added under INFO tw2002; holo lists title+name; not anomaly. | `test_f2_density` / `test_plant_14` |
| f3 | Starts | TEDIT Intrepid 7 / Valiant 3148 / Lexington 3959; captain mapping UNVERIFIED. | CONFIRMED locations; UNVERIFIED captains. | Zyrain `FED_ZYRAIN_START=7`; others via `Random(f"fed:{seed}")` among 11+ not dead-end, >= `FED_START_MIN_HOPS=6` from 1. | `test_f3_starts_rng_isolated` / `test_plant_16` |
| f4 | Blocked by fighters | Never enter sector with player fighters. Mines: Iago only. | CONFIRMED fighters; SOURCE-CONFLICT mines. | Skip fighter sectors; `FED_BLOCKED_BY_MINES=False`. | `test_f4_blocked` / `test_plant_3` |
| f5 | Movement | Nelson/Clausewitz wander; Zyrain stays / teleports to rescue. | CONFIRMED shape; hops/day UNVERIFIED. | `FED_HOPS_PER_DAY=3` on tick_day; Zyrain returns home next tick after f8. | `test_f5_wander_and_trap` |
| f6 | Evil ISS presence | Fed sharing sector destroys evil ISS unless cloaked. | CONFIRMED: Bible; Iago. | After each Fed hop and player move. | `test_f6_presence` |
| **Attacks / FedSpace protect** | | | | | |
| f7 | Attack Fed | Legal try; podded; -10 align; -10% exp. | CONFIRMED: cabal formulas; docs wiki. | `fed:<name>` target; `_destroy_ship(..., reason="federal", always_escape=True)`; killer_id None. | `test_f7_attack_fed` / `test_plant_2` |
| f8 | Protect trader | Zyrain summoned on attack vs fedsafe in FedSpace. Outcome UNVERIFIED. | CONFIRMED summon; UNVERIFIED punish. | `FED_PROTECT_PUNISH=pod` (default): refuse damage, FED_ZYRAIN, pod attacker, keep -200. `refuse`: today + Zyrain shown. | `test_f8_protect` / `test_plant_1` |
| f9 | fedsafe def | Keep `is_fedsafe` (align>=0, exp<=999). | SOURCE-CONFLICT fighter/align floors. | `FEDSAFE_MIN_ALIGNMENT=0`, `FEDSAFE_MAX_FIGHTERS=None`. | `test_f9_fedsafe` |
| f10 | Deploy in FedSpace | Stays refused (no invented Zyrain summon). | Outcome UNVERIFIED. | No change. | `test_f10_deploy_refused` |
| **Extern tows** | | | | | |
| f11 | Arms limit | 99+ fighters towed (Gypsy TWGS). | SOURCE-CONFLICT 50/99/100+. | `FED_TOW_FIGHTER_LIMIT=98` (tow when `fighters > 98`). | `test_f11_arms_tow` / `test_plant_4` |
| f12 | Parking | Max 5 ships/sector; which ship UNVERIFIED. | CONFIRMED 5; UNVERIFIED order. | Latest arrivals first (reverse `occupant_ids`) after f11. | `test_f12_parking` / `test_plant_5` |
| f13 | Cloak | Cloaked still towed. | CONFIRMED: TWFAQ Q18. | Cloak stays on. | `test_f13_cloak_tow` / `test_plant_6` |
| f14 | Dest | Random outside FedSpace vs MSL. | SOURCE-CONFLICT. | `FED_TOW_DEST=random` default; `msl` uses `msl_sectors`. | `test_f14_dest` / `test_plant_7` |
| f15 | Empty ships | Repo empty ships. | N/A single-ship. | Documented only. | n/a |
| **Police HQ** | | | | | |
| f16 | Entry | Align >= 0 (wiki) vs -50 MBBS. | SOURCE-CONFLICT. | `POLICE_MIN_ALIGNMENT=0`; sector 1; 0 turns. | `test_f16_entry` |
| f17 | Commission | 500..999 -> 1000 once. | CONFIRMED boost; once = MBBS. | `COMMISSION_ONCE=True`. | `test_f17_commission` / `test_plant_8` |
| f18 | post_reward | +1 align / 1000 cr on red target. | CONFIRMED rate. | `REWARD_MIN=1000`; `any_red` default. | `test_f18_post_reward` / `test_plant_9` |
| f19 | claim_reward | Kill (no escape), not pod. | CONFIRMED: REV. | `pending_rewards[killer]` on death only. | `test_f19_claim` / `test_plant_10` |
| f20 | Ten Most Wanted | Up to 10 evil; titles not numbers. | CONFIRMED columns; order UNVERIFIED. | Align asc, reward desc, id; corp None. | `test_f20_most_wanted` / `test_plant_12` |
| f21 | Underground | Out of scope. | — | Documented. | n/a |
| **ISS repo** | | | | | |
| f22 | Evil ISS | Destroyed on move (TWGS) / own-fighter safe (MBBS). | CONFIRMED both readings. | `ISS_REPO_MODE=twgs`; cloaked safe; align 0 ok. | `test_f22_iss_repo` / `test_plant_11` |
| f23 | Hail | Warning when align first < 0 in ISS. | UNVERIFIED wording. | Owner-only `FED_HAIL`. | `test_f23_hail` |
| **Extra** | | | | | |
| f24 | vs Ferrengi | Do not fight. | UNVERIFIED. | No interaction. | `test_f24_no_ferrengi_fight` |
| f25 | Challenges / rob | Never enter challenge sectors; not rob/toll/mine/quasar targets. | — | Enforced. | `test_f25_not_targets` |
| f26 | Tolls/mines | Never pay/hit. | — | Skipped. | `test_f26_no_toll_mine` |

### Deliberate differences

- Feds move on the day tick (`FED_HOPS_PER_DAY`), not real time; Zyrain returns to post at the tick.
- Deploying in FedSpace stays refused (no invented Zyrain summon); -200 keep for fedsafe attack.
- Police HQ in sector 1 (StarDock / GAP 1.5); police verbs cost 0 turns.
- Everyone counts as off-line at Extern for tows.
- No Galactic Bank tax, Underground bounties, Fed hold confiscation, empty-ship repo, ship TransWarp.
- Corp column in Ten Most Wanted empty until corporations slice.

## Planted bugs

| # | planted bug | caught by |
| --- | --- | --- |
| 1 | Zyrain not summoned / no pod on fedsafe FedSpace attack | `test_plant_1_zyrain_protect` |
| 2 | Fed takes damage / wrong attack penalty | `test_plant_2_fed_attack_penalty` |
| 3 | Fed enters fighter sector | `test_plant_3_fed_enters_fighters` |
| 4 | Tow at 98 or miss 99 | `test_plant_4_tow_threshold` |
| 5 | 6th ship / wrong arrival order | `test_plant_5_parking_order` |
| 6 | Cloaked skipped by tow | `test_plant_6_cloak_tow` |
| 7 | Tow dest in FedSpace | `test_plant_7_tow_dest` |
| 8 | Commission at 499 / outside / twice / lowers 1200 | `test_plant_8_commission` |
| 9 | post_reward on good / wrong align / credits | `test_plant_9_post_reward` |
| 10 | claim on pod / non-killer / twice | `test_plant_10_claim_reward` |
| 11 | Evil ISS not destroyed / cloaked / align 0 | `test_plant_11_iss_repo` |
| 12 | Most Wanted shows align numbers / good player | `test_plant_12_most_wanted_fog` |
| 13 | Legacy spawns Feds / tows / police verbs | `test_plant_13_legacy` / `test_fed_legacy_is_unchanged` |
| 14 | Fed density missing / as ship 40 | `test_plant_14_fed_density` |
| 15 | Legal list != handler for apply_commission | `test_plant_15_legal_handler` |
| 16 | Fed/tow draws from universe.rng | `test_plant_16_rng_isolated` |


## Seat brain acceptance bars

Score-threshold tests that measure day-10 net worth under overnight parking
pin FED_MODE = "legacy" inside the bar test only (never soften tw2002 rules):

- 	ests/test_seat_bot_n2.py::test_n2_day10_beats_n1_and_keeps_organics
- 	ests/test_seat_bot_n3.py::test_n3_day10_ferry_and_net_worth
- 	ests/test_economy_calibration_v1.py::test_n3_ten_day_growth_sits_inside_the_band
