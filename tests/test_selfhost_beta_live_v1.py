"""selfhost-beta-v1 item 8: the real lobby and real `tw2k serve` workers on free ephemeral ports.

Two games through the lobby's HTTP API: claim a seat through the proxy, play an action, open the
spectator websocket through the proxy, check one game's seat token is useless in the other,
stop the lobby gracefully and confirm both games come back from their snapshots.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from tw2k.public.config import port_is_free

REPO = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows host (job object, CREATE_NO_WINDOW)")


def _free_block(n: int) -> int:
    from tests._port_lock import claim_ports

    return claim_ports(n, low=40000, high=46000)


def _start(env: dict, root: Path, url: str) -> subprocess.Popen:
    p = subprocess.Popen([sys.executable, "-m", "tw2k.cli", "lobby"], env=env, cwd=str(REPO),
                         stdout=open(root / "lobby.out", "ab"), stderr=subprocess.STDOUT)
    deadline = time.time() + 60
    while time.time() < deadline:
        assert p.poll() is None, (root / "lobby.out").read_text(errors="replace")
        try:
            if httpx.get(url + "/healthz", timeout=2).status_code == 200:
                return p
        except httpx.HTTPError:
            time.sleep(0.3)
    raise AssertionError("lobby did not come up")


def _stop(p: subprocess.Popen, root: Path, url: str) -> None:
    key = (root / "lobby.shutdown.key").read_text().strip()
    assert httpx.post(url + "/admin/shutdown", headers={"x-lobby-shutdown": key}).status_code == 200
    p.wait(60)


def test_item8_two_real_games_through_the_lobby(tmp_path) -> None:
    base = _free_block(4)
    root = tmp_path / "selfhost"
    root.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("TW2K_", "TW2002_"))}
    env.update(TW2K_LOBBY_ROOT=str(root), TW2K_LOBBY_PORT=str(base), TW2K_GAME_PORTS=f"{base + 1}-{base + 3}",
               TW2K_LOBBY_DAY_PRESETS="2m=120", PYTHONPATH=str(REPO / "src"))
    url = f"http://127.0.0.1:{base}"
    lob = _start(env, root, url)
    try:
        a = httpx.Client(base_url=url, timeout=90)
        b = httpx.Client(base_url=url, timeout=90)
        for c in (a, b):
            assert c.post("/api/accept", json={}).status_code == 200
        g1 = a.post("/api/games", json={"name": "Live one", "day": "2m", "bots": 2, "universe_size": 200}).json()
        g2 = b.post("/api/games", json={"name": "Live two", "day": "2m", "bots": 1, "universe_size": 200,
                                        "rules": "legacy", "starting_package": "classic"}).json()
        assert g1["status"] == g2["status"] == "running"
        claims = {}
        for c, g in ((a, g1), (b, g2)):
            claim = c.post(f"/api/games/{g['id']}/join", json={}).json()["claim_url"]
            claims[g["id"]] = claim.split("token=")[1]
            r = c.get(claim, follow_redirects=False)
            assert r.status_code == 303 and r.headers["location"].startswith(f"/g/{g['id']}/bot")
            c.get(r.headers["location"])
        obs = a.get(f"/g/{g1['id']}/harness/v1/P1/observation?peek=1", headers={"X-TW2K-Seat": "P1"})
        assert obs.status_code == 200
        page = a.get(f"/g/{g1['id']}/bot", headers={"accept": "text/html"}).text
        assert "<title>Galaxy War Command</title>" in page and f'src="/g/{g1["id"]}/static/' in page

        # one game's seat token is useless in the other, and in the other seat
        leak = httpx.get(f"{url}/g/{g2['id']}/harness/v1/P1/observation?peek=1",
                         headers={"authorization": f"Bearer {claims[g1['id']]}"},
                         cookies={"gwc_guest": a.cookies.get("gwc_guest")})
        assert leak.status_code == 401
        assert a.get(f"/g/{g2['id']}/harness/v1/P1/observation?peek=1",
                     headers={"X-TW2K-Seat": "P1"}).status_code == 401
        assert a.post(f"/g/{g1['id']}/control/pause").status_code == 404
        assert a.get(f"/g/{g1['id']}/api/state").status_code in (403, 404)

        # spectator over the proxied websocket
        watcher = httpx.Client(base_url=url, timeout=30)
        watcher.post("/api/accept", json={})
        assert watcher.get(f"/g/{g1['id']}/watch", follow_redirects=False).status_code == 303
        state = watcher.get(f"/g/{g1['id']}/state")
        assert state.status_code == 200 and state.json()["status"] in ("running", "paused")

        async def ws_frame() -> str:
            from websockets.asyncio.client import connect

            cookie = "; ".join(f"{k}={v}" for k, v in watcher.cookies.items())
            async with connect(f"ws://127.0.0.1:{base}/g/{g1['id']}/ws",
                               additional_headers={"cookie": cookie}, open_timeout=10) as ws:
                return await asyncio.wait_for(ws.recv(), 15)

        assert json.loads(asyncio.run(ws_frame()))

        # graceful lobby restart: both games come back from snapshots with rotated tokens
        _stop(lob, root, url)
        for g in (g1, g2):
            assert list((root / "games" / g["id"] / "snapshots").glob("snap-*.jsonl"))
        lob = _start(env, root, url)
        for g in (g1, g2):
            assert a.get(f"/api/games/{g['id']}").json()["status"] == "running"
        assert a.get(f"/g/{g1['id']}/harness/v1/P1/observation?peek=1",
                     headers={"X-TW2K-Seat": "P1"}).status_code == 401
        again = a.post(f"/api/games/{g1['id']}/resume", json={}).json()["claim_url"]
        a.get(again)
        assert a.get(f"/g/{g1['id']}/harness/v1/P1/observation?peek=1",
                     headers={"X-TW2K-Seat": "P1"}).status_code == 200
        _stop(lob, root, url)
        logs = "".join(p.read_text(encoding="utf-8", errors="replace") for p in (root / "logs").glob("*.log*"))
        for tok in list(claims.values()) + [again.split("token=")[1], a.cookies.get("gwc_guest")]:
            assert tok not in logs
    finally:
        if lob.poll() is None:
            lob.kill()
            lob.wait(10)
        from tests._port_lock import release_ports

        release_ports(*range(base, base + 4))
    for port in range(base, base + 4):
        assert port_is_free(port)
