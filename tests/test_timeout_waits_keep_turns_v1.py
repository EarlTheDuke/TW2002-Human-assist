"""A slow seat keeps its banked turns under v3.11.

North Star run (2026-11-07) and the Claude seat pilot (2026-11-08): the server
inserts a WAIT when a seat takes longer than its deadline (a person reading, a
model thinking). The WAIT-loop guard counted those, and four in a row "ended the
day early": every banked turn thrown away (the pilot seat dropped to 10/250 after an
11-minute pause). Under v3.11 turn regen those turns only trickle back, and the day
already rolls on the clock, so a server-inserted WAIT no longer counts toward the
stand-down. A WAIT the seat chooses still does, and legacy rules are unchanged.
"""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tw2k.server.runner import note_wait_streak, wait_counts_toward_standdown


def _streak(counts: list[bool]) -> int:
    waits: dict[str, int] = {}
    day: dict[str, int] = {}
    for c in counts:
        note_wait_streak(waits, day, "P1", 1, c)
    return waits["P1"]


def test_v311_server_inserted_waits_do_not_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.turn_regen_live()
    inserted = wait_counts_toward_standdown(True, True, timed_out=True)
    assert inserted is False
    assert _streak([inserted] * 6) == 0


def test_v311_a_chosen_wait_still_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    chosen = wait_counts_toward_standdown(True, True, timed_out=False)
    assert chosen is True
    assert _streak([chosen] * 4) == 4


def test_legacy_counts_inserted_waits_as_before(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TURN_REGEN_MODE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    assert not K.turn_regen_live()
    assert wait_counts_toward_standdown(True, True, timed_out=True) is True


def test_a_refused_or_non_wait_turn_never_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert wait_counts_toward_standdown(False, True, timed_out=False) is False
    assert wait_counts_toward_standdown(True, False, timed_out=False) is False
