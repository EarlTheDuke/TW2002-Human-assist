# Make it amazing — ranked slices (2026-09-27)

Planning only, plus the four V4-lite nits that shipped in the same turn. No product code from this list until Commander queues a slice. No paid API, no real video, no `:8031` / `:8032`.

## What was played

Short offline matches on a test host (port ≥ 8033, seed 250925, heuristic P1, external P2). The token was a throwaway test value, not a live seat.

| Seat | What happened |
|---|---|
| Human, default `/bot` at 1440×900 | Load showed the media HUD over the ship card. The stage detail box overlapped the stage value. SELL opened an 8-control form. There is no one-click trade on this layout. SCAN was `ok` (sector 16). |
| Computer-use, `mode=cu` at 1280×800 | Page did not scroll (`scrollHeight` 800). Two one-click trade buttons were on screen. The Refresh button exists but is not visible once connected (R still works; a click agent cannot see it). |
| Seat brain, 6 turns, `--harness` on that same host | 6/6 ok. Kinds: `plot_course` 2, `buy_ship` 1, `trade` 1, `warp` 2. No engine failures. |

Read for this pass: video-cockpit phase plan (V3–V7 and §7), `docs/plans/2026-09-26-seat-bot-next.md` (N1–N4 already landed; do not reopen), and `docs/playtests/COMPUTER_USE_INSIGHTS.md` (2026-09-21). The old P0 stall and the missing testids are already fixed (idle auto-WAIT, G2 banner names the blocking seat, warp/scan testids). The leftover that still showed up today is click targets that are hidden or covered.

## Ranked backlog

Each row is one slice. Fog-safety means the screen may use only that seat's Observation and `/events`.

| # | Slice | Payoff | Size | Risk | Test idea | Fog |
|---|---|---|---|---|---|---|
| 1 | Opening clip must not cover the ship | The first thing a human sees is the ship, not a still on top of it | S | Low | Playwright: after connect, ship card is visible and its box does not intersect a visible HUD | Event stills only, from the fogged batch |
| 2 | One-click trades on the default layout | SELL/BUY in one click, same as `mode=cu` | S | Low | Click `quick-sell-fuel_ore` on default `/bot`; toast says SELL and ok | Qty from `legal_actions`, this port only |
| 3 | Stage detail sits under the stage value | The hint line is readable | S | Low | At 1440×900 both testids are visible and their boxes do not intersect | `stage_hint` is already on the page |
| 4 | Visible Refresh in `mode=cu` | A click agent can refresh without hunting for R | S | Low | `refresh` is visible inside `#cuScreen` at 1280×800 and a click refetches | No new data |
| 5 | Default keys S and 1–9 | Same muscle memory as CU, on the big layout | M | Keys can fire inside a form | S scans; 1 warps; ignored in inputs, contentEditable, and key-repeat | Existing verbs only |
| 6 | Warp chip shows a known port code | "44 BBS" instead of a bare number | S | Low | A visited neighbour with a remembered port renders that code on the warp button | `known_sectors` / `known_ports` only; unknown stays a number |
| 7 | Port tape marks what you can sell | The commodity you hold is obvious | S | Low | With fuel ore aboard, that row has `data-can-sell="true"` | This sector's port plus your cargo |
| 8 | Planet runway | "organics for N days" on an owned world | S | The day math must match `planets.py` | A world with a known stockpile shows the same day count the engine would | `owned_planets` only |
| 9 | Plot confirm shows hops and the first step | You see the route before you spend the turn | S | Low | The plot form's preview contains the hop count and the first sector id | `plot_course` result is already the seat's own route |
| 10 | Last result stays readable during a clip | The toast/result is not under the still | S | Ties to slice 1 | After a trade, `#lastResult` is visible and not covered | No new fields |
| 11 | CU trade button shows the credit total | "SELL Fuel x10 · 320 cr" before the click | S | Low | The button text includes the list-price total from the envelope | Envelope prices only |
| 12 | History does not play as a new clip | Connecting mid-match does not replay the backlog | S | Might drop a clip the player wanted | Events with `seq` already stored at connect do not call `playResolved` | Same fogged feed, just not replayed |

## Top 3, specced

### 1. Opening clip must not cover the ship

**Payoff.** On the default layout the v1 HUD is `position: fixed` over the right column. A play at 1440×900 found it visible on load and intersecting `[data-testid=ship]`.

**Change.** Events already in the log when the page connects are history. Do not start a clip for them. A clip that does play uses the viewport (or the CU slot), and the v1 HUD is not shown on top of `#ship`. Slice 12 is the same rule; build them together.

**Accept.**
- Playwright, default `/bot`, 1440×900, test host ≥ 8033: after the turn banner is up, `[data-testid=ship]` is visible and does not intersect a visible `[data-testid=media-hud]`.
- A trade after connect still plays `dock.port` in the viewport (existing V2 test stays green).
- `mode=cu` still docks a still in `#cuMediaSlot` and still has no `<video>`.

**Fog.** The batch is the seat's `/events`. No `/state`.

### 2. One-click trades on the default layout

**Payoff.** CU already sells in one click. The default SELL opened a form with 8 controls (commodity, qty, price, confirm). Same trade, more clicks, easier to mis-click.

**Change.** Render the same buttons the CU row uses (`quick-sell-<commodity>` / `quick-buy-<commodity>`, max qty, list price, no haggle) under the verb pad on the default layout. Keep the form behind MORE / the existing verb for a chosen price.

**Accept.**
- On a port that buys fuel, with fuel aboard: `[data-testid=quick-sell-fuel_ore]` is visible on default `/bot`.
- One click posts a trade. `#lastResult` contains `SELL` and `ok`.
- A second test with an empty hold: the sell button is absent, not a dead control.
- CU buttons keep their `cu-quick-*` testids. G2 still fits 1280×800.

**Fog.** Quantities come from `legal_actions` for this seat. The button does not read another seat's cargo.

### 3. Stage detail sits under the stage value

**Payoff.** `[data-testid=stage-hint-detail]` overlapped `[data-testid=stage-hint]` at 1440×900, so the hint line and the stage name fight for the same pixels.

**Change.** Layout only. The detail is a block under `#sbStage` inside the same card, wrapping instead of covering. No new observation fields.

**Accept.**
- Playwright at 1440×900: both nodes are visible, both have non-zero height, and their boxes do not intersect.
- The detail text is unchanged (still the server stage hint).
- The scoreboard still fits one row at 1440×900, or wraps without covering Credits.

**Fog.** Display only.

## Needs Ben

- Real video clips (phase-plan V3) and any paid image or video API.
- Sound, if it means new audio assets. The mute label can stay as it is.
- A live match on `:8031` or the pilot host on `:8032`.
- API keys or tunnel credentials.

## Not in this list

Seat-brain N1–N4 are already in the tree. The 6-turn local brain run did not fail. A new brain rung is not the next player-visible win. V4-lite cache, preload, counters, and CU stills just shipped; do not rebuild them.
