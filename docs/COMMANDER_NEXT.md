# COMMANDER_NEXT — competitive seat bot (fogged observation)

## State
- **machine_state:** `WAITING_COMMANDER`
- **phase:** `seat-bot-competitive`
- **updated_at:** `2026-09-24T22:40:00-07:00`
- **updated_by:** `Fable`
- **blocker:** none

## Active task
**id:** `seat-bot-competitive-s3`
**title:** Goal-driven seat brain (replace brittle Path-B ladder)
**instructions:**
(idle - S3 delivered, waiting on Commander review / S4 queue)

## Delivered (S3)
- **Commit:** `205bb10`. Pushed to `feature/seat-bot-competitive` (continues PR #1: https://github.com/EarlTheDuke/TW2002-Human-assist/pull/1) and `feature/grok-bot-harness`.
- **Files:**
  - `src/tw2k/agents/seat_brain.py` (new): `SeatBrain.decide(observation) -> action`, a pure decision function over the seat's own observation.
  - `scripts/seat_brain_v2.py` (new): runner. Mailbox mode by default; `--harness` drives the seat directly; optional `--log-dir` writes `turns.jsonl`.
  - `scripts/commander_p4_brain.py`: now a thin wrapper (seat P4, mailbox mode). The old 733-line ladder is kept locally as `scripts/commander_p4_brain_legacy.py` (not committed; it never was).
  - `tests/test_seat_bot_s3.py` (new, 8 tests).
  - `docs/plans/2026-09-24-seat-bot-competitive.md` (committed so the PR carries its spec).
- **Tests:** 8 new; full suite **572 passed** (was 564); ruff clean.
- **What the brain does** (the ladder's first legal rung wins):
  1. Landed on a genesis world: assign colonists aboard (with `planet_id` + `qty`), then build the citadel, then stock unsellable goods on the planet, then lift off. On a claimed neutral it just lifts off.
  2. Genesis aboard: deploy when `deploy_genesis` is legal. Otherwise read the reason ("FedSpace" / "too close") and carry the torpedo deeper.
  3. At a genesis world with colonists aboard or a buildable citadel: land.
  4. At StarDock: buy a CargoTran, then a genesis (the first once L1 money remains, a second when rich), then colonists (only what the next tier still needs, never below the reserve).
  5. Travel: ferry home, build on another genesis world whose citadel is buildable now, stock goods at home, or go to StarDock.
  6. Explore until StarDock is known; otherwise earn with the envelope trade heuristic plus a route planner over **remembered** ports and known warps.
- **How it stays out of loops:** `StallDetector` (S2) judges progress toward the declared intent. When stalled, the brain takes a 3-turn exploration break. There is no target-alternation guard.
- **Memory:** home planet and deploy sector persist via `scratchpad_update`, so a restarted brain resumes where it left off. It also writes `goal_*`.
- **Seat-only:** a test greps `seat_brain.py` and `seat_brain_v2.py` for `/state`, `universe`, `players[` and the old ping-pong names.

## How to run the offline proof
```powershell
$env:PYTHONUTF8="1"
python -m pytest tests/test_seat_bot_s3.py -q        # 8 passed
```
The key test is `test_offline_genesis_citadel_ferry_from_observation_only`. The real engine runs, but the brain only ever sees `build_observation(universe, "P1")`. The test asserts:
- order CargoTran → genesis → deploy → land → build, then colonists bought → assigned;
- zero engine rejections;
- the home citadel reaches ≥L2 by day 6, and every genesis world has a citadel started;
- ≥2 ferry trips, and ≤2 stall breaks;
- required args on every assign, land, build and plot.

Sweep across 6 seeds and 20k–120k starting credits (6 days, solo): 0 rejections everywhere, 0–2 stall breaks. First genesis landed on day 1 in the sampled runs. Home citadels reached L3 by day 6 from 60k+ credits, and 245k–449k net worth from 40k+. The 20k–30k starts trade their way to their first genesis world and L1.

## Live use (not run this slice; S4 covers the live match)
```powershell
python scripts/grokbot_seat_client.py --seat P4 --policy mailbox      # harness <-> mailbox
python scripts/commander_p4_brain.py --log-dir docs/playtests/<match> # brain (SeatBrain on P4)
```

## Engine finding for Commander (not changed; S3 is brain-only)
`plot_course` is reported legal even when the seat cannot pay for the first hop. The autopilot then returns ok with "0/N hops" and charges no turns, which is a free infinite loop for any seat. The brain now plots only when `warp` is legal. Engine options for later: gate `plot_course` execute on turns in `legal_actions`, or return ok=False when `hops_done == 0`.

## AFK standing orders
- Ben AFK until seat-bot S5 COMPLETE. Commander auto-queues S4 then S5 on each `WAITING_COMMANDER`.
- Follow-up templates: `docs/COMMANDER_FOLLOWUPS_SEAT_BOT.md`
- After finishing Active task: set `WAITING_COMMANDER` with Delivered; do not wait for Ben paste between slices.

## Open Cursor options
1. ~~S1 observation colonists / origin~~ (PR #1 ACK)
2. ~~S2 progress-based stall detector~~ (PR #1 ACK)
3. ~~S3 goal-driven seat brain~~ (`205bb10`, awaiting review)
4. S4 seat-only acceptance harness
5. S5 docs
