# gap-map-refresh-v5

Plan only. Every October row, graded at tip `f969cee`. A row is Match when the original rule is what a normal game does now. Match-behind-flag means the original rule is in the code and the named switch stays off. Partial means part of the rule is in. Different means the game still does something else. Missing means this pass found no handler. Ben-decision is a number Ben has not chosen. Class M colonists and random StarDock stay in that last bucket.

## Counts

| Grade | Rows |
|---|---|
| Match | 50 |
| Match-behind-flag | 17 |
| Partial | 53 |
| Different | 38 |
| Missing | 11 |
| Ben-decision | 2 |
| Total | 171 |

## Still open, and no switch at all

Play feel first. These are Missing or Partial, and no flag names them.

1. Planet scanner (4.13). Shielded planets still show their fighters.
2. Scanner fog for planet fighters and shields (6.1). Same leak.
3. Good-trader and evil-trader perks (9.7). Where you are safe is still incomplete.
4. Overnight ship parking in a citadel (6.9).
5. The good-trader daily tax (11.6).
6. Radio channels (13.2).
7. The daily stats screen (12.7).
8. FedComm (13.6).

Gold-mode aliens (8.9), corporation rankings (10.11), and the evil trade loops (14.5) are also Missing. They change less of a normal day, so they sit behind those eight.

## Every row

1.1 Match. Default universe is 1000 sectors.
1.2 Different. One-way lanes are still about 15 percent, not about 3 percent.
1.3 Different. A plotted course stops at 60 hops. The setting of 45 is unverified.
1.4 Match. FedSpace is sectors 1 through 10.
1.5 Ben-decision. StarDock stays in sector 1.
1.6 Partial. Terra exists while class 0 is on. Colonist packing stays behind TERRA_COLONIST_MODE.
1.7 Match. Class 0 ports are on (CLASS0_MODE).
1.8 Partial. Bank, tavern, shipyard, and hardware are on. Not every StarDock menu is.
1.9 Partial. Ferrengal's mines and fighters are on. The quasar is not built.
1.10 Different. Ports still appear in about 65 percent of deep sectors, not 40 percent.
1.11 Different. Starting planets are still sparse.
1.12 Match. A sector holds at most 5 planets.
1.13 Match-behind-flag UNIVERSE_TOPOLOGY_MODE. Dead ends, traps, tunnels, and one bubble.
1.14 Match. FedSpace keeps 5 ships per sector and tows the rest.
1.15 Partial. Feds tow a ship with 99 or more fighters. The Bible says 50.
1.16 Match. A good trader with under 1000 experience is already safe in FedSpace.
1.17 Match. The nightly Extern sweep runs.
1.18 Different. Sectors 2 through 10 still get decorative federal ports.
1.19 Match. Sector caps are 5000 fighters, 30000 with a planet, and 99 mines.
1.20 Match. You can pick your fighters and mines back up.
2.1 Match. Three trade goods.
2.2 Different. Port class numbers still do not match the original table.
2.3 Match-behind-flag PORT_PRICE_MODE. The original price curve is coded and off.
2.4 Match. Each port has its own MCIC and productivity.
2.5 Different. Prices and ship costs still do not sit on one scale.
2.6 Partial. Haggling exists. The live window stays behind HAGGLE_LIVE_MODE.
2.7 Match. The first trade in a sector costs a turn. Later trades there do not.
2.8 Match-behind-flag PORT_REGEN_MODE. Five percent restock is coded and off.
2.9 Different. Ports still do not open the day full.
2.10 Different. Class 0 hold prices are still flat.
2.11 Match-behind-flag SHOP_PRICE_MODE. The hold and fighter price waves are coded and off.
2.12 Match. Robbing a port is on.
2.13 Match. Stealing from a port is on.
2.14 Partial. A bust is on. Clearing the record is not the full original service.
2.15 Partial. Blowing a port is behind PORT_ATTACK_MODE, which stays off.
2.16 Match. Building and upgrading a port is on.
2.17 Match-behind-flag DETECT_GEAR_MODE. The psychic probe price peek is coded and off.
2.18 Match. StarDock trading is on.
3.1 Partial. The live roster is behind SHIP_ROSTER_MODE.
3.2 Partial. Merchant cruiser stats are close and not fully on the live table.
3.3 Different. Scout numbers still disagree with the screen.
3.4 Partial. Missile frigate is close.
3.5 Different. Battleship price still disagrees.
3.6 Partial. Corporate flagship is close.
3.7 Different. Colonial transport still disagrees.
3.8 Different. CargoTran still disagrees.
3.9 Different. Merchant freighter still disagrees.
3.10 Partial. Havoc gunstar is close and has no ship TransWarp until the roster switch.
3.11 Match-behind-flag SHIP_ROSTER_MODE. The live price is coded and off.
3.12 Match-behind-flag SHIP_ROSTER_MODE. The four mid-ships are in the table.
3.13 Match-behind-flag SHIP_ROSTER_MODE. The Tholian Sentinel is in the table.
3.14 Match-behind-flag SHIP_ROSTER_MODE. The Interdictor Cruiser is in the table.
3.15 Partial. Some per-ship caps are on. The full chart waits on the roster switch.
3.16 Match. Combat odds are already the chart. The naming switch stays off and changes nothing.
3.17 Partial. Trade-in is 25 percent. TRADE_IN_MODE stays off.
3.18 Match. A player can own more than one ship.
3.19 Match. Empty ships can be captured.
3.20 Partial. A federal commission exists. The ISS rule is only partly the original.
4.1 Partial. Genesis works. The price sources still disagree, and the empty start is behind GENESIS_START_MODE.
4.2 Partial. Atomic detonators exist. The old port-nuke mine is still sold.
4.3 Match. Marker beacons are on.
4.4 Match. Corbomite is on.
4.5 Match. Cloaks are on.
4.6 Different. An ether probe still scans one sector and is not shot down.
4.7 Match. Mine disruptors are on.
4.8 Different. Armid prices and caps still disagree.
4.9 Partial. Limpets attach and can be queried. Removal is only partly the original service.
4.10 Different. A photon is still not limited to the frigate and the ISS, and it does not shut a sector down.
4.11 Different. Density info is still a free scan, not a bought device.
4.12 Different. Holo info is still free.
4.13 Missing. No planet scanner.
4.14 Match-behind-flag DETECT_GEAR_MODE. Same probe as 2.17.
4.15 Match. Ship TransWarp is on.
4.16 Partial. Planet transport is on. A ship-to-ship beam is not the original chart.
4.17 Partial. Cloak, disruptor, atomic, and beacon caps exist. Not every item is capped.
5.1 Match. Entry order is NavHaz, limpet, armids, sector quasar, then fighters.
5.2 Match. NavHaz damages on the percent, and FedSpace clears it at night.
5.3 Different. Armid damage still does not match the original formula.
5.4 Different. Offensive fighters still do not match the original exchange.
5.5 Match. Defensive fighters challenge an entering ship.
5.6 Different. Toll math still disagrees.
5.7 Different. Ship versus ship still does not match the original exchange.
5.8 Match. A ship can send only its charted fighters in one attack.
5.9 Match. Retreat is a verb and a flee spends extra turns.
5.10 Partial. Some ships cannot be fled. The Tholian case is not fully the original.
5.11 Match. Surrender is a verb.
5.12 Partial. A destroyed ship becomes a pod. The clean loadout stays behind DEATH_POD_MODE.
5.13 Different. Pod limits and elimination still disagree.
5.14 Partial. Experience drops on death. Alignment from the loss is only partly the original.
5.15 Match. Furbing another ship's holds is on.
5.17 Match. Corbomite and disruptors fire in combat.
5.18 Partial. A photon damps a quasar for one approach. It does not do the full sector shutdown.
5.19 Match. Landing on a defended planet is a fight.
5.20 Partial. FedSpace combat has penalties. It is not the full original police response.
6.1 Missing. Planet fighters and shields stay visible without a scanner.
6.2 Partial. Citadel costs follow the class table that is on. The class M level-1 colonist figure is Ben's choice.
6.3 Ben-decision. Class M population cap stays 30,000 until Ben chooses. The die-off rule is behind PLANET_PROD_MODE.
6.4 Match-behind-flag PLANET_PROD_MODE. Fuel from colonists divided by 3, and the 5 percent die-off.
6.5 Match-behind-flag GENESIS_START_MODE. A new planet starts empty.
6.6 Match. Five planets per sector, same as 1.12.
6.7 Partial. Genesis class choice is only partly the original.
6.8 Match. Planetary trading is on.
6.9 Missing. No overnight parking of a ship inside a citadel.
6.10 Partial. Destroying a planet is in. The colonist-kill rule is only partly the original.
6.11 Different. Corporate planet quirks still disagree.
6.12 Different. Planet experience and alignment still disagree.
6.13 Match-behind-flag PLANET_DIVIDEND_PAY_MODE. Turning it off stops the growth dividend.
6.14 Different. Some citadel perk lines still say the perk is missing.
7.2 Match-behind-flag CITADEL_DAYS_MODE. Build days can use the slower scale.
7.3 Match. A finished level still grants fighters and shields.
7.4 Match. Atmospheric quasar factor is the original one.
7.5 Different. The treasury cap still disagrees.
8.1 Different. Ferrengi hulls still disagree.
8.2 Different. Ferrengi behavior is only partly the original.
8.3 Different. How many Ferrengi appear, and how fast, still disagrees.
8.4 Partial. A Ferrengi bounty is paid. The experience is only partly the original.
8.6 Match. Alien traders other than Ferrengi are on.
8.7 Partial. Federal ships exist. The live ship table stays behind FED_SHIPS_MODE.
8.8 Partial. Fighters fight players. There is no separate NPC crew.
8.9 Missing. No gold-mode aliens.
9.1 Match-behind-flag STARTING_PACKAGE_MODE. The clean start package is coded and off.
9.2 Partial. Experience sources exist. Discovery experience stays behind DISCOVERY_EXP_MODE.
9.3 Different. Experience from a player kill still disagrees.
9.4 Match. Alignment already moves by the fighters lost times the other alignment, divided by 5000.
9.5 Partial. Some other alignment hits exist. Not the full list.
9.6 Match. Rank titles are already the original ladders.
9.7 Missing. No separate good-trader and evil-trader perk set.
9.8 Partial. A rob pays from experience. The full pricing limit is not the original table.
9.9 Partial. A mixed-alignment corp can lose experience. The rule is only partly the original.
10.1 Partial. Creating a corporation is in. The purchase rule still has a source conflict.
10.2 Partial. Joining is in. The checks are only partly the original.
10.3 Match. A joiner already has to match the C.E.O.'s alignment.
10.4 Different. The member cap is 5. The original sample differs.
10.5 Match. The C.E.O. can drop a member.
10.6 Partial. Members can transfer. Not every original transfer is in.
10.7 Partial. Corp assets and member locations are only partly visible.
10.8 Match. A corp memo exists.
10.9 Partial. Corporate fighters and mines exist. Corporate ships are only partly the original.
10.10 Partial. A C.E.O. leaving does not follow every original ending.
10.11 Missing. No corporation ranking screen.
10.12 Match-behind-flag ALLIANCE_MODE. Alliances are coded and off.
11.1 Partial. The hardware shop is in. Not every original item price is the live one.
11.2 Partial. The shipyard is in. Trade-in and the roster stay partly off.
11.3 Match. Police HQ can grant a commission.
11.4 Match. A killed player can carry a bounty.
11.5 Match. The galactic bank is on.
11.6 Missing. No daily tax on a good trader.
11.7 Partial. Underground access is only partly the original mafia.
11.8 Match. The tavern is on.
11.9 Partial. Feds tow and answer some crimes. Not every evil-trader attack is the original.
11.10 Partial. Class 0 and StarDock have some defence. Not the full original set.
11.11 Partial. Some Big Bang options exist. Not the whole original screen.
12.1 Match. Turns per day are a game setting.
12.2 Match-behind-flag TURN_REGEN_MODE. Turns can come back across 24 hours.
12.3 Different. Movement is still by turns, not by the clock. Planet goods can accrue on PLANET_REALTIME_PROD_MODE.
12.4 Partial. Extern cleans FedSpace. Not every original nightly job is in.
12.5 Different. The match still ends on net worth. Experience ranking stays behind EXP_SCORE_MODE.
12.6 Partial. Tournament options are only partly the original.
12.7 Missing. No daily stats screen.
13.1 Partial. A direct hail exists.
13.2 Missing. No radio channels.
13.3 Partial. Mail is only partly the original.
13.4 Partial. Fighter and combat reports exist and are not the full original set.
13.5 Different. An ether-probe report is still the one-sector scan.
13.6 Missing. No FedComm.
14.1 Partial. The computer can plot a course. Not every original helper is in.
14.2 Match. Towing is on.
14.3 Different. Planet-busting experience still disagrees.
14.4 Match. An unmanned ship can still hold fighters.
14.5 Missing. The evil trading loops are not a coded path.
14.6 Different. Systems that were never in the original are still in this game.
