"""Who has an open cockpit right now.

A code bot (anything that is not an external or human seat) counts as online.
An external seat counts as online only after this process has seen a harness
poll inside the window. The engine does not import the server. The harness
calls note_poll.
"""

from __future__ import annotations

import time

_polls: dict[tuple[int, str], float] = {}
COCKPIT_OPEN_S = 30.0


def note_poll(universe, player_id: str, when: float | None = None) -> None:
    """A cockpit just read or posted for this seat."""
    _polls[(id(universe), str(player_id))] = time.time() if when is None else float(when)


def cockpit_open(universe, player_id: str, window: float = COCKPIT_OPEN_S, now: float | None = None) -> bool:
    stamp = _polls.get((id(universe), str(player_id)))
    if stamp is None:
        return False
    clock = time.time() if now is None else float(now)
    return (clock - stamp) <= float(window)


def seat_online(universe, player_id: str) -> bool:
    """True when a hail should flash on the screen instead of waiting as mail."""
    player = universe.players.get(player_id)
    if player is None or not getattr(player, "alive", True):
        return False
    kind = str(getattr(player, "agent_kind", "") or "")
    if kind not in ("external", "human"):
        return True
    return cockpit_open(universe, player_id)


def mark_ai_cockpit(player) -> None:
    """A lobby AI cockpit seat is named 'AI cockpit' or 'AI cockpit N'."""
    name = str(getattr(player, "name", "") or "")
    if name == "AI cockpit" or name.startswith("AI cockpit "):
        player.ai_cockpit = True


def inactive_deletion_exempt(universe, player) -> bool:
    """Connected seats and AI cockpit seats are not inactive-user deletions."""
    if getattr(player, "ai_cockpit", False):
        return True
    name = str(getattr(player, "name", "") or "")
    if name == "AI cockpit" or name.startswith("AI cockpit "):
        return True
    return seat_online(universe, player.id)
