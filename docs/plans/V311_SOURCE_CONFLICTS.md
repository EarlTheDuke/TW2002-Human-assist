# V311 source conflicts

Ben can rule on these. Each row is one that NOTEs 143, 148, 150, 151, 157, or 158 hit where two sources print different numbers. The current choice is what the engine does today. A switch that is off leaves the stored game alone.

## NOTE 143 — planets

| Row | Competing numbers | Sources | Current choice |
|---|---|---|---|
| 6.10 / 6.12 Destroying a planet | −1 alignment and +50 experience, or −50 alignment | `cabal_strategy_site/formulas.html` and both glossaries print −1 / +50. The October gap map recorded the older engine reading of −50. | The blow is −1 alignment and +50 experience while `RANK_MODE` is tw2002, which is the stored default. NOTE 143 did not add a second switch for this pair. The on-planet trader kill is a separate printed pair, 0.1666 of experience and −0.3333 of alignment, behind `PLANET_ZDY_MODE`. Colonist-kill alignment is an ellipsis, so it is not in this table. |

## NOTE 148 — ships and combat

| Row | Competing numbers | Sources | Current choice |
|---|---|---|---|
| 8.1 Ferrengi combat odds | FERRSPEC 1.0 / 1.2 / 1.4, or the Bible chart 1.2 / 1.4 / 1.4 | `docs/playtests/npc/FERRENGI.md` n2 picks FERRSPEC. The Bible ship chart is in `docs/reference/tw2002/S3_tw2002_bible_v1.htm`: Assault Trader 1.2:1 and 3,000 / 2,000 fighters, Battle Cruiser 1.4:1, Dreadnaught 1.4:1. The v3.05 revision lets the Assault Trader carry a density or holo scanner, and that chart prints Both. | `FERRENGI_ODDS_BY_HULL` keeps 1.0, 1.2, and 1.4. `FERRENGI_ODDS_MODE` (NOTE 164, row 200) reads the Bible chart when it is on, including the Assault Trader volley of 2,000 and the holo scanner. Off, FERRSPEC stays, and `FERRENGI_ATTACK_MODE` still caps that volley at 1,000. |
| Photon wave duration | 1 second, or 10 seconds | Cabal `twgs.html` and the modern manual print 1 second. Gypsy's v2.03 V-screen prints 10 seconds. | `PHOTON_WAVE_DURATION` is already 1. NOTE 148 left it. |

## NOTE 150 — ports, trading, haggling

| Row | Competing numbers | Sources | Current choice |
|---|---|---|---|
| 2.8 Port regeneration | 5 percent a day, or a sample of 1 percent | v3.05 revision history: the TEDIT range is 1 to 200 percent and the standard is 5 percent. Cabal `twgs.html` shows one game at 1 percent. | `PORT_REGEN_PER_DAY` stays 0.05. `PORT_REGEN_MODE` chooses whether that 5 percent applies to max stock or to productivity. NOTE 150 did not switch the 1 percent sample. |
| 9.8 Rob and steal caps | Experience times 3 and divided by 30, or times 6 and divided by 21 | Cabal `formulas.html` prints both the classic factors and the MBBS factors. The playtest says MBBS breaks a tie for v3.11. | `ROB_CREDIT_FACTOR` is 6 and `STEAL_HOLD_DIVISOR` is 21. NOTE 150 did not switch the classic pair. |
| Good-haggle experience | +1 and +2, or 5 for the exact best price | The adopted reading is +1 for a good haggle and +2 for a great one. S7 says "haggle for 2 points". Eugene Hung's player tip says the exact best price pays 5. | `HAGGLE_EXP_MODE` pays +1 / +2 when it is on. The 5 was not adopted. Which counter counts as great is still unverified, so it is not a second number here. |

## NOTE 151 — corporations, the Federation, ranks, turns

| Row | Competing numbers | Sources | Current choice |
|---|---|---|---|
| 1.15 FedSpace fighter tow | More than 50, or 99 or more | The Bible says more than 50. Gypsy says 99 or more. | Stored `FED_TOW_FIGHTER_LIMIT` is 98, so a ship is towed above 98. `FED_TOW_LIMIT_MODE` (NOTE 117) uses 50 when it is on. NOTE 151 did not add another switch. |
| 5.20 Fedsafe fighter ceiling | 50 or less, or no fighter ceiling | Iago: non-negative alignment, under 1000 experience, and 50 fighters or less. One Iago line says less than 50. The Bible's tow line is more than 50. The stored fedsafe rule ignores fighters. | `FEDSAFE_FIGHTER_CAP_MODE` uses 50 when it is on. Stored `FEDSAFE_MAX_FIGHTERS` stays unset. NOTE 151 left that switch. |
| 12.1 Turns per day | 250, or 750, or 1000 | Cabal glossary Classic and RULINGS s2 print 250. Gypsy's sample V-screen prints 750. The cabal income table assumes 1000, which is also `STARTING_TURNS_PER_DAY`. | Turns per day stay a game setting. `STARTING_PACKAGE_MODE` uses 250 when the profile is on. A scripted match that does not set the package stays at 1000. NOTE 151 did not add a third switch. |
| 12.4 Days until an inactive user is deleted | 30 days, or 7 days | Cabal `twgs.html` and `stardock_modernmanual/advanced__twgs-settings.md` print 30. Gypsy's v2.03 V-screen prints 7. | `INACTIVE_USER_MODE` uses 30 wall-clock days when it is on. Game days do not count. A connected seat and an AI cockpit seat stay, and a game generated before the switch was on is not swept. Off, a quiet trader stays in the game. The 7-day sample is not the on value. |

## NOTE 157 — universe and navigation

| Row | Competing numbers | Sources | Current choice |
|---|---|---|---|
| 1.2 Two-way warp count | 30 percent of the sectors as the total, or 30 percent extra on a connected tree | Cabal `twgs.html` option F: "Total number of two way warps... Default is 30% of the total sectors." `Big_Bang.html` says 100 percent creates as many two-way warps as there are sectors, and recommends 30 percent. A total of 30 percent cannot connect the map. GAP_MAP 1.2 reads the same 30 percent as extra lanes. | `TWO_WAY_WARP_MODE` adds extra two-way lanes equal to 30 percent of the sector count, on top of the spanning tree. A 1,000-sector game adds 300. Off, the average stays 2.7. A game that sets `avg_warps` keeps that average. |

## NOTE 158 — scoring and the end of the game

| Row | Competing numbers | Sources | Current choice |
|---|---|---|---|
| Re-entry fighters | 250, or the Initial Fighters setting, or up to 2,500 | The v3.11 revision history: a Scout re-entry gets the minimum of 250 fighters and the Initial Fighters value, instead of up to 2,500. Cabal `twgs.html` leaves Initial fighters blank. RULINGS s2 prints 30. The stored start is 20. | `REENTRY_FIGHTERS_MODE` uses this game's initial fighters, capped at 250, and also capped by the scout's room. Off, the scout has 0. The 2,500 grant is not the on value. |
| Experience and alignment ceiling | 4,500,000, or 999,999,999 | The v3.11 revision says a gain past the limit stops at the boundary. The same history handles a name change from 0 to 4,500,000 experience, and caps a charge at 999,999,999. The editor range in `SysOpUpdated.html` is also 0 to 999,999,999. The sentence does not say which boundary is the stat cap. | No clamp. NOTE 158 did not pick one of those two ceilings. |
| Match length | No printed length, or this beta's 30 days and 100,000,000 credits | The Bible and EIS say there is no built-in win and the sysop sets the duration. Cabal `twgs.html` "Days to allow entry: Unlimited" is how long a new trader may join, not how long the match lasts. | The day cap, the last player standing, the credit bar, and a creator end stay. `EXP_SCORE_MODE` already ranks a day-cap finish by experience when it is on. NOTE 158 did not add an end switch. |
| Times blown up | Unlimited, or a later lockout | Cabal `twgs.html` prints Tournament Mode Off and Maximum times blown up Unlimited. `TWGS_v2_Revision_History.html` later adds pod and death lockouts. | `TIMES_BLOWN_MODE` (NOTE 164, row 202) says unlimited on the legacy destroy line when elimination is off. Off, that line still prints death `#N/3`. The later lockout was not switched. `DEATH_DELAY_MODE` remains the timeout. Two pods a day and out-until-midnight stay the stored death path. |
| High score | TriCron HiScore 0, or the trader list | Cabal `twgs.html` prints TriCron HiScore 0 for that game. EIS `CompDisplays.html` lists traders in order of experience, with a title or the experience value, the corporation, and the ship. | `TRADER_RANK_LIST_MODE` is the list. NOTE 158 did not add a TriCron score. |
