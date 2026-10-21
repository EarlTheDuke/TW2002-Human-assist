# V311 remaining gaps (NOTE 166)

NOTE 161 listed the open rows. NOTE 163, now on the tip, matched 6.7, 6.11, 9.2, 9.5, and 13.4. NOTE 162 moved the grades that were already true, and built the printed pieces that were not. NOTE 164 adds four switches. Two of those switches sit on rows NOTE 163 already graded, and those rows are counted once. NOTE 166 matches the next five bottom rows that have a printed source. Each row is listed once.

The grades are the 171 rows in `docs/plans/gap-map-refresh-v6.md`. Row 181 is NavPoints (`NAVPOINT_MODE`, NOTE 159). NOTE 162 uses rows 182-186. Row 187 is `BOUNTY_GOOD_MODE` from NOTE 163. NOTE 164 uses rows 200-203. NOTE 166 uses row 204. Rows 205-212 stay free.

**157 of 171 rows match the original rule (91.8%).** That count is Match 71 plus Match-behind-flag 86. A Match-behind-flag row is coded, and its switch stays off until `V311_PROFILE` is `v311`. A normal game, with every switch at the stored default, matches 71 of 171 (41.5%). The other rows are Partial 8, Different 4, Missing 0, and Ben-decision 2. Twelve rows are still Partial, Different, or Missing. StarDock in sector 1 (1.5) and the class M population cap (6.3) stay Ben-decision and are not in the lists below.

NOTE 163's 129 already includes 6.11 and 13.4. NOTE 164 adds the grades for 8.1 and 12.6 only. `CORP_SHIP_DISBAND_MODE` and `FIGHTER_REPORT_MODE` are extra behaviours on 6.11 and 13.4, not a second grade. NOTE 166 adds 9.8, 10.1, 1.15, 5.14, and 5.20.

`docs/plans/V311_SOURCE_CONFLICTS.md` is on this tip. NOTE 164 updates the Ferrengi odds row and the times-blown row there.
## Matched in NOTE 163

- **6.7 Genesis class.** Match. The launch rolls a class when the torpedo commits, and a requested class is ignored. `PLANET_CLASS_MODE` stays off the profile because it would roll only M and U. The crowding note prints no weights.
- **6.11 Corp planet quirks.** Match-behind-flag, counted once. `CORP_PLANET_DISBAND_MODE` and `SPECIAL_HULL_RULES_MODE` are the planet split and the Tholian 4:1. `CORP_SHIP_DISBAND_MODE` (NOTE 164, row 201) is the ship sentence in the same v3.06 revision. It does not add a second grade.
- **9.2 Ways to gain experience.** Match. Trade, the first dock, midnight, genesis, a port destroy, and the kill share are the stored awards. An alien's own experience is not printed.
- **9.5 Other alignment sources.** Match-behind-flag. `BOUNTY_GOOD_MODE` row 187. A bounty on a good trader costs 1 alignment per 250 credits and no experience. The other named sources were already in.
- **13.4 Fighter and combat reports.** Match-behind-flag, counted once. `OWNER_HAZARD_NOTICE_MODE` and `SIEGE_REPORT_MODE` tell the owner about a landing, a fighter hit, a mine, and a siege. `FIGHTER_REPORT_MODE` (NOTE 164, row 203) is a separate list of sectors where that trader owns fighters, omitting a count of 0. It is not an observation field, and it does not add a second grade.

## Built in NOTE 162

Five switches, each defaulting to legacy. `V311_PROFILE=v311` turns the helper on. The string `1` does not.

- **1.8 Class 9 StarDock services.** Match-behind-flag. `FEDERATION_HALL_MODE` row 182. Federation Hall lists registrations, and the hardware counter shows a shop screen.
- **10.6 Transfers between members.** Match-behind-flag. `CORP_CARGO_TREASURY_MODE` row 183. Cargo holds move between members, and the corporation treasury takes deposits.
- **11.7 Underground.** Match-behind-flag. `UG_NAME_MODE` row 184. A total unknown buys a new name for 100 credits. A higher experience has no printed price, so it is refused.
- **11.9 Fed attack on evil players.** Match-behind-flag. `FED_HUNT_MODE` row 185. An evil ship that meets a Federal is destroyed. A sector with no Federal is left alone.
- **14.1 Computer menu helpers.** Match-behind-flag. `CIM_MODE` row 186. CIM lists explored sectors and ports, hides a port behind hostile fighters, and plots a path. NavPoints are `NAVPOINT_MODE` row 181.

## Already the stored game

These were on the "can build now" list. A normal game already does the printed rule. A switch that defaulted to legacy would have changed that game, or it would have had nothing to turn on.

- **3.15 Per-ship capacity table.** Match. `SHIP_SPECS_TW2002` and `equip_room` already cap mines, genesis, photons, fighters, shields, and holds.
- **4.16 Ship transporter.** Match. `SHIP_TRANSPORT_RANGE` is the Bible chart. The ISS stays 10.
- **5.6 Toll fighters.** Match. The toll is 5 credits per fighter, and the pot is collected by picking the fighters up in that sector.
- **10.4 Members limit.** Match. The stored join path uses `CORP_MAX_MEMBERS` 5. The config default of 2 is the legacy corporation path.
- **10.7 Corp assets and member locations.** Match. `member_block` already lists the planet fields and member fields on the EIS corporate menu.
- **10.9 Corporate ships.** Match. `CORPSHIP_MODE` is tw2002. Corporate hulls are password protected, and a corp mate can board one.

## Needs Ben's ruling

Two sources disagree, or the difference is a choice Ben already made and has not reopened. Where queued #83, #87, or #88 wrote the pair, the section name is the one in `V311_SOURCE_CONFLICTS.md`.

- **1.6 Terra colonists.** Partial. Regen of 750 a day and a one-turn load are in. The profile opens the pool at 30,000 with 1,000 people per hold. The Bible's "about 100,000" was not adopted. Deliberate choice by Ben. Small.
- **2.5 Price scale vs ship cost.** Different. `ECONOMY_SCALE_MODE` is already tw2002, and prices and hull costs still do not sit on one scale. The cabal samples are not a printed default. No printed number. Large.
- **4.1 Genesis price.** Partial. Genesis works. The engine price is 25,000. A sample TEDIT prints 80,000. This pair is not in `V311_SOURCE_CONFLICTS.md` yet. Source conflict. Small.
- **6.2 Class-table citadel costs.** Partial. The class goods are on, and build days are `CITADEL_DAYS_MODE`. The class M level-1 colonist figure is Ben's NOTE 19 choice, the same hold as row 6.3. Deliberate choice by Ben. Small.
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

## NOTE 166 matched

Taken from the bottom of the lists above, skipping a row whose missing piece has no printed number, and skipping the readings the rulings sheet told us not to turn on. NOTE 162 already built the can-build rows, so those were left. Profile row 204. The other four rows were already the printed rule, so they get no second switch. `"1"` does not turn the new switch on.

- **14.6, 12.3, 11.11.** Left. The printed v3.11 reading is the stored game: leave the house rules in the program, move by turns, and do not build bubbles. A switch that deleted them, or that turned the clock or the bubbles on, is the reading the sheet rejected.
- **12.4, 6.10, 5.7, 4.8, 2.15.** Left. The missing piece has no printed number.
- **9.8 Rob and steal caps.** Match. No new switch. The stored factors are experience times 6 and experience divided by 21. That is the MBBS pair the sample screen agrees with. The classic pair stays off.
- **10.1 Corporate FlagShip.** Match. No new switch. `CFS_CEO_RULE` is `purchase`. Only the C.E.O. buys one, including a spare. A member can be handed the helm. The use-only reading stays off.
- **5.20 FedSpace fighters.** Match-behind-flag. No new switch. `FEDSAFE_FIGHTER_CAP_MODE` row 167 already removes protection above 50 fighters when the profile is on. The rest of a police chase is not printed, so none was added.
- **5.14 Self-destruct alignment.** Match-behind-flag. `SELF_DESTRUCT_ALIGN_MODE` row 204. Off, the button halves experience and halves alignment of either sign. On, experience is still cut in half, a negative alignment is cut in half, and a good alignment stays. A kill by someone else still halves both signs. The two-day lock stays the existing one. Source: the MBBS manual for the amounts, and EIS CompMisc for the button.
- **1.15 FedSpace tow.** Match-behind-flag. No new switch. `FED_TOW_LIMIT_MODE` row 168 already tows above 50 when the profile is on. Off, the tow stays above 98.

## NOTE 164 matched

Profile rows 200-203. Each switch stays legacy until `V311_PROFILE` is `v311`. `"1"` does not turn one on.

- **8.1 Ferrengi odds.** Match-behind-flag. This is a new grade. `FERRENGI_ODDS_MODE` row 200. Off, odds stay 1.0 / 1.2 / 1.4 and an Assault Trader sends 1,000 with no scanner room. On, the Bible chart is 1.2 / 1.4 / 1.4, that volley is 2,000, and the hull can carry a holo scanner. `FERRENGI_ATTACK_MODE` still uses the FERRSPEC 1,000 while the odds switch is off. Source: `S3_tw2002_bible_v1.htm` and the v3.05 scanner line.
- **6.11 Corp ships on disband.** Not a new grade. `CORP_SHIP_DISBAND_MODE` row 201. Off, every parked corporate hull becomes defunct. On, a parked hull in the living C.E.O.'s sector becomes that C.E.O.'s, ships outside stay defunct, and a dead C.E.O. takes nothing. Planets stay `CORP_PLANET_DISBAND_MODE`. The Tholian 4:1 stays `SPECIAL_HULL_RULES_MODE`. The ship the C.E.O. is flying is unchanged until they leave it. Source: v3.06 revision, ships in the C.E.O.'s sector.
- **12.6 Times blown up.** Match-behind-flag. This is a new grade. `TIMES_BLOWN_MODE` row 202. Off, the legacy destroy line stays `death #N/3`. On, and only when elimination is off, that line says unlimited and does not print `/3`. No lockout was added. `DEATH_MODE` and `DEATH_DELAY_MODE` stay as they are. Source: cabal `twgs.html`, Tournament Mode Off and Maximum times blown up Unlimited.
- **13.4 Fighter report.** Not a new grade. `FIGHTER_REPORT_MODE` row 203. Off, `fighter_report` returns nothing. On, it lists sectors where that trader owns fighters and omits a count of 0. Owner notices stay `OWNER_HAZARD_NOTICE_MODE`. Siege losses stay `SIEGE_REPORT_MODE`. The list is not an observation field. Source: the revision that stopped the fighter report from showing sectors with 0 fighters.

## Grades moved in NOTE 162

These ten were already what the game does, or they were already behind a switch. The every-row line now says so.

- **3.20 Federal commission and the ISS.** Match.
- **4.9 Limpet removal.** Match.
- **4.10 Photon missile.** Match-behind-flag. `PHOTON_LIMPET_MODE`.
- **5.18 Photon interaction.** Match-behind-flag. `PHOTON_FOLLOW_DAMP_MODE` and `PHOTON_LIMPET_MODE`.
- **6.12 Planet destroy experience.** Match. +50 experience and −1 alignment.
- **8.8 NPCs and player fighters.** Match.
- **10.2 Joining.** Match-behind-flag. `CORP_ALIGNMENT_RULE`.
- **13.1 Direct messages.** Match-behind-flag. `MAIL_MODE` and `COMMS_V311_MODE`.
- **13.3 Mail.** Match-behind-flag. `MAIL_MODE`.
- **14.5 Evil trading loops.** Match-behind-flag. `EVIL_TRADE_LOOP_MODE`.
