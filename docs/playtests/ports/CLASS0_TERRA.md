# Class 0 ports and Terra (CLASS0_MODE)

Colonists come from Terra (sector 1), not from an endless StarDock shelf. Alpha Centauri and Rylos are the other two Class 0 ports (fighters / shields / holds only). Shields follow the fighter price wave in opposite phase. The Major Space Lanes between sector 1, Alpha Centauri and Rylos are swept of fighters and mines every Extern (day tick).

Switch: `K.CLASS0_MODE` (`tw2002` default; `legacy` = today's build byte-identical). Sub-switches: `K.SHIELD_PRICE_MODE` (`mirror` | `flat`), `K.CLASS0_EXTERN_PLANET_RULE` (`keep` | `cap_l2` | `remove`).

Sources under `C:\Users\sugar\tw2002_reference\` (same shorthand as GAP_MAP.md): Bible, TEDIT (twgs.html), REV, REV2, Iago, Slice, MBBS, cabal, docs wiki, EIS, MM. Target TWGS 3.11; MBBS tie-breaker. Marks: CONFIRMED / SOURCE-CONFLICT / UNVERIFIED.

**Legacy (`CLASS0_MODE = "legacy"`):** no Terra, `buy_equip` colonists 10 cr / 0 turns / unlimited at sector 1, shields flat 10, no Alpha Centauri / Rylos, no MSL set, no sweep, `remove_limpet` only at sector 1 (HARDWARE_MODE rules), `terra_colonists` absent from the legal list and harness `/rules` verbs (handler: "unsupported action"). Universe generation consumes no extra draws from the generator rng or `universe.rng` in either mode (new draws use `random.Random(f"class0:{seed}")`).

## Rules table

| # | rule | original | mark and source | this slice (CLASS0_MODE tw2002) |
| --- | --- | --- | --- | --- |
| **Terra** | | | | |
| t1 | Where | Terra is the planet in sector 1; colonists for every other planet come from there. | CONFIRMED: Bible; EIS TradeWars.html / Navigate.html; TWBible_original. | `Universe.terra_colonists` / `terra_max` (not a Planet row). Cannot be landed on, claimed, sieged, destroyed, genesis-blocked or taxed. Test: `test_t1_terra_is_universe_state`. |
| t2 | Pool size | TEDIT Max Terra Colonists 100,000 vs Iago 10,000 holds. | SOURCE-CONFLICT (TWGS taken). Day-1 fill UNVERIFIED (Max read as opening). | `K.TERRA_MAX_COLONISTS = 100_000`; starts full. Unit = one hold. Test: `test_t2_terra_starts_full`. |
| t3 | Regeneration | TEDIT / MM: 750 colonists per day. MBBS 20,000 is a sysop suggestion. REV2 percent-of-max is post-3.11. | CONFIRMED (TWGS editor). | `+K.TERRA_REGEN_PER_DAY = 750` per day tick, never above max. Test: `test_t3_terra_regen`. |
| t4 | Load cost | Earth takes one turn; Auto removed. | CONFIRMED: REV. | `terra_colonists` costs `K.TERRA_LOAD_TURNS = 1`. Test: `test_t4_terra_load_turns`. |
| t5 | Price | Take / grab / pick up; no price printed. | UNVERIFIED by absence. | `K.TERRA_COLONIST_PRICE = 0`. Net-worth still uses `K.COLONIST_PRICE = 10`. Test: `test_t5_terra_free`. |
| t6 | Load size | Take into holds; drop-off on Terra (Iago megaholds). | CONFIRMED drop-back. | take ≤ min(pool, cargo_free); leave ≤ min(cargo colonists, max−pool). Test: `test_t6_take_leave_caps`. |
| t7 | Who | Any trader / hull with holds. | UNVERIFIED that nobody is barred. | Any alive trader with holds; escape pod OK if it has holds. Test: `test_t7_any_trader`. |
| t8 | Old path | StarDock sold colonists in this game. | n/a (this game's invention). | `buy_equip colonists` refused under tw2002; legal list drops it. Legacy unchanged. Test: `test_t8_buy_equip_colonists`. |
| t9 | Jettison | −1 alignment each (cabal / Iago). | OUT OF SCOPE. | Documented as next. |
| **Class 0 ports** | | | | |
| t10 | Three ports | Sol, Alpha Centauri, Rylos. | CONFIRMED: Bible; cabal glossary; docs wiki; Iago; S4 wiki. | Sector 1 StarDock IS Sol Class 0. AC/Rylos: `Port(class_id=FEDERAL, special=...)`. Test: `test_t10_three_class0`. |
| t11 | What they sell | Fighters, shields, holds only. | CONFIRMED: Bible; EIS; cabal glossary. | Special ports accept only those three; else "Class 0 ports sell only fighters, shields and holds". Test: `test_t11_class0_sells`. |
| t12 | Prices | Same daily price at every Class 0; calendar not stock. | CONFIRMED in shape: cabal tips #27; Iago. Stock never runs out UNVERIFIED. | Fighters = `fighter_unit_price`; holds = hold formula; same day at all three. Test: `test_t12_same_day_prices`. |
| t13 | Shield price | When ftrs cheap, shields dear (Iago); daily change (cabal). Numbers UNVERIFIED (chart missing). | CONFIRMED in shape; numbers UNVERIFIED (mirror of Hekate). | `K.SHIELD_PRICE_MODE = "mirror"` → `shield_unit_price` = round(200 − sin(day/87·2π)·40) clamped 160..239. `"flat"` = 10. Valuation stays 10. Test: `test_t13_shield_wave`. |
| t14 | Dock turn | Docking costs 1 turn. | CONFIRMED: gap 2.7; Bible; docs wiki. | First `buy_equip` of a visit at AC/Rylos costs `PORT_DOCK_TURN_COST`; later 0. Sector 1 stays 0 (deliberate). Test: `test_t14_dock_turn`. |
| t15 | Placement | Outside FedSpace; players must find them; sector numbers are settings. Original 6-out + backdoor NOT copied. | CONFIRMED location shape; algorithm numbers UNVERIFIED. | After generate: `Random(f"class0:{seed}")`; hops [4,12]; out-degree then rng; separation ≥ 4. Fallback replaces a normal port. Test: `test_t15_placement`. |
| t16 | Not robbable | Class 0 not rob targets; attack out of scope. Blow-up SOURCE-CONFLICT (Slice no vs later yes). | ROB already refuses FEDERAL. | Keep + test for special ports. Test: `test_t16_no_rob`. |
| t17 | Limpet removal | All Class 0 remove limpets. Fee TEDIT 1,250 vs Slice/cabal ~5,000. | CONFIRMED service; SOURCE-CONFLICT fee (TEDIT taken). | `class0_service_here` for legal + handler. Test: `test_t17_remove_limpet_class0`. |
| t18 | Place during day | Figs/mines/planets allowed in AC/Rylos sectors. | CONFIRMED: cabal glossary / tips #26. | Existing deploy/genesis rules. Test: `test_t18_deploy_allowed`. |
| **MSL / Extern** | | | | |
| t19 | MSL set | Lanes between 1↔AC, 1↔Rylos, AC↔Rylos (both directions) + the Class 0 sectors. | CONFIRMED: Bible; cabal glossary; Slice; MM. Tie-break UNVERIFIED. | Fewest hops; lex-smallest sector-id path. `Universe.msl_sectors` sorted. Test: `test_t19_msl_set`. |
| t20 | Nightly sweep | Fighters and mines cleared on Extern. Toll credits lost UNVERIFIED. Beacons not swept UNVERIFIED. | CONFIRMED sweep. | After `_overnight_retreats`, before `regenerate_ports`. Owner-only `EXTERN_SWEEP`. Test: `test_t20_extern_sweep`. |
| t21 | Planets at Extern | TWGS: may place; Slice: reduce to L2; docs wiki: or lose them. | SOURCE-CONFLICT (TWGS `keep` taken). | `CLASS0_EXTERN_PLANET_RULE`; `cap_l2`/`remove` wired, off. Test: `test_t21_planet_rules`. |
| t22 | MSL advice | Feds remove anything in the MSLs. | CONFIRMED in shape: Gypsy; GAP 13.6. | Legal list note "Major Space Lane: removed at Extern"; handler unchanged. Test: `test_t22_msl_note`. |
| t23 | Density / scans | Port 100; Planet 500 (Terra). | CONFIRMED: cabal density; S3 bible tip. | AC/Rylos +100; Terra +500 to sector 1 under INFO tw2002. Holo/report name + class 0 + prices. Test: `test_t23_density_and_report`. |
| t24 | Interdictor | Don't function at StarDock and Terra. | CONFIRMED: REV. | Already true (no planets in FedSpace); regression only. Test: `test_t24_interdictor_regression`. |
| **FedSpace outposts** | | | | |
| t25 | FedSpace "Federal" ports are not Class 0 | Exactly three Class 0 ports (Sol, Alpha Centauri, Rylos) and every one sells fighters, shields and holds; StarDock (Class 9) also sells them ("Buy Class 0 Items", premium). No non-trading Class 0 port exists. Whether sectors 2-10 hold ports at all is UNVERIFIED (GAP 1.18). | CONFIRMED three / what they sell: cabal glossary "Class 0 Ports"; EIS TradeWars.html + ShipyardMenu.html; Iago_War_Manual.txt ("five sources: SD, the three class 0 ports"). | Our ours-only FedSpace ports (universe.py, 60% of sectors 2-10, stored `PortClass.FEDERAL`, trade nothing) are labelled for seats: `K.FED_OUTPOST_MODE` `tw2002` → sector port view and holo/probe view get `class_id: null`, `class_display` "Federal outpost (not Class 0)", `note` naming where fighters/shields/holds are sold; `buy_equip` refusal (legal list = handler) appends `K.FED_OUTPOST_BUY_REASON`. Generation, engine class and trading unchanged. `legacy` = class 0 / old reason byte-identical. Tests: `tests/test_fed_outpost_label.py`. |

### Deliberate differences

- StarDock stays in sector 1 (GAP 1.5), so Sol + Terra + StarDock share sector 1; no Shipyard Class 0 premium.
- Alpha Centauri / Rylos keep the existing warp graph (no 6-out + backdoor), so seeds and bars stay comparable.
- Terra is Universe state, not a Planet row (cannot be destroyed by the planet-collision bug).
- Colonist net-worth value stays 10 (`K.COLONIST_PRICE`) though Terra charges 0; shields valued at 10 though priced on the wave.
- StarDock `buy_equip` stays 0 turns; only Alpha Centauri / Rylos charge the dock turn.
- Day tick = Extern; prices change per game day, not calendar day.
- Toll credits on swept fighters are lost; beacons are not swept (both UNVERIFIED).
- Jettison colonists, port attack on Class 0, random StarDock location: out of scope (next).
- t25: the FedSpace outposts (sectors 2-10) stay in the universe (removing them or making them normal ports would reshuffle every seed and the original is UNVERIFIED); they are only relabelled. Seats that start in sectors 2-10 (server/runner.py `_build_agents`) used to read them as Class 0.

## What the engine does (CLASS0_MODE tw2002)

- New verb `terra_colonists` `{mode: take|leave, qty}`. Legal only in sector 1, not landed, not in a fighter challenge.
- `buy_equip` at sector 1 drops colonists; shields use `shield_unit_price`. At AC/Rylos: fighters/shields/holds only + dock turn.
- `remove_limpet` at sector 1, Alpha Centauri, Rylos via `class0_service_here`.
- Placement of AC/Rylos + MSL set at generation; Terra pool starts full; regen + sweep on day tick.
- Observation: `terra` block in sector 1; `class0_port` at special ports; `is_msl` only on current sector; no leak of `Universe.class0_sectors` to seats.
- Seat brains / prompts: `terra_colonists` instead of buying colonists; Class 0 / shield wave / MSL notes.

## Out of scope / next

Jettison colonists; FedSpace police / Feds / tows / bounties (fedspace-police-v1); port attack on Class 0; random StarDock location; original AC/Rylos warp topology.

## Planted bugs

Each plant was a real code mutation applied to the engine, run against `tests/test_class0_terra_v1.py`, then reverted. The table is filled from that run.

| # | planted bug (real mutation) | file | result | caught by |
| --- | --- | --- | --- | --- |
| p1 | buy_equip colonists still listed at sector 1 under tw2002 | legality.py | caught | test_plant_1_colonists_still_sold |
| p2 | terra_colonists take ignores pool / free holds | class0.py | caught | test_plant_2_take_ignores_pool_or_holds |
| p3 | terra_colonists costs 0 turns | class0.py | caught | test_plant_3_terra_charges_or_zero_turns |
| p4 | Terra regen applied twice / no max cap | class0.py | caught | test_plant_4_regen_double_or_over_max |
| p5 | terra leave exceeds max | class0.py | caught | test_plant_5_leave_exceeds_max_or_invents |
| p6 | Alpha Centauri legal list keeps non-Class-0 items | legality.py | caught | test_plant_6_alpha_sells_non_class0 |
| p8 | shields always flat 10 under mirror | class0.py | caught | test_plant_8_shields_flat_under_mirror |
| p11 | Extern sweep skips all MSL sectors | class0.py | caught | test_plant_11_sweep_scope |
| p13 | remove_limpet handler still StarDock-only (legal != handler) | hardware.py | caught | test_plant_13_remove_limpet_legal_handler |
| p16 | terra_colonists handler not refused under legacy | class0.py | caught | test_plant_16_legacy_no_tw_features |
| p16b | terra_colonists offered in legal list under legacy | legality.py | caught | test_plant_16_legacy_no_tw_features |

11 plants: 11/11 caught on the first strengthened run.

t25 (class0-outpost-label) plants, run against `tests/test_fed_outpost_label.py`, then reverted:

| # | planted bug (real mutation) | file | result | caught by |
| --- | --- | --- | --- | --- |
| o1 | sector view keeps class 0 on the outpost | observation.py | caught | test_observation_labels_outpost_not_class0, test_llm_prompt_has_no_class0_for_outpost |
| o2 | buy_equip refusal does not name the outpost | class0.py | caught | test_buy_equip_reason_names_outpost_legal_equals_handler |
| o3 | outpost reason applied under FED_OUTPOST_MODE legacy | class0.py | caught | test_legacy_shows_class0_and_old_reason |
| o4 | Alpha Centauri / Rylos treated as outposts | class0.py | caught | test_alpha_rylos_still_class0, test_holo_probe_view_labels_outpost |
| o5 | holo / probe view still shows class 0 | scanners.py | caught | test_holo_probe_view_labels_outpost |

5 plants: 5/5 caught.

## Delivered

- Rules table t1-t24 with marks. Deliberate differences listed. `CLASS0_MODE` default `tw2002`; `legacy` keeps buy_equip colonists / flat shields / no AC-Rylos / no MSL / no sweep / no terra_colonists verb. Sub-switches `SHIELD_PRICE_MODE` and `CLASS0_EXTERN_PLANET_RULE`. 11 planted bugs, all caught. Legal list equals handlers for new paths. Brains rejected_engine 0 on the scripted match.
- Open conflicts kept as named constants: t2 (TEDIT 100k vs Iago 10k), t13 (mirror numbers UNVERIFIED), t17 (limpet fee TEDIT), t21 (keep vs cap_l2).
- Collateral: parity_s4 builder covers `terra_colonists`; parity_s6 harness verb count is 56. Scanners INFO_MODE legacy fog fixture also pins `CLASS0_MODE=legacy` so goldens stay byte-identical. Seat-bot N2 day-10 bar pins `CLASS0_MODE=legacy` (colonist scarcity changes NW; do not weaken tw2002 rules).
- Before/after `scripts/run_scripted_match.py --seats N3,N3,N2,N2,N1,H --seed 250925 --days 10`, default modes. Before = origin eb19593. After = this slice. Score drift is expected (Terra pool + shield wave + MSL). Rejected 0/0 both sides; bots still colonize (planets built) and are not stuck buying colonists at StarDock (`buy_equip colonists` is absent under tw2002; brains use `terra_colonists`).

| # | Seat | Net worth before | Net worth after | Ship before → after | Planets | Rejected | Deaths after |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | N3-P1 | 540,933 | 361,525 | battleship → cargotran | 3 | 0/0 | 1 |
| 2 | N3-P2 | 387,789 | 460,644 | battleship → cargotran | 3 | 0/0 | 0 |
| 3 | N2-P4 | 343,561 | 283,365 | cargotran → cargotran | 2 | 0/0 | 1 |
| 4 | N1-P5 | 331,595 | 289,309 | merchant_cruiser | 2 | 0/0 | 0 |
| 5 | N2-P3 | 202,320 | 250,188 | cargotran → merchant_cruiser | 2 | 0/0 | 0 |
| 6 | H-P6 | 196,161 | 181,834 | merchant_cruiser | 0 | 0/0 | 0 |

Explanation: with colonists free but turn-costed and pool-limited at Terra, early ferry throughput drops, so N3 seats stay on CargoTran longer and NW redistributes (P2 leads after). Shield price wave changes defense spend. Two deaths vs zero before — not a stuck-at-StarDock loop (rejected still 0). Ranking after: P2, P1, P5, P4, P3, P6.
