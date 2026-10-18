"""Reverse proxy for /g/<id>/... (HTTP streamed, websockets pumped both ways)."""

from __future__ import annotations

import asyncio
from http.cookies import SimpleCookie

import httpx
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.websockets import WebSocket, WebSocketDisconnect

from .worker import LOBBY_HEADER

_HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers",
        "transfer-encoding", "upgrade", "host", "content-length"}
_DROP_REQ = _HOP | {LOBBY_HEADER, "cf-connecting-ip", "x-forwarded-for", "forwarded", "x-real-ip"}
_DROP_WS = _DROP_REQ | {"sec-websocket-key", "sec-websocket-version", "sec-websocket-extensions",
                        "sec-websocket-accept", "sec-websocket-protocol", "origin"}
LOBBY_COOKIE_PREFIX = "gwc_"


def strip_lobby_cookies(raw: str) -> str:
    """Pass the game its own cookies only; the guest and watch cookies stay with the lobby."""
    if not raw:
        return ""
    jar: SimpleCookie = SimpleCookie()
    try:
        jar.load(raw)
    except Exception:
        return ""
    return "; ".join(f"{k}={m.value}" for k, m in jar.items() if not k.startswith(LOBBY_COOKIE_PREFIX))


def upstream_headers(headers, extra: dict[str, str] | None, *, drop: set[str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for k, v in headers.items():
        key = k.lower()
        if key in drop:
            continue
        if key == "cookie":
            v = strip_lobby_cookies(v)
            if not v:
                continue
        if extra and key in extra:
            continue
        out.append((key, v))
    for k, v in (extra or {}).items():
        out.append((k.lower(), v))
    return out


class Proxy:
    def __init__(self, *, timeout_s: float = 90.0) -> None:
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(timeout_s, connect=5.0), follow_redirects=False)

    async def close(self) -> None:
        await self.client.aclose()

    async def http(self, request: Request, port: int, subpath: str, *, body: bytes,
                   extra: dict[str, str] | None = None) -> Response:
        url = f"http://127.0.0.1:{port}/{subpath}"
        query = request.url.query
        if query:
            url += "?" + query
        req = self.client.build_request(request.method, url, content=body,
                                        headers=upstream_headers(request.headers, extra, drop=_DROP_REQ))
        try:
            upstream = await self.client.send(req, stream=True)
        except httpx.HTTPError:
            return Response('{"detail":"this game is not answering right now"}', status_code=502,
                            media_type="application/json")
        headers = [(k, v) for k, v in upstream.headers.multi_items() if k.lower() not in _HOP]
        resp = StreamingResponse(upstream.aiter_raw(), status_code=upstream.status_code,
                                 background=BackgroundTask(upstream.aclose))
        resp.raw_headers = [(k.encode("latin-1"), v.encode("latin-1")) for k, v in headers]
        if "content-length" in upstream.headers and "content-encoding" not in upstream.headers:
            resp.raw_headers.append((b"content-length", upstream.headers["content-length"].encode("latin-1")))
        return resp

    async def websocket(self, ws: WebSocket, port: int, subpath: str, *, extra: dict[str, str] | None = None) -> None:
        from websockets.asyncio.client import connect
        from websockets.exceptions import ConnectionClosed, InvalidStatus

        url = f"ws://127.0.0.1:{port}/{subpath}"
        if ws.url.query:
            url += "?" + ws.url.query
        try:
            upstream = await connect(url, additional_headers=upstream_headers(ws.headers, extra, drop=_DROP_WS),
                                     open_timeout=10, max_size=8 * 1024 * 1024)
        except (InvalidStatus, OSError, asyncio.TimeoutError):
            await ws.close(code=1008)
            return
        await ws.accept()

        async def client_to_game() -> None:
            try:
                while True:
                    msg = await ws.receive()
                    if msg["type"] == "websocket.disconnect":
                        return
                    if msg.get("text") is not None:
                        await upstream.send(msg["text"])
                    elif msg.get("bytes") is not None:
                        await upstream.send(msg["bytes"])
            except (WebSocketDisconnect, ConnectionClosed, RuntimeError):
                return

        async def game_to_client() -> None:
            try:
                async for data in upstream:
                    if isinstance(data, bytes):
                        await ws.send_bytes(data)
                    else:
                        await ws.send_text(data)
            except (ConnectionClosed, WebSocketDisconnect, RuntimeError):
                return

        tasks = [asyncio.create_task(client_to_game()), asyncio.create_task(game_to_client())]
        try:
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for t in tasks:
                t.cancel()
            await upstream.close()
            try:
                await ws.close()
            except RuntimeError:
                pass
