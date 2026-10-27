"""v311-rulings-v1 (COMMANDER NOTE 57). Each RULINGS_v311.md ruling under V311_PROFILE.

Source: C:\\Users\\sugar\\tw2002_reference\\RULINGS_v311.md. Every test quotes its section.
Defaults stay legacy, so the bank pin and the 10-day digests do not move.

Plants:
  pb1 - the offensive wave is sized 1 x (max fighters + max shields) instead of 1.25 x.
  pb2 - recover_turns pays its own 250/86400 next to refresh_offline_turns (double regen).
NOTE 59 (v311-kill-cash-addendum-v1) plants:
  pb3 - kill_cash_held() drops `or v311_profile()`, so a kill under the profile pays the killer.
  pb4 - the pod top-up is skipped, so the pod after a kill holds 0 credits instead of 25.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tests.test_citadel_class_tables_v1 import _build, _fill, _land, _plant
from tests.test_phase_abc import _make_universe
from tests.test_ship_combat_core_v1 import _challenge, _duel
from tests.test_tw2002_live_profile_v1 import HELPERS
from tw2k.engine import GameConfig, generate_universe, tick_day
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.bank import collect_daily_tax, tax_on
from tw2k.engine.combat import _resolve_fighter_sector_combat, offensive_wave_size
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import (
    Commodity,
    EventKind,
    FighterDeployment,
    FighterMode,
    PlanetClass,
    Player,
    Ship,
    ShipClass,
)
from tw2k.engine.runner import apply_action, grant_starting_planet, recover_turns, refresh_offline_turns

pytestmark = pytest.mark.legacy_profile

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "plans" / "v311-profile-v1.md"


def _on(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")


def _universe(seed: int = 57):
    u = generate_universe(GameConfig(seed=seed, universe_size=40, max_days=12, turns_per_day=1000,
                                     starting_credits=20_000, enable_ferrengi=False, enable_planets=False))
    p = Player(id="P1", name="Seat", sector_id=1, credits=20_000, turns_per_day=250, ship=Ship())
    u.players["P1"] = p
    u.sectors[1].occupant_ids.append("P1")
    return u, p


def test_defaults_stay_legacy() -> None:
    assert K.V311_PROFILE == "legacy"
    assert K.v311_profile() is False
    assert K.TAX_RULE_MODE == "legacy"
    assert K.tax_v311() is False
    assert K.tax_terms() == (5, 100_000, 0)
    assert K.KILL_CASH_MODE == "legacy"
    assert K.kill_cash_held() is False
    assert K.POD_CASH_MODE == "legacy"
    assert K.pod_cash_live() is False
    assert K.DEATH_CREDITS_ON_HAND == "lost"
    assert K.CITADEL_COST_MODE == "credits"
    assert K.CITADEL_BUILD_TIME_SCALE == 0.25


def test_s2_starting_package(monkeypatch) -> None:
    """RULINGS s2: "Merchant Cruiser, 300 credits, 30 fighters, 20 holds, 0 shields,
    250 turns/day, plus a free class M start planet when "Start with planet = Yes"."
    """
    _on(monkeypatch)
    assert K.starting_package_live() is True
    assert K.opening_loadout(20_000, K.STARTING_TURNS_PER_DAY, 1) == (300, 250, 30)
    ship = Ship()
    assert ship.ship_class is ShipClass.MERCHANT_CRUISER
    assert ship.holds == 20
    assert ship.shields == 0
    assert K.ship_specs()["merchant_cruiser"]["holds"] == 20
    u, p = _universe()
    grant_starting_planet(u, p)
    owned = [pl for pl in u.planets.values() if pl.owner_id == "P1"]
    assert [pl.class_id.value for pl in owned] == ["M"]


RULINGS_S3_DAYS = {
    "M": (4, 4, 5, 10, 5, 15),
    "K": (6, 5, 8, 5, 4, 8),
    "O": (6, 5, 8, 5, 4, 8),
    "L": (2, 5, 5, 8, 5, 12),
    "C": (5, 5, 7, 5, 4, 8),
    "H": (4, 5, 8, 12, 5, 18),
    "U": (8, 4, 5, 5, 4, 8),
}


def test_s3_citadel_days_and_goods_cost(monkeypatch) -> None:
    """RULINGS s3: "Original answer (days for L1..L6, by planet class): M Earth: 4 / 4 / 5 / 10 / 5 / 15"
    and "CITADEL_DAYS_MODE="live" and CITADEL_BUILD_TIME_SCALE=1.0; also CITADEL_COST_MODE should
    use the class commodity table (no credits)."

    CITADEL_FIDELITY_MODE tw2002 (the default) already charges the class goods with no credits.
    CITADEL_COST_MODE "class" would take the hidden path that consumes colonists, so the profile
    leaves it at "credits" and citadel_fidelity_rules() stays True.
    """
    _on(monkeypatch)
    for cls, days in RULINGS_S3_DAYS.items():
        got = tuple(K.citadel_class_cost(cls, level)[4] for level in range(1, 7))
        assert got == days, cls
    assert K.citadel_fidelity_rules() is True
    u, (owner, *_) = _make_universe(seed=19057)
    planet = _plant(u, owner.id, class_id=PlanetClass.M, level=0)
    colonists, fuel, organics, equipment, days = K.citadel_class_cost("M", 1)
    assert (fuel, organics, equipment, days) == (300, 200, 250, 4)
    _fill(planet, colonists, fuel, organics, equipment)
    _land(u, owner, planet)
    owner.credits = 20_000
    res = _build(u, owner, planet.id)
    assert res.ok, res.error
    assert owner.credits == 20_000
    assert planet.stockpile[Commodity.FUEL_ORE] == 0
    assert planet.stockpile[Commodity.ORGANICS] == 0
    assert planet.stockpile[Commodity.EQUIPMENT] == 0
    assert planet.colonists[Commodity.COLONISTS] == colonists
    assert planet.citadel_complete_day == u.day + 4


RULINGS_S4 = {
    "merchant_cruiser": (41_300, 20, 75, 2_500, 3, 1.0),
    "scout_marauder": (15_950, 10, 25, 250, 2, 2.0),
    "missile_frigate": (100_800, 12, 60, 5_000, 3, 1.3),
    "battleship": (88_500, 16, 80, 10_000, 4, 1.6),
    "corporate_flagship": (163_500, 20, 85, 20_000, 3, 1.2),
    "colonial_transport": (63_600, 50, 250, 200, 6, 0.6),
    "cargotran": (51_950, 50, 125, 400, 4, 0.8),
    "merchant_freighter": (33_400, 30, 65, 300, 2, 0.8),
    "imperial_starship": (329_000, 40, 150, 50_000, 4, 1.5),
    "havoc_gunstar": (79_000, 12, 50, 10_000, 3, 1.2),
    "star_master": (61_300, 20, 73, 5_000, 3, 1.4),
    "constellation": (72_500, 20, 80, 5_000, 3, 1.4),
    "tkhasi_orion": (42_250, 30, 60, 750, 2, 1.1),
    "tholian_sentinel": (47_500, 10, 50, 2_500, 4, 1.0),
    "taurean_mule": (63_600, 50, 150, 300, 4, 0.5),
    "interdictor_cruiser": (539_000, 10, 40, 100_000, 15, 1.2),
}


def _row(spec: dict) -> tuple:
    return (spec["cost"], spec["holds"], spec["max_holds"], spec["max_fighters"],
            spec["turns_per_warp"], spec["offensive_odds"])


def test_s4_full_ship_roster(monkeypatch) -> None:
    """RULINGS s4: "Original answer (base cost / initial-max holds / max fighters / turns per warp /
    offensive odds), from the real v3.34b shipyard catalog" - 17 hulls, e.g. "Escape Pod 14,446 |
    1-5 | 50 | 6 | 0.8" and "T'Khasi Orion 42,250 | 30-60 | 750 | 2 | 1.1"; "load the full table above".
    """
    legacy = {k: _row(v) for k, v in K.ship_specs().items()}
    assert legacy["scout_marauder"][1] == 25
    _on(monkeypatch)
    specs = K.ship_specs()
    assert set(specs) == set(RULINGS_S4)
    for key, row in RULINGS_S4.items():
        assert _row(specs[key]) == row, key
        assert K.ship_cost(key) == row[0], key
    assert _row(K.hull_spec(K.ESCAPE_POD)) == (14_446, 1, 5, 50, 6, 0.8)
    assert K.ship_cost(K.ESCAPE_POD) == 0
    assert len(RULINGS_S4) + 1 == 17


def test_s5_hourly_regen_capped_without_a_midnight_refill(monkeypatch) -> None:
    """RULINGS s5: "turns come back hourly, pro-rated from the daily allowance (about
    turns_per_day / 24 per hour), capped at the daily allowance; no midnight full refill".

    The two engine paths share one clock: the scheduler's recover_turns and apply_action's
    refresh_offline_turns never both pay the same seconds, and many short calls add up.
    """
    _on(monkeypatch)
    assert K.turn_regen_live() and K.live_pace() and K.starting_package_live()
    clock = {"now": 0.0}
    monkeypatch.setattr("time.time", lambda: clock["now"])
    u, p = _universe()
    p.turns_today = 200
    refresh_offline_turns(p)
    clock["now"] = 3600.0
    assert recover_turns(p, 3600.0) == 10  # 250 / 24 = 10.4 an hour, the fraction carries
    res = apply_action(u, p.id, Action(kind=ActionKind.WAIT, args={}))
    assert res.ok
    assert p.turns_today == 190 + res.turns_spent  # apply_action paid nothing again
    before = p.turns_today
    for step in range(1, 3601):
        clock["now"] = 3600.0 + step
        recover_turns(p, 1.0)
    assert before - p.turns_today in (10, 11)
    clock["now"] += 30 * 86_400
    recover_turns(p, 30 * 86_400.0)
    assert p.turns_today == 0  # capped at the daily allowance
    p.turns_today = 40
    tick_day(u)
    assert p.turns_today == 40  # no midnight refill


def test_s5_a_seat_short_of_a_warp_rests_until_turns_pool(monkeypatch) -> None:
    """RULINGS s5: "you will recover spent turns every hour" (EIS GeneralUpdated). Turns come
    back one at a time, so a seat short of a warp rests instead of spending each returned turn
    on a wait (the soak's day-2 stall). Off, the trade-cost safety net is unchanged."""
    from tw2k.server.runner import _is_day_done

    p = Player(id="P1", name="Seat", turns_per_day=250, ship=Ship())
    p.turns_today = 249
    legacy = _is_day_done(p)
    _on(monkeypatch)
    assert _is_day_done(p) is True
    p.turns_today = 247
    assert _is_day_done(p) is False
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    p.turns_today = 249
    assert _is_day_done(p) is legacy


def _clash(monkeypatch, stack: int, shields: int, fighters: int):
    _on(monkeypatch)
    u, p = _universe(seed=5757)
    u.players["P9"] = Player(id="P9", name="Owner", sector_id=1, ship=Ship())
    u.sectors[1].occupant_ids.append("P9")
    sid = next(s for s in u.sectors if s > 10)
    u.sectors[1].occupant_ids.remove("P1")
    p.sector_id = sid
    u.sectors[sid].occupant_ids.append("P1")
    p.ship.shields, p.ship.fighters = shields, fighters
    u.sectors[sid].fighters = FighterDeployment(owner_id="P9", count=stack, mode=FighterMode.OFFENSIVE)
    deaths = p.deaths
    _resolve_fighter_sector_combat(u, "P1", sid)
    return u, p, u.sectors[sid], p.deaths - deaths


def test_s6_offensive_wave_cap(monkeypatch) -> None:
    """RULINGS s6: "offensive sector fighters attack an entering ship at 1:1 odds, sending 1.25 x
    (the ship's MAX fighters + MAX shields), or all they have if fewer; fighters not used or
    surviving stay in the sector; afterwards they act as defenders."
    """
    _on(monkeypatch)
    mc = K.ship_specs()["merchant_cruiser"]
    wave = offensive_wave_size(Ship())
    assert wave == -(-(mc["max_fighters"] + mc["max_shields"]) * 5 // 4) == 3_625
    # A small stack sends all it has; the ship survives and the stack is gone.
    _, p, sector, died = _clash(monkeypatch, stack=300, shields=100, fighters=500)
    assert (p.ship.shields, p.ship.fighters, sector.fighters, died) == (0, 300, None, 0)
    # A big stack sends the capped wave; leftovers stay and the ship is destroyed.
    _, p, sector, died = _clash(monkeypatch, stack=10_000, shields=100, fighters=500)
    assert died == 1
    assert sector.fighters is not None and sector.fighters.count == 10_000 - 600
    # A wave exactly the ship's shields plus fighters cancels out at 1:1: the ship lives, empty.
    _, p, sector, died = _clash(monkeypatch, stack=2_900, shields=400, fighters=2_500)
    assert (p.ship.shields, p.ship.fighters, died) == (0, 0, 0)
    assert sector.fighters is None


def test_s7_tax(monkeypatch) -> None:
    """RULINGS s7: "good traders (alignment above 0) carrying over 49,999 credits on the ship pay 10%
    of the cash on hand, once per day when they enter; +1 alignment per 1,500 credits paid; evil
    traders are never taxed. MBBS mode uses 5% over 100,000 (not the default)."
    """
    p = Player(id="P1", name="Seat", alignment=0, credits=100_001)
    assert tax_on(p) == (5_000, 3)  # legacy MBBS figures
    assert tax_on(p, 100_000) == (0, 0)
    _on(monkeypatch)
    assert K.tax_terms() == (10, 49_999, 1)
    assert tax_on(p, 60_000) == (0, 0)  # alignment 0 is not positive
    p.alignment = 1
    assert tax_on(p, 60_000) == (6_000, 4)  # the live confirmation case in s7
    assert tax_on(p, 50_000) == (5_000, 3)
    assert tax_on(p, 49_999) == (0, 0)
    p.alignment = -5
    assert tax_on(p, 900_000) == (0, 0)
    u, seat = _universe()
    seat.alignment, seat.credits = 10, 60_000
    collect_daily_tax(u)
    taxes = [ev for ev in u.events if ev.kind is EventKind.TAX_COLLECTED]
    assert [ev.payload["tax"] for ev in taxes] == [6_000]
    assert seat.credits == 54_000 and seat.alignment == 14


def _kill(monkeypatch, seed: int):
    u, killer, victim, _c, sid = _duel(seed)
    killer.ship.fighters, killer.credits, killer.ship.holds = 2_000, 300, 20
    victim.ship.fighters, victim.ship.shields, victim.ship.holds = 30, 0, 20
    victim.credits = 10_000
    deaths = victim.deaths
    res = apply_action(u, killer.id, Action(kind=ActionKind.ATTACK, args={"target": victim.id, "qty": 200}))
    assert res.ok, res.error
    assert victim.deaths == deaths + 1
    return u, killer, victim


def test_addendum_a_kill_pays_the_killer_nothing_and_the_pod_has_25(monkeypatch) -> None:
    """RULINGS Addendum A (live v3.34b, trials T1 and T6): "in normal play the killer gets nothing
    from a logged-off victim, and the victim's on-hand cash is destroyed (the pod has 25 credits)";
    "the killer took the victim's 7 extra holds ("7 empty"). Keep the holds-salvage path."
    """
    u, killer, victim = _kill(monkeypatch, 59001)  # profile off: the old game pays the killer
    assert killer.credits == 300 + 10_000 and victim.credits == 0
    _on(monkeypatch)
    assert K.kill_cash_held() and K.pod_cash_live()
    assert K.KILL_CASH_MODE == "legacy" and K.POD_CASH_MODE == "legacy"
    assert K.DEATH_CREDITS_ON_HAND == "lost"
    u, killer, victim = _kill(monkeypatch, 59001)
    assert killer.credits == 300  # "Killer paid 0 (300 -> 300)"
    assert victim.ship.ship_class is ShipClass.ESCAPE_POD
    assert victim.credits == K.POD_CASH_CREDITS == 25  # "pod, 25 cr"
    assert not [e for e in u.events if e.kind is EventKind.CREDITS_RECOVERED]
    lost = [e for e in u.events if e.kind is EventKind.SHIP_DESTROYED and e.payload.get("victim") == victim.id]
    assert lost[-1].payload["credits_lost"] == 10_000
    furb = [e for e in u.events if e.kind is EventKind.SHIP_FURBED]
    assert furb and furb[-1].payload["holds_gained"] == 7  # "salvaged these cargo holds: 7 empty"
    assert killer.ship.holds == 27


def test_addendum_a_no_shared_sector_the_challenge_answers(monkeypatch) -> None:
    """RULINGS Addendum A Q6(b): "Fighters: 5 (belong to Ktvictim) [Defensive] / You have to destroy
    the fighters to remain in this sector." The help lists "<A> Attack Deployed Fighters", "<P> Pay
    Toll (if applicable)", "<R> RETREAT", "<S> Surrender your ship"; the defensive prompt is
    "Option? (A,D,I,R,S,?)". So a non-corp player cannot stay without clearing them.
    """
    _on(monkeypatch)
    from tw2k.engine.runner import CHALLENGE_REFUSAL, CHALLENGE_VERBS

    free = {ActionKind.WAIT, ActionKind.HAIL, ActionKind.BROADCAST, ActionKind.RADIO, ActionKind.QUERY_LIMPETS}
    answers = {k.value for k in CHALLENGE_VERBS - free}
    assert answers == {"attack", "pay_toll", "retreat", "surrender"}
    assert CHALLENGE_REFUSAL == "answer the fighters first: attack, retreat, pay the toll or surrender"
    for mode, toll_legal in (("defensive", False), ("toll", True)):
        u, owner, ship, home, there = _challenge(59002, mode=mode, count=5)
        assert ship.fighter_challenge and ship.fighter_challenge["mode"] == mode
        las = {la.kind: la for la in legal_actions(u, ship.id)}
        assert las["attack"].legal and las["retreat"].legal and las["surrender"].legal
        assert las["pay_toll"].legal is toll_legal, mode  # "Pay Toll (if applicable)"
        for kind in ("warp", "scan", "trade", "land_planet", "deploy_fighters"):
            assert not las[kind].legal, (mode, kind)
        assert not apply_action(u, ship.id, Action(kind=ActionKind.SCAN, args={})).ok
        assert ship.sector_id == there and ship.fighter_challenge is not None
        tick_day(u)  # waiting out the day does not let it stay
        assert ship.sector_id == home and ship.fighter_challenge is None


def test_addendum_a_fighter_exchange_is_one_to_one(monkeypatch) -> None:
    """RULINGS Addendum A Q6(b): "How many fighters do you wish to use (0 to 750) [0]? 10 /
    You lost 5 fighter(s) / You destroyed 5 enemy fighters. / You destroyed all the fighters."
    """
    _on(monkeypatch)
    u, owner, ship, home, there = _challenge(59003, count=5)
    assert ship.ship.ship_class is ShipClass.MERCHANT_CRUISER
    ship.ship.fighters = 1_990
    res = apply_action(u, ship.id, Action(kind=ActionKind.ATTACK, args={"target": "fighters", "qty": 10}))
    assert res.ok, res.error
    assert ship.ship.fighters == 1_985  # "You lost 5 fighter(s)"
    assert u.sectors[there].fighters is None  # "You destroyed all the fighters."
    assert ship.fighter_challenge is None
    u, owner, ship, home, there = _challenge(59004, count=50)
    ship.ship.fighters = 30
    assert apply_action(u, ship.id, Action(kind=ActionKind.ATTACK, args={"target": "fighters", "qty": 30})).ok
    assert ship.ship.fighters == 0 and u.sectors[there].fighters.count == 20  # 30 for 30


def test_profile_sets_exactly_the_documented_set(monkeypatch) -> None:
    """NOTE 57 item 8: V311_PROFILE turns on items 1-6 plus every MASTER_PLAN yes switch, and
    nothing else. docs/plans/v311-profile-v1.md lists the same switches."""
    off = {name: getattr(K, name)() for name in K.V311_PROFILE_HELPERS}
    assert [n for n, v in off.items() if v] == ["citadel_fidelity_rules"]
    _on(monkeypatch)
    assert all(getattr(K, name)() for name in K.V311_PROFILE_HELPERS)
    others = [n for n in HELPERS if n not in K.V311_PROFILE_HELPERS and getattr(K, n)()]
    assert others == []
    assert K.rank_display() == "exp"
    assert K.planet_value_score_mode() == "experience"
    assert K.TW2002_LIVE_PROFILE == "legacy"
    text = PLAN.read_text(encoding="utf-8")
    for name, (switch, _) in K.V311_PROFILE_HELPERS.items():
        assert f"`{switch}`" in text, switch
        assert f"`{name}`" in text, name


def test_the_live_profile_does_not_turn_on_the_v311_profile(monkeypatch) -> None:
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    assert K.v311_profile() is False
    assert K.V311_PROFILE == "legacy"
