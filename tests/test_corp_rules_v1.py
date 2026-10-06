"""CORP_RULES.md. The corporate menu behind K.CORP_MODE."""

from __future__ import annotations

import copy

from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.constants import CORP_MAX_MEMBERS, hull_spec
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import FighterDeployment, FighterMode, MineDeployment, MineType, Player
from tw2k.engine.runner import apply_action, tick_day


def _u():
    u = generate_universe(GameConfig(
        seed=31, universe_size=90, max_days=3, turns_per_day=60,
        starting_credits=25_000, enable_ferrengi=False, enable_planets=True,
    ))
    for pid, name in (("P1", "Ann"), ("P2", "Ben"), ("P3", "Cid")):
        p = Player(id=pid, name=name, agent_kind="external", sector_id=1, credits=25_000)
        u.players[pid] = p
        u.sectors[1].occupant_ids.append(pid)
    return u


def _act(u, pid, kind, **args):
    return apply_action(u, pid, Action(kind=ActionKind(kind), args=args))


def test_cr1_cr2_create_is_free_anywhere():
    u = _u()
    u.players["P1"].sector_id = 40
    u.players["P1"].credits = 0
    res = _act(u, "P1", "corp_create", ticker="XYZ", name="Ex")
    assert res.ok and res.turns_spent == 0
    assert u.players["P1"].corp_ticker == "XYZ"
    assert u.players["P1"].credits == 0
    assert u.corporations["XYZ"].ceo_id == "P1"


def test_cr3_cr4_cr5_cr6_password_and_one_breakin():
    u = _u()
    assert _act(u, "P1", "corp_create", ticker="XYZ", name="Ex").ok
    assert _act(u, "P1", "corp_invite", target="P2").error == "set a password first"
    assert _act(u, "P2", "corp_join", ticker="XYZ", password="nope").error == "set a password first"
    assert _act(u, "P1", "corp_set_password", password="Zx9").ok
    assert _act(u, "P2", "corp_join", ticker="XYZ", password="zx9").error == "wrong password"
    assert u.players["P2"].corp_breakins_today == 1
    again = _act(u, "P2", "corp_join", ticker="XYZ", password="ZZZZ")
    assert again.ok is False and again.error == "one break-in attempt per day"
    assert u.players["P2"].corp_breakins_today == 1
    tick_day(u)
    assert u.players["P2"].corp_breakins_today == 0
    assert _act(u, "P2", "corp_join", ticker="XYZ", password="Zx9").ok
    assert "password" not in u.events[-1].payload


def test_cr7_sixth_member_is_refused():
    u = _u()
    _act(u, "P1", "corp_create", ticker="XYZ", name="Ex")
    _act(u, "P1", "corp_set_password", password="Zx9")
    for i, pid in enumerate(("P2", "P3")):
        assert _act(u, pid, "corp_join", ticker="XYZ", password="Zx9").ok
    for n in range(2):
        pid = f"E{n}"
        u.players[pid] = Player(id=pid, name=pid, sector_id=1, credits=1000)
        assert _act(u, pid, "corp_join", ticker="XYZ", password="Zx9").ok
    assert len(u.corporations["XYZ"].member_ids) == CORP_MAX_MEMBERS
    u.players["E9"] = Player(id="E9", name="E9", sector_id=1, credits=1000)
    assert _act(u, "E9", "corp_join", ticker="XYZ", password="Zx9").error == "corp is full"
    u.config.corp_max_members = 7
    assert _act(u, "E9", "corp_join", ticker="XYZ", password="Zx9").error == "corp is full"


def test_cr9_hek_penalty():
    u = _u()
    _act(u, "P1", "corp_create", ticker="XYZ", name="Ex")
    _act(u, "P1", "corp_set_password", password="Zx9")
    _act(u, "P2", "corp_join", ticker="XYZ", password="Zx9")
    # Highest good alignment 2328 / 4 = 582. P2 is evil, so the corp is mixed.
    u.players["P1"].alignment = 2328
    u.players["P1"].experience = 102
    u.players["P2"].alignment = -80558
    u.players["P2"].experience = 7890
    before = u.day
    tick_day(u)
    assert u.day == before + 1
    # Midnight grants +1 experience before the penalty, and +1 alignment, so 2329 // 4 = 582.
    assert u.players["P2"].experience == 7890 + 1 - 582
    assert u.players["P1"].experience == 1


def test_cr11_ceo_leave_dissolves_and_rogues_fighters():
    u = _u()
    _act(u, "P1", "corp_create", ticker="XYZ", name="Ex")
    _act(u, "P1", "corp_set_password", password="Zx9")
    _act(u, "P2", "corp_join", ticker="XYZ", password="Zx9")
    u.players["P1"].sector_id = 20
    u.sectors[40].fighters = FighterDeployment(owner_id="P1", count=200, mode=FighterMode.DEFENSIVE, corp_ticker="XYZ")
    u.sectors[20].fighters = FighterDeployment(owner_id="P1", count=10, mode=FighterMode.DEFENSIVE, corp_ticker="XYZ")
    assert _act(u, "P1", "corp_leave").ok
    assert "XYZ" not in u.corporations
    assert u.players["P2"].corp_ticker is None
    assert u.sectors[20].fighters.owner_id == "P1"
    assert u.sectors[20].fighters.corp_ticker is None
    assert u.sectors[40].fighters.owner_id == "rogue"


def test_cr14_drop_keeps_ship_fighters():
    u = _u()
    _act(u, "P1", "corp_create", ticker="XYZ", name="Ex")
    _act(u, "P1", "corp_set_password", password="Zx9")
    _act(u, "P2", "corp_join", ticker="XYZ", password="Zx9")
    u.players["P2"].ship.fighters = 40
    assert _act(u, "P1", "corp_drop", target="P2").ok
    assert u.players["P2"].corp_ticker is None
    assert u.players["P2"].ship.fighters == 40


def test_cr16_transfer_refuses_over_the_receiver_room():
    u = _u()
    _act(u, "P1", "corp_create", ticker="XYZ", name="Ex")
    _act(u, "P1", "corp_set_password", password="Zx9")
    _act(u, "P2", "corp_join", ticker="XYZ", password="Zx9")
    cap = int(hull_spec(u.players["P2"].ship.ship_class.value)["max_fighters"])
    u.players["P2"].ship.fighters = cap - 500
    u.players["P1"].ship.fighters = 1000
    res = _act(u, "P1", "corp_transfer", target="P2", item="fighters", qty=1000, direction="give")
    assert res.ok is False and "500" in (res.error or "")
    assert u.players["P2"].ship.fighters == cap - 500
    assert _act(u, "P2", "corp_transfer", target="P1", item="fighters", qty=300, direction="take").ok
    assert u.players["P2"].ship.fighters == cap - 200


def test_cr18_personal_fighters_hit_a_corp_mate():
    from tw2k.engine.corp import deploy_friend

    u = _u()
    _act(u, "P1", "corp_create", ticker="XYZ", name="Ex")
    _act(u, "P1", "corp_set_password", password="Zx9")
    _act(u, "P2", "corp_join", ticker="XYZ", password="Zx9")
    personal = FighterDeployment(owner_id="P1", count=10, mode=FighterMode.DEFENSIVE)
    corporate = FighterDeployment(owner_id="P1", count=10, mode=FighterMode.DEFENSIVE, corp_ticker="XYZ")
    assert deploy_friend(u, "P2", personal) is False
    assert deploy_friend(u, "P2", corporate) is True
    mine = MineDeployment(owner_id="P1", kind=MineType.LIMPET, count=1, corp_ticker="XYZ")
    assert deploy_friend(u, "P2", mine) is True


def test_cr26_treasury_verbs_are_unsupported():
    u = _u()
    _act(u, "P1", "corp_create", ticker="XYZ", name="Ex")
    kinds = {la.kind: la for la in legal_actions(u, "P1")}
    assert kinds["corp_deposit"].legal is False
    assert kinds["corp_withdraw"].legal is False
    assert _act(u, "P1", "corp_deposit", amount=10).error == "unsupported action"


def test_cr27_password_stays_off_the_event():
    u = _u()
    _act(u, "P1", "corp_create", ticker="XYZ", name="Ex")
    _act(u, "P1", "corp_set_password", password="Zx9")
    blob = str(u.events[-1].payload)
    assert "Zx9" not in blob


def test_cr32_legal_create_matches_away_from_stardock():
    u = _u()
    u.players["P1"].sector_id = 40
    u.players["P1"].credits = 0
    las = {la.kind: la for la in legal_actions(u, "P1")}
    saved = copy.deepcopy(u)
    res = _act(u, "P1", "corp_create", ticker="QQQ", name="Q")
    assert las["corp_create"].legal is True
    assert res.ok
    assert saved.players["P1"].credits == 0
