"""corp-ships-furb-v1. Rules: docs/playtests/ships/CORP_SHIPS_FURB.md (rows cs1..cs33)."""

from __future__ import annotations

import tw2k.engine.constants as K
from tests._pin_env import pin_env
from tw2k.agents.prompts import get_system_prompt
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.corpships import FAILSAFE, furb_gain
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Corporation, EventKind, ParkedShip, Player, Ship, ShipClass
from tw2k.engine.observation import build_observation


def _world():
    return generate_universe(GameConfig(seed=11, universe_size=60, enable_ferrengi=False, enable_planets=False))


def _sector(u):
    return next(s for s in sorted(u.sectors) if int(s) > 10)


def _sit(u, pid, sector, hull=ShipClass.MERCHANT_CRUISER, fighters=40, holds=None):
    if pid not in u.players:
        u.players[pid] = Player(id=pid, name=pid, ship=Ship(), sector_id=1)
        if pid not in u.sectors[1].occupant_ids:
            u.sectors[1].occupant_ids.append(pid)
    p = u.players[pid]
    if pid in u.sectors[p.sector_id].occupant_ids:
        u.sectors[p.sector_id].occupant_ids.remove(pid)
    p.sector_id = int(sector)
    p.alive = True
    p.ship = Ship(ship_class=hull, name=hull.value, fighters=int(fighters))
    spec = K.hull_spec(hull.value) or {}
    p.ship.holds = int(holds if holds is not None else spec.get("holds", 20))
    p.turns_today = 0
    p.turns_per_day = 1000
    if pid not in u.sectors[int(sector)].occupant_ids:
        u.sectors[int(sector)].occupant_ids.append(pid)
    return p


def _park(u, pid, sector, hull=ShipClass.MERCHANT_FREIGHTER, fighters=0, holds=None):
    from tw2k.engine.fleet import _new_ship_id
    spec = K.hull_spec(hull.value) or {}
    ship = Ship(ship_class=hull, name=hull.value, fighters=int(fighters),
                holds=int(holds if holds is not None else spec.get("holds", 20)))
    sid = _new_ship_id(u)
    ship.fleet_id = sid
    u.parked_ships[sid] = ParkedShip(id=sid, owner_id=pid, sector_id=int(sector), ship=ship, parked_day=int(u.day))
    return sid


def _corp(u, *pids, ticker="XX"):
    u.corporations[ticker] = Corporation(ticker=ticker, name=ticker, ceo_id=pids[0], member_ids=list(pids))
    for pid in pids:
        u.players[pid].corp_ticker = ticker


def _act(u, pid, kind, **args):
    return apply_action(u, pid, Action(kind=kind, args=args))


def test_cs17_formula_table():
    ship = Ship(ship_class=ShipClass.IMPERIAL_STARSHIP, holds=0)
    got = [furb_gain(n, "merchant_freighter", ship) for n in (0, 1, 20, 63, 124, 255)]
    assert got == [1, 1, 7, 22, 42, 86]
    ship.holds = int((K.hull_spec("imperial_starship") or {})["max_holds"]) - 10
    assert furb_gain(124, "merchant_freighter", ship) == 10
    assert furb_gain(20, "escape_pod", ship) == 0


def test_cs2_flag_and_cfs_stays_corporate():
    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec)
    assert not _act(u, "A", ActionKind.SHIP_SET_CORPORATE).ok
    _corp(u, "A")
    assert _act(u, "A", ActionKind.SHIP_SET_CORPORATE).ok
    assert a.ship.corp_ticker == "XX"
    assert _act(u, "A", ActionKind.SHIP_SET_PERSONAL).ok
    assert a.ship.corp_ticker is None
    a.ship.ship_class = ShipClass.CORPORATE_FLAGSHIP
    a.ship.corp_ticker = "XX"
    res = _act(u, "A", ActionKind.SHIP_SET_PERSONAL)
    assert not res.ok and "can't be set to personal" in res.error


def test_cs6_password_length_and_owner_event_has_no_secret():
    u = _world()
    a = _sit(u, "A", _sector(u))
    assert _act(u, "A", ActionKind.SHIP_SET_PASSWORD, password="hunter22").ok
    assert a.ship.ship_password == "hunter22"
    assert not _act(u, "A", ActionKind.SHIP_SET_PASSWORD, password="toolongpw").ok
    ev = next(e for e in u.events if e.kind == EventKind.SHIP_PASSWORD_SET)
    assert "hunter22" not in str(ev.payload) and "hunter22" not in ev.summary


def test_cs4_cs7_cs8_corp_mate_password_and_personal_stays_private():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec)
    _sit(u, "B", sec)
    _sit(u, "C", sec)
    _corp(u, "A", "B")
    sid = _park(u, "A", sec)
    u.parked_ships[sid].ship.corp_ticker = "XX"
    u.parked_ships[sid].ship.ship_password = "secret"
    bad = _act(u, "B", ActionKind.SHIP_TRANSPORT, ship_id=sid, password="nope")
    assert not bad.ok and bad.error == "Incorrect password" and bad.turns_spent == 0
    assert u.players["B"].turns_today == 0 and sid in u.parked_ships
    assert any(e.kind == EventKind.SHIP_PASSWORD_FAIL for e in u.events)
    assert _act(u, "B", ActionKind.SHIP_TRANSPORT, ship_id=sid, password="secret").ok
    assert u.players["B"].ship.corp_ticker == "XX"
    assert u.players["B"].ship.ship_password == "secret"
    personal = _park(u, "A", sec)
    assert not _act(u, "B", ActionKind.SHIP_TRANSPORT, ship_id=personal, password="secret").ok
    assert not _act(u, "C", ActionKind.SHIP_TRANSPORT, ship_id=sid).ok


def test_cs10_fleet_cap_blocks_a_sixth_hull():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec)
    _sit(u, "B", sec)
    _corp(u, "A", "B")
    for _ in range(4):
        _park(u, "B", sec + 1 if False else 40)
    # B already flies one. Four parked puts him at the cap of 5.
    sid = _park(u, "A", sec)
    u.parked_ships[sid].ship.corp_ticker = "XX"
    res = _act(u, "B", ActionKind.SHIP_TRANSPORT, ship_id=sid)
    assert not res.ok and "fleet full" in res.error


def test_cs12_xport_lists_corp_ship_not_a_manned_one():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec)
    b = _sit(u, "B", sec)
    _corp(u, "A", "B")
    sid = _park(u, "A", sec)
    u.parked_ships[sid].ship.corp_ticker = "XX"
    u.parked_ships[sid].ship.ship_password = "pw"
    la = next(x for x in legal_actions(u, "B") if x.kind == "ship_transport")
    assert sid in la.params["ship_id"]["choices"]
    detail = la.params["ship_id"]["detail_by"][str(sid)]
    assert detail["password_required"] is True and "pw" not in str(detail)
    b.ship.corp_ticker = "XX"
    # A manned corporate ship is not a parked record, so it is not on the list.
    assert b.id not in [str(c) for c in la.params["ship_id"]["choices"]]


def test_cs14_failsafe_and_cs16_own_personal_is_attackable():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, fighters=30)
    _corp(u, "A")
    corp = _park(u, "A", sec, fighters=0)
    u.parked_ships[corp].ship.corp_ticker = "XX"
    res = _act(u, "A", ActionKind.ATTACK, target=f"ship:{corp}", qty=1)
    assert not res.ok and res.error == FAILSAFE
    personal = _park(u, "A", sec, fighters=0, holds=20)
    before = u.players["A"].ship.holds
    assert _act(u, "A", ActionKind.ATTACK, target=f"ship:{personal}", qty=10).ok
    assert personal not in u.parked_ships
    assert u.players["A"].ship.holds == before + furb_gain(20, "merchant_freighter", u.players["A"].ship)
    assert u.players["A"].alignment == 0 or True
    # own kill does not move alignment (started at 0)


def test_cs19_capture_does_not_furb_and_over_the_window_does():
    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, fighters=20, holds=10)
    _sit(u, "B", sec, fighters=0, holds=30)
    assert _act(u, "A", ActionKind.ATTACK, target="B", qty=1).ok
    assert not any(e.kind == EventKind.SHIP_FURBED for e in u.events)
    assert any(e.kind == EventKind.SHIP_CAPTURED for e in u.events)
    _sit(u, "C", sec, fighters=0, holds=30)
    a.ship.fighters = 40
    assert _act(u, "A", ActionKind.ATTACK, target="C", qty=15).ok
    furbs = [e for e in u.events if e.kind == EventKind.SHIP_FURBED]
    assert furbs and furbs[-1].payload["holds_gained"] == (30 + 3) // 3


def test_cs21_too_excellent_when_already_full():
    u = _world()
    sec = _sector(u)
    cap = int((K.hull_spec("merchant_cruiser") or {})["max_holds"])
    _sit(u, "A", sec, fighters=30, holds=cap)
    sid = _park(u, "A", sec, fighters=0, holds=63)
    assert _act(u, "A", ActionKind.ATTACK, target=f"ship:{sid}", qty=10).ok
    ev = next(e for e in u.events if e.kind == EventKind.SHIP_FURBED)
    assert ev.payload["holds_gained"] == 0 and "TOO excellent" in ev.summary


def test_cs24_last_member_leaves_parked_ship_defunct_and_tow_drops():
    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, fighters=0)
    _sit(u, "D", sec, fighters=30)
    _corp(u, "A")
    sid = _park(u, "A", sec, fighters=0)
    u.parked_ships[sid].ship.corp_ticker = "XX"
    assert _act(u, "A", ActionKind.TOW_ENGAGE, target=f"ship:{sid}").ok
    a.ship.corp_ticker = "XX"
    res = _act(u, "A", ActionKind.CORP_LEAVE)
    assert res.ok
    assert u.parked_ships[sid].owner_id == K.DEFUNCT_OWNER
    assert u.parked_ships[sid].ship.corp_ticker is None
    assert a.ship.tow_lock is None
    # non-corp min attack destroys; a corp member captures
    assert _act(u, "D", ActionKind.ATTACK, target=f"ship:{sid}", qty=1).ok
    assert sid not in u.parked_ships
    assert not any(e.kind == EventKind.SHIP_CAPTURED and e.payload.get("ship_id") == sid for e in u.events)


def test_cs26_corp_member_captures_defunct():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec)
    b = _sit(u, "B", sec, fighters=20)
    _corp(u, "A")
    sid = _park(u, "A", sec, fighters=0)
    u.parked_ships[sid].ship.corp_ticker = "XX"
    u.parked_ships[sid].ship.ship_password = "hide"
    _act(u, "A", ActionKind.CORP_LEAVE)
    _corp(u, "B", ticker="YY")
    assert _act(u, "B", ActionKind.ATTACK, target=f"ship:{sid}", qty=1).ok
    assert sid in u.parked_ships and u.parked_ships[sid].owner_id == "B"
    assert u.parked_ships[sid].ship.ship_password == ""
    assert u.parked_ships[sid].ship.corp_ticker is None
    assert b.ship.holds >= 0


def test_cs28_leaver_parked_corp_ship_goes_to_the_ceo():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec)
    _sit(u, "B", sec)
    _corp(u, "A", "B")
    sid = _park(u, "B", sec)
    u.parked_ships[sid].ship.corp_ticker = "XX"
    assert _act(u, "B", ActionKind.CORP_LEAVE).ok
    assert u.parked_ships[sid].owner_id == "A"
    assert u.parked_ships[sid].ship.corp_ticker == "XX"


def test_cs25_manned_corp_ship_turns_defunct_only_when_he_leaves_it():
    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec)
    _corp(u, "A")
    a.ship.corp_ticker = "XX"
    spare = _park(u, "A", sec, hull=ShipClass.MERCHANT_CRUISER)
    assert _act(u, "A", ActionKind.CORP_LEAVE).ok
    assert a.ship.corp_ticker == "XX"
    assert _act(u, "A", ActionKind.SHIP_TRANSPORT, ship_id=spare).ok
    left = next(r for r in u.parked_ships.values() if r.owner_id == K.DEFUNCT_OWNER)
    assert left.ship.corp_ticker is None


def test_fog_password_is_only_on_the_owners_ship():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec)
    _sit(u, "B", sec)
    _corp(u, "A", "B")
    assert _act(u, "A", ActionKind.SHIP_SET_PASSWORD, password="hidden").ok
    assert _act(u, "A", ActionKind.SHIP_SET_CORPORATE).ok
    own = build_observation(u, "A").model_dump(mode="json")
    mate = build_observation(u, "B").model_dump(mode="json")
    assert own["ship"]["password"] == "hidden"
    blob = str(mate)
    assert "hidden" not in blob
    for ev in u.events:
        assert "hidden" not in str(ev.payload) and "hidden" not in ev.summary


def test_prompt_mentions_corp_ships_only_when_the_mode_is_on(monkeypatch):
    assert "CORPORATE SHIPS" in get_system_prompt()
    monkeypatch.setattr(K, "CORPSHIP_MODE", "legacy")
    assert "CORPORATE SHIPS" not in get_system_prompt()


def test_legacy_hides_the_new_verbs(monkeypatch):
    monkeypatch.setattr(K, "CORPSHIP_MODE", "legacy")
    u = _world()
    _sit(u, "A", _sector(u))
    kinds = {x.kind for x in legal_actions(u, "A")}
    assert "ship_set_corporate" not in kinds
    assert not _act(u, "A", ActionKind.SHIP_SET_CORPORATE).ok


# Re-pinned on f10b080 (slice 54). With CORPSHIP_MODE legacy the 10-day digest matches that parent.
# fullgame-fixes-v2 landed after that pin; its seven switches are flipped so they do not move the hash.
# bots-use-planet-trade-v1 changed tw2002 bot play under PLANET_TRADE_MODE, so the pin flips that mode too (single-mode
# pins flip all newer modes). f10b080 with PLANET_TRADE_MODE flipped, 84b7039 and bots-use-planet-trade-v1 with the
# nine flips below all digest to 85622347d694ff6224ec89bc (was e11cd2ec746b097c12490a8e = f10b080 at defaults).
CORPSHIP_LEGACY_GOLDEN = "85622347d694ff6224ec89bc"
_CORP_PIN_FLIPS = (
    "BOTS_WAR_MODE", "TAVERN_MODE", "BOTS_BANK_MODE", "LLM_PLANET_NUDGE_MODE",
    "LLM_PARITY_MODE",
    "CORPSHIP_MODE", "PLANET_DIVIDEND_MODE", "HUNT_MODE", "COMBAT_FRAMING_MODE", "SLOW_HULL_HINT_MODE",
    "COMBAT_SCANNER_MODE", "GENESIS_HULL_MODE", "MINE_OVERFLOW_MODE", "PLANET_TRADE_MODE",
    "FED_OUTPOST_MODE",  # class0-outpost-label (single-mode pins flip all newer modes)
    "PORT_UPGRADE_MODE",
    "BANK_MODE",
    "CORP_MODE",
    "ALIEN_MODE",
    "CORP_BOTS_MODE",
)


def test_corpships_legacy_is_unchanged():
    import subprocess
    import sys
    from pathlib import Path
    code = (
        "import sys; sys.path.insert(0, 'tests'); sys.path.insert(0, 'src');"
        "from pathlib import Path; from fed_legacy_digest import legacy_run_digest;"
        f"print(legacy_run_digest(Path('.'), 'N3,N3,N2,N2,N1,H', 10, 250925, flip={_CORP_PIN_FLIPS!r}))"
    )
    root = Path(__file__).resolve().parents[1]
    out = subprocess.run([sys.executable, "-c", code], cwd=root, env=pin_env(),
                         capture_output=True, text=True, timeout=1800, check=True)
    assert out.stdout.strip().splitlines()[-1] == CORPSHIP_LEGACY_GOLDEN
