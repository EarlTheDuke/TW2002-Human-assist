"""cockpit-dashboard-custom-v1. The deck can be rearranged and then put back.

Nothing saved leaves the stylesheet grid alone. A saved layout comes back
after reload, a hidden panel stays hidden, and Reset restores the boxes.
At 390 the stack stays put and only show/hide applies.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._cu_host import CuHost

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "playtests" / "cockpit-dashboard-custom-v1"
TOK = "deck-custom-v1-token-p2-00000000000"
PANELS = ("viewport", "nav", "ship", "context", "term")


def _ready(page, deck: str = "default") -> None:
    page.wait_for_selector("#shipSvg [data-testid=ship-body]", timeout=20_000)
    page.wait_for_function(
        """(deck) => document.body.getAttribute('data-deck') === deck
          && (document.querySelector('#waitchip') || {}).textContent === 'YOUR MOVE'""",
        arg=deck,
        timeout=20_000,
    )


def _boxes(page) -> dict:
    return page.evaluate(
        """() => {
          const out = {};
          ["viewport", "nav", "ship", "context", "term"].forEach((id) => {
            const r = document.getElementById(id).getBoundingClientRect();
            out[id] = [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)];
          });
          const deck = document.getElementById("deck");
          out.cols = deck.style.gridTemplateColumns;
          out.rows = deck.style.gridTemplateRows;
          out.font = getComputedStyle(document.body).fontSize;
          out.zoom = document.body.style.zoom || "1";
          out.areas = getComputedStyle(deck).gridTemplateAreas;
          out.deck = document.body.getAttribute("data-deck");
          return out;
        }"""
    )


def _close(a, b, slack: int = 2) -> None:
    for pid in PANELS:
        for left, right in zip(a[pid], b[pid]):
            assert abs(left - right) <= slack, (pid, a[pid], b[pid])


def _shot(page, name: str) -> None:
    page.evaluate("() => window.scrollTo(0, 0)")
    path = SHOTS / name
    page.screenshot(path=str(path))
    assert path.stat().st_size > 5000, path


def test_dashboard_saves_reloads_and_resets(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    SHOTS.mkdir(parents=True, exist_ok=True)
    with CuHost(tmp_path, TOK, max_days=30, turns_per_day=400) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            legacy = browser.new_page(viewport={"width": 1280, "height": 800})
            legacy.goto(f"{host.base}/bot?seat=P2&token={TOK}")
            legacy.wait_for_selector("[data-testid=ship]", timeout=20_000)
            assert legacy.locator("[data-testid=layout-open]").count() == 0
            assert legacy.locator("[data-testid=layout-menu]").count() == 0
            legacy.close()

            wide = browser.new_page(viewport={"width": 1280, "height": 800})
            phone = browser.new_page(viewport={"width": 390, "height": 844})
            url = f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}"
            wide.goto(url)
            phone.goto(url)
            _ready(wide)
            _ready(phone)
            assert wide.locator("[data-testid=warp-clip]").count() == 1
            assert "Fighters" in wide.locator("#shipStats").inner_text()
            fresh = _boxes(wide)
            assert fresh["cols"] == "" and fresh["rows"] == ""
            assert fresh["font"] == "15px" and fresh["zoom"] == "1"
            assert "view" in fresh["areas"] and "ship" in fresh["areas"]
            assert wide.evaluate("() => window.__tw2kLayout.key()") == "tw2k-deck-v1:lobby:P2"
            phone_font = phone.evaluate("() => getComputedStyle(document.body).fontSize")
            assert phone_font == "12px"
            assert phone.evaluate("() => getComputedStyle(document.getElementById('deck')).display") == "block"
            assert phone.locator(".splitter").first.is_hidden()
            _shot(wide, "1280-default.png")
            _shot(phone, "390-default.png")

            phone.locator("[data-testid=layout-open]").click()
            phone.locator("[data-testid=layout-menu]").wait_for(state="visible")
            assert phone.locator("[data-testid=up-ship]").is_hidden()
            assert phone.locator("[data-testid=down-nav]").is_hidden()
            before_stack = phone.evaluate(
                """() => ["viewport", "nav", "ship", "context", "term"].map((id) => {
                  const r = document.getElementById(id).getBoundingClientRect();
                  return Math.round(r.y);
                })"""
            )
            assert before_stack == sorted(before_stack)
            phone.locator("[data-testid=show-term]").uncheck()
            phone.wait_for_function("() => document.getElementById('term').hidden")
            after_stack = phone.evaluate(
                """() => ["viewport", "nav", "ship", "context"].map((id) => {
                  const r = document.getElementById(id).getBoundingClientRect();
                  return Math.round(r.y);
                })"""
            )
            assert after_stack == sorted(after_stack)
            assert phone.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
            _shot(phone, "390-log-hidden.png")
            phone.reload()
            _ready(phone, "custom")
            assert phone.locator("#term").is_hidden()
            assert phone.locator("#shipSvg [data-testid=ship-body]").count() == 1
            phone.locator("[data-testid=layout-open]").click()
            phone.locator("[data-testid=layout-reset]").click()
            _ready(phone, "default")
            assert phone.locator("#term").is_visible()
            phone.locator("[data-testid=show-viewport]").uncheck()
            phone.wait_for_function("() => document.getElementById('viewport').hidden")
            phone.locator("[data-testid=layout-close]").click()
            assert phone.locator("#viewport").is_hidden()
            assert phone.locator("[data-testid=layout-open]").is_visible()
            phone.locator("[data-testid=layout-open]").click()
            phone.locator("[data-testid=layout-reset]").click()
            _ready(phone, "default")
            assert phone.locator("#viewport").is_visible()

            wide.locator("[data-testid=layout-open]").click()
            wide.locator("[data-testid=up-ship]").click()
            wide.wait_for_function(
                """() => {
                  const ship = document.getElementById("ship").getBoundingClientRect();
                  const nav = document.getElementById("nav").getBoundingClientRect();
                  return ship.x < nav.x;
                }"""
            )
            wide.locator("[data-testid=show-term]").uncheck()
            wide.locator("[data-testid=font-inc]").click()
            wide.locator("[data-testid=font-inc]").click()
            wide.locator("[data-testid=font-inc]").click()
            wide.locator("[data-testid=zoom-inc]").click()
            assert wide.locator("[data-testid=font-readout]").inner_text() == "18px"
            assert wide.locator("[data-testid=zoom-readout]").inner_text() == "110%"
            wide.locator("[data-testid=splitter-col-0]").focus()
            wide.keyboard.press("ArrowLeft")
            wide.wait_for_function("() => window.__tw2kLayout.state().cols")
            touched = wide.evaluate("() => window.__tw2kLayout.state().cols.slice()")
            wide.evaluate(
                """() => {
                  const el = document.querySelector('[data-testid=splitter-col-1]');
                  const r = el.getBoundingClientRect();
                  const down = {bubbles: true, cancelable: true, pointerId: 7, pointerType: 'touch', button: 0, clientX: r.x + 4, clientY: r.y + 40};
                  el.dispatchEvent(new PointerEvent('pointerdown', down));
                  el.dispatchEvent(new PointerEvent('pointermove', Object.assign({}, down, {clientX: r.x + 48, buttons: 1})));
                  el.dispatchEvent(new PointerEvent('pointerup', Object.assign({}, down, {clientX: r.x + 48})));
                }"""
            )
            wide.wait_for_function(
                """(before) => {
                  const cols = window.__tw2kLayout.state().cols;
                  return cols && Math.abs(cols[1] - before[1]) > 0.01;
                }""",
                arg=touched,
            )
            assert wide.locator("#term").is_hidden()
            assert wide.evaluate("() => getComputedStyle(document.getElementById('log')).fontSize") == "18px"
            assert wide.locator("#shipSvg [data-testid=ship-body]").count() == 1
            wide.locator("[data-testid=layout-close]").click()
            wide.locator("[data-testid=layout-menu]").wait_for(state="hidden")
            _shot(wide, "1280-custom.png")
            wide.locator("[data-testid=layout-open]").click()
            wide.locator("[data-testid=layout-menu]").wait_for(state="visible")
            _shot(wide, "1280-layout-menu.png")

            other = browser.new_page(viewport={"width": 1280, "height": 800})
            other.goto(f"{host.base}/bot?layout=redesign&seat=P3&token={TOK}")
            other.wait_for_function("() => document.body.getAttribute('data-deck') === 'default'", timeout=20_000)
            assert other.locator("#term").is_visible()
            assert other.evaluate("() => window.__tw2kLayout.key()") == "tw2k-deck-v1:lobby:P3"
            other.close()

            wide.reload()
            _ready(wide, "custom")
            assert wide.locator("#term").is_hidden()
            assert wide.evaluate(
                """() => {
                  const ship = document.getElementById("ship").getBoundingClientRect();
                  const nav = document.getElementById("nav").getBoundingClientRect();
                  return ship.x < nav.x && document.body.style.zoom === "1.1"
                    && getComputedStyle(document.body).fontSize === "18px";
                }"""
            )
            wide.locator("[data-testid=layout-open]").click()
            wide.locator("[data-testid=layout-reset]").click()
            _ready(wide, "default")
            restored = _boxes(wide)
            _close(fresh, restored)
            assert restored["cols"] == "" and restored["rows"] == ""
            assert restored["font"] == "15px" and restored["zoom"] == "1"
            assert wide.evaluate("() => localStorage.getItem('tw2k-deck-v1:lobby:P2')") is None
            assert wide.locator("#shipSvg [data-testid=ship-body]").count() == 1
            assert wide.locator("#term").is_visible()
            wide.locator("[data-testid=show-viewport]").uncheck()
            wide.wait_for_function("() => document.getElementById('viewport').hidden")
            wide.locator("[data-testid=layout-close]").click()
            assert wide.locator("#viewport").is_hidden()
            opener = wide.locator("[data-testid=layout-open]")
            assert opener.is_visible()
            assert wide.evaluate(
                """() => {
                  const button = document.getElementById('layoutOpen');
                  const header = document.getElementById('cmdline');
                  const manual = document.getElementById('manualLink').getBoundingClientRect();
                  const box = button.getBoundingClientRect();
                  const head = header.getBoundingClientRect();
                  const clear = box.right <= manual.left + 1 || manual.right <= box.left + 1
                    || box.bottom <= manual.top + 1 || manual.bottom <= box.top + 1;
                  return button.closest('#viewport') === null
                    && button.closest('#cmdline') === header
                    && box.width > 20
                    && box.top >= head.top - 1
                    && box.bottom <= head.bottom + 1
                    && clear;
                }"""
            )
            opener.click()
            wide.locator("[data-testid=layout-reset]").click()
            _ready(wide, "default")
            assert wide.locator("#viewport").is_visible()
            assert wide.locator("#term").is_visible()
            _close(fresh, _boxes(wide))
        finally:
            browser.close()
