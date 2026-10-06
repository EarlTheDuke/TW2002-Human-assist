"""fullgame2 P7: an LLM seat sat out days 2-4 waiting with 47-50 turns left.

Two causes, two fixes:
  * its own day-1 goal "wait until the day ends" stayed at the top of the action_hint every day;
    LLMAgent now adds a NEW DAY line until the seat writes fresh short/medium goals
    (K.LLM_NEW_DAY_GOAL_NOTICE, agent-side only);
  * the scheduler's 4-WAIT stand-down counted yesterday's end-of-day waits, so day 2 ended after
    two waits; the streak now restarts each game day (server.runner.note_wait_streak).
"""

from __future__ import annotations

import asyncio
import json

import pytest

from tw2k.agents import llm as llm_mod
from tw2k.agents.llm import LLMAgent, new_day_goal_notice
from tw2k.agents.prompts import format_observation
from tw2k.engine import ActionKind, GameConfig, build_observation, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.models import Player
from tw2k.server.runner import note_wait_streak


def _obs(day: int = 2, turns_remaining: int = 50, goals: dict | None = None):
    u = generate_universe(GameConfig(seed=7, universe_size=60, max_days=8, turns_per_day=50))
    u.players["P7"] = Player(id="P7", name="Grok", agent_kind="external", sector_id=1)
    obs = build_observation(u, "P7")
    return obs.model_copy(update={
        "day": day,
        "turns_remaining": turns_remaining,
        "goals": goals if goals is not None else {"short": "wait until the day ends", "medium": "", "long": ""},
    })


def test_notice_on_later_day_with_old_goals():
    text = new_day_goal_notice(_obs(day=2, turns_remaining=50), goals_day=1)
    assert text.startswith("NEW DAY 2:")
    assert "50 turns left today" in text
    assert "written on day 1" in text
    assert text.isascii()


@pytest.mark.parametrize("kwargs, goals_day", [
    ({"day": 1}, 1),                                   # written today
    ({"day": 3}, 3),
    ({"day": 2, "turns_remaining": 0}, 1),             # nothing left to do today
    ({"day": 2, "goals": {"short": "", "medium": " ", "long": "win"}}, 1),  # only a long goal
    ({"day": 2, "goals": {}}, 1),
])
def test_no_notice(kwargs, goals_day):
    assert new_day_goal_notice(_obs(**kwargs), goals_day=goals_day) == ""


def test_no_notice_before_first_act_and_when_switched_off(monkeypatch):
    assert new_day_goal_notice(_obs(), goals_day=None) == ""
    monkeypatch.setattr(K, "LLM_NEW_DAY_GOAL_NOTICE", False)
    assert new_day_goal_notice(_obs(), goals_day=1) == ""


def _reply(kind: str = "wait", goals: dict | None = None) -> str:
    body = {"thought": "t", "action": {"kind": kind, "args": {}}}
    if goals is not None:
        body["goals"] = goals
    return json.dumps(body)


def test_llm_agent_prompt_carries_notice_until_fresh_goals(monkeypatch):
    agent = LLMAgent("P7", "Grok", provider="xai", model="test-model")
    prompts: list[str] = []
    replies = iter([
        _reply("wait", {"short": "wait until the day ends", "medium": "tomorrow go to sector 1"}),  # day 1
        _reply("wait"),                                       # day 2, goals untouched
        _reply("warp", {"short": "warp toward sector 1", "medium": "buy a CargoTran"}),  # day 2, re-plan
        _reply("wait"),                                       # day 2 again
    ])

    async def fake_call(prompt: str) -> str:
        prompts.append(prompt)
        return next(replies)

    monkeypatch.setattr(agent, "_call", fake_call)
    goals_d1 = {"short": "", "medium": "", "long": ""}
    goals_old = {"short": "wait until the day ends", "medium": "tomorrow go to sector 1", "long": ""}
    goals_new = {"short": "warp toward sector 1", "medium": "buy a CargoTran", "long": ""}

    a1 = asyncio.run(agent.act(_obs(day=1, turns_remaining=2, goals=goals_d1)))
    assert a1.kind == ActionKind.WAIT and agent.goals_day == 1
    assert "NEW DAY" not in prompts[0]

    asyncio.run(agent.act(_obs(day=2, turns_remaining=50, goals=goals_old)))
    assert "NEW DAY 2" in prompts[1] and agent.goals_day == 1

    asyncio.run(agent.act(_obs(day=2, turns_remaining=49, goals=goals_old)))
    assert "NEW DAY 2" in prompts[2]
    assert agent.goals_day == 2

    asyncio.run(agent.act(_obs(day=2, turns_remaining=46, goals=goals_new)))
    assert "NEW DAY" not in prompts[3]


def test_prompt_unchanged_when_no_notice(monkeypatch):
    """No notice -> the exact format_observation text (code paths and digests untouched)."""
    agent = LLMAgent("P7", "Grok", provider="xai", model="test-model")
    seen: list[str] = []

    async def fake_call(prompt: str) -> str:
        seen.append(prompt)
        return _reply("wait")

    monkeypatch.setattr(agent, "_call", fake_call)
    obs = _obs(day=3, goals={"short": "trade 39<->391", "medium": "", "long": ""})
    asyncio.run(agent.act(obs))  # first act: goals_day := 3, no notice
    assert seen[0] == format_observation(obs)
    assert llm_mod.new_day_goal_notice is new_day_goal_notice


def test_wait_streak_restarts_each_day():
    waits: dict[str, int] = {}
    days: dict[str, int] = {}
    # day 1 ends with two waits (P7 at seq 20-21)
    assert note_wait_streak(waits, days, "P7", 1, True) == 1
    assert note_wait_streak(waits, days, "P7", 1, True) == 2
    # day 2: the first wait starts a new streak instead of reaching 3
    assert note_wait_streak(waits, days, "P7", 2, True) == 1
    assert note_wait_streak(waits, days, "P7", 2, True) == 2
    assert note_wait_streak(waits, days, "P7", 2, True) == 3
    assert note_wait_streak(waits, days, "P7", 2, True) == 4  # stand-down threshold, same day only
    # any other action (or a failed wait) resets
    assert note_wait_streak(waits, days, "P7", 2, False) == 0
    assert note_wait_streak(waits, days, "P7", 2, True) == 1
    # seats are independent
    assert note_wait_streak(waits, days, "P5", 2, True) == 1
    assert waits["P7"] == 1
