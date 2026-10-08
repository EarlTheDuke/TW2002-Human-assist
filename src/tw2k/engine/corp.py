"""Corporations. docs/playtests/corps/CORP_RULES.md.

Legacy handlers stay in runner.py. This module runs only while K.corp_rules_on().
"""

from __future__ import annotations

from typing import Any

from . import constants as K
from .actions import Action, ActionKind, ActionResult
from .models import (
    Commodity,
    Corporation,
    EventKind,
    FighterDeployment,
    FighterMode,
    MineDeployment,
    MineType,
    Universe,
)


def _password_eq(stored: str, given: str) -> bool:
    if K.CORPSHIP_PASSWORD_CASE != "exact":
        return stored.casefold() == given.casefold()
    return stored == given


def _side(alignment: int) -> str:
    if int(alignment) < 0:
        return "evil"
    return "good" if K.CORP_SIDE_OF_ZERO == "good" or int(alignment) > 0 else "evil"


def _corp_of(universe: Universe, pid: str):
    player = universe.players.get(pid)
    if player is None or not player.corp_ticker:
        return None
    return universe.corporations.get(player.corp_ticker)


def _is_member(universe: Universe, pid: str, corp: Corporation) -> bool:
    return pid in corp.member_ids and universe.players.get(pid) is not None


def _allied_only(universe: Universe, a_id: str, b_id: str) -> bool:
    a = universe.players.get(a_id)
    if a is None:
        return False
    for ally_id in a.alliances:
        ally = universe.alliances.get(ally_id)
        if ally is not None and ally.active and b_id in ally.member_ids:
            return True
    return False


def deploy_friend(universe: Universe, pid: str, dep) -> bool:
    """True when this deployment recognizes pid (no toll, no mine, no challenge)."""
    from .combat import _are_allied

    if not K.corp_rules_on():
        return dep.owner_id == pid or _are_allied(universe, pid, dep.owner_id)
    if dep.owner_id == K.ROGUE_OWNER_ID:
        return False
    ticker = getattr(dep, "corp_ticker", None)
    me = universe.players.get(pid)
    recognized = False
    recognized = (me is not None and me.corp_ticker == ticker) if ticker else dep.owner_id == pid
    if recognized:
        return True
    if K.ALLIANCE_DEPLOY_FRIENDLY == "none":
        return False
    if K.ALLIANCE_DEPLOY_FRIENDLY == "corporate" and not ticker:
        return False
    owner = dep.owner_id if not ticker else None
    if owner and _allied_only(universe, pid, owner):
        return True
    if ticker and me is not None:
        for mid in universe.corporations.get(ticker, Corporation(ticker=ticker, name="", ceo_id="")).member_ids:
            if _allied_only(universe, pid, mid):
                return True
    return False


def _controls(universe: Universe, pid: str, dep) -> bool:
    if dep is None:
        return False
    ticker = getattr(dep, "corp_ticker", None)
    if ticker:
        me = universe.players.get(pid)
        if K.CORP_RECLAIM_BY == "member":
            return me is not None and me.corp_ticker == ticker
        corp = universe.corporations.get(ticker)
        return corp is not None and corp.ceo_id == pid
    return dep.owner_id == pid


def event_visible(event, player_id: str, universe: Universe) -> bool:
    kind = event.kind
    if kind == EventKind.CORP_ROGUE:
        return True
    if kind in (EventKind.CORP_PASSWORD_SET, EventKind.CORP_BREAKIN_FAILED, EventKind.CORP_EXP_PENALTY):
        return event.actor_id == player_id  # QC 57: the penalty row is the member's own (cr9 "private")
    if kind == EventKind.CORP_TRANSFER:
        target = event.payload.get("target")
        return event.actor_id == player_id or target == player_id
    ticker = event.payload.get("ticker")
    corp = universe.corporations.get(ticker) if ticker else None
    members = set(corp.member_ids) if corp is not None else set()
    target = event.payload.get("target")
    if kind in (EventKind.CORP_DROP, EventKind.CORP_OUSTED, EventKind.CORP_DISSOLVED):
        return player_id == event.actor_id or player_id in members or player_id == target
    if kind == EventKind.CORP_INVITE:
        # cr27: the named target only; holding a pass does not show the other passes (QC 57)
        return player_id == event.actor_id or player_id in members or player_id == target
    if player_id == event.actor_id or player_id in members:
        return True
    return False


def _emit(universe: Universe, kind: EventKind, actor_id: str, summary: str, payload: dict, sector_id: int | None = None) -> None:
    universe.emit(kind, actor_id=actor_id, sector_id=sector_id, payload=payload, summary=summary)


def handle_corp_create(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    if player.corp_ticker is not None:
        return ActionResult(ok=False, error="already in a corporation")
    ticker = (action.args.get("ticker") or "").upper().strip()[:3]
    name = action.args.get("name") or f"Corp {ticker}"
    if not ticker or ticker in universe.corporations:
        return ActionResult(ok=False, error="invalid or taken ticker")
    cost = int(K.CORP_CREATE_COST)
    if player.credits < cost:
        return ActionResult(ok=False, error=f"need {cost} cr to incorporate")
    player.credits -= cost
    corp = Corporation(
        ticker=ticker, name=name, ceo_id=pid, member_ids=[pid],
        formed_day=universe.day, password=str(K.CORP_NEW_PASSWORD or ""),
    )
    universe.corporations[ticker] = corp
    player.corp_ticker = ticker
    _emit(universe, EventKind.CORP_CREATE, pid, f"{player.name} incorporated {name} [{ticker}]",
          {"ticker": ticker, "name": name}, player.sector_id)
    return ActionResult(ok=True, turns_spent=int(K.CORP_TURN_COST))


def handle_corp_set_password(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not K.corp_rules_on():
        return ActionResult(ok=False, error="unsupported action")
    player = universe.players[pid]
    corp = _corp_of(universe, pid)
    if corp is None or corp.ceo_id != pid:
        return ActionResult(ok=False, error="only the C.E.O. may set the password")
    raw = str(action.args.get("password") or "")
    if not raw or len(raw) > int(K.CORPSHIP_PASSWORD_MAX_LEN):
        return ActionResult(ok=False, error=f"password must be 1..{int(K.CORPSHIP_PASSWORD_MAX_LEN)} characters")
    corp.password = raw
    _emit(universe, EventKind.CORP_PASSWORD_SET, pid, f"{player.name} set the {corp.ticker} password",
          {"ticker": corp.ticker})
    return ActionResult(ok=True, turns_spent=int(K.CORP_TURN_COST))


def handle_corp_invite(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    corp = _corp_of(universe, pid)
    if corp is None:
        return ActionResult(ok=False, error="not in a corporation")
    if not corp.password:
        return ActionResult(ok=False, error="set a password first")
    if K.CORP_APPROVER == "ceo" and corp.ceo_id != pid:
        return ActionResult(ok=False, error="only the C.E.O. may invite")
    if pid not in corp.member_ids:
        return ActionResult(ok=False, error="not in a corporation")
    target = action.args.get("target")
    if target not in universe.players or not universe.players[target].alive:
        return ActionResult(ok=False, error="no such trader")
    if target == pid or universe.players[target].corp_ticker:
        return ActionResult(ok=False, error="no such trader")
    held = flagship_join_block(universe.players[target])
    if held:
        return ActionResult(ok=False, error=held)
    universe.players[target].inbox.append({
        "from": pid, "kind": "corp_invite", "ticker": corp.ticker,
        "password": corp.password,
        "message": f"You are invited to join {corp.name} [{corp.ticker}].",
        "day": universe.day,
    })
    if target not in corp.invited_ids:
        corp.invited_ids.append(target)
    _emit(universe, EventKind.CORP_INVITE, pid,
          f"{player.name} invited {universe.players[target].name} to {corp.ticker}",
          {"ticker": corp.ticker, "target": target})
    return ActionResult(ok=True, turns_spent=int(K.CORP_TURN_COST))


def flagship_buy_block(universe: Universe, pid: str, class_key: str) -> str | None:
    """bc24: only the C.E.O. buys a Corporate FlagShip. Purchase, not use."""
    if class_key != "corporate_flagship" or not K.corp_bots_on() or K.CFS_CEO_RULE != "purchase":
        return None
    player = universe.players[pid]
    corp = universe.corporations.get(player.corp_ticker or "")
    if corp is None or corp.ceo_id != pid:
        return "only a C.E.O. may buy a Corporate FlagShip"
    return None


def flagship_join_block(player) -> str | None:
    """bc25: a pilot flying a FlagShip cannot join. A parked one does not count."""
    if not K.corp_bots_on() or K.CFS_HOLDER_MAY_JOIN or K.CFS_JOIN_CHECK != "flown":
        return None
    if getattr(getattr(player, "ship", None), "ship_class", None) is None:
        return None
    if player.ship.ship_class.value == "corporate_flagship":
        return "a FlagShip pilot cannot join a corporation"
    return None


def _join_block(universe: Universe, pid: str, corp: Corporation | None, password: str) -> str | None:
    player = universe.players[pid]
    if player.corp_ticker is not None:
        return "already in a corporation"
    if not player.alive:
        return "not alive"
    if corp is None:
        return "no such corporation"
    if not corp.password:
        return "set a password first"
    capped = int(getattr(player, "corp_breakins_today", 0) or 0) >= int(K.CORP_BREAKIN_PER_DAY)
    if K.CORP_BREAKIN_RULE != "wrong_guesses" and capped:
        return "one break-in attempt per day"
    if not _password_eq(corp.password, password):
        if capped:
            return "one break-in attempt per day"
        return "wrong password"
    if len(corp.member_ids) >= int(K.CORP_MAX_MEMBERS):
        return "corp is full"
    if K.CORP_ALIGNMENT_RULE == "same_side":
        ceo = universe.players.get(corp.ceo_id)
        if ceo is not None and _side(player.alignment) != _side(ceo.alignment):
            return "alignment does not match the C.E.O."
    held = flagship_join_block(player)
    if held:
        return held
    return None


def handle_corp_join(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    ticker = (action.args.get("ticker") or "").upper()
    corp = universe.corporations.get(ticker)
    password = str(action.args.get("password") or "")
    capped = int(getattr(player, "corp_breakins_today", 0) or 0) >= int(K.CORP_BREAKIN_PER_DAY)
    if corp is not None and corp.password and capped and K.CORP_BREAKIN_RULE != "wrong_guesses":
        return ActionResult(ok=False, error="one break-in attempt per day")
    reason = _join_block(universe, pid, corp, password)
    if reason == "wrong password" and corp is not None:
        player.corp_breakins_today = int(getattr(player, "corp_breakins_today", 0) or 0) + 1
        if int(K.CORP_BREAKIN_ALIGN_LOSS):
            player.alignment -= int(K.CORP_BREAKIN_ALIGN_LOSS)
        _emit(universe, EventKind.CORP_BREAKIN_FAILED, pid, f"{player.name} failed to join {ticker}",
              {"ticker": ticker})
        return ActionResult(ok=False, error="wrong password")
    if reason:
        return ActionResult(ok=False, error=reason)
    assert corp is not None
    corp.member_ids.append(pid)
    if pid in corp.invited_ids:
        corp.invited_ids.remove(pid)
    player.corp_ticker = ticker
    _emit(universe, EventKind.CORP_JOIN, pid, f"{player.name} joined {corp.name} [{ticker}]", {"ticker": ticker})
    return ActionResult(ok=True, turns_spent=int(K.CORP_TURN_COST))


def _planets_on_leave(universe: Universe, pid: str, ticker: str, ceo_id: str) -> None:
    if K.CORP_LEAVER_PLANETS == "leaver_keeps":
        for planet in universe.planets.values():
            if planet.owner_id == pid and planet.corp_ticker == ticker:
                planet.corp_ticker = None
        return
    for planet in universe.planets.values():
        if planet.owner_id == pid and planet.corp_ticker == ticker:
            planet.owner_id = ceo_id


def _call_corpship(which: str, universe: Universe, *args) -> None:
    if not K.corpship_on():
        return
    from . import corpships
    getattr(corpships, which)(universe, *args)


def remove_member(universe: Universe, pid: str, corp: Corporation, *, dissolve: bool = False) -> None:
    """Take pid out. dissolve=False keeps the corp and moves his ticker-planets."""
    player = universe.players.get(pid)
    if player is not None and player.corp_ticker == corp.ticker:
        player.corp_ticker = None
    corp.member_ids = [m for m in corp.member_ids if m != pid]
    if not dissolve:
        _planets_on_leave(universe, pid, corp.ticker, corp.ceo_id)
        _call_corpship("on_member_leave", universe, pid, corp.ticker)


def _rogue(dep) -> None:
    dep.owner_id = K.ROGUE_OWNER_ID
    dep.corp_ticker = None
    dep.toll_credits = 0 if hasattr(dep, "toll_credits") else getattr(dep, "toll_credits", 0)


def disband(universe: Universe, corp: Corporation) -> None:
    ceo = universe.players.get(corp.ceo_id)
    if ceo is not None and not ceo.alive:
        ceo = None  # QC 57: an eliminated C.E.O. (cr15) takes nothing; his sector goes rogue too
    ceo_sector = ceo.sector_id if ceo is not None else None
    for sector in universe.sectors.values():
        dep = sector.fighters
        if dep is not None and getattr(dep, "corp_ticker", None) == corp.ticker:
            if sector.id == ceo_sector and ceo is not None:
                dep.owner_id = corp.ceo_id
                dep.corp_ticker = None
            else:
                count = int(dep.count)
                _rogue(dep)
                universe.emit(  # cr28: public, no owner (QC 57: no actor either, or rivals log a C.E.O. sighting)
                    EventKind.CORP_ROGUE, actor_id=None, sector_id=sector.id,
                    payload={"sector_id": sector.id, "count": count, "kind": "fighters"},
                    summary=f"{count} corporate fighters in {sector.id} went rogue",
                )
        kept: list = []
        for md in list(sector.mines):
            if getattr(md, "corp_ticker", None) != corp.ticker:
                kept.append(md)
                continue
            if sector.id == ceo_sector and ceo is not None:
                md.owner_id = corp.ceo_id
                md.corp_ticker = None
                kept.append(md)
            elif K.CORP_DISBAND_MINES == "removed":
                continue
            else:
                md.owner_id = K.ROGUE_OWNER_ID
                md.corp_ticker = None
                kept.append(md)
        sector.mines = kept
    if K.CORP_DISBAND_PLANETS == "v306":
        # REV 372-374: planets in the C.E.O.'s sector become his, the rest are orphaned (QC 57: the
        # orphan event names the real former owner instead of None).
        for planet in list(universe.planets.values()):
            if planet.corp_ticker != corp.ticker:
                continue
            if ceo is not None and planet.sector_id == ceo.sector_id:
                planet.owner_id = corp.ceo_id
                planet.corp_ticker = None
                continue
            former = planet.owner_id
            planet.owner_id = None
            planet.corp_ticker = None
            universe.emit(
                EventKind.PLANET_ORPHANED, actor_id=former, sector_id=planet.sector_id,
                payload={"planet_id": planet.id, "planet_name": planet.name, "former_owner": former,
                         "citadel_level": planet.citadel_level, "fighters": planet.fighters},
                summary=(f"Planet {planet.name} (L{planet.citadel_level} citadel, {planet.fighters} fighters) "
                         f"is now UNCLAIMED after [{corp.ticker}] disbanded."),
            )
    else:
        from .runner import _release_dissolved_corp_planets
        _release_dissolved_corp_planets(universe, corp.ticker)
    _call_corpship("on_corp_extinct", universe, corp.ticker)
    for mid in list(corp.member_ids):
        member = universe.players.get(mid)
        if member is not None:
            member.corp_ticker = None
        universe.emit(
            EventKind.CORP_DISSOLVED, actor_id=corp.ceo_id,
            payload={"ticker": corp.ticker, "target": mid},
            summary=f"[{corp.ticker}] dissolved",
        )
    corp.member_ids = []
    universe.corporations.pop(corp.ticker, None)


def handle_corp_leave(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    corp = _corp_of(universe, pid)
    if corp is None:
        return ActionResult(ok=False, error="not in a corp")
    if corp.ceo_id == pid:
        disband(universe, corp)
    else:
        remove_member(universe, pid, corp)
        _emit(universe, EventKind.CORP_LEAVE, pid, f"{player.name} left {corp.ticker}", {"ticker": corp.ticker})
    return ActionResult(ok=True, turns_spent=int(K.CORP_TURN_COST))


def handle_corp_drop(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not K.corp_rules_on():
        return ActionResult(ok=False, error="unsupported action")
    corp = _corp_of(universe, pid)
    if corp is None or corp.ceo_id != pid:
        return ActionResult(ok=False, error="only the C.E.O. may drop a member")
    target = action.args.get("target")
    if target == pid or target not in corp.member_ids:
        return ActionResult(ok=False, error="no such member")
    remove_member(universe, target, corp)
    _emit(universe, EventKind.CORP_DROP, pid, f"{universe.players[pid].name} dropped a member from {corp.ticker}",
          {"ticker": corp.ticker, "target": target})
    dropped = universe.players.get(target)
    if dropped is not None:
        dropped.inbox.append({
            "from": pid, "kind": "corp_drop", "ticker": corp.ticker,
            "message": f"You were dropped from {corp.ticker}.", "day": universe.day,
        })
    return ActionResult(ok=True, turns_spent=int(K.CORP_TURN_COST))


def _ship_room(ship, item: str) -> int:
    spec = K.hull_spec(ship.ship_class.value) or {}
    if item == "credits":
        return 10**12
    if item == "fighters":
        return max(0, int(spec.get("max_fighters") or 0) - int(ship.fighters))
    if item == "shields":
        return max(0, int(spec.get("max_shields") or 0) - int(ship.shields))
    if item in ("armid_mines", "limpet_mines"):
        kind = MineType.ARMID if item == "armid_mines" else MineType.LIMPET
        return max(0, int(spec.get("max_mines") or 0) - int(ship.mines.get(kind, 0)))
    return 0


def _ship_have(ship, item: str) -> int:
    if item == "credits":
        return 0
    if item == "fighters":
        return int(ship.fighters)
    if item == "shields":
        return int(ship.shields)
    if item == "armid_mines":
        return int(ship.mines.get(MineType.ARMID, 0))
    if item == "limpet_mines":
        return int(ship.mines.get(MineType.LIMPET, 0))
    return 0


def _whole(raw: Any) -> int:
    """A whole quantity, else 0 (QC 57: 2.5 and True are not quantities)."""
    if isinstance(raw, bool):
        return 0
    if isinstance(raw, float):
        return int(raw) if raw.is_integer() else 0
    try:
        return int(raw or 0)
    except (TypeError, ValueError):
        return 0


def _move_cargo(giver, receiver, item: str, qty: int) -> None:
    if item == "credits":
        giver.credits -= qty
        receiver.credits += qty
        return
    g, r = giver.ship, receiver.ship
    if item == "fighters":
        g.fighters -= qty
        r.fighters += qty
    elif item == "shields":
        g.shields -= qty
        r.shields += qty
    else:
        kind = MineType.ARMID if item == "armid_mines" else MineType.LIMPET
        g.mines[kind] = int(g.mines.get(kind, 0)) - qty
        r.mines[kind] = int(r.mines.get(kind, 0)) + qty


def handle_corp_transfer(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not K.corp_rules_on():
        return ActionResult(ok=False, error="unsupported action")
    if not K.CORP_TRANSFER_TAKE and action.args.get("direction") == "take":
        return ActionResult(ok=False, error="take is not allowed")
    player = universe.players[pid]
    corp = _corp_of(universe, pid)
    if corp is None:
        return ActionResult(ok=False, error="not in a corporation")
    target_id = action.args.get("target")
    target = universe.players.get(target_id) if isinstance(target_id, str) else None
    item = str(action.args.get("item") or "")
    direction = str(action.args.get("direction") or "give")
    qty = _whole(action.args.get("qty"))
    allowed = tuple(x for x in ("credits", "fighters", "shields", "armid_mines", "limpet_mines")
                    if x in ("credits", "fighters", "shields")
                    or (x == "armid_mines" and "armid" in K.CORP_TRANSFER_MINE_KINDS)
                    or (x == "limpet_mines" and "limpet" in K.CORP_TRANSFER_MINE_KINDS))
    if item not in allowed or direction not in ("give", "take") or qty < 1:
        return ActionResult(ok=False, error="invalid transfer")
    if target is None or target.corp_ticker != corp.ticker or target_id == pid or not target.alive:
        return ActionResult(ok=False, error="no such member")
    if target.sector_id != player.sector_id:
        return ActionResult(ok=False, error="not in the same sector")
    if K.CORP_TRANSFER_LANDED == "refuse" and (player.planet_landed is not None or target.planet_landed is not None):
        return ActionResult(ok=False, error="both traders must be in their ships")
    if K.hardware_tw2002() and getattr(target.ship, "cloaked", False):
        return ActionResult(ok=False, error="that trader is cloaked")
    giver, receiver = (player, target) if direction == "give" else (target, player)
    if item == "credits":
        if giver.credits < qty:
            return ActionResult(ok=False, error=f"at most {giver.credits} credits")
    else:
        have = _ship_have(giver.ship, item)
        room = _ship_room(receiver.ship, item)
        if qty > have:
            return ActionResult(ok=False, error=f"at most {have}")
        if qty > room:
            return ActionResult(ok=False, error=f"the ship can take {room} more")
    _move_cargo(giver, receiver, item, qty)
    _emit(universe, EventKind.CORP_TRANSFER, pid,
          f"{player.name} transferred {qty} {item}",
          {"ticker": corp.ticker, "target": target_id, "item": item, "qty": qty, "direction": direction})
    return ActionResult(ok=True, turns_spent=int(K.CORP_TURN_COST))


def handle_corp_deposit(universe: Universe, pid: str, action: Action) -> ActionResult:
    return ActionResult(ok=False, error="unsupported action")


def handle_corp_withdraw(universe: Universe, pid: str, action: Action) -> ActionResult:
    return ActionResult(ok=False, error="unsupported action")


def extern_corp_step(universe: Universe) -> None:
    for player in universe.players.values():
        player.corp_breakins_today = 0
    if K.CORP_ALIGNMENT_RULE == "mixed":
        _mixed_penalty(universe)
    elif K.CORP_ALIGNMENT_RULE == "same_side":
        _oust_opposite(universe)
    for corp in list(universe.corporations.values()):
        ceo = universe.players.get(corp.ceo_id)
        if ceo is None or not ceo.alive:
            disband(universe, corp)
            continue
        for mid in list(corp.member_ids):
            member = universe.players.get(mid)
            if member is None or not member.alive:
                if mid == corp.ceo_id:
                    disband(universe, corp)
                    break
                remove_member(universe, mid, corp)


def mixed_loss(universe: Universe, corp: Corporation) -> int:
    """cr9: experience each alive member loses at the next Extern (0 for a straight corp or same_side)."""
    if K.CORP_ALIGNMENT_RULE != "mixed":
        return 0
    alive = [universe.players[m] for m in corp.member_ids
             if m in universe.players and universe.players[m].alive]
    goods = [p for p in alive if int(p.alignment) > 0]
    evils = [p for p in alive if int(p.alignment) < 0]
    if not goods or not evils:
        return 0
    if K.MIXED_CORP_EXP_RULE == "least_extreme":
        most_good = max(int(p.alignment) for p in goods)
        most_evil = min(int(p.alignment) for p in evils)
        base = min(most_good, abs(most_evil))
    else:
        base = max(int(p.alignment) for p in goods)
    return int(base) // int(K.MIXED_CORP_EXP_DIVISOR)


def _mixed_penalty(universe: Universe) -> None:
    for corp in list(universe.corporations.values()):
        alive = [universe.players[m] for m in corp.member_ids
                 if m in universe.players and universe.players[m].alive]
        loss = mixed_loss(universe, corp)
        if loss <= 0:
            continue
        for player in alive:
            if int(player.experience) <= int(K.MIXED_CORP_EXP_FLOOR):
                continue
            player.experience = max(int(K.MIXED_CORP_EXP_FLOOR), int(player.experience) - loss)
            universe.emit(
                EventKind.CORP_EXP_PENALTY, actor_id=player.id,
                payload={"ticker": corp.ticker, "loss": loss, "experience": int(player.experience)},
                summary=f"{player.name} lost {loss} experience for a mixed corp",
            )


def _oust_opposite(universe: Universe) -> None:
    for corp in list(universe.corporations.values()):
        ceo = universe.players.get(corp.ceo_id)
        if ceo is None:
            continue
        ceo_side = _side(ceo.alignment)
        for mid in list(corp.member_ids):
            if mid == corp.ceo_id:
                continue
            member = universe.players.get(mid)
            if member is None or not member.alive:
                continue
            if _side(member.alignment) != ceo_side:
                remove_member(universe, mid, corp)
                universe.emit(
                    EventKind.CORP_OUSTED, actor_id=corp.ceo_id,
                    payload={"ticker": corp.ticker, "target": mid},
                    summary=f"{member.name} was ousted from {corp.ticker}",
                )


def _ownership(player, raw) -> tuple[str | None, str | None]:
    """Return (ownership, error)."""
    choice = raw if raw in ("personal", "corporate") else None
    if choice is None:
        choice = "corporate" if player.corp_ticker and K.CORP_DEPLOY_DEFAULT == "corporate" else "personal"
    if choice == "corporate" and not player.corp_ticker:
        return None, "corporate deployments need a corporation"
    return choice, None


def handle_deploy_fighters(universe: Universe, pid: str, action: Action) -> ActionResult:
    from .runner import _resolve_fighter_sector_combat

    player = universe.players[pid]
    sector = universe.sectors[player.sector_id]
    try:
        qty = int(action.args.get("qty", 0))
    except (TypeError, ValueError):
        qty = -1
    mode_raw = action.args.get("mode", "defensive")
    try:
        mode = FighterMode(mode_raw)
    except ValueError:
        return ActionResult(ok=False, error=f"invalid fighter mode {mode_raw!r}")
    ownership, err = _ownership(player, action.args.get("ownership"))
    if err:
        return ActionResult(ok=False, error=err)
    ticker = player.corp_ticker if ownership == "corporate" else None
    cost = K.TURN_COST["deploy_fighters"]
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    if sector.id in K.FEDSPACE_SECTORS:
        return ActionResult(ok=False, error="cannot deploy fighters in FedSpace")
    dep = sector.fighters
    if qty == 0:
        if not _controls(universe, pid, dep):
            return ActionResult(ok=False, error="you do not control those fighters")
        if action.args.get("ownership") not in ("personal", "corporate"):
            ownership = "corporate" if getattr(dep, "corp_ticker", None) else "personal"  # QC 57: keep the kind
            ticker = player.corp_ticker if ownership == "corporate" else None
        dep.mode = mode
        if ownership == "personal":
            dep.owner_id = pid
            dep.corp_ticker = None
        else:
            dep.corp_ticker = ticker
            dep.owner_id = pid
        return ActionResult(ok=True, turns_spent=cost)
    if qty <= 0 or qty > player.ship.fighters:
        return ActionResult(ok=False, error="invalid fighter quantity")
    if K.sector_fighter_tw2002() and (dep is None or _controls(universe, pid, dep)):
        cap = K.SECTOR_FIGHTER_CAP_WITH_PLANET if sector.planet_ids else K.SECTOR_FIGHTER_CAP
        have = int(dep.count) if dep is not None else 0
        if have + qty > cap:
            return ActionResult(ok=False, error="sector fighter cap")
    if dep is None:
        sector.fighters = FighterDeployment(owner_id=pid, count=qty, mode=mode, corp_ticker=ticker)
    elif _same_group(player, dep, ownership, ticker):
        dep.count += qty
        dep.mode = mode
        dep.owner_id = pid
        dep.corp_ticker = ticker
    elif _cross_group(player, dep, ownership):
        return ActionResult(ok=False, error="that group is the other kind")
    else:
        _resolve_fighter_sector_combat(universe, pid, sector.id, incoming_fighters=qty, incoming_mode=mode)
        player.ship.fighters -= qty
        return ActionResult(ok=True, turns_spent=cost)
    player.ship.fighters -= qty
    universe.emit(
        EventKind.DEPLOY_FIGHTERS, actor_id=pid, sector_id=sector.id,
        payload={"qty": qty, "mode": mode.value, "ownership": ownership},
        summary=f"{player.name} deployed {qty} {mode.value} fighters in {sector.id}",
    )
    return ActionResult(ok=True, turns_spent=cost)


def _same_group(player, dep, ownership: str, ticker: str | None) -> bool:
    if ownership == "corporate":
        return getattr(dep, "corp_ticker", None) == ticker
    return getattr(dep, "corp_ticker", None) in (None, "") and dep.owner_id == player.id


def _cross_group(player, dep, ownership: str) -> bool:
    """Personal into your corp's corporate group, or corporate into your personal group."""
    dep_ticker = getattr(dep, "corp_ticker", None)
    if ownership == "personal" and dep_ticker and dep_ticker == player.corp_ticker:
        return True
    if ownership == "corporate" and not dep_ticker and dep.owner_id == player.id:
        return True
    return False


def handle_deploy_mines(universe: Universe, pid: str, action: Action) -> ActionResult:
    from .runner import _handle_atomic_detonation

    player = universe.players[pid]
    sector = universe.sectors[player.sector_id]
    try:
        qty = int(action.args.get("qty", 0))
    except (TypeError, ValueError):
        qty = 0
    try:
        kind = MineType(action.args.get("kind", "armid"))
    except ValueError:
        return ActionResult(ok=False, error="invalid mine type")
    ownership, err = _ownership(player, action.args.get("ownership"))
    if err:
        return ActionResult(ok=False, error=err)
    ticker = player.corp_ticker if ownership == "corporate" else None
    if kind == MineType.ATOMIC and not K.atomic_mines_sold():
        return ActionResult(ok=False, error="atomic mines are retired (ATOMIC_MINES_PORT_NUKE off)")
    if qty <= 0 or qty > player.ship.mines.get(kind, 0):
        return ActionResult(ok=False, error="insufficient mines")
    if sector.id in K.FEDSPACE_SECTORS:
        return ActionResult(ok=False, error="cannot deploy mines in FedSpace")
    cost = K.TURN_COST["deploy_mines"]
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    if kind == MineType.ATOMIC:
        return _handle_atomic_detonation(universe, pid, qty, sector, cost)
    if kind != MineType.ATOMIC and K.sector_fighter_tw2002():
        sitting = sum(int(m.count) for m in sector.mines)
        if sitting + qty > K.SECTOR_MINE_CAP:
            return ActionResult(ok=False, error="sector mine cap")
    existing = next((m for m in sector.mines if m.kind == kind and _same_group(player, m, ownership, ticker)), None)
    if existing:
        existing.count += qty
        existing.owner_id = pid
    else:
        sector.mines.append(MineDeployment(owner_id=pid, kind=kind, count=qty, corp_ticker=ticker))
    player.ship.mines[kind] -= qty
    universe.emit(
        EventKind.DEPLOY_MINES, actor_id=pid, sector_id=sector.id,
        payload={"qty": qty, "kind": kind.value, "ownership": ownership},
        summary=f"{player.name} deployed {qty} {kind.value} mines in {sector.id}",
    )
    return ActionResult(ok=True, turns_spent=cost)


def public_corporations(universe: Universe) -> list[dict[str, Any]]:
    rows = []
    for corp in universe.corporations.values():
        members = []
        exp = 0
        align = 0
        for mid in corp.member_ids:
            player = universe.players.get(mid)
            if player is None:
                continue
            exp += int(player.experience)
            align += int(player.alignment)
            members.append({"id": mid, "name": player.name, "ceo": mid == corp.ceo_id})
        rows.append({
            "ticker": corp.ticker, "name": corp.name, "formed_day": corp.formed_day,
            "ceo": corp.ceo_id, "members": members, "exp": exp, "alignment": align,
        })
    rows.sort(key=lambda r: (-r["exp"], r["ticker"]))
    for i, row in enumerate(rows, start=1):
        row["rank"] = i
    return rows


def member_block(universe: Universe, player) -> dict[str, Any] | None:
    corp = universe.corporations.get(player.corp_ticker) if player.corp_ticker else None
    if corp is None:
        return None
    members = []
    for mid in corp.member_ids:
        other = universe.players.get(mid)
        if other is None:
            continue
        cloaked = K.hardware_tw2002() and getattr(other.ship, "cloaked", False)
        row: dict[str, Any] = {
            "id": mid, "name": other.name, "ceo": mid == corp.ceo_id,
            "on_planet": other.planet_landed is not None,
            "fighters": int(other.ship.fighters), "shields": int(other.ship.shields),
            "armid_mines": int(other.ship.mines.get(MineType.ARMID, 0)),
            "limpet_mines": int(other.ship.mines.get(MineType.LIMPET, 0)),
            "credits": int(other.credits), "alive": other.alive,
        }
        if not cloaked:
            row["sector_id"] = other.sector_id
        members.append(row)
    planets = []
    for planet in universe.planets.values():
        if planet.corp_ticker != corp.ticker:
            continue
        from .planets import planet_growth_status  # cr23: production and stock per commodity (QC 57)
        growth = planet_growth_status(planet.class_id, planet.colonists,
                                      int(planet.stockpile.get(Commodity.ORGANICS, 0)))
        row = {
            "sector_id": planet.sector_id, "name": planet.name,
            "population": sum(int(n) for n in planet.colonists.values()),
            "production": growth["production"],
            "stock": {c.value: int(n) for c, n in planet.stockpile.items()},
            "fighters": int(planet.fighters), "citadel_level": int(planet.citadel_level),
            "shields": int(planet.shields), "credits": int(planet.treasury),
        }
        if K.corp_bots_on():  # bc26: members can name the planet and its fighter output
            from .planets import fighters_from_colonists
            row["planet_id"] = planet.id
            row["production"] = dict(growth["production"])
            row["production"]["fighters"] = int(fighters_from_colonists(planet.class_id, planet.colonists))
        planets.append(row)
    goods = [universe.players[m] for m in corp.member_ids
             if m in universe.players and universe.players[m].alive and int(universe.players[m].alignment) > 0]
    evils = [universe.players[m] for m in corp.member_ids
             if m in universe.players and universe.players[m].alive and int(universe.players[m].alignment) < 0]
    mixed = bool(goods and evils)
    penalty = mixed_loss(universe, corp)  # QC 57: follows the rule, the formula and same_side
    return {
        "ticker": corp.ticker, "name": corp.name, "ceo_id": corp.ceo_id,
        "members": members, "planets": planets, "password": corp.password,
        "cap": int(K.CORP_MAX_MEMBERS), "mixed": mixed, "exp_penalty_tomorrow": penalty,
    }


def append_legal(out: list, universe: Universe, player, player_id: str, _la) -> None:
    """Tw2002 corp verbs. Deposit and withdraw are not offered."""
    in_corp = player.corp_ticker is not None and player.corp_ticker in universe.corporations
    corp = universe.corporations.get(player.corp_ticker) if in_corp else None
    reason = "already in a corporation" if player.corp_ticker is not None else None
    if reason is None and int(player.credits) < int(K.CORP_CREATE_COST):  # QC 57: the handler's cost check
        reason = f"need {int(K.CORP_CREATE_COST)} cr to incorporate"
    out.append(_la(ActionKind.CORP_CREATE, legal=reason is None, reason=reason,
                   params={"ticker": {"type": "str", "required": True, "max_len": 3,
                                      "taken": sorted(universe.corporations)},
                           "name": {"type": "str", "required": False},
                           "cost": int(K.CORP_CREATE_COST), "turn_cost": int(K.CORP_TURN_COST)}))
    pw_reason = "only the C.E.O. may set the password" if corp is None or corp.ceo_id != player_id else None
    out.append(_la(ActionKind.CORP_SET_PASSWORD, legal=pw_reason is None, reason=pw_reason,
                   params={"password": {"type": "str", "required": True,
                                        "max_len": int(K.CORPSHIP_PASSWORD_MAX_LEN)},
                           "case": K.CORPSHIP_PASSWORD_CASE}))
    targets = []
    if corp is not None and corp.password and (K.CORP_APPROVER == "member" or corp.ceo_id == player_id):
        for other_id, other in universe.players.items():
            if other_id == player_id or not other.alive or other.corp_ticker:
                continue
            if flagship_join_block(other):
                continue
            targets.append({"player_id": other_id, "name": other.name})
    if not in_corp:
        inv_reason = "not in a corporation"
    elif not corp.password:
        inv_reason = "set a password first"
    elif not targets:
        inv_reason = "no trader to invite"
    else:
        inv_reason = None
    out.append(_la(ActionKind.CORP_INVITE, legal=inv_reason is None, reason=inv_reason,
                   params={"target": {"type": "str", "required": True, "choices": [t["player_id"] for t in targets]},
                           "targets": targets}))
    corps = []
    joinable = []
    breakins_left = max(0, int(K.CORP_BREAKIN_PER_DAY) - int(getattr(player, "corp_breakins_today", 0) or 0))
    for c in universe.corporations.values():
        room = int(K.CORP_MAX_MEMBERS) - len(c.member_ids)
        row = {"ticker": c.ticker, "name": c.name, "members": len(c.member_ids),
               "cap": int(K.CORP_MAX_MEMBERS), "room": room}
        # QC 57: the same checks the handler makes, minus the password itself (cr5, cr7, cr8)
        why = _join_block(universe, player_id, c, c.password) if c.password else "closed: no password set"
        if why:
            row["reason"] = why
        else:
            joinable.append(c.ticker)
        corps.append(row)
    if player.corp_ticker:
        join_reason = "already in a corporation"
    elif not player.alive:
        join_reason = "not alive"
    elif (
        K.CORP_BREAKIN_RULE != "wrong_guesses"
        and breakins_left <= 0
        and any(c.password for c in universe.corporations.values())
    ):
        join_reason = "one break-in attempt per day"
        joinable = []
    elif not joinable:
        join_reason = "no corporation with room"
    else:
        join_reason = None
    out.append(_la(ActionKind.CORP_JOIN, legal=join_reason is None, reason=join_reason,
                   params={"ticker": {"type": "str", "required": True, "choices": joinable},
                           "password": {"type": "str", "required": True},
                           "corps": corps,
                           "breakin_attempts_left": breakins_left}))
    out.append(_la(ActionKind.CORP_LEAVE, legal=in_corp, reason=None if in_corp else "not in a corp",
                   params={"dissolves": bool(corp and corp.ceo_id == player_id)}))
    members = [{"player_id": m, "name": universe.players[m].name}
               for m in (corp.member_ids if corp else []) if m != player_id and m in universe.players]
    if corp is None or corp.ceo_id != player_id:
        drop_reason = "only the C.E.O. may drop a member"
    elif not members:
        drop_reason = "no member to drop"
    else:
        drop_reason = None
    out.append(_la(ActionKind.CORP_DROP, legal=drop_reason is None, reason=drop_reason,
                   params={"target": {"type": "str", "required": True, "choices": [m["player_id"] for m in members]},
                           "members": members}))
    partners = []
    if corp is not None:
        for mid in corp.member_ids:
            if mid == player_id:
                continue
            other = universe.players.get(mid)
            if other is None or not other.alive or other.sector_id != player.sector_id:
                continue
            if other.planet_landed is not None or player.planet_landed is not None:
                continue
            if K.hardware_tw2002() and getattr(other.ship, "cloaked", False):
                continue
            items = ("credits", "fighters", "shields", "armid_mines", "limpet_mines")
            partners.append({
                "player_id": mid, "name": other.name,
                "give_room": {item: _ship_room(other.ship, item) for item in items},
                "take_max": {item: (_ship_have(other.ship, item) if item != "credits" else int(other.credits))
                             for item in items},
            })
    if not in_corp:
        xfer_reason = "not in a corporation"
    elif not partners:
        xfer_reason = "no corp mate here in a ship"
    else:
        xfer_reason = None
    out.append(_la(ActionKind.CORP_TRANSFER, legal=xfer_reason is None, reason=xfer_reason,
                   params={"target": {"type": "str", "required": True, "choices": [p["player_id"] for p in partners]},
                           "item": {"type": "str", "required": True,
                                    "choices": ["credits", "fighters", "shields", "armid_mines", "limpet_mines"]},
                           "qty": {"type": "int", "required": True, "min": 1},
                           "direction": {"type": "str", "required": True, "choices": ["give", "take"]},
                           "partners": partners}))
    memo_ok = in_corp and (K.CORP_MEMO_SENDERS == "member" or (corp and corp.ceo_id == player_id))
    memo_reason = None if memo_ok else ("not in a corporation" if not in_corp else "only the C.E.O. may send a memo")
    out.append(_la(ActionKind.CORP_MEMO, legal=memo_ok, reason=memo_reason,
                   params={"message": {"type": "str", "required": True, "max_len": 1000}}))
    out.append(_la(ActionKind.CORP_DEPOSIT, legal=False, reason="unsupported action",
                   params={"amount": {"type": "int", "required": True, "min": 1, "max": 0}}))
    out.append(_la(ActionKind.CORP_WITHDRAW, legal=False, reason="unsupported action",
                   params={"amount": {"type": "int", "required": True, "min": 1, "max": 0}}))
