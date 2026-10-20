"""Public links for a lobby reached through a proxy.

A Cloudflare quick tunnel terminates https and connects to http://127.0.0.1.
Pages and websockets have to stay on the address the browser opened.
"""

from __future__ import annotations

import re
from urllib.parse import quote, urlsplit

from .security import is_https, is_loopback

_QUOTED_LOOPBACK = re.compile(
    r"""(?P<q>["'`])(?P<scheme>https?|wss?)://(?:127\.0\.0\.1|localhost|\[::1\])(?::\d+)?(?P<rest>/[^"'`]*)?(?P=q)"""
)


def host_only(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = "http://" + raw
    return (urlsplit(raw).hostname or "").lower()


def request_origin(headers, scheme: str, netloc: str = "") -> str:
    """scheme://host the browser should keep.

    A tunnel often delivers the request as http://127.0.0.1 while the public
    name is in Host or X-Forwarded-Host and the scheme is in X-Forwarded-Proto.
    """
    raw_host = _header(headers, "host") or netloc
    forwarded = _header(headers, "x-forwarded-host").split(",")[0].strip()
    host = raw_host
    if forwarded and is_loopback(host_only(raw_host)):
        host = forwarded
    out = "https" if is_https(headers, scheme or "http") else (scheme or "http")
    return f"{out}://{host}"


def lobby_link(origin: str) -> str:
    return origin.rstrip("/") + "/"


def seat_link(origin: str, game_id: str, seat: str, token: str) -> str:
    """Cockpit link. Query keeps seat, token, and layout=redesign."""
    base = origin.rstrip("/")
    seat_q = quote(seat, safe="")
    token_q = quote(token, safe="")
    return f"{base}/g/{game_id}/bot?seat={seat_q}&token={token_q}&layout=redesign"


def websocket_url(page: str, path: str = "/ws") -> str:
    """ws:// on an http page, wss:// on an https page, same host as the page."""
    parts = urlsplit(page)
    scheme = "wss" if parts.scheme == "https" else "ws"
    if not path.startswith("/"):
        path = "/" + path
    return f"{scheme}://{parts.netloc}{path}"


def rebase_onto(page: str, target: str) -> str:
    """Move a loopback or same-host URL onto the page the browser has open."""
    if not target:
        return target
    page_parts = urlsplit(page)
    if target.startswith("/") and not target.startswith("//"):
        return f"{page_parts.scheme}://{page_parts.netloc}{target}"
    got = urlsplit(target)
    if got.scheme not in ("http", "https", "ws", "wss"):
        return target
    same = (got.hostname or "").lower() == (page_parts.hostname or "").lower()
    if not is_loopback(got.hostname) and not same:
        return target
    path = got.path or "/"
    query = f"?{got.query}" if got.query else ""
    frag = f"#{got.fragment}" if got.fragment else ""
    if got.scheme in ("ws", "wss"):
        scheme = "wss" if page_parts.scheme == "https" else "ws"
    else:
        scheme = "https" if page_parts.scheme == "https" else (page_parts.scheme or "http")
    return f"{scheme}://{page_parts.netloc}{path}{query}{frag}"


def loopback_to_path(value: str) -> str:
    """http://127.0.0.1:8099/g/ab/bot?seat=P1&token=t -> that path, query, and fragment.

    A relative path stays as it is, so the browser keeps the page origin.
    A public absolute URL stays as it is.
    """
    if "://" not in (value or ""):
        return value
    got = urlsplit(value)
    if got.scheme not in ("http", "https", "ws", "wss"):
        return value
    if not is_loopback(got.hostname):
        return value
    path = got.path or "/"
    query = f"?{got.query}" if got.query else ""
    frag = f"#{got.fragment}" if got.fragment else ""
    return f"{path}{query}{frag}"


def rewrite_embedded_urls(text: str, base: str = "") -> str:
    """Quoted loopback URLs in a served page follow the browser, not 127.0.0.1."""

    def sub(match: re.Match[str]) -> str:
        rest = match.group("rest") or "/"
        path = rest
        if base and path.startswith("/") and not path.startswith("//") and not path.startswith(base + "/"):
            path = base + path
        if match.group("scheme") in ("ws", "wss"):
            return "(location.protocol==='https:'?'wss:':'ws:')+'//'+location.host+'" + path + "'"
        return f"{match.group('q')}{path}{match.group('q')}"

    return _QUOTED_LOOPBACK.sub(sub, text)


def _header(headers, name: str) -> str:
    if not headers:
        return ""
    getter = getattr(headers, "get", None)
    if getter is None:
        return ""
    value = getter(name)
    if value:
        return str(value).strip()
    value = getter(name.lower())
    return str(value).strip() if value else ""
