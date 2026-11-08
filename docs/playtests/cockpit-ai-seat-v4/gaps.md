# Cockpit seat v4: the North Star run under v3.11 (2026-11-07)

The first North Star test since v3.11 became the default. A real model played one
seat from the rendered cockpit only (screenshot + visible text, no engine access)
for a whole 3-day game.

## Setup

| Item | Value |
| --- | --- |
| Game | Galaxy War Command lobby, game `8b7d203d`, 1 AI seat (P1) + 3 code bots, 500 sectors |
| Rules | v3.11 default, 1-hour days, 3 days, 250 turns a day refilling at +1 every 14.4 s |
| Model | kimi-k2.6 on the tinybox (OpenAI-compatible, vision) via `scripts/ai_cockpit_player.py --provider custom` |
| Player settings | `AI_COCKPIT_TIMEOUT_S=240`, `AI_COCKPIT_NO_TURN_WAITS=250`, `--min-interval 1` |
| Run files | `run-player.txt` (screen line per move), `run-actions.jsonl` (every action) in this folder |

The xAI and Anthropic keys in `.env` were both rejected as invalid on 2026-11-07, so
the run used the tinybox. A 30-minute-day attempt was dropped after 6 moves: the model
needs ~45 s a move, so a 30-minute day only fits ~40 moves.

## What happened

- **Day 1:** read the manual, lifted off, scanned, opened the Computer port report,
  explored 6 sectors, then at move 13 found a pair (buy fuel ore at Hydra-58 for 14,
  sell at sector 198 for 33). It ran that pair, then a better one (58 ↔ 245, sells at
  37-38), for the rest of the game.
- **Days 2-3:** the same 20-hold round trip, about 450 cr profit each.
- **End:** 120 moves in 3 hours. 300 → 11,340 credits, net worth 40,790, rank
  Sergeant, **3rd of 4**. Bot Vega won on experience (71 vs 56).
- It never went to StarDock (sector 1, on its map and in the manual it read), never
  bought holds, never banked, never haggled, never claimed a planet. 11k credits sat idle.

**The good news for the North Star question:** the basic trade loop ran entirely from the
cockpit. The AI found ports from the port table, warped with the warp buttons, used
BUY 20 / SELL 20, and read the result in the log. Two clicks failed out of 120 (one
jQuery-style selector the model invented, one at game end). Nothing on the screen was
missing for the moves it actually made.

## Findings

Ranked by what blocks the test. "Kind" says where the fix belongs.

| # | Finding | Kind | Evidence | Fix |
| --- | --- | --- | --- | --- |
| 1 | **A slow seat loses its saved turns.** The server inserts an auto-WAIT when an external seat takes over 120 s, and the WAIT-loop guard counts those. Four in a row (8 minutes) and the seat "ends the day early": every saved turn is thrown away. Under v3.11 turns then trickle back at +1 per 14.4 s. A human who steps away for 8 minutes gets the same thing. | Server rule (`src/tw2k/server/runner.py`, the guard after `note_wait_streak`) | Day 2: 248 → 10 turns ("249 turns skipped") while the model was thinking. Day 3: 32 and 153 skipped. | Don't count the server's own timeout auto-WAITs toward the stand-down, or skip the stand-down under v3.11, where the day already rolls on the clock. The guard was there to stop a waiting seat holding up the day, and under v3.11 nothing waits for it. Needs Ben's OK (rule change, flag-gated). |
| 2 | **The model only sees 8.5% of the manual.** The player keeps the first 6,000 of 70,000 characters. Half of that is the rule-mode table and the contents. Trading/haggling, StarDock services, Hardware, the bank and planets are cut off. | Test harness (`scripts/ai_cockpit/runner.py` `_read_manual`, `providers.system_prompt`) | `text-manual.txt`: "StarDock is sector 1" is in, "StarDock services" and hold prices are not. | Skip the mode table and contents, and keep the playing sections. Or let the model open a manual section by name when it needs it, the way a person would. |
| 3 | **We can't tell "didn't know" from "chose not to".** The reply is a bare action. The model's reasoning isn't saved, and there's no field for "what I needed and couldn't see". The North Star question asks exactly that, so the run can't answer it. | Test harness | `run-actions.jsonl` has no reasons. | Add `reason` and `missing` fields to the reply format and log them. The gap list then comes from the AI's own words, not from guessing. |
| 4 | **No memory past 8 moves.** The prompt carries the last 8 screens/actions only. A plan like "save 5,000, fly to StarDock, buy holds, come back" can't survive. The loop it fell into is what a player with 8 moves of memory would do. | Test harness | About 50 identical round trips over moves 13-120. | A short notes pad the model writes and reads every move: goals, known ports and prices, StarDock. A human keeps the same notes on paper. |
| 5 | **The model is slow.** kimi-k2.6 took a median of 46 s per move (up to 7 minutes) and wrote up to 7,500 tokens of thinking. 14 replies went past the 240 s limit. That's about 56 minutes of a 3-hour game spent idle. 120 moves in 3 days, where a human makes hundreds. | Model choice | `player.log` cost lines and timeouts. | Restore a cloud key (Grok fast or Claude), or cap the thinking. Fix #1 first, since it turns slowness into lost turns. |
| 6 | The cockpit's turn line is right, and the "turns go up" thing seen during the run is not a bug: v3.11 refills turns all day ("TURNS 247/250 (+1 every 14.4 s)"). | None | Screens show it plainly. | None. |

## What the run did not test

Combat, Ferrengi, planets, citadels, StarDock purchases, banking, corporations and
messaging never came up, because the AI stayed on one trade route. The next run needs fixes
2-4 in the harness, so the AI gets past the first route. Then the gap list will cover
the rest of the cockpit.
