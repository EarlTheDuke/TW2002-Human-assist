# COMMANDER_NEXT - Complete cockpit + multi-bot parity

## State
- **machine_state:** `WAITING_COMMANDER`
- **phase:** `parity-s5`
- **updated_at:** `2026-09-21T20:42:00-07:00`
- **updated_by:** `Fable`

## Active task
**id:** `parity-s5-known-map`
**title:** S5 — known-space map on /bot
**instructions:**
(idle - waiting on Commander ACK)

**S5 delivered** (tip `dc3291b`, pushed). Done-when met: a human sees where they are in known space and plots a course by tapping a known sector - proven in the browser (1-hop and 3-hop autopilot from map taps, zero rejects). Fog tests: `known_sectors` = exactly visited/scanned/probed/current, coords only for those, no coords in the LLM message. F5 copilot route leak fixed (BFS over `known_warps`). 539 tests green, ruff clean. Details in `docs/GROK_CURSOR_HANDOFF.md` 20:41 PT entry.

:8031 restarted on S5; tunnel healthy (200). Re-read `.tw2k/public_base_url.txt` if it changes.

## Queue
_S6 multi-bot ops + Path-B reference client, or S7 polish/a11y - Commander's call._

## Ben messages (rare)
_Spectator still needs the one-click link in `.tw2k\spectator_link.txt` (swap tunnel base if remote). Re-read `.tw2k\public_base_url.txt` after tunnel watchdog re-exposes._
