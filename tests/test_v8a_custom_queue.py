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
        again = _citadel(u, 1)
        time.sleep(0.2)
        assert provider.calls == 1
        cached = q.feed_for("A")
        assert any(note["status"] == "cached" and note["swap"] is True for note in cached["ready"])
        assert q.placeholder("A", again.seq) == "planet.citadel"
    finally:
        q.stop()


def test_a_cache_hit_does_not_skip_a_running_job(tmp_path) -> None:
    from tw2k.media.custom_queue import CustomQueue

    warmed = tmp_path / "warm"
    provider = FakeProvider()
    q = CustomQueue(warmed, provider).start()
    try:
        u, _, _ = _universe()
        _citadel(u, 1)
        _wait(lambda: provider.calls == 1)
        _wait(lambda: any(warmed.glob("*.webm")))
    finally:
        q.stop()

    live = tmp_path / "live"
    live.mkdir()
    for webm in warmed.glob("*.webm"):
        (live / webm.name).write_bytes(webm.read_bytes())
    gate = Gate()
    q = CustomQueue(live, gate).start()
    try:
        u, _, _ = _universe()
        _citadel(u, 2)
        assert gate.started.wait(2)
        hit = _citadel(u, 1)
        early = q.feed_for("A")
        assert early["ready"] == [] and early["moments"] == []
        assert early["next_since"] == 0
        assert q.placeholder("A", hit.seq) == "planet.citadel"
        gate.release.set()
        _wait(lambda: q.feed_for("A")["ready"] or q.feed_for("A")["moments"])
        done = q.feed_for("A")
        statuses = {note["status"] for note in done["ready"] + done["moments"]}
        assert {"late", "cached"} <= statuses
        later = q.feed_for("A", done["next_since"])
        assert later["ready"] == [] and later["moments"] == []
    finally:
        gate.release.set()
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


def test_complete_citadels_reaches_the_owner(tmp_path) -> None:
    from tw2k.engine.models import Planet, PlanetClass
    from tw2k.engine.planets import _complete_citadels
    from tw2k.media.custom_queue import CustomQueue

    provider = FakeProvider()
    u, a, b = _universe()
    c = Player(id="C", name="Witness", ship=Ship(holds=20), sector_id=5)
    u.players["C"] = c
    u.sectors[5].occupant_ids.append("C")
    a.sector_id = 1
    planet = Planet(
        id=7, sector_id=5, name="Haven", class_id=PlanetClass.M, owner_id="A",
        citadel_level=0, citadel_target=1, citadel_complete_day=1,
    )
    u.planets[7] = planet
    u.day = 1
    q = CustomQueue(tmp_path, provider).start()
    try:
        _complete_citadels(u)
        ev = next(e for e in u.events if e.kind == EventKind.CITADEL_COMPLETE)
        assert ev.actor_id is None
        assert q.placeholder("A", ev.seq) == "planet.citadel"
        assert q.placeholder("B", ev.seq) is None
        assert q.placeholder("C", ev.seq) is None
        _wait(lambda: provider.calls == 1)
    finally:
        q.stop()


def test_flag_off_citadel_matches_the_engine_without_an_actor() -> None:
    from types import SimpleNamespace

    from tw2k.agents.seat_brain import SeatBrain
    from tw2k.engine.models import Planet, PlanetClass
    from tw2k.engine.observation import event_view
    from tw2k.engine.planets import _complete_citadels

    emit = (ROOT / "src/tw2k/engine/planets.py").read_text(encoding="utf-8")
    body = emit.split("EventKind.CITADEL_COMPLETE", 1)[1].split("summary=", 1)[0]
    assert "actor_id" not in body
    u, a, _ = _universe()
    for planet in u.planets.values():
        planet.citadel_complete_day = None
    u.planets[7] = Planet(
        id=7, sector_id=5, name="Haven", class_id=PlanetClass.M, owner_id="A",
        citadel_level=0, citadel_target=1, citadel_complete_day=1,
    )
    u.day = 1
    _complete_citadels(u)
    ev = next(e for e in u.events if e.kind == EventKind.CITADEL_COMPLETE)
    view = event_view(ev)
    assert json.dumps({"actor_id": view["actor_id"]}) == '{"actor_id": null}'
    witness = SimpleNamespace(rivals=[], net_worth=0, self_id="C", events=[view], worlds=lambda: [])
    assert SeatBrain._rival_pressure(None, witness) is None
    stamped = dict(view)
    stamped["actor_id"] = "A"
    pressured = SimpleNamespace(rivals=[], net_worth=0, self_id="C", events=[stamped], worlds=lambda: [])
    got = SeatBrain._rival_pressure(None, pressured)
    assert got and "citadel_complete" in got["empire_signals"]


def test_an_engine_citadel_does_not_late_another_job(tmp_path) -> None:
    from tw2k.engine.models import Planet, PlanetClass
    from tw2k.engine.planets import _complete_citadels
    from tw2k.media.custom_queue import CustomQueue

    gate = Gate()
    q = CustomQueue(tmp_path, gate).start()
    try:
        u, a, _ = _universe()
        first = _citadel(u, 1)
        assert gate.started.wait(2)
        for planet in u.planets.values():
            planet.citadel_complete_day = None
        u.planets[8] = Planet(
            id=8, sector_id=5, name="Haven", class_id=PlanetClass.M, owner_id="A",
            citadel_level=0, citadel_target=1, citadel_complete_day=1,
        )
        a.sector_id = 1
        u.day = 1
        _complete_citadels(u)
        gate.release.set()
        _wait(lambda: (q.job_for("A", first.seq) or {}).get("status") == "ready")
    finally:
        gate.release.set()
        q.stop()


def test_a_restart_expires_a_job_left_running(tmp_path) -> None:
    from tw2k.media.custom_queue import CustomQueue

    gate = Gate()
    q = CustomQueue(tmp_path, gate).start()
    u, _, _ = _universe()
    _citadel(u, 1)
    assert gate.started.wait(2)
    q.stop()
    q2 = CustomQueue(tmp_path, FakeProvider()).start()
    try:
        u2, _, _ = _universe()
        _citadel(u2, 2)
        _wait(lambda: q2.feed_for("A")["ready"])
        assert q2.feed_for("A", -4)["ready"]
        assert q2.feed_for("A", 10**9)["ready"]
        q2._conn.execute(
            """INSERT INTO jobs (hash, seat, match_id, status, created, cost_cents, trigger_seq, clip_key, day, swap)
               VALUES ('old', 'A', 'm', 'running', ?, 0, 1, 'planet.citadel', '2026-09-28', 0)""",
            (time.time() - 700,),
        )
        q2._conn.commit()
        q2._expire_deadlines()
        assert q2._conn.execute("SELECT status FROM jobs WHERE hash='old'").fetchone()["status"] == "expired"
    finally:
        gate.release.set()
        q2.stop()


def test_finish_does_not_revive_an_expired_job(tmp_path) -> None:
    from tw2k.media.custom_queue import CustomQueue

    gate = Gate()
    q = CustomQueue(tmp_path, gate).start()
    try:
        u, _, _ = _universe()
        _citadel(u, 1)
        assert gate.started.wait(2)
        q._conn.execute("UPDATE jobs SET status='expired', swap=0 WHERE status='running'")
        q._conn.commit()
        row = q._conn.execute("SELECT * FROM jobs").fetchone()
        assert row["status"] == "expired"
        q._finish(row, b"fake-webm")
        again = q._conn.execute("SELECT status, swap FROM jobs WHERE id=?", (row["id"],)).fetchone()
        assert again["status"] == "expired" and again["swap"] == 0
        assert not (tmp_path / f"{row['hash']}.webm").exists()
        assert not (tmp_path / f"{row['hash']}.json").exists()
    finally:
        gate.release.set()
        q.stop()


def test_a_failed_cache_write_removes_the_clip(tmp_path, monkeypatch) -> None:
    from tw2k.media.custom_queue import CustomQueue

    q = CustomQueue(tmp_path, FakeProvider())
    q._conn.execute(
        """INSERT INTO jobs (hash, seat, match_id, status, created, cost_cents, trigger_seq, clip_key, day, swap)
           VALUES ('abcd', 'A', 'm', 'running', ?, 33, 1, 'planet.genesis', '2026-09-28', 0)""",
        (time.time(),),
    )
    q._conn.commit()
    row = q._conn.execute("SELECT * FROM jobs WHERE hash='abcd'").fetchone()
    original = Path.write_bytes

    def boom(self, data):
        if self.suffix == ".webm":
            original(self, data)
            raise OSError("disk")
        return original(self, data)

    monkeypatch.setattr(Path, "write_bytes", boom)
    q._finish(row, b"fake-webm")
    assert not (tmp_path / "abcd.webm").exists()
    assert not (tmp_path / "abcd.json").exists()
    status = q._conn.execute("SELECT status, swap FROM jobs WHERE hash='abcd'").fetchone()
    assert status["status"] == "discarded" and status["swap"] == 0
    q.stop()


def test_emit_with_the_queue_stays_close_to_flag_off(tmp_path) -> None:
    from tw2k.media.custom_queue import CustomQueue

    u, _, _ = _universe()

    def burst() -> float:
        started = time.perf_counter()
        for n in range(12):
            _citadel(u, n + 1)
        return time.perf_counter() - started

    off = burst()
    gate = Gate()
    q = CustomQueue(tmp_path, gate).start()
    try:
        on = burst()
    finally:
        gate.release.set()
        q.stop()
    assert on < off + 0.15


def test_prompts_omit_facts_the_seat_cannot_see() -> None:
    from tw2k.engine.models import Event
    from tw2k.engine.observation import _PUBLIC_EVENTS, _event_visible_to

    u, a, _ = _universe()
    files = list((ROOT / "tests" / "fixtures" / "media_events").glob("*.json"))
    assert len(files) >= 10
    checked = 0
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        for row in data.get("batch") or []:
            payload = dict(row.get("facts") or {})
            payload["secret_scan"] = "HIDDENINTEL"
            ev = Event(
                seq=row["seq"], tick=row.get("tick") or 1, day=row.get("day") or 1,
                kind=EventKind(row["kind"]), actor_id=row.get("actor_id"),
                sector_id=row.get("sector_id"), payload=payload, summary=row.get("summary") or "",
            )
            text = json.dumps(prompt_for(u, a.id, ev, "planet.citadel"))
            if ev.actor_id:
                assert _event_visible_to(ev, ev.actor_id, u) is True
            if ev.kind not in _PUBLIC_EVENTS:
                assert _event_visible_to(ev, "nobody", u) is False
            assert "HIDDENINTEL" not in text and "secret_scan" not in text
            assert "_witnesses" not in text
            summary = row.get("summary") or ""
            if summary and summary not in json.dumps(row.get("facts") or {}):
                assert summary not in text
            checked += 1
    assert checked >= 10


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
  swap: R.considerCustomSwap('planet.citadel', note),
  gone: R.considerCustomSwap(null, note),
  late: R.considerCustomSwap('planet.citadel', late),
  card: R.momentCard(late),
  library: R.momentCard({trust:'auto', approved_by:'Ben', hash:'abc'})
}));
"""
    got = json.loads(subprocess.run(
        [NODE, "-e", script, str(ROOT / "web" / "media-resolver.js"), str(MANIFEST)],
        capture_output=True, text=True, check=True, timeout=30,
    ).stdout)
    assert got["off"] == []
    # The citadel self rule is dead: the engine emits no actor, and the client
    # does not swap that clip into the cockpit. It is listed in Moments.
    assert got["on"] == []
    assert got["gen"] == ["planet.genesis"]
    assert got["swap"] is True and got["gone"] is False
    assert got["late"] is False
    assert got["card"]["badge"] == "live-generated" and got["card"]["trust"] == "auto"
    assert got["library"] is None
