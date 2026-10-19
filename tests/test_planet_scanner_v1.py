"""A planet scanner is sold only when that switch is on.

Off, StarDock does not sell one, and a stranger still cannot read fighters.
On, it costs 30,000. It shows the fighters of a planet with no shields.
A shielded planet stays dark.

Plants:
  pb1 — a scanner still hides the fighters of an unshielded planet.
  pb2 — StarDock sells a planet scanner while the switch is off.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Planet, PlanetClass, Player, Ship
from tw2k.engine.observation import _planet_brief


def _world():
    u = generate_universe(GameConfig(seed=5101, universe_size=80, enable_ferrengi=False, enable_planets=True))
    u.players["A"] = Player(
        id="A", name="Alpha", ship=Ship(holds=20, fighters=20),
        sector_id=K.STARDOCK_SECTOR, credits=50_000,
    )
    u.sectors[K.STARDOCK_SECTOR].occupant_ids.append("A")
    bare = Planet(id=9001, sector_id=20, name="Bare", class_id=PlanetClass.M,
                  owner_id="B", fighters=40, shields=0)
    shielded = Planet(id=9002, sector_id=21, name="Shielded", class_id=PlanetClass.M,
                      owner_id="B", fighters=40, shields=25)
    return u, bare, shielded


def _shop(u):
    buy = next(a for a in legal_actions(u, "A") if a.kind == "buy_equip")
    return buy.params["item"]["choices"], buy.params["item"]["unit_price_by"]


def test_switch_stays_off() -> None:
    assert K.PLANET_SCANNER_MODE == "legacy"
    assert K.planet_scanner_live() is False
    assert K.PLANET_SCANNER_COST == 30_000


def test_off_does_not_sell_or_reveal() -> None:
    u, bare, shielded = _world()
    choices, prices = _shop(u)
    assert "planet_scanner" not in choices
    assert "planet_scanner" not in prices
    bought = apply_action(u, "A", Action(kind=ActionKind.BUY_EQUIP, args={"item": "planet_scanner", "qty": 1}))
    assert bought.ok is False
    assert u.players["A"].ship.planet_scanner is False
    u.players["A"].ship.planet_scanner = True
    assert "fighters" not in _planet_brief(bare, u.players["A"])
    assert "fighters" not in _planet_brief(shielded, u.players["A"])
    assert "planet_scanner" not in Ship().model_dump()


def test_on_reads_unshielded_planets_only() -> None:
    _prior_planet_scanner_mode = K.PLANET_SCANNER_MODE
    try:
        u, bare, shielded = _world()
        try:
            K.PLANET_SCANNER_MODE = "live"
            choices, prices = _shop(u)
            assert "planet_scanner" in choices
            assert prices["planet_scanner"] == 30_000
            bought = apply_action(u, "A", Action(kind=ActionKind.BUY_EQUIP, args={"item": "planet_scanner", "qty": 1}))
            assert bought.ok is True
            assert u.players["A"].credits == 20_000
            assert u.players["A"].ship.planet_scanner is True
            again = apply_action(u, "A", Action(kind=ActionKind.BUY_EQUIP, args={"item": "planet_scanner", "qty": 1}))
            assert again.ok is False
            seen = _planet_brief(bare, u.players["A"])
            assert seen["owner_id"] == "B"
            assert seen["fighters"] == 40
            assert "fighters" not in _planet_brief(shielded, u.players["A"])
            u.players["A"].ship.planet_scanner = False
            assert "fighters" not in _planet_brief(bare, u.players["A"])
        finally:
            K.PLANET_SCANNER_MODE = "legacy"
    finally:
        K.PLANET_SCANNER_MODE = _prior_planet_scanner_mode
