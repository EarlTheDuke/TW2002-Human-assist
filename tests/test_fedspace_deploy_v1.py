"""FedSpace fighter drops. Legacy refuses them. Live annihilates them."""

from __future__ import annotations

import pytest

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Commodity, FighterDeployment, FighterMode, Player, Ship

pytestmark = pytest.mark.legacy_profile


def _seat(fighters: int, holds: int):
    universe = generate_universe(GameConfig(seed=123, universe_size=40, max_days=2))
    player = Player(id="P1", name="Tester", ship=Ship(fighters=fighters, holds=holds))
    universe.players["P1"] = player
    universe.sectors[1].occupant_ids.append("P1")
    player.sector_id = 1
    return universe, player


def _drop(universe, qty: int):
    return apply_action(
        universe,
        "P1",
        Action(kind=ActionKind.DEPLOY_FIGHTERS, args={"qty": qty, "mode": "defensive"}),
    )


def test_legacy_refuses_a_fedspace_drop():
    assert K.FEDSPACE_DEPLOY_MODE == "legacy"
    universe, player = _seat(30, 35)
    result = _drop(universe, 5)
    assert result.ok is False
    assert result.error == "cannot deploy fighters in FedSpace"
    assert player.ship.fighters == 30
    assert player.ship.holds == 35
    assert universe.sectors[1].fighters is None
    assert player.turns_today == 0


def test_live_takes_ten_percent_and_places_nothing():
    _prior_fedspace_deploy_mode = K.FEDSPACE_DEPLOY_MODE
    try:
        universe, player = _seat(30, 35)
        try:
            K.FEDSPACE_DEPLOY_MODE = "live"
            result = _drop(universe, 5)
            assert result.ok is True
            assert player.ship.fighters == 27
            assert player.ship.holds == 31
            assert universe.sectors[1].fighters is None
            assert player.turns_today == K.TURN_COST["deploy_fighters"]

            universe, player = _seat(20, 10)
            result = _drop(universe, 10)
            assert result.ok is True
            assert player.ship.fighters == 18
            assert universe.sectors[1].fighters is None

            universe, player = _seat(30, 35)
            player.ship.cargo[Commodity.FUEL_ORE] = 35
            _drop(universe, 5)
            assert player.ship.holds == 31
            assert player.ship.cargo_used == 31
        finally:
            K.FEDSPACE_DEPLOY_MODE = "legacy"
    finally:
        K.FEDSPACE_DEPLOY_MODE = _prior_fedspace_deploy_mode


def test_live_still_offers_a_drop_when_the_sector_is_full():
    _prior_fedspace_deploy_mode = K.FEDSPACE_DEPLOY_MODE
    try:
        universe, _player = _seat(30, 35)
        universe.sectors[1].fighters = FighterDeployment(
            owner_id="P1", count=K.SECTOR_FIGHTER_CAP, mode=FighterMode.DEFENSIVE,
        )
        offered = {item.kind: item for item in legal_actions(universe, "P1")}
        assert offered["deploy_fighters"].legal is False
        assert offered["deploy_fighters"].reason == "cannot deploy fighters in FedSpace"
        try:
            K.FEDSPACE_DEPLOY_MODE = "live"
            offered = {item.kind: item for item in legal_actions(universe, "P1")}
            assert offered["deploy_fighters"].legal is True
            assert offered["deploy_fighters"].params["qty"]["max"] == 30
        finally:
            K.FEDSPACE_DEPLOY_MODE = "legacy"
    finally:
        K.FEDSPACE_DEPLOY_MODE = _prior_fedspace_deploy_mode
