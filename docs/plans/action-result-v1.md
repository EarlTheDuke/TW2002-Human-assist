# action-result-v1

Game 5 showed two holes that make a seat trust the wrong answer.

The action API answered `accepted: true` as soon as the move was queued. The engine could then reject it. The only place the rejection showed up was the event feed. `POST /hold` is an AI helper and stays.

A plotted route with execute flew every hop, added those turns on the clock, and then told the caller it spent 0. The legality line still names the first hop, because the route is not known until a target is given. The result of the execute is what was hiding the cost.

`ACTION_RESULT_MODE` defaults to `legacy`. Nothing in that answer changes, so the pin stays `9b607d3dae940c0b1a69f6d7` and the scripted digests do not move.

`report` does two things. The action POST still says `accepted: true` (the move was queued) and adds `result` with `ok`, `rejected`, `error`, and `turns_spent`. A plotted route hands the hop total back to the outer turn counter, which adds it once, so the ship spends the same turns and the result names them.

Do not turn the switch on until Ben says so.

Suite on b911c77: 2480 passed, 2 failed, 1 skipped, 3051s. Both failures are the known flakes (WinError 10048 and the spectator-feed timeout). Five new tests passed. pb1 and pb2 were re-broken and restored.

10-day seed 250925 digest 24863a3d and seed 4242 digest 98a47c8a, both rejected 0/0, both the same as the runs on fa2a821. 30-day seed 250925 digest 86a15277. N3, N2, and H rejected 0/0. N1 had one engine reject (0/1). Exceptions 0. Same path as fa2a821. 30-day seed 4242 digest b274e3d1 is the first measurement of that seed on this path. N3 2,071,033, N2 768,667, N1 632,729, H 74,827, all rejected 0/0, exceptions 0.
