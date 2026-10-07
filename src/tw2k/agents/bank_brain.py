"""Purse math for the bank bots. Pure functions. No universe, no random draw.

Every number is read from K at call time.
"""

from __future__ import annotations

from ..engine import constants as K


def nest_egg(net_worth: int) -> int:
    """The staged balance a seat keeps. The highest stage at or under net worth."""
    kept = 0
    for floor, amount in K.BOT_BANK_NEST_EGG_STAGES:
        if int(net_worth) >= int(floor):
            kept = int(amount)
    return kept


def purse(credits: int, balance: int, egg: int, withdraw_max: int) -> int:
    """Cash a StarDock buy may spend: on hand plus the bank, minus the nest egg.

    Never more than the cash plus what a withdraw is allowed to take right now.
    """
    on_hand = max(0, int(credits))
    banked = max(0, int(balance))
    kept = max(0, int(egg))
    legal = max(0, int(withdraw_max))
    return max(0, min(on_hand + banked - kept, on_hand + legal))


def trade_capital(holds: int) -> int:
    """The cash a seat keeps for the next trade loop."""
    per_hold = max(0, int(holds)) * int(K.BOT_BANK_CAPITAL_PER_HOLD)
    return max(int(K.BOT_BANK_MIN_FLOAT), per_hold)


def away_reserve(holds: int, planned: list[int], flags: int, owns_fighters: bool) -> int:
    """Cash carried out of StarDock.

    `planned` is each off-dock purchase, in credits. `flags` is how many risk
    flags are on. Each one halves the cap, and the cap never falls below the
    trade capital plus the single largest planned purchase. A purchase bigger
    than the cap is carried whole, with the trade capital.
    """
    trade = trade_capital(holds)
    amounts = [max(0, int(item)) for item in planned]
    if not owns_fighters:
        amounts.append(int(K.BOT_BANK_TOLL_BUDGET))
    biggest = max(amounts) if amounts else 0
    floor = trade + biggest
    cap = int(K.BOT_BANK_AWAY_CAP)
    for _ in range(max(0, int(flags))):
        cap = max(floor, cap // 2)
    if biggest + trade > int(K.BOT_BANK_AWAY_CAP):
        return floor
    return min(trade + sum(amounts), max(cap, floor) if int(flags) else cap)


def withdraw_amount(
    cost: int, keep: int, credits: int, balance: int, egg: int, withdraw_max: int, *, recovery: bool,
) -> int:
    """The exact shortfall. A normal buy does not spend the nest egg. Recovery may."""
    shortfall = int(cost) + int(keep) - int(credits)
    if shortfall < 1:
        return 0
    protected = 0 if recovery else max(0, int(egg))
    room = max(0, int(balance) - protected)
    legal = max(0, int(withdraw_max))
    return max(0, min(shortfall, room, legal))


def risk_flags(
    *, days_since_loss: int | None, ship_class: str, alignment: int, fedsafe: bool,
    threat_hops: int | None, fighters: int,
) -> int:
    """How many death-risk flags are on. Each one halves the away cap.

    A recent loss, a podless hull, not being FedSafe, a threat within a few hops,
    and a thin fighter load each count once. The inputs are the seat's own.
    """
    count = 0
    if days_since_loss is not None and 0 <= int(days_since_loss) <= int(K.BOT_BANK_RISK_DAYS):
        count += 1
    if str(ship_class or "") in set(K.PODLESS_HULLS):
        count += 1
    if (not fedsafe) or int(alignment) < int(K.FEDSAFE_MIN_ALIGNMENT):
        count += 1
    if threat_hops is not None and int(threat_hops) <= int(K.BOT_BANK_RISK_HOPS):
        count += 1
    if int(fighters) < int(K.BOT_BANK_RISK_FIGHTERS):
        count += 1
    return count


def tax_keep(reserve: int, planned_max: int, alignment: int) -> int:
    """Good seats leave at most the tax line, unless one planned buy needs more.

    Evil seats are never taxed, so they keep the whole reserve.
    """
    if int(alignment) < int(K.TAX_MIN_ALIGNMENT):
        return int(reserve)
    line = int(K.TAX_THRESHOLD)
    if int(planned_max) > line:
        return int(reserve)
    return min(int(reserve), line)


def deposit_amount(credits: int, reserve: int, deposit_max: int, *, day1: bool) -> int:
    """Spare above the away reserve. Day 1 deposits at most the first nest stage,
    and only when that still leaves the reserve on the ship."""
    spare = int(credits) - int(reserve)
    if day1:
        cap = int(K.BOT_BANK_DAY1_DEPOSIT)
        if int(credits) - cap < int(reserve):
            return 0
        spare = min(spare, cap)
    legal = max(0, int(deposit_max))
    if spare < 1 or legal < 1:
        return 0
    return min(spare, legal)
