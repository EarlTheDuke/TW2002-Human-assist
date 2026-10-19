"""Code-bot ship upgrade, Ferrengi hold recovery, and dead-end escape (NOTE 92).

Bot policy only. Each decision returns None while its switch is off, so a
profile-off turn keeps the old action. The yard's net cost is whatever
``buy_ship`` already published, including TRADE_IN_PARTS_MODE when that switch
is on. This module never sells fighters to raise the cash.
"""

from __future__ import annotations

from typing import Any

from tw2k.engine.constants import (
    BOTS_ESCAPE_WINDOW,
    BOTS_HOLD_FLOOR,
    BOTS_WORKING_FLOAT,
    STARDOCK_SECTOR,
    bots_escape_live,
    bots_ferrengi_recovery_live,
    bots_upgrade_live,
    hold_total_price,
    holds_affordable,
    hull_spec,
    plot_course_hop_limit,
)

# Cargo hulls a trader steps up through. Combat hulls stay on their own ladder.
_TRADING_HULLS = (
    "merchant_cruiser",
    "merchant_freighter",
    "cargotran",
    "colonial_transport",
)


def _legal(legal_actions: list | None) -> dict[str, dict]:
    return {str(la.get("kind")): la for la in (legal_actions or []) if isinstance(la, dict)}


def _ok(legal: dict, kind: str) -> bool:
    return bool((legal.get(kind) or {}).get("legal"))


def _course_target(universe: Any, here: int, goal: int) -> int:
    """A plot target on the shortest course to ``goal`` that the hop limit accepts.

    A course longer than ``plot_course_hop_limit`` is refused whole, so a bot
    in a far pocket would repeat that refusal and never leave. The waypoint is
    the furthest sector on that course the limit still allows.
    """
    if universe is None or int(here) == int(goal):
        return int(goal)
    from tw2k.engine.runner import _bfs_path

    limit = int(plot_course_hop_limit())
    path = _bfs_path(
        universe, int(here), int(goal), max_depth=max(limit, len(universe.sectors)),
    )
    if not path or len(path) <= limit:
        return int(goal)
    return int(path[limit - 1])


def ferrengi_loss_sectors(events: list | None, day: int | None, me: str | None) -> set[int]:
    """Sectors where Ferrengi took holds from this ship today or yesterday.

    Same window the hazard memory uses (today and the day before). Empty when
    the recovery switch is off.
    """
    if not bots_ferrengi_recovery_live():
        return set()
    bad: set[int] = set()
    for ev in events or []:
        if not isinstance(ev, dict):
            continue
        ev_day = ev.get("day")
        if day is not None and ev_day is not None and int(ev_day) < int(day) - 1:
            continue
        kind = str(ev.get("kind") or "")
        if kind not in ("ferrengi_tribute", "ferrengi_encounter"):
            continue
        facts = ev.get("facts") or {}
        actor = ev.get("actor_id")
        victim = facts.get("victim") or actor
        if me and victim not in (me, None) and actor != me:
            continue
        if kind == "ferrengi_tribute" and int(facts.get("holds_stolen") or 0) <= 0:
            continue
        sector = ev.get("sector_id")
        if sector is None:
            sector = facts.get("sector")
        if sector is not None:
            bad.add(int(sector))
    return bad


def _hold_qty(class_key: str, holds: int, cap: int, credits: int, day: int) -> int:
    room = max(0, int(cap) - int(holds))
    if room <= 0 or int(credits) <= 0:
        return 0
    return int(holds_affordable(class_key, holds, credits, day, room))


def dock_step(
    *,
    here: int | None,
    class_key: str,
    holds: int,
    max_holds: int,
    fighters: int,
    credits: int,
    day: int,
    legal_actions: list | None,
) -> dict[str, Any] | None:
    """Buy holds up to the hull cap, then a bigger trading hull. None when off.

    Recovery below the floor spends the purse to climb back to the floor.
    An upgrade above that keeps ``BOTS_WORKING_FLOAT`` aboard. Fighters are
    never sold to pay for either.
    """
    upgrade = bots_upgrade_live()
    recover = bots_ferrengi_recovery_live()
    if not upgrade and not recover:
        return None
    if here is None or int(here) != int(STARDOCK_SECTOR):
        return None
    legal = _legal(legal_actions)
    buy = legal.get("buy_equip") or {}
    items = ((buy.get("params") or {}).get("item") or {})
    choices = {str(c) for c in (items.get("choices") or [])}
    hold_cap = int((items.get("max_by") or {}).get("holds") or 0)
    spec = hull_spec(str(class_key or "")) or {}
    cap = int(max_holds or spec.get("max_holds") or holds)
    if hold_cap > 0:
        cap = min(cap, int(holds) + hold_cap)
    if recover and int(holds) < int(BOTS_HOLD_FLOOR) and buy.get("legal") and "holds" in choices:
        qty = _hold_qty(class_key, holds, min(cap, int(BOTS_HOLD_FLOOR)), credits, day)
        if qty <= 0:
            qty = _hold_qty(class_key, holds, cap, credits, day)
        if qty > 0:
            return {
                "kind": "buy_equip",
                "args": {"item": "holds", "qty": int(qty)},
                "thought": f"rebuy {qty} holds after the loss (floor {BOTS_HOLD_FLOOR})",
            }
    if not upgrade:
        return None
    spare = int(credits) - int(BOTS_WORKING_FLOAT)
    if buy.get("legal") and "holds" in choices and int(holds) < cap and spare > 0:
        qty = _hold_qty(class_key, holds, cap, spare, day)
        if qty > 0 and hold_total_price(class_key, holds, qty, day) <= spare:
            return {
                "kind": "buy_equip",
                "args": {"item": "holds", "qty": int(qty)},
                "thought": f"buy {qty} holds, keeping a {BOTS_WORKING_FLOAT} float",
            }
    if int(holds) < cap:
        return None
    ship = legal.get("buy_ship") or {}
    if not ship.get("legal"):
        return None
    spec_ship = (ship.get("params") or {}).get("ship_class") or {}
    offered = {str(c) for c in (spec_ship.get("choices") or [])}
    blocked = spec_ship.get("blocked_by") or {}
    nets = spec_ship.get("net_cost_by") or {}
    current_max = int((hull_spec(str(class_key or "")) or {}).get("max_holds") or holds)
    best: str | None = None
    best_holds = current_max
    best_cost = 0
    for key in _TRADING_HULLS:
        if key not in offered or key == class_key or key in blocked:
            continue
        mx = int((hull_spec(key) or {}).get("max_holds") or 0)
        if mx <= best_holds:
            continue
        cost = nets.get(key)
        if cost is None:
            continue
        # Credits on the ship only. Do not sell the fighter stack to make up a shortfall.
        if int(fighters) > 0 and int(credits) < int(cost):
            continue
        if int(credits) - int(cost) < int(BOTS_WORKING_FLOAT):
            continue
        best, best_holds, best_cost = key, mx, int(cost)
    if best is None:
        return None
    return {
        "kind": "buy_ship",
        "args": {"ship_class": best},
        "thought": (
            f"trade up to {best} ({best_cost} cr net, yard trade-in) "
            f"and keep the fighters off the bill"
        ),
    }


def recovery_course(
    *,
    here: int | None,
    holds: int,
    plot_legal: bool,
    warp_legal: bool,
    home: int | None = None,
    universe: Any = None,
) -> dict[str, Any] | None:
    """Plot to StarDock (or home) when holds are under the floor. None when off."""
    if not bots_ferrengi_recovery_live():
        return None
    if here is None or int(holds) >= int(BOTS_HOLD_FLOOR):
        return None
    if int(here) == int(STARDOCK_SECTOR):
        return None
    # plot_legal means the first hop can be paid. A dead end has no warp target;
    # the course is still the way out, so a false warp_legal does not block it.
    if not plot_legal or warp_legal is None:
        return None
    target = _course_target(universe, int(here), int(STARDOCK_SECTOR))
    why = "holds under the floor; StarDock to rebuy"
    if home is not None and int(home) != int(here) and int(home) != int(STARDOCK_SECTOR):
        # Home is the fallback the note allows. Holds are sold at StarDock, so that comes first.
        why = "holds under the floor; StarDock to rebuy (home is the other heading)"
    return {
        "kind": "plot_course",
        "args": {"target": target, "execute": True},
        "thought": why,
    }


def escape_course(
    *,
    here: int | None,
    adjacent_ids: list[int],
    last_from: int | None,
    trail: list[tuple[int, bool]],
    plot_legal: bool,
    warp_legal: bool,
    universe: Any = None,
) -> dict[str, Any] | None:
    """Shortest legal course to StarDock out of a dead end, a one-way, or a 20-action loop.

    ``trail`` entries are ``(sector, traded)`` for the decisions already taken.
    A two-port trade run has trades in the window, so it is not a dead-end loop.
    """
    if not bots_escape_live():
        return None
    if here is None or int(here) == int(STARDOCK_SECTOR):
        return None
    # plot_legal means the first hop can be paid. Out of turns, this stays None
    # so the bot waits instead of repeating a rejected course. warp_legal does
    # not block a dead end (no local target).
    if not plot_legal or warp_legal is None:
        return None
    ids = [int(a) for a in adjacent_ids]
    dead = len(ids) == 0
    recent_sectors = [int(s) for s, _traded in trail[-int(BOTS_ESCAPE_WINDOW):]]
    fresh = [a for a in ids if a not in set(recent_sectors)]
    one_way = (
        last_from is not None
        and int(last_from) != int(here)
        and int(last_from) not in ids
        and not fresh
    )
    # Plot out before a 20-action pocket is on the log. Eight quiet actions in
    # one or two sectors is enough to call it a trap; a two-port trade still
    # has a trade in that span and is left alone.
    lead = min(8, int(BOTS_ESCAPE_WINDOW))
    window = trail[-lead:]
    looping = (
        len(window) >= lead
        and not any(traded for _s, traded in window)
        and len({int(s) for s, _t in window}) <= 2
    )
    if not (dead or one_way or looping):
        return None
    target = _course_target(universe, int(here), int(STARDOCK_SECTOR))
    return {
        "kind": "plot_course",
        "args": {"target": int(target), "execute": True},
        "thought": "dead end or one-way; shortest course out toward StarDock",
    }


def steer_off_loss(action: dict[str, Any], bad: set[int], legal_warps: list[int]) -> dict[str, Any]:
    """If this warp or plot aims at a Ferrengi-loss sector, take another exit."""
    if not bad or not isinstance(action, dict):
        return action
    kind = str(action.get("kind") or "")
    if kind not in ("warp", "plot_course"):
        return action
    try:
        target = int((action.get("args") or {}).get("target"))
    except (TypeError, ValueError):
        return action
    if target not in bad:
        return action
    for hop in legal_warps:
        if int(hop) not in bad:
            steered = dict(action)
            steered["kind"] = "warp"
            steered["args"] = {"target": int(hop)}
            steered["thought"] = f"avoid sector {target}; Ferrengi took holds there"
            return steered
    if int(STARDOCK_SECTOR) not in bad:
        return {
            "kind": "plot_course",
            "args": {"target": int(STARDOCK_SECTOR), "execute": True},
            "thought": f"avoid sector {target}; plot to StarDock",
        }
    return action
