"""legal_actions() - which verbs a player may use right now, as data.

Parity S3 (docs/plans/2026-09-21-bot-human-parity.md, Fable plan F3/D3).

Until now the engine's preconditions lived only *inside* the runner
handlers (``if ...: return ActionResult(ok=False, error=...)``) and reached
players as prose in ``action_hint``. That left the cockpit two bad options:
re-implement the rules in JavaScript (a second engine) or light up buttons
that the engine then rejects. This module is the third option: a **pure,
read-only query** - like ``build_observation`` - that reports, per verb,
whether it is legal *now* and why not, plus the parameter envelope a legal
call must stay inside.

Contract
--------
* No mutation. Same constants as the handlers (``TURN_COST``, ``SHIP_SPECS``,
  StarDock sector, port sides/stock, planet ownership).
* It does **not** replace handler validation: the engine still rejects a bad
  action. It only predicts. The test matrix in ``tests/test_parity_s3.py``
  pins ``legal == apply_action(...).ok`` for the *precise* verbs on fixture
  states so the two cannot drift.
* ``detail`` says how much to trust an entry:
    - ``"precise"`` - every handler precondition is mirrored (S3 verbs:
      warp, plot_course, trade, scan, probe, wait; plus hail, broadcast).
    - ``"coarse"``  - only the context precondition is checked (right
      place / owns the thing). The UI still renders these disabled with the
      reason; S4 promotes them to precise one group at a time.
* ``params`` describes the arguments: ``{"name": {"type", "choices"?, "min"?,
  "max"?, "required"}}``. Choices are the *only* legal values (warp targets,
  commodities this port trades on that side, ...). ``max`` for trade qty is
  the engine's own cap at the **listed** price - a rejected haggle settles at
  list price, so the affordability check uses list.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from . import constants as K
from .actions import ActionKind
from .economy import port_buy_price, port_sell_price
from .models import Commodity, PortClass, Universe

TRADE_COMMODITIES = (Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT)


class LegalAction(BaseModel):
    kind: str
    legal: bool
    reason: str | None = None
    turn_cost: int = 0
    detail: str = "coarse"  # "precise" | "coarse"
    params: dict[str, dict[str, Any]] = Field(default_factory=dict)


def _turns_left(player) -> int:
    return int(player.turns_per_day - player.turns_today)


def _warp_cost(player) -> int:
    spec = K.SHIP_SPECS.get(player.ship.ship_class.value)
    if spec and "turns_per_warp" in spec:
        return int(spec["turns_per_warp"])
    return int(K.TURN_COST["warp"])


def _need_turns(player, cost: int) -> str | None:
    if _turns_left(player) < cost:
        return f"out of turns ({_turns_left(player)} left, needs {cost})"
    return None


def _la(kind: ActionKind, *, legal: bool, reason: str | None = None, cost: int = 0,
        detail: str = "precise", params: dict[str, dict[str, Any]] | None = None) -> LegalAction:
    return LegalAction(kind=kind.value, legal=legal, reason=None if legal else reason,
                       turn_cost=cost, detail=detail, params=params or {})


def legal_actions(universe: Universe, player_id: str) -> list[LegalAction]:
    player = universe.players[player_id]
    sector = universe.sectors[player.sector_id]
    out: list[LegalAction] = []

    if not player.alive:
        return [_la(k, legal=False, reason="player is destroyed", detail="precise") for k in ActionKind]

    turns_left = _turns_left(player)
    landed = player.planet_landed is not None
    at_stardock = player.sector_id == K.STARDOCK_SECTOR
    in_fedspace = player.sector_id in K.FEDSPACE_SECTORS
    port = sector.port
    trading_port = port is not None and port.class_id != PortClass.STARDOCK
    other_ids = [pid for pid in sector.occupant_ids if pid != player_id and pid in universe.players]
    ferrengi_ids = [f.id for f in universe.ferrengi.values() if f.sector_id == sector.id and f.alive]
    targets_here = other_ids + ferrengi_ids
    planets_here = [pl for pl in sector.planet_ids if pl in universe.planets]

    # ---- precise (S3) -------------------------------------------------------

    # wait: costs 1 turn, so it is the one verb that also dies at 0 turns left.
    wcost = int(K.TURN_COST.get("wait", 1))
    reason = _need_turns(player, wcost)
    out.append(_la(ActionKind.WAIT, legal=reason is None, reason=reason, cost=wcost))

    # warp
    wc = _warp_cost(player)
    warps = list(sector.warps)
    # NB: the engine does not gate warp on `planet_landed` (observed in
    # _handle_warp); we mirror the engine, not the rulebook.
    reason = "no warps out of this sector" if not warps else _need_turns(player, wc)
    out.append(_la(ActionKind.WARP, legal=reason is None, reason=reason, cost=wc,
                   params={"target": {"type": "int", "required": True, "choices": warps}}))

    # scan
    sc = int(K.TURN_COST["scan"])
    reason = _need_turns(player, sc)
    out.append(_la(ActionKind.SCAN, legal=reason is None, reason=reason, cost=sc,
                   params={"tier": {"type": "str", "required": False,
                                    "choices": [K.SCAN_TIER_BASIC, K.SCAN_TIER_DENSITY, K.SCAN_TIER_HOLO]}}))

    # plot_course: legal whenever a target is given; route existence is per-target and the
    # engine reports "no route" - we expose the known sectors as suggested choices.
    known = sorted(int(s) for s in (player.known_warps or {}) if int(s) != player.sector_id)
    out.append(_la(ActionKind.PLOT_COURSE, legal=True, reason=None, cost=0,
                   params={"target": {"type": "int", "required": True, "suggested": known},
                           "execute": {"type": "bool", "required": False}}))

    # probe
    probes = int(getattr(player.ship, "ether_probes", 0) or 0)
    reason = None
    if probes <= 0:
        reason = "no ether probes loaded (buy_equip probe at StarDock)"
    else:
        reason = _need_turns(player, sc)
    out.append(_la(ActionKind.PROBE, legal=reason is None, reason=reason, cost=sc,
                   params={"target": {"type": "int", "required": True, "min": 1, "max": len(universe.sectors)}}))

    # trade
    tc = int(K.TURN_COST["trade"])
    if not trading_port:
        out.append(_la(ActionKind.TRADE, legal=False, cost=tc,
                       reason="no trading port in this sector" if port is None else "StarDock has no commodity market"))
    else:
        reason = _need_turns(player, tc)
        buy_choices: list[str] = []
        sell_choices: list[str] = []
        qty_max: dict[str, dict[str, int]] = {}
        listed: dict[str, dict[str, int]] = {}
        for c in TRADE_COMMODITIES:
            st = port.stock.get(c)
            if st is None:
                continue
            if port.sells(c):
                unit = port_sell_price(port, c)
                afford = player.credits // unit if unit > 0 else 0
                mx = max(0, min(st.current, player.ship.cargo_free, afford))
                if mx > 0:
                    buy_choices.append(c.value)
                qty_max.setdefault(c.value, {})["buy"] = mx
                listed.setdefault(c.value, {})["buy"] = unit
            if port.buys(c):
                unit = port_buy_price(port, c)
                have = int(player.ship.cargo.get(c, 0))
                mx = max(0, min(have, st.maximum - st.current))
                if mx > 0:
                    sell_choices.append(c.value)
                qty_max.setdefault(c.value, {})["sell"] = mx
                listed.setdefault(c.value, {})["sell"] = unit
        if reason is None and not buy_choices and not sell_choices:
            reason = "nothing you can buy or sell here right now (cargo, credits, holds or port stock)"
        out.append(_la(ActionKind.TRADE, legal=reason is None, reason=reason, cost=tc, params={
            "side": {"type": "str", "required": True, "choices": ["buy", "sell"]},
            "commodity": {"type": "str", "required": True,
                          "choices": sorted(set(buy_choices) | set(sell_choices)),
                          "buy_choices": buy_choices, "sell_choices": sell_choices},
            "qty": {"type": "int", "required": True, "min": 1, "max_by": qty_max},
            "unit_price": {"type": "int", "required": False, "listed_by": listed},
        }))

    # hail / broadcast: free, always legal; hail needs another living player.
    hail_targets = [pid for pid, p in universe.players.items() if pid != player_id and p.alive]
    out.append(_la(ActionKind.HAIL, legal=bool(hail_targets), reason="no other commanders alive", cost=0,
                   params={"target": {"type": "str", "required": True, "choices": hail_targets},
                           "message": {"type": "str", "required": True}}))
    out.append(_la(ActionKind.BROADCAST, legal=True, cost=0, params={"message": {"type": "str", "required": True}}))

    # ---- coarse (context only; S4 makes these precise) -----------------------
    def coarse(kind: ActionKind, ok: bool, why: str, cost: int = 0, params=None) -> None:
        out.append(_la(kind, legal=ok, reason=why, cost=cost, detail="coarse", params=params))

    coarse(ActionKind.BUY_SHIP, at_stardock and not landed, "must be at StarDock (sector 1)",
           params={"ship_class": {"type": "str", "required": True, "choices": sorted(K.SHIP_SPECS)}})
    coarse(ActionKind.BUY_EQUIP, at_stardock and not landed, "must be at StarDock (sector 1)",
           params={"item": {"type": "str", "required": True}, "qty": {"type": "int", "required": True, "min": 1}})
    coarse(ActionKind.ATTACK, bool(targets_here) and not landed and turns_left >= K.TURN_COST.get("attack", 5),
           "no target in this sector" if not targets_here else ("you are landed" if landed else "out of turns"),
           cost=int(K.TURN_COST.get("attack", 5)), params={"target": {"type": "str", "required": True, "choices": targets_here}})
    coarse(ActionKind.PHOTON_MISSILE, bool(other_ids) and getattr(player.ship, "photon_missiles", 0) > 0,
           "needs a rival in sector and a loaded photon missile",
           params={"target": {"type": "str", "required": True, "choices": other_ids}})
    coarse(ActionKind.DEPLOY_FIGHTERS, (not in_fedspace) and (not landed) and player.ship.fighters > 0,
           "FedSpace forbids deployments" if in_fedspace else "no fighters aboard / landed",
           cost=int(K.TURN_COST.get("deploy_fighters", 1)),
           params={"qty": {"type": "int", "required": True, "min": 1, "max": int(player.ship.fighters)},
                   "mode": {"type": "str", "required": True, "choices": ["defensive", "offensive", "toll"]}})
    mines_total = sum(int(v) for v in (player.ship.mines or {}).values())
    coarse(ActionKind.DEPLOY_MINES, (not in_fedspace) and (not landed) and mines_total > 0,
           "FedSpace forbids deployments" if in_fedspace else "no mines aboard / landed",
           params={"qty": {"type": "int", "required": True, "min": 1},
                   "kind": {"type": "str", "required": True, "choices": ["armid", "limpet", "atomic"]}})
    coarse(ActionKind.DEPLOY_ATOMIC, (not in_fedspace) and int((player.ship.mines or {}).get("atomic", 0) or 0) > 0,
           "needs an atomic mine aboard, outside FedSpace")
    coarse(ActionKind.DEPLOY_GENESIS, (not landed) and (not in_fedspace) and int(player.ship.genesis or 0) > 0,
           "needs a genesis torpedo, in space, outside FedSpace (and >=3 hops from StarDock)",
           cost=int(K.GENESIS_DEPLOY_TURN_COST))
    coarse(ActionKind.LAND_PLANET, bool(planets_here) and not landed, "no planet here" if not planets_here else "already landed",
           cost=int(K.TURN_COST.get("land_planet", 3)), params={"planet_id": {"type": "int", "required": True, "choices": planets_here}})
    coarse(ActionKind.LIFTOFF, landed, "not landed", cost=int(K.TURN_COST.get("liftoff", 1)))
    own_landed = landed and universe.planets.get(player.planet_landed) is not None \
        and universe.planets[player.planet_landed].owner_id == player_id
    landed_planet = universe.planets.get(player.planet_landed) if landed else None
    coarse(ActionKind.CLAIM_PLANET, bool(landed_planet) and landed_planet.owner_id is None,
           "land on an ownerless (orphaned) planet first",
           params={"planet_id": {"type": "int", "required": True, "choices": [player.planet_landed] if landed else []}})
    for k in (ActionKind.ASSIGN_COLONISTS, ActionKind.LOAD_PLANET_CARGO, ActionKind.DUMP_PLANET_CARGO, ActionKind.BUILD_CITADEL):
        coarse(k, bool(own_landed), "must be landed on a planet you own",
               params={"planet_id": {"type": "int", "required": True, "choices": [player.planet_landed] if own_landed else []}})
    coarse(ActionKind.QUERY_LIMPETS, any(lt.owner_id == player_id for lt in universe.limpets.values()), "you own no limpets")
    in_corp = player.corp_ticker is not None
    coarse(ActionKind.CORP_CREATE, at_stardock and not in_corp and player.credits >= K.CORP_FORMATION_COST,
           f"at StarDock, not in a corp, and {K.CORP_FORMATION_COST} cr",
           params={"ticker": {"type": "str", "required": True}, "name": {"type": "str", "required": True}})
    coarse(ActionKind.CORP_INVITE, in_corp, "not in a corp", params={"target": {"type": "str", "required": True, "choices": hail_targets}})
    invited = [t for t, c in universe.corporations.items() if player_id in getattr(c, "invited_ids", [])]
    coarse(ActionKind.CORP_JOIN, (not in_corp) and bool(invited), "no pending corp invite",
           params={"ticker": {"type": "str", "required": True, "choices": invited}})
    coarse(ActionKind.CORP_LEAVE, in_corp, "not in a corp")
    coarse(ActionKind.CORP_DEPOSIT, in_corp and player.credits > 0, "not in a corp / no credits",
           params={"amount": {"type": "int", "required": True, "min": 1, "max": int(player.credits)}})
    coarse(ActionKind.CORP_WITHDRAW, in_corp, "not in a corp", params={"amount": {"type": "int", "required": True, "min": 1}})
    coarse(ActionKind.CORP_MEMO, in_corp, "not in a corp", params={"message": {"type": "str", "required": True}})
    pending_for_me = [a.id for a in universe.alliances.values() if (not a.active) and player_id in a.member_ids and a.proposed_by != player_id]
    active_mine = [a.id for a in universe.alliances.values() if a.active and player_id in a.member_ids]
    coarse(ActionKind.PROPOSE_ALLIANCE, bool(hail_targets), "no other commanders alive",
           params={"target": {"type": "str", "required": True, "choices": hail_targets}, "terms": {"type": "str", "required": False}})
    coarse(ActionKind.ACCEPT_ALLIANCE, bool(pending_for_me), "no alliance proposal pending for you",
           params={"target": {"type": "str", "required": True}})
    coarse(ActionKind.BREAK_ALLIANCE, bool(active_mine), "you are in no alliance",
           params={"target": {"type": "str", "required": True}})

    # Keep engine order stable: follow ActionKind declaration order.
    order = {k.value: i for i, k in enumerate(ActionKind)}
    out.sort(key=lambda la: order.get(la.kind, 999))
    return out


def legal_actions_compact(actions: list[LegalAction]) -> dict[str, Any]:
    """Small form for the LLM user message: legal kinds + short reasons for the rest."""
    return {
        "legal": [a.kind for a in actions if a.legal],
        "blocked": {a.kind: a.reason for a in actions if not a.legal and a.reason},
    }
