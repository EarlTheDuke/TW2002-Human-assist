"""alien-traders-v1: placement, hops, and mines. Combat is a later pass."""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.alien import alien_day_step, place_aliens, population
from tw2k.engine.models import FighterDeployment, FighterMode, MineDeployment, MineType


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
