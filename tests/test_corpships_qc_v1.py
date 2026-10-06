"""QC of corp-ships-furb-v1 (slice 53): rows and planted bugs the first pass did not pin.

Rules: docs/playtests/ships/CORP_SHIPS_FURB.md. Helpers come from tests/test_corpships_v1.py.
"""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tw2k.engine import ActionKind
from tw2k.engine.corpships import FAILSAFE, apply_furb, furb_gain
from tw2k.engine.fleet import fleet_net_worth
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Alliance, EventKind, Ship, ShipClass
from tw2k.engine.observation import build_observation
from tests.test_corpships_v1 import _act, _corp, _park, _sector, _sit, _world


def _la(u, pid, kind):
    return next(x for x in legal_actions(u, pid) if x.kind == kind)


def _corp_ship(u, owner, sec, pw="", ticker="XX", **kw):
    sid = _park(u, owner, sec, **kw)
    u.parked_ships[sid].ship.corp_ticker = ticker
    u.parked_ships[sid].ship.ship_password = pw
    return sid


def _furbs(u):
    return [e for e in u.events if e.kind == EventKind.SHIP_FURBED]


# ---- passwords (cs6-cs8, pb2 pb3 pb4 pb5) ---------------------------------------------------------------


def test_qc_owner_is_never_asked_for_his_own_password():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec)
    _corp(u, "A")
    sid = _corp_ship(u, "A", sec, pw="Secret")
    assert _act(u, "A", ActionKind.SHIP_TRANSPORT, ship_id=sid).ok


def test_qc_password_matrix_transport():
    u = _world()
    sec = _sector(u)
    for pid in ("A", "B", "C"):
        _sit(u, pid, sec)
    _corp(u, "A", "B")
    blank = _corp_ship(u, "A", sec)
    locked = _corp_ship(u, "A", sec, pw="Secret")
    personal = _park(u, "A", sec)
    u.parked_ships[personal].ship.ship_password = "Secret"
    # non-member with the right password: refused
    assert not _act(u, "C", ActionKind.SHIP_TRANSPORT, ship_id=locked, password="Secret").ok
    # corp mate, personal ship, right password: refused
    assert not _act(u, "B", ActionKind.SHIP_TRANSPORT, ship_id=personal, password="Secret").ok
    # case matters (CORPSHIP_PASSWORD_CASE exact)
    bad = _act(u, "B", ActionKind.SHIP_TRANSPORT, ship_id=locked, password="secret")
    assert not bad.ok and bad.error == "Incorrect password" and u.players["B"].turns_today == 0
    missing = _act(u, "B", ActionKind.SHIP_TRANSPORT, ship_id=locked)
    assert not missing.ok and missing.error == "Incorrect password"
    assert locked in u.parked_ships and u.parked_ships[locked].owner_id == "A"
    # corp mate, blank password: boards without one
    assert _act(u, "B", ActionKind.SHIP_TRANSPORT, ship_id=blank).ok
    assert u.players["B"].ship.fleet_id == blank and u.players["B"].ship.corp_ticker == "XX"


def test_qc_password_fail_is_not_shown_to_the_owner():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec)
    _sit(u, "B", sec)
    _corp(u, "A", "B")
    sid = _corp_ship(u, "A", sec, pw="Secret")
    assert not _act(u, "B", ActionKind.SHIP_TRANSPORT, ship_id=sid, password="x").ok
    fail = [e for e in u.events if e.kind == EventKind.SHIP_PASSWORD_FAIL]
    assert len(fail) == 1 and fail[0].actor_id == "B"
    assert fail[0].payload.get("_witnesses") == ["B"]
    owner_view = str(build_observation(u, "A").model_dump(mode="json"))
    assert "ship_password_fail" not in owner_view and "Incorrect password" not in owner_view


def test_qc_password_exactly_max_len_and_printable():
    u = _world()
    a = _sit(u, "A", _sector(u))
    assert _act(u, "A", ActionKind.SHIP_SET_PASSWORD, password="A" * int(K.CORPSHIP_PASSWORD_MAX_LEN)).ok
    assert not _act(u, "A", ActionKind.SHIP_SET_PASSWORD, password="A" * (int(K.CORPSHIP_PASSWORD_MAX_LEN) + 1)).ok
    assert not _act(u, "A", ActionKind.SHIP_SET_PASSWORD, password="tab\there").ok
    assert _act(u, "A", ActionKind.SHIP_SET_PASSWORD, password="").ok and a.ship.ship_password == ""


# ---- tow (cs13) -----------------------------------------------------------------------------------------


def test_qc_corp_tow_needs_the_password_and_personal_stays_owner_only():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec)
    b = _sit(u, "B", sec)
    _corp(u, "A", "B")
    sid = _corp_ship(u, "A", sec, pw="Secret")
    personal = _park(u, "A", sec)
    la = _la(u, "B", "tow_engage")
    assert f"ship:{sid}" in la.params["target"]["choices"]
    assert f"ship:{personal}" not in la.params["target"]["choices"]
    assert "password" in la.params
    bad = _act(u, "B", ActionKind.TOW_ENGAGE, target=f"ship:{sid}", password="nope")
    assert not bad.ok and bad.error == "Incorrect password" and b.turns_today == 0 and b.ship.tow_lock is None
    assert not _act(u, "B", ActionKind.TOW_ENGAGE, target=f"ship:{personal}").ok
    assert _act(u, "B", ActionKind.TOW_ENGAGE, target=f"ship:{sid}", password="Secret").ok
    assert b.ship.tow_lock is not None and u.parked_ships[sid].owner_id == "A"


def test_qc_non_member_cannot_tow_a_corp_ship_even_with_the_password():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec)
    _sit(u, "C", sec)
    _corp(u, "A")
    sid = _corp_ship(u, "A", sec, pw="Secret")
    assert f"ship:{sid}" not in _la(u, "C", "tow_engage").params["target"]["choices"]
    assert not _act(u, "C", ActionKind.TOW_ENGAGE, target=f"ship:{sid}", password="Secret").ok


def test_qc_tow_legal_detail_shows_password_required_not_the_password():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec)
    _sit(u, "B", sec)
    _corp(u, "A", "B")
    sid = _corp_ship(u, "A", sec, pw="Secret")
    la = _la(u, "B", "tow_engage")
    detail = la.params["target"]["detail_by"][f"ship:{sid}"]
    assert detail["password_required"] is True and "Secret" not in str(la.params)


# ---- failsafe matrix (cs14-cs16, cs30, pb12 pb13 pb24) ------------------------------------------------------


def test_qc_failsafe_matrix_and_legal_list_agree():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, ShipClass.BATTLESHIP, fighters=900)
    for pid in ("M", "L", "R"):
        _sit(u, pid, 40)
    _corp(u, "A", "M")
    u.alliances["a1"] = Alliance(id="a1", member_ids=["A", "L"], proposed_by="A", formed_day=1, active=True)
    u.players["A"].alliances.append("a1")
    rows = {
        "own_corporate": (_corp_ship(u, "A", sec), False),
        "own_personal": (_park(u, "A", sec), True),
        "mate_corporate": (_corp_ship(u, "M", sec), False),
        "mate_personal": (_park(u, "M", sec), True),
        "ally": (_park(u, "L", sec), False),
        "rival": (_park(u, "R", sec), True),
    }
    defunct = _park(u, "R", sec)
    u.parked_ships[defunct].owner_id = K.DEFUNCT_OWNER
    rows["defunct"] = (defunct, True)
    choices = _la(u, "A", "attack").params["target"]["unmanned_choices"]
    for name, (sid, ok) in rows.items():
        assert (f"ship:{sid}" in choices) is ok, name
    for name, (sid, ok) in rows.items():
        res = _act(u, "A", ActionKind.ATTACK, target=f"ship:{sid}", qty=50)
        assert res.ok is ok, (name, res.error)
        if not ok and name.endswith("corporate"):
            assert res.error == FAILSAFE and sid in u.parked_ships


def test_qc_own_kill_costs_no_alignment_but_a_rival_kill_does():
    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, ShipClass.BATTLESHIP, fighters=900)
    _sit(u, "R", 40)
    a.alignment = 1000
    own = _park(u, "A", sec, fighters=50)
    assert _act(u, "A", ActionKind.ATTACK, target=f"ship:{own}", qty=400).ok
    assert own not in u.parked_ships and a.alignment == 1000
    rival = _park(u, "R", sec, fighters=50)
    assert _act(u, "A", ActionKind.ATTACK, target=f"ship:{rival}", qty=400).ok
    assert a.alignment < 1000


def test_qc_own_ship_at_the_exact_minimum_is_destroyed_and_furbed_not_captured():
    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, fighters=30, holds=20)
    own = _park(u, "A", sec, fighters=0, holds=63)
    assert _act(u, "A", ActionKind.ATTACK, target=f"ship:{own}", qty=1).ok
    assert own not in u.parked_ships
    assert not any(e.kind == EventKind.SHIP_CAPTURED for e in u.events)
    assert a.ship.holds == 20 + 22


# ---- furb (cs17-cs21, pb14 pb15 pb16 pb18 pb19) ---------------------------------------------------------------


def test_qc_furb_uses_current_holds_not_the_hull_base():
    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, ShipClass.BATTLESHIP, fighters=900, holds=10)
    sid = _park(u, "A", sec, fighters=0, holds=124)  # a merchant freighter carrying bought holds
    base = int((K.hull_spec("merchant_freighter") or {})["holds"])
    assert base != 124
    assert _act(u, "A", ActionKind.ATTACK, target=f"ship:{sid}", qty=10).ok
    assert a.ship.holds == 10 + 42
    ev = _furbs(u)[-1]
    assert ev.payload["holds_gained"] == 42 and "TOO excellent" not in ev.summary
    assert "You salvage 42 cargo holds" in ev.summary


def test_qc_furb_cap_is_the_attacker_hull_max_not_its_base():
    u = _world()
    sec = _sector(u)
    spec = K.hull_spec("merchant_cruiser") or {}
    base, cap = int(spec["holds"]), int(spec["max_holds"])
    assert cap > base
    a = _sit(u, "A", sec, fighters=30, holds=base)
    sid = _park(u, "A", sec, fighters=0, holds=255)
    assert _act(u, "A", ActionKind.ATTACK, target=f"ship:{sid}", qty=10).ok
    assert a.ship.holds == min(cap, base + 86)
    assert a.ship.holds <= cap
    ev = _furbs(u)[-1]
    assert ev.payload["capped"] is (base + 86 > cap)


def test_qc_manned_kill_furbs_and_a_pod_kill_is_too_excellent():
    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, ShipClass.BATTLESHIP, fighters=900, holds=10)
    pod = Ship(ship_class=ShipClass.ESCAPE_POD, holds=2)
    assert furb_gain(2, "escape_pod", a.ship) == 0
    apply_furb(u, "A", pod, "B")
    ev = _furbs(u)[-1]
    assert ev.payload["holds_gained"] == 0 and "TOO excellent" in ev.summary and a.ship.holds == 10
    _sit(u, "B", sec, ShipClass.MERCHANT_FREIGHTER, fighters=0, holds=63)
    assert _act(u, "A", ActionKind.ATTACK, target="B", qty=100).ok
    ev = _furbs(u)[-1]
    assert ev.payload["holds_gained"] == 22 and ev.payload["victim_class"] == "merchant_freighter"
    assert a.ship.holds == 32


def test_qc_furb_event_never_reaches_a_third_party():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, fighters=30, holds=10)
    _sit(u, "W", sec)
    sid = _park(u, "A", sec, fighters=0, holds=20)
    assert _act(u, "A", ActionKind.ATTACK, target=f"ship:{sid}", qty=10).ok
    assert _furbs(u)[-1].payload["_witnesses"] == ["A"]


# ---- defunct (cs24-cs28, pb20 pb21 pb22 pb23) ----------------------------------------------------------------


def test_qc_extinction_touches_only_that_corps_ships_and_keeps_the_password():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec)
    _sit(u, "B", sec)
    _corp(u, "A", ticker="XX")
    _corp(u, "B", ticker="YY")
    mine = _corp_ship(u, "A", sec, pw="keep", ticker="XX")
    theirs = _corp_ship(u, "B", sec, ticker="YY")
    personal = _park(u, "A", sec)
    nw_before = fleet_net_worth(u, "A")
    assert _act(u, "A", ActionKind.CORP_LEAVE).ok
    assert u.parked_ships[mine].owner_id == K.DEFUNCT_OWNER
    assert u.parked_ships[mine].ship.ship_password == "keep"
    assert u.parked_ships[theirs].owner_id == "B" and u.parked_ships[theirs].ship.corp_ticker == "YY"
    assert u.parked_ships[personal].owner_id == "A"
    assert fleet_net_worth(u, "A") < nw_before
    assert sum(1 for e in u.events if e.kind == EventKind.SHIP_DEFUNCT) == 1


def test_qc_defunct_ship_cannot_be_boarded_or_towed_by_anyone():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec)
    _corp(u, "A")
    sid = _corp_ship(u, "A", sec)
    assert _act(u, "A", ActionKind.CORP_LEAVE).ok
    _corp(u, "A", ticker="ZZ")
    assert sid not in _la(u, "A", "ship_transport").params["ship_id"]["choices"]
    assert f"ship:{sid}" not in _la(u, "A", "tow_engage").params["target"]["choices"]
    assert not _act(u, "A", ActionKind.SHIP_TRANSPORT, ship_id=sid).ok
    assert not _act(u, "A", ActionKind.TOW_ENGAGE, target=f"ship:{sid}").ok


def test_qc_ceo_leaving_hands_his_parked_corp_ships_to_the_first_remaining_member():
    u = _world()
    sec = _sector(u)
    for pid in ("A", "B", "C"):
        _sit(u, pid, sec)
    _corp(u, "A", "B", "C")
    sid = _corp_ship(u, "A", sec)
    assert _act(u, "A", ActionKind.CORP_LEAVE).ok
    assert u.parked_ships[sid].owner_id == "B"


def test_qc_leaver_cannot_unflag_the_corp_ship_he_is_still_flying():
    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec)
    _sit(u, "B", sec)
    _corp(u, "A", "B")
    a.ship.corp_ticker = "XX"
    assert _act(u, "A", ActionKind.CORP_LEAVE).ok
    assert a.ship.corp_ticker == "XX"
    assert not _la(u, "A", "ship_set_personal").legal
    assert not _act(u, "A", ActionKind.SHIP_SET_PERSONAL).ok
    _corp(u, "A", ticker="ZZ")
    assert not _la(u, "A", "ship_set_corporate").legal
    assert not _act(u, "A", ActionKind.SHIP_SET_CORPORATE).ok
    assert a.ship.corp_ticker == "XX"
    spare = _park(u, "A", sec, hull=ShipClass.MERCHANT_CRUISER)
    assert _act(u, "A", ActionKind.SHIP_TRANSPORT, ship_id=spare).ok
    (left,) = list(u.parked_ships.values())
    assert left.owner_id == "B" and left.ship.corp_ticker == "XX"


# ---- capture of corp ships (cs29) -----------------------------------------------------------------------------


def test_qc_captured_corp_ship_becomes_personal_and_loses_its_password():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, fighters=20)
    _sit(u, "R", 40)
    _corp(u, "R", ticker="RR")
    sid = _corp_ship(u, "R", sec, pw="pw", ticker="RR")
    assert _act(u, "A", ActionKind.ATTACK, target=f"ship:{sid}", qty=1).ok
    rec = u.parked_ships[sid]
    assert rec.owner_id == "A" and rec.ship.corp_ticker is None and rec.ship.ship_password == ""
    assert not _furbs(u)


# ---- observation / legacy (cs31, pb25) and save -----------------------------------------------------------------


def test_qc_rival_sees_labels_but_never_corp_ships_or_passwords():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec)
    _sit(u, "R", sec)
    _corp(u, "A")
    sid = _corp_ship(u, "A", sec, pw="Zq9x")
    obs = build_observation(u, "R").model_dump(mode="json")
    assert "corp_ships" not in obs and "Zq9x" not in str(obs)
    mate = build_observation(u, "A").model_dump(mode="json")
    assert [r["ship_id"] for r in mate["corp_ships"]] == [sid]


def test_qc_legacy_adds_no_observation_key_or_param(monkeypatch):
    monkeypatch.setattr(K, "CORPSHIP_MODE", "legacy")
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec)
    _corp(u, "A")
    _park(u, "A", sec)
    obs = build_observation(u, "A").model_dump(mode="json")
    assert "corp_ships" not in obs
    assert not {"ownership", "password", "password_set"} & set(obs["ship"])
    assert all("ownership" not in s for s in (obs.get("fleet") or {}).get("ships", []))
    assert "password" not in _la(u, "A", "ship_transport").params
    assert "password" not in _la(u, "A", "tow_engage").params
    assert "detail_by" not in _la(u, "A", "ship_transport").params["ship_id"]


def test_qc_ship_fields_round_trip_and_are_omitted_at_default():
    s = Ship()
    dumped = s.model_dump(mode="json")
    assert "corp_ticker" not in dumped and "ship_password" not in dumped
    s.corp_ticker, s.ship_password = "XX", "pw"
    back = Ship.model_validate(s.model_dump(mode="json"))
    assert back.corp_ticker == "XX" and back.ship_password == "pw"


@pytest.mark.parametrize("kind", ["ship_set_corporate", "ship_set_personal", "ship_set_password"])
def test_qc_legal_list_equals_handler_for_the_flag_verbs(kind):
    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec)
    states = []
    for corp in (False, True):
        for flag in (None, "XX", "OLD"):
            for hull in (ShipClass.MERCHANT_CRUISER, ShipClass.CORPORATE_FLAGSHIP):
                states.append((corp, flag, hull))
    akind = ActionKind(kind)
    for corp, flag, hull in states:
        u.corporations.clear()
        a.corp_ticker = None
        if corp:
            _corp(u, "A")
        a.ship = Ship(ship_class=hull, holds=20, corp_ticker=flag)
        legal = _la(u, "A", kind).legal
        args = {"password": "pw"} if kind == "ship_set_password" else {}
        res = _act(u, "A", akind, **args)
        assert res.ok is legal, (kind, corp, flag, hull.value, res.error)


def test_qc_leaver_towing_a_corp_ship_drops_the_beam():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec)
    b = _sit(u, "B", sec)
    _corp(u, "A", "B")
    sid = _corp_ship(u, "B", sec)
    assert _act(u, "B", ActionKind.TOW_ENGAGE, target=f"ship:{sid}").ok
    assert _act(u, "B", ActionKind.CORP_LEAVE).ok
    assert u.parked_ships[sid].owner_id == "A" and b.ship.tow_lock is None
    rel = [e for e in u.events if e.kind == EventKind.TOW_RELEASED]
    assert rel and rel[-1].payload.get("reason") == "left_corp"


def test_qc_defunct_refuse_alt_refuses_the_attack(monkeypatch):
    monkeypatch.setattr(K, "DEFUNCT_NONCORP_CAPTURE", "refuse")
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, fighters=20)
    sid = _park(u, "Z", sec)
    u.parked_ships[sid].owner_id = K.DEFUNCT_OWNER
    res = _act(u, "A", ActionKind.ATTACK, target=f"ship:{sid}", qty=1)
    assert not res.ok and sid in u.parked_ships and u.players["A"].turns_today == 0


def test_qc_password_case_alt_is_case_blind(monkeypatch):
    monkeypatch.setattr(K, "CORPSHIP_PASSWORD_CASE", "ignore")
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec)
    _sit(u, "B", sec)
    _corp(u, "A", "B")
    sid = _corp_ship(u, "A", sec, pw="Secret")
    assert not _act(u, "B", ActionKind.SHIP_TRANSPORT, ship_id=sid, password="wrong").ok
    assert _act(u, "B", ActionKind.SHIP_TRANSPORT, ship_id=sid, password="SECRET").ok


def test_qc_owner_tows_his_own_locked_corp_ship_without_the_password():
    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec)
    _corp(u, "A")
    sid = _corp_ship(u, "A", sec, pw="Secret")
    assert _act(u, "A", ActionKind.TOW_ENGAGE, target=f"ship:{sid}").ok and a.ship.tow_lock is not None


def test_qc_parked_corp_ship_password_never_reaches_a_corp_mate():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec)
    _sit(u, "B", sec)
    _corp(u, "A", "B")
    _corp_ship(u, "A", sec, pw="Zq9x")
    for pid in ("A", "B"):
        obs = build_observation(u, pid).model_dump(mode="json")
        assert "Zq9x" not in str(obs)
        assert obs["corp_ships"][0]["password_required"] is True
        assert "Zq9x" not in str([la.model_dump() for la in legal_actions(u, pid)])


def test_qc_a_bought_hull_is_personal_with_no_password():
    u = _world()
    a = _sit(u, "A", K.STARDOCK_SECTOR)
    a.credits = 10_000_000
    _corp(u, "A")
    a.ship.corp_ticker, a.ship.ship_password = "XX", "pw"
    res = _act(u, "A", ActionKind.BUY_SHIP, ship_class="cargotran")
    assert res.ok, res.error
    assert a.ship.ship_class == ShipClass.CARGOTRAN
    assert a.ship.corp_ticker is None and a.ship.ship_password == ""


def test_qc_other_corps_members_never_see_our_corp_ships():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec)
    _sit(u, "R", sec)
    _corp(u, "A", ticker="XX")
    _corp(u, "R", ticker="YY")
    _corp_ship(u, "A", sec, ticker="XX")
    assert build_observation(u, "R").model_dump(mode="json").get("corp_ships") == []


@pytest.mark.parametrize("flag,expect", [(None, "personal"), ("RR", "corp RR"), ("defunct", "defunct Corp")])
def test_qc_destroy_event_reports_the_real_label(flag, expect):
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, ShipClass.BATTLESHIP, fighters=900)
    _sit(u, "R", 40)
    _corp(u, "R", ticker="RR")
    sid = _park(u, "R", sec, fighters=5)
    if flag == "defunct":
        u.parked_ships[sid].owner_id = K.DEFUNCT_OWNER
    else:
        u.parked_ships[sid].ship.corp_ticker = flag
    assert _act(u, "A", ActionKind.ATTACK, target=f"ship:{sid}", qty=200).ok
    ev = next(e for e in u.events if e.kind == EventKind.UNMANNED_SHIP_DESTROYED)
    assert ev.payload["ownership"] == expect
