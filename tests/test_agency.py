"""Agency initiative: hint level, metrics, prompt budgets."""

from __future__ import annotations

import json

import pytest

from tw2k.agents.prompts import (
    SYSTEM_PROMPT,
    _MATCH_PROMPT_MINIMAL,
    get_system_prompt,
    stage_hint,
)
from tw2k.engine.agency import hint_level, is_minimal
from tw2k.engine.match_metrics import build_match_metrics_payload
from tw2k.engine.models import Event, EventKind
from tw2k.engine.observation import Observation


def test_hint_level_defaults_full(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TW2K_HINT_LEVEL", raising=False)
    assert hint_level() == "full"
    assert not is_minimal()


def test_hint_level_minimal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TW2K_HINT_LEVEL", "minimal")
    assert hint_level() == "minimal"
    assert is_minimal()


def test_hint_level_invalid_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TW2K_HINT_LEVEL", "banana")
    assert hint_level() == "full"


def test_get_system_prompt_respects_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TW2K_HINT_LEVEL", "minimal")
    s = get_system_prompt()
    assert s == _MATCH_PROMPT_MINIMAL
    assert "docs/PLAYBOOK.md" in s
    monkeypatch.setenv("TW2K_HINT_LEVEL", "full")
    assert get_system_prompt() == SYSTEM_PROMPT


def test_stage_hint_minimal_drops_next_milestone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TW2K_HINT_LEVEL", "minimal")
    obs = Observation(
        day=1,
        tick=1,
        max_days=15,
        finished=False,
        self_id="P1",
        self_name="Test",
        credits=1000,
        alignment=0,
        alignment_label="neutral",
        experience=0,
        rank="Green",
        turns_remaining=80,
        turns_per_day=80,
        ship={"class": "merchant_cruiser", "holds": 20, "cargo": {}, "fighters": 20, "shields": 0},
        corp_ticker=None,
        planet_landed=None,
        scratchpad="",
        goals={"short": "", "medium": "", "long": ""},
        alive=True,
        net_worth=5000,
        owned_planets=[],
        sector={"id": 1, "warps_out": [2], "warps_count": 3},
        adjacent=[],
        known_ports=[],
        known_warps={},
        trade_log=[],
        trade_summary={},
        recent_failures=[],
        other_players=[],
        rivals=[],
        orphaned_planets=[],
        inbox=[],
        recent_events=[],
        alliances=[],
        corp=None,
        deaths=0,
        max_deaths=3,
        action_hint="",
    )
    h = stage_hint(obs)
    assert "stage" in h
    assert "next_milestone" not in h


def test_prompt_budget_full_under_ceiling() -> None:
    assert len(SYSTEM_PROMPT) < 50_000


def test_prompt_budget_minimal_shorter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TW2K_HINT_LEVEL", "minimal")
    minimal = get_system_prompt()
    assert len(minimal) < 20_000
    assert len(minimal) < len(SYSTEM_PROMPT)


def test_minimal_prompt_names_critical_observation_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TW2K_HINT_LEVEL", "minimal")
    s = get_system_prompt()
    for needle in (
        "sector.warps_out",
        "recent_events",
        "recent_failures",
        "action_hint",
        "known_warps",
    ):
        assert needle in s


def test_match_metrics_counts_parse_errors() -> None:
    events = [
        Event(
            seq=1,
            tick=1,
            day=1,
            kind=EventKind.AGENT_THOUGHT,
            actor_id="P1",
            payload={"thought": "[parse error] broken"},
            summary="",
        ),
        Event(
            seq=2,
            tick=2,
            day=1,
            kind=EventKind.AGENT_THOUGHT,
            actor_id="P1",
            payload={"thought": "[LLM error] 400"},
            summary="",
        ),
    ]
    p = build_match_metrics_payload(events)
    assert p["llm_health"]["parse_error_thoughts"] == 1
    assert p["llm_health"]["llm_error_thoughts"] == 1
    assert p["event_count"] == 2


def test_events_jsonl_roundtrip_for_metrics() -> None:
    ev = Event(
        seq=1,
        tick=0,
        day=1,
        kind=EventKind.GAME_START,
        payload={"players": []},
        summary="start",
    )
    row = json.loads(ev.model_dump_json())
    row["kind"] = EventKind(row["kind"])
    back = Event.model_validate(row)
    assert back.kind is EventKind.GAME_START
