"""Runtime toggles for match LLM agency vs coaching (see docs/AGENCY_INITIATIVE.md)."""

from __future__ import annotations

import os

_VALID = frozenset({"full", "minimal"})


def hint_level() -> str:
    """TW2K_HINT_LEVEL: ``full`` (default) or ``minimal``."""
    v = (os.environ.get("TW2K_HINT_LEVEL") or "full").strip().lower()
    return v if v in _VALID else "full"


def is_minimal() -> bool:
    return hint_level() == "minimal"
