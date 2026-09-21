# GROK ↔ CURSOR HANDOFF — TW2K Multi-Bot Edition

**Living doc.** Commander (Grok Bot) ↔ Cursor (Fable). Ben is **AFK** — do not ask him questions. Use the AFK loop below.

| Field | Value |
|-------|--------|
| Project root | this repo |
| Orchestrator | **Commander** (Grok Bot) |
| Coder (~99%) | **Cursor / Fable** |
| AFK mailbox | `docs/COMMANDER_NEXT.md` |
| Started | 2026-09-20 (PT) |
| Branch target | `feature/grok-bot-harness` |
| Status | **AFK LOOP — Phase 2 queued** |

---

## AFK loop (how this keeps going without Ben)

```
Cursor agent (one long session)          Commander (routine ~every 10 min)
──────────────────────────────          ────────────────────────────────
read COMMANDER_NEXT.md                  read COMMANDER_NEXT + handoff
do Active task                          if WAITING_COMMANDER:
update handoff Changelog                  write next Active task (Phase N+1)
set WAITING_COMMANDER                     set machine_state COMMANDER_QUEUED
sleep ~2 min, re-read mailbox           if BLOCKED_NEEDS_BEN → ping Ben
if new task / COMMANDER_QUEUED → work   if COMPLETE → pause watch, ping Ben
if COMPLETE → exit cleanly              else stay quiet
```

**Cursor never exits the session until** `machine_state` is `COMPLETE` or `BLOCKED_NEEDS_BEN`, or wall-clock **8 hours** from start (then set BLOCKED_NEEDS_BEN: "session timebox hit").

**Polling:** between tasks, `Start-Sleep -Seconds 120` (PowerShell) or equivalent, then re-read `docs/COMMANDER_NEXT.md`. Cap idle polls at 4 hours waiting on Commander; if still idle, set BLOCKED_NEEDS_BEN.

**Commander** does **not** type into the Cursor UI. Commander only writes files + (when needed) messages Ben. Cursor discovers new work by re-reading the mailbox.

---

## 1. Product goal

Ship TW2K-AI with existing LLM API players (including **custom/Qwen**) **plus up to four Grok Bot** seats via token-authenticated **external harness** for game testing.

Success:
1. Mixed match: e.g. 2× Qwen (`qwen3.8:latest`) + 4× `external` Grok Bot seats
2. External seats: pull Observation → POST Action JSON (localhost + bearer token)
3. Spectator + optional `/play` still work
4. Smoke script + `docs/GROK_BOT_PLAYER_GUIDE.md`
5. Handoff + COMMANDER_NEXT stay current

Non-goals: public multi-human net play; rewrite engine language; Cursor on-demand spend.

---

## 2. Architecture lock

### Keep
- Pure `engine/`, `BaseAgent.act(Observation) -> Action`, fog-of-war
- LLM providers: `xai | openai | anthropic | deepseek | custom | cursor`
- MCP human/copilot tools

### Add — `ExternalAgent` + HTTP harness
- Kind: `external`
- Per seat: player_id, name, bearer token (gitignored token file)
- Block with timeout (`TW2K_EXTERNAL_TIMEOUT_S`, default ~120) → WAIT + AGENT_ERROR on timeout
- Endpoints on **127.0.0.1**:
  - `GET /harness/v1/{player_id}/observation`
  - `POST /harness/v1/{player_id}/action`
  - `GET /harness/v1/{player_id}/status`
  - Optional later: `WS /harness/v1/{player_id}/ws` turn_due
- Restart/CLI JSON supports mix of custom Qwen + external seats

### Do not
- Commit secrets; bind 0.0.0.0 without explicit flag; break default AI-vs-AI serve

---

## 3. Phased delivery

### Phase 0 — Plan (DONE)
- Plan only → `docs/plans/2026-09-20-external-harness.md`
- Then WAITING_COMMANDER (no Phase 1 code until Commander queues it)

### Phase 1 — ExternalAgent + REST + tests + smoke script
### Phase 2 — `scripts/run_2qwen_4external.ps1` + tokens file + Grok Bot player guide
### Phase 3 — Optional WS, spectator labels, cost N/A for external

---

## 4. Acceptance criteria

- [ ] 2× custom Qwen + 4× external starts
- [ ] 401 on bad token; timeout → WAIT; valid Action applies
- [ ] Smoke script green; no secrets in git
- [ ] AFK mailbox ends at COMPLETE

---

## 5. Orchestrator notes (Commander)

_2026-09-20 PT — AFK protocol enabled. Mailbox: docs/COMMANDER_NEXT.md. Commander watch routine polls ~10 min. Cursor: long session with 2-min sleep polls. First task = Phase 0 plan._

_2026-09-20 21:30 PT — Commander: Phase 0 plan accepted (sane: ExternalAgent=HumanAgent+turn_seq+long-poll+tokens; REST /harness/v1; 1a–1f phasing). Queued Phase 1 in COMMANDER_NEXT.md → machine_state COMMANDER_QUEUED, phase 1._


_2026-09-20 21:58 PT — Commander: Phase 1 accepted (ExternalAgent+REST+tests+smoke; tip `e700ea6`; 486 tests; smoke PASS). Queued Phase 2 in COMMANDER_NEXT.md → machine_state COMMANDER_QUEUED, phase 2. Scope: `run_2qwen_4external.ps1` + `gen_external_tokens.py` + `docs/GROK_BOT_PLAYER_GUIDE.md` + ARCHITECTURE/ROADMAP touch._

---

## 6. Changelog

### 2026-09-20 — Commander
- Bootstrap + AFK mailbox/loop. Architecture: ExternalAgent harness for 4 Grok Bots; keep Qwen custom seats.

### Cursor — (append below)

<!-- Fable: append dated Done / Next / Blockers -->

### 2026-09-20 21:22 PT — Fable — Phase 0 (plan) DONE
- **Done:** `docs/plans/2026-09-20-external-harness.md` — verified ground truth (HumanAgent queue pattern, runner deadline branch, AgentSpec/override flow, PlayerKind, meta.json, MCP token pattern), design (`ExternalAgent` = HumanAgent + `turn_seq` + long-poll event + per-seat token + `last_result`), file-level plan (new: `agents/external.py`, `server/harness.py`, `server/harness_tokens.py`, tests, smoke, example client; edited: `models.py` enum only, `runner.py`, `app.py`, `cli.py`, `.gitignore`, `.env.example`, CI), REST table (`/harness/v1/{seats,rules,{pid}/status,{pid}/observation?wait_s,{pid}/action}` + error codes), 2×Qwen+4×external CLI and restart-body configs, 16 tests, phasing 1a–1f/2/3, risks.
- **No harness code written** (Phase 0 lock respected).
- **Env facts for Commander:** TinyBox `/api` on the current key serves `qwen3.8:latest` (200); `kimi-k2.5`/`k2.6` → 400 Model not found. Windows needs `PYTHONUTF8=1` or the rich banner crashes.
- **Next (on COMMANDER_QUEUED):** Phase 1a — cut `feature/grok-bot-harness`, `ExternalAgent` + `PlayerKind.EXTERNAL` + unit tests.
- **Blockers:** none. (FYI only, not blocking: `docs/MIXED_LLM_ACCESS.md` is untracked and embeds a stale Open WebUI key — should be redacted before it is ever committed.)
- **Verify:** `Get-Content docs/plans/2026-09-20-external-harness.md | Select-Object -First 20`

### 2026-09-20 21:30 PT — Commander — Phase 0 ACK → Phase 1 queued
- **Ack:** Plan at `docs/plans/2026-09-20-external-harness.md` accepted; no code changes from Commander.
- **Queued:** Phase 1 (1a–1f ExternalAgent + REST + tests + smoke) via `COMMANDER_QUEUED`.
- **Next after Cursor finishes Phase 1:** Phase 2 script + tokens helper + Grok Bot player guide.

### 2026-09-20 21:52 PT — Fable — Phase 1 (ExternalAgent + REST + tests + smoke) DONE
- **Branch:** `feature/grok-bot-harness` pushed to origin (8 commits on top of `cursor-composer-provider` @ `c43510e`; tip `e700ea6`).
- **Done (per plan §2):**
  - 1a `src/tw2k/agents/external.py` — `ExternalAgent` (kind `external`, 1-slot queue, `turn_seq`, `turn_due` long-poll event, `last_result`, token held in-memory only); `PlayerKind.EXTERNAL`; exported from `tw2k.agents`.
  - 1b `src/tw2k/server/harness_tokens.py` — explicit > env `TW2K_EXTERNAL_TOKEN_<PID>` > tokens file > generated+persisted (`.tw2k/external_tokens.json`, 0600 best-effort); `mask()` ASCII-only; `verify()` via `hmac.compare_digest`. `.gitignore` adds `.tw2k/` + `*external_tokens*.json`; `.env.example` documents the knobs.
  - 1c `server/runner.py` — `AgentSpec.external_token` (excluded from meta.json), `MatchSpec.external_timeout_s` (default 120), `_build_agents` external branch, deadline branch generalized: external timeout → WAIT + `AGENT_ERROR{external_timeout:true}`; `record_result` hook after `apply_action`; timeout WAITs count toward `last_action_was_timeout`.
  - 1d `server/harness.py` — `/harness/v1/{seats,rules,{pid}/status,{pid}/observation?wait_s&format,{pid}/action}`; 401/403/404/409(`not_external`|`stale_turn`|`not_awaiting`)/422/429/503 per plan; loopback-only unless `TW2K_HARNESS_ALLOW_REMOTE=1`; `actor_kind` stripped from bot submissions. Mounted in `create_app`.
  - 1e `cli.py` `--external P3,P4`, `--external-timeout-s`, `--external-tokens-file`; `_build_default_spec` resolves seat tokens (only when external seats exist, so LLM-only matches never create `.tw2k/`); `/control/restart` accepts `agents[].kind="external"`, `agents[].token`, `external_timeout_s`; banner prints `EXTERNAL token=abcd...wxyz` (masked) + harness URL.
  - 1f `scripts/smoke_external_harness.py` (offline, exit 0, added to CI offline-smoke step) + `scripts/external_client_example.py` (reference long-poll bot; drove a live `tw2k serve --external P2` on :8010 for 4 turns, all `ok`).
  - Lint tidy commit: cleared 18 pre-existing ruff 0.15 findings in untouched files so CI's ruff job is green.
- **Tests:** `tests/test_external_harness_phase1.py` — 15 tests covering plan items 1–16 (11/12/13 merged into one HTTP flow). Full suite **486 passed** (was 471). `ruff check src tests scripts` clean on tracked files.
- **Verify:**
  ```powershell
  git checkout feature/grok-bot-harness
  python -m ruff check src tests scripts
  $env:PYTHONUTF8="1"; python -m pytest -q tests/test_external_harness_phase1.py
  python scripts/smoke_external_harness.py          # PASS external harness smoke
  # live: tw2k serve --agent-kind heuristic --num-agents 2 --external P2 --port 8010
  #       then set TW2K_HARNESS_PLAYER=P2 / TW2K_HARNESS_TOKEN=<from .tw2k/external_tokens.json>
  #       python scripts/external_client_example.py
  ```
- **Deviations from plan:** none functional. Plan test 11/12/13 live in one test function. Long-poll cap 60 s. `HUMAN_TURN_START` is *not* emitted for external seats (as planned).
- **Housekeeping note (my mistake, not blocking):** while cleaning up after the live check I ran `Remove-Item saves\*seed42*`, which also removed today's earlier gitignored seed-42 match saves (the 3× and 4× Qwen runs Ben watched). Nothing tracked was affected; no replay of those two matches is possible now.
- **Next (on COMMANDER_QUEUED):** Phase 2 — `scripts/run_2qwen_4external.ps1`, `scripts/gen_external_tokens.py`, `docs/GROK_BOT_PLAYER_GUIDE.md`, ARCHITECTURE/ROADMAP touch.
- **Blockers:** none.

### 2026-09-20 21:58 PT — Commander — Phase 1 ACK → Phase 2 queued
- **Ack:** Phase 1 on `feature/grok-bot-harness` @ `e700ea6` accepted (486 tests, ruff clean, smoke PASS, live REST check).
- **Queued:** Phase 2 via `COMMANDER_QUEUED` — `scripts/run_2qwen_4external.ps1`, `scripts/gen_external_tokens.py`, `docs/GROK_BOT_PLAYER_GUIDE.md`, ARCHITECTURE/ROADMAP touch.
- **Next after Cursor finishes Phase 2:** Phase 3 polish or COMPLETE if acceptance criteria met.

### 2026-09-20 22:06 PT — Fable — Phase 2 (mixed-match script + tokens + guide) DONE
- **Branch:** `feature/grok-bot-harness` @ `e1fa90b` (pushed).
- **Done:**
  - `scripts/gen_external_tokens.py` — mints/keeps tokens for `--seats` (default P3–P6) in the gitignored tokens file; prints masked; `--rotate`, `--show` (explicit opt-in to print env lines).
  - `scripts/run_2qwen_4external.ps1` — sets `PYTHONUTF8`, pre-generates tokens, prints per-seat env + curl one-liners (masked), then `tw2k serve --provider custom --model qwen3.8:latest --num-agents 6 --external P3,P4,P5,P6 --external-timeout-s 120 --starting-credits 1000000`. Params: `-Port -StartingCredits -MaxDays -TimeoutS -Seed -Model -Names`.
  - `docs/GROK_BOT_PLAYER_GUIDE.md` — setup, endpoint table, status-code table, turn protocol, observation field map, 30-verb arg cheat sheet (arg names checked against `engine/runner.py` handlers), minimal bot example, good-turn checklist, troubleshooting.
  - `docs/ARCHITECTURE.md` (agent list, server routes, ExternalAgent section) and `docs/ROADMAP.md` (Phase X block with acceptance criteria).
- **Live acceptance check:** ran the script on :8020 → banner shows P1/P2 `custom qwen3.8:latest`, P3–P6 `EXTERNAL token=xxxx...xxxx`; `/state` confirms kinds; `/harness/v1/seats` lists 4 seats; `external_client_example.py` as P3 completed `warp → ok` inside the mixed match (Qwen seats took their turns first). Server stopped afterward; temp tokens file removed. `.tw2k/` confirmed gitignored (`git check-ignore`).
- **Regression:** `smoke_external_harness.py` PASS; `tests/test_external_harness_phase1.py` 15 passed; ruff clean on tracked files.
- **Fix during phase:** PowerShell reserves `$pid`; loop var renamed to `$seat` in the run script.
- **Verify:**
  ```powershell
  python scripts/gen_external_tokens.py            # masked P3..P6
  powershell -File scripts/run_2qwen_4external.ps1 -Port 8020 -MaxDays 1
  # other shell: $env:TW2K_HARNESS_URL="http://127.0.0.1:8020"; $env:TW2K_HARNESS_PLAYER="P3"
  #              $env:TW2K_HARNESS_TOKEN=(Get-Content .tw2k\external_tokens.json | ConvertFrom-Json).P3
  #              python scripts/external_client_example.py
  ```
- **Handoff §4 acceptance status:** 2×Qwen+4×external starts ✅ · 401 bad token / timeout→WAIT / valid Action applies ✅ (tests 8, 10, 12) · smoke green, no secrets in git ✅ · mailbox COMPLETE — Commander's call.
- **Next (on COMMANDER_QUEUED):** Phase 3 optional — `WS /harness/v1/{pid}/ws` turn_due push, spectator `EXTERNAL` badge, cost `n/a` column, MCP `tw2k_list_external_seats`. Or COMPLETE.
- **Blockers:** none.
