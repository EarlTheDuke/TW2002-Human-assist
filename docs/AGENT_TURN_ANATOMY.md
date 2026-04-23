# Agent Turn Anatomy — what the LLM actually sees, when, and in what order

_Forensic audit. Generated 2026-04-17 against `main` at commit `5e88cf5`.
Every claim in this doc is backed by a live artifact in `docs/agent_turn/`._

> **Regenerate anytime with** `python scripts/dump_turn_anatomy.py`.
> The script runs a small heuristic sim to day 1 tick ~11 and dumps
> the full pipeline for one player.

**See also:** [AGENCY_INITIATIVE.md](AGENCY_INITIATIVE.md) — initiative to map directive prompt layers, baseline token budgets, and a phased path toward more model agency while keeping engine contracts.

---

## TL;DR

On every turn, the game sends the LLM **two strings**:
1. A constant **`SYSTEM_PROMPT`** (~14 KB, ~3,500 tokens) — the rules of
   the game, the worked example, and the output schema.
2. A per-turn **user message** — a compact JSON blob, ~5 KB (~1,300
   tokens) for a mid-day-1 state, describing the player's world.

The LLM replies with **one JSON object** carrying four things in a
single shot:
- A **thought** (1–3 sentences, not re-surfaced).
- A **scratchpad_update** (up to 1,500 chars, persisted; shown back next
  turn as `scratchpad`).
- A **goals** block with `short` / `medium` / `long` horizons (persisted;
  shown back next turn _as text_ at the top of `action_hint`).
- An **action** — the one verb + args that the engine executes.

**The agent writes its plan for the next turn in the SAME response as
its current action.** There is no separate planning phase.

Five artifacts in this directory capture exactly what happened on one
turn, for one player, in a live simulated match:

| File | What it is |
|---|---|
| [`system_prompt.md`](agent_turn/system_prompt.md) | Verbatim `SYSTEM_PROMPT` string sent as `role: system` |
| [`user_message.json`](agent_turn/user_message.json) | Exact JSON sent as `role: user` (the "observation") |
| [`observation_raw.json`](agent_turn/observation_raw.json) | Full `Observation` pydantic object — **superset** of what's sent |
| [`action_hint.txt`](agent_turn/action_hint.txt) | The per-turn hint strip embedded inside `user_message.json` |
| [`stage_hint.json`](agent_turn/stage_hint.json) | Auto-computed arc stage (S1..S5) |
| [`example_llm_response.json`](agent_turn/example_llm_response.json) | Plausible grok-4-fast response with goals + action |

**`cursor` provider:** the same `get_system_prompt()` + `format_observation()` strings are concatenated into one headless prompt for the Cursor Agent CLI (`agent -p --mode ask --output-format json`, model e.g. `composer-2-fast`). Auth: `agent login` or `CURSOR_API_KEY`. Env: `TW2K_CURSOR_*` in `.env.example`. If the combined prompt would exceed the Windows command-line budget, the engine temporarily uses the minimal system prompt for that turn only.

---

## 1. The pipeline, end to end

One turn of one agent, in execution order:

```
┌─────────────────────────────── server tick loop ────────────────────────────────┐
│                                                                                 │
│  1. build_observation(universe, player_id)                                      │
│       → Observation (pydantic BaseModel, ~22 fields)                            │
│       • reads:  ship, sector, adjacent sectors, known_ports, trade_log,         │
│                 scratchpad, goal_{short,medium,long}, inbox, recent_events,     │
│                 owned_planets, alliances, corp, limpets, probes                 │
│       • builds: action_hint (prose strip, computed inside this function)        │
│                 stage_hint (S1..S5 arc label, computed from obs)                │
│                                                                                 │
│  2. format_observation(obs)                                                     │
│       → str (compact JSON, currently ~5,100 chars)                              │
│       ⚠ This SUBSETS the Observation — see §4. Some fields never reach the LLM. │
│                                                                                 │
│  3. agent.act(obs)                                                              │
│       └─ LLMAgent._call_xai(observation_str)                                    │
│             messages = [                                                        │
│               {role: "system", content: SYSTEM_PROMPT},                         │
│               {role: "user",   content: observation_str}                        │
│             ]                                                                   │
│             model = grok-4-1-fast-reasoning                                     │
│             max_tokens = 1200, temperature = 0.6                                │
│             timeout = 120s (reasoning models do hidden thinking first)          │
│                                                                                 │
│  4. _parse_response(raw_str)                                                    │
│       → Action(kind, args, thought, scratchpad_update,                          │
│                goal_short, goal_medium, goal_long)                              │
│                                                                                 │
│  5. apply_action(universe, player_id, action)                                   │
│       → ActionResult(ok, error, event_seqs)                                     │
│       • Side effects (before the verb runs):                                    │
│           player.thought             = action.thought                           │
│           player.scratchpad          = action.scratchpad_update  (if provided)  │
│           player.goal_short / goal_medium / goal_long  (if provided; ""=clear;  │
│                                                        omitted=unchanged)       │
│       • Then the verb executes: warp / trade / scan / buy_ship / ...            │
│       • On `trade buy`:  cargo_cost  ← weighted-avg update                      │
│         On `trade sell`: realized_profit = (unit - basis) * qty                 │
│         Appends to player.trade_log (rolling 50)                                │
│                                                                                 │
│  6. 0.6s spectator delay ÷ speed_multiplier  →  next agent's turn               │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

Sources for every step, by line:

- `build_observation` → `src/tw2k/engine/observation.py:88-278`
- `_action_hint` → `src/tw2k/engine/observation.py:393-656`
- `stage_hint` → `src/tw2k/agents/prompts.py:263-321`
- `format_observation` → `src/tw2k/agents/prompts.py:352-379`
- `LLMAgent.act` → `src/tw2k/agents/llm.py:218-245`
- `_parse_response` → `src/tw2k/agents/llm.py:377-461`
- `apply_action` goals persistence → `src/tw2k/engine/runner.py` (inside `_handle_trade` and peer handlers)

---

## 2. The SYSTEM prompt (what's CONSTANT across turns)

See [`agent_turn/system_prompt.md`](agent_turn/system_prompt.md) for the
literal string (16,664 chars). Structure:

1. **Win conditions** — 100M cr OR last-alive OR highest-net-worth at timeout.
2. **One-screen cheat sheet** — output schema including the `goals` block.
3. **Winning progression A→E** — trade → upgrade → colonize → fortify → win.
4. **Key rules** — warp must be in `warps_out`; `deploy_genesis` requires space; etc.
5. **What's in your observation** — explicitly lists `ship.cargo_cost_avg`,
   `known_ports[*].age_days`, `trade_log`, `action_hint`. (See §4 — some
   of these claims are currently aspirational; the raw `Observation` has
   them, the user message does not.)
6. **Goal discipline** — three horizons, update when a goal is done, prefer numbers.
7. **Day-1 worked example** — 5 turns with the exact JSON shape.
8. **Trading / StarDock price sheet / Colonize loop / Combat / Diplomacy** — mechanics.
9. **Observation fields you MUST read** — enumerated list.
10. **Complete action verb list** — 36 verbs across 6 categories.
11. **Output rules** — JSON only, no markdown, kind must be a known verb.

**Token cost, per turn:** the full prompt at ~14 KB costs ~3,500 input
tokens on grok-4-fast. Sent every turn. With prompt caching on the xAI
side this compresses significantly, but the pricing accounting is still
per-call.

---

## 3. The USER message — exactly what the LLM sees each turn

From [`user_message.json`](agent_turn/user_message.json). Captured at
**day 1, tick 11** for `Captain Reyes` (P1), seed 42. Top-level keys, in
output order:

```
day, tick, max_days
self  ← {id, name, credits, alignment, turns_remaining, turns_per_day,
          ship, corp_ticker, planet_landed}
stage_hint ← {stage: "S1", label: "Opening Trades", reason, next_milestone}
scratchpad ← verbatim string the agent itself wrote last turn
sector     ← full detail of the sector you stand in
adjacent   ← brief view of every sector in warps_out
other_players ← corpmates: full state. Non-corpmates: visible only if
                same sector or recently seen; otherwise just id + name
inbox ← last 10 hails
known_ports_top ← up to 15 port-intel entries the agent has gathered
recent_events ← last 12 events from the global feed (warps, trades,
                agent_thoughts, errors — yours AND others')
action_hint ← prose strip, assembled fresh every turn (§5)
```

### What `self.ship` contains

```json
"ship": {
  "class": "merchant_cruiser",
  "holds": 20,
  "cargo": {"fuel_ore": 0, "organics": 0, "equipment": 20, "colonists": 0},
  "cargo_cost_avg":  {"equipment": 32},     ← what you PAID per unit
  "cargo_value_at_cost": {"equipment": 640}, ← qty × avg (your break-even)
  "fighters": 620, "shields": 0,
  "mines":  {"armid": 0, "limpet": 0, "atomic": 0},
  "genesis": 0, "photon_missiles": 0, "ether_probes": 0,
  "photon_disabled_ticks": 0, "cargo_free": 0
}
```

> **Q: "Do they see ship status?"** Yes — fully. Class, every hold, per-commodity
> average cost basis (since commit `18972af`), break-even value, all weapons, all
> equipment, cargo_free. Nothing is hidden from their own ship.

### What `sector` contains

```json
"sector": {
  "id": 338,
  "warps_out": [736, 845, 874],
  "is_fedspace": false,
  "occupants": ["P1"],
  "fighter_group": null,
  "mines": [],
  "planets": [],
  "port": {
    "class_id": 1, "code": "BSS", "name": "Andros-338",
    "buys":  ["fuel_ore"],
    "sells": ["organics", "equipment"],
    "stock": {
      "fuel_ore":  {"current": 3058, "max": 4068, "price": 17, "side": "buys_from_player"},
      "organics":  {"current": 1116, "max": 2617, "price": 25, "side": "sells_to_player"},
      "equipment": {"current": 3793, "max": 4148, "price": 27, "side": "sells_to_player"}
    }
  },
  "ferrengi": []
}
```

Plus `adjacent[]` with lightweight entries per warp target:

```json
{"id": 874, "port": "SBS", "fighter_count": 0, "fighter_owner": null,
 "mines": 0, "has_planets": false, "occupants": ["P2"], "known": true}
```

> **Q: "Do they see the map and scan info?"** They see:
> - **Where they are**: `sector` (full detail — port, stock, planets, occupants, mines, ferrengi)
> - **One hop out**: `adjacent[]` (every warp target, with port code + fighter counts + who's there)
> - **Port memory**: `known_ports_top` — up to 15 ports they've personally visited, with stock levels, prices, and `age_days` since last visit.
>
> They do NOT see a global map of 1000 sectors. Exploration is the
> gameplay. To reach into the fog, they must `scan` (costs 1 turn) or
> `probe target=<sector_id>` (costs 5000 cr, one-shot remote scan).

### What `known_ports_top` looks like (two entries shown)

```json
[
  {
    "sector_id": 338, "class": "BSS",
    "stock": {
      "fuel_ore":  {"current": 3058, "max": 4068, "price": 17, "side": "buys_from_player"},
      "organics":  {"current": 1116, "max": 2617, "price": 25, "side": "sells_to_player"},
      "equipment": {"current": 3793, "max": 4148, "price": 27, "side": "sells_to_player"}
    },
    "last_seen_day": 1,
    "age_days": 0         ← < 2 means fresh intel; > 2 is stale (system prompt teaches this)
  },
  {"sector_id": 874, "class": "SBS", "stock": {...}, "age_days": 0}
]
```

### What `stage_hint` looks like

```json
{
  "stage": "S1",
  "label": "Opening Trades",
  "reason": "Day 1, net worth $96,730 — still establishing port pair",
  "next_milestone": "Complete 3 profitable round-trips on one port pair"
}
```

The arc has 5 stages (`S1`..`S5`) and is auto-computed by
`prompts.py::stage_hint()` from `credits`, `net_worth`, ship class, max
citadel level, corp membership. Injected fresh every turn so the agent
never loses track of phase.

### What `recent_events` looks like

Last 12 entries from the global event feed — warps, trades, thoughts,
buys, failures. Includes the agent's OWN last thoughts and actions
(since they were logged before `build_observation` ran), plus rivals'
visible actions. This is how the agent "remembers" what it just did.

---

## 4. What the LLM does NOT see — the gap between Observation and user message

**This section documents a gap found during the audit, and the fix
shipped the same day. Kept here so the history is readable.**

### What was missing (audit finding, 2026-04-17)

The `Observation` pydantic model has 22+ fields. The original
`format_observation` shipped only ~10 of them to the LLM. Fields
stripped before the payload was sent:

| Field on `Observation` | System prompt references it? | Was reachable via? |
|---|---|---|
| `goals` | YES — §"GOAL DISCIPLINE" | Only as text at top of `action_hint` |
| `trade_log` | YES — "trade_log (last 5) — your own recent trades with realized_profit" | Only partial, via `action_hint`'s "P&L at this port" line |
| `owned_planets` | YES — "self.owned_planets — your planets (id, sector_id, citadel_level, ...)" | Only when standing in-sector via `action_hint` |
| `net_worth` | YES — §"OBSERVATION FIELDS YOU MUST READ" | Only as prose in `stage_hint.reason` |
| `alive`, `deaths`, `max_deaths` | Combat section | Not sent |
| `experience`, `rank`, `alignment_label` | Prompt mentions rank/alignment | Not sent |
| `alliances`, `corp` (full) | Diplomacy section | Not sent |
| `limpets_owned`, `probe_log` | Recon section | Not sent |

### Fix shipped (commit after `1cc7b5b`)

`format_observation` now ships everything the system prompt references.
Current dump script output:

```
[info] user_message top-level keys:
  ['action_hint', 'adjacent', 'alliances', 'corp', 'day', 'goals',
   'inbox', 'known_ports_top', 'max_days', 'other_players',
   'owned_planets', 'recent_events', 'scratchpad', 'sector', 'self',
   'stage_hint', 'tick', 'trade_log']

[info] self.* keys:
  ['alignment', 'alignment_label', 'alive', 'corp_ticker', 'credits',
   'deaths', 'experience', 'id', 'max_deaths', 'name', 'net_worth',
   'planet_landed', 'rank', 'ship', 'turns_per_day', 'turns_remaining']

[info] fields on Observation BUT NOT in user_message:
  ['finished', 'limpets_owned', 'probe_log']
```

Remaining three un-sent fields are intentional:
- `finished` — redundant with the turn loop itself.
- `limpets_owned` — specialized, add when limpet tracking gameplay
  is active.
- `probe_log` — same story for ether probes.

### Cost of the fix

User-message payload grew **5,095 → 6,055 chars** (+19%, ~+240 tokens
per turn on grok-4-fast). Well under 1% of the ~400k input token/min
limit. The `goals` / `trade_log` / `owned_planets` fields are the
three with the highest signal-to-token ratio — their inclusion
directly closes the "system prompt told me to read this but I can't
see it" loop.

### Regression protection

Four tests in `tests/test_phase_abc.py::TestPhaseGObservationSurface`
now lock this in:
- `test_g1_user_message_has_top_level_goals`
- `test_g2_user_message_has_trade_log`
- `test_g3_user_message_has_owned_planets`
- `test_g4_user_message_self_has_net_worth_and_survival`

Any future `format_observation` refactor that drops these fields will
fail CI.

---

## 5. The `action_hint` — how turn-by-turn "memory" is actually delivered

Built fresh inside `build_observation` by `_action_hint` every turn.
Currently what the LLM sees for our captured turn:

```
YOUR GOALS — NOW: warp 7 -> sell 20 fuel_ore @>=26cr; warp 5 buy 20 fo @<=22cr; repeat until cr>=45k
         / DAY: hit 45k cr, warp back to sector 1, buy_ship cargotran (43.5k), fill holds with colonists for Genesis run
         / MATCH: CargoTran day 1, Genesis a dead-end sector day 2, Citadel L2 by day 3; ferry colonists to compound planet production.
| Verbs available: warp trade scan wait + 29 more (see system prompt).
| warp target MUST be in [736, 845, 874].
| port BUYS fuel_ore / port SELLS organics,equipment — use trade.
```

This strip is where most of the "memory surfacing" actually lives.
Sections it can contain, in this order:

1. **YOUR GOALS** — `short` / `medium` / `long` the agent itself wrote
   last turn. Empty-goals variant nudges: "GOALS EMPTY — set
   `goal_short`/`goal_medium`/`goal_long`".
2. **Verbs available** — a cap-it-all reminder of the verb set.
3. **warp target MUST be in [...]** — the legal-warp list.
4. **port BUYS .../port SELLS ...** — if standing at a tradeable port.
5. **P&L at this port** — if cargo and port.buys overlap, shows
   cost basis, port bid, and expected realized profit per commodity.
   _This is the ONLY place cost-basis P&L reaches the LLM in its
   current state._
6. **At StarDock**: equipment menu + "Ships you can afford NOW: ...".
7. **Per-weapon nudges** — genesis loaded, colonists in cargo,
   photon missiles, probes (each with the verb shape).
8. **Owned planets here** — land_planet nudge.
9. **Landed on planet** — build_citadel / assign_colonists nudge.
10. **Unowned planets here** — land to inspect.
11. **Ferrengi present** — attack-or-flee nudge.
12. **Unread inbox count** — respond hint.
13. **END OF DAY** — if turns_left < warp cost, force the agent to `wait`.
14. **YOUR LAST ACTION FAILED** — recovery nudge, with the exact error
    string, since the last successful action.

This hint is the **single most important piece of per-turn steering**.
The goals appearing FIRST (since commit `18972af`) is the commitment
mechanism that made Reyes stop drifting from her CargoTran plan in V8
onward.

---

## 6. Answering the user's questions directly

### "Do they write their plan for the next turn?"
**Yes, in the SAME response as their current action.** The output schema
requires `goals.{short,medium,long}` fields. The engine persists them to
`Player.goal_short / goal_medium / goal_long`, and next turn's
`action_hint` surfaces them at the top under `YOUR GOALS —`. Omit a
field to keep the prior value; write `""` to clear it; write a new
string to replace.

### "Do they see the same game goals?"
Yes — they see whatever they themselves wrote last turn, until they
overwrite it. Three horizons:
- `short` = next 1–3 turns (tactical)
- `medium` = this in-game day (operational)
- `long` = how they plan to win (strategic)

The SYSTEM prompt also ships 5 hard-coded meta-goals (A→B→C→D→E:
Trade→Upgrade→Colonize→Fortify→Win), and the `stage_hint` block in
every user message tells them which of the 5 stages they're currently
in with a named `next_milestone`.

### "Do they see good memory?"
Yes, after the 2026-04-17 fix. Concrete breakdown:
- **`scratchpad`** ✅ — up to 1,500 chars of free-form notes they wrote
  last turn. Shown back verbatim.
- **`goals` (3 horizons)** ✅ — as a top-level structured block in the
  user message AND as prose at the top of `action_hint`.
- **Cargo cost basis** ✅ — `self.ship.cargo_cost_avg` and
  `cargo_value_at_cost` (added commit `18972af`).
- **Known ports with age** ✅ — `known_ports_top` with `age_days`.
- **Recent events (last 12)** ✅ — global feed, includes own thoughts
  and actions.
- **Inbox** ✅ — last 10 hails.
- **`trade_log`** ✅ — last 5 trades with `realized_profit` on sells.
- **`owned_planets`** ✅ — full structured list: id, sector, citadel
  level + target, colonist pools, fighters, shields.
- **`self.net_worth`**, **`self.alive/deaths/max_deaths`**,
  **`self.rank/experience/alignment_label`**, **`alliances`**,
  **`corp`** ✅ — all now present.

### "Do they know how much they paid for something?"
**Yes.** See `self.ship.cargo_cost_avg` in the user message. For our
captured turn: Reyes has 20 equipment in hold, `cargo_cost_avg.equipment =
32`, `cargo_value_at_cost.equipment = 640`. When she's next at a port
that bids on equipment, `action_hint` will also spell out:

```
P&L at this port: 20 equipment cost=32cr, port bids 34cr -> +40cr
```

### "Do they see ship status?"
**Yes, completely.** Every field on the ship model ships. Class, holds,
per-commodity cargo, per-commodity cost basis, fighters, shields, three
mine types, genesis torpedoes, photon missiles, ether probes, free
holds, and any "photon_disabled" timer.

### "Do they see maps and scan info?"
- **Current sector**: full detail (port stock/prices, planets, mines,
  fighter groups, ferrengi, all occupants).
- **One warp out**: every sector in `warps_out`, with lightweight summary
  (port code, fighter counts, planets yes/no, occupants, and whether
  they've been there before via `"known": true`).
- **Beyond that**: `known_ports_top` — up to 15 ports they've
  personally visited, with stock and prices at last visit, and the
  `age_days` staleness indicator.
- **No global map.** The universe is 1,000 sectors; discovery is the
  gameplay loop. The `scan` verb maps more neighbors; `probe` remote-scans
  any single sector for 5k cr.

### "In what order and how does the pipeline really work?"
See §1 diagram and the per-turn sequence:

1. **Engine** computes observation (reads game state + persisted agent
   memory).
2. **Engine** builds `action_hint` string (this is where goals,
   cost-basis P&L, end-of-day warnings, and recovery nudges get
   injected).
3. **Formatter** projects `Observation → JSON user message` (currently
   drops several fields — §4).
4. **Transport**: `messages=[system, user]` sent to grok-4-fast at
   `https://api.x.ai/v1`, `max_tokens=1200`, `temperature=0.6`,
   `timeout=120s`.
5. **Parser** extracts `action`, `thought`, `scratchpad_update`, and
   `goals.{short,medium,long}` (tolerates flat `goal_short` synonym).
6. **Engine** persists `thought`, `scratchpad`, `goal_*` onto the
   `Player` BEFORE running the verb.
7. **Engine** runs the verb. Trades update `cargo_cost` and append to
   `trade_log` with `realized_profit` on sells.
8. Events emit to the global feed. UI broadcasts via WebSocket.
9. Loop sleeps `action_delay_s / speed_multiplier` (0.06s at 10×),
   then the next agent gets a turn.

A single agent's turn currently takes **~3–5 seconds wall clock** on
grok-4-fast, dominated by the LLM's hidden reasoning pass. At
`speed_multiplier=10`, the artificial spectator delay contributes
0.06s — negligible.

---

## 7. What a real LLM response looks like

See [`agent_turn/example_llm_response.json`](agent_turn/example_llm_response.json).
Directly mirrors the output schema in the system prompt:

```json
{
  "thought": "At sector 5 (SBB fuel_ore seller). My goal is to run 5<->7 until I hit 45k cr. Buying 20 holds of fuel_ore below list.",
  "scratchpad_update": "sec 5(SBB fo@21, eq@40) <-> sec 7(BSB fo@27, eq@35) paired.\nCargoTran 43.5k @ sec 1 once cr>=45k. Loop complete: 3 done, 2 to go. Est cr after this round-trip: ~45.5k.",
  "goals": {
    "short":  "buy 20 fo @<=19cr (haggle); warp 5 -> 7; sell @>=27cr; this is trip 4/5",
    "medium": "hit 45k cr THIS DAY, warp 1, buy_ship cargotran, load colonists for Genesis",
    "long":   "CargoTran day 1, Genesis day 2, Citadel L2 day 3; out-produce Vex"
  },
  "action": {
    "kind": "trade",
    "args": {"commodity": "fuel_ore", "qty": 20, "side": "buy", "unit_price": 19}
  }
}
```

What the engine does with each field, in order:

1. `player.thought = action.thought`  → displayed in UI, emitted as an `agent_thought` event in `recent_events`.
2. `player.scratchpad = action.scratchpad_update` (capped at 8,000c internally, surfaced at 1,500c via the prompt schema).
3. `player.goal_short = "buy 20 fo @..."` (capped 240c).
4. `player.goal_medium = "hit 45k cr THIS DAY, ..."`.
5. `player.goal_long = "CargoTran day 1, ..."`.
6. `action.kind = "trade"` dispatches to `_handle_trade` → `execute_trade` runs haggling + settlement + cost-basis update + `trade_log` append.

---

## 8. Open follow-ups identified by this audit

1. ~~**Ship the already-persisted memory to the LLM.**~~ **DONE.**
   `format_observation` now includes `trade_log`, `owned_planets`,
   structured `goals`, `net_worth`, and survival fields. +240 tokens
   per turn. Regression tests in `TestPhaseGObservationSurface`.
2. **Parallelize the two agents' LLM calls within one match.** Currently
   serial; LLM latency ≈ 4s per agent per turn. Concurrent calls would
   roughly halve wall-clock per match.
3. **Consider trimming `SYSTEM_PROMPT`.** It's 3,500 tokens of constant
   payload. Some sections (price sheet, full verb list) could move to
   the user message and be surfaced only when relevant (e.g. ship
   menu only when at StarDock).
4. **Re-check grok's goal-discipline behavior after the fix.** With
   `goals` now shipping as a structured block, the model may lean on
   it more reliably than it did when goals were only in prose. Worth a
   before/after match comparison at the same seed.
