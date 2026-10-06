"""ship-combat-core-v1: defensive/toll challenge and ship-vs-ship combat. Real engine path.

Rules: docs/playtests/combat/SHIP_COMBAT.md. Numbers are hardcoded here on purpose
(odds 1.0/1.6/2.0, fighters per attack, 1.25 flee, 5 cr per toll fighter); the test
does not read them back from constants.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tests.test_phase_abc import _first_non_fed_sector, _make_universe
from tw2k.agents.seat_acceptance import validate_action
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import (
    Commodity,
    EventKind,
    FerrengiShip,
    FighterDeployment,
    FighterMode,
    MineDeployment,
    MineType,
    Planet,
    PlanetClass,
    ShipClass,
)
from tw2k.engine.observation import _event_visible_to, build_observation, event_facts
from tw2k.engine.runner import apply_action

ROOT = Path(__file__).resolve().parents[1]
HULLS = [c for c in ShipClass if c is not ShipClass.ESCAPE_POD]  # the pod is not for sale


@pytest.fixture(autouse=True)
def _legacy_info(monkeypatch):
    # These tests burn turns with a free scan; scanners are SCANNERS_HIDDEN_INFO.md's business.
    monkeypatch.setattr(K, "INFO_MODE", "legacy")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


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


def _act(u, pid: str, kind: ActionKind, **args):
    return apply_action(u, pid, Action(kind=kind, args=args))


def _duel(seed: int, a_hull=ShipClass.MERCHANT_CRUISER, d_hull=ShipClass.MERCHANT_CRUISER):
    u, (a, d, c) = _make_universe(seed=seed)
    sid = _first_non_fed_sector(u)
    _park(u, a, sid)
    _park(u, d, sid)
    a.ship.ship_class = a_hull
    d.ship.ship_class = d_hull
    # Keep flee destinations predictable: no neighbor holds fighters.
    for w in u.sectors[sid].warps:
        u.sectors[w].fighters = None
    return u, a, d, c, sid


def _challenge(seed: int, mode: str = "defensive", count: int = 10, *, one_way: bool = False, credits: int = 1000):
    """B warps from `home` into `there`, held by A's fighters. Returns (u, owner, ship, home, there)."""
    u, (owner, ship, c) = _make_universe(seed=seed)
    home = _first_non_fed_sector(u, 40)
    there = _first_non_fed_sector(u, home + 1)
    _link(u, home, there)
    if one_way:
        u.sectors[there].warps = [w for w in u.sectors[there].warps if w != home]
        if not u.sectors[there].warps:
            u.sectors[there].warps = [1]
    u.sectors[there].fighters = FighterDeployment(owner_id=owner.id, count=count, mode=FighterMode(mode))
    u.sectors[there].mines = []
    u.sectors[home].mines = []
    _park(u, ship, home)
    ship.credits = credits
    res = _act(u, ship.id, ActionKind.WARP, target=there)
    assert res.ok, res.error
    assert ship.sector_id == there
    return u, owner, ship, home, there


def _last(u, kind: EventKind):
    return next(e for e in reversed(u.events) if e.kind is kind)


# ---------------------------------------------------------------------------
# rules table
# ---------------------------------------------------------------------------


def test_rules_table_is_written_first() -> None:
    doc = (ROOT / "docs" / "playtests" / "combat" / "SHIP_COMBAT.md").read_text(encoding="utf-8")
    for mark in ("CONFIRMED", "SOURCE-CONFLICT", "UNVERIFIED"):
        assert mark in doc
    for words in ("attack, retreat, or surrender", "1.25", "fighters per attack", "Shields first",
                  "Deliberate differences", "COMBAT_MODE", "formulas.html", "fleeing.html"):
        assert words in doc, words


# ---------------------------------------------------------------------------
# ship vs ship
# ---------------------------------------------------------------------------


def test_odds_multiply_the_attackers_fighters() -> None:
    # Battleship odds 1.6 against a Merchant Cruiser at 1.0. 100 fighters deal 160.
    u, a, d, _c, _sid = _duel(35101, ShipClass.BATTLESHIP)
    a.ship.fighters, d.ship.fighters, d.ship.shields = 500, 400, 100
    res = _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=100)
    assert res.ok, res.error
    assert res.turns_spent == 5
    assert d.ship.shields == 0
    assert d.ship.fighters == 400 - 60
    assert a.ship.fighters == 400
    ev = _last(u, EventKind.COMBAT)
    facts = event_facts(ev)
    assert facts["sent"] == 100 and facts["attacker_losses"] == 100 and facts["defender_losses"] == 60


def test_defender_odds_raise_the_real_defense() -> None:
    # Scout Marauder defends at 2.0: 40 fighters + 10 shields are worth 100. 99 do not beat it.
    u, a, d, _c, _sid = _duel(35102, ShipClass.MERCHANT_CRUISER, ShipClass.SCOUT_MARAUDER)
    a.ship.fighters, d.ship.fighters, d.ship.shields = 300, 40, 10
    assert _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=99).ok
    # floor(99 / 2) = 49 units: 10 shields, then 39 fighters.
    assert (d.ship.shields, d.ship.fighters) == (0, 1)
    assert d.deaths == 0
    assert a.ship.fighters == 201


def test_beating_the_defense_destroys_the_ship_and_costs_what_it_took() -> None:
    u, a, d, _c, _sid = _duel(35103, ShipClass.BATTLESHIP)
    a.ship.fighters, d.ship.fighters, d.ship.shields = 1000, 300, 100
    deaths = d.deaths
    assert _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=600).ok
    # Real defense 400 at 1.0; ceil(400 / 1.6) = 250 fighters lost.
    assert a.ship.fighters == 750
    assert d.deaths == deaths + 1
    assert d.ship.ship_class is ShipClass.ESCAPE_POD  # DEATH_MODE tw2002: DEATH_ESCAPE_PODS.md
    assert event_facts(_last(u, EventKind.COMBAT))["outcome"] == "destroyed"


def test_per_attack_cap_is_in_the_list_and_the_handler() -> None:
    # Scout Marauder: 250 fighters per attack.
    u, a, d, _c, _sid = _duel(35104, ShipClass.SCOUT_MARAUDER)
    a.ship.fighters, d.ship.fighters = 300, 5000
    listed = _la(u, a.id, "attack")
    assert listed.legal
    assert listed.params["qty"]["max"] == 250
    over = _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=251)
    assert not over.ok
    assert a.ship.fighters == 300 and d.ship.fighters == 5000 and a.turns_today == 0
    assert _act(u, a.id, ActionKind.ATTACK, target=d.id).ok  # missing qty sends the cap
    assert a.ship.fighters == 50


def test_shields_absorb_first() -> None:
    u, a, d, _c, _sid = _duel(35105)
    a.ship.fighters, d.ship.fighters, d.ship.shields = 500, 300, 200
    assert _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=150).ok
    assert d.ship.shields == 50
    assert d.ship.fighters == 300


def test_photon_disabled_defender_shields_do_not_absorb() -> None:
    u, a, d, _c, _sid = _duel(35106)
    a.ship.fighters, d.ship.fighters, d.ship.shields = 500, 300, 200
    d.ship.photon_disabled_ticks = 1
    assert _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=150).ok
    assert d.ship.shields == 200
    assert d.ship.fighters == 150


def test_attack_with_no_fighters_is_not_offered_or_taken() -> None:
    u, a, d, _c, _sid = _duel(35107)
    a.ship.fighters = 0
    listed = _la(u, a.id, "attack")
    assert not listed.legal
    assert "fighters" in (listed.reason or "")
    res = _act(u, a.id, ActionKind.ATTACK, target=d.id)
    assert not res.ok
    assert a.deaths == 0 and a.turns_today == 0


def test_attacker_loses_what_it_sent_and_is_never_destroyed() -> None:
    u, a, d, _c, _sid = _duel(35108)
    a.ship.fighters, d.ship.fighters, d.ship.shields = 50, 5000, 0
    assert _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=50).ok
    assert a.ship.fighters == 0
    assert a.deaths == 0 and a.alive
    assert d.ship.fighters == 4950


def test_defender_flees_only_past_one_and_a_quarter() -> None:
    # After the wave the defender has 100 fighters + 0 shields. 125 on hand do not make it flee.
    u, a, d, _c, sid = _duel(35109)
    a.ship.fighters, d.ship.fighters, d.ship.shields = 126, 101, 0
    assert _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=1).ok
    assert a.ship.fighters == 125 and d.ship.fighters == 100
    assert d.sector_id == sid
    assert not event_facts(_last(u, EventKind.COMBAT))["defender_fled"]
    # 126 on hand against 100: it flees one hop.
    u, a, d, _c, sid = _duel(35109)
    a.ship.fighters, d.ship.fighters, d.ship.shields = 127, 101, 0
    assert _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=1).ok
    assert d.sector_id != sid and d.sector_id in u.sectors[sid].warps
    assert d.flee_penalty
    # 110 on hand against 100 never flees (1.1 is under 1.25).
    u, a, d, _c, sid = _duel(35109)
    a.ship.fighters, d.ship.fighters, d.ship.shields = 111, 101, 0
    assert _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=1).ok
    assert d.sector_id == sid


def test_flee_counts_shields_and_skips_hostile_fighters_and_mines() -> None:
    u, a, d, c, sid = _duel(35110)
    a.ship.fighters, d.ship.fighters, d.ship.shields = 1000, 50, 50
    extra = _first_non_fed_sector(u, sid + 1)
    _link(u, sid, extra)
    warps = sorted(u.sectors[sid].warps)
    assert len(warps) >= 2
    safe = warps[-1]
    for w in warps[:-1]:
        u.sectors[w].fighters = FighterDeployment(owner_id=c.id, count=3, mode=FighterMode.DEFENSIVE)
    u.sectors[safe].mines = [MineDeployment(owner_id=c.id, kind=MineType.ARMID, count=9)]
    assert _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=10).ok
    assert d.sector_id == safe
    assert u.sectors[safe].mines[0].count == 9  # no hazard fired on the flee
    assert d.fighter_challenge is None
    facts = event_facts(_last(u, EventKind.COMBAT))
    assert facts["defender_fled"] is True
    assert safe not in facts.values()


def test_tholian_never_flees_and_an_interdictor_holds_the_target() -> None:
    u, a, d, _c, sid = _duel(35111, ShipClass.MERCHANT_CRUISER, ShipClass.THOLIAN_SENTINEL)
    a.ship.fighters, d.ship.fighters, d.ship.shields = 2000, 10, 0
    assert _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=1).ok
    assert d.sector_id == sid
    u, a, d, _c, sid = _duel(35111, ShipClass.INTERDICTOR_CRUISER)
    a.ship.fighters, d.ship.fighters, d.ship.shields = 2000, 10, 0
    assert _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=1).ok
    assert d.sector_id == sid


def test_flee_penalty_hits_the_next_land_or_port_only() -> None:
    u, a, d, _c, sid = _duel(35112)
    a.ship.fighters, d.ship.fighters, d.ship.shields = 1000, 50, 0
    assert _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=1).ok
    assert d.flee_penalty
    here = u.sectors[d.sector_id]
    here.planet_ids = list(here.planet_ids)
    pl = Planet(id=97001, sector_id=d.sector_id, name="Haven", class_id=PlanetClass.M, owner_id=d.id)
    u.planets[pl.id] = pl
    here.planet_ids.append(pl.id)
    listed = _la(u, d.id, "land_planet")
    assert listed.turn_cost == K.TURN_COST["land_planet"] + 1
    d.turns_today = 0
    res = _act(u, d.id, ActionKind.LAND_PLANET, planet_id=pl.id)
    assert res.ok, res.error
    assert d.turns_today == K.TURN_COST["land_planet"] + 1
    assert not d.flee_penalty
    # Any other turn-using action first cancels it.
    u, a, d, _c, sid = _duel(35112)
    a.ship.fighters, d.ship.fighters, d.ship.shields = 1000, 50, 0
    assert _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=1).ok
    d.turns_today = 0
    assert _act(u, d.id, ActionKind.SCAN).ok
    assert not d.flee_penalty


def test_ferrengi_target_uses_odds_and_pays_the_bounty() -> None:
    u, a, _d, _c, sid = _duel(35113, ShipClass.BATTLESHIP)
    u.ferrengi["F9"] = FerrengiShip(id="F9", name="Grabby", sector_id=sid, aggression=3, fighters=120, shields=40)
    a.ship.fighters = 500
    credits = a.credits
    listed = _la(u, a.id, "attack")
    assert "F9" in listed.params["target"]["ferrengi"]
    assert _act(u, a.id, ActionKind.ATTACK, target="F9", qty=100).ok
    # 100 * 1.6 = 160 against (40 + 120) * 1.0 = 160: beaten. The attacker loses ceil(160 / 1.6) = 100.
    assert not u.ferrengi["F9"].alive
    assert a.ship.fighters == 400
    assert a.credits > credits


# ---------------------------------------------------------------------------
# the challenge
# ---------------------------------------------------------------------------


def test_defensive_fighters_challenge_and_hold_every_other_verb() -> None:
    u, owner, ship, home, there = _challenge(35201)
    assert ship.fighter_challenge == {"sector_id": there, "from_sector": home, "mode": "defensive"}
    las = {la.kind: la for la in legal_actions(u, ship.id)}
    for kind in ("warp", "trade", "scan", "land_planet", "deploy_fighters", "plot_course"):
        assert not las[kind].legal, kind
        if kind in ("warp", "scan", "plot_course"):
            assert "answer the fighters" in (las[kind].reason or "")
    assert las["attack"].legal and las["attack"].params["target"]["choices"] == ["fighters"]
    assert las["retreat"].legal and las["surrender"].legal
    assert not las["pay_toll"].legal
    turns = ship.turns_today
    for kind, args in ((ActionKind.WARP, {"target": home}), (ActionKind.SCAN, {}),
                       (ActionKind.ATTACK, {"target": owner.id})):
        res = apply_action(u, ship.id, Action(kind=kind, args=args))
        assert not res.ok, kind
    assert ship.turns_today == turns and ship.sector_id == there
    # WAIT (and the free hail, broadcast, limpet query) stay open; the challenge stays too.
    assert las["wait"].legal and las["query_limpets"].legal
    assert _act(u, ship.id, ActionKind.WAIT).ok
    assert ship.fighter_challenge is not None and ship.sector_id == there
    # Defensive fighters never shoot first: fighters and shields untouched by the entry.
    assert ship.ship.fighters == 200 and ship.ship.shields == 100


def test_observation_shows_the_challenge_and_nothing_hidden() -> None:
    u, owner, ship, home, there = _challenge(35202, mode="toll", count=6)
    obs = build_observation(u, ship.id)
    assert obs.fighter_challenge == {"sector_id": there, "mode": "toll", "count": 6, "can_retreat": True,
                                     "retreat_to": home, "toll": 30}
    assert "FIGHTER CHALLENGE" in obs.action_hint and "pay_toll" in obs.action_hint
    # The fighter group was already in the sector brief; the pot stays the owner's secret.
    assert obs.sector["fighter_group"]["count"] == 6 and "toll_credits" not in obs.sector["fighter_group"]
    ev = _last(u, EventKind.FIGHTER_CHALLENGE)
    assert event_facts(ev) == {"mode": "toll", "count": 6}
    assert _event_visible_to(ev, ship.id, u)
    assert not _event_visible_to(ev, "C", u)
    # Other ships in a sector still show no fighters or shields.
    _park(u, u.players["C"], there)
    seen = build_observation(u, ship.id)
    other = next(o for o in seen.other_players if o["id"] == "C")
    assert "fighters" not in other and "shields" not in other


def test_retreat_goes_back_costs_a_warp_and_fires_nothing() -> None:
    u, owner, ship, home, there = _challenge(35203)
    u.sectors[home].mines = [MineDeployment(owner_id=owner.id, kind=MineType.ARMID, count=9)]
    listed = _la(u, ship.id, "retreat")
    assert listed.legal and listed.turn_cost == 3 and listed.params["to"] == home
    before = ship.turns_today
    fighters, shields = ship.ship.fighters, ship.ship.shields
    res = _act(u, ship.id, ActionKind.RETREAT)
    assert res.ok, res.error
    assert ship.sector_id == home
    assert ship.turns_today == before + 3
    assert (ship.ship.fighters, ship.ship.shields) == (fighters, shields)
    assert u.sectors[home].mines[0].count == 9
    assert ship.fighter_challenge is None
    assert event_facts(_last(u, EventKind.RETREAT)) == {"from": there, "to": home}


def test_no_retreat_after_a_one_way_warp_or_under_an_interdictor() -> None:
    u, owner, ship, home, there = _challenge(35204, one_way=True)
    listed = _la(u, ship.id, "retreat")
    assert not listed.legal and "warp back" in (listed.reason or "")
    res = _act(u, ship.id, ActionKind.RETREAT)
    assert not res.ok and ship.sector_id == there and ship.turns_today == 3
    u, owner, ship, home, there = _challenge(35205)
    pl = Planet(id=97002, sector_id=there, name="Gate", class_id=PlanetClass.M, owner_id=owner.id,
                citadel_level=6)
    pl.stockpile[Commodity.FUEL_ORE] = 5000
    u.planets[pl.id] = pl
    u.sectors[there].planet_ids.append(pl.id)
    listed = _la(u, ship.id, "retreat")
    assert not listed.legal and "interdictor" in (listed.reason or "")
    assert not _act(u, ship.id, ActionKind.RETREAT).ok
    assert pl.stockpile[Commodity.FUEL_ORE] == 5000


def test_pay_toll_is_five_per_fighter_into_the_pot() -> None:
    u, owner, ship, home, there = _challenge(35206, mode="toll", count=8, credits=100)
    listed = _la(u, ship.id, "pay_toll")
    assert listed.legal and listed.params["amount"] == 40 and listed.turn_cost == 0
    owner_credits = owner.credits
    res = _act(u, ship.id, ActionKind.PAY_TOLL)
    assert res.ok, res.error
    assert ship.credits == 60
    assert u.sectors[there].fighters.toll_credits == 40
    assert owner.credits == owner_credits
    assert ship.fighter_challenge is None
    assert _act(u, ship.id, ActionKind.SCAN).ok


def test_a_ship_that_cannot_pay_enters_and_must_answer() -> None:
    u, owner, ship, home, there = _challenge(35207, mode="toll", count=8, credits=39)
    listed = _la(u, ship.id, "pay_toll")
    assert not listed.legal and "40" in (listed.reason or "")
    assert not _act(u, ship.id, ActionKind.PAY_TOLL).ok
    assert ship.credits == 39
    assert _la(u, ship.id, "retreat").legal


def test_attacking_the_fighters_clears_them_or_leaves_the_challenge() -> None:
    u, owner, ship, home, there = _challenge(35208, count=50)
    ship.ship.fighters = 30
    res = _act(u, ship.id, ActionKind.ATTACK, target="fighters", qty=30)
    assert res.ok, res.error
    assert ship.ship.fighters == 0 and ship.deaths == 0
    assert u.sectors[there].fighters.count == 20
    assert ship.fighter_challenge is not None
    assert not _la(u, ship.id, "attack").legal  # nothing left to send
    ship.ship.fighters = 100
    u.sectors[there].fighters.toll_credits = 77
    credits = ship.credits
    assert _act(u, ship.id, ActionKind.ATTACK, target="fighters").ok
    assert u.sectors[there].fighters is None
    assert ship.ship.fighters == 80
    assert ship.credits == credits + 77
    assert ship.fighter_challenge is None
    assert _la(u, ship.id, "warp").legal


def test_fighter_attack_uses_the_hulls_odds() -> None:
    u, owner, ship, home, there = _challenge(35209, count=100)
    ship.ship.ship_class = ShipClass.SCOUT_MARAUDER
    ship.ship.fighters = 150
    assert _act(u, ship.id, ActionKind.ATTACK, target="fighters", qty=50).ok
    assert u.sectors[there].fighters is None
    assert ship.ship.fighters == 100


def test_surrender_takes_the_existing_death_with_a_warning() -> None:
    u, owner, ship, home, there = _challenge(35210, credits=1000)
    listed = _la(u, ship.id, "surrender")
    assert listed.legal and "200 fighters" in listed.params["warning"]
    deaths = ship.deaths
    res = _act(u, ship.id, ActionKind.SURRENDER)
    assert res.ok, res.error
    assert ship.deaths == deaths + 1
    # DEATH_MODE tw2002 (DEATH_ESCAPE_PODS.md d20): the pod goes back where the ship came from.
    # gb14: surrender is not a player ship-kill, so the cash sinks.
    assert ship.sector_id == home and ship.ship.ship_class is ShipClass.ESCAPE_POD
    assert ship.credits == 0
    assert ship.fighter_challenge is None
    assert event_facts(_last(u, EventKind.SURRENDER)) == {"mode": "defensive"}
    assert _last(u, EventKind.SHIP_DESTROYED).payload["reason"] == "surrender"


def test_offensive_fighters_take_no_surrender_and_open_no_challenge() -> None:
    u, (owner, ship, _c) = _make_universe(seed=35211)
    home = _first_non_fed_sector(u, 40)
    there = _first_non_fed_sector(u, home + 1)
    _link(u, home, there)
    u.sectors[there].fighters = FighterDeployment(owner_id=owner.id, count=5, mode=FighterMode.OFFENSIVE)
    _park(u, ship, home)
    assert _act(u, ship.id, ActionKind.WARP, target=there).ok
    assert ship.fighter_challenge is None
    assert not _la(u, ship.id, "surrender").legal
    assert not _act(u, ship.id, ActionKind.SURRENDER).ok


def test_corp_mate_is_not_challenged_and_a_course_stops_at_a_challenge() -> None:
    u, (owner, mate, other) = _make_universe(seed=35212)
    owner.corp_ticker = mate.corp_ticker = "ZZ"
    home = _first_non_fed_sector(u, 40)
    there = _first_non_fed_sector(u, home + 1)
    _link(u, home, there)
    u.sectors[there].fighters = FighterDeployment(
        owner_id=owner.id, count=5, mode=FighterMode.DEFENSIVE, corp_ticker="ZZ",
    )
    _park(u, mate, home)
    assert _act(u, mate.id, ActionKind.WARP, target=there).ok
    assert mate.fighter_challenge is None
    far = next(w for w in u.sectors[there].warps if w != home)
    _park(u, other, home)
    res = _act(u, other.id, ActionKind.PLOT_COURSE, target=far, execute=True)
    assert res.ok, res.error
    assert other.sector_id == there and other.fighter_challenge is not None


def test_a_stale_challenge_clears_when_the_fighters_go() -> None:
    u, owner, ship, home, there = _challenge(35213)
    u.sectors[there].fighters = None
    assert _la(u, ship.id, "scan").legal
    assert _act(u, ship.id, ActionKind.SCAN).ok
    assert ship.fighter_challenge is None


# ---------------------------------------------------------------------------
# legacy switch
# ---------------------------------------------------------------------------


def test_legacy_switch_keeps_the_old_dice_and_entry_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Golden numbers recorded on the unmodified engine (21a9783) with the same script."""
    monkeypatch.setattr(K, "COMBAT_MODE", "legacy")
    monkeypatch.setattr(K, "DEATH_MODE", "legacy")  # recorded with the old death (fighters back to 20)
    golden = {35001: (177, 0, 20, 0, 1, 1), 35002: (127, 0, 20, 0, 1, 2), 35003: (114, 0, 20, 0, 1, 2)}
    for seed, want in golden.items():
        u, (a, b, _c) = _make_universe(seed=seed)
        sid = _first_non_fed_sector(u)
        _park(u, a, sid)
        _park(u, b, sid)
        a.ship.fighters, a.ship.shields = 200, 100
        b.ship.fighters, b.ship.shields = 150, 50
        assert "qty" not in _la(u, a.id, "attack").params
        res = _act(u, a.id, ActionKind.ATTACK, target=b.id)
        assert res.ok and res.turns_spent == 5
        ev = _last(u, EventKind.COMBAT)
        got = (a.ship.fighters, a.ship.shields, b.ship.fighters, b.ship.shields, b.deaths, len(ev.payload["rounds"]))
        assert got == want, seed
        assert ev.payload["exchange_max_rounds"] == 3
    for mode, credits, pot in (("defensive", 1000, 0), ("toll", 965, 35)):
        u, (owner, b, _c) = _make_universe(seed=35005)
        home = _first_non_fed_sector(u, 40)
        there = _first_non_fed_sector(u, home + 1)
        _link(u, home, there)
        u.sectors[there].fighters = FighterDeployment(owner_id=owner.id, count=7, mode=FighterMode(mode))
        _park(u, b, home)
        b.credits = 1000
        assert _act(u, b.id, ActionKind.WARP, target=there).ok
        assert b.sector_id == there and b.fighter_challenge is None
        assert b.credits == credits and u.sectors[there].fighters.toll_credits == pot
        res = _act(u, b.id, ActionKind.SURRENDER)
        assert not res.ok and res.error == "surrender waits for the defensive challenge"
        assert not _la(u, b.id, "retreat").legal and not _act(u, b.id, ActionKind.RETREAT).ok
        assert _act(u, b.id, ActionKind.SCAN).ok


# ---------------------------------------------------------------------------
# seat brains and the heuristic seat stay legal
# ---------------------------------------------------------------------------


def _brains():
    import importlib.util

    spec = importlib.util.spec_from_file_location("sba", ROOT / "scripts" / "seat_brain_acceptance.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from tw2k.agents.seat_brain import SeatBrain

    return {"N1": mod.n1_brain, "N2": mod.n2_brain, "N3": SeatBrain}


@pytest.mark.parametrize("case", ["toll-rich", "toll-broke", "defensive", "one-way-strong", "one-way-weak"])
def test_seat_brains_answer_a_challenge_legally(case: str) -> None:
    for name, make in _brains().items():
        mode = "toll" if case.startswith("toll") else "defensive"
        u, owner, ship, home, there = _challenge(35301, mode=mode, count=50, one_way=case.startswith("one-way"),
                                                 credits=10 if case == "toll-broke" else 5000)
        if case == "one-way-weak":
            ship.ship.fighters = 10
        brain = make()
        obs = build_observation(u, ship.id).model_dump(mode="json")
        act = brain.decide(obs)
        assert validate_action(obs, act) == [], (name, case, act)
        res = apply_action(u, ship.id, Action(kind=act["kind"], args=act.get("args") or {}))
        assert res.ok, (name, case, act, res.error)
        want = {"toll-rich": "pay_toll", "toll-broke": "retreat", "defensive": "retreat",
                "one-way-strong": "attack", "one-way-weak": "surrender"}[case]
        assert act["kind"] == want, (name, case, act)


@pytest.mark.parametrize("case", ["toll-rich", "defensive", "one-way-weak"])
def test_heuristic_seat_answers_a_challenge_legally(case: str) -> None:
    import asyncio

    from tw2k.agents import HeuristicAgent

    mode = "toll" if case.startswith("toll") else "defensive"
    u, owner, ship, home, there = _challenge(35302, mode=mode, count=50, one_way=case.startswith("one-way"),
                                             credits=5000)
    if case == "one-way-weak":
        ship.ship.fighters = 10
    agent = HeuristicAgent(ship.id, ship.name, seed=1)
    obs = build_observation(u, ship.id)
    act = asyncio.run(agent.act(obs))
    res = apply_action(u, ship.id, act)
    assert res.ok, (case, act, res.error)


# ---------------------------------------------------------------------------
# fuzz: all 16 hulls
# ---------------------------------------------------------------------------


def test_fuzz_all_sixteen_hulls() -> None:
    assert len(HULLS) == 16
    rng = random.Random(250925)
    for i in range(400):
        a_hull = HULLS[i % 16]
        d_hull = HULLS[rng.randrange(16)]
        u, a, d, c, sid = _duel(36000 + (i % 7), a_hull, d_hull)
        a_spec, d_spec = K.SHIP_SPECS_TW2002[a_hull.value], K.SHIP_SPECS_TW2002[d_hull.value]
        a.ship.fighters = rng.randint(0, a_spec["max_fighters"])
        a.ship.shields = rng.randint(0, a_spec["max_shields"])
        d.ship.fighters = rng.randint(0, d_spec["max_fighters"])
        d.ship.shields = rng.randint(0, d_spec["max_shields"])
        if rng.random() < 0.1:
            d.ship.photon_disabled_ticks = 1
        a.credits, d.credits = rng.randint(0, 50_000), rng.randint(0, 50_000)
        listed = _la(u, a.id, "attack")
        cap = min(a.ship.fighters, a_spec["fighters_per_attack"])
        assert listed.legal == (cap > 0), (a_hull, a.ship.fighters)
        if not listed.legal:
            assert not _act(u, a.id, ActionKind.ATTACK, target=d.id).ok
            continue
        assert listed.params["qty"]["max"] == cap
        qty = rng.randint(1, cap)
        a0, d0f, d0s, deaths0 = a.ship.fighters, d.ship.fighters, d.ship.shields, d.deaths
        a_s0 = a.ship.shields
        res = _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=qty)
        assert res.ok, res.error
        facts = event_facts(_last(u, EventKind.COMBAT))
        # Conservation: what each side lost is exactly what left the ships. Nothing is created.
        assert a0 - a.ship.fighters == facts["attacker_losses"] <= qty
        assert a.ship.shields == a_s0 and a.deaths == 0 and a.alive
        if d.deaths == deaths0:
            assert d0f - d.ship.fighters == facts["defender_losses"]
            assert 0 <= d.ship.shields <= d0s
            assert facts["outcome"] in ("hit", "miss")
        else:
            assert facts["outcome"] == "destroyed" and facts["defender_losses"] == d0f
        for p in (a, d, c):
            assert p.ship.fighters >= 0 and p.ship.shields >= 0 and p.credits >= 0
        assert sum(1 for s in u.sectors.values() if d.id in s.occupant_ids) == 1


def test_fuzz_challenge_answers_keep_counts_whole() -> None:
    rng = random.Random(4242)
    for i in range(160):
        mode = rng.choice(["defensive", "toll"])
        u, owner, ship, home, there = _challenge(36100 + (i % 5), mode=mode, count=rng.randint(1, 400),
                                                 one_way=rng.random() < 0.3, credits=rng.randint(0, 3000))
        ship.ship.ship_class = HULLS[i % 16]
        ship.ship.fighters = rng.randint(0, 600)
        for _ in range(6):
            las = {la.kind: la for la in legal_actions(u, ship.id)}
            options = [k for k in ("attack", "retreat", "pay_toll", "surrender") if las[k].legal]
            if not options or ship.fighter_challenge is None:
                break
            kind = rng.choice(options)
            args = {}
            if kind == "attack":
                args = {"target": "fighters", "qty": rng.randint(1, las["attack"].params["qty"]["max"])}
            dep = u.sectors[there].fighters
            before = (ship.ship.fighters, dep.count if dep else 0, ship.credits, dep.toll_credits if dep else 0,
                      owner.credits)
            res = apply_action(u, ship.id, Action(kind=ActionKind(kind), args=args))
            assert res.ok, (kind, res.error)
            dep = u.sectors[there].fighters
            if kind == "attack":
                facts = event_facts(_last(u, EventKind.COMBAT))
                assert before[0] - ship.ship.fighters == facts["attacker_losses"]
                assert before[1] - (dep.count if dep else 0) == facts["defender_losses"]
            if kind == "pay_toll":
                assert before[2] - ship.credits == dep.toll_credits - before[3] == 5 * dep.count
            if kind == "retreat":
                assert ship.ship.fighters == before[0] and ship.sector_id == home
            assert ship.ship.fighters >= 0 and ship.credits >= 0 and owner.credits >= 0
            assert dep is None or dep.count > 0
            if not ship.alive or ship.sector_id != there:
                break


def test_every_new_verb_has_a_cockpit_form_and_prompt_line() -> None:
    js = (ROOT / "web" / "bot.js").read_text(encoding="utf-8")
    for kind in ("retreat", "pay_toll"):
        assert f'"{kind}"' in js
    prompts = (ROOT / "src" / "tw2k" / "agents" / "prompts.py").read_text(encoding="utf-8")
    for kind in ("retreat", "pay_toll"):
        assert kind in prompts
