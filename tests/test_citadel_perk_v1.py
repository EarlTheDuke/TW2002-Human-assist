"""Citadel perk lines, the reaction setter, and when shields fight. The switch stays off."""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tests.test_phase_abc import _make_universe
from tests.test_siege_path_v1 import _place, _planet
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import Planet, PlanetClass
from tw2k.engine.runner import apply_action

pytestmark = pytest.mark.legacy_profile


def test_legacy_keeps_the_old_lines_and_shields():
    _prior_citadel_perk_mode = K.CITADEL_PERK_MODE
    try:
        K.CITADEL_PERK_MODE = "legacy"
        assert "not yet" in K.citadel_perks()[1][2]
        early = Planet(
            id=1, sector_id=20, name="M", class_id=PlanetClass.M, shields=10, citadel_level=4,
        )
        assert K.fighting_planet_shields(early) == 10
    finally:
        K.CITADEL_PERK_MODE = _prior_citadel_perk_mode


def test_live_names_the_computer_and_the_shields():
    _prior_citadel_perk_mode = K.CITADEL_PERK_MODE
    try:
        from tw2k.agents.prompts import get_system_prompt
        try:
            K.CITADEL_PERK_MODE = "live"
            assert "not yet" not in K.citadel_perks()[1][2]
            assert "2 to 1" in K.citadel_perks()[1][2]
            assert "level 5" in K.citadel_perks()[4][2]
            assert "not yet" in K.CITADEL_PERK[1][2]
            prompt = get_system_prompt()
            assert "2 to 1" in prompt
            assert "stocked shields fight at citadel level 5" in prompt
            assert "not yet in this game" not in prompt
        finally:
            K.CITADEL_PERK_MODE = "legacy"
    finally:
        K.CITADEL_PERK_MODE = _prior_citadel_perk_mode


def test_live_reaction_waits_for_level_2():
    _prior_citadel_perk_mode = K.CITADEL_PERK_MODE
    try:
        try:
            K.CITADEL_PERK_MODE = "live"
            u, (owner, *_) = _make_universe(seed=8840)
            planet = _planet(8840, fighters=4, shields=0, level=1)
            planet.owner_id = owner.id
            _place(u, planet, owner)
            owner.planet_landed = planet.id
            denied = apply_action(u, owner.id, Action(
                kind=ActionKind.SET_MILITARY_REACTION, args={"planet_id": planet.id, "pct": 40},
            ))
            assert denied.ok is False
            assert denied.error == "combat control requires citadel level 2"
            assert planet.military_reaction_pct == 0
            planet.citadel_level = 2
            allowed = apply_action(u, owner.id, Action(
                kind=ActionKind.SET_MILITARY_REACTION, args={"planet_id": planet.id, "pct": 40},
            ))
            assert allowed.ok, allowed.error
            assert planet.military_reaction_pct == 40
        finally:
            K.CITADEL_PERK_MODE = "legacy"
    finally:
        K.CITADEL_PERK_MODE = _prior_citadel_perk_mode


def test_legacy_reaction_works_before_level_2():
    _prior_citadel_perk_mode = K.CITADEL_PERK_MODE
    try:
        K.CITADEL_PERK_MODE = "legacy"
        u, (owner, *_) = _make_universe(seed=8841)
        planet = _planet(8841, fighters=4, shields=0, level=1)
        planet.owner_id = owner.id
        _place(u, planet, owner)
        owner.planet_landed = planet.id
        allowed = apply_action(u, owner.id, Action(
            kind=ActionKind.SET_MILITARY_REACTION, args={"planet_id": planet.id, "pct": 25},
        ))
        assert allowed.ok, allowed.error
        assert planet.military_reaction_pct == 25
    finally:
        K.CITADEL_PERK_MODE = _prior_citadel_perk_mode


def test_live_shields_wait_for_level_5():
    _prior_citadel_perk_mode = K.CITADEL_PERK_MODE
    try:
        try:
            K.CITADEL_PERK_MODE = "live"
            early = Planet(
                id=1, sector_id=20, name="M", class_id=PlanetClass.M, shields=10, citadel_level=4,
            )
            ready = Planet(
                id=2, sector_id=20, name="M", class_id=PlanetClass.M, shields=10, citadel_level=5,
            )
            assert K.fighting_planet_shields(early) == 0
            assert K.fighting_planet_shields(ready) == 10
        finally:
            K.CITADEL_PERK_MODE = "legacy"
    finally:
        K.CITADEL_PERK_MODE = _prior_citadel_perk_mode
