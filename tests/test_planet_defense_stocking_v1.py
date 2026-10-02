"""Move fighters and shields between a landed ship and its planet."""

from __future__ import annotations

from tests.test_phase_abc import _make_universe
from tw2k.engine import constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import EventKind, Planet, PlanetClass
from tw2k.engine.observation import event_facts
from tw2k.engine.runner import apply_action

SECTOR = 120
COST = K.TURN_COST["deposit_planet_defense"]


def _stand(u, player) -> None:
    here = u.sectors[player.sector_id]
    if player.id in here.occupant_ids:
        here.occupant_ids.remove(player.id)
    player.sector_id = SECTOR
    player.planet_landed = None
    if player.id not in u.sectors[SECTOR].occupant_ids:
        u.sectors[SECTOR].occupant_ids.append(player.id)


def _world(seed: int = 9101):
    u, (owner, mate, outsider) = _make_universe(seed=seed)
    planet = Planet(
        id=91001, sector_id=SECTOR, name="Stock", class_id=PlanetClass.M,
        owner_id=owner.id, fighters=0, shields=0, citadel_level=0, citadel_target=0,
    )
    u.planets[planet.id] = planet
    u.sectors[SECTOR].planet_ids.append(planet.id)
    for player in (owner, mate, outsider):
        _stand(u, player)
    owner.planet_landed = planet.id
    owner.ship.fighters = 100
    owner.ship.shields = 100
    return u, owner, mate, outsider, planet


def _move(u, pid: str, kind: str, qty: int, *, direction: str = "deposit"):
    action = ActionKind.DEPOSIT_PLANET_DEFENSE if direction == "deposit" else ActionKind.WITHDRAW_PLANET_DEFENSE
    return apply_action(u, pid, Action(kind=action, args={"planet_id": 91001, "kind": kind, "qty": qty}))


def test_min_level_constant_is_zero() -> None:
    assert K.PLANET_DEFENSE_MIN_LEVEL == 0


def test_deposit_and_withdraw_fighters() -> None:
    u, owner, _, _, planet = _world()
    before = owner.turns_today
    res = _move(u, owner.id, "fighters", 40)
    assert res.ok, res.error
    assert res.turns_spent == COST
    assert owner.turns_today == before + COST
    assert owner.ship.fighters == 60
    assert planet.fighters == 40
    ev = next(e for e in u.events if e.kind is EventKind.PLANET_DEFENSE_TRANSFER)
    public = {"planet_id": 91001, "kind": "fighters", "qty": 40, "direction": "deposit"}
    assert {k: ev.payload[k] for k in public} == public
    assert set(ev.payload) <= set(public) | {"_witnesses"}
    assert event_facts(ev) == public

    back = _move(u, owner.id, "fighters", 10, direction="withdraw")
    assert back.ok, back.error
    assert planet.fighters == 30
    assert owner.ship.fighters == 70


def test_shields_move_ten_ship_shields_per_planet_shield() -> None:
    u, owner, _, _, planet = _world()
    owner.ship.shields = 15
    one = _move(u, owner.id, "shields", 1)
    assert one.ok, one.error
    assert owner.ship.shields == 5
    assert planet.shields == 1
    two = _move(u, owner.id, "shields", 2)
    assert two.ok is False
    assert "not enough shields" in (two.error or "")
    assert owner.ship.shields == 5 and planet.shields == 1

    owner.ship.shields = 390  # merchant cruiser cap is 400
    pulled = _move(u, owner.id, "shields", 1, direction="withdraw")
    assert pulled.ok, pulled.error
    assert owner.ship.shields == 400
    assert planet.shields == 0
    planet.shields = 1
    owner.ship.shields = 395
    blocked = _move(u, owner.id, "shields", 1, direction="withdraw")
    assert blocked.ok is False
    assert "shield cap" in (blocked.error or "")
    assert planet.shields == 1 and owner.ship.shields == 395


def test_refusals_for_landing_owner_caps_and_stock() -> None:
    u, owner, _, outsider, planet = _world()
    owner.planet_landed = None
    missed = _move(u, owner.id, "fighters", 1)
    assert missed.ok is False and missed.error == "must be landed on the planet first"
    assert owner.turns_today == 0

    owner.planet_landed = planet.id
    outsider.planet_landed = planet.id
    denied = _move(u, outsider.id, "fighters", 1)
    assert denied.ok is False and denied.error == "planet not owned by you or your corp"

    planet.fighters = K.PLANET_FIGHTER_CAP - 1
    owner.ship.fighters = 5
    over = _move(u, owner.id, "fighters", 2)
    assert over.ok is False and "cap" in (over.error or "")
    assert planet.fighters == K.PLANET_FIGHTER_CAP - 1

    planet.fighters = 0
    owner.ship.fighters = 3
    short = _move(u, owner.id, "fighters", 4)
    assert short.ok is False and short.error == "not enough fighters on the ship"

    planet.fighters = 4
    owner.ship.fighters = 0
    below = _move(u, owner.id, "fighters", 5, direction="withdraw")
    assert below.ok is False and below.error == "cannot take planet fighters below 0"
    assert planet.fighters == 4

    planet.fighters = 30
    owner.ship.fighters = 2490  # merchant cruiser fighter cap is 2500
    capped = _move(u, owner.id, "fighters", 20, direction="withdraw")
    assert capped.ok is False and "fighter cap" in (capped.error or "")


def test_corp_mate_can_deposit_and_an_outsider_cannot() -> None:
    u, owner, mate, outsider, planet = _world()
    planet.corp_ticker = "QQ"
    mate.corp_ticker = "QQ"
    mate.planet_landed = planet.id
    mate.ship.fighters = 12
    res = _move(u, mate.id, "fighters", 12)
    assert res.ok, res.error
    assert planet.fighters == 12
    outsider.planet_landed = planet.id
    outsider.ship.fighters = 8
    no = _move(u, outsider.id, "fighters", 1)
    assert no.ok is False
    assert planet.fighters == 12


def test_level_gate_follows_the_constant() -> None:
    u, owner, _, _, planet = _world()
    planet.citadel_level = 1
    old = K.PLANET_DEFENSE_MIN_LEVEL
    K.PLANET_DEFENSE_MIN_LEVEL = 2
    try:
        res = _move(u, owner.id, "fighters", 1)
        assert res.ok is False
        assert res.error == "planet citadel level is below the defense stocking minimum"
        la = {x.kind: x for x in legal_actions(u, owner.id)}["deposit_planet_defense"]
        assert la.legal is False and la.reason == res.error
    finally:
        K.PLANET_DEFENSE_MIN_LEVEL = old


def test_stocked_fighters_are_what_the_siege_fights() -> None:
    u, owner, _, outsider, planet = _world()
    owner.ship.fighters = 2000
    assert _move(u, owner.id, "fighters", 2000).ok
    owner.planet_landed = None
    outsider.ship.fighters = 20
    outsider.ship.shields = 0
    landed = apply_action(u, outsider.id, Action(
        kind=ActionKind.LAND_PLANET, args={"planet_id": planet.id},
    ))
    assert landed.ok, landed.error
    assert outsider.deaths == 1
    assert planet.owner_id == owner.id
    assert planet.fighters > 0
