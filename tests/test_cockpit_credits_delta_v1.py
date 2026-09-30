"""Signed credit change beside this seat's balance."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._cu_host import VIEW_H, VIEW_W, CuHost

TOK = "credits-delta-v1-token-p2-00000000000"
MAP_TOP = {1440: 714, 1920: 927}
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-polish-v1"


def _open(page, host) -> None:
    page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
    page.wait_for_selector("#turnBanner.turn", timeout=20_000)
    page.wait_for_function(
        "() => document.querySelector('[data-testid=credits]')?.textContent !== '-'",
        timeout=15_000,
    )


def _layout(page) -> dict:
    return page.evaluate(
        """() => {
          const tabs = [...document.querySelectorAll('#mfd [role=tab]')].map((t) => t.getBoundingClientRect().top);
          const tabTop = Math.min(...tabs);
          const cell = document.querySelector('#sbCredits').closest('.score').getBoundingClientRect();
          const bar = document.querySelector('#scoreboard').getBoundingClientRect();
          return {
            mapY: document.querySelector('#mapCard').getBoundingClientRect().top,
            mfd: document.querySelector('.mfd-body').getBoundingClientRect().height,
            tabSpread: Math.max(...tabs) - tabTop,
            cellW: cell.width,
            barH: bar.height,
          };
        }"""
    )


def _assert_layout(page, width: int) -> None:
    lay = _layout(page)
    assert abs(lay["mapY"] - MAP_TOP[width]) < 4, lay["mapY"]
    assert abs(lay["mfd"] - 420) < 1
    assert lay["tabSpread"] < 2
    assert abs(lay["cellW"] - 156) < 2
    assert abs(lay["barH"] - 88) < 1


def _action(request) -> dict:
    return json.loads(request.post_data or "{}").get("action") or {}


def _install(page, offset: dict) -> None:
    def handle(route) -> None:
        if offset["n"] is None:
            route.continue_()
            return
        response = route.fetch()
        data = response.json()
        obs = data.get("observation")
        if isinstance(obs, dict) and isinstance(obs.get("credits"), (int, float)):
            obs["credits"] = int(obs["credits"]) + int(offset["n"])
            data["observation"] = obs
        route.fulfill(response=response, json=data)

    page.route("**/observation**", handle)


def _shift(page, offset: dict, amount: int, sign: str, text: str) -> None:
    offset["n"] = amount
    with page.expect_response(lambda r: "/observation" in r.url and r.ok, timeout=15_000):
        page.get_by_test_id("refresh").click()
    page.wait_for_function(
        """(want) => {
          const d = document.querySelector('[data-testid=credits-delta]');
          return d && !d.hidden && d.getAttribute('data-sign') === want.sign && d.textContent === want.text;
        }""",
        arg={"sign": sign, "text": text},
        timeout=10_000,
    )


def test_credits_delta_flashes_inside_the_cell(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    SHOTS.mkdir(parents=True, exist_ok=True)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        posts: list[str] = []
        page.on(
            "request",
            lambda r: posts.append(r.url) if r.method == "POST" and r.url.endswith("/action") else None,
        )
        offset = {"n": None}
        _install(page, offset)
        _open(page, host)
        assert page.get_by_test_id("credits-delta").get_attribute("hidden") is not None
        _assert_layout(page, 1440)
        assert posts == []

        _shift(page, offset, 210, "up", "+210")
        color = page.get_by_test_id("credits-delta").evaluate("el => getComputedStyle(el).color")
        assert color == "rgb(61, 214, 140)"
        _assert_layout(page, 1440)
        page.screenshot(path=str(SHOTS / "after-1440x900-credits.png"))

        _shift(page, offset, 210 - 1500, "down", "-1,500")
        loss = page.get_by_test_id("credits-delta").evaluate("el => getComputedStyle(el).color")
        assert loss == "rgb(255, 107, 138)"
        assert posts == []
        page.wait_for_function(
            "() => document.querySelector('[data-testid=credits-delta]')?.hidden === true",
            timeout=8_000,
        )
        _assert_layout(page, 1440)

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
        page.close()

        wide = browser.new_page(viewport={"width": 1920, "height": 1080})
        wide_offset = {"n": None}
        _install(wide, wide_offset)
        _open(wide, host)
        assert wide.get_by_test_id("credits-delta").get_attribute("hidden") is not None
        _assert_layout(wide, 1920)
        _shift(wide, wide_offset, 210, "up", "+210")
        _assert_layout(wide, 1920)
        wide.screenshot(path=str(SHOTS / "after-1920x1080-credits.png"))
        wide.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')",
            timeout=20_000,
        )
        assert cu.evaluate("() => document.scrollingElement.scrollHeight") <= VIEW_H
        assert not cu.get_by_test_id("credits-delta").is_visible()
        assert cu.locator("#cuScreen [data-testid=credits-delta]").count() == 0
        cu.close()


def test_credits_delta_holds_in_firefox(tmp_path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as p:
        browser = p.firefox.launch()
        for width, height in ((1440, 900), (1920, 1080)):
            page = browser.new_page(viewport={"width": width, "height": height})
            offset = {"n": None}
            _install(page, offset)
            _open(page, host)
            assert page.get_by_test_id("credits-delta").get_attribute("hidden") is not None
            _assert_layout(page, width)
            _shift(page, offset, 210, "up", "+210")
            _assert_layout(page, width)
            page.close()
        browser.close()
