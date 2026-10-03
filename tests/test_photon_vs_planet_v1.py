"""A photon damps vulnerable planet cannons for one approach."""

from __future__ import annotations

from tests.test_phase_abc import _make_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.combat import _destroy_ship
from tw2k.engine.models import Commodity, EventKind, Planet, PlanetClass
from tw2k.engine.observation import event_facts
from tw2k.engine.runner import apply_action, tick_day


def _lane(u):
    for sid, sector in u.sectors.items():
        if sid <= 10:
            continue
        for dest in sector.warps:
            if dest > 10:
                return sid, dest
    raise AssertionError("no warp lane")


def _stand(u, player, sid: int) -> None:
    here = u.sectors[player.sector_id]
    if player.id in here.occupant_ids:
        here.occupant_ids.remove(player.id)
    player.sector_id = sid
    player.planet_landed = None
    player.turns_today = 0
    if player.id not in u.sectors[sid].occupant_ids:
        u.sectors[sid].occupant_ids.append(player.id)


def _plant(u, sid: int, planet_id: int, owner: str, *, level: int, shields: int) -> Planet:
    sector = u.sectors[sid]
    sector.planet_ids = [pid for pid in sector.planet_ids if pid != planet_id]
    planet = Planet(
        id=planet_id, sector_id=sid, name=f"P{planet_id}", class_id=PlanetClass.M,
        owner_id=owner, citadel_level=level, citadel_target=level, shields=shields,
        quasar_sector_pct=10, quasar_atm_pct=10,
    )
    planet.stockpile[Commodity.FUEL_ORE] = 10_000
    u.planets[planet.id] = planet
    if planet.id not in sector.planet_ids:
        sector.planet_ids.append(planet.id)
    return planet


def _clear(u, sid: int) -> None:
    sector = u.sectors[sid]
    sector.mines.clear()
    sector.fighters = None


def _photon(u, shooter, target):
    shooter.ship.photon_missiles = 1
    shooter.turns_today = 0
    before = target.ship.photon_disabled_ticks
    res = apply_action(
        u, shooter.id, Action(kind=ActionKind.PHOTON_MISSILE, args={"target": target.id}),
    )
    assert res.ok, res.error
    assert shooter.ship.photon_missiles == 0
    assert target.ship.photon_disabled_ticks > before
    return res


def _damped(u):
    return [ev for ev in u.events if ev.kind is EventKind.QUASAR_DAMPED]


def _sector_shots(u, planet_id: int):
    return [
        ev for ev in u.events
        if ev.kind is EventKind.QUASAR_FIRE
        and ev.payload.get("mode") == "sector"
        and ev.payload.get("planet_id") == planet_id
    ]


def test_photon_with_no_planet_does_not_damp() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=14001)
    origin, _dest = _lane(u)
    u.sectors[origin].planet_ids.clear()
    _stand(u, attacker, origin)
    _stand(u, owner, origin)
    u.events.clear()
    _photon(u, owner, attacker)
    assert attacker.photon_damped_sector_id is None
    assert not _damped(u)


def test_damped_warp_skips_sector_quasar_and_stays_for_the_approach() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=14002)
    origin, dest = _lane(u)
    planet = _plant(u, dest, 88051, owner.id, level=3, shields=0)
    attacker.ship.fighters = 2000
    attacker.ship.shields = 0
    _clear(u, dest)
    _stand(u, attacker, dest)
    _stand(u, owner, dest)
    u.events.clear()
    _photon(u, owner, attacker)
    assert attacker.photon_damped_sector_id == dest
    shot = _damped(u)[-1]
    assert shot.payload["planet_id"] == 88051
    assert shot.payload["damped"] is True
    assert "shields" not in shot.payload
    assert "fighters" not in shot.payload
    assert set(event_facts(shot)) == {"planet_id", "damped"}
    assert "199" not in shot.summary and "10000" not in shot.summary

    _stand(u, attacker, origin)
    assert attacker.photon_damped_sector_id == dest
    u.events.clear()
    res = apply_action(u, attacker.id, Action(kind=ActionKind.WARP, args={"target": dest}))
    assert res.ok, res.error
    assert not _sector_shots(u, planet.id)
    assert planet.stockpile[Commodity.FUEL_ORE] == 10_000
    assert attacker.photon_damped_sector_id == dest


def test_leaving_the_sector_clears_the_damp_and_the_next_warp_is_shot() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=14003)
    origin, dest = _lane(u)
    planet = _plant(u, dest, 88052, owner.id, level=3, shields=0)
    attacker.ship.fighters = 2000
    attacker.ship.shields = 0
    _clear(u, dest)
    _clear(u, origin)
    _stand(u, attacker, dest)
    _stand(u, owner, dest)
    _photon(u, owner, attacker)
    res = apply_action(u, attacker.id, Action(kind=ActionKind.WARP, args={"target": origin}))
    assert res.ok, res.error
    assert attacker.photon_damped_sector_id is None
    u.events.clear()
    res = apply_action(u, attacker.id, Action(kind=ActionKind.WARP, args={"target": dest}))
    assert res.ok, res.error
    assert _sector_shots(u, planet.id)[-1].payload["damage"] == 333
    assert planet.stockpile[Commodity.FUEL_ORE] == 9000


def test_citadel_and_shield_gate() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=14004)
    origin, dest = _lane(u)
    planet = _plant(u, dest, 88053, owner.id, level=5, shields=200)
    attacker.ship.fighters = 2000
    attacker.ship.shields = 0
    _clear(u, dest)

    def approach(level: int, shields: int) -> tuple[bool, int]:
        planet.citadel_level = level
        planet.shields = shields
        planet.stockpile[Commodity.FUEL_ORE] = 10_000
        attacker.photon_damped_sector_id = None
        attacker.ship.fighters = 2000
        attacker.ship.photon_disabled_ticks = 0
        _stand(u, attacker, dest)
        _stand(u, owner, dest)
        owner.ship.photon_missiles = 1
        u.events.clear()
        _photon(u, owner, attacker)
        marked = attacker.photon_damped_sector_id == dest
        _stand(u, attacker, origin)
        u.events.clear()
        apply_action(u, attacker.id, Action(kind=ActionKind.WARP, args={"target": dest}))
        return marked, int(planet.stockpile[Commodity.FUEL_ORE])

    marked, fuel = approach(5, 200)
    assert marked is False
    assert fuel == 9000

    marked, fuel = approach(5, 199)
    assert marked is True
    assert fuel == 10_000

    marked, fuel = approach(4, 200)
    assert marked is True
    assert fuel == 10_000


def test_landing_skips_atmosphere_and_offensive_fighters_then_clears() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=14005)
    _origin, dest = _lane(u)
    planet = _plant(u, dest, 88054, owner.id, level=3, shields=0)
    planet.quasar_sector_pct = 0
    planet.fighters = 30
    planet.military_reaction_pct = 100
    attacker.ship.fighters = 100
    attacker.ship.shields = 0
    _clear(u, dest)
    _stand(u, attacker, dest)
    _stand(u, owner, dest)
    u.events.clear()
    _photon(u, owner, attacker)
    res = apply_action(u, attacker.id, Action(kind=ActionKind.LAND_PLANET, args={"planet_id": planet.id}))
    assert res.ok, res.error
    assert not [ev for ev in u.events if ev.kind is EventKind.QUASAR_FIRE]
    assert planet.stockpile[Commodity.FUEL_ORE] == 10_000
    combat = [ev for ev in u.events if ev.kind is EventKind.COMBAT][-1]
    phases = [row["phase"] for row in combat.payload["rounds"]]
    assert "offense" not in phases
    assert "defense" in phases
    assert attacker.photon_damped_sector_id is None


def test_without_a_photon_atmosphere_and_offense_still_run() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=14006)
    _origin, dest = _lane(u)
    planet = _plant(u, dest, 88055, owner.id, level=3, shields=0)
    planet.fighters = 30
    planet.military_reaction_pct = 100
    attacker.ship.fighters = 5000
    attacker.ship.shields = 0
    _clear(u, dest)
    _stand(u, attacker, dest)
    u.events.clear()
    res = apply_action(u, attacker.id, Action(kind=ActionKind.LAND_PLANET, args={"planet_id": planet.id}))
    assert res.ok, res.error
    shots = [ev for ev in u.events if ev.kind is EventKind.QUASAR_FIRE]
    assert len(shots) == 2
    combat = [ev for ev in u.events if ev.kind is EventKind.COMBAT][-1]
    phases = [row["phase"] for row in combat.payload["rounds"]]
    assert "offense" in phases


def test_shields_and_defensive_fighters_still_apply_while_damped() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=14007)
    _origin, dest = _lane(u)
    planet = _plant(u, dest, 88056, owner.id, level=3, shields=40)
    planet.quasar_atm_pct = 0
    planet.fighters = 0
    attacker.ship.fighters = 100
    attacker.ship.shields = 0
    _clear(u, dest)
    _stand(u, attacker, dest)
    _stand(u, owner, dest)
    _photon(u, owner, attacker)
    res = apply_action(u, attacker.id, Action(kind=ActionKind.LAND_PLANET, args={"planet_id": planet.id}))
    assert res.ok is False
    assert res.error == "planetary defenses repelled landing"
    assert planet.shields == 35
    assert attacker.photon_damped_sector_id is None


def test_death_clears_the_damp_before_the_ship_returns() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=14008)
    origin, dest = _lane(u)
    planet = _plant(u, dest, 88057, owner.id, level=3, shields=0)
    planet.quasar_atm_pct = 0
    attacker.photon_damped_sector_id = dest
    attacker.ship.fighters = 2000
    attacker.ship.shields = 0
    _destroy_ship(u, attacker.id, reason="quasar", killer_id=owner.id)
    assert attacker.photon_damped_sector_id is None
    _clear(u, dest)
    _stand(u, attacker, origin)
    apply_action(u, attacker.id, Action(kind=ActionKind.WARP, args={"target": dest}))
    assert _sector_shots(u, planet.id)
    assert planet.stockpile[Commodity.FUEL_ORE] == 9000


def test_day_tick_clears_the_damp() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=14009)
    origin, dest = _lane(u)
    planet = _plant(u, dest, 88058, owner.id, level=3, shields=0)
    planet.quasar_atm_pct = 0
    attacker.photon_damped_sector_id = dest
    attacker.ship.fighters = 2000
    attacker.ship.shields = 0
    tick_day(u)
    assert attacker.photon_damped_sector_id is None
    planet.stockpile[Commodity.FUEL_ORE] = 10_000
    planet.quasar_sector_pct = 10
    _clear(u, dest)
    _stand(u, attacker, origin)
    apply_action(u, attacker.id, Action(kind=ActionKind.WARP, args={"target": dest}))
    assert _sector_shots(u, planet.id)
    assert planet.stockpile[Commodity.FUEL_ORE] == 9000
