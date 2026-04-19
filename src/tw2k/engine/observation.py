"""Observation builder — constructs the limited-information view an agent sees."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .economy import port_buy_price, port_sell_price
from .models import Commodity, Event, EventKind, PortClass, Universe
from .runner import full_net_worth

# ---------------------------------------------------------------------------
# Fog of war — per-agent event visibility rules.
#
# The full universe.events feed is god-mode data for the spectator UI. Agents
# must see a filtered view: their own actions, events in their own sector,
# and things explicitly addressed to them (hails, corp/alliance traffic).
# Leaking other players' warps/genesis/citadel/trade events breaks the core
# TW2002 intel loop — if opponents' moves show up in your turn, there's no
# reason to scout or probe. Fix: classify each EventKind and filter.
# ---------------------------------------------------------------------------

# Visible to every player. Galaxy-wide drama / public channels.
_PUBLIC_EVENTS: frozenset[EventKind] = frozenset({
    EventKind.GAME_START,
    EventKind.DAY_TICK,
    EventKind.GAME_OVER,
    EventKind.PLAYER_ELIMINATED,
    EventKind.PLANET_ORPHANED,
    EventKind.BROADCAST,
    EventKind.PORT_DESTROYED,
    EventKind.ATOMIC_DETONATION,
    EventKind.FERRENGI_SPAWN,
})

# Visible ONLY to actor_id. Personal actions, internal errors, private intel.
_ACTOR_ONLY_EVENTS: frozenset[EventKind] = frozenset({
    EventKind.SCAN,
    EventKind.PROBE,
    EventKind.BUY_SHIP,
    EventKind.BUY_EQUIP,
    EventKind.AGENT_THOUGHT,
    EventKind.AGENT_ERROR,
    EventKind.WARP_BLOCKED,
    EventKind.TRADE_FAILED,
    EventKind.AUTOPILOT,
    EventKind.LIMPET_REPORT,
    EventKind.PHOTON_FIRED,
    EventKind.FED_RESPONSE,
})

# Party-restricted events — visibility derived from payload.
_HAIL_EVENTS: frozenset[EventKind] = frozenset({EventKind.HAIL})
_CORP_EVENTS: frozenset[EventKind] = frozenset({
    EventKind.CORP_CREATE,
    EventKind.CORP_INVITE,
    EventKind.CORP_JOIN,
    EventKind.CORP_LEAVE,
    EventKind.CORP_DEPOSIT,
    EventKind.CORP_WITHDRAW,
    EventKind.CORP_MEMO,
})
_ALLIANCE_EVENTS: frozenset[EventKind] = frozenset({
    EventKind.ALLIANCE_PROPOSED,
    EventKind.ALLIANCE_FORMED,
    EventKind.ALLIANCE_BROKEN,
})


def _event_visible_to(event: Event, player_id: str, universe: Universe) -> bool:
    """Return True if `event` is visible to `player_id` under fog of war.

    Default rule for anything not matched by the tables above is
    "witnessed" — the actor always sees their own events, plus anyone who
    was in `event.sector_id` at emit time (captured via payload._witnesses).
    """
    kind = event.kind
    if kind in _PUBLIC_EVENTS:
        return True
    if kind in _ACTOR_ONLY_EVENTS:
        return event.actor_id == player_id
    if kind in _HAIL_EVENTS:
        target = event.payload.get("target")
        return event.actor_id == player_id or target == player_id
    if kind in _CORP_EVENTS:
        if event.actor_id == player_id:
            return True
        ticker = event.payload.get("ticker")
        if not ticker:
            return False
        corp = universe.corporations.get(ticker)
        if corp is None:
            return False
        # Members AND invited players can see corp traffic relevant to them.
        return player_id in corp.member_ids or player_id in corp.invited_ids
    if kind in _ALLIANCE_EVENTS:
        if event.actor_id == player_id:
            return True
        # ALLIANCE_PROPOSED addresses a specific target.
        if event.payload.get("target") == player_id:
            return True
        aid = event.payload.get("alliance_id")
        if aid is not None:
            ally = universe.alliances.get(aid)
            if ally is not None and player_id in ally.member_ids:
                return True
        # Fallback — some payloads ship `members` directly.
        members = event.payload.get("members")
        if isinstance(members, (list, tuple)) and player_id in members:
            return True
        return False
    # Default — sector witnesses + actor.
    if event.actor_id == player_id:
        return True
    witnesses = event.payload.get("_witnesses")
    if isinstance(witnesses, (list, tuple, set)):
        return player_id in witnesses
    # If we have no witness list (very old events, or emitted without
    # sector_id), fall back to "actor only" — safest default, prevents leaks.
    return False


def _filter_visible_events(
    events: list[Event], player_id: str, universe: Universe, limit: int
) -> list[Event]:
    """Walk backwards from the newest event, collecting up to `limit`
    that are visible to `player_id`."""
    out: list[Event] = []
    for ev in reversed(events):
        if _event_visible_to(ev, player_id, universe):
            out.append(ev)
            if len(out) >= limit:
                break
    out.reverse()
    return out


def _event_to_dict(event: Event) -> dict[str, Any]:
    """Convert an Event to the dict shape exposed in observations, stripping
    private-metadata keys (anything starting with underscore, like _witnesses).
    """
    clean_payload: dict[str, Any] = {}
    for k, v in (event.payload or {}).items():
        if isinstance(k, str) and k.startswith("_"):
            continue
        clean_payload[k] = v
    return {
        "seq": event.seq,
        "day": event.day,
        "tick": event.tick,
        "kind": event.kind.value,
        "actor_id": event.actor_id,
        "sector_id": event.sector_id,
        "summary": event.summary,
        # Payload is not currently included in the observation schema
        # (see class Observation below), but if we ever start exposing it,
        # this ensures _witnesses never leaks.
        # "payload": clean_payload,
    }


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
    # Persistent 3-horizon goals the agent itself wrote last turn. Surfacing
    # them in the observation forces commitment: if the agent said "save for
    # cargotran" yesterday and today is at StarDock with 45k, the goal is
    # right there at the top reminding them to execute.
    goals: dict[str, str] = Field(default_factory=dict)
    alive: bool = True
    net_worth: int = 0
    # Planets this player owns (subset view; one entry per planet).
    owned_planets: list[dict[str, Any]] = Field(default_factory=list)

    # Current sector full detail
    sector: dict[str, Any]
    adjacent: list[dict[str, Any]]

    # Port intel database (persistent across turns)
    known_ports: list[dict[str, Any]]

    # Last N trades this player executed (capped at 5 in the observation —
    # full 50-entry ledger lives on the Player). Each entry carries the
    # post-haggle unit price AND the realized profit on sells so the
    # agent can answer "what did my loop actually earn me?" without
    # reconstructing from the rolling global event feed.
    trade_log: list[dict[str, Any]] = Field(default_factory=list)

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

    # Known ports database (most profitable view first). Each entry also
    # gets an `age_days` field derived from `last_seen_day` so the agent
    # can tell stale-vs-fresh intel at a glance. Prices/stock can drift
    # significantly between visits; without this the LLM happily commits
    # to plans built on 3-day-old snapshots.
    known_ports: list[dict[str, Any]] = []
    for sid, entry in sorted(player.known_ports.items()):
        e = {"sector_id": sid, **entry}
        lsd = entry.get("last_seen_day")
        if isinstance(lsd, int):
            e["age_days"] = max(0, universe.day - lsd)
        known_ports.append(e)

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

    # Recent events — filtered by per-agent fog of war. Agents only see
    # events they witnessed, acted upon, or were explicitly addressed by
    # (hails, corp/alliance traffic, public broadcasts). Other commanders'
    # warps, planet deploys, and citadel builds are NOT leaked here — that
    # forces the classic TW2002 intel loop (scouting, probes, limpets).
    recent = _filter_visible_events(universe.events, player_id, universe, event_history)
    recent_events = [_event_to_dict(e) for e in recent]

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
        # Compute YOUR share of the treasury. Now that full_net_worth
        # attributes treasury proportionally, members need to see their
        # own slice directly so they can reason about deposits as a
        # value-preserving team investment rather than a score sink.
        alive_members = [
            mid for mid in c.member_ids
            if mid in universe.players and universe.players[mid].alive
        ]
        treasury_share = (
            c.treasury // len(alive_members) if alive_members else 0
        )
        # Pull the last 5 corp_memos out of the inbox so the team channel
        # is at-a-glance visible without scanning all 40 inbox entries.
        # Memos appear in every member's inbox, so reading from the
        # current player's inbox gives a consistent feed.
        recent_memos = [
            {
                "from": m.get("from"),
                "day": m.get("day"),
                "tick": m.get("tick"),
                "message": m.get("message"),
            }
            for m in (player.inbox or [])
            if m.get("kind") == "corp_memo" and m.get("ticker") == c.ticker
        ][-5:]
        corp_summary = {
            "ticker": c.ticker,
            "name": c.name,
            "ceo_id": c.ceo_id,
            "members": list(c.member_ids),
            "treasury": c.treasury,
            "treasury_share": treasury_share,
            "planet_ids": list(c.planet_ids),
            "recent_memos": recent_memos,
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
        goals={
            "short": getattr(player, "goal_short", "") or "",
            "medium": getattr(player, "goal_medium", "") or "",
            "long": getattr(player, "goal_long", "") or "",
        },
        alive=player.alive,
        # Full net worth (ship assets + every owned planet). Using the
        # universe-aware helper so the agent's self-reported number
        # matches the victory check exactly — no more "I had 24k in the
        # UI but actually won/lost on a different total" surprises.
        net_worth=full_net_worth(universe, player),
        owned_planets=owned_planets,
        sector=sector_info,
        adjacent=adjacent,
        known_ports=known_ports,
        trade_log=list(getattr(player, "trade_log", []) or [])[-5:],
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
    # Per-commodity cost basis. `cargo_cost_avg` is the weighted-average
    # unit price the player actually paid for what's currently in the hold
    # (ints, rounded for readability — float precision isn't meaningful
    # at the 1-cr granularity the LLM reasons at). `cargo_value_at_cost` is
    # the product qty*avg, so the agent has an immediate "break-even sell"
    # number right next to the cargo qty.
    cargo_qty = {c.value: ship.cargo.get(c, 0) for c in Commodity}
    cargo_cost = getattr(ship, "cargo_cost", {}) or {}
    cost_avg: dict[str, int] = {}
    cost_total: dict[str, int] = {}
    for c in Commodity:
        qty = ship.cargo.get(c, 0)
        if qty > 0:
            avg = float(cargo_cost.get(c, 0.0) or 0.0)
            cost_avg[c.value] = round(avg)
            cost_total[c.value] = round(avg * qty)
    return {
        "class": ship.ship_class.value,
        "holds": ship.holds,
        "cargo": cargo_qty,
        "cargo_cost_avg": cost_avg,
        "cargo_value_at_cost": cost_total,
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

    hints: list[str] = []

    # Prior-turn goals FIRST — this is the commitment mechanism. If the agent
    # said last turn "save 45k for cargotran", we want that to be the very
    # first thing in the hint stream this turn, not buried below movement/
    # port notes. An unwritten goal is a drifting goal.
    if player is not None:
        g_short = (getattr(player, "goal_short", "") or "").strip()
        g_med = (getattr(player, "goal_medium", "") or "").strip()
        g_long = (getattr(player, "goal_long", "") or "").strip()
        if g_short or g_med or g_long:
            parts: list[str] = []
            if g_short:
                parts.append(f"NOW: {g_short}")
            if g_med:
                parts.append(f"DAY: {g_med}")
            if g_long:
                parts.append(f"MATCH: {g_long}")
            hints.append("YOUR GOALS — " + " / ".join(parts))
        else:
            hints.append(
                "GOALS EMPTY — set `goal_short`/`goal_medium`/`goal_long` in "
                "your JSON output so future you knows the plan."
            )

    hints.append(
        "Verbs available: warp trade scan wait + 29 more (see system prompt)."
    )

    # Low-turns warning: loudly tell the agent what it CANNOT do this turn.
    # Without this, agents (esp. CargoTran with 3-turns/warp) repeatedly
    # submit warps when turns_remaining < 3 and the engine rejects them,
    # which flooded the feed with 30+ consecutive "out of turns" errors.
    turns_rem: int | None = None
    if player is not None:
        tpd = getattr(player, "turns_per_day", None)
        tod = getattr(player, "turns_today", None)
        if isinstance(tpd, int) and isinstance(tod, int):
            turns_rem = tpd - tod
    ship = getattr(player, "ship", None) if player is not None else None
    warp_cost = K.TURN_COST.get("warp", 2)
    if ship is not None:
        spec = K.SHIP_SPECS.get(getattr(ship.ship_class, "value", ""))
        if spec and "turns_per_warp" in spec:
            warp_cost = int(spec["turns_per_warp"])
    trade_cost = K.TURN_COST.get("trade", 3)
    if isinstance(turns_rem, int) and turns_rem >= 0:
        blocked: list[str] = []
        if turns_rem < warp_cost:
            blocked.append(f"warp (needs {warp_cost})")
        if turns_rem < trade_cost:
            blocked.append(f"trade (needs {trade_cost})")
        if blocked:
            hints.append(
                f"LOW TURNS — turns_remaining={turns_rem}. "
                f"Cannot: {', '.join(blocked)}. "
                f"End the day with `wait` (burns 1 turn) or do a 1-turn action "
                f"like `scan` / `transmit`. Do NOT spam warp/trade."
            )

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

        # Cargo P&L vs. this port: if the player is carrying commodities the
        # port buys, show break-even + expected realized profit at LIST price.
        # This is the concrete number that protects against selling at a loss
        # and lets the agent decide "actually, haggle up — this port's offer
        # is under my cost basis."
        ship = getattr(player, "ship", None) if player is not None else None
        cargo = getattr(ship, "cargo", None) if ship is not None else None
        cargo_cost = getattr(ship, "cargo_cost", None) if ship is not None else None
        if cargo and cargo_cost:
            buys_set = set(port.get("buys") or [])
            stock_map = port.get("stock") or {}
            pnl_parts: list[str] = []
            for commodity_name, qty in cargo.items():
                key = getattr(commodity_name, "value", str(commodity_name))
                if not isinstance(qty, int) or qty <= 0:
                    continue
                if key not in buys_set:
                    continue
                avg = float(cargo_cost.get(commodity_name, 0.0) or 0.0)
                stock_entry = stock_map.get(key) or {}
                bid = stock_entry.get("price")
                if not isinstance(bid, int):
                    continue
                delta = bid - avg
                realized = round(delta * qty)
                sign = "+" if realized >= 0 else ""
                pnl_parts.append(
                    f"{qty} {key} cost={avg:.0f}cr, port bids {bid}cr -> {sign}{realized}cr"
                )
            if pnl_parts:
                hints.append("P&L at this port: " + " | ".join(pnl_parts))

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

        # Affordable-ship menu: list the ship classes the player can ACTUALLY
        # afford right now, sorted by hold count. V7 showed LLM agents sitting
        # on 50k cash without upgrading because the prompt said "upgrade around
        # 100-150k" and they took it literally. This surfaces the concrete set
        # of legal buy_ship targets and the cargo/fighter trade-offs so the
        # agent can make a grounded decision on day 1-2.
        if player is not None:
            credits = int(getattr(player, "credits", 0) or 0)
            cur_ship = getattr(player, "ship", None)
            cur_class_val = getattr(getattr(cur_ship, "ship_class", None), "value", None)
            cur_holds = int(getattr(cur_ship, "holds", 0) or 0) if cur_ship is not None else 0
            alignment = int(getattr(player, "alignment", 0) or 0)
            in_corp = bool(getattr(player, "corp_ticker", None))
            affordable: list[str] = []
            for class_key, spec in K.SHIP_SPECS.items():
                if class_key == cur_class_val:
                    continue
                cost = int(spec.get("cost", 0))
                if cost <= 0 or cost > credits:
                    continue
                if spec.get("corp_only") and not in_corp:
                    continue
                min_align = int(spec.get("min_alignment", -10**9))
                if alignment < min_align:
                    continue
                holds = int(spec.get("holds", 0))
                disp = spec.get("display_name", class_key)
                tag = f"{disp} ({cost:,}cr, {holds}h)"
                if holds > cur_holds and cur_holds > 0:
                    tag += f" x{holds / cur_holds:.1f}"
                affordable.append(tag)
            if affordable:
                # Keep the list short so it doesn't dominate the hint stream.
                shown = ", ".join(affordable[:4])
                hints.append(
                    f"Ships you can afford NOW ({credits:,}cr): {shown}. "
                    f"Use `buy_ship class=<snake_case_name>` to upgrade."
                )
            else:
                # Give a concrete ladder target so they know what to save for.
                next_up = min(
                    (
                        (int(s["cost"]), k, s.get("display_name", k))
                        for k, s in K.SHIP_SPECS.items()
                        if k != cur_class_val
                        and int(s.get("cost", 0)) > credits
                        and not s.get("corp_only", False)
                    ),
                    default=None,
                )
                if next_up is not None:
                    cost, _, disp = next_up
                    hints.append(
                        f"Next ship in budget: {disp} at {cost:,}cr "
                        f"(need {cost - credits:,} more) — keep trading."
                    )

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

    # Inbox backlog — FYI only. Distinguishing direct hails from broadcasts
    # and corp memos matters because each channel has different relevance:
    # hails are 1:1 intent, broadcasts are galaxy noise, corp_memos are team
    # coordination from a group you've already committed to. Framing is
    # "you have N messages" not "you must respond" — the agent decides.
    inbox = getattr(player, "inbox", None) if player is not None else None
    if inbox:
        recent = inbox[-20:]
        unread_hails = sum(
            1 for m in recent if not m.get("read") and m.get("kind") == "hail"
        )
        unread_bcasts = sum(
            1 for m in recent if not m.get("read") and m.get("kind") == "broadcast"
        )
        unread_memos = sum(
            1 for m in recent if not m.get("read") and m.get("kind") == "corp_memo"
        )
        unread_invites = sum(
            1 for m in recent if not m.get("read") and m.get("kind") == "corp_invite"
        )
        total_unread = unread_hails + unread_bcasts + unread_memos + unread_invites
        if total_unread:
            parts = []
            if unread_hails:
                parts.append(f"{unread_hails} hail(s)")
            if unread_bcasts:
                parts.append(f"{unread_bcasts} broadcast(s)")
            if unread_memos:
                parts.append(f"{unread_memos} corp memo(s)")
            if unread_invites:
                parts.append(f"{unread_invites} corp invite(s)")
            hints.append(
                f"FYI: {' + '.join(parts)} in inbox — see `inbox` field. "
                "No obligation to reply; respond only if it serves your goals."
            )

    # Soft situational awareness — these are FYI nudges, not mandates. The
    # philosophy: surface state the agent might have missed; let it decide
    # whether to act. A smarter LLM should route around these correctly.
    if player is not None and ship is not None:
        # Unarmed-in-deep-space awareness. Post-match forensics on seed 7777
        # showed both eliminated players died with 0 ship fighters / 0 shields
        # against Ferrengi battleships. This is pure information, no nudge
        # to do something specific.
        ship_fighters = int(getattr(ship, "fighters", 0) or 0)
        ship_shields = int(getattr(ship, "shields", 0) or 0)
        cur_sid = sector_info.get("id")
        in_fedspace = cur_sid in K.FEDSPACE_SECTORS if cur_sid is not None else False
        if ship_fighters == 0 and ship_shields == 0:
            if in_fedspace:
                hints.append(
                    f"FYI: ship has 0 fighters / 0 shields. StarDock sells "
                    f"fighters (~{K.FIGHTER_COST}cr ea). Deep-space Ferrengi "
                    f"favor unarmed targets."
                )
            else:
                hints.append(
                    "FYI: in deep space with 0 fighters / 0 shields — "
                    "Ferrengi that enter this sector will likely attack. "
                    "StarDock (sec 1) has the fighter shop."
                )

        # Multi-planet expansion hint. Tiered by how many planets the agent
        # already owns, because the strategic tradeoff shifts:
        #   1 planet  -> "cluster near it (easy ferry) OR diversify (risk spread)"
        #   2 planets -> "empire forming; a 3rd roughly doubles production headroom"
        #   3+ planets-> "dominant builder path — each new planet compounds"
        # In every case it's a one-line FYI. The agent decides WHERE and WHEN.
        # Names surface the sectors they already own so the LLM can reason
        # about "near here vs far away" without re-reading owned_planets[*].
        genesis_loaded = int(getattr(ship, "genesis", 0) or 0)
        credits_now = int(getattr(player, "credits", 0) or 0)
        n_planets = len(owned_planets) if owned_planets else 0
        if (
            n_planets >= 1
            and genesis_loaded == 0
            and credits_now >= K.GENESIS_TORPEDO_COST
        ):
            sector_list = ", ".join(
                f"s{p.get('sector_id')}" for p in owned_planets[:3] if p.get("sector_id") is not None
            )
            if n_planets == 1:
                hints.append(
                    f"FYI: you own 1 planet ({sector_list}) and could afford "
                    f"another Genesis ({K.GENESIS_TORPEDO_COST}cr at StarDock). "
                    f"Cluster near {sector_list} = cheap colonist ferry; "
                    f"build far away = risk spread if one planet falls."
                )
            elif n_planets == 2:
                hints.append(
                    f"FYI: you own 2 planets ({sector_list}) and could afford "
                    f"a 3rd Genesis ({K.GENESIS_TORPEDO_COST}cr). Empire forming — "
                    "a 3rd planet roughly doubles daily production capacity."
                )
            else:
                hints.append(
                    f"FYI: you own {n_planets} planets and could afford another "
                    f"Genesis ({K.GENESIS_TORPEDO_COST}cr). Top-tier commanders "
                    "run 5-15 planets; each new one compounds your income."
                )

        # Citadel-tier gap hint. Only fire when credits/treasury clearly
        # permit the next tier but the planet is noticeably short on idle
        # colonists — that exact shape is what capped Vex at L2 in the
        # last 30-day match.
        if owned_planets:
            for plan in owned_planets:
                lvl = int(plan.get("citadel_level", 0) or 0)
                tgt = int(plan.get("citadel_target", 0) or 0)
                if tgt > lvl or lvl >= 6:
                    continue  # already building OR maxed
                next_cost = K.CITADEL_TIER_COST[lvl]
                need_cr, need_col, _days = next_cost
                treasury = int(plan.get("treasury", 0) or 0)
                colonists = plan.get("colonists") or {}
                idle = int(colonists.get("colonists", 0) or 0)
                have_cr = treasury + credits_now
                if have_cr >= need_cr and idle < need_col and idle >= need_col // 2:
                    gap = need_col - idle
                    pid = plan.get("id")
                    hints.append(
                        f"FYI: planet {pid} is credit-ready for Citadel L{lvl + 1} "
                        f"({need_cr}cr, have {have_cr}). Short ~{gap} idle colonists "
                        f"(idle={idle}/{need_col})."
                    )
                    break  # only flag the first such planet to keep hint short

        # ---------- Corp awareness hints ----------
        # Soft nudges at moments where a corp would mechanically help. All
        # FYI-framed so an agent that prefers to fly solo can ignore them.
        # These fire only when the agent is NOT already in a corp, except
        # the invite-pending hint which fires from the inbox signal.
        in_corp = bool(getattr(player, "corp_ticker", None))
        corp_create_cost = getattr(K, "CORP_FORMATION_COST", 500_000)

        # Hint A — you have enough cash to form a corp and don't have one.
        # The purpose is to ensure the agent knows this branch exists at
        # the moment they're mechanically capable of taking it. The prompt
        # already explains corps; this just activates the verb at the
        # right cash threshold.
        if not in_corp and credits_now >= corp_create_cost:
            hints.append(
                f"FYI: you have {credits_now}cr (>= {corp_create_cost} cr for "
                "`corp_create` at StarDock). A corp unlocks corporate_flagship "
                "(20k fighters, 650k cr), pools treasury across members (your "
                "share counts toward net worth), grants mates friendly-fire "
                "immunity + shared planet access. Not required — solo is fine."
            )

        # Hint B — a corp invite is sitting unread in the inbox. The
        # invitee needs concrete mechanics to decide, not just "you have
        # an invite." This surfaces the cost/benefit inline so they don't
        # have to ask.
        inbox_now = getattr(player, "inbox", None) or []
        pending_invites = [
            m for m in inbox_now
            if m.get("kind") == "corp_invite" and not m.get("read")
        ]
        if pending_invites and not in_corp:
            inv = pending_invites[-1]  # most recent
            ticker = inv.get("ticker") or "?"
            hints.append(
                f"FYI: corp invite to [{ticker}] in inbox. Joining is free. "
                "Benefits: treasury share counts toward your net worth, "
                "friendly-fire immunity with mates, shared planet access, "
                "corporate_flagship unlock. Costs: deposits are one-way for "
                "non-CEO members (only CEO may withdraw). `corp_join "
                f'{{"ticker":"{ticker}"}}\' to accept.'
            )

        # Hint C — 2+ planets still solo. At this scale the coordination
        # costs of running an empire alone (colonist ferries, citadel
        # upgrade funding, defense coverage) start to bite. A corp partner
        # is one strategic answer; not the only one, so soft-frame it.
        if not in_corp and n_planets >= 2:
            hints.append(
                f"FYI: you run {n_planets} planets solo. A corp partner would "
                "pool treasury for faster citadel upgrades (your share of "
                "treasury counts), cover your planets with friendly fighters, "
                "and share colonist-ferry routes. `corp_create` (500k at "
                "StarDock) then `corp_invite` — or wait for someone to "
                "approach you."
            )

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
