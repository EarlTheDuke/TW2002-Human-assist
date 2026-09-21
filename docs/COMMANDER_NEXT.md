# COMMANDER_NEXT — AFK task mailbox

Cursor: read this file at every loop iteration.
Commander: overwrite **Active task** when advancing phases. Do not ask Ben.

## State
- **machine_state:** `COMPLETE`
- **phase:** `2`
- **updated_at:** `2026-09-20T22:16:00-07:00`
- **updated_by:** `Commander`
- **stop_when:** `machine_state` is `COMPLETE` or `BLOCKED_NEEDS_BEN`

## Active task (do this now)
**id:** `afk-complete`
**title:** AFK build complete — exit cleanly
**instructions:**
Phase 2 acceptance met. machine_state is COMPLETE. Cursor: exit the AFK loop cleanly (no further phases queued). Optional Phase 3 polish (WS / spectator EXTERNAL badge / cost n/a / MCP list seats) is deferred — not required for success.

## Queue (Commander fills when advancing)
_Empty — COMPLETE._

## Ben messages (rare)
_AFK external-harness build finished. Branch `feature/grok-bot-harness` @ `e1fa90b`. See handoff Changelog._
