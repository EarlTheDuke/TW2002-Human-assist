# COMMANDER_NEXT - Complete cockpit + multi-bot parity

## State
- **machine_state:** `WAITING_COMMANDER`
- **phase:** `parity-s6`
- **updated_at:** `2026-09-21T21:11:00-07:00`
- **updated_by:** `Fable`

## Active task
**id:** `parity-s6-multibot-pathb`
**title:** S6 — Multi-bot ops + Path-B reference client
**instructions:**
(idle - waiting on Commander ACK)

**S6 delivered** (tip `d854820`, pushed). Done-when met: 2 Path-B seats ran competitively (same fogged Observation + `/rules` as LLM seats) 10/10 ok each with zero stale/fallback while an unattended sibling idle-WAITed; webhook `turn_due` verified lean with runner deadline; lobby chips on `/bot`; `/seats` fog leak (sibling `sector_id`) fixed. 544 tests green, ruff clean. Details in `docs/GROK_CURSOR_HANDOFF.md` 21:10 PT entry.

**Verify from the box** (`:8031` now hosts 2 Qwen + P3/P4/P5 external; re-read `.tw2k/public_base_url.txt`):
```powershell
python scripts/grokbot_seat_client.py --public --seat P4 --policy heuristic --max-turns 5     # scripted opponent
python scripts/grokbot_seat_client.py --public --seat P5 --policy mailbox                     # you are the brain: answer .tw2k/mailbox/P5.pending.json
# open {base}/bot?seat=P3 - lobby chips show P4/P5 "bot attached" while their clients run
```

## Queue
_S7 polish/a11y after S6 ACK, or COMPLETE if north-star acceptance met._

## Ben messages (rare)
_Spectator still needs the one-click link in `.tw2k\spectator_link.txt` (swap tunnel base if remote). Re-read `.tw2k\public_base_url.txt` after tunnel watchdog re-exposes._
