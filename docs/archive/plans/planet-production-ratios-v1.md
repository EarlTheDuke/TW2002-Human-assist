# planet-production-ratios-v1

2026-10-11. `PLANET_PROD_MODE` stays `legacy`.

Live uses the S1 colonists-per-unit table. Class M is 3, 7, and 13. The handbook example holds: 1,500 colonists on fuel make 500 fuel, and 700 on organics make 100. Class H makes no organics. Class U makes nothing.

Below half the class cap, population still grows 5 percent when organics are in stock. Above half, that same 5 percent is a die-off. The handbook called the output a bell that peaks at half. It did not give a second formula, and the 500-fuel example is the plain ratio, so this switch does not scale the product again.

Off, a day still makes units per 100 colonists and does not shrink the population.

Tier S on 863990e: four tests pass, planted bugs failed the 500-fuel day and the die-off and were restored, the bank pin stayed 9b607d3dae940c0b1a69f6d7, and the 10-day games stayed 24863a3d and 98a47c8a with rejected 0/0.
