# stardock-sector-v1

This slice is a decision. Nothing moves.

On the live server the StarDock sat in a random sector. In that game it was sector 351. Sector 1 was Sol, a class 0 port, plus Terra. The StarDock port bought fuel, organics, and equipment.

This copy keeps `STARDOCK_SECTOR = 1`. That is on purpose. The bots and the scripted games know the dock is in sector 1. Moving it would hide the dock and change every game.

Sector 1 stays the StarDock until Ben says otherwise. There is no new switch, because there is nothing to turn on. Whether the dock buys goods is the older `PORT_CLASS_MAP_MODE` switch, and that one stays `legacy`.

The engine did not change, so the four scripted games stay the ones from 19ba88e.
