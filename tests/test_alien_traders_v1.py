"""alien-traders-v1: placement, hops, mines, and attack targets."""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, generate_universe
from tw2k.engine.alien import alien_day_step, place_aliens, population
from tw2k.engine.combat import _resolve_ship_attack_tw2002
from tw2k.engine.legality import legal_actions
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import apply_action
from tw2k.engine.scanners import density_reading, sector_view
from tw2k.engine.models import (
    FighterDeployment,
    FighterMode,
    MineDeployment,
    MineType,
    Player,
    Ship,
    ShipClass,
)


def test_al1_population_and_legacy_places_nobody(monkeypatch):
    u = generate_universe(GameConfig(seed=1, universe_size=1000, max_days=3))
    assert population(u) == 40
    before = u.rng.getstate()
    place_aliens(u)
    assert u.rng.getstate() == before
    assert len(u.aliens) == 40
    assert all(a.sector_id not in K.FEDSPACE_SECTORS for a in u.aliens.values())
    assert all(a.alive and a.id.startswith("alien:") for a in u.aliens.values())
    monkeypatch.setattr(K, "ALIEN_MODE", "legacy")
    bare = generate_universe(GameConfig(seed=1, universe_size=1000, max_days=3))
    place_aliens(bare)
    assert bare.aliens == {}


def test_al7_fighters_block_a_hop():
    u = generate_universe(GameConfig(seed=2, universe_size=200, max_days=3))
    place_aliens(u)
    alien = next(iter(u.aliens.values()))
    home = next(sid for sid, sector in u.sectors.items() if sector.warps and sid not in K.FEDSPACE_SECTORS)
    alien.sector_id = home
    for dest in u.sectors[home].warps:
        u.sectors[dest].fighters = FighterDeployment(owner_id="P9", count=1, mode=FighterMode.DEFENSIVE)
    alien_day_step(u)
    assert alien.sector_id == home and alien.alive


def test_al8_armids_can_destroy_and_pay_nothing():
    u = generate_universe(GameConfig(seed=3, universe_size=200, max_days=3))
    place_aliens(u)
    alien = next(iter(u.aliens.values()))
    home = next(
        sid for sid, sector in u.sectors.items()
        if sector.warps and sid not in K.FEDSPACE_SECTORS
    )
    dest = u.sectors[home].warps[0]
    alien.sector_id = home
    alien.ship.fighters = 1
    alien.ship.shields = 0
    for other in list(u.sectors[home].warps):
        if other != dest:
            u.sectors[other].fighters = FighterDeployment(owner_id="P9", count=1, mode=FighterMode.OFFENSIVE)
    u.sectors[dest].mines.append(MineDeployment(owner_id="P9", kind=MineType.ARMID, count=50))
    credits = {pid: player.credits for pid, player in u.players.items()}
    alien_day_step(u)
    assert not alien.alive
    assert all(u.players[pid].credits == credits[pid] for pid in credits)
    assert any(ev.kind.value == "ship_destroyed" and ev.payload.get("kind") == "alien" for ev in u.events)


def test_al10_legal_attack_lists_the_alien_in_the_sector():
    u = generate_universe(GameConfig(seed=5, universe_size=200, max_days=3))
    place_aliens(u)
    alien = next(iter(u.aliens.values()))
    alien.ship.fighters = 0
    alien.ship.shields = 0
    alien.ship.corbomite = 0
    player = Player(
        id="A", name="Ann",
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, fighters=400, shields=50),
        sector_id=alien.sector_id, credits=1_000, alignment=100, experience=0,
    )
    u.players["A"] = player
    u.sectors[alien.sector_id].occupant_ids.append("A")
    attack = next(row for row in legal_actions(u, player.id) if row.kind == ActionKind.ATTACK)
    assert alien.id in attack.params["target"]["choices"]
    result = apply_action(u, player.id, Action(kind=ActionKind.ATTACK, args={"target": alien.id, "qty": 1}))
    assert result.ok and not alien.alive


def test_al24_sector_view_lists_the_alien_hull():
    u = generate_universe(GameConfig(seed=6, universe_size=200, max_days=3))
    place_aliens(u)
    alien = next(iter(u.aliens.values()))
    player = Player(
        id="A", name="Ann",
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, fighters=10),
        sector_id=alien.sector_id, credits=1_000, alignment=100,
    )
    u.players["A"] = player
    u.sectors[alien.sector_id].occupant_ids.append("A")
    sector = build_observation(u, "A").sector
    row = next(item for item in sector["aliens"] if item["id"] == alien.id)
    assert row["hull"] == alien.ship.ship_class.value
    assert row["name"] == alien.name
    assert row["rank"] and row["side"] in ("good", "evil")
    hint = build_observation(u, "A").action_hint
    assert f"Alien trader {alien.name} ({row['rank']}, {row['side']}, {row['hull']}) is here." in hint
    assert "Aliens never attack" in hint
    assert "half its experience" in hint


def test_al23_alien_adds_ship_density_and_shows_on_a_scan():
    u = generate_universe(GameConfig(seed=7, universe_size=200, max_days=3))
    place_aliens(u)
    alien = next(iter(u.aliens.values()))
    sid = next(
        sector.id for sector in u.sectors.values()
        if sector.id not in K.FEDSPACE_SECTORS
        and not any(row.alive and row.sector_id == sector.id for row in u.aliens.values())
    )
    before = density_reading(u, sid)["density"]
    alien.sector_id = sid
    assert density_reading(u, sid)["density"] == before + K.DENSITY_PER_SHIP
    view = sector_view(u, "P1", sid)
    assert view["aliens"][0]["id"] == alien.id
    assert view["aliens"][0]["hull"] == alien.ship.ship_class.value


def test_al25_ranks_list_live_aliens_without_a_location(monkeypatch):
    u = generate_universe(GameConfig(seed=8, universe_size=200, max_days=3))
    player = Player(
        id="A", name="Ann",
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, fighters=10),
        sector_id=1, credits=1_000, alignment=100,
    )
    u.players["A"] = player
    u.sectors[1].occupant_ids.append("A")
    block = build_observation(u, "A").alien_ranks
    live = [alien for alien in u.aliens.values() if alien.alive]
    assert block["active"] == len(live)
    experiences = [row["experience"] for row in block["ranks"]]
    assert experiences == sorted(experiences, reverse=True)
    for row in block["ranks"]:
        assert set(row) == {"name", "rank", "side", "experience"}
    monkeypatch.setattr(K, "ALIEN_MODE", "legacy")
    bare = generate_universe(GameConfig(seed=8, universe_size=200, max_days=3))
    bare.players["A"] = player
    bare.sectors[1].occupant_ids.append("A")
    assert build_observation(bare, "A").alien_ranks is None


def test_al15_opposite_kill_pays_half_experience_and_the_credits():
    u = generate_universe(GameConfig(seed=4, universe_size=200, max_days=3))
    place_aliens(u)
    alien = next(iter(u.aliens.values()))
    alien.experience = 100
    alien.alignment = -200
    alien.credits = 5_000
    alien.ship.fighters = 0
    alien.ship.shields = 0
    alien.ship.corbomite = 0
    player = Player(
        id="A", name="Ann",
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, fighters=400, shields=50),
        sector_id=alien.sector_id, credits=1_000, alignment=100, experience=0,
    )
    u.players["A"] = player
    u.sectors[alien.sector_id].occupant_ids.append("A")
    _resolve_ship_attack_tw2002(u, "A", alien, 2)
    assert not alien.alive
    assert player.experience == 50
    assert player.alignment == 200
    assert player.credits == 6_000
    killed = next(ev for ev in u.events if ev.kind.value == "ship_destroyed" and ev.payload.get("victim") == alien.id)
    assert killed.payload["kind"] == "alien" and killed.payload["credits"] == 5_000


def test_al19_exact_minimum_captures_and_does_not_blast():
    u = generate_universe(GameConfig(seed=9, universe_size=200, max_days=3))
    alien = next(iter(u.aliens.values()))
    alien.experience = 80
    alien.alignment = -100
    alien.credits = 2_000
    alien.ship.fighters = 0
    alien.ship.shields = 0
    alien.ship.corbomite = 3
    player = Player(
        id="A", name="Ann",
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, fighters=400, shields=50),
        sector_id=alien.sector_id, credits=1_000, alignment=100, experience=0,
    )
    u.players["A"] = player
    u.sectors[alien.sector_id].occupant_ids.append("A")
    before = int(player.ship.fighters)
    _resolve_ship_attack_tw2002(u, "A", alien, 1)
    assert not alien.alive
    assert player.experience == 40
    assert player.credits == 3_000
    assert int(player.ship.fighters) == before
    parked = next(iter(u.parked_ships.values()))
    assert parked.owner_id == "A"
    assert parked.ship.ship_class == alien.ship.ship_class
    assert any(ev.kind.value == "alien_captured" for ev in u.events)
    assert not any(ev.kind.value == "corbomite_blast" for ev in u.events)
