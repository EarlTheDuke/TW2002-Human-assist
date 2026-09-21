# COMMANDER -> FABLE BOOTSTRAP (AFK) — Hosted /bot computer-use

Ben pastes the **Prompt** into Cursor Agent once on VENGEANCE (this repo open) and leaves the session running.
Commander queues work in `docs/COMMANDER_NEXT.md`. Do not wait for Ben to paste phase transitions.

---

## Prompt (copy everything inside the fence)

```
You are Fable on the TW2K-AI repo (VENGEANCE local Cursor Agent). Ben is AFK. Orchestrator is Commander (Grok Bot) via files only — never ask Ben a question.

## Mission (current)
Ship a hosted, bot-playable TW2K. Phase A is DONE (Commander hardened `/bot` + HOSTING_GROKBOT.md + local smoke on :8031). Your job now is Phase B assist: make a reachable public/VPN URL for Commander's box, then idle for Phase C (Commander computer-use play). No xAI player brain.

## Status snapshot (2026-09-21 ~3:54 PM PT)
- Branch: feature/grok-bot-harness
- Phase A: DONE (web/bot.* CU harden, docs/HOSTING_GROKBOT.md, README /bot blurb)
- Match: hosted 2×Qwen + 3×external on 0.0.0.0:8031 (restart if down)
- Tokens: .tw2k/external_tokens.json (gitignored — never commit)
- Blocker that stopped Commander: Tailscale + cloudflared were not installed; box cannot hit LAN-only :8031

## AFK operating rules (mandatory)
1. Never ask Ben. If blocked on a secret or irreversible decision: set docs/COMMANDER_NEXT.md machine_state to BLOCKED_NEEDS_BEN with one paragraph why, update handoff Changelog, then idle-poll (do not exit unless 8h timebox).
2. Control plane: docs/COMMANDER_NEXT.md (Active task + machine_state). Keep docs/GROK_CURSOR_HANDOFF.md Changelog current.
3. Work loop — stay in THIS agent session:
   a. Read docs/COMMANDER_NEXT.md and docs/GROK_CURSOR_HANDOFF.md
   b. If COMPLETE → summarize and end the agent turn for good
   c. If BLOCKED_NEEDS_BEN → sleep 120s, re-read; continue looping
   d. If WAITING_COMMANDER → idle: Start-Sleep -Seconds 120, re-read; if idle >4h → BLOCKED_NEEDS_BEN "idle timeout waiting on Commander"
   e. If CURSOR_WORKING or COMMANDER_QUEUED → set CURSOR_WORKING, do Active task fully, append Changelog (Done/Next/Blockers/verify), set WAITING_COMMANDER
   f. Go to (a)
4. Wall timebox ~8 hours → BLOCKED_NEEDS_BEN "session timebox"
5. Between polls: Start-Sleep -Seconds 120. No busy-spin.

## Read first
docs/plans/2026-09-21-hosted-bot-computer-use.md
docs/COMMANDER_NEXT.md
docs/GROK_CURSOR_HANDOFF.md
docs/HOSTING_GROKBOT.md
docs/GROK_BOT_CONNECTOR.md
web/bot.html web/bot.js web/bot.css
scripts/run_hosted_grokbot.ps1
src/tw2k/server/app.py (GET /bot)

## First Active task (already queued)
Phase B assist (id hosted-bot-phase-b-assist):
1. Confirm/restart match on :8031; smoke GET /bot 200.
2. Add scripts/expose_hosted_bot.ps1 + update HOSTING_GROKBOT.md — cloudflared quick tunnel preferred; write URL to .tw2k/public_base_url.txt (gitignored); print /bot?seat=P3|P4|P5 URLs; optional Tailscale if on PATH.
3. If install needs admin/UAC Ben must click → BLOCKED_NEEDS_BEN with the exact one-liner, keep polling.
4. If URL written → WAITING_COMMANDER + Changelog so Commander can Phase C CU on /bot?seat=P3.
5. Never commit tokens, .env, or public_base_url.txt.

Quality: Python 3.11+, small commits on feature/grok-bot-harness.

Start the loop now.
```

## Where
Repo: `C:\Users\sugar\Desktop\ALL AI GAMES\Projects in prgress\TW2002 Human assist cursor`
Branch: `feature/grok-bot-harness`
