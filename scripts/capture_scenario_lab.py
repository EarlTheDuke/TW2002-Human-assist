"""Focused capture checks. No server, no paid API.

    python scripts/capture_scenario_lab.py

(i) Boundary table: five hull pairs, qty = min-1 / min / min+1.
(ii)(iii) Cabal tow and MBBS addendum #6 need slice 51. This tree prints that they are skipped.
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
    print("\nCabal blockade (scout captures, tows to sector 1, sell): SKIPPED. Slice 51 tow is not on origin.")
    print("MBBS addendum #6 (capture a towed ship, tow continues, sell at StarDock): SKIPPED. Same reason.")


if __name__ == "__main__":
    main()
