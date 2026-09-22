# GROK - CURSOR HANDOFF - TW2K Multi-Bot Edition

**Living doc.** Commander (Grok Bot) <-> Cursor (Fable). Ben may be AFK - prefer the AFK loop; do not block on questions.

| Field | Value |
|-------|--------|
| Project root | this repo |
| Orchestrator | **Commander** (Grok Bot) |
| Coder (~99%) | **Cursor / Fable** (local Agent on VENGEANCE) |
| AFK mailbox | `docs/COMMANDER_NEXT.md` |
| Plan (current) | `docs/plans/2026-09-21-hosted-bot-computer-use.md` |
| Branch target | `feature/grok-bot-harness` |
| Status | **COMMANDER_QUEUED - S2 read-only cockpit tapes** |
| Prior | Phase 2 external harness COMPLETE @ e1fa90b (2026-09-20) |

---

## Current mission (2026-09-21)

Host TW2K on a reachable URL with a **bot-playable `/bot` UI**. Commander plays via **computer use**. Insights from that play become the next fix backlog. No xAI keys Ã¢â‚¬â€ Grok Bot is the player.

Phases: A Cursor polish/smoke Ã¢â€ â€™ B host URL Ã¢â€ â€™ C Commander CU playtest Ã¢â€ â€™ D insights doc Ã¢â€ â€™ loop.

---

## AFK loop (unchanged)

```
Cursor agent (one long session)          Commander (routine ~every 10 min)
read COMMANDER_NEXT.md                  read COMMANDER_NEXT + handoff
do Active task                          if WAITING_COMMANDER:
update handoff Changelog                  write next Active task
set WAITING_COMMANDER                     set COMMANDER_QUEUED
sleep ~2 min, re-read mailbox           if BLOCKED_NEEDS_BEN -> ping Ben
if new task / COMMANDER_QUEUED -> work  if COMPLETE -> pause watch, ping Ben
if COMPLETE -> exit cleanly             else stay quiet
```

**Cursor never exits** until `COMPLETE` or `BLOCKED_NEEDS_BEN`, or **8h** wall timebox.
**Polling:** `Start-Sleep -Seconds 120`. Cap idle waiting on Commander at 4h.
**Commander** only writes files (+ Ben when needed). Cursor discovers work by re-reading the mailbox.

---

## Changelog

### 2026-09-21 18:53 PT — Commander — S1 ACK → S2 queued
- **Ack:** parity-s1-server-data @ `5065a4f` accepted (peek, fogged `/events`+facts, spectator gate, xAI gate, webhook deadline; 499 tests).
- **Queued:** Active task `parity-s2-readonly-tapes` — Where/Know panels on `/bot`, English last_result, events log; peek-powered.
- mailbox → `COMMANDER_QUEUED` phase `parity-s2`.
### 2026-09-21 18:25 PT — Commander — merged plans, queued S1
- Fable E0 plan accepted. Canonical: docs/plans/2026-09-21-bot-human-parity.md
- Accepted Fable D1–D13 (peek first, event stream, legal_actions later, spectator gate, no recommend-move, quarantine route table, gate xAI script).
- Queued Active task parity-s1-server-data. mailbox COMMANDER_QUEUED.

### 2026-09-21 17:59 PT — Commander — complete human cockpit direction
- Ben expanded the north star: /bot becomes a complete human interface; competitive multi-Grok-Bot parity remains core.
- Added deferred immersive-media wish list (semantic events -> optional images/video; accessibility and CU fallbacks).
- Refreshed Fable E0 independent-plan task + AFK bootstrap. No implementation queued until plans merge.

### 2026-09-21 17:51 PT — Commander — E0 parity plans
- Hosted CU loop COMPLETE earlier. New goal: multi-bot + human /bot info and tool parity vs API LLM seats.
- Commander plan: docs/plans/2026-09-21-commander-parity-plan.md
- Queued Fable independent plan: docs/plans/2026-09-21-fable-parity-plan.md (no code). mailbox COMMANDER_QUEUED.

### 2026-09-21 17:32 PT — Commander — Phase C2 PASS → COMPLETE
- **C2 re-playtest:** 8 successful P3 WARPs on `/bot?seat=P3` (lhr.life). Phase D checks all PASS (WAITING names seat, data-testid clicks 0 misses, YOUR TURN without reload, no idle-sibling stall).
- Artifacts: `docs/playtests/C2_SESSION_LOG.md`, `docs/playtests/screenshots-c2/{01-connected,02-your-turn,08-waiting-seat}.png`.
- **Decision:** No D2 Cursor pass (no new UI friction beyond Qwen wait). Optional polish deferred.
- mailbox → `COMPLETE`. Pausing TW2K AFK handoff watch. Cursor should exit cleanly.

### 2026-09-21 17:24 PT — Commander — Phase D ACK → Phase C2 re-playtest
- **Ack:** Phase D @ `2e4a5c2`/`e5184a9`/`db8f0be` accepted (idle auto-WAIT, `current_turn` banner, stable `data-testid`, long-poll YOUR TURN; 490 tests).
- Tunnel 503 → re-ran `expose_hosted_bot.ps1`; new base in `.tw2k/public_base_url.txt`.
- Match restarted (3 seats, 120 turns/day, P3 token pinned); P3 `turns_remaining=120`.
- mailbox → `COMMANDER_WORKING` phase `hosted-bot-cu-c2`. Cursor idle.
- **Doing:** computer-use re-playtest on `/bot?seat=P3` (≥8 turns validating D fixes).

### 2026-09-21 15:54 PT — Commander — requeue Phase B assist for Cursor paste
- Ben asked for updated Cursor paste. Phase A still DONE; prior BLOCKED was missing Tailscale/cloudflared.
- New Active task: `hosted-bot-phase-b-assist` — expose_hosted_bot.ps1 + write `.tw2k/public_base_url.txt` + HOSTING update.
- mailbox -> COMMANDER_QUEUED. Bootstrap refreshed in COMMANDER_TO_FABLE_BOOTSTRAP.md.


### 2026-09-21 11:05 PT â€” Commander â€” Phase B BLOCKED_NEEDS_BEN
- Phase A already done; VENGEANCE tw2k listening 0.0.0.0:8031; tokens present.
- Cannot expose URL: Tailscale + cloudflared missing on VENGEANCE; Commander box cannot hit LAN.
- mailbox -> BLOCKED_NEEDS_BEN (task hosted-bot-phase-b-url). Ben: Tailscale Serve / cloudflared quick tunnel / other public URL -> then Phase C CU on /bot?seat=P3.

### 2026-09-21 (Commander) â€” Phase A done on VENGEANCE (no Cursor paste)
- Ben AFK: cannot inject local Cursor Agent; Commander executed Phase A via Shell on VENGEANCE
- Hardened `web/bot.*` for computer use (pulse banner, action gating, classified errors, strip ?token=)
- Added `docs/HOSTING_GROKBOT.md` + README `/bot` blurb
- machine_state: WAITING_COMMANDER (need reachable host URL for Phase B/C)

### 2026-09-21 (Commander) Ã¢â‚¬â€ reopen for hosted computer-use
- Queued Phase A: polish `/bot`, `HOSTING_GROKBOT.md`, smoke against `run_hosted_grokbot.ps1`
- Plan written: `docs/plans/2026-09-21-hosted-bot-computer-use.md`
- machine_state: COMMANDER_QUEUED (task `hosted-bot-ui-hosting`)

---

## Prior handoff body (Phase 0Ã¢â‚¬â€œ2 external harness)

## 1. Product goal

Ship TW2K-AI with existing LLM API players (including **custom/Qwen**) **plus up to four Grok Bot** seats via token-authenticated **external harness** for game testing.

Success:
1. Mixed match: e.g. 2Ãƒâ€” Qwen (`qwen3.8:latest`) + 4Ãƒâ€” `external` Grok Bot seats
2. External seats: pull Observation Ã¢â€ â€™ POST Action JSON (localhost + bearer token)
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

### Add Ã¢â‚¬â€ `ExternalAgent` + HTTP harness
- Kind: `external`
- Per seat: player_id, name, bearer token (gitignored token file)
- Block with timeout (`TW2K_EXTERNAL_TIMEOUT_S`, default ~120) Ã¢â€ â€™ WAIT + AGENT_ERROR on timeout
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

### Phase 0 Ã¢â‚¬â€ Plan (DONE)
- Plan only Ã¢â€ â€™ `docs/plans/2026-09-20-external-harness.md`
- Then WAITING_COMMANDER (no Phase 1 code until Commander queues it)

### Phase 1 Ã¢â‚¬â€ ExternalAgent + REST + tests + smoke script
### Phase 2 Ã¢â‚¬â€ `scripts/run_2qwen_4external.ps1` + tokens file + Grok Bot player guide
### Phase 3 Ã¢â‚¬â€ Optional WS, spectator labels, cost N/A for external

---

## 4. Acceptance criteria

- [x] 2Ãƒâ€” custom Qwen + 4Ãƒâ€” external starts
- [x] 401 on bad token; timeout Ã¢â€ â€™ WAIT; valid Action applies
- [x] Smoke script green; no secrets in git
- [x] AFK mailbox ends at COMPLETE

---

## 5. Orchestrator notes (Commander)

_2026-09-21 18:53 PT — Commander: S1 accepted (`5065a4f`). Queued S2 read-only cockpit tapes. mailbox COMMANDER_QUEUED._

_2026-09-21 17:32 PT — Commander: C2 re-playtest PASS (8 turns); hosted /bot CU loop COMPLETE. AFK watch paused._


_2026-09-21 17:24 PT — Commander: Phase D accepted; C2 re-playtest in progress (COMMANDER_WORKING). Cursor idle until D2 or COMPLETE._


_2026-09-20 PT Ã¢â‚¬â€ AFK protocol enabled. Mailbox: docs/COMMANDER_NEXT.md. Commander watch routine polls ~10 min. Cursor: long session with 2-min sleep polls. First task = Phase 0 plan._

_2026-09-20 21:30 PT Ã¢â‚¬â€ Commander: Phase 0 plan accepted (sane: ExternalAgent=HumanAgent+turn_seq+long-poll+tokens; REST /harness/v1; 1aÃ¢â‚¬â€œ1f phasing). Queued Phase 1 in COMMANDER_NEXT.md Ã¢â€ â€™ machine_state COMMANDER_QUEUED, phase 1._


_2026-09-20 21:58 PT Ã¢â‚¬â€ Commander: Phase 1 accepted (ExternalAgent+REST+tests+smoke; tip `e700ea6`; 486 tests; smoke PASS). Queued Phase 2 in COMMANDER_NEXT.md Ã¢â€ â€™ machine_state COMMANDER_QUEUED, phase 2. Scope: `run_2qwen_4external.ps1` + `gen_external_tokens.py` + `docs/GROK_BOT_PLAYER_GUIDE.md` + ARCHITECTURE/ROADMAP touch._

_2026-09-20 22:16 PT Ã¢â‚¬â€ Commander: Phase 2 accepted (`run_2qwen_4external.ps1` + `gen_external_tokens.py` + `GROK_BOT_PLAYER_GUIDE.md`; tip `e1fa90b`; live mixed match + P3 turn ok). Handoff Ã‚Â§4 acceptance met. Skipping optional Phase 3 polish. Set machine_state COMPLETE; pausing TW2K AFK handoff watch._

---



_2026-09-21 11:05 PT â€” Commander: Phase A complete; Phase B blocked on reachable host URL (no Tailscale/cloudflared on VENGEANCE). Set BLOCKED_NEEDS_BEN; ping Ben for tunnel/URL. Phase C waits._

## 6. Changelog

### 2026-09-20 Ã¢â‚¬â€ Commander
- Bootstrap + AFK mailbox/loop. Architecture: ExternalAgent harness for 4 Grok Bots; keep Qwen custom seats.

### Cursor Ã¢â‚¬â€ (append below)

<!-- Fable: append dated Done / Next / Blockers -->

### 2026-09-20 21:22 PT Ã¢â‚¬â€ Fable Ã¢â‚¬â€ Phase 0 (plan) DONE
- **Done:** `docs/plans/2026-09-20-external-harness.md` Ã¢â‚¬â€ verified ground truth (HumanAgent queue pattern, runner deadline branch, AgentSpec/override flow, PlayerKind, meta.json, MCP token pattern), design (`ExternalAgent` = HumanAgent + `turn_seq` + long-poll event + per-seat token + `last_result`), file-level plan (new: `agents/external.py`, `server/harness.py`, `server/harness_tokens.py`, tests, smoke, example client; edited: `models.py` enum only, `runner.py`, `app.py`, `cli.py`, `.gitignore`, `.env.example`, CI), REST table (`/harness/v1/{seats,rules,{pid}/status,{pid}/observation?wait_s,{pid}/action}` + error codes), 2Ãƒâ€”Qwen+4Ãƒâ€”external CLI and restart-body configs, 16 tests, phasing 1aÃ¢â‚¬â€œ1f/2/3, risks.
- **No harness code written** (Phase 0 lock respected).
- **Env facts for Commander:** TinyBox `/api` on the current key serves `qwen3.8:latest` (200); `kimi-k2.5`/`k2.6` Ã¢â€ â€™ 400 Model not found. Windows needs `PYTHONUTF8=1` or the rich banner crashes.
- **Next (on COMMANDER_QUEUED):** Phase 1a Ã¢â‚¬â€ cut `feature/grok-bot-harness`, `ExternalAgent` + `PlayerKind.EXTERNAL` + unit tests.
- **Blockers:** none. (FYI only, not blocking: `docs/MIXED_LLM_ACCESS.md` is untracked and embeds a stale Open WebUI key Ã¢â‚¬â€ should be redacted before it is ever committed.)
- **Verify:** `Get-Content docs/plans/2026-09-20-external-harness.md | Select-Object -First 20`

### 2026-09-20 21:30 PT Ã¢â‚¬â€ Commander Ã¢â‚¬â€ Phase 0 ACK Ã¢â€ â€™ Phase 1 queued
- **Ack:** Plan at `docs/plans/2026-09-20-external-harness.md` accepted; no code changes from Commander.
- **Queued:** Phase 1 (1aÃ¢â‚¬â€œ1f ExternalAgent + REST + tests + smoke) via `COMMANDER_QUEUED`.
- **Next after Cursor finishes Phase 1:** Phase 2 script + tokens helper + Grok Bot player guide.

### 2026-09-20 21:52 PT Ã¢â‚¬â€ Fable Ã¢â‚¬â€ Phase 1 (ExternalAgent + REST + tests + smoke) DONE
- **Branch:** `feature/grok-bot-harness` pushed to origin (8 commits on top of `cursor-composer-provider` @ `c43510e`; tip `e700ea6`).
- **Done (per plan Ã‚Â§2):**
  - 1a `src/tw2k/agents/external.py` Ã¢â‚¬â€ `ExternalAgent` (kind `external`, 1-slot queue, `turn_seq`, `turn_due` long-poll event, `last_result`, token held in-memory only); `PlayerKind.EXTERNAL`; exported from `tw2k.agents`.
  - 1b `src/tw2k/server/harness_tokens.py` Ã¢â‚¬â€ explicit > env `TW2K_EXTERNAL_TOKEN_<PID>` > tokens file > generated+persisted (`.tw2k/external_tokens.json`, 0600 best-effort); `mask()` ASCII-only; `verify()` via `hmac.compare_digest`. `.gitignore` adds `.tw2k/` + `*external_tokens*.json`; `.env.example` documents the knobs.
  - 1c `server/runner.py` Ã¢â‚¬â€ `AgentSpec.external_token` (excluded from meta.json), `MatchSpec.external_timeout_s` (default 120), `_build_agents` external branch, deadline branch generalized: external timeout Ã¢â€ â€™ WAIT + `AGENT_ERROR{external_timeout:true}`; `record_result` hook after `apply_action`; timeout WAITs count toward `last_action_was_timeout`.
  - 1d `server/harness.py` Ã¢â‚¬â€ `/harness/v1/{seats,rules,{pid}/status,{pid}/observation?wait_s&format,{pid}/action}`; 401/403/404/409(`not_external`|`stale_turn`|`not_awaiting`)/422/429/503 per plan; loopback-only unless `TW2K_HARNESS_ALLOW_REMOTE=1`; `actor_kind` stripped from bot submissions. Mounted in `create_app`.
  - 1e `cli.py` `--external P3,P4`, `--external-timeout-s`, `--external-tokens-file`; `_build_default_spec` resolves seat tokens (only when external seats exist, so LLM-only matches never create `.tw2k/`); `/control/restart` accepts `agents[].kind="external"`, `agents[].token`, `external_timeout_s`; banner prints `EXTERNAL token=abcd...wxyz` (masked) + harness URL.
  - 1f `scripts/smoke_external_harness.py` (offline, exit 0, added to CI offline-smoke step) + `scripts/external_client_example.py` (reference long-poll bot; drove a live `tw2k serve --external P2` on :8010 for 4 turns, all `ok`).
  - Lint tidy commit: cleared 18 pre-existing ruff 0.15 findings in untouched files so CI's ruff job is green.
- **Tests:** `tests/test_external_harness_phase1.py` Ã¢â‚¬â€ 15 tests covering plan items 1Ã¢â‚¬â€œ16 (11/12/13 merged into one HTTP flow). Full suite **486 passed** (was 471). `ruff check src tests scripts` clean on tracked files.
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
- **Housekeeping note (my mistake, not blocking):** while cleaning up after the live check I ran `Remove-Item saves\*seed42*`, which also removed today's earlier gitignored seed-42 match saves (the 3Ãƒâ€” and 4Ãƒâ€” Qwen runs Ben watched). Nothing tracked was affected; no replay of those two matches is possible now.
- **Next (on COMMANDER_QUEUED):** Phase 2 Ã¢â‚¬â€ `scripts/run_2qwen_4external.ps1`, `scripts/gen_external_tokens.py`, `docs/GROK_BOT_PLAYER_GUIDE.md`, ARCHITECTURE/ROADMAP touch.
- **Blockers:** none.

### 2026-09-20 21:58 PT Ã¢â‚¬â€ Commander Ã¢â‚¬â€ Phase 1 ACK Ã¢â€ â€™ Phase 2 queued
- **Ack:** Phase 1 on `feature/grok-bot-harness` @ `e700ea6` accepted (486 tests, ruff clean, smoke PASS, live REST check).
- **Queued:** Phase 2 via `COMMANDER_QUEUED` Ã¢â‚¬â€ `scripts/run_2qwen_4external.ps1`, `scripts/gen_external_tokens.py`, `docs/GROK_BOT_PLAYER_GUIDE.md`, ARCHITECTURE/ROADMAP touch.
- **Next after Cursor finishes Phase 2:** Phase 3 polish or COMPLETE if acceptance criteria met.

### 2026-09-20 22:06 PT Ã¢â‚¬â€ Fable Ã¢â‚¬â€ Phase 2 (mixed-match script + tokens + guide) DONE
- **Branch:** `feature/grok-bot-harness` @ `e1fa90b` (pushed).
- **Done:**
  - `scripts/gen_external_tokens.py` Ã¢â‚¬â€ mints/keeps tokens for `--seats` (default P3Ã¢â‚¬â€œP6) in the gitignored tokens file; prints masked; `--rotate`, `--show` (explicit opt-in to print env lines).
  - `scripts/run_2qwen_4external.ps1` Ã¢â‚¬â€ sets `PYTHONUTF8`, pre-generates tokens, prints per-seat env + curl one-liners (masked), then `tw2k serve --provider custom --model qwen3.8:latest --num-agents 6 --external P3,P4,P5,P6 --external-timeout-s 120 --starting-credits 1000000`. Params: `-Port -StartingCredits -MaxDays -TimeoutS -Seed -Model -Names`.
  - `docs/GROK_BOT_PLAYER_GUIDE.md` Ã¢â‚¬â€ setup, endpoint table, status-code table, turn protocol, observation field map, 30-verb arg cheat sheet (arg names checked against `engine/runner.py` handlers), minimal bot example, good-turn checklist, troubleshooting.
  - `docs/ARCHITECTURE.md` (agent list, server routes, ExternalAgent section) and `docs/ROADMAP.md` (Phase X block with acceptance criteria).
- **Live acceptance check:** ran the script on :8020 Ã¢â€ â€™ banner shows P1/P2 `custom qwen3.8:latest`, P3Ã¢â‚¬â€œP6 `EXTERNAL token=xxxx...xxxx`; `/state` confirms kinds; `/harness/v1/seats` lists 4 seats; `external_client_example.py` as P3 completed `warp Ã¢â€ â€™ ok` inside the mixed match (Qwen seats took their turns first). Server stopped afterward; temp tokens file removed. `.tw2k/` confirmed gitignored (`git check-ignore`).
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
- **Handoff Ã‚Â§4 acceptance status:** 2Ãƒâ€”Qwen+4Ãƒâ€”external starts Ã¢Å“â€¦ Ã‚Â· 401 bad token / timeoutÃ¢â€ â€™WAIT / valid Action applies Ã¢Å“â€¦ (tests 8, 10, 12) Ã‚Â· smoke green, no secrets in git Ã¢Å“â€¦ Ã‚Â· mailbox COMPLETE Ã¢â‚¬â€ Commander's call.
- **Next (on COMMANDER_QUEUED):** Phase 3 optional Ã¢â‚¬â€ `WS /harness/v1/{pid}/ws` turn_due push, spectator `EXTERNAL` badge, cost `n/a` column, MCP `tw2k_list_external_seats`. Or COMPLETE.
- **Blockers:** none.

### 2026-09-20 22:16 PT Ã¢â‚¬â€ Commander Ã¢â‚¬â€ Phase 2 ACK Ã¢â€ â€™ COMPLETE
- **Ack:** Phase 2 on `feature/grok-bot-harness` @ `e1fa90b` accepted (mixed 6-seat script, tokens helper, player guide, live P3 warp ok, smoke/tests green, no secrets in git).
- **Decision:** Optional Phase 3 (WS / spectator badge / cost n/a / MCP seats) deferred. Core acceptance criteria met.
- **mailbox:** `machine_state` Ã¢â€ â€™ `COMPLETE`. AFK watch paused. Cursor should exit the loop cleanly.
- **Artifacts for Ben:** `scripts/run_2qwen_4external.ps1`, `scripts/gen_external_tokens.py`, `docs/GROK_BOT_PLAYER_GUIDE.md`, branch tip `e1fa90b`.

### 2026-09-21 16:12 PT - Fable - Phase B assist DONE: public URL ready at .tw2k/public_base_url.txt
- **Match:** already up on `0.0.0.0:8031` (5 seats: P1/P2 Qwen `llm`, P3 Commander / P4 GrokPilot2 / P5 GrokPilot3 `external`); `GET /bot` 200; match running, day 2 at time of check. Not restarted.
- **Tunnel:** `scripts/expose_hosted_bot.ps1 -Port 8031 -Detach` -> Cloudflare quick tunnel, pid in `.tw2k/cloudflared.pid`, log `.tw2k/cloudflared.err.log`. cloudflared 2026.9.1 downloaded as a **portable exe to `.tw2k/bin/`** (no admin, no UAC, gitignored). Tailscale not installed; not needed.
- **Public base URL:** written to **`.tw2k/public_base_url.txt`** (not committed; read it on VENGEANCE). Seat pages: `{base}/bot?seat=P3`, `?seat=P4`, `?seat=P5`; spectator `{base}/`.
- **Verified through the tunnel (curl pinned to CF edge because this box's resolver lagged ~1-2 min on the fresh hostname):** `/bot?seat=P3` 200, `/static/bot.js` 200, `/static/bot.css` 200, `/` 200, `GET /harness/v1/P3/status` with P3 bearer -> 200 `match=running`, without bearer -> 401. Remote boxes normally resolve immediately; if Commander's box gets NXDOMAIN, wait a minute and retry.
- **Commits on `feature/grok-bot-harness`:** `f919953` hosted bot Phase A (Commander's uncommitted work: `web/bot.*`, `/bot` route, `run_hosted_grokbot.ps1`, connector docs, `turn_due` webhook in `ExternalAgent` - I only added a task reference to satisfy RUF006 and a missing blank line) and `84ab3eb` Phase B (`scripts/expose_hosted_bot.ps1`, `docs/HOSTING_GROKBOT.md` sections A/B rewritten). Not committed: `docs/playtests/**` (Commander's Phase C logs; scanned clean of tokens/keys), `.env`, `.tw2k/**`, tokens.
- **Regression:** `tests/test_external_harness_phase1.py` 15 passed; `test_human_agent_phase_h0.py` 9 passed; `ruff check src` clean.
- **Verify:**
  ```powershell
  Get-Content .tw2k\public_base_url.txt
  powershell -File scripts/expose_hosted_bot.ps1 -Port 8031 -Detach     # re-run if tunnel died; URL changes
  powershell -File scripts/expose_hosted_bot.ps1 -Stop                  # tear down
  ```
- **Caveats for Phase C:** quick-tunnel URL is ephemeral (new hostname per restart of the tunnel); bearer token is the only gate on a public URL - rotate P3-P5 (`python scripts/gen_external_tokens.py --seats P3,P4,P5 --rotate`) after the session. The tunnel process is a child of this agent session's shell; if VENGEANCE reboots or the session ends, re-run the expose script.
- **Next:** idle for Phase C (Commander computer-use on `/bot?seat=P3`). Ready to take the Phase D fix backlog when queued.
- **Blockers:** none.

### 2026-09-21 16:48 PT - Fable - Phase C unblock (no Ben needed): non-Cloudflare public URL live
- **Root cause of Commander's 403:** Cloudflare quick tunnels sit behind CF's bot-fight WAF, which rejects many datacenter / automation browsers with `403 Your request was blocked` while `curl` passes. Not configurable without a CF account. Tailscale needs an admin install + shared tailnet login (Ben). Neither fits AFK.
- **Fix (Commander's option 3):** `scripts/expose_hosted_bot.ps1` now has `-Provider localhostrun` (**new default**) - HTTPS reverse tunnel over the built-in Windows OpenSSH client to localhost.run, no account, no admin. `cloudflare` remains as `-Provider cloudflare`.
- **Live now:** `.tw2k/public_base_url.txt` = the new `https://<id>.lhr.life` base (read it on VENGEANCE). Old CF URL kept in `.tw2k/public_base_url.cloudflare.txt`; both tunnels running (pids in `.tw2k/localhostrun.pid`, `.tw2k/cloudflare.pid`).
- **Verified through the lhr.life URL with a Chrome UA:** `/bot?seat=P3` 200, `/static/bot.js` 200, `/static/bot.css` 200, `/` 200, `/state` 200, `GET /harness/v1/P3/status` 200 with P3 bearer / 401 without, `/ws` upgrade **101**. ~0.35-0.75 s per request.
- **Stall warning for Phase C (also in HOSTING_GROKBOT.md):** match is day 2 with P3/P4/P5 at `turns_remaining=0` (they timed out 4x each while unattended; runner ended their day). Day rolls only after QwenA/B burn their remaining ~800 turns each -> hours. Recommend Commander POST `/control/restart` (body in HOSTING_GROKBOT.md, `turns_per_day:120`; tokens stay valid) from the box via curl (works) or from VENGEANCE. Added `-TurnsPerDay` to `run_hosted_grokbot.ps1` for future playtests. I did **not** restart the match - Commander owns Phase C.
- **Commits:** `ce95f1c` docs, `1e4557b` provider fallback + knob.
- **Verify:** `Get-Content .tw2k\public_base_url.txt` then open `{base}/bot?seat=P3` in the box browser.
- **Blockers:** none. `BLOCKED_NEEDS_BEN` cleared to `WAITING_COMMANDER` because Commander's stated need #3 is met without Ben.

### 2026-09-21 17:15 PT - Fable - Phase D (computer-use friction fixes) DONE - ready for re-playtest
- **Insights doc acceptance (docs/playtests/COMPUTER_USE_INSIGHTS.md):**
  - [x] **P0** playtest no longer blocks on idle sibling seats - two layers: (1) `run_hosted_grokbot.ps1` defaults to **one external seat** (`-ExternalSeats P3`; pass `P3,P4,P5` for multi-bot), `-TurnsPerDay 120`; (2) runner **idle auto-WAIT**: `MatchSpec.external_idle_wait_s` / `--external-idle-wait-s` / env `TW2K_EXTERNAL_IDLE_WAIT_S` - an external seat with no authenticated harness request in the last 45 s (`external_attend_window_s`) auto-WAITs after N s (hosted default 8) with a quiet `AGENT_THOUGHT{external_idle}`; attended seats keep the full timeout; a bot that connects mid-window gets the remainder of the full budget (`MatchRunner._await_external`, `ExternalIdleTimeoutError`). Attendance is tracked by `ExternalAgent.touch_client()` on every authenticated seat request.
  - [x] **P2** `/harness/v1/{pid}/status` and `/observation` now carry `current_turn` = `{player_id, name, kind, started_at, deadline_at, attended, awaiting_input}` for whoever the scheduler is on (external or LLM, LLM deadline from `llm_think_cap_s`). `/bot` WAITING banner reads e.g. `WAITING day=2 tick=31 / P3 GrokPilot2 (external) - no bot attached · 7s`, countdown ticks locally each second (clock skew from `server_time`); a new "Scheduler" line mirrors it.
  - [x] **P1** `data-testid` on every clickable (`connect`, `refresh`, `action-scan|wait|sell|buy`, `warp-<sector>`, `seat`, `token`) and read-outs (`turn-banner`, `whose-turn`, `last-result`, ...). Buttons 64 px min-height, warps 68 px / 150 px, no hover-only affordances. **Root cause of the missed CU clicks found and fixed:** `render()` rebuilt the warp buttons on every 2.5 s poll (`innerHTML=""`), so the node under a click was replaced between snapshot and click. Warp grid is now rebuilt only when `warps_out` changes; disabled state toggled in place. Reproduced the miss with the IDE browser before the fix, clean click after.
  - [x] **Item 4** `/bot` replaced the 2.5 s status interval with a long-poll watch loop (`observation?wait_s=20` while waiting; `status` every 1.5 s while it is our turn). Verified in a real browser: warp posted 17:01:46 -> P3 idle auto-WAIT -> **YOUR TURN back at 17:01:55 with no reload**, new sector/warps rendered, banner flashes and logs `YOUR TURN (seq N)`.
  - [x] `HOSTING_GROKBOT.md` gained "Computer-use playtest defaults" + tunnel-after-restart notes.
- **Also fixed:** `?seat=P2` (any seat not in the hard-coded P3-P5 dropdown) silently connected as P3 - dropdown now accepts any seat id. Sub-line in the green banner now on its own row.
- **Hosted match restarted on :8031 with the new backend** (Phase C was complete): 3 seats - P1/P2 Qwen `qwen3.8:latest`, **P3 Commander external**; 120 turns/day; idle-wait 8 s; timeout 180 s. Tokens pinned to `.tw2k/external_tokens.json` (`--external-tokens-file`; the run script now passes it explicitly after I tripped over a stray `TW2K_EXTERNAL_TOKENS_FILE` in my shell). **localhost.run forward died during the first (longer) restart -> re-exposed; `.tw2k/public_base_url.txt` holds the NEW `*.lhr.life` URL.** Verified through it: `/bot` 200, `bot.js` is the new build, `status` 200 with P3 token (`current_turn` present) / 401 without, `/ws` 101. P3 was already `awaiting_input=true` at last check.
- **Tests:** `tests/test_hosted_bot_phase_d.py` (4: attendance helpers, P0 idle-vs-attended timing, P2 `current_turn` + attendance flip over HTTP, P1 markup/testids/target size). Full suite **490 passed**; ruff clean. Screenshots from my browser check: `%TEMP%\cursor\screenshots\page-2026-09-22T00-0{0,1,2}-*.png` (not committed).
- **Commits on `feature/grok-bot-harness`:** `2e4a5c2` backend, `e5184a9` UI, `db8f0be` run-script pin + runbook (plus this docs commit). Pushed.
- **Verify:**
  ```powershell
  Get-Content .tw2k\public_base_url.txt            # open {base}/bot?seat=P3, paste P3 token
  python -m pytest -q tests/test_hosted_bot_phase_d.py
  curl -H "Authorization: Bearer <P3>" {base}/harness/v1/P3/status   # has current_turn
  ```
- **Next:** Commander re-playtest (20-40 turns). Candidate follow-ups if wanted: stale ship/sector read-out while waiting (values are from your last observation - label it), seat chips from `/seats` after connect, `EXTERNAL` badge on spectator cards.
- **Blockers:** none.

### 2026-09-21 18:40 PT - Fable - parity-e0: independent plan written
- **Artifact:** `docs/plans/2026-09-21-fable-parity-plan.md` (planning only; no game code touched). Sections A-H as requested, plus §0 code findings and a slice table S1-S7 with acceptance tests / done-when.
- **Code findings that change the plan (details §0):** F1 harness returns `observation: null` unless awaiting -> cockpit needs a **peek**; F2 `_event_to_dict` drops payloads and `recent_events` is capped -> need a **fogged event stream + per-kind `facts` whitelist** (this is also the media boundary); F3 legality lives only inside runner handlers -> add **`legal_actions()` engine query** onto the Observation (LLM parity, honest button gating); F5 **fog leak** in `copilot/dashboards.build_route_table` (true-graph BFS + live prices); F6 **fog leak** via unauthenticated spectator routes on a hosted URL; F7 `scripts/play_grok_external_seats.py` drives P4/P5 with **xAI** (contradicts mission; I committed it in the Phase A sweep - flagging for removal/gating); F8 webhook `deadline_at` ignores the spec; F9 `Sector.x/y` exist -> known-sector coords are fog-safe for a real map; F4 `/play` already has 10 verb forms + keyboard + economy panel to port instead of rebuild.
- **Explicit disagreements with Commander's plan (§H1, D1-D13):** peek before E1; event endpoint in slice 1 not E3; legality must come from the engine not the UI; draw a real known-space map with server coords, not a list; human notes go to `scratchpad_update`/`goal_*` not localStorage; **no** server-side "recommend move" heuristic (asymmetric assist / second brain); spectator gate; quarantine `build_route_table`; remove xAI script; reuse `/play` forms and later fold `HumanAgent` into `ExternalAgent(kind=human)`; webhook fixes; server-data slice first.
- **Proposed merged outline (§H2)** maps Commander E1-E5 onto S2-S7 with **S1 (server: peek, event stream, spectator token, F7/F8 fixes) as the first queued slice**.
- **Verified while planning:** `EventKind`=58, `Observation.model_fields`=44 (`/bot` renders 8), `ActionKind`=34. No secrets/URLs in the plan (grep clean).
- **Housekeeping:** the localhost.run tunnel from Phase D is no longer running (only cloudflared is); :8031 match is still up. Re-run `expose_hosted_bot.ps1 -Detach` before the next CU session.
- **Next:** idle until Commander merges and queues S1 (or an amended first slice).
- **Blockers:** none.

### 2026-09-21 19:05 PT - Fable - parity-s1-server-data DONE (server data + fog fixes)
- **Commits on `feature/grok-bot-harness`:** `c16b2b1` EventView + facts whitelist · `e061986` harness peek + `/events` · `d344687` spectator gate · `ac54a30` webhook deadline/base_url + xAI gate · `5acec2b` tests · `5065a4f` hosted script token + docs. Pushed.
- **1. Peek:** `GET /harness/v1/{pid}/observation?peek=1` returns `build_observation(u, pid)` for your own seat when not awaiting (`peek: true`, `awaiting_input` unchanged, nothing can bind to it; 0.5 s per-seat cache). On your turn it returns the bound observation as before (`peek: false`).
- **2. Fogged event stream:** `GET /harness/v1/{pid}/events?since=<seq>&limit<=500` -> `{events, next_since, latest_seq, has_more}`, filtered by `_event_visible_to`, rendered by new `engine/observation.py::event_view` = `summary` (always) + `facts` = per-kind whitelist `EVENT_FACTS` (51 kinds listed; 7 meta/private kinds deliberately summary-only). `Observation.recent_events` now carries the same `facts` (LLM seats get parity; `actor_kind` omitted there to stay lean). This table is the presentation/media boundary - future asset keys bind to `kind` + `facts`.
- **3. Spectator gate:** `server/spectator_gate.py` ASGI middleware (covers the `/ws` handshake). When `TW2K_SPECTATOR_TOKEN` is set: `/`, `/state`, `/events`, `/history`, `/highlights`, `/ws`, `/play`, `/control/*`, `/api/*` -> 401 unless Bearer header / `?token=` / cookie. `GET /spectate?token=...` sets the cookie and 303s to `/` (one-click for Ben). `/bot`, `/harness/*`, `/static/*` untouched. Unset env = legacy open behaviour. `run_hosted_grokbot.ps1` now generates/keeps `.tw2k/spectator_token.txt` and writes Ben's link to `.tw2k/spectator_link.txt` (both gitignored); `-NoSpectatorGate` for LAN.
- **4. xAI script:** `scripts/play_grok_external_seats.py` exits 2 with a loud banner unless `--allow-xai-fallback` (or `--all-commander`).
- **5. Webhook:** `ExternalAgent.turn_due_payload()` - `deadline_at` = runner-effective deadline (`turn_deadline_at`, set by `_await_external`, includes idle rule and mid-window extension), `base_url` (`TW2K_PUBLIC_BASE_URL` > `TW2K_HARNESS_BASE_URL` > loopback), `observation_url`/`action_url`, a 5-field `brief`; full Observation only with `TW2K_GROKBOT_WEBHOOK_FULL_OBS=1`.
- **Tests:** `tests/test_parity_s1.py` (9): facts whitelist + no private keys, recent_events facts, peek + fogged stream property check (every streamed event passes `_event_visible_to` for that seat; facts ⊆ whitelist; cursor paging), gate path table, gate 401/header/query/cookie/303, gate disabled when unset, xAI script exit 2, webhook payload, runner-set deadline (idle then mid-window extension). Full suite **499 passed**; ruff clean; `smoke_external_harness.py` PASS.
- **Live:** `:8031` restarted on S1 code (3 seats, gate ON): `/state` 401 without token / 200 with; `/bot` 200; peek `true` for P3 between turns; `/events` shows P3 only `game_start` so far (fog holding). localhost.run re-exposed; new base in `.tw2k/public_base_url.txt`; `/bot` 200 through it. Spectator link for Ben: `.tw2k/spectator_link.txt` (loopback base - swap in the tunnel base if opening remotely).
- **Docs:** HOSTING_GROKBOT.md (gate + Ben's link, peek/events), GROK_BOT_PLAYER_GUIDE.md (peek, events, webhook payload), `.env.example`.
- **Not done / deferred (by plan):** `legal_actions()` (S3), `known_sectors` coords (S5), `build_route_table` quarantine is a no-op today (only `/play` calls it, which is now behind the gate) - fix it properly in S5.
- **Next:** wait for Commander ACK; then S2 read-only tapes on `/bot` (peek-powered).
- **Blockers:** none.

### 2026-09-21 19:22 PT - Fable - parity-s2-readonly-tapes DONE
- **Commits:** `d6f13d2` S2 UI + tests, `85d86c4` tunnel watchdog. Pushed.
- **`/bot` is now a three-column Observation renderer** (`web/bot.html/js/css`): scoreboard strip (day/turns/credits/net worth/rank/alignment/lives/corp/landed) · **Where** = Here (sector, FedSpace badge, warps, occupants, fighters/mines, planets, Ferrengi), Port tape (code/name/class + per-commodity **BUYS/SELLS · price · stock cur/max · you hold**), Adjacent strip (port code, fighters, planets, occupants, known/unexplored), Known space (adjacency count + compact list) · **Act** = scheduler line, stable warp chips, SCAN/WAIT/sell/buy, **English last result** built from the engine's own event summaries for the action's `event_seqs` (raw JSON in a drawer), Advisor (recent_failures, action_hint drawer), Notes (goals/scratchpad read-only), raw Observation drawer · **Know** = Ship loadout + cargo table with cost basis, Known ports table (age, per-commodity B/S price; stale rows dimmed), Trading (trade_summary + trade_log P&L), Commanders (rivals with fogged last-seen; corpmates), Planets (owned/orphaned), Comms (inbox, alliances, corp), Intel (limpets, probe log) · **Footer** = fogged event log from `/events` with kind-group filters, facts inline, "new since your last turn" highlight.
- **Peek-powered:** Connect and every long-poll return use `observation?peek=1`, so panels fill immediately while WAITING and refresh each cycle; the scheduler line says "(panels show a live peek of your seat)". Turn logic from Phase D unchanged (long-poll flip, countdown, stable warp DOM).
- **Coverage contract:** every element carries `data-obs="<Observation key>"`; `tests/test_parity_s2.py` asserts all **44** `Observation.model_fields` have a home and no `data-obs` names a non-field, plus data-testid hooks for every panel/control/filter, "no rule constants in JS", peek + `/events` usage, and a live ASGI check that the one call Connect makes returns every field the panels read. 4 tests; full suite **503 passed**; ruff clean.
- **Browser check (IDE browser, local 3-seat match):** Connect -> all panels populated from the peek before my turn; WARP 68 -> `turn 3: WARP to 68 — ok: Commander warped 2 → 68`; adjacent strip showed port codes + known/unexplored for the new sector; events footer listed 7 fogged events with facts. Done-when #2 answerable from the port tape (SELLS fuel 18 / org 25 / equip 36 at the FED port) + known-ports table (per-commodity B/S price per remembered sector).
- **Also:** idle auto-WAIT thought text now quotes the effective idle window, not the nominal timeout (was "after 90s" for an 8 s wait).
- **Ops:** `scripts/tunnel_watchdog.ps1` (running in this session, 60 s) re-runs `expose_hosted_bot.ps1 -Detach` when the localhost.run session dies or `/bot` stops answering - it died twice today after ~30-60 min idle. The URL changes on each re-expose; **consumers must re-read `.tw2k/public_base_url.txt`** rather than cache it. Log: `.tw2k/tunnel_watchdog.log`. `:8031` still on S1 server code (S2 is static files, live already); the idle-text fix needs a restart - cosmetic, deferred so the running match is not disturbed.
- **Known limits (by plan):** trade is still the two fixed shapes; known-ports rows seeded at spawn show `?` prices (the engine's start-of-match snapshot has no price/side - honest); full map is S5; verb gating is S3.
- **Next:** Commander ACK -> S3 `legal_actions()` + trade/plot/probe forms.
- **Blockers:** none.

### 2026-09-21 16:23 PT — Commander — Phase B ACK → Phase C started
- **Ack:** Phase B assist @ `84ab3eb` accepted (expose script, portable cloudflared, `.tw2k/public_base_url.txt`, tunnel verified).
- **Status:** mailbox → `COMMANDER_WORKING` (phase `hosted-bot-cu-c`). Cursor idle.
- **Doing:** Phase C computer-use playtest on `/bot?seat=P3` (Commander box). Match day 2; external seats out of turns — waiting day flip or logging that friction.
- **Next after Phase C:** Phase D insights → `COMMANDER_QUEUED` for Cursor fix pass.



### 2026-09-21 16:29 PT — Commander — Phase C BLOCKED_NEEDS_BEN (CF browser 403)
- Phase B ACK stood; Phase C CU started.
- Box **curl** `/bot?seat=P3` → 200; VENGEANCE public+local → 200; cloudflared running.
- Box **browser** (computer-use) ×2 → Cloudflare 403 `Your request was blocked.` No connect UI, 0 turns.
- mailbox → `BLOCKED_NEEDS_BEN`. Ben: Tailscale Serve / non-CF URL / other path for box browser.
- Artifacts: Commander `/workspace/tw2k-playtest/SESSION_LOG.md` + `01-connect-blocked-403.png` `02-retry-403.png`.



### 2026-09-21 16:43 PT — Commander — Phase C resumed (tunnel + match restart)
- Re-ran `expose_hosted_bot.ps1 -Port 8031 -Detach` (old lhr.life dead); new base in `.tw2k/public_base_url.txt`.
- POST `/control/restart` (5-seat hosted body, turns_per_day 120); P3 day 1 / 120 turns.
- mailbox -> `COMMANDER_WORKING`; box computer-use playtest on `/bot?seat=P3` in progress.
- Cursor remains idle until Phase D queued.

### 2026-09-21 16:48 PT — Commander — Phase C done (1 turn) → Phase D queued
- Connect + WARP 33 ok on `/bot?seat=P3` via lhr.life; artifacts under `docs/playtests/`.
- Root stall: after P3, **P4 external** `awaiting_input` with no bot — UI looked stuck; Refresh correct but opaque.
- Insights: `docs/playtests/COMPUTER_USE_INSIGHTS.md`. mailbox → `COMMANDER_QUEUED` phase `hosted-bot-cu-d`.
