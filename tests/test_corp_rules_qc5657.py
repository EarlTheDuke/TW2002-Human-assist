"""QC slice 57 (corp-rules-v1): rules and fog the slice tests did not cover. CORP_RULES.md."""

from __future__ import annotations

import random

from tw2k.engine import GameConfig, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import FighterDeployment, FighterMode, MineDeployment, MineType, Player
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import _apply_sector_hazards, apply_action, tick_day

NEW_VERBS = {"corp_set_password", "corp_drop", "corp_transfer"}


def _u(n=4):
    u = generate_universe(GameConfig(
        seed=31, universe_size=90, max_days=5, turns_per_day=200,
        starting_credits=25_000, enable_ferrengi=False, enable_planets=True,
    ))
    names = ("Ann", "Ben", "Cid", "Dot", "Eve", "Fay", "Gus")
    for i in range(n):
        pid = f"P{i + 1}"
        u.players[pid] = Player(id=pid, name=names[i], agent_kind="external", sector_id=1, credits=25_000)
        u.sectors[1].occupant_ids.append(pid)
    return u


def _act(u, pid, kind, **args):
    return apply_action(u, pid, Action(kind=ActionKind(kind), args=args))


def _corp(u, members=("P2",), password="Zx9"):
    assert _act(u, "P1", "corp_create", ticker="XYZ", name="Ex").ok
    assert _act(u, "P1", "corp_set_password", password=password).ok
    for pid in members:
        assert _act(u, pid, "corp_join", ticker="XYZ", password=password).ok
    return u.corporations["XYZ"]


def _kind(la):
    return getattr(la.kind, "value", la.kind)


def _legal(u, pid, kind):
    return next(la for la in legal_actions(u, pid) if _kind(la) == kind)


def _move(u, pid, sector_id):
    p = u.players[pid]
    for s in u.sectors.values():
        if pid in s.occupant_ids:
            s.occupant_ids.remove(pid)
    p.sector_id = sector_id
    u.sectors[sector_id].occupant_ids.append(pid)


def _far_sector(u, *avoid):
    for sid in sorted(u.sectors):
        if sid not in K.FEDSPACE_SECTORS and sid not in avoid and sid > 20:
            return sid
    raise AssertionError("no sector")


def _seen_kinds(u, pid):
    obs = build_observation(u, pid)
    return [e["kind"] for e in obs.model_dump(mode="json")["recent_events"]]


# ---- legacy keeps the engine before the slice ---------------------------------------------

def test_qc_legacy_dead_trader_list_has_no_new_corp_verbs(monkeypatch):
    monkeypatch.setattr(K, "CORP_MODE", "legacy")
    u = _u()
    u.players["P1"].alive = False
    kinds = {_kind(la) for la in legal_actions(u, "P1")}
    assert not (kinds & NEW_VERBS)


def test_qc_legacy_new_corp_verbs_are_unsupported(monkeypatch):
    monkeypatch.setattr(K, "CORP_MODE", "legacy")
    u = _u()
    u.players["P1"].credits = 600_000
    assert _act(u, "P1", "corp_create", ticker="XYZ", name="Ex").ok
    assert u.players["P1"].credits == 600_000 - K.CORP_FORMATION_COST
    for kind, args in (("corp_set_password", {"password": "abc"}), ("corp_drop", {"target": "P2"}),
                       ("corp_transfer", {"target": "P2", "item": "credits", "qty": 1, "direction": "give"})):
        res = _act(u, "P1", kind, **args)
        assert res.ok is False and "unsupported" in (res.error or "")
    assert u.corporations["XYZ"].password == ""
    assert "password" not in u.corporations["XYZ"].model_dump()


def test_qc_legacy_create_needs_stardock_and_treasury_works(monkeypatch):
    monkeypatch.setattr(K, "CORP_MODE", "legacy")
    u = _u()
    u.players["P1"].credits = 600_000
    _move(u, "P1", 40)
    assert _act(u, "P1", "corp_create", ticker="XYZ", name="Ex").ok is False
    _move(u, "P1", 1)
    assert _act(u, "P1", "corp_create", ticker="XYZ", name="Ex").ok
    assert _act(u, "P1", "corp_deposit", amount=1000).ok
    assert u.corporations["XYZ"].treasury == 1000
    obs = build_observation(u, "P1").model_dump(mode="json")
    assert "treasury" in obs["corp"] and "corporations" not in obs


# ---- fog: cr27 / cr28 ---------------------------------------------------------------------

def test_qc_invite_is_hidden_from_other_pass_holders():
    u = _u()
    _corp(u, members=())
    assert _act(u, "P1", "corp_invite", target="P2").ok
    assert _act(u, "P1", "corp_invite", target="P3").ok
    obs = build_observation(u, "P3").model_dump(mode="json")
    invites = [e for e in obs["recent_events"] if e["kind"] == "corp_invite"]
    assert len(invites) == 1  # only his own pass, not P2's
    assert "corp_invite" not in _seen_kinds(u, "P4")


def test_qc_exp_penalty_is_private():
    u = _u()
    _corp(u, members=("P2",))
    u.players["P1"].alignment = 400
    u.players["P1"].experience = 900
    u.players["P2"].alignment = -400
    u.players["P2"].experience = 900
    tick_day(u)
    mine = [e for e in u.events if e.kind.value == "corp_exp_penalty"]
    assert len(mine) == 2
    obs = build_observation(u, "P1").model_dump(mode="json")
    seen = [e for e in obs["recent_events"] if e["kind"] == "corp_exp_penalty"]
    assert len(seen) == 1


def test_qc_password_never_reaches_a_non_member():
    u = _u()
    _corp(u, members=("P2",), password="Qz7")
    assert _act(u, "P1", "corp_invite", target="P3").ok
    for pid in ("P4",):
        blob = build_observation(u, pid).model_dump_json()
        assert "Qz7" not in blob
        assert "Qz7" not in str([la.model_dump() for la in legal_actions(u, pid)])
    for ev in u.events:
        assert "Qz7" not in str(ev.payload) and "Qz7" not in (ev.summary or "")
    assert "Qz7" in build_observation(u, "P2").model_dump_json()  # members hand out passes


# ---- join: legal list == handler -----------------------------------------------------------

def test_qc_join_legal_hides_closed_corps_and_spent_breakins():
    u = _u()
    assert _act(u, "P1", "corp_create", ticker="XYZ", name="Ex").ok
    la = _legal(u, "P2", "corp_join")
    assert "XYZ" not in la.params["ticker"]["choices"]  # closed until the C.E.O. sets a password
    assert _act(u, "P1", "corp_set_password", password="Zx9").ok
    la = _legal(u, "P2", "corp_join")
    assert la.legal and "XYZ" in la.params["ticker"]["choices"]
    assert _act(u, "P2", "corp_join", ticker="XYZ", password="bad").ok is False
    la = _legal(u, "P2", "corp_join")
    assert la.legal is False and "break-in" in (la.reason or "")
    assert la.params["breakin_attempts_left"] == 0


def test_qc_same_side_join_and_oust(monkeypatch):
    monkeypatch.setattr(K, "CORP_ALIGNMENT_RULE", "same_side")
    u = _u()
    _corp(u, members=())
    u.players["P2"].alignment = -10
    assert _act(u, "P2", "corp_join", ticker="XYZ", password="Zx9").ok is False
    assert "XYZ" not in _legal(u, "P2", "corp_join").params["ticker"]["choices"]
    u.players["P3"].alignment = 0  # zero counts as good
    assert _act(u, "P3", "corp_join", ticker="XYZ", password="Zx9").ok
    u.players["P3"].alignment = -500
    tick_day(u)
    assert "P3" not in u.corporations["XYZ"].member_ids
    assert any(e.kind.value == "corp_ousted" for e in u.events)


def test_qc_mixed_rule_never_applies_same_side():
    u = _u()
    _corp(u, members=())
    u.players["P2"].alignment = -900
    assert _act(u, "P2", "corp_join", ticker="XYZ", password="Zx9").ok


# ---- transfers ----------------------------------------------------------------------------

def test_qc_transfer_refuses_an_eliminated_member_and_fractions():
    u = _u()
    _corp(u, members=("P2",))
    assert _act(u, "P1", "corp_transfer", target="P2", item="credits", qty=2.5, direction="give").ok is False
    assert _act(u, "P1", "corp_transfer", target="P2", item="credits", qty=True, direction="give").ok is False
    u.players["P2"].alive = False
    assert _act(u, "P1", "corp_transfer", target="P2", item="credits", qty=10, direction="give").ok is False
    assert _legal(u, "P1", "corp_transfer").params["partners"] == []


def test_qc_transfer_take_and_give_matrix():
    u = _u()
    _corp(u, members=("P2",))
    sid = _far_sector(u)
    _move(u, "P1", sid)
    _move(u, "P2", sid)
    u.players["P2"].ship.shields = 300
    before = u.players["P1"].ship.shields
    assert _act(u, "P1", "corp_transfer", target="P2", item="shields", qty=100, direction="take").ok
    assert u.players["P1"].ship.shields == before + 100 and u.players["P2"].ship.shields == 200
    assert _act(u, "P1", "corp_transfer", target="P3", item="credits", qty=1, direction="take").ok is False
    _move(u, "P2", 1)
    assert _act(u, "P1", "corp_transfer", target="P2", item="credits", qty=1, direction="give").ok is False


# ---- deployments --------------------------------------------------------------------------

def test_qc_leaver_is_not_recognized_by_the_corporate_group_he_last_fed():
    u = _u()
    _corp(u, members=("P2",))
    sid = _far_sector(u)
    u.sectors[sid].fighters = FighterDeployment(owner_id="P2", count=400, mode=FighterMode.OFFENSIVE,
                                                corp_ticker="XYZ")
    assert _act(u, "P2", "corp_leave").ok
    _move(u, "P2", sid)
    u.players["P2"].ship.fighters = 20
    _apply_sector_hazards(u, "P2", u.sectors[sid], entry_verb="warp")
    assert u.players["P2"].ship.fighters < 20 or u.players["P2"].deaths > 0


def test_qc_corporate_group_lets_a_member_pass_and_blocks_others():
    u = _u()
    _corp(u, members=("P2",))
    sid = _far_sector(u)
    u.sectors[sid].fighters = FighterDeployment(owner_id="P1", count=400, mode=FighterMode.OFFENSIVE,
                                                corp_ticker="XYZ")
    for pid in ("P2", "P4"):
        _move(u, pid, sid)
        u.players[pid].ship.fighters = 20
        _apply_sector_hazards(u, pid, u.sectors[sid], entry_verb="warp")
    assert u.players["P2"].ship.fighters == 20 and u.players["P2"].deaths == 0
    assert u.players["P4"].ship.fighters < 20 or u.players["P4"].deaths > 0


def test_qc_redeploy_zero_without_ownership_keeps_the_kind():
    u = _u()
    _corp(u, members=("P2",))
    sid = _far_sector(u)
    _move(u, "P1", sid)
    assert _act(u, "P1", "deploy_fighters", qty=10, mode="defensive", ownership="personal").ok
    assert u.sectors[sid].fighters.corp_ticker is None
    assert _act(u, "P1", "deploy_fighters", qty=0, mode="toll").ok
    dep = u.sectors[sid].fighters
    assert dep.mode == FighterMode.TOLL and dep.corp_ticker is None


def test_qc_deploy_legal_offers_ownership_and_recall_lists_corporate_groups():
    u = _u()
    _corp(u, members=("P2",))
    sid = _far_sector(u)
    _move(u, "P1", sid)
    _move(u, "P2", sid)
    la = _legal(u, "P1", "deploy_fighters")
    assert set(la.params["ownership"]["choices"]) == {"personal", "corporate"}
    assert la.params["ownership"]["default"] == "corporate"
    assert set(_legal(u, "P4", "deploy_fighters").params["ownership"]["choices"]) == {"personal"}
    assert _act(u, "P1", "deploy_fighters", qty=10, mode="defensive", ownership="corporate").ok
    rec = _legal(u, "P2", "recall_deployed")
    assert rec.legal and "fighters" in rec.params["what"]["choices"]
    assert _act(u, "P2", "recall_deployed", what="fighters", qty=5).ok
    dm = _legal(u, "P1", "deploy_mines")
    assert "ownership" in dm.params


def test_qc_limpet_view_follows_s12_for_corp_mates():
    # s12 (scanners-hidden-info-v1): you see your own and your corp's limpets. QC 57 keeps that for a
    # corp mate's personal limpet (open call for Ben) and labels the group by ownership.
    from tw2k.engine.scanners import visible_mines
    u = _u()
    _corp(u, members=("P2",))
    sid = _far_sector(u)
    u.sectors[sid].mines = [MineDeployment(owner_id="P2", kind=MineType.LIMPET, count=3)]
    assert visible_mines(u, "P1", u.sectors[sid])[0]["owner"] == "personal"
    assert visible_mines(u, "P3", u.sectors[sid]) == []
    u.sectors[sid].mines = [MineDeployment(owner_id="P2", kind=MineType.LIMPET, count=3, corp_ticker="XYZ")]
    assert visible_mines(u, "P1", u.sectors[sid])[0]["owner"] == "corporate"
    assert visible_mines(u, "P3", u.sectors[sid]) == []


def test_qc_sector_view_shows_fighter_ownership():
    u = _u()
    _corp(u, members=("P2",))
    sid = _far_sector(u)
    u.sectors[sid].fighters = FighterDeployment(owner_id="P1", count=5, mode=FighterMode.DEFENSIVE,
                                                corp_ticker="XYZ")
    _move(u, "P2", sid)
    obs = build_observation(u, "P2").model_dump(mode="json")
    assert obs["sector"]["fighter_group"]["ownership"] == "corporate"


# ---- rogue --------------------------------------------------------------------------------

def _edge(u):
    for sid in sorted(u.sectors):
        if sid in K.FEDSPACE_SECTORS or sid <= 20:
            continue
        for w in sorted(u.sectors[sid].warps):
            if w not in K.FEDSPACE_SECTORS and w > 20:
                return sid, w
    raise AssertionError("no edge")


def test_qc_rogue_kill_has_no_killer_and_no_keyerror():
    u = _u()
    planet = next(pl for pl in u.planets.values() if pl.sector_id not in K.FEDSPACE_SECTORS)
    dst = planet.sector_id
    planet.owner_id = "P4"  # a hostile landing runs the sector hazards, then the fighter-loss kill
    u.sectors[dst].fighters = FighterDeployment(owner_id=K.ROGUE_OWNER_ID, count=5000, mode=FighterMode.OFFENSIVE)
    p = u.players["P3"]
    _move(u, "P3", dst)
    p.ship.fighters = 1
    p.ship.shields = 0
    p.ship.corbomite = 5
    _act(u, "P3", "land_planet", planet_id=planet.id)
    for pid in u.players:
        build_observation(u, pid)
        legal_actions(u, pid)
    deaths = [e for e in u.events if e.kind.value == "ship_destroyed"]
    assert deaths, "the rogue group should destroy the ship"
    assert deaths[-1].payload.get("killer_id") is None and deaths[-1].actor_id is None
    assert K.ROGUE_OWNER_ID not in u.players


def test_qc_eliminated_ceo_sector_fighters_go_rogue():
    u = _u()
    _corp(u, members=("P2",))
    sid = _far_sector(u)
    _move(u, "P1", sid)
    u.sectors[sid].fighters = FighterDeployment(owner_id="P2", count=50, mode=FighterMode.DEFENSIVE,
                                                corp_ticker="XYZ")
    u.players["P1"].alive = False
    tick_day(u)
    assert "XYZ" not in u.corporations
    assert u.sectors[sid].fighters.owner_id == K.ROGUE_OWNER_ID


def test_qc_disband_mines_ceo_sector_personal_elsewhere_rogue_or_removed(monkeypatch):
    for mode in ("rogue", "removed"):
        monkeypatch.setattr(K, "CORP_DISBAND_MINES", mode)
        u = _u()
        _corp(u, members=("P2",))
        a, b = _far_sector(u), _far_sector(u, _far_sector(u))
        _move(u, "P1", a)
        u.sectors[a].mines = [MineDeployment(owner_id="P2", kind=MineType.ARMID, count=4, corp_ticker="XYZ")]
        u.sectors[b].mines = [MineDeployment(owner_id="P2", kind=MineType.ARMID, count=4, corp_ticker="XYZ")]
        assert _act(u, "P1", "corp_leave").ok
        assert u.sectors[a].mines[0].owner_id == "P1" and u.sectors[a].mines[0].corp_ticker is None
        if mode == "rogue":
            assert u.sectors[b].mines[0].owner_id == K.ROGUE_OWNER_ID
        else:
            assert u.sectors[b].mines == []
        assert all(p.corp_ticker is None for p in u.players.values())


def test_qc_v306_orphan_names_the_real_former_owner(monkeypatch):
    monkeypatch.setattr(K, "CORP_DISBAND_PLANETS", "v306")
    u = _u()
    _corp(u, members=("P2",))
    planet = next(iter(u.planets.values()))
    planet.owner_id = "P2"
    planet.corp_ticker = "XYZ"
    _move(u, "P1", _far_sector(u, planet.sector_id))
    assert _act(u, "P1", "corp_leave").ok
    assert planet.owner_id is None and planet.corp_ticker is None
    orphan = [e for e in u.events if e.kind.value == "planet_orphaned"]
    assert orphan and orphan[-1].payload["former_owner"] == "P2"


# ---- leave / drop planets (cr10, cr14) -----------------------------------------------------

def test_qc_leaver_planets_corp_keeps_and_leaver_keeps(monkeypatch):
    for mode, owner, ticker in (("corp_keeps", "P1", "XYZ"), ("leaver_keeps", "P2", None)):
        monkeypatch.setattr(K, "CORP_LEAVER_PLANETS", mode)
        u = _u()
        _corp(u, members=("P2",))
        planet = next(iter(u.planets.values()))
        planet.owner_id, planet.corp_ticker = "P2", "XYZ"
        u.players["P2"].ship.fighters = 77
        assert _act(u, "P2", "corp_leave").ok
        assert (planet.owner_id, planet.corp_ticker) == (owner, ticker)
        assert u.players["P2"].ship.fighters == 77


# ---- observation (cr22-cr24) ---------------------------------------------------------------

def test_qc_member_block_planets_and_penalty_estimate(monkeypatch):
    u = _u()
    _corp(u, members=("P2",))
    planet = next(iter(u.planets.values()))
    planet.owner_id, planet.corp_ticker = "P2", "XYZ"
    block = build_observation(u, "P1").model_dump(mode="json")["corp"]
    row = block["planets"][0]
    assert {"production", "stock", "population"} <= set(row)
    u.players["P1"].alignment, u.players["P2"].alignment = 2000, -9000
    monkeypatch.setattr(K, "MIXED_CORP_EXP_RULE", "least_extreme")
    u.players["P1"].alignment, u.players["P2"].alignment = 9000, -2000
    block = build_observation(u, "P1").model_dump(mode="json")["corp"]
    assert block["exp_penalty_tomorrow"] == 2000 // 4
    monkeypatch.setattr(K, "CORP_ALIGNMENT_RULE", "same_side")
    block = build_observation(u, "P1").model_dump(mode="json")["corp"]
    assert block["exp_penalty_tomorrow"] == 0


def test_qc_rivals_see_only_the_public_list():
    u = _u()
    _corp(u, members=("P2",))
    obs = build_observation(u, "P4").model_dump(mode="json")
    assert obs.get("corp") is None
    row = obs["corporations"][0]
    assert set(row) == {"ticker", "name", "formed_day", "ceo", "members", "rank", "exp", "alignment"}
    blob = str(row)
    assert "credits" not in blob and "sector" not in blob


def test_qc_ranking_sums_members_and_ties_by_ticker():
    from tw2k.engine.corp import public_corporations
    u = _u(5)
    _corp(u, members=("P2",))
    assert _act(u, "P3", "corp_create", ticker="ABC", name="Ab").ok
    for pid, exp in (("P1", 100), ("P2", 50), ("P3", 150)):
        u.players[pid].experience = exp
    rows = public_corporations(u)
    assert [r["ticker"] for r in rows] == ["ABC", "XYZ"] and rows[1]["exp"] == 150
    assert [r["rank"] for r in rows] == [1, 2]


# ---- recall failure does not move ownership; create alt cost ---------------------------------

def test_qc_failed_recall_keeps_the_owner():
    u = _u()
    _corp(u, members=("P2",))
    sid = _far_sector(u)
    _move(u, "P2", sid)
    u.sectors[sid].fighters = FighterDeployment(owner_id="P1", count=50, mode=FighterMode.DEFENSIVE,
                                                corp_ticker="XYZ")
    u.players["P2"].turns_today = u.players["P2"].turns_per_day
    res = _act(u, "P2", "recall_deployed", what="fighters", qty=5)
    assert res.ok is False
    assert u.sectors[sid].fighters.owner_id == "P1"


def test_qc_create_cost_alt_legal_matches_handler(monkeypatch):
    monkeypatch.setattr(K, "CORP_CREATE_COST", 500_000)
    u = _u()
    la = _legal(u, "P1", "corp_create")
    res = _act(u, "P1", "corp_create", ticker="XYZ", name="Ex")
    assert la.legal == res.ok


# ---- legal == handler property test (cr32) ---------------------------------------------------

def test_qc_corp_verbs_legal_matches_handler_property():
    import copy
    rng = random.Random(5657)
    for trial in range(60):
        u = _u(5)
        if rng.random() < 0.8:
            assert _act(u, "P1", "corp_create", ticker="XYZ", name="Ex").ok
            if rng.random() < 0.8:
                _act(u, "P1", "corp_set_password", password="Zx9")
                for pid in ("P2", "P3"):
                    if rng.random() < 0.6:
                        _act(u, pid, "corp_join", ticker="XYZ", password="Zx9")
        sid = rng.choice([1, _far_sector(u)])
        for pid in u.players:
            if rng.random() < 0.5:
                _move(u, pid, sid)
            u.players[pid].ship.fighters = rng.choice([0, 30, 2000])
        if rng.random() < 0.3:
            u.players["P2"].alive = False
        if rng.random() < 0.3:
            u.players["P3"].corp_breakins_today = 1
        for pid in u.players:
            if not u.players[pid].alive:
                continue
            for la in legal_actions(u, pid):
                kind = _kind(la)
                if kind not in ("corp_invite", "corp_join", "corp_drop", "corp_transfer", "corp_leave",
                                "corp_set_password", "corp_memo"):
                    continue
                args = {}
                if kind == "corp_invite":
                    if not la.params["target"]["choices"]:
                        assert not la.legal
                        continue
                    args = {"target": la.params["target"]["choices"][0]}
                elif kind == "corp_join":
                    if not la.params["ticker"]["choices"]:
                        assert not la.legal
                        continue
                    args = {"ticker": la.params["ticker"]["choices"][0], "password": "Zx9"}
                elif kind == "corp_drop":
                    if not la.params["target"]["choices"]:
                        assert not la.legal
                        continue
                    args = {"target": la.params["target"]["choices"][0]}
                elif kind == "corp_transfer":
                    if not la.params["partners"]:
                        assert not la.legal
                        continue
                    part = la.params["partners"][0]
                    args = {"target": part["player_id"], "item": "credits", "qty": 1, "direction": "give"}
                elif kind == "corp_set_password":
                    args = {"password": "Ab1"}
                elif kind == "corp_memo":
                    args = {"message": "hi"}
                v = copy.deepcopy(u)
                res = apply_action(v, pid, Action(kind=ActionKind(kind), args=args))
                if kind == "corp_transfer" and u.players[pid].credits < 1:
                    continue
                assert res.ok == la.legal, (trial, pid, kind, args, la.reason, res.error)


# ---- seat bots (cr29) -----------------------------------------------------------------------

def _pair_steps(u, monkeypatch, policy, rounds=4):
    from tw2k.agents.seat_acceptance import validate_action
    from tw2k.agents.seat_brain import SeatBrain, View
    monkeypatch.setattr(K, "BOT_CORP_POLICY", policy)
    brains = {pid: SeatBrain() for pid in u.players}
    used = []
    for _ in range(rounds):
        for pid in sorted(u.players):
            obs = build_observation(u, pid).model_dump(mode="json")
            act = brains[pid]._corp_pair(View(obs))
            if act is None:
                continue
            assert validate_action(obs, act) == []
            res = _act(u, pid, act["kind"], **act["args"])
            assert res.ok, (pid, act, res.error)
            used.append((pid, act["kind"]))
    return used


def test_qc_policy_off_never_uses_corp_verbs(monkeypatch):
    u = _u()
    assert _pair_steps(u, monkeypatch, "off") == []
    assert not u.corporations


def test_qc_pair_policy_forms_one_corp_and_deploys_corporate(monkeypatch):
    from tw2k.agents.seat_brain import PAIR_PASSWORD, PAIR_TICKER, SeatBrain, View
    u = _u()
    used = _pair_steps(u, monkeypatch, "pair")
    assert [k for _, k in used] == ["corp_create", "corp_set_password", "corp_invite", "corp_join"]
    assert sorted(u.corporations[PAIR_TICKER].member_ids) == ["P1", "P2"]
    assert u.players["P3"].corp_ticker is None and u.players["P4"].corp_ticker is None
    for pid in ("P3", "P4"):  # the password never reaches a non-member's observation
        assert PAIR_PASSWORD not in build_observation(u, pid).model_dump_json()
    sid = _far_sector(u)
    _move(u, "P2", sid)
    u.players["P2"].ship.fighters = 50
    obs = build_observation(u, "P2").model_dump(mode="json")
    assert SeatBrain._pair_ownership(View(obs), "deploy_fighters") == {"ownership": "corporate"}
    assert _act(u, "P2", "deploy_fighters", qty=10, mode="defensive", ownership="corporate").ok
    assert u.sectors[sid].fighters.corp_ticker == PAIR_TICKER
    obs3 = build_observation(u, "P3").model_dump(mode="json")
    assert SeatBrain._pair_ownership(View(obs3), "deploy_fighters") == {}


def test_qc_cr30_prompt_numbers_follow_the_constants(monkeypatch):
    from tw2k.agents.prompts import get_system_prompt
    assert "Corporations are free and work in any sector" in get_system_prompt()
    monkeypatch.setattr(K, "CORP_CREATE_COST", 500_000)
    monkeypatch.setattr(K, "CORP_TURN_COST", 2)
    text = get_system_prompt()
    assert "Corporations cost 500,000 credits and 2 turns and work in any sector" in text
    assert "Corporations are free" not in text
    monkeypatch.setattr(K, "CORP_MODE", "legacy")
    assert "Corporations cost" not in get_system_prompt()


def test_qc_holo_view_labels_fighter_ownership(monkeypatch):
    from tw2k.engine.scanners import sector_view
    u = _u()
    _corp(u, members=("P2",))
    sid = _far_sector(u)
    sec = u.sectors[sid]
    sec.fighters = FighterDeployment(owner_id="P1", count=7, mode=FighterMode.DEFENSIVE, corp_ticker="XYZ")
    assert sector_view(u, "P3", sid)["fighters"]["ownership"] == "corporate"
    sec.fighters = FighterDeployment(owner_id=K.ROGUE_OWNER_ID, count=7, mode=FighterMode.DEFENSIVE)
    assert sector_view(u, "P3", sid)["fighters"]["ownership"] == "rogue"
    sec.fighters = FighterDeployment(owner_id="P2", count=7, mode=FighterMode.DEFENSIVE)
    assert sector_view(u, "P3", sid)["fighters"]["ownership"] == "personal"
    monkeypatch.setattr(K, "CORP_MODE", "legacy")
    assert "ownership" not in sector_view(u, "P3", sid)["fighters"]


# ---- plant follow-ups (QC 57 mutation run) ----------------------------------------------------

def test_qc_pb6_changed_password_invalidates_old_pass():
    u = _u()
    assert _act(u, "P1", "corp_create", ticker="XYZ", name="Ex").ok
    assert _act(u, "P1", "corp_set_password", password="aa").ok
    assert _act(u, "P1", "corp_invite", target="P2").ok
    assert _act(u, "P1", "corp_set_password", password="bb").ok
    old = [m for m in u.players["P2"].inbox if m.get("kind") == "corp_invite"][-1]["password"]
    assert old == "aa"
    res = _act(u, "P2", "corp_join", ticker="XYZ", password=old)
    assert not res.ok and res.error == "wrong password"
    assert u.players["P2"].corp_ticker is None


def test_qc_pb8_alignment_rule_mixed_never_ousts_and_same_side_does(monkeypatch):
    from tw2k.engine.corp import extern_corp_step
    u = _u()
    _corp(u, members=("P2",))
    u.players["P1"].alignment, u.players["P2"].alignment = 500, -500
    extern_corp_step(u)
    assert "P2" in u.corporations["XYZ"].member_ids  # mixed (default): stays, pays the penalty
    monkeypatch.setattr(K, "CORP_ALIGNMENT_RULE", "same_side")
    extern_corp_step(u)
    assert "P2" not in u.corporations["XYZ"].member_ids and u.players["P2"].corp_ticker is None


def test_qc_pb9_penalty_formula_and_straight_corp(monkeypatch):
    from tw2k.engine.corp import extern_corp_step
    u = _u()
    _corp(u, members=("P2", "P3"))
    u.players["P1"].alignment, u.players["P2"].alignment, u.players["P3"].alignment = 2_000, 300, -400
    for pid in ("P1", "P2", "P3"):
        u.players[pid].experience = 10_000
    extern_corp_step(u)  # highest_good: 2000 // 4 = 500
    assert [u.players[p].experience for p in ("P1", "P2", "P3")] == [9_500] * 3
    monkeypatch.setattr(K, "MIXED_CORP_EXP_RULE", "least_extreme")
    extern_corp_step(u)  # min(2000, |-400|) // 4 = 100
    assert [u.players[p].experience for p in ("P1", "P2", "P3")] == [9_400] * 3
    u.players["P3"].alignment = 50  # straight corp: no loss
    extern_corp_step(u)
    assert [u.players[p].experience for p in ("P1", "P2", "P3")] == [9_400] * 3


def test_qc_pb13_rogue_group_forgets_its_corp_and_cannot_be_recalled():
    from tw2k.engine.corp import deploy_friend, disband
    u = _u()
    _corp(u, members=("P2",))
    sid = _far_sector(u)
    u.sectors[sid].fighters = FighterDeployment(owner_id="P2", count=30, mode=FighterMode.DEFENSIVE,
                                                corp_ticker="XYZ")
    u.sectors[sid].mines = [MineDeployment(owner_id="P2", kind=MineType.ARMID, count=4, corp_ticker="XYZ")]
    disband(u, u.corporations["XYZ"])  # P1 (C.E.O.) is in sector 1, so the groups in sid go rogue
    dep, md = u.sectors[sid].fighters, u.sectors[sid].mines[0]
    assert dep.owner_id == K.ROGUE_OWNER_ID and dep.corp_ticker is None
    assert md.owner_id == K.ROGUE_OWNER_ID and md.corp_ticker is None
    for pid in ("P1", "P2"):
        assert not deploy_friend(u, pid, dep) and not deploy_friend(u, pid, md)
    _move(u, "P2", sid)
    u.players["P2"].ship.fighters = 0
    rec = _legal(u, "P2", "recall_deployed")
    assert not rec.legal or not (rec.params.get("fighters") or rec.params.get("mines"))
    assert not _act(u, "P2", "recall_deployed", what="fighters", qty=5).ok
    assert not apply_action(u, "P2", Action(kind=ActionKind.RECALL_DEPLOYED,
                                            args={"what": "mines", "kind": "armid", "qty": 1})).ok
    assert u.sectors[sid].fighters.count == 30


def test_qc_pb16_transfer_refuses_landed_and_cloaked_partners(monkeypatch):
    u = _u()
    _corp(u, members=("P2",))
    sid = _far_sector(u)
    _move(u, "P1", sid)
    _move(u, "P2", sid)
    u.players["P1"].ship.fighters = 50
    assert _act(u, "P1", "corp_transfer", target="P2", item="credits", qty=10, direction="give").ok
    u.players["P2"].planet_landed = 999
    res = _act(u, "P1", "corp_transfer", target="P2", item="credits", qty=10, direction="give")
    assert not res.ok and "ships" in res.error
    assert "P2" not in _legal(u, "P1", "corp_transfer").params["target"]["choices"]
    u.players["P2"].planet_landed = None
    if K.hardware_tw2002():
        u.players["P2"].ship.cloaked = True
        res = _act(u, "P1", "corp_transfer", target="P2", item="credits", qty=10, direction="give")
        assert not res.ok and "cloaked" in res.error
        assert "P2" not in _legal(u, "P1", "corp_transfer").params["target"]["choices"]


def test_qc_pb18_transfer_with_a_non_member_is_refused():
    u = _u()
    _corp(u, members=("P2",))
    sid = _far_sector(u)
    for pid in ("P1", "P3"):
        _move(u, pid, sid)
    for direction in ("give", "take"):
        res = _act(u, "P1", "corp_transfer", target="P3", item="credits", qty=10, direction=direction)
        assert not res.ok and res.error == "no such member"
    assert u.players["P1"].credits == 25_000 and u.players["P3"].credits == 25_000


def test_qc_pb20_corporate_limpet_never_attaches_to_a_member():
    u = _u()
    _corp(u, members=("P2",))
    sid = _far_sector(u)
    u.sectors[sid].mines = [MineDeployment(owner_id="P1", kind=MineType.LIMPET, count=3, corp_ticker="XYZ")]
    _move(u, "P2", sid)
    _apply_sector_hazards(u, "P2", u.sectors[sid], entry_verb="warp")
    assert u.sectors[sid].mines and u.sectors[sid].mines[0].count == 3
    _move(u, "P4", sid)
    _apply_sector_hazards(u, "P4", u.sectors[sid], entry_verb="warp")
    assert not u.sectors[sid].mines or u.sectors[sid].mines[0].count == 2


def test_qc_pb21_toll_bill_and_surrender_follow_deploy_friend(monkeypatch):
    from tw2k.engine.runner import _surrender_deployment
    u = _u()
    _corp(u, members=("P2",))
    sid = _far_sector(u)
    nb = next(w for w in sorted(u.sectors[sid].warps) if w not in K.FEDSPACE_SECTORS)
    _move(u, "P2", nb)
    monkeypatch.setattr(K, "COMBAT_MODE", "legacy")  # the toll is billed before the warp (no challenge)
    monkeypatch.setattr(K, "INFO_MODE", "legacy")
    sec = u.sectors[sid]
    sec.fighters = FighterDeployment(owner_id="P1", count=10, mode=FighterMode.TOLL, corp_ticker="XYZ")
    warp = _legal(u, "P2", "warp")
    assert str(sid) not in warp.params["toll_due_by"]
    assert _surrender_deployment(u, "P2", sec) is None
    sec.fighters = FighterDeployment(owner_id="P1", count=10, mode=FighterMode.TOLL)  # a mate's personal group
    warp = _legal(u, "P2", "warp")
    assert warp.params["toll_due_by"].get(str(sid), 0) > 0
    assert _surrender_deployment(u, "P2", sec) is sec.fighters


def test_qc_pb22_member_adds_to_the_corp_group_without_combat():
    u = _u()
    _corp(u, members=("P2",))
    sid = _far_sector(u)
    for pid in ("P1", "P2"):
        _move(u, pid, sid)
        u.players[pid].ship.fighters = 50
    assert _act(u, "P1", "deploy_fighters", qty=10, mode="defensive", ownership="corporate").ok
    assert _act(u, "P2", "deploy_fighters", qty=5, mode="defensive", ownership="corporate").ok
    dep = u.sectors[sid].fighters
    assert dep.count == 15 and dep.corp_ticker == "XYZ"
    assert u.players["P1"].ship.fighters == 40 and u.players["P2"].ship.fighters == 45
    assert not any(e.kind.value == "combat" for e in u.events if e.sector_id == sid)


def test_qc_pb24_rivals_see_no_corp_traffic():
    u = _u()
    _corp(u, members=("P2",))
    assert _act(u, "P1", "corp_invite", target="P3").ok
    assert _act(u, "P1", "corp_memo", message="meet at 77").ok
    assert _act(u, "P2", "corp_leave").ok
    kinds = [k for k in _seen_kinds(u, "P4") if str(k).startswith("corp_")]
    assert kinds == []
    assert "meet at 77" not in build_observation(u, "P4").model_dump_json()


def test_qc_pb25_ranking_orders_by_experience_not_ticker():
    from tw2k.engine.corp import public_corporations
    u = _u(5)
    _corp(u, members=("P2",))
    assert _act(u, "P3", "corp_create", ticker="ABC", name="Ab").ok
    for pid, exp in (("P1", 100), ("P2", 60), ("P3", 150)):
        u.players[pid].experience = exp
    rows = public_corporations(u)
    assert [(r["ticker"], r["exp"]) for r in rows] == [("XYZ", 160), ("ABC", 150)]


def test_qc_password_length_invite_targets_and_ceo_approver(monkeypatch):
    u = _u(5)
    _corp(u, members=("P2",))
    too_long = "x" * (int(K.CORPSHIP_PASSWORD_MAX_LEN) + 1)
    assert not _act(u, "P1", "corp_set_password", password=too_long).ok
    assert _act(u, "P3", "corp_create", ticker="ABC", name="Ab").ok
    assert not _act(u, "P1", "corp_invite", target="P3").ok  # already in a corp
    assert "P3" not in _legal(u, "P1", "corp_invite").params["target"]["choices"]
    assert _act(u, "P2", "corp_invite", target="P4").ok  # any member hands out a pass (default)
    monkeypatch.setattr(K, "CORP_APPROVER", "ceo")
    assert not _act(u, "P2", "corp_invite", target="P5").ok
    assert not _legal(u, "P2", "corp_invite").legal
    assert _act(u, "P1", "corp_invite", target="P5").ok


def test_qc_mixed_penalty_ignores_eliminated_and_extern_dissolves_dead_ceo_corp():
    from tw2k.engine.corp import extern_corp_step
    u = _u()
    _corp(u, members=("P2", "P3"))
    u.players["P1"].alignment, u.players["P2"].alignment, u.players["P3"].alignment = 2_000, 100, -400
    for pid in ("P1", "P2", "P3"):
        u.players[pid].experience = 5_000
    u.players["P3"].alive = False  # the only evil member is eliminated: straight corp
    extern_corp_step(u)
    assert u.players["P1"].experience == 5_000 and u.players["P2"].experience == 5_000
    assert "P3" not in u.corporations["XYZ"].member_ids
    u.players["P1"].alive = False  # eliminated C.E.O. -> the corp dissolves at Extern
    extern_corp_step(u)
    assert "XYZ" not in u.corporations and u.players["P2"].corp_ticker is None


def test_qc_credit_transfer_cannot_exceed_the_givers_cash():
    u = _u()
    _corp(u, members=("P2",))
    sid = _far_sector(u)
    for pid in ("P1", "P2"):
        _move(u, pid, sid)
    assert not _act(u, "P1", "corp_transfer", target="P2", item="credits", qty=25_001, direction="give").ok
    assert not _act(u, "P1", "corp_transfer", target="P2", item="credits", qty=25_001, direction="take").ok
    assert _act(u, "P1", "corp_transfer", target="P2", item="credits", qty=25_000, direction="take").ok
    assert u.players["P1"].credits == 50_000 and u.players["P2"].credits == 0


def test_qc_transfer_have_check_turns_and_fog():
    u = _u()
    _corp(u, members=("P2",))
    sid = _far_sector(u)
    for pid in ("P1", "P2", "P4"):
        _move(u, pid, sid)
    u.players["P1"].ship.fighters = 50
    assert not _act(u, "P1", "corp_transfer", target="P2", item="fighters", qty=51, direction="give").ok
    t0 = u.players["P1"].turns_today
    res = _act(u, "P1", "corp_transfer", target="P2", item="fighters", qty=5, direction="give")
    assert res.ok and res.turns_spent == 0 and u.players["P1"].turns_today == t0
    assert "corp_transfer" in _seen_kinds(u, "P2")
    assert "corp_transfer" not in _seen_kinds(u, "P4")


def test_qc_ownership_guards_on_deploy():
    u = _u()
    _corp(u, members=("P2",))
    sid = _far_sector(u)
    for pid in ("P1", "P3", "P4"):
        _move(u, pid, sid)
        u.players[pid].ship.fighters = 50
        u.players[pid].ship.mines[MineType.ARMID] = 10
    # no corp, no corporate deployment
    assert _legal(u, "P3", "deploy_fighters").params["ownership"]["choices"] == ["personal"]
    assert not _act(u, "P3", "deploy_fighters", qty=5, mode="defensive", ownership="corporate").ok
    # corporate into your own personal group (or the reverse) is refused, nothing moves
    assert _act(u, "P1", "deploy_fighters", qty=10, mode="defensive", ownership="corporate").ok
    res = _act(u, "P1", "deploy_fighters", qty=5, mode="defensive", ownership="personal")
    assert not res.ok and u.sectors[sid].fighters.count == 10 and u.players["P1"].ship.fighters == 40
    # a qty-0 change by someone who does not control the group is refused
    assert not _act(u, "P4", "deploy_fighters", qty=0, mode="offensive", ownership="personal").ok
    assert u.sectors[sid].fighters.mode == FighterMode.DEFENSIVE and u.sectors[sid].fighters.corp_ticker == "XYZ"
    # personal and corporate armids stay two groups
    assert apply_action(u, "P1", Action(kind=ActionKind.DEPLOY_MINES,
                                        args={"kind": "armid", "qty": 3, "ownership": "personal"})).ok
    assert apply_action(u, "P1", Action(kind=ActionKind.DEPLOY_MINES,
                                        args={"kind": "armid", "qty": 2, "ownership": "corporate"})).ok
    groups = sorted((m.corp_ticker or "", int(m.count)) for m in u.sectors[sid].mines if m.kind == MineType.ARMID)
    assert groups == [("", 3), ("XYZ", 2)]


def test_qc_leaver_cannot_recall_the_corporate_group_he_deployed():
    u = _u()
    _corp(u, members=("P2",))
    sid = _far_sector(u)
    _move(u, "P2", sid)
    u.players["P2"].ship.fighters = 50
    assert _act(u, "P2", "deploy_fighters", qty=10, mode="defensive", ownership="corporate").ok
    assert _act(u, "P2", "corp_leave").ok
    assert not _act(u, "P2", "recall_deployed", what="fighters", qty=5).ok
    assert u.sectors[sid].fighters.count == 10 and u.sectors[sid].fighters.corp_ticker == "XYZ"
