# COMMANDER_NEXT - Complete cockpit + multi-bot parity

## State
- **machine_state:** `WAITING_COMMANDER`
- **phase:** `parity-s4`
- **updated_at:** `2026-09-21T20:24:00-07:00`
- **updated_by:** `Fable`

## Active task
**id:** `parity-s4-verb-groups`
**title:** S4 - full context verb groups on /bot
**instructions:**
(idle - waiting on Commander ACK)

**S4 delivered** (tip `c62d2e9`, pushed). All five done-when items met: all 34 verbs `precise` (19 fixtures × 34 verbs match `apply_action`), forms/pads for every promoted verb in four context groups (disabled + `data-reason` everywhere), Observation + `format_observation` legality intact, S2 `data-obs` coverage holds, 535 tests green, ruff clean, browser proof of **three** groups (comms, StarDock, combat) with zero precondition rejects. Details in `docs/GROK_CURSOR_HANDOFF.md` 20:23 PT entry.

Engine finding worth knowing: `deploy_atomic` is not in the engine dispatch table (always "unsupported action"); atomics go through `deploy_mines kind=atomic`. Reported as never-legal with that reason.

:8031 restarted on S4; watchdog re-exposed the tunnel; **re-read `.tw2k/public_base_url.txt`**.

## Queue
_S5 known-space map after S4 ACK._

## Ben messages (rare)
_Spectator still needs the one-click link in `.tw2k\spectator_link.txt` (swap tunnel base if remote). Re-read `.tw2k\public_base_url.txt` after tunnel watchdog re-exposes._
