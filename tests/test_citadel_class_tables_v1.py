"""Class citadel costs stay dark. Credits mode is unchanged."""

from __future__ import annotations

from pathlib import Path

import tw2k.engine.constants as K
from tests.test_phase_abc import _make_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Commodity, EventKind, Planet, PlanetClass
from tw2k.engine.observation import build_observation, event_facts
from tw2k.engine.runner import apply_action

ROOT = Path(__file__).resolve().parents[1]


def _plant(u, owner: str, *, class_id: PlanetClass, level: int) -> Planet:
    sid = next(sector_id for sector_id in u.sectors if sector_id > 10)
    planet = Planet(
        id=88501, sector_id=sid, name="Hold", class_id=class_id,
        owner_id=owner, citadel_level=level, citadel_target=level,
    )
    u.planets[planet.id] = planet
    u.sectors[sid].planet_ids.append(planet.id)
    return planet


def _land(u, player, planet: Planet) -> None:
    here = u.sectors[player.sector_id]
    if player.id in here.occupant_ids:
        here.occupant_ids.remove(player.id)
    player.sector_id = planet.sector_id
    player.planet_landed = planet.id
    player.turns_today = 0
    if player.id not in u.sectors[planet.sector_id].occupant_ids:
        u.sectors[planet.sector_id].occupant_ids.append(player.id)


def _fill(planet: Planet, colonists: int, fuel: int, organics: int, equipment: int) -> None:
    for pool in planet.colonists:
        planet.colonists[pool] = 0
    planet.colonists[Commodity.COLONISTS] = colonists
    planet.stockpile[Commodity.FUEL_ORE] = fuel
    planet.stockpile[Commodity.ORGANICS] = organics
    planet.stockpile[Commodity.EQUIPMENT] = equipment


def _build(u, player, planet_id: int):
    return apply_action(
        u, player.id, Action(kind=ActionKind.BUILD_CITADEL, args={"planet_id": planet_id}),
    )


def test_default_mode_is_credits_and_unmentioned() -> None:
    assert K.CITADEL_COST_MODE == "credits"
    assert K.CITADEL_BUILD_TIME_SCALE == 0.25
    assert set(K.CITADEL_CLASS_COSTS) == {cls.value for cls in PlanetClass}
    prompt = (ROOT / "src" / "tw2k" / "agents" / "prompts.py").read_text(encoding="utf-8")
    app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    for text in (prompt, app):
        assert "CITADEL_COST_MODE" not in text
        assert "CITADEL_CLASS_COSTS" not in text
    runner = (ROOT / "src" / "tw2k" / "engine" / "runner.py").read_text(encoding="utf-8")
    assert "getenv" not in runner
    assert "environ" not in runner


def test_credits_build_does_not_touch_the_stockpile(monkeypatch) -> None:
    monkeypatch.setattr(K, "CITADEL_FIDELITY_MODE", "legacy")
    u, (owner, *_) = _make_universe(seed=19001)
    planet = _plant(u, owner.id, class_id=PlanetClass.M, level=0)
    _fill(planet, 1000, 500, 500, 500)
    _land(u, owner, planet)
    owner.credits = 20_000
    obs = build_observation(u, owner.id)
    home = next(row for row in obs.sector["planets"] if row["id"] == planet.id)
    assert "fuel_ore" not in home["citadel_next_build"]
    assert home["citadel_next_build"]["credits"] == 5_000
    res = _build(u, owner, planet.id)
    assert res.ok, res.error
    assert owner.credits == 15_000
    assert planet.stockpile[Commodity.FUEL_ORE] == 500
    assert planet.citadel_complete_day == u.day + 1
    built = next(ev for ev in u.events if ev.kind is EventKind.BUILD_CITADEL)
    assert built.payload["cost_cr"] == 5_000
    assert built.payload["cost_col"] == 1_000


def test_each_class_charges_level_1_and_level_6(monkeypatch) -> None:
    monkeypatch.setattr(K, "CITADEL_COST_MODE", "class")
    for cls in PlanetClass:
        for level in (1, 6):
            colonists, fuel, organics, equipment, days = K.citadel_class_cost(cls.value, level)
            u, (owner, *_) = _make_universe(seed=19100 + ord(cls.value) + level)
            planet = _plant(u, owner.id, class_id=cls, level=level - 1)
            _fill(planet, colonists, fuel, organics, equipment)
            _land(u, owner, planet)
            owner.credits = 80_000
            before = owner.credits
            u.events.clear()
            res = _build(u, owner, planet.id)
            assert res.ok, (cls.value, level, res.error)
            assert owner.credits == before
            assert planet.citadel_target == level
            assert planet.citadel_complete_day == u.day + days
            assert planet.stockpile[Commodity.FUEL_ORE] == 0
            assert planet.stockpile[Commodity.ORGANICS] == 0
            assert planet.stockpile[Commodity.EQUIPMENT] == 0
            assert sum(planet.colonists.values()) == 0
            built = next(ev for ev in u.events if ev.kind is EventKind.BUILD_CITADEL)
            assert set(event_facts(built)) == {
                "planet_id", "level_target", "completes_day", "cost_cr", "cost_col",
            }
            assert built.payload["cost_cr"] == 0
            assert built.payload["cost_col"] == colonists
            assert "fuel_ore" not in built.payload


def test_a_shortage_charges_nothing(monkeypatch) -> None:
    monkeypatch.setattr(K, "CITADEL_COST_MODE", "class")
    u, (owner, *_) = _make_universe(seed=19200)
    planet = _plant(u, owner.id, class_id=PlanetClass.M, level=0)
    colonists, fuel, organics, equipment, _days = K.citadel_class_cost("M", 1)
    _fill(planet, colonists, fuel, organics, equipment - 1)
    _land(u, owner, planet)
    owner.credits = 80_000
    u.events.clear()
    res = _build(u, owner, planet.id)
    assert res.ok is False
    assert "equipment" in res.error
    assert owner.credits == 80_000
    assert planet.citadel_target == 0
    assert planet.citadel_complete_day is None
    assert planet.stockpile[Commodity.FUEL_ORE] == fuel
    assert planet.stockpile[Commodity.ORGANICS] == organics
    assert planet.stockpile[Commodity.EQUIPMENT] == equipment - 1
    assert sum(planet.colonists.values()) == colonists
    assert not any(ev.kind is EventKind.BUILD_CITADEL for ev in u.events)
    actions = legal_actions(u, owner.id)
    quote = next(row for row in actions if row.kind == ActionKind.BUILD_CITADEL.value)
    assert quote.legal is False
    assert quote.params["next"]["equipment"] == equipment
    assert quote.params["next"]["credits"] == 0


def test_scaled_days_never_drop_below_one() -> None:
    assert K.citadel_build_days(2) == 1
    assert K.citadel_build_days(4) == 1
    assert K.citadel_build_days(8) == 2
    assert K.citadel_build_days(18) == 4
    assert K.citadel_class_cost("L", 1)[-1] == 1
    assert K.citadel_class_cost("U", 1)[-1] == 2
    assert K.citadel_class_cost("H", 6)[-1] == 4
