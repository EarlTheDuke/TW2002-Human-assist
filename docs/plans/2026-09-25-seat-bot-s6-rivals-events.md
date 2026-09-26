# Seat-bot S6 — rivals / events / orphans mid-game pivots (2026-09-25)

## Goal
Extend the fogged SeatBrain so it actually consumes `rivals`, `recent_events` / `recent_failures`, and `orphaned_planets` for mid-game pivots — without god `/state` and without breaking the S3 goal ladder (explore → CargoTran → genesis → citadel → ferry).

## Why
Match `multibot-2026-09-25-qwen2-kimi3-grok`: Path-B P6 leads early NW only because cash is unspent while still mapping for StarDock. LLM seats use rivals/events more aggressively. Gap list from Commander (2026-09-25): SeatBrain under-uses rivals, orphaned_planets, rich recent_events, and flexible mid-game pivots.

## Non-goals
- S5 docs (separate; may still be queued)
- S7 /bot polish
- God-state coaching
- Live match mid-patch unless crash

## Deliverable
1. Teach `src/tw2k/agents/seat_brain.py` (and thin wrappers) to read:
   - `rivals` — race pressure (if trailing a rival with citadel/early genesis signal in fogged public fields, prefer genesis/citadel rungs sooner when legal)
   - `recent_events` / `recent_failures` — on repeated self-failures, change plan (no blind retry)
   - `orphaned_planets` — when genesis path blocked/slow and a true orphan is claimable per legal_actions, consider `claim_planet` only when landed on a listed orphan
2. Keep StallDetector + required args + fogged-only rules.
3. Tests: unit/offline cases proving (a) rival pressure changes priority when legal, (b) repeated failure avoids same illegal retry, (c) orphan claim only when observation lists orphan + legal.
4. Continue `feature/seat-bot-competitive` / PR #1. No secrets in commits.

## Done when
- pytest green for new S6 tests + prior seat-bot tests
- Mailbox `WAITING_COMMANDER` with Delivered SHA/files/how-to-run
