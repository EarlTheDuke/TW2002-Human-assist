"""V8 custom queue with a fake provider. No network and no paid call."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import threading
import time
from pathlib import Path

import pytest

from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.models import _MEDIA_CUSTOM_HOOK, EventKind, Player, Ship
from tw2k.media.custom_queue import (
    DAY_CAP_CENTS,
    JOBS_PER_MATCH,
    MATCH_CAP_CENTS,
    FakeProvider,
    current,
    prompt_for,
    start_if_enabled,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "web" / "media" / "manifest.json"
NODE = shutil.which("node")


class Gate:
    def __init__(self) -> None:
        self.calls = 0
        self.threads: list[int] = []
        self.started = threading.Event()
        self.release = threading.Event()

    def __call__(self, job: dict) -> bytes:
        self.calls += 1
        self.threads.append(threading.get_ident())
        self.started.set()
        assert self.release.wait(5)
        return b"fake-webm"


def _wait(pred, timeout: float = 3) -> None:
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return
        time.sleep(0.02)
    raise AssertionError("timed out")


def _universe():
    cfg = GameConfig(seed=2026, universe_size=50, max_days=5)
    u = generate_universe(cfg)
    a = Player(id="A", name="Alice", ship=Ship(holds=20), sector_id=1)
    b = Player(id="B", name="BobSecretName", ship=Ship(holds=20), sector_id=2)
    u.players["A"] = a
    u.players["B"] = b
    u.sectors[1].occupant_ids.append("A")
    u.sectors[2].occupant_ids.append("B")
    return u, a, b


def _citadel(u, level: int, **extra):
    payload = {"planet_id": 7, "from": level - 1, "to": level, "secret_scan": "HIDDENINTEL"}
    payload.update(extra)
    return u.emit(
        EventKind.CITADEL_COMPLETE,
        actor_id="A",
        sector_id=1,
        payload=payload,
        summary="BobSecretName should not be in the prompt",
    )


def test_flag_off_starts_nothing(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("TW2K_VIDEO_CUSTOM", raising=False)
    running = current()
    if running is not None:
        running.stop()
    assert start_if_enabled(tmp_path) is None
    assert _MEDIA_CUSTOM_HOOK is None
    assert current() is None
    assert not any(tmp_path.iterdir())


def test_manifest_flags_three_rare_keys() -> None:
    triggers = [t for t in json.loads(MANIFEST.read_text(encoding="utf-8"))["triggers"] if t.get("custom")]
    keys = {t["clip"] for t in triggers}
    assert keys == {"planet.genesis", "planet.citadel", "self.ship_destroyed"}
    citadel = next(t for t in triggers if t["clip"] == "planet.citadel")
    assert citadel["custom_only"] is True


def test_defaults_are_one_dollar_and_five_dollars() -> None:
    assert MATCH_CAP_CENTS == 100
    assert DAY_CAP_CENTS == 500
    assert JOBS_PER_MATCH == 3


def test_emit_returns_before_the_slow_provider(tmp_path) -> None:
    gate = Gate()
    from tw2k.media.custom_queue import CustomQueue

    q = CustomQueue(tmp_path, gate).start()
    try:
        u, _, _ = _universe()
        game = threading.get_ident()
        started = time.perf_counter()
        ev = _citadel(u, 1)
        elapsed = time.perf_counter() - started
        assert elapsed < 0.25
        assert ev in u.events
        assert q.placeholder("A", ev.seq) == "planet.citadel"
        assert gate.started.wait(2)
        assert game not in gate.threads
    finally:
        gate.release.set()
        q.stop()


def test_fourth_job_is_refused_and_logged(tmp_path, caplog) -> None:
    from tw2k.media.custom_queue import CustomQueue

    provider = FakeProvider()
    q = CustomQueue(tmp_path, provider).start()
    try:
        u, _, _ = _universe()
        with caplog.at_level(logging.WARNING, logger="tw2k.media.custom"):
            for level in (1, 2, 3, 4):
                _citadel(u, level)
        assert "match cap" in caplog.text
        _wait(lambda: provider.calls == 3)
        assert provider.calls == 3
    finally:
        q.stop()


def test_day_cap_is_refused(tmp_path, caplog) -> None:
    from tw2k.media.custom_queue import CustomQueue

    provider = FakeProvider()
    q = CustomQueue(tmp_path, provider, day_cap_cents=50).start()
    try:
        u, _, _ = _universe()
        with caplog.at_level(logging.WARNING, logger="tw2k.media.custom"):
            _citadel(u, 1)
            _citadel(u, 2)
        assert "day cap" in caplog.text
        _wait(lambda: provider.calls == 1)
        assert provider.calls == 1
    finally:
        q.stop()


def test_identical_prompt_does_not_call_the_provider_twice(tmp_path) -> None:
    from tw2k.media.custom_queue import CustomQueue

    provider = FakeProvider()
    q = CustomQueue(tmp_path, provider).start()
    try:
        u, _, _ = _universe()
        _citadel(u, 1)
        _wait(lambda: provider.calls == 1)
        _wait(lambda: any(tmp_path.glob("*.webm")))
        _citadel(u, 1)
        time.sleep(0.2)
        assert provider.calls == 1
    finally:
        q.stop()


def test_a_seat_runs_one_job_at_a_time(tmp_path) -> None:
    from tw2k.media.custom_queue import CustomQueue

    gate = Gate()
    q = CustomQueue(tmp_path, gate).start()
    try:
        u, _, _ = _universe()
        _citadel(u, 1)
        _citadel(u, 2)
        assert gate.started.wait(2)
        time.sleep(0.15)
        assert gate.calls == 1
        gate.release.set()
        _wait(lambda: gate.calls == 2)
    finally:
        gate.release.set()
        q.stop()


def test_one_provider_call_while_the_same_hash_is_in_flight(tmp_path) -> None:
    from tw2k.media.custom_queue import CustomQueue

    gate = Gate()
    q = CustomQueue(tmp_path, gate).start()
    try:
        u, _, _ = _universe()
        _citadel(u, 1)
        assert gate.started.wait(2)
        _citadel(u, 1)
        time.sleep(0.1)
        assert gate.calls == 1
    finally:
        gate.release.set()
        q.stop()


def test_late_clip_stays_in_the_seat_reel(tmp_path) -> None:
    from tw2k.media.custom_queue import CustomQueue

    gate = Gate()
    q = CustomQueue(tmp_path, gate, manifest_path=MANIFEST).start()
    before = MANIFEST.read_bytes()
    try:
        u, _, _ = _universe()
        ev = _citadel(u, 1)
        assert gate.started.wait(2)
        u.emit(EventKind.WARP, actor_id="A", sector_id=1, payload={"from": 1, "to": 2}, summary="warp")
        gate.release.set()
        _wait(lambda: (q.job_for("A", ev.seq) or {}).get("status") == "late")
        moments = q.moments_for("A")
        assert moments and moments[0]["trust"] == "auto" and moments[0]["badge"] == "live-generated"
        assert moments[0]["approved_by"] is None and moments[0]["swap"] is False
        assert q.moments_for("B") == []
        assert q.promote_to_library(moments[0]["hash"]) is False
        assert MANIFEST.read_bytes() == before
    finally:
        gate.release.set()
        q.stop()


def test_ready_clip_can_swap_only_while_the_placeholder_shows(tmp_path) -> None:
    from tw2k.media.custom_queue import CustomQueue

    gate = Gate()
    q = CustomQueue(tmp_path, gate).start()
    try:
        u, _, _ = _universe()
        ev = _citadel(u, 1)
        assert gate.started.wait(2)
        gate.release.set()
        _wait(lambda: (q.job_for("A", ev.seq) or {}).get("status") == "ready")
        feed = q.feed_for("A")
        assert feed["ready"][0]["swap"] is True and feed["ready"][0]["placeholder"] == "planet.citadel"
        assert feed["moments"] == []
        assert q.clip_bytes("B", feed["ready"][0]["hash"]) is None
        assert q.clip_bytes("A", feed["ready"][0]["hash"]) == b"fake-webm"
    finally:
        gate.release.set()
        q.stop()


def test_prompts_omit_facts_the_seat_cannot_see() -> None:
    u, a, _ = _universe()
    samples = [
        _citadel(u, 1),
        u.emit(
            EventKind.GENESIS_DEPLOYED,
            actor_id="A",
            sector_id=1,
            payload={"planet_id": 3, "class": "M", "name": "Eden", "secret_scan": "HIDDENINTEL"},
            summary="BobSecretName detonated a Genesis",
        ),
        u.emit(
            EventKind.SHIP_DESTROYED,
            actor_id="B",
            sector_id=1,
            payload={"victim": "A", "reason": "guns", "secret_scan": "HIDDENINTEL", "_witnesses": ["A"]},
            summary="BobSecretName destroyed a ship",
        ),
    ]
    for ev in samples:
        text = json.dumps(prompt_for(u, a.id, ev, "planet.citadel"))
        assert "HIDDENINTEL" not in text
        assert "BobSecretName" not in text
        assert "_witnesses" not in text
        assert "secret_scan" not in text


def test_a_hidden_seat_gets_no_job(tmp_path) -> None:
    from tw2k.media.custom_queue import CustomQueue

    provider = FakeProvider()
    q = CustomQueue(tmp_path, provider).start()
    try:
        u, _, _ = _universe()
        ev = u.emit(
            EventKind.SHIP_DESTROYED,
            actor_id="B",
            sector_id=1,
            payload={"victim": "A", "reason": "guns"},
            summary="destroyed",
        )
        assert q.placeholder("A", ev.seq) == "self.ship_destroyed"
        assert q.placeholder("B", ev.seq) is None
        first = u.emit(
            EventKind.GENESIS_DEPLOYED,
            actor_id="A",
            sector_id=1,
            payload={"planet_id": 4, "class": "K", "name": "First"},
            summary="first",
        )
        second = u.emit(
            EventKind.GENESIS_DEPLOYED,
            actor_id="A",
            sector_id=1,
            payload={"planet_id": 5, "class": "M", "name": "Later"},
            summary="again",
        )
        assert q.placeholder("A", first.seq) == "planet.genesis"
        assert q.placeholder("A", second.seq) is None
    finally:
        q.stop()


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_client_skips_custom_only_and_refuses_a_late_swap() -> None:
    script = r"""
const fs = require('fs');
const R = require(process.argv[1]);
const m = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const obs = {self_id:'A', sector:{id:1}};
const cit = [{seq:1, kind:'citadel_complete', actor_id:'A', sector_id:1, facts:{planet_id:7, from:0, to:1}}];
const off = R.resolve(cit, obs, {}, m);
const on = R.resolve(cit, obs, {videoCustom:true}, m);
const gen = R.resolve([{seq:2, kind:'genesis_deployed', actor_id:'A', sector_id:1, facts:{planet_id:3, class:'M', name:'Eden'}}], obs, {}, m);
const note = {swap:true, placeholder:'planet.citadel', seq:1, trust:'auto', approved_by:null, hash:'abc'};
const late = {swap:false, placeholder:'planet.citadel', seq:1, trust:'auto', approved_by:null, hash:'abc'};
process.stdout.write(JSON.stringify({
  off: off.map(h => h.clip_key),
  on: on.map(h => h.clip_key),
  gen: gen.map(h => h.clip_key),
  swap: R.considerCustomSwap('planet.citadel', note, 1, 1),
  gone: R.considerCustomSwap(null, note, 1, 1),
  newer: R.considerCustomSwap('planet.citadel', note, 4, 1),
  hot: R.considerCustomSwap('planet.citadel', note, 1, 4),
  late: R.considerCustomSwap('planet.citadel', late, 1, 1),
  card: R.momentCard(late),
  library: R.momentCard({trust:'auto', approved_by:'Ben', hash:'abc'})
}));
"""
    got = json.loads(subprocess.run(
        [NODE, "-e", script, str(ROOT / "web" / "media-resolver.js"), str(MANIFEST)],
        capture_output=True, text=True, check=True, timeout=30,
    ).stdout)
    assert got["off"] == []
    assert got["on"] == ["planet.citadel"]
    assert got["gen"] == ["planet.genesis"]
    assert got["swap"] is True and got["gone"] is False and got["newer"] is False and got["hot"] is False
    assert got["late"] is False
    assert got["card"]["badge"] == "live-generated" and got["card"]["trust"] == "auto"
    assert got["library"] is None
