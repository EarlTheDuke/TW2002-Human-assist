"""A race grudge starts only when that switch is on.

Off, a witnessed kill leaves the list empty. On, another alien of the
same race in the sector puts the killer at the top. Ten names, newest
first. A lone kill does not start one. The list is not saved.

Plants:
  pb1 — a witnessed live kill still leaves the list empty.
  pb2 — the switch off still records the killer.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine.alien import note_gold_grudge, on_alien_killed
from tw2k.engine.models import AlienTrader, GameConfig, Player, Ship
from tw2k.engine.universe import generate_universe


def _alien(aid: str, race: str, sector: int = 5) -> AlienTrader:
    return AlienTrader(id=aid, name=aid, ship_name=aid, sector_id=sector, ship=Ship(), race=race)


def _world():
    u = generate_universe(GameConfig(seed=3, universe_size=40, enable_ferrengi=False, enable_planets=False))
    u.players["A"] = Player(id="A", name="Alpha", ship=Ship(), sector_id=5, credits=1000)
    u.aliens["X"] = _alien("X", "Zed")
    u.aliens["Y"] = _alien("Y", "Zed")
    return u


def test_switch_stays_off() -> None:
    assert K.GOLD_ALIEN_MODE == "legacy"
    assert K.gold_alien_live() is False


def test_off_records_nothing() -> None:
    u = _world()
    on_alien_killed(u, "A", u.aliens["X"])
    assert u.gold_grudges == {}
    assert "gold_grudges" not in u.model_dump()
    blank = AlienTrader(id="Z", name="Z", ship_name="Z", sector_id=1, ship=Ship()).model_dump()
    assert "race" not in blank and "protective" not in blank


def test_on_needs_a_witness_and_keeps_ten() -> None:
    u = _world()
    K.GOLD_ALIEN_MODE = "live"
    try:
        alone = _world()
        alone.aliens.pop("Y")
        on_alien_killed(alone, "A", alone.aliens["X"])
        assert alone.gold_grudges == {}
        on_alien_killed(u, "A", u.aliens["X"])
        assert u.gold_grudges["Zed"] == ["A"]
        assert "gold_grudges" not in u.model_dump()
        for n in range(11):
            note_gold_grudge(u, f"P{n}", u.aliens["X"])
        assert u.gold_grudges["Zed"][0] == "P10"
        assert len(u.gold_grudges["Zed"]) == 10
        assert "P0" not in u.gold_grudges["Zed"]
    finally:
        K.GOLD_ALIEN_MODE = "legacy"
