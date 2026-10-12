"""A ship on your citadel is inside it only when that switch is on.

Off, the parked-ship record has no planet, and a Fed tow still runs.
On, the hull remembers the citadel. An attack there fails. A tow skips
you. Boarding that hull from space is refused.

Plants:
  pb1 — an attack still hits a ship that is landed on its citadel.
  pb2 — leaving the hull on the citadel forgets the planet.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.fed import run_tows
from tw2k.engine.fleet import _park_manned, target_block
from tw2k.engine.models import Planet, PlanetClass, Player, Ship


def _world():
    u = generate_universe(GameConfig(seed=5101, universe_size=40, enable_ferrengi=False, enable_planets=True))
    planet = Planet(id=7, sector_id=K.STARDOCK_SECTOR, name="Home", class_id=PlanetClass.M,
                    owner_id="A", citadel_level=1)
    u.planets[7] = planet
    u.players["A"] = Player(
        id="A", name="Alpha", ship=Ship(holds=20, fighters=200),
        sector_id=K.STARDOCK_SECTOR, credits=50_000, planet_landed=7,
    )
    u.players["B"] = Player(
        id="B", name="Bravo", ship=Ship(holds=20, fighters=50),
        sector_id=K.STARDOCK_SECTOR, credits=50_000,
    )
    u.sectors[K.STARDOCK_SECTOR].occupant_ids.extend(["A", "B"])
    return u


def test_switch_stays_off() -> None:
    assert K.CITADEL_PARK_MODE == "legacy"
    assert K.citadel_park_live() is False


def test_off_leaves_the_ship_in_the_sector() -> None:
    u = _world()
    sid = _park_manned(u, "A")
    assert sid is not None
    assert "planet_id" not in u.parked_ships[sid].model_dump()
    hit = apply_action(u, "B", Action(kind=ActionKind.ATTACK, args={"target": "A", "qty": 1}))
    assert hit.error != "that ship is inside the citadel"


def test_on_parks_inside_the_citadel() -> None:
    u = _world()
    K.CITADEL_PARK_MODE = "live"
    try:
        blocked = apply_action(u, "B", Action(kind=ActionKind.ATTACK, args={"target": "A", "qty": 1}))
        assert blocked.ok is False
        assert blocked.error == "that ship is inside the citadel"
        before = u.players["A"].sector_id
        assert run_tows(u) >= 0
        assert u.players["A"].sector_id == before
        sid = _park_manned(u, "A")
        assert u.parked_ships[sid].planet_id == 7
        u.players["A"].planet_landed = None
        why, _hops = target_block(u, "A", u.parked_ships[sid])
        assert why == "that ship is inside a citadel"
    finally:
        K.CITADEL_PARK_MODE = "legacy"
