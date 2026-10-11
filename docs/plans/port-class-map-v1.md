# port-class-map-v1

A live TWGS v3.34b game numbers ports 1 BBS, 2 BSB, 3 SBB, 4 SSB, 6 BSS, 7 SSS, 8 BBB, 9 StarDock, 0 Sol. This copy has class 1 as BSS and class 6 as BBS. The sector-1 StarDock trades no goods. The live StarDock buys fuel, organics, and equipment.

`PORT_CLASS_MAP_MODE` defaults to `legacy`. Class 1 stays BSS, class 6 stays BBS, and StarDock still has no commodity book, so the pin and the scripted digests stay put.

`live` swaps those two letters and gives the sector-1 StarDock a buy-all book. The stock comes from its own random stream, so later ports keep the same sizes. Sector 1 stays the StarDock. Its class number stays 8.

Class 7 stays BBB. Live class 7 is SSS, and live class 8 is a normal port that buys all three. Class 8 cannot be that normal port while it is also the StarDock id. That move waits for `stardock-sector-v1`. Class 0 still trades no commodities. Sol does not either. The Sol name and the hardware counter in sector 1 wait with the sector move. Class 9 stays the built SSS port. Live class 9 is the StarDock. Class 5 was not seen live and stays SBS.

Do not turn the switch on until Ben says so.

Suite on 6ee5d69: 2489 passed, 2 failed, 1 skipped, 3074s. Both failures are the known flakes (WinError 10048 and the spectator-feed timeout). Four new tests passed. pb1 and pb2 were re-broken and restored.

10-day seed 250925 digest 24863a3d and seed 4242 digest 98a47c8a, both rejected 0/0, both the same as the runs on b4d57f9. 30-day seed 250925 digest 86a15277. N3 3,390,327, N2 1,106,844, and H 529,130 rejected 0/0. N1 1,441,461 had one engine reject (0/1). Exceptions 0. 30-day seed 4242 digest b274e3d1. N3 2,071,033, N2 768,667, N1 632,729, H 74,827, all rejected 0/0, exceptions 0. The flag stayed legacy.
