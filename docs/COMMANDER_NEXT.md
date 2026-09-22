# COMMANDER_NEXT - Complete cockpit + multi-bot parity

## State
- **machine_state:** `WAITING_COMMANDER`
- **phase:** `parity-s2`
- **updated_at:** `2026-09-21T19:23:00-07:00`
- **updated_by:** `Fable`

## Active task
**id:** `parity-s2-readonly-tapes`
**title:** S2 — read-only cockpit tapes on `/bot` (peek-powered)
**instructions:**
(idle - waiting on Commander ACK)

**S2 delivered** (`d6f13d2`, pushed). All four done-when items met; details in `docs/GROK_CURSOR_HANDOFF.md` 19:22 PT entry.

Verify from the box: **re-read `.tw2k/public_base_url.txt`** (tunnel was re-created; a watchdog now re-exposes automatically and rewrites that file), open `{base}/bot?seat=P3`, paste the P3 token. Panels fill immediately while WAITING (peek). Check: port tape shows BUYS/SELLS + price + stock per commodity; Known ports table shows per-sector B/S prices; last result is an English sentence; Events footer lists fogged events with filters. `python -m pytest -q` -> 503 passed.

## Queue
_S3 legality + core verbs after S2 ACK._

## Ben messages (rare)
_Spectator still needs the one-click link in `.tw2k\spectator_link.txt` (swap tunnel base if remote)._
