"""bank-live-v1. The account cap comes off only when the switch is on."""
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.bank import handle_bank_deposit
from tw2k.engine.models import GameConfig, Player
from tw2k.engine.universe import generate_universe
import tw2k.engine.constants as K


def _seat(credits: int = 600_000):
    universe = generate_universe(GameConfig(seed=7, universe_size=30, max_days=2, enable_ferrengi=False))
    player = Player(id="P1", name="Tester", credits=credits)
    player.sector_id = K.STARDOCK_SECTOR
    universe.players["P1"] = player
    universe.sectors[player.sector_id].occupant_ids.append("P1")
    return universe, player


def _deposit(universe, amount: int):
    return handle_bank_deposit(
        universe, "P1", Action(kind=ActionKind.BANK_DEPOSIT, args={"amount": amount}),
    )


def test_flag_stays_legacy_and_the_old_bank_stays() -> None:
    assert K.BANK_LIVE_MODE == "legacy"
    assert K.bank_live() is False
    assert K.BANK_INTEREST_PCT == 0
    assert K.BANK_WITHDRAW_FEE == 0
    assert K.TAX_RATE_PCT == 5
    assert K.BANK_MAX_BALANCE == 500_000


def test_off_still_stops_at_the_cap() -> None:
    universe, player = _seat()
    result = _deposit(universe, 600_000)
    assert result.ok is False
    assert player.bank_balance == 0
    assert player.credits == 600_000


def test_on_takes_more_than_the_old_cap_and_only_at_stardock(monkeypatch) -> None:
    monkeypatch.setattr(K, "BANK_LIVE_MODE", "live")
    universe, player = _seat()
    result = _deposit(universe, 600_000)
    assert result.ok is True
    assert player.bank_balance == 600_000
    assert player.credits == 0
    player.sector_id = 20
    again = _deposit(universe, 1)
    assert again.ok is False
    assert "StarDock" in (again.error or "")
