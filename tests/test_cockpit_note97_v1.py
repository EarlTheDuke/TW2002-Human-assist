"""NOTE 97 cockpit. J is the class catalog, Z shows the reference, a landing names the reaction.

Screens go to docs/playtests/note97-v1/ at 1366 and 390. The StarDock class on the
sector line is a label: 8 while the class map is legacy, 9 while it is live.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tests._cu_host import CuHost
from tw2k.engine.models import Planet, PlanetClass
from tw2k.engine.observation import build_observation

TOK = "note97-cockpit-token-p2-000000000"
PLANET_ID = 88097
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "note97-v1"


def _ready(host: CuHost):
    deadline = time.time() + 20
    while time.time() < deadline:
        universe = host.runner.state.universe
        agent = next((row for row in host.runner.state.agents if row.player_id == "P2"), None)
        if host.parked and universe is not None and agent is not None and agent.awaiting_input and "P2" in universe.players:
            return universe, universe.players["P2"], agent
        time.sleep(0.05)
    raise AssertionError("seat did not become ready")


def _publish(universe, agent) -> None:
    agent.current_observation = build_observation(universe, "P2")


def _own_planet(universe, me) -> None:
    planet = Planet(
        id=PLANET_ID, sector_id=me.sector_id, name="Hold40",
        class_id=PlanetClass.M, owner_id="P2", military_reaction_pct=40,
    )
    universe.planets[planet.id] = planet
    universe.sectors[me.sector_id].planet_ids.append(planet.id)
    me.planet_landed = None


def _to_stardock(universe, me) -> None:
    here = universe.sectors[me.sector_id]
    if "P2" in here.occupant_ids:
        here.occupant_ids.remove("P2")
    me.sector_id = int(K.STARDOCK_SECTOR)
    me.planet_landed = None
    dock = universe.sectors[me.sector_id]
    if "P2" not in dock.occupant_ids:
        dock.occupant_ids.append("P2")
    me.known_sectors.add(me.sector_id)


def _shot(page, name: str, selector: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.locator(selector).screenshot(path=str(SHOTS / name))


def test_catalog_rules_and_reaction(tmp_path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK, turns_per_day=400) as host, sync_playwright() as pw:
        universe, me, agent = _ready(host)
        _own_planet(universe, me)
        _publish(universe, agent)
        browser = pw.chromium.launch()
        try:
            for width, height in ((1366, 900), (390, 844)):
                me.planet_landed = None
                _publish(universe, agent)
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
                page.wait_for_function(
                    "() => (document.querySelector('#waitchip') || {}).textContent === 'YOUR MOVE'",
                    timeout=20_000,
                )
                page.keyboard.press("c")
                page.wait_for_selector("#menu[data-screen=computer]", timeout=10_000)
                page.keyboard.press("j")
                page.wait_for_selector("#menu[data-screen=planet-catalog] [data-planet-class=M]", timeout=10_000)
                catalog = page.locator("#menu").inner_text()
                assert "Class M Earth" in catalog
                assert "Your planets" in catalog
                _shot(page, f"{width}-j.png", "#menu")
                page.locator("[data-your-planets]").click()
                page.wait_for_selector("#menu[data-screen=planet-specs]", timeout=10_000)
                assert "Your planets" in page.locator("#menu").inner_text()
                page.keyboard.press("Escape")
                page.keyboard.press("z")
                page.wait_for_function(
                    "() => /Citadel tables/.test((document.querySelector('#menu[data-screen=rules]') || {}).innerText || '')",
                    timeout=10_000,
                )
                rules = page.locator("#menu").inner_text()
                assert "Citadel tables" in rules
                assert "Flee rule" in rules
                assert "Haggle bands" in rules
                assert "Combat odds" in rules
                page.locator("#menu .y", has_text="Citadel tables").scroll_into_view_if_needed()
                _shot(page, f"{width}-rules.png", "#menu")
                page.keyboard.press("Escape")
                page.locator("#here button", has_text="Land on Hold40").click()
                page.wait_for_selector("#dangerOk", timeout=10_000)
                page.locator("#dangerOk").click()
                page.wait_for_function(
                    "() => /Military reaction 40/.test((document.querySelector('#lastResult') || {}).textContent || '')",
                    timeout=20_000,
                )
                page.wait_for_selector("[data-reaction=pct]", timeout=10_000)
                assert "Military reaction 40%" in page.locator("[data-reaction=pct]").inner_text()
                result = page.locator("#lastResult").inner_text()
                assert "Military reaction 40%" in result
                assert "40%.." not in result
                page.locator("[data-reaction=pct]").scroll_into_view_if_needed()
                _shot(page, f"{width}-planet.png", ".planet")
                page.close()
        finally:
            browser.close()


def test_stardock_sector_label_follows_the_class_map(tmp_path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    assert K.PORT_CLASS_MAP_MODE == "legacy"
    with CuHost(tmp_path, TOK, turns_per_day=400) as host, sync_playwright() as pw:
        universe, me, agent = _ready(host)
        _to_stardock(universe, me)
        port = universe.sectors[int(K.STARDOCK_SECTOR)].port
        assert port is not None
        assert int(port.class_id) == 8
        _publish(universe, agent)
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1366, "height": 900})
            page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
            page.wait_for_function(
                "() => (document.querySelector('#sectorText [data-port-class]') || {}).textContent === '8'",
                timeout=20_000,
            )
            monkeypatch.setattr(K, "PORT_CLASS_MAP_MODE", "live")
            assert int(universe.sectors[int(K.STARDOCK_SECTOR)].port.class_id) == 8
            page.reload()
            page.wait_for_function(
                "() => (document.querySelector('#sectorText [data-port-class]') || {}).textContent === '9'",
                timeout=20_000,
            )
            page.keyboard.press("c")
            page.wait_for_selector("#menu[data-screen=computer]", timeout=10_000)
            page.keyboard.press("r")
            page.wait_for_function(
                """() => [...document.querySelectorAll('[data-port=report]')].some((el) => {
                  const text = (el.textContent || '').trim();
                  return text.startsWith('1') && /class 9/.test(text);
                })""",
                timeout=10_000,
            )
        finally:
            browser.close()
