"""Track B engine: D22 corp fixes and class M planet units.

D22-1 is unconditional. The mixed-corp event names the experience that was
actually taken, down to the floor of 1.

D22-2 stays off. CORP_LEAVER_DEPLOYMENTS "to_ceo" moves the leaver's corporate
fighters and mines onto the C.E.O. Legacy, and V311_PROFILE, leave the
owner id on the ex-member.

Class M net worth, Terra drops, and the genesis seed scale only when their
flags are on (they are on under V311_PROFILE) and class M stores people.
"""

from __future__ import annotations

import pytest

from tw2k.engine import GameConfig, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.corp import _mixed_penalty, extern_corp_step, mixed_loss
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import (
    Commodity,
    EventKind,
    FighterDeployment,
    FighterMode,
    LimpetTrack,
    MineDeployment,
    MineType,
    Planet,
    PlanetClass,
    Player,
)
from tw2k.engine.observation import _sector_detail
from tw2k.engine.runner import _bfs_path, apply_action, grant_starting_planet, tick_day
from tw2k.engine.victory import _planet_asset_value, full_net_worth, planet_tax_value

pytestmark = pytest.mark.legacy_profile


def _u():
    u = generate_universe(GameConfig(
        seed=31, universe_size=90, max_days=20, turns_per_day=60,
        starting_credits=25_000, enable_ferrengi=False, enable_planets=True,
    ))
    for pid, name in (("P1", "Ann"), ("P2", "Ben"), ("P3", "Cid")):
        p = Player(id=pid, name=name, agent_kind="external", sector_id=1, credits=25_000)
        u.players[pid] = p
        u.sectors[1].occupant_ids.append(pid)
    return u


def _act(u, pid, kind, **args):
    return apply_action(u, pid, Action(kind=ActionKind(kind), args=args))


def _join_xyz(u):
    assert _act(u, "P1", "corp_create", ticker="XYZ", name="Ex").ok
    assert _act(u, "P1", "corp_set_password", password="Zx9").ok
    assert _act(u, "P2", "corp_join", ticker="XYZ", password="Zx9").ok
    assert _act(u, "P3", "corp_join", ticker="XYZ", password="Zx9").ok


def _profile(monkeypatch, profile: str) -> None:
    if profile == "v311":
        monkeypatch.setattr(K, "V311_PROFILE", "v311")


def _penalty_for(u, pid: str):
    found = [e for e in u.events if e.kind == EventKind.CORP_EXP_PENALTY and e.actor_id == pid]
    assert len(found) == 1
    return found[0]


def _quiet_sectors(u, n: int) -> list[int]:
    blocked = {int(s) for s in (getattr(u, "msl_sectors", None) or [])}
    blocked.update(int(s) for s in (getattr(u, "class0_sectors", {}) or {}).values())
    blocked.add(int(K.STARDOCK_SECTOR))
    found: list[int] = []
    if 40 in u.sectors and 40 not in blocked:
        found.append(40)
    for sid in sorted(u.sectors):
        if sid in found or sid in blocked or sid <= 10:
            continue
        found.append(sid)
        if len(found) >= n:
            return found
    raise AssertionError("no sector outside the MSL sweep")


def _valued_planet(class_id: PlanetClass, people: int) -> Planet:
    return Planet(
        id=9001,
        sector_id=20,
        name="Home",
        class_id=class_id,
        owner_id="P1",
        origin="other",
        colonists={
            Commodity.FUEL_ORE: 0,
            Commodity.ORGANICS: 0,
            Commodity.EQUIPMENT: 0,
            Commodity.COLONISTS: people,
        },
    )


def _land_world(u, class_id: PlanetClass = PlanetClass.M) -> Planet:
    sid = 20 if 20 in u.sectors else next(iter(u.sectors))
    pid = int(u.next_planet_id)
    u.next_planet_id = pid + 1
    planet = Planet(
        id=pid,
        sector_id=sid,
        name="Home",
        class_id=class_id,
        owner_id="P1",
        origin="other",
    )
    u.planets[pid] = planet
    u.sectors[sid].planet_ids.append(pid)
    player = u.players["P1"]
    if player.sector_id in u.sectors and player.id in u.sectors[player.sector_id].occupant_ids:
        u.sectors[player.sector_id].occupant_ids.remove(player.id)
    player.sector_id = sid
    player.planet_landed = pid
    u.sectors[sid].occupant_ids.append(player.id)
    return planet


def _deep_sector(u) -> int:
    for sid in sorted(u.sectors):
        sector = u.sectors[sid]
        if sid > 10 and not sector.planet_ids and len(_bfs_path(u, K.STARDOCK_SECTOR, sid)) >= K.GENESIS_MIN_HOPS_FROM_STARDOCK:
            return sid
    raise AssertionError("no deep empty sector")


def _stand(u, pid: str, sid: int) -> None:
    player = u.players[pid]
    if player.sector_id in u.sectors and pid in u.sectors[player.sector_id].occupant_ids:
        u.sectors[player.sector_id].occupant_ids.remove(pid)
    player.sector_id = sid
    player.planet_landed = None
    if pid not in u.sectors[sid].occupant_ids:
        u.sectors[sid].occupant_ids.append(pid)


def _cid_corp(u):
    _join_xyz(u)
    u.players["P1"].alignment = 800
    u.players["P1"].experience = 5_000
    u.players["P2"].alignment = -100
    u.players["P2"].experience = 4_000
    u.players["P3"].name = "Cid"
    u.players["P3"].alignment = 100
    u.players["P3"].experience = 30


def _hekate_corp(u):
    _join_xyz(u)
    u.players["P1"].name = "Hekate"
    u.players["P1"].alignment = 2328
    u.players["P1"].experience = 102
    u.players["P2"].name = "Merlin"
    u.players["P2"].alignment = 1064
    u.players["P2"].experience = 1
    u.players["P3"].name = "Acid"
    u.players["P3"].alignment = -80558
    u.players["P3"].experience = 7890


def test_d22_1_legacy_message_names_the_formula():
    """Profile off is the old sentence: the formula, even when the floor took less."""
    assert K.CORP_EXP_PENALTY_MODE == "legacy"
    assert K.corp_exp_penalty_taken() is False
    u = _u()
    _cid_corp(u)
    assert mixed_loss(u, u.corporations["XYZ"]) == 200
    _mixed_penalty(u)
    assert u.players["P3"].experience == 1
    assert u.players["P1"].experience == 4_800
    event = _penalty_for(u, "P3")
    assert event.payload == {"ticker": "XYZ", "loss": 200, "experience": 1}
    assert event.summary == "Cid lost 200 experience for a mixed corp"


def test_d22_1_taken_flag_names_the_experience_removed(monkeypatch):
    monkeypatch.setattr(K, "CORP_EXP_PENALTY_MODE", "taken")
    u = _u()
    _cid_corp(u)
    assert mixed_loss(u, u.corporations["XYZ"]) == 200
    _mixed_penalty(u)
    assert u.players["P3"].experience == 1
    event = _penalty_for(u, "P3")
    assert event.payload == {"ticker": "XYZ", "loss": 29, "experience": 1}
    assert event.summary == "Cid lost 29 experience for a mixed corp"
    ann = _penalty_for(u, "P1")
    assert ann.payload["loss"] == 200
    assert ann.summary == "Ann lost 200 experience for a mixed corp"


def test_d22_1_legacy_hekate_message_is_the_formula():
    u = _u()
    _hekate_corp(u)
    assert mixed_loss(u, u.corporations["XYZ"]) == 582
    _mixed_penalty(u)
    assert u.players["P1"].experience == 1
    assert u.players["P2"].experience == 1
    assert u.players["P3"].experience == 7890 - 582
    hekate = _penalty_for(u, "P1")
    assert hekate.payload == {"ticker": "XYZ", "loss": 582, "experience": 1}
    assert hekate.summary == "Hekate lost 582 experience for a mixed corp"
    assert not any(e.kind == EventKind.CORP_EXP_PENALTY and e.actor_id == "P2" for e in u.events)


def test_d22_1_v311_names_the_taken_amount_and_uses_least_extreme(monkeypatch):
    """Evil -400 and good 800: least extreme is 100. Cid's 30 becomes 1, so the event says 29."""
    _profile(monkeypatch, "v311")
    assert K.corp_exp_penalty_taken() is True
    assert K.mixed_corp_exp_rule() == "least_extreme"
    assert K.MIXED_CORP_EXP_FLOOR == 1
    u = _u()
    _cid_corp(u)
    u.players["P2"].alignment = -400
    assert mixed_loss(u, u.corporations["XYZ"]) == 100
    _mixed_penalty(u)
    assert u.players["P3"].experience == 1
    assert u.players["P1"].experience == 4_900
    event = _penalty_for(u, "P3")
    assert event.payload == {"ticker": "XYZ", "loss": 29, "experience": 1}
    assert event.summary == "Cid lost 29 experience for a mixed corp"
    u2 = _u()
    _hekate_corp(u2)
    assert mixed_loss(u2, u2.corporations["XYZ"]) == 582
    _mixed_penalty(u2)
    assert u2.players["P1"].experience == 1
    hekate = _penalty_for(u2, "P1")
    assert hekate.payload["loss"] == 101
    assert hekate.summary == "Hekate lost 101 experience for a mixed corp"
    assert not any(e.kind == EventKind.CORP_EXP_PENALTY and e.actor_id == "P2" for e in u2.events)


def test_d22_2_legacy_keeps_the_reported_owner():
    assert K.CORP_LEAVER_DEPLOYMENTS == "legacy"
    assert K.corp_leaver_to_ceo() is False
    u = _u()
    _join_xyz(u)
    for pid in ("P1", "P2", "P3"):
        u.players[pid].alignment = 50
    corp_sid, personal_sid = _quiet_sectors(u, 2)
    u.sectors[corp_sid].fighters = FighterDeployment(
        owner_id="P2", count=300, mode=FighterMode.DEFENSIVE, corp_ticker="XYZ", toll_credits=40,
    )
    u.sectors[corp_sid].mines.append(
        MineDeployment(owner_id="P2", kind=MineType.ARMID, count=5, corp_ticker="XYZ"),
    )
    u.sectors[personal_sid].fighters = FighterDeployment(
        owner_id="P2", count=8, mode=FighterMode.DEFENSIVE,
    )
    u.limpets["P2:P3"] = LimpetTrack(
        owner_id="P2", target_id="P3", placed_sector=1, placed_day=u.day, corp_ticker="XYZ",
    )
    for _ in range(4):
        tick_day(u)
    assert u.sectors[corp_sid].fighters.owner_id == "P2"
    assert u.sectors[corp_sid].fighters.corp_ticker == "XYZ"
    assert u.sectors[corp_sid].fighters.count == 300
    assert _act(u, "P2", "corp_leave").ok
    assert u.players["P2"].corp_ticker is None
    assert "XYZ" in u.corporations
    fighters = u.sectors[corp_sid].fighters
    assert fighters.owner_id == "P2"
    assert fighters.corp_ticker == "XYZ"
    assert fighters.toll_credits == 40
    assert u.sectors[corp_sid].mines[0].owner_id == "P2"
    assert u.sectors[corp_sid].mines[0].corp_ticker == "XYZ"
    assert u.sectors[personal_sid].fighters.owner_id == "P2"
    assert u.sectors[personal_sid].fighters.corp_ticker is None
    assert u.limpets["P2:P3"].owner_id == "P2"
    leaver = _sector_detail(u, u.sectors[corp_sid], "P2")
    ceo = _sector_detail(u, u.sectors[corp_sid], "P1")
    assert leaver["fighter_group"]["owner_id"] == "P2"
    assert leaver["fighter_group"]["toll_credits"] == 40
    assert leaver["fighter_group"]["ownership"] == "corporate"
    assert ceo["fighter_group"]["owner_id"] == "P2"
    assert "toll_credits" not in ceo["fighter_group"]


@pytest.mark.parametrize("profile", ["legacy", "v311"])
def test_d22_2_to_ceo_moves_corporate_fighters_and_mines(monkeypatch, profile):
    _profile(monkeypatch, profile)
    monkeypatch.setattr(K, "CORP_LEAVER_DEPLOYMENTS", "to_ceo")
    u = _u()
    _join_xyz(u)
    for pid in ("P1", "P2", "P3"):
        u.players[pid].alignment = 50
    corp_sid, personal_sid = _quiet_sectors(u, 2)
    u.sectors[corp_sid].fighters = FighterDeployment(
        owner_id="P2", count=300, mode=FighterMode.DEFENSIVE, corp_ticker="XYZ", toll_credits=40,
    )
    u.sectors[corp_sid].mines.append(
        MineDeployment(owner_id="P2", kind=MineType.LIMPET, count=2, corp_ticker="XYZ"),
    )
    u.sectors[personal_sid].fighters = FighterDeployment(owner_id="P2", count=8, mode=FighterMode.OFFENSIVE)
    u.limpets["P2:P3"] = LimpetTrack(
        owner_id="P2", target_id="P3", placed_sector=1, placed_day=u.day, corp_ticker="XYZ",
    )
    for _ in range(4):
        tick_day(u)
    assert _act(u, "P2", "corp_leave").ok
    fighters = u.sectors[corp_sid].fighters
    assert fighters.owner_id == "P1"
    assert fighters.corp_ticker == "XYZ"
    assert fighters.count == 300
    assert fighters.toll_credits == 40
    assert u.sectors[corp_sid].mines[0].owner_id == "P1"
    assert u.sectors[corp_sid].mines[0].corp_ticker == "XYZ"
    assert u.sectors[personal_sid].fighters.owner_id == "P2"
    assert u.sectors[personal_sid].fighters.corp_ticker is None
    assert u.limpets["P2:P3"].owner_id == "P2"
    ceo = _sector_detail(u, u.sectors[corp_sid], "P1")
    leaver = _sector_detail(u, u.sectors[corp_sid], "P2")
    assert ceo["fighter_group"]["owner_id"] == "P1"
    assert ceo["fighter_group"]["toll_credits"] == 40
    assert ceo["fighter_group"]["ownership"] == "corporate"
    assert leaver["fighter_group"]["owner_id"] == "P1"
    assert "toll_credits" not in leaver["fighter_group"]


def test_d22_2_ceo_leave_still_rogues_off_sector_fighters(monkeypatch):
    monkeypatch.setattr(K, "CORP_LEAVER_DEPLOYMENTS", "to_ceo")
    u = _u()
    _join_xyz(u)
    away, home = _quiet_sectors(u, 2)
    _stand(u, "P1", home)
    u.sectors[away].fighters = FighterDeployment(
        owner_id="P1", count=200, mode=FighterMode.DEFENSIVE, corp_ticker="XYZ",
    )
    u.sectors[home].fighters = FighterDeployment(
        owner_id="P1", count=10, mode=FighterMode.DEFENSIVE, corp_ticker="XYZ",
    )
    assert _act(u, "P1", "corp_leave").ok
    assert "XYZ" not in u.corporations
    assert u.sectors[away].fighters.owner_id == "rogue"
    assert u.sectors[away].fighters.corp_ticker is None
    assert u.sectors[home].fighters.owner_id == "P1"
    assert u.sectors[home].fighters.corp_ticker is None


def test_d22_3_stored_defaults_stay_and_v311_selects_the_live_rules(monkeypatch):
    assert K.CORP_ALIGNMENT_RULE == "mixed"
    assert K.MIXED_CORP_EXP_RULE == "highest_good"
    assert K.MIXED_CORP_EXP_FLOOR == 1
    assert K.CORP_LEAVER_DEPLOYMENTS == "legacy"
    assert K.CORP_EXP_PENALTY_MODE == "legacy"
    assert K.corp_alignment_rule() == "mixed"
    assert K.mixed_corp_exp_rule() == "highest_good"
    assert K.corp_join_check() is False
    assert K.corp_leaver_to_ceo() is False
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.CORP_ALIGNMENT_RULE == "mixed"
    assert K.MIXED_CORP_EXP_RULE == "highest_good"
    assert K.MIXED_CORP_EXP_FLOOR == 1
    assert K.CORP_LEAVER_DEPLOYMENTS == "legacy"
    assert K.CORP_EXP_PENALTY_MODE == "legacy"
    assert K.corp_alignment_rule() == "join_check"
    assert K.corp_join_check() is True
    assert K.mixed_corp_exp_rule() == "least_extreme"
    assert K.mixed_corp_least_extreme() is True
    assert K.corp_leaver_to_ceo() is True
    assert K.corp_exp_penalty_taken() is True
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    assert K.corp_alignment_rule() == "mixed"
    assert K.mixed_corp_exp_rule() == "highest_good"
    assert K.corp_leaver_to_ceo() is False
    assert K.corp_exp_penalty_taken() is False


def test_d22_2_v311_moves_corporate_fighters_to_the_ceo(monkeypatch):
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.CORP_LEAVER_DEPLOYMENTS == "legacy"
    assert K.corp_leaver_to_ceo() is True
    u = _u()
    _join_xyz(u)
    for pid in ("P1", "P2", "P3"):
        u.players[pid].alignment = 50
    corp_sid, personal_sid = _quiet_sectors(u, 2)
    u.sectors[corp_sid].fighters = FighterDeployment(
        owner_id="P2", count=300, mode=FighterMode.DEFENSIVE, corp_ticker="XYZ", toll_credits=40,
    )
    u.sectors[corp_sid].mines.append(
        MineDeployment(owner_id="P2", kind=MineType.ARMID, count=5, corp_ticker="XYZ"),
    )
    u.sectors[personal_sid].fighters = FighterDeployment(owner_id="P2", count=8, mode=FighterMode.DEFENSIVE)
    for _ in range(4):
        tick_day(u)
    assert _act(u, "P2", "corp_leave").ok
    assert u.sectors[corp_sid].fighters.owner_id == "P1"
    assert u.sectors[corp_sid].fighters.corp_ticker == "XYZ"
    assert u.sectors[corp_sid].fighters.toll_credits == 40
    assert u.sectors[corp_sid].mines[0].owner_id == "P1"
    assert u.sectors[personal_sid].fighters.owner_id == "P2"
    assert u.sectors[personal_sid].fighters.corp_ticker is None
    ceo = _sector_detail(u, u.sectors[corp_sid], "P1")
    leaver = _sector_detail(u, u.sectors[corp_sid], "P2")
    assert ceo["fighter_group"]["toll_credits"] == 40
    assert "toll_credits" not in leaver["fighter_group"]


def _arm_join_check(monkeypatch, how: str) -> None:
    if how == "v311":
        monkeypatch.setattr(K, "V311_PROFILE", "v311")
    else:
        monkeypatch.setattr(K, "CORP_ALIGNMENT_RULE", "join_check")


@pytest.mark.parametrize("how", ["constant", "v311"])
def test_join_check_zero_may_join_and_opposite_signs_may_not(monkeypatch, how):
    _arm_join_check(monkeypatch, how)
    u = _u()
    assert _act(u, "P1", "corp_create", ticker="XYZ", name="Ex").ok
    assert _act(u, "P1", "corp_set_password", password="Zx9").ok
    u.players["P1"].alignment = -1
    u.players["P2"].alignment = 0
    assert _act(u, "P2", "corp_join", ticker="XYZ", password="Zx9").ok
    assert u.players["P2"].corp_ticker == "XYZ"
    u.players["P3"].alignment = 2
    refused = _act(u, "P3", "corp_join", ticker="XYZ", password="Zx9")
    assert refused.ok is False
    assert refused.error == "alignment does not match the C.E.O."
    assert u.players["P3"].corp_ticker is None
    listed = {la.kind: la for la in legal_actions(u, "P3")}
    assert "XYZ" not in listed["corp_join"].params["ticker"]["choices"]


@pytest.mark.parametrize("how", ["constant", "v311"])
def test_join_check_drift_stays_in_and_the_extern_penalty_still_runs(monkeypatch, how):
    _arm_join_check(monkeypatch, how)
    u = _u()
    assert _act(u, "P1", "corp_create", ticker="XYZ", name="Ex").ok
    assert _act(u, "P1", "corp_set_password", password="Zx9").ok
    u.players["P1"].alignment = -1
    u.players["P2"].alignment = -5
    assert _act(u, "P2", "corp_join", ticker="XYZ", password="Zx9").ok
    u.players["P1"].alignment = -400
    u.players["P1"].experience = 5_000
    u.players["P2"].alignment = 800
    u.players["P2"].experience = 5_000
    extern_corp_step(u)
    assert u.players["P2"].corp_ticker == "XYZ"
    assert "XYZ" in u.corporations
    assert not any(e.kind == EventKind.CORP_OUSTED for e in u.events)
    loss = 100 if how == "v311" else 200
    assert mixed_loss(u, u.corporations["XYZ"]) == loss
    assert u.players["P1"].experience == 5_000 - loss
    assert u.players["P2"].experience == 5_000 - loss


def test_class_m_flags_default_legacy_and_v311_turns_the_helpers_on(monkeypatch):
    assert K.CLASS_M_NW_MODE == "legacy"
    assert K.CLASS_M_DROP_MODE == "legacy"
    assert K.CLASS_M_GENESIS_MODE == "legacy"
    assert K.class_m_nw_units() is False
    assert K.class_m_drop_units() is False
    assert K.class_m_genesis_units() is False
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.CLASS_M_NW_MODE == "legacy"
    assert K.class_m_nw_units() is True
    assert K.class_m_drop_units() is True
    assert K.class_m_genesis_units() is True
    assert K.class_m_fidelity_live() is True


def test_class_m_net_worth_legacy_prices_each_person():
    planet = _valued_planet(PlanetClass.M, K.LIVE_STARTING_COLONISTS)
    each = K.LIVE_STARTING_COLONISTS * K.COLONIST_PRICE
    assert _planet_asset_value(planet) == each
    assert planet_tax_value(planet) == each
    u = _u()
    before = full_net_worth(u, u.players["P1"])
    grant_starting_planet(u, u.players["P1"])
    assert full_net_worth(u, u.players["P1"]) - before == each


@pytest.mark.parametrize("nw,fidelity", [("legacy", "live"), ("live", "legacy")])
def test_class_m_net_worth_needs_both_switches(monkeypatch, nw, fidelity):
    monkeypatch.setattr(K, "CLASS_M_NW_MODE", nw)
    monkeypatch.setattr(K, "CLASS_M_FIDELITY_MODE", fidelity)
    planet = _valued_planet(PlanetClass.M, K.LIVE_STARTING_COLONISTS)
    each = K.LIVE_STARTING_COLONISTS * K.COLONIST_PRICE
    assert _planet_asset_value(planet) == each
    assert planet_tax_value(planet) == each


def test_class_m_net_worth_live_prices_thousands_and_keeps_the_tax_basis(monkeypatch):
    monkeypatch.setattr(K, "CLASS_M_NW_MODE", "live")
    monkeypatch.setattr(K, "CLASS_M_FIDELITY_MODE", "live")
    planet = _valued_planet(PlanetClass.M, K.LIVE_STARTING_COLONISTS)
    thousands = (K.LIVE_STARTING_COLONISTS // K.CLASS_M_PEOPLE_PER_THOUSAND) * K.COLONIST_PRICE
    assert _planet_asset_value(planet) == thousands
    assert planet_tax_value(planet) == K.LIVE_STARTING_COLONISTS * K.COLONIST_PRICE
    other = _valued_planet(PlanetClass.L, K.LIVE_STARTING_COLONISTS)
    assert _planet_asset_value(other) == K.LIVE_STARTING_COLONISTS * K.COLONIST_PRICE


def test_class_m_net_worth_v311_leaves_the_free_start_out(monkeypatch):
    """NOTE 75. The free start is still 191,000 people, and the tax basis still prices each one. Net worth does not."""
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u = _u()
    player = u.players["P1"]
    before = full_net_worth(u, player)
    grant_starting_planet(u, player)
    home = next(pl for pl in u.planets.values() if pl.owner_id == "P1")
    assert home.class_id == PlanetClass.M
    assert sum(home.colonists.values()) == K.LIVE_STARTING_COLONISTS
    assert full_net_worth(u, player) - before == 0
    assert planet_tax_value(home) == K.LIVE_STARTING_COLONISTS * K.COLONIST_PRICE
    other = _valued_planet(PlanetClass.L, 4_000)
    assert _planet_asset_value(other) == 4_000 * K.COLONIST_PRICE


def _load_max(u) -> int:
    listed = {la.kind: la for la in legal_actions(u, "P1")}
    return int(listed["load_planet_cargo"].params["qty"]["max_by"]["colonists"])


def _dump_max(u) -> int:
    listed = {la.kind: la for la in legal_actions(u, "P1")}
    return int(listed["dump_planet_cargo"].params["qty"]["max_by"]["colonists"])


def test_class_m_drops_legacy_are_one_to_one():
    u = _u()
    planet = _land_world(u)
    planet.colonists[Commodity.FUEL_ORE] = 1_000
    u.players["P1"].ship.cargo[Commodity.COLONISTS] = 5
    assert _load_max(u) == u.players["P1"].ship.cargo_free
    assert _act(u, "P1", "dump_planet_cargo", planet_id=planet.id, commodity="colonists", qty=5, pool="fuel_ore").ok
    assert planet.colonists[Commodity.FUEL_ORE] == 1_005
    assert u.players["P1"].ship.cargo[Commodity.COLONISTS] == 0
    refused = _act(u, "P1", "load_planet_cargo", planet_id=planet.id, commodity="colonists", qty=1_000, pool="fuel_ore")
    assert refused.ok is False and refused.error == "not enough cargo holds"
    assert planet.colonists[Commodity.FUEL_ORE] == 1_005
    assert _act(u, "P1", "load_planet_cargo", planet_id=planet.id, commodity="colonists", qty=5, pool="fuel_ore").ok
    assert planet.colonists[Commodity.FUEL_ORE] == 1_000
    assert u.players["P1"].ship.cargo[Commodity.COLONISTS] == 5


def test_class_m_drops_scale_a_legacy_terra_hold(monkeypatch):
    monkeypatch.setattr(K, "CLASS_M_DROP_MODE", "live")
    monkeypatch.setattr(K, "CLASS_M_FIDELITY_MODE", "live")
    assert K.colonists_per_hold() == 1
    u = _u()
    planet = _land_world(u)
    player = u.players["P1"]
    player.ship.cargo[Commodity.COLONISTS] = 5
    assert _act(u, "P1", "dump_planet_cargo", planet_id=planet.id, commodity="colonists", qty=5, pool="fuel_ore").ok
    assert planet.colonists[Commodity.FUEL_ORE] == 5_000
    assert player.ship.cargo[Commodity.COLONISTS] == 0
    partial = _act(u, "P1", "load_planet_cargo", planet_id=planet.id, commodity="colonists", qty=1_500, pool="fuel_ore")
    assert partial.ok is False and partial.error == "class M colonists move by the thousand"
    assert planet.colonists[Commodity.FUEL_ORE] == 5_000
    assert _load_max(u) == 5_000
    assert _act(u, "P1", "load_planet_cargo", planet_id=planet.id, commodity="colonists", qty=1_000, pool="fuel_ore").ok
    assert planet.colonists[Commodity.FUEL_ORE] == 4_000
    assert player.ship.cargo[Commodity.COLONISTS] == 1
    assert player.ship.cargo_used == 1
    player.ship.cargo[Commodity.COLONISTS] = 2
    assert _act(
        u, "P1", "assign_colonists", planet_id=planet.id, **{"from": "ship", "to": "organics", "qty": 2},
    ).ok
    assert planet.colonists[Commodity.ORGANICS] == 2_000
    assert player.ship.cargo[Commodity.COLONISTS] == 0
    back = _act(
        u, "P1", "assign_colonists", planet_id=planet.id, **{"from": "organics", "to": "ship", "qty": 2_000},
    )
    assert back.ok, back.error
    assert planet.colonists[Commodity.ORGANICS] == 0
    assert player.ship.cargo[Commodity.COLONISTS] == 2


def test_class_m_drop_room_is_quoted_in_cargo_units(monkeypatch):
    monkeypatch.setattr(K, "CLASS_M_DROP_MODE", "live")
    monkeypatch.setattr(K, "CLASS_M_FIDELITY_MODE", "live")
    u = _u()
    planet = _land_world(u)
    cap = K.CLASS_M_CATEGORY_CAP
    planet.colonists[Commodity.FUEL_ORE] = cap - 2_500
    planet.colonists[Commodity.ORGANICS] = cap
    planet.colonists[Commodity.EQUIPMENT] = cap
    planet.colonists[Commodity.COLONISTS] = cap
    u.players["P1"].ship.cargo[Commodity.COLONISTS] = 10
    assert _dump_max(u) == 2
    assert _act(u, "P1", "dump_planet_cargo", planet_id=planet.id, commodity="colonists", qty=2, pool="fuel_ore").ok
    assert planet.colonists[Commodity.FUEL_ORE] == cap - 500
    over = _act(u, "P1", "dump_planet_cargo", planet_id=planet.id, commodity="colonists", qty=1, pool="fuel_ore")
    assert over.ok is False and "cap" in (over.error or "")


def test_class_m_drops_v311_keep_terra_people(monkeypatch):
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.colonists_per_hold() == K.CLASS_M_PEOPLE_PER_THOUSAND
    u = _u()
    planet = _land_world(u)
    player = u.players["P1"]
    player.ship.cargo[Commodity.COLONISTS] = 2_000
    assert player.ship.cargo_used == 2
    assert _act(u, "P1", "dump_planet_cargo", planet_id=planet.id, commodity="colonists", qty=2_000, pool="fuel_ore").ok
    assert planet.colonists[Commodity.FUEL_ORE] == 2_000
    assert player.ship.cargo[Commodity.COLONISTS] == 0
    assert _load_max(u) == 2_000
    assert _act(u, "P1", "load_planet_cargo", planet_id=planet.id, commodity="colonists", qty=2_000, pool="fuel_ore").ok
    assert planet.colonists[Commodity.FUEL_ORE] == 0
    assert player.ship.cargo[Commodity.COLONISTS] == 2_000
    assert player.ship.cargo_used == 2


def test_class_m_other_classes_stay_one_to_one(monkeypatch):
    monkeypatch.setattr(K, "CLASS_M_DROP_MODE", "live")
    monkeypatch.setattr(K, "CLASS_M_FIDELITY_MODE", "live")
    u = _u()
    planet = _land_world(u, PlanetClass.L)
    u.players["P1"].ship.cargo[Commodity.COLONISTS] = 5
    assert _act(u, "P1", "dump_planet_cargo", planet_id=planet.id, commodity="colonists", qty=5, pool="fuel_ore").ok
    assert planet.colonists[Commodity.FUEL_ORE] == 5
    assert _load_max(u) == 5


def _genesis(u, weights: dict[str, float]):
    sid = _deep_sector(u)
    _stand(u, "P1", sid)
    u.players["P1"].ship.genesis = 1
    res = _act(u, "P1", "deploy_genesis")
    assert res.ok, res.error
    planet = next(pl for pl in u.planets.values() if pl.owner_id == "P1" and pl.origin == "genesis")
    assert planet.class_id.value in weights
    return planet


def test_class_m_genesis_seed_legacy_is_handbook_units(monkeypatch):
    monkeypatch.setattr(K, "PLANET_CLASS_WEIGHTS", {"M": 1.0})
    u = _u()
    planet = _genesis(u, {"M": 1.0})
    assert sum(planet.colonists.values()) == K.GENESIS_SEED_COLONISTS


def test_class_m_genesis_seed_scales_only_class_m(monkeypatch):
    monkeypatch.setattr(K, "CLASS_M_GENESIS_MODE", "live")
    monkeypatch.setattr(K, "CLASS_M_FIDELITY_MODE", "live")
    monkeypatch.setattr(K, "PLANET_CLASS_WEIGHTS", {"M": 1.0})
    u = _u()
    planet = _genesis(u, {"M": 1.0})
    assert sum(planet.colonists.values()) == K.GENESIS_SEED_COLONISTS * K.CLASS_M_PEOPLE_PER_THOUSAND
    assert planet.colonists[Commodity.COLONISTS] == 0
    monkeypatch.setattr(K, "PLANET_CLASS_WEIGHTS", {"L": 1.0})
    u2 = _u()
    other = _genesis(u2, {"L": 1.0})
    assert other.class_id == PlanetClass.L
    assert sum(other.colonists.values()) == K.GENESIS_SEED_COLONISTS


def test_class_m_genesis_v311_starts_empty(monkeypatch):
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    monkeypatch.setattr(K, "PLANET_CLASS_WEIGHTS", {"M": 1.0})
    assert K.class_m_genesis_units() is True
    assert K.genesis_start_live() is True
    u = _u()
    planet = _genesis(u, {"M": 1.0})
    assert planet.class_id == PlanetClass.M
    assert sum(planet.colonists.values()) == 0
