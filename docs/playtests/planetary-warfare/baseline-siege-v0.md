# Baseline siege table (today's rules)

Recorded after the siege-gap fixes (`27be2ed` and earlier). Citadel level 2. Attacker shields 0. 30 seeds per cell. The combat dice are reseeded 0 through 29 on one universe, then `land_planet` runs. Reaction and quasar are not in this run.

A planet with 0 fighters is captured every time, including at 200 shields. The attacker loses no fighters on those landings. Shields do not stop the landing by themselves.

No cell in this grid was repelled. Each fight ended as a capture or with the attacker's ship destroyed. When both sides reach 0 fighters in the same round, the result is the attacker destroyed. Equal fighter counts at 0 shields capture 30.0% of the time (100 vs 100, 1000 vs 1000, and 10000 vs 10000). Planet shields in this range change that only when they are a real share of the attacker's volley: 100 vs 100 falls from 30.0% at 0 shields to 0.0% at 50 shields, while 10000 vs 10000 only falls from 30.0% to 26.7% at 200 shields.

An attacker with about ten times the planet's fighters captures every cell in this grid. Mean fighters left is 0 when the ship is destroyed. The engine then respawns that ship; the table does not count the fresh fighter load.

Citadel level 2. Attacker shields 0. 30 seeds per cell (combat dice reseeded 0..29).

| Planet fighters | Planet shields | Attacker fighters | Capture | Repelled | Attacker destroyed | Mean fighters left |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 100 | 100.0% | 0.0% | 0.0% | 100.0 |
| 0 | 10 | 100 | 100.0% | 0.0% | 0.0% | 100.0 |
| 0 | 50 | 100 | 100.0% | 0.0% | 0.0% | 100.0 |
| 0 | 200 | 100 | 100.0% | 0.0% | 0.0% | 100.0 |
| 100 | 0 | 100 | 30.0% | 0.0% | 70.0% | 2.6 |
| 100 | 10 | 100 | 10.0% | 0.0% | 90.0% | 1.5 |
| 100 | 50 | 100 | 0.0% | 0.0% | 100.0% | 0.0 |
| 100 | 200 | 100 | 0.0% | 0.0% | 100.0% | 0.0 |
| 1000 | 0 | 100 | 0.0% | 0.0% | 100.0% | 0.0 |
| 1000 | 10 | 100 | 0.0% | 0.0% | 100.0% | 0.0 |
| 1000 | 50 | 100 | 0.0% | 0.0% | 100.0% | 0.0 |
| 1000 | 200 | 100 | 0.0% | 0.0% | 100.0% | 0.0 |
| 10000 | 0 | 100 | 0.0% | 0.0% | 100.0% | 0.0 |
| 10000 | 10 | 100 | 0.0% | 0.0% | 100.0% | 0.0 |
| 10000 | 50 | 100 | 0.0% | 0.0% | 100.0% | 0.0 |
| 10000 | 200 | 100 | 0.0% | 0.0% | 100.0% | 0.0 |
| 0 | 0 | 1000 | 100.0% | 0.0% | 0.0% | 1000.0 |
| 0 | 10 | 1000 | 100.0% | 0.0% | 0.0% | 1000.0 |
| 0 | 50 | 1000 | 100.0% | 0.0% | 0.0% | 1000.0 |
| 0 | 200 | 1000 | 100.0% | 0.0% | 0.0% | 1000.0 |
| 100 | 0 | 1000 | 100.0% | 0.0% | 0.0% | 896.9 |
| 100 | 10 | 1000 | 100.0% | 0.0% | 0.0% | 896.9 |
| 100 | 50 | 1000 | 100.0% | 0.0% | 0.0% | 896.9 |
| 100 | 200 | 1000 | 100.0% | 0.0% | 0.0% | 896.9 |
| 1000 | 0 | 1000 | 30.0% | 0.0% | 70.0% | 24.9 |
| 1000 | 10 | 1000 | 26.7% | 0.0% | 73.3% | 23.5 |
| 1000 | 50 | 1000 | 23.3% | 0.0% | 76.7% | 18.8 |
| 1000 | 200 | 1000 | 10.0% | 0.0% | 90.0% | 10.7 |
| 10000 | 0 | 1000 | 0.0% | 0.0% | 100.0% | 0.0 |
| 10000 | 10 | 1000 | 0.0% | 0.0% | 100.0% | 0.0 |
| 10000 | 50 | 1000 | 0.0% | 0.0% | 100.0% | 0.0 |
| 10000 | 200 | 1000 | 0.0% | 0.0% | 100.0% | 0.0 |
| 0 | 0 | 10000 | 100.0% | 0.0% | 0.0% | 10000.0 |
| 0 | 10 | 10000 | 100.0% | 0.0% | 0.0% | 10000.0 |
| 0 | 50 | 10000 | 100.0% | 0.0% | 0.0% | 10000.0 |
| 0 | 200 | 10000 | 100.0% | 0.0% | 0.0% | 10000.0 |
| 100 | 0 | 10000 | 100.0% | 0.0% | 0.0% | 9896.9 |
| 100 | 10 | 10000 | 100.0% | 0.0% | 0.0% | 9896.9 |
| 100 | 50 | 10000 | 100.0% | 0.0% | 0.0% | 9896.9 |
| 100 | 200 | 10000 | 100.0% | 0.0% | 0.0% | 9896.9 |
| 1000 | 0 | 10000 | 100.0% | 0.0% | 0.0% | 8965.3 |
| 1000 | 10 | 10000 | 100.0% | 0.0% | 0.0% | 8965.3 |
| 1000 | 50 | 10000 | 100.0% | 0.0% | 0.0% | 8965.3 |
| 1000 | 200 | 10000 | 100.0% | 0.0% | 0.0% | 8965.3 |
| 10000 | 0 | 10000 | 30.0% | 0.0% | 70.0% | 247.6 |
| 10000 | 10 | 10000 | 30.0% | 0.0% | 70.0% | 246.0 |
| 10000 | 50 | 10000 | 30.0% | 0.0% | 70.0% | 239.7 |
| 10000 | 200 | 10000 | 26.7% | 0.0% | 73.3% | 224.6 |
