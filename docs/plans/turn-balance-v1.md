# Turn balance for a full-length game (NOTE 93)

Measured 2026-10-19 on `feature/grokbot-player` tip `ea4cfffb` plus this slice, under `V311_PROFILE=v311`.

## What was run

Headless scripted games, 30 days, 1,000 sectors, Ferrengi on, `play_to_day_cap` so a win does not stop the clock. Seeds 250925 and 4242. Turns per day 250, the classic pocket (cabal glossary, "Classic": 1,000 sectors, 250 turns per day; GAP_MAP 9.1: the daily turn count is a sysop setting).

Lineup: code bots N3, N2, N1 and the heuristic H. Each of those seats spends the whole pocket every day. A second run adds a fifth seat, another H, that stops after a 40-turn sitting and then idles until the next day. Forty turns is a stand-in for one short session, not a measured human log. The length is UNVERIFIED.

The scripted harness holds the wall clock still and refills the pocket at the day boundary (`scripts/run_scripted_match.py`). That is the same count as "spent every turn that the day allowed," and it is not the hourly trickle. RULINGS s5, already live under the v3.11 profile, pays turns back across the real day and caps them at the allowance, with no midnight refill. The tables below are the scripted refill. The clock section says what the hourly rule changes.

Opening cash in these runs is the script's 20,000, not the v3.11 lobby pocket of 300. The turn counts do not depend on that cash. Absolute net worth would be lower from a 300-credit start.

## Turns used and turns left at the cap

A seat that plays the whole day uses 250 and leaves 0. The same number on day 1, day 10, day 20 and day 30, both seeds, all four full seats.

The short sitting uses 41 or 42 (one action can step past the 40-turn stop) and leaves 208 or 209. Over 30 days that seat played about 1,250 turns and left about 6,260 at the cap. A full seat played 7,500.

| Seed | Seat | Turns used / day | Left at the cap / day | Turns played in 30 days |
|---|---|---:|---:|---:|
| both | N3, N2, N1, H | 250 | 0 | 7,500 |
| 250925 | H short sitting (P5) | 41–42 | 208–209 | ~1,250 (6,273 left at the cap) |
| 4242 | H short sitting (P5) | 41–42 | 208–209 | ~1,250 (6,257 left at the cap) |

## Experience and net worth, full seats

Every full seat spent the same 250. The spread is the brain, not the turn pocket.

Seed 250925:

| Seat | Day 10 XP | Day 10 net worth | Day 20 XP | Day 20 net worth | Day 30 XP | Day 30 net worth |
|---|---:|---:|---:|---:|---:|---:|
| N3-P1 | 273 | 111,656 | 396 | 174,216 | 427 | 201,016 |
| N2-P2 | 201 | 105,064 | 213 | 124,160 | 225 | 152,820 |
| N1-P3 | 146 | 603,757 | 156 | 978,067 | 166 | 1,177,355 |
| H-P4 | 428 | 103,650 | 809 | 73,639 | 1,293 | 70,724 |

Seed 4242:

| Seat | Day 10 XP | Day 10 net worth | Day 20 XP | Day 20 net worth | Day 30 XP | Day 30 net worth |
|---|---:|---:|---:|---:|---:|---:|
| N3-P1 | 261 | 126,666 | 277 | 123,486 | 133 | 41,506 |
| N2-P2 | 103 | 95,968 | 113 | 95,968 | 129 | 91,213 |
| N1-P3 | 136 | 84,545 | 190 | 95,845 | 357 | 115,699 |
| H-P4 | 477 | 54,922 | 1,162 | 62,747 | 1,807 | 62,308 |

N3 on seed 4242 is in a scout marauder by day 28 with 0 credits and about half the day-20 experience. That is a ship loss, not a turn shortage. N1 on seed 250925 holds most of the wealth while sitting on the lowest experience of the four. Experience and net worth are not the same race.

## How far a one-session seat falls behind

Same heuristic, same seeds. P4 spends 250. P5 spends about 41.

| Seed | Day | Full H experience | Short H experience | Full H net worth | Short H net worth |
|---|---:|---:|---:|---:|---:|
| 250925 | 10 | 430 | 75 | 106,505 | 63,710 |
| 250925 | 20 | 841 | 184 | 87,032 | 64,848 |
| 250925 | 30 | 1,313 | 266 | 78,766 | 63,966 |
| 4242 | 10 | 477 | 67 | 54,922 | 58,390 |
| 4242 | 20 | 1,162 | 166 | 62,747 | 54,078 |
| 4242 | 30 | 1,807 | 230 | 62,308 | 51,213 |

Experience stays near the turn ratio, about one fifth to one eighth of the full seat. Net worth does not. By day 30 the short seat still holds roughly 80% of the full heuristic's net worth, and on seed 4242 it was slightly ahead at day 10. Among seats that all spend 250, N1's day-30 net worth on seed 250925 is about 16 times the heuristic's. The brain gap is wider than the session gap on wealth. The session gap is the one that shows up in experience and in turns left at the cap.

## Hourly regen, and a 10-minute test day

RULINGS s5 (v3.11 profile, `turn_regen_live`): turns come back across the day, pro-rated from the allowance, and they stop at the cap. A new day does not hand the pocket back in one lump.

On a real day of 86,400 seconds and a pocket of 250, a turn comes back about every 5.8 minutes. A seat that is online all day spends the allowance as it returns, and also spends the opening bank on day 1, so day 1 is about 500 turns and every later day is about 250. The scripted table counts 250 every day, including day 1. The missing piece is that one extra opening-day regen, 250 turns, small next to the 6,000-turn hole of a 40-turn sitting.

A seat that logs in once, empties a full bank of 250, and leaves, then sits offline while the cap refills, spends the same 250 the next day. Waste is about 0. The seat that falls behind is the one that does not empty the bank.

NOTE 68's fast test day is 10 minutes (600 seconds). A turn then comes back every 2.4 seconds, which is why the lobby day hint says turns rarely run out. A person who sits for that whole 10 minutes is present for the entire day and can spend the same 250 a bot spends. The scripted turn totals would match the 24-hour table, because both grant one pocket per day to a seat that stays. The 24-hour day is the one that punishes a short sitting: 30 minutes of wall clock returns about 5 turns, so the only turns they get are the ones already in the bank.

## Three options

1. **Per-game turns per day.** Shipped in this slice. Original stays 250 and is omitted from the save, so today's games do not move. 500, 1,000, or a custom 50–5,000 replaces the pocket for every seat. Source: the classic 250 is a game setting (cabal glossary "Classic"; GAP_MAP 9.1, turns are sysop-set), not a rule baked into the engine. Effect on these numbers: a larger pocket helps a sitting that would have spent more than 250 before the clock ran out. It does not pay back hours the seat was offline. A 40-turn sitting against a 1,000 cap leaves 960 at the cap instead of 210, so the absolute gap against a full-time seat gets wider.

2. **Keep the daily bank cap, and do not add a tighter one.** RULINGS s5 already stops the bank at the day's allowance. A once-a-day player who empties that bank keeps up on turns. A tighter cap (a few hours of regen, not the whole day) is not in the original, and it would be what makes a single daily login fall behind even when the player spends every banked turn. Leave the cap where s5 put it.

3. **Catch-up turns for a seat that was offline.** No source in the original. s5 says the hours you missed are not paid later. Paying them in a lump when the seat opens would hand the 40-turn sitting the other 210 and erase the experience gap in the table above. It would also let that sitting out-spend a seat that was online all day, if the lump arrives on top of the same-day regen. Leave it off unless a game asks for it as its own setting.
