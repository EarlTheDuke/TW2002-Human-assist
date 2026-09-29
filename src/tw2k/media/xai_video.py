"""xAI Grok Imagine video adapter. Loaded only when the custom provider is xai.

The key comes from TW2K_XAI_VIDEO_KEY. It is sent only to api.x.ai and is never
logged, stored in a clip, or returned to the browser. Tests pass a transport.
The dated snapshot grok-imagine-video-1.5-2026-05-30 is not the request id;
the public docs name the model grok-imagine-video-1.5.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from itertools import pairwise
from pathlib import Path
from typing import Any

log = logging.getLogger("tw2k.media.custom")

# Public model id. Dated alias grok-imagine-video-1.5-2026-05-30 is the snapshot name.
MODEL = "grok-imagine-video-1.5"
API_ROOT = "https://api.x.ai"
GENERATE_URL = API_ROOT + "/v1/videos/generations"
MAX_FLASH_PER_S = 3
LUMA_JUMP = 40.0
PALETTE_LIMIT = 48.0
MAX_WIDTH = 854
MAX_HEIGHT = 480
MAX_BYTES = 20 * 1024 * 1024
REQUEST_BUDGET_S = 30.0
POST_CENTS = 33
MAGIC = b"TW2KF1"

Transport = Callable[[str, str, dict[str, str], bytes | None], tuple[int, dict[str, str], bytes]]


def _stills_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "web" / "media" / "stills"


def _scrub(text: str, key: str) -> str:
    if key and key in text:
        return text.replace(key, "[redacted]")
    return text


def _host_allowed(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").lower()
    return host == "api.x.ai" or host == "vidgen.x.ai" or host.endswith(".x.ai")


def _content_ok(header: str) -> bool:
    kind = header.split(";", 1)[0].strip().lower()
    return kind.startswith("video/") or kind == "application/octet-stream"


class _StripAuthRedirect(urllib.request.HTTPRedirectHandler):
    """Drop Authorization unless the next URL is still https://api.x.ai."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is None:
            return None
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme != "https" or (parsed.hostname or "").lower() != "api.x.ai":
            redirected.remove_header("Authorization")
        return redirected


def urllib_transport(
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes | None,
    *,
    max_bytes: int = MAX_BYTES,
    budget_s: float = REQUEST_BUDGET_S,
) -> tuple[int, dict[str, str], bytes]:
    opener = urllib.request.build_opener(_StripAuthRedirect)
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    deadline = time.monotonic() + budget_s
    try:
        resp = opener.open(req, timeout=budget_s)
    except urllib.error.HTTPError as exc:
        hdrs = {k.lower(): v for k, v in exc.headers.items()}
        if _skip_body(headers, hdrs, max_bytes):
            return exc.code, hdrs, b""
        raw, truncated = _read_capped(exc, max_bytes, deadline)
        return exc.code, hdrs, b"" if truncated else raw
    with resp:
        hdrs = {k.lower(): v for k, v in resp.headers.items()}
        if _skip_body(headers, hdrs, max_bytes):
            return resp.status, hdrs, b""
        raw, truncated = _read_capped(resp, max_bytes, deadline)
        return resp.status, hdrs, b"" if truncated else raw


def _skip_body(request_headers: dict[str, str], response_headers: dict[str, str], max_bytes: int) -> bool:
    accept = (request_headers.get("Accept") or "").lower()
    if "octet-stream" not in accept:
        return False
    if not _content_ok(response_headers.get("content-type", "")):
        return True
    try:
        length = int(response_headers.get("content-length") or 0)
    except ValueError:
        length = 0
    return length > max_bytes


def _read_capped(resp: Any, max_bytes: int, deadline: float) -> tuple[bytes, bool]:
    chunks: list[bytes] = []
    total = 0
    while total <= max_bytes:
        if time.monotonic() > deadline:
            break
        block = resp.read(64 * 1024)
        if not block:
            break
        total += len(block)
        if total > max_bytes:
            return b"", True
        chunks.append(block)
    return b"".join(chunks), False


def pack_clip(width: int, height: int, duration_s: float, frames: list[tuple[int, int, int]]) -> bytes:
    payload = json.dumps({
        "w": width,
        "h": height,
        "duration_s": duration_s,
        "frames": [list(rgb) for rgb in frames],
    }).encode("utf-8")
    return MAGIC + len(payload).to_bytes(4, "big") + payload


def _luma(rgb: tuple[int, int, int]) -> float:
    red, green, blue = rgb
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _jumped(left: Any, right: Any) -> bool:
    if isinstance(left, tuple) and len(left) == 3 and not isinstance(left[0], tuple):
        return abs(_luma(left) - _luma(right)) >= LUMA_JUMP
    pairs = zip(left, right, strict=False)
    return any(abs(a - b) >= LUMA_JUMP for a, b in pairs)


def max_jumps_in_a_second(frames: list[Any], duration_s: float) -> int:
    if len(frames) < 2 or duration_s <= 0:
        return 0
    flags = [1 if _jumped(a, b) else 0 for a, b in pairwise(frames)]
    span = max(1, round(len(frames) / duration_s))
    worst = 0
    for index in range(len(flags)):
        worst = max(worst, sum(flags[index:index + span]))
    return worst


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


def palette_distance(frames: list[Any], bible: tuple[float, float, float]) -> float:
    colors: list[tuple[float, float, float]] = []
    for frame in frames:
        if isinstance(frame, tuple) and len(frame) == 3 and not isinstance(frame[0], tuple):
            colors.append((float(frame[0]), float(frame[1]), float(frame[2])))
        elif isinstance(frame, dict):
            colors.append((float(frame["r"]), float(frame["g"]), float(frame["b"])))
    if not colors:
        return 999.0
    mean = tuple(sum(color[i] for color in colors) / len(colors) for i in range(3))
    return sum(abs(a - b) for a, b in zip(mean, bible, strict=True)) / 3


def decode_clip(data: bytes) -> dict[str, Any] | None:
    if data.startswith(MAGIC) and len(data) >= 10:
        size = int.from_bytes(data[6:10], "big")
        try:
            parsed = json.loads(data[10:10 + size])
        except json.JSONDecodeError:
            return None
        frames = [tuple(int(channel) for channel in rgb) for rgb in parsed.get("frames") or []]
        return {
            "w": int(parsed.get("w") or 0),
            "h": int(parsed.get("h") or 0),
            "duration_s": float(parsed.get("duration_s") or 0),
            "frames": frames,
            "mean": None,
        }
    return _decode_encoded(data)


def _decode_encoded(data: bytes) -> dict[str, Any] | None:
    if shutil.which("ffprobe") is None or shutil.which("ffmpeg") is None:
        return None
    fd, name = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    path = Path(name)
    try:
        path.write_bytes(data)
        probe = _ffprobe(path)
        if probe is None:
            return None
        frames, mean = _sample_frames(path)
        if not frames:
            return None
        return {
            "w": probe["w"],
            "h": probe["h"],
            "duration_s": probe["duration_s"],
            "frames": frames,
            "mean": mean,
        }
    finally:
        path.unlink(missing_ok=True)


def _ffprobe(path: Path) -> dict[str, Any] | None:
    proc = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration:format=duration",
            "-of", "json", str(path),
        ],
        capture_output=True, timeout=20, check=False,
    )
    if proc.returncode != 0:
        return None
    try:
        payload = json.loads(proc.stdout.decode("utf-8", "replace"))
        stream = (payload.get("streams") or [{}])[0]
        width = int(stream.get("width") or 0)
        height = int(stream.get("height") or 0)
        fmt = payload.get("format") if isinstance(payload.get("format"), dict) else {}
        duration = float(stream.get("duration") or fmt.get("duration") or 0)
    except (json.JSONDecodeError, TypeError, ValueError, IndexError):
        return None
    if width <= 0 or height <= 0 or duration <= 0:
        return None
    return {"w": width, "h": height, "duration_s": duration}


def _sample_frames(path: Path) -> tuple[list[list[float]], tuple[float, float, float] | None]:
    proc = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-i", str(path),
            "-vf", "scale=8:8", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
        ],
        capture_output=True, timeout=40, check=False,
    )
    if proc.returncode != 0 or not proc.stdout:
        return [], None
    frame_bytes = 8 * 8 * 3
    raw = proc.stdout
    frames: list[list[float]] = []
    totals = [0.0, 0.0, 0.0]
    pixels = 0
    for start in range(0, len(raw) - frame_bytes + 1, frame_bytes):
        chunk = raw[start:start + frame_bytes]
        regions: list[float] = []
        for offset in range(0, frame_bytes, 3):
            red, green, blue = chunk[offset], chunk[offset + 1], chunk[offset + 2]
            regions.append(0.2126 * red + 0.7152 * green + 0.0722 * blue)
            totals[0] += red
            totals[1] += green
            totals[2] += blue
            pixels += 1
        frames.append(regions)
    if pixels == 0:
        return frames, None
    return frames, (totals[0] / pixels, totals[1] / pixels, totals[2] / pixels)


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

    def _headers(self, download: bool, url: str) -> dict[str, str]:
        headers = {"Accept": "application/octet-stream" if download else "application/json"}
        if not download:
            headers["Content-Type"] = "application/json"
        host = (urllib.parse.urlparse(url).hostname or "").lower()
        if host == "api.x.ai":
            headers["Authorization"] = "Bearer " + self._key
        return headers

    def _generate(self, job: dict[str, Any]) -> bytes | None:
        payload = {
            "model": MODEL,
            "prompt": str(job.get("prompt") or ""),
            "duration": 4,
            "resolution": "480p",
            "aspect_ratio": "16:9",
        }
        started = self._clock()
        status, body = self._post_with_retry(payload, started)
        if status is None:
            return None
        if status >= 400 or _flagged(body):
            self.last_reject = _http_reason(status, body)
            return None
        request_id = str(body.get("request_id") or body.get("id") or "")
        if not request_id:
            self.last_reject = "transport"
            return None
        posted = job.get("on_post")
        if callable(posted):
            posted(_usage_cents(body))
        poll = f"{API_ROOT}/v1/videos/{request_id}"
        backoff = 5.0
        done: dict[str, Any] | None = None
        while done is None:
            if self._clock() - started >= self._timeout_s:
                self.last_reject = "timeout"
                return None
            status, body = self._request("GET", poll, None)
            if status in (429, 503):
                self._sleep(backoff)
                backoff = min(backoff * 2, 30.0)
                continue
            if status >= 400:
                self.last_reject = _http_reason(status, body)
                return None
            state = str(body.get("status") or "")
            if state == "expired":
                self.last_reject = "timeout"
                return None
            if state == "failed":
                err = body.get("error") if isinstance(body.get("error"), dict) else {}
                self.last_reject = _safe_code(str(err.get("code") or "failed"))
                return None
            if _flagged(body):
                self.last_reject = "moderation"
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
        if video.get("respect_moderation") is False:
            self.last_reject = "moderation"
            return None
        if not _announced_ok(self, video):
            return None
        url = str(video.get("url") or "")
        if not _host_allowed(url):
            self.last_reject = "url_rejected"
            return None
        raw, headers = self._download(url)
        if raw is None:
            return None
        if not _content_ok(headers.get("content-type", "")):
            self.last_reject = "url_rejected"
            return None
        length = int(headers.get("content-length") or 0)
        if length > MAX_BYTES or len(raw) > MAX_BYTES:
            self.last_reject = "url_rejected"
            return None
        sample = decode_clip(raw)
        if sample is None:
            self.last_reject = "undecodable"
            return None
        return self._checked(raw, sample)

    def _post_with_retry(self, payload: dict[str, Any], started: float) -> tuple[int | None, dict[str, Any]]:
        backoff = 1.0
        status = 0
        body: dict[str, Any] = {}
        for attempt in range(4):
            if self._clock() - started >= self._timeout_s:
                self.last_reject = "timeout"
                return None, {}
            status, body = self._request("POST", GENERATE_URL, payload)
            if status in (429, 503) and attempt < 3:
                self._sleep(backoff)
                backoff = min(backoff * 2, 30.0)
                continue
            return status, body
        self.last_reject = _http_reason(status, body)
        return None, body

    def _request(self, method: str, url: str, payload: dict[str, Any] | None) -> tuple[int, dict[str, Any]]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        status, _headers, raw = self._transport(method, url, self._headers(False, url), body)
        if not raw:
            return status, {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return status, {}
        return status, parsed if isinstance(parsed, dict) else {}

    def _download(self, url: str) -> tuple[bytes | None, dict[str, str]]:
        try:
            status, headers, raw = self._transport("GET", url, self._headers(True, url), None)
        except Exception as exc:
            self.last_reject = "transport"
            log.warning("custom video download failed: %s", _scrub(str(exc), self._key))
            return None, {}
        if status >= 400 or not raw:
            self.last_reject = "url_rejected" if status < 400 else _http_reason(status, {})
            return None, {k.lower(): v for k, v in headers.items()}
        return raw, {k.lower(): v for k, v in headers.items()}

    def _checked(self, raw: bytes, sample: dict[str, Any]) -> bytes | None:
        duration = float(sample.get("duration_s") or 0)
        width = int(sample.get("w") or 0)
        height = int(sample.get("h") or 0)
        if duration <= 0 or duration > 5:
            self.last_reject = "duration"
            return None
        if width <= 0 or height <= 0 or width > MAX_WIDTH or height > MAX_HEIGHT:
            self.last_reject = "resolution"
            return None
        frames = sample.get("frames") or []
        if max_jumps_in_a_second(frames, duration) > MAX_FLASH_PER_S:
            self.last_reject = "flash"
            return None
        bible = _bible_mean(self._stills)
        mean = sample.get("mean")
        distance = palette_distance([mean], bible) if mean and bible else (
            palette_distance(frames, bible) if bible else 999.0
        )
        if bible is None or distance > PALETTE_LIMIT:
            self.last_reject = "style"
            return None
        return raw


def _usage_cents(body: dict[str, Any]) -> int:
    usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
    if usage.get("cost_cents") is not None:
        return int(usage["cost_cents"])
    if usage.get("cost_usd") is not None:
        return round(float(usage["cost_usd"]) * 100)
    return POST_CENTS


def _safe_code(code: str) -> str:
    cleaned = "".join(ch for ch in code if ch.isalnum() or ch == "_")[:40]
    return cleaned or "failed"


def _announced_ok(provider: XaiImagineProvider, video: dict[str, Any]) -> bool:
    announced = video.get("duration")
    if announced is not None:
        try:
            seconds = float(announced)
        except (TypeError, ValueError):
            seconds = 0.0
        if seconds <= 0 or seconds > 5:
            provider.last_reject = "duration"
            return False
    if video.get("width") is not None and video.get("height") is not None:
        try:
            width, height = int(video["width"]), int(video["height"])
        except (TypeError, ValueError):
            width, height = 0, 0
        if width <= 0 or height <= 0 or width > MAX_WIDTH or height > MAX_HEIGHT:
            provider.last_reject = "resolution"
            return False
    return True


def _http_reason(status: int, body: dict[str, Any]) -> str:
    if _flagged(body) and status < 400:
        return "moderation"
    if status == 401:
        return "http_401"
    if status == 429:
        return "http_429"
    if status >= 400:
        return f"http_{status}"
    return "transport"


def _flagged(body: dict[str, Any]) -> bool:
    if body.get("moderation_flag") or body.get("moderated"):
        return True
    mod = body.get("moderation")
    if mod is True:
        return True
    if isinstance(mod, dict) and (mod.get("blocked") or mod.get("flagged")):
        return True
    video = body.get("video") if isinstance(body.get("video"), dict) else {}
    if video.get("respect_moderation") is False:
        return True
    return False
