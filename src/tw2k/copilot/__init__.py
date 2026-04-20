"""TW2K AI copilot — helps a human player decide and execute actions.

The copilot is organized into four pieces:

- **VoiceAgent** (`chat_agent.py`) — turns a human utterance + current
  observation into either an immediate action, a multi-step plan to
  confirm, or a clarifying question. Typed-only in H2; voice in H3+.
- **TaskAgent** (`task_agent.py`) — long-running autopilot loop that
  executes actions until a terminal condition fires or the human
  interrupts. "Run my trade loop until 30k cr" is a TaskAgent job.
- **UIAgent** (`ui_agent.py`) — fast, rule-based annotations for the
  cockpit UI (button tooltips, suggested next move). No LLM cost.
- **CopilotSession** (`session.py`) — per-human state container that
  glues everything together and exposes a small async API used by the
  FastAPI endpoints.

Engine interactions always go through the same `HumanAgent.submit_action`
path manual play uses, with `actor_kind_override("copilot")` scoped
around the dispatch so every resulting event is tagged correctly for
replay + forensics.

See `docs/HUMAN_COPILOT_PLAN.md` §5-6 for the full design.
"""

from __future__ import annotations

from .session import CopilotMode, CopilotSession
from .standing_orders import StandingOrder, StandingOrderKind
from .tools import TOOL_CATALOG, ToolCall, ToolSpec

__all__ = [
    "TOOL_CATALOG",
    "CopilotMode",
    "CopilotSession",
    "StandingOrder",
    "StandingOrderKind",
    "ToolCall",
    "ToolSpec",
]
