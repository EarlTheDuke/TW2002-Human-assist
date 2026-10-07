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
| f7 | Attack Fed | Legal try; podded; -10 align; -10% exp. | CONFIRMED: cabal formulas; docs wiki. | `fed:<name>` target; `_destroy_ship(..., reason="federal", always_escape=True)`; killer_id None. Same gate as any attack (fighters aboard, photon, qty 1..cap). The 10% is the pod's own loss (cabal formulas, same page: "If you are podded, you loose 10% of your exp"), taken once; DEATH_MODE legacy (no pod loss) takes it in the handler. | `test_f7_attack_fed` / `test_plant_2` / `test_qc_attack_fed_legal_equals_handler` / `test_qc_attack_fed_costs_ten_percent_once_under_legacy_death` |
| f8 | Protect trader | Zyrain summoned on attack vs fedsafe in FedSpace. Outcome UNVERIFIED. | CONFIRMED summon; UNVERIFIED punish. | `FED_PROTECT_PUNISH=pod` (default): refuse damage, FED_ZYRAIN, pod attacker, keep -200. `refuse`: today + Zyrain shown. | `test_f8_protect` / `test_plant_1` |
| f9 | fedsafe def | Keep `is_fedsafe` (align>=0, exp<=999). | SOURCE-CONFLICT fighter/align floors. | `FEDSAFE_MIN_ALIGNMENT=0`, `FEDSAFE_MAX_FIGHTERS=None` (live switches under FED_MODE tw2002, read by `victory.is_fedsafe`). | `test_f9_fedsafe` / `test_qc_f9_fedsafe_switches_work` |
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
| f19 | claim_reward | Kill (no escape), not pod. | CONFIRMED: REV. | `pending_rewards[killer]` on death only. Underground contracts are a separate list (`STARDOCK_TAVERN.md` tv17) and are not paid here. | `test_f19_claim` / `test_plant_10` |
| f20 | Ten Most Wanted | Up to 10 evil; titles not numbers. | CONFIRMED columns; order UNVERIFIED. | Align asc, reward desc, id; corp None. | `test_f20_most_wanted` / `test_plant_12` |
| f21 | Underground | Built in `STARDOCK_TAVERN.md`, not in this file. | — | Hit contracts stay off `posted_rewards`. | `test_pb26_contracts_are_not_police_rewards` |
| **ISS repo** | | | | | |
| f22 | Evil ISS | Destroyed on move (TWGS) / own-fighter safe (MBBS). | CONFIRMED both readings. | `ISS_REPO_MODE=twgs`; cloaked safe; align 0 ok. A move is a warp (also each plot_course hop), a retreat, or a planet transporter beam. | `test_f22_iss_repo` / `test_plant_11` / `test_qc_iss_repo_on_retreat` |
| f23 | Hail | Warning when align first < 0 in ISS. | UNVERIFIED wording. | Owner-only `FED_HAIL` at the end of the action that turned the pilot evil (so it lands before the next warp). | `test_f23_hail` / `test_qc_hail_precedes_repossession` |
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

## QC fixes (independent review of 58acec8)

Found by the reviewer, each pinned by a `test_qc_*` test that failed on 58acec8 (mutation run: 17/17 caught).

- f7 legal != handler: the legal list blocked `attack fed:<name>` with no fighters aboard (or photon-offline), but the handler podded the ship anyway and ignored `qty`. Now the same gate as a player attack.
- f7 experience: -10% was taken twice (handler x0.9, then the forced pod's 10%). The cabal row "Attacking a Fed: -10, but you get podded / Loose 10%" sits on the page that says "If you are podded, you loose 10% of your exp" - one loss. (Judgment call: reading the 10% as the pod's.)
- f23: `FED_HAIL` fired only inside the warp that repossessed the ship (twgs), so the warning arrived with the kill. It now fires when the action that made the pilot evil ends.
- f22: retreat and planet transporter moves skipped the evil-ISS check.
- Observation: Federals in your own sector were only visible as `fed:<name>` attack targets; the sector block now lists them (`sector.federals`, title + name), holo/probe memory keeps them, and the LLM prompt now carries the `police` and `fedspace` blocks (absent under legacy).
- Fog: the `fedspace` hint counted cloaked rivals in `ships_here` (revealing hidden ships) and said `will_be_towed` for every ship once a sector was crowded. It now counts only ships the seat can see and flags parking only for the seat's own late-arrival position. The Extern tow itself still counts cloaked ships (f13).
- `FED_REPOSSESS` reaches the sector occupants as the spec says (was owner-only).
- f9 switches `FEDSAFE_MIN_ALIGNMENT` / `FEDSAFE_MAX_FIGHTERS` were defined but never read.
- Legacy: `scanners.sector_view` added `"federals": []` under legacy, which landed in holo memory (state drift over a 3-day 6-seat run). Now tw2002 only. `test_qc_fed_legacy_matches_pre_slice_golden` pins a digest recorded on the engine without this slice (4a2200a + the class0 terra QC fixes cherry-picked); the rebased QC commit matches it byte for byte.
- `Universe.federals` was an untyped list (a model_dump / model_validate round trip turned Feds into dicts and `tick_federals` crashed). `Federal` now lives in `models.py`.
- No bounty if killer == victim.
- Seat brain: `_avoid_fed_tow` warped out of FedSpace on every visit while armed (N3 solo seed 250925: 9-24 times a day, ping-pong with its StarDock errands, day-10 NW 459,040 vs 539,364 legacy). Tows run only at Extern, so the brain now leaves when the turns left only just cover the trip out (`FED_TOW_EXIT_MARGIN_WARPS`), and the 98-fighter buy cap applies only late in the day. Fixed NW 539,364. The brain also claims bounties and takes the free commission (`_police_hq`).
- Known gap (not fixed): a multi-hop `plot_course` that runs out of turns inside FedSpace leaves an armed seat with fewer turns than one warp costs, so it cannot leave and takes the Extern arms tow (6-seat seed 250925, P4 day 8, sector 10, 3 turns left vs warp 4). The tow is the designed outcome; route planning does not yet avoid ending the day in FedSpace.

Score bars under FED_MODE tw2002: all three bars pass on 58acec8 and on the fix, so the FED_MODE pins are removed (see "Seat brain acceptance bars" below).

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

58acec8 pinned FED_MODE = "legacy" inside three score bars. QC re-ran them with the pin removed under
FED_MODE tw2002, on 58acec8 and on the QC fix: all three pass. On the QC fix rebased on bc868c6 the unpinned
(tw2002) run prints the same day-10 table as the pinned (legacy) run on bc868c6 (N3 seed 250925: N2 NW 565,421,
N3 NW 931,084; the scripted bar seats do not overnight in FedSpace armed). The spec pins only when a bar drops, so
the pins are removed and the bars now guard the default rules:

- `tests/test_seat_bot_n2.py::test_n2_day10_beats_n1_and_keeps_organics`
- `tests/test_seat_bot_n3.py::test_n3_day10_ferry_and_net_worth`
- `tests/test_economy_calibration_v1.py::test_n3_ten_day_growth_sits_inside_the_band`

Still pinned (by design, they compare pre-slice goldens or need the refuse path): the `legacy` fixtures in
`tests/test_experience_alignment_v1.py` / `tests/test_scanners_hidden_info_v1.py` (new observation keys),
`FED_PROTECT_PUNISH = "refuse"` in the experience-alignment `tw` fixture (the rank scenario keeps flying after the
fedsafe attack; under `pod` the attacker is podded and the scenario cannot continue), and the prompt-equality
pins in `tests/test_agency.py` / `test_system_prompt_names_the_commission`.
