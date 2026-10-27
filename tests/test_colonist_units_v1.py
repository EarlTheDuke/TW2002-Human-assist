"""NOTE 89. Terra people must not land as handbook colonists on a non-M world.

Live Terra packs 1,000 people in a hold. A take of 30 holds is 30,000 people.
Class M already stores people. A Class C drop of that cargo is 30 handbook
colonists. A remainder is refused. Picking them back up restores the people.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Commodity, Planet, PlanetClass, Player, Ship, ShipClass
from tw2k.engine.observation import build_observation
from tw2k.engine.ship_exit import handle_jettison
from tw2k.engine.victory import _planet_asset_value

pytestmark = pytest.mark.legacy_profile

ROOT = Path(__file__).resolve().parents[1]


def _world():
    u = generate_universe(GameConfig(
        seed=89, universe_size=40, max_days=5, enable_ferrengi=False, enable_planets=True,
    ))
    u.players["P1"] = Player(
        id="P1", name="N1",
        ship=Ship(holds=40, fighters=20, shields=0, ship_class=ShipClass.MERCHANT_CRUISER),
        sector_id=K.STARDOCK_SECTOR, credits=5_000, turns_today=0, alignment=100,
    )
    u.sectors[K.STARDOCK_SECTOR].occupant_ids.append("P1")
    return u


def _act(u, kind, **args):
    return apply_action(u, "P1", Action(kind=ActionKind(kind), args=args))


def _land(u, class_id: PlanetClass) -> Planet:
    sid = 12 if 12 in u.sectors else next(s for s in u.sectors if s != K.STARDOCK_SECTOR)
    pid = int(u.next_planet_id)
    u.next_planet_id = pid + 1
    planet = Planet(
        id=pid, sector_id=sid, name="Colony", class_id=class_id, owner_id="P1", origin="genesis",
    )
    u.planets[pid] = planet
    u.sectors[sid].planet_ids.append(pid)
    player = u.players["P1"]
    if player.id in u.sectors[player.sector_id].occupant_ids:
        u.sectors[player.sector_id].occupant_ids.remove(player.id)
    player.sector_id = sid
    player.planet_landed = pid
    u.sectors[sid].occupant_ids.append(player.id)
    return planet


def _take(u, qty: int):
    assert u.players["P1"].planet_landed is None
    res = _act(u, "terra_colonists", mode="take", qty=qty)
    assert res.ok, res.error
    return res


def test_switch_stays_legacy_until_the_profile(monkeypatch) -> None:
    assert K.COLONIST_UNITS_MODE == "legacy"
    assert K.COLONIST_NW_UNITS_MODE == "legacy"
    assert K.colonist_units_live() is False
    assert K.colonist_nw_units() is False
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.COLONIST_UNITS_MODE == "legacy"
    assert K.COLONIST_NW_UNITS_MODE == "legacy"
    assert K.colonist_units_live() is True
    assert K.colonist_nw_units() is True


def test_thirty_holds_land_as_thirty_on_class_c(monkeypatch) -> None:
    """Live quote: take qty=30 is 30,000 people; the Class C pool gains 30, not 30,000."""
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u = _world()
    _take(u, 30)
    ship = u.players["P1"].ship
    assert ship.cargo[Commodity.COLONISTS] == 30_000
    assert ship.cargo_used == 30
    planet = _land(u, PlanetClass.C)
    partial = _act(
        u, "assign_colonists", planet_id=planet.id, **{"from": "ship", "to": "fuel_ore", "qty": 1_500},
    )
    assert partial.ok is False
    assert partial.error == "colonists move by the thousand"
    assert ship.cargo[Commodity.COLONISTS] == 30_000
    assert sum(planet.colonists.values()) == 0
    listed = {la.kind: la for la in legal_actions(u, "P1")}
    assert listed["assign_colonists"].params["qty"]["max_by"]["ship"] == 30_000
    assert listed["dump_planet_cargo"].params["qty"]["max_by"]["colonists"] == 30_000
    dropped = _act(
        u, "assign_colonists", planet_id=planet.id, **{"from": "ship", "to": "fuel_ore", "qty": 30_000},
    )
    assert dropped.ok, dropped.error
    assert planet.colonists[Commodity.FUEL_ORE] == 30
    assert ship.cargo.get(Commodity.COLONISTS, 0) == 0
    assert ship.cargo_used == 0
    back = _act(
        u, "assign_colonists", planet_id=planet.id, **{"from": "fuel_ore", "to": "ship", "qty": 30},
    )
    assert back.ok, back.error
    assert planet.colonists[Commodity.FUEL_ORE] == 0
    assert ship.cargo[Commodity.COLONISTS] == 30_000
    assert ship.cargo_used == 30
    _act(u, "assign_colonists", planet_id=planet.id, **{"from": "ship", "to": "fuel_ore", "qty": 30_000})
    dumped = _act(u, "load_planet_cargo", planet_id=planet.id, commodity="colonists", qty=30, pool="fuel_ore")
    assert dumped.ok, dumped.error
    assert ship.cargo[Commodity.COLONISTS] == 30_000
    again = _act(u, "dump_planet_cargo", planet_id=planet.id, commodity="colonists", qty=30_000, pool="fuel_ore")
    assert again.ok, again.error
    assert planet.colonists[Commodity.FUEL_ORE] == 30


def test_class_m_still_stores_people(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u = _world()
    _take(u, 30)
    planet = _land(u, PlanetClass.M)
    dropped = _act(
        u, "assign_colonists", planet_id=planet.id, **{"from": "ship", "to": "fuel_ore", "qty": 30_000},
    )
    assert dropped.ok, dropped.error
    assert planet.colonists[Commodity.FUEL_ORE] == 30_000
    assert u.players["P1"].ship.cargo.get(Commodity.COLONISTS, 0) == 0


def test_legacy_drop_stays_one_to_one() -> None:
    assert K.v311_profile() is False
    u = _world()
    _take(u, 30)
    ship = u.players["P1"].ship
    assert ship.cargo[Commodity.COLONISTS] == 30
    assert ship.cargo_used == 30
    planet = _land(u, PlanetClass.C)
    dropped = _act(
        u, "assign_colonists", planet_id=planet.id, **{"from": "ship", "to": "fuel_ore", "qty": 30},
    )
    assert dropped.ok, dropped.error
    assert planet.colonists[Commodity.FUEL_ORE] == 30
    assert "cargo_holds" not in build_observation(u, "P1").ship


def test_holds_and_the_cargo_line_count_thousands(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u = _world()
    _take(u, 30)
    ship = u.players["P1"].ship
    obs = build_observation(u, "P1")
    assert obs.ship["cargo_holds"]["colonists"] == 30
    assert obs.ship["cargo_free"] == 10
    assert "(30 holds)" in obs.action_hint
    ship.cargo[Commodity.COLONISTS] = 2_500
    odd = handle_jettison(u, "P1", Action(kind=ActionKind.JETTISON, args={"commodity": "colonists", "qty": 500}))
    assert odd.ok is False and odd.error == "colonists move by the thousand"
    res = handle_jettison(u, "P1", Action(kind=ActionKind.JETTISON, args={"commodity": "colonists", "qty": 2_000}))
    assert res.ok, res.error
    assert u.players["P1"].alignment == 98
    assert ship.cargo.get(Commodity.COLONISTS, 0) == 500


def test_net_worth_prices_people_as_thousands(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u = _world()
    player = u.players["P1"]
    bare = player.net_worth
    player.ship.cargo[Commodity.COLONISTS] = 30_000
    player.ship.cargo_cost[Commodity.COLONISTS] = 0.0
    assert player.net_worth - bare == 30 * K.COLONIST_PRICE
    planet = Planet(
        id=3, sector_id=12, name="C", class_id=PlanetClass.C, owner_id="P1", origin="genesis",
        colonists={Commodity.COLONISTS: 30},
    )
    assert _planet_asset_value(planet) == 30 * K.COLONIST_PRICE
    monkeypatch.setattr(K, "COLONIST_UNITS_MODE", "legacy")
    monkeypatch.setattr(K, "TERRA_COLONIST_MODE", "live")
    assert K.colonist_units_live() is True  # the profile still turns it on
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "COLONIST_NW_UNITS_MODE", "live")
    monkeypatch.setattr(K, "TERRA_COLONIST_MODE", "live")
    assert K.colonist_units_live() is False
    assert K.colonist_nw_units() is True
    swollen = Planet(
        id=4, sector_id=12, name="C", class_id=PlanetClass.C, owner_id="P1", origin="genesis",
        colonists={Commodity.COLONISTS: 30_000},
    )
    assert _planet_asset_value(swollen) == 30 * K.COLONIST_PRICE


def test_seed_250925_n1_net_worth_stays_under_340k(monkeypatch) -> None:
    """Profile-on 10-day seed 250925. N1's full net worth stays under 340,000.

    NOTE 89 measured this run under 150,000, which caught a non-M landing that
    scored 30 holds as 30,000 colonists. That landing still converts. With the
    economy2 chart forced off, the same profile-on seats finish N1 at 83,688.
    NOTE 112 turns the chart on with the profile. NOTE 150's cabal table then
    takes a first ask inside the printed percent, and N1 sells 606 times and
    ends at 321,290, of which 308,113 is credits. Planet assets are the gap
    between full and public net worth: 1,370 on the one class M world, guarded
    under 20,000. A 30-hold mis-score at COLONIST_PRICE 10 would add about
    300,000 and still fail both ceilings.
    """
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    spec = importlib.util.spec_from_file_location(
        "run_scripted_match_note89", ROOT / "scripts" / "run_scripted_match.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    result = mod.run_match(["N3", "N2", "N1", "H"], seed=250925, days=10, reject_report=30)
    n1 = next(row for row in result["players"].values() if row["seat"] == "N1")
    print(
        f"NOTE89 day-10 N1 net worth {n1['net_worth']} public {n1['public_net_worth']} "
        f"credits {n1['credits']} sells {n1['sells']} "
        f"rej {n1['rejected_validate']}/{n1['rejected_engine']}"
    )
    assert result["days_played"] == 10
    assert n1["exceptions"] == 0
    # Measured this run: 321,290 full, 308,113 credits, planet gap 1,370.
    # 340,000 leaves a little room for the same trade path. 20,000 is the
    # planet-asset guard: the class M world scored 1,370, and a non-M drop
    # scored as people would clear this by itself.
    assert n1["net_worth"] < 340_000
    assert n1["net_worth"] - n1["public_net_worth"] < 20_000


def test_v311_class_m_refuses_a_fraction_of_a_thousand(monkeypatch) -> None:
    """75 people are not a thousand. They must not leave a class M pool, or land back on one."""
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u = _world()
    home = _land(u, PlanetClass.M)
    home.colonists[Commodity.ORGANICS] = 63_000
    home.colonists[Commodity.FUEL_ORE] = 91_000
    refused = _act(u, "load_planet_cargo", planet_id=home.id, commodity="colonists", qty=75, pool="organics")
    assert refused.ok is False
    assert refused.error == "class M colonists move by the thousand"
    assert u.players["P1"].ship.cargo.get(Commodity.COLONISTS, 0) == 0
    assert home.colonists[Commodity.ORGANICS] == 63_000
    to_ship = _act(u, "assign_colonists", planet_id=home.id, **{"from": "organics", "to": "ship", "qty": 75})
    assert to_ship.ok is False and to_ship.error == "class M colonists move by the thousand"
    assert home.colonists[Commodity.ORGANICS] == 63_000
    # A pool-to-pool move is still people already on the world. 75 may shift.
    shifted = _act(u, "assign_colonists", planet_id=home.id, **{"from": "organics", "to": "equipment", "qty": 75})
    assert shifted.ok, shifted.error
    assert home.colonists[Commodity.ORGANICS] == 62_925
    assert home.colonists[Commodity.EQUIPMENT] == 75
    ship = u.players["P1"].ship
    ship.cargo[Commodity.COLONISTS] = 75
    onto = _act(u, "dump_planet_cargo", planet_id=home.id, commodity="colonists", qty=75, pool="fuel_ore")
    assert onto.ok is False and onto.error == "class M colonists move by the thousand"
    assert home.colonists[Commodity.FUEL_ORE] == 91_000
    assert ship.cargo[Commodity.COLONISTS] == 75
    back = _act(u, "assign_colonists", planet_id=home.id, **{"from": "ship", "to": "fuel_ore", "qty": 75})
    assert back.ok is False and back.error == "class M colonists move by the thousand"
    assert home.colonists[Commodity.FUEL_ORE] == 91_000


def test_v311_fraction_on_empty_class_l_says_move_by_thousand(monkeypatch) -> None:
    """75 people in the hold are not a class-cap failure on an empty class L that still has room."""
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u = _world()
    planet = _land(u, PlanetClass.L)
    assert sum(planet.colonists.values()) == 0
    assert K.planet_colonist_cap("L") == 40_000
    ship = u.players["P1"].ship
    ship.cargo[Commodity.COLONISTS] = 75
    listed = {la.kind: la for la in legal_actions(u, "P1")}
    assert listed["dump_planet_cargo"].legal is False
    assert listed["dump_planet_cargo"].reason == K.COLONIST_MOVE_BY_THOUSAND
    assert listed["assign_colonists"].legal is False
    assert listed["assign_colonists"].reason == K.COLONIST_MOVE_BY_THOUSAND
    assert "cap" not in listed["dump_planet_cargo"].reason
    assert "40000" not in listed["assign_colonists"].reason
    dumped = _act(u, "dump_planet_cargo", planet_id=planet.id, commodity="colonists", qty=75, pool="organics")
    assert dumped.ok is False and dumped.error == K.COLONIST_MOVE_BY_THOUSAND
    assert sum(planet.colonists.values()) == 0
    assert ship.cargo[Commodity.COLONISTS] == 75
    # One full row is not the whole planet: the other product rows still have the printed maximum.
    # The thousand message stays, because room remains. The cap is named when every row is full.
    planet.colonists[Commodity.COLONISTS] = 40_000
    one_row = {la.kind: la for la in legal_actions(u, "P1")}
    assert one_row["dump_planet_cargo"].legal is False
    assert one_row["dump_planet_cargo"].reason == K.COLONIST_MOVE_BY_THOUSAND
    for pool in (Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT, Commodity.COLONISTS):
        planet.colonists[pool] = 40_000
    full = {la.kind: la for la in legal_actions(u, "P1")}
    assert full["dump_planet_cargo"].legal is False
    assert full["dump_planet_cargo"].reason == "planet is at its class cap"


def test_v311_class_m_thousands_land_as_handbook_on_class_l(monkeypatch) -> None:
    """1,000 class M people are 1 handbook colonist. 40,000 people are 40. The L cap stays 40,000."""
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u = _world()
    home = _land(u, PlanetClass.M)
    home.colonists[Commodity.ORGANICS] = 63_000
    loaded = _act(u, "load_planet_cargo", planet_id=home.id, commodity="colonists", qty=1_000, pool="organics")
    assert loaded.ok, loaded.error
    assert home.colonists[Commodity.ORGANICS] == 62_000
    assert u.players["P1"].ship.cargo[Commodity.COLONISTS] == 1_000
    assert u.players["P1"].ship.cargo_used == 1
    colony = _land(u, PlanetClass.L)
    assert sum(colony.colonists.values()) == 0
    dumped = _act(u, "dump_planet_cargo", planet_id=colony.id, commodity="colonists", qty=1_000, pool="organics")
    assert dumped.ok, dumped.error
    assert colony.colonists[Commodity.ORGANICS] == 1
    assert sum(colony.colonists.values()) == 1
    assert u.players["P1"].ship.cargo.get(Commodity.COLONISTS, 0) == 0
    assert K.planet_colonist_cap("L") == 40_000
    assert K.PLANET_MAX_COLONISTS["L"] == 40_000

    u2 = _world()
    home2 = _land(u2, PlanetClass.M)
    home2.colonists[Commodity.FUEL_ORE] = 113_000
    loaded2 = _act(u2, "load_planet_cargo", planet_id=home2.id, commodity="colonists", qty=40_000, pool="fuel_ore")
    assert loaded2.ok, loaded2.error
    assert home2.colonists[Commodity.FUEL_ORE] == 73_000
    ship2 = u2.players["P1"].ship
    assert ship2.cargo[Commodity.COLONISTS] == 40_000
    assert ship2.cargo_used == 40
    colony2 = _land(u2, PlanetClass.L)
    dumped2 = _act(u2, "dump_planet_cargo", planet_id=colony2.id, commodity="colonists", qty=40_000, pool="fuel_ore")
    assert dumped2.ok, dumped2.error
    assert colony2.colonists[Commodity.FUEL_ORE] == 40
    assert sum(colony2.colonists.values()) == 40
    assert ship2.cargo.get(Commodity.COLONISTS, 0) == 0
    assert K.planet_colonist_cap(colony2.class_id.value) == 40_000
