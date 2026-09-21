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

### B) Cloudflare quick tunnel — `scripts/expose_hosted_bot.ps1` (no account, no admin)
```powershell
powershell -File scripts/expose_hosted_bot.ps1 -Port 8031 -Detach   # leaves tunnel running
powershell -File scripts/expose_hosted_bot.ps1 -Stop                 # tear it down
```
What it does:
1. Confirms `http://127.0.0.1:8031/bot` answers 200 (start the match first with `run_hosted_grokbot.ps1`).
2. Finds `cloudflared` on PATH, else `.tw2k\bin\cloudflared.exe`, else downloads the portable exe there (user-writable; gitignored). No UAC.
3. Runs `cloudflared tunnel --url http://127.0.0.1:8031`, captures the `https://*.trycloudflare.com` URL, writes it to **`.tw2k\public_base_url.txt`** (gitignored), and prints `/bot?seat=P3|P4|P5` + spectator URLs.
4. Verifies `GET {base}/bot` through the tunnel. A brand-new hostname can take ~1 min to reach *this* box's resolver; the script falls back to pinning Cloudflare's edge IP so the check proves the tunnel, not local DNS. Remote boxes usually resolve immediately.
5. Without `-Detach` it stays in the foreground (Ctrl+C stops and removes the URL file). `-Detach` writes `.tw2k\cloudflared.pid` and returns.

Hand Commander: the contents of `.tw2k\public_base_url.txt` + the P3 token (read from `.tw2k\external_tokens.json` on VENGEANCE; never paste tokens into git or chat logs that get committed).

Notes: quick tunnels are semi-public — the bearer token is the only gate, so keep `TW2K_HARNESS_ALLOW_REMOTE=1` paired with strong tokens and rotate after a session. The URL changes every time the tunnel restarts; re-run the script and re-send. WebSocket (`/ws` spectator feed) works through quick tunnels.

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