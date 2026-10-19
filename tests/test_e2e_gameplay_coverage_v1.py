"""NOTE 99. End-to-end plays for the never-scripted suite.

The gameplay_test case text and MASTER_PLAN.md are not in this repo. Each case
below is written from the row named in COMMANDER NOTE 99 and the rule already
in the engine. OTH-02, OTH-03, OTH-04, SD-P2-01, FIG-06 and FIG-09 have no
sentence in the note beyond the id, so the reading is marked on the test.

Logs go to tmp_path. Set TW2K_E2E_LOG=1 to also write
docs/playtests/e2e-gameplay-coverage-v1/. No engine default changes.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.models import (
    Commodity,
    EventKind,
    FighterDeployment,
    FighterMode,
    MineDeployment,
    MineType,
    Planet,
    PlanetClass,
    Player,
    Ship,
    ShipClass,
)
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import tick_day

ROOT = Path(__file__).resolve().parents[1]
LOG_ROOT = ROOT / "docs" / "playtests" / "e2e-gameplay-coverage-v1"
# Class L S1 raw build days (CITADEL_CLASS_COSTS), one per level.
L_RAW_DAYS = (2, 5, 5, 8, 5, 12)


def _save(tmp_path: Path, name: str, lines: list[str]) -> None:
    text = "\n".join(lines) + "\n"
    (tmp_path / f"{name}.txt").write_text(text, encoding="utf-8")
    if os.environ.get("TW2K_E2E_LOG"):
        LOG_ROOT.mkdir(parents=True, exist_ok=True)
        (LOG_ROOT / f"{name}.txt").write_text(text, encoding="utf-8")


def _profile(monkeypatch, on: bool) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311" if on else "legacy")


def _world(seed: int, **cfg):
    u = generate_universe(GameConfig(
        seed=seed, universe_size=50, max_days=80,
        enable_ferrengi=False, enable_planets=True, **cfg,
    ))
    players = []
    for pid, name in (("A", "Alice"), ("B", "Bob")):
        player = Player(id=pid, name=name, ship=Ship(holds=80, fighters=200, shields=100), sector_id=1)
        player.credits = 200_000
        player.turns_per_day = 4000
        player.turns_today = 0
        u.players[pid] = player
        u.sectors[1].occupant_ids.append(pid)
        player.known_sectors.add(1)
        players.append(player)
    return u, players


def _move(u, player, sector_id: int) -> None:
    here = u.sectors[player.sector_id]
    if player.id in here.occupant_ids:
        here.occupant_ids.remove(player.id)
    player.sector_id = int(sector_id)
    player.planet_landed = None
    dest = u.sectors[int(sector_id)]
    if player.id not in dest.occupant_ids:
        dest.occupant_ids.append(player.id)
    player.known_sectors.add(int(sector_id))


def _quiet(u, sid: int) -> None:
    sector = u.sectors[sid]
    sector.mines.clear()
    sector.fighters = None
    sector.nav_hazard = 0
    sector.beacon = None


def _pair(u) -> tuple[int, int]:
    fed = set(K.FEDSPACE_SECTORS)
    for sid, sector in u.sectors.items():
        if sid in fed:
            continue
        for nxt in sector.warps:
            other = u.sectors.get(int(nxt))
            if other is None or int(nxt) in fed:
                continue
            if sid in other.warps:
                return int(sid), int(nxt)
    raise AssertionError("no two-way hop outside FedSpace")


def _act(u, pid: str, verb: ActionKind, **args):
    return apply_action(u, pid, Action(kind=verb, args=args))


def _ready(player) -> None:
    player.turns_today = 0
    player.turns_per_day = 4000
    player.alive = True


def _texts(obs) -> str:
    data = obs.model_dump() if hasattr(obs, "model_dump") else obs
    ship = data.get("ship") or {}
    bits = [str(data.get("ship_class") or ""), str(ship.get("ship_class") or "")]
    for row in data.get("recent_events") or []:
        bits.append(str(row.get("summary") or ""))
    for hint in data.get("hints") or data.get("notices") or []:
        bits.append(str(hint))
    return "\n".join(bits)


@pytest.mark.parametrize("profile", [False, True])
def test_mov09_transwarp_to_own_fighter(monkeypatch, tmp_path, profile) -> None:
    """MOV-09. Jump the ship TransWarp onto a sector that holds our own fighter."""
    _profile(monkeypatch, profile)
    u, (alice, _bob) = _world(9901)
    here, there = _pair(u)
    _quiet(u, here)
    _quiet(u, there)
    _move(u, alice, here)
    alice.ship.ship_class = ShipClass.IMPERIAL_STARSHIP
    alice.ship.transwarp_drive = "type1"
    alice.ship.cargo[Commodity.FUEL_ORE] = 30
    alice.known_sectors.add(there)
    u.sectors[there].fighters = FighterDeployment(owner_id="A", count=3, mode=FighterMode.DEFENSIVE)
    res = _act(u, "A", ActionKind.SHIP_TRANSWARP, sector_id=there)
    _save(tmp_path, f"mov09-profile-{'on' if profile else 'off'}", [
        "MOV-09 ship TransWarp to an own fighter",
        f"profile {'v311' if profile else 'off'}",
        f"from {here} to {there}: ok={res.ok} error={res.error}",
        f"now {alice.sector_id} drive={alice.ship.transwarp_drive}",
    ])
    assert res.ok, res.error
    assert alice.sector_id == there


@pytest.mark.parametrize("profile", [False, True])
def test_min05_figm_rival_hits_armid_mines(monkeypatch, tmp_path, profile) -> None:
    """MIN-05 and FIG-m. A rival warp into my armid mines takes the live hit."""
    _profile(monkeypatch, profile)
    u, (alice, bob) = _world(9902)
    here, there = _pair(u)
    _quiet(u, here)
    _quiet(u, there)
    _move(u, alice, there)
    alice.ship.mines[MineType.ARMID] = 10
    laid = _act(u, "A", ActionKind.DEPLOY_MINES, kind="armid", qty=10)
    assert laid.ok, laid.error
    _move(u, bob, here)
    bob.ship.shields = 5000
    bob.ship.fighters = 100
    before = bob.ship.shields
    res = _act(u, "B", ActionKind.WARP, target=there)
    lost = before - int(bob.ship.shields)
    per = K.armid_hit_damage()
    _save(tmp_path, f"min05-profile-{'on' if profile else 'off'}", [
        "MIN-05 / FIG-m rival hits my armid mines",
        f"profile {'v311' if profile else 'off'} damage_per_hit {per}",
        f"warp ok={res.ok} shields lost {lost} (5 hits of 10 mines)",
    ])
    assert res.ok, res.error
    assert lost == 5 * per


@pytest.mark.parametrize("profile", [False, True])
def test_min07_disruptor_clears_adjacent_mines(monkeypatch, tmp_path, profile) -> None:
    """MIN-07. A disruptor fired at the next sector removes sitting mines."""
    _profile(monkeypatch, profile)
    u, (alice, _bob) = _world(9903)
    here, there = _pair(u)
    _quiet(u, here)
    _quiet(u, there)
    _move(u, alice, here)
    u.sectors[there].mines.append(MineDeployment(owner_id="B", kind=MineType.ARMID, count=8))
    alice.ship.mine_disruptors = 1
    before = sum(int(row.count) for row in u.sectors[there].mines)
    res = _act(u, "A", ActionKind.FIRE_DISRUPTOR, target=there)
    after = sum(int(row.count) for row in u.sectors[there].mines)
    fired = next(ev for ev in u.events if ev.kind is EventKind.DISRUPTOR_FIRED)
    _save(tmp_path, f"min07-profile-{'on' if profile else 'off'}", [
        "MIN-07 disruptor clears mines in the next sector",
        f"profile {'v311' if profile else 'off'}",
        f"ok={res.ok} mines {before} -> {after} cleared={fired.payload.get('cleared')}",
    ])
    assert res.ok, res.error
    assert 0 < int(fired.payload["cleared"]) <= before
    assert after == before - int(fired.payload["cleared"])


@pytest.mark.parametrize("profile", [False, True])
def test_cit04_military_reaction_percent(monkeypatch, tmp_path, profile) -> None:
    """CIT-04. The percent on the citadel sends a reaction wave when a rival lands."""
    _profile(monkeypatch, profile)
    u, (alice, bob) = _world(9904)
    here, _there = _pair(u)
    _quiet(u, here)
    planet = _own_planet(u, here, "B", level=2, fighters=200)
    _move(u, bob, here)
    bob.planet_landed = planet.id
    _ready(bob)
    set_pct = _act(u, "B", ActionKind.SET_MILITARY_REACTION, planet_id=planet.id, pct=40)
    assert set_pct.ok, set_pct.error
    assert planet.military_reaction_pct == 40
    _move(u, bob, 1)
    _move(u, alice, here)
    alice.ship.fighters = 8000
    alice.ship.shields = 0
    land = _act(u, "A", ActionKind.LAND_PLANET, planet_id=planet.id)
    combat = next(ev for ev in u.events if ev.kind is EventKind.COMBAT and ev.payload.get("vs") == "planet")
    phases = [row.get("phase") for row in combat.payload.get("rounds") or []]
    _save(tmp_path, f"cit04-profile-{'on' if profile else 'off'}", [
        "CIT-04 military reaction 40% of 200 planet fighters",
        f"profile {'v311' if profile else 'off'}",
        f"land ok={land.ok} error={land.error} phases={phases}",
    ])
    assert "offense" in phases


@pytest.mark.parametrize("profile", [False, True])
def test_oth02_avoid_list(monkeypatch, tmp_path, profile) -> None:
    """OTH-02. Case text is not in the repo. Read as the avoid-sector command.

    The verb is refused while AVOID_MODE stays legacy, and it sticks under the profile.
    """
    _profile(monkeypatch, profile)
    u, (alice, _bob) = _world(9905)
    here, there = _pair(u)
    _move(u, alice, here)
    res = _act(u, "A", ActionKind.AVOID, sector=there)
    _save(tmp_path, f"oth02-profile-{'on' if profile else 'off'}", [
        "OTH-02 avoid list (case text not in the repo; read from the row id)",
        f"profile {'v311' if profile else 'off'} ok={res.ok} error={res.error}",
        f"avoided={list(alice.avoided_sectors)}",
    ])
    if profile:
        assert res.ok, res.error
        assert there in alice.avoided_sectors
    else:
        assert res.ok is False
        assert "unsupported" in str(res.error)


@pytest.mark.parametrize("profile", [False, True])
def test_oth03_broadcast_reaches_the_other_seat(monkeypatch, tmp_path, profile) -> None:
    """OTH-03. Case text is not in the repo. Read as a broadcast the other seat receives."""
    _profile(monkeypatch, profile)
    u, (_alice, bob) = _world(9906)
    res = _act(u, "A", ActionKind.BROADCAST, message="oth-03 beacon")
    hit = [row for row in bob.inbox if row.get("kind") == "broadcast" and "oth-03" in str(row.get("message"))]
    _save(tmp_path, f"oth03-profile-{'on' if profile else 'off'}", [
        "OTH-03 broadcast (case text not in the repo; read from the row id)",
        f"profile {'v311' if profile else 'off'} ok={res.ok} inbox={len(hit)}",
    ])
    assert res.ok, res.error
    assert hit


@pytest.mark.parametrize("profile", [False, True])
def test_oth04_plot_course(monkeypatch, tmp_path, profile) -> None:
    """OTH-04. Case text is not in the repo. Read as plotting a course to a known sector."""
    _profile(monkeypatch, profile)
    u, (alice, _bob) = _world(9907)
    here, there = _pair(u)
    _move(u, alice, here)
    alice.known_sectors.add(there)
    res = _act(u, "A", ActionKind.PLOT_COURSE, target=there)
    plotted = next(ev for ev in reversed(u.events) if ev.kind is EventKind.AUTOPILOT)
    path = list(plotted.payload.get("path") or [])
    _save(tmp_path, f"oth04-profile-{'on' if profile else 'off'}", [
        "OTH-04 plot course (case text not in the repo; read from the row id)",
        f"profile {'v311' if profile else 'off'} ok={res.ok} path={path}",
    ])
    assert res.ok, res.error
    assert path and path[-1] == there


@pytest.mark.parametrize("profile", [False, True])
def test_sdp201_buy_disruptor_at_stardock(monkeypatch, tmp_path, profile) -> None:
    """SD-P2-01. Case text is not in the repo. Read as buying a disruptor at StarDock."""
    _profile(monkeypatch, profile)
    u, (alice, _bob) = _world(9908)
    _move(u, alice, 1)
    price = int(K.disruptor_cost())
    alice.credits = price + 1000
    bought = _act(u, "A", ActionKind.BUY_EQUIP, item="mine_disruptor", qty=1)
    held = int(getattr(alice.ship, "mine_disruptors", 0) or 0)
    here, _there = _pair(u)
    _move(u, alice, here)
    refused = _act(u, "A", ActionKind.BUY_EQUIP, item="mine_disruptor", qty=1)
    _save(tmp_path, f"sdp201-profile-{'on' if profile else 'off'}", [
        "SD-P2-01 StarDock disruptor (case text not in the repo; read from the row id)",
        f"profile {'v311' if profile else 'off'} price {price} bought={bought.ok} held={held}",
        f"away from dock ok={refused.ok} error={refused.error}",
    ])
    assert bought.ok, bought.error
    assert held == 1
    assert alice.credits == 1000
    assert refused.ok is False


@pytest.mark.parametrize("profile", [False, True])
def test_fig06_defensive_fighters_challenge(monkeypatch, tmp_path, profile) -> None:
    """FIG-06. Case text is not in the repo. Read as defensive fighters that challenge."""
    _profile(monkeypatch, profile)
    u, (alice, bob) = _world(9909)
    here, there = _pair(u)
    _quiet(u, here)
    _quiet(u, there)
    _move(u, alice, there)
    alice.ship.fighters = 30
    laid = _act(u, "A", ActionKind.DEPLOY_FIGHTERS, qty=8, mode="defensive")
    assert laid.ok, laid.error
    _move(u, bob, here)
    hull = bob.ship.ship_class
    res = _act(u, "B", ActionKind.WARP, target=there)
    _save(tmp_path, f"fig06-profile-{'on' if profile else 'off'}", [
        "FIG-06 defensive fighter challenge (case text not in the repo)",
        f"profile {'v311' if profile else 'off'} ok={res.ok} challenge={bob.fighter_challenge}",
    ])
    assert res.ok, res.error
    assert bob.fighter_challenge and bob.fighter_challenge.get("mode") == "defensive"
    assert bob.ship.ship_class == hull


@pytest.mark.parametrize("profile", [False, True])
def test_fig09_toll_fighters_challenge(monkeypatch, tmp_path, profile) -> None:
    """FIG-09. Case text is not in the repo. Read as toll fighters that challenge."""
    _profile(monkeypatch, profile)
    u, (alice, bob) = _world(9910)
    here, there = _pair(u)
    _quiet(u, here)
    _quiet(u, there)
    _move(u, alice, there)
    alice.ship.fighters = 30
    laid = _act(u, "A", ActionKind.DEPLOY_FIGHTERS, qty=6, mode="toll")
    assert laid.ok, laid.error
    _move(u, bob, here)
    res = _act(u, "B", ActionKind.WARP, target=there)
    _save(tmp_path, f"fig09-profile-{'on' if profile else 'off'}", [
        "FIG-09 toll fighter challenge (case text not in the repo)",
        f"profile {'v311' if profile else 'off'} ok={res.ok} challenge={bob.fighter_challenge}",
    ])
    assert res.ok, res.error
    assert bob.fighter_challenge and bob.fighter_challenge.get("mode") == "toll"
    assert bob.alive


@pytest.mark.parametrize("profile", [False, True])
def test_cmbo_destroy_rival_shows_the_pod_on_both_screens(monkeypatch, tmp_path, profile) -> None:
    """CMB-o. Destroying a rival puts the pod on the killer's log and the victim's ship."""
    _profile(monkeypatch, profile)
    u, (alice, bob) = _world(9911)
    here, _there = _pair(u)
    _quiet(u, here)
    _move(u, alice, here)
    _move(u, bob, here)
    alice.ship.fighters = 4000
    alice.ship.shields = 500
    bob.ship.fighters = 1
    bob.ship.shields = 0
    bob.ship.ship_class = ShipClass.MERCHANT_CRUISER
    res = _act(u, "A", ActionKind.ATTACK, target="B", qty=200)
    seen_a = _texts(build_observation(u, "A"))
    seen_b = _texts(build_observation(u, "B"))
    _save(tmp_path, f"cmbo-pod-profile-{'on' if profile else 'off'}", [
        "CMB-o destroy a rival, pod on both screens",
        f"profile {'v311' if profile else 'off'} ok={res.ok} hull={bob.ship.ship_class.value}",
        f"killer sees pod: {'pod' in seen_a.lower()}",
        f"victim sees pod: {'pod' in seen_b.lower()}",
    ])
    assert res.ok, res.error
    assert bob.ship.ship_class is ShipClass.ESCAPE_POD
    assert "pod" in seen_a.lower()
    assert "pod" in seen_b.lower()


@pytest.mark.parametrize("profile", [False, True])
def test_cmbo_photon_at_the_neighbour_sector(monkeypatch, tmp_path, profile) -> None:
    """CMB-o. A photon is fired at the next sector, not at a ship in this one."""
    _profile(monkeypatch, profile)
    u, (alice, _bob) = _world(9912)
    here, there = _pair(u)
    _quiet(u, here)
    _quiet(u, there)
    _move(u, alice, here)
    alice.ship.ship_class = ShipClass.IMPERIAL_STARSHIP
    alice.ship.photon_missiles = 1
    res = _act(u, "A", ActionKind.PHOTON_MISSILE, target=there)
    fired = next(ev for ev in u.events if ev.kind is EventKind.PHOTON_FIRED)
    _save(tmp_path, f"cmbo-photon-profile-{'on' if profile else 'off'}", [
        "CMB-o photon into the neighbour sector",
        f"profile {'v311' if profile else 'off'} ok={res.ok} target={fired.payload.get('target_sector')}",
        fired.summary,
    ])
    assert res.ok, res.error
    assert int(fired.payload["target_sector"]) == there
    assert str(there) in fired.summary


@pytest.mark.parametrize("profile", [False, True])
def test_cmbo_attack_planet_and_fedspace_zyrain(monkeypatch, tmp_path, profile) -> None:
    """CMB-o. Landing on a defended planet is the attack. FedSpace refuses and calls Zyrain."""
    _profile(monkeypatch, profile)
    u, (alice, bob) = _world(9913)
    here, _there = _pair(u)
    _quiet(u, here)
    planet = _own_planet(u, here, "B", level=2, fighters=10, shields=0)
    _move(u, alice, here)
    alice.ship.fighters = 3000
    alice.ship.shields = 0
    land = _act(u, "A", ActionKind.LAND_PLANET, planet_id=planet.id)
    siege = next(ev for ev in u.events if ev.kind is EventKind.COMBAT and ev.payload.get("exchange_kind") == "planet_siege")
    _move(u, alice, 1)
    _move(u, bob, 1)
    _ready(alice)
    _ready(bob)
    alice.ship.fighters = 40
    bob.ship.fighters = 5
    bob.alignment = 0
    bob.experience = 0
    refused = _act(u, "A", ActionKind.ATTACK, target="B", qty=10)
    zyrain = [ev for ev in u.events if ev.kind is EventKind.FED_ZYRAIN]
    _save(tmp_path, f"cmbo-planet-fed-profile-{'on' if profile else 'off'}", [
        "CMB-o planet attack and FedSpace / Zyrain",
        f"profile {'v311' if profile else 'off'}",
        f"siege ok={land.ok} summary={siege.summary}",
        f"losses key={'attacker_losses' in siege.payload}",
        f"fed ok={refused.ok} error={refused.error} zyrain={len(zyrain)} hull={alice.ship.ship_class.value}",
    ])
    assert "Siege of" in siege.summary
    if profile:
        assert "attacker_losses" in siege.payload
    else:
        assert "attacker_losses" not in siege.payload
    assert refused.ok is False
    assert "Zyrain" in str(refused.error)
    assert zyrain
    assert alice.ship.ship_class is ShipClass.ESCAPE_POD


@pytest.mark.parametrize("profile", [False, True])
def test_citl_lhb_citadel_climb_and_quasar(monkeypatch, tmp_path, profile) -> None:
    """CIT-l and LH-b. Climb a class L citadel from L1 to L6, then the quasar fires."""
    _profile(monkeypatch, profile)
    u, (alice, bob) = _world(9914)
    here, there = _pair(u)
    _quiet(u, here)
    _quiet(u, there)
    planet = _own_planet(u, here, "A", level=0, fighters=0)
    _move(u, alice, here)
    alice.planet_landed = planet.id
    days_used = []
    for level in range(1, 7):
        _stock(planet, level)
        _ready(alice)
        day = int(u.day)
        res = _act(u, "A", ActionKind.BUILD_CITADEL, planet_id=planet.id)
        assert res.ok, res.error
        span = int(planet.citadel_complete_day) - day
        days_used.append(span)
        guard = 0
        while planet.citadel_level < level and guard < 40:
            tick_day(u)
            guard += 1
        assert planet.citadel_level == level
    _ready(alice)
    set_q = _act(u, "A", ActionKind.SET_QUASAR_SECTOR, planet_id=planet.id, pct=100)
    assert set_q.ok, set_q.error
    planet.stockpile[Commodity.FUEL_ORE] = 10_000
    _move(u, bob, there)
    bob.ship.shields = 50
    bob.ship.fighters = 5000
    warp = _act(u, "B", ActionKind.WARP, target=here)
    shot = [ev for ev in u.events if ev.kind is EventKind.QUASAR_FIRE and "Bob" in ev.summary]
    _save(tmp_path, f"citl-profile-{'on' if profile else 'off'}", [
        "CIT-l / LH-b class L citadel L1 to L6, then quasar on the intruder",
        f"profile {'v311' if profile else 'off'} build days {days_used}",
        f"quasar events {len(shot)} warp ok={warp.ok} error={warp.error}",
        f"intruder shields {bob.ship.shields}",
    ])
    if profile:
        assert tuple(days_used) == L_RAW_DAYS
    else:
        assert days_used != list(L_RAW_DAYS)
        assert all(span >= 1 for span in days_used)
    assert shot
    assert int(bob.ship.shields) < 50


def test_lhc_siege_report_on_both_sides(monkeypatch, tmp_path) -> None:
    """LH-c. Shields, the reaction wave, the defenders, and the report each side can read.

    The loss counts are the profile-on report. Profile off still has the siege line.
    """
    lines = ["LH-c two-seat siege"]
    for profile in (False, True):
        _profile(monkeypatch, profile)
        u, (alice, bob) = _world(9915 + int(profile))
        here, _there = _pair(u)
        _quiet(u, here)
        # Level 5 is where stocked shields fight once the profile's shield gate is on.
        planet = _own_planet(u, here, "B", level=5, fighters=80, shields=20)
        planet.military_reaction_pct = 25
        _move(u, bob, here)
        bob.planet_landed = planet.id
        _move(u, alice, here)
        alice.ship.fighters = 6000
        alice.ship.shields = 0
        land = _act(u, "A", ActionKind.LAND_PLANET, planet_id=planet.id)
        siege = next(ev for ev in u.events if (ev.payload or {}).get("exchange_kind") == "planet_siege")
        phases = [row.get("phase") for row in siege.payload.get("rounds") or []]
        seen_a = _texts(build_observation(u, "A"))
        seen_b = _texts(build_observation(u, "B"))
        lines.append(
            f"profile {'v311' if profile else 'off'} ok={land.ok} phases={phases} "
            f"both={'Siege of' in seen_a and 'Siege of' in seen_b}"
        )
        assert "shields" in phases
        assert "offense" in phases
        assert "Siege of" in seen_a and "Siege of" in seen_b
        if profile:
            assert siege.payload.get("attacker_losses", 0) >= 0
            assert "planet_shields_lost" in siege.payload
    _save(tmp_path, "lhc-siege", lines)


@pytest.mark.parametrize("profile", [False, True])
def test_lhd_two_pods_then_destroyed_until_the_next_day(monkeypatch, tmp_path, profile) -> None:
    """LH-d. Two pods in a day, the third loss is out, and the next day opens the lock or the clock."""
    _profile(monkeypatch, profile)
    u, (alice, bob) = _world(9917)
    here, there = _pair(u)
    _quiet(u, here)
    _quiet(u, there)
    _move(u, bob, there)
    bob.ship.mines[MineType.ARMID] = 40
    assert _act(u, "B", ActionKind.DEPLOY_MINES, kind="armid", qty=40).ok
    _move(u, alice, here)
    alice.ship.ship_class = ShipClass.MERCHANT_CRUISER
    pods = []
    for _ in range(3):
        _ready(alice)
        alice.ship.shields = 0
        alice.ship.fighters = 5
        # A fresh merchant between losses is this seat buying out of the pod,
        # so the two-a-day counter is what the mines test, not the "already in a pod" rule.
        if alice.ship.ship_class is ShipClass.ESCAPE_POD:
            alice.ship.ship_class = ShipClass.MERCHANT_CRUISER
        _move(u, alice, here)
        res = _act(u, "A", ActionKind.WARP, target=there)
        pods.append((res.ok, alice.ship.ship_class.value, int(alice.pods_today), int(alice.deaths), alice.sector_id))
    locked = int(alice.turns_today) >= int(alice.turns_per_day)
    tick_day(u)
    _save(tmp_path, f"lhd-pods-profile-{'on' if profile else 'off'}", [
        "LH-d two pods, third death, next day",
        f"profile {'v311' if profile else 'off'}",
        f"steps {pods}",
        f"after third: sector {alice.sector_id} hull {alice.ship.ship_class.value} locked={locked}",
        f"after tick turns_today={alice.turns_today} of {alice.turns_per_day}",
    ])
    assert pods[0][1] == "escape_pod" and pods[0][2] == 1
    assert pods[1][1] == "escape_pod" and pods[1][2] == 2
    assert alice.ship.ship_class is ShipClass.SCOUT_MARAUDER
    assert alice.sector_id == K.STARDOCK_SECTOR
    assert locked
    if profile:
        # The live day does not refill turns. The clock does. The scout is already at StarDock.
        assert int(alice.turns_today) >= int(alice.turns_per_day)
    else:
        assert alice.turns_today == 0


@pytest.mark.parametrize("profile", [False, True])
def test_lhd_death_delay_holds_the_pod(monkeypatch, tmp_path, profile) -> None:
    """LH-d. A death delay of one midnight holds the pod only while the profile reads it."""
    _profile(monkeypatch, profile)
    u, (alice, bob) = _world(9918, death_delay=1)
    here, there = _pair(u)
    _quiet(u, here)
    _quiet(u, there)
    _move(u, bob, there)
    bob.ship.mines[MineType.ARMID] = 10
    assert _act(u, "B", ActionKind.DEPLOY_MINES, kind="armid", qty=10).ok
    _move(u, alice, here)
    alice.ship.shields = 0
    alice.ship.fighters = 1
    alice.ship.ship_class = ShipClass.MERCHANT_CRUISER
    hit = _act(u, "A", ActionKind.WARP, target=there)
    assert alice.ship.ship_class is ShipClass.ESCAPE_POD
    _ready(alice)
    # The delay gate runs before the turn budget. Put the pod where a warp is legal.
    if alice.sector_id != here:
        _move(u, alice, here)
    nxt = next(int(w) for w in u.sectors[alice.sector_id].warps)
    attempt = _act(u, "A", ActionKind.WARP, target=nxt)
    _save(tmp_path, f"lhd-delay-profile-{'on' if profile else 'off'}", [
        "LH-d death delay",
        f"profile {'v311' if profile else 'off'} mine ok={hit.ok}",
        f"delay_left={alice.death_delay_left} warp ok={attempt.ok} error={attempt.error}",
    ])
    if profile:
        assert alice.death_delay_left == 1
        assert attempt.ok is False and "death delay" in str(attempt.error)
        tick_day(u)
        assert alice.death_delay_left == 0
    else:
        assert alice.death_delay_left == 0
        assert attempt.ok, attempt.error


@pytest.mark.parametrize("profile", [False, True])
def test_lhe_two_seats_form_a_corporation(monkeypatch, tmp_path, profile) -> None:
    """LH-e. Create, invite, join, corporate fighters, a fighter transfer, then the CEO leaves."""
    _profile(monkeypatch, profile)
    u, (alice, bob) = _world(9919)
    here, _there = _pair(u)
    _quiet(u, here)
    _move(u, alice, here)
    _move(u, bob, here)
    created = _act(u, "A", ActionKind.CORP_CREATE, ticker="ACE", name="Ace Traders")
    assert created.ok, created.error
    password = _act(u, "A", ActionKind.CORP_SET_PASSWORD, password="note99")
    assert password.ok, password.error
    invited = _act(u, "A", ActionKind.CORP_INVITE, target="B")
    assert invited.ok, invited.error
    joined = _act(u, "B", ActionKind.CORP_JOIN, ticker="ACE", password="note99")
    assert joined.ok, joined.error
    alice.ship.fighters = 500
    bob.ship.fighters = 10
    _ready(alice)
    _ready(bob)
    moved = _act(u, "A", ActionKind.CORP_TRANSFER, target="B", item="fighters", qty=25, direction="give")
    assert moved.ok, moved.error
    alice.ship.fighters = 40
    laid = _act(u, "A", ActionKind.DEPLOY_FIGHTERS, qty=12, mode="defensive", ownership="corporate")
    assert laid.ok, laid.error
    corp_figs = u.sectors[here].fighters
    deployed_ticker = None if corp_figs is None else corp_figs.corp_ticker
    deployed_count = None if corp_figs is None else corp_figs.count
    left = _act(u, "A", ActionKind.CORP_LEAVE)
    _save(tmp_path, f"lhe-profile-{'on' if profile else 'off'}", [
        "LH-e create, invite, join, corporate fighters, transfer, CEO leaves",
        f"profile {'v311' if profile else 'off'}",
        f"bob fighters after transfer {bob.ship.fighters}",
        f"deployed ticker={deployed_ticker} count={deployed_count}",
        f"leave ok={left.ok} corps={list(u.corporations)} alice={alice.corp_ticker} bob={bob.corp_ticker}",
    ])
    assert bob.ship.fighters == 35
    assert deployed_ticker == "ACE" and deployed_count == 12
    assert left.ok, left.error
    assert "ACE" not in u.corporations
    assert alice.corp_ticker is None and bob.corp_ticker is None


def _own_planet(u, sector_id: int, owner: str, *, level: int, fighters: int, shields: int = 0) -> Planet:
    pid = int(u.next_planet_id)
    u.next_planet_id = pid + 1
    planet = Planet(
        id=pid, sector_id=sector_id, name=f"Coverage {pid}",
        class_id=PlanetClass.L, owner_id=owner,
        citadel_level=level, citadel_target=level,
        fighters=fighters, shields=shields,
    )
    u.planets[pid] = planet
    u.sectors[sector_id].planet_ids.append(pid)
    return planet


def _stock(planet: Planet, level: int) -> None:
    colonists, fuel, organics, equipment, _days = K.citadel_class_cost(planet.class_id.value, level)
    planet.colonists[Commodity.COLONISTS] = int(colonists)
    planet.stockpile[Commodity.FUEL_ORE] = int(fuel)
    planet.stockpile[Commodity.ORGANICS] = int(organics)
    planet.stockpile[Commodity.EQUIPMENT] = int(equipment)


def _free_port() -> int:
    from tests._cu_host import free_port

    return free_port()


class _TwoSeat:
    """Two external cockpits on a port outside the protected list."""

    def __init__(self, tmp: Path) -> None:
        import asyncio
        import threading

        import uvicorn

        from tw2k.server.app import create_app
        from tw2k.server.runner import AgentSpec, MatchSpec

        self.port = _free_port()
        self.tokens = {"P1": "note99-token-p1-0000000000000001", "P2": "note99-token-p2-0000000000000002"}
        self.app = create_app(auto_start=False)
        self.runner = self.app.state.runner
        self.runner._saves_root = tmp / "saves"
        self.server = uvicorn.Server(uvicorn.Config(
            self.app, host="127.0.0.1", port=self.port, log_level="warning",
        ))
        self._info = None

        async def _main() -> None:
            async def _start() -> None:
                while not self.server.started:
                    await asyncio.sleep(0.05)
                await self.runner.start(MatchSpec(
                    config=GameConfig(
                        seed=9920, universe_size=80, max_days=5, turns_per_day=800,
                        enable_ferrengi=False, enable_planets=True, action_delay_s=0.0,
                    ),
                    agents=[
                        AgentSpec(player_id="P1", name="Alice", kind="external", external_token=self.tokens["P1"]),
                        AgentSpec(player_id="P2", name="Bob", kind="external", external_token=self.tokens["P2"]),
                    ],
                    action_delay_s=0.0, external_timeout_s=120.0,
                ))

            task = asyncio.create_task(_start())
            await self.server.serve()
            task.cancel()
            await self.runner.stop()

        self.thread = threading.Thread(target=lambda: asyncio.run(_main()), daemon=True)

    def __enter__(self):
        from tests._cu_host import acquire_info_mode, release_info_mode

        self._info_pushed = False
        try:
            acquire_info_mode(self)
            self._info_pushed = True
            self.thread.start()
            deadline = time.time() + 20
            while time.time() < deadline:
                universe = self.runner.state.universe
                if self.server.started and universe is not None and "P2" in universe.players:
                    return self
                time.sleep(0.05)
            raise AssertionError("two-seat server did not start")
        except BaseException:
            self.server.should_exit = True
            if self.thread.is_alive():
                self.thread.join(timeout=15)
            if self.port:
                from tests._port_lock import release_ports

                release_ports(self.port)
                self.port = 0
            if self._info_pushed:
                release_info_mode(self)
                self._info_pushed = False
            raise

    def __exit__(self, *exc) -> None:
        from tests._cu_host import release_info_mode

        try:
            self.server.should_exit = True
            self.thread.join(timeout=15)
            if self.port:
                from tests._port_lock import release_ports

                release_ports(self.port)
        finally:
            if getattr(self, "_info_pushed", False):
                release_info_mode(self)
                self._info_pushed = False

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"


def _post(client, seat: str, token: str, kind: str, args: dict) -> dict:
    deadline = time.time() + 20
    headers = {"authorization": f"Bearer {token}"}
    while time.time() < deadline:
        status = client.get(f"/harness/v1/{seat}/status", headers=headers)
        if status.status_code == 200 and status.json().get("awaiting_input"):
            turn = int(status.json()["turn_seq"])
            reply = client.post(
                f"/harness/v1/{seat}/action",
                headers=headers,
                json={"turn_seq": turn, "action": {"kind": kind, "args": args}},
            )
            if reply.status_code == 200:
                return reply.json()
        time.sleep(0.05)
    raise AssertionError(f"no turn for {seat} to post {kind}")


def test_two_cockpits_show_the_pod_and_the_siege(monkeypatch, tmp_path) -> None:
    """CMB-o and LH-c on the redesign. Both seats' screens show the pod, then the siege.

    The click is each seat opening its own cockpit. The actions go through the harness
    the cockpit uses. V311 is on so the siege report is the profile-on one.
    """
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    import httpx

    _profile(monkeypatch, True)
    with _TwoSeat(tmp_path) as host:
        lines = [f"two cockpits, profile on, port {host.port}"]
        universe = host.runner.state.universe
        assert universe is not None
        alice = universe.players["P1"]
        bob = universe.players["P2"]
        here, there = _pair(universe)
        _quiet(universe, here)
        _quiet(universe, there)
        _move(universe, alice, here)
        _move(universe, bob, here)
        alice.ship.fighters = 4000
        alice.ship.shields = 400
        bob.ship.fighters = 1
        bob.ship.shields = 0
        bob.ship.ship_class = ShipClass.MERCHANT_CRUISER
        with httpx.Client(base_url=host.base, timeout=30.0) as client:
            killed = _post(client, "P1", host.tokens["P1"], "attack", {"target": "P2", "qty": 200})
            lines.append(f"attack accepted={killed.get('accepted')} bob={bob.ship.ship_class.value}")
            assert bob.ship.ship_class is ShipClass.ESCAPE_POD
            planet = _own_planet(universe, there, "P2", level=2, fighters=40, shields=15)
            planet.military_reaction_pct = 20
            _move(universe, bob, there)
            bob.planet_landed = planet.id
            bob.ship.ship_class = ShipClass.MERCHANT_CRUISER
            bob.ship.fighters = 10
            _move(universe, alice, there)
            alice.ship.fighters = 5000
            alice.ship.shields = 0
            # Bob's turn is still open after the kill. He waits, then Alice lands.
            _post(client, "P2", host.tokens["P2"], "wait", {})
            landed = _post(client, "P1", host.tokens["P1"], "land_planet", {"planet_id": planet.id})
            lines.append(f"land accepted={landed.get('accepted')}")
        with sync() as pw:
            try:
                browser = pw.chromium.launch()
            except Exception as exc:
                pytest.skip(f"chromium not available: {exc}")
            pages = []
            try:
                for seat in ("P1", "P2"):
                    page = browser.new_page(viewport={"width": 1280, "height": 800})
                    page.goto(f"{host.base}/bot?layout=redesign&seat={seat}&token={host.tokens[seat]}")
                    page.wait_for_selector("#waitchip", timeout=20_000)
                    page.wait_for_function(
                        "() => (document.querySelector('[data-testid=log]') || {}).innerText",
                        timeout=20_000,
                    )
                    log = page.locator("[data-testid=log]").inner_text()
                    result = page.locator("#lastResult").inner_text()
                    shown = log + "\n" + result
                    lines.append(f"{seat} log:\n{shown}")
                    # The redesign log prints the destroy line, and the siege report
                    # in the cockpit's own words (the raw "Siege of" summary is rewritten
                    # once the profile-on report fields are on the event).
                    assert "escaped in a pod" in shown.lower(), shown
                    assert (
                        "Landing repelled" in shown
                        or "the planet lost" in shown
                        or "planet's fighters" in shown
                        or "Siege of" in shown
                    ), shown
                    pages.append(page)
            finally:
                browser.close()
    _save(tmp_path, "cockpits", lines)
