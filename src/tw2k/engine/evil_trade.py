"""Steal-dump-transport and rob-transport for a negative-alignment seat.

Glossary SDT and RTR (classictw_docs_wiki/Glossary.html): steal equipment,
land, dump, beam to the other ship; or rob one port, beam, and rob the next.
Fake bust is per pilot (SHIP_FLEET.md fl28). Cargo stays on the hull you
leave, so a haul is dumped or sold before a beam. Amounts are the existing
experience caps (ROB_STEAL.md, formulas.html). This module only picks the
next legal step. It does not invent a range, a price, or an experience cap.
"""

from __future__ import annotations

from typing import Any

from . import constants as K
from .rob_steal import max_rob_credits, max_steal_holds

_HAUL = ("equipment", "organics", "fuel_ore")


def next_evil_step(view: Any, *, last_crime_sector: int | None = None) -> dict[str, Any] | None:
    """The next SDT or RTR action, or None when the seat should trade as usual."""
    try:
        align = int(view.obs.get("alignment") or 0)
        exp = int(view.obs.get("experience") or 0)
    except (TypeError, ValueError):
        return None
    if align > int(K.ROB_MIN_ALIGNMENT):
        return None
    here = view.here
    hauled = _hauled(view)
    if view.landed is not None and hauled:
        return _dump(view, int(view.landed))
    if hauled:
        if here is None:
            return None
        return _land(view, int(here))
    if view.landed is not None:
        if view.ok("liftoff"):
            return {"kind": "liftoff", "args": {}, "thought": "evil loop: lift off to beam"}
        return None
    if here is None:
        return None
    here_id = int(here)
    if last_crime_sector is not None and int(last_crime_sector) == here_id:
        return _transport(view, here_id)
    stolen = _steal(view, exp)
    if stolen is not None:
        return stolen
    robbed = _rob(view, exp)
    if robbed is not None:
        return robbed
    return _transport(view, here_id)


def _hauled(view: Any) -> bool:
    cargo = view.cargo or {}
    return any(int(cargo.get(name) or 0) > 0 for name in _HAUL)


def _dump(view: Any, planet_id: int) -> dict[str, Any] | None:
    if not view.ok("dump_planet_cargo"):
        return None
    choices = {str(item) for item in view.choices("dump_planet_cargo", "commodity")}
    cargo = view.cargo or {}
    for commodity in _HAUL:
        held = int(cargo.get(commodity) or 0)
        if held <= 0 or commodity not in choices:
            continue
        room = view.max_by("dump_planet_cargo", "qty", commodity) or held
        qty = min(held, int(room))
        if qty <= 0:
            continue
        return {
            "kind": "dump_planet_cargo",
            "args": {"planet_id": planet_id, "commodity": commodity, "qty": int(qty)},
            "thought": f"evil loop: dump {qty} {commodity} on planet {planet_id}",
        }
    return None


def _land(view: Any, here: int) -> dict[str, Any] | None:
    """Land on an own planet here. A haul is not beamed: the cargo would stay behind."""
    if view.landed is not None or not view.ok("land_planet"):
        return None
    choices = {int(item) for item in view.choices("land_planet", "planet_id")}
    ids = []
    for planet in view.owned or []:
        if not isinstance(planet, dict) or planet.get("id") is None:
            continue
        if int(planet.get("sector_id") or -1) != here:
            continue
        pid = int(planet["id"])
        if pid in choices:
            ids.append(pid)
    if not ids:
        return None
    pid = min(ids)
    return {
        "kind": "land_planet",
        "args": {"planet_id": pid},
        "thought": f"evil loop: land on planet {pid} to dump",
    }


def _steal(view: Any, experience: int) -> dict[str, Any] | None:
    if not view.ok("steal") or "busted" in view.reason("steal").lower():
        return None
    if "equipment" not in {str(item) for item in view.choices("steal", "commodity")}:
        return None
    room = int(view.max_by("steal", "qty", "equipment") or 0)
    qty = min(room, int(view.cargo_free or 0), max_steal_holds(experience))
    if qty <= 0:
        return None
    return {
        "kind": "steal",
        "args": {"commodity": "equipment", "qty": int(qty)},
        "thought": f"evil loop: steal {qty} equipment",
    }


def _rob(view: Any, experience: int) -> dict[str, Any] | None:
    if not view.ok("rob") or "busted" in view.reason("rob").lower():
        return None
    legal_max = int((view.params("rob").get("amount") or {}).get("max") or 0)
    amount = min(legal_max, max_rob_credits(experience))
    if amount <= 0:
        return None
    return {
        "kind": "rob",
        "args": {"amount": int(amount)},
        "thought": f"evil loop: rob {amount} credits",
    }


def _transport(view: Any, here: int) -> dict[str, Any] | None:
    if not view.ok("ship_transport"):
        return None
    legal = {int(item) for item in view.choices("ship_transport", "ship_id")}
    best: tuple[int, int] | None = None
    fleet = view.obs.get("fleet") if isinstance(view.obs, dict) else None
    ships = (fleet or {}).get("ships") if isinstance(fleet, dict) else None
    for ship in ships or []:
        if not isinstance(ship, dict) or not ship.get("in_range"):
            continue
        try:
            sid = int(ship.get("ship_id"))
            sector = int(ship.get("sector_id"))
            hops = int(ship.get("hops"))
        except (TypeError, ValueError):
            continue
        if sid not in legal or hops <= 0 or sector == here:
            continue
        key = (hops, sid)
        if best is None or key < best:
            best = key
    if best is None:
        return None
    return {
        "kind": "ship_transport",
        "args": {"ship_id": best[1]},
        "thought": f"evil loop: beam to ship {best[1]} ({best[0]} hops)",
    }
