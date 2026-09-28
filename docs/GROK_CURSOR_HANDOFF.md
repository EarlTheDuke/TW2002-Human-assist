# GROK - CURSOR HANDOFF - TW2K Multi-Bot Edition

**Living doc.** Commander (Grok Bot) <-> Cursor (Fable). Ben may be AFK - prefer the AFK loop; do not block on questions.

| Field | Value |
|-------|--------|
| Project root | this repo |
| Orchestrator | **Commander** (Grok Bot) |
| Coder (~99%) | **Cursor / Fable** (local Agent on VENGEANCE) |
| AFK mailbox | `docs/COMMANDER_NEXT.md` |
| Plan (current) | `docs/plans/2026-09-21-bot-human-parity.md` |
| Branch target | `feature/grok-bot-harness` |
| Status | **COMMANDER_WORKING - multi-bot playtest** |
| Prior | Phase 2 external harness COMPLETE @ e1fa90b (2026-09-20) |

---

## Current mission (2026-09-21)

Host TW2K on a reachable URL with a **bot-playable `/bot` UI**. Commander plays via **computer use**. Insights from that play become the next fix backlog. No xAI keys ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Grok Bot is the player.

Phases: A Cursor polish/smoke ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ B host URL ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ C Commander CU playtest ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ D insights doc ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ loop.

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

### 2026-09-28 10:25 PT - Fable - the death-card close keeps the escape pod
- The × on the death card, and a click on the card backdrop, use the same Skip path as Escape. The escape pod still plays. A second close ends the pod. Turning the viewport off, or a still that fails to load, still clears everything. Suite 750 passed; ruff clean; manifest OK.

### 2026-09-28 09:24 PT - Fable - Skip ends the death clip and leaves the escape pod
- Skip during ship destruction plays the escape pod. A second Skip ends the pod. Skip on any other clip still clears the queue, and each Skip is counted. Quick-trade names and totals sit a space apart. Suite 749 passed; ruff clean; manifest OK.

### 2026-09-28 08:03 PT - Fable - trade names stay whole on the button
- Quick-trade buttons keep the short name and the credit total, wrapping to another row or a second line instead of shrinking the name away. Plotting the sector you are in says you are already here. A negative or zero target asks for a valid sector. Suite 748 passed; ruff clean; manifest OK.

### 2026-09-28 06:45 PT - Fable - trade buttons show the list-price total
- One-click sell and buy buttons include price times quantity. The plot form names the hop count and first sector from warps this seat already has, or says the route is shown after plotting. The mode=cu turn card uses the same remembered port codes as the warp buttons. An SBB port marks organics and equipment, not fuel, and an empty hold marks nothing. STARDOCK on the neighbour buttons stays inside 1440x900, 1280x800, and the one-screen CU page. Suite 746 passed; ruff clean; manifest OK.

### 2026-09-28 05:45 PT - Fable - warp buttons show a remembered port code
- A warp button names the port only when this seat already remembers that sector. The port table marks a commodity you hold when the port buys it. Default and mode=cu stay inside 1280x800, and the S / 1-9 hints stay. Suite 742 passed; ruff clean; manifest OK.

### 2026-09-28 04:45 PT - Fable - default cockpit scans with S and warps with 1-9
- S and 1-9 on the default page do what they do in mode=cu, and they stay quiet in a form, on a repeated key, or when the verb is not legal. A chained pod's timer restarts when it reaches the front of the queue. The manifest report prints the clip budget and the stills total separately. Suite 740 passed; ruff clean; manifest OK.

### 2026-09-28 03:20 PT - Fable - death then the escape pod stay in order
- Incoming fire no longer skips the death clip, and a later action from this seat no longer drops the queued pod. StarDock's sector comes from the manifest. Designed stills count on their own. Suite 737 passed; ruff clean; manifest OK.

### 2026-09-28 02:26 PT - Fable - placeholder triggers for later viewport moments
- StarDock, planets, weapons, mines, death and the escape pod, hail, and game over each resolve to a still. Death keeps the pod ahead of anything less urgent. Preload fetches clip video only in Live, posters only when the viewport is not Off, and drops the blobs after the fetch. Suite 733 passed; ruff clean; manifest OK.

### 2026-09-28 01:05 PT - Fable - hashed clips preload from cache
- Idle preload fetches the approved P0–P2 webms after the page is interactive, stops at the 12 MB / 3.5 MB caps, and skips that work when saveData is on. A second load plays those clips with 0 bytes transferred. A missing-port route says there isn't enough port intel. Suite 730 passed; ruff clean; manifest OK.

### 2026-09-28 00:20 PT - Fable - a failed clip cannot hide the next one
- Each clip has its own token, so a leftover play error from a missing file does not hide or double-count the clip that replaced it. The approve catalog stays beside the manifest you pass in. Suite 729 passed; ruff clean; manifest OK.

### 2026-09-27 23:21 PT - Fable - approve refuses stand-ins; missing clips fall back each time
- The approve script only touches real pilot takes and writes the same approval into the clip catalog, so a rewire cannot restore an old one. A missing video falls back on the last source, and the next missing clip does too. Suite 727 passed; ruff clean; manifest OK.

### 2026-09-27 22:30 PT - Fable - approved clips play, stand-ins stay the fallback
- The 14 pilot clips play by default. A ffmpeg stand-in stays first with approved_by null, and fallback_still stays. Approve or unapprove one take or the batch with scripts/media_approve_clips.py. Swap a file with scripts/media_swap_clip.py. The window background stays the canvas starfield. Suite 725 passed; ruff clean; manifest OK.

### 2026-09-27 20:41 PT - Fable - route form clears a stale refusal
- Opening REPEAT ROUTE hides a previous rejection. A pair is suggested only when each known port buys what the other sells. Suite 718 passed; ruff clean; manifest OK.

### 2026-09-27 20:05 PT - Fable - CU banner countdown stays whole
- The WAITING line is a phrase plus a separate countdown. A long actor name ellipsizes. The seconds stay fully visible. Suite 717 passed; ruff clean; manifest OK.

### 2026-09-27 16:30 PT - Fable - CU top bar keeps the status line
- The turn banner shrinks and ellipsizes. Credits, status, and seat do not shrink, so a long status line stays inside its cell. The CU Refresh button uses the cockpit button style. Suite 717 passed; ruff clean; manifest OK.

### 2026-09-27 16:00 PT - Fable - visible Refresh in mode=cu
- The Refresh button moves onto the `mode=cu` top bar (`#cuScreen`, testid `refresh`). A click refetches and does not post an action. The default layout keeps it on the auth bar.
- A 404 or 500 from `manifest.json` sets `manifestFailed` and clears the pending event queue, same as a dropped fetch. Suite 717 passed; ruff clean; manifest OK.

### 2026-09-27 15:15 PT - Fable - one-click trades on the default layout
- The default layout gets `quick-sell-<commodity>` / `quick-buy-<commodity>` under the verb pad: max qty, list price, no form. They hide when a trade is not legal right now. SELL/BUY still open the form. `mode=cu` keeps `cu-quick-*`.
- Events that arrive before the manifest loads stay in one capped queue (history first). A failed manifest fetch clears that queue so it cannot grow or play late. Suite 715 passed; ruff clean; manifest OK.

### 2026-09-27 14:30 PT - Fable - amz-1 fix
- A scan (and any other non-clip) on the default layout plays inside the viewport. The floating HUD is not shown, so it cannot cover the ship.
- Connect keeps paging `/events` as history until the first response's `latest_seq`, or until a page comes back empty. A 310-scan log does not play.
- A history batch calls the resolver even when the manifest has not loaded yet, and applies it again once the manifest arrives. Nothing plays. Suite 713 passed; ruff clean; manifest OK.

### 2026-09-27 13:40 PT - Fable - amz-1 first look
- The first `/events` batch after connect sets `lastSeq` and visit/dock state and does not play. Later batches still play `dock.port` in the viewport.
- The full-window HUD stays `pointer-events: none` when shown; only the card takes clicks. CU `viewport=off` does not play a non-clip event (a scan) into the hidden slot.
- Stage detail is a block under `#sbStage`. The default baseline no longer expects `media-hud-dismiss` visible on load. Suite 711 passed; ruff clean; manifest OK.

### 2026-09-27 12:35 PT - Fable - V4 nits + make-it-amazing plan
- Default H ignores key-repeat, empty `key`, and contentEditable targets.
- `mode=cu&viewport=off` does not record a clip cooldown and does not play into the hidden slot. A witnessed combat on that page leaves `playedKeys` without `combat.witnessed` and the HUD hidden.
- `benchSwap` restores the caption and `data-swap` it touched. The number is resolve plus that write only (no image decode, no layout). The CU timing guard is +5% plus 25 ms.
- Plan: `docs/plans/2026-09-27-cur-make-it-amazing.md`. Offline notes: HUD covered the ship, stage detail overlapped the stage, default SELL was an 8-control form, CU Refresh was not visible, seat brain 6/6 ok. Suite 710 passed before the plan doc; ruff clean.

### 2026-09-27 11:35 PT - Fable - grokbot-player V4-lite delivered
- Hashed files under `web/media/` (`name.<8+ hex>.ext`) get `Cache-Control: public, max-age=31536000, immutable`. `manifest.json` and other media files get `no-cache`. Other `/static` files are unchanged. `MediaStaticFiles` in `src/tw2k/server/media_cache.py`.
- After load, `requestIdleCallback` preloads unique posters for clip priorities 0–2, capped at 12 MB of blobs. It does not run in `mode=cu`, with reduced motion, or when `navigator.connection.saveData` is set. Bytes fetched before the document is interactive stayed at 0 (the fetch starts after `load`).
- Session counters (plays, skips, preemptions, stale-drops, poster-fallbacks) live in `sessionStorage` and render in the Raw observation drawer. No network.
- `mode=cu` defaults to stills in `#cuMediaSlot` (instant swap, no video). `?viewport=off` hides the slot with `visibility: hidden` so the height stays. `?viewport=live` is allowed and labeled in the player guide as not for scored CU play; with placeholders it is still a poster.
- Resolve+swap p95 0.10 ms over 40 warp-burst iterations (budget 4 ms). That bench is resolve plus a caption/attribute write only: it excludes image decode and layout, and it restores the caption afterwards. CU scan-to-toast median: viewport off 168 ms, stills 161 ms (−3.7%). The guard is +5% plus 25 ms slack (`stills <= off * 1.05 + 25`), the same slack as the V1 click-to-result test.
- G7 nits: H toggles hold on the default layout as well as `mode=cu` (the button already said `(H)`). The 401 test fails only `/events` and presses R, because the refresh button is hidden once `mode=cu` is connected.
- `tests/test_video_cockpit_v4.py` (4). Suite 709 passed; ruff clean; manifest OK (16 stills).

### 2026-09-27 10:40 PT - Fable - grokbot-player G7 delivered
- Player guide section 9 (`docs/GROK_BOT_PLAYER_GUIDE.md`): seat claim link, both `/bot` layouts, status line (Day N of M, GAME OVER), CU keys, one-click trades, RUN ROUTE, END SLOT, reconnect banner, Live/Stills/Off + Skip + reduced motion. No screenshots.
- `docs/SEAT_BOT_NOTES.md`: all 46 `Observation` fields (checked against `observation.py`), banned god-state, and the `seat_brain.py` goal ladder. `status_line` is harness-only, not an Observation field.
- Event log dedupes by `seq` (`web/bot.js`). A 401/403 from `/events` stops the `/bot` poll and shows the reconnect banner. Spectator `/history` also stops on 401/403; that page has no banner.
- END SLOT uses the same solid green primary style as SCAN on the default layout (`hold-slot`) and in `mode=cu` (`cu-hold`).
- A viewport clip hides the v1 HUD. Off does not record cooldown for a clip that did not play. Live manifest drops unused `max_queue` and `crossfade_ms` (schema and the v2 example still allow them).
- `:8031` host logs in the main folder had host/tunnel URLs replaced with `<redacted>`. Those files are not in git.
- `tests/test_g7_pilot_items.py` (2) plus tighter HUD asserts and an Off-cooldown replay in `tests/test_video_cockpit_v2.py`. Suite 705 passed; ruff clean; manifest OK (16 stills).

### 2026-09-27 09:37 PT - Fable - video cockpit V2 QC fixes delivered
- Dismiss (Skip, Esc, viewport click, HUD x) calls `session.stop()`, so the next poll cannot redraw the clip. The CU auto-hide timer uses the same finish path as the viewport timer, and a clip renders only when `consider()` actually started one.
- Stills is a poster only (no `vp-push` / tint, no video src). Off silences a resolved clip: no viewport layer, no caption change, and that clip is not copied onto the v1 HUD. Events that resolve to no clip still use the v1 HUD, except in Off. CU stays a HUD still, not Off.
- A waiting clip keeps `sector_id` through `finish()`, so the promoted caption is not "Docking at " with an empty sector. A newer self action drops a waiting clip (`postedSeq`).
- `tests/test_video_cockpit_v2.py`: skip then a scan does not replay; CU timer then a scan does not restore the dock HUD; Live / Stills / Off on one resolved clip; promoted dock keeps sector 19; `_exchange_outcome` hit, miss, destroyed, attacker destroyed, both at 0, and the Ferrengi path. Suite 703 passed; ruff clean; manifest OK.
- Left unused: manifest `max_queue` (queue is hard-coded to 1) and `crossfade_ms`. Did not chase the default `/bot` console 404.

### 2026-09-26 22:07 PT - Fable - video cockpit V1 (viewport shell) delivered
- Default `/bot` middle column gets `#viewport`: procedural canvas starfield seeded by the seat's own sector (station glyph when a port is present, FedSpace tint), per-hull CSS cockpit frames (hauler / light / heavy / capital from `ship.class`), caption strip, Skip, Live / Stills / Off (saved in localStorage, `?viewport=` override), "Sound: off". `web/viewport.js`; `bot.js` just calls `TW2KViewport.update(obs)` (default layout only).
- Decoration only: no fetch, no `/state`, no focus steal, ~30 fps, paused when the tab is hidden or the viewport is off-screen. Reduced motion forces Stills (no running animation, no `<video>`). `mode=cu` shows no viewport (no-op script).
- `tests/test_video_cockpit_v1.py` (6): baseline of 106 visible testids (captured before the change) all still visible; 1440x900 screenshot; modes/persist/override; hull mapping; Skip keeps focus; reduced motion; CU none; timing off 164 ms vs live 162 ms median. Suite 686 passed + 1 xfail; ruff clean.

### 2026-09-26 21:20 PT - Fable - video cockpit V0 (spec lock + fixtures) delivered
- `web/media/manifest.schema.json` (2020-12, v1 + v2), `scripts/media_validate_manifest.py` extended (schema, files, known predicates, trigger->clip refs, EventKinds, public-kind locality, bytes + budget, `--probe`), `web/media/examples/manifest.v2.example.json` (placeholder poster variants).
- `scripts/media_record_fixtures.py` -> `tests/fixtures/media_events/*.json` (11 scenarios, real engine, seed 250925, exactly what `/events` gives the viewer); resolver table in `docs/plans/2026-09-26-video-cockpit-v0-fixtures.md`.
- Finding: a destroyed seat never sees its own `ship_destroyed` (victim moved before emit). Strict xfail in `tests/test_video_cockpit_v0.py`.
- No runtime / UI change (live manifest stays v1). Suite 680 passed + 1 xfail; ruff clean.

### 2026-09-26 21:00 PT - Fable - grokbot-player G6 (four CU pilot fixes, revised scope) delivered
- Status line: `status_fields()` (engine/observation.py) -> harness `status_line` + `day/max_days/turns_left_today/turns_per_day/rank/seats`. The CU top bar has one Status cell and the Turn card starts with it; the CU banner and toast no longer show seq or tick.
- Game over: once the match ends every harness read is 200 with `game_over/winner/win_reason/standings/your_rank`, and every write is 409 `game_over`. `/bot` (both layouts) shows a GAME OVER panel, hides action controls and stops polling.
- Speed: `run_route` macro (`agents/route_macro.py`, `POST /harness/v1/{seat}/macro`). One legal step per held turn from the seat's own observation; it stops on another commander / Ferrengi / hostile fighters, an empty port, low turns, a failed step, hold released, or leaving the route. There is a slot digest (status `digest`, toast, Turn card) and CU REPEAT ROUTE (G) + auto-accept B/X. Report adds clicks, turns/click, wall s/game turn.
- Wake-up ping: `Authorization` from `TW2K_GROKBOT_WEBHOOK_AUTH[_<SEAT>]` or `.tw2k/grokbot_webhook_auth[_<SEAT>].txt` (never logged); `status_line` in brief; final `game_over` ping; the pilot reads `.tw2k/grokbot_webhook_url.txt`.
- `tests/test_cu_pilot_fixes_g6.py` (12). Suite 662 passed; ruff clean; pilot dry run 23/23 on `:8032`. No pilot launched; `:8031` untouched.

### 2026-09-26 19:35 PT - Fable - grokbot-player G5 prep done -> BLOCKED_NEEDS_BEN (pilot not launched)
- `scripts/run_cu_pilot.ps1`: P1 QwenA (LLM, custom), P2 SeatBrain (`seat_brain_v2 --harness`, 60 s), P3 Commander (external CU, 600 s, hold on); seed 250925, 2 days, 60 turns/day, `:8032` (refuses 8031), spectator gate on, tunnel watchdog on, turn_due webhook for P3 only. It needs an explicit `-DryRun` (paused host + checks) or `-Go` (the pilot, after Ben's go).
- New: `--start-paused` (MatchSpec.paused now honoured); per-action log `saves/<run>/external_actions.jsonl` (posts incl. 4xx, engine result, think time, posts per turn, auto-WAIT, held, releases) + `scripts/cu_pilot_report.py`; `POST /harness/v1/{seat}/webhook_test`; `scripts/cu_pilot_check.py` (23 checks).
- Found by the dry run: uvicorn access logs kept `?token=` from claim/spectate URLs. Added a `uvicorn.access` redaction filter. Deleted the affected local logs and rotated the P2/P3 pilot tokens.
- `tests/test_cu_pilot_g5.py` (5). Suite 650 passed; ruff clean. Dry run 23/23 on `:8032`; `:8031` untouched.

### 2026-09-26 19:14 PT - Fable - grokbot-player G4 (reach + turn cadence) delivered
- Tunnel: `run_hosted_grokbot.ps1 -Tunnel [-TunnelProvider] [-TunnelIntervalS]` starts `tunnel_watchdog.ps1` hidden (pid in `.tw2k/tunnel_watchdog.pid`). The watchdog logs a health line every check, re-exposes on any non-200 (503), and re-runs `write_seat_links.py` whenever `.tw2k/public_base_url.txt` changes. The webhook `bot_url` reads the same file, so it follows the tunnel.
- Per-seat timeouts: `AgentSpec.external_timeout_s`, CLI `--external-seat-timeouts P3=600,P4=120`, restart `agents[i].timeout_s`, wrapper `-ExternalTimeoutS` (default 600; `-TimeoutS` alias) + `-SeatTimeouts`. Status `timeout_s`/`deadline_at` are per seat. LLM think caps and the idle auto-WAIT are unchanged.
- `turn_due` webhook adds `seat` + `bot_url` (`{base}/bot?seat=Pn&mode=cu`); still no observation and no token. It retries up to 4 attempts (1/2/4 s backoff) while the turn is open. Every attempt is logged to `saves/<run>/webhook_deliveries.jsonl`, the `tw2k.webhook` logger and status `webhook` (host only; the URL path/query is never logged). No ping on held turns.
- Hold my slot: `POST /harness/v1/{seat}/hold {hold}` or `hold` on the action POST. The runner keeps a holding seat for up to `external_hold_max_actions` (10) extra actions. Releasing during a held turn, or leaving it idle past the deadline, ends the slot without spending a turn or raising AGENT_ERROR. The CU cockpit has a HOLD SLOT / END SLOT button (key H).
- `tests/test_turn_cadence_g4.py` (9) + G2 smoke gained the H key. Suite 645 passed; ruff clean. Live `:8032` demo: 600 s deadline honored (action at 230 s accepted), webhook 503 -> retry 200 logged, hold chained 2 actions + released. `:8031` untouched.

### 2026-09-26 18:33 PT - Fable - grokbot-player G3 (seat login without pasting secrets) delivered
- `GET /bot/claim?seat=P6&token=...` (new `build_seat_claim_router`) verifies the seat token, sets HttpOnly `tw2k_seat_P6` (Path=/harness/, SameSite=Lax, Secure behind https, 14 days) and 303s to `/bot?seat=P6&mode=cu`. 401 bad/missing token, 403 other seat's token or non-loopback without `TW2K_HARNESS_ALLOW_REMOTE`, 503 no match. Open in the spectator gate.
- Harness auth accepts that cookie in place of the Bearer header (Bearer wins); per-seat scope unchanged (P2 cookie on P3 routes = 403). Cookie-authenticated writes must send `X-TW2K-Seat: <seat>` (CSRF guard).
- `tw2k serve` with external seats writes `.tw2k/seat_links/<seat>.txt` (`server/seat_links.py`; base = TW2K_PUBLIC_BASE_URL > .tw2k/public_base_url.txt > bound port). `scripts/write_seat_links.py` refreshes them after a tunnel change (prints masked tokens only). `/bot` connects with the cookie when no token is pasted and only reuses a token stored for the same seat.
- Fixed while testing: `refresh()` skipped entirely when no token was pasted.
- `tests/test_seat_claim_g3.py` (10, incl. Playwright one-click claim -> play); G2 browser helpers moved to `tests/_cu_host.py` + `tests/conftest.py`. Suite 636 passed; ruff clean. Live CLI check on `:8032` with temp tokens; `:8031` untouched.

### 2026-09-26 18:05 PT - Fable - grokbot-player G2 (one-screen turn layout, mode=cu) delivered
- `/bot?seat=Pn&mode=cu` is a fixed 1280x800 grid: top bar (YOUR TURN / WAITING + deadline countdown, credits, net worth, turns, day, seat); left = sector + numbered warp buttons, port tape, known-space map; middle = result toast, big verb buttons with key hints, MORE VERBS panel, forms, keyboard legend; right = ship/cargo, goal + stage hint, last 5 events, plain-text Turn card. The live controls are moved in, so behaviour and data-testids match the default page.
- Keys (CU only, one keymap for legend and handler): 1-9 warp, S scan, B buy, X sell, T trade, P plot course, E end turn (wait), M more verbs, R refresh, Esc close. An unavailable key says why in the toast; the toast keeps the last result or rejection until the next action. The clip HUD docks into spare space instead of covering fields.
- Default `/bot` unchanged (all G2 CSS scoped to `mode-cu`). `tests/test_cockpit_cu_g2.py`: Playwright smoke at 1280x800 (every decision field inside the viewport, no page scroll, keys, SELL form CONFIRM on screen, HUD docked, only own-seat harness requests, default page untouched) + static scope test + Node Turn-card test. Playwright is an optional `e2e` extra; the browser test skips without it.
- Suite 626 passed; ruff clean. Local matches on `:8032`/`:8033` only; live `:8031` untouched.

### 2026-09-26 17:30 PT - Fable - grokbot-player G1 (cockpit parity CP1-CP5) delivered
- `/bot` now renders every key an API LLM seat gets in `format_observation`: planet tape (id, origin, colonists per pool + total, stockpile, production, organics burn, growth, runway), all fog-visible other players (non-corpmates included; occupant chips named), operator directive `(set day D.T)` + last-8 dialogue transcript, `stage_hint` chip from the `format=both` API twin, twin JSON drawer, `/rules` system prompt drawer, and "My thoughts" / "LLM usage" event toggles (off by default, own seat only).
- Pure formatters in new `web/bot-parity.js`; `tests/test_cockpit_parity_g1.py` runs them under Node against engine-built observations. Also repaired double-encoded UTF-8 in `web/bot.js` / `bot.html`, and cleared ruff findings in `planets.py` + 3 tracked scripts.
- Suite 623 passed; ruff clean (src, tests, scripts). Browser-checked on a local `:8032` match; live `:8031` untouched.

- **2026-09-25 PT** — Clip library ML0–ML2: web/media/ + 16 stills + media-player.js on /bot (see docs/plans/2026-09-26-clip-library.md). ML3 video pending.

### 2026-09-25 21:35 PT - Commander - voice architecture: Remote access section
- Added Remote access (host-colocated loop, browser thin clients via tunnel, compressed audio only, tunnel token auth) to `docs/plans/2026-09-26-voice-layer-architecture.md`. Scaffold unchanged.


### 2026-09-25 21:25 PT - Commander - voice layer architecture + scaffold
- Wrote `docs/plans/2026-09-26-voice-layer-architecture.md` (STT→Grok→TTS overlap, providers, <800ms, security, sequence).
- Added isolated `voice/` scaffold (README, server.py, index.html, requirements.txt, .env.example). No keys; no TW2K game/`/bot` edits.
- Mailbox `WAITING_COMMANDER` on `voice-layer-scaffold`. Cockpit-parity plan + S5 still open.

### 2026-09-25 21:20 PT - Commander - cockpit vs API observation parity plan
- Wrote `docs/plans/2026-09-26-cockpit-parity-plan.md` (plan only; no game code).
- Finding: API LLM seats and `/bot` share one fogged `Observation`; gaps are render + `format=both`/`stage_hint`/`/rules` twins (G1-G26), not a richer API pack. Hard ban on god `/state` unchanged.
- Proposed Cursor slices CP0-CP6 (start CP1 empire planet tape after ACK). Mailbox `WAITING_COMMANDER` on `cockpit-parity-plan`; seat-bot S5 docs still open.
- Blockers: none (Ben choose S5 vs CP1 next).

### 2026-09-25 22:45 PT - Fable - seat-bot S6 delivered (`e8c2f18`, PR #1)
- SeatBrain now reads rivals (public NW + witnessed empire events), its own failure events + `recent_failures` (ban exact retry, shelve repeated verb for the day), and `orphaned_planets` (claim only a listed orphan while landed + legal). Observation fix: `recent_failures` groups rejections by verb (was all "unknown").
- Pressure deliberately does not defer the CargoTran or spend the citadel reserve on a 2nd genesis: offline sweeps showed -5k..-140k NW for that.
- `tests/test_seat_bot_s6.py` 16; seat-bot 53; suite 597 passed; ruff clean. Live `:8031` untouched.
- Blockers: none.
### 2026-09-25 16:05 PT - Fable - seat-bot S4 delivered (`7a9813d`, PR #1)
- `src/tw2k/agents/seat_acceptance.py`: seat-only envelope validator (required args, choices, qty caps, plot execute), milestone tracker, recorded-trace replay, synthetic storyboards. `scripts/seat_brain_acceptance.py` CLI (synthetic / record / replay); `seat_brain_v2.py --record` tees live mailbox payloads.
- `tests/test_seat_bot_s4.py` (9): storyboards, validator negatives (missing planet_id/qty etc.), >200-state grid sweep, record->replay with a fresh brain (identical milestones), HTTP harness e2e with request-path fog audit (only P1's own endpoints). Suite 581 passed; ruff clean.
- Next: S5 docs when queued. Blockers: none.
### 2026-09-24 22:40 PT - Fable - seat-bot S3 delivered (`205bb10`, PR #1)
- `src/tw2k/agents/seat_brain.py`: goal-driven `SeatBrain` from the seat's own observation only; `scripts/seat_brain_v2.py` runner (mailbox / `--harness`); `commander_p4_brain.py` is now a thin P4 wrapper (legacy ladder kept locally, uncommitted).
- Offline proof: `tests/test_seat_bot_s3.py` (8) drives the real engine through `build_observation` only; CargoTran -> genesis -> deploy -> land -> citadel -> ferry, 0 rejections, home citadel >=L2 by day 6. Suite 572 passed; ruff clean.
- Bugs found and fixed while building: brain spent itself to 6 cr (reserve vanished while a citadel was building; ferried without need); free infinite `plot_course` loop when the first hop is unaffordable (engine returns ok with 0 hops - reported to Commander); full holds of unsellable goods blocking the ferry (now stocked on the genesis world); second genesis world never visited to build.
- Next: S4 acceptance harness when queued. Blockers: none.
### 2026-09-24 18:40 PT - Fable - seat-bot S1 + S2 ready (PR #1)
- **PR:** https://github.com/EarlTheDuke/TW2002-Human-assist/pull/1 (head `feature/seat-bot-competitive` @ `557b780`, base `review/seat-bot-base`; commits `e04103e` S1, `557b780` S2 also on `feature/grok-bot-harness`).
- **S1:** `Planet.origin` set on every ownership change (genesis / claim on neutral land or orphan `claim_planet` / other on seizure, map start, legacy). `owned_planets[]` adds `origin`, `colonists` per pool, `colonists_total`, `stockpile` (owner-only; same shape as `sector.planets[]`). Prompts: `assign_colonists` examples now carry `planet_id` + `qty`; `deploy_genesis` 3-hop rule; field list + neutral-vs-genesis note.
- **S2:** `src/tw2k/agents/stall.py` - `StallDetector.observe(obs, Intent(kind, target))`; progress = arrival or beating best known-warp distance to target, universal empire signals, intent credit/colonist signals; stalled after `window` idle turns. Not wired into a brain yet.
- **Tests:** `test_seat_bot_s1.py` 9, `test_seat_bot_s2.py` 11; suite 564 passed; ruff clean.
- **Next:** Commander review -> S3 goal-driven seat brain using S1 fields + S2 detector.
- **Blockers:** none.
### 2026-09-22 02:30 PT - Fable - session timebox -> BLOCKED_NEEDS_BEN
- **Session summary (18:03 -> 02:30 PT):** parity-e0 independent plan, then slices **S1-S6 all delivered and ACK'd** on `feature/grok-bot-harness` (tip `c3094ea`, pushed): peek + fogged event stream + spectator gate + xAI gate + webhook fix (S1); Observation-driven `/bot` tapes (S2); `legal_actions()` engine query + verb pad (S3); all 34 verbs precise + four context groups with envelope-driven forms (S4); fog-safe known-space map with click-to-plot + copilot route leak fix (S5); Path-B reference client, mailbox brain protocol, fog-safe `/seats` lobby + chips (S6). Suite 490 -> **544 passed**, ruff clean throughout. Three fog leaks found and closed in code (spectator routes, `build_route_table` true-graph BFS, `/seats` sibling `sector_id`), plus the Federal-port `sells_to_player` mislabel.
- **State left running:** `:8031` = Commander's `playtest-3qwen-commander` match (restarted by Commander ~21:22); `tunnel_watchdog.ps1` (last re-expose 02:20, `/bot` 200); public URL in `.tw2k/public_base_url.txt`; spectator link in `.tw2k/spectator_link.txt`. No tokens/URLs committed.
- **Why blocked:** ~8 h wall timebox per AFK rules; mailbox was `COMMANDER_WORKING` with no Cursor task queued. Loop stopped.
- **To resume:** Ben relaunches the Fable session (same prompt). Open items for Commander to queue: S7 polish/a11y (keyboard map, mobile tabs, `present()` media boundary stub, help drawer from `/rules`), or `COMPLETE`.

### 2026-09-21 21:12 PT â€” Commander â€” S6 ACK -> multi-bot playtest
- S6 accepted (d854820): Path-B client, lobby chips, seats fog fix, webhook; 544 tests.
- S7 deferred. Starting live playtest: heuristic P4/P5 + P3 on /bot.
- mailbox COMMANDER_WORKING phase parity-playtest.

### 2026-09-21 20:47 PT â€” Commander â€” S5 ACK -> S6 queued
- S5 accepted (`dc3291b`): known_sectors coords fog-safe, F5 known_warps BFS, /bot SVG map + plot taps (1-hop + 3-hop), 539 tests.
- Queued parity-s6-multibot-pathb: multi-seat lobby chips, Path-B `grokbot_seat_client.py`, webhook harden, docs/tests. No S7 yet.
- mailbox COMMANDER_QUEUED phase `parity-s6`.
### 2026-09-21 20:25 PT â€” Commander â€” S4 ACK -> S5 queued
- S4 accepted (c62d2e9): all 34 verbs precise; combat/StarDock/planets/comms pads; 535 tests.
- Note: deploy_atomic undispatched (use deploy_mines kind=atomic) â€” leave documented.
- Queued parity-s5-known-map. mailbox COMMANDER_QUEUED.
### 2026-09-21 20:02 PT - Commander - S3 ACK -> S4 queued
- **Ack:** parity-s3-legality-verbs @ tip `138a6fe` accepted (`engine/legality.py` precise core verbs, Observation.legal_actions, /bot verb pad + trade/plot/probe forms, Fed port `side=not_traded` fix, 515 tests).
- **Queued:** Active task `parity-s4-verb-groups` - promote coarse legal_actions to precise + /bot forms by group: combat/presence, StarDock, planets, then comms/corp if engine-legal.
- mailbox -> `COMMANDER_QUEUED` phase `parity-s4`.
### 2026-09-21 19:33 PT - Commander - S2 ACK -> S3 queued
- **Ack:** parity-s2-readonly-tapes @ `d6f13d2` / `85d86c4` accepted (peek-powered Where/Know/Act panels, English last_result, events footer, 44-field data-obs contract; 503 tests; tunnel watchdog).
- **Queued:** Active task `parity-s3-legality-verbs` - `engine/legality.py` + `Observation.legal_actions` + /bot core verb pad (warp/plot_course/trade qty+haggle/scan/probe/wait) with disabled+reason; no recommend-move.
- mailbox -> `COMMANDER_QUEUED` phase `parity-s3`.

### 2026-09-21 18:53 PT â€” Commander â€” S1 ACK â†’ S2 queued
- **Ack:** parity-s1-server-data @ `5065a4f` accepted (peek, fogged `/events`+facts, spectator gate, xAI gate, webhook deadline; 499 tests).
- **Queued:** Active task `parity-s2-readonly-tapes` â€” Where/Know panels on `/bot`, English last_result, events log; peek-powered.
- mailbox -> `COMMANDER_QUEUED` phase `parity-s2`.
### 2026-09-21 18:25 PT â€” Commander â€” merged plans, queued S1
- Fable E0 plan accepted. Canonical: docs/plans/2026-09-21-bot-human-parity.md
- Accepted Fable D1â€“D13 (peek first, event stream, legal_actions later, spectator gate, no recommend-move, quarantine route table, gate xAI script).
- Queued Active task parity-s1-server-data. mailbox COMMANDER_QUEUED.

### 2026-09-21 17:59 PT â€” Commander â€” complete human cockpit direction
- Ben expanded the north star: /bot becomes a complete human interface; competitive multi-Grok-Bot parity remains core.
- Added deferred immersive-media wish list (semantic events -> optional images/video; accessibility and CU fallbacks).
- Refreshed Fable E0 independent-plan task + AFK bootstrap. No implementation queued until plans merge.

### 2026-09-21 17:51 PT â€” Commander â€” E0 parity plans
- Hosted CU loop COMPLETE earlier. New goal: multi-bot + human /bot info and tool parity vs API LLM seats.
- Commander plan: docs/plans/2026-09-21-commander-parity-plan.md
- Queued Fable independent plan: docs/plans/2026-09-21-fable-parity-plan.md (no code). mailbox COMMANDER_QUEUED.

### 2026-09-21 17:32 PT â€” Commander â€” Phase C2 PASS â†’ COMPLETE
- **C2 re-playtest:** 8 successful P3 WARPs on `/bot?seat=P3` (lhr.life). Phase D checks all PASS (WAITING names seat, data-testid clicks 0 misses, YOUR TURN without reload, no idle-sibling stall).
- Artifacts: `docs/playtests/C2_SESSION_LOG.md`, `docs/playtests/screenshots-c2/{01-connected,02-your-turn,08-waiting-seat}.png`.
- **Decision:** No D2 Cursor pass (no new UI friction beyond Qwen wait). Optional polish deferred.
- mailbox â†’ `COMPLETE`. Pausing TW2K AFK handoff watch. Cursor should exit cleanly.

### 2026-09-21 17:24 PT â€” Commander â€” Phase D ACK â†’ Phase C2 re-playtest
- **Ack:** Phase D @ `2e4a5c2`/`e5184a9`/`db8f0be` accepted (idle auto-WAIT, `current_turn` banner, stable `data-testid`, long-poll YOUR TURN; 490 tests).
- Tunnel 503 â†’ re-ran `expose_hosted_bot.ps1`; new base in `.tw2k/public_base_url.txt`.
- Match restarted (3 seats, 120 turns/day, P3 token pinned); P3 `turns_remaining=120`.
- mailbox â†’ `COMMANDER_WORKING` phase `hosted-bot-cu-c2`. Cursor idle.
- **Doing:** computer-use re-playtest on `/bot?seat=P3` (â‰¥8 turns validating D fixes).

### 2026-09-21 15:54 PT â€” Commander â€” requeue Phase B assist for Cursor paste
- Ben asked for updated Cursor paste. Phase A still DONE; prior BLOCKED was missing Tailscale/cloudflared.
- New Active task: `hosted-bot-phase-b-assist` â€” expose_hosted_bot.ps1 + write `.tw2k/public_base_url.txt` + HOSTING update.
- mailbox -> COMMANDER_QUEUED. Bootstrap refreshed in COMMANDER_TO_FABLE_BOOTSTRAP.md.


### 2026-09-21 11:05 PT Ã¢â‚¬â€ Commander Ã¢â‚¬â€ Phase B BLOCKED_NEEDS_BEN
- Phase A already done; VENGEANCE tw2k listening 0.0.0.0:8031; tokens present.
- Cannot expose URL: Tailscale + cloudflared missing on VENGEANCE; Commander box cannot hit LAN.
- mailbox -> BLOCKED_NEEDS_BEN (task hosted-bot-phase-b-url). Ben: Tailscale Serve / cloudflared quick tunnel / other public URL -> then Phase C CU on /bot?seat=P3.

### 2026-09-21 (Commander) Ã¢â‚¬â€ Phase A done on VENGEANCE (no Cursor paste)
- Ben AFK: cannot inject local Cursor Agent; Commander executed Phase A via Shell on VENGEANCE
- Hardened `web/bot.*` for computer use (pulse banner, action gating, classified errors, strip ?token=)
- Added `docs/HOSTING_GROKBOT.md` + README `/bot` blurb
- machine_state: WAITING_COMMANDER (need reachable host URL for Phase B/C)

### 2026-09-21 (Commander) ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â reopen for hosted computer-use
- Queued Phase A: polish `/bot`, `HOSTING_GROKBOT.md`, smoke against `run_hosted_grokbot.ps1`
- Plan written: `docs/plans/2026-09-21-hosted-bot-computer-use.md`
- machine_state: COMMANDER_QUEUED (task `hosted-bot-ui-hosting`)

---

## Prior handoff body (Phase 0ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“2 external harness)

## 1. Product goal

Ship TW2K-AI with existing LLM API players (including **custom/Qwen**) **plus up to four Grok Bot** seats via token-authenticated **external harness** for game testing.

Success:
1. Mixed match: e.g. 2ÃƒÆ’Ã¢â‚¬â€ Qwen (`qwen3.8:latest`) + 4ÃƒÆ’Ã¢â‚¬â€ `external` Grok Bot seats
2. External seats: pull Observation ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ POST Action JSON (localhost + bearer token)
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

### Add ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â `ExternalAgent` + HTTP harness
- Kind: `external`
- Per seat: player_id, name, bearer token (gitignored token file)
- Block with timeout (`TW2K_EXTERNAL_TIMEOUT_S`, default ~120) ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ WAIT + AGENT_ERROR on timeout
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

### Phase 0 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Plan (DONE)
- Plan only ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ `docs/plans/2026-09-20-external-harness.md`
- Then WAITING_COMMANDER (no Phase 1 code until Commander queues it)

### Phase 1 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â ExternalAgent + REST + tests + smoke script
### Phase 2 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â `scripts/run_2qwen_4external.ps1` + tokens file + Grok Bot player guide
### Phase 3 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Optional WS, spectator labels, cost N/A for external

---

## 4. Acceptance criteria

- [x] 2ÃƒÆ’Ã¢â‚¬â€ custom Qwen + 4ÃƒÆ’Ã¢â‚¬â€ external starts
- [x] 401 on bad token; timeout ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ WAIT; valid Action applies
- [x] Smoke script green; no secrets in git
- [x] AFK mailbox ends at COMPLETE

---

## 5. Orchestrator notes (Commander)

_2026-09-21 20:47 PT - Commander: S5 accepted (`dc3291b`). Queued S6 multi-bot ops + Path-B client. mailbox COMMANDER_QUEUED._

_2026-09-21 19:33 PT - Commander: S2 accepted (`d6f13d2`). Queued S3 legality + core verbs. mailbox COMMANDER_QUEUED._

_2026-09-21 19:33 PT â€” Commander: S2 accepted (`d6f13d2`). Queued S3 legality + core verbs. mailbox COMMANDER_QUEUED._

_2026-09-21 18:53 PT â€” Commander: S1 accepted (`5065a4f`). Queued S2 read-only cockpit tapes. mailbox COMMANDER_QUEUED._

_2026-09-21 17:32 PT â€” Commander: C2 re-playtest PASS (8 turns); hosted /bot CU loop COMPLETE. AFK watch paused._


_2026-09-21 17:24 PT â€” Commander: Phase D accepted; C2 re-playtest in progress (COMMANDER_WORKING). Cursor idle until D2 or COMPLETE._


_2026-09-20 PT ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â AFK protocol enabled. Mailbox: docs/COMMANDER_NEXT.md. Commander watch routine polls ~10 min. Cursor: long session with 2-min sleep polls. First task = Phase 0 plan._

_2026-09-20 21:30 PT ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Commander: Phase 0 plan accepted (sane: ExternalAgent=HumanAgent+turn_seq+long-poll+tokens; REST /harness/v1; 1aÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“1f phasing). Queued Phase 1 in COMMANDER_NEXT.md ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ machine_state COMMANDER_QUEUED, phase 1._


_2026-09-20 21:58 PT ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Commander: Phase 1 accepted (ExternalAgent+REST+tests+smoke; tip `e700ea6`; 486 tests; smoke PASS). Queued Phase 2 in COMMANDER_NEXT.md ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ machine_state COMMANDER_QUEUED, phase 2. Scope: `run_2qwen_4external.ps1` + `gen_external_tokens.py` + `docs/GROK_BOT_PLAYER_GUIDE.md` + ARCHITECTURE/ROADMAP touch._

_2026-09-20 22:16 PT ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Commander: Phase 2 accepted (`run_2qwen_4external.ps1` + `gen_external_tokens.py` + `GROK_BOT_PLAYER_GUIDE.md`; tip `e1fa90b`; live mixed match + P3 turn ok). Handoff Ãƒâ€šÃ‚Â§4 acceptance met. Skipping optional Phase 3 polish. Set machine_state COMPLETE; pausing TW2K AFK handoff watch._

---



_2026-09-21 11:05 PT Ã¢â‚¬â€ Commander: Phase A complete; Phase B blocked on reachable host URL (no Tailscale/cloudflared on VENGEANCE). Set BLOCKED_NEEDS_BEN; ping Ben for tunnel/URL. Phase C waits._

## 6. Changelog

### 2026-09-20 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Commander
- Bootstrap + AFK mailbox/loop. Architecture: ExternalAgent harness for 4 Grok Bots; keep Qwen custom seats.

### Cursor ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â (append below)

<!-- Fable: append dated Done / Next / Blockers -->

### 2026-09-20 21:22 PT ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Fable ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Phase 0 (plan) DONE
- **Done:** `docs/plans/2026-09-20-external-harness.md` ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â verified ground truth (HumanAgent queue pattern, runner deadline branch, AgentSpec/override flow, PlayerKind, meta.json, MCP token pattern), design (`ExternalAgent` = HumanAgent + `turn_seq` + long-poll event + per-seat token + `last_result`), file-level plan (new: `agents/external.py`, `server/harness.py`, `server/harness_tokens.py`, tests, smoke, example client; edited: `models.py` enum only, `runner.py`, `app.py`, `cli.py`, `.gitignore`, `.env.example`, CI), REST table (`/harness/v1/{seats,rules,{pid}/status,{pid}/observation?wait_s,{pid}/action}` + error codes), 2ÃƒÆ’Ã¢â‚¬â€Qwen+4ÃƒÆ’Ã¢â‚¬â€external CLI and restart-body configs, 16 tests, phasing 1aÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“1f/2/3, risks.
- **No harness code written** (Phase 0 lock respected).
- **Env facts for Commander:** TinyBox `/api` on the current key serves `qwen3.8:latest` (200); `kimi-k2.5`/`k2.6` ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ 400 Model not found. Windows needs `PYTHONUTF8=1` or the rich banner crashes.
- **Next (on COMMANDER_QUEUED):** Phase 1a ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â cut `feature/grok-bot-harness`, `ExternalAgent` + `PlayerKind.EXTERNAL` + unit tests.
- **Blockers:** none. (FYI only, not blocking: `docs/MIXED_LLM_ACCESS.md` is untracked and embeds a stale Open WebUI key ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â should be redacted before it is ever committed.)
- **Verify:** `Get-Content docs/plans/2026-09-20-external-harness.md | Select-Object -First 20`

### 2026-09-20 21:30 PT ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Commander ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Phase 0 ACK ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ Phase 1 queued
- **Ack:** Plan at `docs/plans/2026-09-20-external-harness.md` accepted; no code changes from Commander.
- **Queued:** Phase 1 (1aÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“1f ExternalAgent + REST + tests + smoke) via `COMMANDER_QUEUED`.
- **Next after Cursor finishes Phase 1:** Phase 2 script + tokens helper + Grok Bot player guide.

### 2026-09-20 21:52 PT ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Fable ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Phase 1 (ExternalAgent + REST + tests + smoke) DONE
- **Branch:** `feature/grok-bot-harness` pushed to origin (8 commits on top of `cursor-composer-provider` @ `c43510e`; tip `e700ea6`).
- **Done (per plan Ãƒâ€šÃ‚Â§2):**
  - 1a `src/tw2k/agents/external.py` ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â `ExternalAgent` (kind `external`, 1-slot queue, `turn_seq`, `turn_due` long-poll event, `last_result`, token held in-memory only); `PlayerKind.EXTERNAL`; exported from `tw2k.agents`.
  - 1b `src/tw2k/server/harness_tokens.py` ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â explicit > env `TW2K_EXTERNAL_TOKEN_<PID>` > tokens file > generated+persisted (`.tw2k/external_tokens.json`, 0600 best-effort); `mask()` ASCII-only; `verify()` via `hmac.compare_digest`. `.gitignore` adds `.tw2k/` + `*external_tokens*.json`; `.env.example` documents the knobs.
  - 1c `server/runner.py` ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â `AgentSpec.external_token` (excluded from meta.json), `MatchSpec.external_timeout_s` (default 120), `_build_agents` external branch, deadline branch generalized: external timeout ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ WAIT + `AGENT_ERROR{external_timeout:true}`; `record_result` hook after `apply_action`; timeout WAITs count toward `last_action_was_timeout`.
  - 1d `server/harness.py` ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â `/harness/v1/{seats,rules,{pid}/status,{pid}/observation?wait_s&format,{pid}/action}`; 401/403/404/409(`not_external`|`stale_turn`|`not_awaiting`)/422/429/503 per plan; loopback-only unless `TW2K_HARNESS_ALLOW_REMOTE=1`; `actor_kind` stripped from bot submissions. Mounted in `create_app`.
  - 1e `cli.py` `--external P3,P4`, `--external-timeout-s`, `--external-tokens-file`; `_build_default_spec` resolves seat tokens (only when external seats exist, so LLM-only matches never create `.tw2k/`); `/control/restart` accepts `agents[].kind="external"`, `agents[].token`, `external_timeout_s`; banner prints `EXTERNAL token=abcd...wxyz` (masked) + harness URL.
  - 1f `scripts/smoke_external_harness.py` (offline, exit 0, added to CI offline-smoke step) + `scripts/external_client_example.py` (reference long-poll bot; drove a live `tw2k serve --external P2` on :8010 for 4 turns, all `ok`).
  - Lint tidy commit: cleared 18 pre-existing ruff 0.15 findings in untouched files so CI's ruff job is green.
- **Tests:** `tests/test_external_harness_phase1.py` ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 15 tests covering plan items 1ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“16 (11/12/13 merged into one HTTP flow). Full suite **486 passed** (was 471). `ruff check src tests scripts` clean on tracked files.
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
- **Housekeeping note (my mistake, not blocking):** while cleaning up after the live check I ran `Remove-Item saves\*seed42*`, which also removed today's earlier gitignored seed-42 match saves (the 3ÃƒÆ’Ã¢â‚¬â€ and 4ÃƒÆ’Ã¢â‚¬â€ Qwen runs Ben watched). Nothing tracked was affected; no replay of those two matches is possible now.
- **Next (on COMMANDER_QUEUED):** Phase 2 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â `scripts/run_2qwen_4external.ps1`, `scripts/gen_external_tokens.py`, `docs/GROK_BOT_PLAYER_GUIDE.md`, ARCHITECTURE/ROADMAP touch.
- **Blockers:** none.

### 2026-09-20 21:58 PT ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Commander ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Phase 1 ACK ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ Phase 2 queued
- **Ack:** Phase 1 on `feature/grok-bot-harness` @ `e700ea6` accepted (486 tests, ruff clean, smoke PASS, live REST check).
- **Queued:** Phase 2 via `COMMANDER_QUEUED` ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â `scripts/run_2qwen_4external.ps1`, `scripts/gen_external_tokens.py`, `docs/GROK_BOT_PLAYER_GUIDE.md`, ARCHITECTURE/ROADMAP touch.
- **Next after Cursor finishes Phase 2:** Phase 3 polish or COMPLETE if acceptance criteria met.

### 2026-09-20 22:06 PT ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Fable ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Phase 2 (mixed-match script + tokens + guide) DONE
- **Branch:** `feature/grok-bot-harness` @ `e1fa90b` (pushed).
- **Done:**
  - `scripts/gen_external_tokens.py` ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â mints/keeps tokens for `--seats` (default P3ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“P6) in the gitignored tokens file; prints masked; `--rotate`, `--show` (explicit opt-in to print env lines).
  - `scripts/run_2qwen_4external.ps1` ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â sets `PYTHONUTF8`, pre-generates tokens, prints per-seat env + curl one-liners (masked), then `tw2k serve --provider custom --model qwen3.8:latest --num-agents 6 --external P3,P4,P5,P6 --external-timeout-s 120 --starting-credits 1000000`. Params: `-Port -StartingCredits -MaxDays -TimeoutS -Seed -Model -Names`.
  - `docs/GROK_BOT_PLAYER_GUIDE.md` ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â setup, endpoint table, status-code table, turn protocol, observation field map, 30-verb arg cheat sheet (arg names checked against `engine/runner.py` handlers), minimal bot example, good-turn checklist, troubleshooting.
  - `docs/ARCHITECTURE.md` (agent list, server routes, ExternalAgent section) and `docs/ROADMAP.md` (Phase X block with acceptance criteria).
- **Live acceptance check:** ran the script on :8020 ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ banner shows P1/P2 `custom qwen3.8:latest`, P3ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“P6 `EXTERNAL token=xxxx...xxxx`; `/state` confirms kinds; `/harness/v1/seats` lists 4 seats; `external_client_example.py` as P3 completed `warp ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ ok` inside the mixed match (Qwen seats took their turns first). Server stopped afterward; temp tokens file removed. `.tw2k/` confirmed gitignored (`git check-ignore`).
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
- **Handoff Ãƒâ€šÃ‚Â§4 acceptance status:** 2ÃƒÆ’Ã¢â‚¬â€Qwen+4ÃƒÆ’Ã¢â‚¬â€external starts ÃƒÂ¢Ã…â€œÃ¢â‚¬Â¦ Ãƒâ€šÃ‚Â· 401 bad token / timeoutÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢WAIT / valid Action applies ÃƒÂ¢Ã…â€œÃ¢â‚¬Â¦ (tests 8, 10, 12) Ãƒâ€šÃ‚Â· smoke green, no secrets in git ÃƒÂ¢Ã…â€œÃ¢â‚¬Â¦ Ãƒâ€šÃ‚Â· mailbox COMPLETE ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Commander's call.
- **Next (on COMMANDER_QUEUED):** Phase 3 optional ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â `WS /harness/v1/{pid}/ws` turn_due push, spectator `EXTERNAL` badge, cost `n/a` column, MCP `tw2k_list_external_seats`. Or COMPLETE.
- **Blockers:** none.

### 2026-09-20 22:16 PT ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Commander ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Phase 2 ACK ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ COMPLETE
- **Ack:** Phase 2 on `feature/grok-bot-harness` @ `e1fa90b` accepted (mixed 6-seat script, tokens helper, player guide, live P3 warp ok, smoke/tests green, no secrets in git).
- **Decision:** Optional Phase 3 (WS / spectator badge / cost n/a / MCP seats) deferred. Core acceptance criteria met.
- **mailbox:** `machine_state` ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ `COMPLETE`. AFK watch paused. Cursor should exit the loop cleanly.
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
  - [x] **P2** `/harness/v1/{pid}/status` and `/observation` now carry `current_turn` = `{player_id, name, kind, started_at, deadline_at, attended, awaiting_input}` for whoever the scheduler is on (external or LLM, LLM deadline from `llm_think_cap_s`). `/bot` WAITING banner reads e.g. `WAITING day=2 tick=31 / P3 GrokPilot2 (external) - no bot attached Â· 7s`, countdown ticks locally each second (clock skew from `server_time`); a new "Scheduler" line mirrors it.
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
- **Artifact:** `docs/plans/2026-09-21-fable-parity-plan.md` (planning only; no game code touched). Sections A-H as requested, plus Â§0 code findings and a slice table S1-S7 with acceptance tests / done-when.
- **Code findings that change the plan (details Â§0):** F1 harness returns `observation: null` unless awaiting -> cockpit needs a **peek**; F2 `_event_to_dict` drops payloads and `recent_events` is capped -> need a **fogged event stream + per-kind `facts` whitelist** (this is also the media boundary); F3 legality lives only inside runner handlers -> add **`legal_actions()` engine query** onto the Observation (LLM parity, honest button gating); F5 **fog leak** in `copilot/dashboards.build_route_table` (true-graph BFS + live prices); F6 **fog leak** via unauthenticated spectator routes on a hosted URL; F7 `scripts/play_grok_external_seats.py` drives P4/P5 with **xAI** (contradicts mission; I committed it in the Phase A sweep - flagging for removal/gating); F8 webhook `deadline_at` ignores the spec; F9 `Sector.x/y` exist -> known-sector coords are fog-safe for a real map; F4 `/play` already has 10 verb forms + keyboard + economy panel to port instead of rebuild.
- **Explicit disagreements with Commander's plan (Â§H1, D1-D13):** peek before E1; event endpoint in slice 1 not E3; legality must come from the engine not the UI; draw a real known-space map with server coords, not a list; human notes go to `scratchpad_update`/`goal_*` not localStorage; **no** server-side "recommend move" heuristic (asymmetric assist / second brain); spectator gate; quarantine `build_route_table`; remove xAI script; reuse `/play` forms and later fold `HumanAgent` into `ExternalAgent(kind=human)`; webhook fixes; server-data slice first.
- **Proposed merged outline (Â§H2)** maps Commander E1-E5 onto S2-S7 with **S1 (server: peek, event stream, spectator token, F7/F8 fixes) as the first queued slice**.
- **Verified while planning:** `EventKind`=58, `Observation.model_fields`=44 (`/bot` renders 8), `ActionKind`=34. No secrets/URLs in the plan (grep clean).
- **Housekeeping:** the localhost.run tunnel from Phase D is no longer running (only cloudflared is); :8031 match is still up. Re-run `expose_hosted_bot.ps1 -Detach` before the next CU session.
- **Next:** idle until Commander merges and queues S1 (or an amended first slice).
- **Blockers:** none.

### 2026-09-21 19:05 PT - Fable - parity-s1-server-data DONE (server data + fog fixes)
- **Commits on `feature/grok-bot-harness`:** `c16b2b1` EventView + facts whitelist Â· `e061986` harness peek + `/events` Â· `d344687` spectator gate Â· `ac54a30` webhook deadline/base_url + xAI gate Â· `5acec2b` tests Â· `5065a4f` hosted script token + docs. Pushed.
- **1. Peek:** `GET /harness/v1/{pid}/observation?peek=1` returns `build_observation(u, pid)` for your own seat when not awaiting (`peek: true`, `awaiting_input` unchanged, nothing can bind to it; 0.5 s per-seat cache). On your turn it returns the bound observation as before (`peek: false`).
- **2. Fogged event stream:** `GET /harness/v1/{pid}/events?since=<seq>&limit<=500` -> `{events, next_since, latest_seq, has_more}`, filtered by `_event_visible_to`, rendered by new `engine/observation.py::event_view` = `summary` (always) + `facts` = per-kind whitelist `EVENT_FACTS` (51 kinds listed; 7 meta/private kinds deliberately summary-only). `Observation.recent_events` now carries the same `facts` (LLM seats get parity; `actor_kind` omitted there to stay lean). This table is the presentation/media boundary - future asset keys bind to `kind` + `facts`.
- **3. Spectator gate:** `server/spectator_gate.py` ASGI middleware (covers the `/ws` handshake). When `TW2K_SPECTATOR_TOKEN` is set: `/`, `/state`, `/events`, `/history`, `/highlights`, `/ws`, `/play`, `/control/*`, `/api/*` -> 401 unless Bearer header / `?token=` / cookie. `GET /spectate?token=...` sets the cookie and 303s to `/` (one-click for Ben). `/bot`, `/harness/*`, `/static/*` untouched. Unset env = legacy open behaviour. `run_hosted_grokbot.ps1` now generates/keeps `.tw2k/spectator_token.txt` and writes Ben's link to `.tw2k/spectator_link.txt` (both gitignored); `-NoSpectatorGate` for LAN.
- **4. xAI script:** `scripts/play_grok_external_seats.py` exits 2 with a loud banner unless `--allow-xai-fallback` (or `--all-commander`).
- **5. Webhook:** `ExternalAgent.turn_due_payload()` - `deadline_at` = runner-effective deadline (`turn_deadline_at`, set by `_await_external`, includes idle rule and mid-window extension), `base_url` (`TW2K_PUBLIC_BASE_URL` > `TW2K_HARNESS_BASE_URL` > loopback), `observation_url`/`action_url`, a 5-field `brief`; full Observation only with `TW2K_GROKBOT_WEBHOOK_FULL_OBS=1`.
- **Tests:** `tests/test_parity_s1.py` (9): facts whitelist + no private keys, recent_events facts, peek + fogged stream property check (every streamed event passes `_event_visible_to` for that seat; facts âŠ† whitelist; cursor paging), gate path table, gate 401/header/query/cookie/303, gate disabled when unset, xAI script exit 2, webhook payload, runner-set deadline (idle then mid-window extension). Full suite **499 passed**; ruff clean; `smoke_external_harness.py` PASS.
- **Live:** `:8031` restarted on S1 code (3 seats, gate ON): `/state` 401 without token / 200 with; `/bot` 200; peek `true` for P3 between turns; `/events` shows P3 only `game_start` so far (fog holding). localhost.run re-exposed; new base in `.tw2k/public_base_url.txt`; `/bot` 200 through it. Spectator link for Ben: `.tw2k/spectator_link.txt` (loopback base - swap in the tunnel base if opening remotely).
- **Docs:** HOSTING_GROKBOT.md (gate + Ben's link, peek/events), GROK_BOT_PLAYER_GUIDE.md (peek, events, webhook payload), `.env.example`.
- **Not done / deferred (by plan):** `legal_actions()` (S3), `known_sectors` coords (S5), `build_route_table` quarantine is a no-op today (only `/play` calls it, which is now behind the gate) - fix it properly in S5.
- **Next:** wait for Commander ACK; then S2 read-only tapes on `/bot` (peek-powered).
- **Blockers:** none.

### 2026-09-21 19:22 PT - Fable - parity-s2-readonly-tapes DONE
- **Commits:** `d6f13d2` S2 UI + tests, `85d86c4` tunnel watchdog. Pushed.
- **`/bot` is now a three-column Observation renderer** (`web/bot.html/js/css`): scoreboard strip (day/turns/credits/net worth/rank/alignment/lives/corp/landed) Â· **Where** = Here (sector, FedSpace badge, warps, occupants, fighters/mines, planets, Ferrengi), Port tape (code/name/class + per-commodity **BUYS/SELLS Â· price Â· stock cur/max Â· you hold**), Adjacent strip (port code, fighters, planets, occupants, known/unexplored), Known space (adjacency count + compact list) Â· **Act** = scheduler line, stable warp chips, SCAN/WAIT/sell/buy, **English last result** built from the engine's own event summaries for the action's `event_seqs` (raw JSON in a drawer), Advisor (recent_failures, action_hint drawer), Notes (goals/scratchpad read-only), raw Observation drawer Â· **Know** = Ship loadout + cargo table with cost basis, Known ports table (age, per-commodity B/S price; stale rows dimmed), Trading (trade_summary + trade_log P&L), Commanders (rivals with fogged last-seen; corpmates), Planets (owned/orphaned), Comms (inbox, alliances, corp), Intel (limpets, probe log) Â· **Footer** = fogged event log from `/events` with kind-group filters, facts inline, "new since your last turn" highlight.
- **Peek-powered:** Connect and every long-poll return use `observation?peek=1`, so panels fill immediately while WAITING and refresh each cycle; the scheduler line says "(panels show a live peek of your seat)". Turn logic from Phase D unchanged (long-poll flip, countdown, stable warp DOM).
- **Coverage contract:** every element carries `data-obs="<Observation key>"`; `tests/test_parity_s2.py` asserts all **44** `Observation.model_fields` have a home and no `data-obs` names a non-field, plus data-testid hooks for every panel/control/filter, "no rule constants in JS", peek + `/events` usage, and a live ASGI check that the one call Connect makes returns every field the panels read. 4 tests; full suite **503 passed**; ruff clean.
- **Browser check (IDE browser, local 3-seat match):** Connect -> all panels populated from the peek before my turn; WARP 68 -> `turn 3: WARP to 68 â€” ok: Commander warped 2 â†’ 68`; adjacent strip showed port codes + known/unexplored for the new sector; events footer listed 7 fogged events with facts. Done-when #2 answerable from the port tape (SELLS fuel 18 / org 25 / equip 36 at the FED port) + known-ports table (per-commodity B/S price per remembered sector).
- **Also:** idle auto-WAIT thought text now quotes the effective idle window, not the nominal timeout (was "after 90s" for an 8 s wait).
- **Ops:** `scripts/tunnel_watchdog.ps1` (running in this session, 60 s) re-runs `expose_hosted_bot.ps1 -Detach` when the localhost.run session dies or `/bot` stops answering - it died twice today after ~30-60 min idle. The URL changes on each re-expose; **consumers must re-read `.tw2k/public_base_url.txt`** rather than cache it. Log: `.tw2k/tunnel_watchdog.log`. `:8031` still on S1 server code (S2 is static files, live already); the idle-text fix needs a restart - cosmetic, deferred so the running match is not disturbed.
- **Known limits (by plan):** trade is still the two fixed shapes; known-ports rows seeded at spawn show `?` prices (the engine's start-of-match snapshot has no price/side - honest); full map is S5; verb gating is S3.
- **Next:** Commander ACK -> S3 `legal_actions()` + trade/plot/probe forms.
- **Blockers:** none.

### 2026-09-21 19:58 PT - Fable - parity-s3-legality-verbs DONE
- **Commits:** `12a2e34` engine legality + Observation/LLM form Â· `e087b64` `/bot` verb pad + forms Â· `138a6fe` tests/guide/watchdog fix. Pushed; tip `138a6fe`.
- **Engine:** `engine/legality.py::legal_actions(universe, pid) -> list[LegalAction{kind, legal, reason, turn_cost, detail, params}]`. Pure query, same constants as handlers, one entry per `ActionKind` (34) in engine order. `detail="precise"` for warp, scan, wait, trade, plot_course, probe, hail, broadcast (every handler precondition mirrored - including two I had to *remove* because the engine does not enforce them: warp/plot_course are NOT gated on `planet_landed`, and `wait` DOES fail at 0 turns). `detail="coarse"` for the other 26 (context precondition only; S4 promotes them). `params` = argument envelope: warp `target.choices`, trade `commodity.buy_choices/sell_choices`, `qty.max_by[c][side]` (engine cap at **list** price since a rejected haggle settles at list), `unit_price.listed_by`, probe `target.min/max`, plot `target.suggested` (known sectors), hail `target.choices`.
- **Observation:** `Observation.legal_actions` (44 -> 45 fields; S2 coverage test forced a `data-obs` home = the verb pad). `format_observation` ships `legal_actions: {legal:[kinds], blocked:{kind: reason}}` so LLM seats reason from the same facts.
- **Observation fix found by the UI:** `_sector_detail` labelled Federal (class 0) port stock `sells_to_player` by fallback although `can_trade` refuses both sides there -> now `side="not_traded"`, `price=null`. The S2 port tape and every LLM seat had been shown a market that did not exist.
- **`/bot`:** verb pad (SCAN / WAIT / TRADE / PLOT COURSE / PROBE + warp chips + quick SELL/BUY) gated **only** by `legal_actions`: disabled buttons carry `data-reason` (engine text) and a reasons list; nothing hidden. Forms: **trade** (side radios enabled per envelope, commodity from `buy/sell_choices`, qty capped by `max_by` with MAX, optional haggle price with list placeholder, live estimate incl. cost-basis P&L and "rejected asks settle at list" note), **plot_course** (target + known-sector picker + execute; preview hops via BFS over the seat's own `known_warps` - presentation only), **probe**, **scan** (tier), **wait**. All 26 coarse verbs shown disabled with reasons in a "More verbs" drawer (forms in S4). Open form is stable across the 1.5 s polls (rebuilt only when the verb's envelope changes) - a second DOM-churn bug of the Phase-D class, caught by the CU browser. `.badge[hidden]` CSS fix (FedSpace badge was stuck on).
- **Tests:** `tests/test_parity_s3.py` (12): matrix over 8 fixture states (StarDock fresh, trading port with cargo, trading port broke+empty, out of turns, one turn left, has probes, landed, dead) x 8 precise verbs asserting `legal == apply_action(...).ok` with actions built from the advertised envelope; purity/determinism/order; trade envelope caps vs list price; Observation + LLM message carry legality; UI contract (gated by `legal_actions`, `data-reason`, no rule constants, forms for all S3 verbs). Full suite **515 passed**; ruff clean.
- **Browser proof (IDE browser, local 2-seat match, no precondition rejects):** TRADE correctly disabled at the FED port ("nothing you can buy or sell here") -> WARP 68 -> WARP 50 (SBB) -> BUY Fuel form prefilled from envelope (qty 20 = holds cap, list 16) with haggle 14 -> `BUY 20 fuel_ore @ 14 â€” ok â€¦ [haggle won at 14cr (list 16)]` -> TRADE re-disabled (holds full) -> WARP 68 -> SCAN -> WARP 70 -> SCAN (known-ports table now shows sector 61 BBS `B 19`) -> WARP 61 -> SELL Fuel form, ask 21 -> `SELL 20 fuel_ore @ 21 â€” ok â€¦ [haggle countered; settled at list 19cr] (+100cr profit)`; Trading panel 2 trades, +100 cr, 35.7 % margin. Every lit button POSTed an accepted action.
- **Ops:** `tunnel_watchdog.ps1` fixed (the re-expose call hung on the child's pipe; now a wrapper process with a 150 s timeout) - it has since logged a clean `tunnel unhealthy (503) -> re-exposed OK` cycle unattended. `:8031` restarted on S3 code (the new `/bot` requires `legal_actions` in the Observation; on the S1 server every verb would read "no legality data"). Re-read `.tw2k/public_base_url.txt`.
- **Not done (by plan):** S4 verb groups; `known_sectors` map (S5).
- **Next:** Commander ACK -> S4.
- **Blockers:** none.

### 2026-09-21 20:23 PT - Fable - parity-s4-verb-groups DONE
- **Commits:** `eca1c24` engine (all 34 precise) Â· `7b3b206` `/bot` groups + forms Â· `c62d2e9` tests/guide. Pushed; tip `c62d2e9`.
- **Engine:** `legal_actions()` now `detail="precise"` for every `ActionKind` (0 coarse). Each mirrors its handler's preconditions in order, including engine quirks I deliberately kept: `corp_join` does not check you are already in a corp; `break_alliance` accepts an inactive (still-proposed) alliance; `hail` only needs a known player id (dead or alive); `build_citadel` never fails on turns (engine waives the cost); `query_limpets` is always legal (0 beacons = empty report); **`deploy_atomic` has no handler in `_DISPATCH`** (engine says "unsupported action") - reported never-legal with "use deploy_mines kind=atomic". Envelopes carry the numbers the forms need: `buy_ship.ship_class.{choices, net_cost_by, trade_in, blocked_by}`, `buy_equip.item.{choices, unit_price_by}` + `qty.max_by` (min of affordability and capacity: fighter/shield headroom, holds to 150, colonists into free holds), `build_citadel.next`, `deploy_genesis.{hops_from_stardock, min_hops}`, `land_planet.planet_id.contested`, planet cargo `commodity.choices` from stockpile/pools/cargo with `qty.max_by`, `assign_colonists.{from, to, qty.max_by, ship_free}`, alliance `alliance_id.choices`, corp `amount.max`. FedSpace `attack`/`photon_missile` are flagged illegal with the alignment-penalty warning **before** the engine docks -200/-100.
- **`/bot`:** four context groups under the core pad - **Combat & presence** (attack, photon_missile, deploy_fighters, deploy_mines, deploy_atomic), **StarDock** (buy_ship, buy_equip, corp_create), **Planets** (land, liftoff, claim, load/dump cargo, assign_colonists, build_citadel, deploy_genesis), **Comms, corp & alliances** (hail, broadcast, propose/accept/break alliance, corp invite/join/leave/deposit/withdraw/memo, query_limpets). Each `<details>` shows "N legal" and auto-opens when any verb is legal (user toggles are respected); every button visible, `disabled` + `data-reason` + the reason printed under the label. Forms are **envelope-driven** (`FORM_SPECS`: choice/int/text fields bound to `params[name].choices|min|max|max_by`) with per-verb preview lines that only echo engine numbers (net cost + trade-in, unit price Ã— qty, citadel tier, hops from StarDock, contested-planet warning). Buttons built once, state updated in place (stable DOM).
- **Tests:** `tests/test_parity_s4.py` (20): **19 fixtures Ã— 34 verbs** (`legal == apply_action(...).ok` with envelope-built actions; plausible action when illegal so the engine must also reject) - fixtures: deep-space hostile pair, FedSpace blocked, allied pair, StarDock rich/broke, FedSpace-not-StarDock, unowned planet here, landed own stocked planet, citadel under construction, landed rival planet, landed orphan, genesis deep / one hop, corp CEO / invited P2 view / member P2 view, alliance proposed to me, out of turns. Every promoted verb is legal=True in at least one fixture (verified). Plus FedSpace-combat flag test and UI contract (groups + forms for all 26, no rule constants). Full suite **535 passed**; ruff clean.
- **Browser proof (local 2-seat, zero precondition rejects):** Comms - `PROPOSE_ALLIANCE target=P1 terms=â€¦ â€” ok: Commander proposed alliance [A1] with HBot` (BREAK ALLIANCE lit right after, as the engine allows). StarDock - after warping 2â†’68â†’70â†’1 all three lit; `BUY_EQUIP item=photon_missiles qty=2 â€” ok â€¦ 24000cr` (ship panel Photons 2; fighters cap shown as 2,480 = headroom); `BUY_SHIP ship_class=cargotran â€” ok â€¦ (33175 cr)` with the choice list correctly omitting corp-only/unique hulls and the preview quoting net cost + trade-in from the envelope (holds 20â†’75). Combat - at 68 `DEPLOY_FIGHTERS qty=5 mode=toll â€” ok`, Here panel shows "Fighters 5 (toll) owner P2". Planets group verified by matrix only (no planet within reach in the test match).
- **Live:** `:8031` restarted on S4 (peek shows 34 precise / 0 coarse). Origin restart dropped the lhr forward as documented; the watchdog re-exposed it unattended 60 s later (`re-exposed OK`), `/bot` 200 through the new URL. **Re-read `.tw2k/public_base_url.txt`.**
- **Next:** Commander ACK -> S5 known-space map (`known_sectors` coords for known sectors only; quarantine `build_route_table`).
- **Blockers:** none.

### 2026-09-21 20:41 PT - Fable - parity-s5-known-map DONE
- **Commits:** `5bf5bbb` engine/copilot Â· `42a2c0a` `/bot` map Â· `dc3291b` tests/guide. Pushed; tip `dc3291b`.
- **Observation:** `known_sectors: [{id, x, y, port, is_fedspace, last_seen_day, warps_known}]` built by `_known_sectors()` from `player.known_sectors âˆª known_warps.keys âˆª {current}` - layout coords from `Sector.x/y` **for those ids only**; `port` is the remembered `known_ports[sid]["class"]` (live only for the current sector). UI-only: `format_observation` does not ship it (LLM seats keep `known_warps`). 45 -> 46 Observation fields; S2 coverage test forced the map card as its `data-obs` home.
- **F5 fixed:** `copilot/dashboards._bfs_hops` now walks `player.known_warps` instead of `universe.sectors` (the true-graph leak). Live prices remain a documented LAN `/play` copilot convenience (`/api/*` is behind the spectator gate on hosted URLs; `/bot` uses snapshots). `test_copilot_phase_h6` fixture now seeds the tester's warp memory so the ranking test stays meaningful.
- **`/bot` map** (`#knownMap` SVG in the Where column, replaces the bare warp list; text twin kept in a drawer): known nodes fitted to the viewBox from server coords; **you-are-here** highlighted; remembered port code under each node; FedSpace ring; edges from `known_warps` - solid when the return warp is remembered, dashed + arrowhead when one-way/return unknown; warp targets with no coordinates drawn as small dashed **stubs** placed around their source (no server coordinate used or implied). Nodes are `role=button`, `tabindex=0`, `data-testid="map-sector-<id>"`, `aria-label`, `<title>` tooltip, Enter/Space activate; click/keypress opens the S3 **plot_course** form prefilled with the target when `legal_actions.plot_course` is legal (map re-keys on legality/awaiting; stable DOM across polls). Reduced-motion respected.
- **Tests:** `tests/test_parity_s5.py` (4): fog (known ids exactly = visited/scanned/probed/current; coords equal the layout; probed-but-unscouted far sector shows no port even if it has one; LLM message has no coords), fresh player knows only where they stand, route BFS honours memory not the true graph, map UI contract (stub placement derives only from the source node's screen position). Full suite **539 passed**; ruff clean.
- **Browser proof (local 2-seat):** after warp 68 â†’ scan â†’ warp 70 â†’ scan the map showed 8 sectors (1 STARDOCK, 2 FED, 28, 34, 50 SBB, 61 BBS, 68, 70 here). Tap `map-sector-61` â†’ plot form prefilled target=61, preview "1 hop(s) through known warps Â· executes" â†’ `PLOT_COURSE target=61 execute=true â€” ok: Commander warped 70 â†’ 61 Â· autopilot completed 1/1 hops`. Tap `map-sector-2` from 61 â†’ preview "3 hop(s)" â†’ `â€¦ warped 61 â†’ 70 Â· 70 â†’ 68 Â· 68 â†’ 2 Â· autopilot completed 3/3 hops toward 2`. Done-when met without opening the harness.
- **Live:** `:8031` restarted on S5; P3 peek shows 6 known sectors (spawn knowledge). Tunnel survived this restart (200); watchdog still running.
- **Next:** Commander ACK -> S6 multi-bot ops + Path-B client (or S7 polish).
- **Blockers:** none.

### 2026-09-21 21:10 PT - Fable - parity-s6-multibot-pathb DONE
- **Commits:** `814add7` client + `/seats` fog Â· `82bac62` `/bot` lobby Â· `d854820` tests/docs. Pushed; tip `d854820`.
- **Path-B client:** `src/tw2k/agents/pathb_client.py` - `SeatClient` (async, `httpx.AsyncClient` injected: live URL or in-process ASGI), `run_seats()` (N seats concurrently, **one SeatClient + one brain object per seat**), `TurnContext` (observation, `llm_user_message`, rules, `deadline_at`, `seconds_left`, `legal(kind)`). Protocol: `/rules` once â†’ long-poll `observation?format=both` â†’ brain (budget = deadline âˆ’ margin) â†’ `POST /action {turn_seq}` â†’ `last_result`. A late or crashing brain gets a **safe `wait`** submitted before the deadline, so the scheduler never has to auto-WAIT an attended seat. Brains: `legal_heuristic_policy` (deterministic, envelope-only: sell if above cost basis / holds full, buy if a *known* port pays more, explore least-known warp, scan unmapped, wait) and `MailboxPolicy` (writes `<dir>/<SEAT>.pending.json` with observation + llm_user_message + rules-once, waits for `<SEAT>.decision.json` matching `turn_seq`, safe wait at margin). CLI `scripts/grokbot_seat_client.py` (`--seat|--seats`, `--policy heuristic|mailbox`, `--public` reads the tunnel URL file, tokens from `TW2K_TOKEN_<SEAT>` or tokens file). **No xAI anywhere** (tested).
- **Fog fix found while building:** `GET /harness/v1/seats` (readable with any seat token) was returning every sibling's `sector_id`, `last_result`, queue state. Now a lobby view only: `player_id, name, kind, alive, awaiting_input, attended, turn_seq` + `current_turn`, `match_status`, `day/tick`, `server_time`.
- **`/bot` lobby:** seat chips from `/seats` (name Â· YOUR TURN/their turn/acting/waiting Â· bot attached/no bot Â· turn_seq; `data-testid="seat-chip-<pid>"`, `data-attended`, `data-awaiting`); tap switches seats when that seat's token is stored in this browser (per-seat `localStorage`), otherwise prompts for a paste with the "one brain per seat" reminder. Stable DOM (re-keyed on state only).
- **Webhook (F8/D11) finished in S1** - verified end-to-end here: `TW2K_GROKBOT_WEBHOOK_URL` receives `turn_due` with runner-effective `deadline_at` (idle window for an unattended seat), `base_url`/`observation_url`/`action_url`, 5-field `brief`, no full Observation.
- **Tests:** `tests/test_parity_s6.py` (5): two in-process Path-B brains + one unattended external + one heuristic seat â†’ each brain â‰¥8 turns, 0 stale, 0 fallback waits, no external timeouts for attended seats, idle auto-WAITs only for the empty seat, brains acted (non-wait) â‰¥10 times; lean webhook captured via monkeypatched httpx; `/seats` field set exact; MailboxPolicy round-trip + deadline fallback; script `--help` + no-xAI grep. Full suite **544 passed**; ruff clean.
- **Live proof (local 5-seat: 2 heuristic + P3/P4/P5 external):** `grokbot_seat_client.py --seats P4,P5 --policy heuristic --max-turns 10` â†’ P4 and P5 each **10/10 ok, 0 failed, 0 stale, 0 fallback** (9 warps + 1 buy each). Browser on P3 showed the lobby: `P3 Commander Â· YOUR TURN Â· bot attached`, `P4 GrokPilot2 Â· waiting Â· bot attached`, `P5 GrokPilot3 Â· waiting Â· bot attached`. Note for operators: an **attended** seat that does not act holds the round for the full timeout (intended - a human thinking); the bots resumed at full speed the moment I closed the P3 tab (idle-WAIT). Documented in HOSTING.
- **Hosted:** `:8031` restarted as the canonical multi-bot layout **2 Qwen + P3, P4, P5 external** (idle-wait 8 s). `/seats` returns lobby fields only; tunnel re-exposed by the watchdog, `/bot` 200. Commander can attach brains now: `python scripts/grokbot_seat_client.py --public --seat P4 --policy mailbox` (tokens in `.tw2k/external_tokens.json`).
- **Docs:** GROK_BOT_PLAYER_GUIDE (Path-B client, mailbox protocol table, lobby endpoint), HOSTING_GROKBOT (multi-bot match runbook + rules of the road), GROK_BOT_CONNECTOR (helper pointer).
- **Next:** Commander ACK -> S7 polish/a11y, or COMPLETE if the north-star acceptance is met.
- **Blockers:** none.

### 2026-09-21 16:23 PT â€” Commander â€” Phase B ACK â†’ Phase C started
- **Ack:** Phase B assist @ `84ab3eb` accepted (expose script, portable cloudflared, `.tw2k/public_base_url.txt`, tunnel verified).
- **Status:** mailbox â†’ `COMMANDER_WORKING` (phase `hosted-bot-cu-c`). Cursor idle.
- **Doing:** Phase C computer-use playtest on `/bot?seat=P3` (Commander box). Match day 2; external seats out of turns â€” waiting day flip or logging that friction.
- **Next after Phase C:** Phase D insights â†’ `COMMANDER_QUEUED` for Cursor fix pass.



### 2026-09-21 16:29 PT â€” Commander â€” Phase C BLOCKED_NEEDS_BEN (CF browser 403)
- Phase B ACK stood; Phase C CU started.
- Box **curl** `/bot?seat=P3` â†’ 200; VENGEANCE public+local â†’ 200; cloudflared running.
- Box **browser** (computer-use) Ã—2 â†’ Cloudflare 403 `Your request was blocked.` No connect UI, 0 turns.
- mailbox â†’ `BLOCKED_NEEDS_BEN`. Ben: Tailscale Serve / non-CF URL / other path for box browser.
- Artifacts: Commander `/workspace/tw2k-playtest/SESSION_LOG.md` + `01-connect-blocked-403.png` `02-retry-403.png`.



### 2026-09-21 16:43 PT â€” Commander â€” Phase C resumed (tunnel + match restart)
- Re-ran `expose_hosted_bot.ps1 -Port 8031 -Detach` (old lhr.life dead); new base in `.tw2k/public_base_url.txt`.
- POST `/control/restart` (5-seat hosted body, turns_per_day 120); P3 day 1 / 120 turns.
- mailbox -> `COMMANDER_WORKING`; box computer-use playtest on `/bot?seat=P3` in progress.
- Cursor remains idle until Phase D queued.

### 2026-09-21 16:48 PT â€” Commander â€” Phase C done (1 turn) â†’ Phase D queued
- Connect + WARP 33 ok on `/bot?seat=P3` via lhr.life; artifacts under `docs/playtests/`.
- Root stall: after P3, **P4 external** `awaiting_input` with no bot â€” UI looked stuck; Refresh correct but opaque.
- Insights: `docs/playtests/COMPUTER_USE_INSIGHTS.md`. mailbox -> `COMMANDER_QUEUED` phase `hosted-bot-cu-d`.
