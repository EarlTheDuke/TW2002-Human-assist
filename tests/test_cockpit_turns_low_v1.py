"""Turns Left goes amber at 10 and red, with a mark, at 3."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._cu_host import VIEW_H, VIEW_W, CuHost

TOK = "turns-low-v1-token-p2-00000000000000"
MAP_TOP = {1440: 714, 1920: 927}
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-polish-v1"
AMBER = "rgb(245, 165, 36)"
RED = "rgb(255, 107, 138)"


def _open(page, host) -> None:
    page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
    page.wait_for_selector("#turnBanner.turn", timeout=20_000)
    page.wait_for_function(
        "() => document.querySelector('[data-testid=turns-left]')?.textContent !== '-'",
        timeout=15_000,
    )


def _layout(page) -> dict:
    return page.evaluate(
        """() => {
          const tabs = [...document.querySelectorAll('#mfd [role=tab]')].map((t) => t.getBoundingClientRect().top);
          const tabTop = Math.min(...tabs);
          const cell = document.querySelector('#sbTurns').closest('.score').getBoundingClientRect();
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


def _install(page, turns: dict) -> None:
    def handle(route) -> None:
        if turns["n"] is None:
            route.continue_()
            return
        response = route.fetch()
        data = response.json()
        obs = data.get("observation")
        if isinstance(obs, dict):
            obs["turns_remaining"] = int(turns["n"])
            data["observation"] = obs
        route.fulfill(response=response, json=data)

    page.route("**/observation**", handle)


def _set_turns(page, turns: dict, n: int) -> None:
    turns["n"] = n
    with page.expect_response(lambda r: "/observation" in r.url and r.ok, timeout=15_000):
        page.get_by_test_id("refresh").click()
    page.wait_for_function(
        "(want) => document.querySelector('[data-testid=turns-left]')?.textContent === String(want)",
        arg=n,
        timeout=10_000,
    )


def _mark(page) -> dict:
    return page.evaluate(
        """() => {
          const el = document.querySelector('[data-testid=turns-left]');
          const before = getComputedStyle(el, '::before');
          return {
            text: el.textContent,
            line: el.parentElement.textContent.replace(/\\s+/g, ' ').trim(),
            level: el.getAttribute('data-level'),
            color: getComputedStyle(el).color,
            mark: before.content,
          };
        }"""
    )


def _expect(page, n: int, level, color, mark: str) -> None:
    got = _mark(page)
    per = got["line"].split("/")[-1].strip()
    assert got["text"] == str(n)
    assert got["line"] == f"{n} / {per}"
    assert got["level"] == level
    if color is not None:
        assert got["color"] == color
    else:
        assert got["color"] not in (AMBER, RED)
    assert got["mark"] == mark


def test_turns_left_warns_without_changing_the_text(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    SHOTS.mkdir(parents=True, exist_ok=True)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        posts: list[str] = []
        page.on(
            "request",
            lambda r: posts.append(r.url) if r.method == "POST" and r.url.endswith("/action") else None,
        )
        turns = {"n": None}
        _install(page, turns)
        _open(page, host)
        _assert_layout(page, 1440)
        assert posts == []

        _set_turns(page, turns, 11)
        _expect(page, 11, None, None, "none")
        _assert_layout(page, 1440)

        _set_turns(page, turns, 10)
        _expect(page, 10, "amber", AMBER, "none")
        _assert_layout(page, 1440)

        _set_turns(page, turns, 3)
        _expect(page, 3, "red", RED, '"!"')
        _assert_layout(page, 1440)
        assert posts == []
        page.screenshot(path=str(SHOTS / "after-1440x900-turnslow.png"))

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
        wide_turns = {"n": 3}
        _install(wide, wide_turns)
        _open(wide, host)
        _expect(wide, 3, "red", RED, '"!"')
        _assert_layout(wide, 1920)
        wide.screenshot(path=str(SHOTS / "after-1920x1080-turnslow.png"))
        wide.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')",
            timeout=20_000,
        )
        assert cu.evaluate("() => document.scrollingElement.scrollHeight") <= VIEW_H
        assert cu.locator("#cuScreen [data-testid=turns-left]").count() == 0
        assert cu.locator("[data-testid=turns-left][data-level]").count() == 0
        cu.close()


def test_turns_left_warning_holds_in_firefox(tmp_path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as p:
        browser = p.firefox.launch()
        for width, height in ((1440, 900), (1920, 1080)):
            page = browser.new_page(viewport={"width": width, "height": height})
            turns = {"n": 11}
            _install(page, turns)
            _open(page, host)
            _expect(page, 11, None, None, "none")
            _set_turns(page, turns, 10)
            _expect(page, 10, "amber", AMBER, "none")
            _set_turns(page, turns, 3)
            _expect(page, 3, "red", RED, '"!"')
            _assert_layout(page, width)
            page.close()
        browser.close()
