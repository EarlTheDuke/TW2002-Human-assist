"""Per-seat directive inbox and reliability helpers for cockpit players.

Ben drops structured goals on disk. A seat reads only its own files and
the cockpit it already has (the rendered page, or the harness routes that
page calls). Nothing here opens a privileged API or adds map data.

The rendered player imports this module directly. The engine re-exports it
without the cockpit player importing ``tw2k``.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

_SEAT = re.compile(r"^[A-Z0-9_-]{1,32}$")
_BEARER = re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{8,}")
_SK = re.compile(r"(?i)\bsk-[A-Za-z0-9_\-]{8,}")
_XAI = re.compile(r"(?i)\bxai-[A-Za-z0-9_\-]{8,}")
_TOKEN_QUERY = re.compile(r"(?i)(token=)[^&\s\"'#]+")

RECOVERY_PRIORITY = 90
DEFAULT_STUCK_AFTER = 6
BEAT_S = 5.0

# Verbs the cockpit seat already posts. A scripted step never emits anything else.
# The model may still propose a kind the cockpit lists; validation uses legal_actions.
STEP_KINDS = frozenset(
    {
        "warp",
        "plot_course",
        "attack",
        "build_citadel",
        "assign_colonists",
        "terra_colonists",
        "buy_equip",
        "scan",
        "liftoff",
        "wait",
    }
)


class DirectiveError(ValueError):
    """A directive file Ben dropped is not usable."""


class RetryableHTTPError(Exception):
    """A harness read or post failed in a way a reconnect should retry."""

    def __init__(self, status: int, detail: object = "") -> None:
        super().__init__(f"HTTP {status}")
        self.status = int(status)
        self.detail = detail


def clean_seat(seat: str) -> str:
    """One seat name, safe to use as a single path component."""
    text = str(seat or "").strip().upper()
    if not _SEAT.fullmatch(text):
        raise DirectiveError(f"not a seat id: {seat!r}")
    return text


def seat_from_url(url: str) -> str:
    """The ``seat`` query on a cockpit link, or ``""``."""
    parsed = urlparse(url or "")
    query = parse_qs(parsed.query)
    found = (query.get("seat") or [""])[0]
    if not found and parsed.fragment:
        found = (parse_qs(parsed.fragment).get("seat") or [""])[0]
    try:
        return clean_seat(found)
    except DirectiveError:
        return ""


def token_from_url(url: str) -> str:
    """The seat token on a cockpit link, query or fragment. For redaction only."""
    parsed = urlparse(url or "")
    query = parse_qs(parsed.query)
    found = (query.get("token") or [""])[0]
    if not found and parsed.fragment:
        found = (parse_qs(parsed.fragment).get("token") or [""])[0]
    return str(found or "")


@dataclass
class Directive:
    """One operator goal. ``sector`` and ``target`` are optional."""

    goal: str
    target: str = ""
    sector: int | None = None
    priority: int = 0
    id: str = ""
    expires_at: datetime | None = None
    expires_day: int | None = None
    source: str = "inbox"
    order: int = 0

    def expired(self, *, now: datetime | None, game_day: int | None) -> bool:
        if self.expires_at is not None and now is not None and now >= self.expires_at:
            return True
        if self.expires_day is not None and game_day is not None and int(game_day) > int(self.expires_day):
            return True
        return False

    def as_dict(self) -> dict[str, Any]:
        row: dict[str, Any] = {"goal": self.goal, "priority": self.priority, "source": self.source}
        if self.id:
            row["id"] = self.id
        if self.target:
            row["target"] = self.target
        if self.sector is not None:
            row["sector"] = self.sector
        if self.expires_day is not None:
            row["expires_day"] = self.expires_day
        if self.expires_at is not None:
            row["expires"] = self.expires_at.isoformat()
        return row


def inbox_paths(root: Path, seat: str) -> list[Path]:
    """Files for this seat only. A sibling seat's file is not in the list."""
    name = clean_seat(seat)
    folder = root / name
    return [root / f"{name}.json", folder / "inbox.json", folder / "recovery.json"]


def parse_directives(payload: object, *, source: str = "inbox", order_start: int = 0) -> list[Directive]:
    """Accept one directive, a list, or ``{"directives": [...]}``."""
    rows = _rows(payload)
    found: list[Directive] = []
    order = order_start
    for row in rows:
        item = _one(row, source=source, order=order)
        order += 1
        if item is not None:
            found.append(item)
    return found


def load_active(
    root: str | Path,
    seat: str,
    *,
    now: datetime | None = None,
    game_day: int | None = None,
) -> list[Directive]:
    """Active directives for ``seat``, highest priority first.

    A missing inbox is empty. A broken file is skipped so one bad drop
    does not kill the seat. Expired rows are left on disk and ignored.
    """
    clock = now if now is not None else datetime.now(UTC)
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=UTC)
    found: list[Directive] = []
    order = 0
    for path in inbox_paths(Path(root), seat):
        if not path.is_file():
            continue
        source = "recovery" if path.name == "recovery.json" else "inbox"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        batch = parse_directives(payload, source=source, order_start=order)
        order += max(1, len(batch))
        found.extend(batch)
    active = [row for row in found if not row.expired(now=clock, game_day=game_day)]
    active.sort(key=lambda row: (-row.priority, row.order))
    return active


def prompt_block(directives: list[Directive]) -> str:
    """Goals for this turn. Not a cheat sheet and not extra map data."""
    if not directives:
        return ""
    lines = [
        "Operator directives for this seat. They are goals from Ben, not extra map data.",
        "Use only what this cockpit shows. If a directive is not legal from the screen, "
        "do not invent a move; take the best legal step or leave the goal for a later turn.",
    ]
    for index, row in enumerate(directives, start=1):
        label = f"{index}. priority {row.priority}"
        if row.id:
            label += f" id {row.id}"
        if row.source == "recovery":
            label += " recovery"
        lines.append(label)
        lines.append(f"   goal: {row.goal}")
        if row.target:
            lines.append(f"   target: {row.target}")
        if row.sector is not None:
            lines.append(f"   sector: {row.sector}")
        if row.expires_day is not None:
            lines.append(f"   expires day: {row.expires_day}")
        elif row.expires_at is not None:
            lines.append(f"   expires: {row.expires_at.isoformat()}")
    return "\n".join(lines)


def cockpit_state(obs: dict[str, Any] | None) -> dict[str, Any]:
    """A short slice of the observation the cockpit already returned."""
    obs = obs or {}
    legal = [
        str(row.get("kind"))
        for row in (obs.get("legal_actions") or [])
        if isinstance(row, dict) and row.get("legal")
    ]
    sector = obs.get("sector") if isinstance(obs.get("sector"), dict) else {}
    return {
        "day": obs.get("day"),
        "sector": sector.get("id"),
        "turns_remaining": obs.get("turns_remaining"),
        "credits": obs.get("credits"),
        "net_worth": obs.get("net_worth"),
        "planet_landed": obs.get("planet_landed"),
        "legal": legal,
    }


def turn_prompt(obs: dict[str, Any] | None, directives: list[Directive], *, note: str = "") -> str:
    """Directive block plus the cockpit slice. This is what a turn log stores."""
    parts = [prompt_block(directives), "", "Cockpit:", json.dumps(cockpit_state(obs), default=str)]
    if note:
        parts.extend(["", note])
    return "\n".join(parts).strip()


def observation_fingerprint(obs: dict[str, Any] | None) -> tuple:
    """Progress is day, sector, net worth, or owned-planet citadel and colonists."""
    obs = obs or {}
    sector = obs.get("sector") if isinstance(obs.get("sector"), dict) else {}
    planets = []
    for planet in obs.get("owned_planets") or []:
        if not isinstance(planet, dict):
            continue
        colonists = planet.get("colonists_total")
        if colonists is None and isinstance(planet.get("colonists"), dict):
            colonists = sum(int(value or 0) for value in planet["colonists"].values())
        elif colonists is None:
            colonists = planet.get("colonists")
        planets.append(
            (
                planet.get("id") if planet.get("id") is not None else planet.get("planet_id"),
                planet.get("citadel_level"),
                colonists,
            )
        )
    return (obs.get("day"), sector.get("id"), obs.get("net_worth"), tuple(planets))


def screen_fingerprint(screen: dict[str, Any] | None) -> tuple:
    """The rendered cockpit's day, sector, and net worth."""
    screen = screen or {}
    return (str(screen.get("day") or ""), str(screen.get("sector") or ""), str(screen.get("nw") or ""))


def validate_proposal(
    action: dict[str, Any] | None,
    observation: dict[str, Any] | None,
    *,
    allowed_kinds: frozenset[str] | set[str] | None = None,
) -> tuple[bool, str]:
    """True when ``action`` is a legal cockpit verb with args the screen allows.

    Choices and quantity caps come only from ``legal_actions``. A kind the
    cockpit does not list is refused. Haggle prices are not checked.
    ``allowed_kinds`` is the verb list the caller can post (the cockpit seat's
    list). None means any kind the cockpit marks legal.
    """
    if not isinstance(action, dict):
        return False, "action is not an object"
    kind = str(action.get("kind") or "").strip()
    if not kind:
        return False, "missing kind"
    if allowed_kinds is not None and kind not in allowed_kinds:
        return False, "not a cockpit action"
    raw_args = action.get("args", {})
    if raw_args is None:
        raw_args = {}
    if not isinstance(raw_args, dict):
        return False, "args must be an object"
    row = _legal_row(observation or {}, kind)
    if row is None:
        return False, f"{kind} is not on the cockpit"
    if not row.get("legal"):
        return False, str(row.get("reason") or f"{kind} is not legal")
    reason = _check_args(kind, raw_args, row.get("params") or {}, observation or {})
    if reason:
        return False, reason
    return True, ""


def directive_step(
    obs: dict[str, Any] | None,
    directives: list[Directive],
    *,
    avoid_kind: str = "",
) -> dict[str, Any] | None:
    """One cockpit-legal step toward the top directive, or None.

    Used when no model is in the loop. A model keeps its own proposal and
    is only rejected when ``validate_proposal`` says the cockpit forbids it.
    This does not pathfind and does not read anything off the observation's
    legal envelope, the sector, or names already on that observation.
    """
    if not directives:
        return None
    top = directives[0]
    obs = obs or {}
    if _is_recovery(top):
        step = _recovery_step(obs, avoid_kind)
    elif top.sector is not None and _here(obs) != int(top.sector):
        step = _travel(obs, int(top.sector), top)
    else:
        step = _onsite(obs, top)
    if step is None:
        return None
    ok, _reason = validate_proposal(step, obs)
    return step if ok else None


def redact_text(text: str, secrets: list[str] | None = None) -> str:
    """Replace bearer tokens, key-shaped values, and ``token=`` query values."""
    if not text:
        return text
    for value in secrets or []:
        if value and len(value) >= 6:
            text = text.replace(value, "[redacted]")
    text = _BEARER.sub("Bearer [redacted]", text)
    text = _SK.sub("[redacted]", text)
    text = _XAI.sub("[redacted]", text)
    text = _TOKEN_QUERY.sub(r"\1[redacted]", text)
    return text


def redact_obj(value: Any, secrets: list[str] | None = None) -> Any:
    if isinstance(value, str):
        return redact_text(value, secrets)
    if isinstance(value, dict):
        return {str(key): redact_obj(item, secrets) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_obj(item, secrets) for item in value]
    return value


class StuckWatch:
    """Count acted turns whose progress fingerprint does not change.

    The same fingerprint ``after`` times asks for a recovery directive.
    ``after * 2`` times escalates. A changed fingerprint clears the streak.
    """

    def __init__(self, after: int = DEFAULT_STUCK_AFTER) -> None:
        self.after = max(2, int(after))
        self.seen = 0
        self._fp: tuple | None = None

    def observe(self, fingerprint: tuple) -> str:
        """Return ``""``, ``"clear"``, ``"recover"``, or ``"escalate"``."""
        if self._fp is None:
            self._fp = fingerprint
            self.seen = 1
            return ""
        if fingerprint != self._fp:
            self._fp = fingerprint
            self.seen = 1
            return "clear"
        self.seen += 1
        if self.seen == self.after:
            return "recover"
        if self.seen == self.after * 2:
            return "escalate"
        return ""


def write_recovery(root: str | Path, seat: str, *, attempt: int, last_action: str) -> Path:
    """A harness-owned file. Ben's ``<seat>.json`` is not modified."""
    name = clean_seat(seat)
    path = Path(root) / name / "recovery.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    goal = (
        "No progress for several turns. Leave this sector if a warp is legal, "
        "otherwise take a different legal action than the last one."
    )
    if last_action:
        goal += f" Last action was {last_action}."
    doc = {
        "id": f"recovery-{int(attempt)}",
        "goal": goal,
        "priority": RECOVERY_PRIORITY,
        "source": "recovery",
    }
    _write_json(path, doc)
    return path


def clear_recovery(root: str | Path, seat: str) -> None:
    path = Path(root) / clean_seat(seat) / "recovery.json"
    try:
        path.unlink()
    except FileNotFoundError:
        return


def write_escalate(
    root: str | Path,
    seat: str,
    *,
    reason: str,
    fingerprint: tuple | None = None,
    turns: int = 0,
) -> Path:
    name = clean_seat(seat)
    path = Path(root) / name / "ESCALATE.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "seat": name,
        "reason": reason,
        "turns": int(turns),
        "fingerprint": list(fingerprint) if fingerprint is not None else None,
        "at": datetime.now(UTC).isoformat(),
    }
    _write_json(path, doc)
    return path


def retryable_error(exc: BaseException) -> bool:
    """Connection drops and 502/503/504. A 409 or 422 is the caller's to keep."""
    status = getattr(exc, "status", None)
    if status is not None:
        try:
            code = int(status)
        except (TypeError, ValueError):
            code = 0
        if code in (502, 503, 504):
            detail = str(getattr(exc, "detail", "") or "")
            return "game_over" not in detail
        return False
    return exc.__class__.__name__ in {
        "ConnectError",
        "ConnectTimeout",
        "ReadTimeout",
        "WriteTimeout",
        "PoolTimeout",
        "RemoteProtocolError",
        "NetworkError",
        "ReadError",
        "WriteError",
        "CloseError",
    } or isinstance(exc, (ConnectionError, TimeoutError))


async def with_reconnect(
    call: Callable[[], Awaitable[Any]],
    *,
    heartbeat: Callable[[], Awaitable[Any]] | None = None,
    attempts: int = 5,
    sleep: Callable[[float], Awaitable[Any]] | None = None,
) -> Any:
    """Call ``call``. On a dropped session, heartbeat and try again.

    The caller keeps the same turn. This does not submit a second action
    by itself; it only repeats the function it was given.
    """
    pause = sleep or asyncio.sleep
    delay = 0.5
    last: BaseException | None = None
    tries = max(1, int(attempts))
    for index in range(tries):
        try:
            return await call()
        except Exception as exc:
            if not retryable_error(exc) or index == tries - 1:
                raise
            last = exc
            if heartbeat is not None:
                try:
                    await heartbeat()
                except Exception:
                    pass
            await pause(delay)
            delay = min(delay * 2, 8.0)
    if last is not None:
        raise last
    raise RuntimeError("reconnect failed")


class DirectiveHarness:
    """One seat's inbox, log, heartbeat file, and stuck watch."""

    def __init__(
        self,
        seat: str,
        root: str | Path,
        *,
        stuck_after: int = DEFAULT_STUCK_AFTER,
        secrets: list[str] | None = None,
        beat_s: float = BEAT_S,
    ) -> None:
        self.seat = clean_seat(seat)
        self.root = Path(root)
        self.stuck = StuckWatch(stuck_after)
        self.secrets = [value for value in (secrets or []) if value and len(value) >= 6]
        self.beat_s = float(beat_s)
        self._last_beat = 0.0
        self._holds: dict[int, int] = {}
        self.last_action = ""
        self.rejection = ""
        self.escalated = False
        self.recoveries = 0

    def active(self, game_day: int | None = None, now: datetime | None = None) -> list[Directive]:
        return load_active(self.root, self.seat, now=now, game_day=game_day)

    def directive_block(self, directives: list[Directive]) -> str:
        text = prompt_block(directives)
        if self.rejection:
            extra = "The last proposal was not submitted: " + self.rejection
            text = f"{text}\n\n{extra}" if text else extra
        if self.escalated:
            flag = (
                "ESCALATED: no progress after the recovery directive. "
                "Keep playing only legal cockpit moves. Ben has been flagged."
            )
            text = f"{text}\n\n{flag}" if text else flag
        return text

    def turn_prompt(self, obs: dict[str, Any] | None, directives: list[Directive]) -> str:
        return turn_prompt(
            obs, directives, note=self.directive_block([]) if self.rejection or self.escalated else ""
        )

    def beat_due(self, now: float | None = None) -> bool:
        import time

        clock = time.monotonic() if now is None else float(now)
        if clock - self._last_beat < self.beat_s:
            return False
        self._last_beat = clock
        return True

    def write_heartbeat(self, status: dict[str, Any] | None) -> Path:
        path = self.root / self.seat / "heartbeat.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        body = redact_obj(dict(status or {}), self.secrets)
        if isinstance(body, dict):
            body["seat"] = self.seat
            body["at"] = datetime.now(UTC).isoformat()
        _write_json(path, body if isinstance(body, dict) else {"seat": self.seat})
        return path

    def record(self, prompt: str, response: Any, outcome: Any) -> None:
        """Append one turn: prompt, response, outcome. Tokens are redacted."""
        path = self.root / self.seat / "turns.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        row = redact_obj(
            {
                "at": datetime.now(UTC).isoformat(),
                "seat": self.seat,
                "prompt": prompt,
                "response": response,
                "outcome": outcome,
            },
            self.secrets,
        )
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, default=str) + "\n")

    def mark_hold(self, turn: int) -> int:
        count = self._holds.get(int(turn), 0) + 1
        self._holds[int(turn)] = count
        return count

    def gate(
        self,
        kind: str,
        args: dict[str, Any] | None,
        obs: dict[str, Any],
        turn: int,
        *,
        allowed_kinds: frozenset[str] | set[str] | None = None,
    ) -> tuple[str, dict[str, Any], str] | None:
        """The action to submit, or None when the caller should try again.

        A legal proposal is returned unchanged. The second illegal proposal
        on the same turn becomes ``wait`` when the cockpit lists wait as legal.
        """
        proposal = {"kind": kind, "args": args or {}}
        ok, reason = validate_proposal(proposal, obs, allowed_kinds=allowed_kinds)
        if ok:
            self.rejection = ""
            self._holds.pop(int(turn), None)
            return kind, dict(args or {}), ""
        count = self.mark_hold(turn)
        self.rejection = reason
        if count >= 2:
            wait = _legal_row(obs, "wait")
            if wait and wait.get("legal"):
                self.rejection = ""
                return "wait", {}, "held: " + reason
        if count >= 4 and not self.escalated:
            self.escalated = True
            write_escalate(
                self.root,
                self.seat,
                reason=reason or "no legal action",
                fingerprint=observation_fingerprint(obs),
                turns=count,
            )
        return None

    def note_fingerprint(self, fingerprint: tuple) -> str:
        signal = self.stuck.observe(fingerprint)
        if signal == "clear":
            clear_recovery(self.root, self.seat)
        elif signal == "recover":
            self.recoveries += 1
            write_recovery(self.root, self.seat, attempt=self.recoveries, last_action=self.last_action)
        elif signal == "escalate":
            self.escalated = True
            write_escalate(
                self.root,
                self.seat,
                reason=f"no progress for {self.stuck.seen} turns",
                fingerprint=fingerprint,
                turns=self.stuck.seen,
            )
        return signal

    def wrap(self, get: Callable[..., Awaitable[Any]], post: Callable[..., Awaitable[Any]], status_path: str):
        """Retry dropped harness calls. Heartbeat uses the raw status GET."""

        async def heartbeat() -> None:
            try:
                body = await get(status_path, None)
            except Exception:
                return
            if isinstance(body, dict):
                self.write_heartbeat(body)

        async def wrapped_get(path: str, params: dict[str, Any] | None = None) -> Any:
            async def call() -> Any:
                return await get(path, params)

            beat = None if str(path).endswith("/status") else heartbeat
            return await with_reconnect(call, heartbeat=beat)

        async def wrapped_post(path: str, body: dict[str, Any]) -> Any:
            async def call() -> Any:
                return await post(path, body)

            return await with_reconnect(call, heartbeat=heartbeat)

        return wrapped_get, wrapped_post


def drop_file(inbox: str | Path, seat: str, source: str | Path) -> Path:
    """Copy a directive file into ``<inbox>/<SEAT>.json`` after it parses."""
    name = clean_seat(seat)
    try:
        payload = json.loads(Path(source).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DirectiveError("directive file could not be read") from exc
    rows = parse_directives(payload)
    if not rows:
        raise DirectiveError("directive file has no goal")
    dest = Path(inbox) / f"{name}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    _write_json(dest, {"directives": [row.as_dict() for row in rows]})
    return dest


def _rows(payload: object) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("directives"), list):
        return list(payload["directives"])
    if isinstance(payload, dict):
        return [payload]
    return []


def _one(row: object, *, source: str, order: int) -> Directive | None:
    if not isinstance(row, dict):
        return None
    goal = str(row.get("goal") or "").strip()
    if not goal:
        return None
    try:
        priority = int(row.get("priority") if row.get("priority") is not None else 0)
    except (TypeError, ValueError):
        priority = 0
    if source == "recovery":
        row_source = "recovery"
    else:
        row_source = "recovery" if str(row.get("source") or "") == "recovery" else "inbox"
    expires_at, expires_day = _expiry(row)
    return Directive(
        goal=goal,
        target=str(row.get("target") or "").strip(),
        sector=_sector(row.get("sector")),
        priority=priority,
        id=str(row.get("id") or "").strip(),
        expires_at=expires_at,
        expires_day=expires_day,
        source=row_source,
        order=order,
    )


def _expiry(row: dict) -> tuple[datetime | None, int | None]:
    day = row.get("expires_day")
    if day not in (None, ""):
        try:
            return None, int(day)
        except (TypeError, ValueError):
            pass
    raw = row.get("expires")
    if raw in (None, ""):
        return None, None
    if isinstance(raw, int):
        return None, raw
    text = str(raw).strip()
    if text.lower().startswith("day:"):
        try:
            return None, int(text.split(":", 1)[1].strip())
        except ValueError:
            return None, None
    if text.isdigit():
        return None, int(text)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None, None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed, None


def _sector(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _legal_row(obs: dict[str, Any], kind: str) -> dict[str, Any] | None:
    for row in obs.get("legal_actions") or []:
        if isinstance(row, dict) and row.get("kind") == kind:
            return row
    return None


def _choices(params: dict, key: str) -> list:
    spec = params.get(key) or {}
    if isinstance(spec, dict) and isinstance(spec.get("choices"), list):
        return list(spec["choices"])
    return []


def _in(value: object, choices: list) -> bool:
    if value in choices:
        return True
    text = str(value)
    return any(str(item) == text for item in choices)


def _check_args(kind: str, args: dict[str, Any], params: dict, obs: dict[str, Any]) -> str:
    if not isinstance(params, dict):
        params = {}
    if kind in ("warp", "plot_course"):
        if "target" not in args:
            return f"{kind} needs a target"
        if not _target_allowed(kind, args.get("target"), params, obs):
            return "target is not a cockpit choice"
    if kind == "attack" and "target" in args:
        allowed = _choices(params, "target")
        target = params.get("target") or {}
        if isinstance(target, dict):
            allowed = allowed + list(target.get("ferrengi") or [])
        if allowed and not _in(args.get("target"), allowed):
            return "target is not a cockpit choice"
    if kind == "trade":
        reason = _check_trade(args, params)
        if reason:
            return reason
    for key, spec in params.items():
        if key not in args or not isinstance(spec, dict):
            continue
        choices = spec.get("choices")
        if isinstance(choices, list) and choices and not _in(args.get(key), choices):
            return f"{key} is not a cockpit choice"
    return ""


def _target_allowed(kind: str, target: object, params: dict, obs: dict[str, Any]) -> bool:
    choices = _choices(params, "target")
    if choices:
        return _in(target, choices)
    if kind != "warp":
        return True
    outs = (obs.get("sector") or {}).get("warps_out") or []
    if not outs:
        return True
    return _in(target, list(outs))


def _check_trade(args: dict[str, Any], params: dict) -> str:
    side = str(args.get("side") or "")
    commodity = args.get("commodity")
    spec = params.get("commodity") or {}
    if not isinstance(spec, dict):
        return ""
    key = "buy_choices" if side == "buy" else "sell_choices" if side == "sell" else ""
    choices = spec.get(key) if key else None
    if isinstance(choices, list) and choices and not _in(commodity, choices):
        return "commodity is not a cockpit choice"
    qty_spec = params.get("qty") or {}
    max_by = qty_spec.get("max_by") if isinstance(qty_spec, dict) else None
    if not isinstance(max_by, dict) or commodity is None or args.get("qty") is None:
        return ""
    band = max_by.get(commodity)
    if band is None:
        band = max_by.get(str(commodity))
    if not isinstance(band, dict) or side not in band:
        return ""
    try:
        qty = int(args["qty"])
        cap = int(band[side])
    except (TypeError, ValueError):
        return "qty is not a number"
    if qty < 1 or qty > cap:
        return "qty is outside the cockpit range"
    return ""


def _is_recovery(row: Directive) -> bool:
    return row.source == "recovery" or row.id.startswith("recovery-")


def _here(obs: dict[str, Any]) -> int:
    sector = obs.get("sector") if isinstance(obs.get("sector"), dict) else {}
    try:
        return int(sector.get("id") or 0)
    except (TypeError, ValueError):
        return 0


def _recovery_step(obs: dict[str, Any], avoid_kind: str) -> dict[str, Any] | None:
    warp = _legal_row(obs, "warp")
    if warp and warp.get("legal") and avoid_kind != "warp":
        choices = _choices(warp.get("params") or {}, "target")
        if not choices:
            choices = list(((obs.get("sector") or {}).get("warps_out")) or [])
        if choices:
            return {
                "kind": "warp",
                "args": {"target": _number(choices[0])},
                "thought": "recovery: leave this sector",
            }
    for kind in ("scan", "liftoff", "wait"):
        if kind == avoid_kind:
            continue
        row = _legal_row(obs, kind)
        if row and row.get("legal"):
            return {"kind": kind, "args": {}, "thought": f"recovery: {kind}"}
    return None


def _travel(obs: dict[str, Any], sector: int, row: Directive) -> dict[str, Any] | None:
    warp = _legal_row(obs, "warp")
    if warp and warp.get("legal"):
        choices = _choices(warp.get("params") or {}, "target")
        if not choices:
            choices = list(((obs.get("sector") or {}).get("warps_out")) or [])
        if _in(sector, choices):
            return {
                "kind": "warp",
                "args": {"target": _number(sector)},
                "thought": f"directive {row.id or row.goal}: warp to {sector}",
            }
    plot = _legal_row(obs, "plot_course")
    if plot and plot.get("legal"):
        choices = _choices(plot.get("params") or {}, "target")
        execute = (plot.get("params") or {}).get("execute") or {}
        allowed = True if not isinstance(execute, dict) else bool(execute.get("legal", True))
        if allowed and (not choices or _in(sector, choices)):
            return {
                "kind": "plot_course",
                "args": {"target": int(sector), "execute": True},
                "thought": f"directive {row.id or row.goal}: plot to {sector}",
            }
    return None


def _onsite(obs: dict[str, Any], row: Directive) -> dict[str, Any] | None:
    goal = f"{row.goal} {row.target}".lower()
    if "attack" in goal:
        attack = _attack(obs, row)
        if attack is not None:
            return attack
    if "citadel" in goal:
        build = _build(obs, row)
        if build is not None:
            return build
    if "colonist" in goal or "quasar" in goal:
        moved = _colonists(obs, row, goal)
        if moved is not None:
            return moved
    return None


def _attack(obs: dict[str, Any], row: Directive) -> dict[str, Any] | None:
    attack = _legal_row(obs, "attack")
    if not attack or not attack.get("legal"):
        return None
    params = attack.get("params") or {}
    target_spec = params.get("target") or {}
    choices = list(target_spec.get("choices") or []) if isinstance(target_spec, dict) else []
    ferrengi = list(target_spec.get("ferrengi") or []) if isinstance(target_spec, dict) else []
    pool = choices + ferrengi
    if not pool:
        return None
    wanted = row.target.strip().lower()
    picked = None
    if wanted:
        for item in pool:
            if str(item).lower() == wanted:
                picked = item
                break
        if picked is None:
            names = _ids_by_name(obs)
            named = names.get(wanted)
            if named is not None and _in(named, pool):
                picked = named
    elif len(pool) == 1:
        picked = pool[0]
    if picked is None:
        return None
    args: dict[str, Any] = {"target": picked}
    qty = params.get("qty") or {}
    if isinstance(qty, dict) and qty.get("max"):
        args["qty"] = int(qty["max"])
    return {"kind": "attack", "args": args, "thought": f"directive {row.id or row.goal}: attack {picked}"}


def _ids_by_name(obs: dict[str, Any]) -> dict[str, Any]:
    found: dict[str, Any] = {}
    pools: list = []
    pools.extend(obs.get("rivals") or [])
    pools.extend(obs.get("other_players") or [])
    sector = obs.get("sector") if isinstance(obs.get("sector"), dict) else {}
    pools.extend(sector.get("occupants") or [])
    for row in pools:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip().lower()
        pid = row.get("player_id") if row.get("player_id") is not None else row.get("id")
        if name and pid is not None:
            found[name] = pid
    return found


def _build(obs: dict[str, Any], row: Directive) -> dict[str, Any] | None:
    build = _legal_row(obs, "build_citadel")
    if not build or not build.get("legal"):
        return None
    planet = _one_id(build.get("params") or {}, "planet_id")
    if planet is None:
        planet = _landed_id(obs)
    if planet is None:
        return None
    return {
        "kind": "build_citadel",
        "args": {"planet_id": planet},
        "thought": f"directive {row.id or row.goal}: build citadel",
    }


def _colonists(obs: dict[str, Any], row: Directive, goal: str) -> dict[str, Any] | None:
    assigned = _assign(obs, row, goal)
    if assigned is not None:
        return assigned
    terra = _legal_row(obs, "terra_colonists")
    if terra and terra.get("legal"):
        params = terra.get("params") or {}
        modes = _choices(params, "mode")
        max_by = (params.get("qty") or {}).get("max_by") if isinstance(params.get("qty"), dict) else {}
        if "take" in [str(item) for item in modes]:
            cap = int((max_by or {}).get("take") or 0)
            if cap > 0:
                return {
                    "kind": "terra_colonists",
                    "args": {"mode": "take", "qty": cap},
                    "thought": f"directive {row.id or row.goal}: take colonists",
                }
    shop = _legal_row(obs, "buy_equip")
    if shop and shop.get("legal"):
        params = shop.get("params") or {}
        items = _choices(params, "item")
        if _in("colonists", items):
            max_by = (params.get("qty") or {}).get("max_by") if isinstance(params.get("qty"), dict) else {}
            cap = int((max_by or {}).get("colonists") or 0)
            if cap > 0:
                return {
                    "kind": "buy_equip",
                    "args": {"item": "colonists", "qty": cap},
                    "thought": f"directive {row.id or row.goal}: buy colonists",
                }
    return None


def _assign(obs: dict[str, Any], row: Directive, goal: str) -> dict[str, Any] | None:
    assign = _legal_row(obs, "assign_colonists")
    if not assign or not assign.get("legal"):
        return None
    params = assign.get("params") or {}
    planet = _one_id(params, "planet_id") or _landed_id(obs)
    origins = _choices(params, "from")
    destinations = _choices(params, "to")
    if planet is None or not origins or not destinations:
        return None
    origin = "ship" if _in("ship", origins) else (origins[0] if len(origins) == 1 else None)
    destination = _pick_to(goal, destinations)
    if origin is None or destination is None:
        return None
    max_by = (params.get("qty") or {}).get("max_by") if isinstance(params.get("qty"), dict) else {}
    cap = int((max_by or {}).get(origin) or (max_by or {}).get(str(origin)) or 0)
    if cap <= 0:
        return None
    return {
        "kind": "assign_colonists",
        "args": {"planet_id": planet, "from": origin, "to": destination, "qty": cap},
        "thought": f"directive {row.id or row.goal}: assign colonists",
    }


def _pick_to(goal: str, choices: list) -> str | None:
    text = [str(item) for item in choices]
    for item in text:
        if item.lower() and item.lower() in goal:
            return item
    if "colonist" in goal and "colonists" in text:
        return "colonists"
    if len(text) == 1:
        return text[0]
    return None


def _one_id(params: dict, key: str) -> Any:
    spec = params.get(key)
    if isinstance(spec, dict):
        choices = spec.get("choices")
        if isinstance(choices, list) and len(choices) == 1:
            return choices[0]
        if spec.get("value") is not None:
            return spec["value"]
    if isinstance(spec, int):
        return spec
    return None


def _number(value: object) -> object:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return value


def _landed_id(obs: dict[str, Any]) -> Any:
    landed = obs.get("planet_landed")
    if isinstance(landed, dict):
        return landed.get("id") if landed.get("id") is not None else landed.get("planet_id")
    if isinstance(landed, int):
        return landed
    return None


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)
