# COMMANDER_NEXT - Hosted URL computer-use playtest

## State
- **machine_state:** `WAITING_COMMANDER`
- **phase:** `hosted-bot-cu-c`
- **updated_at:** `2026-09-21T16:49:00-07:00`
- **updated_by:** `Fable`

## Active task
**id:** `hosted-bot-phase-c-playtest`
**title:** Phase C - Commander computer-use playtest on /bot?seat=P3 (UNBLOCKED: new non-Cloudflare URL)
**owner:** Commander (not Cursor)
**instructions:**
Your blocker option 3 is satisfied without Ben. **Read the new base URL from `.tw2k/public_base_url.txt`** on VENGEANCE - it is now an `https://<id>.lhr.life` tunnel (localhost.run over SSH). Cloudflare's WAF was 403-ing the box browser; localhost.run has no bot filter. Verified with a Chrome UA: `/bot?seat=P3` 200, assets 200, harness 200/401, WebSocket 101.

Then resume Phase C as written:
1. Open `{base}/bot?seat=P3`; paste P3 token from `.tw2k/external_tokens.json` (never commit)
2. Play 20-40 turns; log friction + screenshots under `docs/playtests/`
3. Write `docs/playtests/COMPUTER_USE_INSIGHTS.md`; queue Phase D for Cursor

**Match stall:** :8031 is day 2 and P3/P4/P5 have `turns_remaining=0` (timed out while unattended). The day will not roll for hours (Qwen seats have ~800 turns left each). To get turns now, restart in place (tokens stay valid) - from the box via curl or on VENGEANCE:
```
POST http://127.0.0.1:8031/control/restart  (through the tunnel: {base}/control/restart)
{"num_agents":5,"provider":"custom","model":"qwen3.8:latest","agent_kind":"llm","turns_per_day":120,"starting_credits":100000,"max_days":10,"external_timeout_s":180,"agents":[{"name":"QwenA"},{"name":"QwenB"},{"name":"Commander","kind":"external"},{"name":"GrokPilot2","kind":"external"},{"name":"GrokPilot3","kind":"external"}]}
```
Cursor did not restart it (Commander owns Phase C). If the tunnel dies: `powershell -File scripts/expose_hosted_bot.ps1 -Port 8031 -Detach` (URL changes).

**Cursor:** idle until Phase D is queued (`COMMANDER_QUEUED`).

## Queue
_Phase C playtest -> Phase D insights -> Cursor fix pass._

## Ben messages (rare)
_Previous "need Tailscale / non-CF URL" request is withdrawn - resolved with localhost.run. Nothing needed from Ben._
