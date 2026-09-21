# External harness plan — `ExternalAgent` + localhost REST for Grok Bot seats

**Date:** 2026-09-20 (PT)
**Author:** Fable (Cursor) for Commander
**Phase:** 0 — plan only. No harness code in this commit.
**Branch for Phase 1+:** `feature/grok-bot-harness` (cut from `cursor-composer-provider`, which is what `main` should fast-forward to; Commander decides merge order).

Architecture lock (from `docs/GROK_CURSOR_HANDOFF.md` §2) is honoured throughout:
`ExternalAgent` + localhost REST + bearer tokens; keep `custom` Qwen seats; engine stays pure; tokens gitignored.

---

## 0. Ground truth I verified before planning

| Fact | Where |
|---|---|
| Agent contract is `BaseAgent.act(Observation) -> Action`, plus optional `close()` | `src/tw2k/agents/base.py` |
| `HumanAgent` already implements "block on an `asyncio.Queue` until an HTTP route pushes an Action" | `src/tw2k/agents/human.py` |
| Scheduler is a serial round-robin; human slots get `HUMAN_TURN_START` + optional `asyncio.wait_for(agent.act, human_deadline_s)` → synthesized WAIT on timeout | `src/tw2k/server/runner.py::_run` (~L500–600) |
| Kind dispatch lives in `MatchRunner._build_agents` (`llm` / `human` / else heuristic) | `runner.py` ~L892–911 |
| Per-slot overrides flow `CLI --agent-providers/--human` → `agent_overrides[]` → `_build_default_spec` → `AgentSpec(kind, provider, model, custom_*)` | `cli.py` L253–276, `app.py` L1062–1094 |
| `/control/restart` accepts the same `agents[]` list at runtime | `app.py` L879 |
| `PlayerKind` enum = `heuristic | llm | human`; `Player.agent_kind` is a plain `str` | `engine/models.py` L66–84, L428 |
| `Event.actor_kind` auto-resolves from `Player.agent_kind` | `models.py` L777–788 |
| `meta.json` persists `kind/provider/model` per agent (never secrets today) | `runner.py::_open_save_sink` L288–297 |
| Existing bearer-auth pattern (optional `TW2K_MCP_TOKEN`) + `httpx` client shape to mirror | `src/tw2k/mcp_server.py::TwkHttpClient` |
| Reference test style for a blocking agent + runner integration | `tests/test_human_agent_phase_h0.py` |
| TinyBox `/api` router on the current key exposes `qwen3.8:latest` (200 on chat). `kimi-k2.5`/`k2.6` → `400 Model not found` | probed 2026-09-20 19:3x PT |
| Windows console needs `PYTHONIOENCODING=utf-8` / `PYTHONUTF8=1` or `rich` crashes on the banner | reproduced 2026-09-20 |

Nothing in `engine/` needs behavioural change. The only engine-package edit is adding an enum member.

---

## 1. Design summary

An **external seat** is a player whose actions come from a process outside the server (a Grok Bot). The server never calls out to the bot. The bot **pulls** its observation and **pushes** one action per turn over loopback HTTP, authenticated with a per-seat bearer token.

```
 Grok Bot (any language)                         tw2k serve (127.0.0.1:8000)
 ───────────────────────                          ──────────────────────────────
 loop:                                            scheduler round-robin
   GET /harness/v1/P3/observation?wait_s=30  ───►   ExternalAgent.act(obs):
        (long-poll; returns as soon as it's           store obs, bump turn_seq,
         P3's turn, or after wait_s)                  set turn_due event,
   ◄──  {awaiting_input:true, turn_seq:17, obs}      await queue.get() w/ timeout
   think…
   POST /harness/v1/P3/action {turn_seq:17, action}►  queue.put → act() returns
   ◄──  {accepted:true}                              apply_action(...) as usual
                                                      record_result → visible on
   GET /harness/v1/P3/status  ◄── last_result         next status/observation
```

Why this shape:

- **Pull, not push.** No callback URLs, no bot-side server, no firewall story. A Grok Bot is just an HTTP client.
- **Same `apply_action` path** as every other agent → determinism, replay, fog-of-war, `actor_kind` tagging, save sink all keep working with zero special cases.
- **`HumanAgent` is the template.** `ExternalAgent` is a `HumanAgent` with (a) a `turn_seq` so stale submissions are rejected, (b) an `asyncio.Event` for long-poll, (c) a per-seat token, (d) `last_result` feedback.
- **Timeout is a runner concern**, exactly like `human_deadline_s` today. On timeout the runner synthesizes a WAIT and emits `AGENT_ERROR`. The existing 4-WAIT streak guard then ends that seat's day, so a dead bot cannot stall the match forever.

---

## 2. File-level plan (Phase 1 unless tagged)

### 2.1 New files

| File | Purpose |
|---|---|
| `src/tw2k/agents/external.py` | `ExternalAgent(BaseAgent)`, `kind = "external"`. Queue + `turn_seq` + `turn_due: asyncio.Event` + `current_observation` + `last_result` + `token` (stored, never serialized). `submit_action(action, turn_seq=None)` raises `StaleTurnError` / `NotYourTurnError` / `QueueFullError`. `act(obs)` sets state, fires event, `await queue.get()` (no timeout inside — runner owns the deadline), clears `awaiting` on return. `wait_for_turn(timeout_s)` for long-poll. `record_result(ok, error, event_seqs)`. `close()` drains + sets a `closed` flag so long-pollers wake and get 503. |
| `src/tw2k/server/harness.py` | `APIRouter(prefix="/harness/v1")`. Dependency `require_seat(player_id, request)` → resolves `ExternalAgent`, checks loopback, verifies `Authorization: Bearer` with `hmac.compare_digest`. Routes in §3. Mounted from `create_app` via `app.include_router(build_harness_router(runner))`. |
| `src/tw2k/server/harness_tokens.py` | Token provisioning: `resolve_seat_tokens(agent_specs) -> dict[player_id, token]`. Order: explicit `AgentSpec.external_token` → env `TW2K_EXTERNAL_TOKEN_<PID>` → tokens file (`TW2K_EXTERNAL_TOKENS_FILE`, default `.tw2k/external_tokens.json`) → generate `secrets.token_urlsafe(32)` and **write it to the tokens file** (create dir, `0o600` where the OS honours it). `mask(token)` helper (`abcd…wxyz`). |
| `tests/test_external_harness_phase1.py` | See §5. |
| `scripts/smoke_external_harness.py` | Offline smoke (no LLM): in-process app, 1 heuristic + 1 external seat, scripted client drives 6 turns via `httpx`, asserts 401/403/409/200 paths + `AGENT_ERROR` on forced timeout. Exit 0/1. Added to CI's offline smoke step. |
| `scripts/external_client_example.py` | Reference bot any Grok Bot can copy: env `TW2K_HARNESS_URL`, `TW2K_HARNESS_PLAYER`, `TW2K_HARNESS_TOKEN`; long-polls, picks a legal warp or trade from `sector.warps_out` / `sector.port`, posts with `turn_seq`, prints `last_result`. ~120 lines, stdlib + httpx only. |
| `scripts/run_2qwen_4external.ps1` **(Phase 2)** | Starts the canonical 6-seat match (§4), prints masked tokens + per-seat curl one-liners. |
| `scripts/gen_external_tokens.py` **(Phase 2)** | Pre-generates `.tw2k/external_tokens.json` for P3–P6 so bots can be configured before the server boots. |
| `docs/GROK_BOT_PLAYER_GUIDE.md` **(Phase 2)** | Endpoint reference, auth, turn protocol, action schema + verb table, legal-move cheat sheet, error codes, example loop, "what a good turn looks like". |

### 2.2 Edited files (surgical)

| File | Change |
|---|---|
| `src/tw2k/engine/models.py` | `PlayerKind.EXTERNAL = "external"` + docstring line. **Only engine edit.** |
| `src/tw2k/agents/__init__.py` | export `ExternalAgent`. |
| `src/tw2k/server/runner.py` | `AgentSpec`: add `external_token: str | None = None` (never written to `meta.json`; add explicit comment). `MatchSpec`: add `external_timeout_s: float = 120.0`. `_build_agents`: `elif ag.kind == "external": ExternalAgent(player_id, name, token=...)`. `_run`: generalize the deadline block — `is_external = agent.kind == "external"`; `deadline = human_deadline_s if is_human else (external_timeout_s if is_external else None)`; on `TimeoutError` for external → WAIT with thought `"[external timeout] no action from client within Ns"` **and** emit `AGENT_ERROR` (human path keeps `AGENT_THOUGHT`). Emit `EXTERNAL_TURN_START`? — **No**: reuse `HUMAN_TURN_START` semantics via a new generic `TURN_START` would touch the UI; instead emit `HUMAN_TURN_START` only for humans (unchanged) and let external seats signal via the harness long-poll. After `apply_action`, call `getattr(agent, "record_result", None)` if present. |
| `src/tw2k/server/app.py` | `create_app(..., external_timeout_s: float | None = None)`; `_build_default_spec` passes `external_token=ov.get("token")` and `external_timeout_s`; `/control/restart` reads `external_timeout_s` from body. `app.include_router(build_harness_router(runner))`. Startup log line listing external seats with **masked** tokens. |
| `src/tw2k/cli.py` | `--external P3,P4,P5,P6` (mirrors `--human`: forces `kind=external`, strips provider/model), `--external-timeout-s` (default 120), `--external-tokens-file`. Banner: `P3: EXTERNAL (GET/POST /harness/v1/P3/...) token=abcd…wxyz`. `agent_kind` help string gains `external`. |
| `src/tw2k/server/replay.py` | No logic change; `AgentSpec(kind="external")` round-trips through meta.json already. Add a one-line test. |
| `web/app.js` **(Phase 3)** | Player card badge `EXTERNAL` (like the LLM/heuristic tag), cost column shows `n/a`. |
| `.gitignore` | `.tw2k/` and `*external_tokens*.json`. |
| `.env.example` | `TW2K_EXTERNAL_TIMEOUT_S`, `TW2K_EXTERNAL_TOKENS_FILE`, `TW2K_EXTERNAL_TOKEN_P3=` (commented), `TW2K_HARNESS_ALLOW_REMOTE=0`. |
| `.github/workflows/ci.yml` | add `python scripts/smoke_external_harness.py` to the offline smoke step. |
| `docs/ARCHITECTURE.md` | Agent list gains `ExternalAgent`; server section gains `/harness/v1/*`. |
| `docs/ROADMAP.md` | New "Phase X — External harness" block with the acceptance criteria from the handoff. |

---

## 3. REST API (`/harness/v1`, loopback only)

All routes require `Authorization: Bearer <seat token>` except where noted. All JSON. Errors are FastAPI-style `{"detail": "..."}`.

| Method & path | Purpose | Success | Errors |
|---|---|---|---|
| `GET /harness/v1/seats` | List external seats: `[{player_id, name, alive, awaiting_input, turn_seq}]` | 200 | 401 (any valid seat token accepted), 503 no match |
| `GET /harness/v1/rules` | `{system_prompt, verbs:[...], action_schema (Action JSON schema), notes}` so a bot sees the same rules an LLM seat does | 200 | 401 |
| `GET /harness/v1/{pid}/status` | `{player_id, name, alive, match_status, day, tick, turns_remaining, awaiting_input, turn_seq, deadline_at (epoch s or null), pending, last_result}` | 200 | 401, 403 wrong seat, 404 no such player, 409 not external, 503 |
| `GET /harness/v1/{pid}/observation?wait_s=0..60&format=json\|llm\|both` | If not awaiting and `wait_s>0`: long-poll on `turn_due` up to `wait_s`. Returns `{awaiting_input, turn_seq, deadline_at, observation: Observation.model_dump(mode="json") \| null, llm_user_message: str \| omitted}` | 200 | as status |
| `POST /harness/v1/{pid}/action` body `{turn_seq?: int, action: {kind, args, thought?, scratchpad_update?, goal_short?, goal_medium?, goal_long?}}` | Push the action for the current turn | 200 `{accepted:true, turn_seq}` | 401/403/404/409(not external) · **409 `stale_turn`** (turn_seq mismatch; body includes `current_turn_seq`) · **409 `not_awaiting`** (scheduler isn't on this seat and no queue slot) · 422 invalid Action · 429 queue full · 503 |
| `WS /harness/v1/{pid}/ws` **(Phase 3, optional)** | Push `turn_due` / `result` frames | — | — |

Design notes:
- `actor_kind` on emitted events resolves to `"external"` automatically via `Player.agent_kind`. Bots **cannot** set `action.actor_kind` (the route strips it) — only the copilot path may override.
- `pid` in the path must match the seat the token was issued for, else 403. Prevents one bot from moving another's ship.
- Loopback check: `request.client.host in {"127.0.0.1", "::1"}` unless `TW2K_HARNESS_ALLOW_REMOTE=1`. Belt-and-braces on top of `--host 127.0.0.1`.
- The observation payload is the same `Observation` object LLM seats get (same fog-of-war). `format=llm` adds the exact `format_observation()` string so a Grok Bot can be prompted identically to an LLM seat if desired.
- `deadline_at` lets the bot budget its thinking time against `external_timeout_s`.

---

## 4. Match configuration — 2× Qwen + 4× external

**CLI (Phase 1):**
```powershell
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"
tw2k serve `
  --provider custom --model qwen3.8:latest `
  --num-agents 6 `
  --agent-names "QwenA,QwenB,GrokBot1,GrokBot2,GrokBot3,GrokBot4" `
  --external P3,P4,P5,P6 `
  --external-timeout-s 120 `
  --starting-credits 1000000 --max-days 15 --port 8000
```
Slots P1–P2 resolve to `kind=llm, provider=custom` from `.env` (`TW2K_CUSTOM_BASE_URL=https://tinybox.silverstarindustries.com/api`, `TW2K_CUSTOM_MODEL=qwen3.8:latest`). Slots P3–P6 become `ExternalAgent`s; tokens come from `.tw2k/external_tokens.json` (generated on first boot if absent).

**`/control/restart` body (equivalent):**
```json
{
  "num_agents": 6,
  "provider": "custom",
  "model": "qwen3.8:latest",
  "agent_kind": "llm",
  "starting_credits": 1000000,
  "max_days": 15,
  "external_timeout_s": 120,
  "agents": [
    {"name": "QwenA", "provider": "custom", "model": "qwen3.8:latest"},
    {"name": "QwenB", "provider": "custom", "model": "qwen3.8:latest"},
    {"name": "GrokBot1", "kind": "external", "token": "<from tokens file>"},
    {"name": "GrokBot2", "kind": "external", "token": "<from tokens file>"},
    {"name": "GrokBot3", "kind": "external"},
    {"name": "GrokBot4", "kind": "external"}
  ]
}
```
Omitting `token` on an external slot → server resolves/generates and persists it to the tokens file (never to `meta.json`, never to stdout unmasked).

**Bot side (each Grok Bot):**
```
TW2K_HARNESS_URL=http://127.0.0.1:8000
TW2K_HARNESS_PLAYER=P3
TW2K_HARNESS_TOKEN=<its token>
python scripts/external_client_example.py
```

`scripts/run_2qwen_4external.ps1` (Phase 2) wraps the CLI above, pre-generates tokens, and prints the four bot env blocks with masked tokens.

---

## 5. Tests (`tests/test_external_harness_phase1.py`)

Unit (no server):
1. `PlayerKind("external")` round-trips; `Player(agent_kind="external")` events carry `actor_kind == "external"`.
2. `ExternalAgent.act()` blocks until `submit_action`; returns the submitted Action; `turn_seq` increments per `act()`.
3. Stale `turn_seq` → `StaleTurnError`; submit while not awaiting → `NotYourTurnError`; second submit same turn → `QueueFullError`.
4. `wait_for_turn(0.05)` returns `False` when idle, `True` once `act()` is entered.
5. `record_result()` surfaces in `last_result`.
6. `harness_tokens.resolve_seat_tokens`: explicit > env > file > generated; generated token is persisted; file written once; `mask()` never returns more than 4+4 chars of the secret.

Runner integration (real `MatchRunner`, `GameConfig(universe_size=40, turns_per_day=12, max_days=2)`, 1 heuristic + 1 external):
7. Scheduler reaches the external seat, `awaiting_input` flips true, a submitted `warp` to a legal `warps_out` target changes `player.sector_id`.
8. With `external_timeout_s=0.2` and no client: `AGENT_ERROR` emitted with `[external timeout]`, WAIT applied, and after 4 consecutive timeouts the seat's day ends (`turns_today == turns_per_day`).
9. `meta.json` for the run contains `kind: "external"` and **no** `token` key anywhere (recursive assert).

HTTP (httpx `ASGITransport` against `create_app(auto_start=False)` then `runner.start(spec)`):
10. Missing bearer → 401; wrong token → 401; valid token for P2 used on `/P3/...` → 403; heuristic seat → 409; unknown → 404; before match → 503.
11. `GET observation?wait_s=2` long-poll returns `awaiting_input: true` with a full observation when it's the seat's turn; `format=llm` includes `llm_user_message`.
12. `POST action` with matching `turn_seq` → 200 and the event feed shows the action; mismatched → 409 `stale_turn` with `current_turn_seq`.
13. `POST action` with `actor_kind: "copilot"` in the body is stripped (event `actor_kind == "external"`).
14. `GET rules` returns the current `get_system_prompt()` text and the 34 verbs from `ActionKind`.
15. `_build_default_spec` with `agents=[{}, {}, {"kind":"external"}, …]` yields the right `AgentSpec.kind` list; CLI `--external P3,P4` produces `kind=external` overrides without provider/model.
16. Non-loopback `request.client.host` → 403 unless `TW2K_HARNESS_ALLOW_REMOTE=1` (monkeypatched client host).

Regression guard: full suite (`471` collected today) must stay green; `ruff check src tests scripts` clean.

---

## 6. Phasing & commits (branch `feature/grok-bot-harness`)

| Phase | Commits (small, each green) | Exit |
|---|---|---|
| 1a | `ExternalAgent` + `PlayerKind.EXTERNAL` + unit tests 1–5 | pytest green |
| 1b | tokens module + `.gitignore` + `.env.example` + tests 6 | no secret in git (`git grep -n external_tokens` shows only ignore rules) |
| 1c | runner wiring (`AgentSpec.external_token`, `MatchSpec.external_timeout_s`, `_build_agents`, timeout branch, `record_result`) + tests 7–9 | integration green |
| 1d | harness router + `create_app` mount + tests 10–14, 16 | HTTP green |
| 1e | CLI flags + `_build_default_spec` + `/control/restart` + test 15 + banner | `tw2k serve --external P2 --agent-kind heuristic` boots |
| 1f | `scripts/smoke_external_harness.py` + `scripts/external_client_example.py` + CI step | smoke exit 0 locally + CI |
| 2 | `run_2qwen_4external.ps1`, `gen_external_tokens.py`, `GROK_BOT_PLAYER_GUIDE.md`, ARCHITECTURE/ROADMAP touch | Commander can start a 6-seat match from the script |
| 3 (optional) | WS turn_due, spectator `EXTERNAL` badge + cost `n/a`, MCP tool `tw2k_list_external_seats` | nice-to-have |

Each phase ends with a handoff Changelog entry (Done / Next / Blockers / verify commands) and `WAITING_COMMANDER`.

---

## 7. Risks & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Serial scheduler × 4 slow bots × 120 s timeout | one round-robin could take 8+ min; Qwen seats starve | `deadline_at` in payloads; guide recommends ≤30 s decisions; timeout default 120 s but `--external-timeout-s 45` for demos; 4-WAIT streak guard ends a dead bot's day; Phase 3 could parallelize *observation build* but not `apply_action` (engine is serial by design) |
| Bot posts for the wrong turn (race after timeout) | wrong-context action | `turn_seq` echo required to be current; stale → 409 with `current_turn_seq` so the bot resyncs |
| Token leakage | anyone on the box can drive a seat | tokens only in `.tw2k/` (gitignored, 0600), masked in logs/banner, never in `meta.json`/events; loopback check; `compare_digest` |
| `/control/restart` regenerates tokens → bots lose auth | bots stuck at 401 | tokens are keyed by `player_id` in the file and re-read on every restart; only *missing* seats get new tokens |
| Two external seats share a token by copy-paste | 403 confusion | `seats` endpoint + startup banner show masked tokens per seat; guide has a checklist |
| Windows `cp1252` console crash on the rich banner | server dies at boot | run scripts set `PYTHONUTF8=1`; document in guide (already bit us today) |
| Qwen seats on TinyBox `/api`: only `qwen3.8:latest` is enabled on this key; Kimi returns 400 | mixed match can't include Kimi | plan uses `qwen3.8:latest`; `MIXED_LLM_ACCESS.md` needs a correction note (the committed key there is stale and should be rotated — flagged to Ben already) |
| Observation JSON is large (~6 KB LLM view, ~15 KB raw) | bot token/latency cost | `format=json\|llm\|both` lets the bot choose; long-poll avoids re-fetching |
| `HUMAN_TURN_START`-dependent UI code assumes `kind=="human"` | none for external | we do **not** emit `HUMAN_TURN_START` for external seats; `/play` unaffected |
| `_is_day_done` / OOT guards | already generic on `Player`, not on kind | no change; covered by test 8 |

---

## 8. Out of scope (explicit)

- Public/remote multiplayer, WebRTC voice, accounts.
- Server-initiated callbacks to bots.
- Changing LLM prompt content or engine rules for external seats — they see exactly what an LLM seat sees.
- Cost accounting for external seats (their spend is on the bot's side) — spectator shows `n/a` in Phase 3.

---

## 9. Verify commands (Phase 1 exit)

```powershell
ruff check src tests scripts
python -m pytest -q
python scripts/smoke_external_harness.py
$env:PYTHONUTF8="1"; tw2k serve --agent-kind heuristic --num-agents 2 --external P2 --external-timeout-s 30 --port 8010
# in another shell, with the token printed to .tw2k/external_tokens.json:
python scripts/external_client_example.py   # env TW2K_HARNESS_URL=http://127.0.0.1:8010 TW2K_HARNESS_PLAYER=P2 TW2K_HARNESS_TOKEN=...
```
