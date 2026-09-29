"""Mocked xAI video adapter. No network and no real key."""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from tests.test_v8a_custom_queue import _citadel, _universe
from tw2k.media.custom_queue import (
    ENV_XAI_KEY,
    STYLE_LINE,
    XAI_MODEL,
    CustomQueue,
    FakeProvider,
    current,
    prompt_for,
    prompt_hash,
    render_visual,
    start_if_enabled,
)
from tw2k.media.xai_video import (
    MAX_BYTES,
    MODEL,
    XaiImagineProvider,
    _bible_mean,
    pack_clip,
    urllib_transport,
)

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
        extra: dict[str, str] = {}
        if isinstance(payload, tuple):
            extra, payload = payload
        headers = {
            "content-type": "application/octet-stream" if isinstance(payload, bytes) else "application/json",
        }
        headers.update({k.lower(): v for k, v in extra.items()})
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        return status, headers, raw


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
    def boom(method, url, headers, body):
        raise AssertionError("network")

    queue = start_if_enabled(tmp_path, transport=boom)
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
    assert sent["duration"] == 4 and sent["resolution"] == "480p" and sent["aspect_ratio"] == "16:9"
    assert "generate_audio" not in sent and "respect_moderation" not in sent
    assert KEY not in body.decode("utf-8")
    assert headers["Authorization"] == "Bearer " + KEY
    assert script.calls[2][2]["Authorization"] == "Bearer " + KEY


def test_moderation_reject_does_not_download(caplog) -> None:
    script = Script([(400, {"error": {"code": "invalid_argument"}})])
    provider = _provider(script)
    with caplog.at_level("WARNING"):
        assert provider(_job()) is None
    assert provider.last_reject == "http_400"
    assert len(script.calls) == 1
    assert KEY not in caplog.text


def test_expired_and_timeout_leave_no_clip() -> None:
    expired = Script([(200, {"request_id": "req-1"}), (200, {"status": "expired"})])
    provider = _provider(expired)
    assert provider(_job()) is None
    assert provider.last_reject == "timeout"
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


def test_pytest_does_not_arm_a_leaked_key(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TW2K_VIDEO_CUSTOM", "1")
    monkeypatch.setenv("TW2K_VIDEO_CUSTOM_PROVIDER", "xai")
    monkeypatch.setenv(ENV_XAI_KEY, KEY)
    assert os.environ.get("PYTEST_CURRENT_TEST")
    sys.modules.pop("tw2k.media.xai_video", None)
    queue = start_if_enabled(tmp_path)
    try:
        assert isinstance(queue.provider, FakeProvider)
        assert "tw2k.media.xai_video" not in sys.modules
    finally:
        queue.stop()


def test_rendered_prose_is_what_we_hash_and_send() -> None:
    hidden = {"secret_scan": "HIDDENINTEL", "victim": "P2", "seq": 9}
    samples = {
        "planet.genesis": {"class": "M", **hidden},
        "planet.citadel": {"from": 0, "to": 1, **hidden},
        "self.ship_destroyed": dict(hidden),
    }
    for template, facts in samples.items():
        text = render_visual(template, facts)
        assert text and STYLE_LINE in text
        assert "{" not in text and "P2" not in text
        assert "HIDDENINTEL" not in text and "secret_scan" not in text
    universe, seat, _ = _universe()
    event = _citadel(universe, 1)
    body = prompt_for(universe, seat.id, event, "planet.citadel")
    assert body["prose"] == render_visual("planet.citadel", {"from": 0, "to": 1, "planet_id": 7, "secret_scan": "HIDDENINTEL"})
    changed = dict(body)
    changed["prose"] = body["prose"] + " extra"
    assert prompt_hash(changed) != prompt_hash(body)


def test_respect_moderation_false_discards_even_with_a_url() -> None:
    done = _done()
    done["video"]["respect_moderation"] = False
    script = Script([(200, {"request_id": "req-1"}), (200, done)])
    provider = _provider(script)
    assert provider(_job()) is None
    assert provider.last_reject == "moderation"
    assert len(script.calls) == 2


def test_a_failed_status_uses_the_error_code() -> None:
    script = Script([(200, {"request_id": "req-1"}), (200, {"status": "failed", "error": {"code": "internal_error"}})])
    provider = _provider(script)
    assert provider(_job()) is None
    assert provider.last_reject == "internal_error"
    assert len(script.calls) == 2


def test_retry_429_then_a_clip_posts_once() -> None:
    clip = pack_clip(854, 480, 4.0, [_rgb(), _rgb(), _rgb(), _rgb()])
    script = Script([
        (429, {}),
        (200, {"request_id": "req-1"}),
        (200, _done()),
        (200, clip),
    ])
    posted: list[int] = []
    job = _job()
    job["on_post"] = posted.append
    assert _provider(script)(job) == clip
    assert posted == [33]
    assert script.calls[0][0] == "POST" and script.calls[1][0] == "POST"


def test_four_503s_are_discarded_without_a_cost() -> None:
    script = Script([(503, {}), (503, {}), (503, {}), (503, {})])
    posted: list[int] = []
    job = _job()
    job["on_post"] = posted.append
    provider = _provider(script)
    assert provider(job) is None
    assert provider.last_reject == "http_503"
    assert posted == []
    assert len(script.calls) == 4


def test_bad_download_urls_never_call_the_transport() -> None:
    for url in (
        "file:///C:/secret.txt",
        "http://169.254.169.254/latest/meta-data",
        "https://evil.example/clip.webm",
    ):
        done = _done(url)
        script = Script([(200, {"request_id": "req-1"}), (200, done), (200, b"should-not-be-read")])
        provider = _provider(script)
        assert provider(_job()) is None
        assert provider.last_reject == "url_rejected"
        assert len(script.calls) == 2


def test_wrong_type_and_oversize_are_rejected() -> None:
    huge = ({"content-type": "video/webm", "content-length": str(MAX_BYTES + 1)}, b"x")
    html = ({"content-type": "text/html"}, b"<html></html>")
    for payload in (huge, html):
        script = Script([
            (200, {"request_id": "req-1"}),
            (200, _done()),
            (200, payload),
        ])
        provider = _provider(script)
        assert provider(_job()) is None
        assert provider.last_reject == "url_rejected"


def test_a_redirect_does_not_forward_the_key() -> None:
    seen: dict[str, str] = {}

    class Second(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            seen.update({k.lower(): v for k, v in self.headers.items()})
            self.send_response(204)
            self.end_headers()

        def log_message(self, format: str, *args) -> None:
            return

    server_b = _serve(Second)

    class First(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(302)
            self.send_header("Location", f"http://127.0.0.1:{server_b.server_address[1]}/next")
            self.end_headers()

        def log_message(self, format: str, *args) -> None:
            return

    server_a = _serve(First)
    try:
        urllib_transport(
            "GET",
            f"http://127.0.0.1:{server_a.server_address[1]}/start",
            {"Authorization": "Bearer dummy-token"},
            None,
            budget_s=5,
        )
        assert "authorization" not in seen
    finally:
        server_a.shutdown()
        server_b.shutdown()


def test_urllib_does_not_read_a_rejected_download() -> None:
    class Resp:
        status = 200

        def __init__(self, headers: dict[str, str]) -> None:
            self.headers = headers
            self.reads = 0

        def read(self, _n: int) -> bytes:
            self.reads += 1
            raise AssertionError("body read")

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> bool:
            return False

    class Opener:
        def __init__(self, resp: Resp) -> None:
            self.resp = resp

        def open(self, _req, timeout=None):
            return self.resp

    html = Resp({"Content-Type": "text/html", "Content-Length": "20"})
    huge = Resp({"Content-Type": "video/webm", "Content-Length": str(MAX_BYTES + 1)})
    for resp in (html, huge):
        opener = Opener(resp)
        original = urllib_transport.__wrapped__ if hasattr(urllib_transport, "__wrapped__") else None
        assert original is None
        import urllib.request

        saved = urllib.request.build_opener
        urllib.request.build_opener = lambda *_a, chosen=opener, **_k: chosen
        try:
            _status, _headers, raw = urllib_transport(
                "GET", "https://vidgen.x.ai/a.webm", {"Accept": "application/octet-stream"}, None,
            )
        finally:
            urllib.request.build_opener = saved
        assert raw == b""
        assert resp.reads == 0


def test_real_encoded_clips_keep_calm_and_discard_strobes(tmp_path) -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        import pytest

        pytest.skip("ffmpeg not installed")
    calm_rgb = _rgb()
    calm = _encode(tmp_path / "calm.mp4", 854, 480, 4, 8, [calm_rgb])
    strobe = _encode(tmp_path / "strobe.mp4", 854, 480, 2, 12, [(0, 0, 0), (255, 255, 255)])
    late = _encode(tmp_path / "late.mp4", 854, 480, 4, 12, [(40, 40, 40)] * 36 + [(0, 0, 0), (255, 255, 255)] * 6)
    big = _encode(tmp_path / "big.mp4", 1920, 1080, 10, 2, [(0, 0, 0)])
    assert _reason(calm) is None
    assert _reason(strobe) == "flash"
    assert _reason(late) == "flash"
    assert _reason(big) in {"duration", "resolution"}


def test_an_expired_inflight_job_still_counts(tmp_path) -> None:
    running = current()
    if running is not None:
        running.stop()
    release = threading.Event()
    entered = threading.Event()
    posts = {"n": 0}

    def transport(method, url, headers, body):
        if method == "POST":
            posts["n"] += 1
            payload = {"request_id": f"req-{posts['n']}"}
            return 200, {"content-type": "application/json"}, json.dumps(payload).encode("utf-8")
        if posts["n"] == 1 and not entered.is_set():
            entered.set()
            assert release.wait(5)
            return 200, {"content-type": "application/json"}, b'{"status":"expired"}'
        return 200, {"content-type": "application/json"}, b'{"status":"failed","error":{"code":"internal_error"}}'

    provider = XaiImagineProvider(key=KEY, transport=transport, stills_dir=STILLS, sleep=lambda _s: None)
    queue = CustomQueue(tmp_path, provider, jobs_per_match=3, match_cap_cents=100).start()
    try:
        universe, _, _ = _universe()
        _citadel(universe, 1)
        assert entered.wait(3)
        queue._conn.execute("UPDATE jobs SET status='expired' WHERE status='running'")
        queue._conn.commit()
        for level in (2, 3, 4):
            queue.on_emit(universe, _citadel(universe, level))
        release.set()
        end = time.time() + 5
        while time.time() < end and posts["n"] < 3:
            time.sleep(0.05)
        time.sleep(0.3)
        assert posts["n"] == 3
    finally:
        release.set()
        queue.stop()


def test_restart_mid_call_keeps_the_spend(tmp_path) -> None:
    running = current()
    if running is not None:
        running.stop()
    release = threading.Event()
    entered = threading.Event()

    def blocking(method, url, headers, body):
        if method == "POST":
            return 200, {"content-type": "application/json"}, b'{"request_id":"req-1"}'
        entered.set()
        assert release.wait(5)
        return 200, {"content-type": "application/json"}, b'{"status":"pending"}'

    provider = XaiImagineProvider(key=KEY, transport=blocking, stills_dir=STILLS, sleep=lambda _s: None)
    queue = CustomQueue(tmp_path, provider, match_cap_cents=33).start()
    universe, _, _ = _universe()
    _citadel(universe, 1)
    assert entered.wait(3)
    queue.stop()
    release.set()
    time.sleep(0.3)
    posts = {"n": 0}

    def counting(method, url, headers, body):
        if method == "POST":
            posts["n"] += 1
        return 200, {"content-type": "application/json"}, b'{"status":"failed","error":{"code":"internal_error"}}'

    again = CustomQueue(
        tmp_path,
        XaiImagineProvider(key=KEY, transport=counting, stills_dir=STILLS, sleep=lambda _s: None),
        match_cap_cents=33,
    ).start()
    try:
        row = again._conn.execute("SELECT status, cost_cents FROM jobs").fetchone()
        assert row["status"] == "expired" and row["cost_cents"] == 33
        again.on_emit(universe, _citadel(universe, 2))
        time.sleep(0.3)
        assert posts["n"] == 0
    finally:
        again.stop()


def test_a_never_started_expired_job_does_not_use_the_cap(tmp_path) -> None:
    running = current()
    if running is not None:
        running.stop()
    script = Script([(200, {"status": "failed", "error": {"code": "internal_error"}})])
    queue = CustomQueue(tmp_path, _provider(script))
    queue._conn.execute(
        """INSERT INTO jobs (hash, seat, match_id, status, created, cost_cents, trigger_seq, clip_key, day, swap, prompt)
           VALUES ('old', 'A', 'm', 'queued', ?, 0, 1, 'planet.genesis', '2026-09-28', 0, '')""",
        (time.time(),),
    )
    queue._conn.commit()
    queue.start()
    try:
        universe, _, _ = _universe()
        match_id = f"{universe.config.seed}:{id(universe)}"
        queue._conn.execute("UPDATE jobs SET match_id=? WHERE hash='old'", (match_id,))
        queue._conn.commit()
        queue.on_emit(universe, _citadel(universe, 1))
        end = time.time() + 3
        saw = False
        while time.time() < end:
            rows = queue._conn.execute("SELECT hash, status, cost_cents FROM jobs").fetchall()
            fresh = [row for row in rows if row["hash"] != "old"]
            if fresh:
                saw = True
                break
            time.sleep(0.05)
        assert saw
        old = queue._conn.execute("SELECT status, cost_cents FROM jobs WHERE hash='old'").fetchone()
        assert old["status"] == "expired" and old["cost_cents"] == 0
    finally:
        queue.stop()


def test_jobs_report_prints_template_status_reason_cost_and_latency(tmp_path, capsys) -> None:
    sys.path.insert(0, str(ROOT))
    from scripts.custom_jobs_report import main

    queue = CustomQueue(tmp_path, FakeProvider())
    queue._conn.execute(
        """INSERT INTO jobs
           (hash, seat, match_id, status, created, cost_cents, trigger_seq, clip_key, day, swap, prompt, reason, started_at, finished_at)
           VALUES ('h', 'A', 'm', 'discarded', ?, 33, 1, 'planet.genesis', '2026-09-28', 0, 'secret prose', 'flash', 10, 14)"""
        ,
        (time.time(),),
    )
    queue._conn.commit()
    assert main(["custom_jobs_report.py", str(tmp_path)]) == 0
    line = capsys.readouterr().out.strip()
    assert line.startswith("planet.genesis discarded flash 33 ")
    assert "secret" not in line
    assert KEY not in line
    queue.stop()


def _serve(handler) -> ThreadingHTTPServer:
    port = _free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _free_port() -> int:
    port = 8033
    while port < 8200:
        if port in (8031, 8032):
            port += 1
            continue
        sock = socket.socket()
        try:
            sock.bind(("127.0.0.1", port))
            return port
        except OSError:
            port += 1
        finally:
            sock.close()
    raise RuntimeError("no free port")


def _encode(path: Path, width: int, height: int, seconds: int, rate: int, pattern: list[tuple[int, int, int]]) -> bytes:
    count = seconds * rate
    colors = [pattern[i % len(pattern)] for i in range(count)]
    pixel = width * height
    raw = b"".join(bytes(rgb) * pixel for rgb in colors)
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(rate),
        "-i", "pipe:0",
        "-an", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-g", "1", "-bf", "0", str(path),
    ]
    proc = subprocess.run(cmd, input=raw, capture_output=True, timeout=90, check=False)
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")[-400:]
    return path.read_bytes()


def _reason(data: bytes) -> str | None:
    script = Script([(200, {"request_id": "req-1"}), (200, _done()), (200, data)])
    provider = _provider(script)
    if provider(_job()) is not None:
        return None
    return provider.last_reject
