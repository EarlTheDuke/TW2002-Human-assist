# Grok Bot plays TW2K like a human (computer use on `/bot`) - master plan (2026-09-26)

**Status:** QUEUED for Cursor (local Agent on VENGEANCE). Owner: Commander (Grok Bot). Approver: Ben.
**Branch:** `feature/grokbot-player` (base = `feature/seat-bot-competitive` @ `4b0fe93` + `feature/clip-library` merged @ `b6bee8c`).
**Worktree:** `C:\Users\sugar\Desktop\ALL AI GAMES\Projects in prgress\TW2K-grokbot-player`
**Mailbox:** `docs/COMMANDER_NEXT.md` in the MAIN folder (`...\TW2002 Human assist cursor`), same AFK loop as `docs/GROK_CURSOR_HANDOFF.md`.

## Goal
Commander (Grok Bot) takes a seat and plays a full TW2K match the way a human does: it opens the
`/bot` cockpit in a browser, reads the screen, and clicks/types actions. No xAI API key, no scripted
brain, no spectator `/state`. The scripted `seat_brain_v2.py` stays as the control/baseline seat.

## Where we are (verified 2026-09-26)
- Bot-human parity S1-S4 + S6 delivered (`/bot` tapes, legality, 34 verbs, known-space map, multi-seat lobby, Path-B client). S5 docs open.
- Cockpit parity plan `docs/plans/2026-09-26-cockpit-parity-plan.md` lists gaps G1-G26 and slices CP0-CP6. Not started.
- `turn_due` webhook exists (`src/tw2k/server/external.py`, `TW2K_GROKBOT_WEBHOOK_URL`); Grok Bot has a matching webhook routine that has never fired in a real match.
- `run_hosted_grokbot.ps1` has `-TimeoutS` (default 180) and `-IdleWaitS` (8); external seat timeout is too short for screenshot play.
- Tunnel: `scripts/tunnel_watchdog.ps1` + `.tw2k/public_base_url.txt` exist but the tunnel is currently DOWN (public `/bot` returns 503). Grok Bot's computer cannot reach `localhost` on VENGEANCE.
- `web/bot.*` already has ~82 `data-testid` hooks; almost no keyboard shortcuts.

## Hard rules (every slice)
1. Fog-safe. `/bot` shows only the seat's own fogged `Observation`. Never feed spectator `/state` to a seat.
2. Never commit tokens, public URLs or spectator links. `.tw2k/` stays gitignored.
3. Do NOT touch the running match on `:8031` or the main folder's working tree (except the mailbox file). Work and test only in the worktree, on ports `:8032+`.
4. Each slice: tests + `ruff` clean, commit(s) pushed to `feature/grokbot-player`, then mailbox `WAITING_COMMANDER` + Delivered note.
5. Docs accurate to what shipped; no invented APIs.

## Slices (in order)

### G1 - Cockpit information parity (= CP1-CP5)
Do CP1 empire planet tape, CP2 other players fog list, CP3 operator dialogue + directive meta,
CP4 prompt twins (stage_hint / rules), CP5 own-thought toggle, as specified in the cockpit parity plan.
**Done when:** every field an API LLM seat receives in `format_observation` is visible on `/bot` without opening Raw obs (CP acceptance list); tests added.

### G2 - "One-screen turn" layout for computer use
- `/bot?seat=P6&mode=cu`: a dense layout that fits the full decision context in ONE 1280x800 screenshot: whose turn + deadline countdown, ship/cargo/credits, sector + warps + port prices, known-space mini map, goal/stage hint, last 5 events, last action result.
- Big high-contrast action buttons; every actionable control has a stable `data-testid` and a visible text label.
- A plain-text "Turn card" block summarizing the same state for easy reading.
- Result toast after each action (ok / illegal + reason) that stays until the next action.
- Keyboard shortcuts for common verbs (warp by number, buy/sell, plot course, end turn), listed on screen.
**Done when:** a Playwright smoke test screenshots at 1280x800 and asserts all decision fields are inside the viewport; the default `/bot` layout is unchanged.

### G3 - Seat login without pasting secrets
- Host writes a per-seat link to `.tw2k/seat_links/<seat>.txt` (like `spectator_link.txt`), e.g. `/bot/claim?seat=P6&token=...`, which sets an HttpOnly cookie and redirects to `/bot?seat=P6&mode=cu`.
- `/bot` API calls accept that cookie in place of the pasted bearer token. Per-seat scope kept (403 wrong seat).
**Done when:** tests cover claim, cookie auth, wrong seat 403, invalid link 401.

### G4 - Reach + turn cadence for a human-speed player
- Tunnel: host wrapper `-Tunnel` switch starts `tunnel_watchdog.ps1`, re-exposes on 503, writes the current URL to `.tw2k/public_base_url.txt`, logs a health line.
- Per-seat timeouts: `-ExternalTimeoutS` (default 600 for computer-use seats) separate from LLM seats; idle-WAIT stays for unattended seats.
- `turn_due` webhook to `TW2K_GROKBOT_WEBHOOK_URL`: `seat`, `turn_seq`, `deadline_at`, public `/bot` URL (no observation dump, no token). Retry with backoff; log deliveries.
- "Hold my slot" control so the computer-use player can take several actions in one scheduler slot and explicitly end it.
**Done when:** a local test match on `:8032` shows logged webhook deliveries, the 600 s external deadline honored, LLM seats unaffected.

### G5 - Pilot match (Commander plays by screen)
- `scripts/run_cu_pilot.ps1`: seed 250925, 2 days, 60 turns/day; P1 QwenA (LLM), P2 scripted `seat_brain_v2` (control), P3 Commander (external, computer use). Port 8032, tunnel on, spectator gate on.
- Per-action log for the CU seat: wall time per action, illegal attempts, retries.
- Cursor STOPS at "ready to launch" and sets `BLOCKED_NEEDS_BEN`. Ben gives the go; Commander plays from its desktop browser.
**Done when:** dry run passes (host up, lineup verified, webhook test ping delivered), then Ben's go.

### G6 - Insights loop
After the pilot, Commander writes `docs/playtests/cu-pilot-*/INSIGHTS.md` (what was hard to see, slow, or misleading on screen). Those become the next slices. Repeat until a full 10-day match is practical.

### G7 - Docs (absorbs seat-bot S5)
Player guide for humans / computer use at `/bot` (mode=cu, shortcuts, claim link), plus seat-bot S5 notes (observation fields, banned god-state, goal ladder).

## Order + stop points
G1, G2, G3, G4, then G5 (stop for Ben), then G6/G7. Commander ACKs each slice via the mailbox before queuing the next.