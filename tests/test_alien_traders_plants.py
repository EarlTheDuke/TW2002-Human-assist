"""One check per planted bug in alien-traders-v1. Each fails if that bug is put back."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, generate_universe
from tw2k.engine.alien import (
    _spawn,
    alien_day_step,
    alien_flee_destination,
    alien_rng,
    place_aliens,
    population,
)
from tw2k.engine.combat import _resolve_ship_attack_tw2002, combat_odds_of
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import (
    Commodity,
    EventKind,
    FighterDeployment,
    FighterMode,
    MineDeployment,
    MineType,
    ParkedShip,
    Player,
    Ship,
    ShipClass,
)
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import apply_action
from tw2k.engine.scanners import density_reading

_FORBIDDEN = {
    "imperial_starship", "corporate_flagship", "interdictor_cruiser", "tholian_sentinel",
    "star_master", "tkhasi_orion", "taurean_mule", "escape_pod",
}


def _u(seed: int = 20):
    return generate_universe(GameConfig(
        seed=seed, universe_size=200, max_days=3, enable_ferrengi=False,
    ))


def _seat(u, pid="A", sector=1, fighters=400, align=100, exp=0, credits=1_000):
    player = Player(
        id=pid, name=pid,
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, fighters=fighters, shields=100),
        sector_id=sector, credits=credits, alignment=align, experience=exp,
    )
    u.players[pid] = player
    if pid not in u.sectors[sector].occupant_ids:
        u.sectors[sector].occupant_ids.append(pid)
    return player


def _open_sector(u):
    return next(
        sid for sid, sector in u.sectors.items()
        if sector.warps and sid not in K.FEDSPACE_SECTORS
    )


def _block(u, sid: int, owner: str = "P9", ticker: str | None = None) -> None:
    dep = FighterDeployment(owner_id=owner, count=1, mode=FighterMode.DEFENSIVE)
    if ticker is not None:
        dep.corp_ticker = ticker
    u.sectors[sid].fighters = dep


def test_pb2_corporate_and_rogue_fighters_block_a_hop():
    u = _u(31)
    alien = next(iter(u.aliens.values()))
    home = _open_sector(u)
    alien.sector_id = home
    for dest in u.sectors[home].warps:
        _block(u, dest, owner="P2", ticker="ZZ")
    alien_day_step(u)
    assert alien.sector_id == home
    for dest in u.sectors[home].warps:
        _block(u, dest, owner=K.ROGUE_OWNER_ID)
    alien_day_step(u)
    assert alien.sector_id == home


def test_pb3_ferrengi_fighters_block_a_hop():
    u = _u(32)
    alien = next(iter(u.aliens.values()))
    home = _open_sector(u)
    alien.sector_id = home
    for dest in u.sectors[home].warps:
        _block(u, dest, owner=K.FERRENGI_OWNER_ID)
    alien_day_step(u)
    assert alien.sector_id == home and alien.alive


def test_pb5_fighters_in_its_own_sector_do_not_hold_it():
    u = _u(33)
    alien = next(iter(u.aliens.values()))
    home = _open_sector(u)
    dest = u.sectors[home].warps[0]
    alien.sector_id = home
    _block(u, home, owner="P9")
    for other in u.sectors[home].warps:
        if other != dest:
            _block(u, other)
        else:
            u.sectors[other].fighters = None
            u.sectors[other].mines.clear()
    alien_day_step(u)
    assert alien.sector_id != home


def test_pb6_day_step_does_not_draw_the_universe_rng():
    u = _u(34)
    before = u.rng.getstate()
    alien_day_step(u)
    assert u.rng.getstate() == before


def test_pb7_replacement_spawns_at_stardock_and_the_count_holds():
    u = _u(35)
    want = population(u)
    victim = next(iter(u.aliens.values()))
    victim.alive = False
    before = set(u.aliens)
    alien_day_step(u)
    live = [alien for alien in u.aliens.values() if alien.alive]
    assert len(live) == want
    spawned = [ev for ev in u.events if ev.kind == EventKind.ALIEN_SPAWN and ev.payload.get("id") not in before]
    assert spawned and all(ev.sector_id == K.STARDOCK_SECTOR for ev in spawned)


def test_pb8_day_400_stays_inside_the_hull_caps():
    u = _u(36)
    u.day = 400
    u.aliens.clear()
    u.next_alien_id = 1
    place_aliens(u)
    assert len(u.aliens) == population(u)
    for alien in u.aliens.values():
        spec = K.hull_spec(alien.ship.ship_class.value)
        assert alien.ship.ship_class.value not in _FORBIDDEN
        assert int(alien.ship.fighters) <= int(spec["max_fighters"])
        assert int(alien.ship.shields) <= int(spec["max_shields"])
        assert int(alien.experience) <= int(K.ALIEN_EXP_CAP)
        assert int(alien.credits) <= int(K.ALIEN_CREDITS_CAP)
        assert int(alien.ship.corbomite) <= int(K.ALIEN_CORBOMITE_MAX)


def test_pb9_spawns_are_not_all_good():
    u = _u(37)
    u.aliens.clear()
    u.next_alien_id = 1
    rng = alien_rng(u.config.seed, u.day, 99)
    for _ in range(200):
        _spawn(u, 20, rng)
    goods = sum(1 for alien in u.aliens.values() if int(alien.alignment) > 0)
    assert 60 < goods < 140


def test_pb10_flee_keeps_the_fighters_it_lost():
    u = _u(38)
    alien = next(iter(u.aliens.values()))
    home = _open_sector(u)
    dest = u.sectors[home].warps[0]
    alien.sector_id = home
    alien.ship.fighters = 30
    alien.ship.shields = 0
    alien.ship.corbomite = 0
    for other in u.sectors[home].warps:
        if other != dest:
            _block(u, other)
        else:
            u.sectors[other].fighters = None
    player = _seat(u, sector=home, fighters=2_000)
    _resolve_ship_attack_tw2002(u, player.id, alien, 10)
    assert alien.alive and alien.sector_id == dest
    assert int(alien.ship.fighters) == 20


def test_pb11_flee_skips_fighter_sectors_and_an_interdictor_holds():
    u = _u(39)
    alien = next(iter(u.aliens.values()))
    home = _open_sector(u)
    alien.sector_id = home
    for dest in u.sectors[home].warps:
        _block(u, dest)
    assert alien_flee_destination(u, alien) is None
    planet = next(pl for pl in u.planets.values() if pl.sector_id not in K.FEDSPACE_SECTORS)
    alien.sector_id = planet.sector_id
    for dest in u.sectors[planet.sector_id].warps:
        u.sectors[dest].fighters = None
    planet.owner_id = "P9"
    planet.citadel_level = int(K.INTERDICTOR_MIN_LEVEL)
    planet.stockpile[Commodity.FUEL_ORE] = int(K.INTERDICTOR_FUEL)
    assert alien_flee_destination(u, alien) is None


def test_pb12_odds_are_the_alien_hull_not_a_merchant():
    u = _u(40)
    alien = next(iter(u.aliens.values()))
    alien.ship.ship_class = ShipClass.BATTLESHIP
    assert combat_odds_of(alien) == K.combat_hull("battleship")[0] or float(combat_odds_of(alien)) == 1.6
    assert float(combat_odds_of(alien)) != 1.0


def test_pb16_an_alien_kill_pays_no_bounty():
    u = _u(41)
    alien = next(iter(u.aliens.values()))
    alien.experience = 40
    alien.alignment = -80
    alien.credits = 100
    alien.ship.fighters = alien.ship.shields = alien.ship.corbomite = 0
    player = _seat(u, sector=alien.sector_id)
    ferr_credits = {fid: int(row.credits) for fid, row in u.ferrengi.items()}
    _resolve_ship_attack_tw2002(u, player.id, alien, 1)
    assert {fid: int(row.credits) for fid, row in u.ferrengi.items()} == ferr_credits
    killed = next(ev for ev in u.events if ev.kind == EventKind.SHIP_DESTROYED and ev.payload.get("victim") == alien.id)
    assert "bounty" not in killed.payload


def test_pb18_aliens_do_not_start_combat():
    u = _u(42)
    assert K.ALIEN_AGGRESSION == "never"
    alien_day_step(u)
    assert not any(
        ev.kind == EventKind.COMBAT and str(ev.actor_id).startswith("alien:")
        for ev in u.events
    )


def test_pb19_a_full_fleet_destroys_instead_of_capturing():
    u = _u(43)
    alien = next(iter(u.aliens.values()))
    alien.experience = 20
    alien.alignment = -40
    alien.credits = 0
    alien.ship.fighters = alien.ship.shields = 0
    alien.ship.corbomite = 2
    player = _seat(u, sector=alien.sector_id, fighters=400)
    for n in range(4):
        u.parked_ships[9000 + n] = ParkedShip(
            id=9000 + n, owner_id="A", sector_id=1,
            ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER), parked_day=1,
        )
    _resolve_ship_attack_tw2002(u, player.id, alien, 1)
    assert not alien.alive
    assert not any(rec.captured_from == alien.name for rec in u.parked_ships.values())
    assert any(ev.kind == EventKind.CORBOMITE_BLAST for ev in u.events)
    assert player.ship.ship_class != ShipClass.ESCAPE_POD


def test_pb20_a_mine_death_does_not_blast_corbomite():
    u = _u(44)
    alien = next(iter(u.aliens.values()))
    home = _open_sector(u)
    dest = u.sectors[home].warps[0]
    alien.sector_id = home
    alien.ship.fighters = 1
    alien.ship.shields = 0
    alien.ship.corbomite = 5
    for other in u.sectors[home].warps:
        if other != dest:
            _block(u, other)
    u.sectors[dest].mines.append(MineDeployment(owner_id="P9", kind=MineType.ARMID, count=50))
    before = int(u.sectors[dest].mines[0].count)
    alien_day_step(u)
    assert not alien.alive
    assert int(u.sectors[dest].mines[0].count) < before
    assert not any(ev.kind == EventKind.CORBOMITE_BLAST for ev in u.events)


def test_pb21_a_mine_death_pays_the_owner_nothing():
    u = _u(45)
    alien = next(iter(u.aliens.values()))
    home = _open_sector(u)
    dest = u.sectors[home].warps[0]
    alien.sector_id = home
    alien.ship.fighters = 1
    alien.ship.shields = 0
    for other in u.sectors[home].warps:
        if other != dest:
            _block(u, other)
    u.sectors[dest].mines.append(MineDeployment(owner_id="P9", kind=MineType.ARMID, count=40))
    owner = _seat(u, pid="P9", sector=1, credits=7_000)
    alien_day_step(u)
    assert not alien.alive and owner.credits == 7_000


def test_pb22_an_alien_is_not_an_occupant_and_cannot_be_hailed():
    u = _u(46)
    alien = next(iter(u.aliens.values()))
    assert alien.id not in u.players
    assert all(alien.id not in sector.occupant_ids for sector in u.sectors.values())
    player = _seat(u, sector=alien.sector_id)
    result = apply_action(u, player.id, Action(kind=ActionKind.HAIL, args={"target": alien.id, "message": "hi"}))
    assert not result.ok


def test_pb25_legacy_dump_omits_the_empty_alien_record(monkeypatch):
    monkeypatch.setattr(K, "ALIEN_MODE", "legacy")
    u = generate_universe(GameConfig(seed=47, universe_size=80, max_days=2, enable_ferrengi=False))
    dumped = u.model_dump()
    assert "aliens" not in dumped and "next_alien_id" not in dumped
    assert not any(ev.kind.value.startswith("alien_") for ev in u.events)


def test_pb28_a_non_witness_does_not_see_the_alien_flee():
    u = _u(48)
    alien = next(iter(u.aliens.values()))
    home = _open_sector(u)
    dest = u.sectors[home].warps[0]
    alien.sector_id = home
    alien.ship.fighters = 30
    alien.ship.shields = 0
    alien.ship.corbomite = 0
    for other in u.sectors[home].warps:
        if other != dest:
            _block(u, other)
        else:
            u.sectors[other].fighters = None
    _seat(u, pid="A", sector=home, fighters=2_000)
    away = next(sid for sid in u.sectors if sid != home)
    _seat(u, pid="B", sector=away, fighters=10)
    _resolve_ship_attack_tw2002(u, "A", alien, 10)
    seen = {row["kind"] for row in build_observation(u, "B").recent_events}
    assert "alien_fled" not in seen
    assert "alien_fled" in {row["kind"] for row in build_observation(u, "A").recent_events}


def test_al28_save_round_trip_keeps_every_alien_field():
    u = _u(49)
    alien = next(iter(u.aliens.values()))
    restored = type(u).model_validate(u.model_dump())
    again = restored.aliens[alien.id]
    assert again.name == alien.name
    assert again.sector_id == alien.sector_id
    assert int(again.experience) == int(alien.experience)
    assert int(again.credits) == int(alien.credits)
    assert again.ship.ship_class == alien.ship.ship_class


def test_al31_the_handler_takes_every_listed_alien():
    u = _u(50)
    alien = next(iter(u.aliens.values()))
    alien.ship.fighters = alien.ship.shields = alien.ship.corbomite = 0
    _seat(u, sector=alien.sector_id, fighters=400)
    attack = next(row for row in legal_actions(u, "A") if row.kind == ActionKind.ATTACK)
    assert alien.id in attack.params["target"]["choices"]
    result = apply_action(u, "A", Action(kind=ActionKind.ATTACK, args={"target": alien.id, "qty": 1}))
    assert result.ok


def test_scenario_lab_e_passes():
    path = Path(__file__).resolve().parents[1] / "scripts" / "alien_traders_scenario_lab.py"
    spec = importlib.util.spec_from_file_location("alien_traders_scenario_lab", path)
    lab = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lab)
    out = lab.main()
    assert out["bible_exp"] == 200 and out["bible_align"] == 125 and out["loot"] == 5_000


def test_pb23_density_is_forty_not_zero(monkeypatch):
    u = _u(51)
    alien = next(iter(u.aliens.values()))
    sid = next(
        sector.id for sector in u.sectors.values()
        if not any(row.alive and row.sector_id == sector.id for row in u.aliens.values())
    )
    before = density_reading(u, sid)["density"]
    alien.sector_id = sid
    assert density_reading(u, sid)["density"] - before == 40
    monkeypatch.setattr(K, "DENSITY_PER_SHIP", 40)
