"""Planet stock price, class caps, and five planets per sector."""

from __future__ import annotations

from tw2k.agents.seat_brain import SeatBrain
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Commodity, Planet, PlanetClass, Player
from tw2k.engine.observation import build_observation
from tw2k.engine.planets import _advance_planets
from tw2k.engine.runner import _bfs_path, apply_action
from tw2k.engine.victory import _planet_asset_value, planet_stock_unit_price

GOODS = (Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT)


def _universe():
    u = generate_universe(GameConfig(
        seed=31, universe_size=90, max_days=3, turns_per_day=200,
        starting_credits=100_000, enable_ferrengi=False, enable_planets=True,
    ))
    for pid, name in (("P1", "Me"), ("P2", "Rival")):
        player = Player(id=pid, name=name, agent_kind="external", sector_id=1, credits=100_000)
        u.players[pid] = player
        u.sectors[1].occupant_ids.append(pid)
    return u


def _move(u, pid: str, sid: int) -> None:
    player = u.players[pid]
    here = u.sectors[player.sector_id]
    here.occupant_ids = [item for item in here.occupant_ids if item != pid]
    player.sector_id = sid
    player.planet_landed = None
    u.sectors[sid].occupant_ids.append(pid)


def _deep_sector(u) -> int:
    for sid in sorted(u.sectors):
        if sid > 10 and len(_bfs_path(u, 1, sid)) >= K.GENESIS_MIN_HOPS_FROM_STARDOCK and not u.sectors[sid].planet_ids:
            return sid
    raise AssertionError("no deep empty sector")


def _lab(class_id: PlanetClass):
    planet = Planet(id=1, sector_id=20, name="Lab", class_id=class_id)
    universe = type("LabUniverse", (), {"planets": {1: planet}})()
    return universe, planet


def _fill_sector(u, sid: int, count: int) -> None:
    for offset in range(count):
        pid = 9001 + offset
        planet = Planet(id=pid, sector_id=sid, name=f"Fill {offset}", class_id=PlanetClass.M)
        u.planets[pid] = planet
        u.sectors[sid].planet_ids.append(pid)


def test_handbook_numbers_are_the_caps() -> None:
    assert K.PLANET_MAX_COLONISTS == {
        "M": 30_000, "K": 40_000, "L": 40_000, "O": 200_000,
        "C": 100_000, "H": 100_000, "U": 3_000,
    }
    assert K.PLANET_MAX_STOCK["M"] == {"fuel_ore": 100_000, "organics": 100_000, "equipment": 100_000}
    assert K.PLANET_MAX_STOCK["K"]["equipment"] == 10_000
    assert K.PLANET_MAX_STOCK["O"]["organics"] == 1_000_000
    assert K.PLANET_MAX_STOCK["H"]["fuel_ore"] == 1_000_000
    assert K.PLANET_MAX_STOCK["C"]["fuel_ore"] == 20_000
    assert K.PLANET_MAX_STOCK["U"]["fuel_ore"] == 10_000
    assert K.PLANETS_PER_SECTOR_CAP == 5


def test_every_class_stays_non_negative_and_inside_the_caps() -> None:
    for class_id in PlanetClass:
        universe, planet = _lab(class_id)
        for good in GOODS:
            planet.colonists[good] = 400
        planet.stockpile[Commodity.ORGANICS] = 80
        _advance_planets(universe)
        total = sum(int(n) for n in planet.colonists.values())
        assert total <= K.PLANET_MAX_COLONISTS[class_id.value]
        assert total >= 1200
        for good in GOODS:
            qty = int(planet.stockpile.get(good, 0))
            assert qty >= 0
            assert qty <= K.PLANET_MAX_STOCK[class_id.value][good.value]


def test_production_and_growth_stop_at_the_cap() -> None:
    for class_id in PlanetClass:
        universe, planet = _lab(class_id)
        cap = K.PLANET_MAX_STOCK[class_id.value]["fuel_ore"]
        planet.stockpile[Commodity.FUEL_ORE] = cap
        planet.colonists[Commodity.FUEL_ORE] = 2_000
        planet.stockpile[Commodity.ORGANICS] = 10
        _advance_planets(universe)
        assert int(planet.stockpile[Commodity.FUEL_ORE]) == cap
        assert int(planet.stockpile[Commodity.ORGANICS]) >= 0

        universe, planet = _lab(class_id)
        colonist_cap = K.PLANET_MAX_COLONISTS[class_id.value]
        planet.colonists[Commodity.COLONISTS] = colonist_cap
        planet.stockpile[Commodity.ORGANICS] = 500
        _advance_planets(universe)
        assert sum(int(n) for n in planet.colonists.values()) == colonist_cap


def test_legacy_mode_still_grows_past_the_cap() -> None:
    previous = K.PLANET_ECONOMY_MODE
    K.PLANET_ECONOMY_MODE = "legacy"
    try:
        universe, planet = _lab(PlanetClass.M)
        planet.stockpile[Commodity.FUEL_ORE] = K.PLANET_MAX_STOCK["M"]["fuel_ore"]
        planet.colonists[Commodity.FUEL_ORE] = 10_000
        _advance_planets(universe)
        assert int(planet.stockpile[Commodity.FUEL_ORE]) > K.PLANET_MAX_STOCK["M"]["fuel_ore"]
    finally:
        K.PLANET_ECONOMY_MODE = previous


def test_sixth_planet_is_refused_and_pays_nothing() -> None:
    u = _universe()
    sid = _deep_sector(u)
    _fill_sector(u, sid, 5)
    _move(u, "P1", sid)
    player = u.players["P1"]
    player.ship.genesis = 1
    credits = player.credits
    turns = player.turns_today
    res = apply_action(u, "P1", Action(kind=ActionKind.DEPLOY_GENESIS, args={}))
    assert res.ok is False
    assert res.error == "sector already holds 5 planets"
    assert player.ship.genesis == 1
    assert player.credits == credits
    assert player.turns_today == turns
    assert len(u.sectors[sid].planet_ids) == 5
    listed = {item.kind: item for item in legal_actions(u, "P1")}["deploy_genesis"]
    assert listed.legal is False
    assert listed.reason == "sector already holds 5 planets"


def test_legacy_mode_allows_a_sixth_planet() -> None:
    previous = K.PLANET_ECONOMY_MODE
    K.PLANET_ECONOMY_MODE = "legacy"
    try:
        u = _universe()
        sid = _deep_sector(u)
        _fill_sector(u, sid, 5)
        _move(u, "P1", sid)
        player = u.players["P1"]
        player.ship.genesis = 1
        res = apply_action(u, "P1", Action(kind=ActionKind.DEPLOY_GENESIS, args={}))
        assert res.ok, res.error
        assert player.ship.genesis == 0
        assert len(u.sectors[sid].planet_ids) == 6
    finally:
        K.PLANET_ECONOMY_MODE = previous


def test_dump_past_the_cap_returns_the_cargo() -> None:
    u = _universe()
    sid = _deep_sector(u)
    planet = Planet(id=42, sector_id=sid, name="Bin", class_id=PlanetClass.M, owner_id="P1")
    cap = K.PLANET_MAX_STOCK["M"]["fuel_ore"]
    planet.stockpile[Commodity.FUEL_ORE] = cap
    u.planets[42] = planet
    u.sectors[sid].planet_ids.append(42)
    _move(u, "P1", sid)
    player = u.players["P1"]
    assert apply_action(u, "P1", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": 42})).ok
    player.ship.cargo[Commodity.FUEL_ORE] = 5
    credits = player.credits
    turns = player.turns_today
    res = apply_action(u, "P1", Action(
        kind=ActionKind.DUMP_PLANET_CARGO,
        args={"planet_id": 42, "commodity": "fuel_ore", "qty": 5},
    ))
    assert res.ok is False
    assert res.error == f"planet fuel_ore cap is {cap}"
    assert player.ship.cargo[Commodity.FUEL_ORE] == 5
    assert int(planet.stockpile[Commodity.FUEL_ORE]) == cap
    assert player.credits == credits
    assert player.turns_today == turns


def test_transwarp_into_a_full_sector_stays_put() -> None:
    u = _universe()
    home = _deep_sector(u)
    away = next(
        sid for sid in sorted(u.sectors)
        if sid != home and sid > 10 and not u.sectors[sid].planet_ids
    )
    planet = Planet(
        id=77, sector_id=home, name="Mover", class_id=PlanetClass.M,
        owner_id="P1", citadel_level=4,
    )
    planet.stockpile[Commodity.FUEL_ORE] = 8_000
    u.planets[77] = planet
    u.sectors[home].planet_ids.append(77)
    _fill_sector(u, away, 5)
    _move(u, "P1", home)
    player = u.players["P1"]
    player.planet_landed = 77
    credits = player.credits
    res = apply_action(u, "P1", Action(
        kind=ActionKind.PLANET_TRANSWARP,
        args={"planet_id": 77, "dest_sector": away},
    ))
    assert res.ok is False
    assert res.error == "sector already holds 5 planets"
    assert planet.sector_id == home
    assert 77 in u.sectors[home].planet_ids
    assert 77 not in u.sectors[away].planet_ids
    assert int(planet.stockpile[Commodity.FUEL_ORE]) == 8_000
    assert player.credits == credits


def test_class_u_unload_stops_at_3000() -> None:
    u = _universe()
    sid = _deep_sector(u)
    planet = Planet(id=32, sector_id=sid, name="U", class_id=PlanetClass.U, owner_id="P1")
    planet.colonists[Commodity.COLONISTS] = 2_953
    u.planets[32] = planet
    u.sectors[sid].planet_ids.append(32)
    _move(u, "P1", sid)
    player = u.players["P1"]
    assert apply_action(u, "P1", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": 32})).ok
    player.ship.cargo[Commodity.COLONISTS] = 75
    listed = {item.kind: item for item in legal_actions(u, "P1")}["assign_colonists"]
    assert listed.params["qty"]["max_by"]["ship"] == 47
    res = apply_action(u, "P1", Action(
        kind=ActionKind.ASSIGN_COLONISTS,
        args={"planet_id": 32, "from": "ship", "to": "colonists", "qty": 47},
    ))
    assert res.ok, res.error
    assert sum(int(n) for n in planet.colonists.values()) == 3_000
    assert player.ship.cargo[Commodity.COLONISTS] == 28
    listed = {item.kind: item for item in legal_actions(u, "P1")}["assign_colonists"]
    assert "ship" not in listed.params["from"]["choices"]
    obs = build_observation(u, "P1").model_dump(mode="json")
    action = SeatBrain(value_allocator=False).decide(obs)
    shipped = action["kind"] == "assign_colonists" and action["args"].get("from") == "ship"
    assert shipped is False


def test_stock_is_priced_at_the_published_base() -> None:
    assert planet_stock_unit_price("fuel_ore") == 26
    assert planet_stock_unit_price("organics") == 56
    assert planet_stock_unit_price("equipment") == 102
    planet = Planet(id=3, sector_id=20, name="Vault", class_id=PlanetClass.M)
    planet.stockpile[Commodity.FUEL_ORE] = 10
    planet.stockpile[Commodity.ORGANICS] = 2
    planet.stockpile[Commodity.EQUIPMENT] = 1
    assert _planet_asset_value(planet) == 10 * 26 + 2 * 56 + 102
    previous = K.PLANET_ECONOMY_MODE
    K.PLANET_ECONOMY_MODE = "legacy"
    try:
        assert planet_stock_unit_price("fuel_ore") == 26
    finally:
        K.PLANET_ECONOMY_MODE = previous
