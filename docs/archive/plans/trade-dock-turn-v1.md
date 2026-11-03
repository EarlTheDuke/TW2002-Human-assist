# trade-dock-turn-v1

Docking costs 1 turn. Later deals in that sector cost none. Leaving the sector starts a new dock.

That rule is already what the engine does. The old gap line that said 3 turns per trade is stale. `TRADE_TURN_MODE` defaults to `legacy` and `live` names the same rule, so the pin and the scripted games stay put.

Do not expect a different game when the switch is on.

Tier S on 595f901: two tests pass, planted bugs failed the free-deal and the one-turn tests and were restored, the bank pin stayed 9b607d3dae940c0b1a69f6d7, and the 10-day games stayed 24863a3d and 98a47c8a with rejected 0/0.
