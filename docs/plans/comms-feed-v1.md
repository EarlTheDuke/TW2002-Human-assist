# comms-feed-v1

Landed on `feature/grokbot-player` in #198 (`81df2c1b`, "Keep trade failures off the COMMS card"). This file records that contract so a later Cursor does not reopen it or land a second filter.

Do not open a second COMMS-filter pull request. #199 was closed as a duplicate of #198. #199 proposed `web/comms-stream.js` and a paint-only filter. That helper was not merged. The landed filter is `web/comms-feed.js`.

## COMMS card

The redesign COMMS card is player channels only:

- Fed Comm
- sub-space radio
- a private hail
- a corporation memo

The card is `#commsCard` (`data-testid="comms-panel"`) in `web/redesign.html`. Its header is COMMS. It paints `#turnLog` from chat rows and holds the send form (Fed Comm, sub-space radio, Hail, Corporation).

## Action outcomes

`TRADE_FAILED`, haggle misses, port notices, planet notices, combat notices, and every other action outcome stay on the LOG / activity feed and on lastResult / verdict. They never appear under the COMMS header.

The LOG is `#activityCard` / `#log` (`data-testid="activity-log"`), outside the COMMS card. lastResult is `#lastResult`. The engine verdict is `#verdict`. A failed trade such as `Guest 1 trade failed: You only have 15 empty holds.` is a `trade_failed` event. It stays on the LOG and on lastResult / verdict.

## Implementation

- `web/comms-feed.js` exports `TW2KCommsFeed` (`isChat`, `isActionOutcome`, `commsFeed`, `activityFeed`, `commsLines`, `lineOf`).
- `web/redesign.html` loads `/static/comms-feed.js` before `/static/redesign.js`.
- `web/redesign.js` paints the LOG with `activityFeed` and the COMMS card with `commsLines`.
- Tests: `tests/test_comms_feed_v1.py`.

Chat kinds the filter keeps are `fed`, `fedcomm`, `radio`, `hail`, `corp`, `corp_memo`, and `broadcast` (the Fed Comm send path). A bare line with no kind still counts as chat when it is a Federation comm-link, a sub-space radio line, a hail, a corporation memo, or a hail that fell on deaf ears. A known non-chat kind stays an action outcome even if the text mentions a hail.

## Seat

The filter does not look at the seat. AI traders are not clamped. A `trade_failed` row with an AI seat stays on the activity feed. The filter does not mute that seat and does not move the row onto the COMMS card.

## Other pages

`/bot` Comms reads the inbox separately. `web/bot.html` paints `#inbox` from the observation inbox in `renderComms` (`web/bot.js`). That card does not use `TW2KCommsFeed`. On `/bot`, `trade_failed` stays in the trade event group.

`/play` has no COMMS stream under that header. `web/play.html` has no COMMS header. It does not paint `recent_events` under COMMS. Neither page needs a paint change for this contract.
