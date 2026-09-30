"""Pause strip on the cockpit video and the spectator page."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from tests._cu_host import VIEW_H, VIEW_W, CuHost
from tw2k.engine.models import EventKind

TOK = "paused-banner-v1-token-p2-00000000000"
MAP_TOP = {1440: 714, 1920: 927}
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-polish-v1"
P2_LINE = "seat P2 disconnected - match paused"
P3_LINE = "seat P3 disconnected - match paused"
PRIVATE = "P3 holds 777701 credits and 424242 fighters"


def _loop(host: CuHost):
    frame = sys._current_frames().get(host.thread.ident)
    while frame is not None:
        runner = frame.f_locals.get("self")
        loop = getattr(runner, "_loop", None)
        if isinstance(loop, asyncio.AbstractEventLoop) and loop.is_running():
            return loop
        frame = frame.f_back
    raise RuntimeError("match loop not found")


def _emit(host: CuHost, actor: str, summary: str) -> None:
    loop = _loop(host)

    async def go() -> None:
        universe = host.runner.state.universe
        assert universe is not None
        dropped = summary.endswith("match paused")
        universe.emit(
            EventKind.OPERATOR_MESSAGE,
            actor_id=actor,
            actor_kind="system",
            payload={"reason": "seat_drop"} if dropped else {"message": "private"},
            summary=summary,
        )
        await host.runner._flush_events()

    asyncio.run_coroutine_threadsafe(go(), loop).result(timeout=10)


def _control(page, host: CuHost, action: str) -> None:
    res = page.request.post(f"{host.base}/control/{action}")
    assert res.ok


def _open(page, host: CuHost) -> None:
    page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
    page.wait_for_selector("#turnBanner.turn", timeout=20_000)


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


def _no_private(page) -> None:
    text = page.get_by_test_id("paused-banner").inner_text()
    assert "777701" not in text
    assert "424242" not in text


def _refresh(page) -> None:
    with page.expect_response(lambda r: "/events?" in r.url and r.ok, timeout=15_000):
        page.get_by_test_id("refresh").click()


def test_paused_banner_follows_status_and_keeps_the_map(browser, tmp_path, monkeypatch) -> None:
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
        assert not page.get_by_test_id("paused-banner").is_visible()
        assert page.locator("#vpScreen [data-testid=paused-banner]").count() == 1
        _assert_layout(page, 1440)

        _control(page, host, "pause")
        page.wait_for_selector("[data-testid=paused-banner]:not([hidden])", timeout=10_000)
        assert page.get_by_test_id("paused-title").inner_text() == "Match paused"
        assert not page.get_by_test_id("paused-reason").is_visible()
        _assert_layout(page, 1440)

        _emit(host, "P3", PRIVATE)
        _emit(host, "P3", P3_LINE)
        _refresh(page)
        assert not page.get_by_test_id("paused-reason").is_visible()
        assert "seat P3" not in page.get_by_test_id("paused-banner").inner_text()
        _no_private(page)

        spec = browser.new_page(viewport={"width": 1440, "height": 900})
        spec.goto(f"{host.base}/")
        spec.wait_for_function(
            """(line) => {
              const reason = document.querySelector('[data-testid=paused-reason]');
              return reason && !reason.hidden && reason.textContent === line;
            }""",
            arg=P3_LINE,
            timeout=10_000,
        )
        _no_private(spec)

        _emit(host, "P2", P2_LINE)
        _refresh(page)
        page.wait_for_function(
            """(line) => document.querySelector('[data-testid=paused-reason]')?.textContent === line""",
            arg=P2_LINE,
            timeout=10_000,
        )
        assert "seat P3" not in page.get_by_test_id("paused-banner").inner_text()
        _no_private(page)
        _assert_layout(page, 1440)
        page.screenshot(path=str(SHOTS / "after-1440x900-paused.png"))
        spec.wait_for_function(
            """(line) => document.querySelector('[data-testid=paused-reason]')?.textContent === line""",
            arg=P2_LINE,
            timeout=10_000,
        )
        _no_private(spec)
        assert posts == []

        _control(page, host, "resume")
        page.wait_for_selector("[data-testid=paused-banner]", state="hidden", timeout=10_000)
        spec.wait_for_selector("[data-testid=paused-banner]", state="hidden", timeout=10_000)
        _assert_layout(page, 1440)
        page.close()
        spec.close()

        wide = browser.new_page(viewport={"width": 1920, "height": 1080})
        _open(wide, host)
        assert not wide.get_by_test_id("paused-banner").is_visible()
        _assert_layout(wide, 1920)
        _control(wide, host, "pause")
        wide.wait_for_function(
            """(line) => document.querySelector('[data-testid=paused-reason]')?.textContent === line""",
            arg=P2_LINE,
            timeout=10_000,
        )
        _no_private(wide)
        _assert_layout(wide, 1920)
        wide.screenshot(path=str(SHOTS / "after-1920x1080-paused.png"))
        _control(wide, host, "resume")
        wide.wait_for_selector("[data-testid=paused-banner]", state="hidden", timeout=10_000)
        wide.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')",
            timeout=20_000,
        )
        _control(cu, host, "pause")
        cu.wait_for_timeout(2_000)
        assert cu.evaluate("() => document.scrollingElement.scrollHeight") <= VIEW_H
        assert not cu.get_by_test_id("paused-banner").is_visible()
        assert cu.locator("#cuScreen [data-testid=paused-banner]").count() == 0
        cu.close()


def test_paused_banner_holds_in_firefox(tmp_path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as p:
        _emit(host, "P3", PRIVATE)
        _emit(host, "P2", P2_LINE)
        browser = p.firefox.launch()
        for width, height in ((1440, 900), (1920, 1080)):
            page = browser.new_page(viewport={"width": width, "height": height})
            _open(page, host)
            assert not page.get_by_test_id("paused-banner").is_visible()
            _assert_layout(page, width)
            _control(page, host, "pause")
            page.wait_for_function(
                """(line) => document.querySelector('[data-testid=paused-reason]')?.textContent === line""",
                arg=P2_LINE,
                timeout=10_000,
            )
            assert "seat P3" not in page.get_by_test_id("paused-banner").inner_text()
            _no_private(page)
            _assert_layout(page, width)
            _control(page, host, "resume")
            page.wait_for_selector("[data-testid=paused-banner]", state="hidden", timeout=10_000)
            page.close()
        browser.close()
