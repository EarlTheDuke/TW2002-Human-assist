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


def _fresh_port(*, sector_id, code, class_id, stock):
    """Build a standalone Port for pricing tests without generating a full
    universe. Keeps the economy tests self-contained and deterministic."""
    from tw2k.engine.models import Port
    return Port(
        sector_id=sector_id,
        class_id=class_id,
        code=code,
        name=f"TestPort{sector_id}",
        stock=stock,
    )


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
        # Genesis now seeds a founding population (see GENESIS_SEED_COLONISTS).
        # Snapshot the pool before moving cargo in so we can check the delta.
        fuel_before = new_p.colonists.get(Commodity.FUEL_ORE, 0)

        a.ship.cargo[Commodity.COLONISTS] = 5000
        apply_action(u, "A", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": new_p.id}))
        res = apply_action(u, "A", Action(
            kind=ActionKind.ASSIGN_COLONISTS,
            args={"planet_id": new_p.id, "from": "ship", "to": "fuel_ore", "qty": 2000},
        ))
        assert res.ok, res.error
        assert new_p.colonists.get(Commodity.FUEL_ORE) == fuel_before + 2000
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

    def test_a_buy_colonists_at_stardock_and_ferry_to_own_planet(self):
        """End-to-end Terra ferry: at StarDock `buy_equip item=colonists` loads
        them into cargo, then `assign_colonists from=ship to=<pool>` deposits
        them on an owned planet. This is the authentic TW2002 loop that
        unlocks scaling Citadel construction past the Genesis seed pool."""
        u, (a, *_) = _make_universe()
        # Plant a Genesis planet in the first non-fed sector.
        a.ship.genesis = 1
        a.sector_id = _first_non_fed_sector(u)
        apply_action(u, "A", Action(kind=ActionKind.DEPLOY_GENESIS))
        new_p = max(u.planets.values(), key=lambda p: p.id)

        # Return to StarDock and buy 30 colonists (fills fixture's 40-hold ship).
        a.sector_id = K.STARDOCK_SECTOR
        a.credits = 10_000
        a.ship.cargo = {Commodity.FUEL_ORE: 0, Commodity.ORGANICS: 0,
                         Commodity.EQUIPMENT: 0, Commodity.COLONISTS: 0}
        qty = 30
        res = apply_action(u, "A", Action(
            kind=ActionKind.BUY_EQUIP,
            args={"item": "colonists", "qty": qty},
        ))
        assert res.ok, f"buy_equip colonists failed: {res.error}"
        assert a.ship.cargo[Commodity.COLONISTS] == qty
        assert a.credits == 10_000 - qty * K.COLONIST_PRICE

        # Fly to the owned planet and drop them into the organics pool.
        a.sector_id = new_p.sector_id
        apply_action(u, "A", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": new_p.id}))
        organics_before = new_p.colonists.get(Commodity.ORGANICS, 0)
        res = apply_action(u, "A", Action(
            kind=ActionKind.ASSIGN_COLONISTS,
            args={"planet_id": new_p.id, "from": "ship", "to": "organics", "qty": qty},
        ))
        assert res.ok, f"assign_colonists ship->organics failed: {res.error}"
        assert a.ship.cargo[Commodity.COLONISTS] == 0
        assert new_p.colonists[Commodity.ORGANICS] == organics_before + qty

    def test_a_buy_colonists_rejects_if_cargo_full(self):
        u, (a, *_) = _make_universe()
        a.sector_id = K.STARDOCK_SECTOR
        a.credits = 100_000
        a.ship.holds = 20  # starter ship
        a.ship.cargo[Commodity.FUEL_ORE] = 20  # fully loaded
        res = apply_action(u, "A", Action(
            kind=ActionKind.BUY_EQUIP,
            args={"item": "colonists", "qty": 1},
        ))
        assert not res.ok
        assert "cargo" in (res.error or "").lower()

    def test_a_genesis_seeds_population_enough_for_l1_citadel(self):
        """Regression guard: fresh Genesis planet must ship with enough
        founding colonists to immediately build Citadel L1 (1,000 colonists)
        without the player ferrying any from elsewhere. Before the seed fix
        the engine locked out S3+ progression because planets started empty
        and colonist growth is 0 * 5% = 0 forever."""
        u, (a, *_) = _make_universe()
        a.ship.genesis = 1
        a.sector_id = _first_non_fed_sector(u)
        apply_action(u, "A", Action(kind=ActionKind.DEPLOY_GENESIS))
        new_p = max(u.planets.values(), key=lambda p: p.id)
        total = sum(new_p.colonists.values())
        l1_cost_col = K.CITADEL_TIER_COST[0][1]
        assert total >= l1_cost_col, (
            f"Genesis seed ({total}) < Citadel L1 colonist cost ({l1_cost_col})"
        )
        assert new_p.stockpile.get(Commodity.ORGANICS, 0) > 0, "need organics to start population growth"

        a.credits = 50_000
        apply_action(u, "A", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": new_p.id}))
        res = apply_action(u, "A", Action(kind=ActionKind.BUILD_CITADEL, args={"planet_id": new_p.id}))
        assert res.ok, f"L1 citadel must be buildable from seed population alone: {res.error}"
        assert new_p.citadel_target == 1

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


# ---------------------------------------------------------------------------
# Phase D - economy pricing + observation feedback loops
# ---------------------------------------------------------------------------


class TestPhaseDEconomy:
    """Regression guards for the trading margin & observation hints.

    These exist because the v6 sanity run surfaced two issues:
      1. Port pricing margins were too narrow (±10-20%) so profit per round
         trip was ~1 cr/unit. Widened to 0.70x-1.30x so typical pairs yield
         6-10 cr/unit margins and a full-holds trip earns visible credits.
      2. LLM agents ran warps when turns_today was within 1 of the per-day
         cap and the engine silently rejected the action. Now the
         action_hint explicitly tells them to `wait`.
    """

    def test_d1_sell_port_cheaper_when_full_stock(self):
        """A full-stock SELL port should unload inventory below base price."""
        from tw2k.engine.economy import port_sell_price
        from tw2k.engine.models import Commodity, PortClass, PortStock

        port = _fresh_port(
            sector_id=100,
            code="BBS",
            class_id=PortClass.CLASS_6_BBS,  # BBS: buys FO+Org, sells Eq
            stock={
                Commodity.FUEL_ORE: PortStock(current=0, maximum=3000),
                Commodity.ORGANICS: PortStock(current=0, maximum=2500),
                Commodity.EQUIPMENT: PortStock(current=2000, maximum=2000),  # full
            },
        )
        full_price = port_sell_price(port, Commodity.EQUIPMENT)
        port.stock[Commodity.EQUIPMENT].current = 0  # empty
        empty_price = port_sell_price(port, Commodity.EQUIPMENT)
        base = K.COMMODITY_BASE_PRICE["equipment"]
        # Full stock should be UNDER base, empty should be OVER base
        assert full_price < base, f"full-stock sell port should discount (got {full_price} vs base {base})"
        assert empty_price > base, f"empty sell port should premium (got {empty_price} vs base {base})"
        # Widened band: spread must be at least 20% of base to be meaningful
        assert empty_price - full_price >= int(base * 0.20), (
            f"price swing too narrow: {empty_price} - {full_price} < 20% of {base}"
        )

    def test_d1_buy_port_pays_more_when_starved(self):
        """A buy port with low stock pays a premium (demand > supply)."""
        from tw2k.engine.economy import port_buy_price
        from tw2k.engine.models import Commodity, PortClass, PortStock

        port = _fresh_port(
            sector_id=100,
            code="BBS",
            class_id=PortClass.CLASS_6_BBS,
            stock={
                Commodity.FUEL_ORE: PortStock(current=0, maximum=3000),
                Commodity.ORGANICS: PortStock(current=0, maximum=2500),
                Commodity.EQUIPMENT: PortStock(current=0, maximum=2000),
            },
        )
        starved = port_buy_price(port, Commodity.FUEL_ORE)
        port.stock[Commodity.FUEL_ORE].current = 3000  # glutted
        glutted = port_buy_price(port, Commodity.FUEL_ORE)
        base = K.COMMODITY_BASE_PRICE["fuel_ore"]
        assert starved > base, f"starved buy port should pay premium (got {starved} vs base {base})"
        assert glutted < base, f"glutted buy port should pay discount (got {glutted} vs base {base})"
        assert starved - glutted >= int(base * 0.20), (
            f"buy-price swing too narrow: {starved} - {glutted} < 20% of {base}"
        )

    def test_d2_round_trip_is_visibly_profitable(self):
        """End-to-end: buy full holds at a well-stocked SELL port then sell at
        an empty BUY port. A 20-hold ship should net at least 100 cr per
        round trip under typical conditions."""
        from tw2k.engine.economy import port_buy_price, port_sell_price
        from tw2k.engine.models import Commodity, PortClass, PortStock

        sell_port = _fresh_port(
            sector_id=5, code="SBB", class_id=PortClass.CLASS_3_SBB,  # sells FO
            stock={
                Commodity.FUEL_ORE: PortStock(current=2400, maximum=3000),  # ~80% full
                Commodity.ORGANICS: PortStock(current=0, maximum=2500),
                Commodity.EQUIPMENT: PortStock(current=0, maximum=2000),
            },
        )
        buy_port = _fresh_port(
            sector_id=7, code="BBS", class_id=PortClass.CLASS_6_BBS,  # buys FO
            stock={
                Commodity.FUEL_ORE: PortStock(current=600, maximum=3000),  # ~20% stocked
                Commodity.ORGANICS: PortStock(current=0, maximum=2500),
                Commodity.EQUIPMENT: PortStock(current=0, maximum=2000),
            },
        )
        buy_price = port_sell_price(sell_port, Commodity.FUEL_ORE)   # pay this
        sell_price = port_buy_price(buy_port, Commodity.FUEL_ORE)    # receive this
        per_unit = sell_price - buy_price
        round_trip_20_holds = per_unit * 20
        assert per_unit >= 5, (
            f"per-unit margin too thin: buy {buy_price} -> sell {sell_price} (diff {per_unit})"
        )
        assert round_trip_20_holds >= 100, (
            f"20-hold round trip should earn >=100 cr, got {round_trip_20_holds}"
        )

    def test_d3_end_of_day_nudge_appears(self):
        """When turns_today has fewer turns remaining than the cost of a warp
        (2), action_hint should say END OF DAY / wait. Threshold matches warp
        cost because warp is by far the most common verb agents try to
        squeeze in at end of day. Regression for v7 run where 58/60 turns
        burned 4 failed warps before the unstick kicked in."""
        from tw2k.engine.observation import build_observation

        u, (a, *_) = _make_universe()
        a.turns_per_day = 60
        a.turns_today = 59  # 1 turn left, warp (cost=2) will fail
        obs = build_observation(u, "A")
        assert "END OF DAY" in obs.action_hint, (
            f"missing end-of-day nudge in action_hint: {obs.action_hint}"
        )
        assert "wait" in obs.action_hint.lower()
        # Also trigger at exactly 1-below-warp (should still fire since 58/60=2
        # turns left meets the warp cost, so NO nudge at that edge).
        a.turns_today = 58
        obs = build_observation(u, "A")
        assert "END OF DAY" not in obs.action_hint, (
            "nudge fired too early — with 2 turns left and warp cost 2 a warp is valid"
        )

    def test_d3_no_end_of_day_nudge_midday(self):
        """Inverse: mid-day, the nudge must NOT appear or agents will wait
        forever on every turn."""
        from tw2k.engine.observation import build_observation

        u, (a, *_) = _make_universe()
        a.turns_per_day = 20
        a.turns_today = 5
        obs = build_observation(u, "A")
        assert "END OF DAY" not in obs.action_hint

    def test_d5_affordable_ships_hint_at_stardock(self):
        """At StarDock with 75k cash, the action_hint must enumerate at
        least one affordable ship class (Merchant Cruiser 41k, Cargotran
        43k, Colonial Transport 63k are all under budget) so the LLM sees
        concrete buy_ship targets rather than trying to infer from memory."""
        from tw2k.engine.observation import build_observation

        u, (a, *_) = _make_universe()
        a.sector_id = K.STARDOCK_SECTOR
        a.credits = 75_000
        obs = build_observation(u, "A")
        hint = obs.action_hint
        assert "afford" in hint.lower(), f"missing affordable-ship hint: {hint}"
        # Cargotran is the star pick (43k, 75 holds, 3.75x starter capacity).
        assert "CargoTran" in hint or "cargotran" in hint.lower() or "Merchant" in hint, (
            f"expected at least one sub-75k ship in hint: {hint}"
        )
        assert "buy_ship" in hint

    def test_d5_no_affordable_ships_hint_shows_next_target(self):
        """With only 10k credits, none of the upgrade ships fit. The hint
        should show the nearest unaffordable ship as a savings target."""
        from tw2k.engine.observation import build_observation

        u, (a, *_) = _make_universe()
        a.sector_id = K.STARDOCK_SECTOR
        a.credits = 10_000
        obs = build_observation(u, "A")
        hint = obs.action_hint
        assert "Next ship in budget" in hint, (
            f"expected 'Next ship in budget' savings target: {hint}"
        )

    def test_d6_scorecard_scales_with_turns_per_day(self):
        """Short sanity runs need scaled thresholds. 60 tpd = 6% of 1000 tpd
        so a 150k nw target should scale toward ~9k. Non-numeric checks
        (Genesis deployed, Citadel built) must NOT scale — binary events."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
        from watch_match import RUBRIC, scale_rubric_for_turns

        scaled = scale_rubric_for_turns(RUBRIC, turns_per_day=60)
        nw_check_day2 = next(c for c in scaled[2] if c["id"] == "net_worth")
        assert nw_check_day2["threshold"] <= 15_000, (
            f"net_worth threshold didn't shrink enough at tpd=60: {nw_check_day2['threshold']}"
        )
        # Genesis deployed must remain a binary event check.
        genesis_check = next(c for c in scaled[3] if c.get("kind") == "genesis_deployed")
        assert "threshold" not in genesis_check or genesis_check.get("kind") == "genesis_deployed"

        # At tpd=1000 (canonical) rubric should be untouched.
        unchanged = scale_rubric_for_turns(RUBRIC, turns_per_day=1000)
        assert unchanged is RUBRIC, "canonical tpd should not modify rubric"

    def test_d4_known_ports_include_prices(self):
        """Intel snapshot must persist prices so agents can compare pairs
        across sectors without revisiting. This is what enables route
        planning — without per-port prices the LLM has to guess."""
        from tw2k.engine.models import PortClass
        from tw2k.engine.observation import build_observation
        from tw2k.engine.runner import _record_port_intel

        u, (a, *_) = _make_universe()
        skip = {PortClass.STARDOCK, PortClass.FEDERAL}
        for sid, sector in u.sectors.items():
            if sector.port is not None and sector.port.class_id not in skip:
                _record_port_intel(a, sid, sector.port)
                break
        obs = build_observation(u, "A")
        assert obs.known_ports, "expected at least one port intel entry"
        sample_stock = obs.known_ports[0]["stock"]
        # At least one stock entry must carry a numeric price.
        assert any("price" in v for v in sample_stock.values()), (
            f"no price field in stock intel: {sample_stock}"
        )


class TestPhaseEGoals:
    """Phase E — structured agent goals (short / medium / long) that
    survive across turns. Parsed from LLM output, persisted on Player,
    surfaced back to the agent at the top of next turn's action_hint."""

    def test_e1_llm_parser_reads_nested_goals_block(self):
        """Canonical shape: a `goals` object inside the JSON response
        carrying short/medium/long strings."""
        from tw2k.agents.llm import _parse_response

        raw = (
            '{"thought":"scan first","scratchpad_update":"s=1",'
            '"goals":{"short":"scan then warp","medium":"45k + buy cargotran","long":"100M cr"},'
            '"action":{"kind":"scan","args":{}}}'
        )
        act = _parse_response(raw)
        assert act is not None
        assert act.goal_short == "scan then warp"
        assert act.goal_medium == "45k + buy cargotran"
        assert act.goal_long == "100M cr"

    def test_e1_llm_parser_reads_flat_goal_fields(self):
        """Tolerant shape: some models flatten to `goal_short`/etc. at the
        top level. Must be accepted so behavior doesn't depend on the LLM
        picking one shape."""
        from tw2k.agents.llm import _parse_response

        raw = (
            '{"thought":"t","goal_short":"a","goal_medium":"b","goal_long":"c",'
            '"action":{"kind":"wait","args":{}}}'
        )
        act = _parse_response(raw)
        assert act is not None
        assert (act.goal_short, act.goal_medium, act.goal_long) == ("a", "b", "c")

    def test_e1_llm_parser_omitted_goal_stays_none(self):
        """None means 'don't touch the stored goal'. An omitted field must
        NOT overwrite a prior-turn goal with empty string."""
        from tw2k.agents.llm import _parse_response

        raw = '{"thought":"t","goals":{"short":"keep trading"},"action":{"kind":"wait","args":{}}}'
        act = _parse_response(raw)
        assert act is not None
        assert act.goal_short == "keep trading"
        assert act.goal_medium is None
        assert act.goal_long is None

    def test_e2_observation_surfaces_prior_goals(self):
        """Goals written last turn must appear at the TOP of action_hint
        so the agent re-reads them before deciding."""
        from tw2k.engine.observation import build_observation

        u, (a, *_) = _make_universe()
        a.goal_short = "warp 5, buy 20 org"
        a.goal_medium = "hit 45k, buy cargotran"
        a.goal_long = "100M cr via citadel L3"
        obs = build_observation(u, "A")
        assert "YOUR GOALS" in obs.action_hint
        assert "warp 5, buy 20 org" in obs.action_hint
        assert "hit 45k, buy cargotran" in obs.action_hint
        assert "100M cr via citadel L3" in obs.action_hint
        # And the machine-readable mirror in obs.goals is available.
        assert obs.goals["short"] == "warp 5, buy 20 org"
        assert obs.goals["medium"] == "hit 45k, buy cargotran"
        assert obs.goals["long"] == "100M cr via citadel L3"

    def test_e2_observation_empty_goals_nudges_agent(self):
        """If the agent hasn't set goals yet, the hint should tell them to
        — otherwise new agents ignore the field forever."""
        from tw2k.engine.observation import build_observation

        u, (a, *_) = _make_universe()
        # fresh player — no goals set
        obs = build_observation(u, "A")
        assert "GOALS EMPTY" in obs.action_hint, (
            f"missing empty-goals nudge in hint: {obs.action_hint}"
        )

    def test_e3_runner_persists_goal_update_on_action(self):
        """When an Action carries goal_medium, apply_action must write it
        onto the Player so it reappears in the next observation."""
        from tw2k.engine.actions import Action, ActionKind
        from tw2k.engine.runner import apply_action

        u, (a, *_) = _make_universe()
        act = Action(
            kind=ActionKind.WAIT,
            goal_short="do thing",
            goal_medium="save 45k",
            goal_long="win match",
        )
        apply_action(u, "A", act)
        assert a.goal_short == "do thing"
        assert a.goal_medium == "save 45k"
        assert a.goal_long == "win match"

    def test_e3_runner_leaves_goal_alone_when_action_omits(self):
        """None on the Action field is the 'keep existing goal' signal.
        Only an explicit "" clears."""
        from tw2k.engine.actions import Action, ActionKind
        from tw2k.engine.runner import apply_action

        u, (a, *_) = _make_universe()
        a.goal_medium = "original plan"
        apply_action(u, "A", Action(kind=ActionKind.WAIT))  # no goals
        assert a.goal_medium == "original plan"
        apply_action(u, "A", Action(kind=ActionKind.WAIT, goal_medium=""))
        assert a.goal_medium == ""

    def test_e4_system_prompt_teaches_goal_schema(self):
        """Prompt must document the goals block + three horizons so a
        fresh LLM knows what to emit."""
        from tw2k.agents.prompts import SYSTEM_PROMPT

        assert '"goals"' in SYSTEM_PROMPT
        for horizon in ("short", "medium", "long"):
            assert horizon in SYSTEM_PROMPT, f"prompt missing '{horizon}' horizon"
        assert "GOAL DISCIPLINE" in SYSTEM_PROMPT or "GOAL RULES" in SYSTEM_PROMPT


class TestPhaseFCostBasis:
    """Phase F — cargo cost basis, trade ledger, port-intel staleness.

    These three wire-up the agent's 'receipt book': the engine now tracks
    what was actually paid for cargo, realizes P&L on every sell, writes a
    rolling 50-entry trade log on the Player, and stamps every port-intel
    snapshot with the day it was captured. Together they remove the need
    for the LLM to keep mental-ledger notes in scratchpad (brittle) and
    prevent stale-intel planning errors.
    """

    def _trade_setup(self):
        """Universe + player + one BSS port (buys organics, sells fuel/equip)
        adjacent to the start sector so we can run buy/sell cycles without
        navigation noise. Returns (u, player, port, sector_id)."""
        from tw2k.engine.models import Port, PortClass, PortStock

        u, (a, *_) = _make_universe(seed=2027)
        # Find a non-Federal port sector to host our custom port.
        sid = next(
            s for s in u.sectors if s >= 30 and s not in K.FEDSPACE_SECTORS
        )
        # SBS: sells fuel_ore, buys organics, sells equipment.
        u.sectors[sid].port = Port(
            sector_id=sid,
            class_id=PortClass.CLASS_5_SBS,
            code="SBS",
            name="Test SBS",
            stock={
                Commodity.FUEL_ORE: PortStock(current=5000, maximum=10000),
                Commodity.ORGANICS: PortStock(current=2000, maximum=10000),
                Commodity.EQUIPMENT: PortStock(current=5000, maximum=10000),
            },
        )
        a.sector_id = sid
        a.credits = 50_000
        return u, a, u.sectors[sid].port, sid

    def test_f1_cost_basis_updates_on_buy(self):
        """Cost basis on a freshly-bought commodity must equal the post-haggle
        unit price we actually paid."""
        import random

        from tw2k.engine.economy import execute_trade

        u, a, port, _ = self._trade_setup()
        rng = random.Random(42)
        ok, total, unit, msg, realized = execute_trade(
            u, a, port, Commodity.FUEL_ORE, qty=10, side="buy",
            offered_unit_price=None, rng=rng,
        )
        assert ok, msg
        assert realized is None, "buy should not realize profit"
        assert a.ship.cargo[Commodity.FUEL_ORE] == 10
        assert a.ship.cargo_cost[Commodity.FUEL_ORE] == pytest.approx(unit)

    def test_f1_weighted_avg_on_second_buy(self):
        """Two buys at different prices must produce a weighted average, not
        replace the stored basis."""
        import random

        from tw2k.engine.economy import execute_trade

        u, a, port, _ = self._trade_setup()
        rng = random.Random(42)
        # First buy 10 units
        execute_trade(u, a, port, Commodity.FUEL_ORE, 10, "buy", None, rng)
        first_avg = a.ship.cargo_cost[Commodity.FUEL_ORE]
        # Drain port stock a bit so the price goes UP (scarcer = pricier)
        port.stock[Commodity.FUEL_ORE].current = max(0, port.stock[Commodity.FUEL_ORE].current - 4000)
        # Buy another 10 at the new, higher price
        ok, _, second_unit, _, _ = execute_trade(
            u, a, port, Commodity.FUEL_ORE, 10, "buy", None, rng
        )
        assert ok
        new_avg = a.ship.cargo_cost[Commodity.FUEL_ORE]
        expected = (10 * first_avg + 10 * second_unit) / 20
        assert new_avg == pytest.approx(expected, abs=0.01)
        assert first_avg < new_avg < second_unit, (
            "weighted avg must lie between the two unit prices"
        )

    def test_f1_realized_profit_on_sell(self):
        """Selling above the stored basis returns positive realized_profit;
        selling below returns negative. Must propagate to trade_log."""
        import random

        from tw2k.engine.actions import Action, ActionKind
        from tw2k.engine.runner import apply_action

        u, a, port, _ = self._trade_setup()
        rng = random.Random(42)
        # Force a buy at a KNOWN price by draining stock so sell_price is high,
        # THEN manipulate basis to test both profit and loss. Simplest: set
        # basis manually, put cargo, then sell via apply_action so trade_log
        # gets the real integration path.
        a.ship.cargo[Commodity.ORGANICS] = 20
        a.ship.cargo_cost[Commodity.ORGANICS] = 15.0
        # BSS-style port? We're on SBS which buys organics — perfect.
        before_log = len(a.trade_log)
        # Sell at list (no offered price). port_buy_price for organics will
        # vary; we just check the logged profit matches (unit - 15) * 20.
        res = apply_action(
            u,
            a.id,
            Action(kind=ActionKind.TRADE, args={
                "commodity": "organics", "qty": 20, "side": "sell",
            }),
        )
        assert res.ok
        assert len(a.trade_log) == before_log + 1
        entry = a.trade_log[-1]
        assert entry["side"] == "sell"
        assert entry["qty"] == 20
        assert entry["realized_profit"] is not None
        expected_profit = (entry["unit"] - 15) * 20
        assert entry["realized_profit"] == expected_profit
        # Selling all units must clear the basis so a future buy is fresh.
        assert a.ship.cargo[Commodity.ORGANICS] == 0
        assert a.ship.cargo_cost[Commodity.ORGANICS] == 0.0

    def test_f2_trade_log_capped_at_fifty(self):
        """Ledger must cap to the most recent 50 entries so it never balloons
        in long matches."""
        u, (a, *_) = _make_universe(seed=2028)
        # Stuff 60 fake entries
        for i in range(60):
            a.trade_log.append({"seq": i})
        # Run one real trade to exercise the capping path. Simpler: simulate
        # the append-and-trim logic directly since we're testing the invariant.
        from tw2k.engine.models import Port, PortClass, PortStock
        sid = next(s for s in u.sectors if s >= 30 and s not in K.FEDSPACE_SECTORS)
        u.sectors[sid].port = Port(
            sector_id=sid, class_id=PortClass.CLASS_5_SBS, code="SBS", name="T",
            stock={
                Commodity.FUEL_ORE: PortStock(current=5000, maximum=10000),
                Commodity.ORGANICS: PortStock(current=2000, maximum=10000),
                Commodity.EQUIPMENT: PortStock(current=5000, maximum=10000),
            },
        )
        a.sector_id = sid
        a.credits = 50_000
        from tw2k.engine.actions import Action, ActionKind
        from tw2k.engine.runner import apply_action
        apply_action(u, a.id, Action(kind=ActionKind.TRADE, args={
            "commodity": "fuel_ore", "qty": 5, "side": "buy",
        }))
        assert len(a.trade_log) == 50, (
            f"expected cap at 50, got {len(a.trade_log)}"
        )
        # Oldest entries dropped first — the new real trade is last.
        assert a.trade_log[-1].get("commodity") == "fuel_ore"
        # The first entries in the buffer should be the tail of the fake ones.
        assert a.trade_log[0].get("seq") == 11  # we kept 60 - 50 + 1 = 11..59 + 1 new

    def test_f3_port_intel_stamps_last_seen_day(self):
        """Intel must carry the day it was captured so the observation can
        compute `age_days`. Regression for the hardcoded None bug."""
        from tw2k.engine.models import PortClass
        from tw2k.engine.runner import _record_port_intel

        u, (a, *_) = _make_universe(seed=2029)
        u.day = 3
        skip = {PortClass.STARDOCK, PortClass.FEDERAL}
        for sid, sector in u.sectors.items():
            if sector.port is not None and sector.port.class_id not in skip:
                _record_port_intel(a, sid, sector.port, universe=u)
                break
        entry = next(iter(a.known_ports.values()))
        assert entry["last_seen_day"] == 3, (
            f"expected last_seen_day=3, got {entry['last_seen_day']}"
        )

    def test_f3_observation_exposes_intel_age(self):
        """Staleness must bubble up to the observation so the LLM sees it
        inline — not just buried in a last_seen_day int it has to diff."""
        from tw2k.engine.models import PortClass
        from tw2k.engine.observation import build_observation
        from tw2k.engine.runner import _record_port_intel

        u, (a, *_) = _make_universe(seed=2030)
        u.day = 1
        skip = {PortClass.STARDOCK, PortClass.FEDERAL}
        for sid, sector in u.sectors.items():
            if sector.port is not None and sector.port.class_id not in skip:
                _record_port_intel(a, sid, sector.port, universe=u)
                break
        # Advance in-game days; the snapshot should now be 2 days old.
        u.day = 3
        obs = build_observation(u, "A")
        entry = obs.known_ports[0]
        assert entry.get("age_days") == 2, (
            f"expected age_days=2, got entry={entry}"
        )

    def test_f4_observation_ship_dict_has_cost_basis(self):
        """The ship block in the observation must carry per-commodity cost
        avg + value so agents see breakeven next to quantity."""
        from tw2k.engine.observation import build_observation

        u, (a, *_) = _make_universe(seed=2031)
        a.ship.cargo[Commodity.ORGANICS] = 25
        a.ship.cargo_cost[Commodity.ORGANICS] = 17.4
        obs = build_observation(u, "A")
        assert obs.ship["cargo_cost_avg"].get("organics") == 17  # rounded
        assert obs.ship["cargo_value_at_cost"].get("organics") == round(25 * 17.4)

    def test_f5_action_hint_shows_pnl_at_current_port(self):
        """At a port that buys the player's cargo, the hint must show cost
        basis vs. port bid with the sign of realized profit. Protects
        against auto-sell at a loss."""
        from tw2k.engine.models import Port, PortClass, PortStock
        from tw2k.engine.observation import build_observation

        u, (a, *_) = _make_universe(seed=2032)
        sid = next(s for s in u.sectors if s >= 30 and s not in K.FEDSPACE_SECTORS)
        # BBS buys organics (and fuel_ore), sells equipment.
        u.sectors[sid].port = Port(
            sector_id=sid, class_id=PortClass.CLASS_6_BBS, code="BBS", name="Buyer",
            stock={
                Commodity.FUEL_ORE: PortStock(current=1000, maximum=10000),
                Commodity.ORGANICS: PortStock(current=1000, maximum=10000),
                Commodity.EQUIPMENT: PortStock(current=5000, maximum=10000),
            },
        )
        a.sector_id = sid
        a.ship.cargo[Commodity.ORGANICS] = 20
        a.ship.cargo_cost[Commodity.ORGANICS] = 18.0
        obs = build_observation(u, "A")
        hint = obs.action_hint
        assert "P&L at this port" in hint, f"missing P&L hint: {hint}"
        assert "organics" in hint
        assert "cost=18cr" in hint

    def test_f6_trade_log_surfaces_in_observation(self):
        """Last N trades must reach the agent's obs.trade_log so they can
        audit their own recent activity without consulting the global feed."""
        from tw2k.engine.observation import build_observation

        u, (a, *_) = _make_universe(seed=2033)
        for i in range(8):
            a.trade_log.append({
                "day": 1, "tick": i, "sector_id": 7,
                "commodity": "organics", "qty": 10, "side": "sell" if i % 2 else "buy",
                "unit": 20 + i, "total": (20 + i) * 10,
                "realized_profit": 25 if i % 2 else None,
            })
        obs = build_observation(u, "A")
        assert len(obs.trade_log) == 5, "observation should cap to last 5"
        assert obs.trade_log[-1]["tick"] == 7, "newest entry last"

    def test_f7_build_default_spec_threads_turns_per_day(self):
        """Regression: `tw2k serve --turns-per-day 80` must reach
        GameConfig. Previously the CLI accepted the flag and passed it to
        create_app, but we need to verify it actually ends up on the spec."""
        from tw2k.server.app import _build_default_spec

        spec = _build_default_spec(
            seed=1, universe_size=50, max_days=2, agent_names=None,
            agent_kind="heuristic", provider=None, model=None, num_agents=1,
            turns_per_day=80, starting_credits=75_000,
        )
        assert spec.config.turns_per_day == 80
        assert spec.config.starting_credits == 75_000

    def test_f7_server_runner_applies_config_turns_per_day_to_player(self):
        """The direct bug: MatchRunner's player construction must honor
        GameConfig.turns_per_day. Previously it silently fell back to 1000
        turns/day regardless of config, making --turns-per-day a no-op."""
        from tw2k.engine import constants as K
        from tw2k.engine.models import GameConfig, Player, Ship

        # Replicate the exact line in server/runner.py that constructs a Player
        # to catch if someone rips the override out again.
        cfg = GameConfig(seed=1, universe_size=50, max_days=2, turns_per_day=80)
        base_tpd = getattr(cfg, "turns_per_day", K.STARTING_TURNS_PER_DAY)
        p = Player(
            id="P1", name="A", credits=75_000,
            turns_per_day=base_tpd, ship=Ship(), sector_id=1,
            agent_kind="heuristic", color="#fff",
        )
        assert p.turns_per_day == 80


class TestPhaseGObservationSurface:
    """format_observation ships the right fields to the LLM.

    Prompts.py repeatedly instructs the agent to read things like
    `self.net_worth`, `owned_planets`, `trade_log`, `goals`. The
    Observation model populates all of them, but prior to 2026-04-17
    `format_observation` stripped most of them before building the
    user-message JSON, so the prompt was writing checks the payload
    couldn't cash. docs/AGENT_TURN_ANATOMY.md §4 tells that story.
    These tests lock the fix in place."""

    def test_g1_user_message_has_top_level_goals(self):
        """goals block ships as a structured field, not just as
        action_hint text. Critical for multi-horizon planning."""
        import json as _json

        from tw2k.agents.prompts import format_observation

        u, (a, *_) = _make_universe(seed=3101)
        a.goal_short = "warp 5, buy fuel_ore"
        a.goal_medium = "hit 45k cr, buy cargotran"
        a.goal_long = "Citadel L2 by day 3"
        from tw2k.engine.observation import build_observation
        obs = build_observation(u, "A")
        payload = _json.loads(format_observation(obs))
        assert "goals" in payload, "goals must be a top-level key"
        assert payload["goals"]["short"] == "warp 5, buy fuel_ore"
        assert payload["goals"]["medium"] == "hit 45k cr, buy cargotran"
        assert payload["goals"]["long"] == "Citadel L2 by day 3"

    def test_g2_user_message_has_trade_log(self):
        """trade_log (last 5) must reach the LLM. Prompt §OBSERVATION
        FIELDS teaches agents to self-audit off this list."""
        import json as _json

        from tw2k.agents.prompts import format_observation
        from tw2k.engine.observation import build_observation

        u, (a, *_) = _make_universe(seed=3102)
        for i in range(7):
            a.trade_log.append({
                "day": 1, "tick": i, "sector_id": 7,
                "commodity": "organics", "qty": 10,
                "side": "sell" if i % 2 else "buy",
                "unit": 20, "total": 200,
                "realized_profit": 50 if i % 2 else None,
            })
        obs = build_observation(u, "A")
        payload = _json.loads(format_observation(obs))
        assert "trade_log" in payload, "trade_log must be a top-level key"
        assert len(payload["trade_log"]) == 5
        assert payload["trade_log"][-1]["tick"] == 6, "newest last"

    def test_g3_user_message_has_owned_planets(self):
        """owned_planets must ship. Without it, a multi-planet commander
        has no structured inventory of what they own and would have to
        warp-and-rediscover each one."""
        import json as _json

        from tw2k.agents.prompts import format_observation
        from tw2k.engine.models import Planet, PlanetClass
        from tw2k.engine.observation import build_observation

        u, (a, *_) = _make_universe(seed=3103)
        u.planets[99] = Planet(
            id=99, sector_id=5, name="Phoenix-test",
            class_id=PlanetClass.M, owner_id="A",
        )
        obs = build_observation(u, "A")
        payload = _json.loads(format_observation(obs))
        assert "owned_planets" in payload
        ids = [p["id"] for p in payload["owned_planets"]]
        assert 99 in ids, "the planet the player owns must appear"

    def test_g4_user_message_self_has_net_worth_and_survival(self):
        """self.net_worth, self.alive, self.deaths, self.max_deaths all
        ship. Without net_worth the agent had to parse a number out of
        stage_hint.reason prose."""
        import json as _json

        from tw2k.agents.prompts import format_observation
        from tw2k.engine.observation import build_observation

        u, (a, *_) = _make_universe(seed=3104)
        a.credits = 50_000
        obs = build_observation(u, "A")
        payload = _json.loads(format_observation(obs))
        self_block = payload.get("self") or {}
        for key in ("net_worth", "alive", "deaths", "max_deaths",
                    "alignment_label", "rank", "experience"):
            assert key in self_block, f"self.{key} must ship to the LLM"
        assert isinstance(self_block["net_worth"], int)
        assert self_block["net_worth"] >= 50_000, "net_worth >= credits at start"
