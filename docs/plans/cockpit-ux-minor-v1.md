# cockpit-ux-minor-v1

Game 8 leftovers on the human screen. No engine path changes.

Already on the tip, so left alone: warp buttons already show the turn cost, the route is the shortest known path, one-way hops are marked, organics at the 9,999 sentinel already say they are holding, and the assign-colonists button already reads ASSIGN COLONISTS.

This slice:

- A price under the port's buy quote says "under the port price". A price over its sell quote says "over the port price". Neither says "N% off list" or "settle at list". A refused offer can counter and still costs the turn.
- The port column is "Stock / room". Goods the port sells show on hand. A port that buys from you shows the room it has left, as `room` after `current / max`.
- The yard list and the ship card add the genesis cap from the TW2002 ship chart.
- The hold button remembers the slot in this tab. Reloading does not post to `/hold`, so it does not end the slot or spend a turn. The button says so.
- Suggested-move text no longer shows `goal_short` or "Action hint (server)" when a hint still contains them.
