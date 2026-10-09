"""When a seat may lay mines and defensive fighters. No engine calls."""

from __future__ import annotations


def seat_may_deploy(skill: str) -> bool:
    """N2 and N3. N1 and H stay out of this slice."""
    return skill in ("N2", "N3")


def mine_spend_ok(*, spent: int, cost: int, profit: int, pct: int) -> bool:
    """This buy keeps mine spend at or under pct% of trading profit so far."""
    if int(profit) <= 0:
        return int(spent) + int(cost) <= 0
    return (int(spent) + int(cost)) * 100 <= int(profit) * int(pct)


def lay_due(*, last_day: int, day: int, gap_days: int) -> bool:
    if last_day >= 0 and int(day) - int(last_day) < int(gap_days):
        return False
    return True
