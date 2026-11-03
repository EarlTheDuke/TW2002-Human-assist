# Fable plan: `/bot` as the complete TW2K cockpit + multi-Grok-Bot parity

**Author:** Fable (Cursor), written from code before reading Commander's plan; §H compares the two.
**Date:** 2026-09-21 PT · **Status:** planning only, no game-code changes.
**Branch for build slices:** `feature/grok-bot-harness` (or a child branch per slice).

Ben's direction, restated as the constraints every slice must satisfy:

1. `/bot` becomes a complete human game interface, not a debug panel.
2. 2–3 Grok Bots compete with the **same fogged Observation, memory, rules text and legal verbs** TinyBox LLM seats get. No xAI API brain; one Grok Bot brain per seat.
3. `/bot` renders authoritative `Observation` + event data. It never derives game truth itself.
4. Computer-use and accessibility are first class: text for everything, stable DOM + `data-testid`, nothing blocks a turn.
5. Immersive media (stills / short clips) is a deferred wish list; the presentation boundary is designed now so media plugs in later without touching engine or turn flow.

---

## 0. What the code actually says (findings that shape the plan)

I read `web/bot.*`, `engine/observation.py`, `engine/actions.py`, `engine/models.py` (EventKind, fog tables), `agents/prompts.py::format_observation`, `server/harness.py`, `server/app.py`, `web/play.js`, `copilot/dashboards.py`, the Phase-C insights, hosting/connector docs and the scripts. Findings, most consequential first:

| # | Finding | Consequence for the plan |
|---|---|---|
| F1 | **An external seat can only fetch its Observation while `awaiting_input`** (`harness.py` returns `observation: null` otherwise; the runner clears `current_observation` when `act()` returns). LLM seats are the same, but a *human* stares at the screen between turns. | Add a read-only **peek** (`build_observation` on demand for your own seat). Fog-safe: it is the seat's own view. Without this a "complete cockpit" is impossible. |
| F2 | `Observation.recent_events` is capped (40 in the model, 12 in the LLM message) and **`_event_to_dict` drops the payload** — only `summary` text survives. | The cockpit's history view, and any future media layer, need a **fogged event stream with a seq cursor** and a **per-kind whitelisted payload** (`facts`). This is the event/presentation boundary Ben asked for, and it must be defined server-side once, not guessed in JS. |
| F3 | **Legality lives only inside runner handlers** (imperative `if … return ActionResult(ok=False)`) plus prose in `action_hint`. Nothing structured says "which verbs are legal right now and why not". | To gate buttons honestly (Ben's rule 3) we need an engine **query** `legal_actions(universe, pid)` — pure, like `build_observation` — surfaced in the Observation so LLM seats get it too (parity, and it retires a chunk of `action_hint` prose over time). The UI must not re-implement preconditions. |
| F4 | `web/play.js` (the `/play` human cockpit for `HumanAgent`) already has forms for **warp, scan, probe, trade buy/sell, wait, land, liftoff, hail, broadcast**, keyboard shortcuts, and an economy panel. It runs on a different transport (`/api/human/*`, no token, no `turn_seq`, LAN only) and is welded to the LLM copilot. | Two cockpits is the wrong end state. Port `/play`'s **presentation pieces** onto the harness transport; do not rebuild them. Long term, `HumanAgent` should become an `ExternalAgent` with `kind="human"` so one cockpit serves humans and bots. Copilot stays optional and out of this build. |
| F5 | **Fog leak:** `copilot/dashboards.py::build_route_table` BFS-es the **true universe graph** (`universe.sectors[cur].warps`, including sectors the player never saw) and reads **live** port prices/stock for known ports instead of the player's remembered snapshot. Served only to `/play` today. | Do **not** reuse it for `/bot` as-is. A cockpit route/heatmap panel must run on `known_warps` + `known_ports` snapshots (client-side is fine — it is presentation over remembered facts). Fix or quarantine the copilot version. |
| F6 | **Fog leak by adjacency:** `/`, `/state`, `/events`, `/history`, `/highlights` are unauthenticated and show the whole galaxy, every ship, every thought. On a hosted URL a competitor (human or bot) can open the spectator. | Hosted mode needs a spectator gate (`TW2K_SPECTATOR_TOKEN`, or bind spectator to a separate loopback-only port). Not a UI task, but it is the biggest fairness hole in the current hosting story. |
| F7 | `scripts/play_grok_external_seats.py` drives P4/P5 with **`api.x.ai`** (`XAI_API_KEY`). It is committed (I swept it in with Commander's Phase A files). | Violates "no xAI brain". Remove it or gate behind an explicit `--allow-xai-fallback` with a loud banner and `actor` note. Fairness claims are hollow while it exists. |
| F8 | `ExternalAgent._fire_turn_due_webhook` computes `deadline_at` from `TW2K_EXTERNAL_TIMEOUT_S` (default 180) rather than `MatchSpec.external_timeout_s`, and ignores the idle-wait rule. | Small correctness fix when wiring Path-B bots; otherwise a bot will think it has 180 s when the runner gives it 8. |
| F9 | `Sector.x/y` layout coordinates exist (`universe._compute_layout`) but are not in the Observation. `known_warps` is a pure adjacency list. | A drawn known-space map needs either coordinates for **known sectors only** (fog-safe: you cannot infer unknown sectors' positions from your own) or a client-side layout. Prefer server coords for stability across sessions; expose only for `known_sectors`. |
| F10 | `format_observation` (what LLM seats read) is a **subset** of `Observation` (drops `limpets_owned`, `probe_log`, trims lists). `/bot` gets the full object. | Parity direction is fine (humans may see everything the model *could* see) as long as we never add fields to `Observation` that `format_observation` cannot also ship. Any new field (legal_actions, known_sector coords) is added to both or documented as UI-only presentation data. |
| F11 | `/bot` today (after Phase D): banner + countdown, 6 stats, port `buys/sells` names only, `action_hint`, warp chips, SCAN/WAIT, "sell all port buys"/"buy first sell", `last_result` JSON, log; long-poll, stable warp DOM, `data-testid`s. | It is a good **turn-taking shell**. Everything below the banner needs to be replaced by Observation-driven panels. |

---

## A. Exact gap: `/bot` vs Observation + `/rules` + 34 verbs

### A1. Observation fields → what `/bot` shows

| Observation field | In `/bot` now | Needed by a competitive human |
|---|---|---|
| `day tick max_days finished` | day/tick | + days remaining, match status |
| `self_id/name credits turns_remaining turns_per_day` | yes | + turn cost per verb (from `TURN_COST`) |
| `net_worth alignment alignment_label experience rank deaths max_deaths alive` | **no** | scoreboard strip |
| `ship.{class holds cargo cargo_free}` | class, free | full cargo table |
| `ship.{cargo_cost_avg cargo_value_at_cost}` | no | break-even per commodity next to cargo |
| `ship.{fighters fighter_cap shields shield_cap mines genesis photon_missiles ether_probes photon_disabled_ticks}` | **no** | combat/loadout panel; drives which verbs make sense |
| `sector.{id warps_out warps_count is_fedspace}` | id, warps as buttons | + FedSpace badge, dead-end marker |
| `sector.port.{code name class_id buys sells}` | code + names | + `stock{current,max,price,side}` per commodity (prices are the game) |
| `sector.{occupants fighter_group mines ferrengi planets}` | **no** | who/what is here; gates attack/land/claim |
| `adjacent[]` | **no** (only ids) | one-hop strip: port code, fighters, planets, occupants, known |
| `known_ports[]` (+ `age_days`) | **no** | the port memory table; core of trading |
| `known_warps{}` | **no** | the map |
| `trade_log[] trade_summary` | **no** | P&L, haggle win rate, best/worst pair |
| `recent_failures[]` | **no** | "stop retrying" panel |
| `owned_planets[] orphaned_planets[]` | **no** | planet roster; gates planet verbs |
| `other_players[] rivals[]` | rivals as one line | leaderboard with fogged last-seen |
| `inbox[]` | **no** | comms; unread badge; reply |
| `alliances[] corp` | **no** | diplomacy panel |
| `limpets_owned[] probe_log[]` | **no** | intel panel |
| `scratchpad goals{}` | **no** | the human's own notes, same storage as bots |
| `operator_directive operator_dialogue` | **no** | n/a for external seats (LLM-only feature) |
| `recent_events[]` | **no** | event log (fogged, summaries) |
| `action_hint` | raw prose | keep, but demote to an "advisor" drawer once panels exist |

### A2. Rules and verbs

`GET /rules` gives `system_prompt`, `verbs` (34), `action_schema`. `/bot` uses none of it. Verb coverage today: **warp, scan, wait, trade (2 fixed shapes)** = 4 of 34, and the trade shapes cannot haggle (`unit_price`) or pick a quantity.

Verbs by context (this grouping drives the UI in §B):

| Context (when the group is visible) | Verbs |
|---|---|
| Always | `warp` `scan` `wait` `plot_course` `hail` `broadcast` |
| At a trading port | `trade` (buy/sell, qty, haggle) |
| At StarDock (sector 1) | `buy_ship` `buy_equip` `corp_create` `corp_invite` `corp_join` `corp_leave` |
| Others / Ferrengi in sector | `attack` `photon_missile` `propose_alliance` `accept_alliance` `break_alliance` |
| Outside FedSpace, in space | `deploy_fighters` `deploy_mines` `deploy_atomic` `deploy_genesis` |
| Planets in sector / landed | `land_planet` `liftoff` `claim_planet` `assign_colonists` `load_planet_cargo` `dump_planet_cargo` `build_citadel` |
| Owns intel items | `probe` (probes) `query_limpets` (limpets) |
| In a corp | `corp_deposit` `corp_withdraw` `corp_memo` |

---

## B. Complete human cockpit — information architecture

Design rule: **every panel is a pure function of `(observation, events, rules, seat_status)`**. No panel keeps game state; the only client state is UI state (which tab, draft form values, notes not yet submitted).

```
┌──────────────────────────────────────────────────────────────────────────┐
│ HEADER   Turn banner (YOUR TURN / WAITING · who · countdown)   Seat chip │
│          Day 3 of 15 · Turns 57/120 · Credits 19,317 · NW 41k · Rank    │
├───────────────┬──────────────────────────────────────┬───────────────────┤
│ LEFT: WHERE   │ CENTER: ACT                          │ RIGHT: KNOW       │
│ • Here        │ • Context verb pad (legal only)      │ • Known ports     │
│   sector,     │   groups per §A2, disabled+reason    │   (sortable, age) │
│   port tape,  │ • Form for the chosen verb           │ • Trade P&L       │
│   occupants,  │   (qty/price/target pickers fed      │ • Planets         │
│   planets,    │    from Observation, never free      │ • Rivals          │
│   fighters,   │    text for ids)                     │ • Comms / inbox   │
│   mines,      │ • Confirm → POST {turn_seq, action}  │ • Diplomacy       │
│   ferrengi    │ • Last result in English + JSON      │ • Intel (probes,  │
│ • Adjacent    │   drawer                             │   limpets)        │
│   strip       │ • Advisor drawer (action_hint,       │ • Notes (goals +  │
│ • Known-space │   recent_failures)                   │   scratchpad)     │
│   map (SVG)   │                                      │                   │
├───────────────┴──────────────────────────────────────┴───────────────────┤
│ FOOTER   Event log (fogged, English, filter by kind) · Raw obs drawer    │
└──────────────────────────────────────────────────────────────────────────┘
```

Mobile: the three columns become tabs **Where / Act / Know** with the header and footer persistent; the verb pad stays reachable in one tap.

### B1. Context-sensitive action flows (each is one screen, ≤3 inputs, preview before POST)

| Flow | Inputs | Preview line (client arithmetic on displayed numbers — presentation, not rules) | POST |
|---|---|---|---|
| Warp | tap adjacent chip | "2 turns · sector 68 · port SBB · 1 fighter group (P1)" | `warp{target}` |
| Plot course | pick target from known sectors (map click or list) | hop count over **known_warps** only; "unknown route" if none | `plot_course{target, execute:true}` |
| Trade | commodity radio (only sides this port trades) · qty slider (max = holds free / cargo, affordability) · optional price | "Sell 20 fuel_ore @ 27 = 540 cr (cost basis 21 → +120)" | `trade{commodity,qty,side,unit_price?}` |
| Scan / Probe | none / target sector | "1 turn" / "5,000 cr, 1 probe left" | `scan{}` / `probe{target}` |
| StarDock | ship list with price, holds, cap, trade-in; equipment grid with unit price and cap headroom | "CargoTran 43,500 − trade-in 8,250 = 35,250" | `buy_ship{ship_class}` / `buy_equip{item,qty}` |
| Combat | target chip (occupant/Ferrengi) | "5 turns · you 620 fighters vs 400" | `attack{target}` / `photon_missile{target}` |
| Deploy | qty + mode/kind | "leaves 420 fighters aboard" | `deploy_fighters` / `deploy_mines` / `deploy_atomic` |
| Planet | planet chip → land; when landed: colonist pools, stockpile, next citadel tier (`citadel_next_build` already precomputed) | "L2 needs 1,000 colonists (have 750)" | `land_planet` `liftoff` `claim_planet` `assign_colonists` `load/dump_planet_cargo` `build_citadel` `deploy_genesis` |
| Comms | recipient chip (rivals) + message | — | `hail` / `broadcast` / `corp_memo` |
| Diplomacy / Corp | target chip, terms/ticker | — | alliance / corp verbs |
| Notes | goals (3 fields) + scratchpad | attached to the **next** submitted action as `goal_*` / `scratchpad_update` | rides on any action |

Every verb button shows **disabled + reason** when illegal (from §C3 `legal_actions`), never hidden, so a human learns the rules and a bot can read the reason.

### B2. Human needs checklist (Ben's list D)

- **Known-space map:** SVG of `known_sectors` (coords server-side, §F9) + `known_warps` edges (arrowheads for one-way when reverse is unknown), port code badge, "you are here", owned planets, last-seen rivals; unknown neighbours drawn as dashed stubs. Click → plot-course target. Zoom/pan; keyboard focusable list twin for screen readers.
- **Economy:** cargo table with cost basis; port tape with price/stock/side; known-ports table sortable by age/price; P&L summary; route suggestions **computed client-side from known_ports snapshots and known_warps** (see F5).
- **Events/history:** fogged stream, English `summary`, grouped by day, filter chips (trade / move / combat / comms / system), "since your last turn" divider, `data-testid="event-<seq>"`.
- **Keyboard:** 1–9 warp by position, S scan, W wait, T trade, P plot, Enter confirm, Esc cancel, `?` help; all focus-visible.
- **Mobile:** tabs, 64 px targets already, sticky banner and confirm bar.
- **Accessibility:** `role="status"` banner (done), `aria-live` on last result, every icon has text, `prefers-reduced-motion` respected (flash → static), high-contrast tokens already in `bot.css`.

---

## C. 2–3 Grok Bot attachment model

### C1. One brain per seat, three transports, same facts

| Transport | Decides from | Acts via | Fit |
|---|---|---|---|
| **Harness (Path B)** | `GET observation?wait_s=…&format=both` + `GET /rules` once | `POST action` with `turn_seq` | Competitive default. Exactly what an LLM seat sees. |
| **Webhook wake** | `turn_due` POST (already in `ExternalAgent`) carrying the Observation | harness POST | AFK bots; needs F8 fix; payload should also carry `base_url` and `deadline_at` from the spec. |
| **Computer use (Path A)** | what `/bot` renders | clicks | UX proof + humans. After §B, `/bot` shows the same fields, so a CU bot is information-equal but latency-poor. |

A seat's token is its identity; the harness already refuses cross-seat use (403) and strips `actor_kind`. Three bots = three tokens = three processes/agents. **Never** one CU browser session driving three seats; the scheduler is serial and each seat's countdown is wall-clock.

### C2. No idle-seat stalls (already shipped, keep)

`external_idle_wait_s` (attended vs unattended by harness traffic) + `-ExternalSeats` defaulting to the seats that actually have bots. Path-B bots are attended by definition (they long-poll). CU bots are attended while the `/bot` tab polls. Add to the guide: a bot that stops polling for 45 s is treated as absent and auto-WAITs after 8 s.

### C3. Legal actions as data (engine query, parity for everyone)

`engine/legality.py::legal_actions(universe, player_id) -> list[LegalAction]` where `LegalAction = {kind, legal: bool, reason: str|None, params: {name: {type, choices?|min?|max?}}}`. Pure, deterministic, no mutation; built from the same constants the handlers use (`TURN_COST`, `SHIP_SPECS`, StarDock sector, planet ownership, cargo/holds, credits). It does **not** replace handler validation — the engine still rejects — it only reports. Surface as `Observation.legal_actions` (so LLM seats gain it too and `action_hint` can shrink) and therefore automatically through the harness. Tests assert `legal_actions[...].legal == apply_action(...).ok` on a fixture matrix so the query and the handlers cannot drift.

### C4. Fairness ledger (what each seat kind gets)

| | LLM (TinyBox) | Grok Bot harness | Grok Bot CU / human `/bot` |
|---|---|---|---|
| Observation | `format_observation` subset | full `Observation` (superset) | rendered full `Observation` |
| Rules | system prompt every turn | `/rules` once | Help drawer from `/rules` |
| Legality | prose `action_hint` → `legal_actions` (C3) | same | buttons gated by same data |
| Memory | server (`known_*`, `scratchpad`, goals) | same | same, drawn |
| Think time | `llm_think_cap_s` | `external_timeout_s` | same |
| Extra tooling | none | none | none (no server-side recommender beyond `action_hint`) |

---

## D. (Folded into §B2 above; the checklist there is the acceptance surface for the human-cockpit slices.)

---

## E. Future immersive media — the contract we design now, build later

**Boundary:** engine → `Event` (kind, actor, sector, payload) → **fogged `EventView`** (`_event_to_dict` + per-kind `facts` whitelist, server) → **`present(eventView)`** (client presentation layer) → `{text, tone, icon, testid, media?: {key, kind: still|clip, caption, durationMs, skippable:true}}`.

Rules baked into the boundary:

1. **Semantic keys, not assets.** The server never names files. `present()` maps `kind` + `facts` (e.g. `warp` + `facts.one_way`, `combat` + `facts.outcome`) to a `media.key`; an **asset manifest** (`web/assets/manifest.json`, theme packs later) maps keys to files. Missing asset → text only, silently.
2. **Media never gates the turn.** The banner, countdown, verb pad and POST path live in the header/act column and are updated by the status loop; media renders in the event log / a dismissible stage area. Turn state never waits on `ended` events.
3. **Skippable, captioned, reduced-motion.** Every clip has `summary` as caption, an instant skip control with `data-testid="media-skip"`, respects `prefers-reduced-motion` (clip → still → text), user setting "media: off / stills / clips" in `localStorage`, default **off** for CU sessions (detect `?cu=1` or setting).
4. **No game logic in media.** `present()` is a pure mapping; it may not read or write anything but the `EventView` and the manifest. Test: run `present()` over a recorded `events.jsonl` and assert output has text for every event and never throws.
5. **Performance.** Lazy-load, cap concurrent media to one, preload only the next likely key (e.g. `warp` when the warp pad is open), total budget configurable; stills first, clips later.
6. **Fog stays server-side.** The whitelist in F2 is the only place payload leaves the engine; media cannot be smarter than the whitelist.

Deferred deliverables (not this build): manifest format, first still set (ports by class, StarDock, planet classes, ship classes, Ferrengi), first clip set (warp, dock, combat, genesis, citadel complete, destruction, day rollover, victory), ambience/sound behind an opt-in.

---

## F. Slices (small, buildable, each with tests and a done-when)

Ordering principle: unblock the cockpit's data first (server), then render (read-only), then act (gated verbs), then bots, then polish. Each slice is one PR-sized change on the branch with pytest + a `/bot` browser check.

| Slice | Scope | Acceptance tests | Done when |
|---|---|---|---|
| **S1 Peek + event stream + fog fixes (server)** | `GET /harness/v1/{pid}/observation?peek=1` returns `build_observation` for your seat any time (rate-limit 2/s). `GET /harness/v1/{pid}/events?since=<seq>&limit=200` returns fogged `EventView`s via `_filter_visible_events` with `facts` whitelist (start with warp/trade/combat/hail/broadcast/day_tick/game_over/land/genesis/citadel). F8 webhook deadline fix. F7 xAI script removed or gated. `TW2K_SPECTATOR_TOKEN` gate on `/`,`/state`,`/events`,`/history`,`/highlights`,`/ws` when set (F6). | peek works when not awaiting; events endpoint never returns an event `_event_visible_to` rejects (property test over a recorded match for each seat); no `_witnesses` or non-whitelisted payload keys; spectator 401 with token set. | A human at `/bot` can read their ship/port/map between turns, and a competitor cannot read the galaxy from `/`. |
| **S2 Read-only tapes on `/bot`** | Replace stats block with §B panels **Where** (here + port tape with prices + adjacent strip) and **Know** (cargo w/ cost basis, known ports table, trade P&L, recent failures, rivals, inbox read-only, planets, intel). English `last_result`; JSON in a drawer. Event log from S1 stream with filters. Uses peek so panels fill immediately after Connect. | Jest-free: pytest renders `bot.html` through the route and asserts `data-testid`s exist; Playwright-less browser check documented; snapshot test that every Observation top-level key has a home in the DOM (`data-obs="<key>"`). | A human answers "what can I sell here at what price, and which known port buys it" without the harness. |
| **S3 `legal_actions` (engine query) + verb pad** | `engine/legality.py`, `Observation.legal_actions`, `format_observation` ships it (LLM parity). `/bot` context verb pad per §A2 with disabled+reason; forms for warp / plot_course / trade (qty+haggle) / scan / probe / wait. | Matrix test: for each fixture state and verb, `legal_actions[kind].legal == apply_action(...).ok`; UI test that disabled buttons carry `data-reason`. | CU bot completes buy → warp → sell with a haggle price from the UI; no button ever POSTs an action the engine rejects for a *precondition* reason (haggle rejections excepted). |
| **S4 StarDock / combat / deploy / planets / comms / corp forms** | Remaining verb groups from §B1 using the `/play` form patterns ported to harness transport. Notes panel writes `goal_*` + `scratchpad_update` onto the next action. | Each form has a fixture-driven test that its POST body validates against `Action.model_json_schema()` and matches handler arg names (`target`, `planet_id`, `item`, `from/to`, `execute`). | Every one of the 34 verbs is reachable from `/bot` in its context; `/play`'s verb coverage is a subset of `/bot`'s. |
| **S5 Known-space map** | `Observation.known_sectors: [{id,x,y,port,last_seen_day}]` (coords only for known sectors; `format_observation` ships ids only). SVG map + list twin; click → plot target; one-way arrows from `known_warps` asymmetry. Client-side route suggestions from snapshots (replaces F5 use). | Fog test: coords present only for `player.known_sectors`; route panel never references a sector outside `known_warps`. | Human plots a 3-hop course to a remembered port by clicking the map. |
| **S6 Multi-bot ops** | Reference Path-B client hardened (`external_client_example.py` → `grokbot_seat_client.py`: `/rules` once, `format=both`, deadline-aware, `scratchpad_update`), one process per seat; webhook payload uses spec timeout; seat lobby on `/bot` (chips from `/seats`, whose turn across seats, token per seat kept in `localStorage` per seat id); `run_hosted_grokbot.ps1 -ExternalSeats P3,P4,P5` doc'd as "only when three bots are attached". | 3 external seats + 2 heuristic in CI: two scripted Path-B clients + one unattended → match completes N turns with zero external timeouts for attended seats, idle WAITs only for the unattended one. | Three Grok Bot processes take turns in one hosted match; a human watches their own seat at `/bot` without stalling anyone. |
| **S7 Polish & a11y** | Keyboard map, mobile tabs, reduced-motion, help drawer from `/rules`, `present()` boundary in code (text-only implementation) with manifest stub. | axe-style checks via a small pytest that greps for `aria-live`, focusable controls, no hover-only; `present()` over `events.jsonl` never throws. | Ben can play a full day on a phone; CU bot completes 20 turns with zero mis-clicks. |

**First implementation slice after merge: S1.** It is server-only, unblocks everything else, closes two real fog leaks, and needs no UI taste decisions from Commander. S2 follows immediately and is where `/bot` visibly becomes a cockpit.

---

## G. Risks

| Risk | Where it bites | Mitigation |
|---|---|---|
| Fog leak through spectator routes on a public URL | `/`, `/state`, `/events`, `/ws` today | S1 spectator token; hosting docs say "never share the spectator URL with a competitor"; consider binding spectator to loopback only in hosted mode. |
| Fog leak through helper code | `build_route_table` true-graph BFS + live prices | Quarantine to `/play`; cockpit computes from snapshots (S5). |
| `/bot` becomes a second engine | verb gating, previews, route math | Gating from `legal_actions` (engine); previews are arithmetic on displayed numbers only and labelled "estimate"; engine result always wins; no rule constants duplicated in JS (fetch `TURN_COST`/prices via `/rules` extension if needed). |
| API vs CU fairness | CU seats pay screenshot latency and lossy reading | State it: CU is the human/UX path; competitive bots use Path B. Same timeout for all. |
| xAI leakage into "Grok Bot" seats | `play_grok_external_seats.py` | Remove/gate (S1). `actor_kind` stays `external`; add an `AgentSpec.brain_label` (free text, e.g. "grok-bot:commander") stamped into `GAME_START` so replays show who drove each seat. |
| Token isolation | one tokens file, three bots on one box | Per-seat env, per-seat process; `/seats` lists masked; rotate after public sessions; never in `meta.json` (tested). |
| Tunnel hosting | lhr.life forward dies on long origin outages; CF 403s CU browsers; URL churn | Runbook already; long-term Tailscale (needs Ben once); expose script `-Stop/-Detach`. |
| Three bots, one desktop | CU contention | Path B for extra seats; one CU browser max per desktop. |
| Observation growth hurts LLM seats | adding `legal_actions`, `known_sectors` | `format_observation` ships compact forms (legal kinds only; sector ids only); size budget test (<8 KB mid-day). |
| Webhook payload carries the whole Observation off-box | Path B webhooks | Send `turn_seq` + `base_url` only; bot pulls observation with its token. |

---

## H. Proposed canonical merged outline + explicit disagreements with Commander's plan

I read Commander's plan after drafting §0–G. We agree on the north star, "one Observation object", legal-only verbs, one brain per seat, Path B as the competitive default, and the media guardrails. The differences below are where the code says something Commander's plan does not cover or assumes.

### H1. Disagreements / additions

| # | Commander's plan | Fable's position | Why (code) |
|---|---|---|---|
| D1 | E1 assumes `/bot` can render the Observation | **Not between turns** — harness returns `observation: null` unless awaiting. Needs the S1 **peek** first. | `harness.py` observation route; `ExternalAgent.act` finally-block clears `current_observation`. |
| D2 | "Event log in English" in E3, sourced implicitly from `recent_events` | Needs a **fogged event endpoint with seq cursor and whitelisted `facts`**; `recent_events` is 40 summaries max and only inside an Observation. This is also the media boundary Ben asked for, so it belongs in slice 1, not E3. | `_event_to_dict` drops payload; `event_history=40`. |
| D3 | "Only legal verbs light up (same preconditions the engine already enforces)" | The engine does not *expose* preconditions. Add `legal_actions()` engine query and put it on the Observation (LLM parity too). Otherwise the UI must re-implement rules = second engine. | Preconditions are inline in `runner.py::_handle_*`; only prose reaches the Observation. |
| D4 | Known-space "sketch"; "known_warps count / simple list" in E1 | Ship **coordinates for known sectors** and draw a real map (S5). A list is not a map for a human. Fog-safe because unknown sectors get no coords. | `Sector.x/y` exist; layout is deterministic per seed. |
| D5 | "Notes field local to the browser" | Use `scratchpad_update` / `goal_*` on the next action so human memory lives **where bot memory lives** (parity, survives browser). Local draft only until submitted. | `Action` already carries these; `Observation` returns them. |
| D6 | "Human 'recommend move' button: top-3 legal actions scored by a tiny heuristic" | **Do not add a server-side recommender.** `action_hint` already exists for all seats; a human-only scorer is an asymmetric assist and a second brain. Show `action_hint` + `legal_actions` instead. | Fairness ledger §C4. |
| D7 | Not mentioned | **Spectator leak** (`/`, `/state`, `/ws` unauthenticated) is the largest fairness hole on a hosted URL. Gate it in S1. | `app.py` routes; `_init_payload` sends every sector. |
| D8 | Not mentioned | `copilot/dashboards.build_route_table` leaks true graph + live prices. Do not reuse for `/bot`. | `_bfs_hops(universe…)`, `port_sell_price(port…)` on live port. |
| D9 | Not mentioned | `play_grok_external_seats.py` uses xAI for P4/P5 — contradicts the mission; remove or gate. | script header. |
| D10 | Not mentioned; `/play` ignored | Reuse `/play`'s verb forms and economy UI patterns on the harness transport; plan to fold `HumanAgent` into `ExternalAgent(kind=human)` later so there is **one cockpit**. | `play.js` has 10 verb forms + keyboard + economy already. |
| D11 | Webhook wake as-is | Fix deadline source (spec, idle rule) and send `turn_seq`+`base_url` rather than the full Observation. | `external.py::_fire_turn_due_webhook`. |
| D12 | E5 "feed `system_prompt` once per match" | Agree; add `format=both` guidance and `deadline_at` budgeting to the reference client, and keep the client in-repo as the canonical Path-B bot (`grokbot_seat_client.py`). | `external_client_example.py` exists but is a toy policy. |
| D13 | Phases E1→E5 ordered UI-first | Server data slice first (S1) so UI slices don't stub or fake anything. | F1–F3. |

Agreements worth stating so the merge keeps them: Path A/B split; no 34-verb dump (context groups); English first, JSON in a drawer; idle-WAIT default; Tailscale long-term; media deferred with the guardrails; "render Observation only".

### H2. Proposed canonical merged outline (`docs/plans/2026-09-21-bot-human-parity.md`)

1. North star + constraints (Ben's five points) + fairness ledger (§C4).
2. Code findings F1–F11 (shared truth; both plans cite them).
3. Gap tables (§A1, §A2).
4. Cockpit IA (§B) + context flows (§B1) + human checklist (§B2).
5. Bot attachment model (§C1–C3), one brain per seat, idle rule.
6. Presentation/media boundary contract (§E) — deferred deliverables listed.
7. Slices: **S1 server data + fog fixes → S2 read-only tapes (= Commander E1) → S3 legality + core verbs (= E2 part 1) → S4 all verb groups (= E2 part 2) → S5 map (= E3 map) → S6 multi-bot ops + Path-B client (= E4+E5) → S7 polish/a11y (= E3 rest)**; each with acceptance tests and done-when.
8. Risks (§G) incl. D7–D9.
9. First queued task: **S1**.

---

## Appendix — verification I ran while planning (no code changed)

- `/bot` post-Phase-D reviewed in browser (turn flip, countdown, stable DOM) — see 17:15 PT Changelog.
- Harness `observation` returns `observation: null` when `awaiting_input` is false (route code, `harness.py`).
- `EventKind` has 58 kinds; fog tables cover public / actor-only / hail / corp / alliance; default rule is witness-list.
- `/play` verb forms: warp, scan, probe, trade×2, wait, land_planet, liftoff, hail, broadcast (`play.js` L454–544).
- `Observation` has 44 fields (`Observation.model_fields`); `/bot` renders 8 of them. `ActionKind` has 34 verbs, matching `/rules`.
