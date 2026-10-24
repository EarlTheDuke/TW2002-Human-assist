# V311 remaining gaps (NOTE 164)

NOTE 161 listed the open rows. NOTE 163, now on the tip, matched 6.7, 6.11, 9.2, 9.5, and 13.4. NOTE 162 moved the grades that were already true, and built the printed pieces that were not. NOTE 164 adds four switches. Two of those switches sit on rows NOTE 163 already graded, and those rows are counted once. Each row is listed once.

The grades are the 171 rows in the every-row list of `docs/plans/gap-map-refresh-v6.md`. Row 181 is NavPoints (`NAVPOINT_MODE`, NOTE 159). NOTE 162 uses rows 182-186. Row 187 is `BOUNTY_GOOD_MODE` from NOTE 163. NOTE 164 uses rows 200-203.

**161 of 171 rows match the original rule (94.2%).** That count is Match 73 plus Match-behind-flag 88. A Match-behind-flag row is coded, and its switch stays off until `V311_PROFILE` is `v311`. A normal game, with every switch at the stored default, matches 73 of 171 (42.7%). The other rows are Partial 7, Different 1, Missing 0, and Ben-decision 2. Eight rows are still Partial or Different.

Nine rows this file had left open are Match or Match-behind-flag on this tip: 2.5, 5.7, 5.14, 5.20, 6.10, 9.8, 10.1, 11.11, and 14.6. They are listed under Matched on this tip. 6.11 and 13.4 stay one grade each. `CORP_SHIP_DISBAND_MODE` and `FIGHTER_REPORT_MODE` are extra behaviours on those rows.

`docs/plans/V311_SOURCE_CONFLICTS.md` is on this tip. NOTE 164 updates the Ferrengi odds row and the times-blown row there.
## Matched in NOTE 163

- **6.7 Genesis class.** Match. The launch rolls a class when the torpedo commits, and a requested class is ignored. `PLANET_CLASS_MODE` stays off the profile because it would roll only M and U. The crowding note prints no weights.
- **6.11 Corp planet quirks.** Match-behind-flag, counted once. `CORP_PLANET_DISBAND_MODE` and `SPECIAL_HULL_RULES_MODE` are the planet split and the Tholian 4:1. `CORP_SHIP_DISBAND_MODE` (NOTE 164, row 201) is the ship sentence in the same v3.06 revision. It does not add a second grade.
- **9.2 Ways to gain experience.** Match. Trade, the first dock, midnight, genesis, a port destroy, and the kill share are the stored awards. An alien's own experience is not printed.
- **9.5 Other alignment sources.** Match-behind-flag. `BOUNTY_GOOD_MODE` row 187. A bounty on a good trader costs 1 alignment per 250 credits and no experience. The other named sources were already in.
- **13.4 Fighter and combat reports.** Match-behind-flag, counted once. `OWNER_HAZARD_NOTICE_MODE` and `SIEGE_REPORT_MODE` tell the owner about a landing, a fighter hit, a mine, and a siege. `FIGHTER_REPORT_MODE` (NOTE 164, row 203) is a separate list of sectors where that trader owns fighters, omitting a count of 0. It is not an observation field, and it does not add a second grade.

## Built in NOTE 162

Five switches, each defaulting to legacy. `V311_PROFILE=v311` turns the helper on. The string `1` does not.

- **1.8 Class 9 StarDock services.** Match-behind-flag. `FEDERATION_HALL_MODE` row 182. Federation Hall lists registrations, and the hardware counter shows a shop screen. NOTE 129 adds `SHIELD_POINT_MODE` (131 a point), `TAVERN_BAR_PRICE_MODE` (drink 80, food 24), and `CINEPLEX_PRICE_MODE` (show 1 at 100). The library and the singles bar are still not built. Fighters at 218 that day stay on the wave.
- **10.6 Transfers between members.** Match-behind-flag. `CORP_CARGO_TREASURY_MODE` row 183. Cargo holds move between members, and the corporation treasury takes deposits.
- **11.7 Underground.** Match-behind-flag. `UG_NAME_MODE` row 184. A total unknown (experience 1 on 19 Oct 2026) buys a new name for 100 credits. A higher experience has no printed price, so it is refused. The Underground menu sold no goods. `UG_NAME_CHANGE` stays false.
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

## Matched on this tip

These nine were still on the open lists. The v6 every-row grade is Match or Match-behind-flag, and the tip code is the evidence named there.

- **2.5 Price scale vs ship cost.** Match-behind-flag. Ports stay on the economy chart and ships stay on the Bible chart. `PORT_MAX_STOCK_MODE` row 223 holds a product maximum of 950 to 2,720. No source prints one scale. `economy.port_sell_price`, `universe._make_port`.
- **5.7 Ship versus ship.** Match. The exchange is the S4/S6 Safety Rating model and the printed expected value: shields, then fighters (S3 Scout 2:1, S2 1:1, S7 fighters-to-use). No source prints a random term (S7, unable to determine the random factors), so the loss split is that expected value under every profile. `combat._resolve_ship_attack_tw2002`. `tests/test_combat_exchange_sources_v1.py`.
- **5.14 Exp and alignment on death.** Match. NOTE 177. A pod costs `POD_EXP_LOSS` 10 percent experience and no alignment. Ship Destroyed costs `SD_EXP_LOSS` and `SD_ALIGN_LOSS`, half of each. `combat._destroy_ship_tw2002`.
- **5.20 Combat in FedSpace.** Match. NOTE 177. Attacking a fedsafe trader in FedSpace summons Captain Zyrain and pods the attacker (`fed.protect_fedspace_attack`, `FED_PROTECT_PUNISH` pod, stored `FED_MODE` tw2002). Attacking a Federal costs `FED_ATTACK_ALIGN_PENALTY` 10 alignment and the pod. `victory.is_fedsafe` leaves an evil trader unprotected.
- **6.10 Planet killer.** Match-behind-flag. NOTE 177. `PLANET_BLOW_ALIGN_MODE` row 214 takes 50 alignment on the blow. Legacy keeps the cabal −1. Experience stays +50. Killing a trader on the planet is `PLANET_ZDY_MODE`. Colonist-kill alignment is still unprinted. `V311_SOURCE_CONFLICTS.md`, NOTE 177, "Destroying a planet".
- **9.8 Rob and steal caps.** Match. NOTE 177. Rob max is experience times `ROB_CREDIT_FACTOR` 6. Steal max is experience divided by `STEAL_HOLD_DIVISOR` 21. `rob_steal.max_rob_credits`.
- **10.1 Create a corporation.** Match-behind-flag. NOTE 177. Filing a charter stays in, and `CORP_CREATE_COST` stays 0. `CFS_CEO_RULE` stays purchase. `CFS_CEO_USE_MODE` row 213 lets only the C.E.O. board a FlagShip. `corpships.board_block`. `V311_SOURCE_CONFLICTS.md`, NOTE 177, "Corporate FlagShip".
- **11.11 Big Bang options.** Match-behind-flag. Density, the one-way share, the 30 percent two-way lanes, and the 95 percent initial starports are `BIG_BANG_DENSITY_MODE`, `ONE_WAY_SHARE_MODE`, `TWO_WAY_WARP_MODE`, and `BIG_BANG_BUILT_MODE` row 221. Bubbles are Gold-only, so v3.11 has none. `universe.generate_universe`.
- **14.6 Ours-only systems.** Match-behind-flag. `ECON_WIN_MODE` row 215 turns the instant credits win off. `ALLIANCE_OFF_MODE` row 222 refuses an in-game pact. `play_to_day_cap` stays. `victory.check_victory`.

## Needs Ben's ruling

A Ben-decision grade, or a Partial whose number is still a choice Ben has not closed. Where the pair is already written, the section name is the one in `V311_SOURCE_CONFLICTS.md`.

- **1.5 StarDock location.** Ben-decision. StarDock stays in sector 1. `constants.STARDOCK_SECTOR`.
- **1.6 Terra colonists.** Partial. Daily regen is `TERRA_REGEN_PER_DAY` 750, and a load costs `TERRA_LOAD_TURNS` 1. The stored pool opens at `TERRA_MAX_COLONISTS` 100,000, one person per hold. `TERRA_COLONIST_MODE` row 25 opens at `TERRA_LIVE_START` 30,000 with `TERRA_LIVE_PER_HOLD` 1,000. `class0.handle_terra_colonists`. Small.
- **1.15 FedSpace fighter limit.** Partial. The stored tow is `FED_TOW_FIGHTER_LIMIT` 98, so a ship with 99 or more fighters is towed. `FED_TOW_LIMIT_MODE` row 168 uses 50 when it is on. `V311_SOURCE_CONFLICTS.md`, NOTE 151, "FedSpace fighter tow" (Bible over 50, Gypsy 99 or more). `fed.run_tows`. Small.
- **4.1 Genesis price.** Partial. Genesis works. `GENESIS_TORPEDO_COST` is 25,000. `GENESIS_TORPEDO_COST_LIVE` is 20,000. A sample settings screen prints 80,000. That pair is not a row in `V311_SOURCE_CONFLICTS.md`. Small.
- **6.2 Class-table citadel costs.** Partial. The class goods are on (`CITADEL_COST_MODE` via `citadel_fidelity_rules`). Build days are `CITADEL_DAYS_MODE` row 2. Class M level 1 in `CITADEL_CLASS_COSTS` is 1,000 colonists, 300 fuel, 200 organics, 250 equipment, and 4 days. `CLASS_M_FIDELITY_MODE` multiplies that colonist figure by 1,000. That figure is Ben's NOTE 19 choice, the same hold as row 6.3. Small.
- **6.3 Class M caps and the bell curve.** Ben-decision. `PLANET_MAX_COLONISTS` for class M stays 30,000 until Ben chooses. The handbook calls daily output a bell that peaks at half that cap. S1 prints no bell-curve shape, so `planets._worked` holds output at that peak above half. Population above half dies off under `PLANET_PROD_MODE` row 26. `constants.planet_prod_live`.

## Can't verify without the real game

A Ven or TWGS screen still has to print the missing number. Guessing it would invent a rule.

- **12.4 Nightly Extern.** Partial. `runner.tick_day` already runs the jobs the sources name: retreats, Ferrengi, the corp penalty, the Class 0 sweep, Terra regen, empty-ship repossession, Fed tows, port regen, bust clearing, photon waves, cloak fails, NavHaz, alien hops, planet production, citadels, treasury, and tax. Collisions and special-port rebuilds are `PLANET_COLLISION_MODE` and `SPECIAL_PORT_DEFENCE_MODE`. `INACTIVE_USER_MODE` row 177 deletes a disconnected human after 30 quiet wall-clock days and stays off. `V311_SOURCE_CONFLICTS.md`, NOTE 151, "Days until an inactive user is deleted" (30, or Gypsy's 7). `INACTIVITY_TIMEOUT_MODE` row 178 sleeps a quiet lobby game after 14,400 seconds and stays off. A job past that list has no name. A live Extern would have to print it. Medium.

## Still Partial or Different

- **2.15 Attack a port.** Partial; confirmed samples Match-behind-flag. Ven GameA v3.34b on 2026-10-24 (`docs/playtests/twgs-live/gap215-port-attack-2026-10-24.md`). When `PORT_ATTACK_MODE` is live, class fallbacks are class 1 H'Catha def 46 / laser 337, class 4 Duriron Minor def 110 / laser 1419, class 6 Khancuhn Primus def 98 / laser 598, class 7 Balmer def 98 / laser 1121. DEF_ONLY fallbacks: class 2 def 55, class 3 def 86, class 5 def 59, with no laser. A captured port name uses that port's def (Peleus 86, Anaxagoras Primus sector 913 def 60). Non-Fed class 8 Vergil Minor def 99 is stored and not applied to engine class 8 (StarDock). Class 0 and class 9 stay BLOCKED. Lasers for classes 2, 3, 5, and non-Fed 8 are still open. `PORT_ATTACK_MODE` row 30 and `PORT_ATTACK_ALL_CLASSES_MODE` row 138 stay legacy. `runner._handle_port_attack`. Medium.
- **4.8 Armid price.** Partial. Detonation is the stored half-count at 20 (`hardware.armid_detonation_hits`). The shop price is `HARDWARE_PRICE_MODE` row 14: stored `ARMID_MINE_COST` 100, live card `ARMID_MINE_COST_LIVE` 1,000. The unit price is sysop-set. Small.
- **12.3 Real-time movement.** Different. Ships move by turns. `DAY_ROLL_CLOCK_MODE` rolls the day while a seat holds the turn. `PLANET_REALTIME_PROD_MODE` stays off, because the original produces at Extern. No speed table is printed. Large.

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
