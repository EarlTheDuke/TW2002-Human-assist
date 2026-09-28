"""Citadel custom clip playback. Flag on, fake provider, no network."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

import pytest

from tests._cu_host import VIEW_H, VIEW_W, CuHost
from tw2k.engine.models import EventKind
from tw2k.media.custom_queue import current

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "web" / "media" / "clips" / "custom"
TOK = "v8a-playback-token-p2-00000000"
CIT = {
    "seq": 900,
    "kind": "citadel_complete",
    "actor_id": "P2",
    "sector_id": 19,
    "facts": {"planet_id": 1, "from": 0, "to": 1},
}
OBS = {"self_id": "P2", "sector": {"id": 19}}


class Gate:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()

    def __call__(self, job: dict) -> bytes:
        self.started.set()
        assert self.release.wait(8)
        return b"fake-webm"


def _clear_cache() -> None:
    if not CACHE.is_dir():
        return
    for path in CACHE.iterdir():
        if path.name == ".gitkeep" or not path.is_file():
            continue
        path.unlink()


def _hold_first(bucket: list):
    def handle(route) -> None:
        if not bucket and "media/moments" in route.request.url:
            bucket.append(route)
            return
        route.continue_()

    return handle


def _urls(page) -> list[str]:
    seen: list[str] = []
    page.on("request", lambda req: seen.append(req.url))
    return seen


def _arm_citadel(page) -> None:
    page.wait_for_function("window.TW2KMedia && window.TW2KMedia.ready()", timeout=20_000)
    page.evaluate(
        """(pack) => {
            TW2KMedia._prime({ lastSeq: 0, visit_sector: 19, docked_in_visit: false });
            TW2KMedia.onEvents([pack.ev], pack.obs);
        }""",
        {"ev": CIT, "obs": OBS},
    )


@pytest.mark.skipif(os.environ.get("TW2K_VIDEO_CUSTOM") == "1", reason="this test owns the flag")
def test_custom_clip_plays_or_lands_in_moments(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TW2K_VIDEO_CUSTOM", "1")
    _clear_cache()
    gate = Gate()
    held: list = []
    with CuHost(tmp_path, TOK) as host:
        queue = current()
        assert queue is not None
        queue.provider = gate
        ctx = browser.new_context(viewport={"width": VIEW_W, "height": VIEW_H})
        live = ctx.new_page()
        live_urls = _urls(live)
        live.route("**/media/moments**", _hold_first(held))
        live.goto(f"{host.base}/bot?seat=P2&viewport=live&token={TOK}")
        live.wait_for_function(
            "() => window.TW2KMedia && TW2KMedia._state && TW2KMedia._state().videoCustom === true",
            timeout=20_000,
        )
        for _ in range(50):
            if held:
                break
            live.wait_for_timeout(100)
        assert held, "moments poll never started"
        _arm_citadel(live)
        live.wait_for_function("() => window.TW2KMedia._state().playing === 'planet.citadel'", timeout=10_000)

        universe = host.runner.state.universe
        me = universe.players["P2"]
        universe.emit(
            EventKind.CITADEL_COMPLETE,
            actor_id="P2",
            sector_id=me.sector_id,
            payload={"planet_id": 1, "from": 0, "to": 1},
            summary="citadel",
        )
        assert gate.started.wait(5)
        gate.release.set()
        feed = {}
        for _ in range(50):
            feed = queue.feed_for("P2")
            if any(note.get("swap") and note.get("placeholder") == "planet.citadel" for note in feed["ready"]):
                break
            live.wait_for_timeout(100)
        assert any(note.get("placeholder") == "planet.citadel" and note.get("swap") for note in feed["ready"])
        assert live.evaluate("() => window.TW2KMedia._state().playing") == "planet.citadel"
        held[0].fulfill(status=200, content_type="application/json", body=json.dumps(feed))
        live.wait_for_function("() => !!document.querySelector('video[data-custom]')", timeout=10_000)
        assert any("/media/custom/" in url for url in live_urls)

        quiet = ctx.new_page()
        quiet_urls = _urls(quiet)
        quiet.goto(f"{host.base}/bot?seat=P2&viewport=live&token={TOK}")
        quiet.wait_for_function(
            "() => window.TW2KMedia && TW2KMedia._state && TW2KMedia._state().videoCustom === true",
            timeout=20_000,
        )
        _arm_citadel(quiet)
        quiet.wait_for_function("() => window.TW2KMedia._state().playing === 'planet.citadel'", timeout=10_000)
        quiet.wait_for_function("() => window.TW2KMedia._state().playing !== 'planet.citadel'", timeout=8_000)
        quiet.wait_for_selector("#mediaMoments li", timeout=15_000)
        quiet.wait_for_timeout(10_000)
        rows = quiet.locator("#mediaMoments li")
        assert rows.count() == 1
        assert "live-generated" in (rows.first.inner_text() or "")
        assert "trust: auto" in (rows.first.inner_text() or "")
        assert not any("/media/custom/" in url for url in quiet_urls)

        cu = ctx.new_page()
        cu_urls = _urls(cu)
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_selector("#mediaMoments li", state="attached", timeout=15_000)
        assert cu.evaluate("document.scrollingElement.scrollHeight") == VIEW_H
        assert not any("/media/custom/" in url for url in cu_urls)

        reduced_ctx = browser.new_context(
            viewport={"width": VIEW_W, "height": VIEW_H}, reduced_motion="reduce",
        )
        reduced = reduced_ctx.new_page()
        reduced_urls = _urls(reduced)
        reduced.goto(f"{host.base}/bot?seat=P2&viewport=live&token={TOK}")
        reduced.wait_for_selector("#mediaMoments li", state="attached", timeout=15_000)
        reduced.wait_for_timeout(1000)
        assert not any("/media/custom/" in url for url in reduced_urls)
        reduced.close()
        reduced_ctx.close()
        cu.close()
        quiet.close()
        live.close()
        ctx.close()
