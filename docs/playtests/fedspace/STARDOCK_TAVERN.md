# StarDock tavern and Underground (TAVERN_MODE)

Lost Trader's Tavern and the hidden Underground, as TWGS 3.11 documents them. Slice 62, `stardock-tavern-underground-v1`. Starts from origin `2ba6ea9` (slice 61 delivered).

Switch: `K.TAVERN_MODE` (`tw2002` default; `legacy` = byte-identical to `2ba6ea9`). Helper `K.tavern_on()`. Code bots stay out: `K.BOT_TAVERN_POLICY = "off"`.

Sources under `C:\Users\sugar\tw2002_reference\`. Target TWGS 3.11; MBBS is the tie-breaker. Marks: CONFIRMED / SOURCE-CONFLICT / UNVERIFIED / OURS / DERIVED.

**Legacy (`TAVERN_MODE = "legacy"`):** the nine verbs are absent and handlers answer "unsupported action"; no tavern observation block; no dock log written or dumped; no Player or Universe tavern field written; no contract hook; no prompt paragraph; no tavern event; no rng consumed.

## Rules table

| # | rule | original | mark and source | this slice (TAVERN_MODE tw2002) | test |
| --- | --- | --- | --- | --- | --- |
| tv1 | Mode | — | OURS. | `TAVERN_MODE` `tw2002` \| `legacy`. `tavern_on()`. | `test_tv1_mode` |
| tv2 | Where | Tavern and Underground are at StarDock. Pod may enter. | CONFIRMED EISSD 49-53, BIB 329-345. DERIVED guard copies `bank.guard`. | Sector `STARDOCK_SECTOR`, alive, in the ship, not landed. Escape pod and the free Scout may enter. `TAVERN_TURN_COST = 0` except the curse. | `test_tv2_guard` |
| tv3 | Announcement | Pay the fee; one notice until the next is posted. | CONFIRMED EIST, TWGSSET 224, MMSET 100, BIB 1414. Length UNVERIFIED (GYPN 463-467 is a different board). Signed UNVERIFIED. | `tavern_announce {text}`. `TAVERN_ANNOUNCE_COST = 100` from credits on hand. One board slot, replaced. Text 1..`TAVERN_TEXT_MAX = 160`, one line, controls stripped. `TAVERN_ANNOUNCE_SIGNED = True`. Shown to every seat in StarDock, with the day. | `test_tv3_announce` |
| tv4 | Conversation | Eavesdrop and add remarks. Live bar chat is a fourth channel. | CONFIRMED EIST, EISGN 80-84, REV 599. Cost UNVERIFIED. Keep-count OURS (HVS 406-411: sysop clears it). | `tavern_talk {text}`. `TAVERN_TALK_COST = 0`. Named, with day. Last `TAVERN_CONVERSATION_KEEP = 20` lines. Live chat is this table. | `test_tv4_talk` |
| tv5 | Graffiti | Anonymous wall. | CONFIRMED BIB 1410-1413, EIST, HVS 412-414. Cost UNVERIFIED. Keep-count OURS. | `tavern_graffiti {text}`. `TAVERN_GRAFFITI_COST = 0`. Author id and name stored nowhere a rival, the replay, or a public event can read. Last `TAVERN_WALL_KEEP = 10` lines. No stall effect. | `test_tv5_graffiti` |
| tv6 | Bar and food | Buy a drink or the Blue Plate Special. | CONFIRMED they exist (EIST). Prices UNVERIFIED. Date scaling UNVERIFIED (IAGO 2247-2249). | `tavern_order {item: drink\|food}`. `TAVERN_DRINK_COST = 20`, `TAVERN_FOOD_COST = 20`. No other field changes. `TAVERN_PRICE_SCALING = "flat"`. | `test_tv6_order` |
| tv7 | Grimy topics | Ask about a topic. | CONFIRMED EIST, BIB 1421-1429. | `grimy_ask {topic, target?}`. Topics `trader`, `underground`, `mafia`, `tricron`, plus lore. Any other topic is a free shrug. | `test_tv7_topics` |
| tv8 | Trace | One port the current ship has docked at. | CONFIRMED IAGO 198-201, REV 783, SLICE 1660-1680. SOURCE-CONFLICT one port vs some ports. Cost UNVERIFIED ("a few thousand"). Pick UNVERIFIED (SLICE says random). Miss charge UNVERIFIED. Lies UNVERIFIED. | `GRIMY_TRACE_COST = 3000`. `GRIMY_TRACE_PORTS = 1`. `GRIMY_TRACE_PICK = "hashed"` (sha256 of seed, day, asker, target). Never-docked hull: nothing, and `GRIMY_CHARGE_ON_MISS = False`. Cloaked target traced. Target is not told. No Ferrengi or alien. `GRIMY_TRACE_LIES = False`. | `test_tv8_trace` |
| tv9 | Dock log | Trace reads ports this hull has docked at. | DERIVED SLICE 1672-1676, EISSY 55-59. Cap UNVERIFIED. | `Ship.dock_log` and `ParkedShip.dock_log`: port sector ids, most recent last, consecutive duplicates collapsed, cap `GRIMY_DOCK_LOG_MAX = 10`. Appended on successful trade, rob, steal, planet trade, and port upgrade. New hull empty. Parked and captured hulls keep the log. Written only under tw2002. | `test_tv9_dock_log` |
| tv10 | Password | Grimy sells the Underground password. | CONFIRMED MBBS 1728-1733, TWFAQ 96-101, TWGS2 89. Cost UNVERIFIED. Default phrase is public. | `GRIMY_PASSWORD_COST = 2000`, once. `ug_password_known`. Shown only in that seat's block. `UG_PASSWORD_SOURCE = "seeded"` (D1): three words from a fixed list via sha256 of the game seed. Alt `twgs_default` = `BEWARE OF KAL DURAK`. Already known: refused, no charge. | `test_tv10_password` |
| tv11 | Tri-Cron tip | Grimy names a combination. The game is a lie. | CONFIRMED BIB 1418-1419. Cost UNVERIFIED. | Free. Fixed answer `2-3-1`. No effect. Tri-Cron is not built. | `test_tv11_tricron_tip` |
| tv12 | Lore | Grimy has a lore file. The file is not in the library. | OURS flavour. Hoax texts CONFIRMED TWFAQ 76-81, IAGO 4276. | `GRIMY_LORE`: computer upgrade (hoax), vulcan thunder (no secret), gary martin (credit). Free, fixed, no state change. | `test_tv12_lore` |
| tv13 | Curse | −1 alignment and −1 experience. | CONFIRMED CF 1341-1345, BIB 582-588, SLICE 1787. SOURCE-CONFLICT once a day (REV 660-662) vs unlimited macros. Turns UNVERIFIED. | `grimy_curse`. −1 / −1. Experience never below 0. `GRIMY_CURSES_PER_DAY = 1`. `GRIMY_CURSE_TURNS = 1`. `GRIMY_RUDE_MARKUP_PCT = 0`. | `test_tv13_curse` |
| tv14 | Entry | Undisplayed U. Alignment ceiling. | CONFIRMED BIB1 527-530, MBBS 1732. SOURCE-CONFLICT 199 (TWFAQ 90-95, CGL, GLOSS, IAGO) vs 100 (MBBS, MISC). | `underground_enter {password}`. `UG_MAX_ALIGNMENT = 199`. Above that: turned away, attempt not counted. Right password sets `ug_entered_day` for the rest of the day at StarDock. `UG_PASSWORD_MATCH = "loose"` (case-insensitive, spaces collapsed). The verb is in the legal list before the password is known, and it is not legal until then (`UG_VERB_VISIBILITY = "known"`). The parity matrix needs one entry per action. A guess still counts. | `test_tv14_enter` |
| tv15 | Wrong passwords | Mug, then halve experience, then murder. | SOURCE-CONFLICT MBBS 4th mug / 5th half / then murder vs TWFAQ 6th kill. Day reset CONFIRMED GLOSS 245. | Per trader per day. `UG_MUG_AT = 4`: credits on hand leave the economy; bank, planets, treasuries stay. `UG_EXP_HALVE_AT = 5`: experience // 2. `UG_MURDER_AT = 6`: `#SD#` never a pod (`UG_MURDER_POD = False`), Scout, out until tomorrow, experience 0, alignment 0, planets, corp, bank, fleet, deployments stay. `UG_MURDER_COUNTS_DEATH = True`. Public `UG_MURDER`. Attempts 1–3: "wrong password". | `test_tv15_ladder` |
| tv16 | Hit contracts | Post a bounty. −1 alignment per 250 credits (−4 per 1,000). | CONFIRMED BIB 1431-1437, IAGO 552-559, MBBS 1723-1763. Min amount UNVERIFIED. | `underground_contract {target, amount}`. Needs entry today. Any non-eliminated trader, including yourself (`UG_CONTRACT_SELF = True`). Never Ferrengi or alien. `UG_CONTRACT_MIN = 1000` from credits on hand. Alignment drops by `amount // UG_CREDITS_PER_ALIGN` with `UG_CREDITS_PER_ALIGN = 250`. Stored on `universe.tavern.ug_contracts`, separate from Police rewards. 0 turns. | `test_tv16_contract` |
| tv17 | Earn and claim | Collect contracts when that trader's ship is destroyed. | CONFIRMED IAGO 556-558. Payout trigger UNVERIFIED (same reading as Police f19). | `UG_CONTRACT_PAYOUT_ON = "ship_destroyed"`: another player's kill, not a pod, moves every open contract on the victim to the killer's pending pool. Pod, Ferrengi, alien, mine, Fed, or murder pays nobody. `underground_claim` pays the whole pending pool to credits on hand, and needs entry today. A killer above 199 cannot enter, so cannot claim. Eliminated target: `UG_CONTRACT_ON_ELIMINATION = "sink"`. Conservation: posted = open + pending + claimed + forfeited. | `test_tv17_earn_claim` |
| tv18 | What Underground shows | — | UNVERIFIED. | `UG_SHOW_CONTRACTS = "totals"`. Inside: each open target's name and total, never the posters, plus own pending. Outside: nothing. | `test_tv18_show` |
| tv19 | Name change | Exists. Price by experience, formula unknown. | CONFIRMED it exists (REV 664-666). NOT BUILT. | `UG_NAME_CHANGE = False` (D5). | `test_tv19_name_change_unbuilt` |
| tv20 | Tri-Cron | Exists. Cost and a round are not documented. | CONFIRMED it exists (EIST). NOT BUILT. | `TAVERN_TRICRON = "off"` (D4). | `test_tv20_tricron_unbuilt` |
| tv21 | Other buildings | Singles Bar, Library, Cineplex, illegal goods. | CONFIRMED they are named. NOT BUILT. | Listed below. | `test_tv21_other_unbuilt` |
| tv22 | Observation | — | OURS shape. | `tavern` block only in StarDock under tw2002: announcement, conversation (last `TAVERN_CONVERSATION_SHOW = 10`), graffiti (last `TAVERN_WALL_SHOW = 5`, no author), prices, `curse_used_today`, `password_known`, own `ug_password` once bought, own `last_trace` today, underground sub-block only when entered today. Quoted as other traders' text. | `test_tv22_observation` |
| tv23 | Legal list | Legal equals the handler. | DERIVED. | Nine verbs with the args and refusal reasons in the spec tv23. | `test_tv23_legal` |
| tv24 | Fog | Trace and password stay private. | CONFIRMED the crowd can lurk (EIST). OURS enforcement. | Trace, password, attempts, mugging, experience loss, contracts, and claims are actor-only. `UG_MURDER` is the one public Underground event. Password string never in a public event, another seat's observation, the replay summary, brain logs, or `--json`. | `test_tv24_fog` |
| tv25 | LLM text | — | OURS. Numbers from K. | One tw2002 paragraph via `rules_text.py`. Absent in legacy. | `test_tv25_prompt` |
| tv26 | Code bots | — | OURS. D7. | `BOT_TAVERN_POLICY = "off"`. SeatBrain and H never emit a tavern verb. `REQUIRED_ARGS` gains the nine verbs. | `test_tv26_bots_off` |
| tv27 | Determinism | — | OURS. | No `universe.rng` and no `random`. Day-tick work sorted by player id. | `test_tv27_deterministic` |
| tv28 | Persistence | — | OURS. | `Universe.tavern`, the Player flags, and dock logs omitted at defaults, survive save/load, never written under legacy. | `test_tv28_save_load` |
| tv29 | Day tick | Curse and wrong-password counters reset. | CONFIRMED GLOSS 174, 245. | Reset by day stamp. Nothing else at the tick. | `test_tv29_day_reset` |
| tv30 | Elimination | — | DERIVED. | An eliminated trader cannot use a verb, is not a target, and his pending pool is forfeited. | `test_tv30_elimination` |
| tv31 | Docs | — | OURS. | This file. GAP_MAP 1.8, 9.5, 11.4, 11.7, 11.8 and the FEDSPACE_POLICE f19 cross-reference land with the engine. | n/a until the engine lands |
| tv32 | Rejected 0 | — | OURS. | Legal list equals the handler for all nine verbs. | `test_tv32_legal_equals_handler` |

## SOURCE-CONFLICT

| constant | this slice | the other reading |
| --- | --- | --- |
| `GRIMY_TRACE_PORTS` | 1 (REV 783) | "some ports" (SLICE) |
| `GRIMY_CURSES_PER_DAY` | 1 (REV 660-662) | unlimited macros (BIB1, SLICE) |
| `UG_MAX_ALIGNMENT` | 199 (TWFAQ) | 100 (MBBS, MISC) |
| wrong-password ladder | mug 4 / halve 5 / murder 6 | TWFAQ names only the 6th kill |

## UNVERIFIED constants

`TAVERN_TURN_COST` 0, `TAVERN_TEXT_MAX` 160, `TAVERN_ANNOUNCE_SIGNED` True, `TAVERN_TALK_COST` 0, `TAVERN_GRAFFITI_COST` 0, `TAVERN_DRINK_COST` 20, `TAVERN_FOOD_COST` 20, `TAVERN_PRICE_SCALING` flat, `GRIMY_TRACE_COST` 3000, `GRIMY_TRACE_PICK` hashed, `GRIMY_CHARGE_ON_MISS` False, `GRIMY_TRACE_LIES` False, `GRIMY_DOCK_LOG_MAX` 10, `GRIMY_DOCK_ACTIONS` trade/rob/steal/planet_trade/port_upgrade, `GRIMY_PASSWORD_COST` 2000, `GRIMY_CURSE_TURNS` 1, `GRIMY_RUDE_MARKUP_PCT` 0, `UG_PASSWORD_MATCH` loose, `UG_MURDER_POD` False, `UG_MURDER_COUNTS_DEATH` True, `UG_CONTRACT_MIN` 1000, `UG_CONTRACT_PAYOUT_ON` ship_destroyed, `UG_CONTRACT_ON_ELIMINATION` sink, `UG_SHOW_CONTRACTS` totals.

## OURS constants

`UG_PASSWORD_SOURCE` seeded, `UG_VERB_VISIBILITY` known, `TAVERN_CONVERSATION_KEEP` 20, `TAVERN_CONVERSATION_SHOW` 10, `TAVERN_WALL_KEEP` 10, `TAVERN_WALL_SHOW` 5, `UG_NAME_CHANGE` False, `TAVERN_TRICRON` off, `BOT_TAVERN_POLICY` off.

## NOT BUILT

Tri-Cron. Underground name change. Singles Bar. Library. Cineplex. Illegal goods. Computer-menu Daily Log announcement. Shipyard re-registration. Live real-time bar chat (merged into the conversation). Prices that grow with the game date. Code-bot use of the Tavern.

## Decisions used

D1 seeded password. D2 alignment ceiling 199. D3 ladder 4/5/6. D4 Tri-Cron unbuilt. D5 name change unbuilt. D6 trace 3000, password 2000, drink and food 20, curse 1 turn. D7 code bots off. D8 free-text boards on, shown as quoted data.

## Planted bugs

Re-break is still ahead. Each named test failed when the bug is planted.

| Bug | Test |
| --- | --- |
| pb1 a verb is legal away from StarDock | `test_tv2_guard` |
| pb2 a free announcement, or two notices stay up | `test_tv3_announce` |
| pb3 announcement text is not capped | `test_pb3_announcement_capped` |
| pb4 a graffiti event names the author | `test_tv5_graffiti_has_no_author` |
| pb5 the conversation grows past 20 | `test_tv4_talk_and_pb5_conversation_capped` |
| pb6 a trace returns the current sector | `test_tv8_trace_and_tv9_dock_log` |
| pb7 a trace returns every port | `test_tv8_trace_and_tv9_dock_log` |
| pb8 a trace charges on a miss | `test_tv8_trace_and_tv9_dock_log` |
| pb9 the trace uses universe.rng | `test_tv27_deterministic` |
| pb10 the dock log is written under legacy, or kept on a new hull | `test_tv8_trace_and_tv9_dock_log`, `test_tv9_new_hull_starts_empty` |
| pb11 the password leaks | `test_tv10_password_and_tv24_fog` |
| pb12 the password match is case-sensitive | `test_tv14_enter_and_tv22` |
| pb13 a second curse, or experience below 0 | `test_tv13_curse` |
| pb14 entry at alignment 200 | `test_tv14_enter_and_tv22` |
| pb15 the attempt counter does not reset | `test_tv15_ladder_and_tv29` |
| pb16 a mugging takes the bank | `test_tv15_ladder_and_tv29` |
| pb17 murder on the 5th try, or through a pod, or experience left on | `test_tv15_ladder_and_tv29` |
| pb18 alignment drops 1 per 1,000 | `test_tv16_tv17_tv18_and_pb26` |
| pb19 a pod kill pays the contract | `test_tv16_tv17_tv18_and_pb26` |
| pb20 a claim without entering | `test_tv16_tv17_tv18_and_pb26` |
| pb21 posters are shown | `test_tv16_tv17_tv18_and_pb26` |
| pb22 underground_enter is listed before the seat knows | `test_tv14_enter_and_tv22` |
| pb23 legacy shows the block or the verbs | `test_tv1_mode` |
| pb24 a code bot emits a Tavern verb | `test_tv26_bots_off` |
| pb25 the paragraph is hard-coded or present in legacy | `test_tv25_prompt` |
| pb26 claim_reward pays an Underground contract | `test_tv16_tv17_tv18_and_pb26` |

## Match check

Scenario lab `scripts/stardock_tavern_scenario_lab.py` PASS: one announcement, anonymous graffiti, an empty new hull traces for free, a docked port costs 3,000, password 2,000, alignment 250 turned away, the 4/5/6 ladder, a pod pays nothing, a real kill pays 10,000, one curse a day.

10-day scripted seats N3,N3,N2,N2,N1,H. Tavern on and legacy are the same action stream. Rejected 0/0, exceptions 0.

Seed 250925, digest `16ad8833`. N3-P1 766,412 cargotran 0 deaths. N2-P3 387,649 cargotran 0. N1-P5 281,031 cargotran 0. N3-P2 163,396 cargotran 0. N2-P4 161,357 cargotran 0. H-P6 50,003 scout 2 deaths.

Seed 424242, digest `4b8d71e0`. N3-P1 753,296 cargotran 0. N2-P3 661,758 cargotran 0. N2-P4 176,554 cargotran 0. N3-P2 134,373 cargotran 0. N1-P5 17,975 scout 2 deaths. H-P6 7,975 scout 4 deaths.

An empty StarDock observation is 29,277 bytes with the tavern on and 27,308 with it off, 1,969 bytes more.

30-day headless, 6 heuristic seats, seed 250925, on `344cb5e` plus the soak print. Stress (2% of StarDock decisions replaced by a legal Tavern verb) elapsed 2633.8s, day-15 save/load identical, events 203291, contract books balanced at 0 posted, no negative credits, exit 0. Legacy elapsed 2717.5s, day-15 save/load identical, events 203184, books balanced, no negative credits, exit 0. Stress was 3% faster than legacy. Re-broke pb1 through pb26 on this tree. Each named test failed, and the source was restored. Re-broke them again on 3a165ee after the parity fix. Each named test failed, and the source was restored. Suite on 3a165ee: 2297 passed, 2 failed, 1 skipped, 3088s. Both failures are the known flakes and both failed alone: WinError 10048, and the spectator-feed timeout.
