"""NOTE 86. Special hulls, Ferrengi grudges, and the 30 s Ferrengi clock.

Each switch is off by default. The stored flag stays legacy when the v3.11 profile turns the helper on.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tests.test_ferrengi_aliens_v1 import _add_player, _world
from tests.test_phase_abc import _first_non_fed_sector, _make_universe
from tests.test_ship_combat_core_v1 import _act, _challenge, _duel, _link, _park
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.ferrengi import (
    _ferrengi_regen,
    _ferrengi_roam_and_hunt,
    _ferrengi_step,
    _make_ferrengi,
    preferred_ferrengi_dest,
    record_ferrengi_grudge,
    settle_ferrengi_pace_day,
)
from tw2k.engine.models import Commodity, EventKind, Planet, PlanetClass, ShipClass
from tw2k.engine.runner import apply_action
from tw2k.engine.ship_transwarp import handle_ship_transwarp


def _live_hulls(monkeypatch) -> None:
    monkeypatch.setattr(K, "SPECIAL_HULL_RULES_MODE", "live")
    monkeypatch.setattr(K, "SHIP_ROSTER_MODE", "live")


def _quiet(u, *sids: int) -> None:
    for sid in sids:
        sec = u.sectors[sid]
        sec.mines = []
        sec.fighters = None


class _Clock:
    """Every pace roll hits, and a hop takes the first listed warp."""

    def random(self) -> float:
        return 0.0

    def randrange(self, n: int) -> int:
        return 0

    def choice(self, seq):
        return list(seq)[0]


def test_helpers_stay_off_and_the_profile_turns_them_on(monkeypatch) -> None:
    assert K.special_hull_rules_on() is False
    assert K.ferrengi_grudge_on() is False
    assert K.ferrengi_pace_on() is False
    assert K.SPECIAL_HULL_RULES_MODE == "legacy"
    assert K.FERRENGI_GRUDGE_MODE == "legacy"
    assert K.FERRENGI_PACE_MODE == "legacy"
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.special_hull_rules_on() is True
    assert K.ferrengi_grudge_on() is True
    assert K.ferrengi_pace_on() is True
    assert K.SPECIAL_HULL_RULES_MODE == "legacy"
    assert K.FERRENGI_GRUDGE_MODE == "legacy"
    assert K.FERRENGI_PACE_MODE == "legacy"


def test_interdictor_holds_only_when_the_rule_and_the_roster_are_on(monkeypatch) -> None:
    u, (pilot, cruiser, mate) = _make_universe(seed=8601)
    sid = _first_non_fed_sector(u)
    nxt = u.sectors[sid].warps[0]
    _link(u, sid, nxt)
    _park(u, pilot, sid)
    _park(u, cruiser, sid)
    _park(u, mate, sid)
    cruiser.ship.ship_class = ShipClass.INTERDICTOR_CRUISER
    pilot.corp_ticker = mate.corp_ticker = cruiser.corp_ticker = "ZZ"
    pilot.turns_today = 0

    res = _act(u, pilot.id, ActionKind.WARP, target=nxt)
    assert res.ok, res.error
    assert pilot.sector_id == nxt

    _park(u, pilot, sid)
    monkeypatch.setattr(K, "SPECIAL_HULL_RULES_MODE", "live")
    res = _act(u, pilot.id, ActionKind.WARP, target=nxt)
    assert res.ok, res.error

    _park(u, pilot, sid)
    _live_hulls(monkeypatch)
    before = int(pilot.turns_today)
    res = _act(u, pilot.id, ActionKind.WARP, target=nxt)
    assert not res.ok
    assert res.error == "an Interdictor Cruiser holds this sector"
    assert int(res.turns_spent or 0) == 0
    assert pilot.turns_today == before
    assert pilot.sector_id == sid
    blocked = next(e for e in reversed(u.events) if e.kind is EventKind.WARP_BLOCKED)
    assert blocked.payload["reason"] == "interdictor_cruiser"

    # A corp mate is held. The cruiser itself is not.
    res = _act(u, mate.id, ActionKind.WARP, target=nxt)
    assert not res.ok
    assert mate.sector_id == sid
    res = _act(u, cruiser.id, ActionKind.WARP, target=nxt)
    assert res.ok, res.error
    assert cruiser.sector_id == nxt


def test_interdictor_holds_transwarp_and_allows_a_fighter_retreat(monkeypatch) -> None:
    _live_hulls(monkeypatch)
    u, (pilot, cruiser, _c) = _make_universe(seed=8602)
    sid = _first_non_fed_sector(u, 40)
    dest = _first_non_fed_sector(u, sid + 1)
    _link(u, sid, dest)
    _park(u, pilot, sid)
    _park(u, cruiser, sid)
    cruiser.ship.ship_class = ShipClass.INTERDICTOR_CRUISER
    pilot.ship.ship_class = ShipClass.IMPERIAL_STARSHIP
    pilot.ship.transwarp_drive = "type1"
    pilot.ship.cargo[Commodity.FUEL_ORE] = 50
    pilot.turns_today = 0
    pilot.turns_per_day = 1000
    res = handle_ship_transwarp(u, pilot.id, Action(kind=ActionKind.SHIP_TRANSWARP, args={"sector_id": dest}))
    assert not res.ok
    assert res.error == "an Interdictor Cruiser holds this sector"
    assert int(res.turns_spent or 0) == 0
    assert pilot.sector_id == sid
    assert pilot.ship.cargo[Commodity.FUEL_ORE] == 50

    u, _owner, ship, home, there = _challenge(8603)
    ic = u.players["C"]
    _park(u, ic, there)
    ic.ship.ship_class = ShipClass.INTERDICTOR_CRUISER
    # NOTE 96. v3.06: a fighter retreat is allowed when an IC is in the sector.
    spent = int(ship.turns_today)
    res = apply_action(u, ship.id, Action(kind=ActionKind.RETREAT, args={}))
    assert res.ok, res.error
    assert ship.sector_id == home
    assert ship.turns_today == spent + K.warp_turns(ship.ship.ship_class.value)
    assert ship.fighter_challenge is None
    assert home != there


def test_combat_flee_and_ferrengi_flee_are_held(monkeypatch) -> None:
    u, a, d, c, sid = _duel(8604)
    assert u.sectors[sid].warps
    _park(u, c, sid)
    c.ship.ship_class = ShipClass.INTERDICTOR_CRUISER
    a.ship.fighters = 500
    d.ship.fighters = 100
    d.ship.shields = 0
    res = _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=10)
    assert res.ok, res.error
    assert d.sector_id != sid

    u, a, d, c, sid = _duel(8605)
    _park(u, c, sid)
    c.ship.ship_class = ShipClass.INTERDICTOR_CRUISER
    a.ship.fighters = 500
    d.ship.fighters = 100
    d.ship.shields = 0
    _live_hulls(monkeypatch)
    res = _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=10)
    assert res.ok, res.error
    assert d.sector_id == sid
    facts = next(e for e in reversed(u.events) if e.kind is EventKind.COMBAT).payload
    assert facts["defender_fled"] is False

    # The attacker being an Interdictor still blocks a flee with the switch off.
    monkeypatch.setattr(K, "SPECIAL_HULL_RULES_MODE", "legacy")
    monkeypatch.setattr(K, "SHIP_ROSTER_MODE", "legacy")
    u, a, d, _c, sid = _duel(8606, a_hull=ShipClass.INTERDICTOR_CRUISER)
    a.ship.fighters = 500
    d.ship.fighters = 100
    d.ship.shields = 0
    res = _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=10)
    assert res.ok, res.error
    assert d.sector_id == sid

    u = _world(seed=8607)
    sid = next(s for s in u.sectors if s >= 20 and any(w not in K.FEDSPACE_SECTORS for w in u.sectors[s].warps))
    pilot = _add_player(u, "A", sector_id=sid, fighters=5)
    _park_ferr = _make_ferrengi(u, fid="e1", sid=sid, aggression=5)
    u.ferrengi = {"e1": _park_ferr}
    from tw2k.engine.ferrengi import open_ferrengi_encounter
    open_ferrengi_encounter(u, _park_ferr, pilot)
    cruiser = _add_player(u, "B", sector_id=sid, fighters=10)
    cruiser.ship.ship_class = ShipClass.INTERDICTOR_CRUISER
    monkeypatch.setattr(K, "FERRENGI_MODE", "tw2002")
    monkeypatch.setattr(K, "FERRENGI_ENCOUNTER", "tribute")
    res = apply_action(u, "A", Action(kind=ActionKind.RETREAT, args={}))
    assert res.ok, res.error
    assert pilot.sector_id != sid

    u = _world(seed=8608)
    sid = next(s for s in u.sectors if s >= 20 and any(w not in K.FEDSPACE_SECTORS for w in u.sectors[s].warps))
    pilot = _add_player(u, "A", sector_id=sid, fighters=5)
    ferr = _make_ferrengi(u, fid="e1", sid=sid, aggression=5)
    u.ferrengi = {"e1": ferr}
    open_ferrengi_encounter(u, ferr, pilot)
    cruiser = _add_player(u, "B", sector_id=sid, fighters=10)
    cruiser.ship.ship_class = ShipClass.INTERDICTOR_CRUISER
    _live_hulls(monkeypatch)
    res = apply_action(u, "A", Action(kind=ActionKind.RETREAT, args={}))
    assert not res.ok
    assert pilot.sector_id == sid


def test_tholian_defends_a_corp_planet_at_four_to_one(monkeypatch) -> None:
    def _fight(seed: int, *, ticker: str | None, planet_ticker: str | None):
        u, a, d, _c, sid = _duel(seed, d_hull=ShipClass.THOLIAN_SENTINEL)
        a.ship.fighters = 20
        a.ship.shields = 0
        d.ship.fighters = 10
        d.ship.shields = 0
        d.corp_ticker = ticker
        if planet_ticker is not None:
            planet = Planet(
                id=1, sector_id=sid, name="Yard", class_id=PlanetClass.M,
                owner_id=d.id, corp_ticker=planet_ticker,
            )
            u.planets[1] = planet
            u.sectors[sid].planet_ids.append(1)
        res = _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=20)
        assert res.ok, res.error
        rnd = next(e for e in reversed(u.events) if e.kind is EventKind.COMBAT).payload["rounds"][0]
        return a, d, rnd

    a, d, rnd = _fight(8610, ticker="ZZ", planet_ticker="ZZ")
    assert rnd["attacker_damage_mult"] == 1.0
    assert rnd["defender_damage_mult"] == 1.0
    assert rnd["attacker_fighters_lost"] == 10
    assert a.ship.fighters == 10

    _live_hulls(monkeypatch)
    a, d, rnd = _fight(8611, ticker="ZZ", planet_ticker="ZZ")
    assert rnd["attacker_damage_mult"] == 1.0
    assert rnd["defender_damage_mult"] == 4.0
    assert rnd["attacker_fighters_lost"] == 20
    assert rnd["defender_fighters_lost"] == 5
    assert a.ship.fighters == 0
    assert d.ship.fighters == 5

    a, _d, rnd = _fight(8612, ticker="ZZ", planet_ticker="YY")
    assert rnd["defender_damage_mult"] == 1.0
    assert rnd["attacker_fighters_lost"] == 10
    assert a.ship.fighters == 10

    _fight_off = _fight
    monkeypatch.setattr(K, "SHIP_ROSTER_MODE", "legacy")
    _a, _d, rnd = _fight_off(8613, ticker="ZZ", planet_ticker="ZZ")
    assert rnd["defender_damage_mult"] == 1.0
    assert rnd["attacker_damage_mult"] == 1.0


def test_grudge_memory_and_banding_follow_the_switch(monkeypatch) -> None:
    u = _world(seed=8620)
    for sid in (30, 31):
        _quiet(u, sid)
    u.sectors[30].warps = [31]
    u.sectors[31].warps = [30]
    ferr = _make_ferrengi(u, fid="e1", sid=30, aggression=3)
    ferr.fighters = 10
    u.ferrengi = {"e1": ferr}
    victim = _add_player(u, "A", sector_id=31, fighters=5)
    record_ferrengi_grudge(u, "A", "e1")
    assert "A" in u.ferrengi_grudges
    assert ferr.grudges == []
    assert preferred_ferrengi_dest(u, ferr, [31]) is None

    monkeypatch.setattr(K, "FERRENGI_GRUDGE_MODE", "live")
    record_ferrengi_grudge(u, "A", "e1")
    assert ferr.grudges == ["A"]
    assert preferred_ferrengi_dest(u, ferr, [31]) == 31
    _ferrengi_step(u, ferr, u.rng)
    assert ferr.sector_id == 31
    assert victim.sector_id == 31

    other = _make_ferrengi(u, fid="e2", sid=31, aggression=3)
    other.fighters = 10
    ferr.sector_id = 30
    ferr.grudges = []
    strong = _add_player(u, "B", sector_id=31, fighters=40)
    u.ferrengi["e2"] = other
    assert int(strong.ship.fighters) > int(ferr.fighters)
    assert preferred_ferrengi_dest(u, ferr, [31]) == 31
    strong.ship.fighters = 1
    assert preferred_ferrengi_dest(u, ferr, [31]) is None


def test_pace_replaces_the_daily_roll_and_regen_stays_daily(monkeypatch) -> None:
    u = _world(seed=8630)
    for sid in (30, 31, 32, 33):
        _quiet(u, sid)
        u.sectors[sid].warps = [30 + ((sid - 29) % 4)]
    # 30 -> 31 -> 32 -> 33 -> 30
    ferr = _make_ferrengi(u, fid="e1", sid=30, aggression=1)
    ferr.fighters = 0
    ferr.shields = 0
    u.ferrengi = {"e1": ferr}
    u.players = {}
    u._rng = _Clock()

    _ferrengi_regen(u)
    assert ferr.fighters == 600  # 20% of the assault trader's 3,000
    assert sum(1 for e in u.events if e.kind is EventKind.FERRENGI_REGEN) == 1

    _ferrengi_roam_and_hunt(u)
    assert sum(1 for e in u.events if e.kind is EventKind.FERRENGI_MOVE) == 1
    assert ferr.sector_id == 31

    monkeypatch.setattr(K, "FERRENGI_PACE_MODE", "live")
    ferr.sector_id = 30
    before = sum(1 for e in u.events if e.kind is EventKind.FERRENGI_MOVE)
    _ferrengi_roam_and_hunt(u)
    assert sum(1 for e in u.events if e.kind is EventKind.FERRENGI_MOVE) == before
    assert ferr.sector_id == 30

    monkeypatch.setattr(K, "TURN_REGEN_DAY_SECONDS", 90)
    settle_ferrengi_pace_day(u)
    assert sum(1 for e in u.events if e.kind is EventKind.FERRENGI_MOVE) == before + 3
    assert ferr.sector_id == 33
    assert ferr.fighters == 600
    assert sum(1 for e in u.events if e.kind is EventKind.FERRENGI_REGEN) == 1
