"""Hash of a short run that destroys at the exact-minimum fighter count.

Re-pinned on 5968646 (slice 50 follow-up). The digest matches that parent with
CAPTURE_MODE legacy: the same attacks still destroy, and capture adds no bytes.
"""

from __future__ import annotations

import hashlib
import json

import tw2k.engine.constants as K
from tw2k.agents.prompts import format_observation, get_system_prompt
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.fleet import _new_ship_id
from tw2k.engine.models import ParkedShip, Player, Ship, ShipClass
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import tick_day


def _sit(u, pid, sector, fighters):
    if pid not in u.players:
        u.players[pid] = Player(id=pid, name=pid, ship=Ship(), sector_id=1)
        u.sectors[1].occupant_ids.append(pid)
    p = u.players[pid]
    if pid in u.sectors[p.sector_id].occupant_ids:
        u.sectors[p.sector_id].occupant_ids.remove(pid)
    p.sector_id = int(sector)
    p.ship.ship_class = ShipClass.MERCHANT_CRUISER
    p.ship.fighters = int(fighters)
    p.ship.shields = 0
    p.turns_today = 0
    p.turns_per_day = 1000
    p.alive = True
    u.sectors[int(sector)].occupant_ids.append(pid)
    return p


def legacy_capture_digest() -> str:
    """Exact-minimum attacks on a manned ship and an unmanned ship, then 3 day ticks."""
    if hasattr(K, "CAPTURE_MODE"):
        K.CAPTURE_MODE = "legacy"
    h = hashlib.sha256()
    h.update(get_system_prompt().encode())
    u = generate_universe(GameConfig(seed=11, universe_size=60, enable_ferrengi=False, enable_planets=False))
    sector = next(s for s in sorted(u.sectors) if int(s) > 10)
    _sit(u, "A", sector, 20)
    _sit(u, "B", sector, 0)
    ship = Ship(ship_class=ShipClass.MERCHANT_FREIGHTER, name="spare", holds=10, fighters=0, shields=0)
    sid = _new_ship_id(u)
    ship.fleet_id = sid
    u.parked_ships[sid] = ParkedShip(id=sid, owner_id="B", sector_id=int(sector), ship=ship, parked_day=u.day)

    def snap(tag: str):
        h.update(tag.encode())
        for pid in ("A", "B"):
            if pid not in u.players:
                continue
            o = build_observation(u, pid)
            h.update(o.model_dump_json().encode())
            h.update(format_observation(o).encode())
        h.update(json.dumps([e.model_dump(mode="json") for e in u.events], sort_keys=True).encode())

    snap("before")
    apply_action(u, "A", Action(kind=ActionKind.ATTACK, args={"target": "B", "qty": 1}))
    snap("manned")
    _sit(u, "A", sector, 20)
    owner = u.parked_ships[sid].owner_id
    apply_action(u, "A", Action(kind=ActionKind.ATTACK, args={"target": f"ship:{sid}", "qty": 1}))
    snap("unmanned")
    h.update(str(sid in u.parked_ships).encode())
    h.update(owner.encode())
    for _ in range(3):
        tick_day(u)
        h.update(json.loads(u.model_dump_json()) and u.model_dump_json().encode())
    h.update(str(K.COMBAT_MODE).encode())
    return h.hexdigest()[:24]


if __name__ == "__main__":
    print(legacy_capture_digest())
