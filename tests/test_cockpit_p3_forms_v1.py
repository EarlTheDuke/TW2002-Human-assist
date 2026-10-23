"""Playtest 3: the trade form keeps the player's side, and an unowned planet is not "Your planet"."""
from __future__ import annotations

from pathlib import Path

import pytest

from tests._cu_host import CuHost, allowed_test_port

ROOT = Path(__file__).resolve().parents[1]
TOK = "p3-forms-token-p2-00000000000000001"


def test_unowned_planet_is_not_yours() -> None:
    js = (ROOT / "web" / "redesign.js").read_text(encoding="utf-8")
    start = js.index("function landLine(p)")
    body = js[start:js.index("\n  }\n", start)]
    assert 'if (!p.owner_id) return "Unclaimed planet.' in body
    assert "p.owner_id === S.self_id) return \"Your planet. \"" in body


def test_reopened_trade_form_keeps_the_chosen_side(tmp_path: Path) -> None:
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    host = CuHost(tmp_path, TOK)
    host.__enter__()
    assert allowed_test_port(host.port)
    from tw2k.engine.models import Commodity

    u = host.runner.state.universe
    u.sectors[u.players["P2"].sector_id].port.stock[Commodity.EQUIPMENT].current = 500
    pw = sync().start()
    browser = pw.chromium.launch()
    try:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
        page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
        page.keyboard.press("Escape")
        page.keyboard.press("p")
        page.wait_for_selector(".frm [data-n=side]", timeout=10_000)
        first = page.locator(".frm [data-n=side]").input_value()
        others = [v for v in page.locator(".frm [data-n=side] option").evaluate_all("os => os.map(o => o.value)") if v != first]
        assert others, "the side picker offers both directions"
        page.locator(".frm [data-n=side]").select_option(others[0])
        chosen = page.locator(".frm [data-n=side]").input_value()
        assert chosen == others[0]
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        page.keyboard.press("p")
        page.wait_for_selector(".frm [data-n=side]", timeout=10_000)
        assert page.locator(".frm [data-n=side]").input_value() == chosen
    finally:
        browser.close()
        pw.stop()
        host.__exit__(None, None, None)
