"""v311-combat-gaps-v1 (COMMANDER NOTE 79). Rows 90 and 93.

Row 91 (CMB-i) and row 92 (FIG-e) were already on this tip. CMB-c is the
plan in docs/plans/ship-odds-exchange-v1.md and has no switch.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

import tw2k.engine.constants as K
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.combat import _destroy_ship
from tw2k.engine.hardware import armid_detonation_hits
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import (
    Commodity,
    EventKind,
    FighterDeployment,
    FighterMode,
    MineDeployment,
    MineType,
    Planet,
    PlanetClass,
    Player,
    Ship,
    ShipClass,
)
from tw2k.engine.runner import apply_action, tick_day
from tw2k.engine.victory import combat_rewards, kill_rewards

pytestmark = pytest.mark.legacy_profile


def _lane(universe):
    for sid, sector in universe.sectors.items():
        if sid <= 10:
            continue
        for dest in sector.warps:
            if dest > 10:
                return sid, dest
    raise AssertionError("no warp lane")


def _stand(universe, player: Player, sid: int) -> None:
    here = universe.sectors[player.sector_id]
    if player.id in here.occupant_ids:
        here.occupant_ids.remove(player.id)
    player.sector_id = sid
    player.planet_landed = None
    player.turns_today = 0
    if player.id not in universe.sectors[sid].occupant_ids:
        universe.sectors[sid].occupant_ids.append(player.id)


def _quasar_world():
    universe = generate_universe(GameConfig(
        seed=79, universe_size=40, max_days=5, turns_per_day=40,
        enable_ferrengi=False, enable_planets=False,
    ))
    origin, dest = _lane(universe)
    shooter = Player(
        id="S", name="Sid", sector_id=origin, credits=10_000,
        ship=Ship(ship_class=ShipClass.MISSILE_FRIGATE, photon_missiles=1, fighters=10, shields=10),
    )
    follower = Player(
        id="F", name="Fay", sector_id=origin, credits=10_000,
        ship=Ship(fighters=100, shields=500),
    )
    owner = Player(id="O", name="Otto", sector_id=dest, credits=10_000, ship=Ship())
    for player in (shooter, follower, owner):
        universe.players[player.id] = player
        universe.sectors[player.sector_id].occupant_ids.append(player.id)
    sector = universe.sectors[dest]
    sector.nav_hazard = 0
    sector.mines = [MineDeployment(owner_id="O", kind=MineType.ARMID, count=4)]
    sector.fighters = FighterDeployment(owner_id="O", count=30, mode=FighterMode.OFFENSIVE)
    planet = Planet(
        id=7901, sector_id=dest, name="Cannon", class_id=PlanetClass.M,
        owner_id="O", citadel_level=3, citadel_target=3, shields=0,
        quasar_sector_pct=10,
    )
    planet.stockpile[Commodity.FUEL_ORE] = 10_000
    universe.planets[planet.id] = planet
    sector.planet_ids.append(planet.id)
    return universe, origin, dest, follower


def _shots(universe, planet_id: int):
    return [
        ev for ev in universe.events
        if ev.kind is EventKind.QUASAR_FIRE and ev.payload.get("planet_id") == planet_id
    ]


def test_following_ship_still_eats_the_quasar_until_the_switch() -> None:
    universe, origin, dest, follower = _quasar_world()
    assert K.photon_follow_damp_live() is False
    fired = apply_action(universe, "S", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": dest}))
    assert fired.ok, fired.error
    assert universe.sectors[dest].photon_wave_remaining == 1
    assert follower.photon_damped_sector_id is None
    moved = apply_action(universe, "F", Action(kind=ActionKind.WARP, args={"target": dest}))
    assert moved.ok, moved.error
    assert follower.sector_id == dest
    assert follower.ship.fighters == 100
    assert universe.sectors[dest].mines[0].count == 4
    assert follower.ship.shields == 500 - (1_000 // 3)
    assert _shots(universe, 7901)
    assert origin > 10


def test_live_wave_damps_the_quasar_for_a_following_ship(monkeypatch) -> None:
    monkeypatch.setattr(K, "PHOTON_FOLLOW_DAMP_MODE", "live")
    universe, _origin, dest, follower = _quasar_world()
    assert apply_action(universe, "S", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": dest})).ok
    moved = apply_action(universe, "F", Action(kind=ActionKind.WARP, args={"target": dest}))
    assert moved.ok, moved.error
    assert follower.photon_damped_sector_id == dest
    assert follower.ship.shields == 500
    assert follower.ship.fighters == 100
    assert universe.sectors[dest].mines[0].count == 4
    assert _shots(universe, 7901) == []


def test_profile_damps_the_following_ship(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.PHOTON_FOLLOW_DAMP_MODE == "legacy"
    universe, _origin, dest, follower = _quasar_world()
    assert apply_action(universe, "S", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": dest})).ok
    assert apply_action(universe, "F", Action(kind=ActionKind.WARP, args={"target": dest})).ok
    assert follower.ship.shields == 500
    assert _shots(universe, 7901) == []


def test_level_five_with_200_shields_still_fires(monkeypatch) -> None:
    monkeypatch.setattr(K, "PHOTON_FOLLOW_DAMP_MODE", "live")
    universe, _origin, dest, follower = _quasar_world()
    planet = universe.planets[7901]
    planet.citadel_level = 5
    planet.citadel_target = 5
    planet.shields = K.QUASAR_PHOTON_SHIELD_MIN
    assert apply_action(universe, "S", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": dest})).ok
    assert apply_action(universe, "F", Action(kind=ActionKind.WARP, args={"target": dest})).ok
    assert follower.ship.shields == 500 - (1_000 // 3)
    assert _shots(universe, 7901)


def test_kill_experience_families_are_already_on() -> None:
    """CMB-i. Cabal formulas.html prints one player-vs-player experience table."""
    assert K.COMBAT_EXP_DIVISOR == {"opposite": 15, "same": 35, "neutral": 25}
    assert K.KILL_EXP_SHARE == 0.10
    universe = generate_universe(GameConfig(seed=1, universe_size=20, enable_ferrengi=False, enable_planets=False))
    universe.players["A"] = Player(id="A", name="Ann", alignment=100, experience=0, sector_id=1)
    universe.players["K"] = Player(id="K", name="Kay", alignment=0, experience=0, sector_id=1)
    assert combat_rewards(universe, "A", -1_000, 15)[0] == 1
    universe.players["A"].alignment = -40
    universe.players["A"].experience = 0
    assert combat_rewards(universe, "A", -80, 35)[0] == 1
    universe.players["A"].alignment = 0
    universe.players["A"].experience = 0
    assert combat_rewards(universe, "A", 500, 25)[0] == 1
    kill_rewards(universe, "K", 12_000, -100_000)
    assert universe.players["K"].experience == 1_200


def test_half_the_armids_already_detonate() -> None:
    """FIG-e. hardware.armid_detonation_hits, damage ARMID_DAMAGE_TW2002."""
    assert K.hardware_tw2002()
    assert K.ARMID_DAMAGE_TW2002 == 20
    assert armid_detonation_hits(11, None) == (5, 20)
    assert armid_detonation_hits(1, None) == (0, 20)


def _pilot(universe) -> Player:
    player = Player(
        id="P", name="Pat", sector_id=1, credits=5_000,
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, fighters=20, shields=10),
    )
    universe.players["P"] = player
    universe.sectors[1].occupant_ids.append("P")
    return player


def test_death_delay_off_lets_the_pod_fly() -> None:
    universe = generate_universe(GameConfig(
        seed=3, universe_size=20, enable_ferrengi=False, enable_planets=False, death_delay=True,
    ))
    player = _pilot(universe)
    assert K.DEATH_DELAY_MODE == "legacy"
    assert K.death_delay_live() is False
    turns = int(player.turns_today)
    _destroy_ship(universe, "P", reason="mines")
    assert player.ship.ship_class.value == "escape_pod"
    assert player.death_delay_left == 0
    assert player.turns_today == turns
    dumped = GameConfig(seed=1).model_dump()
    assert "death_delay" not in dumped
    assert "deaths_per_day" not in dumped
    waited = apply_action(universe, "P", Action(kind=ActionKind.WAIT))
    assert waited.ok, waited.error


def test_default_yes_waits_until_the_next_day(monkeypatch) -> None:
    monkeypatch.setattr(K, "DEATH_DELAY_MODE", "live")
    assert K.DEATH_DELAY_MODE == "live"
    universe = generate_universe(GameConfig(
        seed=4, universe_size=20, enable_ferrengi=False, enable_planets=False,
    ))
    player = _pilot(universe)
    assert K.death_delay_enabled(universe.config) is True
    assert K.deaths_per_day_allowance(universe.config) == 0
    _destroy_ship(universe, "P", reason="mines")
    assert player.ship.ship_class.value == "escape_pod"
    assert player.deaths_today == 1
    assert player.death_delay_left == 1
    assert apply_action(universe, "P", Action(kind=ActionKind.WAIT)).error == "death delay"
    assert all(
        not row.legal and row.reason == "death delay"
        for row in legal_actions(universe, "P") if row.kind == "wait"
    )
    _destroy_ship(universe, "P", reason="combat", killer_id="O", by_other=True)
    assert player.death_delay_left == 1
    tick_day(universe)
    assert player.death_delay_left == 0
    assert apply_action(universe, "P", Action(kind=ActionKind.WAIT)).ok


def test_one_death_per_day_allows_one_restart(monkeypatch) -> None:
    monkeypatch.setattr(K, "DEATH_DELAY_MODE", "live")
    universe = generate_universe(GameConfig(
        seed=6, universe_size=20, enable_ferrengi=False, enable_planets=False, deaths_per_day=1,
    ))
    player = _pilot(universe)
    _destroy_ship(universe, "P", reason="mines")
    assert player.death_delay_left == 0
    assert apply_action(universe, "P", Action(kind=ActionKind.WAIT)).ok
    player.ship.ship_class = ShipClass.MERCHANT_CRUISER
    _destroy_ship(universe, "P", reason="mines")
    assert player.deaths_today == 2
    assert player.death_delay_left == 1
    assert apply_action(universe, "P", Action(kind=ActionKind.WAIT)).error == "death delay"
    tick_day(universe)
    assert player.death_delay_left == 0
    player.ship.ship_class = ShipClass.MERCHANT_CRUISER
    _destroy_ship(universe, "P", reason="mines")
    assert player.deaths_today == 1
    assert player.death_delay_left == 0


def test_two_deaths_per_day_lets_both_restarts_fly(monkeypatch) -> None:
    monkeypatch.setattr(K, "DEATH_DELAY_MODE", "live")
    universe = generate_universe(GameConfig(
        seed=8, universe_size=20, enable_ferrengi=False, enable_planets=False, deaths_per_day=2,
    ))
    player = _pilot(universe)
    _destroy_ship(universe, "P", reason="mines")
    player.ship.ship_class = ShipClass.MERCHANT_CRUISER
    _destroy_ship(universe, "P", reason="mines")
    assert player.deaths_today == 2
    assert player.death_delay_left == 0
    assert apply_action(universe, "P", Action(kind=ActionKind.WAIT)).ok


def test_profile_default_locks_and_no_does_not(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.DEATH_DELAY_MODE == "legacy"
    unset = generate_universe(GameConfig(seed=5, universe_size=20, enable_ferrengi=False, enable_planets=False))
    pilot = _pilot(unset)
    _destroy_ship(unset, "P", reason="mines")
    assert pilot.death_delay_left == 1
    assert apply_action(unset, "P", Action(kind=ActionKind.WAIT)).error == "death delay"
    tick_day(unset)
    assert apply_action(unset, "P", Action(kind=ActionKind.WAIT)).ok

    off = generate_universe(GameConfig(
        seed=9, universe_size=20, enable_ferrengi=False, enable_planets=False, death_delay=False,
    ))
    held = _pilot(off)
    turns = int(held.turns_today)
    held.pods_today = int(K.PODS_PER_DAY)
    held.pods_day = int(off.day)
    _destroy_ship(off, "P", reason="mines")
    assert held.ship.ship_class.value == "scout_marauder"
    assert held.death_delay_left == 0
    assert held.turns_today == turns
    assert apply_action(off, "P", Action(kind=ActionKind.WAIT)).ok


def test_death_delay_is_yes_or_no_and_deaths_per_day_has_no_stored_ceiling() -> None:
    assert GameConfig().death_delay is None
    assert GameConfig(death_delay="").death_delay is None
    assert GameConfig(death_delay=True).death_delay is True
    assert GameConfig(death_delay="yes").death_delay is True
    assert GameConfig(death_delay=False).death_delay is False
    assert GameConfig(death_delay="No").death_delay is False
    assert GameConfig().deaths_per_day is None
    assert GameConfig(deaths_per_day=0).deaths_per_day is None
    assert GameConfig(deaths_per_day=1).deaths_per_day == 1
    assert GameConfig(deaths_per_day=2).deaths_per_day == 2
    assert GameConfig(deaths_per_day=1_000_000).deaths_per_day == 1_000_000
    dumped = GameConfig(seed=1, death_delay=False, deaths_per_day=2).model_dump()
    assert dumped["death_delay"] is False
    assert dumped["deaths_per_day"] == 2
    assert "death_delay" not in GameConfig(seed=1).model_dump()
    for bad in (0, 1, 2, -1, "two"):
        with pytest.raises(ValidationError):
            GameConfig(death_delay=bad)
    for bad in (-1, True, "two"):
        with pytest.raises(ValidationError):
            GameConfig(deaths_per_day=bad)
