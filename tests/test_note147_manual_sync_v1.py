"""NOTE 147: the player manual names the sections a player meets, and every link resolves.

Headings are the ones in SECTIONS, including the rules block. A link is dead when a
contents anchor has no id, or when a path on the page does not answer 200.
The string "1" does not turn the v3.11 profile on. This file does not change a rule.
"""
from __future__ import annotations

import asyncio
import re
import threading

import httpx
import pytest

import tw2k.engine.constants as K
from tw2k.public.manual import SECTIONS, render

_SECTION = re.compile(r'<section id="([a-z0-9-]+)">(.*?)</section>', re.S)
_HASH = re.compile(r'href="#([^"]+)"')
_PATH = re.compile(r'href="(/[^"#?]*)')

_TOPICS = (
    "Comms panel",
    "COMMS_V311_MODE",
    "fell on deaf ears",
    "PLANET_ZDY_MODE",
    "1,666 experience",
    "QUASAR_ATM_ORDER_MODE",
    "PLANET_INTERDICT_SAFE_MODE",
    "FULL_LENGTH_TURN_LIMITS_MODE",
    "Turns left today",
    "trycloudflare.com",
    "layout=redesign",
    "Lost the host. Reconnecting.",
    "still being tuned",
    "ten pictures",
    "does not play that same picture twice",
    "Plotting a course does not",
    "Classic Trade Wars 2002 v3.11",
)


def _ids(html: str) -> set[str]:
    return set(re.findall(r'id="([^"]+)"', html))


def _section(html: str, sid: str) -> str:
    for found, body in _SECTION.findall(html):
        if found == sid:
            return body
    raise AssertionError(sid)


def test_each_topic_names_what_you_do_and_which_switch_it_uses(monkeypatch) -> None:
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    pages = {}
    for value in ("legacy", "1", "v311"):
        monkeypatch.setattr(K, "V311_PROFILE", value)
        pages[value] = render("Galaxy War Command")
    for value, html in pages.items():
        for needle in _TOPICS:
            assert needle in html, (value, needle)
        assert "Full-length games use" not in html
    assert "in v3.11 games" not in pages["legacy"]
    assert "in v3.11 games" not in pages["1"]
    assert pages["legacy"] != pages["v311"]
    for sid in ("warp-pictures", "sharing", "staying-up"):
        assert _section(pages["legacy"], sid) == _section(pages["1"], sid)
        assert _section(pages["legacy"], sid) == _section(pages["v311"], sid)
    quiet = pages["legacy"]
    assert "<td>If the computer or the browser stops</td><td>off</td>" in quiet
    assert "The rules table marks this section off." in quiet


def test_every_manual_heading_renders_and_no_link_is_dead(tmp_path) -> None:
    lobby_html = render("Galaxy War Command")
    game_html = render("Galaxy War Command", lobby=False)
    for html in (lobby_html, game_html):
        ids = _ids(html)
        assert "rules-in-this-game" in ids
        for href in _HASH.findall(html):
            assert href in ids, href
        for sid, title in SECTIONS:
            assert f'<h2>{title}</h2>' in html
            assert sid in ids
            assert f'href="#{sid}"' in html

    from tests._cu_host import LOBBY_FREE_START, allowed_test_port, free_port
    from tests._port_lock import release_ports
    from tw2k.public.config import LobbyConfig
    from tw2k.public.lobby import create_lobby_app
    from tw2k.server.app import create_app

    lobby_port = free_port(LOBBY_FREE_START)
    game_base = free_port(LOBBY_FREE_START, count=10)
    assert lobby_port != 8099 and allowed_test_port(lobby_port)
    cfg = LobbyConfig(port=lobby_port, game_ports=range(game_base, game_base + 10), root=tmp_path)
    lobby = create_lobby_app(cfg)
    worker = create_app(auto_start=False)

    async def _follow(app, html: str) -> str:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://manual") as client:
            for path in sorted(set(_PATH.findall(html))):
                got = await client.get(path)
                assert got.status_code == 200, path
                assert got.text.strip()
            manual = await client.get("/manual")
        assert manual.status_code == 200
        return manual.text

    try:
        served_lobby = asyncio.run(_follow(lobby, lobby_html))
        served_game = asyncio.run(_follow(worker, game_html))
    finally:
        release_ports(lobby_port, *range(game_base, game_base + 10))

    for body in (served_lobby, served_game):
        for _sid, title in SECTIONS:
            assert f"<h2>{title}</h2>" in body
        assert "Rules in this game" in body

    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    import uvicorn

    port = free_port()
    assert port != 8099 and allowed_test_port(port)
    server = uvicorn.Server(uvicorn.Config(worker, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=lambda: asyncio.run(server.serve()), daemon=True)
    thread.start()
    try:
        for _ in range(100):
            try:
                httpx.get(f"http://127.0.0.1:{port}/manual", timeout=0.5)
                break
            except httpx.HTTPError:
                thread.join(0.05)
        else:
            raise RuntimeError("manual server did not start")
        with sync() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(java_script_enabled=False, viewport={"width": 1280, "height": 800})
            page = ctx.new_page()
            page.goto(f"http://127.0.0.1:{port}/manual")
            text = page.inner_text("body")
            for _sid, title in SECTIONS:
                assert title in text
            assert "Rules in this game" in text
            for heading in page.locator("h2").all():
                assert heading.inner_text().strip()
            page.close()
            ctx.close()
            browser.close()
    finally:
        server.should_exit = True
        thread.join(5)
        release_ports(port)
