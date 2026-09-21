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
| Status | **AFK LOOP — Phase 1 queued** |

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
