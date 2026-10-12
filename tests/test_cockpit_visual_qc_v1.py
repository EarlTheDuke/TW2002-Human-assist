"""cockpit-visual-qc-v1. Pictures of the cockpit at three sizes."""
from __future__ import annotations

import shutil
from pathlib import Path

from tw2k.engine.models import FighterDeployment, FighterMode, ShipClass

from tests._cu_host import CuHost

TOK = "visual-qc-v1-token-p2-00000000000"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "playtests" / "cockpit-visuals-v1"
REF = Path(r"C:\Users\sugar\tw2002_reference\cockpit_assets\screens")
SIZES = ((1920, 1080), (1440, 900), (390, 844))
SCREENS = ("lobby", "deep-space", "docked", "landed", "combat", "death-pod", "mid-video", "visuals-off")


def _advance(page) -> None:
    """Click WAIT and return once that click has a result.

    The next picture's own wait confirms the new observation. Requiring the
    turn banner here races the other seat and hides the combat picture, whose
    challenge disables WAIT.
    """
    page.wait_for_selector("[data-testid=action-wait]:not([disabled])", timeout=20_000)
    previous = page.locator("#lastResult").inner_text()
    page.get_by_test_id("action-wait").click()
    page.wait_for_function(
        "(prev) => (document.querySelector('#lastResult')?.textContent || '') !== prev",
        arg=previous, timeout=20_000,
    )


def _your_turn(page, host) -> None:
    page.wait_for_function(
        """() => {
          const b = document.querySelector('#turnBanner');
          const t = b?.textContent || '';
          return !!(b && (b.classList.contains('turn') || t.includes('GAME OVER') || t.includes('MATCH')));
        }""",
        timeout=45_000,
    )
    banner = page.locator("#turnBanner").inner_text()
    if "YOUR TURN" in banner:
        return
    universe = _universe(host)
    me = universe.players["P2"]
    p2 = [e.summary for e in universe.events if e.actor_id == "P2"][:12]
    raise AssertionError(f"banner={banner!r} day={universe.day} p2={p2}")


def _shot(page, name: str, width: int, height: int) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REF.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}-{width}x{height}.png"
    page.screenshot(path=str(path))
    shutil.copy2(path, REF / path.name)
    assert path.stat().st_size > 5000, path


def _universe(host):
    return host.runner.state.universe


def _place(host, sector_id: int) -> None:
    universe = _universe(host)
    me = universe.players["P2"]
    old = universe.sectors[me.sector_id]
    if "P2" in old.occupant_ids:
        old.occupant_ids.remove("P2")
    me.sector_id = int(sector_id)
    me.planet_landed = None
    me.fighter_challenge = None
    dest = universe.sectors[int(sector_id)]
    if "P2" not in dest.occupant_ids:
        dest.occupant_ids.append("P2")
    me.known_sectors.add(int(sector_id))


def _repark(host) -> int:
    universe = _universe(host)
    dest = next(
        s for s in universe.sectors.values()
        if s.id > 10 and s.port and (s.port.code or "").startswith("B") and "S" in (s.port.code or "")
    )
    _place(host, dest.id)
    return dest.id


def _deep(host) -> int:
    universe = _universe(host)
    sector = next(s for s in universe.sectors.values() if s.id > 10 and s.port is None and not s.planet_ids)
    _place(host, sector.id)
    return sector.id


def _land(host) -> tuple[int, int]:
    universe = _universe(host)
    sector = next(s for s in universe.sectors.values() if s.planet_ids)
    _place(host, sector.id)
    planet_id = int(sector.planet_ids[0])
    universe.players["P2"].planet_landed = planet_id
    return sector.id, planet_id


def _combat_into(universe) -> None:
    """Put the challenge on the observation that is about to be built.

    Setting it earlier lets the day tick send the ship back the way it came,
    and the picture is taken before that challenge is on screen.
    """
    me = universe.players["P2"]
    sector = next(s for s in universe.sectors.values() if s.id > 10 and s.warps and s.port is None)
    old = universe.sectors[me.sector_id]
    if "P2" in old.occupant_ids:
        old.occupant_ids.remove("P2")
    me.sector_id = sector.id
    me.planet_landed = None
    if "P2" not in sector.occupant_ids:
        sector.occupant_ids.append("P2")
    me.known_sectors.add(sector.id)
    sector.fighters = FighterDeployment(owner_id="P1", count=25, mode=FighterMode.DEFENSIVE)
    me.fighter_challenge = {
        "sector_id": sector.id, "from_sector": int(sector.warps[0]), "mode": "defensive",
    }


def _on_next_observation(mutate) -> tuple:
    """Run mutate(universe) inside the next P2 turn's observation build."""
    import tw2k.server.runner as server_runner

    real = server_runner.build_observation

    def wrapped(universe, pid):
        if pid == "P2" and not wrapped.used:
            wrapped.used = True
            mutate(universe)
            server_runner.build_observation = real
        return real(universe, pid)

    wrapped.used = False
    server_runner.build_observation = wrapped
    return server_runner, real


def _pod(host) -> None:
    universe = _universe(host)
    me = universe.players["P2"]
    me.ship.ship_class = ShipClass.ESCAPE_POD
    me.fighter_challenge = None
    universe.sectors[me.sector_id].fighters = None


def test_cockpit_screens_at_three_sizes(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    # Four waits in a row otherwise end the day, and the other seat then plays
    # out the clock before the next picture can be taken.
    import tw2k.server.runner as server_runner
    monkeypatch.setattr(server_runner, "note_wait_streak", lambda *a, **k: 0)
    with CuHost(tmp_path, TOK, max_days=30) as host:
        for width, height in SIZES:
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(f"{host.base}/bot")
            page.wait_for_selector("[data-testid=turn-banner]", timeout=20_000)
            _shot(page, "lobby", width, height)

            page.goto(f"{host.base}/bot?seat=P2&token={TOK}&visuals=0")
            _your_turn(page, host)
            page.wait_for_timeout(400)
            assert page.get_by_test_id("scene-still").is_hidden()
            _shot(page, "visuals-off", width, height)

            page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
            _your_turn(page, host)
            _advance(page)
            dock_id = _repark(host)
            _advance(page)
            page.wait_for_function(
                "(sid) => document.querySelector('#sbSector')?.textContent === String(sid)",
                arg=dock_id, timeout=20_000,
            )
            page.get_by_test_id("mfd-tab-port").click()
            code = page.locator("#portCode").inner_text().strip()
            assert code not in ("", "-", "none"), code
            _shot(page, "docked", width, height)

            deep_id = _deep(host)
            _advance(page)
            page.wait_for_function(
                "(sid) => document.querySelector('#sbSector')?.textContent === String(sid)",
                arg=deep_id, timeout=20_000,
            )
            page.get_by_test_id("map-recenter").click()
            _shot(page, "deep-space", width, height)

            land_sector, land_planet = _land(host)
            _advance(page)
            page.wait_for_function(
                "([sid, pid]) => document.querySelector('#sbSector')?.textContent === String(sid)"
                " && (document.querySelector('#sbLanded')?.textContent || '').includes(String(pid))",
                arg=[land_sector, land_planet], timeout=15_000,
            )
            _shot(page, "landed", width, height)

            server_runner, real_build = _on_next_observation(_combat_into)
            try:
                _advance(page)
                page.wait_for_selector("[data-testid=fighter-challenge]:not([hidden])", timeout=15_000)
                _shot(page, "combat", width, height)
            finally:
                server_runner.build_observation = real_build

            _pod(host)
            _advance(page)
            page.wait_for_function(
                "() => (document.querySelector('#shipClass')?.textContent || '').includes('escape_pod')",
                timeout=15_000,
            )
            _shot(page, "death-pod", width, height)
            page.evaluate(
                """() => {
                  const media = window.TW2KMedia;
                  if (media && media.playEntry) {
                    media.playEntry({clip: "clips/placeholder/ph_dock_port_std_a.webm", caption: "Docking"}, "dock");
                  }
                }"""
            )
            page.wait_for_selector("[data-testid=media-hud]:not([hidden])", timeout=10_000)
            _shot(page, "mid-video", width, height)
            page.close()
    missing = [name for name in SCREENS if not list(OUT.glob(f"{name}-*.png"))]
    assert not missing, missing
