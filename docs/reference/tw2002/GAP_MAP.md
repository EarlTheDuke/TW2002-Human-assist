# TW2K vs Trade Wars 2002 (v3.x, TWGS 3.11 rules) - Gap Map
Generated 2026-10-03 (PT) for Ben. Read-only analysis; nothing in the repo was changed.

## Plain-words summary (15 lines)
1. Trade Wars 2002 is a space game: you fly a ship, buy goods cheap at one space-port, sell them for more at another, build planets, and fight other players.
2. TW2K is our computer copy of it. I compared our copy to the old rule books one rule at a time, like checking homework answers against the answer key.
3. What we already copy well: flying between sectors, the three trade goods, the port types, planets with their citadel forts (that part is almost finished), basic corporations, and the Ferrengi bad guys.
4. Biggest gap one is prices: in the real game every port has its own personality and your experience changes the price; ours uses one simple curve, and haggling never costs you anything.
5. Biggest gap two is ships: the real game has 16 ships with their own limits; we have 10, several cost 10 times more than they should, and nothing limits how many mines or torpedoes a ship can carry.
6. Biggest gap three is fighting: real fighters left in a sector can block you, charge a 5-credit-per-fighter toll, or let you run away or surrender; ours is mostly one dice roll.
7. When your ship blows up, the real game gives you a tiny escape pod and takes some of your experience; ours hands you a free new ship, and three deaths knock you out for good.
8. The real game has gadgets we do not have yet: cloaking, corbomite traps, mine sweepers, real scanners you must buy, and a TransWarp drive for ships.
9. The good-guy / bad-guy system is mostly missing: no robbing or stealing from ports, no police station, no bounties, no Federal patrol ships, no bank, no tavern.
10. Also missing are the special towns: Terra (where colonists come from), the other two Class 0 supply ports, and a StarDock you have to go find.
11. Some differences are on purpose and I marked them: the StarDock is always sector 1, the game is turn-based, there is a 30-day finish with winners, and we have alliances the original never had.
12. Where the old books disagree with each other (ship prices, how hard mines hit, the rob formula, how many turns per day) I flagged it so Ben can choose instead of me guessing.
13. The tables below hold 171 rules: 9 match, 34 partly match, 59 are different, and 69 are missing.
14. Suggested start: fix prices, ship limits and fighter rules first, because they change how every single game feels; the 15-step list below says what to build in what order.
15. Anything tagged UNVERIFIED means I could not prove it from the files on this computer, so treat it as a question, not a fact.

## Proposed build order: the 15 most valuable next slices
1. **Economy realism (rows 2.3-2.11, 1.10)**  
   Per-port price personality (MCIC and productivity), experience-based prices, a haggle that can fail and cost a turn, 1-turn docking, slower regen, ports that start empty. Needs the human economy-scale decision first. Size M, High.
2. **Ship roster and caps (3.1-3.16, 4.17)**  
   Add the 6 missing ships, per-ship max holds, mines, genesis, photons, fighters per attack and combat odds, then fix prices and turns-per-warp once the source choice is made. Size M, High.
3. **Sector fighter rules (5.4-5.6, 5.10-5.11, 1.20)**  
   Offensive wave of 1.25x, defensive fighters that challenge (attack, retreat, surrender), toll at 5 cr per fighter, plus a way to pick your fighters back up. Size M, High.
4. **Ship-vs-ship combat core (5.7-5.9)**  
   Attacker picks how many fighters, ship odds and per-attack caps apply, a defender flees when outgunned by 1.25x. Replaces the 3-round dice roll. Size L, High.
5. **Death and escape pods (5.12-5.15)**  
   Destroyed ships leave a pod that flees, 10% exp loss, a pods-per-day limit (or keep elimination as a switch), salvage. Size M, High.
6. **Planet economy limits (6.3-6.6, 6.8, 6.2)**  
   Max colonists and stock per class, bell-curve production, 5 planets per sector, genesis planets start empty, planet-to-port trading, switch the class-table citadel costs on. Size M, High.
7. **Scanners and hidden information (4.11-4.14, 6.1)**  
   Buyable density and holo scanners with real numbers, a planet scanner, and hiding planet and ship fighter counts from plain view. Size M, High.
8. **Experience and alignment engine (9.2-9.5, 9.8, 9.6)**  
   Kill, port and planet formulas for exp and alignment, exp loss on death, rank titles; alignment starts to matter again. Size M, Med.
9. **Rob, steal, bust (2.12-2.14)**  
   The evil money path: alignment under -100, exp-limited takes, 1-in-50 bust, daily bust clearing. Needs step 8 first. Size M, Med.
10. **Hardware set (4.3-4.9, 4.17, 11.1)**  
   Cloak, corbomite, mine disruptor, beacons, limpet removal, ether probes that fly a path and can be shot down. Size M, Med.
11. **Photon and hazard order (4.10, 5.1-5.3, 5.18)**  
   Photon only on the two right ships, fired next door, switches off mines and fighters for a short wave; sector events in the real order; mine damage and 50% detonation. Size M, Med.
12. **Class 0 ports, Terra, random StarDock (1.5-1.7)**  
   Add Terra with limited colonists, Alpha Centauri and Rylos supply ports with daily-moving prices; optionally hide the StarDock. Size M, Med.
13. **FedSpace, Fed ships, Police and bounties (1.14-1.17, 8.7, 11.3, 11.4, 11.9, 3.20)**  
   Fed patrol ships, tow-outs, commission at 500 alignment, player bounties, repossession of an evil ISS. Size L, Med.
14. **Ship TransWarp, transporter, multiple ships, towing (4.15, 4.16, 3.18, 14.2)**  
   Ships can own spare ships, tow them, jump by TransWarp to a fighter, and beam between ships. Size L, Med.
15. **Ferrengi and alien upgrade (8.1-8.3, 8.6)**  
   Three real Ferrengi ships, tribute and surrender, grudges, plus neutral alien traders to shoot at. Size M, Med.

Later / lower value: port attack and building (2.15-2.16), Galactic Bank, Tavern, Underground (11.5-11.8), corp extras (10.x), messaging channels (13.x), Gold-mode aliens, real-time movement.

## Counts by status
| Category | Match | Partial | Different | Missing | Total |
|---|---|---|---|---|---|
| 1. Universe, sectors, warps, FedSpace, StarDock, special ports | 2 | 1 | 7 | 10 | 20 |
| 2. Ports and trading | 2 | 2 | 8 | 6 | 18 |
| 3. Ships | 0 | 6 | 8 | 6 | 20 |
| 4. Ship equipment and hardware | 0 | 2 | 6 | 9 | 17 |
| 5. Combat (not planets) | 1 | 3 | 7 | 8 | 19 |
| 6. Planets (remaining gaps only; shipped work B1-E3 is not re-listed) | 0 | 3 | 7 | 4 | 14 |
| 7. Citadels (gaps only) | 2 | 0 | 2 | 0 | 4 |
| 8. Aliens, NPCs, bad guys | 0 | 1 | 3 | 4 | 8 |
| 9. Players: turns, experience, alignment, ranks | 0 | 1 | 3 | 5 | 9 |
| 10. Corporations | 1 | 6 | 2 | 3 | 12 |
| 11. Special locations and events | 0 | 3 | 0 | 8 | 11 |
| 12. Game flow | 1 | 2 | 3 | 1 | 7 |
| 13. Messaging, transmissions, probes | 0 | 3 | 1 | 2 | 6 |
| 14. Anything else notable | 0 | 1 | 2 | 3 | 6 |
| **All** | **9** | **34** | **59** | **69** | **171** |

Source tags across rows: CONFIRMED 128, SOURCE-CONFLICT 19, UNVERIFIED 24 (a row counts as the worst tag it carries).

## Decisions where sources conflict (need a human choice)
1. **Ship prices and some stats**: Bible chart (Merchant Cruiser 41,300 ... ISS 339,000) vs OldBBS_2002SHIP.txt (26,300 ... 128,600) vs ours (several 10x higher). Also Scout fighters 250 (Bible) vs 150 (MBBS), Corporate Flagship shields 1,000 (Bible) vs 1,500 (MBBS, docs wiki, OldBBS). Decide which table is the target.
2. **Economy scale**: Original sample trades suggest much larger profit per hold than our 18/25/36 base prices, while our big ships cost far more than the original. Change both together or neither.
3. **Starting fighters**: 30 (Bible, V-screen sample) vs ours 20.
4. **Turns per day**: 250 (cabal glossary, classic), 750 (Gypsy sample), 1000 (cabal income table, ours).
5. **Armid mines**: Half the mines detonate (formulas.html), Bible says 20 damage each; ours is 100 damage, 1-10 hits. A v3 per-mine number was not found.
6. **Sector offensive fighter wave**: formulas.html says 1.25x your max fighters+shields in one place and 1.25x the fighters needed to kill you in another.
7. **Rob and steal factors**: Credits x3 vs x6 and holds /30 vs /21 (classic vs MBBS); John Pritchett's exp table differs again.
8. **Port regeneration**: Standard 5%/day (v3.05 notes) vs 1% in the sample game vs ours about 10% effective.
9. **Fighter and shield prices**: 160-239 on an 87-day cycle (Hekate) vs 110-234 on about 30 days (Iago, v1.03d) vs ours flat 50 / 10.
10. **Hardware prices**: Bible values (Genesis 25,000 ...) vs one sample TEDIT (Genesis 80,000, photon 160,000 ...). Ours uses Bible-like Genesis, much cheaper others.
11. **FedSpace fighter tow limit**: More than 50 fighters (Bible) vs 99 or more (Gypsy).
12. **Federal commission**: Alignment 500 to apply, 1000 automatic (docs wiki, Gypsy, Iago, Bible agree); ours requires 2000 and a unique ship.
13. **Atmospheric quasar**: x0.5 (TWGS Classic) vs x2 (MBBS); ours x2 by earlier decision.
14. **Planet destroy alignment**: -50 (Bible) vs -1 when killing a trader on a planet (formulas.html); ours -50.
15. **Pods vs elimination**: Original: 2 pods a day, third death is out until midnight. Ours: 3 deaths is out for the whole match. Keep as a switch?
16. **Experience and alignment kill formulas**: MBBS vs Gold/classic versions; pick one family.
17. **Win conditions and turn recovery**: Original has no built-in win and returns turns hourly; ours has three win paths and a daily reset. Probably keep ours, but it is a decision.
18. **Corp disband rule**: Original v3.06: CEO-sector planets go to the CEO, others become Rogue. Ours keeps every living owner. Already a deliberate difference. `CORP_RULES.md` cr12 keeps `owner_keeps`; `v306` is the alt.

## How to read the tables

Source shorthand (all under C:\Users\sugar\tw2002_reference\):
- Bible = stardock_manuals_and_text_docs\Bible_TWGS_edit_2007_Clme.htm
- Gypsy_Big_Dummies_Guide.html, Iago_War_Manual.txt, Someguy_MBBS_manual.txt ("MBBS"), OldBBS_2002SHIP.txt, TWFAQ_FERRSPEC_ferrengi.txt, Misc_*.txt = stardock_manuals_and_text_docs\
- cabal X = cabal_strategy_site\X (formulas.html, haggling.html, economy1/2.html, twgs.html, pods.html, fleeing.html, glossary.html, corps.html); S1_planet_handbook_v1.01.html sits in the reference root.
- REV = classictw_museum_wiki\tw-attac_TW2002_v3_revision_history_to_v3.11.html; TWGS_v2_Revision_History.html is in the same folder.
- docs wiki X = classictw_docs_wiki\X.html (ship pages, Alignment, Big_Bang, Furbing ...)
- EIS X = eis_tw2002_v3_docs\X.html
Tags in column (a): CONFIRMED = two or more sources agree or a tested formula page states it; SOURCE-CONFLICT = sources disagree (both given); UNVERIFIED = one weak source, or I could not find it. Tags are mine; nothing here is a verbatim quote.
Ours (b): paths are under TW2K-grokbot-player\src\tw2k\engine\ unless noted; line numbers are from the files as read on 2026-10-03 (PT) and may shift. The repo was only read, never changed.
Status (c): Match = same rule/value; Partial = built but incomplete or only some values match; Different = built but works another way or with other numbers; Missing = not in the engine (checked by grep or by reading the handler).
Size/priority (d): S = a constants/rule tweak (hours), M = one new handler or system (a day or two), L = several systems (a week); priority is impact on feel of a 30-day, mostly-bot match (High/Med/Low).
Ours-vs-original note: docs\plans\planetary-warfare-comparison.md predates the shipped B1-E3 work; its "missing" list is stale and I did not trust it.


## 1. Universe, sectors, warps, FedSpace, StarDock, special ports

| # / item | (a) Original rule, source, confidence | (b) Ours | (c) Status | (d) Size / priority |
|---|---|---|---|---|
| 1.1 Universe size | Default 1000 sectors (more with Gold). [Big_Bang.html, cabal twgs.html] CONFIRMED | GameConfig.universe_size default 1000 (models.py, cli.py). | Match | S / Low |
| 1.2 Warp structure and one-way share | Big Bang makes about 30% extra two-way warps and about 3% one-way warps, so most lanes are two-way. [Big_Bang.html, twgs.html] CONFIRMED | universe.py: random spanning tree plus extras to avg_warps 2.7, then 15% of edges one-way (GameConfig.one_way_fraction), strong connectivity kept. | Different | S / Med |
| 1.3 Course length / plot course | Computer plots routes up to a max course length of 45 hops (setting 20-255). [Big_Bang.html] UNVERIFIED for 3.11 default | PLOT_COURSE action exists (actions.py); no max length found in the code I read (runner.py _bfs_path). | Missing | S / Low |
| 1.4 FedSpace = sectors 1-10 plus StarDock | FedSpace is sectors 1-10 plus the StarDock sector. [cabal glossary.html "Fed", Gypsy_Big_Dummies_Guide.html] CONFIRMED | K.FEDSPACE_SECTORS = 1..10 (constants.py). | Match | S / Low |
| 1.5 StarDock location | StarDock sits in a normal-looking sector that players must find (sample game: sector 3880 of 5000); only Terra is fixed at sector 1. [Gypsy_Big_Dummies_Guide.html V-screen sample, glossary.html] CONFIRMED | K.STARDOCK_SECTOR = 1 and universe.py makes sector 1 the StarDock; all bots start there when all_start_stardock. | Different | S / Low (deliberate, bot-friendly; keep unless you want exploration) |
| 1.6 Terra (sector 1) colonist source | Colonists are loaded at Terra: it holds a capped pool (about 100,000) that regrows (about 750/day), loading takes 1 turn, "Auto" is not allowed there. [Bible_TWGS_edit_2007_Clme.htm, TW2002 v3 revision history v3.00, S1_planet_handbook_v1.01.html] UNVERIFIED on exact numbers (Bible only) | No Terra. buy_equip item "colonists" at the StarDock for K.COLONIST_PRICE = 10 cr, unlimited, 0 turns (runner.py _handle_buy_equip:1647). | Different | M / Med |
| 1.7 Class 0 ports (Sol/Terra, Alpha Centauri, Rylos) | Three Class 0 ports sell holds, fighters, shields; prices change daily at midnight; they are cleaned at Extern like FedSpace but you CAN place fighters, mines and planets there. [cabal glossary.html "Class 0 Ports", Bible, Iago_War_Manual.txt] CONFIRMED | Missing. The single StarDock sells fighters/shields/holds at flat prices (runner.py _handle_buy_equip). universe.py has no Alpha Centauri/Rylos. | Missing | M / Med |
| 1.8 Class 9 StarDock services | StarDock holds Shipyard, Hardware Emporium, Police HQ, Galactic Bank, Tavern (Lost Traders), Underground access and Federation Hall. [EIS StarDockMenu.html, HardwareMenu, ShipyardMenu, PoliceMenu, BankMenu, TavernMenu] CONFIRMED | Only buy_ship and buy_equip at sector 1 (runner.py:1596, :1647). See categories 3, 4, 9, 11 for each service. | Partial | L / Med |
| 1.9 Ferrengal (Ferrengi home sector) | A fortified Ferrengi home sector exists (Bible: heavy mines; Planet Handbook shows a Ferrengal Quasar cannon). [Bible, S1_planet_handbook_v1.01.html] UNVERIFIED (detail) | Missing; four Ferrengi are seeded in random deep-space sectors (universe.py). | Missing | S / Low |
| 1.10 Port density | Big Bang: up to 40% of sectors get ports, 95% of that built at start. [Big_Bang.html, twgs.html] CONFIRMED | K.PORT_SPAWN_PROBABILITY = 0.65 of sectors 11+ (about 65%), plus FedSpace Federal ports. | Different | S / Med (changes how easy trade pairs are) |
| 1.11 Planet density at start | Big Bang: up to 20% of sectors (range 2-40%) get natural planets. [Big_Bang.html, twgs.html] CONFIRMED | GameConfig.planet_spawn_probability = 0.03 on sectors 11+, uniform random class, unowned (universe.py). | Different | S / Low |
| 1.12 Max planets per sector | Sector limit of 5 planets (TEDIT; V-screen "Maximum number of Planets per sector: 5"). [Gypsy_Big_Dummies_Guide.html, twgs.html] CONFIRMED | No cap in _handle_deploy_genesis (runner.py:1438). | Missing | S / Med |
| 1.13 Bubbles / tunnels / dead ends / black holes | Big Bang can build bubbles; tunnels, dead ends and sysop black holes (in, no out) shape defence. [Big_Bang.html, cabal glossary.html] CONFIRMED | universe.py makes no bubbles or black holes (the random graph has natural dead ends). | Missing | M / Low |
| 1.14 FedSpace ship limit per sector | "Ships per FedSpace sector" (sample 5); extra ships are towed out at Extern. [Gypsy_Big_Dummies_Guide.html, cabal glossary.html, Bible] CONFIRMED | Missing. | Missing | S / Low |
| 1.15 FedSpace fighter limit | Carrying too many fighters gets you towed out of FedSpace at Extern: Bible says more than 50, Gypsy says 99 or more. [Bible vs Gypsy_Big_Dummies_Guide.html] SOURCE-CONFLICT | Missing (attack in FedSpace is only penalised, see 5.20). | Missing | S / Low |
| 1.16 Fed protection rules (good and under 1000 exp) | Good traders (alignment 0+) with 999 exp or less are "fedsafe"; evil traders are never safe in FedSpace. [cabal glossary.html "Fedsafe", Bible] CONFIRMED | Missing: FedSpace attacks cost -200 alignment and emit FED_RESPONSE for everyone (runner.py _handle_attack:718). | Different | M / Med |
| 1.17 Nightly Extern clean-up of FedSpace | At Extern: NavHaz cleared in FedSpace, empty ships repossessed, armament violators towed, fighters in Major Space Lanes removed by the Feds. [cabal glossary.html "Extern", Gypsy_Big_Dummies_Guide.html] CONFIRMED | tick_day (runner.py:164) has no FedSpace clean-up. | Missing | S / Low |
| 1.18 Fed ports inside FedSpace | No source I read says sectors 2-10 hold normal ports. [none found] UNVERIFIED | universe.py puts a class-0 "Federal" port in sectors 2-10 with 60% chance; PORT_CLASS_TRADES[0] trades nothing so they look like decoration. Observation text fixed by class0-outpost-label (CLASS0_TERRA.md t25, `K.FED_OUTPOST_MODE`): seats see "Federal outpost (not Class 0)", not class 0. | Different | S / Low (ours-only; generation unchanged) |
| 1.19 Max fighters / mines per sector | Old v1.03d: 5000 fighters (30000 with a planet) and 99 mines per sector. v3 value not found. [Iago_War_Manual.txt] UNVERIFIED for v3 | No cap on sector fighters or mines (runner.py _handle_deploy_fighters:579, _handle_deploy_mines:619). | Missing | S / Low |
| 1.20 Picking fighters back up | You can pick up your own deployed fighters (and collect toll money) by visiting the sector. [Iago_War_Manual.txt, Bible] CONFIRMED | No action to recall fighters or mines (actions.py has only DEPLOY_*). | Missing | S / Med |

## 2. Ports and trading

| # / item | (a) Original rule, source, confidence | (b) Ours | (c) Status | (d) Size / priority |
|---|---|---|---|---|
| 2.1 Commodities | Three trade goods: Fuel Ore, Organics, Equipment (Colonists are cargo from Terra). [Bible, cabal formulas.html] CONFIRMED | Commodity enum FUEL_ORE/ORGANICS/EQUIPMENT (+COLONISTS cargo) in models.py. | Match | S / Low |
| 2.2 Port classes | Eight trading classes: 1 BBS, 2 BSB, 3 SBB, 4 SSB, 5 SBS, 6 BSS, 7 SSS, 8 BBB; 0 and 9 are special. [cabal twgs.html port-creation table, Bible] CONFIRMED | K.PORT_CLASS_TRADES numbers them differently (1 BSS, 6 BBS, 7 BBB, 8 StarDock) and has no SSS-type port. | Different | S / Low (bots that know public TW lore will misread) |
| 2.3 Price depends on stock and experience | Price = base curve by the port's "% of max" stock, scaled by the port's hidden max-change-in-cost (MCIC) and by your experience (improves to roughly 1000 exp). [cabal formulas.html, economy1/2.html, haggling.html] CONFIRMED | economy.py port_sell_price = base x (1.25 - 0.65 x stock) and port_buy_price = base x (1.45 - 0.70 x stock); port.experience[player] is stored (+0.05/trade) but never used. | Different | M / High |
| 2.4 Per-port MCIC and productivity | Each port/commodity has hidden productivity (units/day = 10 x value, max 32,760 MBBS or 65,530) and MCIC (-100..100). [cabal economy1.html, economy2.html] CONFIRMED | Missing; all ports share one curve; max stock is 3000 +/-, K.PORT_DEFAULT_MAX_STOCK. | Missing | M / Med |
| 2.5 Price scale vs ship cost | Sample trades show about 130 cr per Equipment at a good buy port and about 47 at a sell port, so profit per hold is large. [cabal economy2.html samples only] UNVERIFIED as a default | K base prices 18 / 25 / 36 (fuel/org/equip). Ours is roughly 3x smaller while some ships cost up to 10x more (see 3.x). | Different | S / High (needs one human economy decision, see conflicts) |
| 2.6 Haggling | Each MCIC has a fixed maximum counter-offer over the port's first offer (about 110-149%); beyond it the port "loses patience" and the turn is wasted. [cabal haggling.html] CONFIRMED | economy.py: acceptance chance = max(0, 1 - 4 x gap); a failed haggle settles at list price, so no downside. | Different | S / Med |
| 2.7 Turn cost of trading | Docking costs 1 turn; trades at that port then cost no extra turns. [Bible, DOCS "Evil or Red Cashing" screen text] CONFIRMED | K.TURN_COST trade = 3 per trade action (runner.py _handle_trade:394). | Different | S / High |
| 2.8 Port regeneration | TEDIT regen 1-200% per day (standard 5%, v3.05); a sample game used 1%/day. [TW2002 v3 revision history, cabal twgs.html] SOURCE-CONFLICT (5% vs 1% sample) | K.PORT_REGEN_PER_DAY = 0.05 but economy.regenerate_ports applies it x2 and drifts buy ports toward 30% of max, sell ports toward max. | Partial | S / Med |
| 2.9 Port stock model | Ports open at 0% and grow from there; a port the traders empty stays thin for days. [cabal economy1.html] CONFIRMED | Ports start at 35-95% of a randomised max (universe.py). | Different | S / Med |
| 2.10 Class 0 hold price | Hold cost = B x H + I x H x (H-1) / 2, with I = 20 and B a daily value (about 151-249). [cabal formulas.html] CONFIRMED | Flat base_hold_cost per ship type, 500-2000 per hold (constants.py SHIP_SPECS). | Different | S / Low |
| 2.11 Fighter and shield prices | Fighters cost about 160-239 and wobble on a long cycle (Hekate: 87 days; Iago for v1.03d: about 110-234 on a 30-day cycle); shields move opposite. [Misc_FigShieldPrices.txt, Misc_Hekatehints.txt, Iago_War_Manual.txt] SOURCE-CONFLICT | K.FIGHTER_COST = 50 flat; shields hard-coded 10 each in _handle_buy_equip. | Different | S / Med (cheap fighters inflate war) |
| 2.12 Rob a port | Needs alignment below -100; take credits up to experience x 3 (classic) or x 6 (MBBS); about 1 in 50 bust chance. [cabal formulas.html, glossary.html, DOCS "Evil or Red Cashing", Misc_megarob.txt] SOURCE-CONFLICT (x3 vs x6) | Missing (grep: no rob/steal/bust in engine). | Missing | M / Med |
| 2.13 Steal from a port | Take goods up to experience / 30 holds (classic) or /21 (MBBS); "same port twice = automatic bust" (fake bust); "Steal from Buy Port" is a setting. [cabal formulas.html, glossary.html] SOURCE-CONFLICT (30 vs 21) | Missing. | Missing | M / Med |
| 2.14 Bust penalty and clearing | A bust costs 10% experience plus lost holds; a port remembers only the last buster; busts clear daily (v3.05; MBBS daily). [cabal glossary.html, TW2002 v3 revision history] CONFIRMED | Missing. | Missing | S / Low |
| 2.15 Attack a port | At a port you may attack it; it fights back with a defensive rating and can be destroyed (-50 alignment, +50 exp). [EIS Tactical.html, classictw_docs_wiki Alignment.html] CONFIRMED | _handle_attack targets players/Ferrengi only; ports die only to atomic mines (_handle_atomic_detonation:657). | Partial | L / Low |
| 2.16 Build or upgrade a port | Players can build a StarPort (needs a planet for materials, subject to a port cap) and upgrade stock with credits (about 250 / 500 / 900 cr per unit of fuel / organics / equipment) for experience and alignment. [cabal twgs.html tables, EIS Tactical.html] UNVERIFIED (single table) | PORT_UPGRADE_MODE. Rules: docs/playtests/ports/PORT_UPGRADE_BUILD.md | In progress | M / Low |
| 2.17 Psychic probe / price peeking | Psychic probe tells you your offer vs the port's accepted price. [EIS HardwareMenu.html] CONFIRMED | Missing (also see 4.x). | Missing | S / Low |
| 2.18 StarDock trading | The StarDock does not trade commodities; it sells services. [EIS StarDockMenu.html] UNVERIFIED (inferred) | Sector 1 StarDock has no stock (universe.py). | Match | S / Low |

## 3. Ships

> Stats in rows 3.2-3.11 are listed as cost / max holds / max fighters / max shields / turns per warp / combat odds. Holds, fighters, shields and TPW agree across Bible_TWGS_edit_2007_Clme.htm, classictw_docs_wiki ship pages and Someguy_MBBS_manual.txt (CONFIRMED). Prices follow the Bible chart; OldBBS_2002SHIP.txt lists different (older, lower) base prices, so every price is SOURCE-CONFLICT. Ours = SHIP_SPECS in constants.py (holds there is the STARTING hold count).

| # / item | (a) Original rule, source, confidence | (b) Ours | (c) Status | (d) Size / priority |
|---|---|---|---|---|
| 3.1 Size of the ship roster | 16 player ships (Merchant Cruiser .. Interdictor Cruiser) plus Escape Pod; Ferrengi fly 3 NPC-only types. [Bible, MBBS, docs wiki] CONFIRMED | 10 ships in K.SHIP_SPECS; no pod ship, no Ferrengi ship types (label only). | Partial | M / Med |
| 3.2 Merchant Cruiser | 41,300 / 75 (starts 20) / 2,500 / 400 / TPW 3 / odds 1.0. [Bible, docs wiki, MBBS] stats CONFIRMED, price SOURCE-CONFLICT (OldBBS_2002SHIP 26,300) | 41,300 / start 20 holds (global cap 150) / 2,500 / 400 / TPW 3. | Partial | S / Low |
| 3.3 Scout Marauder | 15,950 / 25 / 250 (Bible, MBBS says 150) / 100 / TPW 2 / odds 2.0. [Bible, MBBS] SOURCE-CONFLICT on fighters and price (OldBBS 13,200) | 75,000 / 25 / 250 / 100 / TPW 2. | Different | S / Med (price about 4.7x) |
| 3.4 Missile Frigate | 100,800 / 60 / 5,000 / 400 / TPW 3 / odds 1.3; may carry photon missiles. [Bible, docs wiki, MBBS] stats CONFIRMED | 100,000 / start 40 holds / 5,000 / 400 / TPW 3, no photon restriction. | Partial | S / Low |
| 3.5 BattleShip | 88,500 / 80 / 10,000 / 750 / TPW 4 / odds 1.6. [Bible, docs wiki, MBBS] price SOURCE-CONFLICT (OldBBS 40,500) | 880,000 / 80 / 10,000 / 400 / TPW 3. | Different | S / Med |
| 3.6 Corporate FlagShip | 163,500 / 85 / 20,000 / 1,500 (Bible chart says 1,000; MBBS, docs wiki, OldBBS agree on 1,500) / TPW 3 / odds 1.2; TransWarp; CEO privilege. [Bible, MBBS, EIS CorporateMenu] price SOURCE-CONFLICT (OldBBS 71,000) | 650,000 / 85 / 20,000 / 1,500 / TPW 3, corp_only flag (membership, CEO-only not verified). | Partial | S / Low |
| 3.7 Colonial Transport | 63,600 / 250 / 200 / 500 / TPW 6 / odds 0.6. [Bible, docs wiki, MBBS] stats CONFIRMED | 63,000 / start 50 holds / 200 / 100 / TPW 3. | Different | S / Med (the big colony hauler is missing: 250 holds) |
| 3.8 CargoTran | 51,950 / 125 / 400 / 1,000 / TPW 4 / odds 0.8. [Bible, docs wiki, MBBS] stats CONFIRMED | 43,500 / 75 / 400 / 100 / TPW 3. | Different | S / Low |
| 3.9 Merchant Freighter | 33,400 / 65 / 300 / 500 / TPW 2 / odds 0.8 (best trading index). [Bible, docs wiki, MBBS, docs "Trading Index"] stats CONFIRMED | 350,000 / 65 / 2,500 / 750 / TPW 3. | Different | S / High (the classic trade ship costs 10x and moves slower) |
| 3.10 Havoc Gunstar | 79,000 / 50 / 10,000 / 3,000 / TPW 3 / odds 1.2; TransWarp range 16. [Bible, docs wiki, MBBS] stats CONFIRMED | 445,000 / start 65 holds / 10,000 / 3,000 / TPW 3, no TransWarp. | Partial | S / Low |
| 3.11 Imperial StarShip (ISS) | 339,000 / 150 / 50,000 / 2,000 / TPW 4 / odds 1.5; TransWarp + photon; needs Federal commission. [Bible, docs wiki, MBBS] price SOURCE-CONFLICT (OldBBS 128,600) | 4,400,000 / 150 / 50,000 / 5,000 / TPW 3, unique ship, min_alignment 2000. | Different | S / Med |
| 3.12 StarMaster, Constellation, T'Khasi Orion, Taurean Mule | Four mid-range ships (e.g. Taurean Mule 150 holds TPW 4; T'Khasi Orion TPW 2, 60 holds). [Bible, docs wiki, MBBS] CONFIRMED | Missing. | Missing | S / Low (data rows once caps exist) |
| 3.13 Tholian Sentinel | 47,500 / 50 / 2,500 / 4,000 / TPW 4; odds 4:1 when defending a corporate planet, 1:1 attacking; attackers must kill it before landing; cannot be fled from. [Bible, docs wiki Tholian_Sentinel] CONFIRMED | Missing. | Missing | M / Low |
| 3.14 Interdictor Cruiser | 539,000 / 40 / 100,000 / 4,000 / TPW 15; interdictor generator stops all other ships leaving its sector; cannot land on planets; cannot TransWarp. [Bible, docs wiki, MBBS] CONFIRMED | Missing (interdiction exists only as the L6 citadel, runner.py _try_interdict). | Missing | M / Low |
| 3.15 Per-ship capacity table | Each ship has its own max/min holds, max fighters per attack, mines, genesis, photon, TransWarp range and ship-transporter range (e.g. Merchant Cruiser 50 mines, 5 genesis; ISS 125 mines, 10 genesis). [Bible chart, MBBS page 2 of ship specs] CONFIRMED | Only max_fighters and max_shields enforced (runner.py _handle_buy_equip); holds capped at 150 for all; mines, genesis, photon, probes unlimited. | Partial | S / High |
| 3.16 Combat odds per ship | Ship "combat odds" scale damage (pod 0.6-0.7 to Battleship 1.6, Scout 2.0). [Bible, MBBS, Misc_shipodds.txt] CONFIRMED | No odds field in SHIP_SPECS; combat.py is symmetric. | Missing | S / High |
| 3.17 Buying a ship and trade-in | At the Shipyard you trade in the old ship (all extras go with it), or sell extra ships; you can also examine specs and change registration (about 5,000 in a sample TEDIT). [EIS ShipyardMenu.html, cabal twgs.html] CONFIRMED (value formula UNVERIFIED) | _handle_buy_ship (runner.py:1596): trade-in 25% of old base cost, fighters/shields/mines kept, cargo truncated; one ship per player. | Different | S / Med |
| 3.18 Owning several ships; selling; abandoning | Players can own more than one ship, leave ships in sectors (towable), sell extras at the Shipyard. [EIS ShipyardMenu, docs wiki Furbing, cabal glossary] CONFIRMED | Missing: Player.ship is a single object (models.py). | Missing | L / Med |
| 3.19 Capturing ships | Podless or empty ships can be captured (TEDIT setting Always/Never/Unoccupied); not Scouts or Escape Pods. [TWGS_v2_Revision_History.html, Bible] CONFIRMED | Missing. | Missing | M / Low |
| 3.20 Federal commission and ISS rule | Alignment 1000+ is automatically commissioned; at 500+ you ask the Police HQ and get boosted to 1000; ISS then allowed; falling below 0 in an ISS gets it repossessed by Captain Zyrain. [docs wiki Imperial_StarShip, Gypsy_Big_Dummies_Guide.html, Iago_War_Manual.txt, Bible] CONFIRMED | K.SHIP_SPECS imperial_starship min_alignment 2000 and unique:true; no commission step, no repossession. | Different | S / Med |

## 4. Ship equipment and hardware

> Hardware prices vary by sysop. Bible and one sample TEDIT (cabal twgs.html) disagree with each other and with ours, so no price gets a CONFIRMED tag. Ours = constants.py price constants and _handle_buy_equip. SSM is a red trading tactic (Sell-Steal-Move), covered by 2.12-2.14, not an item.

| # / item | (a) Original rule, source, confidence | (b) Ours | (c) Status | (d) Size / priority |
|---|---|---|---|---|
| 4.1 Genesis Torpedo | Creates a planet (random class), per-ship cap by ship (0-20), not in FedSpace, 5 planets per sector max; Bible price 25,000 vs sample TEDIT 80,000. [Bible, cabal twgs.html, Big_Bang.html] SOURCE-CONFLICT (price) | K.GENESIS_TORPEDO_COST 25,000; runner.py:1438 deploys it (4 turns, 3-hop rule from StarDock, seeds 2,500 colonists); no per-ship cap. | Partial | S / Med |
| 4.2 Atomic Detonator | Carried item (max 5 per ship); destroys a planet (kill the colonists first or it kills you), -50 alignment; can also act as a corbomite-like trap. [EIS HardwareMenu.html, Bible] CONFIRMED | "Atomic mines" (K.ATOMIC_MINE_COST 4,000) detonate at once on port/planet/fighters (runner.py:657); planet_destroy is a separate action. | Different | M / Low |
| 4.3 Marker beacons | Leave a message beacon in a sector; two in one sector both explode; density value 1. [EIS HardwareMenu.html, Bible] CONFIRMED | Missing. | Missing | S / Low |
| 4.4 Corbomite device | Up to 1,500 per ship; undetectable; damages the ship that destroys you. [EIS HardwareMenu.html, Bible] CONFIRMED | Missing. | Missing | M / Med |
| 4.5 Cloaking device | Max 5 per ship, hides the ship (density 0 plus an anomaly) so it cannot be attacked; can fail (3% setting; unsafe after about 24 hours); a photon missile decloaks. [Bible, EIS HardwareMenu.html, Gypsy_Big_Dummies_Guide.html, Iago] CONFIRMED | Missing. | Missing | M / Med |
| 4.6 Ether probe | Max 25 per ship; flies a multi-sector path anywhere, maps it into your computer, destroyed by any hostile fighters; owner is told. [Iago_War_Manual.txt, EIS HardwareMenu.html, Bible] CONFIRMED | K.ETHER_PROBE_COST 5,000; _handle_probe (runner.py:2127) scans one sector for 1 turn, +3 xp, never destroyed, no path. | Different | M / Med |
| 4.7 Mine disruptor | Max 10 per ship, each clears up to 12 mines in an adjacent sector. [EIS HardwareMenu.html, Bible] CONFIRMED | Missing. | Missing | M / Med |
| 4.8 Armid mines (item) | Bought in bulk at the Hardware Emporium; 99 per sector in old versions; unit price sysop-set (sample 4,000). [cabal twgs.html, Iago] UNVERIFIED defaults | K.ARMID_MINE_COST 100, no per-ship cap. | Different | S / Low |
| 4.9 Limpet mines | Attach to a ship you hit; only one attached at a time; you can query where it is; removable at the StarDock for a fee (sample 1,250). [Bible, cabal twgs.html] CONFIRMED | Attach and query exist (runner.py _attach_limpet, _handle_query_limpets:2101); no removal service. | Partial | S / Low |
| 4.10 Photon missile | Only Missile Frigate (10 carried) or ISS (5) can use it; fired at an adjacent sector, it disables mines, sector fighters, quasar, CCC and interdictor there for a short wave; blows up on contact with offensive fighters/mines if carried; a FedSpace setting. [Bible, REV v3.0x, S1_planet_handbook_v1.01.html] CONFIRMED | _handle_photon_missile (runner.py:2063): any ship, same-sector player target, sets that player's photon_disabled_ticks; PHOTON_DURATION_TICKS 1; no effect on mines/fighters. | Different | M / Med |
| 4.11 Density scanner | Hardware item; 0 turns; shows a number per adjacent sector (5 per fighter, 10 per mine, 40 manned ship, 100 port, 500 planet, etc.). [Bible, Gypsy_Big_Dummies_Guide.html] CONFIRMED | scan tier "density" in _handle_scan (runner.py:482): counts two hops out, free to all, 1 turn, no hardware. | Different | M / High |
| 4.12 Holographic scanner | Hardware item; costs 1 turn; reveals adjacent sectors in detail; Havoc Gunstar has only the holo. [Bible, Gypsy_Big_Dummies_Guide.html] CONFIRMED | "holo" tier gives 1-hop full intel incl. port stock and mines, no hardware needed. | Different | S / Med |
| 4.13 Planet scanner | Shows owner and fighters of planets that have no shields. [EIS HardwareMenu.html] CONFIRMED | Missing; planet fighters and shields are always visible (observation.py ~616, ~657). | Missing | S / Med |
| 4.14 Psychic probe | Tells you how your price compares to what the port will accept. [EIS HardwareMenu.html] CONFIRMED | Missing. | Missing | S / Low |
| 4.15 TransWarp drive (ship) | Type 1 (self) and Type 2 (tow); only Havoc, CFS, ISS; needs a friendly fighter in the target (else blind warp, risk of ending in a pod); uses fuel from holds (3 per sector is modern-manual only); commissioned blues may warp to FedSpace. [Bible, Gypsy_Big_Dummies_Guide.html, cabal glossary.html] CONFIRMED (fuel number UNVERIFIED) | Missing for ships. Only planet_transwarp (planets, runner.py:2639). | Missing | M / Med |
| 4.16 Ship transporter (ship to ship) | Each ship has a transporter range (e.g. 5 sectors) to beam into another of your ships. [Bible chart, Iago] CONFIRMED | Missing for ships (planet_transport only). | Missing | M / Low |
| 4.17 Capacity limits on all items | Cloaks max 5, probes 25, atomic 5, disruptors 10, beacons, photons per ship. [EIS HardwareMenu.html, Bible] CONFIRMED | No caps (see 3.15). | Missing | S / Med |

## 5. Combat (not planets)

> Planet landing combat (quasar, 20:1 shields, 2:1 reaction fighters, 3:1 defenders) is already built and compared in docs\plans\planetary-warfare-comparison.md, so it is not repeated. Odds table: sector fighters 1:1 (all modes), planet shields 20:1, planet offensive 2:1, planet defensive 3:1.

| # / item | (a) Original rule, source, confidence | (b) Ours | (c) Status | (d) Size / priority |
|---|---|---|---|---|
| 5.1 Order of events entering a hostile sector | NavHaz, then limpet, then armid mines, then sector quasar, then fighters, then the "avoid sector?" prompt. [cabal formulas.html, S1_planet_handbook_v1.01.html] CONFIRMED | _apply_sector_hazards (runner.py:256): mines then limpet then fighters; sector quasar fires later in _handle_warp; no NavHaz, no avoid prompt. | Partial | M / Med |
| 5.2 NavHaz | Each 1% of navigational hazard does 10 damage with chance equal to the %; cleared in FedSpace at Extern. [cabal glossary.html "Nav Hazz", cabal formulas.html] CONFIRMED | Sector.nav_hazard field exists (models.py:310) but nothing reads it. | Missing | S / Low |
| 5.3 Armid mine damage | When a mined sector is entered, half of the mines (rounded down) detonate; Bible says 20 damage each; no v3 per-mine number found. [cabal formulas.html, Bible] SOURCE-CONFLICT on damage | K.ARMID_DAMAGE 100 per hit; hits = min(count, random 1..10). | Different | S / Med |
| 5.4 Offensive sector fighters | Attack at 1:1, sending up to 1.25 times the fighters needed to destroy you (one place says 1.25 times your max figs+shields); the rest wait for the next entry. [cabal formulas.html lines 1045/1186, Misc_offensive_pod.txt] SOURCE-CONFLICT (inside formulas.html) | combat.py _resolve_fighter_sector_combat: one exchange, losses = other side x random 0.8-1.1; no wave cap. | Different | M / High |
| 5.5 Defensive sector fighters | Block entry: you are asked to attack, retreat or surrender; they do not shoot first. [Iago_War_Manual.txt, cabal formulas.html] CONFIRMED | Defensive mode does nothing at all (runner.py _apply_sector_hazards). | Missing | M / High |
| 5.6 Toll fighters | You pay 5 credits per fighter to stay or pass, or retreat, or attack; collect by visiting the sector. [Iago_War_Manual.txt, cabal formulas.html] CONFIRMED | Toll = min(credits, max(10, min(10000, count))) charged automatically (about 1 cr/fighter). | Different | S / Med |
| 5.7 Ship vs ship attack | Attacker picks how many fighters (capped per ship), ship combat odds apply, shields absorb with fighters, the defender may warp away if the attacker is much stronger. [EIS Tactical.html, Bible chart] CONFIRMED (exact formula UNVERIFIED) | _handle_attack (runner.py:718) 5 turns, no fighter-count choice; combat.py _resolve_ship_combat: up to 3 rounds of fighters x random 0.8-1.2 each side. | Different | L / High |
| 5.8 Max fighters per attack | Each ship has a cap per attack (e.g. Merchant Cruiser 750, Battleship 3,000, ISS 10,000). [Bible chart] CONFIRMED | Missing. | Missing | S / Med |
| 5.9 Flee / retreat rule | A defender flees if the attacker's fighters exceed (defender fighters + shields) x 1.25; one hop to a sector without enemy fighters; Tholian never; interdictor blocks; no hazards fire; v3.11.54 added a one-turn penalty. [cabal fleeing.html, cabal glossary.html, cabal formulas.html] CONFIRMED | Missing (only Ferrengi flee). | Missing | M / Med |
| 5.10 No retreat cases | Cannot retreat if you arrived by one-way warp or TransWarp, or if a planetary interdictor holds the sector (IC does not block). [REV v3.01-3.02, cabal fleeing.html] CONFIRMED | Missing. | Missing | S / Low |
| 5.11 Surrender | You may surrender to defensive or toll fighters instead of fighting. [Iago_War_Manual.txt] CONFIRMED | Missing. | Missing | S / Low |
| 5.12 Escape pod on death | A destroyed ship becomes an Escape Pod (TPW 6, odds 0.6-0.7, 50 shields) that flees along a safe path 3-20 sectors away; self-inflicted deaths use the previous sector. [cabal pods.html, MBBS, Bible] CONFIRMED | Missing: _destroy_ship (combat.py) ejects to StarDock with a free Merchant Cruiser. | Different | M / High |
| 5.13 Pod limit and elimination | Two pods per day; the third kills you until midnight (tournament mode has lockout settings). [REV v3.05, S1_planet_handbook_v1.01.html, cabal glossary.html] CONFIRMED | K.MAX_DEATHS_BEFORE_ELIM 3: permanent elimination after 3 deaths. | Different | S / Med |
| 5.14 Exp and alignment cost of dying | Being podded costs 10% exp and no alignment; self-destruct costs 50% of both. [cabal pods.html] CONFIRMED | combat.py _destroy_ship: credits x0.75, deaths +1, no exp/alignment change. | Different | S / Med |
| 5.15 Salvage and furbing | Winner may get salvage; holds of a destroyed ship transfer to the attacker (furbing). [Gypsy_Big_Dummies_Guide.html, docs wiki Furbing] CONFIRMED | Cargo is just cleared on death. | Missing | M / Low |
| 5.17 Corbomite and mine disruptor in combat | Corbomite hurts the killer; disruptors clear mines before entering. [EIS HardwareMenu.html] CONFIRMED | Missing (rows 4.4, 4.7). | Missing | M / Med |
| 5.18 Photon interaction | Photon disables sector mines/fighters/quasar so a following ship can enter; also decloaks. [S1_planet_handbook_v1.01.html, Gypsy_Big_Dummies_Guide.html] CONFIRMED | Photon only disables the target ship (runner.py:2063) and damps planets (_mark_photon_planet_damp). | Partial | M / Med |
| 5.19 Planet landing combat | Quasar x2, shields 20:1, reaction wave 2:1, defenders 3:1. [S1_planet_handbook_v1.01.html, cabal formulas.html] CONFIRMED | Built (runner.py _planet_odds_fight:811, _handle_land_planet:902). | Match | S / Low |
| 5.20 Combat in FedSpace | Attacking in FedSpace summons Captain Zyrain (kills attacker) for good players under 1000 exp; evil traders are not protected. [Bible, docs wiki Imperial_StarShip] UNVERIFIED (detail) | _handle_attack: FED_RESPONSE event and -200 alignment; photon in FedSpace -100 (runner.py:733). | Partial | M / Med |

## 6. Planets (remaining gaps only; shipped work B1-E3 is not re-listed)

> Already built and not repeated: citadel L1-L6 effects, treasury and 2% interest, military reaction, planet shields, quasar sector/atmosphere, planet transwarp and transporter, planet_destroy, land/odds combat, corp-planet dissolve rules. See docs\plans\planetary-warfare-comparison.md (note: its "missing" list is stale) and docs\playtests\planetary-warfare\SUMMARY.md.

| # / item | (a) Original rule, source, confidence | (b) Ours | (c) Status | (d) Size / priority |
|---|---|---|---|---|
| 6.1 Scanner fog for planet fighters and shields | Planet owner and fighters are only visible through a planet scanner (and only if unshielded) or by landing. [EIS HardwareMenu.html] CONFIRMED | observation.py (~616, ~657) shows every planet's fighters and shields to everyone; other ships' fighters also visible (~495). | Missing | S / Med |
| 6.2 Class-table citadel costs | Citadel levels cost colonists, ore, organics and equipment that depend on planet class (2-7 weeks to L6). [S1_planet_handbook_v1.01.html section VII] CONFIRMED | K.CITADEL_CLASS_COSTS is coded but K.CITADEL_COST_MODE = "credits" keeps it dark. | Partial | S / Med |
| 6.3 Max colonists, stock caps and bell-curve production | Each class has max colonists (M 30,000, O 200,000 ...), max stock per good and production peaking at half of max population; colonists grow below 50% and die off above. [S1_planet_handbook_v1.01.html] CONFIRMED | planets.py _advance_planets: flat 5% growth when organics stock > 0, no max population, no stock caps, production = workers x coefficient/100 (M 3/5/3). | Different | M / High |
| 6.4 Production ratios by class | Colonists needed per unit differ by class (e.g. Class M 3/7/13, O 20/2/100, H 1/-/500). [S1_planet_handbook_v1.01.html] CONFIRMED | PLANET_PROD_COEFF (planets.py:26) is a different matrix (units per 100 colonists). | Different | S / Med |
| 6.5 Genesis starting population | A new planet starts with no colonists and usually no goods (sysop may add). [S1_planet_handbook_v1.01.html] CONFIRMED | K.GENESIS_SEED_COLONISTS 2,500 plus 25 organics (runner.py:1489-1503). | Different | S / Med |
| 6.6 Planets per sector and collisions | Max 5 per sector; Bible mentions nightly "unstable planetary mass" collisions. [Gypsy_Big_Dummies_Guide.html, Bible] cap CONFIRMED, collisions UNVERIFIED | No cap (runner.py:1438). | Missing | S / Med |
| 6.7 Genesis class choice | Planet class is random and weighted by how crowded the sector is. [Misc_JPhints_JohnPritchett.txt] UNVERIFIED (one source) | K.PLANET_CLASS_WEIGHTS fixed weights. | Partial | S / Low |
| 6.8 Planetary trading | A mobile planet parked under a port can sell its goods to that port at a fixed price (MBBS 100%). [cabal glossary.html, REV v3.0x] CONFIRMED | Built in slice 54 planetary-trading-v1: `planet_trade` (port menu <N>), behind `K.PLANET_TRADE_MODE`; see docs/playtests/planets/PLANETARY_TRADING.md. | Done (TWGS curve default, `PLANET_TRADE_PRICING="mbbs100"` for MBBS 100%) | M / Med |
| 6.9 Ship exchange and overnight parking in a citadel | Citadel lets you park a ship overnight and swap into another of your ships; CEO ships are never swappable. [Bible, EIS CitadelMenu] CONFIRMED | Missing (single-ship model). | Missing | M / Low |
| 6.10 Planet killer rules | Atomic detonator destroys a planet after its colonists are dead, -50 alignment; killing a trader on a planet gives +0.17 x their exp +50, -0.33 x their alignment -1. [Bible, cabal formulas.html] SOURCE-CONFLICT (-50 vs -1) | planet_destroy (runner.py:2876) zeroes colonists then removes; alignment -50. | Partial | S / Low |
| 6.11 Corp planet quirks | On corp disband planets in the CEO's sector go to the CEO, others become Rogue; Tholian Sentinel defends corp planets at 4:1. [REV v3.06, docs wiki Tholian_Sentinel] CONFIRMED | Every living owner keeps planets (deliberate difference, runner.py _release_dissolved_corp_planets); no Sentinel. | Different | S / Low |
| 6.12 Planet-based exp and alignment | Creating a planet gives +25 exp and +10 alignment; planet busting loops give 75 exp per cycle. [docs wiki Alignment, cabal glossary.html] CONFIRMED | XP_AWARDS deploy_genesis 100, claim_planet 75; no alignment change. | Different | S / Low |
| 6.13 Planet value dividend | Not in the original. | planets.py _pay_planet_value_tax pays owners a credit dividend (K.PLANET_VALUE_TAX_RATE). | Different | S / Low (ours-only; decide keep or remove) |
| 6.14 Stale citadel perk text | n/a | K.CITADEL_PERK still says L2 Combat Control Computer and L5 Planetary shields are "not yet in this game". | Different | S / Low |

## 7. Citadels (gaps only)

| # / item | (a) Original rule, source, confidence | (b) Ours | (c) Status | (d) Size / priority |
|---|---|---|---|---|
| 7.2 Build time | 2 to 7 weeks to L6 depending on class. [S1_planet_handbook_v1.01.html] CONFIRMED | K.CITADEL_BUILD_TIME_SCALE = 0.25 (deliberate for a 30-day match). | Different | S / Low |
| 7.3 Free fighters/shields on completion | None in the original. [S1_planet_handbook_v1.01.html] CONFIRMED | Gift constants are 0 (no-op). | Match | S / Low |
| 7.4 Atmospheric quasar damage factor | TWGS Classic uses x0.5, MBBS uses x2. [cabal formulas.html vs S1_planet_handbook] SOURCE-CONFLICT | Ours picked MBBS x2 (recorded decision in the planetary docs). | Match | S / Low |
| 7.5 Treasury cap | 999,999,999,999,999. [S1_planet_handbook_v1.01.html] CONFIRMED | K.PLANET_TREASURY_CAP 10,000,000. | Different | S / Low |

## 8. Aliens, NPCs, bad guys

> I searched every .html/.htm/.txt/.md file in the reference folder for "Mad Mac", "Lenny" and a Cabal NPC and found none of them (UNVERIFIED, nothing to compare; the twclone source files were not searched). The only named pirate seen is "Blackbane" in a v3.34 note, after 3.11. Federation ships are covered here and again in 11.

| # / item | (a) Original rule, source, confidence | (b) Ours | (c) Status | (d) Size / priority |
|---|---|---|---|---|
| 8.1 Ferrengi ships | Three types: Assault Trader (TPW 2, 3,000 figs, 200 shields), Battle Cruiser (TPW 3, 8,000, 800), Dreadnought (TPW 4, 15,000, 1,000, 50 mines, 1 photon). [Bible, docs wiki Ferrengi pages] CONFIRMED (odds: FERRSPEC vs Bible differ) | Ferrengi are a dataclass with fighters 100+300 x aggression and shields 50 x aggression; ship_class label is battleship or missile_frigate. | Different | M / Med |
| 8.2 Ferrengi behaviour | They roam on their own, steal and extort, demand tribute, usually accept surrender, hold grudges and band together. [TWFAQ_FERRSPEC_ferrengi.txt, Bible, EIS GeneralUpdated.html] CONFIRMED | Hunt armed players by an aggression threshold, flee if the victim has 1.5x their fighters (K.FERRENGI_*); no tribute, surrender or grudges. | Different | M / Med |
| 8.3 Ferrengi numbers and pace | TEDIT: Ferrengi move chance about 1 in 20 per 30 s, 20% regen; v3 NPCs act in real time. [cabal twgs.html, EIS GeneralUpdated.html] CONFIRMED | Spawn 3/day (initial 4), move prob 0.6/day, strength ramp over 200 days, grace of 5 days. | Different | S / Low |
| 8.4 Ferrengi kill rewards | Alignment gain plus Fed bounty credits. [Bible, Iago_War_Manual.txt] CONFIRMED | Bounty 1000 x aggression, +10 alignment, xp 20 x aggression. | Partial | S / Low |
| 8.6 Alien traders (non-Ferrengi) | Game-run "aliens" with exp and alignment who trade and fight; killing them changes your alignment (half their exp if opposite, quarter if same). [Bible, Gypsy_Big_Dummies_Guide.html] CONFIRMED (exp split UNVERIFIED, one source) | Missing. | Missing | M / Med |
| 8.7 Federal ships | Admiral Nelson (density 462), Captain Zyrain (489), Fleet Admiral Clausewitz (512) patrol FedSpace; they cannot enter sectors holding player fighters; Zyrain kills evil ISS and attackers in FedSpace. [Bible, Iago_War_Manual.txt, docs wiki Imperial_StarShip] CONFIRMED | Missing (only an event for attacks in FedSpace). | Missing | L / Med |
| 8.8 NPCs and player fighters | Aliens and Feds cannot move into fighter sectors; Ferrengi ignore fighters but hit mines (old version). [Iago_War_Manual.txt] UNVERIFIED for v3 | Not checked in code. | Missing | S / Low |
| 8.9 Gold-mode aliens | Gold lets sysops add protective, banding, grudge aliens (Gold only). [TWGS_v2_Revision_History.html] UNVERIFIED | Missing | Missing | M / Low |

## 9. Players: turns, experience, alignment, ranks

> Bank, Police HQ, bounties, tavern, underground and tax are listed in category 11.

| # / item | (a) Original rule, source, confidence | (b) Ours | (c) Status | (d) Size / priority |
|---|---|---|---|---|
| 9.1 Starting package | V-screen sample: 30 fighters, 20 holds, credits/turns sysop-set; classic is 250 turns per day. [Gypsy_Big_Dummies_Guide.html, cabal glossary.html] SOURCE-CONFLICT on turns | K.STARTING_CREDITS 20,000, fighters 20, holds 20, turns 1000, ship Merchant Cruiser. | Partial | S / Low |
| 9.2 Ways to gain experience | Trade, dock first time at a port (+1), kill (formulas below), create planets (+25), destroy ports (+50), midnight login (+1). [docs wiki Alignment, cabal glossary.html, Bible] CONFIRMED | K.XP_AWARDS: trade 1, warp 1, scan 1, probe 3, kill_player 200, kill_ferr 20 x aggression, genesis 100, claim 75, citadel 50 x level, alliance 25. | Different | S / Med |
| 9.3 Experience from PvP kills | MBBS: exp = your fighters lost / 15 (blue vs red), /35 (same colour), /25 (neutral); pod or self-destruct kill gives 10% of victim exp. [cabal formulas.html, cabal pods.html] SOURCE-CONFLICT (MBBS vs Gold/classic variants) | Flat 200 xp. | Different | S / Med |
| 9.4 Alignment from kills | Alignment moves by your fighters lost x enemy alignment x 0.2 / 1000 (MBBS) or alignment/5000 x fighters lost (Gold/classic). [cabal formulas.html] SOURCE-CONFLICT | Missing (only fixed penalties: atomic -50, FedSpace attack -200, photon in FedSpace -100, Ferrengi kill +10). | Missing | M / Med |
| 9.5 Other alignment sources | Post rewards (+1 per 1000 cr), jettison colonists (-1 each, max 250/day), create planet +10, destroy port -50, upgrade ports, pay taxes, underground -4 per 1000 posted. [docs wiki Alignment, Gypsy_Big_Dummies_Guide.html] CONFIRMED | Tax alignment is `GALACTIC_BANK_TAX.md` gb21 (floor of the tax / 1500). The other sources here are still missing. | Partial | M / Med |
| 9.6 Rank titles | 22 good and 22 evil titles with doubling exp thresholds (2 up to 4,194,304). [Gypsy_Big_Dummies_Guide.html] CONFIRMED | K.RANK_TABLE 9 ranks from 0 to 250,000 and K.ALIGNMENT_TIERS (victory.py labels). | Different | S / Low |
| 9.7 Good vs evil perks | Good: ISS, FedSpace protection under 1000 exp, TransWarp into FedSpace; evil: rob/steal, underground, no Fed safety. [cabal corps.html, Gypsy_Big_Dummies_Guide.html] CONFIRMED | Missing as systems (alignment is mostly cosmetic except ISS). | Missing | L / Med |
| 9.8 Experience-based pricing/rob limits | Your exp sets how well you haggle (to 1000) and how much you can rob/steal. [cabal formulas.html, haggling.html] CONFIRMED | port.experience is tracked (economy.py) but unused; Player.experience only drives ranks and victory. | Missing | S / Med |
| 9.9 Mixed-alignment corp exp loss | Mixed corps lose exp at Extern (1/4 of the least extreme alignment). [Misc_Alignment_to_exp_changes_twgs.txt] UNVERIFIED | `docs/playtests/corps/CORP_RULES.md` cr9. TWGS reading is the highest good alignment / 4. | Built | S / Low |

## 10. Corporations

| # / item | (a) Original rule, source, confidence | (b) Ours | (c) Status | (d) Size / priority |
|---|---|---|---|---|
| 10.1 Create a corporation | Any trader can file a charter and becomes CEO (cost not found). [EIS CorporateMenu.html] UNVERIFIED (cost) | `CORP_RULES.md` cr1-cr2. Anywhere, cost 0. Legacy stays StarDock and 500,000. | Built | S / Low |
| 10.2 Joining | Needs CEO approval and a corporate security pass (password). [EIS CorporateMenu.html] CONFIRMED | `CORP_RULES.md` cr3-cr6. Password, one wrong guess a day. | Built | S / Low |
| 10.3 Same-alignment rule | Joiners must match the CEO's side; if your side flips you are ousted. [EIS CorporateMenu.html] CONFIRMED | `CORP_RULES.md` cr8. TWGS mixed is the default; same_side ousts. | Built | S / Low |
| 10.4 Members limit | Sample TEDIT: 5 traders per corp (setting). [Gypsy_Big_Dummies_Guide.html] CONFIRMED (a setting) | `CORP_RULES.md` cr7. `CORP_MAX_MEMBERS` 5. | Built | S / Low |
| 10.5 Drop (kick) a member | CEO may drop a member, who keeps assets on their ship. [EIS CorporateMenu.html] CONFIRMED | `CORP_RULES.md` cr14. | Built | S / Low |
| 10.6 Transfers between members | Credits, fighters, mines and shields can be transferred between members in the same sector. [EIS CorporateMenu.html] CONFIRMED | `CORP_RULES.md` cr16. The treasury is off (cr26). | Built | M / Med |
| 10.7 Corp assets and member locations | Corp menu lists planets (pop, production, stock, fighters, citadel, shields, credits) and members' sector, fighters, shields, mines, credits. [EIS CorporateMenu.html] CONFIRMED | `CORP_RULES.md` cr22-cr24. | Built | S / Low |
| 10.8 Corp memo | CEO or members send a memo to all members. [EIS CorporateMenu.html] CONFIRMED | `CORP_RULES.md` cr25. Any member. | Match | S / Low |
| 10.9 Corporate vs personal fighters, mines, ships | Fighters and mines may be personal or corporate; corporate ships are password protected; corp members cross-use. [Bible, EIS CorporateMenu.html] CONFIRMED | `CORP_RULES.md` cr17-cr21. Ships stay in `CORP_SHIPS_FURB.md`. | Built | M / Med |
| 10.10 CEO leaves or corp ends | If the CEO leaves the corp dissolves and corporate fighters go rogue; v3.06 rules for planets/ships. [EIS CorporateMenu.html, REV v3.06] CONFIRMED | `CORP_RULES.md` cr11-cr13. Planets stay owner_keeps (conflict 18). | Built | S / Low |
| 10.11 Corporation rankings | Corps ranked by exp with a combined alignment. [EIS CorporateMenu.html] CONFIRMED | `CORP_RULES.md` cr24. | Built | S / Low |
| 10.12 Alliances | Not in the original (only corps). | propose/accept/break alliance actions, 25 xp. | Different | S / Low (ours-only; keep or remove) |

## 11. Special locations and events

> "Lenny's" does not appear in any .html/.htm/.txt/.md file in the reference folder (UNVERIFIED); the closest match is the Lost Traders Tavern at the StarDock. Big Bang (universe creation) is covered by 1.1-1.13.

| # / item | (a) Original rule, source, confidence | (b) Ours | (c) Status | (d) Size / priority |
|---|---|---|---|---|
| 11.1 Hardware Emporium | Sells armid/limpet mines, atomic detonators, genesis, photons, ether probes, cloaks, disruptors, beacons, scanners, psychic probe, transporter, TransWarp drives, limpet removal. [EIS HardwareMenu.html] CONFIRMED | _handle_buy_equip (runner.py:1647) sells fighters, shields, 3 mine kinds, photons, probes, genesis, holds, colonists. Missing the rest (rows 4.3-4.17). | Partial | M / Med |
| 11.2 Shipyard | Buy, sell, examine ships; change registration. [EIS ShipyardMenu.html] CONFIRMED | Buy only (see 3.17). | Partial | M / Med |
| 11.3 Police HQ and Federal commission | Apply for commission at alignment 500+, claim bounty rewards, see ten most wanted, post rewards (about 1,000 cr per alignment point). [EIS PoliceMenu.html, Gypsy_Big_Dummies_Guide.html] CONFIRMED | Missing. | Missing | M / Med |
| 11.4 Bounties on players | Bounties are posted at Police HQ (good) or Underground (evil); collect on kill. [EIS PoliceMenu.html, Iago_War_Manual.txt] CONFIRMED | Only Ferrengi bounty (1000 x aggression); no player bounties. | Missing | M / Med |
| 11.5 Galactic Bank | Personal account, max about 500,000, transfers to other players, no interest, protects cash from the good-trader tax. [EIS BankMenu.html, S1_planet_handbook_v1.01.html] CONFIRMED | `docs/playtests/fedspace/GALACTIC_BANK_TAX.md` (galactic-bank-tax-v1). TWGS cap 500,000. | Built | S / Low |
| 11.6 Good-trader daily tax | Good traders carrying more than about 50,000 credits are taxed 10% once per day on first login. [Bible, EIS GeneralUpdated.html] UNVERIFIED (the 10% / 50,000 numbers are Bible-only; that a daily tax exists is in EIS GeneralUpdated.html) | `GALACTIC_BANK_TAX.md`: TWGS reading, over 100,000 at 5%, alignment 0 or more. | Built | S / Low |
| 11.7 Underground (Mafia) | Reachable at alignment under 200; sells illegal goods, changes names, lowers alignment, posts hits; wrong password too often is fatal. [cabal glossary.html, Bible] CONFIRMED | Missing. | Missing | M / Low |
| 11.8 Lost Traders Tavern | Announcements (100 cr), bar and graffiti, eavesdropping, Grimy Trader tracing, Tri-Cron gambling. [EIS TavernMenu.html] CONFIRMED | Missing. | Missing | M / Low |
| 11.9 Fed attack on evil players | Zyrain repossesses an evil ISS; Feds hunt evil players who enter FedSpace. [docs wiki Imperial_StarShip, Iago_War_Manual.txt] CONFIRMED | Missing. | Missing | M / Med |
| 11.10 StarDock/Class 0 defence | Special ports have huge defence (about 248k fighters to kill with a stock Interdictor) and are rebuilt by the Feds after the radiation clears. [cabal formulas.html lines 1854-1859 for the fighter numbers; REV v3.10 says the Feds rebuild StarDock and Class 0 ports after radiation clears, stronger in Gold] UNVERIFIED (numbers are one author's estimate) | StarDock cannot be attacked or destroyed. | Missing | M / Low |
| 11.11 Big Bang options | Sysop options at creation: port %, planet %, bubbles, one-way %, course length, Gold options. [Big_Bang.html] CONFIRMED | universe.py takes seed, size, avg warps, one-way fraction, planet probability; no bubbles or special-port options. | Partial | M / Low |

## 12. Game flow

| # / item | (a) Original rule, source, confidence | (b) Ours | (c) Status | (d) Size / priority |
|---|---|---|---|---|
| 12.1 Turns per day | Classic Big Bang: 250 turns/day (cabal glossary); sample live game 750; Cabal income table assumes a 1000-turn game. [cabal glossary.html, Gypsy_Big_Dummies_Guide.html, cabal corps.html] SOURCE-CONFLICT | K.STARTING_TURNS_PER_DAY 1000 (cli --turns-per-day overrides). | Match | S / Low |
| 12.2 Turn recovery | v3 gives back spent turns every hour (pro-rated), not only at midnight. [EIS GeneralUpdated.html, REV v3.00] CONFIRMED | tick_day (runner.py:164) resets turns once per day; day advances when every bot is out of turns (server/runner.py:637-658). | Different | S / Low (suits a turn-based match; a human decision) |
| 12.3 Real-time movement and attacks | v3 ships move and attack at a speed set by ship size; fast ships escape slow ones. [EIS GeneralUpdated.html] CONFIRMED | Fully turn-based, no travel delay. | Different | L / Low (deliberate) |
| 12.4 Nightly Extern | Port regen, planet production, bust clearing, FedSpace clean-up, tows, corp/player timeouts, Class 0 price change, dead players return. [cabal glossary.html, EIS GeneralUpdated.html] CONFIRMED | tick_day does regen, Ferrengi, planets, citadels, treasury, victory; no busts, tows, FedSpace clean-up, price cycle, respawn. | Partial | M / Med |
| 12.5 Game end | No built-in win; sysop sets duration or tournament rules; scores are exp/alignment ranks. [Bible, EIS TradeWars.html] CONFIRMED (UNVERIFIED if any other end exists) | victory.py: last alive, 100M-credit economic win (scaled), or day-cap net worth. | Different | S / Low (deliberate; keep) |
| 12.6 Tournament mode | Kill/pod thresholds with lockout and max times blown up. [TWGS_v2_Revision_History.html] CONFIRMED | K.MAX_DEATHS_BEFORE_ELIM 3 only. | Partial | S / Low |
| 12.7 Daily stats screens | Real-time game stats (V screen): ports, planets, traders, aliens, fighters and mines in use. [Gypsy_Big_Dummies_Guide.html, EIS GeneralUpdated.html] CONFIRMED | Not verified (observation.py only grepped). | Missing | S / Low |

## 13. Messaging, transmissions, probes

| # / item | (a) Original rule, source, confidence | (b) Ours | (c) Status | (d) Size / priority |
|---|---|---|---|---|
| 13.1 Direct messages | Hail one trader (online only); messages last about 10 seconds; mail for offline players. [Bible, EIS GeneralUpdated.html] CONFIRMED | HAIL and BROADCAST into inbox, 0 turns. | Partial | S / Low |
| 13.2 Radio channels | Subspace radio channels 0-60000 for corp chat. [Bible, EIS GeneralUpdated.html] CONFIRMED | Missing (corp_memo is one-way). | Missing | S / Low |
| 13.3 Mail | "New Mail" notification, stored mail. [EIS GeneralUpdated.html] CONFIRMED | Inbox only. | Partial | S / Low |
| 13.4 Fighter and combat reports | Daily log and fighter reports tell owners what hit their sectors. [Bible] UNVERIFIED | Events exist; whether owners are told was not verified. | Partial | S / Med |
| 13.5 Ether probe report | Probe returns a sector list and owner is told whose probe a fighter killed. [Iago_War_Manual.txt, Bible] CONFIRMED | Probe returns one sector, never destroyed. | Different | S / Low |
| 13.6 FedComm | Federation broadcasts (e.g. "don't deploy in MSL"). [Gypsy_Big_Dummies_Guide.html] CONFIRMED | Missing. | Missing | S / Low |

## 14. Anything else notable

| # / item | (a) Original rule, source, confidence | (b) Ours | (c) Status | (d) Size / priority |
|---|---|---|---|---|
| 14.1 Computer menu helpers | Avoids, backtrack, NavPoints, quick stats, Find Route, CIM mapping. [EIS GeneralNew.html, Navigate, cabal glossary.html] CONFIRMED | PLOT_COURSE and known_* maps only. | Partial | M / Low |
| 14.2 Towing and tractor beam | Tow another ship (furbing, carrying fighters); pre-lock before combat. [cabal glossary.html, docs wiki Furbing] CONFIRMED | Missing. | Missing | L / Low |
| 14.3 Planet busting for exp | Create then destroy planets for 75 exp per loop. [cabal glossary.html] CONFIRMED | genesis xp 100, planet_destroy; loop cost vs reward not examined. | Different | S / Low |
| 14.4 Unmanned-ship fighters | Fighters on unmanned ships are excluded from universe totals. [docs wiki Interdictor_Cruiser] CONFIRMED | n/a (single ship). | Missing | S / Low |
| 14.5 Evil trading loops (SDF, SDT, D/RTR) | Steal-Dump-Flee and related tactics need rob/steal, towing, multiple ships. [cabal glossary.html] CONFIRMED | Missing, depends on 2.12, 3.18, 14.2. | Missing | L / Low |
| 14.6 Ours-only systems | Not in the original. | Alliances, planet value dividend, 100M-credit victory, play_to_day_cap, observation helper blocks for bots. | Different | S / Low |
