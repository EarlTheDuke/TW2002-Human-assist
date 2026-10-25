"""The Cineplex at StarDock. Flavor only. No engine secrets.

TWINSTR and the live StarDock menu name the theatre. The original Bible calls
the show a useless ANSI for a nominal credit amount and says it holds no
secrets. NOTE 129 (docs/playtests/twgs-live/illegal-goods.txt) priced show 1,
"Vulcan Thunder", at 100 credits. The other titles were listed and not opened,
so they are not sold. The stored ticket stays 0 until CINEPLEX_PRICE_MODE is on.
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
    if int(player.sector_id) != int(K.stardock_sector_of(universe)):
        return False, "Cineplex is at StarDock", 0, {}
    cost = int(K.cineplex_cost())
    params: dict = {"cost": cost}
    if cost:
        params["show"] = 1
        params["title"] = K.CINEPLEX_SHOW1_TITLE
        if int(player.credits) < cost:
            return False, "not enough credits", 0, params
    return True, None, 0, params


def handle_cineplex(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not K.stardock_extra_on():
        return ActionResult(ok=False, error="unsupported action")
    ok, why, _cost, params = legal_spec(universe, pid)
    if not ok:
        return ActionResult(ok=False, error=why or "not here")
    player = universe.players[pid]
    cost = int(params.get("cost") or 0)
    payload: dict = {"_witnesses": [player.id]}
    if cost:
        player.credits = int(player.credits) - cost
        summary = (
            f'You\'ll LOVE "{K.CINEPLEX_SHOW1_TITLE}". '
            f"{cost} credits. It has no secrets."
        )
        payload["cost"] = cost
        payload["show"] = 1
    else:
        summary = _LINE
    universe.emit(
        EventKind.CINEPLEX,
        actor_id=player.id,
        sector_id=player.sector_id,
        payload=payload,
        summary=summary,
    )
    return ActionResult(ok=True, turns_spent=0)
