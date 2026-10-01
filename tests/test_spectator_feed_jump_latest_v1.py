"""Jump to latest returns a scrolled spectator feed to the newest event."""

from __future__ import annotations

import asyncio
import sys

from tests._cu_host import CuHost
from tw2k.engine.models import EventKind

TOK = "feed-jump-latest-v1-token-p2-0000000"


def _loop(host: CuHost):
    frame = sys._current_frames().get(host.thread.ident)
    while frame is not None:
        runner = frame.f_locals.get("self")
        loop = getattr(runner, "_loop", None)
        if isinstance(loop, asyncio.AbstractEventLoop) and loop.is_running():
            return loop
        frame = frame.f_back
    raise RuntimeError("match loop not found")


def _fill_feed(host: CuHost) -> None:
    loop = _loop(host)

    async def go() -> None:
        universe = host.runner.state.universe
        assert universe is not None
        player = universe.players["P2"]
        for n in range(40):
            universe.emit(
                EventKind.WARP,
                actor_id="P2",
                sector_id=player.sector_id,
                payload={"from": player.sector_id, "to": player.sector_id},
                summary=f"Commander held in {player.sector_id} ({n})",
            )
        await host.runner._flush_events()

    asyncio.run_coroutine_threadsafe(go(), loop).result(timeout=10)


def _scroll_height(page) -> int:
    return page.evaluate("() => document.documentElement.scrollHeight")


def test_jump_to_latest_returns_the_scrolled_feed(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/")
        page.wait_for_selector("#eventFeed", timeout=20_000)
        _fill_feed(host)
        page.wait_for_function(
            "() => document.querySelectorAll('#eventFeed li').length >= 20",
            timeout=10_000,
        )
        jump = page.get_by_test_id("feed-jump-latest")
        assert not jump.is_visible()
        quiet = _scroll_height(page)
        page.locator("#eventFeed").evaluate("el => { el.scrollTop = 0 }")
        page.wait_for_function(
            """() => {
              const btn = document.querySelector('[data-testid=feed-jump-latest]');
              return btn && !btn.hidden;
            }""",
            timeout=5_000,
        )
        assert _scroll_height(page) == quiet
        jump.click()
        page.wait_for_function(
            """() => {
              const el = document.getElementById('eventFeed');
              const btn = document.querySelector('[data-testid=feed-jump-latest]');
              const slack = el.scrollHeight - el.clientHeight - el.scrollTop;
              return btn.hidden && slack <= 8;
            }""",
            timeout=5_000,
        )
        page.close()

        wide = browser.new_page(viewport={"width": 1920, "height": 1080})
        wide.goto(f"{host.base}/")
        wide.wait_for_function(
            "() => document.querySelectorAll('#eventFeed li').length >= 20",
            timeout=10_000,
        )
        tall = _scroll_height(wide)
        wide.locator("#eventFeed").evaluate("el => { el.scrollTop = 0 }")
        wide.wait_for_selector("[data-testid=feed-jump-latest]:not([hidden])", timeout=5_000)
        assert _scroll_height(wide) == tall
        wide.close()
