"""Move credits into a citadel treasury, and pay daily interest."""

from __future__ import annotations

from tests.test_phase_abc import _make_universe
from tests.test_siege_path_v1 import _land, _place, _planet
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.constants import PLANET_TREASURY_CAP, PLANET_TREASURY_INTEREST_PCT, TURN_COST
from tw2k.engine.models import EventKind
from tw2k.engine.observation import build_observation, event_facts
from tw2k.engine.runner import apply_action, tick_day

SECTOR = 120
COST = TURN_COST["deposit_treasury"]


def _bank(seed: int = 9101, *, level: int = 1, treasury: int = 0, credits: int = 5000):
    u, (owner, mate, outsider) = _make_universe(seed=seed)
    planet = _planet(91001, fighters=0, shields=0, level=level, treasury=treasury)
    planet.owner_id = owner.id
    planet.corp_ticker = "QQ"
    planet.citadel_target = level
    _place(u, planet, owner)
    owner.planet_landed = planet.id
    owner.credits = credits
    mate.corp_ticker = "QQ"
    for player in (mate, outsider):
        player.sector_id = SECTOR
        if player.id not in u.sectors[SECTOR].occupant_ids:
            u.sectors[SECTOR].occupant_ids.append(player.id)
    return u, owner, mate, outsider, planet


def _move(u, pid: str, amount: int, *, direction: str = "deposit"):
    kind = ActionKind.DEPOSIT_TREASURY if direction == "deposit" else ActionKind.WITHDRAW_TREASURY
    return apply_action(u, pid, Action(kind=kind, args={"planet_id": 91001, "amount": amount}))


def test_deposit_and_withdraw() -> None:
    u, owner, _, outsider, planet = _bank()
    before = owner.turns_today
    res = _move(u, owner.id, 400)
    assert res.ok, res.error
    assert owner.credits == 4600
    assert planet.treasury == 400
    assert owner.turns_today == before + COST
    ev = next(e for e in u.events if e.kind is EventKind.PLANET_TREASURY)
    assert event_facts(ev) == {"planet_id": 91001, "direction": "deposit", "amount": 400}
    assert "treasury" not in ev.payload or set(ev.payload) <= {"planet_id", "direction", "amount", "_witnesses"}
    hidden = next(p for p in build_observation(u, outsider.id).sector["planets"] if p["id"] == 91001)
    assert "treasury" not in hidden

    back = _move(u, owner.id, 150, direction="withdraw")
    assert back.ok, back.error
    assert planet.treasury == 250
    assert owner.credits == 4750


def test_refusals() -> None:
    u, owner, _, outsider, planet = _bank(level=0, credits=100)
    missed = _move(u, owner.id, 10)
    owner.planet_landed = None
    # level check happens after landed. Put them back for the level case.
    owner.planet_landed = planet.id
    low = _move(u, owner.id, 10)
    assert low.ok is False and low.error == "treasury requires citadel level 1"
    assert owner.turns_today == 0

    planet.citadel_level = 1
    owner.planet_landed = None
    away = _move(u, owner.id, 10)
    assert away.ok is False and away.error == "must be landed on the planet first"

    owner.planet_landed = planet.id
    outsider.planet_landed = planet.id
    denied = _move(u, outsider.id, 10)
    assert denied.ok is False and denied.error == "planet not owned by you or your corp"

    owner.credits = 30
    short = _move(u, owner.id, 40)
    assert short.ok is False and short.error == "not enough credits"
    assert planet.treasury == 0

    owner.credits = 50
    planet.treasury = PLANET_TREASURY_CAP - 10
    over = _move(u, owner.id, 11)
    assert over.ok is False and "cap" in (over.error or "")
    assert planet.treasury == PLANET_TREASURY_CAP - 10

    planet.treasury = 8
    below = _move(u, owner.id, 9, direction="withdraw")
    assert below.ok is False and below.error == "cannot take planet treasury below 0"
    assert planet.treasury == 8
    assert missed.ok is False


def test_corp_mate_can_deposit() -> None:
    u, _, mate, _, planet = _bank(treasury=20)
    mate.planet_landed = planet.id
    mate.credits = 80
    res = _move(u, mate.id, 15)
    assert res.ok, res.error
    assert planet.treasury == 35


def test_interest_on_the_day_tick_and_capture_halves_treasury() -> None:
    assert PLANET_TREASURY_INTEREST_PCT == 2
    u, owner, _, _, planet = _bank(treasury=1000, level=2)
    tick_day(u)
    assert planet.treasury == 1020
    planet.citadel_level = 0
    planet.treasury = 1000
    tick_day(u)
    assert planet.treasury == 1000
    planet.citadel_level = 2
    planet.treasury = PLANET_TREASURY_CAP - 5
    tick_day(u)
    assert planet.treasury == PLANET_TREASURY_CAP

    u, (attacker, *_) = _make_universe(seed=9108)
    attacker.ship.fighters = 1000
    attacker.ship.shields = 0
    held = _planet(91008, fighters=10, shields=0, treasury=80)
    _place(u, held, attacker)
    taken = _land(u, attacker.id, held.id)
    assert taken.ok, taken.error
    assert held.treasury == 40


def test_empty_ship_is_repelled_by_shields_and_destroyed_by_fighters() -> None:
    u, (attacker, *_) = _make_universe(seed=9109)
    attacker.ship.fighters = 0
    attacker.ship.shields = 0
    shields = _planet(91009, fighters=0, shields=40)
    _place(u, shields, attacker)
    blocked = _land(u, attacker.id, shields.id)
    assert blocked.ok is False
    assert blocked.error == "planetary defenses repelled landing"
    assert attacker.deaths == 0
    assert attacker.ship.fighters == 0
    assert shields.shields == 40
    assert shields.owner_id == "B"
    assert attacker.planet_landed is None

    u, (attacker, *_) = _make_universe(seed=9110)
    attacker.ship.fighters = 0
    fighters = _planet(9110, fighters=12, shields=0)
    _place(u, fighters, attacker)
    lost = _land(u, attacker.id, fighters.id)
    assert lost.ok is True
    assert attacker.deaths == 1
    assert fighters.owner_id == "B"
