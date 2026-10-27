"""detect-gear-v1. Prices that already match stay. The three that do not move only when the switch is on."""
import pytest

import tw2k.engine.constants as K

pytestmark = pytest.mark.legacy_profile


def test_flag_stays_legacy_and_the_matched_prices_stay() -> None:
    assert K.DETECT_GEAR_MODE == "legacy"
    assert K.detect_gear_live() is False
    assert K.DENSITY_SCANNER_COST == 2_000
    assert K.HOLO_SCANNER_COST == 25_000
    assert K.CLOAK_COST == 25_000
    assert K.BEACON_COST == 100
    assert K.BEACON_MAX_BY_HULL["merchant_cruiser"] == 50
    assert K.CORBOMITE_COST == 1_000
    assert K.ATOMIC_DETONATOR_COST == 60_000


def test_off_keeps_the_old_three() -> None:
    assert K.disruptor_cost() == 40_000
    assert K.psychic_probe_cost() == 2_500
    assert K.ether_probe_cost() == 5_000


def test_on_uses_the_measured_three(monkeypatch) -> None:
    monkeypatch.setattr(K, "DETECT_GEAR_MODE", "live")
    assert K.disruptor_cost() == 6_000
    assert K.psychic_probe_cost() == 10_000
    assert K.ether_probe_cost() == 3_000
    assert K.ATOMIC_DETONATOR_COST == 60_000
    assert K.atomic_detonator_cost() == 60_000
    assert K.DISRUPTOR_CLEAR_MAX == 12
