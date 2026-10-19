"""In-memory key for one lobby game's AI seats. Nothing here is written down.

NOTE 100. The key and the endpoint live on this object until the game ends
or the process stops. Logs use mask_key. Callers must not put either value
in a save, a response, or a log line.
"""

from __future__ import annotations

import time
from collections import deque

from ..engine import constants as K

# Public sentence. The cockpit already shows broadcast summaries. No key in it.
FALLBACK_LINE = "Playing the heuristic brain. No key is on the server."


def mask_key(key: str) -> str:
    """``key ****`` plus the last four characters, or ``key ****`` when shorter."""
    text = str(key or "")
    if len(text) < 4:
        return "key ****"
    return "key ****" + text[-4:]


class AiRow:
    """One game. ``repr`` omits the key, the endpoint, and the seat tokens."""

    def __init__(self, brain: str) -> None:
        self.brain = brain
        self.key = ""
        self.url = ""
        self.tokens: dict[str, str] = {}

    def __repr__(self) -> str:
        return f"AiRow(brain={self.brain!r}, seats={sorted(self.tokens)})"


class AiMemory:
    """Process-local table. ``drop`` forgets the key."""

    def __init__(self) -> None:
        self._rows: dict[str, AiRow] = {}

    def remember(self, gid: str, *, key: str, url: str, brain: str) -> None:
        row = self._rows.get(gid)
        if row is None:
            row = AiRow(brain)
            self._rows[gid] = row
        row.brain = brain
        row.key = key
        row.url = url

    def hold_tokens(self, gid: str, tokens: dict[str, str], *, brain: str) -> None:
        row = self._rows.get(gid)
        if row is None:
            row = AiRow(brain)
            self._rows[gid] = row
        row.brain = brain
        row.tokens = dict(tokens)

    def row(self, gid: str) -> AiRow | None:
        return self._rows.get(gid)

    def drop(self, gid: str) -> None:
        row = self._rows.pop(gid, None)
        if row is None:
            return
        row.key = ""
        row.url = ""
        row.tokens.clear()

    def drop_all(self) -> None:
        for gid in list(self._rows):
            self.drop(gid)


class LlmBudget:
    """Per-game call cap and per-minute limit. A miss returns None so the heuristic plays.

    ``lasting_fallback`` is set when the cap is hit, the endpoint is missing,
    or the endpoint errors. A minute that is already full skips that one call
    and tries again on a later turn.
    """

    def __init__(self, *, url: str, cap: int | None = None, per_minute: int | None = None) -> None:
        self.url = url
        self.cap = int(K.LOBBY_AI_CALL_CAP if cap is None else cap)
        self.per_minute = int(K.LOBBY_AI_CALLS_PER_MINUTE if per_minute is None else per_minute)
        self.calls = 0
        self.stamps: deque[float] = deque()
        self.lasting_fallback = False

    def __call__(self, key: str, obs: dict, cockpit: dict | None):
        if self.lasting_fallback:
            return None
        now = time.monotonic()
        while self.stamps and now - self.stamps[0] >= 60:
            self.stamps.popleft()
        if self.calls >= self.cap:
            self.lasting_fallback = True
            return None
        if len(self.stamps) >= self.per_minute:
            return None
        try:
            from ..agents import cockpit_seat as seat

            picked = seat._llm_http_choose(key, obs, cockpit, url=self.url)
        except Exception:
            self.lasting_fallback = True
            return None
        if picked is None:
            self.lasting_fallback = True
            return None
        self.calls += 1
        self.stamps.append(time.monotonic())
        return picked


async def drive_seats(client, tokens: dict[str, str], *, brain: str, key: str, url: str,
                      days: int, idle_s: float) -> None:
    """Play each AI seat through the cockpit routes. ``client`` is already aimed at the worker."""
    import asyncio

    from ..agents.cockpit_seat import run_http

    llm = brain == "llm"
    budget = LlmBudget(url=url) if llm else None
    if budget is not None and not str(key or "").strip():
        budget.lasting_fallback = True
    line = FALLBACK_LINE if llm else None

    async def one(seat: str, token: str) -> None:
        await run_http(
            client, seat, token, days, lobby=True, idle_s=idle_s,
            llm_key=key if llm else "",
            llm_ask=budget,
            fallback_line=line,
        )

    await asyncio.gather(*(one(seat, token) for seat, token in tokens.items()))
