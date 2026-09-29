"""Local brackets: one line under the video, from this seat's sector only."""

from __future__ import annotations

import time

from tests._cu_host import VIEW_H, VIEW_W, CuHost
from tw2k.engine.models import Commodity
from tw2k.engine.observation import build_observation

TOK = "brackets-v1-token-p2-0000000000000"


def _agent(host):
    return next(a for a in host.runner.state.agents if a.player_id == "P2")


def _wait_parked(host: CuHost):
    deadline = time.time() + 15
    universe = host.runner.state.universe
    me = universe.players["P2"]
    while time.time() < deadline:
        port = universe.sectors[me.sector_id].port
        held = me.ship.cargo.get(Commodity.FUEL_ORE, 0)
        if me.sector_id > 10 and held >= 10 and port is not None:
            return universe, me
        time.sleep(0.05)
    raise AssertionError("seat did not park")


def _move_other_here(host, *, listed: bool):
    universe = host.runner.state.universe
    me = universe.players["P2"]
    other = universe.players["P1"]
    here = universe.sectors[me.sector_id]
    if "P1" in universe.sectors[other.sector_id].occupant_ids and other.sector_id != here.id:
        universe.sectors[other.sector_id].occupant_ids.remove("P1")
    other.sector_id = here.id
    if listed and "P1" not in here.occupant_ids:
        here.occupant_ids.append("P1")
    if not listed and "P1" in here.occupant_ids:
        here.occupant_ids.remove("P1")
    return universe, me, other


def _park_planet(universe, sector_id: int):
    planet = next(iter(universe.planets.values()))
    origin = planet.sector_id
    old = universe.sectors[origin]
    if planet.id in old.planet_ids and origin != sector_id:
        old.planet_ids.remove(planet.id)
    planet.sector_id = sector_id
    planet.owner_id = None
    planet.name = "Terra"
    dest = universe.sectors[sector_id]
    if planet.id not in dest.planet_ids:
        dest.planet_ids.append(planet.id)
    return planet, origin


def _clear_planets(universe, sector_id: int, planet, origin: int) -> None:
    sector = universe.sectors[sector_id]
    if planet.id in sector.planet_ids:
        sector.planet_ids.remove(planet.id)
    planet.sector_id = origin
    old = universe.sectors.get(origin)
    if old is not None and planet.id not in old.planet_ids:
        old.planet_ids.append(planet.id)


def test_brackets_list_seen_ships_and_planets_only(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        _wait_parked(host)
        universe, me, other = _move_other_here(host, listed=True)
        planet, origin = _park_planet(universe, me.sector_id)
        seen = build_observation(universe, "P2")
        assert "P1" in seen.sector["occupants"]
        assert any(p["name"] == "Terra" for p in seen.sector["planets"])
        _agent(host).current_observation = seen

        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.add_init_script(
            "window.__cls = 0;"
            "new PerformanceObserver((list) => {"
            "  for (const e of list.getEntries()) if (!e.hadRecentInput) window.__cls += e.value;"
            "}).observe({type: 'layout-shift', buffered: true});"
        )
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_function(
            "() => (document.querySelector('[data-testid=local-brackets]')?.textContent || '').includes('Terra')",
            timeout=15_000,
        )
        text = page.get_by_test_id("local-brackets").inner_text()
        assert "HBot · ship" in text
        assert "Terra · unowned" in text
        assert "fighters" not in text and "citadel" not in text
        assert page.locator("#viewport + #mapCard").count() == 1
        body = page.evaluate("() => document.querySelector('.mfd-body').getBoundingClientRect().height")
        assert abs(body - 420) < 1
        assert page.evaluate("() => window.__cls") < 0.1

        _move_other_here(host, listed=False)
        _clear_planets(universe, me.sector_id, planet, origin)
        hidden = build_observation(universe, "P2")
        assert "P1" not in hidden.sector["occupants"]
        assert any(row.get("id") == "P1" and row.get("sector_id") == me.sector_id for row in hidden.other_players)
        assert any(row.get("id") == "P1" for row in hidden.rivals)
        assert hidden.sector["planets"] == []
        _agent(host).current_observation = hidden
        page.get_by_test_id("refresh").click()
        page.wait_for_function(
            "() => document.querySelector('[data-testid=local-brackets]').textContent.trim() === ''",
            timeout=10_000,
        )
        assert "HBot" not in page.get_by_test_id("local-brackets").inner_text()
        assert other.name == "HBot" and me.sector_id == other.sector_id
        page.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')",
            timeout=20_000,
        )
        assert cu.evaluate("() => document.scrollingElement.scrollHeight") <= VIEW_H
