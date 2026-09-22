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
    # Argument envelope. Usually {arg_name: {type, required, choices|min|max|max_by|...}};
    # a few informational entries are scalars/None (e.g. deploy_genesis.hops_from_stardock).
    params: dict[str, Any] = Field(default_factory=dict)


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
        detail: str = "precise", params: dict[str, Any] | None = None) -> LegalAction:
    return LegalAction(kind=kind.value, legal=legal, reason=None if legal else reason,
                       turn_cost=cost, detail=detail, params=params or {})


def legal_actions(universe: Universe, player_id: str) -> list[LegalAction]:
    player = universe.players[player_id]
    sector = universe.sectors[player.sector_id]
    out: list[LegalAction] = []

    if not player.alive:
        return [_la(k, legal=False, reason="player is destroyed", detail="precise") for k in ActionKind]

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

    # Lazy imports: these helpers live in runner/combat/ferrengi which import
    # observation, which imports this module lazily. Keep the cycle out of
    # module import time.
    from .combat import _are_allied
    from .ferrengi import _ferrengi_by_name  # noqa: F401  (documented target resolver)
    from .runner import _bfs_path, _planet_was_orphaned

    # ---- comms (precise) ------------------------------------------------------
    # hail: engine only requires a known player id (alive or not); we list alive first.
    others_all = [pid for pid in universe.players if pid != player_id]
    hail_targets = sorted(others_all, key=lambda pid: (not universe.players[pid].alive, pid))
    out.append(_la(ActionKind.HAIL, legal=bool(hail_targets), reason="no other commanders in this match", cost=0,
                   params={"target": {"type": "str", "required": True, "choices": hail_targets},
                           "message": {"type": "str", "required": True}}))
    out.append(_la(ActionKind.BROADCAST, legal=True, cost=0, params={"message": {"type": "str", "required": True}}))

    # ---- S4 group 1: combat / presence ---------------------------------------
    atk_cost = int(K.TURN_COST["attack"])
    hostile_players = [pid for pid in other_ids if not _are_allied(universe, player_id, pid)]
    attack_targets = hostile_players + ferrengi_ids
    if not attack_targets:
        reason = "no target in this sector" if not targets_here else "everyone here is a corp mate or ally"
    elif in_fedspace:
        # The engine rejects AND docks 200 alignment - worth a loud reason.
        reason = "FedSpace - combat forbidden (attempting costs 200 alignment)"
    else:
        reason = _need_turns(player, atk_cost)
    out.append(_la(ActionKind.ATTACK, legal=reason is None, reason=reason, cost=atk_cost,
                   params={"target": {"type": "str", "required": True, "choices": attack_targets,
                                      "players": hostile_players, "ferrengi": ferrengi_ids}}))

    photons = int(getattr(player.ship, "photon_missiles", 0) or 0)
    if photons <= 0:
        reason = "no photon missiles loaded (buy_equip photon_missiles at StarDock)"
    elif not hostile_players:
        reason = "needs a rival commander in this sector (not a corp mate or ally)"
    elif in_fedspace:
        reason = "FedSpace forbids weapons fire (attempting costs 100 alignment)"
    else:
        reason = _need_turns(player, atk_cost)
    out.append(_la(ActionKind.PHOTON_MISSILE, legal=reason is None, reason=reason, cost=atk_cost,
                   params={"target": {"type": "str", "required": True, "choices": hostile_players}}))

    df_cost = int(K.TURN_COST["deploy_fighters"])
    fighters = int(player.ship.fighters or 0)
    if fighters <= 0:
        reason = "no fighters aboard"
    elif in_fedspace:
        reason = "cannot deploy fighters in FedSpace"
    else:
        reason = _need_turns(player, df_cost)
    out.append(_la(ActionKind.DEPLOY_FIGHTERS, legal=reason is None, reason=reason, cost=df_cost,
                   params={"qty": {"type": "int", "required": True, "min": 1, "max": fighters},
                           "mode": {"type": "str", "required": True, "choices": ["defensive", "offensive", "toll"]},
                           "existing_here": ({"owner_id": sector.fighters.owner_id, "count": sector.fighters.count}
                                             if sector.fighters else None)}))

    dm_cost = int(K.TURN_COST["deploy_mines"])
    mines_have = {k.value if hasattr(k, "value") else str(k): int(v) for k, v in (player.ship.mines or {}).items() if int(v) > 0}
    if not mines_have:
        reason = "no mines aboard (buy_equip armid_mines / limpet_mines / atomic_mines)"
    elif in_fedspace:
        reason = "cannot deploy mines in FedSpace"
    else:
        reason = _need_turns(player, dm_cost)
    out.append(_la(ActionKind.DEPLOY_MINES, legal=reason is None, reason=reason, cost=dm_cost,
                   params={"kind": {"type": "str", "required": True, "choices": sorted(mines_have)},
                           "qty": {"type": "int", "required": True, "min": 1, "max_by": mines_have}}))
    # deploy_atomic has no handler in the engine dispatch table; atomics detonate via deploy_mines kind=atomic.
    out.append(_la(ActionKind.DEPLOY_ATOMIC, legal=False,
                   reason="not a dispatched verb - use deploy_mines with kind=atomic (detonates immediately)"))

    # ---- S4 group 2: StarDock cluster -----------------------------------------
    my_spec = K.SHIP_SPECS.get(player.ship.ship_class.value, {}) or {}
    if not at_stardock:
        out.append(_la(ActionKind.BUY_SHIP, legal=False, reason="must be at StarDock (sector 1)",
                       params={"ship_class": {"type": "str", "required": True, "choices": []}}))
        out.append(_la(ActionKind.BUY_EQUIP, legal=False, reason="must be at StarDock (sector 1)",
                       params={"item": {"type": "str", "required": True, "choices": []},
                               "qty": {"type": "int", "required": True, "min": 1, "max_by": {}}}))
    else:
        trade_in = int(my_spec.get("cost", 0) * 0.25)
        owned_classes = {p.ship.ship_class.value for p in universe.players.values()}
        ship_choices: list[str] = []
        net_cost_by: dict[str, int] = {}
        blocked_by: dict[str, str] = {}
        for key, spec in K.SHIP_SPECS.items():
            net = int(spec["cost"]) - trade_in
            net_cost_by[key] = net
            if spec.get("corp_only") and player.corp_ticker is None:
                blocked_by[key] = "corporation-only"
            elif int(spec.get("min_alignment", 0)) > player.alignment:
                blocked_by[key] = f"alignment too low (needs {spec.get('min_alignment')})"
            elif spec.get("unique") and key in owned_classes:
                blocked_by[key] = "already owned elsewhere"
            elif player.credits < net:
                blocked_by[key] = f"insufficient credits ({player.credits} < {net})"
            else:
                ship_choices.append(key)
        out.append(_la(ActionKind.BUY_SHIP, legal=bool(ship_choices),
                       reason=None if ship_choices else "no ship you can buy right now (credits / alignment / corp)",
                       params={"ship_class": {"type": "str", "required": True, "choices": ship_choices,
                                              "net_cost_by": net_cost_by, "trade_in": trade_in, "blocked_by": blocked_by}}))

        prices = {
            "fighters": int(K.FIGHTER_COST), "shields": 10, "armid_mines": int(K.ARMID_MINE_COST),
            "limpet_mines": int(K.LIMPET_MINE_COST), "atomic_mines": int(K.ATOMIC_MINE_COST),
            "photon_missiles": int(K.PHOTON_MISSILE_COST), "ether_probes": int(K.ETHER_PROBE_COST),
            "genesis": int(K.GENESIS_TORPEDO_COST), "holds": int(my_spec.get("base_hold_cost", 0) or 0),
            "colonists": int(K.COLONIST_PRICE),
        }
        cap_by = {
            "fighters": max(0, int(my_spec.get("max_fighters", 0)) - int(player.ship.fighters)),
            "shields": max(0, int(my_spec.get("max_shields", 0)) - int(player.ship.shields)),
            "holds": max(0, 150 - int(player.ship.holds)),
            "colonists": max(0, int(player.ship.cargo_free)),
        }
        equip_max: dict[str, int] = {}
        for item, unit in prices.items():
            afford = player.credits // unit if unit > 0 else 0
            mx = min(afford, cap_by[item]) if item in cap_by else afford
            equip_max[item] = max(0, int(mx))
        equip_choices = [i for i, m in equip_max.items() if m >= 1]
        out.append(_la(ActionKind.BUY_EQUIP, legal=bool(equip_choices),
                       reason=None if equip_choices else "cannot afford any equipment (or all capacities full)",
                       params={"item": {"type": "str", "required": True, "choices": equip_choices, "unit_price_by": prices},
                               "qty": {"type": "int", "required": True, "min": 1, "max_by": equip_max}}))

    in_corp = player.corp_ticker is not None and player.corp_ticker in universe.corporations
    corp = universe.corporations.get(player.corp_ticker) if in_corp else None
    if player.corp_ticker is not None:
        reason = "already in a corporation"
    elif not at_stardock:
        reason = "must be at StarDock (sector 1)"
    elif player.credits < K.CORP_FORMATION_COST:
        reason = f"need {K.CORP_FORMATION_COST} cr to incorporate (have {player.credits})"
    else:
        reason = None
    out.append(_la(ActionKind.CORP_CREATE, legal=reason is None, reason=reason,
                   params={"ticker": {"type": "str", "required": True, "max_len": 3, "taken": sorted(universe.corporations)},
                           "name": {"type": "str", "required": False}}))

    # ---- S4 group 3: planets ---------------------------------------------------
    lp_cost = int(K.TURN_COST["land_planet"])
    contested: list[int] = []
    for plid in planets_here:
        pl = universe.planets[plid]
        hostile = pl.owner_id is not None and pl.owner_id != player_id and not (
            pl.corp_ticker and player.corp_ticker and pl.corp_ticker == player.corp_ticker)
        if hostile and pl.fighters > 0:
            contested.append(plid)
    reason = "no planet in this sector" if not planets_here else _need_turns(player, lp_cost)
    out.append(_la(ActionKind.LAND_PLANET, legal=reason is None, reason=reason, cost=lp_cost,
                   params={"planet_id": {"type": "int", "required": True, "choices": planets_here,
                                         "contested": contested}}))

    lo_cost = int(K.TURN_COST["liftoff"])
    reason = "not landed on a planet" if not landed else _need_turns(player, lo_cost)
    out.append(_la(ActionKind.LIFTOFF, legal=reason is None, reason=reason, cost=lo_cost))

    landed_planet = universe.planets.get(player.planet_landed) if landed else None
    owned_landed = landed_planet is not None and landed_planet.sector_id == sector.id and (
        landed_planet.owner_id == player_id
        or (landed_planet.corp_ticker and player.corp_ticker and landed_planet.corp_ticker == player.corp_ticker))
    owned_reason = ("not landed on a planet" if not landed
                    else "landed planet is not owned by you or your corp" if not owned_landed else None)
    xfer_cost = int(K.TURN_COST.get("liftoff", 1))
    pid_param = {"type": "int", "required": True, "choices": [landed_planet.id] if owned_landed else []}
    pool_names = ["fuel_ore", "organics", "equipment", "colonists"]

    # load_planet_cargo: stockpile commodities and colonist pools -> ship.
    load_avail: dict[str, int] = {}
    if owned_landed:
        for c in TRADE_COMMODITIES:
            n = int(landed_planet.stockpile.get(c, 0) or 0)
            if n > 0:
                load_avail[c.value] = n
        col_pools = {c.value: int(n) for c, n in landed_planet.colonists.items() if int(n) > 0}
        if col_pools:
            load_avail["colonists"] = sum(col_pools.values())
    free = int(player.ship.cargo_free)
    if owned_reason:
        reason = owned_reason
    elif not load_avail:
        reason = "planet has nothing to load (empty stockpile and no colonists)"
    elif free <= 0:
        reason = "no free cargo holds"
    else:
        reason = _need_turns(player, xfer_cost)
    out.append(_la(ActionKind.LOAD_PLANET_CARGO, legal=reason is None, reason=reason, cost=xfer_cost,
                   params={"planet_id": pid_param,
                           "commodity": {"type": "str", "required": True, "choices": sorted(load_avail)},
                           "qty": {"type": "int", "required": True, "min": 1,
                                   "max_by": {c: min(n, free) for c, n in load_avail.items()}},
                           "pool": {"type": "str", "required": False, "choices": pool_names,
                                    "pools": ({c.value: int(n) for c, n in landed_planet.colonists.items()} if owned_landed else {})}}))

    # dump_planet_cargo: ship cargo (incl. colonists) -> planet.
    cargo_have = {c.value: int(n) for c, n in (player.ship.cargo or {}).items() if int(n) > 0}
    if owned_reason:
        reason = owned_reason
    elif not cargo_have:
        reason = "holds are empty"
    else:
        reason = _need_turns(player, xfer_cost)
    out.append(_la(ActionKind.DUMP_PLANET_CARGO, legal=reason is None, reason=reason, cost=xfer_cost,
                   params={"planet_id": pid_param,
                           "commodity": {"type": "str", "required": True, "choices": sorted(cargo_have)},
                           "qty": {"type": "int", "required": True, "min": 1, "max_by": cargo_have},
                           "pool": {"type": "str", "required": False, "choices": pool_names}}))

    # assign_colonists: move colonists ship <-> pools / pool <-> pool.
    ship_cols = int((player.ship.cargo or {}).get(Commodity.COLONISTS, 0) or 0)
    pools_have = ({c.value: int(n) for c, n in landed_planet.colonists.items() if int(n) > 0} if owned_landed else {})
    from_choices = (["ship"] if ship_cols > 0 else []) + sorted(pools_have)
    if owned_reason:
        reason = owned_reason
    elif not from_choices:
        reason = "no colonists aboard or on the planet"
    else:
        reason = _need_turns(player, xfer_cost)
    out.append(_la(ActionKind.ASSIGN_COLONISTS, legal=reason is None, reason=reason, cost=xfer_cost,
                   params={"planet_id": pid_param,
                           "from": {"type": "str", "required": True, "choices": from_choices},
                           "to": {"type": "str", "required": True, "choices": pool_names + (["ship"] if free > 0 else [])},
                           "qty": {"type": "int", "required": True, "min": 1,
                                   "max_by": {**({"ship": ship_cols} if ship_cols > 0 else {}), **pools_have},
                                   "ship_free": free}}))

    # build_citadel: next tier cost in credits (personal or corp treasury) + colonists on planet.
    citadel_params: dict[str, Any] = {"planet_id": pid_param}
    if owned_reason:
        reason = owned_reason
    elif landed_planet.citadel_target > landed_planet.citadel_level:
        reason = f"citadel L{landed_planet.citadel_target} already under construction (done day {landed_planet.citadel_complete_day})"
    elif landed_planet.citadel_level + 1 > K.CITADEL_LEVELS:
        reason = "citadel already at max level"
    else:
        nl = landed_planet.citadel_level + 1
        cred_cost, col_cost, days = K.CITADEL_TIER_COST[nl - 1]
        treasury = int(corp.treasury) if corp is not None else 0
        avail_col = sum(int(n) for n in landed_planet.colonists.values())
        citadel_params["next"] = {"level": nl, "credits": cred_cost, "colonists": col_cost, "days": days,
                                  "colonists_have": avail_col, "pay_from": "corp" if treasury >= cred_cost else "personal"}
        if treasury < cred_cost and player.credits < cred_cost:
            reason = f"need {cred_cost} cr to start citadel L{nl} (have {player.credits}; corp treasury {treasury})"
        elif avail_col < col_cost:
            reason = f"need {col_cost} colonists on planet (have {avail_col})"
        else:
            reason = None  # turn cost is waived by the engine when short
    out.append(_la(ActionKind.BUILD_CITADEL, legal=reason is None, reason=reason,
                   cost=int(K.TURN_COST.get("land_planet", 3)), params=citadel_params))

    # deploy_genesis
    gen_cost = int(K.GENESIS_DEPLOY_TURN_COST)
    genesis = int(player.ship.genesis or 0)
    hops = len(_bfs_path(universe, K.STARDOCK_SECTOR, sector.id)) if sector.id != K.STARDOCK_SECTOR else 0
    if genesis <= 0:
        reason = "no genesis torpedoes loaded (buy_equip genesis at StarDock)"
    elif in_fedspace:
        reason = "cannot deploy genesis in FedSpace"
    elif 0 < hops < K.GENESIS_MIN_HOPS_FROM_STARDOCK:
        reason = f"too close to StarDock ({hops} hops, need >={K.GENESIS_MIN_HOPS_FROM_STARDOCK}); warp deeper"
    elif landed:
        reason = "must be in space to deploy genesis (liftoff first)"
    else:
        reason = _need_turns(player, gen_cost)
    out.append(_la(ActionKind.DEPLOY_GENESIS, legal=reason is None, reason=reason, cost=gen_cost,
                   params={"hops_from_stardock": hops, "min_hops": int(K.GENESIS_MIN_HOPS_FROM_STARDOCK)}))

    # claim_planet: landed on a former-player orphan.
    cp_cost = int(K.TURN_COST.get("claim_planet", 2))
    if landed_planet is None:
        reason = "must be landed on the orphaned planet first"
    elif landed_planet.owner_id is not None:
        reason = f"planet {landed_planet.name} is already owned by {landed_planet.owner_id}"
    elif landed_planet.corp_ticker is not None:
        reason = f"planet {landed_planet.name} is corp-owned ([{landed_planet.corp_ticker}])"
    elif not _planet_was_orphaned(universe, landed_planet.id):
        reason = f"planet {landed_planet.name} is neutral, not a former-player orphan (land_planet claims it automatically)"
    else:
        reason = _need_turns(player, cp_cost)
    out.append(_la(ActionKind.CLAIM_PLANET, legal=reason is None, reason=reason, cost=cp_cost,
                   params={"planet_id": {"type": "int", "required": False,
                                         "choices": [landed_planet.id] if landed_planet is not None else []}}))

    # ---- S4 group 4: corp / alliance / intel -----------------------------------
    out.append(_la(ActionKind.QUERY_LIMPETS, legal=True, cost=0,
                   params={"active": sum(1 for lt in universe.limpets.values() if lt.owner_id == player_id)}))

    is_ceo = corp is not None and corp.ceo_id == player_id
    invite_targets = ([pid for pid in others_all if pid not in corp.invited_ids and pid not in corp.member_ids]
                      if corp is not None else [])
    if not in_corp:
        reason = "not in a corporation"
    elif not is_ceo:
        reason = "only the CEO may invite"
    elif not invite_targets:
        reason = "everyone is already invited or a member"
    else:
        reason = None
    out.append(_la(ActionKind.CORP_INVITE, legal=reason is None, reason=reason,
                   params={"target": {"type": "str", "required": True, "choices": invite_targets}}))

    joinable = [t for t, c in universe.corporations.items()
                if player_id in c.invited_ids and len(c.member_ids) < universe.config.corp_max_members]
    full_invites = [t for t, c in universe.corporations.items()
                    if player_id in c.invited_ids and len(c.member_ids) >= universe.config.corp_max_members]
    reason = None if joinable else ("that corp is full" if full_invites else "no pending corp invite")
    out.append(_la(ActionKind.CORP_JOIN, legal=reason is None, reason=reason,
                   params={"ticker": {"type": "str", "required": True, "choices": joinable}}))

    out.append(_la(ActionKind.CORP_LEAVE, legal=player.corp_ticker is not None,
                   reason="not in a corp", params={"ticker": player.corp_ticker}))

    reason = "not in a corporation" if not in_corp else ("no credits to deposit" if player.credits <= 0 else None)
    out.append(_la(ActionKind.CORP_DEPOSIT, legal=reason is None, reason=reason,
                   params={"amount": {"type": "int", "required": True, "min": 1, "max": int(player.credits)}}))

    treasury = int(corp.treasury) if corp is not None else 0
    if not in_corp:
        reason = "not in a corporation"
    elif not is_ceo:
        reason = "only the CEO may withdraw"
    elif treasury <= 0:
        reason = "corp treasury is empty"
    else:
        reason = None
    out.append(_la(ActionKind.CORP_WITHDRAW, legal=reason is None, reason=reason,
                   params={"amount": {"type": "int", "required": True, "min": 1, "max": treasury}}))

    out.append(_la(ActionKind.CORP_MEMO, legal=in_corp, reason="not in a corporation",
                   params={"message": {"type": "str", "required": True, "max_len": 1000}}))

    allied_active = {m for a in universe.alliances.values() if a.active and player_id in a.member_ids for m in a.member_ids}
    propose_targets = [pid for pid in others_all if pid not in allied_active]
    reason = None if propose_targets else ("no other commanders in this match" if not others_all else "already allied with everyone")
    out.append(_la(ActionKind.PROPOSE_ALLIANCE, legal=reason is None, reason=reason,
                   params={"target": {"type": "str", "required": True, "choices": propose_targets},
                           "terms": {"type": "str", "required": False}}))

    acceptable = [a.id for a in universe.alliances.values()
                  if player_id in a.member_ids and not a.active and a.proposed_by != player_id]
    out.append(_la(ActionKind.ACCEPT_ALLIANCE, legal=bool(acceptable), reason="no alliance proposal pending for you",
                   params={"alliance_id": {"type": "str", "required": True, "choices": acceptable}}))

    # NB: the engine lets you "break" an inactive (still-proposed) alliance too; mirror it.
    breakable = [a.id for a in universe.alliances.values() if player_id in a.member_ids]
    out.append(_la(ActionKind.BREAK_ALLIANCE, legal=bool(breakable), reason="you are in no alliance",
                   params={"alliance_id": {"type": "str", "required": True, "choices": breakable,
                                           "active": [a.id for a in universe.alliances.values() if a.active and player_id in a.member_ids]}}))

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
