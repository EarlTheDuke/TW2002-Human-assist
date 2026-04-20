# TW2K-AI — Roadmap

Phased build plan. Each phase ends with a runnable, watchable artifact.

## Phase 0 — Foundation ✅
- [x] Project scaffolding, pyproject, README, gitignore
- [x] DESIGN.md, ARCHITECTURE.md, ROADMAP.md

## Phase 1 — Minimum Watchable Match (MWM) ✅
Goal: A seeded universe of 1000 sectors with 2 agents trading commodities, visible in a live browser UI.

- [x] Engine models (Universe, Sector, Port, Ship, Player, Event)
- [x] Universe generator (connected graph, port placement, planet seeding, 2D layout)
- [x] Movement + turns + FedSpace
- [x] Port trading with floating prices
- [x] Action schema + engine.apply_action
- [x] Observation builder
- [x] HeuristicAgent (baseline trader)
- [x] Event broadcaster + in-process runner
- [x] FastAPI server + WebSocket feed
- [x] Spectator UI: galaxy map + event log + agent panels + transmissions
- [x] CLI: `tw2k serve`, `tw2k sim`, `tw2k probe`

**Exit criteria:** Run `tw2k serve`, open browser, watch two heuristic traders accumulate credits for 1 in-game day. ✅

## Phase 2 — Combat & Territory ✅
- [x] Haggling (unit_price parameter with success probability curve)
- [x] Ship classes + StarDock upgrades
- [x] Fighters (deploy, offensive/defensive/toll modes)
- [x] Mines (armid, limpet)
- [x] Ship-vs-ship combat
- [x] Ferrengi NPC spawn + daily scaling
- [ ] Richer sector claim visualization on map (phase 6)
- [ ] HeuristicAgent combat behavior beyond basic ferrengi check (phase 6)

**Exit criteria:** Agents fight Ferrengi, claim sectors, and can kill each other outside FedSpace. ✅

## Phase 3 — Planets & Industry ✅ (core)
- [x] Planet models + classes (M, K, L, O, H, U, C)
- [x] Colonists + production simulation per-day
- [x] Land / liftoff
- [ ] Citadels (levels 1–6) — structural only; full mechanics in phase 6
- [x] Genesis Torpedoes (cost modeled; creation action pending)
- [ ] Planet siege / capture (stretch)
- [ ] Planet UI overlay (stretch)

## Phase 4 — Corporations & Diplomacy ✅
- [x] Corp formation, invites, shared treasury
- [x] Messaging (hail, broadcast)
- [x] Corporate Flagship & Imperial StarShip (ship spec)
- [x] Intel sharing between corp members (observation builder)
- [x] Alliance / betrayal mechanics (join / leave)

## Phase 5 — LLM Agents ✅
- [x] `LLMAgent` with Anthropic backend
- [x] `LLMAgent` with OpenAI backend
- [x] Scratchpad / persistent memory
- [x] Structured JSON output with robust parsing + fallback
- [x] Thought bubble display in UI
- [x] Prompt engineering: rules brief, strategy primer, observation format
- [x] Heuristic fallback on repeated LLM failures

**Exit criteria:** Two Claude (or two GPT) agents play a full match end-to-end, negotiate an alliance, and one eventually betrays or is eliminated. ✅ (ready to run; depends on API key)

## Phase 6 — Polish & Replay
- [ ] Replay mode (`tw2k replay <id>`)
- [x] Speed controls in UI (pause, 1×, 2×, 8×)
- [ ] Persistent match history browser
- [ ] Configurable ruleset YAML
- [x] USER_GUIDE.md finalized

## Phase H — Human Player + AI Copilot ✅ (through H5.5)

Goal: add a real human player to the live multi-agent match with a dedicated
cockpit UI, voice I/O, and an AI copilot that can plan, execute, and narrate
on the human's behalf along a *Manual → Advisory → Delegated → Autopilot*
spectrum. Full design doc: `docs/HUMAN_COPILOT_PLAN.md`.

- [x] **H0** — `PlayerKind.HUMAN`, `HumanAgent` / `ScriptedHumanAgent`,
      scheduler blocking on `HUMAN_TURN_START`, `POST /api/human/action`,
      `tw2k serve --human P1` flag, optional `--human-deadline-s` auto-WAIT.
- [x] **H1** — `/play` cockpit UI (three-column: sector/warps · ship+cargo+actions
      · events/copilot/inspector), `GET /api/match/humans` + `/api/human/observation`,
      10 action forms (warp, trade, scan, probe, land, liftoff, hail, broadcast, …),
      keyboard shortcuts W/S/P/B/L/./Esc/Enter/F5/?.
- [x] **H2** — `tw2k/copilot/` subpackage: tool catalog (`tools.py`), provider
      facade (`provider.py`), `ChatAgent` / `TaskAgent` / `UIAgent`,
      `CopilotSession` with four-mode spectrum, standing orders, confirm/cancel,
      active-task banner; `/api/copilot/{state,chat,mode,confirm,cancel,...}`;
      copilot-originated actions tagged `actor_kind="copilot"` end-to-end.
- [x] **H2.5** — `tw2k human-sim <seed> "<intent>"` headless CLI runs the full
      ChatAgent → TaskAgent → scheduler pipeline with no browser / uvicorn,
      built-in scripted responders (`--demo pass`, `--demo trade`) for
      zero-API-key CI.
- [x] **H3** — browser push-to-talk (Web Speech API), hold-Space binding,
      commodity + sector-number grammar hints via `normalizeVoiceTranscript()`,
      interim results in PTT status pill.
- [x] **H4** — browser TTS (`speechSynthesis`) with debounce + speaking pulse,
      always-on autopilot interrupt listener (`stop`/`hold`/`pause`/`cancel`),
      `safety.py` escalation (hostile fighters / low turns / low credits / combat),
      red escalation banner, 7.5 s idle-report watchdog for long tasks.
- [x] **H5 (first pack)** — copilot long-term memory (prefs, learned rules,
      favorite sectors, JSON persistence, `remember X = Y` / `forget X` NL hooks),
      structured JSONL decision tracer (`CopilotTracer`, opt-in via
      `TW2K_COPILOT_TRACE=1`), what-if preview on pending plans (credit/turn/
      cargo/risk heuristics, dashed "Predicted outcome" card), 9-language voice
      (BCP-47 selector persisted in `localStorage`), mobile-friendly `/play`
      layout (900 px tablet / 720 px phone media queries).
- [x] **H5.5 polish** — fixed manual-cockpit warp/probe/hail key mismatch
      (`to` → `target`), added LLM tool-arg synonym normalizer (`destination`/
      `dest`/`sector` → `target`, `planet` → `planet_id`, `quantity` → `qty`, …)
      so autopilot survives LLM tool-use slop, added reciprocal `🧑 Cockpit`
      link in spectator header.

**Exit criteria:** a human can open `/play`, manually move + trade, hand control
to Grok/Claude/GPT-4o via voice or text, watch a `profit_loop` task run hands-off
with TTS narration, interrupt with "stop", and have preferences remembered across
sessions. ✅

### Phase H deferred (next session / H6+)
- Deepgram STT / Cartesia / ElevenLabs TTS upgrades (currently browser-only).
- MCP-exposed copilot tools (let Claude Code / Cursor drive the game).
- Weave / OpenTelemetry streaming of the existing JSONL trace events.
- Multi-human multiplayer in one match, with per-human voice channels.
- Economy dashboards on `/play` (price heatmaps, trade-route suggestions
  backed by the what-if heuristic).

## Backlog / stretch
- Multi-agent matches (3–8 players)
- Fine-grained ground assault
- Sub-space radio "public channel" with encryption
- Federation police AI
- ZTM-style scripting hooks for custom agents
