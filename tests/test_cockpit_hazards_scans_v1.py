"""Landing warning, scan numbers, arrival hits, and the hazard lines.

The browser tests share one page and run in this order. The landing fight
and the entry-clash shield soak stay off except inside the tests that turn
them on. The stored flags stay legacy.
"""

from __future__ import annotations

from pathlib import Path

import tw2k.engine.constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import EventKind, FighterDeployment, FighterMode, MineDeployment, MineType
from tw2k.engine.runner import _planet_fighters_defend
from tw2k.engine.scanners import handle_probe

from tests._cu_host import CuHost

TOK = "hazard-token-p2-000000000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-hazards-scans-v1"


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


def _next(page, mutate=None) -> None:
    page.keyboard.press("Escape")
    page.evaluate("() => { const el = document.querySelector('#lastResult'); if (el) el.textContent = ''; }")
    page.keyboard.press(".")
    confirm = page.locator("#dangerOk")
    if confirm.count() and confirm.is_visible():
        confirm.click()
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
    origin = universe.sectors[planet.sector_id]
    if planet.id in origin.planet_ids:
        origin.planet_ids.remove(planet.id)
    planet.sector_id = int(sector_id)
    dest = universe.sectors[sector_id]
    if planet.id not in dest.planet_ids:
        dest.planet_ids.append(planet.id)


def _install():
    import pytest

    @pytest.fixture(scope="module")
    def world(tmp_path_factory):
        sync = pytest.importorskip("playwright.sync_api").sync_playwright
        pw = sync().start()
        saved_info = K.INFO_MODE
        saved_landing = K.PLANET_LANDING_COMBAT_MODE
        saved_clash = K.OFFENSIVE_CLASH_MODE
        host = CuHost(tmp_path_factory.mktemp("hazards"), TOK)
        host.__enter__()
        K.INFO_MODE = "tw2002"
        universe = host.runner.state.universe
        me = universe.players["P2"]
        me.ship.scanner = "holo"
        me.ship.shields = 400
        browser, page = _page(pw, host)
        try:
            yield {"page": page, "universe": universe, "host": host}
        finally:
            K.PLANET_LANDING_COMBAT_MODE = saved_landing
            K.OFFENSIVE_CLASH_MODE = saved_clash
            browser.close()
            host.__exit__(None, None, None)
            pw.stop()
            K.INFO_MODE = saved_info

    return world


world = _install()


def test_landing_names_the_holder_before_it_posts(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    planet = next(iter(universe.planets.values()))

    def plant():
        _move_planet(universe, planet, me.sector_id)
        planet.owner_id = "P1"
        planet.citadel_level = 1
        planet.fighters = 300
        planet.shields = 40
        planet.name = "Held Rock"
        _sit(universe, "P1", me.sector_id)

    _next(page, plant)
    page.locator("#here button", has_text="Land on").click()
    page.wait_for_selector("#menu", timeout=10_000)
    text = page.locator("#menu").inner_text()
    assert "HBot holds this planet" in text
    assert "not on this scan" in text
    _shoot(page, "land", "#menu")
    page.keyboard.press("Escape")
    page.keyboard.press("A")
    page.wait_for_selector(".frm", timeout=10_000)
    options = page.locator(".frm option").evaluate_all("els => els.map(el => el.textContent)")
    assert not any("Held Rock" in (row or "") for row in options)
    page.keyboard.press("Escape")
    saved_landing = K.PLANET_LANDING_COMBAT_MODE
    try:
        K.PLANET_LANDING_COMBAT_MODE = "tw2002"
        _next(page)
        page.locator("#here button", has_text="Land on").click()
        page.wait_for_selector("#menu")
        armed = page.locator("#menu").inner_text()
        assert "Fighters 300" in armed
        assert "shields 40" in armed
        _shoot(page, "land-armed", "#menu")
        page.keyboard.press("Escape")
        assert _planet_fighters_defend(planet) is True
        K.PLANET_LANDING_COMBAT_MODE = "legacy"
        assert _planet_fighters_defend(planet) is False
    finally:
        K.PLANET_LANDING_COMBAT_MODE = saved_landing


def test_density_scan_lists_each_neighbour(world):
    page = world["page"]
    page.evaluate("() => { const el = document.querySelector('#lastResult'); if (el) el.textContent = ''; }")
    page.keyboard.press("S")
    page.wait_for_selector(".frm select", timeout=10_000)
    page.locator(".frm select").select_option("density")
    page.locator(".frm button", has_text="CONFIRM").click()
    _back(page, "Warps :")
    text = page.locator("#lastResult").inner_text()
    assert "Warps :" in text
    assert "NavHaz :" in text
    _shoot(page, "density", "#lastResult")


def test_holo_scan_lists_what_is_next_door(world):
    page = world["page"]
    page.evaluate("() => { const el = document.querySelector('#lastResult'); if (el) el.textContent = ''; }")
    page.keyboard.press("S")
    page.wait_for_selector(".frm select", timeout=10_000)
    page.locator(".frm select").select_option("holo")
    page.locator(".frm button", has_text="CONFIRM").click()
    _back(page, "holo scan")
    text = page.locator("#lastResult").inner_text()
    assert "Sector " in text
    assert "Anom :" in text
    _shoot(page, "holo", "#lastResult")


def test_arrival_puts_the_mine_hit_on_the_result(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    target = int(universe.sectors[me.sector_id].warps[0])

    def lay():
        sector = universe.sectors[target]
        sector.mines.append(MineDeployment(owner_id="P1", kind=MineType.ARMID, count=2))
        me.ship.shields = 400

    _next(page, lay)
    page.locator("#warps button", has_text=str(target)).first.click()
    _back(page, "mines hit")
    text = page.locator("#lastResult").inner_text()
    assert "mines hit" in text
    assert "remain" in text
    _shoot(page, "arrival", "#lastResult")


def test_fighters_and_mines_name_the_trader(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    sector = universe.sectors[me.sector_id]

    def plant():
        sector.fighters = FighterDeployment(owner_id="P1", count=12, mode=FighterMode.TOLL)
        sector.mines.append(MineDeployment(owner_id="P1", kind=MineType.ARMID, count=1))
        _sit(universe, "P1", me.sector_id)

    _next(page, plant)
    text = page.locator("#sectorText").inner_text()
    assert "belong to HBot" in text
    _shoot(page, "owners", "#sectorText")
    sector.fighters = None
    sector.mines = [row for row in sector.mines if not (row.owner_id == "P1" and row.count == 1)]


def test_offensive_clash_stays_on_todays_path(world):
    from tw2k.engine.combat import _resolve_fighter_sector_combat

    universe = world["universe"]
    me = universe.players["P2"]
    sector = universe.sectors[me.sector_id]
    saved_fighters = sector.fighters
    saved_shields = int(me.ship.shields)
    saved_count = int(me.ship.fighters)
    saved_clash = K.OFFENSIVE_CLASH_MODE
    saved_notice = K.OWNER_HAZARD_NOTICE_MODE
    try:
        me.ship.shields = 50
        me.ship.fighters = 20
        sector.fighters = FighterDeployment(owner_id="P1", count=5, mode=FighterMode.OFFENSIVE)
        K.OFFENSIVE_CLASH_MODE = "legacy"
        _resolve_fighter_sector_combat(universe, "P2", me.sector_id)
        assert int(me.ship.shields) == 50
        me.ship.shields = 50
        me.ship.fighters = 20
        sector.fighters = FighterDeployment(owner_id="P1", count=5, mode=FighterMode.OFFENSIVE)
        K.OFFENSIVE_CLASH_MODE = "tw2002"
        _resolve_fighter_sector_combat(universe, "P2", me.sector_id)
        assert int(me.ship.shields) < 50
        K.OFFENSIVE_CLASH_MODE = "legacy"
        from tw2k.engine.observation import _event_visible_base

        notice = next(ev for ev in reversed(universe.events) if ev.payload.get("defender_owner") == "P1")
        saved_payload = dict(notice.payload)
        notice.payload["_witnesses"] = []
        notice.payload.pop("victim", None)
        assert _event_visible_base(notice, "P1", universe) is False
        K.OWNER_HAZARD_NOTICE_MODE = "tw2002"
        assert _event_visible_base(notice, "P1", universe) is True
        K.OWNER_HAZARD_NOTICE_MODE = "legacy"
        notice.payload.clear()
        notice.payload.update(saved_payload)
        sector.fighters = saved_fighters
        me.ship.shields = saved_shields
        me.ship.fighters = saved_count
    finally:
        K.OFFENSIVE_CLASH_MODE = saved_clash
        K.OWNER_HAZARD_NOTICE_MODE = saved_notice


def test_citadel_form_shows_the_cost_before_confirm(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    planet = next(p for p in universe.planets.values() if p.name == "Held Rock")

    def own():
        _move_planet(universe, planet, me.sector_id)
        planet.owner_id = "P2"
        planet.citadel_level = 0
        planet.citadel_target = 0
        planet.fighters = 0
        planet.shields = 0
        for key in list(planet.stockpile):
            planet.stockpile[key] = 0
        _sit(universe, "P2", me.sector_id)

    _next(page, own)
    page.locator("#here button", has_text="Land on").click()
    page.locator("#dangerOk").click()
    _back(page, "ok")
    page.keyboard.press("B")
    page.wait_for_selector("#dangerOk", timeout=10_000)
    text = page.locator("#menu").inner_text()
    assert "Fuel ore" in text
    assert "Colonists" in text
    assert "1 day" in text
    assert "1 days" not in text
    assert page.locator("#dangerOk").inner_text() == "CONFIRM"
    assert page.locator("[data-n=planet_id]").count() == 0
    _shoot(page, "citadel", "#menu")
    page.keyboard.press("Escape")
    page.keyboard.press("Q")
    _back(page, "ok")


def test_port_report_marks_a_port_never_visited(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    missing = next(sid for sid in universe.sectors if sid not in me.known_warps and sid != me.sector_id)
    me.known_ports[missing] = {"class": "BSB", "stock": {}, "last_seen_day": None}
    seen = next(sid for sid in universe.sectors if sid != missing and sid not in me.known_warps and sid != me.sector_id)
    me.known_ports[seen] = {
        "class": "SBB",
        "last_seen_day": 1,
        "stock": {"fuel_ore": {"current": 40, "max": 80, "price": 22, "side": "buys_from_player"}},
    }
    _next(page)
    page.keyboard.press("C")
    page.keyboard.press("R")
    page.wait_for_selector("[data-port=report]", timeout=10_000)
    text = page.locator("#menu").inner_text()
    assert "not visited" in text
    assert "Buying" in text
    assert "%" in text
    _shoot(page, "ports", "#menu")
    page.keyboard.press("Escape")


def test_owner_hears_when_their_mine_hits(world):
    page = world["page"]
    universe = world["universe"]

    def hit():
        universe.emit(
            EventKind.MINE_DETONATED,
            actor_id="P2",
            sector_id=universe.players["P2"].sector_id,
            payload={"hits": 1, "damage": 30, "victim": "P1"},
            summary="1 armid mines hit HBot",
        )

    _next(page, hit)
    page.wait_for_function(
        "() => (document.querySelector('#lastResult').textContent || '').includes('for 30 damage')",
        timeout=20_000,
    )
    text = page.locator("#lastResult").inner_text()
    assert "Your mines hit" in text
    assert "for 30 damage" in page.locator("#log").inner_text()
    _shoot(page, "alert", "#lastResult")


def test_small_lines_name_the_command_and_the_probe(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    neighbour = int(universe.sectors[me.sector_id].warps[0])
    universe.sectors[neighbour].fighters = FighterDeployment(owner_id="P1", count=8, mode=FighterMode.OFFENSIVE)
    me.ship.ether_probes = 1
    result = handle_probe(universe, "P2", Action(kind=ActionKind.PROBE, args={"target": neighbour}))
    assert result.ok
    summary = universe.events[-1].summary
    assert "in sector" in summary
    assert "1 sector out" in summary
    empty = next(sid for sid, sector in universe.sectors.items() if sector.port is None and sid != me.sector_id)

    def move():
        _sit(universe, "P2", empty)

    _next(page, move)
    assert page.locator("#here button", has_text="Rob this port").count() == 0
    page.keyboard.press("C")
    page.keyboard.press("K")
    page.wait_for_selector("#menu", timeout=10_000)
    assert "You have explored" in page.locator("#menu").inner_text()
    _shoot(page, "known", "#menu")
    page.keyboard.press("Escape")
    me.ship.marker_beacons = 1
    _next(page)
    page.keyboard.press("R")
    page.wait_for_selector(".frm", timeout=10_000)
    page.locator(".frm button", has_text="CONFIRM").click()
    assert "beacon message" in page.locator("#lastResult").inner_text().lower()
    page.evaluate("() => window.__tw2kTest.setAwaiting(false)")
    page.locator("#warps button").first.click()
    text = page.locator("#lastResult").inner_text()
    assert "will run when your turn comes" in text
    _shoot(page, "waiting", "#lastResult")
    page.evaluate("() => window.__tw2kTest.setAwaiting(true)")


def test_stardock_names_the_remaining_gear(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]

    def dock():
        _sit(universe, "P2", 1)
        me.credits = 5_000_000
        me.ship.scanner = None
        me.ship.genesis = 0

    _next(page, dock)
    page.locator("#here button", has_text="StarDock: buy gear").click()
    page.wait_for_selector(".frm", timeout=10_000)
    options = page.locator(".frm option").evaluate_all("els => els.map(el => el.textContent)")
    for name in ("Genesis Torpedo", "Cloaking Device", "Density Scanner", "Holographic Scanner"):
        assert name in options
    _shoot(page, "gear", ".frm")
    page.keyboard.press("Escape")
