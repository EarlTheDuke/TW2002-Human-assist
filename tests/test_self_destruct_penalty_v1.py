"""R5 B. Self-destruct MBBS penalties stay behind SELF_DESTRUCT_PENALTY_MODE.

Off, the button still takes half the experience and half the alignment,
either sign, and sits the pilot out today and tomorrow. On, experience is
still cut in half, a negative alignment is cut in half, and a non-negative
alignment stays. A Ship Destroyed that is not the button still halves either
sign. The stored flag stays legacy. V311_PROFILE "v311" turns the helper on.
The string "1" does not.
"""
from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tests.test_fedspace_police_v1 import _world
from tw2k.engine import Action, ActionKind, apply_action
from tw2k.engine.combat import _destroy_ship_tw2002
from tw2k.engine.runner import tick_day

pytestmark = pytest.mark.legacy_profile


def _arm(monkeypatch, mode: str) -> None:
    monkeypatch.setattr(K, "SHIP_EXIT_MODE", "tw2002")
    monkeypatch.setattr(K, "SELF_DESTRUCT_PENALTY_MODE", mode)
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")


def _pilot(alignment: int, experience: int = 1000):
    universe = _world(
        seed=5140 + alignment,
        players={"A": dict(alignment=alignment, fighters=10, sector_id=20)},
    )
    universe.players["A"].experience = experience
    universe.players["A"].turns_today = 0
    return universe


def test_switch_defaults_legacy_and_only_v311_turns_it_on(monkeypatch) -> None:
    assert K.SELF_DESTRUCT_PENALTY_MODE == "legacy"
    assert K.self_destruct_mbbs_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.self_destruct_mbbs_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.self_destruct_mbbs_live() is True
    assert K.SELF_DESTRUCT_PENALTY_MODE == "legacy"
    assert K.V311_PROFILE_HELPERS["self_destruct_mbbs_live"][0] == "SELF_DESTRUCT_PENALTY_MODE"


def test_legacy_halves_good_and_bad_alignment(monkeypatch) -> None:
    _arm(monkeypatch, "legacy")
    good = _pilot(100)
    assert apply_action(good, "A", Action(kind=ActionKind.SELF_DESTRUCT)).ok
    assert good.players["A"].experience == 500
    assert good.players["A"].alignment == 50
    assert good.players["A"].self_destruct_lock_day == good.day + 1
    assert good.players["A"].turns_today >= good.players["A"].turns_per_day

    bad = _pilot(-80)
    assert apply_action(bad, "A", Action(kind=ActionKind.SELF_DESTRUCT)).ok
    assert bad.players["A"].experience == 500
    assert bad.players["A"].alignment == -40


def test_mbbs_leaves_good_alignment_and_halves_bad(monkeypatch) -> None:
    _arm(monkeypatch, "v311")
    good = _pilot(100)
    assert apply_action(good, "A", Action(kind=ActionKind.SELF_DESTRUCT)).ok
    assert good.players["A"].experience == 500
    assert good.players["A"].alignment == 100
    assert good.players["A"].self_destruct_lock_day == good.day + 1
    day = good.day
    tick_day(good)
    assert good.day == day + 1
    assert good.players["A"].turns_today >= good.players["A"].turns_per_day

    bad = _pilot(-80)
    assert apply_action(bad, "A", Action(kind=ActionKind.SELF_DESTRUCT)).ok
    assert bad.players["A"].experience == 500
    assert bad.players["A"].alignment == -40


def test_profile_uses_mbbs_and_a_real_destroy_still_halves_good_alignment(monkeypatch) -> None:
    monkeypatch.setattr(K, "SHIP_EXIT_MODE", "tw2002")
    monkeypatch.setattr(K, "SELF_DESTRUCT_PENALTY_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    good = _pilot(200, experience=400)
    assert apply_action(good, "A", Action(kind=ActionKind.SELF_DESTRUCT)).ok
    assert good.players["A"].experience == 200
    assert good.players["A"].alignment == 200

    other = _pilot(200, experience=400)
    _destroy_ship_tw2002(other, "A", "fighters", "B", True, force_destroyed=True)
    assert other.players["A"].experience == 200
    assert other.players["A"].alignment == 100
