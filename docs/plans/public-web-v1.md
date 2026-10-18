# public-web-v1 (COMMANDER NOTE 58, part A)

Plan only. No source, web, test or constants file was changed to write this.

Goal: anyone can go to Ben's site https://thesingularity.netlify.app/ (repo EarlTheDuke/singularity-portfolio), press Play, and play our TW2002 clone in the browser: alone against code bots, with friends, with their own AI player, or by commanding their own AI player by voice or text.

Code read (read only): `C:\Users\sugar\qc_bridge\wt_wire` at its working tip (V311_PROFILE from NOTE 57 present; NOTE 59 in progress). Portfolio read (read only): the local clone `...\Projects in progress\singularity-portfolio` (`netlify.toml`, `README.md`, `package.json`, `netlify/functions/proxy.js` listed, not opened). Rules: `C:\Users\sugar\tw2002_reference\RULINGS_v311.md`, `MASTER_PLAN.md`.

Price date: all prices are assumed as of 2026-10-17 (the date of this doc) but come from the last public price lists the author knows. Every dollar figure below is an estimate. Re-check each row on the provider's price page before buying anything.

## 0. Decisions in one screen

1. Host the game on one Hetzner Cloud VPS to start (Docker Compose: Caddy + a new lobby service + one game worker process per game). Second choice: Fly.io, one Machine per game.
2. One game per OS process. The engine switches are module globals in `src/tw2k/engine/constants.py`, and `create_app` in `src/tw2k/server/app.py` owns exactly one `MatchRunner`. So two games with different rules cannot share a process today.
3. The Netlify site stays static. It gets a TW2002 landing page and tutorials, and links out to `https://play.<domain>/`. No iframe for play (cookies and microphone break inside it). An iframe is used only for the read-only live demo.
4. Guest play first (a session cookie, no sign-up). Sign-in comes later, only for stored keys, leaderboards and more games per person.
5. Human players use the redesign cockpit (`COCKPIT_LAYOUT=redesign`) as an external seat over `/harness/v1`. `/bot` stays unchanged in the code; the public server just serves the redesign layout.
6. Public games default to the v3.11 rules (`V311_PROFILE="v311"`) chosen per game at the lobby. The stored default in `constants.py` stays `"legacy"` so the bank pin and digests stay valid.
7. Bring-your-own AI keys are held in worker memory only. They are never written to disk, logs, events or snapshots. Stored keys (encrypted) come later and only for signed-in users who opt in.
8. Voice uses the browser's own speech APIs first (free, push-to-talk). A server speech service is optional and late.

## 1. What exists today (facts from the repo)

| Area | What the code has | File |
|---|---|---|
| Web server | FastAPI app, one `MatchRunner` per app, `/ws` websocket, static `web/` | `src/tw2k/server/app.py` (`create_app`) |
| Match setup | `MatchSpec`, `AgentSpec`, `GameConfig` | `src/tw2k/server/runner.py`, `src/tw2k/engine/models.py` |
| Seat kinds | `llm`, `heuristic`, `human`, `external` (runner builds them in `_build_agents`) | `src/tw2k/server/runner.py` ~line 1441 |
| Code bots | `HeuristicAgent` in process; `SeatBrain` N1/N2/N3 runs out of process over HTTP | `agents/heuristic.py`, `agents/seat_brain.py`, `scripts/seat_brain_v2.py` |
| Cockpit | Redesign page behind `COCKPIT_LAYOUT=redesign` or `?layout=redesign`; `/bot2` always redesign | `web/redesign.*`, `app.py` `_cockpit_layout` |
| Seat API | `/harness/v1/{seat}/status, observation, events, reference, action, hold, macro`; bearer token or claim cookie; loopback only unless `TW2K_HARNESS_ALLOW_REMOTE=1` | `src/tw2k/server/harness.py` |
| Seat tokens | `secrets.token_urlsafe(32)`, constant-time compare, masked in logs, tokens file 0600 | `src/tw2k/server/harness_tokens.py` |
| Claim links | `/bot/claim?seat=..&token=..` sets HttpOnly cookie `tw2k_seat_<SEAT>` with Path `/harness/`; writes need header `X-TW2K-Seat` | `src/tw2k/server/seat_links.py` |
| Spectator gate | One token per process (`TW2K_SPECTATOR_TOKEN`) gates `/`, `/state`, `/events`, `/ws`, `/control/*`, `/api/*` | `src/tw2k/server/spectator_gate.py` |
| Log redaction | `?token=` is redacted from uvicorn access logs | `app.py` `_RedactTokenQuery` |
| Saves | `saves/<run-id>/meta.json`, `actions.jsonl`, `events.jsonl`; `tw2k replay` re-executes actions | `server/runner.py` `_open_save_sink`, `server/replay.py` |
| Operator orders | `/api/ai-directives` GET/POST/DELETE and `/chat` set a text directive an LLM seat reads next turn | `app.py` |
| Copilot and voice | `/play` cockpit with copilot, push-to-talk (`SpeechRecognition`) and TTS (`speechSynthesis`) | `web/play.js`, `src/tw2k/copilot/*`, tests `test_voice_ui_phase_h3..h5.py` |
| LLM fallback | After 5 timeouts or an error the LLM seat plays as `HeuristicAgent` and emits `agent_fallback` | `agents/llm.py` `_mark_fallback` |
| Cost tracking | Per-seat LLM cost, `/api/cost` | `engine/llm_pricing.py`, `agents/llm_usage.py` |
| MCP bridge | MCP server that drives a running match over HTTP | `src/tw2k/mcp_server.py` |
| Rules profile | `V311_PROFILE` turns on the 60-switch v3.11 set; NOTE 59 is adding `kill_cash_held` and `POD_CASH_MODE` (pod keeps 25 credits) | `engine/constants.py`, `docs/plans/v311-profile-v1.md` |

Things the public site needs that do not exist yet: a lobby, more than one game per server, resume of a live game after a restart, per-game routing, public-mode lockdown of `/control/*` and `/api/*`, rate limits, a health route (`/healthz` is listed as open in `spectator_gate.py` but no route serves it), and a per-seat route for AI orders.

## 2. Hosting

### 2.1 Constraints that come from our code

| Constraint | Where | Consequence for hosting |
|---|---|---|
| Engine switches are module globals (`K.X = ...`), ~125 `*_MODE` names | `engine/constants.py` | One game per process. A worker sets its switches once at start. |
| One `MatchRunner` per FastAPI app | `app.py` `create_app` | A lobby must start one worker per game. |
| Long-lived websocket `/ws` for the spectator; cockpit polls harness routes; harness waits up to `MAX_WAIT_S = 60` | `app.py`, `harness.py` | Host must allow websockets and 60 s+ requests. Netlify proxy rewrites cannot carry either. |
| v3.11 turn regen runs on the wall clock (`TURN_REGEN_DAY_SECONDS = 24*3600`) | `constants.py`, `engine/runner.py` line ~177 | A v3.11 game with original pacing lasts real weeks. Games must survive restarts. No sleep-to-zero host that loses state. |
| Saves are append-only files on local disk | `server/runner.py` | Needs a persistent disk or object storage. |
| `meta.json` stores config and seats but not switch values | `_open_save_sink` | Must add a `switches` record before public saves mean anything. |
| `Universe.events` is an in-memory list that grows all game | `engine/models.py` | Memory per worker grows with game length. Measure in P0. |

### 2.2 Sizing assumptions (to be replaced by P0 measurements)

- One active game worker: about 250 MB RAM and about 0.1 vCPU on average (1,000 sectors, 1 human, 3 code bots, `action_delay_s` 0.6). This is a guess; P0 item 1 measures it.
- Lobby + Caddy + SQLite: 0.5 vCPU, 0.5 GB.
- "Concurrent players" means humans connected at the same time. Assume 1.5 humans per active game, so 10 / 100 / 1,000 players = about 7 / 67 / 667 active games.
- Idle games are hibernated to disk (P2), so they cost disk, not RAM.
- Add 50% headroom.

Needed: 10 players = 2 vCPU / 4 GB. 100 players = 12 vCPU / 24-32 GB. 1,000 players = about 100 vCPU / 250 GB, which is only affordable if P0 shows a smaller worker or if P7 puts several games in one process (needs the switch refactor in 12.6).

### 2.3 Providers compared (features)

| | VPS (Hetzner Cloud; DigitalOcean similar) | Fly.io | Render | Railway |
|---|---|---|---|---|
| Model | Whole Linux box; we run Docker Compose | Firecracker Machines; can start one Machine per game by API | Fixed services from a blueprint | Fixed services; usage billing |
| Websockets | Yes (Caddy) | Yes | Yes | Yes |
| Sleep / cold start | Never sleeps | Optional auto-stop; start in about 1-3 s | Free tier sleeps after ~15 min idle, ~30-60 s cold start; paid tiers do not sleep | Optional "app sleeping"; paid usage stays up |
| Persistent disk | Local SSD + volumes | Volumes, one per Machine, one region, no replication | Disk on paid services; a service with a disk runs one instance and has no zero-downtime deploy | Volumes, one per service |
| Regions | Hetzner: EU (DE, FI) and US (Ashburn, Hillsboro), Singapore; DO: many (NYC, SFO, TOR, LON, FRA, AMS, SGP, BLR, SYD) | ~30 regions | Oregon, Ohio, Virginia, Frankfurt, Singapore | US West, US East, EU West, SE Asia |
| Process-per-game fit | Good: lobby spawns local processes | Good: Machine per game, auto-stop = free hibernation | Poor: no cheap per-game spawn; all games in one big service | Poor to fair: same as Render |
| Ops effort | Highest: OS patches, firewall, backups are ours | Medium: flyctl, Machines API, volume care | Low | Low |
| Lock-in | None | Medium (Machines API) | Medium | Medium |

### 2.4 Monthly cost estimates (USD, re-check before buying)

| Players at once | Hetzner Cloud | DigitalOcean | Fly.io (Machine per game, auto-stop) | Render | Railway (usage) |
|---|---|---|---|---|---|
| 10 | $10-20 (CPX21/CPX31) | $24-48 (2-4 vCPU droplet) | $30-60 (7 x shared-cpu-1x 512 MB + lobby + volumes) | $90-110 (Pro 2 CPU/4 GB + disk; plus a workspace fee if any) | $45-60 (Pro plan $20 incl. usage; ~1 vCPU + 2.5 GB used) |
| 100 | $65-90 (CPX51 16 vCPU/32 GB or CCX33; +20% for backups) | $190-250 (2 x 8 vCPU/16 GB) | $250-400 | $450-500 (Pro Ultra 8 CPU/32 GB) | $300-400 |
| 1,000 | $800-1,100 (3-4 x CCX53), or ~$400 on EU dedicated servers | $1,200-1,800 | $2,300-3,500 | $4,500+ and multiple disk services behind a router (high ops) | $3,000-3,500 |

Extras on every option: domain $10-20 a year; object storage for backups $1-6 a month at our size; egress is small (text JSON, a few KB per action) except at 1,000 players.

### 2.5 Recommendation

Start on one Hetzner Cloud VPS (CPX31, 4 vCPU / 8 GB, in Ashburn if most players are in the US, else Falkenstein), running Docker Compose with Caddy, the lobby, and one `tw2k` worker process per game.

Reasons:
1. Process-per-game is forced by our module-global switches; a single box runs that model with no extra platform work.
2. RAM is 3-6 times cheaper than Fly, Render or Railway at every size in the table.
3. Local disk is persistent; long v3.11 games and their save logs are safe across restarts.
4. Nothing sleeps; websockets and 60 s harness waits work through Caddy as-is.
5. No lock-in. The same compose file runs on DigitalOcean or any other VPS.

Cost of the choice: we own patching, firewall and backups. Section 12.8-12.9 and milestone P3 cover them.

Fallback: if Ben does not want to run a server, use Fly.io with one Machine per game (auto-stop gives hibernation for free) and keep snapshots in object storage instead of Machine volumes. Expect about 2-4 times the Hetzner cost at 100+ players.

### 2.6 Shape of the deployment

```
Browser ──HTTPS/WSS──> Caddy (play.<domain>, Let's Encrypt TLS)
                         ├─ /            -> lobby (FastAPI + SQLite)   new: src/tw2k/public/
                         ├─ /g/<game>/*  -> worker for <game> (127.0.0.1:<port>), prefix stripped
                         └─ /g/<game>/*  (worker asleep) -> lobby "waking" page, spawns worker
lobby ──spawn/stop──> worker = `tw2k serve` with --host 127.0.0.1, its own port, saves dir,
                      tokens file, switch overlay, COCKPIT_LAYOUT=redesign, TW2K_PUBLIC_MODE=1
lobby ──Caddy admin API (localhost:2019 only)──> add/remove the /g/<game> route
nightly: restic -> object storage (SQLite .backup + saves + snapshots)
```

Per-game routes: use a path prefix `/g/<game_id>/` with Caddy `handle_path` (one hostname, one certificate, cookies isolated by path, no DNS API secret on the server). This needs small base-path changes: the redesign page and spectator page use absolute paths (`web/redesign.js` 4, `web/redesign.html` 5, `web/app.js` 13, `web/index.html` 3), and the claim cookie path `/harness/` in `seat_links.py` must become `/g/<id>/harness/`. `web/bot.js` and `web/bot.html` are not served publicly and stay unchanged.

Alternative: one subdomain per game (`<id>.play.<domain>`) needs a wildcard certificate by DNS-01 (a DNS API token on the server). Per-name on-demand certificates would hit Let's Encrypt's per-domain weekly limit at scale. Not chosen.

The harness loopback check (`_check_loopback`) is meaningless behind Caddy, because every request arrives from 127.0.0.1. Public mode must rely on the seat token alone and set `TW2K_HARNESS_ALLOW_REMOTE` deliberately; P0 adds a test that a request with no token still gets 401 through the proxy.

### 2.7 Linking the Netlify site to the game

| Option | Works? | Why |
|---|---|---|
| Netlify rewrite/proxy `/play/* -> game host` (status 200) | No | Netlify proxy does not carry websockets and times out long requests; harness waits up to 60 s. |
| Iframe the cockpit inside a Netlify page | No for play | Seat cookies would be third-party cookies (blocked by Safari, limited by Chrome). The portfolio sends `Permissions-Policy: microphone=()` for every page, which blocks push-to-talk inside the frame. |
| Iframe the read-only live demo | Yes | No cookies, no mic. Worker sends `Content-Security-Policy: frame-ancestors https://thesingularity.netlify.app`. |
| Link out to `https://play.<domain>/` | Yes, chosen | Own origin, first-party cookies, mic permission on its own page. |

Domain: `thesingularity.netlify.app` is a Netlify subdomain; we cannot create `play.thesingularity.netlify.app`. Ben buys a domain (open question 1). Then:
- DNS: apex and `www` -> Netlify (keeps the `netlify.app` name working too); `play` A/AAAA -> the VPS IPs. TTL 300 during launch.
- TLS: Caddy gets and renews Let's Encrypt certificates for `play.<domain>` automatically. Netlify handles the apex.
- CORS: the game server does not need CORS for play (same origin). One public read-only route, `GET /public/v1/stats` (games running, players online, demo link), gets `Access-Control-Allow-Origin: https://thesingularity.netlify.app` (and the new apex) for the landing page counter. No credentials, GET only.
- Without a domain (fallback): use the host's own name (Fly gives `<app>.fly.dev`; a VPS needs a domain for TLS).

Changes in the singularity-portfolio repo (a separate PR there; Netlify deploys `main`):

| File | Change |
|---|---|
| `tw2002.html` (new) | Landing page: what the game is, three screenshots, buttons Play now / Watch the live demo / Tutorials / Watch a replay, cost and privacy notes for AI keys and voice. |
| `tw2002/tutorials/*.html` (new) | Static tutorial pages (section 11) with screenshots. |
| `index.html` | One featured-project card linking to `tw2002.html`. |
| `netlify.toml` | Redirects: `/tw2002 -> /tw2002.html` (301); `/tw2002/play -> https://play.<domain>/` (302); `/tw2002/demo -> https://play.<domain>/demo` (302). No change to the global `Permissions-Policy` (the mic is used on `play.<domain>`, not on Netlify). |
| `README.md` | Layout table gains the two new entries. |

No Netlify Function and no secret are needed on the portfolio side.

## 3. Accounts and sessions

### 3.1 Guest play (P1)

- First visit to `play.<domain>` sets `tw2k_sid`: 32 random bytes, HttpOnly, Secure, SameSite=Lax, Path=/, 30-day rolling expiry. The lobby stores only its SHA-256.
- The player picks a display name per game: 3-20 characters, letters, digits, space, `-`, `_`. Names are checked server-side (they are shown to other players; see 4.4).
- Creating or joining a game gives the player one seat. The seat is an `external` seat with a fresh token from `harness_tokens.generate_token()`.
- The lobby never stores the seat token in plain text. "Resume" asks the worker (loopback admin route, new) to rotate that seat's token and redirects through `/g/<id>/bot/claim`. Each resume kills any older copy of the token.
- A one-time recovery link is shown at game creation (a separate secret, hashed in SQLite) so a player can resume on another device.

### 3.2 Reconnect

- The cockpit polls `status`/`observation`; a dropped connection just resumes polling. The spectator websocket reconnects with backoff (already in `web/app.js` patterns; verify in P1).
- If the worker hibernated (P2), `/g/<id>/` lands on the lobby's waking page, which starts the worker from its snapshot and reloads within a few seconds.

### 3.3 Expiry and reaping

| Item | Lifetime |
|---|---|
| Guest session `tw2k_sid` | 30 days rolling |
| Seat claim cookie | Until the game ends, capped at 30 days, refreshed on use |
| Recovery link | Until the game ends |
| Fast game (legacy, or v3.11 with day length 1 h or less) with no human action | Hibernate after 15 min; reap after 3 days |
| Real-time v3.11 game (24 h days) with no human action | Hibernate after 15 min; reap after 14 days |
| Finished game | Read-only replay kept 30 days (owner may pin up to 3) |

### 3.4 Sign-in (P6)

Email magic link (a transactional mail provider) or OAuth (GitHub, Google). Signing in merges the guest session's games into the account. Needed only for: stored encrypted AI keys, public leaderboards, more than 2 active games, and account deletion with data export.

## 4. Abuse limits and security

### 4.1 Limits

| Limit | Value at launch (tune later) | Where enforced |
|---|---|---|
| New games per session | 3 per hour, 10 per day | lobby |
| New games per IP | 10 per day | lobby |
| Active games per guest / signed-in user | 2 / 5 | lobby |
| Server-wide active games | Admission cap (start 30 on CPX31); beyond it "server full, try the live demo" | lobby |
| Harness requests per seat token | 10 per s, burst 20 | new middleware (worker) |
| One action per turn | Already 429 | `harness.py` |
| Retry storm | `API_RETRY_LIMIT` per `API_RETRY_WINDOW_S` | `harness.py` `retry_blocked` |
| Websockets per IP | 10 | Caddy or lobby |
| Request body | 64 KB | Caddy `request_body max_size` |
| Text fields (names, hail, radio, broadcast, directives) | 200 chars, control characters stripped | worker, new validation |
| Seats per game | 8 (matches `AGENT_COLORS` and the name pool in `app.py`) | lobby form |
| Universe size | 2,000 max in public (admin can go higher) | lobby form |

### 4.2 Public mode lockdown (new flag `TW2K_PUBLIC_MODE`, off by default)

When on, the worker:
- refuses `/control/restart`, `/control/speed`, `/control/pause`, `/control/resume` (the lobby does lifecycle);
- refuses `/play`, `/api/human/*`, `/api/copilot/*`, `/api/economy/*` (universe-wide prices are a leak), and `/api/ai-directives*` (replaced by a per-seat route, section 9);
- serves `/` and `/ws` only under the spectator rules of section 7;
- serves `/bot` with the redesign layout (`COCKPIT_LAYOUT=redesign`), and the harness;
- never accepts API keys in a request body (today `/control/restart` takes `agents[i].custom_api_key`).

### 4.3 Admin kill switch

- A state file read on every lobby request: `open`, `no-new-games`, `read-only` (games pause, viewing allowed), `maintenance` (static page).
- Admin routes on a separate port bound to the Tailscale interface only, protected by an admin token: list games, stop a game, stop all, ban a session or IP, change the state.
- SSH only over Tailscale; the public firewall opens 80 and 443 only.

### 4.4 Input validation and XSS

- Actions: already validated by the `Action` model (422); `API_ARGS_MODE` live is part of the v3.11 profile.
- New-game form: one strict pydantic model with enums and ranges (section 5).
- XSS: `web/redesign.js` writes HTML with `innerHTML` in 93 places. Its `esc()` (line 6) escapes `& < >` but not quotes, so a name inside an attribute can break out. Public players control names and message text. P0 makes `esc()` escape `"` and `'`, audits every site that prints a name, ship name, planet name, corp name, memo, hail, radio or broadcast, and adds server-side name rules. `web/app.js` has its own `esc()`; audit it the same way.
- Prompt injection: rival messages reach LLM seats through the observation. They cannot read a key (keys are not in the prompt) but can try to steer the AI. Tell AI owners.

### 4.5 Logging without secrets

- Keep `_RedactTokenQuery`; add a filter for `Authorization`, `Cookie`, `X-Access-Code`, `custom_api_key` and any `sk-`/`xai-` shaped strings.
- `agents/llm.py` `_mark_fallback` puts the provider exception text into the `agent_fallback` event, which every spectator receives. In public mode, publish only a reason code (`timeout`, `auth_failed`, `rate_limited`, `provider_error`).
- Structured JSON logs: time, game id, seat, route, status, latency, a 6-character session hash prefix. 14-day retention.
- P3 pass bar includes a grep of a week of logs for token, cookie and key patterns: zero hits.

### 4.6 Bring-your-own AI keys

Rules (from the NOTE): never stored in plain text; never logged; never sent to other players or spectators; deletable.

| Mode | When | How |
|---|---|---|
| A. Your own bot, no key on our server | P5 | You run any agent (our `mcp_server.py`, `scripts/external_client_example.py`, your code) against your seat token. Our server never sees your provider key. Recommended for power users. |
| B. Per-session, in memory (default) | P5 | Key typed into the cockpit, sent once over TLS to the lobby, forwarded over loopback to the worker, kept only in the `LLMAgent` object. Not in env, argv, disk, `meta.json` (already excluded by `_open_save_sink`), snapshots, events or logs. Lost on hibernate or restart: the seat plays as a code bot until the owner re-enters it. "Forget key" button drops it at once. |
| C. Stored, encrypted (opt-in) | P6, signed-in only | AES-GCM with a server master key from a 0600 env file (or a KMS later); per-user row; UI shows provider and last 4 characters only; delete button; deleted with the account; decrypted only inside the worker that runs the seat. |
| D. Browser-run AI | Later, maybe | Page JS calls the provider directly with the key in browser memory and plays through the harness. Works only while the tab is open; provider browser support varies. |

## 5. Start New Game screen

Original-style choices first, advanced ones folded. Every field maps to existing code unless marked new.

| Field | Choices (default) | Maps to |
|---|---|---|
| Rules | Original v3.11 (default) / Classic clone (legacy) | `V311_PROFILE` = `"v311"` / `"legacy"` in the worker overlay. v3.11 includes the 60 switches in `docs/plans/v311-profile-v1.md` plus NOTE 59's kill cash and pod cash. |
| Universe size | 200 / 500 / 1,000 (default) / 2,000 | `GameConfig.universe_size` |
| Game length (days) | 7 / 15 / 30 (default) / 60 | `GameConfig.max_days` (`VICTORY_DEFAULT_MAX_DAYS = 30`) |
| Turns per day | v3.11: 250 (default, RULINGS s2/s5); legacy: 1,000; range 50-2,000 | `GameConfig.turns_per_day`; honoured under live pace (`live-profile-pace-fix-v1`) |
| Day length (real time) | v3.11 only: 24 h original / 4 h / 1 h / 15 min | `TURN_REGEN_DAY_SECONDS` set in the worker at start (as `scripts/v311_soak.py --day-seconds` does). Legacy: a day ends when every seat is out of turns. |
| Starting package | Follows Rules. v3.11: Merchant Cruiser, 300 credits, 30 fighters, 20 holds, 0 shields, 250 turns, free class M planet (RULINGS s2). Legacy: 20,000 credits, 20 fighters, 20 holds, 1,000 turns. | `STARTING_PACKAGE_MODE` via the profile; `opening_loadout`, `grant_starting_planet`. Custom credits (`GameConfig.starting_credits`) only apply under legacy. |
| Start location | FedSpace 1-10 spread (default) / everyone at StarDock | `GameConfig.all_start_stardock` |
| Code-bot opponents | 0-7 (default 3) | Seats of kind `heuristic`; total seats max 8 |
| Bot strength | Easy = `HeuristicAgent` / Normal = SeatBrain N2 / Hard = SeatBrain N3 | Easy exists in process. Normal/Hard need a new in-process adapter around `agents/seat_brain.py` (today it runs over HTTP from `scripts/seat_brain_v2.py`). |
| Ferrengi | Off / Low / Normal (default) / High | `enable_ferrengi`, `ferrengi_per_day`, `ferrengi_max_alive`, `ferrengi_grace_days`, `ferrengi_strength_ramp_days`, `ferrengi_min_strength_scale` presets |
| Human seats | 1 (solo) up to 8 minus bots; invite links for the rest | external seats with claim links |
| AI seats | 0-n "your own AI" seats (section 8) | `llm` seats with an in-memory key, or `external` seats for mode A |
| Visibility | Private (invite only, default) / Public (listed in the lobby, open seats joinable) | lobby |
| Spectators | None / Owner only (default) / Public after the game / Public live (bots-and-AI-only games) | section 7 |
| Advanced: seed | Random (default) / fixed number | `GameConfig.seed` |
| Advanced: one-way warps | Normal 15% (current default) / Few 3% (closer to the original, MASTER_PLAN MOV-f) / None | `GameConfig.one_way_fraction` |
| Advanced: win rule | Play all days (default) / allow early win | `GameConfig.play_to_day_cap` |
| Advanced: deaths before out | Rules default / 0 = never | `GameConfig.elimination_deaths` |
| Advanced: planets, corporations | On (default) / off | `enable_planets`, `enable_corps` |

Multi-human pacing is set by the server, not shown: with more than one human seat the worker turns on `TW2K_SEAT_DEADLINE_MODE=live` (75 s per turn, 3 misses pass the seat for the day) and, for fast games, `TW2K_ASYNC_DAY_MODE=live` (parallel turns, 20-minute day cap). Both env overrides already exist (`constants.py` `_forced_mode`).

Validation: the form posts one JSON body to `POST /lobby/v1/games`; unknown keys are rejected; enums and ranges as above; the response is the game id and a redirect to the claim link.

## 6. Play straight from the dashboard (no AI)

- The cockpit is the redesign page (`web/redesign.*`) at `/g/<id>/bot?seat=P1`, opened through the claim redirect. Keys, forms and screens are the ones built in NOTEs 32-56 (computer menu, port, StarDock, planet and citadel forms, Rules and Help).
- The human seat is `kind="external"`; the cockpit posts to `/harness/v1/{seat}/action` with `turn_seq`. `/play` and `HumanAgent` stay internal.
- Solo game against bots: the round-robin scheduler waits for the human. Use `pause_on_seat_drop` (exists) so the game pauses when the human leaves, for legacy and short-day games.
- Real-time v3.11 game: bots should keep playing while the human is away, and the human's turns come back hourly (`offline-turn-regen-v1`). Today an absent external seat gets an auto-WAIT after `external_idle_wait_s`. New (P2, behind a legacy-default flag): an away seat is skipped without spending a turn.
- `COCKPIT_FIELDS_MODE="tw2002"` adds the cockpit block (verdict, haggle, hold quote, own last-seen prices) that closed most AI-seat gaps in `docs/playtests/cockpit-ai-seat-v3/gaps.md`. Recommend it on for public games; Ben decides (open question 6).
- Mobile: the redesign has 390 px passes (cockpit-gaps-v1 screenshots); P4 adds a phone smoke test.

## 7. Spectator overview and fog rules

Today `/` (`web/index.html` + `web/app.js`) shows every sector, ship and agent thought, gated by one token per process. In a game with humans that is a full map for anyone watching.

| Game type | Live view for non-players | After the game |
|---|---|---|
| Bots and AI only (incl. the live demo) | Full spectator view, public or owner-only per the form | Full replay |
| Has human players, private | Owner and invited spectators see the "public board" only | Full replay if the owner allows |
| Has human players, public | Public board for everyone | Full replay if the owner allows |
| Your own seat | Your cockpit (fogged by the engine's own rules) | Full replay |

- Public board (new, P4): standings (experience under v3.11, `final_standings` in `harness.py`), V-screen daily counts (`DAILY_STATS_MODE`), FedComm broadcasts, highlights without sector numbers, day and time to next day. No map, no positions, no thoughts.
- A player in a running game cannot open the full spectator view of that game (lobby checks the session's seats before issuing the spectator token).
- AI seat thoughts are shown only to that seat's owner while the game runs.
- Per-game spectator tokens: each worker gets its own `TW2K_SPECTATOR_TOKEN`; the lobby sets the `tw2k_spectator` cookie with Path `/g/<id>/`.
- Later option: a delayed full view (for example one game day behind) by streaming `events.jsonl` with a lag.

## 8. Add your own AI player

- Seat type `llm` (`agents/llm.py`). Providers offered: xAI, Anthropic, OpenAI, DeepSeek. Not offered publicly: `cursor` (runs a local CLI) and `custom` base URLs until an SSRF guard exists (https only, public IPs only, no redirects, block 169.254.169.254 and private ranges).
- Default models are the ones in `llm.py` (`DEFAULT_XAI_MODEL`, `DEFAULT_ANTHROPIC_MODEL`, `DEFAULT_OPENAI_MODEL`, `DEFAULT_DEEPSEEK_MODEL`); the lobby shows a short curated list per provider. Model names change; re-check at launch.
- Cost warning before start: estimated tokens per turn x turns per day x days x price from `engine/llm_pricing.py`. P5 measures tokens per turn from real saves (`scripts/cost_report.py`). Show the estimate in dollars with the words "estimate; your provider bills you".
- Live cost: per-seat cost from `MatchCostTracker` shown in the owner's cockpit only.
- Spend cap: owner sets a USD cap; at the cap the seat switches to its code-bot fallback and the owner is told.
- Timeouts: `llm_think_cap_s` (default 90 s) capped at 60 s in public; after 5 timeouts the existing fallback plays the turn as `HeuristicAgent`. A bad key falls back at once with reason code `auth_failed`.
- Key handling: section 4.6.
- Mode A (your own bot): the lobby gives the owner the seat token once and links the harness docs (`docs/GROK_BOT_CONNECTOR.md`, `scripts/external_client_example.py`, `tw2k mcp`).

## 9. Command your own AI player in real time

What exists: operator directives (`/api/ai-directives`, `/api/ai-directives/chat`) store a directive and a dialogue on the player; the LLM reads them on its next turn. `/play` has push-to-talk (`SpeechRecognition`) and spoken replies (`speechSynthesis`) for the copilot. `docs/LOCAL_STT_PLAN.md` (faster-whisper) and `docs/plans/2026-09-26-voice-layer-architecture.md` (streaming STT, Grok, streaming TTS, under 800 ms) are plans.

Plan:
- New per-seat route `POST /harness/v1/{seat}/orders` authenticated by the AI seat's owner token (new: an owner token for `llm` seats). It replaces `/api/ai-directives` in public mode.
- Orders panel in the cockpit (owner of an AI seat): a text box, a push-to-talk button (hold the button or the backtick key), and the AI's replies.
- Two kinds of order:
  - Quick commands, parsed in the browser, no LLM: `status`, `pause AI`, `resume AI`, `hold position`, `go to StarDock`, `stop trading`, `retreat`.
  - Free text, sent as a directive: "trade ore between 42 and 101 until you have 50,000, then buy 10 holds".
- Risky orders (attack, self-destruct, sell or trade in the ship, bank transfer, port attack) need a confirm click or the spoken word "confirm" within 10 s.
- Report back: on its next turn the AI writes a one-line acknowledgement into the dialogue ("Trading 42 and 101 until 50,000"); its action results appear in the cockpit log. Optional spoken readouts (browser `speechSynthesis`) for the acknowledgement, combat, docking, and day end.
- Latency: browser speech gives a final transcript in about 0.5-1.5 s. The order is stored at once and acted on at the AI's next turn: seconds in a solo game, up to one scheduler round in a multi-seat game. Say so in the UI ("will act on its next turn").

| Speech option | Cost | Privacy | Browsers | Plan |
|---|---|---|---|---|
| Browser Web Speech (`SpeechRecognition`, `speechSynthesis`) | Free | Chrome sends audio to Google; Safari to Apple; disclose | Chrome, Edge, Safari; Firefox has no recognition (text only) | P6 default |
| faster-whisper on our VPS | CPU only; a small model handles short push-to-talk clips | Audio stays on our server, never stored | All (mic via `getUserMedia`) | Optional later; watch CPU |
| Streaming cloud STT/TTS (per voice-layer doc) | Per-minute fees | Third party | All | Only with the user's own key; not funded by Ben |

Push-to-talk only. No open mic, no recorded audio, transcripts kept only in the game's dialogue.

## 10. Demo games

- Pre-recorded replays: `tw2k replay saves/<id>` (`create_replay_app`, `ReplayRunner`) re-executes `actions.jsonl` through the engine. Candidates:
  1. v3.11 code-bot 10-day soak, seed 250925 (`docs/playtests/v311-profile-v1/`).
  2. Cockpit AI seat 10-day run (`docs/playtests/cockpit-ai-seat-v3/`).
  3. LLM seats vs code bots.
  4. A planet siege with the v3.11 landing combat.
- Caution: under v3.11 the turn regen reads the wall clock, so re-executing actions may not give the same turn counts. P4 either records regen in the action log or adds an event-playback mode that streams `events.jsonl` with recorded timing. Pass bar: a replay of a v3.11 save ends with the same standings.
- Serving: one shared replay worker per demo, started on demand, hibernated when nobody watches. Speed control is per viewer in the browser, not on the shared worker.
- Live always-on demo: one worker, bots only (2 Easy + 2 Hard), v3.11 rules, 500 sectors, 10-minute days, new seed after each game over. Full spectator view (no humans, so no fog problem). Shown on `tw2002.html` in an iframe (read-only). About 0.2 vCPU and 300 MB.

## 11. Step-by-step tutorials

In-game: a "Tutorial" game type (fixed seed, 100-200 sectors, solo, v3.11 starting package, Ferrengi off until lesson 7). A coach panel in the cockpit shows the goal, the key to press, and a hint. A step is done when a check on the seat's own observation passes (new `src/tw2k/public/tutorial.py`; reuse ideas from `copilot/ui_agent.py` `button_hints` and `suggest_next_move`).

| Lesson | You learn | Done when |
|---|---|---|
| 1 Read the screen and move | Sector line, warps, turns per warp, `M` move, course plot | You warp 3 times and plot a course |
| 2 First trade | Port classes (BBS, SBB ...), dock, buy where the port sells, sell where it buys, the haggle | One buy and one sale with a profit |
| 3 Port pairs | Computer R port report, Computer K, find a pair next to each other, profit per turn | Three round trips on one pair |
| 4 StarDock | Hold prices, fighters, shields, scanners, the ship catalog, the bank | You buy holds and deposit credits |
| 5 First planet | Genesis torpedo, Terra colonists (1,000 per hold under v3.11), land, assign colonists, production | A planet with colonists producing |
| 6 Citadel | Class goods cost (no credits), build days per class (RULINGS s3), L1 treasury, L2 military reaction | Citadel L1 started (day length shortened for the lesson) |
| 7 Combat | Deploy fighters and their modes, toll, attack with fighters, the flee rule, pods, Ferrengi | You clear a fighter group and survive a Ferrengi |
| 8 Corporations (optional) | Create, invite, corp credits | You create a corp |

On the site: the same lessons as static pages on Netlify (`tw2002/tutorials/1.html` ... `8.html`), with screenshots taken by the cockpit visual QC harness (`tests/test_cockpit_visual_qc_v1.py`) at 1920 and 390 px. Each page ends with "Try this lesson", linking to `https://play.<domain>/tutorial/<n>`. Numbers on the pages come from the game's Rules and Help (`server/reference.py`) so they match the rules in force.

## 12. Wiring up every existing option

Legend: Public = shown on the New Game screen; Server = set by the lobby per game type, not by the user; Internal = fixed, never exposed; Retire = no effect, remove later.

### 12.1 Engine switches in `src/tw2k/engine/constants.py`

| Group | Switches | Exposure |
|---|---|---|
| Rules profile | `V311_PROFILE` | Public (Rules field) |
| The v3.11 set (60, `V311_PROFILE_HELPERS`) | `STARTING_PACKAGE_MODE`, `CITADEL_DAYS_MODE`, `CITADEL_COST_MODE`, `SHIP_ROSTER_MODE`, `TURN_REGEN_MODE`, `LIVE_PACE_MODE`, `OFFENSIVE_CLASH_MODE`, `TAX_RULE_MODE`, `FEDSPACE_DEPLOY_MODE`, `PORT_CLASS_MAP_MODE`, `HAGGLE_WINDOW_MODE`, `OWN_PLANET_TURN_MODE`, `TRADE_IN_MODE`, `HARDWARE_PRICE_MODE`, `PLANET_SHIELD_ACTIVE_MODE`, `GENESIS_SCORE_MODE`, `ACTION_RESULT_MODE`, `ASSIGN_POOL_FIX_MODE`, `HOLD_RULES_MODE`, `PLANET_NW_MODE`, `PORT_PRICE_MODE`, `PORT_REGEN_MODE`, `SHOP_PRICE_MODE`, `GENESIS_START_MODE`, `TERRA_COLONIST_MODE`, `PLANET_PROD_MODE`, `CITADEL_PERK_MODE`, `EXP_SCORE_MODE`, `DEATH_POD_MODE`, `PORT_ATTACK_MODE`, `HAGGLE_LIVE_MODE`, `DISCOVERY_EXP_MODE`, `FED_SHIPS_MODE`, `DETECT_GEAR_MODE`, `AVOID_MODE`, `OWN_PLANET_FIGHTER_MODE`, `RANK_DISPLAY_MODE`, `API_ARGS_MODE`, `PLANET_COLONIST_CAP_MODE`, `LANDED_STATE_MODE`, `PLANET_DIVIDEND_PAY_MODE`, `PLANET_VALUE_SCORE_MODE`, `PLANET_SCANNER_MODE`, `SCANNER_FOG_MODE`, `CITADEL_PARK_MODE`, `RADIO_CHANNEL_MODE`, `DAILY_STATS_MODE`, `FEDCOMM_MODE`, `CORP_RANK_MODE`, `CLASS_M_FIDELITY_MODE`, `PORT_STOCK_FIDELITY_MODE`, `SHIP_EXIT_MODE`, `RIVAL_STRENGTH_MODE`, `PLANET_LANDING_COMBAT_MODE`, `OWNER_HAZARD_NOTICE_MODE`, `SHIP_FLEE_MODE`, `PLANET_SHIELD_MODE`, `FERRENGI_ENGAGE_MODE`, `SIEGE_REPORT_MODE`, `PLANET_GROWTH_MODE` | Only through the profile. Not one by one. |
| Added by NOTE 59 (in progress) | `KILL_CASH_MODE` (killer not paid), `POD_CASH_MODE` (pod keeps 25 credits) | Through the profile |
| "No" list (not original, or not yet safe) | `PORT_OPEN_STOCK_MODE`, `PLANET_CLASS_MODE`, `BANK_LIVE_MODE`, `ALLIANCE_MODE`, `PLANET_REALTIME_PROD_MODE`, `UNIVERSE_TOPOLOGY_MODE`, `GOLD_ALIEN_MODE` | Internal at launch. P6 may add a "House rules" panel for `ALLIANCE_MODE` and `GOLD_ALIEN_MODE`, clearly marked "not in the original". `UNIVERSE_TOPOLOGY_MODE` stays internal until bots escape dead ends (MASTER_PLAN DAY-g). |
| No-op names | `TRADE_TURN_MODE`, `WARP_COST_MODE`, `ALIGNMENT_MODE`, `RANK_TITLES_MODE`, `COMBAT_ODDS_MODE`, `CORP_RULES_V2_MODE`, `COCKPIT_PARITY_MODE` | Retire |
| Match infrastructure | `SEAT_DEADLINE_MODE`, `ASYNC_DAY_MODE` (env `TW2K_SEAT_DEADLINE_MODE`, `TW2K_ASYNC_DAY_MODE`) | Server (multi-human games) |
| Harness extras | `COCKPIT_FIELDS_MODE` | Server (recommend on in public; Ben decides) |
| Test only | `AI_COCKPIT_SEAT_MODE` | Internal |
| Old profile | `TW2002_LIVE_PROFILE` (also turns on the "No" list) | Internal; never offered |
| Already original by default | `ECONOMY_SCALE_MODE`, `CITADEL_FIDELITY_MODE`, `PLANET_ECONOMY_MODE`, `SECTOR_FIGHTER_MODE`, `COMBAT_MODE`, `DEATH_MODE`, `INFO_MODE`, `RANK_MODE`, `ROB_MODE`, `HARDWARE_MODE`, `FERRENGI_MODE`, `CLASS0_MODE`, `SHIELD_PRICE_MODE`, `FED_OUTPOST_MODE`, `NET_WORTH_MODE`, `BUY_RESERVE_MODE`, `PLANET_DIVIDEND_MODE`, `HUNT_MODE`, `COMBAT_FRAMING_MODE`, `SLOW_HULL_HINT_MODE`, `COMBAT_SCANNER_MODE`, `GENESIS_HULL_MODE`, `MINE_OVERFLOW_MODE`, `FED_MODE`, `ISS_REPO_MODE`, `SHIP_TW_MODE`, `FLEET_MODE`, `CAPTURE_MODE`, `CORPSHIP_MODE`, `TOW_MODE`, `PLANET_TRADE_MODE`, `PORT_UPGRADE_MODE`, `BANK_MODE`, `TAVERN_MODE`, `STARDOCK_EXTRA_MODE`, `CORP_MODE`, `CORP_FIX_MODE`, `ROGUE_KEEP_MODE`, `ALIEN_MODE` | Internal |
| Bot behaviour | `BOTS_BANK_MODE`, `H_RECOVERY_MODE`, `BOTS_WAR_MODE`, `BOTS_TAVERN_MODE`, `BOTS_DEPLOY_MODE`, `CORP_BOTS_MODE` | Internal |
| LLM prompt shaping | `LLM_PARITY_MODE`, `LLM_PLANET_NUDGE_MODE`, `LLM_QUASAR_NUDGE_MODE` | Internal |
| Constants that matter publicly | `TURN_REGEN_DAY_SECONDS` (day length), `SEAT_DEADLINE_S`, `ASYNC_DAY_CAP_S`, `API_RETRY_LIMIT` | Day length is Public (v3.11 only); the rest Server |

The worker applies the overlay once, before `generate_universe`, and writes every switch value into `meta.json` (new `switches` key, `schema_version` 2).

### 12.2 `GameConfig` (`engine/models.py`)

| Field | Exposure |
|---|---|
| `seed`, `universe_size`, `max_days`, `turns_per_day`, `all_start_stardock`, `enable_ferrengi`, `ferrengi_*` (5), `one_way_fraction`, `play_to_day_cap`, `elimination_deaths`, `enable_planets`, `enable_corps` | Public (section 5) |
| `starting_credits` | Public advanced, legacy rules only |
| `corp_max_members` | Server (set from seat count, as `_build_default_spec` does) |
| `llm_think_cap_s` | Server (60 s cap in public) |
| `action_delay_s` | Server (0.6 s default; demo worker may slow it) |
| `avg_warps`, `planet_spawn_probability` | Internal |

### 12.3 `MatchSpec` and `AgentSpec` (`server/runner.py`)

| Field | Exposure |
|---|---|
| `paused`, `pause_on_seat_drop`, `seat_drop_after_s` | Server (solo and short-day games pause when the human leaves) |
| `human_deadline_s` | Internal (`HumanAgent` is not used publicly) |
| `external_timeout_s`, `external_idle_wait_s`, `external_attend_window_s`, `external_hold_max_actions` | Server, per game type |
| `AgentSpec.kind`: `heuristic` / `llm` / `external` / `human` | Bots / your AI / humans and your own bot / internal |
| `provider`, `model` | Public for AI seats (curated list) |
| `custom_base_url`, `custom_api_key`, `custom_max_tokens` | Internal until the SSRF guard; key handling per 4.6 |
| `external_token`, `external_timeout_s` | Server (token minted by the lobby) |

### 12.4 CLI (`src/tw2k/cli.py`)

| Command / option | Exposure |
|---|---|
| `serve` with `--host --port --seed --universe-size --max-days --num-agents --agent-kind --turns-per-day --starting-credits --agent-names --action-delay-s --external --external-timeout-s --external-seat-timeouts --external-tokens-file --external-idle-wait-s --start-paused --pause-on-seat-drop --seat-drop-after-s --play-to-day-cap --all-start-stardock --one-way-fraction --no-ferrengi --ferrengi-* --port-stock-fidelity --haggle-live --no-auto-start` | The lobby's worker launcher uses these (the spec mapping above). New: `--profile`, `--day-seconds`, `--switches-file`, `--public-prefix`. |
| `serve --provider --model --agent-providers --agent-models --human --human-deadline-s` | Internal (public AI seats are created by the lobby, not by CLI lists) |
| `replay` | Server (demo and finished-game replays) |
| `sim`, `human-sim`, `probe` | Internal (P0 measurements use `sim`) |
| `mcp` | Public as documentation for mode A (runs on the user's machine) |

### 12.5 Environment variables (names only; values are never printed)

| Variable | Exposure |
|---|---|
| `COCKPIT_LAYOUT` | Server: `redesign` on every public worker |
| `TW2K_SPECTATOR_TOKEN` | Server: per worker, minted by the lobby |
| `TW2K_HARNESS_ALLOW_REMOTE` | Server: on behind Caddy (tokens are the guard) |
| `TW2K_EXTERNAL_TOKENS_FILE`, `TW2K_EXTERNAL_TOKEN_<PID>` | Server: per-game tokens file, 0600 |
| `TW2K_PUBLIC_BASE_URL`, `TW2K_HARNESS_BASE_URL`, `TW2K_SEAT_LINKS_DIR` | Server: `https://play.<domain>/g/<id>` |
| `TW2K_SAVES_DIR` | Server: `/srv/tw2k/data/games/<id>/saves` |
| `TW2K_EXTERNAL_TIMEOUT_S`, `TW2K_EXTERNAL_IDLE_WAIT_S`, `TW2K_THINK_CAP_S` | Server |
| `TW2K_SEAT_DEADLINE_MODE`, `TW2K_ASYNC_DAY_MODE` | Server (multi-human) |
| `TW2K_PORT_STOCK_FIDELITY`, `TW2K_HAGGLE_LIVE` | Internal (covered by the profile) |
| `TW2K_HINT_LEVEL` | Internal (`full`) |
| `TW2K_VIDEO_CUSTOM` and the media provider keys | Internal; off in public (paid video generation) |
| `TW2K_BRIDGE_DIR`, `TW2K_GROKBOT_WEBHOOK_*` | Internal; off in public |
| `TW2K_COPILOT_PROVIDER`, `TW2K_COPILOT_TRACE` | Internal (copilot not public at launch) |
| `TW2K_COST_OVERRIDES_PATH` | Server (price table updates) |
| Provider keys `XAI_API_KEY`, `GROK_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `TW2K_CUSTOM_API_KEY` | Never set on public workers. With no server key, `default_provider()` returns `none` and `agent_kind=auto` resolves to `heuristic`, so no game can bill Ben by accident. |
| `TW2K_*_MODEL`, `TW2K_CUSTOM_*`, `TW2K_CURSOR_*`, `TW2K_XAI_*` | Internal |
| `TW2K_MCP_TOKEN` | Mode A documentation only |
| OpenTelemetry vars (`copilot/otel.py`) | Internal |
| New: `TW2K_PUBLIC_MODE`, `TW2K_PUBLIC_PREFIX` | Server |

### 12.6 HTTP routes (`server/app.py`, `server/harness.py`)

| Route | Public exposure |
|---|---|
| `/bot` (redesign), `/bot/claim`, `/static/*` | Yes |
| `/harness/v1/{seat}/status, observation, events, reference, action, hold`, `/harness/v1/rules`, `/harness/v1/seats` | Yes, seat token; `seats` reviewed so it lists no tokens and no hidden info |
| `/harness/v1/{seat}/macro` (`run_route`) | Yes (it is a cockpit convenience; keep it within one held slot) |
| `/harness/v1/{seat}/webhook_test`, `/harness/v1/bridge*`, `/harness/v1/{seat}/media/*` | No |
| `/`, `/state`, `/events`, `/history`, `/highlights`, `/ws` | Spectator rules (section 7) |
| `/control/*` | No (lobby only, over loopback) |
| `/api/cost` | Owner of an AI seat, own seat only (new filter) |
| `/api/ai-directives*` | No; replaced by `/harness/v1/{seat}/orders` |
| `/api/human/*`, `/api/match/humans`, `/api/copilot/*`, `/api/economy/*`, `/play` | No |
| `/bot2` | No (same page as `/bot` redesign) |
| New: `/healthz`, `/public/v1/stats`, lobby `/lobby/v1/*` | Yes |

Multi-game per process (needed only near 1,000 players): move every switch read behind a per-game context (for example a `Rules` object on `GameConfig` passed to the helpers) so one process can host many games. That touches hundreds of helper calls across the engine. It is a large, engine-wide change and is out of scope until P7 shows it is needed.

### 12.7 Save and load

1. P0: `meta.json` gets `switches` and `schema_version: 2`.
2. P2: a snapshot at each day tick and on hibernate: `Universe.model_dump_json()` gzipped, plus the RNG state, per-seat turn-regen clocks (`turn_regen_frac` and timestamps), and code-bot memory where a bot keeps it.
3. Resume = load the newest snapshot, then apply the actions logged after it.
4. Test: kill a worker mid-day, resume, and compare a state digest with an uninterrupted run, for legacy and for v3.11 with a short day.
5. Players see "Saved" after every day tick. There is no manual "load an old save" for players (it would let them undo deaths); the admin can roll a game back.

### 12.8 Scaling

- Process model: lobby (1 process) + one worker per active game + Caddy. Workers bind 127.0.0.1 only.
- Admission: the lobby caps active workers per host (start: 6 per vCPU, tuned by P0 data) and hibernates the longest-idle game when it needs room.
- Horizontal: hosts table in SQLite; new games go to the least-loaded host; each host has its own Caddy and name (`h1.play.<domain>`), and the lobby redirects to it. Moving a hibernated game = copying its directory.
- Load test before each tier: 30 simulated humans (scripted cockpit clients over HTTP) + bots for 2 hours.

### 12.9 Monitoring and alerts

- `/healthz` on lobby and workers; an external uptime check every minute.
- Metrics: active games, hibernated games, wakes per hour, worker crashes, 5xx rate, p95 action latency, harness 429s, LLM fallbacks, new games per hour, RAM, CPU, disk.
- Alerts (email or Discord webhook to Ben): host down 2 min; disk over 80%; RAM over 85% for 10 min; a worker crash loop (3 in 10 min); 5xx over 2% for 5 min; new games per hour over 5 times the weekly normal (abuse); backup job failed.
- Error tracking is optional and must use the same scrubbing filters as the logs.

### 12.10 Backups

- Nightly restic snapshot to object storage of `/srv/tw2k/data` (SQLite through `.backup`, games, snapshots). Keep 7 daily, 4 weekly, 3 monthly. Encrypted by restic; the repository password lives only on the server and in Ben's password manager.
- Weekly provider snapshot of the VPS (+20% on Hetzner).
- Restore drill monthly: new VPS, restore, start the lobby, open a resumed game. Target under 1 hour.

## 13. Phased milestones

Each milestone is one or two NOTE-sized slices of 5-8 items. Standing pass bar for every slice that touches the repo: all tests green; legacy default games unchanged (bank pin `9b607d3dae940c0b1a69f6d7`, 10-day digests `24863a3d` / `98a47c8a`); `/bot` legacy page byte-identical; new behaviour behind a legacy-default flag; v3.11 10-day soak rejected 0, exceptions 0.

**P0 public-hardening (local, no hosting)**
1. Measure RAM and CPU of one worker: 200 / 1,000 / 2,000 sectors, 1 cockpit seat + 3 bots, 10 days, legacy and v3.11 (short day). Write `docs/playtests/public-web/p0-sizing.md`.
2. `TW2K_PUBLIC_MODE` (off by default) with the lockdown of 4.2.
3. `agent_fallback` publishes a reason code only in public mode.
4. XSS: `esc()` escapes quotes in `web/redesign.js` and `web/app.js`; audit every name and message site; server-side name rules.
5. `meta.json` `switches` record, `schema_version` 2.
6. `/healthz` on the worker.
7. Per-token rate limit middleware on the harness.
8. Test: no token gets 401 through a local reverse proxy (loopback check is void there).
Pass: standing bar; a 10-day local run in public mode shows no 5xx and zero secret patterns in logs.

**P1 lobby and one worker per game (local)**
1. `src/tw2k/public/lobby.py` (FastAPI) + SQLite schema (sessions, games, seats, hosts).
2. Worker launcher: `tw2k serve` per game with port, saves dir, tokens file, switch overlay (`--profile`, `--day-seconds`).
3. New Game form (Rules, size, days, turns per day, day length, bots, Ferrengi, start location).
4. Guest session cookie; display names; recovery link.
5. Base path `/g/<id>/` in the redesign and spectator pages; claim cookie path per game.
6. Resume through token rotation; "My games" list.
7. Playwright test: create a game, play 10 actions in the cockpit, reload, resume.
Pass: two games with different rules run at once on one machine and each keeps its own switches (checked through `/harness/v1/{seat}/reference`).

**P2 persistence and hibernation**
1. Day-tick and hibernate snapshots; resume from snapshot + actions.
2. Idle hibernation and the waking page.
3. Away seats skipped without spending a turn (new legacy-default flag).
4. Reaper for idle and finished games.
5. In-process adapter for SeatBrain N2/N3 bots (Normal/Hard).
6. Resume-equals-continuous digest test (legacy and v3.11).
Pass: kill -9 mid-day resumes to the same digest; 50 hibernate/wake cycles show no drift.

**P3 closed beta on the VPS**
1. `deploy/` (new): compose file, Caddyfile, systemd unit, provisioning notes.
2. Domain, DNS, TLS; firewall 80/443; SSH over Tailscale.
3. restic backups and a restore drill.
4. Uptime check, metrics, alerts.
5. Admin kill switch and admin port.
6. Abuse limits of 4.1.
7. Netlify: `tw2002.html`, redirects, home card (portfolio PR).
Pass: restore drill under 1 hour; SSL Labs grade A; 10 invited testers for one week; uptime over 99%; zero secrets in a week of logs.

**P4 spectate, demos, tutorials v1**
1. Public board.
2. Spectator rules of section 7 with per-game tokens.
3. Live demo worker + iframe on `tw2002.html`.
4. Three curated replays; replay of a v3.11 save gives the same standings.
5. Tutorial game type and coach panel, lessons 1-4.
6. Static tutorial pages 1-4 on Netlify.
7. Phone smoke test at 390 px.
Pass: a new player finishes lessons 1-4 without help in under 30 minutes (3 testers).

**P5 your own AI**
1. AI seat with an in-memory key (mode B), four providers, curated models.
2. Cost estimate before start; live cost; spend cap.
3. Timeouts and fallback with owner notice.
4. Mode A docs and a "connect your own bot" page.
5. Owner token for `llm` seats and `POST /harness/v1/{seat}/orders` (text).
6. Orders panel (text) and AI acknowledgements.
Pass: a test key never appears in logs, events, snapshots, `meta.json` or other seats' responses (automated search); a revoked key falls back within one turn.

**P6 accounts and voice**
1. Sign-in (magic link or OAuth), merge guest games.
2. Opt-in encrypted key storage, delete, account deletion.
3. Push-to-talk orders with browser speech; quick commands; confirm on risky orders.
4. Spoken readouts.
5. Tutorials 5-8 in game and on the site.
6. House rules panel (`ALLIANCE_MODE`, `GOLD_ALIEN_MODE`, marked not original).
Pass: voice order to acknowledgement in under 3 s in a solo game (Chrome); Firefox falls back to text cleanly.

**P7 open launch and scale out**
1. Public lobby list and joinable seats.
2. Second host and placement.
3. Load test to 100 concurrent players.
4. Leaderboards (experience under v3.11).
5. Decide on multi-game-per-process (switch refactor) from P0 and load-test data.
Pass: 100 simulated players for 2 hours, p95 action latency under 300 ms, no worker crash.

## 14. Risks

| Risk | Effect | Mitigation |
|---|---|---|
| Name and trademark: "Trade Wars 2002" is a trademark of its owners | Public hosting under that name may draw a complaint | Ben decides the public name (open question 9) |
| Module-global switches | One process per game; RAM cost at scale | P0 numbers; refactor only if needed (12.6) |
| Wall-clock turn regen | Replays and resumes may drift | Snapshots carry regen clocks; replay test in P4 |
| Worker memory grows (`Universe.events`) | Long games use more RAM | P0 measures; cap or spill old events to disk if needed |
| XSS through names and messages | Account and seat takeover in the browser | P0 escape audit before any public game |
| Key leak through errors | User keys exposed to spectators | Reason codes only; automated leak search in P5 |
| `/control` and `/api` open by default | Anyone could restart a game or read all prices | `TW2K_PUBLIC_MODE` lockdown in P0 |
| Single VPS | Outage takes every game down | Backups, restore drill, second host in P7 |
| LLM cost surprises for users | Angry users | Estimates, live cost, spend caps, BYO only |
| Browser speech privacy and support | Users surprised; Firefox users lose voice | Disclosure; text always works |
| Long real-time games | Players drift away; disk fills | Hibernation, reaping, short day-length options |
| v3.11 balance: class M L1 needs 1,000,000 colonists, the start planet has 191,000 (`docs/playtests/v311-profile-v1/README.md`) | Citadels feel out of reach | Ben's call on class M ratios (NOTE 41 item 10); tutorial lesson 6 uses a shortened setup |

## 15. Open questions for Ben

1. Which domain, and may `play.<domain>` point at a VPS?
2. Hetzner (cheapest, we run it) or Fly.io (less admin, 2-4 times the cost)? US or EU region?
3. Guest-only at launch, sign-in later: OK?
4. Public default rules v3.11: OK? Default day length for v3.11 games (24 h original or 1 h)?
5. Spectator policy for games with humans: public board only, full replay after the game?
6. `COCKPIT_FIELDS_MODE` on for public games?
7. Admission cap at launch (30 active games)?
8. Should Ben's server ever pay for any AI or speech (for example the live demo with an LLM seat), or is it BYO only?
9. Public name of the game.

## 16. Rough monthly cost (estimates, re-check)

| Stage | Items | USD per month |
|---|---|---|
| Closed beta (P3) | Hetzner CPX31 ~$17, provider backups ~$4, object storage ~$1-5, domain ~$1.5, uptime and alerts free tier | about $25-30 |
| 100 concurrent players | Hetzner CPX51/CCX33 ~$65-75, backups ~$15, storage ~$5, mail for sign-in $0-15 | about $90-110 |
| 1,000 concurrent players | 3-4 dedicated-CPU hosts ~$800-1,100, storage ~$20, mail ~$15-30 | about $850-1,200 |
| Same, on Fly.io instead | Machine per game | about $40-70 / $300-450 / $2,500-3,700 |
| AI and voice | Paid by each user with their own key | $0 to Ben |
