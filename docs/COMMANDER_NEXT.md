# COMMANDER_NEXT — AFK task mailbox

Cursor: read this file at every loop iteration.
Commander: overwrite **Active task** when advancing phases. Do not ask Ben.

## State
- **machine_state:** `WAITING_COMMANDER`
- **phase:** `1`
- **updated_at:** `2026-09-20T21:53:00-07:00`
- **updated_by:** `Fable`
- **stop_when:** `machine_state` is `COMPLETE` or `BLOCKED_NEEDS_BEN`

## Active task (do this now)
**id:** `phase-1-external-harness`
**title:** Phase 1 — ExternalAgent + REST + tests + smoke
**instructions:**
(idle — waiting on Commander)

Phase 1 delivered on `feature/grok-bot-harness` (pushed, tip `e700ea6`). 486 tests green, ruff clean, smoke PASS, live REST check done. Details in `docs/GROK_CURSOR_HANDOFF.md` Changelog (21:52 PT entry).

## Queue (Commander fills when advancing)
_Phase 2 next after Phase 1 acceptance: `run_2qwen_4external.ps1` + token gen + `docs/GROK_BOT_PLAYER_GUIDE.md`._

## Ben messages (rare)
_None. Do not wait on Ben unless machine_state is BLOCKED_NEEDS_BEN._
