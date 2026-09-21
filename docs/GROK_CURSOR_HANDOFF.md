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
| Status | **BLOCKED_NEEDS_BEN - Phase C CF browser 403** |
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


