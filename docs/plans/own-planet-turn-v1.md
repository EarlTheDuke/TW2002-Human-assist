# own-planet-turn-v1

Landing costs 3 turns and lifting off costs 1. On the live server, landing on a planet you already own and then lifting off cost 1 turn total, and that turn was taken on liftoff.

`OWN_PLANET_TURN_MODE` defaults to `legacy`. Landing still costs 3 and lifting off still costs 1, so the pin and the scripted digests stay put.

`live` makes the landing free when the planet is already yours. Lifting off still costs 1. A planet you do not own stays at 3 plus 1. A corp mate's planet was not measured, so it stays at 3 plus 1 too.

When the sector has any planet that is not yours, the landing menu still shows 3, because one menu covers every planet there. The landing itself is free only for the planet you already own.

Do not turn the switch on until Ben says so.
