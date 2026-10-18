"""SQLite state for the lobby: guests (hashed cookies), games, seats (hashed tokens)."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS guests (
    id TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    accepted_at REAL,
    last_seen REAL
);
CREATE TABLE IF NOT EXISTS games (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    creator TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    status TEXT NOT NULL,
    port INTEGER,
    pid INTEGER,
    settings TEXT NOT NULL,
    listed INTEGER NOT NULL DEFAULT 1,
    restarts INTEGER NOT NULL DEFAULT 0,
    last_activity REAL NOT NULL,
    note TEXT
);
CREATE TABLE IF NOT EXISTS seats (
    game_id TEXT NOT NULL,
    seat TEXT NOT NULL,
    guest_id TEXT,
    token_hash TEXT,
    claimed_at REAL,
    PRIMARY KEY (game_id, seat)
);
CREATE TABLE IF NOT EXISTS flags (
    name TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

ACTIVE = ("starting", "running", "sleeping")
LIVE = ("starting", "running")


class Store:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(self.path), check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript(SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def _x(self, sql: str, args: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._db.execute(sql, args).fetchall()

    # guests -------------------------------------------------------------
    def touch_guest(self, gid: str) -> dict[str, Any]:
        now = time.time()
        self._x("INSERT OR IGNORE INTO guests (id, created_at, last_seen) VALUES (?, ?, ?)", (gid, now, now))
        self._x("UPDATE guests SET last_seen=? WHERE id=?", (now, gid))
        row = self._x("SELECT * FROM guests WHERE id=?", (gid,))
        return dict(row[0])

    def guest(self, gid: str) -> dict[str, Any] | None:
        row = self._x("SELECT * FROM guests WHERE id=?", (gid,))
        return dict(row[0]) if row else None

    def accept(self, gid: str) -> None:
        self.touch_guest(gid)
        self._x("UPDATE guests SET accepted_at=? WHERE id=?", (time.time(), gid))

    # games --------------------------------------------------------------
    def add_game(self, gid: str, *, name: str, creator: str, settings: dict, listed: bool, seats: list[str]) -> None:
        now = time.time()
        self._x(
            "INSERT INTO games (id, name, creator, created_at, updated_at, status, settings, listed, last_activity)"
            " VALUES (?, ?, ?, ?, ?, 'starting', ?, ?, ?)",
            (gid, name, creator, now, now, json.dumps(settings, sort_keys=True), 1 if listed else 0, now),
        )
        for seat in seats:
            self._x("INSERT INTO seats (game_id, seat) VALUES (?, ?)", (gid, seat))

    def game(self, gid: str) -> dict[str, Any] | None:
        row = self._x("SELECT * FROM games WHERE id=?", (gid,))
        return _game(row[0]) if row else None

    def games(self, statuses: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
        if statuses:
            marks = ",".join("?" * len(statuses))
            rows = self._x(f"SELECT * FROM games WHERE status IN ({marks}) ORDER BY created_at", statuses)
        else:
            rows = self._x("SELECT * FROM games ORDER BY created_at")
        return [_game(r) for r in rows]

    def set_game(self, gid: str, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = time.time()
        cols = ", ".join(f"{k}=?" for k in fields)
        self._x(f"UPDATE games SET {cols} WHERE id=?", (*fields.values(), gid))

    def count_games(self, statuses: tuple[str, ...]) -> int:
        marks = ",".join("?" * len(statuses))
        return int(self._x(f"SELECT COUNT(*) FROM games WHERE status IN ({marks})", statuses)[0][0])

    def count_human_seats(self, statuses: tuple[str, ...] = ACTIVE) -> int:
        marks = ",".join("?" * len(statuses))
        row = self._x(
            f"SELECT COUNT(*) FROM seats s JOIN games g ON g.id=s.game_id WHERE g.status IN ({marks})", statuses
        )
        return int(row[0][0])

    # seats --------------------------------------------------------------
    def seats(self, gid: str) -> list[dict[str, Any]]:
        return [dict(r) for r in self._x("SELECT * FROM seats WHERE game_id=? ORDER BY seat", (gid,))]

    def guest_seat(self, gid: str, guest: str) -> str | None:
        row = self._x("SELECT seat FROM seats WHERE game_id=? AND guest_id=?", (gid, guest))
        return row[0][0] if row else None

    def claim_seat(self, gid: str, guest: str, seat: str | None = None) -> str | None:
        """Atomically give the guest an open seat (the named one, or the first); returns it or None."""
        with self._lock:
            if seat is None:
                row = self._db.execute(
                    "SELECT seat FROM seats WHERE game_id=? AND guest_id IS NULL ORDER BY seat LIMIT 1", (gid,)
                ).fetchone()
            else:
                row = (seat,)
            if row is None:
                return None
            cur = self._db.execute(
                "UPDATE seats SET guest_id=?, claimed_at=? WHERE game_id=? AND seat=? AND guest_id IS NULL",
                (guest, time.time(), gid, row[0]),
            )
            return row[0] if cur.rowcount == 1 else None

    def set_seat_hash(self, gid: str, seat: str, token_hash: str | None) -> None:
        self._x("UPDATE seats SET token_hash=? WHERE game_id=? AND seat=?", (token_hash, gid, seat))

    def guest_games(self, guest: str) -> list[dict[str, Any]]:
        rows = self._x(
            "SELECT g.*, s.seat AS my_seat FROM games g JOIN seats s ON s.game_id=g.id WHERE s.guest_id=?"
            " ORDER BY g.created_at",
            (guest,),
        )
        return [_game(r) for r in rows]

    # flags --------------------------------------------------------------
    def flag(self, name: str, default: str = "") -> str:
        row = self._x("SELECT value FROM flags WHERE name=?", (name,))
        return row[0][0] if row else default

    def set_flag(self, name: str, value: str) -> None:
        self._x("INSERT INTO flags (name, value) VALUES (?, ?) ON CONFLICT(name) DO UPDATE SET value=excluded.value",
                (name, value))


def _game(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["settings"] = json.loads(d["settings"])
    d["listed"] = bool(d["listed"])
    return d
