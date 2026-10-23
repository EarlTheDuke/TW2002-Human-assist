"""NOTE 162. Federation Hall, the hardware shop screen, and CIM.

Each helper stays off until its own mode is ``v311`` or ``V311_PROFILE`` is ``v311``.
Off, these handlers are not offered and they change nothing.
"""

from __future__ import annotations

from typing import Any

from . import constants as K
from .actions import Action, ActionResult
from .models import EventKind, Universe

_SHOP_LINES = {
    "fighters": "Fighters, up to this hull's chart cap.",
    "shields": "Shields, up to this hull's chart cap.",
    "holds": "Cargo holds, up to this hull's chart cap.",
    "genesis": "Genesis torpedoes, up to this hull's chart cap.",
    "photon_missiles": "Photon missiles, up to this hull's chart cap.",
    "armid_mines": "Armid mines, up to this hull's chart cap.",
    "limpet_mines": "Limpet mines, up to this hull's chart cap.",
    "atomic_mines": "Atomic detonators, up to this hull's chart cap.",
    "ether_probes": "Ether probes.",
    "cloak": "Cloaking devices.",
    "mine_disruptor": "Mine disruptors.",
    "colonists": "Colonists.",
    "planet_scanner": "Planet scanner.",
    "transwarp_drive": "Ship TransWarp drive.",
}


def shop_screen(choices: list[str], prices: dict, room_by: dict) -> list[dict[str, Any]]:
    """One line per item the counter will sell. Absent from the buy list while the hall is off."""
    rows = []
    for item in choices:
        rows.append({
            "item": item,
            "price": int(prices.get(item, 0) or 0),
            "room": int(room_by.get(item, 0) or 0),
            "line": _SHOP_LINES.get(item, str(item).replace("_", " ")),
        })
    return rows


def _hall_block(universe: Universe) -> dict[str, Any]:
    listed = []
    ranked = []
    for corp in universe.corporations.values():
        members = []
        exp = 0
        for mid in corp.member_ids:
            player = universe.players.get(mid)
            if player is None:
                continue
            exp += int(player.experience)
            members.append({"name": player.name, "ceo": mid == corp.ceo_id})
        row = {
            "registration": corp.ticker,
            "name": corp.name,
            "formed_day": int(corp.formed_day),
            "members": members,
            "exp": exp,
        }
        listed.append(row)
        ranked.append(dict(row))
    listed.sort(key=lambda row: row["registration"])
    ranked.sort(key=lambda row: (-row["exp"], row["registration"]))
    for place, row in enumerate(ranked, start=1):
        row["rank"] = place
    return {"listed": listed, "ranked": ranked}


def federation_hall_spec(universe: Universe, player_id: str) -> tuple[bool, str | None, dict]:
    player = universe.players[player_id]
    if int(player.sector_id) != int(K.STARDOCK_SECTOR):
        return False, "must be at StarDock", {}
    if player.planet_landed is not None:
        return False, "lift off first", {}
    return True, None, {"hall": _hall_block(universe)}


def handle_federation_hall(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not K.federation_hall_live():
        return ActionResult(ok=False, error="unsupported action")
    ok, why, _params = federation_hall_spec(universe, pid)
    if not ok:
        return ActionResult(ok=False, error=why or "must be at StarDock")
    player = universe.players[pid]
    hall = _hall_block(universe)
    universe.emit(
        EventKind.FEDERATION_HALL,
        actor_id=pid,
        sector_id=player.sector_id,
        payload=hall,
        summary=f"{player.name} reads Federation Hall",
    )
    return ActionResult(ok=True, turns_spent=0)


def _hostile_fighters(universe: Universe, player, sector_id: int) -> bool:
    sector = universe.sectors.get(int(sector_id))
    dep = sector.fighters if sector is not None else None
    if dep is None or int(dep.count) <= 0:
        return False
    if dep.owner_id == player.id:
        return False
    ticker = getattr(dep, "corp_ticker", None)
    if ticker and ticker == player.corp_ticker:
        return False
    return True


def _cim_sectors(player) -> list[dict[str, Any]]:
    rows = []
    for sid in sorted(int(s) for s in player.known_sectors):
        warps = player.known_warps.get(sid)
        if warps is None:
            warps = player.known_warps.get(str(sid))
        rows.append({"sector_id": sid, "warps": [int(w) for w in (warps or [])]})
    return rows


def _cim_ports(universe: Universe, player) -> list[dict[str, Any]]:
    rows = []
    for sid in sorted(int(s) for s in player.known_ports):
        if _hostile_fighters(universe, player, sid):
            rows.append({"sector_id": sid, "info": "unavailable"})
            continue
        entry = player.known_ports.get(sid) or player.known_ports.get(str(sid)) or {}
        # Playtest 4: CIM R printed nothing. TWGS's port report lists each
        # commodity as buying or selling with its amount and percent of max,
        # from the trader's own last look (known_ports), never live stock.
        goods: dict[str, dict[str, Any]] = {}
        for name, row in (entry.get("stock") or {}).items():
            if not isinstance(row, dict):
                continue
            side = row.get("side")
            if side not in ("buys_from_player", "sells_to_player"):
                continue
            cur = int(row.get("current") or 0)
            top = int(row.get("max") or 0)
            goods[str(name)] = {
                "side": "buying" if side == "buys_from_player" else "selling",
                "qty": cur,
                "pct": (cur * 100 // top) if top > 0 else 0,
            }
        rows.append({
            "sector_id": sid,
            "port": entry.get("code") or entry.get("port"),
            "class": entry.get("class"),
            "last_seen_day": entry.get("last_seen_day"),
            "goods": goods,
        })
    return rows


def cim_spec(universe: Universe, player_id: str) -> tuple[bool, str | None, dict]:
    del universe, player_id
    return True, None, {
        "query": {"type": "str", "required": True, "choices": ["I", "R", "F", "Q"]},
        "target": {"type": "int", "required": False},
    }


def handle_cim(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not K.cim_live():
        return ActionResult(ok=False, error="unsupported action")
    player = universe.players[pid]
    query = str((action.args or {}).get("query") or "").strip().upper()
    if query == "Q":
        report: dict[str, Any] = {"query": "Q"}
    elif query == "I":
        report = {"query": "I", "sectors": _cim_sectors(player)}
    elif query == "R":
        report = {"query": "R", "ports": _cim_ports(universe, player)}
    elif query == "F":
        from .runner import query_route
        route = query_route(universe, pid, (action.args or {}).get("target"))
        report = {"query": "F", "route": route}
    else:
        return ActionResult(ok=False, error="CIM query is I, R, F, or Q")
    universe.emit(
        EventKind.CIM_REPORT,
        actor_id=pid,
        sector_id=player.sector_id,
        payload=report,
        summary=f"{player.name} reads CIM {query}",
    )
    return ActionResult(ok=True, turns_spent=0)
