"""Bank form stays open, haggle keeps the offer, and the leftover cockpit wording."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tests._cu_host import CuHost

PORT_TOK = "fix2-port-token-p2-000000000000"
DOCK_TOK = "fix2-dock-token-p2-000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-fullpass-fix2-v1"
WIDTHS = ((1920, 1080, "1920"), (1440, 900, "1440"), (1366, 768, "1366"), (390, 844, "390"))


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


def _shoot(page, stem: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    for width, height, name in WIDTHS:
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(150)
        page.evaluate(
            """() => {
              const el = document.querySelector('#menu:not([hidden])')
                || document.querySelector('.frm')
                || document.querySelector('.porttbl')
                || document.querySelector('#here');
              if (el) el.scrollIntoView({ block: 'center' });
            }"""
        )
        page.screenshot(path=str(SHOTS / f"{name}-{stem}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


def _sector(page) -> str:
    return page.evaluate(
        """() => {
          const m = (document.querySelector('#sectorText').innerText || '').match(/Sector\\s*:?\\s*(\\d+)/);
          return m ? m[1] : '';
        }"""
    )


@pytest.fixture(scope="module")
def seats(tmp_path_factory):
    _prior_haggle_live_mode = K.HAGGLE_LIVE_MODE
    try:
        sync = pytest.importorskip("playwright.sync_api").sync_playwright
        old = K.HAGGLE_LIVE_MODE
        K.HAGGLE_LIVE_MODE = "live"
        pw = sync().start()
        port_host = CuHost(tmp_path_factory.mktemp("fix2-port"), PORT_TOK)
        port_host.__enter__()
        dock_host = CuHost(tmp_path_factory.mktemp("fix2-dock"), DOCK_TOK, park_at=1)
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
    finally:
        K.HAGGLE_LIVE_MODE = _prior_haggle_live_mode


def test_haggle_launcher_stays_legacy_until_asked(monkeypatch) -> None:
    _prior_haggle_live_mode = K.HAGGLE_LIVE_MODE
    try:
        from tw2k.server.app import _apply_haggle_live

        monkeypatch.delenv("TW2K_HAGGLE_LIVE", raising=False)
        old = K.HAGGLE_LIVE_MODE
        try:
            K.HAGGLE_LIVE_MODE = "legacy"
            _apply_haggle_live()
            assert K.HAGGLE_LIVE_MODE == "legacy"
            monkeypatch.setenv("TW2K_HAGGLE_LIVE", "live")
            _apply_haggle_live()
            assert K.HAGGLE_LIVE_MODE == "live"
            monkeypatch.setenv("TW2K_HAGGLE_LIVE", "nope")
            K.HAGGLE_LIVE_MODE = "legacy"
            _apply_haggle_live()
            assert K.HAGGLE_LIVE_MODE == "legacy"
        finally:
            K.HAGGLE_LIVE_MODE = old
            monkeypatch.delenv("TW2K_HAGGLE_LIVE", raising=False)
    finally:
        K.HAGGLE_LIVE_MODE = _prior_haggle_live_mode


def test_trading_column_shows_units_wanted(seats) -> None:
    port = seats["port"]
    _quiet(port)
    rows = port.evaluate(
        """() => [...document.querySelectorAll('.porttbl tr')].slice(1).map((tr) => ({
          status: tr.children[1].textContent,
          trading: tr.children[2].textContent.replace(/,/g, '')
        }))"""
    )
    buying = [row for row in rows if row["status"].startswith("Buying")]
    assert buying, rows
    for row in buying:
        room = row["status"].split("room ")[1].replace(",", "")
        assert row["trading"] == room
    _shoot(port, "port")


def test_focus_lands_on_the_first_number(seats) -> None:
    port = seats["port"]
    _quiet(port)
    port.keyboard.press("p")
    port.wait_for_selector(".frm [data-n=qty]", timeout=10_000)
    assert port.evaluate("() => document.activeElement && document.activeElement.dataset.n") == "qty"
    port.keyboard.press("Escape")


def test_waiting_row_says_waiting(seats) -> None:
    port = seats["port"]
    _quiet(port)
    port.evaluate("() => window.__tw2kTest.setAwaiting(false)")
    assert "Waiting for your turn." in port.locator(".porttbl").inner_text()
    port.evaluate("() => window.__tw2kTest.setAwaiting(true)")
    assert "Waiting for your turn." not in port.locator(".porttbl").inner_text()


def test_haggle_retry_keeps_side_commodity_and_qty(seats) -> None:
    port = seats["port"]
    _quiet(port)
    port.keyboard.press("p")
    port.wait_for_selector(".frm [data-n=unit_price]", timeout=10_000)
    port.locator(".frm [data-n=side]").select_option("sell")
    port.locator(".frm [data-n=commodity]").select_option("fuel_ore")
    port.locator(".frm [data-n=qty]").fill("10")
    port.locator(".frm [data-n=unit_price]").fill("999")
    assert "list" in port.locator("[data-list=price]").inner_text()
    port.keyboard.press("Enter")
    port.wait_for_function(
        "() => /FAILED|REFUSED|counters at/.test(document.querySelector('#lastResult').textContent || '')",
        timeout=20_000,
    )
    text = port.locator("#lastResult").inner_text()
    assert "Commander" not in text
    assert "Quantity must be positive" not in text
    assert port.locator(".frm [data-n=side]").input_value() == "sell"
    assert port.locator(".frm [data-n=commodity]").input_value() == "fuel_ore"
    assert port.locator(".frm [data-n=qty]").input_value() == "10"
    assert port.locator(".frm [data-n=unit_price]").input_value().isdigit()
    _shoot(port, "haggle")
    port.keyboard.press("Escape")


def test_wording_drops_the_seat_name_and_fixes_plurals(seats) -> None:
    dock = seats["dock"]
    _quiet(dock)
    dock.get_by_role("button", name="StarDock: buy gear").click()
    dock.wait_for_selector(".frm [data-n=item]", timeout=10_000)
    dock.locator(".frm [data-n=item]").select_option("marker_beacon")
    dock.locator(".frm [data-n=qty]").fill("3")
    dock.keyboard.press("Enter")
    dock.wait_for_function("() => /^ok —/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)
    beacons = dock.locator("#lastResult").inner_text()
    assert "Commander" not in beacons
    assert "marker beacons" in beacons
    _quiet(dock)
    dock.evaluate("() => { document.querySelector('#lastResult').textContent = ''; }")
    dock.get_by_role("button", name="StarDock: buy gear").click()
    dock.locator(".frm [data-n=item]").select_option("fighters")
    dock.locator(".frm [data-n=qty]").fill("10")
    dock.keyboard.press("Enter")
    dock.wait_for_function("() => /fighters/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)
    fighters = dock.locator("#lastResult").inner_text()
    assert "Commander" not in fighters
    assert re.search(r"\d,\d{3} cr", fighters)
    dock.keyboard.press("u")
    dock.wait_for_function("() => (document.querySelector('#lastResult').textContent || '').length > 0", timeout=10_000)
    genesis = dock.locator("#lastResult").inner_text()
    assert "Commander" not in genesis
    assert "buy gear" not in genesis.lower()
    assert "torpedo" in genesis.lower() or "stardock" in genesis.lower()


def test_bank_form_survives_refresh_then_deposit_and_withdraw(seats) -> None:
    dock = seats["dock"]
    _quiet(dock)
    dock.get_by_role("button", name="Bank").click()
    dock.wait_for_selector(".frm[data-screen=bank] [data-n=amount]", timeout=10_000)
    amount = dock.locator(".frm [data-n=amount]").input_value()
    assert amount.isdigit() and int(amount) > 0
    assert "Balance" in dock.locator(".frm").inner_text()
    dock.wait_for_timeout(6_500)
    assert dock.locator(".frm[data-screen=bank]").count() == 1
    assert dock.locator(".frm [data-n=amount]").input_value() == amount
    assert "Balance" in dock.locator(".frm").inner_text()
    _shoot(dock, "bank")
    dock.locator(".frm [data-n=amount]").fill("100")
    dock.keyboard.press("Enter")
    dock.wait_for_function("() => /^ok —/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)
    assert "not accepted" not in dock.locator("#lastResult").inner_text().lower()
    _quiet(dock)
    dock.get_by_role("button", name="Bank").click()
    dock.wait_for_selector(".frm[data-screen=bank] [data-n=side]", timeout=10_000)
    dock.locator(".frm [data-n=side]").select_option("withdraw")
    dock.locator(".frm [data-n=amount]").fill("40")
    dock.keyboard.press("Enter")
    dock.wait_for_function("() => /^ok —/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)


def test_stardock_hides_the_empty_port_header(seats) -> None:
    dock = seats["dock"]
    _quiet(dock)
    assert dock.locator(".porttbl").count() == 0
    here = dock.locator("#here").inner_text()
    assert "Items" not in here
    assert "Bank" in here


def test_g_lists_fighters_left_in_another_sector(seats) -> None:
    port = seats["port"]
    _quiet(port)
    home = _sector(port)
    assert home.isdigit()
    port.keyboard.press("f")
    port.wait_for_selector(".frm [data-n=leave]", timeout=10_000)
    port.locator(".frm [data-n=leave]").fill("10")
    port.keyboard.press("Enter")
    port.wait_for_function("() => /^ok —/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)
    port.locator("#warps button").first.click()
    port.wait_for_function(
        """(home) => {
          const m = (document.querySelector('#sectorText').innerText || '').match(/Sector\\s*:?\\s*(\\d+)/);
          return m && m[1] !== home && document.querySelector('#waitchip').textContent === 'YOUR MOVE';
        }""",
        arg=home,
        timeout=20_000,
    )
    port.keyboard.press("g")
    port.wait_for_selector("#menu[data-screen='Deployed Fighters']", timeout=10_000)
    text = port.locator("#menu").inner_text()
    assert f"Sector {home}" in text
    assert "10" in text
    assert "fighters" in text.lower()
    _shoot(port, "fighters")
    port.keyboard.press("Escape")
