# COMMANDER_NEXT — competitive seat bot (fogged observation)

## State
- **machine_state:** `WAITING_COMMANDER`
- **phase:** `seat-bot-competitive`
- **updated_at:** `2026-09-25T16:05:00-07:00`
- **updated_by:** `Fable`
- **blocker:** none

## Active task
**id:** `seat-bot-competitive-s4`
**title:** Seat-only acceptance harness
**instructions:**
(idle - S4 delivered, waiting on Commander review / S5 queue)

## Delivered (S4)
- **Commit:** `7a9813d`. Pushed to `feature/seat-bot-competitive` (continues PR #1: https://github.com/EarlTheDuke/TW2002-Human-assist/pull/1) and `feature/grok-bot-harness`.
- **Files:**
  - `src/tw2k/agents/seat_acceptance.py` (new, seat-only):
    - `validate_action(obs, action)` judges an action ONLY against that observation's own `legal_actions`: legal flag, required args per verb, values inside `choices`, `qty` positive and within `max_by`/`max`, and `plot_course` `execute` true.
    - `MilestoneTracker` / `Report` track genesis_bought → genesis_deployed → landed_genesis → citadel_started → colonists_bought → ferry_home → colonists_assigned, plus completed ferry trips.
    - `replay(brain, payloads)` runs recorded mailbox payloads through a brain.
    - `synthetic_obs(...)`, `STORYBOARD` and `ferry_storyboard()` provide hand-built fogged observations with consistent envelopes.
  - `scripts/seat_brain_acceptance.py` (new CLI): `synthetic`, `record` (an offline engine run where the brain sees only `build_observation(u, seat)`; writes mailbox-format JSONL), and `replay` (a fresh brain plus the validator; exit 0 only if there are no errors and the empire loop completed).
  - `scripts/seat_brain_v2.py`: new `--record FILE` tees every live mailbox payload to JSONL, so real matches can be replayed offline.
  - `tests/test_seat_bot_s4.py` (new, 9 tests).
- **Tests:** 9 new; full suite **581 passed** (was 572); S3 still 8/8; ruff clean.
  - Storyboards (15 steps): the brain emits the expected action at every step, valid per the envelope, and hits all 7 milestones in order.
  - Validator negatives: missing `planet_id` / `qty`, qty 0 and over-cap, `planet_id` outside choices, plot missing or false `execute`, an illegal verb, and a warp target outside choices.
  - Grid sweep: >200 synthetic states (sector × planets incl. a claimed neutral × colonists × genesis × credits × landed). The brain never violates the envelope and never assigns colonists to a claimed neutral.
  - Record → replay: a 2-day offline recording has 0 engine rejections. A fresh brain replays it to identical milestones and ferry count with 0 validation errors.
  - HTTP end-to-end: the brain plays P1 over `/harness/v1` in an in-process match vs a heuristic seat, reaching all milestones and 2+ ferry trips with 0 failed/stale submits. **Request-path audit:** traffic is limited to `/harness/v1/rules`, `/P1/observation`, `/P1/action` and `/P1/status`, with no `/state`, `/seats`, or other seat.

## How to run the harness
```powershell
$env:PYTHONUTF8="1"
python -m pytest tests/test_seat_bot_s4.py -q                      # 9 passed
python scripts/seat_brain_acceptance.py synthetic                  # storyboards, no engine
python scripts/seat_brain_acceptance.py record --out $env:TEMP\seat_trace.jsonl --days 3
python scripts/seat_brain_acceptance.py replay $env:TEMP\seat_trace.jsonl
# live trace for replay later:  python scripts/commander_p4_brain.py --record docs/playtests/<match>/p4_trace.jsonl
```
Sample 3-day record/replay: 689 turns, 0 errors, empire_loop_ok, genesis bought at turn 1, first colonists assigned at turn 97, 62 ferry trips. Traces are ~10 MB/day, so none is committed; tests record into a temp dir.

## Not done (out of scope / optional)
- Optional live 3×Kimi match: not run. The live-trace tee (`--record`) is in place for when it is.

## AFK standing orders
- Ben AFK until seat-bot S5 COMPLETE. Commander auto-queues S4 then S5 on each `WAITING_COMMANDER`.
- Follow-up templates: `docs/COMMANDER_FOLLOWUPS_SEAT_BOT.md`
- After finishing Active task: set `WAITING_COMMANDER` with Delivered; do not wait for Ben paste between slices.

## Open Cursor options
1. ~~S1 observation colonists / origin~~ (PR #1 ACK)
2. ~~S2 progress-based stall detector~~ (PR #1 ACK)
3. ~~S3 goal-driven seat brain~~ (`205bb10` ACK)
4. ~~S4 seat-only acceptance harness~~ (`7a9813d`, awaiting review)
5. S5 docs
