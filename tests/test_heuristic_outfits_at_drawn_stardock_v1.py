"""A code bot outfits at StarDock where v3.11 put it, not at sector 1.

Claude seat session 2 (2026-11-08): with 1,000,000 credits every bot still flew the
starting Merchant Cruiser with 30 fighters. The heuristic outfitted and fitted a
scanner only when ``sector id == 1`` — the legacy StarDock. Under v3.11 sector 1 is
Terra and StarDock is drawn per game, so those branches never ran.
"""

from __future__ import annotations

import asyncio

import pytest

from tw2k.agents.heuristic import HeuristicAgent
from tw2k.engine import ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.models import Player, Ship
from tw2k.engine.observation import build_observation


@pytest.mark.parametrize("seed", [1, 2])
def test_a_rich_bot_buys_gear_at_the_drawn_stardock(monkeypatch, seed: int) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u = generate_universe(GameConfig(seed=seed, universe_size=200, max_days=5, enable_ferrengi=False))
    dock = K.stardock_sector_of(u)
    assert dock != 1  # the case the old check missed
    p = Player(id="P5", name="Bot", ship=Ship(), credits=1_000_000)
    p.sector_id = dock
    p.turns_per_day = 250
    p.turns_today = 0
    u.players["P5"] = p
    u.sectors[dock].occupant_ids.append("P5")
    agent = HeuristicAgent("P5", "Bot")
    bought: list[str] = []
    for _ in range(12):
        act = asyncio.run(agent.act(build_observation(u, "P5")))
        if act.kind is ActionKind.BUY_EQUIP:
            bought.append(str((act.args or {}).get("item")))
        assert apply_action(u, "P5", act).ok
        if bought and p.sector_id != dock:
            break
    assert "fighters" in bought, bought
    assert p.ship.fighters > 30
