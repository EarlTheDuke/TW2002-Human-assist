## Match-play notes — TW2K-AI

Running notebook captured while actually playing a 365-day match
(seed 17, P1 human via Cursor-agent-driven HTTP, P2+P3 Grok
`grok-4-1-fast-reasoning`). Start date 2026-04-19. Each entry has
context ("why I hit this"), a sketch of a fix or feature, and a
sharpness tag:

- **friction** — slowed the human player down but worked around.
- **bug** — wrong output or schema drift not yet fixed.
- **gap** — a feature clearly missing once you try to actually play.
- **upgrade** — works today, would be much nicer with more polish.

Philosophy: don't mandate agent behaviour, but *do* fix places where
either the human UX, the copilot's intel surface, or the test/dev
tooling fails to carry obvious information across a boundary.

---

### 1. Density-scan port codes don't persist to `known_ports` — gap

**Context.** First real move I made was a `scan tier=density` at Sol-1.
The event payload contained port codes for 18 sectors out to 2 hops
(e.g. `263: BBS`, `409: SBB`, `487: BSS`). But `known_ports` on
subsequent observations only held the 3 sectors I'd physically
visited. I had to go grovelling through `/events?limit=500`, parse the
scan payload out of the JSON, and re-derive the map manually to spot
that **263 was a BBS one warp from where I was standing** — the
single most important intel of my first day of play.

**Impact.** An LLM agent running the same game would miss this
entirely unless it happened to re-read its own scan event right away,
which its short event window discourages. It directly translates to
the "4.5× profit gap" I saw against the Grok opponents on day 1.

**Sketch.**
- On `density` and `holo` scans, merge each neighbour's observed
  `port_code` into `player.known_ports` as a tombstoned entry
  (no stock yet, just `{sector_id, class, stock: {}, last_seen_day}`).
- On `holo` specifically, also persist stock snapshot (it already
  has the data).
- Add an `action_hint` / copilot hint that reads "from your last
  density scan, nearest unexplored BBS port is sector 263 (2 warps)"
  so the player doesn't need to re-parse raw events to act.

---

### 2. LLM agents completely ignore `inbox` alliance proposals — gap

**Context.** I issued `propose_alliance` to both P2 and P3 with
explicit non-aggression terms. The proposals landed as `active=false`
alliances and appeared in the opponents' `inbox`. Across the next
~15 ticks of Grok turns, **neither agent referenced the proposal in
their scratchpad or goal output** — they kept trade-tunneling on
their existing loops.

**Impact.** Diplomacy is nearly invisible to the LLM agents. The
mechanic exists in the engine but not in the prompt surface, so
alliances are effectively human-only in practice.

**Sketch.**
- In the LLM agent's observation, promote `inbox` from a raw list
  to a structured "pending decisions" block at the top of the
  observation, with a one-line synopsis per item:
  `PENDING PROPOSAL A1 from Captain Reyes: 30-day NAP. Accept
  via accept_alliance(A1), decline by ignoring.`
- Add an explicit `DECISIONS WAITING FOR YOU` header to
  `action_hint` when `inbox` is non-empty so the agent is nudged
  to consider non-trade actions.
- Consider a tiny in-prompt rubric: *"Alliances limit future PvP
  but protect your economy and give you warp-rights support;
  consider the ask."* Keeps autonomy, raises awareness.

---

### 3. Starting positions are dramatically unequal — design question

**Context.** P1 (me) spawned in Sol-1 (sector 1, in FedSpace, class-8
StarDock, adjacent to a BSB/SSB pair). P2 spawned at 865 which is
adjacent to a productive equipment-sell BSB pair at 251/381.
P3 spawned at 929 with an SSB+BSB pair one warp each direction.

All three start positions are "3 good trade pairs in ≤2 warps," but
**the margins are wildly different**. My Sol-1 fuel loop pulled 40cr
per trip (12.5% margin). P2's equipment loop pulls 180cr per trip
(32% margin). P3's fuel loop pulls 80cr per trip (26% margin). That
isn't "random luck" — it's a structural pricing variance not reflected
in a Sol-centric start.

**Impact.** Playing from Sol as the human feels like a handicap. If
this is intentional ("StarDock's safety tax"), it should be surfaced
in the action_hint. If it's not intentional, the economy placement
pass should balance expected-day-1-profit across the 3 starting
clusters.

**Sketch.**
- Add a metric to `/api/economy/prices`: `expected_profit_per_trip`
  for each port pair within 3 warps of `seed_spawn_points[i]`.
- If the spread across spawn points is >2× we have a balance bug;
  the universe gen should nudge spawn points toward equivalent
  expected-value pairs, or give StarDock a starting bonus
  (free cargo pod, discounted CargoTran, something tangible).

---

### 4. Wall-clock pacing is brutal for a human — upgrade

**Context.** At `--action-delay-s 0.3 --speed 1.0` with 3 agents
where 2 are Grok LLMs, each P1 turn cycles every ~15 seconds of
wall time (Grok latency is the bottleneck). A bounded 7-action
batch took ~100s to drain. A full 120-turn day = ~30 minutes real
time. A 365-day match at this pace = 180+ hours theoretical.

**Impact.** Unplayable as a single sitting; fine as episodic.
The expectation-setting is important.

**Sketch.**
- Add a "fast-forward while I'm not looking" mode: when
  `/play` has no active WebSocket connection from a browser and no
  pending P1 action for >30s, the scheduler temporarily boosts
  `speed_multiplier` to match the LLM turn pace rather than
  blocking on `action_delay_s` as if a human was watching. As soon
  as the WebSocket reconnects or P1 submits an action, it drops
  back to configured speed.
- Or simpler: expose a `--human-idle-speed` flag.

---

### 5. `known_ports.stock` still shows day-1 prices 8 ticks later — friction

**Context.** After I warped to 712 and traded, then left, my
`known_ports[1]` entry for sector 712 still shows the original
stock/price snapshot. That's fine for the "I remember what I saw"
semantic. But the observation doesn't tell me staleness clearly —
`age_days` is 0 until tomorrow, so I'm not warned that the stock
I saw is already depleted by my own trade plus any NPC activity.

**Impact.** I nearly planned a 2-lap commit on 263 equipment
pricing without considering that my first lap would move the
port's stock enough that lap 2's price might worsen.

**Sketch.**
- Add `ticks_since_seen` to `known_ports` entries (not just days).
- In `action_hint`, when we're about to plan a multi-lap commit,
  warn: "stock snapshot is N ticks old; prices may have drifted".
- Or: when a human/copilot issues a trade, invalidate that port's
  intel price field and mark it `needs_rescan: true`.

---

### 6. `/state` endpoint exposes all opponents' scratchpads + goals — feature, but load-bearing

**Context.** I get near-omniscient intel on P2 and P3 strategies
just by hitting `GET /state`. That's how I figured out P2's
251/381 equipment loop, P3's 929/397 fuel loop, and their "CargoTran
day 1, genesis day 2, citadel L3+" mid-game plans — directly from
reading their scratchpads in the JSON.

**Impact.** This is **intentional for the spectator UI** but
**unbalanced for a competitive game**. The human gets perfect
information via HTTP while the LLM agents only see their own view.

**Sketch.**
- Two modes for `/state`:
  - `spectator=true` (current): everything, for the dashboard UI.
  - `spectator=false` (new default for non-localhost?): scratchpads
    + goals of non-self players are redacted or replaced with
    fog-of-war placeholder `"[hidden]"`.
- Or keep `/state` as-is and have the human cockpit's
  `/api/human/observation` explicitly *not* surface other players'
  inner state. Currently the human observation already does the
  right thing — the issue is `/state` bleeds through to anyone who
  calls it. Cursor-agent playthroughs are the leaky case.

---

### 7. MCP server isn't auto-registered with Cursor — friction

**Context.** The `tw2k mcp` server we built in H6 isn't wired into
this workspace's `.cursor/mcp.json`, so Cursor's `CallMcpTool`
doesn't see it. The user asked me to "drive your slot via MCP from
Cursor" and I had to fall back to HTTP.

**Impact.** The whole H6 MCP story is undiscoverable unless a user
manually edits a JSON file they've probably never opened.

**Sketch.**
- Ship a template `.cursor/mcp.json` under a new
  `cursor-integration/` example directory, with a README that says
  "copy this to `.cursor/mcp.json` and reload Cursor."
- Or: a `tw2k mcp install-cursor` subcommand that writes the
  workspace config for you, with a dry-run flag.
- Document in `docs/USER_GUIDE.md` that MCP is opt-in and how to
  turn it on.

---

### 8. Opening `--help` line says "Use ~80-120 for watchable sanity runs" — need longer-run guidance — upgrade

**Context.** CLI flag guidance covers "watchable sanity runs" but
not "actual campaign at 365 days." User asked, I guessed 120 tpd,
but we had no doc saying "for a year-long match: 120-300 tpd; API
cost estimate at 2 Grok agents is ~$40-$100."

**Sketch.**
- Add a "Campaign sizing" section to `docs/USER_GUIDE.md` with
  rough wall-clock + API-cost estimates for (30, 90, 365)-day
  matches at 1/4/8× speed. Empirical table, updated after this
  campaign actually finishes.

---

### 9. Agent-driven P1 can't react to `inbox` the way an LLM slot could — gap

**Context.** When I propose alliances from P1, my own `inbox`
doesn't get an agent-style "you have a decision" nudge in the
observation — because P1 is human and the observation is
human-centric. But when I'm driving P1 via Cursor agent I'm in
a hybrid mode: effectively an LLM driving a human slot. The human
action_hint doesn't include "other proposals pending for you" etc.

**Impact.** When opponents eventually accept or counter-propose,
I might miss the inbox entry unless I remember to check.

**Sketch.**
- Human observation's `action_hint` should surface `inbox` items
  the same way the LLM prompt will after fix #2. Basically:
  `action_hint` becomes a multi-source aggregator, not just a
  port/warp nudge.

---

### 10. No per-match "driver log" when two agents are collaborating — gap

**Context.** The primary agent (me in Cursor chat) briefs a
background subagent (the "driver") to execute N laps autonomously.
The driver writes to its own transcript file but there's no shared
"match log" where both primary and driver are appending notes. If
the driver sees something strategically interesting — "Grok P2
just accepted alliance!" — it has no channel to flag it to the
primary other than the final return message when it's done.

**Sketch.**
- The driver can append-write to a shared match log file (e.g.
  `saves/match_{seed}_{date}.md`) with timestamped entries.
- Primary agent can tail that file between driver invocations.
- Long-term: a small `/api/session/note` POST endpoint that both
  agents can write to, surfaced in the spectator UI.

---

### 13. Port price saturation makes hold upgrades near-worthless against small-stock ports — economy balance

**Context.** Seed-17 driver upgraded Merchant Cruiser from 20 to 35
holds (+75% capacity) during the 263↔712 equipment loop. Expected
per-lap profit boost: 20×8 = 160 → 35×8 = 280 cr/trip. Observed:
margin oscillated 280 / 140 / 280 / 175 cr depending on how recently
the port had been dumped on, averaging ~175 cr/lap (vs stable 160
cr/lap at 20 holds). Mechanism: a single 35-unit sell at 712 BSB
moves its internal stock from ~1,000 to ~1,070 which is enough for
the price function to drop buy-from-player from 40 to 37. Recovery
takes a few dozen ticks of non-interaction.

**Impact.** 
- A 75% capacity upgrade delivered only a 9% throughput gain against
  a stock-limited port. The driver's own forensic: "~500-lap payback
  on the 7,500 cr hold upgrade — premature."
- This creates a hidden trap: the *right* move is to pair a capacity
  upgrade with a port-rotation strategy (alternate 712, 776, 487,
  etc.) so no one port saturates, not to pump bigger loads into the
  same pair.
- LLM agents won't figure this out unless they analyze 3-5 laps of
  price deltas, which exceeds their typical per-turn context.

**Sketch.**
- Expose a `saturation_hint` on the observation's `known_ports`
  entry: *"you've pushed 110 units of equipment into this port in
  the last 20 ticks; expect -2 cr/unit next sell."* Derivable from
  the existing port stock model.
- Add to `action_hint`: *"port appears saturated — consider rotating
  to port X at sector Y for next lap."*
- Economy rebalance question: should 712-class BSB ports have
  stiffer stock caps relative to Sol-1's trading volume, or should
  the price function have a smaller "kick" per unit traded so that
  bigger ships get reliable proportional gains? Discuss after
  campaign.
- Add `docs/HEALTHY_GAME_PLAYBOOK.md` section on when to upgrade
  holds vs buy CargoTran vs rotate ports.

**Credit:** flagged from seed-17 day-3 by driver self-critique.

---

### 12. `buy_equip item=holds` doesn't update `net_worth` — bug

**Context.** Seed-17 day-3 tick-324. Driver upgraded Merchant Cruiser
from 20 → 35 holds via `buy_equip item=holds qty=15`. Credits dropped
by ~7,900 cr (holds + concurrent trade activity), but **net_worth
dropped by a near-identical 6,660 cr** despite the ship gaining 15
holds of permanent capacity. Holds are not fungible (can't be sold
back) but they are absolutely part of ship value — a bigger ship
with more holds commands a higher market price, and ship trade-in
credit logic presumably accounts for them.

**Impact.** Makes every capacity upgrade look like a strict scorecard
loss. An LLM agent reading `net_worth` as a progress signal will be
actively dis-incentivised from upgrading holds, shields, or
fighters — the very pre-requisites for deep-game play. The
`best_pair` / economic dashboards are correct; only the total net
number misleads.

**Sketch.**
- Audit `Player.net_worth` computation (likely in
  `src/tw2k/engine/models.py` around the `ship_value` property).
- Decide whether holds contribute to `net_worth_ship`:
  - Option A (mirror buy cost): `holds × base_hold_cost` is added.
    Simple, but makes net_worth super-linear with cash because
    you always pay to add holds.
  - Option B (mirror sell value): `holds × (base_hold_cost × trade_in_pct)`,
    where `trade_in_pct` is something like 0.7. Matches how ships
    resell.
  - Option C (baseline only): the ship's listed price implicitly
    counts some baseline holds; extra ones are sunk into capability.
    Net_worth_ship = ship_price_base. This is the current behaviour
    and causes the misleading delta.
- Shields and fighters likely have the same issue; verify when
  driver next buys either.

**Credit:** flagged from seed-17 day-3 driver session.

---

### 11. `haggle_win_rate_pct` reports 100% while every trade settles at list — bug

**Context.** Driver subagent tried explicit bids (-20% on buys, +20%
on sells) on 6 consecutive equipment laps + 2 fuel laps at ports
263 / 712 / 761. **Every trade settled at the port's list price** —
`lap 1 event note: "bid 25 rejected, settled at list"; "bid 48
rejected, settled at list"`. Yet `trade_summary.haggle_win_rate_pct`
remains 100% across 14 sells, and `avg_margin_pct` is computed from
realized profit which is the list-to-list spread, not any bid-based
advantage.

**Impact.** The haggle mechanic is either (a) silently rejecting any
bid outside a tight tolerance, or (b) the "win rate" metric is
mis-defined (counting any completed trade, not bid-accepted trades).
Either way, a player reading `trade_summary` is being told they're
an expert haggler when they've literally never beaten list price.
This directly misleads LLM agents that use their own trade_summary
as a feedback signal for bid tuning.

**Sketch.**
- Inspect `src/tw2k/engine/economy.execute_trade` — trace how
  `offered` (bid) is compared to the port's accept band, whether
  a "haggle win" event is emitted distinct from "trade settled,"
  and what the realized unit price is when a bid is rejected.
- Define `haggle_win` explicitly as *"unit price diverged from list
  in the player's favor by ≥ some threshold"* and count only those.
- Extend the trade event payload to expose the `bid`, `counter`, and
  `settled` prices separately so downstream UI/analytics can show
  the negotiation clearly.
- If haggle is intentionally disabled for Phase H / MVP, document
  that in the observation's `action_hint` so agents stop wasting
  prompt tokens on bids that do nothing.

**Credit:** flagged by the driver subagent during seed-17 day-1
(equipment loop 263↔712), 2026-04-19.

---

## Post-game wrap-up checklist

When we declare the match complete (winner decided, all three
strategies played out, or we concede early), come back here and:

- [ ] Score each note against what actually happened (did it still
  feel like a gap at day 100? day 200?).
- [ ] Promote the top 3-5 to the main roadmap.
- [ ] Spawn an `IMPROVEMENTS_SEED17_POST.md` with a prioritised plan
  for the next match.

---

# Match 2 findings (seed 17, 1M starting credits)

Match 2 launched 2026-04-20 ~18:51 UTC. Every player starts with
1,000,000 credits so the game arc is about combat / planets / corp
rather than the CargoTran grind. We're deliberately exercising every
major mechanic to find where the engine breaks or where the agent
intel surface is thin. Entries below use the same tag vocabulary as
match 1 (friction / bug / gap / upgrade).

### M2-watchlist (things to log the moment they happen, blank until observed)

- Attack: combat resolution fairness, alignment deltas, ship respawn,
  fighter/shield bookkeeping.
- Photon missile: actual effect duration, target's fighter disable
  state reflected in observation, cost accounting.
- Atomic mine deployment: detonation trigger, port-damage calculation,
  blast radius, whether opponents see the mine before they trigger it.
- Genesis deployment: 4-turn blocking, planet class assignment,
  seed-colonist count, FedSpace distance enforcement.
- Build citadel: level progression, colonist consumption, day-timer
  enforcement, defensive stats gained per level.
- Land planet / liftoff: turn cost, hostile-planet siege mechanic.
- Assign colonists: production numbers, treasury growth.
- Corp create / invite / join / deposit: whether Grok actually accepts
  corp invites (match 1 note #2 suggests alliance was ignored; corp
  may be different).
- Hail / broadcast: does either reach opponent LLM context and prompt
  them to reconsider?
- Ferrengi encounters: does hostile AI spawn in late-game sectors?
- Player elimination: `MAX_DEATHS_BEFORE_ELIM = 3`, verify count
  increments correctly.

Findings get appended *below* this watchlist as they're discovered.

---

### M2-1. `_resolve_ship_combat` crashes on player-vs-player kill — bug (FIXED)

**Context.** First-ever PvP kill in match 2: P1 Havoc Gunstar (8,020
fighters) vs P2 BattleShip (20 fighters) at sector 514, tick 49. Combat
event emitted correctly (P2 down to 0 fighters, 0 shields). Immediately
after the `emit(COMBAT, …)` call, the attack handler crashed with:

```
AttributeError: 'Player' object has no attribute 'aggression'
  File "src/tw2k/engine/combat.py", line 202, in _resolve_ship_combat
    bounty = K.FERRENGI_BOUNTY_PER_AGG * target.aggression
```

Root cause in `src/tw2k/engine/combat.py` destruction check:

```python
if d_fighters <= 0:
    if hasattr(target, "alive"):
        # Ferrengi        ← wrong! Player ALSO has `alive`
        target.alive = False
        bounty = K.FERRENGI_BOUNTY_PER_AGG * target.aggression
```

Both `Player` (models.py:366) and `FerrengiShip` (models.py:514) carry
`alive: bool = True`. The `hasattr(target, "alive")` check therefore
matches every target type and the code proceeded into the Ferrengi
branch for a Player target, blowing up on the next line when it tried
to read `aggression` (which is only on `FerrengiShip`).

**Impact.**
- Every ship-vs-ship PvP kill crashes the engine mid-turn.
- Partial state left behind: COMBAT event is already emitted (showing
  defender at 0/0), so the spectator sees the fight happen, but the
  defender's ship is NOT actually destroyed, `_destroy_ship` never
  runs, the kill XP is never awarded, the death counter isn't
  incremented, and `MAX_DEATHS_BEFORE_ELIM` logic never fires.
- Players end up as unkillable hulks with 0/0 loadout, still occupying
  their sector, still landed on their planet, still able to continue
  acting (including running build_citadel as P2 did on Phoenix 514-28).
- Blocks the entire PvP victory path. Alignment adjustments, bounties,
  and elimination mechanics are all unreachable.

**Fix.** Replaced the duck-typing with an `isinstance(target, FerrengiShip)`
check so the branch is type-safe and intent is explicit:

```python
if isinstance(target, FerrengiShip):
    target.alive = False
    bounty = K.FERRENGI_BOUNTY_PER_AGG * target.aggression
    ...
else:
    _award_xp(universe, attacker_id, "kill_player")
    _destroy_ship(universe, target.id, reason="combat", killer_id=attacker_id)
```

`FerrengiShip` was added to the imports from `.models`. The other
`hasattr(target, "alive")` check at `combat.py:124` is semantically
correct (it guards against combat with a corpse, which applies to
either type) and was left in place with a comment confirming intent.

**Regression coverage added** in `tests/test_engine.py`:
- `test_pvp_kill_respawns_victim_without_crash` — overwhelming PvP kill
  must route through `_destroy_ship`: victim ejected to StarDock,
  `deaths += 1`, ship downgraded to Merchant Cruiser, 75% credits
  retained, attacker gets `kill_player` XP, no exception.
- `test_pvp_kill_elimination_after_max_deaths` — the other branch of
  `_destroy_ship`: a victim with `deaths == MAX_DEATHS_BEFORE_ELIM - 1`
  gets flagged `alive = False` on the next lethal hit.
- `test_ferrengi_kill_pays_bounty_and_alignment` — guards the legitimate
  Ferrengi branch (bounty paid, alignment +10, Ferrengi.alive=False).
- `test_pvp_kill_in_fedspace_blocked_and_penalized` — attacking inside
  FedSpace is refused and the defender is never touched (no partial-state
  mutation).

**Verdict.** Full suite green: 366 passed in 179s, ruff clean. Match 2
relaunched with the fix applied 2026-04-20.

**Follow-up (deferred).** Decide whether PvP kills should cost the
attacker alignment outside FedSpace (classic TW2002 evil hit for
killing good/neutral players). User opted to defer for match 2 so the
combat-arc plays out without surprise alignment drift on P1.

**Credit.** Discovered during match 2 Phase 2A strike, 2026-04-20 tick
49. Match state unrecoverable post-crash (partial mutation had left P2
as a zombie); restarted with fix applied.


---

### M2-1. PvP combat mis-routes to Ferrengi branch, raises AttributeError, kills the match scheduler — bug (severity: **CRITICAL — game-breaking**)

**Context.** Match 2, day 1 tick 49. P1 (Havoc Gunstar, 8020 fighters,
3000 shields) attacked P2 (BattleShip, 20 fighters, 0 shields) in
sector 514, outside FedSpace.

What I initially observed was combat math resolving correctly (P2's
20 fighters deleted in exchange 1, P1 lost 16 shields) and P2 ending
up as a zombie (alive=False but not ejected, no SHIP_DESTROYED event,
no death counter increment, no credit penalty, no planet orphan).

Then I submitted the next action (`warp 514 -> 173`) and it hung.
After 30+ seconds of polling, `GET /state` revealed the truth: the
match scheduler task had CRASHED mid-combat and was dead.

```
runner.state.status   = "error"
runner.state.last_error:
    'Player' object has no attribute 'aggression'
    Traceback ...
      File "src/tw2k/server/runner.py", line 470, in _run
        result = apply_action(universe, agent.player_id, action)
      File "src/tw2k/engine/runner.py", line 695, in _handle_attack
        _resolve_ship_combat(universe, pid, target)
      File "src/tw2k/engine/combat.py", line 202, in _resolve_ship_combat
        bounty = K.FERRENGI_BOUNTY_PER_AGG * target.aggression
    AttributeError: 'Player' object has no attribute 'aggression'
current_player_idx = None
```

So my "silent zombie" hypothesis was wrong — the reason there was
no SHIP_DESTROYED / planet_orphan / death-counter / credit-penalty /
XP event is that **the handler threw an uncaught exception after
`target.alive = False` (line 201) but before anything else could run
(lines 202–215)**, and then the scheduler task died entirely. No
further ticks, no further actions, no ability for any player to
move. The `/api/human/action` endpoint still returns `queued:true`
but the consumer of that queue is dead, so every subsequent action
silently disappears. From the human player's POV the server just
hangs forever.

Post-crash zombie state of P2 (the fields that were mutated before
the exception fired):

```
P2: alive=False  sec=514 (NOT StarDock)  ship=battleship (NOT downgraded)
    fighters=0   shields=0   credits=73842 (NOT –25%)
    deaths=0 (NOT incremented)  alignment=0 (no delta)
    holds=80 cargo=unchanged   planet 28 "Phoenix 514-28" still owned
```

**This renders the entire match unplayable after the first PvP kill.**
Every time P1 kills *any* player it will crash the scheduler the same
way. The game literally cannot be completed with combat in it.

**Root cause.** Two compounding defects, one of logic and one of
error-containment:

*(a) Logic bug.* `src/tw2k/engine/combat.py` line 199:

```python
if d_fighters <= 0:
    if hasattr(target, "alive"):
        # Ferrengi
        target.alive = False
        bounty = K.FERRENGI_BOUNTY_PER_AGG * target.aggression
        ...
    else:
        _award_xp(universe, attacker_id, "kill_player")
        _destroy_ship(universe, target.id, reason="combat", killer_id=attacker_id)
```

*(b) Scheduler fragility.* `src/tw2k/server/runner.py` line 470 calls
`apply_action(...)` with no try/except around it. Its immediately-
preceding `try/except Exception` block (line 381–455) only catches
exceptions from `agent.act(obs)` — not from action handlers. Any
AttributeError / KeyError / IndexError raised from inside any
handler therefore escapes the loop, is caught by the outer
`except Exception` at line 561, flips the runner to `status=error`,
and the task exits. Nothing respawns it.

The `hasattr(target, "alive")` check is meant to distinguish Ferrengi
NPCs from Players, but **`Player` objects also have `.alive`**, so
every successful PvP kill falls into the Ferrengi branch. The first
line (`target.alive = False`) executes, then `target.aggression`
raises `AttributeError` on the Player and the rest of the branch
(bounty, alignment, XP, SHIP_DESTROYED event) never runs.

The AttributeError propagates up through `apply_action` and is caught
by the scheduler's outer `except Exception` in
`src/tw2k/server/runner.py:561`. That handler sets
`self.state.status = "error"`, saves the traceback to
`state.last_error`, and exits the scheduler loop. **The entire match
halts.** The HTTP server is still up (you can `GET /state`, `GET
/events`, `POST /control/resume`, etc.), but no player, human or LLM,
will ever take another turn until the process is restarted. The
`/control/resume` endpoint only recovers from `paused`, not from
`error`, so there is no in-process way to unstick the match.

Verified on match 2, day 1 tick 49: after P1's `attack P2`, the next
poll of `/state` showed:
```
status: error
last_error: 'Player' object has no attribute 'aggression'
(traceback pointing at combat.py:202)
```
No further `agent_thought`, `warp`, or `human_turn_start` events
emitted for any player after seq 118.

**Impact.**

- PvP "kills" don't eject the victim to StarDock → they stay parked
  in the kill sector as a zombie (still visible in occupant lists,
  still listed as a planet owner).
- No 25 % credit penalty → the loser's net_worth is preserved.
- No death counter increment → `MAX_DEATHS_BEFORE_ELIM = 3` can never
  trigger from PvP, so nobody can ever actually be eliminated by
  another player. The entire "3 strikes and you're out" design is
  dead code for human-vs-human play.
- No `SHIP_DESTROYED` event → spectator UI and event-driven
  copilot hints won't notice the kill. Agents polling for their own
  death (to, e.g., abandon a plan) won't be notified.
- Owned planets aren't orphaned → P2's planet at 514 is still
  `owner_id=P2` even though P2 is `alive=False`. If citadel
  mechanics rely on the owner being alive, behavior is undefined.
- Attacker gets no XP (`_award_xp kill_player` is only in the else
  branch) and no alignment bonus/penalty.

**Sketch of a fix.**

- Discriminate by attribute that Players don't have (e.g.
  `hasattr(target, "aggression")`) or by type check
  (`isinstance(target, Ferrengi)` / `isinstance(target, Player)`).
- Or reorder: check `isinstance(target, Player)` first and dispatch
  to `_destroy_ship` + `_award_xp(kill_player)`, else Ferrengi.
- Add a regression test that instantiates P1 with enough fighters to
  one-shot P2 and asserts post-combat: P2 at StarDock, ship class
  MERCHANT_CRUISER, deaths=1, SHIP_DESTROYED event emitted.
- Separately, the scheduler's catch-all at `runner.py:561` should
  probably also wrap `apply_action` in a per-action try/except that
  emits an `AGENT_ERROR` and moves to the next player rather than
  nuking the whole match. Right now a single handler bug is enough
  to freeze every player for the rest of the game — that's a
  reliability problem independent of M2-1's root cause.

---

### M2-2. Unprovoked PvP outside FedSpace has zero alignment cost — gap

**Context.** Same attack as M2-1. P1 initiated combat on P2 (an
alliance-proposed neutral player, not a previous aggressor) in
non-FedSpace sector 514. Pre-attack alignment: 0. Post-attack
alignment: 0. No delta.

Looking at `_handle_attack` in `runner.py`:

```python
if player.sector_id == K.FEDSPACE_SECTOR_ID:
    player.alignment -= 200
    return ActionResult(ok=False, error="FedSpace — combat forbidden")
```

The only alignment adjustment for attacking another player is the
FedSpace refusal (which happens *before* combat resolves). Once you
leave FedSpace, attacking a neutral/friendly player is morally free.

**Impact.** In classic TW2002, attacking a non-Evil player cost you
alignment proportional to the target's alignment. Without any
alignment cost, the "FedSpace safety + alignment system" loses most
of its teeth — a high-alignment player can pirate freely the moment
they leave sector 1.

**Sketch.** In `_resolve_ship_combat` (or `_handle_attack`):
- If target is a Player and target.alignment >= 0, subtract a
  penalty from attacker (e.g. `attacker.alignment -= max(10,
  target.alignment // 2)`).
- If target was already Evil, smaller or no penalty.
- Optionally, the penalty should be witnessed → emit an
  `ALIGNMENT_CHANGED` event so spectators and LLM opponents can see
  who went rogue.

---

### M2-3. COMBAT event payload doesn't carry deltas or XP award — friction

**Context.** M2-1 attack produced this payload:

```json
{
  "attacker": "P1", "defender": "P2",
  "attacker_f": 8020, "attacker_s": 2984,
  "defender_f": 0, "defender_s": 0
}
```

Post-combat values only. To figure out "I lost 16 shields, P2 lost
20 fighters" I had to snapshot pre-combat state separately. The
payload also doesn't include XP awarded, alignment delta, whether
the target was destroyed, or a reason (collision vs ordered attack).

**Impact.** A driver agent has to manually save pre-state before
every attack action or parse two events in sequence to reconstruct
the delta. The UI can't render "P2 lost 20 fighters" without the
same workaround. A corp-ally copilot can't watch the event stream
and say "our ally just got shredded" unless it also snapshots.

**Sketch.** Enrich the payload:

```json
{
  "attacker": "P1", "defender": "P2",
  "pre":  {"a_f": 8020, "a_s": 3000, "d_f": 20, "d_s": 0},
  "post": {"a_f": 8020, "a_s": 2984, "d_f": 0,  "d_s": 0},
  "delta":{"a_f": 0,    "a_s": -16,  "d_f": -20,"d_s": 0},
  "attacker_xp_gained": 5,
  "attacker_alignment_delta": 0,
  "destroyed": true,
  "reason": "ordered_attack"
}
```

Same shape should work for NPC combat, collisions, and mine
detonations — gives one canonical combat payload.



---

### M2-4. `buy_ship` massively under-credits `net_worth` (M1-12 confirmed on two ships) -- bug

**Context.** Match 2B, d1t1: P1 bought Havoc Gunstar via
`buy_ship havoc_gunstar` while carrying a merchant_cruiser.
- Credits: 999,000 -> 564,325 (spent 434,675 cr out-of-pocket after
  10k trade-in credit for the merchant_cruiser).
- `net_worth`: 1,020,650 -> 787,825 (delta **-232,825**).
- Havoc Gunstar list price: 445,000 cr.

If the ship were valued at list-minus-trade-in (435k), `net_worth`
should have been FLAT (-435k cash, +435k ship). Instead the ship is
credited at ~201k inside `net_worth` accounting -- **a 234k
undervaluation per purchase**.

**Impact confirmed on P3 too.** Same match, d1t123: P3 bought a
BattleShip (869,675 out of pocket, list 880k). `net_worth`
1,021,284 -> 570,959 (delta -450,325). BattleShip credited at
~419k, undervalued by ~450k.

This is the M1-12 pattern reproduced on a clean match with two
independent purchases, so the bug isn't a trade-in accounting edge.

**Sketch.** `net_worth` almost certainly counts ship value from
only one or two SHIP_SPECS fields (e.g. hull cost without
per-hold/fighter/shield modifiers). Either use the list price from
SHIP_SPECS directly or make `net_worth` include both paid-cash and
ship-upgrade at parity.

**Impact on play.** The ladder is scored by `net_worth`. Upgrading
your ship -- the most expensive, most consequential decision in the
game -- is a *penalty* on the scoreboard. Players who hoard cash in
a merchant_cruiser look better on the board than players who
invested in a Havoc/BattleShip. Badly warps incentives.

---

### M2-5. Planet ownership is invisible to `net_worth` -- bug

**Context.** P1 deployed a Genesis torpedo at s514 (d1t91),
consuming 1 torpedo worth 25,000 cr. `net_worth` dropped
787,825 -> 763,450 (delta -24,375, matches torpedo cost). The
resulting L-class planet `Phoenix 514-28` owned by P1 (with
seed colonists + production lines running) contributed **zero** to
`net_worth`.

Same pattern on P3's and P2's planets through day 3.

**Impact.** Another anti-incentive: deploying Genesis is scored as
a pure cash burn unless/until you build a high-level citadel,
because the planet itself doesn't show up. The engine does carry
all the data (`planet.colonists`, `planet.stockpile`,
`planet.citadel_level`) to price this properly.

**Sketch.** Add to the `_compute_net_worth` routine:
- Base planet value: ~25,000 cr (matches Genesis cost -- restores
  the invariant).
- + stockpile @ current port prices (fuel_ore 20, organics 25, eq 35).
- + citadel_level bonus (L1 = 25k, L2 = 50k, ...) reflecting the
  cash + colonist investment.
- + a fighter-garrison line at 50 cr/fighter.

**Related upgrade.** Planets should also surface in `observation`
for the owner (ideally with stockpile + production estimates) so a
driver agent can plan trade runs to/from their own planets without
calling `/api/sector/<id>`.

---

### M2-6. Hint says `photon_missile` / `ether_probe` (singular) but engine requires plural -- bug

**Context.** Driver read `observation.action_hint` which lists:
`buy_equip (fighters/shields/holds/armid_mines/limpet_mines/atomic_mines/genesis/photon_missile/ether_probe/colonists)`

Issuing `buy_equip item=photon_missile` or `item=ether_probe`
returned `agent_error P1: invalid action: unknown item`. The
correct names are `photon_missiles` and `ether_probes`. The
other items accept singular (`genesis`, `atomic_mines`, etc.).

**Impact.** Two wasted agent turns on debug. Harder to write a
robust external client -- the hint is authoritative and lies here.

**Fix.** Either (a) normalize the engine to accept both singular
and plural for all items, or (b) fix the hint text to match the
engine. (a) is more forgiving; both are trivial.

---

### M2-7. Scheduler `4-wait auto-end-day` interacts badly with a persistent queue -- gap/bug (FIXED)

**Context.** Match 2B d3-d4. The driver subagent got stuck in an
`agent_thought waiting for day end` -> `wait` loop. The
scheduler's intended guardrail (`runner.py` ~L506):

`if waits.get(agent.player_id, 0) >= 4: player.turns_today = player.turns_per_day`

fires correctly -- after 4 consecutive waits, the day auto-ends.
**But the HumanAgent's submitted-action queue is NOT cleared on
auto-end.** Any actions queued BEHIND those 4 waits (including
productive actions like `scan`, `warp`, `attack`) just sit
until the next day, and then the next 4 waits in front of them
trigger ANOTHER auto-end. A human who has accidentally queued
`[wait, wait, wait, wait, build_citadel]` has just signed up
for a 2-day delay on their citadel.

**Reproducer (observed live).**
1. Queue 12 `wait` + `scan` + `warp` + `attack` in that
   order (pending = 15).
2. Wait for the queue to drain across day starts.
3. Each day: 4 waits fire, day auto-ends (queue drops by 4),
   remaining 8+3 actions persist to tomorrow.
4. `scan` / `warp` / `attack` don't fire until day 4 from
   submission.

**Impact.** In M2B this locked the primary out of the engine for
3+ real-time days while trying to take over P1 from a stuck
driver. No path to recover without killing the server.

**Sketch.**
1. On auto-end-day, DROP any remaining `wait` actions at the
   head of the queue (not all actions -- specifically the wait
   streak that caused the auto-end).
2. OR clear the queue entirely and emit a warning.
3. PLUS expose `DELETE /api/human/queue?player_id=P1` so an
   orchestrator can flush a stuck queue without killing the
   server (also fixes the orchestration gap below).

---

### M2-8. No queue-flush / cancel endpoint for a HumanAgent -- gap (FIXED)

**Context.** When the driver subagent was stalled in M2B the
primary had no way to reset P1's queued actions short of killing
the server. `/api/human/action` only appends; `pending` is
exposed but there's no `cancel` or `clear`.

**Impact.** No admin recovery from a stuck external agent. Every
stall requires a full match restart, losing state.

**Sketch.**
- `DELETE /api/human/queue?player_id=P1` -> clears queue, returns
  count dropped.
- `GET /api/human/queue?player_id=P1` -> returns the ordered list
  of pending Actions for transparency (right now the only signal is
  the integer count returned on submit).
- Optional: `POST /api/human/action?replace=true` to atomically
  swap a single queued action.

---

### M2-9. `agent_thought` is not a submittable Action -- friction (docs)

**Context.** Attempted `POST /api/human/action` with
`kind=agent_thought` to leave a narration breadcrumb in the
event stream. Got a pydantic enum-reject error listing the 31
valid kinds. `agent_thought` is *emitted* by the engine but
can't be *submitted* by an external client.

**Impact.** A Cursor driver or web client can't leave a
free-form note in the event stream for an observer without a
custom path. Low severity but surprising.

**Sketch.** Option A: accept `agent_thought` as an Action
(engine simply emits it without consuming a turn). Option B:
add a `POST /api/human/thought` endpoint that just appends an
event. Either is ~5 lines.



---

### M2-7 + M2-8 FIX VERDICT (2026-04-21)

Both shipped together as a single P0 patch before Match 3 (tinybox / qwen3.5:122b).

**M2-7 fix (`src/tw2k/server/runner.py` + `src/tw2k/agents/human.py`).**
The 4-wait auto-end-day guard now calls `agent.drop_leading_waits()`
when auto-ending. The new `HumanAgent.drop_leading_waits()` strips
only the contiguous leading run of `WAIT` actions (preserving
anything productive behind them). The emitted `AGENT_THOUGHT`
payload now carries `waits_flushed: N` so the forensic log shows
the flush happened. Non-human agents ignore the call via duck-type
fallback (`getattr(agent, "drop_leading_waits", None)`).

**M2-8 fix (`src/tw2k/server/app.py` + `src/tw2k/agents/human.py`).**
New `DELETE /api/human/queue?player_id=P1` endpoint calls the new
`HumanAgent.clear_queue()` method. Returns
`{"player_id": "P1", "dropped": N, "pending": 0}`. Error cases:
400 missing id, 404 no-such-player, 409 not-a-human, 503 no-match.
Safe to call while `act()` is blocked on `queue.get()` � the
coroutine just keeps waiting for the next push.

**Regression coverage** in `tests/test_human_queue_flush.py`:
- `test_drop_leading_waits_strips_only_leading_run` (unit)
- `test_drop_leading_waits_empty_is_zero`
- `test_drop_leading_waits_non_wait_head_is_zero`
- `test_clear_queue_drops_everything` (unit)
- `test_auto_end_day_flushes_leading_wait_streak` (integration:
  queue `[wait x 8, scan]` -> scheduler consumes 4 waits, fires
  guard, flushes remaining 4, scan surfaces)
- `test_delete_queue_flushes_and_returns_dropped_count` (HTTP)
- `test_delete_queue_404_on_unknown_player`
- `test_delete_queue_409_on_non_human_slot`
- `test_delete_queue_503_when_no_match`
- `test_delete_queue_400_on_missing_player_id`

All 10 green locally. These fixes do not affect AI-only matches
(no human slot = `drop_leading_waits`/`clear_queue` never
called), but close the door on the M2B stall pattern the next time
a driver subagent plays P1.



---

## Match 4 findings (seed 17, 1M credits, qwen3.5:122b via tinybox, `--play-to-day-cap`)

Captured live while Match 4 is still running (snapshot at day 21 /
tick 1445 / ~9.5 h wall time). All three players alive, planet empires
forming, alliance A1 (P2+P3) vs lone P1 (corp SOL), Ferrengi killed
P2 on d15 and P3 on d17, both respawned and kept playing � the
elimination fix works.

### M3-1 (half-fix). Qwen3.5:122b returns empty `content` under JSON mode � bug

**Context.** After shipping the `<think>...</think>` stripping + the
bracket-balanced last-`{...}` extractor for Match 4, we expected
the parse-error rate to collapse. It halved (from ~50% to ~34%) but
didn't collapse. Forensic pass over 2000 events:

- 337 parse-error thoughts out of 977 total thoughts (34.5%).
- **335 of those 337 are literal empty content** � i.e. the model
  returned `message.content == ""` and the parser correctly
  gave up.
- Only 2 of 337 had non-empty content that still failed JSON. The
  parser fix for those is effectively complete.

**Root cause.** OpenWebUI's Ollama `/ollama/v1/chat/completions`
shim, when serving a reasoning model like `qwen3.5:122b` with
`response_format={"type":"json_object"}`, sometimes puts the
entire answer into the **`reasoning`** sibling field and leaves
`content` empty. The smoke test we ran before launch already
showed this shape:

`json
{"message":{"role":"assistant","content":"",
           "reasoning":"Thinking Process:\n\n1. ..."}}
`

`_call_custom` only reads `choices[0].message.content`. Empty
string -> `_parse_response` returns None -> the agent WAITs that
turn. At 120 turns/day x 3 agents we're losing ~122 agent-turns
per game-day to this. It's the single biggest throughput drag on
the current setup.

**Fix sketch (do after Match 4 ends).** In `_call_custom` read
both fields and prefer content, falling back to reasoning:

`python
msg = resp.choices[0].message
text = (getattr(msg, "content", "") or "").strip()
if not text:
    # OpenWebUI/Ollama reasoning-model fallback: answer is in the
    # 
easoning sibling field. Only shows up on providers that
    # split chain-of-thought from final content.
    text = (getattr(msg, "reasoning", "") or "").strip()
return text
`

The existing `<think>`-stripping in `_parse_response` already
handles the reasoning-prose-plus-JSON shape, so this one fallback
hop should cut Match-4-style parse errors to near zero.

Also worth doing at the same time:
- Bump `TW2K_CUSTOM_MAX_TOKENS` default from 700 to 1200 for
  reasoning-class models.
- When the final parse still fails, log the first 200 chars of
  BOTH `content` and `reasoning` in the parse-error thought so
  the next forensic pass doesn't have to re-derive this shape.

Regression test idea: mock an openai client that returns
`ChatCompletion` with `content=""` and `reasoning='{"action":{"kind":"wait","args":{}}}'`,
assert the agent submits a wait (not a parse-error WAIT).

### M4-2. `buy_equip fighters` ignores ship hull capacity � gap/friction (18 hits)

**Context.** 18 `agent_error` events with
`"exceeds ship fighter capacity"`. The hint lists the cost
and the StarDock price, but not the cap. With everyone flying
CargoTrans / Battleships, the cap matters as much as the cost.

**Fix.** `observation.action_hint` (for `buy_equip fighters`)
should include `max_buy = ship.fighter_cap - ship.fighters` so
the agent can see in one place how many it can actually take.
Same story for `shields` -> `shield_cap`.

### M4-3. `buy_equip` accepts `qty<=0` then errors � bug (7 hits)

**Context.** 7 `agent_error` with `"invalid fighter quantity"`.
The action passed the schema (`qty` is an int), but the handler
rejected it. So the agent's turn is consumed on a no-op.

**Fix.** Either accept `qty<=0` as a no-op silently (no turn
consumed) or reject in `apply_action` BEFORE incrementing
`turns_today`. The second option is more honest � it's an input
error, should not cost a turn. Add a unit test with `qty=0`
and `qty=-5` asserting `turns_today` is unchanged.

### M4-4. `buy_equip ether_probe` (singular) still rejected � bug (4 hits)

**Context.** Recurrence of M2-6. The observation hint on at least
some turns still says `ether_probe` (singular), the engine wants
`ether_probes` (plural). Agents of course match the hint.

**Fix.** Unchanged from M2-6: normalize the item name in
`apply_action` or in the hint, once and for all. Pick plural
(matches `fighters`, `shields`, `holds`, `photon_missiles`),
then accept the singular as an alias in the action handler for
back-compat.

### M4-5. Citadel L3+ colonist threshold not in `action_hint` � gap (2 hits + 1 `only 0 colonists in cargo`)

**Context.** P3 landed on planet 29 and tried `build_citadel`
twice, both rejected with `need 4000 colonists on planet
(have 1203)` / `(have 1278)`. The thought shows P3 understands
the general idea � they assigned 75 more colonists between
attempts � but the exact threshold isn't visible.

**Fix.** Planet observation should carry the next-citadel
requirements:

`json
"planet": {
  "id": 29, "citadel_level": 2,
  "next_citadel": {
    "level": 3, "cost_cr": 25000, "cost_col": 4000,
    "have_col": 1278, "shortfall_col": 2722
  }
}
`

### M4-6. No `alliance_status` in observation � gap (3 `alliance already active` hits)

**Context.** 3 `agent_error` on `accept_alliance` for an
already-active alliance. The alliance-formation event fires, but
the agent that proposed it tries to `accept` it on a later turn
and gets rejected.

**Fix.** Add an `alliances` block to every observation:

`json
"alliances": [
  {"id": "A1", "members": ["P2","P3"], "status": "active",
   "created_day": 11}
],
"alliance_invites": [{"id":"A2", "from":"P1", "expires_day": 24}]
`

Agents can then see at a glance "I'm already in A1, don't re-accept".

### M4-7. `deploy_genesis` hint doesn't state torpedo requirement � gap (2 hits)

**Context.** 2 `agent_error` on `deploy_genesis` with
`no genesis torpedoes loaded`. The agent had the sector + 3
hops from StarDock + an empty sector, but not the torpedo in
cargo. The action doesn't feel like it should be free, but the
hint doesn't flag this precondition.

**Fix.** Make the `deploy_genesis` hint carry
`cargo_has_genesis_torpedo: true/false` and include a short
recipe in `action_hint` text: `"requires 1 genesis torpedo
in cargo (buy at StarDock for Ncr)"`.

### M4-8. `ether_probes` / `photon_missiles` buy hint missing `requires-cargo-hold` � observation

**Context.** Not a direct error this match, but while chasing M4-4
I noticed `buy_equip photon_missiles` takes a cargo-hold slot
per missile, and that's not surfaced in the hint either. Same
pattern as M4-7 � pre-conditions buried in the handler.

**Fix.** Bundle all buy-type preconditions into the hint as a
single `requirements` block the LLM can scan:
`requires_holds_free`, `requires_ship_class_at_least`,
`requires_alignment`, `requires_experience`, etc.

### M4-9. Ferrengi `ferr_15_348` killed P2 and P3 on different days � observation

Same raider (1600 f / 243 s) one-shotted both P2 (d15) and P3 (d17).
Not a bug per se � Ferrengi are meant to be persistent � but worth
noting:

- Ferrengi fleet growth is real (64 active raiders by day 21, some
  at 3100 f / 500 s).
- Ferrengi ships regenerate / repair between kills apparently.
- Agents are not reading the `ferrengi_in_sector` hint as a hard
  stop.

**Fix candidate (later).** Observation hint when a Ferrengi is in
the current or any adjacent sector should be loud (`threat_level =
critical`), and the warp hint should star that target sector so
the agent can't miss it. Today the agent warps straight into the
raider's sector and dies.

### M4-10. Pace projection vs `--max-days` � observation

At the current rate (~2.2 game-days per real-hour, limited by the
122B-MoE latency plus the 34% empty-content waste) a full 365-day
match takes ~165 hours of wall clock. If we want overnight
runs to actually finish, future configurations should pair a
shorter cap (30-60 days) with the same per-player-credit setting,
or fix M3-1 to recover the 34% lost turns.



### M4-11. Big events don't show up in the spectator event feed � gap

**Context.** While narrating the match the user noted they couldn't
see the broadcasts, hails, genesis deploys, alliance formations,
etc. in the event ribbon. I had to dig them out of `/events` to
reconstruct the story, which means the spectator UI is silently
suppressing some of the best content in the game.

**Verified root cause.** Every one of those events already ships a
rich `summary` string from the engine � e.g.

- `"Commodore Eris Vahn (broadcast): TRAPPED P2 in 348-450 dead-end..."`
- `"==== ALLIANCE FORMED [A1]: Admiral Tanis Rho + Commodore Eris Vahn ===="`
- `"Admiral Tanis Rho detonated a Genesis torpedo � new M-class planet Phoenix 679-29 forms..."`
- `"==== Citadel L2 on Genesis 651-28 now operational ===="`
- `"*** Commodore Eris Vahn's ship destroyed (ferrengi); ejected to StarDock [death #1/3] ***"`

The problem is on the client: `web/app.js :: kindCategoryClass`
lumps ALL of these into the single `diplomacy` category:

`js
if (kind === "hail" || kind === "broadcast" || kind === "corp_memo"
    || kind === "alliance_proposed" || kind === "alliance_formed" || kind === "alliance_broken"
    || kind === "assign_colonists" || kind === "build_citadel" || kind === "citadel_complete"
    || kind === "genesis_deployed") return "diplomacy";
`

`eventPassesFilter` then drops every `diplomacy` event when
`state.filters.diplomacy` is off. Additional bug: `corp_create`,
`land_planet`, `liftoff`, `deploy_fighters` fall through to
the `system` bucket because they aren't matched anywhere, so
they vanish when the system filter is off.

**Fix sketch (post-match).**

1. Split `diplomacy` into two categories:
   - `diplomacy` = hail, broadcast, corp_memo, corp_create,
     alliance_proposed, alliance_formed, alliance_broken.
   - `empire` = build_citadel, citadel_complete, genesis_deployed,
     assign_colonists, land_planet, liftoff, deploy_fighters,
     player_eliminated.
2. Promote the `empire` category to **on by default** alongside
   combat and trade. These are the match's headline moments; they
   shouldn't be opt-in.
3. Add a `headline` flag on the engine side (or a client-side
   derived check) for events whose `summary` starts with
   `====` or `***` � render those with a bolder/brighter
   style so alliance-formed, citadel-complete, and ship-destroyed
   can't scroll past unnoticed.
4. Make sure `corp_create`, `ferrengi_attack`, `deploy_fighters`
   have explicit classifier entries so nothing interesting lands
   in `system` by accident.
5. Re-verify: after the split and the defaults, spectate a 5-day
   scripted run (`tests/test_replay_roundtrip.py` style) and
   assert the rendered feed contains at least one each of
   `hail`, `broadcast`, `alliance_formed`, `citadel_complete`,
   `genesis_deployed`, `ship_destroyed`.

**Also worth fixing together:** the engine was emitting a genesis
deploy on `d4 t450` (P3 Tanis, "Phoenix 679-29") and a broadcast
chain from `d4 t379` onward (P2 Eris' "TRAPPED" message), both
of which I initially missed in my narrative because the
`limit=200` window rolled them off. The UI fix above solves the
spectator side of this; the evaluation workflow also wants a
`/events?kind=broadcast,genesis_deployed,...` filter so forensic
passes don't rely on `limit=` sizing.



### M3-1 PROPER FIX PLAN (do this before the next match)

Confirmed in Match 4: every D23 t1625-t1640 parse error on Commodore
Eris Vahn shows `content_len=0`. After 6 such empty-content responses
in a row the scheduler's auto-stand-down guard ended her day early
with 91 turns skipped (76% of a 120-turn day). This is the single
biggest quality-of-match lever we have.

**Layer 1 � read both fields in `_call_custom` (and `_call_openai` for parity).**

\\\python
resp = await client.chat.completions.create(**kwargs)
msg = resp.choices[0].message
content = (getattr(msg, "content", "") or "").strip()
if not content:
    # OpenWebUI + Ollama reasoning-model shim: when response_format=json_object
    # is set on a model like qwen3.5:122b the answer can land in the
    # reasoning sibling with empty content.
    content = (getattr(msg, "reasoning", "") or "").strip()
return content
\\\

**Layer 2 � provider-side headroom.**
- Bump `TW2K_CUSTOM_MAX_TOKENS` default from 700 to **1200**. The
  reasoning trace alone can eat 400-600 tokens; under a 700 cap the
  JSON gets truncated and the shim falls back to reasoning-only.
- Pass `extra_body={"options": {"num_predict": 1200}, ...}` to the
  Ollama native path for the same reason.

**Layer 3 � self-diagnostic parse-error thoughts.** Replace the
current `[parse error] couldn't parse: <content_preview>` with:

\\\
[parse error]
  content[0:200]   = "<first 200 chars or (empty)>"
  reasoning[0:200] = "<first 200 chars or (empty)>"
  finish_reason    = "length" | "stop" | "content_filter" | ...
\\\

So the next time this regresses (or a new provider splits fields
differently) we can see the shape of the failure without re-deriving
it from the Ollama backend.

**Layer 4 � regression tests in `tests/test_phase_abc.py`.**

1. `test_custom_falls_back_to_reasoning_when_content_empty`
   Mock `AsyncOpenAI` returning `ChatCompletion` with
   `content=""` and `reasoning='{"action":{"kind":"wait","args":{}}}'`;
   assert the returned Action is WAIT, not a parse-error WAIT.
2. `test_custom_prefers_content_over_reasoning_when_both_present`
   Don't drop the final answer in favour of the scratchpad.
3. `test_custom_parse_error_thought_contains_both_previews`
   Force a hard parse failure and assert the emitted thought carries
   both `content[0:200]` and `reasoning[0:200]` tags.

**Layer 5 � validate against live model.** 30-day
`--play-to-day-cap` smoke match on qwen3.5:122b via tinybox.
Success criteria:

- parse-error rate < 5% of LLM calls (Match 4 baseline: 34.5%).
- Zero `agent_thought "Standing down for the day (N turns skipped)"`
  events traceable to empty-content streaks.
- Concrete-actions-per-game-day >= 30 per player (Match 4 P2 at day 23
  had ~12 after Eris's D23 skip).

**Layer 6 � provider-agnostic helper.** Move the "content-or-reasoning"
coalescing into a shared `_coalesce_message_text(msg)` used by
`_call_openai`, `_call_custom`, `_call_deepseek` and `_call_xai`
so the next model that splits these fields (DeepSeek-R1, Grok-4
reasoning, gpt-oss thinker, ...) is covered automatically. Doc the
known-splitter models in the helper's docstring.

Effort estimate: ~30 lines of source, ~60 lines of test, ~45 min
including the 30-day validation match. Do this WITH a rebuild of the
`play_to_day_cap` banner line so the next match also visibly
confirms the flag is on.

### M4-12. "False trap" from closed-world reading of `known_warps` -- bug

**Context.** Commodore Eris Vahn broadcast a "TRAPPED in 348-450
dead-end" SOS from day 3 onward. She wasn't actually trapped --
every universe is fully connected by generation-time invariant
(`test_universe_is_fully_reachable_from_sector_1`). She'd simply
never scanned or probed beyond the two sectors she'd visited, so
her `known_warps` contained only the `348 <-> 450` pair. She
concluded "absence of edges in my map == there are no edges" and
ping-ponged 348 <-> 450 for 10+ warps across days 5-11.

**Forensic data:**

- Scans by P2 during alleged trap (d3-d11): **zero**.
- Scans by P3 during rescue (d3-d11): **zero**.
- Actual exit: a Ferrengi killed Eris in 450 on d15 t1030; respawn
  ejected her to StarDock (sector 1), which is how she "escaped".
  Same thing happened to P3 two days later.

**Root cause.** The observation surfaces `known_warps` and
`known_sectors` but never tells the agent "there are unexplored
edges you can still discover". So "what I don't know doesn't exist"
is a plausible reading of the data.

**Fix sketch.**

- Include `sector.warps_count` (total warps out, from the
  universe) alongside `sector.known_warps` (the ones you've
  personally revealed). Let the agent compute the gap.
- Add a one-liner to `action_hint` when `len(known_warps) < warps_count`:
  `"at least {N} unexplored warps from this sector -- run scan (basic)
  to reveal them"`.
- Stronger: refuse the `"dead-end"` narrative in the system prompt.
  Something like: "known_warps is your PERSONAL map, not the
  universe. If known_warps is empty or short, scan before concluding
  anything is a dead-end. TW2002 universes are always fully connected."

**Regression.** Scripted 5-day match where an agent starts in a
sector with warps_count=4 but known_warps=[]. Assert the agent runs
at least one scan within its first 5 turns (heuristic) and does NOT
emit a broadcast containing "dead-end" / "trapped".

### M4-13. Self-chatter amnesia -- bug (20+ redundant hails observed)

**Context.** P3 Admiral Tanis Rho sent the **same** "FINAL ALLIANCE
PROPOSAL" hail to P2 19 times between d9 and d13, continuing to
re-send it for two full game-days AFTER alliance A1 was already
formed (d11 t901). Similar pattern: P2 sent 8+ "TRAP CONFIRMED,
STOP PROBING" replies on day 7 alone.

The agent is planning each turn from observation without reading
its own recent outbound messages -- it has amnesia about what it
just said.

**Fix.** Add a `my_outbox` block to every observation, capped at
the last N=10 messages across hail + broadcast + corp_memo:

\\\json
"my_outbox": [
  {"day": 11, "tick": 901, "kind": "hail", "to": "P2",
   "summary": "FINAL ALLIANCE PROPOSAL..."},
  {"day": 11, "tick": 898, "kind": "hail", "to": "P2", ...}
]
\\\

Also add `outstanding_proposals` and `active_alliances` /
`active_corps` blocks so the agent can see "A1 already active
with P2" without having to infer it.

### M4-14. Hail-delivery status is invisible to sender -- gap

**Context.** Eris sent 2 direct hails to Mira (d5 t501, d6 t632)
offering 25% of future profits for a rescue. Mira never sent a
response and also never gave a declination. From Eris's observation
there's no way to know whether Mira saw the hail, is ignoring it,
or her client is broken. Eris ended up re-broadcasting the SOS 4+
more times on the assumption "maybe it didn't go through."

**Not necessarily a bug** -- silence is a valid strategy. But the
sender has no feedback loop.

**Fix.** Observation sidecar `hail_inbox_status` showing the last
N inbound hails (already partially present) AND an
`outbound_hail_log` with per-target `last_sent_day` +
`replies_received` counters. Enough to make the "they're
ignoring me" signal legible so the agent can stop re-broadcasting.

**Lower-priority alternative:** a `silent` / `ignore` flag on
the hail endpoint so ignore becomes a first-class action the target
has to choose (like a decline), rather than happening implicitly
by doing nothing. Probably too heavy-handed; do the observation
fix first.

