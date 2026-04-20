"""Per-match copilot registry — one `CopilotSession` per HUMAN slot.

Owned by the FastAPI app's state. Rebuilt whenever the match
(re)starts so stale sessions from a previous run can't leak back in.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..agents.human import HumanAgent
from .chat_agent import ChatAgent
from .memory import MemoryStore
from .otel import build_bridge as _build_otel_bridge
from .session import CopilotSession
from .trace import CopilotTracer, _env_enabled


class CopilotRegistry:
    def __init__(
        self,
        *,
        memory_dir: Path | str | None = None,
        trace_dir: Path | str | None = None,
    ) -> None:
        self._sessions: dict[str, CopilotSession] = {}
        self._memory_store = MemoryStore(memory_dir)
        self._trace_dir = Path(trace_dir) if trace_dir is not None else None

    def clear(self) -> None:
        for sess in self._sessions.values():
            # Release OTEL session spans cleanly; JSONL sink has no
            # close phase. Failures are swallowed inside shutdown().
            sess.tracer.shutdown()
        self._sessions.clear()

    def get(self, player_id: str) -> CopilotSession | None:
        return self._sessions.get(player_id)

    def all(self) -> list[CopilotSession]:
        return list(self._sessions.values())

    @property
    def memory_store(self) -> MemoryStore:
        return self._memory_store

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
            # Phase H6.3: if TW2K_OTEL_ENDPOINT (or TW2K_OTEL_CONSOLE) is
            # set, build a long-lived OTEL session span for this player.
            # `build_bridge` returns None when OTEL is disabled/missing.
            otel_bridge = _build_otel_bridge(
                player_id=ag.player_id,
                attributes={"tw2k.agent_name": ag.name},
            )
            tracer = CopilotTracer(
                player_id=ag.player_id,
                root_dir=self._trace_dir,
                # enable tracer when root is set AND env opt-in fires; when
                # no root is set, the tracer is a cheap no-op.
                enable=(self._trace_dir is not None and _env_enabled()),
                otel_bridge=otel_bridge,
            )
            self._sessions[ag.player_id] = CopilotSession(
                player_id=ag.player_id,
                human_agent=ag,
                universe_fn=universe_fn,
                broadcast_fn=broadcast_fn,
                chat_agent=chat_agent,
                task_next_step_factory=task_next_step_factory,
                memory_store=self._memory_store,
                tracer=tracer,
            )
