"""Terra can open at 30,000 and pack 1,000 colonists in a hold. The switch stays off."""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tests.test_class0_terra_v1 import _act, _world
from tw2k.engine import ActionKind
from tw2k.engine.class0 import regen_terra
from tw2k.engine.models import Commodity

pytestmark = pytest.mark.legacy_profile


def test_legacy_terra_opens_full_and_one_colonist_fills_a_hold():
    _prior_terra_colonist_mode = K.TERRA_COLONIST_MODE
    try:
        K.TERRA_COLONIST_MODE = "legacy"
        universe = _world()
        assert universe.terra_colonists == 100_000
        result = _act(universe, "A", ActionKind.TERRA_COLONISTS, mode="take", qty=2)
        cargo = universe.players["A"].ship.cargo.get(Commodity.COLONISTS)
        assert result.ok
        assert cargo == 2
        assert universe.players["A"].ship.cargo_free == 48
    finally:
        K.TERRA_COLONIST_MODE = _prior_terra_colonist_mode


def test_live_opens_at_30000_and_packs_1000_per_hold():
    _prior_terra_colonist_mode = K.TERRA_COLONIST_MODE
    try:
        try:
            K.TERRA_COLONIST_MODE = "live"
            universe = _world()
            player = universe.players["A"]
            credits = player.credits
            assert universe.terra_colonists == 30_000
            assert universe.terra_max == 100_000
            result = _act(universe, "A", ActionKind.TERRA_COLONISTS, mode="take", qty=2)
            assert result.ok and result.turns_spent == 1
            assert player.ship.cargo.get(Commodity.COLONISTS) == 2_000
            assert player.ship.cargo_free == 48
            assert universe.terra_colonists == 28_000
            assert player.credits == credits
        finally:
            K.TERRA_COLONIST_MODE = "legacy"
    finally:
        K.TERRA_COLONIST_MODE = _prior_terra_colonist_mode


def test_live_day_adds_750():
    _prior_terra_colonist_mode = K.TERRA_COLONIST_MODE
    try:
        try:
            K.TERRA_COLONIST_MODE = "live"
            universe = _world()
            universe.terra_colonists = 1_000
            regen_terra(universe)
            assert universe.terra_colonists == 1_750
        finally:
            K.TERRA_COLONIST_MODE = "legacy"
    finally:
        K.TERRA_COLONIST_MODE = _prior_terra_colonist_mode


def test_live_leave_returns_1000_per_hold():
    _prior_terra_colonist_mode = K.TERRA_COLONIST_MODE
    try:
        try:
            K.TERRA_COLONIST_MODE = "live"
            universe = _world()
            _act(universe, "A", ActionKind.TERRA_COLONISTS, mode="take", qty=2)
            result = _act(universe, "A", ActionKind.TERRA_COLONISTS, mode="leave", qty=1)
            assert result.ok
            assert universe.players["A"].ship.cargo.get(Commodity.COLONISTS) == 1_000
            assert universe.terra_colonists == 29_000
        finally:
            K.TERRA_COLONIST_MODE = "legacy"
    finally:
        K.TERRA_COLONIST_MODE = _prior_terra_colonist_mode
