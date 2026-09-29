"""Captain-to-pilot notes for one seat. Plain text only, own seat only.

The log lives under ``.tw2k/bridge/<match>/<seat>.sqlite``. A heuristic or LLM
seat never reads it. The cockpit renders every string with textContent.
"""

from __future__ import annotations

import os
import re
import sqlite3
import threading
import time
from pathlib import Path

MAX_TEXT = 500
ACKS = frozenset({"taken", "done", "declined"})
_HITS: dict[str, list[float]] = {}
_LOCK = threading.Lock()
_WINDOW_S = 60.0
_MAX_POSTS = 20


def root_dir() -> Path:
    raw = os.environ.get("TW2K_BRIDGE_DIR", "").strip()
    if raw:
        return Path(raw)
    from .harness_tokens import _repo_root

    return _repo_root() / ".tw2k" / "bridge"


def _safe(match_id: str, seat: str) -> tuple[str, str]:
    match = re.sub(r"[^A-Za-z0-9._-]", "_", match_id)[:80] or "match"
    who = re.sub(r"[^A-Za-z0-9._-]", "", seat.upper())[:16]
    if not who:
        raise ValueError("seat")
    return match, who


def _connect(match_id: str, seat: str) -> sqlite3.Connection:
    match, who = _safe(match_id, seat)
    folder = root_dir() / match
    folder.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(folder / f"{who}.sqlite", timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS messages (
             id INTEGER PRIMARY KEY,
             role TEXT NOT NULL,
             text TEXT NOT NULL,
             status TEXT NOT NULL DEFAULT '',
             ack_of INTEGER,
             created REAL NOT NULL
           )"""
    )
    return conn


def _row(row: sqlite3.Row) -> dict:
    return {
        "id": int(row["id"]),
        "role": row["role"],
        "text": row["text"],
        "status": row["status"],
        "ack_of": row["ack_of"],
        "created": row["created"],
    }


def _allow(seat: str) -> bool:
    now = time.monotonic()
    hits = [t for t in _HITS.get(seat, []) if now - t < _WINDOW_S]
    if len(hits) >= _MAX_POSTS:
        _HITS[seat] = hits
        return False
    hits.append(now)
    _HITS[seat] = hits
    return True


def _clean(text: str) -> str:
    body = (text or "").strip()
    if not body or len(body) > MAX_TEXT:
        raise ValueError("text")
    return body


def post(match_id: str, seat: str, role: str, text: str, ack_of: int | None = None) -> dict:
    if role not in ("captain", "pilot"):
        raise ValueError("role")
    body = _clean(text)
    with _LOCK:
        if not _allow(seat):
            raise PermissionError("rate")
        conn = _connect(match_id, seat)
        try:
            if ack_of is not None:
                target = conn.execute(
                    "SELECT id, role FROM messages WHERE id=?", (int(ack_of),)
                ).fetchone()
                if target is None or target["role"] != "captain":
                    raise LookupError("ack_of")
            status = "pending" if role == "captain" else ""
            cur = conn.execute(
                "INSERT INTO messages (role, text, status, ack_of, created) VALUES (?,?,?,?,?)",
                (role, body, status, ack_of, time.time()),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM messages WHERE id=?", (cur.lastrowid,)).fetchone()
            return _row(row)
        finally:
            conn.close()


def ack(match_id: str, seat: str, msg_id: int, status: str) -> dict:
    if status not in ACKS:
        raise ValueError("status")
    with _LOCK:
        conn = _connect(match_id, seat)
        try:
            row = conn.execute("SELECT * FROM messages WHERE id=?", (int(msg_id),)).fetchone()
            if row is None or row["role"] != "captain":
                raise LookupError("id")
            conn.execute("UPDATE messages SET status=? WHERE id=?", (status, int(msg_id)))
            conn.commit()
            fresh = conn.execute("SELECT * FROM messages WHERE id=?", (int(msg_id),)).fetchone()
            return _row(fresh)
        finally:
            conn.close()


def since(match_id: str, seat: str, after: int) -> list[dict]:
    with _LOCK:
        conn = _connect(match_id, seat)
        try:
            rows = conn.execute(
                "SELECT * FROM messages WHERE id>? ORDER BY id", (int(after),)
            ).fetchall()
            return [_row(row) for row in rows]
        finally:
            conn.close()


def pending(match_id: str, seat: str) -> list[dict]:
    with _LOCK:
        conn = _connect(match_id, seat)
        try:
            rows = conn.execute(
                "SELECT * FROM messages WHERE role='captain' AND status IN ('pending','taken') ORDER BY id"
            ).fetchall()
            return [_row(row) for row in rows]
        finally:
            conn.close()
