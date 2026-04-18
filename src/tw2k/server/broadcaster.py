"""WebSocket event broadcaster — fan-out pattern."""

from __future__ import annotations

import asyncio
import json
from typing import Any


class Broadcaster:
    """Keeps a set of connected WebSocket clients and fans out messages."""

    def __init__(self, history_cap: int = 400):
        self._subscribers: set[asyncio.Queue[str]] = set()
        self._history: list[str] = []
        self._history_cap = history_cap
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=1000)
        async with self._lock:
            # Replay recent history to new subscribers (so they see the start of the match)
            for item in self._history:
                try:
                    q.put_nowait(item)
                except asyncio.QueueFull:
                    break
            self._subscribers.add(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        async with self._lock:
            self._subscribers.discard(q)

    def reset_history(self) -> None:
        """Clear retained history — call on match restart so new subscribers
        don't replay the previous match's events."""
        self._history.clear()

    async def publish(self, message: dict[str, Any]) -> None:
        text = json.dumps(message, default=str)
        async with self._lock:
            self._history.append(text)
            if len(self._history) > self._history_cap:
                # Keep the init event + latest N-1
                init = self._history[0] if self._history and '"init"' in self._history[0] else None
                self._history = self._history[-self._history_cap :]
                if init is not None and init not in self._history:
                    self._history.insert(0, init)
            dead: list[asyncio.Queue[str]] = []
            for q in self._subscribers:
                try:
                    q.put_nowait(text)
                except asyncio.QueueFull:
                    dead.append(q)
            for q in dead:
                self._subscribers.discard(q)
