"""Phase H6.4 UI smoke tests — economy dashboard panel.

Static asserts keeping the cockpit HTML/CSS/JS honest without a
headless browser. Every H6.4 UI deliverable has a test here:

* ``<details class="economy-panel">`` section with top-routes list +
  mini heatmap table.
* CSS classes ``eco-cell``, ``eco-sell``, ``eco-buy`` for heatmap
  color coding.
* JS helpers ``refreshEconomy`` + ``renderEconomy`` wired from
  ``refreshObservation`` so the panel stays in sync with sector moves.
* Debug hook ``window.__tw2kEconomy`` exposed for Playwright / manual
  console.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"


@pytest.fixture(scope="module")
def play_html() -> str:
    return (WEB / "play.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def play_css() -> str:
    return (WEB / "play.css").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def play_js() -> str:
    return (WEB / "play.js").read_text(encoding="utf-8")


# Markup -------------------------------------------------------------------


def test_economy_panel_present(play_html: str) -> None:
    assert 'id="economyPanel"' in play_html
    assert 'class="economy-panel"' in play_html


def test_economy_routes_list_present(play_html: str) -> None:
    assert 'id="economyRoutes"' in play_html
    assert 'class="economy-routes"' in play_html


def test_economy_heatmap_present(play_html: str) -> None:
    assert 'id="economyHeatmap"' in play_html
    assert 'id="economyHeatmapBody"' in play_html
    # Header row advertises the three tradable commodities.
    for label in ("Fuel", "Org.", "Equip."):
        assert label in play_html


# CSS ----------------------------------------------------------------------


def test_economy_css_classes_present(play_css: str) -> None:
    for cls in (
        ".economy-panel",
        ".economy-routes",
        ".economy-heatmap",
        ".eco-cell",
        ".eco-sell",
        ".eco-buy",
    ):
        assert cls in play_css, f"missing CSS class {cls}"


# JS -----------------------------------------------------------------------


def test_economy_js_helpers_present(play_js: str) -> None:
    for sym in ("refreshEconomy", "renderEconomy", "__tw2kEconomy"):
        assert sym in play_js, f"missing JS symbol {sym}"


def test_economy_refresh_wired_into_observation_refresh(play_js: str) -> None:
    """`refreshObservation` must call `refreshEconomy()` so the panel
    auto-updates on warp / scan / trade."""
    # Grab the body of refreshObservation by searching for the call.
    # Anchoring on the substring is enough for a smoke test.
    idx = play_js.find("async function refreshObservation")
    assert idx >= 0
    body = play_js[idx:idx + 4000]
    assert "refreshEconomy()" in body


def test_economy_endpoints_referenced(play_js: str) -> None:
    assert "/api/economy/prices" in play_js
    assert "/api/economy/routes" in play_js


def test_economy_route_click_plots_course(play_js: str) -> None:
    """Clicking a route row should route through `openActionForm('plot_course', ...)`."""
    assert "openActionForm(\"plot_course\"" in play_js or "openActionForm('plot_course'" in play_js
