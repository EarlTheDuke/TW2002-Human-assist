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
