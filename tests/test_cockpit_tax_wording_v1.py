"""COMMANDER NOTE 83. The bank warning and the dawn tax line use the server's tax rule.

A legacy game says 5% over 100,000. A v3.11 game says 10% over 49,999.
The dawn line names the night, and an older tax is not called last night's.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tw2k.engine import constants as K
from tw2k.engine.models import EventKind

from tests._cu_host import CuHost

TOK = "note83-tax-token-p2-00000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-tax-wording-v1"
OLD_WARN = "The dawn tax takes 10% of the cash on your ship when it is over 49,999."
OLD_DAWN = "Overnight Federation tax. Day "


def _open(browser, host, width, height):
    page = browser.new_page(viewport={"width": width, "height": height})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    return page


def _show(page, host):
    from tw2k.engine.observation import build_observation

    agent = next(a for a in host.runner.state.agents if a.player_id == "P2")
    agent.current_observation = build_observation(host.runner.state.universe, "P2")
    page.evaluate("() => window.__tw2kTest && window.__tw2kTest.setAwaiting(true)")
    page.wait_for_timeout(400)


def _host(tmp_path_factory, name):
    host = CuHost(tmp_path_factory.mktemp(name), TOK, seed=8301)
    host.__enter__()
    # The helper skips its own reserved ports and starts at 8050. Refusing
    # every port from 8031 through 8119 made these three tests fail on that start.
    from tests._cu_host import RESERVED_TEST_PORTS
    if host.port in RESERVED_TEST_PORTS:
        host.__exit__(None, None, None)
        pytest.fail(f"host bound a reserved port {host.port}")
    return host


def _shoot(page, stem):
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOTS / f"{stem}.png"))


@pytest.fixture
def browser():
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    pw = sync().start()
    try:
        launched = pw.chromium.launch(headless=True)
    except Exception as exc:
        pw.stop()
        pytest.skip(f"chromium is not installed: {exc}")
    yield launched
    launched.close()
    pw.stop()


def _warn(page, host, width, height, stem):
    page.set_viewport_size({"width": width, "height": height})
    u = host.runner.state.universe
    me = u.players["P2"]
    me.planet_landed = None
    me.sector_id = int(K.STARDOCK_SECTOR)
    me.credits = 90_000
    me.bank_balance = 50_000
    _show(page, host)
    page.keyboard.press("Escape")
    page.wait_for_selector("#here button[data-kind=bank]", timeout=10_000)
    page.locator("#here button", has_text="Bank").click()
    page.wait_for_selector("#formSlot [data-n=side]", timeout=10_000)
    page.locator("#formSlot [data-n=side]").select_option("withdraw")
    page.locator("#formSlot [data-n=amount]").fill("20000")
    page.locator("#formSlot button", has_text="CONFIRM").click()
    page.wait_for_selector("#dangerOk", timeout=10_000)
    text = page.locator("#menu").inner_text()
    _shoot(page, stem)
    return text


def test_legacy_withdraw_uses_the_five_percent_line(browser, tmp_path_factory):
    """The old fixed sentence names 10% and 49,999. A legacy game must not."""
    assert K.V311_PROFILE == "legacy"
    host = _host(tmp_path_factory, "note83-legacy")
    try:
        page = _open(browser, host, 1280, 800)
        text = _warn(page, host, 1280, 800, "1280-withdraw")
        assert "The dawn tax takes 5% of the cash on your ship when it is over 100,000." in text
        assert OLD_WARN not in text
        page.keyboard.press("Escape")
        narrow = _warn(page, host, 390, 844, "390-withdraw")
        assert "5% of the cash on your ship when it is over 100,000." in narrow
        assert OLD_WARN not in narrow
    finally:
        host.__exit__(None, None, None)


def test_v311_withdraw_keeps_the_ten_percent_line(browser, tmp_path_factory):
    prior = K.V311_PROFILE
    K.V311_PROFILE = "v311"
    host = _host(tmp_path_factory, "note83-v311")
    try:
        page = _open(browser, host, 1280, 800)
        text = _warn(page, host, 1280, 800, "1280-withdraw-v311")
        assert OLD_WARN in text
        assert "5% of the cash on your ship when it is over 100,000." not in text
    finally:
        K.V311_PROFILE = prior
        host.__exit__(None, None, None)


def test_the_dawn_line_names_the_night_and_an_older_tax_is_not_last_night(browser, tmp_path_factory):
    host = _host(tmp_path_factory, "note83-dawn")
    try:
        page = _open(browser, host, 1280, 800)
        u = host.runner.state.universe
        me = u.players["P2"]
        u.day = 2
        u.emit(
            EventKind.TAX_COLLECTED, actor_id="P2", sector_id=me.sector_id,
            payload={"credits_before": 999_000, "tax": 49_950, "align_gain": 33, "new_alignment": 33},
            summary="Day 2 tax 49,950 cr",
        )
        _show(page, host)
        page.wait_for_selector("[data-tax=overnight]", timeout=10_000)
        line = page.locator("[data-tax=overnight]").inner_text()
        assert line == "Overnight Federation tax for the night before day 2: 49,950 cr, alignment +33."
        assert OLD_DAWN not in line
        _shoot(page, "1280-tax")
        page.set_viewport_size({"width": 390, "height": 844})
        _shoot(page, "390-tax")
        u.config.max_days = 30
        u.day = 7
        _show(page, host)
        page.wait_for_function("() => document.querySelector('#sbDay').textContent === '7'", timeout=10_000)
        page.keyboard.press("V")
        page.wait_for_function(
            "() => /Last night: no tax/.test(document.querySelector('#menu').textContent || '')",
            timeout=10_000,
        )
        status = page.locator("#menu").inner_text()
        assert "for the night before day 2: 49,950 cr, alignment +33." in status
        assert "Last night: no tax" in status
        assert "Last night: 49,950" not in status
    finally:
        host.__exit__(None, None, None)
