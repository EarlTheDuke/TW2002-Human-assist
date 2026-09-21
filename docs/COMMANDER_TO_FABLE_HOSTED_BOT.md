# COMMANDER -> FABLE: Hosted URL Grok Bot play

Ben's direction (2026-09-21): Host the game where Grok Bot can reach it; Commander plays via **computer use** on a URL. Build the game for that. Full plan: `docs/plans/2026-09-21-hosted-bot-computer-use.md`.

## Already landed (verify/extend — do not redo blindly)

- `web/bot.html`, `web/bot.js`, `web/bot.css` — large-button Grok Bot cockpit using `/harness/v1`
- `GET /bot` in `src/tw2k/server/app.py`
- `scripts/run_hosted_grokbot.ps1` — `--host 0.0.0.0`, `TW2K_HARNESS_ALLOW_REMOTE=1`, 2 Qwen + 3 external
- `docs/GROK_BOT_CONNECTOR.md` — architecture + hosted path
- Webhook fire on external turn_due in `ExternalAgent` (optional AFK)

## Your job (Phase A)

See Active task in `docs/COMMANDER_NEXT.md` and Phase A in the plan doc.

Branch: `feature/grok-bot-harness`. No xAI keys. Grok Bot = Commander via URL + computer use.