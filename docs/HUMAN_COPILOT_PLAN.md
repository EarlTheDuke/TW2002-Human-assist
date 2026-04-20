# TW2K-AI — Human Player + AI Copilot Plan

**Status:** Design & planning. No code written yet. All of this is reversible.
**Last updated:** 2026-04-19
**Owner of this doc:** refer back to this file before each new phase. Edit in place when decisions change; append to the Changelog at the bottom.

---

## Table of contents

1. [Summary & goals](#1-summary--goals)
2. [Decisions locked in](#2-decisions-locked-in)
3. [System architecture](#3-system-architecture)
4. [Control modes (the "semi-automatic" spectrum)](#4-control-modes-the-semi-automatic-spectrum)
5. [Copilot agents (Voice / Task / UI + EventRelay)](#5-copilot-agents)
6. [Copilot tool catalog](#6-copilot-tool-catalog)
7. [Voice pipeline — Pipecat adoption](#7-voice-pipeline--pipecat-adoption)
8. [Turn / tick semantics (pause-the-world)](#8-turn--tick-semantics)
9. [The `/play` UI](#9-the-play-ui)
10. [Safety, guardrails, confirmation rules](#10-safety-guardrails-confirmation-rules)
11. [Testing strategy](#11-testing-strategy)
12. [Phased roadmap H0 → H5](#12-phased-roadmap-h0--h5)
13. [Risks and open questions](#13-risks--open-questions)
14. [Glossary](#14-glossary)
15. [Changelog](#15-changelog)

---

## 1. Summary & goals

**Primary goal:** add a human player to the live multi-agent universe, with three ways to play on the same screen:

- **Manual** — human clicks/types every action.
- **Assisted (advisory)** — AI copilot annotates and suggests, human still decides and acts.
- **Delegated / autopilot** — human speaks or types intent ("run my trade loop until 30k cr"), copilot executes, human can interrupt.

**Non-goals (for this milestone):**

- Multiplayer humans (one human + N AI agents per match).
- Mobile native app.
- Live-broadcast mode.
- Anti-cheat / matchmaking / user accounts.

**Why this matters:**
- Makes the game actually playable as a *game*, not just a spectator sim.
- Turns our well-tested agent/tool-use stack into an AI copilot — a far more valuable piece than another autonomous bot.
- Gives us a concrete product demo target: "here's a person playing a space trader sim with a Claude/Grok copilot."

---

## 2. Decisions locked in

These are settled. If we revisit one, edit here and log why in §15.

| # | Decision | Rationale |
|---|---|---|
| D-1 | **Replace one AI player with the human**, not add a 4th seat | Preserves economy tuning and existing tests (~20k cr starting, 3-player equilibrium). |
| D-2 | **Pause-the-world turn semantics** for the human (default); live-mode is opt-in later | 36,000 decisions per player per match is impossible for a human at wall-clock pace. Pause-the-world is a ~50-LOC scheduler tweak. |
| D-3 | **Adopt Pipecat (BSD-2) as the voice pipeline** instead of hand-rolling STT/LLM/TTS | Smoke-tested 2026-04-19: installs cleanly on Win + Py 3.13, every service we need imports. Saves weeks on interruption, VAD, smart-turn, and tool-cancellation work we'd otherwise do twice. |
| D-4 | **Three-agent copilot split: VoiceAgent / TaskAgent / UIAgent + EventRelay** | Borrowed from Gradient Bang (proven in a game of similar shape). Lets each role use a different model/thinking-budget/timeout. |
| D-5 | **Copilot never writes game state directly** — it submits actions through the same `apply_action` path LLM bots already use | Preserves determinism, replay, fog-of-war rules, and our entire existing test surface. |
| D-6 | **Voice is optional**; full feature set must be playable with mouse + keyboard only | Avoid holding shipping hostage to voice-stack work. |
| D-7 | **Pipecat in an opt-in install extra** (`tw2k[voice]`) | Keeps core engine/CI install lightweight (~1 GB of ML deps only when you want voice). |
| D-8 | **Log `actor` on every action event** (`heuristic` / `llm` / `human` / `copilot`) | Audit trail, replay fidelity, and post-game analytics. |
| D-9 | **Use `pipecat.services.xai.llm.GrokLLMService`**, not the deprecated `pipecat.services.grok.llm` | Namespace moved in v1.0. Old path still works but emits DeprecationWarning. |

---

## 3. System architecture

```
                      ┌─────────────────────────────────────┐
                      │     Browser  — two pages            │
                      │                                     │
                      │  /         (spectator, existing)    │
                      │  /play     (human cockpit, new)     │
                      └─────────────────────────────────────┘
                           ▲                   ▲      ▲
                           │                   │      │
                           │ WebSocket (state) │      │ WebRTC audio
                           │                   │      │   (optional, voice mode)
                           ▼                   ▼      ▼
  ┌──────────────────────────────┐        ┌────────────────────────────┐
  │  TW2K engine server          │◄──────►│  Copilot service           │
  │  (existing FastAPI +         │  HTTP  │  (new, Pipecat-based)      │
  │   asyncio + our runner)      │  tools │                            │
  │                              │        │  • VoiceAgent (live chat)  │
  │  • / (spectator)             │        │  • TaskAgent  (autopilot)  │
  │  • /state  (JSON snapshot)   │        │  • UIAgent    (fast reads) │
  │  • /events (WebSocket)       │        │  • EventRelay (msg bus)    │
  │  • /api/action   (new)       │        │  • Pipecat pipeline:       │
  │  • /api/human/action (new)   │        │    STT → LLM → TTS + VAD   │
  │  • /api/copilot/...  (new)   │        │    + interruption handling │
  └──────────────────────────────┘        └────────────────────────────┘
                 ▲
                 │ (in-process, unchanged)
                 │
  ┌──────────────┴───────────────┐
  │  agents/                     │
  │   BaseAgent                  │
  │    ├─ HeuristicAgent         │
  │    ├─ LLMAgent (Grok/Claude) │
  │    └─ HumanAgent (NEW)       │     waits on /api/human/action
  └──────────────────────────────┘
                 ▲
                 │ (pure, deterministic)
                 │
  ┌──────────────┴───────────────┐
  │  engine/                     │   models.py, runner.py,
  │  Universe / Sector / Port /  │   combat.py, planets.py,
  │  Ship / Player / Event …     │   ferrengi.py, observation.py
  │  apply_action(...) → Events  │   — unchanged by this project
  └──────────────────────────────┘
```

Key properties:

- **Engine is untouched logic-wise.** The only engine changes are: `PlayerKind.HUMAN`, a wait state in the scheduler, and tagging `actor` on action events.
- **Copilot runs as a separate process/subtask.** If it crashes, manual play still works. If the engine crashes, the copilot can surface the error and retry on reconnect.
- **The copilot is a client of the engine**, exactly like the browser is. It speaks JSON over HTTP + WebSocket. No shared memory.
- **WebRTC is peer-to-peer** (browser ↔ copilot), no cloud dependency. We use Pipecat's `SmallWebRTCTransport`.

---

## 4. Control modes (the "semi-automatic" spectrum)

Four explicit modes the human can switch between at any time (radio buttons + hotkey).

| Mode | Who decides? | Who executes? | When useful |
|---|---|---|---|
| **Manual** | Human | Human | Learning, delicate fights, experimentation |
| **Advisory** | Human | Human (copilot annotates options, no action on its own) | Default for most decisions |
| **Delegated** | Human expresses intent ("warp to 874 and sell fuel_ore") | Copilot translates & executes | Routine trades, repetitive hops |
| **Autopilot** | Copilot within standing orders + guardrails | Copilot (human can interrupt any time) | Long trade loops, idle farming, "wake me when something interesting happens" |

**The engine doesn't distinguish Advisory/Delegated/Autopilot** — all it sees is an action with `actor=copilot` vs `actor=human`. The UX differences are entirely in the UI and copilot prompt.

Transitions between modes are cheap and can happen mid-turn. Saying "stop" or hitting the Manual button always works and always cancels the current copilot step *before* the next engine call.

---

## 5. Copilot agents

Three specialized agents that share an event bus. Based on Gradient Bang's architecture. The same pattern works whether we're in text-only H2 or full voice H4.

### 5.1 VoiceAgent
- **Role:** real-time conversation with the human.
- **Latency target:** first speech token within 1.5s of end-of-speech.
- **LLM:** cheap & fast, no thinking budget. Default **Claude Haiku** or **Grok Fast**.
- **Tools:** action tools (warp/buy/sell/…), dialog tools (`ask_human`, `speak`), planning tools (`find_path`, `evaluate_trade_pair`), `start_task()` / `cancel_task()`.
- **Responsibilities:**
  - Interpret the human's voice/text.
  - Emit single actions or short plans directly (< 5 steps).
  - Hand off long/complex plans to TaskAgent via `start_task()`.
  - Narrate what's happening (with TTS in H4+).
  - Handle clarifying questions.

### 5.2 TaskAgent
- **Role:** long-running autonomous plans the human approved and walked away from.
- **Latency target:** none — can afford thinking tokens.
- **LLM:** higher-quality, extended-thinking allowed. Default **Claude Sonnet** (expensive but rare).
- **Lifetime:** hard-capped (e.g. 30 min) so it can't run forever; cancel-on-interruption always on.
- **Tools:** full action set, `speak()` (reports back through VoiceAgent), `request_confirmation()` (bubbles to human for guardrail events).
- **Pattern:** human says "run a trade loop until I hit 30k credits or something breaks." VoiceAgent calls `start_task("profit_loop", target_cr=30000)`. TaskAgent runs turns in the background, reporting via `speak()` periodically (idle-report pattern — silence > 7.5s → one-sentence status).

### 5.3 UIAgent
- **Role:** instant answers for the `/play` UI (and for VoiceAgent's planning calls).
- **Latency target:** <500ms per query. Mostly cached from game state, not LLM-driven.
- **LLM:** often none. When used: fast cheap models. No thinking budget.
- **Examples:** "what's my current status?", "list ports within 3 hops sorted by margin," "plot a course to 874."
- **Why separate:** makes UI responsiveness independent of the live voice conversation.

### 5.4 EventRelay
- **Role:** message bus between the three agents + the engine + the UI.
- **Concretely:** a tiny publish/subscribe over asyncio queues in the copilot process, plus a WebSocket to the `/play` frontend.
- **Messages:**
  - `engine_event` (game events — trades, combat, warps…)
  - `human_utterance` (voice-transcribed or typed)
  - `copilot_speech` (for TTS + transcript)
  - `task_progress` (TaskAgent → VoiceAgent → human)
  - `confirmation_request` / `confirmation_response`
  - `mode_change`

---

## 6. Copilot tool catalog

Tools are defined **once** in a JSON schema file and reused across all three agents and all LLM providers (Anthropic/xAI/OpenAI all support compatible tool-use shapes).

### 6.1 Action tools — one per engine action
`warp` `plot_course` `scan` `probe` `buy` `sell` `refuel` `haggle_settle` `deploy_fighters` `upgrade_ship` `corp_invite` `corp_send_msg` `attack` `deploy_genesis` `land_planet` `liftoff` `pass_turn`.

One-to-one mapping with `engine.apply_action`. Validation happens engine-side; the copilot just passes args.

### 6.2 Planning tools (copilot-internal, never sent to engine)
- `find_path(from_sector, to_sector, avoid=["prison","ferrengi"])` — Dijkstra over `player.known_warps`. Returns warp sequence or `null` if unreachable.
- `evaluate_trade_pair(buy_sector, sell_sector, commodity)` — uses `known_ports` snapshots to project margin per unit.
- `scan_trade_plan(commodity)` — ranks all known port pairs by profit per turn.
- `simulate_plan(plan)` — dry-run the plan against current state locally, return predicted credit/cargo trajectory + flagged risks.
- `check_standing_orders(plan)` — verify plan violates no active standing order.

### 6.3 Dialog tools
- `speak(message, urgency)` — queue text for TTS + transcript (H3+).
- `ask_human(question, options[])` — stop and request a decision.
- `remember(fact)` — append to the player's `scratchpad` (persists across turns).
- `forget(fact_pattern)` — clear a memory.

### 6.4 Orchestration tools
- `start_task(kind, params)` — VoiceAgent hands work to TaskAgent.
- `cancel_task(task_id, reason)` — kill in-flight TaskAgent work.
- `pause_autopilot()` / `resume_autopilot()`.
- `set_standing_order(rule)` / `clear_standing_order(rule)`.

### 6.5 Observability tools
- `get_observation()` — returns the same `Observation` the autonomous LLM agents see.
- `get_recent_events(n)` — for explaining "why did you just sell?"
- `get_my_plan()` — current multi-step plan, if any.

---

## 7. Voice pipeline — Pipecat adoption

### 7.1 Verdict (verified 2026-04-19)
**Adopt Pipecat v1.0.0.** Installs cleanly on our target platform. Covers every provider we need.

### 7.2 Smoke test results (local, 2026-04-19)

Ran in a throwaway venv on Windows 10 + Python 3.13.6:

```
pip install "pipecat-ai[webrtc,grok,anthropic,silero]==1.0.0" "pipecat-ai[websockets-base]"
```

| Check | Result |
|---|---|
| Clean install, all wheels present for Win + Py 3.13 | ✅ ~2 min, ~1 GB |
| `Pipeline`, `PipelineRunner`, `PipelineTask` | ✅ |
| `LLMContext` (v1.0 unified) | ✅ |
| `SmallWebRTCTransport` (local P2P, no cloud) | ✅ |
| `GrokLLMService` (via `pipecat.services.xai.llm`) | ✅ |
| `AnthropicLLMService` | ✅ |
| `OpenAILLMService` | ✅ |
| `SileroVADAnalyzer` (onnxruntime runs) | ✅ |
| `FrameProcessor` | ✅ |

**Two findings worth pinning:**
- **`websockets-base` extra must be installed alongside service extras** — it's a transitive dep that service extras don't auto-pull.
- **`pipecat.services.grok.*` is deprecated in v1.0** → use `pipecat.services.xai.*`. `GrokLLMService` is still the class name.

### 7.3 Pinned version
`pipecat-ai == 1.0.0` — exact pin, not `>=`. We bump manually after reading CHANGELOG.

### 7.4 The `tw2k[voice]` optional extra (to add in H3)

To `pyproject.toml`:

```toml
[project.optional-dependencies]
voice = [
  "pipecat-ai[webrtc,grok,anthropic,silero,websockets-base]==1.0.0",
  # Add [deepgram] / [cartesia] only when/if we outgrow browser speechSynthesis.
]
```

Installed via `pip install -e ".[voice]"`. Core engine, CI, tests never pay the ~1 GB dep cost.

### 7.5 Service selection matrix (initial; tunable per-player)

| Layer | MVP default | Upgrade path | Why |
|---|---|---|---|
| **STT** | Browser Web Speech API (free, Chrome/Edge) | Deepgram via Pipecat | Free to start; Deepgram is industry-leading streaming STT when we need it. |
| **LLM — VoiceAgent** | Claude Haiku 4.5 or Grok Fast | Sonnet for "strategic mode" | Latency + cost sensitive. Both have solid tool-use. |
| **LLM — TaskAgent** | Claude Sonnet 4.5 | Opus for long-horizon planning | Thinking budget + best tool-use we have access to. |
| **LLM — UIAgent** | Grok Fast (often no-LLM) | Haiku if Grok tool-use unreliable | Cheapest & fastest; results mostly cached. |
| **TTS** | Browser `speechSynthesis` (free) | Cartesia via Pipecat | Robotic but free; upgrade only when voice-output matters. |
| **VAD** | Pipecat Silero (onnxruntime, local) | Smart-turn ML model | Local, zero cost, runs offline. |
| **Transport** | `SmallWebRTCTransport` (P2P, local) | Daily (if we ever go multi-user cloud) | Zero infra for solo play. |
| **Noise suppression** | Off in dev | Krisp (Pipecat integration) in production | Not needed for local testing. |

### 7.6 Pipecat pipeline topology (H3 first pass)

```
browser mic
  → aiortc WebRTC audio frames
  → SileroVADAnalyzer (end-of-turn detection)
  → (H3) browser Web Speech transcription  OR  (H4) Deepgram STT processor
  → LLMContextAggregator (manages conversation history + tool schemas)
  → GrokLLMService  / AnthropicLLMService  (VoiceAgent role)
  → our custom ToolExecutor (routes tool calls → tw2k engine API)
  → LLMResponseAggregator
  → (H4+) Cartesia TTS  OR  browser speechSynthesis
  → WebRTC audio frames back
  → browser speakers
```

Pipecat provides every box except **ToolExecutor**, which is the thin shim we write that turns "LLM wants to call `warp(target=874)`" into an HTTP POST to `/api/human/action` and converts the engine's response back into a tool result.

---

## 8. Turn / tick semantics

The default mode for human-in-game matches is **pause-the-world**:

1. Scheduler loops through players in order.
2. When it reaches a `PlayerKind.HUMAN` player, it emits a `human_turn_start` event, transitions to `AWAITING_HUMAN_ACTION`, and **does not advance any other player** until the human submits an action (via `/api/human/action`).
3. Optional per-turn deadline: `--human-deadline-s 120` (default: none / unlimited). If set and the deadline expires, the human auto-passes.
4. AI players retain their own action delays (`--action-delay-s`) for watchability, but those are only applied when advancing *their* turn, not during the human's wait.

Live-mode (shared wall-clock) is deferred. When we add it:
- All players tick on a fixed schedule.
- Human missed-turn behavior: configurable (auto-pass / repeat-last-action / hand to copilot).
- This is the mode where the copilot earns its keep most dramatically.

**Replay implication:** every human action is logged verbatim with its full input shape (manual-click / typed-text / voice-transcript + copilot-plan-id if applicable). Replaying a human match deterministically re-fires those inputs.

---

## 9. The `/play` UI

Single dense screen. Browser-served HTML/JS (consistent with our existing spectator UI — we do not adopt React for this).

```
┌───────────────────────┬──────────────────────────┬─────────────────────────┐
│  SECTOR & MAP         │  SHIP & ACTIONS          │  COPILOT                │
│                       │                          │                         │
│ • current sector      │ • credits, cargo, fuel,  │ • Transcript (you/me)   │
│ • warps out + labels  │   fighters, HP           │                         │
│ • route plan          │ • known-ports board      │ • Mode toggle:          │
│   (dotted overlay)    │   (sector, class,        │   [Manual] [Advisory]   │
│ • adjacent sectors    │    last-seen stock,      │   [Delegated] [Auto]    │
│   (warp-in preview)   │    proj. margin, hops)   │                         │
│ • prisons highlighted │                          │ • Push-to-talk button   │
│                       │ • Quick actions:         │   (hold space)          │
│ • standing orders     │   [Warp] [Scan] [Buy]    │                         │
│   panel (togglable)   │   [Sell] [Refuel]        │ • Current plan:         │
│                       │   [Haggle…] [More…]      │   ▸ warp 874            │
│                       │                          │   ▸ sell fuel_ore       │
│                       │ • Recent failures badge  │   ▸ warp back           │
│                       │   (from `recent_failures`│   [Confirm] [Cancel]    │
│                       │    field)                │                         │
│                       │                          │ • "Copilot's view"      │
│                       │                          │   collapsible panel —   │
│                       │                          │   shows exactly what    │
│                       │                          │   the LLM sees          │
├───────────────────────┴──────────────────────────┴─────────────────────────┤
│  EVENT TICKER   ← engine events this tick, tagged by actor                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

Three design principles (from our spectator UI and Gradient Bang experience):

- **Everything the autonomous LLM sees, the human can see.** The "Copilot's view" panel exposes the same `Observation` + `action_hint` we built into `engine/observation.py` during the memory overhaul. Great for debugging, great for learning the game.
- **Quick-action buttons cover 100% of legal actions.** Voice/text is optional; the game is always playable keyboard-only.
- **Every copilot action is event-tagged.** Human can replay the match and see "this was me vs. this was the copilot."

### Keyboard shortcuts (draft, TW2002-ish)
- `W` warp, `S` scan, `P` probe, `B` buy, `L` sell, `R` refuel, `M` messages, `C` corp, `Space` push-to-talk, `Esc` cancel current plan, `1`/`2`/`3`/`4` mode switch.

---

## 10. Safety, guardrails, confirmation rules

Three layers, enforced in this order before any copilot-initiated action fires.

### 10.1 Hard confirmation list (always requires explicit human yes)
- Attack another player or corp.
- Deploy Genesis torpedo.
- Sell or scrap the ship, drop below minimum fuel for return.
- Any single action that moves > 50% of net worth.
- Any destructive action in FedSpace.

### 10.2 Standing-order check
Runs before every copilot action. Defined by the human, e.g.:
- "Never sell at < 20% margin."
- "Never warp into a sector with known Ferrengi if HP < 50%."
- "Keep ≥ 500 cr reserved for fuel home."
- "Never accept a haggle counter > 10% below list."

Blocked actions bubble back to the human as `ask_human` requests, not silent failures.

### 10.3 Sanity heuristics (cheap, no LLM call)
Leverage what we already built:
- **`recent_failures` counter** — block a 3rd attempt at the same failed action.
- **`action_hint` "REPEATED FAILURES" line** — if it fires, copilot must re-plan, not retry.
- **Cost-basis check** — reject a sell below cost basis unless explicit "dump" mode.

All three layers are **engine-enforced, not copilot-enforced.** The copilot can propose anything; `apply_action` + a new `guardrail_check` stage reject + return machine-readable reasons the copilot can verbalize.

---

## 11. Testing strategy

### 11.1 Existing tests stay green
- All-AI matches continue working. The human feature is strictly additive.
- `test_heuristic_smoke`, `test_observation_memory`, `test_replay_roundtrip`, all phase-X tests pass unchanged.

### 11.2 New tests — headless first, browser second

**Scripted-Human fixture.** An agent implementation that pulls its actions from a pre-written script. Swappable with `HumanAgent` in any test:

```python
human = ScriptedHuman([
    {"action": "scan"},
    {"action": "warp", "target": 874},
    {"action": "sell", "commodity": "fuel_ore", "haggle_pct": 20},
])
```

This is how we integration-test Phases H0 and H1 without a browser.

**Copilot round-trip tests (H2+).** Stand up a mock engine, feed VoiceAgent a known utterance, assert it emits the expected tool-call sequence. Mirrors Gradient Bang's `EventRelay↔VoiceAgent` integration tests.

**Replay tests.** A human match's event log must replay deterministically, just like AI-only matches. New fixtures: captured `human_action` events with their original verbatim inputs.

**Manual smoke.** Every phase ends with a manual play session (see §12 exit criteria). Cheap, critical.

---

## 12. Phased roadmap H0 → H5

Each phase is **independently shippable and reversible.** Each ends with a concrete, demonstrable artifact.

### Phase H0 — Foundation
*No human visible yet, no copilot. Makes everything else possible.*

- [ ] Add `PlayerKind` enum (`HEURISTIC | LLM | HUMAN`).
- [ ] `HumanAgent` class — blocks in `decide()` until a new action appears on an asyncio queue.
- [ ] `/api/human/action` POST endpoint that pushes to that queue.
- [ ] Scheduler: emit `human_turn_start` event, set `AWAITING_HUMAN_ACTION` state, don't advance others until resolved.
- [ ] `actor` field on all action events (`heuristic | llm | human | copilot`).
- [ ] Replay stores human actions verbatim.
- [ ] Tests: `ScriptedHuman` fixture; scheduler respects HUMAN wait; replay round-trips a scripted-human match.

**Exit criteria:** `tw2k serve --players heuristic,heuristic,human` starts a match that hangs forever at the human's first turn. Other AIs do not advance. No crashes.

### Phase H1 — Manual play (no AI copilot)
*Make the game actually playable by a person.*

- [ ] `/play` route + HTML/JS cockpit (see §9 layout).
- [ ] Quick-action buttons for every legal engine action.
- [ ] Keyboard shortcuts (draft map above).
- [ ] Minimap / local warp graph (reuse what we built for map-readability Phase 3).
- [ ] Known-ports board + recent-failures badge (from `observation.py`).
- [ ] "Copilot's view" collapsible panel (read-only; just renders `Observation`).
- [ ] Event ticker with actor tags.
- [ ] `--human-deadline-s` optional per-turn timeout.

**Exit criteria:** a human can play a full 5-day match against 3 Grok bots using only mouse/keyboard. All existing AI-vs-AI matches still work. All tests green.

### Phase H2 — Text copilot (advisory + delegated, typed only)
*Introduce the three-agent copilot architecture with text I/O. No voice yet.*

- [x] Copilot subpackage (`tw2k/copilot/`) with ChatAgent / TaskAgent / UIAgent + per-match `CopilotRegistry`. EventRelay reuses the existing `Broadcaster`.
- [x] Tool schema file (`copilot/tools.py`) with `TOOL_CATALOG` + cross-provider adapter (`to_openai`, `to_anthropic`); all LLMs in xAI/DeepSeek/Custom use the OpenAI shape.
- [x] Tool executor shim: `CopilotSession.tool_to_action` translates `ToolCall` → engine `Action`, routes through `HumanAgent` with `actor_kind="copilot"` via a new `Action.actor_kind` override field and scheduler-side `actor_kind_override(...)` context manager.
- [x] Chat panel in `/play` (typed input, text output) + streaming `copilot_chat` WS events.
- [x] Advisory overlays via `UIAgent.button_hints` exposed at `GET /api/copilot/hints` (rule-based, no LLM).
- [x] Plan preview + `[Confirm]` / `[Cancel]` (pending multi-step plans queued in `CopilotSession.pending_plan`).
- [x] Standing-orders store + enforcement layer (`copilot/standing_orders.py` + `CopilotSession._dispatch_one` gate; blocks logged to chat history as `standing_order_block`).
- [x] Mode toggle working for Manual / Advisory / Delegated / Autopilot (`/api/copilot/mode`).
- [x] Tests: 28 new H2 tests — tool schema, parse_tool_response fences/prose, standing orders, ChatAgent classification, `TaskAgent` loop + cancel, delegated-mode end-to-end with actor_kind assertion, pure-AI regression, UIAgent hints.

**Exit criteria:** human types "run my trade loop until 30k credits" and it runs end-to-end, including interruption via `Esc`. — **met** (covered by `test_task_agent_runs_until_target_credits_reached` + `test_task_agent_cancellation_stops_loop`).

### Phase H2.5 — Headless `human-sim` CLI (borrowed from Gradient Bang)
*Integration test harness + dev tool. Small, high-leverage.*

- [ ] `tw2k human-sim <seed> "intent string"` — runs a full copilot pipeline headlessly, no browser, emits events to stdout.
- [ ] Used as the CI-friendly integration test for Phase H2+ and as a forensic tool for debugging copilot loops.

**Exit criteria:** `tw2k human-sim 42 "find the best trade loop and run it for 5 days"` runs to completion and prints a structured summary.

### Phase H3 — Voice input (STT)
*Add Pipecat, browser-only STT first.*

- [ ] Add `tw2k[voice]` optional extra (Pipecat v1.0.0 pinned).
- [ ] Copilot service switches from text-loop to Pipecat pipeline, text channel still works as a peer input.
- [ ] Browser Web Speech API integration; transcript panel renders what was heard *before* the copilot acts.
- [ ] Push-to-talk (hold Space) in `/play`.
- [ ] `SmallWebRTCTransport` wiring.
- [ ] Voice grammar hints for sector numbers ("eight seventy four") and commodity names.

**Exit criteria:** the full Phase H2 loop works hands-free for input, on Chrome/Edge, Windows + macOS.

### Phase H4 — Voice output (TTS) + autopilot mode + interruption
*The full "semi-automatic" experience.*

- [ ] Browser `speechSynthesis` TTS channel (free MVP).
- [ ] Autopilot mode wired up; TaskAgent runs in the background.
- [ ] Idle-report loop (Gradient Bang pattern): > 7.5s silence → one-sentence status.
- [ ] Interrupt-word detection in autopilot mode ("stop" / "hold" / "pause") via always-on listening.
- [ ] `cancel_on_interruption=True` on async tool calls (Pipecat v1.0 feature).
- [ ] Safety-critical escalation ("combat imminent — take manual?").

**Exit criteria:** human plays 30 min hands-off in autopilot while the copilot narrates and only interrupts for big decisions. "Stop" always works within ~1s.

### Phase H5 — Polish & power features (any order, as needed)
- Deepgram STT upgrade for accuracy/latency.
- Cartesia / ElevenLabs TTS upgrade for voice quality.
- Copilot long-term memory ("I prefer class-7 ports").
- What-if simulator UI (draws from `simulate_plan`).
- Mobile-friendly `/play` layout.
- Weave/OpenTelemetry tracing of copilot decisions.
- Multi-language STT.
- MCP-exposed copilot tools (so Claude Code / Cursor can drive the game).

---

## 13. Risks & open questions

### 13.1 Known risks (with mitigation)

1. **Voice ambiguity.** "Sell fuel" — how much? which port? → copilot prefers to `ask_human` over guessing. Always surface the transcript before acting.
2. **Latency budget.** Voice (300ms) + STT (200ms) + LLM (800ms) + tool round-trip (100ms) ≥ 1.4s. → mandatory prompt-caching, mandatory "thinking…" indicator, VoiceAgent picks the fastest model.
3. **Trust spiral.** One bad copilot trade → human micromanages forever. → every action carries a rationale + predicted outcome. Offer `[Undo last copilot action]` for reversible moves (warp-back is always allowed).
4. **Pipecat v1.0 is 5 days old.** → pinned exact version, manual bumps after CHANGELOG review, isolated behind opt-in extra.
5. **Windows + Python 3.13 wheel matrix.** → verified 2026-04-19 in smoke test (§7.2). If a future Pipecat bump breaks on 3.13, fallback: run copilot subprocess on 3.12 venv while engine stays on 3.13.
6. **Dep footprint (~1 GB).** → opt-in extra. Anyone who doesn't need voice never installs it.
7. **Test coverage of voice paths.** → integration tests at the *tool-call* level, not the audio level (mock STT output). Manual voice smoke only at phase exits.

### 13.2 Open questions (answer before the relevant phase)

- **H0:** what's the per-turn deadline default for live-mode (which we're deferring anyway)?
- **H1:** do we render planet-surface UI now or stretch-goal it? (Current autonomous agents barely use planets.)
- **H2:** cross-provider tool schema — one JSON format, or per-provider adapters? (Gradient Bang uses a single format + adapters — preferred.)
- **H2:** should standing-orders be natural-language or structured rules? (Probably structured, parsed by copilot from NL input and surfaced back for confirmation.)
- **H3:** push-to-talk vs. wake-word — which feels less annoying? (Probably PTT for user-initiated commands, wake-word only in autopilot interrupt mode.)
- **H4:** do we let TaskAgent trigger `speak()` directly, or always route through VoiceAgent? (Routing through VoiceAgent keeps voice style consistent.)
- **H5:** MCP-exposure — worth it? How many external tools benefit?

---

## 14. Glossary

| Term | Meaning |
|---|---|
| **Pause-the-world** | Scheduler halts all players while waiting on a human turn. |
| **Pipecat** | BSD-2 Python framework for real-time voice AI pipelines. v1.0 shipped 2026-04-14. We pin 1.0.0. |
| **SmallWebRTCTransport** | Pipecat's built-in peer-to-peer WebRTC transport. No STUN/TURN needed for localhost. |
| **EventRelay** | In-copilot message bus between VoiceAgent / TaskAgent / UIAgent / frontend. |
| **Standing order** | Human-defined persistent rule the copilot must obey (e.g. "never sell below 20% margin"). |
| **Delegated mode** | Human expresses intent; copilot translates & executes one or a few actions. |
| **Autopilot mode** | Copilot runs a TaskAgent plan in the background until a guardrail fires or human interrupts. |
| **Scripted-Human** | Test fixture that satisfies the `HumanAgent` interface but pulls actions from a pre-written list. |
| **`actor` tag** | Enum stamped on every action event: `heuristic | llm | human | copilot`. |
| **Copilot's view** | Collapsible UI panel that renders the same `Observation` dict an autonomous LLM agent sees. |
| **Human-sim** | Planned CLI (H2.5) that runs the copilot pipeline headlessly for tests and forensics. |

---

## 15. Changelog

| Date | Change | Reason |
|---|---|---|
| 2026-04-19 | Initial draft. D-1 through D-9 locked in. Pipecat v1.0.0 smoke test passed on Win + Py 3.13.6. | Brainstorm → plan doc creation. |
| 2026-04-19 | **Phase H0 shipped.** `PlayerKind` enum, `Event.actor_kind`, `HumanAgent` + `ScriptedHumanAgent`, `/api/human/action` endpoint, scheduler blocks on `HUMAN_TURN_START`, `tw2k serve --human P1` flag. 9 new tests + full 222-test suite green. Manual smoke: `tw2k serve --human P2` stalls waiting on P2 while P1 (heuristic) continues to act; POST unblocks; error codes 404/409/422 verified. | H0 exit criteria met. |
| 2026-04-19 | **Phase H1 shipped.** `/play` cockpit route + `web/play.html` / `play.js` / `play.css` three-column UI (sector + warps, ship vitals + cargo + 10 action forms, events + copilot placeholder + raw-observation inspector). New endpoints: `GET /api/match/humans` (enumerates slots, carries `awaiting_input` flag so the page can enable buttons on fresh loads) and `GET /api/human/observation?player_id=` (full Observation — same object the LLM path consumes). `--human-deadline-s` CLI flag + `MatchSpec.human_deadline_s` forces auto-WAIT via `asyncio.wait_for` with a tagged `AGENT_THOUGHT auto_wait=True` event for forensics. Keyboard shortcuts W/S/P/B/L/./Esc/Enter/F5/?. 11 new H1 tests; full 233-test suite + ruff green. Manual verify on port 8005: cockpit auto-binds to the only human, shows full state + live event ticker (actor-tagged), action submit round-trips via POST /api/human/action, error codes 404/409/503 verified; pure-AI match on 8006 confirmed unaffected (empty humans list, no leaked `human` actor_kind). | H1 exit criteria met. |
| 2026-04-19 | **Phase H2 shipped.** New `tw2k/copilot/` subpackage: `tools.py` (TOOL_CATALOG + OpenAI/Anthropic adapters + `ToolCall`), `provider.py` (unified `call_llm` wrapper reusing existing Anthropic/OpenAI-compatible clients + `mock:*` responder hooks for deterministic tests), `standing_orders.py` (MIN_CREDIT_RESERVE / NO_WARP_TO_SECTORS / MAX_HAGGLE_DELTA_PCT guardrails), `chat_agent.py` (per-utterance classifier: speak / plan / action / start_task / cancel / clarify), `task_agent.py` (long-running autopilot loop with cancellation + terminal conditions), `ui_agent.py` (rule-based button tooltips + next-move heuristic), `session.py` (per-human state: mode, chat history, pending plan, active task, standing orders), `registry.py` (per-match `CopilotRegistry`). Engine: `Action.actor_kind` override field + `actor_kind_override` contextvar + scheduler wrapper so copilot-dispatched actions emit events tagged `actor_kind="copilot"` while manual human submissions stay tagged `"human"`. Server: `/api/copilot/{state,chat,mode,confirm,cancel,standing-orders,hints}` + lifespan hook rebuilds the registry on match (re)start. UI: `/play` RIGHT panel now hosts mode toggle (Manual/Advisory/Delegated/Autopilot), plan preview with Confirm/Cancel, active-task banner, chat transcript with streaming `copilot_chat` WS events, standing-orders list/form. Keyboard: `/` focuses chat, `Esc` cancels pending plan or active task, `Enter` confirms a pending plan. 28 new H2 tests (tool schema, parse_tool_response with fences/prose, ChatAgent mock round-trip, `TaskAgent` trade-loop until target credits + cancellation, standing-order block through full `CopilotSession` pipeline, actor_kind tagging end-to-end, pure-AI regression) + full 261-test suite + ruff green on all H2 files. Exit criterion: scripted trade loop reaches target credits via `TaskAgent` and is interruptible via `Esc`. | H2 exit criteria met. |
