"""COMMANDER NOTE 67: a player's manual a person and a computer-use AI can both read.

Numbers come from the engine at render time. The page is plain HTML. The cockpit
button exists only on the redesign layout.
"""

from __future__ import annotations

import asyncio
import re
import threading
from pathlib import Path

import httpx
import pytest

import tw2k.engine.constants as K
from tw2k.engine import GameConfig
from tw2k.public.config import LobbyConfig
from tw2k.public.lobby import create_lobby_app
from tw2k.public.manual import SECTIONS, render
from tw2k.public.pages import about, disclaimer
from tw2k.public.worker import rewrite_text
from tw2k.server.app import create_app

REPO = Path(__file__).resolve().parents[1]
SHOTS = REPO / "docs" / "playtests" / "player-manual-v1"
HEADINGS = [title for _sid, title in SECTIONS]


def _free_port() -> int:
    from tests._cu_host import free_port

    return free_port()


def test_every_section_has_an_anchor_and_the_contents_resolve() -> None:
    html = render("Galaxy War Command")
    ids = set(re.findall(r'id="([a-z0-9-]+)"', html))
    hrefs = re.findall(r'href="#([a-z0-9-]+)"', html)
    assert hrefs
    for href in hrefs:
        assert href in ids
    for sid, title in SECTIONS:
        assert f'id="{sid}"' in html
        assert f"<h2>{title}</h2>" in html
    assert "<table>" in html
    assert "<script" not in html.lower()
    assert "<canvas" not in html.lower()
    assert "<img" not in html.lower()
    assert "Original rule source:" in html


def test_numbers_follow_the_engine_under_legacy_and_v311(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    legacy = render("Galaxy War Command")
    credits, turns, fighters = K.opening_loadout(K.STARTING_CREDITS, K.STARTING_TURNS_PER_DAY, 0)
    assert f"{credits:,} credits" in legacy
    assert f"{turns:,} turns" in legacy
    assert f"{fighters:,} fighters" in legacy
    assert f"{K.TERRA_LOAD_TURNS} turn" in legacy
    assert f"{K.HOME_PLANET_FUEL:,}" in legacy

    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    live = render("Galaxy War Command")
    live_credits, live_turns, live_fighters = K.opening_loadout(K.STARTING_CREDITS, K.STARTING_TURNS_PER_DAY, 0)
    assert live_credits == K.LIVE_STARTING_CREDITS
    assert live_turns == K.LIVE_STARTING_TURNS
    assert live_fighters == K.LIVE_STARTING_FIGHTERS
    assert f"{live_credits:,} credits" in live
    assert f"{live_turns:,} turns" in live
    assert f"{live_fighters:,} fighters" in live
    assert live != legacy

    monkeypatch.setattr(K, "TERRA_LOAD_TURNS", 7)
    planted = render("Galaxy War Command")
    assert planted != live
    assert "Loading them costs 7 turn" in planted
    assert "Loading them costs 1 turn" not in planted


def test_added_sections_follow_the_engine_and_name_v311_only_rules(monkeypatch) -> None:
    """NOTE 84. New sections read the live helpers. Profile-only rules say so."""
    from tw2k.engine.victory import end_rule_line

    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    legacy = render("Galaxy War Command")
    for sid in ("ship-trade-in", "rankings"):
        assert f'id="{sid}"' in legacy
    assert "Ship trade-in" in legacy
    assert "Rankings and the end of the game" in legacy
    assert "Fighters to the C.E.O. when a member leaves: Only the v3.11 profile turns this on. In this process it is off." in legacy
    assert "Alignment join check: Only the v3.11 profile turns this on. In this process it is off." in legacy
    assert "Least-extreme mixed-corp experience: Only the v3.11 profile turns this on. In this process it is off." in legacy
    assert "the highest good alignment, divided by 4" in legacy
    assert "Day roll while a seat holds the turn: Only the v3.11 profile turns this on. In this process it is off." in legacy
    assert "The day does not roll while a seat holds its turn." in legacy
    assert "Part-by-part trade-in: The v3.11 profile turns this on. In this process it is off." in legacy
    assert "Trade-in surplus: The v3.11 profile turns this on. In this process it is off." in legacy
    assert "25 percent of the hull" in legacy
    assert f"{K.trade_in_credit(K.STARTING_SHIP):,} credits" in legacy
    assert "Hungry buy-price anchor: The v3.11 profile turns this on. In this process it is off." in legacy
    assert "fuel 38, organics 73, equipment 102" in legacy
    assert "Experience ranking of every trader: The v3.11 profile turns this on. In this process it is off." in legacy
    assert "not published" in legacy
    assert end_rule_line(10) in legacy
    assert "highest net worth" in legacy
    assert "End game for everyone" in legacy
    assert "GAME OVER - Ended by the game's creator." in legacy
    assert "not a v3.11-only rule" in legacy
    assert "until the next day" in legacy
    assert "still faces the quasar" in legacy
    assert "200 shields" in legacy
    assert "Bust-clear interval: The v3.11 profile turns this on. In this process it is off." in legacy
    assert "Every day clears every bust." in legacy
    assert "Ether probe cap: The v3.11 profile turns this on. In this process it is off." in legacy
    assert "No maximum number of ether probes" in legacy
    assert "Corp planet disband: The v3.11 profile turns this on. In this process it is off." in legacy
    assert "stays with its owner" in legacy
    assert "not a v3.11-only switch" in legacy
    assert f"{K.ether_probe_cost():,} credits" in legacy
    assert "No death delay is loaded." in legacy
    assert "Prime Evil" in legacy
    assert "Captain First" not in legacy

    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    live = render("Galaxy War Command")
    assert live != legacy
    assert "Fighters to the C.E.O. when a member leaves: Only the v3.11 profile turns this on. In this process it is on." in live
    assert "move to the C.E.O. when you leave" in live
    assert "Alignment join check: Only the v3.11 profile turns this on. In this process it is on." in live
    assert "opposite signs" in live
    assert "Least-extreme mixed-corp experience: Only the v3.11 profile turns this on. In this process it is on." in live
    assert "smaller of the highest good alignment" in live
    assert "Day roll while a seat holds the turn: Only the v3.11 profile turns this on. In this process it is on." in live
    assert "even while a seat still holds its turn" in live
    assert "Part-by-part trade-in: The v3.11 profile turns this on. In this process it is on." in live
    receipt = K.trade_in_receipt(K.STARTING_SHIP)
    assert f"The total is {receipt['total']:,}" in live
    assert f"{K.part_trade_credit(10_000):,}" in live
    assert "Hungry buy-price anchor: The v3.11 profile turns this on. In this process it is on." in live
    assert "hungry quotes: fuel 38, organics 73, equipment 102" in live
    assert "Experience ranking of every trader: The v3.11 profile turns this on. In this process it is on." in live
    assert "place, name, title, experience, corporation" in live
    assert end_rule_line(10) in live
    assert "most experience" in live
    assert f"{K.ether_probe_cost():,} credits" in live
    assert K.ether_probe_cost() == K.ETHER_PROBE_COST_LIVE
    assert "still faces the quasar" in live
    assert "No death delay is loaded." in live
    assert "Bust-clear interval: The v3.11 profile turns this on. In this process it is on." in live
    assert "No interval is set, so bust records clear every day." in live
    assert "A game can set the interval to 1 or to 7." in live
    assert "Ether probe cap: The v3.11 profile turns this on. In this process it is on." in live
    assert f"stops at {K.PROBE_CHART_MAX} ether probes" in live
    assert "Corp planet disband: The v3.11 profile turns this on. In this process it is on." in live
    assert "planets in the C.E.O.'s sector become the C.E.O.'s" in live
    weekly = render("Galaxy War Command", GameConfig(bust_clear_days=7))
    assert "every 7 days" in weekly
    assert "No interval is set" not in weekly

    monkeypatch.setattr(K, "PHOTON_WAVE_DURATION", 3)
    longer = render("Galaxy War Command")
    assert "mines and fighters until 3 days" in longer
    assert "mines and fighters until the next day" not in longer

    monkeypatch.setattr(K, "CORP_DISBAND_PLANETS", "v306")
    disbanded = render("Galaxy War Command")
    assert "planets in the C.E.O.'s sector become the C.E.O.'s" in disbanded

    monkeypatch.setattr(K, "RANK_MODE", "legacy")
    old_ranks = render("Galaxy War Command")
    assert "Captain First" in old_ranks
    assert "Prime Evil" not in old_ranks


def test_a_games_own_settings_are_the_numbers_on_its_page() -> None:
    cfg = GameConfig(starting_credits_override=43210, turns_per_day=222, turn_regen_day_seconds=600)
    html = render("Galaxy War Command", cfg)
    assert "43,210 credits" in html
    assert "222 turns" in html
    assert "600 seconds" in html
    assert "10 minutes" in html
    assert "These numbers are this game&#x27;s settings." in html


def test_lobby_pages_link_to_the_manual_and_the_page_is_a_route(tmp_path) -> None:
    for html in (disclaimer("Galaxy War Command"), about("Galaxy War Command")):
        assert 'href="/manual"' in html
    from tests._cu_host import LOBBY_FREE_START, free_port
    from tests._port_lock import release_ports

    lobby_port = free_port(LOBBY_FREE_START)
    game_base = free_port(LOBBY_FREE_START, count=10)
    cfg = LobbyConfig(port=lobby_port, game_ports=range(game_base, game_base + 10), root=tmp_path)
    app = create_lobby_app(cfg)
    assert any(getattr(route, "path", None) == "/manual" for route in app.routes)

    async def _get() -> tuple[int, str, int, str]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://lobby") as client:
            manual = await client.get("/manual")
            home = await client.get("/")
        return manual.status_code, manual.text, home.status_code, home.text

    status, body, home_status, home = asyncio.run(_get())
    assert status == 200
    assert "Getting started" in body and "Combat" in body
    assert home_status == 200
    assert 'href="/manual"' in home
    release_ports(lobby_port, *range(game_base, game_base + 10))


def test_a_worker_prefix_rewrites_the_manual() -> None:
    text = rewrite_text("/manual", '<a href="/about">About</a>', base="/g/abc", brand_name="")
    assert 'href="/g/abc/about"' in text


def test_the_manual_is_readable_at_both_widths_and_the_bot_page_has_no_button(tmp_path) -> None:
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    import uvicorn

    port = _free_port()
    app = create_app(auto_start=False)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=lambda: asyncio.run(server.serve()), daemon=True)
    thread.start()
    for _ in range(100):
        try:
            httpx.get(f"http://127.0.0.1:{port}/manual", timeout=0.5)
            break
        except httpx.HTTPError:
            thread.join(0.05)
    else:
        raise RuntimeError("manual server did not start")

    SHOTS.mkdir(parents=True, exist_ok=True)
    base = f"http://127.0.0.1:{port}"
    try:
        manual_page = httpx.get(f"{base}/manual", timeout=5)
        assert manual_page.status_code == 200
        assert 'href="/bot"' in manual_page.text
        bot = httpx.get(f"{base}/bot", timeout=5)
        assert bot.status_code == 200
        assert "manualLink" not in bot.text
        redesign = httpx.get(f"{base}/bot?layout=redesign", timeout=5)
        assert 'id="manualLink"' in redesign.text
        assert 'href="/manual"' in redesign.text

        with sync() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"{base}/bot?layout=redesign")
            with page.expect_popup() as popped:
                page.click("#manualLink")
            opened = popped.value
            opened.wait_for_load_state("domcontentloaded")
            assert "/manual" in opened.url
            assert "Getting started" in opened.inner_text("body")
            opened.close()
            page.close()

            plain = browser.new_context(java_script_enabled=False, viewport={"width": 1280, "height": 800})
            quiet = plain.new_page()
            quiet.goto(f"{base}/manual")
            text = quiet.inner_text("body")
            for title in HEADINGS:
                assert title in text
            sizes = quiet.evaluate(
                """() => [document.body, document.querySelector('p'), document.querySelector('li'), document.querySelector('td')]
                  .filter(Boolean)
                  .map((node) => parseFloat(getComputedStyle(node).fontSize))"""
            )
            assert sizes and min(sizes) >= 16
            quiet.close()
            plain.close()

            for width, tag in ((1280, "1280"), (390, "390")):
                ctx = browser.new_context(viewport={"width": width, "height": 800})
                shot = ctx.new_page()
                shot.goto(f"{base}/manual")
                fits = shot.evaluate(
                    "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
                )
                assert fits, f"horizontal scroll at {width}"
                shot.screenshot(path=str(SHOTS / f"{tag}-top.png"))
                shot.locator("#walkthrough").scroll_into_view_if_needed()
                shot.screenshot(path=str(SHOTS / f"{tag}-walkthrough.png"))
                shot.locator("#combat").scroll_into_view_if_needed()
                shot.screenshot(path=str(SHOTS / f"{tag}-combat.png"))
                shot.close()
                ctx.close()
            browser.close()
    finally:
        server.should_exit = True
        thread.join(5)
