"""NOTE 96. Settled Interdictor corrections, and the constants that stay queued.

The special-hull switch stays legacy. The profile turns it on. Rows 131-134 are unused.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tests.test_phase_abc import _first_non_fed_sector, _make_universe
from tests.test_ship_combat_core_v1 import _act, _challenge, _link, _park
from tests.test_v311_fed_ferrengi_gaps_v1 import _live_hulls, _quiet
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import ParkedShip, Ship, ShipClass
from tw2k.engine.runner import apply_action

pytestmark = pytest.mark.legacy_profile

ROOT = Path(__file__).resolve().parents[1]


def test_a_cloaked_landed_or_ported_interdictor_drops_the_well(monkeypatch) -> None:
    u, (pilot, cruiser, _mate) = _make_universe(seed=9601)
    sid = _first_non_fed_sector(u)
    nxt = u.sectors[sid].warps[0]
    _link(u, sid, nxt)
    _quiet(u, sid, nxt)
    _park(u, pilot, sid)
    _park(u, cruiser, sid)
    cruiser.ship.ship_class = ShipClass.INTERDICTOR_CRUISER
    pilot.turns_today = 0

    res = _act(u, pilot.id, ActionKind.WARP, target=nxt)
    assert res.ok, res.error

    _park(u, pilot, sid)
    _live_hulls(monkeypatch)
    res = _act(u, pilot.id, ActionKind.WARP, target=nxt)
    assert not res.ok
    assert res.error == "an Interdictor Cruiser holds this sector"
    assert pilot.sector_id == sid

    cruiser.ship.cloaked = True
    res = _act(u, pilot.id, ActionKind.WARP, target=nxt)
    assert res.ok, res.error
    assert pilot.sector_id == nxt

    _park(u, pilot, sid)
    cruiser.ship.cloaked = False
    cruiser.planet_landed = 1
    res = _act(u, pilot.id, ActionKind.WARP, target=nxt)
    assert res.ok, res.error

    _park(u, pilot, sid)
    cruiser.planet_landed = None
    cruiser.port_visit_sector_id = sid
    res = _act(u, pilot.id, ActionKind.WARP, target=nxt)
    assert res.ok, res.error
    assert pilot.sector_id == nxt


def test_a_parked_interdictor_does_not_hold(monkeypatch) -> None:
    u, (pilot, cruiser, _mate) = _make_universe(seed=9602)
    sid = _first_non_fed_sector(u)
    nxt = u.sectors[sid].warps[0]
    _link(u, sid, nxt)
    _quiet(u, sid, nxt)
    _park(u, pilot, sid)
    _park(u, cruiser, sid)
    cruiser.ship.ship_class = ShipClass.MERCHANT_CRUISER
    hull = Ship(ship_class=ShipClass.INTERDICTOR_CRUISER)
    u.parked_ships[1] = ParkedShip(
        id=1, owner_id=cruiser.id, sector_id=sid, ship=hull, parked_day=u.day,
    )
    pilot.turns_today = 0
    _live_hulls(monkeypatch)
    res = _act(u, pilot.id, ActionKind.WARP, target=nxt)
    assert res.ok, res.error
    assert pilot.sector_id == nxt


def test_a_fighter_retreat_passes_an_interdictor_on_and_off(monkeypatch) -> None:
    u, _owner, ship, home, there = _challenge(9603)
    ic = u.players["C"]
    _park(u, ic, there)
    ic.ship.ship_class = ShipClass.INTERDICTOR_CRUISER
    res = apply_action(u, ship.id, Action(kind=ActionKind.RETREAT, args={}))
    assert res.ok, res.error
    assert ship.sector_id == home

    u, _owner, ship, home, there = _challenge(9604)
    ic = u.players["C"]
    _park(u, ic, there)
    ic.ship.ship_class = ShipClass.INTERDICTOR_CRUISER
    _live_hulls(monkeypatch)
    res = apply_action(u, ship.id, Action(kind=ActionKind.RETREAT, args={}))
    assert res.ok, res.error
    assert ship.sector_id == home
    assert ship.fighter_challenge is None


def test_queued_constants_keep_their_values_and_the_search_note() -> None:
    assert K.FERRENGI_ALIGN_ON_KILL == 10
    assert K.FERRENGI_XP_BY_HULL == {
        K.FERRENGI_HULL_ASSAULT: 50,
        K.FERRENGI_HULL_CRUISER: 100,
        K.FERRENGI_HULL_DREAD: 150,
    }
    assert K.FERRENGAL_QUASAR_FUEL == 10_000
    assert K.FERRENGAL_QUASAR_PCT == 10
    assert K.V311_COURSE_MAX_HOPS == 45
    assert K.GAMEA_COURSE_MAX_HOPS == 20
    assert K.FERRENGI_BAND_STRONG == "more_fighters_than_this_ship"
    assert "UNVERIFIED" in (K.plot_course_hop_limit.__doc__ or "")
    source = (ROOT / "src/tw2k/engine/constants.py").read_text(encoding="utf-8")
    start = source.find('COURSE_MAX_MODE = "legacy"')
    end = source.find("V311_COURSE_MAX_HOPS = 45", start)
    comment = source[start:end]
    for needle in (
        "UNVERIFIED, searched:",
        "docs/playtests/twgs-live/plotted-course-limit.txt",
        "uploads/",
        "Max Course Length=20",
        "Maximum Course Length",
        "No route within 45 warps",
        "n96-course-max",
    ):
        assert needle in comment, needle
    assert source.count("UNVERIFIED, searched:") >= 5
    queue = (ROOT / "docs/plans/live-twgs-test-queue-v1.md").read_text(encoding="utf-8")
    for needle in (
        "FERRENGI_XP_BY_HULL",
        "FERRENGI_ALIGN_ON_KILL",
        "FERRENGAL_QUASAR_FUEL",
        "FERRENGI_BAND_STRONG",
        "V311_COURSE_MAX_HOPS",
        "GameConfig.death_delay",
        "death_delay_days",
        "ceil(R / A)",
        "RULINGS_v311.md",
    ):
        assert needle in queue
    odds = (ROOT / "docs/plans/ship-odds-exchange-v1.md").read_text(encoding="utf-8")
    assert "ceil(R / A)" in odds
    assert "floor(P / D)" in odds
