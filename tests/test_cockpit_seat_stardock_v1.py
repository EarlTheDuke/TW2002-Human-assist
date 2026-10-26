"""The cockpit seat finds StarDock where the cockpit paints it (GAP 1.5, #192).

A v3.11 game places StarDock at random and the observation names it in
sector.stardock_sector. A stored game leaves the field out: StarDock is sector 1.
"""

from __future__ import annotations

from tw2k.agents.cockpit_seat import STARDOCK_SECTOR, stardock_of
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.models import Player, Ship
from tw2k.engine.observation import build_observation


def test_stored_game_keeps_sector_1() -> None:
    assert stardock_of({"sector": {"id": 7}}) == STARDOCK_SECTOR == 1
    assert stardock_of({}) == 1
    assert stardock_of({"sector": {"id": 7, "stardock_sector": "junk"}}) == 1


def test_named_dock_wins() -> None:
    assert stardock_of({"sector": {"id": 7, "stardock_sector": 42}}) == 42


def test_v311_observation_names_the_random_dock(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u = generate_universe(GameConfig(seed=11, universe_size=80, max_days=3, enable_ferrengi=False))
    dock = K.stardock_sector_of(u)
    assert dock != 1
    p = Player(id="P1", name="P1", ship=Ship(), credits=1000)
    p.sector_id = dock
    u.players["P1"] = p
    u.sectors[dock].occupant_ids.append("P1")
    obs = build_observation(u, "P1").model_dump(mode="json")
    assert stardock_of(obs) == dock
