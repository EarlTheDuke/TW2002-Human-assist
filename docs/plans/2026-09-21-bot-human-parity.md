# Canonical plan: complete `/bot` cockpit + multi-Grok-Bot parity (2026-09-21)

**Status:** MERGED by Commander from:
- `docs/plans/2026-09-21-commander-parity-plan.md`
- `docs/plans/2026-09-21-fable-parity-plan.md`

**Branch:** `feature/grok-bot-harness`  
**North star:** `/bot` becomes a complete human TW2K interface. 2–3 Grok Bots compete with the same fogged Observation, map memory, rules text, and legal verbs as TinyBox LLM/API seats. Immersive stills/video are a deferred wish list with an event/presentation boundary designed now.

**Hard constraints**
1. No xAI / `api.x.ai` as a Grok Bot brain.
2. One Grok Bot brain per external seat.
3. `/bot` renders authoritative Observation + fogged events — never a second engine.
4. Computer-use + a11y first class: text, stable DOM/`data-testid`, nothing blocks a turn.
5. Fog of war must hold on hosted URLs (spectator gate required).

---

## Shared truth (code findings Fable F1–F11 — accepted)

| ID | Finding | Merge decision |
|----|---------|----------------|
| F1 | Harness returns `observation: null` unless `awaiting_input` | **S1 peek** required before UI tapes |
| F2 | `recent_events` drops payloads; capped | **S1 fogged event stream** + per-kind `facts` whitelist (= media boundary) |
| F3 | Legality only inside runner handlers | **S3 `legal_actions()`** engine query on Observation |
| F4 | `/play` already has verb forms + economy | **Reuse presentation; one cockpit long-term** |
| F5 | `build_route_table` true-graph + live price leak | Quarantine; cockpit map uses `known_*` only |
| F6 | Unauthenticated spectator on hosted URL | **S1 spectator token / loopback split** |
| F7 | `play_grok_external_seats.py` uses xAI | Remove or loud `--allow-xai-fallback` gate |
| F8 | Webhook deadline ignores MatchSpec / idle | Fix in multi-bot / Path-B slice |
| F9 | `Sector.x/y` exist | Known-sector coords for map (S5) |
| F10 | `format_observation` is a subset | New fields ship to both Observation and LLM format (or documented UI-only) |
| F11 | `/bot` is a turn-taking shell | Keep shell; replace panels with Observation-driven UI |

---

## Path split (kept from Commander)

| Path | Who | Think | Act |
|------|-----|-------|-----|
| A Cockpit | Humans + CU bots | What `/bot` shows | Buttons |
| B Harness brain | Competitive Grok seats | `observation?format=both` + `/rules` | `POST .../action` |

Extra Grok seats default to Path B. CU proves the human product.

---

## Resolved disagreements (Commander accepts Fable)

| ID | Resolution |
|----|------------|
| D1 | Peek before info UI |
| D2 | Fogged event endpoint in S1 (not deferred to polish) |
| D3 | `legal_actions()` from engine; UI does not re-implement rules |
| D4 | Real known-space map with server coords for known sectors (S5), not just a list |
| D5 | Human notes via `scratchpad_update` / `goal_*` on Action; local draft until submit |
| D6 | **No** server-side recommend-move scorer; show `action_hint` + `legal_actions` |
| D7–D9 | Spectator gate, quarantine route table, remove/gate xAI script in S1 |
| D10 | Port `/play` forms onto harness transport; later `HumanAgent` → `ExternalAgent(kind=human)` |
| D11–D12 | Webhook deadline + Path-B reference client in multi-bot slice |
| D13 | **Server data first (S1), then UI** |

Commander E1–E5 map to Fable S2–S7 with S1 inserted first.

---

## Delivery slices

### S1 — Server data + fog fixes (FIRST BUILD)
Owner: Fable  
Done when:
1. Authenticated seat can **peek** its own Observation between turns (fog-safe).
2. Fogged **event stream** with seq cursor + per-kind whitelisted `facts` (media-ready boundary; text always present).
3. Hosted spectator gated (`TW2K_SPECTATOR_TOKEN` or loopback-only spectator bind).
4. `play_grok_external_seats.py` removed or `--allow-xai-fallback` with loud banner.
5. Webhook `deadline_at` uses MatchSpec timeout + idle rule; payload includes `turn_seq` + `base_url` (not full Observation dump).
6. Tests cover peek, event fog whitelist, spectator 401 without token, webhook deadline.
7. Docs note: re-run `expose_hosted_bot.ps1 -Detach` (localhost.run) before next CU; prefer Tailscale long-term.

### S2 — Read-only cockpit tapes (= Commander E1)
Ship/cargo/loadout, port stock+prices, adjacent strip, known_ports table, known_warps summary, trade_summary + trade_log, recent_failures, English last_result (JSON drawer), scoreboard strip. Peek-powered so values update while WAITING.

### S3 — Legality + core verbs
`legal_actions()` on Observation; trade form (commodity/qty/haggle); plot_course; probe; keep warp/scan/wait. Buttons only when legal.

### S4 — Full context verb groups
Attack/hail when occupants; StarDock cluster in sector 1; planet cluster when applicable; alliance/corp later if already legal in engine.

### S5 — Known-space map
Draw known sectors using server x/y for known only; you-are-here; click-to-plot when legal.

### S6 — Multi-bot ops + Path-B client
`-ExternalSeats P3,P4,P5` lobby/seat chips; one brain per seat; `grokbot_seat_client.py` (observation both + rules + POST); turn_due webhook hardened; idle-WAIT remains default for unattended.

### S7 — Human polish / a11y
Keyboard shortcuts, English event feed, notes/goals UI, mobile targets, reduced-motion, captions hooks for future media.

### Future wish list (deferred)
Semantic event → optional still/clip; skippable; captioned; never blocks turn; never encodes game rules in assets. Asset manifest / theme packs later.

---

## First queued task
**S1** only. No S2+ until Commander ACKs S1.