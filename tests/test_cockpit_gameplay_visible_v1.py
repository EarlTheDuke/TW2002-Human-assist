"""Carried gear, sector mines and beacons, port class, paid price, experience, mail, one-way warps."""

from __future__ import annotations

from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.engine.models import Commodity, MineDeployment, MineType

from tests._cu_host import CuHost

TOK = "visible-token-p2-0000000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-gameplay-visible-v1"


def _page(pw, host):
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    return browser, page


def _shoot(page, stem: str, selector: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    for width, height, name in ((1920, 1080, "1920"), (390, 844, "390")):
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(150)
        page.evaluate(
            "(sel) => { const el = document.querySelector(sel); if (el) el.scrollIntoView({ block: 'center' }); }",
            selector,
        )
        page.screenshot(path=str(SHOTS / f"{name}-{stem}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    _prior_info_mode = K.INFO_MODE
    try:
        sync = pytest.importorskip("playwright.sync_api").sync_playwright
        pw = sync().start()
        host = CuHost(tmp_path_factory.mktemp("visible"), TOK)
        host.__enter__()
        K.INFO_MODE = "tw2002"
        universe = host.runner.state.universe
        me = universe.players["P2"]
        sector = universe.sectors[me.sector_id]
        sector.mines.append(MineDeployment(owner_id="P2", kind=MineType.ARMID, count=5))
        sector.beacon = "Danger, Ferrengi"
        dest = int(sector.warps[0])
        me.known_warps[dest] = []
        ship = me.ship
        ship.mines[MineType.ATOMIC] = 1
        ship.ether_probes = 3
        ship.genesis = 2
        ship.photon_missiles = 1
        ship.corbomite = 4
        ship.marker_beacons = 2
        ship.psychic_probe = 1
        ship.scanner = "holo"
        ship.cargo[Commodity.FUEL_ORE] = 10
        ship.cargo_cost[Commodity.FUEL_ORE] = 26.0
        me.experience = 1500
        me.inbox.append({"from": "P1", "kind": "hail", "message": "Meet me at StarDock", "day": 1})
        browser, opened = _page(pw, host)
        opened.code = sector.port.code
        try:
            yield opened
        finally:
            browser.close()
            host.__exit__(None, None, None)
            pw.stop()
    finally:
        K.INFO_MODE = _prior_info_mode


def test_carried_gear_shows_on_the_ship_and_zeros_on_ship_info(page) -> None:
    page.locator("#shipStats").scroll_into_view_if_needed()
    stats = page.locator("#shipStats").inner_text()
    for label in ("Atomic mines", "Ether probes", "Genesis", "Photons", "Corbomite", "Beacons", "Psychic probe", "Holographic Scanner"):
        assert label in stats
    assert page.locator("[data-gear=detonator]").count() == 0
    _shoot(page, "gear", "#shipStats")
    page.keyboard.press("i")
    page.wait_for_selector("#menu[data-screen=ship-info]", timeout=10_000)
    info = page.locator("#menu").inner_text()
    assert "Atomic detonators" in info and "0" in info
    assert "Cloaks" in info
    page.keyboard.press("Escape")


def test_sector_shows_armid_mines(page) -> None:
    line = page.locator("[data-mines=sector]").inner_text()
    assert "armid" in line and "5" in line


def test_sector_shows_the_beacon_message(page) -> None:
    assert "Danger, Ferrengi" in page.locator("[data-beacon=here]").inner_text()
    _shoot(page, "sector", "#sectorText")


def test_port_panel_and_report_show_the_class_code(page) -> None:
    assert page.code in page.locator("[data-port=code]").inner_text()
    _shoot(page, "port", "[data-port=code]")
    page.keyboard.press("c")
    page.keyboard.press("r")
    page.wait_for_selector("#menu [data-port=report]", timeout=10_000)
    assert page.code in page.locator("#menu").inner_text()
    page.keyboard.press("Escape")


def test_holds_show_the_price_paid(page) -> None:
    paid = page.locator("[data-paid=fuel_ore]").inner_text()
    assert "paid" in paid and "26" in paid


def test_experience_is_on_the_bar_and_on_status(page) -> None:
    assert page.locator("#xp").inner_text() == "1,500"
    page.keyboard.press("v")
    page.wait_for_selector("#menu[data-screen='Game Status']", timeout=10_000)
    assert "Experience" in page.locator("#menu").inner_text()
    assert "1,500" in page.locator("#menu").inner_text()
    _shoot(page, "status", "#menu")
    page.keyboard.press("Escape")


def test_unread_mail_shows_and_y_reads_it(page) -> None:
    assert "Meet me at StarDock" in page.locator("[data-mail=unread]").inner_text()
    page.keyboard.press("y")
    page.wait_for_selector("#menu [data-mail=letter]", timeout=10_000)
    assert "Meet me at StarDock" in page.locator("#menu").inner_text()
    _shoot(page, "mail", "#menu")
    page.keyboard.press("Escape")


def test_one_way_warps_are_marked(page) -> None:
    assert "one-way" in page.locator("#warps").inner_text()
    assert page.locator("#map .lane.oneway").count() >= 1
