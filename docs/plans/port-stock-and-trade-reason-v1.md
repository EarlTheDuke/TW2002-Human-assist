# Port stock and trade reasons

`PORT_STOCK_FIDELITY_MODE` stays `legacy`. `PORT_OPEN_STOCK_MODE` stays `legacy` too. Ben decides any later default flip.

`live` (or the live profile) opens a selling side at its maximum and a buying side at current 0, so the room is the maximum. A quiet day puts 5% of the maximum back on a selling side, capped at the maximum. That 5% is `PORT_REGEN_PER_DAY`. On a buying side the same day moves current toward 0, so the room grows. It does not shrink the room. A trade still moves one unit per unit. One visit still cannot move more than the maximum.

Prices stay on the existing stock fraction. A full seller and a hungry buyer already sit at opposite ends of that curve.

The old lumped sentence stays on the legacy path, and the trade action gains no `why` key while the flag is off. With the flag on, each commodity that cannot trade names its own cause.

The cockpit, behind `COCKPIT_LAYOUT=redesign`, reads those causes from the port table. Status shows current/max when the port is selling and room left when it is buying. A price that cannot trade is grey, and a tap repeats the reason. `/bot` without the layout flag is unchanged.

A test game turns the flag on with `TW2K_PORT_STOCK_FIDELITY=live` or `serve --port-stock-fidelity live`.
