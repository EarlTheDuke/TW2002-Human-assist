"""Seat-bot competitive S1 - owned_planets parity for empire play.

docs/plans/2026-09-24-seat-bot-competitive.md: an owning seat must see its
planets' colonists (per pool + total), stockpile, and how it acquired each
planet (genesis vs claim), from its own fogged observation only.
"""

from __future__ import annotations

import json

from tw2k.agents.prompts import format_observation
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Commodity, EventKind, Planet, Player
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import _bfs_path, apply_action


def _universe():
    u = generate_universe(GameConfig(seed=31, universe_size=90, max_days=3, turns_per_day=200,
                                     starting_credits=100_000, enable_ferrengi=False, enable_planets=True))
    for pid, name in (("P1", "Me"), ("P2", "Rival")):
        p = Player(id=pid, name=name, agent_kind="external", sector_id=1, credits=100_000)
        u.players[pid] = p
        u.sectors[1].occupant_ids.append(pid)
    return u


def _move(u, pid: str, sid: int) -> None:
    p = u.players[pid]
    u.sectors[p.sector_id].occupant_ids = [x for x in u.sectors[p.sector_id].occupant_ids if x != pid]
    p.sector_id = sid
    u.sectors[sid].occupant_ids.append(pid)


def _deep_sector(u) -> int:
    for sid in sorted(u.sectors):
        if sid > 10 and len(_bfs_path(u, 1, sid)) >= K.GENESIS_MIN_HOPS_FROM_STARDOCK and not u.sectors[sid].planet_ids:
            return sid
    raise AssertionError("no deep empty sector")


def _owned(u, pid="P1") -> dict[int, dict]:
    return {p["id"]: p for p in build_observation(u, pid).owned_planets}


def _deploy_genesis(u) -> int:
    deep = _deep_sector(u)
    _move(u, "P1", deep)
    u.players["P1"].ship.genesis = 1
    res = apply_action(u, "P1", Action(kind=ActionKind.DEPLOY_GENESIS, args={}))
    assert res.ok, res.error
    return next(pid for pid in u.sectors[deep].planet_ids if u.planets[pid].owner_id == "P1")


def test_genesis_planet_shows_seed_colonists_and_origin() -> None:
    u = _universe()
    plid = _deploy_genesis(u)
    entry = _owned(u)[plid]
    assert entry["origin"] == "genesis"
    assert entry["colonists_total"] == K.GENESIS_SEED_COLONISTS
    assert set(entry["colonists"]) == {"fuel_ore", "organics", "equipment", "colonists"}
    assert sum(entry["colonists"].values()) == entry["colonists_total"]
    assert entry["stockpile"]["organics"] >= 25
    # Existing keys preserved.
    for k in ("id", "sector_id", "name", "class", "citadel_level", "citadel_target",
              "citadel_complete_day", "fighters", "shields"):
        assert k in entry, k


def test_assign_colonists_from_ship_is_visible_to_owner() -> None:
    u = _universe()
    plid = _deploy_genesis(u)
    p = u.players["P1"]
    assert apply_action(u, "P1", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": plid})).ok
    p.ship.cargo[Commodity.COLONISTS] = 15
    before = _owned(u)[plid]
    res = apply_action(u, "P1", Action(kind=ActionKind.ASSIGN_COLONISTS,
                                       args={"planet_id": plid, "from": "ship", "to": "organics", "qty": 15}))
    assert res.ok, res.error
    after = _owned(u)[plid]
    assert after["colonists"]["organics"] == before["colonists"]["organics"] + 15
    assert after["colonists_total"] == before["colonists_total"] + 15
    assert p.ship.cargo[Commodity.COLONISTS] == 0


def test_neutral_landing_claim_is_distinguishable_from_genesis() -> None:
    u = _universe()
    gen_id = _deploy_genesis(u)
    neutral = next(pl for pl in u.planets.values() if pl.owner_id is None and pl.id != gen_id)
    neutral.colonists = {c: 0 for c in neutral.colonists}
    _move(u, "P1", neutral.sector_id)
    assert apply_action(u, "P1", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": neutral.id})).ok
    owned = _owned(u)
    assert owned[neutral.id]["origin"] == "claim"
    assert owned[neutral.id]["colonists_total"] == 0
    assert owned[gen_id]["origin"] == "genesis"
    # The engine agrees the claim world cannot build yet, and says why.
    la = {x.kind: x for x in legal_actions(u, "P1")}["build_citadel"]
    assert la.legal is False and "colonists" in (la.reason or "")


def test_orphan_claim_planet_is_claim_origin() -> None:
    u = _universe()
    pl = next(iter(u.planets.values()))
    pl.owner_id = None
    pl.corp_ticker = None
    pl.origin = "genesis"  # it WAS someone's genesis world; the new owner claimed it
    u.emit(EventKind.PLANET_ORPHANED, actor_id="P2", sector_id=pl.sector_id,
           payload={"planet_id": pl.id, "planet_name": pl.name, "former_owner": "P2"}, summary="orphaned")
    _move(u, "P1", pl.sector_id)
    u.players["P1"].planet_landed = pl.id
    assert apply_action(u, "P1", Action(kind=ActionKind.CLAIM_PLANET, args={})).ok
    assert _owned(u)[pl.id]["origin"] == "claim"


def test_siege_seizure_is_other_origin() -> None:
    u = _universe()
    pl = next(iter(u.planets.values()))
    pl.owner_id, pl.corp_ticker, pl.fighters, pl.origin = "P2", None, 0, "genesis"
    _move(u, "P1", pl.sector_id)
    assert apply_action(u, "P1", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": pl.id})).ok
    assert _owned(u)[pl.id]["origin"] == "other"


def test_rival_planets_stay_fogged() -> None:
    u = _universe()
    plid = _deploy_genesis(u)
    assert plid in _owned(u, "P1")
    assert plid not in _owned(u, "P2")  # another seat never sees my colonists via owned_planets


def test_llm_message_ships_colonists_and_origin() -> None:
    u = _universe()
    plid = _deploy_genesis(u)
    msg = json.loads(format_observation(build_observation(u, "P1")))
    entry = next(p for p in msg["owned_planets"] if p["id"] == plid)
    assert entry["origin"] == "genesis" and entry["colonists_total"] == K.GENESIS_SEED_COLONISTS


def test_legal_reasons_for_empire_verbs() -> None:
    u = _universe()
    # deploy_genesis: outside FedSpace but too close to StarDock.
    near = next(s for s in sorted(u.sectors) if s not in K.FEDSPACE_SECTORS
                and 0 < len(_bfs_path(u, 1, s)) < K.GENESIS_MIN_HOPS_FROM_STARDOCK)
    _move(u, "P1", near)
    u.players["P1"].ship.genesis = 1
    la = {x.kind: x for x in legal_actions(u, "P1")}["deploy_genesis"]
    assert la.legal is False and "too close to StarDock" in (la.reason or "")
    assert apply_action(u, "P1", Action(kind=ActionKind.DEPLOY_GENESIS, args={})).ok is False
    _move(u, "P1", 1)
    # assign_colonists: not landed.
    plid = _deploy_genesis(u)
    la = {x.kind: x for x in legal_actions(u, "P1")}["assign_colonists"]
    assert la.legal is False and la.reason == "not landed on a planet"
    # Landed on own genesis world with seed colonists: assign + build are legal.
    assert apply_action(u, "P1", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": plid})).ok
    las = {x.kind: x for x in legal_actions(u, "P1")}
    assert las["assign_colonists"].legal is True
    assert las["build_citadel"].legal is True
    assert las["build_citadel"].params["next"]["colonists_have"] == _owned(u)[plid]["colonists_total"]


def test_legacy_planet_without_origin_defaults_to_other() -> None:
    data = Planet(id=1, sector_id=5, name="Old", class_id="M").model_dump()
    data.pop("origin")
    assert Planet.model_validate(data).origin == "other"
