"""Switch-literal pins for Match-behind-flag helpers that older tests only
turned on through V311_PROFILE.

Each test sets the switch itself to the 3.11 value and leaves V311_PROFILE
and TW2002_LIVE_PROFILE at legacy. The documented numbers are the ones in
docs/plans/gap-map-refresh-v6.md. The legacy default is asserted beside them.
"""
from __future__ import annotations

import tw2k.engine.constants as K
from tests.test_fedspace_police_v1 import _world
from tw2k.engine.bank import tax_on
from tw2k.engine.fed import run_tows
from tw2k.engine.models import Player
from tw2k.engine.victory import is_fedsafe


def _profiles_off(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")


def test_fed_tow_limit_live_tows_above_50_and_legacy_stays_98(monkeypatch) -> None:
    """GAP 1.15. Bible more than 50 when FED_TOW_LIMIT_MODE is live. Gypsy 98 when off."""
    _profiles_off(monkeypatch)
    monkeypatch.setattr(K, "FED_MODE", "tw2002")
    monkeypatch.setattr(K, "FED_TOW_LIMIT_MODE", "legacy")
    assert K.fed_tow_fighter_limit() == 98
    legacy = _world(
        players={
            "AT": dict(fighters=98, sector_id=3),
            "OVER": dict(fighters=99, sector_id=4),
        }
    )
    assert run_tows(legacy) == 1
    assert legacy.players["AT"].sector_id == 3
    assert legacy.players["OVER"].sector_id not in K.FEDSPACE_SECTORS

    monkeypatch.setattr(K, "FED_TOW_LIMIT_MODE", "live")
    assert K.V311_PROFILE == "legacy"
    assert K.fed_tow_fighter_limit() == 50
    assert K.FED_TOW_FIGHTER_LIMIT == 98
    live = _world(
        seed=4615,
        players={
            "AT": dict(fighters=50, sector_id=3),
            "OVER": dict(fighters=51, sector_id=4),
        },
    )
    assert run_tows(live) == 1
    assert live.players["AT"].sector_id == 3
    assert live.players["OVER"].sector_id not in K.FEDSPACE_SECTORS


def test_fedsafe_fighter_cap_live_is_50_and_legacy_ignores_fighters(monkeypatch) -> None:
    """GAP 5.20. More than 50 fighters removes FedSpace protection. 50 is still safe. Off, fighter count does not matter."""
    _profiles_off(monkeypatch)
    monkeypatch.setattr(K, "FED_MODE", "tw2002")
    monkeypatch.setattr(K, "FEDSAFE_FIGHTER_CAP_MODE", "legacy")
    universe = _world(
        players={"A": dict(alignment=0, experience=100, fighters=51, sector_id=3)}
    )
    trader = universe.players["A"]
    assert is_fedsafe(trader) is True

    monkeypatch.setattr(K, "FEDSAFE_FIGHTER_CAP_MODE", "live")
    assert K.V311_PROFILE == "legacy"
    assert K.fedsafe_max_fighters() == 50
    assert is_fedsafe(trader) is False
    trader.ship.fighters = 50
    assert is_fedsafe(trader) is True
    assert K.FEDSAFE_FIGHTER_CAP_MODE == "live"


def test_tax_rule_v311_is_ten_percent_over_49999_and_legacy_stays_five(monkeypatch) -> None:
    """GAP 11.6. Ten percent of cash on hand at 50,000 or more, alignment above 0. Legacy stays 5 percent over 100,000."""
    _profiles_off(monkeypatch)
    monkeypatch.setattr(K, "TAX_RULE_MODE", "legacy")
    assert K.tax_terms() == (5, 100_000, 0)
    seat = Player(id="P1", name="Seat", alignment=1, credits=100_001)
    assert tax_on(seat) == (5_000, 3)
    assert tax_on(seat, 60_000) == (0, 0)

    monkeypatch.setattr(K, "TAX_RULE_MODE", "v311")
    assert K.V311_PROFILE == "legacy"
    assert K.tax_terms() == (10, 49_999, 1)
    assert tax_on(seat, 49_999) == (0, 0)
    assert tax_on(seat, 50_000) == (5_000, 3)
    assert tax_on(seat, 60_000) == (6_000, 4)
    seat.alignment = 0
    assert tax_on(seat, 60_000) == (0, 0)
    seat.alignment = -5
    assert tax_on(seat, 900_000) == (0, 0)


def test_trade_in_parts_live_itemises_and_legacy_stays_25_percent(monkeypatch) -> None:
    """GAP 3.17. Itemised parts when TRADE_IN_PARTS_MODE is live. Legacy trade-in stays 25 percent of the sticker."""
    _profiles_off(monkeypatch)
    monkeypatch.setattr(K, "TRADE_IN_MODE", "legacy")
    monkeypatch.setattr(K, "TRADE_IN_PARTS_MODE", "legacy")
    sticker = K.ship_cost("merchant_cruiser")
    assert K.trade_in_credit("merchant_cruiser") == int(sticker * 0.25)
    assert K.trade_in_credit(K.ESCAPE_POD) == int(K.ship_cost("scout_marauder") * 0.25)

    monkeypatch.setattr(K, "TRADE_IN_PARTS_MODE", "live")
    assert K.V311_PROFILE == "legacy"
    assert K.trade_in_live() is False
    receipt = K.trade_in_receipt("merchant_cruiser")
    assert receipt["holds"] == 6_677
    assert receipt["hull"] == 8_999
    assert receipt["total"] == 34_844
    assert K.trade_in_credit("merchant_cruiser") == 34_844
    assert K.trade_in_credit("scout_marauder") == 12_380
    assert K.trade_in_credit(K.ESCAPE_POD) == 12_728
    assert K.TRADE_IN_FRACTION_LEGACY == 0.25
