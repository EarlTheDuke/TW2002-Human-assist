# V311 remaining gaps (NOTE 163, updated by NOTE 164)

NOTE 161 listed the open rows. NOTE 163 matched five of them. NOTE 164 adds four switches. Two of those switches sit on rows NOTE 163 already graded, and those rows are counted once.

The grades are the 171 rows in `docs/plans/gap-map-refresh-v6.md`. Queued #89 (NavPoints, row 181) and #93 (NOTE 162, rows 182-186) are not in this file. NOTE 163's switch is profile row 187. NOTE 164 uses rows 200-203.

**131 of 171 rows match the original rule (76.6%).** That count is Match 59 plus Match-behind-flag 72. A Match-behind-flag row is coded, and its switch stays off until `V311_PROFILE` is `v311`. A normal game, with every switch at the stored default, matches 59 of 171 (34.5%). The other rows are Partial 31, Different 6, Missing 1, and Ben-decision 2. Thirty-eight rows are still Partial, Different, or Missing. StarDock in sector 1 (1.5) and the class M population cap (6.3) stay Ben-decision and are not in the lists below.

NOTE 163's 129 already includes 6.11 and 13.4. NOTE 164 adds the grades for 8.1 and 12.6 only. `CORP_SHIP_DISBAND_MODE` and `FIGHTER_REPORT_MODE` are extra behaviours on 6.11 and 13.4, not a second grade.

`docs/plans/V311_SOURCE_CONFLICTS.md` is on this tip. NOTE 164 updates the Ferrengi odds row and the times-blown row there.

Ten of the 38 are not work. The printed rule is already in the game, or it is already behind a switch, and the grade line was not moved. The other 28 are grouped by what blocks them. Size is the slice: small, medium, or large.

## Matched in NOTE 163

- **6.7 Genesis class.** Match. The launch rolls a class when the torpedo commits, and a requested class is ignored. `PLANET_CLASS_MODE` stays off the profile because it would roll only M and U. The crowding note prints no weights.
- **6.11 Corp planet quirks.** Match-behind-flag, counted once. `CORP_PLANET_DISBAND_MODE` and `SPECIAL_HULL_RULES_MODE` are the planet split and the Tholian 4:1. `CORP_SHIP_DISBAND_MODE` (NOTE 164, row 201) is the ship sentence in the same v3.06 revision. It does not add a second grade.
- **9.2 Ways to gain experience.** Match. Trade, the first dock, midnight, genesis, a port destroy, and the kill share are the stored awards. An alien's own experience is not printed.
- **9.5 Other alignment sources.** Match-behind-flag. `BOUNTY_GOOD_MODE` row 187. A bounty on a good trader costs 1 alignment per 250 credits and no experience. The other named sources were already in.
- **13.4 Fighter and combat reports.** Match-behind-flag, counted once. `OWNER_HAZARD_NOTICE_MODE` and `SIEGE_REPORT_MODE` tell the owner about a landing, a fighter hit, a mine, and a siege. `FIGHTER_REPORT_MODE` (NOTE 164, row 203) is a separate list of sectors where that trader owns fighters, omitting a count of 0. It is not an observation field, and it does not add a second grade.

## Can build now

The rule is printed in the in-repo docs. Nothing here is waiting on a second source or on Ben.

- **1.8 Class 9 StarDock services.** Partial. Bank, tavern, shipyard, and hardware are on. Federation Hall, and the shop screens that are still only buy lists, are not. Feature not built. Medium.
- **3.15 Per-ship capacity table.** Partial. The roster switch rewrites cost, holds, fighters, turns, and odds. Mines, genesis, photons, and the probe cap are already on their own chart switches. The caps that switch does not rewrite are still open. Feature not built. Small.
- **4.16 Ship transporter.** Partial. A ship-to-ship beam is in, with `SHIP_TRANSPORT_RANGE`. The gap line still says that table is not the Bible chart, so the remaining work is any hull whose range disagrees with that chart. Feature not built. Small.
- **5.6 Toll fighters.** Different. The toll is not 5 credits per fighter, and it is not collected by visiting the sector. Iago and the cabal formulas print the 5. Feature not built. Medium.
- **10.4 Members limit.** Different. Join uses `GameConfig.corp_max_members`, whose default is 2. The TEDIT sample is 5, and `CORP_MAX_MEMBERS` is already 5. Feature not built. Small.
- **10.6 Transfers between members.** Partial. Credits, fighters, shields, armids, and limpets move in the same sector. Holds and the corp treasury do not, and deposit is refused. Feature not built. Small.
- **10.7 Corp assets and member locations.** Partial. The corp screen does not show every planet field and member field the EIS corporate menu lists. Feature not built. Small.
- **10.9 Corporate ships.** Partial. Corporate fighters and mines are in, and `CORPSHIP_MODE` is already tw2002. Corporate ships are only partly the original shared, password-protected hulls. Feature not built. Medium.
- **11.7 Underground.** Partial. The door, the password, and the Grimy are in. The original mafia shop is not that whole menu. Feature not built. Medium.
- **11.9 Fed attack on evil players.** Partial. Feds tow, and they answer some crimes. They do not yet hunt every evil trader who enters FedSpace. Feature not built. Medium.
- **14.1 Computer menu helpers.** Partial. Avoids were already in. NavPoints are `NAVPOINT_MODE` (NOTE 159, queued #89): four named points, Terra, StarDock, and a course. Backtrack, quick stats, and find route read the known map and were left without a switch. CIM mapping is not built. Feature not built. Medium.

## Needs Ben's ruling

Two sources disagree, or the difference is a choice Ben already made and has not reopened. Where queued #83, #87, or #88 wrote the pair, the section name is the one in `V311_SOURCE_CONFLICTS.md`.

- **1.6 Terra colonists.** Partial. Regen of 750 a day and a one-turn load are in. The profile opens the pool at 30,000 with 1,000 people per hold. The Bible's "about 100,000" was not adopted. Deliberate choice by Ben. Small.
- **1.15 FedSpace fighter limit.** Partial. `FED_TOW_LIMIT_MODE` (NOTE 117) tows above 50 when it is on. The stored game tows above 98. `V311_SOURCE_CONFLICTS.md`, NOTE 151, "FedSpace fighter tow" (Bible over 50, Gypsy 99 or more). Source conflict. Small.
- **2.5 Price scale vs ship cost.** Different. `ECONOMY_SCALE_MODE` is already tw2002, and prices and hull costs still do not sit on one scale. The cabal samples are not a printed default. No printed number. Large.
- **4.1 Genesis price.** Partial. Genesis works. The engine price is 25,000. A sample TEDIT prints 80,000. This pair is not in `V311_SOURCE_CONFLICTS.md` yet. Source conflict. Small.
- **5.14 Exp and alignment on death.** Partial. A pod drops experience. Self-destruct alignment is the open half: the wiki and the MBBS manuals do not say the same thing (`docs/playtests/combat/DEATH_ESCAPE_PODS.md`, d13). This pair is not in `V311_SOURCE_CONFLICTS.md` yet. Source conflict. Small.
- **5.20 Combat in FedSpace.** Partial. Penalties exist. They are not the full police response, and that script is thin. The fighter ceiling is `V311_SOURCE_CONFLICTS.md`, NOTE 151, "Fedsafe fighter ceiling" (50 or less, or no ceiling). `FEDSAFE_FIGHTER_CAP_MODE` uses 50 when it is on. Source conflict. Medium.
- **6.2 Class-table citadel costs.** Partial. The class goods are on, and build days are `CITADEL_DAYS_MODE`. The class M level-1 colonist figure is Ben's NOTE 19 choice, the same hold as row 6.3. Deliberate choice by Ben. Small.
- **9.8 Rob and steal caps.** Partial. A rob pays from experience. The stored factors are the MBBS pair, 6 and 21. The classic pair has no switch. `V311_SOURCE_CONFLICTS.md`, NOTE 150, "Rob and steal caps". Source conflict. Small.
- **10.1 Create a corporation.** Partial. Filing a charter is in. `CFS_CEO_RULE` is still `purchase` or `use`. This pair is not in `V311_SOURCE_CONFLICTS.md` yet. Source conflict. Small.
- **11.11 Big Bang options.** Partial. Density, the one-way share, and the 30 percent extra two-way lanes (NOTE 157, queued #87) are switches. Bubbles are `UNIVERSE_TOPOLOGY_MODE`, and the profile leaves them off because code bots trap in dead ends. Gold options stay off as a Gold add-on. Deliberate choice by Ben. Medium.
- **12.3 Real-time movement.** Different. Ships still move by turns. `DAY_ROLL_CLOCK_MODE` rolls the day. `PLANET_REALTIME_PROD_MODE` stays off because the original produces at Extern. The October map marked this deliberate. Deliberate choice by Ben. Large.
- **14.6 Ours-only systems.** Different. Alliances, the planet dividend, the credit win, and the day cap are still in this game. The profile leaves alliances out because they are not in the original. This map does not delete them. Deliberate choice by Ben. Large.

## Can't verify without the real game

A number was not printed, or the gap line no longer names the missing piece. Guessing it would invent a rule.

- **2.15 Attack a port.** Partial. Blowing a port is behind `PORT_ATTACK_MODE` and `PORT_ATTACK_ALL_CLASSES_MODE`. Classes 0 through 5 and 7 through 9 have no measured rating or barrage. No printed number. Medium.
- **4.8 Armid price.** Partial. Detonation is the stored half-count at 20. The shop price moves only under `HARDWARE_PRICE_MODE`. The unit price is sysop-set, and the 4,000 is a sample. No printed number. Small.
- **5.7 Ship versus ship.** Different. The exchange is still not the original. CMB-c is `docs/plans/ship-odds-exchange-v1.md` only. The attacker picking fighters is printed. The exchange formula is not. No printed number. Large.
- **6.10 Planet killer.** Partial. The blow is −1 alignment and +50 experience, which is the current choice in `V311_SOURCE_CONFLICTS.md`, NOTE 143, "Destroying a planet". Killing a trader on the planet is `PLANET_ZDY_MODE`. Colonist-kill alignment is an ellipsis, and a citadel's extra blow experience is not printed. No printed number. Small.
- **12.4 Nightly Extern.** Partial. The jobs named on the every-row line are in, or they are behind `PLANET_COLLISION_MODE` and `SPECIAL_PORT_DEFENCE_MODE`. `INACTIVE_USER_MODE` (NOTE 151, queued #83) deletes a disconnected human after 30 quiet wall-clock days and stays off. `V311_SOURCE_CONFLICTS.md`, NOTE 151, "Days until an inactive user is deleted" (30, or Gypsy's 7). The map says a job past that list has no name. No printed number. Medium.

## NOTE 164 matched

Profile rows 200-203. Each switch stays legacy until `V311_PROFILE` is `v311`. `"1"` does not turn one on.

- **8.1 Ferrengi odds.** Match-behind-flag. This is a new grade. `FERRENGI_ODDS_MODE` row 200. Off, odds stay 1.0 / 1.2 / 1.4 and an Assault Trader sends 1,000 with no scanner room. On, the Bible chart is 1.2 / 1.4 / 1.4, that volley is 2,000, and the hull can carry a holo scanner. `FERRENGI_ATTACK_MODE` still uses the FERRSPEC 1,000 while the odds switch is off. Source: `S3_tw2002_bible_v1.htm` and the v3.05 scanner line.
- **6.11 Corp ships on disband.** Not a new grade. `CORP_SHIP_DISBAND_MODE` row 201. Off, every parked corporate hull becomes defunct. On, a parked hull in the living C.E.O.'s sector becomes that C.E.O.'s, ships outside stay defunct, and a dead C.E.O. takes nothing. Planets stay `CORP_PLANET_DISBAND_MODE`. The Tholian 4:1 stays `SPECIAL_HULL_RULES_MODE`. The ship the C.E.O. is flying is unchanged until they leave it. Source: v3.06 revision, ships in the C.E.O.'s sector.
- **12.6 Times blown up.** Match-behind-flag. This is a new grade. `TIMES_BLOWN_MODE` row 202. Off, the legacy destroy line stays `death #N/3`. On, and only when elimination is off, that line says unlimited and does not print `/3`. No lockout was added. `DEATH_MODE` and `DEATH_DELAY_MODE` stay as they are. Source: cabal `twgs.html`, Tournament Mode Off and Maximum times blown up Unlimited.
- **13.4 Fighter report.** Not a new grade. `FIGHTER_REPORT_MODE` row 203. Off, `fighter_report` returns nothing. On, it lists sectors where that trader owns fighters and omits a count of 0. Owner notices stay `OWNER_HAZARD_NOTICE_MODE`. Siege losses stay `SIEGE_REPORT_MODE`. The list is not an observation field. Source: the revision that stopped the fighter report from showing sectors with 0 fighters.

## Grade not moved

These stay Partial, Different, or Missing on the map. The printed rule is already what the game does, or it is already behind a switch. They are not in the three lists above.

- **3.20 Federal commission and the ISS.** A trader at 1,000 alignment is commissioned, Police HQ raises 500 through 999 to 1,000, and an evil ISS is repossessed on the move.
- **4.9 Limpet removal.** Attach, query, and the StarDock fee of 1,250 are in while hardware is tw2002.
- **4.10 Photon missile.** The wave decloaks, damps a quasar, and holds mines and fighters. A limpet during that wave is `PHOTON_LIMPET_MODE`. The interdictor still holds, which matches S1. Duration stays 1 second (`V311_SOURCE_CONFLICTS.md`, NOTE 148, "Photon wave duration").
- **5.18 Photon interaction.** A follower who enters the wave is `PHOTON_FOLLOW_DAMP_MODE`. Decloak and the quasar damp are already in the wave. The same limpet switch and the same interdictor hold as 4.10.
- **6.12 Planet destroy experience.** The stored blow is +50 experience and −1 alignment, the same choice as the NOTE 143 conflict row. The create-and-destroy loop is 14.3, behind `PLANET_BUST_EXP_MODE`.
- **8.8 NPCs and player fighters.** Aliens and Feds already refuse a sector that holds fighters. Ferrengi already ignore fighters and take mine hits. No second switch was added.
- **10.2 Joining.** The invite, the password, and the C.E.O. approval are in. The sign-agreement check is `CORP_ALIGNMENT_RULE` and stays off in the stored value.
- **13.1 Direct messages.** `MAIL_MODE` flashes a hail for about 10 seconds and stores mail for an offline trader. `COMMS_V311_MODE` is the same-sector hail. The every-row line still says there is no mail switch.
- **13.3 Mail.** Stored mail and the New Mail line are the same `MAIL_MODE` switch. The every-row line still says mail is only the inbox a hail writes.
- **14.5 Evil trading loops.** `EVIL_TRADE_LOOP_MODE` (NOTE 115) steals, dumps, and beams, or robs and beams, and the profile turns it on. The every-row line still says there is no coded path.
