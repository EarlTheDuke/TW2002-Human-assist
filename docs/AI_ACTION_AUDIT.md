# AI Action Audit — April 2026

## Tl;dr

Before this audit, TW2K-AI's LLM agents could *literally not* claim a planet even
if the prompt asked them to. Three independent bugs compounded:

1. **Prompt gap:** 33 engine action verbs existed, only 16 were documented to the LLM.
   Critically missing: `deploy_genesis`, `assign_colonists`, `build_citadel`,
   `photon_missile`, `probe`, `plot_course`, `propose_alliance`, `corp_deposit`.
2. **Game-mechanics bug:** Genesis-deployed planets spawned with **0 colonists**.
   Citadel L1 requires 1,000. Colonist growth is `total * 5%` = 0 forever.
   The entire S3/S4/S5 progression path was unreachable in the current engine.
3. **Silent failures:** when an LLM issued an illegal action the engine returned
   an error string but the next observation only surfaced it via the global
   `recent_events` feed, buried behind up to 12 other events. Agents commonly
   got stuck re-issuing the same failing action turn after turn.

All three are fixed in the same changeset. This doc captures the audit for
future reference and lists follow-ups.

## Evidence

### Prompt vs. action space diff

Engine `ActionKind` enum (from `src/tw2k/engine/actions.py`) has 33 kinds.
The old `SYSTEM_PROMPT` listed 16. The 17 missing (pre-fix):

```
deploy_genesis       photon_missile       probe
assign_colonists     deploy_atomic        plot_course
build_citadel        query_limpets        corp_deposit
propose_alliance     accept_alliance      break_alliance
corp_withdraw        corp_memo
```

Every missing verb was a legitimate, routable handler. Not vapourware.

### Real match behavior (artifacts/run-20260418T161349Z-smoke)

```
kind             count
agent_thought    24,500
warp                522
trade               144
```

No `land_planet`, no `deploy_genesis`, no `buy_ship`, no `build_citadel`.
The agents spent the entire match warping and trading.

### Heuristic agent was also weak

`src/tw2k/agents/heuristic.py` only emits `WARP`, `TRADE`, `BUY_EQUIP`,
`ATTACK`, `WAIT`. It's a fine baseline for trade loops but gives us zero
signal on the planet/citadel arc. Treat it as a sanity baseline, not a
"is the full game functioning" proxy.

### Day-2 stuck-agent example (from today's LLM sanity run)

```
step=40 day=2 P2@sector475 credits=19600 turns=18/20 last_act_dt=6.8s
step=50 day=2 P2@sector475 credits=19600 turns=18/20 last_act_dt=9.1s
step=60 day=2 P2@sector475 credits=19600 turns=18/20 last_act_dt=10.3s
step=70 day=2 P2@sector475 credits=19600 turns=18/20 last_act_dt=5.8s
```

Same sector, same turn count — each LLM call succeeded as an API round-trip,
but the ACTION kept getting rejected by the engine and the agent never saw
a clear "your last action failed, because X" signal.

## Fixes shipped

### 1. Game mechanic — Genesis seed population

`src/tw2k/engine/runner.py::_handle_deploy_genesis` now seeds fresh planets
with `GENESIS_SEED_COLONISTS` (2,500) split across the four colonist pools
(40/25/15/20% weighted) and drops a 25-unit organics stockpile so population
growth can kick in immediately.

New regression test:
`tests/test_phase_abc.py::TestPhaseA::test_a_genesis_seeds_population_enough_for_l1_citadel`
verifies the full claim→land→build path works with *zero* colonist ferrying.

### 2. Prompt — full verb coverage + planet playbook

`src/tw2k/agents/prompts.py::SYSTEM_PROMPT` now documents:

- every action verb with args + preconditions
- explicit "core progression" 6-step sequence
  (buy genesis → warp → deploy_genesis → land → build_citadel → liftoff)
- StarDock price sheet (ships + equipment) with costs and hull stats
- Citadel level tiers (L1..L6 cost/days table)
- how to pick up / rebalance colonists via `assign_colonists`
- "if your last action failed, read `recent_events` and change plan" directive

### 3. Dynamic action_hint — state-aware legal verbs

`src/tw2k/engine/observation.py::_action_hint` now takes the full player
object and emits concrete per-turn nudges:

- if at StarDock: reminder of buy_ship/buy_equip/corp_create
- if you carry genesis torpedoes outside FedSpace: "deploy_genesis HERE
  creates a planet (4 turns)"
- if cargo contains colonists: "use assign_colonists from=ship to=<pool>"
- if you own a planet in this sector: "land_planet planet_id=<id>"
- if you're landed: "build_citadel planet_id=<id> starts L<next>"
- surfaces `YOUR LAST ACTION FAILED: <reason>` from the most recent
  self-caused AGENT_ERROR / TRADE_FAILED / WARP_BLOCKED event, cleared
  once the player successfully acts

This is the highest-leverage change for LLM follow-through: the model no
longer has to remember the global verb table, it reads a live cheat sheet
every observation.

## Follow-ups (not yet shipped)

- **LLM re-verification run.** Re-run `scripts/run_match_headless.py --kind llm`
  with the updated prompt + action_hint. Expect to see `deploy_genesis`,
  `land_planet`, `build_citadel` events appear in `events.jsonl`. Rubric
  should count at least one "planet claimed" milestone by end of day 2.
- **Heuristic agent upgrade.** Teach `heuristic.py` to attempt a planet
  claim on day 2 when net_worth > 100k, so the heuristic baseline also
  exercises the full stack. This will catch future regressions where the
  claim path breaks even when the LLM isn't flaky.
- **Real Terra port (optional, nostalgia).** Authentic TW2002 had a unique
  Sol/Terra port that sold Colonists for a price. We sidestepped that by
  seeding Genesis planets directly, which is simpler and preserves all the
  downstream mechanics. Revisit if we want the classic "race to sector 1
  with a Colonial Transport" subgame.
- **Structured `last_action_error` field.** Today we surface it via the
  `action_hint` string. A dedicated `Observation.last_action_error` field
  (cleared on next successful action) would be more reliable for model
  post-processing. Low priority as long as the string form keeps working.
- **Action-telemetry rubric.** `scripts/watch_match.py` should track the
  fraction of `AGENT_ERROR` events per player and alert when a player is
  stuck (>5 consecutive failures). Makes long sanity runs self-monitoring.
