"""trade-dock-turn-v1. The first deal of a visit costs one turn. The next deals do not."""

from __future__ import annotations

from tw2k.engine import constants as K
from tw2k.engine.economy import begin_port_visit, trade_turn_cost
from tw2k.engine.models import Player


def _player() -> Player:
    return Player(id="P1", name="Tiny Box", agent_kind="llm", sector_id=5)


def test_default_is_one_turn_then_free() -> None:
    assert K.TRADE_TURN_MODE == "legacy"
    player = _player()
    assert trade_turn_cost(player) == 1
    begin_port_visit(player)
    assert trade_turn_cost(player) == 0
    player.end_port_visit()
    assert trade_turn_cost(player) == 1


def test_live_names_the_same_visit_rule() -> None:
    prior = K.TRADE_TURN_MODE
    K.TRADE_TURN_MODE = "live"
    try:
        player = _player()
        assert trade_turn_cost(player) == 1
        begin_port_visit(player)
        assert trade_turn_cost(player) == 0
    finally:
        K.TRADE_TURN_MODE = prior
