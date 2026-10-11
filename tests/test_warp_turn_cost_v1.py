"""warp-turn-cost-v1. A warp costs that ship's turns per warp."""

from __future__ import annotations

from tw2k.engine import constants as K
from tw2k.engine.legality import _warp_cost
from tw2k.engine.models import Player, ShipClass
from tw2k.engine.runner import _warp_cost_for


def _player(class_name: ShipClass) -> Player:
    player = Player(id="P1", name="Tiny Box", agent_kind="llm", sector_id=5)
    player.ship.ship_class = class_name
    return player


def test_default_uses_the_ship_table() -> None:
    assert K.WARP_COST_MODE == "legacy"
    assert K.warp_turns("merchant_cruiser") == 3
    assert K.warp_turns("merchant_freighter") == 2
    assert K.warp_turns("scout_marauder") == 2
    freighter = _player(ShipClass.MERCHANT_FREIGHTER)
    assert _warp_cost_for(freighter) == 2
    assert _warp_cost(freighter) == 2


def test_live_names_the_same_ship_costs() -> None:
    prior = K.WARP_COST_MODE
    K.WARP_COST_MODE = "live"
    try:
        assert K.warp_turns("merchant_cruiser") == 3
        assert K.warp_turns("merchant_freighter") == 2
    finally:
        K.WARP_COST_MODE = prior
