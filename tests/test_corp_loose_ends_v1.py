"""Today's behaviour for the corp loose ends, recorded before the fixes.

These are the legacy-side facts. The gated tw2002 path is added later.
"""

from __future__ import annotations

from tw2k.engine import constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.combat import _destroy_ship
from tw2k.engine.fleet import attack_unmanned
from tw2k.engine.bank import on_ship_lost
from tw2k.engine.corp import disband
from tw2k.engine.models import EventKind, FighterDeployment, FighterMode, TowLock
from tw2k.engine.scanners import limpet_visible
from tw2k.engine.tow import emit_hold, extern_hold_why

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


def test_today_a_mate_lock_does_not_hold_a_ship_over_extern(monkeypatch):
    monkeypatch.setattr(K, "CORP_FIX_MODE", "legacy")
    u = _world()
    owner = _sit(u, "A", 1, align=100, fighters=0)
    mate = _sit(u, "B", 1, align=100, fighters=0)
    owner.corp_ticker = mate.corp_ticker = "XYZ"
    sid = _park(u, "A", 1)
    mate.ship.tow_lock = TowLock(kind="ship", ship_id=sid, engaged_day=u.day)
    assert extern_hold_why(u, u.parked_ships[sid]) == "no_lock"
    owner.ship.tow_lock = TowLock(kind="ship", ship_id=sid, engaged_day=u.day)
    assert extern_hold_why(u, u.parked_ships[sid]) is None


def _mate_hold(align=100, fighters=0, ticker="XYZ", holder="owner_or_corp"):
    u = _world()
    owner = _sit(u, "A", 1, align=align, fighters=0)
    mate = _sit(u, "B", 1, align=align, fighters=fighters)
    owner.corp_ticker = mate.corp_ticker = ticker
    sid = _park(u, "A", 1)
    mate.ship.tow_lock = TowLock(kind="ship", ship_id=sid, engaged_day=u.day)
    return u, sid, mate


def test_cl2_a_corp_mate_holds_the_ship_over_extern(monkeypatch):
    monkeypatch.setattr(K, "TOW_EXTERN_HOLDER", "owner_or_corp")
    u, sid, _mate = _mate_hold()
    assert extern_hold_why(u, u.parked_ships[sid]) is None
    emit_hold(u, u.parked_ships[sid])
    event = next(e for e in u.events if e.kind == EventKind.EXTERN_TOW_HOLD)
    assert event.payload["_witnesses"] == ["A", "B"]


def test_cl2_an_ally_does_not_hold(monkeypatch):
    monkeypatch.setattr(K, "TOW_EXTERN_HOLDER", "owner_or_corp")
    u, sid, mate = _mate_hold()
    mate.corp_ticker = "OTHER"
    assert extern_hold_why(u, u.parked_ships[sid]) == "no_lock"


def test_cl2_a_mate_holds_another_members_hull(monkeypatch):
    monkeypatch.setattr(K, "TOW_EXTERN_HOLDER", "owner_or_corp")
    u = _world()
    owner = _sit(u, "C", 1, align=100)
    mate = _sit(u, "B", 1, align=100)
    owner.corp_ticker = mate.corp_ticker = "XYZ"
    sid = _park(u, "C", 1)
    mate.ship.tow_lock = TowLock(kind="ship", ship_id=sid, engaged_day=u.day)
    assert extern_hold_why(u, u.parked_ships[sid]) is None


def test_cl2_owner_setting_ignores_the_mate(monkeypatch):
    monkeypatch.setattr(K, "TOW_EXTERN_HOLDER", "owner")
    u, sid, _mate = _mate_hold()
    assert extern_hold_why(u, u.parked_ships[sid]) == "no_lock"


def test_cl2_the_mate_must_be_fedsafe(monkeypatch):
    monkeypatch.setattr(K, "TOW_EXTERN_HOLDER", "owner_or_corp")
    monkeypatch.setattr(K, "TOW_EXTERN_REQUIRE_GOOD", True)
    u, sid, _mate = _mate_hold(align=-10)
    assert extern_hold_why(u, u.parked_ships[sid]) == "tower_not_good"
    u2, sid2, mate2 = _mate_hold(fighters=int(K.FED_TOW_FIGHTER_LIMIT) + 1)
    assert extern_hold_why(u2, u2.parked_ships[sid2]) == "tower_has_too_many_fighters"
    mate2.sector_id = 2
    assert extern_hold_why(u2, u2.parked_ships[sid2]) == "not_same_sector"


def test_cl3_an_ex_member_cannot_trade_in_a_borrowed_hull():
    from tw2k.engine.legality import legal_actions
    u = _u()
    pilot = u.players["P2"]
    pilot.credits = 2_000_000
    pilot.ship.corp_ticker = "XYZ"
    refused = _act(u, "P2", "buy_ship", ship_class="scout_marauder")
    assert refused.error == "this is another corporation's ship - you cannot trade it in"
    assert pilot.ship.ship_class.value == "merchant_cruiser"
    offer = next(row for row in legal_actions(u, "P2") if row.kind == "buy_ship")
    assert offer.legal is False and offer.params["ship_class"]["trade_in"] == 0


def test_cl3_a_current_member_still_trades_the_hull_in():
    u = _u()
    pilot = u.players["P2"]
    pilot.credits = 2_000_000
    pilot.corp_ticker = "XYZ"
    pilot.ship.corp_ticker = "XYZ"
    assert _act(u, "P2", "buy_ship", ship_class="scout_marauder").ok
    assert pilot.ship.ship_class.value == "scout_marauder"


def test_cl3_allow_and_legacy_keep_today(monkeypatch):
    u = _u()
    pilot = u.players["P2"]
    pilot.credits = 2_000_000
    pilot.ship.corp_ticker = "XYZ"
    monkeypatch.setattr(K, "CORPSHIP_EXMEMBER_TRADEIN", "allow")
    assert _act(u, "P2", "buy_ship", ship_class="scout_marauder").ok
    monkeypatch.setattr(K, "CORPSHIP_EXMEMBER_TRADEIN", "refuse")
    monkeypatch.setattr(K, "CORP_FIX_MODE", "legacy")
    pilot.ship.ship_class = type(pilot.ship.ship_class)("merchant_cruiser")
    pilot.ship.corp_ticker = "XYZ"
    assert _act(u, "P2", "buy_ship", ship_class="scout_marauder").ok


def test_today_a_corp_mate_sees_a_personal_limpet(monkeypatch):
    monkeypatch.setattr(K, "LIMPET_CORP_VIEW", "all_corp")
    u = _u()
    u.players["P1"].corp_ticker = "XYZ"
    u.players["P2"].corp_ticker = "XYZ"
    assert limpet_visible(u, "P2", "P1") is True
    u.players["P2"].corp_ticker = None
    assert limpet_visible(u, "P2", "P1") is False


def test_cl6_a_mate_sees_only_a_corporate_limpet():
    from tw2k.engine.models import LimpetTrack, MineDeployment, MineType
    u = _u()
    u.players["P1"].corp_ticker = "XYZ"
    u.players["P2"].corp_ticker = "XYZ"
    u.players["P3"].corp_ticker = "XYZ"
    personal = MineDeployment(owner_id="P1", kind=MineType.LIMPET, count=1)
    corporate = MineDeployment(owner_id="P1", kind=MineType.LIMPET, count=1, corp_ticker="XYZ")
    assert limpet_visible(u, "P2", "P1", personal) is False
    assert limpet_visible(u, "P2", "P1", corporate) is True
    assert limpet_visible(u, "P1", "P1", personal) is True
    u.limpets["old"] = LimpetTrack(owner_id="P1", target_id="P3", placed_sector=1, placed_day=1)
    u.limpets["corp"] = LimpetTrack(
        owner_id="P1", target_id="P3", placed_sector=9, placed_day=1, corp_ticker="XYZ",
    )
    _act(u, "P2", "query_limpets")
    reports = u.events[-1].payload["reports"]
    assert [row["placed_sector"] for row in reports] == [9]
    _act(u, "P1", "query_limpets")
    assert len(u.events[-1].payload["reports"]) == 2


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


def test_cl4_your_own_unmanned_corbomite_fires_on_you():
    u = _world()
    pilot = _sit(u, "A", 40, fighters=100)
    pilot.ship.shields = 0
    sid = _park(u, "A", 40)
    u.parked_ships[sid].ship.corbomite = 1
    u.parked_ships[sid].ship.fighters = 0
    u.parked_ships[sid].ship.shields = 0
    assert attack_unmanned(u, "A", f"ship:{sid}", Action(kind=ActionKind.ATTACK, args={"qty": 5})).ok
    assert pilot.ship.fighters == 80
    assert any(e.kind == EventKind.CORBOMITE_BLAST for e in u.events)


def test_cl4_inert_does_not_fire_on_your_own_hull(monkeypatch):
    monkeypatch.setattr(K, "CORBOMITE_OWN_SHIP", "inert")
    u = _world()
    pilot = _sit(u, "A", 40, fighters=100)
    sid = _park(u, "A", 40)
    u.parked_ships[sid].ship.corbomite = 1
    u.parked_ships[sid].ship.fighters = 0
    u.parked_ships[sid].ship.shields = 0
    assert attack_unmanned(u, "A", f"ship:{sid}", Action(kind=ActionKind.ATTACK, args={"qty": 5})).ok
    assert pilot.ship.fighters == 100
    assert not any(e.kind == EventKind.CORBOMITE_BLAST for e in u.events)


def test_cl4_a_flown_ship_does_not_detonate_on_itself():
    u = _world()
    pilot = _sit(u, "A", 40, fighters=100)
    other = _sit(u, "B", 40, fighters=100)
    pilot.ship.corbomite = 1
    _destroy_ship(u, "A", "combat", killer_id="A")
    assert not any(e.kind == EventKind.CORBOMITE_BLAST for e in u.events)
    assert other.ship.fighters == 100
    u2 = _world()
    victim = _sit(u2, "A", 40, fighters=100)
    killer = _sit(u2, "B", 40, fighters=100)
    victim.ship.corbomite = 1
    _destroy_ship(u2, "A", "combat", killer_id="B")
    assert killer.ship.fighters == 80


def test_today_salvage_overkill_stays_none():
    assert K.SALVAGE_OVERKILL == "none"


def _furb(sent, needed):
    from tw2k.engine.corpships import apply_furb
    from tw2k.engine.models import Ship, ShipClass
    u = _u()
    attacker = u.players["P1"]
    attacker.ship.holds = 20
    victim = Ship(ship_class=ShipClass.MERCHANT_CRUISER, holds=30)
    apply_furb(u, "P1", victim, "P2", sent=sent, needed=needed)
    return attacker.ship.holds, u.events[-1].summary


def test_cl5_no_limit_still_salvages_an_overkill():
    holds, summary = _furb(10, 0)
    assert holds == 31
    assert "salvage" in summary


def test_cl5_ratio_keeps_a_measured_attack_and_drops_an_overkill(monkeypatch):
    monkeypatch.setattr(K, "SALVAGE_OVERKILL", "ratio")
    holds, summary = _furb(4, 2)
    assert holds == 31 and "salvage" in summary
    holds, summary = _furb(5, 2)
    assert holds == 20 and summary == "overkill - the hull is destroyed with its holds"
