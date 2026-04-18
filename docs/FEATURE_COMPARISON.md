# TW2K-AI vs Original TradeWars 2002 — Feature Comparison

> Audit date: post-haggle/diversification fixes.
> Source of truth for "we have it": code refs in `src/tw2k/`, `web/`, audited by sub-agent.
> Source of truth for "original has it": TW2002 v3.x classic spec (Gary Martin / EIS edition).

Legend: ✅ done · ⚠️ partial / shallow · ❌ missing · 💤 stub (constant/enum exists, no logic) · ✂️ intentionally cut (out of scope for AI exhibition).

Priority for completion: **P0** (game-defining; spectator-visible drama), **P1** (deep play, alliances/late-game), **P2** (flavor / parity), **P3** (BBS-era plumbing not relevant to LLM exhibition).

---

## ✅ Post-implementation status (Phases A + B + C)

As of the Phase A/B/C implementation pass, **every P0 and most P1 items below are now implemented** in code and covered by `tests/test_phase_abc.py` + `scripts/smoke_phase_abc.py`:

**Phase A — "Make the late game exist"** (all complete):
- `assign_colonists` wired — ship↔planet pool transfers for F/O/E/fighters.
- `build_citadel` wired — L1–L6 with day-build timer, cost, and colonist consumption.
- `deploy_genesis` action — consumes a torpedo, creates new planet in current sector.
- Player elimination — `alive=False` after `K.MAX_DEATHS_BEFORE_ELIM` deaths.
- Per-ship `turns_per_warp` — `_warp_cost_for` honors `K.SHIP_SPECS`.
- Ferrengi roam & hunt — daily move + sector attack step in `tick_day`.

**Phase B — "Make the universe usable & dramatic"** (all complete):
- `plot_course(target, execute?)` — BFS pathfind + optional multi-warp execution.
- `photon_missile(target)` — disables target's fighters for `PHOTON_DURATION_TICKS`.
- `deploy_mines(kind=atomic)` — atomic detonation, damages ports/planets, hits alignment.
- Limpet tracking — auto-attach on warp through seeded sector, `query_limpets` reports.
- Citadel combat — quasar cannon and interdictor hooks in ship-vs-planet resolution.
- Replay scrubber UI — range slider over event seq + "live" toggle in spectator panel.

**Phase C — "Polish & parity"** (all complete):
- `propose_alliance` / `accept_alliance` / `break_alliance` — formal engine state + UI chips.
- Scan tiers — `SCAN_TIER_BASIC/DENSITY/HOLO/ETHER`, plus `probe` action for remote scouting.
- Corp treasury — `corp_deposit`, `corp_withdraw`, `corp_memo` channel.
- Map one-way warp arrowheads + recent-warp directional trails.
- Combat flash + hail bubbles on the SVG map.
- Alignment rank tiers + XP (`RANK_TABLE`, `ALIGNMENT_TIERS`, `XP_AWARDS`) surfaced on player cards.

**Validation:** 25 pytest cases pass (`tests/test_engine.py` + `tests/test_phase_abc.py`), plus 35 checks in `scripts/smoke_phase_abc.py`, plus a 20k-step heuristic sanity match with no exceptions.

The tables below are kept for historical context; *status cells may now read stale*.

---

## 1. Universe & Navigation

| Feature | Original TW2002 | TW2K-AI | Status | Priority |
|---|---|---|---|---|
| Procedural sector graph (1k–20k) | yes | 1–~5k tested, default 1000 | ✅ | — |
| Deterministic seed | yes | yes (`GameConfig.seed`) | ✅ | — |
| Avg 2–3 warps/sector | yes | configurable, similar | ✅ | — |
| One-way warps (~15 %) | yes | yes (`_one_way_some_edges`) | ✅ | — |
| FedSpace 1–10 (no PvP) | yes | yes (constants + handlers) | ✅ | — |
| Stardock fixed sector | yes (sec 5454/1) | sector 1 | ✅ | — |
| Dead-end sectors | yes (often 1-warp loops) | possible incidentally | ⚠️ | P2 |
| Density Scanner / Holo Scanner | yes (long-range info) | basic `scan` (current+adjacent) | ⚠️ | P1 |
| Ether Probe (remote scout) | yes — drop probe, watch route | ❌ | ❌ | P1 |
| Computer Auto-plot route | yes (CIM-style course plot) | ❌ — agents must hop sector by sector | ❌ | **P0** |
| TransWarp Drive | yes — instant jump anywhere | ❌ (constant `hyperwarp` exists, unused) | 💤 | P1 |
| Avoid-list / personal map | yes | partial — `known_sectors` only | ⚠️ | P2 |
| Sector visualization (UI) | text in original | force-directed SVG map | ✅ | — |

**Why the P0:** without auto-plot, a 1000-sector universe is effectively a 5-warp neighbourhood. Agents will never explore. This is the single biggest reason their play looks repetitive.

---

## 2. Ports & Trade

| Feature | Original | TW2K-AI | Status | Priority |
|---|---|---|---|---|
| Class 1–8 + Federal | yes | yes (`PORT_CLASS_TRADES`) | ✅ | — |
| Per-commodity stock & cap | yes | yes | ✅ | — |
| Stock regeneration / day | yes | yes (`PORT_REGEN_PER_DAY`) | ✅ | — |
| Price curves vs stock % | yes | yes (`port_sell_price`/`port_buy_price`) | ✅ | — |
| Haggling (counter-offers) | yes — multi-round, port walks 50 % | one-shot bid; reject = list price | ⚠️ | P2 |
| Port experience effect on prices | yes | stored, **never read** | 💤 | P2 |
| **Port destruction** (atomic mine/photon) | yes | ❌ | ❌ | P1 |
| Port "BUST" rep system (smuggler tag) | yes | ❌ | ❌ | P3 |
| Port re-class over time | rare | ❌ | ❌ | P3 |
| StarDock services menu | yes | ships + equipment | ✅ | — |
| Hardware shop pricing tiers | yes | flat catalog | ⚠️ | P2 |

---

## 3. Commodities & Cargo

| Feature | Original | TW2K-AI | Status |
|---|---|---|---|
| Fuel Ore / Organics / Equipment | yes | yes | ✅ |
| Colonists | yes | enum exists; only useful for assigning to planets | ⚠️ (assign_colonists not wired) |
| Cargo holds (purchasable up to ship max) | yes | yes (`buy_equip` "holds") | ✅ |
| Holds-eject / pod | yes | ❌ | ❌ P3 |

---

## 4. Ships

| Feature | Original | TW2K-AI | Status | Priority |
|---|---|---|---|---|
| ~16 ship classes | yes | **10** classes | ⚠️ | P2 |
| Per-ship turns/warp | yes (varies 2–6) | constant 2 turns regardless | 💤 (`turns_per_warp` defined, unused) | **P0** |
| Trade-in 25 % at StarDock | yes | yes | ✅ | — |
| Corp-only ship gating | yes | yes (`corp_only`) | ✅ | — |
| Min-alignment gating | yes | yes (`min_alignment`) | ✅ | — |
| Unique ships (Imperial StarShip) | yes | flag exists; not enforced | ⚠️ | P2 |
| Genesis torpedoes (cargo) | yes | purchasable; **no action consumes** | 💤 | **P0** |
| Photon Missile (cargo) | yes — one-shot crit | ❌ | ❌ | P1 |
| Atomic detonator | yes | ❌ | ❌ | P1 |
| Ether Probes / Scout Drones | yes | ❌ | ❌ | P1 |
| Cloaking | yes (some ships) | ❌ | ❌ | P2 |
| TransWarp drive (built-in) | yes (some ships) | ❌ | ❌ | P1 |
| Self-destruct | yes | ❌ | ❌ | P3 |
| Ship destruction → escape pod | yes | yes (eject to StarDock, MC, –25 % cr) | ✅ | — |

---

## 5. Combat

| Feature | Original | TW2K-AI | Status | Priority |
|---|---|---|---|---|
| Ship-vs-ship in same sector | yes | yes (`attack` action) | ✅ | — |
| Fighter combat odds tables | yes (deterministic table) | 3-round abstract roll | ⚠️ | P1 |
| Shields absorb 1:1 | yes | yes | ✅ | — |
| FedSpace police response | yes (kills aggressor) | yes (`FED_RESPONSE`, alignment –200) | ✅ | — |
| **Photon Missile** | yes — disables fighters | ❌ | ❌ | P1 |
| Sector fighters auto-engage on warp-in | yes (offensive only) | yes | ✅ | — |
| Toll fighters (charge credits) | yes | yes | ✅ | — |
| Defensive fighters (passive) | yes | yes | ✅ | — |
| Limpet **tracks** carrier afterwards | yes | stored only, no tracking | 💤 | P1 |
| Player elimination (ship destroyed → out) | yes | **broken** — humans never set `alive=False` | ❌ | **P0** |
| Bounty on Ferrengi kills | yes | yes (`BOUNTY_PER_FERRENGI_KIL`) | ✅ | — |
| Fame / kill log | yes | event feed only | ⚠️ | P2 |

**P0 callout:** elimination victory is documented but unreachable. Pick a path: either (a) "ship destroyed = ejected, lose ship + cargo" (current) and remove elimination victory; or (b) treat third destruction in N days as elimination.

---

## 6. Mines

| Feature | Original | TW2K-AI | Status | Priority |
|---|---|---|---|---|
| Armid (damage on entry) | yes | yes | ✅ | — |
| Limpet (tracker) | yes | deployable, **no tracking logic** | ⚠️ | P1 |
| Atomic (destroy port/planet) | yes | ❌ | ❌ | P1 |
| Mine sweeping | yes (with mines, ETI scout) | ❌ | ❌ | P2 |
| Mine IFF (corp safe) | yes | partial — `attack` corp check yes; mines no | ⚠️ | P1 |

---

## 7. Sector Control / Fighters

| Feature | Original | TW2K-AI | Status |
|---|---|---|---|
| Defensive / Offensive / Toll modes | yes | yes | ✅ |
| Corp ally bypass | yes | yes | ✅ |
| Photon Disruptor counter | yes | ❌ | ❌ P2 |
| Sector ownership recorded | yes | only via deployment owner | ⚠️ P2 |
| Fed-Sector ban on deployment | yes | yes | ✅ |

---

## 8. Planets

| Feature | Original | TW2K-AI | Status | Priority |
|---|---|---|---|---|
| Planet types M/K/L/O/H/U/C with prod rates | yes | enum exists, prod uses flat colonist multiplier | ⚠️ | P1 |
| Land / Liftoff | yes | yes | ✅ | — |
| Claim if unowned | yes | yes | ✅ | — |
| Corp-shared planets | yes | yes (corp mate landing) | ✅ | — |
| **Genesis Torpedo creates planet** | yes — drops new planet in sector | ❌ — torpedoes purchasable, no action | ❌ | **P0** |
| **Build/upgrade Citadel L1–L6** | yes | enum exists, no handler | ❌ (`build_citadel` declared, returns "unsupported") | **P0** |
| **Assign colonists to F/O/E/Fighters** | yes | enum exists, no handler | ❌ (`assign_colonists` same) | **P0** |
| Citadel L2 Quasar Cannons (planet combat) | yes | ❌ | ❌ | P1 |
| Citadel L3 Atmosphere (faster growth) | yes | ❌ | ❌ | P2 |
| Citadel L4 Transporters (move goods) | yes | ❌ | ❌ | P1 |
| Citadel L5 Interdictor (block warps) | yes | ❌ | ❌ | P1 |
| Citadel L6 Planetary Defense Net | yes | ❌ | ❌ | P2 |
| Treasury (deposit / withdraw) | yes | model field, never updated | 💤 | P1 |
| Planet fighters / shields | yes | model fields, no combat use | 💤 | P1 |
| Planet siege / invasion | yes (drop colonists, blow citadel) | ❌ | ❌ | P1 |

**Planets are the biggest gap.** Without working planets the late-game has no spectacle, and corp value collapses.

---

## 9. Corporations

| Feature | Original | TW2K-AI | Status |
|---|---|---|---|
| Create at StarDock (cost) | yes | yes (500k cr) | ✅ |
| Member cap (3) | yes | configurable | ✅ |
| Invite / Join / Leave | yes | yes | ✅ |
| Shared planets/sectors | yes | landing only | ⚠️ |
| Corp treasury (shared funds) | yes | model field, **never used** | 💤 P1 |
| Corp memos / log | yes | only via broadcast/hail | ⚠️ P2 |
| CEO transfer / dissolve | yes | leave dissolves if empty; no transfer | ⚠️ P2 |
| Disband on betrayal | manual | n/a | — |
| Corporate FlagShip | yes | gated by `corp_only` flag | ✅ |

---

## 10. Aliens & NPCs

| Feature | Original | TW2K-AI | Status | Priority |
|---|---|---|---|---|
| Ferrengi pirates spawn | yes | yes | ✅ | — |
| **Ferrengi roam / hunt** | yes (move & attack) | ❌ — they sit | ❌ | **P0** |
| Ferrengi flee weak | yes | ❌ | ❌ | P1 |
| Cabal (rare apex predator) | yes | ❌ | ❌ | P2 |
| Alien races (Ferrengi/Cabal/Marauders) | yes | only Ferrengi | ⚠️ | P2 |
| Alien diplomacy | minimal in original | n/a | ✂️ | — |

Static Ferrengi rob the game of mid-game tension. Even simple "wander 1 sector/day, attack any non-corp player in same sector" would change the dynamic.

---

## 11. Communication & Diplomacy

| Feature | Original | TW2K-AI | Status |
|---|---|---|---|
| Hail individual | yes | yes | ✅ |
| Sub-space broadcast | yes | yes | ✅ |
| Inbox | yes | yes (per-player `inbox`) | ✅ |
| Real-time chat | yes (BBS multi-node) | ✂️ (LLM agents async) | n/a |
| Corp memo channel | yes | use broadcast | ⚠️ P2 |
| Bulletin board / news | yes | ❌ | ❌ P3 |
| **Formal alliance / NAP** | not formalized in original; emergent | emergent only — agents must police themselves | ⚠️ P1 |

For an LLM exhibition, a lightweight "alliance" record (with a structured `propose_alliance` / `accept` / `break` action that the engine actually tracks) would be high spectator value: alliances on the screen, drama when they break.

---

## 12. Player Progression

| Feature | Original | TW2K-AI | Status | Priority |
|---|---|---|---|---|
| Alignment (good/evil ±) | yes | yes (PvP-in-Fed penalty) | ⚠️ shallow | P2 |
| Experience points | yes | ❌ | ❌ | P2 |
| Rank tiers (Civilian → Imperial) | yes | ❌ | ❌ | P2 |
| Net worth tracking | yes | yes | ✅ | — |
| Death penalty | yes (lose ship + cargo) | yes | ✅ | — |
| Permadeath option | tournament games | ❌ | ❌ | P1 (toggleable) |

---

## 13. Victory Conditions

| Feature | Original | TW2K-AI | Status |
|---|---|---|---|
| Highest net worth at game end | yes (tournament) | yes | ✅ |
| Economic threshold (`100M`) | yes | yes (scales with `max_days`) | ✅ |
| Last player standing | yes | declared, **unreachable** (humans never die) | ❌ **P0** |
| Sector-domination % | hinted | constant defined, **never used** | 💤 P1 |
| Corp-domination | yes | ❌ | ❌ P1 |

---

## 14. Spectator UI (we are *ahead* of original here)

| Feature | Original (text) | TW2K-AI | Status |
|---|---|---|---|
| Galaxy map | text CIM dump | live SVG, pan/zoom, color | ✅ |
| Event feed | scrolling text | filterable real-time | ✅ |
| Player cards | text status | rich cards, cargo legend | ✅ (just added) |
| Transmissions panel | terminal text | dedicated panel | ✅ |
| Pause/speed/restart | n/a | yes | ✅ |
| **Replay scrubber** | n/a | partial — `/events?since=` exists, no UI | ⚠️ P2 |
| Map shows directed warps | n/a | renders as undirected | ⚠️ P2 |
| Combat animation / flash | n/a | none | ❌ P2 |
| Ship-to-ship comm overlay (hail bubbles) | n/a | none | ❌ P2 |
| Per-player route trail | n/a | recent-warp highlight only | ⚠️ P2 |

---

## 15. Misc original-game systems

| Feature | Original | TW2K-AI | Notes |
|---|---|---|---|
| Online multiplayer (BBS) | yes | ✂️ | replaced by LLM agents |
| Daily reset clock (real time) | yes | per-day tick | ✅ |
| Logbook / replay | partial | event feed | ✅ |
| Trade Wars Editor | yes | ❌ | ✂️ out of scope |

---

# Recommended Roadmap to "Full-Featured"

I'd group the work into **3 tightly scoped phases**, each shippable independently. Each phase ends with a playable demo and a smoke test.

### Phase A — "Make the late game exist" (~the core gap)
1. **Wire `assign_colonists`** — colonists work F/O/E or fighters; planet stockpile fills daily.
2. **Wire `build_citadel`** — L1–L6 with cost & day-build timer; observation exposes treasury+stockpile+citadel.
3. **Wire genesis torpedo action** — consume from `ship.genesis`, create planet in current sector.
4. **Player elimination fix** — destroyed ship after Nth death = `alive=False`; elimination victory becomes reachable.
5. **Per-ship `turns_per_warp`** — make the actual constant the source of truth (already defined!).
6. **Ferrengi roam & hunt** — simple `move_ferrengi` step in day tick; attack player in same sector.

### Phase B — "Make the universe usable & dramatic"
7. **Computer auto-plot route** — new `plot_course(target)` action: agent supplies a destination, engine returns warp path; warp action accepts a multi-step path consuming turns.
8. **Photon missile + atomic mine** — the spectator-spec'd "OH SHIT" actions.
9. **Limpet tracking** — fighter-owner can `query_limpets` to see where their tagged ship is.
10. **Citadel combat** (L2 Quasar Cannons, L5 Interdictor) — landing on a defended planet is now risky.
11. **Replay scrubber UI** — slider over event seq, snap to event of interest.

### Phase C — "Polish & parity"
12. Formal `propose_alliance` / `break_alliance` action with engine-tracked state and UI badges.
13. Density / Holo / Ether-probe scan tiers.
14. Corp treasury, corp memos channel.
15. Map: render one-way warps with arrowheads.
16. Combat flash + hail-bubble animations.
17. Alignment-driven port discounts; rank tiers.
18. Optional permadeath / tournament toggles in `GameConfig`.

---

# Quick wins (could land today)

These are <50-line changes that give big returns:

- **Per-ship `turns_per_warp`** — already in constants, just consume it. (1-line fix in `runner.py:_handle_warp`.)
- **Limpet expiration / tracker query in observation** — at minimum, expose "your limpets are in sectors X, Y" so the action becomes meaningful.
- **Ferrengi 1-step random walk per day** — adds movement without full AI.
- **Render one-way warps** — change SVG line to arrowed marker when reverse warp absent.
- **Expose planet `treasury`, `stockpile`, `shields` in `observation.py`** — agents can already see citadel level; let them see the rest.
- **Map directional arrows** in `web/app.js` so spectators see the one-way trap topology that already exists in the engine.

---

# What we should *not* try to clone

- BBS multi-node real-time chat — replaced by LLM observation/inbox.
- Trade Wars Editor — modding tool, not a game feature.
- Online registration / SysOp config — irrelevant for AI exhibition.
- ANSI text UI — superseded by web spectator.

---

**Bottom line:** mechanically we're at maybe **55–60 %** of vintage TW2002. The economy, port classes, fighter sector control, corps, and Ferrengi *spawning* are solid. The missing 40 % is concentrated in **planets/citadels, long-range navigation, dramatic special weapons, NPC AI, and elimination**. Phase A alone closes the most painful spectator gaps.
