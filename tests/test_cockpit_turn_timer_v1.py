"""Countdown bar inside this seat's turn banner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._cu_host import VIEW_H, VIEW_W, CuHost

TOK = "turn-timer-v1-token-p2-000000000000"
MAP_TOP = {1440: 714, 1920: 927}
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-polish-v1"
WINDOW = 600.0


def _open(page, host) -> None:
    page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
    page.wait_for_selector("#turnBanner.turn", timeout=20_000)
    page.wait_for_selector("[data-testid=turn-timer]", timeout=10_000)


def _layout(page) -> dict:
    return page.evaluate(
        """() => {
          const tabs = [...document.querySelectorAll('#mfd [role=tab]')].map((t) => t.getBoundingClientRect().top);
          const tabTop = Math.min(...tabs);
          return {
            mapY: document.querySelector('#mapCard').getBoundingClientRect().top,
            mfd: document.querySelector('.mfd-body').getBoundingClientRect().height,
            tabSpread: Math.max(...tabs) - tabTop,
            banner: document.querySelector('#turnBanner').getBoundingClientRect().height,
          };
        }"""
    )


def _assert_layout(page, width: int) -> None:
    lay = _layout(page)
    assert abs(lay["mapY"] - MAP_TOP[width]) < 4, lay["mapY"]
    assert abs(lay["mfd"] - 420) < 1
    assert lay["tabSpread"] < 2
    assert abs(lay["banner"] - 92) < 2


def _timer(page) -> dict:
    return page.evaluate(
        """() => {
          const bar = document.querySelector('[data-testid=turn-timer]');
          const fill = bar && bar.querySelector('.turn-timer-fill');
          const track = bar ? bar.getBoundingClientRect().width : 0;
          const w = fill ? fill.getBoundingClientRect().width : 0;
          return {
            level: bar ? bar.getAttribute('data-level') : '',
            pct: track ? (w / track) * 100 : 0,
          };
        }"""
    )


def _action(request) -> dict:
    return json.loads(request.post_data or "{}").get("action") or {}


def _install(page, remain: dict) -> None:
    def handle(route) -> None:
        if remain["s"] is None:
            route.continue_()
            return
        response = route.fetch()
        data = response.json()
        ct = data.get("current_turn")
        now = data.get("server_time")
        if isinstance(ct, dict) and isinstance(now, (int, float)) and ct.get("deadline_at"):
            left = float(remain["s"])
            ct["started_at"] = now - (WINDOW - left)
            ct["deadline_at"] = now + left
            data["current_turn"] = ct
        route.fulfill(response=response, json=data)

    page.route("**/status", handle)
    page.route("**/observation**", handle)


def _show(page, remain: dict, seconds: float, level: str) -> dict:
    remain["s"] = seconds
    with page.expect_response(lambda r: "/observation" in r.url and r.ok, timeout=15_000):
        page.get_by_test_id("refresh").click()
    page.wait_for_function(
        "(level) => document.querySelector('[data-testid=turn-timer]')?.getAttribute('data-level') === level",
        arg=level,
        timeout=10_000,
    )
    return _timer(page)


def test_turn_timer_drains_inside_the_banner(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    SHOTS.mkdir(parents=True, exist_ok=True)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        posts: list[str] = []
        page.on(
            "request",
            lambda r: posts.append(r.url) if r.method == "POST" and r.url.endswith("/action") else None,
        )
        remain = {"s": None}
        _install(page, remain)
        _open(page, host)
        assert page.locator("#turnBanner [data-testid=turn-timer]").count() == 1
        first = _timer(page)
        assert first["level"] == "ok"
        assert first["pct"] > 90
        _assert_layout(page, 1440)
        assert posts == []

        amber = _show(page, remain, 45, "amber")
        assert abs(amber["pct"] - (45 / WINDOW) * 100) < 4
        _assert_layout(page, 1440)
        page.screenshot(path=str(SHOTS / "after-1440x900-timer.png"))
        red = _show(page, remain, 10, "red")
        assert red["pct"] < 6
        assert posts == []
        remain["s"] = None

        page.wait_for_selector("[data-testid=action-scan]:not([disabled])", timeout=15_000)
        with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000) as scan:
            page.keyboard.press("s")
        assert _action(scan.value)["kind"] == "scan"
        page.wait_for_selector("#turnBanner:not(.turn)", timeout=15_000)
        assert page.locator("[data-testid=turn-timer]").count() == 0
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_selector("[data-testid=turn-timer]", timeout=10_000)
        page.wait_for_selector("#warpBtns button:not([disabled])", timeout=20_000)
        target = page.locator("#warpBtns button").first.get_attribute("data-target")
        with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000) as warp:
            page.keyboard.press("1")
        got = _action(warp.value)
        assert got["kind"] == "warp" and str(got["args"]["target"]) == target
        page.close()

        wide = browser.new_page(viewport={"width": 1920, "height": 1080})
        wide_remain = {"s": None}
        _install(wide, wide_remain)
        _open(wide, host)
        _assert_layout(wide, 1920)
        _show(wide, wide_remain, 45, "amber")
        _assert_layout(wide, 1920)
        wide.screenshot(path=str(SHOTS / "after-1920x1080-timer.png"))
        wide.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')",
            timeout=20_000,
        )
        assert cu.evaluate("() => document.scrollingElement.scrollHeight") <= VIEW_H
        assert not cu.get_by_test_id("turn-timer").is_visible()
        assert cu.locator("#cuScreen [data-testid=turn-timer]").count() == 0
        cu.close()


def test_turn_timer_holds_in_firefox(tmp_path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as p:
        browser = p.firefox.launch()
        for width, height in ((1440, 900), (1920, 1080)):
            page = browser.new_page(viewport={"width": width, "height": height})
            _open(page, host)
            info = _timer(page)
            assert info["level"] == "ok"
            assert info["pct"] > 90
            assert page.locator("#turnBanner [data-testid=turn-timer]").count() == 1
            _assert_layout(page, width)
            page.close()
        browser.close()
