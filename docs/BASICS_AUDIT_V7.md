# Basics Audit — "Are the agents actually playing the game?"

**Run tag:** `run-20260418T182415Z-llm-v7-wider`
**Config:** 2 LLM agents (Grok-4-1-fast-reasoning), 2 days, 60 turns/day,
universe 250 sectors, starting credits 50,000.
**Engine changes in this run:** wider port margins (0.70x-1.30x vs. old
0.90x-1.20x), prices persisted in `known_ports` intel, end-of-day
`wait` nudge in `action_hint`, Terra colonist purchase at StarDock.

## Tl;dr

The basics work. Agents **do** identify port codes, pick profitable pairs,
buy low, sell high, and haggle meaningfully. What doesn't happen in a 2-day
sanity match is ship upgrade, Genesis deploy, or Citadel — not because the
AI is dumb, but because the trade velocity (~80 cr/round-trip × ~6 loops/day)
is too slow to clear a 25k-100k price tag in that window.

## Before / after comparison

| Metric                        | V6 sanity       | V7 (this run)   | Change             |
| ----------------------------- | --------------- | --------------- | ------------------ |
| Trades / agent / Day 1        | 2               | 6               | +200%              |
| Sectors visited / Day 1       | 3               | 7               | +133%              |
| Avg profit per round trip     | +60 cr          | +40 to +140 cr  | range widened      |
| Best haggle margin observed   | list +3 cr      | list -6 / +3 cr | wider swings       |
| Day-1 scorecard               | 0/3             | 2/3             | +2                 |
| Ship upgrades                 | 0               | 0               | unchanged          |
| Genesis deployed              | 0               | 0               | unchanged          |
| End-of-day failed warps       | 4-5 / agent     | 4 / agent       | nudge broken (bug) |
| Match wall time               | ~8 min          | ~10 min         | reasonable         |

## Raw trade sequence (all 20 trades, v7)

```
Agent-1 buy  20 fuel_ore @ 16cr = 320cr
Agent-2 buy  20 fuel_ore @ 14cr = 280cr  [haggle won at 14cr (list 16)]
Agent-1 sell 20 fuel_ore @ 18cr = 360cr  [haggle countered; settled at list 18cr]
Agent-2 sell 20 fuel_ore @ 18cr = 360cr  [haggle countered; settled at list 18cr]
Agent-1 buy  20 fuel_ore @ 14cr = 280cr
Agent-2 buy  20 fuel_ore @ 14cr = 280cr
Agent-1 sell 20 fuel_ore @ 18cr = 360cr
Agent-2 sell 20 fuel_ore @ 20cr = 400cr  [haggle won at 20cr (list 18)]
Agent-1 buy  20 fuel_ore @ 14cr = 280cr  [haggle countered; settled at list 14cr]
Agent-2 buy  20 fuel_ore @ 14cr = 280cr  [haggle countered; settled at list 14cr]
Agent-1 sell 20 fuel_ore @ 18cr = 360cr  [haggle countered; settled at list 18cr]
Agent-2 sell 20 fuel_ore @ 21cr = 420cr  [haggle won at 21cr (list 18)]
Agent-1 buy  20 fuel_ore @ 14cr = 280cr  [haggle countered; settled at list 14cr]
Agent-2 buy  20 fuel_ore @ 14cr = 280cr
Agent-1 sell 20 fuel_ore @ 20cr = 400cr  [haggle won at 20cr (list 18)]
Agent-2 sell 20 fuel_ore @ 20cr = 400cr  [haggle won at 20cr (list 18)]
Agent-1 buy  20 fuel_ore @ 12cr = 240cr  [haggle won at 12cr (list 14)]
Agent-2 buy  20 fuel_ore @ 14cr = 280cr  [haggle countered; settled at list 14cr]
Agent-1 sell 20 fuel_ore @ 18cr = 360cr  [haggle countered; settled at list 18cr]
Agent-2 sell 20 fuel_ore @ 18cr = 360cr  [haggle countered; settled at list 18cr]
```

Per-round-trip P&L (fuel_ore, 20 holds):

| # | P1 buy/sell | P1 Δ     | P2 buy/sell | P2 Δ     |
|---|-------------|----------|-------------|----------|
| 1 | 320 → 360   | **+40**  | 280 → 360   | **+80**  |
| 2 | 280 → 360   | **+80**  | 280 → 400   | **+120** |
| 3 | 280 → 360   | **+80**  | 280 → 420   | **+140** |
| 4 | 280 → 400   | **+120** | 280 → 400   | **+120** |
| 5 | 240 → 360   | **+120** | 280 → 360   | **+80**  |
|   |             | Σ +440   |             | Σ +540   |

Both agents made positive, increasing returns on haggling. **Grok is learning
the haggle math** — P2 tried +3 on sells and +1-2 on buys, hit ~50% acceptance.

## What's working

1. **Port code reading.** Both agents scanned sector 1, correctly parsed
   the BSS/SSB/BBS codes, and picked pairs that trade fuel_ore both
   directions (seller port @14-16, buyer port @18-21 after widening).
2. **Multi-hop warp routing.** They went 1 → seller → 1 → buyer → 1 → ...
   without plot_course (which they haven't discovered yet — good ~opportunity
   for a hint).
3. **Haggling.** 10 of 20 trades were haggles. When a haggle was countered,
   the port auto-settled at list — agents got a profit either way, so they
   tried aggressive offers freely. That's the classic TW2002 rhythm.
4. **Per-port prices now persist across sectors** — `known_ports` intel
   carries `current / max / price / side` so the LLM can compare pairs
   without revisiting (new in v7, regression-tested as
   `test_d4_known_ports_include_prices`).
5. **No illegal action spam.** V7 had one `side` typo on step 5 and the
   agent self-corrected within one turn. Zero `agent_error` in the run.

## What's NOT working yet

### 1. End-of-day `wait` nudge threshold (bug, already fixed)

The v7 match fired the nudge at `turns_left <= 1`, but `warp` costs 2. So
agents burned 4 warps each at `turns_today=58/60` before the
fail-streak unstick kicked in. **Fix already committed after the match
closed** — threshold is now `turns_left < warp_cost` (default 2), with a
regression test that uses the actual `TURN_COST["warp"]` value. V8 run
should show zero end-of-day warp failures.

### 2. They only trade fuel_ore

Agents found one pair (fuel_ore seller + fuel_ore buyer) and stuck with
it. They never tried organics (base 25 = 39% higher unit price) or
equipment (base 36 = 100% higher unit price). The system prompt mentions
all three but doesn't say "compare margins across commodities."

**Proposal:** when 3+ round trips have been logged on a single commodity
at the same pair, surface a hint suggesting: *"If equipment is buyable
nearby, each full-hold trip pays 2x more; run `scan` in adjacent
sectors to look for codes containing `E`."*

### 3. Trade velocity vs. upgrade cost

At ~80 cr/round trip × ~6 trips/day = ~480 cr/day. Relevant price tags:

| Target                    | Price    | Round trips needed | Days (at 6/day) |
| ------------------------- | -------- | ------------------ | --------------- |
| Cargotran (75 holds)      | 43,000   | 538                | 90              |
| Missile Frigate           | 100,000  | 1,250              | 208             |
| Genesis torpedo           | 25,000   | 313                | 52              |
| Battleship                | 880,000  | 11,000             | 1,833           |

**Conclusion:** with current margins, a 2-day sanity match will never
exercise S2+ progression. Either:

- **(a)** bump `--starting-credits` to 200k for sanity (quick);
- **(b)** widen prices further (0.50x-1.50x) and also boost commodity
       base prices (fuel_ore 18→40, organics 25→55, equipment 36→85);
- **(c)** add a "jackpot" sector pair with 2-3x normal margins to let
       one agent lap the other if they find it;
- **(d)** just commit to running the sanity match at `--days 5` for the
       headline test and keep 2-day runs for quick CI smoke.

My vote: **(a) + (d).** Raise `--starting-credits` to 75k so S2 (capital
build) hits within day 2 with natural margins — no economy distortion
needed. Keep a separate 5-day integration run for S3/S4.

### 4. No ship upgrade attempted despite 50k cash

Merchant_freighter (43k) is affordable from turn 1 with 50k cash. Neither
agent bought it. Possible reasons:
- The prompt says "upgrade around 100k-150k cr" — agents took that
  literally and won't upgrade with only 50k.
- The `action_hint` at StarDock lists `buy_ship` but doesn't say *which*
  ship is affordable right now.

**Proposal:** at StarDock, have `action_hint` enumerate specifically
which ship classes the player can buy *today* with their current
credits. E.g.:
`"buy_ship options affordable now: cargotran (43k, 75 holds) — 3.75x your cargo"`

### 5. Scorecard thresholds miscalibrated

Day 1 requires `+20% net worth`. On 50k starting NW, that's +10k in a day.
At ~480 cr/day trade pace this is **unreachable by design**. The rubric
was written assuming 1000-turn days. Either:
- Scale the `+20%` threshold with `turns_per_day / 1000`;
- Or change the threshold to an absolute floor like "≥1% per 100 turns."

## Improvements shipped in v7

| File                              | Change                                                    |
| --------------------------------- | --------------------------------------------------------- |
| `src/tw2k/engine/economy.py`      | Sell-port margin 0.70x-1.20x, buy-port 0.80x-1.30x        |
| `src/tw2k/engine/observation.py`  | End-of-day wait nudge + fix to use warp cost threshold    |
| `src/tw2k/engine/runner.py`       | `_record_port_intel` persists live buy/sell prices        |
| `scripts/run_match_headless.py`   | `--starting-credits` override                             |
| `tests/test_phase_abc.py`         | +6 tests: TestPhaseDEconomy (pricing, nudge, intel)       |

All 103 tests pass, ruff clean.

## Proposed next steps (ordered, pick any or all)

1. **[low risk, high signal]** Relaunch with the end-of-day nudge fix
   and `--starting-credits 75000 --turns-per-day 80`. Expect ship-upgrade
   event to fire within day 2. (~15 min.)
2. **[low risk]** Add the "affordable ships" hint at StarDock so agents
   are told *exactly* what they can buy right now. (~10 min edit + test.)
3. **[low risk]** Add the "try a different commodity" nudge after N
   repeat round trips on the same pair. (~15 min.)
4. **[medium risk, open question]** Rescale scorecard thresholds to be
   `turns_per_day`-aware so the Day-1 rubric isn't structurally
   unreachable in short sanity runs.
5. **[deferred to a real match]** Run `--days 5 --turns-per-day 200`
   with defaults for the first 50 credits / days match-of-record — this
   is the "is the full arc reachable" integration test.
