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
| Photon wave duration | 1 second, or 10 seconds, or 20 seconds | Cabal `twgs.html` General Editor Two: `Photon Wave Dur. : 1 seconds.` Modern manual `advanced__twgs-settings.md`, General Editor Two, row P: photon wave duration 1 second. Gypsy's v2.03 V-screen: "Photon Missile Wave duration is 10 seconds." GameA TWSTATS [Settings] prints `Photon Missile Duration=20 Sec` (`docs/playtests/twgs-live/twstats-costs-ven.txt`). Cabal `other.html` option P says a sysop may set 1 second or 10 seconds. That is a setting choice, not a second v3.11 default. | Recommend cabal and the modern manual, 1 second, for v3.11. The tip already maps that 1 second to `PHOTON_WAVE_DURATION` 1 day-tick (`constants.py`). Gypsy's 10 seconds and GameA's 20 seconds are DIFFERENT and deferred: there is no realtime photon clock, and they are not applied. No duration switch was added. `PHOTON_CLOAK_SETTINGS_MODE` (row 230) does not change the duration. |

## NOTE 150 — ports, trading, haggling

| Row | Competing numbers | Sources | Current choice |
|---|---|---|---|
| 2.8 Port regeneration | 5 percent a day, a sample of 1 percent, or the economy2 10 percent pair | v3.05 revision history: the TEDIT range is 1 to 200 percent and the standard is 5 percent. Cabal `twgs.html` shows one game at 1 percent. economy2's T-Edit shows productivity 261, 95 and 210 on maximums 2610, 950 and 2100, which is 10 percent of capacity. | `PORT_REGEN_PER_DAY` stays 0.05. `PORT_REGEN_MODE` (row 22) applies that 5 percent to the maximum, once, when it is on and the drain curve is off. Legacy still applies it once to productivity. The 1 percent sample is not the on value. Row 224 `PORT_DRAIN_CURVE_MODE` restocks 10 percent of the maximum, once, while it is on, including under the v311 profile. That 10 percent is the economy2 pair, not 5 percent applied twice. No new default was added. |
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

## Ven 2026-10-24 — hardware prices still queued

Read-only. `docs/playtests/twgs-live/twstats-costs-ven.txt`. GameA `TWSTATS.TXT` v3.34b `[Costs]`. Photon Missile=40,000 cr and Atomic Detonator=15,000 cr are on that card. Stored `PHOTON_MISSILE_COST` 12,000 and `ATOMIC_DETONATOR_COST` 60,000 stay. This note does not switch them.

| Row | Competing numbers | Sources | Current choice |
|---|---|---|---|
| 4.15 Type I TWarp | 12,500, or 50,000 | Stored `SHIP_TW_TYPE1_COST` is the cabal twgs.html TEDIT sample 12,500. Live GameA TWSTATS prints Type I TWarp=50,000 cr. | Stored 12,500 stays. DIFFERENT. Queued. No new switch. |
| 4.15 Type II TWarp | 20,000, or 80,000 | Stored `SHIP_TW_TYPE2_COST` is 20,000. OldFAQ v2 prints 80,000 and is unused. Live GameA TWSTATS prints Type II TWarp=80,000 cr. | Stored 20,000 stays. DIFFERENT. Queued. No new switch. |
| 4.15 TWarp upgrade | 9,000, or 10,000, or OldFAQ 40,000 | Stored `SHIP_TW_UPGRADE_COST` is 9,000. OldFAQ v2 prints 40,000 and is unused. Live GameA TWSTATS prints TWarp Upgrade=10,000 cr. | Stored 9,000 stays. DIFFERENT. Queued. No new switch. |
| Citadel transport | 50,000 and 25,000 | Live GameA TWSTATS prints Citadel Transport Unit=50,000 cr and Citadel Transport Upgrade=25,000 cr. The planet transporter already charges `PLANET_TRANSPORTER_COST_FIRST` 50,000 and `PLANET_TRANSPORTER_COST_EXTRA` 25,000. | Those planet charges stay. The Hardware Emporium labels are not a shop switch. DIFFERENT. Queued. |

Disagreement with the later shop-price section: ship TransWarp quotes follow `hardware_price_live` there (SOURCE-CONFLICT). This section keeps the capture's queued reading, plus Photon Missile=40,000 cr and Atomic Detonator=15,000 cr, which that later section does not list.

## NOTE 177 - rulings under Ben's delegation (lean v3.11 original: Bible / TWGS default over sysop or TEDIT samples)

| Row | Competing readings | Sources | Ruling |
|---|---|---|---|
| 10.1 Corporate FlagShip | Only the C.E.O. buys one (bc24 purchase), or only the C.E.O. uses one | Gypsy_Big_Dummies_Guide: "Only C.E.O.'s can use Corporate Flagships so they are not available for trade" and "As C.E.O. you will have privileges ... such as owning an Corporate Flagship". | R10 A. `CFS_CEO_RULE` purchase stays. A member may board. `CFS_CEO_USE_MODE` still blocks boarding when set to v311 by itself, and the profile does not select it. An ex-C.E.O. keeps the hull he already flies. Charter cost: no source prints one; `CORP_CREATE_COST` 0 stays. |
| 6.10 / 6.12 Destroying a planet | -1 alignment (cabal formulas.html), or -50 (Bible) | S3 Bible, Atomic Detonator: "it takes your alignment down (50 points down)"; same line in Bible_TWGS_edit_2007. Cabal formulas.html table prints -1 / +50. | Bible. `PLANET_BLOW_ALIGN_MODE` (row 214) takes 50 alignment on the blow; +50 experience is the same. Legacy keeps -1. The ZDY trader-kill products are unchanged. |
| 8.1 Ferrengi combat odds | FERRSPEC 1.0 / 1.2 / 1.4, or the Bible chart 1.2 / 1.4 / 1.4 | NOTE 177 first read no Bible chart. That was wrong: the S3 Bible ship table prints Assault Trader 1.2:1 (3,000 / 2,000), Battle Cruiser 1.4:1, Dreadnaught 1.4:1. The 1.2 / 1.4 / 1.6 line in Someguy_MBBS_addendum is a later MBBS change. | Bible, per the delegation. `FERRENGI_ODDS_MODE` (NOTE 164, row 200) is that switch; on under the profile. Stored `FERRENGI_ODDS_BY_HULL` stays FERRSPEC. Counted once. |

## Ven 2026-10-24 — ship TransWarp and photon missile prices

Read-only. `docs/playtests/twgs-live/twstats-costs-ven.txt`. GameA `TWSTATS.TXT` v3.34b `[Costs]`.

| Row | Competing numbers | Sources | Current choice |
|---|---|---|---|
| 4.15 Type I TWarp | 12,500, or 50,000 | Stored `SHIP_TW_TYPE1_COST` is the cabal twgs.html TEDIT sample, 12,500. Live GameA TWSTATS prints `Type I TWarp=50,000 cr`. | Stored `SHIP_TW_TYPE1_COST` stays 12,500. `ship_tw_type1_cost()` returns 50,000 when `hardware_price_live()` is on (`HARDWARE_PRICE_MODE`, `TW2002_LIVE_PROFILE`, or `V311_PROFILE`). `SHIP_TW_MODE` stays. SOURCE-CONFLICT. No new profile row. |
| 4.15 Type II TWarp | 20,000, or 80,000 | Stored `SHIP_TW_TYPE2_COST` is the cabal TEDIT sample, 20,000. OldFAQ v2 prints 80,000. Live GameA TWSTATS prints `Type II TWarp=80,000 cr`. | Stored `SHIP_TW_TYPE2_COST` stays 20,000. `ship_tw_type2_cost()` returns 80,000 on the same hardware-price card. SOURCE-CONFLICT. |
| 4.15 TWarp upgrade | 9,000, or 10,000, or 40,000 | Stored `SHIP_TW_UPGRADE_COST` is the cabal TEDIT sample, 9,000. OldFAQ v2 prints 40,000. Live GameA TWSTATS prints `TWarp Upgrade=10,000 cr`. | Stored `SHIP_TW_UPGRADE_COST` stays 9,000. `ship_tw_upgrade_cost()` returns 10,000 on the same card. SOURCE-CONFLICT. |
| Citadel Transport Unit / Upgrade | 50,000 and 25,000 | Live GameA TWSTATS prints `Citadel Transport Unit=50,000 cr` and `Citadel Transport Upgrade=25,000 cr`. Planet transport already charges `PLANET_TRANSPORTER_COST_FIRST` 50,000 and `PLANET_TRANSPORTER_COST_EXTRA` 25,000. | Already the planet transporter prices. No new shop switch. The Hardware Emporium label is not a second item. |
| 4.10 Photon missile | 12,000, or 40,000, or 160,000 | Stored `PHOTON_MISSILE_COST` is 12,000. Live GameA TWSTATS prints `Photon Missile=40,000 cr`. Cabal `twgs.html` General Editor Three prints Photon Missile $160,000. | Stored `PHOTON_MISSILE_COST` stays 12,000. `photon_missile_cost()` returns 40,000 when `hardware_price_live()` is on (`HARDWARE_PRICE_MODE`, `TW2002_LIVE_PROFILE`, or `V311_PROFILE`). SOURCE-CONFLICT. DIFFERENT on the stored card. Atomic detonators stay off this switch. |
## Ven 2026-10-24 — ship rename and limpet removal

Read-only. `docs/playtests/twgs-live/ship-rename-limpet-ven.txt`. No interactive dock. No turn counter.

| Row | Competing numbers | Sources | Current choice |
|---|---|---|---|
| 4.9 Limpet removal | 1,250, or 5,000 | Cabal `twgs.html` General Editor Three prints Limpet Removal $1,250. Live GameA TWSTATS prints Limpet Removal=5,000 cr. The same line is on GameK and the listed GameA backups. One `CostLimpetRemoval` field fills StarDock and Class 0. Cabal's Genesis, Armid, and Limpet mine prices in that sample also disagree with this BigBang card. | Stored `LIMPET_REMOVAL_COST` stays 1,250. `limpet_removal_cost()` returns 5,000 when `hardware_price_live()` is on (`HARDWARE_PRICE_MODE`, `TW2002_LIVE_PROFILE`, or `V311_PROFILE`). Both docks use that one fee. Turns were not measured. |
| 3.17 Ship rename | 5,000 in both sources. Turns not measured | Live GameA TWSTATS `Reregister Ship=5,000 cr`. Cabal TEDIT `$5,000`. Name prompts `(30 chars)` and `(30 letters)`. No before/after turn counter. | `SHIP_RENAME_COST` 5,000 and `SHIP_RENAME_NAME_MAX` 30 are CONFIRMED. The action stays behind `SHIP_RENAME_MODE`. The handler stays credit-only. That 0-turn result is not a measured turn cost. |

## Libram archives, the singles bar, and the 47-credit drop

Checked from the tip references only: Bible, cabal, MBBS, Gypsy, `docs/reference`, and the existing playtest notes. None of the three is a printed rule that can be wired. `STARDOCK_DOORS_MODE` row 233 stays as it is. Archives stay empty lines. The bar still takes no credits. No new switch.

| Reading | What is printed | What is not printed | Choice |
|---|---|---|---|
| Libram Universitatus archive contents | The 19 Oct capture lists the menu and nothing inside it (`docs/playtests/twgs-live/stardock-menus.txt`): `<A> Archive of Alien Races`, `<B> Archive of Galactic Organizations`, `<C> Miscellaneous Documents`, `<Q> To Leave`, under "Library, no charge". `illegal-goods.txt`: "Library charged nothing and listed archives, not goods." S3 and the 2007 Bible use a different key. The Levy list prints `<+> The Library console` and `<L> Return to your ship and leave`. S3, "The Library": "The library is not important, just interesting the first time you go. It tells you about 'Alien Derelicts' which have nothing to do with the game, and also gives you a glimpse at the ship specifications on the Ferrengi vessel(s)." `TWBible_original_v1x.txt` prints that sentence with "shipspecs". `TWFAQ_TW2002.faq.txt`: "Hit a plus sign to enter the Library and you can look at ANSIs of *non existing* Alien Derelicts and existing Ferrengi Craft." Iago: the `+` library is "useful only for determining which ships are currently being used by the Ferrengi. Data on alien derelicts is useless." Leonard Adolph, in Iago: "The Ferrengi ships in the Library appear when the ships in the .DAT file appear. Thus, the Battle Cruiser appearing in the Library indicates that at least 21 positions in the .DAT file are being used and there are that many Ferrengi roaming around. When the Dreadnaught appears in the library there are at least 31 Ferrengi ships in the game." | No source prints the ANSI, a document body, or which Libram key would show a Ferrengi hull. Cabal, the MBBS manuals, Gypsy, the modern manual, and the EIS v3 StarDock pages do not print "Libram Universitatus". NOTE 130: "L as a library and B as a singles bar are 3.34b. S3 puts the library on `+` and does not list a singles bar." | Deferred. Empty archive lines stay. The `+` Ferrengi-appearance sentence was not copied onto archives A, B, or C. That would invent the reading. |
| Singles bar price, options, effects | `TWFAQ_TW2002.faq.txt`: "Hit <B> to find the Singles Bar but *don't* go in because you'll get robbed." Iago and `Misc_Player_Tips_Tricks_Cheats.htm`: "Single's Bar, where you can get robbed. Nothing more." The capture prompt and exit are already behind row 233. The exit says the VidCredit account is "much lower" and prints no amount (`illegal-goods.txt`). | No price. No option list. No item name. "Nothing more" names no second effect. | Deferred. The door still confirms, prints the capture exit, and charges 0. A robbery amount was not added. |
| 47-credit StarDock drop | `illegal-goods.txt`: credits 140 on the previous tavern line, then "You have 93 credits." "The screen did not print the price. The balance fell by 47. No item name." | No Bible, cabal, MBBS, Gypsy, modern-manual, or EIS line names a 47-credit StarDock item or tip. Gypsy's "Ship Base Cost : 47,500" is a hull price. Someguy's "Page 47" is a page number. NOTE 130's "about 47 cr per equipment" is a port sample. | Deferred. 47 is not a product and is not a constant. |
