# Grok Bot Player Guide — driving an external seat over `/harness/v1`

You are an out-of-process bot occupying one seat (e.g. `P3`) in a live TW2K-AI match. The server never calls you. You **pull** your observation, decide, and **push** exactly one action per turn over loopback HTTP with a bearer token.

Reference implementation: `scripts/external_client_example.py` (≈120 lines, `httpx` only). Copy it and replace `decide()`.

---

## 1. Setup (operator side)

```powershell
# one-time: mint tokens for the four bot seats (gitignored file)
python scripts/gen_external_tokens.py --seats P3,P4,P5,P6

# start the canonical 2x Qwen + 4x external match
powershell -File scripts/run_2qwen_4external.ps1        # spectator: http://127.0.0.1:8000
```

Each bot gets three env vars (values from `.tw2k/external_tokens.json`; `--show` prints them):

```
TW2K_HARNESS_URL=http://127.0.0.1:8000
TW2K_HARNESS_PLAYER=P3
TW2K_HARNESS_TOKEN=<that seat's token>
```

Never commit the tokens file. The server only accepts loopback clients unless `TW2K_HARNESS_ALLOW_REMOTE=1`.

---

## 2. Endpoints

All under `/harness/v1`, all JSON, all require `Authorization: Bearer <token>`. `{pid}` must be the seat your token was issued for.

| Method | Path | Purpose |
|---|---|---|
| GET | `/seats` | All external seats + status. Any valid seat token works. |
| GET | `/rules` | `system_prompt` (the exact rules text LLM seats get), `verbs[]`, `action_schema` (JSON schema of `Action`). Fetch once. |
| GET | `/{pid}/status` | Cheap heartbeat: `awaiting_input`, `turn_seq`, `deadline_at`, `turns_remaining`, `day`, `tick`, `match_status`, `last_result`. |
| GET | `/{pid}/observation?wait_s=30&format=json` | **Long-poll.** Blocks up to `wait_s` (max 60) until it is your turn. Returns status fields plus `observation` (null if not your turn). `format=llm` adds `llm_user_message` (the compact JSON string LLM seats are prompted with); `format=both` gives both. |
| GET | `/{pid}/observation?peek=1` | **Peek (S1).** When it is *not* your turn, returns a fresh read-only Observation for your seat instead of null (`peek: true`). Same fog as your turn; `awaiting_input` stays false and you cannot act on it. Use it to refresh your map/ship/port memory between turns. Cached 0.5 s server-side. |
| GET | `/{pid}/events?since=0&limit=200` | **Fogged event history (S1).** Events with `seq > since` that your seat is allowed to see (same rule as `recent_events`), oldest first. Each has `summary` (always) and `facts` — a per-kind whitelisted subset of the payload (e.g. `warp: {from,to}`, `trade: {commodity,qty,side,unit,total,realized_profit}`, `combat: {exchange_kind,attacker,defender,...}`). Response: `{events, next_since, latest_seq, has_more}`; page with `since=next_since`. Max `limit` 500. |
| POST | `/{pid}/action` | Body `{"turn_seq": N, "action": {...}}`. One per turn. |

### Webhook wake (optional, Path B)
If the host sets `TW2K_GROKBOT_WEBHOOK_URL` (or `TW2K_GROKBOT_WEBHOOK_<PID>`), the server POSTs when your turn starts:
`{"event":"turn_due","player_id","name","turn_seq","started_at","deadline_at","base_url","observation_url","action_url","brief":{day,tick,sector_id,turns_remaining,credits}}`.
`deadline_at` is the runner's **effective** deadline (it already reflects the unattended idle auto-WAIT rule). The full Observation is not included — pull it from `observation_url` with your token (`TW2K_GROKBOT_WEBHOOK_FULL_OBS=1` on the host restores the fat payload).

### Status codes

| Code | Meaning | What to do |
|---|---|---|
| 200 | ok | — |
| 401 | missing/unknown token | fix `TW2K_HARNESS_TOKEN` |
| 403 | token belongs to another seat, or non-loopback client | use your own `pid`; run on the same machine |
| 404 | no such player | check `pid` |
| 409 `"not_external"` | that seat is an LLM/heuristic/human | wrong `pid` |
| 409 `{"code":"stale_turn","current_turn_seq":N}` | your `turn_seq` is old (you were too slow; server already auto-WAITed) | re-poll observation, use the new `turn_seq` |
| 409 `{"code":"not_awaiting"}` | not your turn | long-poll `observation` instead of posting blind |
| 422 | action failed schema validation | check `kind` ∈ `verbs`, `args` shape |
| 429 | you already posted for this turn | wait for the next turn |
| 503 | match not running / seat closed | back off, retry status every few seconds; exit when `match_status` is `finished` |

---

## 3. Turn protocol

```
loop:
  r = GET /harness/v1/{pid}/observation?wait_s=30          # blocks until your turn
  if r.match_status in (finished, error): exit
  if not r.awaiting_input: continue                        # poll timed out, no turn yet
  obs      = r.observation
  turn_seq = r.turn_seq
  deadline = r.deadline_at                                 # epoch seconds; finish before this
  action   = decide(obs)                                   # your brain
  POST /harness/v1/{pid}/action {"turn_seq": turn_seq, "action": action}
  GET  /harness/v1/{pid}/status  -> last_result {ok, error, event_seqs}
```

Rules of the road:

- **Always echo `turn_seq`.** It guards you against applying a decision to a turn that already expired.
- **Budget your thinking against `deadline_at`.** Default timeout is 120 s (`--external-timeout-s`). Miss it and the server plays `wait` for you and logs an `AGENT_ERROR`. Four misses in a row end your day.
- **The scheduler is serial.** While you think, every other seat waits. Aim for ≤30 s per turn in a 6-seat match.
- **Read `last_result` before your next decision.** `ok:false` with `error` tells you exactly why the engine rejected the move; failed precondition actions cost no turn, but repeating them wastes your time budget.
- `action.actor_kind` is ignored; your events are tagged `actor_kind="external"` automatically.

---

## 4. The observation

Same object every LLM seat sees — same fog of war. Key fields (full model: `src/tw2k/engine/observation.py::Observation`):

| Field | What it is |
|---|---|
| `day`, `tick`, `max_days`, `finished` | match clock |
| `self_id`, `self_name`, `credits`, `net_worth`, `alignment`, `experience`, `rank`, `alive`, `deaths` | you |
| `turns_remaining`, `turns_per_day` | turn budget today. `warp` costs 2–3, `trade` 3, `attack` 5, `scan` 1, `wait` 1 |
| `ship` | `class`, `holds`, `cargo{fuel_ore,organics,equipment,colonists}`, `cargo_free`, `cargo_cost_avg`, `fighters`, `shields`, `mines`, `genesis`, `photon_missiles`, `ether_probes` |
| `sector` | where you are: `id`, **`warps_out`** (the only legal warp targets), `is_fedspace`, `port{code,buys[],sells[],stock{c:{current,max,price,side}}}`, `planets[]`, `occupants[]`, `fighter_group`, `mines[]`, `ferrengi[]` |
| `adjacent[]` | one-hop summaries: `id`, `port` code, `fighter_count`, `has_planets`, `occupants`, `known` |
| `known_ports[]`, `known_warps{sid:[...]}` | your accumulated map memory (grows as you scan/warp/probe) |
| `trade_log[]`, `trade_summary` | your last 25 trades + realized P&L aggregates |
| `recent_failures[]` | grouped repeated failures — if something is here, stop retrying it |
| `owned_planets[]`, `orphaned_planets[]` | planets you own / ownerless planets you can claim |
| `other_players[]`, `rivals[]`, `alliances[]`, `corp`, `inbox[]` | diplomacy + public leaderboard |
| `recent_events[]` | last ~12 global events, incl. your own `agent_error`s |
| `scratchpad`, `goals{short,medium,long}` | your own notes from last turn (set via `scratchpad_update` / `goal_*` on your action) |
| `action_hint` | server-built prose strip: legal warps, port buys/sells, P&L, StarDock menu, "YOUR LAST ACTION FAILED" |

Port codes are three letters in order **Fuel Ore, Organics, Equipment**; `B` = port buys from you, `S` = port sells to you. `stock[c].side` spells it out per commodity.

---

## 5. Action cheat sheet

`{"kind": <verb>, "args": {...}, "thought": "optional", "scratchpad_update": "optional ≤1500c", "goal_short|goal_medium|goal_long": "optional"}`

| Verb | Args | Notes |
|---|---|---|
| `warp` | `{"target": <sector_id>}` | target **must** be in `sector.warps_out` |
| `plot_course` | `{"target": <sector_id>, "execute": true}` | BFS autopilot ≤10 hops through known warps |
| `scan` | `{}` | reveals neighbours' warps/ports; 1 turn |
| `probe` | `{"target": <sector_id>}` | remote scan any sector; 5,000 cr |
| `trade` | `{"commodity":"fuel_ore\|organics\|equipment","qty":N,"side":"buy\|sell","unit_price":<opt>}` | must be at a port that trades that side; `unit_price` = haggle |
| `wait` | `{}` | burns 1 turn; better than a doomed action |
| `buy_ship` | `{"ship_class": "<key>"}` | StarDock (sector 1) only; 25 % trade-in |
| `buy_equip` | `{"item":"fighters\|shields\|holds\|genesis\|colonists\|armid\|limpet\|atomic\|photon\|probe","qty":N}` | StarDock only |
| `deploy_fighters` | `{"qty":N,"mode":"defensive\|offensive\|toll"}` | not in FedSpace |
| `deploy_mines` | `{"qty":N,"kind":"armid\|limpet\|atomic"}` | |
| `attack` | `{"target": "<player_id or ferrengi id>"}` | same sector; 5 turns; FedSpace attack = Federation retaliation |
| `photon_missile` | `{"target": "<player_id>"}` | |
| `deploy_genesis` | `{}` | in space, outside FedSpace, ≥3 hops from StarDock, `ship.genesis ≥ 1` |
| `land_planet` / `liftoff` | `{"planet_id": <id>}` / `{}` | |
| `claim_planet` | `{"planet_id": <id>}` | only for a landed planet listed in `orphaned_planets` |
| `assign_colonists` | `{"planet_id":<id>,"from":"ship","to":"fuel_ore\|organics\|equipment\|fighters","qty":N}` | landed on your planet |
| `load_planet_cargo` / `dump_planet_cargo` | `{"planet_id":<id>,"commodity":"...","qty":N}` | move stockpile ↔ holds while landed |
| `build_citadel` | `{"planet_id": <id>}` | L1 5k cr + 1k colonists, completes next day |
| `hail` / `broadcast` | `{"target":"<pid>","message":"..."}` / `{"message":"..."}` | 0 turns |
| `propose_alliance` / `accept_alliance` / `break_alliance` | `{"target":"<pid>","terms":"..."}` / `{"target":"<pid>"}` / `{"target":"<pid>"}` | |
| `corp_create` / `corp_invite` / `corp_join` / `corp_leave` / `corp_deposit` / `corp_withdraw` / `corp_memo` | see `/rules.system_prompt` | 500k cr to create, at StarDock |

The authoritative list is `GET /rules` → `verbs` (34 today) and the JSON schema in `action_schema`. The `system_prompt` there is the same rules text LLM seats receive — worth feeding to your own model verbatim if your bot is LLM-backed.

---

## 6. Example: a minimal bot

```python
import httpx, os, random
BASE, PID = os.environ["TW2K_HARNESS_URL"], os.environ["TW2K_HARNESS_PLAYER"]
H = {"authorization": f"Bearer {os.environ['TW2K_HARNESS_TOKEN']}"}

with httpx.Client(base_url=BASE, headers=H, timeout=70) as c:
    while True:
        r = c.get(f"/harness/v1/{PID}/observation", params={"wait_s": 30}).json()
        if r.get("match_status") in ("finished", "error"): break
        if not r.get("awaiting_input"): continue
        obs, seq = r["observation"], r["turn_seq"]
        port, cargo = obs["sector"].get("port") or {}, obs["ship"]["cargo"]
        sell = next((k for k in port.get("buys", []) if cargo.get(k)), None)
        if sell:
            action = {"kind": "trade", "args": {"commodity": sell, "qty": cargo[sell], "side": "sell"}}
        elif port.get("sells") and obs["ship"]["cargo_free"] and obs["credits"] > 500:
            action = {"kind": "trade", "args": {"commodity": port["sells"][0], "qty": min(obs["ship"]["cargo_free"], 10), "side": "buy"}}
        else:
            action = {"kind": "warp", "args": {"target": random.choice(obs["sector"]["warps_out"])}}
        c.post(f"/harness/v1/{PID}/action", json={"turn_seq": seq, "action": action})
        print(c.get(f"/harness/v1/{PID}/status").json()["last_result"])
```

---

## 7. What a good turn looks like

1. Read `last_result` and `recent_failures` first. If the previous action failed, do something different.
2. Check `turns_remaining`. Below 3, `wait` — you cannot warp or trade.
3. At a port: sell anything in `cargo` the port `buys`; buy what it `sells` if you have `cargo_free` and a known buyer nearby (`known_ports`).
4. Otherwise move: pick a `warps_out` target you have not visited (`adjacent[].known == false`) or one leading toward a profitable pair.
5. Once rich (≈45k+), go to sector 1 and `buy_ship` a bigger hull; then `buy_equip genesis` + colonists and plant a planet ≥3 hops from StarDock. Planets are how the leaderboard is won.
6. Write a one-line `scratchpad_update` and `goal_short` so you do not forget your plan between turns.
7. Respond well inside `deadline_at`.

---

## 8. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Every POST → 409 `stale_turn` | You are slower than `--external-timeout-s`. Speed up or ask the operator to raise the timeout. |
| 401 right after server restart | Tokens are stable per seat across restarts; check you copied the right seat's token, not another bot's. |
| Server crashed at boot with `UnicodeEncodeError` | Windows console encoding. Start via `run_2qwen_4external.ps1` or set `PYTHONUTF8=1`. |
| `warp` → `ok:false` "not a warp from here" | You used a sector not in `sector.warps_out`. |
| `deploy_genesis` → "too close to StarDock" | Need ≥3 hops from sector 1; warp deeper. |
| Spectator shows your seat idling | You are not long-polling; `awaiting_input` was true and nobody answered. |
