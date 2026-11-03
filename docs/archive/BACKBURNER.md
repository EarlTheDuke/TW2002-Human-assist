## Back-burner ideas — TW2K-AI

Captured during Seed-7777 post-mortem (4-player, 30-day match). Each item has
a thumbnail of motivation, a sketch of the simplest implementation, and the
observation or user-stated reason that triggered it so we can pick them up
in a future session without re-deriving context.

**Philosophy reminder:** changes should surface awareness and opportunity to
the LLM agents, not mandate their actions. The agents' autonomy is the point
of the game — a smarter model should be able to beat a dumber model because
it chose better, not because it was railroaded into the same move.

---

### 1. Pirate-personality AI agents (user request)

**Motivation.** All 4 agents in Seed-7777 played the same risk-averse
merchant game: trade fuel_ore, ignore other players, ignore Ferrengi,
hoard credits. Zero PvP in 30 days. A TW2002 match without piracy is
missing half the drama.

**Sketch.**
- Add a `personality` field to the agent config (enum: `merchant`,
  `pirate`, `builder`, `diplomat`, `chaotic`).
- Pass the personality into the system prompt as a flavor block:
  a pirate agent gets "you view other commanders as prey," a builder gets
  "long-game citadel empire," etc. Still ends with the same JSON output
  schema and the same legal verbs — we're tuning priors, not mechanics.
- Personalities bias goal-generation, not action availability. A pirate
  still has to plan fighter loadouts, find a target, etc. — they just
  *want* to.
- Match launch: `--personalities pirate,merchant,builder,diplomat` or
  randomize per seed.

**Open questions.**
- Do we want personalities that FIGHT each other in the system prompt
  (pirate vs peacekeeper)? Probably yes — that's the emergent story.
- Keep the rubric universal or add personality-specific scorecards
  (pirate scored on kills + bounty; builder on citadel levels)?

**Related work.** Rebellion roleplay prompts in agent frameworks, "town
hall" multi-agent simulations.

---

### 2. Force-test planet defenses in a scripted scenario

**Motivation.** Seed-7777 had 3 planets with 2,000 fighters each and
nobody ever attacked one. Engine code exists for "hostile warps into
defended sector" but we have zero observational evidence that it fires
correctly — we're shipping untested defense logic.

**Sketch.** `scripts/invasion_test.py` — spawn a heavy Ferrengi
battleship inside a known player-planet sector and step the tick. Assert
that `COMBAT` emits, fighters deplete as expected, and the planet either
falls or the Ferrengi dies. Can also be a pytest (deterministic).

**Deferred because.** User said "wait for a game that tests it for us."
Fine — but if three more matches go by with zero planet invasions we
should build the scripted test ourselves.

---

### 3. Multi-planet economies / 2nd Genesis incentive

**Motivation.** Vex won with 1 planet. Real TW2002 winners run 5–15.
The engine already supports multiple planets per commander; agents just
never build them.

**Sketch.** Already partially addressed by the "2nd Genesis affordable"
hint (Phase L). Watch the next match — if agents *still* only build one
planet, consider:
- Showing a rolling "planet economy ROI" stat (colonists/credits/day).
- Pushing rubric weight toward N-planet-citadels rather than total net
  worth alone.

---

### 4. Ship-upgrade laziness (still CargoTran at day 30)

**Motivation.** All 4 agents stopped at CargoTran and never upgraded
despite pooling 75k+ credits. A Scout Marauder or Battleship is ~90k and
triples combat power.

**Sketch.**
- Add a soft hint at StarDock when `credits >= cheapest_upgrade_cost *
  1.5` *and* `experience >= 500`.
- Or, better, extend the `affordable_ships` hint to auto-recommend a
  class that matches the agent's current strategy (pirate → Battleship;
  trader → Merchant Freighter).

---

### 5. Fighter/shield refill hint at StarDock

**Motivation.** Companion to the unarmed-in-deep-space FYI we just
added: when a player is AT StarDock with `ship.fighters == 0`, emit a
FYI ("restock before warping deep") — right at the point of purchase.

**Sketch.** 2-line addition to `_action_hint`. Gate on `sector_id == 1
and ship.fighters < 100`.

---

### 6. Corp/alliance diplomacy actually used by agents

**Motivation.** Zero corps formed, zero alliances formed in Seed-7777.
System prompt describes the verbs; agents never try them.

**Sketch.** Needs a prompt-level example in `DAY-1 WORKED EXAMPLE`
showing how and when to propose a NAP. Possibly a stage-hint:
"STAGE: day >= 5 with a neighboring commander who owns a planet — a
NAP costs nothing and blocks a mutually ruinous PvP."

---

### 7. Colonist-ferry dedicated "action"

**Motivation.** The single binding constraint on citadel progression is
colonist count. Ferrying 75 colonists/trip from StarDock to a 6-hop
planet takes ~12 turns round-trip — that's almost an entire day per
trip for 75 pop gain. Citadel L3 needs 4,000 colonists. That's 53 trips
= two game-weeks of pure ferry work. Agents rightly decline.

**Sketch options.**
- Larger colonist-cargo discount (colonists use fewer "holds" per unit).
- An autopilot `ferry_colonists planet_id=X` macro that does the entire
  loop in one action at a turn-count cost proportional to hops.
- Higher natural planet population growth when idle colonists > 1k
  (geometric growth is what real TW2002 has).

---

### 8. FedSpace dead-end — we fixed ONE shape, watch for others

**Motivation.** The generator fix forbids converting FedSpace edges to
one-way and forbids leaving any sector with 0 outbound warps. But there
could still be weird sub-graph shapes that trap agents for strategic
reasons (a one-way tunnel to a dead-end deep sector).

**Sketch.** Add a post-generation report: "longest shortest-path back to
sector 1 from any sector" and warn if > 20 hops. Currently unchecked.

---

### 9. Inbox response tracking

**Motivation.** Blake sent 8 broadcast bounties; no agent responded.
We now surface them in the hint as FYI (no obligation), which is the
right call. But we don't measure whether agents ever USE hail for
anything — could reveal a capability gap.

**Sketch.** Add a match-end summary:
`total_hails, unique_senders, unique_recipients, avg_response_latency`.

---

### 10. Orphaned-planet reclaim mechanic

**Motivation.** 2 of 3 deployed planets in Seed-7777 ended up orphaned
(citadel L2, 2k fighters, no owner) because their captains died. They
just sat there for the rest of the match. Real TW2002 allows a living
commander to "take" an orphan planet.

**Sketch.**
- Action: `claim_planet planet_id=X` — legal only if landed AND planet
  has `owner_id is None` AND player defeats any remaining planet
  fighters (or the planet just transfers if fighters are 0).
- Would make elimination less terminal for the story — someone else
  inherits the fortress.

---

## How to use this doc

When starting a new session, skim this file, pick the item with the
highest current leverage (usually the one that showed up in the most
recent match analysis), and move it to a TODO. Delete or prune entries
that become irrelevant after mechanics changes.
