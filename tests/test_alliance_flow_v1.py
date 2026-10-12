"""alliance-flow-v1. Peaceful allied landings and plain proposal endings stay off."""
from tw2k.engine import Action, ActionKind, GameConfig, generate_universe
from tw2k.engine.models import Alliance, Planet, PlanetClass, Player, Ship, ShipClass
from tw2k.engine.runner import apply_action, tick_day
import tw2k.engine.constants as K


def _pair():
    universe = generate_universe(GameConfig(seed=3, universe_size=30, max_days=2, enable_ferrengi=False))
    sid = next(s for s in sorted(universe.sectors) if s > 10)
    left = Player(id="P1", name="Left", sector_id=sid, ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER))
    right = Player(id="P2", name="Right", sector_id=sid, ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER))
    universe.players["P1"] = left
    universe.players["P2"] = right
    universe.sectors[sid].occupant_ids.extend(["P1", "P2"])
    planet = Planet(id=9002, sector_id=sid, name="Camp", class_id=PlanetClass.M, owner_id="P2")
    universe.planets[9002] = planet
    universe.sectors[sid].planet_ids.append(9002)
    universe.alliances["A1"] = Alliance(id="A1", member_ids=["P1", "P2"], proposed_by="P2", formed_day=universe.day, active=True)
    left.alliances.append("A1")
    right.alliances.append("A1")
    return universe


def test_flag_stays_legacy() -> None:
    assert K.ALLIANCE_MODE == "legacy"
    assert K.alliance_live() is False


def test_off_an_ally_still_seizes_and_a_break_stays_hostile() -> None:
    universe = _pair()
    result = apply_action(universe, "P1", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": 9002}))
    assert result.ok is True
    assert universe.planets[9002].owner_id == "P1"
    universe.alliances["A2"] = Alliance(id="A2", member_ids=["P1", "P2"], proposed_by="P2", formed_day=1, active=False)
    apply_action(universe, "P1", Action(kind=ActionKind.BREAK_ALLIANCE, args={"alliance_id": "A2"}))
    assert "BROKEN" in universe.events[-1].summary
    tick_day(universe)
    assert "A2" in universe.alliances


def test_on_an_ally_lands_in_peace_and_a_proposal_ends_in_plain_words(monkeypatch) -> None:
    monkeypatch.setattr(K, "ALLIANCE_MODE", "live")
    universe = _pair()
    result = apply_action(universe, "P1", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": 9002}))
    assert result.ok is True
    assert universe.planets[9002].owner_id == "P2"
    assert "SEIZED" not in universe.events[-1].summary
    universe.alliances["A2"] = Alliance(
        id="A2", member_ids=["P1", "P2"], proposed_by="P2", formed_day=universe.day, active=False,
    )
    apply_action(universe, "P1", Action(kind=ActionKind.BREAK_ALLIANCE, args={"alliance_id": "A2"}))
    assert universe.events[-1].summary == "Left declined the alliance proposal [A2]"
    universe.alliances["A3"] = Alliance(
        id="A3", member_ids=["P1", "P2"], proposed_by="P2", formed_day=universe.day, active=False,
    )
    tick_day(universe)
    assert "A3" not in universe.alliances
    assert any(ev.summary == "The alliance proposal [A3] expired." for ev in universe.events)
