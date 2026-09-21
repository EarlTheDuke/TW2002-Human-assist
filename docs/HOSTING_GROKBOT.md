# Hosting TW2K for Grok Bot computer-use

**Goal:** Run a match on a URL Commander's box (or sibling Grok Bots) can open, then play via `/bot` with computer use.

**Do not** use xAI API keys as the player brain. External seats wait on `/harness/v1`; Grok Bot decides.

---

## Quick start (VENGEANCE / LAN)

```powershell
cd "C:\Users\sugar\Desktop\ALL AI GAMES\Projects in prgress\TW2002 Human assist cursor"
powershell -File scripts\run_hosted_grokbot.ps1 -Port 8031 -PublicHost "YOUR_TAILSCALE_OR_LAN_HOST"
```

Script sets:
- bind `0.0.0.0` (or `-HostAddr`)
- `TW2K_HARNESS_ALLOW_REMOTE=1` (token still required)
- 2x Qwen (TinyBox custom) + 3x external (P3–P5)
- mints/prints masked tokens from `.tw2k/external_tokens.json` (gitignored)

Open:
- Cockpit: `http://<host>:8031/bot?seat=P3`
- Spectator: `http://<host>:8031/`
- Paste the **full** P3 token into Connect (never commit tokens).

Env alternate: `TW2K_BIND_HOST=0.0.0.0` if your `tw2k serve` path reads it (script passes `-HostAddr` / `--host`).

---

## Reachability options

### A) Tailscale (preferred for long sessions; needs an admin install once)
1. Install Tailscale on the host PC: `winget install tailscale.tailscale` (UAC prompt — Ben must click) and on Commander's box; log both into the same tailnet.
2. Run hosted script with `-PublicHost your-pc.tailnet-name.ts.net` (or Tailscale IP).
3. `scripts/expose_hosted_bot.ps1` prints the Tailscale IP / MagicDNS URLs automatically when `tailscale` is on PATH; pass `-Tailscale` to also run `tailscale serve --bg http://127.0.0.1:8031` for HTTPS inside the tailnet.
4. Send Commander: base URL + which seat/token (or path to tokens file on VENGEANCE only).

As of 2026-09-21 Tailscale is **not** installed on VENGEANCE; option B below works without admin and is what Phase B used.

### B) Public tunnel — `scripts/expose_hosted_bot.ps1` (no account, no admin)
```powershell
powershell -File scripts/expose_hosted_bot.ps1 -Port 8031 -Detach                        # localhost.run (default)
powershell -File scripts/expose_hosted_bot.ps1 -Port 8031 -Detach -Provider cloudflare   # Cloudflare quick tunnel
powershell -File scripts/expose_hosted_bot.ps1 -Stop                                     # tear down all tunnels
```
Two providers, same flow:

| Provider | URL | How | Use when |
|---|---|---|---|
| `localhostrun` (default) | `https://<id>.lhr.life` | `ssh -R 80:127.0.0.1:8031 nokey@localhost.run` with the built-in Windows OpenSSH client | **Computer-use / headless / datacenter browsers.** Verified 2026-09-21: `/bot`, assets, `/state`, harness auth (200/401) and WebSocket upgrade (101) all pass. |
| `cloudflare` | `https://<words>.trycloudflare.com` | portable `cloudflared` downloaded to `.tw2k\bin\` | Human browsers. **Cloudflare's bot-fight WAF returns `403 Your request was blocked` to many datacenter/automation browsers** (curl still works) and cannot be disabled on account-less quick tunnels — this is what blocked Commander's box on 2026-09-21. |

What the script does:
1. Confirms `http://127.0.0.1:8031/bot` answers 200 (start the match first with `run_hosted_grokbot.ps1`).
2. Starts the tunnel as a hidden child process, captures the public URL, writes it to **`.tw2k\public_base_url.txt`** (plus `public_base_url.<provider>.txt`; all gitignored), prints `/bot?seat=P3|P4|P5` + spectator URLs.
3. Verifies `GET {base}/bot` with a Chrome-like User-Agent. A brand-new hostname can take ~1 min to reach *this* box's resolver; the script falls back to pinning the edge IP from 1.1.1.1. A `403` here means the provider is bot-blocking — switch provider.
4. `-Detach` writes `.tw2k\<provider>.pid` and returns; otherwise Ctrl+C stops the tunnel and removes the URL file.

Hand Commander: the contents of `.tw2k\public_base_url.txt` + the P3 token (read from `.tw2k\external_tokens.json` on VENGEANCE; never paste tokens into git or chat logs that get committed).

Notes: both tunnels are semi-public — the bearer token is the only gate, so keep `TW2K_HARNESS_ALLOW_REMOTE=1` paired with strong tokens and rotate after a session (`python scripts/gen_external_tokens.py --seats P3,P4,P5 --rotate`). URLs change on every tunnel restart; re-run the script and re-send. The tunnel is a child of whatever shell launched it — a reboot or closed session drops it.

### Playtest stall: external seats out of turns
If P3–P5 show `turns_remaining=0` before anyone drove them, the external seats timed out (`--external-timeout-s`) four times each and the runner ended their day; the day only rolls when the Qwen seats also finish their 1000 turns, which can take hours. For playtests start the match with a short day, e.g. `run_hosted_grokbot.ps1 -TurnsPerDay 120`, or restart in place (tokens are stable):
```powershell
$body = '{"num_agents":5,"provider":"custom","model":"qwen3.8:latest","agent_kind":"llm","turns_per_day":120,"starting_credits":100000,"max_days":10,"external_timeout_s":180,"agents":[{"name":"QwenA"},{"name":"QwenB"},{"name":"Commander","kind":"external"},{"name":"GrokPilot2","kind":"external"},{"name":"GrokPilot3","kind":"external"}]}'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8031/control/restart -ContentType application/json -Body $body
```

### C) VPS
1. Deploy the repo + `.env` (custom Qwen endpoint must be reachable from the VPS, or run heuristic seats for a UI-only smoke).
2. Reverse-proxy HTTPS to the app port; keep harness token auth on.
3. Firewall: only expose 443 (or the game port) as needed.

### D) Same LAN only
Use the host LAN IP. Commander's box must be on that network (or VPN). LAN IP alone is not enough if the box is remote.

---

## Security checklist

- Bearer tokens required even with `TW2K_HARNESS_ALLOW_REMOTE=1`
- Never commit `.env` or `.tw2k/external_tokens.json`
- Prefer Tailscale over a public Cloudflare URL for long sessions
- Rotate tokens (`scripts/gen_external_tokens.py`) if a URL leaked
- `/bot?token=` is supported for automation but the page strips it from the address bar after load — prefer paste

---

## Smoke checklist

1. Host prints cockpit URL and masked seat tokens
2. Browser loads `/bot` (no 404 on css/js)
3. Connect with P3 token → main panel appears
4. When YOUR TURN pulses green → SCAN or WARP succeeds (log line + WAITING)
5. Spectator `/` still shows the match

---

## Seat map (canonical hosted)

| Seat | Name | Brain |
|------|------|--------|
| P1–P2 | QwenA/B | TinyBox custom LLM |
| P3–P5 | Commander / GrokPilot2/3 | External → Grok Bot via `/bot` |

## Related

- Plan: `docs/plans/2026-09-21-hosted-bot-computer-use.md`
- Connector: `docs/GROK_BOT_CONNECTOR.md`
- Script: `scripts/run_hosted_grokbot.ps1`