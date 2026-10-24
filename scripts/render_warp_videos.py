#!/usr/bin/env python3
"""Record the ten redesign warp scenes for every hull.

Headless Chromium paints the same SVG the cockpit uses (NOTE 126 meshes,
web/warp-variants.js cameras, plume, and flash). Frames are stepped by
seeking the CSS animations, then ffmpeg packs each scene into a short
VP9 webm at 800x520, 16 fps, at or under 300 KB.

Output:
  web/warp-video/<hull>/NN.webm
  web/warp-video/manifest.json

The manifest's generated.clips array is the slot for later AI videos.
A non-empty webm there replaces the captured file for that clip id.

Usage:
  PYTHONPATH=src /tmp/venv/bin/python scripts/render_warp_videos.py
  PYTHONPATH=src /tmp/venv/bin/python scripts/render_warp_videos.py --only merchant_cruiser:01
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
STAGE = ROOT / "scripts" / "warp_video_stage.html"
OUT = WEB / "warp-video"
CLIPS = WEB / "media" / "warp-clips.json"
ART = Path("/opt/cursor/artifacts/note135-warp-video")
FPS = 16
VIEW_W = 800
VIEW_H = 520
MAX_BYTES = 300 * 1024

GENERATED_ABOUT = (
    "Drop generated (AI) videos here later. Each entry replaces the captured "
    "file for that clip id when webm is a non-empty path. Paths are relative "
    "to /static/warp-video/ (for example generated/merchant_cruiser/01.webm) "
    "unless they start with / or http. An empty webm is ignored and the "
    "captured file plays. Leave clips empty until those files exist. "
    'Shape: {"id": "merchant_cruiser.streak.01", "webm": "generated/merchant_cruiser/01.webm", "duration_ms": 1600}.'
)

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".webm": "video/webm",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        path = unquote(urlparse(self.path).path)
        if path in ("/", "/stage.html"):
            body = STAGE.read_bytes()
            self._send(200, "text/html; charset=utf-8", body)
            return
        if not path.startswith("/static/"):
            self._send(404, "text/plain", b"missing")
            return
        rel = path[len("/static/") :]
        file = (WEB / rel).resolve()
        if not str(file).startswith(str(WEB.resolve())) or not file.is_file():
            self._send(404, "text/plain", b"missing")
            return
        self._send(200, MIME.get(file.suffix.lower(), "application/octet-stream"), file.read_bytes())

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        return


def serve() -> tuple[ThreadingHTTPServer, int]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, int(server.server_address[1])


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "csv=p=0", str(path),
        ],
        text=True,
    ).strip()
    return float(out or "0")


def encode(frames: Path, dest: Path, crf: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-framerate", str(FPS),
        "-i", str(frames / "%03d.png"),
        "-c:v", "libvpx-vp9",
        "-pix_fmt", "yuv420p",
        "-b:v", "0",
        "-crf", str(crf),
        "-deadline", "good",
        "-cpu-used", "4",
        "-lag-in-frames", "0",
        "-row-mt", "1",
        "-an",
        "-f", "webm",
        str(dest),
    ]
    subprocess.check_call(cmd)


def ffprobe_size(path: Path) -> tuple[int, int]:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path),
        ],
        text=True,
    ).strip()
    width, height = out.split(",")
    return int(width), int(height)


def good_file(path: Path, duration_ms: int) -> bool:
    if not path.is_file() or path.stat().st_size < 800 or path.stat().st_size > MAX_BYTES:
        return False
    try:
        dur = ffprobe_duration(path)
        width, height = ffprobe_size(path)
    except (subprocess.CalledProcessError, ValueError):
        return False
    if width < VIEW_W or height < VIEW_H:
        return False
    return abs(dur - duration_ms / 1000) <= 0.2 and 1.5 <= dur <= 3.05


def record_one(page, hull: str, number: str, duration_ms: int, dest: Path, thumb: Path) -> None:
    work = Path("/tmp/warp-frames") / f"{hull}-{number}"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    meta = page.evaluate("([hull, n]) => window.prepareClip(hull, n)", [hull, number])
    if int(meta["animations"]) < 1:
        raise RuntimeError(f"{hull} {number} painted no animation")
    frames = max(8, int(round(duration_ms / 1000 * FPS)))
    times = [min(duration_ms - 1, int(round(i * 1000 / FPS))) for i in range(frames)]
    mid = times[len(times) // 3]
    for index, at in enumerate(times):
        count = page.evaluate("(ms) => window.seekClip(ms)", at)
        if int(count) < 1:
            raise RuntimeError(f"{hull} {number} lost animation at {at}")
        shot = work / f"{index:03d}.png"
        page.screenshot(path=str(shot), clip={"x": 0, "y": 0, "width": VIEW_W, "height": VIEW_H})
        if at == mid:
            thumb.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(shot, thumb)
    last_error = None
    for crf in (28, 34, 40):
        try:
            encode(work, dest, crf)
        except subprocess.CalledProcessError as exc:
            last_error = exc
            continue
        if good_file(dest, duration_ms):
            shutil.rmtree(work, ignore_errors=True)
            return
    shutil.rmtree(work, ignore_errors=True)
    size = dest.stat().st_size if dest.is_file() else 0
    dur = 0.0
    if dest.is_file():
        try:
            dur = ffprobe_duration(dest)
        except (subprocess.CalledProcessError, ValueError):
            dur = 0.0
    raise RuntimeError(f"{dest} size={size} dur={dur:.3f} target={duration_ms} ({last_error})")


def jobs(only: str) -> list[tuple[str, dict]]:
    doc = json.loads(CLIPS.read_text(encoding="utf-8"))
    want_hull = ""
    want_n = ""
    if only:
        if ":" in only:
            want_hull, want_n = only.split(":", 1)
        else:
            want_hull = only
        want_n = want_n.zfill(2) if want_n else ""
    rows: list[tuple[str, dict]] = []
    for hull, clips in doc["hulls"].items():
        if want_hull and hull != want_hull:
            continue
        for row in clips:
            number = f"{int(row['id'].rsplit('.', 1)[-1]):02d}"
            if want_n and number != want_n:
                continue
            rows.append((hull, row))
    return rows


def write_manifest() -> dict:
    doc = json.loads(CLIPS.read_text(encoding="utf-8"))
    hulls: dict[str, list[dict]] = {}
    for hull, clips in doc["hulls"].items():
        packed = []
        for row in clips:
            number = f"{int(row['id'].rsplit('.', 1)[-1]):02d}"
            rel = f"{hull}/{number}.webm"
            path = OUT / rel
            if not path.is_file():
                continue
            packed.append({
                "n": number,
                "id": row["id"],
                "webm": rel,
                "duration_ms": int(row["duration_ms"]),
                "bytes": path.stat().st_size,
            })
        hulls[hull] = packed
    manifest = {
        "version": 1,
        "note": "Captured pictures of the ten procedural warp scenes for each hull.",
        "generated": {
            "about": GENERATED_ABOUT,
            "clips": [],
        },
        "hulls": hulls,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def contact_sheet(thumbs: Path) -> None:
    from PIL import Image, ImageDraw

    doc = json.loads(CLIPS.read_text(encoding="utf-8"))
    names = list(doc["hulls"])
    tiles = []
    for hull in names:
        row = []
        for n in range(1, 11):
            src = thumbs / f"{hull}-{n:02d}.png"
            if not src.is_file():
                row.append(Image.new("RGB", (120, 78), (16, 16, 16)))
                continue
            img = Image.open(src).convert("RGB")
            img.thumbnail((120, 78))
            row.append(img)
        tiles.append(row)
    width = 120
    height = 78
    label = 18
    sheet = Image.new("RGB", (width * 10, (height + label) * len(names)), (0, 0, 0))
    draw = ImageDraw.Draw(sheet)
    for r, hull in enumerate(names):
        draw.text((4, r * (height + label)), hull, fill=(180, 220, 255))
        for c, img in enumerate(tiles[r]):
            sheet.paste(img, (c * width, label + r * (height + label)))
    ART.mkdir(parents=True, exist_ok=True)
    sheet.save(ART / "contact-sheet.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="", help="hull or hull:NN")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    sync_playwright = __import__("playwright.sync_api", fromlist=["sync_playwright"]).sync_playwright
    server, port = serve()
    thumbs = Path("/tmp/warp-thumbs")
    thumbs.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch(args=["--force-device-scale-factor=1"])
            except Exception:
                browser = pw.chromium.launch(channel="chrome", args=["--force-device-scale-factor=1"])
            page = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H}, device_scale_factor=1)
            page.goto(f"http://127.0.0.1:{port}/stage.html", wait_until="domcontentloaded")
            page.wait_for_function(
                "() => window.TW2KWarpHull && window.TW2KWarpHull.source === 'note126' && window.prepareClip",
                timeout=20_000,
            )
            todo = jobs(args.only)
            for index, (hull, row) in enumerate(todo, start=1):
                number = f"{int(row['id'].rsplit('.', 1)[-1]):02d}"
                dest = OUT / hull / f"{number}.webm"
                ms = int(row["duration_ms"])
                if not args.force and good_file(dest, ms) and (thumbs / f"{hull}-{number}.png").is_file():
                    print(f"skip {hull} {number}", flush=True)
                    continue
                print(f"record {index}/{len(todo)} {hull} {number} {ms}ms", flush=True)
                record_one(page, hull, number, ms, dest, thumbs / f"{hull}-{number}.png")
                print(f"  {dest.stat().st_size} bytes {ffprobe_duration(dest):.3f}s", flush=True)
            browser.close()
    finally:
        server.shutdown()
    manifest = write_manifest()
    if not args.only:
        contact_sheet(thumbs)
        sample = OUT / "merchant_cruiser" / "01.webm"
        if sample.is_file():
            ART.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(sample, ART / "merchant-cruiser-01.webm")
    counted = sum(len(rows) for rows in manifest["hulls"].values())
    print(f"manifest clips {counted}", flush=True)


if __name__ == "__main__":
    main()
