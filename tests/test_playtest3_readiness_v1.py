"""NOTE 136 playtest3-readiness-v1.

Ben's beta flow: a lobby game with starting credits, AI seats, a scripted
cockpit seat, full-length days, and the redesign cockpit. Two people open
the &token= seat links through an https proxy. Each plays, then the creator
ends the game.

The clock nudge is off unless PLAYTEST_CLOCK_NUDGE_MODE=on. "1" does not flip it.
"""

from __future__ import annotations

import asyncio
import datetime
import http.client
import ipaddress
import json
import os
import ssl
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

import tests._cu_host as cu
import tw2k.engine.constants as K
from tw2k.public import pages
from tw2k.public import worker as W
from tw2k.public.workers import admin_headers

ROOT = Path(__file__).resolve().parents[1]
# Screenshots of a run. TW2K_SHOT_DIR overrides; the default is a temp folder,
# so a box without /opt/cursor (or a read-only one) can still run the test.
SHOTS = Path(os.environ.get("TW2K_SHOT_DIR") or (Path(tempfile.gettempdir()) / "tw2k_note136"))


def test_clock_nudge_stays_legacy_until_it_is_turned_on(monkeypatch) -> None:
    assert K.PLAYTEST_CLOCK_NUDGE_MODE == "legacy"
    assert K.playtest_clock_nudge_on() is False
    monkeypatch.setattr(K, "PLAYTEST_CLOCK_NUDGE_MODE", "1")
    assert K.playtest_clock_nudge_on() is False
    monkeypatch.setattr(K, "PLAYTEST_CLOCK_NUDGE_MODE", "on")
    assert K.playtest_clock_nudge_on() is True
    assert "/manual" in W.OPEN_EXACT


def test_join_form_keeps_the_invite_key() -> None:
    html = pages.join_confirm(
        "Galaxy War Command",
        game={"id": "ab12", "name": "Alpha", "settings": {"day_seconds": 86400}},
        seat="P2",
        key="invite-secret",
    )
    assert 'name="k" value="invite-secret"' in html
    assert "Real time, 24 h" in html
    assert 'value="24h"' not in html


def test_worker_accepts_the_game_prefix_on_its_own_port() -> None:
    """The scripted seat opens the worker directly, and the page asks for /g/<id>/static."""
    seen: dict[str, str] = {}

    async def app(scope, receive, send):
        seen["path"] = scope.get("path") or ""
        seen["raw"] = (scope.get("raw_path") or b"").decode("ascii")

    async def receive():
        return {"type": "http.request"}

    async def send(_message):
        return None

    gate = W.AcceptBasePath(app, base="/g/ab12")

    async def hit(path: str) -> None:
        await gate({"type": "http", "path": path, "raw_path": path.encode("ascii")}, receive, send)

    asyncio.run(hit("/g/ab12/static/redesign.js"))
    assert seen["path"] == "/static/redesign.js"
    assert seen["raw"] == "/static/redesign.js"
    asyncio.run(hit("/static/redesign.css"))
    assert seen["path"] == "/static/redesign.css"
    asyncio.run(hit("/g/ab12/harness/v1/P4/observation"))
    assert seen["path"] == "/harness/v1/P4/observation"
    asyncio.run(hit("/g/other/static/redesign.js"))
    assert seen["path"] == "/g/other/static/redesign.js"


def test_created_page_shows_the_cockpit_token_link() -> None:
    link = "https://blue-pond.trycloudflare.com/g/ab12/bot?seat=P1&token=sekret&layout=redesign"
    html = pages.created(
        "Galaxy War Command",
        game={"id": "ab12", "name": "Alpha", "settings": {"day_seconds": 86400, "game_length": "full"}},
        join_links=[("P1", "https://blue-pond.trycloudflare.com/join/ab12/P1?k=invite")],
        watch_link="https://blue-pond.trycloudflare.com/g/ab12/watch",
        cockpit_links=[("P1", link)],
    )
    assert 'data-testid="seat-link"' in html
    assert "layout=redesign" in html and "token=sekret" in html
    assert "Send each player their cockpit link" in html
    assert "Full-length game" in html


class _Proxy(BaseHTTPRequestHandler):
    """The public TLS edge in front of the lobby, with keep-alive on both legs.

    The first version spoke HTTP/1.0 to the browser and opened a fresh
    upstream connection per request. Two cockpits polling every two seconds
    left thousands of TIME_WAIT sockets on Windows, and Chromium began to
    get ERR_NO_BUFFER_SPACE: assets that never loaded, polls that stopped.
    """

    protocol_version = "HTTP/1.1"
    lobby_port = 0
    public_host = ""
    timeout = 330

    def log_message(self, fmt: str, *args) -> None:
        return

    def _upstream(self, fresh: bool = False) -> http.client.HTTPConnection:
        conn = getattr(self, "_conn", None)
        if conn is None or fresh:
            if conn is not None:
                conn.close()
            # The create POST waits out a slow worker boot. This has to outlive it.
            conn = http.client.HTTPConnection("127.0.0.1", self.lobby_port, timeout=300)
            self._conn = conn
        return conn

    def finish(self) -> None:
        conn = getattr(self, "_conn", None)
        if conn is not None:
            conn.close()
        super().finish()

    def _forward(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        host = self.public_host
        headers = {
            k: v
            for k, v in self.headers.items()
            if k.lower() not in ("host", "content-length", "accept-encoding", "connection", "keep-alive")
        }
        headers["Host"] = host
        headers["X-Forwarded-Proto"] = "https"
        headers["X-Forwarded-Host"] = host
        headers["X-Forwarded-For"] = "127.0.0.1"
        for attempt in (0, 1):
            conn = self._upstream(fresh=attempt > 0)
            try:
                conn.request(self.command, self.path, body=body, headers=headers)
                resp = conn.getresponse()
                data = resp.read()
                break
            except (http.client.RemoteDisconnected, BrokenPipeError, ConnectionResetError):
                # uvicorn closed an idle keep-alive socket; a request it never read is safe to resend.
                if attempt:
                    raise
        if resp.will_close:
            self._upstream(fresh=True)
        self.send_response(resp.status)
        for key, value in resp.getheaders():
            if key.lower() in ("transfer-encoding", "connection", "content-length", "keep-alive"):
                continue
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def do_GET(self) -> None:
        self._forward()

    def do_POST(self) -> None:
        self._forward()

    def do_HEAD(self) -> None:
        self._forward()


class _TLSProxyServer(ThreadingHTTPServer):
    """TLS per connection, in that connection's own thread.

    Wrapping the listening socket ran every handshake inside accept() on the
    one serve_forever thread, with no timeout. Chromium opens speculative
    sockets that may never send a ClientHello, and one of those stalled every
    later request: a cockpit tab that never loaded, or polls that stopped
    for good while the direct-to-worker AI seat played on (the Windows hang).
    """

    daemon_threads = True

    def __init__(self, address, handler, ctx: ssl.SSLContext) -> None:
        self.tls = ctx
        super().__init__(address, handler)

    def finish_request(self, request, client_address) -> None:
        request.settimeout(15)
        try:
            request = self.tls.wrap_socket(request, server_side=True)
        except (OSError, ssl.SSLError):
            request.close()
            return
        super().finish_request(request, client_address)


def _cert(directory: Path) -> tuple[str, str]:
    """A one-day cert for 127.0.0.1, written with the cryptography library."""
    pytest.importorskip("cryptography")
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    cert_path = directory / "proxy.crt"
    key_path = directory / "proxy.key"
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    now = datetime.datetime.now(datetime.UTC)
    builder = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(private.public_key())
        .serial_number(x509.random_serial_number())
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))]),
            critical=False,
        )
    )
    if hasattr(builder, "not_valid_before_utc"):
        builder = builder.not_valid_before_utc(now).not_valid_after_utc(now + datetime.timedelta(days=1))
    else:
        naive = now.replace(tzinfo=None)
        builder = builder.not_valid_before(naive).not_valid_after(naive + datetime.timedelta(days=1))
    issued = builder.sign(private, hashes.SHA256())
    key_path.write_bytes(private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    cert_path.write_bytes(issued.public_bytes(serialization.Encoding.PEM))
    return str(cert_path), str(key_path)


def test_the_proxy_cert_loads_from_python(tmp_path) -> None:
    pytest.importorskip("cryptography")
    cert, key = _cert(tmp_path)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    text = Path(cert).read_text(encoding="utf-8")
    assert "BEGIN CERTIFICATE" in text


def _wait_http(url: str, timeout_s: float = 30) -> None:
    import httpx

    deadline = time.time() + timeout_s
    last = ""
    while time.time() < deadline:
        try:
            if httpx.get(url, timeout=1.0, verify=False).status_code < 500:
                return
        except Exception as exc:
            last = str(exc)
        time.sleep(0.2)
    raise RuntimeError(f"never answered {url}: {last}")


def _wait_seat_links(page, timeout_s: float = 60) -> None:
    """The created page has the links, or it is the boot-failure page.

    Waiting out a selector timeout hid that page. The create click already
    waited for the worker, so this only covers the HTML arriving.
    """
    deadline = time.time() + timeout_s
    last = ""
    while time.time() < deadline:
        if page.locator("[data-testid=seat-link]").count():
            return
        try:
            last = " ".join(page.locator("body").inner_text(timeout=1_000).split())
        except Exception as exc:
            last = str(exc)
        if "could not start" in last.lower():
            raise AssertionError("the game did not start: " + last[:500])
        time.sleep(0.25)
    raise AssertionError("seat links never appeared: " + last[:500])


def _tail(path: Path, n: int = 40) -> str:
    if not path.is_file():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-n:])


def _latest_gid(lobby) -> str | None:
    try:
        games = lobby.store.games()
    except Exception:
        return None
    if not games:
        return None
    return str(games[-1].get("id") or "") or None


def _seat_logs(lobby, gid: str | None) -> str:
    if not gid:
        return "no game id"
    root = lobby.workers.game_dir(gid) / "ai-cockpit"
    if not root.is_dir():
        return "no ai-cockpit directory"
    paths = sorted(root.glob("player.log")) + sorted(root.glob("*/player.log"))
    paths += sorted(root.glob("player.err")) + sorted(root.glob("*/player.err"))
    if not paths:
        return "no player.log or player.err"
    chunks = []
    for path in paths:
        body = _tail(path) or "(empty)"
        chunks.append(f"--- {path.relative_to(root)} ---\n{body}")
    return "\n".join(chunks)


def _scheduler_state(lobby, gid: str | None) -> str:
    if not gid:
        return "no game id"
    procs = []
    try:
        rows = lobby._cockpit_entries(gid)
    except Exception:
        rows = []
    for row in rows:
        proc = row.get("proc")
        exit_code = None if proc is None else proc.poll()
        procs.append(f"{row.get('seat')} pid={getattr(proc, 'pid', None)} exit={exit_code}")
    cockpit = "cockpit=[" + "; ".join(procs) + "]"
    worker = lobby.workers.workers.get(gid)
    if worker is None:
        return cockpit + " worker=missing"
    import httpx

    try:
        data = httpx.get(
            f"http://127.0.0.1:{worker.port}/state",
            headers=admin_headers(lobby.secrets.lobby_secret(gid), lobby.secrets.spectator_token(gid)),
            timeout=5,
        ).json()
    except Exception as exc:
        return f"{cockpit} state unread ({exc.__class__.__name__}: {exc})"
    seats = []
    for row in data.get("players") or []:
        seats.append(
            f"{row.get('id')}:{row.get('kind')} alive={row.get('alive')} "
            f"sector={row.get('sector_id')} turns={row.get('turns_today')}/{row.get('turns_per_day')}"
        )
    return (
        f"status={data.get('status')} day={data.get('day')} finished={data.get('finished')} "
        f"turn_wait={json.dumps(data.get('turn_wait'), default=str)} "
        f"seats=[{'; '.join(seats)}] {cockpit}"
    )


def _worker_log(lobby, gid: str | None) -> str:
    logs = lobby.cfg.logs_dir
    if gid:
        path = logs / f"game-{gid}.log"
        if path.is_file():
            return f"--- game-{gid}.log ---\n{_tail(path)}"
    found = sorted(logs.glob("game-*.log")) if logs.is_dir() else []
    if not found:
        return "no worker log"
    path = found[-1]
    return f"--- {path.name} ---\n{_tail(path)}"


def _failure_report(lobby, gid: str | None, exc: BaseException, notes: dict | None = None) -> str:
    """What the merge runner dropped: seat logs, player.err, scheduler state."""
    parts = [
        "PLAYTEST FAILURE",
        f"{type(exc).__name__}: {exc}",
        "scheduler: " + _scheduler_state(lobby, gid),
        "seat logs:",
        _seat_logs(lobby, gid),
        "worker:",
        _worker_log(lobby, gid),
    ]
    progress = _tail(SHOTS / "progress.txt", 20)
    if progress:
        parts.append("progress:\n" + progress)
    if notes:
        shown = {key: value for key, value in notes.items() if key != "links"}
        if shown:
            parts.append("notes: " + json.dumps(shown, default=str)[:1500])
    return "\n".join(parts)


def test_two_humans_play_two_days_through_the_proxy(monkeypatch, tmp_path) -> None:
    """Creator, two token links, two days, then the creator ends the game."""
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    import uvicorn

    from tw2k.public.config import LobbyConfig
    from tw2k.public.lobby import create_lobby_app

    monkeypatch.setenv("LOBBY_AI_SEAT_MODE", "on")
    monkeypatch.setenv("PLAYTEST_CLOCK_NUDGE_MODE", "on")
    monkeypatch.setattr(K, "LOBBY_AI_SEAT_MODE", "on")
    monkeypatch.setattr(K, "AI_COCKPIT_SEAT_MODE", "tw2002")
    monkeypatch.setattr(K, "FULL_LENGTH_TURN_LIMITS_MODE", "v311")

    base = cu.free_port(cu.LOBBY_FREE_START, count=4)
    lobby_port, proxy_port = base, base + 1
    game_ports = range(base + 2, base + 4)
    for port in (lobby_port, proxy_port, *game_ports):
        assert port != 8099
        assert cu.allowed_test_port(port)
    assert lobby_port not in game_ports

    cfg = LobbyConfig(
        port=lobby_port,
        game_ports=game_ports,
        root=tmp_path / "lobby",
        idle_s=3600,
        tick_s=30,
        # An idle VM boots in a few seconds. The loaded Windows merge box
        # spent the old 90s cap inside the create POST, and the click gave up.
        boot_timeout_s=240,
        max_games=1,
    )
    app = create_lobby_app(cfg, port_probe=lambda _p: True)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=lobby_port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    proxy: ThreadingHTTPServer | None = None
    notes: dict[str, str] = {}
    try:
        _wait_http(f"http://127.0.0.1:{lobby_port}/healthz")
        cert, key = _cert(tmp_path)
        _Proxy.lobby_port = lobby_port
        _Proxy.public_host = f"127.0.0.1:{proxy_port}"
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert, key)
        proxy = _TLSProxyServer(("127.0.0.1", proxy_port), _Proxy, ctx)
        threading.Thread(target=proxy.serve_forever, daemon=True).start()
        origin = f"https://127.0.0.1:{proxy_port}"
        _wait_http(origin + "/healthz")
        SHOTS.mkdir(parents=True, exist_ok=True)
        played: dict[str, str | None] = {"gid": None}
        try:
            _drive(sync, origin, app.state.lobby, notes, played)
        except Exception as exc:
            try:
                gid = played.get("gid") or _latest_gid(app.state.lobby)
                report = _failure_report(app.state.lobby, gid, exc, notes)
            except Exception as report_exc:
                report = (
                    f"PLAYTEST FAILURE\n{type(exc).__name__}: {exc}\n"
                    f"report failed: {type(report_exc).__name__}: {report_exc}"
                )
            print(report, file=sys.stderr, flush=True)
            raise AssertionError(report) from exc
    finally:
        if proxy is not None:
            proxy.shutdown()
        server.should_exit = True
        thread.join(timeout=20)
        from tests._port_lock import release_ports

        release_ports(lobby_port, proxy_port, *game_ports)
    (SHOTS / "notes.txt").write_text("\n".join(f"{k}: {v}" for k, v in notes.items()) + "\n", encoding="utf-8")


def _drive(sync, origin: str, lobby, notes: dict[str, str], played: dict[str, str | None]) -> None:
    with sync() as pw:
        browser = pw.chromium.launch()
        try:
            creator = browser.new_context(
                ignore_https_errors=True, viewport={"width": 1280, "height": 720},
                color_scheme="dark", forced_colors="none",
            )
            guest = browser.new_context(
                ignore_https_errors=True, viewport={"width": 1280, "height": 720},
                color_scheme="dark", forced_colors="none",
            )
            home = creator.new_page()
            home.goto(origin + "/", wait_until="domcontentloaded")
            home.screenshot(path=str(SHOTS / "01-disclaimer.png"))
            home.get_by_role("button", name="I understand").click()
            home.wait_for_url(origin + "/")
            home.get_by_role("link", name="New game").click()
            home.wait_for_selector("#game_length")
            home.fill("#name", "Playtest 3")
            home.select_option("#universe_size", "200")
            home.fill("#max_days", "2")
            home.select_option("#starting_credits", "100000")
            home.select_option("#humans", "2")
            home.select_option("#bots", "1")
            home.select_option("#ai_opponents", "1")
            home.select_option("#ai_brain", "heuristic")
            home.check("#ai_cockpit")
            home.select_option("#ai_cockpit_provider", "scripted")
            home.select_option("#game_length", "full")
            home.screenshot(path=str(SHOTS / "02-new-game.png"))
            # The form POST does not return until the worker is healthy.
            # Playwright's 30s click cap fired while that boot was still going.
            home.get_by_role("button", name="Create game").click(timeout=300_000)
            _wait_seat_links(home)
            home.screenshot(path=str(SHOTS / "03-created-links.png"))
            links = {
                row.get_attribute("data-seat"): row.inner_text().strip()
                for row in home.locator("[data-testid=seat-link]").all()
            }
            assert set(links) == {"P1", "P2"}
            for seat, url in links.items():
                assert url.startswith(origin + "/g/")
                assert f"seat={seat}" in url and "token=" in url and "layout=redesign" in url
                assert "127.0.0.1:" + str(origin.rsplit(":", 1)[-1]) in url
            notes["links"] = "two https cockpit links with token and layout=redesign"
            created = home.locator("body").inner_text()
            assert "Full-length" in created
            assert "AI cockpit" in created
            gid = links["P1"].split("/g/")[1].split("/")[0]
            played["gid"] = gid

            p1 = creator.new_page()
            p2 = guest.new_page()
            for tag, page in (("P1", p1), ("P2", p2)):
                _watch_net(page, tag)
            p1.goto(links["P1"], wait_until="domcontentloaded")
            p2.goto(links["P2"], wait_until="domcontentloaded")
            _accept_if_asked(p2)
            _wait_cockpit(p1)
            _wait_cockpit(p2)
            for seat, page in (("P1", p1), ("P2", p2)):
                page.bring_to_front()
                page.screenshot(path=str(SHOTS / f"0{4 if seat == 'P1' else 5}-cockpit-{seat.lower()}.png"))
            for page in (p1, p2):
                assert "Turns left today" in page.locator("[data-testid=turns-left-today]").inner_text()
                turns = page.locator("[data-testid=turns-left-today]")
                box = turns.bounding_box()
                assert box and box["width"] > 80, box

            goals = {"P1": _fresh(), "P2": _fresh()}
            pages = {"P1": p1, "P2": p2}
            (SHOTS / "progress.txt").write_text("", encoding="utf-8")
            _wait_ai(lobby, gid)
            # A healthy run on this VM finishes the whole test in about two
            # minutes. The old 540s cap was the loaded Windows run that never
            # left day 1, because the seat-open check had matched the failure
            # line and the scheduler was still on that seat.
            deadline = time.time() + 720
            last_ai = 0.0
            while time.time() < deadline and not all(_day_done(row) for row in goals.values()):
                moved = False
                for seat, page in pages.items():
                    if _chip(page) != "YOUR MOVE":
                        continue
                    page.bring_to_front()
                    if _day_done(goals[seat]):
                        before = _result(page)
                        _pass(page)
                        _settle(page, before, 8)
                    else:
                        _step(page, seat, goals[seat], lobby, gid, notes)
                    moved = True
                    break
                if time.time() - last_ai > 15:
                    _progress(f"goals={goals} ai={_ai_tail(lobby, gid)}")
                    last_ai = time.time()
                if not moved:
                    page = pages["P1" if int(time.time()) % 2 == 0 else "P2"]
                    page.bring_to_front()
                    time.sleep(0.25)
            else:
                if not all(_day_done(row) for row in goals.values()):
                    _progress(f"STOP goals={goals} ai={_ai_tail(lobby, gid)}")
                    tail = (SHOTS / "progress.txt").read_text(encoding="utf-8")[-1500:]
                    raise AssertionError(f"day 1 did not finish: {goals}\n{tail}")

            _manual(p1)
            _layout(p1)
            _layout(p2, prefix="p2-")
            _rewind(lobby, gid)
            _wait_day(p1, "2")
            _wait_day(p2, "2")
            p1.screenshot(path=str(SHOTS / "13-day-2.png"))
            notes["day"] = "day 2 after the playtest clock moved one day length"
            _day2_move(pages, notes)

            p1.bring_to_front()
            p1.keyboard.press("Escape")
            opened = False
            deadline = time.time() + 45
            while time.time() < deadline:
                if p1.locator("#dangerOk").count() and p1.locator("#dangerOk").is_visible():
                    opened = True
                    break
                if p1.locator("[data-testid=end-for-everyone]").count() == 0:
                    p1.keyboard.press("?")
                else:
                    _js_click(p1, "[data-testid=end-for-everyone]")
                time.sleep(0.25)
            assert opened, "end confirm never opened"
            _js_click(p1, "#dangerOk")
            p1.wait_for_selector("[data-game-over=panel]", timeout=20_000)
            over = p1.locator("[data-game-over=panel]").inner_text()
            assert "Ended by the game's creator" in over
            p2.wait_for_selector("[data-game-over=panel]", timeout=20_000)
            assert "Ended by the game's creator" in p2.locator("[data-game-over=panel]").inner_text()
            p1.screenshot(path=str(SHOTS / "14-game-over.png"))
            notes["end"] = over
        except Exception:
            try:
                notes["page"] = " ".join(home.locator("body").inner_text(timeout=2_000).split())[:800]
            except Exception:
                pass
            _dump_pages({"creator": creator, "guest": guest}, notes)
            raise
        finally:
            browser.close()


_PENDING: dict[str, dict[int, tuple[str, str, str]]] = {}


def _watch_net(page, tag: str) -> None:
    """Every failed or non-OK request a cockpit tab makes, to net.txt."""
    def log(line: str) -> None:
        with open(SHOTS / "net.txt", "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%H:%M:%S')} {tag} {line}\n")

    pending = _PENDING.setdefault(tag, {})
    page.on("request", lambda r: pending.__setitem__(id(r), (time.strftime("%H:%M:%S"), r.method, r.url)))
    page.on("requestfinished", lambda r: pending.pop(id(r), None))
    page.on("requestfailed", lambda r: pending.pop(id(r), None))
    page.on("requestfailed", lambda r: log(f"FAILED {r.method} {r.url} {r.failure}"))
    page.on("response", lambda r: r.status >= 400 and log(f"{r.status} {r.request.method} {r.url}"))
    page.on("console", lambda m: m.type in ("error", "warning") and log(f"console.{m.type} {m.text[:300]}"))
    page.on("pageerror", lambda e: log(f"pageerror {str(e)[:300]}"))


def _dump_pages(contexts: dict, notes: dict[str, str]) -> None:
    """On a failure, every open tab: a screenshot, its URL, and its visible text."""
    for tag, pending in _PENDING.items():
        notes[f"pending-{tag}"] = " | ".join(f"{t} {m} {u}" for t, m, u in list(pending.values())[:20])
    for name, ctx in contexts.items():
        for i, page in enumerate(list(ctx.pages)):
            tag = f"fail-{name}-{i}"
            try:
                page.screenshot(path=str(SHOTS / f"{tag}.png"))
            except Exception as exc:
                notes[f"{tag}-shot"] = type(exc).__name__
            try:
                text = " ".join(page.locator("body").inner_text(timeout=2_000).split())[:600]
            except Exception as exc:
                text = f"<{type(exc).__name__}>"
            notes[tag] = f"{page.url} :: {text}"


def _fresh() -> dict[str, bool]:
    return {"trade": False, "warp": False, "dock": False, "gear": False, "fight": False}


def _day_done(row: dict[str, bool]) -> bool:
    return row["trade"] and row["warp"] and row["dock"] and row["gear"] and row["fight"]


def _has_text(page, selector: str, text: str) -> bool:
    return bool(page.evaluate(
        """([sel, text]) => [...document.querySelectorAll(sel)].some((node) => (node.textContent || '').includes(text))""",
        [selector, text],
    ))


def _js_click_text(page, selector: str, text: str) -> bool:
    return bool(page.evaluate(
        """([sel, text]) => {
          const el = [...document.querySelectorAll(sel)].find((node) => (node.textContent || '').includes(text));
          if (!el) return false;
          el.click();
          return true;
        }""",
        [selector, text],
    ))


def _js_click(page, selector: str) -> bool:
    return bool(page.evaluate(
        """(sel) => {
          const el = document.querySelector(sel);
          if (!el) return false;
          el.click();
          return true;
        }""",
        selector,
    ))


def _progress(line: str) -> None:
    path = SHOTS / "progress.txt"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{time.strftime('%H:%M:%S')} {line}\n")


def _ai_logs(lobby, gid: str) -> list[Path]:
    """Seat logs live in ai-cockpit/<seat>/, not in ai-cockpit/player.log."""
    root = lobby.workers.game_dir(gid) / "ai-cockpit"
    if not root.is_dir():
        return []
    found: list[Path] = []
    direct = root / "player.log"
    if direct.is_file():
        found.append(direct)
    found.extend(sorted(root.glob("*/player.log")))
    found.extend(sorted(root.glob("*/player.err")))
    return found


def _ai_text(lobby, gid: str) -> str:
    try:
        paths = _ai_logs(lobby, gid)
        if not paths:
            return "no ai log"
        chunks = []
        for path in paths:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            where = path.parent.name if path.parent.name != "ai-cockpit" else "ai-cockpit"
            chunks.append(f"{where}/{path.name}: " + " || ".join(lines[-6:]))
        return " // ".join(chunks)
    except Exception as exc:
        return str(exc)


def _ai_tail(lobby, gid: str) -> str:
    return _ai_text(lobby, gid)


def _seat_page_is_open(text: str) -> bool:
    """The success line is 'seat page is open'.

    'the seat page did not open' contains the older phrase 'seat page open'.
    Matching that phrase marked a dead seat ready, and day 1 then ran until
    the cap while the scheduler stayed on it.
    """
    return any(line.strip().startswith("seat page is open") for line in text.splitlines())


def test_a_failed_open_is_not_a_ready_seat(tmp_path) -> None:
    """The failure sentence must not count, and a failure still prints the logs."""
    assert not _seat_page_is_open("the seat page did not open: TimeoutError")
    assert not _seat_page_is_open("P3/player.log: the seat page did not open: TimeoutError")
    assert _seat_page_is_open("seat page is open http://127.0.0.1/bot?seat=P3")
    assert _seat_page_is_open(
        "the seat page did not open: Error\nseat page is open http://127.0.0.1/bot\n"
    )
    root = tmp_path / "games" / "ab" / "ai-cockpit" / "P3"
    root.mkdir(parents=True)
    (root / "player.log").write_text("the seat page did not open: TimeoutError\n", encoding="utf-8")
    (root / "player.err").write_text("browser closed\n", encoding="utf-8")
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "game-ab.log").write_text("worker boot\n", encoding="utf-8")

    class Proc:
        pid = 9

        def poll(self):
            return 1

    class Workers:
        workers: dict = {}

        def game_dir(self, gid):
            return tmp_path / "games" / gid

    class Lobby:
        workers = Workers()
        cfg = type("C", (), {"logs_dir": logs})()

        def _cockpit_entries(self, gid):
            return [{"seat": "P3", "proc": Proc()}]

    report = _failure_report(Lobby(), "ab", AssertionError("day 1 did not finish"))
    assert "PLAYTEST FAILURE" in report
    assert "player.err" in report
    assert "browser closed" in report
    assert "the seat page did not open" in report
    assert "exit=1" in report
    assert "worker boot" in report
    assert "turn_wait" not in report
    assert "worker=missing" in report


def _seat_log_text(lobby, gid: str) -> str:
    root = lobby.workers.game_dir(gid) / "ai-cockpit"
    if not root.is_dir():
        return ""
    parts: list[str] = []
    direct = root / "player.log"
    paths = ([direct] if direct.is_file() else []) + sorted(root.glob("*/player.log"))
    for path in paths:
        parts.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def _wait_ai(lobby, gid: str, timeout_s: float = 360) -> None:
    """Block until the cockpit seat has the page open.

    Day 1 used to start while this process was still launching. The scheduler
    holds that seat until the first client connects, so P2 never finished.
    The open budget is one slow Chromium launch on the loaded Windows box,
    not the few seconds this VM needs.
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        text = _seat_log_text(lobby, gid)
        if _seat_page_is_open(text):
            _progress(f"ai ready {text[-400:]}")
            return
        time.sleep(0.5)
    raise AssertionError(f"ai cockpit did not open: {_ai_text(lobby, gid)}")


def _result(page) -> str:
    try:
        return page.locator("#lastResult").inner_text(timeout=1000)
    except Exception:
        return ""


def _settle(page, before: str, timeout_s: float = 25) -> str:
    """Wait until the last line changes or the turn is no longer ours."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        now = _result(page)
        if now != before or _chip(page) != "YOUR MOVE":
            return now
        time.sleep(0.2)
    return _result(page)


def _chip(page) -> str:
    try:
        return page.locator("#waitchip").inner_text(timeout=1000).strip()
    except Exception:
        return ""


def _accept_if_asked(page) -> None:
    """The guest gets the server-rendered disclaimer first; accept it and wait for the cockpit URL."""
    button = page.get_by_role("button", name="I understand")
    page.wait_for_selector("form[action$='/accept'] button, #credits", timeout=30_000)
    if button.count():
        with page.expect_navigation(wait_until="domcontentloaded", timeout=30_000):
            button.click()


def _wait_cockpit(page) -> None:
    page.wait_for_function(
        """() => {
          const credits = document.querySelector('#credits');
          const turns = document.querySelector('[data-testid=turns-left-today]');
          // 'complete' means every stylesheet and script finished: a tab whose
          // assets stalled showed credits from the first paint but never polled.
          return document.readyState === 'complete' && credits && credits.textContent
            && credits.textContent !== '-' && turns && turns.textContent;
        }""",
        timeout=90_000,
    )
    info = page.evaluate(
        """() => {
          const deck = document.querySelector('#deck');
          const box = deck ? deck.getBoundingClientRect() : null;
          return {
            forced: matchMedia('(forced-colors: active)').matches,
            bg: getComputedStyle(document.body).backgroundColor,
            deck: box ? {w: box.width, h: box.height, y: box.top} : null,
            here: (document.querySelector('#here') || {}).textContent || '',
            warps: (document.querySelector('#warps') || {}).textContent || '',
            err: (document.querySelector('#err') || {}).textContent || '',
          };
        }"""
    )
    (SHOTS / "cockpit-debug.txt").write_text(str(info) + "\n", encoding="utf-8")


def _sector(page) -> str:
    return page.locator("#pSector").inner_text().strip()


def _here(page) -> str:
    return page.locator("#here").inner_text()


def _step(page, seat: str, row: dict[str, bool], lobby, gid: str, notes: dict[str, str]) -> None:
    page.keyboard.press("Escape")
    before = _result(page)
    if _js_click_text(page, "#here button", "Lift off"):
        outcome = _settle(page, before)
        _progress(f"{seat} liftoff chip={_chip(page)!r} result={outcome[:160]!r} sector={_sector(page)}")
        if "lift" in outcome.lower() or not _has_text(page, "#here button", "Lift off"):
            notes.setdefault(f"{seat}-liftoff", outcome[:180] or "left the home planet")
        return
    if not row["fight"] and _attack_bot(page):
        row["fight"] = True
        notes[f"{seat}-fight"] = _result(page)[:180]
        _progress(f"{seat} fight {notes[f'{seat}-fight']!r}")
        page.screenshot(path=str(SHOTS / f"09-combat-{seat}.png"))
        return
    before = _result(page)
    if not row["trade"] and page.locator("#here button.tbtn").count():
        selector = "#here button.tbtn.buy" if page.locator("#here button.tbtn.buy").count() else "#here button.tbtn.sell"
        _js_click(page, selector)
        outcome = _settle(page, before)
        _progress(f"{seat} trade result={outcome[:160]!r}")
        if outcome.lower().startswith("ok"):
            row["trade"] = True
            notes[f"{seat}-trade"] = outcome[:180]
            page.screenshot(path=str(SHOTS / f"06-trade-{seat}.png"))
        return
    if not row["warp"]:
        before_plays = int(page.locator("#warpClip").get_attribute("data-plays") or "0")
        if before_plays > 0:
            clip = page.locator("#warpClip").get_attribute("data-clip") or ""
            row["warp"] = True
            notes[f"{seat}-warp"] = clip
            page.screenshot(path=str(SHOTS / f"07-warp-{seat}.png"))
            _progress(f"{seat} warp already playing {clip!r}")
        elif page.locator("#warps button").count() and not _has_text(page, "#here button", "Lift off"):
            _js_click(page, "#warps button")
            try:
                page.wait_for_function(
                    f"""() => Number(document.querySelector('#warpClip').getAttribute('data-plays') || 0) > {before_plays}""",
                    timeout=20_000,
                )
            except Exception:
                page.wait_for_timeout(1200)
            clip = page.locator("#warpClip").get_attribute("data-clip") or ""
            plays = int(page.locator("#warpClip").get_attribute("data-plays") or "0")
            _progress(f"{seat} warp plays={plays} clip={clip!r} sector={_sector(page)}")
            if plays > before_plays:
                row["warp"] = True
                notes[f"{seat}-warp"] = clip
                page.screenshot(path=str(SHOTS / f"07-warp-{seat}.png"))
            else:
                detail = page.evaluate(
                    """() => ({
                      sector: (document.querySelector('#pSector') || {}).textContent,
                      result: (document.querySelector('#lastResult') || {}).textContent,
                      plays: (document.querySelector('#warpClip') || {}).getAttribute('data-plays'),
                      clip: (document.querySelector('#warpClip') || {}).getAttribute('data-clip'),
                    })"""
                )
                (SHOTS / "warp-debug.txt").write_text(str(detail) + "\n", encoding="utf-8")
                _progress(f"{seat} warp failed {detail}")
            return
        if row["warp"]:
            return
    if not row["dock"]:
        if _at_dock(page):
            row["dock"] = True
            notes[f"{seat}-dock"] = _here(page)[:180]
            page.screenshot(path=str(SHOTS / f"08-stardock-{seat}.png"))
            return
        _engage(page, 1)
        return
    if row["dock"] and not row["gear"]:
        if _has_text(page, "#here button", "StarDock: buy gear"):
            if _buy_fighters(page):
                row["gear"] = True
                notes[f"{seat}-gear"] = _result(page)[:180]
            return
        if not _at_dock(page):
            _engage(page, 1)
        return
    if not row["trade"]:
        here = _sector(page)
        seen = {bit for bit in notes.get(f"{seat}-seen", "").split(",") if bit}
        _progress(f"{seat} still looking for a port in {here}")
        moved = page.evaluate(
            """(seen) => {
              const buttons = [...document.querySelectorAll('#warps button')];
              const dest = (btn) => ((btn.textContent || '').match(/:([0-9]+)/) || [])[1] || '';
              const fresh = buttons.find((btn) => dest(btn) && !seen.includes(dest(btn)));
              const pick = fresh || buttons[0];
              if (!pick) return false;
              pick.click();
              return dest(pick) || true;
            }""",
            list(seen),
        )
        if moved:
            seen.add(here)
            if isinstance(moved, str):
                seen.add(moved)
            notes[f"{seat}-seen"] = ",".join(sorted(seen))
            _settle(page, before, 8)
        return
    if not row["fight"]:
        if _attack_bot(page):
            row["fight"] = True
            notes[f"{seat}-fight"] = _result(page)[:180]
            _progress(f"{seat} fight {notes[f'{seat}-fight']!r}")
            page.screenshot(path=str(SHOTS / f"09-combat-{seat}.png"))
            return
        target = _bot_sector(lobby, gid, seat)
        if target is None:
            raise AssertionError("no code bot on the board")
        if _sector(page) == str(target):
            raise AssertionError(f"{seat} is in {target} but cannot attack the code bot: {_here(page)[:240]}")
        _engage(page, target)
        return
    page.keyboard.press(".")


def _at_dock(page) -> bool:
    text = _here(page)
    return "StarDock" in text or _sector(page) == "1"


def _engage(page, sector: int) -> bool:
    if _sector(page) == str(sector):
        return True
    before = _result(page)
    if page.locator("[data-testid=engage]").count():
        _js_click(page, "[data-testid=engage]")
        outcome = _settle(page, before, 40)
        _progress(f"engage {sector} -> sector={_sector(page)} result={outcome[:140]!r}")
        return "refused" not in outcome.lower()
    page.keyboard.press("c")
    page.keyboard.press("f")
    try:
        page.locator("#sectorAsk").wait_for(timeout=4_000)
    except Exception:
        page.keyboard.press("Escape")
        _progress(f"engage {sector} no prompt chip={_chip(page)!r} result={_result(page)[:120]!r}")
        return False
    page.locator("#sectorAsk").fill(str(sector))
    _js_click(page, "#sectorGo")
    try:
        page.locator("[data-testid=engage]").wait_for(timeout=8_000)
    except Exception:
        page.keyboard.press("Escape")
        _progress(f"engage {sector} no button result={_result(page)[:140]!r}")
        return False
    _js_click(page, "[data-testid=engage]")
    outcome = _settle(page, before, 40)
    _progress(f"engage {sector} -> sector={_sector(page)} result={outcome[:140]!r}")
    return "refused" not in outcome.lower()


def _buy_fighters(page) -> bool:
    before = _result(page)
    _js_click_text(page, "#here button", "StarDock: buy gear")
    select = page.locator("#formSlot select[data-n=item]")
    try:
        select.wait_for(timeout=6_000)
    except Exception:
        _progress("gear form did not open: " + _result(page)[:160])
        return False
    chosen = page.evaluate(
        """() => {
          const sel = document.querySelector('#formSlot select[data-n=item]');
          if (!sel) return '';
          const opts = [...sel.options].filter((opt) => !opt.disabled);
          const fighter = opts.find((opt) => /fighter/i.test(opt.value) || /fighter/i.test(opt.textContent || ''));
          return (fighter || opts[0] || {}).value || '';
        }"""
    )
    if not chosen:
        _progress("gear list was empty")
        return False
    select.select_option(value=chosen)
    qty = page.locator("#formSlot input[data-n=qty]")
    if qty.count():
        qty.fill("5")
    _js_click_text(page, "#formSlot button", "CONFIRM")
    outcome = _settle(page, before)
    _progress(f"gear {chosen!r} result={outcome[:160]!r}")
    return bool(outcome) and "refused" not in outcome.lower() and "not accepted" not in outcome.lower()


def _attack_bot(page) -> bool:
    if "(code bot)" not in _here(page) and page.locator("#here button", has_text="Attack").count() == 0:
        return False
    page.keyboard.press("a")
    form = page.locator("#formSlot")
    try:
        form.wait_for(timeout=4_000)
    except Exception:
        return False
    select = form.locator("select[data-n=target]")
    if select.count() == 0:
        return False
    labels = select.locator("option").all_inner_texts()
    chosen = next((label for label in labels if "code bot" in label.lower()), "")
    if not chosen:
        page.keyboard.press("Escape")
        return False
    select.select_option(label=chosen)
    qty = form.locator("input[data-n=qty]")
    if qty.count() and not qty.input_value():
        qty.fill("1")
    form.locator("button", has_text="CONFIRM").evaluate("el => el.click()")
    page.wait_for_timeout(800)
    result = page.locator("#lastResult").inner_text()
    if "not accepted" in result.lower() or "refused" in result.lower():
        return False
    return True


def _bot_sector(lobby, gid: str, seat: str) -> int | None:
    import httpx

    worker = lobby.workers.workers.get(gid)
    if worker is None:
        return None
    headers = admin_headers(lobby.secrets.lobby_secret(gid), lobby.secrets.spectator_token(gid))
    data = httpx.get(f"http://127.0.0.1:{worker.port}/state", headers=headers, timeout=10).json()
    me = next((row for row in data.get("players") or [] if row.get("id") == seat), None)
    bots = [row for row in data.get("players") or [] if row.get("kind") == "heuristic" and row.get("alive", True)]
    if not bots:
        return None
    if me is None:
        return int(bots[0]["sector_id"])
    here = int(me["sector_id"])
    bots.sort(key=lambda row: abs(int(row["sector_id"]) - here))
    return int(bots[0]["sector_id"])


def _manual(page) -> None:
    page.bring_to_front()
    with page.context.expect_page() as popped:
        page.evaluate("() => document.querySelector('#manualLink').click()")
    manual = popped.value
    manual.wait_for_load_state("domcontentloaded")
    body = manual.locator("body").inner_text()
    manual.screenshot(path=str(SHOTS / "10-manual.png"), full_page=False)
    assert "Full-length games use" in body
    assert "not available in this game" not in body.lower()
    manual.close()


def _menu_click(page, selector: str) -> None:
    """Click a layout control that the live deck keeps moving under the pointer.

    The cockpit animations never settle, so a pointer click waits out its
    budget. The button's own click listener is what saves the deck, and the
    caller still checks the deck attribute and localStorage afterwards.
    """
    hit = page.evaluate(
        """(sel) => {
          const el = document.querySelector(sel);
          if (!el) return false;
          el.scrollIntoView({block: 'center', inline: 'nearest'});
          el.click();
          return true;
        }""",
        selector,
    )
    assert hit, selector


def _layout(page, prefix: str = "") -> None:
    page.bring_to_front()
    _menu_click(page, "[data-testid=layout-open]")
    page.locator("[data-testid=layout-menu]").wait_for()
    before_font = page.locator("[data-testid=font-readout]").inner_text()
    _menu_click(page, "[data-testid=font-inc]")
    page.wait_for_function("() => document.body.getAttribute('data-deck') === 'custom'")
    assert page.locator("[data-testid=font-readout]").inner_text() != before_font
    stored = page.evaluate("() => Object.keys(localStorage).some((k) => k.indexOf('tw2k-deck-v1:') === 0)")
    assert stored
    page.screenshot(path=str(SHOTS / f"11-layout-{prefix}saved.png"))
    _menu_click(page, "[data-testid=layout-reset]")
    page.wait_for_function("() => document.body.getAttribute('data-deck') === 'default'")
    cleared = page.evaluate("() => Object.keys(localStorage).every((k) => k.indexOf('tw2k-deck-v1:') !== 0)")
    assert cleared
    page.screenshot(path=str(SHOTS / f"12-layout-{prefix}reset.png"))
    _menu_click(page, "[data-testid=layout-close]")


def _rewind(lobby, gid: str) -> None:
    import httpx

    worker = lobby.workers.workers[gid]
    headers = admin_headers(lobby.secrets.lobby_secret(gid), lobby.secrets.spectator_token(gid))
    response = httpx.post(
        f"http://127.0.0.1:{worker.port}/control/rewind-day",
        headers=headers,
        json={},
        timeout=10,
    )
    assert response.status_code == 200, response.text
    deadline = time.time() + 25
    day = None
    while time.time() < deadline:
        day = httpx.get(f"http://127.0.0.1:{worker.port}/state", headers=headers, timeout=10).json().get("day")
        if day == 2:
            _progress(f"server day {day}")
            return
        time.sleep(0.4)
    raise AssertionError(f"server day stayed {day} after rewind")


def _wait_day(page, day: str) -> None:
    try:
        page.evaluate("() => window.__tw2kTest && window.__tw2kTest.refreshNow()")
    except Exception:
        pass
    try:
        page.wait_for_function(
            """(day) => {
              const el = document.querySelector('#sbDay');
              return !!el && (el.textContent || '').trim() === day;
            }""",
            arg=day,
            timeout=90_000,
        )
    except Exception:
        got = ""
        try:
            got = page.evaluate("() => (document.querySelector('#sbDay') || {}).textContent || ''")
        except Exception:
            got = ""
        raise AssertionError(f"cockpit day is {got!r}, wanted {day}") from None


def _pass(page) -> None:
    """Spend this turn without ending the seat's day.

    Since 1dd63a6 a fourth Wait in a row opens "One more Wait ends your day"
    and waits for CONFIRM. A bare "." left that dialog open: the seat held the
    turn until the server's idle timeout, and a confirmed Wait would end the
    day. When the dialog shows, close it and take a warp instead.
    """
    page.keyboard.press(".")
    try:
        page.wait_for_function(
            """() => {
              const m = document.querySelector('#menu');
              return !!(m && !m.hidden && m.dataset.screen === 'Wait' && document.querySelector('#dangerOk'));
            }""",
            timeout=1_500,
        )
    except Exception:
        return
    page.keyboard.press("Escape")
    page.wait_for_function("() => { const m = document.querySelector('#menu'); return !m || m.hidden; }", timeout=5_000)
    if not _js_click(page, "#warps button"):
        # No lane to take: end the day after all rather than hold the turn.
        page.keyboard.press(".")
        page.locator("#dangerOk").click(timeout=5_000)


def _turns_left(page) -> int | None:
    """The first number on the turns-left line, or None when it cannot be read."""
    try:
        text = page.locator("[data-testid=turns-left-today]").inner_text(timeout=1000)
    except Exception:
        return None
    digits = ""
    for ch in text:
        if ch.isdigit():
            digits += ch
        elif digits:
            break
    return int(digits) if digits else None


def _spent(page, start: int | None) -> bool:
    now = _turns_left(page)
    return start is not None and now is not None and now < start


def _day2_move(pages: dict, notes: dict[str, str]) -> None:
    """One real day-2 action from each human, in whichever order the turn arrives.

    Waiting on P1 first left P2 holding the scheduler, so P1's chip stayed
    WAITING until the 60s budget ran out. A seat that has already moved passes
    at once, and a seat that has not moves on the turn it is offered.
    """
    pending = set(pages)
    # A move that lands can leave #lastResult reading the same text as the
    # last one (two equal trades), and the chip can flip to WAITING before
    # _settle looks. The server-side turn counter is the proof: a seat whose
    # turns-left number dropped since day 2 began has moved.
    start = {seat: _turns_left(page) for seat, page in pages.items()}
    deadline = time.time() + 300
    while pending and time.time() < deadline:
        acted = False
        for seat, page in pages.items():
            page.bring_to_front()
            if _chip(page) != "YOUR MOVE":
                continue
            before = _result(page)
            if seat not in pending:
                _pass(page)
            elif page.locator("#here button.tbtn").count():
                _js_click(page, "#here button.tbtn")
                if page.locator("#formSlot button", has_text="CONFIRM").count():
                    _js_click(page, "#formSlot button")
            elif page.locator("#warps button").count():
                _js_click(page, "#warps button")
            else:
                _pass(page)
            outcome = _settle(page, before, 30)
            landed = outcome != before or _chip(page) != "YOUR MOVE" or _spent(page, start.get(seat))
            if seat in pending and landed:
                pending.discard(seat)
                notes[f"{seat}-day2"] = (outcome or "acted on day 2")[:180]
                _progress(f"{seat} day 2 {notes[f'{seat}-day2']!r}")
            acted = True
            break
        for seat in list(pending):
            if _spent(pages[seat], start.get(seat)):
                pending.discard(seat)
                notes[f"{seat}-day2"] = "acted on day 2 (turns left dropped)"
                _progress(f"{seat} day 2 turns left dropped")
        if not acted:
            time.sleep(0.2)
    if pending:
        who = ", ".join(sorted(pending))
        raise AssertionError(f"{who} never moved on day 2")
