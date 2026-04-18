"""Tests for the stage-aware prompt wiring in `tw2k.agents.prompts`.

We build minimal `Observation` fakes with `Observation.model_construct` — this
skips Pydantic validation so we only need to set the fields we actually care
about per test. (Building a full Observation via the real engine is expensive
and would couple these tests to the observation builder.)
"""

from __future__ import annotations

import json
from typing import Any

from tw2k.agents.prompts import SYSTEM_PROMPT, format_observation, stage_hint
from tw2k.engine.observation import Observation


def _obs(**overrides: Any) -> Observation:
    """Build a minimal Observation via model_construct (no validation)."""
    defaults: dict[str, Any] = {
        "day": 1,
        "tick": 0,
        "max_days": 6,
        "finished": False,
        "self_id": "P1",
        "self_name": "Tester",
        "credits": 20_000,
        "alignment": 0,
        "alignment_label": "Neutral",
        "experience": 0,
        "rank": "Civilian",
        "turns_remaining": 1000,
        "turns_per_day": 1000,
        "ship": {"class": "merchant_cruiser", "holds": 20, "cargo": {}},
        "corp_ticker": None,
        "planet_landed": None,
        "scratchpad": "",
        "alive": True,
        "net_worth": 40_000,
        "owned_planets": [],
        "sector": {"id": 1, "warps_out": [2, 3], "is_fedspace": True, "occupants": [], "port": None, "planets": []},
        "adjacent": [],
        "known_ports": [],
        "other_players": [],
        "inbox": [],
        "recent_events": [],
        "alliances": [],
        "corp": None,
        "deaths": 0,
        "max_deaths": 3,
        "limpets_owned": [],
        "probe_log": [],
        "action_hint": "",
    }
    defaults.update(overrides)
    return Observation.model_construct(**defaults)


# ---------------------------------------------------------------------------
# A. SYSTEM_PROMPT roadmap
# ---------------------------------------------------------------------------


def test_system_prompt_contains_all_five_stages():
    for label in (
        "S1 Opening Trades",
        "S2 Capital Build",
        "S3 Establish a Home",
        "S4 Fortify & Form",
        "S5 Project Power",
    ):
        assert label in SYSTEM_PROMPT, f"missing stage label in SYSTEM_PROMPT: {label}"
    assert "YOUR ROADMAP (5 STAGES)" in SYSTEM_PROMPT
    assert "Turns = money" in SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# B. stage_hint decision rules
# ---------------------------------------------------------------------------


def test_stage_hint_s1_fresh_agent():
    obs = _obs(day=1, credits=20_000, net_worth=20_000, owned_planets=[])
    hint = stage_hint(obs)
    assert hint["stage"] == "S1"
    assert hint["label"] == "Opening Trades"
    assert "next_milestone" in hint


def test_stage_hint_s2_after_capital_build():
    obs = _obs(day=2, credits=250_000, net_worth=250_000, owned_planets=[])
    hint = stage_hint(obs)
    assert hint["stage"] == "S2"
    assert hint["label"] == "Capital Build"


def test_stage_hint_s3_with_planet_no_citadel():
    obs = _obs(
        day=3,
        credits=300_000,
        net_worth=300_000,
        owned_planets=[{"id": 7, "sector_id": 42, "citadel_level": 0, "citadel_target": 1}],
    )
    hint = stage_hint(obs)
    assert hint["stage"] == "S3"
    assert hint["label"] == "Establish a Home"


def test_stage_hint_s4_citadel_l2():
    obs = _obs(
        day=4,
        credits=900_000,
        net_worth=1_200_000,
        owned_planets=[{"id": 7, "sector_id": 42, "citadel_level": 2, "citadel_target": 2}],
    )
    hint = stage_hint(obs)
    assert hint["stage"] == "S4"
    assert hint["label"] == "Fortify & Form"


def test_stage_hint_s5_citadel_l3():
    obs = _obs(
        day=5,
        credits=2_000_000,
        net_worth=2_500_000,
        owned_planets=[{"id": 7, "sector_id": 42, "citadel_level": 3, "citadel_target": 3}],
    )
    hint = stage_hint(obs)
    assert hint["stage"] == "S5"
    assert hint["label"] == "Project Power"


def test_stage_hint_s5_flagship_triggers_without_citadel():
    obs = _obs(
        day=5,
        credits=1_000_000,
        net_worth=1_500_000,
        ship={"class": "imperial_starship", "holds": 80, "cargo": {}},
        owned_planets=[],
    )
    assert stage_hint(obs)["stage"] == "S5"


def test_stage_hint_s4_corp_without_citadel():
    obs = _obs(day=3, credits=600_000, net_worth=600_000, corp_ticker="CAB", owned_planets=[])
    assert stage_hint(obs)["stage"] == "S4"


def test_eliminated_player_stage():
    obs = _obs(alive=False, deaths=3, max_deaths=3)
    hint = stage_hint(obs)
    assert hint["stage"] == "ELIMINATED"
    assert "Respawn" in hint["next_milestone"]


# ---------------------------------------------------------------------------
# C. format_observation injects stage_hint
# ---------------------------------------------------------------------------


def test_format_observation_includes_stage_hint():
    obs = _obs(day=1, credits=20_000, net_worth=40_000)
    rendered = format_observation(obs, compact=True)
    assert "stage_hint" in rendered
    payload = json.loads(rendered)
    assert "stage_hint" in payload
    assert payload["stage_hint"]["stage"] == "S1"
    keys = list(payload.keys())
    assert keys.index("stage_hint") == keys.index("self") + 1, (
        f"stage_hint should sit right after 'self' in the payload; got order {keys}"
    )
