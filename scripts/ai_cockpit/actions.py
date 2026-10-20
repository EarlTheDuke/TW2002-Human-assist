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


def _folded(labels: list[str]) -> list[str]:
    return [row.strip() for row in labels if row and str(row).strip()]


def label_on_screen(label: str, labels: list[str]) -> bool:
    """True when a click label is one of the visible controls."""
    wanted = (label or "").strip()
    if not wanted:
        return False
    rows = _folded(labels)
    if any(row.casefold() == wanted.casefold() for row in rows):
        return True
    head = wanted.casefold()
    if head in ("sell", "buy") or head.startswith("sell ") or head.startswith("buy "):
        kind = "sell" if head.startswith("sell") else "buy"
        return any(row.casefold().startswith(kind) for row in rows)
    return False


def reject_reason(action: Action, labels: list[str], *, selectors: list[str] | None = None,
                  fields: list[str] | None = None) -> str:
    """Empty when the action matches a visible control. Otherwise the reason it does not."""
    if action.op == "wait":
        return ""
    if action.op == "press":
        if not action.key or len(action.key) > 20:
            return "press needs one key"
        return ""
    if action.op == "type":
        if not action.text:
            return "type needs text"
        known = {row.casefold() for row in (selectors or [])}
        names = {row.casefold() for row in (fields or [])}
        selector = action.selector.strip()
        if selector and selector.casefold() not in known and not any(name in selector.casefold() for name in names):
            return "that field is not on screen"
        return ""
    if action.op == "click":
        if label_on_screen(action.label, labels):
            return ""
        selector = action.selector.strip()
        known = {row.casefold() for row in (selectors or [])}
        if selector and selector.casefold() in known:
            return ""
        return "that control is not on screen"
    return "op is not usable"
