"""Unit tests for the Phase 4 /history ring buffer.

The MatchRunner maintains a per-player deque of sparkline samples
(credits, net worth, fighters, etc). These tests exercise it without
needing the FastAPI app or the asyncio loop — we instantiate the
runner, attach a minimal universe, and call the private sample /
snapshot helpers directly.
"""

from __future__ import annotations

from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.models import Player, Ship
from tw2k.server.broadcaster import Broadcaster
from tw2k.server.runner import MatchRunner


def _fresh_runner() -> MatchRunner:
    r = MatchRunner(Broadcaster())
    cfg = GameConfig(seed=7, universe_size=50, max_days=2)
    universe = generate_universe(cfg)
    # Universe.generate_universe() doesn't seed players — the runner does that
    # during agent build. For these unit tests we just inject two dummies so
    # the sampler has someone to record.
    for i, pid in enumerate(("P1", "P2")):
        universe.players[pid] = Player(
            id=pid,
            name=f"Test {pid}",
            ship=Ship(),
            sector_id=1,
            credits=1000 * (i + 1),
            color="#6ee7ff",
            agent_kind="heuristic",
        )
    r.state.universe = universe
    return r


def test_history_empty_snapshot_before_sampling():
    r = _fresh_runner()
    snap = r.history_snapshot()
    assert snap["max_samples"] == MatchRunner.HISTORY_MAX_SAMPLES
    assert snap["samples"] == {}


def test_history_records_one_sample_per_call():
    r = _fresh_runner()
    r._record_history_sample()
    snap = r.history_snapshot()
    # Every player should get exactly one sample.
    assert set(snap["samples"].keys()) == set(r.state.universe.players.keys())
    for pid, samples in snap["samples"].items():
        assert len(samples) == 1
        s = samples[0]
        # Required fields for the client sparklines.
        for k in ("seq", "day", "tick", "credits", "net_worth", "fighters",
                  "shields", "experience", "alignment", "sector_id", "alive"):
            assert k in s, f"sample for {pid} is missing {k}"


def test_history_ring_buffer_enforces_cap():
    r = _fresh_runner()
    # Use a tiny cap so we can check eviction without looping 240 times.
    r.HISTORY_MAX_SAMPLES = 5
    r._history.clear()
    for _ in range(12):
        r._record_history_sample()
    snap = r.history_snapshot()
    for samples in snap["samples"].values():
        assert len(samples) == 5  # capped


def test_history_limit_parameter_trims_output():
    r = _fresh_runner()
    for _ in range(8):
        r._record_history_sample()
    full = r.history_snapshot()
    limited = r.history_snapshot(limit=3)
    for pid in full["samples"]:
        assert len(limited["samples"][pid]) == 3
        # Returned slice should be the TAIL (most recent).
        assert limited["samples"][pid] == full["samples"][pid][-3:]


def test_history_samples_track_credit_changes():
    r = _fresh_runner()
    universe = r.state.universe
    pid = next(iter(universe.players.keys()))
    player = universe.players[pid]
    player.credits = 100
    r._record_history_sample()
    player.credits = 250
    r._record_history_sample()
    player.credits = 175
    r._record_history_sample()
    samples = r.history_snapshot()["samples"][pid]
    creds = [s["credits"] for s in samples]
    assert creds == [100, 250, 175]


def test_snapshot_planet_block_includes_colonists_and_stockpile():
    """The spectator UI's per-commander Planets section renders
    citadel progress, colonist pools, and commodity stockpile. Those
    three fields all live inside the `planets` array in the server
    snapshot. If a refactor drops them, the UI silently shows only
    names + treasury and the spectator can't tell if Citadel L2 is
    actually progressing.

    Locks the contract: every planet in snapshot()['planets'] must
    expose `colonists` (dict of commodity->int) and `stockpile`
    (dict of commodity->int), with the idle-colonists key present
    in `colonists`.
    """
    from tw2k.engine.models import Commodity, Planet, PlanetClass

    r = _fresh_runner()
    universe = r.state.universe
    # Seed a fake player-owned planet with a real idle pool + stockpile
    # so the test asserts non-empty structures, not just presence of keys.
    universe.planets[99] = Planet(
        id=99,
        sector_id=5,
        name="TestPlanet-99",
        class_id=PlanetClass.M,
        owner_id="P1",
        citadel_level=1,
        citadel_target=2,
        colonists={
            Commodity.FUEL_ORE: 120,
            Commodity.ORGANICS: 80,
            Commodity.EQUIPMENT: 40,
            Commodity.COLONISTS: 500,  # idle pool
        },
        stockpile={
            Commodity.FUEL_ORE: 25,
            Commodity.ORGANICS: 10,
            Commodity.EQUIPMENT: 5,
        },
        fighters=200,
        shields=50,
        treasury=4200,
    )
    snap = r.snapshot()
    planet_blocks = {pl["id"]: pl for pl in snap["planets"]}
    assert 99 in planet_blocks, "planet 99 must show up in snapshot"
    block = planet_blocks[99]
    assert block["name"] == "TestPlanet-99"
    assert block["owner_id"] == "P1"
    assert block["citadel_level"] == 1
    assert block["citadel_target"] == 2

    assert "colonists" in block, "UI planet section needs colonist pool"
    assert "stockpile" in block, "UI planet section needs stockpile"
    assert block["colonists"]["colonists"] == 500, "idle pool must surface"
    assert block["colonists"]["fuel_ore"] == 120
    assert block["stockpile"]["fuel_ore"] == 25
    assert block["fighters"] == 200
    assert block["treasury"] == 4200
