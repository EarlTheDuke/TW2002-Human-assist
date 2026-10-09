"""Tri-Cron placement, payout, and the StarDock tavern action."""

from __future__ import annotations

import random

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, Ship
from tw2k.engine.tricron import PLACE_231, number_from, play_match


def test_sd1_grimy_order_puts_the_first_cron_in_the_tens() -> None:
    # 2-3-1: first cron is tens, second is ones, third is hundreds.
    assert number_from((4, 5, 6), PLACE_231) == 645


def test_sd2_ten_rounds_and_the_ante_enters_the_jackpot() -> None:
    result = play_match(random.Random(1), champion=99_999, jackpot=5_000)
    assert result["ante"] == 100
    assert result["jackpot"] == 5_100
    assert result["took_jackpot"] is False
    assert result["player_total"] != result["house_total"]


def test_sd3_two_to_one_only_when_the_player_beats_the_house() -> None:
    win = play_match(random.Random(0), champion=99_999, jackpot=0)
    lose = play_match(random.Random(2), champion=99_999, jackpot=0)
    assert win["beat_house"] is True and win["payback"] == 200
    assert lose["beat_house"] is False and lose["payback"] == 0
    assert win["credits_delta"] == 100
    assert lose["credits_delta"] == -100


def test_sd4_beating_the_champion_takes_the_jackpot_including_the_ante() -> None:
    result = play_match(random.Random(0), champion=0, jackpot=5_000)
    assert result["took_jackpot"] is True
    assert result["jackpot_prize"] == 5_100
    assert result["jackpot"] == 0
    assert result["champion"] == 5401
    assert result["credits_delta"] == 200 + 5_100 - 100


def _world():
    return generate_universe(GameConfig(
        seed=3, universe_size=20, max_days=6, enable_planets=False, enable_ferrengi=False,
    ))


def _seat(universe, *, credits):
    sector = int(K.STARDOCK_SECTOR)
    player = Player(id="P1", name="P1", ship=Ship(), credits=credits, sector_id=sector)
    universe.players["P1"] = player
    universe.sectors[sector].occupant_ids.append("P1")
    return player


def _kinds(universe, pid):
    return {row.kind for row in legal_actions(universe, pid)}


def test_sd5_legacy_hides_tricron(monkeypatch) -> None:
    monkeypatch.setattr(K, "STARDOCK_EXTRA_MODE", "legacy")
    monkeypatch.setattr(K, "CITADEL_FIDELITY_MODE", "legacy")
    universe = _world()
    player = _seat(universe, credits=1_000)
    assert "tricron" not in _kinds(universe, player.id)
    result = apply_action(universe, player.id, Action(kind=ActionKind.TRICRON, args={}))
    assert result.ok is False
    assert player.credits == 1_000


def test_sd6_a_stardock_match_pays_the_house_odds() -> None:
    universe = _world()
    player = _seat(universe, credits=1_000)
    assert "tricron" in _kinds(universe, player.id)
    rng = random.Random(f"tricron:{int(universe.config.seed)}:{int(universe.day)}:P1:0")
    expected = play_match(rng, champion=int(K.TRICRON_OPENING_CHAMPION), jackpot=int(K.TRICRON_OPENING_JACKPOT))
    result = apply_action(universe, player.id, Action(kind=ActionKind.TRICRON, args={}))
    assert result.ok is True
    assert player.credits == 1_000 + expected["payback"] + expected["jackpot_prize"] - expected["ante"]
    assert universe.tavern["tricron_jackpot"] == expected["jackpot"]
    assert universe.tavern["tricron_champion"] == expected["champion"]


def test_sd7_a_broke_trader_cannot_ante() -> None:
    universe = _world()
    player = _seat(universe, credits=50)
    result = apply_action(universe, player.id, Action(kind=ActionKind.TRICRON, args={}))
    assert result.ok is False
    assert player.credits == 50
    assert not isinstance(getattr(universe, "tavern", None), dict) or "tricron_played" not in universe.tavern


def test_sd8_tricron_is_only_at_stardock() -> None:
    universe = _world()
    player = _seat(universe, credits=1_000)
    away = next(sid for sid in universe.sectors if sid != int(K.STARDOCK_SECTOR))
    player.sector_id = away
    result = apply_action(universe, player.id, Action(kind=ActionKind.TRICRON, args={}))
    assert result.ok is False
    assert player.credits == 1_000
