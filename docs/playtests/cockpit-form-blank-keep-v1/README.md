# cockpit-form-blank-keep-v1 (COMMANDER NOTE 62)

Redesign cockpit only (`COCKPIT_LAYOUT=redesign`); `/bot` legacy is unchanged.

Every 2 seconds the cockpit rebuilds the open form from fresh game state. Before this fix a box the
player had cleared got its default back on the next rebuild (Bank: the 500,000 room within 2 s), so
CONFIRM moved money the player had not asked for. Now any box the player has typed in, deleted from
or cleared keeps exactly what the player left there, including an empty box, for as long as the
form stays open. Opening the form again is the only thing that brings the default back. An empty
amount answers "Type an amount." and sends nothing.

Screens (taken by `tests/test_cockpit_form_blank_keep_v1.py` after the box was cleared and 6.5 s,
more than 3 refreshes, had passed, then CONFIRM pressed):

* `1920-bank-blank.png`, `390-bank-blank.png` - StarDock Bank, amount empty, "Type an amount."
* `1920-fighters-blank.png`, `390-fighters-blank.png` - Take/Leave Fighters, "leave in sector" empty.
* `1920-trade-blank.png`, `390-trade-blank.png` - Port trade with qty 5 and the haggle offer cleared;
  side and commodity stay as they were.
* `1920-jettison-blank.png`, `390-jettison-blank.png` - Jettison cargo, quantity empty.
