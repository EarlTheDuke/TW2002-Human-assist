# action-result-v1

Game 5 showed two holes that make a seat trust the wrong answer.

The action API answered `accepted: true` as soon as the move was queued. The engine could then reject it. The only place the rejection showed up was the event feed. `POST /hold` is an AI helper and stays.

A plotted route with execute flew every hop, added those turns on the clock, and then told the caller it spent 0. The legality line still names the first hop, because the route is not known until a target is given. The result of the execute is what was hiding the cost.

`ACTION_RESULT_MODE` defaults to `legacy`. Nothing in that answer changes, so the pin stays `9b607d3dae940c0b1a69f6d7` and the scripted digests do not move.

`report` does two things. The action POST still says `accepted: true` (the move was queued) and adds `result` with `ok`, `rejected`, `error`, and `turns_spent`. A plotted route hands the hop total back to the outer turn counter, which adds it once, so the ship spends the same turns and the result names them.

Do not turn the switch on until Ben says so.
