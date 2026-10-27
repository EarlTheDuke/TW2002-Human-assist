"""api-arg-hardening-v1. Aliases, the reject flag, and a plotted course that stays put."""
from types import SimpleNamespace

import pytest

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, generate_universe
from tw2k.engine.models import Player, Ship, ShipClass
from tw2k.engine.runner import apply_action
from tw2k.server.harness import arg_error, retry_blocked, rewrite_api_args

pytestmark = pytest.mark.legacy_profile


def _seat():
    universe = generate_universe(GameConfig(seed=3, universe_size=20, max_days=2, enable_ferrengi=False))
    sid = next(s for s in sorted(universe.sectors) if s > 10 and universe.sectors[s].warps)
    player = Player(id="P1", name="Pilot", sector_id=sid, ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER))
    universe.players["P1"] = player
    universe.sectors[sid].occupant_ids.append("P1")
    return universe, player


def test_flag_stays_legacy() -> None:
    assert K.API_ARGS_MODE == "legacy"
    assert K.api_args_live() is False


def test_off_rejects_stay_quiet_and_a_plot_does_not_move() -> None:
    universe, player = _seat()
    home = player.sector_id
    for _ in range(int(K.API_REJECT_STREAK)):
        result = apply_action(universe, "P1", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": 1}))
        assert result.ok is False
    assert not any("identical rejected" in ev.summary for ev in universe.events)
    assert "reject_loop_count" not in player.model_dump()
    warp = universe.sectors[home].warps[0]
    plotted = apply_action(universe, "P1", Action(kind=ActionKind.PLOT_COURSE, args={"target": warp, "execute": False}))
    assert plotted.ok is True
    assert player.sector_id == home


def test_on_the_twentieth_reject_is_flagged_and_aliases_name_amount(monkeypatch) -> None:
    monkeypatch.setattr(K, "API_ARGS_MODE", "live")
    universe, player = _seat()
    for _ in range(int(K.API_REJECT_STREAK)):
        apply_action(universe, "P1", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": 1}))
    assert any(ev.summary == "20 identical rejected actions in a row: land_planet" for ev in universe.events)
    action = Action(kind=ActionKind.BANK_DEPOSIT, args={"credits": 25})
    rewrite_api_args(action)
    assert action.args == {"amount": 25}
    bare = Action(kind=ActionKind.BANK_DEPOSIT, args={})
    assert arg_error(bare, "amount must be a whole number") == (
        "amount is required. Valid names: amount. Aliases: credits, qty."
    )
    monkeypatch.setattr(K, "API_RETRY_LIMIT", 2)
    agent = SimpleNamespace()
    assert retry_blocked(agent) is False
    assert retry_blocked(agent) is False
    assert retry_blocked(agent) is True
