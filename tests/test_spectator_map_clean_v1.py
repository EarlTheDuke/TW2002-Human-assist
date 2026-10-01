"""Spectator map defaults to discovered space and can open the full galaxy."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from tests._cu_host import CuHost
from tw2k.engine.models import EventKind

TOK = "spectator-map-v1-token-p2-000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-polish-v1"

COUNTS = """() => {
  const all = document.querySelectorAll('#sectors-layer > g[data-id]').length;
  const shown = document.querySelectorAll('#sectors-layer > g[data-id]:not(.map-off)').length;
  return {all, shown};
}"""


def _loop(host: CuHost):
    frame = sys._current_frames().get(host.thread.ident)
    while frame is not None:
        runner = frame.f_locals.get("self")
        loop = getattr(runner, "_loop", None)
        if isinstance(loop, asyncio.AbstractEventLoop) and loop.is_running():
            return loop
        frame = frame.f_back
    raise RuntimeError("match loop not found")


def _warp_p2(host: CuHost) -> int:
    loop = _loop(host)

    async def go() -> int:
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
        return dest

    return asyncio.run_coroutine_threadsafe(go(), loop).result(timeout=10)


def test_spectator_map_is_quiet_until_galaxy(tmp_path: Path, browser) -> None:
    errors: list[str] = []
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        paused = page.request.post(f"{host.base}/control/pause")
        assert paused.ok
        page.goto(f"{host.base}/")
        page.wait_for_function(
            """() => {
              const all = document.querySelectorAll('#sectors-layer > g[data-id]').length;
              const shown = document.querySelectorAll('#sectors-layer > g[data-id]:not(.map-off)').length;
              return all > 20 && shown > 0 && shown < all;
            }""",
            timeout=15_000,
        )
        quiet = page.evaluate(COUNTS)
        assert quiet["shown"] < quiet["all"], quiet
        assert page.locator("#miniMap").count() == 1
        assert page.get_by_test_id("map-follow-mode").count() == 1
        assert page.get_by_test_id("toggle-planets").count() == 1
        assert page.get_by_test_id("toggle-ports").count() == 1
        assert page.get_by_test_id("toggle-ferrengi").count() == 1

        dest = _warp_p2(host)
        page.wait_for_function(
            """(dest) => {
              const ring = document.querySelector('[data-testid=follow-ring]');
              const node = document.querySelector('#sectors-layer > g[data-id="' + dest + '"] circle');
              return !!ring && ring.getAttribute('data-player') === 'P2'
                && !!node
                && ring.getAttribute('cx') === node.getAttribute('cx')
                && ring.getAttribute('cy') === node.getAttribute('cy');
            }""",
            arg=str(dest),
            timeout=10_000,
        )
        page.screenshot(path=str(SHOTS / "after-spectator-map-1440x900.png"))

        page.get_by_test_id("galaxy-toggle").click()
        page.wait_for_function(
            """() => {
              const all = document.querySelectorAll('#sectors-layer > g[data-id]').length;
              const shown = document.querySelectorAll('#sectors-layer > g[data-id]:not(.map-off)').length;
              return all > 20 && shown === all;
            }""",
            timeout=10_000,
        )
        full = page.evaluate(COUNTS)
        assert full["shown"] == full["all"]
        assert full["all"] > quiet["shown"]
        page.screenshot(path=str(SHOTS / "after-spectator-map-galaxy-1440x900.png"))
        assert errors == []
        page.close()
