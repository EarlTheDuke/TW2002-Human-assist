"""Track H: lobby and seat links through a Cloudflare quick tunnel.

No tunnel is opened. ``_FakeQuickTunnel`` stands in for cloudflared: it ends
TLS for ``https://blue-pond.trycloudflare.com`` and forwards plain http to
the lobby on 127.0.0.1 with the headers cloudflared sends (the public Host,
X-Forwarded-Proto, Cf-Visitor, Cf-Connecting-Ip, Cf-Ray) and no
X-Forwarded-Host. Websocket upgrades are piped through as raw bytes.
Chromium resolves the public name to the fake edge, so the address bar,
every link, and every request stay on the tunnel name with no port.
"""

from __future__ import annotations

import datetime
import ipaddress
import json
import select
import socket
import ssl
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from starlette.requests import Request

import tests._cu_host as cu
from tw2k.public.share_url import request_origin, seat_link

PUBLIC = "blue-pond.trycloudflare.com"
ORIGIN = f"https://{PUBLIC}"


# --------------------------------------------------------------------- no browser

def _request(headers: dict[str, str], path: str = "/") -> Request:
    scope = {
        "type": "http", "method": "GET", "path": path, "raw_path": path.encode(), "query_string": b"",
        "scheme": "http", "server": ("127.0.0.1", 8099), "client": ("127.0.0.1", 50000),
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    return Request(scope)


CLOUDFLARED = {
    "host": PUBLIC,
    "x-forwarded-proto": "https",
    "cf-visitor": '{"scheme":"https"}',
    "cf-connecting-ip": "203.0.113.7",
    "x-forwarded-for": "203.0.113.7",
}


def test_cloudflared_headers_give_the_public_https_origin() -> None:
    req = _request(CLOUDFLARED)
    assert request_origin(req.headers, req.url.scheme, req.url.netloc) == ORIGIN
    # Some cloudflared builds send only Cf-Visitor for the scheme.
    only_visitor = {k: v for k, v in CLOUDFLARED.items() if k != "x-forwarded-proto"}
    req = _request(only_visitor)
    assert request_origin(req.headers, req.url.scheme, req.url.netloc) == ORIGIN


def test_a_host_rewriting_tunnel_still_gives_the_public_origin() -> None:
    # cloudflared --http-host-header 127.0.0.1:8099 rewrites Host and keeps the name in X-Forwarded-Host.
    req = _request({"host": "127.0.0.1:8099", "x-forwarded-host": PUBLIC, "x-forwarded-proto": "https"})
    assert request_origin(req.headers, req.url.scheme, req.url.netloc) == ORIGIN


def test_a_forged_forwarded_host_does_not_move_a_public_request() -> None:
    req = _request({"host": PUBLIC, "x-forwarded-host": "evil.example", "x-forwarded-proto": "https"})
    assert request_origin(req.headers, req.url.scheme, req.url.netloc) == ORIGIN


def test_seat_links_on_the_tunnel_keep_seat_token_and_layout() -> None:
    link = seat_link(ORIGIN, "ab12", "P1", "s/k+t=")
    got = urlsplit(link)
    assert (got.scheme, got.netloc, got.path) == ("https", PUBLIC, "/g/ab12/bot")
    q = parse_qs(got.query)
    assert q == {"seat": ["P1"], "token": ["s/k+t="], "layout": ["redesign"]}


def test_lobby_forms_through_the_tunnel_are_same_origin(tmp_path) -> None:
    from tw2k.public.config import LobbyConfig
    from tw2k.public.lobby import Lobby

    lobby = Lobby(LobbyConfig(port=0, game_ports=range(0), root=tmp_path), port_probe=lambda _p: True)
    assert lobby.same_origin(_request({**CLOUDFLARED, "origin": ORIGIN}))
    rewritten = {"host": "127.0.0.1:8099", "x-forwarded-host": PUBLIC, "x-forwarded-proto": "https", "origin": ORIGIN}
    assert lobby.same_origin(_request(rewritten))
    assert not lobby.same_origin(_request({**CLOUDFLARED, "origin": "https://evil.example"}))
    # X-Forwarded-Host only counts when the socket Host is loopback.
    forged = {**CLOUDFLARED, "x-forwarded-host": "evil.example", "origin": "https://evil.example"}
    assert not lobby.same_origin(_request(forged))


# --------------------------------------------------------------------- fake tunnel

class _FakeQuickTunnel:
    """cloudflared's edge, on a free local port, with Host kept as the public name."""

    def __init__(self, lobby_port: int, port: int, ctx: ssl.SSLContext) -> None:
        self.lobby_port = lobby_port
        self.ctx = ctx
        self.hosts: list[str] = []
        self.paths: list[str] = []
        self.upgrades = 0
        self.sock = socket.create_server(("127.0.0.1", port))
        self.sock.settimeout(0.5)
        self._stop = False
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self._stop = True
        self.thread.join(timeout=5)
        self.sock.close()

    def _serve(self) -> None:
        while not self._stop:
            try:
                raw, _ = self.sock.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            threading.Thread(target=self._conn, args=(raw,), daemon=True).start()

    def _conn(self, raw: socket.socket) -> None:
        raw.settimeout(15)
        try:
            client = self.ctx.wrap_socket(raw, server_side=True)
        except (OSError, ssl.SSLError):
            raw.close()
            return
        up: socket.socket | None = None
        try:
            buf = b""
            while True:
                while b"\r\n\r\n" not in buf:
                    chunk = client.recv(65536)
                    if not chunk:
                        return
                    buf += chunk
                head, buf = buf.split(b"\r\n\r\n", 1)
                lines = head.decode("latin-1").split("\r\n")
                method, path, _ = lines[0].split(" ", 2)
                headers = [tuple(x.split(":", 1)) for x in lines[1:] if ":" in x]
                host = next((v.strip() for k, v in headers if k.lower() == "host"), "")
                self.hosts.append(host)
                self.paths.append(path)
                upgrade = any(k.lower() == "upgrade" and "websocket" in v.lower() for k, v in headers)
                drop = {"x-forwarded-host", "x-forwarded-proto", "cf-visitor", "cf-connecting-ip", "cf-ray",
                        "x-forwarded-for"}
                out = [f"{method} {path} HTTP/1.1"]
                out += [f"{k}:{v}" for k, v in headers if k.lower() not in drop]
                out += ["X-Forwarded-Proto: https", 'Cf-Visitor: {"scheme":"https"}',
                        "Cf-Connecting-Ip: 203.0.113.7", "X-Forwarded-For: 203.0.113.7", "Cf-Ray: 0000-FAKE"]
                if up is None:
                    up = socket.create_connection(("127.0.0.1", self.lobby_port), timeout=300)
                up.sendall(("\r\n".join(out) + "\r\n\r\n").encode("latin-1"))
                if upgrade:
                    self.upgrades += 1
                    if buf:
                        up.sendall(buf)
                    self._pipe(client, up)
                    return
                length = int(next((v for k, v in headers if k.lower() == "content-length"), "0") or 0)
                while len(buf) < length:
                    chunk = client.recv(65536)
                    if not chunk:
                        return
                    buf += chunk
                body, buf = buf[:length], buf[length:]
                if body:
                    up.sendall(body)
                if not self._relay_response(up, client, method):
                    return
        except (OSError, ssl.SSLError, ValueError):
            return
        finally:
            for s in (client, up):
                if s is not None:
                    try:
                        s.close()
                    except OSError:
                        pass

    @staticmethod
    def _relay_response(up: socket.socket, client: socket.socket, method: str) -> bool:
        """One response, Content-Length or chunked. False when either side should close."""
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = up.recv(65536)
            if not chunk:
                return False
            buf += chunk
        head, rest = buf.split(b"\r\n\r\n", 1)
        text = head.decode("latin-1").lower()
        status = int(text.split(" ", 2)[1])
        client.sendall(head + b"\r\n\r\n")
        close = "\r\nconnection: close" in text
        if method == "HEAD" or status in (204, 304) or 100 <= status < 200:
            return not close
        if "\r\ntransfer-encoding: chunked" in text:
            data = rest
            while not data.endswith(b"0\r\n\r\n"):
                chunk = up.recv(65536)
                if not chunk:
                    return False
                data += chunk
            client.sendall(data)
            return not close
        length = None
        for line in text.split("\r\n"):
            if line.startswith("content-length:"):
                length = int(line.split(":", 1)[1])
        if length is None:
            client.sendall(rest)
            while True:
                chunk = up.recv(65536)
                if not chunk:
                    return False
                client.sendall(chunk)
        data = rest
        while len(data) < length:
            chunk = up.recv(65536)
            if not chunk:
                return False
            data += chunk
        client.sendall(data)
        return not close

    @staticmethod
    def _pipe(a: socket.socket, b: socket.socket) -> None:
        a.settimeout(None)
        b.settimeout(None)
        while True:
            ready, _, _ = select.select([a, b], [], [], 60)
            if not ready:
                return
            for s in ready:
                if isinstance(s, ssl.SSLSocket):
                    data = s.recv(65536)
                    while data and s.pending():
                        data += s.recv(s.pending())
                else:
                    data = s.recv(65536)
                if not data:
                    return
                (b if s is a else a).sendall(data)


def _cert(directory: Path) -> tuple[str, str]:
    pytest.importorskip("cryptography")
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, PUBLIC)])
    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    issued = (
        x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(private.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5)).not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName(
            [x509.DNSName(PUBLIC), x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))]), critical=False)
        .sign(private, hashes.SHA256())
    )
    # A throwaway self-signed pair under tmp_path for the fake edge, not a stored key.
    key_path, cert_path = directory / "edge.key", directory / "edge.crt"
    key_path.write_bytes(private.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    cert_path.write_bytes(issued.public_bytes(serialization.Encoding.PEM))
    return str(cert_path), str(key_path)


def _wait_http(url: str, timeout_s: float = 30) -> None:
    import httpx

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if httpx.get(url, timeout=1.0).status_code < 500:
                return
        except Exception:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"never answered {url}")


def _wait_cockpit(page) -> None:
    page.wait_for_function(
        """() => {
          const c = document.querySelector('#credits');
          return document.readyState === 'complete' && c && c.textContent && c.textContent !== '-';
        }""",
        timeout=90_000,
    )


def test_lobby_and_seat_links_work_through_a_fake_quick_tunnel(monkeypatch, tmp_path) -> None:
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    import uvicorn

    from tests._port_lock import release_ports
    from tw2k.public.ai_cockpit_launch import cockpit_seat_url
    from tw2k.public.config import LobbyConfig
    from tw2k.public.lobby import create_lobby_app

    base = cu.free_port(cu.LOBBY_FREE_START, count=4)
    lobby_port, edge_port = base, base + 1
    game_ports = range(base + 2, base + 4)
    for port in (lobby_port, edge_port, *game_ports):
        assert port != 8099 and cu.allowed_test_port(port)

    cfg = LobbyConfig(port=lobby_port, game_ports=game_ports, root=tmp_path / "lobby", idle_s=3600, tick_s=30,
                      boot_timeout_s=240, max_games=1)
    app = create_lobby_app(cfg, port_probe=lambda _p: True)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=lobby_port, log_level="warning",
                                           ws="websockets", proxy_headers=False))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    edge: _FakeQuickTunnel | None = None
    try:
        _wait_http(f"http://127.0.0.1:{lobby_port}/healthz")
        cert, key = _cert(tmp_path)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert, key)
        edge = _FakeQuickTunnel(lobby_port, edge_port, ctx)
        _drive(sync, edge_port, app.state.lobby, edge, cockpit_seat_url)
    finally:
        if edge is not None:
            edge.close()
        server.should_exit = True
        thread.join(timeout=20)
        release_ports(lobby_port, edge_port, *game_ports)


def _drive(sync, edge_port: int, lobby, edge: _FakeQuickTunnel, cockpit_seat_url) -> None:
    seen: list[str] = []
    failed: list[str] = []
    with sync() as pw:
        browser = pw.chromium.launch(args=[f"--host-resolver-rules=MAP {PUBLIC}:443 127.0.0.1:{edge_port}"])
        try:
            def context():
                ctx = browser.new_context(ignore_https_errors=True, viewport={"width": 1280, "height": 800})
                ctx.on("request", lambda r: seen.append(r.url))
                ctx.on("requestfailed", lambda r: failed.append(f"{r.url} {r.failure}"))
                ctx.on("websocket", lambda ws: seen.append(ws.url))
                return ctx

            creator, guest, third = context(), context(), context()
            home = creator.new_page()
            home.goto(ORIGIN + "/", wait_until="domcontentloaded")
            home.get_by_role("button", name="I understand").click()
            home.wait_for_url(ORIGIN + "/")
            home.get_by_role("link", name="New game").click()
            home.wait_for_selector("#humans")
            home.fill("#name", "Tunnel")
            home.select_option("#universe_size", "200")
            home.select_option("#humans", "3")
            home.select_option("#bots", "0")
            home.get_by_role("button", name="Create game").click(timeout=300_000)
            home.wait_for_selector("[data-testid=seat-link]", timeout=60_000)
            links = {
                row.get_attribute("data-seat"): row.inner_text().strip()
                for row in home.locator("[data-testid=seat-link]").all()
            }
            assert set(links) == {"P1", "P2", "P3"}, links
            body = home.locator("body").inner_text()
            assert "127.0.0.1" not in body and "localhost" not in body
            for seat, url in links.items():
                got = urlsplit(url)
                assert (got.scheme, got.netloc) == ("https", PUBLIC), url
                q = parse_qs(got.query)
                assert q["seat"] == [seat] and q["token"][0] and q["layout"] == ["redesign"], url
            gid = urlsplit(links["P1"]).path.split("/")[2]
            joins = [c.inner_text().strip() for c in home.locator("code.link").all() if "/join/" in c.inner_text()]
            assert len(joins) == 3, joins
            for href in joins:
                assert href.startswith(ORIGIN + f"/join/{gid}/"), href

            # P1: the created-page link as copied.
            p1 = creator.new_page()
            p1.goto(links["P1"], wait_until="domcontentloaded")
            _wait_cockpit(p1)
            assert urlsplit(p1.url).netloc == PUBLIC

            # P2: the mode=cu&token= link the cockpit player and the lobby hand out, in a fresh browser.
            token2 = parse_qs(urlsplit(links["P2"]).query)["token"][0]
            p2 = guest.new_page()
            p2.goto(ORIGIN + cockpit_seat_url(gid, "P2", token2), wait_until="domcontentloaded")
            accept = p2.get_by_role("button", name="I understand")
            p2.wait_for_selector("form[action$='/accept'] button, #credits", timeout=30_000)
            if accept.count():
                with p2.expect_navigation(wait_until="domcontentloaded", timeout=30_000):
                    accept.click()
            _wait_cockpit(p2)
            assert urlsplit(p2.url).netloc == PUBLIC
            assert "mode=cu" in p2.url
            # The redesign cockpit takes the token off the address bar once it has the seat.
            assert "token=" not in urlsplit(p2.url).query

            # P3: the invite join link, through the join form, onto the cockpit.
            p3 = third.new_page()
            p3.goto(next(h for h in joins if h.split("?")[0].endswith("/P3")), wait_until="domcontentloaded")
            accept = p3.get_by_role("button", name="I understand")
            if accept.count():
                accept.click()
                p3.wait_for_load_state("domcontentloaded")
            p3.locator("form[action*='/join'] button[type=submit], form[action*='/join'] button").first.click()
            _wait_cockpit(p3)
            assert urlsplit(p3.url).netloc == PUBLIC and f"/g/{gid}/" in p3.url
        finally:
            browser.close()
    bad = [u for u in seen if urlsplit(u).hostname and urlsplit(u).hostname != PUBLIC]
    assert not bad, "requests left the tunnel name: " + json.dumps(bad[:20])
    assert all(h == PUBLIC for h in edge.hosts), set(edge.hosts)
    tunnel_fail = [f for f in failed if "net::ERR_ABORTED" not in f]
    assert not tunnel_fail, tunnel_fail[:20]
    assert any(p.startswith(f"/g/{gid}/") for p in edge.paths)
