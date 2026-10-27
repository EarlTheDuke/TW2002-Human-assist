"""NOTE 102, rows 145-149. Each new switch off and on, and the two rows left unused."""
from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.alien import alien_day_step
from tw2k.engine.fed import _legal_fed_hops
from tw2k.engine.ferrengi import _apply_mines_to_ferrengi, _ferrengi_hops
from tw2k.engine.models import (
    AlienTrader,
    Commodity,
    EventKind,
    Federal,
    FerrengiShip,
    FighterDeployment,
    FighterMode,
    GameConfig,
    MineDeployment,
    MineType,
    ParkedShip,
    Planet,
    PlanetClass,
    Player,
    PortClass,
    Ship,
    ShipClass,
)
from tw2k.engine.observation import game_status
from tw2k.engine.runner import apply_action, tick_day
from tw2k.engine.universe import generate_universe

pytestmark = pytest.mark.legacy_profile

FUEL = Commodity.FUEL_ORE


def _world(seed: int = 7):
    u = generate_universe(
        GameConfig(seed=seed, universe_size=40, max_days=30, enable_ferrengi=False, enable_planets=True)
    )
    player = Player(
        id="P1", name="Ada", ship=Ship(ship_class=ShipClass.INTERDICTOR_CRUISER, fighters=15_000, shields=100),
        sector_id=1, credits=1_000_000, turns_per_day=500, experience=0, alignment=0,
    )
    u.players["P1"] = player
    u.sectors[1].occupant_ids.append("P1")
    return u, player


def _attack(u, qty: int = 15_000):
    return apply_action(u, "P1", Action(kind=ActionKind.ATTACK, args={"target": "port", "confirm": True, "qty": qty}))


def test_new_switches_stay_legacy() -> None:
    assert K.SPECIAL_PORT_DEFENCE_MODE == "legacy"
    assert K.special_port_defence_live() is False


def test_profile_turns_the_four_helpers_on(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.special_port_defence_live()
    assert K.SPECIAL_PORT_DEFENCE_MODE == "legacy"


def test_midnight_and_first_dock_already_run_under_the_profile(monkeypatch) -> None:
    """Row 145 does not add a second midnight or first-dock award.

    DISCOVERY_EXP_MODE already pays +1 at the day tick to a living trader who
    spent a turn, and +1 the first time that trader trades at a port.
    """
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u, player = _world()
    idle = Player(id="P2", name="Bea", ship=Ship(), sector_id=2, turns_per_day=100, experience=0, alignment=0)
    u.players["P2"] = idle
    player.turns_today = 3
    idle.turns_today = 0
    tick_day(u)
    # Experience is the documented +1. Alignment also gains that point, and the
    # rest of the profile may add more the same night, so this check is the experience.
    assert player.experience == 1
    assert idle.experience == 0
    tick_day(u)
    assert player.experience == 2
    assert idle.experience == 0

    from tests.test_ports_haggle_v1 import _port, _seat, _trade

    universe, trader = _seat()
    _port(universe, PortClass.CLASS_1_BSS, FUEL, -100, 0)
    trader.experience = 0
    assert _trade(universe, "sell", "fuel_ore").ok
    first = trader.experience
    assert _trade(universe, "sell", "fuel_ore").ok
    assert trader.experience == first + K.xp_award("trade")
    assert first == K.xp_award("trade") + 1


def test_special_port_off_is_not_the_huge_defence(monkeypatch) -> None:
    u, player = _world()
    before = player.ship.fighters
    res = _attack(u, 100)
    assert res.ok, res.error
    assert player.ship.fighters == before - 100
    assert u.sectors[1].special_port_figs == 0
    assert u.sectors[1].special_port_down_day is None
    assert u.sectors[1].port is not None
    assert player.experience == 0


def test_special_port_a_short_wave_does_not_kill_it(monkeypatch) -> None:
    monkeypatch.setattr(K, "SPECIAL_PORT_DEFENCE_MODE", "live")
    u, player = _world()
    res = _attack(u, 15_000)
    assert res.ok, res.error
    assert u.sectors[1].port is not None
    assert u.sectors[1].special_port_down_day is None
    assert u.sectors[1].special_port_figs == 15_000
    assert player.experience == 0
    assert player.ship.fighters == 0


def test_special_port_the_budget_destroys_and_the_feds_rebuild(monkeypatch) -> None:
    monkeypatch.setattr(K, "SPECIAL_PORT_DEFENCE_MODE", "live")
    u, player = _world()
    spent = 0
    while u.sectors[1].special_port_down_day is None:
        player.ship.fighters = 15_000
        player.turns_today = 0
        res = _attack(u)
        assert res.ok, res.error
        spent += 15_000
        assert spent < 300_000
    assert spent >= K.SPECIAL_PORT_FIGS_FIRST
    assert player.experience == K.PORT_DESTROY_EXPERIENCE
    assert u.sectors[1].port is not None
    down = int(u.sectors[1].special_port_down_day)
    player.ship.fighters = 10
    player.turns_today = 0
    dead = apply_action(u, "P1", Action(kind=ActionKind.TRADE, args={"side": "buy", "commodity": "fuel_ore", "qty": 1}))
    assert dead.ok is False
    assert "radiating" in dead.error
    assert player.alive is False or player.ship.ship_class == ShipClass.ESCAPE_POD
    for _ in range(K.SPECIAL_PORT_RADIATION_DAYS - 1):
        tick_day(u)
        assert u.sectors[1].special_port_down_day == down
    tick_day(u)
    assert u.sectors[1].special_port_down_day is None
    assert K.special_port_figs_needed(u.special_ports_destroyed) == K.SPECIAL_PORT_FIGS_AFTER
    assert K.special_port_rating(u.special_ports_destroyed) == K.SPECIAL_PORT_RATING_AFTER


def test_class_0_uses_the_same_budget(monkeypatch) -> None:
    monkeypatch.setattr(K, "SPECIAL_PORT_DEFENCE_MODE", "live")
    u, player = _world()
    deep = next(sid for sid, sector in u.sectors.items() if sid > 10 and sector.port is not None)
    u.sectors[deep].port.class_id = PortClass.FEDERAL
    player.sector_id = deep
    res = _attack(u, 500)
    assert res.ok, res.error
    assert u.sectors[deep].special_port_figs == 500
    assert u.sectors[deep].port is not None


def test_npcs_already_treat_player_fighters_as_the_stored_rule() -> None:
    """Row 147. Iago's War Manual v1.1: Ferrengi ignore fighters and hit mines.
    Aliens and Feds do not move into a fighter sector. No new switch.
    """
    u, _player = _world()
    home = next(sid for sid, sector in u.sectors.items() if sid > 10 and sector.warps)
    for wid in u.sectors[home].warps:
        u.sectors[wid].fighters = FighterDeployment(owner_id="P1", count=5, mode=FighterMode.DEFENSIVE)
    alien = AlienTrader(id="alien:1", name="Zog", ship_name="Zog", sector_id=home, ship=Ship(fighters=10))
    u.aliens[alien.id] = alien
    alien_day_step(u)
    assert u.aliens[alien.id].sector_id == home

    fed = Federal(name="Nelson", title="Captain", sector_id=home, density=462, home_sector=home)
    assert _legal_fed_hops(u, fed) == []
    u.sectors[u.sectors[home].warps[0]].fighters = None
    assert u.sectors[home].warps[0] in _legal_fed_hops(u, fed)

    blocked = u.sectors[home].warps[0]
    u.sectors[blocked].fighters = FighterDeployment(owner_id="P1", count=8, mode=FighterMode.DEFENSIVE)
    hops = _ferrengi_hops(u, u.sectors[home])
    assert blocked in hops

    ferr = FerrengiShip(id="F1", name="Rag", sector_id=blocked, aggression=3, fighters=40, shields=30)
    u.sectors[blocked].mines.append(MineDeployment(owner_id="P1", kind=MineType.ARMID, count=10))
    before = ferr.shields
    _apply_mines_to_ferrengi(u, ferr)
    assert ferr.shields < before


def test_collisions_on_name_the_sector_and_may_drop_two_planets(monkeypatch) -> None:
    monkeypatch.setattr(K, "PLANET_COLLISION_PCT_PER_EXCESS", 0)
    u, _player = _world()
    _overload(u, 12, 7)
    tick_day(u)
    assert len(u.sectors[12].planet_ids) == 7
    notes = [ev for ev in u.events if ev.kind == EventKind.PLANET_COLLISION]
    assert notes and "sector 12" in notes[-1].summary

    monkeypatch.setattr(K, "PLANET_COLLISION_PCT_PER_EXCESS", 100)
    u2, _p = _world(seed=8)
    _overload(u2, 12, 7)
    before = float(u2.sectors[12].nav_hazard)
    tick_day(u2)
    assert len(u2.sectors[12].planet_ids) == 5
    lost = [ev for ev in u2.events if ev.kind == EventKind.PLANET_COLLISION and ev.payload.get("destroyed")]
    assert lost and "sector" not in lost[-1].summary
    gone = lost[-1].payload["destroyed"]
    assert len(gone) == 2
    assert all(name in ("Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta") for name in gone)
    assert " and " in lost[-1].summary
    assert float(u2.sectors[12].nav_hazard) > before

    u3, _p = _world(seed=9)
    _overload(u3, 1, 8)
    tick_day(u3)
    assert len(u3.sectors[1].planet_ids) == 8


def test_bust_on_pays_75_for_the_loop_and_not_more(monkeypatch) -> None:
    u, player = _world()
    player.experience = 0
    first = _bust_once(u, player)
    assert player.experience == 75
    assert first == 75
    _bust_once(u, player)
    assert player.experience == 150


def test_bust_under_the_profile_is_the_same_75(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u, player = _world()
    player.experience = 0
    _bust_once(u, player)
    assert player.experience == 75
    assert K.xp_award("deploy_genesis") + K.xp_award("destroy_planet") == 75


def test_unmanned_fighters_are_left_out_of_the_v_screen(monkeypatch) -> None:
    u, player = _world()
    player.ship.fighters = 10
    u.parked_ships[4] = ParkedShip(
        id=4, owner_id="P1", sector_id=12, parked_day=1,
        ship=Ship(fighters=40_000, mines={MineType.ARMID: 3}),
    )
    legacy = game_status(u)
    assert legacy["fighters_in_use"] >= 40_000
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    stats = game_status(u)
    aboard = sum(int(p.ship.fighters) for p in u.players.values())
    deployed = sum(int(s.fighters.count) for s in u.sectors.values() if s.fighters is not None)
    planets = sum(int(pl.fighters) for pl in u.planets.values())
    assert stats["fighters_in_use"] == aboard + deployed + planets
    assert stats["fighters_in_use"] < 40_000
    assert stats["mines_in_use"] >= 3


def _overload(u, sector_id: int, count: int) -> None:
    sector = u.sectors[sector_id]
    sector.planet_ids = []
    names = ("Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta")
    for n in range(count):
        pid = 500 + n
        planet = Planet(id=pid, sector_id=sector_id, name=names[n], class_id=PlanetClass.M, owner_id="P1")
        u.planets[pid] = planet
        sector.planet_ids.append(pid)


def _own_planet(u, player) -> Planet:
    planet = Planet(id=77, sector_id=12, name="Bust", class_id=PlanetClass.M, owner_id=player.id)
    u.planets[77] = planet
    u.sectors[12].planet_ids.append(77)
    player.sector_id = 12
    player.planet_landed = 77
    player.ship.atomic_detonators = 1
    player.turns_today = 0
    return planet


def _bust_once(u, player) -> int:
    """Create, then destroy. Returns the experience that loop added."""
    start = int(player.experience)
    deep = _deep_sector(u)
    player.sector_id = deep
    player.planet_landed = None
    player.ship.genesis = 1
    player.ship.atomic_detonators = 1
    player.turns_today = 0
    made = apply_action(u, "P1", Action(kind=ActionKind.DEPLOY_GENESIS, args={}))
    assert made.ok, made.error
    planet = next(pl for pl in u.planets.values() if pl.owner_id == player.id and pl.sector_id == deep)
    player.planet_landed = planet.id
    player.turns_today = 0
    while planet.id in u.planets:
        player.turns_today = 0
        player.ship.atomic_detonators = max(1, int(player.ship.atomic_detonators))
        res = apply_action(u, "P1", Action(kind=ActionKind.PLANET_DESTROY, args={"planet_id": planet.id}))
        assert res.ok, res.error
    return int(player.experience) - start


def _deep_sector(u) -> int:
    from tw2k.engine.runner import _bfs_path

    for sid in sorted(u.sectors):
        if sid in K.FEDSPACE_SECTORS or u.sectors[sid].planet_ids:
            continue
        path = _bfs_path(u, K.STARDOCK_SECTOR, sid)
        if path and len(path) >= K.GENESIS_MIN_HOPS_FROM_STARDOCK:
            return sid
    raise AssertionError("no sector far enough from StarDock")
