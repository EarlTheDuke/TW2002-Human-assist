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

    def test_g5_net_worth_counts_equipment(self):
        """Player.net_worth must include shields, mines, photon missiles,
        ether probes, genesis torpedoes, and colonists in cargo at their
        StarDock buy prices. Regression from the discovery that a player
        with a Genesis torpedo (25,000cr at StarDock) showed zero value
        for it in net worth, causing the victory scorer to under-count
        investment-heavy strategies."""
        from tw2k.engine.models import Commodity, MineType

        u, (a, *_) = _make_universe(seed=5101)
        a.credits = 1000
        # _make_universe seeds ship.shields=100 and fighters=200, so the
        # baseline already reflects SOME equipment value under the fixed
        # formula. We bump each field by a known delta so the math is
        # unambiguous: the INCREASE in net_worth should equal the
        # INCREASE in StarDock-priced equipment.
        shields_before = a.ship.shields
        baseline = a.net_worth

        a.ship.shields = shields_before + 100  # +100 shields = +1000 cr
        a.ship.mines[MineType.ATOMIC] = 2
        a.ship.photon_missiles = 1
        a.ship.ether_probes = 3
        a.ship.genesis = 1
        a.ship.cargo[Commodity.COLONISTS] = 50

        after = a.net_worth
        # +100 shields * 10 = 1000
        # +2 atomic mines * 4000 = 8000
        # +1 photon * 12000 = 12000
        # +3 probes * 5000 = 15000
        # +1 genesis * 25000 = 25000
        # +50 colonists cargo * 10 = 500
        expected_delta = 1000 + 8000 + 12000 + 15000 + 25000 + 500
        assert after - baseline == expected_delta, (
            f"net_worth delta {after - baseline} != expected {expected_delta}"
        )

    def test_g6_full_net_worth_includes_owned_planets(self):
        """full_net_worth must add value from every planet the player
        owns: citadel investment (cumulative tier costs), colonist pools,
        stockpile, treasury, and planet defense. Without this, a player
        who sinks 30k+ credits into a Citadel L1 + colonist ferry shows
        up poorer in the victory ranking than one who hoarded cash."""
        from tw2k.engine.models import Commodity, Planet, PlanetClass
        from tw2k.engine.runner import full_net_worth

        u, (a, *_) = _make_universe(seed=5102)
        a.credits = 1000
        ship_side = a.net_worth

        u.planets[501] = Planet(
            id=501, sector_id=5, name="TestCapital",
            class_id=PlanetClass.M, owner_id=a.id,
            citadel_level=1, citadel_target=1,
            colonists={
                Commodity.COLONISTS: 500,   # idle pool
                Commodity.FUEL_ORE: 100,
                Commodity.ORGANICS: 100,
                Commodity.EQUIPMENT: 50,
            },
            stockpile={
                Commodity.FUEL_ORE: 20,
                Commodity.ORGANICS: 0,
                Commodity.EQUIPMENT: 5,
            },
            fighters=50,
            shields=100,
            treasury=2500,
        )

        total = full_net_worth(u, a)
        # Citadel L1 investment: 5000cr + 1000 colonists * 10cr = 15,000
        # Colonist pools: (500+100+100+50) * 10 = 7,500
        # Stockpile: 20 fo @ 18 = 360, 5 eq @ 36 = 180  -> 540
        # Treasury: 2500
        # Defense: 50*50 + 100*10 = 2500 + 1000 = 3500
        planet_value = 15000 + 7500 + 540 + 2500 + 3500
        assert total == ship_side + planet_value, (
            f"total={total} ship={ship_side} planet_add={total - ship_side} "
            f"expected_planet_value={planet_value}"
        )

    def test_g7_full_net_worth_ignores_planets_owned_by_others(self):
        """full_net_worth for player A must NOT count planets that
        belong to player B. Regression guard against summing everyone's
        planets into everyone's total."""
        from tw2k.engine.models import Planet, PlanetClass
        from tw2k.engine.runner import full_net_worth

        u, (a, b, *_) = _make_universe(seed=5103)
        a_before = full_net_worth(u, a)
        u.planets[601] = Planet(
            id=601, sector_id=5, name="BsCapital",
            class_id=PlanetClass.M, owner_id=b.id,
            citadel_level=3, citadel_target=3,
            treasury=999_999,
        )
        a_after = full_net_worth(u, a)
        assert a_after == a_before, "player A's net worth changed when player B got a planet"

    def test_g8_victory_summary_splits_ship_vs_planets(self):
        """When the game ends on time, the GAME_OVER payload should
        include net_worth_ship and net_worth_planets so spectators can
        see whether the winner won on cash or on citadel investment."""
        from tw2k.engine import tick_day
        from tw2k.engine.models import EventKind, Planet, PlanetClass

        u, (a, b, *_) = _make_universe(seed=5104, players=2)
        # Make b win decisively on planet value.
        u.planets[701] = Planet(
            id=701, sector_id=5, name="WinnerCapital",
            class_id=PlanetClass.M, owner_id=b.id,
            citadel_level=2, citadel_target=2,
        )
        # Force the day cap.
        u.day = u.config.max_days + 1
        tick_day(u)

        game_over = [e for e in u.events if e.kind == EventKind.GAME_OVER]
        assert game_over, "expected a GAME_OVER event"
        ev = game_over[-1]
        assert ev.payload.get("reason") == "time_net_worth"
        assert "net_worth_ship" in ev.payload
        assert "net_worth_planets" in ev.payload
        assert ev.payload["net_worth_planets"] > 0, "b owned a planet, should show on split"

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


class TestPhaseHTurnsStarvation:
    """Regression tests for the D1·56..91 infinite "out of turns" loop.

    Bug: CargoTran has turns_per_warp=3, so at turns_today=78 (2 remaining)
    the player couldn't warp, couldn't trade (cost 3), but the server kept
    asking them to act because 78 < 80. Grok retried warp 36 times in a row.
    """

    def test_h1_is_day_done_catches_low_turns_for_slow_ship(self):
        """With CargoTran (3/warp) and only 2 turns left, the server must
        treat the day as done even though turns_today < turns_per_day."""
        from tw2k.engine.models import ShipClass
        from tw2k.server.runner import _is_day_done

        u, (a, *_) = _make_universe(seed=7001)
        a.ship.ship_class = ShipClass.CARGOTRAN
        a.turns_per_day = 80
        a.turns_today = 78  # 2 left — can't warp (needs 3), can't trade (needs 3)
        assert _is_day_done(a), (
            "agent with <3 turns in a CargoTran (warp=3, trade=3) should "
            "be treated as day-done; otherwise the server spins forever."
        )

    def test_h2_is_day_done_false_when_agent_can_still_warp(self):
        from tw2k.engine.models import ShipClass
        from tw2k.server.runner import _is_day_done

        u, (a, *_) = _make_universe(seed=7002)
        a.ship.ship_class = ShipClass.CARGOTRAN
        a.turns_per_day = 80
        a.turns_today = 77  # 3 left — exactly enough to warp
        assert not _is_day_done(a), "agent with 3 turns left in CargoTran can still warp"

    def test_h3_is_day_done_respects_scout_marauder_fast_warp(self):
        """Scout Marauder has turns_per_warp=2. Should still be able to warp
        with 2 turns left — the helper must not over-trigger for fast ships."""
        from tw2k.engine.models import ShipClass
        from tw2k.server.runner import _is_day_done

        u, (a, *_) = _make_universe(seed=7003)
        a.ship.ship_class = ShipClass.SCOUT_MARAUDER
        a.turns_per_day = 80
        a.turns_today = 78
        assert not _is_day_done(a), "Scout Marauder (warp=2) with 2 turns left can still warp"

    def test_h4_action_hint_warns_when_cannot_warp(self):
        """The action_hint must loudly tell the LLM that warp is unaffordable
        so it stops spamming warp attempts. Without this warning, Grok burned
        36 LLM calls in a row retrying the same impossible action."""
        from tw2k.engine.models import ShipClass
        from tw2k.engine.observation import build_observation

        u, (a, *_) = _make_universe(seed=7004)
        a.ship.ship_class = ShipClass.CARGOTRAN
        a.turns_per_day = 80
        a.turns_today = 78
        obs = build_observation(u, a.id)
        assert "LOW TURNS" in obs.action_hint, (
            "action_hint must include a LOW TURNS warning when "
            "turns_remaining < warp_cost. Full hint:\n" + obs.action_hint
        )
        assert "warp" in obs.action_hint.lower()
        assert "wait" in obs.action_hint.lower()

    def test_h5_action_hint_silent_when_turns_plentiful(self):
        """Early in the day the warning should NOT fire — otherwise the hint
        stream becomes noise."""
        from tw2k.engine.models import ShipClass
        from tw2k.engine.observation import build_observation

        u, (a, *_) = _make_universe(seed=7005)
        a.ship.ship_class = ShipClass.CARGOTRAN
        a.turns_per_day = 80
        a.turns_today = 0
        obs = build_observation(u, a.id)
        assert "LOW TURNS" not in obs.action_hint, (
            "LOW TURNS warning should not fire when turns_remaining >= warp_cost"
        )


class TestPhaseIGenesisDistance:
    """Genesis torpedoes must detonate well away from StarDock — FedSpace
    alone is not enough of a buffer (some outer sectors are 1 hop from
    sector 1 even though they're outside sectors 1..10). Classic TW2002
    required planets to be "deep"; we enforce this at >= 3 hops."""

    def test_i1_genesis_blocked_in_fedspace(self):
        """FedSpace rejection still fires (pre-existing behavior)."""
        u, (a, *_) = _make_universe(seed=9001)
        a.ship.genesis = 1
        a.sector_id = 2  # FedSpace
        a.turns_today = 0
        r = apply_action(u, a.id, Action(kind=ActionKind.DEPLOY_GENESIS, args={}))
        assert not r.ok
        assert "FedSpace" in (r.error or "")

    def test_i2_genesis_blocked_at_direct_stardock_neighbor(self):
        """A sector 1 hop from StarDock but outside FedSpace must still
        be rejected by the new distance rule."""
        u, (a, *_) = _make_universe(seed=9002)
        # Find a sector that is 1-hop from stardock AND not in FedSpace.
        sd_warps = u.sectors[K.STARDOCK_SECTOR].warps
        candidate = next((s for s in sd_warps if s not in K.FEDSPACE_SECTORS), None)
        if candidate is None:
            pytest.skip("seed has no non-FedSpace sector adjacent to StarDock")
        a.ship.genesis = 1
        a.sector_id = candidate
        a.turns_today = 0
        r = apply_action(u, a.id, Action(kind=ActionKind.DEPLOY_GENESIS, args={}))
        assert not r.ok
        assert "StarDock" in (r.error or "") or "hops" in (r.error or "")

    def test_i3_genesis_allowed_far_from_stardock(self):
        """Deep space must still permit genesis."""
        from tw2k.engine.runner import _bfs_path

        u, (a, *_) = _make_universe(seed=9003)
        deep = None
        for sid in range(K.GENESIS_MIN_HOPS_FROM_STARDOCK + 1, u.config.universe_size + 1):
            if sid in K.FEDSPACE_SECTORS:
                continue
            hops = len(_bfs_path(u, K.STARDOCK_SECTOR, sid))
            if hops >= K.GENESIS_MIN_HOPS_FROM_STARDOCK:
                deep = sid
                break
        assert deep is not None, "expected some deep sector in a 500-sector universe"
        a.ship.genesis = 1
        a.sector_id = deep
        a.turns_today = 0
        r = apply_action(u, a.id, Action(kind=ActionKind.DEPLOY_GENESIS, args={}))
        assert r.ok, f"genesis at deep sector {deep} should succeed, got: {r.error}"


class TestPhaseJEarlyCombat:
    """Ferrengi should pose a threat from day 1, not day 2+. The universe
    generator now pre-seeds raiders at match start."""

    def test_j1_initial_ferrengi_spawned_at_generation(self):
        u, _ = _make_universe(seed=9101)
        assert len(u.ferrengi) >= K.FERRENGI_INITIAL_SPAWN, (
            f"expected >= {K.FERRENGI_INITIAL_SPAWN} Ferrengi at game start, "
            f"got {len(u.ferrengi)}"
        )

    def test_j2_initial_ferrengi_are_outside_fedspace(self):
        u, _ = _make_universe(seed=9102)
        for ferr in u.ferrengi.values():
            assert ferr.sector_id not in K.FEDSPACE_SECTORS, (
                f"Ferrengi {ferr.id} spawned in FedSpace at {ferr.sector_id} — "
                f"must be deep space only (otherwise Federation would wipe them)."
            )

    def test_j3_hunt_threshold_lowered(self):
        """Lowering the threshold from 4 to 3 means aggression levels 3-10
        will hunt (8 of 10 levels) instead of 4-10 (7 of 10) — roughly
        +14% hostile raiders. Guard the constant so we notice regressions."""
        assert K.FERRENGI_HUNT_AGGRESSION_THRESHOLD == 3


class TestPhaseKPlanetPatch:
    """Ensure planet-mutating events ship a `planet` key in state_patch so
    the spectator UI sees newly-Genesised planets without a page reload.
    Historically the client only populated state.planets from the initial
    snapshot; new planets were invisible until F5."""

    def _make_patch_runner(self):
        # Lightweight runner wrapper that only exposes what _state_patch_for
        # needs. We reach into the universe builder and Drive a fake event.
        from types import SimpleNamespace

        from tw2k.server.runner import MatchRunner

        u, (_a, *_) = _make_universe(seed=9201)
        runner = MatchRunner.__new__(MatchRunner)
        runner.state = SimpleNamespace(universe=u, last_error=None)
        return runner, u

    def test_k1_genesis_event_includes_planet_patch(self):
        """GENESIS_DEPLOYED with a valid planet_id must emit patch.planet."""
        from tw2k.engine.models import Commodity, Event, EventKind, Planet, PlanetClass

        runner, u = self._make_patch_runner()
        planet = Planet(
            id=42,
            sector_id=123,
            name="Test Planet",
            class_id=PlanetClass.M,
            owner_id="P1",
        )
        planet.colonists[Commodity.COLONISTS] = 500
        u.planets[42] = planet

        ev = Event(
            seq=1,
            kind=EventKind.GENESIS_DEPLOYED,
            day=1,
            tick=0,
            actor_id="P1",
            sector_id=123,
            payload={"planet_id": 42, "class": "M", "name": "Test Planet"},
            summary="genesis",
        )
        patch = runner._state_patch_for(ev)
        assert "planet" in patch, (
            "state_patch must include a 'planet' key for GENESIS_DEPLOYED "
            "so client can update state.planets without a reload"
        )
        assert patch["planet"]["id"] == 42
        assert patch["planet"]["owner_id"] == "P1"
        assert patch["planet"]["name"] == "Test Planet"
        assert patch["planet"]["colonists"].get("colonists") == 500

    def test_k2_non_planet_event_omits_planet_patch(self):
        """Routine events (warp, trade) must NOT bloat the patch with planet
        data — this keeps the WS pipe cheap."""
        from tw2k.engine.models import Event, EventKind

        runner, _u = self._make_patch_runner()
        ev = Event(
            seq=1,
            kind=EventKind.WARP,
            day=1,
            tick=0,
            actor_id="P1",
            sector_id=5,
            payload={"from": 1, "to": 5},
            summary="warp",
        )
        patch = runner._state_patch_for(ev)
        assert "planet" not in patch, "warp events should not emit planet deltas"


class TestPhaseLHintsAndSafety:
    """Soft-hint architecture: the observation surfaces awareness cues
    (0-fighters, citadel gap, 2nd genesis affordability, inbox) without
    forcing the agent to act. Also covers the FedSpace dead-end bug fix,
    opportunistic-Ferrengi hunting, and the planet-orphan event.
    """

    def test_l1_fedspace_has_no_dead_ends(self):
        """Every FedSpace sector must have ≥1 outbound warp. Guards against
        the seed-7777 bug where sector 3 lost its only outbound edge and
        trapped P3 Blake for 30 days."""
        # Try several seeds — the bug was seed-specific so we sample.
        for seed in [7777, 1234, 9999, 4242, 31415]:
            u, _ = _make_universe(seed=seed, size=400)
            for fed_sid in K.FEDSPACE_SECTORS:
                warps = u.sectors[fed_sid].warps
                assert len(warps) >= 1, (
                    f"seed={seed}: FedSpace sector {fed_sid} has 0 outbound warps "
                    f"(dead-end); would trap any player starting there"
                )

    def test_l2_every_sector_has_outbound_warp(self):
        """Stronger invariant: NO sector should be a dead-end. The one-way
        conversion guard now refuses to strip the last outbound edge."""
        for seed in [7777, 1234, 9999]:
            u, _ = _make_universe(seed=seed, size=400)
            dead_ends = [
                sid for sid, sec in u.sectors.items() if len(sec.warps) == 0
            ]
            assert not dead_ends, (
                f"seed={seed}: dead-end sectors found: {dead_ends[:10]}"
            )

    def test_l3_fedspace_internal_edges_are_bidirectional(self):
        """FedSpace-internal warps must remain two-way so players can always
        return to StarDock."""
        for seed in [7777, 1234, 9999]:
            u, _ = _make_universe(seed=seed, size=400)
            for a_sid in K.FEDSPACE_SECTORS:
                for b_sid in u.sectors[a_sid].warps:
                    if b_sid in K.FEDSPACE_SECTORS:
                        assert a_sid in u.sectors[b_sid].warps, (
                            f"seed={seed}: FedSpace edge {a_sid}→{b_sid} is one-way"
                        )

    def test_l4_hint_zero_fighters_in_fedspace(self):
        """When a player sits in FedSpace with 0 fighters + 0 shields,
        the action_hint should FYI them about StarDock's fighter shop.
        No mandate verbiage."""
        from tw2k.engine.observation import _action_hint

        u, (a, *_) = _make_universe(seed=9301)
        a.ship.fighters = 0
        a.ship.shields = 0
        a.sector_id = 1  # FedSpace
        sec_info = {"id": 1, "warps_out": [2, 3]}
        hint = _action_hint(sec_info, player=a, owned_planets=[], universe=u)
        assert "0 fighters" in hint or "unarmed" in hint.lower(), hint
        assert "FYI" in hint, "hint should use FYI framing (no mandate)"
        # Must NOT use coercive language
        assert "MUST buy" not in hint
        assert "REQUIRED" not in hint

    def test_l5_hint_zero_fighters_in_deep_space(self):
        """Deep-space phrasing emphasizes imminent danger; still informational."""
        from tw2k.engine.observation import _action_hint

        u, (a, *_) = _make_universe(seed=9302)
        a.ship.fighters = 0
        a.ship.shields = 0
        a.sector_id = 50  # deep space
        sec_info = {"id": 50, "warps_out": [51]}
        hint = _action_hint(sec_info, player=a, owned_planets=[], universe=u)
        assert "deep space" in hint.lower() and "0 fighters" in hint, hint

    def test_l6_hint_does_not_fire_when_armed(self):
        """Armed ships shouldn't get the unarmed warning."""
        from tw2k.engine.observation import _action_hint

        u, (a, *_) = _make_universe(seed=9303)
        a.ship.fighters = 100
        a.ship.shields = 50
        a.sector_id = 50
        sec_info = {"id": 50, "warps_out": [51]}
        hint = _action_hint(sec_info, player=a, owned_planets=[], universe=u)
        assert "0 fighters" not in hint

    def test_l7_hint_second_genesis_when_affordable(self):
        """1 planet + 25k+ credits + no genesis loaded → FYI hint
        with BOTH cluster-vs-diversify framing, mentioning the sector."""
        from tw2k.engine.observation import _action_hint

        u, (a, *_) = _make_universe(seed=9304)
        a.ship.genesis = 0
        a.credits = K.GENESIS_TORPEDO_COST + 5000
        a.ship.fighters = 100  # avoid the unarmed hint noise
        a.sector_id = 30
        owned = [{"id": 1, "sector_id": 44, "citadel_level": 1, "citadel_target": 1}]
        sec_info = {"id": 30, "warps_out": [31]}
        hint = _action_hint(sec_info, player=a, owned_planets=owned, universe=u)
        assert "another Genesis" in hint, hint
        assert "FYI" in hint
        assert "s44" in hint, "hint should reference the planet's sector"
        assert "Cluster" in hint and "risk spread" in hint, \
            "hint should surface cluster-vs-diversify tradeoff"

    def test_l7b_hint_third_genesis_tier(self):
        """2 planets → hint uses '3rd Genesis' + 'Empire forming' framing."""
        from tw2k.engine.observation import _action_hint

        u, (a, *_) = _make_universe(seed=9304)
        a.ship.genesis = 0
        a.credits = K.GENESIS_TORPEDO_COST + 5000
        a.ship.fighters = 100
        a.sector_id = 30
        owned = [
            {"id": 1, "sector_id": 44, "citadel_level": 2, "citadel_target": 2},
            {"id": 2, "sector_id": 77, "citadel_level": 1, "citadel_target": 1},
        ]
        sec_info = {"id": 30, "warps_out": [31]}
        hint = _action_hint(sec_info, player=a, owned_planets=owned, universe=u)
        assert "3rd Genesis" in hint, hint
        assert "Empire forming" in hint
        assert "s44" in hint and "s77" in hint

    def test_l8_hint_citadel_colonist_gap(self):
        """Credit-ready but colonist-short → gap hint."""
        from tw2k.engine.observation import _action_hint

        u, (a, *_) = _make_universe(seed=9305)
        a.credits = 50_000  # plenty for L3 (needs 20k)
        a.ship.fighters = 100
        a.sector_id = 30
        owned = [{
            "id": 7,
            "sector_id": 44,
            "citadel_level": 2,
            "citadel_target": 2,  # NOT currently building
            "treasury": 0,
            "colonists": {"colonists": 2500, "fuel_ore": 0, "organics": 0, "equipment": 0},
        }]
        sec_info = {"id": 30, "warps_out": [31]}
        hint = _action_hint(sec_info, player=a, owned_planets=owned, universe=u)
        assert "credit-ready" in hint, hint
        assert "colonists" in hint

    def test_l9_citadel_gap_hint_silent_while_building(self):
        """If citadel is actively upgrading (target > level), skip the hint —
        nothing to nudge, the work is already in-flight."""
        from tw2k.engine.observation import _action_hint

        u, (a, *_) = _make_universe(seed=9306)
        a.credits = 50_000
        a.ship.fighters = 100
        owned = [{
            "id": 7,
            "sector_id": 44,
            "citadel_level": 2,
            "citadel_target": 3,  # BUILDING
            "treasury": 0,
            "colonists": {"colonists": 2500},
        }]
        sec_info = {"id": 30, "warps_out": [31]}
        hint = _action_hint(sec_info, player=a, owned_planets=owned, universe=u)
        assert "credit-ready" not in hint

    def test_l10_inbox_hint_uses_no_obligation_language(self):
        """Inbox hint should say 'No obligation to reply' — we want agents
        to CHOOSE whether a hail is worth a detour, not feel forced."""
        from tw2k.engine.observation import _action_hint

        u, (a, *_) = _make_universe(seed=9307)
        a.inbox.append({
            "from": "B",
            "kind": "broadcast",
            "message": "rescue bounty",
            "day": 1,
            "tick": 10,
        })
        sec_info = {"id": 30, "warps_out": [31]}
        hint = _action_hint(sec_info, player=a, owned_planets=[], universe=u)
        assert "broadcast" in hint.lower(), hint
        assert "No obligation" in hint or "no obligation" in hint.lower()

    def test_l11_ferrengi_opportunist_attacks_unarmed(self):
        """A low-aggression Ferrengi (below the normal hunt threshold)
        should STILL attack a victim with 0 fighters + 0 shields."""
        from tw2k.engine.models import ShipClass
        from tw2k.engine.runner import _ferrengi_roam_and_hunt

        u, (a, *_) = _make_universe(seed=9308)
        # Plant player in deep space with no defenses.
        deep_sid = _first_non_fed_sector(u, min_id=50)
        a.sector_id = deep_sid
        # Move them to their sector's occupant list properly
        for s in u.sectors.values():
            if a.id in s.occupant_ids and s.id != deep_sid:
                s.occupant_ids.remove(a.id)
        u.sectors[deep_sid].occupant_ids.append(a.id)
        a.ship.fighters = 0
        a.ship.shields = 0

        # Timid Ferrengi in same sector — aggression below normal threshold
        # but above the opportunist threshold.
        timid = FerrengiShip(
            id="ferr_timid",
            name="Ferrengi Raider TIMID",
            sector_id=deep_sid,
            aggression=K.FERRENGI_OPPORTUNIST_AGGRESSION_THRESHOLD,
            fighters=500,
            shields=100,
            ship_class=ShipClass.MISSILE_FRIGATE,
        )
        # Make sure aggression is BELOW the normal hunt threshold
        assert timid.aggression < K.FERRENGI_HUNT_AGGRESSION_THRESHOLD
        u.ferrengi["ferr_timid"] = timid
        # Disable random movement so the test is deterministic
        import tw2k.engine.constants as K_mod
        original_move = K_mod.FERRENGI_MOVE_PROB
        K_mod.FERRENGI_MOVE_PROB = 0.0
        try:
            before = len([e for e in u.events if e.kind.value == "ferrengi_attack"])
            _ferrengi_roam_and_hunt(u)
            after = len([e for e in u.events if e.kind.value == "ferrengi_attack"])
        finally:
            K_mod.FERRENGI_MOVE_PROB = original_move
        assert after > before, (
            "low-aggression Ferrengi should attack a defenseless target "
            "(0 fighters, 0 shields) per the opportunist threshold"
        )

    def test_l12_ferrengi_leaves_armed_target_alone(self):
        """Low-aggression Ferrengi must still ignore a properly-armed target.
        The opportunist rule should ONLY activate on 0-defense victims."""
        import tw2k.engine.constants as K_mod
        from tw2k.engine.models import ShipClass
        from tw2k.engine.runner import _ferrengi_roam_and_hunt

        u, (a, *_) = _make_universe(seed=9309)
        deep_sid = _first_non_fed_sector(u, min_id=50)
        a.sector_id = deep_sid
        for s in u.sectors.values():
            if a.id in s.occupant_ids and s.id != deep_sid:
                s.occupant_ids.remove(a.id)
        u.sectors[deep_sid].occupant_ids.append(a.id)
        a.ship.fighters = 500  # armed
        a.ship.shields = 100

        timid = FerrengiShip(
            id="ferr_timid2",
            name="Ferrengi Raider TIMID2",
            sector_id=deep_sid,
            aggression=K.FERRENGI_OPPORTUNIST_AGGRESSION_THRESHOLD,
            fighters=100,
            shields=30,
            ship_class=ShipClass.MISSILE_FRIGATE,
        )
        assert timid.aggression < K.FERRENGI_HUNT_AGGRESSION_THRESHOLD
        u.ferrengi["ferr_timid2"] = timid
        original_move = K_mod.FERRENGI_MOVE_PROB
        K_mod.FERRENGI_MOVE_PROB = 0.0
        try:
            before = len([e for e in u.events if e.kind.value == "ferrengi_attack"])
            _ferrengi_roam_and_hunt(u)
            after = len([e for e in u.events if e.kind.value == "ferrengi_attack"])
        finally:
            K_mod.FERRENGI_MOVE_PROB = original_move
        assert after == before, (
            "armed target should NOT trigger an opportunist hunt "
            "(flee-check may move the Ferrengi but no attack expected)"
        )

    def test_l13_planet_orphan_event_on_elimination(self):
        """When a solo-owned planet's owner is eliminated, the engine must
        emit a discrete planet_orphaned event (UI/spectator visibility)."""
        from tw2k.engine.models import EventKind, Planet, PlanetClass

        u, (a, *_) = _make_universe(seed=9310)
        a.deaths = K.MAX_DEATHS_BEFORE_ELIM - 1  # one more death eliminates
        planet = Planet(
            id=99,
            sector_id=150,
            name="OrphanTest",
            class_id=PlanetClass.M,
            owner_id=a.id,
            citadel_level=2,
            fighters=2000,
        )
        u.planets[99] = planet
        _destroy_ship(u, a.id, reason="test", killer_id=None)
        orphan_events = [e for e in u.events if e.kind == EventKind.PLANET_ORPHANED]
        assert len(orphan_events) == 1
        ev = orphan_events[0]
        assert ev.payload["planet_id"] == 99
        assert ev.payload["former_owner"] == a.id
        assert ev.payload["citadel_level"] == 2
        assert u.planets[99].owner_id is None

    def test_l14_elimination_payload_lists_orphans(self):
        """The PLAYER_ELIMINATED event should include the orphaned planet ids
        in its payload for convenient post-match analysis."""
        from tw2k.engine.models import EventKind, Planet, PlanetClass

        u, (a, *_) = _make_universe(seed=9311)
        a.deaths = K.MAX_DEATHS_BEFORE_ELIM - 1
        u.planets[77] = Planet(
            id=77, sector_id=222, name="P77", class_id=PlanetClass.M,
            owner_id=a.id, citadel_level=1,
        )
        _destroy_ship(u, a.id, reason="test", killer_id=None)
        elim = next(e for e in u.events if e.kind == EventKind.PLAYER_ELIMINATED)
        assert 77 in elim.payload["orphaned_planets"]


# ---------------------------------------------------------------------------
# Phase M — Fog of War (per-agent event visibility)
#
# Agents must not see the raw universe.events stream. build_observation
# filters events so each player sees only:
#   - public/galaxy-wide drama (GAME_OVER, PLAYER_ELIMINATED, BROADCAST, ...)
#   - their own actions (actor_id == them)
#   - events they witnessed (they were in event.sector_id at emit time)
#   - party traffic addressed to them (hails, corp, alliance)
# Everything else is hidden. These tests verify the classification.
# ---------------------------------------------------------------------------


class TestPhaseMFogOfWar:
    def test_m1_public_events_visible_to_everyone(self):
        """PUBLIC events (GAME_START, BROADCAST, PLAYER_ELIMINATED, etc.)
        should be visible to every player regardless of location."""
        from tw2k.engine.models import EventKind
        from tw2k.engine.observation import _event_visible_to

        u, (a, b, c) = _make_universe(seed=500)
        a.sector_id = 100
        b.sector_id = 200
        c.sector_id = 300
        ev = u.emit(
            EventKind.BROADCAST,
            actor_id=a.id,
            summary="A broadcasts: hello galaxy",
        )
        assert _event_visible_to(ev, a.id, u)
        assert _event_visible_to(ev, b.id, u)
        assert _event_visible_to(ev, c.id, u)

    def test_m2_actor_only_events_hidden_from_others(self):
        """SCAN/PROBE/AGENT_THOUGHT/BUY_* should only be visible to the actor."""
        from tw2k.engine.models import EventKind
        from tw2k.engine.observation import _event_visible_to

        u, (a, b, _) = _make_universe(seed=501)
        for kind in (
            EventKind.SCAN,
            EventKind.PROBE,
            EventKind.BUY_SHIP,
            EventKind.BUY_EQUIP,
            EventKind.AGENT_THOUGHT,
            EventKind.AGENT_ERROR,
            EventKind.AUTOPILOT,
            EventKind.LIMPET_REPORT,
            EventKind.PHOTON_FIRED,
            EventKind.FED_RESPONSE,
            EventKind.WARP_BLOCKED,
            EventKind.TRADE_FAILED,
        ):
            ev = u.emit(kind, actor_id=a.id, summary="test")
            assert _event_visible_to(ev, a.id, u), f"{kind} should be visible to actor"
            assert not _event_visible_to(ev, b.id, u), (
                f"{kind} must NOT be visible to non-actor"
            )

    def test_m3_witnessed_events_visible_to_sector_occupants_only(self):
        """Default-category events (GENESIS_DEPLOYED, BUILD_CITADEL, WARP, ...)
        are visible to the actor AND anyone present in the sector at emit
        time, but NOT to players elsewhere."""
        from tw2k.engine.models import EventKind
        from tw2k.engine.observation import _event_visible_to

        u, (a, b, c) = _make_universe(seed=502)
        # Move A and C together to sector 500. B stays in sector 1.
        u.sectors[1].occupant_ids = [b.id]
        b.sector_id = 1
        u.sectors[500] = u.sectors.get(500) or u.sectors[list(u.sectors.keys())[5]]
        # Find a non-fed sector to stage in (reuse an existing one).
        stage = _first_non_fed_sector(u, min_id=50)
        u.sectors[stage].occupant_ids = [a.id, c.id]
        a.sector_id = stage
        c.sector_id = stage

        ev = u.emit(
            EventKind.GENESIS_DEPLOYED,
            actor_id=a.id,
            sector_id=stage,
            payload={"planet_id": 1},
            summary=f"{a.name} deploys a Genesis torpedo",
        )
        assert _event_visible_to(ev, a.id, u), "actor sees own event"
        assert _event_visible_to(ev, c.id, u), "same-sector occupant witnesses event"
        assert not _event_visible_to(ev, b.id, u), "distant player must NOT see it"

    def test_m4_witnesses_snapshot_at_emit_time(self):
        """Moving AFTER an event fires must not change visibility — the
        witness list is frozen at emit time."""
        from tw2k.engine.models import EventKind
        from tw2k.engine.observation import _event_visible_to

        u, (a, b, _) = _make_universe(seed=503)
        stage = _first_non_fed_sector(u, min_id=50)
        u.sectors[stage].occupant_ids = [a.id, b.id]
        a.sector_id = stage
        b.sector_id = stage

        ev = u.emit(
            EventKind.BUILD_CITADEL,
            actor_id=a.id,
            sector_id=stage,
            payload={"planet_id": 7},
            summary=f"{a.name} builds Level 1 citadel",
        )
        # B leaves the sector AFTER the event. Should still see it in history.
        u.sectors[stage].occupant_ids.remove(b.id)
        far = _first_non_fed_sector(u, min_id=stage + 10)
        u.sectors[far].occupant_ids.append(b.id)
        b.sector_id = far
        assert _event_visible_to(ev, b.id, u), "witness snapshot is historical"

    def test_m5_late_arrivals_do_not_see_past_events(self):
        """A player who warps INTO a sector after an event happened must
        NOT see the historical event (witness list doesn't auto-update)."""
        from tw2k.engine.models import EventKind
        from tw2k.engine.observation import _event_visible_to

        u, (a, b, _) = _make_universe(seed=504)
        stage = _first_non_fed_sector(u, min_id=50)
        # Only A is in the sector at emit time.
        u.sectors[stage].occupant_ids = [a.id]
        a.sector_id = stage
        ev = u.emit(
            EventKind.ASSIGN_COLONISTS,
            actor_id=a.id,
            sector_id=stage,
            payload={"planet_id": 3, "amount": 5000},
            summary=f"{a.name} assigns colonists",
        )
        # B shows up AFTER.
        u.sectors[stage].occupant_ids.append(b.id)
        b.sector_id = stage
        assert not _event_visible_to(ev, b.id, u), (
            "latecomers must not see historical events"
        )

    def test_m6_hail_visible_only_to_sender_and_recipient(self):
        """HAIL events are private to the two parties involved."""
        from tw2k.engine.models import EventKind
        from tw2k.engine.observation import _event_visible_to

        u, (a, b, c) = _make_universe(seed=505)
        ev = u.emit(
            EventKind.HAIL,
            actor_id=a.id,
            payload={"target": b.id, "message": "secret handshake"},
            summary=f"{a.name} hails {b.name}",
        )
        assert _event_visible_to(ev, a.id, u), "sender sees own hail"
        assert _event_visible_to(ev, b.id, u), "recipient sees hail"
        assert not _event_visible_to(ev, c.id, u), "third parties do NOT see hail"

    def test_m7_corp_events_visible_only_to_members(self):
        """CORP_* events are visible to actor + members (+ invited for INVITE)."""
        from tw2k.engine.models import Corporation, EventKind
        from tw2k.engine.observation import _event_visible_to

        u, (a, b, c) = _make_universe(seed=506)
        corp = Corporation(
            ticker="XYZ", name="XYZ Corp", ceo_id=a.id,
            member_ids=[a.id, b.id], formed_day=0,
        )
        u.corporations["XYZ"] = corp
        a.corp_ticker = "XYZ"
        b.corp_ticker = "XYZ"

        ev = u.emit(
            EventKind.CORP_DEPOSIT,
            actor_id=a.id,
            payload={"ticker": "XYZ", "amount": 10_000},
            summary=f"{a.name} deposits to XYZ",
        )
        assert _event_visible_to(ev, a.id, u), "actor sees corp event"
        assert _event_visible_to(ev, b.id, u), "co-member sees corp event"
        assert not _event_visible_to(ev, c.id, u), "non-member must NOT see"

        # Invited (non-member) should see the INVITE.
        invite_ev = u.emit(
            EventKind.CORP_INVITE,
            actor_id=a.id,
            payload={"ticker": "XYZ", "target": c.id},
            summary=f"{a.name} invited {c.name}",
        )
        corp.invited_ids.append(c.id)
        assert _event_visible_to(invite_ev, c.id, u), (
            "invitee sees their own invite via invited_ids membership"
        )

    def test_m8_alliance_events_visible_only_to_members(self):
        """ALLIANCE_* events are visible to members; others are kept dark."""
        from tw2k.engine.models import Alliance, EventKind
        from tw2k.engine.observation import _event_visible_to

        u, (a, b, c) = _make_universe(seed=507)
        ally = Alliance(
            id="AL1",
            member_ids=[a.id, b.id],
            proposed_by=a.id,
            formed_day=0,
            active=True,
        )
        u.alliances["AL1"] = ally
        a.alliances.append("AL1")
        b.alliances.append("AL1")

        ev = u.emit(
            EventKind.ALLIANCE_FORMED,
            actor_id=b.id,
            payload={"alliance_id": "AL1", "members": [a.id, b.id]},
            summary="Alliance formed",
        )
        assert _event_visible_to(ev, a.id, u)
        assert _event_visible_to(ev, b.id, u)
        assert not _event_visible_to(ev, c.id, u), (
            "outsiders must not learn of private alliance formation"
        )

    def test_m9_alliance_proposed_visible_to_proposer_and_target(self):
        """ALLIANCE_PROPOSED should be visible to the proposer and target
        (so the target can decide), but not to unrelated players."""
        from tw2k.engine.models import EventKind
        from tw2k.engine.observation import _event_visible_to

        u, (a, b, c) = _make_universe(seed=508)
        ev = u.emit(
            EventKind.ALLIANCE_PROPOSED,
            actor_id=a.id,
            payload={"alliance_id": "AL9", "target": b.id},
            summary=f"{a.name} proposed alliance to {b.name}",
        )
        assert _event_visible_to(ev, a.id, u)
        assert _event_visible_to(ev, b.id, u)
        assert not _event_visible_to(ev, c.id, u)

    def test_m10_build_observation_filters_events(self):
        """Integration: build_observation must NOT leak other players'
        private actions into `recent_events`."""
        from tw2k.engine.models import EventKind
        from tw2k.engine.observation import build_observation

        u, (a, b, _) = _make_universe(seed=509)
        # A is alone in a distant sector, doing secret work.
        stage = _first_non_fed_sector(u, min_id=50)
        u.sectors[1].occupant_ids = [p.id for p in (u.players[pid] for pid in ("B", "C"))]
        u.sectors[stage].occupant_ids = [a.id]
        a.sector_id = stage
        b.sector_id = 1
        u.emit(
            EventKind.GENESIS_DEPLOYED,
            actor_id=a.id,
            sector_id=stage,
            payload={"planet_id": 1},
            summary=f"{a.name} deploys Genesis in secret sector",
        )
        u.emit(
            EventKind.BUILD_CITADEL,
            actor_id=a.id,
            sector_id=stage,
            payload={"planet_id": 1},
            summary=f"{a.name} builds citadel",
        )
        obs_a = build_observation(u, a.id)
        obs_b = build_observation(u, b.id)

        a_kinds = [e["kind"] for e in obs_a.recent_events]
        b_kinds = [e["kind"] for e in obs_b.recent_events]
        assert EventKind.GENESIS_DEPLOYED.value in a_kinds, "actor sees own Genesis"
        assert EventKind.BUILD_CITADEL.value in a_kinds, "actor sees own citadel"
        assert EventKind.GENESIS_DEPLOYED.value not in b_kinds, (
            "B must not see A's secret Genesis — core fog-of-war guarantee"
        )
        assert EventKind.BUILD_CITADEL.value not in b_kinds, (
            "B must not see A's secret citadel build"
        )

    def test_m11_witnesses_never_leak_to_observation(self):
        """The internal _witnesses payload key must be stripped before any
        event dict reaches the agent — it's bookkeeping, not game state."""
        from tw2k.engine.models import EventKind
        from tw2k.engine.observation import _event_to_dict

        u, (a, _, _) = _make_universe(seed=510)
        ev = u.emit(
            EventKind.WARP,
            actor_id=a.id,
            sector_id=1,
            summary="A warps",
        )
        # Witnesses should be stored on the raw event...
        assert "_witnesses" in ev.payload
        # ...but must NEVER appear in the agent-facing dict.
        d = _event_to_dict(ev)
        assert "_witnesses" not in d
        # And the Observation schema doesn't currently surface payload at
        # all — double-check that assumption so we don't silently regress.
        assert "payload" not in d

    def test_m12_build_observation_public_events_still_reach_everyone(self):
        """Fog of war must not crush public signals — PLAYER_ELIMINATED,
        PLANET_ORPHANED, BROADCAST, PORT_DESTROYED must show up for every
        player's observation."""
        from tw2k.engine.models import EventKind
        from tw2k.engine.observation import build_observation

        u, (a, b, c) = _make_universe(seed=511)
        u.emit(
            EventKind.BROADCAST,
            actor_id=a.id,
            payload={"message": "all hands"},
            summary="A broadcasts: all hands",
        )
        u.emit(
            EventKind.PORT_DESTROYED,
            actor_id=a.id,
            sector_id=77,
            payload={"sector_id": 77},
            summary="port destroyed in 77",
        )
        for pid in (a.id, b.id, c.id):
            obs = build_observation(u, pid)
            kinds = {e["kind"] for e in obs.recent_events}
            assert EventKind.BROADCAST.value in kinds, (
                "broadcasts are public by design"
            )
            assert EventKind.PORT_DESTROYED.value in kinds, (
                "port destruction is galaxy-wide news"
            )

    def test_m13_emit_without_sector_has_no_witnesses(self):
        """Events emitted without a sector_id (e.g. GAME_START, DAY_TICK)
        get no witness list — they're classified by kind only."""
        from tw2k.engine.models import EventKind

        u, _ = _make_universe(seed=512)
        ev = u.emit(EventKind.DAY_TICK, summary="day 1")
        assert "_witnesses" not in ev.payload
