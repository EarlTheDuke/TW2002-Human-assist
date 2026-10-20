# Playtest 3 dry run

NOTE 153. Checklist: `docs/playtests/PLAYTEST3_READINESS.md` on `track-g-note136` (that file is not on this tip). This run followed that list on `feature/grokbot-player` at `ea20cf86`, with the two routing fixes below.

Game `7b31c521`, "Playtest 3 dry run". Lobby `127.0.0.1:8020`, worker `8021`. State `/tmp/playtest3-dryrun2` (not in the repo). `V311_PROFILE=v311` came from the form's v3.11 rule set. Shots are in `playtest3-dryrun-v1/`.

## Ports

The lobby refuses 8031–8098, so the open pockets inside that block cannot host it. 8099–8119 are the standing lobby. This run used 8020 for the lobby and 8021 for the game. Both are outside 8031–8037, 8041, 8042, 8045–8049, 8055–8119, and 8099–8119.

## Lineup

The readiness list asks for a full-length 2-day game, one scripted cockpit, one code bot, and one heuristic AI opponent. This note asks for 3 fast days, 2 human browser seats, and 2 AI cockpit seats. The dry run used that request:

- Rule set v3.11, 100,000 credits, Original 250 turns, 200 sectors, 3 days
- Game length fast, day length 300 seconds (a `5m` preset added for this lobby only)
- 2 human seats, 1 code bot (Vega), 0 harness AI opponents, Ferrengi on
- 2 scripted hard AI cockpit seats
- Listed, hold the clock until the first player opens a seat

`AI_COCKPIT_SEAT_MODE` stays `legacy` in the tree. The lobby process set it to `tw2002` before `run()`, which is what shows the cockpit checkbox. v3.11 does not turn that switch on by itself.

## Fixes before the rerun

Two small public-mode bugs stopped the first pass. The engine was not changed. Profile-off behavior is unchanged. The scripted-match digests were not at risk.

1. A browser on the worker's own `/bot` page, which is how the scripted cockpit seat opens, asks for `/g/<id>/static` and `/g/<id>/harness` because the page is rewritten with `TW2K_BASE_PATH`. The worker only served those routes without the prefix, so the script loaded and the screen stayed `day=- turns=-- sector=-`. `AcceptBasePath` strips that prefix on the worker. The public lock still sees the path after the strip, so `/control` stays closed.
2. The in-game Manual link is rewritten to `/g/<id>/manual`. `/manual` was outside the open list, so the cockpit received `{"detail":"not available in this game"}`. `/manual` is now an open path. The player manual has no seat token.

After the fix the scripted seats parsed the screen and played. P3 log: `screen day=1 turns=250 credits=100,000 cr nw=123,650 chip=YOUR MOVE sector=189`, then lift off and warps. By day 3, P3 had sold cargo (`credits=102,280`) and P4 had bought and sold (`step 69 click BUY 32`).

## Checklist

| Item | Result | Evidence |
| --- | --- | --- |
| Disclaimer, "I understand" | Pass | `playtest3-dryrun-v1/01-disclaimer.png` |
| New-game lineup above | Pass | `02b-form-filled.png`, created page "Day length: 300s" |
| Created page: scripted cockpit running | Pass | "AI cockpit seat P3: scripted hard, running" and the same for P4. `03-created.png` |
| Created page: https token cockpit links with `layout=redesign` | Fail | The page prints lobby join links, `http://127.0.0.1:8020/join/7b31c521/P1?k=…` and P2. Opening one lands on `/g/7b31c521/bot?seat=P1&mode=cu`, which is the redesign cockpit. The link itself has no `token` and no `layout=redesign`. That shape is the unmerged note 136 created page. |
| Both seats land at home, 100,000 cr, 250/250, YOUR MOVE, day line | Pass | P1 sector 29, "You are LANDED on Guest 1's Home", `TURNS250/250 (full)`, "Day 1 ends in 04:56", YOUR MOVE, 100,000 cr. `04-cockpit-p1.png`. P2 sector 147, Guest 2's Home, same pocket, first paint was WAITING until P1 moved. `04-cockpit-p2.png`. The turn line and the day line sit in the header stat, and both were readable at 1280. |
| Q, lift off, "ok — lifted off." | Pass | Both seats: "ok — lifted off. Turns spent 1. Credits +0." `06-liftoff-P1.png`, `06-liftoff-P2.png` |
| Trade at a BUY or SELL port | Pass on P2, fail on P1 | P2 at Beta-147 Class 5 (SBS) clicked BUY 20. The match log is `Guest 2 buy 20 fuel_ore @ 15cr = 300cr`. End credits 88,817 match 100,000 − 300 − 1,015 fighters − 9,868 tax. Holds at the end were 20/20. `07-trade-P2.png`. P1's first ports had nothing to sell into empty holds, and the driver moved on after one hop. Guest 1 has no trade event. End credits 89,087 match 100,000 − 1,015 − 9,898 tax. |
| Warp one hop, clip, turn drop | Pass | P1 `1:29 (3t)`, clip `merchant_cruiser.gate.06`, "ok — warped 109 → 29. Turns spent 3." `08-warp-clip-P1.png`, `08-warp-P1.png`. P2 clip `merchant_cruiser.streak.01`, "ok — warped 147 → 15. Turns spent 3." |
| StarDock, Class 9, Terra unclaimable | Pass | Both reached sector 1. "Sol-1 StarDock, Class 9 (STARDOCK)". "Terra (colonist source, cannot be claimed)." `09-stardock-P1.png` |
| Buy fighters, "ok — bought … fighters" | Pass | Both: "ok — bought 5 fighters for 1,015 cr." `10-fighters-P1.png` |
| Fight the code bot | Pass | Attack list: "Vega, a Merchant Cruiser, 430 fighters, 0 shields (code bot)". Both seats sent 10 fighters in sector 1. Log: "Combat in 1: Guest 1 sent 10 fighters, lost 10; Vega lost 0 shields and 10 fighters" and the same line for Guest 2. Fighters on the day-2 header are 25 (30 starting + 5 bought − 10 lost). `11-combat-P1.png` shows Vega in sector 1; the result line in that shot is still the fighter purchase because the driver matched the previous ok line. |
| Manual is the v3.11 player manual, with the full-length paragraph | Pass for the manual, fail for that paragraph | Both seats opened Manual from the header. Title "Galaxy War Command", "These numbers are this game's settings", Profile row v3.11. `12-manual-P1.png`. The fast game's page does not include "Full-length games use a 24-hour day". That paragraph is added when the game is full-length. This run was a 300-second day. |
| Layout: larger font, then Reset layout | Pass | Both seats: computed `--cockpit-font` was `17px`, then `default` after Reset layout. `13-layout-P1.png`, `14-layout-reset-P1.png` |
| Day 2, each seat acts | Pass | Header DAY 2/3. Subspace log "Day 2 dawns". P1 "ok — warped 1 → 42" clip `merchant_cruiser.headon.03`. P2 the same hop, clip `merchant_cruiser.chase.02`. `08-warp-P1-day2.png` |
| Day 3, each seat acts | Pass | Header DAY 3/3. P1 "ok — warped 42 → 1. Turns spent 3, 1 came back." clip `merchant_cruiser.headon.07`. P2 the same hop, clip `merchant_cruiser.top.08`. `08-warp-P1-day3.png` |
| Creator ends the game | Pass | `?` menu, End game for everyone, confirm. Header chip GAME OVER. Panel on P1: "GAME OVER - Ended by the game's creator. Decided by experience: 1st AI cockpit 2 10, 2nd AI cockpit 1 8, 3rd Vega 4, 4th Guest 2 3, 5th Guest 1 1. You finished 5th of 5." P2 shows the same ranking and "You finished 4th of 5." Match event: "Ended by the game's creator. AI cockpit 2 leads on experience (10)". `16-game-over-p1.png`, `16-game-over-p2.png` |

## What this run changed in the tree

`src/tw2k/public/worker.py` adds `AcceptBasePath` and puts `/manual` on the open list. `tests/test_selfhost_beta_v1.py` covers the prefixed manual and static routes, and checks that `/g/<id>/control/end` still answers only the lobby. No profile helper was added. No profile-off guard moved.
