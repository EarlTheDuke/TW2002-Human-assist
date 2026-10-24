"""NOTE 78 (v311-universe-planet-gaps-v1). Each switch off stays on the clone rule.

On, the S1 treasury cap, the course cap, the Big Bang densities, the 3%
one-way share and the detonator planet-killer are in force. Stored defaults
stay legacy.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

import tw2k.engine.constants as K
from tests.test_phase_abc import _make_universe
from tests.test_ship_hardware_v2 import _planet, _world
from tw2k.agents.rules_text import plot_course_line
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import (
    GameConfig,
    MineType,
    Player,
    PortClass,
    Sector,
    Ship,
    ShipClass,
    Universe,
)
from tw2k.engine.planets import _accrue_planet_treasury
from tw2k.engine.runner import apply_action, query_route
from tw2k.engine.universe import generate_universe


def _las(u, pid: str) -> dict:
    return {la.kind: la for la in legal_actions(u, pid)}


def _move(u, player, dest: int) -> None:
    if player.id in u.sectors[player.sector_id].occupant_ids:
        u.sectors[player.sector_id].occupant_ids.remove(player.id)
    player.sector_id = dest
    u.sectors[dest].occupant_ids.append(player.id)


def _trade_port(u) -> int:
    for sid in sorted(u.sectors):
        port = u.sectors[sid].port
        if sid <= 10 or port is None:
            continue
        if port.class_id in (PortClass.STARDOCK, PortClass.FEDERAL):
            continue
        if getattr(port, "special", None):
            continue
        return sid
    raise AssertionError("no trade port")


def _warps(u) -> dict[int, list[int]]:
    return {sid: list(sec.warps) for sid, sec in u.sectors.items()}


def _one_ways(u) -> int:
    n = 0
    for sid, sec in u.sectors.items():
        for dest in sec.warps:
            if sid not in u.sectors[int(dest)].warps:
                n += 1
    return n


def _line(hops: int, *, max_course_length: int | None = None) -> tuple[Universe, Player]:
    """A two-way chain. Sector hops+1 is `hops` warps from sector 1."""
    n = hops + 1
    sectors = {}
    for i in range(1, n + 1):
        warps = []
        if i > 1:
            warps.append(i - 1)
        if i < n:
            warps.append(i + 1)
        sectors[i] = Sector(id=i, warps=warps)
    cfg: dict = {"seed": 1, "universe_size": n, "enable_ferrengi": False, "enable_planets": False}
    if max_course_length is not None:
        cfg["max_course_length"] = max_course_length
    u = Universe(
        config=GameConfig(**cfg),
        sectors=sectors,
    )
    player = Player(
        id="P1", name="P1", sector_id=1, credits=1000,
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER),
        turns_per_day=10_000,
    )
    u.players["P1"] = player
    u.sectors[1].occupant_ids.append("P1")
    return u, player


def test_stored_defaults_stay_legacy() -> None:
    assert K.TREASURY_CAP_MODE == "legacy"
    assert K.COURSE_MAX_MODE == "legacy"
    assert K.BIG_BANG_DENSITY_MODE == "legacy"
    assert K.ONE_WAY_SHARE_MODE == "legacy"
    assert K.ATOMIC_DETONATOR_MODE == "legacy"
    assert K.treasury_cap_live() is False
    assert K.course_max_live() is False
    assert K.big_bang_density_live() is False
    assert K.one_way_share_live() is False
    assert K.atomic_detonator_live() is False
    assert K.planet_treasury_cap() == K.PLANET_TREASURY_CAP == 10_000_000
    assert K.plot_course_hop_limit() == K.PLOT_COURSE_MAX_DEPTH * 6 == 60
    assert K.V311_COURSE_MAX_HOPS == 45
    assert K.atomic_mines_sold() is True
    assert K.ATOMIC_MINES_PORT_NUKE is True


def test_profile_turns_the_five_on_without_writing_the_flags(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.treasury_cap_live() and K.course_max_live() and K.big_bang_density_live()
    assert K.one_way_share_live() and K.atomic_detonator_live()
    assert K.TREASURY_CAP_MODE == "legacy"
    assert K.COURSE_MAX_MODE == "legacy"
    assert K.BIG_BANG_DENSITY_MODE == "legacy"
    assert K.ONE_WAY_SHARE_MODE == "legacy"
    assert K.ATOMIC_DETONATOR_MODE == "legacy"
    assert K.PLANET_TREASURY_CAP == 10_000_000
    assert K.ATOMIC_MINES_PORT_NUKE is True
    assert K.planet_treasury_cap() == 999_999_999_999_999
    assert K.plot_course_hop_limit() == 45
    assert K.atomic_mines_sold() is False


def test_treasury_cap_off_is_ten_million_and_on_is_s1(monkeypatch) -> None:
    u, (owner, *_) = _make_universe(seed=7810)
    planet = _planet(u, 120, colonists=0, owner=owner.id)
    planet.citadel_level = 1
    planet.citadel_target = 1
    planet.treasury = K.PLANET_TREASURY_CAP - 5
    owner.planet_landed = planet.id
    owner.credits = 20_000_000
    _move(u, owner, 120)
    refused = apply_action(u, owner.id, Action(
        kind=ActionKind.DEPOSIT_TREASURY, args={"planet_id": planet.id, "amount": 6},
    ))
    assert refused.ok is False
    assert refused.error == f"planet treasury cap is {K.PLANET_TREASURY_CAP}"
    assert "room" not in _las(u, owner.id)["deposit_treasury"].params
    planet.citadel_level = 2
    planet.treasury = K.PLANET_TREASURY_CAP - 5
    _accrue_planet_treasury(u)
    assert planet.treasury == K.PLANET_TREASURY_CAP

    monkeypatch.setattr(K, "TREASURY_CAP_MODE", "live")
    assert K.PLANET_TREASURY_CAP == 10_000_000
    planet.treasury = 10_000_000
    taken = apply_action(u, owner.id, Action(
        kind=ActionKind.DEPOSIT_TREASURY, args={"planet_id": planet.id, "amount": 100},
    ))
    assert taken.ok, taken.error
    assert planet.treasury == 10_000_100
    params = _las(u, owner.id)["deposit_treasury"].params
    assert params["capacity"] == 999_999_999_999_999
    assert params["room"] == 999_999_999_999_999 - 10_000_100
    planet.treasury = K.S1_PLANET_TREASURY_CAP - 5
    planet.citadel_level = 2
    _accrue_planet_treasury(u)
    assert planet.treasury == K.S1_PLANET_TREASURY_CAP


def test_course_over_45_is_refused_only_when_live(monkeypatch) -> None:
    u, _player = _line(49)
    preview = apply_action(u, "P1", Action(kind=ActionKind.PLOT_COURSE, args={"target": 50}))
    assert preview.ok, preview.error
    assert "10 warps" in plot_course_line()
    asked = query_route(u, "P1", 50)
    assert asked["ok"] and len(asked["path"]) == 49
    short = apply_action(u, "P1", Action(kind=ActionKind.PLOT_COURSE, args={"target": 21}))
    assert short.ok, short.error

    monkeypatch.setattr(K, "COURSE_MAX_MODE", "live")
    assert K.PLOT_COURSE_MAX_DEPTH == 10
    refused = apply_action(u, "P1", Action(kind=ActionKind.PLOT_COURSE, args={"target": 50}))
    assert refused.ok is False
    assert refused.error == "plotted course is longer than 45 hops"
    assert u.players["P1"].sector_id == 1
    queried = query_route(u, "P1", 50)
    assert queried["ok"] is False
    assert queried["error"] == "plotted course is longer than 45 hops"
    assert queried["path"] == []
    allowed = apply_action(u, "P1", Action(kind=ActionKind.PLOT_COURSE, args={"target": 21}))
    assert allowed.ok, allowed.error
    assert "45 warps" in plot_course_line()
    assert "UNVERIFIED" in K.course_max_live.__doc__ or "UNVERIFIED" in (
        K.__dict__["plot_course_hop_limit"].__doc__ or ""
    )


def _plot(u: Universe, target: int, *, execute: bool = False):
    return apply_action(u, "P1", Action(
        kind=ActionKind.PLOT_COURSE, args={"target": target, "execute": execute},
    ))


def test_live_plot_accepts_the_cap_and_refuses_one_more(monkeypatch) -> None:
    """NOTE 96. 45 stays. A computer plot of that many hops succeeds; one more is refused.

    The computer course plotter reads query_route (cockpit C, then F, and CIM F).
    plot_course is the same graph, including execute.
    """
    cap = int(K.V311_COURSE_MAX_HOPS)
    assert cap == 45
    at_cap = cap + 1
    over = cap + 2
    legacy, _who = _line(cap + 1)
    assert K.course_max_live() is False
    assert K.plot_course_hop_limit() == 60
    assert _plot(legacy, over).ok
    seen = query_route(legacy, "P1", over)
    assert seen["ok"] and seen["hops"] == cap + 1

    def _boundary(label: str) -> None:
        assert K.course_max_live() is True, label
        assert K.plot_course_hop_limit() == cap
        fresh, who = _line(cap + 1)
        refused = _plot(fresh, over)
        assert refused.ok is False, label
        assert refused.error == f"plotted course is longer than {cap} hops"
        assert who.sector_id == 1 and who.turns_today == 0
        flown = _plot(fresh, over, execute=True)
        assert flown.ok is False and flown.error == refused.error
        assert who.sector_id == 1 and who.turns_today == 0
        asked = query_route(fresh, "P1", over)
        assert asked["ok"] is False
        assert asked["error"] == refused.error
        assert asked["path"] == []
        preview = _plot(fresh, at_cap)
        assert preview.ok, preview.error
        assert who.sector_id == 1
        route = query_route(fresh, "P1", at_cap)
        assert route["ok"] and route["hops"] == cap and len(route["path"]) == cap
        shorter = _plot(fresh, 2)
        assert shorter.ok, shorter.error
        done = _plot(fresh, at_cap, execute=True)
        assert done.ok, done.error
        assert who.sector_id == at_cap
        gone, pilot = _line(cap + 1)
        prev = over - 1
        gone.sectors[prev].warps = [w for w in gone.sectors[prev].warps if int(w) != over]
        missing = query_route(gone, "P1", over)
        assert missing["ok"] is False and missing["error"] == "no route"
        blocked = _plot(gone, over)
        assert blocked.ok is False and blocked.error == "no route to target"
        assert pilot.sector_id == 1

    monkeypatch.setattr(K, "COURSE_MAX_MODE", "live")
    assert K.V311_PROFILE != "v311"
    _boundary("COURSE_MAX_MODE")
    monkeypatch.setattr(K, "COURSE_MAX_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.COURSE_MAX_MODE == "legacy"
    _boundary("v311 profile")


def test_a_game_refuses_one_hop_past_its_own_course_length(monkeypatch) -> None:
    """NOTE 96. GameA TWSTATS is 20. Unset live games keep the published sample 45.

    TWGS stores Maximum Course Length on the game (BIGBANG, then TEDIT). The
    plotter reads GameConfig.max_course_length when that is set.
    """
    assert K.GAMEA_COURSE_MAX_HOPS == 20
    assert K.V311_COURSE_MAX_HOPS == 45
    assert "max_course_length" not in GameConfig(seed=1).model_dump()
    stored = GameConfig(seed=1, max_course_length=K.GAMEA_COURSE_MAX_HOPS)
    assert stored.model_dump()["max_course_length"] == 20
    assert GameConfig(max_course_length=300).max_course_length == 300
    assert GameConfig(max_course_length=0).max_course_length == 0
    assert GameConfig(max_course_length="").max_course_length is None
    for bad in (-1, True, "twenty"):
        with pytest.raises(ValidationError):
            GameConfig(max_course_length=bad)

    cap = int(K.GAMEA_COURSE_MAX_HOPS)
    at_cap = cap + 1
    over = cap + 2
    monkeypatch.setattr(K, "COURSE_MAX_MODE", "legacy")
    legacy, _who = _line(cap + 1, max_course_length=cap)
    assert K.plot_course_hop_limit(legacy.config) == 60
    assert _plot(legacy, over).ok

    monkeypatch.setattr(K, "COURSE_MAX_MODE", "live")
    assert K.plot_course_hop_limit() == 45
    fresh, who = _line(cap + 1, max_course_length=cap)
    assert K.plot_course_hop_limit(fresh.config) == cap
    refused = _plot(fresh, over)
    assert refused.ok is False
    assert refused.error == f"plotted course is longer than {cap} hops"
    assert who.sector_id == 1 and who.turns_today == 0
    flown = _plot(fresh, over, execute=True)
    assert flown.ok is False and flown.error == refused.error
    assert who.sector_id == 1 and who.turns_today == 0
    asked = query_route(fresh, "P1", over)
    assert asked["ok"] is False and asked["path"] == []
    assert asked["error"] == refused.error
    preview = _plot(fresh, at_cap)
    assert preview.ok and who.sector_id == 1
    route = query_route(fresh, "P1", at_cap)
    assert route["ok"] and route["hops"] == cap and len(route["path"]) == cap
    done = _plot(fresh, at_cap, execute=True)
    assert done.ok, done.error
    assert who.sector_id == at_cap

    monkeypatch.setattr(K, "COURSE_MAX_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.COURSE_MAX_MODE == "legacy"
    profile, pilot = _line(cap + 1, max_course_length=cap)
    assert K.plot_course_hop_limit(profile.config) == cap
    blocked = _plot(profile, over)
    assert blocked.ok is False
    assert blocked.error == f"plotted course is longer than {cap} hops"
    assert pilot.sector_id == 1


def test_big_bang_densities_keep_sol_terra_stardock_and_class0(monkeypatch) -> None:
    cfg = GameConfig(seed=11, universe_size=400, enable_ferrengi=False)
    off = generate_universe(cfg)
    assert off.sectors[1].port is not None
    assert off.sectors[1].port.class_id is PortClass.STARDOCK
    assert "StarDock" in (off.sectors[1].port.name or "")
    decorative = [
        sid for sid in range(2, 11)
        if off.sectors[sid].port is not None and off.sectors[sid].port.special is None
    ]
    assert decorative
    deep = list(range(11, 401))
    off_ports = sum(1 for sid in deep if off.sectors[sid].port is not None)
    assert off_ports / len(deep) > 0.55
    assert len(off.planets) < 40

    monkeypatch.setattr(K, "BIG_BANG_DENSITY_MODE", "live")
    on = generate_universe(GameConfig(seed=11, universe_size=400, enable_ferrengi=False))
    assert on.class0_sectors == off.class0_sectors
    assert on.terra_colonists == off.terra_colonists
    assert on.terra_max == off.terra_max
    assert on.sectors[1].port.class_id is PortClass.STARDOCK
    assert on.sectors[1].port.name == off.sectors[1].port.name
    assert all(on.sectors[sid].port is None for sid in range(2, 11))
    on_ports = sum(1 for sid in deep if on.sectors[sid].port is not None)
    assert 0.30 < on_ports / len(deep) < 0.50
    assert 50 < len(on.planets) < 120
    for sid in on.class0_sectors.values():
        assert on.sectors[sid].port is not None
        assert on.sectors[sid].port.special in ("alpha_centauri", "rylos")


def test_one_way_share_is_three_percent_unless_the_game_sets_it(monkeypatch) -> None:
    plain = GameConfig(seed=7, universe_size=250, enable_ferrengi=False, enable_planets=False)
    explicit = GameConfig(
        seed=7, universe_size=250, enable_ferrengi=False, enable_planets=False,
        one_way_fraction=0.15,
    )
    custom = GameConfig(
        seed=7, universe_size=250, enable_ferrengi=False, enable_planets=False,
        one_way_fraction=0.40,
    )
    assert "one_way_fraction" not in plain.model_fields_set
    assert "one_way_fraction" in explicit.model_fields_set
    off = generate_universe(plain)
    off_explicit = generate_universe(explicit)
    assert _warps(off) == _warps(off_explicit)

    monkeypatch.setattr(K, "ONE_WAY_SHARE_MODE", "live")
    assert K.DEFAULT_ONE_WAY_FRACTION == 0.15
    thinned = generate_universe(plain)
    kept = generate_universe(explicit)
    custom_on = generate_universe(custom)
    assert _warps(kept) == _warps(off)
    assert _one_ways(thinned) < _one_ways(off) // 2
    monkeypatch.setattr(K, "ONE_WAY_SHARE_MODE", "legacy")
    custom_off = generate_universe(custom)
    assert _warps(custom_on) == _warps(custom_off)
    assert _one_ways(custom_off) > _one_ways(off)


def test_atomic_mine_stays_until_the_detonator_switch(monkeypatch) -> None:
    u, (owner, *_) = _make_universe(seed=7811, size=80)
    sid = _trade_port(u)
    _move(u, owner, sid)
    port = u.sectors[sid].port
    assert port.stock
    for row in port.stock.values():
        row.current = 1000
    before = sum(int(row.current) for row in port.stock.values())
    assert before > 0
    owner.ship.mines[MineType.ATOMIC] = 1
    boom = apply_action(u, owner.id, Action(
        kind=ActionKind.DEPLOY_MINES, args={"kind": "atomic", "qty": 1},
    ))
    assert boom.ok, boom.error
    after = sum(int(row.current) for row in port.stock.values())
    assert after < before

    fresh, (pilot, *_) = _make_universe(seed=7812, size=80)
    sid = _trade_port(fresh)
    _move(fresh, pilot, sid)
    port = fresh.sectors[sid].port
    for row in port.stock.values():
        row.current = 1000
    held = sum(int(row.current) for row in port.stock.values())
    pilot.ship.mines[MineType.ATOMIC] = 1
    monkeypatch.setattr(K, "ATOMIC_DETONATOR_MODE", "live")
    assert K.ATOMIC_MINES_PORT_NUKE is True
    assert K.atomic_mines_sold() is False
    refused = apply_action(fresh, pilot.id, Action(
        kind=ActionKind.DEPLOY_MINES, args={"kind": "atomic", "qty": 1},
    ))
    assert refused.ok is False
    assert refused.error == (
        "atomic mines are retired; an atomic detonator kills the colonists first, then the planet"
    )
    assert sum(int(row.current) for row in port.stock.values()) == held
    assert pilot.ship.mines[MineType.ATOMIC] == 1
    _move(fresh, pilot, K.STARDOCK_SECTOR)
    assert "atomic_mines" not in _las(fresh, pilot.id)["buy_equip"].params["item"]["choices"]


def test_detonator_kills_colonists_first_then_the_planet(monkeypatch) -> None:
    monkeypatch.setattr(K, "ATOMIC_DETONATOR_MODE", "live")
    u, sid, _adj = _world()
    pl = _planet(u, sid, colonists=40, owner="B")
    u.players["A"].planet_landed = pl.id
    cleared = apply_action(u, "A", Action(
        kind=ActionKind.PLANET_DESTROY, args={"planet_id": pl.id},
    ))
    assert cleared.ok, cleared.error
    assert sum(pl.colonists.values()) == 0
    assert pl.id in u.planets
    blocked = apply_action(u, "A", Action(
        kind=ActionKind.PLANET_DESTROY, args={"planet_id": pl.id},
    ))
    assert blocked.ok is False
    assert "atomic detonator" in (blocked.error or "")
    u.players["A"].ship.atomic_detonators = 1
    gone = apply_action(u, "A", Action(
        kind=ActionKind.PLANET_DESTROY, args={"planet_id": pl.id},
    ))
    assert gone.ok, gone.error
    assert pl.id not in u.planets
    assert u.players["A"].ship.atomic_detonators == 0

    u, sid, _adj = _world(seed=5203)
    pl = _planet(u, sid, colonists=12, owner="B")
    u.players["A"].planet_landed = pl.id
    u.players["A"].ship.atomic_detonators = 1
    backfire = apply_action(u, "A", Action(
        kind=ActionKind.DEPLOY_ATOMIC, args={"planet_id": pl.id},
    ))
    assert backfire.ok, backfire.error
    assert pl.id in u.planets
    assert sum(pl.colonists.values()) == 12
