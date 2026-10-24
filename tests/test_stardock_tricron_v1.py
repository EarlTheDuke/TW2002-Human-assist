"""Tri-Cron placement, payout, and the StarDock tavern action.

The capture is docs/playtests/twgs-live/tricron.txt (19 Oct 2026, NOTE 129).
"""

from __future__ import annotations

import random
from pathlib import Path

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, Ship
from tw2k.engine.tricron import PLACE_231, number_from, play_match

CAPTURE = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "twgs-live" / "tricron.txt"


def test_sd1_grimy_order_puts_the_first_cron_in_the_tens() -> None:
    # 2-3-1: first cron is tens, second is ones, third is hundreds.
    assert number_from((4, 5, 6), PLACE_231) == 645
    # Capture: position 1 is hundreds, 2 is tens, 3 is ones. 941 is that shape.
    assert number_from((9, 4, 1), (1, 2, 3)) == 941


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
    monkeypatch.setattr(K, "TRICRON_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    assert K.TRICRON_MODE == "legacy"
    assert K.tricron_live() is False
    universe = _world()
    player = _seat(universe, credits=1_000)
    assert "tricron" not in _kinds(universe, player.id)
    result = apply_action(universe, player.id, Action(kind=ActionKind.TRICRON, args={}))
    assert result.ok is False
    assert result.error == "unsupported action"
    assert player.credits == 1_000
    monkeypatch.setattr(K, "TRICRON_MODE", "1")
    assert K.tricron_live() is False
    assert "tricron" not in _kinds(universe, player.id)
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    assert K.tricron_live() is False


def test_sd6_a_stardock_match_pays_the_house_odds(monkeypatch) -> None:
    monkeypatch.setattr(K, "TRICRON_MODE", "v311")
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
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


def test_sd7_a_broke_trader_cannot_ante(monkeypatch) -> None:
    monkeypatch.setattr(K, "TRICRON_MODE", "v311")
    universe = _world()
    player = _seat(universe, credits=50)
    result = apply_action(universe, player.id, Action(kind=ActionKind.TRICRON, args={}))
    assert result.ok is False
    assert player.credits == 50
    assert not isinstance(getattr(universe, "tavern", None), dict) or "tricron_played" not in universe.tavern


def test_sd8_tricron_is_only_at_stardock(monkeypatch) -> None:
    monkeypatch.setattr(K, "TRICRON_MODE", "v311")
    universe = _world()
    player = _seat(universe, credits=1_000)
    away = next(sid for sid in universe.sectors if sid != int(K.STARDOCK_SECTOR))
    player.sector_id = away
    result = apply_action(universe, player.id, Action(kind=ActionKind.TRICRON, args={}))
    assert result.ok is False
    assert player.credits == 1_000


def test_capture_pins_ante_rounds_jackpot_and_a_two_to_one_win(monkeypatch) -> None:
    """tricron.txt: ante 100, 10 rounds, jackpot 5,000, and a win of 100 on that ante."""
    text = CAPTURE.read_text(encoding="utf-8")
    assert "The game will last for 10 rounds." in text
    assert "1 (hundreds), 2 (tens) or 3 (ones)" in text
    assert "your payback is 2 to 1." in text
    assert "The jackpot now stands at 5,000 credits." in text
    assert "with a score of 5000" in text
    assert "The current ante is 100 credits per match." in text
    assert "You win 100 credits!" in text
    assert "You have 228 credits." in text
    assert "128 to 228" in text
    assert K.TRICRON_ANTE == 100
    assert K.TRICRON_ROUNDS == 10
    assert K.TRICRON_OPENING_JACKPOT == 5_000
    assert K.TRICRON_OPENING_CHAMPION == 5_000

    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TRICRON_MODE", "legacy")
    universe = _world()
    player = _seat(universe, credits=128)
    universe.config.seed = 10
    universe.day = 1
    refused = apply_action(universe, player.id, Action(kind=ActionKind.TRICRON, args={}))
    assert refused.ok is False
    assert player.credits == 128

    monkeypatch.setattr(K, "TRICRON_MODE", "v311")
    assert K.TRICRON_MODE == "v311"
    tipped = apply_action(universe, player.id, Action(kind=ActionKind.GRIMY_ASK, args={"topic": "tricron"}))
    assert tipped.ok is True
    assert player.credits == 128
    assert any(ev.payload.get("answer") == "2-3-1" for ev in universe.events)

    dealt = apply_action(universe, player.id, Action(kind=ActionKind.TRICRON, args={}))
    assert dealt.ok is True
    assert player.credits == 228
    event = next(ev for ev in universe.events if ev.kind is ActionKind.TRICRON or ev.kind.value == "tricron")
    assert event.summary == "You win 100 credits!"
    assert event.payload["ante"] == 100
    assert event.payload["rounds"] == 10
    assert event.payload["payback"] == 200
    assert event.payload["player_total"] == 4482
    assert event.payload["house_total"] == 4276
    assert universe.tavern["tricron_jackpot"] == 5_100
    assert universe.tavern["tricron_champion"] == 5_000

    bad = apply_action(universe, player.id, Action(kind=ActionKind.TRICRON, args={"order": [1, 1, 1]}))
    assert bad.ok is False
    assert player.credits == 228
