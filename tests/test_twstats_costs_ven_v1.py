"""Ven 2026-10-24 GameA TWSTATS capture.

docs/playtests/twgs-live/twstats-costs-ven.txt
Photon Missile and Atomic Detonator lines are pinned. Every other label in
[Version], [Settings], and [Costs] must be present. No new price switch.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.agents.prompts import get_system_prompt
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, Ship, ShipClass
from tw2k.server.reference import _prices

pytestmark = pytest.mark.legacy_profile

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "docs" / "playtests" / "twgs-live" / "twstats-costs-ven.txt"

VERBATIM = """\
# GameA TWSTATS.TXT — Costs / BigBang card (read-only Ven probe)
# Source: C:\\Games\\TWGS\\program files\\EIS\\TWGS\\Game\\GameA\\OUTPUT\\TWSTATS.TXT
# Machine: VENGEANCE (89b0d9d2-d2d4-4d5b-8b34-9abf7cd9f545)
# File mtime (Ven local): 2026-10-24 06:27:19 AM
# Captured: 2026-10-24 ~10:48 AM America/Los_Angeles
# Version header: Major=3 Minor=34 Revision=b
# Touched nothing: AFK Slot A / GrokAFK24 / ports 8031-8037/8041 / twgs.exe
#
# Full [Costs] section + nearby Settings lines that touch hardware prices/timing.

[Version]
Major Version=3
Minor Version=34
Revision=b

[Settings]  # hardware-adjacent only
Photon Missile Duration=20 Sec
FedSpace Photons=False
Photons Disable Players=True
Cloak Fail Percent=3%
Multiple Photons=False

[Costs]
Tavern Announcement=100 cr
Limpet Removal=5,000 cr
Reregister Ship=5,000 cr
Citadel Transport Unit=50,000 cr
Citadel Transport Upgrade=25,000 cr
Genesis Torpedo=20,000 cr
Armid Mine=1,000 cr
Limpet Mine=10,000 cr
Beacon=100 cr
Type I TWarp=50,000 cr
Type II TWarp=80,000 cr
TWarp Upgrade=10,000 cr
Psychic Probe=10,000 cr
Planet Scanner=30,000 cr
Atomic Detonator=15,000 cr
Corbomite=1,000 cr
Ether Probe=3,000 cr
Photon Missile=40,000 cr
Cloaking Device=25,000 cr
Mine Disruptor=6,000 cr
Holographic Scanner=25,000 cr
Density Scanner=2,000 cr
"""

COSTS = {
    "Tavern Announcement": 100,
    "Limpet Removal": 5_000,
    "Reregister Ship": 5_000,
    "Citadel Transport Unit": 50_000,
    "Citadel Transport Upgrade": 25_000,
    "Genesis Torpedo": 20_000,
    "Armid Mine": 1_000,
    "Limpet Mine": 10_000,
    "Beacon": 100,
    "Type I TWarp": 50_000,
    "Type II TWarp": 80_000,
    "TWarp Upgrade": 10_000,
    "Psychic Probe": 10_000,
    "Planet Scanner": 30_000,
    "Atomic Detonator": 15_000,
    "Corbomite": 1_000,
    "Ether Probe": 3_000,
    "Photon Missile": 40_000,
    "Cloaking Device": 25_000,
    "Mine Disruptor": 6_000,
    "Holographic Scanner": 25_000,
    "Density Scanner": 2_000,
}

SETTINGS = {
    "Photon Missile Duration": "20 Sec",
    "FedSpace Photons": "False",
    "Photons Disable Players": "True",
    "Cloak Fail Percent": "3%",
    "Multiple Photons": "False",
}

VERSION = {
    "Major Version": "3",
    "Minor Version": "34",
    "Revision": "b",
}

QUEUED = (
    "Type I TWarp=50,000 cr",
    "Type II TWarp=80,000 cr",
    "TWarp Upgrade=10,000 cr",
    "Citadel Transport Unit=50,000 cr",
    "Citadel Transport Upgrade=25,000 cr",
)

NOTE_PATHS = (
    ROOT / "docs/plans/GAP_MAP.md",
    ROOT / "docs/reference/tw2002/GAP_MAP.md",
    ROOT / "docs/plans/gap-map-refresh-v6.md",
    ROOT / "docs/plans/live-twgs-test-queue-v1.md",
    ROOT / "docs/plans/V311_SOURCE_CONFLICTS.md",
    ROOT / "docs/plans/hardware-price-v1.md",
    ROOT / "docs/plans/v311-profile-v1.md",
)

COST_LINE = re.compile(r"^([^=]+)=([0-9,]+) cr$")
PAIR_LINE = re.compile(r"^([^=]+)=(.+)$")


def _sections(text: str) -> dict[str, dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    section: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and "]" in line:
            section = line[1:line.index("]")].strip()
            found.setdefault(section, {})
            continue
        if section is None:
            continue
        match = PAIR_LINE.match(line)
        assert match, line
        found[section][match.group(1)] = match.group(2)
    return found


def test_capture_body_is_the_ven_file() -> None:
    text = CAPTURE.read_text(encoding="utf-8")
    assert text.startswith(VERBATIM)
    for line in text[len(VERBATIM):].splitlines():
        assert line == "" or line.startswith("#"), line
    assert "Photon Missile=40,000 cr" in text
    assert "Atomic Detonator=15,000 cr" in text


def test_photon_and_atomic_lines_and_every_other_label() -> None:
    sections = _sections(CAPTURE.read_text(encoding="utf-8"))
    assert set(sections) == {"Version", "Settings", "Costs"}
    assert sections["Version"] == VERSION
    assert sections["Settings"] == SETTINGS
    costs = {
        label: int(raw.replace(",", "").removesuffix(" cr"))
        for label, raw in sections["Costs"].items()
    }
    assert costs == COSTS
    assert costs["Photon Missile"] == 40_000
    assert costs["Atomic Detonator"] == 15_000
    for label, raw in sections["Costs"].items():
        assert COST_LINE.match(f"{label}={raw}")


def test_stored_prices_stay_and_no_new_switch() -> None:
    assert K.PHOTON_MISSILE_COST == 12_000
    assert K.ATOMIC_DETONATOR_COST == 60_000
    assert K.SHIP_TW_TYPE1_COST == 12_500
    assert K.SHIP_TW_TYPE2_COST == 20_000
    assert K.SHIP_TW_UPGRADE_COST == 9_000
    assert K.PLANET_TRANSPORTER_COST_FIRST == 50_000
    assert K.PLANET_TRANSPORTER_COST_EXTRA == 25_000
    assert K.HARDWARE_PRICE_MODE == "legacy"
    photon = getattr(K, "photon_missile_cost", None)
    detonator = getattr(K, "atomic_detonator_cost", None)
    if photon is not None:
        assert photon() == K.PHOTON_MISSILE_COST
    if detonator is not None:
        assert detonator() == K.ATOMIC_DETONATOR_COST
    assert not hasattr(K, "TWARP_PRICE_MODE")
    assert not hasattr(K, "CITADEL_TRANSPORT_PRICE_MODE")


def test_unbuilt_rows_are_queued_notes() -> None:
    for path in NOTE_PATHS:
        body = path.read_text(encoding="utf-8")
        assert "DIFFERENT" in body
        assert "queued" in body.lower()
        for label in QUEUED:
            assert label in body, (path.name, label)
    hardware = (ROOT / "docs/playtests/ships/SHIP_TRANSWARP.md").read_text(encoding="utf-8")
    assert "Type I TWarp=50,000 cr" in hardware
    assert "DIFFERENT" in hardware
    tow = (ROOT / "docs/playtests/ships/SHIP_TOW.md").read_text(encoding="utf-8")
    assert "Type II TWarp=80,000 cr" in tow
    assert "TWarp Upgrade=10,000 cr" in tow
    assert "queued" in tow.lower()

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


def test_capture_line_is_the_live_photon() -> None:
    text = _capture()
    assert "[Costs]" in text
    assert "Photon Missile=40,000 cr" in text
    costs = _costs(text)
    assert costs["Photon Missile"] == 40_000
    assert K.HARDWARE_PRICE_MODE == "legacy"
    assert K.PHOTON_MISSILE_COST == 12_000
    assert costs["Photon Missile"] == K.PHOTON_MISSILE_COST_LIVE
    assert K.photon_missile_cost() == K.PHOTON_MISSILE_COST
    assert "photon_missile_live" not in K.V311_PROFILE_HELPERS
    assert K.V311_PROFILE_HELPERS["hardware_price_live"][0] == "HARDWARE_PRICE_MODE"


def test_live_card_quotes_the_capture_and_keeps_the_other_pins(monkeypatch) -> None:
    photon = _costs(_capture())["Photon Missile"]
    universe, player = _world()
    prices = next(row for row in legal_actions(universe, "P1") if row.kind == "buy_equip")
    quoted = prices.params["item"]["unit_price_by"]
    assert quoted["photon_missiles"] == 12_000
    assert quoted["armid_mines"] == 100
    assert quoted["limpet_mines"] == 250
    assert quoted["genesis"] == 25_000
    bare = player.net_worth
    player.ship.photon_missiles = 1
    assert player.net_worth - bare == 12_000
    assert "photon_missiles 12,000 cr each" in get_system_prompt()

    monkeypatch.setattr(K, "HARDWARE_PRICE_MODE", "live")
    assert K.HARDWARE_PRICE_MODE == "live"
    assert K.photon_missile_cost() == photon
    assert K.PHOTON_MISSILE_COST == 12_000
    assert K.armid_mine_cost() == 1_000
    assert K.limpet_mine_cost() == 10_000
    assert K.genesis_torpedo_cost() == 20_000
    assert K.ether_probe_cost() == 3_000
    assert K.armid_hit_damage() == 30
    live_quote = next(row for row in legal_actions(universe, "P1") if row.kind == "buy_equip")
    live_prices = live_quote.params["item"]["unit_price_by"]
    assert live_prices["photon_missiles"] == photon
    assert live_prices["armid_mines"] == 1_000
    sheet = {row["name"]: row["price"] for row in _prices("missile_frigate", 20, 1)}
    assert sheet["Photon missile"] == photon
    assert player.net_worth - bare == photon
    assert f"photon_missiles {photon:,} cr each" in get_system_prompt()

    before = player.credits
    bought_photon = apply_action(
        universe, "P1", Action(kind=ActionKind.BUY_EQUIP, args={"item": "photon_missiles", "qty": 1})
    )
    assert bought_photon.ok, bought_photon.error
    assert before - player.credits == photon
    assert player.ship.photon_missiles == 2


def test_v311_and_live_profile_use_the_card_and_detect_gear_does_not(monkeypatch) -> None:
    photon = _costs(_capture())["Photon Missile"]
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.HARDWARE_PRICE_MODE == "legacy"
    assert K.photon_missile_cost() == photon

    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    assert K.photon_missile_cost() == photon

    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    monkeypatch.setattr(K, "DETECT_GEAR_MODE", "live")
    assert K.photon_missile_cost() == 12_000
    assert K.disruptor_cost() == 6_000
    assert K.psychic_probe_cost() == 10_000


def test_notes_record_the_source_conflict() -> None:
    text = _capture()
    assert "Photon Missile=40,000 cr" in text
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
        assert "hardware_price_live" in body
    conflicts = (ROOT / "docs/plans/V311_SOURCE_CONFLICTS.md").read_text(encoding="utf-8")
    assert "Photon Missile=40,000 cr" in conflicts
    assert "DIFFERENT" in conflicts
    hardware = (ROOT / "docs/playtests/ships/SHIP_HARDWARE.md").read_text(encoding="utf-8")
    assert "photon_missile_cost" in hardware
