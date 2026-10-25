"""v3.11 NavPoints. Four named sectors, plus Terra and StarDock.

EIS ``GeneralNew.html`` (NavPoints): assign a sector to one of four programmable
NavPoints. The move menu lists those, Terra, and StarDock, and selecting one
lays in a course.

EIS ``Navigate.html`` ``<N> Move to NavPoint`` and ``Tactical.html`` ``<Y> Set
NavPoints`` (also Someguy ``TWINSTR.txt``): the unit is pre-programmed with
sector 1 (Terra) and, when the game has one, StarDock. There are four other
definable points.

``tw-attac_TW2002_v3_revision_history_to_v3.11.html``: the menu shows a sector
scan only when the sector is in FedSpace, it is your current sector, or you
have at least one fighter deployed there. Otherwise the line is ``No Scan``.

The printed pages do not give a name length or a clear key. This game keeps a
name to 20 characters, and clear drops a slot. ``0`` clears all four, the same
shape as the avoid list.
"""

from __future__ import annotations

from typing import Any

from . import constants as K
from .actions import Action, ActionResult
from .models import EventKind, Universe

_RESERVED = frozenset({"terra", "stardock"})


def _stored(player) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for row in player.navpoints or []:
        try:
            slot = int(row.get("slot"))
            sector = int(row.get("sector"))
        except (TypeError, ValueError, AttributeError):
            continue
        if slot < 1 or slot > int(K.NAVPOINT_SLOTS):
            continue
        out[slot] = {"slot": slot, "name": str(row.get("name") or ""), "sector": sector}
    return out


def _write(player, points: dict[int, dict[str, Any]]) -> None:
    player.navpoints = [points[slot] for slot in sorted(points)]


def scan_line(universe: Universe, player, sector_id: int) -> str:
    """The v3.11 menu line for one sector. ``No Scan`` is the printed refusal."""
    sector = universe.sectors.get(int(sector_id))
    if sector is None:
        return "No Scan"
    fighters = sector.fighters
    own = (
        fighters is not None
        and fighters.owner_id == player.id
        and int(fighters.count) >= 1
    )
    visible = (
        K.in_fedspace(universe, sector_id)
        or int(sector_id) == int(player.sector_id)
        or own
    )
    if not visible:
        return "No Scan"
    bits: list[str] = []
    if sector.port is not None:
        label = getattr(sector.port.class_id, "value", sector.port.class_id)
        bits.append(f"Port {label}")
    names = []
    for planet_id in sector.planet_ids:
        planet = universe.planets.get(planet_id)
        if planet is not None and planet.name:
            names.append(str(planet.name))
    if names:
        bits.append("Planets " + ", ".join(names))
    if not bits:
        return "No planets or ports."
    return ". ".join(bits) + "."


def menu_rows(universe: Universe, player) -> list[dict[str, Any]]:
    """Programmable slots first, then the pre-programmed Terra and StarDock lines."""
    points = _stored(player)
    rows: list[dict[str, Any]] = []
    for slot in range(1, int(K.NAVPOINT_SLOTS) + 1):
        row = points.get(slot)
        if row is None:
            rows.append({
                "kind": "set", "slot": slot, "name": "", "sector": None, "scan": "",
            })
            continue
        rows.append({
            "kind": "set",
            "slot": slot,
            "name": row["name"],
            "sector": int(row["sector"]),
            "scan": scan_line(universe, player, int(row["sector"])),
        })
    terra = 1
    dock = int(K.stardock_sector_of(universe))
    rows.append({
        "kind": "fixed", "slot": "terra", "name": "Terra", "sector": terra,
        "scan": scan_line(universe, player, terra),
    })
    rows.append({
        "kind": "fixed", "slot": "stardock", "name": "StarDock", "sector": dock,
        "scan": scan_line(universe, player, dock),
    })
    return rows


def resolve_navpoint(player, token: object, universe=None) -> int | None:
    """A slot, a name, Terra, or StarDock. None when that point is not set."""
    if token is None or isinstance(token, bool):
        return None
    text = str(token).strip()
    if not text:
        return None
    low = text.lower()
    if low == "terra":
        return 1
    if low == "stardock":
        return int(K.stardock_sector_of(universe))
    points = _stored(player)
    if text.isdigit():
        row = points.get(int(text))
        return None if row is None else int(row["sector"])
    for row in points.values():
        if str(row["name"]).lower() == low:
            return int(row["sector"])
    return None


def _slot(raw: object) -> int | None:
    try:
        slot = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return slot


def _set(universe: Universe, player, action: Action) -> ActionResult:
    slot = _slot(action.args.get("slot"))
    if slot is None or slot < 1 or slot > int(K.NAVPOINT_SLOTS):
        return ActionResult(ok=False, error=f"NavPoints are 1 through {int(K.NAVPOINT_SLOTS)}")
    name = str(action.args.get("name") or "").strip()
    if not name:
        return ActionResult(ok=False, error="A NavPoint needs a name")
    if len(name) > int(K.NAVPOINT_NAME_MAX):
        return ActionResult(
            ok=False, error=f"A NavPoint name is at most {int(K.NAVPOINT_NAME_MAX)} characters",
        )
    if name.lower() in _RESERVED or name.isdigit():
        return ActionResult(ok=False, error="That name is reserved")
    try:
        sector = int(action.args.get("sector"))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ActionResult(ok=False, error="A NavPoint needs a sector")
    if sector not in universe.sectors:
        return ActionResult(ok=False, error="invalid sector")
    points = _stored(player)
    for other, row in points.items():
        if other != slot and str(row["name"]).lower() == name.lower():
            return ActionResult(ok=False, error="That name is already a NavPoint")
    points[slot] = {"slot": slot, "name": name, "sector": sector}
    _write(player, points)
    universe.emit(
        EventKind.NAVPOINT,
        actor_id=player.id,
        sector_id=player.sector_id,
        payload={"op": "set", "slot": slot, "name": name, "sector": sector},
        summary=f"NavPoint {slot} {name} logged at sector {sector}.",
    )
    return ActionResult(ok=True, turns_spent=0)


def _clear(universe: Universe, player, action: Action) -> ActionResult:
    slot = _slot(action.args.get("slot", action.args.get("sector")))
    if slot is None:
        return ActionResult(ok=False, error="clear needs a slot, or 0 to clear all")
    points = _stored(player)
    if slot == 0:
        player.navpoints = []
        summary = "NavPoints cleared."
    elif slot < 1 or slot > int(K.NAVPOINT_SLOTS):
        return ActionResult(ok=False, error=f"NavPoints are 1 through {int(K.NAVPOINT_SLOTS)}")
    else:
        points.pop(slot, None)
        _write(player, points)
        summary = f"NavPoint {slot} cleared."
    universe.emit(
        EventKind.NAVPOINT,
        actor_id=player.id,
        sector_id=player.sector_id,
        payload={"op": "clear", "slot": slot},
        summary=summary,
    )
    return ActionResult(ok=True, turns_spent=0)


def _list(universe: Universe, player) -> ActionResult:
    rows = menu_rows(universe, player)
    shown = [
        f"{row['name']} sector {row['sector']}"
        for row in rows
        if row.get("sector") is not None and row.get("name")
    ]
    universe.emit(
        EventKind.NAVPOINT,
        actor_id=player.id,
        sector_id=player.sector_id,
        payload={"op": "list", "rows": rows},
        summary="NavPoints: " + (", ".join(shown) if shown else "none") + ".",
    )
    return ActionResult(ok=True, turns_spent=0)


def apply_navpoint(universe: Universe, pid: str, action: Action) -> ActionResult:
    """Set, list, or clear. Off, the verb is not a command."""
    if not K.navpoint_live():
        return ActionResult(ok=False, error="unsupported action")
    player = universe.players[pid]
    op = str(action.args.get("op") or "list").strip().lower()
    if op == "list":
        return _list(universe, player)
    if op == "set":
        return _set(universe, player, action)
    if op == "clear":
        return _clear(universe, player, action)
    return ActionResult(ok=False, error="navpoint op is set, list, or clear")


def legal_spec(universe: Universe, player_id: str) -> tuple[bool, None, dict[str, Any]]:
    player = universe.players[player_id]
    return True, None, {
        "slots": int(K.NAVPOINT_SLOTS),
        "prompt": (
            "Set NavPoints. Use this option to log important sectors to your navigation unit."
        ),
        "move": "Selecting one of the listed NavPoints will lay in a course for that destination.",
        "rows": menu_rows(universe, player),
    }
