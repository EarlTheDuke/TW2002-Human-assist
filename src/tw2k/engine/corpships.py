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
    given = str(supplied or "")
    if K.CORPSHIP_PASSWORD_CASE != "exact":
        given, pw = given.casefold(), pw.casefold()
    if given != pw:
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
        if K.DEFUNCT_NONCORP_CAPTURE == "refuse" and player.corp_ticker is None:
            return "only a corporation member can attack a defunct Corp ship"
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
    """cs26: a trader with no corp cannot capture a defunct hull. cs30: your own corp cannot.

    QC: your own hull is never "captured" (it is already yours); the exact minimum destroys it and furbs (cs16).
    """
    if rec.owner_id == attacker.id:
        return False
    if rec.ship.corp_ticker and _same_corp(attacker, rec.ship.corp_ticker):
        return False
    if rec.owner_id == K.DEFUNCT_OWNER and attacker.corp_ticker is None:
        return False  # "destroy"; under "refuse" attack_block never lets the attack start
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


def furb_raw(victim_holds: int, victim_class: str) -> int:
    """cs17 before the attacker's cap: (holds + 3) // 3. Excluded hulls (pods) give nothing."""
    if victim_class in K.FURB_EXCLUDED_HULLS:
        return 0
    return (int(victim_holds) + int(K.FURB_BONUS)) // int(K.FURB_DIVISOR)


def furb_gain(victim_holds: int, victim_class: str, attacker_ship) -> int:
    raw = furb_raw(victim_holds, victim_class)
    if raw <= 0:
        return 0
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
    raw = furb_raw(int(victim_ship.holds), victim_ship.ship_class.value)
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
            "capped": gained < raw,  # QC: the attacker's max_holds cut the gain
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
    _release_leaver_tow(universe, pid, ticker)


def _release_leaver_tow(universe: Universe, pid: str, ticker: str) -> None:
    """QC (cs28, EIS <X>): a leaver loses access to corp assets, so his beam drops a corporate hull of that corp."""
    if not K.tow_on():
        return
    from .tow import lock_of, release
    player = universe.players[pid]
    lock = lock_of(player.ship)
    if lock is None or lock.kind != "ship":
        return
    rec = universe.parked_ships.get(int(lock.ship_id or -1))
    if rec is not None and rec.ship.corp_ticker == ticker and rec.owner_id != pid:
        release(universe, player.ship, pid, "left_corp")


def _emit_flag(universe: Universe, player: Player, flag: str) -> None:
    universe.emit(
        EventKind.SHIP_FLAG_CHANGED,
        actor_id=player.id,
        sector_id=int(player.sector_id),
        payload={"flag": flag, "ticker": player.ship.corp_ticker, "_witnesses": [player.id]},
        summary=f"{player.name} set this ship {flag}",
    )


_OTHER_CORP = "this is another corporation's ship"


def corporate_block(player: Player) -> str | None:
    if player.corp_ticker is None:
        return "you are not in a corporation"
    if player.ship.corp_ticker == player.corp_ticker:
        return "this ship is already corporate"
    if player.ship.corp_ticker:
        return _OTHER_CORP  # QC cs25/cs28: a leaver's borrowed hull is not his to re-flag
    return None


def exmember_tradein_block(player: Player) -> str | None:
    """A borrowed corporate hull is not his to sell. None keeps today's trade-in."""
    if not K.corp_fix_on(corp=True) or not K.corpship_on():
        return None
    if K.CORPSHIP_EXMEMBER_TRADEIN != "refuse":
        return None
    if personal_block(player) == _OTHER_CORP:
        return _OTHER_CORP + " - you cannot trade it in"
    return None


def personal_block(player: Player) -> str | None:
    spec = K.hull_spec(player.ship.ship_class.value) or {}
    if spec.get("corp_only"):
        return "Corporate ships of this class can't be set to personal"
    if not player.ship.corp_ticker:
        return "this ship is already personal"
    if player.ship.corp_ticker != player.corp_ticker:
        return _OTHER_CORP  # QC cs25/cs28: otherwise he keeps it and it never passes on
    return None


def handle_set_corporate(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not K.corpship_on():
        return ActionResult(ok=False, error="unsupported action")
    player = universe.players[pid]
    why = corporate_block(player)
    if why is not None:
        return ActionResult(ok=False, error=why)
    player.ship.corp_ticker = player.corp_ticker
    _emit_flag(universe, player, "corporate")
    return ActionResult(ok=True, turns_spent=int(K.CORPSHIP_SET_TURNS))


def handle_set_personal(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not K.corpship_on():
        return ActionResult(ok=False, error="unsupported action")
    player = universe.players[pid]
    why = personal_block(player)
    if why is not None:
        return ActionResult(ok=False, error=why)
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
    why_c = corporate_block(player)
    out.append(("ship_set_corporate", why_c is None, why_c, int(K.CORPSHIP_SET_TURNS), {}))
    why_p = personal_block(player)
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
