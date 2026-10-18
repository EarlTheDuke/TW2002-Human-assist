"""NOTE 52. Ferrengi engage stays legacy. The growth switch is not touched."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.engine.ferrengi import _make_ferrengi, open_ferrengi_encounter
from tw2k.engine.models import Commodity, PlanetClass
from tw2k.engine.observation import build_observation

from tests._cu_host import CuHost

TOK = "note51-polish-token-p2-00000000000"
TOK1 = "note51-polish-token-p1-00000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "note51-polish-v1"


def _page(pw, host, token, seat):
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{host.base}/bot?layout=redesign&seat={seat}&token={token}")
    page.wait_for_selector("#waitchip", timeout=20_000)
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


def _your_move(page) -> None:
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=25_000)


def _wait(page, host, pid: str) -> None:
    streak = getattr(host.runner, "_wait_streak", None)
    if isinstance(streak, dict):
        streak[pid] = 0
    page.evaluate("() => { if (window.__tw2kTest) window.__tw2kTest.resetWaits(); }")
    page.keyboard.press("Escape")
    page.keyboard.press(".")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)


def _move(universe, pid: str, sector_id: int) -> None:
    player = universe.players[pid]
    origin = universe.sectors[player.sector_id]
    if pid in origin.occupant_ids:
        origin.occupant_ids.remove(pid)
    player.sector_id = int(sector_id)
    player.planet_landed = None
    dest = universe.sectors[player.sector_id]
    if pid not in dest.occupant_ids:
        dest.occupant_ids.append(pid)


@pytest.fixture
def world(tmp_path):
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    pw = sync().start()
    host = CuHost(tmp_path, TOK, max_days=8)
    host.__enter__()
    browser, page = _page(pw, host, TOK, "P2")
    _your_move(page)
    try:
        yield {"page": page, "universe": host.runner.state.universe, "host": host, "pw": pw}
    finally:
        browser.close()
        host.__exit__(None, None, None)
        pw.stop()


def test_the_attacked_player_hears_who_and_the_shields_left(tmp_path):
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    pw = sync().start()
    host = CuHost(tmp_path, TOK, p1_token=TOK1, max_days=6, turns_per_day=30)
    host.__enter__()
    browser, first = _page(pw, host, TOK1, "P1")
    second = browser.new_page(viewport={"width": 1440, "height": 900})
    second.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
    second.wait_for_selector("#waitchip", timeout=20_000)
    try:
        universe = host.runner.state.universe
        sector = universe.sectors[40]
        sector.fighters = None
        sector.mines = []
        for pid, fighters, shields in (("P1", 200, 0), ("P2", 80, 40)):
            _move(universe, pid, 40)
            universe.players[pid].ship.fighters = fighters
            universe.players[pid].ship.shields = shields
        pages = {"P1": first, "P2": second}

        def ready() -> str:
            for _ in range(40):
                for pid, pg in pages.items():
                    if pg.locator("#waitchip").inner_text() == "YOUR MOVE":
                        return pid
                first.wait_for_timeout(250)
            raise AssertionError("nobody reached YOUR MOVE")

        for _ in range(2):
            pid = ready()
            _wait(pages[pid], host, pid)
        actor = ready()
        other = "P2" if actor == "P1" else "P1"
        page = pages[actor]
        previous = page.locator("#lastResult").inner_text()
        page.keyboard.press("Escape")
        page.locator("[data-key=A]").click()
        page.wait_for_selector(".frm", timeout=8_000)
        page.locator(".frm select").evaluate(
            """(el, name) => {
              const hit = [...el.options].find((o) => new RegExp(name, 'i').test(o.textContent || ''));
              el.value = hit ? hit.value : el.options[0].value;
            }""",
            universe.players[other].name,
        )
        page.locator(".frm input[type=number]").evaluate("(el) => { el.value = '40'; }")
        page.locator(".frm button", has_text="CONFIRM").click()
        page.wait_for_function(
            "() => { const now = document.querySelector('#lastResult').textContent || ''; return now !== "
            + json.dumps(previous)
            + " && /fighters remain/.test(now); }",
            timeout=20_000,
        )
        text = page.locator("#lastResult").inner_text()
        assert "fighters remain" in text
        assert "fighters and" in text and "shields" in text
        _shoot(page, "attack", "#lastResult")
        victim = pages[other]
        _your_move(victim)
        victim.wait_for_function(
            "() => /attacked you in 40/.test(document.querySelector('#lastResult').textContent || '') && /shields left/.test(document.querySelector('#lastResult').textContent || '')",
            timeout=20_000,
        )
        heard = victim.locator("#lastResult").inner_text()
        assert "fighters and" in heard and "shields left" in heard
        log = victim.locator("#log").inner_text()
        assert "attacked you in 40" in log
        _shoot(victim, "hit", "#lastResult")
    finally:
        browser.close()
        host.__exit__(None, None, None)
        pw.stop()


def test_one_fighter_still_says_how_many_remain(world):
    page = world["page"]
    universe = world["universe"]
    home = int(universe.players["P2"].sector_id)

    def arm() -> None:
        me = universe.players["P2"]
        me.planet_landed = None
        me.turns_today = 0
        me.ship.fighters = 20
        rival = universe.players["P1"]
        _move(universe, "P1", home)
        _move(universe, "P2", home)
        rival.ship.ship_class = me.ship.ship_class
        rival.ship.fighters = 5
        rival.ship.shields = 0
        rival.turns_today = int(rival.turns_per_day)

    page.keyboard.press("Escape")
    page.keyboard.press(".")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
    arm()
    _your_move(page)
    page.keyboard.press("a")
    page.wait_for_selector(".frm")
    page.locator(".frm input[type=number]").evaluate("(el) => { el.value = '1'; }")
    page.evaluate("() => { document.querySelector('#lastResult').textContent = ''; }")
    page.locator(".frm button.verb", has_text="CONFIRM").click()
    page.wait_for_function(
        "() => /You lost/.test(document.querySelector('#lastResult').textContent || '') && /remain/.test(document.querySelector('#lastResult').textContent || '')",
        timeout=20_000,
    )


def _plant_ferrengi(universe):
    me = universe.players["P2"]
    me.planet_landed = None
    for good in list(me.ship.cargo):
        me.ship.cargo[good] = 0
    ferr = _make_ferrengi(universe, fid="note52d10a", sid=int(me.sector_id), aggression=8)
    ferr.name = "Ferrengi Battle Cruiser _d10a"
    ferr.fighters = 1200
    universe.ferrengi[ferr.id] = ferr
    open_ferrengi_encounter(universe, ferr, me)
    return ferr


def test_an_ignored_boarding_says_what_the_ferrengi_took(world):
    page = world["page"]
    universe = world["universe"]
    assert K.FERRENGI_ENGAGE_MODE == "legacy"
    fields = set(build_observation(universe, "P2").model_dump().keys())
    _plant_ferrengi(universe)
    page.wait_for_function(
        "() => /surrender costs 5 cargo holds/.test(document.querySelector('#log').textContent || '')",
        timeout=15_000,
    )
    _wait(page, world["host"], "P2")
    _your_move(page)
    page.wait_for_function(
        "() => /You ignored the Ferrengi Battle Cruiser d10a/.test(document.querySelector('#lastResult').textContent || '')",
        timeout=20_000,
    )
    text = page.locator("#lastResult").inner_text()
    assert "5 cargo holds" in text
    assert "cr" in text
    assert "_d10a" not in text
    assert set(build_observation(universe, "P2").model_dump().keys()) == fields
    _shoot(page, "tribute", "#lastResult")


def test_the_tribute_log_says_paid(world):
    page = world["page"]
    universe = world["universe"]
    _plant_ferrengi(universe)
    page.wait_for_function("() => /Ferrengi Fighter Attack/.test(document.querySelector('#log').textContent || '')", timeout=15_000)
    _wait(page, world["host"], "P2")
    _your_move(page)
    page.wait_for_function(
        "() => /paid tribute to Ferrengi Battle Cruiser d10a/.test(document.querySelector('#log').textContent || '')",
        timeout=20_000,
    )
    log = page.locator("#log").inner_text()
    assert "surrendered tribute" not in log
    assert "5 cargo holds" in log
    _shoot(page, "paid", "#log")


def test_a_ferrengi_name_uses_one_form(world):
    page = world["page"]
    universe = world["universe"]
    page.keyboard.press("Escape")
    page.keyboard.press(".")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
    _move(universe, "P2", 40)
    universe.sectors[40].fighters = None
    universe.sectors[40].mines = []
    _plant_ferrengi(universe)
    universe.players["P1"].turns_today = int(universe.players["P1"].turns_per_day)
    _your_move(page)
    page.wait_for_function(
        "() => /Ferrengi Battle Cruiser d10a/.test(document.querySelector('#sectorText').textContent || '')",
        timeout=15_000,
    )
    shown = page.locator("#sectorText").inner_text()
    assert "_d10a" not in shown
    page.keyboard.press("a")
    page.wait_for_selector(".frm")
    options = page.locator(".frm option").evaluate_all("els => els.map((el) => el.textContent)")
    assert any("d10a" in (text or "") and "_d10a" not in (text or "") for text in options)
    _shoot(page, "name", "#sectorText")


def test_a_boarding_names_fighters_and_the_surrender_cost(world):
    page = world["page"]
    universe = world["universe"]
    _plant_ferrengi(universe)
    page.wait_for_function(
        "() => /1,200 fighters/.test(document.querySelector('#log').textContent || '') && /surrender costs 5 cargo holds and all your cargo; with empty holds, 5 cargo holds and 10% of the credits on board/.test(document.querySelector('#log').textContent || '')",
        timeout=15_000,
    )
    _shoot(page, "board", "#log")


def test_leave_product_starts_with_a_quantity(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    planet = next(iter(universe.planets.values()))
    old = universe.sectors.get(planet.sector_id)
    if old is not None and planet.id in getattr(old, "planet_ids", []):
        old.planet_ids.remove(planet.id)
    planet.sector_id = int(me.sector_id)
    planet.owner_id = "P2"
    planet.class_id = PlanetClass.M
    planet.name = "Phoenix"
    planet.fighters = 0
    planet.shields = 0
    if planet.id not in universe.sectors[me.sector_id].planet_ids:
        universe.sectors[me.sector_id].planet_ids.append(planet.id)
    me.ship.cargo[Commodity.FUEL_ORE] = 12
    _wait(page, world["host"], "P2")
    _your_move(page)
    page.locator("#here button", has_text="Phoenix").click()
    page.locator("#dangerOk").click()
    page.wait_for_function(
        "() => (document.querySelector('#lastResult').textContent || '').toLowerCase().includes('land')",
        timeout=20_000,
    )
    page.keyboard.press("v")
    page.wait_for_selector(".frm input[type=number]", timeout=10_000)
    assert int(page.locator(".frm input[type=number]").input_value()) == 12
    page.wait_for_timeout(2500)
    assert int(page.locator(".frm input[type=number]").input_value()) == 12
    _shoot(page, "leave", ".frm")
