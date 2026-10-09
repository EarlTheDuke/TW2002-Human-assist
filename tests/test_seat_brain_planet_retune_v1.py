"""The seat brain no longer prices a citadel as a free garrison."""

from __future__ import annotations

from tw2k.agents.seat_acceptance import validate_action
from tw2k.agents.seat_brain import (
    CITADEL_GIFT_FIGHTERS_PER_LEVEL,
    CITADEL_GIFT_SHIELDS_PER_LEVEL,
    CITADEL_TIER_COST,
    SeatBrain,
    _defense_value,
    _planned_tier,
    next_tier,
)
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.actions import Action
from tw2k.engine.models import Commodity, Planet, PlanetClass, Player
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import apply_action


def test_citadel_value_is_the_credit_cost_not_a_garrison() -> None:
    assert CITADEL_GIFT_FIGHTERS_PER_LEVEL == 0
    assert CITADEL_GIFT_SHIELDS_PER_LEVEL == 0
    assert _defense_value(1) == 0
    assert _defense_value(2) == 0
    assert _defense_value(6) == 0
    planet = {"citadel_level": 1, "citadel_target": 1, "id": 1, "sector_id": 40, "class": "M"}
    assert next_tier(planet) == (0, 2_000)
    fresh = {"citadel_level": 0, "citadel_target": 0, "id": 2, "sector_id": 40}
    assert _planned_tier(fresh) is None
    planned = _planned_tier(planet)
    assert planned is not None
    cred, col, bonus, level = planned
    assert (cred, col, level) == (0, 2_000, 2)
    assert bonus == 10_000 + 2_000 * 10
    assert bonus != 105_000
    assert CITADEL_TIER_COST[1][0] == 10_000


def test_planner_picks_only_legal_actions() -> None:
    """A short fogged walk, including a citadel the seat cannot afford."""
    universe = generate_universe(GameConfig(
        seed=21011, universe_size=80, max_days=30, turns_per_day=40,
        starting_credits=100, enable_ferrengi=False, enable_planets=False,
    ))
    seat = Player(
        id="P1", name="Seat", agent_kind="external", sector_id=12, credits=100,
        turns_per_day=40,
    )
    universe.players["P1"] = seat
    universe.sectors[12].occupant_ids.append("P1")
    planet = Planet(
        id=88701, sector_id=12, name="Thin", class_id=PlanetClass.M,
        owner_id="P1", origin="genesis", citadel_level=0, citadel_target=0,
    )
    planet.colonists[Commodity.COLONISTS] = 5_000
    universe.planets[planet.id] = planet
    universe.sectors[12].planet_ids.append(planet.id)
    seat.planet_landed = planet.id
    seat.known_sectors.add(12)
    brain = SeatBrain()
    kinds: list[str] = []
    for _ in range(25):
        if seat.turns_today >= seat.turns_per_day:
            break
        obs = build_observation(universe, "P1").model_dump(mode="json")
        action = brain.decide(obs)
        errors = validate_action(obs, action)
        assert errors == [], (action.get("kind"), errors)
        result = apply_action(universe, "P1", Action(**action))
        assert result.ok, (action.get("kind"), result.error)
        kinds.append(str(action.get("kind")))
        if seat.credits < CITADEL_TIER_COST[0][0]:
            assert action.get("kind") != "build_citadel"
    assert kinds
    assert "planet_destroy" not in kinds
    assert "build_citadel" not in kinds
