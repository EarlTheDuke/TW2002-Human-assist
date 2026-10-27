"""The growth dividend stays on. Off, a planet's new value pays nothing.

The original has no credit dividend. The recorded games already include this
one, so the switch stays on. The planet panel says so, and it says when
colonists are dying off.
"""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tests.test_phase_abc import _make_universe
from tw2k.engine.models import Commodity, EventKind, Planet, PlanetClass
from tw2k.engine.observation import build_observation
from tw2k.engine.planets import colonist_trend
from tw2k.engine.runner import planet_tax_value, tick_day

pytestmark = pytest.mark.legacy_profile


def test_default_still_pays() -> None:
    assert K.PLANET_DIVIDEND_PAY_MODE == "legacy"
    assert K.planet_dividend_off() is False
    u, owner, planet, payout = _grown(82001)
    tick_day(u)
    assert owner.credits == 1_000 + payout
    assert any(ev.kind is EventKind.PLANET_TAX_PAYOUT for ev in u.events)
    row = _row(u, owner.id, planet.id)
    assert "dividend" not in row
    assert "colonist_trend" not in row


def test_off_pays_nothing_and_says_so(monkeypatch) -> None:
    monkeypatch.setattr(K, "PLANET_DIVIDEND_PAY_MODE", "off")
    u, owner, planet, _payout = _grown(82002)
    tick_day(u)
    assert owner.credits == 1_000
    assert not any(ev.kind is EventKind.PLANET_TAX_PAYOUT for ev in u.events)
    assert planet.last_tax_value == planet_tax_value(planet)
    assert _row(u, owner.id, planet.id)["dividend"] == "none"


def test_live_production_names_the_die_off(monkeypatch) -> None:
    monkeypatch.setattr(K, "PLANET_PROD_MODE", "live")
    assert "die off" in colonist_trend("M", 20_000)
    assert "5% more" in colonist_trend("M", 1_000)


def _grown(seed: int):
    u, (owner, *_) = _make_universe(seed=seed)
    owner.credits = 1_000
    planet = Planet(
        id=8801, sector_id=120, name="DividendMine",
        class_id=PlanetClass.H, owner_id=owner.id,
    )
    planet.colonists[Commodity.FUEL_ORE] = 1_000
    planet.last_tax_value = planet_tax_value(planet)
    u.planets[planet.id] = planet
    gain = 80 * K.COMMODITY_BASE_PRICE["fuel_ore"] + 20 * K.FIGHTER_COST
    return u, owner, planet, int(gain * K.PLANET_VALUE_TAX_RATE)


def _row(u, pid: str, planet_id: int) -> dict:
    obs = build_observation(u, pid).model_dump(mode="json")
    return next(p for p in obs["owned_planets"] if p["id"] == planet_id)
