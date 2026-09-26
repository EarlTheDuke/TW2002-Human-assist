"""Observation builder — constructs the limited-information view an agent sees."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .agency import is_minimal
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
    EventKind.MATCH_METRICS,
    EventKind.PLAYER_ELIMINATED,
    EventKind.PLANET_ORPHANED,
    EventKind.PLANET_CLAIMED,
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
    EventKind.PLANET_TAX_PAYOUT,
    # Out-of-band meta event — belongs to actor only (keeps opponents
    # from reading each other's token spend, which would be a weird
    # side-channel and also clutter their observation feed).
    EventKind.LLM_USAGE,
    EventKind.OPERATOR_DIRECTIVE_SET,
    EventKind.OPERATOR_DIRECTIVE_CLEARED,
    EventKind.OPERATOR_MESSAGE,
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


# ---------------------------------------------------------------------------
# Event → EventView (the presentation / media boundary)
# ---------------------------------------------------------------------------
#
# Parity S1 (docs/plans/2026-09-21-bot-human-parity.md). An `EventView` is the
# ONLY shape in which event payload data leaves the engine towards a seat:
# the Observation's `recent_events`, the harness `/events` stream, and any
# future cockpit media layer all consume it. Two guarantees:
#
#   * `summary` (plain text) is always present, so a text-only client or a
#     screen reader never needs `facts`.
#   * `facts` is a per-kind WHITELIST of payload keys. Anything not listed
#     here (private `_witnesses`, bulky scan `neighbors`, probe intel dumps,
#     LLM token usage, ...) never ships. Visibility (who may see the event
#     at all) is decided separately by `_event_visible_to`; this table only
#     decides which fields of a visible event are shown.
#
# Keep the lists small and semantic - they are the "event keys" a future
# still/clip asset manifest will bind to (e.g. warp + facts.from/to,
# combat + facts.exchange_kind). Never put derived game rules here.
EVENT_FACTS: dict[EventKind, tuple[str, ...]] = {
    EventKind.DAY_TICK: ("day",),
    EventKind.GAME_START: (),
    EventKind.GAME_OVER: ("reason", "net_worth", "credits"),
    EventKind.WARP: ("from", "to"),
    EventKind.WARP_BLOCKED: ("target",),
    EventKind.AUTOPILOT: ("target", "executed", "hops_done"),
    EventKind.TRADE: ("commodity", "qty", "side", "unit", "total", "realized_profit", "toll_to", "amount"),
    EventKind.TRADE_FAILED: ("commodity", "qty", "side", "reason"),
    EventKind.SCAN: ("tier",),
    EventKind.PROBE: ("target", "port_code"),
    EventKind.DEPLOY_FIGHTERS: ("qty", "mode"),
    EventKind.DEPLOY_MINES: ("qty", "kind"),
    EventKind.MINE_DETONATED: ("hits", "damage", "victim"),
    EventKind.PHOTON_FIRED: ("target",),
    EventKind.PHOTON_HIT: ("target", "disabled_ticks"),
    EventKind.ATOMIC_DETONATION: ("qty", "port_destroyed"),
    EventKind.PORT_DESTROYED: ("qty",),
    EventKind.COMBAT: (
        "exchange_kind", "vs", "attacker", "defender", "attacker_f", "attacker_s",
        "defender_f", "defender_s", "attacker_losses", "defender_losses", "sector_claimed",
        "planet_id", "planet_name", "citadel_level",
    ),
    EventKind.SHIP_DESTROYED: ("victim", "reason", "deaths", "death_sector", "killer_id", "kind", "bounty"),
    EventKind.PLAYER_ELIMINATED: ("killer", "deaths"),
    EventKind.PLANET_ORPHANED: ("planet_id", "planet_name", "former_owner"),
    EventKind.PLANET_CLAIMED: ("planet_id", "planet_name", "citadel_level", "fighters"),
    EventKind.FERRENGI_SPAWN: ("id", "aggression", "fighters"),
    EventKind.FERRENGI_MOVE: ("id", "from", "to", "reason"),
    EventKind.FERRENGI_ATTACK: ("victim",),
    EventKind.LAND_PLANET: ("planet_id", "class", "seized"),
    EventKind.LIFTOFF: ("planet_id",),
    EventKind.GENESIS_DEPLOYED: ("planet_id", "class", "name"),
    EventKind.ASSIGN_COLONISTS: ("planet_id", "qty", "to", "from"),
    EventKind.PLANET_CARGO_TRANSFER: ("planet_id", "commodity", "qty", "direction"),
    EventKind.BUILD_CITADEL: ("planet_id", "level_target", "completes_day", "cost_cr", "cost_col"),
    EventKind.CITADEL_COMPLETE: ("planet_id", "from", "to"),
    EventKind.PLANET_TAX_PAYOUT: ("planet_id", "planet_name", "payout"),
    EventKind.BUY_SHIP: ("ship_class", "net_cost"),
    EventKind.BUY_EQUIP: ("item", "qty", "total"),
    EventKind.CORP_CREATE: ("ticker", "name"),
    EventKind.CORP_INVITE: ("ticker", "target"),
    EventKind.CORP_JOIN: ("ticker",),
    EventKind.CORP_LEAVE: ("ticker",),
    EventKind.CORP_DEPOSIT: ("ticker", "amount"),
    EventKind.CORP_WITHDRAW: ("ticker", "amount"),
    EventKind.CORP_MEMO: ("ticker", "message"),
    EventKind.ALLIANCE_PROPOSED: ("alliance_id", "target"),
    EventKind.ALLIANCE_FORMED: ("alliance_id", "members"),
    EventKind.ALLIANCE_BROKEN: ("alliance_id", "breaker"),
    EventKind.HAIL: ("target", "message"),
    EventKind.BROADCAST: ("message",),
    EventKind.AGENT_THOUGHT: ("thought", "auto_wait", "external_idle", "turns_skipped"),
    EventKind.AGENT_ERROR: ("error", "external_timeout"),
    EventKind.FED_RESPONSE: ("reason",),
    EventKind.HUMAN_TURN_START: ("turns_remaining", "deadline_s"),
}


def event_facts(event: Event) -> dict[str, Any]:
    """Whitelisted, JSON-safe subset of the payload for `event.kind`."""
    keys = EVENT_FACTS.get(event.kind)
    if not keys:
        return {}
    payload = event.payload or {}
    out: dict[str, Any] = {}
    for k in keys:
        if k in payload and not (isinstance(k, str) and k.startswith("_")):
            v = payload[k]
            # Enums / other objects -> plain values; keep scalars and small lists.
            if hasattr(v, "value") and not isinstance(v, (str, int, float, bool)):
                v = v.value
            out[k] = v
    return out


def event_view(event: Event) -> dict[str, Any]:
    """The fog-safe presentation view of one event (see EVENT_FACTS)."""
    return {
        "seq": event.seq,
        "day": event.day,
        "tick": event.tick,
        "kind": event.kind.value,
        "actor_id": event.actor_id,
        "actor_kind": getattr(event, "actor_kind", None),
        "sector_id": event.sector_id,
        "summary": event.summary,
        "facts": event_facts(event),
    }


def _event_to_dict(event: Event) -> dict[str, Any]:
    """Event shape inside `Observation.recent_events`.

    Same as `event_view` minus `actor_kind` (LLM seats never needed it) and
    with `facts` omitted when empty to keep the LLM payload tight.
    """
    view = event_view(event)
    view.pop("actor_kind", None)
    if not view["facts"]:
        view.pop("facts")
    return view


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
    # Out-of-band human operator context for autonomous LLM players. This is
    # not an engine action; it steers the next normal LLM decision.
    operator_directive: str = ""
    operator_directive_updated_day: int | None = None
    operator_directive_updated_tick: int | None = None
    operator_dialogue: list[dict[str, Any]] = Field(default_factory=list)
    alive: bool = True
    net_worth: int = 0
    # Planets this player owns (subset view; one entry per planet).
    owned_planets: list[dict[str, Any]] = Field(default_factory=list)

    # Current sector full detail
    sector: dict[str, Any]
    adjacent: list[dict[str, Any]]

    # Port intel database (persistent across turns)
    known_ports: list[dict[str, Any]]

    # Warp graph for every sector the agent has VISITED, SCANNED, or PROBED.
    # Key is the source sector_id (as a string for JSON safety in LLM
    # payloads — Python ints round-trip fine but some model providers
    # normalize dict keys), value is the list of sector_ids that sector's
    # warps go to. This is the single most important piece of navigational
    # memory: without it, a 12-event horizon means an LLM that entered
    # sector 406 three turns ago and learned "warps_out = [475]" cannot
    # remember that fact when planning this turn's move. Result: deadloops.
    # Data only grows; sector warps are static in this engine.
    known_warps: dict[str, list[int]] = Field(default_factory=dict)

    # Last N trades this player executed. Observation carries the last 25
    # (engine stores 50 on the Player). 5 was too short to see haggle
    # patterns on a 300-tick/day match — by trade 6 the earliest haggle
    # failures scroll out and the agent can't tell its "asked +30%" was
    # being rejected 80% of the time.
    trade_log: list[dict[str, Any]] = Field(default_factory=list)

    # Rolling aggregate of trade_log so the agent has one number per thing
    # it should track: total_trades, total_profit (cr), avg_margin (%),
    # haggle_win_rate (%), best_pair / worst_pair (port-class tuples with
    # their realized profit). Keeps the LLM from having to do arithmetic
    # over 25 json rows to answer "is this pair actually earning?"
    trade_summary: dict[str, Any] = Field(default_factory=dict)

    # Grouped recent-failure counter: same (kind, target) pairs that
    # failed >=2 times in the last ~40 events are surfaced here so the
    # LLM can explicitly see "I tried warp 406->712 four times, all
    # blocked — STOP trying." Fixes the Grok 406-475 deadloop class.
    recent_failures: list[dict[str, Any]] = Field(default_factory=list)

    # Other players — corp mates show full state, others show last-known summary
    other_players: list[dict[str, Any]]

    # Match 13 — rivals: every other alive player summarized with public
    # state (net_worth, ship_class, corp_ticker, alive) plus fog-of-war
    # gated location (last_seen_sector/last_seen_day only if we've
    # witnessed them recently). Separate from other_players because the
    # latter's schema is optimized for corp-mate visibility rules;
    # rivals is the symmetric "public leaderboard" view every agent sees.
    rivals: list[dict[str, Any]] = Field(default_factory=list)

    # Match 13 — true orphaned planets currently in the universe: planets
    # that became ownerless because a player was eliminated. Empty neutral
    # map-start planets are intentionally excluded so agents don't mistake
    # them for valuable former-player holdings.
    orphaned_planets: list[dict[str, Any]] = Field(default_factory=list)

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

    # Parity S5 - fog-safe layout for the known-space map. One entry per
    # sector the player KNOWS (visited / scanned / probed, plus the current
    # sector): {id, x, y, port, is_fedspace, last_seen_day}. Coordinates come
    # from the universe layout, but only for these ids - a seat cannot infer
    # where unexplored sectors sit. `port` is the REMEMBERED code from
    # known_ports (or the live one for the current sector), never a live
    # peek at a sector you have not scouted. UI-only presentation data:
    # format_observation does not ship it (LLM seats reason from known_warps).
    known_sectors: list[dict[str, Any]] = Field(default_factory=list)

    # Parity S3 - structured legality. One entry per ActionKind:
    # {kind, legal, reason, turn_cost, detail: precise|coarse, params}.
    # Produced by engine.legality.legal_actions (pure query, same constants
    # as the handlers). The cockpit gates its verb pad from this and ONLY
    # this; LLM seats receive the compact form via format_observation.
    legal_actions: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------


def build_observation(universe: Universe, player_id: str, event_history: int = 40) -> Observation:
    player = universe.players[player_id]
    sector = universe.sectors[player.sector_id]

    # Match 13 — payload-shrink under timeout pressure. If this player has
    # timed out 3+ times in a row the model is demonstrably struggling
    # with context size; we halve the event history, trade log, and known
    # ports list for THIS observation so the next LLM call has less to
    # chew through. Clears automatically on the next non-timeout action
    # (see server/runner.py where recent_timeouts gets reset to 0).
    timeouts_recent = int(getattr(player, "recent_timeouts", 0) or 0)
    trim_payload = timeouts_recent >= 3
    if trim_payload:
        event_history = min(event_history, 20)

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
    # Match 13 — under timeout pressure cap to 15 most-recently-seen ports
    # (lowest age_days). Full list only matters to tactically fresh planning,
    # and the agent is obviously missing the window on "tactical" right now.
    if trim_payload and len(known_ports) > 15:
        known_ports.sort(key=lambda p: int(p.get("age_days", 10**9)))
        known_ports = known_ports[:15]

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

    # Owner-only, so exposing colonist pools / stockpile / origin is fog-safe.
    # Empire play (ferry sizing, citadel tiers) is impossible without them.
    # Growth fields stay on this list only — sector briefs must not publish
    # another owner's runway just because we warped into their sector.
    from .planets import planet_growth_status
    owned_planets: list[dict[str, Any]] = []
    for planet in universe.planets.values():
        if planet.owner_id != player.id:
            continue
        colonists = {c.value: int(n) for c, n in planet.colonists.items()}
        growth = planet_growth_status(
            planet.class_id, planet.colonists, int(planet.stockpile.get(Commodity.ORGANICS, 0)),
        )
        owned_planets.append({
            "id": planet.id,
            "sector_id": planet.sector_id,
            "name": planet.name,
            "class": planet.class_id.value,
            "origin": getattr(planet, "origin", "other") or "other",
            "citadel_level": planet.citadel_level,
            "citadel_target": getattr(planet, "citadel_target", 0),
            "citadel_complete_day": getattr(planet, "citadel_complete_day", None),
            "fighters": planet.fighters,
            "shields": planet.shields,
            # Same shape as sector.planets[] (_planet_brief): per-pool dict + total.
            "colonists": colonists,
            "colonists_total": sum(colonists.values()),
            "stockpile": {c.value: int(n) for c, n in planet.stockpile.items()},
            "production": growth["production"],
            "organics_consumption_per_day": growth["organics_consumption_per_day"],
            "growth_active": growth["growth_active"],
            "organics_days_left": growth["organics_days_left"],
        })

    # Match 13 — true orphaned planets. owner_id is None AND corp_ticker is
    # None AND we have a PLANET_ORPHANED event proving this was a former
    # player's holding. Startup neutral planets also have owner_id=None,
    # but they are empty and auto-claimed by landing; keep them out of the
    # orphan list so agents don't chase them as free citadel prizes.
    orphan_former: dict[int, str] = {}
    for ev in universe.events:
        if ev.kind is EventKind.PLANET_ORPHANED:
            plid = ev.payload.get("planet_id")
            former = ev.payload.get("former_owner")
            if isinstance(plid, int) and isinstance(former, str):
                orphan_former[plid] = former
    orphaned_planets: list[dict[str, Any]] = []
    for planet in universe.planets.values():
        if planet.owner_id is not None or planet.corp_ticker is not None:
            continue
        former_owner = orphan_former.get(planet.id)
        if former_owner is None:
            continue
        orphaned_planets.append({
            "id": planet.id,
            "sector_id": planet.sector_id,
            "name": planet.name,
            "class": planet.class_id.value,
            "citadel_level": planet.citadel_level,
            "fighters": planet.fighters,
            "shields": planet.shields,
            "former_owner_id": former_owner,
        })
    # Rank orphans by citadel level + fighters so the most strategically
    # valuable ones appear first; cap to 5 entries.
    orphaned_planets.sort(
        key=lambda p: (-p["citadel_level"], -p["fighters"])
    )
    orphaned_planets = orphaned_planets[:5]

    # Match 13 — rivals block. Every other alive player summarized with
    # public numbers (net_worth, ship_class, corp_ticker, alive). We also
    # include a last_seen_sector / last_seen_day if our event history
    # contains a WARP / SCAN / PROBE / LAND_PLANET event witnessed by us
    # that reveals the rival's location. This is strict fog-of-war —
    # agents can only see location when they've actually witnessed it,
    # preserving the TW2002 scouting loop while still giving them a
    # leaderboard-level awareness of who they're competing against.
    rivals: list[dict[str, Any]] = []
    last_seen: dict[str, tuple[int, int, int]] = {}  # pid -> (day, tick, sector)
    for ev in universe.events:
        if ev.actor_id is None or ev.actor_id == player_id:
            continue
        if ev.actor_id not in universe.players:
            continue
        # Require a concrete sector_id AND fog-of-war visibility for US
        if ev.sector_id is None:
            continue
        if not _event_visible_to(ev, player_id, universe):
            continue
        last_seen[ev.actor_id] = (ev.day, ev.tick, ev.sector_id)
    for other_id, other in universe.players.items():
        if other_id == player_id:
            continue
        entry: dict[str, Any] = {
            "id": other_id,
            "name": other.name,
            "alive": other.alive,
            "corp_ticker": other.corp_ticker,
            "net_worth": full_net_worth(universe, other) if other.alive else 0,
            "ship_class": other.ship.ship_class.value,
            "deaths": other.deaths,
        }
        seen = last_seen.get(other_id)
        if seen is not None:
            entry["last_seen_day"] = seen[0]
            entry["last_seen_tick"] = seen[1]
            entry["last_seen_sector"] = seen[2]
        rivals.append(entry)

    from .legality import legal_actions as _legal_actions
    from .runner import alignment_label, rank_for
    legal = [la.model_dump() for la in _legal_actions(universe, player_id)]
    known_sectors = _known_sectors(universe, player)
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
        operator_directive=getattr(player, "operator_directive", "") or "",
        operator_directive_updated_day=getattr(player, "operator_directive_updated_day", None),
        operator_directive_updated_tick=getattr(player, "operator_directive_updated_tick", None),
        operator_dialogue=list(getattr(player, "operator_dialogue", []) or []),
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
        known_warps={str(sid): list(warps) for sid, warps in (player.known_warps or {}).items()},
        trade_log=list(getattr(player, "trade_log", []) or [])[-(10 if trim_payload else 25):],
        trade_summary=_summarize_trade_log(getattr(player, "trade_log", []) or []),
        recent_failures=_aggregate_recent_failures(universe, player_id),
        other_players=others,
        rivals=rivals,
        orphaned_planets=orphaned_planets,
        inbox=list(player.inbox[-40:]),
        recent_events=recent_events,
        alliances=alliances,
        corp=corp_summary,
        deaths=player.deaths,
        max_deaths=K.MAX_DEATHS_BEFORE_ELIM,
        limpets_owned=limpets_owned,
        probe_log=probe_log,
        known_sectors=known_sectors,
        legal_actions=legal,
        action_hint=_action_hint(
            sector_info,
            player,
            owned_planets,
            universe,
            orphaned_planets=orphaned_planets,
            rivals=rivals,
        ),
    )
    return obs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _known_sectors(universe: Universe, player) -> list[dict[str, Any]]:
    """Fog-safe map nodes (Parity S5). See Observation.known_sectors."""
    from . import constants as K

    ids: set[int] = set(int(s) for s in (player.known_sectors or set()))
    ids.update(int(s) for s in (player.known_warps or {}))
    ids.add(int(player.sector_id))
    out: list[dict[str, Any]] = []
    for sid in sorted(ids):
        sector = universe.sectors.get(sid)
        if sector is None:
            continue
        remembered = (player.known_ports or {}).get(sid) or {}
        if sid == player.sector_id:
            port_code = sector.port.code if sector.port else None
        else:
            port_code = remembered.get("class")  # remembered code only
        out.append({
            "id": sid,
            "x": round(float(getattr(sector, "x", 0.0) or 0.0), 4),
            "y": round(float(getattr(sector, "y", 0.0) or 0.0), 4),
            "port": port_code,
            "is_fedspace": sid in K.FEDSPACE_SECTORS,
            "last_seen_day": remembered.get("last_seen_day"),
            "warps_known": sid in (player.known_warps or {}),
        })
    return out


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
    # Fighter/shield capacity + headroom — without these the LLM had to
    # mental-map ship_class → max-fighters tables, which Match-5 showed it
    # can't do reliably (GrokFast kept submitting buy_equip fighters 500
    # on a cargotran whose cap was 400; 4 rejected buys in 8 days).
    # Surfacing `fighter_cap` / `fighter_headroom` as first-class fields
    # gives the agent a direct "can I buy N more?" read.
    from .constants import SHIP_SPECS  # local import to avoid cycle

    spec = SHIP_SPECS.get(ship.ship_class.value, {}) or {}
    fighter_cap = int(spec.get("max_fighters", 0) or 0)
    shield_cap = int(spec.get("max_shields", 0) or 0)
    cur_fighters = int(getattr(ship, "fighters", 0) or 0)
    cur_shields = int(getattr(ship, "shields", 0) or 0)
    return {
        "class": ship.ship_class.value,
        "holds": ship.holds,
        "cargo": cargo_qty,
        "cargo_cost_avg": cost_avg,
        "cargo_value_at_cost": cost_total,
        "fighters": cur_fighters,
        "fighter_cap": fighter_cap,
        "fighter_headroom": max(0, fighter_cap - cur_fighters),
        "shields": cur_shields,
        "shield_cap": shield_cap,
        "shield_headroom": max(0, shield_cap - cur_shields),
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
        # Total out-warps from this sector. Same as len(warps_out); surfaced
        # as a first-class field so reasoning models (M4-12) notice it and
        # can distinguish "I have 1 known warp because I only explored one"
        # from "this sector is a genuine 1-warp dead-end pocket". Without
        # this, agents in 2-sector dead-end tunnels broadcast false "trapped"
        # alerts — Match 4 P2 sent 8+ distress hails from a real pocket but
        # also claimed a 999k bounty that confused rivals into wasting turns.
        "warps_count": len(sector.warps),
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
                # Parity S3: report the side the engine will actually accept.
                # Federal (class 0) ports hold stock but neither buy nor sell
                # (can_trade rejects both); the old fallback labelled them
                # "sells_to_player", which lit up trades the engine refused.
                if p.buys(commodity):
                    side, price = "buys_from_player", port_buy_price(p, commodity)
                elif p.sells(commodity):
                    side, price = "sells_to_player", port_sell_price(p, commodity)
                else:
                    side, price = "not_traded", None
                port_info["stock"][commodity.value] = {
                    "current": s.current,
                    "max": s.maximum,
                    "price": price,
                    "side": side,
                }
        info["port"] = port_info
    return info


def _planet_brief(planet) -> dict[str, Any]:
    from . import constants as K

    colonist_totals = {c.value: planet.colonists.get(c, 0) for c in planet.colonists}
    available_colonists = sum(colonist_totals.values())
    # Next-level citadel build requirements — precomputed so LLMs don't
    # have to memorize the (credit, colonist, days) cost tiers. Keeps
    # GrokFast-class "build_citadel fails → agent keeps retrying" loops
    # out of the action feed (Match-5 had 2 rejected L2 attempts in
    # 3 turns because colonists hadn't accumulated yet).
    cur_level = int(planet.citadel_level or 0)
    cur_target = int(getattr(planet, "citadel_target", 0) or 0)
    next_build: dict[str, Any] | None = None
    if cur_level < K.CITADEL_LEVELS and cur_target <= cur_level:
        nl = cur_level + 1
        tier = K.CITADEL_TIER_COST[nl - 1]
        cred_need, col_need, days = tier
        blocker: str | None = None
        if available_colonists < col_need:
            blocker = (
                f"colonists {available_colonists}/{col_need} on planet"
            )
        next_build = {
            "level": nl,
            "credits": cred_need,
            "colonists": col_need,
            "days": days,
            "colonists_have": available_colonists,
            "colonists_short": max(0, col_need - available_colonists),
            "possible": blocker is None,
            "blocker": blocker,
        }
    return {
        "id": planet.id,
        "name": planet.name,
        "class": planet.class_id.value,
        "owner_id": planet.owner_id,
        "corp_ticker": planet.corp_ticker,
        "citadel_level": planet.citadel_level,
        "citadel_target": cur_target,
        "citadel_complete_day": getattr(planet, "citadel_complete_day", None),
        "citadel_next_build": next_build,
        "fighters": planet.fighters,
        "shields": planet.shields,
        "treasury": planet.treasury,
        "stockpile": {c.value: planet.stockpile.get(c, 0) for c in planet.stockpile},
        "colonists": colonist_totals,
        "colonists_total": available_colonists,
    }


_FEDSPACE_CACHE: set[int] | None = None


def _fedspace_set(universe: Universe) -> set[int]:
    from . import constants as K
    return K.FEDSPACE_SECTORS


def _summarize_trade_log(trade_log: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate the full (up to 50-entry) trade ledger into a single row
    the LLM can read in one glance.

    Why: the 25-entry `trade_log` slice still requires the agent to do
    mental arithmetic to answer "am I actually making money on this
    loop?" Providing total_profit, avg_margin, and haggle_win_rate as
    precomputed numbers frees the LLM to focus on strategy rather than
    pretending to be a spreadsheet.

    Fields:
      total_trades       : int — total number of trade events (buys+sells)
      sells              : int — subset that were sells (realized_profit != None)
      total_profit_cr    : int — sum of realized_profit across all sells
      avg_margin_pct     : float — mean of (realized_profit / unit_basis * 100) over sells
      haggle_win_rate_pct: float — % of trades where the note is NOT "haggle countered"
      best_pair          : {commodity, total_profit_cr, n_trades} | None
      worst_pair         : {commodity, total_profit_cr, n_trades} | None
    """
    if not trade_log:
        return {
            "total_trades": 0,
            "sells": 0,
            "total_profit_cr": 0,
            "avg_margin_pct": 0.0,
            "haggle_win_rate_pct": 0.0,
            "best_pair": None,
            "worst_pair": None,
        }

    total = len(trade_log)
    sells = [t for t in trade_log if t.get("side") == "sell" and t.get("realized_profit") is not None]
    total_profit = sum(int(t.get("realized_profit") or 0) for t in sells)

    # Margin % per sell — realized_profit / (unit * qty - realized_profit)
    # is the cost-basis total; (realized_profit / cost_basis) is the margin.
    # Skip entries with zero cost_basis (shouldn't happen for a real sell).
    margins: list[float] = []
    for t in sells:
        unit = int(t.get("unit") or 0)
        qty = int(t.get("qty") or 0)
        gross = unit * qty
        profit = int(t.get("realized_profit") or 0)
        cost_basis = gross - profit
        if cost_basis > 0:
            margins.append(100.0 * profit / cost_basis)
    avg_margin = sum(margins) / len(margins) if margins else 0.0

    # Haggle win rate — note is "haggle countered" when the port rejected
    # our ask and settled at list. Any other note (or empty) means the
    # haggle either wasn't attempted or was accepted.
    haggle_losses = sum(
        1 for t in trade_log
        if "haggle countered" in str(t.get("note") or "").lower()
    )
    haggle_rate = 100.0 * (total - haggle_losses) / total if total else 0.0

    # Best / worst pair by commodity (crude but actionable).
    by_commodity: dict[str, dict[str, int]] = {}
    for t in sells:
        c = str(t.get("commodity") or "?")
        row = by_commodity.setdefault(c, {"total_profit_cr": 0, "n_trades": 0})
        row["total_profit_cr"] += int(t.get("realized_profit") or 0)
        row["n_trades"] += 1
    best_pair: dict[str, Any] | None = None
    worst_pair: dict[str, Any] | None = None
    if by_commodity:
        best_key = max(by_commodity, key=lambda k: by_commodity[k]["total_profit_cr"])
        worst_key = min(by_commodity, key=lambda k: by_commodity[k]["total_profit_cr"])
        best_pair = {"commodity": best_key, **by_commodity[best_key]}
        worst_pair = {"commodity": worst_key, **by_commodity[worst_key]}

    return {
        "total_trades": total,
        "sells": len(sells),
        "total_profit_cr": total_profit,
        "avg_margin_pct": round(avg_margin, 1),
        "haggle_win_rate_pct": round(haggle_rate, 1),
        "best_pair": best_pair,
        "worst_pair": worst_pair,
    }


def _aggregate_recent_failures(
    universe: Universe, player_id: str, lookback: int = 40
) -> list[dict[str, Any]]:
    """Group the player's recent failure events by (kind, target) and
    surface any group seen >= 2 times.

    This is the direct fix for the "Grok tried warp 406->712 four times
    in a row" pathology. The _recent_self_error helper already surfaces
    the MOST RECENT failure in the action_hint, but that doesn't help
    an agent that's been failing the SAME action repeatedly — it just
    keeps seeing the same error text and keeps retrying.

    Target extraction:
      - warp_blocked / autopilot  -> payload.target  (target sector_id)
      - trade_failed              -> payload.commodity + payload.side
      - agent_error               -> payload.kind    (attempted verb)
    """
    try:
        from .models import EventKind as E
    except Exception:
        return []

    fail_kinds: set = {E.WARP_BLOCKED, E.TRADE_FAILED, E.AGENT_ERROR}

    events = getattr(universe, "events", None) or []
    buckets: dict[tuple, dict[str, Any]] = {}
    # Walk backwards over the tail; only count events where this player
    # is the actor, and give up once we've considered `lookback` events.
    considered = 0
    for ev in reversed(events):
        if considered >= lookback:
            break
        considered += 1
        if ev.actor_id != player_id:
            continue
        if ev.kind not in fail_kinds:
            continue
        payload = ev.payload or {}
        if ev.kind == E.WARP_BLOCKED:
            key = ("warp_blocked", payload.get("target"))
            label = f"warp → {payload.get('target')}"
        elif ev.kind == E.TRADE_FAILED:
            key = ("trade_failed", payload.get("commodity"), payload.get("side"))
            label = f"trade {payload.get('side')} {payload.get('commodity')}"
        else:  # AGENT_ERROR
            # The scheduler stores the rejected action under payload["action"];
            # older emitters used payload["kind"]. Without this every rejection
            # collapsed into one "unknown rejected" bucket.
            verb = payload.get("kind") or (payload.get("action") or {}).get("kind")
            key = ("agent_error", verb)
            label = f"{verb or 'unknown'} rejected"

        row = buckets.setdefault(key, {
            "kind": ev.kind.value,
            "target_label": label,
            "count": 0,
            "last_summary": ev.summary or "",
            "last_day": ev.day,
            "last_tick": ev.tick,
        })
        row["count"] += 1

    # Only surface groups with >=2 hits, sorted descending by count.
    out = [row for row in buckets.values() if row["count"] >= 2]
    out.sort(key=lambda r: (-r["count"], -r["last_tick"]))
    return out


def _action_hint(
    sector_info: dict[str, Any],
    player: Any = None,
    owned_planets: list[dict[str, Any]] | None = None,
    universe: Any = None,
    orphaned_planets: list[dict[str, Any]] | None = None,
    rivals: list[dict[str, Any]] | None = None,
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
    full_hints = not is_minimal()

    # Operator directives outrank routine strategic drift but do not override
    # the legal action system or common-sense survival constraints.
    directive = str(getattr(player, "operator_directive", "") or "").strip() if player is not None else ""
    if directive:
        short = directive if len(directive) <= 260 else directive[:257].rstrip() + "..."
        hints.append(
            "OPERATOR DIRECTIVE ACTIVE — treat this as your most important "
            f"strategic consideration unless illegal, suicidal, or impossible: {short}"
        )

    # Phase D.2 — post-timeout discontinuity hint. If the previous turn was
    # a WAIT synthesized from an LLM timeout, the tick was wasted and the
    # agent's chain-of-thought context was truncated. Tell it loudly so it
    # re-anchors on its scratchpad plan instead of silently drifting.
    # Comes FIRST so it's unmissable.
    if player is not None and getattr(player, "last_action_was_timeout", False):
        hints.append(
            "PREVIOUS TURN LOST TO LLM TIMEOUT — your last tick was a forced "
            "WAIT; no decision was actually made. Re-read your `scratchpad` "
            "and `goal_*` fields before acting so a multi-step plan isn't "
            "silently abandoned."
        )

    # Match 13 — POST-DEATH re-arm hint. Fires on the FIRST observation
    # after a SHIP_DESTROYED, and persists until ship fighters >= 500 AND
    # shields >= 1. Purpose: Match 12's "no_survivors" wipeout happened
    # because agents kept warping back into deep space with <100 fighters
    # after each death. We surface the concrete "you had X fighters when
    # you died" number so they can't hand-wave the under-defense problem.
    # Cleared automatically once the re-arm threshold is met (see below).
    if player is not None:
        ship_now = getattr(player, "ship", None)
        ship_fighters_now = int(getattr(ship_now, "fighters", 0) or 0) if ship_now is not None else 0
        ship_shields_now = int(getattr(ship_now, "shields", 0) or 0) if ship_now is not None else 0
        last_death_day = getattr(player, "last_death_day", None)
        if last_death_day is not None:
            last_sector = getattr(player, "last_death_sector", None)
            last_killer = str(getattr(player, "last_death_killer_id", "") or "")
            last_reason = str(getattr(player, "last_death_reason", "") or "attack")
            death_events: list[Any] = []
            if universe is not None:
                death_events = [
                    ev for ev in (getattr(universe, "events", []) or [])
                    if ev.kind is EventKind.SHIP_DESTROYED
                    and ev.payload.get("victim") == getattr(player, "id", None)
                ]
            same_sector = sum(
                1 for ev in death_events
                if last_sector is not None and ev.payload.get("death_sector") == last_sector
            )
            same_killer = sum(
                1 for ev in death_events
                if last_killer and ev.payload.get("killer_id") == last_killer
            )
            deaths_remaining = max(0, int(K.MAX_DEATHS_BEFORE_ELIM) - int(getattr(player, "deaths", 0) or 0))
            if full_hints and last_sector is not None:
                severity = "REPEATED ROUTE DEATH" if same_sector >= 2 or same_killer >= 2 else "ROUTE RISK"
                if deaths_remaining <= 1:
                    severity = "LAST-LIFE RISK"
                repeat_bits: list[str] = []
                if same_sector >= 2:
                    repeat_bits.append(f"{same_sector} deaths in sector {last_sector}")
                if same_killer >= 2:
                    repeat_bits.append(f"{same_killer} deaths to {last_killer}")
                repeat_line = f" ({'; '.join(repeat_bits)})" if repeat_bits else ""
                attacker_line = f" by {last_killer}" if last_killer else ""
                hints.append(
                    f"{severity} — last ship loss was {last_reason}{attacker_line} "
                    f"in sector {last_sector}{repeat_line}. Treat that sector/route "
                    "as hot until avoided, scouted, re-armed for, or cleared. "
                    "Options include reroute, safer local trade, probe/scan, "
                    "buy fighters/shields or a combat hull, hunt the threat if "
                    "you can outgun it, or knowingly accept the risk."
                )
            # Still under-armed? Keep the hint loud.
            if ship_fighters_now < 500 or ship_shields_now < 1:
                if full_hints:
                    last_fighters = int(getattr(player, "last_death_fighters", 0) or 0)
                    credits_now = int(getattr(player, "credits", 0) or 0)
                    target_fighters = 500
                    fighter_cost_total = target_fighters * K.FIGHTER_COST
                    afford_line = (
                        f"you have {credits_now:,}cr — {target_fighters} fighters = "
                        f"{fighter_cost_total:,}cr at StarDock"
                    )
                    hints.append(
                        f"YOU JUST DIED to {last_reason} on day {last_death_day} "
                        f"(ship had {last_fighters} fighters). Before warping outside "
                        f"FedSpace again, consider buying at least {target_fighters} "
                        f"fighters and >=1 shield at StarDock (sec "
                        f"{K.STARDOCK_SECTOR}). {afford_line}. This hint auto-"
                        f"clears once you're back above that threshold."
                    )
            else:
                # Re-armed: clear the persistent flag so the hint stops.
                # Safe to mutate player here — build_observation is read-
                # after-write from the engine's POV; subsequent observations
                # just see the cleared value.
                try:
                    player.last_death_day = None
                    player.last_death_sector = None
                    player.last_death_killer_id = ""
                    player.last_death_fighters = 0
                    player.last_death_reason = ""
                except Exception:
                    pass

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
        elif full_hints:
            hints.append(
                "GOALS EMPTY — set `goal_short`/`goal_medium`/`goal_long` in "
                "your JSON output so future you knows the plan."
            )

    # M4-12: Map-coverage / dead-end hint. Without this, reasoning models
    # read `known_warps` (size N) and conclude "the universe has N sectors",
    # broadcast false "I'm trapped" alerts, and stop scanning. The engine
    # always generates a fully-connected universe, but individual sectors
    # can be 1-warp dead-end pockets — we surface both facts.
    if universe is not None and player is not None:
        try:
            known_n = len(getattr(player, "known_warps", {}) or {})
            total_n = len(getattr(universe, "sectors", {}) or {})
        except Exception:
            known_n = 0
            total_n = 0
        if total_n > 0 and known_n > 0 and known_n < max(8, total_n // 50):
            hints.append(
                f"MAP COVERAGE — you have `known_warps` for {known_n} of ~"
                f"{total_n} sectors. The universe is fully connected; "
                f"SCAN from new sectors or spend 5k on a PROBE to grow your "
                f"map before assuming you're trapped."
            )
        # Dead-end pocket detection: current sector has 1 warp AND that
        # destination also has 1 warp back here -> genuine 2-sector pocket.
        warps_out = sector_info.get("warps_out") or []
        if len(warps_out) == 1:
            dest_id = int(warps_out[0])
            try:
                dest = universe.sectors.get(dest_id)
            except Exception:
                dest = None
            if dest is not None:
                dest_warps = list(getattr(dest, "warps", []) or [])
                here_id = sector_info.get("id")
                if len(dest_warps) == 1 and int(dest_warps[0]) == here_id:
                    hints.append(
                        f"DEAD-END POCKET — sectors {here_id} and {dest_id} "
                        "only warp to each other. Only a Citadel L4 "
                        "transwarp drive can exit. Do NOT broadcast a "
                        "rescue bounty — no ship can reach you here."
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

        if full_hints:
            ship = getattr(player, "ship", None) if player is not None else None
            cargo_free = int(getattr(ship, "cargo_free", 0) or 0) if ship is not None else 0
            credits = int(getattr(player, "credits", 0) or 0) if player is not None else 0
            cargo = getattr(ship, "cargo", None) if ship is not None else None
            stock_map = port.get("stock") or {}
            buy_opts: list[str] = []
            sell_opts: list[str] = []
            for commodity_name, stock_entry in stock_map.items():
                if not isinstance(stock_entry, dict):
                    continue
                price = int(stock_entry.get("price", 0) or 0)
                current = int(stock_entry.get("current", 0) or 0)
                maximum = int(stock_entry.get("max", 0) or 0)
                if price <= 0:
                    continue
                if stock_entry.get("side") == "sells_to_player":
                    qty = min(cargo_free, credits // price, current)
                    if qty > 0:
                        buy_opts.append(
                            f"buy {qty} {commodity_name} @ {price}cr "
                            f"(max=min(free {cargo_free}, credits//price {credits // price}, stock {current}))"
                        )
                elif stock_entry.get("side") == "buys_from_player" and cargo:
                    have = 0
                    for key, qty_have in cargo.items():
                        if getattr(key, "value", str(key)) == commodity_name:
                            have = int(qty_have or 0)
                            break
                    capacity = max(0, maximum - current)
                    qty = min(have, capacity)
                    if qty > 0:
                        sell_opts.append(
                            f"sell {qty} {commodity_name} @ {price}cr "
                            f"(max=min(cargo {have}, port_capacity {capacity}))"
                        )
            if buy_opts or sell_opts:
                opts = buy_opts[:2] + sell_opts[:2]
                hints.append("TRADE PRECHECK — " + " | ".join(opts))

            # Cargo P&L vs. this port (strategy — omitted in minimal agency mode).
            cargo_cost = getattr(ship, "cargo_cost", None) if ship is not None else None
            if cargo and cargo_cost:
                buys_set = set(port.get("buys") or [])
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
            "genesis/photon_missiles/ether_probes/colonists), corp_create legal here."
        ]
        if full_hints:
            ship_sd = getattr(player, "ship", None) if player is not None else None
            if ship_sd is not None:
                free = getattr(ship_sd, "cargo_free", None)
                if isinstance(free, int) and free > 0:
                    bits.append(
                        f"Cargo free={free} — `buy_equip item=colonists qty={free}` loads Terra colonists at 10 cr each."
                    )
                credits_now = int(getattr(player, "credits", 0) or 0)
                spec = K.SHIP_SPECS.get(getattr(getattr(ship_sd, "ship_class", None), "value", ""), {}) or {}
                fighter_cap = int(spec.get("max_fighters", 0) or 0)
                shield_cap = int(spec.get("max_shields", 0) or 0)
                fighter_headroom = max(0, fighter_cap - int(getattr(ship_sd, "fighters", 0) or 0))
                shield_headroom = max(0, shield_cap - int(getattr(ship_sd, "shields", 0) or 0))
                max_fighters = min(fighter_headroom, credits_now // K.FIGHTER_COST)
                max_shields = min(shield_headroom, credits_now // 10)
                max_colonists = min(int(free or 0), credits_now // K.COLONIST_PRICE)
                bits.append(
                    "StarDock max buy_equip now: "
                    f"fighters {max_fighters}, shields {max_shields}, colonists {max_colonists}; "
                    "valid items are fighters, shields, holds, armid_mines, limpet_mines, "
                    "atomic_mines, genesis, photon_missiles, ether_probes, colonists."
                )
        hints.append(" ".join(bits))

        # Affordable-ship menu: list the ship classes the player can ACTUALLY
        # afford right now, sorted by hold count. V7 showed LLM agents sitting
        # on 50k cash without upgrading because the prompt said "upgrade around
        # 100-150k" and they took it literally. This surfaces the concrete set
        # of legal buy_ship targets and the cargo/fighter trade-offs so the
        # agent can make a grounded decision on day 1-2.
        if full_hints and player is not None:
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

    # Phase D.1 — away-from-StarDock upgrade nudge. If the player is still in
    # the starter merchant_cruiser AND is currently NOT at StarDock AND has
    # more than enough credits to afford a meaningful upgrade, remind them
    # that `buy_ship` is a 0-turn action at sector 1. Without this hint the
    # affordable-ships list only fires when they happen to already be at
    # StarDock — agents who warp out on day 1 to start trading stay in the
    # starter hull for the rest of the match despite sitting on 500k+ cr.
    # Threshold is 1.25x cheapest affordable non-corp ship so we don't nag
    # players who are just barely above the merchant_cruiser cost.
    if (
        full_hints
        and player is not None
        and sector_id is not None
        and sector_id != K.STARDOCK_SECTOR
    ):
        cur_ship = getattr(player, "ship", None)
        cur_class_val = getattr(getattr(cur_ship, "ship_class", None), "value", None)
        if cur_class_val == K.STARTING_SHIP:
            credits = int(getattr(player, "credits", 0) or 0)
            alignment = int(getattr(player, "alignment", 0) or 0)
            in_corp = bool(getattr(player, "corp_ticker", None))
            affordable: list[tuple[int, int, str]] = []
            for class_key, spec in K.SHIP_SPECS.items():
                if class_key == cur_class_val:
                    continue
                cost = int(spec.get("cost", 0))
                if cost <= 0:
                    continue
                if spec.get("corp_only") and not in_corp:
                    continue
                if int(spec.get("min_alignment", -10**9)) > alignment:
                    continue
                if credits < int(cost * 1.25):
                    continue
                holds = int(spec.get("holds", 0))
                disp = spec.get("display_name", class_key)
                affordable.append((holds, cost, f"{disp} ({cost:,}cr, {holds}h)"))
            if affordable:
                affordable.sort(key=lambda t: (-t[0], t[1]))
                picks = ", ".join(tag for _h, _c, tag in affordable[:2])
                hints.append(
                    f"STILL IN STARTER HULL with {credits:,}cr — you can "
                    f"afford {picks}. `buy_ship` is a 0-turn action at "
                    f"StarDock (sector {K.STARDOCK_SECTOR}); warp back to "
                    f"upgrade before burning more days trading in 20 holds."
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
                    next_build = plan.get("citadel_next_build") or {}
                    if isinstance(next_build, dict) and next_build:
                        blocker = next_build.get("blocker")
                        have = next_build.get("colonists_have")
                        need = next_build.get("colonists")
                        short = next_build.get("colonists_short")
                        credits_need = next_build.get("credits")
                        if blocker:
                            hints.append(
                                f"Landed on planet {landed_id} (citadel L{lvl}). "
                                f"L{lvl + 1} precheck: need {need} colonists (have {have}, short {short}) "
                                f"and {credits_need}cr; blocker={blocker}. Use `assign_colonists` or ferry more first."
                            )
                        else:
                            hints.append(
                                f"Landed on planet {landed_id} (citadel L{lvl}). "
                                f"`build_citadel planet_id={landed_id}` is legal for L{lvl + 1} "
                                f"(needs {credits_need}cr and {need} colonists); `liftoff` to leave."
                            )
                    else:
                        hints.append(
                            f"Landed on planet {landed_id} (citadel L{lvl}). `build_citadel planet_id={landed_id}` starts L{lvl + 1}; "
                            f"`assign_colonists` to rebalance; `liftoff` to leave."
                        )

    # Planets in sector (unowned) → local opportunity only. These are
    # usually empty neutral map-start planets, not true former-player
    # orphans. Landing claims neutral planets automatically, but they
    # still need imported colonists before citadel work.
    planets_here = sector_info.get("planets") or []
    if planets_here and not (owned_planets and any(p.get("sector_id") == sector_id for p in owned_planets)):
        hints.append(
            f"{len(planets_here)} neutral/unowned planet(s) here — `land_planet` claims an empty neutral planet. "
            "Bring/ferry colonists before `build_citadel`; do NOT use `claim_planet` unless it is listed in `orphaned_planets`."
        )

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
    if full_hints and player is not None and ship is not None:
        # Match 13 — tiered Ferrengi defense hint. Raiders spawn with
        # 100 + aggression*300 fighters (aggression 1..10), i.e. 400..3,100
        # fighters each. Agents must be AWARE of that number to decide
        # whether their own fighter count is safe. Three tiers:
        #   * in FedSpace              -> optional advice (FYI)
        #   * outside FedSpace, <500   -> LOUD: UNDEFENDED IN DEEP SPACE
        #   * outside FedSpace, <1000  -> FYI: stay sharp, stock up
        # Match 12 wipeout happened with Tanis at 0 fighters, Mira/Eris
        # with only ~20 fighters purchased once. Concrete numbers help.
        ship_fighters = int(getattr(ship, "fighters", 0) or 0)
        ship_shields = int(getattr(ship, "shields", 0) or 0)
        cur_sid = sector_info.get("id")
        in_fedspace = cur_sid in K.FEDSPACE_SECTORS if cur_sid is not None else False
        credits_now = int(getattr(player, "credits", 0) or 0)
        buy_500_cost = 500 * K.FIGHTER_COST
        if not in_fedspace and ship_fighters < 500:
            # Louder text for the most dangerous case.
            hints.append(
                f"UNDEFENDED IN DEEP SPACE — ship has {ship_fighters} fighters "
                f"/ {ship_shields} shields. Ferrengi raiders spawn with "
                f"400-3,100 fighters (aggression 1-10). Any warp from here "
                f"could meet one. StarDock (sec {K.STARDOCK_SECTOR}) sells "
                f"fighters at {K.FIGHTER_COST}cr ea — 500 fighters = "
                f"{buy_500_cost:,}cr, you have {credits_now:,}cr."
            )
        elif not in_fedspace and ship_fighters < 1000:
            hints.append(
                f"FYI: ship has {ship_fighters} fighters in deep space. "
                f"Ferrengi raiders carry 400-3,100 fighters. You'll likely "
                f"win vs. aggression 1-3 raiders but lose to higher. "
                f"StarDock sells fighters at {K.FIGHTER_COST}cr ea."
            )
        elif in_fedspace and ship_fighters == 0 and ship_shields == 0:
            hints.append(
                f"FYI: ship has 0 fighters / 0 shields. StarDock sells "
                f"fighters ({K.FIGHTER_COST}cr ea). Ferrengi raiders (400-"
                f"3,100 fighters) patrol deep space and favor unarmed targets."
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

        # Grouped-failure counter — anything attempted >=2 times and still
        # failing is almost certainly a dead end. Surface the counts so
        # the LLM cannot pretend it hasn't tried yet. This is the
        # specific fix for the Grok 406-475 deadloop class: 4x
        # warp_blocked on same target should STOP retries, not invite
        # attempt #5.
        failures = _aggregate_recent_failures(universe, player.id)
        if failures:
            top = failures[:3]
            parts = [f"{f['target_label']} x{f['count']}" for f in top]
            hints.append(
                "REPEATED FAILURES (stop retrying — try a different target): "
                + ", ".join(parts)
            )

        # Match 13 — precondition-failed-last-turn emphasis. If the most
        # recent self-error was a precondition (e.g. "need 2000 colonists"
        # / "not landed"), engine no longer charges turns for it, but
        # repeating it still costs a thought budget this turn. Surface
        # a gentle reminder to read the concrete state fields.
        err_text = (err or "").lower()
        pre_markers = (
            "need", "must be", "not landed", "not owned", "no such planet",
            "invalid", "insufficient", "exceeds", "only ",
        )
        if err_text and any(m in err_text for m in pre_markers):
            hints.append(
                "Note: precondition failures are FREE (no turn charged in the "
                "engine) — but check `owned_planets[].colonists` / "
                "`ship.cargo` / `credits` BEFORE re-submitting the same "
                "verb. Repeating the same mistake wastes this turn's "
                "thought budget."
            )

    # Match 13 — true orphaned-planet awareness. Only planets made
    # ownerless by an eliminated player reach `orphaned_planets`; empty
    # neutral map-start planets do not.
    if orphaned_planets:
        if full_hints:
            shown = orphaned_planets[:3]
            parts: list[str] = []
            for op in shown:
                label = (
                    f"{op.get('name')} s{op.get('sector_id')} "
                    f"L{op.get('citadel_level', 0)} citadel, "
                    f"{op.get('fighters', 0)} fighters"
                )
                if op.get("former_owner_id"):
                    label += f" (was {op['former_owner_id']})"
                parts.append(label)
            more = (
                ""
                if len(orphaned_planets) <= 3
                else f" (+{len(orphaned_planets) - 3} more)"
            )
            hints.append(
                "ORPHANED PLANETS (claimable): "
                + "; ".join(parts)
                + more
                + ". Warp to the sector, `land_planet`, then `claim_planet` (2 "
                "turns) to inherit citadel + fighters + stockpile. Free of "
                "Genesis cost."
            )
        else:
            hints.append(
                "ORPHANED PLANETS — see `orphaned_planets` in observation; "
                "`land_planet` then `claim_planet` to inherit."
            )

    # Match 13 — rivals gap awareness. If any alive rival is more than 2x
    # your net worth OR you lead the field by >2x, prompt a decision.
    # Strictly informational — lists the 4 interaction verbs available.
    if full_hints and rivals and player is not None:
        my_nw = max(1, int(full_net_worth(universe, player)))
        alive_rivals = [r for r in rivals if r.get("alive") and r.get("net_worth")]
        if alive_rivals:
            top = max(alive_rivals, key=lambda r: int(r.get("net_worth") or 0))
            top_nw = int(top.get("net_worth") or 0)
            # Are we already allied / corp-mates with them?
            my_corp = getattr(player, "corp_ticker", None)
            their_corp = top.get("corp_ticker")
            same_corp = bool(my_corp and my_corp == their_corp)
            if not same_corp:
                if top_nw > my_nw * 2:
                    hints.append(
                        f"TRAILING: {top.get('name')} leads at "
                        f"{top_nw:,}cr ({top_nw / my_nw:.1f}x your "
                        f"{my_nw:,}cr). Interaction verbs: "
                        f"`propose_alliance` (non-aggression pact), "
                        f"`corp_create`+`corp_invite` (pooled treasury), "
                        f"`hail` (diplomacy), or direct `attack`/"
                        f"`photon_missile`. Acting on the gap is optional."
                    )
                elif my_nw > top_nw * 2 and len(alive_rivals) >= 1:
                    hints.append(
                        f"YOU LEAD the field at {my_nw:,}cr (next: "
                        f"{top.get('name')} {top_nw:,}cr). Watch for "
                        f"rivals forming alliances against you; a corp "
                        f"or alliance of your own locks in friendly-fire "
                        f"immunity with any partner."
                    )

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
