# landed-state-v1

Game 8 warped away and left the ship marked landed on a planet nine hops back. The bank and Terra then said to lift off. A warp and an executing plot were also accepted from the surface.

`LANDED_STATE_MODE` stays `legacy`, so that old path and the bank pin stay. `live` drops a landing whose planet is not in this sector, and refuses warp, trade, and an executing plot until the ship lifts off. A plot with the box unchecked still stays put. The liftoff button sends the action itself. It does not open a confirm with nothing to fill in.
