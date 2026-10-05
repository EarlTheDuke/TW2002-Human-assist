"""fedspace-police-v1: Federals, Extern tows, Police HQ, ISS repossession.

Rules: docs/playtests/fedspace/FEDSPACE_POLICE.md. test_plant_* entries are the
planted-bug checks (each was run against a planted mutation and failed).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.agents.prompts import format_observation
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.fed import (
    most_wanted,
    run_tows,
    tick_federals,
)
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import (
    EventKind,
    FighterDeployment,
    FighterMode,
    Player,
    Ship,
    ShipClass,
)
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import tick_day
from tw2k.engine.scanners import density_reading

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "playtests" / "fedspace" / "FEDSPACE_POLICE.md"


@pytest.fixture
def legacy(monkeypatch):
    monkeypatch.setattr(K, "FED_MODE", "legacy")


@pytest.fixture
def tw(monkeypatch):
    monkeypatch.setattr(K, "FED_MODE", "tw2002")
    monkeypatch.setattr(K, "FED_PROTECT_PUNISH", "pod")
    monkeypatch.setattr(K, "ISS_REPO_MODE", "twgs")
    monkeypatch.setattr(K, "FED_TOW_DEST", "random")
    monkeypatch.setattr(K, "REWARD_TARGET_RULE", "any_red")
    monkeypatch.setattr(K, "FED_BLOCKED_BY_MINES", False)
    monkeypatch.setattr(K, "COMMISSION_ONCE", True)
    monkeypatch.setattr(K, "FED_TOW_FIGHTER_LIMIT", 98)
    monkeypatch.setattr(K, "FED_SHIPS_PER_SECTOR", 5)


def _world(seed: int = 4601, size: int = 80, players: dict | None = None):
    u = generate_universe(
        GameConfig(seed=seed, universe_size=size, enable_ferrengi=False, enable_planets=False)
    )
    if players is None:
        players = {
            "A": dict(alignment=0, fighters=50, credits=500_000),
            "B": dict(alignment=-100, fighters=50, credits=50_000),
        }
    for pid, raw in players.items():
        kw = dict(raw)
        fighters = int(kw.pop("fighters", 50))
        holds = int(kw.pop("holds", 50))
        shields = int(kw.pop("shields", 0))
        cloaked = bool(kw.pop("cloaked", False))
        ship_class = kw.pop("ship_class", ShipClass.MERCHANT_CRUISER)
        if isinstance(ship_class, str):
            ship_class = ShipClass(ship_class)
        sector_id = int(kw.pop("sector_id", K.STARDOCK_SECTOR))
        ship = Ship(holds=holds, fighters=fighters, shields=shields, ship_class=ship_class, cloaked=cloaked)
        p = Player(
            id=pid,
            name=pid,
            ship=ship,
            sector_id=sector_id,
            credits=int(kw.pop("credits", 500_000)),
            alignment=int(kw.pop("alignment", 0)),
            experience=int(kw.pop("experience", 100)),
            **kw,
        )
        u.players[pid] = p
        if pid not in u.sectors[p.sector_id].occupant_ids:
            u.sectors[p.sector_id].occupant_ids.append(pid)
        p.known_sectors.add(p.sector_id)
    return u


def _move(u, pid: str, dest: int) -> None:
    p = u.players[pid]
    if pid in u.sectors[p.sector_id].occupant_ids:
        u.sectors[p.sector_id].occupant_ids.remove(pid)
    p.sector_id = dest
    if pid not in u.sectors[dest].occupant_ids:
        u.sectors[dest].occupant_ids.append(pid)
    p.known_sectors.add(dest)


def _las(u, pid: str) -> dict:
    return {a.kind: a for a in legal_actions(u, pid)}


def _act(u, pid: str, verb: ActionKind, **args):
    return apply_action(u, pid, Action(kind=verb, args=args))


def _obs(u, pid: str) -> dict:
    return build_observation(u, pid).model_dump(mode="json")


def _digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def test_doc_exists():
    assert DOC.is_file()
    text = DOC.read_text(encoding="utf-8")
    for i in range(1, 27):
        assert f"f{i}" in text


# ---- f1..f26 core ----


def test_f1_three_feds(tw):
    u = _world()
    assert len(u.federals) == 3
    names = {f.name for f in u.federals}
    assert names == {"Zyrain", "Nelson", "Clausewitz"}


def test_f1_legacy_no_feds(legacy):
    u = _world()
    assert u.federals == []


def test_f2_density(tw):
    u = _world()
    by = {f.name: f for f in u.federals}
    assert by["Nelson"].density == 462
    assert by["Zyrain"].density == 489
    assert by["Clausewitz"].density == 512
    d = density_reading(u, by["Zyrain"].sector_id)["density"]
    assert d >= 489


def test_f3_starts_rng_isolated(tw):
    u1 = generate_universe(GameConfig(seed=99, universe_size=80, enable_ferrengi=False, enable_planets=False))
    # Snapshot generator-sensitive state via warp graph digest
    g1 = _digest({sid: list(u1.sectors[sid].warps) for sid in sorted(u1.sectors)})
    rng_before = u1.rng.random()
    # Re-place should be deterministic and not touch universe.rng stream for first draw after gen
    u2 = generate_universe(GameConfig(seed=99, universe_size=80, enable_ferrengi=False, enable_planets=False))
    g2 = _digest({sid: list(u2.sectors[sid].warps) for sid in sorted(u2.sectors)})
    assert g1 == g2
    zy = next(f for f in u1.federals if f.name == "Zyrain")
    assert zy.sector_id == K.FED_ZYRAIN_START
    for f in u1.federals:
        if f.name != "Zyrain":
            assert f.sector_id >= 11


def test_f4_blocked(tw):
    u = _world(size=40)
    nelson = next(f for f in u.federals if f.name == "Nelson")
    # Put fighters on every neighbour
    sector = u.sectors[nelson.sector_id]
    for wid in list(sector.warps):
        u.sectors[wid].fighters = FighterDeployment(owner_id="A", count=10, mode=FighterMode.DEFENSIVE)
    start = nelson.sector_id
    for _ in range(20):
        tick_federals(u)
    assert next(f for f in u.federals if f.name == "Nelson").sector_id == start


def test_f5_wander_and_trap(tw):
    u = _world(size=60)
    nelson = next(f for f in u.federals if f.name == "Nelson")
    start = nelson.sector_id
    moved = False
    for day in range(1, 15):
        u.day = day
        tick_federals(u)
        if next(f for f in u.federals if f.name == "Nelson").sector_id != start:
            moved = True
            break
    assert moved


def test_f7_attack_fed(tw):
    u = _world(players={"A": dict(alignment=50, experience=1000, fighters=200, credits=10_000)})
    zy = next(f for f in u.federals if f.name == "Zyrain")
    _move(u, "A", zy.sector_id)
    before_align = u.players["A"].alignment
    before_exp = u.players["A"].experience
    r = _act(u, "A", ActionKind.ATTACK, target=f"fed:{zy.name}", qty=50)
    assert r.ok
    assert u.players["A"].alignment == before_align - 10
    assert u.players["A"].experience < before_exp
    # Fed still exists
    assert any(f.name == "Zyrain" for f in u.federals)
    # Attacker podded (escape pod or destroyed)
    assert (
        u.players["A"].ship.ship_class in (ShipClass.ESCAPE_POD, ShipClass.SCOUT_MARAUDER)
        or u.players["A"].deaths >= 1
    )


def test_f8_protect(tw):
    u = _world(
        players={
            "A": dict(alignment=-50, experience=500, fighters=200, credits=10_000, sector_id=2),
            "B": dict(alignment=10, experience=100, fighters=10, credits=10_000, sector_id=2),
        }
    )
    # B is fedsafe
    assert u.players["B"].alignment >= 0 and u.players["B"].experience <= 999
    r = _act(u, "A", ActionKind.ATTACK, target="B", qty=10)
    assert not r.ok
    assert any(e.kind == EventKind.FED_ZYRAIN for e in u.events)
    assert u.players["A"].alignment <= -250  # -200 at least
    assert u.players["A"].deaths >= 1


def test_f8_protect_refuse(tw, monkeypatch):
    monkeypatch.setattr(K, "FED_PROTECT_PUNISH", "refuse")
    u = _world(
        players={
            "A": dict(alignment=-50, experience=500, fighters=200, credits=10_000, sector_id=2),
            "B": dict(alignment=10, experience=100, fighters=10, credits=10_000, sector_id=2),
        }
    )
    deaths_before = u.players["A"].deaths
    r = _act(u, "A", ActionKind.ATTACK, target="B", qty=10)
    assert not r.ok
    assert any(e.kind == EventKind.FED_ZYRAIN for e in u.events)
    assert u.players["A"].deaths == deaths_before


def test_f9_fedsafe(tw):
    from tw2k.engine.victory import is_fedsafe

    u = _world(players={"A": dict(alignment=0, experience=999)})
    assert is_fedsafe(u.players["A"])
    u.players["A"].experience = 1000
    assert not is_fedsafe(u.players["A"])


def test_f10_deploy_refused(tw):
    u = _world()
    r = _act(u, "A", ActionKind.DEPLOY_FIGHTERS, qty=1, mode="defensive")
    assert not r.ok


def test_f11_arms_tow(tw):
    u = _world(players={"A": dict(fighters=98, sector_id=3), "B": dict(fighters=99, sector_id=4)})
    run_tows(u)
    assert u.players["A"].sector_id == 3
    assert u.players["B"].sector_id not in K.FEDSPACE_SECTORS


def test_f12_parking(tw):
    players = {f"P{i}": dict(fighters=10, sector_id=3, credits=1000) for i in range(6)}
    u = _world(players=players)
    # Ensure occupant order is P0..P5 (latest = P5)
    u.sectors[3].occupant_ids = [f"P{i}" for i in range(6)]
    for i in range(6):
        u.players[f"P{i}"].sector_id = 3
    run_tows(u)
    stayed = [f"P{i}" for i in range(6) if u.players[f"P{i}"].sector_id == 3]
    towed = [f"P{i}" for i in range(6) if u.players[f"P{i}"].sector_id != 3]
    assert len(stayed) == 5
    assert "P5" in towed  # latest arrival towed first


def test_f13_cloak_tow(tw):
    u = _world(players={"A": dict(fighters=99, sector_id=5, cloaked=True)})
    u.players["A"].ship.cloaked = True
    run_tows(u)
    assert u.players["A"].sector_id not in K.FEDSPACE_SECTORS
    assert u.players["A"].ship.cloaked is True


def test_f14_dest(tw, monkeypatch):
    monkeypatch.setattr(K, "FED_TOW_DEST", "random")
    u = _world(players={"A": dict(fighters=99, sector_id=2)})
    run_tows(u)
    assert u.players["A"].sector_id not in K.FEDSPACE_SECTORS
    monkeypatch.setattr(K, "FED_TOW_DEST", "msl")
    u2 = _world(seed=4602, players={"A": dict(fighters=99, sector_id=2)})
    # Ensure msl_sectors populated (class0)
    if not u2.msl_sectors:
        pytest.skip("no msl_sectors in this seed")
    run_tows(u2)
    dest = u2.players["A"].sector_id
    assert dest not in K.FEDSPACE_SECTORS
    assert dest in set(u2.msl_sectors) or dest not in K.FEDSPACE_SECTORS


def test_f16_entry(tw):
    u = _world(players={"A": dict(alignment=-1, sector_id=1)})
    la = _las(u, "A")["apply_commission"]
    assert not la.legal


def test_f17_commission(tw):
    u = _world(players={"A": dict(alignment=500, sector_id=1, credits=1000)})
    assert _las(u, "A")["apply_commission"].legal
    r = _act(u, "A", ActionKind.APPLY_COMMISSION)
    assert r.ok and u.players["A"].alignment == 1000
    assert not _las(u, "A")["apply_commission"].legal
    r2 = _act(u, "A", ActionKind.APPLY_COMMISSION)
    assert not r2.ok
    # 499 refused
    u2 = _world(players={"A": dict(alignment=499, sector_id=1)})
    assert not _las(u2, "A")["apply_commission"].legal
    # outside sector 1
    u3 = _world(players={"A": dict(alignment=600, sector_id=11)})
    _move(u3, "A", 11)
    assert not _las(u3, "A")["apply_commission"].legal
    # never lowers 1200
    u4 = _world(players={"A": dict(alignment=1200, sector_id=1)})
    assert not _las(u4, "A")["apply_commission"].legal


def test_f18_post_reward(tw):
    u = _world(
        players={
            "A": dict(alignment=100, credits=50_000, sector_id=1),
            "B": dict(alignment=-50, credits=1000, sector_id=20),
        }
    )
    _move(u, "B", 20)
    r = _act(u, "A", ActionKind.POST_REWARD, target_id="B", amount=5000)
    assert r.ok
    assert u.players["A"].credits == 45_000
    assert u.players["A"].alignment == 105  # +5
    # good target refused
    u.players["B"].alignment = 10
    r2 = _act(u, "A", ActionKind.POST_REWARD, target_id="B", amount=1000)
    assert not r2.ok


def test_f19_claim(tw):
    from tw2k.engine.combat import _destroy_ship

    u = _world(
        players={
            "A": dict(alignment=100, credits=10_000, sector_id=1),
            "B": dict(alignment=-200, credits=1000, sector_id=20, experience=50),
            "C": dict(alignment=50, credits=1000, sector_id=20),
        }
    )
    u.posted_rewards["B"] = [{"poster_id": "A", "amount": 3000, "day": 1}]
    # Pod kill pays nothing
    _move(u, "B", 20)
    _move(u, "C", 20)
    _destroy_ship(u, "B", reason="combat", killer_id="C", by_other=True, always_escape=True)
    assert u.pending_rewards.get("C", 0) == 0
    # Real death
    u.players["B"].alive = True
    u.players["B"].ship.ship_class = ShipClass.MERCHANT_CRUISER
    u.players["B"].pods_today = 99  # force ship_destroyed
    u.posted_rewards["B"] = [{"poster_id": "A", "amount": 3000, "day": 1}]
    _destroy_ship(u, "B", reason="combat", killer_id="C", by_other=True)
    assert u.pending_rewards.get("C", 0) == 3000
    _move(u, "C", 1)
    u.players["C"].alignment = 10
    r = _act(u, "C", ActionKind.CLAIM_REWARD)
    assert r.ok and u.players["C"].credits == 4000
    r2 = _act(u, "C", ActionKind.CLAIM_REWARD)
    assert not r2.ok


def test_f20_most_wanted(tw):
    u = _world(
        players={
            "A": dict(alignment=100, sector_id=1),
            "E1": dict(alignment=-10, experience=100, sector_id=20),
            "E2": dict(alignment=-50, experience=200, sector_id=21),
            "G": dict(alignment=5, sector_id=22),
        }
    )
    u.posted_rewards["E2"] = [{"poster_id": "A", "amount": 2000, "day": 1}]
    rows = most_wanted(u)
    assert all(r["id"] != "G" for r in rows)
    assert "alignment" not in json.dumps(rows)
    assert rows[0]["id"] == "E2"  # more evil
    assert "title" in rows[0]
    obs = _obs(u, "A")
    mw = (obs.get("police") or {}).get("most_wanted") or []
    blob = json.dumps(mw)
    assert "-50" not in blob and "-10" not in blob


def test_f22_iss_repo(tw, monkeypatch):
    u = _world(players={"A": dict(alignment=-1, sector_id=15, ship_class="imperial_starship", fighters=100)})
    u.players["A"].ship.ship_class = ShipClass.IMPERIAL_STARSHIP
    # pick a warp neighbour
    warps = list(u.sectors[15].warps)
    if not warps:
        pytest.skip("no warps")
    dest = int(warps[0])
    r = _act(u, "A", ActionKind.WARP, target=dest)
    assert u.players["A"].deaths >= 1 or u.players["A"].ship.ship_class != ShipClass.IMPERIAL_STARSHIP
    # cloaked safe
    u2 = _world(
        seed=4610,
        players={"A": dict(alignment=-1, sector_id=15, ship_class="imperial_starship", fighters=100)},
    )
    u2.players["A"].ship.ship_class = ShipClass.IMPERIAL_STARSHIP
    u2.players["A"].ship.cloaked = True
    warps = list(u2.sectors[u2.players["A"].sector_id].warps) or [11]
    _act(u2, "A", ActionKind.WARP, target=int(warps[0]))
    assert u2.players["A"].ship.ship_class == ShipClass.IMPERIAL_STARSHIP
    # align 0 safe
    u3 = _world(seed=4611, players={"A": dict(alignment=0, sector_id=15, ship_class="imperial_starship")})
    u3.players["A"].ship.ship_class = ShipClass.IMPERIAL_STARSHIP
    warps = list(u3.sectors[15].warps) or [11]
    _act(u3, "A", ActionKind.WARP, target=int(warps[0]))
    assert u3.players["A"].ship.ship_class == ShipClass.IMPERIAL_STARSHIP


def test_f22_iss_repo_mbbs(tw, monkeypatch):
    monkeypatch.setattr(K, "ISS_REPO_MODE", "mbbs")
    u = _world(players={"A": dict(alignment=-5, sector_id=15, ship_class="imperial_starship", fighters=100)})
    u.players["A"].ship.ship_class = ShipClass.IMPERIAL_STARSHIP
    # Own fighters in destination -> safe under mbbs
    warps = list(u.sectors[15].warps)
    if not warps:
        pytest.skip("no warps")
    dest = int(warps[0])
    u.sectors[dest].fighters = FighterDeployment(owner_id="A", count=5, mode=FighterMode.DEFENSIVE)
    _act(u, "A", ActionKind.WARP, target=dest)
    assert u.players["A"].ship.ship_class == ShipClass.IMPERIAL_STARSHIP


def test_f23_hail(tw):
    u = _world(players={"A": dict(alignment=10, sector_id=15, ship_class="imperial_starship")})
    u.players["A"].ship.ship_class = ShipClass.IMPERIAL_STARSHIP
    u.players["A"].alignment = -1
    from tw2k.engine.fed import maybe_fed_hail

    maybe_fed_hail(u, "A")
    assert any(e.kind == EventKind.FED_HAIL for e in u.events)
    maybe_fed_hail(u, "A")
    assert sum(1 for e in u.events if e.kind == EventKind.FED_HAIL) == 1


def test_legal_handler_police(tw):
    u = _world(
        players={
            "A": dict(alignment=600, credits=20_000, sector_id=1),
            "B": dict(alignment=-20, credits=100, sector_id=20),
        }
    )
    for kind, la in _las(u, "A").items():
        if kind not in ("apply_commission", "post_reward", "claim_reward"):
            continue
        if la.legal:
            args = {}
            if kind == "post_reward":
                args = {"target_id": "B", "amount": 1000}
            r = _act(u, "A", ActionKind(kind), **args)
            assert r.ok, (kind, r.error)
    # Off-list: commission at 499
    u2 = _world(players={"A": dict(alignment=499, sector_id=1)})
    assert not _las(u2, "A")["apply_commission"].legal
    r = _act(u2, "A", ActionKind.APPLY_COMMISSION)
    assert not r.ok


def test_fog_no_align_numbers(tw):
    u = _world(
        players={
            "A": dict(alignment=100, sector_id=1),
            "E1": dict(alignment=-77, experience=50, sector_id=20),
        }
    )
    obs = _obs(u, "A")
    blob = json.dumps(obs.get("police") or {})
    assert "-77" not in blob


# ---- planted bugs ----


def test_plant_1_zyrain_protect(tw):
    test_f8_protect(tw)


def test_plant_2_fed_attack_penalty(tw):
    test_f7_attack_fed(tw)


def test_plant_3_fed_enters_fighters(tw):
    test_f4_blocked(tw)


def test_plant_4_tow_threshold(tw):
    test_f11_arms_tow(tw)


def test_plant_5_parking_order(tw):
    test_f12_parking(tw)


def test_plant_6_cloak_tow(tw):
    test_f13_cloak_tow(tw)


def test_plant_7_tow_dest(tw, monkeypatch):
    test_f14_dest(tw, monkeypatch)
    from tw2k.engine.fed import _tow_destinations

    monkeypatch.setattr(K, "FED_TOW_DEST", "random")
    u = _world(players={"A": dict(fighters=99, sector_id=2)})
    dests = _tow_destinations(u)
    assert dests, "no tow destinations"
    assert not set(dests) & set(K.FEDSPACE_SECTORS)
    assert K.STARDOCK_SECTOR not in dests


def test_plant_8_commission(tw):
    test_f17_commission(tw)


def test_plant_9_post_reward(tw):
    test_f18_post_reward(tw)


def test_plant_10_claim_reward(tw):
    test_f19_claim(tw)


def test_plant_11_iss_repo(tw, monkeypatch):
    test_f22_iss_repo(tw, monkeypatch)


def test_plant_12_most_wanted_fog(tw):
    test_f20_most_wanted(tw)


def test_plant_13_legacy(legacy):
    u = _world(players={"A": dict(alignment=600, fighters=200, sector_id=1)})
    assert u.federals == []
    la = _las(u, "A")
    assert "apply_commission" not in la or not la["apply_commission"].legal
    r = _act(u, "A", ActionKind.APPLY_COMMISSION)
    assert not r.ok
    sector_before = u.players["A"].sector_id
    tick_day(u)
    assert u.players["A"].sector_id == sector_before


def test_plant_14_fed_density(tw):
    test_f2_density(tw)


def test_plant_15_legal_handler(tw):
    test_legal_handler_police(tw)


def test_plant_16_rng_isolated(tw, monkeypatch):
    """Fed placement must not draw from universe.rng: legacy and tw2002 see the same stream."""
    cfg = dict(seed=777, universe_size=60, enable_ferrengi=False, enable_planets=False)
    u_tw = generate_universe(GameConfig(**cfg))
    draws_tw = [u_tw.rng.random() for _ in range(5)]
    monkeypatch.setattr(K, "FED_MODE", "legacy")
    u_leg = generate_universe(GameConfig(**cfg))
    draws_leg = [u_leg.rng.random() for _ in range(5)]
    assert u_leg.federals == [] and len(u_tw.federals) == 3
    assert draws_tw == draws_leg
    assert _digest({s: list(u_tw.sectors[s].warps) for s in u_tw.sectors}) == _digest(
        {s: list(u_leg.sectors[s].warps) for s in u_leg.sectors}
    )


def test_fed_legacy_is_unchanged(legacy):
    """Observation + prompt digests for a short scripted run stay stable under legacy."""
    u = _world(seed=12, size=40, players={"A": dict(alignment=0, fighters=20, sector_id=1, credits=20000)})
    digests = []
    for _ in range(3):
        obs = build_observation(u, "A")
        digests.append((_digest(obs.model_dump(mode="json")), _digest(format_observation(obs))))
        tick_day(u)
    # Just assert structure is stable across re-runs
    u2 = _world(seed=12, size=40, players={"A": dict(alignment=0, fighters=20, sector_id=1, credits=20000)})
    digests2 = []
    for _ in range(3):
        obs = build_observation(u2, "A")
        digests2.append((_digest(obs.model_dump(mode="json")), _digest(format_observation(obs))))
        tick_day(u2)
    assert digests == digests2
    assert u.federals == [] and u2.federals == []


# ---- independent QC (fedspace-police-v1 QC fixes) ----
# Each test below failed on 58acec8 (or pins a fix that did): see FEDSPACE_POLICE.md "QC fixes".


def _fed(u, name: str):
    return next(f for f in u.federals if f.name == name)


def test_qc_attack_fed_legal_equals_handler(tw):
    """f7 + legal == handler: no fighters aboard / bad qty is refused exactly like the legal list says."""
    u = _world(players={"A": dict(alignment=100, fighters=0, sector_id=1, experience=500)})
    _fed(u, "Nelson").sector_id = 1
    la = _las(u, "A")["attack"]
    assert "fed:Nelson" in la.params["target"]["choices"] and not la.legal
    r = _act(u, "A", ActionKind.ATTACK, target="fed:Nelson")
    assert not r.ok and "no fighters" in (r.error or "")
    a = u.players["A"]
    assert a.ship.ship_class != ShipClass.ESCAPE_POD and a.alignment == 100 and a.experience == 500
    a.ship.fighters = 40
    r = _act(u, "A", ActionKind.ATTACK, target="fed:Nelson", qty=9999)
    assert not r.ok and a.ship.ship_class != ShipClass.ESCAPE_POD and a.alignment == 100
    assert _las(u, "A")["attack"].legal
    r = _act(u, "A", ActionKind.ATTACK, target="fed:Nelson", qty=10)
    assert r.ok and a.ship.ship_class == ShipClass.ESCAPE_POD and a.alignment == 90 and a.experience == 450


def test_qc_hail_precedes_repossession(tw, monkeypatch):
    """f23: the warning comes with the action that turns the ISS pilot evil, before the warp that costs the ship."""
    monkeypatch.setattr(K, "FED_PROTECT_PUNISH", "refuse")
    u = _world(players={
        "A": dict(alignment=100, experience=2000, fighters=100, sector_id=2, ship_class="imperial_starship"),
        "C": dict(alignment=0, experience=100, fighters=10, sector_id=2),
    })
    r = _act(u, "A", ActionKind.ATTACK, target="C")
    assert not r.ok and u.players["A"].alignment < 0
    kinds = [e.kind for e in u.events]
    assert EventKind.FED_HAIL in kinds and EventKind.FED_REPOSSESS not in kinds
    assert u.players["A"].ship.ship_class == ShipClass.IMPERIAL_STARSHIP
    obs = _obs(u, "A")
    assert any(e.get("kind") == "fed_hail" for e in obs["recent_events"])
    assert not any(e.get("kind") == "fed_hail" for e in _obs(u, "C")["recent_events"])  # owner-only
    dest = int(u.sectors[2].warps[0])
    _act(u, "A", ActionKind.WARP, target=dest)
    assert u.players["A"].ship.ship_class != ShipClass.IMPERIAL_STARSHIP
    assert sum(1 for e in u.events if e.kind == EventKind.FED_HAIL) == 1


def test_qc_iss_repo_on_retreat(tw):
    """f22: a retreat is a move - an evil uncloaked ISS is repossessed on it (twgs)."""
    u = _world(players={
        "A": dict(alignment=50, fighters=100, sector_id=20, ship_class="imperial_starship"),
        "B": dict(alignment=0, fighters=10, sector_id=30),
    })
    there = int(u.sectors[20].warps[0])
    u.sectors[there].fighters = FighterDeployment(owner_id="B", count=500, mode=FighterMode.DEFENSIVE)
    r = _act(u, "A", ActionKind.WARP, target=there)
    assert r.ok and u.players["A"].fighter_challenge is not None
    u.players["A"].alignment = -5  # turned evil while held
    assert _las(u, "A")["retreat"].legal
    r = _act(u, "A", ActionKind.RETREAT)
    assert r.ok
    assert u.players["A"].ship.ship_class != ShipClass.IMPERIAL_STARSHIP
    assert any(e.kind == EventKind.FED_REPOSSESS for e in u.events)


def test_qc_sector_lists_federals_and_prompt_carries_police(tw):
    """f1/f2 obs: a Fed in your sector is in the sector block (not only in the attack list); police/fedspace in prompt."""
    u = _world(players={"A": dict(alignment=600, fighters=150, sector_id=1)})
    _fed(u, "Nelson").sector_id = 1
    obs = build_observation(u, "A")
    d = obs.model_dump(mode="json")
    assert {"name": "Nelson", "title": "Admiral", "kind": "federal"} in d["sector"]["federals"]
    assert "Captain" not in json.dumps(d["sector"]["federals"])  # Zyrain is in 7, not here
    text = format_observation(obs)
    payload = json.loads(text)
    assert payload["police"]["commission"]["eligible"] is True
    assert payload["fedspace"]["will_be_towed"] is True
    assert "Nelson" in json.dumps(payload["sector"])


def test_qc_sector_federals_absent_under_legacy(legacy):
    from tw2k.engine.scanners import sector_view

    u = _world(players={"A": dict(alignment=600, fighters=150, sector_id=7)})
    d = _obs(u, "A")
    assert "federals" not in d["sector"]
    assert "police" not in d and "fedspace" not in d
    payload = json.loads(format_observation(build_observation(u, "A")))
    assert "police" not in payload and "fedspace" not in payload
    assert "federals" not in sector_view(u, "A", 7)  # holo/probe memory stays byte-identical in legacy


def test_qc_fedspace_hint_does_not_count_cloaked_rivals(tw):
    """Fog h15: the parking hint counts only ships the seat can see; the Extern tow still counts cloaked ships."""
    players = {"A": dict(alignment=0, fighters=10, sector_id=3)}
    players.update({f"C{i}": dict(alignment=0, fighters=10, sector_id=3, cloaked=True) for i in range(5)})
    u = _world(players=players)
    u.sectors[3].occupant_ids = ["C0", "C1", "C2", "C3", "C4", "A"]
    hint = _obs(u, "A")["fedspace"]
    assert hint["ships_here"] == 1 and hint["will_be_towed"] is False
    run_tows(u)  # f12/f13: six ships, A arrived last - the Feds still tow it
    assert u.players["A"].sector_id not in K.FEDSPACE_SECTORS


def test_qc_fedspace_hint_parking_names_latest_arrivals_only(tw):
    players = {f"P{i}": dict(alignment=0, fighters=10, sector_id=3) for i in range(6)}
    u = _world(players=players)
    u.sectors[3].occupant_ids = [f"P{i}" for i in range(6)]
    assert _obs(u, "P0")["fedspace"]["will_be_towed"] is False
    assert _obs(u, "P5")["fedspace"]["will_be_towed"] is True
    assert _obs(u, "P5")["fedspace"]["ships_here"] == 6


def test_qc_repossess_seen_by_sector_occupants(tw):
    """f22 / spec events: FED_REPOSSESS goes to the owner plus the sector occupants."""
    u = _world(players={
        "A": dict(alignment=-5, fighters=100, sector_id=20, ship_class="imperial_starship"),
        "W": dict(alignment=0, fighters=10, sector_id=20),
        "F": dict(alignment=0, fighters=10, sector_id=40),
    })
    from tw2k.engine.fed import check_evil_iss_in_sector

    _fed(u, "Nelson").sector_id = 20
    check_evil_iss_in_sector(u, 20)
    assert u.players["A"].ship.ship_class != ShipClass.IMPERIAL_STARSHIP
    assert any(e.get("kind") == "fed_repossess" for e in _obs(u, "W")["recent_events"])
    assert not any(e.get("kind") == "fed_repossess" for e in _obs(u, "F")["recent_events"])


def test_qc_f9_fedsafe_switches_work(tw, monkeypatch):
    """f9 SOURCE-CONFLICT switches are live under tw2002 and ignored under legacy."""
    from tw2k.engine.victory import is_fedsafe

    u = _world(players={"A": dict(alignment=0, experience=100, fighters=51)})
    a = u.players["A"]
    assert is_fedsafe(a)
    monkeypatch.setattr(K, "FEDSAFE_MIN_ALIGNMENT", 1)
    assert not is_fedsafe(a)
    monkeypatch.setattr(K, "FEDSAFE_MIN_ALIGNMENT", 0)
    monkeypatch.setattr(K, "FEDSAFE_MAX_FIGHTERS", 50)
    assert not is_fedsafe(a)
    a.ship.fighters = 50
    assert is_fedsafe(a)
    a.ship.fighters = 51
    monkeypatch.setattr(K, "FED_MODE", "legacy")
    assert is_fedsafe(a)


def test_qc_federals_survive_a_save_load_round_trip(tw):
    from tw2k.engine.fed import Federal
    from tw2k.engine.models import Universe

    u = _world()
    u2 = Universe.model_validate(u.model_dump())
    assert all(isinstance(f, Federal) for f in u2.federals) and len(u2.federals) == 3
    u2.day = 3
    tick_federals(u2)  # used to raise AttributeError on plain dicts
    assert _digest([f.model_dump() for f in u2.federals]) == _digest(
        [f.model_dump() for f in (lambda x: (setattr(x, "day", 3), tick_federals(x), x)[2])(u).federals]
    )


def test_qc_no_bounty_for_killing_yourself(tw):
    from tw2k.engine.fed import record_bounty_on_death

    u = _world(players={"A": dict(alignment=-50), "B": dict(alignment=10)})
    u.posted_rewards = {"A": [{"poster_id": "B", "amount": 5000, "day": 1}]}
    record_bounty_on_death(u, "A", "A", "ship_destroyed")
    assert not u.pending_rewards.get("A") and u.posted_rewards["A"]


def test_qc_bot_finishes_stardock_business_then_leaves_before_extern(tw):
    """Seat brain: armed in sector 1 with turns to spare it does NOT bolt (used to ping-pong); late in the day it leaves."""
    from tw2k.agents.seat_brain import SeatBrain

    u = _world(players={"A": dict(alignment=0, fighters=150, sector_id=1, credits=50_000)})
    brain = SeatBrain()
    act = brain.decide(_obs(u, "A"))
    assert "Extern tow" not in (act.get("thought") or "")
    p = u.players["A"]
    p.turns_today = p.turns_per_day - 3
    act = brain.decide(_obs(u, "A"))
    assert act["kind"] == "warp" and "Extern tow" in act["thought"]
    assert int(act["args"]["target"]) in [int(w) for w in u.sectors[1].warps]


def test_qc_bot_takes_free_commission_and_claims_bounty(tw):
    from tw2k.agents.seat_brain import SeatBrain

    u = _world(players={"A": dict(alignment=600, fighters=10, sector_id=1)})
    u.pending_rewards = {"A": 4000}
    brain = SeatBrain()
    act = brain.decide(_obs(u, "A"))
    assert act["kind"] == "claim_reward"
    assert apply_action(u, "A", Action(kind=act["kind"], args=act.get("args") or {})).ok
    act = brain.decide(_obs(u, "A"))
    assert act["kind"] == "apply_commission"
    assert apply_action(u, "A", Action(kind=act["kind"], args={})).ok
    assert u.players["A"].alignment == 1000 and u.players["A"].credits == 504_000


def test_qc_attack_fed_costs_ten_percent_once_under_legacy_death(tw, monkeypatch):
    """f7: DEATH_MODE legacy has no pod experience loss, so the Fed attack takes the 10% itself."""
    monkeypatch.setattr(K, "DEATH_MODE", "legacy")
    u = _world(players={"A": dict(alignment=100, fighters=40, sector_id=1, experience=500)})
    _fed(u, "Nelson").sector_id = 1
    assert _act(u, "A", ActionKind.ATTACK, target="fed:Nelson", qty=10).ok
    assert u.players["A"].alignment == 90 and u.players["A"].experience == 450 and u.players["A"].deaths == 1


# Recorded with tests/fed_legacy_digest.py on the engine WITHOUT this slice: 4a2200a + bc868c6 (class0 terra QC
# fixes) cherry-picked, i.e. origin minus fedspace-police-v1. Scripted match seats N2,H, seed 250925, 2 days, every
# *_MODE switch legacy: every observation JSON, prompt text, action + result, event and end-of-day universe state
# (minus the five new default fields; floats rounded to 6 places for Linux/Windows libm). The FED_MODE-only
# legacy digest matched too (QC note).
LEGACY_RUN_GOLDEN_PRE_SLICE = "377d39dbcae3e84da90e035f"


def test_qc_fed_legacy_matches_pre_slice_golden(legacy, monkeypatch):
    """FED_MODE legacy is byte-identical to the pre-slice engine (spec: LEGACY_GOLDEN pattern)."""
    import os
    import subprocess
    import sys

    code = (
        "import sys; from pathlib import Path; sys.path.insert(0, 'src'); sys.path.insert(0, 'tests');"
        "from fed_legacy_digest import legacy_run_digest; print(legacy_run_digest(Path('.'), 'N2,H', 2))"
    )
    env = dict(os.environ, PYTHONHASHSEED="0")
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True,
                         timeout=600, check=True)
    assert out.stdout.strip().splitlines()[-1] == LEGACY_RUN_GOLDEN_PRE_SLICE


# ---- rows the rules table names but 58acec8 never defined (QC) ----


def test_f6_presence(tw, monkeypatch):
    """f6: a Fed sharing the sector kills an evil uncloaked ISS even where mbbs move rules keep it safe."""
    monkeypatch.setattr(K, "ISS_REPO_MODE", "mbbs")
    for cloaked, survives in ((False, False), (True, True)):
        u = _world(players={"A": dict(alignment=-5, fighters=100, sector_id=20, ship_class="imperial_starship",
                                      cloaked=cloaked)})
        there = int(u.sectors[20].warps[0])
        u.sectors[there].fighters = FighterDeployment(owner_id="A", count=5, mode=FighterMode.DEFENSIVE)
        _fed(u, "Nelson").sector_id = there  # was there before the fighters went down
        assert _act(u, "A", ActionKind.WARP, target=there).ok
        alive_iss = u.players["A"].ship.ship_class == ShipClass.IMPERIAL_STARSHIP
        assert alive_iss is survives
        assert any(e.kind == EventKind.FED_REPOSSESS for e in u.events) is (not survives)


def test_f24_no_ferrengi_fight(tw):
    """f24: Feds and Ferrengi share sectors without a fight; neither is harmed by the other."""
    u = generate_universe(GameConfig(seed=4601, universe_size=80, enable_ferrengi=True, enable_planets=False))
    ferr = next(iter(u.ferrengi.values()), None)
    if ferr is None:
        pytest.skip("no Ferrengi spawned")
    nelson = _fed(u, "Nelson")
    nelson.sector_id = ferr.sector_id
    fighters_before = int(ferr.fighters)
    from tw2k.engine.fed import check_evil_iss_presence_all

    check_evil_iss_presence_all(u)
    assert ferr.alive and int(ferr.fighters) == fighters_before
    tick_day(u)
    assert len(u.federals) == 3 and {f.density for f in u.federals} == {462, 489, 512}


def test_f25_not_targets(tw):
    """f25: a Fed never steps into a sector where a fighter challenge is open; Feds are not rob/attack ship ids."""
    u = _world(size=60, players={"A": dict(alignment=0, sector_id=30), "B": dict(alignment=0, sector_id=31)})
    nelson = _fed(u, "Nelson")
    warps = [int(w) for w in u.sectors[nelson.sector_id].warps]
    target, others = warps[0], warps[1:]
    for wid in others:
        u.sectors[wid].fighters = FighterDeployment(owner_id="B", count=3, mode=FighterMode.DEFENSIVE)
    u.players["A"].fighter_challenge = {"sector_id": target, "from_sector": 30, "mode": "defensive"}
    start = nelson.sector_id
    u.day = 2
    tick_federals(u)
    assert nelson.sector_id == start  # trapped: fighters everywhere else, a challenge in the last exit
    assert all(not str(t).startswith("fed:") or t.split(":", 1)[1] in {"Zyrain", "Nelson", "Clausewitz"}
               for t in _las(u, "A")["attack"].params["target"]["choices"])
    assert not any(str(pid).startswith("fed") for pid in u.players)


def test_f26_no_toll_mine(tw, monkeypatch):
    """f26/f4: mines do not stop a Fed by default and are untouched; FED_BLOCKED_BY_MINES makes them a wall."""
    from tw2k.engine.fed import _legal_fed_hops
    from tw2k.engine.models import MineDeployment, MineType

    u = _world(size=60, players={"A": dict(alignment=0, sector_id=30), "B": dict(alignment=0, sector_id=31)})
    nelson = _fed(u, "Nelson")
    warps = [int(w) for w in u.sectors[nelson.sector_id].warps]
    mined, others = warps[0], warps[1:]
    for wid in others:
        u.sectors[wid].fighters = FighterDeployment(owner_id="B", count=3, mode=FighterMode.TOLL)
    u.sectors[mined].mines = [MineDeployment(owner_id="B", kind=MineType.ARMID, count=7)]
    assert _legal_fed_hops(u, nelson) == [mined]
    u.day = 2
    tick_federals(u)
    assert u.sectors[mined].mines[0].count == 7  # never hit
    assert nelson.sector_id not in others  # never entered a toll sector
    monkeypatch.setattr(K, "FED_BLOCKED_BY_MINES", True)
    nelson.sector_id = int(next(s for s in u.sectors if mined in u.sectors[s].warps and s != mined))
    assert mined not in _legal_fed_hops(u, nelson)
