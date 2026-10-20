"""A box the player clears stays empty through the 2-second refresh, and an empty amount posts nothing.

COMMANDER NOTE 62 cockpit-form-blank-keep-v1. Before the fix the refresh rebuilt the form and put the
default back into a cleared box (Bank: 500,000 within 2 s), so CONFIRM moved money the player did
not ask for. Each test clears a prefilled box, waits more than 3 refresh cycles, checks the box is
still empty, then presses CONFIRM (and Enter on the bank) and checks for "Type an amount." with no
action POST. Reopening the form is the only thing that brings the default back.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.engine.models import Commodity

from tests._cu_host import CuHost
from tests._refresh import wait_refreshes

DOCK_TOK = "blank-dock-token-p2-0000000000000"
PORT_TOK = "blank-port-token-p2-0000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-form-blank-keep-v1"
WIDTHS = ((1920, 1080, "1920"), (390, 844, "390"))


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
        page.evaluate("() => { const el = document.querySelector('.frm'); if (el) el.scrollIntoView({ block: 'center' }); }")
        page.screenshot(path=str(SHOTS / f"{name}-{stem}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


def _clear_and_wait(page, box: str) -> str:
    before = page.locator(box).input_value()
    assert before != "", "the form should open with a default in the box"
    page.locator(box).fill("")
    wait_refreshes(page, 3)
    assert page.locator(".frm").count() == 1
    assert page.locator(box).input_value() == "", "the refresh put a value back into the cleared box"
    return before


def _refused_without_post(page, press) -> None:
    posts: list[str] = []

    def seen(request) -> None:
        if request.method == "POST" and request.url.endswith("/action"):
            posts.append(request.url)

    page.evaluate("() => { document.querySelector('#lastResult').textContent = ''; }")
    page.on("request", seen)
    try:
        press()
        page.wait_for_function(
            "() => /Type an amount\\./.test(document.querySelector('#lastResult').textContent || '')", timeout=10_000
        )
        page.wait_for_timeout(1_000)
    finally:
        page.remove_listener("request", seen)
    assert posts == []


def _confirm(page):
    return lambda: page.locator(".frm button.verb", has_text="CONFIRM").click()


@pytest.fixture(scope="module")
def seats(tmp_path_factory):
    _prior_haggle_live_mode = K.HAGGLE_LIVE_MODE
    _prior_ship_exit_mode = K.SHIP_EXIT_MODE
    try:
        sync = pytest.importorskip("playwright.sync_api").sync_playwright
        saved = (K.HAGGLE_LIVE_MODE, K.SHIP_EXIT_MODE)
        K.HAGGLE_LIVE_MODE = "live"
        K.SHIP_EXIT_MODE = "tw2002"
        pw = sync().start()
        dock_host = CuHost(tmp_path_factory.mktemp("blank-dock"), DOCK_TOK, park_at=1)
        dock_host.__enter__()
        port_host = CuHost(tmp_path_factory.mktemp("blank-port"), PORT_TOK)
        port_host.__enter__()
        port_host.runner.state.universe.players["P2"].ship.cargo[Commodity.COLONISTS] = 4
        dock_browser, dock_page = _page(pw, dock_host, DOCK_TOK)
        port_browser, port_page = _page(pw, port_host, PORT_TOK)
        try:
            yield {"dock": dock_page, "port": port_page}
        finally:
            dock_browser.close()
            port_browser.close()
            dock_host.__exit__(None, None, None)
            port_host.__exit__(None, None, None)
            pw.stop()
            K.HAGGLE_LIVE_MODE, K.SHIP_EXIT_MODE = saved
    finally:
        K.HAGGLE_LIVE_MODE = _prior_haggle_live_mode
        K.SHIP_EXIT_MODE = _prior_ship_exit_mode


def test_bank_amount_stays_empty_and_confirm_or_enter_posts_nothing(seats) -> None:
    dock = seats["dock"]
    _quiet(dock)
    dock.get_by_role("button", name="Bank").click()
    box = ".frm[data-screen=bank] [data-n=amount]"
    dock.wait_for_selector(box, timeout=10_000)
    default = _clear_and_wait(dock, box)
    _refused_without_post(dock, _confirm(dock))
    _shoot(dock, "bank-blank")
    wait_refreshes(dock, 1)
    assert dock.locator(box).input_value() == ""
    dock.locator(box).focus()
    _refused_without_post(dock, lambda: dock.keyboard.press("Enter"))
    assert dock.locator(box).input_value() == ""
    dock.locator(box).fill("123")
    wait_refreshes(dock, 3)
    assert dock.locator(box).input_value() == "123"
    _quiet(dock)
    dock.get_by_role("button", name="Bank").click()
    dock.wait_for_selector(box, timeout=10_000)
    assert dock.locator(box).input_value() == default, "opening the form again brings the default back"
    _quiet(dock)


def test_fighters_leave_box_stays_empty_and_confirm_posts_nothing(seats) -> None:
    port = seats["port"]
    _quiet(port)
    port.keyboard.press("f")
    box = ".frm[data-screen=fighters] [data-n=leave]"
    port.wait_for_selector(box, timeout=10_000)
    _clear_and_wait(port, box)
    _refused_without_post(port, _confirm(port))
    _shoot(port, "fighters-blank")
    _quiet(port)


def test_cleared_haggle_offer_stays_empty_and_trades_at_the_list(seats) -> None:
    port = seats["port"]
    _quiet(port)
    port.keyboard.press("p")
    box = ".frm [data-n=unit_price]"
    port.wait_for_selector(box, timeout=10_000)
    port.locator(".frm [data-n=qty]").fill("5")
    side = port.locator(".frm [data-n=side]").input_value()
    commodity = port.locator(".frm [data-n=commodity]").input_value()
    assert commodity != "", "the form opens on a commodity it offers"
    _clear_and_wait(port, box)
    assert port.locator(".frm [data-n=qty]").input_value() == "5"
    assert port.locator(".frm [data-n=side]").input_value() == side
    assert port.locator(".frm [data-n=commodity]").input_value() == commodity
    _shoot(port, "trade-blank")
    with port.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000) as caught:
        _confirm(port)()
    body = caught.value.post_data_json
    args = (body() if callable(body) else body)["action"]["args"]
    assert args["qty"] == 5
    assert "unit_price" not in args, "a cleared offer trades at the list price (cockpit-fullpass-fix-v1)"
    port.wait_for_function("() => /^(ok|REFUSED|FAILED)/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)
    _quiet(port)


def test_jettison_quantity_stays_empty_and_confirm_posts_nothing(seats) -> None:
    port = seats["port"]
    _quiet(port)
    port.keyboard.press("j")
    box = "[data-screen=jettison] [data-n=qty]"
    port.wait_for_selector(box, timeout=10_000)
    _clear_and_wait(port, box)
    _refused_without_post(port, _confirm(port))
    _shoot(port, "jettison-blank")
    _quiet(port)
