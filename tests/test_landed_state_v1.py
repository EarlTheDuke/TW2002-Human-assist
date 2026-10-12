"""A landing follows the ship. Legacy keeps the old flag. Live does not.

Live refuses warp, trade, and an executing plot while the ship is still on
the planet. A flag left behind in another sector is dropped, so Terra and
the bank are not told to lift off nine hops away.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tests.test_citadel_class_tables_v1 import _land, _plant
from tests.test_phase_abc import _make_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import PlanetClass
from tw2k.engine.runner import apply_action


def test_legacy_warp_keeps_the_landing() -> None:
    assert K.LANDED_STATE_MODE == "legacy"
    assert K.landed_state_live() is False
    u, owner, planet = _sitting(81401)
    dest = u.sectors[planet.sector_id].warps[0]
    res = _warp(u, owner, dest)
    assert res.ok, res.error
    assert owner.sector_id == dest
    assert owner.planet_landed == planet.id


def test_live_refuses_a_warp_from_the_surface(monkeypatch) -> None:
    monkeypatch.setattr(K, "LANDED_STATE_MODE", "live")
    u, owner, planet = _sitting(81402)
    dest = u.sectors[planet.sector_id].warps[0]
    res = _warp(u, owner, dest)
    assert res.ok is False
    assert res.error == "lift off first"
    assert owner.sector_id == planet.sector_id
    assert owner.planet_landed == planet.id
    plotted = apply_action(u, owner.id, Action(
        kind=ActionKind.PLOT_COURSE, args={"target": dest, "execute": True},
    ))
    assert plotted.ok is False
    assert plotted.error == "lift off first"
    assert owner.sector_id == planet.sector_id
    planned = apply_action(u, owner.id, Action(
        kind=ActionKind.PLOT_COURSE, args={"target": dest, "execute": False},
    ))
    assert planned.ok, planned.error
    assert owner.sector_id == planet.sector_id


def test_live_drops_a_landing_left_in_another_sector(monkeypatch) -> None:
    monkeypatch.setattr(K, "LANDED_STATE_MODE", "live")
    u, owner, planet = _sitting(81403)
    away = u.sectors[planet.sector_id].warps[0]
    _move(u, owner, away)
    owner.planet_landed = planet.id
    warp = next(la for la in legal_actions(u, owner.id) if la.kind == "warp")
    assert warp.legal is True
    assert owner.planet_landed is None
    dest = u.sectors[away].warps[0]
    res = _warp(u, owner, dest)
    assert res.ok, res.error
    assert owner.sector_id == dest
    assert owner.planet_landed is None


def _sitting(seed: int):
    u, _players = _make_universe(seed=seed)
    owner = next(iter(u.players.values()))
    planet = _plant(u, owner.id, class_id=PlanetClass.M, level=0)
    _land(u, owner, planet)
    owner.turns_today = 0
    return u, owner, planet


def _warp(u, owner, dest: int):
    return apply_action(u, owner.id, Action(kind=ActionKind.WARP, args={"target": dest}))


def _move(u, owner, dest: int) -> None:
    here = u.sectors[owner.sector_id]
    if owner.id in here.occupant_ids:
        here.occupant_ids.remove(owner.id)
    owner.sector_id = dest
    if owner.id not in u.sectors[dest].occupant_ids:
        u.sectors[dest].occupant_ids.append(owner.id)
