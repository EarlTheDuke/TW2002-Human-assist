"""fed-ships-ferrengi-v1. The three starships appear only when the switch is on."""
import pytest

import tw2k.engine.constants as K
from tw2k.engine import GameConfig, generate_universe

pytestmark = pytest.mark.legacy_profile


def _universe():
    return generate_universe(
        GameConfig(seed=4, universe_size=20, max_days=3, enable_planets=False, enable_ferrengi=False)
    )


def test_flag_stays_legacy_and_regen_is_already_twenty_percent() -> None:
    assert K.FED_SHIPS_MODE == "legacy"
    assert K.fed_ships_live() is False
    assert K.FERRENGI_REGEN_PCT == 0.20


def test_off_adds_no_starships() -> None:
    universe = _universe()
    assert universe.fed_starships == []
    assert [f.name for f in universe.federals] == ["Zyrain", "Nelson", "Clausewitz"]


def test_on_places_the_three_starships(monkeypatch) -> None:
    monkeypatch.setattr(K, "FED_SHIPS_MODE", "live")
    universe = _universe()
    ships = universe.fed_starships
    assert [s.name for s in ships] == ["Intrepid", "Valiant", "Lexington"]
    assert ships[0].sector_id == K.STARDOCK_SECTOR
    assert ships[1].sector_id != ships[0].sector_id
    assert ships[2].sector_id != ships[1].sector_id
    assert [f.name for f in universe.federals] == ["Zyrain", "Nelson", "Clausewitz"]
