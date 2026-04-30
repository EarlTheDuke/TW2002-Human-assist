from __future__ import annotations

from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.ferrengi import _spawn_ferrengi
from tw2k.server.app import _build_default_spec


def _base_fighters(aggression: int) -> int:
    return 100 + aggression * 300


def _base_shields(aggression: int) -> int:
    return aggression * 50


def _expected_scale(day: int, *, ramp_days: int = 100, min_scale: float = 0.25) -> float:
    progress = min(1.0, max(0.0, day / ramp_days))
    return min_scale + (1.0 - min_scale) * progress


def _spawn_one_at_day(day: int):
    cfg = GameConfig(
        seed=day + 1000,
        universe_size=80,
        enable_ferrengi=False,
        ferrengi_per_day=1,
        ferrengi_strength_ramp_days=100,
        ferrengi_min_strength_scale=0.25,
    )
    u = generate_universe(cfg)
    u.day = day
    _spawn_ferrengi(u)
    return next(iter(u.ferrengi.values()))


def test_ferrengi_spawn_starts_at_min_strength() -> None:
    ferr = _spawn_one_at_day(0)

    scale = _expected_scale(0)
    assert ferr.fighters == int(_base_fighters(ferr.aggression) * scale)
    assert ferr.shields == int(_base_shields(ferr.aggression) * scale)


def test_ferrengi_spawn_ramps_halfway_by_day_50() -> None:
    ferr = _spawn_one_at_day(50)

    # 25% floor + half of the remaining 75% = 62.5%.
    assert ferr.fighters == int(_base_fighters(ferr.aggression) * 0.625)
    assert ferr.shields == int(_base_shields(ferr.aggression) * 0.625)


def test_ferrengi_spawn_reaches_full_strength_by_day_100() -> None:
    ferr = _spawn_one_at_day(100)

    assert ferr.fighters == _base_fighters(ferr.aggression)
    assert ferr.shields == _base_shields(ferr.aggression)


def test_initial_ferrengi_seed_uses_starting_day_ramp() -> None:
    cfg = GameConfig(
        seed=42,
        universe_size=80,
        enable_ferrengi=True,
        ferrengi_strength_ramp_days=100,
        ferrengi_min_strength_scale=0.25,
    )
    u = generate_universe(cfg)

    assert u.ferrengi
    scale = _expected_scale(u.day)
    for ferr in u.ferrengi.values():
        assert ferr.fighters == int(_base_fighters(ferr.aggression) * scale)
        assert ferr.shields == int(_base_shields(ferr.aggression) * scale)


def test_default_spec_accepts_ferrengi_ramp_overrides() -> None:
    spec = _build_default_spec(
        seed=1,
        universe_size=80,
        max_days=10,
        agent_names=None,
        agent_kind="heuristic",
        provider=None,
        model=None,
        num_agents=2,
        ferrengi_strength_ramp_days=75,
        ferrengi_min_strength_scale=0.1,
    )

    assert spec.config.ferrengi_strength_ramp_days == 75
    assert spec.config.ferrengi_min_strength_scale == 0.1
