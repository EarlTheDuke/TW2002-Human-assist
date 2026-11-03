# starting-package-v1

A live TWGS Big Bang game opened with 300 credits, 30 fighters, 250 turns, a Merchant Cruiser, 20 holds, and a free class M planet carrying 191,000 colonists and no goods. Turns came back over the wall clock at about 10 to 11 an hour, and a new day did not fill the counter back to 250.

`STARTING_PACKAGE_MODE` defaults to `legacy`. That is still 20,000 credits, 20 fighters, 1,000 turns, no home planet, and a full refill when the day ticks. The pin and the scripted digests stay put.

`live` uses 300 / 30 / 250, skips the ±1,000 credit skew (it is bigger than the whole stake), and grants the class M planet in the seat's start sector. The live planet in the session was 10 hops away, in sector 557. The placement rule was not published, so the start sector is a stand-in. The 191,000 colonists sit in the unassigned pool, because the screen did not say which product they worked, and an empty stock means they do not grow. Class M's colonist cap in this copy is 30,000. The live planet was over that cap. The cap is not changed here.

Turn recovery on `live` adds `elapsed seconds * 250 / 86400`, and it never gives more than a full day. One hour is 10 turns. A day tick does not zero the counter. The login line that showed 26 turns and then a separate recovery is not reproduced. That split was not explained by the transcripts.

Do not turn the switch on until Ben says so.

Suite on bd77254: 2484 passed, 3 failed, 1 skipped, 2929s. Two failures are the known flakes (WinError 10048 and the spectator-feed timeout). The Firefox caption timeout passed alone in 14s. Five new tests passed. pb1 and pb2 were re-broken and restored.

10-day seed 250925 digest 24863a3d and seed 4242 digest 98a47c8a, both rejected 0/0, both the same as the runs on 79100a5. 30-day seed 250925 digest 86a15277. N3, N2, and H rejected 0/0. N1 had one engine reject (0/1). Exceptions 0. 30-day seed 4242 digest b274e3d1, rejected 0/0, exceptions 0. Those scripted runs were on aaa8cad, before the turn-loop import fix. That fix does not run in scripted matches, and the flag stayed legacy.
