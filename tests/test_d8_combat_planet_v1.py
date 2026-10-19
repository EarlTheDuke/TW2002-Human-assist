"""NOTE 41 engine gates. Each new switch stays legacy unless the test turns it on."""

from __future__ import annotations

import tw2k.engine.constants as K
from tests.test_phase_abc import _first_non_fed_sector, _make_universe
from tests.test_ship_combat_core_v1 import _act, _duel
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.runner import apply_action
from tw2k.engine.models import EventKind, FerrengiShip, Planet, PlanetClass
from tw2k.engine.observation import event_facts


def _stand(u, player, sector_id: int) -> None:
    here = u.sectors[player.sector_id]
    if player.id in here.occupant_ids:
        here.occupant_ids.remove(player.id)
    player.sector_id = int(sector_id)
    player.planet_landed = None
    dest = u.sectors[player.sector_id]
    if player.id not in dest.occupant_ids:
        dest.occupant_ids.append(player.id)


def test_published_flee_uses_the_fighters_sent() -> None:
    # 300 sent against 400 shields is not enough. What is left after the hit would still flee.
    _prior_ship_flee_mode = K.SHIP_FLEE_MODE
    try:
        u, a, d, _c, sid = _duel(41001)
        a.ship.fighters, d.ship.fighters, d.ship.shields = 1000, 0, 400
        try:
            K.SHIP_FLEE_MODE = "tw2002"
            assert _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=300).ok
            assert d.sector_id == sid
            facts = event_facts(next(e for e in reversed(u.events) if e.kind is EventKind.COMBAT))
            assert facts["shield_losses"] == 300
            assert facts["defender_fled"] is False
            assert d.ship.shields == 100
        finally:
            K.SHIP_FLEE_MODE = "legacy"
    finally:
        K.SHIP_FLEE_MODE = _prior_ship_flee_mode


def test_siege_report_names_the_losses_only_when_the_switch_is_on() -> None:
    _prior_siege_report_mode = K.SIEGE_REPORT_MODE
    try:
        def land(seed: int):
            u, (owner, attacker, _other) = _make_universe(seed=seed)
            planet = Planet(
                id=41010, sector_id=80, name="Phoenix", class_id=PlanetClass.M,
                owner_id=owner.id, fighters=500, shields=30, citadel_level=2, citadel_target=2,
            )
            u.planets[planet.id] = planet
            u.sectors[80].planet_ids.append(planet.id)
            _stand(u, attacker, 80)
            attacker.ship.fighters = 40
            attacker.ship.shields = 0
            res = _act(u, attacker.id, ActionKind.LAND_PLANET, planet_id=planet.id)
            fight = next(e for e in reversed(u.events) if e.kind is EventKind.COMBAT and e.payload.get("vs") == "planet")
            return res, fight

        refused, fight = land(41010)
        assert not refused.ok
        assert "planetary defenses repelled landing" in (refused.error or "")
        assert "planet_fighters_lost" not in event_facts(fight)
        try:
            K.SIEGE_REPORT_MODE = "tw2002"
            refused, fight = land(41011)
            facts = event_facts(fight)
            assert facts["planet_fighters_lost"] >= 0
            assert facts["planet_shields_lost"] >= 0
            assert facts["attacker_losses"] >= 0
            assert facts["defender_owner"]
        finally:
            K.SIEGE_REPORT_MODE = "legacy"
    finally:
        K.SIEGE_REPORT_MODE = _prior_siege_report_mode


def test_planet_shields_need_level_5_when_the_switch_is_on() -> None:
    _prior_planet_shield_mode = K.PLANET_SHIELD_MODE
    try:
        u, (owner, _mate, _out) = _make_universe(seed=41020)
        planet = Planet(
            id=41020, sector_id=90, name="Shield", class_id=PlanetClass.M,
            owner_id=owner.id, fighters=0, shields=0, citadel_level=2, citadel_target=2,
        )
        u.planets[planet.id] = planet
        u.sectors[90].planet_ids.append(planet.id)
        _stand(u, owner, 90)
        owner.planet_landed = planet.id
        owner.ship.shields = 30
        try:
            K.PLANET_SHIELD_MODE = "tw2002"
            res = apply_action(u, owner.id, Action(kind=ActionKind.DEPOSIT_PLANET_DEFENSE, args={"planet_id": planet.id, "kind": "shields", "qty": 1}))
            assert not res.ok
            assert res.error == "Planetary shields need a Level 5 citadel"
            assert planet.shields == 0
        finally:
            K.PLANET_SHIELD_MODE = "legacy"
        ok = apply_action(u, owner.id, Action(kind=ActionKind.DEPOSIT_PLANET_DEFENSE, args={"planet_id": planet.id, "kind": "shields", "qty": 1}))
        assert ok.ok, ok.error
        assert planet.shields == 1
    finally:
        K.PLANET_SHIELD_MODE = _prior_planet_shield_mode


def test_attack_refusal_says_one_to() -> None:
    u, a, d, _c, _sid = _duel(41030)
    a.ship.fighters = 2000
    res = _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=5000)
    assert not res.ok
    assert "1 to" in (res.error or "")
    assert ".." not in (res.error or "")


def test_ferrengi_engages_on_entry_and_strikes_back() -> None:
    _prior_ferrengi_engage_mode = K.FERRENGI_ENGAGE_MODE
    try:
        u, (pilot, _b, _c) = _make_universe(seed=41040)
        home = _first_non_fed_sector(u, 40)
        there = u.sectors[home].warps[0]
        _stand(u, pilot, home)
        pilot.ship.fighters = 20
        u.ferrengi["F41"] = FerrengiShip(
            id="F41", name="Dread", sector_id=there, aggression=8, fighters=400, shields=200,
        )
        start = len(u.events)
        assert _act(u, pilot.id, ActionKind.WARP, target=there).ok
        assert not any(e.kind is EventKind.FERRENGI_ENCOUNTER for e in u.events[start:])
        try:
            K.FERRENGI_ENGAGE_MODE = "tw2002"
            u, (pilot, _b, _c) = _make_universe(seed=41041)
            home = _first_non_fed_sector(u, 40)
            there = u.sectors[home].warps[0]
            _stand(u, pilot, home)
            pilot.ship.fighters = 20
            u.ferrengi["F41"] = FerrengiShip(
                id="F41", name="Dread", sector_id=there, aggression=8, fighters=400, shields=200,
            )
            assert _act(u, pilot.id, ActionKind.WARP, target=there).ok
            assert any(e.kind is EventKind.FERRENGI_ENCOUNTER for e in u.events)
            u, a, _d, _c, sid = _duel(41042)
            a.ship.fighters = 30
            u.ferrengi["F42"] = FerrengiShip(
                id="F42", name="Dread", sector_id=sid, aggression=8, fighters=800, shields=400,
            )
            assert _act(u, a.id, ActionKind.ATTACK, target="F42", qty=10).ok
            assert any(e.kind is EventKind.FERRENGI_ATTACK for e in u.events)
        finally:
            K.FERRENGI_ENGAGE_MODE = "legacy"
    finally:
        K.FERRENGI_ENGAGE_MODE = _prior_ferrengi_engage_mode
