"""Atomic detonator shop price.

Ven GameA TWSTATS v3.34b lists Atomic Detonator at 15,000 credits under
[Costs] (docs/playtests/twgs-live/twstats-costs-ven.txt).

The stored constant stays 60,000. atomic_detonator_cost() returns 15,000
when atomic_detonator_live() is on: ATOMIC_DETONATOR_MODE live,
TW2002_LIVE_PROFILE live, or V311_PROFILE v311. HARDWARE_PRICE_MODE does
not move this price. The port-nuke atomic mine stays a different item.
No new profile row.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import GameConfig, Player, Ship
from tw2k.engine.runner import apply_action
from tw2k.engine.universe import generate_universe
from tw2k.server.reference import game_reference

pytestmark = pytest.mark.legacy_profile

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "docs" / "playtests" / "twgs-live" / "twstats-costs-ven.txt"


def _ven_atomic_cost() -> int:
    text = CAPTURE.read_text(encoding="utf-8")
    match = re.search(r"\[Costs\].*?Atomic Detonator=([0-9,]+) cr", text, re.S)
    assert match, text
    return int(match.group(1).replace(",", ""))


def _quoted_price() -> int:
    rows = next(section for section in game_reference()["sections"] if section["id"] == "prices")["rows"]
    return next(row["price"] for row in rows if row["name"] == "Atomic detonator")


def _dock(credits: int = 80_000):
    universe = generate_universe(
        GameConfig(seed=4, universe_size=20, max_days=3, enable_planets=False, enable_ferrengi=False)
    )
    player = Player(id="P1", name="Trader", ship=Ship(), credits=credits, experience=0)
    dock = int(K.stardock_sector_of(universe))
    player.sector_id = dock
    universe.players["P1"] = player
    universe.sectors[dock].occupant_ids.append("P1")
    return universe, player


def _buy_one(universe, player):
    before = int(player.net_worth)
    bought = apply_action(
        universe,
        "P1",
        Action(kind=ActionKind.BUY_EQUIP, args={"item": "atomic_detonator", "qty": 1}),
    )
    assert bought.ok, bought.error
    return before


def _legal_price(universe) -> int:
    buy = next(action for action in legal_actions(universe, "P1") if action.kind == ActionKind.BUY_EQUIP)
    return int(buy.params["item"]["unit_price_by"]["atomic_detonator"])


def test_ven_capture_is_15_000() -> None:
    assert _ven_atomic_cost() == 15_000
    assert K.ATOMIC_DETONATOR_COST_LIVE == 15_000


def test_stored_default_stays_60_000() -> None:
    assert K.ATOMIC_DETONATOR_MODE == "legacy"
    assert K.ATOMIC_DETONATOR_COST == 60_000
    assert K.atomic_detonator_live() is False
    assert K.atomic_detonator_cost() == 60_000
    assert K.hardware_v2_prices()["atomic_detonator"] == 60_000
    assert _quoted_price() == 60_000
    assert K.ATOMIC_MINE_COST == 4_000
    assert K.PHOTON_MISSILE_COST == 12_000
    assert "atomic_detonator_cost" not in K.V311_PROFILE_HELPERS


def test_live_gate_and_profiles_charge_15_000(monkeypatch) -> None:
    ven = _ven_atomic_cost()
    monkeypatch.setattr(K, "ATOMIC_DETONATOR_MODE", "live")
    assert K.V311_PROFILE == "legacy" and K.TW2002_LIVE_PROFILE == "legacy"
    assert K.atomic_detonator_cost() == ven
    assert K.hardware_v2_prices()["atomic_detonator"] == ven
    assert K.armid_mine_cost() == 100

    monkeypatch.setattr(K, "ATOMIC_DETONATOR_MODE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    assert K.ATOMIC_DETONATOR_MODE == "legacy"
    assert K.atomic_detonator_cost() == ven

    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.ATOMIC_DETONATOR_MODE == "legacy"
    assert K.HARDWARE_PRICE_MODE == "legacy"
    assert K.atomic_detonator_live() is True
    assert K.atomic_detonator_cost() == ven
    assert _quoted_price() == ven


def test_hardware_price_mode_alone_leaves_atomic_at_60_000(monkeypatch) -> None:
    monkeypatch.setattr(K, "HARDWARE_PRICE_MODE", "live")
    assert K.hardware_price_live() is True
    assert K.atomic_detonator_live() is False
    assert K.atomic_mines_sold() is True
    assert K.atomic_detonator_cost() == K.ATOMIC_DETONATOR_COST == 60_000
    assert K.hardware_v2_prices()["atomic_detonator"] == 60_000
    assert K.armid_mine_cost() == 1_000
    assert K.limpet_mine_cost() == 10_000
    assert K.genesis_torpedo_cost() == 20_000
    assert K.ether_probe_cost() == 3_000
    assert K.ATOMIC_MINE_COST == 4_000
    assert K.PHOTON_MISSILE_COST == 12_000


def test_shop_charges_60_000_until_the_detonator_gate_is_on(monkeypatch) -> None:
    universe, player = _dock()
    assert _legal_price(universe) == 60_000
    before = _buy_one(universe, player)
    assert player.ship.atomic_detonators == 1
    assert player.credits == 80_000 - 60_000
    assert player.net_worth == before

    monkeypatch.setattr(K, "HARDWARE_PRICE_MODE", "live")
    universe, player = _dock()
    assert _legal_price(universe) == 60_000
    _buy_one(universe, player)
    assert player.credits == 80_000 - 60_000

    monkeypatch.setattr(K, "HARDWARE_PRICE_MODE", "legacy")
    monkeypatch.setattr(K, "ATOMIC_DETONATOR_MODE", "live")
    universe, player = _dock()
    assert _legal_price(universe) == 15_000
    before = _buy_one(universe, player)
    assert player.credits == 80_000 - 15_000
    assert player.net_worth == before
    assert K.atomic_mines_sold() is False

    monkeypatch.setattr(K, "ATOMIC_DETONATOR_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    universe, player = _dock()
    assert K.ATOMIC_DETONATOR_MODE == "legacy"
    assert _legal_price(universe) == 15_000
    _buy_one(universe, player)
    assert player.credits == 80_000 - 15_000
