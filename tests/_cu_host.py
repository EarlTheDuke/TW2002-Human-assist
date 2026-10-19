"""Shared helpers for the /bot browser tests (G2 mode=cu, G3 seat claim).

`CuHost` runs the real app + a match on a background thread on a free local
port. The default scan starts at 8050 and skips the reserved live ports.
Heuristic P1, external P2 parked on a two-way trading port with 10 fuel ore. `browser`
yields a Playwright Chromium, or skips when Playwright / the browser binary
is missing.
"""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path

import pytest

from tw2k.engine import GameConfig
from tw2k.engine.models import Commodity
from tw2k.server.app import create_app
from tw2k.server.runner import AgentSpec, MatchSpec

VIEW_W, VIEW_H = 1280, 800

# Nested hosts each saved INFO_MODE and the later __exit__ put back the inner
# value, which was already "legacy". One saved value, restored when the last
# host closes, leaves the mode the suite started with.
_info_depth = 0
_info_saved: str | None = None


def acquire_info_mode(holder) -> None:
    """Set INFO_MODE to legacy while this holder is open."""
    global _info_depth, _info_saved
    import tw2k.engine.constants as K

    if getattr(holder, "_info_held", False):
        return
    if _info_depth == 0:
        _info_saved = K.INFO_MODE
    _info_depth += 1
    holder._info_held = True
    holder._info_mode = _info_saved
    K.INFO_MODE = "legacy"


def release_info_mode(holder) -> None:
    """Restore the mode saved before the first open host, once none remain."""
    global _info_depth, _info_saved
    if not getattr(holder, "_info_held", False):
        return
    holder._info_held = False
    import tw2k.engine.constants as K

    _info_depth -= 1
    if _info_depth <= 0:
        _info_depth = 0
        if _info_saved is not None:
            K.INFO_MODE = _info_saved
        _info_saved = None


# Live games and standing test servers. A scan may use 8038-8040, 8043-8044,
# and 8050-8054. Every other port from 8031 through 8119 is reserved.
# 8037 is a live game. 8058 is the watcher and 8059 is the Commander test.
RESERVED_TEST_PORTS = frozenset().union(
    range(8031, 8038),
    (8041, 8042),
    range(8045, 8050),
    range(8055, 8060),
    range(8060, 8099),
    range(8099, 8120),
)


def free_port(start: int = 8050) -> int:
    from tests._port_lock import claim_ports

    return claim_ports(
        1, low=start, high=start + 200, avoid=set(RESERVED_TEST_PORTS), sequential=True,
    )


class CuHost:
    def __init__(self, tmp: Path, token: str, *, max_days: int = 3, turns_per_day: int = 60,
                 seed: int = 250925, park_at: int | None = None, fuel: int = 10,
                 p1_token: str | None = None, day_seconds: float | None = None) -> None:
        import uvicorn

        self.token = token
        self.p1_token = p1_token
        self.max_days, self.turns_per_day = max_days, turns_per_day
        self.seed, self.park_at, self.fuel = seed, park_at, fuel
        self.day_seconds = day_seconds  # NOTE 60: GameConfig.turn_regen_day_seconds (None = unset)
        self.parked = False  # set once P2 sits on the parking port with its fuel
        self.port = 0
        self.app = create_app(auto_start=False)
        self.runner = self.app.state.runner
        self.runner._saves_root = tmp / "saves"
        self.server = None
        self.thread = None
        self._uvicorn = uvicorn

    async def _start(self) -> None:
        while not self.server.started:
            await asyncio.sleep(0.05)
        await self.runner.start(MatchSpec(
            config=GameConfig(seed=self.seed, universe_size=200, max_days=self.max_days, turns_per_day=self.turns_per_day,
                              starting_credits=50_000,
                              enable_ferrengi=False, enable_planets=True, action_delay_s=0.0,
                              turn_regen_day_seconds=self.day_seconds),
            agents=[
                AgentSpec(player_id="P1", name="HBot", kind="external", external_token=self.p1_token)
                if self.p1_token else
                AgentSpec(player_id="P1", name="HBot", kind="heuristic"),
                AgentSpec(player_id="P2", name="Commander", kind="external", external_token=self.token),
            ],
            action_delay_s=0.1,
            external_timeout_s=600.0,
        ))
        # Park the seat on a two-way trading port with cargo to sell, so the port
        # tape and the quick SELL form are exercised. The first observation may
        # predate the move; tests act once before relying on it.
        while self.runner.state.universe is None or "P2" not in self.runner.state.universe.players:
            await asyncio.sleep(0.02)
        u = self.runner.state.universe
        me = u.players["P2"]
        if self.park_at is not None:
            dest = u.sectors[int(self.park_at)]
        else:
            dest = next(s for s in u.sectors.values() if s.id > 10 and s.port and (s.port.code or "").startswith("B")
                        and "S" in (s.port.code or ""))
        u.sectors[me.sector_id].occupant_ids.remove("P2")
        me.sector_id = dest.id
        dest.occupant_ids.append("P2")
        me.known_sectors.add(dest.id)
        me.ship.cargo[Commodity.FUEL_ORE] = self.fuel
        self.parked = True

    async def _main(self) -> None:
        async def start_logged() -> None:
            try:
                await self._start()
            except Exception:
                import traceback

                traceback.print_exc()
                raise

        task = asyncio.create_task(start_logged())
        await self.server.serve()
        task.cancel()
        await self.runner.stop()

    def __enter__(self) -> CuHost:
        # The cockpit tests drive the free scan and read today's adjacent view: they test the
        # UI, not the scanner rules (SCANNERS_HIDDEN_INFO.md), so the host runs INFO_MODE legacy.
        acquire_info_mode(self)
        # free_port reserves the port across processes before uvicorn binds it.
        self.port = free_port()
        self.server = self._uvicorn.Server(
            self._uvicorn.Config(self.app, host="127.0.0.1", port=self.port, log_level="warning")
        )
        self.thread = threading.Thread(target=lambda: asyncio.run(self._main()), daemon=True)
        self.thread.start()
        deadline = time.time() + 20
        while time.time() < deadline and not self.server.started:
            time.sleep(0.05)
        if not self.server.started:
            release_info_mode(self)
        assert self.server.started, "host did not start"
        deadline = time.time() + 20
        # Wait for the park too: a test that reads the seat's port right after
        # `with CuHost(...)` must see the parking port, not the start sector.
        while time.time() < deadline and not (self.runner.state.universe is not None and self.parked):
            time.sleep(0.1)
        return self

    def __exit__(self, *exc) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=15)
        if self.port:
            from tests._port_lock import release_ports

            release_ports(self.port)
        from tw2k.media.custom_queue import current

        running = current()
        if running is not None:
            running.stop()
        release_info_mode(self)

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"


@pytest.fixture()
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as pw:
        try:
            b = pw.chromium.launch()
        except Exception as exc:  # browser binary not installed
            pytest.skip(f"chromium not available: {exc}")
        yield b
        b.close()


def inside(box: dict | None) -> bool:
    return (bool(box) and box["x"] >= 0 and box["y"] >= 0
            and box["x"] + box["width"] <= VIEW_W + 0.5 and box["y"] + box["height"] <= VIEW_H + 0.5)
