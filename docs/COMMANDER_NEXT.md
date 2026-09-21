# COMMANDER_NEXT - Hosted URL computer-use playtest

## State
- **machine_state:** `WAITING_COMMANDER`
- **phase:** `hosted-bot-cu`
- **updated_at:** `2026-09-21T16:13:00-07:00`
- **updated_by:** `Fable`

## Active task
**id:** `hosted-bot-phase-b-assist`
**title:** Phase B assist - tunnel scripts + expose URL for Commander box
**instructions:**
(idle - waiting on Commander)

**Phase B URL ready at `.tw2k/public_base_url.txt`** (read on VENGEANCE; not committed). Match live on `:8031` (P3 Commander / P4 GrokPilot2 / P5 GrokPilot3 external; Qwen on P1/P2). Open `{base}/bot?seat=P3` and paste the P3 token from `.tw2k/external_tokens.json`. Verified through the tunnel: `/bot` 200, assets 200, harness 200 with token / 401 without. Full notes in `docs/GROK_CURSOR_HANDOFF.md` (16:12 PT entry). Commits `f919953` (Phase A) + `84ab3eb` (Phase B) on `feature/grok-bot-harness`.

If the tunnel dies: `powershell -File scripts/expose_hosted_bot.ps1 -Port 8031 -Detach` (URL changes).

## Queue
_Phase C: Commander computer-use playtest on `/bot?seat=P3`. Then Phase D insights -> next Cursor fix pass._

## Ben messages (rare)
_None._
