"""Live custom clips. Off unless TW2K_VIDEO_CUSTOM=1.

The default provider is local and fake. The xAI adapter loads only when
TW2K_VIDEO_CUSTOM_PROVIDER=xai and TW2K_XAI_VIDEO_KEY is set, and that module
is not imported otherwise.

The game thread does one SQLite insert for a flagged trigger. The provider
runs on a worker thread and never opens a network connection. Caps, the
prompt hash cache, and the late-clip reel live here.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from ..engine.models import Event, EventKind, Universe, set_media_custom_hook
from ..engine.observation import _event_visible_to, event_view

log = logging.getLogger("tw2k.media.custom")

ENV_FLAG = "TW2K_VIDEO_CUSTOM"
ENV_CACHE = "TW2K_VIDEO_CUSTOM_CACHE"
ENV_PROVIDER = "TW2K_VIDEO_CUSTOM_PROVIDER"
ENV_XAI_KEY = "TW2K_XAI_VIDEO_KEY"
XAI_MODEL = "grok-imagine-video-1.5-2026-05-30"
JOB_DEADLINE_S = 600
JOB_CENTS = 33  # 4s * $0.08 + $0.01 image, in cents. $1/match allows 3.
MATCH_CAP_CENTS = 100
DAY_CAP_CENTS = 500
JOBS_PER_MATCH = 3
MODEL = "fake-local"
PARAMS = {"resolution": "480p", "duration_s": 4, "generate_audio": False}
COUNTED = ("queued", "running", "ready", "late", "discarded")
HOT_KINDS = {
    EventKind.SHIP_DESTROYED,
    EventKind.PLAYER_ELIMINATED,
    EventKind.PHOTON_HIT,
    EventKind.MINE_DETONATED,
    EventKind.FERRENGI_ATTACK,
    EventKind.COMBAT,
}

_current: CustomQueue | None = None


def current() -> CustomQueue | None:
    return _current


class FakeProvider:
    """Writes a stand-in locally. No network, no key, no paid call."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, job: dict[str, Any]) -> bytes:
        self.calls += 1
        return b"fake-webm"


def hull_family(class_value: str) -> str:
    name = (class_value or "").lower()
    if "pod" in name:
        return "pod"
    if any(bit in name for bit in ("freighter", "merchant", "cargo", "hauler", "barge")):
        return "hauler"
    if any(bit in name for bit in ("fighter", "interceptor", "corvette", "gun")):
        return "fighter"
    return "other"


def sector_look(universe: Universe, sector_id: int | None) -> str:
    sector = universe.sectors.get(sector_id) if isinstance(sector_id, int) else None
    port = getattr(sector, "port", None) if sector is not None else None
    if port is None:
        return "deep"
    code = getattr(getattr(port, "class_id", None), "name", "") or ""
    if str(code).upper() == "STARDOCK":
        return "stardock"
    return "port_near"


def _repo_manifest() -> Path:
    return Path(__file__).resolve().parents[3] / "web" / "media" / "manifest.json"


def load_custom_triggers(path: Path | None = None) -> list[dict[str, Any]]:
    data = json.loads((path or _repo_manifest()).read_text(encoding="utf-8"))
    return [t for t in data.get("triggers") or [] if t.get("custom")]


def prompt_for(universe: Universe, seat: str, event: Event, template_id: str) -> dict[str, Any]:
    """Fog-legal facts plus this seat's own hull and the sector look. No summary."""
    view = event_view(event)
    player = universe.players.get(seat)
    ship = getattr(player, "ship", None) if player is not None else None
    class_value = getattr(getattr(ship, "ship_class", None), "value", "") or ""
    facts = view.get("facts") or {}
    return {
        "template_id": template_id,
        "fields": {"kind": view.get("kind"), "facts": facts, "sector_id": view.get("sector_id")},
        "refs": {"hull": hull_family(str(class_value)), "sector_look": sector_look(universe, event.sector_id)},
        "model": _prompt_model(),
        "params": PARAMS,
    }


def _prompt_model() -> str:
    """The dated xAI alias only when that adapter is actually armed."""
    if os.environ.get(ENV_PROVIDER) == "xai" and (os.environ.get(ENV_XAI_KEY) or "").strip():
        return XAI_MODEL
    return MODEL


def prompt_hash(prompt: dict[str, Any]) -> str:
    raw = json.dumps(prompt, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _citadel_owner(universe: Universe, event: Event) -> str | None:
    """Citadel completion has no actor. The planet owner is the seat that sees it."""
    if event.kind != EventKind.CITADEL_COMPLETE:
        return None
    pid = (event.payload or {}).get("planet_id")
    planet = universe.planets.get(pid) if isinstance(pid, int) else None
    if planet is None:
        return None
    return planet.owner_id


def _rule_ok(rule: str, event: Event, seat: str) -> bool:
    facts = (event_view(event).get("facts") or {})

    def pred(name: str) -> bool:
        if name == "self":
            return event.actor_id == seat
        if name == "self_victim":
            return facts.get("victim") == seat
        return False

    for part in str(rule or "").split("&&"):
        token = part.strip()
        if not token:
            return False
        neg = token.startswith("!")
        ok = pred(token[1:] if neg else token)
        if neg:
            ok = not ok
        if not ok:
            return False
    return True


class CustomQueue:
    def __init__(
        self,
        cache_dir: Path,
        provider: Callable[[dict[str, Any]], bytes] | None = None,
        *,
        triggers: list[dict[str, Any]] | None = None,
        match_cap_cents: int = MATCH_CAP_CENTS,
        day_cap_cents: int = DAY_CAP_CENTS,
        jobs_per_match: int = JOBS_PER_MATCH,
        manifest_path: Path | None = None,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.provider = provider or FakeProvider()
        self.triggers = triggers if triggers is not None else load_custom_triggers()
        self.kinds = {t["kind"] for t in self.triggers}
        self.match_cap_cents = match_cap_cents
        self.day_cap_cents = day_cap_cents
        self.jobs_per_match = jobs_per_match
        self.manifest_path = manifest_path or _repo_manifest()
        self._db_path = self.cache_dir / "jobs.sqlite"
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
              id INTEGER PRIMARY KEY,
              hash TEXT NOT NULL,
              seat TEXT NOT NULL,
              match_id TEXT NOT NULL,
              status TEXT NOT NULL,
              created REAL NOT NULL,
              cost_cents INTEGER NOT NULL,
              trigger_seq INTEGER NOT NULL,
              clip_key TEXT NOT NULL,
              day TEXT NOT NULL,
              swap INTEGER NOT NULL DEFAULT 0,
              prompt TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS seen (
              hash TEXT NOT NULL,
              seat TEXT NOT NULL,
              match_id TEXT NOT NULL,
              PRIMARY KEY (hash, seat, match_id)
            );
            CREATE TABLE IF NOT EXISTS notices (
              seat TEXT NOT NULL,
              seq INTEGER NOT NULL,
              clip_key TEXT NOT NULL,
              hash TEXT NOT NULL,
              PRIMARY KEY (seat, seq)
            );
            """
        )
        self._conn.commit()
        cols = {row[1] for row in self._conn.execute("PRAGMA table_info(jobs)")}
        if "prompt" not in cols:
            self._conn.execute("ALTER TABLE jobs ADD COLUMN prompt TEXT NOT NULL DEFAULT ''")
            self._conn.commit()
        self._universes: dict[str, Universe] = {}

    @property
    def worker_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> CustomQueue:
        global _current
        if self._thread is not None:
            return self
        with self._lock:
            self._conn.execute(
                "UPDATE jobs SET status='expired', swap=0 WHERE status IN ('queued','running')"
            )
            self._conn.commit()
        set_media_custom_hook(self._hook)
        _current = self
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="tw2k-custom-queue", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        global _current
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            if not self._thread.is_alive():
                self._thread = None
        if _current is self:
            _current = None
            set_media_custom_hook(None)
        try:
            self._conn.close()
        except sqlite3.ProgrammingError:
            pass

    def _hook(self, universe: Universe, event: Event) -> None:
        try:
            self.on_emit(universe, event)
        except Exception:
            log.exception("custom queue hook failed")

    def on_emit(self, universe: Universe, event: Event) -> None:
        if event.kind.value not in self.kinds:
            return
        for seat in list(universe.players):
            self._consider(universe, event, seat)

    def _consider(self, universe: Universe, event: Event, seat: str) -> None:
        owner = _citadel_owner(universe, event)
        if owner != seat and not _event_visible_to(event, seat, universe):
            return
        trigger = next((t for t in self.triggers if t["kind"] == event.kind.value and _rule_ok(t["rule"], event, seat)), None)
        if trigger is None and owner == seat:
            trigger = next((t for t in self.triggers if t.get("clip") == "planet.citadel" and t["kind"] == event.kind.value), None)
        if trigger is None:
            return
        clip = str(trigger["clip"])
        if clip == "planet.genesis" and not (event.payload or {}).get("is_first"):
            return
        prompt = prompt_for(universe, seat, event, clip)
        digest = prompt_hash(prompt)
        match_id = f"{getattr(universe.config, 'seed', 0)}:{id(universe)}"
        self._universes[match_id] = universe
        self._enqueue(seat, event, clip, digest, match_id, json.dumps(prompt, sort_keys=True))

    def _enqueue(self, seat, event, clip, digest, match_id, prompt_json: str) -> None:
        day = date.today().isoformat()
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO notices (seat, seq, clip_key, hash) VALUES (?, ?, ?, ?)",
                (seat, event.seq, clip, digest),
            )
            self._conn.execute(
                "INSERT OR IGNORE INTO seen (hash, seat, match_id) VALUES (?, ?, ?)",
                (digest, seat, match_id),
            )
            cached = self.cache_dir / f"{digest}.webm"
            if cached.is_file():
                blocked = self._later_than(match_id, seat, event.seq)
                self._insert_job(
                    digest, seat, match_id, "late" if blocked else "cached", 0,
                    event.seq, clip, day, swap=0 if blocked else 1, prompt=prompt_json,
                )
                self._conn.commit()
                return
            existing = self._conn.execute(
                "SELECT id FROM jobs WHERE hash=? AND match_id=? AND status IN ('queued','running','ready','late')",
                (digest, match_id),
            ).fetchone()
            if existing is not None:
                self._conn.commit()
                return
            count = self._conn.execute(
                f"SELECT COUNT(*) FROM jobs WHERE match_id=? AND status IN ({','.join('?' * len(COUNTED))})",
                (match_id, *COUNTED),
            ).fetchone()[0]
            if count >= self.jobs_per_match:
                self._conn.commit()
                log.warning("custom job refused: match cap of %s for seat %s", self.jobs_per_match, seat)
                return
            spent_match = self._conn.execute(
                f"SELECT COALESCE(SUM(cost_cents),0) FROM jobs WHERE match_id=? AND status IN ({','.join('?' * len(COUNTED))})",
                (match_id, *COUNTED),
            ).fetchone()[0]
            spent_day = self._conn.execute(
                f"SELECT COALESCE(SUM(cost_cents),0) FROM jobs WHERE day=? AND status IN ({','.join('?' * len(COUNTED))})",
                (day, *COUNTED),
            ).fetchone()[0]
            if spent_match + JOB_CENTS > self.match_cap_cents:
                self._conn.commit()
                log.warning("custom job refused: match cap for seat %s", seat)
                return
            if spent_day + JOB_CENTS > self.day_cap_cents:
                self._conn.commit()
                log.warning("custom job refused: day cap for seat %s", seat)
                return
            self._insert_job(
                digest, seat, match_id, "queued", JOB_CENTS, event.seq, clip, day,
                swap=0, prompt=prompt_json,
            )
            self._conn.commit()
        self._wake.set()

    def _insert_job(self, digest, seat, match_id, status, cost, seq, clip, day, *, swap: int, prompt: str = "") -> None:
        self._conn.execute(
            """INSERT INTO jobs (hash, seat, match_id, status, created, cost_cents, trigger_seq, clip_key, day, swap, prompt)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (digest, seat, match_id, status, time.time(), cost, seq, clip, day, swap, prompt),
        )

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._expire_deadlines()
                job = self._claim()
            except sqlite3.ProgrammingError:
                break
            if job is None:
                self._wake.wait(0.05)
                self._wake.clear()
                continue
            try:
                data = self.provider(dict(job))
            except Exception:
                log.exception("custom provider failed")
                data = None
            if self._stop.is_set():
                break
            try:
                self._finish(job, data)
            except sqlite3.ProgrammingError:
                break

    def _expire_deadlines(self) -> None:
        cutoff = time.time() - JOB_DEADLINE_S
        with self._lock:
            self._conn.execute(
                """UPDATE jobs SET status='expired', swap=0
                   WHERE status IN ('queued','running') AND created < ?""",
                (cutoff,),
            )
            self._conn.commit()

    def _claim(self) -> sqlite3.Row | None:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM jobs WHERE status='queued' ORDER BY id"
            ).fetchall()
            for row in rows:
                running = self._conn.execute(
                    "SELECT 1 FROM jobs WHERE seat=? AND match_id=? AND status='running'",
                    (row["seat"], row["match_id"]),
                ).fetchone()
                if running is not None:
                    continue
                self._conn.execute("UPDATE jobs SET status='running' WHERE id=?", (row["id"],))
                self._conn.commit()
                return row
        return None

    def _finish(self, job: sqlite3.Row, data: bytes | None) -> None:
        digest = job["hash"]
        status = "discarded"
        swap = 0
        if data:
            blocked = self._blocked_for(job)
            status = "late" if blocked else "ready"
            swap = 0 if blocked else 1
        with self._lock:
            cur = self._conn.execute(
                "UPDATE jobs SET status=?, swap=? WHERE id=? AND status='running'",
                (status, swap, job["id"]),
            )
            self._conn.commit()
            if cur.rowcount != 1:
                return
        if not data:
            return
        webm = self.cache_dir / f"{digest}.webm"
        meta_path = self.cache_dir / f"{digest}.json"
        meta = {
            "hash": digest,
            "trust": "auto",
            "approved_by": None,
            "status": status,
            "clip_key": job["clip_key"],
            "badge": "live-generated",
        }
        try:
            webm.write_bytes(data)
            meta_path.write_text(json.dumps(meta), encoding="utf-8")
        except Exception:
            webm.unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)
            with self._lock:
                self._conn.execute(
                    "UPDATE jobs SET status='discarded', swap=0 WHERE id=?",
                    (job["id"],),
                )
                self._conn.commit()
            log.exception("custom clip cache write failed")

    def _later_than(self, match_id: str, seat: str, seq: int) -> bool:
        universe = self._universes.get(match_id)
        if universe is None:
            return False
        for ev in universe.events:
            if ev.seq <= seq:
                continue
            if not _event_visible_to(ev, seat, universe):
                continue
            if ev.kind == EventKind.CITADEL_COMPLETE and ev.actor_id is None:
                continue
            if ev.actor_id == seat or ev.kind in HOT_KINDS:
                return True
        return False

    def _blocked_for(self, job: sqlite3.Row) -> bool:
        return self._later_than(job["match_id"], job["seat"], job["trigger_seq"])

    def placeholder(self, seat: str, seq: int) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT clip_key FROM notices WHERE seat=? AND seq=?", (seat, seq)
            ).fetchone()
        return row["clip_key"] if row else None

    def job_for(self, seat: str, seq: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                """SELECT jobs.* FROM jobs
                   JOIN seen ON seen.hash=jobs.hash AND seen.seat=? AND seen.match_id=jobs.match_id
                   WHERE jobs.trigger_seq=? AND jobs.seat=?
                   ORDER BY jobs.id DESC LIMIT 1""",
                (seat, seq, seat),
            ).fetchone()
        return dict(row) if row else None

    def feed_for(self, seat: str, since: int = 0) -> dict[str, Any]:
        ready, moments = [], []
        with self._lock:
            since = int(since)
            if since < 0:
                since = 0
            newest_id = int(self._conn.execute(
                "SELECT COALESCE(MAX(id), 0) FROM jobs WHERE seat=?", (seat,)
            ).fetchone()[0])
            if since > newest_id:
                since = 0
            # A running job blocks only its own match. The cursor still stops
            # at that hole so a later poll can deliver it when it finishes.
            pending = self._conn.execute(
                """SELECT id, match_id FROM jobs
                   WHERE seat=? AND id>? AND status IN ('queued','running')
                   ORDER BY id LIMIT 1""",
                (seat, since),
            ).fetchone()
            sql = """SELECT jobs.* FROM jobs JOIN seen ON seen.hash=jobs.hash AND seen.seat=?
                     AND seen.match_id=jobs.match_id
                     WHERE jobs.seat=? AND jobs.id > ? AND jobs.status IN ('ready','late','cached')"""
            args: list[Any] = [seat, seat, since]
            if pending is not None:
                sql += " AND (jobs.id < ? OR jobs.match_id != ?)"
                args.extend([int(pending["id"]), pending["match_id"]])
            rows = self._conn.execute(sql, args).fetchall()
            pending_flag = self._conn.execute(
                "SELECT 1 FROM jobs WHERE seat=? AND status IN ('queued','running') LIMIT 1",
                (seat,),
            ).fetchone() is not None
        hole = int(pending["id"]) if pending is not None else None
        newest = since
        for row in rows:
            rid = int(row["id"])
            if hole is None or rid < hole:
                newest = max(newest, rid)
            note = self._note(row)
            if row["status"] in ("ready", "cached") and row["swap"]:
                ready.append(note)
            elif row["status"] in ("late", "cached"):
                moments.append(note)
        return {"ready": ready, "moments": moments, "next_since": newest, "pending": pending_flag}

    def moments_for(self, seat: str) -> list[dict[str, Any]]:
        return self.feed_for(seat)["moments"]

    def _note(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "hash": row["hash"],
            "seq": row["trigger_seq"],
            "placeholder": row["clip_key"],
            "swap": bool(row["swap"]),
            "trust": "auto",
            "approved_by": None,
            "badge": "live-generated",
            "status": row["status"],
            "caption": str(row["clip_key"]).rsplit(".", 1)[-1].replace("_", " "),
        }

    def clip_bytes(self, seat: str, digest: str) -> bytes | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM seen WHERE hash=? AND seat=?", (digest, seat)
            ).fetchone()
        if row is None:
            return None
        path = self.cache_dir / f"{digest}.webm"
        if not path.is_file():
            return None
        return path.read_bytes()

    def promote_to_library(self, digest: str) -> bool:
        """A trust:auto clip never enters the base manifest from this queue."""
        return False


def start_if_enabled(cache_dir: Path | None = None) -> CustomQueue | None:
    """Start the worker only when the flag is exactly \"1\". Otherwise do nothing."""
    if os.environ.get(ENV_FLAG) != "1":
        return None
    override = os.environ.get(ENV_CACHE)
    folder = cache_dir or (Path(override) if override else (_repo_manifest().parent / "clips" / "custom"))
    provider = None
    if os.environ.get(ENV_PROVIDER) == "xai" and (os.environ.get(ENV_XAI_KEY) or "").strip():
        from .xai_video import XaiImagineProvider

        provider = XaiImagineProvider(key=(os.environ.get(ENV_XAI_KEY) or "").strip())
    elif os.environ.get(ENV_PROVIDER) == "xai":
        log.warning("xai video provider requested without a key; using the local stand-in")
    return CustomQueue(folder, provider).start()
