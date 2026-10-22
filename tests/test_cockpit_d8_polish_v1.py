"""NOTE 43. One page, in this order. Switches are turned on only inside a test and put back."""

from __future__ import annotations

from pathlib import Path

import tw2k.engine.constants as K
from tw2k.engine.models import EventKind, FerrengiShip
from tw2k.engine.observation import event_facts

from tests._cu_host import CuHost

TOK = "d8-polish-token-p2-000000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "d8-combat-polish-v1"


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
            "(sel) => { const el = (sel && document.querySelector(sel)) || document.querySelector('#menu') || document.querySelector('.frm') || document.querySelector('#here'); if (el) el.scrollIntoView({ block: 'center' }); }",
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
    page.evaluate("() => { if (window.__tw2kTest) window.__tw2kTest.resetWaits(); const el = document.querySelector('#lastResult'); if (el) el.textContent = ''; }")
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


def _install():
    import pytest

    @pytest.fixture(scope="module")
    def world(tmp_path_factory):
        _prior_planet_shield_mode = K.PLANET_SHIELD_MODE
        _prior_siege_report_mode = K.SIEGE_REPORT_MODE
        _prior_planet_landing_combat_mode = K.PLANET_LANDING_COMBAT_MODE
        _prior_ferrengi_engage_mode = K.FERRENGI_ENGAGE_MODE
        try:
            sync = pytest.importorskip("playwright.sync_api").sync_playwright
            pw = sync().start()
            host = CuHost(tmp_path_factory.mktemp("d8p"), TOK)
            host.__enter__()
            browser, page = _page(pw, host)
            try:
                yield {"page": page, "universe": host.runner.state.universe, "host": host}
            finally:
                K.PLANET_SHIELD_MODE = "legacy"
                K.SIEGE_REPORT_MODE = "legacy"
                K.PLANET_LANDING_COMBAT_MODE = "legacy"
                K.FERRENGI_ENGAGE_MODE = "legacy"
                browser.close()
                host.__exit__(None, None, None)
                pw.stop()
        finally:
            K.PLANET_SHIELD_MODE = _prior_planet_shield_mode
            K.SIEGE_REPORT_MODE = _prior_siege_report_mode
            K.PLANET_LANDING_COMBAT_MODE = _prior_planet_landing_combat_mode
            K.FERRENGI_ENGAGE_MODE = _prior_ferrengi_engage_mode

    return world


world = _install()


def test_arrival_without_fighters_does_not_ask_for_a_challenge(world):
    _prior_ferrengi_engage_mode = K.FERRENGI_ENGAGE_MODE
    try:
        page = world["page"]
        universe = world["universe"]
        me = universe.players["P2"]
        target = int(universe.sectors[me.sector_id].warps[0])
        universe.sectors[target].fighters = None
        _sit(universe, "P1", target)
        universe.players["P1"].ship.fighters = 40
        page.locator("#warps button", has_text=str(target)).first.click()
        _back(page, "warped")
        assert "fighters first" not in page.locator("#lastResult").inner_text()
        _shoot(page, "arrival", "#lastResult")
        nxt = int(universe.sectors[me.sector_id].warps[0])
        universe.sectors[nxt].fighters = None
        universe.ferrengi["F43"] = FerrengiShip(
            id="F43", name="Dreadnought", sector_id=nxt, aggression=8, fighters=400, shields=200,
        )
        me.ship.fighters = 20
        try:
            K.FERRENGI_ENGAGE_MODE = "tw2002"
            page.locator("#warps button", has_text=str(nxt)).first.click()
            _back(page, "Ferrengi")
            text = page.locator("#lastResult").inner_text()
            assert text.lower().count("fighters first") == 0
            _shoot(page, "ferrengi", "#lastResult")
        finally:
            K.FERRENGI_ENGAGE_MODE = "legacy"
    finally:
        K.FERRENGI_ENGAGE_MODE = _prior_ferrengi_engage_mode


def test_grey_shields_stay_when_the_switch_hides_them(world):
    _prior_planet_shield_mode = K.PLANET_SHIELD_MODE
    try:
        page = world["page"]
        universe = world["universe"]
        me = universe.players["P2"]
        planet = next(iter(universe.planets.values()))
        old = universe.sectors.get(planet.sector_id)
        if old is not None and planet.id in getattr(old, "planet_ids", []):
            old.planet_ids.remove(planet.id)
        planet.sector_id = int(me.sector_id)
        planet.owner_id = "P2"
        planet.citadel_level = 0
        planet.name = "Shield Rock"
        if planet.id not in universe.sectors[me.sector_id].planet_ids:
            universe.sectors[me.sector_id].planet_ids.append(planet.id)
        me.ship.shields = 400
        try:
            K.PLANET_SHIELD_MODE = "tw2002"
            _next(page, world["host"])
            page.locator("#here button", has_text="Land on").click()
            page.locator("#dangerOk").click()
            _back(page, "ok")
            page.keyboard.press("F")
            page.wait_for_selector(".frm [data-n=kind]", timeout=10_000)
            shields = page.locator(".frm option[value=shields]").evaluate("el => ({disabled: el.disabled, text: el.textContent})")
            assert shields["disabled"] is True
            assert "Level 5" in shields["text"]
            _shoot(page, "shields", ".frm")
            page.keyboard.press("Escape")
            page.keyboard.press("Q")
            _back(page, "ok")
        finally:
            K.PLANET_SHIELD_MODE = "legacy"
    finally:
        K.PLANET_SHIELD_MODE = _prior_planet_shield_mode


def test_a_shieldless_repulse_skips_the_zero_shields(world):
    _prior_siege_report_mode = K.SIEGE_REPORT_MODE
    try:
        page = world["page"]
        universe = world["universe"]
        me = universe.players["P2"]
        planet = next(p for p in universe.planets.values() if p.name == "Shield Rock")
        planet.owner_id = "P1"
        planet.citadel_level = 2
        planet.fighters = 800
        planet.shields = 0
        planet.military_reaction_pct = 0
        planet.name = "Phoenix"
        me.ship.fighters = 40
        me.ship.shields = 0
        try:
            K.SIEGE_REPORT_MODE = "tw2002"
            _next(page, world["host"])
            page.locator("#here button", has_text="Phoenix").click()
            page.wait_for_selector("#menu", timeout=10_000)
            menu = page.locator("#menu").inner_text()
            assert "Phoenix" in menu or "fighters" in menu.lower(), menu
            page.locator("#dangerOk").click()
            page.wait_for_function(
                "() => { const t = document.querySelector('#lastResult').textContent || '';"
                " if (/repelled|REFUSED|landed/i.test(t)) { window.__hit = t; return true; } return false; }",
                timeout=20_000,
            )
            text = page.evaluate("() => window.__hit")
            assert "Landing repelled" in text, text
            assert "planet shields" not in text
            assert "of the planet's fighters" in text
            assert "of your fighters" in text
            log = page.locator("#log").inner_text()
            assert "Landing repelled" in log
            assert "of the planet's fighters" in log
            assert "of your fighters" in log
            assert log.lower().count("landing repelled") == 1
            assert "invalid action" not in log.lower()
            _shoot(page, "siege", "#lastResult")
        finally:
            K.SIEGE_REPORT_MODE = "legacy"
    finally:
        K.SIEGE_REPORT_MODE = _prior_siege_report_mode


def test_an_l0_planet_does_not_claim_a_combat_computer(world):
    _prior_planet_landing_combat_mode = K.PLANET_LANDING_COMBAT_MODE
    try:
        page = world["page"]
        universe = world["universe"]
        me = universe.players["P2"]
        # Self-contained: do not rely on the earlier tests renaming a planet.
        planet = next(
            (p for p in universe.planets.values() if p.name in ("Phoenix", "Shield Rock")),
            None,
        ) or next(iter(universe.planets.values()))
        old = universe.sectors.get(planet.sector_id)
        if old is not None and planet.id in getattr(old, "planet_ids", []):
            old.planet_ids.remove(planet.id)
        planet.sector_id = int(me.sector_id)
        if planet.id not in universe.sectors[me.sector_id].planet_ids:
            universe.sectors[me.sector_id].planet_ids.append(planet.id)
        planet.name = "Phoenix"
        planet.citadel_level = 0
        planet.fighters = 40
        planet.shields = 0
        planet.owner_id = "P1"
        try:
            K.PLANET_LANDING_COMBAT_MODE = "tw2002"
            _next(page, world["host"])
            page.locator("#here button", has_text="Phoenix").click()
            page.wait_for_function(
                "() => (document.querySelector('#menu')?.innerText || '').includes('Its fighters will fight your landing.')",
                timeout=20_000,
            )
            text = page.locator("#menu").inner_text()
            assert "Its fighters will fight your landing." in text
            assert "Combat Control" not in text
            _shoot(page, "land", "#menu")
            page.keyboard.press("Escape")
        finally:
            K.PLANET_LANDING_COMBAT_MODE = "legacy"
    finally:
        K.PLANET_LANDING_COMBAT_MODE = _prior_planet_landing_combat_mode


def test_a_strike_back_names_the_fighters_and_the_shields(world):
    _prior_ferrengi_engage_mode = K.FERRENGI_ENGAGE_MODE
    try:
        page = world["page"]
        universe = world["universe"]
        me = universe.players["P2"]
        me.ship.fighters = 80
        me.ship.shields = 40
        universe.ferrengi["F44"] = FerrengiShip(
            id="F44", name="Dreadnought", sector_id=int(me.sector_id), aggression=8, fighters=900, shields=400,
        )
        try:
            K.FERRENGI_ENGAGE_MODE = "tw2002"
            _next(page, world["host"])
            page.keyboard.press("A")
            page.wait_for_selector(".frm", timeout=10_000)
            page.locator(".frm input").first.evaluate("el => { el.value = '10'; }")
            if page.locator(".frm select").count():
                page.locator(".frm select").first.evaluate(
                    """el => {
                      const hit = [...el.options].find(o => /dreadnought/i.test(o.textContent || ''));
                      if (hit) el.value = hit.value;
                    }"""
                )
            page.locator(".frm button", has_text="CONFIRM").click()
            page.wait_for_function(
                "() => { const t = document.querySelector('#lastResult').textContent || '';"
                " if (t.includes('struck back')) { window.__hit = t; return true; } return false; }",
                timeout=20_000,
            )
            text = page.evaluate("() => window.__hit")
            assert "You sent" in text
            assert "Dreadnought struck back" in text
            assert "shields" in text
            fight = next(e for e in reversed(universe.events) if e.kind is EventKind.COMBAT and (e.payload or {}).get("exchange_kind") == "ferrengi_vs_ship")
            assert "shield_losses" in event_facts(fight)
            _shoot(page, "strike", "#lastResult")
        finally:
            K.FERRENGI_ENGAGE_MODE = "legacy"
    finally:
        K.FERRENGI_ENGAGE_MODE = _prior_ferrengi_engage_mode
