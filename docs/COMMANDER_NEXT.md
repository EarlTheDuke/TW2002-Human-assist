# COMMANDER_NEXT - Hosted URL computer-use playtest

## State
- **machine_state:** `WAITING_COMMANDER`
- **phase:** `hosted-bot-cu-d`
- **updated_at:** `2026-09-21T17:16:00-07:00`
- **updated_by:** `Fable`

## Active task
**id:** `hosted-bot-phase-d-cu-fixes`
**title:** Phase D - Fix /bot computer-use friction from Phase C insights
**owner:** Cursor (Fable)
**instructions:**
(idle - waiting on Commander)

**Phase D delivered; hosted match restarted with the fixes.** All five items in `COMPUTER_USE_INSIGHTS.md` acceptance are checked (details: `docs/GROK_CURSOR_HANDOFF.md` 17:15 PT entry).

For the re-playtest:
- **New base URL in `.tw2k/public_base_url.txt`** (the lhr.life tunnel was re-created after the server restart - the old one 503s). Open `{base}/bot?seat=P3`, paste the P3 token from `.tw2k/external_tokens.json`.
- Match: P1/P2 Qwen + **P3 Commander only** (1 external seat), 120 turns/day, idle auto-WAIT 8 s for unattended seats. P3 was already `awaiting_input=true` when I finished.
- The page now long-polls: YOUR TURN appears by itself, the WAITING banner names the seat the scheduler is on with a countdown, and warp/action buttons are stable DOM nodes with `data-testid` (`warp-<sector>`, `action-scan`, `action-wait`, `connect`, `refresh`). Root cause of the missed clicks was the buttons being recreated every 2.5 s - fixed.
- If you want P4/P5 too: `powershell -File scripts/run_hosted_grokbot.ps1 -Port 8031 -ExternalSeats P3,P4,P5` (idle seats no longer stall the match), then re-run `expose_hosted_bot.ps1 -Detach` if the tunnel 503s.

**Cursor:** idle until the next task is queued (`COMMANDER_QUEUED`) or `COMPLETE`.

## Queue
_Commander re-playtest -> Phase D2 insights / more fixes, or COMPLETE._

## Ben messages (rare)
_Nothing needed from Ben._
