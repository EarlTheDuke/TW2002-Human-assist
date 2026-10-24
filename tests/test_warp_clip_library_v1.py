"""Ten distinct warp clips per hull, only on a real move.

The roll lives in web/warp-variants.js (takeId) and web/media/warp-clips.json.
A captured file is served only when playback is "move" (web/warp-video.js).
Browser coverage of a refused warp and a plotted course stays in
test_cockpit_warp_video_v1.py and test_note146_warp_clips_10_v1.py.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tw2k.engine.models import ShipClass

ROOT = Path(__file__).resolve().parents[1]
CLIPS = ROOT / "web" / "media" / "warp-clips.json"
VARIANTS = ROOT / "web" / "warp-variants.js"
VIDEO = ROOT / "web" / "warp-video.js"
REDESIGN = ROOT / "web" / "redesign.js"
MANIFEST = ROOT / "web" / "warp-video" / "manifest.json"
README = ROOT / "web" / "warp-video" / "README.md"
PLAN = ROOT / "docs" / "plans" / "cockpit-warp-clip-library-v1.md"
HULLS = tuple(cls.value for cls in ShipClass)
MAX_BYTES = 300 * 1024

NODE = r"""
const fs = require("fs");
const vm = require("vm");
const sandbox = {};
sandbox.window = sandbox;
vm.runInNewContext(fs.readFileSync(process.argv[1], "utf8"), sandbox);
const api = sandbox.TW2KWarpVariants;
if (!api || api.styles.length !== 10) {
  console.error("styles");
  process.exit(1);
}
const glows = new Set(api.styles.map((row) => row.glow));
if (glows.size !== 10) process.exit(2);
const signatures = new Set(api.styles.map((row) =>
  [row.camera, row.stars, row.exit, row.glow, row.plume, row.streak, row.flash].join("|")));
if (signatures.size !== 10) process.exit(3);
const hull = "merchant_cruiser";
const ids = api.styles.map((row) => hull + "." + row.style + "." + row.n);
const pictures = ids.map((id, i) => api.stars(id, api.styles[i].stars));
if (new Set(pictures).size !== 10) process.exit(4);
pictures.forEach((html, i) => {
  if (!html.includes(api.styles[i].glow)) process.exit(5);
  if (api.stars(ids[i], api.styles[i].stars) !== html) process.exit(6);
});
let state = { bag: [], last: "" };
const rolled = [];
for (let n = 0; n < 50; n++) {
  state = api.takeId(ids, state);
  rolled.push(state.last);
}
if (rolled.length !== 50) process.exit(7);
if (rolled.some((id, i) => i && id === rolled[i - 1])) process.exit(8);
if (new Set(rolled).size < 10) process.exit(9);
if (!rolled.every((id) => id.startsWith(hull + "."))) process.exit(10);
const pod = api.styles.map((row) => "escape_pod." + row.style + "." + row.n);
let podState = { bag: [], last: "" };
const podRoll = [];
for (let n = 0; n < 10; n++) {
  podState = api.takeId(pod, podState);
  podRoll.push(podState.last);
}
if (new Set(podRoll).size !== 10) process.exit(11);
if (!podRoll.every((id) => id.startsWith("escape_pod."))) process.exit(12);
console.log("ok");
"""


def _probe(path: Path) -> tuple[int, int, float]:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        text=True,
    )
    doc = json.loads(out)
    stream = doc["streams"][0]
    return int(stream["width"]), int(stream["height"]), float(doc["format"]["duration"])


def test_each_hull_rolls_ten_distinct_ids() -> None:
    doc = json.loads(CLIPS.read_text(encoding="utf-8"))
    assert set(doc["hulls"]) == set(HULLS)
    styles = json.loads(
        subprocess.check_output(
            [
                "node",
                "-e",
                "const fs=require('fs');const vm=require('vm');const s={};s.window=s;"
                "vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),s);"
                "process.stdout.write(JSON.stringify(s.TW2KWarpVariants.styles));",
                str(VARIANTS),
            ],
            text=True,
        )
    )
    assert len(styles) == 10
    for hull, rows in doc["hulls"].items():
        assert len(rows) == 10, hull
        ids = [row["id"] for row in rows]
        assert len(set(ids)) == 10
        for row, style in zip(rows, styles, strict=True):
            assert row["id"] == f"{hull}.{style['style']}.{style['n']}"
            assert row["id"].startswith(hull + ".")
            assert row["kind"] == "svg"
            assert row["camera"] == style["camera"]
            assert row["stars"] == style["stars"]
            assert row["exit"] == style["exit"]
            assert row["duration_ms"] == style["duration_ms"]
            assert 1500 <= row["duration_ms"] <= 3000


def test_random_pick_covers_ten_and_does_not_repeat() -> None:
    out = subprocess.check_output(["node", "-e", NODE, str(VARIANTS)], text=True)
    assert out.strip() == "ok"


def test_file_plays_only_for_a_real_move() -> None:
    video = VIDEO.read_text(encoding="utf-8")
    page = REDESIGN.read_text(encoding="utf-8")
    assert 'playback !== "move"' in video
    assert "generated" in video
    assert "function isRealMove" in page
    assert 'ev.kind === "warp"' in page
    assert "hops_done" in page
    assert 'chosen.playback = "move"' in page
    assert "api.takeId" in page
    # A blocked warp is a different event kind, so it never enters the player.
    start = page.index("function isRealMove")
    body = page[start : page.index("async function playWarpClips")]
    assert "warp_blocked" not in body
    assert "plot_course" not in body
    for name in ("bot.html", "bot.js", "bot-parity.js"):
        text = (ROOT / "web" / name).read_text(encoding="utf-8")
        assert "warp-video" not in text
        assert "warp-clips.json" not in text


def test_captured_files_match_the_hull_and_stay_short() -> None:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert doc["generated"]["clips"] == []
    assert "generated (AI)" in doc["generated"]["about"]
    assert set(doc["hulls"]) == set(HULLS)
    for hull, rows in doc["hulls"].items():
        assert len(rows) == 10, hull
        assert [row["n"] for row in rows] == [f"{n:02d}" for n in range(1, 11)]
        for row in rows:
            assert row["id"].startswith(hull + ".")
            assert row["webm"] == f"{hull}/{row['n']}.webm"
            path = ROOT / "web" / "warp-video" / row["webm"]
            assert path.is_file()
            assert path.stat().st_size == row["bytes"]
            assert path.stat().st_size <= MAX_BYTES
            width, height, duration = _probe(path)
            assert (width, height) == (800, 520), path
            assert abs(duration - row["duration_ms"] / 1000) <= 0.2


def test_clip_eleven_and_the_live_gen_hook_are_documented() -> None:
    readme = README.read_text(encoding="utf-8")
    plan = PLAN.read_text(encoding="utf-8")
    for text in (readme, plan):
        assert "11" in text
        assert "generated.clips" in text or "generated/" in text
        assert "playback" in text
    assert "ShipClass" in plan or "ship.class" in plan
    assert "resolve(chosen)" in plan
    variants = VARIANTS.read_text(encoding="utf-8")
    assert 'playback === "move"' in variants
    assert VARIANTS.stat().st_size < 60 * 1024
    assert CLIPS.stat().st_size < 60 * 1024
