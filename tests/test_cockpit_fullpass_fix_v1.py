"""Bank, trade price, refusals, computer, keys, haggle, forms, gear, scan, wait, and the 1366 bar."""

from __future__ import annotations

from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tests._cu_host import CuHost

PORT_TOK = "fullpass-port-token-p2-000000000000"
DOCK_TOK = "fullpass-dock-token-p2-000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-fullpass-fix-v1"


def _page(pw, host, token, width=1440, height=900):
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": width, "height": height})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={token}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    return browser, page


def _quiet(page) -> None:
    page.keyboard.press("Escape")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)


@pytest.fixture(scope="module")
def seats(tmp_path_factory):
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    old = K.HAGGLE_LIVE_MODE
    K.HAGGLE_LIVE_MODE = "live"
    pw = sync().start()
    port_host = CuHost(tmp_path_factory.mktemp("fullpass-port"), PORT_TOK)
    port_host.__enter__()
    dock_host = CuHost(tmp_path_factory.mktemp("fullpass-dock"), DOCK_TOK, park_at=1)
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
        K.HAGGLE_LIVE_MODE = old


def test_trade_form_prefills_the_listed_price(seats) -> None:
    port = seats["port"]
    _quiet(port)
    port.keyboard.press("p")
    port.wait_for_selector(".frm [data-n=unit_price]", timeout=10_000)
    price = port.locator(".frm [data-n=unit_price]").input_value()
    assert price.isdigit() and int(price) > 0
    focused = port.evaluate("() => document.activeElement && document.activeElement.dataset.n")
    assert focused
    SHOTS.mkdir(parents=True, exist_ok=True)
    port.screenshot(path=str(SHOTS / "1440-trade.png"))


def test_blank_price_trades_at_the_list(seats) -> None:
    port = seats["port"]
    _quiet(port)
    port.keyboard.press("p")
    port.wait_for_selector(".frm [data-n=unit_price]", timeout=10_000)
    port.locator(".frm [data-n=side]").select_option("sell")
    port.locator(".frm [data-n=commodity]").select_option("fuel_ore")
    port.locator(".frm [data-n=qty]").fill("1")
    port.locator(".frm [data-n=unit_price]").fill("")
    port.keyboard.press("Enter")
    port.wait_for_function("() => /^ok —/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)
    assert "patience" not in port.locator("#lastResult").inner_text().lower()


def test_haggle_shows_the_counter_and_keeps_the_form(seats) -> None:
    port = seats["port"]
    _quiet(port)
    port.keyboard.press("p")
    port.wait_for_selector(".frm [data-n=unit_price]", timeout=10_000)
    port.locator(".frm [data-n=side]").select_option("sell")
    port.locator(".frm [data-n=commodity]").select_option("fuel_ore")
    listed = int(port.locator(".frm [data-n=unit_price]").input_value())
    offer = max(listed + 1, (listed * 108) // 100)
    if offer * 100 > listed * 112:
        offer = (listed * 112) // 100
    port.locator(".frm [data-n=qty]").fill("1")
    port.locator(".frm [data-n=unit_price]").fill(str(offer))
    port.locator(".frm button.verb", has_text="CONFIRM").click()
    if offer > listed:
        port.wait_for_function("() => /counters at/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)
    else:
        port.wait_for_function("() => /^FAILED/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)
    text = port.locator("#lastResult").inner_text()
    assert not text.startswith("ok")
    assert port.locator(".frm [data-n=unit_price]").input_value().isdigit()


def test_scan_offers_density_and_holo(seats) -> None:
    port = seats["port"]
    _quiet(port)
    port.keyboard.press("s")
    port.wait_for_selector(".frm [data-n=tier]", timeout=10_000)
    labels = port.locator(".frm [data-n=tier]").inner_text()
    assert "density" in labels and "holo" in labels
    port.locator(".frm [data-n=tier]").select_option("holo")
    port.locator(".frm button.verb", has_text="CONFIRM").click()
    port.wait_for_function("() => /HoloScan|holo/i.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)
    assert port.locator("#lastResult").inner_text().startswith("ok")


def test_wait_writes_its_own_line(seats) -> None:
    port = seats["port"]
    _quiet(port)
    port.keyboard.press(".")
    port.wait_for_function("() => /^You wait/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)
    assert "Turns spent" in port.locator("#lastResult").inner_text()


def test_help_lists_the_space_keys(seats) -> None:
    port = seats["port"]
    _quiet(port)
    port.locator("#keys button[data-key='?']").click()
    port.wait_for_selector("#menu", timeout=10_000)
    text = port.locator("#menu").inner_text()
    for label in ("Game Status", "Show Deployed Fighters", "Self Destruct", "Jettison Cargo", "Quit"):
        assert label in text
    SHOTS.mkdir(parents=True, exist_ok=True)
    port.screenshot(path=str(SHOTS / "1440-help.png"))


def test_status_fighters_and_plain_refusals(seats) -> None:
    port = seats["port"]
    _quiet(port)
    port.keyboard.press("v")
    port.wait_for_selector("#menu[data-screen='Game Status']", timeout=10_000)
    assert "Day" in port.locator("#menu").inner_text()
    port.keyboard.press("Escape")
    port.keyboard.press("g")
    port.wait_for_selector("#menu[data-screen='Deployed Fighters']", timeout=10_000)
    assert "ship" in port.locator("#menu").inner_text().lower()
    port.keyboard.press("Escape")
    port.keyboard.press("b")
    port.locator("#dangerOk").click()
    port.wait_for_function("() => /not in this game/.test(document.querySelector('#lastResult').textContent || '')", timeout=10_000)
    assert not port.locator("#lastResult").inner_text().startswith("ok")
    port.keyboard.press("j")
    assert "Jettison" in port.locator("#menu").inner_text()
    port.keyboard.press("Escape")
    port.keyboard.press("q")
    assert "Quit" in port.locator("#menu").inner_text()


def test_computer_report_universe_and_an_unknown_key(seats) -> None:
    port = seats["port"]
    _quiet(port)
    port.keyboard.press("c")
    port.keyboard.press("r")
    port.wait_for_selector("#menu[data-screen='Port Report']", timeout=10_000)
    report = port.locator("#menu").inner_text()
    assert "cr" in report
    SHOTS.mkdir(parents=True, exist_ok=True)
    port.screenshot(path=str(SHOTS / "1440-report.png"))
    port.keyboard.press("Escape")
    port.keyboard.press("c")
    port.keyboard.press("k")
    port.wait_for_selector("#menu[data-screen='Known Universe']", timeout=10_000)
    assert "warps" in port.locator("#menu").inner_text()
    port.keyboard.press("Escape")
    port.keyboard.press("c")
    port.keyboard.press("i")
    port.wait_for_function("() => /not a computer command/.test(document.querySelector('#lastResult').textContent || '')", timeout=10_000)


def test_top_bar_is_one_row_at_1366(seats) -> None:
    port = seats["port"]
    port.set_viewport_size({"width": 1366, "height": 768})
    port.wait_for_timeout(200)
    same = port.evaluate(
        """() => {
          const mid = (id) => { const r = document.querySelector(id).getBoundingClientRect(); return r.top + r.height / 2; };
          return Math.abs(mid('#cmdline .prompt') - mid('#waitchip')) < 8
            && Math.abs(mid('#cmdline .prompt') - mid('#align')) < 8;
        }"""
    )
    assert same
    SHOTS.mkdir(parents=True, exist_ok=True)
    port.screenshot(path=str(SHOTS / "1366-trade.png"))
    port.set_viewport_size({"width": 1440, "height": 900})


def test_port_screens_at_each_width(seats) -> None:
    port = seats["port"]
    SHOTS.mkdir(parents=True, exist_ok=True)
    for width, height, name in ((1920, 1080, "1920"), (1440, 900, "1440"), (1366, 768, "1366"), (390, 844, "390")):
        port.set_viewport_size({"width": width, "height": height})
        _quiet(port)
        port.keyboard.press("p")
        port.wait_for_selector(".frm [data-n=unit_price]", timeout=10_000)
        port.screenshot(path=str(SHOTS / f"{name}-trade.png"))
        port.keyboard.press("Escape")
        port.keyboard.press("c")
        port.keyboard.press("r")
        port.wait_for_selector("#menu[data-screen='Port Report']", timeout=10_000)
        port.screenshot(path=str(SHOTS / f"{name}-report.png"))
        port.keyboard.press("Escape")
        port.locator("#keys button[data-key='?']").click()
        port.wait_for_selector("#menu", timeout=10_000)
        port.screenshot(path=str(SHOTS / f"{name}-help.png"))
        port.keyboard.press("Escape")
    port.set_viewport_size({"width": 1440, "height": 900})


def test_bank_has_an_amount_and_withdraw(seats) -> None:
    dock = seats["dock"]
    _quiet(dock)
    dock.get_by_role("button", name="Bank").click()
    dock.wait_for_selector(".frm[data-screen=bank] [data-n=amount]", timeout=10_000)
    text = dock.locator(".frm").inner_text()
    assert "Balance" in text and "Room" in text
    assert "Withdraw" in dock.locator(".frm [data-n=side]").inner_text()
    amount = dock.locator(".frm [data-n=amount]").input_value()
    assert amount.isdigit() and int(amount) > 0
    focused = dock.evaluate("() => document.activeElement && document.activeElement.dataset.n")
    assert focused == "amount"
    SHOTS.mkdir(parents=True, exist_ok=True)
    dock.screenshot(path=str(SHOTS / "1440-bank.png"))
    dock.locator(".frm [data-n=amount]").fill("100")
    dock.keyboard.press("Enter")
    dock.wait_for_function("() => /^ok —/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)


def test_gear_shows_the_price_and_a_blank_qty_asks(seats) -> None:
    dock = seats["dock"]
    _quiet(dock)
    dock.get_by_role("button", name="StarDock: buy gear").click()
    dock.wait_for_selector("[data-gear=price]", timeout=10_000)
    assert "cr each" in dock.locator("[data-gear=price]").inner_text()
    dock.locator(".frm [data-n=qty]").fill("")
    dock.locator(".frm button.verb", has_text="CONFIRM").click()
    dock.wait_for_function("() => /How many/.test(document.querySelector('#lastResult').textContent || '')", timeout=10_000)
    dock.locator(".frm [data-n=item]").select_option("fighters")
    dock.locator(".frm [data-n=qty]").fill("9999999")
    dock.locator(".frm button.verb", has_text="CONFIRM").click()
    dock.wait_for_function("() => /^REFUSED/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)
    text = dock.locator("#lastResult").inner_text()
    assert "not enough credits" in text
    assert "fighters" in text
    assert "," in text
    assert "<" not in text
    assert not text.startswith("ok")


def test_photon_refusal_is_plain(seats) -> None:
    dock = seats["dock"]
    _quiet(dock)
    dock.keyboard.press("c")
    dock.keyboard.press("p")
    dock.wait_for_function("() => /photon/i.test(document.querySelector('#lastResult').textContent || '')", timeout=10_000)
    text = dock.locator("#lastResult").inner_text()
    assert "buy gear" not in text.lower()
    assert "No photon missiles" in text


def test_bank_screen_at_each_width(seats) -> None:
    dock = seats["dock"]
    SHOTS.mkdir(parents=True, exist_ok=True)
    for width, height, name in ((1920, 1080, "1920"), (1366, 768, "1366"), (390, 844, "390")):
        dock.set_viewport_size({"width": width, "height": height})
        _quiet(dock)
        dock.get_by_role("button", name="Bank").click()
        dock.wait_for_selector(".frm[data-screen=bank]", timeout=10_000)
        dock.screenshot(path=str(SHOTS / f"{name}-bank.png"))
        dock.keyboard.press("Escape")
    dock.set_viewport_size({"width": 1440, "height": 900})
