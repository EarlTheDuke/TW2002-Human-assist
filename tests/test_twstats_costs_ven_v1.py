"""Ven 2026-10-24 GameA TWSTATS [Costs]: photon missile and atomic detonator.

docs/playtests/twgs-live/twstats-costs-ven.txt
Stored prices stay 12,000 and 60,000. The live card is hardware_price_live().
SOURCE-CONFLICT with the cabal sample (photon 160,000, detonator 60,000).
"""

from __future__ import annotations

import re
from pathlib import Path

import tw2k.engine.constants as K
from tw2k.agents.prompts import get_system_prompt
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, Ship, ShipClass
from tw2k.server.reference import _prices

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "docs" / "playtests" / "twgs-live" / "twstats-costs-ven.txt"
COST_LINE = re.compile(r"^([A-Za-z0-9' /.]+)=([0-9,]+) cr$")


def _capture() -> str:
    return CAPTURE.read_text(encoding="utf-8")


def _costs(text: str) -> dict[str, int]:
    found: dict[str, int] = {}
    for line in text.splitlines():
        match = COST_LINE.match(line.strip())
        if match:
            found[match.group(1)] = int(match.group(2).replace(",", ""))
    return found


def _world(ship: Ship | None = None, credits: int = 200_000):
    universe = generate_universe(
        GameConfig(seed=4, universe_size=20, max_days=3, enable_planets=False, enable_ferrengi=False)
    )
    player = Player(
        id="P1",
        name="Trader",
        ship=ship or Ship(ship_class=ShipClass.MISSILE_FRIGATE),
        credits=credits,
        experience=0,
    )
    player.sector_id = K.STARDOCK_SECTOR
    universe.players["P1"] = player
    universe.sectors[K.STARDOCK_SECTOR].occupant_ids.append("P1")
    return universe, player


def test_capture_lines_are_the_live_card() -> None:
    text = _capture()
    assert "[Costs]" in text
    assert "Photon Missile=40,000 cr" in text
    assert "Atomic Detonator=15,000 cr" in text
    costs = _costs(text)
    assert costs["Photon Missile"] == 40_000
    assert costs["Atomic Detonator"] == 15_000
    assert K.HARDWARE_PRICE_MODE == "legacy"
    assert K.PHOTON_MISSILE_COST == 12_000
    assert K.ATOMIC_DETONATOR_COST == 60_000
    assert costs["Photon Missile"] == K.PHOTON_MISSILE_COST_LIVE
    assert costs["Atomic Detonator"] == K.ATOMIC_DETONATOR_COST_LIVE
    assert K.photon_missile_cost() == K.PHOTON_MISSILE_COST
    assert K.atomic_detonator_cost() == K.ATOMIC_DETONATOR_COST
    assert "photon_missile_live" not in K.V311_PROFILE_HELPERS
    assert "atomic_detonator_price_live" not in K.V311_PROFILE_HELPERS
    assert K.V311_PROFILE_HELPERS["hardware_price_live"][0] == "HARDWARE_PRICE_MODE"


def test_live_card_quotes_the_capture_and_keeps_the_other_pins(monkeypatch) -> None:
    costs = _costs(_capture())
    photon = costs["Photon Missile"]
    detonator = costs["Atomic Detonator"]
    universe, player = _world()
    prices = next(row for row in legal_actions(universe, "P1") if row.kind == "buy_equip")
    quoted = prices.params["item"]["unit_price_by"]
    assert quoted["photon_missiles"] == 12_000
    assert quoted["atomic_detonator"] == 60_000
    assert quoted["armid_mines"] == 100
    assert quoted["limpet_mines"] == 250
    assert quoted["genesis"] == 25_000
    bare = player.net_worth
    player.ship.photon_missiles = 1
    player.ship.atomic_detonators = 1
    assert player.net_worth - bare == 12_000 + 60_000
    assert "photon_missiles 12,000 cr each" in get_system_prompt()
    assert "atomic_detonator 60,000 cr each" in get_system_prompt()

    monkeypatch.setattr(K, "HARDWARE_PRICE_MODE", "live")
    assert K.HARDWARE_PRICE_MODE == "live"
    assert K.photon_missile_cost() == photon
    assert K.atomic_detonator_cost() == detonator
    assert K.PHOTON_MISSILE_COST == 12_000
    assert K.ATOMIC_DETONATOR_COST == 60_000
    assert K.armid_mine_cost() == 1_000
    assert K.limpet_mine_cost() == 10_000
    assert K.genesis_torpedo_cost() == 20_000
    assert K.ether_probe_cost() == 3_000
    assert K.ATOMIC_MINE_COST == 4_000
    assert K.armid_hit_damage() == 30
    live_quote = next(row for row in legal_actions(universe, "P1") if row.kind == "buy_equip")
    live_prices = live_quote.params["item"]["unit_price_by"]
    assert live_prices["photon_missiles"] == photon
    assert live_prices["atomic_detonator"] == detonator
    assert live_prices["armid_mines"] == 1_000
    sheet = {row["name"]: row["price"] for row in _prices("missile_frigate", 20, 1)}
    assert sheet["Photon missile"] == photon
    assert sheet["Atomic detonator"] == detonator
    assert player.net_worth - bare == photon + detonator
    assert f"photon_missiles {photon:,} cr each" in get_system_prompt()
    assert f"atomic_detonator {detonator:,} cr each" in get_system_prompt()

    before = player.credits
    bought_photon = apply_action(
        universe, "P1", Action(kind=ActionKind.BUY_EQUIP, args={"item": "photon_missiles", "qty": 1})
    )
    assert bought_photon.ok, bought_photon.error
    bought_detonator = apply_action(
        universe, "P1", Action(kind=ActionKind.BUY_EQUIP, args={"item": "atomic_detonator", "qty": 1})
    )
    assert bought_detonator.ok, bought_detonator.error
    assert before - player.credits == photon + detonator
    assert player.ship.photon_missiles == 2
    assert player.ship.atomic_detonators == 2


def test_v311_and_live_profile_use_the_card_and_detect_gear_does_not(monkeypatch) -> None:
    costs = _costs(_capture())
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.HARDWARE_PRICE_MODE == "legacy"
    assert K.photon_missile_cost() == costs["Photon Missile"]
    assert K.atomic_detonator_cost() == costs["Atomic Detonator"]

    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    assert K.photon_missile_cost() == costs["Photon Missile"]
    assert K.atomic_detonator_cost() == costs["Atomic Detonator"]

    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    monkeypatch.setattr(K, "DETECT_GEAR_MODE", "live")
    assert K.photon_missile_cost() == 12_000
    assert K.atomic_detonator_cost() == 60_000
    assert K.disruptor_cost() == 6_000
    assert K.psychic_probe_cost() == 10_000


def test_notes_record_the_source_conflict() -> None:
    text = _capture()
    assert "Photon Missile=40,000 cr" in text
    assert "Atomic Detonator=15,000 cr" in text
    both = [
        ROOT / "docs/plans/GAP_MAP.md",
        ROOT / "docs/reference/tw2002/GAP_MAP.md",
        ROOT / "docs/plans/gap-map-refresh-v6.md",
        ROOT / "docs/plans/V311_SOURCE_CONFLICTS.md",
        ROOT / "docs/plans/v311-profile-v1.md",
        ROOT / "docs/plans/live-twgs-test-queue-v1.md",
    ]
    for path in both:
        body = path.read_text(encoding="utf-8")
        assert "SOURCE-CONFLICT" in body
        assert "40,000" in body
        assert "15,000" in body
        assert "hardware_price_live" in body
    conflicts = (ROOT / "docs/plans/V311_SOURCE_CONFLICTS.md").read_text(encoding="utf-8")
    assert "Photon Missile=40,000 cr" in conflicts
    assert "Atomic Detonator=15,000 cr" in conflicts
    assert "DIFFERENT" in conflicts
    hardware = (ROOT / "docs/playtests/ships/SHIP_HARDWARE.md").read_text(encoding="utf-8")
    assert "photon_missile_cost" in hardware
    detonator = (ROOT / "docs/playtests/ships/SHIP_HARDWARE_V2.md").read_text(encoding="utf-8")
    assert "atomic_detonator_cost" in detonator
    assert "60_000" in detonator or "60,000" in detonator
