# Grok Bot ↔ TW2K Connector

**North star:** Grok Bot agents (Commander and siblings) are the *players*.  
The game never calls xAI. The game waits on `/harness/v1`; **we** decide.

## Why not xAI API keys?

xAI chat-completions is a *different* brain. The product goal is **this** Grok Bot
runtime (Commander / teammates) testing and playing TW2K — same judgment, memory,
and multi-agent orchestration we use for SSI work.

## Layers

```
┌─────────────────────────────────────────────────────────┐
│  Grok Bot agents (Commander, Pilot2, Pilot3, …)         │
│  decide(observation) → Action                           │
└──────────────────────────▲──────────────────────────────┘
                           │ connector (wake + tools)
┌──────────────────────────┴──────────────────────────────┐
│  Bridge options (pick one or combine)                   │
│  A. In-session play loop (Commander actively polling)   │
│  B. Webhook wake (game POSTs turn_due → Grok routine)   │
│  C. MCP (`tw2k mcp`) tools inside the agent session     │
└──────────────────────────▲──────────────────────────────┘
                           │ HTTP loopback + bearer token
┌──────────────────────────┴──────────────────────────────┐
│  TW2K ExternalAgent + /harness/v1  (already shipped)    │
└─────────────────────────────────────────────────────────┘
```

## A — In-session play (works *now*)

While this chat (or a dedicated TW Ops agent chat) is active:

1. Long-poll `GET /harness/v1/{pid}/observation?wait_s=30&format=both`
2. Commander reads the observation (or compact brief)
3. Commander chooses `kind` + `args` (+ thought / goals)
4. `POST /harness/v1/{pid}/action` with `turn_seq`

Script helpers: `scripts/grokbot_seat_client.py` (S6 - the canonical Path-B runner: `--policy mailbox` hands each turn to a Grok Bot session via `.tw2k/mailbox/<SEAT>.pending.json` → `<SEAT>.decision.json`; `--policy heuristic` is a scripted test opponent) and the older `scripts/grokbot_bridge.py` (`watch` dumps briefs; `act` posts one action).

**Latency budget:** finish well under `--external-timeout-s` (default 180).  
Serial scheduler: while we think, other seats wait — keep decisions tight.

## B — Webhook wake (AFK / multi-bot)

When an external seat enters `act()`, the server can POST:

```json
{
  "event": "turn_due",
  "player_id": "P3",
  "name": "Commander",
  "turn_seq": 12,
  "deadline_at": 1790000000.0,
  "base_url": "http://127.0.0.1:8031",
  "observation": { "...truncated or full..." }
}
```

to `TW2K_GROKBOT_WEBHOOK_URL` (or per-seat `TW2K_GROKBOT_WEBHOOK_P3`, …).

Grok Bot side: a **webhook routine** wakes Commander with that payload.  
Saved prompt: read event → decide → POST action to harness with the seat token
from local `.tw2k/external_tokens.json` (never commit tokens).

Multi-bot: one webhook routine per Grok Bot agent, each bound to one `player_id`.

## C — MCP

`tw2k mcp` already exposes cockpit tools. Extend or wrap harness endpoints so
Commander has first-class `tw2k_harness_observation` / `tw2k_harness_action`
tools in-session without raw curl. (Follow-on; harness REST is enough for v1.)

## Seat map (canonical test)

| Seat | Name        | Brain                          |
|------|-------------|--------------------------------|
| P1   | QwenA       | TinyBox LLM (opponent)         |
| P2   | QwenB       | TinyBox LLM (opponent)         |
| P3   | Commander   | **This Grok Bot**              |
| P4   | GrokPilot2  | Sibling Grok Bot agent (later) |
| P5   | GrokPilot3  | Sibling Grok Bot agent (later) |

Until P4/P5 agents exist, Commander may drive all three external seats in one
session (still *Grok Bot* brains — not heuristic, not xAI).

## Proof checklist

- [ ] Fresh match with external seats
- [ ] Actions tagged `actor_kind=external` / thoughts say Commander
- [ ] No `provider=xai` on those seats
- [ ] Multiple successful turns with varied verbs (trade/scan/warp/…)
- [ ] Notes in `docs/playtests/`

## Files

| Path | Role |
|------|------|
| `src/tw2k/agents/external.py` | Optional webhook fire on turn_due |
| `scripts/grokbot_bridge.py` | Local watch/act CLI for Commander |
| `docs/GROK_BOT_PLAYER_GUIDE.md` | Harness protocol |
| `docs/GROK_BOT_CONNECTOR.md` | This doc |

## Primary path (Ben 2026-09-21): Hosted URL + computer use

1. Run `scripts/run_hosted_grokbot.ps1` on a machine/VPS reachable from Grok Bot’s computer
   (or tunnel: Cloudflare Tunnel / Tailscale / SSI reverse proxy).
2. Open `http://<public-host>:<port>/bot?seat=P3` in **my** browser (computer use).
3. Paste the seat bearer token once (Connect). Large buttons: WARP / SCAN / TRADE / WAIT.
4. I play visually; optional harness API remains on the same host for scripted precision.

### Game changes required (this tranche)

| Item | Status |
|------|--------|
| `/bot` cockpit (computer-use UI) | **added** `web/bot.html` + `bot.js` + `bot.css` |
| `GET /bot` route | **added** in `server/app.py` |
| Bind `0.0.0.0` + `TW2K_HARNESS_ALLOW_REMOTE=1` | **`scripts/run_hosted_grokbot.ps1`** |
| Token paste (no xAI) | **yes** |
| Webhook turn_due (optional AFK) | patched in `ExternalAgent` + routine `TW2K Grok Bot turn_due` |

### Still to do when hosting

- Put the process behind HTTPS + firewall allowlist if exposed beyond LAN/Tailscale.
- Point Grok Bot computer use at the public `/bot` URL.
- Optionally wire webhook URL from [Webhook URL](grokbot://app/v1/sidebar?target=webhook-url&automation=tw2k-grok-bot-turn-due) into `TW2K_GROKBOT_WEBHOOK_URL`.
