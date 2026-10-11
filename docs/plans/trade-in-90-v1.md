# trade-in-90-v1

The live yard quoted a trade-in as about 90 percent of each part. A pod's lines added to 16,829. A Scout's lines added to 18,571, and the holds alone were more than half. A Merchant Cruiser with 30 holds was offered 44,932, which was more than its sticker. This copy pays 25 percent of the hull sticker and never hands back a surplus.

`TRADE_IN_MODE` defaults to `legacy`. That 25 percent and the kept surplus stay, so the pin and the scripted digests stay put. A pod still buys a Scout for nothing on that path.

`live` pays 90 percent of the hull sticker. When that credit is larger than the next hull, the difference is paid in cash. A pod counts as a Scout's hull, same as today, so the percent applies to the Scout sticker.

The live lines also name holds, drive, computer, fighters, shields, and a scanner. Only two receipts were written down. No price formula for those parts was published, so this slice does not invent one. Extra holds still add nothing.

Do not turn the switch on until Ben says so.

Suite on 0a0c7cd: 2492 passed, 2 failed, 1 skipped, 3069s. Both failures are the known flakes (WinError 10048 and the spectator-feed timeout). Three new tests passed. pb1 and pb2 were re-broken and restored.

10-day seed 250925 digest 24863a3d and seed 4242 digest 98a47c8a, both rejected 0/0, both the same as the runs on f99ee10. 30-day seed 250925 digest 86a15277. N3 3,390,327, N2 1,106,844, and H 529,130 rejected 0/0. N1 1,441,461 had one engine reject (0/1). Exceptions 0. 30-day seed 4242 digest b274e3d1. N3 2,071,033, N2 768,667, N1 632,729, H 74,827, all rejected 0/0, exceptions 0. The flag stayed legacy.
