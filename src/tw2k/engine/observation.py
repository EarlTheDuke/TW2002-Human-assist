"""Observation builder — constructs the limited-information view an agent sees."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .economy import port_buy_price, port_sell_price
from .models import Commodity, PortClass, Universe


class Observation(BaseModel):
    """What an agent sees on its turn."""

    # Match-level
    day: int
    tick: int
    max_days: int
    finished: bool

    # Self
    self_id: str
    self_name: str
    credits: int
    alignment: int
    alignment_label: str = ""
    experience: int = 0
    rank: str = "Civilian"
    turns_remaining: int
    turns_per_day: int
    ship: dict[str, Any]
    corp_ticker: str | None
    planet_landed: int | None
    scratchpad: str
    alive: bool = True
    net_worth: int = 0
    # Planets this player owns (subset view; one entry per planet).
    owned_planets: list[dict[str, Any]] = Field(default_factory=list)

    # Current sector full detail
    sector: dict[str, Any]
    adjacent: list[dict[str, Any]]

    # Port intel database (persistent across turns)
    known_ports: list[dict[str, Any]]

    # Other players — corp mates show full state, others show last-known summary
    other_players: list[dict[str, Any]]

    # Messaging
    inbox: list[dict[str, Any]]

    # Recent events feed (global newsworthy items)
    recent_events: list[dict[str, Any]]

    # Diplomatic state
    alliances: list[dict[str, Any]] = Field(default_factory=list)
    corp: dict[str, Any] | None = None  # corp summary if member
    deaths: int = 0
    max_deaths: int = 3

    # Persistent intel
    limpets_owned: list[dict[str, Any]] = Field(default_factory=list)
    probe_log: list[dict[str, Any]] = Field(default_factory=list)

    # Legal actions hint (textual grammar)
    action_hint: str = Field(default="")


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------


def build_observation(universe: Universe, player_id: str, event_history: int = 20) -> Observation:
    player = universe.players[player_id]
    sector = universe.sectors[player.sector_id]

    ship = _ship_dict(player.ship)

    # Current sector detail
    sector_info = _sector_detail(universe, sector, player_id)

    # Adjacent sector summaries
    adjacent: list[dict[str, Any]] = []
    for wid in sector.warps:
        w = universe.sectors[wid]
        adjacent.append({
            "id": wid,
            "port": w.port.code if w.port else None,
            "fighter_count": w.fighters.count if w.fighters else 0,
            "fighter_owner": w.fighters.owner_id if w.fighters else None,
            "mines": sum(m.count for m in w.mines),
            "has_planets": bool(w.planet_ids),
            "occupants": list(w.occupant_ids),
            "known": wid in player.known_sectors,
        })

    # Known ports database (most profitable view first)
    known_ports: list[dict[str, Any]] = []
    for sid, entry in sorted(player.known_ports.items()):
        known_ports.append({"sector_id": sid, **entry})

    # Other players visibility
    others: list[dict[str, Any]] = []
    corp_mate_ids = set()
    if player.corp_ticker and player.corp_ticker in universe.corporations:
        corp_mate_ids = set(universe.corporations[player.corp_ticker].member_ids) - {player_id}
    for other_id, other in universe.players.items():
        if other_id == player_id:
            continue
        if other_id in corp_mate_ids:
            others.append({
                "id": other_id,
                "name": other.name,
                "is_corpmate": True,
                "credits": other.credits,
                "sector_id": other.sector_id,
                "ship_class": other.ship.ship_class.value,
                "fighters": other.ship.fighters,
                "alive": other.alive,
                "alignment": other.alignment,
            })
        else:
            # Limited visibility — only what's recently visible through events or sharing same sector
            visible = (other.sector_id == player.sector_id) or (other_id in sector.occupant_ids)
            entry: dict[str, Any] = {
                "id": other_id,
                "name": other.name,
                "is_corpmate": False,
                "alive": other.alive,
                "corp_ticker": other.corp_ticker,
            }
            if visible:
                entry.update({
                    "sector_id": other.sector_id,
                    "ship_class": other.ship.ship_class.value,
                })
            others.append(entry)

    # Recent events (global feed — truncated)
    recent = universe.events[-event_history:]
    recent_events = [
        {
            "seq": e.seq,
            "day": e.day,
            "tick": e.tick,
            "kind": e.kind.value,
            "actor_id": e.actor_id,
            "sector_id": e.sector_id,
            "summary": e.summary,
        }
        for e in recent
    ]

    turns_remaining = player.turns_per_day - player.turns_today

    # Active alliances visible to this player
    from . import constants as K
    alliances: list[dict[str, Any]] = []
    for ally in universe.alliances.values():
        if player.id in ally.member_ids or ally.proposed_by == player.id:
            alliances.append({
                "id": ally.id,
                "members": ally.member_ids,
                "active": ally.active,
                "proposed_by": ally.proposed_by,
                "formed_day": ally.formed_day,
            })

    corp_summary: dict[str, Any] | None = None
    if player.corp_ticker and player.corp_ticker in universe.corporations:
        c = universe.corporations[player.corp_ticker]
        corp_summary = {
            "ticker": c.ticker,
            "name": c.name,
            "ceo_id": c.ceo_id,
            "members": list(c.member_ids),
            "treasury": c.treasury,
            "planet_ids": list(c.planet_ids),
        }

    limpets_owned: list[dict[str, Any]] = []
    for lt in universe.limpets.values():
        if lt.owner_id != player.id:
            continue
        target = universe.players.get(lt.target_id)
        limpets_owned.append({
            "target_id": lt.target_id,
            "target_name": target.name if target else None,
            "current_sector": target.sector_id if target else None,
            "placed_day": lt.placed_day,
        })

    probe_log: list[dict[str, Any]] = []
    for sid, entry in sorted(player.probe_log.items()):
        probe_log.append({"sector_id": sid, **entry})

    owned_planets: list[dict[str, Any]] = []
    for planet in universe.planets.values():
        if planet.owner_id != player.id:
            continue
        owned_planets.append({
            "id": planet.id,
            "sector_id": planet.sector_id,
            "name": planet.name,
            "class": planet.class_id.value,
            "citadel_level": planet.citadel_level,
            "citadel_target": getattr(planet, "citadel_target", 0),
            "citadel_complete_day": getattr(planet, "citadel_complete_day", None),
            "fighters": planet.fighters,
            "shields": planet.shields,
        })

    from .runner import alignment_label, rank_for
    obs = Observation(
        day=universe.day,
        tick=universe.tick,
        max_days=universe.config.max_days,
        finished=universe.finished,
        self_id=player.id,
        self_name=player.name,
        credits=player.credits,
        alignment=player.alignment,
        alignment_label=alignment_label(player.alignment),
        experience=player.experience,
        rank=rank_for(player.experience),
        turns_remaining=turns_remaining,
        turns_per_day=player.turns_per_day,
        ship=ship,
        corp_ticker=player.corp_ticker,
        planet_landed=player.planet_landed,
        scratchpad=player.scratchpad,
        alive=player.alive,
        net_worth=player.net_worth,
        owned_planets=owned_planets,
        sector=sector_info,
        adjacent=adjacent,
        known_ports=known_ports,
        other_players=others,
        inbox=list(player.inbox[-40:]),
        recent_events=recent_events,
        alliances=alliances,
        corp=corp_summary,
        deaths=player.deaths,
        max_deaths=K.MAX_DEATHS_BEFORE_ELIM,
        limpets_owned=limpets_owned,
        probe_log=probe_log,
        action_hint=_action_hint(sector_info),
    )
    return obs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ship_dict(ship) -> dict[str, Any]:
    return {
        "class": ship.ship_class.value,
        "holds": ship.holds,
        "cargo": {c.value: ship.cargo.get(c, 0) for c in Commodity},
        "fighters": ship.fighters,
        "shields": ship.shields,
        "mines": {m.value: ship.mines.get(m, 0) for m in ship.mines},
        "genesis": ship.genesis,
        "photon_missiles": getattr(ship, "photon_missiles", 0),
        "ether_probes": getattr(ship, "ether_probes", 0),
        "photon_disabled_ticks": getattr(ship, "photon_disabled_ticks", 0),
        "cargo_free": ship.cargo_free,
    }


def _sector_detail(universe: Universe, sector, player_id: str) -> dict[str, Any]:
    info: dict[str, Any] = {
        "id": sector.id,
        "warps_out": list(sector.warps),
        "is_fedspace": sector.id in _fedspace_set(universe),
        "occupants": list(sector.occupant_ids),
        "fighter_group": None,
        "mines": [{"owner": m.owner_id, "kind": m.kind.value, "count": m.count} for m in sector.mines],
        "planets": [
            _planet_brief(universe.planets[pid]) for pid in sector.planet_ids if pid in universe.planets
        ],
        "port": None,
        "ferrengi": [
            {"id": f.id, "name": f.name, "aggression": f.aggression, "fighters": f.fighters}
            for f in universe.ferrengi.values()
            if f.sector_id == sector.id and f.alive
        ],
    }
    if sector.fighters:
        info["fighter_group"] = {
            "owner_id": sector.fighters.owner_id,
            "count": sector.fighters.count,
            "mode": sector.fighters.mode.value,
        }
    if sector.port is not None:
        p = sector.port
        port_info: dict[str, Any] = {
            "class_id": int(p.class_id),
            "code": p.code,
            "name": p.name,
            "buys": [c.value for c in Commodity if c != Commodity.COLONISTS and p.buys(c)],
            "sells": [c.value for c in Commodity if c != Commodity.COLONISTS and p.sells(c)],
            "stock": {},
        }
        if p.class_id != PortClass.STARDOCK:
            for commodity, s in p.stock.items():
                price = port_buy_price(p, commodity) if p.buys(commodity) else port_sell_price(p, commodity)
                port_info["stock"][commodity.value] = {
                    "current": s.current,
                    "max": s.maximum,
                    "price": price,
                    "side": "buys_from_player" if p.buys(commodity) else "sells_to_player",
                }
        info["port"] = port_info
    return info


def _planet_brief(planet) -> dict[str, Any]:
    return {
        "id": planet.id,
        "name": planet.name,
        "class": planet.class_id.value,
        "owner_id": planet.owner_id,
        "corp_ticker": planet.corp_ticker,
        "citadel_level": planet.citadel_level,
        "citadel_target": getattr(planet, "citadel_target", 0),
        "citadel_complete_day": getattr(planet, "citadel_complete_day", None),
        "fighters": planet.fighters,
        "shields": planet.shields,
        "treasury": planet.treasury,
        "stockpile": {c.value: planet.stockpile.get(c, 0) for c in planet.stockpile},
        "colonists": {c.value: planet.colonists.get(c, 0) for c in planet.colonists},
    }


_FEDSPACE_CACHE: set[int] | None = None


def _fedspace_set(universe: Universe) -> set[int]:
    from . import constants as K
    return K.FEDSPACE_SECTORS


def _action_hint(sector_info: dict[str, Any]) -> str:
    hints = [
        "Core actions: warp(target=<sector_id>), trade(commodity=<fuel_ore|organics|equipment>, qty=<int>, side=<buy|sell>, unit_price=<optional>), scan(), wait()",
        "Movement is only to sectors in sector.warps_out. Trade only at ports that buy/sell that commodity.",
    ]
    if sector_info.get("port"):
        hints.append("You are at a port — use TRADE.")
    if sector_info.get("planets"):
        hints.append("Planets are landable with LAND_PLANET(planet_id=<id>).")
    if sector_info.get("ferrengi"):
        hints.append("Ferrengi present — consider ATTACK or WARP out.")
    return " | ".join(hints)
