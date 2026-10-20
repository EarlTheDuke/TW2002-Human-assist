"""One thing the player may do on the seat page."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

OPS = ("click", "type", "press", "wait")
_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class Action:
    op: str
    label: str = ""
    selector: str = ""
    text: str = ""
    key: str = ""
    ms: int = 0

    def as_dict(self) -> dict[str, object]:
        return {
            "op": self.op,
            "label": self.label,
            "selector": self.selector,
            "text": self.text,
            "key": self.key,
            "ms": self.ms,
        }


class ActionError(ValueError):
    """The model, or the page, did not produce a usable action."""


def _clip(value: object, limit: int = 200) -> str:
    return str(value or "")[:limit]


def parse_action(payload: object) -> Action:
    """Accept a dict or a model message that contains one JSON object."""
    if isinstance(payload, str):
        match = _OBJECT.search(payload)
        if match is None:
            raise ActionError("the reply had no action object")
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ActionError("the reply was not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ActionError("an action is a JSON object")
    op = str(payload.get("op") or "").strip().lower()
    if op not in OPS:
        raise ActionError("op must be click, type, press, or wait")
    try:
        ms = int(payload.get("ms") or 0)
    except (TypeError, ValueError) as exc:
        raise ActionError("ms must be a number") from exc
    ms = max(0, min(ms, 10_000))
    return Action(
        op=op,
        label=_clip(payload.get("label")),
        selector=_clip(payload.get("selector")),
        text=_clip(payload.get("text"), 80),
        key=_clip(payload.get("key"), 40),
        ms=ms,
    )
