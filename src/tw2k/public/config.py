"""Lobby settings (env-driven) and the port guard for `tw2k lobby`."""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass, field
from pathlib import Path

ENV_LOBBY_PORT = "TW2K_LOBBY_PORT"
ENV_GAME_PORTS = "TW2K_GAME_PORTS"
ENV_LOBBY_ROOT = "TW2K_LOBBY_ROOT"
ENV_IDLE_MIN = "TW2K_LOBBY_IDLE_MIN"
ENV_ARCHIVE_DAYS = "TW2K_LOBBY_ARCHIVE_DAYS"
ENV_MAX_GAMES = "TW2K_LOBBY_MAX_GAMES"
ENV_MAX_SEATS = "TW2K_LOBBY_MAX_SEATS"
ENV_BRAND_NAME = "TW2K_BRAND"
ENV_DAY_PRESETS = "TW2K_LOBBY_DAY_PRESETS"

DEFAULT_LOBBY_PORT = 8099
DEFAULT_GAME_PORTS = range(8100, 8120)
# Other local servers live here; the lobby refuses any configuration that overlaps it.
PROTECTED_PORTS = range(8031, 8099)
DEFAULT_BRAND = "Galaxy War Command"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def parse_port_range(raw: str) -> range:
    text = (raw or "").strip()
    if "-" in text:
        lo_s, hi_s = text.split("-", 1)
        lo, hi = int(lo_s), int(hi_s)
    else:
        lo = hi = int(text)
    if not (1024 <= lo <= hi <= 65535):
        raise ValueError(f"bad port range {raw!r}")
    if hi - lo + 1 > 64:
        raise ValueError(f"port range {raw!r} is wider than 64 ports")
    return range(lo, hi + 1)


def parse_day_presets(raw: str) -> dict[str, int]:
    """``2m=120,5m=300``: extra day lengths offered next to 10m/30m/1h/24h (10 s to 7 days)."""
    out: dict[str, int] = {}
    for part in (raw or "").split(","):
        if not part.strip():
            continue
        label, _, secs = part.partition("=")
        label = label.strip()
        if not label or len(label) > 8 or not label.isalnum():
            raise ValueError(f"bad day preset label {label!r}")
        val = int(secs)
        if not 10 <= val <= 604800:
            raise ValueError(f"day preset {label} must be 10..604800 seconds")
        out[label] = val
    return out


def _overlaps_protected(ports: range | list[int]) -> bool:
    return any(p in PROTECTED_PORTS for p in ports)


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


@dataclass
class LobbyConfig:
    host: str = "127.0.0.1"
    port: int = DEFAULT_LOBBY_PORT
    game_ports: range = DEFAULT_GAME_PORTS
    root: Path = field(default_factory=lambda: _repo_root() / "saves" / "selfhost")
    max_games: int = 10
    max_human_seats: int = 10
    idle_s: float = 30 * 60.0
    archive_s: float = 7 * 86400.0
    brand: str = DEFAULT_BRAND
    new_games_per_hour: int = 3
    joins_per_10min: int = 20
    actions_per_s: int = 12
    body_limit: int = 64 * 1024
    stop_timeout_s: float = 15.0
    boot_timeout_s: float = 90.0
    external_idle_wait_s: float = 3.0
    tick_s: float = 5.0
    extra_day_presets: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.host not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("the lobby only binds loopback; the tunnel reaches it from this PC")
        if _overlaps_protected([self.port]) or _overlaps_protected(self.game_ports):
            raise ValueError("lobby ports overlap the protected 8031-8098 block")
        if self.port in self.game_ports:
            raise ValueError("lobby port sits inside the game port range")
        self.max_games = max(1, min(int(self.max_games), len(self.game_ports)))
        self.root = Path(self.root)

    @classmethod
    def from_env(cls, **overrides) -> "LobbyConfig":
        kw: dict = {}
        if os.environ.get(ENV_LOBBY_PORT):
            kw["port"] = int(os.environ[ENV_LOBBY_PORT])
        if os.environ.get(ENV_GAME_PORTS):
            kw["game_ports"] = parse_port_range(os.environ[ENV_GAME_PORTS])
        if os.environ.get(ENV_LOBBY_ROOT):
            kw["root"] = Path(os.environ[ENV_LOBBY_ROOT])
        kw["idle_s"] = _float_env(ENV_IDLE_MIN, 30.0) * 60.0
        kw["archive_s"] = _float_env(ENV_ARCHIVE_DAYS, 7.0) * 86400.0
        kw["max_games"] = max(1, _int_env(ENV_MAX_GAMES, 10))
        kw["max_human_seats"] = max(1, _int_env(ENV_MAX_SEATS, 10))
        kw["brand"] = (os.environ.get(ENV_BRAND_NAME) or DEFAULT_BRAND).strip()[:40]
        if os.environ.get(ENV_DAY_PRESETS):
            kw["extra_day_presets"] = parse_day_presets(os.environ[ENV_DAY_PRESETS])
        kw.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**kw)

    @property
    def day_presets(self) -> dict[str, int]:
        from .security import DAY_PRESETS

        return {**DAY_PRESETS, **self.extra_day_presets}

    @property
    def db_path(self) -> Path:
        return self.root / "lobby.sqlite3"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    @property
    def games_dir(self) -> Path:
        return self.root / "games"

    @property
    def archive_dir(self) -> Path:
        return self.root / "archive"


def port_is_free(port: int, host: str = "127.0.0.1") -> bool:
    """True when nothing listens on host:port. Binds briefly; never connects to or signals the owner.

    A connection the server already closed can keep the port in wait for a minute.
    That is not a listener. On POSIX the probe sets SO_REUSEADDR so a restart can
    bind again while that wait runs. A socket that is still listening still fails
    the bind. Windows keeps the exclusive probe, because SO_REUSEADDR there would
    hide a live listener.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        elif os.name != "nt":
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def pick_port(cfg: LobbyConfig, taken: set[int], *, probe=port_is_free) -> int | None:
    for port in cfg.game_ports:
        if port in taken:
            continue
        if probe(port):
            return port
    return None


def assert_lobby_port(cfg: LobbyConfig, port: int) -> None:
    if port not in cfg.game_ports:
        raise RuntimeError(f"port {port} is outside the lobby's range")
