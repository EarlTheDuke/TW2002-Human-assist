"""Ven 2026-10-24 GameA TWSTATS [Costs]: ship TransWarp shop prices.

docs/playtests/twgs-live/twstats-costs-ven.txt
Stored cabal samples stay 12,500 / 20,000 / 9,000. The live card is
hardware_price_live(). SHIP_TW_MODE stays. Citadel transport already
matches the planet transporter constants. No shop switch for those.
"""

from __future__ import annotations

import re
from pathlib import Path

import tw2k.engine.constants as K
from tw2k.agents.prompts import get_system_prompt
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, Ship, ShipClass
from tw2k.public.manual import render
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


def _world(credits: int = 200_000, drive: str | None = None):
    universe = generate_universe(
        GameConfig(seed=4, universe_size=20, max_days=3, enable_planets=False, enable_ferrengi=False)
    )
    ship = Ship(ship_class=ShipClass.IMPERIAL_STARSHIP)
    if drive is not None:
        ship.transwarp_drive = drive
    player = Player(id="P1", name="Trader", ship=ship, credits=credits, experience=0)
    player.sector_id = K.STARDOCK_SECTOR
    universe.players["P1"] = player
    universe.sectors[K.STARDOCK_SECTOR].occupant_ids.append("P1")
    return universe, player


def _quote(universe) -> dict:
    row = next(item for item in legal_actions(universe, "P1") if item.kind == "buy_equip")
    return row.params["item"]


def test_capture_lines_are_the_live_card() -> None:
    text = _capture()
    assert "[Costs]" in text
    assert "Type I TWarp=50,000 cr" in text
    assert "Type II TWarp=80,000 cr" in text
    assert "TWarp Upgrade=10,000 cr" in text
    assert "Citadel Transport Unit=50,000 cr" in text
    assert "Citadel Transport Upgrade=25,000 cr" in text
    costs = _costs(text)
    assert costs["Type I TWarp"] == 50_000
    assert costs["Type II TWarp"] == 80_000
    assert costs["TWarp Upgrade"] == 10_000
    assert K.HARDWARE_PRICE_MODE == "legacy"
    assert K.SHIP_TW_MODE == "tw2002"
    assert K.SHIP_TW_TYPE1_COST == 12_500
    assert K.SHIP_TW_TYPE2_COST == 20_000
    assert K.SHIP_TW_UPGRADE_COST == 9_000
    assert costs["Type I TWarp"] == K.SHIP_TW_TYPE1_COST_LIVE
    assert costs["Type II TWarp"] == K.SHIP_TW_TYPE2_COST_LIVE
    assert costs["TWarp Upgrade"] == K.SHIP_TW_UPGRADE_COST_LIVE
    assert K.ship_tw_type1_cost() == K.SHIP_TW_TYPE1_COST
    assert K.ship_tw_type2_cost() == K.SHIP_TW_TYPE2_COST
    assert K.ship_tw_upgrade_cost() == K.SHIP_TW_UPGRADE_COST
    assert "ship_tw_price_live" not in K.V311_PROFILE_HELPERS
    assert K.V311_PROFILE_HELPERS["hardware_price_live"][0] == "HARDWARE_PRICE_MODE"
    assert costs["Citadel Transport Unit"] == K.PLANET_TRANSPORTER_COST_FIRST == 50_000
    assert costs["Citadel Transport Upgrade"] == K.PLANET_TRANSPORTER_COST_EXTRA == 25_000


def test_live_card_quotes_the_capture_and_keeps_the_stored_samples(monkeypatch) -> None:
    costs = _costs(_capture())
    type1 = costs["Type I TWarp"]
    type2 = costs["Type II TWarp"]
    upgrade = costs["TWarp Upgrade"]
    universe, player = _world(credits=12_499)
    short = _quote(universe)
    assert short["unit_price_by"]["transwarp_drive"] == 12_500
    assert "transwarp_drive" not in short["choices"]
    assert "The Type 1 drive costs 12,500 credits" in render("Galaxy War Command")
    assert "A Type 2 drive costs 20,000 credits" in render("Galaxy War Command")
    assert "The upgrade from Type 1 costs 9,000 credits" in render("Galaxy War Command")
    prompt = get_system_prompt()
    assert "transwarp_drive at StarDock (12,500)" in prompt
    assert "transwarp_type2 20,000 or transwarp_upgrade 9,000" in prompt
    bare = player.net_worth
    player.ship.transwarp_drive = "type1"
    assert player.net_worth == bare
    player.ship.transwarp_drive = "type2"
    assert player.net_worth == bare
    player.ship.transwarp_drive = None
    assert K.ship_tw_drive_value(None) == 0
    assert K.ship_tw_drive_value("type1") == 12_500
    assert K.ship_tw_drive_value("type2") == 20_000

    monkeypatch.setattr(K, "HARDWARE_PRICE_MODE", "live")
    assert K.HARDWARE_PRICE_MODE == "live"
    assert K.SHIP_TW_MODE == "tw2002"
    assert K.ship_tw_type1_cost() == type1
    assert K.ship_tw_type2_cost() == type2
    assert K.ship_tw_upgrade_cost() == upgrade
    assert K.SHIP_TW_TYPE1_COST == 12_500
    assert K.SHIP_TW_TYPE2_COST == 20_000
    assert K.SHIP_TW_UPGRADE_COST == 9_000
    assert K.PLANET_TRANSPORTER_COST_FIRST == 50_000
    assert K.PLANET_TRANSPORTER_COST_EXTRA == 25_000
    broke = _quote(universe)
    assert broke["unit_price_by"]["transwarp_drive"] == type1
    assert "transwarp_drive" not in broke["choices"]
    player.credits = 200_000
    offered = _quote(universe)
    assert offered["unit_price_by"]["transwarp_drive"] == type1
    assert offered["unit_price_by"]["transwarp_type2"] == type2
    assert "transwarp_upgrade" not in offered["unit_price_by"]
    assert offered["choices"].count("transwarp_drive") == 1
    assert "transwarp_drive" in offered["choices"]
    assert "transwarp_type2" in offered["choices"]
    sheet = {row["name"]: row["price"] for row in _prices("imperial_starship", 40, 1)}
    assert sheet["TransWarp type 1"] == type1
    assert sheet["TransWarp type 2"] == type2
    assert sheet["TransWarp upgrade"] == upgrade
    manual = render("Galaxy War Command")
    assert f"The Type 1 drive costs {type1:,} credits" in manual
    assert f"A Type 2 drive costs {type2:,} credits" in manual
    assert f"The upgrade from Type 1 costs {upgrade:,} credits" in manual
    live_prompt = get_system_prompt()
    assert f"transwarp_drive at StarDock ({type1:,})" in live_prompt
    assert f"transwarp_type2 {type2:,} or transwarp_upgrade {upgrade:,}" in live_prompt
    scored = player.net_worth
    player.ship.transwarp_drive = "type1"
    assert player.net_worth - scored == type1
    player.ship.transwarp_drive = "type2"
    assert player.net_worth - scored == type2
    player.ship.transwarp_drive = None
    assert K.ship_tw_drive_value("type1") == type1
    assert K.ship_tw_drive_value("type2") == type2

    before = player.credits
    worth = player.net_worth
    bought = apply_action(
        universe, "P1", Action(kind=ActionKind.BUY_EQUIP, args={"item": "transwarp_drive", "qty": 1})
    )
    assert bought.ok, bought.error
    assert before - player.credits == type1
    assert player.ship.transwarp_drive == "type1"
    assert player.net_worth == worth

    player.ship.transwarp_drive = None
    player.credits = before
    bought_type2 = apply_action(
        universe, "P1", Action(kind=ActionKind.BUY_EQUIP, args={"item": "transwarp_type2", "qty": 1})
    )
    assert bought_type2.ok, bought_type2.error
    assert before - player.credits == type2
    assert player.ship.transwarp_drive == "type2"

    player.ship.transwarp_drive = "type1"
    player.credits = upgrade - 1
    refused = apply_action(
        universe, "P1", Action(kind=ActionKind.BUY_EQUIP, args={"item": "transwarp_upgrade", "qty": 1})
    )
    assert not refused.ok
    assert player.credits == upgrade - 1
    assert player.ship.transwarp_drive == "type1"
    player.credits = upgrade
    upgraded = apply_action(
        universe, "P1", Action(kind=ActionKind.BUY_EQUIP, args={"item": "transwarp_upgrade", "qty": 1})
    )
    assert upgraded.ok, upgraded.error
    assert player.credits == 0
    assert player.ship.transwarp_drive == "type2"


def test_v311_and_live_profile_use_the_card_and_detect_gear_does_not(monkeypatch) -> None:
    costs = _costs(_capture())
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.HARDWARE_PRICE_MODE == "legacy"
    assert K.SHIP_TW_MODE == "tw2002"
    assert K.ship_tw_type1_cost() == costs["Type I TWarp"]
    assert K.ship_tw_type2_cost() == costs["Type II TWarp"]
    assert K.ship_tw_upgrade_cost() == costs["TWarp Upgrade"]

    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    assert K.ship_tw_type1_cost() == costs["Type I TWarp"]
    assert K.ship_tw_type2_cost() == costs["Type II TWarp"]
    assert K.ship_tw_upgrade_cost() == costs["TWarp Upgrade"]
    assert K.SHIP_TW_MODE == "tw2002"

    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    monkeypatch.setattr(K, "DETECT_GEAR_MODE", "live")
    assert K.ship_tw_type1_cost() == 12_500
    assert K.ship_tw_type2_cost() == 20_000
    assert K.ship_tw_upgrade_cost() == 9_000


def test_notes_record_the_source_conflict() -> None:
    text = _capture()
    assert "Type I TWarp=50,000 cr" in text
    assert "Type II TWarp=80,000 cr" in text
    assert "TWarp Upgrade=10,000 cr" in text
    both = [
        ROOT / "docs/plans/GAP_MAP.md",
        ROOT / "docs/reference/tw2002/GAP_MAP.md",
        ROOT / "docs/plans/gap-map-refresh-v6.md",
        ROOT / "docs/plans/V311_SOURCE_CONFLICTS.md",
        ROOT / "docs/plans/v311-profile-v1.md",
        ROOT / "docs/plans/live-twgs-test-queue-v1.md",
        ROOT / "docs/plans/hardware-price-v1.md",
    ]
    for path in both:
        body = path.read_text(encoding="utf-8")
        assert "SOURCE-CONFLICT" in body
        assert "50,000" in body
        assert "80,000" in body
        assert "10,000" in body
        assert "hardware_price_live" in body
    conflicts = (ROOT / "docs/plans/V311_SOURCE_CONFLICTS.md").read_text(encoding="utf-8")
    assert "Type I TWarp=50,000 cr" in conflicts
    assert "Type II TWarp=80,000 cr" in conflicts
    assert "TWarp Upgrade=10,000 cr" in conflicts
    assert "Citadel Transport Unit=50,000 cr" in conflicts
    assert "No new shop switch" in conflicts
    assert "PLANET_TRANSPORTER_COST_FIRST" in conflicts
    tow = (ROOT / "docs/playtests/ships/SHIP_TOW.md").read_text(encoding="utf-8")
    assert "ship_tw_type2_cost" in tow
    assert "ship_tw_upgrade_cost" in tow
    drive = (ROOT / "docs/playtests/ships/SHIP_TRANSWARP.md").read_text(encoding="utf-8")
    assert "ship_tw_type1_cost" in drive
    assert "12,500" in drive or "12_500" in drive
