"""Completing a citadel adds no free fighters or shields."""

from __future__ import annotations

import tw2k.engine.constants as K
from tests.test_phase_abc import _make_universe
from tw2k.engine.models import EventKind, Planet, PlanetClass
from tw2k.engine.observation import event_facts
from tw2k.engine.planets import _complete_citadels


def _plant(u, level: int, target: int, fighters: int, shields: int) -> Planet:
    sid = next(sector_id for sector_id in u.sectors if sector_id > 10)
    planet = Planet(
        id=88401, sector_id=sid, name="Hold", class_id=PlanetClass.M,
        owner_id="A", citadel_level=level, citadel_target=target,
        citadel_complete_day=u.day, fighters=fighters, shields=shields,
    )
    u.planets[planet.id] = planet
    u.sectors[sid].planet_ids.append(planet.id)
    return planet


def _finish(u, planet: Planet):
    before = (planet.fighters, planet.shields)
    u.events.clear()
    _complete_citadels(u)
    ev = next(event for event in u.events if event.kind is EventKind.CITADEL_COMPLETE)
    assert set(event_facts(ev)) == {"planet_id", "from", "to"}
    assert "fighters" not in ev.payload
    assert "shields" not in ev.payload
    assert "gift" not in ev.summary.lower()
    assert "fighter" not in ev.summary.lower()
    assert "shield" not in ev.summary.lower()
    return before


def test_constants_are_off() -> None:
    assert K.CITADEL_GIFT_FIGHTERS_PER_LEVEL == 0
    assert K.CITADEL_GIFT_SHIELDS_PER_LEVEL == 0
    assert K.CITADEL_TIER_COST == [
        (5_000, 1_000, 1),
        (10_000, 2_000, 1),
        (20_000, 4_000, 2),
        (40_000, 8_000, 2),
        (80_000, 16_000, 3),
        (160_000, 32_000, 4),
    ]


def test_levels_two_through_six_add_nothing() -> None:
    for target in range(2, 7):
        u, _players = _make_universe(seed=18000 + target)
        planet = _plant(u, target - 1, target, 7, 3)
        _finish(u, planet)
        assert planet.citadel_level == target
        assert planet.citadel_complete_day is None
        assert planet.fighters == 7
        assert planet.shields == 3


def test_existing_garrison_stays() -> None:
    u, _players = _make_universe(seed=18010)
    planet = _plant(u, 2, 3, 4000, 800)
    _finish(u, planet)
    assert planet.fighters == 4000
    assert planet.shields == 800


def test_old_gift_returns_when_constants_are_patched(monkeypatch) -> None:
    monkeypatch.setattr(K, "CITADEL_GIFT_FIGHTERS_PER_LEVEL", 1000)
    monkeypatch.setattr(K, "CITADEL_GIFT_SHIELDS_PER_LEVEL", 250)
    u, _players = _make_universe(seed=18020)
    planet = _plant(u, 1, 2, 0, 0)
    _finish(u, planet)
    assert planet.fighters == 2000
    assert planet.shields == 500

    u2, _players = _make_universe(seed=18021)
    rich = _plant(u2, 3, 4, 9000, 2000)
    _finish(u2, rich)
    assert rich.fighters == 9000
    assert rich.shields == 2000

    u3, _players = _make_universe(seed=18022)
    low = _plant(u3, 0, 1, 4, 1)
    _finish(u3, low)
    assert low.citadel_level == 1
    assert low.fighters == 4
    assert low.shields == 1
