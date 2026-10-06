"""Galactic Bank and the good-trader tax. docs/playtests/fedspace/GALACTIC_BANK_TAX.md."""

from __future__ import annotations

from typing import Any

from . import constants as K
from .actions import Action, ActionResult
from .models import EventKind, Player, Universe

_NO_TRADER = "no such trader"
_POD_SCOUT = frozenset({"escape_pod", "scout_marauder"})


def on() -> bool:
    return K.bank_on()


def _player(universe: Universe, pid: str) -> Player | None:
    return universe.players.get(pid)


def _alive(player: Player) -> bool:
    return bool(player.alive)


def guard(universe: Universe, player: Player) -> str | None:
    if not _alive(player):
        return "player is destroyed"
    if player.planet_landed is not None:
        return "lift off first"
    if player.sector_id != K.STARDOCK_SECTOR:
        return "the bank is at StarDock"
    return None


def room(player: Player) -> int:
    return max(0, int(K.BANK_MAX_BALANCE) - int(player.bank_balance))


def tax_on(player: Player, credits: int | None = None) -> tuple[int, int]:
    """Tax and alignment this cash would owe. (0, 0) when the trader is exempt."""
    cash = int(player.credits if credits is None else credits)
    if int(player.alignment) < int(K.TAX_MIN_ALIGNMENT) or cash <= int(K.TAX_THRESHOLD):
        return 0, 0
    if K.TAX_ROUNDING == "floor":
        tax = cash * int(K.TAX_RATE_PCT) // 100
    else:
        tax = round(cash * int(K.TAX_RATE_PCT) / 100)
    per = int(K.TAX_CREDITS_PER_ALIGN)
    award = tax // per if per else 0
    if award > int(K.TAX_ALIGN_AWARD_MAX) and K.TAX_ALIGN_OVERFLOW == "none":
        award = 0
    elif award > int(K.TAX_ALIGN_AWARD_MAX):
        award = int(K.TAX_ALIGN_AWARD_MAX)
    return tax, award


def _amount(raw: Any) -> int | None:
    if isinstance(raw, bool):
        return None
    try:
        amount = int(raw)
    except (TypeError, ValueError):
        return None
    return amount


def _refuse(maximum: int) -> ActionResult:
    return ActionResult(ok=False, error=f"the bank can accept {maximum:,} more")


def deposit_legal_spec(universe: Universe, pid: str) -> tuple[bool, str | None, int, dict[str, Any]]:
    if not on() or pid not in universe.players:
        return False, "unsupported action", 0, {}
    player = universe.players[pid]
    why = guard(universe, player)
    maximum = min(int(player.credits), room(player))
    params = {"max_amount": maximum, "balance": int(player.bank_balance), "room": room(player),
              "capacity": int(K.BANK_MAX_BALANCE)}
    if why is None and maximum < 1:
        # VERBS section (QC 56): say which side is empty
        why = "no credits on hand" if int(player.credits) < 1 else "account full"
    return why is None, why, 0, params


def withdraw_legal_spec(universe: Universe, pid: str) -> tuple[bool, str | None, int, dict[str, Any]]:
    if not on() or pid not in universe.players:
        return False, "unsupported action", 0, {}
    player = universe.players[pid]
    why = guard(universe, player)
    maximum = int(player.bank_balance)
    params = {"max_amount": maximum, "balance": maximum}
    if why is None and maximum < 1:
        why = "nothing in the account"
    return why is None, why, 0, params


def _recipients(universe: Universe, player: Player) -> list[dict[str, Any]]:
    rows = []
    for other_id in sorted(universe.players):
        other = universe.players[other_id]
        if other_id == player.id or not _alive(other):
            continue
        if not K.BANK_TRANSFER_CORPMATES and player.corp_ticker and other.corp_ticker == player.corp_ticker:
            continue
        their_room = room(other)
        row = {
            "player_id": other_id,
            "name": other.name,
            "max_amount": min(int(player.credits), their_room) if K.BANK_TRANSFER_SOURCE == "cash"
            else min(int(player.bank_balance), their_room),
        }
        if K.BANK_SHOW_RECIPIENT_ROOM:
            row["room"] = their_room
        rows.append(row)
    return rows


def transfer_legal_spec(universe: Universe, pid: str) -> tuple[bool, str | None, int, dict[str, Any]]:
    if not on() or pid not in universe.players:
        return False, "unsupported action", 0, {}
    player = universe.players[pid]
    why = guard(universe, player)
    recipients = _recipients(universe, player)
    spendable = int(player.credits) if K.BANK_TRANSFER_SOURCE == "cash" else int(player.bank_balance)
    best = max((int(r["max_amount"]) for r in recipients), default=0)
    if not K.BANK_TRANSFER_RESPECTS_CAP:
        best = spendable if recipients else 0
    params = {"recipients": recipients, "max_amount": best}
    if why is None and not recipients:
        why = _NO_TRADER
    elif why is None and spendable < 1:
        why = "no credits on hand" if K.BANK_TRANSFER_SOURCE == "cash" else "nothing in the account"
    elif why is None and best < 1:
        why = "every account is full"  # QC 56: the handler refuses every recipient at room 0
    return why is None, why, 0, params


def handle_bank_deposit(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not on():
        return ActionResult(ok=False, error="unsupported action")
    player = universe.players[pid]
    why = guard(universe, player)
    if why:
        return ActionResult(ok=False, error=why)
    amount = _amount((action.args or {}).get("amount"))
    if amount is None or amount < 1:
        return ActionResult(ok=False, error="amount must be a whole number")
    maximum = min(int(player.credits), room(player))
    if amount > maximum:
        if K.BANK_OVERCAP == "clip":
            amount = maximum
        else:
            return _refuse(maximum)
    if amount < 1:
        return _refuse(0)
    player.credits -= amount
    player.bank_balance = int(player.bank_balance) + amount
    universe.emit(
        EventKind.BANK_DEPOSIT, actor_id=pid, sector_id=player.sector_id,
        payload={"amount": amount, "balance": int(player.bank_balance)},
        summary=f"{player.name} deposited {amount}cr",
    )
    return ActionResult(ok=True, turns_spent=int(K.BANK_TURN_COST) if K.BANK_TURN_COST else 0)


def handle_bank_withdraw(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not on():
        return ActionResult(ok=False, error="unsupported action")
    player = universe.players[pid]
    why = guard(universe, player)
    if why:
        return ActionResult(ok=False, error=why)
    amount = _amount((action.args or {}).get("amount"))
    if amount is None or amount < 1:
        return ActionResult(ok=False, error="amount must be a whole number")
    if amount > int(player.bank_balance):
        return ActionResult(ok=False, error=f"at most {int(player.bank_balance)} credits")
    player.bank_balance = int(player.bank_balance) - amount
    player.credits += amount
    universe.emit(
        EventKind.BANK_WITHDRAW, actor_id=pid, sector_id=player.sector_id,
        payload={"amount": amount, "balance": int(player.bank_balance)},
        summary=f"{player.name} withdrew {amount}cr",
    )
    return ActionResult(ok=True, turns_spent=int(K.BANK_TURN_COST) if K.BANK_TURN_COST else 0)


def handle_bank_transfer(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not on():
        return ActionResult(ok=False, error="unsupported action")
    player = universe.players[pid]
    why = guard(universe, player)
    if why:
        return ActionResult(ok=False, error=why)
    target_id = str((action.args or {}).get("to_player") or "")
    other = universe.players.get(target_id)
    if other is None or other.id == player.id or not _alive(other):
        return ActionResult(ok=False, error=_NO_TRADER)
    if not K.BANK_TRANSFER_CORPMATES and player.corp_ticker and other.corp_ticker == player.corp_ticker:
        return ActionResult(ok=False, error=_NO_TRADER)
    amount = _amount((action.args or {}).get("amount"))
    if amount is None or amount < 1:
        return ActionResult(ok=False, error="amount must be a whole number")
    their_room = room(other)
    if K.BANK_TRANSFER_RESPECTS_CAP and amount > their_room:
        return _refuse(their_room)
    if K.BANK_TRANSFER_SOURCE == "account":
        if amount > int(player.bank_balance):
            return ActionResult(ok=False, error=f"at most {int(player.bank_balance)} credits")
        player.bank_balance = int(player.bank_balance) - amount
    else:
        if amount > int(player.credits):
            return _refuse(min(int(player.credits), their_room))
        player.credits -= amount
    other.bank_balance = int(other.bank_balance) + amount
    universe.emit(
        EventKind.BANK_TRANSFER, actor_id=pid, sector_id=player.sector_id,
        payload={"to_player": target_id, "amount": amount, "balance": int(player.bank_balance)},
        summary=f"{player.name} transferred {amount}cr",
    )
    universe.emit(
        EventKind.BANK_TRANSFER_RECEIVED, actor_id=target_id, sector_id=other.sector_id,
        payload={"from_player": pid, "from_name": player.name, "amount": amount,
                 "balance": int(other.bank_balance)},
        summary=f"{player.name} put {amount}cr in your account",
    )
    return ActionResult(ok=True, turns_spent=int(K.BANK_TURN_COST) if K.BANK_TURN_COST else 0)


def collect_daily_tax(universe: Universe) -> None:
    """gb23: last step of the day tick. Day 1 never reaches here."""
    if not on() or K.TAX_WHEN != "day_tick":
        return
    for pid in sorted(universe.players):
        player = universe.players[pid]
        if not _alive(player):
            continue
        tax, award = tax_on(player)
        if tax <= 0:
            continue
        before = int(player.credits)
        taken = min(tax, before)
        if K.TAX_TO == "sink":
            player.credits = before - taken
        player.alignment = int(player.alignment) + award
        if int(K.TAX_EXP):
            player.experience = int(player.experience) + int(K.TAX_EXP)
        universe.emit(
            EventKind.TAX_COLLECTED, actor_id=pid, sector_id=player.sector_id,
            payload={"credits_before": before, "tax": taken, "align_gain": award,
                     "new_alignment": int(player.alignment)},
            summary=f"The Federation collected {taken} credits in taxes (+{award} alignment)",
        )


def on_ship_lost(universe: Universe, player: Player, killer_id: str | None, by_other: bool, hull: str) -> int:
    """gb13-gb14. No-op unless the bank and the lost-cash rule are both on. Returns credits removed."""
    if not on() or K.DEATH_CREDITS_ON_HAND != "lost":
        return 0
    lost = int(player.credits)
    if lost <= 0:
        return 0
    player.credits = 0
    recovered = 0
    real_hull = hull not in _POD_SCOUT
    killer = universe.players.get(str(killer_id or ""))
    if by_other and real_hull and K.DEATH_CREDITS_TO_KILLER == "player_ship_kill" and killer is not None:
        recovered = lost * int(K.DEATH_CREDITS_RECOVER_PCT) // 100
        killer.credits = int(killer.credits) + recovered
        universe.emit(
            EventKind.CREDITS_RECOVERED, actor_id=killer.id, sector_id=killer.sector_id,
            payload={"from_player": player.id, "credits_recovered": recovered},
            summary=f"Recovered {recovered}cr",
        )
    elif by_other and real_hull and killer is None and K.DEATH_CREDITS_FERRENGI == "to_ferrengi":
        ship = (getattr(universe, "ferrengi", None) or {}).get(killer_id)
        if ship is not None and hasattr(ship, "credits"):
            ship.credits = int(ship.credits) + lost
            recovered = lost
    return lost


def self_view(player: Player) -> dict[str, int]:
    tax, _award = tax_on(player)
    return {
        "bank_balance": int(player.bank_balance),
        "bank_room": room(player),
        "tax_due_tomorrow": tax,
    }
