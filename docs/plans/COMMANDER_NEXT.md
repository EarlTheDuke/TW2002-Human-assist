# COMMANDER_NEXT

Standing mailbox for TW2K Dev Commander.

Report Page: https://cursor.com/canvas/store-edda9433-2d33-4b62-8d22-af10c2ff3895/b7c0b37a-f606-4a76-a69c-426bc1689683

Playtest wrap: `docs/playtests/multibot-2026-10-24-sat-grok-l3/README.md`

Tip parent: `feature/grokbot-player` @ `5a8cab96` (GAP 1.5, random StarDock under the v3.11 profile). This change folds the 2026-10-25 Ven GameA lasers into GAP 2.15 and grades that row Match-behind-flag. Class 2 New Cesium 55/482, class 3 Peleus 86/873, and class 5 Aesculapius 59/391 are in `PORT_LASER_BARRAGE`. Non-Fed class 8 Vergil Minor 99/954 stays on `PORT_ATTACK_GAMEA_SAMPLES` and is not written into the class maps. Fed prior class 8 stays FED_PRIOR (def 91 / laser 701) and unwired. Counts are 75 Match, 96 Match-behind-flag, 0 Partial, 0 Ben-decision. 4.10 stays Match-behind-flag in the every-row list. Its October cell still says Partial for duration and was not regraded. `PORT_ATTACK_MODE` and `PORT_ATTACK_ALL_CLASSES_MODE` stay legacy. Parent `ec4bc50b` is Libram key C. The parent change on `5a8cab96` is GAP 1.5 on `STARDOCK_LOCATION_MODE` row 236. Parent `2ba08a05` is the verified deferral tip (#189). The mailbox sha `307f2b07` is not an object on this branch. Parent `fec5d73c` is the verified #188 tip (Grade GAP 12.4 nightly Extern as Match-behind-flag). That parent already contains #187 (GAP 4.8), #186 (R1–R14), #180, the handbook curve (#183), the port-attack samples (#185), attack turns row 228 (#164), ship capacity row 229 (#163), the photon-cloak card row 230 (#161), Tri-Cron row 231 (#160), Grimy tips row 232 (#155), StarDock doors row 233 (#153), the interdictor damp row 234 (#171), the limpet and rename capture (#154), the full TWSTATS capture (#157), the October Missing-cell close (#173), and the leftover grades (#181). `SELF_DESTRUCT_PENALTY_MODE` is row 235. GAP 1.5 is Match-behind-flag. Ben approved the Commander recommendation 2026-10-24. Off, StarDock stays in sector 1. On, generation places it in a random ordinary sector. Terra stays sector 1. FedSpace is sectors 1-10 plus that sector. Ben-decision count is 0. Partial count is 0. GAP 4.8 detonation is Match. The shop unit price is Match-behind-flag on `HARDWARE_PRICE_MODE`. No third Armid price was added. GAP 12.4 is Match-behind-flag. No new switch for 12.4. `INACTIVE_USER_MODE` and `INACTIVITY_TIMEOUT_MODE` stay off. Libram key C, Miscellaneous Documents, lists Ferrengi hulls present on a living ship in this game. Keys A and B stay the capture header and an empty line. No ANSI. No Alien Derelict text. `STARDOCK_DOORS_MODE` row 233 is the same switch. The singles bar still takes no credits. The unnamed 47-credit drop stays deferred. Photon duration recommends cabal and the modern manual, 1 second, already `PHOTON_WAVE_DURATION` 1 day-tick.

## Standing queue

1. Remaining step before the next Class L ferry is a wt_live redeploy. Player of Games will request that redeploy when about to ferry.
2. Hotter L3 retest start bank is **2M** credits. Decided by the Commander under Ben's proactive grant.
3. Ops note: Computer Use seats 1–3 min/action; double-queue re-fire observed. Plan around that for the next multi-bot.
4. DONE. GAP 6.3 handbook curve is Match-behind-flag on the tip (#183). Do not regress.
5. DONE. GAP 2.15 lasers are in. Grade is Match-behind-flag. Classes 2, 3, and 5 are 482, 873, and 391 in `PORT_LASER_BARRAGE` (defs 55, 86, 59). Vergil Minor laser 954 stays sample-list only. Engine class 8 maps are untouched. Fed prior class 8 stays FED_PRIOR and unwired. Do not regress classes 1, 4, 6, and 7 (46/337, 110/1419, 98/598, 98/1121). Tip parent `5a8cab96`.
6. DONE. R1–R14 from `docs/plans/V311_RULINGS_FOR_BEN.md` are adopted. Grades are in `docs/plans/gap-map-refresh-v6.md`.
7. DONE. GAP 4.8 detonation is Match. Shop unit price is Match-behind-flag on `HARDWARE_PRICE_MODE` (stored 100, live card 1,000). No third price.
8. DONE. GAP 12.4 is Match-behind-flag (`fec5d73c`). The printed Extern and midnight jobs already run from `runner.tick_day`. Collisions, Class 0 and Class 9 rebuilds, inactive deletion, and the lobby timeout stay on switches that already exist. No new switch. Do not regress `INACTIVE_USER_MODE` or `INACTIVITY_TIMEOUT_MODE`.
9. The merge stack is cleared. Drafts #25, #28, #37, #82, #99, and #103 stay draft and out of merge order.
10. DONE as a deferral (`2ba08a05`). A singles-bar price and a named 47-credit drop are not printed. The mailbox sha `307f2b07` is not an object on this branch. Quotes are in `V311_REMAINING.md` 1.8 and `V311_SOURCE_CONFLICTS.md`. Photon duration (GAP 4.10): recommend cabal and the modern manual, 1 second, for v3.11. That reading is already `PHOTON_WAVE_DURATION` 1 day-tick. Gypsy 10 seconds and GameA 20 seconds stay recorded. No duration switch.
11. DONE (`ec4bc50b`). Libram key C (Miscellaneous Documents) lists Ferrengi hulls present on a living ship. Plain text from `FERRENGI_HULL_SPECS` and the live odds chart. Keys A and B stay the capture header and one empty line. No new switch. No ANSI. No Alien Derelict text. `STARDOCK_DOORS_MODE` row 233 stays legacy by default.
12. DONE. GAP 1.5 is Match-behind-flag on `STARDOCK_LOCATION_MODE` row 236. Ben approved the Commander recommendation 2026-10-24. A stored game keeps StarDock in sector 1. `V311_PROFILE=v311` places it in a random ordinary sector at generation. Terra stays sector 1. FedSpace is sectors 1-10 plus that sector. The string `1` does not turn the switch on. Do not invent a fixed sector, Alien Derelict text, bar prices, or lasers.

## Blockers

- The Class L ferry waits on the wt_live redeploy. Player of Games requests it.
- Ben-decision is closed. GAP 1.5 is Match-behind-flag on `STARDOCK_LOCATION_MODE` row 236.
- Drafts #25, #28, #37, #82, #99, and #103 stay open and out of merge order. They are not the next merge.

## Adopted R1–R14

| Reply | Row | Grade | Switch |
|---|---|---|---|
| R1 A | 1.6 Terra 100,000 / 1 per hold | Match | `TERRA_COLONIST_MODE` left as documented |
| R2 A | 1.15 Fed tow more than 50 | Match-behind-flag | `FED_TOW_LIMIT_MODE` row 168, already wired |
| R3 A | 2.5 two price lists | Match-behind-flag | left |
| R4 A | 4.1 Genesis 25,000 | Match | `GENESIS_TORPEDO_COST` is 25000. Live card 20,000 stays on the hardware switch |
| R5 B | 5.14 self-destruct | Match-behind-flag | `SELF_DESTRUCT_PENALTY_MODE` row 235, new, default legacy. Row 228 stays `ATTACK_TURN_MODE` |
| R6 A | 5.20 FedSpace more than 50 | Match-behind-flag | `FEDSAFE_FIGHTER_CAP_MODE` row 167, already wired |
| R7 A | 6.2 Class M L1 printed 1,000 | Match | `CLASS_M_FIDELITY_MODE` was not flipped |
| R8 A | 8.1 Bible Ferrengi odds | Match-behind-flag | `FERRENGI_ODDS_MODE` row 200 |
| R9 B | 9.8 rob x6 / steal /21 | Match | stored factors |
| R10 A | 10.1 CEO buys, member may board | Match | `CFS_CEO_USE_MODE` taken off the profile |
| R11 A | 11.11 no bubbles, no Gold | Match-behind-flag | already |
| R12 A | 12.3 turns stay | Match | `PLANET_REALTIME_PROD_MODE` stays off |
| R13 A | 12.6 no lockout | Match-behind-flag | `TIMES_BLOWN_MODE` row 202 |
| R14 A | 14.6 alliances off, credit finish stays | Match-behind-flag | `ECON_WIN_MODE` taken off the profile |

`CLASS_M_FIDELITY_MODE` still multiplies class M colonists by 1,000 when the profile is on (NOTE 19). R7 A did not turn that on or off. The adopted citadel figure is the printed 1,000, which a normal game uses.

## 2026-10-24 — Sat Grok L3 wrap (`82578bfe`)

Ben ended Sat Grok L3 game `82578bfe` and asked this wrap folded into GAP_MAP, this mailbox, and the standing queue.

- Day 10 stop. Start bank 500k credits. Six seats. Zero citadels.
- Seats: P1 and P2 real Grok Computer Use, P3 Qwen TinyBox, P4 Kimi TinyBox, P5 and P6 heuristic.
- P1 New 270-206 Class L: stockpile 150/125/150 (L1 goods met). Colonists only ~40/400 after Leave false class-cap on qty=75 people.
- P2 Mid Eden #50 Class L: goods above L1. Colonists 336/400. Closest to L1.
- Cash at stop: P4 227k, P2 201k, P1 91k, P3 70k, P6 19k, P5 18k.
- GWC lobby empty. Dual-seat watch paused. Original EIS TWGS :23 left running (untouched).

## 2026-10-25 — GAP 2.15 Ven GameA lasers

Player of Games measured TW Test Game 2 (Slot A), TW2002 v3.34b under TWGS v2.20b. Capture: `docs/playtests/twgs-live/gap215-port-attack-2026-10-25.md` (JSON: `docs/playtests/twgs-live/gap215_final.json`). Method: a 0-fighter commit aborts after the def and shield text, then a 1-fighter commit records the laser battle points.

CONFIRMED this pass: class 2 New Cesium sector 160, def 55 / laser 482 / plasma; class 3 Peleus sector 436, def 86 / laser 873 / Class 2 Halos; class 5 Aesculapius sector 404, def 59 / laser 391 / plasma; class 8 Vergil Minor sector 119 (non-Fed), def 99 / laser 954 / Class 4 Sunstorm. Those four rows were DEF_ONLY on 2026-10-24.

Unchanged: class 1 H'Catha 46/337, class 4 Duriron Minor 110/1419, class 6 Khancuhn Primus 98/598 KNOWN, class 7 Balmer 98/1121. Class 0 Sol and class 9 StarDock stay BLOCKED. Fed prior class 8 REPORT def 91 / laser 701 / class 3 shielding stays FED_PRIOR and unwired. Variance samples Leipzig, Mastro, Anaxagoras Primus, and Mirador Outpost stay def-only.

`PORT_LASER_BARRAGE` gained 482, 873, and 391 for classes 2, 3, and 5. Class 8 was not written into `PORT_DEFENSE_RATING` or `PORT_LASER_BARRAGE`. `_port_attack_gamea_row` still returns None for class 8. GAP 2.15 is Match-behind-flag. Counted grades: 75 Match, 96 Match-behind-flag, 0 Partial, 0 Ben-decision. 4.10 stays Match-behind-flag in `gap-map-refresh-v6.md`. The October GAP_MAP cell for 4.10 still says Partial for duration and was left as written.

## 2026-10-24 — GAP 2.15 Ven GameA port-attack ratings

Player of Games measured TW Test Game 2 (Slot A), TW2002 v3.34b under TWGS v2.20b. Capture: `docs/playtests/twgs-live/gap215-port-attack-2026-10-24.md` (JSON: `docs/playtests/twgs-live/gap215_final.json`). EIS :23 was not touched.

CONFIRMED lasers: class 1 H'Catha sector 478, 337 battle points (def 46); class 4 Duriron Minor sector 122, 1419 (def 110); class 6 Khancuhn Primus, 598 (def 98, prior REPORT2); class 7 Balmer sector 688, 1121 (def 98). DEF_ONLY: class 2 New Cesium 160 def 55, class 3 Peleus 436 def 86, class 5 Aesculapius 404 def 59, class 8 Vergil Minor 119 (non-Fed) def 99. BLOCKED: class 0 Sol and class 9 StarDock.

A 0-fighter commit aborts after the def and shield text. Def rating is per port (class 3 Peleus 86 vs Anaxagoras Primus sector 913 def 60). Non-Fed class 8 (def 99, class 4 Sunstorm) differs from the Fed class 8 prior (def 91 / laser 701). This fold did not change the engine. Tip #185 (`7fd2db0d`) then stored the confirmed samples in `PORT_DEFENSE_RATING` and `PORT_LASER_BARRAGE`: class 1 H'Catha 46/337, class 4 Duriron Minor 110/1419, class 6 Khancuhn Primus 98/598, class 7 Balmer 98/1121, and DEF_ONLY defs for class 2 (55), class 3 (86), and class 5 (59). The class 6 pair is one row in that set. GAP 2.15 stays Partial because lasers for classes 2, 3, 5, and non-Fed 8 are still unmeasured.

## Standing queue (superseded)

The queue at the top of this file replaces the list that used to sit here. The capture notes below stay as history. GAP 2.15 numbers were not invented in this note; they are the measured samples already on the tip.
