"""Warp buttons show a port code only from this seat's memory.

An unvisited neighbour stays a bare number even when the live sector has a
port. A port row is marked sellable only when this seat holds the commodity
and the port buys it. Both layouts stay inside 1280x800.
"""

from __future__ import annotations

import time

from tests._cu_host import VIEW_H, VIEW_W, CuHost
from tw2k.engine.models import Commodity
from tw2k.engine.observation import build_observation

TOK = "amz6-codes-token-p2-000000000000"


def _wait_parked(host: CuHost):
    deadline = time.time() + 15
    u = host.runner.state.universe
    me = u.players["P2"]
    while time.time() < deadline:
        port = u.sectors[me.sector_id].port
        held = me.ship.cargo.get(Commodity.FUEL_ORE, 0)
        if held >= 10 and port is not None and (port.code or "").startswith("B"):
            return u, me
        time.sleep(0.05)
    raise AssertionError("seat did not park on a port that buys fuel")


def _replace_snapshot(host: CuHost, universe) -> None:
    agent = next(a for a in host.runner.state.agents if a.player_id == "P2")
    agent.current_observation = build_observation(universe, "P2")


def test_warp_code_comes_from_memory_and_fuel_row_can_sell(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        universe, me = _wait_parked(host)
        here = universe.sectors[me.sector_id]
        unknown = next(sid for sid in here.warps if sid not in me.known_ports and universe.sectors[sid].port)
        live_code = universe.sectors[unknown].port.code
        assert live_code and live_code != "ZZZ"
        _replace_snapshot(host, universe)

        page = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_function(
            "() => document.querySelector('[data-testid=port-row-fuel_ore]')?.getAttribute('data-can-sell') === 'true'",
            timeout=15_000,
        )
        page.get_by_test_id("mfd-tab-port").click()
        fuel = page.locator("[data-testid=port-row-fuel_ore]")
        assert fuel.locator(".can-sell-mark").is_visible()
        rows = page.locator("#portTape tbody tr[data-testid^='port-row-']")
        for i in range(rows.count()):
            row = rows.nth(i)
            if row.get_attribute("data-testid") == "port-row-fuel_ore":
                continue
            assert row.get_attribute("data-can-sell") is None

        label = page.evaluate(f"() => document.querySelector('[data-testid=warp-{unknown}]').textContent")
        assert label == f"WARP {unknown}"
        assert live_code not in label

        me.known_ports[unknown] = {"class": "ZZZ", "stock": {}, "last_seen_day": universe.day}
        _replace_snapshot(host, universe)
        page.get_by_test_id("refresh").click()
        page.wait_for_function(
            f"() => document.querySelector('[data-testid=warp-{unknown}]').textContent === 'WARP {unknown} ZZZ'",
            timeout=10_000,
        )
        bare = next((sid for sid in here.warps if sid != unknown and sid not in me.known_ports), None)
        if bare is not None:
            bare_label = page.evaluate(f"() => document.querySelector('[data-testid=warp-{bare}]').textContent")
            assert bare_label == f"WARP {bare}"

        hints = page.evaluate("""() => ({
            scan: getComputedStyle(document.querySelector('[data-testid=action-scan]'), '::after').content,
            warp: getComputedStyle(document.querySelector('#warpBtns button'), '::before').content,
            wide: document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
        })""")
        assert "S" in hints["scan"] and "counter(warpkey)" in hints["warp"] and hints["wide"]
        page.close()


def test_cu_page_stays_one_screen_when_warp_buttons_show_codes(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK + "-cu") as host:
        universe, me = _wait_parked(host)
        for sid in universe.sectors[me.sector_id].warps:
            me.known_ports[sid] = {"class": "BBS", "stock": {}, "last_seen_day": universe.day}
        _replace_snapshot(host, universe)

        page = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        page.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}-cu")
        page.wait_for_selector("[data-testid=cu-turn]", timeout=20_000)
        page.wait_for_function("() => document.querySelector('[data-testid=cu-turn]').textContent.includes('YOUR TURN')", timeout=20_000)
        page.wait_for_function(
            "() => [...document.querySelectorAll('#warpBtns button')].some((b) => b.textContent.endsWith(' BBS'))",
            timeout=15_000,
        )
        fit = page.evaluate("""() => ({
            scroll: document.scrollingElement.scrollHeight,
            wide: document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
            scan: getComputedStyle(document.querySelector('[data-testid=action-scan]'), '::after').content,
            warp: getComputedStyle(document.querySelector('#warpBtns button'), '::before').content,
        })""")
        assert fit["scroll"] <= VIEW_H
        assert fit["wide"] and "S" in fit["scan"] and "counter(cuwarp)" in fit["warp"]
        page.close()


def _move(universe, me, dest: int) -> None:
    universe.sectors[me.sector_id].occupant_ids.remove("P2")
    me.sector_id = dest
    universe.sectors[dest].occupant_ids.append("P2")


def test_sbb_marks_organics_and_equipment_and_an_empty_hold_marks_nothing(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK + "-sbb") as host:
        universe, me = _wait_parked(host)
        dest = next(s for s in universe.sectors.values() if s.port and s.port.code == "SBB")
        _move(universe, me, dest.id)
        me.ship.cargo[Commodity.FUEL_ORE] = 10
        me.ship.cargo[Commodity.ORGANICS] = 5
        me.ship.cargo[Commodity.EQUIPMENT] = 4
        _replace_snapshot(host, universe)

        page = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}-sbb")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_function(
            "() => document.querySelector('[data-testid=port-row-organics]')?.getAttribute('data-can-sell') === 'true'",
            timeout=15_000,
        )
        page.get_by_test_id("mfd-tab-port").click()
        assert page.locator("[data-testid=port-row-equipment]").get_attribute("data-can-sell") == "true"
        assert page.locator("[data-testid=port-row-fuel_ore]").get_attribute("data-can-sell") is None
        assert page.locator("[data-testid=port-row-organics] .can-sell-mark").is_visible()
        assert page.locator("[data-testid=port-row-equipment] .can-sell-mark").is_visible()

        for commodity in (Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT):
            me.ship.cargo[commodity] = 0
        _replace_snapshot(host, universe)
        page.get_by_test_id("refresh").click()
        page.wait_for_function(
            "() => ![...document.querySelectorAll('#portTape tbody tr')].some((r) => r.getAttribute('data-can-sell'))",
            timeout=10_000,
        )
        page.close()


def test_stardock_codes_on_every_neighbour_do_not_overflow(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK + "-sd") as host:
        universe, me = _wait_parked(host)
        warps = list(universe.sectors[me.sector_id].warps)
        assert warps
        bare = warps[-1] if len(warps) > 1 else None
        for sid in warps:
            if sid != bare:
                me.known_ports[sid] = {"class": "STARDOCK", "stock": {}, "last_seen_day": universe.day}
        _replace_snapshot(host, universe)

        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}-sd")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_function(
            "() => [...document.querySelectorAll('#warpBtns button')].some((b) => b.textContent.includes('STARDOCK'))",
            timeout=15_000,
        )
        for width, height in ((1440, 900), (1280, 800)):
            page.set_viewport_size({"width": width, "height": height})
            fit = page.evaluate("""() => ({
                wide: document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
                clipped: [...document.querySelectorAll('#warpBtns button')].some((b) => b.scrollWidth > b.clientWidth + 2),
                scan: getComputedStyle(document.querySelector('[data-testid=action-scan]'), '::after').content,
                warp: getComputedStyle(document.querySelector('#warpBtns button'), '::before').content,
            })""")
            assert fit["wide"] and not fit["clipped"], fit
            assert "S" in fit["scan"] and "counter(warpkey)" in fit["warp"]
        if bare is not None:
            bare_label = page.evaluate(f"() => document.querySelector('[data-testid=warp-{bare}]').textContent")
            assert bare_label == f"WARP {bare}"
        page.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}-sd")
        cu.wait_for_function("() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')", timeout=20_000)
        cu.wait_for_function(
            "() => document.querySelector('#cuTurnCard')?.textContent.includes('STARDOCK')",
            timeout=15_000,
        )
        card = cu.locator("#cuTurnCard").inner_text()
        coded = next(sid for sid in warps if sid != bare)
        assert f"{coded} STARDOCK" in card
        if bare is not None:
            assert f"{bare} STARDOCK" not in card
        fit = cu.evaluate("""() => ({
            scroll: document.scrollingElement.scrollHeight,
            wide: document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
            clipped: [...document.querySelectorAll('#warpBtns button')].some((b) => b.scrollWidth > b.clientWidth + 2),
            scan: getComputedStyle(document.querySelector('[data-testid=action-scan]'), '::after').content,
            warp: getComputedStyle(document.querySelector('#warpBtns button'), '::before').content,
        })""")
        assert fit["scroll"] <= VIEW_H and fit["wide"] and not fit["clipped"], fit
        assert "S" in fit["scan"] and "counter(cuwarp)" in fit["warp"]
        cu.close()
