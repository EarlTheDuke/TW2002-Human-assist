"""A contested landing form shows this ship, not the planet's fighters."""

from __future__ import annotations

import time

from tests._cu_host import CuHost
from tw2k.engine.models import Planet, PlanetClass
from tw2k.engine.observation import build_observation

TOK = "land-planet-brief-v1-token-p2-00000"
PLANET_ID = 88021
MAP_TOP = {1440: 714}


def _wait_parked(host: CuHost):
    deadline = time.time() + 15
    universe = host.runner.state.universe
    me = universe.players["P2"]
    while time.time() < deadline:
        sector = universe.sectors[me.sector_id]
        if me.sector_id > 10 and sector.warps:
            return universe, me
        time.sleep(0.05)
    raise AssertionError("seat did not park")


def test_land_form_hides_hostile_planet_numbers(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        universe, me = _wait_parked(host)
        planet = Planet(
            id=PLANET_ID, sector_id=me.sector_id, name="FogHold",
            class_id=PlanetClass.M, owner_id="P1",
            fighters=12345, shields=6789, citadel_level=2, citadel_target=2,
        )
        universe.planets[planet.id] = planet
        universe.sectors[me.sector_id].planet_ids.append(planet.id)
        me.ship.fighters = 222
        me.ship.shields = 33
        agent = next(a for a in host.runner.state.agents if a.player_id == "P2")
        agent.current_observation = build_observation(universe, "P2")

        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_selector("[data-verb=land_planet]:not([disabled])", timeout=20_000)
        lay = page.evaluate(
            """() => ({
              mapY: document.querySelector('#mapCard').getBoundingClientRect().top,
              mfd: document.querySelector('.mfd-body').getBoundingClientRect().height,
            })"""
        )
        assert abs(lay["mapY"] - MAP_TOP[1440]) < 4, lay["mapY"]
        assert abs(lay["mfd"] - 420) < 1
        page.click("[data-verb=land_planet]")
        page.wait_for_selector("#verbForm[data-verb=land_planet]", timeout=10_000)
        page.evaluate(
            """(id) => {
              const sel = document.querySelector('#verbForm select[name=planet_id]');
              sel.value = String(id);
              sel.dispatchEvent(new Event('change', { bubbles: true }));
            }""",
            PLANET_ID,
        )
        text = page.locator("#verbForm").inner_text()
        assert "222" in text
        assert "33" in text
        assert str(PLANET_ID) in text
        for hidden in ("12345", "12,345", "6789", "6,789"):
            assert hidden not in text, hidden
        page.close()
