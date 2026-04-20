"""Per-match copilot registry — one `CopilotSession` per HUMAN slot.

Owned by the FastAPI app's state. Rebuilt whenever the match
(re)starts so stale sessions from a previous run can't leak back in.
"""

from __future__ import annotations

from typing import Any

from ..agents.human import HumanAgent
from .chat_agent import ChatAgent
from .session import CopilotSession


class CopilotRegistry:
    def __init__(self) -> None:
        self._sessions: dict[str, CopilotSession] = {}

    def clear(self) -> None:
        self._sessions.clear()

    def get(self, player_id: str) -> CopilotSession | None:
        return self._sessions.get(player_id)

    def all(self) -> list[CopilotSession]:
        return list(self._sessions.values())

    def rebuild(
        self,
        *,
        runner,
        broadcaster,
        chat_agent_factory=None,
        task_next_step_factory=None,
    ) -> None:
        """Create a fresh session for every HUMAN slot in `runner.state.agents`.

        Cleanly replaces any previous sessions — callers must invoke
        `clear()` (or call rebuild again) before match-restart so chat
        history from the previous run doesn't leak.
        """
        self._sessions.clear()

        def universe_fn():
            return runner.state.universe

        async def broadcast_fn(msg: dict[str, Any]) -> None:
            await broadcaster.publish(msg)

        for ag in runner.state.agents:
            if not isinstance(ag, HumanAgent):
                continue
            chat_agent = (chat_agent_factory or ChatAgent)()
            self._sessions[ag.player_id] = CopilotSession(
                player_id=ag.player_id,
                human_agent=ag,
                universe_fn=universe_fn,
                broadcast_fn=broadcast_fn,
                chat_agent=chat_agent,
                task_next_step_factory=task_next_step_factory,
            )
