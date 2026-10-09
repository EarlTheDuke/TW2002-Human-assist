"""Quasar reminder for an LLM seat. Off mode adds no line."""

from __future__ import annotations

import hashlib

from tw2k.agents.llm import quasar_notice
from tw2k.engine import constants as K
from tw2k.engine.observation import Observation

_LINE = "Your quasar cannon is unarmed here: set_quasar_sector / set_quasar_atm"


def _obs(*, ore=500, level=3, sector_pct=0, atm_pct=0, landed=7, corp=None, planet_corp=None, owned=True):
    plan = {
        "id": 7,
        "citadel_level": level,
        "quasar_sector_pct": sector_pct,
        "quasar_atm_pct": atm_pct,
        "stockpile": {"fuel_ore": ore},
        "corp_ticker": planet_corp,
    }
    return Observation.model_construct(
        finished=False,
        turns_remaining=10,
        planet_landed=landed,
        corp_ticker=corp,
        owned_planets=[plan] if owned else [],
        sector={"planets": [] if owned else [plan]},
    )


def _digest(obs) -> str:
    extra = quasar_notice(obs)
    body = obs.model_dump_json() + (("\n" + extra) if extra else "")
    return hashlib.sha256(body.encode()).hexdigest()


def test_qn1_off_digest_is_the_observation_alone(monkeypatch) -> None:
    monkeypatch.setattr(K, "LLM_QUASAR_NUDGE_MODE", "off")
    obs = _obs()
    assert quasar_notice(obs) == ""
    assert _digest(obs) == hashlib.sha256(obs.model_dump_json().encode()).hexdigest()


def test_qn2_on_digest_moves_and_names_both_verbs() -> None:
    obs = _obs()
    assert quasar_notice(obs) == _LINE
    assert _digest(obs) != hashlib.sha256(obs.model_dump_json().encode()).hexdigest()


def test_qn3_ore_499_hides_and_500_shows() -> None:
    # Plant: a `>` against the floor hides the line at 500.
    assert quasar_notice(_obs(ore=499)) == ""
    assert quasar_notice(_obs(ore=500)) == _LINE


def test_qn4_citadel_level_2_hides() -> None:
    assert quasar_notice(_obs(level=2)) == ""
    assert quasar_notice(_obs(level=3)) == _LINE


def test_qn5_floor_reverted_to_2000_hides_500_ore(monkeypatch) -> None:
    monkeypatch.setattr(K, "LLM_QUASAR_NUDGE_ORE_FLOOR", 2000)
    assert quasar_notice(_obs(ore=500)) == ""
    assert quasar_notice(_obs(ore=2000)) == _LINE


def test_qn6_both_cannons_set_hides_the_line() -> None:
    assert quasar_notice(_obs(sector_pct=30, atm_pct=60)) == ""
    assert quasar_notice(_obs(sector_pct=30, atm_pct=0)) == _LINE
    assert quasar_notice(_obs(sector_pct=0, atm_pct=60)) == _LINE


def test_qn7_not_landed_hides() -> None:
    assert quasar_notice(_obs(landed=None)) == ""


def test_qn8_a_corp_planet_shows_and_another_corp_does_not() -> None:
    shown = _obs(owned=False, corp="AAA", planet_corp="AAA")
    hidden = _obs(owned=False, corp="AAA", planet_corp="BBB")
    assert quasar_notice(shown) == _LINE
    assert quasar_notice(hidden) == ""
