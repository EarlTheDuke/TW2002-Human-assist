# Bots use planetary warfare

`BOTS_WAR_MODE` `tw2002` | `legacy`. Legacy is the bot at `f96fb56`. This slice does not change an engine rule. It changes how SeatBrain uses the siege, citadel, fighter, and mine verbs the engine already has.

Sources: Iago's war manual, the MBBS manual, the Cabal base and blockade notes, the original Bible, S3, and the engine docs under `docs/playtests/planetary-warfare/`. TWGS 3.11 is the default. MBBS breaks a tie. Strategy rows say how a bot chooses. They do not change the engine.

Root-cause trace on `885bdb0`, seed 250925, 10 days, seats N3,N3,N2,N2,N1,H, before any war code. `_maybe_lay_armids` was called 4,575 times and laid 0 mines. 4,034 calls were not at the home sector, 379 were in a swept lane, 158 were at home and then refused because `_home_is_corridor` was true, and 4 were not a legal mine deploy. `_lay_fighters` exists and is never called.

10-day seed 250925 on `67c050a`, seats N3,N3,N2,N2,N1,H, rejected 0/0, exceptions 0. Legacy (`--bots-war legacy`) digest `16ad8833`, total 1,809,848. War on (`--war-policy full`) digest `6441dbe7`, total 1,738,810. `land_planet` in the report includes ordinary landings; the legacy run has them too and has no mines, pickets, deposits, or reaction.

| Seat | Legacy net worth | Legacy ship | Legacy deaths | War net worth | War ship | War deaths |
| --- | --- | --- | --- | --- | --- | --- |
| N3-P1 | 766,412 | cargotran | 0 | 706,053 | cargotran | 0 |
| N2-P3 | 387,649 | cargotran | 0 | 470,469 | cargotran | 0 |
| N1-P5 | 281,031 | cargotran | 0 | 266,872 | cargotran | 0 |
| N3-P2 | 163,396 | cargotran | 0 | 94,772 | scout | 5 |
| N2-P4 | 161,357 | cargotran | 0 | 150,336 | cargotran | 0 |
| H-P6 | 50,003 | scout | 2 | 50,308 | scout | 6 |

War report, policy full: P3 laid 55 corporate armids and 10 corporate defensive fighters and set reaction once. P5 laid 64 personal armids and 10 personal defensive fighters, deposited 10 fighters, and set reaction once. P1 deposited 412 fighters. P2, P4, and H laid no mines.

10-day seed 4242 on the same tree, rejected 0/0, exceptions 0. Legacy digest `2734bc10`, total 1,802,336. War full digest `827389f1`, total 1,649,064. The legacy report has no mines, pickets, deposits, or reaction.

| Seat | Legacy net worth | Legacy ship | Legacy deaths | War net worth | War ship | War deaths |
| --- | --- | --- | --- | --- | --- | --- |
| N3-P1 | 571,103 | cargotran | 0 | 490,207 | cargotran | 0 |
| N2-P3 | 493,268 | cargotran | 0 | 503,948 | cargotran | 0 |
| N1-P5 | 401,985 | cargotran | 0 | 390,740 | cargotran | 0 |
| N2-P4 | 172,075 | cargotran | 0 | 169,550 | cargotran | 0 |
| N3-P2 | 147,899 | cargotran | 0 | 78,613 | scout | 3 |
| H-P6 | 16,006 | scout | 5 | 16,006 | scout | 8 |

P3 laid 57 corporate armids and 10 corporate fighters. P5 deposited 20 fighters and set reaction, and laid no mines.

10-day seed 250925, `--war-policy defend`, rejected 0/0, exceptions 0, digest `41a49cf7`, total 1,734,907. N3-P1 733,020 cargotran 0 deaths. N2-P3 437,944 cargotran 0. N1-P5 268,211 cargotran 0. N2-P4 150,861 cargotran 0. N3-P2 94,683 scout 5 deaths. H-P6 50,188 scout 5 deaths. P3 laid 57 corporate armids. P5 laid 66 personal armids. P1 deposited 200 fighters. N3-P2 still lost the CargoTran with no mines of its own.

30-day seed 250925, war full, on this tree, rejected 0/0, exceptions 0, digest `132ac666`, total 6,444,225, elapsed 901s. Day 10 matches the defend 10-day above. N3-P1 2,265,237 battleship 0 deaths (the report's 5 `ship_destroyed` rows are kills by P1). N2-P3 1,760,848 cargotran 4 deaths. N1-P5 1,468,811 cargotran 0. N2-P4 495,760 cargotran 0. N3-P2 403,381 scout 12 deaths. H-P6 50,188 scout 19 deaths. P3 laid 103 corporate armids, 10 corporate fighters, 472 fighter deposits, 10 shield deposits, reaction once. P5 laid 345 personal armids and 10 fighters. P1 deposited 1,150 fighters.

30-day seed 250925, war off, rejected 0/0, exceptions 0, digest `b15d65a0`, total 6,280,129, elapsed 1188s. That digest matches the bank-slice 30-day. The report has no mines, pickets, deposits, or reaction. N3-P1 2,823,128 battleship 0 deaths. N2-P3 1,520,218 cargotran 4 deaths. N1-P5 892,662 cargotran 5 deaths. N3-P2 523,588 cargotran 0 deaths. N2-P4 470,530 scout 1 death. H-P6 50,003 scout 7 deaths.

30-day seed 4242, war full, rejected 0/0, exceptions 0, digest `59264641`, total 4,399,285, elapsed 1086s. Day 10 matches the war-full 10-day for this seed. N2-P3 2,046,508 battleship 2 deaths. N1-P5 885,641 scout 6 deaths. N2-P4 873,242 cargotran 0. N3-P2 314,781 scout 20 deaths. N3-P1 263,107 scout 17 deaths. H-P6 16,006 scout 15 deaths. P3 laid 161 corporate armids and 58 corporate fighters. P5 laid 1 personal armid.

30-day seed 4242, war off, rejected 0/0, exceptions 0, digest `80c77c67`, total 7,544,495, elapsed 1114s. Day 10 matches the war-off 10-day. The report has no mines, pickets, deposits, or reaction. N3-P1 3,563,863 battleship 0 deaths. N2-P3 1,502,972 cargotran 2 deaths. N1-P5 1,308,791 cargotran 2 deaths. N2-P4 712,074 scout 4 deaths. N3-P2 440,789 cargotran 0 deaths. H-P6 16,006 scout 6 deaths. War on for this seed totals 4,399,285, and N3-P1 ends at 263,107 in a scout.

## Rules

| # | Rule | Mark | Constant | Test |
| --- | --- | --- | --- | --- |
| bw1 | Mode on. Legacy, policy off, and an LLM seat emit nothing new. N3 and N2 may siege. N1 and H only defend | OURS | `BOTS_WAR_MODE` tw2002, `BOT_WAR_POLICY` full, `BOT_WAR_SKILLS` N3/N2 full, N1/H defend | `test_bw1_mode` |
| bw2 | A threat map of seen planets, groups, mines, and intruders. Bounded. Built only from the seat's own observations | OURS | `BOT_WAR_MAP_MAX` 64 | `test_bw2_threat_map` |
| bw3 | Rival fighters and shields are trusted only when seen today, or padded when older than 3 days. Hidden fields are not read | CONFIRMED | `BOT_WAR_INTEL_STALE_DAYS` 3, `BOT_WAR_INTEL_STALE_PAD_PCT` 50 | `test_bw3_fog` |
| bw4 | Armids bought for home are laid at home, at a dead-end entrance, or at the best own planet. A shared corridor is not mined. Re-buy below 10. Never FedSpace or a swept lane | CONFIRMED | `BOT_WAR_HOME_MINES` 10 | `test_bw4_armids` |
| bw5 | Each guarded sector gets a defensive picket. The ship keeps 40% of its fighters. Offensive only at a dead-end entrance. Toll mode never. Travel pickets off | CONFIRMED | `BOT_WAR_PICKET_MIN` 10, `BOT_WAR_WALL_PCT` 20, `BOT_WAR_KEEP_ABOARD_PCT` 40, `BOT_WAR_OFFENSIVE_AT_ENTRANCE` True, `BOT_WAR_TRAVEL_PICKETS` False | `test_bw5_pickets` |
| bw6 | A solo deploy sends no new ownership arg. A corp bot sends corporate. A mate's group is not stacked, recalled, or attacked | CONFIRMED | — | `test_bw6_ownership` |
| bw7 | Citadels are stocked to a level ladder, best planet first, inside the purse and 25% of liquid net worth a day | STRATEGY | `BOT_WAR_PLANET_FIGHTERS_BY_LEVEL`, `BOT_WAR_PLANET_SHIELDS_BY_LEVEL`, `BOT_WAR_DEFENCE_BUDGET_PCT` 25 | `test_bw7_stock` |
| bw8 | At citadel 2 or higher, military reaction is set to 20 once. The 6666 workaround is not copied | CONFIRMED | `BOT_WAR_REACTION_PCT` 20 | `test_bw8_reaction` |
| bw9 | At citadel 3 or higher, quasar sector 30 and atmosphere 60, once. Planet ore stays at least 2000 | CONFIRMED | `BOT_WAR_QUASAR_SECTOR_PCT` 30, `BOT_WAR_QUASAR_ATM_PCT` 60, `BOT_WAR_QUASAR_ORE_FLOOR` 2000 | `test_bw9_quasar` |
| bw10 | Moving a discovered level-4 planet is implemented and off | STRATEGY | `BOT_WAR_MOVE_DISCOVERED` False | `test_bw10_move` |
| bw11 | A level-6 interdictor is priced into the siege estimate. The bot does not land there unless the hold is covered | CONFIRMED | `INTERDICTOR_MIN_LEVEL`, `INTERDICTOR_FUEL` | `test_bw11_interdictor` |
| bw12 | The 1639-shield bug, the 6666 reaction bug, and the Magic Moth cannon bug are not copied. An L5 planet with 1700 shields can be sieged | OURS | — | `test_bw12_no_shield_bug` |
| bw13 | After day 5, an N2 or N3 with a holo scanner and 2000 fighters may spend 10 turns and 1 probe a day scouting | STRATEGY | `BOT_WAR_START_DAY` 5, `BOT_WAR_SCOUT_MIN_FIGHTERS` 2000, `BOT_WAR_SCOUT_TURNS_PER_DAY` 10, `BOT_WAR_PROBES_PER_DAY` 1 | `test_bw13_scout` |
| bw14 | One siege sequence a day. Not a mate, an ally, or FedSpace. An orphan is claimed, not sieged. Two days of cooldown after a failure | STRATEGY | `BOT_WAR_SIEGES_PER_DAY` 1, `BOT_WAR_SIEGE_COOLDOWN_DAYS` 2 | `test_bw14_targets` |
| bw15 | The estimate replays shield soak, reaction waves, then the defensive grind, plus seen hazards and quasar. Attack only with 25% fighters left, at least 100, prize at least 1.5 times the fighter cost, and at most 40% of net worth at risk | OURS | `BOT_WAR_ASSUME_PLANET_ORE` 5000, `BOT_WAR_SIEGE_MARGIN_PCT` 25, `BOT_WAR_SIEGE_MIN_LEFT` 100, `BOT_WAR_PRIZE_MIN_RATIO` 1.5, `BOT_WAR_RISK_NW_PCT` 40 | `test_bw15_estimate` |
| bw16 | Buy fighters first, take a corp top-up between attempts, photon first when it is cheaper, then land. At most 3 land tries. Re-estimate after a repel | CONFIRMED | `BOT_WAR_LAND_TRIES` 3 | `test_bw16_execute` |
| bw17 | Leave when the margin breaks, when shields are gone under an atmospheric quasar, when a stronger ship arrives, or when fewer than 20 turns remain | STRATEGY | `BOT_WAR_RESERVE_TURNS` 20 | `test_bw17_retreat` |
| bw18 | After a capture, stock, set reaction and quasar, and lay a picket. Do not destroy the captured planet | CONFIRMED | — | `test_bw18_after_capture` |
| bw19 | If home was hit, go back within 8 hops, restock, re-lay, and retake the next day only if the estimate clears. Do not chase a ship across the map | STRATEGY | `BOT_WAR_DEFEND_MAX_HOPS` 8 | `test_bw19_defend` |
| bw20 | Ship hunting stays on the existing hunt rules, plus a siege ship parked at the bot's own planet when those odds already allow it | OURS | — | `test_bw20_hunt` |
| bw21 | One siege target per corp per day. Home defence comes first. A mate's corp planet may be restocked | CONFIRMED | — | `test_bw21_corp` |
| bw22 | War spending stays inside 30% of liquid net worth and the bank purse. Nothing before day 5 except home pickets of hardware already owned. A 30% net-worth drop switches to defend for 3 days | OURS | `BOT_WAR_DAILY_BUDGET_PCT` 30, `BOT_WAR_NW_DROP_STOP_PCT` 30, `BOT_WAR_COOLDOWN_DAYS` 3 | `test_bw22_budget` |
| bw23 | A good bot sieges only an evil owner or someone who already attacked it | STRATEGY | `BOT_WAR_GOOD_ATTACKS_ANY` False | `test_bw23_alignment` |
| bw24 | Every war verb is taken from the legal list, inside the legal max. No FedSpace deploy. No deploy into a rival group | OURS | — | `test_bw24_legal` |
| bw25 | War options compete on value per turn. N3 spends at most 40% of the day's turns on war, N2 at most 30% | OURS | `BOT_WAR_MAX_TURNS_PCT` 40 for N3, 30 for N2 | `test_bw25_turns` |
| bw26 | No random draw. The map, grudges, cooldowns, and the day's spend survive a save. Policy off stores nothing new | OURS | — | `test_bw26_save` |
| bw27 | `--war-report` counts mines, fighters, deposits, settings, scans, sieges, captures, losses, deaths, and spend | OURS | — | `test_bw27_report` |
| bw28 | The acceptance table names the args for reaction, quasar, defence deposit, and recall | OURS | — | `test_bw28_args` |
| bw29 | No prompt text. An LLM seat only sees the bots' deployments as ordinary game state | OURS | — | `test_bw29_llm` |
| bw30 | The gap map and the growth note point here | OURS | — | `test_bw30_docs` |

Level targets for bw7: fighters 500 / 2,000 / 5,000 / 10,000 / 20,000 / 30,000 at citadel 1 through 6. Shields 0 / 0 / 50 / 200 / 500 / 1,000.

## Findings

These are engine facts. This slice does not change them.

| # | Finding |
| --- | --- |
| F1 | A planet in your sector is fully visible. The original planet scanner shows owner and fighters only when the planet has no shields. Bots self-restrict (bw3). |
| F2 | Iago's military reaction fires when someone enters the sector. The engine applies that percent as waves during a landing. To be verified at the start commit. |
| F3 | MBBS shield odds are 22.5 to 1 divided by the ship's combat odds. The engine uses a flat `PLANET_SHIELD_ODDS` of 20. SOURCE-CONFLICT. |
| F4 | Iago's atmospheric quasar is 1 damage per 1 ore. The engine's `QUASAR_ATM_FACTOR` is 2. SOURCE-CONFLICT, already documented. |
| F5 | The engine seizes the planet, drops the citadel one level, and halves the treasury. No source found for the level drop or the half treasury. UNVERIFIED. |
| F6 | A trader landed in the citadel is not fought by the siege. To be verified with a characterisation test. |
| F7 | Toll fighters block a hostile landing until they are paid, retreated from, or attacked. That matches Iago. |
| F8 | Bots buy armids and do not lay them. The corridor guard and the forever `armids_stocked` flag are the cause. Fixed by bw4, not by deleting the corridor guard. |

## SOURCE-CONFLICT

F3 `PLANET_SHIELD_ODDS` 20 versus MBBS 22.5 divided by combat odds. F4 `QUASAR_ATM_FACTOR` 2 versus Iago's 3 times the sector cannon.

## UNVERIFIED

F5 the capture drops the citadel one level and halves the treasury.

## Decisions used

D1 policy `full`. D2 travel pickets off. D3 discovered-planet move off. D4 the open sector view stays (bots self-restrict). D5 F2, F3, F5, and F6 stay findings. D6 a good bot does not siege a good owner who never attacked it.

## NOT BUILT as engine changes

No new verb. No observation change. No prompt change. Ferrengi and alien war logic stay. Atomic detonation strategy stays. StarDock blockades stay.

## Planted bugs

Re-break is still ahead. Each named test fails when the bug is planted.

| Bug | Test |
| --- | --- |
| pb1 mines are bought once and never again | `test_bw4_armids` |
| pb2 a dead-end entrance is still treated as a corridor | `test_bw4_armids` |
| pb3 mines in FedSpace or a swept lane | `test_bw4_armids` |
| pb4 fighters deployed in toll mode | `test_bw5_pickets` |
| pb5 the picket leaves under 40% aboard | `test_bw5_pickets` |
| pb6 a solo bot sends an ownership arg | `test_bw6_ownership` |
| pb7 a corp bot deploys personal | `test_bw6_ownership` |
| pb8 fighters stacked onto a mate's group | `test_bw6_ownership` |
| pb9 stocking spends the bank purse | `test_bw7_stock` |
| pb10 reaction set again every visit | `test_bw8_reaction` |
| pb11 quasar set below the minimum level | `test_bw9_quasar` |
| pb12 planet ore sold below the quasar floor | `test_bw9_quasar` |
| pb13 the threat map reads the universe | `test_bw2_threat_map` |
| pb14 the estimate skips the shield soak | `test_bw15_estimate` |
| pb15 reaction waves use the defensive odds | `test_bw15_estimate` |
| pb16 the margin gate is inverted | `test_bw15_estimate` |
| pb17 the risk cap uses ship value | `test_bw15_estimate` |
| pb18 a mate or ally is sieged | `test_bw14_targets` |
| pb19 more than 3 land tries, or no cooldown | `test_bw16_execute` |
| pb20 no new estimate after a repel | `test_bw16_execute` |
| pb21 no retreat when shields are gone under a quasar | `test_bw17_retreat` |
| pb22 the defence chase exceeds 8 hops | `test_bw19_defend` |
| pb23 a good bot sieges a good owner | `test_bw23_alignment` |
| pb24 a random tie-break | `test_bw26_save` |
| pb25 a net-worth drop stays in defend forever | `test_bw22_budget` |
| pb26 legacy mode still lays the new pickets | `test_bw1_mode` |
