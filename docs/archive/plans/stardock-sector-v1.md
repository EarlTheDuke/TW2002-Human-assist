# stardock-sector-v1

Ben approved the Commander recommendation on 2026-10-24. `STARDOCK_LOCATION_MODE` row 236 stays legacy, so a stored game still puts StarDock in sector 1. `V311_PROFILE=v311` places it in a random ordinary sector at generation. Terra stays sector 1. FedSpace is sectors 1-10 plus that sector. The notes below are what this slice recorded before that approval.

This slice was a decision. Nothing moved then.

On the live server the StarDock sat in a random sector. In that game it was sector 351. Sector 1 was Sol, a class 0 port, plus Terra. The StarDock port bought fuel, organics, and equipment.

This copy keeps `STARDOCK_SECTOR = 1` as the stored default. The bots and the scripted games know the dock is in sector 1 until the switch is on. Moving it on a stored game would hide the dock and change every game.

Whether the dock buys goods is the older `PORT_CLASS_MAP_MODE` switch, and that one stays `legacy`.

The engine did not change, so the four scripted games stay the ones from 19ba88e.

Suite on 271f3c2: 2506 passed, 2 failed, 1 skipped, 2945s. Both failures are the known flakes. No new tests and no plants, because the engine did not change.
