"""Known space header counts only this seat's known sectors."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._cu_host import VIEW_H, VIEW_W, CuHost
from tests.test_amz6_warp_codes import _replace_snapshot

TOK = "explored-count-v1-token-p2-00000000000"
MAP_TOP = {1440: 714, 1920: 927}
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-polish-v1"


def _open(page, host) -> None:
    page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
    page.wait_for_selector("#turnBanner.turn", timeout=20_000)
    page.wait_for_function(
        "() => (document.querySelector('[data-testid=explored-count]')?.textContent || '').startsWith('Explored ')",
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
            headH: document.querySelector('#mapCard > h2').getBoundingClientRect().height,
          };
        }"""
    )


def _assert_layout(page, width: int) -> None:
    lay = _layout(page)
    assert abs(lay["mapY"] - MAP_TOP[width]) < 4, lay["mapY"]
    assert abs(lay["mfd"] - 420) < 1
    assert lay["tabSpread"] < 2
    assert lay["headH"] < 36, lay["headH"]


def _count(page) -> int:
    text = page.get_by_test_id("explored-count").inner_text().strip()
    assert text.startswith("Explored ")
    return int(text.split()[-1])


def _known(page) -> list[str]:
    return page.evaluate(
        """() => [...document.querySelectorAll('#knownMap .node:not(.stub)')]
          .map((e) => e.getAttribute('data-sector'))"""
    )


def _action(request) -> dict:
    return json.loads(request.post_data or "{}").get("action") or {}


def _forget(host, universe, sid: int) -> None:
    me = universe.players["P2"]
    me.known_sectors.discard(sid)
    if isinstance(me.known_warps, dict):
        me.known_warps.pop(sid, None)
    _replace_snapshot(host, universe)


def test_explored_count_matches_this_seat(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    SHOTS.mkdir(parents=True, exist_ok=True)
    with CuHost(tmp_path, TOK) as host:
        universe = host.runner.state.universe
        other = universe.players["P1"]
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        posts: list[str] = []
        page.on(
            "request",
            lambda r: posts.append(r.url) if r.method == "POST" and r.url.endswith("/action") else None,
        )
        _open(page, host)
        known = _known(page)
        assert _count(page) == len(known) and known
        _assert_layout(page, 1440)
        assert posts == []

        on_map = {int(sid) for sid in known}
        extra = next(sid for sid in universe.sectors if int(sid) not in on_map)
        other.known_sectors.add(extra)
        _replace_snapshot(host, universe)
        page.get_by_test_id("refresh").click()
        page.wait_for_timeout(500)
        assert _count(page) == len(known)
        assert page.locator(f"[data-testid=map-sector-{extra}].node:not(.stub)").count() == 0
        assert posts == []
        page.screenshot(path=str(SHOTS / "after-1440x900-explored.png"))

        page.wait_for_selector("[data-testid=action-scan]:not([disabled])", timeout=15_000)
        with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000) as scan:
            page.keyboard.press("s")
        assert _action(scan.value)["kind"] == "scan"
        page.wait_for_selector("#turnBanner:not(.turn)", timeout=15_000)
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_selector("#warpBtns button:not([disabled])", timeout=20_000)
        target = int(page.locator("#warpBtns button").first.get_attribute("data-target"))
        _forget(host, universe, target)
        page.get_by_test_id("refresh").click()
        page.wait_for_function(
            """(id) => {
              const nodes = [...document.querySelectorAll('#knownMap .node:not(.stub)')];
              return !nodes.some((e) => e.getAttribute('data-sector') === String(id));
            }""",
            arg=target,
            timeout=10_000,
        )
        before = _count(page)
        with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000) as warp:
            page.keyboard.press("1")
        got = _action(warp.value)
        assert got["kind"] == "warp" and int(got["args"]["target"]) == target
        page.wait_for_selector("#turnBanner:not(.turn)", timeout=15_000)
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_function(
            """(want) => (document.querySelector('[data-testid=explored-count]')?.textContent || '') === want""",
            arg=f"Explored {before + 1}",
            timeout=15_000,
        )
        page.close()

        wide = browser.new_page(viewport={"width": 1920, "height": 1080})
        _open(wide, host)
        assert _count(wide) == len(_known(wide))
        _assert_layout(wide, 1920)
        wide.screenshot(path=str(SHOTS / "after-1920x1080-explored.png"))
        wide.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')",
            timeout=20_000,
        )
        assert cu.evaluate("() => document.scrollingElement.scrollHeight") <= VIEW_H
        assert not cu.get_by_test_id("explored-count").is_visible()
        assert cu.locator("#cuScreen [data-testid=explored-count]").count() == 0
        cu.close()


def test_explored_count_holds_in_firefox(tmp_path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as p:
        browser = p.firefox.launch()
        for width, height in ((1440, 900), (1920, 1080)):
            page = browser.new_page(viewport={"width": width, "height": height})
            _open(page, host)
            assert _count(page) == len(_known(page))
            _assert_layout(page, width)
            page.close()
        browser.close()
