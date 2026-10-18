# selfhost-beta-v1 smoke (COMMANDER NOTE 61 item 8)

Command (from the repo root, nothing else running on these ports):

```powershell
python scripts\selfhost\smoke.py --lobby-port 8099 --game-ports 8100-8102
```

Lobby on 127.0.0.1:8099, games on 8100, 8101 and 8102 (the lobby was capped at 3 games for the
run, so the fourth try shows the beta-full answer). Each game: v3.11 rules, 1000 sectors,
2 code bots, 1 guest seat played over HTTP through the lobby proxy (`/g/<id>/harness/v1/...`),
a 120 s day, run to day 3. Raw timeline and samples: `smoke.json`.

## Results

| Check | Result |
|---|---|
| Game start (create to healthy worker) | 1.4 s, 1.4 s, 1.4 s |
| Fourth game | 503 "The beta is full right now, try again later" |
| Guest actions through the proxy | 125 / 124 / 120 sent; the engine accepted every action it received (125 / 124 / 119) |
| Cross-game token checks (each guest's token against the other 2 games) | 6 of 6 answered 401 |
| Spectator on each game (`/g/<id>/watch`) | state 200 on all 3; 143 / 187 / 231 websocket frames in 10 s through the proxy; `/control/pause` 404; seat observation and seat action 401 |
| Sleep (admin "Sleep") and wake | sleeping after 6.9 s; woken by its player's next poll and back to play in 3.1 s (seat resumed with a fresh token) |
| Lobby restart (graceful stop, start) | stop 7.3 s, start 2.8 s; all 3 games came back from their snapshots, each guest resumed its seat (old tokens answered 401) |
| Day 3 | all 3 games at day 3 after 256 s (the day clock kept its place across the restart) |
| CPU, all processes (lobby + 3 workers + console hosts, 17 samples) | average 18.7 %, peak 98.5 % (sum of per-process percent; the peak is the lobby restart) |
| RAM, all processes | average 341 MB, peak 347 MB |
| Tokens, guest cookies in `saves\selfhost-smoke\logs\` | 0 hits |
| Final stop | ports 8099-8102 free afterwards; whole run 264 s |

Per process (17 samples each, `per_process_summary` in `smoke.json`):

| Process | CPU average | CPU peak | RAM average | RAM peak |
|---|---|---|---|---|
| lobby (8099) | 15.5 % | 93.7 % | 76 MB | 83 MB |
| worker 8100 | 1.0 % | 4.7 % | 80 MB | 81 MB |
| worker 8101 | 1.1 % | 3.1 % | 80 MB | 84 MB |
| worker 8102 | 1.0 % | 3.1 % | 80 MB | 82 MB |

The one action on the slept game that did not get a 200 was sent while that game was asleep
(the lobby answers 503 "waking up" and the guest retries); it never reached the engine. Each
guest also logged 3 connection errors: those are the polls made while the lobby was down for its
restart; the guest retried and carried on.

## Screens (1920 and 390 wide)

* `disclaimer-*.png` - first visit; "I understand" must be pressed before anything else.
* `new-game-*.png` - rules (v3.11 preselected, legacy available), starting package, universe size
  (1000 default), max days, turns per day, day length (30 minutes default), open human seats,
  code bots 0-5, Ferrengi, listed or link-only. Taken before any game existed.
* `lobby-*.png` - the lobby as a new visitor sees it with three running games: each card has its
  rules, day and open seats and a Watch button, the beta-full notice, and the footer link
  "About these test games".
* `cockpit-header-*.png` - the seat's cockpit through `/g/<id>/bot`, connected by its claim cookie,
  with the "GALAXY WAR COMMAND" title frame.
* `spectator-*.png` - the read-only watch page through `/g/<id>/` (title, heading and tagline
  rebranded).
* `beta-full-*.png` - "New game" while every slot is taken.

All screens are from this 8099 run.

## Commander retest

1. `scripts\selfhost\start.ps1 -Quick` (lobby on 8099 and a Quick Tunnel; needs `cloudflared`).
2. Open the printed `https://...trycloudflare.com` address on 3-5 devices, accept, create games,
   take seats, watch one from another device.
3. `scripts\selfhost\stop.ps1`.
