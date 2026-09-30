"""This seat's last action on the video caption, then back to the sector line."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tests._cu_host import VIEW_H, VIEW_W, CuHost

TOK = "last-result-v1-token-p2-000000000000"
MAP_TOP = {1440: 714, 1920: 927}
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-polish-v1"


def _open(page, host) -> None:
    page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
    page.wait_for_selector("#turnBanner.turn", timeout=20_000)
    page.wait_for_function(
        "() => /^Sector /.test(document.querySelector('#vpCaption')?.textContent || '')",
        timeout=15_000,
    )


def _layout(page) -> dict:
    return page.evaluate(
        """() => {
          const tabs = [...document.querySelectorAll('#mfd [role=tab]')].map((t) => t.getBoundingClientRect().top);
          const tabTop = Math.min(...tabs);
          return {
            mapY: document.querySelector('#mapCard').getBoundingClientRect().top,
            mfd: document.querySelector('.mfd-body').getBoundingClientRect().height,
            tabSpread: Math.max(...tabs) - tabTop,
          };
        }"""
    )


def _assert_layout(page, width: int) -> None:
    lay = _layout(page)
    assert abs(lay["mapY"] - MAP_TOP[width]) < 4, lay["mapY"]
    assert abs(lay["mfd"] - 420) < 1
    assert lay["tabSpread"] < 2


def _caption(page) -> str:
    return page.locator("#vpCaption").inner_text()


def _no_private(page) -> None:
    text = _caption(page)
    assert "777701" not in text
    assert "424242" not in text


def _action(request) -> dict:
    return json.loads(request.post_data or "{}").get("action") or {}


def _seq(page) -> int:
    found = re.search(r"seq=(\d+)", page.locator("#turnBanner").inner_text())
    assert found
    return int(found.group(1))


def _reject(page, host) -> None:
    res = page.request.post(
        f"{host.base}/harness/v1/P2/action",
        headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json", "X-TW2K-Seat": "P2"},
        data=json.dumps({"turn_seq": _seq(page), "action": {"kind": "warp", "args": {"target": 999999}}}),
    )
    assert res.ok


def test_last_result_uses_the_caption_then_yields(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    SHOTS.mkdir(parents=True, exist_ok=True)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        posts: list[str] = []
        page.on(
            "request",
            lambda r: posts.append(r.url) if r.method == "POST" and r.url.endswith("/action") else None,
        )
        _open(page, host)
        assert page.locator("#vpCaption").get_attribute("data-result") is None
        _assert_layout(page, 1440)

        page.wait_for_selector("[data-testid=action-scan]:not([disabled])", timeout=15_000)
        with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000) as scan:
            page.keyboard.press("s")
        assert _action(scan.value)["kind"] == "scan"
        page.wait_for_function(
            "() => (document.querySelector('#vpCaption')?.textContent || '').includes('scanned')",
            timeout=15_000,
        )
        shown = _caption(page)
        assert shown in page.locator("[data-testid=last-result]").inner_text()
        _no_private(page)
        _assert_layout(page, 1440)
        page.screenshot(path=str(SHOTS / "after-1440x900-result.png"))
        assert posts == [posts[0]]

        page.wait_for_function(
            """() => {
              const cap = document.querySelector('#vpCaption');
              return cap && !cap.getAttribute('data-result') && /^Sector /.test(cap.textContent || '');
            }""",
            timeout=12_000,
        )
        assert len(posts) == 1

        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        _reject(page, host)
        page.wait_for_function(
            "() => (document.querySelector('#vpCaption')?.textContent || '').includes('no warp')",
            timeout=15_000,
        )
        err = _caption(page)
        assert err in page.locator("[data-testid=last-result]").inner_text()
        _no_private(page)
        _assert_layout(page, 1440)

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
        wide.wait_for_selector("#turnBanner.turn", timeout=20_000)
        wide.wait_for_selector("[data-testid=action-scan]:not([disabled])", timeout=15_000)
        wide.keyboard.press("s")
        wide.wait_for_function(
            "() => (document.querySelector('#vpCaption')?.textContent || '').includes('scanned')",
            timeout=15_000,
        )
        _no_private(wide)
        _assert_layout(wide, 1920)
        wide.screenshot(path=str(SHOTS / "after-1920x1080-result.png"))
        wide.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')",
            timeout=20_000,
        )
        assert cu.evaluate("() => document.scrollingElement.scrollHeight") <= VIEW_H
        assert not cu.locator("#vpCaption").is_visible()
        assert cu.locator("#cuScreen [data-result]").count() == 0
        cu.close()


def test_last_result_caption_holds_in_firefox(tmp_path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as p:
        browser = p.firefox.launch()
        for width, height in ((1440, 900), (1920, 1080)):
            page = browser.new_page(viewport={"width": width, "height": height})
            _open(page, host)
            _assert_layout(page, width)
            page.wait_for_selector("[data-testid=action-scan]:not([disabled])", timeout=15_000)
            page.keyboard.press("s")
            page.wait_for_function(
                "() => (document.querySelector('#vpCaption')?.textContent || '').includes('scanned')",
                timeout=15_000,
            )
            assert _caption(page) in page.locator("[data-testid=last-result]").inner_text()
            _no_private(page)
            _assert_layout(page, width)
            page.close()
        browser.close()
