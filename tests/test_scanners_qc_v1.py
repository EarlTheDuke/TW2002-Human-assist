"""Independent QC of scanners-hidden-info-v1 (29257a1).

Each test failed on 29257a1. Real engine path.
"""

from __future__ import annotations

import json

import tw2k.engine.constants as K
from tests.test_phase_abc import _first_non_fed_sector, _make_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import FighterDeployment, FighterMode, MineDeployment, MineType
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import apply_action
from tw2k.engine.scanners import sector_view


def _park(u, p, sid: int) -> None:
    here = u.sectors[p.sector_id]
    if p.id in here.occupant_ids:
        here.occupant_ids.remove(p.id)
    p.sector_id = sid
    p.planet_landed = None
    if p.id not in u.sectors[sid].occupant_ids:
        u.sectors[sid].occupant_ids.append(p.id)


def _adj(u, pid: str) -> dict[int, dict]:
    return {int(x["id"]): x for x in build_observation(u, pid).adjacent}


def _neighbor(u, home: int) -> int:
    return next(w for w in u.sectors[home].warps if w not in K.FEDSPACE_SECTORS and w != K.STARDOCK_SECTOR)


# ---------------------------------------------------------------------------
# density must not erase a prior holo reading
# ---------------------------------------------------------------------------


def test_a_density_scan_does_not_erase_a_prior_holo_reading() -> None:
    u, (a, b, c) = _make_universe(seed=71001)
    home = _first_non_fed_sector(u, 40)
    there = _neighbor(u, home)
    _park(u, a, home)
    _park(u, b, there)
    u.sectors[there].fighters = FighterDeployment(owner_id=b.id, count=17, mode=FighterMode.DEFENSIVE)
    a.ship.scanner = "holo"
    a.credits = 50_000
    assert apply_action(u, a.id, Action(kind=ActionKind.SCAN, args={"tier": "holo"})).ok
    before = _adj(u, a.id)[there]
    assert before.get("fighter_count") == 17 and before.get("seen") and before["seen"]["traders"]
    # Free density (also what the cockpit S key sends with empty args).
    assert apply_action(u, a.id, Action(kind=ActionKind.SCAN, args={"tier": "density"})).ok
    after = _adj(u, a.id)[there]
    assert after.get("fighter_count") == 17, after
    assert after.get("seen") and after["seen"].get("traders"), after
    assert after.get("density") == before.get("density")
    assert after.get("scan_tier") == "density"  # last op was density
    assert a.scan_memory[there].get("has_holo") is True


def test_cockpit_empty_args_scan_is_density_and_keeps_holo() -> None:
    """web/bot.js S key submits scan with args {}. That is a density scan."""
    u, (a, b, c) = _make_universe(seed=71002)
    home = _first_non_fed_sector(u, 40)
    there = _neighbor(u, home)
    _park(u, a, home)
    u.sectors[there].fighters = FighterDeployment(owner_id=b.id, count=9, mode=FighterMode.TOLL)
    a.ship.scanner = "holo"
    assert apply_action(u, a.id, Action(kind=ActionKind.SCAN, args={"tier": "holo"})).ok
    assert apply_action(u, a.id, Action(kind=ActionKind.SCAN, args={})).ok  # empty = density
    after = _adj(u, a.id)[there]
    assert after.get("fighter_count") == 9 and after.get("seen")


# ---------------------------------------------------------------------------
# limpets never on a holo / probe view
# ---------------------------------------------------------------------------


def test_holo_and_probe_hide_even_your_own_limpets() -> None:
    u, (a, b, c) = _make_universe(seed=71003)
    home = _first_non_fed_sector(u, 40)
    there = _neighbor(u, home)
    _park(u, a, home)
    u.sectors[there].mines = [
        MineDeployment(owner_id=a.id, kind=MineType.LIMPET, count=2),
        MineDeployment(owner_id=a.id, kind=MineType.ARMID, count=3),
    ]
    view = sector_view(u, a.id, there)
    assert all(m["kind"] != "limpet" for m in view["mines"])
    assert any(m["kind"] == "armid" and m["count"] == 3 for m in view["mines"])
    a.ship.scanner = "holo"
    assert apply_action(u, a.id, Action(kind=ActionKind.SCAN, args={"tier": "holo"})).ok
    seen = _adj(u, a.id)[there]["seen"]
    assert all(m["kind"] != "limpet" for m in seen.get("mines") or [])


# ---------------------------------------------------------------------------
# legal list / handler: scan without scanner; fog to rivals
# ---------------------------------------------------------------------------


def test_scan_without_a_scanner_is_refused_the_same_way_in_list_and_handler() -> None:
    u, (a, b, c) = _make_universe(seed=71004)
    la = {x.kind: x for x in legal_actions(u, a.id)}["scan"]
    assert not la.legal and "scanner" in (la.reason or "")
    res = apply_action(u, a.id, Action(kind=ActionKind.SCAN, args={}))
    assert not res.ok and res.error == la.reason


def test_a_rival_never_sees_scan_neighbors_or_probe_route() -> None:
    u, (a, b, c) = _make_universe(seed=71005)
    home = _first_non_fed_sector(u, 40)
    there = _neighbor(u, home)
    _park(u, a, home)
    _park(u, b, there)
    a.ship.scanner = "holo"
    a.ship.ether_probes = 2
    assert apply_action(u, a.id, Action(kind=ActionKind.SCAN, args={"tier": "holo"})).ok
    assert apply_action(u, a.id, Action(kind=ActionKind.PROBE, args={"target": there})).ok
    other = build_observation(u, b.id).model_dump(mode="json")
    kinds = {e["kind"] for e in other["recent_events"]}
    assert "scan" not in kinds and "probe" not in kinds
    blob = json.dumps(other)
    assert '"neighbors"' not in blob
    # A's own facts stay fogged (no neighbors key).
    mine = build_observation(u, a.id).model_dump(mode="json")
    for e in mine["recent_events"]:
        if e["kind"] in ("scan", "probe"):
            assert "neighbors" not in e.get("facts", {})
            assert "route" not in e.get("facts", {})


def test_adjacent_without_a_scan_carries_no_live_contents() -> None:
    u, (a, b, c) = _make_universe(seed=71006)
    home = _first_non_fed_sector(u, 40)
    there = _neighbor(u, home)
    _park(u, a, home)
    _park(u, b, there)
    u.sectors[there].fighters = FighterDeployment(owner_id=b.id, count=44, mode=FighterMode.OFFENSIVE)
    adj = _adj(u, a.id)[there]
    assert set(adj) <= {"id", "port", "known"} or (
        adj.get("fighter_count") is None and not adj.get("seen") and adj.get("density") is None
    )
    assert adj.get("fighter_count") in (None, 0) and not adj.get("occupants") and not adj.get("seen")


def test_warp_list_does_not_advertise_tolls_under_tw2002_combat() -> None:
    u, (a, b, c) = _make_universe(seed=71007)
    home = _first_non_fed_sector(u, 40)
    there = _neighbor(u, home)
    _park(u, a, home)
    u.sectors[there].fighters = FighterDeployment(owner_id=b.id, count=20, mode=FighterMode.TOLL)
    warp = {x.kind: x for x in legal_actions(u, a.id)}["warp"]
    assert warp.params.get("toll_due_by") == {}
    assert there in warp.params["target"]["choices"]
