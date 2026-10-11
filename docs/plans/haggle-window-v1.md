# haggle-window-v1

A live TWGS v3.34b session took a sell at about +3% to +8% over the opening bid, and a buy at about -3% to -8% under the opening ask. A sell at 137% ended the trade. About 85% of an ask was still answered, with an insult, and the port kept talking. This copy pays a hidden 110% to 149% that grows with MCIC, in one shot.

`HAGGLE_WINDOW_MODE` defaults to `legacy`. That chart stays, so the pin and the scripted digests stay put. A refused counter still costs one turn on both settings. That turn is the original rule. It is not changed.

`live` takes a one-shot counter only inside a flat +8% / -8% band. The far edge is 108, so a buy floor is 92 (200 - 108). A sell past 130 is the wild bid from the session, and it ends the trade the same way. Offers between the band and that wild bid also end the trade here. The live port countered those by 1% to 4% a round and kept the deal open. Those rounds are not built. One sell the notes called 108% was 3,600 on an opening of 3,326, which is 8.2%. A flat 108 can miss that receipt by a few credits. The exact edge was not probed, so the band was not widened to fit it.

Do not turn the switch on until Ben says so.

Suite on 182bfa2: 2494 passed, 2 failed, 1 skipped, 3045s. Both failures are the known flakes (WinError 10048 and the spectator-feed timeout). Two new tests passed. pb1 and pb2 were re-broken and restored.

10-day seed 250925 digest 24863a3d and seed 4242 digest 98a47c8a, both rejected 0/0, both the same as the runs on 0c36636. 30-day seed 250925 digest 86a15277. N3 3,390,327, N2 1,106,844, and H 529,130 rejected 0/0. N1 1,441,461 had one engine reject (0/1). Exceptions 0. 30-day seed 4242 digest b274e3d1. N3 2,071,033, N2 768,667, N1 632,729, H 74,827, all rejected 0/0, exceptions 0. The flag stayed legacy.
