"""Static smoke tests for the spectator UI.

These do NOT launch a browser. They parse `web/index.html`, `web/style.css`,
and `web/app.js` as text and assert that the structural contract between
the three is intact:

* Required element IDs exist
* Each resizable/collapsible panel has the expected data attributes
* The CSS ships class hooks for collapse / fullscreen / resize handles
* The JS exports the key initialisation entry points

This lets CI catch accidental breakage (e.g. a grep-and-replace removing
an ID the JS depends on) without needing a headless browser.

Phase 1 contract is documented in docs/UI_DESIGN.md.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def html_text() -> str:
    return (WEB / "index.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def css_text() -> str:
    return (WEB / "style.css").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def js_text() -> str:
    return (WEB / "app.js").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# HTML structural parser
# ---------------------------------------------------------------------------


class DomCollector(HTMLParser):
    """Minimal parser that records tags with their attributes in-order."""

    def __init__(self):
        super().__init__()
        self.tags: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, {k: (v or "") for k, v in attrs}))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, {k: (v or "") for k, v in attrs}))


def parse_html(html: str) -> list[tuple[str, dict[str, str]]]:
    p = DomCollector()
    p.feed(html)
    return p.tags


def ids(tags):
    return {attrs.get("id") for _, attrs in tags if attrs.get("id")}


def classes_for(tags, sought_id: str) -> set[str]:
    for _, attrs in tags:
        if attrs.get("id") == sought_id:
            return set(attrs.get("class", "").split())
    return set()


def find_with_attr(tags, key: str, value: str) -> list[dict[str, str]]:
    return [attrs for _, attrs in tags if attrs.get(key) == value]


# ---------------------------------------------------------------------------
# Structural tests
# ---------------------------------------------------------------------------


REQUIRED_IDS = {
    # Topbar
    "statusDot", "statusLabel", "dayLabel", "tickLabel",
    "pauseBtn", "restartBtn",
    # Layout shell
    "layout", "colLeft", "colRight",
    # Panels
    "panelMap", "panelEvents", "panelPlayers", "panelMessages",
    # Map
    "galaxy", "sectorTip", "mapSectorCount",
    # Event feed
    "eventFeed", "replayLive", "replayScrub", "replayLabel",
    # Transmissions
    "messageFeed",
    # Modals / overlays
    "gameOverModal", "gameOverSummary", "modalClose",
    "shortcutsToast",
}


def test_required_element_ids_present(html_text):
    tags = parse_html(html_text)
    present = ids(tags)
    missing = REQUIRED_IDS - present
    assert not missing, f"index.html missing required IDs: {sorted(missing)}"


def test_panels_have_data_panel_attribute(html_text):
    tags = parse_html(html_text)
    expected = {"map", "events", "players", "messages"}
    found = {attrs.get("data-panel") for _, attrs in tags if attrs.get("data-panel")}
    assert expected <= found, f"missing data-panel names: {expected - found}"


def test_each_resize_handle_has_a_kind(html_text):
    tags = parse_html(html_text)
    handles = [
        attrs for _, attrs in tags
        if "resize-handle" in attrs.get("class", "")
    ]
    assert len(handles) >= 3, f"expected >= 3 resize handles, got {len(handles)}"
    kinds = {h.get("data-resize") for h in handles}
    assert {"map-events", "left-right", "players-messages"} <= kinds


def test_collapse_buttons_cover_every_panel(html_text, js_text):
    tags = parse_html(html_text)
    static_targets = {
        attrs.get("data-collapse")
        for _, attrs in tags
        if "collapse-btn" in attrs.get("class", "")
    }
    # The players-panel collapse button is injected by renderPlayers().
    # Assert either it's in the HTML or the JS emits it.
    has_players = ("players" in static_targets) or (
        'data-collapse="players"' in js_text
    )
    assert has_players, "no collapse button defined for the players panel"
    for key in ("map", "events", "messages"):
        assert key in static_targets, f"static collapse button missing for {key}"


def test_shortcuts_toast_lists_known_keys(html_text):
    # The toast should mention all shortcuts users can actually invoke in
    # Phase 1: Space, F, Esc, ?, R, and the 1-9 player focus placeholder.
    assert "Space" in html_text
    assert ">F<" in html_text or "<kbd>F" in html_text
    assert "Esc" in html_text
    assert ">?<" in html_text or "<kbd>?" in html_text
    assert ">R<" in html_text or "<kbd>R" in html_text


# ---------------------------------------------------------------------------
# CSS contract
# ---------------------------------------------------------------------------


def test_css_has_layout_hooks(css_text):
    required_selectors = [
        ".layout",                 # root flex container
        ".col-left", ".col-right", # columns
        ".resize-handle",           # drag handles
        ".resize-horizontal", ".resize-vertical",
        ".panel.collapsed",         # collapse state
        ".layout.fullscreen-map",   # fullscreen mode
        ".shortcuts-toast",         # toast
        ".collapse-btn",            # button styling
        ".panel-body",              # body wrapper (used by collapse)
    ]
    missing = [s for s in required_selectors if s not in css_text]
    assert not missing, f"style.css missing selectors: {missing}"


def test_css_resize_handle_has_cursor(css_text):
    assert "row-resize" in css_text
    assert "col-resize" in css_text


# ---------------------------------------------------------------------------
# JS entry points
# ---------------------------------------------------------------------------


def test_js_has_layout_init(js_text):
    # These function names form the Phase 1 public-ish surface. Keep in sync
    # with docs/UI_DESIGN.md.
    for name in (
        "initLayout",
        "initResizers",
        "initCollapseButtons",
        "initShortcuts",
        "applyLayout",
        "loadLayout",
        "saveLayout",
        "resetLayout",
        "togglePanel",
        "toggleFullscreenMap",
    ):
        assert name in js_text, f"app.js missing function `{name}`"


def test_js_localstorage_key_is_versioned(js_text):
    assert 'LAYOUT_KEY = "tw2k:layout:v1"' in js_text, (
        "layout storage key must be versioned so schema bumps don't collide"
    )


def test_js_shortcuts_cover_expected_keys(js_text):
    # These key codes / names must be handled somewhere in the shortcut
    # handler. Grep is enough.
    for frag in ('"Space"', 'Escape', '"f"', '"F"', '"?"', '"R"', "/^[1-9]$/"):
        assert frag in js_text, f"missing shortcut handling for {frag}"


# ---------------------------------------------------------------------------
# Phase 2 contract (map clarity: mini-map, zoom controls, LOD classes)
# ---------------------------------------------------------------------------


PHASE2_REQUIRED_IDS = {"mapControls", "mapZoomReadout", "miniMap", "miniMapSvg"}


def test_phase2_map_elements_present(html_text):
    tags = parse_html(html_text)
    present = ids(tags)
    missing = PHASE2_REQUIRED_IDS - present
    assert not missing, f"index.html missing Phase 2 map element IDs: {sorted(missing)}"


def test_phase2_map_controls_have_actions(html_text):
    tags = parse_html(html_text)
    actions = {
        attrs.get("data-map-action")
        for _, attrs in tags
        if attrs.get("data-map-action")
    }
    expected = {"zoom-in", "zoom-out", "fit", "toggle-mini"}
    missing = expected - actions
    assert not missing, f"missing map-control actions: {sorted(missing)}"


def test_phase2_css_has_lod_and_minimap_rules(css_text):
    required = [
        "#galaxy.zoom-far",
        "#galaxy.zoom-mid",
        "#galaxy.zoom-near",
        ".map-controls",
        ".map-btn",
        ".mini-map",
        ".mini-viewport",
    ]
    missing = [s for s in required if s not in css_text]
    assert not missing, f"style.css missing Phase 2 selectors: {missing}"


def test_phase2_js_has_map_api(js_text):
    for name in (
        "fitGalaxy",
        "zoomBy",
        "buildMiniMap",
        "setMiniMapVisible",
        "initMapControls",
        "updateLODClasses",
        "refreshMiniShips",
    ):
        assert name in js_text, f"app.js missing Phase 2 map helper `{name}`"


def test_phase2_js_zoom_shortcuts(js_text):
    # + / - / 0 / M should be wired as keyboard shortcuts.
    for frag in ('"+"', '"-"', '"0"', '"m"', '"M"'):
        assert frag in js_text, f"missing keybinding for {frag}"


def test_js_players_panel_lookup_matches_html(js_text, html_text):
    """Regression test: the JS must look up the players panel by an ID
    that actually exists in index.html.

    Browser verification (2026-04-17) caught the first pass of Phase 1 wiring
    `playersPanel` in JS while the HTML used `panelPlayers`. This assertion
    would have failed immediately for that mismatch.
    """
    tags = parse_html(html_text)
    html_ids = ids(tags)
    # Pull out the IDs referenced for the players panel in app.js.
    import re
    refs = set(re.findall(r'getElementById\("([^"]+)"\)', js_text))
    player_refs = {r for r in refs if "player" in r.lower() or "panelPlayers" in r}
    # At least one of the IDs the JS looks up for the players panel
    # must actually exist in the HTML.
    assert any(r in html_ids for r in player_refs), (
        f"No players-panel lookup in app.js resolves to an HTML id. "
        f"JS looked up {sorted(player_refs)}; HTML has {sorted(html_ids)}."
    )
