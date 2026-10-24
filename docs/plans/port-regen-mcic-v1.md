# port-regen-mcic-v1

2026-10-11. `PORT_REGEN_MODE` stays `legacy`.

Each port already stores its own MCIC and productivity (`universe.py`). A day still adds 5% of that productivity while the switch is off. That is the same path the pin and the two 10-day games use.

Live adds 5% of the max stock per day, and one visit cannot move more than that max. The ports still open empty. Opening them full stays on `PORT_OPEN_STOCK_MODE`, which is a different switch. While `PORT_DRAIN_CURVE_MODE` is on, the same day uses 10% of the maximum instead. That rate is the drain-curve card, not this 5% applied twice.

MCIC stays the number already on the port. This slice does not change prices.

Tier S on 5d85a01: four tests pass, planted bugs failed the live regen and the visit cap and were restored, the bank pin stayed 9b607d3dae940c0b1a69f6d7, and the 10-day games stayed 24863a3d and 98a47c8a with rejected 0/0.
