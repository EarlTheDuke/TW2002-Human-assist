"""Bridge: the seat owner talks to the pilot on that seat only."""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest

from tests._cu_host import VIEW_H, VIEW_W, CuHost
from tw2k.engine import GameConfig
from tw2k.server import seat_links
from tw2k.server.app import create_app
from tw2k.server.runner import AgentSpec, MatchSpec

TOK2 = "bridge-token-p2-00000000000000000"
TOK3 = "bridge-token-p3-00000000000000000"


def _spec() -> MatchSpec:
    return MatchSpec(
        config=GameConfig(seed=11, universe_size=40, max_days=2, turns_per_day=8, starting_credits=20_000,
                          enable_ferrengi=False, enable_planets=False, action_delay_s=0.0),
        agents=[
            AgentSpec(player_id="P1", name="HBot", kind="heuristic"),
            AgentSpec(player_id="P2", name="Seat2", kind="external", external_token=TOK2),
            AgentSpec(player_id="P3", name="Seat3", kind="external", external_token=TOK3),
        ],
        action_delay_s=0.0,
        external_timeout_s=30.0,
    )


def _run(tmp_path: Path, body) -> None:
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"

    async def go() -> None:
        client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5555)),
            base_url="http://bridge.test",
        )
        await runner.start(_spec())
        for _ in range(300):
            if runner.state.agents and runner.state.universe is not None:
                break
            await asyncio.sleep(0.02)
        try:
            await body(client)
        finally:
            await runner.stop()
            await client.aclose()

    asyncio.run(go())


def _auth(token: str, seat: str = "P2") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-TW2K-Seat": seat}


def test_bridge_is_own_seat_plain_text_and_ordered(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TW2K_BRIDGE_DIR", str(tmp_path / "bridge"))
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)

    async def body(client) -> None:
        missing = await client.get("/harness/v1/bridge")
        assert missing.status_code == 401
        spec = await client.get("/harness/v1/bridge", headers={"cookie": "tw2k_spectator=look"})
        assert spec.status_code == 403
        other = await client.get("/harness/v1/bridge", params={"seat": "P3"}, headers=_auth(TOK2))
        assert other.status_code == 403
        other_post = await client.post(
            "/harness/v1/bridge", headers=_auth(TOK2), json={"text": "nope", "seat": "P3"},
        )
        assert other_post.status_code == 403
        empty = await client.post("/harness/v1/bridge", headers=_auth(TOK2), json={"text": "  "})
        assert empty.status_code == 400
        huge = await client.post("/harness/v1/bridge", headers=_auth(TOK2), json={"text": "x" * 501})
        assert huge.status_code == 400
        nasty = "<script>alert(1)</script>"
        first = await client.post("/harness/v1/bridge", headers=_auth(TOK2), json={"text": nasty})
        assert first.status_code == 200
        assert first.json()["text"] == nasty and first.json()["role"] == "captain"
        assert first.json()["status"] == "pending"
        second = await client.post("/harness/v1/bridge", headers=_auth(TOK2), json={"text": "hold the port"})
        assert second.status_code == 200
        page = await client.get("/harness/v1/bridge", params={"since": first.json()["id"]}, headers=_auth(TOK2))
        assert page.status_code == 200
        msgs = page.json()["messages"]
        assert [m["text"] for m in msgs] == ["hold the port"]
        assert msgs[0]["id"] > first.json()["id"]
        hidden = await client.get("/harness/v1/bridge", headers=_auth(TOK3, "P3"))
        assert hidden.json()["messages"] == []
        cookie = {"cookie": f"{seat_links.cookie_name('P2')}={TOK2}"}
        no_csrf = await client.post("/harness/v1/bridge", headers=cookie, json={"text": "cookie"})
        assert no_csrf.status_code == 403
        with_csrf = await client.post(
            "/harness/v1/bridge",
            headers={**cookie, "X-TW2K-Seat": "P2"},
            json={"text": "cookie ok"},
        )
        assert with_csrf.status_code == 200
        reply = await client.post(
            "/harness/v1/bridge/reply",
            headers=_auth(TOK2),
            json={"text": "taken, heading there", "ack_of": first.json()["id"]},
        )
        assert reply.status_code == 200 and reply.json()["role"] == "pilot"
        bad = await client.post(
            "/harness/v1/bridge/ack", headers=_auth(TOK2), json={"id": first.json()["id"], "status": "maybe"},
        )
        assert bad.status_code == 400
        acked = await client.post(
            "/harness/v1/bridge/ack", headers=_auth(TOK2), json={"id": first.json()["id"], "status": "taken"},
        )
        assert acked.status_code == 200 and acked.json()["status"] == "taken"
        pending = await client.get("/harness/v1/bridge/pending", headers=_auth(TOK2))
        ids = [row["id"] for row in pending.json()["orders"]]
        assert first.json()["id"] in ids and second.json()["id"] in ids
        done = await client.post(
            "/harness/v1/bridge/ack", headers=_auth(TOK2), json={"id": first.json()["id"], "status": "done"},
        )
        assert done.json()["status"] == "done"
        left = await client.get("/harness/v1/bridge/pending", headers=_auth(TOK2))
        assert first.json()["id"] not in [row["id"] for row in left.json()["orders"]]
        for n in range(20):
            burst = await client.post("/harness/v1/bridge", headers=_auth(TOK3, "P3"), json={"text": f"n{n}"})
            assert burst.status_code == 200
        limited = await client.post("/harness/v1/bridge", headers=_auth(TOK3, "P3"), json={"text": "too many"})
        assert limited.status_code == 429

    _run(tmp_path, body)


def test_bridge_panel_stays_off_the_map_and_cu_stays_800(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TW2K_BRIDGE_DIR", str(tmp_path / "bridge"))
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    sync_api = pytest.importorskip("playwright.sync_api")
    with CuHost(tmp_path, TOK2) as host, sync_api.sync_playwright() as pw:
        browsers = []
        for name in ("chromium", "firefox"):
            try:
                browsers.append(getattr(pw, name).launch())
            except Exception as exc:
                pytest.fail(f"{name} did not launch: {exc}")
        try:
            for browser in browsers:
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                page.goto(f"{host.base}/bot?seat=P2&token={TOK2}")
                page.wait_for_selector("#turnBanner.turn", timeout=20_000)
                assert page.evaluate(
                    "() => !!document.querySelector('#colAct #viewport + #mapCard')"
                    " && !!document.querySelector('#colKnow #bridgePanel')"
                )
                page.get_by_test_id("bridge-panel").locator("summary").click()
                nasty = "<img src=x onerror=alert(1)>"
                page.get_by_test_id("bridge-input").fill(nasty)
                page.get_by_test_id("bridge-send").click()
                page.wait_for_function(
                    "(needle) => document.querySelector('#bridgeList').textContent.includes(needle)",
                    arg=nasty,
                    timeout=8_000,
                )
                assert page.evaluate("() => document.querySelectorAll('#bridgeList img, #bridgeList script').length") == 0
                page.get_by_test_id("bridge-input").focus()
                page.keyboard.type("s")
                assert page.get_by_test_id("bridge-input").input_value() == "s"
                page.close()
                cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
                cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK2}")
                cu.wait_for_function(
                    "() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')",
                    timeout=20_000,
                )
                cu.wait_for_selector("[data-testid=cu-bridge]", timeout=8_000)
                height = cu.evaluate("() => document.scrollingElement.scrollHeight")
                assert height <= VIEW_H, height
                for _ in range(4):
                    if cu.evaluate("() => document.querySelector('[data-testid=cu-bridge]').hidden"):
                        break
                    cu.get_by_role("button", name="Done").first.click()
                    cu.wait_for_timeout(400)
                assert cu.evaluate("() => document.querySelector('[data-testid=cu-bridge]').hidden")
                cu.close()
        finally:
            for browser in browsers:
                browser.close()
