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
        action_hint=_action_hint(sector_info, player, owned_planets, universe),
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


def _action_hint(
    sector_info: dict[str, Any],
    player: Any = None,
    owned_planets: list[dict[str, Any]] | None = None,
    universe: Any = None,
) -> str:
    """State-aware legal-action hint string shown to the LLM every turn.

    The goal is to remind the agent of verbs that are LEGAL RIGHT NOW given
    its concrete state (ship cargo, StarDock proximity, owned planets, inbox
    backlog, recent failures). Large LLMs skim the system prompt; a targeted
    per-turn nudge is much more reliable for activating rarely-used verbs
    like deploy_genesis / assign_colonists / build_citadel.
    """
    from . import constants as K

    hints: list[str] = [
        "Verbs available: warp trade scan wait + 29 more (see system prompt).",
    ]

    # Movement
    warps_out = sector_info.get("warps_out") or []
    if warps_out:
        sample = ", ".join(str(w) for w in warps_out[:5])
        more = "" if len(warps_out) <= 5 else f" (+{len(warps_out) - 5} more)"
        hints.append(f"warp target MUST be in [{sample}{more}].")

    # Port / trade
    port = sector_info.get("port") or {}
    if port:
        buys = port.get("buys") or []
        sells = port.get("sells") or []
        bits = []
        if buys:
            bits.append(f"port BUYS {','.join(buys)}")
        if sells:
            bits.append(f"port SELLS {','.join(sells)}")
        if bits:
            hints.append(" / ".join(bits) + " — use trade.")

    # StarDock-specific — the set of verbs that ONLY work at sector 1
    sector_id = sector_info.get("id")
    if sector_id == K.STARDOCK_SECTOR:
        bits = [
            "At StarDock: buy_ship, buy_equip (fighters/shields/holds/armid_mines/limpet_mines/atomic_mines/"
            "genesis/photon_missile/ether_probe/colonists), corp_create legal here."
        ]
        # Concrete colonist-ferry nudge: the player can load holds with
        # colonists for 10 cr each and fly them out to their own planet.
        ship = getattr(player, "ship", None) if player is not None else None
        if ship is not None:
            free = getattr(ship, "cargo_free", None)
            if isinstance(free, int) and free > 0:
                bits.append(
                    f"Cargo free={free} — `buy_equip item=colonists qty={free}` loads Terra colonists at 10 cr each."
                )
        hints.append(" ".join(bits))

    # Ship inventory → actionable verbs
    if player is not None:
        ship = getattr(player, "ship", None)
        if ship is not None:
            genesis = getattr(ship, "genesis", 0) or 0
            if genesis > 0 and sector_id not in K.FEDSPACE_SECTORS and getattr(player, "planet_landed", None) is None:
                hints.append(
                    f"You carry {genesis} genesis torpedo(es) — `deploy_genesis` HERE creates a planet you own (4 turns)."
                )
            colonists = 0
            cargo = getattr(ship, "cargo", None)
            if cargo is not None:
                try:
                    colonists = int(cargo.get(Commodity.COLONISTS, 0))
                except Exception:
                    pass
            if colonists > 0:
                hints.append(
                    f"You have {colonists} colonists in cargo — land on a planet you own and use "
                    f"`assign_colonists from=ship to=<fuel_ore|organics|equipment|colonists> qty=<n>` to deposit."
                )
            photon = getattr(ship, "photon_missiles", 0) or 0
            if photon > 0:
                hints.append(f"{photon} photon missile(s) loaded — `photon_missile target=<player_id>`.")
            probes = getattr(ship, "ether_probes", 0) or 0
            if probes > 0:
                hints.append(f"{probes} probe(s) loaded — `probe target=<sector_id>` to remote-scan.")

    # Owned planets — land / build / assign
    if owned_planets:
        here_planets = [p for p in owned_planets if p.get("sector_id") == sector_id]
        if here_planets and getattr(player, "planet_landed", None) is None:
            ids = ", ".join(str(p["id"]) for p in here_planets)
            hints.append(f"You own planet(s) in this sector: [{ids}] — `land_planet planet_id=<id>`.")
        landed_id = getattr(player, "planet_landed", None) if player is not None else None
        if landed_id is not None:
            plan = next((p for p in owned_planets if p.get("id") == landed_id), None)
            if plan is not None:
                lvl = int(plan.get("citadel_level", 0) or 0)
                tgt = int(plan.get("citadel_target", 0) or 0)
                if tgt > lvl:
                    hints.append(f"Citadel L{tgt} already building on planet {landed_id}; use `liftoff` and return when done.")
                elif lvl < 6:
                    hints.append(
                        f"Landed on planet {landed_id} (citadel L{lvl}). `build_citadel planet_id={landed_id}` starts L{lvl + 1}; "
                        f"`assign_colonists` to rebalance; `liftoff` to leave."
                    )

    # Planets in sector (unowned) → exploration hint only
    planets_here = sector_info.get("planets") or []
    if planets_here and not (owned_planets and any(p.get("sector_id") == sector_id for p in owned_planets)):
        hints.append(f"{len(planets_here)} unowned planet(s) here — land_planet to inspect.")

    # Ferrengi presence
    if sector_info.get("ferrengi"):
        hints.append("Ferrengi present — attack for XP or warp out.")

    # Inbox backlog
    inbox = getattr(player, "inbox", None) if player is not None else None
    if inbox:
        unread = sum(1 for m in inbox[-20:] if not m.get("read"))
        if unread:
            hints.append(f"{unread} unread hail(s) in inbox — consider `hail` to respond.")

    # End-of-day safety: if the agent has fewer turns left than the cheapest
    # useful action (warp=2), just tell them to wait. Without this nudge, LLM
    # agents routinely spam warp at turns=58/60 and eat 4+ failed actions per
    # day on "out of turns for this day". Threshold is warp.cost (2) because
    # that's the most common verb the agent will try to squeeze in.
    if player is not None:
        turns_left = (
            getattr(player, "turns_per_day", 0) or 0
        ) - (getattr(player, "turns_today", 0) or 0)
        warp_cost = K.TURN_COST.get("warp", 2)
        if 0 < turns_left < warp_cost:
            hints.append(
                f"END OF DAY: only {turns_left} turn(s) left, warp costs "
                f"{warp_cost}. Emit `{{\"kind\":\"wait\",\"args\":{{}}}}` to "
                "rest — new day refills your turn pool."
            )
        elif turns_left <= 0:
            hints.append(
                "END OF DAY: 0 turns left — only `wait` will succeed until the next day_tick."
            )

    # Recent failure feedback — surface the LAST failure since the player's last successful action
    if universe is not None and player is not None:
        err = _recent_self_error(universe, player.id)
        if err:
            hints.append(f"YOUR LAST ACTION FAILED: {err} — change approach this turn.")

    return " | ".join(hints)


def _recent_self_error(universe: Any, player_id: str) -> str:
    """Return the most recent self-caused failure summary since the player's
    last *successful* gameplay action. Returns '' if their last action was OK.

    This lets the LLM see e.g. `trade_failed: port rejected` or
    `agent_error: must be landed on the planet first` on the very next turn
    without having to scan the global recent_events feed.
    """
    try:
        from .models import EventKind as E
    except Exception:
        return ""

    success_kinds = {
        E.WARP, E.TRADE, E.SCAN, E.DEPLOY_FIGHTERS, E.DEPLOY_MINES,
        E.LAND_PLANET, E.LIFTOFF, E.ASSIGN_COLONISTS, E.BUILD_CITADEL,
        E.GENESIS_DEPLOYED, E.BUY_SHIP, E.BUY_EQUIP, E.CORP_CREATE,
        E.CORP_INVITE, E.CORP_JOIN, E.CORP_LEAVE,
    }
    error_kinds = {E.AGENT_ERROR, E.TRADE_FAILED, E.WARP_BLOCKED}

    events = getattr(universe, "events", None) or []
    for ev in reversed(events[-80:]):
        if ev.actor_id != player_id:
            continue
        if ev.kind in error_kinds:
            return (ev.summary or ev.payload.get("error", "") or str(ev.kind.value))[:220]
        if ev.kind in success_kinds:
            return ""
    return ""
