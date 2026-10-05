"""Independent QC plants for ship-hardware-v2 (fog leaks, ports, legacy harness)."""

from __future__ import annotations

import socket

import pytest

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.hardware import add_navhaz, apply_navhaz
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Commodity, Planet, PlanetClass, Player, Ship
from tw2k.engine.observation import build_observation


@pytest.fixture
def tw(monkeypatch):
    monkeypatch.setattr(K, "HARDWARE_MODE", "tw2002")


@pytest.fixture
def legacy(monkeypatch):
    monkeypatch.setattr(K, "HARDWARE_MODE", "legacy")


def _pair(seed: int = 9101):
    u = generate_universe(GameConfig(seed=seed, universe_size=60, enable_ferrengi=False, enable_planets=True))
    sid = next(
        s
        for s in sorted(u.sectors)
        if s > 10 and len(u.sectors[s].warps) >= 1 and all(w > 10 for w in u.sectors[s].warps)
    )
    adj = u.sectors[sid].warps[0]
    for s in (sid, adj):
        sec = u.sectors[s]
        sec.mines, sec.fighters, sec.planet_ids = [], None, []
        sec.nav_hazard = 0.0
        sec.beacon = None
    u.players["A"] = Player(
        id="A", name="Alpha", ship=Ship(holds=40, fighters=5, shields=5), sector_id=sid, credits=500_000
    )
    u.players["B"] = Player(
        id="B", name="Bravo", ship=Ship(holds=40, fighters=80, shields=40), sector_id=sid, credits=50_000
    )
    u.sectors[sid].occupant_ids.extend(["A", "B"])
    for p in ("A", "B"):
        u.players[p].known_sectors.update([sid, adj])
    return u, sid, adj


def test_plant_cloaked_navhaz_death_stays_hidden(tw) -> None:
    """Plant: NavHaz hit while cloaked becomes visible after death strips the cloak."""
    u, sid, _ = _pair()
    u.players["A"].ship.cloaked = True
    u.players["A"].ship.cloak_activated_day = u.day
    add_navhaz(u.sectors[sid], 100)

    class _Hit:
        def random(self) -> float:
            return 0.0

    apply_navhaz(u, "A", u.sectors[sid], _Hit())
    assert u.players["A"].deaths >= 1
    assert u.players["A"].ship.cloaked is False
    kinds = [e["kind"] for e in build_observation(u, "B").recent_events]
    assert "navhaz_hit" not in kinds


def test_plant_cloaked_detonator_backfire_stays_hidden(tw) -> None:
    """Plant: cloaked atomic backfire event leaks after the ship is stripped."""
    u, sid, _ = _pair()
    a = u.players["A"]
    a.ship.cloaked = True
    a.ship.cloak_activated_day = u.day
    a.ship.atomic_detonators = 1
    a.ship.fighters = 200
    a.ship.shields = 100
    pl = Planet(id=7701, sector_id=sid, name="Trap", class_id=PlanetClass.M, owner_id="B")
    pl.colonists[Commodity.FUEL_ORE] = 10
    pl.fighters = 0
    pl.shields = 0
    u.planets[pl.id] = pl
    u.sectors[sid].planet_ids.append(pl.id)
    a.planet_landed = pl.id
    r = apply_action(u, "A", Action(kind=ActionKind.DEPLOY_ATOMIC, args={"planet_id": pl.id}))
    assert r.ok
    assert a.deaths >= 1
    assert a.ship.cloaked is False
    kinds = [e["kind"] for e in build_observation(u, "B").recent_events]
    assert "atomic_detonator" not in kinds


def test_plant_beacon_author_not_in_rival_obs(tw) -> None:
    u, sid, _ = _pair(9102)
    # Put B next door so they only learn via sector/scan, not the launch event.
    u.sectors[sid].occupant_ids.remove("B")
    u.players["B"].sector_id = u.sectors[sid].warps[0]
    u.sectors[u.players["B"].sector_id].occupant_ids.append("B")
    u.players["A"].ship.marker_beacons = 2
    assert apply_action(u, "A", Action(kind=ActionKind.LAUNCH_BEACON, args={"message": "ghost drop"})).ok
    blob = str(build_observation(u, "B").model_dump(mode="json"))
    assert "ghost drop" not in blob  # B is not in the sector yet
    assert "BEACON" not in blob.upper() or "beacon_launched" not in blob
    # Move B in: text is visible, author is not.
    dest = sid
    u.sectors[u.players["B"].sector_id].occupant_ids.remove("B")
    u.players["B"].sector_id = dest
    u.sectors[dest].occupant_ids.append("B")
    obs = build_observation(u, "B").model_dump(mode="json")
    assert obs["sector"].get("beacon") == "ghost drop"
    # Beacon text only — no owner field on the sector / event trail for the rival.
    assert "owner" not in (obs["sector"] or {})
    assert not any(e["kind"] in ("beacon_launched", "beacon_destroyed") for e in obs["recent_events"])


def test_plant_corbomite_count_hidden_from_rival(tw) -> None:
    u, sid, _ = _pair(9103)
    u.players["A"].ship.corbomite = 1500
    blob = str(build_observation(u, "B").model_dump(mode="json"))
    assert "1500" not in blob or '"corbomite"' not in blob
    assert '"corbomite"' not in blob


def test_plant_psychic_probe_private(tw) -> None:
    from tw2k.engine.hardware import emit_psychic_probe

    u, sid, _ = _pair(9104)
    u.players["A"].ship.psychic_probe = 1
    emit_psychic_probe(u, "A", "fuel_ore", "sell", 20, 18, 5)
    assert any(e["kind"] == "psychic_probe" for e in build_observation(u, "A").recent_events)
    assert not any(e["kind"] == "psychic_probe" for e in build_observation(u, "B").recent_events)


def test_plant_legacy_harness_hides_deploy_atomic(legacy) -> None:
    from pathlib import Path

    src = Path(__file__).resolve().parents[1].joinpath("src/tw2k/server/harness.py").read_text(encoding="utf-8")
    # /rules filters both new verbs under HARDWARE_MODE legacy.
    assert "deploy_atomic" in src
    block = src.split("if not K.hardware_tw2002():", 1)[1].split("return {", 1)[0]
    assert "launch_beacon" in block and "deploy_atomic" in block
    # Legal list still carries the historical illegal stub (builder pin).
    u, _, _ = _pair(9105)
    las = {a.kind: a for a in legal_actions(u, "A")}
    assert "launch_beacon" not in las
    assert las["deploy_atomic"].legal is False
    assert "not a dispatched verb" in las["deploy_atomic"].reason


def test_plant_navhaz_persists_across_day_partial_decay(tw) -> None:
    from tw2k.engine.hardware import navhaz_pct
    from tw2k.engine.runner import tick_day

    u, sid, _ = _pair(9106)
    add_navhaz(u.sectors[sid], 40)
    assert navhaz_pct(u.sectors[sid]) == 40
    tick_day(u)
    assert navhaz_pct(u.sectors[sid]) == 37  # -3 dispersion


def test_plant_entry_order_navhaz_before_limpet(tw) -> None:
    """NavHaz death must prevent limpet attach (entry order)."""
    from tw2k.engine.hardware import limpets_on_target
    from tw2k.engine.models import MineDeployment, MineType

    u, sid, adj = _pair(9107)
    u.sectors[sid].occupant_ids.remove("B")
    u.players["B"].sector_id = adj
    u.sectors[adj].occupant_ids.append("B")
    # Hostile limpet waiting in adj; lethal NavHaz too.
    u.sectors[adj].mines = [MineDeployment(owner_id="B", kind=MineType.LIMPET, count=3)]
    add_navhaz(u.sectors[adj], 100)
    u.players["A"].ship.fighters = 1
    u.players["A"].ship.shields = 1
    u.players["A"].turns_today = 0

    # Force NavHaz hit via warp
    class _Hit:
        def random(self):
            return 0.0

        def randint(self, a, b):
            return a

        def choice(self, seq):
            return seq[0]

    import tw2k.engine.runner as runner

    real = runner._rng_for
    runner._rng_for = lambda universe: _Hit()  # type: ignore[assignment]
    try:
        r = apply_action(u, "A", Action(kind=ActionKind.WARP, args={"target": adj}))
    finally:
        runner._rng_for = real
    assert r.ok
    assert u.players["A"].deaths >= 1
    assert limpets_on_target(u, "A") == []


def test_free_port_skips_reserved_live_range() -> None:
    from tests._cu_host import RESERVED_TEST_PORTS, free_port

    assert frozenset(range(8031, 8037)) == RESERVED_TEST_PORTS
    # Occupy 8040 so the helper must walk past it; still must never return 8031-8036.
    held = []
    try:
        for p in range(8040, 8045):
            s = socket.socket()
            s.bind(("127.0.0.1", p))
            held.append(s)
        # Default start is 8040; with 8040-8044 held, next free is >=8045.
        got = free_port()
        assert got not in RESERVED_TEST_PORTS
        assert got >= 8045
        # Even if asked to start inside the reserved band, never return 8031-8036.
        got2 = free_port(start=8031)
        assert got2 not in RESERVED_TEST_PORTS
    finally:
        for s in held:
            s.close()


def test_scanners_legacy_golden_delta_is_own_ship_and_legal_only(tw, monkeypatch) -> None:
    """Builder claim: INFO-legacy golden regen is only new own-ship keys + legal entries.

    Under HARDWARE_MODE legacy those keys/verbs stay hidden (no legacy exposure).
    """
    monkeypatch.setattr(K, "INFO_MODE", "legacy")
    monkeypatch.setattr(K, "RANK_MODE", "legacy")
    monkeypatch.setattr(K, "ROB_MODE", "legacy")
    monkeypatch.setattr(K, "HARDWARE_MODE", "legacy")
    u, _, _ = _pair(9200)
    ship = build_observation(u, "A").model_dump(mode="json")["ship"]
    for k in (
        "corbomite",
        "marker_beacons",
        "psychic_probe",
        "atomic_detonators",
        "cloaks",
        "mine_disruptors",
        "cloaked",
    ):
        assert k not in ship
    kinds = {a["kind"] for a in build_observation(u, "A").model_dump(mode="json")["legal_actions"]}
    assert "launch_beacon" not in kinds
