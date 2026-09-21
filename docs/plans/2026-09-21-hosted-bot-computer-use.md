# Plan: Hosted URL + computer-use playtest (2026-09-21)

**North star:** Host TW2K on a URL Grok Bot can reach. Commander (and sibling bots) play via **computer use** on a bot-friendly UI. Playing that way produces the insight backlog that drives the next build passes.

**Orchestration:** Same as last night — Commander writes the mailbox; Cursor/Fable on VENGEANCE codes ~99% in one long AFK Agent session.

**Out of scope this loop:** xAI / `api.x.ai` as player brain; TinyBox as Commander brain; MCP connector (later).

---

## Phase A — Cursor local: playable bot UI + host path (ACTIVE)

**Owner:** Fable (Cursor local) via `docs/COMMANDER_NEXT.md`  
**Branch:** `feature/grok-bot-harness`

1. Smoke `/bot` against a live `run_hosted_grokbot.ps1` match (connect P3 token → warp/scan/trade/wait).
2. Harden UI for computer use:
   - Buttons disabled unless `awaiting` + not busy
   - Loud YOUR TURN / WAITING banners (color + text, no hover-only)
   - Targets ≥48px; high contrast
   - Show sector warps, port line, credits, turns left, last result, short action log
   - Persist seat+token in localStorage; reconnect survives refresh
   - Clear error toast on 401 / stale turn_seq / timeout
3. Optional: seat chips from `GET /harness/v1/seats` after connect.
4. Optional light `/spectate` note on spectator home (do not steal seats).
5. Write `docs/HOSTING_GROKBOT.md`: Tailscale / Cloudflare tunnel / VPS / LAN; print seat URLs; token paste path; security (tokens still required; `TW2K_HARNESS_ALLOW_REMOTE`).
6. Document `TW2K_BIND_HOST` / script `-HostAddr` / `-PublicHost` in README snippet.
7. Append Changelog; set mailbox `WAITING_COMMANDER`.

**Done when:** Commander can open `http://localhost:<port>/bot?seat=P3`, paste token, complete ≥1 full turn cycle without console errors.

---

## Phase B — Host reachable URL

**Owner:** Ben + Commander assist on VENGEANCE

1. Run `powershell -File scripts/run_hosted_grokbot.ps1 -Port 8031 -PublicHost <tailscale-or-tunnel-host>`.
2. Expose with Tailscale Serve / MagicDNS, or Cloudflare quick tunnel, or LAN IP if box is on same net.
3. Send Commander: public base URL + P3 token (or path to `.tw2k/external_tokens.json` for Commander to read on VENGEANCE only — never commit tokens).

**Done when:** Commander's box browser loads `/bot` and Connect succeeds.

---

## Phase C — Commander computer-use playtest

**Owner:** Commander

1. Open `/bot?seat=P3` on box desktop; connect.
2. Play **20–40 turns** (warp / trade / scan / wait) while Qwen holds P1–P2.
3. Screenshot friction moments; note stalls, missing info, mis-clicks, UI lies, engine waits.

**Done when:** Session log + screenshots exist under `docs/playtests/`.

---

## Phase D — Insight → fix backlog → next Cursor pass

**Owner:** Commander writes; Fable implements ranked fixes

1. Write `docs/playtests/COMPUTER_USE_INSIGHTS.md` (what broke / confused / ranked P0–P2 fixes).
2. Queue next Active task in `COMMANDER_NEXT.md` from that backlog.
3. Repeat A→C until `/bot` is a reliable multi-bot test bed.

---

## Seat map (canonical)

| Seat | Name | Brain |
|------|------|--------|
| P1–P2 | QwenA/B | TinyBox custom LLM |
| P3–P5 | Commander / GrokPilot2/3 | External → Grok Bot via `/bot` or harness |

## Success metric for this undertaking

Not "API keys work." Success = **Grok Bot agents play the hosted game through a real UI**, and we ship concrete engine/UI fixes from that experience.