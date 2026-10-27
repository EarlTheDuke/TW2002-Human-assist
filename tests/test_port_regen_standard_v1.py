"""GAP 2.8. The printed standard is 5 percent, applied once.

v3.05: TEDIT regen runs from 1 to 200 percent a day. Standard is 5 percent.
Cabal twgs.html shows one game at 1 percent. That sample is not the default.
PORT_REGEN_MODE (row 22) already adds 5 percent of the maximum once.
PORT_DRAIN_CURVE_MODE (row 224) restocks 10 percent of the maximum once while
it is on. That 10 percent is the economy2 pair (261 on 2610), not 5 percent
applied twice. The old pull toward 30 percent of max is not in the function.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.engine.economy import regenerate_ports
from tw2k.engine.models import Commodity, GameConfig, Port, PortClass, PortStock, Sector, Universe

pytestmark = pytest.mark.legacy_profile

ROOT = Path(__file__).resolve().parents[1]
FUEL = Commodity.FUEL_ORE
EQ = Commodity.EQUIPMENT


def _world(fuel_current: int, eq_current: int, fuel_prod: int, eq_prod: int, maximum: int = 1000) -> tuple[Universe, Port]:
    # Class 1 buys fuel and sells equipment on both the stored map and the live map.
    port = Port(
        class_id=PortClass.CLASS_1_BSS,
        stock={
            FUEL: PortStock(current=fuel_current, maximum=maximum),
            EQ: PortStock(current=eq_current, maximum=maximum),
        },
        productivity={FUEL: fuel_prod, EQ: eq_prod},
        mcic={FUEL: -40, EQ: 40},
    )
    universe = Universe(config=GameConfig(seed=1), sectors={1: Sector(id=1, port=port)})
    return universe, port


def test_stored_rate_stays_the_printed_standard() -> None:
    assert K.PORT_REGEN_MODE == "legacy"
    assert K.PORT_DRAIN_CURVE_MODE == "legacy"
    assert K.PORT_REGEN_PER_DAY == 0.05
    assert K.PORT_REGEN_PER_DAY != 0.01
    assert K.V311_PORT_REGEN_PER_DAY == 0.10
    assert K.port_regen_live() is False
    assert K.port_drain_curve_live() is False
    assert K.port_regen_per_day() == 0.05


def test_legacy_adds_five_percent_of_productivity_once() -> None:
    universe, port = _world(fuel_current=0, eq_current=100, fuel_prod=200, eq_prod=200)
    assert port.buys(FUEL) and port.sells(EQ)
    regenerate_ports(universe)
    assert port.stock[FUEL].current == 10
    assert port.stock[EQ].current == 110
    regenerate_ports(universe)
    assert port.stock[FUEL].current == 20
    assert port.stock[EQ].current == 120


def test_legacy_buy_port_does_not_hold_at_thirty_percent() -> None:
    universe, port = _world(fuel_current=300, eq_current=100, fuel_prod=200, eq_prod=0)
    regenerate_ports(universe)
    assert port.stock[FUEL].current == 310
    assert port.stock[EQ].current == 100
    assert port.stock[FUEL].current != round(1000 * 0.30)


def test_live_switch_is_five_percent_of_max_once(monkeypatch) -> None:
    monkeypatch.setattr(K, "PORT_REGEN_MODE", "live")
    assert K.port_regen_live() is True
    assert K.port_drain_curve_live() is False
    assert K.port_regen_per_day() == 0.05
    universe, port = _world(fuel_current=100, eq_current=100, fuel_prod=800, eq_prod=800)
    regenerate_ports(universe)
    assert port.stock[FUEL].current == 150
    assert port.stock[EQ].current == 150


def test_v311_keeps_the_drain_curve_ten_percent_once(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.port_regen_live() is True
    assert K.port_drain_curve_live() is True
    assert K.port_stock_fidelity_live() is True
    assert K.port_regen_per_day() == 0.10
    universe, port = _world(fuel_current=800, eq_current=100, fuel_prod=50, eq_prod=50)
    assert port.buys(FUEL) and port.sells(EQ)
    regenerate_ports(universe)
    assert port.stock[FUEL].current == 700
    assert port.stock[EQ].current == 200
    assert port.stock[FUEL].current != round(1000 * 0.30)


def test_gap_records_the_one_percent_sample_and_the_existing_switch() -> None:
    for path in (
        ROOT / "docs" / "plans" / "GAP_MAP.md",
        ROOT / "docs" / "reference" / "tw2002" / "GAP_MAP.md",
    ):
        row = next(line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("| 2.8 "))
        assert "Match-behind-flag" in row
        assert "| Partial |" not in row
        assert "1%" in row
        assert "PORT_REGEN_MODE" in row
        assert "row 224" in row
        assert "not 5% applied twice" in row
    conflicts = (ROOT / "docs" / "plans" / "V311_SOURCE_CONFLICTS.md").read_text(encoding="utf-8")
    assert "1 percent" in conflicts
    assert "not 5 percent applied twice" in conflicts
    plan = (ROOT / "docs" / "plans" / "v311-profile-v1.md").read_text(encoding="utf-8")
    assert "GAP 2.8 adds no switch" in plan
    assert "`PORT_REGEN_MODE`" in plan
    assert "`port_regen_live`" in plan
