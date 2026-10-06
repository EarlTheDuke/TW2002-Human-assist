"""Focused Galactic Bank checks. No server, no paid call.

Prints bank_tax_scenario_lab: PASS when the spec's scene holds.
The day tick still grants +1 alignment at midnight before the tax, so a blue
seat who starts at 0 ends at 17 (1 + floor(25000/1500)) and a red seat who
must stay evil has to start at -2.
"""

from __future__ import annotations

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe, tick_day
from tw2k.engine.combat import _destroy_ship
from tw2k.engine.models import EventKind, Player, Ship, ShipClass


def _seat(uid: str, name: str, credits: int, alignment: int = 0) -> Player:
    player = Player(id=uid, name=name, ship=Ship(), credits=credits, alignment=alignment)
    player.sector_id = 1
    return player


def _put(u, player: Player) -> None:
    u.players[player.id] = player
    u.sectors[1].occupant_ids.append(player.id)


def main() -> None:
    u = generate_universe(GameConfig(
        seed=56, universe_size=20, max_days=6, enable_planets=False, enable_ferrengi=False,
    ))
    blue = _seat("B", "Blue", 1_000_000, 0)
    red = _seat("R", "Red", 2_000_000, -2)
    killer = _seat("K", "Kai", 0, 0)
    victim = _seat("V", "Vic", 500_000, 0)
    _put(u, blue)
    _put(u, red)
    _put(u, killer)
    _put(u, victim)

    refused = apply_action(u, "B", Action(kind=ActionKind.BANK_DEPOSIT, args={"amount": 600_000}))
    assert not refused.ok and refused.error == "the bank can accept 500,000 more", refused.error
    assert apply_action(u, "B", Action(kind=ActionKind.BANK_DEPOSIT, args={"amount": 500_000})).ok
    assert blue.credits == 500_000 and blue.bank_balance == 500_000

    tick_day(u)
    tax = next(e for e in reversed(u.events) if e.kind is EventKind.TAX_COLLECTED and e.actor_id == "B")
    assert tax.payload["tax"] == 25_000 and tax.payload["align_gain"] == 16, tax.payload
    assert blue.credits == 475_000 and blue.bank_balance == 500_000 and blue.alignment == 17
    assert red.credits == 2_000_000 and red.alignment == -1

    victim.credits = 500_000  # the tax scene above is blue and red; this seat's cash is the pod scene
    assert apply_action(u, "V", Action(kind=ActionKind.BANK_DEPOSIT, args={"amount": 200_000})).ok
    assert victim.credits == 300_000
    _destroy_ship(u, "V", "attack", killer_id="K", by_other=True)
    assert victim.credits == 0 and victim.bank_balance == 200_000 and killer.credits == 300_000
    assert victim.ship.ship_class is ShipClass.ESCAPE_POD
    victim.sector_id = 1
    if "V" not in u.sectors[1].occupant_ids:
        u.sectors[1].occupant_ids.append("V")
    assert apply_action(u, "V", Action(kind=ActionKind.BANK_WITHDRAW, args={"amount": 200_000})).ok
    bought = apply_action(u, "V", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": "scout_marauder"}))
    assert bought.ok, bought.error
    assert victim.ship.ship_class is not ShipClass.ESCAPE_POD

    victim.ship.ship_class = ShipClass.ESCAPE_POD
    victim.credits = 40_000
    before = killer.credits
    _destroy_ship(u, "V", "attack", killer_id="K", by_other=True)
    assert victim.credits == 0 and killer.credits == before
    assert victim.turns_today >= victim.turns_per_day  # Ship Destroyed

    rival = _seat("Z", "Zed", 0, 0)
    rival.bank_balance = 500_000
    _put(u, rival)
    blocked = apply_action(u, "B", Action(kind=ActionKind.BANK_TRANSFER, args={"to_player": "Z", "amount": 50_000}))
    assert not blocked.ok and blocked.error == "the bank can accept 0 more", blocked.error

    print("bank_tax_scenario_lab: PASS")
    print(f"blue tax {tax.payload['tax']} align_gain {tax.payload['align_gain']} "
          f"alignment {blue.alignment} balance {blue.bank_balance}")
    print(f"red credits {red.credits} alignment {red.alignment}")
    print(f"pod killer {300_000} then pod-on-pod killer delta 0; hull {victim.ship.ship_class.value}")


if __name__ == "__main__":
    main()
