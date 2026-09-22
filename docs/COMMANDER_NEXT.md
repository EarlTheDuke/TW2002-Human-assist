# COMMANDER_NEXT - Complete cockpit + multi-bot parity

## State
- **machine_state:** `WAITING_COMMANDER`
- **phase:** `parity-s3`
- **updated_at:** `2026-09-21T19:59:00-07:00`
- **updated_by:** `Fable`

## Active task
**id:** `parity-s3-legality-verbs`
**title:** S3 - legal_actions() + core verb pad on /bot
**instructions:**
(idle - waiting on Commander ACK)

**S3 delivered** (tip `138a6fe`, pushed). All done-when items met: matrix test (8 states x 8 precise verbs, `legal == apply_action.ok`), disabled buttons carry `data-reason`, browser buy -> warp -> sell with haggle from the UI with zero precondition rejects, 515 tests green, ruff clean. Details in `docs/GROK_CURSOR_HANDOFF.md` 19:58 PT entry.

Notable: the UI exposed a real observation bug - Federal ports were labelled `sells_to_player` though the engine refuses trades there; fixed (`side=not_traded`). :8031 restarted on S3 code (the new pad needs `legal_actions`); tunnel healthy; **re-read `.tw2k/public_base_url.txt`**.

## Queue
_S4 full verb groups (StarDock, combat, planets, comms, corp) after S3 ACK - promote their `legal_actions` entries from coarse to precise one group at a time._

## Ben messages (rare)
_Spectator still needs the one-click link in `.tw2k\spectator_link.txt` (swap tunnel base if remote). Re-read `.tw2k\public_base_url.txt` after tunnel watchdog re-exposes._
