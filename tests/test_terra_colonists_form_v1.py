"""A Terra load names the colonists, and one hold is one colonist until live.

Live, one hold is 1,000 colonists. The sentence uses that count. Legacy stays
at one colonist per hold, so the old sentence does not move.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tests.test_class0_terra_v1 import _act, _world
from tw2k.engine.actions import ActionKind
from tw2k.engine.models import Commodity, EventKind


def test_legacy_sentence_matches_the_holds(monkeypatch) -> None:
    monkeypatch.setattr(K, "CLASS0_MODE", "tw2002")
    assert K.colonists_per_hold() == 1
    u = _world()
    res = _act(u, "A", ActionKind.TERRA_COLONISTS, mode="take", qty=5)
    assert res.ok, res.error
    said = _said(u)
    assert "take 5 colonists" in said
    assert u.players["A"].ship.cargo[Commodity.COLONISTS] == 5


def test_live_sentence_names_the_people(monkeypatch) -> None:
    monkeypatch.setattr(K, "CLASS0_MODE", "tw2002")
    monkeypatch.setattr(K, "TERRA_COLONIST_MODE", "live")
    assert K.colonists_per_hold() == 1_000
    u = _world()
    u.terra_colonists = 50_000
    u.players["A"].ship.holds = 20
    res = _act(u, "A", ActionKind.TERRA_COLONISTS, mode="take", qty=2)
    assert res.ok, res.error
    assert u.players["A"].ship.cargo[Commodity.COLONISTS] == 2_000
    assert "take 2000 colonists" in _said(u)
    assert u.terra_colonists == 48_000


def _said(u) -> str:
    return next(ev.summary for ev in u.events if ev.kind is EventKind.TERRA_COLONISTS)
