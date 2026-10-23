"""Playtest 4 (game 668cbeaf at 5b73cb5): cockpit fixes, in the browser.

* A form open at one port no longer freezes the HERE panel after a move.
* A click made while a command waits for the turn joins the queue; only a
  move replaces a queued move (a StarDock purchase is not dropped).
* CIM I/R draw the report the engine sends in the cim_report event.
"""
from __future__ import annotations

import pytest

from tests._cu_host import CuHost

TOK = "playtest4-cockpit-token-p2-0000000000"


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    pw = sync().start()
    host = CuHost(tmp_path_factory.mktemp("pt4"), TOK)
    host.__enter__()
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    try:
        yield {"page": page, "universe": host.runner.state.universe, "host": host}
    finally:
        browser.close()
        host.__exit__(None, None, None)
        pw.stop()


def test_queue_keeps_a_purchase_and_moves_replace_moves(world):
    page = world["page"]
    page.evaluate("() => window.__tw2kTest.setAwaiting(false)")
    page.evaluate("() => window.__tw2kTest.queue('buy_equip', {item: 'fighters', qty: 1}, 'buy 1 fighters')")
    page.evaluate("() => window.__tw2kTest.queue('warp', {target: 2}, 'warp to 2')")
    text = page.locator("#lastResult").inner_text()
    assert "replaces" not in text, text
    assert page.evaluate("() => window.__tw2kTest.queued()") == ["buy_equip", "warp"]
    page.evaluate("() => window.__tw2kTest.queue('warp', {target: 3}, 'warp to 3')")
    assert page.locator("#lastResult").inner_text().endswith("This replaces your queued warp to 2.")
    assert page.evaluate("() => window.__tw2kTest.queued()") == ["buy_equip", "warp"]
    page.evaluate("() => window.__tw2kTest.setAwaiting(true)")
    assert page.evaluate("() => window.__tw2kTest.queued()") == []


def test_cim_report_rows_render(world):
    page = world["page"]
    body = page.evaluate("""() => window.__tw2kTest.cimBody({query: 'R', ports: [
        {sector_id: 7, class: '2', last_seen_day: 3, goods: {fuel_ore: {side: 'buying', qty: 1200, pct: 60}}},
        {sector_id: 9, info: 'unavailable'}]})""")
    assert "Fuel Ore buying 1,200 (60%)" in body and "seen day 3" in body
    assert "report unavailable" in body
    sectors = page.evaluate("() => window.__tw2kTest.cimBody({query: 'I', sectors: [{sector_id: 4, warps: [1, 5]}]})")
    assert "warps 1 - 5" in sectors
    empty = page.evaluate("() => window.__tw2kTest.cimBody({query: 'R', ports: []})")
    assert "No ports in your computer yet." in empty


def test_here_panel_follows_a_move_with_a_form_open(world):
    page, universe = world["page"], world["universe"]
    player = universe.players["P2"]
    start = int(player.sector_id)
    page.keyboard.press("p")
    page.wait_for_selector("#formSlot .frm", timeout=8_000)
    dest = next(int(w) for w in universe.sectors[start].warps if int(w) != start)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    page.evaluate("(d) => window.__tw2kTest.queue('warp', {target: d}, 'warp to ' + d)", dest)
    page.wait_for_function("(d) => document.querySelector('#pSector').textContent === String(d)", arg=dest, timeout=20_000)
    page.wait_for_function("() => !document.querySelector('#formSlot .frm')", timeout=10_000)
