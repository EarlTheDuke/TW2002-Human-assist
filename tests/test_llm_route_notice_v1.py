"""fullgame3 P7: an LLM seat 10 hops from StarDock hand-picked single warps for 2+ days.

It started in sector 7 with 250k cr in the starter hull, warped 94 <-> 160 <-> 280 ... "mapping
toward sector 1", and reached StarDock only on day 3 with zero trades. The prompt lists
`plot_course` but never its `execute` arg (and _compact_legal drops params), so it never knew one
action flies the whole route. LLMAgent now adds an AUTOPILOT line (K.LLM_ROUTE_NOTICE, agent-side
only): for the starter-hull StarDock errand, and for a single-warp loop that revisits sectors.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from tw2k.agents import llm as llm_mod
from tw2k.agents.llm import ROUTE_LOOP_WINDOW, LLMAgent, route_notice
from tw2k.engine import GameConfig, build_observation, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.models import Player
from tw2k.engine.runner import _bfs_path


def _universe():
    return generate_universe(GameConfig(seed=7, universe_size=60, max_days=8, turns_per_day=50))


def _far_sector(u) -> int:
    far = max((s for s in u.sectors if s != K.STARDOCK_SECTOR), key=lambda s: len(_bfs_path(u, s, 1) or []))
    assert len(_bfs_path(u, far, 1)) >= 3
    return far


def _obs(sector: int | None = None, credits: int = 250_000, turns_today: int = 0, **update):
    u = _universe()
    sid = _far_sector(u) if sector is None else sector
    u.players["P7"] = Player(id="P7", name="Grok", agent_kind="external", sector_id=sid,
                             credits=credits, turns_today=turns_today, turns_per_day=50)
    obs = build_observation(u, "P7")
    return obs.model_copy(update=update) if update else obs


def test_stardock_errand_names_execute():
    obs = _obs()
    assert obs.ship["class"] == K.STARTING_SHIP
    text = route_notice(obs, [])
    assert text.startswith("AUTOPILOT TO STARDOCK")
    assert 'plot_course {"target":1,"execute":true}' in text
    assert "do NOT need to explore" in text
    assert text.isascii()


@pytest.mark.parametrize("kwargs", [
    {"sector": K.STARDOCK_SECTOR},          # already there
    {"credits": 15_000},                    # no upgrade affordable
    {"turns_today": 49},                    # first hop unaffordable (execute illegal)
    {"turns_today": 50},                    # no turns left
])
def test_no_stardock_notice(kwargs):
    assert route_notice(_obs(**kwargs), []) == ""


def test_switch_off_and_finished(monkeypatch):
    assert route_notice(_obs(finished=True), []) == ""
    monkeypatch.setattr(K, "LLM_ROUTE_NOTICE", False)
    assert route_notice(_obs(), []) == ""


def _loop_trail(day: int, here: int, other: int, kind: str = "warp"):
    seq = [here if i % 2 == 0 else other for i in range(ROUTE_LOOP_WINDOW)]
    return [(day, s, kind) for s in seq]


def test_single_warp_loop_check():
    obs = _obs(credits=15_000)              # no StarDock errand: only the loop case can fire
    here = obs.sector["id"]
    text = route_notice(obs, _loop_trail(obs.day, here, 999))
    assert text.startswith(f"LOOP CHECK: your last {ROUTE_LOOP_WINDOW} turns")
    assert str(here) in text and '"execute":true' in text


@pytest.mark.parametrize("trail_kind, day_shift, n", [
    ("trade", 0, ROUTE_LOOP_WINDOW),        # not all warps
    ("autopilot", 0, ROUTE_LOOP_WINDOW),    # already flying the autopilot
    ("warp", -1, ROUTE_LOOP_WINDOW),        # yesterday's warps
    ("warp", 0, ROUTE_LOOP_WINDOW - 1),     # too short
])
def test_no_loop_check(trail_kind, day_shift, n):
    obs = _obs(credits=15_000)
    trail = _loop_trail(obs.day + day_shift, obs.sector["id"], 999, trail_kind)[-n:]
    assert route_notice(obs, trail) == ""


def test_no_loop_check_without_revisit():
    obs = _obs(credits=15_000)
    trail = [(obs.day, 900 + i, "warp") for i in range(ROUTE_LOOP_WINDOW)]
    assert route_notice(obs, trail) == ""


def test_llm_agent_prompt_and_trail(monkeypatch):
    agent = LLMAgent("P7", "Grok", provider="xai", model="test-model")
    prompts: list[str] = []
    replies = iter([
        json.dumps({"thought": "t", "action": {"kind": "plot_course", "args": {"target": 1, "execute": True}}}),
        json.dumps({"thought": "t", "action": {"kind": "wait", "args": {}}}),
    ])

    async def fake_call(prompt: str) -> str:
        prompts.append(prompt)
        return next(replies)

    monkeypatch.setattr(agent, "_call", fake_call)
    far = _obs()
    asyncio.run(agent.act(far))
    assert "AUTOPILOT TO STARDOCK" in prompts[0]
    assert agent.route_trail == [(far.day, far.sector["id"], "autopilot")]

    dock = _obs(sector=K.STARDOCK_SECTOR)
    asyncio.run(agent.act(dock))
    assert "AUTOPILOT TO STARDOCK" not in prompts[1]
    assert "FIRST PLANET" in prompts[1]
    assert agent.route_trail[-1] == (dock.day, K.STARDOCK_SECTOR, "wait")
    assert llm_mod.ROUTE_LOOP_WINDOW == ROUTE_LOOP_WINDOW
