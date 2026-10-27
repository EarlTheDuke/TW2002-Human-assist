"""NOTE 129 gap 1.8. Libram Universitatus and the singles-bar door.

The menu lines are read from the live captures. The unnamed balance drop
is not a product and is not charged.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import EventKind, FerrengiShip, Player, Ship
from tw2k.engine.stardock_doors import (
    FERRSPEC_KEY,
    HIDDEN_KEYS,
    SINGLES_ENTERED,
    SINGLES_PROMPT,
    WHERE_TO_PROMPT,
    archive_document_lines,
    archive_lines,
    ferrengi_hull_lines,
    where_to_lines,
)

pytestmark = pytest.mark.legacy_profile

ROOT = Path(__file__).resolve().parents[1]
MENUS = (ROOT / "docs/playtests/twgs-live/stardock-menus.txt").read_text(encoding="utf-8")
ILLEGAL = (ROOT / "docs/playtests/twgs-live/illegal-goods.txt").read_text(encoding="utf-8")


def _quoted(text: str, start: str, end: str) -> list[str]:
    block = text.split(start, 1)[1].split(end, 1)[0]
    return [line for line in block.splitlines() if line.startswith("<")]


def _world():
    return generate_universe(GameConfig(
        seed=129, universe_size=20, max_days=6, enable_planets=False, enable_ferrengi=False,
    ))


def _seat(universe, *, sector, credits=140):
    player = Player(id="P1", name="P1", ship=Ship(), credits=credits, sector_id=sector)
    universe.players["P1"] = player
    universe.sectors[sector].occupant_ids.append("P1")
    return player


def _kinds(universe):
    return {row.kind: row for row in legal_actions(universe, "P1")}


def test_capture_where_to_and_library_lines() -> None:
    assert "<StarDock> Where to?" in MENUS
    assert WHERE_TO_PROMPT in MENUS
    listed = _quoted(MENUS, "Obvious places:\n", "\nNot on that list:")
    assert where_to_lines() == listed
    assert "<L> The Libram Universitatus" in listed
    assert all(not line.startswith("<B>") and not line.startswith("<U>") for line in listed)
    assert HIDDEN_KEYS == ("B", "U")
    archives = _quoted(MENUS, "Library, no charge:\n", "\n\nPolice:")
    assert archive_lines() == archives
    prompt = next(line for line in MENUS.splitlines() if line.startswith("B opens:"))
    assert prompt.split("B opens:", 1)[1].strip() == SINGLES_PROMPT


def test_capture_singles_exit_names_no_item_and_no_price() -> None:
    entered = ILLEGAL.split("Singles bar, StarDock B, answered Yes:\n", 1)[1]
    entered = entered.split("\nCredits on the previous", 1)[0]
    assert entered == SINGLES_ENTERED
    assert "140" in ILLEGAL and "93" in ILLEGAL
    assert "No item name" in ILLEGAL
    assert "47" not in SINGLES_ENTERED
    assert "47" not in SINGLES_PROMPT


def test_legacy_hides_both_doors(monkeypatch) -> None:
    monkeypatch.setattr(K, "STARDOCK_DOORS_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    universe = _world()
    player = _seat(universe, sector=int(K.STARDOCK_SECTOR))
    kinds = _kinds(universe)
    assert "library" not in kinds
    assert "singles_bar" not in kinds
    library = apply_action(universe, "P1", Action(kind=ActionKind.LIBRARY, args={"archive": "A"}))
    bar = apply_action(universe, "P1", Action(kind=ActionKind.SINGLES_BAR, args={"confirm": True}))
    assert library.ok is False and bar.ok is False
    assert player.credits == 140
    assert not any(event.kind in (EventKind.LIBRARY, EventKind.SINGLES_BAR) for event in universe.events)


def test_the_string_one_does_not_open_the_doors(monkeypatch) -> None:
    monkeypatch.setattr(K, "STARDOCK_DOORS_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.stardock_doors_live() is False
    universe = _world()
    _seat(universe, sector=int(K.STARDOCK_SECTOR))
    assert "library" not in _kinds(universe)


def test_v311_lists_the_library_and_the_hidden_bar(monkeypatch) -> None:
    monkeypatch.setattr(K, "STARDOCK_DOORS_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.stardock_doors_live() is True
    universe = _world()
    _seat(universe, sector=int(K.stardock_sector_of(universe)))
    kinds = _kinds(universe)
    library = kinds["library"]
    bar = kinds["singles_bar"]
    assert library.legal is True and library.turn_cost == 0
    assert [row["line"] for row in library.params["where_to"]] == where_to_lines()
    assert [row["line"] for row in library.params["archives"]] == archive_lines()
    assert library.params["charge"] == 0
    assert bar.legal is True
    assert bar.params["listed"] is False
    assert bar.params["prompt"] == SINGLES_PROMPT
    assert bar.params["charge"] == 0
    assert "B" not in {row["key"] for row in library.params["where_to"]}
    assert "U" not in {row["key"] for row in library.params["where_to"]}


def _library(universe, key: str):
    result = apply_action(universe, "P1", Action(kind=ActionKind.LIBRARY, args={"archive": key}))
    event = next(row for row in reversed(universe.events) if row.kind == EventKind.LIBRARY)
    return result, event


def _put_ferr(universe, *, fid: str, hull: str, alive: bool = True, name: str = "Ship") -> None:
    universe.ferrengi[fid] = FerrengiShip(
        id=fid,
        name=name,
        sector_id=int(K.STARDOCK_SECTOR),
        aggression=3,
        fighters=10,
        shields=10,
        hull=hull,
        alive=alive,
    )


def test_archives_are_empty_and_free(monkeypatch) -> None:
    monkeypatch.setattr(K, "STARDOCK_DOORS_MODE", "v311")
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    universe = _world()
    player = _seat(universe, sector=int(K.STARDOCK_SECTOR), credits=140)
    assert universe.ferrengi == {}
    for key, label in (
        ("A", "Archive of Alien Races"),
        ("B", "Archive of Galactic Organizations"),
        ("C", "Miscellaneous Documents"),
    ):
        result, event = _library(universe, key)
        assert result.ok is True and result.turns_spent == 0
        assert event.payload["lines"] == [f"<{key}> {label}", ""]
        assert event.summary == "\n".join(event.payload["lines"])
        assert event.payload["charge"] == 0
        assert event.payload["label"] == label
        assert "Ferrengi" not in event.summary
        assert "Derelict" not in event.summary
    assert next(row for row in reversed(universe.events) if row.payload["archive"] == "C").payload["hulls"] == []
    leave = apply_action(universe, "P1", Action(kind=ActionKind.LIBRARY, args={"archive": "Q"}))
    assert leave.ok is True
    left = next(row for row in reversed(universe.events) if row.kind == EventKind.LIBRARY)
    assert left.summary == "To Leave"
    assert left.payload["lines"] == []
    assert player.credits == 140
    refused = apply_action(universe, "P1", Action(kind=ActionKind.LIBRARY, args={"archive": "Z"}))
    assert refused.ok is False


def test_legacy_door_does_not_list_ferrengi_in_use(monkeypatch) -> None:
    monkeypatch.setattr(K, "STARDOCK_DOORS_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    universe = _world()
    player = _seat(universe, sector=int(K.STARDOCK_SECTOR), credits=140)
    _put_ferr(universe, fid="F1", hull=K.FERRENGI_HULL_ASSAULT, name="Grabby")
    _put_ferr(universe, fid="F2", hull=K.FERRENGI_HULL_DREAD, name="Big")
    result = apply_action(universe, "P1", Action(kind=ActionKind.LIBRARY, args={"archive": "C"}))
    assert result.ok is False
    assert player.credits == 140
    assert not any(event.kind == EventKind.LIBRARY for event in universe.events)
    assert "library" not in _kinds(universe)


def test_doors_on_lists_only_living_ferrengi_hulls(monkeypatch) -> None:
    monkeypatch.setattr(K, "STARDOCK_DOORS_MODE", "v311")
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "FERRENGI_ODDS_MODE", "legacy")
    universe = _world()
    player = _seat(universe, sector=int(K.STARDOCK_SECTOR), credits=140)
    _put_ferr(universe, fid="F1", hull=K.FERRENGI_HULL_ASSAULT, name="Grabby")
    _put_ferr(universe, fid="F1b", hull=K.FERRENGI_HULL_ASSAULT, name="Second")
    _put_ferr(universe, fid="F2", hull=K.FERRENGI_HULL_CRUISER, name="Cruiser Name")
    _put_ferr(universe, fid="F3", hull=K.FERRENGI_HULL_DREAD, alive=False, name="Dead Dread")
    _put_ferr(universe, fid="F4", hull="", name="Legacy Raider")
    _put_ferr(universe, fid="F5", hull="derelict", name="Alien Derelict")
    result, event = _library(universe, FERRSPEC_KEY)
    assert result.ok is True and result.turns_spent == 0
    lines = event.payload["lines"]
    assert lines == archive_document_lines(universe, "C")
    assert event.summary == "\n".join(lines)
    assert event.payload["hulls"] == [K.FERRENGI_HULL_ASSAULT, K.FERRENGI_HULL_CRUISER]
    assert event.payload["charge"] == 0
    assault = K.FERRENGI_HULL_SPECS[K.FERRENGI_HULL_ASSAULT]
    cruiser = K.FERRENGI_HULL_SPECS[K.FERRENGI_HULL_CRUISER]
    assert lines == [
        "<C> Miscellaneous Documents",
        "",
        *ferrengi_hull_lines(K.FERRENGI_HULL_ASSAULT),
        "",
        *ferrengi_hull_lines(K.FERRENGI_HULL_CRUISER),
    ]
    assert assault["max_fighters"] == 3000
    assert assault["odds"] == 1.0
    assert K.ferrengi_fighters_per_attack(K.FERRENGI_HULL_ASSAULT) == 1000
    assert cruiser["max_fighters"] == 8000
    assert "Odds 1.0" in lines
    assert "Fighters 3000" in lines
    assert "Fighters per attack 1000" in lines
    assert "Odds 1.2" in lines
    assert "Fighters 8000" in lines
    assert "Fighters per attack 2000" in lines
    assert lines.count("Ferrengi Assault Trader") == 1
    assert "Ferrengi Dreadnought" not in lines
    assert "Grabby" not in event.summary
    assert "Dead Dread" not in event.summary
    assert "Legacy Raider" not in event.summary
    assert "Derelict" not in event.summary
    assert "\x1b" not in event.summary
    for key, label in (("A", "Archive of Alien Races"), ("B", "Archive of Galactic Organizations")):
        _result, stub = _library(universe, key)
        assert stub.payload["lines"] == [f"<{key}> {label}", ""]
        assert "Ferrengi" not in stub.summary
        assert "hulls" not in stub.payload
    assert player.credits == 140


def test_doors_on_bible_chart_when_the_odds_switch_is_on(monkeypatch) -> None:
    monkeypatch.setattr(K, "STARDOCK_DOORS_MODE", "v311")
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "FERRENGI_ODDS_MODE", "v311")
    universe = _world()
    _seat(universe, sector=int(K.STARDOCK_SECTOR))
    _put_ferr(universe, fid="F1", hull=K.FERRENGI_HULL_ASSAULT)
    _result, event = _library(universe, "C")
    lines = event.payload["lines"]
    assert "Odds 1.2" in lines
    assert "Fighters per attack 2000" in lines
    assert "Fighters 3000" in lines
    assert "Odds 1.0" not in lines
    assert "Ferrengi Battle Cruiser" not in lines
    assert "Ferrengi Dreadnought" not in lines


def test_singles_door_confirms_without_a_charge(monkeypatch) -> None:
    monkeypatch.setattr(K, "STARDOCK_DOORS_MODE", "v311")
    universe = _world()
    player = _seat(universe, sector=int(K.STARDOCK_SECTOR), credits=140)
    declined = apply_action(universe, "P1", Action(kind=ActionKind.SINGLES_BAR, args={"confirm": False}))
    assert declined.ok is True
    assert player.credits == 140
    assert not any(event.kind == EventKind.SINGLES_BAR for event in universe.events)
    entered = apply_action(universe, "P1", Action(kind=ActionKind.SINGLES_BAR, args={"confirm": True}))
    assert entered.ok is True and entered.turns_spent == 0
    assert player.credits == 140
    event = next(row for row in universe.events if row.kind == EventKind.SINGLES_BAR)
    assert event.summary == SINGLES_ENTERED
    assert event.payload["charged"] is False
    assert event.payload["entered"] is True
    assert "item" not in event.payload
    assert "47" not in str(event.payload)


def test_doors_are_only_at_stardock(monkeypatch) -> None:
    monkeypatch.setattr(K, "STARDOCK_DOORS_MODE", "v311")
    universe = _world()
    away = next(sid for sid in universe.sectors if int(sid) != int(K.STARDOCK_SECTOR))
    player = _seat(universe, sector=away, credits=140)
    kinds = _kinds(universe)
    assert kinds["library"].legal is False
    assert kinds["singles_bar"].legal is False
    result = apply_action(universe, "P1", Action(kind=ActionKind.SINGLES_BAR, args={"confirm": True}))
    assert result.ok is False
    assert player.credits == 140
