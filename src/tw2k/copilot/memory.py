"""Copilot long-term memory — per-player preferences that survive restarts.

A very deliberate MVP:

* One JSON file per human (``saves/copilot_memory_{player_id}.json``).
* Three buckets — ``preferences`` (free-form key/value strings the human
  tells the copilot to remember, e.g. ``preferred_port_class = "7"``),
  ``learned_rules`` (one-line natural-language rules the copilot has
  auto-captured from confirmed plans), and ``stats`` (monotonic
  counters like ``session_count`` / ``plans_confirmed``).
* Public API is pure Python — loads/saves are cheap filesystem calls
  and never go through the LLM so every test can poke it directly.

The memory is surfaced to ``ChatAgent`` as a short summary string that
it can splice into the system prompt, and to the cockpit UI via
``GET /api/copilot/memory`` so the right panel can render a
"Memory (3 prefs, 2 rules)" chip.

This is the H5.1 deliverable. Richer retrieval (vector search over
long chat transcripts, cross-match habit learning, etc.) is future
work; the on-disk JSON shape is forward-compatible because we keep
everything inside a single top-level ``dict``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Hard cap on each bucket so a runaway learner can't inflate the file
# without bound. These match the soft numbers the UI chip shows.
MAX_PREFERENCES = 64
MAX_LEARNED_RULES = 64
MAX_FAVORITE_SECTORS = 32

MEMORY_FILE_PREFIX = "copilot_memory_"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class CopilotMemory(BaseModel):
    """Serialisable snapshot of everything we remember for one player."""

    player_id: str
    preferences: dict[str, str] = Field(default_factory=dict)
    learned_rules: list[str] = Field(default_factory=list)
    favorite_sectors: list[int] = Field(default_factory=list)
    stats: dict[str, int] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    # ------------------- mutation helpers -------------------------------

    def remember(self, key: str, value: str) -> None:
        key = (key or "").strip().lower()
        value = (value or "").strip()
        if not key or not value:
            return
        self.preferences[key] = value
        # Clamp oldest if over cap.
        if len(self.preferences) > MAX_PREFERENCES:
            oldest = next(iter(self.preferences))
            if oldest != key:
                self.preferences.pop(oldest, None)
        self._touch()

    def forget(self, key: str) -> bool:
        key = (key or "").strip().lower()
        had = key in self.preferences
        self.preferences.pop(key, None)
        if had:
            self._touch()
        return had

    def recall(self, key: str) -> str | None:
        key = (key or "").strip().lower()
        return self.preferences.get(key)

    def add_learned_rule(self, rule: str) -> None:
        rule = (rule or "").strip()
        if not rule:
            return
        # Dedupe — case-insensitive. Move existing match to the tail so
        # "most recently reinforced" is visible in the UI.
        lower = rule.lower()
        existing = [r for r in self.learned_rules if r.lower() == lower]
        if existing:
            for r in existing:
                self.learned_rules.remove(r)
        self.learned_rules.append(rule)
        # Trim from the head — oldest rules evict first.
        while len(self.learned_rules) > MAX_LEARNED_RULES:
            self.learned_rules.pop(0)
        self._touch()

    def mark_favorite_sector(self, sector_id: int) -> None:
        try:
            sid = int(sector_id)
        except (TypeError, ValueError):
            return
        if sid in self.favorite_sectors:
            self.favorite_sectors.remove(sid)
        self.favorite_sectors.append(sid)
        while len(self.favorite_sectors) > MAX_FAVORITE_SECTORS:
            self.favorite_sectors.pop(0)
        self._touch()

    def bump_stat(self, name: str, delta: int = 1) -> int:
        name = (name or "").strip()
        if not name:
            return 0
        self.stats[name] = int(self.stats.get(name, 0)) + int(delta)
        self._touch()
        return self.stats[name]

    def clear_all(self) -> None:
        self.preferences.clear()
        self.learned_rules.clear()
        self.favorite_sectors.clear()
        self.stats.clear()
        self._touch()

    # ------------------- rendering --------------------------------------

    def summary_line(self) -> str:
        """One-line chip text for the cockpit right panel."""
        pieces: list[str] = []
        if self.preferences:
            pieces.append(f"{len(self.preferences)} prefs")
        if self.learned_rules:
            pieces.append(f"{len(self.learned_rules)} rules")
        if self.favorite_sectors:
            pieces.append(f"{len(self.favorite_sectors)} favs")
        runs = int(self.stats.get("session_count", 0))
        if runs:
            pieces.append(f"{runs} sessions")
        if not pieces:
            return "memory: empty"
        return "memory: " + ", ".join(pieces)

    def prompt_block(self) -> str:
        """Multi-line block the ChatAgent can splice into a system prompt.

        Keeps it under ~400 chars so we don't burn context on returning
        agents. If nothing is remembered, returns an empty string so the
        prompt stays short.
        """
        if not self.preferences and not self.learned_rules:
            return ""
        lines: list[str] = ["[memory]"]
        for k, v in list(self.preferences.items())[-12:]:
            lines.append(f"- pref: {k} = {v}")
        for r in self.learned_rules[-12:]:
            lines.append(f"- learned: {r}")
        if self.favorite_sectors:
            fav = ", ".join(str(s) for s in self.favorite_sectors[-8:])
            lines.append(f"- favorite_sectors: {fav}")
        return "\n".join(lines)

    # ------------------- private ---------------------------------------

    def _touch(self) -> None:
        self.updated_at = time.time()


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class MemoryStore:
    """Tiny JSON-file-per-player persistence.

    ``root_dir`` defaults to an in-memory "no persistence" shim — tests
    can instantiate without a filesystem. Production wiring uses
    ``saves/`` so memory survives server restarts.
    """

    def __init__(self, root_dir: Path | str | None = None) -> None:
        self._root = Path(root_dir) if root_dir is not None else None
        # In-memory cache keeps reads cheap (~µs) and keeps tests
        # deterministic when no root_dir is set.
        self._cache: dict[str, CopilotMemory] = {}

    @property
    def root(self) -> Path | None:
        return self._root

    def _path_for(self, player_id: str) -> Path | None:
        if self._root is None:
            return None
        return self._root / f"{MEMORY_FILE_PREFIX}{player_id}.json"

    def load(self, player_id: str) -> CopilotMemory:
        cached = self._cache.get(player_id)
        if cached is not None:
            return cached
        p = self._path_for(player_id)
        if p is not None and p.exists():
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
                mem = CopilotMemory.model_validate(raw)
            except Exception:
                mem = CopilotMemory(player_id=player_id)
        else:
            mem = CopilotMemory(player_id=player_id)
        self._cache[player_id] = mem
        return mem

    def save(self, mem: CopilotMemory) -> None:
        self._cache[mem.player_id] = mem
        p = self._path_for(mem.player_id)
        if p is None:
            return
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(
            json.dumps(mem.model_dump(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        tmp.replace(p)

    def delete(self, player_id: str) -> bool:
        self._cache.pop(player_id, None)
        p = self._path_for(player_id)
        if p is None or not p.exists():
            return False
        try:
            p.unlink()
            return True
        except OSError:
            return False


# ---------------------------------------------------------------------------
# Tiny NL heuristics — let `ChatAgent` pipe "remember X = Y" directly
# ---------------------------------------------------------------------------


_REMEMBER_PATTERNS = (
    # "remember that my preferred port class is 7"
    # "remember preferred_port_class = 7"
    # "note: min_reserve = 5000"
    "remember",
    "note",
    "save this",
    "save that",
    "don't forget",
    "dont forget",
)

_FORGET_PATTERNS = (
    "forget",
    "drop that",
    "unlearn",
)


def parse_remember_directive(utterance: str) -> tuple[str, str] | None:
    """Pull a (key, value) pair out of an imperative utterance.

    Very simple — we don't want the memory system to silently capture
    everything the human says. We only match explicit "remember ..." /
    "note ..." phrasings, and require a ``=`` or ``:`` or ``is`` split.

    Returns ``None`` if no directive is found.
    """
    if not utterance:
        return None
    u = utterance.strip().lower()
    if not any(u.startswith(p) or f" {p} " in u for p in _REMEMBER_PATTERNS):
        return None

    # Strip a leading imperative verb so we don't ship "remember" as key.
    for p in _REMEMBER_PATTERNS:
        if u.startswith(p + " "):
            u = u[len(p) + 1 :].strip()
            break
        if u.startswith(p + ":"):
            u = u[len(p) + 1 :].strip()
            break

    # Chop "that" prefix.
    if u.startswith("that "):
        u = u[5:].strip()

    # Try splitters in priority order.
    for splitter in (" = ", ":", " is ", " = ", "="):
        if splitter in u:
            k, _, v = u.partition(splitter)
            k = k.strip()
            v = v.strip(" .\"'")
            if k and v:
                return (k, v)
    return None


def parse_forget_directive(utterance: str) -> str | None:
    if not utterance:
        return None
    u = utterance.strip().lower()
    for p in _FORGET_PATTERNS:
        if u.startswith(p + " "):
            rest = u[len(p) + 1 :].strip(" .\"'")
            if rest.startswith("that "):
                rest = rest[5:]
            if rest.startswith("my "):
                rest = rest[3:]
            return rest or None
    return None


__all__ = [
    "MAX_FAVORITE_SECTORS",
    "MAX_LEARNED_RULES",
    "MAX_PREFERENCES",
    "MEMORY_FILE_PREFIX",
    "CopilotMemory",
    "MemoryStore",
    "parse_forget_directive",
    "parse_remember_directive",
]
