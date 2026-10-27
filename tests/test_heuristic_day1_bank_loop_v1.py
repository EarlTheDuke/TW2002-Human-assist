"""H banks one nest stage on day 1 and then trades (v3.11, StarDock drawn by #192).

The StarDock deposit caps day 1 at BOT_BANK_DAY1_DEPOSIT, while _bank_the_purse
plotted home whenever the purse was over 50,000. On day 1 the two agreed on
nothing: dock, deposit 10,000, one hop out, plot home, five times over.
"""

from __future__ import annotations

import asyncio

import pytest

from tw2k.agents.heuristic import HeuristicAgent
from tw2k.engine import ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.models import Player, Ship
from tw2k.engine.observation import build_observation


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_day1_banks_once_and_does_not_shuttle(monkeypatch, seed: int) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u = generate_universe(GameConfig(seed=seed, universe_size=200, max_days=5, enable_ferrengi=False))
    dock = K.stardock_sector_of(u)
    p = Player(id="P5", name="Bot", ship=Ship(), credits=100_000)
    p.sector_id = dock
    p.turns_per_day = 250
    p.turns_today = 0
    u.players["P5"] = p
    u.sectors[dock].occupant_ids.append("P5")
    agent = HeuristicAgent("P5", "Bot")
    homeward = 0
    trades = 0
    for _ in range(20):
        act = asyncio.run(agent.act(build_observation(u, "P5")))
        if act.kind is ActionKind.PLOT_COURSE and int((act.args or {}).get("target") or 0) == dock:
            homeward += 1
        if act.kind is ActionKind.TRADE:
            trades += 1
        assert apply_action(u, "P5", act).ok
    assert int(u.day) == 1
    # A scouting warp back through StarDock may bank one more stage; a plotted trip may not.
    assert p.bank_balance >= int(K.BOT_BANK_DAY1_DEPOSIT)
    assert homeward == 0
    assert trades >= 2
