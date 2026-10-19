"""Lobby secrets, guest cookies, client IPs, rate limits and new-game validation."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import re
import secrets
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GUEST_COOKIE = "gwc_guest"
WATCH_COOKIE_PREFIX = "gwc_w_"
GUEST_COOKIE_MAX_AGE = 60 * 86400

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}
_PROXY_HEADERS = ("cf-connecting-ip", "cf-ray", "x-forwarded-for", "forwarded", "x-real-ip")


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Secrets:
    """One master key on disk; every per-game secret is derived from it, so none is stored."""

    def __init__(self, root: Path) -> None:
        path = Path(root) / "lobby.key"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            tmp = path.with_suffix(".tmp")
            tmp.write_text(secrets.token_hex(32), encoding="ascii")
            tmp.replace(path)
        self._key = bytes.fromhex(path.read_text(encoding="ascii").strip())

    def _derive(self, purpose: str, gid: str, n: int = 32) -> str:
        return hmac.new(self._key, f"{purpose}:{gid}".encode(), hashlib.sha256).hexdigest()[: n * 2]

    def lobby_secret(self, gid: str) -> str:
        return self._derive("lobby", gid)

    def spectator_token(self, gid: str) -> str:
        return self._derive("spectator", gid)

    def watch_key(self, gid: str) -> str:
        return self._derive("watch", gid, 12)

    def watch_cookie(self, gid: str) -> str:
        return self._derive("watch-cookie", gid)

    def ip_tag(self, ip: str) -> str:
        return self._derive("ip", ip, 4)


def new_guest_cookie() -> str:
    return secrets.token_urlsafe(32)


def guest_id(cookie: str | None) -> str | None:
    if not cookie or len(cookie) < 40 or len(cookie) > 64:
        return None
    return sha256_hex(cookie)


def new_seat_token() -> str:
    return secrets.token_urlsafe(32)


def is_loopback(host: str | None) -> bool:
    if not host:
        return False
    if host in _LOOPBACK:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def client_ip(headers, peer: str | None) -> str:
    """The real player IP: Cloudflare's header when the request came through the local tunnel."""
    if is_loopback(peer):
        cf = (headers.get("cf-connecting-ip") or "").strip()
        if cf:
            try:
                return str(ipaddress.ip_address(cf))
            except ValueError:
                return "invalid"
    return peer or "unknown"


def is_local_admin(headers, peer: str | None) -> bool:
    """Loopback and not relayed by the tunnel (tunnel traffic also arrives from 127.0.0.1)."""
    if not is_loopback(peer):
        return False
    return not any(headers.get(h) for h in _PROXY_HEADERS)


def is_https(headers, scheme: str) -> bool:
    return scheme == "https" or (headers.get("x-forwarded-proto") or "").lower() == "https" or bool(
        headers.get("cf-visitor") and "https" in headers.get("cf-visitor", "")
    )


class RateLimiter:
    """Sliding-window counters keyed by (bucket, who)."""

    def __init__(self, clock=time.monotonic) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = {}
        self._lock = threading.Lock()
        self._clock = clock

    def allow(self, bucket: str, who: str, limit: int, window_s: float) -> bool:
        now = self._clock()
        key = (bucket, who)
        with self._lock:
            q = self._hits.setdefault(key, deque())
            while q and now - q[0] >= window_s:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            if len(self._hits) > 20000:
                self._hits = {k: v for k, v in self._hits.items() if v and now - v[-1] < 3600}
            return True


# --- new-game form -------------------------------------------------------------

DAY_PRESETS = {"10m": 600, "30m": 1800, "1h": 3600, "24h": 86400}
UNIVERSE_SIZES = (200, 500, 1000, 2000)
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 '._-]{0,39}$")
_STARTS = ("v311", "classic")


@dataclass
class GameForm:
    name: str
    rules: str = "v311"
    universe_size: int = 1000
    max_days: int = 30
    turns_per_day: int = 250
    starting_package: str = "v311"
    bots: int = 2
    ferrengi: bool = True
    day: str = "30m"
    humans: int = 1
    listed: bool = True
    day_seconds: int = 1800
    # None is Original: the worker does not pass an override.
    starting_credits_override: int | None = None
    home_planet_name: str | None = None
    tournament_lockout: str | None = None
    tournament_kill_threshold: int | None = None

    def settings(self) -> dict[str, Any]:
        out = {
            "rules": self.rules,
            "universe_size": self.universe_size,
            "max_days": self.max_days,
            "turns_per_day": self.turns_per_day,
            "starting_package": self.starting_package,
            "bots": self.bots,
            "ferrengi": self.ferrengi,
            "day": self.day,
            "day_seconds": self.day_seconds,
            "humans": self.humans,
            "seed": secrets.randbelow(2**31 - 1) + 1,
        }
        if self.starting_credits_override is not None:
            out["starting_credits_override"] = self.starting_credits_override
        if self.home_planet_name:
            out["home_planet_name"] = self.home_planet_name
        if self.tournament_lockout and self.tournament_kill_threshold is not None:
            out["tournament_lockout"] = self.tournament_lockout
            out["tournament_kill_threshold"] = self.tournament_kill_threshold
        return out


class FormError(ValueError):
    pass


def _as_int(data: dict, key: str, default: int, lo: int, hi: int) -> int:
    raw = data.get(key, default)
    if isinstance(raw, bool):
        raise FormError(f"{key} must be a number")
    try:
        val = int(str(raw).strip())
    except (TypeError, ValueError):
        raise FormError(f"{key} must be a whole number") from None
    if not lo <= val <= hi:
        raise FormError(f"{key} must be between {lo} and {hi}")
    return val


def _as_bool(data: dict, key: str, default: bool) -> bool:
    raw = data.get(key, default)
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in ("1", "true", "on", "yes"):
        return True
    if text in ("0", "false", "off", "no", ""):
        return False
    raise FormError(f"{key} must be on or off")


_ALLOWED = {"name", "rules", "universe_size", "max_days", "turns_per_day", "starting_package", "bots", "ferrengi",
            "day", "humans", "listed", "visibility", "starting_credits", "starting_credits_custom",
            "home_planet_name", "tournament_lockout", "tournament_kill_threshold"}

_CREDITS_MAX = 10_000_000


def home_planet_name(raw) -> str | None:
    """1 to 30 characters, or None when the trader leaves it blank."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if len(text) > 30 or any(ord(ch) < 32 for ch in text):
        raise FormError("home planet name must be 1 to 30 characters")
    return text


def starting_credits_line(override: int | None, original: int) -> str:
    """Same sentence the cockpit and the worker show."""
    if override is None:
        return f"Starting credits: {int(original):,} (original)"
    return f"Starting credits: {int(override):,} (test setting)"


def credits_phrase(settings: dict) -> str:
    """Lobby card line. v3.11 original is 300; classic original is 20,000."""
    override = settings.get("starting_credits_override")
    original = 300 if settings.get("rules") == "v311" or settings.get("starting_package") == "v311" else 20_000
    return starting_credits_line(None if override is None else int(override), original)


def _credits_override(data: dict) -> int | None:
    """Original (missing or 'original') is no override. Anything else is 0..10,000,000."""
    if "starting_credits" not in data and "starting_credits_custom" not in data:
        return None
    raw = data.get("starting_credits", "original")
    if isinstance(raw, bool):
        raise FormError("starting credits must be a whole number")
    if raw is None:
        return None
    text = str(raw).strip().lower().replace(",", "").replace("_", "")
    if text in ("", "original", "none"):
        return None
    if text == "custom":
        if "starting_credits_custom" not in data or str(data.get("starting_credits_custom", "")).strip() == "":
            raise FormError("Type a starting credit amount.")
        return _as_int(data, "starting_credits_custom", 0, 0, _CREDITS_MAX)
    if isinstance(raw, float) or "." in text:
        raise FormError("starting credits must be a whole number")
    try:
        val = int(text)
    except ValueError:
        raise FormError("starting credits must be a whole number") from None
    if not 0 <= val <= _CREDITS_MAX:
        raise FormError(f"starting credits must be between 0 and {_CREDITS_MAX}")
    return val


def _tournament(data: dict) -> tuple[str | None, int | None]:
    """Off unless the form names a lockout and a maximum. Blank stays off."""
    if "tournament_lockout" not in data and "tournament_kill_threshold" not in data:
        return None, None
    text = str(data.get("tournament_lockout") or "").strip().lower().replace(" ", "_").replace("-", "_")
    if text in ("", "none", "off", "n/a", "na"):
        return None, None
    aliases = {"deaths": "deaths", "deaths_only": "deaths", "pods_and_deaths": "pods_and_deaths"}
    if text not in aliases:
        raise FormError("tournament lockout must be none, deaths, or pods and deaths")
    if str(data.get("tournament_kill_threshold") or "").strip() == "":
        raise FormError("Type a maximum times blown up.")
    return aliases[text], _as_int(data, "tournament_kill_threshold", 1, 1, 99)


def parse_game_form(data: dict, presets: dict[str, int] | None = None) -> GameForm:
    presets = presets or DAY_PRESETS
    unknown = set(data) - _ALLOWED
    if unknown:
        raise FormError(f"unknown field: {sorted(unknown)[0]}")
    name = str(data.get("name", "")).strip()
    if not _NAME_RE.match(name):
        raise FormError("game name: 1-40 letters, numbers, spaces or . _ ' -")
    rules = str(data.get("rules", "v311")).strip()
    if rules not in ("v311", "legacy"):
        raise FormError("rules must be v311 or legacy")
    size = _as_int(data, "universe_size", 1000, 200, 2000)
    if size not in UNIVERSE_SIZES:
        raise FormError(f"universe size must be one of {', '.join(map(str, UNIVERSE_SIZES))}")
    start = str(data.get("starting_package", "v311" if rules == "v311" else "classic")).strip()
    if start not in _STARTS:
        raise FormError("starting package must be v311 or classic")
    if rules == "v311" and start != "v311":
        raise FormError("v3.11 rules always use the v3.11 starting package")
    day = str(data.get("day", "30m")).strip()
    if day not in presets:
        raise FormError(f"day length must be one of {', '.join(presets)}")
    vis = data.get("visibility")
    listed = _as_bool(data, "listed", True) if vis is None else str(vis).strip() == "listed"
    if vis is not None and str(vis).strip() not in ("listed", "link"):
        raise FormError("visibility must be listed or link")
    lockout, blows = _tournament(data)
    return GameForm(
        name=name,
        rules=rules,
        universe_size=size,
        max_days=_as_int(data, "max_days", 30, 1, 365),
        turns_per_day=_as_int(data, "turns_per_day", 250, 20, 2000),
        starting_package=start,
        bots=_as_int(data, "bots", 2, 0, 5),
        ferrengi=_as_bool(data, "ferrengi", True),
        day=day,
        humans=_as_int(data, "humans", 1, 1, 4),
        listed=listed,
        day_seconds=int(presets[day]),
        starting_credits_override=_credits_override(data),
        home_planet_name=home_planet_name(data.get("home_planet_name")),
        tournament_lockout=lockout,
        tournament_kill_threshold=blows,
    )


def mask_path(path: str) -> str:
    """Strip query strings (claim tokens) from anything that is logged."""
    return path.split("?", 1)[0]
