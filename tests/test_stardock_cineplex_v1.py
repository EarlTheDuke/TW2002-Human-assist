"""Cineplex is a StarDock picture with no secrets. Price is UNVERIFIED and stays 0."""

from __future__ import annotations

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, Ship


def _world():
    return generate_universe(GameConfig(
        seed=3, universe_size=20, max_days=6, enable_planets=False, enable_ferrengi=False,
    ))


def _seat(universe, *, sector, credits=1_000):
    player = Player(id="P1", name="P1", ship=Ship(), credits=credits, sector_id=sector)
    universe.players["P1"] = player
    universe.sectors[sector].occupant_ids.append("P1")
    return player


def _kinds(universe):
    return {row.kind: row for row in legal_actions(universe, "P1")}


def test_cx1_legacy_hides_the_theatre(monkeypatch) -> None:
    monkeypatch.setattr(K, "STARDOCK_EXTRA_MODE", "legacy")
    universe = _world()
    player = _seat(universe, sector=int(K.STARDOCK_SECTOR))
    assert "cineplex" not in _kinds(universe)
    result = apply_action(universe, "P1", Action(kind=ActionKind.CINEPLEX, args={}))
    assert result.ok is False
    assert player.credits == 1_000


def test_cx2_the_picture_has_no_secrets_and_no_charge() -> None:
    universe = _world()
    player = _seat(universe, sector=int(K.STARDOCK_SECTOR))
    assert _kinds(universe)["cineplex"].legal is True
    result = apply_action(universe, "P1", Action(kind=ActionKind.CINEPLEX, args={}))
    assert result.ok is True
    assert player.credits == 1_000
    shown = [event.summary for event in universe.events if event.kind == "cineplex" or getattr(event.kind, "value", "") == "cineplex"]
    assert shown == ["The Cineplex plays a short picture. It has no secrets."]


def test_cx3_the_theatre_is_only_at_stardock() -> None:
    universe = _world()
    away = next(sid for sid in universe.sectors if int(sid) != int(K.STARDOCK_SECTOR))
    player = _seat(universe, sector=away)
    assert _kinds(universe)["cineplex"].legal is False
    result = apply_action(universe, "P1", Action(kind=ActionKind.CINEPLEX, args={}))
    assert result.ok is False
    assert player.credits == 1_000
