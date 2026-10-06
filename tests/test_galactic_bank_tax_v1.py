"""Galactic Bank and the good-trader tax. docs/playtests/fedspace/GALACTIC_BANK_TAX.md."""

from __future__ import annotations

from tw2k.agents.prompts import get_system_prompt
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe, tick_day
from tw2k.engine import constants as K
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, Ship, ShipClass
from tw2k.engine.victory import full_net_worth


def _world(credits=1_000_000, alignment=0, sector=1):
    u = generate_universe(GameConfig(
        seed=3, universe_size=20, max_days=6, enable_planets=False, enable_ferrengi=False,
    ))
    player = Player(id="A", name="Ada", ship=Ship(), credits=credits, alignment=alignment, experience=0)
    player.sector_id = sector
    u.players["A"] = player
    u.sectors[sector].occupant_ids.append("A")
    return u, player


def _do(u, kind, **args):
    return apply_action(u, "A", Action(kind=kind, args=args))


def test_gb1_only_at_stardock():
    u, _ = _world(sector=12)
    assert not _do(u, ActionKind.BANK_DEPOSIT, amount=10).ok
    u.players["A"].sector_id = 1
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=10).ok


def test_gb4_gb5_cap_is_refused():
    u, player = _world()
    res = _do(u, ActionKind.BANK_DEPOSIT, amount=600_000)
    assert not res.ok and "500,000" in (res.error or "")
    assert player.bank_balance == 0 and player.credits == 1_000_000
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=500_000).ok
    assert player.bank_balance == 500_000
    assert not _do(u, ActionKind.BANK_DEPOSIT, amount=1).ok


def test_gb7_withdraw_and_net_worth_holds():
    u, player = _world()
    before = full_net_worth(u, player)
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=100_000).ok
    assert full_net_worth(u, player) == before
    assert _do(u, ActionKind.BANK_WITHDRAW, amount=40_000).ok
    assert player.bank_balance == 60_000 and player.credits == 940_000
    assert player.turns_today == 0


def test_gb8_transfer_from_cash_and_unknown_id():
    u, player = _world()
    other = Player(id="B", name="Bea", ship=Ship(), credits=0)
    other.sector_id = 4
    u.players["B"] = other
    assert _do(u, ActionKind.BANK_TRANSFER, to_player="Z", amount=50).error == "no such trader"
    assert _do(u, ActionKind.BANK_TRANSFER, to_player="A", amount=50).error == "no such trader"
    assert _do(u, ActionKind.BANK_TRANSFER, to_player="B", amount=50_000).ok
    assert player.credits == 950_000 and other.bank_balance == 50_000


def test_gb17_gb19_tax_table():
    u, player = _world(credits=100_001, alignment=0)
    tick_day(u)
    assert player.credits == 100_001 - 5_000
    assert player.alignment == 1 + 3  # midnight +1, then floor(5000/1500)
    red, who = _world(credits=2_000_000, alignment=-2)  # midnight +1 still leaves them evil
    tick_day(red)
    assert who.credits == 2_000_000


def test_gb13_cash_lost_balance_kept(monkeypatch):
    u, player = _world(credits=300_000)
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=200_000).ok
    killer = Player(id="K", name="Kai", ship=Ship(), credits=0)
    killer.sector_id = 1
    u.players["K"] = killer
    from tw2k.engine.combat import _destroy_ship
    _destroy_ship(u, "A", "attack", killer_id="K", by_other=True)
    assert player.credits == 0 and player.bank_balance == 200_000
    assert killer.credits == 100_000


def test_gb32_prompt_and_legacy(monkeypatch):
    assert "Galactic Bank" in get_system_prompt()
    monkeypatch.setattr(K, "BANK_MODE", "legacy")
    assert "Galactic Bank" not in get_system_prompt()
    u, _ = _world()
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=10).error == "unsupported action"
    assert ActionKind.BANK_DEPOSIT.value not in {row.kind for row in legal_actions(u, "A")}


def test_pod_kill_pays_the_killer_nothing():
    u, player = _world(credits=80_000)
    player.ship.ship_class = ShipClass.ESCAPE_POD
    killer = Player(id="K", name="Kai", ship=Ship(), credits=0)
    u.players["K"] = killer
    from tw2k.engine.combat import _destroy_ship
    _destroy_ship(u, "A", "attack", killer_id="K", by_other=True)
    assert player.credits == 0 and killer.credits == 0
