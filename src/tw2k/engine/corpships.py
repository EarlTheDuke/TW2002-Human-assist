"""Corporate ships, ship passwords, and furb hold salvage. docs/playtests/ships/CORP_SHIPS_FURB.md.

Fleet, tow, capture and combat call in here. CORPSHIP_MODE legacy never reaches these branches.
"""

from __future__ import annotations

from typing import Any

from . import constants as K
from .actions import Action, ActionResult
from .models import EventKind, ParkedShip, Player, Universe

FAILSAFE = "Corp attack failsafe: that is a corporate ship of your corp"
_PRINTABLE = set(range(32, 127))


def label(ship) -> str:
    if getattr(ship, "corp_ticker", None):
        return f"corp {ship.corp_ticker}"
    return "personal"


def sector_label(universe: Universe, rec: ParkedShip) -> str:
    if rec.owner_id == K.DEFUNCT_OWNER:
        return "defunct Corp"
    return label(rec.ship)


def _same_corp(player: Player, ticker: str | None) -> bool:
    return bool(ticker) and player.corp_ticker == ticker


def on_new_hull(player: Player) -> None:
    """cs3: a bought hull is personal, unless the class is corporation-only."""
    if not K.corpship_on():
        return
    spec = K.hull_spec(player.ship.ship_class.value) or {}
    if spec.get("corp_only") and player.corp_ticker:
        player.ship.corp_ticker = player.corp_ticker
    elif K.CORPSHIP_NEW_DEFAULT == "personal":
        player.ship.corp_ticker = None
    player.ship.ship_password = ""


def on_new_spare(player: Player, ship) -> None:
    if not K.corpship_on():
        return
    spec = K.hull_spec(ship.ship_class.value) or {}
    if spec.get("corp_only") and player.corp_ticker:
        ship.corp_ticker = player.corp_ticker
    elif K.CORPSHIP_NEW_DEFAULT == "personal":
        ship.corp_ticker = None
    ship.ship_password = ""


def transport_records(universe: Universe, pid: str) -> list[ParkedShip]:
    from .fleet import owned_parked
    own = list(owned_parked(universe, pid))
    if not K.corpship_on():
        return own
    player = universe.players[pid]
    seen = {int(r.id) for r in own}
    extra = []
    if player.corp_ticker:
        for rec in universe.parked_ships.values():
            if int(rec.id) in seen:
                continue
            if rec.ship.corp_ticker == player.corp_ticker and rec.owner_id != K.DEFUNCT_OWNER:
                extra.append(rec)
    return own + extra


def board_block(universe: Universe, pid: str, rec: ParkedShip) -> str | None:
    """Why a ship you do not own cannot be boarded. None means the range checks may proceed."""
    player = universe.players[pid]
    if rec.owner_id == K.DEFUNCT_OWNER:
        return "a defunct Corp ship cannot be boarded"
    if K.CORPSHIP_PERSONAL_ACCESS == "owner" and not rec.ship.corp_ticker:
        return "not your ship (own ships only)"
    if not _same_corp(player, rec.ship.corp_ticker):
        return "not your ship (own ships only)"
    if K.CORPSHIP_BOARD_CAP:
        from .fleet import fleet_size
        if fleet_size(universe, pid) >= int(K.FLEET_MAX_SHIPS):
            return "fleet full"
    return None


def password_block(pid: str, rec: ParkedShip, supplied: Any) -> str | None:
    if rec.owner_id == pid:
        return None
    pw = str(getattr(rec.ship, "ship_password", "") or "")
    if not pw:
        return None
    if K.CORPSHIP_PASSWORD_CASE == "exact" and str(supplied or "") != pw:
        return "Incorrect password"
    return None


def tow_block(universe: Universe, pid: str, rec: ParkedShip) -> str | None:
    """Replaces the owner check when CORPSHIP_TOW lets corp mates lock a corporate hull."""
    if K.CORPSHIP_TOW != "corp_with_password":
        return "not your ship (own ships only)"
    player = universe.players[pid]
    if rec.owner_id == K.DEFUNCT_OWNER:
        return "a defunct Corp ship cannot be towed"
    if not rec.ship.corp_ticker or not _same_corp(player, rec.ship.corp_ticker):
        return "not your ship (own ships only)"
    return None


def attack_block(universe: Universe, pid: str, rec: ParkedShip) -> str | None:
    """None means the attack is allowed. The failsafe string means refuse."""
    from .combat import _are_allied
    player = universe.players[pid]
    if rec.owner_id == K.DEFUNCT_OWNER:
        return None
    if rec.ship.corp_ticker and _same_corp(player, rec.ship.corp_ticker):
        return FAILSAFE
    if rec.owner_id == pid:
        return None
    owner = universe.players.get(rec.owner_id)
    same = owner is not None and _same_corp(player, owner.corp_ticker) and not rec.ship.corp_ticker
    if same:
        return None
    if owner is not None and _are_allied(universe, pid, rec.owner_id):
        return "cannot attack a corp mate or ally"
    return None


def capture_allowed(attacker: Player, rec: ParkedShip) -> bool:
    """cs26: a trader with no corp cannot capture a defunct hull. cs30: your own corp cannot."""
    if rec.ship.corp_ticker and _same_corp(attacker, rec.ship.corp_ticker):
        return False
    if rec.owner_id == K.DEFUNCT_OWNER and attacker.corp_ticker is None:
        return K.DEFUNCT_NONCORP_CAPTURE != "destroy"
    return True


def on_captured(ship, attacker: Player) -> None:
    """cs29: the hull becomes the captor's. Password cleared. A corp-only hull stays corporate."""
    if not K.corpship_on() or K.CORPSHIP_CAPTURE_FLAG != "captor_default":
        return
    ship.ship_password = ""
    spec = K.hull_spec(ship.ship_class.value) or {}
    if spec.get("corp_only") and attacker.corp_ticker:
        ship.corp_ticker = attacker.corp_ticker
    else:
        ship.corp_ticker = None


def furb_gain(victim_holds: int, victim_class: str, attacker_ship) -> int:
    if victim_class in K.FURB_EXCLUDED_HULLS:
        return 0
    raw = (int(victim_holds) + int(K.FURB_BONUS)) // int(K.FURB_DIVISOR)
    spec = K.hull_spec(attacker_ship.ship_class.value) or {}
    cap = int(spec.get("max_holds", attacker_ship.holds))
    room = max(0, cap - int(attacker_ship.holds))
    return min(raw, room)


def apply_furb(universe: Universe, attacker_id: str, victim_ship, victim_id: str) -> None:
    if not K.corpship_on():
        return
    attacker = universe.players.get(attacker_id)
    if attacker is None:
        return
    gained = furb_gain(int(victim_ship.holds), victim_ship.ship_class.value, attacker.ship)
    attacker.ship.holds = int(attacker.ship.holds) + gained
    if gained <= 0:
        line = ("Excellent, you have obliterated the target! "
                "...In fact, TOO excellent! You can't salvage anything from it!")
    else:
        line = f"Excellent, you have obliterated the target! You salvage {gained} cargo holds."
    universe.emit(
        EventKind.SHIP_FURBED,
        actor_id=attacker_id,
        sector_id=int(attacker.sector_id),
        payload={
            "attacker": attacker_id,
            "victim": victim_id,
            "victim_class": victim_ship.ship_class.value,
            "holds_gained": gained,
            "capped": gained == 0,
            "_witnesses": [attacker_id],
        },
        summary=line,
    )


def park_owner(universe: Universe, pid: str, ship) -> str:
    """cs25 / cs28: leaving a corporate hull you can no longer fly hands it on."""
    if not K.corpship_on() or K.CORPSHIP_OWNER_ON_BOARD != "pilot":
        return pid
    ticker = getattr(ship, "corp_ticker", None)
    player = universe.players[pid]
    if not ticker or player.corp_ticker == ticker:
        return pid
    corp = universe.corporations.get(ticker)
    if corp is None or not corp.member_ids:
        ship.corp_ticker = None
        return K.DEFUNCT_OWNER
    if K.CORPSHIP_ON_LEAVE == "to_ceo":
        if corp.ceo_id in corp.member_ids:
            return corp.ceo_id
        return corp.member_ids[0]
    return pid


def _release_tow(universe: Universe, rec: ParkedShip) -> None:
    if not K.tow_on():
        return
    from .tow import release, towed_by, towing
    hauler = towed_by(universe, "ship", rec.id)
    if hauler and towing(universe, hauler) is not None:
        release(universe, universe.players[hauler].ship, hauler, "defunct", owner_id=rec.owner_id)


def on_corp_extinct(universe: Universe, ticker: str) -> None:
    """cs24: parked corporate hulls of a dead corp become defunct. A manned one waits until he leaves it."""
    for rec in list(universe.parked_ships.values()):
        if rec.ship.corp_ticker != ticker:
            continue
        _release_tow(universe, rec)
        rec.owner_id = K.DEFUNCT_OWNER
        rec.ship.corp_ticker = None
        universe.emit(
            EventKind.SHIP_DEFUNCT,
            actor_id=None,
            sector_id=int(rec.sector_id),
            payload={"ship_id": int(rec.id), "ticker": ticker},
            summary=f"ship {rec.id} is now a defunct Corp ship",
        )


def on_member_leave(universe: Universe, pid: str, ticker: str) -> None:
    """cs28: parked corporate hulls of a leaver pass to the CEO. The one he flies stays until he parks it."""
    corp = universe.corporations.get(ticker)
    if corp is None:
        return
    heir = corp.ceo_id if corp.ceo_id in corp.member_ids else (corp.member_ids[0] if corp.member_ids else None)
    if heir is None or heir == pid:
        return
    for rec in universe.parked_ships.values():
        if rec.owner_id == pid and rec.ship.corp_ticker == ticker:
            rec.owner_id = heir


def _emit_flag(universe: Universe, player: Player, flag: str) -> None:
    universe.emit(
        EventKind.SHIP_FLAG_CHANGED,
        actor_id=player.id,
        sector_id=int(player.sector_id),
        payload={"flag": flag, "ticker": player.ship.corp_ticker, "_witnesses": [player.id]},
        summary=f"{player.name} set this ship {flag}",
    )


def handle_set_corporate(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not K.corpship_on():
        return ActionResult(ok=False, error="unsupported action")
    player = universe.players[pid]
    if player.corp_ticker is None:
        return ActionResult(ok=False, error="you are not in a corporation")
    if player.ship.corp_ticker == player.corp_ticker:
        return ActionResult(ok=False, error="this ship is already corporate")
    player.ship.corp_ticker = player.corp_ticker
    _emit_flag(universe, player, "corporate")
    return ActionResult(ok=True, turns_spent=int(K.CORPSHIP_SET_TURNS))


def handle_set_personal(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not K.corpship_on():
        return ActionResult(ok=False, error="unsupported action")
    player = universe.players[pid]
    spec = K.hull_spec(player.ship.ship_class.value) or {}
    if spec.get("corp_only"):
        return ActionResult(ok=False, error="Corporate ships of this class can't be set to personal")
    if not player.ship.corp_ticker:
        return ActionResult(ok=False, error="this ship is already personal")
    player.ship.corp_ticker = None
    _emit_flag(universe, player, "personal")
    return ActionResult(ok=True, turns_spent=int(K.CORPSHIP_SET_TURNS))


def handle_set_password(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not K.corpship_on():
        return ActionResult(ok=False, error="unsupported action")
    player = universe.players[pid]
    raw = action.args.get("password", "")
    text = "" if raw is None else str(raw)
    if any(ord(ch) not in _PRINTABLE for ch in text):
        return ActionResult(ok=False, error="password must be printable ASCII")
    if len(text) > int(K.CORPSHIP_PASSWORD_MAX_LEN):
        return ActionResult(ok=False, error=f"password is longer than {K.CORPSHIP_PASSWORD_MAX_LEN}")
    player.ship.ship_password = text
    universe.emit(
        EventKind.SHIP_PASSWORD_SET,
        actor_id=pid,
        sector_id=int(player.sector_id),
        payload={"set": bool(text), "_witnesses": [pid]},
        summary=f"{player.name} changed this ship's password",
    )
    return ActionResult(ok=True, turns_spent=int(K.CORPSHIP_SET_TURNS))


def note_password_fail(universe: Universe, pid: str) -> None:
    player = universe.players[pid]
    universe.emit(
        EventKind.SHIP_PASSWORD_FAIL,
        actor_id=pid,
        sector_id=int(player.sector_id),
        payload={"_witnesses": [pid]},
        summary="Incorrect password",
    )


def corp_ships_block(universe: Universe, pid: str) -> list[dict[str, Any]] | None:
    player = universe.players[pid]
    if not player.corp_ticker:
        return None
    rows = []
    for rec in sorted(universe.parked_ships.values(), key=lambda r: int(r.id)):
        if rec.ship.corp_ticker != player.corp_ticker or rec.owner_id == K.DEFUNCT_OWNER:
            continue
        owner = universe.players.get(rec.owner_id)
        rows.append({
            "ship_id": int(rec.id),
            "owner": owner.name if owner else rec.owner_id,
            "class": rec.ship.ship_class.value,
            "sector": int(rec.sector_id),
            "password_required": bool(rec.ship.ship_password),
        })
    return rows


def legal_specs(universe: Universe, pid: str) -> list[tuple[str, bool, str | None, int, dict[str, Any]]]:
    player = universe.players[pid]
    out = []
    spec = K.hull_spec(player.ship.ship_class.value) or {}
    if player.corp_ticker is None:
        why_c = "you are not in a corporation"
    elif player.ship.corp_ticker == player.corp_ticker:
        why_c = "this ship is already corporate"
    else:
        why_c = None
    out.append(("ship_set_corporate", why_c is None, why_c, int(K.CORPSHIP_SET_TURNS), {}))
    if spec.get("corp_only"):
        why_p = "Corporate ships of this class can't be set to personal"
    elif not player.ship.corp_ticker:
        why_p = "this ship is already personal"
    else:
        why_p = None
    out.append(("ship_set_personal", why_p is None, why_p, int(K.CORPSHIP_SET_TURNS), {}))
    out.append(("ship_set_password", True, None, int(K.CORPSHIP_SET_TURNS),
                {"password": {"type": "str", "required": False}}))
    return out


def detail_for(universe: Universe, pid: str, rec: ParkedShip, hops: int | None) -> dict[str, Any]:
    owner = universe.players.get(rec.owner_id)
    return {
        "owner": owner.name if owner else rec.owner_id,
        "class": rec.ship.ship_class.value,
        "hops": hops,
        "password_required": bool(getattr(rec.ship, "ship_password", "")),
        "ownership": sector_label(universe, rec),
    }
