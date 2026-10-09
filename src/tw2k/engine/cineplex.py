"""The Cineplex at StarDock. Flavor only. No engine secrets.

TWINSTR and the live StarDock menu name the theatre. The live player did not
enter it. The original Bible calls the show a useless ANSI for a nominal
credit amount and says it holds no secrets. No price number was on the screen,
so CINEPLEX_COST stays 0 and is marked UNVERIFIED.
"""

from __future__ import annotations

from . import constants as K
from .actions import Action, ActionResult
from .models import EventKind, Universe

_LINE = "The Cineplex plays a short picture. It has no secrets."


def legal_spec(universe: Universe, player_id: str) -> tuple[bool, str | None, int, dict]:
    player = universe.players[player_id]
    if not player.alive:
        return False, "player is destroyed", 0, {}
    if player.planet_landed is not None:
        return False, "you are on a planet", 0, {}
    if int(player.sector_id) != int(K.STARDOCK_SECTOR):
        return False, "Cineplex is at StarDock", 0, {}
    return True, None, 0, {"cost": int(K.CINEPLEX_COST)}


def handle_cineplex(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not K.stardock_extra_on():
        return ActionResult(ok=False, error="unsupported action")
    ok, why, _cost, _params = legal_spec(universe, pid)
    if not ok:
        return ActionResult(ok=False, error=why or "not here")
    player = universe.players[pid]
    universe.emit(
        EventKind.CINEPLEX,
        actor_id=player.id,
        sector_id=player.sector_id,
        payload={"_witnesses": [player.id]},
        summary=_LINE,
    )
    return ActionResult(ok=True, turns_spent=0)
