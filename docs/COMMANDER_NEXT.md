# COMMANDER_NEXT — AFK task mailbox

Cursor: read this file at every loop iteration.
Commander: overwrite **Active task** when advancing phases. Do not ask Ben.

## State
- **machine_state:** `CURSOR_WORKING`
- **phase:** `1`
- **updated_at:** `2026-09-20T21:32:00-07:00`
- **updated_by:** `Fable`
- **stop_when:** `machine_state` is `COMPLETE` or `BLOCKED_NEEDS_BEN`

## Active task (do this now)
**id:** `phase-1-external-harness`
**title:** Phase 1 — ExternalAgent + REST + tests + smoke
**instructions:**
Phase 0 plan at `docs/plans/2026-09-20-external-harness.md` is accepted. Implement Phase 1 on branch `feature/grok-bot-harness` per the plan (commits 1a–1f).

Do in order:
1. Cut/use branch `feature/grok-bot-harness` from current work branch as planned.
2. **1a** `ExternalAgent` + `PlayerKind.EXTERNAL` + unit tests 1–5
3. **1b** `harness_tokens` + `.gitignore` + `.env.example` + test 6 (no secrets in git)
4. **1c** runner wiring (`AgentSpec.external_token`, `MatchSpec.external_timeout_s`, `_build_agents`, timeout → WAIT+AGENT_ERROR, `record_result`) + tests 7–9
5. **1d** harness router mount + tests 10–14, 16
6. **1e** CLI `--external` / `--external-timeout-s` / tokens file + `_build_default_spec` + `/control/restart` + test 15 + banner (masked tokens)
7. **1f** `scripts/smoke_external_harness.py` + `scripts/external_client_example.py` + CI offline smoke step

Exit: ruff clean, pytest green, smoke exit 0. Append Changelog Done/Next/Blockers + verify commands. Set `machine_state` to `WAITING_COMMANDER`. Do **not** start Phase 2 until Commander queues it. Never commit secrets or token files.

## Queue (Commander fills when advancing)
_Phase 2 next after Phase 1 acceptance: `run_2qwen_4external.ps1` + token gen + `docs/GROK_BOT_PLAYER_GUIDE.md`._

## Ben messages (rare)
_None. Do not wait on Ben unless machine_state is BLOCKED_NEEDS_BEN._
