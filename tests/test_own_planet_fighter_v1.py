"""own-planet-landing-fighters-v1. The owner lands only when the switch is on."""
import pytest

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, generate_universe
from tw2k.engine.combat import open_challenge
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import FighterDeployment, FighterMode, Planet, PlanetClass, Player, Ship, ShipClass
from tw2k.engine.runner import apply_action

pytestmark = pytest.mark.legacy_profile


def _world():
    universe = generate_universe(GameConfig(seed=3, universe_size=30, max_days=2, enable_ferrengi=False))
    sid = next(s for s in sorted(universe.sectors) if s > 10)
    owner = Player(id="P1", name="Owner", sector_id=sid, ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER))
    universe.players["P1"] = owner
    universe.sectors[sid].occupant_ids.append("P1")
    planet = Planet(id=9001, sector_id=sid, name="Home", class_id=PlanetClass.M, owner_id="P1")
    universe.planets[9001] = planet
    universe.sectors[sid].planet_ids.append(9001)
    universe.sectors[sid].fighters = FighterDeployment(owner_id="P2", count=100, mode=FighterMode.DEFENSIVE)
    owner.fighter_challenge = {"sector_id": sid, "from_sector": list(universe.sectors[sid].warps)[0], "mode": "defensive"}
    return universe


def test_flag_stays_legacy() -> None:
    assert K.OWN_PLANET_FIGHTER_MODE == "legacy"
    assert K.own_planet_fighter_live() is False


def test_off_the_fighters_still_block_the_owner() -> None:
    universe = _world()
    result = apply_action(universe, "P1", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": 9001}))
    assert result.ok is False
    assert universe.players["P1"].planet_landed is None
    land = next(la for la in legal_actions(universe, "P1") if la.kind == "land_planet")
    assert land.legal is False


def test_on_the_owner_lands_and_a_toll_names_the_price(monkeypatch) -> None:
    monkeypatch.setattr(K, "OWN_PLANET_FIGHTER_MODE", "live")
    universe = _world()
    result = apply_action(universe, "P1", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": 9001}))
    assert result.ok is True
    assert universe.players["P1"].planet_landed == 9001
    sid = universe.players["P1"].sector_id
    universe.sectors[sid].fighters = FighterDeployment(owner_id="P2", count=100, mode=FighterMode.TOLL)
    universe.players["P1"].fighter_challenge = None
    back = list(universe.sectors[sid].warps)[0]
    assert open_challenge(universe, "P1", universe.sectors[sid], back) is True
    assert "500 credits" in universe.events[-1].summary
