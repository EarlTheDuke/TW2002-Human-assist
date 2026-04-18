# The Healthy Game Playbook

> A step-by-step arc of what a **successful, healthy TradeWars 2002 game** looks like,
> synthesised from the TradeWars 2002 Bible (Blackfist / Justin Curry, 1993 → Clme, 2007),
> The Cabal's Secret Hideout strategy archive, the TradeWars Documentation Wiki (classictw),
> tw2002.win reference, and The Stardock archive.
>
> **Two jobs** for this document:
> 1. Source text for a *simple, concrete* agent prompt — so every LLM agent knows the shape of a winning game.
> 2. A scoring rubric for the human/spectator — so we can tell whether the AI is actually playing well.
>
> Every mechanic referenced here is implemented in our TW2K-AI engine (see `docs/FEATURE_COMPARISON.md` — all P0/P1 gaps closed during the Phase A/B/C pass).

---

## 0. The one-line version

> **Trade → Save → Found a hidden planet → Build a Citadel → Defend it → Dominate the late game.**

The whole game is a climb from a 20-hold Merchant Cruiser ferrying cargo between two ports to an owner of a Level-5+ Citadel (or a corp of them) that out-produces and out-fights the opposition. The question is just **how fast**, **how safely**, and **how many rivals you take out on the way**.

---

## 1. Victory conditions we actually judge on

In a tournament-length game (our default: 5–30 days) **a player wins by any of:**

| # | Victory | Trigger in our engine |
|---|---|---|
| 1 | **Highest net worth** at game end | `is_finished` returns true at `max_days`, rank by `net_worth` |
| 2 | **Economic threshold** | Net worth > scaled `ECONOMIC_VICTORY_THRESHOLD` |
| 3 | **Last player standing** | All other players `alive=False` (3 deaths each) |

So "healthy" play = **earning credits faster than you can lose them, while staying alive.**

---

## 2. The five stages of a healthy game

Stages are **soft** — a great player compresses them; a timid one stretches them. But every healthy game hits every stage in order.

| Stage | Typical window* | Primary goal | Exit trigger |
|---|---|---|---|
| **S1. Opening Trades** | Day 1 (first 100–200 turns) | Get to positive cash flow. | First port-pair loop is paying & known. |
| **S2. Capital Build** | Day 1 late → Day 2 | Stack ~500k credits on-hand or in bank. | Bank has ≥500k OR ship upgrade purchased. |
| **S3. Establish a Home** | Day 2 → Day 3 | Deploy Genesis in a safe dead-end; start Level-1 Citadel. | Citadel L1 complete, planet has colonists producing. |
| **S4. Fortify & Form** | Day 3 → Day 5 | Reach Citadel L2 (combat) → L3 (quasar). Optionally form or join a corp. Alliance with non-threats. | L2+ citadel, ≥1 ally or corp member, ≥1M net worth. |
| **S5. Project Power** | Day 5+ | Hunt ports, hunt rivals, upgrade to ISS, reach L4–L5 citadel, close out the game. | Victory condition triggers. |

\*Windows assume `max_days=6` (our current default) and 1,000 turns/day. With `max_days=2` the player must collapse S1–S3 into one day and treat S4/S5 as a stretch goal.

---

## 3. Stage-by-stage playbook

### S1 — Opening Trades (Day 1, first ~200 turns)

**What success looks like**

1. **Scan the starting neighbourhood.** Spend 1 turn on `scan` from the start sector to see adjacent ports. If you see a Class 1–8 port adjacent, you have a trade candidate.
2. **Find a port pair** — two adjacent ports where opposite commodities are sold:

   | Pair | Buys at A → Sells at B | Buys at B → Sells at A |
   |---|---|---|
   | Class 1 ↔ 2 | Fuel Ore | Organics |
   | Class 1 ↔ 3 | Fuel Ore | Equipment |
   | Class 2 ↔ 3 | Organics | Equipment |
   | Class 3 ↔ 6 | Equipment | F.O. + Org |
   | Class 5 ↔ 6 | F.O. + Equip | Org |

   *(Any "S"/"B" mismatch on a single commodity works — for our port codes, a port of `SSB` paired with a `BBS` is ideal.)*

3. **Trade the loop**: buy cheap commodity at A → warp to B → sell high → buy opposite commodity → warp back → repeat.
4. **Haggle every transaction.** First offer should be 10–15% better than list. If the counter-offer fails, our engine auto-settles at list — so haggling is free money when it hits.
5. **Stop draining a port at ~50% stock.** The first half of a port's stock is worth *more than twice* the second half (Cabal, Economy ch.3). Move on to a new pair when prices flatten.

**Done-for-the-day tells**

- Net worth up ≥20–30% from starting (≥~48k from ~40k).
- Ship ended the day outside FedSpace (risky) OR inside FedSpace with <50k on-hand (safe — the original game taxes 10% over 50k).
- At least 2 distinct ports have been visited and `known_ports` map is growing.

**Unhealthy smells**

- Haggle bids *identical* to list every turn (agent isn't exploiting the free margin).
- Ship stuck in sectors 1–10 all day (no exploration).
- More than 3 `wait` actions in a row (engine auto-ends the day after 4 — already handled).

---

### S2 — Capital Build (Day 1 late → Day 2)

**What success looks like**

1. **Scale the trade circuit.** Find a second port pair and rotate between them (each pair is now half-drained and restocks overnight).
2. **Buy a Density Scanner** the first time you're at StarDock (our equipment catalog: `buy_equip kind=density_scanner`). This exposes `SCAN_TIER_DENSITY` and cuts port-finding turns in half.
3. **Deposit at StarDock** once you go over ~50k credits on-hand. Interest = 0 in the original game (and in ours), but the bank *protects* you from death-penalty cargo loss.
4. **Stretch goal: upgrade the ship.** StarMaster, Merchant Freighter, or Scout Marauder in StarDock — pay 25% trade-in on the old ship. Only do this if you can still afford ≥500k post-upgrade.
5. **Watch alignment.** Don't stray below 0 unless you're deliberately going pirate. If you are, flip past −100 quickly (pirate protection benefits).

**Done-for-the-day tells**

- Net worth ≥150–300k by end of Day 2.
- Player knows ≥6 ports and ≥30 sectors (`known_sectors` ≥30).
- Still alive; deaths = 0.

---

### S3 — Establish a Home (Day 2 → Day 3)

**What success looks like**

1. **Pick a safe sector.** Ideal candidate:
   - Exactly **one** warp in and **one** warp out, and they're the same sector (a cul-de-sac).
   - **No one-way backdoor warps into it** — use `plot_course` from more than one other sector to verify.
   - Not on a major FedSpace ↔ StarDock lane.
2. **Deploy Genesis Torpedo** (25k credits + 4 turns): `deploy_genesis` in the chosen sector.
3. **Ferry colonists from Terra (sector 1).** Fill holds with Commodity `colonists` → warp to your planet → `land_planet` → `assign_colonists` to fuel_ore (most), organics, equipment, and fighters.
4. **Start Citadel Level 1.** `build_citadel planet_id=…` deducts credits + colonists, sets a day-count timer. L1 builds in ~2 days at our defaults.
5. **Do NOT leave ship fighters on the planet pre-L2.** Anyone who finds it can land and take them. Park 1 fighter in the sector as a tripwire (so a visitor lights up your event log via `FIGHTER_REPORT`).

**Done-for-the-day tells**

- `planet.owner_id == you`, planet has ≥1000 fuel-ore colonists, `citadel_target=1`.
- Player has a bank of ≥200k credits left for stocking.
- No rival has entered your home sector (check event feed for foreign warp-in).

---

### S4 — Fortify & Form (Day 3 → Day 5)

**What success looks like**

1. **Citadel L1 → L2 (Combat Control).** At L2 you can leave fighters on the planet; invaders face 4:1 defensive odds. This is the single biggest security milestone in the game.
2. **Citadel L2 → L3 (Quasar Cannon).** Sector-shot combat becomes possible — planet fires on hostile ships that enter.
3. **Optional corporation.** At StarDock with ≥500k credits, `corp_create`. Invite a trusted second player. Benefits:
   - Shared planet landing (corp mates can refuel/restock).
   - Shared treasury (`corp_deposit` / `corp_withdraw`).
   - Corp-only ships unlocked (Corporate Flagship).
4. **Diplomatic layer.** `propose_alliance` with a rival who isn't directly on your trade route. Once both sides `accept_alliance`:
   - Neither side can attack the other (engine-enforced).
   - Good insurance while you're vulnerable pre-L5.
5. **Probe for enemies.** Use `probe` (ether probes) to remotely scout suspected enemy home sectors. `query_limpets` on any limpet you've deployed.

**Done-for-the-day tells**

- Citadel ≥ L2.
- Net worth ≥ 1M.
- At least one of: corp formed, ally accepted, or enemy planet located.

**Unhealthy smells**

- Agent is *still* trading the same two ports from Day 1 with no planet (stuck in S1).
- Player has ≥2M in cash but no citadel (over-saving, under-investing).
- Agent proposes alliance with *every* player including direct rivals (dilutes the diplomatic signal).

---

### S5 — Project Power (Day 5+)

**What success looks like**

- **Citadel L4** unlocks planet TransWarp — move the planet if discovered.
- **Citadel L5** unlocks shields — the planet becomes near-impregnable.
- **Imperial StarShip or Corporate Flagship** for the Attacker role.
- **Photon missile** (disables enemy fighters) or **atomic mine** (destroys a port or planet) for burst offence.
- **Take territory**: drop offensive fighters in choke sectors, take down rival planets/ports.
- **Endgame net worth push**: With a L4+ citadel and corp treasury you can compound faster than any trader without one. Lean into the daily production loop.

**Done-for-the-day tells (end of match)**

- Alive.
- Net worth > all rivals *or* all rivals eliminated.
- Player has played all 5 stages without skipping.

---

## 4. Universal tactics (every stage)

| Tactic | Why |
|---|---|
| **Turns = money.** Never end a day with unused turns when there's a trade available. | Engine auto-ends day after 4 consecutive `wait`s; don't waste them. |
| **Haggle every trade.** First offer 10–15% better than list. | Free margin on successful haggles; engine auto-settles failures at list (Phase A fix). |
| **Drop 1 fighter** in any sector you want to monitor. | Triggers `FIGHTER_REPORT` when anyone crosses it. |
| **Use `plot_course`** for anything >3 hops away. | Turns a 15-turn manual warp into 1 decision + N automatic warps. |
| **Keep ≥20% of holds free** at turn-end during early game. | Needed for colonists pickups / surprise arbitrage. |
| **Pay attention to the event feed.** Another player entering your home sector = emergency. | Our event stream exposes `warp` into your sectors with `FIGHTER_REPORT`. |
| **Alignment is a resource.** Staying neutral/positive = FedSpace protection + eventual Imperial StarShip path. Going −100 unlocks port robbery but forfeits Fed protection. | Our engine implements alignment tiers (`ALIGNMENT_TIERS` in `constants.py`) and XP rank (`RANK_TABLE`). |
| **Don't carry atomic mines unless you're about to use them.** | Any fighter/mine hit will detonate them — instant turn drain and alignment crash. |
| **The CEO should cloak and hide.** Don't sit on a planet you own if enemies are active. | Once Phase C adds cloaking we'll expose this; for now: stay mobile. |

---

## 5. Day-level progression rubric (for the spectator)

The watcher can score an LLM agent against these milestones per day. A healthy arc over 5 days hits most of these in order.

```
Day 1  ✅ Identified a port pair and completed ≥3 profitable round-trips.
       ✅ Net worth ended ≥20% above start.
       ✅ Visited ≥4 distinct sectors outside FedSpace.

Day 2  ✅ Ran ≥2 distinct port pairs.
       ✅ Net worth ≥ 150k.
       ✅ Bought a density scanner or ship upgrade.

Day 3  ✅ Identified a candidate home sector (1-in / 1-out / no backdoor).
       ✅ Deployed Genesis (`DEPLOY_GENESIS` event).
       ✅ Started `BUILD_CITADEL` target=1.

Day 4  ✅ Citadel ≥ L1 complete (event `CITADEL_COMPLETE`).
       ✅ Colonists on planet ≥ 2000 across F/O/E.
       ✅ Net worth ≥ 500k.

Day 5  ✅ Citadel ≥ L2.
       ✅ At least one of: corp formed, alliance accepted, enemy scouted.
       ✅ Net worth ≥ 1M OR rival eliminated.
```

Anything missed for ≥2 consecutive days = **arc is stalled**, flag for prompt tuning.

---

## 6. Anti-patterns (red flags we should fix)

| Symptom | Likely root cause | Fix lever |
|---|---|---|
| Agents stay within 5-warp bubble all game | Prompt doesn't say "explore". Engine doesn't surface distant ports. | Bigger prompt explicit nudge; `plot_course` pre-fill in observation. |
| All agents do the same port pair | Starting sectors or observation prompt is too uniform. | Diversified starts (already done), + prompt fingerprint variance. |
| No agent forms a corp / deploys genesis | Prompt never mentions planets/corps. | Add Stage 3+ milestones to prompt (this doc). |
| Haggle bids ≈ list every time | Prompt says "haggle" but gives no structure. | Prompt should specify "first offer 10–15% better than list". |
| Deaths > 0 before Day 3 | Agent attacking or blundering into mines / Ferrengi. | Prompt: "never attack until Stage 4 unless surrounded". |
| Alignment <−100 by Day 2 without pirate plan | Agent randomly firing on non-hostile ships. | Prompt: "alignment is a resource; don't burn it without a plan". |
| Net worth flat after Day 2 | Agent stuck in a drained pair or on `wait`. | Prompt: "if a port is <50% stock, find a new pair". |

---

## 7. The simple prompt (seed for Section 8)

We will use this document to build an **additive prompt** on top of the existing `SYSTEM_PROMPT`. It should be ~10 lines and map directly to the stage the agent is in. Outline:

```
You are playing TradeWars 2002. Your mission is to be the richest, most feared,
or last-alive player at the end. Follow this five-stage arc:

  S1 (Day 1, ≤200 turns): Find a port pair near your start. Trade it until stocks
     fall to ~50%, then find another. Always haggle 10–15% above list.
  S2 (End Day 1–2): Reach 500k credits. Buy a density scanner. Maybe upgrade ship.
  S3 (Day 2–3): Pick a dead-end sector (1-in, 1-out, no backdoor). Deploy Genesis.
     Ferry colonists from Terra (sector 1). Start Citadel L1.
  S4 (Day 3–5): Citadel L2 (defensive), optional corp, optional alliance with
     a non-threat. Probe enemy sectors. Citadel L3 for quasar cannon.
  S5 (Day 5+): L4/L5 citadel, ISS or Corp Flagship, take out rivals.

Turns are money — never end the day with unused turns. Don't attack in
FedSpace (you'll be killed by Federals). Don't leave fighters on a planet
before Citadel L2. Use `plot_course` for anything >3 hops away.
```

This is the text to wire into `src/tw2k/agents/prompts.py` as the stage-aware section — done in the next commit.

---

## 8. Watcher rubric JSON (for automation)

So that `scripts/watch_match.py` can auto-score per day, the milestones above are structured here:

```json
{
  "day_1": [
    {"check": "net_worth_gain_pct",    "threshold": 20},
    {"check": "distinct_trades",       "threshold": 3},
    {"check": "distinct_sectors",      "threshold": 4}
  ],
  "day_2": [
    {"check": "distinct_port_pairs",   "threshold": 2},
    {"check": "net_worth",             "threshold": 150000},
    {"check": "bought_upgrade",        "one_of": ["density_scanner", "ship_upgrade"]}
  ],
  "day_3": [
    {"check": "event_kind_seen",       "kind": "genesis_deployed"},
    {"check": "event_kind_seen",       "kind": "build_citadel"}
  ],
  "day_4": [
    {"check": "event_kind_seen",       "kind": "citadel_complete"},
    {"check": "net_worth",             "threshold": 500000}
  ],
  "day_5": [
    {"check": "citadel_level_min",     "threshold": 2},
    {"check": "any_of_events",         "kinds": ["corp_create", "alliance_formed", "probe"]},
    {"check": "net_worth",             "threshold": 1000000}
  ]
}
```

Implementation lives in `scripts/watch_match.py` (to be extended) — every day-tick it appends a ✅ / ❌ line per check to `match.log`, making "is the game healthy?" a one-glance question.

---

## 9. Source material

- **TradeWars 2002 Bible** — Justin Curry (1993), updated Blackfist (1994), Clme (2007).
  [penismightier.com/clme/Trade_Wars/Trade_Wars_2002_Bible.htm](https://www.penismightier.com/clme/Trade_Wars/Trade_Wars_2002_Bible.htm)
- **The Cabal's Secret Hideout — Economy** (chapter 3, port-drain math).
  `tw-cabal.navhaz.com/strategy/economy3.html`
- **TradeWars Documentation Wiki / classictw.com** — port-pair tables, citadel levels, TPPT.
- **tw2002.win reference** — citadel level effects (L1 treasury, L2 combat, L3 quasar, L4 transwarp, L5 shields, L6 defense net).
- **The Stardock archive** — planet class production rates, ship catalog, defense strategy.
- **Gypsy's Big Dummy's Guide to TradeWars Text** (classictw wiki) — turns & day 1 walkthrough.

All cited verbatim in the research pass on 2026-04-18.
