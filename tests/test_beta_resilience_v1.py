"""NOTE 141. A killed lobby comes back with the same game, seat, and day clock.

The long cases each start their own lobby process on a free port. The browser
case is its own process and its own page. Nothing here binds 8099.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

import tests._cu_host as cu
import tw2k.engine.constants as K
import tw2k.public.worker as W
from tests._port_lock import release_ports

REPO = Path(__file__).resolve().parents[1]
PLAYER = "ai_cockpit_player.py"


def _fake_runner(universe, day_mark=1_700_000_000.0):
    return SimpleNamespace(state=SimpleNamespace(universe=universe, status="running"), _live_day_mark=day_mark)


def test_a_port_in_time_wait_is_not_a_listener() -> None:
    """A restart must be able to bind while the last connection is still closing."""
    import socket

    from tw2k.public.config import port_is_free

    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = int(server.getsockname()[1])
    try:
        assert not port_is_free(port)
        client = socket.create_connection(("127.0.0.1", port))
        conn, _ = server.accept()
        conn.close()
        client.close()
    finally:
        server.close()
    if os.name != "nt":
        hexport = f"{port:04X}"
        deadline = time.time() + 2
        waiting = False
        while time.time() < deadline:
            text = Path("/proc/net/tcp").read_text(encoding="utf-8", errors="replace")
            waiting = any(
                line.split()[1].endswith(":" + hexport) and line.split()[3] == "06"
                for line in text.splitlines()[1:]
                if len(line.split()) > 3
            )
            if waiting:
                break
            time.sleep(0.05)
        assert waiting, "the closed server port did not reach time-wait"
    assert port_is_free(port)


def test_a_good_snapshot_is_kept_and_a_broken_one_is_named(tmp_path) -> None:
    from tw2k.engine import GameConfig, generate_universe

    universe = generate_universe(GameConfig(seed=11, universe_size=60, max_days=2))
    runner = _fake_runner(universe)
    good = W.write_snapshot(runner, "play", tmp_path)
    assert good is not None
    meta, _loaded = W.load_snapshot(good)
    assert meta["day_started_at"] == 1_700_000_000.0
    assert meta["day_seconds"] == float(K.TURN_REGEN_DAY_SECONDS)
    broken = tmp_path / "snap-999999999999999.jsonl"
    broken.write_text("this is not a save\n", encoding="utf-8")
    chosen, corrupt = W.choose_snapshot(tmp_path)
    assert chosen == good and corrupt is False
    good.unlink()
    chosen, corrupt = W.choose_snapshot(tmp_path)
    assert chosen is None and corrupt is True
    empty, flag = W.choose_snapshot(tmp_path / "missing")
    assert empty is None and flag is False


def test_rewrite_puts_the_lobby_prefix_on_the_seat_socket() -> None:
    source = (REPO / "web" / "redesign.js").read_text(encoding="utf-8")
    assert "Lost the host. Reconnecting." in source
    assert "linkDelay * 2" in source
    rewritten = W.rewrite_text("/static/redesign.js", 'new WebSocket(`${location.host}/ws`)',
                               base="/g/ab12", brand_name="")
    assert rewritten == 'new WebSocket(`${location.host}/g/ab12/ws`)'


def test_one_does_not_turn_on_full_length_or_the_cockpit(monkeypatch) -> None:
    monkeypatch.setattr(K, "FULL_LENGTH_TURN_LIMITS_MODE", "legacy")
    monkeypatch.setattr(K, "AI_COCKPIT_SEAT_MODE", "legacy")
    monkeypatch.setenv("FULL_LENGTH_TURN_LIMITS_MODE", "1")
    monkeypatch.setenv("AI_COCKPIT_SEAT_MODE", "1")
    from tw2k.public.lobby import _apply_host_switches

    _apply_host_switches()
    assert K.FULL_LENGTH_TURN_LIMITS_MODE == "legacy"
    assert K.AI_COCKPIT_SEAT_MODE == "legacy"


def _block(n: int) -> int:
    base = cu.free_port(cu.LOBBY_FREE_START, count=n)
    assert base != 8099 and cu.allowed_test_port(base)
    for port in range(base, base + n):
        assert port != 8099 and cu.allowed_test_port(port)
    return base


def _env(root: Path, base: int) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("TW2K_", "TW2002_"))}
    env.update(
        TW2K_LOBBY_ROOT=str(root),
        TW2K_LOBBY_PORT=str(base),
        TW2K_GAME_PORTS=f"{base + 1}-{base + 3}",
        PYTHONPATH=str(REPO / "src") + os.pathsep + str(REPO),
        PYTHONIOENCODING="utf-8",
        AI_COCKPIT_SEAT_MODE="tw2002",
        FULL_LENGTH_TURN_LIMITS_MODE="v311",
    )
    return env


def _start(env: dict[str, str], root: Path, url: str) -> subprocess.Popen:
    out = open(root / "lobby.out", "ab")  # noqa: SIM115  the lobby keeps this handle
    proc = subprocess.Popen(
        [sys.executable, "-m", "tw2k.cli", "lobby"],
        env=env, cwd=str(REPO), stdout=out, stderr=subprocess.STDOUT, start_new_session=True,
    )
    deadline = time.time() + 90
    try:
        while time.time() < deadline:
            if proc.poll() is not None:
                raise AssertionError((root / "lobby.out").read_text(encoding="utf-8", errors="replace")[-4000:])
            try:
                if httpx.get(url + "/healthz", timeout=2).status_code == 200:
                    return proc
            except httpx.HTTPError:
                time.sleep(0.3)
        raise AssertionError("lobby did not come up\n" + (root / "lobby.out").read_text(encoding="utf-8", errors="replace")[-4000:])
    except Exception:
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                proc.kill()
        proc.wait(10)
        raise


def _alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _kill_tree(proc: subprocess.Popen | None, extra: list[int]) -> None:
    if proc is None:
        for pid in extra:
            if _alive(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
        return
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            proc.kill()
    for pid in extra:
        if _alive(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    try:
        proc.wait(10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(10)


def _pids_for(root: Path, gid: str) -> list[int]:
    found = []
    db = root / "lobby.sqlite3"
    if db.exists():
        import sqlite3

        con = sqlite3.connect(str(db))
        try:
            row = con.execute("SELECT pid FROM games WHERE id=?", (gid,)).fetchone()
        finally:
            con.close()
        if row and row[0]:
            found.append(int(row[0]))
    pid_path = root / "games" / gid / "ai-cockpit" / "player.pid"
    if pid_path.is_file():
        text = pid_path.read_text(encoding="ascii").strip()
        if text.isdigit():
            found.append(int(text))
    return found


def _player_pids(root: Path, gid: str) -> list[int]:
    """The cockpit command line is long, so `ps` truncates it. Read /proc instead."""
    run = str(root / "games" / gid / "ai-cockpit")
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        text = raw.replace(b"\x00", b" ").decode("utf-8", errors="replace")
        if PLAYER in text and run in text:
            found.append(int(entry.name))
    return found


def _listen_pids(port: int) -> list[int]:
    hexport = f"{port:04X}"
    inodes: set[str] = set()
    for name in ("tcp", "tcp6"):
        try:
            lines = (Path("/proc/net") / name).read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 10 or parts[3] != "0A" or not parts[1].endswith(":" + hexport):
                continue
            inodes.add(parts[9])
    if not inodes:
        return []
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        fd_dir = entry / "fd"
        try:
            links = [os.readlink(fd) for fd in fd_dir.iterdir()]
        except OSError:
            continue
        if any(link.startswith("socket:[") and link[8:-1] in inodes for link in links):
            found.append(int(entry.name))
    return found


def _port_states(port: int) -> list[str]:
    hexport = f"{port:04X}"
    found = []
    for name in ("tcp", "tcp6"):
        try:
            lines = (Path("/proc/net") / name).read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines[1:]:
            parts = line.split()
            if len(parts) > 3 and (parts[1].endswith(":" + hexport) or parts[2].endswith(":" + hexport)):
                found.append(f"{name} {parts[1]} {parts[2]} {parts[3]}")
    return found


def _wait_port(port: int) -> None:
    from tw2k.public.config import port_is_free

    deadline = time.time() + 20
    while time.time() < deadline:
        if port_is_free(port):
            return
        for pid in _listen_pids(port):
            if _alive(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
        time.sleep(0.2)
    raise AssertionError(f"port {port} stayed busy ({_listen_pids(port)}; {_port_states(port)})")


def test_kill_and_restart_keeps_the_game_the_seat_and_the_clock(tmp_path: Path) -> None:
    base = _block(4)
    root = tmp_path / "selfhost"
    root.mkdir()
    env = _env(root, base)
    url = f"http://127.0.0.1:{base}"
    lob = None
    gid = ""
    try:
        lob = _start(env, root, url)
        client = httpx.Client(base_url=url, timeout=120)
        assert client.post("/api/accept", json={}).status_code == 200
        created = client.post("/api/games", json={
            "name": "Still here",
            "rules": "v311",
            "universe_size": 200,
            "max_days": 30,
            "bots": 0,
            "humans": 1,
            "ferrengi": False,
            "game_length": "full",
            "ai_cockpit": True,
            "ai_cockpit_provider": "scripted",
        }).json()
        assert created.get("status") == "running", created
        gid = created["id"]
        claim = client.post(f"/api/games/{gid}/join", json={}).json()["claim_url"]
        token = claim.split("token=", 1)[1]
        assert client.get(claim, follow_redirects=False).status_code == 303
        headers = {"authorization": f"Bearer {token}", "X-TW2K-Seat": "P1"}

        def observe() -> dict:
            response = client.get(f"/g/{gid}/harness/v1/P1/observation?peek=1&format=json", headers=headers)
            assert response.status_code == 200, response.text[:400]
            return response.json()

        deadline = time.time() + 40
        first = None
        while time.time() < deadline:
            body = observe()
            clock = body.get("turn_clock") or {}
            if clock.get("day_started_at") and clock.get("day_seconds") == 86400:
                first = body
                break
            time.sleep(0.4)
        assert first is not None, "the full-length day clock did not start"
        snaps = root / "games" / gid / "snapshots"
        deadline = time.time() + 20
        while time.time() < deadline and not list(snaps.glob("snap-*.jsonl")):
            time.sleep(0.3)
        assert list(snaps.glob("snap-*.jsonl")), "the game did not autosave"
        posted = client.post(f"/g/{gid}/harness/v1/P1/action", headers=headers, json={"action": {"kind": "wait"}})
        if posted.status_code == 200:
            before = max(path.stat().st_mtime for path in snaps.glob("snap-*.jsonl"))
            deadline = time.time() + 20
            while time.time() < deadline:
                newer = [path for path in snaps.glob("snap-*.jsonl") if path.stat().st_mtime > before + 0.01]
                if newer:
                    break
                time.sleep(0.3)
        deadline = time.time() + 30
        players = []
        while time.time() < deadline:
            players = [pid for pid in _player_pids(root, gid) if _alive(pid)]
            if players:
                break
            time.sleep(0.4)
        assert players, (root / "lobby.out").read_text(encoding="utf-8", errors="replace")[-2000:]
        old_player = players[0]
        for pid in players:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        deadline = time.time() + 8
        while time.time() < deadline and any(_alive(pid) for pid in players):
            time.sleep(0.2)
        quiet = observe()
        clock = quiet["turn_clock"]
        assert clock.get("day_seconds") == 86400 and clock.get("day_started_at")
        snaps = root / "games" / gid / "snapshots"
        deadline = time.time() + 15
        saved = None
        while time.time() < deadline:
            files = sorted(snaps.glob("snap-*.jsonl"))
            if files and time.time() - files[-1].stat().st_mtime > 2.5:
                saved = files[-1]
                break
            time.sleep(0.3)
        assert saved is not None, "the quiet game did not finish its autosave"
        meta, universe = W.load_snapshot(saved)
        started = float(meta["day_started_at"])
        seat = universe.players["P1"]
        sector = int(seat.sector_id)
        credits = int(seat.credits)
        left_n = max(0, int(seat.turns_per_day) - int(seat.turns_today))
        left = f"Turns left today: {left_n:,} of {int(seat.turns_per_day):,}"
        home = client.get("/").text
        assert "Still here" in home
        cookies = dict(client.cookies)
        client.close()
        extra = _pids_for(root, gid)
        _kill_tree(lob, extra)
        _wait_port(base)
        lob = _start(env, root, url)
        client = httpx.Client(base_url=url, timeout=120, cookies=cookies)
        assert client.get("/healthz").status_code == 200
        listed = client.get("/api/games").json()["games"]
        assert any(row["id"] == gid and row["status"] == "running" for row in listed)
        assert "Still here" in client.get("/").text
        again = observe()
        again_clock = again["turn_clock"]
        assert abs(float(again_clock["day_started_at"]) - started) < 1.0
        assert again_clock["day_seconds"] == 86400
        assert abs(float(again_clock["next_day_at"]) - (started + 86400)) < 1.0
        assert again["observation"]["sector"]["id"] == sector
        assert again["observation"]["credits"] == credits
        assert (again.get("turns_left_line") or "") == left
        assert client.get(claim, follow_redirects=False).status_code == 303
        deadline = time.time() + 40
        restarted = []
        while time.time() < deadline:
            restarted = [pid for pid in _player_pids(root, gid) if _alive(pid) and pid != old_player]
            if restarted:
                break
            time.sleep(0.4)
        assert restarted, "the AI cockpit did not come back"
        logs = "".join(path.read_text(encoding="utf-8", errors="replace") for path in (root / "logs").glob("*.log*"))
        assert token not in logs
    finally:
        extra = _pids_for(root, gid) if gid else []
        extra += _player_pids(root, gid) if gid else []
        _kill_tree(lob, extra)
        release_ports(*range(base, base + 4))


def test_a_corrupt_save_is_a_lobby_message(tmp_path: Path) -> None:
    base = _block(4)
    root = tmp_path / "selfhost"
    root.mkdir()
    env = _env(root, base)
    env["AI_COCKPIT_SEAT_MODE"] = "legacy"
    env["FULL_LENGTH_TURN_LIMITS_MODE"] = "legacy"
    url = f"http://127.0.0.1:{base}"
    lob = None
    gid = ""
    try:
        lob = _start(env, root, url)
        client = httpx.Client(base_url=url, timeout=120)
        assert client.post("/api/accept", json={}).status_code == 200
        created = client.post("/api/games", json={
            "name": "Torn page",
            "universe_size": 200,
            "bots": 0,
            "humans": 1,
            "ferrengi": False,
            "day": "10m",
        }).json()
        assert created.get("status") == "running", created
        gid = created["id"]
        snaps = root / "games" / gid / "snapshots"
        deadline = time.time() + 30
        while time.time() < deadline and not list(snaps.glob("snap-*.jsonl")):
            time.sleep(0.3)
        assert list(snaps.glob("snap-*.jsonl"))
        cookies = dict(client.cookies)
        client.close()
        extra = _pids_for(root, gid)
        _kill_tree(lob, extra)
        _wait_port(base)
        for path in snaps.glob("snap-*.jsonl"):
            path.write_text("{not a save\n", encoding="utf-8")
        lob = _start(env, root, url)
        client = httpx.Client(base_url=url, timeout=120, cookies=cookies)
        assert client.get("/healthz").status_code == 200
        page = client.get("/")
        assert page.status_code == 200
        assert "could not be read" in page.text
        assert "Torn page" in page.text
        assert "Traceback" not in page.text
        row = client.get(f"/api/games/{gid}").json()
        assert row["status"] == "failed"
        game_page = client.get(f"/g/{gid}/bot", headers={"accept": "text/html"})
        assert game_page.status_code == 410
        assert "could not be read" in game_page.text
        assert "Traceback" not in game_page.text
    finally:
        extra = _pids_for(root, gid) if gid else []
        _kill_tree(lob, extra)
        release_ports(*range(base, base + 4))


def test_a_dropped_socket_backs_off_and_resyncs(tmp_path: Path) -> None:
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    token = "resilience-seat-token-p2-0000000001"
    host = cu.CuHost(tmp_path, token)
    host.__enter__()
    assert host.port != 8099 and cu.allowed_test_port(host.port)
    pw = sync().start()
    browser = pw.chromium.launch()
    try:
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={token}")
        page.wait_for_function("() => document.querySelector('#pSector').textContent !== '-'", timeout=20_000)
        sector = page.locator("#pSector").inner_text()
        page.evaluate(
            """() => {
              const Real = window.WebSocket;
              let left = 1;
              function Wrapped(url, protocols) {
                if (left > 0) { left -= 1; throw new Error('down'); }
                return new Real(url, protocols);
              }
              window.WebSocket = Wrapped;
              window.__tw2kLink.drop();
            }"""
        )
        page.wait_for_function(
            "() => document.querySelector('#err') && document.querySelector('#err').dataset.kind === 'reconnect'",
            timeout=10_000,
        )
        page.wait_for_function(
            """() => {
              const waits = window.__tw2kLink.waits();
              const err = document.querySelector('#err');
              const back = !err || err.hidden || err.dataset.kind !== 'reconnect';
              return window.__tw2kLink.attempts() >= 3
                && waits.indexOf(500) >= 0 && waits.indexOf(1000) >= 0 && back
                && document.querySelector('#pSector').textContent !== '-';
            }""",
            timeout=15_000,
        )
        assert page.locator("#pSector").inner_text() == sector
        assert page.evaluate("() => window.__tw2kLink.attempts()") >= 3
    finally:
        browser.close()
        pw.stop()
        host.__exit__(None, None, None)
