"""NOTE 178, then R14 A.

14.6 keeps ECON_WIN_MODE. R14 A keeps the 100,000,000 credit finish and the
day cap, so the profile does not turn the switch on. Setting the switch
itself to v311 still drops the instant credits win. Legacy keeps the 100M win.
5.7 and 11.11 are docs reclassifications. 12.3 is R12 A (turns stay). 12.4
stays Partial.
"""
from __future__ import annotations

from types import SimpleNamespace

import tw2k.engine.constants as K
from tw2k.engine import victory


def _world(credits: int):
    p = SimpleNamespace(id="A", name="A", alive=True, credits=credits, experience=0,
                        alignment=0, net_worth=0, corp_ticker=None)
    q = SimpleNamespace(id="B", name="B", alive=True, credits=0, experience=0,
                        alignment=0, net_worth=0, corp_ticker=None)
    return p, q


def test_switch_defaults_legacy_and_the_profile_leaves_the_credit_finish(monkeypatch):
    assert K.ECON_WIN_MODE == "legacy"
    assert K.econ_win_off_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.econ_win_off_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.econ_win_off_live() is False
    assert "econ_win_off_live" not in K.V311_PROFILE_HELPERS
    monkeypatch.setattr(K, "ECON_WIN_MODE", "v311")
    assert K.econ_win_off_live() is True


def _ends_on_credits(monkeypatch, mode: str) -> bool:
    from tests.test_fedspace_police_v1 import _world as world
    monkeypatch.setattr(K, "ECON_WIN_MODE", mode)
    universe = world(players={"A": dict(sector_id=20), "B": dict(sector_id=21)})
    universe.players["A"].credits = victory.economic_threshold(universe.config.max_days) + 1
    universe.finished = False
    universe.day = 1
    victory_check = __import__("tw2k.engine.runner", fromlist=["_check_victory"])._check_victory
    victory_check(universe)
    return bool(universe.finished) and universe.win_reason == "economic"


def test_credits_win_fails_off_passes_on(monkeypatch):
    assert _ends_on_credits(monkeypatch, "legacy") is True
    assert _ends_on_credits(monkeypatch, "v311") is False


def test_end_rule_line_drops_instant_win_on(monkeypatch):
    assert "Instant win" in victory.end_rule_line(30)
    monkeypatch.setattr(K, "ECON_WIN_MODE", "v311")
    assert "Instant win" not in victory.end_rule_line(30)


def test_legacy_unchanged():
    assert K.VICTORY_CREDITS_THRESHOLD == 100_000_000
    assert victory.economic_threshold(30) == 100_000_000
    assert victory.end_rule_line(30).endswith("Instant win: 100,000,000 credits on hand.")
