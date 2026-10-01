"""Hotkey list for this cockpit, drawn from the keys the page already binds."""

from __future__ import annotations

import json

import pytest

from tests._cu_host import VIEW_H, VIEW_W, CuHost

TOK = "keys-help-v1-token-p2-000000000000"
MAP_TOP = {1440: 714, 1920: 927}
BOUND = ["S", "1-9", "H", "?", "Esc", "Enter", "Space"]


def _open(page, host) -> None:
    page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
    page.wait_for_selector("#turnBanner.turn", timeout=20_000)
    page.wait_for_selector("[data-testid=keys-help]", timeout=15_000)


def _layout(page) -> dict:
    return page.evaluate(
        """() => {
          const tabs = [...document.querySelectorAll('#mfd [role=tab]')].map((t) => t.getBoundingClientRect().top);
          const tabTop = Math.min(...tabs);
          const ship = document.querySelector('[data-testid=inst-ship]').getBoundingClientRect();
          const bar = document.querySelector('#scoreboard').getBoundingClientRect();
          return {
            mapY: document.querySelector('#mapCard').getBoundingClientRect().top,
            mfd: document.querySelector('.mfd-body').getBoundingClientRect().height,
            tabSpread: Math.max(...tabs) - tabTop,
            barH: bar.height,
            shipW: ship.width,
          };
        }"""
    )


def _assert_layout(page, width: int) -> None:
    lay = _layout(page)
    assert abs(lay["mapY"] - MAP_TOP[width]) < 4, lay["mapY"]
    assert abs(lay["mfd"] - 420) < 1
    assert lay["tabSpread"] < 2
    assert abs(lay["barH"] - 88) < 1
    assert abs(lay["shipW"] - 230) < 2


def _listed(page) -> list[str]:
    return page.locator("[data-testid=keys-help-overlay] [data-hotkey]").evaluate_all(
        "els => els.map((e) => e.getAttribute('data-hotkey'))"
    )


def _action(request) -> dict:
    return json.loads(request.post_data or "{}").get("action") or {}


def test_keys_overlay_lists_bound_keys_and_stays_off_the_map(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        posts: list[str] = []
        page.on("request", lambda r: posts.append(r.url) if r.method == "POST" and r.url.endswith("/action") else None)
        _open(page, host)
        assert not page.get_by_test_id("keys-help-overlay").is_visible()
        assert page.get_by_test_id("keys-help").get_attribute("aria-expanded") == "false"
        _assert_layout(page, 1440)

        page.get_by_test_id("keys-help").click()
        page.wait_for_selector("[data-testid=keys-help-overlay]:not([hidden])", timeout=5_000)
        assert _listed(page) == BOUND
        page.wait_for_timeout(200)
        assert posts == []
        _assert_layout(page, 1440)
        page.keyboard.press("?")
        assert not page.get_by_test_id("keys-help-overlay").is_visible()
        page.keyboard.press("?")
        page.wait_for_selector("[data-testid=keys-help-overlay]:not([hidden])", timeout=5_000)
        page.keyboard.press("Escape")
        assert not page.get_by_test_id("keys-help-overlay").is_visible()
        assert posts == []

        page.locator("#tokenInput").focus()
        page.keyboard.press("?")
        assert not page.get_by_test_id("keys-help-overlay").is_visible()
        page.locator("#tokenInput").blur()

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
        _open(wide, host)
        _assert_layout(wide, 1920)
        wide.get_by_test_id("keys-help").click()
        wide.wait_for_selector("[data-testid=keys-help-overlay]:not([hidden])", timeout=5_000)
        assert _listed(wide) == BOUND
        _assert_layout(wide, 1920)
        wide.keyboard.press("Escape")
        assert not wide.get_by_test_id("keys-help-overlay").is_visible()
        wide.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')",
            timeout=20_000,
        )
        assert cu.evaluate("() => document.scrollingElement.scrollHeight") <= VIEW_H
        assert not cu.get_by_test_id("keys-help").is_visible()
        assert not cu.get_by_test_id("keys-help-overlay").is_visible()
        assert cu.locator("#cuScreen [data-testid=keys-help]").count() == 0
        assert cu.locator("#cuScreen [data-testid=keys-help-overlay]").count() == 0


def test_keys_overlay_holds_in_firefox(tmp_path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as p:
        browser = p.firefox.launch()
        for width, height in ((1440, 900), (1920, 1080)):
            page = browser.new_page(viewport={"width": width, "height": height})
            _open(page, host)
            assert not page.get_by_test_id("keys-help-overlay").is_visible()
            _assert_layout(page, width)
            page.get_by_test_id("keys-help").click()
            page.wait_for_selector("[data-testid=keys-help-overlay]:not([hidden])", timeout=5_000)
            assert _listed(page) == BOUND
            _assert_layout(page, width)
            page.keyboard.press("Escape")
            assert not page.get_by_test_id("keys-help-overlay").is_visible()
            page.close()
        browser.close()
