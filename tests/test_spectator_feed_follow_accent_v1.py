"""Followed player's spectator feed lines get a thin color mark."""

from __future__ import annotations

import asyncio
import sys

from tests._cu_host import CuHost
from tw2k.engine.models import EventKind

TOK = "feed-follow-accent-v1-token-p2-0000000"


def _loop(host: CuHost):
    frame = sys._current_frames().get(host.thread.ident)
    while frame is not None:
        runner = frame.f_locals.get("self")
        loop = getattr(runner, "_loop", None)
        if isinstance(loop, asyncio.AbstractEventLoop) and loop.is_running():
            return loop
        frame = frame.f_back
    raise RuntimeError("match loop not found")


def _warp_p2(host: CuHost) -> None:
    loop = _loop(host)

    async def go() -> None:
        universe = host.runner.state.universe
        assert universe is not None
        player = universe.players["P2"]
        src = player.sector_id
        dest = int(universe.sectors[src].warps[0])
        occupants = universe.sectors[src].occupant_ids
        if "P2" in occupants:
            occupants.remove("P2")
        player.sector_id = dest
        if "P2" not in universe.sectors[dest].occupant_ids:
            universe.sectors[dest].occupant_ids.append("P2")
        universe.emit(
            EventKind.WARP,
            actor_id="P2",
            sector_id=dest,
            payload={"from": src, "to": dest},
            summary=f"Commander warped {src} to {dest}",
        )
        await host.runner._flush_events()

    asyncio.run_coroutine_threadsafe(go(), loop).result(timeout=10)


def test_followed_player_events_get_a_color_mark(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        assert page.request.post(f"{host.base}/control/pause").ok
        page.goto(f"{host.base}/")
        page.wait_for_selector("[data-testid=map-follow-mode]", timeout=20_000)
        assert page.locator("[data-filter=combat]").is_checked()
        _warp_p2(host)
        page.wait_for_selector("#eventFeed li[data-actor=P2].follow-accent", timeout=10_000)
        mark = page.evaluate(
            """() => {
              const row = document.querySelector('#eventFeed li[data-actor="P2"].follow-accent');
              const probe = document.createElement('span');
              probe.style.color = row.style.getPropertyValue('--player-color');
              document.body.appendChild(probe);
              const rgb = getComputedStyle(probe).color;
              probe.remove();
              const shadow = getComputedStyle(row).boxShadow;
              const others = [...document.querySelectorAll('#eventFeed li[data-actor]')].filter(
                (el) => el.getAttribute('data-actor') !== 'P2' && el.classList.contains('follow-accent')
              );
              return { shadow, rgb, others: others.length };
            }"""
        )
        assert mark["rgb"] in mark["shadow"], mark
        assert "inset" in mark["shadow"]
        assert mark["others"] == 0

        page.select_option("[data-testid=map-follow-mode]", "all")
        page.wait_for_function(
            "() => document.querySelectorAll('#eventFeed li.follow-accent').length === 0",
            timeout=5_000,
        )
        assert page.locator("[data-filter=combat]").is_checked()
        assert page.evaluate("() => localStorage.getItem('tw2k:eventFilters')") is None

        page.select_option("[data-testid=map-follow-mode]", "follow")
        page.select_option("[data-testid=map-follow-player]", "P2")
        page.wait_for_selector("#eventFeed li[data-actor=P2].follow-accent", timeout=5_000)
        page.close()
