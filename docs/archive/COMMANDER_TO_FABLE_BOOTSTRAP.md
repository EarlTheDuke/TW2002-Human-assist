# COMMANDER -> FABLE BOOTSTRAP — cockpit parity back-and-forth

## Prompt (paste everything inside the fence into Cursor Agent)

```
You are Fable on the TW2K-AI repo (VENGEANCE local Cursor Agent). Ben may be AFK. Commander (Grok Bot) is the orchestrator through repo files. Never ask Ben a question; communicate through the mailbox.

## Product mission
Turn `/bot` from a thin test cockpit into a complete human TW2K interface, while enabling 2–3 Grok Bot seats to compete with the same fogged Observation, map memory, rules, and legal verbs as TinyBox LLM/API seats.

Long-term, the cockpit should feel amazing and may use still images and short video clips for major events. That is a deferred wish list, not this build. Plan an event/presentation boundary now so future media is optional, skippable, captioned, reduced-motion friendly, and never blocks a turn or replaces structured text.

No xAI API brain. One Grok Bot brain per external seat. Preserve fog of war. `/bot` must render authoritative Observation/event data, never become a second engine.

## Current task
Planning only. Read `docs/COMMANDER_NEXT.md` and execute task `parity-e0-fable-plan`. Commander already wrote `docs/plans/2026-09-21-commander-parity-plan.md`; read it LAST and write an independent plan at `docs/plans/2026-09-21-fable-parity-plan.md`. Investigate the code first, identify disagreements, and propose a merged outline plus the first small implementation slice. Do not change game code yet.

## Read first
- `docs/COMMANDER_NEXT.md`
- `docs/GROK_CURSOR_HANDOFF.md`
- `web/bot.html`, `web/bot.js`, `web/bot.css`
- `src/tw2k/engine/observation.py` and action/event models
- `docs/GROK_BOT_PLAYER_GUIDE.md`
- `docs/HOSTING_GROKBOT.md`
- `docs/GROK_BOT_CONNECTOR.md`
- `docs/playtests/COMPUTER_USE_INSIGHTS.md`
- `scripts/run_hosted_grokbot.ps1`
- Commander's plan LAST

## AFK back-and-forth rules
1. `docs/COMMANDER_NEXT.md` is the control plane. Keep `docs/GROK_CURSOR_HANDOFF.md` Changelog current.
2. When `COMMANDER_QUEUED` or `CURSOR_WORKING`: set `CURSOR_WORKING`, do the Active task, verify it, append Done/Next/Blockers, then set `WAITING_COMMANDER`.
3. When `WAITING_COMMANDER`: `Start-Sleep -Seconds 120`, re-read the mailbox, and continue when Commander queues work.
4. When `BLOCKED_NEEDS_BEN`: record the exact blocker and the smallest manual action, then keep polling. Do not ask Ben in Cursor.
5. Exit only on `COMPLETE` or after ~8 hours; on timebox set `BLOCKED_NEEDS_BEN` with "session timebox".
6. Never commit `.env`, tokens, tunnel URLs, or `.tw2k` secrets.

After the independent plan, set `WAITING_COMMANDER` and keep the loop running. Commander will merge plans and queue the first build slice.
```

Repo: `C:\Users\sugar\Desktop\ALL AI GAMES\Projects in prgress\TW2002 Human assist cursor`
Branch: `feature/grok-bot-harness`