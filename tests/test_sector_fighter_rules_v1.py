"""Sector fighter caps, toll pot, recall, and surrender. Real engine path."""

from __future__ import annotations

import random

import pytest

import tw2k.engine.constants as K
from tests.test_phase_abc import _first_non_fed_sector, _make_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import (
    Alliance,
    Corporation,
    EventKind,
    FighterDeployment,
    FighterMode,
    MineDeployment,
    MineType,
    Planet,
    PlanetClass,
)
from tw2k.engine.observation import _event_visible_to, build_observation, event_facts
from tw2k.engine.runner import apply_action


def _park(u, player, sid: int) -> None:
    here = u.sectors[player.sector_id]
    if player.id in here.occupant_ids:
        here.occupant_ids.remove(player.id)
    player.sector_id = sid
    player.planet_landed = None
    player.turns_today = 0
    if player.id not in u.sectors[sid].occupant_ids:
        u.sectors[sid].occupant_ids.append(player.id)


def _link(u, a: int, b: int) -> None:
    if b not in u.sectors[a].warps:
        u.sectors[a].warps.append(b)
    if a not in u.sectors[b].warps:
        u.sectors[b].warps.append(a)


def _la(u, pid: str, kind: str):
    return {la.kind: la for la in legal_actions(u, pid)}[kind]


def _money(u) -> int:
    credits = sum(int(p.credits) for p in u.players.values())
    pots = sum(int(s.fighters.toll_credits) for s in u.sectors.values() if s.fighters is not None)
    return credits + pots


def test_fighter_cap_is_in_the_list_and_the_handler() -> None:
    u, (owner, *_) = _make_universe(seed=34001)
    sid = _first_non_fed_sector(u)
    assert not u.sectors[sid].planet_ids
    _park(u, owner, sid)
    owner.ship.fighters = 20
    u.sectors[sid].fighters = FighterDeployment(owner_id=owner.id, count=4990, mode=FighterMode.DEFENSIVE)
    listed = _la(u, owner.id, "deploy_fighters")
    assert listed.legal
    assert listed.params["qty"]["max"] == 10
    over = apply_action(u, owner.id, Action(kind=ActionKind.DEPLOY_FIGHTERS, args={"qty": 11, "mode": "defensive"}))
    assert not over.ok
    assert u.sectors[sid].fighters.count == 4990
    assert owner.ship.fighters == 20
    assert owner.turns_today == 0
    ok = apply_action(u, owner.id, Action(kind=ActionKind.DEPLOY_FIGHTERS, args={"qty": 10, "mode": "defensive"}))
    assert ok.ok, ok.error
    assert u.sectors[sid].fighters.count == 5000
    assert owner.ship.fighters == 10


def test_a_planet_raises_the_fighter_cap() -> None:
    u, (owner, *_) = _make_universe(seed=34011)
    sid = _first_non_fed_sector(u)
    _park(u, owner, sid)
    owner.ship.fighters = 20
    u.sectors[sid].fighters = FighterDeployment(owner_id=owner.id, count=5000, mode=FighterMode.DEFENSIVE)
    blocked = _la(u, owner.id, "deploy_fighters")
    assert not blocked.legal
    planet = Planet(id=91001, sector_id=sid, name="Cap", class_id=PlanetClass.M)
    u.planets[planet.id] = planet
    u.sectors[sid].planet_ids.append(planet.id)
    listed = _la(u, owner.id, "deploy_fighters")
    assert listed.legal
    assert listed.params["qty"]["max"] == 20
    ok = apply_action(u, owner.id, Action(kind=ActionKind.DEPLOY_FIGHTERS, args={"qty": 10, "mode": "defensive"}))
    assert ok.ok, ok.error
    assert u.sectors[sid].fighters.count == 5010


def test_mine_cap_is_in_the_list_and_the_handler() -> None:
    u, (owner, *_) = _make_universe(seed=34002)
    sid = _first_non_fed_sector(u)
    _park(u, owner, sid)
    owner.ship.mines[MineType.ARMID] = 5
    u.sectors[sid].mines.append(MineDeployment(owner_id=owner.id, kind=MineType.ARMID, count=97))
    listed = _la(u, owner.id, "deploy_mines")
    assert listed.legal
    assert listed.params["qty"]["max_by"]["armid"] == 2
    over = apply_action(u, owner.id, Action(kind=ActionKind.DEPLOY_MINES, args={"qty": 3, "kind": "armid"}))
    assert not over.ok
    assert sum(m.count for m in u.sectors[sid].mines) == 97
    assert owner.ship.mines[MineType.ARMID] == 5
    assert owner.turns_today == 0
    ok = apply_action(u, owner.id, Action(kind=ActionKind.DEPLOY_MINES, args={"qty": 2, "kind": "armid"}))
    assert ok.ok, ok.error
    assert sum(m.count for m in u.sectors[sid].mines) == 99


def test_toll_price_is_in_the_list_and_the_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    # The toll billed on the warp is the COMBAT_MODE legacy entry path now. In tw2002 combat the
    # same 5-per-fighter bill is paid at the challenge (tests/test_ship_combat_core_v1.py).
    monkeypatch.setattr(K, "COMBAT_MODE", "legacy")
    u, (owner, payer, outsider) = _make_universe(seed=34003)
    home = _first_non_fed_sector(u, 40)
    there = _first_non_fed_sector(u, home + 1)
    _link(u, home, there)
    _park(u, owner, there)
    owner.ship.fighters = 10
    placed = apply_action(u, owner.id, Action(kind=ActionKind.DEPLOY_FIGHTERS, args={"qty": 4, "mode": "toll"}))
    assert placed.ok, placed.error
    _park(u, payer, home)
    payer.credits = 1000
    owner_credits = owner.credits
    listed = _la(u, payer.id, "warp")
    assert listed.params["toll_due_by"][str(there)] == 20
    before = _money(u)
    res = apply_action(u, payer.id, Action(kind=ActionKind.WARP, args={"target": there}))
    assert res.ok, res.error
    assert payer.credits == 980
    assert owner.credits == owner_credits
    assert u.sectors[there].fighters.toll_credits == 20
    assert _money(u) == before
    _park(u, outsider, there)
    seen = build_observation(u, outsider.id)
    assert "toll_credits" not in seen.sector["fighter_group"]
    owner_seen = build_observation(u, owner.id)
    assert owner_seen.sector["fighter_group"]["toll_credits"] == 20
    u2, (owner2, payer2, *_) = _make_universe(seed=34004)
    a = _first_non_fed_sector(u2, 50)
    b = _first_non_fed_sector(u2, a + 1)
    _link(u2, a, b)
    _park(u2, owner2, b)
    owner2.ship.fighters = 8
    assert apply_action(u2, owner2.id, Action(kind=ActionKind.DEPLOY_FIGHTERS, args={"qty": 4, "mode": "toll"})).ok
    _park(u2, payer2, a)
    payer2.credits = 19
    blocked = apply_action(u2, payer2.id, Action(kind=ActionKind.WARP, args={"target": b}))
    assert not blocked.ok
    assert payer2.credits == 19
    assert payer2.sector_id == a
    assert payer2.turns_today == 0
    assert u2.sectors[b].fighters.toll_credits == 0


def test_owner_collects_the_pot_by_recalling() -> None:
    u, (owner, payer, bystander) = _make_universe(seed=34005)
    home = _first_non_fed_sector(u, 60)
    there = _first_non_fed_sector(u, home + 1)
    _link(u, home, there)
    _park(u, owner, there)
    owner.ship.fighters = 20
    assert apply_action(u, owner.id, Action(kind=ActionKind.DEPLOY_FIGHTERS, args={"qty": 10, "mode": "toll"})).ok
    _park(u, payer, home)
    payer.credits = 500
    assert apply_action(u, payer.id, Action(kind=ActionKind.WARP, args={"target": there})).ok
    # tw2002 combat: the warp opens a challenge and the toll is paid as its own action.
    assert apply_action(u, payer.id, Action(kind=ActionKind.PAY_TOLL, args={})).ok
    assert u.sectors[there].fighters.toll_credits == 50
    _park(u, owner, there)
    owner.turns_today = 0
    before = owner.credits
    part = apply_action(u, owner.id, Action(kind=ActionKind.RECALL_DEPLOYED, args={"what": "fighters", "qty": 4}))
    assert part.ok, part.error
    assert part.turns_spent == 1
    assert owner.credits == before + 20
    assert owner.ship.fighters == 14
    assert u.sectors[there].fighters.count == 6
    assert u.sectors[there].fighters.toll_credits == 30
    ev = next(e for e in u.events if e.kind is EventKind.RECALL_DEPLOYED)
    assert set(event_facts(ev)) <= {"what", "qty", "kind"}
    assert "cr" not in ev.summary
    _park(u, bystander, home)
    assert not _event_visible_to(ev, bystander.id, u)
    rest = apply_action(u, owner.id, Action(kind=ActionKind.RECALL_DEPLOYED, args={"what": "fighters", "qty": 6}))
    assert rest.ok, rest.error
    assert owner.credits == before + 50
    assert u.sectors[there].fighters is None


def test_recall_owner_gate_is_in_the_list_and_the_handler() -> None:
    u, (owner, other, *_) = _make_universe(seed=34006)
    sid = _first_non_fed_sector(u)
    _park(u, owner, sid)
    _park(u, other, sid)
    owner.ship.fighters = 8
    other.ship.fighters = 8
    assert apply_action(u, owner.id, Action(kind=ActionKind.DEPLOY_FIGHTERS, args={"qty": 5, "mode": "defensive"})).ok
    other.turns_today = 0
    listed = _la(u, other.id, "recall_deployed")
    assert not listed.legal
    taken = other.ship.fighters
    res = apply_action(u, other.id, Action(kind=ActionKind.RECALL_DEPLOYED, args={"what": "fighters", "qty": 5}))
    assert not res.ok
    assert other.ship.fighters == taken
    assert u.sectors[sid].fighters.count == 5
    assert u.sectors[sid].fighters.owner_id == owner.id
    assert other.turns_today == 0


def test_recall_mines_and_ship_room() -> None:
    u, (owner, *_) = _make_universe(seed=34007)
    sid = _first_non_fed_sector(u)
    _park(u, owner, sid)
    owner.ship.mines[MineType.ARMID] = 4
    assert apply_action(u, owner.id, Action(kind=ActionKind.DEPLOY_MINES, args={"qty": 3, "kind": "armid"})).ok
    owner.turns_today = 0
    res = apply_action(u, owner.id, Action(kind=ActionKind.RECALL_DEPLOYED, args={"what": "mines", "kind": "armid", "qty": 2}))
    assert res.ok, res.error
    assert owner.ship.mines[MineType.ARMID] == 3
    assert u.sectors[sid].mines[0].count == 1
    owner.ship.fighters = 2500
    u.sectors[sid].fighters = FighterDeployment(owner_id=owner.id, count=5, mode=FighterMode.DEFENSIVE)
    owner.turns_today = 0
    listed = _la(u, owner.id, "recall_deployed")
    assert "fighters" not in listed.params["what"]["choices"]
    blocked = apply_action(u, owner.id, Action(kind=ActionKind.RECALL_DEPLOYED, args={"what": "fighters", "qty": 1}))
    assert not blocked.ok
    assert owner.ship.fighters == 2500
    assert u.sectors[sid].fighters.count == 5


def test_surrender_gate_is_in_the_list_and_the_handler() -> None:
    u, (owner, victim, *_) = _make_universe(seed=34008)
    sid = _first_non_fed_sector(u)
    _park(u, owner, sid)
    owner.ship.fighters = 6
    assert apply_action(u, owner.id, Action(kind=ActionKind.DEPLOY_FIGHTERS, args={"qty": 4, "mode": "offensive"})).ok
    _park(u, victim, sid)
    victim.credits = 400
    listed = _la(u, victim.id, "surrender")
    assert not listed.legal
    res = apply_action(u, victim.id, Action(kind=ActionKind.SURRENDER, args={}))
    assert not res.ok
    assert victim.deaths == 0
    assert victim.credits == 400
    assert victim.sector_id == sid
    u.sectors[sid].fighters.mode = FighterMode.DEFENSIVE
    listed = _la(u, victim.id, "surrender")
    assert not listed.legal
    assert "challenge" in (listed.reason or "").lower()
    blocked = apply_action(u, victim.id, Action(kind=ActionKind.SURRENDER, args={}))
    assert not blocked.ok
    assert victim.deaths == 0
    assert victim.credits == 400
    assert victim.sector_id == sid
    u.sectors[sid].fighters.mode = FighterMode.TOLL
    listed = _la(u, victim.id, "surrender")
    assert not listed.legal
    blocked = apply_action(u, victim.id, Action(kind=ActionKind.SURRENDER, args={}))
    assert not blocked.ok
    assert victim.deaths == 0


def test_destroying_toll_fighters_pays_the_pot_to_the_attacker() -> None:
    u, (owner, attacker, *_) = _make_universe(seed=34009)
    sid = _first_non_fed_sector(u)
    _park(u, owner, sid)
    _park(u, attacker, sid)
    u.sectors[sid].fighters = FighterDeployment(
        owner_id=owner.id, count=1, mode=FighterMode.TOLL, toll_credits=1234,
    )
    attacker.ship.fighters = 100
    attacker.credits = 1000
    res = apply_action(u, attacker.id, Action(kind=ActionKind.DEPLOY_FIGHTERS, args={"qty": 20, "mode": "offensive"}))
    assert res.ok, res.error
    assert attacker.credits == 2234
    assert u.sectors[sid].fighters is None or u.sectors[sid].fighters.owner_id == attacker.id
    combat = next(e for e in reversed(u.events) if e.kind is EventKind.COMBAT)
    assert "toll_credits" not in event_facts(combat)
    assert "1234" not in combat.summary


def test_legacy_switch_keeps_the_old_toll_and_no_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(K, "SECTOR_FIGHTER_MODE", "legacy")
    u, (owner, payer, *_) = _make_universe(seed=34010)
    home = _first_non_fed_sector(u, 70)
    there = _first_non_fed_sector(u, home + 1)
    _link(u, home, there)
    _park(u, owner, there)
    owner.ship.fighters = 30
    u.sectors[there].fighters = FighterDeployment(owner_id=owner.id, count=6000, mode=FighterMode.DEFENSIVE)
    listed = _la(u, owner.id, "deploy_fighters")
    assert listed.legal
    assert listed.params["qty"]["max"] == 30
    assert apply_action(u, owner.id, Action(kind=ActionKind.DEPLOY_FIGHTERS, args={"qty": 10, "mode": "defensive"})).ok
    assert u.sectors[there].fighters.count == 6010
    u.sectors[there].fighters = FighterDeployment(owner_id=owner.id, count=3, mode=FighterMode.TOLL)
    _park(u, payer, home)
    payer.credits = 100
    owner.credits = 100
    assert "toll_due_by" not in _la(u, payer.id, "warp").params
    assert apply_action(u, payer.id, Action(kind=ActionKind.WARP, args={"target": there})).ok
    assert payer.credits == 90
    assert owner.credits == 110
    assert u.sectors[there].fighters.toll_credits == 0
    assert not _la(u, owner.id, "recall_deployed").legal
    assert not _la(u, payer.id, "surrender").legal




def test_unpaid_toll_makes_warp_and_hostile_land_illegal(monkeypatch: pytest.MonkeyPatch) -> None:
    """0.1 legal list and handler agree when credits < toll due (COMBAT_MODE legacy entry path).

    In tw2002 combat a ship that cannot pay enters and is challenged instead.
    """
    monkeypatch.setattr(K, "COMBAT_MODE", "legacy")
    u, (owner, payer, *_) = _make_universe(seed=34201)
    home = _first_non_fed_sector(u, 80)
    there = _first_non_fed_sector(u, home + 1)
    _link(u, home, there)
    _park(u, owner, there)
    owner.ship.fighters = 10
    assert apply_action(u, owner.id, Action(kind=ActionKind.DEPLOY_FIGHTERS, args={"qty": 10, "mode": "toll"})).ok
    _park(u, payer, home)
    payer.credits = 10
    listed = _la(u, payer.id, "warp")
    assert listed.params["toll_due_by"][str(there)] == 50
    assert there not in listed.params["target"]["choices"]
    if not listed.params["target"]["choices"]:
        assert not listed.legal
        assert "toll" in (listed.reason or "").lower()
    blocked = apply_action(u, payer.id, Action(kind=ActionKind.WARP, args={"target": there}))
    assert not blocked.ok
    assert payer.credits == 10
    assert payer.sector_id == home
    assert payer.turns_today == 0

    # When every neighbor is an unpaid toll, warp itself is illegal.
    home_sec = u.sectors[home]
    home_sec.warps[:] = [there]
    u.sectors[there].warps[:] = [w for w in u.sectors[there].warps if w != home] + [home]
    listed = _la(u, payer.id, "warp")
    assert not listed.legal
    assert "toll" in (listed.reason or "").lower()
    assert listed.params["target"]["choices"] == []

    planet = Planet(id=93001, sector_id=there, name="TollWorld", class_id=PlanetClass.M, owner_id=owner.id)
    u.planets[planet.id] = planet
    u.sectors[there].planet_ids.append(planet.id)
    _park(u, payer, there)
    payer.credits = 10
    payer.turns_today = 0
    land_listed = _la(u, payer.id, "land_planet")
    assert not land_listed.legal
    assert "toll" in (land_listed.reason or "").lower()
    land = apply_action(u, payer.id, Action(kind=ActionKind.LAND_PLANET, args={"planet_id": planet.id}))
    assert not land.ok
    assert payer.planet_landed is None
    assert payer.credits == 10
    assert payer.turns_today == 0


def test_atomic_detonation_pays_toll_pot_to_detonator() -> None:
    """0.2 clearing fighters on an atomic pays the pot in tw2002 mode."""
    u, (owner, bomber, *_) = _make_universe(seed=34202)
    sid = _first_non_fed_sector(u)
    _park(u, owner, sid)
    _park(u, bomber, sid)
    u.sectors[sid].fighters = FighterDeployment(
        owner_id=owner.id, count=8, mode=FighterMode.TOLL, toll_credits=777,
    )
    bomber.ship.mines[MineType.ATOMIC] = 1
    bomber.credits = 100
    before = _money(u)
    res = apply_action(u, bomber.id, Action(kind=ActionKind.DEPLOY_MINES, args={"qty": 1, "kind": "atomic"}))
    assert res.ok, res.error
    assert u.sectors[sid].fighters is None
    assert bomber.credits == 877
    assert _money(u) == before


def test_deploy_clash_returns_fighters_over_cap_to_ship() -> None:
    """0.3 deploy-clash excess past the sector cap returns to the ship."""
    u, (owner, attacker, *_) = _make_universe(seed=34203)
    sid = _first_non_fed_sector(u)
    assert not u.sectors[sid].planet_ids
    _park(u, owner, sid)
    _park(u, attacker, sid)
    u.sectors[sid].fighters = FighterDeployment(owner_id=owner.id, count=1, mode=FighterMode.DEFENSIVE)
    attacker.ship.fighters = 6000
    res = apply_action(u, attacker.id, Action(kind=ActionKind.DEPLOY_FIGHTERS, args={"qty": 6000, "mode": "offensive"}))
    assert res.ok, res.error
    combat = next(e for e in reversed(u.events) if e.kind is EventKind.COMBAT)
    att_losses = int(combat.payload["attacker_losses"])
    dep = u.sectors[sid].fighters
    assert dep is not None
    assert dep.owner_id == attacker.id
    assert dep.count == 5000
    assert attacker.ship.fighters == 6000 - att_losses - 5000
    assert attacker.ship.fighters + dep.count == 6000 - att_losses


def test_surrender_refused_until_defensive_challenge() -> None:
    """0.4 surrender stays illegal without a live challenge (a ship parked here was never challenged)."""
    u, (owner, victim, *_) = _make_universe(seed=34204)
    sid = _first_non_fed_sector(u)
    _park(u, owner, sid)
    _park(u, victim, sid)
    u.sectors[sid].fighters = FighterDeployment(owner_id=owner.id, count=5, mode=FighterMode.DEFENSIVE)
    victim.credits = 800
    listed = _la(u, victim.id, "surrender")
    assert not listed.legal
    res = apply_action(u, victim.id, Action(kind=ActionKind.SURRENDER, args={}))
    assert not res.ok
    assert victim.deaths == 0
    assert victim.credits == 800
    assert victim.sector_id == sid


def test_corp_mate_and_ally_not_charged_toll() -> None:
    """0.5 corp mates and allies pass toll fighters without paying."""
    u, (owner, mate, ally) = _make_universe(seed=34301)
    home = _first_non_fed_sector(u, 90)
    there = _first_non_fed_sector(u, home + 1)
    _link(u, home, there)
    _park(u, owner, there)
    owner.ship.fighters = 6
    assert apply_action(u, owner.id, Action(kind=ActionKind.DEPLOY_FIGHTERS, args={"qty": 4, "mode": "toll"})).ok
    assert u.sectors[there].fighters.toll_credits == 0
    corp = Corporation(ticker="ZZ", name="Zed", ceo_id=owner.id, member_ids=[owner.id, mate.id], formed_day=0)
    u.corporations["ZZ"] = corp
    owner.corp_ticker = "ZZ"
    mate.corp_ticker = "ZZ"
    _park(u, mate, home)
    mate.credits = 500
    before_mate = mate.credits
    res = apply_action(u, mate.id, Action(kind=ActionKind.WARP, args={"target": there}))
    assert res.ok, res.error
    assert mate.credits == before_mate
    assert u.sectors[there].fighters.toll_credits == 0

    bond = Alliance(id="A1", member_ids=[owner.id, ally.id], proposed_by=owner.id, formed_day=0, active=True)
    u.alliances["A1"] = bond
    owner.alliances.append("A1")
    ally.alliances.append("A1")
    _park(u, ally, home)
    ally.credits = 500
    before_ally = ally.credits
    res = apply_action(u, ally.id, Action(kind=ActionKind.WARP, args={"target": there}))
    assert res.ok, res.error
    assert ally.credits == before_ally
    assert u.sectors[there].fighters.toll_credits == 0


def test_recall_refused_when_not_in_that_sector() -> None:
    """0.5 recall only works while standing in the sector with your group."""
    u, (owner, *_) = _make_universe(seed=34302)
    here = _first_non_fed_sector(u, 100)
    away = _first_non_fed_sector(u, here + 1)
    _park(u, owner, here)
    owner.ship.fighters = 12
    assert apply_action(u, owner.id, Action(kind=ActionKind.DEPLOY_FIGHTERS, args={"qty": 5, "mode": "defensive"})).ok
    _park(u, owner, away)
    owner.turns_today = 0
    listed = _la(u, owner.id, "recall_deployed")
    assert not listed.legal
    taken = owner.ship.fighters
    res = apply_action(u, owner.id, Action(kind=ActionKind.RECALL_DEPLOYED, args={"what": "fighters", "qty": 5}))
    assert not res.ok
    assert owner.ship.fighters == taken
    assert u.sectors[here].fighters is not None
    assert u.sectors[here].fighters.count == 5
    assert owner.turns_today == 0


def test_existing_over_cap_group_not_shrunk_on_deploy() -> None:
    """0.5 an already over-cap group stays put when a deploy is refused."""
    u, (owner, *_) = _make_universe(seed=34303)
    sid = _first_non_fed_sector(u)
    assert not u.sectors[sid].planet_ids
    _park(u, owner, sid)
    owner.ship.fighters = 20
    u.sectors[sid].fighters = FighterDeployment(owner_id=owner.id, count=6000, mode=FighterMode.DEFENSIVE)
    listed = _la(u, owner.id, "deploy_fighters")
    assert not listed.legal
    res = apply_action(u, owner.id, Action(kind=ActionKind.DEPLOY_FIGHTERS, args={"qty": 1, "mode": "defensive"}))
    assert not res.ok
    assert u.sectors[sid].fighters.count == 6000
    assert owner.ship.fighters == 20
    assert owner.turns_today == 0


def test_atomic_deploy_allowed_at_mine_cap() -> None:
    """0.5 atomic detonates and does not count against the 99 sitting-mine cap."""
    u, (owner, *_) = _make_universe(seed=34304)
    sid = _first_non_fed_sector(u)
    _park(u, owner, sid)
    u.sectors[sid].mines.append(MineDeployment(owner_id=owner.id, kind=MineType.ARMID, count=99))
    owner.ship.mines[MineType.ATOMIC] = 1
    listed = _la(u, owner.id, "deploy_mines")
    assert listed.legal
    assert "atomic" in listed.params["kind"]["choices"]
    assert listed.params["qty"]["max_by"]["atomic"] == 1
    before = sum(int(m.count) for m in u.sectors[sid].mines)
    res = apply_action(u, owner.id, Action(kind=ActionKind.DEPLOY_MINES, args={"qty": 1, "kind": "atomic"}))
    assert res.ok, res.error
    assert sum(int(m.count) for m in u.sectors[sid].mines) == before
    assert owner.ship.mines[MineType.ATOMIC] == 0


def test_fuzz_tolls_caps_and_fog() -> None:
    for seed in range(34100, 34112):
        u, (a, b, watcher) = _make_universe(seed=seed, size=80)
        left = _first_non_fed_sector(u, 20)
        right = _first_non_fed_sector(u, left + 1)
        _link(u, left, right)
        if seed % 2 == 0:
            planet = Planet(id=92000 + seed, sector_id=right, name="Fuzz", class_id=PlanetClass.M)
            u.planets[planet.id] = planet
            u.sectors[right].planet_ids.append(planet.id)
        for player, sid in ((a, left), (b, right)):
            _park(u, player, sid)
            player.ship.fighters = 40
            player.ship.mines[MineType.ARMID] = 8
            player.credits = 5000
        _park(u, watcher, left)
        rng = random.Random(seed)
        for _step in range(24):
            actor = a if rng.randrange(2) == 0 else b
            roll = rng.randrange(6)
            if roll == 0:
                action = Action(kind=ActionKind.DEPLOY_FIGHTERS, args={
                    "qty": rng.randint(1, 6),
                    "mode": rng.choice(["defensive", "offensive", "toll"]),
                })
            elif roll == 1:
                action = Action(kind=ActionKind.DEPLOY_MINES, args={"qty": rng.randint(1, 3), "kind": "armid"})
            elif roll == 2:
                action = Action(kind=ActionKind.RECALL_DEPLOYED, args={"what": "fighters", "qty": rng.randint(1, 4)})
            elif roll == 3:
                action = Action(kind=ActionKind.RECALL_DEPLOYED, args={"what": "mines", "kind": "armid", "qty": 1})
            elif roll == 4:
                other = right if actor.sector_id == left else left
                action = Action(kind=ActionKind.WARP, args={"target": other})
            else:
                action = Action(kind=ActionKind.SURRENDER, args={})
            before = _money(u)
            deaths = actor.deaths
            apply_action(u, actor.id, action)
            after = _money(u)
            if actor.deaths > deaths:
                assert after <= before
            else:
                assert after == before, f"seed {seed} created credits {before} -> {after}"
            for p in (a, b, watcher):
                assert p.ship.fighters >= 0
                assert p.credits >= 0
                assert all(int(n) >= 0 for n in p.ship.mines.values())
            for sec in u.sectors.values():
                if sec.fighters is not None:
                    assert sec.fighters.count >= 0
                    assert sec.fighters.toll_credits >= 0
                    cap = 30000 if sec.planet_ids else 5000
                    assert sec.fighters.count <= cap
                assert sum(int(m.count) for m in sec.mines) <= 99
                assert all(int(m.count) >= 0 for m in sec.mines)
        seen = build_observation(u, watcher.id)
        group = (seen.sector or {}).get("fighter_group") or {}
        if group.get("owner_id") != watcher.id:
            assert "toll_credits" not in group
