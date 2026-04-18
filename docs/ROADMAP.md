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
- [ ] Speed controls in UI (pause, 1×, 2×, 8×)
- [ ] Persistent match history browser
- [ ] Configurable ruleset YAML
- [ ] USER_GUIDE.md finalized

## Backlog / stretch
- Multi-agent matches (3–8 players)
- Human-in-the-loop agent
- Fine-grained ground assault
- Sub-space radio "public channel" with encryption
- Federation police AI
- ZTM-style scripting hooks for custom agents
