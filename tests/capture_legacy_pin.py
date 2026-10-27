"""Hash of a short run that destroys at the exact-minimum fighter count.

Re-pinned in QC on ad21ac6 (the slice-51 parent): the digest matches that parent with
CAPTURE_MODE legacy on Windows and Linux alike (floats rounded to 6 places before hashing).
"""

from __future__ import annotations

import hashlib
import json
import re

import tw2k.engine.constants as K
from tw2k.agents.prompts import format_observation, get_system_prompt
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.fleet import _new_ship_id
from tw2k.engine.models import ParkedShip, Player, Ship, ShipClass
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import tick_day


def _sit(u, pid, sector, fighters):
    if pid not in u.players:
        u.players[pid] = Player(id=pid, name=pid, ship=Ship(), sector_id=1)
        u.sectors[1].occupant_ids.append(pid)
    p = u.players[pid]
    if pid in u.sectors[p.sector_id].occupant_ids:
        u.sectors[p.sector_id].occupant_ids.remove(pid)
    p.sector_id = int(sector)
    p.ship.ship_class = ShipClass.MERCHANT_CRUISER
    p.ship.fighters = int(fighters)
    p.ship.shields = 0
    p.turns_today = 0
    p.turns_per_day = 1000
    p.alive = True
    u.sectors[int(sector)].occupant_ids.append(pid)
    return p


def _stable(text: str) -> bytes:
    """Round every float in a JSON dump to 6 places. Sector map x/y come from math.cos/sin/hypot, whose
    last bits differ between libms (glibc vs MSVC); unrounded, the digest only matched on Windows."""
    def walk(v):
        if isinstance(v, float):
            return round(v, 6)
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items()}
        return v
    return json.dumps(walk(json.loads(text))).encode()


_FLOAT = re.compile(r"-?\d+\.\d{7,}")


def _stable_text(text: str) -> bytes:
    return _FLOAT.sub(lambda m: f"{float(m.group()):.6f}", text).encode()


def legacy_capture_digest() -> str:
    """Exact-minimum attacks on a manned ship and an unmanned ship, then 3 day ticks."""
    forced = {
        "CAPTURE_MODE": "legacy",
        "PLANET_TRADE_MODE": "legacy",  # planetary-trading-v1
        "CORPSHIP_MODE": "legacy",  # corp-ships-furb-v1
        "PORT_UPGRADE_MODE": "legacy",  # port-upgrade-build-v1
        "BANK_MODE": "legacy",  # galactic-bank-tax-v1
        "CORP_MODE": "legacy",  # corp-rules-v1
        "ALIEN_MODE": "legacy",  # alien-traders-v1
        "CORP_BOTS_MODE": "legacy",  # bots-use-corps-v1
        "LLM_PARITY_MODE": "legacy",  # llm-rules-parity-v1
        "LLM_PLANET_NUDGE_MODE": "legacy",
        "LLM_QUASAR_NUDGE_MODE": "off",
        "BOTS_BANK_MODE": "legacy",
        "TAVERN_MODE": "legacy",
        "BOTS_WAR_MODE": "legacy",
        "CORP_FIX_MODE": "legacy",
        "BOTS_TAVERN_MODE": "legacy",
        "BOTS_DEPLOY_MODE": "legacy",
        "STARDOCK_EXTRA_MODE": "legacy",
        "CITADEL_FIDELITY_MODE": "legacy",
        "H_RECOVERY_MODE": "legacy",
        "PLANET_DIVIDEND_MODE": "legacy",
        "HUNT_MODE": "legacy",
        "COMBAT_FRAMING_MODE": "legacy",
        "SLOW_HULL_HINT_MODE": "legacy",
        "COMBAT_SCANNER_MODE": "legacy",
        "GENESIS_HULL_MODE": "legacy",
        "MINE_OVERFLOW_MODE": "legacy",  # fullgame-fixes-v2
        "FED_OUTPOST_MODE": "legacy",  # class0-outpost-label
        "V311_PROFILE": "legacy",  # R-4: the stored default is v311
    }
    prior = {}
    try:
        for name, value in forced.items():
            if hasattr(K, name):
                prior[name] = getattr(K, name)
                setattr(K, name, value)
        h = hashlib.sha256()
        h.update(get_system_prompt().encode())
        u = generate_universe(GameConfig(seed=11, universe_size=60, enable_ferrengi=False, enable_planets=False))
        sector = next(s for s in sorted(u.sectors) if int(s) > 10)
        _sit(u, "A", sector, 20)
        _sit(u, "B", sector, 0)
        ship = Ship(ship_class=ShipClass.MERCHANT_FREIGHTER, name="spare", holds=10, fighters=0, shields=0)
        sid = _new_ship_id(u)
        ship.fleet_id = sid
        u.parked_ships[sid] = ParkedShip(id=sid, owner_id="B", sector_id=int(sector), ship=ship, parked_day=u.day)

        def snap(tag: str):
            h.update(tag.encode())
            for pid in ("A", "B"):
                if pid not in u.players:
                    continue
                o = build_observation(u, pid)
                h.update(_stable(o.model_dump_json()))
                h.update(_stable_text(format_observation(o)))
            h.update(_stable(json.dumps([e.model_dump(mode="json") for e in u.events], sort_keys=True)))

        snap("before")
        apply_action(u, "A", Action(kind=ActionKind.ATTACK, args={"target": "B", "qty": 1}))
        snap("manned")
        _sit(u, "A", sector, 20)
        owner = u.parked_ships[sid].owner_id
        apply_action(u, "A", Action(kind=ActionKind.ATTACK, args={"target": f"ship:{sid}", "qty": 1}))
        snap("unmanned")
        h.update(str(sid in u.parked_ships).encode())
        h.update(owner.encode())
        for _ in range(3):
            tick_day(u)
            h.update(_stable(u.model_dump_json()))
        h.update(str(K.COMBAT_MODE).encode())
        return h.hexdigest()[:24]
    finally:
        for name, value in prior.items():
            setattr(K, name, value)


if __name__ == "__main__":
    print(legacy_capture_digest())
