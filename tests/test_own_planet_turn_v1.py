"""Own-planet landing turns. Legacy charges 3 plus 1. Live charges the 1 on liftoff."""

from __future__ import annotations

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player


def _seat(owner_id: str | None):
    universe = generate_universe(GameConfig(seed=123, universe_size=40, max_days=2))
    planet = next(iter(universe.planets.values()))
    planet.owner_id = owner_id
    planet.fighters = 0
    planet.shields = 0
    sector = universe.sectors[planet.sector_id]
    sector.fighters = None
    if hasattr(sector, "mines"):
        sector.mines = []
    player = Player(id="P1", name="Tester")
    player.sector_id = planet.sector_id
    universe.players["P1"] = player
    sector.occupant_ids.append("P1")
    return universe, player, planet


def _land(universe, planet_id: int):
    return apply_action(
        universe,
        "P1",
        Action(kind=ActionKind.LAND_PLANET, args={"planet_id": planet_id}),
    )


def _lift(universe):
    return apply_action(universe, "P1", Action(kind=ActionKind.LIFTOFF, args={}))


def test_legacy_charges_three_to_land_on_your_own_planet():
    assert K.OWN_PLANET_TURN_MODE == "legacy"
    universe, player, planet = _seat("P1")
    result = _land(universe, planet.id)
    assert result.ok is True
    assert player.turns_today == 3
    lift = _lift(universe)
    assert lift.ok is True
    assert player.turns_today == 4


def test_live_takes_the_one_turn_on_liftoff():
    universe, player, planet = _seat("P1")
    K.OWN_PLANET_TURN_MODE = "live"
    try:
        result = _land(universe, planet.id)
        assert result.ok is True
        assert player.turns_today == 0
        offered = {item.kind: item for item in legal_actions(universe, "P1")}
        assert offered["liftoff"].turn_cost == 1
        lift = _lift(universe)
        assert lift.ok is True
        assert player.turns_today == 1
    finally:
        K.OWN_PLANET_TURN_MODE = "legacy"


def test_live_still_charges_three_for_a_planet_you_do_not_own():
    universe, player, planet = _seat("P2")
    K.OWN_PLANET_TURN_MODE = "live"
    try:
        result = _land(universe, planet.id)
        assert result.ok is True
        assert player.turns_today == 3
    finally:
        K.OWN_PLANET_TURN_MODE = "legacy"
