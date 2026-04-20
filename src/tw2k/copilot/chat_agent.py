"""ChatAgent — the text/voice front door of the copilot.

Given a human utterance + current observation, produces one of:

- `ChatResponse(kind="speak", message=...)` — advisory reply, no action.
- `ChatResponse(kind="plan", plan=[ToolCall, ...], needs_confirm=True)` — multi-step plan
  the human must Confirm before execution.
- `ChatResponse(kind="action", plan=[ToolCall])` — single immediate
  action (Delegated mode). Bypasses confirm when mode allows.
- `ChatResponse(kind="start_task", task_kind=..., task_params=...)` —
  hand off to TaskAgent (autopilot).
- `ChatResponse(kind="cancel")` — human said "stop / cancel / nvm".
- `ChatResponse(kind="clarify", message=...)` — ask a clarifying question.

The LLM emits our JSON envelope (see `provider.parse_tool_response`).
We fan it out into a `ChatResponse` here.

This agent deliberately doesn't loop — each call is one LLM round-trip.
Multi-turn tool loops live in TaskAgent.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..engine import Observation
from . import provider as prov
from .tools import TOOL_CATALOG, ToolCall

# Small-budget system prompt. Phrased so JSON-mode models emit a clean
# envelope on every reply.
SYSTEM_PROMPT = """\
You are the AI copilot for a solo human player of a Trade Wars 2002-style
space trader game. You help them by:
  - Answering questions about game state (short, factual).
  - Translating their intent into ONE tool call (Delegated mode).
  - Proposing a multi-step plan to confirm (Autopilot/long-running goal).
  - Handing off long goals ("run my trade loop until 30k cr") to the
    autopilot TaskAgent via start_task.

You always reply with a SINGLE JSON object (no prose, no markdown fences).
Pick ONE of these envelope shapes:

  1. Direct action:
     {"tool": "<tool_name>", "arguments": {...}, "thought": "..."}
  2. Multi-step plan (human will Confirm before execution):
     {"plan": [{"tool": ..., "arguments": ...}, ...], "thought": "..."}
  3. Speak only (advisory, no action taken):
     {"tool": "speak", "arguments": {"message": "..."}, "thought": "..."}
  4. Hand off autopilot:
     {"tool": "start_task", "arguments": {"kind": "profit_loop",
        "params": {"target_cr": 30000}}, "thought": "..."}
  5. Clarify:
     {"tool": "ask_human", "arguments": {"question": "...",
        "options": ["a","b"]}, "thought": "..."}

Rules:
  - Use exactly the tool names from the catalog. No custom tools.
  - If the human says "stop", "cancel", "abort", emit
    {"tool":"cancel_task","arguments":{"reason":"human_cancel"}}.
  - Keep `thought` short (<= 40 words), it is shown verbatim to the human.
  - Prefer `plan` for anything longer than one step; prefer `start_task`
    for open-ended goals that need many turns.
"""


# ---------------------------------------------------------------------------
# ChatResponse model
# ---------------------------------------------------------------------------


ChatKind = Literal["speak", "plan", "action", "start_task", "cancel", "clarify", "noop"]


class ChatResponse(BaseModel):
    kind: ChatKind
    message: str = ""
    plan: list[ToolCall] = Field(default_factory=list)
    task_kind: str | None = None
    task_params: dict[str, Any] = Field(default_factory=dict)
    needs_confirm: bool = False
    options: list[str] = Field(default_factory=list)
    thought: str = ""


# ---------------------------------------------------------------------------
# Formatter — user message
# ---------------------------------------------------------------------------


def _compact_observation(obs: Observation) -> dict[str, Any]:
    """Shrink Observation to the keys the copilot actually uses per turn.

    Sends roughly 1-2 kB of JSON instead of 20 kB. Keeps the LLM round
    cheap and avoids blowing past small context windows.
    """
    sec = obs.sector or {}
    port = sec.get("port")
    return {
        "day": obs.day,
        "tick": obs.tick,
        "turns_remaining": obs.turns_remaining,
        "credits": obs.credits,
        "alignment": obs.alignment,
        "rank": obs.rank,
        "ship": {
            "class": obs.ship.get("class"),
            "hull": obs.ship.get("hull"),
            "max_hull": obs.ship.get("max_hull"),
            "cargo": obs.ship.get("cargo", {}),
            "cargo_max": obs.ship.get("cargo_max"),
            "fighters": obs.ship.get("fighters"),
            "shields": obs.ship.get("shields"),
        },
        "sector": {
            "id": sec.get("id"),
            "warps": sec.get("warps", []),
            "port": (
                {
                    "class_id": port.get("class_id"),
                    "buying": port.get("buying"),
                    "selling": port.get("selling"),
                    "prices": port.get("prices"),
                    "stock": port.get("stock"),
                }
                if port
                else None
            ),
            "players_here": sec.get("players_here", []),
        },
        "goals": obs.goals,
        "scratchpad": obs.scratchpad[:500] if obs.scratchpad else "",
        "trade_summary": obs.trade_summary,
        "known_warps_count": len(obs.known_warps or {}),
        "known_ports_count": len(obs.known_ports or []),
    }


def _tool_list_for_prompt() -> str:
    """Render the catalog as a compact reference included with every call."""
    lines = []
    for t in TOOL_CATALOG.values():
        args = list(t.parameters.get("properties", {}).keys())
        lines.append(f"- {t.name}({', '.join(args)}): {t.description}")
    return "\n".join(lines)


def build_user_prompt(utterance: str, obs: Observation, *, mode: str) -> str:
    return (
        f"[mode={mode}]\n"
        f"HUMAN: {utterance.strip()}\n\n"
        f"OBSERVATION (JSON):\n{json.dumps(_compact_observation(obs))}\n\n"
        f"TOOL CATALOG:\n{_tool_list_for_prompt()}\n\n"
        "Respond with a single JSON envelope now."
    )


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class ChatAgent:
    """One-shot JSON-envelope LLM call per chat turn.

    Not stateful by itself — CopilotSession owns the conversation history
    and the active mode, passing them in via `build_user_prompt`.
    """

    def __init__(
        self,
        *,
        provider: str | None = None,
        model: str | None = None,
        timeout_s: float = 25.0,
    ):
        self.provider = provider
        self.model = model
        self.timeout_s = timeout_s

    async def respond(
        self, utterance: str, obs: Observation, *, mode: str
    ) -> ChatResponse:
        user = build_user_prompt(utterance, obs, mode=mode)
        try:
            raw = await prov.call_llm(
                system=SYSTEM_PROMPT,
                user=user,
                provider=self.provider,
                model=self.model,
                timeout_s=self.timeout_s,
            )
        except RuntimeError as exc:
            return ChatResponse(
                kind="speak",
                message=f"[copilot offline] {exc}",
                thought="no provider configured",
            )
        except TimeoutError:
            return ChatResponse(
                kind="speak",
                message=(
                    f"[copilot timed out after {self.timeout_s:.0f}s] try rephrasing."
                ),
                thought="llm timeout",
            )
        except Exception as exc:  # network, auth, model error
            return ChatResponse(
                kind="speak",
                message=f"[copilot error] {type(exc).__name__}: {exc}",
                thought="llm exception",
            )

        calls = prov.parse_tool_response(raw)
        return self._classify(calls, raw)

    @staticmethod
    def _classify(calls: list[ToolCall], raw: str) -> ChatResponse:
        if not calls:
            return ChatResponse(
                kind="speak",
                message=(
                    "[copilot reply wasn't parseable JSON — try rephrasing] "
                    f"{raw[:200]}"
                ),
                thought="parse failure",
            )

        if len(calls) == 1:
            c = calls[0]
            spec = c.spec()

            if c.name == "cancel_task":
                return ChatResponse(
                    kind="cancel", message="Cancelling.", thought=c.thought
                )
            if c.name == "ask_human":
                return ChatResponse(
                    kind="clarify",
                    message=str(c.arguments.get("question", "")),
                    options=list(c.arguments.get("options", []) or []),
                    thought=c.thought,
                )
            if c.name == "speak":
                return ChatResponse(
                    kind="speak",
                    message=str(c.arguments.get("message", "")),
                    thought=c.thought,
                )
            if c.name == "start_task":
                return ChatResponse(
                    kind="start_task",
                    task_kind=str(c.arguments.get("kind", "profit_loop")),
                    task_params=dict(c.arguments.get("params", {}) or {}),
                    message="Starting autopilot task.",
                    thought=c.thought,
                    needs_confirm=True,
                )
            # Any action tool with a single call → immediate action.
            if spec is not None and spec.group == "action":
                return ChatResponse(
                    kind="action", plan=[c], thought=c.thought
                )
            # Planning / observability single call — treat as speak for now.
            return ChatResponse(
                kind="speak",
                message=f"[ignored tool {c.name} — planning tools arrive in H3]",
                thought=c.thought,
            )

        # Multi-step — always needs confirm.
        return ChatResponse(
            kind="plan",
            plan=calls,
            needs_confirm=True,
            thought=calls[0].thought if calls else "",
        )
