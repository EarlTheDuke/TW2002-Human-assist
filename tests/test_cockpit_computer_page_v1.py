"""A TradeWars-style computer page, drawn from this seat's own observation."""

from __future__ import annotations

import json
import time

import pytest

from tests._cu_host import VIEW_H, VIEW_W, CuHost
from tw2k.engine.observation import build_observation

TOK = "computer-page-v1-token-p2-000000000"
MAP_TOP = {1440: 714, 1920: 927}


def _wait_parked(host: CuHost):
    deadline = time.time() + 15
    universe = host.runner.state.universe
    me = universe.players["P2"]
    while time.time() < deadline:
        sector = universe.sectors[me.sector_id]
        if me.sector_id > 10 and me.turns_per_day - me.turns_today >= 2 and sector.warps and sector.port:
            return universe, me
        time.sleep(0.05)
    raise AssertionError("seat did not park")


def _serve(host, universe):
    agent = next(a for a in host.runner.state.agents if a.player_id == "P2")
    agent.current_observation = build_observation(universe, "P2")


def _open(page, host) -> None:
    page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
    page.wait_for_selector("#turnBanner.turn", timeout=20_000)
    page.wait_for_selector("#warpBtns button", timeout=15_000)
    page.wait_for_selector("[data-testid=computer-toggle]", timeout=15_000)


def _layout(page) -> dict:
    return page.evaluate(
        """() => {
          const tabs = [...document.querySelectorAll('#mfd [role=tab]')].map((t) => t.getBoundingClientRect().top);
          const btn = document.querySelector('[data-testid=computer-toggle]').getBoundingClientRect();
          const body = document.querySelector('.mfd-body').getBoundingClientRect();
          const readout = document.querySelector('[data-testid=computer-page]');
          const box = readout.getBoundingClientRect();
          const tabTop = Math.min(...tabs);
          return {
            mapY: document.querySelector('#mapCard').getBoundingClientRect().top,
            mfd: body.height,
            tabSpread: Math.max(...tabs) - tabTop,
            buttonAbove: btn.bottom <= tabTop + 2,
            buttonNear: tabTop - btn.top < 40,
            pageInside: readout.hidden || (box.top >= body.top - 1 && box.bottom <= body.bottom + 1 && box.height > 40),
          };
        }"""
    )


def _assert_layout(page, width: int) -> None:
    lay = _layout(page)
    assert abs(lay["mapY"] - MAP_TOP[width]) < 4, lay["mapY"]
    assert abs(lay["mfd"] - 420) < 1
    assert lay["tabSpread"] < 2
    assert lay["buttonAbove"] and lay["buttonNear"]
    assert lay["pageInside"]


def _kv(page, sel: str) -> dict:
    return page.evaluate(
        """(sel) => {
          const el = document.querySelector(sel);
          const out = {};
          el.querySelectorAll('.k').forEach((k, i) => { out[k.textContent] = el.querySelectorAll('.v')[i].textContent; });
          return out;
        }""",
        sel,
    )


def _assert_values(page, unknown: int, remembered: int | None, live_code: str) -> None:
    body = page.get_by_test_id("computer-page").inner_text()
    assert f"Sector  {page.locator('#hereId').inner_text().strip()}" in body
    assert page.locator("#portCode").inner_text().strip() in body
    port_meta = _kv(page, "#portMeta")
    assert f"class {port_meta['Class']}" in body
    ship = _kv(page, "#shipLoadout")
    for key in ("Holds", "Fighters", "Shields", "Genesis"):
        assert ship[key] in body, (key, ship[key], body)
    assert page.locator("#sbCredits").inner_text().strip() in body
    assert page.locator("#sbTurns").inner_text().strip() in body
    cells = page.evaluate(
        """() => [...document.querySelectorAll('#portTape tbody td')].map((td) => (td.childNodes[0] ? td.childNodes[0].textContent : td.textContent).trim())"""
    )
    for text in cells:
        if text and text != "-":
            assert text in body, text
    for label in page.locator("#warpBtns button").all_inner_texts():
        parts = label.split()
        sid = parts[1]
        line = next(row for row in body.splitlines() if row.startswith(f"  {sid} ") or row == f"  {sid}")
        assert sid in line
        if len(parts) > 2:
            assert parts[2] in line
    hidden = next(row for row in body.splitlines() if row.startswith(f"  {unknown} ") or row == f"  {unknown}")
    assert "BBS" not in hidden
    if live_code:
        assert live_code not in hidden
    if remembered is not None:
        shown = next(row for row in body.splitlines() if row.startswith(f"  {remembered}"))
        assert "SSB" in shown
    assert "424242" not in body
    assert "777701" not in body


def _action(request) -> dict:
    return json.loads(request.post_data or "{}").get("action") or {}


def test_computer_page_matches_cards_and_stays_off_the_map(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        universe, me = _wait_parked(host)
        other = universe.players["P1"]
        other.ship.fighters = 424242
        other.credits = 777701
        warps = list(universe.sectors[me.sector_id].warps)
        ported = [sid for sid in warps if universe.sectors[sid].port]
        assert ported
        unknown = ported[0]
        remembered = ported[1] if len(ported) > 1 else None
        live = universe.sectors[unknown].port
        live_code = live.code if live else ""
        me.known_ports.pop(unknown, None)
        other.known_ports[unknown] = {"class": "BBS", "stock": {}, "last_seen_day": universe.day}
        if remembered is not None:
            me.known_ports[remembered] = {"class": "SSB", "stock": {}, "last_seen_day": universe.day}
        _serve(host, universe)

        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.add_init_script(
            "window.__cls = 0;"
            "new PerformanceObserver((list) => {"
            "  for (const e of list.getEntries()) if (!e.hadRecentInput) window.__cls += e.value;"
            "}).observe({type: 'layout-shift', buffered: true});"
        )
        _open(page, host)
        assert page.get_by_test_id("computer-toggle").get_attribute("aria-pressed") == "false"
        assert not page.get_by_test_id("computer-page").is_visible()
        _assert_layout(page, 1440)
        assert page.evaluate("() => window.__cls") < 0.1

        wide = browser.new_page(viewport={"width": 1920, "height": 1080})
        _open(wide, host)
        wide.get_by_test_id("computer-toggle").click()
        wide.wait_for_selector("[data-testid=computer-page]:not([hidden])", timeout=5_000)
        _assert_layout(wide, 1920)
        _assert_values(wide, unknown, remembered, live_code)
        wide.get_by_test_id("computer-toggle").click()
        assert not wide.get_by_test_id("computer-page").is_visible()
        _assert_layout(wide, 1920)
        wide.close()

        page.get_by_test_id("computer-toggle").click()
        page.wait_for_selector("[data-testid=computer-page]:not([hidden])", timeout=5_000)
        _assert_layout(page, 1440)
        _assert_values(page, unknown, remembered, live_code)
        assert page.evaluate("() => sessionStorage.getItem('tw2k_computer_P2')") == "1"

        page.wait_for_selector("[data-testid=action-scan]:not([disabled])", timeout=15_000)
        with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000) as scan:
            page.keyboard.press("s")
        assert _action(scan.value)["kind"] == "scan"
        page.wait_for_selector("#turnBanner:not(.turn)", timeout=15_000)
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_selector("#warpBtns button:not([disabled])", timeout=20_000)
        target = page.locator("#warpBtns button").first.get_attribute("data-target")
        with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000) as warp:
            page.keyboard.press("1")
        got = _action(warp.value)
        assert got["kind"] == "warp" and str(got["args"]["target"]) == target

        page.reload()
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_selector("[data-testid=computer-page]:not([hidden])", timeout=15_000)
        assert page.get_by_test_id("computer-toggle").get_attribute("aria-pressed") == "true"
        page.get_by_test_id("computer-toggle").click()
        assert not page.get_by_test_id("computer-page").is_visible()
        _assert_layout(page, 1440)
        assert page.evaluate("() => sessionStorage.getItem('tw2k_computer_P2')") == "0"
        page.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')",
            timeout=20_000,
        )
        assert cu.evaluate("() => document.scrollingElement.scrollHeight") <= VIEW_H
        assert not cu.get_by_test_id("computer-toggle").is_visible()
        assert not cu.get_by_test_id("computer-page").is_visible()
        assert cu.locator("#cuScreen [data-testid=computer-toggle]").count() == 0
        assert cu.locator("#cuScreen [data-testid=computer-page]").count() == 0


def test_computer_page_holds_in_firefox(tmp_path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as p:
        universe, me = _wait_parked(host)
        other = universe.players["P1"]
        other.ship.fighters = 424242
        other.credits = 777701
        warps = list(universe.sectors[me.sector_id].warps)
        ported = [sid for sid in warps if universe.sectors[sid].port]
        unknown = ported[0]
        remembered = ported[1] if len(ported) > 1 else None
        live = universe.sectors[unknown].port
        live_code = live.code if live else ""
        me.known_ports.pop(unknown, None)
        other.known_ports[unknown] = {"class": "BBS", "stock": {}, "last_seen_day": universe.day}
        if remembered is not None:
            me.known_ports[remembered] = {"class": "SSB", "stock": {}, "last_seen_day": universe.day}
        _serve(host, universe)
        browser = p.firefox.launch()
        for width, height in ((1440, 900), (1920, 1080)):
            page = browser.new_page(viewport={"width": width, "height": height})
            _open(page, host)
            assert not page.get_by_test_id("computer-page").is_visible()
            _assert_layout(page, width)
            page.get_by_test_id("computer-toggle").click()
            page.wait_for_selector("[data-testid=computer-page]:not([hidden])", timeout=5_000)
            _assert_layout(page, width)
            _assert_values(page, unknown, remembered, live_code)
            page.get_by_test_id("computer-toggle").click()
            assert not page.get_by_test_id("computer-page").is_visible()
            page.close()
        browser.close()
