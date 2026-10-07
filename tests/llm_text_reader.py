"""Offline stand-in for an LLM seat. It reads only the rendered prompt texts.

It never calls a paid API and never reads an Observation object. A verb is
used only when the system prompt names it, so the legacy prompt cannot reach
the ten verbs this slice documents.
"""

from __future__ import annotations

import json
import re
from typing import Any

from tw2k.agents.llm import LLMAgent


def _user(user_turn: str) -> dict[str, Any]:
    data = json.loads(user_turn)
    if not isinstance(data, dict):
        raise ValueError("user turn is not an object")
    return data


def _legal(user: dict[str, Any]) -> set[str]:
    block = user.get("legal_actions") or {}
    return {str(kind) for kind in (block.get("legal") or [])}


def _stardock(system: str) -> int:
    match = re.search(r"StarDock \(sector (\d+)\)", system)
    return int(match.group(1)) if match else 1


def _here(user: dict[str, Any]) -> int | None:
    sector = user.get("sector") or {}
    raw = sector.get("id")
    return int(raw) if raw is not None else None


def _credits(user: dict[str, Any]) -> int:
    return int((user.get("self") or {}).get("credits") or 0)


def _execute_named(system: str) -> bool:
    return '"execute":true' in system


def _verb_named(system: str, verb: str) -> bool:
    return f"`{verb}" in system or f'"{verb}' in system or f" {verb} " in system


def _action(kind: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"action": {"kind": kind, "args": args or {}}}


def _join_password_named(system: str) -> bool:
    return 'corp_join {"ticker":"XYZ","password":' in system


def _invite(user: dict[str, Any]) -> dict[str, Any] | None:
    for row in user.get("inbox") or []:
        if isinstance(row, dict) and row.get("ticker") and row.get("password"):
            return row
    return None


def _tax_line(system: str) -> int | None:
    match = re.search(r"carrying over ([0-9,]+) credits", system)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def choose(system: str, user_turn: str) -> dict[str, Any]:
    """Pick one action from the system prompt and the user-turn JSON."""
    user = _user(user_turn)
    legal = _legal(user)
    here = _here(user)
    dock = _stardock(system)
    credits = _credits(user)
    at_dock = here == dock

    if (
        _execute_named(system)
        and "plot_course" in legal
        and here is not None
        and not at_dock
        and credits >= 20_000
    ):
        return _action("plot_course", {"target": dock, "execute": True})

    if at_dock and "buy_ship" in legal and credits >= 50_000 and _verb_named(system, "buy_ship"):
        return _action("buy_ship", {"ship_class": "cargotran"})

    tax = _tax_line(system)
    if (
        tax is not None
        and _verb_named(system, "bank_deposit")
        and "bank_deposit" in legal
        and at_dock
        and credits > tax
    ):
        return _action("bank_deposit", {"amount": credits - tax})

    invite = _invite(user)
    if invite and _join_password_named(system) and "corp_join" in legal:
        return _action("corp_join", {"ticker": invite["ticker"], "password": invite["password"]})

    if _verb_named(system, "corp_transfer") and "corp_transfer" in legal:
        return _action(
            "corp_transfer",
            {"target": "P3", "item": "credits", "qty": 1000, "direction": "give"},
        )

    if _verb_named(system, "port_upgrade") and "port_upgrade" in legal and credits >= 250:
        return _action("port_upgrade", {"commodity": "fuel_ore", "units": 1})

    if "trade" in legal:
        return _action("trade", {"commodity": "fuel_ore", "qty": 1, "side": "buy"})
    if "warp" in legal:
        adjacent = user.get("adjacent") or []
        target = adjacent[0]["id"] if adjacent and isinstance(adjacent[0], dict) else 1
        return _action("warp", {"target": target})
    return _action("wait")


def reply(system: str, user_turn: str) -> str:
    return json.dumps(choose(system, user_turn))


class TextReaderAgent(LLMAgent):
    """LLMAgent seat whose reply is `choose`, with no network client."""

    def __init__(self, player_id: str, name: str) -> None:
        super().__init__(player_id, name, provider="openai", model="text-reader")
        self._warmed = True

    async def warmup(self) -> tuple[bool, str]:
        self._warmed = True
        return True, "text reader"

    async def _call(self, observation_json: str) -> str:
        from tw2k.agents.prompts import get_system_prompt

        return reply(get_system_prompt(), observation_json)
