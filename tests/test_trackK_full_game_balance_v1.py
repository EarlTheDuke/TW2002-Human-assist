"""Track K. Rows 216 and 217: full-length turn limit and an even start.

FULL_GAME_TURNS_MODE keeps the host's daily turns for any game length.
FULL_GAME_BALANCE_MODE drops the per-seat credit skew in a full-length game.
Both default to legacy and turn on only under V311_PROFILE=v311.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import tw2k.engine.constants as K
from tw2k.public import manual
from tw2k.public.security import parse_game_form, turns_phrase


@pytest.fixture
def full_on(monkeypatch):
    monkeypatch.setattr(K, "FULL_LENGTH_TURN_LIMITS_MODE", "v311")


def _form(**extra):
    data = {"name": "Long game", "game_length": "full", "max_days": "365"}
    data.update(extra)
    return parse_game_form(data)


def test_defaults_legacy_and_only_v311_turns_them_on(monkeypatch):
    assert K.FULL_GAME_TURNS_MODE == "legacy"
    assert K.FULL_GAME_BALANCE_MODE == "legacy"
    assert K.full_game_turns_live() is False
    assert K.full_game_balance_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.full_game_turns_live() is False
    assert K.full_game_balance_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.full_game_turns_live() is True
    assert K.full_game_balance_live() is True
    assert K.V311_PROFILE_HELPERS["full_game_turns_live"][0] == "FULL_GAME_TURNS_MODE"
    assert K.V311_PROFILE_HELPERS["full_game_balance_live"][0] == "FULL_GAME_BALANCE_MODE"


def test_manual_has_a_line_for_each_switch():
    text = repr(vars(manual))
    for name in ("FULL_GAME_TURNS_MODE", "FULL_GAME_BALANCE_MODE"):
        assert name in text


def test_long_game_turns_legacy_shrink_v311_keep(monkeypatch, full_on):
    assert _form().turns_per_day == K.full_length_daily_cap(365)
    monkeypatch.setattr(K, "FULL_GAME_TURNS_MODE", "v311")
    assert _form().turns_per_day == 250


def test_host_turns_choice_ignored_legacy_kept_v311(monkeypatch, full_on):
    assert _form(turns_per_day="1000").turns_per_day == K.full_length_daily_cap(365)
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    form = _form(turns_per_day="1000")
    assert form.turns_per_day == 1000
    assert form.settings()["turns_per_day_override"] == 1000


def test_engine_override_follows_the_switch(monkeypatch, full_on):
    cfg = SimpleNamespace(game_length="full", max_days=365)
    assert K.full_length_turns_override(cfg, 600) == K.full_length_daily_cap(365)
    monkeypatch.setattr(K, "FULL_GAME_TURNS_MODE", "v311")
    assert K.full_length_turns_override(cfg, 600) == 600
    assert K.full_length_turns_override(cfg, None) == 250
    fast = SimpleNamespace(game_length=None, max_days=365)
    assert K.full_length_turns_override(fast, None) is None


def test_even_start_drops_skew_only_full_and_on(monkeypatch):
    monkeypatch.setattr(K, "STARTING_PACKAGE_MODE", "legacy", raising=False)
    if K.starting_package_live():
        pytest.skip("this host runs the live starting package")
    skewed = {K.opening_loadout(20_000, 250, i)[0] for i in range(4)}
    assert len(skewed) > 1
    even = {K.opening_loadout(20_000, 250, i, even=True)[0] for i in range(4)}
    assert even == {20_000}
    full = SimpleNamespace(game_length="full")
    fast = SimpleNamespace(game_length=None)
    assert K.full_game_even_start(full) is False
    monkeypatch.setattr(K, "FULL_GAME_BALANCE_MODE", "v311")
    assert K.full_game_even_start(full) is True
    assert K.full_game_even_start(fast) is False


def test_lobby_card_line(monkeypatch):
    s = {"game_length": "full", "turns_per_day": 250}
    assert turns_phrase(s) == "Turns per day: 250 (full-length)"
    monkeypatch.setattr(K, "FULL_GAME_BALANCE_MODE", "v311")
    assert turns_phrase(s).endswith("Every seat starts the same")


def test_legacy_unchanged():
    assert K.full_length_daily_cap(30) == 250
    assert K.full_length_daily_cap(365) == 50
    assert K.opening_loadout(20_000, 250, 1) == K.opening_loadout(20_000, 250, 1, even=False)
