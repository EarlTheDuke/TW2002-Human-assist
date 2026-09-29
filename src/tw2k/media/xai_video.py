"""xAI Grok Imagine video adapter. Loaded only when the custom provider is xai.

The key comes from TW2K_XAI_VIDEO_KEY. It is sent only to api.x.ai and is never
logged, stored in a clip, or returned to the browser. Tests pass a transport;
this module does not call the network unless that default transport is used.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

log = logging.getLogger("tw2k.media.custom")

MODEL = "grok-imagine-video-1.5-2026-05-30"
API_ROOT = "https://api.x.ai"
GENERATE_URL = API_ROOT + "/v1/videos/generations"
MAX_FLASH_PER_S = 3.0
LUMA_JUMP = 40.0
PALETTE_LIMIT = 48.0
MAX_WIDTH = 854
MAX_HEIGHT = 480
MAGIC = b"TW2KF1"

Transport = Callable[[str, str, dict[str, str], bytes | None], tuple[int, dict[str, str], bytes]]


def _stills_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "web" / "media" / "stills"


def _scrub(text: str, key: str) -> str:
    if key and key in text:
        return text.replace(key, "[redacted]")
    return text


def urllib_transport(method: str, url: str, headers: dict[str, str], body: bytes | None) -> tuple[int, dict[str, str], bytes]:
    import urllib.error
    import urllib.request

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, {k.lower(): v for k, v in exc.headers.items()}, exc.read()


def pack_clip(width: int, height: int, duration_s: float, frames: list[tuple[int, int, int]]) -> bytes:
    """Test stand-in the checker can read without a video codec."""
    payload = json.dumps({
        "w": width,
        "h": height,
        "duration_s": duration_s,
        "frames": [list(rgb) for rgb in frames],
    }).encode("utf-8")
    return MAGIC + len(payload).to_bytes(4, "big") + payload


def _luma(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def flash_per_second(frames: list[tuple[int, int, int]], duration_s: float) -> float:
    if duration_s <= 0 or len(frames) < 2:
        return 0.0
    jumps = 0
    prev = _luma(frames[0])
    for rgb in frames[1:]:
        cur = _luma(rgb)
        if abs(cur - prev) >= LUMA_JUMP:
            jumps += 1
        prev = cur
    return jumps / duration_s


def _bible_mean(stills_dir: Path) -> tuple[float, float, float] | None:
    try:
        from PIL import Image
    except ImportError:
        return None
    acc = [0.0, 0.0, 0.0]
    count = 0
    for path in sorted(stills_dir.glob("*.png")):
        image = Image.open(path).convert("RGB").resize((8, 8))
        for pixel in image.getdata():
            acc[0] += pixel[0]
            acc[1] += pixel[1]
            acc[2] += pixel[2]
            count += 1
    if count == 0:
        return None
    return (acc[0] / count, acc[1] / count, acc[2] / count)


def palette_distance(frames: list[tuple[int, int, int]], bible: tuple[float, float, float]) -> float:
    if not frames:
        return 999.0
    mean = (
        sum(rgb[0] for rgb in frames) / len(frames),
        sum(rgb[1] for rgb in frames) / len(frames),
        sum(rgb[2] for rgb in frames) / len(frames),
    )
    return sum(abs(a - b) for a, b in zip(mean, bible, strict=True)) / 3


def decode_clip(data: bytes) -> dict[str, Any] | None:
    if data.startswith(MAGIC) and len(data) >= 10:
        size = int.from_bytes(data[6:10], "big")
        body = data[10:10 + size]
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            return None
        frames = [tuple(int(c) for c in rgb) for rgb in parsed.get("frames") or []]
        return {
            "w": int(parsed.get("w") or 0),
            "h": int(parsed.get("h") or 0),
            "duration_s": float(parsed.get("duration_s") or 0),
            "frames": frames,
        }
    return _decode_with_ffmpeg(data)


def _decode_with_ffmpeg(data: bytes) -> dict[str, Any] | None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not data:
        return None
    try:
        proc = subprocess.run(
            [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-i", "pipe:0",
                "-vf", "scale=32:32", "-f", "rawvideo", "-pix_fmt", "rgb24",
                "-vframes", "8", "pipe:1",
            ],
            input=data, capture_output=True, timeout=20, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0 or not proc.stdout:
        return None
    # One average colour per 32x32 frame is enough for the flash and palette checks.
    frame_bytes = 32 * 32 * 3
    raw = proc.stdout
    frames = []
    for start in range(0, len(raw) - frame_bytes + 1, frame_bytes):
        chunk = raw[start:start + frame_bytes]
        n = len(chunk) // 3
        frames.append((
            sum(chunk[i] for i in range(0, len(chunk), 3)) // n,
            sum(chunk[i] for i in range(1, len(chunk), 3)) // n,
            sum(chunk[i] for i in range(2, len(chunk), 3)) // n,
        ))
    if not frames:
        return None
    return {"w": 32, "h": 32, "duration_s": 4.0, "frames": frames}


class XaiImagineProvider:
    def __init__(
        self,
        *,
        key: str,
        transport: Transport | None = None,
        stills_dir: Path | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        timeout_s: float = 600,
    ) -> None:
        self._key = key
        self._transport = transport or urllib_transport
        self._stills = stills_dir or _stills_dir()
        self._clock = clock
        self._sleep = sleep
        self._timeout_s = timeout_s
        self.last_reject: str | None = None

    def __call__(self, job: dict[str, Any]) -> bytes | None:
        self.last_reject = None
        if not self._key:
            self.last_reject = "no-key"
            return None
        try:
            return self._generate(job)
        except Exception as exc:
            self.last_reject = "transport"
            log.warning("custom video request failed: %s", _scrub(str(exc), self._key))
            return None

    def _headers(self, download: bool) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if not download:
            headers["Content-Type"] = "application/json"
        headers["Authorization"] = "Bearer " + self._key
        return headers

    def _generate(self, job: dict[str, Any]) -> bytes | None:
        payload = {
            "model": MODEL,
            "prompt": str(job.get("prompt") or ""),
            "duration": 4,
            "resolution": "480p",
            "aspect_ratio": "16:9",
            "generate_audio": False,
            "respect_moderation": True,
        }
        started = self._clock()
        status, body = self._request("POST", GENERATE_URL, payload, download=False)
        if status >= 400 or _flagged(body):
            self.last_reject = "moderation"
            return None
        request_id = str(body.get("request_id") or body.get("id") or "")
        if not request_id:
            self.last_reject = "transport"
            return None
        poll = f"{API_ROOT}/v1/videos/{request_id}"
        backoff = 5.0
        done: dict[str, Any] | None = None
        while done is None:
            if self._clock() - started >= self._timeout_s:
                self.last_reject = "timeout"
                return None
            status, body = self._request("GET", poll, None, download=False)
            if status >= 400 or _flagged(body):
                self.last_reject = "moderation"
                return None
            state = str(body.get("status") or "")
            if state == "expired":
                self.last_reject = "expired"
                return None
            if state == "done":
                done = body
                break
            if state not in ("pending", "queued", "in_progress", ""):
                self.last_reject = "transport"
                return None
            self._sleep(backoff)
            backoff = min(backoff * 2, 30.0)
        video = done.get("video") if isinstance(done.get("video"), dict) else {}
        reason = _sane(done, video)
        if reason:
            self.last_reject = reason
            return None
        url = str(video.get("url") or "")
        if not url:
            self.last_reject = "transport"
            return None
        raw = self._download(url)
        if raw is None:
            self.last_reject = "transport"
            return None
        sample = decode_clip(raw)
        if sample is None:
            self.last_reject = "undecodable"
            return None
        return self._checked(raw, sample, video)

    def _request(self, method: str, url: str, payload: dict[str, Any] | None, *, download: bool) -> tuple[int, dict[str, Any]]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        status, _headers, raw = self._transport(method, url, self._headers(download), body)
        if not raw:
            return status, {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return status, {}
        return status, parsed if isinstance(parsed, dict) else {}

    def _download(self, url: str) -> bytes | None:
        host_ok = url.startswith(API_ROOT + "/")
        headers = self._headers(download=True) if host_ok else {"Accept": "video/mp4"}
        status, _headers, raw = self._transport("GET", url, headers, None)
        if status >= 400 or not raw:
            return None
        return raw

    def _checked(self, raw: bytes, sample: dict[str, Any], video: dict[str, Any]) -> bytes | None:
        duration = float(sample.get("duration_s") or video.get("duration") or 0)
        width = int(sample.get("w") or video.get("width") or 0)
        height = int(sample.get("h") or video.get("height") or 0)
        if duration <= 0 or duration > 5 or width > MAX_WIDTH or height > MAX_HEIGHT or width <= 0 or height <= 0:
            self.last_reject = "duration" if duration <= 0 or duration > 5 else "resolution"
            return None
        frames = sample.get("frames") or []
        if flash_per_second(frames, duration) > MAX_FLASH_PER_S:
            self.last_reject = "flash"
            return None
        bible = _bible_mean(self._stills)
        if bible is None or palette_distance(frames, bible) > PALETTE_LIMIT:
            self.last_reject = "style"
            return None
        return raw


def _flagged(body: dict[str, Any]) -> bool:
    if body.get("moderation_flag") or body.get("moderated"):
        return True
    mod = body.get("moderation")
    if mod is True:
        return True
    if isinstance(mod, dict) and (mod.get("blocked") or mod.get("flagged")):
        return True
    err = body.get("error") or {}
    if isinstance(err, dict) and err.get("code") in ("invalid_argument", "content_policy_violation"):
        return True
    return False


def _sane(done: dict[str, Any], video: dict[str, Any]) -> str | None:
    duration = video.get("duration", done.get("duration"))
    if duration is not None and (float(duration) <= 0 or float(duration) > 5):
        return "duration"
    width = video.get("width")
    height = video.get("height")
    if width is not None and int(width) > MAX_WIDTH:
        return "resolution"
    if height is not None and int(height) > MAX_HEIGHT:
        return "resolution"
    return None
