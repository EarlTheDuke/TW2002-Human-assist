"""A full hold tints the used number without changing the text."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._cu_host import VIEW_H, VIEW_W, CuHost

TOK = "cargo-full-v1-token-p2-0000000000000"
MAP_TOP = {1440: 714, 1920: 927}
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-polish-v1"
AMBER = "rgb(245, 165, 36)"


def _open(page, host) -> None:
    page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
    page.wait_for_selector("#turnBanner.turn", timeout=20_000)
    page.wait_for_selector("[data-testid=hull-holds] .n", timeout=15_000)


def _layout(page) -> dict:
    return page.evaluate(
        """() => {
          const tabs = [...document.querySelectorAll('#mfd [role=tab]')].map((t) => t.getBoundingClientRect().top);
          const tabTop = Math.min(...tabs);
          const bar = document.querySelector('#scoreboard').getBoundingClientRect();
          const holds = document.querySelector('[data-testid=hull-holds]').getBoundingClientRect();
          return {
            mapY: document.querySelector('#mapCard').getBoundingClientRect().top,
            mfd: document.querySelector('.mfd-body').getBoundingClientRect().height,
            tabSpread: Math.max(...tabs) - tabTop,
            barH: bar.height,
            holdsW: holds.width,
          };
        }"""
    )


def _assert_layout(page, width: int, holds_w: float) -> None:
    lay = _layout(page)
    assert abs(lay["mapY"] - MAP_TOP[width]) < 4, lay["mapY"]
    assert abs(lay["mfd"] - 420) < 1
    assert lay["tabSpread"] < 2
    assert abs(lay["barH"] - 88) < 1
    assert abs(lay["holdsW"] - holds_w) < 1


def _action(request) -> dict:
    return json.loads(request.post_data or "{}").get("action") or {}


def _install(page, cargo: dict) -> None:
    def handle(route) -> None:
        if cargo["free"] is None:
            route.continue_()
            return
        response = route.fetch()
        data = response.json()
        obs = data.get("observation")
        ship = obs.get("ship") if isinstance(obs, dict) else None
        if isinstance(ship, dict):
            ship["holds"] = 20
            ship["cargo_free"] = int(cargo["free"])
            held = dict(ship.get("cargo") or {})
            held["fuel_ore"] = 20 - int(cargo["free"])
            held["organics"] = 0
            held["equipment"] = 0
            ship["cargo"] = held
            obs["ship"] = ship
            data["observation"] = obs
        route.fulfill(response=response, json=data)

    page.route("**/observation**", handle)


def _set_free(page, cargo: dict, free: int) -> None:
    cargo["free"] = free
    with page.expect_response(lambda r: "/observation" in r.url and r.ok, timeout=15_000):
        page.get_by_test_id("refresh").click()
    used = 20 - free
    page.wait_for_function(
        "(want) => document.querySelector('[data-testid=hull-holds] .n')?.textContent === want",
        arg=f"{used}/20",
        timeout=10_000,
    )


def _mark(page) -> dict:
    return page.evaluate(
        """() => {
          const row = document.querySelector('[data-testid=hull-holds]');
          const n = row.querySelector('.n');
          return {
            text: n.textContent,
            level: row.getAttribute('data-level'),
            color: getComputedStyle(n).color,
            mark: getComputedStyle(n, '::before').content,
          };
        }"""
    )


def test_full_hold_marks_the_used_number(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    SHOTS.mkdir(parents=True, exist_ok=True)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        posts: list[str] = []
        page.on(
            "request",
            lambda r: posts.append(r.url) if r.method == "POST" and r.url.endswith("/action") else None,
        )
        cargo = {"free": 1}
        _install(page, cargo)
        _open(page, host)
        holds_w = _layout(page)["holdsW"]
        _assert_layout(page, 1440, holds_w)
        got = _mark(page)
        assert got["text"] == "19/20"
        assert got["level"] is None
        assert got["color"] != AMBER
        assert got["mark"] == "none"
        assert posts == []

        _set_free(page, cargo, 0)
        full = _mark(page)
        assert full["text"] == "20/20"
        assert full["level"] == "full"
        assert full["color"] == AMBER
        assert full["mark"] == '"!"'
        _assert_layout(page, 1440, holds_w)
        assert posts == []
        page.screenshot(path=str(SHOTS / "after-1440x900-cargofull.png"))

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
        got_action = _action(warp.value)
        assert got_action["kind"] == "warp" and str(got_action["args"]["target"]) == target
        page.close()

        wide = browser.new_page(viewport={"width": 1920, "height": 1080})
        wide_cargo = {"free": 0}
        _install(wide, wide_cargo)
        _open(wide, host)
        wide_w = _layout(wide)["holdsW"]
        full_w = _mark(wide)
        assert full_w["text"] == "20/20" and full_w["level"] == "full" and full_w["color"] == AMBER
        _assert_layout(wide, 1920, wide_w)
        wide.screenshot(path=str(SHOTS / "after-1920x1080-cargofull.png"))
        wide.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')",
            timeout=20_000,
        )
        assert cu.evaluate("() => document.scrollingElement.scrollHeight") <= VIEW_H
        assert cu.locator("#cuScreen [data-testid=hull-holds]").count() == 0
        assert cu.locator("[data-testid=hull-holds][data-level]").count() == 0
        cu.close()


def test_full_hold_mark_holds_in_firefox(tmp_path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as p:
        browser = p.firefox.launch()
        for width, height in ((1440, 900), (1920, 1080)):
            page = browser.new_page(viewport={"width": width, "height": height})
            cargo = {"free": 1}
            _install(page, cargo)
            _open(page, host)
            holds_w = _layout(page)["holdsW"]
            room = _mark(page)
            assert room["text"] == "19/20" and room["level"] is None and room["mark"] == "none"
            _set_free(page, cargo, 0)
            full = _mark(page)
            assert full["text"] == "20/20" and full["level"] == "full" and full["color"] == AMBER
            assert full["mark"] == '"!"'
            _assert_layout(page, width, holds_w)
            page.close()
        browser.close()
