# AI cockpit player (NOTE 128)

An AI seat that plays Galaxy War Command the way a person does. It opens a normal cockpit link, looks at the rendered page, and uses the same buttons and keys. It does not import the engine, call the harness, or read state that is not on the screen.

The seat link is the one a person uses:

```
/g/<game>/bot?seat=Pn&mode=cu&token=...&layout=redesign
```

`layout=redesign` asks for the redesign cockpit even when `COCKPIT_LAYOUT` is unset. `/bot` (the legacy page, `web/bot.html`, `web/bot.js`, `web/bot-parity.js`) is unchanged.

## Runner

```
python3 scripts/ai_cockpit_player.py \
  --url 'http://127.0.0.1:8050/bot?seat=P2&mode=cu&token=...&layout=redesign' \
  --provider scripted \
  --max-turns 40 \
  --min-interval 1 \
  --stop-file runs/ai-cockpit/STOP \
  --run-dir runs/ai-cockpit
```

Each step:

1. Wait until the chip says YOUR MOVE, NO TURNS, or GAME OVER.
2. Save a screenshot and the page's visible text under the run folder (`screen-NNN.png`, `text-NNN.txt`).
3. Ask the provider for one action: click a visible label or selector, type text, press a key, or wait.
4. Do that action.

The first action from the scripted provider is the header Manual link, which opens the in-game player manual in a new tab. The runner saves that page as `text-manual.txt` and `screen-manual.png`, then goes back to the cockpit. Live providers are told to do the same before they trade.

The loop stops when the chip says GAME OVER, the stop file exists, or `--max-turns` actions have been taken. `--min-interval` is the minimum seconds between actions. A stop file that already exists skips the browser.

`modules.txt` in the run folder lists any `tw2k` modules the process loaded. A clean run leaves it empty.

## Providers

| `--provider` | Key variable | Default model variable |
| --- | --- | --- |
| `scripted` | none | rule-based trader, offline |
| `grok` (alias `xai`) | `XAI_API_KEY` | `XAI_MODEL` (default `grok-4`) |
| `openai` | `OPENAI_API_KEY` | `OPENAI_MODEL` (default `gpt-4o`) |
| `anthropic` | `ANTHROPIC_API_KEY` | `ANTHROPIC_MODEL` (default `claude-sonnet-4-5`) |

The scripted trader reads the manual, clicks the first SELL button it can see, and otherwise presses `.` to spend a turn.

Keys are read from the environment at call time. They are not written into source, the run log, `actions.jsonl`, or screenshots' text sidecars. Logs replace key values, `sk-...`, `xai-...`, bearer tokens, and `token=` query values with `[redacted]`.

## How Ben adds a key later

Pick one provider and export its variable in the shell that starts the player. Do not put the key in a file in this repo, in the lobby database, or in a command that gets committed.

```
export XAI_API_KEY='...'          # or OPENAI_API_KEY, or ANTHROPIC_API_KEY
export XAI_MODEL='grok-4'         # optional
python3 scripts/ai_cockpit_player.py \
  --provider grok \
  --url "$SEAT_URL" \
  --max-turns 40 \
  --min-interval 1 \
  --run-dir runs/ai-cockpit
```

The lobby does not store the key. A live provider that finds an empty variable stops with a message that names the variable and does not echo a key.

## Lobby hook

`AI_COCKPIT_SEAT_MODE` already exists. The stored value stays `legacy`. `ai_cockpit_seat_on()` is true when that value is `tw2002` or when `TW2002_LIVE_PROFILE` is `live`. `V311_PROFILE` does not turn it on, and the helper is not in `V311_PROFILE_HELPERS`.

`Lobby.launch_browser_seat(...)` and `tw2k.public.ai_cockpit_launch.launch_player(...)` start the runner only while the switch is on. While it is legacy they return None and start no process. `start_game` does not call them, so today's harness AI seats are unchanged. A later lobby control can call `launch_browser_seat` with the game id, the seat, and that seat's token. The child receives the seat link and nothing from the engine.

The log line is `ai cockpit player seat=Pn provider=...`. It does not include the token.

## Tests

`tests/test_ai_cockpit_player_v1.py` runs the scripted provider against a `CuHost` on a port from `free_port`. The port is an open pocket below 8060 and outside 8031-8037, 8041, 8042, 8045-8049, and 8055-8119. The same file checks the source has no `tw2k` import, the player process loads no `tw2k` module, and a run that has keys in its environment does not write those keys or the seat token into the text log.
