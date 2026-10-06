"""INFO_MODE tw2002: long range scanners, path ether probes and port reports.

Rules and sources: docs/playtests/scanners/SCANNERS_HIDDEN_INFO.md (rows s1-s20).
Everything here writes into the scanning player's own memory (scan_memory,
probe_log, known_warps, known_ports). Seats only ever read it back through the
fogged observation (observation.build_observation).
"""

from __future__ import annotations

from typing import Any

from . import constants as K
from .actions import Action, ActionResult
from .models import EventKind, MineType, Universe


def friendly(universe: Universe, pid: str, owner_id: str | None) -> bool:
    """Yours, your corp's or an ally's (fighters that neither stop a probe nor block a report)."""
    if owner_id is None:
        return True
    from .combat import _are_allied

    return owner_id == pid or _are_allied(universe, pid, owner_id)


def hostile_fighters(universe: Universe, pid: str, sector_id: int) -> bool:
    """s13/s17: any fighter of somebody else, in any mode."""
    sector = universe.sectors.get(sector_id)
    dep = sector.fighters if sector is not None else None
    if dep is None or int(dep.count) <= 0:
        return False
    from .corp import deploy_friend
    return not deploy_friend(universe, pid, dep)


def limpet_visible(universe: Universe, viewer_id: str, owner_id: str) -> bool:
    """s12: limpets sit 'almost invisible'. You see your own and your corp's."""
    if owner_id == viewer_id:
        return True
    viewer = universe.players.get(viewer_id)
    owner = universe.players.get(owner_id)
    return bool(viewer and owner and viewer.corp_ticker and viewer.corp_ticker == owner.corp_ticker)


def _fighter_view(s) -> dict[str, Any] | None:
    if s.fighters is None or int(s.fighters.count) <= 0:
        return None
    row: dict[str, Any] = {"owner_id": s.fighters.owner_id, "count": int(s.fighters.count),
                           "mode": s.fighters.mode.value}
    if K.corp_rules_on():  # CORP_RULES.md cr17 / TWI 433-436 (QC 57): the display says Personal or Corporate
        row["ownership"] = ("rogue" if s.fighters.owner_id == K.ROGUE_OWNER_ID
                            else "corporate" if getattr(s.fighters, "corp_ticker", None) else "personal")
    return row


def visible_mines(universe: Universe, viewer_id: str, sector) -> list[dict[str, Any]]:
    out = []
    for m in sector.mines:
        if int(m.count) <= 0:
            continue
        if m.kind == MineType.LIMPET and not limpet_visible(universe, viewer_id, m.owner_id):
            if not (K.corp_rules_on() and getattr(m, "corp_ticker", None) and
                    universe.players.get(viewer_id) and
                    universe.players[viewer_id].corp_ticker == m.corp_ticker):
                continue
        label = m.owner_id
        if K.corp_rules_on():
            if m.owner_id == K.ROGUE_OWNER_ID:
                label = "rogue"
            elif getattr(m, "corp_ticker", None):
                label = "corporate"
            else:
                label = "personal"
        out.append({"owner": label if K.corp_rules_on() else m.owner_id, "kind": m.kind.value, "count": int(m.count)})
    return out


def traders_in(universe: Universe, viewer_id: str, sector, *, combat_scan: bool = False) -> list[dict[str, Any]]:
    """s11: other traders in a sector, 'w/ N ftrs, in <ship>'.

    combat_scan (your own sector only): a Combat Scanner hull also reads their shields (COMBAT_SCANNER_MODE).
    """
    viewer = universe.players.get(viewer_id)
    scanner = (combat_scan and K.combat_scanner_on() and viewer is not None
               and viewer.ship.ship_class.value in K.COMBAT_SCANNER_HULLS)
    out = []
    for oid in sector.occupant_ids:
        if oid == viewer_id or oid not in universe.players:
            continue
        o = universe.players[oid]
        if not o.alive:
            continue
        if K.hardware_tw2002() and getattr(o.ship, "cloaked", False):
            continue  # h15: cloaked ships hidden even from corp location / scans
        out.append({"id": oid, "name": o.name, "ship_name": o.ship.name, "ship_class": o.ship.ship_class.value,
                    "fighters": int(o.ship.fighters)})
        if scanner:
            out[-1]["shields"] = int(o.ship.shields)
    return out


def _ferrengi_in(universe: Universe, sector_id: int) -> list:
    return [f for f in universe.ferrengi.values() if f.sector_id == sector_id and f.alive]


def density_reading(universe: Universe, sector_id: int) -> dict[str, Any]:
    """s6/s7: one sector's density, warps out, nav hazard and anomaly."""
    s = universe.sectors[sector_id]
    density = 0
    anomaly = False
    if s.fighters is not None and int(s.fighters.count) > 0:
        density += K.DENSITY_PER_FIGHTER * int(s.fighters.count)
    for m in s.mines:
        if m.kind == MineType.LIMPET:
            if int(m.count) > 0:
                density += K.DENSITY_PER_LIMPET * int(m.count)
                anomaly = True
        elif m.kind == MineType.ARMID:
            density += K.DENSITY_PER_ARMID * int(m.count)
    cloaked_here = False
    ships = 0
    for oid in s.occupant_ids:
        if oid not in universe.players:
            continue
        pl = universe.players[oid]
        if not pl.alive:
            continue
        if K.hardware_tw2002() and getattr(pl.ship, "cloaked", False):
            cloaked_here = True
            continue  # h15: cloaked ship density 0
        ships += 1
    # Players already counted in ships; Ferrengi use hull density under tw2002.
    density += K.DENSITY_PER_SHIP * ships
    from .ferrengi import ferrengi_density
    for f in _ferrengi_in(universe, sector_id):
        density += int(ferrengi_density(f))
    if K.alien_on():  # ALIEN_TRADERS.md al23: an alien counts as a manned ship
        density += K.DENSITY_PER_SHIP * sum(
            1 for alien in universe.aliens.values()
            if alien.alive and alien.sector_id == sector_id
        )
    if K.fleet_on():  # SHIP_FLEET.md fl22: 38 per uncloaked unmanned ship (manned stays 40)
        from .fleet import density_unmanned
        um_density, um_anomaly = density_unmanned(universe, sector_id)
        density += um_density
        cloaked_here = cloaked_here or um_anomaly
    if cloaked_here:
        anomaly = True
    if s.port is not None:
        density += K.DENSITY_PER_PORT
    density += K.DENSITY_PER_PLANET * sum(1 for p in s.planet_ids if p in universe.planets)
    # CLASS0_TERRA.md t23: Terra adds planet density to sector 1 (not a Planet row).
    if K.class0_tw2002() and K.info_tw2002() and int(sector_id) == K.STARDOCK_SECTOR:
        if getattr(universe, "terra_colonists", None) is not None:
            density += K.DENSITY_PER_PLANET
    # fedspace-police-v1 f2: Federal starship densities
    if K.fed_tw2002() and K.info_tw2002():
        from .fed import fed_density_bonus
        density += fed_density_bonus(universe, sector_id)
    navhaz = 0
    if K.hardware_tw2002():  # SHIP_HARDWARE_V2.md v9/v24: beacon 1, NavHaz 21 per percent
        from .hardware import navhaz_pct
        navhaz = navhaz_pct(s)
        density += K.DENSITY_PER_NAVHAZ_PCT * navhaz
        if getattr(s, "beacon", None):
            density += K.DENSITY_PER_BEACON
    return {"density": density, "warps": len(s.warps), "navhaz": navhaz, "anomaly": anomaly}


def sector_view(universe: Universe, viewer_id: str, sector_id: int) -> dict[str, Any]:
    """s9/s13: what a holo scan or a passing probe shows of one sector (no stock, no limpets)."""
    s = universe.sectors[sector_id]
    view: dict[str, Any] = {
        "port": (
            (
                lambda p: {
                    "name": p.name,
                    "code": ("0" if getattr(p, "special", None) in ("alpha_centauri", "rylos") else p.code),
                    "class_id": int(p.class_id),
                    **(
                        {"special": p.special, "sells": ["fighters", "shields", "holds"]}
                        if getattr(p, "special", None) in ("alpha_centauri", "rylos")
                        else {}
                    ),
                }
            )(s.port)
            if s.port is not None else None
        ),
        "planets": [{"name": universe.planets[p].name, "class": universe.planets[p].class_id.value}
                    for p in s.planet_ids if p in universe.planets],
        "traders": traders_in(universe, viewer_id, s),
        "ferrengi": (
            [{"name": f.name, "fighters": int(f.fighters),
              "hull": getattr(f, "hull", "") or None,
              "shields": int(f.shields)} for f in _ferrengi_in(universe, sector_id)]
            if K.ferrengi_tw2002()
            else [{"name": f.name, "fighters": int(f.fighters)} for f in _ferrengi_in(universe, sector_id)]
        ),
        "fighters": _fighter_view(s),
        # Limpets never show on a holo or a probe (SCANNERS_HIDDEN_INFO.md s9/s13), even your own.
        "mines": [m for m in visible_mines(universe, viewer_id, s) if m["kind"] != MineType.LIMPET.value],
    }
    if K.alien_on():  # ALIEN_TRADERS.md al24: holo and probe show the real hull
        from .alien import alien_brief
        view["aliens"] = [
            alien_brief(alien)
            for alien in sorted(universe.aliens.values(), key=lambda row: row.id)
            if alien.alive and alien.sector_id == sector_id
        ]
    if K.fed_outpost_tw2002() and view["port"] is not None:  # CLASS0_TERRA.md t25: same label as the sector view
        from .class0 import fed_outpost_label, is_fed_outpost
        if is_fed_outpost(s.port, sector_id):
            fed_outpost_label(view["port"])
    if K.hardware_tw2002() and getattr(s, "beacon", None):
        view["beacon"] = s.beacon  # the text only; who launched it is never shown
    if K.fed_tw2002():
        from .fed import federals_in_sector
        view["federals"] = [{"name": f.name, "title": f.title} for f in federals_in_sector(universe, sector_id)]
    if K.fleet_on():  # SHIP_FLEET.md fl22: never inside "traders"
        from .fleet import sector_unmanned_view
        view["unmanned_ships"] = sector_unmanned_view(universe, viewer_id, sector_id)
    return view


def scan_turns(tier: str) -> int:
    return int(K.SCAN_TURNS_TW2002.get(tier, 1))


def scan_reason(universe: Universe, pid: str, tier: str | None) -> str | None:
    """Why `scan tier=<tier>` is illegal now (the legal list and the handler share this)."""
    player = universe.players[pid]
    tiers = K.scan_tiers(getattr(player.ship, "scanner", None))
    if not tiers:
        room = K.scanner_room(player.ship.ship_class.value)
        if room is None:
            return "this hull cannot carry a long range scanner"
        return "no long range scanner (buy_equip density_scanner or holo_scanner at StarDock)"
    tier = tier or tiers[0]
    if tier not in tiers:
        if tier in (K.SCANNER_DENSITY, K.SCANNER_HOLO):
            return f"{tier} scan needs a holo scanner" if tier == K.SCANNER_HOLO else f"no {tier} scanner"
        return f"unknown scan tier {tier!r}"
    if player.turns_today + scan_turns(tier) > player.turns_per_day:
        return "out of turns"
    return None


def handle_scan(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    sector = universe.sectors[player.sector_id]
    tiers = K.scan_tiers(getattr(player.ship, "scanner", None))
    raw = action.args.get("tier")
    tier = str(raw).lower() if raw else (tiers[0] if tiers else K.SCANNER_DENSITY)
    why = scan_reason(universe, pid, tier)
    if why is not None:
        return ActionResult(ok=False, error=why)
    cost = scan_turns(tier)
    from .runner import _learn_sector

    _learn_sector(player, universe, sector.id)  # your own sector's lanes, as on arrival
    stamp = {"day": universe.day, "tick": universe.tick, "from": sector.id, "tier": tier}
    readings: list[dict[str, Any]] = []
    for wid in sector.warps:
        wid = int(wid)
        prev = player.scan_memory.get(wid) or {}
        entry: dict[str, Any] = {**stamp, **density_reading(universe, wid)}
        if tier == K.SCANNER_HOLO:
            entry.update(sector_view(universe, pid, wid))
            entry["has_holo"] = True
            entry["holo_day"] = stamp["day"]
            entry["holo_tick"] = stamp["tick"]
        elif prev.get("has_holo"):
            # A free density refresh must not erase a prior holo reading (QC).
            for k in ("port", "planets", "traders", "ferrengi", "fighters", "mines", "beacon", "aliens"):
                if k in prev:
                    entry[k] = prev[k]
            entry["has_holo"] = True
            entry["holo_day"] = prev.get("holo_day", prev.get("day"))
            entry["holo_tick"] = prev.get("holo_tick", prev.get("tick"))
        player.scan_memory[wid] = entry
        readings.append({"id": wid, **entry})
    universe.emit(
        EventKind.SCAN,
        actor_id=pid,
        sector_id=sector.id,
        payload={"tier": tier, "neighbors": readings},
        summary=(f"{player.name} ran a density scan from {sector.id}" if tier == K.SCANNER_DENSITY
                 else f"{player.name} ran a holo scan from {sector.id}"),
    )
    return ActionResult(ok=True, turns_spent=cost)


def probe_route(universe: Universe, src: int, dst: int) -> list[int]:
    from .runner import _bfs_path

    return _bfs_path(universe, src, dst, max_depth=K.PROBE_MAX_HOPS)


def probe_reason(universe: Universe, pid: str, target: Any) -> str | None:
    player = universe.players[pid]
    if int(player.ship.ether_probes or 0) <= 0:
        return "no ether probes loaded"
    try:
        tid = int(target)
    except (TypeError, ValueError):
        return "invalid target sector"
    if tid not in universe.sectors:
        return "invalid target sector"
    if tid == player.sector_id:
        return "the probe is already in that sector"
    if player.turns_today + int(K.TURN_COST["scan"]) > player.turns_per_day:
        return "out of turns"
    if not probe_route(universe, player.sector_id, tid):
        return f"no route within {K.PROBE_MAX_HOPS} hops"
    return None


def handle_probe(universe: Universe, pid: str, action: Action) -> ActionResult:
    """s13: fly the route, explore each sector, die at the first hostile fighters."""
    from .runner import _learn_sector, _record_port_intel

    player = universe.players[pid]
    target = action.args.get("target")
    why = probe_reason(universe, pid, target)
    if why is not None:
        return ActionResult(ok=False, error=why)
    tid = int(target)
    cost = int(K.TURN_COST["scan"])
    route = probe_route(universe, player.sector_id, tid)
    player.ship.ether_probes -= 1
    reported: list[int] = []
    destroyed_at: int | None = None
    for sid in route:
        if hostile_fighters(universe, pid, sid):
            destroyed_at = sid
            player.probe_log[sid] = {"day": universe.day, "tick": universe.tick,
                                     "intel": {"sector_id": sid, "probe_destroyed": True}}
            break
        sec = universe.sectors[sid]
        _learn_sector(player, universe, sid)
        if sec.port is not None:
            _record_port_intel(player, sid, sec.port, universe=universe)
        intel = {"sector_id": sid, "warps_out": [int(w) for w in sec.warps], **sector_view(universe, pid, sid)}
        player.probe_log[sid] = {"day": universe.day, "tick": universe.tick, "intel": intel}
        reported.append(sid)
    # PROBE is an actor-only event: the firer is told (s13), the fighters' owner is not.
    end = destroyed_at if destroyed_at is not None else tid
    summary = (f"{player.name}'s probe was destroyed by fighters in {destroyed_at} after {len(reported)} sectors"
               if destroyed_at is not None
               else f"{player.name}'s probe reached {tid} ({len(reported)} sectors) and self-destructed")
    universe.emit(
        EventKind.PROBE,
        actor_id=pid,
        sector_id=end,
        payload={"target": tid, "port_code": None, "route": reported, "destroyed_at": destroyed_at},
        summary=summary,
    )
    return ActionResult(ok=True, turns_spent=cost)


def port_report(universe: Universe, player, sector_id: int, entry: dict[str, Any]) -> dict[str, Any]:
    """s16/s17: the CIM port report for one remembered port, as the observation shows it."""
    from .economy import port_buy_price, port_sell_price

    e = dict(entry)
    sector = universe.sectors.get(int(sector_id))
    explored = int(sector_id) in (player.known_warps or {})
    if sector is None or sector.port is None or not explored:
        e["report"] = "remembered"
        return e
    if hostile_fighters(universe, player.id, int(sector_id)):
        e["report"] = "blocked"
        return e
    port = sector.port
    stock: dict[str, dict[str, Any]] = {}
    for c, s in port.stock.items():
        row: dict[str, Any] = {"current": s.current, "max": s.maximum}
        if port.buys(c):
            row["price"] = port_buy_price(port, c, player.experience)
            row["side"] = "buys_from_player"
        elif port.sells(c):
            row["price"] = port_sell_price(port, c, player.experience)
            row["side"] = "sells_to_player"
        stock[c.value] = row
    e.update({"class": port.class_id.code, "stock": stock, "last_seen_day": universe.day, "report": "live"})
    return e
