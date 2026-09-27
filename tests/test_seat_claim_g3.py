"""Grokbot-player G3 - seat login without pasting secrets.

Done when (docs/plans/2026-09-26-grokbot-plays-by-screen.md, G3): tests cover
claim, cookie auth, wrong seat 403, invalid link 401.

    GET /bot/claim?seat=P2&token=<P2 token>  -> 303 /bot?seat=P2&mode=cu + HttpOnly tw2k_seat_P2 cookie
    /harness/v1/P2/*  with that cookie        -> same as Bearer (writes also need X-TW2K-Seat)
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from tests._cu_host import CuHost
from tw2k.engine import GameConfig
from tw2k.server import seat_links
from tw2k.server.app import create_app
from tw2k.server.runner import AgentSpec, MatchSpec

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "web" / "bot.js").read_text(encoding="utf-8")
TOK2 = "g3-claim-token-p2-000000000000000"
TOK3 = "g3-claim-token-p3-000000000000000"


def _spec() -> MatchSpec:
    return MatchSpec(
        config=GameConfig(seed=9, universe_size=60, max_days=2, turns_per_day=12, starting_credits=25_000,
                          enable_ferrengi=False, enable_planets=False, action_delay_s=0.0),
        agents=[
            AgentSpec(player_id="P1", name="HBot", kind="heuristic"),
            AgentSpec(player_id="P2", name="Seat2", kind="external", external_token=TOK2),
            AgentSpec(player_id="P3", name="Seat3", kind="external", external_token=TOK3),
        ],
        action_delay_s=0.0,
        external_timeout_s=30.0,
    )


def _run(tmp_path: Path, body, client_host: str = "127.0.0.1") -> None:
    """Start a 3-seat match in-process and run `body(client, runner)`."""
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"

    async def go() -> None:
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=(client_host, 5555)), base_url="http://g3.test")
        await runner.start(_spec())
        for _ in range(300):
            if runner.state.agents and runner.state.universe is not None:
                break
            await asyncio.sleep(0.02)
        try:
            await body(client, runner)
        finally:
            await runner.stop()
            await client.aclose()

    asyncio.run(go())


def _cookie(tok: str, seat: str = "P2") -> dict[str, str]:
    return {"cookie": f"{seat_links.cookie_name(seat)}={tok}"}


# ------------------------------------------------------------------ claim
def test_claim_sets_httponly_seat_cookie_and_redirects_to_cu(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)

    async def body(client, runner) -> None:
        r = await client.get("/bot/claim", params={"seat": "p2", "token": TOK2})
        assert r.status_code == 303
        assert r.headers["location"] == "/bot?seat=P2&mode=cu"
        sc = r.headers["set-cookie"]
        assert sc.startswith(f"tw2k_seat_P2={TOK2};")
        assert "HttpOnly" in sc and "samesite=lax" in sc.lower() and "Path=/harness/" in sc and "Secure" not in sc
        assert r.headers["cache-control"] == "no-store" and r.headers["referrer-policy"] == "no-referrer"
        # Behind an https tunnel the cookie is Secure.
        r = await client.get("/bot/claim", params={"seat": "P2", "token": TOK2}, headers={"x-forwarded-proto": "https"})
        assert "Secure" in r.headers["set-cookie"]
        # mode=default lands on the classic layout.
        r = await client.get("/bot/claim", params={"seat": "P2", "token": TOK2, "mode": "default"})
        assert r.headers["location"] == "/bot?seat=P2"

    _run(tmp_path, body)


# ------------------------------------------------------------------ cookie auth
def test_cookie_authenticates_seat_routes_and_writes_need_the_seat_header(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)

    async def body(client, runner) -> None:
        ck = _cookie(TOK2)
        assert (await client.get("/harness/v1/P2/status", headers=ck)).status_code == 200
        r = await client.get("/harness/v1/P2/observation", params={"peek": 1, "format": "both"}, headers=ck)
        assert r.status_code == 200 and r.json()["observation"]["self_id"] == "P2"
        assert (await client.get("/harness/v1/P2/events", params={"since": 0}, headers=ck)).status_code == 200
        assert (await client.get("/harness/v1/seats", headers=ck)).status_code == 200
        assert (await client.get("/harness/v1/rules", headers=ck)).status_code == 200

        for _ in range(400):
            st = (await client.get("/harness/v1/P2/status", headers=ck)).json()
            if st.get("awaiting_input"):
                break
            await asyncio.sleep(0.02)
        assert st.get("awaiting_input"), "P2 never got a turn"
        post = {"turn_seq": st["turn_seq"], "action": {"kind": "wait", "args": {}}}
        # CSRF guard: a cookie alone cannot write; the header must name this seat.
        assert (await client.post("/harness/v1/P2/action", json=post, headers=ck)).status_code == 403
        assert (await client.post("/harness/v1/P2/action", json=post, headers={**ck, "x-tw2k-seat": "P3"})).status_code == 403
        r = await client.post("/harness/v1/P2/action", json=post, headers={**ck, "x-tw2k-seat": "P2"})
        assert r.status_code == 200 and r.json()["accepted"] is True
        # Bearer clients are unaffected (no extra header needed).
        assert (await client.get("/harness/v1/P2/status", headers={"authorization": f"Bearer {TOK2}"})).status_code == 200

    _run(tmp_path, body)


# ------------------------------------------------------------------ wrong seat 403
def test_wrong_seat_is_403_for_link_and_cookie(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)

    async def body(client, runner) -> None:
        r = await client.get("/bot/claim", params={"seat": "P3", "token": TOK2})
        assert r.status_code == 403 and "set-cookie" not in r.headers
        # P2's cookie on P3's routes: authenticated, but not this seat.
        assert (await client.get("/harness/v1/P3/status", headers=_cookie(TOK2))).status_code == 403
        assert (await client.get("/harness/v1/P3/observation", params={"peek": 1}, headers=_cookie(TOK2))).status_code == 403
        # A cookie planted under the wrong seat name still resolves to its real owner.
        assert (await client.get("/harness/v1/P3/status", headers=_cookie(TOK2, seat="P3"))).status_code == 403
        # Two claimed seats in one browser: each route uses its own cookie.
        both = {"cookie": f"tw2k_seat_P2={TOK2}; tw2k_seat_P3={TOK3}"}
        assert (await client.get("/harness/v1/P2/status", headers=both)).json()["player_id"] == "P2"
        assert (await client.get("/harness/v1/P3/status", headers=both)).json()["player_id"] == "P3"

    _run(tmp_path, body)


# ------------------------------------------------------------------ invalid link 401
def test_invalid_link_and_cookie_are_401(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)

    async def body(client, runner) -> None:
        for params in ({"seat": "P2", "token": "not-a-real-token-000000000000"}, {"seat": "P2"}, {"token": TOK2}, {}):
            r = await client.get("/bot/claim", params=params)
            assert r.status_code == 401 and "set-cookie" not in r.headers, params
        assert (await client.get("/harness/v1/P2/status", headers=_cookie("forged-token-0000000000000000"))).status_code == 401
        assert (await client.get("/harness/v1/P2/status")).status_code == 401

    _run(tmp_path, body)


def test_claim_keeps_loopback_rule_and_skips_spectator_gate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_HARNESS_ALLOW_REMOTE", raising=False)
    monkeypatch.setenv("TW2K_SPECTATOR_TOKEN", "g3-spectator-token-0000000000")

    async def remote(client, runner) -> None:
        assert (await client.get("/bot/claim", params={"seat": "P2", "token": TOK2})).status_code == 403
        monkeypatch.setenv("TW2K_HARNESS_ALLOW_REMOTE", "1")
        assert (await client.get("/bot/claim", params={"seat": "P2", "token": TOK2})).status_code == 303
        assert (await client.get("/state")).status_code == 401  # the spectator stays gated

    _run(tmp_path, remote, client_host="10.1.2.3")


# ------------------------------------------------------------------ host writes the links
def test_host_writes_one_link_per_external_seat(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    links = tmp_path / "seat_links"
    monkeypatch.setenv("TW2K_SEAT_LINKS_DIR", str(links))
    monkeypatch.setenv("TW2K_PUBLIC_BASE_URL", "https://example.test/")
    body = {"num_agents": 3, "agent_kind": "heuristic", "universe_size": 60, "max_days": 1, "turns_per_day": 5,
            "agents": [{"kind": "heuristic"}, {"kind": "external", "token": TOK2}, {"kind": "external", "token": TOK3}]}

    async def go(app, expect: bool) -> None:
        app.state.runner._saves_root = tmp_path / "saves"
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5555)), base_url="http://g3.test")
        assert (await client.post("/control/restart", json=body)).status_code == 200
        await app.state.runner.stop()
        await client.aclose()
        assert links.exists() == expect

    asyncio.run(go(create_app(auto_start=False), expect=False))  # tests / embedded apps never write
    asyncio.run(go(create_app(auto_start=False, seat_links=True), expect=True))
    assert sorted(p.name for p in links.iterdir()) == ["P2.txt", "P3.txt"]
    assert (links / "P2.txt").read_text(encoding="utf-8") == f"https://example.test/bot/claim?seat=P2&token={TOK2}\n"


def test_write_seat_links_script_prints_masked_tokens_only(tmp_path: Path) -> None:
    toks = tmp_path / "tokens.json"
    toks.write_text(f'{{"P3": "{TOK3}", "P6": "{TOK2}"}}', encoding="utf-8")
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "write_seat_links.py"), "--tokens-file", str(toks),
                          "--dir", str(tmp_path / "links"), "--base", "http://127.0.0.1:8032"],
                         capture_output=True, text=True, check=True, timeout=60).stdout
    assert TOK2 not in out and TOK3 not in out and "g3-c...0000" in out
    assert (tmp_path / "links" / "P6.txt").read_text(encoding="utf-8").strip() == f"http://127.0.0.1:8032/bot/claim?seat=P6&token={TOK2}"


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_seat_links_are_gitignored() -> None:
    r = subprocess.run(["git", "check-ignore", "-q", ".tw2k/seat_links/P6.txt"], cwd=ROOT, check=False)
    assert r.returncode == 0


def test_bot_js_uses_cookie_when_no_token_is_pasted() -> None:
    assert 'if (state.token) h.Authorization = `Bearer ${state.token}`;' in JS
    assert '"X-TW2K-Seat": state.seat' in JS and 'credentials: "same-origin"' in JS
    assert 'if (state.token || params.get("seat"))' in JS, "a seat link lands on /bot?seat=..; auto-connect via cookie"
    assert "Paste the harness bearer token first." not in JS
    assert "tw2k_bot_token_${state.seat}" in JS, "only a token stored for this seat is reused"


# ------------------------------------------------------------------ browser: one click, no paste
def test_browser_claim_link_plays_without_pasting(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK2) as host:
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()
        page.goto(seat_links.claim_url(host.base, "P2", TOK2))
        assert page.url == f"{host.base}/bot?seat=P2&mode=cu"
        page.wait_for_selector("#cuTurn.turn", timeout=20_000)
        assert page.locator("#tokenInput").input_value() == ""
        assert page.evaluate("Object.keys(localStorage).filter((k) => k.startsWith('tw2k_bot_token'))") == []
        assert "tw2k_seat_" not in page.evaluate("document.cookie"), "seat cookie must be HttpOnly"
        page.keyboard.press("s")
        page.wait_for_function("/SCAN .*ok/.test(document.querySelector('#cuToast').textContent)", timeout=15_000)
        # A fresh browser without the cookie is told how to sign in, not shown an error dump.
        page2 = browser.new_context().new_page()
        page2.goto(f"{host.base}/bot?seat=P2&mode=cu")
        page2.wait_for_function("document.querySelector('#err').textContent.includes('seat_links')", timeout=10_000)
        assert page2.locator("#authBar").is_visible()
        ctx.close()
