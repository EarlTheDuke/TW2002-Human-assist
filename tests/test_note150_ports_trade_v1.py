"""NOTE 150. The cabal haggle table, which the straight line does not match.

The switch stays legacy while it is off, including when V311_PROFILE is "1".
The switch, or V311_PROFILE "v311" alone, uses the printed percent.
"""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tw2k.engine.economy import haggle_bound
from tw2k.public.manual import render

pytestmark = pytest.mark.legacy_profile


def test_haggle_table_fails_off_and_passes_on(monkeypatch) -> None:
    """GAP 2.6. Equipment at MCIC -20 is 110.2 percent. Fuel at -90 is 149.4 percent.

    The straight line gives those same offers 117.8 percent and 145.1 percent.
    A sell-port MCIC the page does not print stays on the line.
    """
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.haggle_table_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")

    def equipment() -> int:
        return haggle_bound(1_000, -20, "sell", "equipment")

    def fuel() -> int:
        return haggle_bound(1_000, -90, "sell", "fuel_ore")

    def unprinted() -> int:
        return haggle_bound(1_000, 50, "sell", "equipment")

    assert equipment() == 1_178
    assert fuel() == 1_451
    assert unprinted() == 1_295

    monkeypatch.setattr(K, "HAGGLE_TABLE_MODE", "v311")
    assert equipment() == 1_102
    assert fuel() == 1_494
    assert unprinted() == 1_295

    monkeypatch.setattr(K, "HAGGLE_TABLE_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.HAGGLE_TABLE_MODE == "legacy"
    assert K.haggle_window_live() is True
    assert equipment() == 1_102
    assert fuel() == 1_494
    assert unprinted() == 1_295


def test_manual_names_the_table() -> None:
    page = render("Galaxy War Command")
    assert "every product uses one straight line from 110 percent to 149 percent." in page
