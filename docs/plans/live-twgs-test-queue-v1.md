# Live TWGS test queue (NOTE 96)

Cur can run these on Ben's server with a new test character. Nothing below was changed. A v3.11 source did not settle the number, so the constant stays and the comment says `UNVERIFIED, searched:`.

Settled in this slice, and not queued: an unmanned Interdictor does not hold, a cloak or a landing or a port visit drops the well, and a fighter-menu retreat is allowed past an Interdictor Cruiser. Sources are in `src/tw2k/engine/combat.py` (`hull_interdict_reason`, `retreat_block`).

The ordered run, with setup, keys, and turn and credit estimates, is `docs/plans/live-twgs-run-sheet-v1.md`. Blank results go in `docs/plans/live-twgs-results-template-v1.csv`. Fill a copy of that CSV. `python3 scripts/live_queue_proposals.py` prints a dry-run proposal and writes nothing.

## NOTE 129 results

Played 19 Oct 2026 on TWGS v2.20b, Trade Wars 2002 ver 3.34b, in TW Test Game 2, as a new character. No other trader was logged in or attacked. No engine constant was changed that day. Captures are in `docs/playtests/twgs-live/`. Two confirmed, five different, four blocked. A later slice put the measured StarDock prices behind switches. The stored defaults were not retuned. `V311_PROFILE` `v311` turns the switches on. The string `1` does not. `TW2002_LIVE_PROFILE` does not.

Unnamed nightly jobs. CONFIRMED. The journal line is "The Ferrengi moved at 12:00:01 AM, on 10/19/54", and the same single line is the journal on 10/11, 10/12, 10/13 and 10/18. No other job is named. Gap row 12.4 gets no new job. `nightly-jobs.txt`.

Fed hunt. BLOCKED. Twenty colonist holds jettisoned and alignment stayed 0 Neutral, so the evil-ship pass was not run. A neutral Merchant Cruiser walked FedSpace sectors 1 through 7 and was left alone. No Federal ship was in them. `fed-hunt.txt`.

StarDock menus. DIFFERENT, then applied behind flags. Live sector 144, Stargate Alpha I, class 9. The where-to list is Cineplex, Bank, Hardware, Libram Universitatus, Police, Shipyards, Tavern. B is a singles bar and U is the Underground door, and neither letter is on that list. Drink is 80 credits, food is 24 a plate, announcement is 100. Class 0 fighters are 218 and shields are 131 a point. Announcement 100 already matched `TAVERN_ANNOUNCE_COST`. Drink 80 and food 24 are `TAVERN_BAR_PRICE_MODE`. Shields at 131 a point are `SHIELD_POINT_MODE`. The stored drink and food prices stay 20, and the stored shield price stays the wave (flat 10 when `SHIELD_PRICE_MODE` is flat). Fighters at 218 were not retuned: that reading sits in the 160-239 wave and may be stock-dependent (UNVERIFIED). Day-to-day shield drift is UNVERIFIED. The menu said 131 a point, and the purse went from 228 to 96, which is 132. The price used is the stated 131. The library and the singles bar are still deferred. Gap row 1.8 stays Match-behind-flag. `stardock-menus.txt`.

Second rob table. BLOCKED. At alignment 0 the port list is Attack, Trade, Quit. No second table was printed. `rob-table.txt`.

Underground name change. DIFFERENT, then applied behind the existing switch. At 1 experience the screen said "Seems you're a total unknown, this'll be cheap" and "We can give you a new identity for 100 credits." The deal was declined. `UG_NAME_CHANGE` stays false. `UG_NAME_MODE` charges 100 credits for that total unknown (experience at most 1). Experience 0 was not on the screen, so that edge is UNVERIFIED. A second experience point was not measured, and that trader is refused. Gap row 11.7 stays Match-behind-flag. `name-change.txt`.

Tri-Cron. CONFIRMED. Ante 100, 10 rounds, three crons from 0 to 9, positions 1, 2 and 3, greater total wins, payback 2 to 1, jackpot 5,000, champion score 5,000. One match paid "You win 100 credits!" and the balance went from 128 to 228. Matches `TRICRON_ANTE`, `TRICRON_ROUNDS` and `TRICRON_OPENING_JACKPOT`. Gap row 11.8 already has those numbers. `tricron.txt`.

Illegal-goods prices. DIFFERENT, then the ticket was applied. The Underground menu sells no good, so no goods constant was added. The singles bar printed no item and no price; the balance fell from 140 to 93, which is 47 credits. That charge is not a constant. Cineplex show 1 asked "100 Credits Please" for Vulcan Thunder. `CINEPLEX_COST` stays 0. Show 1 is 100 credits behind `CINEPLEX_PRICE_MODE`. The other titles were not opened. Gap rows 1.8 and 11.7 stay Match-behind-flag. `illegal-goods.txt`.

Per-attempt alignment and experience awards. BLOCKED. No steal and no rob was offered, so no delta was on the screen. `rob-awards.txt`.

Solo steal-dump-flee. BLOCKED. The one ship never got a steal prompt, and no solo steps appeared. `sdf-solo.txt`.

Economy price scale. DIFFERENT, recorded, anchors kept. Opening quotes, experience 0 or 1, and the screen does not print MCIC. Fuel selling at 100 percent of max: 11. Fuel buying at 100 percent: 27. Organics selling at 100 percent: 31. Organics buying at 94 percent: 66. Equipment selling at 100 percent: 56. The chart anchors behind `PRICE_SCALE_SELL_250` and `PRICE_SCALE_BUY_250` stay the economy2 100% totals: about 15, 35, 28, 71 and 49 for those same sides, and 128 for equipment buying, which this screen did not quote. `PRICE_SCALE_MODE` already quotes that chart when the flag is live or the v3.11 profile is on. The stored flag stays legacy. The day-1 numbers were not written into the anchors. The organics buy is 94 percent, equipment buying is missing, and MCIC was not printed, so these quotes are not a new formula. Gap row 2.5 stays the two printed lists (ports on the economy2 chart, ships on the Bible chart). `docs/playtests/twgs-live/price-scale.txt`. `tests/test_note129_price_scale_v1.py`.

Computer menu B. DIFFERENT, wired under the profile. The live label is "Begin Self Destruct". B asks "ARE YOU SURE CAPTAIN?" and N says "Self Destruct Aborted...". Y reuses `handle_self_destruct`. `<` stays the previous-sector key and is not B. A legacy Computer menu still uses B for backtrack. No new engine constant. `computer-b.txt`.

Death delay maximum. CLOSED. 24 Oct 2026, Ven GameA / Slot A. TEDIT was not opened. Sources are tedit.exe strings, `GameA\OUTPUT\TWSTATS.TXT`, and `REVISION.TXT`. Death Delay is Yes/No. The prompt is "Enable Death Delay?". The default is Yes. TWSTATS reads `Death Delay=True`. The help forces a podded player out for a day. If it is disabled, they re-enter immediately and death does not affect turns. Gold is what can disable it. S7 #16's 0/1/2 day count is the older SoftDocs model and is not this TEDIT field. There is no numeric maximum. `GameConfig.death_delay` is that yes/no switch. `docs/playtests/twgs-live/death-delay-max.txt`.

Deaths Per Day maximum. BLOCKED. The same sources show a separate number. The prompt is "How many deaths per day?". The default is 0. TWSTATS reads `Deaths Per Day=0`. When Death Delay is on, that many deaths may restart, and the next death waits until the next day. The help example is 1: one death and a restart, and the second death waits. The largest whole number TEDIT accepts was not measured. Slot A may lock the game. No ceiling was invented. `GameConfig.deaths_per_day`.

| Item | Current value | What to do on live TWGS | What to record | Constant it settles |
|---|---|---|---|---|
| Ferrengi kill experience | Assault trader 50, battle cruiser 100, dreadnought 150 | Kill one of each hull with a good trader (alignment above 0) and again with a neutral or evil trader. Read experience before and after. | The experience change for each hull, and whether alignment changed the award | `FERRENGI_XP_BY_HULL` |
| Ferrengi alignment on a kill | +10, and only when alignment is already above 0 | Same three kills. Read alignment before and after. | The alignment delta for a good trader and for a neutral or evil trader | `FERRENGI_ALIGN_ON_KILL` |
| Ferrengal quasar | 10,000 fuel at 10% (333 damage). Does not burn a planet's ore | Enter the Ferrengal sector in a ship with known shields and fighters. Do not land. | The quasar line: damage, fuel burned if shown, and the planet's sector percent and ore if a scan shows them | `FERRENGAL_QUASAR_FUEL`, `FERRENGAL_QUASAR_PCT` |
| Ferrengi banding cutoff | Bands when the target has more fighters than this Ferrengi, and another Ferrengi is in that sector or one hop out | Watch two Ferrengi near a trader who has more fighters than one of them and fewer than the other. | Whether the weaker ship steps into the trader's sector, and the fighter counts on all three | `FERRENGI_BAND_STRONG` |
| Ferrengi attack clock | A pace hop only relocates. The tribute menu opens on the day tick | Sit still in one sector until a Ferrengi hops in. Stay for the rest of the day. | Whether the Flee / Attack / Surrender menu appears on the hop, or only after midnight | `FERRENGI_PACE_MODE` attack timing |
| Plotted course limit | 45 hops when `COURSE_MAX_MODE` is live | From the computer, plot a course you know is longer than 45 hops, and one of 45 or fewer. | The refusal text, or the plotted length, and the General Editor "Maximum Course Length" value | `V311_COURSE_MAX_HOPS` |
| Death delay maximum | CLOSED. Yes/No, default Yes. No numeric maximum. S7's day count is not this field | Measured 24 Oct 2026 from tedit.exe strings, GameA TWSTATS, and REVISION.TXT. TEDIT was not opened | Death Delay=True. Prompt: Enable Death Delay? Gold-only can disable | `GameConfig.death_delay` |
| Deaths Per Day maximum | any whole number, default 0. TEDIT maximum unmeasured. BLOCKED | Open TEDIT on a spare game, not Slot A if it is locked. Try 0, 1, 2, and the largest whole number the field accepts | The highest accepted value, and the refusal text. Do not invent a maximum | `GameConfig.deaths_per_day` |
| Flying pod sentence | S7 said a flying pod does not start a new sentence. v3 waits until the next day only after Deaths Per Day is used, and a new day starts a new allowance | With Deaths Per Day at 0, lose a ship and see the wait. Repeat with Deaths Per Day at 1, then with Death Delay set to No | Whether the first death waits, whether the second death waits, and whether No takes turns | `death_delay_days` |
| Ship-odds loss split | Attacker loses `ceil(R / A)` when `P >= R`, else the defender loses `floor(P / D)` | In a Missile Frigate (odds 1.3) send 100 fighters at a Merchant Cruiser (1.0) with a known fighter and shield count. Repeat from a Merchant Cruiser. | Fighters and shields left on both ships | `docs/plans/ship-odds-exchange-v1.md` (no new switch; `RULINGS_v311.md` is not in the repo or an open pull request) |

## Live TWGS test queue (NOTE 98)

Items whose numbers are not settled by a v3.11 source. Run each one on Ben's server with a new test character. Record the screen text. The constant column is what a later slice may set.

| item | current value | what to do | what to record | constant |
|---|---|---|---|---|
| Port rating and barrage, classes 0-5 and 7-9 | unset. Class 6 stays rating 98, barrage 598. 2026-10-24: queued with Player of Games on Ven GameA after Sat Grok L3 ended; Class 6 already known 98/598. | Attack one port of each class with a ship that can survive a return shot. Read the defensive rating before the shot | The rating, the return-shot number, the fighters you sent, whether the port was destroyed, and the port's size or productivity on that same screen | `PORT_DEFENSE_RATING`, `PORT_LASER_BARRAGE` |
| Port fighters from the port's size | no formula | On that same attack, note anything the screen calls the port's fighters or firepower | The words and the numbers, next to the port's productivity | a new constant, only if the screen prints a formula or a fighter count |
| Class 0 and StarDock blow | the cabal 22 formula is not used | Blow one Class 0 port and StarDock only if the game can spare them. The cabal rule of thumb is about 248,000 fighters and 32,000 shields on an Interdictor the first time | Fighters sent, shields lost, the rating before and after, and whether the other special ports' ratings rose | `PORT_DEFENSE_RATING` for classes 0 and 9 |
| Port capture | not implemented. A blown port stays in the sector | After a destroy, try to claim or capture the port | Whether any command captures a port, or the only result is the destroyed port | none until a screen shows a capture |
| Alien kill alignment share | `ALIEN_KILL_ALIGN_SHARE` 0.5, subtracted from the alien's alignment. Experience is already half if opposite and a quarter if the same | Kill one alien of the other alignment and one of the same alignment. Note your alignment before and after, and the alien's alignment and experience | The alignment change next to the alien's alignment and its experience, so the half-experience reading can be kept or dropped | `ALIEN_KILL_ALIGN_SHARE` |

## Live TWGS test queue (NOTE 102)

Numbers a v3.11 source does not settle. Each row is the live test that would pin the constant. Use a new test character. Do not use a running beta game.

| item | current value | live test | what to record | constant |
|---|---|---|---|---|
| StarDock / Class 0 first kill | 248,000 fighters spent, rating 2,500 | Attack StarDock or a Class 0 port with a stock Interdictor until it goes down. A corpie may feed fighters. | Fighters spent, shields lost, waves, and the defensive rating before the kill | `SPECIAL_PORT_FIGS_FIRST`, `SPECIAL_PORT_RATING_FIRST` |
| StarDock / Class 0 later kill | 890,000 fighters, rating 5,000 | After that port is rebuilt, kill it again, or kill a different special port | Fighters spent and the rating on the second kill | `SPECIAL_PORT_FIGS_AFTER`, `SPECIAL_PORT_RATING_AFTER` |
| Special-port return fire | not modelled; a wave only spends the fighters sent | Same attacks | Shields and fighters the port removes per wave | no constant yet |
| Planet collision chance | 10 percent per planet over the cap of 5, never past 100 | Overload a sector past the planet limit and run Extern for several days | Whether a collision happens, and how many planets are lost | `PLANET_COLLISION_PCT_PER_EXCESS` |
| Collision log wording | "Unstable planetary mass in sector N" every night; the loss line names the planets and leaves the sector number out | Same overload | The exact daily-log lines | no named constant. The two daily-log sentences are inline in the day tick |
| Sector 1 overload | skipped (Old FAQ v2) | Overload sector 1 if the game allows it | Whether Extern collides planets there | the `STARDOCK_SECTOR` skip in `_planet_collisions` |

## Live TWGS test queue (NOTE 103)

`<` backtracks. `>` opens quick stats on this cockpit. The documented quick-stats key is `/`, and this cockpit does not bind it. No new live keypress in this pass. The 19 Oct 2026 `<` capture stays `docs/playtests/twgs-live/computer-b.txt`. The reading is `docs/playtests/note103-quick-backtrack-v1.md`.

Handlers, kept. `web/redesign.js` `key` sends a prompt `>` to `quickStats` (menu screen `quick-stats`) and a prompt `<` to `backtrack`. `backtrack` warps with `act("warp")` when `cameFrom` is still in `warps_out`, and otherwise refuses. The keydown listener passes `<` and `>` through before `toUpperCase`. Computer menu copies, same file, `CKEYS`: S calls `quickStats`, B calls `backtrack` unless `self_destruct` is a legal action, in which case B calls `beginSelfDestruct`. That B split is NOTE 110. The unshifted comma is not bound.

`<` is the backtrack key. CONFIRMED. EIS `MainMenu.html` prints `<<>` Return to Previous Sector, and says the unshifted comma was discontinued as of v3.05. The v3.11 revision history says the same (v3.05: backtrack is `<` only; 02/04/97: `<` or `,` moves the ship to the last sector visited). `computer-b.txt` pressed `<` after a one-way hop from 157 to 50. The game tried to warp to 157, said the lane was not adjacent, plotted 4 hops, and asked to engage the autopilot. This cockpit warps at once when the previous sector is still a warp out. When it is not, the line is "You cannot backtrack to N from here." The plotted course is DIFFERENT. v3.11 text describes a move for adjacent port pairs and does not describe that plot, so the refuse stays. UNVERIFIED: `<` on an adjacent pair on live TWGS. The capture was a one-way.

`>` quick stats. KEPT. DIFFERENT / UNVERIFIED against the docs. EIS `GlobalCommands.html` Quick-stats and `CompMisc.html` Personal Settings print the key as `</>`, the `/` key inside the docs' angle brackets. The v3.06 revision history says the quick-stats line appears when `/` is pressed. `GeneralNew.html` Quick-stats says type `</>` from any prompt. That is the same slash. It is not both `<` and `>`. No capture presses `>` or `/`. This cockpit still opens quick stats on `>`. `/` stays unbound. Do not add that key without a live press.

| item | current value | live test | what to record | constant |
|---|---|---|---|---|
| Quick-stats and backtrack keys | `>` quick stats, `<` adjacent backtrack. `/` is the documented quick-stats key and is not bound. A non-adjacent `<` plots on 3.34b and refuses here | From a prompt, press `>`, then `/`. After an adjacent hop, press `<`. After a one-way hop, press `<` | Which key opens quick stats. Whether each `<` warps or plots | the two keys in the cockpit |

## Live TWGS test queue (NOTE 97)

Numbers a v3.11 source does not settle. Searched before these rows were added: `CompDisplays.html` (J is a type catalog, no colonist table), `HardwareMenu.html` (better deal, more points, no amounts), `ShipyardMenu.html` ("hefty fee", no price and no length), S2 `S2_cabal_formulas.html` (no haggle-experience table), S7 `S7_softdocs_slice-10.txt` ("haggle for 2 points" as a player method). A player tip says the exact best price pays 5 experience. That tip was not adopted.

| item | current value | live test | what to record | constant |
|---|---|---|---|---|
| Good haggle experience | +1 | Make a deal that beats the offer and stops short of the hidden bound | Experience before and after | `HAGGLE_EXP_GOOD` |
| Great haggle experience | +2, when the accepted price reaches the hidden bound | Repeat and take the price the port will not beat | Experience before and after, and whether 5 is awarded for the exact best price | `HAGGLE_EXP_GREAT` |
| Ship rename | 5000 credits, 30 characters, 0 turns | At the shipyard, rename the ship | Credits taken, the longest name accepted, and the turn counter | `SHIP_RENAME_COST`, `SHIP_RENAME_NAME_MAX` |

## Live TWGS test queue (NOTE 110)

One added check. NOTE 103 mapped Computer B to backtrack on this cockpit. The original backtrack key is `<`. This row asks what B does on the original TW2002 Computer menu. It does not add a constant.

| item | current value | live test | what to record | constant |
|---|---|---|---|---|
| Computer menu B | Under the v3.11 profile, Computer B is Begin Self Destruct. N aborts. Y reuses the existing self-destruct. `<` stays the previous-sector key. A legacy Computer menu still uses B for backtrack | On the original TW2002 Computer menu, read the label next to B. Press B. From a prompt, after one move, press `<` | The menu label for B, and whether B and `<` do the same thing | none, cockpit key, not an engine constant |

## Live TWGS test queue (NOTE 112)

GAP 2.5 is `PRICE_SCALE_MODE` (profile row 165). The economy2 100% chart totals are the quotes. Shield unit price, the ship-versus-ship loss split, and real-time travel seconds are not in a saved file, so they are not switched.

Searched before these rows were added: `docs/playtests/ports/ECONOMY_SCALE.md` (no shield unit price), `docs/plans/ship-odds-exchange-v1.md` (loss split already queued under NOTE 96), `docs/reference/tw2002/GAP_MAP.md` row 5.7 and row 12.3, `docs/reference/tw2002/eis_tw2002_v3_docs/GeneralUpdated.html` (RealtimeMovement and InteractiveCombat: a rate by size and power, SysOp may cut it to 1/4 or 1/2 or double it, and an attack waits for the hop; no seconds and no per-hull table). StarDock trade-in is already `TRADE_IN_MODE` row 13 and `TRADE_IN_PARTS_MODE` row 76. The published 1.25 flee is already `SHIP_FLEE_MODE` row 56. Day roll while a seat holds the turn is already `DAY_ROLL_CLOCK_MODE` row 81, and a legacy game with its own day length is `LEGACY_DAY_CLOCK_MODE` row 164. `PLANET_REALTIME_PROD_MODE` stays off the profile because the original produces at Extern.

| item | current value | live test | what to record | constant |
|---|---|---|---|---|
| Shield unit price | 131 a point behind `SHIELD_POINT_MODE`. The stored price stays the wave, or flat 10 when `SHIELD_PRICE_MODE` is flat. Day-to-day drift is UNVERIFIED. Fighters that day were 218 and stay on the wave | Buy one shield on a second day and read it next to that day's fighter price | The credit price, and whether it is still 131 a point | `SHIELD_POINT_LIVE`, only if a second day prints a different point price |
| Ship-odds loss split | already queued under NOTE 96. No new switch | See the NOTE 96 row | Fighters and shields left on both ships | `docs/plans/ship-odds-exchange-v1.md` |
| Attack turn cost | an attack spends 5 turns | Attack a ship and read the turn counter before and after | Turns spent, and whether that number changes with the hull | `TURN_COST["attack"]` |
| Attacker destroyed by its own attack | the attack does not destroy the attacker | Send every fighter into a stronger ship | Whether the attacker is podded | no constant until a screen shows it |
| Real-time hop time | no delay. Movement spends turns per warp | Warp one sector in a Merchant Cruiser and in a Scout. Time the hop. Repeat after a SysOp speed change if one is set | Seconds for each hull, and the speed setting | a per-hull travel time, only if the screen or the editor prints one |

## Live TWGS test queue (NOTE 115)

GAP 14.5. Rob, steal, bust, the flee penalty, and the Underground password ladder are already built. These rows have no closed number in the repo, so they were not coded. Searched: `classictw_docs_wiki/Glossary.html` (SDF, SDT, SST, Flee Penalty), `docs/playtests/fedspace/STARDOCK_TAVERN.md` (tv19-tv21), `docs/playtests/ports/ROB_STEAL.md` (r22). Player-advice figures that were not adopted: upgrade equipment to 1260-1510, steal exactly 250, keep experience over 7500, and 14 million per 1,000 turns.

| item | current value | live test | what to record | constant |
|---|---|---|---|---|
| Steal-dump-flee, solo | not built. The glossary says SDF needs another corpie and does not give the steps. The flee penalty is already one turn on the next land or port | With a corpie, run one steal-dump-flee cycle. Also try it with one ship | The turns spent, whether the penalty landed, and the solo steps if the game allows them | none until the screen shows a solo procedure |
| Underground name change | `UG_NAME_CHANGE` stays false. A total unknown at 1 experience is 100 credits behind `UG_NAME_MODE`. A higher experience was not priced | In the Underground, change the name of a trader with more than 1 experience | Credits taken and whether the price moves with experience | a higher-experience price, only if the screen prints one |
| Tri-Cron | `TAVERN_TRICRON` is off. The tip is free and the game is not built | Buy one Tri-Cron round | The cost and what one round does | a Tri-Cron cost, only if the screen prints one |
| Illegal goods | Cineplex show 1 is 100 credits behind `CINEPLEX_PRICE_MODE`. The Underground menu sells no good. The singles bar and the library are not built. The 47 credit bar drop has no item name | Buy one illegal good, if a later visit sells one, and open the library if a stub is added | The item name and the price | a price, only if the screen prints one |
| Rob and steal success awards | steal `max(1, qty // 6)` alignment and `max(1, qty // 15)` experience; rob divides credits by 10,000. Marked UNVERIFIED | Steal a known number of holds, then rob a known number of credits. Read alignment and experience before and after | The two deltas next to the holds and the credits | `STEAL_SUCCESS_ALIGN_DIVISOR`, `STEAL_SUCCESS_EXP_DIVISOR`, `ROB_SUCCESS_ALIGN_DIVISOR`, `ROB_SUCCESS_EXP_DIVISOR` |

## Live TWGS test queue (NOTE 117)

GAP 5.20, 1.15, and the confirmed corp-break-in line of GAP 9.5 are switched (profile rows 167-169). These rows were read and not switched. No number below is printed in a saved source.

Searched: `docs/plans/gap-map-refresh-v6.md` still-open ranks 6-11 and 27, `classictw_docs_wiki/Feds.html` (confiscate holds, no count), `classictw_docs_wiki/Imperial_StarShip.html` and `Iago_War_Manual.txt` (evil ISS avoids FedSpace; the three Federals are not a hunt of every evil trader), `cabal_strategy_site/formulas.html` (MBBS rob EXP * 6 and steal EXP / 21, already `ROB_CREDIT_FACTOR` and `STEAL_HOLD_DIVISOR`; alignment table), `classictw_docs_wiki/Alignment.html` (upgrade and colonist-kill cells are ellipses), `runner.tick_day` (the named Extern jobs already run).

Ven 2026-10-24 GameA TWSTATS (`docs/playtests/twgs-live/twstats-costs-ven.txt`) prints `Type I TWarp=50,000 cr`, `Type II TWarp=80,000 cr`, and `TWarp Upgrade=10,000 cr`. Stored cabal samples stay 12,500, 20,000, and 9,000. SOURCE-CONFLICT. The three quotes use `hardware_price_live`. `SHIP_TW_MODE` stays. Citadel Transport Unit 50,000 and Citadel Transport Upgrade 25,000 already match `PLANET_TRANSPORTER_COST_FIRST` and `PLANET_TRANSPORTER_COST_EXTRA`. No shop switch for those.

| item | current value | live test | what to record | constant |
|---|---|---|---|---|
| Remaining Extern jobs | `tick_day` already runs retreats, Ferrengi, the corp penalty, the Class 0 sweep, Terra, empty-ship repo, Fed tows, port regen, busts, photons, cloaks, NavHaz, aliens, planets, citadels, treasury, and tax. Collisions and special-port rebuilds already have switches | Watch one midnight and list any job the screen names that is not in that list | The job name and the numbers on that line | none until a screen names a missing job |
| Fed hold confiscation | not built. Feds.html says the Feds can confiscate holds from a ship that violates FedLaw. No count | Violate FedLaw in FedSpace and read the hold line | Holds taken, and what the violation was | a hold count, only if the screen prints one |
| Evil trader hunted in FedSpace | an evil ISS is already repossessed. Other evil ships are not hunted | Enter FedSpace in an evil ship that is not an ISS, in a sector with a Federal, and in a sector without one | Whether the ship is podded, towed, or left alone | none until the screen shows a hunt |
| Jettison colonist cap | 250 alignment in one day, good traders only. formulas.html says -1 per colonist, one time per extern, and does not print 250 | Jettison more than 250 colonists in one day while good. Repeat the next day | Alignment lost each day | `_COLONIST_CAP`, only if the screen prints a cap |
| Tax alignment | no alignment change on the daily tax | Pay the daily tax and read alignment before and after | The alignment delta next to the credits taken | an alignment figure, only if the screen prints one |
| Port-upgrade alignment | no alignment change on a port upgrade. Alignment.html says upgrading a port gives you "..." | Upgrade one port and read alignment and experience | Both deltas | an alignment figure, only if the screen prints one |
| Colonist-kill alignment | destroying a planet is already -1 alignment and +50 experience. Killing colonists on a planet has no separate award. Alignment.html says "..." | Attack colonists on a planet and read alignment and experience | Both deltas, and whether the planet remains | an alignment figure, only if the screen prints one |
| Limpet removal fee | `LIMPET_REMOVAL_COST` 1250, marked UNVERIFIED | Remove one limpet at StarDock and at a Class 0 port | The credit price on each screen | `LIMPET_REMOVAL_COST` |
| Type I TWarp price | Stored `SHIP_TW_TYPE1_COST` 12,500. Live card `ship_tw_type1_cost` 50,000 when `hardware_price_live`. SOURCE-CONFLICT | Buy a Type I drive on an ISS, FlagShip, or Havoc at StarDock with the live card on | The credit price on the hardware screen | `SHIP_TW_TYPE1_COST` |
| Type II TWarp price | Stored `SHIP_TW_TYPE2_COST` 20,000. Live card `ship_tw_type2_cost` 80,000 when `hardware_price_live`. OldFAQ v2 80,000. SOURCE-CONFLICT | Buy a Type II drive on a TransWarp hull at StarDock with the live card on | The credit price on the hardware screen | `SHIP_TW_TYPE2_COST` |
| TWarp upgrade price | Stored `SHIP_TW_UPGRADE_COST` 9,000. Live card `ship_tw_upgrade_cost` 10,000 when `hardware_price_live`. OldFAQ v2 40,000. SOURCE-CONFLICT | Upgrade a fitted Type I drive at StarDock with the live card on | The credit price on the hardware screen | `SHIP_TW_UPGRADE_COST` |
