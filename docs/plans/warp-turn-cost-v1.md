# warp-turn-cost-v1

A warp costs that hull's turns per warp. On the tw2002 ship table a merchant cruiser is 3 and a freighter is 2. A scout is 2.

That is already what the engine charges. `WARP_COST_MODE` defaults to `legacy` and `live` names the same numbers, so the pin and the scripted games stay put.

The flat fallback of 2 is only for a hull with no table row.

Do not expect a different game when the switch is on.
