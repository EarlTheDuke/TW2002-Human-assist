"""Mocked xAI video adapter. No network and no real key."""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from tests.test_v8a_custom_queue import _citadel, _universe
from tw2k.media.custom_queue import (
    ENV_XAI_KEY,
    XAI_MODEL,
    CustomQueue,
    FakeProvider,
    current,
    start_if_enabled,
)
from tw2k.media.xai_video import MODEL, XaiImagineProvider, _bible_mean, pack_clip

ROOT = Path(__file__).resolve().parents[1]
STILLS = ROOT / "web" / "media" / "stills"
KEY = "unit-video-key"
SECRET = re.compile(r"xai-[A-Za-z0-9]{16,}|sk-[A-Za-z0-9]{16,}")


class Script:
    def __init__(self, steps: list) -> None:
        self.steps = list(steps)
        self.calls: list[tuple] = []

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url, dict(headers), body))
        status, payload = self.steps.pop(0)
        if isinstance(payload, bytes):
            return status, {}, payload
        return status, {}, json.dumps(payload).encode("utf-8")


def _rgb() -> tuple[int, int, int]:
    mean = _bible_mean(STILLS)
    assert mean is not None
    return tuple(int(round(c)) for c in mean)


def _provider(script: Script, **kw) -> XaiImagineProvider:
    return XaiImagineProvider(key=KEY, transport=script, stills_dir=STILLS, sleep=lambda _s: None, **kw)


def _done(url: str = "https://api.x.ai/v1/videos/req-1/content") -> dict:
    return {
        "status": "done",
        "request_id": "req-1",
        "video": {"url": url, "duration": 4, "width": 854, "height": 480},
        "moderation_flag": False,
    }


def _job() -> dict:
    return {"prompt": '{"template_id":"planet.genesis"}', "hash": "abc"}


def test_flag_off_does_not_load_the_adapter(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("TW2K_VIDEO_CUSTOM", raising=False)
    monkeypatch.delenv("TW2K_VIDEO_CUSTOM_PROVIDER", raising=False)
    monkeypatch.delenv(ENV_XAI_KEY, raising=False)
    running = current()
    if running is not None:
        running.stop()
    sys.modules.pop("tw2k.media.xai_video", None)
    assert start_if_enabled(tmp_path) is None
    assert "tw2k.media.xai_video" not in sys.modules


def test_flag_on_without_the_switch_stays_on_the_fake_provider(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TW2K_VIDEO_CUSTOM", "1")
    monkeypatch.delenv("TW2K_VIDEO_CUSTOM_PROVIDER", raising=False)
    monkeypatch.setenv(ENV_XAI_KEY, KEY)
    sys.modules.pop("tw2k.media.xai_video", None)
    queue = start_if_enabled(tmp_path)
    try:
        assert isinstance(queue.provider, FakeProvider)
        assert "tw2k.media.xai_video" not in sys.modules
    finally:
        queue.stop()


def test_a_missing_key_does_not_load_the_adapter(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TW2K_VIDEO_CUSTOM", "1")
    monkeypatch.setenv("TW2K_VIDEO_CUSTOM_PROVIDER", "xai")
    monkeypatch.delenv(ENV_XAI_KEY, raising=False)
    sys.modules.pop("tw2k.media.xai_video", None)
    queue = start_if_enabled(tmp_path)
    try:
        assert isinstance(queue.provider, FakeProvider)
        assert "tw2k.media.xai_video" not in sys.modules
    finally:
        queue.stop()


def test_the_switch_and_a_key_load_the_adapter(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TW2K_VIDEO_CUSTOM", "1")
    monkeypatch.setenv("TW2K_VIDEO_CUSTOM_PROVIDER", "xai")
    monkeypatch.setenv(ENV_XAI_KEY, KEY)
    queue = start_if_enabled(tmp_path)
    try:
        assert type(queue.provider).__name__ == "XaiImagineProvider"
        assert type(queue.provider).__module__ == "tw2k.media.xai_video"
        assert MODEL == XAI_MODEL
    finally:
        queue.stop()


def test_a_passing_clip_uses_the_dated_model_and_returns_the_bytes() -> None:
    clip = pack_clip(854, 480, 4.0, [_rgb(), _rgb(), _rgb(), _rgb()])
    script = Script([
        (200, {"request_id": "req-1"}),
        (200, _done()),
        (200, clip),
    ])
    got = _provider(script)(_job())
    assert got == clip
    method, url, headers, body = script.calls[0]
    assert method == "POST" and url.endswith("/v1/videos/generations")
    sent = json.loads(body)
    assert sent["model"] == MODEL
    assert sent["duration"] == 4 and sent["resolution"] == "480p"
    assert sent["generate_audio"] is False and sent["respect_moderation"] is True
    assert KEY not in body.decode("utf-8")
    assert headers["Authorization"] == "Bearer " + KEY
    assert script.calls[2][2]["Authorization"] == "Bearer " + KEY


def test_moderation_reject_does_not_download(caplog) -> None:
    script = Script([(400, {"error": {"code": "invalid_argument"}})])
    provider = _provider(script)
    with caplog.at_level("WARNING"):
        assert provider(_job()) is None
    assert provider.last_reject == "moderation"
    assert len(script.calls) == 1
    assert KEY not in caplog.text


def test_expired_and_timeout_leave_no_clip() -> None:
    expired = Script([(200, {"request_id": "req-1"}), (200, {"status": "expired"})])
    provider = _provider(expired)
    assert provider(_job()) is None
    assert provider.last_reject == "expired"
    assert len(expired.calls) == 2

    clock = {"now": 0.0}

    def now() -> float:
        return clock["now"]

    def jump(seconds: float) -> None:
        clock["now"] += 601

    pending = Script([(200, {"request_id": "req-1"}), (200, {"status": "pending"})])
    slow = XaiImagineProvider(
        key=KEY, transport=pending, stills_dir=STILLS, clock=now, sleep=jump, timeout_s=600,
    )
    assert slow(_job()) is None
    assert slow.last_reject == "timeout"


def test_flash_and_style_checks_discard_the_clip() -> None:
    strobe = [(0, 0, 0), (255, 255, 255)] * 8
    flash = Script([
        (200, {"request_id": "req-1"}),
        (200, _done()),
        (200, pack_clip(854, 480, 4.0, strobe)),
    ])
    provider = _provider(flash)
    assert provider(_job()) is None
    assert provider.last_reject == "flash"

    neon = Script([
        (200, {"request_id": "req-1"}),
        (200, _done()),
        (200, pack_clip(854, 480, 4.0, [(255, 0, 255)] * 4)),
    ])
    provider = _provider(neon)
    assert provider(_job()) is None
    assert provider.last_reject == "style"


def test_a_bad_duration_is_rejected_before_download() -> None:
    script = Script([
        (200, {"request_id": "req-1"}),
        (200, {"status": "done", "video": {"url": "https://api.x.ai/v1/videos/req-1/content", "duration": 30, "width": 854, "height": 480}}),
    ])
    provider = _provider(script)
    assert provider(_job()) is None
    assert provider.last_reject == "duration"
    assert len(script.calls) == 2


def test_cap_refusal_makes_no_http_call(tmp_path) -> None:
    running = current()
    if running is not None:
        running.stop()
    script = Script([])
    queue = CustomQueue(tmp_path, _provider(script), jobs_per_match=3)
    universe, _, _ = _universe()
    match_id = f"{universe.config.seed}:{id(universe)}"
    for n in range(3):
        queue._conn.execute(
            """INSERT INTO jobs (hash, seat, match_id, status, created, cost_cents, trigger_seq, clip_key, day, swap, prompt)
               VALUES (?, 'A', ?, 'ready', ?, 33, ?, 'planet.citadel', '2026-09-28', 0, '')""",
            (f"h{n}", match_id, time.time(), n),
        )
    queue._conn.commit()
    event = _citadel(universe, 1)
    queue.on_emit(universe, event)
    assert len(script.calls) == 0
    queued = queue._conn.execute("SELECT COUNT(*) FROM jobs WHERE status='queued'").fetchone()[0]
    assert queued == 0
    queue.stop()


def test_a_failed_check_does_not_enter_the_feed(tmp_path) -> None:
    strobe = [(0, 0, 0), (255, 255, 255)] * 8
    script = Script([
        (200, {"request_id": "req-1"}),
        (200, _done()),
        (200, pack_clip(854, 480, 4.0, strobe)),
    ])
    queue = CustomQueue(tmp_path, _provider(script)).start()
    try:
        universe, _, _ = _universe()
        _citadel(universe, 1)
        deadline = time.time() + 3
        status = None
        while time.time() < deadline:
            row = queue._conn.execute("SELECT status FROM jobs").fetchone()
            if row is not None and row["status"] == "discarded":
                status = row["status"]
                break
            time.sleep(0.05)
        assert status == "discarded"
        feed = queue.feed_for("A")
        assert feed["ready"] == [] and feed["moments"] == []
        assert list(tmp_path.glob("*.webm")) == []
    finally:
        queue.stop()


def test_a_transport_error_does_not_log_the_key(caplog) -> None:
    def boom(method, url, headers, body):
        raise RuntimeError("rejected " + KEY)

    provider = XaiImagineProvider(key=KEY, transport=boom, stills_dir=STILLS, sleep=lambda _s: None)
    with caplog.at_level("WARNING"):
        assert provider(_job()) is None
    assert provider.last_reject == "transport"
    assert KEY not in caplog.text


def test_source_has_no_video_api_key() -> None:
    for folder in ("src", "tests", "web"):
        for path in (ROOT / folder).rglob("*"):
            if path.suffix not in {".py", ".js", ".json", ".md"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            assert SECRET.search(text) is None, path
