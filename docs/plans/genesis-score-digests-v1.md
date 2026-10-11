# genesis-score-digests-v1

genesis-score-v1 shipped the fair-score switch and never wrote down the scripted games. `GENESIS_SCORE_MODE` is still `legacy`, so these games are that off path. No engine change.

Run on 575d5ac, flag off.

10-day seed 250925 digest 24863a3d, rejected 0/0. Citadel {"P1": [2, 2, 2, 0], "P2": [0], "P3": [1]}.
10-day seed 4242 digest 98a47c8a, rejected 0/0. Citadel {"P1": [2, 0], "P2": [0], "P3": [2]}.
30-day seed 250925 digest 86a15277. N3 3,390,327 0/0, N1 1,441,461 0/1, N2 1,106,844 0/0, H 529,130 0/0. Exceptions 0. Citadel {"P1": [5, 3, 2, 0], "P2": [0, 0], "P3": [3, 0]}.
30-day seed 4242 digest b274e3d1. N3 2,071,033, N2 768,667, N1 632,729, H 74,827, all rejected 0/0. Exceptions 0. Citadel {"P1": [3, 2, 2, 1], "P2": [0], "P3": [3]}.

These are the same digests the later slices already matched with the switch off.

Batch A gate on 5dfc4d2: suite 2514 passed, 2 failed, 1 skipped, 3340s. Both failures are the known flakes (WinError 10048 and the spectator-feed timeout). The six plants from assign-colonists, hold-rules, and planet-nw were re-broken and restored. The 30-day games above are the gate games.
