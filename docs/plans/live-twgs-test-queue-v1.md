# Live TWGS test queue (NOTE 96)

Cur can run these on Ben's server with a new test character. Nothing below was changed. A v3.11 source did not settle the number, so the constant stays and the comment says `UNVERIFIED, searched:`.

Settled in this slice, and not queued: an unmanned Interdictor does not hold, a cloak or a landing or a port visit drops the well, and a fighter-menu retreat is allowed past an Interdictor Cruiser. Sources are in `src/tw2k/engine/combat.py` (`hull_interdict_reason`, `retreat_block`).

The ordered run, with setup, keys, and turn and credit estimates, is `docs/plans/live-twgs-run-sheet-v1.md`. Blank results go in `docs/plans/live-twgs-results-template-v1.csv`. Fill a copy of that CSV. `python3 scripts/live_queue_proposals.py` prints a dry-run proposal and writes nothing.

| Item | Current value | What to do on live TWGS | What to record | Constant it settles |
|---|---|---|---|---|
| Ferrengi kill experience | Assault trader 50, battle cruiser 100, dreadnought 150 | Kill one of each hull with a good trader (alignment above 0) and again with a neutral or evil trader. Read experience before and after. | The experience change for each hull, and whether alignment changed the award | `FERRENGI_XP_BY_HULL` |
| Ferrengi alignment on a kill | +10, and only when alignment is already above 0 | Same three kills. Read alignment before and after. | The alignment delta for a good trader and for a neutral or evil trader | `FERRENGI_ALIGN_ON_KILL` |
| Ferrengal quasar | 10,000 fuel at 10% (333 damage). Does not burn a planet's ore | Enter the Ferrengal sector in a ship with known shields and fighters. Do not land. | The quasar line: damage, fuel burned if shown, and the planet's sector percent and ore if a scan shows them | `FERRENGAL_QUASAR_FUEL`, `FERRENGAL_QUASAR_PCT` |
| Ferrengi banding cutoff | Bands when the target has more fighters than this Ferrengi, and another Ferrengi is in that sector or one hop out | Watch two Ferrengi near a trader who has more fighters than one of them and fewer than the other. | Whether the weaker ship steps into the trader's sector, and the fighter counts on all three | `FERRENGI_BAND_STRONG` |
| Ferrengi attack clock | A pace hop only relocates. The tribute menu opens on the day tick | Sit still in one sector until a Ferrengi hops in. Stay for the rest of the day. | Whether the Flee / Attack / Surrender menu appears on the hop, or only after midnight | `FERRENGI_PACE_MODE` attack timing |
| Plotted course limit | 45 hops when `COURSE_MAX_MODE` is live | From the computer, plot a course you know is longer than 45 hops, and one of 45 or fewer. | The refusal text, or the plotted length, and the General Editor "Maximum Course Length" value | `V311_COURSE_MAX_HOPS` |
| Death delay maximum | Any whole number of days. No ceiling in the code | In TEDIT, open Death Delay and try 0, 1, 2, and the largest number the field accepts. | The highest accepted value, and the message if it refuses | `GameConfig.death_delay` |
| Flying pod sentence | A pod that is already flying does not start a death-delay sentence when it is destroyed | With death delay at 1 or more, lose a ship, wait out the sentence so the pod can move, then lose the pod. Repeat with death delay at 0. | Whether a new sentence starts, and how many midnights | `death_delay_days` |
| Ship-odds loss split | Attacker loses `ceil(R / A)` when `P >= R`, else the defender loses `floor(P / D)` | In a Missile Frigate (odds 1.3) send 100 fighters at a Merchant Cruiser (1.0) with a known fighter and shield count. Repeat from a Merchant Cruiser. | Fighters and shields left on both ships | `docs/plans/ship-odds-exchange-v1.md` (no new switch; `RULINGS_v311.md` is not in the repo or an open pull request) |

## Live TWGS test queue (NOTE 98)

Items whose numbers are not settled by a v3.11 source. Run each one on Ben's server with a new test character. Record the screen text. The constant column is what a later slice may set.

| item | current value | what to do | what to record | constant |
|---|---|---|---|---|
| Port rating and barrage, classes 0-5 and 7-9 | unset. Class 6 stays rating 98, barrage 598 | Attack one port of each class with a ship that can survive a return shot. Read the defensive rating before the shot | The rating, the return-shot number, the fighters you sent, whether the port was destroyed, and the port's size or productivity on that same screen | `PORT_DEFENSE_RATING`, `PORT_LASER_BARRAGE` |
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

GeneralNew.html gives `<` and `>` to quick stats. The v3.11 revision history says the backtrack key is `<` only. The cockpit uses `>` for quick stats and `<` for backtrack, and both commands are also on the Computer menu.

| item | current value | live test | what to record | constant |
|---|---|---|---|---|
| Quick-stats and backtrack keys | `>` quick stats, `<` backtrack | From a prompt, press each key | Which screen opens | the two keys in the cockpit |

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
| Computer menu B | This cockpit's Computer menu uses B for backtrack. The original backtrack key is `<` | On the original TW2002 Computer menu, read the label next to B. Press B. From a prompt, after one move, press `<` | The menu label for B, and whether B and `<` do the same thing | none, cockpit key, not an engine constant |
