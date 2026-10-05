"""Holes the first planet-cap tests let through, plus the full-world landing.

Every test runs the real engine (apply_action, legal_actions, tick_day,
build_observation). Each of the five holes is covered for class M, K and U.
"""

from __future__ import annotations

from tw2k.agents.seat_brain import SeatBrain, SeatMemory
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Commodity, Planet, PlanetClass, Player
from tw2k.engine.observation import build_observation
from tw2k.engine.planets import organics_consumption
from tw2k.engine.runner import _bfs_path, apply_action, tick_day

CLASSES = (PlanetClass.M, PlanetClass.K, PlanetClass.U)
GOODS = (Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT)


def _universe():
    u = generate_universe(GameConfig(
        seed=31, universe_size=90, max_days=3, turns_per_day=200,
        starting_credits=100_000, enable_ferrengi=False, enable_planets=True,
    ))
    player = Player(id="P1", name="Me", agent_kind="external", sector_id=1, credits=100_000)
    u.players["P1"] = player
    u.sectors[1].occupant_ids.append("P1")
    return u


def _move(u, sid: int) -> None:
    player = u.players["P1"]
    here = u.sectors[player.sector_id]
    here.occupant_ids = [item for item in here.occupant_ids if item != "P1"]
    player.sector_id = sid
    player.planet_landed = None
    u.sectors[sid].occupant_ids.append("P1")


def _deep(u) -> int:
    for sid in sorted(u.sectors):
        if sid > 10 and len(_bfs_path(u, 1, sid)) >= K.GENESIS_MIN_HOPS_FROM_STARDOCK and not u.sectors[sid].planet_ids:
            return sid
    raise AssertionError("no deep empty sector")


def _world(u, class_id: PlanetClass, pid: int, colonists: int, *, land: bool = True) -> Planet:
    """An owned world holding ``colonists`` idle colonists. The player lands on it."""
    sid = _deep(u)
    planet = Planet(
        id=pid, sector_id=sid, name=class_id.value, class_id=class_id,
        owner_id="P1", origin="genesis",
    )
    planet.colonists[Commodity.COLONISTS] = colonists
    u.planets[pid] = planet
    u.sectors[sid].planet_ids.append(pid)
    _move(u, sid)
    if land:
        assert apply_action(u, "P1", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": pid})).ok
    return planet


def _total(planet: Planet) -> int:
    return sum(int(n) for n in planet.colonists.values())


def _legal(u, kind: str):
    return {item.kind: item for item in legal_actions(u, "P1")}[kind]


def _dump(u, planet: Planet, qty: int):
    return apply_action(u, "P1", Action(
        kind=ActionKind.DUMP_PLANET_CARGO,
        args={"planet_id": planet.id, "commodity": "colonists", "qty": qty, "pool": "colonists"},
    ))


def _assign(u, planet: Planet, qty: int, src: str = "ship", dst: str = "colonists"):
    return apply_action(u, "P1", Action(
        kind=ActionKind.ASSIGN_COLONISTS,
        args={"planet_id": planet.id, "from": src, "to": dst, "qty": qty},
    ))


# (a) colonist cap in the dump handler ---------------------------------------

def test_dump_colonists_stops_at_the_cap() -> None:
    for index, class_id in enumerate(CLASSES):
        cap = K.PLANET_MAX_COLONISTS[class_id.value]
        u = _universe()
        planet = _world(u, class_id, 40 + index, cap)
        player = u.players["P1"]
        player.ship.cargo[Commodity.COLONISTS] = 4
        turns, credits, events = player.turns_today, player.credits, len(u.events)
        res = _dump(u, planet, 4)
        assert res.ok is False, class_id
        assert res.error == f"planet colonist cap is {cap}"
        assert player.ship.cargo[Commodity.COLONISTS] == 4
        assert _total(planet) == cap
        assert (player.turns_today, player.credits, len(u.events)) == (turns, credits, events)


def test_dump_colonists_one_past_the_room_is_refused_and_the_room_is_taken() -> None:
    for index, class_id in enumerate(CLASSES):
        cap = K.PLANET_MAX_COLONISTS[class_id.value]
        u = _universe()
        planet = _world(u, class_id, 80 + index, cap - 3)
        player = u.players["P1"]
        player.ship.cargo[Commodity.COLONISTS] = 10
        res = _dump(u, planet, 4)
        assert res.ok is False, class_id
        assert res.error == f"planet colonist cap is {cap}"
        assert player.ship.cargo[Commodity.COLONISTS] == 10
        assert _total(planet) == cap - 3
        res = _dump(u, planet, 3)
        assert res.ok, res.error
        assert player.ship.cargo[Commodity.COLONISTS] == 7
        assert _total(planet) == cap


# (b) colonist cap in the assign handler (ship to pool) ----------------------

def test_assign_from_ship_stops_at_the_cap() -> None:
    for index, class_id in enumerate(CLASSES):
        cap = K.PLANET_MAX_COLONISTS[class_id.value]
        u = _universe()
        planet = _world(u, class_id, 50 + index, cap)
        player = u.players["P1"]
        player.ship.cargo[Commodity.COLONISTS] = 4
        turns, credits, events = player.turns_today, player.credits, len(u.events)
        res = _assign(u, planet, 4)
        assert res.ok is False, class_id
        assert res.error == f"planet colonist cap is {cap}"
        assert player.ship.cargo[Commodity.COLONISTS] == 4
        assert _total(planet) == cap
        assert (player.turns_today, player.credits, len(u.events)) == (turns, credits, events)


def test_assign_from_ship_one_past_the_room_is_refused_and_the_room_is_taken() -> None:
    for index, class_id in enumerate(CLASSES):
        cap = K.PLANET_MAX_COLONISTS[class_id.value]
        u = _universe()
        planet = _world(u, class_id, 90 + index, cap - 3)
        player = u.players["P1"]
        player.ship.cargo[Commodity.COLONISTS] = 10
        res = _assign(u, planet, 4, dst="fuel_ore")
        assert res.ok is False, class_id
        assert res.error == f"planet colonist cap is {cap}"
        assert player.ship.cargo[Commodity.COLONISTS] == 10
        assert _total(planet) == cap - 3
        res = _assign(u, planet, 3, dst="fuel_ore")
        assert res.ok, res.error
        assert player.ship.cargo[Commodity.COLONISTS] == 7
        assert _total(planet) == cap


def test_a_full_world_still_moves_colonists_between_pools_and_back_to_the_ship() -> None:
    """The cap is on colonists arriving from the ship. Moves inside the world are free."""
    for index, class_id in enumerate(CLASSES):
        cap = K.PLANET_MAX_COLONISTS[class_id.value]
        u = _universe()
        planet = _world(u, class_id, 100 + index, cap)
        player = u.players["P1"]
        res = _assign(u, planet, 10, src="colonists", dst="organics")
        assert res.ok, res.error
        assert planet.colonists[Commodity.ORGANICS] == 10
        res = _assign(u, planet, 5, src="colonists", dst="ship")
        assert res.ok, res.error
        assert player.ship.cargo[Commodity.COLONISTS] == 5
        assert _total(planet) == cap - 5
        # Dumping other cargo is not blocked by a full colonist pool.
        player.ship.cargo[Commodity.FUEL_ORE] = 3
        res = apply_action(u, "P1", Action(
            kind=ActionKind.DUMP_PLANET_CARGO,
            args={"planet_id": planet.id, "commodity": "fuel_ore", "qty": 3},
        ))
        assert res.ok, res.error


# (c) legal list for dump_planet_cargo shows the remaining room --------------

def test_dump_legal_max_is_the_remaining_room() -> None:
    for index, class_id in enumerate(CLASSES):
        cap = K.PLANET_MAX_COLONISTS[class_id.value]
        u = _universe()
        planet = _world(u, class_id, 60 + index, cap - 3)
        player = u.players["P1"]
        player.ship.cargo[Commodity.COLONISTS] = 10
        listed = _legal(u, "dump_planet_cargo")
        assert listed.legal is True
        assert listed.params["qty"]["max_by"]["colonists"] == 3
        # Fewer aboard than room: the hold count is the limit.
        player.ship.cargo[Commodity.COLONISTS] = 2
        assert _legal(u, "dump_planet_cargo").params["qty"]["max_by"]["colonists"] == 2
        planet.colonists[Commodity.COLONISTS] = cap
        player.ship.cargo[Commodity.COLONISTS] = 10
        listed = _legal(u, "dump_planet_cargo")
        assert listed.legal is False
        assert listed.reason == "planet is at its class cap"
        assert "colonists" not in listed.params["qty"]["max_by"]
        assert "colonists" not in listed.params["commodity"]["choices"]


def test_dump_legal_list_keeps_other_cargo_when_colonists_are_full() -> None:
    for index, class_id in enumerate(CLASSES):
        cap = K.PLANET_MAX_COLONISTS[class_id.value]
        u = _universe()
        _world(u, class_id, 110 + index, cap)
        player = u.players["P1"]
        player.ship.cargo[Commodity.COLONISTS] = 10
        player.ship.cargo[Commodity.FUEL_ORE] = 5
        listed = _legal(u, "dump_planet_cargo")
        assert listed.legal is True
        assert listed.params["qty"]["max_by"] == {"fuel_ore": 5}
        assert listed.params["commodity"]["choices"] == ["fuel_ore"]


# (d) legal list for assign_colonists shows the remaining room ---------------

def test_assign_legal_max_is_the_remaining_room() -> None:
    for index, class_id in enumerate(CLASSES):
        cap = K.PLANET_MAX_COLONISTS[class_id.value]
        u = _universe()
        planet = _world(u, class_id, 70 + index, cap - 3)
        player = u.players["P1"]
        player.ship.cargo[Commodity.COLONISTS] = 10
        listed = _legal(u, "assign_colonists")
        assert listed.params["qty"]["max_by"]["ship"] == 3
        assert "ship" in listed.params["from"]["choices"]
        player.ship.cargo[Commodity.COLONISTS] = 2
        assert _legal(u, "assign_colonists").params["qty"]["max_by"]["ship"] == 2
        planet.colonists[Commodity.COLONISTS] = cap
        player.ship.cargo[Commodity.COLONISTS] = 10
        listed = _legal(u, "assign_colonists")
        assert "ship" not in listed.params["from"]["choices"]
        assert "ship" not in listed.params["qty"]["max_by"]
        # The pool is still there to move from, so the verb stays legal.
        assert listed.legal is True


def test_assign_list_offers_only_the_pools_when_the_colonists_sit_in_a_pool() -> None:
    for index, class_id in enumerate(CLASSES):
        cap = K.PLANET_MAX_COLONISTS[class_id.value]
        u = _universe()
        planet = _world(u, class_id, 120 + index, 0)
        planet.colonists[Commodity.FUEL_ORE] = cap
        u.players["P1"].ship.cargo[Commodity.COLONISTS] = 10
        listed = _legal(u, "assign_colonists")
        assert listed.legal is True
        assert listed.params["from"]["choices"] == ["fuel_ore"]


# (e) a world already over its cap must not shrink ---------------------------

def test_over_cap_world_is_not_shrunk() -> None:
    """Day tick on a world over every cap leaves colonists and stock where they are."""
    for index, class_id in enumerate(CLASSES):
        u = _universe()
        planet = _world(u, class_id, 130 + index, 0, land=False)
        colonist_cap = K.PLANET_MAX_COLONISTS[class_id.value]
        planet.colonists[Commodity.COLONISTS] = colonist_cap + 50
        for good in GOODS:
            planet.colonists[good] = 100
            planet.stockpile[good] = K.PLANET_MAX_STOCK[class_id.value][good.value] + 500
        pools = {name: int(n) for name, n in planet.colonists.items()}
        total = _total(planet)
        assert total > colonist_cap
        tick_day(u)
        assert u.day == 2
        assert {name: int(n) for name, n in planet.colonists.items()} == pools, class_id
        assert _total(planet) == total
        assert int(planet.stockpile[Commodity.FUEL_ORE]) == K.PLANET_MAX_STOCK[class_id.value]["fuel_ore"] + 500
        assert int(planet.stockpile[Commodity.EQUIPMENT]) == K.PLANET_MAX_STOCK[class_id.value]["equipment"] + 500
        # Only the normal organics burn comes off the organics stock. No clamp to the cap.
        organics_cap = K.PLANET_MAX_STOCK[class_id.value]["organics"]
        assert int(planet.stockpile[Commodity.ORGANICS]) == organics_cap + 500 - organics_consumption(total)


def test_over_cap_world_stays_put_over_several_days() -> None:
    for index, class_id in enumerate(CLASSES):
        u = _universe()
        planet = _world(u, class_id, 140 + index, 0, land=False)
        colonist_cap = K.PLANET_MAX_COLONISTS[class_id.value]
        planet.colonists[Commodity.COLONISTS] = colonist_cap + 77
        planet.stockpile[Commodity.ORGANICS] = 1_000_000
        for _ in range(3):
            tick_day(u)
        assert _total(planet) == colonist_cap + 77, class_id


# The N2 ladder and a full world ----------------------------------------------

def _brain_at_home(class_id: PlanetClass, colonists: int):
    u = _universe()
    planet = _world(u, class_id, 32, colonists)
    planet.citadel_level = 6
    player = u.players["P1"]
    player.ship.cargo[Commodity.COLONISTS] = 28
    brain = SeatBrain(value_allocator=False)
    brain.decide(build_observation(u, "P1").model_dump(mode="json"))
    assert apply_action(u, "P1", Action(kind=ActionKind.LIFTOFF, args={})).ok
    player.ship.cargo[Commodity.COLONISTS] = 28
    space = build_observation(u, "P1").model_dump(mode="json")
    return brain, brain.decide(space)


def test_full_world_is_not_an_unload_landing() -> None:
    for class_id in CLASSES:
        brain, action = _brain_at_home(class_id, K.PLANET_MAX_COLONISTS[class_id.value])
        assert 32 in brain.mem.no_colonist_room, class_id
        assert action["kind"] != "land_planet", class_id


def test_a_world_with_room_is_still_an_unload_landing() -> None:
    for class_id in CLASSES:
        brain, action = _brain_at_home(class_id, K.PLANET_MAX_COLONISTS[class_id.value] - 500)
        assert 32 not in brain.mem.no_colonist_room, class_id
        assert action["kind"] == "land_planet", class_id
        assert action["args"] == {"planet_id": 32}


def _brain_one_hop_away(class_id: PlanetClass, colonists: int):
    """The brain has seen the world from the ground, then stands one hop away holding colonists."""
    u = _universe()
    planet = _world(u, class_id, 32, colonists)
    planet.citadel_level = 6
    player = u.players["P1"]
    player.ship.cargo[Commodity.COLONISTS] = 28
    brain = SeatBrain(value_allocator=False)
    brain.decide(build_observation(u, "P1").model_dump(mode="json"))
    assert apply_action(u, "P1", Action(kind=ActionKind.LIFTOFF, args={})).ok
    _move(u, sorted(u.sectors[planet.sector_id].warps)[0])
    player.ship.cargo[Commodity.COLONISTS] = 28
    return brain, brain.decide(build_observation(u, "P1").model_dump(mode="json"))


def test_the_ladder_does_not_ferry_colonists_to_a_full_home() -> None:
    for class_id in CLASSES:
        brain, action = _brain_one_hop_away(class_id, K.PLANET_MAX_COLONISTS[class_id.value])
        assert 32 in brain.mem.no_colonist_room
        assert "ferry colonists home" not in str(action.get("thought")), class_id
        brain, action = _brain_one_hop_away(class_id, K.PLANET_MAX_COLONISTS[class_id.value] - 500)
        assert "ferry colonists home" in str(action.get("thought")), class_id


def test_a_world_that_gets_room_again_is_forgotten_as_full() -> None:
    for class_id in CLASSES:
        cap = K.PLANET_MAX_COLONISTS[class_id.value]
        u = _universe()
        planet = _world(u, class_id, 32, cap)
        planet.citadel_level = 6
        player = u.players["P1"]
        player.ship.cargo[Commodity.COLONISTS] = 28
        brain = SeatBrain(value_allocator=False)
        brain.decide(build_observation(u, "P1").model_dump(mode="json"))
        assert 32 in brain.mem.no_colonist_room
        planet.colonists[Commodity.COLONISTS] = cap - 500
        brain.decide(build_observation(u, "P1").model_dump(mode="json"))
        assert 32 not in brain.mem.no_colonist_room, class_id


def test_the_full_world_note_survives_a_memory_round_trip() -> None:
    mem = SeatMemory()
    mem.no_colonist_room.add(32)
    again = SeatMemory.load(mem.dump())
    assert again.no_colonist_room == {32}
