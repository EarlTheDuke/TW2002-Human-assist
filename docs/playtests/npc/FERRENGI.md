# Ferrengi NPCs (FERRENGI_MODE)

Three Ferrengi hulls, Ferrengal home, tribute encounter (Flee / Attack / Surrender), grudges, regen, mine hits on roam.

Switch: `K.FERRENGI_MODE` (`tw2002` default; `legacy` = pre-slice simplified raiders, byte-identical). Sub-switches: `K.FERRENGI_ENCOUNTER` (`tribute` | `auto_combat`), `K.FERRENGI_FIGHTER_BLOCK` (False), `K.FERRENGI_HIT_MINES` (True), `K.FERRENGI_ALIGN_ON_KILL` (10), `K.FERRENGAL_MINES` (50), `K.FERRENGI_REGEN_PCT` (0.20), `K.FERRENGI_SEES_CLOAK` (False).

Sources under `C:\Users\sugar\tw2002_reference\` (GAP_MAP shorthand): Bible / BibleV1, FERRSPEC, TEDIT, Iago, MBBS, docs wiki Ferrengi_*, EIS TradeWars, Planet Handbook. Target TWGS 3.11; MBBS tie-breaker. Marks: CONFIRMED / SOURCE-CONFLICT / UNVERIFIED.

**Legacy (`FERRENGI_MODE = "legacy"`):** no Ferrengal, fighters/shields `100+300*agg` / `50*agg`, ship_class battleship/missile_frigate labels, no regen, no mine hits, no grudges, no cargo/credits, auto-combat (no encounter), density 40 each, flat `FERRENGI_COMBAT_ODDS` 1.0, same `universe.rng` draw order for spawn/roam. Pin: `test_ferrengi_legacy_is_unchanged`.

## Rules table

| # | rule | original | mark and source | this slice (FERRENGI_MODE tw2002) | test |
| --- | --- | --- | --- | --- | --- |
| **Hulls** | | | | | |
| n1 | Three hulls | Assault Trader, Battle Cruiser, Dreadnought. | CONFIRMED: FERRSPEC, MBBS 17-19, wiki. | `FerrengiShip.hull` key. | `test_n1_three_hulls` |
| n2 | Specs | AT 3k/200/50/2/1.0/40; BC 8k/800/75/3/1.2/100; DN 15k/1k/100/4/1.4/100. | CONFIRMED counts; odds SOURCE-CONFLICT FERRSPEC vs Bible — pick FERRSPEC. | `FERRENGI_HULL_SPECS` + `FERRENGI_ODDS_BY_HULL`. | `test_n2_specs` / `test_plant_1` |
| n3 | Hull by aggression | UNVERIFIED day gates. | UNVERIFIED. | aggr 1-4 AT, 5-7 BC, 8-10 DN. | `test_n3_hull_mix` |
| n4 | Combat odds | Per hull. | CONFIRMED shape. | `ferrengi_odds` / `combat_odds_of`. | `test_n4_odds` |
| n5 | Density | 40 / 100 / 100 when Ferrengi-piloted. | CONFIRMED: FERRSPEC. | `ferrengi_density` under INFO tw2002. | `test_n5_density` / `test_plant_2` |
| **Ferrengal** | | | | | |
| n6 | Home sector | Deep fortified home. | CONFIRMED: Bible, TEDIT HomeBase, Iago. | `ferrengal_sector` via `Random(f"ferrengal:{seed}")`, prefer dead-end, >=8 hops. | `test_n6_ferrengal` / `test_plant_3` / `test_plant_14` |
| n7 | Contents | 50 mines; fighters; Quasar deferred. | CONFIRMED mines; fighters UNVERIFIED (1000). | 50 armid + 1000 defensive fighters, owner `ferrengi`. | `test_n7_mines` |
| n8 | Spawn near home | Prefer neighbourhood. | UNVERIFIED radius. | `FERRENGAL_SPAWN_RADIUS=3`. | `test_n8_spawn_near` |
| **Pace** | | | | | |
| n9 | Regen | TEDIT 20% of max. | CONFIRMED pct. | floor(max * 0.20) toward hull max each tick_day. | `test_n9_regen` / `test_plant_10` |
| n10 | Move prob | TEDIT 1 in 20 real-time. | SOURCE-CONFLICT vs 0.6 day-tick. | Keep 0.6 (deliberate). | n/a |
| n11 | Strength ramp | Existing. | - | Cap at hull max. | `test_n11_ramp_cap` |
| **Behaviour** | | | | | |
| n12 | Fighters / mines | Ignore fighters; hit mines. | CONFIRMED Iago; UNVERIFIED for v3. | `FERRENGI_FIGHTER_BLOCK=False`, `HIT_MINES=True`. | `test_n12_fighters_mines` / `test_plant_4` / `test_plant_5` |
| n13 | Hunt / flee | Prefer weak; flee if outgunned; grudge prefer. | CONFIRMED cowardly. | Keep thresholds; prefer grudges. | `test_n13_grudge_prefer` |
| n14 | Encounter | Flee / Attack / Surrender / Info. | CONFIRMED Bible prompt. | `ferrengi_encounter`; Info = observation. | `test_n14_encounter` / `test_plant_6` |
| n15 | Tribute | Cargo, some holds, sometimes credits. | CONFIRMED shape; amounts UNVERIFIED. | all cargo; up to 5 holds; 10% credits if empty. | `test_n15_tribute` / `test_plant_7` |
| n16 | Attack under enc | Resolve combat. | - | Clears encounter; can grudge. | `test_n16_attack_enc` |
| n17 | Flee | Leave sector. | - | Any neighbour; flee_penalty. | `test_n17_flee` |
| n18 | Grudge | Forever blood feud. | CONFIRMED Bible/Iago/MBBS. | `ferrengi_grudges` set; hunt prefer. Blood Hunt pack deferred. | `test_n18_grudge` / `test_plant_9` |
| n19 | Kill rewards | Align + bounty + xp. | CONFIRMED Bible; +10 UNVERIFIED magnitude. | `FERRENGI_ALIGN_ON_KILL`; bounty*agg; salvage credits. | `test_n19_kill` / `test_plant_8` |
| n20 | Cargo on Ferrengi | Steal / carry. | CONFIRMED steal. | cargo + credits fields; salvage on kill. | `test_n20_cargo` |
| **FedSpace** | | | | | |
| n21 | No FedSpace | Never enter 1..10. | CONFIRMED prior. | Kept. | `test_n21_no_fedspace` / `test_plant_16` |
| n22 | vs Feds | No fight. | UNVERIFIED f24. | Kept. | `test_n22_no_fed_fight` |
| n23 | Cloak | Skip cloaked. | UNVERIFIED extend from Iago Fed. | `FERRENGI_SEES_CLOAK=False`. | `test_n23_cloak` / `test_plant_13` |
| **Deferred** | | | | | |
| n24 | Alien traders | Exp/align; SD entry; fighter block. | CONFIRMED GAP 8.6. | `ALIEN_TRADERS.md` al1-al32. | `test_al7_hops` |
| n25-n28 | Obs / verbs / fog / legal==handler | - | - | Encounter block; hull in lists; `_actor_cloaked` unchanged. | `test_n26_legal_handler` / `test_plant_12` |

### Deliberate differences

- Day-tick movement/spawn instead of real-time 1-in-20 per ~30s; move prob kept 0.6.
- Ferrengal Quasar planet / invincible flag / Overlord / Scorpion / capturable ships: deferred.
- Alien traders are specified in `ALIEN_TRADERS.md` (slice 58).
- Blood Hunt pack AI deferred; grudges are a preference set only.
- Tribute hold-steal (5), credit pct (10%), spawn credits (500*agg), Ferrengal fighters (1000): named UNVERIFIED constants.
- Odds from FERRSPEC not Bible chart (SOURCE-CONFLICT).
- Encounter Info is observation, not a separate ActionKind.
- Initial/daily spawn still respects `ferrengi_max_alive` and grace days.

## Planted bugs

| # | planted bug | caught by |
| --- | --- | --- |
| 1 | Wrong Assault max / odds | `test_plant_1_assault_specs` |
| 2 | BC/DN density as 40 | `test_plant_2_density` |
| 3 | No Ferrengal / in FedSpace / mines != 50 | `test_plant_3_ferrengal` |
| 4 | Ferrengi blocked by player fighters | `test_plant_4_fighter_block` |
| 5 | Mines ignored on entry | `test_plant_5_mines` |
| 6 | Encounter skipped (auto-combat) | `test_plant_6_encounter` |
| 7 | Surrender leaves cargo / no credits | `test_plant_7_tribute` |
| 8 | Kill align/bounty wrong | `test_plant_8_kill_rewards` |
| 9 | Grudge not recorded / ignored | `test_plant_9_grudge` |
| 10 | Regen over max / never | `test_plant_10_regen` |
| 11 | Legacy places Ferrengal / encounters | `test_plant_11_legacy` |
| 12 | Legal != handler under encounter | `test_plant_12_legal_handler` |
| 13 | Cloaked hunted | `test_plant_13_cloak` |
| 14 | Ferrengal uses universe.rng | `test_plant_14_rng` |
| 15 | Spec table wrong for DN | `test_plant_15_dread_specs` |
| 16 | Ferrengi in FedSpace after ticks | `test_plant_16_fedspace` |

Recorded run (each mutation applied to the engine, test file run, mutation reverted): 15 logic-path plants (1-3, 5-16), 15 caught, 0 missed. Plant 4 as a constant flip is masked by the test fixture's monkeypatch, so it is pinned by `test_plant_4_fighter_block` but not counted. Plants 12, 14 and 16 were re-run after the soft-encounter change and the stronger rng / FedSpace tests.

- Overnight encounter clear: an open `ferrengi_encounter` at day end flees (or tributes if no warp) so idle seats cannot stall forever (deliberate; original is real-time).
- Ignoring the hail (deliberate): the original prompt forces Attack/Retreat/Surrender. Here any other action (WAIT, warp, trade, attacking someone else) is legal but the Ferrengi take tribute first (same as Surrender), then the action runs. Keeps scripted/LLM seats that do not read the encounter from stalling; legal_actions flags those verbs with `ferrengi_note`.
- No Ferrengal when `GameConfig.enable_ferrengi` is False (no Ferrengi, no home base). Observation omits a null `ferrengi_encounter` (same rule as the null `police` / `fedspace` blocks), so legacy observation JSON keeps its old bytes.
