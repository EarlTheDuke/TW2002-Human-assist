"""Public rank follows experience when the switch is on. The switch stays off."""

from __future__ import annotations

import tw2k.engine.constants as K
from tests.test_phase_abc import _make_universe
from tw2k.engine.observation import Observation, status_fields
from tw2k.server.harness import final_standings


def _obs():
    return Observation.model_construct(
        net_worth=10,
        experience=5,
        rivals=[{"net_worth": 100, "experience": 1, "alive": True}],
        day=1,
        max_days=2,
        finished=False,
        turns_remaining=4,
        turns_per_day=10,
    )


def test_legacy_rank_follows_net_worth_and_the_old_warp():
    K.EXP_SCORE_MODE = "legacy"
    saved = K.RANK_MODE
    K.RANK_MODE = "legacy"
    try:
        assert status_fields(_obs())["rank"] == 2
        assert K.xp_award("warp") == 1
    finally:
        K.RANK_MODE = saved


def test_live_rank_follows_experience():
    K.EXP_SCORE_MODE = "live"
    try:
        assert status_fields(_obs())["rank"] == 1
        assert K.xp_award("warp") == 0
        assert K.xp_award("trade") == 1
        assert K.xp_award("first_dock") == 1
        assert K.xp_award("deploy_genesis") == 25
        assert K.xp_award("destroy_port") == 50
    finally:
        K.EXP_SCORE_MODE = "legacy"


def test_live_warp_is_zero_even_on_the_old_table():
    K.EXP_SCORE_MODE = "live"
    saved = K.RANK_MODE
    K.RANK_MODE = "legacy"
    try:
        assert K.xp_award("warp") == 0
    finally:
        K.RANK_MODE = saved
        K.EXP_SCORE_MODE = "legacy"


def test_live_standings_put_experience_first():
    K.EXP_SCORE_MODE = "live"
    try:
        u, players = _make_universe(seed=8850)
        for p in players:
            p.experience = 0
        rich, skilled = players[0], players[1]
        rich.experience = 1
        skilled.experience = 40
        rows = final_standings(u)["standings"]
        assert rows[0]["seat"] == skilled.id
        assert rows[0]["experience"] == 40
        assert "net_worth" in rows[0]
    finally:
        K.EXP_SCORE_MODE = "legacy"
