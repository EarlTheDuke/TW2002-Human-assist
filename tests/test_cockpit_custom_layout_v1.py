"""cockpit-custom-layout-v1. Panels move, hide, and grow the map without a drag.

Font and zoom stay the controls already in the layout menu. The save is this
browser's localStorage. Reset layout puts the stylesheet grid back.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._cu_host import CuHost

ROOT = Path(__file__).resolve().parents[1]
SHOTS = Path("/opt/cursor/artifacts/note113")
TOK = "deck-custom-layout-v1-token-p2-000000"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_pages_decode_as_utf8_and_bot_stays_plain() -> None:
    bot = _text(ROOT / "web" / "bot.html")
    script = _text(ROOT / "web" / "bot.js")
    parity = _text(ROOT / "web" / "bot-parity.js")
    page = _text(ROOT / "web" / "redesign.html")
    layout = _text(ROOT / "web" / "layout.js")
    assert "layout-open" not in bot
    assert "map-larger" not in bot
    assert "panel-menu" not in script
    assert "Larger map" not in parity
    assert "Reset layout" in page
    assert "Larger map" in page
    assert page.count("data-testid=\"font-inc\"") == 1
    assert page.count("data-testid=\"zoom-inc\"") == 1
    assert "setMap" in layout


def _ready(page, deck: str = "default") -> None:
    page.wait_for_selector("#shipSvg [data-testid=ship-body]", timeout=20_000)
    page.wait_for_function(
        """(deck) => document.body.getAttribute('data-deck') === deck
          && (document.querySelector('#waitchip') || {}).textContent === 'YOUR MOVE'""",
        arg=deck,
        timeout=20_000,
    )


def _map(page) -> dict:
    return page.evaluate(
        """() => {
          const rect = document.getElementById("map").getBoundingClientRect();
          const deck = document.getElementById("deck").getBoundingClientRect();
          return {
            w: rect.width, h: rect.height, deckW: deck.width,
            boost: document.body.getAttribute("data-map-boost"),
            sector: document.getElementById("pSector").textContent,
          };
        }"""
    )


def _fits(page) -> None:
    info = page.evaluate(
        """() => {
          const doc = document.documentElement;
          const wide = [];
          document.querySelectorAll("body *").forEach((el) => {
            const r = el.getBoundingClientRect();
            if (r.width > 0 && r.right > doc.clientWidth + 1) wide.push(el.id || el.className || el.tagName);
          });
          return {scroll: doc.scrollWidth, client: doc.clientWidth, wide: wide.slice(0, 12)};
        }"""
    )
    assert info["scroll"] <= info["client"] + 1, info


def _shot(page, name: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.evaluate("() => window.scrollTo(0, 0)")
    path = SHOTS / name
    page.screenshot(path=str(path))
    assert path.stat().st_size > 5000, path


def _labels(page) -> None:
    ok = page.evaluate(
        """() => {
          const need = ["Move up", "Move down", "Hide", "Show"];
          const rows = [...document.querySelectorAll("#layoutList .layout-row")];
          if (rows.length !== 5) return false;
          return rows.every((row) => need.every((label) =>
            [...row.querySelectorAll("button")].some((button) => button.textContent.trim() === label)));
        }"""
    )
    assert ok
    assert page.locator("[data-testid=font-inc]").count() == 1
    assert page.locator("[data-testid=zoom-inc]").count() == 1
    assert page.locator("[data-testid=layout-reset]").inner_text() == "Reset layout"


def test_custom_layout_three_viewports(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK, max_days=30, turns_per_day=400) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            legacy = browser.new_page(viewport={"width": 1280, "height": 720})
            legacy.goto(f"{host.base}/bot?seat=P2&token={TOK}")
            legacy.wait_for_selector("[data-testid=ship]", timeout=20_000)
            assert legacy.locator("[data-testid=layout-open]").count() == 0
            assert legacy.locator("[data-testid=map-larger]").count() == 0
            assert legacy.locator(".panel-menu-open").count() == 0
            legacy.close()

            url = f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}"
            wide = browser.new_context(viewport={"width": 1280, "height": 720}).new_page()
            wide.goto(url)
            _ready(wide)
            fresh = _map(wide)
            assert fresh["boost"] == "0"
            assert wide.evaluate("() => getComputedStyle(document.body).fontSize") == "15px"
            assert wide.evaluate("() => document.body.style.zoom || '1'") == "1"
            assert "Command" in wide.locator("[data-testid=prompt-line]").inner_text()
            assert len(wide.locator("[data-testid=command-keys]").inner_text()) > 10
            _fits(wide)
            _shot(wide, "1280x720-default.png")

            wide.locator("[data-testid=layout-open]").click()
            wide.locator("[data-testid=layout-menu]").wait_for(state="visible")
            _labels(wide)
            sector = fresh["sector"]
            wide.locator("[data-testid=up-ship]").focus()
            wide.keyboard.press("Enter")
            wide.wait_for_function(
                """() => {
                  const ship = document.getElementById("ship").getBoundingClientRect();
                  const nav = document.getElementById("nav").getBoundingClientRect();
                  return ship.x < nav.x;
                }"""
            )
            assert wide.locator("#pSector").inner_text() == sector
            wide.locator("[data-testid=hide-term]").click()
            wide.wait_for_function("() => document.getElementById('term').hidden")
            wide.locator("[data-testid=font-inc]").click()
            wide.locator("[data-testid=zoom-inc]").click()
            wide.locator("[data-testid=map-larger]").click()
            wide.locator("[data-testid=map-larger]").click()
            wide.wait_for_function(
                """(before) => {
                  const rect = document.getElementById("map").getBoundingClientRect();
                  return rect.width > before + 100 && document.body.getAttribute("data-map-boost") === "2";
                }""",
                arg=fresh["w"],
            )
            assert wide.locator("[data-testid=map-size]").inner_text() == "Larger"
            assert wide.locator("[data-testid=font-readout]").inner_text() == "16px"
            assert wide.locator("[data-testid=zoom-readout]").inner_text() == "110%"
            wide.locator("[data-testid=layout-close]").click()
            _fits(wide)
            _shot(wide, "1280x720-custom.png")
            grown = _map(wide)
            wide.reload()
            _ready(wide, "custom")
            again = _map(wide)
            assert wide.locator("#term").is_hidden()
            assert again["w"] > fresh["w"] + 100
            assert abs(again["w"] - grown["w"]) < 40
            assert again["boost"] == "2"
            assert wide.evaluate(
                """() => document.body.style.zoom === "1.1"
                  && getComputedStyle(document.body).fontSize === "16px"
                  && document.getElementById("ship").getBoundingClientRect().x
                    < document.getElementById("nav").getBoundingClientRect().x"""
            )
            assert "Command" in wide.locator("[data-testid=prompt-line]").inner_text()
            wide.locator("[data-testid=layout-open]").click()
            wide.locator("[data-testid=show-panel-term]").click()
            wide.wait_for_function("() => !document.getElementById('term').hidden")
            wide.locator("[data-testid=layout-reset]").click()
            _ready(wide, "default")
            restored = _map(wide)
            assert restored["boost"] == "0"
            assert abs(restored["w"] - fresh["w"]) < 16
            assert abs(restored["h"] - fresh["h"]) < 16
            assert wide.locator("#term").is_visible()
            assert wide.evaluate("() => localStorage.getItem('tw2k-deck-v1:lobby:P2')") is None
            assert wide.evaluate("() => getComputedStyle(document.body).fontSize") == "15px"
            assert wide.evaluate("() => document.body.style.zoom || '1'") == "1"
            _shot(wide, "1280x720-reset.png")
            wide.context.close()

            big = browser.new_context(viewport={"width": 1600, "height": 1000}).new_page()
            big.goto(url)
            _ready(big)
            base = _map(big)
            big.locator("[data-testid=panel-menu-nav]").click()
            pop = big.locator("[data-testid=panel-menu-pop-nav]")
            pop.wait_for(state="visible")
            assert pop.locator("[data-cmd=up]").inner_text() == "Move up"
            assert pop.locator("[data-cmd=hide]").inner_text() == "Hide"
            assert pop.locator("[data-cmd=show]").inner_text() == "Show"
            for _ in range(3):
                pop.locator("[data-cmd=larger]").click()
            big.wait_for_function(
                """() => {
                  const map = document.getElementById("map").getBoundingClientRect();
                  const deck = document.getElementById("deck").getBoundingClientRect();
                  return document.body.getAttribute("data-map-boost") === "3" && map.width > deck.width * 0.5;
                }"""
            )
            big.keyboard.press("Escape")
            pop.wait_for(state="hidden")
            _fits(big)
            _shot(big, "1600x1000-large-map.png")
            big.reload()
            _ready(big, "custom")
            assert _map(big)["boost"] == "3"
            assert _map(big)["w"] > base["w"] + 150
            big.locator("[data-testid=layout-open]").click()
            big.locator("[data-testid=layout-reset]").click()
            _ready(big, "default")
            back = _map(big)
            assert back["boost"] == "0"
            assert abs(back["w"] - base["w"]) < 16
            _shot(big, "1600x1000-reset.png")
            big.context.close()

            phone = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
            phone.goto(url)
            _ready(phone)
            phone_fresh = _map(phone)
            assert phone.evaluate("() => getComputedStyle(document.getElementById('deck')).display") == "block"
            phone.locator("[data-testid=layout-open]").click()
            phone.locator("[data-testid=layout-menu]").wait_for(state="visible")
            _labels(phone)
            assert phone.locator("[data-testid=up-ship]").is_hidden()
            assert phone.locator("[data-testid=hide-term]").is_visible()
            assert phone.locator("[data-testid=show-panel-term]").is_visible()
            phone.locator("[data-testid=layout-close]").click()
            phone.locator("[data-testid=panel-menu-ship]").click()
            ship_pop = phone.locator("[data-testid=panel-menu-pop-ship]")
            ship_pop.wait_for(state="visible")
            assert ship_pop.locator("[data-cmd=up]").is_disabled()
            assert ship_pop.locator("[data-cmd=down]").inner_text() == "Move down"
            phone.locator("[data-testid=layout-open]").click()
            phone.locator("[data-testid=hide-term]").click()
            phone.wait_for_function("() => document.getElementById('term').hidden")
            phone.locator("[data-testid=map-larger]").click()
            phone.locator("[data-testid=map-larger]").click()
            phone.wait_for_function(
                """(before) => document.getElementById("map").getBoundingClientRect().height > before + 80""",
                arg=phone_fresh["h"],
            )
            phone.locator("[data-testid=layout-close]").click()
            _fits(phone)
            _shot(phone, "390x844-custom.png")
            phone.reload()
            _ready(phone, "custom")
            assert phone.locator("#term").is_hidden()
            assert _map(phone)["h"] > phone_fresh["h"] + 80
            assert _map(phone)["boost"] == "2"
            phone.locator("[data-testid=layout-open]").click()
            phone.locator("[data-testid=layout-reset]").click()
            _ready(phone, "default")
            phone_back = _map(phone)
            assert phone.locator("#term").is_visible()
            assert phone_back["boost"] == "0"
            assert abs(phone_back["h"] - phone_fresh["h"]) < 24
            phone.locator("[data-testid=show-sectorReport]").uncheck()
            phone.wait_for_function("() => document.getElementById('sectorReport').hidden")
            phone.locator("[data-testid=layout-close]").click()
            assert phone.locator("[data-testid=layout-open]").is_visible()
            _fits(phone)
            phone.context.close()
        finally:
            browser.close()
