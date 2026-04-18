"""Pytest suite covering Phase A/B/C features.

Complements `scripts/smoke_phase_abc.py` — the latter prints a pretty report,
this file lets CI treat each check as a proper unit test.
"""

from __future__ import annotations

import pytest

from tw2k.engine import (
    Action,
    ActionKind,
    GameConfig,
    apply_action,
    generate_universe,
    tick_day,
)
from tw2k.engine import constants as K
from tw2k.engine.models import (
    Commodity,
    FerrengiShip,
    MineDeployment,
    MineType,
    Player,
    Ship,
)
from tw2k.engine.runner import _destroy_ship, alignment_label, rank_for

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_universe(seed: int = 2026, size: int = 200, players: int = 3):
    """Build a universe with N players stacked in sector 1 with generous kits."""
    cfg = GameConfig(seed=seed, universe_size=size, max_days=10, planet_spawn_probability=0.06)
    u = generate_universe(cfg)
    names = ["Alice", "Bob", "Carol", "Dave"][:players]
    pids = ["A", "B", "C", "D"][:players]
    ps = []
    for pid, name in zip(pids, names, strict=True):
        p = Player(id=pid, name=name, ship=Ship(holds=40, fighters=200, shields=100), sector_id=1)
        u.players[pid] = p
        u.sectors[1].occupant_ids.append(pid)
        p.known_sectors.add(1)
        ps.append(p)
    return u, ps


def _first_non_fed_sector(u, min_id: int = 30) -> int:
    return next(sid for sid in u.sectors if sid >= min_id and sid not in K.FEDSPACE_SECTORS)


# ---------------------------------------------------------------------------
# Phase A
# ---------------------------------------------------------------------------


class TestPhaseA:
    def test_a5_per_ship_warp_turn_cost(self):
        u, (a, *_) = _make_universe()
        target = u.sectors[1].warps[0]
        res = apply_action(u, "A", Action(kind=ActionKind.WARP, args={"target": target}))
        assert res.ok, res.error
        assert a.turns_today == 3  # Merchant Cruiser default

    def test_a3_deploy_genesis_creates_planet(self):
        u, (a, *_) = _make_universe()
        a.ship.genesis = 1
        a.sector_id = _first_non_fed_sector(u)
        pre = len(u.planets)
        res = apply_action(u, "A", Action(kind=ActionKind.DEPLOY_GENESIS))
        assert res.ok, res.error
        assert len(u.planets) == pre + 1
        assert a.ship.genesis == 0
        new_p = max(u.planets.values(), key=lambda p: p.id)
        assert new_p.owner_id == "A"
        assert new_p.sector_id == a.sector_id

    def test_a1_assign_colonists_to_commodity(self):
        u, (a, *_) = _make_universe()
        a.ship.genesis = 1
        a.sector_id = _first_non_fed_sector(u)
        apply_action(u, "A", Action(kind=ActionKind.DEPLOY_GENESIS))
        new_p = max(u.planets.values(), key=lambda p: p.id)

        a.ship.cargo[Commodity.COLONISTS] = 5000
        apply_action(u, "A", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": new_p.id}))
        res = apply_action(u, "A", Action(
            kind=ActionKind.ASSIGN_COLONISTS,
            args={"planet_id": new_p.id, "from": "ship", "to": "fuel_ore", "qty": 2000},
        ))
        assert res.ok, res.error
        assert new_p.colonists.get(Commodity.FUEL_ORE) == 2000
        assert a.ship.cargo[Commodity.COLONISTS] == 3000

    def test_a2_build_citadel_completes_after_days(self):
        u, (a, *_) = _make_universe()
        a.ship.genesis = 1
        a.sector_id = _first_non_fed_sector(u)
        apply_action(u, "A", Action(kind=ActionKind.DEPLOY_GENESIS))
        new_p = max(u.planets.values(), key=lambda p: p.id)
        a.ship.cargo[Commodity.COLONISTS] = 5000
        apply_action(u, "A", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": new_p.id}))
        apply_action(u, "A", Action(
            kind=ActionKind.ASSIGN_COLONISTS,
            args={"planet_id": new_p.id, "from": "ship", "to": "colonists", "qty": 3000},
        ))
        a.credits = 200_000
        res = apply_action(u, "A", Action(kind=ActionKind.BUILD_CITADEL, args={"planet_id": new_p.id}))
        assert res.ok, res.error
        assert new_p.citadel_target == 1
        assert new_p.citadel_level == 0
        for _ in range(5):
            tick_day(u)
        assert new_p.citadel_level == 1

    def test_a4_player_eliminated_after_max_deaths(self):
        u, (a, *_) = _make_universe()
        a.alive = True
        a.deaths = 0
        for _ in range(K.MAX_DEATHS_BEFORE_ELIM):
            _destroy_ship(u, "A", reason="test")
        assert not a.alive
        assert a.deaths >= K.MAX_DEATHS_BEFORE_ELIM

    def test_a6_ferrengi_roam_and_hunt(self):
        u, (a, b, c) = _make_universe()
        far_sid = _first_non_fed_sector(u, min_id=50)
        b.sector_id = far_sid
        u.sectors[1].occupant_ids = [x for x in u.sectors[1].occupant_ids if x != "B"]
        u.sectors[far_sid].occupant_ids.append("B")
        pre_fighters = b.ship.fighters
        hit = False
        for _ in range(10):
            u.ferrengi.clear()
            u.ferrengi["ferr_test"] = FerrengiShip(
                id="ferr_test", name="Test Raider", sector_id=b.sector_id,
                aggression=9, fighters=400, shields=200,
            )
            tick_day(u)
            if b.ship.fighters < pre_fighters or not b.alive:
                hit = True
                break
        assert hit


# ---------------------------------------------------------------------------
# Phase B
# ---------------------------------------------------------------------------


class TestPhaseB:
    def test_b1_plot_course_previews_and_executes(self):
        u, (a, b, *_) = _make_universe()
        target = next(sid for sid in u.sectors if sid > 100)
        b.turns_today = 0
        # Preview
        res = apply_action(u, "B", Action(kind=ActionKind.PLOT_COURSE, args={"target": target}))
        assert res.ok, res.error
        # Execute
        res = apply_action(u, "B", Action(
            kind=ActionKind.PLOT_COURSE, args={"target": target, "execute": True}
        ))
        assert res.ok, res.error
        assert b.sector_id != 1

    def test_b2_photon_missile_disables_target_fighters(self):
        u, (a, b, c) = _make_universe()
        sid = _first_non_fed_sector(u, min_id=50)
        b.sector_id = sid
        c.sector_id = sid
        u.sectors[1].occupant_ids = []
        u.sectors[sid].occupant_ids.extend(["B", "C"])
        b.ship.photon_missiles = 1
        b.turns_today = 0
        res = apply_action(u, "B", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": "C"}))
        assert res.ok, res.error
        assert c.ship.photon_disabled_ticks > 0
        assert b.ship.photon_missiles == 0

    def test_b3_atomic_mine_detonates_and_hits_alignment(self):
        u, (a, b, *_) = _make_universe()
        sid = _first_non_fed_sector(u, min_id=50)
        b.sector_id = sid
        b.ship.mines[MineType.ATOMIC] = 3
        pre_align = b.alignment
        b.turns_today = 0
        res = apply_action(u, "B", Action(
            kind=ActionKind.DEPLOY_MINES, args={"kind": "atomic", "qty": 1}
        ))
        assert res.ok, res.error
        assert b.alignment < pre_align

    def test_b4_limpet_attaches_and_reports(self):
        u, (a, b, c) = _make_universe()
        sid_l = _first_non_fed_sector(u, min_id=60)
        inbound = next((s.id for s in u.sectors.values() if sid_l in s.warps and s.id != sid_l), None)
        if inbound is None:
            pytest.skip("no neighbor warps into chosen sector")
        u.sectors[sid_l].mines.append(MineDeployment(owner_id="B", kind=MineType.LIMPET, count=2))
        c.sector_id = inbound
        u.sectors[1].occupant_ids = [x for x in u.sectors[1].occupant_ids if x != "C"]
        u.sectors[inbound].occupant_ids.append("C")
        c.turns_today = 0
        res = apply_action(u, "C", Action(kind=ActionKind.WARP, args={"target": sid_l}))
        assert res.ok, res.error
        assert any(lt.target_id == "C" for lt in u.limpets.values())
        b.turns_today = 0
        res = apply_action(u, "B", Action(kind=ActionKind.QUERY_LIMPETS))
        assert res.ok, res.error


# ---------------------------------------------------------------------------
# Phase C
# ---------------------------------------------------------------------------


class TestPhaseC:
    def test_c1_alliance_propose_and_accept(self):
        u, (a, b, c) = _make_universe()
        b.turns_today = 0
        c.turns_today = 0
        res = apply_action(u, "B", Action(
            kind=ActionKind.PROPOSE_ALLIANCE, args={"target": "C", "terms": "test pact"}
        ))
        assert res.ok, res.error
        assert len(u.alliances) == 1
        aid = next(iter(u.alliances))
        assert not u.alliances[aid].active
        res = apply_action(u, "C", Action(
            kind=ActionKind.ACCEPT_ALLIANCE, args={"alliance_id": aid}
        ))
        assert res.ok, res.error
        assert u.alliances[aid].active
        assert aid in b.alliances
        assert aid in c.alliances

    def test_c1_allies_cannot_attack_each_other(self):
        u, (a, b, c) = _make_universe()
        apply_action(u, "B", Action(
            kind=ActionKind.PROPOSE_ALLIANCE, args={"target": "C", "terms": "nap"}
        ))
        aid = next(iter(u.alliances))
        apply_action(u, "C", Action(kind=ActionKind.ACCEPT_ALLIANCE, args={"alliance_id": aid}))
        sid = _first_non_fed_sector(u, min_id=50)
        b.sector_id = sid
        c.sector_id = sid
        u.sectors[1].occupant_ids = []
        u.sectors[sid].occupant_ids.extend(["B", "C"])
        b.turns_today = 0
        res = apply_action(u, "B", Action(kind=ActionKind.ATTACK, args={"target": "C"}))
        assert not res.ok

    def test_c3_corp_deposit_withdraw_treasury(self):
        u, (a, *_) = _make_universe()
        a.sector_id = K.STARDOCK_SECTOR
        a.credits = 1_000_000
        a.turns_today = 0
        res = apply_action(u, "A", Action(
            kind=ActionKind.CORP_CREATE, args={"ticker": "ZZZ", "name": "Zog"}
        ))
        assert res.ok, res.error
        res = apply_action(u, "A", Action(
            kind=ActionKind.CORP_DEPOSIT, args={"amount": 200_000}
        ))
        assert res.ok, res.error
        assert u.corporations["ZZZ"].treasury == 200_000
        res = apply_action(u, "A", Action(
            kind=ActionKind.CORP_WITHDRAW, args={"amount": 50_000}
        ))
        assert res.ok, res.error
        assert u.corporations["ZZZ"].treasury == 150_000

    def test_c6_alignment_label_and_rank_scale(self):
        # Labels must partition monotonically: worse alignment -> "lower" tier.
        labels = [alignment_label(v) for v in [-5000, -500, -100, 0, 200, 1000, 5000]]
        # All should be strings and partition (at least 4 distinct tiers across the range)
        assert all(isinstance(l, str) and l for l in labels)
        assert len(set(labels)) >= 4
        # Neutral region
        assert alignment_label(0) == "Neutral"
        # Rank climbs with XP
        r_low = rank_for(0)
        r_high = rank_for(10_000_000)
        assert isinstance(r_low, str) and isinstance(r_high, str)
        assert r_low != r_high

    def test_c2_probe_action_exists(self):
        """Sanity: ether-probe action runs without raising when stock exists."""
        u, (a, *_) = _make_universe()
        a.ship.ether_probes = 2
        a.turns_today = 0
        # Pick a known sector, any warp-adjacent
        target = u.sectors[1].warps[0]
        res = apply_action(u, "A", Action(kind=ActionKind.PROBE, args={"target": target}))
        assert res.ok, res.error
        assert a.ship.ether_probes == 1
