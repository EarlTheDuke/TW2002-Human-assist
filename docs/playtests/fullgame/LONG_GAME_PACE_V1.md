# Long-game pace (slice 68)

Live game 4 slowed from about 0.8 to 0.25 game days per hour by day 19. This
slice speeds the headless seat path with no rule or outcome change.

## Cause

A 20-day cProfile on seed 250925 pointed at the seat brain:

- `_nav_graph` rebuilt the known-warp map on almost every BFS (~935k builds).
- `_distances_from` / pair search then walked that graph for trade quotes.

Observation feed indexing from soak-30day already kept event scans flat.
The remaining growth was in nav rebuilds as the known map grew.

## Fix

Cache `_nav_graph` on the same per-decision bag as the BFS cache. Each
`decide()` still builds the graph once; pair search reuses it. Pure speed-up:
same digests and event totals.

## Bars

Per-day wall time at day 60 within 1.5x of day 5 (seed 250925, seats
N3,N3,N2,N2,N1,H). Digests and saves identical at day 10/30 on seeds 250925
and 4242.

## Before / after (seed 250925)

| Window | Before total | After total | Notes |
| --- | ---: | ---: | --- |
| 15 days | 564.8 s | 344.9 s | day 14: 74.4 → 35.9 s |
| 60 days | 2995 s | 2213 s | day 59: 36.9 → 38.3 s; bar 0.95× day 5 (PASS) |

Event and planet counts matched day-for-day on both windows. Ranking on the
60-day pair was identical (`P1,P3,P2,P4,P5,P6`). Day-19 spike fell from 151 s
to 81 s.

Seed 4242, 10 days, action digest `84d21648` before and after. Net worth by seat matched. Seed 4242, 30 days, action digest `9ac79bc9` before and after. Ranking `P5, P3, P1, P4, P6, P2` both. The instrumented 60-day seed 250925 pair also kept digest `ea2733f5` (wall 3163 s → 2253 s; day 60 about 38 s, 1.00× its day 5).

## How to measure

```powershell
$env:PYTHONHASHSEED="0"
$env:PYTHONPATH="src"
python scripts/long_game_pace_lab.py --seed 250925 --days 60 --json artifacts/pace68/run.json
```
