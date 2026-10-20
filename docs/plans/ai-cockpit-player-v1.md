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

The scripted trader reads the manual, then plays from the screen text. It records the sector, the port code and prices, the directed warps, and the holds. It sells where the port is buying unless a seen port pays more and the hop still fits. It buys where the port is selling when a seen bid is higher and the turns left cover the sale. Once that pair is known it stays on it: a one-way warp is not taken just to look around, and if the next full trip does not fit it parks on the selling port for the next day. On the last day those leftover turns are waits, then the day-end confirm. A counter below a better reachable bid for the same good is declined. A refused haggle is left. At StarDock it buys one hold when it can pay, and more only when the seen spread is wider than the unit price, then fighters. It does not leave a known route to shop for gear. Sectors whose text showed Ferrengi, deployed mines, or hostile fighters are not warped back into. The StarDock gear list names Armid, Limpet, and Atomic mines; that catalog is not a threat. It keeps acting while the chip says YOUR MOVE, waits on NO TURNS for the next day, and stops when the chip says GAME OVER.

On seed 250925 the seat starts at sector 16 with net worth 72,227. The 9-turn, 3-day game is one organics trip on each trading day and still finishes at 74,037. The same seat with 24 turns repeats the 16/35 pair and finished at 77,437 (gain 5,210). The previous trader on that same 24-turn game wandered off the pair and finished at 74,857, including a load it bought and could not sell. Day 1 has no port stock to buy, so a 1-day game still ends at 72,297 after the fuel sale, without the old wander down the one-way warp to 126.

Keys are read from the environment at call time. They are not written into source, the run log, `actions.jsonl`, or screenshots' text sidecars. Logs replace key values, `sk-...`, `xai-...`, bearer tokens, and `token=` query values with `[redacted]`.

A live provider's system prompt is the trading playbook plus the manual text captured from the seat page. Each call also gets a short memory of the last few screens and actions. A reply that is not a click, type, press, or wait on a control that is on the screen is rejected and asked again, up to two retries, and then the runner waits. Each reply's token counts are priced with the same USD-per-million table as `src/tw2k/engine/llm_pricing.py` (curated 2026-04-22; the player keeps its own copy and does not import that module). The run log gains a line:

```
cost provider=grok model=grok-4 input_tokens=120 output_tokens=40 usd=0.000960
```

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

## Lobby seat

`AI_COCKPIT_SEAT_MODE` already exists. The stored value stays `legacy`. `ai_cockpit_seat_on()` is true when that value is `tw2002` or when `TW2002_LIVE_PROFILE` is `live`. `V311_PROFILE` does not turn it on, and the helper is not in `V311_PROFILE_HELPERS`.

While the switch is legacy, the new-game form has no AI cockpit seat control, and `ai_cockpit`, `ai_cockpit_provider`, and `ai_cockpit_model` are unknown fields. While it is on, the Players section offers **AI cockpit seat**, a provider (scripted, Grok, OpenAI, Anthropic), and a model name. The form does not ask for a key. `settings()` stores the provider and the model only when the box is checked.

`start_game` adds that one external seat after the human seats and any harness AI seats. The harness driver does not receive it. After the worker is healthy, the lobby starts `scripts/ai_cockpit_player.py` against the worker's `/bot?seat=Pn&mode=cu&token=...&layout=redesign` link. The log line is `ai cockpit player seat=Pn provider=... model=...`. It does not include the token.

The created page and the lobby row show `AI cockpit seat: <provider>, running` (or `stopped`). **Watch** is the spectator. **AI seat** and **Open Pn** go to `/games/<id>/ai-seat`, which redirects the creator to the seat page. The token is not written into the lobby HTML.

The runner reloads the original seat link if the page closes or the chip disappears, presses Escape when a click is swallowed by a dialog, and exits 0 when the chip says GAME OVER. A stop file still ends the run. `Lobby.launch_browser_seat(...)` still returns None while the switch is legacy.

## Tests

`tests/test_ai_cockpit_player_v1.py` runs the scripted provider against a `CuHost` on a port from `free_port`. That is an open pocket, or an OS ephemeral port that `allowed_test_port` accepts, outside 8031-8119 and 8120-8249. One game lasts three days and must finish with a higher net worth than it started. The same file checks the source has no `tw2k` import, the player process loads no `tw2k` module, a run that has keys in its environment does not write those keys or the seat token into the text log, and the new-game control is missing while the switch is legacy.
