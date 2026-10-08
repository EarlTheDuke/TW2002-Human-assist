"""Today's behaviour for the corp loose ends, recorded before the fixes.

These are the legacy-side facts. The gated tw2002 path is added later.
"""

from __future__ import annotations

from tw2k.engine.bank import on_ship_lost
from tw2k.engine.constants import SALVAGE_OVERKILL
from tw2k.engine.corp import disband
from tw2k.engine.models import FighterDeployment, FighterMode, TowLock
from tw2k.engine.scanners import limpet_visible
from tw2k.engine.tow import extern_hold_why

from tests.test_corp_rules_v1 import _act, _u
from tests.test_ship_tow_v1 import _park, _sit, _world


def test_today_a_correct_password_is_refused_after_a_wrong_guess():
    u = _u()
    assert _act(u, "P1", "corp_create", ticker="XYZ", name="Ex").ok
    assert _act(u, "P1", "corp_set_password", password="Zx9").ok
    assert _act(u, "P2", "corp_join", ticker="XYZ", password="nope").error == "wrong password"
    refused = _act(u, "P2", "corp_join", ticker="XYZ", password="Zx9")
    assert refused.ok is False and refused.error == "one break-in attempt per day"
    assert u.players["P2"].corp_ticker is None


def test_today_a_mate_lock_does_not_hold_a_ship_over_extern():
    u = _world()
    owner = _sit(u, "A", 1, align=100, fighters=0)
    mate = _sit(u, "B", 1, align=100, fighters=0)
    owner.corp_ticker = mate.corp_ticker = "XYZ"
    sid = _park(u, "A", 1)
    mate.ship.tow_lock = TowLock(kind="ship", ship_id=sid, engaged_day=u.day)
    assert extern_hold_why(u, u.parked_ships[sid]) == "no_lock"
    owner.ship.tow_lock = TowLock(kind="ship", ship_id=sid, engaged_day=u.day)
    assert extern_hold_why(u, u.parked_ships[sid]) is None


def test_today_a_corp_mate_sees_a_personal_limpet():
    u = _u()
    u.players["P1"].corp_ticker = "XYZ"
    u.players["P2"].corp_ticker = "XYZ"
    assert limpet_visible(u, "P2", "P1") is True
    u.players["P2"].corp_ticker = None
    assert limpet_visible(u, "P2", "P1") is False


def test_today_disband_zeros_the_toll_pot():
    u = _u()
    assert _act(u, "P1", "corp_create", ticker="XYZ", name="Ex").ok
    u.sectors[2].fighters = FighterDeployment(
        owner_id="P1", count=5, mode=FighterMode.TOLL, corp_ticker="XYZ", toll_credits=400,
    )
    disband(u, u.corporations["XYZ"])
    assert u.sectors[2].fighters.toll_credits == 0


def test_today_a_self_death_pays_the_other_player_nothing():
    u = _u()
    victim = u.players["P1"]
    killer = u.players["P2"]
    victim.credits = 800
    killer.credits = 100
    lost = on_ship_lost(u, victim, killer.id, False, "merchant_cruiser")
    assert lost == 800 and victim.credits == 0 and killer.credits == 100


def test_today_salvage_overkill_stays_none():
    assert SALVAGE_OVERKILL == "none"
