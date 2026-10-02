"""A seized landing does not refresh the spectator planet row."""

from __future__ import annotations

import asyncio
import sys

from tests._cu_host import CuHost
from tw2k.engine.models import EventKind, Planet, PlanetClass

TOK = "siege-planet-patch-v1-token-00000000"
PLANET_ID = 77001
SECTOR = 50


def _loop(host: CuHost):
    frame = sys._current_frames().get(host.thread.ident)
    while frame is not None:
        runner = frame.f_locals.get("self")
        loop = getattr(runner, "_loop", None)
        if isinstance(loop, asyncio.AbstractEventLoop) and loop.is_running():
            return loop
        frame = frame.f_back
    raise RuntimeError("match loop not found")


def _seed(host: CuHost) -> None:
    universe = host.runner.state.universe
    assert universe is not None
    planet = Planet(
        id=PLANET_ID, sector_id=SECTOR, name="SiegeHold",
        class_id=PlanetClass.M, owner_id="P1", corp_ticker="QQ",
        citadel_level=2, citadel_target=2,
    )
    universe.planets[planet.id] = planet
    universe.sectors[SECTOR].planet_ids.append(planet.id)
    universe.players["P2"].corp_ticker = "ACE"


def _seize(host: CuHost) -> None:
    loop = _loop(host)

    async def go() -> None:
        universe = host.runner.state.universe
        assert universe is not None
        planet = universe.planets[PLANET_ID]
        planet.owner_id = "P2"
        planet.corp_ticker = "ACE"
        planet.citadel_level = 1
        universe.emit(
            EventKind.LAND_PLANET,
            actor_id="P2",
            sector_id=SECTOR,
            payload={"planet_id": PLANET_ID, "class": "M", "seized": True},
            summary="Commander landed on SiegeHold — SEIZED!",
        )
        await host.runner._flush_events()

    asyncio.run_coroutine_threadsafe(go(), loop).result(timeout=10)


def _row(page) -> dict:
    return page.evaluate(
        """(id) => {
          const name = "SiegeHold";
          const cardOf = (pid) => {
            const card = document.querySelector(`.player-card[data-pid="${pid}"]`);
            if (!card) return null;
            const hit = [...card.querySelectorAll(".planet-name")].find((el) => el.textContent === name);
            if (!hit) return null;
            const row = hit.closest(".planet-row");
            return {
              owner: pid,
              citadel: row.querySelector(".citadel-chip").textContent,
            };
          };
          return { p1: cardOf("P1"), p2: cardOf("P2"), planetId: id };
        }""",
        PLANET_ID,
    )


def test_seized_landing_leaves_the_planet_row_unchanged(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        assert page.request.post(f"{host.base}/control/pause").ok
        _seed(host)
        page.goto(f"{host.base}/")
        page.wait_for_function(
            """() => [...document.querySelectorAll('.player-card[data-pid="P1"] .planet-name')]
              .some((el) => el.textContent === "SiegeHold")""",
            timeout=20_000,
        )
        quiet = page.evaluate("() => document.documentElement.scrollHeight")
        before = _row(page)
        assert before["p1"] == {"owner": "P1", "citadel": "L2"}
        assert before["p2"] is None

        _seize(host)
        page.wait_for_timeout(600)
        after = _row(page)
        # The universe already has the new owner and the damaged citadel.
        # The public landing event carries planet_id, class, and seized, plus
        # the actor id. It does not carry corp_ticker or citadel_level, and
        # the spectator planet patch list omits LAND_PLANET, so the row stays.
        assert after == before
        assert page.evaluate("() => document.documentElement.scrollHeight") == quiet

        universe = host.runner.state.universe
        assert universe is not None
        ev = next(e for e in universe.events if e.kind is EventKind.LAND_PLANET and e.payload.get("seized"))
        public = {key: value for key, value in ev.payload.items() if not str(key).startswith("_")}
        assert public == {"planet_id": PLANET_ID, "class": "M", "seized": True}
        assert "planet" not in host.runner._state_patch_for(ev)
        assert universe.planets[PLANET_ID].owner_id == "P2"
        assert universe.planets[PLANET_ID].citadel_level == 1
        page.close()
