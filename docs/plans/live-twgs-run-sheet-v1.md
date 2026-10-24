# Live TWGS run sheet (NOTE 110)

Use a new test character on a private test game. Do not use Ben's beta games. Do not use ports 8099-8119.

This sheet orders every row in `docs/plans/live-twgs-test-queue-v1.md`. Same character, same ship, and the same sector stay together. Cheapest and safest first. Port kills, StarDock kills, and planet overload are last, and only if the game can spare them.

Write each result in a copy of `docs/plans/live-twgs-results-template-v1.csv`. Then run `python3 scripts/live_queue_proposals.py` on that copy. The script is a dry run. It writes nothing and changes nothing. This sheet does not change a constant. No new switch. Helper row 166 is not used.

Prices below are this game's figures, so you can budget. Record the live screen, not these figures. Fighter price used here is `FIGHTER_COST` (50). Ship prices used here are Merchant Cruiser 41,300 and Missile Frigate 100,800.

## Order

| Group | Setup | About | Only if the game can spare it |
|---|---|---|---|
| A | TEDIT, no ship | 0 turns, 0 credits | no |
| B | Merchant Cruiser, one safe sector | about 2 turns, 0 credits | no |
| C | Same character, one normal port, then the StarDock shipyard | about 20 turns, 5,000 credits plus the cargo quote | no |
| D | Two characters, small ships, no ports | about 15 turns, about 5,000 credits of fighters, plus a Missile Frigate if you buy one | no |
| E | Ferrengi, watch before any kill | one day on the clock, then six kills, plus fighter restock | no |
| F | Pods, after the TEDIT delay is set | the delay in midnights, twice; two replacement ships | the two lost ships |
| G | Port shots that are not kills | 8 classes, a few turns each, fighters for a return shot | no |
| H | Planet overload | several Extern days, and the planets you build | yes |
| J | One warp in a Merchant Cruiser and a Scout, then one shield at StarDock | a few turns, one shield | no |
| K | Underground, one steal, one rob, a corpie if the game has one | the turns those visits take | no |
| L | One midnight, FedSpace, colonists, one port upgrade, one limpet | visits and one jettison. Not a port kill | no |
| I | Class 0 and StarDock kills | first kill about 248,000 fighters, later kill about 890,000 | yes |

## Group A. TEDIT only

Turns: 0. Credits: 0.

Setup: the new test character is logged out. You are in TEDIT on the private test game. No ship, no sector.

### Death delay maximum

item_id: n96-death-delay-max

CLOSED. 24 Oct 2026, Ven GameA / Slot A. TEDIT was not opened. Death Delay is Yes/No. The prompt is "Enable Death Delay?". The default is Yes. TWSTATS reads Death Delay=True. There is no numeric maximum. S7 #16's day count is not this field. Gold is what can turn it off.

Settles: `GameConfig.death_delay`. Leave Death Delay on before Group F unless that group is recording No.

### Deaths Per Day maximum

item_id: n96-deaths-per-day-max

BLOCKED. Deaths Per Day is a separate number. The prompt is "How many deaths per day?". The default is 0. TWSTATS reads Deaths Per Day=0. The largest whole number the field accepts was not measured. Slot A may lock the game. Do not invent a maximum. Open TEDIT on a spare game when one is free. Try 0, then 1, then 2, then the largest whole number the field accepts.

Read: the highest accepted value, and the message if the field refuses.

Settles: `GameConfig.deaths_per_day`. TEDIT maximum unmeasured.

## Group B. Computer, one cheap ship, one safe sector

Turns: about 2. Credits: 0.

Setup: the new test character, in a Merchant Cruiser, in a safe sector that is not StarDock and not a port you will attack. Move once, into another safe sector, so backtrack has a previous sector. Do not fight. Do not fly a plotted course.

### Plotted course limit

item_id: n96-course-max

Keys: from the command prompt open the computer, then the course plotter. On this project's cockpit that is C, then F. On the original TW2002 computer menu, press the letter printed beside the course plotter and write that letter in the notes. Plot one course you know is longer than this game's Maximum Course Length, and one of that length. On GameA that length is 20. Do not fly either course.

Read: the refusal text. Confirm whether the number in it is 20. TEDIT field bounds are still unread.

Settles: the per-game length on `GameConfig.max_course_length`. `V311_COURSE_MAX_HOPS` stays the unset default, the published sample 45. `GAMEA_COURSE_MAX_HOPS` is the measured GameA value and is not applied until a game sets the field. This visit does not change `COURSE_MAX_MODE`.

Status: GameA's setting is measured. `docs/playtests/twgs-live/plotted-course-limit.txt` records TWSTATS `Max Course Length=20` on 2026-10-24. The live plot that would show the refusal number, and the TEDIT numeric min and max, are still blocked. No plot was run. No TEDIT was opened.

### Quick-stats and backtrack keys

item_id: n103-quick-backtrack

Keys: from a prompt, press `>`, then `/`. The cockpit opens quick stats on `>` and does nothing on `/`. Then press `<` after one adjacent move, and again after a one-way move. The group's one move can be the adjacent hop. Do not fly a plotted course.

Read: which key opens quick stats. Whether `<` warps back or plots a course, for the adjacent hop and for the one-way hop.

Settles: the two keys in the cockpit. No engine constant. `<` is already the backtrack key in EIS `MainMenu.html` and in `computer-b.txt`. `>` stays quick stats here. `/` is the documented quick-stats key and is not bound until a live press says which key opens the screen. A non-adjacent `<` plots on 3.34b and this cockpit refuses. See `docs/playtests/note103-quick-backtrack-v1.md`.

### Computer menu B

item_id: n110-computer-b

Keys: open the original TW2002 Computer menu. Read the label next to B before you press it. Then press B. From a prompt, press `<` again.

Read: the menu label for B, and whether B and `<` do the same thing.

Settles: none, cockpit key, not an engine constant. Measured in `computer-b.txt`. Under the v3.11 profile, Computer B is Begin Self Destruct and `<` stays the previous-sector key. A legacy Computer menu still uses B for backtrack.

### Real-time hop time

item_id: n112-hop-time

Keys: warp one sector in the Merchant Cruiser. Time the hop. Change to a Scout if the shipyard has one, warp one sector, and time that hop. If a SysOp speed setting is on the screen, change it and repeat both warps.

Read: seconds for each hull, and the speed setting.

Settles: a per-hull travel time, only if the screen or the editor prints one. This game spends turns per warp and does not delay the hop.

## Group C. Trading, then the shipyard

Turns: about 20 for the trip. The rename fee is 5,000 credits. Turns on the rename were not measured, so this game does not charge a turn for it. Credits: `SHIP_RENAME_COST` is 5,000, plus whatever the port quotes for the two haggling deals.

Setup: the same character and the same Merchant Cruiser. Use one normal port. Not StarDock. Not a class 0 port. Do the rename at the StarDock shipyard after the two deals, and before any later group destroys a port.

### Good haggle experience

item_id: n97-haggle-good

Keys: dock, open trade, and accept a price that beats the offer and stops short of the hidden bound.

Read: experience before and after.

Settles: `HAGGLE_EXP_GOOD` (1).

### Great haggle experience

item_id: n97-haggle-great

Keys: at the same port, or the next normal port, take the price the port will not beat.

Read: experience before and after, and whether 5 is awarded for the exact best price.

Settles: `HAGGLE_EXP_GREAT` (2).

### Ship rename

item_id: n97-ship-rename

Keys: at the StarDock shipyard, rename the ship. Try a 30-character name, then one character more.

Read: credits taken, the longest name accepted, and the turn counter.

Settles: `SHIP_RENAME_COST` (5,000) and `SHIP_RENAME_NAME_MAX` (30) are CONFIRMED (Ven 2026-10-24). Still read the turn counter. Turns are not settled.

### Shield unit price

item_id: n112-shield-price

Keys: at StarDock, buy one shield. Come back on a second day and buy one shield again. Read that day's fighter price on the same visit.

Read: the credit price each day, next to that day's fighter price.

Settles: a shield price, only if the screen prints one. The flat 10 stays until then. The fighter wave in this game is 160 to 239.

## Group D. Small fights, not ports

Turns: about 15. Credits: 100 fighters is 5,000 at `FIGHTER_COST` 50, plus losses. A Missile Frigate is 100,800 in this game if this character has to buy one. Record the live shipyard price.

Setup: two test characters on the same private test game. One flies a Missile Frigate (odds 1.3). The other flies a Merchant Cruiser (odds 1.0). Meet in an empty sector. No port in that sector. No Ferrengi until Group E.

### Ship-odds loss split

item_id: n96-ship-odds

Keys: from the Missile Frigate, send 100 fighters at the Merchant Cruiser. Note fighters and shields on both ships first. Repeat from the Merchant Cruiser, again with 100 fighters, after both ships are restocked to known counts.

Read: fighters and shields left on both ships after each pass.

Settles: `docs/plans/ship-odds-exchange-v1.md`. No new switch. `RULINGS_v311.md` is not in the repo. The expected split is attacker loses ceil(R / A) when P >= R, else the defender loses floor(P / D).

### Ship-odds loss split

item_id: n112-ship-odds

Keys: no second fight. The NOTE 96 row above is this measurement.

Read: the same fighters and shields.

Settles: `docs/plans/ship-odds-exchange-v1.md`. Already queued. No new switch.

### Attack turn cost

item_id: n112-attack-turns

Keys: attack one ship. Read the turn counter before and after. Repeat from the other hull.

Read: turns spent, and whether that number changes with the hull.

Settles: `ATTACK_TURN_MODE` (profile row 228). Live KillTest spent 0 turns on a ship attack (`docs/playtests/twgs-live/attack-turn-cost-ven.txt`). Stored games keep `TURN_COST["attack"]` at 5. Only a Merchant Cruiser was measured, so there is no per-hull cost.

### Attacker destroyed by its own attack

item_id: n112-attacker-destroyed

Keys: from the weaker ship, send every fighter into the stronger ship.

Read: whether the attacker is podded.

Settles: no constant until a screen shows it. This game does not destroy the attacker for spending its own fighters.

### Alien kill alignment share

item_id: n98-alien-align

Keys: kill one alien of the other alignment, then one alien of the same alignment. Do not use a port.

Read: your alignment before and after, and the alien's alignment and experience.

Settles: `ALIEN_KILL_ALIGN_SHARE` (0.5).

## Group E. Ferrengi, watch first

Turns: one day on the clock while you sit, then the turns to restock and to make six kills (three hulls while good, three hulls while neutral or evil). Credits: fighter restock at 50 each, plus whatever those fights spend.

Setup: the same character when you are watching. A second alignment, good and then neutral or evil, is required for the kills. Use a sector where two Ferrengi can be seen. Do not blow a port.

### Ferrengi banding cutoff

item_id: n96-ferrengi-banding

Keys: none beyond moving to a sector where you can see two Ferrengi. Hold more fighters than one of them and fewer than the other. Another Ferrengi should be in your sector or one hop out.

Read: whether the weaker ship steps into your sector, and the fighter counts on all three.

Settles: `FERRENGI_BAND_STRONG`.

### Ferrengi attack clock

item_id: n96-ferrengi-clock

Keys: sit still in one sector until a Ferrengi hops in. Stay for the rest of the day. Do not fire.

Read: whether the Flee / Attack / Surrender menu appears on the hop, or only after midnight.

Settles: `FERRENGI_PACE_MODE`.

### Ferrengal quasar

item_id: n96-ferrengal-quasar

Keys: enter the Ferrengal sector in a ship with known shields and fighters. Do not land.

Read: the quasar line (damage, and fuel burned if shown). If a scan shows the planet, read sector percent and ore.

Settles: `FERRENGAL_QUASAR_FUEL` (10,000) and `FERRENGAL_QUASAR_PCT` (10).

### Ferrengi kill experience

item_id: n96-ferrengi-xp

Keys: as a good trader (alignment above 0), kill one assault trader, one battle cruiser, and one dreadnought. Repeat all three as a neutral or evil trader. The next row uses these same six kills.

Read: experience before and after each kill, and whether alignment changed the award.

Settles: `FERRENGI_XP_BY_HULL` (assault trader 50, battle cruiser 100, dreadnought 150).

### Ferrengi alignment on a kill

item_id: n96-ferrengi-align

Keys: the same six kills as the experience row. Read alignment on each of them. Do not make a second set of kills for this row.

Read: the alignment delta for a good trader and for a neutral or evil trader.

Settles: `FERRENGI_ALIGN_ON_KILL` (10, and only when alignment is already above 0).

## Group F. Pods

Turns: the death-delay midnights, then the same wait again with the delay at 0. Credits: two replacement ships. A Merchant Cruiser is 41,300 in this game. Pay the live shipyard price and record it.

Setup: Group A left Death Delay on. Deaths Per Day is the allowance, default 0. This destroys the ship. Do it only when the character can buy another ship.

### Flying pod sentence

item_id: n96-flying-pod

Keys: with Deaths Per Day at 0, lose the ship. The wait is until the next day, not an S7 count of days. Then set Deaths Per Day to 1, lose the ship, buy back, and lose it again. Then set Death Delay to No and lose the ship.

Read: whether the first death waits, whether the second death waits, and whether No takes the day's turns.

Settles: `death_delay_days`. S7's flying-pod sentence is not the v3 TEDIT field.

## Group G. Port shots, not kills

Turns: a few per class, eight classes (1, 2, 3, 4, 5, 7, 8, and 9). Credits: only the fighters you send to draw a return shot, at 50 each. Do not destroy the port. Do not shoot StarDock here. Do not shoot a class 0 port here.

Setup: one ship that can survive a return shot. A new sector for each class.

### Port rating and barrage, classes 0-5 and 7-9

Measured 2026-10-24 on Ven GameA (TW Test Game 2, Slot A, v3.34b). Capture: `docs/playtests/twgs-live/gap215-port-attack-2026-10-24.md`. Do not repeat the confirmed shots. CONFIRMED lasers: class 1 337, class 4 1419, class 6 598 (prior REPORT2), class 7 1121. Still open: lasers for classes 2, 3, 5, and non-Fed class 8. Class 0 and StarDock stay Group I. Def rating is per port, not a class constant. A 0-fighter commit aborts after the def and shield text.

item_id: n98-port-rating

Keys: attack one port of each of those classes. Class 6 is already rating 98 and barrage 598. Skip class 6. Skip class 0 until Group I. Read the defensive rating before the shot. The 2026-10-24 capture already holds classes 1, 2, 3, 4, 5, 7, and non-Fed 8.

Read: the rating, the return-shot number, the fighters you sent, whether the port was destroyed (it should not be), and the port's size or productivity on that same screen.

Settles: `PORT_DEFENSE_RATING` and `PORT_LASER_BARRAGE`.

### Port fighters from the port's size

item_id: n98-port-fighters

Keys: the same attacks as the rating row. Do not make a second pass for this row.

Read: any words the screen uses for the port's fighters or firepower, next to the port's productivity.

Settles: a new constant, only if the screen prints a formula or a fighter count. No constant until then.

## Group H. Planet overload

Only if the game can spare the planets. Turns: several Extern days, plus the turns to build past the cap. Credits: whatever those planets cost to build. Do this before Group I so a StarDock kill cannot confuse the sector 1 check.

### Planet collision chance

item_id: n102-collision-chance

Keys: overload one sector past the planet cap and run Extern for several days. The cap in this game is `PLANETS_PER_SECTOR_CAP` (5).

Read: whether a collision happens, and how many planets are lost.

Settles: `PLANET_COLLISION_PCT_PER_EXCESS` (10 percent per planet over the cap, never past 100).

### Collision log wording

item_id: n102-collision-log

Keys: the same overload as the chance row.

Read: the exact daily-log lines. The stand-in wording is "Unstable planetary mass in sector N" every night, and a loss line that names the planets and leaves the sector number out.

Settles: no named constant. The two daily-log sentences are inline in the day tick.

### Sector 1 overload

item_id: n102-sector1

Keys: overload sector 1 only if the game can spare it. Run Extern.

Read: whether Extern collides planets there.

Settles: `STARDOCK_SECTOR` (1), the skip of that sector in the day tick.

## Group J. One warp, already counted above

The hop is in Group B and the shield buy is in Group C. This heading is the order-table row for those two steps.

## Group K. Underground, steal, and rob

Turns: the trip to StarDock's Underground, one steal, and one rob. Credits: whatever the screen charges for a name change, one Tri-Cron, and one illegal good. A corpie is needed for the paired steal-dump-flee. Try the solo pass on the same character.

Setup: the same test character. Do not blow a port. Do not use a beta game.

### Steal-dump-flee, solo

item_id: n115-sdf-solo

Keys: with a corpie, run one steal-dump-flee cycle. Then try the same cycle with one ship.

Read: the turns spent, whether the penalty landed, and the solo steps if the game allows them.

Settles: none until the screen shows a solo procedure. The glossary says SDF needs another corpie and does not give the steps. The flee penalty in this game is already one turn on the next land or port.

### Underground name change

item_id: n115-ug-name

Keys: in the Underground, change the trader's name.

Read: credits taken, and whether the price moves with experience.

Settles: a higher-experience price, only if the screen prints one. Experience 1 is 100 credits (`name-change.txt`, `UG_NAME_UNKNOWN_COST`). `UG_NAME_MODE` stays legacy until v311. `UG_NAME_CHANGE` stays false.

### Tri-Cron

item_id: n115-tricron

Keys: buy one Tri-Cron round.

Read: the cost, and what one round does.

Settled by NOTE 129 (`tricron.txt`). Ante 100, 10 rounds, payback 2 to 1. `TRICRON_MODE` stays legacy. The tip is free.

### Illegal goods

item_id: n115-illegal

Keys: buy one illegal good, if the Underground sells any.

Read: the item name and the price.

Settles: a price, only if the screen prints one. The library and the singles-bar door are `STARDOCK_DOORS_MODE` row 233 and take no credits. Cineplex show 1 is `CINEPLEX_PRICE_MODE`. Illegal goods are named and not built. The 47 credit bar drop has no item name.

### Rob and steal success awards

item_id: n115-rob-steal

Keys: steal a known number of holds, then rob a known number of credits.

Read: alignment and experience before and after, next to the holds and the credits.

Settles: `STEAL_SUCCESS_ALIGN_DIVISOR`, `STEAL_SUCCESS_EXP_DIVISOR`, `ROB_SUCCESS_ALIGN_DIVISOR`, and `ROB_SUCCESS_EXP_DIVISOR`. The stand-in is steal max(1, qty // 6) alignment and max(1, qty // 15) experience, and rob divides credits by 10,000. Marked UNVERIFIED.

## Group L. Midnight, FedSpace, colonists, one upgrade, one limpet

Turns: one midnight of watching, the trip into FedSpace, one jettison, one port upgrade, one colonist attack, and one limpet removal. Credits: the limpet fee on the screen, the upgrade, and the colonists you jettison. Do not blow a port. A Class 0 visit here is a limpet removal, not a kill.

Setup: one good trader for the jettison and the tax. One evil ship that is not an Imperial StarShip for the FedSpace hunt. A planet you can afford to damage for the colonist attack.

### Remaining Extern jobs

item_id: n117-extern-jobs

Keys: watch one midnight. List any job the screen names.

Read: the job name and the numbers on that line. Compare with the jobs this game already runs: retreats, Ferrengi, the corp penalty, the Class 0 sweep, Terra, empty-ship repo, Fed tows, port regen, busts, photons, cloaks, NavHaz, aliens, planets, citadels, treasury, and tax.

Settles: none until a screen names a missing job.

### Tax alignment

item_id: n117-tax-align

Keys: pay the daily tax on that same midnight, or the next one.

Read: alignment before and after, next to the credits taken.

Settles: an alignment figure, only if the screen prints one. This game does not change alignment on the daily tax.

### Fed hold confiscation

item_id: n117-fed-holds

Keys: violate FedLaw in FedSpace. Read the hold line.

Read: holds taken, and what the violation was.

Settles: a hold count, only if the screen prints one. Confiscation is not built.

### Evil trader hunted in FedSpace

item_id: n117-evil-hunt

Keys: enter FedSpace in an evil ship that is not an Imperial StarShip. Do it once in a sector with a Federal, and once in a sector without one.

Read: whether the ship is podded, towed, or left alone.

Settles: none until the screen shows a hunt. An evil Imperial StarShip is already repossessed. Other evil ships are not hunted.

### Jettison colonist cap

item_id: n117-jettison

Keys: while good, jettison more than 250 colonists in one day. Repeat the next day.

Read: alignment lost each day.

Settles: `_COLONIST_CAP`, only if the screen prints a cap. This game stops a good trader at 250 alignment in one day. The formula page says -1 per colonist, one time per extern, and does not print 250.

### Port-upgrade alignment

item_id: n117-port-upgrade

Keys: upgrade one port. Read alignment and experience before and after.

Read: both deltas.

Settles: an alignment figure, only if the screen prints one. This game does not change alignment on a port upgrade.

### Colonist-kill alignment

item_id: n117-colonist-kill

Keys: attack colonists on a planet. Read alignment and experience before and after.

Read: both deltas, and whether the planet remains.

Settles: an alignment figure, only if the screen prints one. Destroying a planet is already -1 alignment and +50 experience. Killing colonists on a planet has no separate award.

### Limpet removal fee

item_id: n117-limpet

Keys: remove one limpet at StarDock, and one at a Class 0 port. Do not blow either port.

Read: the credit price on each screen.

Settles: stored `LIMPET_REMOVAL_COST` stays 1,250. Live GameA is 5,000 behind `limpet_removal_cost` (SOURCE-CONFLICT, Ven 2026-10-24). An on-screen compare of StarDock and Class 0, and any turn debit, are still open.

### Type I TWarp price

item_id: n117-tw-type1

Keys: at StarDock, on an Imperial StarShip, Corporate FlagShip, or Havoc Gunstar, buy one Type I drive while the live hardware card is on.

Read: the credit price.

Settles: stored `SHIP_TW_TYPE1_COST` stays 12,500. Live GameA is 50,000 behind `ship_tw_type1_cost` (SOURCE-CONFLICT, Ven 2026-10-24). `SHIP_TW_MODE` stays.

### Type II TWarp price

item_id: n117-tw-type2

Keys: at StarDock, on a TransWarp hull with no drive fitted, buy one Type II drive while the live hardware card is on.

Read: the credit price.

Settles: stored `SHIP_TW_TYPE2_COST` stays 20,000. Live GameA is 80,000 behind `ship_tw_type2_cost` (SOURCE-CONFLICT, Ven 2026-10-24). OldFAQ v2 was 80,000.

### TWarp upgrade price

item_id: n117-tw-upgrade

Keys: at StarDock, with a Type I drive already fitted, buy the upgrade while the live hardware card is on.

Read: the credit price.

Settles: stored `SHIP_TW_UPGRADE_COST` stays 9,000. Live GameA is 10,000 behind `ship_tw_upgrade_cost` (SOURCE-CONFLICT, Ven 2026-10-24). OldFAQ v2 was 40,000.
### Photon missile price

item_id: n117-photon

Keys: at StarDock, on a Missile Frigate, buy one photon while the live hardware card is on.

Read: the credit price.

Settles: stored `PHOTON_MISSILE_COST` stays 12,000. Live GameA is 40,000 behind `photon_missile_cost` (SOURCE-CONFLICT, Ven 2026-10-24). Cabal sample is 160,000. DIFFERENT on the stored card.

## Group I. Class 0 and StarDock kills

Only if the game can spare the ports. Do this last. One first kill serves the blow row, the first-kill row, the return-fire row, and the capture row. Do not repeat that kill for each row.

Turns: about 11 waves the first time, then the rebuild, then the second kill. Credits: the cabal thumb is about 248,000 fighters and 32,000 shields on an Interdictor the first time. At `FIGHTER_COST` 50, 248,000 fighters is 12,400,000 credits. The later kill is about 890,000 fighters, which is 44,500,000 credits at that same price. Record the live spend. A corpie may feed fighters.

Setup: a stock Interdictor, or the live equivalent, and a private test game that can lose one Class 0 port and StarDock.

### Class 0 and StarDock blow

item_id: n98-class0-stardock-blow

Keys: blow one Class 0 port and StarDock.

Read: fighters sent, shields lost, the rating before and after, and whether the other special ports' ratings rose.

Settles: `PORT_DEFENSE_RATING` for classes 0 and 9.

### StarDock / Class 0 first kill

item_id: n102-special-first

Keys: the same first kill. Attack until the port goes down.

Read: fighters spent, shields lost, waves, and the defensive rating before the kill.

Settles: `SPECIAL_PORT_FIGS_FIRST` (248,000) and `SPECIAL_PORT_RATING_FIRST` (2,500).

### Special-port return fire

item_id: n102-special-return

Keys: the same waves. Do not add waves for this row.

Read: shields and fighters the port removes per wave.

Settles: no constant yet.

### Port capture

item_id: n98-port-capture

Keys: after the destroy, try to claim or capture the port.

Read: whether any command captures a port, or the only result is the destroyed port.

Settles: none until a screen shows a capture.

### StarDock / Class 0 later kill

item_id: n102-special-later

Keys: after that port is rebuilt, kill it again, or kill a different special port.

Read: fighters spent and the rating on the second kill.

Settles: `SPECIAL_PORT_FIGS_AFTER` (890,000) and `SPECIAL_PORT_RATING_AFTER` (5,000).
