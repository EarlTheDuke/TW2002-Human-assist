"""GAP 1.5. StarDock placement stays behind STARDOCK_LOCATION_MODE.

Off, the dock stays in sector 1 and the stored field stays unset. On, a new
universe moves that port to a random ordinary sector. Terra stays sector 1.
FedSpace is sectors 1-10 plus the dock sector. V311_PROFILE "v311" turns the
helper on. The string "1" does not. TW2002_LIVE_PROFILE does not.
"""
from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.bank import guard as bank_guard
from tw2k.engine.models import Player, PortClass
from tw2k.engine.navpoints import menu_rows, resolve_navpoint


def _legacy(monkeypatch) -> None:
    monkeypatch.setattr(K, "STARDOCK_LOCATION_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")


def _mode_on(monkeypatch) -> None:
    _legacy(monkeypatch)
    monkeypatch.setattr(K, "STARDOCK_LOCATION_MODE", "v311")


def _world(seed: int):
    return generate_universe(GameConfig(
        seed=seed, universe_size=80, max_days=2, enable_ferrengi=True,
    ))


def test_switch_defaults_legacy_and_only_v311_turns_it_on(monkeypatch) -> None:
    assert K.STARDOCK_LOCATION_MODE == "legacy"
    assert K.stardock_location_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    monkeypatch.setattr(K, "STARDOCK_LOCATION_MODE", "1")
    assert K.stardock_location_live() is False
    monkeypatch.setattr(K, "STARDOCK_LOCATION_MODE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    assert K.stardock_location_live() is False
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.stardock_location_live() is True
    assert K.STARDOCK_LOCATION_MODE == "legacy"
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "STARDOCK_LOCATION_MODE", "v311")
    assert K.stardock_location_live() is True
    assert K.V311_PROFILE_HELPERS["stardock_location_live"][0] == "STARDOCK_LOCATION_MODE"


def test_off_keeps_stardock_in_sector_1(monkeypatch) -> None:
    _legacy(monkeypatch)
    universe = _world(15)
    assert universe.stardock_sector is None
    assert K.stardock_sector_of(universe) == 1
    port = universe.sectors[1].port
    assert port is not None and port.class_id == PortClass.STARDOCK
    assert K.fedspace_sectors_of(universe) == set(range(1, 11))
    assert K.in_fedspace(universe, 1) and K.in_fedspace(universe, 10)
    assert not K.in_fedspace(universe, 11)
    dumped = universe.model_dump()
    assert "stardock_sector" not in dumped
    rows = {row["slot"]: row["sector"] for row in menu_rows(universe, Player(id="A", name="A"))}
    assert rows["terra"] == 1
    assert rows["stardock"] == 1


def test_string_1_does_not_move_the_dock(monkeypatch) -> None:
    _legacy(monkeypatch)
    left = _world(15)
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    monkeypatch.setattr(K, "STARDOCK_LOCATION_MODE", "1")
    right = _world(15)
    assert right.stardock_sector is None
    assert right.sectors[1].port is not None
    assert right.sectors[1].port.class_id == PortClass.STARDOCK
    assert right.sectors[1].port.name == left.sectors[1].port.name


def test_on_places_an_ordinary_sector_and_fedspace_includes_it(monkeypatch) -> None:
    _mode_on(monkeypatch)
    docks: set[int] = set()
    for seed in (1, 2, 3, 7, 11, 19, 42, 99):
        universe = _world(seed)
        dock = int(universe.stardock_sector)
        docks.add(dock)
        assert dock != 1
        assert dock not in K.FEDSPACE_SECTORS
        specials = {int(v) for v in (universe.class0_sectors or {}).values()}
        assert dock not in specials
        home = getattr(universe, "ferrengal_sector", None)
        if home:
            assert dock != int(home)
        port = universe.sectors[dock].port
        assert port is not None
        assert port.class_id == PortClass.STARDOCK
        assert not getattr(port, "special", None)
        origin = universe.sectors[1].port
        assert origin is None or origin.class_id != PortClass.STARDOCK
        assert K.fedspace_sectors_of(universe) == set(range(1, 11)) | {dock}
        for sid in range(1, 11):
            assert K.in_fedspace(universe, sid)
        assert K.in_fedspace(universe, dock)
        other = next(sid for sid in range(11, 80) if sid != dock)
        assert not K.in_fedspace(universe, other)
        assert int(universe.terra_colonists or 0) > 0
        player = Player(id="A", name="A", sector_id=1)
        assert bank_guard(universe, player) == "the bank is at StarDock"
        player.sector_id = dock
        assert bank_guard(universe, player) is None
        rows = {row["slot"]: row["sector"] for row in menu_rows(universe, player)}
        assert rows["terra"] == 1
        assert rows["stardock"] == dock
        assert resolve_navpoint(player, "stardock", universe) == dock
        assert resolve_navpoint(player, "terra", universe) == 1
        assert resolve_navpoint(player, "stardock") == 1
    assert len(docks) > 1
