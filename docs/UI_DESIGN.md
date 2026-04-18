# TW2K-AI Spectator UI — Design Contract

This document is the single source of truth for the spectator UI at
`http://localhost:8000/`. It's written phase-by-phase so new work can be
reviewed against the contract and `tests/test_ui_smoke.py` can mechanically
assert it.

The UI is intentionally **vanilla** — no React, no Tailwind, no framework.
Three files:

| File | Role |
|------|------|
| `web/index.html` | Structure: panels, IDs, data attributes |
| `web/style.css`  | Styling, layout, animations |
| `web/app.js`     | WebSocket client, rendering, interactivity |

All assets are served by FastAPI at `/static/...`.

---

## Phase 1 — Resizable workspace (shipped)

### Goals
1. User owns the layout: every panel boundary is draggable.
2. Every panel can be collapsed to just its header.
3. A fullscreen-map mode for zoomed-in spectating.
4. Layout state persists across reloads via `localStorage`.
5. Keyboard shortcuts for common actions.

### Layout shell

```
┌───────────────────────────── header (topbar) ─────────────────────────────┐
│                                                                           │
├──────────────── col-left (flex-col) ──────────────┬── col-right ──────────┤
│                                                   │                       │
│                  MAP PANEL                        │   PLAYERS PANEL       │
│                                                   │                       │
├── resize-handle (horizontal, data-resize=map-e…) ─│───── resize-handle ───┤
│                                                   │                       │
│                 EVENTS PANEL                      │  TRANSMISSIONS PANEL  │
│                                                   │                       │
└───────────────────────────────────┬───────────────┴───────────────────────┘
                                    │
                    resize-handle (vertical, data-resize=left-right)
```

* `div#layout.layout` — root flex-row container.
* `div#colLeft.col.col-left` — flex-column holding map + events.
* `div#colRight.col.col-right` — flex-column holding players + messages.
* Each vertical/horizontal boundary is a `.resize-handle` element with a
  `data-resize` marker (`map-events`, `left-right`, `players-messages`).

### Panels

Every panel has:

| Requirement | Selector |
|-------------|----------|
| `data-panel` attribute (one of `map`, `events`, `players`, `messages`) | `.panel[data-panel]` |
| A `.panel-header` with title + `.header-right` container | `.panel > .panel-header` |
| A collapse button with `data-collapse="<panel>"` | `.collapse-btn` |
| A `.panel-body` wrapping all content below the header | `.panel > .panel-body` |

The players panel's header + collapse button are injected by
`renderPlayers()` on first render (because the panel is otherwise built
dynamically from WebSocket state).

### State persistence

Key: `tw2k:layout:v1` (versioned — bump the suffix when the schema changes).

Payload shape (all fields optional):

```json
{
  "rightWidthPx": 420,
  "mapFlex": 2.1,
  "eventsFlex": 1,
  "playersFlex": 1.4,
  "messagesFlex": 1,
  "collapsed": { "events": true },
  "fullscreenMap": false
}
```

### Keyboard shortcuts

| Key | Action | Notes |
|-----|--------|-------|
| `Space` | Pause / resume match | Same as clicking the ⏸ button |
| `F` | Toggle fullscreen map | Hides side + events columns |
| `Esc` | Exit fullscreen, close modal, or close shortcut toast | Priority in that order |
| `?` (or Shift+/) | Toggle shortcut help toast | Bottom-right overlay |
| `R` (no modifiers) | Reset layout to defaults | Clears `localStorage` |
| `1`–`9` | Flash / select the Nth player | Phase 3 will add follow-camera |

Shortcuts are ignored while focus is inside an `<input>`, `<textarea>`, or
any `contentEditable` element — so typing in the replay scrubber never
pauses the match.

### JS public surface (Phase 1)

These functions are expected to exist in `web/app.js` and are asserted by
`tests/test_ui_smoke.py`:

```
initLayout           -- bootstrap (called from the IIFE)
initResizers         -- wire pointer events on every .resize-handle
initCollapseButtons  -- delegated click handler for .collapse-btn
initShortcuts        -- global keydown handler
applyLayout(cfg)     -- write flex-basis / collapse state from cfg
loadLayout()         -- read cfg from localStorage
saveLayout(patch)    -- merge-patch cfg into localStorage
resetLayout()        -- clear everything
togglePanel(key)     -- collapse/expand one panel
toggleFullscreenMap(force?) -- toggle or force fullscreen mode
```

---

## Phase 2 — Map clarity (shipped)

### Goals
1. Reduce visual clutter at default zoom so the galaxy is readable.
2. Give the user first-class zoom/pan controls — no hidden gestures.
3. Provide an always-visible orientation aid (mini-map) for long pans.
4. Scale detail with zoom level so close-ups show more, overview shows less.

### Level-of-detail (LOD)
The `#galaxy` SVG gets one of three classes depending on the ratio of the
full-galaxy extent to the current viewBox width:

| Class | When | Visual effect |
|-------|------|---------------|
| `zoom-far`  | galaxy/view < 0.75 (zoomed out past overview) | warps dimmed to 25% / sector labels hidden |
| `zoom-mid`  | 0.75 ≤ galaxy/view < 2.2  | warps at 55% opacity, labels dimmed |
| `zoom-near` | galaxy/view ≥ 2.2 | warps fully drawn, sector strokes heavier |

LOD is driven entirely by CSS (see `#galaxy.zoom-*` rules in `style.css`),
so future phases can re-theme without touching the zoom math.

### Floating controls
A `.map-controls` toolbar is anchored to the bottom-right of the map panel:

| Button | `data-map-action` | Action |
|--------|-------------------|--------|
| `+` | `zoom-in`       | Zoom in 25% (clamped at 12× in)  |
| `−` | `zoom-out`      | Zoom out 25% (clamped at 3× out) |
| `⤢` | `fit`           | Reset viewBox to full-galaxy extent |
| `▣` | `toggle-mini`   | Show/hide the mini-map (persisted to `tw2k:map:mini`) |
| `NN%` | (readout)     | Current zoom ratio (100% = fit) |

Wheel-zoom respects the same clamp limits as the buttons.

### Mini-map
`#miniMap > svg#miniMapSvg` renders a static dot-cloud of every sector
plus a dynamic ship layer and a viewport rectangle indicating the part
of the galaxy the main map is showing. Clicking anywhere on the mini-map
recenters the main viewBox on that galaxy coordinate.

### Keyboard shortcuts (Phase 2 additions)

| Key | Action |
|-----|--------|
| `+` / `=` | Zoom in |
| `-` / `_` | Zoom out |
| `0` | Fit galaxy |
| `M` | Toggle mini-map |

### JS public surface (Phase 2)

```
fitGalaxy            -- reset viewBox to galaxyExtent
zoomBy(factor, cx?, cy?) -- scale viewBox around (cx,cy) with clamping
buildMiniMap         -- build static mini-map SVG once per match
refreshMiniShips     -- re-draw ship dots on the mini-map (per render)
setMiniMapVisible    -- show/hide + persist
initMapControls      -- wire the floating toolbar
updateLODClasses     -- apply zoom-far/mid/near to #galaxy
```

## Phase 3 — Follow-camera + drawer (shipped)

### Goals
1. First-class "zoom in on this player" affordance — the user shouldn't
   have to manually chase ships across the galaxy.
2. A dedicated side drawer for deep-dive info (ship loadout, diplomacy,
   sector contents) without squeezing the rest of the UI.
3. Clear visual cue on the map when follow mode is active.

### Interaction surfaces

| Trigger | Effect |
|---------|--------|
| Click a player card in the Commanders panel | Opens player drawer, starts following |
| Press `1`–`9` | Opens player drawer for the Nth commander, starts following |
| Click any sector node on the map | Opens sector drawer (no follow) |
| Drawer `◎ Follow` button | Toggles follow-camera on/off for the open player |
| Drawer `✕` button, or `Esc` | Closes drawer and clears follow |

### Follow-camera behavior
* When a player is followed, `updateFollowCamera()` runs after every
  render. It only re-centers the viewBox when either:
  * the followed player's sector changed since last centering, OR
  * the player drifted outside a 15% margin of the current view.
* This keeps the camera smooth during pans/zooms and snaps back only
  on meaningful movement.
* A dashed accent ring (`.ship-follow-ring`) pulses around the
  followed ship so the spectator knows follow is active.

### Drawer DOM contract
```
<aside id="detailDrawer" class="detail-drawer" hidden>
  <div class="drawer-head">
    <div class="drawer-title" id="drawerTitle">…</div>
    <div class="drawer-head-right">
      <button class="drawer-btn" id="drawerFollowBtn" data-drawer-action="toggle-follow">◎ Follow</button>
      <button class="drawer-btn" data-drawer-action="close">✕</button>
    </div>
  </div>
  <div class="drawer-body" id="drawerBody">…</div>
</aside>
```

`drawer-body` content is regenerated on every `render()` via
`renderDrawer()`, so live stats (credits, fighters, followed player's
current sector) stay in sync automatically.

### JS public surface (Phase 3)

```
openDrawer(kind, id)   -- kind = "player" | "sector"
closeDrawer()
renderDrawer()         -- route to player/sector renderer
renderPlayerDrawer(id)
renderSectorDrawer(id)
setFollow(playerId)    -- null to clear
toggleFollow()         -- based on drawer's current player
updateFollowCamera()
initDrawer()           -- event wiring
```

## Phase 4 — Player trajectory (shipped)

### Goals
1. Give spectators a "where has this player been going?" signal at a glance.
2. Avoid client-side accumulation: if you reload the page the trend
   should still be there.
3. Keep the wire format small — this is spectator flavor, not telemetry.

### Server: `/history` ring buffer

`MatchRunner._history: dict[pid, collections.deque]` is sized by
`MatchRunner.HISTORY_MAX_SAMPLES` (default 240). After every full
round-robin pass through agents the runner calls
`_record_history_sample()`, which appends:

```json
{
  "seq": 1234,
  "day": 3,
  "tick": 42,
  "credits": 12500,
  "net_worth": 17800,
  "fighters": 40,
  "shields": 250,
  "experience": 5,
  "alignment": 2,
  "sector_id": 17,
  "alive": true
}
```

`/history?limit=N` returns `{"samples": {pid: [...]}, "max_samples": 240}`
with at most N samples per player (default 120). The buffer is reset
on `await runner.start(spec)`.

### Client: inline sparklines

`state.history: Map<pid, Sample[]>` is populated by `fetchHistory()`,
called once at boot and every 4 seconds thereafter. Three sparklines
render inline on each player card (and inside the detail drawer):

| Metric | Color |
|--------|-------|
| credits | var(--accent) |
| net_worth | `#ffd166` |
| fighters | `#ff6e6e` |

`sparklineSvg(series, color)` produces a tight 72×18 polyline with a
dot at the right end. `.spark-row` / `.spark-cell` / `.spark-label`
are the CSS hooks. When history hasn't been seeded yet the row shows
an italicised "history" placeholder instead of an empty SVG.

### JS public surface (Phase 4)

```
fetchHistory()              -- poll the server for the latest buffer
sparklineSvg(series, color) -- pure fn; returns an <svg> string
renderSparklineRow(pid)     -- 3-up sparkline row for a player card / drawer
SPARK_METRICS               -- frozen config: which keys to graph, in order
```

### Tests

* `tests/test_history_buffer.py` — 5 unit tests on the server side
  (ring buffer cap, limit parameter, sampling tracks credit changes,
  required fields present, empty state).
* `tests/test_ui_smoke.py` — 3 new static assertions: JS helpers exist,
  CSS selectors exist, `state.history` is a `Map`.

---

## Testing

`tests/test_ui_smoke.py` runs in CI and asserts the **static** contract:
required IDs, panel data attributes, resize handles, collapse buttons,
CSS selectors, JS function names, and shortcut handling. It does NOT
launch a browser — that's covered by live matches after each phase.

For manual smoke-test of Phase 1:

1. `tw2k serve` → open `http://localhost:8000`.
2. Drag the vertical handle between left and right columns — the right
   column should resize and the new width should persist across reload.
3. Drag the horizontal handle between map and events — ratio should persist.
4. Click the ▾ button on each panel — panel collapses to header, chevron
   rotates, state persists.
5. Press `F` — map goes fullscreen; `Esc` exits.
6. Press `?` — shortcut toast appears; `Esc` or `?` again to dismiss.
7. Press `R` — layout resets to defaults, `localStorage` is cleared.
8. Press `1` — first player card flashes briefly.
