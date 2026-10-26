"""Standing in the StarDock sector is the shipyard and bank gate.

There is no second entered or docked flag. Sector 1 is that sector until
STARDOCK_LOCATION_MODE (or the v311 profile) stores another. Buy gear can
still open at Sol after the dock moves. Shipyards and the bank name the
sector that actually holds the dock, and they open there.
"""
from __future__ import annotations

from pathlib import Path

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.bank import guard as bank_guard
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, Ship
from tw2k.engine.stardock_doors import library_spec
from tw2k.engine.v311_buildable import federation_hall_spec

ROOT = Path(__file__).resolve().parents[1]
REDESIGN = (ROOT / "web" / "redesign.js").read_text(encoding="utf-8")


def _legacy(monkeypatch) -> None:
    monkeypatch.setattr(K, "STARDOCK_LOCATION_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")


def _world(seed: int = 15):
    return generate_universe(GameConfig(
        seed=seed, universe_size=80, max_days=2, enable_ferrengi=False,
    ))


def _seat(universe, sector: int) -> Player:
    player = Player(
        id="A", name="A", sector_id=int(sector), credits=5_000_000,
        alignment=5000, ship=Ship(),
    )
    universe.players["A"] = player
    row = universe.sectors.get(int(sector))
    if row is not None and "A" not in row.occupant_ids:
        row.occupant_ids.append("A")
    return player


def _kind(universe, kind: str):
    return next(row for row in legal_actions(universe, "A") if row.kind == kind)


def _away(universe, dock: int) -> int:
    return next(sid for sid in range(11, 80) if int(sid) != int(dock))


def test_sector_1_opens_shipyards_and_the_bank_when_the_dock_is_there(monkeypatch) -> None:
    _legacy(monkeypatch)
    universe = _world()
    assert K.stardock_sector_of(universe) == 1
    player = _seat(universe, 1)
    ship = _kind(universe, "buy_ship")
    gear = _kind(universe, "buy_equip")
    assert ship.legal is True
    assert gear.legal is True
    assert bank_guard(universe, player) is None
    bought = apply_action(universe, "A", Action(
        kind=ActionKind.BUY_SHIP, args={"ship_class": ship.params["ship_class"]["choices"][0]},
    ))
    assert bought.ok is True
    deposited = apply_action(universe, "A", Action(kind=ActionKind.BANK_DEPOSIT, args={"amount": 1000}))
    assert deposited.ok is True
    player.sector_id = _away(universe, 1)
    refused = _kind(universe, "buy_ship")
    assert refused.legal is False
    assert refused.reason == "must be at StarDock (sector 1)"
    assert bank_guard(universe, player) == "the bank is at StarDock (sector 1)"
    assert apply_action(universe, "A", Action(kind=ActionKind.BANK_DEPOSIT, args={"amount": 10})).ok is False


def test_moved_dock_opens_at_the_stored_sector_and_not_at_sol(monkeypatch) -> None:
    _legacy(monkeypatch)
    monkeypatch.setattr(K, "STARDOCK_LOCATION_MODE", "v311")
    monkeypatch.setattr(K, "FEDERATION_HALL_MODE", "v311")
    monkeypatch.setattr(K, "STARDOCK_DOORS_MODE", "v311")
    universe = _world(42)
    dock = int(K.stardock_sector_of(universe))
    assert dock != 1
    player = _seat(universe, 1)
    # The soak: Sol still sells gear. The old shipyard line claimed sector 1.
    gear = _kind(universe, "buy_equip")
    ship = _kind(universe, "buy_ship")
    assert gear.legal is True
    assert ship.legal is False
    assert ship.reason == f"must be at StarDock (sector {dock})"
    assert ship.reason != "must be at StarDock (sector 1)"
    assert bank_guard(universe, player) == f"the bank is at StarDock (sector {dock})"
    hall_ok, hall_why, _hall = federation_hall_spec(universe, "A")
    door_ok, door_why, _door = library_spec(universe, "A")
    assert hall_ok is False and hall_why == f"must be at StarDock (sector {dock})"
    assert door_ok is False and door_why == f"that door is at StarDock (sector {dock})"

    player.sector_id = dock
    universe.sectors[dock].occupant_ids.append("A")
    ship = _kind(universe, "buy_ship")
    assert ship.legal is True
    assert bank_guard(universe, player) is None
    assert apply_action(universe, "A", Action(kind=ActionKind.BANK_DEPOSIT, args={"amount": 1000})).ok
    hall_ok, hall_why, _hall = federation_hall_spec(universe, "A")
    door_ok, door_why, _door = library_spec(universe, "A")
    assert hall_ok is True and hall_why is None
    assert door_ok is True and door_why is None

    player.sector_id = _away(universe, dock)
    ship = _kind(universe, "buy_ship")
    assert ship.legal is False
    assert ship.reason == f"must be at StarDock (sector {dock})"
    assert bank_guard(universe, player) == f"the bank is at StarDock (sector {dock})"


def test_cockpit_offers_shipyards_only_in_the_dock_sector() -> None:
    assert "function atStarDockSector" in REDESIGN
    assert "function stardockSectorId" in REDESIGN
    assert 'b.dataset.kind = "stardock_course"' in REDESIGN
    assert "Number(s.id) === 1 || (s.port && /stardock/i.test" not in REDESIGN
    gate = REDESIGN.split("const dockHere = atStarDockSector(s);", 1)[1].split("box.appendChild(spaceBox());", 1)[0]
    assert 'reasonButton("buy_ship", "Shipyards"' in gate
    assert "dataset.kind = \"bank\"" in gate
    assert gate.index("if (dockHere)") < gate.index('reasonButton("buy_ship", "Shipyards"')
    assert "starDockCourseButton()" in gate
