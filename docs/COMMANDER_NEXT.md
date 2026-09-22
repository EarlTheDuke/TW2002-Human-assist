# COMMANDER_NEXT - Complete cockpit + multi-bot parity

## State
- **machine_state:** `WAITING_COMMANDER`
- **phase:** `parity-s1`
- **updated_at:** `2026-09-21T19:06:00-07:00`
- **updated_by:** `Fable`

## Active task
**id:** `parity-s1-server-data`
**title:** S1 — server data + fog fixes (peek, event stream, spectator gate, xAI gate, webhook deadline)
**instructions:**
(idle - waiting on Commander ACK)

**S1 delivered** (7 commits, tip `5065a4f`, pushed). All seven done-when items met; details in `docs/GROK_CURSOR_HANDOFF.md` 19:05 PT entry.

Quick verify from the box (token from `.tw2k/external_tokens.json`, base from `.tw2k/public_base_url.txt` - re-exposed, `/bot` 200):
- `GET {base}/harness/v1/P3/observation?peek=1` -> `peek:true`, full fogged Observation while WAITING
- `GET {base}/harness/v1/P3/events?since=0` -> `{events[{seq,kind,summary,facts}], next_since, latest_seq}`
- `GET {base}/state` -> **401** (spectator gate ON); Ben's one-click link is in `.tw2k/spectator_link.txt` (swap the tunnel base if remote)
- `python scripts/play_grok_external_seats.py` -> exit 2 + banner

:8031 was restarted on S1 code (P1/P2 Qwen + P3 external, 120 turns/day, idle-wait 8 s). Ready for S2 when queued.

## Queue
_S2 read-only cockpit tapes (peek-powered) after S1 ACK._

## Ben messages (rare)
_Spectator now needs a token on the hosted URL: open the link in `.tw2k\spectator_link.txt` once (sets a cookie). Nothing else needed._
