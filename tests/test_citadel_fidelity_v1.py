"""Citadel fidelity: goods are spent, colonists stay, fighters wait for L2."""

from __future__ import annotations

import tw2k.engine.constants as K
from tests.test_citadel_class_tables_v1 import _build, _fill, _land, _plant
from tests.test_phase_abc import _make_universe
from tw2k.agents.llm import citadel_goods_notice
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import Commodity, EventKind, PlanetClass
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import apply_action
from tw2k.engine.victory import _planet_asset_value, planet_stock_unit_price


def _ready(u, *, class_id: PlanetClass = PlanetClass.M, level: int = 0, ore_delta: int = 0, col_delta: int = 0):
    owner = next(iter(u.players.values()))
    planet = _plant(u, owner.id, class_id=class_id, level=level)
    colonists, fuel, organics, equipment, _days = K.citadel_class_cost(class_id.value, level + 1)
    _fill(planet, colonists + col_delta, fuel + ore_delta, organics, equipment)
    _land(u, owner, planet)
    owner.credits = 80_000
    return owner, planet, colonists


def test_cf1_colonists_are_not_consumed() -> None:
    u, _players = _make_universe(seed=71001)
    owner, planet, colonists = _ready(u)
    before = owner.credits
    res = _build(u, owner, planet.id)
    assert res.ok, res.error
    assert sum(planet.colonists.values()) == colonists
    assert owner.credits == before
    assert planet.stockpile[Commodity.FUEL_ORE] == 0
    assert planet.stockpile[Commodity.ORGANICS] == 0
    assert planet.stockpile[Commodity.EQUIPMENT] == 0
    built = next(ev for ev in u.events if ev.kind is EventKind.BUILD_CITADEL)
    assert built.payload["cost_cr"] == 0
    assert built.payload["cost_col"] == 0


def test_cf3_no_credit_charge() -> None:
    u, _players = _make_universe(seed=71003)
    owner, planet, _colonists = _ready(u)
    res = _build(u, owner, planet.id)
    assert res.ok, res.error
    assert owner.credits == 80_000


def test_cf4_days_follow_the_class_table() -> None:
    u, _players = _make_universe(seed=71004)
    owner, planet, _colonists = _ready(u, class_id=PlanetClass.U, level=0)
    _days = K.citadel_class_cost("U", 1)[-1]
    res = _build(u, owner, planet.id)
    assert res.ok, res.error
    assert planet.citadel_complete_day == u.day + _days
    assert _days == 2


def test_cf5_fighters_do_not_defend_before_level_2() -> None:
    u, (owner, attacker, *_) = _make_universe(seed=71005)
    planet = _plant(u, owner.id, class_id=PlanetClass.M, level=1)
    planet.fighters = 40
    planet.shields = 0
    sector = u.sectors[planet.sector_id]
    sector.fighters = None
    attacker.sector_id = planet.sector_id
    attacker.ship.fighters = 15
    u.sectors[planet.sector_id].occupant_ids.append(attacker.id)
    res = apply_action(u, attacker.id, Action(kind=ActionKind.LAND_PLANET, args={"planet_id": planet.id}))
    assert res.ok, res.error
    assert attacker.ship.fighters == 15
    assert planet.fighters == 40
    assert attacker.planet_landed == planet.id


def test_cf5b_level_2_fighters_do_defend() -> None:
    u, (owner, attacker, *_) = _make_universe(seed=71015)
    planet = _plant(u, owner.id, class_id=PlanetClass.M, level=2)
    planet.fighters = 40
    planet.shields = 0
    sector = u.sectors[planet.sector_id]
    sector.fighters = None
    attacker.sector_id = planet.sector_id
    attacker.ship.fighters = 30
    u.sectors[planet.sector_id].occupant_ids.append(attacker.id)
    res = apply_action(u, attacker.id, Action(kind=ActionKind.LAND_PLANET, args={"planet_id": planet.id}))
    assert attacker.ship.fighters < 30 or res.ok is False
    assert planet.fighters < 40


def test_cf6_landed_colonists_join_fuel_production() -> None:
    u, _players = _make_universe(seed=71006)
    owner, planet, _colonists = _ready(u)
    owner.ship.cargo[Commodity.COLONISTS] = 25
    before = int(planet.colonists.get(Commodity.FUEL_ORE, 0))
    idle_before = int(planet.colonists.get(Commodity.COLONISTS, 0))
    res = apply_action(u, owner.id, Action(
        kind=ActionKind.ASSIGN_COLONISTS,
        args={"planet_id": planet.id, "from": "ship", "to": "colonists", "qty": 25},
    ))
    assert res.ok, res.error
    assert planet.colonists.get(Commodity.FUEL_ORE, 0) == before + 25
    assert planet.colonists.get(Commodity.COLONISTS, 0) == idle_before


def test_cf7_exact_ore_is_enough() -> None:
    u, _players = _make_universe(seed=71007)
    owner, planet, _colonists = _ready(u, ore_delta=0)
    res = _build(u, owner, planet.id)
    assert res.ok, res.error


def test_cf8_exact_colonist_count_is_enough() -> None:
    u, _players = _make_universe(seed=71008)
    owner, planet, colonists = _ready(u, col_delta=0)
    assert sum(planet.colonists.values()) == colonists
    res = _build(u, owner, planet.id)
    assert res.ok, res.error
    assert sum(planet.colonists.values()) == colonists


def test_cf9_net_worth_uses_goods_not_the_credit_tier() -> None:
    u, _players = _make_universe(seed=71009)
    _owner, planet, _colonists = _ready(u)
    planet.citadel_level = 1
    planet.citadel_target = 1
    for pool in list(planet.colonists):
        planet.colonists[pool] = 0
    planet.colonists[Commodity.FUEL_ORE] = 1000
    for commodity in list(planet.stockpile):
        planet.stockpile[commodity] = 0
    planet.treasury = 0
    planet.fighters = 0
    planet.shields = 0
    fuel, org, eq = 300, 200, 250
    goods = (
        fuel * planet_stock_unit_price("fuel_ore")
        + org * planet_stock_unit_price("organics")
        + eq * planet_stock_unit_price("equipment")
    )
    credit_tier = 5_000 + 1_000 * K.COLONIST_PRICE
    assert goods != credit_tier
    colonist_value = 1000 * K.COLONIST_PRICE
    assert _planet_asset_value(planet) == goods + colonist_value


def test_cf10_genesis_seed_has_no_idle_pool() -> None:
    u, (owner, *_) = _make_universe(seed=71010)
    owner.ship.genesis = 1
    from tests.test_phase_abc import _first_non_fed_sector
    owner.sector_id = _first_non_fed_sector(u)
    apply_action(u, owner.id, Action(kind=ActionKind.DEPLOY_GENESIS))
    planet = max(u.planets.values(), key=lambda p: p.id)
    assert planet.colonists.get(Commodity.COLONISTS, 0) == 0
    assert sum(planet.colonists.values()) == K.GENESIS_SEED_COLONISTS


def test_cf11_a_shortage_spends_nothing() -> None:
    u, _players = _make_universe(seed=71011)
    owner, planet, colonists = _ready(u)
    planet.stockpile[Commodity.EQUIPMENT] -= 1
    fuel = planet.stockpile[Commodity.FUEL_ORE]
    org = planet.stockpile[Commodity.ORGANICS]
    eq = planet.stockpile[Commodity.EQUIPMENT]
    u.events.clear()
    res = _build(u, owner, planet.id)
    assert res.ok is False
    assert "equipment" in res.error
    assert owner.credits == 80_000
    assert planet.citadel_target == 0
    assert planet.stockpile[Commodity.FUEL_ORE] == fuel
    assert planet.stockpile[Commodity.ORGANICS] == org
    assert planet.stockpile[Commodity.EQUIPMENT] == eq
    assert sum(planet.colonists.values()) == colonists
    assert not any(ev.kind is EventKind.BUILD_CITADEL for ev in u.events)


def test_cf12_legacy_mode_still_charges_credits(monkeypatch) -> None:
    monkeypatch.setattr(K, "CITADEL_FIDELITY_MODE", "legacy")
    u, _players = _make_universe(seed=71012)
    owner, planet, colonists = _ready(u)
    fuel = planet.stockpile[Commodity.FUEL_ORE]
    res = _build(u, owner, planet.id)
    assert res.ok, res.error
    assert owner.credits == 80_000 - 5_000
    assert planet.stockpile[Commodity.FUEL_ORE] == fuel
    assert sum(planet.colonists.values()) == 0


def test_cf13_planet_trade_keeps_the_citadel_goods() -> None:
    from tests.test_planet_trade import _lab, _pt

    u, _sid, _a, planet = _lab(stock=(300, 200, 250))
    planet.colonists[Commodity.FUEL_ORE] = 2500
    blocked = _pt(u, planet_id=900, commodity="equipment", qty=250)
    assert not blocked.ok
    assert planet.stockpile[Commodity.EQUIPMENT] == 250
    planet.stockpile[Commodity.EQUIPMENT] = 300
    sold = _pt(u, planet_id=900, commodity="equipment", qty=50)
    assert sold.ok, sold.error
    assert planet.stockpile[Commodity.EQUIPMENT] == 250


def test_llm_brief_names_the_goods_shortfall() -> None:
    u, _players = _make_universe(seed=71013)
    owner, planet, _colonists = _ready(u)
    planet.stockpile[Commodity.FUEL_ORE] = 0
    obs = build_observation(u, owner.id)
    line = citadel_goods_notice(obs)
    assert "fuel_ore" in line
    assert "build_citadel" in line
