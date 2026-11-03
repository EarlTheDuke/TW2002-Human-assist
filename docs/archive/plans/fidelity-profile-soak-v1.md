# fidelity-profile-soak-v1

`TW2002_LIVE_PROFILE` stays `legacy`. This run turned it on only for the match.

## What broke

A scripted day called `tick_day` and expected a fresh turn count. With the live profile on, a new day does not refill turns: the server gives them back by the hour. The headless match spent day 1, then every later day was already out of turns. Thirty days finished in about 11 seconds. Net worth never moved after the opening. No exceptions.

The script now treats the day boundary as that hour, and only when the live opening or the hourly turn clock is on. The legacy path still refills inside `tick_day`. The stored profile is still `legacy`.

## 30 days, profile on, seeds 250925 and 4242

No crashes. No exceptions. Rejected 0/0 on both seeds. About 12 minutes for 30 simulated days.

Seed 250925, digest `4cd0b8f9`. H 46,590 (2 sells). N2 42,630. N1 42,350. N3 32,670 on a CargoTran. All alive. The numbers stop changing on day 2.

Seed 4242, digest `1c3d87d6`. H 132,810 (101 sells) through day 2, then flat. N2 43,590. N3 32,295 on a CargoTran. N1 died on day 1 and sat in an escape pod at 5,100.

The legacy 30-day pair is still `86a15277` / `b274e3d1`, with net worth in the hundreds of thousands to the millions. The live-profile games stay near the opening stake.

## Why they stop

The profile turns on one-way lanes and dead ends. The code bots warp into a sector with no way out (seed 250925, sector 61, zero warps) and then pass the rest of their turns. That is the map the flag asked for, not a crash. They do not buy a way out.

## Regression

`tests/test_fidelity_profile_soak_v1.py`: profile on, 10 days, seed 250925, no exceptions, every seat warps, every seat plays past the first day. The test puts the profile back to `legacy`.

Bank pin `9b607d3dae940c0b1a69f6d7`. Legacy 10-day digests stay `24863a3d` and `98a47c8a`, rejected 0/0.
