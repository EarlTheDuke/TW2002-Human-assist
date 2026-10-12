"""Corporation rankings appear only when that switch is on.

Off, the observation does not carry them. On, corps are ordered by
the members' experience added together, with alignment added together.

Plants:
  pb1 — the live screen still leaves the ranking off the observation.
  pb2 — the switch off still publishes the ranking.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine.models import Corporation, GameConfig, Player, Ship
from tw2k.engine.observation import build_observation, corporation_rankings
from tw2k.engine.universe import generate_universe


def _world():
    u = generate_universe(GameConfig(seed=3, universe_size=40, enable_ferrengi=False, enable_planets=False))
    u.players["A"] = Player(id="A", name="Alpha", ship=Ship(), sector_id=1, credits=1000, experience=10, alignment=5)
    u.players["B"] = Player(id="B", name="Bravo", ship=Ship(), sector_id=1, credits=1000, experience=40, alignment=-2)
    u.sectors[1].occupant_ids.append("A")
    u.corporations["LOW"] = Corporation(ticker="LOW", name="Low", ceo_id="A", member_ids=["A"])
    u.corporations["HIGH"] = Corporation(ticker="HIGH", name="High", ceo_id="B", member_ids=["B"])
    return u


def test_switch_stays_off() -> None:
    assert K.CORP_RANK_MODE == "legacy"
    assert K.corp_rank_live() is False


def test_off_omits_the_ranking() -> None:
    dumped = build_observation(_world(), "A").model_dump()
    assert "corp_rankings" not in dumped


def test_on_orders_by_experience() -> None:
    u = _world()
    K.CORP_RANK_MODE = "live"
    try:
        rows = corporation_rankings(u)
        assert [row["ticker"] for row in rows] == ["HIGH", "LOW"]
        assert rows[0]["experience"] == 40 and rows[0]["alignment"] == -2
        assert rows[1]["experience"] == 10 and rows[1]["alignment"] == 5
        assert build_observation(u, "A").model_dump()["corp_rankings"] == rows
    finally:
        K.CORP_RANK_MODE = "legacy"
