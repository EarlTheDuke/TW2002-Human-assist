"""Playtest 3 leftovers (d): the Computer (C) menu must be readable over the enlarged map."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

CSS = Path(__file__).resolve().parents[1] / "web" / "redesign.css"
TOK = "p3dtok"


def _z(selector: str) -> int:
    css = CSS.read_text(encoding="utf-8")
    m = re.search(re.escape(selector) + r"\{[^}]*z-index:(\d+)", css)
    assert m, selector
    return int(m.group(1))


def test_menu_sits_above_the_enlarged_map_and_panel_menus():
    menu = _z("#menu")
    assert menu > _z("#nav.enlarged")
    assert menu > _z("#layoutMenu")
    assert menu > _z(".panel-menu")
    assert menu < _z("#err")


def test_computer_menu_is_on_top_with_the_map_enlarged(tmp_path, monkeypatch):
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    from tests._cu_host import CuHost

    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    with CuHost(tmp_path, TOK, park_at=1, fuel=0) as host, sync() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
            page.wait_for_selector("#keys button[data-key=C]", timeout=20_000)
            page.wait_for_selector("#mapEnlarge", timeout=20_000)
            page.locator("#mapEnlarge").click()
            page.wait_for_selector("#nav.enlarged", timeout=10_000)
            page.keyboard.press("C")
            page.wait_for_selector("#menu[data-screen=computer]", timeout=10_000)
            on_top = page.evaluate(
                "() => { const m = document.getElementById('menu'); const r = m.getBoundingClientRect();"
                " const t = document.elementFromPoint(r.left + r.width / 2, r.top + 30); return m.contains(t); }"
            )
            assert on_top
            assert "Port Report" in page.locator("#menu").inner_text()
        finally:
            browser.close()
