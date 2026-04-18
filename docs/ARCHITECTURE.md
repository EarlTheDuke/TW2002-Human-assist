# TW2K-AI — Architecture

## Layered design

```
 ┌───────────────────────────────────────────────────────────────┐
 │                     Browser (spectator)                       │
 │   static HTML + JS + Canvas — consumes WebSocket events       │
 └───────────────────────────────────────────────────────────────┘
                             ▲
                    WebSocket (JSON events)
                             │
 ┌───────────────────────────────────────────────────────────────┐
 │                 server/  (FastAPI + asyncio)                  │
 │  • HTTP:   / (index), /state (snapshot), /static/*            │
 │  • WS:     /ws (event stream), /ws/agent/:id (optional)       │
 │  • Runner: game loop, tick scheduler, agent dispatcher        │
 └───────────────────────────────────────────────────────────────┘
                             ▲
                             │   (in-process)
 ┌──────────────────────────┴────────────────────────────────────┐
 │                      agents/                                  │
 │  BaseAgent  ◄─ HeuristicAgent                                 │
 │             ◄─ LLMAgent (Anthropic / OpenAI backend)          │
 │  Each agent: Observation → Action + thought log               │
 └───────────────────────────────────────────────────────────────┘
                             ▲
                             │   (pure, synchronous)
 ┌──────────────────────────┴────────────────────────────────────┐
 │                      engine/                                  │
 │  Pydantic state models: Universe, Sector, Port, Ship, Player, │
 │      Planet, Corporation, Event                               │
 │  Systems: movement, trading, combat, planets, corp, ferrengi  │
 │  GameState holds everything; every mutation emits Events.     │
 └───────────────────────────────────────────────────────────────┘
```

## Key invariants

- **`engine/` is pure.** No network, no LLM, no time — just state + deterministic rules. Given the same seed and action log, it replays identically.
- **Events are the source of truth.** Every state change produces a typed `Event`. The server broadcasts events; the spectator UI reconstructs view from the event stream.
- **Agents are side-effect-free in their own process.** Given an `Observation`, they return an `Action` plus a `thought` string for display. The engine validates and applies the action.

## Data models (abridged)

### `engine/models.py`

```python
class Universe(BaseModel):
    seed: int
    sectors: dict[int, Sector]
    players: dict[str, Player]
    corporations: dict[str, Corporation]
    day: int
    tick: int
    events: list[Event]            # full history
    config: GameConfig

class Sector(BaseModel):
    id: int
    warps: list[int]                # out-edges
    port: Port | None
    planet_ids: list[int]
    fighters: FighterDeployment | None
    mines: list[MineDeployment]
    nav_hazard: float               # ionic turbulence etc

class Port(BaseModel):
    class_id: int                    # 0..8
    stock: dict[Commodity, PortStock]
    experience: dict[str, float]     # per-player familiarity

class Player(BaseModel):
    id: str
    name: str
    credits: int
    alignment: int
    experience: int
    ship: Ship
    sector_id: int
    planet_landed: int | None
    corp_ticker: str | None
    turns_today: int
    alive: bool

class Ship(BaseModel):
    ship_class: ShipClass
    holds: int
    cargo: dict[Commodity, int]      # includes COLONISTS as a pseudo-commodity
    fighters: int
    shields: int
    mines: dict[MineType, int]
    genesis: int

class Event(BaseModel):
    tick: int
    day: int
    kind: EventKind
    actor_id: str | None
    sector_id: int | None
    payload: dict
```

## Action schema

```python
class Action(BaseModel):
    kind: ActionKind                 # enum: WARP, TRADE, DEPLOY_FIGHTERS, ...
    args: dict[str, Any]
    # agent-provided rationale, never consulted by engine
    thought: str = ""
```

The engine exposes `apply_action(state, player_id, action) -> ActionResult` where
`ActionResult` contains `(new_events, observation_patch, error | None)`.

## Observation model

Agents never see the full `Universe`. They get an `Observation` containing:
- Self full state (ship, cargo, credits, alignment, turns).
- Current sector full detail + adjacent sector summaries (warps revealed).
- Known ports from an on-board **port log** (persistent memory over scans).
- Last-seen locations of other players (if in corp, always; if scanned, stale).
- Last N incoming messages.
- A **summary of significant events** since last turn (combats, corp messages, alarm triggers).

Observations are built by `engine/observation.py::build_observation(state, player_id)`.

## Agent contract

```python
class BaseAgent(Protocol):
    name: str
    player_id: str
    async def act(self, obs: Observation) -> Action: ...
```

### HeuristicAgent
Rule-based baseline for tests + fallback when no API key is configured. Implements a competent trade-loop player so we can validate combat & economy without LLM costs.

### LLMAgent
- Holds a **scratchpad** — a rolling journal of what the agent has "noticed" and planned. Passed to the LLM each turn as persistent memory.
- Prompts the LLM with: system prompt (rules brief), scratchpad, current observation JSON, and the action schema.
- Parses the LLM's JSON response: `{ thought, scratchpad_update, action }`.
- Falls back to a safe `WAIT` if the LLM output is malformed, logging the parse error as an event so spectators can see it.

## Game loop

```python
async def run_match(config):
    state = build_universe(config)
    agents = [make_agent(p, config) for p in state.players.values()]
    broadcaster = EventBroadcaster()

    while not state.is_finished():
        for agent in cycle(agents):
            if state.day_advanced_this_cycle():
                tick_day(state)
                broadcaster.emit_day_tick(state)

            obs = build_observation(state, agent.player_id)
            action = await agent.act(obs)
            result = apply_action(state, agent.player_id, action)
            broadcaster.emit_events(result.new_events)
            await asyncio.sleep(config.pacing.action_delay_s)

    broadcaster.emit_finish(state)
```

Pacing controls (default):
- `action_delay_s = 0.6` — spectators need time to read the event log.
- `llm_think_cap_s = 15` — if the LLM hasn't responded, default to WAIT.
- `day_ticks_per_hour = 120` — roughly 30s per in-game day.

## Spectator UI

Single-page app loaded from `/`:
- **Galaxy Map** (SVG) — all 1000 sectors laid out with a force-directed graph (computed once at universe generation and cached).
- **Sector detail panel** — clicking a sector shows port, planets, fighters, visitors.
- **Agent dashboards** — per-player card with credits, alignment, ship, cargo, last action, last thought bubble.
- **Event feed** — scrolling log, color-coded by event kind.
- **Timeline** — day / tick / turn used.
- **Message tab** — inter-agent hails/broadcasts.

The UI is purely a consumer of the event stream; no game logic client-side beyond view state.

## Replay & determinism

- Every match is logged to `saves/<run-id>/events.jsonl`.
- `tw2k replay <run-id>` re-broadcasts the events to the spectator UI at configurable speed.
- A match can be re-simulated from seed + action log to verify determinism (useful for regression testing).

## Testing strategy

- Unit tests per engine system (movement, trading, combat) with synthetic states.
- Property tests for universe generation (connectivity, port distribution).
- Integration test: 2 `HeuristicAgent`s run a full match to completion in under 5 seconds CPU.
- LLM-agent tests stub the API with canned responses.
