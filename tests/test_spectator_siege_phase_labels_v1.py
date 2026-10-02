"""Spectator volley log names each siege phase."""

from __future__ import annotations

import asyncio
import sys

from tests._cu_host import CuHost
from tw2k.engine.models import EventKind

TOK = "siege-phase-labels-v1-token-000000"


def _loop(host: CuHost):
    frame = sys._current_frames().get(host.thread.ident)
    while frame is not None:
        runner = frame.f_locals.get("self")
        loop = getattr(runner, "_loop", None)
        if isinstance(loop, asyncio.AbstractEventLoop) and loop.is_running():
            return loop
        frame = frame.f_back
    raise RuntimeError("match loop not found")


def _publish(host: CuHost) -> None:
    loop = _loop(host)

    async def go() -> None:
        universe = host.runner.state.universe
        assert universe is not None
        universe.emit(
            EventKind.COMBAT,
            actor_id="P2",
            sector_id=universe.players["P2"].sector_id,
            payload={
                "exchange_kind": "planet_siege",
                "exchange_max_rounds": 3,
                "vs": "planet",
                "planet_id": 88021,
                "rounds": [
                    {"round": 1, "phase": "shields", "shields_removed": 2, "attacker_fighters_lost": 0,
                     "defender_fighters_lost": 0, "attacker_f_after": 200},
                    {"round": 2, "phase": "offense", "attacker_fighters_lost": 40,
                     "defender_fighters_lost": 20, "attacker_f_after": 160},
                    {"round": 3, "phase": "defense", "attacker_fighters_lost": 30,
                     "defender_fighters_lost": 10, "attacker_f_after": 130},
                ],
            },
            summary="Siege phases",
        )
        await host.runner._flush_events()

    asyncio.run_coroutine_threadsafe(go(), loop).result(timeout=10)


def test_volley_log_names_shields_offense_and_defense(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        assert page.request.post(f"{host.base}/control/pause").ok
        page.goto(f"{host.base}/")
        page.wait_for_selector("#eventFeed", timeout=20_000)
        _publish(host)
        page.wait_for_selector(".combat-rounds [data-phase=defense]", timeout=20_000)
        words = page.locator(".combat-rounds [data-phase]").all_text_contents()
        assert words == ["Shields", "Offense", "Defense"]
        page.close()
