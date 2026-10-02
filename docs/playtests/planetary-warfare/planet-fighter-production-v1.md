# Planet fighter production

Recorded from `scripts/planetary_scenario_lab.py --production` after owned planets started minting fighters on the day tick. One product pool at a time, rate 100. A divisor of 0 adds nothing. Class U still makes commodities and makes no fighters. The planet cap is 1,000,000, the same as the original maximum.

1500 fuel colonists on class M make 50 fighters. 700 organics colonists on the same planet add 10.

| Class | Pool | 1000 colonists | 10000 colonists |
|---|---|---:|---:|
| M | fuel_ore | 33 | 333 |
| M | organics | 14 | 142 |
| M | equipment | 7 | 76 |
| K | fuel_ore | 33 | 333 |
| K | organics | 0 | 6 |
| K | equipment | 0 | 1 |
| O | fuel_ore | 3 | 33 |
| O | organics | 33 | 333 |
| O | equipment | 0 | 6 |
| L | fuel_ore | 41 | 416 |
| L | organics | 16 | 166 |
| L | equipment | 4 | 41 |
| C | fuel_ore | 0 | 8 |
| C | organics | 0 | 4 |
| C | equipment | 0 | 0 |
| H | fuel_ore | 20 | 200 |
| H | organics | 0 | 0 |
| H | equipment | 0 | 0 |
| U | fuel_ore | 0 | 0 |
| U | organics | 0 | 0 |
| U | equipment | 0 | 0 |
