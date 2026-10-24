"""Ven 2026-10-24 read-only capture: ship rename and limpet removal.

docs/playtests/twgs-live/ship-rename-limpet-ven.txt
Fee 5,000 and a 30-character name are CONFIRMED. Turns were not measured.
Stored limpet removal stays 1,250. The live card's 5,000 sits on hardware_price_live.
"""

from __future__ import annotations

from pathlib import Path

import tw2k.engine.constants as K
from tw2k.agents.prompts import get_system_prompt
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import LimpetTrack, Player, Ship, ShipClass

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "docs" / "playtests" / "twgs-live" / "ship-rename-limpet-ven.txt"


def _capture() -> str:
    return CAPTURE.read_text(encoding="utf-8")


def _row(text: str, item: str) -> str:
    for line in text.splitlines():
        if line.startswith(f"| {item} |"):
            return line
    raise AssertionError(item)


def _world():
    universe = generate_universe(
        GameConfig(seed=5101, universe_size=80, enable_ferrengi=False, enable_planets=True)
    )
    universe.players["A"] = Player(
        id="A",
        name="Alpha",
        ship=Ship(name="Unnamed", holds=20, ship_class=ShipClass.MERCHANT_CRUISER),
        sector_id=K.STARDOCK_SECTOR,
        credits=50_000,
        turns_today=0,
    )
    universe.sectors[K.STARDOCK_SECTOR].occupant_ids.append("A")
    return universe


def _move(universe, sector: int) -> None:
    player = universe.players["A"]
    occupants = universe.sectors[player.sector_id].occupant_ids
    if "A" in occupants:
        occupants.remove("A")
    player.sector_id = sector
    universe.sectors[sector].occupant_ids.append("A")


def _stick(universe, sector: int) -> None:
    universe.limpets["B:A"] = LimpetTrack(
        owner_id="B", target_id="A", placed_sector=sector, placed_day=universe.day,
    )


def test_capture_confirms_the_rename_fee_and_the_name_length() -> None:
    text = _capture()
    assert "Reregister Ship=5,000 cr" in text
    assert "SHIP_RENAME_COST = 5000" in text
    assert "(30 chars)" in text
    assert "(30 letters)" in text
    assert "What do you want to name this ship? (30 chars)" in text
    assert "TURNS spent: NOT measured" in text
    assert K.SHIP_RENAME_MODE == "legacy"
    assert K.SHIP_RENAME_COST == 5_000
    assert K.SHIP_RENAME_NAME_MAX == 30
    assert not hasattr(K, "SHIP_RENAME_TURNS")
    for line in K.SHIP_RENAME_FEE_PROMPT:
        assert line in text
    for line in K.SHIP_RENAME_BROKE_PROMPT:
        assert line in text
    for line in K.SHIP_RENAME_NAME_PROMPTS:
        assert K.fill_measured_prompt(line, K.SHIP_RENAME_NAME_MAX) in text
    spoken = K.ship_rename_office_prompt()
    assert "That'll be 5000 creds to process a different ship name." in spoken
    assert "What do you want to name your ship? (30 chars)" in spoken
    assert "{N}" not in spoken


def test_rename_stays_behind_the_switch_and_charges_no_invented_turn(monkeypatch) -> None:
    universe = _world()
    kinds = {row.kind for row in legal_actions(universe, "A")}
    assert "ship_rename" not in kinds
    monkeypatch.setattr(K, "SHIP_RENAME_MODE", "live")
    row = next(item for item in legal_actions(universe, "A") if item.kind == "ship_rename")
    assert row.legal is True
    assert row.params["cost"] == 5_000
    assert row.params["name"]["max_length"] == 30
    assert "That'll be 5000 creds" in row.params["prompt"]
    assert row.params["broke"] == K.ship_rename_broke_text()
    short = apply_action(universe, "A", Action(kind=ActionKind.SHIP_RENAME, args={"name": "A" * 31}))
    assert short.ok is False
    assert universe.players["A"].credits == 50_000
    done = apply_action(universe, "A", Action(kind=ActionKind.SHIP_RENAME, args={"name": "A" * 30}))
    assert done.ok, done.error
    assert done.turns_spent == 0
    assert universe.players["A"].ship.name == "A" * 30
    assert universe.players["A"].credits == 45_000
    assert universe.players["A"].turns_today == 0


def test_capture_records_the_limpet_source_conflict() -> None:
    text = _capture()
    assert "Limpet Removal=5,000 cr" in text
    assert "LIMPET_REMOVAL_COST = 5000" in text
    assert "<D> Limpet Removal : $1,250" in text
    assert "CostLimpetRemoval" in text
    assert "same fee for StarDock and Class 0" in text
    assert "TURNS: NOT measured" in text
    for line in K.LIMPET_REMOVAL_OFFER:
        assert line in text
    for line in K.LIMPET_REMOVAL_DONE:
        assert line in text
    for line in K.LIMPET_REMOVAL_BROKE:
        assert line in text
    assert K.LIMPET_REMOVAL_COST == 1_250
    assert K.LIMPET_REMOVAL_COST_LIVE == 5_000
    assert K.limpet_removal_cost() == 1_250
    assert K.HARDWARE_PRICE_MODE == "legacy"
    assert "limpet_removal_live" not in K.V311_PROFILE_HELPERS
    assert K.V311_PROFILE_HELPERS["hardware_price_live"][0] == "HARDWARE_PRICE_MODE"
    offer = K.limpet_removal_offer()
    assert "pay the 1250 credit fee for search" in offer
    assert "{N}" not in offer
    assert "(1,250 cr)" in get_system_prompt()


def test_live_card_uses_5000_and_both_docks_share_it(monkeypatch) -> None:
    universe = _world()
    rylos = universe.class0_sectors["rylos"]

    def charge(sector: int) -> int:
        _move(universe, sector)
        universe.players["A"].credits = 50_000
        universe.players["A"].turns_today = 4
        _stick(universe, sector)
        row = next(item for item in legal_actions(universe, "A") if item.kind == "remove_limpet")
        assert row.legal is True
        assert row.params["fee"] == K.limpet_removal_cost()
        assert row.params["prompt"] == K.limpet_removal_offer(row.params["fee"])
        assert row.params["broke"] == K.limpet_removal_broke_text()
        assert "they can't tell who it belonged to." in row.params["done"]
        before = universe.players["A"].credits
        result = apply_action(universe, "A", Action(kind=ActionKind.REMOVE_LIMPET, args={}))
        assert result.ok, result.error
        assert result.turns_spent == 0
        assert universe.players["A"].turns_today == 4
        return before - universe.players["A"].credits

    assert charge(K.STARDOCK_SECTOR) == 1_250
    assert charge(rylos) == 1_250

    monkeypatch.setattr(K, "HARDWARE_PRICE_MODE", "live")
    assert K.limpet_removal_cost() == 5_000
    assert "(5,000 cr)" in get_system_prompt()
    assert K.LIMPET_REMOVAL_COST == 1_250
    assert "pay the 5000 credit fee" in K.limpet_removal_offer()
    assert charge(K.STARDOCK_SECTOR) == 5_000
    assert charge(rylos) == 5_000

    monkeypatch.setattr(K, "HARDWARE_PRICE_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.HARDWARE_PRICE_MODE == "legacy"
    assert K.limpet_removal_cost() == 5_000
    assert charge(K.STARDOCK_SECTOR) == charge(rylos) == 5_000

    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    assert K.limpet_removal_cost() == 5_000
    broke = _world()
    broke.players["A"].credits = 4_999
    _stick(broke, K.STARDOCK_SECTOR)
    row = next(item for item in legal_actions(broke, "A") if item.kind == "remove_limpet")
    assert row.legal is False
    assert "credits" in (row.reason or "")
    assert row.params["fee"] == 5_000
    assert "haven't the funds" in row.params["broke"]


def test_queue_and_gap_map_record_the_capture() -> None:
    queue = (ROOT / "docs/plans/live-twgs-test-queue-v1.md").read_text(encoding="utf-8")
    rename = _row(queue, "Ship rename")
    assert "CONFIRMED" in rename
    assert "not measured" in rename
    assert "0 turns" not in rename
    limpet = _row(queue, "Limpet removal fee")
    assert "SOURCE-CONFLICT" in limpet
    assert "1,250" in limpet
    assert "5,000" in limpet
    assert "CostLimpetRemoval" in limpet
    gap = (ROOT / "docs/plans/GAP_MAP.md").read_text(encoding="utf-8")
    assert "ship-rename-limpet-ven.txt" in gap
    assert "Fee 5,000 CONFIRMED" in gap
    assert "cabal TEDIT $1,250 vs live GameA TWSTATS Limpet Removal=5,000 cr" in gap
    conflicts = (ROOT / "docs/plans/V311_SOURCE_CONFLICTS.md").read_text(encoding="utf-8")
    assert "Ven 2026-10-24" in conflicts
    assert "1,250, or 5,000" in conflicts
    assert CAPTURE.is_file()
