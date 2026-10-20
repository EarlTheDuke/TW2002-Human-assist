"""v3.11 player communications. Off, the older hail, broadcast, radio, and memo stay.

On, four channels share one line length, one pause between sends, and a turn log:

- Sub-space radio. Channel 0 (and an unset channel) is off. Channels 1 to 60000
  are heard by every other trader tuned to that same channel. EIS CompMisc and
  GlobalCommands. The Bible's corp-only reading stays on the older radio switch.
- Fed Comm. One line to every trader who has not turned the comm-link off.
- A private hail to one trader in the same sector. An offline trader, or one who
  has turned hails off, does not receive it, and it is not stored as mail.
  v3.11 revision history: a hail is not the mail service.
- A corporation memo to the other members only.

Each received line is shown at the start of a turn and dropped after
HAIL_SHOW_SECONDS (the revision's 10-second message life).
"""

from __future__ import annotations

import time

from . import constants as K
from .actions import Action, ActionResult
from .models import EventKind, Universe


def _line(kind: str, name: str, message: str, *, channel: int | None = None, ticker: str = "") -> str:
    if kind == "fedcomm":
        return f"Federation comm-link, {name}: {message}"
    if kind == "radio":
        return f"Sub-space radio [{int(channel)}] {name}: {message}"
    if kind == "hail":
        return f"{name} hails you: {message}"
    return f"Corporate memo ({ticker}) {name}: {message}"


def _fresh(rows: list, now: float) -> list:
    limit = float(K.HAIL_SHOW_SECONDS)
    kept = []
    for row in rows or []:
        try:
            at = float(row.get("at") or 0)
        except (TypeError, ValueError, AttributeError):
            continue
        if now - at <= limit:
            kept.append(row)
    return kept[-40:]


def _text(raw) -> tuple[str, str | None]:
    text = " ".join(str(raw or "").split())
    if not text:
        return "", "type a message"
    if len(text) > int(K.COMMS_LINE_MAX):
        return "", f"a message line is {int(K.COMMS_LINE_MAX)} characters or less"
    return text, None


def _pause(player, now: float) -> str | None:
    last = float(getattr(player, "comms_sent_at", 0) or 0)
    if last and now - last < float(K.COMMS_MIN_GAP_S):
        return "wait a moment before the next message"
    return None


def _stamp(player, now: float) -> None:
    player.comms_sent_at = float(now)


def _give(player, row: dict, now: float) -> None:
    log = _fresh(list(getattr(player, "turn_log", None) or []), now)
    log.append(row)
    player.turn_log = log[-40:]


def _emit(universe: Universe, pid: str, kind: EventKind, summary: str, heard: list[str], payload: dict) -> None:
    universe.emit(
        kind,
        actor_id=pid,
        payload={**payload, "_witnesses": [pid, *heard]},
        summary=summary,
    )


def seat_view(universe: Universe, player) -> tuple[list[dict], dict]:
    """The turn log and the comms panel facts. Incoming lines, plus a hail that was not heard."""
    now = time.time()
    rows = _fresh(list(getattr(player, "turn_log", None) or []), now)
    player.turn_log = rows
    public = []
    for row in rows:
        public.append({
            "kind": row.get("kind") or "",
            "from": row.get("from") or "",
            "from_name": row.get("from_name") or "",
            "message": row.get("message") or "",
            "line": row.get("line") or "",
            "channel": row.get("channel"),
            "ticker": row.get("ticker") or "",
        })
    here = []
    for other in universe.players.values():
        if other.id == player.id or not other.alive:
            continue
        if int(other.sector_id) != int(player.sector_id):
            continue
        here.append({"id": other.id, "name": other.name})
    here.sort(key=lambda item: item["id"])
    channel = player.radio_channel
    meta = {
        "line_max": int(K.COMMS_LINE_MAX),
        "gap_s": float(K.COMMS_MIN_GAP_S),
        "show_s": int(K.HAIL_SHOW_SECONDS),
        "radio_channel": int(channel) if channel else 0,
        "fedcomm": not bool(getattr(player, "fedcomm_mute", False)),
        "hails": not bool(getattr(player, "hail_mute", False)),
        "here": here,
        "corp": player.corp_ticker or "",
    }
    return public, meta


def send_radio(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    args = action.args or {}
    if "channel" in args:
        try:
            channel = int(args.get("channel"))
        except (TypeError, ValueError):
            return ActionResult(ok=False, error="radio channel must be 0 to 60000")
        if channel < 0 or channel > int(K.RADIO_CHANNEL_MAX):
            return ActionResult(ok=False, error="radio channel must be 0 to 60000")
        player.radio_channel = channel
    message = args.get("message")
    if message is None or str(message) == "":
        return ActionResult(ok=True, turns_spent=0)
    text, bad = _text(message)
    if bad:
        return ActionResult(ok=False, error=bad)
    tuned = int(player.radio_channel or 0)
    if tuned <= 0:
        return ActionResult(ok=False, error="the radio is off. Pick a channel from 1 to 60000")
    now = time.time()
    wait = _pause(player, now)
    if wait:
        return ActionResult(ok=False, error=wait)
    heard: list[str] = []
    line = _line("radio", player.name, text, channel=tuned)
    for other in universe.players.values():
        if other.id == pid or not other.alive:
            continue
        if int(other.radio_channel or 0) != tuned:
            continue
        _give(other, {
            "kind": "radio", "from": pid, "from_name": player.name, "message": text,
            "channel": tuned, "line": line, "at": now,
        }, now)
        heard.append(other.id)
    _stamp(player, now)
    _emit(universe, pid, EventKind.BROADCAST, line, heard, {"channel": tuned, "message": text, "link": "radio"})
    return ActionResult(ok=True, turns_spent=0)


def send_fed(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    args = action.args or {}
    if "listen" in args:
        player.fedcomm_mute = not bool(args.get("listen"))
    message = args.get("message")
    if message is None or str(message) == "":
        return ActionResult(ok=True, turns_spent=0)
    text, bad = _text(message)
    if bad:
        return ActionResult(ok=False, error=bad)
    now = time.time()
    wait = _pause(player, now)
    if wait:
        return ActionResult(ok=False, error=wait)
    heard: list[str] = []
    line = _line("fedcomm", player.name, text)
    for other in universe.players.values():
        if other.id == pid or not other.alive:
            continue
        if bool(getattr(other, "fedcomm_mute", False)):
            continue
        _give(other, {
            "kind": "fedcomm", "from": pid, "from_name": player.name, "message": text,
            "line": line, "at": now,
        }, now)
        heard.append(other.id)
    _stamp(player, now)
    _emit(universe, pid, EventKind.BROADCAST, line, heard, {"message": text, "link": "fed"})
    return ActionResult(ok=True, turns_spent=0)


def send_hail(universe: Universe, pid: str, action: Action) -> ActionResult:
    from .presence import seat_online

    player = universe.players[pid]
    target_id = (action.args or {}).get("target")
    target = universe.players.get(target_id) if isinstance(target_id, str) else None
    if target is None or not target.alive:
        return ActionResult(ok=False, error="unknown target")
    if int(target.sector_id) != int(player.sector_id):
        return ActionResult(ok=False, error="that trader is not in this sector")
    text, bad = _text((action.args or {}).get("message"))
    if bad:
        return ActionResult(ok=False, error=bad)
    now = time.time()
    wait = _pause(player, now)
    if wait:
        return ActionResult(ok=False, error=wait)
    _stamp(player, now)
    quiet = (not seat_online(universe, target.id)) or bool(getattr(target, "hail_mute", False))
    if quiet:
        line = f"Your hail to {target.name} fell on deaf ears."
        _give(player, {
            "kind": "hail", "from": pid, "from_name": player.name, "message": text,
            "line": line, "at": now,
        }, now)
        _emit(universe, pid, EventKind.HAIL, line, [], {"target": target.id, "message": text, "delivery": "lost"})
        return ActionResult(ok=True, turns_spent=0)
    line = _line("hail", player.name, text)
    _give(target, {
        "kind": "hail", "from": pid, "from_name": player.name, "message": text,
        "line": line, "at": now,
    }, now)
    _emit(
        universe, pid, EventKind.HAIL, line, [target.id],
        {"target": target.id, "message": text, "delivery": "live"},
    )
    return ActionResult(ok=True, turns_spent=0)


def send_corp(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    if not player.corp_ticker or player.corp_ticker not in universe.corporations:
        return ActionResult(ok=False, error="not in a corporation")
    corp = universe.corporations[player.corp_ticker]
    if K.corp_rules_on() and K.CORP_MEMO_SENDERS == "ceo" and corp.ceo_id != pid:
        return ActionResult(ok=False, error="only the C.E.O. may send a memo")
    text, bad = _text((action.args or {}).get("message"))
    if bad:
        return ActionResult(ok=False, error=bad)
    now = time.time()
    wait = _pause(player, now)
    if wait:
        return ActionResult(ok=False, error=wait)
    heard: list[str] = []
    line = _line("corp", player.name, text, ticker=corp.ticker)
    for mid in corp.member_ids:
        if mid == pid:
            continue
        other = universe.players.get(mid)
        if other is None or not other.alive:
            continue
        _give(other, {
            "kind": "corp", "from": pid, "from_name": player.name, "message": text,
            "ticker": corp.ticker, "line": line, "at": now,
        }, now)
        heard.append(other.id)
    _stamp(player, now)
    _emit(
        universe, pid, EventKind.CORP_MEMO, line, heard,
        {"ticker": corp.ticker, "message": text},
    )
    return ActionResult(ok=True, turns_spent=0)
