"""discovery-exp-daily-bonus-v1. Off, only the first trader at a port scores."""
import pytest

import tw2k.engine.constants as K
from tests.test_ports_haggle_v1 import _port, _seat, _trade
from tw2k.engine.models import Commodity, Player, PortClass, Ship
from tw2k.engine.runner import tick_day

pytestmark = pytest.mark.legacy_profile

FUEL = Commodity.FUEL_ORE


def test_flag_stays_legacy() -> None:
    assert K.DISCOVERY_EXP_MODE == "legacy"
    assert K.discovery_exp_live() is False


def test_off_a_later_trader_gets_no_discovery_point() -> None:
    universe, player = _seat()
    port = _port(universe, PortClass.CLASS_1_BSS, FUEL, -100, 0)
    port.experience["someone"] = 0.2
    player.experience = 0
    res = _trade(universe, "sell", "fuel_ore")
    assert res.ok, res.error
    assert player.experience == K.xp_award("trade")


def test_on_each_player_scores_once_per_port(monkeypatch) -> None:
    monkeypatch.setattr(K, "DISCOVERY_EXP_MODE", "live")
    universe, player = _seat()
    port = _port(universe, PortClass.CLASS_1_BSS, FUEL, -100, 0)
    port.experience["someone"] = 0.2
    player.experience = 0
    assert _trade(universe, "sell", "fuel_ore").ok
    assert player.experience == K.xp_award("trade") + 1
    assert _trade(universe, "sell", "fuel_ore").ok
    assert player.experience == K.xp_award("trade") + 1 + K.xp_award("trade")


def test_on_the_daily_point_needs_a_turn_spent(monkeypatch) -> None:
    monkeypatch.setattr(K, "DISCOVERY_EXP_MODE", "live")
    universe, player = _seat()
    idle = Player(id="P9", name="Idle", ship=Ship(), credits=0, experience=10, alignment=0)
    idle.turns_today = 0
    idle.sector_id = 1
    universe.players["P9"] = idle
    for other in universe.players.values():
        other.credits = 0
        other.bank_balance = 0
    player.turns_today = 4
    player.experience = 10
    player.alignment = 0
    tick_day(universe)
    assert player.experience == 11 and player.alignment == 1
    assert idle.experience == 10 and idle.alignment == 0


def test_off_the_daily_point_still_reaches_everyone() -> None:
    universe, player = _seat()
    for other in universe.players.values():
        other.turns_today = 0
        other.experience = 10
        other.alignment = 0
        other.alive = True
        other.credits = 0
        other.bank_balance = 0
    player.turns_today = 0
    tick_day(universe)
    assert all(p.experience == 11 and p.alignment == 1 for p in universe.players.values())
