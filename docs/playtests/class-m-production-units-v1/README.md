# class-m-production-units-v1 (COMMANDER NOTE 64)

Engine change only where `class_m_fidelity_live()` is true (CLASS_M_FIDELITY_MODE live, V311_PROFILE
or the live profile). Profile off is the old game.

Class M under that switch stores people (191,000 at start, citadel L1 needs 1,000,000). Production,
fighters and growth used to divide the raw people count, so class M made 1,000 times the original.
They now count each product pool in thousands (Ben's NOTE 19: "production is colonists(1000s)/ratio"):

* 1,500,000 fuel people make 500 fuel and 50 fighters a day; with 700,000 organics people, 500 fuel,
  100 organics and 60 fighters (the S1 example).
* The 191,000 start on fuel makes 63 fuel and 6 fighters a day.
* Output stops at the S1 class M Max/Day (5,000 / 2,142 / 1,153 and 829 fighters), reached at
  15,000 thousand per pool. S1 publishes no bell-curve shape, so output stays at that peak above it.
* A pool below 15,000 thousand grows about 5% a day (the rate is not published). A pool above half
  does not shrink; only people above the 30,000 thousand pool cap die back.

Screens (taken by `tests/test_class_m_production_units_v1.py`, redesign cockpit with the class M,
production and growth switches on):

* `1920-planet.png`, `390-planet.png` - the planet card: Fuel Ore 500 per day, Organics 100 per day,
  Fighters 60 per day, all from the server, and "2,200,000 (i.e. 2,200 thousands)".
