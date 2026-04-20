# TradeWars 2002 — AI Edition (TW2K-AI)

A faithful, from-scratch reimplementation of Chris Sherrick's **TradeWars 2002** (the BBS door game from 1986), designed for **LLM-driven agents** to play head-to-head while you spectate in real time — and, as of Phase H, for **you to jump in as a human player** with a voice-driven AI copilot flying wingman.

## What this is

- A full-fidelity TW2002 game engine written in Python (sectors, warps, ports, ships, combat, fighters, mines, planets, Ferrengi, corporations).
- A pluggable **agent layer** where each player is an LLM that reasons about strategy, trades, scouts, wages war, and can form or betray alliances.
- A **spectator-first web UI** — a live galaxy map, event feed, per-agent status panels, and a "thought log" window into each agent's reasoning so you can enjoy watching the match unfold.
- A **human cockpit at `/play`** (Phase H) — manual controls, live observation feed, and a voice-aware AI copilot along a *Manual → Advisory → Delegated → Autopilot* spectrum, with long-term memory, what-if preview, 9-language voice, mobile-friendly layout, and structured JSONL decision tracing. Full story in `docs/HUMAN_COPILOT_PLAN.md`.

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

From `/play` you can manually click/type actions, push-to-talk voice commands, flip to Autopilot to have the copilot run a trade loop hands-off, and say "stop" to take the wheel back. The spectator view (`/`) and the cockpit are linked both ways (`🧑 Cockpit` / `◎ Spectator` buttons in the headers).

See `docs/USER_GUIDE.md` §8.5 for the full human-copilot walkthrough, `docs/HUMAN_COPILOT_PLAN.md` for the design doc + changelog, and `docs/DESIGN.md` for the underlying game mechanics.

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
