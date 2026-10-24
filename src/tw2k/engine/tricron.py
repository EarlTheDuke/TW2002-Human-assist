"""Tri-Cron, the Lost Trader's Tavern game. No engine calls.

Confirmed screen: docs/playtests/twgs-live/tricron.txt (19 Oct 2026).
Ante 100, 10 rounds, three crons from 0 to 9, positions 1 (hundreds),
2 (tens) and 3 (ones), the greater total wins, payback 2 to 1, jackpot
5,000, champion score 5,000. One win on that screen paid "You win 100
credits!" (balance 128 to 228). The omitted placement is 2-3-1, the
combination STARDOCK_TAVERN.md tv11 and the Bible already name. The house
uses the same order. The ante is added to the jackpot before the match
is scored. A tie is not a greater total, so it does not pay.
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
