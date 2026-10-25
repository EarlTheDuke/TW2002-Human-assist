# COMMANDER_NEXT

Standing mailbox for TW2K Dev Commander.

Report Page: https://cursor.com/canvas/store-edda9433-2d33-4b62-8d22-af10c2ff3895/b7c0b37a-f606-4a76-a69c-426bc1689683

Playtest wrap: `docs/playtests/multibot-2026-10-24-sat-grok-l3/README.md`

Tip parent: `feature/grokbot-player` @ `7a0fcf03` (#193, Fold 2026-10-25 Ven GAP 2.15 lasers). Counts: 75 Match, 96 Match-behind-flag, 0 Partial, 0 Ben-decision. The Dev fidelity backlog is empty (171/171). The October GAP_MAP cell for 4.10 duration is Match-behind-flag, aligned with the every-row list in `docs/plans/gap-map-refresh-v6.md` and with `docs/plans/V311_REMAINING.md`. Duration recommendation is cabal and the modern manual, 1 second. The tip already maps that to `PHOTON_WAVE_DURATION` 1 day-tick. Gypsy 10 seconds and GameA 20 seconds stay recorded. No realtime clock. No duration switch. Limpet, interdictor, and price subgrades were not flipped. `PORT_ATTACK_MODE` and `PORT_ATTACK_ALL_CLASSES_MODE` stay legacy.

## Standing queue

The Dev fidelity backlog is empty (171/171). No standing GAP item is left for the next Dev session.

PoG (Player of Games), not Dev:

1. wt_live redeploy, on request. The Class L ferry waits until Player of Games asks for that redeploy.
2. Hotter L3 retest start bank is **2M** credits and is already live on their side. Decided by the Commander under Ben's proactive grant.

Ops note, not a fidelity gap: Computer Use seats 1–3 min/action; double-queue re-fire observed. Plan around that for the next multi-bot.

History (DONE GAP items, collapsed; do not reopen as fidelity work): GAP 2.15 lasers are Match-behind-flag on #193. Classes 2, 3, and 5 are 482, 873, and 391 in `PORT_LASER_BARRAGE` (defs 55, 86, 59). Vergil Minor laser 954 stays sample-list only. Classes 1, 4, 6, and 7 stay 46/337, 110/1419, 98/598, and 98/1121. Fed prior class 8 stays FED_PRIOR and unwired. GAP 1.5 is Match-behind-flag on `STARDOCK_LOCATION_MODE` row 236 (`5a8cab96`; Ben approved the Commander recommendation 2026-10-24). GAP 6.3 handbook curve is Match-behind-flag (#183). GAP 4.8 detonation is Match. The shop unit price is Match-behind-flag on `HARDWARE_PRICE_MODE` (stored 100, live card 1,000). No third price. GAP 12.4 is Match-behind-flag (`fec5d73c`). No new switch. `INACTIVE_USER_MODE` and `INACTIVITY_TIMEOUT_MODE` stay off. R1–R14 are adopted. Libram key C is `ec4bc50b`. The singles-bar price and the unnamed 47-credit drop stay deferred (`2ba08a05`). The mailbox sha `307f2b07` is not an object on this branch. Parent chain before #193: `5a8cab96`, `ec4bc50b`, `2ba08a05`, `fec5d73c`.

## Next Dev (product / hygiene)

Listed only. Not launched from this mailbox.

a) P1 cockpit ship-stage spike. Merchant Cruiser and Imperial StarShip only. SVG path from the P0 pack: `docs/plans/cockpit-ship-stage-p0.md`, `docs/plans/cockpit-ship-stage-p0-render.md`, `docs/plans/cockpit-ship-stage-p0-fx.md`, and `docs/plans/cockpit-ship-stage-p0-silhouette-bible.md`. Fighter markers are 100:1 (`max(1, ceil(n / 100))` when n is at least 1). Ben-gated product code. Do not implement from this note.

b) Optional COMMS cleanup. Keep COMMS for player channels. `TRADE_FAILED` and other action outcomes stay in verdict / lastResult. They are not Fed Comm.

c) Drafts #25, #28, #37, #82, #99, and #103 stay draft and out of merge order.

## Blockers

- PoG: the Class L ferry waits on the wt_live redeploy. Player of Games requests it.
- Dev fidelity: none. 171 of 171 rows are Match or Match-behind-flag.

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

`PORT_LASER_BARRAGE` gained 482, 873, and 391 for classes 2, 3, and 5. Class 8 was not written into `PORT_DEFENSE_RATING` or `PORT_LASER_BARRAGE`. `_port_attack_gamea_row` still returns None for class 8. GAP 2.15 is Match-behind-flag. Counted grades: 75 Match, 96 Match-behind-flag, 0 Partial, 0 Ben-decision. 4.10 stays Match-behind-flag in `gap-map-refresh-v6.md`. At #193 the October GAP_MAP cell for 4.10 duration still said Partial and was left as written. This mailbox refresh aligns that cell to Match-behind-flag.

## 2026-10-24 — GAP 2.15 Ven GameA port-attack ratings

Player of Games measured TW Test Game 2 (Slot A), TW2002 v3.34b under TWGS v2.20b. Capture: `docs/playtests/twgs-live/gap215-port-attack-2026-10-24.md` (JSON: `docs/playtests/twgs-live/gap215_final.json`). EIS :23 was not touched.

CONFIRMED lasers: class 1 H'Catha sector 478, 337 battle points (def 46); class 4 Duriron Minor sector 122, 1419 (def 110); class 6 Khancuhn Primus, 598 (def 98, prior REPORT2); class 7 Balmer sector 688, 1121 (def 98). DEF_ONLY: class 2 New Cesium 160 def 55, class 3 Peleus 436 def 86, class 5 Aesculapius 404 def 59, class 8 Vergil Minor 119 (non-Fed) def 99. BLOCKED: class 0 Sol and class 9 StarDock.

A 0-fighter commit aborts after the def and shield text. Def rating is per port (class 3 Peleus 86 vs Anaxagoras Primus sector 913 def 60). Non-Fed class 8 (def 99, class 4 Sunstorm) differs from the Fed class 8 prior (def 91 / laser 701). This fold did not change the engine. Tip #185 (`7fd2db0d`) then stored the confirmed samples in `PORT_DEFENSE_RATING` and `PORT_LASER_BARRAGE`: class 1 H'Catha 46/337, class 4 Duriron Minor 110/1419, class 6 Khancuhn Primus 98/598, class 7 Balmer 98/1121, and DEF_ONLY defs for class 2 (55), class 3 (86), and class 5 (59). The class 6 pair is one row in that set. GAP 2.15 stays Partial because lasers for classes 2, 3, 5, and non-Fed 8 are still unmeasured.

## Standing queue (superseded)

The queue at the top of this file replaces the list that used to sit here. The capture notes below stay as history. GAP 2.15 numbers were not invented in this note; they are the measured samples already on the tip.
