"""NOTE 45. Planet class, ship capacity, and the rules reference."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request, urlopen

import tw2k.engine.constants as K

from tests._cu_host import CuHost

TOK = "info-audit-token-p2-0000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-info-audit-v1"


def _page(pw, host):
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    return browser, page


def _shoot(page, stem: str, selector: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    for width, name in ((1920, "1920"), (390, "390")):
        page.set_viewport_size({"width": width, "height": 844 if width == 390 else 1080})
        page.wait_for_timeout(80)
        page.evaluate(
            "(sel) => { const el = document.querySelector(sel); if (el) el.scrollIntoView({ block: 'center' }); }",
            selector,
        )
        page.screenshot(path=str(SHOTS / f"{name}-{stem}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


def _install():
    import pytest

    @pytest.fixture(scope="module")
    def world(tmp_path_factory):
        sync = pytest.importorskip("playwright.sync_api").sync_playwright
        pw = sync().start()
        host = CuHost(tmp_path_factory.mktemp("audit"), TOK)
        host.__enter__()
        browser, page = _page(pw, host)
        try:
            yield {"page": page, "universe": host.runner.state.universe, "host": host}
        finally:
            browser.close()
            host.__exit__(None, None, None)
            pw.stop()

    return world


world = _install()


def test_the_sector_line_shows_the_planet_class(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    planet = next(iter(universe.planets.values()))
    old = universe.sectors.get(planet.sector_id)
    if old is not None and planet.id in getattr(old, "planet_ids", []):
        old.planet_ids.remove(planet.id)
    planet.sector_id = int(me.sector_id)
    planet.name = "Audit Rock"
    if planet.id not in universe.sectors[me.sector_id].planet_ids:
        universe.sectors[me.sector_id].planet_ids.append(planet.id)
    host = world["host"]
    host.runner._wait_streak = {"P2": 0}
    page.keyboard.press(".")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    text = page.locator("[data-planet=class]").inner_text()
    assert "Audit Rock" in text
    assert "(" in text and ")" in text
    _shoot(page, "sector", "#sectorText")


def test_ship_info_shows_the_room_left(world):
    page = world["page"]
    page.keyboard.press("I")
    page.wait_for_selector("[data-screen=ship-info]", timeout=10_000)
    text = page.locator("#menu").inner_text()
    assert "Empty holds" in text
    assert " of " in text
    _shoot(page, "ship", "#menu")
    page.keyboard.press("Escape")


def test_rules_panel_and_the_reference_match_the_engine(world):
    page = world["page"]
    host = world["host"]
    page.keyboard.press("Z")
    page.wait_for_selector("[data-screen=rules] [data-ship=merchant_cruiser]", timeout=20_000)
    text = page.locator("#menu").inner_text()
    spec = K.ship_specs()["merchant_cruiser"]
    assert "Merchant Cruiser" in text
    assert f"{spec['cost']:,}" in text or str(spec["cost"]) in text
    assert "net worth" in text.lower()
    _shoot(page, "rules", "#menu")
    req = Request(
        f"{host.base}/harness/v1/P2/reference",
        headers={"Authorization": "Bearer " + TOK, "X-TW2K-Seat": "P2"},
    )
    with urlopen(req, timeout=10) as resp:
        body = json.load(resp)
    ships = next(section["rows"] for section in body["sections"] if section["id"] == "ships")
    cruiser = next(row for row in ships if row["id"] == "merchant_cruiser")
    assert cruiser["cost"] == int(spec["cost"])
    assert cruiser["max_fighters"] == int(spec["max_fighters"])
    prices = next(section["rows"] for section in body["sections"] if section["id"] == "prices")
    colonist = next(row for row in prices if row["name"] == "Colonist")
    assert colonist["price"] == int(K.COLONIST_PRICE)
    assert "constants.py" in colonist["source"]
