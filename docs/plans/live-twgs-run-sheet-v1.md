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
| I | Class 0 and StarDock kills | first kill about 248,000 fighters, later kill about 890,000 | yes |

## Group A. TEDIT only

Turns: 0. Credits: 0.

Setup: the new test character is logged out. You are in TEDIT on the private test game. No ship, no sector.

### Death delay maximum

item_id: n96-death-delay-max

Keys: TEDIT, Death Delay. Try 0, then 1, then 2, then the largest whole number the field accepts.

Read: the highest accepted value, and the message if the field refuses.

Settles: `GameConfig.death_delay`. Leave the field at 1 or more before Group F, unless you are recording the 0 case in that group.

## Group B. Computer, one cheap ship, one safe sector

Turns: about 2. Credits: 0.

Setup: the new test character, in a Merchant Cruiser, in a safe sector that is not StarDock and not a port you will attack. Move once, into another safe sector, so backtrack has a previous sector. Do not fight. Do not fly a plotted course.

### Plotted course limit

item_id: n96-course-max

Keys: from the command prompt open the computer, then the course plotter. On this project's cockpit that is C, then F. On the original TW2002 computer menu, press the letter printed beside the course plotter and write that letter in the notes. Plot one course you know is longer than 45 hops, and one of 45 or fewer. Do not fly either course.

Read: the refusal text, or the plotted length. In the General Editor, read "Maximum Course Length".

Settles: `V311_COURSE_MAX_HOPS`. The queue also names `COURSE_MAX_MODE`, the switch that turns the cap on. This visit does not change the switch.

### Quick-stats and backtrack keys

item_id: n103-quick-backtrack

Keys: from a prompt, press `>`, then press `<`. The one move in this group's setup is the previous sector for `<`.

Read: which screen opens for each key.

Settles: the two keys in the cockpit. No engine constant.

### Computer menu B

item_id: n110-computer-b

Keys: open the original TW2002 Computer menu. Read the label next to B before you press it. Then press B. From a prompt, press `<` again.

Read: the menu label for B, and whether B and `<` do the same thing.

Settles: none, cockpit key, not an engine constant. NOTE 103 made B backtrack on this cockpit. The original backtrack key is `<`.

## Group C. Trading, then the shipyard

Turns: about 20 for the trip. The rename itself is 0 turns. Credits: `SHIP_RENAME_COST` is 5,000, plus whatever the port quotes for the two haggling deals.

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

Settles: `SHIP_RENAME_COST` (5,000) and `SHIP_RENAME_NAME_MAX` (30).

## Group D. Small fights, not ports

Turns: about 15. Credits: 100 fighters is 5,000 at `FIGHTER_COST` 50, plus losses. A Missile Frigate is 100,800 in this game if this character has to buy one. Record the live shipyard price.

Setup: two test characters on the same private test game. One flies a Missile Frigate (odds 1.3). The other flies a Merchant Cruiser (odds 1.0). Meet in an empty sector. No port in that sector. No Ferrengi until Group E.

### Ship-odds loss split

item_id: n96-ship-odds

Keys: from the Missile Frigate, send 100 fighters at the Merchant Cruiser. Note fighters and shields on both ships first. Repeat from the Merchant Cruiser, again with 100 fighters, after both ships are restocked to known counts.

Read: fighters and shields left on both ships after each pass.

Settles: `docs/plans/ship-odds-exchange-v1.md`. No new switch. `RULINGS_v311.md` is not in the repo. The expected split is attacker loses ceil(R / A) when P >= R, else the defender loses floor(P / D).

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

Setup: Group A has already set Death Delay. This destroys the ship. Do it only when the character can buy another ship.

### Flying pod sentence

item_id: n96-flying-pod

Keys: with death delay at 1 or more, lose the ship. Wait out the sentence until the pod can move. Then lose the pod. Set death delay to 0 and repeat.

Read: whether a new sentence starts when the flying pod is destroyed, and how many midnights pass.

Settles: `death_delay_days`.

## Group G. Port shots, not kills

Turns: a few per class, eight classes (1, 2, 3, 4, 5, 7, 8, and 9). Credits: only the fighters you send to draw a return shot, at 50 each. Do not destroy the port. Do not shoot StarDock here. Do not shoot a class 0 port here.

Setup: one ship that can survive a return shot. A new sector for each class.

### Port rating and barrage, classes 0-5 and 7-9

item_id: n98-port-rating

Keys: attack one port of each of those classes. Class 6 is already rating 98 and barrage 598. Skip class 6. Skip class 0 until Group I. Read the defensive rating before the shot.

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
