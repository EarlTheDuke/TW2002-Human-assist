"""F leaves or takes fighters, and mine counts stay on the ship panel."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._cu_host import CuHost

pytestmark = pytest.mark.legacy_profile

PORT_TOK = "fighters-port-token-p2-000000000000"
DOCK_TOK = "fighters-dock-token-p2-000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-fighters-mines-v1"
WIDTHS = ((1920, 1080, "1920"), (1366, 768, "1366"), (390, 844, "390"))


def _page(pw, host, token):
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={token}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    return browser, page


def _quiet(page) -> None:
    page.keyboard.press("Escape")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)


def _shoot(page, stem: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    for width, height, name in WIDTHS:
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(150)
        page.evaluate(
            """() => {
              const el = document.querySelector('.frm') || document.querySelector('#shipStats') || document.querySelector('#ship');
              if (el) el.scrollIntoView({ block: 'center' });
            }"""
        )
        page.screenshot(path=str(SHOTS / f"{name}-{stem}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


@pytest.fixture(scope="module")
def seats(tmp_path_factory):
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    pw = sync().start()
    port_host = CuHost(tmp_path_factory.mktemp("fighters-port"), PORT_TOK)
    port_host.__enter__()
    dock_host = CuHost(tmp_path_factory.mktemp("fighters-dock"), DOCK_TOK, park_at=1)
    dock_host.__enter__()
    port_browser, port_page = _page(pw, port_host, PORT_TOK)
    dock_browser, dock_page = _page(pw, dock_host, DOCK_TOK)
    try:
        yield {"port": port_page, "dock": dock_page}
    finally:
        port_browser.close()
        dock_browser.close()
        port_host.__exit__(None, None, None)
        dock_host.__exit__(None, None, None)
        pw.stop()


def test_ship_panel_shows_zero_mines_and_f_leaves_then_takes(seats) -> None:
    port = seats["port"]
    _quiet(port)
    assert port.locator("[data-mines=armid]").inner_text().endswith("0")
    assert port.locator("[data-mines=limpet]").inner_text().endswith("0")
    _shoot(port, "mines0")
    port.keyboard.press("f")
    port.wait_for_selector(".frm[data-screen=fighters] [data-n=leave]", timeout=10_000)
    form = port.locator(".frm[data-screen=fighters]").inner_text()
    assert "yours" in form and "On board" in form and "holds up to" in form
    modes = port.locator(".frm [data-n=mode]").inner_text()
    assert "defensive" in modes and "offensive" in modes and "toll" in modes
    aboard = int(port.locator(".frm [data-n=leave]").input_value() or "0")
    port.locator(".frm [data-n=leave]").fill(str(aboard + 5))
    port.locator(".frm [data-n=mode]").select_option("offensive")
    _shoot(port, "fighters")
    port.keyboard.press("Enter")
    port.wait_for_function("() => /^ok —/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)
    assert "offensive" in port.locator("#lastResult").inner_text().lower()
    _quiet(port)
    port.keyboard.press("f")
    port.wait_for_selector(".frm [data-n=leave]", timeout=10_000)
    assert port.locator(".frm [data-n=leave]").input_value() == "5"
    port.locator(".frm [data-n=leave]").fill("0")
    port.keyboard.press("Enter")
    port.wait_for_function("() => /^ok —/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)
    _shoot(port, "recalled")
    _quiet(port)
    port.keyboard.press("f")
    port.wait_for_selector(".frm [data-n=leave]", timeout=10_000)
    assert port.locator(".frm [data-n=leave]").input_value() == "0"
    assert "holds up to" in port.locator(".frm").inner_text()
    port.keyboard.press("Escape")


def test_bought_mines_show_on_the_panel_and_the_h_form(seats) -> None:
    dock = seats["dock"]
    _quiet(dock)
    assert dock.locator("[data-mines=armid]").inner_text().endswith("0")
    dock.get_by_role("button", name="StarDock: buy gear").click()
    dock.wait_for_selector(".frm [data-n=item]", timeout=10_000)
    dock.locator(".frm [data-n=item]").select_option("armid_mines")
    dock.locator(".frm [data-n=qty]").fill("4")
    dock.keyboard.press("Enter")
    dock.wait_for_function("() => /^ok —/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)
    dock.wait_for_function("() => document.querySelector('[data-mines=armid]').textContent.trim().endsWith('4')", timeout=10_000)
    assert dock.locator("[data-mines=limpet]").inner_text().endswith("0")
    dock.keyboard.press("h")
    dock.wait_for_selector(".frm[data-screen=mines] [data-mines=form]", timeout=10_000)
    text = dock.locator("[data-mines=form]").inner_text()
    assert "On board: armid 4" in text
    assert "limpet 0" in text
    assert "In this sector" in text
    _shoot(dock, "mines")
    dock.keyboard.press("Escape")
