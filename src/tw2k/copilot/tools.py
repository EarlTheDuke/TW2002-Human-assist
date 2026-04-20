"""Copilot tool catalog + cross-provider adapters.

One schema → three provider shapes (Anthropic / OpenAI / xAI share the
OpenAI shape). The same catalog is used by VoiceAgent and TaskAgent.

Tools split into five groups (doc §6):

- **action**        — one per engine `ActionKind`. LLM → engine.
- **planning**      — copilot-internal reads over the observation
                      (find_path, evaluate_trade_pair). Never hit engine.
- **dialog**        — talk back to the human (speak, ask_human).
- **orchestration** — start_task / cancel_task / set_standing_order.
- **observability** — get_observation / get_recent_events.

The H2 implementation is deliberately compact: we expose the tools the
scripted-mock and real-LLM code paths need for the exit criterion
("run my trade loop until 30k cr"). Extra tools can slot in later
without touching the adapter code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Tool schema — source of truth
# ---------------------------------------------------------------------------

ToolGroup = Literal["action", "planning", "dialog", "orchestration", "observability"]


@dataclass(frozen=True)
class ToolSpec:
    """Single tool entry in the catalog.

    `parameters` uses the JSON-Schema subset shared by every provider
    we target. `engine_action` is set for tools that map 1:1 to an
    engine `ActionKind`; planning/dialog/orchestration tools leave it
    None and are handled inside the copilot process.
    """

    name: str
    group: ToolGroup
    description: str
    parameters: dict[str, Any]
    engine_action: str | None = None  # ActionKind.value, or None

    def to_openai(self) -> dict[str, Any]:
        """OpenAI / xAI / DeepSeek / Ollama (OpenAI-compat) tool shape."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_anthropic(self) -> dict[str, Any]:
        """Anthropic Messages API tool shape."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }


def _obj(**props: dict[str, Any]) -> dict[str, Any]:
    """Tiny helper: build a JSON-Schema object with given properties.

    All listed props are REQUIRED unless they carry a `"default"` key.
    Keeps the catalog below compact and readable.
    """
    required = [k for k, v in props.items() if "default" not in v]
    return {
        "type": "object",
        "properties": props,
        "required": required,
        "additionalProperties": False,
    }


# ---------------------------------------------------------------------------
# Catalog entries
# ---------------------------------------------------------------------------

_COMMODITY_ENUM = ["fuel_ore", "organics", "equipment"]

TOOL_CATALOG: dict[str, ToolSpec] = {
    # ---- action tools (engine-facing) -------------------------------------
    "warp": ToolSpec(
        name="warp",
        group="action",
        description="Warp to an adjacent sector (must be in current sector's warps list).",
        parameters=_obj(target={"type": "integer", "description": "Target sector id"}),
        engine_action="warp",
    ),
    "plot_course": ToolSpec(
        name="plot_course",
        group="action",
        description=(
            "Auto-pilot through the shortest known-warps path to a target sector. "
            "Consumes turns for each hop until arrival or out-of-turns."
        ),
        parameters=_obj(target={"type": "integer", "description": "Destination sector id"}),
        engine_action="plot_course",
    ),
    "scan": ToolSpec(
        name="scan",
        group="action",
        description="Long-range scan of the current sector's warps.",
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
        engine_action="scan",
    ),
    "probe": ToolSpec(
        name="probe",
        group="action",
        description="Launch an etherprobe toward a target sector to gather intel.",
        parameters=_obj(target={"type": "integer", "description": "Sector to probe"}),
        engine_action="probe",
    ),
    "buy": ToolSpec(
        name="buy",
        group="action",
        description=(
            "Buy `qty` units of a commodity from the port in the current sector. "
            "Maps to the TRADE action with side='buy'."
        ),
        parameters=_obj(
            commodity={"type": "string", "enum": _COMMODITY_ENUM},
            qty={"type": "integer", "minimum": 1},
            unit_price={
                "type": "integer",
                "description": "Optional haggle counter-offer; omit to accept port ask.",
                "default": None,
            },
        ),
        engine_action="trade",  # side=buy
    ),
    "sell": ToolSpec(
        name="sell",
        group="action",
        description=(
            "Sell `qty` units of a commodity to the port in the current sector. "
            "Maps to the TRADE action with side='sell'."
        ),
        parameters=_obj(
            commodity={"type": "string", "enum": _COMMODITY_ENUM},
            qty={"type": "integer", "minimum": 1},
            unit_price={
                "type": "integer",
                "description": "Optional haggle counter-offer; omit to accept port bid.",
                "default": None,
            },
        ),
        engine_action="trade",  # side=sell
    ),
    "attack": ToolSpec(
        name="attack",
        group="action",
        description="Attack another ship in the current sector.",
        parameters=_obj(target_id={"type": "string", "description": "Target player id"}),
        engine_action="attack",
    ),
    "deploy_fighters": ToolSpec(
        name="deploy_fighters",
        group="action",
        description="Deploy a fighter wing in the current sector.",
        parameters=_obj(qty={"type": "integer", "minimum": 1}),
        engine_action="deploy_fighters",
    ),
    "land_planet": ToolSpec(
        name="land_planet",
        group="action",
        description="Land on a planet in the current sector (planet_id required).",
        parameters=_obj(planet_id={"type": "integer"}),
        engine_action="land_planet",
    ),
    "liftoff": ToolSpec(
        name="liftoff",
        group="action",
        description="Lift off from the planet back to orbit.",
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
        engine_action="liftoff",
    ),
    "pass_turn": ToolSpec(
        name="pass_turn",
        group="action",
        description="Do nothing this turn (WAIT).",
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
        engine_action="wait",
    ),
    # ---- planning tools (copilot-internal) --------------------------------
    "find_path": ToolSpec(
        name="find_path",
        group="planning",
        description=(
            "Compute shortest warp path from current sector to a target, "
            "over the player's known_warps (fog-of-war respecting)."
        ),
        parameters=_obj(
            target={"type": "integer"},
            avoid={
                "type": "array",
                "items": {"type": "integer"},
                "description": "Sector ids to avoid",
                "default": [],
            },
        ),
    ),
    "evaluate_trade_pair": ToolSpec(
        name="evaluate_trade_pair",
        group="planning",
        description=(
            "Estimate per-unit margin between a buy-port and a sell-port for a given "
            "commodity, using the player's known_ports snapshots."
        ),
        parameters=_obj(
            buy_sector={"type": "integer"},
            sell_sector={"type": "integer"},
            commodity={"type": "string", "enum": _COMMODITY_ENUM},
        ),
    ),
    # ---- dialog tools (copilot-internal) ----------------------------------
    "speak": ToolSpec(
        name="speak",
        group="dialog",
        description=(
            "Say something back to the human, shown in the /play chat panel "
            "(and spoken via TTS in H4+)."
        ),
        parameters=_obj(
            message={"type": "string"},
            urgency={
                "type": "string",
                "enum": ["low", "normal", "high"],
                "default": "normal",
            },
        ),
    ),
    "ask_human": ToolSpec(
        name="ask_human",
        group="dialog",
        description="Pause and request a decision from the human before continuing.",
        parameters=_obj(
            question={"type": "string"},
            options={
                "type": "array",
                "items": {"type": "string"},
                "default": [],
            },
        ),
    ),
    # ---- orchestration tools (copilot-internal) ---------------------------
    "start_task": ToolSpec(
        name="start_task",
        group="orchestration",
        description=(
            "Hand off a long-running goal to the TaskAgent (autopilot). "
            "Returns immediately; progress is reported back via copilot events."
        ),
        parameters=_obj(
            kind={
                "type": "string",
                "enum": ["profit_loop", "explore", "flee"],
                "description": "Task archetype — profit_loop shuttles trade goods until target.",
            },
            params={
                "type": "object",
                "description": "Task-specific knobs (e.g. {'target_cr': 30000}).",
                "default": {},
            },
        ),
    ),
    "cancel_task": ToolSpec(
        name="cancel_task",
        group="orchestration",
        description="Cancel any running autopilot task (also fires on human Esc).",
        parameters={
            "type": "object",
            "properties": {"reason": {"type": "string", "default": "human_cancel"}},
            "additionalProperties": False,
        },
    ),
    # ---- observability tools ---------------------------------------------
    "get_observation": ToolSpec(
        name="get_observation",
        group="observability",
        description="Return the player's current Observation (same view LLM agents see).",
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
    ),
}


# ---------------------------------------------------------------------------
# Adapter helpers
# ---------------------------------------------------------------------------


def tool_schema_for_provider(provider: str) -> list[dict[str, Any]]:
    """Return the full catalog rendered for a given LLM provider.

    `provider` values mirror `tw2k.agents.llm.default_provider()`:
    'anthropic', 'openai', 'xai', 'deepseek', 'custom'. All non-Anthropic
    providers use the OpenAI-compatible `{type: function, function: ...}`
    wrapper since every endpoint we ship against honours that shape.
    """
    provider = (provider or "openai").lower()
    items = list(TOOL_CATALOG.values())
    if provider == "anthropic":
        return [t.to_anthropic() for t in items]
    return [t.to_openai() for t in items]


def tools_by_group(group: ToolGroup) -> list[ToolSpec]:
    return [t for t in TOOL_CATALOG.values() if t.group == group]


# ---------------------------------------------------------------------------
# ToolCall model — the single structured shape every LLM response is
# normalised to before the executor runs it. Keeps the rest of the copilot
# agnostic of Anthropic-vs-OpenAI-vs-manual-JSON parsing quirks.
# ---------------------------------------------------------------------------


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    # Optional free-text rationale the LLM attached — shown in the chat log
    # so the human can see *why* the copilot chose this.
    thought: str = ""

    def spec(self) -> ToolSpec | None:
        return TOOL_CATALOG.get(self.name)

    def validate_against_catalog(self) -> str | None:
        """Return None if OK, else a human-readable error reason.

        We only validate structural things here (tool exists, no unknown
        args). Value-level validation (sector exists, enough credits, …)
        happens engine-side via `apply_action` and is surfaced back to
        the copilot on rejection.
        """
        spec = self.spec()
        if spec is None:
            return f"unknown tool {self.name!r}"
        props = spec.parameters.get("properties", {})
        unknown = [k for k in self.arguments if k not in props]
        if unknown:
            return f"unknown argument(s) for {self.name}: {unknown!r}"
        required = spec.parameters.get("required", [])
        missing = [k for k in required if k not in self.arguments]
        if missing:
            return f"missing required argument(s) for {self.name}: {missing!r}"
        return None
