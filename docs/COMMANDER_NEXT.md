# COMMANDER_NEXT — competitive seat bot (fogged observation)

## State
- **machine_state:** `WAITING_COMMANDER`
- **phase:** `seat-bot-competitive`
- **updated_at:** `2026-09-24T18:40:00-07:00`
- **updated_by:** `Fable`
- **blocker:** none

## Active task
**id:** `seat-bot-competitive-s1`
**title:** Observation parity + competitive seat brain (fogged only)
**instructions:**
(idle - waiting on Commander review)

**S1 + S2 ready for review:** https://github.com/EarlTheDuke/TW2002-Human-assist/pull/1
(head `feature/seat-bot-competitive` @ `557b780`, base `review/seat-bot-base` = pre-S1 tip, so the diff is only these slices; same commits are on `feature/grok-bot-harness`).

- S1: `owned_planets[]` now has `origin` (genesis|claim|other), `colonists` (per pool), `colonists_total`, `stockpile`; prompt drift fixed (`assign_colonists` needs `planet_id`+`qty`; genesis 3-hop rule).
- S2: `src/tw2k/agents/stall.py` progress-based stall detector (not yet wired into a brain; S3 consumes it).
- Tests: `tests/test_seat_bot_s1.py` (9), `tests/test_seat_bot_s2.py` (11); full suite 564 passed; ruff clean.

Verify: `python -m pytest tests/test_seat_bot_s1.py tests/test_seat_bot_s2.py -q`

Note: a running `:8031` server must be restarted to serve the new `owned_planets` fields.

## Open Cursor options
1. ~~S1 observation colonists / origin~~ (PR #1)
2. ~~S2 progress-based stall detector~~ (PR #1)
3. S3 goal-driven seat brain (next after ACK)
4. S4 seat-only acceptance harness
