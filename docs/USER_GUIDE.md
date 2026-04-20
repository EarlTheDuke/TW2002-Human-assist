# TW2K-AI — User Guide

This guide walks you through installing, configuring, and running a TW2K-AI match.

---

## 1. Install

Requires **Python 3.11+** (tested on 3.13).

From the project root:

```powershell
pip install -e .
```

This installs the `tw2k` command-line tool and all dependencies.

---

## 2. Configure an LLM provider (optional but recommended)

For LLM-driven agents, set an API key. Either provider works; the first key found is used.

### Claude (Anthropic) — recommended

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
# Optional: override the model (defaults to Claude Sonnet 4.5)
$env:TW2K_ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
```

### GPT (OpenAI)

```powershell
$env:OPENAI_API_KEY = "sk-..."
# Optional: override model (defaults to gpt-4o-mini for cost)
$env:TW2K_OPENAI_MODEL = "gpt-4o"
```

### No API key?
You can still run matches — the engine falls back to the built-in heuristic agent. Good for testing; not as fun to watch.

---

## 3. Run a match

```powershell
tw2k serve
```

Default: 2 LLM agents (if a key is set), 1000-sector galaxy, 10 in-game days max.

Open http://localhost:8000 in your browser and watch the match unfold.

### Useful flags

```powershell
tw2k serve `
  --port 8000 `
  --seed 12345 `            # deterministic universe generation
  --universe-size 1000 `    # number of sectors
  --max-days 10 `           # turns before time-victory
  --num-agents 2 `          # how many players
  --agent-kind auto `       # auto | llm | heuristic
  --provider anthropic `    # force a specific backend
  --model claude-sonnet-4-5-20250929
```

### Quick headless sim (no LLM needed)
Tests the engine end-to-end with heuristic players:

```powershell
tw2k sim --seed 1 --max-days 2
```

### Probe a universe seed
See what would be generated for a given seed, without playing:

```powershell
tw2k probe --seed 42
```

---

## 4. Spectating

The spectator web page has four zones:

| Zone | Description |
|---|---|
| **Top bar** | Day/tick counters, connection status, pause ⏸, speed (0.5×/1×/2×/5×), and `⟳ New Match` |
| **Galaxy map** | Pan (drag) and zoom (scroll). Hover sectors for details. Orange = port, blue = FedSpace, purple-outlined = has planet, white = StarDock. Ship positions are colored dots. |
| **Commanders panel** | Live stats per player: credits, net worth, ship, sector, fighters, cargo bar, and the agent's own **scratchpad** (its private working memory). |
| **Event feed** | Chronological log of every significant action and outcome, including agent **thoughts**. Filter by category with the checkboxes. |
| **Transmissions** | Private hails + public broadcasts between agents — the space for diplomacy, alliances, threats, or betrayals. |

Click any sector on the map to highlight it; hover for a tooltip showing port, planets, occupants, and warp connections.

---

## 5. What to watch for

An interesting match usually plays out in phases:

1. **Opening (Day 1–3)**: Both agents find ports near FedSpace, establish trade loops, build up 100–500k credits.
2. **Outfitting**: Agents return to StarDock, buy fighters/shields/mines, possibly upgrade to a Missile Frigate (100k) or bigger.
3. **Expansion**: Deploying fighters to claim sectors; exploring deeper into the galaxy looking for BBB ports (buys everything, huge profits).
4. **First contact**: Agents run into each other, into Ferrengi raiders, or find each other's deployed fighters. This is where diplomacy or combat starts.
5. **Alliance phase**: Look at the Transmissions panel — agents may hail each other to form a **corporation** (500k cr at StarDock). Corps can't attack each other and share intel.
6. **Endgame**: Either a betrayal, an economic sprint to 100M cr, or time runs out with net-worth deciding the winner.

---

## 6. Controls reference

| Control | Effect |
|---|---|
| Pause / Resume | Freezes the match. Useful if you want to read thoughts carefully. |
| Speed 0.5× / 1× / 2× / 5× | Scales the delay between agent actions. Does NOT speed up LLM thinking, only the pause between turns. |
| New Match | Discards the current game and starts fresh with a new random seed. |
| Click sector | Shows sector details. |
| Drag map | Pan around the galaxy. |
| Scroll wheel | Zoom in / out (zooms toward cursor). |
| Filter checkboxes | Show/hide event categories in the feed. |

---

## 7. Cost & time expectations (LLM play)

A 2-agent match of ~10 in-game days typically consumes **200–600 LLM calls per agent** (one per turn), depending on how efficiently they use their turn allowance.

| Provider | Model | ~Cost per match | ~Wall-clock |
|---|---|---|---|
| Anthropic | claude-sonnet-4-5 | $1.50 – $4.00 | 25–60 min |
| OpenAI | gpt-4o-mini | $0.08 – $0.20 | 20–45 min |
| OpenAI | gpt-4o | $2.00 – $5.00 | 30–60 min |

You can cap a match by lowering `--max-days` or `--universe-size`.

---

## 8. Troubleshooting

**"LLM provider: none"** — no API key in env. Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`, or run with `--agent-kind heuristic`.

**Agents always play `wait`** — their LLM is returning malformed JSON. Try a stronger model (e.g. `claude-sonnet-4-5` instead of Haiku, or `gpt-4o` instead of `gpt-4o-mini`). The event feed will show `[parse error]` thoughts when this happens.

**Match looks frozen** — check the `status` in the top bar. If it says `paused`, click ⏸ to resume. If `running`, an LLM may just be slow to respond (up to 20s per call). Low-cost models are usually fast.

**Heuristic agents get stuck in loops** — known limitation of the baseline bot; it doesn't pathfind well. LLM agents handle this gracefully.

**Port stock prices look wrong** — port prices float with stock level. A port that just bought 2000 Fuel Ore will pay less for the next unit. This is correct behavior.

---

## 8.5. Playing as a human (with or without an AI copilot)

TW2K-AI supports a real human player alongside the AI agents, with a dedicated
cockpit UI at `/play` and an optional voice-driven AI copilot that can plan,
execute, and narrate on your behalf. Full design: `docs/HUMAN_COPILOT_PLAN.md`.

### 8.5.1. Start a match with a human slot

```powershell
tw2k serve `
  --port 8000 `
  --seed 777 `
  --universe-size 200 `
  --max-days 30 `
  --num-agents 3 `
  --agent-kind heuristic `
  --human P1 `                # P1 is the human; P2/P3/P4 stay AI
  --human-deadline-s 300 `    # optional: auto-WAIT if human AFK 5 min
  --starting-credits 75000
```

Then open http://localhost:8000/play. The spectator view (`/`) now has a
`🧑 Cockpit` button in the header; the cockpit has a `◎ Spectator` button
going back — toggle freely.

### 8.5.2. The cockpit (`/play`) layout

| Zone | What it shows |
|---|---|
| **Left — Cockpit** | Current sector (ID, planets, port stock + prices, occupants), adjacent-warp chips (click to prefill a warp), your ship vitals + cargo + turns, and per-action forms (warp, trade, scan, probe, land, liftoff, hail, broadcast, wait). |
| **Middle — Events + observation inspector** | Live per-player event feed filtered to things that actually affect you, plus a collapsible "raw observation" pane showing the exact JSON the copilot sees. |
| **Right — Copilot** | Mode toggle (Manual / Advisory / Delegated / Autopilot), chat transcript + input + 🎤 push-to-talk button, pending-plan card with "Predicted outcome" (what-if), active-task banner, memory pane (prefs + learned rules + favorite sectors + remember form), voice-language selector, 🔈 TTS toggle, safety escalation banner. |

Keyboard: `/` focus chat · `Esc` cancel pending plan / active task · `Enter`
confirm pending plan · `W/S/P/B/L/.` open warp/scan/probe/broadcast/land/wait
forms · `F5` refresh observation · `?` shortcut cheatsheet. Hold `Space` for
push-to-talk in the chat area.

### 8.5.3. The four copilot modes

| Mode | Behaviour |
|---|---|
| **Manual** | Copilot is muted. Every action is yours. Use this while learning the engine or if you want the copilot to stop suggesting things. |
| **Advisory** | Copilot proposes plans (with a "Predicted outcome" card) but does **not** execute them — you click **Confirm** to run each plan. Great default: you see Grok/Claude's reasoning + estimated credit/turn/cargo impact before any action fires. |
| **Delegated** | Copilot auto-executes single-step actions the moment it's confident (e.g. `"warp to 48"` just goes). Long-running tasks still pop a one-click preview. |
| **Autopilot** | Copilot runs long-running `profit_loop` / `explore` / custom tasks hands-off, narrates via TTS, pings every ~7.5 s with an idle-report, and can be interrupted by saying **"stop"** / **"hold"** / **"pause"**. Safety escalation banner fires on hostile fighters, low turns, low credits, or incoming combat. |

Long-running tasks in Delegated and Autopilot still require **one** confirm
click the first time — the preview card in the right panel shows the task goal
(e.g. `profit_loop {target_cr: 120000, commodity: organics}`) and a
Confirm/Cancel pair. After that first consent the task runs without further
prompts until it hits its target, runs out of turns, you interrupt it, or a
safety signal escalates.

### 8.5.4. Voice

Works on any Chromium browser (Chrome/Edge/Opera) — no API keys, no server
deps. Firefox and Safari fall back to typing.

- **Push-to-talk**: hold the `🎤 Hold to talk` button (or hold `Space` with
  the chat focused). Interim transcript streams into the PTT status pill;
  on release, the final transcript is normalised (commodity aliases,
  "eight seventy four" → `874`, etc.) and fed into the same chat pipeline
  as typing.
- **TTS**: click `🔈 Voice` in the right header to enable spoken copilot
  replies via `speechSynthesis`. Picks a voice matching your language
  selector (9 BCP-47 options: EN, EN-GB, ES, FR, DE, IT, PT-BR, JA, ZH;
  persisted in `localStorage`). De-duped against back-to-back identical
  lines; cancels on mode change.
- **Autopilot interrupt**: a second `SpeechRecognition` instance runs
  always-on while in Autopilot mode and matches `stop` / `hold` / `pause` /
  `cancel` / `abort` — drops you back to Advisory within one LLM cycle.

### 8.5.5. Memory, remember/forget, learned rules

The copilot has per-player long-term memory persisted to
`saves/copilot_memory/<player_id>.json`. Three kinds of state:

- **Preferences** (`key = value`) — say or type `remember favorite commodity = organics`
  and it sticks across sessions; `forget favorite commodity` removes it.
  You can also use the remember-form in the memory pane.
- **Learned rules** — every plan you Confirm contributes its thought as a
  rule the copilot surfaces in its prompt-block on future sessions.
- **Favorite sectors** — every successful `warp` / `plot_course` target gets
  auto-marked, so Grok knows where you like to hang out.

A live chip in the memory pane shows the running summary (e.g.
`memory: 3 prefs, 2 rules, 4 favs, 7 sessions`).

### 8.5.6. What-if preview

Any pending plan (Advisory mode, or the first preview of a long-running
Autopilot task) shows a dashed **"Predicted outcome"** card with:

- Per-plan one-liner: `+3 500 credits · -18 turns · +80 Organics`.
- Colour cues: `.is-positive` (green) / `.is-negative` (red).
- A warnings list when the heuristic spots risks (out-of-stock ports,
  no-warp-to-sector standing order blocking, etc.).

Heuristic-only — no engine fork — so it's cheap enough to recompute on every
render without affecting match throughput.

### 8.5.7. Structured decision tracing (debugging + forensics)

Set `TW2K_COPILOT_TRACE=1` before `tw2k serve` and the copilot writes every
significant decision to `saves/copilot_traces/copilot_trace_<player_id>.jsonl`:
utterances, chat responses, mode changes, memory updates, action dispatches
(ok/reason), standing-order blocks, safety signals, escalations. Opt-in; a
1 024-event in-memory ring is always kept for tests and live inspection.

Tail it in a second window:

```powershell
Get-Content -Wait -Tail 20 "saves/copilot_traces/copilot_trace_P1.jsonl"
```

### 8.5.8. Which AI am I talking to?

Same resolution as autonomous agents (`src/tw2k/copilot/provider.py`):

1. Explicit `--provider` flag.
2. `TW2K_COPILOT_PROVIDER` env var.
3. First matching env: `TW2K_CUSTOM_BASE_URL` → `XAI_API_KEY` / `GROK_API_KEY`
   → `ANTHROPIC_API_KEY` → `OPENAI_API_KEY` → `DEEPSEEK_API_KEY` → `"none"`.

To pin the copilot to a specific brain while leaving the AI agents on their
own wiring:

```powershell
$env:TW2K_COPILOT_PROVIDER = "anthropic"
tw2k serve --human P1 --agent-kind heuristic
```

### 8.5.9. Mobile / phone layout

`/play` has two responsive tiers (`web/play.css`):

- `@media (max-width: 900px)` — tablet. Cockpit columns stack, 40 px touch
  targets on PTT / TTS / voice-lang buttons, unwrapped chat form.
- `@media (max-width: 720px)` — phone. Voice buttons go icon-only, mode
  row becomes horizontally scrollable, chat input expands to full width.

No native app — just open `/play` in mobile Safari/Chrome on the same LAN.

### 8.5.10. Headless human-sim (no browser, no uvicorn)

For CI or scripted regressions, drive the entire copilot pipeline from the
CLI with zero API keys:

```powershell
tw2k human-sim 7 "run a quick trade loop" --demo trade
```

Prints a structured JSON summary (chat turns, dispatched actions, task
final status, copilot/human event counts, tail of the engine log). Built-in
demos: `--demo pass` and `--demo trade`. `--script file.json` loads arbitrary
scripted responses; `--provider anthropic|openai|xai|...` flips to a live LLM.

---

## 9. Extending

See `docs/ARCHITECTURE.md` for the code layout.

- **New agent** — subclass `tw2k.agents.base.BaseAgent`, implement `async def act(obs)`. Wire it in via the runner.
- **New action** — add a variant to `ActionKind`, write a handler in `engine/runner.py`, and add a stanza to the LLM system prompt in `agents/prompts.py`.
- **Tuning** — edit constants in `engine/constants.py` (port distributions, turn costs, ship specs, victory thresholds).
- **New ship class** — add a row to `SHIP_SPECS` in constants and a `ShipClass` enum value in `models.py`.

---

## 10. Quick command recap

```powershell
tw2k serve                  # default: 2 LLM agents, 1000 sectors, 10 days, port 8000
tw2k serve --agent-kind heuristic --max-days 3    # no-cost sanity check match
tw2k serve --human P1 --agent-kind heuristic --starting-credits 75000   # play as P1 with AI opponents + copilot at /play
tw2k sim --seed 1 --max-days 2                    # headless simulation, prints summary
tw2k probe --seed 42                              # inspect universe generation
tw2k human-sim 7 "run a quick trade loop" --demo trade   # headless copilot pipeline (no browser)
```

Then browse to [http://localhost:8000](http://localhost:8000) and enjoy the show.
