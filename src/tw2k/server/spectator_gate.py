"""Spectator gate - keep whole-galaxy intel off a public URL (Parity S1, F6).

The spectator UI (`/`, `/state`, `/events`, `/ws`, ...) shows every sector,
every ship and every agent thought. On a LAN that is fine; on a hosted URL
it hands any competitor an unfogged map. When ``TW2K_SPECTATOR_TOKEN`` is
set, this ASGI middleware requires that token for every *spectator /
operator* route while leaving the per-seat, token-authenticated cockpit
surface (`/bot`, `/harness/v1/*`, `/static/*`) untouched.

Accepted credentials (any one):

* ``Authorization: Bearer <token>`` header
* ``?token=<token>`` query string
* ``tw2k_spectator=<token>`` cookie - set by visiting ``/spectate?token=<token>``
  once, which then redirects to ``/`` so a browser (and its WebSocket) works
  without pasting anything again.

Unset token = gate disabled (legacy behaviour; default for local dev).
"""

from __future__ import annotations

import hmac
import os
from collections.abc import Awaitable, Callable
from http.cookies import SimpleCookie
from typing import Any
from urllib.parse import parse_qs

ENV_TOKEN = "TW2K_SPECTATOR_TOKEN"
COOKIE_NAME = "tw2k_spectator"
LOGIN_PATH = "/spectate"

# Paths that are always open (per-seat auth or static assets).
_OPEN_PREFIXES = ("/static/", "/harness/")
_OPEN_EXACT = {"/bot", LOGIN_PATH, "/healthz"}

# Everything else that shows or changes global match state is gated.
_GATED_EXACT = {"/", "/state", "/events", "/history", "/highlights", "/ws", "/play"}
_GATED_PREFIXES = ("/control/", "/api/")

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]


def spectator_token() -> str:
    return (os.environ.get(ENV_TOKEN) or "").strip()


def is_gated_path(path: str) -> bool:
    if path in _OPEN_EXACT or path.startswith(_OPEN_PREFIXES):
        return False
    if path in _GATED_EXACT or path.startswith(_GATED_PREFIXES):
        return True
    return False


def _headers(scope: Scope) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in scope.get("headers") or []:
        out[k.decode("latin-1").lower()] = v.decode("latin-1")
    return out


def _presented_token(scope: Scope) -> str:
    h = _headers(scope)
    auth = h.get("authorization", "")
    scheme, _, tok = auth.partition(" ")
    if scheme.lower() == "bearer" and tok.strip():
        return tok.strip()
    qs = parse_qs((scope.get("query_string") or b"").decode("latin-1"))
    if qs.get("token"):
        return qs["token"][0].strip()
    raw_cookie = h.get("cookie", "")
    if raw_cookie:
        jar: SimpleCookie = SimpleCookie()
        try:
            jar.load(raw_cookie)
        except Exception:
            return ""
        m = jar.get(COOKIE_NAME)
        if m is not None:
            return m.value.strip()
    return ""


def _ok(presented: str, expected: str) -> bool:
    return bool(presented) and hmac.compare_digest(presented.encode("utf-8"), expected.encode("utf-8"))


class SpectatorGate:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        expected = spectator_token()
        path = scope.get("path") or "/"
        if not expected:
            # Gate disabled. /spectate still works as a plain redirect.
            if path == LOGIN_PATH and scope["type"] == "http":
                await _redirect(send, "/")
                return
            await self.app(scope, receive, send)
            return

        presented = _presented_token(scope)

        if path == LOGIN_PATH and scope["type"] == "http":
            if _ok(presented, expected):
                await _redirect(send, "/", set_cookie=f"{COOKIE_NAME}={presented}; Path=/; HttpOnly; SameSite=Lax")
            else:
                await _json(send, 401, {"detail": "spectator token required: open /spectate?token=<token>"})
            return

        if not is_gated_path(path) or _ok(presented, expected):
            await self.app(scope, receive, send)
            return

        if scope["type"] == "websocket":
            # Closing before accept makes uvicorn answer the handshake with 403.
            await send({"type": "websocket.close", "code": 1008})
            return
        await _json(send, 401, {"detail": "spectator token required (TW2K_SPECTATOR_TOKEN is set)"})


async def _json(send: Send, status: int, body: dict[str, Any]) -> None:
    import json

    raw = json.dumps(body).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(raw)).encode("latin-1")),
                (b"cache-control", b"no-store"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": raw})


async def _redirect(send: Send, location: str, *, set_cookie: str | None = None) -> None:
    headers = [(b"location", location.encode("latin-1")), (b"content-length", b"0")]
    if set_cookie:
        headers.append((b"set-cookie", set_cookie.encode("latin-1")))
    await send({"type": "http.response.start", "status": 303, "headers": headers})
    await send({"type": "http.response.body", "body": b""})
