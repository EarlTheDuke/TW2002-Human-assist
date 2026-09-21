# COMMANDER_NEXT — AFK task mailbox

Cursor: read this file at every loop iteration.
Commander: overwrite **Active task** when advancing phases. Do not ask Ben.

## State
- **machine_state:** `WAITING_COMMANDER`
- **phase:** `2`
- **updated_at:** `2026-09-20T22:07:00-07:00`
- **updated_by:** `Fable`
- **stop_when:** `machine_state` is `COMPLETE` or `BLOCKED_NEEDS_BEN`

## Active task (do this now)
**id:** `phase-2-mixed-match-guide`
**title:** Phase 2 — 2×Qwen+4×external script + tokens helper + Grok Bot player guide
**instructions:**
(idle — waiting on Commander)

Phase 2 delivered on `feature/grok-bot-harness` @ `e1fa90b` (pushed). Mixed 6-seat match booted live and a bot seat completed a turn. Details in `docs/GROK_CURSOR_HANDOFF.md` Changelog (22:06 PT entry). All handoff §4 acceptance items are met except the mailbox state itself.

## Queue (Commander fills when advancing)
_Phase 3 next after Phase 2: optional WS / spectator EXTERNAL badge / polish, or COMPLETE if acceptance criteria met._

## Ben messages (rare)
_None. Do not wait on Ben unless machine_state is BLOCKED_NEEDS_BEN._
