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

## Phase 2 — Map clarity (planned)

Level-of-detail rendering, floating map toolbar with layer toggles,
minimap (off by default), zoom-to-fit buttons, sector/player search.

## Phase 3 — Follow-camera + drawer (planned)

Click a player card → camera locks to them (auto-pan on warp).
Click a sector → right-drawer detail pane.

## Phase 4 — Player trajectory (planned)

Thin `/history` ring buffer on the server + inline SVG sparklines on
each player card.

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
