# V311 remaining gaps (NOTE 164)

NOTE 161 listed the open rows. NOTE 163, now on the tip, matched 6.7, 6.11, 9.2, 9.5, and 13.4. NOTE 162 moved the grades that were already true, and built the printed pieces that were not. NOTE 164 adds four switches. Two of those switches sit on rows NOTE 163 already graded, and those rows are counted once. Each row is listed once.

The grades are the 171 rows in the every-row list of `docs/plans/gap-map-refresh-v6.md`. Row 181 is NavPoints (`NAVPOINT_MODE`, NOTE 159). NOTE 162 uses rows 182-186. Row 187 is `BOUNTY_GOOD_MODE` from NOTE 163. NOTE 164 uses rows 200-203. Row 228 is `ATTACK_TURN_MODE` (#164). Row 235 is `SELF_DESTRUCT_PENALTY_MODE` (R5 B).

**169 of 171 rows match the original rule (98.8%).** That count is Match 75 plus Match-behind-flag 94. The every-row list was 75 and 93 before 12.4 moved; 4.8 had already moved into the 93. A header that once said 76 and 91 was one swap off an earlier list. A Match-behind-flag row is coded, and its switch stays off until `V311_PROFILE` is `v311`. A normal game, with every switch at the stored default, matches 75 of 171 (43.9%). The other rows are Partial 1, Different 0, Missing 0, and Ben-decision 1. Two rows are still not a full match. 4.8 and 12.4 are in the 94. Detonation is Match and is not a second row. 12.4 added no switch.

R1–R14 from `V311_RULINGS_FOR_BEN.md` are adopted. 6.11 and 13.4 stay one grade each. `CORP_SHIP_DISBAND_MODE` and `FIGHTER_REPORT_MODE` are extra behaviours on those rows. GAP 6.3 stays Match-behind-flag (#183). GAP 2.15 stays Partial; the confirmed samples stay Match-behind-flag (#185).

`docs/plans/V311_SOURCE_CONFLICTS.md` is on this tip. NOTE 164 updates the Ferrengi odds row and the times-blown row there.
## Matched in NOTE 163

- **6.7 Genesis class.** Match. The launch rolls a class when the torpedo commits, and a requested class is ignored. `PLANET_CLASS_MODE` stays off the profile because it would roll only M and U. The crowding note prints no weights.
- **6.11 Corp planet quirks.** Match-behind-flag, counted once. `CORP_PLANET_DISBAND_MODE` and `SPECIAL_HULL_RULES_MODE` are the planet split and the Tholian 4:1. `CORP_SHIP_DISBAND_MODE` (NOTE 164, row 201) is the ship sentence in the same v3.06 revision. It does not add a second grade.
- **9.2 Ways to gain experience.** Match. Trade, the first dock, midnight, genesis, a port destroy, and the kill share are the stored awards. An alien's own experience is not printed.
- **9.5 Other alignment sources.** Match-behind-flag. `BOUNTY_GOOD_MODE` row 187. A bounty on a good trader costs 1 alignment per 250 credits and no experience. The other named sources were already in.
- **13.4 Fighter and combat reports.** Match-behind-flag, counted once. `OWNER_HAZARD_NOTICE_MODE` and `SIEGE_REPORT_MODE` tell the owner about a landing, a fighter hit, a mine, and a siege. `FIGHTER_REPORT_MODE` (NOTE 164, row 203) is a separate list of sectors where that trader owns fighters, omitting a count of 0. It is not an observation field, and it does not add a second grade.

## Built in NOTE 162

Five switches, each defaulting to legacy. `V311_PROFILE=v311` turns the helper on. The string `1` does not.

- **1.8 Class 9 StarDock services.** Match-behind-flag. `FEDERATION_HALL_MODE` row 182. Federation Hall lists registrations, and the hardware counter shows a shop screen. NOTE 129 adds `SHIELD_POINT_MODE` row 225 (131 a point), `TAVERN_BAR_PRICE_MODE` row 226 (drink 80, food 24), and `CINEPLEX_PRICE_MODE` row 227 (show 1 at 100). Fighters at 218 that day stay on the wave. `STARDOCK_DOORS_MODE` row 233 puts the Libram Universitatus on the where-to list and opens the singles bar from B, which is not on that list. The archives stay empty lines. The bar stays free. The unnamed 47-credit drop stays deferred. Checked again from the tip references only. No engine change.

  The name "Libram Universitatus" and the archive keys are the 19 Oct capture (`docs/playtests/twgs-live/stardock-menus.txt`): `<A> Archive of Alien Races`, `<B> Archive of Galactic Organizations`, `<C> Miscellaneous Documents`, `<Q> To Leave`, under "Library, no charge". That capture does not print a document body. `illegal-goods.txt` says "Library charged nothing and listed archives, not goods." S3 and the 2007 Bible print a different door: `<+> The Library console`, and `<L> Return to your ship and leave`. S3, "The Library": "The library is not important, just interesting the first time you go. It tells you about 'Alien Derelicts' which have nothing to do with the game, and also gives you a glimpse at the ship specifications on the Ferrengi vessel(s)." `TWBible_original_v1x.txt` is the same sentence with "shipspecs". `TWFAQ_TW2002.faq.txt`: "Hit a plus sign to enter the Library and you can look at ANSIs of *non existing* Alien Derelicts and existing Ferrengi Craft." Iago: "+" is "useful only for determining which ships are currently being used by the Ferrengi. Data on alien derelicts is useless." Leonard Adolph, in Iago: "The Ferrengi ships in the Library appear when the ships in the .DAT file appear. Thus, the Battle Cruiser appearing in the Library indicates that at least 21 positions in the .DAT file are being used and there are that many Ferrengi roaming around. When the Dreadnaught appears in the library there are at least 31 Ferrengi ships in the game." That is the `+` console. It does not print the ANSI, and it does not say which Libram archive would show a hull. Cabal, the MBBS manuals, Gypsy, the modern manual, and the EIS v3 StarDock pages do not print Libram archive text. Filling A, B, or C would invent the reading. Quotes: `V311_SOURCE_CONFLICTS.md`, "Libram archives, the singles bar, and the 47-credit drop".

  Singles bar. `TWFAQ_TW2002.faq.txt`: "Hit <B> to find the Singles Bar but *don't* go in because you'll get robbed." Iago and `Misc_Player_Tips_Tricks_Cheats.htm`: "Single's Bar, where you can get robbed. Nothing more." No price, no option list, and no item. The capture exit says the VidCredit account is "much lower" and does not print a number. Credits on the previous tavern line were 140. The next hardware line was 93. `illegal-goods.txt`: "The screen did not print the price. The balance fell by 47. No item name." 47 is that subtraction. Gypsy's "Ship Base Cost : 47,500" is a hull price. Someguy's "Page 47" is a page number. The opening-quote note's "about 47 cr per equipment" is a port sample. None of those is this drop. The door still confirms and does not bill.
- **10.6 Transfers between members.** Match-behind-flag. `CORP_CARGO_TREASURY_MODE` row 183. Cargo holds move between members, and the corporation treasury takes deposits.
- **11.7 Underground.** Match-behind-flag. `UG_NAME_MODE` row 184. A total unknown (experience 1 on 19 Oct 2026) buys a new name for 100 credits. A higher experience has no printed price, so it is refused. The Underground menu sold no goods. `UG_NAME_CHANGE` stays false.
- **11.9 Fed attack on evil players.** Match-behind-flag. `FED_HUNT_MODE` row 185. An evil ship that meets a Federal is destroyed. A sector with no Federal is left alone.
- **14.1 Computer menu helpers.** Match-behind-flag. `CIM_MODE` row 186. CIM lists explored sectors and ports, hides a port behind hostile fighters, and plots a path. NavPoints are `NAVPOINT_MODE` row 181. Computer B is Begin Self Destruct when ship exit is on (NOTE 110 / NOTE 129, `computer-b.txt`). Y reuses `handle_self_destruct`. `<` stays the previous-sector key. No new row.

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
- **5.14 Exp and alignment on death.** Match-behind-flag. R5 B. A pod costs `POD_EXP_LOSS` 10 percent experience and no alignment. A Ship Destroyed that is not the button still costs half of each. Self-destruct is `SELF_DESTRUCT_PENALTY_MODE` row 235. `combat._destroy_ship_tw2002`.
- **5.20 Combat in FedSpace.** Match-behind-flag. R6 A. `FEDSAFE_FIGHTER_CAP_MODE` row 167. More than 50 fighters removes protection. 50 is still safe. `fed.protect_fedspace_attack`. `victory.is_fedsafe`.
- **6.10 Planet killer.** Match-behind-flag. NOTE 177. `PLANET_BLOW_ALIGN_MODE` row 214 takes 50 alignment on the blow. Legacy keeps the cabal −1. Experience stays +50. Killing a trader on the planet is `PLANET_ZDY_MODE`. Colonist-kill alignment is still unprinted. `V311_SOURCE_CONFLICTS.md`, NOTE 177, "Destroying a planet".
- **9.8 Rob and steal caps.** Match. NOTE 177. Rob max is experience times `ROB_CREDIT_FACTOR` 6. Steal max is experience divided by `STEAL_HOLD_DIVISOR` 21. `rob_steal.max_rob_credits`.
- **10.1 Create a corporation.** Match. R10 A. Filing a charter stays in, and `CORP_CREATE_COST` stays 0. `CFS_CEO_RULE` stays purchase. A member may board. `CFS_CEO_USE_MODE` is not selected by the profile. `corpships.board_block`.
- **11.11 Big Bang options.** Match-behind-flag. Density, the one-way share, the 30 percent two-way lanes, and the 95 percent initial starports are `BIG_BANG_DENSITY_MODE`, `ONE_WAY_SHARE_MODE`, `TWO_WAY_WARP_MODE`, and `BIG_BANG_BUILT_MODE` row 221. Bubbles are Gold-only, so v3.11 has none. `universe.generate_universe`.
- **14.6 Ours-only systems.** Match-behind-flag. R14 A. `ALLIANCE_OFF_MODE` row 222 refuses an in-game pact. The planet bonus stays off. The day cap and the 100,000,000 credit finish stay. `ECON_WIN_MODE` is not selected. `victory.check_victory`.

## Needs Ben's ruling

- **1.5 StarDock location.** Ben-decision. StarDock stays in sector 1. `constants.STARDOCK_SECTOR`. Nothing in R1–R14 picks a sector.

## Adopted from the suggested reply

These left the Ben list. The grade is the every-row line in `gap-map-refresh-v6.md`.

- **1.6 Terra colonists.** Match. R1 A. Stored pool `TERRA_MAX_COLONISTS` 100,000, one person per hold. `TERRA_COLONIST_MODE` is unchanged.
- **1.15 FedSpace fighter limit.** Match-behind-flag. R2 A. `FED_TOW_LIMIT_MODE` row 168. Bible more than 50 when on. Stored Gypsy stays 98.
- **2.5 Price scale.** Match-behind-flag. R3 A. Left as it was.
- **4.1 Genesis price.** Match. R4 A. `GENESIS_TORPEDO_COST` is 25,000. The live card 20,000 stays on `HARDWARE_PRICE_MODE` and is not the adopted price.
- **5.14 Self-destruct.** Match-behind-flag. R5 B. `SELF_DESTRUCT_PENALTY_MODE` row 235.
- **5.20 FedSpace fighters.** Match-behind-flag. R6 A. `FEDSAFE_FIGHTER_CAP_MODE` row 167. More than 50.
- **6.2 Class M level 1.** Match. R7 A. Printed 1,000 colonists. `CLASS_M_FIDELITY_MODE` was not flipped.
- **6.3 Handbook curve.** Match-behind-flag. Already on the tip (#183). Not reopened.
- **8.1 through 14.6.** R8 A, R9 B, R10 A, R11 A, R12 A, R13 A, R14 A. R10 stopped selecting `CFS_CEO_USE_MODE`. R14 stopped selecting `ECON_WIN_MODE`. The others already matched.

## Can't verify without the real game

A Ven or TWGS screen still has to print a missing number. Guessing it would invent a rule. 12.4 left this list: the printed Extern and midnight jobs are named in the every-row line of `gap-map-refresh-v6.md`, and they already run. 2.15 stays under Still Partial because lasers for classes 2, 3, and 5, and for non-Fed class 8, are still unmeasured.

## Graded this pass

- **4.8 Armid price.** Detonation Match. Shop unit price Match-behind-flag. Counted once, as Match-behind-flag. Stored half-count at 20 (`hardware.armid_detonation_hits`). `HARDWARE_PRICE_MODE` row 14 keeps `ARMID_MINE_COST` 100 and `ARMID_MINE_COST_LIVE` 1,000. The Bible prints no Armid unit price. Cabal General Editor Three $4,000 is that TEDIT sample, the same dump as Genesis $80,000, and it is not a third constant. Ven GameA `Armid Mine=1,000 cr` is the live card. Small.
- **12.4 Nightly Extern.** Match-behind-flag. Counted once. No new switch. Cabal glossary Extern names NavHaz, empty-ship repossession, armament tows, busts, port construction, and player and corp timeouts. Its Midnight names the return from death, Class 0 and Class 9 prices, and +1 experience and +1 alignment. The docs-wiki Glossary numbers the same night, plus the tax reset, the Grimy curse, 2 pods, colonist jettison, the corp-break-in reset, the MSL sweep, two-planet collisions, Class 0 and Class 9 rebuilds, and the Underground password reset. `runner.tick_day` runs those jobs. The day number is the reset for the curse, the jettison, the password attempts, and the pods. Collisions and rebuilds stay `PLANET_COLLISION_MODE` and `SPECIAL_PORT_DEFENCE_MODE`. `INACTIVE_USER_MODE` and `INACTIVITY_TIMEOUT_MODE` stay off. The wiki's level-2 MSL citadel is the t21 conflict, and TWGS keep stays. Cabal `twgs.html` NavHaz dispersion 100 percent stays the hardware note's MBBS 3 percent. v3.06 fixed rogue assets on a maintenance delete, and Iago 47 keeps the corporation, so that sentence was not wired again. Medium.

## Still Partial

2.15 is the only counted Partial.

- **2.15 Attack a port.** Partial; confirmed samples Match-behind-flag. Ven GameA v3.34b on 2026-10-24 (`docs/playtests/twgs-live/gap215-port-attack-2026-10-24.md`). When `PORT_ATTACK_MODE` is live, class fallbacks are class 1 H'Catha def 46 / laser 337, class 4 Duriron Minor def 110 / laser 1419, class 6 Khancuhn Primus def 98 / laser 598, class 7 Balmer def 98 / laser 1121. DEF_ONLY fallbacks: class 2 def 55, class 3 def 86, class 5 def 59, with no laser. A captured port name uses that port's def (Peleus 86, Anaxagoras Primus sector 913 def 60). Non-Fed class 8 Vergil Minor def 99 is stored and not applied to engine class 8 (StarDock). Class 0 and class 9 stay BLOCKED. Lasers for classes 2, 3, 5, and non-Fed 8 are still open. `PORT_DEFENSE_RATING` and `PORT_LASER_BARRAGE` hold those confirmed samples (#185), including classes 1, 2, 3, 4, 5, and 7 beside class 6. `PORT_ATTACK_MODE` row 30 and `PORT_ATTACK_ALL_CLASSES_MODE` row 138 stay legacy. `runner._handle_port_attack`. Medium.

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
- **4.10 Photon missile.** Counted Match-behind-flag. Limpet attach is Match-behind-flag (`PHOTON_LIMPET_MODE`). The level 6 interdictor damp is Match-behind-flag (`PHOTON_INTERDICT_DAMP_MODE` row 234). The price is Match-behind-flag (`photon_missile_cost` on `HARDWARE_PRICE_MODE`). The FedSpace photon card is Match-behind-flag (`PHOTON_CLOAK_SETTINGS_MODE` row 230) and stays off. Duration is still not one number. Recommend the cabal and modern-manual 1 second for v3.11. Cabal `twgs.html` General Editor Two prints `Photon Wave Dur. : 1 seconds.` The modern manual, General Editor Two, prints photon wave duration 1 second. Gypsy's v2.03 V-screen prints "Photon Missile Wave duration is 10 seconds." GameA TWSTATS prints `Photon Missile Duration=20 Sec`. The tip already maps that recommended 1 second to `PHOTON_WAVE_DURATION` 1 day-tick. Gypsy's 10 seconds and GameA's 20 seconds stay recorded and are not applied. There is no realtime clock and no duration switch. A seconds value was not added.
- **5.18 Photon interaction.** Match-behind-flag. `PHOTON_FOLLOW_DAMP_MODE`, `PHOTON_LIMPET_MODE`, and `PHOTON_INTERDICT_DAMP_MODE`.
- **6.12 Planet destroy experience.** Match. +50 experience and −1 alignment.
- **8.8 NPCs and player fighters.** Match.
- **10.2 Joining.** Match-behind-flag. `CORP_ALIGNMENT_RULE`.
- **13.1 Direct messages.** Match-behind-flag. `MAIL_MODE` and `COMMS_V311_MODE`.
- **13.3 Mail.** Match-behind-flag. `MAIL_MODE`.
- **14.5 Evil trading loops.** Match-behind-flag. `EVIL_TRADE_LOOP_MODE`.
