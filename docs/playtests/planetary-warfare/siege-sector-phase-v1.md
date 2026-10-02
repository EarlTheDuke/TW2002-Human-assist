# Siege sector phase

Recorded from `scripts/planetary_scenario_lab.py --hazards`. The clear column is the odds fight with no sector hazards. Ten armid mines and 100 offensive sector fighters belong to the planet owner. The full odds grid was re-run with a clear sector and still matches `siege-odds-and-reaction-v1.md`.

A ship of 100 fighters dies to 10 armids before it can land, because at least one mine detonates for 100 damage. A ship of 1000 fighters often lives through that and still captures. One hundred offensive sector fighters sometimes stop the 100-fighter ship and do not stop the 1000-fighter ship.

Citadel level 2. Attacker shields 0. Reaction 0. 30 seeds. Mines are armids owned by the planet owner. Sector fighters are offensive and owned by the planet owner.

| Attacker | Planet fighters | Planet shields | Clear capture | 10 mines capture | 100 sector fighters capture |
|---:|---:|---:|---:|---:|---:|
| 100 | 0 | 0 | 100.0% | 0.0% | 66.7% |
| 100 | 100 | 0 | 0.0% | 0.0% | 0.0% |
| 1000 | 0 | 0 | 100.0% | 90.0% | 100.0% |
| 1000 | 100 | 0 | 100.0% | 60.0% | 100.0% |
