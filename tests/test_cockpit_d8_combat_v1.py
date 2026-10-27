"""NOTE 41 cockpit sentences. One page, in this order. No stored flag moves."""

from __future__ import annotations

from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tests._cu_host import CuHost
from tw2k.engine.models import EventKind, FerrengiShip, Planet, PlanetClass

pytestmark = pytest.mark.legacy_profile

TOK = "d8-combat-token-p2-000000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "d8-combat-planet-fixes-v1"


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
        page.wait_for_timeout(120)
        page.evaluate(
            "(sel) => { const el = (sel && document.querySelector(sel)) || document.querySelector('#menu') || document.querySelector('#here'); if (el) el.scrollIntoView({ block: 'center' }); }",
            selector,
        )
        page.screenshot(path=str(SHOTS / f"{name}-{stem}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


def _back(page, needle: str) -> None:
    page.wait_for_function(
        "() => (document.querySelector('#lastResult').textContent || '').includes(" + repr(needle) + ")",
        timeout=20_000,
    )
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)


def _next(page, host, mutate=None) -> None:
    host.runner._wait_streak = {"P2": 0}
    page.keyboard.press("Escape")
    page.evaluate(
        "() => { if (window.__tw2kTest) window.__tw2kTest.resetWaits();"
        " const el = document.querySelector('#lastResult'); if (el) el.textContent = ''; }"
    )
    page.keyboard.press(".")
    menu = page.locator("#menu")
    if menu.count() and menu.is_visible() and "ends your day" in (menu.inner_text() or ""):
        page.keyboard.press("Escape")
        host.runner._wait_streak = {"P2": 0}
        page.evaluate("() => window.__tw2kTest.resetWaits()")
        page.keyboard.press(".")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
    if mutate:
        mutate()
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=30_000)


def _sit(universe, pid: str, sector_id: int) -> None:
    player = universe.players[pid]
    origin = universe.sectors[player.sector_id]
    if pid in origin.occupant_ids:
        origin.occupant_ids.remove(pid)
    player.sector_id = int(sector_id)
    player.planet_landed = None
    dest = universe.sectors[player.sector_id]
    if pid not in dest.occupant_ids:
        dest.occupant_ids.append(pid)
    if pid != "P2":
        player.turns_today = int(player.turns_per_day)


def _move_planet(universe, planet, sector_id: int) -> None:
    old = universe.sectors.get(planet.sector_id)
    if old is not None and planet.id in old.planet_ids:
        old.planet_ids.remove(planet.id)
    planet.sector_id = int(sector_id)
    dest = universe.sectors[sector_id]
    if planet.id not in dest.planet_ids:
        dest.planet_ids.append(planet.id)


def _install():
    import pytest

    @pytest.fixture(scope="module")
    def world(tmp_path_factory):
        _prior_info_mode = K.INFO_MODE
        try:
            sync = pytest.importorskip("playwright.sync_api").sync_playwright
            pw = sync().start()
            host = CuHost(tmp_path_factory.mktemp("d8"), TOK)
            host.__enter__()
            saved_info = K.INFO_MODE
            K.INFO_MODE = "tw2002"
            universe = host.runner.state.universe
            me = universe.players["P2"]
            me.ship.scanner = "holo"
            me.ship.fighters = 800
            me.ship.shields = 200
            browser, page = _page(pw, host)
            try:
                yield {"page": page, "universe": universe, "host": host}
            finally:
                K.INFO_MODE = saved_info
                browser.close()
                host.__exit__(None, None, None)
                pw.stop()
        finally:
            K.INFO_MODE = _prior_info_mode

    return world


world = _install()


def test_holo_scan_names_the_ships(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    nxt = int(universe.sectors[me.sector_id].warps[0])

    def plant():
        universe.ferrengi["F8"] = FerrengiShip(
            id="F8", name="Dreadnought", sector_id=nxt, aggression=8, fighters=6806, shields=400,
        )

    _next(page, world["host"], plant)
    page.keyboard.press("S")
    page.wait_for_selector(".frm select", timeout=10_000)
    page.locator(".frm select").select_option("holo")
    page.locator(".frm button", has_text="CONFIRM").click()
    _back(page, "Ships Dreadnought")
    assert "6,806 fighters" in page.locator("#lastResult").inner_text()
    _shoot(page, "holo", "#lastResult")


def test_attack_qty_is_clamped_to_the_cap(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]

    def plant():
        _sit(universe, "P1", me.sector_id)
        universe.players["P1"].ship.fighters = 10
        me.ship.fighters = 800

    _next(page, world["host"], plant)
    page.keyboard.press("A")
    page.wait_for_selector(".frm", timeout=10_000)
    label = page.locator(".frm label", has_text="fighters").inner_text()
    assert "fighters (1 to " in label
    assert "0 to" not in label
    _shoot(page, "attack", ".frm")
    page.locator(".frm input").first.evaluate("el => { el.value = '5000'; }")
    page.locator(".frm button", has_text="CONFIRM").click()
    _back(page, "ok")
    text = page.locator("#lastResult").inner_text()
    assert "must be" not in text
    assert me.ship.fighters < 800


def test_rival_citadel_warns_that_it_will_fight(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    planet = next(iter(universe.planets.values()))

    def plant():
        _move_planet(universe, planet, me.sector_id)
        planet.owner_id = "P1"
        planet.citadel_level = 2
        planet.citadel_target = 2
        planet.fighters = 40
        planet.shields = 10
        planet.has_transporter = False
        planet.name = "Phoenix"
        _sit(universe, "P1", universe.sectors[me.sector_id].warps[0])

    _next(page, world["host"], plant)
    page.locator("#here button", has_text="Land on").click()
    page.wait_for_selector("#menu", timeout=10_000)
    text = page.locator("#menu").inner_text()
    assert "Combat Control computer" in text
    assert "Landing claims it" not in text
    _shoot(page, "land", "#menu")
    page.keyboard.press("Escape")


def test_own_planet_shows_reaction_and_blocks_early_shields(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    planet = next(p for p in universe.planets.values() if p.name == "Phoenix")

    def claim():
        planet.owner_id = "P2"
        planet.military_reaction_pct = 50
        planet.has_transporter = False
        me.ship.fighters = 40
        me.ship.shields = 30

    _next(page, world["host"], claim)
    page.locator("#here button", has_text="Land on").click()
    page.locator("#dangerOk").click()
    _back(page, "ok")
    card = page.locator("#here").inner_text()
    assert "Military reaction 50%" in card
    assert "No transporter (buy one)." in card
    _shoot(page, "planet", "[data-reaction='pct']")
    page.keyboard.press("F")
    page.wait_for_selector(".frm select", timeout=10_000)
    shields = page.locator(".frm option[value='shields']").evaluate("el => ({disabled: el.disabled, text: el.textContent})")
    assert shields["disabled"] is True, shields
    assert "Level 5" in shields["text"]
    _shoot(page, "shields", ".frm")
    page.keyboard.press("Escape")
    page.locator("#here button", has_text="Set reaction").click()
    page.locator(".frm input").first.fill("50")
    page.locator(".frm button", has_text="CONFIRM").click()
    _back(page, "to 50%")
    page.keyboard.press("F")
    page.wait_for_selector(".frm")
    page.locator(".frm [data-n='kind']").select_option("fighters")
    page.locator(".frm input").first.fill("5")
    page.locator(".frm button", has_text="CONFIRM").click()
    _back(page, "ok")
    page.keyboard.press("G")
    page.wait_for_selector(".frm")
    page.locator(".frm [data-n='kind']").select_option("fighters")
    page.locator(".frm input").first.fill("1")
    page.locator(".frm button", has_text="CONFIRM").click()
    _back(page, "1 fighter from")
    assert "1 fighters" not in page.locator("#lastResult").inner_text()


def test_status_keeps_the_tax_and_the_fallback(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]

    def stamp():
        universe.emit(
            EventKind.TAX_COLLECTED,
            actor_id="P2",
            sector_id=me.sector_id,
            payload={"credits_before": 1000, "tax": 24210, "align_gain": 3, "new_alignment": 3},
            summary="Overnight Federation tax 24210 cr",
        )
        universe.emit(
            EventKind.RETREAT,
            actor_id="P2",
            sector_id=me.sector_id,
            payload={"from": 301, "to": 87, "overnight": True},
            summary="Commander fell back 301 -> 87 at the end of the day (the fighters hold 301)",
        )
        universe.day = int(universe.day) + 1

    _next(page, world["host"], stamp)
    text = page.locator("#lastResult").inner_text()
    if "fell back" not in text:
        _next(page, world["host"])
        text = page.locator("#lastResult").inner_text()
    assert "fell back" in text
    page.keyboard.press("Q")
    _back(page, "ok")
    page.keyboard.press("V")
    page.wait_for_selector("#menu", timeout=10_000)
    status = page.locator("#menu").inner_text()
    assert "24,210" in status
    assert "none yet" not in status
    _shoot(page, "status", "#menu")
    page.keyboard.press("Escape")
