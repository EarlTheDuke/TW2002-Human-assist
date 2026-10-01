"""The spectator leaderboard marks a net worth that moved."""

from __future__ import annotations

import asyncio
import sys

from tests._cu_host import CuHost
from tw2k.engine.models import EventKind

TOK = "lb-trend-v1-token-p2-00000000000000"


def _loop(host: CuHost):
    frame = sys._current_frames().get(host.thread.ident)
    while frame is not None:
        runner = frame.f_locals.get("self")
        loop = getattr(runner, "_loop", None)
        if isinstance(loop, asyncio.AbstractEventLoop) and loop.is_running():
            return loop
        frame = frame.f_back
    raise RuntimeError("match loop not found")


def _shift(host: CuHost, delta: int) -> None:
    loop = _loop(host)

    async def go() -> None:
        universe = host.runner.state.universe
        assert universe is not None
        player = universe.players["P2"]
        player.credits += delta
        universe.emit(
            EventKind.SCAN,
            actor_id="P2",
            sector_id=player.sector_id,
            payload={"tier": "basic"},
            summary="Commander scanned",
        )
        await host.runner._flush_events()

    asyncio.run_coroutine_threadsafe(go(), loop).result(timeout=10)


def _height(page) -> int:
    return page.evaluate("() => document.documentElement.scrollHeight")


def _color(page, direction: str) -> str:
    return page.evaluate(
        """(direction) => getComputedStyle(
          document.querySelector(`.lb-row[data-lb-player="P2"] .lb-trend.${direction}`)
        ).color""",
        direction,
    )


def test_leaderboard_marks_a_net_worth_change(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        assert page.request.post(f"{host.base}/control/pause").ok
        page.goto(f"{host.base}/")
        page.wait_for_selector(".lb-row[data-lb-player=P2] .lb-nw", timeout=20_000)
        quiet = _height(page)
        before = page.locator(".lb-row[data-lb-player=P2] .lb-nw").inner_text()

        _shift(host, 1000)
        page.wait_for_function(
            """(before) => {
              const row = document.querySelector('.lb-row[data-lb-player="P2"]');
              const nw = row.querySelector('.lb-nw').textContent;
              const trend = row.querySelector('.lb-trend');
              return nw !== before && trend && trend.getAttribute('data-trend') === 'up';
            }""",
            arg=before,
            timeout=10_000,
        )
        assert _color(page, "up") == "rgb(121, 255, 176)"
        assert _height(page) == quiet
        mid = page.locator(".lb-row[data-lb-player=P2] .lb-nw").inner_text()

        _shift(host, -2000)
        page.wait_for_function(
            """(mid) => {
              const row = document.querySelector('.lb-row[data-lb-player="P2"]');
              const nw = row.querySelector('.lb-nw').textContent;
              const trend = row.querySelector('.lb-trend');
              return nw !== mid && trend && trend.getAttribute('data-trend') === 'down';
            }""",
            arg=mid,
            timeout=10_000,
        )
        assert _color(page, "down") == "rgb(255, 93, 110)"
        assert _height(page) == quiet
        page.close()

        wide = browser.new_page(viewport={"width": 1920, "height": 1080})
        wide.goto(f"{host.base}/")
        wide.wait_for_selector(".lb-row[data-lb-player=P2] .lb-nw", timeout=20_000)
        tall = _height(wide)
        seen = wide.locator(".lb-row[data-lb-player=P2] .lb-nw").inner_text()
        _shift(host, 500)
        wide.wait_for_function(
            """(seen) => {
              const row = document.querySelector('.lb-row[data-lb-player="P2"]');
              const nw = row.querySelector('.lb-nw').textContent;
              const trend = row.querySelector('.lb-trend');
              return nw !== seen && trend && trend.getAttribute('data-trend') === 'up';
            }""",
            arg=seen,
            timeout=10_000,
        )
        assert _height(wide) == tall
        wide.close()
