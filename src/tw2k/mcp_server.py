"""MCP server for TW2K-AI (Phase H6.1).

Exposes a running ``tw2k serve`` instance as a Model Context Protocol
server so Claude Code, Cursor, or any MCP-aware client can drive a live
match end-to-end — read observations, chat with the copilot, flip modes,
confirm plans, submit manual actions, read memory / safety / what-if.

Design
------

This module is a **thin HTTP proxy**: the MCP server runs alongside the
``tw2k serve`` process (or on the user's dev box) and forwards every tool
call to the already-live FastAPI app over HTTP. That means:

* No match bootstrap inside the MCP server — it does not own a Universe.
  The user still launches ``tw2k serve --human P1`` exactly as they would
  for browser play; the MCP server then just *drives* that match.
* Nothing new to test at the protocol level — ``TwkHttpClient`` is a
  dumb wrapper around ``httpx.AsyncClient`` that hits the same endpoints
  the ``/play`` cockpit already uses. Tests exercise the wrapper against
  an in-process ASGI app the same way ``tests/test_server.py`` does.
* Auth is optional. Set ``TW2K_MCP_TOKEN`` and both the server and the
  HTTP client ship a matching ``Authorization: Bearer …`` header. For
  local dev the default is no-auth because the server binds 127.0.0.1.

The MCP python SDK is a **soft dependency** — this file can be imported
with or without ``pip install mcp``. ``start_mcp_server()`` raises a
friendly RuntimeError if the SDK is missing, and the ``TwkHttpClient``
half is always importable so the unit tests don't need the SDK either.

Tools exposed (14)
------------------

- ``tw2k_list_humans`` — enumerate human slots + status
- ``tw2k_get_observation(player_id)`` — full observation JSON
- ``tw2k_get_copilot_state(player_id)`` — mode, chat, plan, memory, …
- ``tw2k_send_chat(player_id, message)`` — chat with the copilot
- ``tw2k_set_mode(player_id, mode)`` — Manual / Advisory / Delegated / Autopilot
- ``tw2k_confirm_plan(player_id, plan_id)`` — run pending plan
- ``tw2k_cancel_plan(player_id)`` — cancel pending plan or task
- ``tw2k_submit_action(player_id, kind, args)`` — raw engine action
- ``tw2k_get_memory(player_id)`` — full memory snapshot
- ``tw2k_remember(player_id, key, value)`` — add a preference
- ``tw2k_forget(player_id, key)`` — drop a preference
- ``tw2k_get_whatif(player_id)`` — prediction for the pending plan
- ``tw2k_get_safety(player_id)`` — current safety signal
- ``tw2k_get_hints(player_id)`` — UI action hints

Setup (Cursor / Claude Code)
----------------------------

Add to the client's ``mcpServers`` config (paths are examples):

.. code-block:: json

    {
      "mcpServers": {
        "tw2k": {
          "command": "tw2k",
          "args": ["mcp"],
          "env": {
            "TW2K_MCP_BASE_URL": "http://127.0.0.1:8000",
            "TW2K_MCP_TOKEN": ""
          }
        }
      }
    }

Then run ``tw2k serve --human P1`` in one terminal; the client will
auto-spawn ``tw2k mcp`` and route tool calls into the live match.
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Callable
from typing import Any

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
ENV_BASE_URL = "TW2K_MCP_BASE_URL"
ENV_TOKEN = "TW2K_MCP_TOKEN"


# ---------------------------------------------------------------------------
# HTTP client — the real workhorse. Tested directly; MCP is just a shell.
# ---------------------------------------------------------------------------


class TwkHttpClient:
    """Thin async HTTP client for the running ``tw2k serve`` instance.

    Every method returns JSON-deserialised dict/list or raises
    ``httpx.HTTPStatusError`` on non-2xx. Kept deliberately minimal so
    each MCP tool is a one-liner.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        client: httpx.AsyncClient | None = None,
        timeout_s: float = 10.0,
    ) -> None:
        self.base_url = (base_url or os.environ.get(ENV_BASE_URL) or DEFAULT_BASE_URL).rstrip("/")
        self.token = token if token is not None else os.environ.get(ENV_TOKEN, "")
        self._client = client
        self._owns_client = client is None
        self._timeout_s = timeout_s

    def _headers(self) -> dict[str, str]:
        h = {"accept": "application/json"}
        if self.token:
            h["authorization"] = f"Bearer {self.token}"
        return h

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url, timeout=self._timeout_s
            )
        return self._client

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _json(self, method: str, path: str, **kw: Any) -> Any:
        client = await self._get_client()
        r = await client.request(method, path, headers=self._headers(), **kw)
        r.raise_for_status()
        if not r.content:
            return {}
        try:
            return r.json()
        except json.JSONDecodeError:
            return {"raw": r.text}

    # ---- read-only ---------------------------------------------------------

    async def list_humans(self) -> dict[str, Any]:
        return await self._json("GET", "/api/match/humans")

    async def get_observation(self, player_id: str) -> dict[str, Any]:
        return await self._json(
            "GET", "/api/human/observation", params={"player_id": player_id}
        )

    async def get_copilot_state(self, player_id: str) -> dict[str, Any]:
        return await self._json(
            "GET", "/api/copilot/state", params={"player_id": player_id}
        )

    async def get_memory(self, player_id: str) -> dict[str, Any]:
        return await self._json(
            "GET", "/api/copilot/memory", params={"player_id": player_id}
        )

    async def get_whatif(self, player_id: str) -> dict[str, Any]:
        return await self._json(
            "GET", "/api/copilot/whatif", params={"player_id": player_id}
        )

    async def get_safety(self, player_id: str) -> dict[str, Any]:
        return await self._json(
            "GET", "/api/copilot/safety", params={"player_id": player_id}
        )

    async def get_hints(self, player_id: str) -> dict[str, Any]:
        return await self._json(
            "GET", "/api/copilot/hints", params={"player_id": player_id}
        )

    # ---- mutating ----------------------------------------------------------

    async def send_chat(self, player_id: str, message: str) -> dict[str, Any]:
        return await self._json(
            "POST",
            "/api/copilot/chat",
            json={"player_id": player_id, "message": message},
        )

    async def set_mode(self, player_id: str, mode: str) -> dict[str, Any]:
        return await self._json(
            "POST",
            "/api/copilot/mode",
            json={"player_id": player_id, "mode": mode},
        )

    async def confirm_plan(self, player_id: str, plan_id: str) -> dict[str, Any]:
        return await self._json(
            "POST",
            "/api/copilot/confirm",
            json={"player_id": player_id, "plan_id": plan_id},
        )

    async def cancel_plan(self, player_id: str) -> dict[str, Any]:
        return await self._json(
            "POST", "/api/copilot/cancel", json={"player_id": player_id}
        )

    async def submit_action(
        self, player_id: str, kind: str, args: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        body = {
            "player_id": player_id,
            "action": {"kind": kind, "args": dict(args or {})},
        }
        return await self._json("POST", "/api/human/action", json=body)

    async def remember(self, player_id: str, key: str, value: str) -> dict[str, Any]:
        return await self._json(
            "POST",
            "/api/copilot/memory/remember",
            json={"player_id": player_id, "key": key, "value": value},
        )

    async def forget(self, player_id: str, key: str) -> dict[str, Any]:
        return await self._json(
            "POST",
            "/api/copilot/memory/forget",
            json={"player_id": player_id, "key": key},
        )


# ---------------------------------------------------------------------------
# Tool registry — structured so we can present metadata to both the MCP SDK
# and our own tests without parsing docstrings.
# ---------------------------------------------------------------------------


ToolFn = Callable[[TwkHttpClient, dict[str, Any]], Any]


async def _tool_list_humans(c: TwkHttpClient, _: dict[str, Any]) -> Any:
    return await c.list_humans()


async def _tool_get_observation(c: TwkHttpClient, a: dict[str, Any]) -> Any:
    return await c.get_observation(a["player_id"])


async def _tool_get_copilot_state(c: TwkHttpClient, a: dict[str, Any]) -> Any:
    return await c.get_copilot_state(a["player_id"])


async def _tool_send_chat(c: TwkHttpClient, a: dict[str, Any]) -> Any:
    return await c.send_chat(a["player_id"], a["message"])


async def _tool_set_mode(c: TwkHttpClient, a: dict[str, Any]) -> Any:
    return await c.set_mode(a["player_id"], a["mode"])


async def _tool_confirm_plan(c: TwkHttpClient, a: dict[str, Any]) -> Any:
    return await c.confirm_plan(a["player_id"], a["plan_id"])


async def _tool_cancel_plan(c: TwkHttpClient, a: dict[str, Any]) -> Any:
    return await c.cancel_plan(a["player_id"])


async def _tool_submit_action(c: TwkHttpClient, a: dict[str, Any]) -> Any:
    return await c.submit_action(a["player_id"], a["kind"], a.get("args") or {})


async def _tool_get_memory(c: TwkHttpClient, a: dict[str, Any]) -> Any:
    return await c.get_memory(a["player_id"])


async def _tool_remember(c: TwkHttpClient, a: dict[str, Any]) -> Any:
    return await c.remember(a["player_id"], a["key"], a["value"])


async def _tool_forget(c: TwkHttpClient, a: dict[str, Any]) -> Any:
    return await c.forget(a["player_id"], a["key"])


async def _tool_get_whatif(c: TwkHttpClient, a: dict[str, Any]) -> Any:
    return await c.get_whatif(a["player_id"])


async def _tool_get_safety(c: TwkHttpClient, a: dict[str, Any]) -> Any:
    return await c.get_safety(a["player_id"])


async def _tool_get_hints(c: TwkHttpClient, a: dict[str, Any]) -> Any:
    return await c.get_hints(a["player_id"])


def _player_id_param() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "player_id": {
                "type": "string",
                "description": "Human slot id, e.g. 'P1'.",
            }
        },
        "required": ["player_id"],
        "additionalProperties": False,
    }


MCP_TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "tw2k_list_humans",
        "description": "List all human player slots in the live match and whether each is awaiting input.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "fn": _tool_list_humans,
    },
    {
        "name": "tw2k_get_observation",
        "description": "Get the full Observation JSON for a human player (sector, ship, cargo, adjacents, action_hint, …).",
        "input_schema": _player_id_param(),
        "fn": _tool_get_observation,
    },
    {
        "name": "tw2k_get_copilot_state",
        "description": "Get the copilot session state (mode, chat, pending_plan, active_task, memory, whatif).",
        "input_schema": _player_id_param(),
        "fn": _tool_get_copilot_state,
    },
    {
        "name": "tw2k_send_chat",
        "description": "Send a natural-language utterance to the copilot (same path as the /play chat box).",
        "input_schema": {
            "type": "object",
            "properties": {
                "player_id": {"type": "string"},
                "message": {"type": "string", "description": "Utterance text."},
            },
            "required": ["player_id", "message"],
            "additionalProperties": False,
        },
        "fn": _tool_send_chat,
    },
    {
        "name": "tw2k_set_mode",
        "description": "Set the copilot mode for a player. Valid modes: manual, advisory, delegated, autopilot.",
        "input_schema": {
            "type": "object",
            "properties": {
                "player_id": {"type": "string"},
                "mode": {
                    "type": "string",
                    "enum": ["manual", "advisory", "delegated", "autopilot"],
                },
            },
            "required": ["player_id", "mode"],
            "additionalProperties": False,
        },
        "fn": _tool_set_mode,
    },
    {
        "name": "tw2k_confirm_plan",
        "description": "Confirm a pending plan (run the tool calls it contains). Use the id from copilot_state.pending_plan.id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "player_id": {"type": "string"},
                "plan_id": {"type": "string"},
            },
            "required": ["player_id", "plan_id"],
            "additionalProperties": False,
        },
        "fn": _tool_confirm_plan,
    },
    {
        "name": "tw2k_cancel_plan",
        "description": "Cancel the currently pending plan or active task for a player.",
        "input_schema": _player_id_param(),
        "fn": _tool_cancel_plan,
    },
    {
        "name": "tw2k_submit_action",
        "description": "Submit a raw engine action (same shape as manual /play clicks). kind in {warp, scan, probe, trade, land_planet, liftoff, hail, broadcast, wait, …}.",
        "input_schema": {
            "type": "object",
            "properties": {
                "player_id": {"type": "string"},
                "kind": {"type": "string"},
                "args": {"type": "object", "additionalProperties": True},
            },
            "required": ["player_id", "kind"],
            "additionalProperties": False,
        },
        "fn": _tool_submit_action,
    },
    {
        "name": "tw2k_get_memory",
        "description": "Get the player's copilot memory (prefs, learned rules, favorite sectors, stats).",
        "input_schema": _player_id_param(),
        "fn": _tool_get_memory,
    },
    {
        "name": "tw2k_remember",
        "description": "Store a copilot preference for a player (e.g. key='favorite commodity', value='organics').",
        "input_schema": {
            "type": "object",
            "properties": {
                "player_id": {"type": "string"},
                "key": {"type": "string"},
                "value": {"type": "string"},
            },
            "required": ["player_id", "key", "value"],
            "additionalProperties": False,
        },
        "fn": _tool_remember,
    },
    {
        "name": "tw2k_forget",
        "description": "Remove a copilot preference for a player.",
        "input_schema": {
            "type": "object",
            "properties": {
                "player_id": {"type": "string"},
                "key": {"type": "string"},
            },
            "required": ["player_id", "key"],
            "additionalProperties": False,
        },
        "fn": _tool_forget,
    },
    {
        "name": "tw2k_get_whatif",
        "description": "Get the what-if prediction (credit / turn / cargo / risk) for the currently pending plan, if any.",
        "input_schema": _player_id_param(),
        "fn": _tool_get_whatif,
    },
    {
        "name": "tw2k_get_safety",
        "description": "Get the current safety signal (ok / notice / warning / critical) for the player.",
        "input_schema": _player_id_param(),
        "fn": _tool_get_safety,
    },
    {
        "name": "tw2k_get_hints",
        "description": "Get UI action hints (button tooltips + next-move suggestions) for a player.",
        "input_schema": _player_id_param(),
        "fn": _tool_get_hints,
    },
]


async def dispatch_tool(
    tool_name: str, arguments: dict[str, Any], *, client: TwkHttpClient
) -> Any:
    """Dispatch a named MCP tool call to its HTTP implementation.

    Pure helper used by the MCP SDK adapter *and* by the unit tests
    (which don't need the SDK installed). Raises ``KeyError`` for
    unknown tool names.
    """
    for spec in MCP_TOOL_SPECS:
        if spec["name"] == tool_name:
            return await spec["fn"](client, arguments)
    raise KeyError(f"unknown tool {tool_name!r}")


def tool_names() -> list[str]:
    return [spec["name"] for spec in MCP_TOOL_SPECS]


# ---------------------------------------------------------------------------
# MCP SDK adapter — soft-imports `mcp`. Only used by the CLI entry point.
# ---------------------------------------------------------------------------


def start_mcp_server(
    *,
    base_url: str | None = None,
    token: str | None = None,
) -> None:
    """Blocking stdio MCP server entry point. Requires ``pip install mcp``.

    Spawned by ``tw2k mcp``. Every tool call is forwarded into a shared
    ``TwkHttpClient`` aimed at the running ``tw2k serve`` instance.
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as e:  # pragma: no cover - branch needs mcp installed
        raise RuntimeError(
            "The 'mcp' package is not installed. Install with "
            "`pip install mcp` to enable `tw2k mcp`."
        ) from e

    server = FastMCP("tw2k-ai")
    client = TwkHttpClient(base_url=base_url, token=token)

    def _register(spec: dict[str, Any]) -> None:
        fn = spec["fn"]
        name = spec["name"]
        description = spec["description"]

        @server.tool(name=name, description=description)
        async def _handler(**kwargs: Any) -> Any:  # type: ignore[misc]
            return await fn(client, kwargs)

        _handler.__name__ = name

    for spec in MCP_TOOL_SPECS:
        _register(spec)

    try:
        asyncio.run(server.run_stdio_async())
    finally:
        asyncio.run(client.aclose())


__all__ = [
    "DEFAULT_BASE_URL",
    "ENV_BASE_URL",
    "ENV_TOKEN",
    "MCP_TOOL_SPECS",
    "TwkHttpClient",
    "dispatch_tool",
    "start_mcp_server",
    "tool_names",
]
