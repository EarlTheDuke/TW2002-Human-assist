# own-planet-turn-v1

Landing costs 3 turns and lifting off costs 1. On the live server, landing on a planet you already own and then lifting off cost 1 turn total, and that turn was taken on liftoff.

`OWN_PLANET_TURN_MODE` defaults to `legacy`. Landing still costs 3 and lifting off still costs 1, so the pin and the scripted digests stay put.

`live` makes the landing free when the planet is already yours. Lifting off still costs 1. A planet you do not own stays at 3 plus 1. A corp mate's planet was not measured, so it stays at 3 plus 1 too.

When the sector has any planet that is not yours, the landing menu still shows 3, because one menu covers every planet there. The landing itself is free only for the planet you already own.

Do not turn the switch on until Ben says so.

Suite on 19ba88e: 2506 passed, 2 failed, 1 skipped, 3042s. Both failures are the known flakes. Three new tests passed. pb1 and pb2 re-broken and restored. With the flag off, 10-day seed 250925 digest 24863a3d and seed 4242 digest 98a47c8a, rejected 0/0, same as 460b2a9. 30-day seed 250925 digest 86a15277, N1 one engine reject. 30-day seed 4242 digest b274e3d1, rejected 0/0.
