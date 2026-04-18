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
tw2k sim --seed 1 --max-days 2                    # headless simulation, prints summary
tw2k probe --seed 42                              # inspect universe generation
```

Then browse to [http://localhost:8000](http://localhost:8000) and enjoy the show.
