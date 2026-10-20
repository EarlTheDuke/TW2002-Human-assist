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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from ..engine import constants as K

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
    # None is Original (250 on the lobby form). A number replaces every seat.
    turns_per_day_override: int | None = None
    # Off unless the new-game form sends it. Missing stays today's start.
    hold_until_human: bool = False
    # NOTE 100. Zero unless LOBBY_AI_SEAT_MODE is on and the form asked for seats.
    # The key and the endpoint never enter settings().
    ai_opponents: int = 0
    ai_brain: str = "heuristic"
    ai_key: str = field(default="", repr=False)
    ai_endpoint: str = field(default="", repr=False)
    # NOTE 128. Off unless AI_COCKPIT_SEAT_MODE is on and the form asked for the seat.
    # The provider and the model are stored. A key is never a form field here.
    ai_cockpit: bool = False
    ai_cockpit_provider: str = "scripted"
    ai_cockpit_model: str = ""
    ai_cockpit_count: int = 1
    ai_cockpit_level: str = "hard"
    # NOTE 131. None is fast test days and is left out of settings. "full" is a
    # full-length game. The field exists only while the process flag is v311.
    game_length: str | None = None

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
        if self.turns_per_day_override is not None:
            out["turns_per_day_override"] = self.turns_per_day_override
        if self.hold_until_human:
            out["hold_until_human"] = True
        if self.ai_opponents:
            out["ai_opponents"] = int(self.ai_opponents)
            out["ai_brain"] = self.ai_brain if self.ai_brain in ("heuristic", "llm") else "heuristic"
        if self.ai_cockpit:
            out["ai_cockpit"] = True
            out["ai_cockpit_provider"] = self.ai_cockpit_provider
            out["ai_cockpit_model"] = self.ai_cockpit_model
            out["ai_cockpit_count"] = int(self.ai_cockpit_count)
            out["ai_cockpit_level"] = self.ai_cockpit_level
        if self.game_length == "full":
            out["game_length"] = "full"
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
            "home_planet_name", "turns_per_day_custom", "hold_until_human"}

_TURNS_MIN = 50
_TURNS_MAX = 5_000
# Accepted only while LOBBY_AI_SEAT_MODE is on. Off, these stay unknown fields.
_AI_FIELDS = {"ai_opponents", "ai_brain", "ai_key", "ai_endpoint"}
# Accepted only while AI_COCKPIT_SEAT_MODE is on. Off, these stay unknown fields.
_COCKPIT_FIELDS = {
    "ai_cockpit", "ai_cockpit_provider", "ai_cockpit_model", "ai_cockpit_count", "ai_cockpit_level",
}
_COCKPIT_PROVIDERS = {"scripted", "grok", "openai", "anthropic"}
_COCKPIT_LEVELS = {"easy", "normal", "hard"}


def ai_label(brain: str) -> str:
    """The name a human sees for an AI seat. Rankings, the end screen and the trader list use it."""
    return "AI (LLM)" if brain == "llm" else "AI (heuristic)"


def _allowed_fields() -> set[str]:
    fields = set(_ALLOWED)
    if K.lobby_ai_seat_on():
        fields |= _AI_FIELDS
    if K.ai_cockpit_seat_on():
        fields |= _COCKPIT_FIELDS
    if K.full_length_turn_limits_on():
        fields.add("game_length")
    return fields


def _cockpit_provider(raw) -> str:
    text = str(raw or "scripted").strip().lower()
    if text == "xai":
        text = "grok"
    if text not in _COCKPIT_PROVIDERS:
        raise FormError("AI cockpit provider must be scripted, grok, openai, or anthropic")
    return text


def _cockpit_level(raw) -> str:
    text = str(raw or "hard").strip().lower()
    if text not in _COCKPIT_LEVELS:
        raise FormError("AI cockpit level must be easy, normal, or hard")
    return text


def _cockpit_model(raw) -> str:
    text = str(raw or "").strip()
    if len(text) > 80 or any(ord(ch) < 32 for ch in text):
        raise FormError("model name must be 80 characters or fewer")
    return text


def _ai_endpoint(raw) -> str:
    """http or https, no userinfo. The address stays in memory; it is not logged."""
    text = str(raw or "").strip()
    if not text or len(text) > 300 or any(ord(ch) < 32 or ch.isspace() for ch in text):
        raise FormError("endpoint URL must be an http or https address")
    parts = urlsplit(text)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise FormError("endpoint URL must be an http or https address")
    return text


def _ai_key(raw) -> str:
    """One line, kept off the GameForm's settings and out of every error string."""
    text = str(raw or "")
    if not text.strip() or len(text) > 500 or any(ord(ch) < 32 for ch in text):
        raise FormError("An LLM seat needs your API key on one line.")
    return text.strip()

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


def turns_phrase(settings: dict) -> str:
    """Lobby card line. Original is the pocket this game already used."""
    if settings.get("game_length") == "full":
        shown = int(settings.get("turns_per_day") or K.FULL_LENGTH_TURNS_PER_DAY)
        return f"Turns per day: {shown:,} (full-length)"
    override = settings.get("turns_per_day_override")
    if override is None:
        shown = int(settings.get("turns_per_day") or 250)
        return f"Turns per day: {shown:,} (original)"
    return f"Turns per day: {int(override):,} (game setting)"


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


def _turns_override(data: dict) -> int | None:
    """Original (missing, 'original', or 250) is no override. Else 50..5,000."""
    if "turns_per_day" not in data and "turns_per_day_custom" not in data:
        return None
    raw = data.get("turns_per_day", "original")
    if isinstance(raw, bool):
        raise FormError("turns per day must be a whole number")
    if raw is None:
        return None
    text = str(raw).strip().lower().replace(",", "").replace("_", "")
    if text in ("", "original", "none", "250"):
        return None
    if text == "custom":
        if "turns_per_day_custom" not in data or str(data.get("turns_per_day_custom", "")).strip() == "":
            raise FormError("Type a turns-per-day amount.")
        return _as_int(data, "turns_per_day_custom", 0, _TURNS_MIN, _TURNS_MAX)
    if isinstance(raw, float) or "." in text:
        raise FormError("turns per day must be a whole number")
    try:
        val = int(text)
    except ValueError:
        raise FormError("turns per day must be a whole number") from None
    if not _TURNS_MIN <= val <= _TURNS_MAX:
        raise FormError(f"turns per day must be between {_TURNS_MIN} and {_TURNS_MAX}")
    return val


def _game_length(data: dict) -> str | None:
    """Missing or fast is today's test day. Full is the only other choice."""
    if "game_length" not in data:
        return None
    try:
        return K.parse_game_length(data.get("game_length"))
    except ValueError as exc:
        raise FormError(str(exc)) from None


def _hold_flag(data: dict) -> bool:
    """Missing stays off, so an old post still starts the clock today."""
    if "hold_until_human" not in data:
        return False
    return _as_bool(data, "hold_until_human", False)


def parse_game_form(data: dict, presets: dict[str, int] | None = None) -> GameForm:
    presets = presets or DAY_PRESETS
    unknown = set(data) - _allowed_fields()
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
    turns_override = _turns_override(data)
    max_days = _as_int(data, "max_days", 30, 1, 365)
    length = _game_length(data) if K.full_length_turn_limits_on() else None
    if length == "full":
        cap = K.full_length_daily_cap(max_days)
        turns_override = cap
        day = "24h"
        day_seconds = int(presets["24h"]) if "24h" in presets else int(K.FULL_LENGTH_DAY_SECONDS)
    else:
        day_seconds = int(presets[day])
    ai_n = 0
    brain = "heuristic"
    ai_key = ""
    ai_endpoint = ""
    if K.lobby_ai_seat_on():
        ai_n = _as_int(data, "ai_opponents", 0, 0, 4)
        brain = str(data.get("ai_brain", "heuristic")).strip().lower() or "heuristic"
        if brain not in ("heuristic", "llm"):
            raise FormError("AI brain must be heuristic or llm")
        if ai_n and brain == "llm":
            # Read into locals the caller moves into process memory. Not into settings().
            ai_endpoint = _ai_endpoint(data.get("ai_endpoint"))
            ai_key = _ai_key(data.get("ai_key"))
        elif not ai_n:
            brain = "heuristic"
    cockpit = False
    cockpit_provider = "scripted"
    cockpit_model = ""
    cockpit_count = 1
    cockpit_level = "hard"
    if K.ai_cockpit_seat_on():
        cockpit = _as_bool(data, "ai_cockpit", False)
        if cockpit:
            cockpit_provider = _cockpit_provider(data.get("ai_cockpit_provider"))
            cockpit_model = _cockpit_model(data.get("ai_cockpit_model"))
            if "ai_cockpit_count" in data:
                cockpit_count = _as_int(data, "ai_cockpit_count", 1, 1, 4)
            cockpit_level = _cockpit_level(data.get("ai_cockpit_level", "hard"))
    return GameForm(
        name=name,
        rules=rules,
        universe_size=size,
        max_days=max_days,
        turns_per_day=250 if turns_override is None else int(turns_override),
        starting_package=start,
        bots=_as_int(data, "bots", 2, 0, 5),
        ferrengi=_as_bool(data, "ferrengi", True),
        day=day,
        humans=_as_int(data, "humans", 1, 1, 4),
        listed=listed,
        day_seconds=day_seconds,
        starting_credits_override=_credits_override(data),
        home_planet_name=home_planet_name(data.get("home_planet_name")),
        turns_per_day_override=turns_override,
        hold_until_human=_hold_flag(data),
        ai_opponents=ai_n,
        ai_brain=brain,
        ai_key=ai_key,
        ai_endpoint=ai_endpoint,
        ai_cockpit=cockpit,
        ai_cockpit_provider=cockpit_provider,
        ai_cockpit_model=cockpit_model,
        ai_cockpit_count=cockpit_count,
        ai_cockpit_level=cockpit_level,
        game_length=length,
    )


def mask_path(path: str) -> str:
    """Strip query strings (claim tokens) from anything that is logged."""
    return path.split("?", 1)[0]
