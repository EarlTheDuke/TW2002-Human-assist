# TradeWars 2002 — AI Edition (TW2K-AI)

A faithful, from-scratch reimplementation of Chris Sherrick's **TradeWars 2002** (the BBS door game from 1986) — designed to be played by **LLM-driven agents** while you spectate in real time via a browser.

## What this is

- A full-fidelity TW2002 game engine written in Python (sectors, warps, ports, ships, combat, fighters, mines, planets, Ferrengi, corporations).
- A pluggable **agent layer** where each player is an LLM that reasons about strategy, trades, scouts, wages war, and can form or betray alliances.
- A **spectator-first web UI** — a live galaxy map, event feed, per-agent status panels, and a "thought log" window into each agent's reasoning so you can enjoy watching the match unfold.

## What this is NOT

- Not the original TWGS/EIS server. That's proprietary DOS-era software. This is a clean-room clone of the *mechanics*.
- Not multiplayer-over-telnet. There is no BBS emulation. The interface is a modern WebSocket + HTML spectator view. Human play is available via a dev CLI, but the focus is AI vs. AI.

## Quick start

```powershell
# 1) Install (Python 3.11+)
pip install -e .

# 2) Configure an LLM provider. Either one works:
$env:ANTHROPIC_API_KEY = "sk-ant-..."
# or
$env:OPENAI_API_KEY = "sk-..."

# 3) Run a 2-agent match and open the spectator UI
tw2k serve
# Then open http://localhost:8000 in your browser
```

See `docs/USER_GUIDE.md` for full instructions and `docs/DESIGN.md` for mechanics.

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
