"""Pure corp-bot pairing. No universe.rng and no other seat's memory.

The match runner calls configure() before day 1. Until then the table is empty
and SeatBrain keeps the older one-pair match-check path.
"""

from __future__ import annotations

import hashlib
from typing import Any

from ..engine import constants as K

_SEED = 0
_PARTNER: dict[str, str] = {}
_ROLE: dict[str, str] = {}


def active() -> bool:
    return bool(_PARTNER)


def clear() -> None:
    global _SEED
    _SEED = 0
    _PARTNER.clear()
    _ROLE.clear()


def _seat_ord(seat_id: str) -> tuple[int, str]:
    digits = "".join(ch for ch in seat_id if ch.isdigit())
    return (int(digits) if digits else 0, seat_id)


def configure(seat_ids: list[str], seed: int, explicit: list[tuple[str, str]] | None = None) -> None:
    """Install pairs. Explicit pairs win. Otherwise consecutive seats, lower id is C.E.O."""
    clear()
    global _SEED
    _SEED = int(seed)
    pairs = list(explicit) if explicit is not None else _consecutive(list(seat_ids))
    for left, right in pairs:
        ceo, mate = sorted((str(left), str(right)), key=_seat_ord)
        _PARTNER[ceo] = mate
        _PARTNER[mate] = ceo
        _ROLE[ceo] = "ceo"
        _ROLE[mate] = "mate"


def _consecutive(seat_ids: list[str]) -> list[tuple[str, str]]:
    ids = [str(s) for s in seat_ids]
    return [(ids[i], ids[i + 1]) for i in range(0, len(ids) - 1, 2)]


def partner_of(seat_id: str) -> str | None:
    return _PARTNER.get(str(seat_id))


def role_of(seat_id: str) -> str | None:
    return _ROLE.get(str(seat_id))


def ticker_for(name: str, seat_id: str, taken: set[str]) -> str | None:
    """bc3: first 3 alphanumerics of the name, else a letter and two digits from the seat id."""
    alnum = "".join(ch for ch in str(name).upper() if ch.isalnum())
    primary = alnum[:3]
    if len(primary) == 3 and primary not in taken:
        return primary
    letters = "".join(ch for ch in str(seat_id).upper() if ch.isalpha()) or "C"
    digits = "".join(ch for ch in str(seat_id) if ch.isdigit()) or "0"
    start = int(digits)
    for step in range(100):
        cand = f"{letters[0]}{(start + step) % 100:02d}"
        if cand not in taken:
            return cand
    return None


def password_for(ticker: str, seed: int | None = None) -> str:
    """bc4: 6 hex chars. The caller must not store this on SeatMemory."""
    used = _SEED if seed is None else int(seed)
    digest = hashlib.sha256(f"{used}:{ticker}:corp".encode()).hexdigest()
    width = int(K.BOT_CORP_PASSWORD_LEN)
    return digest[:width]


def credit_give(giver_credits: int, giver_need: int, receiver_credits: int, receiver_need: int, *,
                reserve: int, pad: int, minimum: int) -> int | None:
    """bc12: the richer hands over the shortfall plus pad. Affordable-alone stays under the minimum."""
    if int(receiver_need) <= 0:
        return None
    short = max(0, int(receiver_need) - int(receiver_credits)) + int(pad)
    surplus = int(giver_credits) - int(giver_need) - int(reserve)
    if short < int(minimum) or surplus < short:
        return None
    return short


def tax_give(credits: int, threshold: int, *, minimum: int) -> int | None:
    """bc13: a good trader hands the cash above the tax line to an evil mate."""
    excess = int(credits) - int(threshold)
    if excess < int(minimum):
        return None
    return excess


def gear_take(mate_have: int, my_room: int, keep_pct: int) -> int | None:
    """bc14: take spare fighters or shields. The giver keeps at least keep_pct percent."""
    have = int(mate_have)
    room = int(my_room)
    if have < 1 or room < 1:
        return None
    keep = (have * int(keep_pct) + 99) // 100
    qty = min(have - keep, room)
    return qty if qty >= 1 else None


def friends(view: Any) -> set[str]:
    """bc9: corp mates from this seat's own corp block."""
    corp = view.obs.get("corp") or {}
    me = str(view.self_id or "")
    return {str(m.get("id")) for m in (corp.get("members") or [])
            if isinstance(m, dict) and m.get("id") and str(m.get("id")) != me}


def next_action(brain: Any, view: Any) -> dict[str, Any] | None:
    """Create, set the password, invite the partner, or join. One 0-turn verb."""
    me = str(view.self_id or "")
    if me not in _PARTNER or K.bot_corp_policy() != "pair":
        return None
    state = _state(brain)
    if int(getattr(state, "corp_free_day", -1)) != int(view.day):
        state.corp_free_day = int(view.day)
        state.corp_free_actions = 0
    if int(getattr(state, "corp_free_actions", 0)) >= int(K.BOT_CORP_MAX_FREE_ACTIONS_PER_DAY):
        return None
    action = _ceo(view, state) if _ROLE.get(me) == "ceo" else _mate(view)
    if action is not None:
        state.corp_free_actions = int(getattr(state, "corp_free_actions", 0)) + 1
        state.corp_partner = _PARTNER[me]
        state.corp_role = _ROLE[me]
    return action


def _state(brain: Any) -> Any:
    mem = getattr(brain, "mem", None)
    if mem is not None:
        return mem
    holder = getattr(brain, "_corp_state", None)
    if holder is None:
        holder = brain._corp_state = _Loose()
    return holder


class _Loose:
    corp_free_day = -1
    corp_free_actions = 0
    corp_partner = None
    corp_role = None
    corp_invites = 0
    corp_invite_day = -1


def _act(kind: str, args: dict[str, Any], thought: str) -> dict[str, Any]:
    return {"kind": kind, "args": args, "thought": thought}


def _ceo(view: Any, state: Any) -> dict[str, Any] | None:
    me = str(view.self_id or "")
    partner = _PARTNER[me]
    mine = view.obs.get("corp_ticker")
    if not mine:
        if int(view.day) > 1 or not view.ok("corp_create"):
            return None
        taken = set((view.params("corp_create").get("ticker") or {}).get("taken") or ())
        ticker = ticker_for(str(view.obs.get("self_name") or me), me, taken)
        if not ticker:
            return None
        return _act("corp_create", {"ticker": ticker, "name": str(view.obs.get("self_name") or ticker)},
                    "pair: found the corp")
    corp = view.obs.get("corp") or {}
    if not corp.get("password") and view.ok("corp_set_password"):
        return _act("corp_set_password", {"password": password_for(str(mine))}, "pair: set the corporate password")
    members = {str(m.get("id")) for m in (corp.get("members") or []) if isinstance(m, dict)}
    if partner in members:
        return None
    if int(getattr(state, "corp_invites", 0)) >= int(K.BOT_CORP_INVITE_RETRIES):
        return None
    if int(getattr(state, "corp_invite_day", -1)) == int(view.day):
        return None
    if view.ok("corp_invite") and partner in set(map(str, view.choices("corp_invite", "target"))):
        state.corp_invites = int(getattr(state, "corp_invites", 0)) + 1
        state.corp_invite_day = int(view.day)
        return _act("corp_invite", {"target": partner}, "pair: invite my partner")
    return None


def _mate(view: Any) -> dict[str, Any] | None:
    if view.obs.get("corp_ticker") or not view.ok("corp_join"):
        return None
    if K.BOT_CORP_ACCEPT_INVITES != "partner_only":
        return None
    partner = _PARTNER[str(view.self_id or "")]
    invites = [m for m in (view.obs.get("inbox") or []) if isinstance(m, dict)
               and m.get("kind") == "corp_invite" and str(m.get("from") or "") == partner and m.get("password")]
    if not invites:
        return None
    latest = invites[-1]
    ticker = str(latest.get("ticker") or "")
    if ticker not in set(map(str, view.choices("corp_join", "ticker"))):
        return None
    return _act("corp_join", {"ticker": ticker, "password": str(latest.get("password"))},
                "pair: join with the pass")


def skip_survey(view: Any) -> bool:
    """bc16: the partner trades once StarDock is known, while the C.E.O. is still in the corp."""
    me = str(view.self_id or "")
    if not active() or K.bot_corp_policy() == "off" or K.BOT_CORP_EXPLORER != "ceo":
        return False
    if role_of(me) != "mate" or not getattr(view, "stardock_known", False):
        return False
    return partner_of(me) in friends(view)


def credit_gift(shortfall: int, giver_credits: int, giver_keep: int) -> int | None:
    """bc12: the shortfall plus the pad, once, and only when the giver can spare it."""
    qty = int(shortfall) + int(K.BOT_CORP_TRANSFER_PAD)
    if int(shortfall) <= 0 or qty < int(K.BOT_CORP_MIN_TRANSFER):
        return None
    surplus = int(giver_credits) - int(giver_keep)
    if surplus < qty:
        return None
    return qty


def fighter_take(giver_have: int, receiver_room: int) -> int:
    """bc14: the receiver's room, and the giver keeps 30 percent. Never negative."""
    return gear_take(giver_have, receiver_room, int(K.BOT_CORP_KEEP_FIGHTERS_PCT)) or 0


def next_hull(current: str) -> str | None:
    costs = K.SHIP_COST_TW2002
    cur = int(costs.get(current) or 0)
    higher = [(cost, key) for key, cost in costs.items()
              if key != "corporate_flagship" and cost > cur]
    if not higher:
        return None
    higher.sort()
    return higher[0][1]
