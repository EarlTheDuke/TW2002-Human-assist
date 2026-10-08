"""Corp loose-ends scenario lab. No server, no paid call.

Prints corp_loose_ends_lab: PASS when the slice 64 scenes hold.
"""

from __future__ import annotations

from tw2k.engine import GameConfig, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.combat import _destroy_ship, _resolve_fighter_attack_tw2002, _resolve_ship_combat
from tw2k.engine.fleet import extern_repossess
from tw2k.engine.models import FighterDeployment, FighterMode, MineType, ParkedShip, Ship, ShipClass, TowLock
from tw2k.engine.runner import _apply_sector_hazards, apply_action
from tw2k.engine.scanners import limpet_visible


def _act(u, pid: str, verb: str, **args):
    return apply_action(u, pid, Action(kind=ActionKind(verb), args=args))


def _move(u, pid: str, sid: int) -> None:
    player = u.players[pid]
    here = u.sectors.get(player.sector_id)
    if here is not None and pid in here.occupant_ids:
        here.occupant_ids.remove(pid)
    player.sector_id = sid
    player.planet_landed = None
    u.sectors[sid].occupant_ids.append(pid)


def _park(u, owner: str, sector: int) -> int:
    hull = ShipClass.MERCHANT_CRUISER
    ship = Ship(ship_class=hull, name=f"{owner}-spare", holds=20, fighters=0)
    sid = max(u.parked_ships, default=0) + 1
    ship.fleet_id = sid
    u.parked_ships[sid] = ParkedShip(id=sid, owner_id=owner, sector_id=sector, ship=ship, parked_day=u.day)
    return sid


def main() -> None:
    u = generate_universe(GameConfig(
        seed=64, universe_size=90, max_days=6, turns_per_day=80,
        starting_credits=50_000, enable_ferrengi=False, enable_planets=True,
    ))
    for pid, name, align in (
        ("P1", "Ann", 400), ("P2", "Bo", -200), ("P3", "Cid", 10),
        ("P4", "Dee", 10), ("P5", "Ed", 10), ("P6", "Fay", 10),
    ):
        from tw2k.engine.models import Player
        u.players[pid] = Player(id=pid, name=name, agent_kind="external", sector_id=1, credits=50_000, alignment=align)
        u.sectors[1].occupant_ids.append(pid)
        u.players[pid].ship.fighters = 0
        u.players[pid].ship.shields = 0

    assert _act(u, "P1", "corp_create", ticker="XYZ", name="Mixed").ok
    assert _act(u, "P1", "corp_set_password", password="Zx9").ok
    assert _act(u, "P2", "corp_join", ticker="XYZ", password="Zx9").ok

    sid = _park(u, "P2", 1)
    u.players["P1"].ship.tow_lock = TowLock(kind="ship", ship_id=sid, engaged_day=u.day)
    taken = extern_repossess(u)
    assert taken == 0 and sid in u.parked_ships, "a mate hold keeps the spare over Extern"
    print(f"extern_hold survived ship {sid}")

    _move(u, "P1", 40)
    _move(u, "P2", 40)
    u.players["P1"].ship.mines[MineType.LIMPET] = 2
    assert _act(u, "P1", "deploy_mines", qty=1, kind="limpet", ownership="personal").ok
    assert _act(u, "P1", "deploy_mines", qty=1, kind="limpet", ownership="corporate").ok
    mines = u.sectors[40].mines
    personal = next(m for m in mines if not m.corp_ticker)
    corporate = next(m for m in mines if m.corp_ticker == "XYZ")
    assert limpet_visible(u, "P2", "P1", personal) is False
    assert limpet_visible(u, "P2", "P1", corporate) is True
    print("limpet_view mate sees corporate only")

    wrong = _act(u, "P3", "corp_join", ticker="XYZ", password="nope")
    right = _act(u, "P3", "corp_join", ticker="XYZ", password="Zx9")
    assert wrong.error == "wrong password" and right.ok and u.players["P3"].corp_ticker == "XYZ"
    print("password wrong then right joins")

    u.players["P2"].ship.corp_ticker = "XYZ"
    assert _act(u, "P2", "corp_leave").ok
    u.players["P2"].credits = 2_000_000
    _move(u, "P2", 1)
    refused = _act(u, "P2", "buy_ship", ship_class="scout_marauder")
    assert refused.error == "this is another corporation's ship - you cannot trade it in"
    print("ex_member trade-in refused")

    _move(u, "P1", 1)
    u.sectors[40].fighters = FighterDeployment(
        owner_id="P1", count=4, mode=FighterMode.TOLL, corp_ticker="XYZ", toll_credits=100,
    )
    assert _act(u, "P1", "corp_leave").ok
    dep = u.sectors[40].fighters
    assert dep.owner_id == K.ROGUE_OWNER_ID and dep.toll_credits == 100
    saved_combat = K.COMBAT_MODE
    K.COMBAT_MODE = "legacy"
    try:
        for payer in ("P5", "P6"):
            _move(u, payer, 40)
            before = u.players[payer].credits
            _apply_sector_hazards(u, payer, u.sectors[40])
            assert u.players[payer].credits < before
    finally:
        K.COMBAT_MODE = saved_combat
    pot = int(u.sectors[40].fighters.toll_credits)
    assert pot > 100
    u.players["P4"].ship.fighters = 40
    u.players["P4"].credits = 10
    assert _resolve_fighter_attack_tw2002(u, "P4", 40, 40)
    assert u.players["P4"].credits == 10 + pot
    assert u.sectors[40].fighters is None
    print(f"rogue_pot kept {pot} and paid to the destroyer")

    u.players["P4"].credits = 500
    u.players["P4"].ship.fighters = 1
    u.players["P4"].ship.shields = 0
    u.players["P1"].ship.fighters = 800
    u.players["P1"].ship.shields = 0
    u.players["P1"].credits = 10
    _move(u, "P4", u.players["P1"].sector_id)
    _resolve_ship_combat(u, "P4", u.players["P1"])
    assert u.players["P4"].credits == 0 and u.players["P1"].credits == 510
    print("return_fire paid the defender 500")

    u.players["P6"].credits = 100
    u.players["P6"].ship.fighters = 20
    u.players["P6"].ship.shields = 0
    u.players["P6"].ship.corbomite = 1
    u.players["P5"].credits = 40
    u.players["P5"].ship.fighters = 10
    u.players["P5"].ship.shields = 0
    _destroy_ship(u, "P6", reason="combat", killer_id="P5", by_other=True)
    assert u.players["P6"].alive and u.players["P6"].credits == 140 and u.players["P5"].credits == 0
    print("corbomite paid the podded owner once")
    print("corp_loose_ends_lab: PASS")


if __name__ == "__main__":
    main()
