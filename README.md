# TradeWars 2002 — AI Edition (TW2K-AI)

A faithful, from-scratch reimplementation of Chris Sherrick's **TradeWars 2002** (the BBS door game from 1986), designed for **LLM-driven agents** to play head-to-head while you spectate in real time — and, as of Phase H, for **you to jump in as a human player** with a voice-driven AI copilot flying wingman.

## What this is

- A full-fidelity TW2002 game engine written in Python (sectors, warps, ports, ships, combat, fighters, mines, planets, Ferrengi, corporations).
- A pluggable **agent layer** where each player is an LLM that reasons about strategy, trades, scouts, wages war, and can form or betray alliances.
- A **spectator-first web UI** — a live galaxy map, event feed, per-agent status panels, and a "thought log" window into each agent's reasoning so you can enjoy watching the match unfold.
- A **human cockpit at `/play`** (Phase H) — manual controls, live observation feed, and a voice-aware AI copilot along a *Manual → Advisory → Delegated → Autopilot* spectrum, with long-term memory, what-if preview, 9-language voice, mobile-friendly layout, an economy dashboard (top trade routes + price heatmap), and structured JSONL decision tracing. Full story in `docs/HUMAN_COPILOT_PLAN.md`.
- An **MCP server** (`tw2k mcp`) that exposes the copilot surface as 14 Model Context Protocol tools, so Cursor / Claude Code / any MCP client can drive a live match programmatically while you watch.
- Optional **OpenTelemetry** streaming of every copilot decision to Jaeger / Weave / Honeycomb.

## What this is NOT

- Not the original TWGS/EIS server. That's proprietary DOS-era software. This is a clean-room clone of the *mechanics*.
- Not multiplayer-over-telnet. There is no BBS emulation. The interface is a modern WebSocket + HTML spectator view + a browser-based human cockpit.
- Not a multi-human online game (yet) — one human + N AI agents per match.

## Quick start — spectate an AI-vs-AI match

```powershell
# 1) Install (Python 3.11+)
pip install -e .

# 2) Configure an LLM provider. Any of these works:
$env:ANTHROPIC_API_KEY = "sk-ant-..."
# or
$env:OPENAI_API_KEY = "sk-..."
# or
$env:XAI_API_KEY = "xai-..."        # Grok

# 3) Run a 2-agent match and open the spectator UI
tw2k serve
# Then open http://localhost:8000 in your browser
```

## Quick start — play as a human, with an AI copilot

No API keys required — the copilot falls back to the browser's built-in voice stack and heuristic agents fill the other slots. Drop an `XAI_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` into the environment to give the copilot a real brain.

```powershell
pip install -e .

# Optional: pick the copilot's brain (defaults to whichever API key it finds).
$env:TW2K_COPILOT_PROVIDER = "xai"   # or "anthropic" / "openai" / "deepseek"
$env:TW2K_COPILOT_TRACE    = "1"     # optional: JSONL decision tracing

tw2k serve `
  --human P1 `                       # P1 is you; other slots stay AI
  --agent-kind heuristic `
  --num-agents 3 `
  --starting-credits 75000 `
  --seed 777

# Then open http://localhost:8000/play in Chrome or Edge
```

From `/play` you can manually click/type actions, push-to-talk voice commands, flip to Autopilot to have the copilot run a trade loop hands-off, and say "stop" to take the wheel back. The spectator view (`/`) and the cockpit are linked both ways (`🧑 Cockpit` / `◎ Spectator` buttons in the headers). The right-column **Economy** panel surfaces the top profitable round-trips between ports you've scouted — click a route to auto-plot course to its buy port.

## Drive the copilot from Cursor / Claude Code (MCP, Phase H6.1)

```powershell
pip install -e ".[mcp]"

# In one terminal:
tw2k serve --human P1 --num-agents 3

# In your MCP client's config (Cursor / Claude Code):
{
  "mcpServers": {
    "tw2k": {
      "command": "tw2k",
      "args": ["mcp"],
      "env": { "TW2K_MCP_BASE_URL": "http://127.0.0.1:8000" }
    }
  }
}
```

Claude/Cursor now has 14 typed tools: read the live observation, chat with the copilot, flip modes, confirm plans, submit raw actions, read memory / safety / what-if. Optional bearer auth via `TW2K_MCP_TOKEN`.

## Trace every copilot decision (OpenTelemetry, Phase H6.3)

```powershell
pip install -e ".[otel]"
$env:TW2K_OTEL_ENDPOINT = "http://localhost:4318"   # OTLP HTTP
tw2k serve --human P1
```

Every chat utterance, LLM call, action dispatch, safety signal, and mode change appears as a span event on a long-lived `copilot.session` trace. Works with Jaeger, Weave, Honeycomb, or any OTLP-HTTP collector. Set `TW2K_OTEL_CONSOLE=1` to mirror spans to stdout for debugging.

## Live per-player LLM cost tracking

Every LLM call now emits an `llm_usage` event carrying provider, model,
fresh/cached/output token counts, and a USD cost computed from the
baked-in pricing table (`src/tw2k/engine/llm_pricing.py`). The runner
accumulates a per-player tally you can query any time:

```powershell
# Live match snapshot
Invoke-RestMethod http://127.0.0.1:8765/api/cost

# Offline report from a save's events.jsonl
python scripts/cost_report.py                         # latest match
python scripts/cost_report.py saves/<run>/events.jsonl --by-day
python scripts/cost_report.py --json                  # for piping
```

Default prices cover **Cursor Composer 2 Fast**, **Claude Sonnet 4.5**,
**GPT-5**, **xAI Grok-4-1-fast-reasoning**, **DeepSeek Chat/Reasoner**,
and `$0` for self-hosted `custom` endpoints. Override the whole table
by setting `TW2K_COST_OVERRIDES_PATH` to a JSON file shaped like
`{"cursor": {"composer-2-fast": {"input": 1.50, "output": 7.50}}}`
(USD per 1M tokens). The final `match_metrics` event carries an
`llm_cost.per_player` rollup so `scripts/summarize_match.py` can show
dollars alongside the other end-of-match stats.

See `docs/USER_GUIDE.md` §8.5 for the full human-copilot walkthrough, `docs/HUMAN_COPILOT_PLAN.md` for the design doc + changelog, `docs/LOCAL_STT_PLAN.md` for the upcoming faster-whisper voice pipeline, `docs/MULTI_HUMAN_PLAN.md` for the upcoming team-play design, and `docs/DESIGN.md` for the underlying game mechanics.

## Project layout

```
tw2002-ai/
├── src/tw2k/
│   ├── engine/        # Pure game engine — deterministic, fully tested
│   ├── agents/        # LLM agents (Anthropic / OpenAI backends + heuristic fallback)
│   ├── server/        # FastAPI + WebSocket broadcaster
│   └── cli.py         # Command-line entry (`tw2k serve`, `tw2k play`, `tw2k sim`)
├── web/               # Static spectator frontend (vanilla JS + Canvas)
├── docs/
│   ├── DESIGN.md      # Full game-mechanics spec
│   ├── ARCHITECTURE.md
│   ├── ROADMAP.md
│   └── USER_GUIDE.md
└── tests/
```

## Status

See `docs/ROADMAP.md` for phase tracking. This is actively under construction.

## License

MIT. Not affiliated with Epic Interactive Strategies or the TradeWars 2002 trademark — this is a tribute project.
