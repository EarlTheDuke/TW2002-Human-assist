"""StarDock where-to doors from the live 3.34b capture (NOTE 129, gap 1.8).

The displayed list gains the Libram Universitatus. B is not on that list.
It asks the singles-bar question. U is the Underground door, already built,
and it is not on the list either.

The library takes no credits. An archive answers with its menu label and an
empty document list. The singles bar, if you go in, prints the capture's
exit lines and does not take credits. The visit that moved a balance from
140 to 93 named no item and printed no price, so that charge stays deferred.
"""

from __future__ import annotations

from . import constants as K
from .actions import Action, ActionResult
from .models import EventKind, Universe

WHERE_TO_PROMPT = "<StarDock> Where to?"

# Displayed keys only. B and U are doors, and neither letter is on this list.
WHERE_TO: tuple[tuple[str, str], ...] = (
    ("C", "The CinePlex Videon Theatres"),
    ("G", "The 2nd National Galactic Bank"),
    ("H", "The Stellar Hardware Emporium"),
    ("L", "The Libram Universitatus"),
    ("P", "The Federal Space Police HQ"),
    ("S", "The Federation Shipyards"),
    ("T", "The Lost Trader's Tavern"),
)

ARCHIVES: tuple[tuple[str, str], ...] = (
    ("A", "Archive of Alien Races"),
    ("B", "Archive of Galactic Organizations"),
    ("C", "Miscellaneous Documents"),
    ("Q", "To Leave"),
)

HIDDEN_KEYS = ("B", "U")

SINGLES_PROMPT = (
    "This is a rather seedy looking single's bar. Are you sure you want to go in there?"
)

# The screen after Yes. No item, no price. The unnamed balance drop is not applied.
SINGLES_ENTERED = (
    "You feel rather nervous as you enter this rather seedy establishment.\n"
    "But after a few drinks you begin to carouse with members of the opposite\n"
    "sex and you forget about your surroundings. You emerge from the place\n"
    "a few hours later with a nasty headache and you notice that your account\n"
    "on your VidCreditCard is much lower than when you entered."
)


def _line(key: str, label: str) -> str:
    return f"<{key}> {label}"


def where_to_lines() -> list[str]:
    """The displayed StarDock where-to list. B and U are not in it."""
    return [_line(key, label) for key, label in WHERE_TO]


def where_to_rows() -> list[dict[str, str]]:
    return [{"key": key, "label": label, "line": _line(key, label)} for key, label in WHERE_TO]


def archive_lines() -> list[str]:
    return [_line(key, label) for key, label in ARCHIVES]


def archive_rows() -> list[dict[str, str]]:
    return [{"key": key, "label": label, "line": _line(key, label)} for key, label in ARCHIVES]


def _at_dock(universe: Universe, player_id: str) -> tuple[bool, str | None]:
    player = universe.players[player_id]
    if not player.alive:
        return False, "player is destroyed"
    if player.planet_landed is not None:
        return False, "you are on a planet"
    if int(player.sector_id) != int(K.STARDOCK_SECTOR):
        return False, "that door is at StarDock"
    return True, None


def library_spec(universe: Universe, player_id: str) -> tuple[bool, str | None, dict]:
    ok, why = _at_dock(universe, player_id)
    params = {
        "prompt": WHERE_TO_PROMPT,
        "where_to": where_to_rows(),
        "archives": archive_rows(),
        "charge": 0,
        "archive": {"type": "str", "required": True, "choices": [key for key, _label in ARCHIVES]},
    }
    return ok, why, params


def singles_spec(universe: Universe, player_id: str) -> tuple[bool, str | None, dict]:
    ok, why = _at_dock(universe, player_id)
    params = {
        "listed": False,
        "prompt": SINGLES_PROMPT,
        "charge": 0,
        "confirm": {"type": "bool", "required": False},
    }
    return ok, why, params


def _archive_key(action: Action) -> str:
    return str((action.args or {}).get("archive") or "").strip().upper()


def _confirmed(value: object) -> bool:
    if value is True:
        return True
    if isinstance(value, str) and value.strip().lower() in {"y", "yes", "true"}:
        return True
    return False


def handle_library(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not K.stardock_doors_live():
        return ActionResult(ok=False, error="unsupported action")
    ok, why = _at_dock(universe, pid)
    if not ok:
        return ActionResult(ok=False, error=why or "that door is at StarDock")
    key = _archive_key(action)
    labels = {letter: label for letter, label in ARCHIVES}
    if key not in labels:
        return ActionResult(ok=False, error="archive is A, B, C, or Q")
    player = universe.players[pid]
    universe.emit(
        EventKind.LIBRARY,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={
            "_witnesses": [pid],
            "archive": key,
            "label": labels[key],
            "lines": [],
            "charge": 0,
        },
        summary=labels[key],
    )
    return ActionResult(ok=True, turns_spent=0)


def handle_singles_bar(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not K.stardock_doors_live():
        return ActionResult(ok=False, error="unsupported action")
    ok, why = _at_dock(universe, pid)
    if not ok:
        return ActionResult(ok=False, error=why or "that door is at StarDock")
    if not _confirmed((action.args or {}).get("confirm")):
        return ActionResult(ok=True, turns_spent=0)
    player = universe.players[pid]
    universe.emit(
        EventKind.SINGLES_BAR,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"_witnesses": [pid], "entered": True, "charged": False},
        summary=SINGLES_ENTERED,
    )
    return ActionResult(ok=True, turns_spent=0)
