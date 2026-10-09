"""Tri-Cron, the Lost Trader's Tavern game. No engine calls.

Live TWGS screen (transcript): ante 100, 10 rounds, payback 2 to 1, jackpot
starts at 5,000, champion score 5,000. Each round deals three crons (0-9).
The player assigns them in the Grimy order 2-3-1 (tens, ones, hundreds),
which the original Bible names as the best combination. The house uses the
same order. The fee is added to the jackpot before the match is scored.
"""

from __future__ import annotations

import random
from typing import Sequence

PLACE_231 = (2, 3, 1)
ROUNDS = 10
ANTE = 100
PAYBACK_NUMERATOR = 2
OPENING_JACKPOT = 5_000
OPENING_CHAMPION = 5_000


def number_from(crons: Sequence[int], order: Sequence[int] = PLACE_231) -> int:
    """Build the three-digit number by placing each cron into the named slot."""
    if len(crons) != 3 or len(order) != 3 or set(order) != {1, 2, 3}:
        raise ValueError("three crons and positions 1, 2, 3")
    slots = {int(pos): int(cron) for pos, cron in zip(order, crons)}
    return slots[1] * 100 + slots[2] * 10 + slots[3]


def _deal(rng: random.Random) -> tuple[int, int, int]:
    return (rng.randrange(10), rng.randrange(10), rng.randrange(10))


def play_match(
    rng: random.Random,
    *,
    ante: int = ANTE,
    rounds: int = ROUNDS,
    champion: int = OPENING_CHAMPION,
    jackpot: int = OPENING_JACKPOT,
    order: Sequence[int] = PLACE_231,
) -> dict[str, int | bool]:
    """Play one match. The ante is already inside the returned jackpot."""
    fee = int(ante)
    pot = int(jackpot) + fee
    player_total = 0
    house_total = 0
    for _ in range(int(rounds)):
        player_total += number_from(_deal(rng), order)
        house_total += number_from(_deal(rng), order)
    beat_house = player_total > house_total
    took_jackpot = player_total > int(champion)
    payback = fee * PAYBACK_NUMERATOR if beat_house else 0
    if took_jackpot:
        prize = pot
        pot = 0
        champ = player_total
    else:
        prize = 0
        champ = int(champion)
    return {
        "ante": fee,
        "player_total": player_total,
        "house_total": house_total,
        "beat_house": beat_house,
        "payback": payback,
        "took_jackpot": took_jackpot,
        "jackpot_prize": prize,
        "jackpot": pot,
        "champion": champ,
        "credits_delta": payback + prize - fee,
    }
