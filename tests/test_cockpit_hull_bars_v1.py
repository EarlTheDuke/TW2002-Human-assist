"""Hull bars on the Ship tab, drawn from this seat's own ship numbers."""

from __future__ import annotations

import time

import pytest

from tests._cu_host import VIEW_H, VIEW_W, CuHost
from tw2k.engine.models import Commodity
from tw2k.engine.observation import build_observation

TOK = "hull-bars-v1-token-p2-000000000000"


def _wait_parked(host: CuHost):
    deadline = time.time() + 15
    universe = host.runner.state.universe
    me = universe.players["P2"]
    while time.time() < deadline:
        if me.sector_id > 10 and me.ship.cargo.get(Commodity.FUEL_ORE, 0) >= 10:
            return universe, me
        time.sleep(0.05)
    raise AssertionError("seat did not park")


def _serve(host, universe):
    agent = next(a for a in host.runner.state.agents if a.player_id == "P2")
    agent.current_observation = build_observation(universe, "P2")
    return agent.current_observation


def _bar(page, name: str) -> dict:
    return page.evaluate(
        """(name) => {
          const row = document.querySelector(`[data-testid="${name}"]`);
          return {value: row.dataset.value, max: row.dataset.max, width: row.querySelector('.fill').style.width};
        }""",
        name,
    )


def _tabs_stay(page) -> None:
    for name in ("ship", "port", "planets", "bridge", "moments"):
        page.get_by_test_id(f"mfd-tab-{name}").click()
        height = page.evaluate("() => document.querySelector('.mfd-body').getBoundingClientRect().height")
        assert abs(height - 420) < 1


def test_hull_bars_follow_this_ships_numbers(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        universe, me = _wait_parked(host)
        other = universe.players["P1"]
        other.ship.fighters = 999
        other.ship.genesis = 9
        other.ship.shields = 500
        me.ship.fighters = 4
        me.ship.shields = 0
        me.ship.genesis = 2
        for commodity in list(me.ship.cargo):
            me.ship.cargo[commodity] = 0
        me.ship.cargo[Commodity.FUEL_ORE] = me.ship.holds
        obs = _serve(host, universe)
        assert obs.ship["cargo_free"] == 0
        assert obs.ship["fighters"] == 4

        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_function("() => document.querySelector('[data-testid=hull-holds]')?.dataset.value !== ''", timeout=15_000)
        holds = _bar(page, "hull-holds")
        assert holds["value"] == str(me.ship.holds) and holds["max"] == str(me.ship.holds) and holds["width"] == "100%"
        assert _bar(page, "hull-shields")["value"] == "0" and _bar(page, "hull-shields")["width"] == "0%"
        genesis = _bar(page, "hull-genesis")
        assert genesis["value"] == "2" and genesis["width"] == "100%"
        assert _bar(page, "hull-fighters")["value"] == "4"
        card = page.locator("#shipLoadout").inner_text()
        assert "999" not in card and "999" not in page.get_by_test_id("hull-bars").inner_text()
        assert "Genesis" in card
        _tabs_stay(page)

        for commodity in list(me.ship.cargo):
            me.ship.cargo[commodity] = 0
        me.ship.shields = 40
        _serve(host, universe)
        page.get_by_test_id("refresh").click()
        page.wait_for_function("() => document.querySelector('[data-testid=hull-holds]')?.dataset.value === '0'", timeout=10_000)
        assert _bar(page, "hull-holds")["width"] == "0%"
        assert _bar(page, "hull-shields")["value"] == "40"
        assert "999" not in page.get_by_test_id("hull-bars").inner_text()
        page.close()

        wide = browser.new_page(viewport={"width": 1920, "height": 1080})
        wide.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        wide.wait_for_selector("#turnBanner.turn", timeout=20_000)
        _tabs_stay(wide)
        wide.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')",
            timeout=20_000,
        )
        assert cu.evaluate("() => document.scrollingElement.scrollHeight") <= VIEW_H


def test_hull_tabs_stay_put_in_firefox(tmp_path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as p:
        _wait_parked(host)
        browser = p.firefox.launch()
        for width, height in ((1440, 900), (1920, 1080)):
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
            page.wait_for_selector("#turnBanner.turn", timeout=20_000)
            page.wait_for_selector("[data-testid=hull-holds]", timeout=15_000)
            _tabs_stay(page)
            page.close()
        browser.close()
