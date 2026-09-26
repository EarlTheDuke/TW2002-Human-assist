# Competitive seat bot from fogged observation (2026-09-24)

> **Status 2026-09-26 (Commander):** N1-N4 delivered and merged onto `feature/seat-bot-competitive` (PRs #2, #4, #5, #6 landed via #7; merge `c225784`). Superseded PR #3 closed. **N5** live rematch (seed 250925, 2xQwen + 3xKimi + P6 Commander, `--record`) starting from the merged tip.

**Master plan** for Path-B / seat-fogged competitive brain work. Slices **S1–S6 delivered** (tip includes `e8c2f18` / docs `93b8069` on `feature/grok-bot-harness` ≡ `origin/feature/seat-bot-competitive`).

**Next phase (authoritative detail):** `docs/plans/2026-09-26-seat-bot-next.md` — steps **N1–N5** after the qwen2-kimi3-grok playtest. Do not contradict that plan; this file absorbs its corrections into the master slice order.

## Goal
Build a competitive TW2K seat player that decides **only** from the per-seat observation / mailbox feed (legal_actions, cargo, credits, known map, owned_planets, events). **Hard ban:** no god-eye `/state`, no reading other seats, no spectator dumps.

Original acceptance (S1–S4 era): Path-B / seat brain completes genesis → land → build_citadel → colonist ferry from observation alone, then holds vs 3xKimi for a short match without Commander hand-patching mid-match.

**Updated acceptance (N phase):** solo day-10 net worth **≥ 400k** on seed **250925** (and competitive rematch vs same lineup after N1–N4), with StarDock reached by routing (`plot_course 1`) not search, and growth-aware colony play (organics / citadel timing / value-per-turn).

## Why (evidence trail)
1. **Kimi3** (`docs/playtests/multibot-2026-09-23-kimi3/`, seed 230923): winner ~427k NW via early genesis + citadel growth; Path-B finished ~99k after hand-patched loops. Full chronology: `FEEDBACK.md`.
2. **qwen2-kimi3-grok** (`docs/playtests/multibot-2026-09-25-qwen2-kimi3-grok/`, seed **250925**, 6 seats, 120 turns/day, 100k start): live P6 ran **S3-era modules** (process started before S6 commit `e8c2f18`); never found StarDock — 96 sectors / 120 warps, credits stuck **100585**. Seed geometry: spawn sector **6**, StarDock (1) neighbors **44/452/493**, shortest path **8 warps**. Current code offline replay from sector 6 @ 100k: StarDock **T1**, CargoTran **T2**, Genesis **T7**, citadel **T9** day 1. Bigger gap is **post-StarDock economy** (ferry burn, organics by class, early L2, `target_planets=2`). See seat-bot-next for verified numbers.

## Non-goals
- S7 /bot polish/a11y (separate)
- xAI/Grok API seat brains
- Changing match economy balance (except engine **correctness**: `plot_course execute` must not be legal when the first hop is unaffordable)
- God-state coaching tools
- Ether probes / FedSpace heading as the StarDock strategy (probes cost money; `plot_course 1` is free and routes the real graph)

## Corrections vs earlier Grok / status-report suggestions (binding)
| Wrong / incomplete | Correct |
|---|---|
| Prefer paths toward FedSpace / use ether probes to find StarDock | **`plot_course` to StarDock (sector 1) even when unseen.** FedSpace is not clustered on StarDock on seed 250925. Probes cost ~5k; plot is free. |
| "Explore until StarDock known" ladder rung | Fatal on large maps. Remove the gate; fall back to exploration only if the engine rejects the plot. |
| Live P6 failure = current brain is weak at finding StarDock | Live process loaded **pre-S6** code; current tip already autopilots on this seed offline. Restart-brain-after-update is an ops rule. |
| Finding StarDock is the main remaining problem | **Economy after StarDock** is the bigger problem (poor seats, ferry NW waste, organics, citadel timing, genesis count, value-per-turn). |
| Treat ABA revisits as the primary explore fix | Real but secondary; frontier-directed explore (plot to nearest known sector with unvisited neighbour) fixes ABA and dead-ends. |
| Feed spectator `/state` into seat brain for recovery | Operator monitoring only — **never** into the seat brain. |

## Delivered slices (S1–S6) — do not re-open unless regression
| Slice | What | Tip |
|---|---|---|
| **S1** | Observation parity: `owned_planets` colonists / origin / stockpile | `e04103e` / PR #1 |
| **S2** | Progress-based `StallDetector` (`src/tw2k/agents/stall.py`) | `557b780` |
| **S3** | Goal-driven `SeatBrain` + `seat_brain_v2` runner | `205bb10` |
| **S4** | Seat-only acceptance harness (record → replay, storyboards) | `7a9813d` |
| **S5** | Docs (observation fields, banned god-state, goal ladder) | **Still open / parked** — update when convenient; N-phase docs may subsume |
| **S6** | Rivals / own failures / orphaned_planets mid-game pivots | `e8c2f18` |

S3 ladder still in code (to be replaced/adjusted by N1–N3): explore until StarDock known → CargoTran → genesis → deploy → citadel → ferry. That explore gate is the critical N1 bug.

## Next slices (N1–N5) — detail in seat-bot-next

Prove **each** step in offline replays across several maps **before** any live rematch. Use S4 harness + `--record` traces.

### N1 — Route instead of search (critical, ~small)
- When the ladder needs StarDock: `plot_course 1` (execute) **regardless** of whether sector 1 is in memory; explore only if plot rejected (S6 failure bans already apply).
- Poor seats: **earn** (trade known ports) before StarDock; go to StarDock when CargoTran or genesis is affordable.
- Exploration when needed: frontier-directed (plot through known warps to nearest known sector with an unvisited neighbour), not greedy local warps.
- **Done when:** seed 250925 from sector 6 reaches StarDock on day 1 at **100k and 20k**; 20k seat makes trade profit on day 1; ABA bounces ≤ 2 per 100 turns in replays.

### N2 — Growth-aware colony management (high)
- Observation (owner-only): per owned planet `production` per pool, organics consumption/day, `growth_active`, `organics_days_left` (from class coefficients already in `planets.py`).
- Brain: size organics pool from class coefficient; when `organics_days_left` < 2, buy cheap organics and `dump_planet_cargo`.
- Citadel: do not burn growth base early (L2 too soon killed compounding in replay). Next tier only if colonists after build stay above a floor, or last ~2 days. A/B before adopting.
- **Done when:** no owned world's organics stockpile hits 0 in a 10-day replay; day-10 NW beats current brain on ≥ 4 of 5 seeds.

### N3 — Value-per-turn allocator (high)
- Replace fixed post-genesis rung priority with estimates: trade (profit/turns), ferry (only for planned tier / starving world), genesis #N (25k + expected growth), organics resupply, sell planet stockpile (`load_planet_cargo` → port).
- Raise `target_planets` **above 2** when affordable (every world compounds; genesis purchase is NW-neutral).
- **Done when:** ferry turns < 40% in 10-day replays; day-10 NW **≥ 400k** solo on seed 250925 (Kimi3 winner benchmark 427k).

### N4 — Ops hygiene (medium, quick)
- `seat_brain_v2.py`: log git SHA + module mtime at start and in every `turns.jsonl` row; write `live_summary.json` every decision (day, sector, credits, NW, goals, planets, last action, stall/replan counts).
- Runbook: after any brain commit, **restart the brain process only**; verify SHA line.
- Engine: `plot_course execute` legality must reflect "first hop affordable" (today ok with 0 hops / free — brain guards it; other seats don't).

### N5 — Live validation
- Same lineup, same seed (or fresh + 250925), brain at N1–N4 tip, `--record` on. Compare P6 vs LLM seats by day; playtest notes; offline replay of recorded trace via S4 harness.

### Live match options (DECIDED 2026-09-26 morning PT)
- **Chosen: A + stop.** Ben stopped the live qwen2-kimi3-grok match mid-match day ~3 / tick ~773 (2026-09-26 morning PT). Leave as documented failure case (S3 brain cannot leave explore on large map). Proceed N1–N5 offline.
- **B.** Closed for this match — Restart **only** the P6 brain process (not host) with current tip; label remainder "S6 brain from day 3".
- **C.** Closed for this match — Finish match, then rematch same seed after N1–N3 for clean comparison.

## Code touchpoints (paths only — implementers)
- Brain ladder / explore / plot / economy / ferry / citadel / organics: `src/tw2k/agents/seat_brain.py` (`_explore_for_stardock`, `_travel`, `_plot`, `_at_stardock`, `_earn`, `target_planets`, assign/dump organics)
- Runner / `turns.jsonl` / `--record` / (missing) `live_summary.json`: `scripts/seat_brain_v2.py`
- Thin wrappers: `scripts/commander_p4_brain.py`
- `plot_course` legality: `src/tw2k/engine/legality.py` (~plot_course always-legal); execute path in `src/tw2k/engine/actions.py` / runner
- Growth / class coeffs / organics gate: `src/tw2k/engine/planets.py`; NW rules: `src/tw2k/engine/victory.py`
- Owner observation fields: `src/tw2k/engine/observation.py` (`owned_planets`)
- Offline replay harness: `src/tw2k/agents/seat_acceptance.py`, `scripts/seat_brain_acceptance.py` (`record` / `replay` / storyboards); live tee via `seat_brain_v2.py --record`
- Stall helper: `src/tw2k/agents/stall.py`

## Constraints
- Branch: continue `feature/grok-bot-harness` **or** `feature/seat-bot-competitive` (tips currently aligned @ `93b8069`). Prefer a clean tip for cloud agents; avoid the dirty local working tree on VENGEANCE unless intentionally syncing docs-only.
- Never commit tokens, `.env`, `.tw2k/*` secrets, live tunnel URLs.
- Keep existing mailbox / external harness protocol.
- Prove offline before live rematch. Do not mid-patch the live match unless Ben explicitly chooses option B.

## Done when (whole Path-B competitive track)
1. ~~S1–S4 (+ S6) tests green~~
2. N1–N3 offline A/B proofs pass acceptance in seat-bot-next
3. N4 ops (SHA in logs, `live_summary.json`, plot_course legality) landed
4. N5 live rematch logged; P6 competitive with LLM seats on day-10 NW (≥400k solo benchmark on 250925)

## References
- **Next plan (N1–N5 detail):** `docs/plans/2026-09-26-seat-bot-next.md`
- Prior S6 detail: `docs/plans/2026-09-25-seat-bot-s6-rivals-events.md`
- Playtests: `docs/playtests/multibot-2026-09-23-kimi3/`, `docs/playtests/multibot-2026-09-25-qwen2-kimi3-grok/`
- Engine: `src/tw2k/engine/observation.py`, `planets.py`, `legality.py`, `victory.py`
- Brain: `src/tw2k/agents/seat_brain.py`, `scripts/seat_brain_v2.py`
