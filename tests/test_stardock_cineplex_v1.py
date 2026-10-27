"""Cineplex is a StarDock picture with no secrets.

Stored CINEPLEX_COST stays 0. NOTE 129 priced show 1, Vulcan Thunder, at 100
credits. That live card is not this file's default.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, Ship

pytestmark = pytest.mark.legacy_profile


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
    monkeypatch.setattr(K, "CITADEL_FIDELITY_MODE", "legacy")
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


def test_cx4_note129_ticket_is_recorded_and_stored_cost_stays_0() -> None:
    root = Path(__file__).resolve().parents[1]
    goods = (root / "docs/playtests/twgs-live/illegal-goods.txt").read_text()
    menus = (root / "docs/playtests/twgs-live/stardock-menus.txt").read_text()
    leftovers = (root / "docs/plans/stardock-leftovers-v1.md").read_text()
    extra = (root / "docs/playtests/fedspace/STARDOCK_EXTRA.md").read_text()
    assert 'You\'ll LOVE "Vulcan Thunder"' in goods
    assert "100 Credits Please" in goods
    assert "The CinePlex Videon Theatres" in menus
    assert "Vulcan Thunder" in leftovers
    assert "illegal-goods.txt" in leftovers
    assert "stardock-menus.txt" in leftovers
    assert "`CINEPLEX_COST` stays 0" in leftovers
    assert "Vulcan Thunder" in extra
    assert "illegal-goods.txt" in extra
    assert K.CINEPLEX_COST == 0
