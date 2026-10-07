"""Scripted Tavern and Underground lab. No LLM. docs/playtests/fedspace/STARDOCK_TAVERN.md."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe  # noqa: E402
from tw2k.engine import constants as K  # noqa: E402
from tw2k.engine.combat import _destroy_ship_tw2002  # noqa: E402
from tw2k.engine.models import Commodity, Planet, PlanetClass, Player, Ship  # noqa: E402
from tw2k.engine.observation import build_observation  # noqa: E402
from tw2k.engine.tavern import password_for  # noqa: E402


def _seat(universe, pid, name, **kw):
    player = Player(id=pid, name=name, ship=Ship(), sector_id=kw.get("sector", 1), **{
        k: v for k, v in kw.items() if k != "sector"
    })
    universe.players[pid] = player
    universe.sectors[player.sector_id].occupant_ids.append(pid)
    return player


def _move(universe, player, sector):
    universe.sectors[player.sector_id].occupant_ids.remove(player.id)
    player.sector_id = sector
    player.end_port_visit()
    universe.sectors[sector].occupant_ids.append(player.id)


def _do(universe, pid, kind, **args):
    result = apply_action(universe, pid, Action(kind=kind, args=args))
    if not result.ok:
        raise SystemExit(f"FAIL {pid} {kind.value}: {result.error}")
    return result


def _port_sector(universe):
    for sid, sector in universe.sectors.items():
        port = sector.port
        if port is None or int(sid) == int(K.STARDOCK_SECTOR):
            continue
        if port.sells(Commodity.FUEL_ORE):
            row = port.stock[Commodity.FUEL_ORE]
            if int(row.current) <= 0:
                row.current = max(int(row.maximum), 20)
            return int(sid)
    raise SystemExit("FAIL no fuel port")


def main() -> int:
    universe = generate_universe(GameConfig(
        seed=11, universe_size=40, max_days=6, enable_planets=False, enable_ferrengi=False,
    ))
    p1 = _seat(universe, "P1", "P1", credits=400_000, alignment=150, experience=20)
    p2 = _seat(universe, "P2", "P2", credits=400_000, alignment=150, experience=20)
    p3 = _seat(universe, "P3", "P3", credits=400_000, alignment=150, experience=40)
    p4 = _seat(universe, "P4", "P4", credits=50_000, alignment=250, experience=10, sector=6)
    p5 = _seat(universe, "P5", "P5", credits=40_000, alignment=50, experience=80)
    p5.bank_balance = 100_000
    klass = next(iter(PlanetClass))
    universe.planets[1] = Planet(id=1, sector_id=5, name="Home", class_id=klass, owner_id="P5")

    _do(universe, "P1", ActionKind.TAVERN_ANNOUNCE, text="first board")
    seen = build_observation(universe, "P2").tavern["announcement"]["text"]
    if seen != "first board":
        raise SystemExit("FAIL P2 did not read the first announcement")
    _do(universe, "P3", ActionKind.TAVERN_ANNOUNCE, text="only this one")
    seen = build_observation(universe, "P2").tavern["announcement"]["text"]
    if seen != "only this one":
        raise SystemExit("FAIL the board kept more than one announcement")
    if build_observation(universe, "P4").tavern is not None:
        raise SystemExit("FAIL P4 away from StarDock saw the tavern")

    _do(universe, "P2", ActionKind.TAVERN_GRAFFITI, text="unsigned line")
    wall = build_observation(universe, "P1").tavern["graffiti"][-1]
    if wall.get("text") != "unsigned line" or "name" in wall:
        raise SystemExit("FAIL graffiti showed an author")

    port_x = _port_sector(universe)
    _move(universe, p1, port_x)
    trade = apply_action(universe, "P1", Action(kind=ActionKind.TRADE, args={
        "commodity": "fuel_ore", "qty": 1, "side": "buy",
    }))
    if not trade.ok:
        raise SystemExit(f"FAIL trade at {port_x}: {trade.error}")
    _move(universe, p1, 1)
    bought = _do(universe, "P1", ActionKind.BUY_SHIP, ship_class="scout_marauder")
    if p1.ship.dock_log:
        raise SystemExit(f"FAIL new hull kept a dock log {p1.ship.dock_log}")
    before = p2.credits
    _do(universe, "P2", ActionKind.GRIMY_ASK, topic="trader", target="P1")
    if p2.credits != before:
        raise SystemExit("FAIL a trace charged for an empty hull")

    port_y = port_x
    _move(universe, p1, port_y)
    trade = apply_action(universe, "P1", Action(kind=ActionKind.TRADE, args={
        "commodity": "fuel_ore", "qty": 1, "side": "buy",
    }))
    if not trade.ok:
        raise SystemExit(f"FAIL second trade: {trade.error}")
    _move(universe, p1, 1)
    before = p2.credits
    _do(universe, "P2", ActionKind.GRIMY_ASK, topic="trader", target="P1")
    if p2.credits != before - int(K.GRIMY_TRACE_COST):
        raise SystemExit("FAIL the trace did not cost 3,000")
    if p2.tavern_last_trace["port_sector"] != port_y:
        raise SystemExit(f"FAIL trace returned {p2.tavern_last_trace}")

    word = password_for(universe.config.seed)
    _do(universe, "P2", ActionKind.GRIMY_ASK, topic="underground")
    if p2.credits != before - int(K.GRIMY_TRACE_COST) - int(K.GRIMY_PASSWORD_COST):
        raise SystemExit("FAIL the password did not cost 2,000")
    _do(universe, "P2", ActionKind.UNDERGROUND_ENTER, password=word.lower())
    p4.ug_password_known = True
    _move(universe, p4, 1)
    turned = apply_action(universe, "P4", Action(kind=ActionKind.UNDERGROUND_ENTER, args={"password": "nope"}))
    if turned.ok or p4.ug_attempts != 0:
        raise SystemExit("FAIL alignment 250 was not turned away")

    for _ in range(3):
        bad = apply_action(universe, "P5", Action(kind=ActionKind.UNDERGROUND_ENTER, args={"password": "wrong"}))
        if bad.ok:
            raise SystemExit("FAIL an early wrong password was accepted")
    _do(universe, "P5", ActionKind.UNDERGROUND_ENTER, password="wrong")
    if p5.credits != 0 or p5.bank_balance != 100_000:
        raise SystemExit("FAIL the mugging touched the bank or left cash")
    _do(universe, "P5", ActionKind.UNDERGROUND_ENTER, password="wrong")
    if p5.experience != 40:
        raise SystemExit(f"FAIL experience halved to {p5.experience}")
    _do(universe, "P5", ActionKind.UNDERGROUND_ENTER, password="wrong")
    if p5.experience != 0 or p5.alignment != 0 or p5.ship.ship_class.value != K.SD_RESTART_HULL:
        raise SystemExit("FAIL the murder did not zero the trader into a Scout")
    if universe.planets[1].owner_id != "P5":
        raise SystemExit("FAIL the murder took the planet")
    if not any("murdered on StarDock" in ev.summary for ev in universe.events):
        raise SystemExit("FAIL no public murder line")

    _do(universe, "P2", ActionKind.UNDERGROUND_CONTRACT, target="P1", amount=10_000)
    if p2.alignment != 150 - 40:
        raise SystemExit(f"FAIL alignment {p2.alignment}")
    p1.credits = 0
    _destroy_ship_tw2002(universe, "P1", "fighters", "P3", True, always_escape=True)
    if int((universe.tavern or {}).get("ug_pending", {}).get("P3", 0)) != 0:
        raise SystemExit("FAIL a pod kill paid the contract")
    _destroy_ship_tw2002(universe, "P1", "fighters", "P3", True, force_destroyed=True)
    if int(universe.tavern["ug_pending"].get("P3", 0)) != 10_000:
        raise SystemExit("FAIL the real kill did not earn 10,000")
    p3.alignment = 300
    _move(universe, p3, 1)
    blocked = apply_action(universe, "P3", Action(kind=ActionKind.UNDERGROUND_ENTER, args={"password": word}))
    if blocked.ok:
        raise SystemExit("FAIL alignment 300 entered")
    claim = apply_action(universe, "P3", Action(kind=ActionKind.UNDERGROUND_CLAIM, args={}))
    if claim.ok:
        raise SystemExit("FAIL a claim without entry")
    p3.alignment = 150
    p3.ug_password_known = True
    _do(universe, "P3", ActionKind.UNDERGROUND_ENTER, password=word)
    before = p3.credits
    _do(universe, "P3", ActionKind.UNDERGROUND_CLAIM)
    if p3.credits != before + 10_000:
        raise SystemExit("FAIL the claim did not pay 10,000")

    _do(universe, "P2", ActionKind.GRIMY_CURSE)
    if p2.alignment != 150 - 40 - 1 or p2.experience != 19:
        raise SystemExit("FAIL the curse did not cost 1/1")
    again = apply_action(universe, "P2", Action(kind=ActionKind.GRIMY_CURSE, args={}))
    if again.ok:
        raise SystemExit("FAIL a second curse was allowed")

    public = []
    for ev in universe.events:
        witnesses = ev.payload.get("_witnesses") or []
        if ev.kind.value == "ug_murder" or (witnesses and witnesses != [ev.actor_id]):
            public.append(ev.summary + str({k: v for k, v in ev.payload.items() if k != "_witnesses"}))
    if word in " ".join(public):
        raise SystemExit("FAIL the password is in a public event")
    for pid, player in universe.players.items():
        if player.ug_password_known:
            continue
        block = build_observation(universe, pid).tavern or {}
        if block.get("ug_password"):
            raise SystemExit(f"FAIL {pid} can see the password")
    print("PASS tavern scenario lab")
    print("bought", bought.ok)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
