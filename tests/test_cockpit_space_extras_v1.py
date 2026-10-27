"""Port crime, port work, planet trade, a detonator, avoid, hail, jettison, and self-destruct.

The tests share one cockpit and run in this order. Jettison and self-destruct
are on only inside this file. The stored flags stay legacy everywhere else.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tests._cu_host import CuHost
from tw2k.engine.models import Commodity, PortClass

pytestmark = pytest.mark.legacy_profile

TOK = "space-token-p2-0000000000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-space-extras-v1"
GOODS = (Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT)


def _page(pw, host):
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    return browser, page


def _shoot(page, stem: str, selector: str = "") -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    for width, height, name in ((1920, 1080, "1920"), (390, 844, "390")):
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(150)
        page.evaluate(
            "(sel) => { const el = (sel && document.querySelector(sel)) || document.querySelector('.frm') || document.querySelector('#menu') || document.querySelector('[data-screen=space]'); if (el) el.scrollIntoView({ block: 'center' }); }",
            selector,
        )
        page.screenshot(path=str(SHOTS / f"{name}-{stem}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


def _action(request) -> dict:
    body = request.post_data_json
    if callable(body):
        body = body()
    return body["action"]


def _posted(page) -> None:
    page.wait_for_function(
        """() => {
          const chip = document.querySelector('#waitchip').textContent;
          const line = document.querySelector('#lastResult').textContent || '';
          return chip === 'YOUR MOVE' && /^(ok|REFUSED|FAILED)/.test(line);
        }""",
        timeout=20_000,
    )


def _form_post(page) -> dict:
    page.evaluate("() => { document.querySelector('#lastResult').textContent = ''; }")
    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000) as caught:
        page.locator(".frm button.verb", has_text="CONFIRM").click()
    _posted(page)
    return _action(caught.value)


def _next(page, mutate=None) -> None:
    page.keyboard.press("Escape")
    page.keyboard.press(".")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
    if mutate:
        mutate()
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=30_000)


def _relocate(universe, sector_id: int) -> None:
    me = universe.players["P2"]
    origin = universe.sectors[me.sector_id]
    if "P2" in origin.occupant_ids:
        origin.occupant_ids.remove("P2")
    me.sector_id = int(sector_id)
    me.planet_landed = None
    dest = universe.sectors[me.sector_id]
    if "P2" not in dest.occupant_ids:
        dest.occupant_ids.append("P2")


def _shift_planet(universe, planet, sector_id: int) -> None:
    origin = universe.sectors[planet.sector_id]
    origin.planet_ids = [pid for pid in origin.planet_ids if pid != planet.id]
    planet.sector_id = int(sector_id)
    planet.owner_id = "P2"
    planet.corp_ticker = None
    planet.last_transwarp_day = None
    dest = universe.sectors[sector_id]
    if planet.id not in dest.planet_ids:
        dest.planet_ids.append(planet.id)


def _buying(port):
    for commodity in GOODS:
        if port.buys(commodity):
            return commodity
    return None


def _other_ports(universe, skip: int) -> list[int]:
    found = []
    for sid, sector in universe.sectors.items():
        port = sector.port
        if port is None or int(sid) == int(skip):
            continue
        if port.class_id in (PortClass.STARDOCK, PortClass.FEDERAL):
            continue
        if getattr(port, "construction", None):
            continue
        found.append(int(sid))
    return found


def _empty_sector(universe) -> int:
    from tw2k.engine.port_build import radiating

    fed = {int(sid) for sid in K.FEDSPACE_SECTORS}
    for sid, sector in universe.sectors.items():
        if int(sid) in fed or int(sid) == 1 or sector.port is not None:
            continue
        if radiating(universe, sid):
            continue
        return int(sid)
    raise AssertionError("no empty sector")


def world(tmp_path_factory):
    return None


def _install():
    import pytest

    @pytest.fixture(scope="module")
    def world(tmp_path_factory):
        _prior_avoid_mode = K.AVOID_MODE
        _prior_ship_exit_mode = K.SHIP_EXIT_MODE
        _prior_rob_bust_denominator = K.ROB_BUST_DENOMINATOR
        try:
            sync = pytest.importorskip("playwright.sync_api").sync_playwright
            saved = (K.AVOID_MODE, K.SHIP_EXIT_MODE, K.ROB_BUST_DENOMINATOR)
            K.AVOID_MODE = "live"
            K.SHIP_EXIT_MODE = "tw2002"
            K.ROB_BUST_DENOMINATOR = 1_000_000_000
            pw = sync().start()
            host = CuHost(tmp_path_factory.mktemp("space"), TOK)
            host.__enter__()
            universe = host.runner.state.universe
            me = universe.players["P2"]
            planet = next(iter(universe.planets.values()))
            browser, page = _page(pw, host)
            try:
                yield {
                    "page": page,
                    "universe": universe,
                    "me": me,
                    "planet": planet,
                    "port_a": int(me.sector_id),
                    "port_b": _other_ports(universe, int(me.sector_id))[0],
                }
            finally:
                browser.close()
                host.__exit__(None, None, None)
                pw.stop()
                K.AVOID_MODE, K.SHIP_EXIT_MODE, K.ROB_BUST_DENOMINATOR = saved
        finally:
            K.AVOID_MODE = _prior_avoid_mode
            K.SHIP_EXIT_MODE = _prior_ship_exit_mode
            K.ROB_BUST_DENOMINATOR = _prior_rob_bust_denominator

    return world


world = _install()


def test_rob_shows_the_risk_and_posts(world) -> None:
    page = world["page"]
    page.wait_for_selector("[data-kind=rob]")
    _shoot(page, "port", "[data-screen=space]")
    assert "dim" in (page.locator("[data-kind=rob]").get_attribute("class") or "")
    page.evaluate("() => { document.querySelector('#lastResult').textContent = ''; }")
    page.get_by_role("button", name="Rob this port", exact=True).click()
    page.wait_for_function("() => /alignment must be -100/.test(document.querySelector('#lastResult').textContent || '')", timeout=10_000)

    def arm() -> None:
        me = world["me"]
        port = world["universe"].sectors[me.sector_id].port
        me.alignment = -200
        me.experience = 420
        me.credits = 100_000
        port.credits = 5_000

    _next(page, arm)
    page.wait_for_function("() => { const b = document.querySelector('[data-kind=rob]'); return b && !b.classList.contains('dim'); }", timeout=20_000)
    page.get_by_role("button", name="Rob this port", exact=True).click()
    page.wait_for_selector("[data-screen=rob]")
    note = page.locator("[data-price=dock]").inner_text()
    assert "1 chance in 50" in note
    assert "-100" in note
    _shoot(page, "rob", "[data-screen=rob]")
    posted = _form_post(page)
    assert posted["kind"] == "rob"
    assert posted["args"]["amount"] == 1


def test_steal_shows_the_risk_and_posts(world) -> None:
    page = world["page"]

    def move() -> None:
        _relocate(world["universe"], world["port_b"])
        port = world["universe"].sectors[world["port_b"]].port
        for commodity in GOODS:
            row = port.stock.get(commodity)
            if row is not None and int(row.current) < 10:
                row.current = 10

    _next(page, move)
    page.wait_for_function("() => { const b = document.querySelector('[data-kind=steal]'); return b && !b.classList.contains('dim'); }", timeout=20_000)
    page.get_by_role("button", name="Steal cargo", exact=True).click()
    page.wait_for_selector("[data-screen=steal]")
    assert "1 chance in 50" in page.locator("[data-price=dock]").inner_text()
    posted = _form_post(page)
    assert posted["kind"] == "steal"
    assert posted["args"]["qty"] == 1


def test_upgrade_shows_the_price_and_posts(world) -> None:
    page = world["page"]
    page.wait_for_function("() => { const b = document.querySelector('[data-kind=port_upgrade]'); return b && !b.classList.contains('dim'); }", timeout=20_000)
    page.get_by_role("button", name="Upgrade this port", exact=True).click()
    page.wait_for_selector("[data-screen=portUpgrade]")
    note = page.locator("[data-price=dock]").inner_text()
    assert "cr a unit" in note
    assert "holds" in note
    _shoot(page, "upgrade", "[data-screen=portUpgrade]")
    posted = _form_post(page)
    assert posted["kind"] == "port_upgrade"
    assert posted["args"]["units"] == 1


def test_planet_trade_shows_the_quote_and_posts(world) -> None:
    page = world["page"]

    def plant() -> None:
        universe = world["universe"]
        _relocate(universe, world["port_a"])
        planet = world["planet"]
        _shift_planet(universe, planet, world["port_a"])
        port = universe.sectors[world["port_a"]].port
        commodity = _buying(port)
        assert commodity is not None
        row = port.stock.get(commodity)
        row.current = 0
        if int(row.maximum) < 100:
            row.maximum = 100
        for key in list(planet.stockpile.keys()):
            planet.stockpile[key] = 0
        planet.stockpile[commodity] = 500

    _next(page, plant)
    page.wait_for_function("() => { const b = document.querySelector('[data-kind=planet_trade]'); return b && !b.classList.contains('dim'); }", timeout=20_000)
    page.get_by_role("button", name="Planet trade", exact=True).click()
    page.wait_for_selector("[data-screen=planetTrade]")
    note = page.locator("[data-price=dock]").inner_text()
    assert "cr" in note
    assert "quote" in note
    _shoot(page, "trade", "[data-screen=planetTrade]")
    posted = _form_post(page)
    assert posted["kind"] == "planet_trade"
    assert posted["args"]["qty"] == 1


def test_build_shows_the_price_and_posts(world) -> None:
    page = world["page"]
    page.keyboard.press("Escape")
    page.evaluate("() => { document.querySelector('#lastResult').textContent = ''; }")
    page.get_by_role("button", name="Build a port", exact=True).click()
    page.wait_for_function("() => /already has a port/.test(document.querySelector('#lastResult').textContent || '')", timeout=10_000)
    empty = _empty_sector(world["universe"])

    def move() -> None:
        _shift_planet(world["universe"], world["planet"], empty)
        _relocate(world["universe"], empty)

    _next(page, move)
    page.wait_for_function("() => { const b = document.querySelector('[data-kind=port_build]'); return b && !b.classList.contains('dim'); }", timeout=20_000)
    page.get_by_role("button", name="Build a port", exact=True).click()
    page.wait_for_selector("[data-screen=portBuild]")
    note = page.locator("[data-price=dock]").inner_text()
    assert "30,000" in note
    _shoot(page, "build", "[data-screen=portBuild]")
    page.locator("[data-screen=portBuild] select").first.select_option("SSS")
    posted = _form_post(page)
    assert posted["kind"] == "port_build"
    assert posted["args"]["port_class"] == "SSS"


def test_avoid_list_is_in_the_computer(world) -> None:
    page = world["page"]
    page.keyboard.press("Escape")
    page.keyboard.press("c")
    page.wait_for_function("() => /Avoid sectors/.test(document.querySelector('#menu').textContent || '')", timeout=10_000)
    _shoot(page, "computer", "#menu")
    page.keyboard.press("o")
    page.wait_for_selector("[data-screen=avoid]")
    assert "0 to clear" in page.locator("[data-price=dock]").inner_text()
    _shoot(page, "avoid", "[data-screen=avoid]")
    page.locator("[data-screen=avoid] input").fill(str(world["port_a"]))
    posted = _form_post(page)
    assert posted["kind"] == "avoid"
    assert posted["args"]["sector"] == world["port_a"]


def test_hail_shows_the_player_and_posts(world) -> None:
    page = world["page"]
    page.keyboard.press("Escape")
    page.get_by_role("button", name="Hail one player", exact=True).click()
    page.wait_for_selector("[data-screen=hail]")
    note = page.locator("[data-price=dock]").inner_text()
    assert "only to" in note
    assert "not the whole sector" in note
    _shoot(page, "hail", "[data-screen=hail]")
    posted = _form_post(page)
    assert posted["kind"] == "hail"
    assert posted["args"]["target"]
    assert posted["args"]["message"] == "Hello"


def test_jettison_explains_the_cost_and_posts(world) -> None:
    page = world["page"]

    def load() -> None:
        world["me"].planet_landed = None
        world["me"].ship.cargo[Commodity.COLONISTS] = 4

    _next(page, load)
    page.keyboard.press("j")
    page.wait_for_selector("[data-screen=jettison]")
    note = page.locator("[data-price=dock]").inner_text()
    assert "1 alignment" in note
    assert "250" in note
    _shoot(page, "jettison", "[data-screen=jettison]")
    page.locator("[data-screen=jettison] select").select_option("colonists")
    posted = _form_post(page)
    assert posted["kind"] == "jettison"
    assert posted["args"]["commodity"] == "colonists"
    assert posted["args"]["qty"] == 1


def test_atomic_shows_the_warning_and_posts(world) -> None:
    page = world["page"]
    planet = world["planet"]

    def land() -> None:
        me = world["me"]
        _relocate(world["universe"], int(planet.sector_id))
        me.planet_landed = int(planet.id)
        me.ship.atomic_detonators = 1
        for key in list(planet.colonists.keys()):
            planet.colonists[key] = 0

    _next(page, land)
    page.wait_for_function("() => { const b = document.querySelector('[data-kind=deploy_atomic]'); return b && !b.classList.contains('dim'); }", timeout=20_000)
    page.get_by_role("button", name="Atomic detonator", exact=True).click()
    page.wait_for_selector("[data-screen=atomic]")
    note = page.locator("[data-price=dock]").inner_text()
    assert "YOUR ship" in note
    assert "No colonists" in note
    _shoot(page, "atomic", "[data-screen=atomic]")
    posted = _form_post(page)
    assert posted["kind"] == "deploy_atomic"
    assert posted["args"]["planet_id"] == int(planet.id)


def test_self_destruct_confirms_then_posts(world) -> None:
    page = world["page"]
    page.keyboard.press("Escape")
    page.keyboard.press("b")
    page.wait_for_selector("#dangerOk", timeout=10_000)
    words = page.locator("#menu").inner_text()
    assert "half your experience" in words
    assert "tomorrow" in words
    _shoot(page, "destruct", "#menu")
    page.evaluate("() => { document.querySelector('#lastResult').textContent = ''; }")
    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000) as caught:
        page.locator("#dangerOk").click()
    page.wait_for_function(
        """() => {
          const chip = document.querySelector('#waitchip').textContent;
          const line = document.querySelector('#lastResult').textContent || '';
          return /^(ok|REFUSED|FAILED)/.test(line) || chip === 'NO TURNS';
        }""",
        timeout=20_000,
    )
    posted = _action(caught.value)
    assert posted["kind"] == "self_destruct"
