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
  the engine's own cap at the **listed** price. A counter past the hidden
  limit does not trade. A no-haggle buy pays the list price, so the
  affordability check uses that price.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from . import constants as K
from .actions import ActionKind
from .combat import _are_allied
from .economy import port_buy_price, port_sell_price, trade_turn_cost
from .models import Commodity, FighterMode, PortClass, Universe

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
    spec = K.hull_spec(player.ship.ship_class.value)
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


def _class_citadel_legal(planet, level: int) -> tuple[str | None, dict[str, Any]]:
    """Stockpile quote. Used only when CITADEL_COST_MODE is class."""
    colonists, fuel, organics, equipment, days = K.citadel_class_cost(planet.class_id.value, level)
    have_fuel = int(planet.stockpile.get(Commodity.FUEL_ORE, 0))
    have_org = int(planet.stockpile.get(Commodity.ORGANICS, 0))
    have_eq = int(planet.stockpile.get(Commodity.EQUIPMENT, 0))
    avail_col = sum(int(n) for n in planet.colonists.values())
    nxt = {
        "level": level,
        "credits": 0,
        "colonists": colonists,
        "fuel_ore": fuel,
        "organics": organics,
        "equipment": equipment,
        "days": days,
        "colonists_have": avail_col,
        "pay_from": "stockpile",
    }
    if have_fuel < fuel:
        return f"need {fuel} fuel_ore on planet (have {have_fuel})", nxt
    if have_org < organics:
        return f"need {organics} organics on planet (have {have_org})", nxt
    if have_eq < equipment:
        return f"need {equipment} equipment on planet (have {have_eq})", nxt
    if avail_col < colonists:
        return f"need {colonists} colonists on planet (have {avail_col})", nxt
    return None, nxt


def planet_destroy_reason(universe: Universe, player, planet) -> str | None:
    """None when a landed attacker may destroy this hostile, empty planet."""
    if player.planet_landed != planet.id:
        return "must be landed on the planet first"
    owner = planet.owner_id
    same_corp = bool(
        planet.corp_ticker and player.corp_ticker and planet.corp_ticker == player.corp_ticker
    )
    allied = owner is not None and _are_allied(universe, player.id, owner)
    if owner is None or owner == player.id or same_corp or allied:
        return "planet is friendly"
    if int(planet.fighters) > 0 or int(planet.shields) > 0:
        return "planet still has defenders"
    if (
        K.hardware_tw2002()
        and sum(int(n) for n in planet.colonists.values()) <= 0
        and int(getattr(player.ship, "atomic_detonators", 0) or 0) <= 0
    ):
        # v15 (Gypsy "Try to Destroy Planet: first you purchase Atomic Detonators").
        return "the colonists are gone - destroying the planet needs an atomic detonator (buy_equip atomic_detonator)"
    return None


def _ownership_param(player) -> dict:
    """CORP_RULES.md cr17: Personal or Corporate, with the default the handler applies when omitted."""
    choices = ["personal", "corporate"] if player.corp_ticker else ["personal"]
    default = "corporate" if player.corp_ticker and K.CORP_DEPLOY_DEFAULT == "corporate" else "personal"
    return {"type": "str", "required": False, "choices": choices, "default": default}


def _ownership_label(dep) -> str:
    if dep.owner_id == K.ROGUE_OWNER_ID:
        return "rogue"
    return "corporate" if getattr(dep, "corp_ticker", None) else "personal"


def _recall_owns(universe: Universe, player, dep) -> bool:
    """The runner's recall test: yours, or (CORP_MODE tw2002) your corp's corporate group; never rogue."""
    if not K.corp_rules_on():
        return dep.owner_id == player.id
    if dep.owner_id == K.ROGUE_OWNER_ID:
        return False
    ticker = getattr(dep, "corp_ticker", None)
    if ticker:
        return player.corp_ticker == ticker
    return dep.owner_id == player.id


def legal_actions(universe: Universe, player_id: str) -> list[LegalAction]:
    player = universe.players[player_id]
    sector = universe.sectors[player.sector_id]
    out: list[LegalAction] = []

    if not player.alive:
        return [_la(k, legal=False, reason="player is destroyed", detail="precise") for k in ActionKind
                if (K.hardware_tw2002() or k != ActionKind.LAUNCH_BEACON)
                and (K.planet_trade_on() or k != ActionKind.PLANET_TRADE)
                and (K.port_upgrade_on() or k not in (ActionKind.PORT_UPGRADE, ActionKind.PORT_BUILD))
                and (K.bank_on() or k not in (ActionKind.BANK_DEPOSIT, ActionKind.BANK_WITHDRAW, ActionKind.BANK_TRANSFER))
                and (K.corp_rules_on() or k not in (ActionKind.CORP_SET_PASSWORD, ActionKind.CORP_DROP,
                                                    ActionKind.CORP_TRANSFER))
                and (K.tavern_on() or k not in (
                    ActionKind.TAVERN_ANNOUNCE, ActionKind.TAVERN_TALK, ActionKind.TAVERN_GRAFFITI,
                    ActionKind.TAVERN_ORDER, ActionKind.GRIMY_ASK, ActionKind.GRIMY_CURSE,
                    ActionKind.UNDERGROUND_ENTER, ActionKind.UNDERGROUND_CONTRACT, ActionKind.UNDERGROUND_CLAIM,
                ))
                and ((K.tavern_on() and K.stardock_extra_on()) or k != ActionKind.TRICRON)
                and (K.stardock_extra_on() or k != ActionKind.CINEPLEX)]

    landed = player.planet_landed is not None
    at_stardock = player.sector_id == K.STARDOCK_SECTOR
    in_fedspace = player.sector_id in K.FEDSPACE_SECTORS
    port = sector.port
    from .port_build import docks_closed
    trading_port = port is not None and port.class_id != PortClass.STARDOCK and not docks_closed(port)
    other_ids = [pid for pid in sector.occupant_ids if pid != player_id and pid in universe.players]
    ferrengi_ids = [f.id for f in universe.ferrengi.values() if f.sector_id == sector.id and f.alive]
    alien_ids: list[str] = []
    if K.alien_on() and not landed:  # ALIEN_TRADERS.md al10: from the ship
        from .victory import fedspace_protects
        for alien in universe.aliens.values():
            if not alien.alive or alien.sector_id != sector.id:
                continue
            if in_fedspace and K.rank_tw2002() and fedspace_protects(alien):
                continue  # al14
            alien_ids.append(alien.id)
        alien_ids.sort()
    targets_here = other_ids + ferrengi_ids + alien_ids
    planets_here = [pl for pl in sector.planet_ids if pl in universe.planets]

    # ---- precise (S3) -------------------------------------------------------

    # wait: costs 1 turn, so it is the one verb that also dies at 0 turns left.
    wcost = int(K.TURN_COST.get("wait", 1))
    reason = _need_turns(player, wcost)
    out.append(_la(ActionKind.WAIT, legal=reason is None, reason=reason, cost=wcost))

    # warp
    wc = _warp_cost(player)
    tow_cost = None
    if K.tow_on():  # SHIP_TOW.md tt6: the tow cost per sector while a tow is engaged
        from .tow import move_cost as tow_move_cost
        from .tow import moving_towee
        if moving_towee(universe, player_id) is not None:
            tow_cost = wc = tow_move_cost(universe, player)
    warps = list(sector.warps)
    # NB: the engine does not gate warp on `planet_landed` (observed in
    # _handle_warp); we mirror the engine, not the rulebook.
    reason = "no warps out of this sector" if not warps else _need_turns(player, wc)
    warp_params: dict[str, Any] = {"target": {"type": "int", "required": True, "choices": warps}}
    if tow_cost is not None:
        warp_params["tow_cost"] = tow_cost
        if reason is not None:
            warp_params["target"]["choices"] = []
    out.append(_la(ActionKind.WARP, legal=reason is None, reason=reason, cost=wc, params=warp_params))

    # scan
    sc = int(K.TURN_COST["scan"])
    if K.info_tw2002():  # SCANNERS_HIDDEN_INFO.md s1-s8: only the fitted scanner's modes
        from .scanners import scan_reason, scan_turns
        tiers = K.scan_tiers(getattr(player.ship, "scanner", None))
        reason = scan_reason(universe, player_id, None)
        by_tier = {t: scan_turns(t) for t in tiers}
        legal_tiers = [t for t in tiers if scan_reason(universe, player_id, t) is None]
        out.append(_la(ActionKind.SCAN, legal=reason is None, reason=reason,
                       cost=by_tier.get(tiers[0], 0) if tiers else 0,
                       params={"tier": {"type": "str", "required": False, "choices": legal_tiers,
                                        "turn_cost_by": by_tier}}))
    else:
        reason = _need_turns(player, sc)
        out.append(_la(ActionKind.SCAN, legal=reason is None, reason=reason, cost=sc,
                       params={"tier": {"type": "str", "required": False,
                                        "choices": [K.SCAN_TIER_BASIC, K.SCAN_TIER_DENSITY, K.SCAN_TIER_HOLO]}}))

    # plot_course: a plan (execute omitted/false) is free and stays legal; route
    # existence is per-target and the engine reports "no route". Execute is a
    # different question: the autopilot's first hop is one warp. If that hop
    # cannot be paid, execute used to return ok with 0 hops and cost nothing
    # (a free loop). `params.execute.legal` mirrors the handler: false unless
    # turns left cover one warp. Preview legality is unchanged.
    known = sorted(int(s) for s in (player.known_warps or {}) if int(s) != player.sector_id)
    hop_block = _need_turns(player, wc)
    execute_ok = hop_block is None
    out.append(_la(ActionKind.PLOT_COURSE, legal=True, reason=None, cost=0,
                   params={"target": {"type": "int", "required": True, "suggested": known},
                           "execute": {"type": "bool", "required": False, "legal": execute_ok,
                                       "reason": None if execute_ok else f"first hop unaffordable: {hop_block}",
                                       "first_hop_turns": wc}}))

    # probe
    probes = int(getattr(player.ship, "ether_probes", 0) or 0)
    reason = None
    if probes <= 0:
        reason = "no ether probes loaded (buy_equip probe at StarDock)"
    else:
        reason = _need_turns(player, sc)
    probe_target: dict[str, Any] = {"type": "int", "required": True, "min": 1, "max": len(universe.sectors)}
    if K.info_tw2002():  # s13: the probe flies a route; the engine reports "no route"
        probe_target["max_hops"] = K.PROBE_MAX_HOPS
    out.append(_la(ActionKind.PROBE, legal=reason is None, reason=reason, cost=sc,
                   params={"target": probe_target}))

    # trade
    tc = trade_turn_cost(player)
    if not trading_port:
        out.append(_la(ActionKind.TRADE, legal=False, cost=tc,
                       reason="no trading port in this sector" if port is None else "StarDock has no commodity market"))
    else:
        reason = _need_turns(player, tc)
        if reason is None and K.rob_tw2002() and getattr(port, "bust_player_id", None) == player_id:
            reason = "you are busted at this port until it clears"
        buy_choices: list[str] = []
        sell_choices: list[str] = []
        qty_max: dict[str, dict[str, int]] = {}
        listed: dict[str, dict[str, int]] = {}
        for c in TRADE_COMMODITIES:
            st = port.stock.get(c)
            if st is None:
                continue
            if port.sells(c):
                unit = port_sell_price(port, c, player.experience)
                afford = player.credits // unit if unit > 0 else 0
                mx = max(0, min(st.current, player.ship.cargo_free, afford))
                if mx > 0:
                    buy_choices.append(c.value)
                qty_max.setdefault(c.value, {})["buy"] = mx
                listed.setdefault(c.value, {})["buy"] = unit
            if port.buys(c):
                unit = port_buy_price(port, c, player.experience)
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


    # rob / steal (ROB_MODE tw2002) — docs/playtests/ports/ROB_STEAL.md
    if K.rob_tw2002():
        from .rob_steal import (
            alignment_allows_crime,
            bust_blocks_player,
            port_allows_crime,
        )
        rc = trade_turn_cost(player)
        ok_port, port_why = port_allows_crime(port)
        rob_reason = None
        steal_reason = None
        if not ok_port:
            rob_reason = steal_reason = port_why
        elif not alignment_allows_crime(player):
            rob_reason = steal_reason = f"alignment must be {K.ROB_MIN_ALIGNMENT} or lower"
        elif port is not None and bust_blocks_player(port, player_id):
            rob_reason = steal_reason = "you are busted at this port until it clears"
        else:
            rob_reason = _need_turns(player, rc)
            steal_reason = rob_reason
        rob_max = 0
        steal_choices: list[str] = []
        steal_qty_max: dict[str, int] = {}
        if ok_port and port is not None and alignment_allows_crime(player) and not bust_blocks_player(port, player_id):
            vault = max(0, int(getattr(port, "credits", 0) or 0))
            if vault <= 0 and rob_reason is None:
                rob_reason = "port has no credits to rob"
            # Legal max is the vault; over-exp-cap requests still go through the handler and bust.
            rob_max = vault
            free = int(player.ship.cargo_free)
            for c in TRADE_COMMODITIES:
                st = port.stock.get(c)
                if st is None or int(st.current) <= 0:
                    continue
                mx = max(0, min(int(st.current), free))
                if mx > 0:
                    steal_choices.append(c.value)
                    steal_qty_max[c.value] = mx
            if not steal_choices and steal_reason is None:
                steal_reason = "nothing to steal here (stock or holds)"
        out.append(_la(ActionKind.ROB, legal=rob_reason is None, reason=rob_reason, cost=rc, params={
            "amount": {"type": "int", "required": True, "min": 1, "max": max(1, rob_max) if rob_reason is None else 1},
        }))
        out.append(_la(ActionKind.STEAL, legal=steal_reason is None, reason=steal_reason, cost=rc, params={
            "commodity": {"type": "str", "required": True, "choices": steal_choices},
            "qty": {"type": "int", "required": True, "min": 1, "max_by": steal_qty_max},
        }))
    # Lazy imports: these helpers live in runner/combat/ferrengi which import
    # observation, which imports this module lazily. Keep the cycle out of
    # module import time.
    from .combat import _are_allied
    from .ferrengi import _ferrengi_by_name  # noqa: F401  (documented target resolver)
    from .runner import _bfs_path, _planet_was_orphaned

    if K.sector_fighter_tw2002():
        from .runner import _toll_blocks
        toll_due: dict[str, int] = {}
        affordable_warps: list[int] = []
        for wid in warps:
            dest = universe.sectors.get(int(wid))
            dep = dest.fighters if dest is not None else None
            bill = 0
            if dep is not None and dep.mode == FighterMode.TOLL:
                from .corp import deploy_friend
                if not deploy_friend(universe, player_id, dep):
                    bill = int(dep.count) * K.SECTOR_TOLL_CREDITS_PER_FIGHTER
                    if bill > 0:
                        toll_due[str(wid)] = bill
            # In tw2002 combat the toll is answered at the challenge, so every warp stays open.
            if bill <= 0 or int(player.credits) >= bill or K.challenge_on():
                affordable_warps.append(int(wid))
        if K.info_tw2002() and K.challenge_on():
            toll_due = {}  # s12: the toll is shown at the challenge, not before you warp in
        for la in out:
            if la.kind == ActionKind.WARP.value:
                la.params["toll_due_by"] = toll_due
                la.params["target"]["choices"] = affordable_warps
                if not affordable_warps and warps:
                    la.legal = False
                    la.reason = "toll fighters demand payment"
                if not la.legal and "tow_cost" in la.params:  # SHIP_TOW.md tt6: no turns for the tow
                    la.params["target"]["choices"] = []
                break

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
    fed_shielded = False
    if in_fedspace and K.rank_tw2002():
        # u1: only a fedsafe trader is shielded in FedSpace.
        from .victory import fedspace_protects
        open_targets = [pid for pid in hostile_players if not fedspace_protects(universe.players[pid])]
        fed_shielded = bool(hostile_players) and not open_targets
        hostile_players = open_targets
    if K.hardware_tw2002():
        hostile_players = [
            pid for pid in hostile_players
            if not getattr(universe.players[pid].ship, "cloaked", False)
        ]
    attack_targets = hostile_players + ferrengi_ids + alien_ids
    # fedspace-police-v1 f7: Federals are legal suicide targets
    if K.fed_tw2002():
        from .fed import federals_in_sector
        fed_ids = [f"fed:{f.name}" for f in federals_in_sector(universe, player.sector_id)]
        attack_targets = attack_targets + fed_ids
        atk_note_fed = "Federal: indestructible - you will be podded" if fed_ids else None
    else:
        fed_ids = []
        atk_note_fed = None
    if fed_shielded and not attack_targets:
        reason = "FedSpace - every trader here is fedsafe (attempting costs 200 alignment)"
    elif not attack_targets:
        reason = "no target in this sector" if not targets_here else "everyone here is a corp mate or ally"
    elif in_fedspace and not K.rank_tw2002():
        # The engine rejects AND docks 200 alignment - worth a loud reason.
        reason = "FedSpace - combat forbidden (attempting costs 200 alignment)"
    else:
        reason = _need_turns(player, atk_cost)
    atk_params: dict[str, Any] = {"target": {"type": "str", "required": True, "choices": attack_targets,
                                             "players": hostile_players, "ferrengi": ferrengi_ids}}
    if K.alien_on():  # ALIEN_TRADERS.md al31: omitted under legacy so the digest stays put
        atk_params["target"]["aliens"] = alien_ids
    if K.fleet_on():
        # SHIP_FLEET.md fl24: unmanned ships go in their own list; `choices` stays exactly as before.
        from .fleet import unmanned_attack_choices
        unmanned = unmanned_attack_choices(universe, player_id)
        atk_params["target"]["unmanned_choices"] = unmanned
        if unmanned and not attack_targets:
            reason = _need_turns(player, atk_cost)
    if K.fed_tw2002():
        atk_params["target"]["federals"] = fed_ids
        if atk_note_fed:
            atk_params["target"]["note"] = atk_note_fed
    if K.combat_tw2002():
        from .combat import attack_cap
        cap = attack_cap(player)
        if reason is None and getattr(player.ship, "photon_disabled_ticks", 0) > 0:
            reason = "your fighters are offline (photon)"
        if reason is None and cap <= 0:
            reason = "no fighters aboard to attack with"
        atk_params["qty"] = {"type": "int", "required": False, "min": 1, "max": cap,
                             "note": "fighters to send; your hull caps one attack"}
    out.append(_la(ActionKind.ATTACK, legal=reason is None, reason=reason, cost=atk_cost, params=atk_params))

    photons = int(getattr(player.ship, "photon_missiles", 0) or 0)
    if K.hardware_tw2002():
        from .hardware import photon_hull_ok
        adj = [int(w) for w in (sector.warps or [])]
        if photons <= 0:
            reason = "no photon missiles loaded (buy_equip photon_missiles at StarDock)"
        elif not photon_hull_ok(player):
            reason = "only Missile Frigate or Imperial StarShip may fire photons"
        elif in_fedspace and not K.rank_tw2002():
            reason = "FedSpace forbids weapons fire (attempting costs 100 alignment)"
        elif not adj:
            reason = "no adjacent sector to photon"
        else:
            reason = _need_turns(player, atk_cost)
        out.append(_la(ActionKind.PHOTON_MISSILE, legal=reason is None, reason=reason, cost=atk_cost,
                       params={"target": {"type": "int", "required": True, "choices": adj,
                                          "note": "adjacent sector id (photon wave)"}}))
    else:
        if photons <= 0:
            reason = "no photon missiles loaded (buy_equip photon_missiles at StarDock)"
        elif fed_shielded and not hostile_players:
            reason = "FedSpace forbids weapons fire at a fedsafe trader (attempting costs 100 alignment)"
        elif not hostile_players:
            reason = "needs a rival commander in this sector (not a corp mate or ally)"
        elif in_fedspace and not K.rank_tw2002():
            reason = "FedSpace forbids weapons fire (attempting costs 100 alignment)"
        else:
            reason = _need_turns(player, atk_cost)
        out.append(_la(ActionKind.PHOTON_MISSILE, legal=reason is None, reason=reason, cost=atk_cost,
                       params={"target": {"type": "str", "required": True, "choices": hostile_players}}))

    df_cost = int(K.TURN_COST["deploy_fighters"])
    fighters = int(player.ship.fighters or 0)
    fighter_max = fighters
    corp_rules = K.corp_rules_on()
    if corp_rules:  # CORP_RULES.md cr17/cr19 (QC 57): the handler's controller test, not owner_id
        from .corp import _controls
        controls_here = sector.fighters is not None and _controls(universe, player_id, sector.fighters)
    else:
        controls_here = sector.fighters is not None and sector.fighters.owner_id == player_id
    if K.sector_fighter_tw2002() and (sector.fighters is None or controls_here):
        cap = K.SECTOR_FIGHTER_CAP_WITH_PLANET if sector.planet_ids else K.SECTOR_FIGHTER_CAP
        have = int(sector.fighters.count) if sector.fighters is not None else 0
        fighter_max = min(fighters, max(0, cap - have))
    if corp_rules and controls_here and not in_fedspace:
        reason = _need_turns(player, df_cost)  # cr19: qty 0 changes mode / ownership without adding
    elif fighters <= 0:
        reason = "no fighters aboard"
    elif in_fedspace:
        reason = "cannot deploy fighters in FedSpace"
    elif fighter_max <= 0:
        reason = "sector fighter cap"
    else:
        reason = _need_turns(player, df_cost)
    df_params = {"qty": {"type": "int", "required": True, "min": 1, "max": fighter_max},
                 "mode": {"type": "str", "required": True, "choices": ["defensive", "offensive", "toll"]},
                 "existing_here": ({"owner_id": sector.fighters.owner_id, "count": sector.fighters.count}
                                   if sector.fighters else None)}
    if corp_rules:
        df_params["ownership"] = _ownership_param(player)
        if controls_here:
            df_params["qty"]["min"] = 0
        if sector.fighters is not None:
            df_params["existing_here"]["ownership"] = _ownership_label(sector.fighters)
    from .class0 import MSL_NOTE as _MSL_NOTE
    from .class0 import class0_tw2002 as _c0
    from .class0 import is_class0_sector as _is_c0
    from .class0 import is_msl_sector as _is_msl
    if _c0() and (_is_msl(universe, player.sector_id) or _is_c0(universe, player.sector_id)):
        if player.sector_id not in K.FEDSPACE_SECTORS:
            df_params["note"] = _MSL_NOTE
    out.append(_la(ActionKind.DEPLOY_FIGHTERS, legal=reason is None, reason=reason, cost=df_cost,
                   params=df_params))

    dm_cost = int(K.TURN_COST["deploy_mines"])
    mines_have = {k.value if hasattr(k, "value") else str(k): int(v) for k, v in (player.ship.mines or {}).items() if int(v) > 0}
    mine_room = None
    if K.sector_fighter_tw2002():
        sitting = sum(int(m.count) for m in sector.mines)
        mine_room = max(0, K.SECTOR_MINE_CAP - sitting)
    mine_max = {}
    for kind_name, have in mines_have.items():
        if kind_name == "atomic" or mine_room is None:
            mine_max[kind_name] = have
        else:
            mine_max[kind_name] = min(have, mine_room)
    if not K.atomic_mines_sold():
        mine_max.pop("atomic", None)  # v19 switch: atomic mines retired
    mine_choices = sorted(k for k, n in mine_max.items() if n > 0)
    if not mines_have:
        reason = "no mines aboard (buy_equip armid_mines / limpet_mines / atomic_mines)"
    elif in_fedspace:
        reason = "cannot deploy mines in FedSpace"
    elif not mine_choices:
        reason = "sector mine cap"
    else:
        reason = _need_turns(player, dm_cost)
    dm_params = {"kind": {"type": "str", "required": True, "choices": mine_choices},
                 "qty": {"type": "int", "required": True, "min": 1, "max_by": mine_max}}
    if K.corp_rules_on():
        dm_params["ownership"] = _ownership_param(player)  # cr17 (QC 57)
    from .class0 import MSL_NOTE as _MSL_NOTE2
    from .class0 import class0_tw2002 as _c0b
    from .class0 import is_class0_sector as _is_c0b
    from .class0 import is_msl_sector as _is_mslb
    if _c0b() and (_is_mslb(universe, player.sector_id) or _is_c0b(universe, player.sector_id)):
        if player.sector_id not in K.FEDSPACE_SECTORS:
            dm_params["note"] = _MSL_NOTE2
    out.append(_la(ActionKind.DEPLOY_MINES, legal=reason is None, reason=reason, cost=dm_cost,
                   params=dm_params))
    if K.hardware_tw2002():
        # v13-v18: deploy_atomic sets an atomic detonator on the planet you are landed on.
        from .hardware import colonists_on, detonator_reason
        lp = universe.planets.get(player.planet_landed) if player.planet_landed is not None else None
        da_reason = detonator_reason(universe, player, lp)
        out.append(_la(ActionKind.DEPLOY_ATOMIC, legal=da_reason is None, reason=da_reason,
                       cost=int(K.TURN_COST["planet_destroy"]),
                       params={"planet_id": {"type": "int", "required": True,
                                             "choices": [lp.id] if lp is not None else []},
                               "detonators_aboard": int(getattr(player.ship, "atomic_detonators", 0) or 0),
                               "colonists_alive": bool(lp is not None and colonists_on(lp) > 0),
                               "note": "colonists still alive disarm it and the blast destroys YOUR ship"}))
    else:
        # deploy_atomic has no handler in the engine dispatch table; atomics detonate via deploy_mines kind=atomic.
        out.append(_la(ActionKind.DEPLOY_ATOMIC, legal=False,
                       reason="not a dispatched verb - use deploy_mines with kind=atomic (detonates immediately)"))

    # ---- S4 group 2: StarDock / Class 0 cluster --------------------------------
    from .class0 import (
        CLASS0_ITEMS,
        class0_buy_ok,
        class0_tw2002,
        shield_unit_price,
        special_port_at,
        terra_legal_params,
    )
    my_spec = K.hull_spec(player.ship.ship_class.value) or {}
    at_special = class0_tw2002() and special_port_at(universe, player.sector_id) is not None
    can_buy, buy_where_err = class0_buy_ok(universe, player_id)
    if not can_buy:
        reason = buy_where_err if class0_tw2002() else "must be at StarDock (sector 1)"
        if not class0_tw2002() and K.FED_OUTPOST_BUY_REASON in buy_where_err:  # t25: name the outpost
            reason = f"{reason}; {K.FED_OUTPOST_BUY_REASON}"
        out.append(_la(ActionKind.BUY_SHIP, legal=False, reason="must be at StarDock (sector 1)",
                       params={"ship_class": {"type": "str", "required": True, "choices": []}}))
        out.append(_la(ActionKind.BUY_EQUIP, legal=False, reason=reason,
                       params={"item": {"type": "str", "required": True, "choices": []},
                               "qty": {"type": "int", "required": True, "min": 1, "max_by": {}}}))
    else:
        # buy_ship only at StarDock
        if not at_stardock:
            out.append(_la(ActionKind.BUY_SHIP, legal=False, reason="must be at StarDock (sector 1)",
                           params={"ship_class": {"type": "str", "required": True, "choices": []}}))
        else:
            from .corpships import exmember_tradein_block
            traded = exmember_tradein_block(player)
            if traded:
                out.append(_la(ActionKind.BUY_SHIP, legal=False, reason=traded,
                               params={"ship_class": {"type": "str", "required": True, "choices": [],
                                                      "net_cost_by": {}, "trade_in": 0, "blocked_by": {}}}))
            else:
                old_key = player.ship.ship_class.value
                trade_in = K.trade_in_credit(old_key)
                owned_classes = {p.ship.ship_class.value for p in universe.players.values()}
                owned_classes.update(p.ship.ship_class.value for p in universe.parked_ships.values())  # fl6
                ship_choices: list[str] = []
                net_cost_by: dict[str, int] = {}
                blocked_by: dict[str, str] = {}
                from .corp import flagship_buy_block
                for key, spec in K.ship_specs().items():
                    net = K.net_hull_cost(old_key, key)
                    net_cost_by[key] = net
                    if spec.get("corp_only") and player.corp_ticker is None:
                        blocked_by[key] = "corporation-only"
                    elif (why := flagship_buy_block(universe, player_id, key)):
                        blocked_by[key] = why
                    elif K.ship_min_alignment(spec, 0) > player.alignment:
                        need = K.ship_min_alignment(spec, 0)
                        blocked_by[key] = f"alignment too low (needs {need})"
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
                if K.fleet_on():  # SHIP_FLEET.md fl4: optional trade_in=false buys a spare (legacy: no param)
                    from .fleet import spare_params
                    out[-1].params["trade_in"] = spare_params(universe, player_id)

        day = int(universe.day)
        prices = {
            "fighters": K.fighter_unit_price(day),
            "shields": shield_unit_price(day) if class0_tw2002() else 10,
            "armid_mines": int(K.ARMID_MINE_COST),
            "limpet_mines": int(K.LIMPET_MINE_COST),
            "atomic_mines": int(K.ATOMIC_MINE_COST),
            "photon_missiles": int(K.PHOTON_MISSILE_COST),
            "ether_probes": int(K.ETHER_PROBE_COST),
            "genesis": int(K.GENESIS_TORPEDO_COST),
            "holds": K.hold_next_price(player.ship.ship_class.value, player.ship.holds, day),
            "colonists": int(K.COLONIST_PRICE),
        }
        if class0_tw2002() and at_stardock:
            prices.pop("colonists", None)
        if at_special:
            prices = {k: prices[k] for k in CLASS0_ITEMS}
            prices["holds"] = K.hold_next_price(player.ship.ship_class.value, player.ship.holds, day)
        if K.hardware_tw2002() and at_stardock:
            prices["cloak"] = int(K.CLOAK_COST)
            prices["mine_disruptor"] = int(K.DISRUPTOR_COST)
            prices.update(K.hardware_v2_prices())
            if not K.atomic_mines_sold():
                prices.pop("atomic_mines", None)
        if K.ship_tw_on() and at_stardock:
            from .ship_transwarp import drive_buyable
            if drive_buyable(player):
                prices["transwarp_drive"] = int(K.SHIP_TW_TYPE1_COST)
                cap_by_tw = 1
            else:
                cap_by_tw = 0
        else:
            cap_by_tw = None
        tow_offer: dict[str, int] = {}
        if K.tow_on() and K.ship_tw_on() and at_stardock:  # SHIP_TOW.md tt16
            from .tow import type2_offer
            tow_offer = type2_offer(player)
            prices.update(tow_offer)
        mines_aboard = sum(int(v) for v in (player.ship.mines or {}).values())
        class_key = player.ship.ship_class.value
        have = {
            "fighters": int(player.ship.fighters),
            "shields": int(player.ship.shields),
            "holds": int(player.ship.holds),
            "genesis": int(player.ship.genesis),
            "photon_missiles": int(player.ship.photon_missiles),
            "armid_mines": mines_aboard,
            "limpet_mines": mines_aboard,
            "atomic_mines": mines_aboard,
            "cloak": int(getattr(player.ship, "cloaks", 0) or 0),
            "mine_disruptor": int(getattr(player.ship, "mine_disruptors", 0) or 0),
        }
        if K.hardware_tw2002():
            from .hardware import v2_have
            have.update(v2_have(player.ship))
        cap_by = {}
        if "colonists" in prices:
            cap_by["colonists"] = max(0, int(player.ship.cargo_free))
        if K.info_tw2002() and at_stardock:  # SCANNERS_HIDDEN_INFO.md s1-s3
            for item, price in K.scanner_offer(class_key, getattr(player.ship, "scanner", None)).items():
                prices[item] = int(price)
                cap_by[item] = 1
        for capped in (
            "fighters", "shields", "holds", "genesis", "photon_missiles",
            "armid_mines", "limpet_mines", "atomic_mines",
            "cloak", "mine_disruptor",
        ):
            if capped not in prices:
                continue
            room = K.equip_room(class_key, capped, have.get(capped, 0))
            if room is not None:
                cap_by[capped] = room
        if K.hardware_tw2002() and at_stardock:
            for capped in K.HARDWARE_V2_ITEMS:
                cap_by[capped] = int(K.equip_room(class_key, capped, have.get(capped, 0)) or 0)
        if cap_by_tw is not None and "transwarp_drive" in prices:
            cap_by["transwarp_drive"] = cap_by_tw
        for item in tow_offer:
            cap_by[item] = 1
        equip_max: dict[str, int] = {}
        for item, unit in prices.items():
            if item == "holds":
                equip_max["holds"] = 0  # placeholder keeps legacy key order; filled below
                continue
            afford = player.credits // unit if unit > 0 else 0
            mx = min(afford, cap_by[item]) if item in cap_by else afford
            equip_max[item] = max(0, int(mx))
        if "holds" in prices:
            equip_max["holds"] = K.holds_affordable(
                player.ship.ship_class.value,
                player.ship.holds,
                player.credits,
                day,
                cap_by.get("holds", 10**9),
            )
        equip_choices = [i for i, m in equip_max.items() if m >= 1]
        if K.hardware_tw2002() and at_stardock:
            from .hardware import photon_hull_ok
            if not photon_hull_ok(player) and "photon_missiles" in equip_choices:
                equip_choices = [i for i in equip_choices if i != "photon_missiles"]
                equip_max["photon_missiles"] = 0
        dock_turns = 0
        if at_special:
            dock_turns = trade_turn_cost(player)
        params = {
            "item": {"type": "str", "required": True, "choices": equip_choices, "unit_price_by": prices},
            "qty": {"type": "int", "required": True, "min": 1, "max_by": equip_max},
        }
        if at_special:
            params["dock_turns"] = dock_turns
        buy_cost = dock_turns if at_special else 0
        if not equip_choices:
            buy_reason = "cannot afford any equipment (or all capacities full)"
        elif buy_cost > 0:
            buy_reason = _need_turns(player, buy_cost)
        else:
            buy_reason = None
        out.append(_la(ActionKind.BUY_EQUIP, legal=buy_reason is None and bool(equip_choices),
                       reason=buy_reason if equip_choices else "cannot afford any equipment (or all capacities full)",
                       params=params, cost=buy_cost))

    # CLASS0_TERRA.md: terra_colonists (sector 1 only under tw2002)
    terra_params = terra_legal_params(universe, player) if class0_tw2002() else None
    if class0_tw2002():
        terra_cost = int(K.TERRA_LOAD_TURNS)
        if terra_params is None:
            reason = "Terra colonists unavailable here"
            if player.sector_id != K.STARDOCK_SECTOR:
                reason = "must be at Terra (sector 1)"
            elif player.planet_landed is not None:
                reason = "must liftoff before loading Terra colonists"
            elif player.fighter_challenge is not None:
                reason = "resolve the fighter challenge first"
            elif universe.terra_colonists is None:
                reason = "Terra unavailable"
            else:
                reason = "no room to take or leave colonists"
            out.append(_la(ActionKind.TERRA_COLONISTS, legal=False, reason=reason,
                           cost=terra_cost,
                           params={"mode": {"type": "str", "required": True, "choices": []},
                                   "qty": {"type": "int", "required": True, "min": 1, "max_by": {}}}))
        else:
            turn_block = _need_turns(player, terra_cost)
            out.append(_la(ActionKind.TERRA_COLONISTS, legal=turn_block is None, reason=turn_block,
                           cost=terra_cost, params=terra_params))

    in_corp = player.corp_ticker is not None and player.corp_ticker in universe.corporations
    corp = universe.corporations.get(player.corp_ticker) if in_corp else None
    if K.corp_rules_on():
        from .corp import append_legal
        append_legal(out, universe, player, player_id, _la)
    elif player.corp_ticker is not None:
        reason = "already in a corporation"
    elif not at_stardock:
        reason = "must be at StarDock (sector 1)"
    elif player.credits < K.CORP_FORMATION_COST:
        reason = f"need {K.CORP_FORMATION_COST} cr to incorporate (have {player.credits})"
    else:
        reason = None
    if not K.corp_rules_on():
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
        if hostile and (pl.fighters > 0 or pl.shields > 0):
            contested.append(plid)
    land_choices = list(planets_here)
    if K.sector_fighter_tw2002():
        from .runner import _toll_blocks
        if _toll_blocks(universe, player_id, sector):
            land_choices = []
            for plid in planets_here:
                pl = universe.planets[plid]
                hostile = pl.owner_id is not None and pl.owner_id != player_id and not (
                    pl.corp_ticker and player.corp_ticker and pl.corp_ticker == player.corp_ticker)
                if not hostile:
                    land_choices.append(plid)
    if not planets_here:
        reason = "no planet in this sector"
    elif not land_choices:
        reason = "toll fighters demand payment"
    else:
        reason = _need_turns(player, lp_cost)
    out.append(_la(ActionKind.LAND_PLANET, legal=reason is None, reason=reason, cost=lp_cost,
                   params={"planet_id": {"type": "int", "required": True, "choices": land_choices,
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
    dump_max = dict(cargo_have)
    if owned_landed and K.planet_limits_on():
        total_col = sum(int(n) for n in landed_planet.colonists.values())
        col_room = K.planet_colonist_room(landed_planet.class_id.value, total_col)
        for name, have in list(dump_max.items()):
            if name == Commodity.COLONISTS.value:
                room = col_room
            else:
                held = int(landed_planet.stockpile.get(Commodity(name), 0))
                room = K.planet_stock_room(landed_planet.class_id.value, name, held)
            if room is not None:
                dump_max[name] = min(have, int(room))
        dump_max = {name: qty for name, qty in dump_max.items() if qty > 0}
    if owned_reason:
        reason = owned_reason
    elif not cargo_have:
        reason = "holds are empty"
    elif not dump_max:
        reason = "planet is at its class cap"
    else:
        reason = _need_turns(player, xfer_cost)
    out.append(_la(ActionKind.DUMP_PLANET_CARGO, legal=reason is None, reason=reason, cost=xfer_cost,
                   params={"planet_id": pid_param,
                           "commodity": {"type": "str", "required": True, "choices": sorted(dump_max)},
                           "qty": {"type": "int", "required": True, "min": 1, "max_by": dump_max},
                           "pool": {"type": "str", "required": False, "choices": pool_names}}))

    # assign_colonists: move colonists ship <-> pools / pool <-> pool.
    ship_cols = int((player.ship.cargo or {}).get(Commodity.COLONISTS, 0) or 0)
    pools_have = ({c.value: int(n) for c, n in landed_planet.colonists.items() if int(n) > 0} if owned_landed else {})
    ship_room = ship_cols
    if owned_landed and ship_cols > 0 and K.planet_limits_on():
        total_col = sum(int(n) for n in landed_planet.colonists.values())
        room = K.planet_colonist_room(landed_planet.class_id.value, total_col)
        if room is not None:
            ship_room = min(ship_cols, int(room))
    from_choices = (["ship"] if ship_room > 0 else []) + sorted(pools_have)
    if owned_reason:
        reason = owned_reason
    elif not from_choices and ship_cols > 0 and ship_room <= 0:
        cap = K.PLANET_MAX_COLONISTS[landed_planet.class_id.value]
        reason = f"planet colonist cap is {cap}"
    elif not from_choices:
        reason = "no colonists aboard or on the planet"
    else:
        reason = _need_turns(player, xfer_cost)
    out.append(_la(ActionKind.ASSIGN_COLONISTS, legal=reason is None, reason=reason, cost=xfer_cost,
                   params={"planet_id": pid_param,
                           "from": {"type": "str", "required": True, "choices": from_choices},
                           "to": {"type": "str", "required": True, "choices": pool_names + (["ship"] if free > 0 else [])},
                           "qty": {"type": "int", "required": True, "min": 1,
                                   "max_by": {**({"ship": ship_room} if ship_room > 0 else {}), **pools_have},
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
        if K.CITADEL_COST_MODE == "class":
            reason, citadel_params["next"] = _class_citadel_legal(landed_planet, nl)
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
        if reason is None and not K.sector_has_planet_room(len(sector.planet_ids)):
            reason = "sector already holds 5 planets"
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

    # ---- HARDWARE_MODE tw2002: cloak / disruptor / limpet removal ----------------
    if K.hardware_tw2002():
        cloaks = int(getattr(player.ship, "cloaks", 0) or 0)
        if cloaks <= 0:
            reason = "no cloaking device aboard (buy_equip cloak at StarDock)"
        elif getattr(player.ship, "cloaked", False):
            reason = "already cloaked"
        else:
            reason = None
        out.append(_la(ActionKind.CLOAK, legal=reason is None, reason=reason, cost=0,
                       params={"cloaks_aboard": cloaks}))

        dis = int(getattr(player.ship, "mine_disruptors", 0) or 0)
        adj = [int(w) for w in (sector.warps or [])]
        if dis <= 0:
            reason = "no mine disruptors aboard"
        elif not adj:
            reason = "no adjacent sector"
        else:
            reason = _need_turns(player, atk_cost)
        out.append(_la(ActionKind.FIRE_DISRUPTOR, legal=reason is None, reason=reason, cost=atk_cost,
                       params={"target": {"type": "int", "required": True, "choices": adj}}))

        attached = sum(1 for lt in universe.limpets.values()
                       if lt.target_id == player_id and lt.target_ship_id is None)
        fee = int(K.LIMPET_REMOVAL_COST)
        from .class0 import class0_service_here as _c0_svc
        if not _c0_svc(universe, player_id):
            reason = "must be at StarDock or a Class 0 port" if K.class0_tw2002() else "must be at StarDock"
        elif attached <= 0:
            reason = "no limpet attached"
        elif player.credits < fee:
            reason = "insufficient credits for limpet removal"
        else:
            reason = None
        out.append(_la(ActionKind.REMOVE_LIMPET, legal=reason is None, reason=reason, cost=0,
                       params={"fee": fee, "attached": attached}))

        # v5-v9: marker beacons
        from .hardware import launch_beacon_reason
        reason = launch_beacon_reason(universe, player_id)
        out.append(_la(ActionKind.LAUNCH_BEACON, legal=reason is None, reason=reason, cost=int(K.BEACON_TURNS),
                       params={"message": {"type": "str", "required": True, "max_len": int(K.BEACON_MESSAGE_MAX)},
                               "beacons_aboard": int(getattr(player.ship, "marker_beacons", 0) or 0),
                               "beacon_here": sector.beacon is not None,
                               "note": "a second beacon in a sector makes both explode"}))
    # legacy: cloak / fire_disruptor / remove_limpet are not offered at all (like rob/steal under ROB_MODE legacy)

    # ---- S4 group 4: corp / alliance / intel -----------------------------------
    out.append(_la(ActionKind.QUERY_LIMPETS, legal=True, cost=0,
                   params={"active": sum(1 for lt in universe.limpets.values() if lt.owner_id == player_id)}))

    is_ceo = corp is not None and corp.ceo_id == player_id
    if K.corp_rules_on():
        is_ceo = False  # tw2002 verbs were added with corp_create; skip the legacy block below
    if not K.corp_rules_on():
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

    # Planet defense stocking. qty is planet fighters, or planet shields.
    # Ship shields move PLANET_SHIELD_SHIP_COST at a time.
    ratio = int(K.PLANET_SHIELD_SHIP_COST)
    fighter_cap = int(my_spec.get("max_fighters", 0) or 0)
    shield_cap = int(my_spec.get("max_shields", 0) or 0)
    ship_fighters = int(player.ship.fighters or 0)
    ship_shields = int(player.ship.shields or 0)
    planet_fighters = int(landed_planet.fighters) if owned_landed else 0
    planet_shields = int(landed_planet.shields) if owned_landed else 0
    level_block = None
    if owned_landed and int(landed_planet.citadel_level or 0) < K.PLANET_DEFENSE_MIN_LEVEL:
        level_block = "planet citadel level is below the defense stocking minimum"
    deposit_max = {
        "fighters": max(0, min(ship_fighters, K.PLANET_FIGHTER_CAP - planet_fighters)),
        "shields": ship_shields // ratio,
    }
    withdraw_max = {
        "fighters": max(0, min(planet_fighters, fighter_cap - ship_fighters)),
        "shields": max(0, min(planet_shields, (shield_cap - ship_shields) // ratio)),
    }

    def _defense_la(kind: ActionKind, maxima: dict[str, int], empty_reason: str) -> None:
        cost = int(K.TURN_COST[kind.value])
        choices = [name for name, n in maxima.items() if n >= 1]
        if owned_reason:
            reason = owned_reason
        elif level_block:
            reason = level_block
        elif not choices:
            reason = empty_reason
        else:
            reason = _need_turns(player, cost)
        out.append(_la(kind, legal=reason is None, reason=reason, cost=cost,
                       params={"planet_id": pid_param,
                               "kind": {"type": "str", "required": True, "choices": choices},
                               "qty": {"type": "int", "required": True, "min": 1,
                                       "max_by": {name: maxima[name] for name in choices}}}))

    _defense_la(ActionKind.DEPOSIT_PLANET_DEFENSE, deposit_max,
                "nothing on the ship to stock (fighters, or 10 shields per planet shield)")
    _defense_la(ActionKind.WITHDRAW_PLANET_DEFENSE, withdraw_max,
                "nothing on the planet to withdraw, or the ship cap is full")

    react_cost = int(K.TURN_COST["set_military_reaction"])
    react_reason = owned_reason or _need_turns(player, react_cost)
    out.append(_la(ActionKind.SET_MILITARY_REACTION, legal=react_reason is None, reason=react_reason,
                   cost=react_cost,
                   params={"planet_id": pid_param,
                           "pct": {"type": "int", "required": True, "min": 0, "max": 100}}))

    level_ok = owned_landed and int(landed_planet.citadel_level or 0) >= 1
    room = max(0, K.PLANET_TREASURY_CAP - int(landed_planet.treasury)) if owned_landed else 0
    deposit_max = min(int(player.credits), room) if level_ok else 0
    withdraw_max = int(landed_planet.treasury) if level_ok else 0

    def _treasury_la(kind: ActionKind, maxima: int, empty_reason: str) -> None:
        cost = int(K.TURN_COST[kind.value])
        if owned_reason:
            reason = owned_reason
        elif owned_landed and int(landed_planet.citadel_level or 0) < 1:
            reason = "treasury requires citadel level 1"
        elif maxima < 1:
            reason = empty_reason
        else:
            reason = _need_turns(player, cost)
        out.append(_la(kind, legal=reason is None, reason=reason, cost=cost,
                       params={"planet_id": pid_param,
                               "amount": {"type": "int", "required": True, "min": 1, "max": max(1, maxima)}}))

    _treasury_la(ActionKind.DEPOSIT_TREASURY, deposit_max, "not enough credits, or the planet treasury is full")
    _treasury_la(ActionKind.WITHDRAW_TREASURY, withdraw_max, "nothing in the planet treasury")

    quasar_cost = int(K.TURN_COST["set_quasar_sector"])
    if owned_reason:
        quasar_reason = owned_reason
    elif owned_landed and int(landed_planet.citadel_level or 0) < K.QUASAR_MIN_LEVEL:
        quasar_reason = "quasar requires citadel level 3"
    else:
        quasar_reason = _need_turns(player, quasar_cost)
    out.append(_la(ActionKind.SET_QUASAR_SECTOR, legal=quasar_reason is None, reason=quasar_reason,
                   cost=quasar_cost,
                   params={"planet_id": pid_param,
                           "pct": {"type": "int", "required": True, "min": 0, "max": 100}}))
    atm_cost = int(K.TURN_COST["set_quasar_atm"])
    if owned_reason:
        atm_reason = owned_reason
    elif owned_landed and int(landed_planet.citadel_level or 0) < K.QUASAR_MIN_LEVEL:
        atm_reason = "quasar requires citadel level 3"
    else:
        atm_reason = _need_turns(player, atm_cost)
    out.append(_la(ActionKind.SET_QUASAR_ATM, legal=atm_reason is None, reason=atm_reason,
                   cost=atm_cost,
                   params={"planet_id": pid_param,
                           "pct": {"type": "int", "required": True, "min": 0, "max": 100}}))

    tw_cost = int(K.TURN_COST["planet_transwarp"])
    if owned_reason:
        tw_reason = owned_reason
    elif owned_landed and int(landed_planet.citadel_level or 0) < K.PLANET_TRANSWARP_MIN_LEVEL:
        tw_reason = "transwarp requires citadel level 4"
    elif owned_landed and landed_planet.last_transwarp_day == universe.day:
        tw_reason = "planet already moved today"
    else:
        tw_reason = _need_turns(player, tw_cost)
    out.append(_la(ActionKind.PLANET_TRANSWARP, legal=tw_reason is None, reason=tw_reason,
                   cost=tw_cost,
                   params={"planet_id": pid_param,
                           "dest_sector": {"type": "int", "required": True}}))

    buy_turns = int(K.TURN_COST["planet_buy_transporter"])
    if owned_reason:
        buy_reason = owned_reason
    elif owned_landed and int(landed_planet.citadel_level or 0) < 1:
        buy_reason = "transporter requires citadel level 1"
    elif owned_landed and landed_planet.has_transporter:
        buy_reason = "transporter already bought"
    elif owned_landed and int(player.credits) < K.PLANET_TRANSPORTER_COST_FIRST:
        buy_reason = "not enough credits"
    else:
        buy_reason = _need_turns(player, buy_turns)
    out.append(_la(ActionKind.PLANET_BUY_TRANSPORTER, legal=buy_reason is None, reason=buy_reason,
                   cost=buy_turns, params={"planet_id": pid_param}))

    hop_turns = int(K.TURN_COST["planet_transport"])
    if owned_reason:
        hop_reason = owned_reason
    elif owned_landed and not landed_planet.has_transporter:
        hop_reason = "planet has no transporter"
    else:
        hop_reason = _need_turns(player, hop_turns)
    out.append(_la(ActionKind.PLANET_TRANSPORT, legal=hop_reason is None, reason=hop_reason,
                   cost=hop_turns,
                   params={"planet_id": pid_param,
                           "dest_sector": {"type": "int", "required": True}}))

    destroy_cost = int(K.TURN_COST["planet_destroy"])
    if not landed or landed_planet is None:
        destroy_reason = "must be landed on the planet first"
    else:
        destroy_reason = planet_destroy_reason(universe, player, landed_planet)
        if destroy_reason is None:
            destroy_reason = _need_turns(player, destroy_cost)
    destroy_choices = [landed_planet.id] if landed_planet is not None else []
    out.append(_la(ActionKind.PLANET_DESTROY, legal=destroy_reason is None, reason=destroy_reason,
                   cost=destroy_cost,
                   params={"planet_id": {"type": "int", "required": True, "choices": destroy_choices}}))

    recall_cost = int(K.TURN_COST["recall_deployed"])
    what_choices: list[str] = []
    max_by: dict[str, int] = {}
    mine_kinds: list[str] = []
    if not K.sector_fighter_tw2002():
        recall_reason = "legacy sector fighters have no recall"
    else:
        dep = sector.fighters
        if dep is not None and _recall_owns(universe, player, dep) and int(dep.count) > 0:
            room = K.equip_room(player.ship.ship_class.value, "fighters", int(player.ship.fighters or 0))
            if room is None:
                room = int(dep.count)
            if room > 0:
                what_choices.append("fighters")
                max_by["fighters"] = min(int(dep.count), room)
        aboard = sum(int(v) for v in (player.ship.mines or {}).values())
        mine_room = K.equip_room(player.ship.ship_class.value, "armid_mines", aboard)
        for mine in sector.mines:
            if not _recall_owns(universe, player, mine) or int(mine.count) <= 0:
                continue
            if mine.kind.value in mine_kinds:
                continue
            if mine.kind.value == "atomic":
                continue
            room = int(mine.count) if mine_room is None else min(int(mine.count), mine_room)
            if room <= 0:
                continue
            mine_kinds.append(mine.kind.value)
            max_by[mine.kind.value] = room
        if mine_kinds:
            what_choices.append("mines")
            max_by["mines"] = max(max_by[k] for k in mine_kinds)
        if not what_choices:
            recall_reason = "nothing of yours to pick up here"
        else:
            recall_reason = _need_turns(player, recall_cost)
    out.append(_la(ActionKind.RECALL_DEPLOYED, legal=recall_reason is None, reason=recall_reason,
                   cost=recall_cost,
                   params={"what": {"type": "str", "required": True, "choices": what_choices},
                           "kind": {"type": "str", "required": False, "choices": sorted(mine_kinds)},
                           "qty": {"type": "int", "required": False, "min": 1, "max_by": max_by}}))

    from .ferrengi import live_ferrengi_encounter
    ferr_enc = live_ferrengi_encounter(universe, player_id)

    surrender_cost = int(K.TURN_COST["surrender"])
    if ferr_enc is not None:
        surrender_reason = _need_turns(player, surrender_cost)
        surrender_params = {"note": "surrender cargo/holds/credits as tribute; ship lives"}
    elif not K.sector_fighter_tw2002():
        surrender_reason = "legacy sector fighters do not take a surrender"
        surrender_params = {}
    else:
        surrender_reason = "surrender waits for the defensive challenge"
        surrender_params = {}
    challenge = None
    if ferr_enc is None and K.sector_fighter_tw2002() and K.combat_tw2002():
        from .combat import live_challenge
        challenge = live_challenge(universe, player_id)
        surrender_reason = "no fighters challenge you here" if challenge is None else _need_turns(player, surrender_cost)
        if challenge is not None and int(player.ship.fighters or 0) > 0:
            surrender_params["warning"] = (f"you still have {int(player.ship.fighters)} fighters; "
                                           "surrender loses the ship (the same as being destroyed)")
    out.append(_la(ActionKind.SURRENDER, legal=surrender_reason is None, reason=surrender_reason,
                   cost=surrender_cost, params=surrender_params))

    # retreat / pay_toll: answers to a fighter challenge (COMBAT_MODE tw2002)
    # or Ferrengi tribute encounter (ferrengi-aliens-v1).
    from .combat import retreat_block
    from .runner import (
        CHALLENGE_REFUSAL,
        CHALLENGE_VERBS,
        FERRENGI_ENCOUNTER_NOTE,
        FERRENGI_ENCOUNTER_VERBS,
        _hostile_toll,
    )
    rc = _warp_cost(player)
    if ferr_enc is not None:
        retreat_reason = _need_turns(player, rc)
        if retreat_reason is None and not sector.warps:
            retreat_reason = "no warp out to flee the Ferrengi"
        pay_reason = "Ferrengi take tribute, not a toll"
        retreat_params = {"note": "flee any neighbour"}
        pay_params = {}
    elif not K.challenge_on():
        retreat_reason = pay_reason = "needs tw2002 combat"
        retreat_params = {}
        pay_params = {}
    elif challenge is None:
        retreat_reason = pay_reason = "no fighters challenge you here"
        retreat_params = {}
        pay_params = {}
    else:
        retreat_reason = retreat_block(universe, player_id) or _need_turns(player, rc)
        toll = _hostile_toll(universe, player_id, sector)
        if toll is None:
            pay_reason = "these fighters take no toll"
        else:
            bill = int(toll.count) * K.SECTOR_TOLL_CREDITS_PER_FIGHTER
            pay_reason = None if int(player.credits) >= bill else f"the toll is {bill} credits"
        retreat_params = {"to": challenge.get("from_sector")}
        pay_params = {}
        toll = _hostile_toll(universe, player_id, sector)
        if toll is not None:
            pay_params["amount"] = int(toll.count) * K.SECTOR_TOLL_CREDITS_PER_FIGHTER
    out.append(_la(ActionKind.RETREAT, legal=retreat_reason is None, reason=retreat_reason, cost=rc,
                   params=retreat_params))
    out.append(_la(ActionKind.PAY_TOLL, legal=pay_reason is None, reason=pay_reason,
                   cost=int(K.TURN_COST["pay_toll"]), params=pay_params))

    if challenge is not None:
        # While fighters challenge the ship, only the answers stay open (SHIP_COMBAT.md).
        allowed = {k.value for k in CHALLENGE_VERBS}
        for la in out:
            if la.kind == ActionKind.ATTACK.value:
                la.params["target"] = {"type": "str", "required": True, "choices": ["fighters"],
                                       "players": [], "ferrengi": []}
                why = _need_turns(player, atk_cost)
                if why is None and getattr(player.ship, "photon_disabled_ticks", 0) > 0:
                    why = "your fighters are offline (photon)"
                if why is None and int((la.params.get("qty") or {}).get("max") or 0) <= 0:
                    why = "no fighters aboard to attack with"
                la.legal, la.reason = why is None, why
            elif la.kind not in allowed and la.legal:
                la.legal, la.reason = False, CHALLENGE_REFUSAL

    if ferr_enc is not None:
        # Same as apply_action: every other legal verb stays legal but pays tribute first.
        allowed_f = {k.value for k in FERRENGI_ENCOUNTER_VERBS}
        fid = str(ferr_enc.get("ferr_id"))
        for la in out:
            if la.kind == ActionKind.ATTACK.value:
                la.params["ferrengi_answer"] = fid
                la.params["ferrengi_note"] = f"attacking {fid} answers; another target pays tribute first"
            elif la.kind not in allowed_f and la.legal:
                la.params["ferrengi_note"] = FERRENGI_ENCOUNTER_NOTE

    if getattr(player, "flee_penalty", False):
        # Same as apply_action: only a turn-using land or port action pays it, and never past the day.
        for la in out:
            if la.kind in (ActionKind.LAND_PLANET.value, ActionKind.TRADE.value) and la.turn_cost > 0:
                extra = min(int(K.FLEE_PENALTY_TURNS), max(0, _turns_left(player) - la.turn_cost))
                la.turn_cost += extra
                la.params["flee_penalty_turns"] = extra

    # Keep engine order stable: follow ActionKind declaration order.
    order = {k.value: i for i, k in enumerate(ActionKind)}
    out.sort(key=lambda la: order.get(la.kind, 999))
    # ---- fedspace-police-v1: Police HQ (sector 1) ----
    if K.fed_tw2002():
        from .fed import police_legal_specs
        kind_map = {
            "apply_commission": ActionKind.APPLY_COMMISSION,
            "post_reward": ActionKind.POST_REWARD,
            "claim_reward": ActionKind.CLAIM_REWARD,
        }
        for kind_val, legal, reason, params in police_legal_specs(universe, player_id):
            out.append(_la(kind_map[kind_val], legal=legal, reason=reason, cost=0, params=params))

    if K.ship_tw_on():
        from .ship_transwarp import legal_spec
        ok, why, params, cost = legal_spec(universe, player_id)
        out.append(_la(ActionKind.SHIP_TRANSWARP, legal=ok, reason=why, cost=cost, params=params))

    if K.fleet_on():  # SHIP_FLEET.md fl7 / fl8 (legacy: absent)
        from .fleet import legal_specs as fleet_legal_specs
        kinds = {"sell_ship": ActionKind.SELL_SHIP, "ship_transport": ActionKind.SHIP_TRANSPORT}
        for kind_val, ok, why, cost, params in fleet_legal_specs(universe, player_id):
            if ok and challenge is not None:
                ok, why = False, CHALLENGE_REFUSAL
            out.append(_la(kinds[kind_val], legal=ok, reason=why, cost=cost, params=params))

    if K.tow_on():  # SHIP_TOW.md tt5 (legacy: absent); after the fleet verbs = ActionKind order
        from .tow import legal_specs as tow_legal_specs
        tkinds = {"tow_engage": ActionKind.TOW_ENGAGE, "tow_release": ActionKind.TOW_RELEASE}
        for kind_val, ok, why, cost, params in tow_legal_specs(universe, player_id):
            if ok and challenge is not None:
                ok, why = False, CHALLENGE_REFUSAL
            out.append(_la(tkinds[kind_val], legal=ok, reason=why, cost=cost, params=params))

    if K.planet_trade_on():  # PLANETARY_TRADING.md pt1 / step 4 (legacy: absent); after the tow verbs
        from .planet_trade import legal_spec as planet_trade_legal_spec
        ok, why, cost, params = planet_trade_legal_spec(universe, player_id)
        if ok and challenge is not None:
            ok, why = False, CHALLENGE_REFUSAL
        out.append(_la(ActionKind.PLANET_TRADE, legal=ok, reason=why, cost=cost, params=params))

    if K.corpship_on():
        from .corpships import legal_specs as corp_legal_specs
        ckinds = {
            "ship_set_corporate": ActionKind.SHIP_SET_CORPORATE,
            "ship_set_personal": ActionKind.SHIP_SET_PERSONAL,
            "ship_set_password": ActionKind.SHIP_SET_PASSWORD,
        }
        for kind_val, ok, why, cost, params in corp_legal_specs(universe, player_id):
            if ok and challenge is not None:
                ok, why = False, CHALLENGE_REFUSAL
            out.append(_la(ckinds[kind_val], legal=ok, reason=why, cost=cost, params=params))

    if K.port_upgrade_on():  # PORT_UPGRADE_BUILD.md (legacy: both verbs absent)
        from .port_build import build_legal_spec, upgrade_legal_spec
        ok, why, cost, params = upgrade_legal_spec(universe, player_id)
        if ok and challenge is not None:
            ok, why = False, CHALLENGE_REFUSAL
        out.append(_la(ActionKind.PORT_UPGRADE, legal=ok, reason=why, cost=cost, params=params))
        ok, why, cost, params = build_legal_spec(universe, player_id)
        if ok and challenge is not None:
            ok, why = False, CHALLENGE_REFUSAL
        out.append(_la(ActionKind.PORT_BUILD, legal=ok, reason=why, cost=cost, params=params))

    if K.bank_on():  # GALACTIC_BANK_TAX.md (legacy: the three verbs are absent)
        from .bank import deposit_legal_spec, transfer_legal_spec, withdraw_legal_spec
        for kind, spec in (
            (ActionKind.BANK_DEPOSIT, deposit_legal_spec),
            (ActionKind.BANK_WITHDRAW, withdraw_legal_spec),
            (ActionKind.BANK_TRANSFER, transfer_legal_spec),
        ):
            ok, why, cost, params = spec(universe, player_id)
            if ok and challenge is not None:
                ok, why = False, CHALLENGE_REFUSAL
            out.append(_la(kind, legal=ok, reason=why, cost=cost, params=params))

    if K.tavern_on():  # STARDOCK_TAVERN.md: after the bank verbs, which is ActionKind order
        from .tavern import legal_specs as tavern_legal_specs
        tavern_kinds = {
            "tavern_announce": ActionKind.TAVERN_ANNOUNCE,
            "tavern_talk": ActionKind.TAVERN_TALK,
            "tavern_graffiti": ActionKind.TAVERN_GRAFFITI,
            "tavern_order": ActionKind.TAVERN_ORDER,
            "grimy_ask": ActionKind.GRIMY_ASK,
            "grimy_curse": ActionKind.GRIMY_CURSE,
            "underground_enter": ActionKind.UNDERGROUND_ENTER,
            "underground_contract": ActionKind.UNDERGROUND_CONTRACT,
            "underground_claim": ActionKind.UNDERGROUND_CLAIM,
            "tricron": ActionKind.TRICRON,
        }
        for kind_val, legal, reason, params, cost in tavern_legal_specs(universe, player_id):
            out.append(_la(tavern_kinds[kind_val], legal=legal, reason=reason or None, cost=cost, params=params))

    if K.stardock_extra_on():
        from .cineplex import legal_spec as cineplex_legal_spec
        ok, why, cost, params = cineplex_legal_spec(universe, player_id)
        if ok and challenge is not None:
            ok, why = False, CHALLENGE_REFUSAL
        out.append(_la(ActionKind.CINEPLEX, legal=ok, reason=why, cost=cost, params=params))

    return out


def legal_actions_compact(actions: list[LegalAction]) -> dict[str, Any]:
    """Small form for the LLM user message: legal kinds + short reasons for the rest."""
    return {
        "legal": [a.kind for a in actions if a.legal],
        "blocked": {a.kind: a.reason for a in actions if not a.legal and a.reason},
    }
