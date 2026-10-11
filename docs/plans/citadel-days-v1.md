# citadel-days-v1

A live TWGS v3.34b screen said a class M level 1 citadel needs 1,000,000 colonists, 300 fuel, 200 organics, 250 equipment, and 4 days, with no credit cost. This copy already charges those goods and no credits. It scales the day table by 0.25, so 4 days become 1. The S1 table says 1,000 colonists. The screen said 1,000,000. That colonist count is a SOURCE-CONFLICT and is not changed.

`CITADEL_DAYS_MODE` defaults to `legacy`. The 0.25 scale stays, so the pin and the scripted digests stay put.

`live` uses the raw day count from the table. A class M level 1 takes 4 days. The colonist requirement stays 1,000 until Ben picks 1,000 or 1,000,000.

Do not turn the switch on until Ben says so.

Suite on 1c16d47: 2498 passed, 2 failed, 1 skipped, 3040s. Both failures are the known flakes (WinError 10048 and the spectator-feed timeout). Two new tests passed. pb1 and pb2 were re-broken and restored.

10-day seed 250925 digest 24863a3d and seed 4242 digest 98a47c8a, both rejected 0/0, both the same as the runs on 9f2b3c3. 30-day seed 250925 digest 86a15277. N3 3,390,327, N2 1,106,844, and H 529,130 rejected 0/0. N1 1,441,461 had one engine reject (0/1). Exceptions 0. 30-day seed 4242 digest b274e3d1. N3 2,071,033, N2 768,667, N1 632,729, H 74,827, all rejected 0/0, exceptions 0. The flag stayed legacy.
