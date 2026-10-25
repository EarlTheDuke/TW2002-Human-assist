# COMMANDER_NEXT

Standing mailbox for TW2K Dev Commander.

Report Page: https://cursor.com/canvas/store-edda9433-2d33-4b62-8d22-af10c2ff3895/b7c0b37a-f606-4a76-a69c-426bc1689683

Playtest wrap: `docs/playtests/multibot-2026-10-24-sat-grok-l3/README.md`

Tip parent: `feature/grokbot-player` @ `3765f609` (#216, P1b batch-1 remainder, Escape Pod and T'Khasi Orion). Counts, checked on this tip against the live-totals sentence in `docs/plans/GAP_MAP.md`, the every-row list in `docs/plans/gap-map-refresh-v6.md`, and `docs/plans/V311_REMAINING.md`: 75 Match, 96 Match-behind-flag, 0 Partial, 0 Ben-decision. The Dev fidelity backlog is empty (171/171). The October GAP_MAP cell for 4.10 duration is Match-behind-flag (#194, `8a31f30f`). Duration recommendation is cabal and the modern manual, 1 second. The tip already maps that to `PHOTON_WAVE_DURATION` 1 day-tick. Gypsy 10 seconds and GameA 20 seconds stay recorded. No realtime clock. No duration switch. Limpet, interdictor, and price subgrades were not flipped. `PORT_ATTACK_MODE` and `PORT_ATTACK_ALL_CLASSES_MODE` stay legacy.

## Standing queue

The Dev fidelity backlog is empty (171/171). No standing GAP item is left. The next Dev session is the ship-stage product queue below.

PoG (Player of Games) owns gameplay, playtests, the wt_live redeploy, and the hotter L3 retest. Dev does not drive seats.

1. wt_live redeploy, on request. The Class L ferry waits until Player of Games asks for that redeploy.
2. Hotter L3 retest start bank is **2M** credits and is already live on their side. Decided by the Commander under Ben's proactive grant.

Ops note, not a fidelity gap: Computer Use seats 1–3 min/action; double-queue re-fire observed. Plan around that for the next multi-bot.

History (DONE GAP items, collapsed; do not reopen as fidelity work): GAP 2.15 lasers are Match-behind-flag on #193. Classes 2, 3, and 5 are 482, 873, and 391 in `PORT_LASER_BARRAGE` (defs 55, 86, 59). Vergil Minor laser 954 stays sample-list only. Classes 1, 4, 6, and 7 stay 46/337, 110/1419, 98/598, and 98/1121. Fed prior class 8 stays FED_PRIOR and unwired. GAP 1.5 is Match-behind-flag on `STARDOCK_LOCATION_MODE` row 236 (`5a8cab96`; Ben approved the Commander recommendation 2026-10-24). GAP 6.3 handbook curve is Match-behind-flag (#183). GAP 4.8 detonation is Match. The shop unit price is Match-behind-flag on `HARDWARE_PRICE_MODE` (stored 100, live card 1,000). No third price. GAP 12.4 is Match-behind-flag (`fec5d73c`). No new switch. `INACTIVE_USER_MODE` and `INACTIVITY_TIMEOUT_MODE` stay off. R1–R14 are adopted. Libram key C is `ec4bc50b`. The singles-bar price and the unnamed 47-credit drop stay deferred (`2ba08a05`). The mailbox sha `307f2b07` is not an object on this branch. Parent chain on this tip: `3765f609` (#216), `9d29349a` (#215), `73c7269a` (#214), `9db677c3` (#213), `d39a3ab7` (#212), `2fd3bbd0` (#211), `e0c03d32` (#210), `8b803c89` (#209), `d91b8e78` (#208), `b42d98f1` (#207), `134b7872` (#206), `5714c733` (#205), `4ad12856` (#204), `b466108d` (#203), `5c613db2` (#202), `4aecd89c` (#201), `6a4ef414` (#200), `81df2c1b` (#198), `c630252a` (#197), `281680c5` (#196), `26d15088` (#195), `8a31f30f` (#194), `7a0fcf03` (#193), `5a8cab96`, `ec4bc50b`, `2ba08a05`, `fec5d73c`.

## Next Dev (product / hygiene)

1. Next product: P1b mesh builds, one batch at a time, on the SVG path (`buildHullFaces` / `projectFace`). WebGL stays off. Start with batch 1, Escape Pod and T'Khasi Orion: `docs/plans/cockpit-ship-stage-p1b-batch1-remainder.md` (#216, `3765f609`). Then the four-hull wave, already contracted: Scout Marauder, Merchant Freighter, BattleShip, Corporate FlagShip (`docs/plans/cockpit-ship-stage-p1b-next-hulls.md`, #197). Fleet order: `docs/plans/cockpit-ship-stage-p1b-fleet-order.md` (#196).

2. Later P1b builds stay behind those two. Contracts already on the tip: batch 2 haulers `docs/plans/cockpit-ship-stage-p1b-batch2-haulers.md` (#202), batch 3 guns `docs/plans/cockpit-ship-stage-p1b-batch3.md` (#208, `d91b8e78`), batch 4 dish and X `docs/plans/cockpit-ship-stage-p1b-batch4.md` (#212, `d39a3ab7`), batch 5 brick and hoops `docs/plans/cockpit-ship-stage-p1b-batch5.md` (#214, `73c7269a`).

3. Then P2 FX product, after the P1b read bar, from the wire checklist `docs/plans/cockpit-ship-stage-p2-wire.md` (#195). Six states onto the ship stage, then the left viewport comes off.

4. Then P3 layout product, from the checklist `docs/plans/cockpit-ship-stage-p3-layout.md` (#201). The P3 section of `docs/plans/cockpit-ship-stage-p0.md` links that checklist. Ship stage about 55–60% and the nav map about 35%, side by side. `#shipSvg` leaves the 140px cap. Product code starts after P2 has merged.

Player of Games owns gameplay, playtests, the wt_live redeploy, and the hotter L3 retest. Dev does not drive seats.

Drafts #25, #28, #37, #82, #99, and #103 stay draft and out of merge order.

Landed, and off this queue: the P1 Merchant Cruiser and Imperial StarShip SVG spike (#215, `9d29349a`). The read bar passed. WebGL stays off. The spike note is `docs/plans/cockpit-ship-stage-p1-spike.md`. COMMS stays on player channels. The contract note is `docs/plans/comms-feed-v1.md` (#203, `b466108d`). `TRADE_FAILED`, haggle misses, and other action outcomes stay off the COMMS card (#198, `81df2c1b`). They stay on the activity log and on lastResult / verdict. COMMS filter work stays closed. Landed hygiene under the ship-stage docs, and off this queue: the pack finder `docs/plans/cockpit-ship-stage-INDEX.md` (#204, `4ad12856`), the 100:1 marker math `docs/plans/cockpit-ship-stage-marker-math.md` (#206, `134b7872`), the INDEX marker-math row (#209, `8b803c89`), the INDEX rows for the P1 acceptance sheet and the batch-3 gun wave (#211, `2fd3bbd0`), and the INDEX batch-4 row (#213, `9db677c3`). The batch-5 sheet and the batch-1 remainder sheet are on the tip. Their INDEX links may land separately.

## Blockers

- PoG: the Class L ferry waits on the wt_live redeploy. Player of Games requests it. Dev does not drive that seat.
- Dev fidelity: none. 171 of 171 rows are Match or Match-behind-flag. The counted Partial backlog is empty. No fidelity row is waiting on a ruling.

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

## 2026-10-25 — queue after #212–#216

#215 (`9d29349a`) landed the P1 Merchant Cruiser and Imperial StarShip SVG spike. The read bar passed. WebGL stays off. The note is `docs/plans/cockpit-ship-stage-p1-spike.md`. #216 (`3765f609`) landed the batch-1 remainder mesh contracts `docs/plans/cockpit-ship-stage-p1b-batch1-remainder.md` (Escape Pod and T'Khasi Orion). #212 (`d39a3ab7`) landed the batch-4 dish and X contracts `docs/plans/cockpit-ship-stage-p1b-batch4.md` (Star Master and Constellation; FlagShip is a re-shot). #213 (`9db677c3`) listed that sheet on the INDEX. #214 (`73c7269a`) landed the batch-5 brick and hoops contracts `docs/plans/cockpit-ship-stage-p1b-batch5.md` (Tholian Sentinel and Interdictor Cruiser). #211 (`2fd3bbd0`) listed the P1 acceptance sheet and the batch-3 gun wave on the INDEX. The batch-5 sheet and the batch-1 remainder sheet are on the tip. Their INDEX links may land separately. Counted grades stay 75 Match, 96 Match-behind-flag, 0 Partial, 0 Ben-decision (`docs/plans/GAP_MAP.md` live totals, `docs/plans/gap-map-refresh-v6.md`, `docs/plans/V311_REMAINING.md`). The October GAP_MAP cell for 4.10 duration stays Match-behind-flag. The Partial backlog is empty. Next product is P1b mesh builds: batch 1 (Escape Pod, T'Khasi Orion), then the four-hull wave already contracted, then the later contracted waves. P2 FX product starts after the P1b read bar. P3 layout is after P2. Player of Games owns gameplay, the wt_live redeploy, and the hotter L3 retest.

## 2026-10-25 — queue after #204–#209

The #205 mailbox refresh (`5714c733`) kept the #201–#203 history. #204 (`4ad12856`) landed the ship-stage pack finder `docs/plans/cockpit-ship-stage-INDEX.md`. #206 (`134b7872`) landed the 100:1 fighter marker math `docs/plans/cockpit-ship-stage-marker-math.md`. #209 (`8b803c89`) added the INDEX marker-math row that links that sheet. Those three are landed hygiene under the ship-stage docs. #207 (`b42d98f1`) landed the P1 read-test `docs/plans/cockpit-ship-stage-p1-acceptance.md` (Pass / Fail / Hold-WebGL) for the in-flight Merchant Cruiser and Imperial StarShip SVG spike. #208 (`d91b8e78`) landed the P1b batch-3 gun contracts `docs/plans/cockpit-ship-stage-p1b-batch3.md` (Missile Frigate and Havoc GunStar; BattleShip is a re-shot only). Those guns follow the batch-2 haulers. Counted grades on this tip stay 75 Match, 96 Match-behind-flag, 0 Partial, 0 Ben-decision (`docs/plans/GAP_MAP.md` live totals, `docs/plans/gap-map-refresh-v6.md`, `docs/plans/V311_REMAINING.md`). The next product item is still the P1 Merchant Cruiser and Imperial StarShip SVG spike. It is in flight and Commander-owned. The read-test is the acceptance sheet. After that spike passes the render bar: P1b batch meshes (fleet order, the next-four contracts, batch 2 haulers, then batch 3 guns), then P2 FX product, then P3 layout product. Player of Games owns gameplay, the wt_live redeploy, and the hotter L3 retest.

## 2026-10-25 — queue after #201–#203

Since the #200 mailbox refresh (`6a4ef414`), three docs landed. #201 (`4aecd89c`) landed the P3 layout checklist (`docs/plans/cockpit-ship-stage-p3-layout.md`) and the link from the P3 section of `docs/plans/cockpit-ship-stage-p0.md`. P3 layout product starts after P2. #202 (`5c613db2`) landed the P1b batch-2 hauler mesh contracts (`docs/plans/cockpit-ship-stage-p1b-batch2-haulers.md`) for CargoTran, Colonial Transport, and the Taurean Mule. Those meshes follow the four-hull wave. #203 (`b466108d`) recorded the landed COMMS feed contract in `docs/plans/comms-feed-v1.md`. COMMS filter work stays closed. Counted grades on this tip stay 75 Match, 96 Match-behind-flag, 0 Partial, 0 Ben-decision (`docs/plans/GAP_MAP.md` live totals, `docs/plans/gap-map-refresh-v6.md`, `docs/plans/V311_REMAINING.md`). The next product item is still the P1 Merchant Cruiser and Imperial StarShip SVG spike. It is in flight and Commander-owned. After that spike passes the render bar: P1b batch meshes (fleet order, the next-four contracts, then batch 2), then P2 FX product, then P3 layout product. Player of Games owns gameplay, the wt_live redeploy, and the hotter L3 retest.

## 2026-10-25 — queue after #194–#198

#194 (`8a31f30f`) set the October GAP_MAP duration cell for 4.10 to Match-behind-flag. Counted grades on this tip stay 75 Match, 96 Match-behind-flag, 0 Partial, 0 Ben-decision (`docs/plans/GAP_MAP.md` live totals, `docs/plans/gap-map-refresh-v6.md`, `docs/plans/V311_REMAINING.md`). #195 landed the P2 wire checklist (`docs/plans/cockpit-ship-stage-p2-wire.md`). P2 product starts after the P1 spike merges. #196 landed the P1b fleet order for the other 15 player hulls. #197 landed the P1b mesh contracts for Scout Marauder, Merchant Freighter, BattleShip, and Corporate FlagShip. #198 (`81df2c1b`) kept COMMS on player channels and took `TRADE_FAILED` off the COMMS card. The next product item is the P1 Merchant Cruiser and Imperial StarShip SVG spike. It is Commander-owned.

## 2026-10-25 — GAP 2.15 Ven GameA lasers

Player of Games measured TW Test Game 2 (Slot A), TW2002 v3.34b under TWGS v2.20b. Capture: `docs/playtests/twgs-live/gap215-port-attack-2026-10-25.md` (JSON: `docs/playtests/twgs-live/gap215_final.json`). Method: a 0-fighter commit aborts after the def and shield text, then a 1-fighter commit records the laser battle points.

CONFIRMED this pass: class 2 New Cesium sector 160, def 55 / laser 482 / plasma; class 3 Peleus sector 436, def 86 / laser 873 / Class 2 Halos; class 5 Aesculapius sector 404, def 59 / laser 391 / plasma; class 8 Vergil Minor sector 119 (non-Fed), def 99 / laser 954 / Class 4 Sunstorm. Those four rows were DEF_ONLY on 2026-10-24.

Unchanged: class 1 H'Catha 46/337, class 4 Duriron Minor 110/1419, class 6 Khancuhn Primus 98/598 KNOWN, class 7 Balmer 98/1121. Class 0 Sol and class 9 StarDock stay BLOCKED. Fed prior class 8 REPORT def 91 / laser 701 / class 3 shielding stays FED_PRIOR and unwired. Variance samples Leipzig, Mastro, Anaxagoras Primus, and Mirador Outpost stay def-only.

`PORT_LASER_BARRAGE` gained 482, 873, and 391 for classes 2, 3, and 5. Class 8 was not written into `PORT_DEFENSE_RATING` or `PORT_LASER_BARRAGE`. `_port_attack_gamea_row` still returns None for class 8. GAP 2.15 is Match-behind-flag. Counted grades: 75 Match, 96 Match-behind-flag, 0 Partial, 0 Ben-decision. 4.10 stays Match-behind-flag in `gap-map-refresh-v6.md`. At #193 the October GAP_MAP cell for 4.10 duration still said Partial. #194 (`8a31f30f`) set that cell to Match-behind-flag. The standing queue counts it there.

## 2026-10-24 — GAP 2.15 Ven GameA port-attack ratings

Player of Games measured TW Test Game 2 (Slot A), TW2002 v3.34b under TWGS v2.20b. Capture: `docs/playtests/twgs-live/gap215-port-attack-2026-10-24.md` (JSON: `docs/playtests/twgs-live/gap215_final.json`). EIS :23 was not touched.

CONFIRMED lasers: class 1 H'Catha sector 478, 337 battle points (def 46); class 4 Duriron Minor sector 122, 1419 (def 110); class 6 Khancuhn Primus, 598 (def 98, prior REPORT2); class 7 Balmer sector 688, 1121 (def 98). DEF_ONLY: class 2 New Cesium 160 def 55, class 3 Peleus 436 def 86, class 5 Aesculapius 404 def 59, class 8 Vergil Minor 119 (non-Fed) def 99. BLOCKED: class 0 Sol and class 9 StarDock.

A 0-fighter commit aborts after the def and shield text. Def rating is per port (class 3 Peleus 86 vs Anaxagoras Primus sector 913 def 60). Non-Fed class 8 (def 99, class 4 Sunstorm) differs from the Fed class 8 prior (def 91 / laser 701). This fold did not change the engine. Tip #185 (`7fd2db0d`) then stored the confirmed samples in `PORT_DEFENSE_RATING` and `PORT_LASER_BARRAGE`: class 1 H'Catha 46/337, class 4 Duriron Minor 110/1419, class 6 Khancuhn Primus 98/598, class 7 Balmer 98/1121, and DEF_ONLY defs for class 2 (55), class 3 (86), and class 5 (59). The class 6 pair is one row in that set. On this 2026-10-24 fold, lasers for classes 2, 3, 5, and non-Fed 8 were still unmeasured, and this note called GAP 2.15 Partial. The 2026-10-25 section is the grade: Match-behind-flag. The standing queue counts 0 Partial.

## Standing queue (superseded)

The queue at the top of this file replaces the list that used to sit here. The capture notes below stay as history. GAP 2.15 numbers were not invented in this note; they are the measured samples already on the tip.
