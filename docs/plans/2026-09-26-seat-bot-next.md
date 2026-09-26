# Seat bot — next plan after the qwen2-kimi3-grok playtest (2026-09-26)

Status: **AUTHORITATIVE for N1–N5** (Ben wrote; Commander absorbed into master
`docs/plans/2026-09-24-seat-bot-competitive.md`). Live qwen2-kimi3-grok match **stopped mid-match**
day ~3 / tick ~773 (2026-09-26 morning PT): Ben chose **option A** (documented failure) + stop;
proceed **N1–N5 offline**. Options B/C closed for this match. Not yet queued in `COMMANDER_NEXT.md`
mailbox — Ben decides when to queue Cursor. Source evidence: match
`docs/playtests/multibot-2026-09-25-qwen2-kimi3-grok/` (seed 250925, 6 seats, 120 turns/day,
100k start), P6 `turns.jsonl`, and offline replays of the SAME seed/spawn with the current brain.

## Cursor / cloud-agent handoff (pointers only; intent unchanged)

| Field | Value |
|-------|--------|
| Master plan | `docs/plans/2026-09-24-seat-bot-competitive.md` (S1–S6 delivered; N1–N5 next) |
| This plan | N1–N5 detail + acceptance ("Done when") — **do not contradict** |
| Branch / starting_ref | `feature/seat-bot-competitive` tip ≡ `feature/grok-bot-harness` @ `93b8069` (prefer clean tip; VENGEANCE tree may be dirty with unrelated work) |
| Hard ban | No `/state` / spectator into seat brain; no live rematch until N1–N3 offline proofs |
| Live match | **Decided:** A + stop mid-match (day ~3 / tick ~773, 2026-09-26 morning PT); failure case; N1–N5 offline. B/C closed for this match. |

**Implement slices in order N1→N5.** Each slice needs offline A/B proof across several maps before live. Acceptance tests are the **Done when** lines under each Ni section (N1: StarDock day 1 @ 100k and 20k + day-1 trade @ 20k + ABA≤2/100; N2: no organics starve + NW beat on ≥4/5 seeds; N3: ferry<40% + day-10 NW≥400k on 250925; N4: SHA/mtime in turns + live_summary.json + plot_course first-hop legality; N5: recorded rematch + offline trace replay).

Primary code paths: `src/tw2k/agents/seat_brain.py`, `scripts/seat_brain_v2.py`, `src/tw2k/engine/legality.py` (plot_course), `src/tw2k/engine/observation.py` / `planets.py` (N2 fields), `scripts/seat_brain_acceptance.py` + `src/tw2k/agents/seat_acceptance.py` (record/replay).

## What actually happened (verified)

1. **The live P6 brain is running old code.** `seat_brain_v2.py` (pid 32164) started
   2026-09-25 17:46 PT. The S6 commit that autopilots to StarDock when holding genesis money
   (`e8c2f18`) landed at 21:13 PT. Python loaded the S3-era modules once, so the live seat has
   no StarDock autopilot.
2. **S3-era rule "explore until StarDock is known" is fatal on big maps.** P6 spawned in sector 6
   (FedSpace), but on seed 250925 FedSpace is NOT clustered around StarDock: sector 1's warps are
   44/452/493 and the shortest route from sector 6 is 8 warps (6→132→264→110→589→401→534→452→1).
   Greedy "prefer unvisited neighbour" exploration covered 96 sectors in 120 warps, got within
   2 hops once (turn 74), and was never adjacent. 120/120 actions were `warp`; credits stayed at
   100,585.
3. **Current code fixes that on this exact seed.** Offline replay from sector 6 with 100k:
   `plot_course 1` on turn 1, CargoTran turn 2, genesis deployed turn 7, citadel turn 9 (all day 1),
   0 engine rejections. The engine's `plot_course` routes over the real warp graph; it is a legal
   verb every seat has (QwenB's own scratchpad: "Path to StarDock: 831->273->452->1").
4. **But a poor seat is still stuck.** Same replay with 20k credits: 3 days, zero trades, zero
   progress — the "find StarDock" rung sits above "earn", and the autopilot only fires with genesis
   money.
5. **And the fixed brain's economy is weak.** 10-day replay: 1,050 of ~1,200 turns spent ferrying
   colonists, 10 trades (+2.4k), net worth 224k on day 4 → 261k on day 10 (≈ +6k/day). QwenB was
   already 222.8k on day 3; the Kimi3 match winner finished at 427k.

## Why the economy stalls (engine rules, `planets.py` / `victory.py`)

- Net worth counts colonists at 10 cr, citadels at their full cost (credits + colonists consumed),
  hulls at **50%** resale, fighters at full StarDock price. Buying colonists, ferrying them, or
  building a citadel is ~net-worth-neutral when it happens.
- What actually grows net worth: **trade profit**, **5%/day colonist growth** (only while the
  planet's organics stockpile > 0; consumption = colonists/100 per day), **production** into the
  stockpile (colonists in a pool × class coefficient / 100), and the **30% tax payout** on each
  day's planet value gain.
- The brain assigns pools with a flat "20% organics" rule that ignores planet class. In the replay
  planet 32 is class **U** (organics coefficient 1): its organics stockpile hit 0 on day 6 and growth
  stopped. The M-class world kept growing ~5%/day.
- Building citadel L2 on day 3 burned 2,000 colonists — the whole growth base of that world
  (1,875 → 75). Neutral on paper that day, but it forfeits the compounding growth + tax.

## Corrections to the Commander status report

- "Prefer paths toward FedSpace / use ether probes": would not help — FedSpace is not adjacent to
  StarDock on this map, and probes cost 5k each when `plot_course 1` is free to plan. The fix is
  to route, not to search.
- "Treat repeated visits as hard taboo sooner": the ABA bounces are real (16), but several were
  forced dead ends (e.g. 861 has one warp). Frontier-directed exploration fixes both.
- `live_summary.json` is stale because `seat_brain_v2.py` never writes it (only `turns.jsonl`);
  the old commander_p4 brain did.
- Status data came from spectator `/state`: fine for operator monitoring, must never feed the seat
  brain (it doesn't).

## Decision for the live match (DECIDED 2026-09-26 morning PT)

**Ben chose A + stop mid-match.** Match halted day ~3 / tick ~773 (2026-09-26 morning PT). Leave as
documented failure case (valid experiment: "S3 brain cannot leave explore mode on a large map").
Proceed **N1–N5 offline**. Do not restart host or brain for this match.

Closed for this match (record only; do not act):
- **B.** Restart only the P6 brain process (not the host) with current code — would have labeled
  remainder "S6 brain from day 3".
- **C.** Finish this match, then rerun the same seed after N1–N3 below for a clean comparison.

## Plan (small slices, each with offline A/B proof before any live match)

### N1 — Route instead of search (critical, ~small)
- Remove the "explore until StarDock known" gate. When the ladder needs StarDock, `plot_course 1`
  (execute) regardless of whether sector 1 is in memory; fall back to exploration only if the
  engine rejects the plot (S6 failure bans already handle that).
- Poor seats: `earn` before StarDock (trade known ports); go to StarDock when a CargoTran or a
  genesis is affordable.
- Exploration, when needed: frontier-directed — plot through known warps to the nearest known
  sector with an unvisited neighbour, instead of greedy local warps (kills ABA / revisit bias).
- Done when: seed 250925 from sector 6 reaches StarDock on day 1 at both 100k and 20k; a
  20k seat makes trade profit on day 1; ABA bounces ≤ 2 per 100 turns in replays.

### N2 — Growth-aware colony management (high)
- Observation (owner-only, fog-safe): add per owned planet `production` per pool, organics
  consumption/day, `growth_active`, `organics_days_left` (derived from class coefficients the
  engine already uses) so brains and LLMs stop guessing.
- Brain: size the organics pool from the class coefficient; when `organics_days_left` < 2, buy
  cheap organics and dump them on the planet (`dump_planet_cargo`) — 75 organics ≈ 1.4k cr keeps a
  3k-colonist world growing ~150 colonists/day.
- Citadel policy: do not burn the growth base early. Build the next tier only if colonists after
  the build stay above a floor (e.g. ≥ the tier cost), or in the last ~2 days (citadels count at
  full cost at the end). A/B this against the current policy before adopting.
- Done when: no owned world's organics stockpile hits 0 in a 10-day replay; day-10 net worth
  beats the current brain on ≥ 4 of 5 seeds.

### N3 — Value-per-turn allocator (high)
- Replace fixed rung priority for post-genesis play with a small estimate per option:
  trade route (profit / turns), ferry (only when it unlocks a planned tier or refills a starving
  world), genesis #N (25k + expected growth), organics resupply, sell planet stockpile
  (`load_planet_cargo` → port).
- Raise `target_planets` above 2 when affordable; genesis is net-worth-neutral on purchase and
  every world compounds.
- Done when: turns spent ferrying < 40% in 10-day replays and day-10 net worth ≥ 400k on seed
  250925 solo (Kimi3 winner benchmark was 427k).

### N4 — Ops hygiene (medium, quick)
- `seat_brain_v2.py`: print git SHA + module mtime at start and in every `turns.jsonl` row; write
  `live_summary.json` (day, sector, credits, NW, goals, planets, last action, stall/replan counts)
  every decision.
- Runbook: after any brain commit, restart the brain process only; verify the SHA line.
- Engine: `plot_course execute` legality should reflect "first hop affordable" (today it returns
  ok with 0 hops and costs nothing — the brain guards it, other seats don't).

### N5 — Live validation
- Same lineup, same seed (or a fresh seed + seed 250925), brain at N1–N4 tip, `--record` trace on.
  Compare P6 vs LLM seats by day; write playtest notes; replay the trace offline with the S4 harness.

## Out of scope
- `/bot` polish, xAI brains, god-state coaching, economy rule changes (except the `plot_course`
  legality bug, which is a correctness fix).
