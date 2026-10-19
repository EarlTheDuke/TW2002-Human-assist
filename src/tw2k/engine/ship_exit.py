"""Jettison and self-destruct. Off unless SHIP_EXIT_MODE is tw2002.

The cockpit keeps the "not in this game" lines while the switch is legacy, and
the verbs stay out of the legal list so the bank pin does not move.

Self-destruct follows the ship-destroyed path: half the experience and half
the alignment (halfway toward zero), and the ship is gone. d13 also keeps the
pilot out tomorrow, so the next day still has no turns. Halfway-to-zero
alignment is the ship-destroyed rule. It is confirmed for a good trader and
UNVERIFIED for a red one.

Jettison of colonists is the published rule: a good trader loses 1 alignment
each, and only 250 of those count in a day. Dumping other cargo into space,
with nothing left behind in the sector, is UNVERIFIED. There is no published
cargo-dump rule in this tree, so the goods are simply gone.
"""

from __future__ import annotations

from typing import Any

from . import constants as K
from .actions import Action, ActionResult
from .models import Commodity

_COLONIST_CAP = 250  # GAP_MAP 9.5: good traders only, max 250 a day


def jettison_spec(universe, pid: str) -> tuple[bool, str | None, int, dict[str, Any]]:
    player = universe.players[pid]
    if player.planet_landed is not None:
        return False, "lift off first", 0, {}
    choices: list[str] = []
    max_by: dict[str, int] = {}
    for key, qty in player.ship.cargo.items():
        name = getattr(key, "value", key)
        have = int(qty or 0)
        if str(name) == Commodity.COLONISTS.value and K.colonist_units_live() and int(K.colonists_per_hold()) > 1:
            per = int(K.colonists_per_hold())
            have = have - (have % per)
        if have > 0:
            choices.append(str(name))
            max_by[str(name)] = have
    if not choices:
        return False, "nothing to jettison", 0, {}
    params = {
        "commodity": {"type": "str", "required": True, "choices": choices},
        "qty": {"type": "int", "required": True, "min": 1, "max_by": max_by},
        "note": "colonists cost a good trader 1 alignment each, up to 250 a day",
    }
    return True, None, 0, params


def self_destruct_spec(universe, pid: str) -> tuple[bool, str | None, int, dict[str, Any]]:
    player = universe.players[pid]
    if not player.alive:
        return False, "you are already out", 0, {}
    return True, None, 0, {
        "note": "half your experience and half your alignment; out today and tomorrow",
    }


def _cargo_key(ship, name: str):
    for key in ship.cargo:
        if getattr(key, "value", key) == name:
            return key
    return None


def handle_jettison(universe, pid: str, action: Action) -> ActionResult:
    if not K.ship_exit_on():
        return ActionResult(ok=False, error="unsupported action")
    legal, why, _cost, _params = jettison_spec(universe, pid)
    if not legal:
        return ActionResult(ok=False, error=why or "nothing to jettison")
    player = universe.players[pid]
    raw = str((action.args or {}).get("commodity") or "")
    key = _cargo_key(player.ship, raw)
    if key is None:
        return ActionResult(ok=False, error="not enough of that cargo")
    try:
        qty = int((action.args or {}).get("qty"))
    except (TypeError, ValueError):
        return ActionResult(ok=False, error="qty must be a whole number")
    have = int(player.ship.cargo.get(key, 0) or 0)
    if qty < 1 or qty > have:
        return ActionResult(ok=False, error="not enough of that cargo")
    align_qty = qty
    if key == Commodity.COLONISTS or getattr(key, "value", key) == Commodity.COLONISTS.value:
        if K.colonist_units_live() and int(K.colonists_per_hold()) > 1:
            per = int(K.colonists_per_hold())
            if qty % per != 0:
                return ActionResult(ok=False, error=K.COLONIST_MOVE_BY_THOUSAND)
            align_qty = K.colonist_holds_for_cargo(qty)
    player.ship.cargo[key] = have - qty
    if key == Commodity.COLONISTS or getattr(key, "value", key) == Commodity.COLONISTS.value:
        _colonist_alignment(universe, player, align_qty)
    return ActionResult(ok=True, turns_spent=0)


def _colonist_alignment(universe, player, qty: int) -> None:
    """Good traders only. The loss stops at zero and at 250 for the day."""
    if int(player.alignment) <= 0 or qty <= 0:
        return
    if int(player.jettison_day) != int(universe.day):
        player.jettison_day = int(universe.day)
        player.jettison_colonists = 0
    room = max(0, _COLONIST_CAP - int(player.jettison_colonists))
    hit = 0
    while hit < qty and hit < room and int(player.alignment) > 0:
        player.alignment -= 1
        hit += 1
    player.jettison_colonists = int(player.jettison_colonists) + hit


def handle_self_destruct(universe, pid: str, action: Action) -> ActionResult:
    if not K.ship_exit_on():
        return ActionResult(ok=False, error="unsupported action")
    legal, why, _cost, _params = self_destruct_spec(universe, pid)
    if not legal:
        return ActionResult(ok=False, error=why or "you are already out")
    from .combat import _destroy_ship_tw2002

    _destroy_ship_tw2002(universe, pid, "self_destruct", None, False, force_destroyed=True)
    universe.players[pid].self_destruct_lock_day = int(universe.day) + 1
    return ActionResult(ok=True, turns_spent=0)
