"""When a seat may spend at the Lost Trader's Tavern. No engine calls."""

from __future__ import annotations


def seat_may_use(skill: str) -> bool:
    """N2, N3, and H. N1 stays out."""
    return skill in ("N2", "N3", "H")


def trace_due(
    *,
    hunting: bool,
    picking_lane: bool,
    credits: int,
    cost: int,
    reserve: int,
    last_day: int,
    day: int,
    gap_days: int,
) -> bool:
    """A trace only while hunting or choosing a lane, and not often enough to matter."""
    if not (hunting or picking_lane):
        return False
    if last_day >= 0 and int(day) - int(last_day) < int(gap_days):
        return False
    if int(credits) - int(cost) < int(reserve):
        return False
    return True


def visit_due(*, hunting: bool, picking_lane: bool, last_day: int, day: int, gap_days: int) -> bool:
    """Time for a tavern visit. A visit can be a free word when a trace would be too large."""
    if not (hunting or picking_lane):
        return False
    if last_day >= 0 and int(day) - int(last_day) < int(gap_days):
        return False
    return True


def trace_fits_income(*, cost: int, spent: int, profit: int) -> bool:
    """This buy keeps tavern spend strictly under 2% of trading profit so far."""
    if int(profit) <= 0:
        return False
    return (int(spent) + int(cost)) * 100 < int(profit) * 2


def join_underground(*, alignment: int, credits: int, password_price: int, already: bool) -> bool:
    """Evil, and more than twice the password price still in hand. A known password is not bought again."""
    if already or int(alignment) >= 0:
        return False
    return int(credits) > 2 * int(password_price)
