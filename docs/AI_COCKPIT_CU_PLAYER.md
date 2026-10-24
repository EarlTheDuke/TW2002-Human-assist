# AI cockpit player — human parity

The player in `scripts/ai_cockpit_player.py` sits in a normal cockpit seat. It opens the seat link, reads the rendered page, and presses the same controls a person can press. The point is to try the interface and surface UX and engine bugs. It is not a stronger bot with a private feed.

## What it may see

The seat link is the one a person uses:

```
/bot?seat=P2&mode=cu&token=...&layout=redesign
```

A lobby game serves that path as `/g/<game>/bot?seat=P2&mode=cu&token=...&layout=redesign`. `layout=redesign` is the cockpit this runner drives (`#waitchip`, the HERE panel, the Manual link). `mode=cu` marks that seat for computer use: larger action targets, and a control the page has greyed out is disabled so it cannot be pressed. The chip text stays **YOUR MOVE**, **WAITING**, **NO TURNS**, or **GAME OVER**. YOUR MOVE is this seat's turn. The one-screen `/bot?mode=cu` page (no `layout=redesign`) is a different layout; this runner does not drive it.

On each step the runner saves `screen-NNN.png` and `text-NNN.txt`, then asks the brain for one action: click a visible label, type into a visible field, press a key, or wait. A click whose label is not on the screen is not sent.

The in-game Manual link is part of the page. The scripted brain opens it before trading. A live brain is told to do the same. The manual text in the prompt is the text that page showed.

## What it must not see

This brain does not import `tw2k`. It does not call `/harness/v1/{seat}/observation`, `/reference`, `/events`, `/status`, or `/action`. It does not read another seat, the universe, or the runner.

That is a different track from:

- TinyBox lobby brains (`src/tw2k/public/tinybox.py`, "LLM (your key)" seats). Those read a server-side observation and post a harness action. Sharing `TW2K_CUSTOM_BASE_URL` with this player does not share that observation. This player still sends the screenshot and the visible text.
- `src/tw2k/agents/cockpit_seat.py`, which is allowed to GET those four harness routes. This runner does not use it.
- `scripts/grokbot_seat_client.py` and `docs/GROK_BOT_PLAYER_GUIDE.md` sections 2–8, which are the harness client. Section 9 of that guide is the page. This player is only the page.

Code bots and TinyBox seats are unchanged. `AI_COCKPIT_SEAT_MODE` stays `legacy` until a lobby turns the cockpit seat on. While it is legacy, the new-game form has no AI cockpit control and no process is started.

## Run it

From the repo root. The API is optional. With no key, `--provider scripted` (the default brain when a live provider is not configured) plays from the screen text and does not open a socket.

```bash
python3 scripts/ai_cockpit_player.py \
  --url 'http://127.0.0.1:8050/bot?seat=P2&mode=cu&token=...&layout=redesign' \
  --provider scripted \
  --level hard \
  --max-turns 40 \
  --min-interval 1 \
  --stop-file runs/ai-cockpit/STOP \
  --run-dir runs/ai-cockpit
```

`--level` is easy, normal, or hard. It applies to the scripted trader only. A stop file that already exists skips the browser. Creating the stop file ends the run. The loop also stops on GAME OVER or `--max-turns`.

`runs/ai-cockpit/player.log` records steps. `actions.jsonl` records each click, type, press, or wait. `modules.txt` lists any `tw2k` module the process loaded. A clean run leaves it empty.

Playwright and a Chromium build are required for a live seat. A missing browser is a log line and exit 1, not a fallback into the harness.

## Model endpoint, when there is one

Pick one provider. Export its variables in the shell that starts the player. Do not put a key in this repo, in the lobby database, in a screenshot sidecar, or on the command line.

| `--provider` | Key | Model | Address |
| --- | --- | --- | --- |
| `scripted` | none | rule-based, offline | none |
| `mock` | none | `--mock-script` JSON list | none |
| `grok` (alias `xai`) | `XAI_API_KEY` | `XAI_MODEL` (default `grok-4`) | `https://api.x.ai/v1/chat/completions` |
| `openai` | `OPENAI_API_KEY` | `OPENAI_MODEL` (default `gpt-4o`) | `https://api.openai.com/v1/chat/completions` |
| `anthropic` | `ANTHROPIC_API_KEY` | `ANTHROPIC_MODEL` (default `claude-sonnet-4-5`) | `https://api.anthropic.com/v1/messages` |
| `custom` (aliases `compatible`, `openai-compatible`) | `AI_COCKPIT_API_KEY`, else `TW2K_CUSTOM_API_KEY`, else `TW2K_TINYBOX_API_KEY` | `AI_COCKPIT_MODEL`, else `TW2K_CUSTOM_MODEL`, else `--model` | `AI_COCKPIT_BASE_URL`, else `TW2K_CUSTOM_BASE_URL`, else `--base-url` |

`custom` speaks the OpenAI chat-completions JSON. A base URL that already ends in `/chat/completions` is used as given. Any other http(s) base gets `/chat/completions` appended, so `https://host/v1` and `https://host/api` both work. A URL with a username or password is refused.

If the base URL, the key, or the model is missing, the runner logs the variable name (`no AI_COCKPIT_API_KEY, scripted fallback`) and uses the scripted trader. It does not call the network and it does not print the key.

```bash
export AI_COCKPIT_BASE_URL='https://example.test/v1'
export AI_COCKPIT_API_KEY='...'
export AI_COCKPIT_MODEL='your-model'
python3 scripts/ai_cockpit_player.py \
  --provider custom \
  --url "$SEAT_URL" \
  --max-turns 40 \
  --min-interval 1 \
  --run-dir runs/ai-cockpit
```

`--base-url` overrides the address for that process. The key is still read from the environment at call time.

The lobby form can store provider `custom` and a model name when `AI_COCKPIT_SEAT_MODE` is `tw2002`. The form does not ask for a key or a base URL. The lobby process environment supplies them, and the child inherits that environment. The log line is `ai cockpit player seat=Pn provider=custom model=...`. It does not include the token or the key.

A live reply that is not a click, type, press, or wait on a control that is on the screen is rejected and asked again, up to two retries, and then the runner waits.

## Secrets

Logs replace key values, `sk-...`, `xai-...`, bearer tokens, and `token=` query values with `[redacted]`. The variables covered are `XAI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `AI_COCKPIT_API_KEY`, `TW2K_CUSTOM_API_KEY`, `TW2K_TINYBOX_API_KEY`, and `TW2K_COCKPIT_LLM_KEY`. Do not commit `runs/`, `.env`, or a seat-link file.

## Tests

`tests/test_ai_cockpit_cu_driver_v1.py` drives the turn loop with a stand-in page and checks the custom endpoint with a fake HTTP call. It does not start TinyBox. `tests/test_ai_cockpit_player_v1.py` still runs the scripted provider against a local cockpit on a free port outside the live bands.
