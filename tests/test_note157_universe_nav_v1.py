"""NOTE 157. Extra two-way lanes are 30 percent of the sector count.

The switch stays legacy while it is off, including when V311_PROFILE is "1".
The switch, or V311_PROFILE "v311" alone, adds those lanes on the spanning tree.
A game that sets avg_warps keeps that average either way.
"""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tw2k.engine.models import GameConfig
from tw2k.engine.universe import generate_universe
from tw2k.public.manual import render

pytestmark = pytest.mark.legacy_profile

_N = 100


def _lanes(universe) -> int:
    seen: set[tuple[int, int]] = set()
    for sid, sector in universe.sectors.items():
        for warp in sector.warps:
            pair = tuple(sorted((int(sid), int(warp))))
            seen.add(pair)  # type: ignore[arg-type]
    return len(seen)


def _plain() -> GameConfig:
    return GameConfig(seed=157, universe_size=_N, enable_ferrengi=False, enable_planets=False)


def test_two_way_lanes_fail_off_and_pass_on(monkeypatch) -> None:
    """GAP 1.2. A 100-sector game adds 30 extra two-way lanes, 129 in all.

    Off, the same game aims at average 2.7, which is 135 lanes.
    """
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.two_way_warp_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    assert K.two_way_warp_live() is False

    legacy = _lanes(generate_universe(_plain()))
    assert legacy == int(_N * K.DEFAULT_AVG_WARPS / 2)
    assert legacy != (_N - 1) + int(_N * K.V311_TWO_WAY_WARP_FRACTION)

    monkeypatch.setattr(K, "TWO_WAY_WARP_MODE", "v311")
    switched = generate_universe(_plain())
    assert _lanes(switched) == (_N - 1) + 30
    assert min(len(sector.warps) for sector in switched.sectors.values()) >= 1

    monkeypatch.setattr(K, "TWO_WAY_WARP_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.TWO_WAY_WARP_MODE == "legacy"
    assert _lanes(generate_universe(_plain())) == (_N - 1) + 30

    explicit = GameConfig(
        seed=157, universe_size=_N, enable_ferrengi=False, enable_planets=False, avg_warps=3.0,
    )
    assert "avg_warps" in explicit.model_fields_set
    assert _lanes(generate_universe(explicit)) == int(_N * 3.0 / 2)


def test_manual_names_the_two_way_switch() -> None:
    page = render("Galaxy War Command")
    assert "TWO_WAY_WARP_MODE" in page
    assert "extra lanes are added until the average is about 2.7 warps a sector." in page
