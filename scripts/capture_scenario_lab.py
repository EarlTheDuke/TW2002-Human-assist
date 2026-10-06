"""Focused capture checks. No server, no paid API.

    python scripts/capture_scenario_lab.py

(i) Boundary table: five hull pairs, qty = min-1 / min / min+1.
(ii) Cabal blockade: a Scout captures an arriving Merchant Cruiser at min qty, tows it to sector 1, sells it.
(iii) MBBS addendum #6: A tows its unmanned Merchant Freighter through B's sector, B captures it with one
fighter and goes to sector 1, A keeps towing into sector 1, B sells it out from under him.
A 30-day invariant pass is scripts/run_match_headless.py (this file only prints the table).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fractions import Fraction  # noqa: E402

import tw2k.engine.constants as K  # noqa: E402
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe  # noqa: E402
from tw2k.engine.capture import min_capture_qty  # noqa: E402
from tw2k.engine.combat import _odds, combat_odds_of  # noqa: E402
from tw2k.engine.fleet import _new_ship_id  # noqa: E402
from tw2k.engine.models import EventKind, ParkedShip, Player, Ship, ShipClass  # noqa: E402


def _world():
    return generate_universe(GameConfig(seed=11, universe_size=40, enable_ferrengi=False, enable_planets=False))


def _sector(u):
    return next(s for s in sorted(u.sectors) if int(s) > 10)


def _sit(u, pid, sector, hull, fighters, shields=0):
    if pid not in u.players:
        u.players[pid] = Player(id=pid, name=pid, ship=Ship(), sector_id=1)
        u.sectors[1].occupant_ids.append(pid)
    p = u.players[pid]
    if pid in u.sectors[p.sector_id].occupant_ids:
        u.sectors[p.sector_id].occupant_ids.remove(pid)
    p.sector_id = int(sector)
    p.ship = Ship(ship_class=hull, fighters=int(fighters), shields=int(shields),
                  holds=int((K.hull_spec(hull.value) or {}).get("holds", 20)))
    p.turns_today = 0
    p.turns_per_day = 1000
    p.alive = True
    if pid not in u.sectors[int(sector)].occupant_ids:
        u.sectors[int(sector)].occupant_ids.append(pid)
    return p


def _outcome(u, corbomite_before):
    captured = any(e.kind == EventKind.SHIP_CAPTURED for e in u.events)
    destroyed = any(e.kind in (EventKind.SHIP_DESTROYED, EventKind.UNMANNED_SHIP_DESTROYED) for e in u.events)
    blast = any(e.kind == EventKind.CORBOMITE_BLAST for e in u.events[corbomite_before:])
    if captured:
        return "captured", blast
    if destroyed:
        return "destroyed", blast
    return "not beaten", blast


def _row(label, att_hull, def_hull, fighters, shields, unmanned=False):
    print(f"\n{label}")
    for delta, name in ((-1, "min-1"), (0, "min"), (1, "min+1")):
        u = _world()
        sec = _sector(u)
        a = _sit(u, "A", sec, att_hull, 500)
        if unmanned:
            ship = Ship(ship_class=def_hull, fighters=fighters, shields=shields, corbomite=1,
                        holds=int((K.hull_spec(def_hull.value) or {}).get("holds", 20)))
            sid = _new_ship_id(u)
            ship.fleet_id = sid
            u.parked_ships[sid] = ParkedShip(id=sid, owner_id="B", sector_id=int(sec), ship=ship, parked_day=u.day)
            _sit(u, "B", 40, ShipClass.MERCHANT_CRUISER, 0)
            a_odds = combat_odds_of(a)
            d_odds = _odds(K.combat_hull(def_hull.value)[0]) * Fraction(str(K.FLEET_UNMANNED_ODDS_FACTOR))
            defense = (shields + fighters) * d_odds
            target = f"ship:{sid}"
        else:
            b = _sit(u, "B", sec, def_hull, fighters, shields)
            b.ship.corbomite = 1
            a_odds = combat_odds_of(a)
            defense = (shields + fighters) * combat_odds_of(b)
            target = "B"
        need = min_capture_qty(defense, a_odds)
        qty = need + delta
        before_f = a.ship.fighters
        mark = len(u.events)
        if qty < 1:
            print(f"  {name}: qty {qty} skipped (below 1)")
            continue
        res = apply_action(u, "A", Action(kind=ActionKind.ATTACK, args={"target": target, "qty": qty}))
        kind, blast = _outcome(u, mark)
        lost = before_f - a.ship.fighters
        print(f"  {name}: qty {qty} (min {need}) -> {kind}, attacker lost {lost}, corbomite {blast}, ok {res.ok}")


def main() -> None:
    pairs = [
        ("MC vs empty MC", ShipClass.MERCHANT_CRUISER, ShipClass.MERCHANT_CRUISER, 0, 0, False),
        ("BS vs MF 100f", ShipClass.BATTLESHIP, ShipClass.MERCHANT_FREIGHTER, 100, 0, False),
        ("MC vs CT 200f/100s", ShipClass.MERCHANT_CRUISER, ShipClass.COLONIAL_TRANSPORT, 200, 100, False),
        ("MC vs Scout (never)", ShipClass.MERCHANT_CRUISER, ShipClass.SCOUT_MARAUDER, 0, 0, False),
        ("BS vs unmanned MF 20f", ShipClass.BATTLESHIP, ShipClass.MERCHANT_FREIGHTER, 20, 0, True),
    ]
    print("Boundary table (corbomite should fire only on a destroy)")
    for row in pairs:
        _row(*row)
    if not K.tow_on():
        print("\nCabal blockade / MBBS addendum #6: SKIPPED (TOW_MODE legacy).")
        return
    _cabal_blockade()
    _mbbs_addendum_6()


def _path(u, start, goal):
    """Shortest warp path start -> goal (BFS, sorted, no rng)."""
    prev = {int(start): None}
    todo = [int(start)]
    while todo:
        cur = todo.pop(0)
        if cur == int(goal):
            break
        for w in sorted(u.sectors[cur].warps):
            if int(w) not in prev:
                prev[int(w)] = cur
                todo.append(int(w))
    out, cur = [], int(goal)
    while cur is not None and cur != int(start):
        out.append(cur)
        cur = prev.get(cur)
    return list(reversed(out))


def _do(u, pid, kind, **args):
    return apply_action(u, pid, Action(kind=kind, args=args))


def _far_sector(u, hops_min=2):
    for s in sorted(u.sectors):
        if int(s) not in K.FEDSPACE_SECTORS and len(_path(u, s, 1)) >= hops_min:
            return int(s)
    raise SystemExit("no sector far enough from StarDock")


def _cabal_blockade():
    print("\n(ii) Cabal blockade: Scout captures an arriving Merchant Cruiser, tows it to sector 1, sells it")
    u = _world()
    sec = _far_sector(u)
    a = _sit(u, "A", sec, ShipClass.SCOUT_MARAUDER, 25)
    b = _sit(u, "B", sec, ShipClass.MERCHANT_CRUISER, 30, 10)
    need = min_capture_qty((30 + 10) * combat_odds_of(b), combat_odds_of(a))
    turns0, credits0 = a.turns_today, a.credits
    res = _do(u, "A", ActionKind.ATTACK, target="B", qty=need)
    rec = next((r for r in u.parked_ships.values() if r.owner_id == "A"), None)
    print(f"  attack qty {need}: ok {res.ok}, captured {rec is not None}, B now in {b.ship.ship_class.value}")
    if rec is None:
        return
    print(f"  tow_engage: ok {_do(u, 'A', ActionKind.TOW_ENGAGE, target=f'ship:{rec.id}').ok}")
    route = _path(u, a.sector_id, 1)
    for hop in route:
        r = _do(u, "A", ActionKind.WARP, target=hop)
        if not r.ok:
            print(f"  warp {hop} refused: {r.error}")
            return
    print(f"  towed {len(route)} hops to sector {a.sector_id}; hull now in {rec.sector_id}")
    sold = _do(u, "A", ActionKind.SELL_SHIP, ship_id=rec.id)
    print(f"  sell_ship: ok {sold.ok}, +{a.credits - credits0} credits, {a.turns_today - turns0} turns in all"
          f" (trade_in_credit {K.trade_in_credit('merchant_cruiser')})")


def _mbbs_addendum_6():
    print("\n(iii) MBBS addendum #6: B captures A's towed Merchant Freighter with 1 fighter, A tows it to sector 1, B sells")
    from tw2k.engine.tow import lock_of
    u = _world()
    y = _far_sector(u, 3)
    x = next(int(w) for w in sorted(u.sectors[y].warps) if int(w) not in K.FEDSPACE_SECTORS)
    a = _sit(u, "A", x, ShipClass.MERCHANT_CRUISER, 10)
    b = _sit(u, "B", y, ShipClass.MERCHANT_CRUISER, 20)
    ship = Ship(ship_class=ShipClass.MERCHANT_FREIGHTER, name="A-freighter", fighters=0,
                holds=int((K.hull_spec("merchant_freighter") or {}).get("holds", 20)))
    sid = _new_ship_id(u)
    ship.fleet_id = sid
    u.parked_ships[sid] = ParkedShip(id=sid, owner_id="A", sector_id=x, ship=ship, parked_day=u.day)
    print(f"  A tow_engage: ok {_do(u, 'A', ActionKind.TOW_ENGAGE, target=f'ship:{sid}').ok}")
    print(f"  A warps {x} -> {y} (B's sector): ok {_do(u, 'A', ActionKind.WARP, target=y).ok}")
    res = _do(u, "B", ActionKind.ATTACK, target=f"ship:{sid}", qty=1)
    told = any(e.kind == EventKind.TOW_TARGET_CAPTURED for e in u.events)
    print(f"  B attacks with 1 fighter: ok {res.ok}, owner now {u.parked_ships[sid].owner_id}, "
          f"A still locked {lock_of(a.ship) is not None}, A told {told}")
    for hop in _path(u, y, 1):
        _do(u, "B", ActionKind.WARP, target=hop)
    hops = _path(u, y, 1)
    for hop in hops:
        r = _do(u, "A", ActionKind.WARP, target=hop)
        if not r.ok:
            print(f"  A warp {hop} refused: {r.error}")
            return
    engaged = lock_of(a.ship) is not None
    print(f"  A towed {len(hops)} hops: A in {a.sector_id}, hull in {u.parked_ships[sid].sector_id}, "
          f"tow engaged {engaged}, owner {u.parked_ships[sid].owner_id}; B in {b.sector_id}")
    c0 = b.credits
    sold = _do(u, "B", ActionKind.SELL_SHIP, ship_id=sid)
    reasons = [e.payload.get("reason") for e in u.events if e.kind == EventKind.TOW_RELEASED]
    print(f"  B sell_ship: ok {sold.ok}, +{b.credits - c0} credits; A locked {lock_of(a.ship) is not None}; "
          f"tow released reasons {reasons}")


if __name__ == "__main__":
    main()
