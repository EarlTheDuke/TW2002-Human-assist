"""TinyBox (server key) brain for lobby AI seats.

The lobby host's own OpenAI-compatible endpoint (Ben's TinyBox Qwen / Kimi
gateway). It reads the same ``TW2K_CUSTOM_*`` settings the CLI ``custom``
provider uses (``agents/llm.py`` ``_call_custom``), so the key is never a form
field. The key stays in this process. Nothing here logs or returns it.

Settings (environment, or a ``.env`` file passed to ``tw2k lobby --env-file``):

  TW2K_CUSTOM_BASE_URL        e.g. https://tinybox.silverstarindustries.com/api
  TW2K_CUSTOM_API_KEY         bearer key (TW2K_TINYBOX_API_KEY is also read)
  TW2K_CUSTOM_MAX_TOKENS      output budget per call (default 6000 qwen / 4000 other)
  TW2K_CUSTOM_THINK_CAP_S     seconds one call may think (default 180)
  TW2K_CUSTOM_KEEP_ALIVE      Ollama keep_alive (default 30m)
  TW2K_CUSTOM_TEMPERATURE     default 0.2 qwen / 0.6 other
  TW2K_TINYBOX_MODELS         form default, e.g. "qwen3.8:latest x2, kimi-k2.6 x2"
  TW2K_TINYBOX_CALL_CAP       model calls per seat per game (default 20000)
  TW2K_TINYBOX_CALLS_PER_MIN  model calls per seat per minute (default 60)
  TW2K_TINYBOX_TURN_S         longest wait for one reply, capped by the think cap (default 100)
"""

from __future__ import annotations

import json
import logging
import os
import re
import socket
import time
import urllib.error
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger("tw2k.lobby.tinybox")

DEFAULT_MODELS = "qwen3.8:latest x2, kimi-k2.6 x2"
DEFAULT_THINK_CAP_S = 180.0
# The lobby worker gives an external seat 120 s per turn; leave room for the post.
DEFAULT_TURN_S = 100.0
DEFAULT_CALL_CAP = 20_000
DEFAULT_PER_MINUTE = 60
_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,79}$")


def load_env_file(path: str | Path) -> list[str]:
    """``KEY=VALUE`` lines into ``os.environ``. Existing variables win. Returns key names only."""
    names: list[str] = []
    for raw in Path(path).read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
            names.append(key)
    return names


def _is_timeout(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    reason = getattr(exc, "reason", None)
    return isinstance(reason, (TimeoutError, socket.timeout))


def _num(name: str, default: float) -> float:
    try:
        value = float(os.environ.get(name, "") or default)
    except ValueError:
        return float(default)
    return value if value > 0 else float(default)


@dataclass
class TinyboxConfig:
    base_url: str
    key: str = field(repr=False)
    think_cap_s: float
    max_tokens: int | None
    keep_alive: str
    call_cap: int
    per_minute: int
    turn_s: float = DEFAULT_TURN_S

    @property
    def call_timeout_s(self) -> float:
        """One call must answer inside the worker's per-turn deadline, or the turn is lost as a WAIT."""
        return max(5.0, min(float(self.think_cap_s), float(self.turn_s)))

    @property
    def ready(self) -> bool:
        return bool(self.base_url and self.key)

    @property
    def endpoint(self) -> str:
        base = self.base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return base + "/chat/completions"

    def __repr__(self) -> str:
        return f"TinyboxConfig(base_url={self.base_url!r}, ready={self.ready})"


def config() -> TinyboxConfig:
    raw_tokens = (os.environ.get("TW2K_CUSTOM_MAX_TOKENS") or "").strip()
    try:
        max_tokens = int(raw_tokens) if raw_tokens else None
    except ValueError:
        max_tokens = None
    return TinyboxConfig(
        base_url=(os.environ.get("TW2K_CUSTOM_BASE_URL") or "").strip(),
        key=(os.environ.get("TW2K_CUSTOM_API_KEY") or os.environ.get("TW2K_TINYBOX_API_KEY") or "").strip(),
        think_cap_s=_num("TW2K_CUSTOM_THINK_CAP_S", DEFAULT_THINK_CAP_S),
        max_tokens=max_tokens if max_tokens and max_tokens > 0 else None,
        keep_alive=(os.environ.get("TW2K_CUSTOM_KEEP_ALIVE") or "30m").strip(),
        call_cap=int(_num("TW2K_TINYBOX_CALL_CAP", DEFAULT_CALL_CAP)),
        per_minute=int(_num("TW2K_TINYBOX_CALLS_PER_MIN", DEFAULT_PER_MINUTE)),
        turn_s=_num("TW2K_TINYBOX_TURN_S", DEFAULT_TURN_S),
    )


def ready() -> bool:
    return config().ready


def default_models_text() -> str:
    return (os.environ.get("TW2K_TINYBOX_MODELS") or DEFAULT_MODELS).strip()


def parse_models(text: str, seats: int) -> list[str]:
    """``"qwen3.8:latest x2, kimi-k2.6 x2"`` -> one model per seat, in seat order.

    A shorter list repeats from the start. A longer list is an error.
    Raises ValueError with a plain sentence.
    """
    names: list[str] = []
    for part in re.split(r"[,\n;]+", str(text or "")):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(.*?)\s*(?:[x\*]\s*(\d+))?$", part, re.IGNORECASE)
        name = (m.group(1) if m else part).strip()
        count = int(m.group(2)) if m and m.group(2) else 1
        if not _MODEL_RE.match(name):
            raise ValueError("Each model name must be letters, digits, or . _ : / @ + -")
        if count < 1 or count > 8:
            raise ValueError("A model count must be between 1 and 8")
        names.extend([name] * count)
    if not names:
        raise ValueError("Name at least one model, e.g. qwen3.8:latest x2, kimi-k2.6 x2")
    if seats > 0 and len(names) > seats:
        raise ValueError(f"That lists {len(names)} models for {seats} AI seats")
    if seats <= 0:
        return names
    return [names[i % len(names)] for i in range(seats)]


# ------------------------------------------------------------------ prompt

SYSTEM_PROMPT = (
    "You are playing Trade Wars 2002 as one trader, through the same cockpit a human uses. "
    "Each turn you see your sector, the warps out of it, the port here and its prices, your ship, "
    "holds and cargo, the ports you know, recent results and the legal actions with their arguments. "
    "Goal: grow net worth and experience over a long game: trade profitably between ports, upgrade "
    "holds and ship, claim and build planets toward a level 3+ citadel and quasar cannon, and defend "
    "what you own. Choose exactly one action from `legal_actions`. Fill its `params` as described "
    "(respect choices/min/max). Reply with ONE JSON object and nothing else: "
    '{"kind": "<legal kind>", "args": {...}, "why": "<one short sentence>"}'
)

_KEEP = (
    "day", "max_days", "turns_remaining", "turns_per_day", "credits", "net_worth", "experience",
    "alignment", "rank", "planet_landed", "action_hint", "bank_balance", "deaths", "max_deaths",
)


def _tail(rows: Any, n: int) -> list[Any]:
    return list(rows or [])[-n:]


def build_prompt(obs: dict[str, Any], cockpit: dict[str, Any] | None, history: list[dict[str, Any]]) -> str:
    """What a human sees in the cockpit, as one JSON document."""
    out: dict[str, Any] = {k: obs.get(k) for k in _KEEP if obs.get(k) is not None}
    out["me"] = {"id": obs.get("self_id"), "name": obs.get("self_name")}
    out["sector"] = obs.get("sector") or {}
    out["adjacent"] = obs.get("adjacent") or []
    out["ship"] = obs.get("ship") or {}
    out["known_ports"] = _tail(obs.get("known_ports"), 15)
    out["known_warps"] = dict(list((obs.get("known_warps") or {}).items())[:40])
    out["owned_planets"] = obs.get("owned_planets") or []
    out["trade_summary"] = obs.get("trade_summary") or {}
    out["recent_trades"] = _tail(obs.get("trade_log"), 8)
    out["recent_failures"] = _tail(obs.get("recent_failures"), 6)
    out["recent_events"] = _tail(obs.get("recent_events"), 10)
    out["inbox"] = _tail(obs.get("inbox"), 5)
    for name in ("fighter_challenge", "ferrengi_encounter", "police", "fedspace", "goals"):
        if obs.get(name):
            out[name] = obs.get(name)
    if cockpit:
        out["cockpit"] = {k: v for k, v in cockpit.items() if k in (
            "hold_quote", "port_notes", "port", "here", "prices", "stardock", "course")}
    legal = []
    blocked = {}
    for row in obs.get("legal_actions") or []:
        if row.get("legal"):
            legal.append({"kind": row.get("kind"), "turn_cost": row.get("turn_cost"),
                          "params": row.get("params") or {}})
        elif row.get("reason"):
            blocked[str(row.get("kind"))] = row.get("reason")
    out["legal_actions"] = legal
    out["blocked_actions"] = blocked
    out["my_last_moves"] = history[-6:]
    return json.dumps(out, default=str, separators=(",", ":"))


def _text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    msg = choices[0].get("message") or {}
    content = str(msg.get("content") or "")
    if "{" in content:
        return content
    # Ollama / OWUI reasoning models sometimes put the JSON in the reasoning field.
    for name in ("reasoning", "reasoning_content", "thinking"):
        alt = str(msg.get(name) or "")
        if "{" in alt:
            return alt
    return content


def parse_choice(text: str) -> tuple[str, dict[str, Any], str] | None:
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    starts = [i for i, ch in enumerate(text) if ch == "{"]
    decoder = json.JSONDecoder()
    found = None
    for i in starts:
        try:
            row, _ = decoder.raw_decode(text[i:])
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("kind"):
            found = row
    if found is None:
        return None
    if isinstance(found.get("action"), dict) and not found.get("args"):
        found = {**found["action"], "why": found.get("why") or found.get("thought")}
    args = found.get("args")
    if args is None:
        args = {k: v for k, v in found.items() if k not in ("kind", "why", "thought")}
    return str(found.get("kind")), args if isinstance(args, dict) else {}, str(found.get("why") or "tinybox")[:200]


def request_body(cfg: TinyboxConfig, model: str, user: str) -> dict[str, Any]:
    """Same request shape as the CLI custom provider (``_call_custom``)."""
    is_qwen = "qwen" in model.lower()
    max_tokens = cfg.max_tokens or (6000 if is_qwen else 4000)
    try:
        temperature = float(os.environ.get("TW2K_CUSTOM_TEMPERATURE", "") or (0.2 if is_qwen else 0.6))
    except ValueError:
        temperature = 0.2 if is_qwen else 0.6
    return {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "keep_alive": cfg.keep_alive,
        "num_predict": max_tokens,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
    }


def ask(cfg: TinyboxConfig, model: str, user: str) -> str:
    """One chat completion. Raises on HTTP or network errors. The key is a header only."""
    body = json.dumps(request_body(cfg, model, user)).encode()
    req = urllib.request.Request(
        cfg.endpoint, data=body, method="POST",
        headers={"authorization": f"Bearer {cfg.key}", "content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=cfg.call_timeout_s) as reply:  # noqa: S310 - host-configured URL
        return _text(json.loads(reply.read().decode()))


class TinyboxSeatBudget:
    """One seat's model and caps. Called from a worker thread by the cockpit seat loop.

    Returns None so the heuristic plays this turn. ``lasting_fallback`` is set
    after the cap, a missing config, or ``max_errors`` errors in a row, and the
    reason is logged once at WARNING.
    """

    threaded = True

    def __init__(self, cfg: TinyboxConfig, model: str, *, gid: str = "", seat: str = "",
                 max_errors: int = 3) -> None:
        self.cfg = cfg
        self.model = model
        self.gid = gid
        self.seat = seat
        self.cap = int(cfg.call_cap)
        self.per_minute = int(cfg.per_minute)
        self.max_errors = int(max_errors)
        self.calls = 0
        self.errors = 0
        self.fallback_turns = 0
        self.timeouts = 0
        self.stamps: deque[float] = deque()
        self.history: list[dict[str, Any]] = []
        self.lasting_fallback = False
        self.reason = ""
        if not cfg.ready:
            self._fall("TinyBox is not configured on the lobby (TW2K_CUSTOM_BASE_URL / key missing)")

    def _fall(self, reason: str) -> None:
        if not self.lasting_fallback:
            self.lasting_fallback = True
            self.reason = reason
            log.warning("ai seat game=%s seat=%s model=%s FALLBACK to heuristic: %s",
                        self.gid, self.seat, self.model, reason)

    def _skip(self, reason: str) -> None:
        self.fallback_turns += 1
        log.info("ai seat game=%s seat=%s model=%s heuristic this turn: %s",
                 self.gid, self.seat, self.model, reason)

    def __call__(self, key: str, obs: dict, cockpit: dict | None):
        if self.lasting_fallback:
            return None
        now = time.monotonic()
        while self.stamps and now - self.stamps[0] >= 60:
            self.stamps.popleft()
        if self.calls >= self.cap:
            self._fall(f"call cap {self.cap} reached")
            return None
        if len(self.stamps) >= self.per_minute:
            self._skip(f"{self.per_minute} calls/minute limit")
            return None
        self.calls += 1
        self.stamps.append(now)
        started = time.monotonic()
        try:
            text = ask(self.cfg, self.model, build_prompt(obs, cockpit, self.history))
        except urllib.error.HTTPError as exc:
            self._latency(started, f"HTTP {exc.code}")
            return self._error(f"HTTP {exc.code}")
        except Exception as exc:  # timeout, refused, bad JSON
            self._latency(started, type(exc).__name__)
            if _is_timeout(exc):
                # A slow reply is not a broken endpoint: play the heuristic this turn, ask again next turn.
                self.timeouts += 1
                self._skip(f"no reply within {self.cfg.call_timeout_s:g}s")
                return None
            return self._error(type(exc).__name__)
        picked = parse_choice(text)
        self._latency(started, picked[0] if picked else "no-action")
        legal = {str(r.get("kind")) for r in (obs.get("legal_actions") or []) if r.get("legal")}
        if picked is None or picked[0] not in legal:
            self._skip("reply had no legal action" if picked is None else f"illegal kind {picked[0]!r}")
            self.errors += 1
            if self.errors >= self.max_errors * 3:
                self._fall(f"{self.errors} unusable replies in a row")
            return None
        self.errors = 0
        self.history.append({"day": obs.get("day"), "sector": (obs.get("sector") or {}).get("id"),
                             "kind": picked[0], "args": picked[1]})
        del self.history[:-12]
        return picked

    def _latency(self, started: float, outcome: str) -> None:
        log.info("ai seat game=%s seat=%s model=%s call %.1fs %s",
                 self.gid, self.seat, self.model, time.monotonic() - started, outcome)

    def _error(self, what: str):
        self.errors += 1
        if self.errors >= self.max_errors:
            self._fall(f"endpoint error {what} ({self.errors} in a row)")
        else:
            self._skip(f"endpoint error {what}")
        return None
