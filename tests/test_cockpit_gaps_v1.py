"""NOTE 56 cockpit-gaps-v1: each test closes one row of cockpit-ai-seat-v2/gaps.md.

The cockpit block rides on the harness observation behind COCKPIT_FIELDS_MODE
(legacy by default) and is drawn by the redesign cockpit only. The browser
tests share one page and run in file order; screens go to
docs/playtests/cockpit-gaps-v1/ at 1920 and 390.
"""

from __future__ import annotations

import asyncio
import math
from pathlib import Path

import httpx

import tw2k.agents.cockpit_seat as seat
import tw2k.engine.constants as K
from tests._cu_host import CuHost
from tests.test_cockpit_ai_seat_v2 import seat_spec
from tests.test_external_harness_phase1 import TOK2, _app_and_client, _auth, _http_spec, _wait_until
from tw2k.engine.models import Commodity, PortClass

TOK = "gaps-v1-token-p2-000000000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-gaps-v1"
ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- legacy switch


def test_legacy_switch_keeps_the_observation_and_reference(tmp_path) -> None:
    """Item 8: with COCKPIT_FIELDS_MODE legacy the observation and Rules and Help are unchanged."""
    assert K.COCKPIT_FIELDS_MODE == "legacy"
    assert K.cockpit_fields_on() is False
    app, http = _app_and_client(tmp_path)
    runner = app.state.runner

    async def _go() -> None:
        await runner.start(_http_spec())
        assert await _wait_until(lambda: runner.state.universe is not None
                                 and any(a.player_id == "P2" for a in runner.state.agents))
        try:
            body = (await http.get("/harness/v1/P2/observation", params={"wait_s": 5},
                                   headers=_auth(TOK2))).json()
            assert "cockpit" not in body
            ref = (await http.get("/harness/v1/P2/reference", headers=_auth(TOK2))).json()
            assert "not_in_original" not in [row.get("id") for row in ref.get("sections") or []]
            r = await http.post("/harness/v1/P2/action", headers=_auth(TOK2), json={
                "turn_seq": body["turn_seq"], "action": {"kind": "wait", "args": {}}})
            assert r.status_code == 200, r.text
            agent = next(a for a in runner.state.agents if a.player_id == "P2")
            assert await _wait_until(
                lambda: int((agent.last_result or {}).get("turn_seq") or -1) >= int(body["turn_seq"]), tries=300)
            assert agent.cockpit_verdict is None
            assert agent.cockpit_port_notes == {}
            again = (await http.get("/harness/v1/P2/observation", params={"wait_s": 0, "peek": 1},
                                    headers=_auth(TOK2))).json()
            assert "cockpit" not in again
        finally:
            await runner.stop()
            await http.aclose()

    asyncio.run(_go())


# ---------------------------------------------------------------- seat (items 6, 7a, 7b)


def test_seat_reads_the_fields_and_counts_days_from_now(tmp_path, monkeypatch) -> None:
    """Items 6, 7a and 7b.

    The seat reads the verdict, the port notes and the hold quote in place of its guesses.
    --days counts from the day it starts: a second run with days=1 joins on day 2 and plays
    day 2. The day-1 row ends after its last result, so it meets the day-2 start.
    Original screens: transcript.txt 2432-2433 (the verdict line), 1141-1150 (Computer R),
    4174 and 4183-4188 (the StarDock hold price and total).
    """
    monkeypatch.setattr(K, "AI_COCKPIT_SEAT_MODE", "tw2002")
    monkeypatch.setattr(K, "PORT_STOCK_FIDELITY_MODE", "live")
    monkeypatch.setattr(K, "HAGGLE_LIVE_MODE", "live")
    monkeypatch.setattr(K, "COCKPIT_FIELDS_MODE", "tw2002")
    from tw2k.server.app import create_app

    app = create_app(auto_start=False)
    app.state.runner._saves_root = tmp_path / "saves"
    runner = app.state.runner
    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 5555))
    http = httpx.AsyncClient(transport=transport, base_url="http://harness.test", timeout=60.0)

    async def _go() -> tuple[dict, dict]:
        await runner.start(seat_spec(2))
        assert await _wait_until(lambda: runner.state.universe is not None)
        try:
            first = await seat.run_http(http, "P2", TOK2, 1, idle_s=120)
            second = await seat.run_http(http, "P2", TOK2, 1, idle_s=120)
            return first, second
        finally:
            await runner.stop()
            await http.aclose()

    first, second = asyncio.run(_go())
    assert (first["start_day"], first["end_day"]) == (1, 1)
    assert [row["day"] for row in first["days"]] == [1]
    assert (second["start_day"], second["end_day"]) == (2, 2)
    assert [row["day"] for row in second["days"]] == [2]
    assert second["posts"] > 0
    for report in (first, second):
        assert report["cockpit_fields"] is True
        assert report["refused"] == []
        assert report["day_end_source"] == "verdict after the last result"
        rows = {row["id"]: row for row in report["gaps"]}
        for gid in ("result_line", "counter_in_log", "price_away", "hold_curve"):
            assert rows[gid]["count"] == 0, (gid, rows[gid])
            assert rows[gid]["status"] == "closed"
        for gid in ("haggle_band", "price_rule"):
            assert rows[gid]["status"] == "not in original"
    assert first["days"][0]["credits_end"] == second["days"][0]["credits_start"]
    assert first["days"][0]["net_worth_end"] == second["days"][0]["net_worth_start"]
    assert second["days"][-1]["net_worth_end"] > first["days"][0]["net_worth_start"]


def test_runner_script_exits_nonzero_on_zero_posts(tmp_path, monkeypatch, capsys) -> None:
    """Item 7a: a run that made 0 posts says why and exits non-zero."""
    import importlib.util

    monkeypatch.setattr(K, "AI_COCKPIT_SEAT_MODE", "legacy")
    monkeypatch.setenv("AI_COCKPIT_SEAT_MODE", "tw2002")
    spec = importlib.util.spec_from_file_location("run_cockpit_seat_t", ROOT / "scripts" / "run_cockpit_seat.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    async def _none(*_a, **_k):
        return {"posts": 0, "days": [], "refused": [], "start_day": 11, "end_day": 11}

    monkeypatch.setattr(seat, "run_http", _none)
    tokens = tmp_path / "tokens.json"
    tokens.write_text('{"P2": "unused-test-token"}', encoding="utf-8")
    code = mod.main(["--base-url", "http://127.0.0.1:9", "--seat", "P2", "--tokens-file", str(tokens), "--days", "1"])
    err = capsys.readouterr().err
    assert code == 3
    assert "the seat made 0 posts: started on day 11" in err
    assert "unused-test-token" not in err


def test_stock_rule_is_marked_not_in_original() -> None:
    """Item 4: no original screen prints a stock-to-price rule, so no hint is added.

    REPORT2.md line 32 ("Prices fall as the port fills") is observed play; the S3 bible
    around lines 3150-3188 says it only in prose. The gaps.md row says not in original.
    """
    status, where = seat.GAP_FIELDS["price_rule"]
    assert status == "not in original"
    assert "REPORT2.md line 32" in where
    from tw2k.server import reference

    section = reference._not_in_original()
    assert section["id"] == "not_in_original"
    assert section["title"] == "Not shown in the original"
    assert "REPORT2.md line 32" in section["source"]


# ---------------------------------------------------------------- browser


def _page(pw, host):
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    return browser, page


def _shoot(page, stem: str, focus: str | None = None) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    for width, height, name in ((1920, 1080, "1920"), (390, 844, "390")):
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(150)
        if focus and page.locator(focus).count():
            page.locator(focus).first.scroll_into_view_if_needed()
            page.wait_for_timeout(80)
        page.screenshot(path=str(SHOTS / f"{name}-{stem}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


def _your_move(page) -> None:
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=30_000)


def _next(page, host, mutate=None) -> None:
    """Post one Wait, apply ``mutate`` while it runs, and come back to YOUR MOVE."""
    host.runner._wait_streak = {"P2": 0}
    page.keyboard.press("Escape")
    page.evaluate("() => { if (window.__tw2kTest) window.__tw2kTest.resetWaits(); }")
    page.keyboard.press(".")
    menu = page.locator("#menu")
    if menu.count() and menu.is_visible() and "ends your day" in (menu.inner_text() or ""):
        page.keyboard.press("Escape")
        host.runner._wait_streak = {"P2": 0}
        page.evaluate("() => window.__tw2kTest.resetWaits()")
        page.keyboard.press(".")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
    if mutate:
        mutate()
    _your_move(page)


def _signed_in(page, host) -> None:
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
    page.wait_for_function("() => document.querySelector('#sbDay').textContent !== '-'", timeout=20_000)
    _your_move(page)


def _verdict(page, test: str) -> str:
    page.wait_for_function(
        "() => { const v = document.querySelector('#verdict'); return !!v && !v.hidden && (" + test + "); }",
        timeout=30_000,
    )
    return page.locator("#verdict").inner_text()


def _sit(universe, pid: str, sector_id: int) -> None:
    player = universe.players[pid]
    origin = universe.sectors[player.sector_id]
    if pid in origin.occupant_ids:
        origin.occupant_ids.remove(pid)
    player.sector_id = int(sector_id)
    player.planet_landed = None
    dest = universe.sectors[player.sector_id]
    if pid not in dest.occupant_ids:
        dest.occupant_ids.append(pid)


def _trade_form(page, side: str, commodity: str, qty: int) -> None:
    # The cockpit re-reads its observation every few seconds; a hold changed between reads
    # shows on the next one, so press P again until the trade is legal on the page.
    for _ in range(20):
        page.keyboard.press("Escape")
        page.keyboard.press("P")
        try:
            page.wait_for_selector("#formSlot [data-n=side]", timeout=1_000)
            break
        except Exception:
            continue
    else:
        raise AssertionError("trade form did not open: " + page.locator("#lastResult").inner_text())
    page.select_option("#formSlot [data-n=side]", side)
    page.select_option("#formSlot [data-n=commodity]", commodity)
    page.fill("#formSlot [data-n=qty]", str(qty))


def _install():
    import pytest

    @pytest.fixture(scope="module")
    def world(tmp_path_factory):
        sync = pytest.importorskip("playwright.sync_api").sync_playwright
        saved = (K.COCKPIT_FIELDS_MODE, K.HAGGLE_LIVE_MODE)
        K.COCKPIT_FIELDS_MODE, K.HAGGLE_LIVE_MODE = "tw2002", "live"
        pw = sync().start()
        host = CuHost(tmp_path_factory.mktemp("gaps"), TOK, max_days=3, turns_per_day=80)
        host.__enter__()
        browser, page = _page(pw, host)
        try:
            yield {"page": page, "universe": host.runner.state.universe, "host": host}
        finally:
            browser.close()
            host.__exit__(None, None, None)
            pw.stop()
            K.COCKPIT_FIELDS_MODE, K.HAGGLE_LIVE_MODE = saved

    return world


world = _install()


def test_verdict_is_its_own_field_and_survives_a_reload(world):
    """Item 1. Original: the outcome prints right after the command, e.g. "You have 2,177
    credits and 20 empty cargo holds." and "We'll buy them for 664 credits." then the deal
    (transcript.txt 2432-2433, 2454, 2470, 9241). The cockpit keeps it in #verdict."""
    page, host = world["page"], world["host"]
    _next(page, host)
    obs = httpx.get(f"{host.base}/harness/v1/P2/observation", params={"wait_s": 0, "peek": 1},
                    headers=_auth(TOK), timeout=10).json()
    turn = int(obs["turn_seq"])
    r = httpx.post(f"{host.base}/harness/v1/P2/action", headers=_auth(TOK), timeout=10, json={
        "turn_seq": turn,
        "action": {"kind": "buy_equip", "args": {"item": "fighters", "qty": 100_000}}})
    assert r.status_code == 200, r.text
    text = _verdict(page, "v.dataset.ok === 'false' && Number(v.dataset.turn) >= " + str(turn))
    assert text.startswith("Last action: ")
    assert "REFUSED" in text and "0 turns spent" in text and "Credits +0." in text
    _your_move(page)
    _signed_in(page, host)
    again = _verdict(page, "v.dataset.ok === 'false'")
    assert again == text
    _shoot(page, "verdict", "#verdict")


def test_trade_form_quotes_counters_and_says_how_the_haggle_ended(world):
    """Item 2. Original (transcript.txt 2456-2470): "We'll sell them for 317 credits.", your
    offer, "We'll sell them for 309 credits.", ..., "Very well, we'll take that offer." A
    failed haggle ends the trade (REPORT2.md lines 20 and 25-31). No accept band is shown."""
    page, host, universe = world["page"], world["host"], world["universe"]
    me = universe.players["P2"]
    port = universe.sectors[me.sector_id].port
    assert port is not None and (port.code or "").startswith("B")  # the port buys fuel ore

    _next(page, host, lambda: me.ship.cargo.__setitem__(Commodity.FUEL_ORE, 20))
    _trade_form(page, "sell", "fuel_ore", 10)
    hint = page.locator("#formSlot").inner_text()
    listed = int(page.locator("#formSlot [data-n=unit_price]").input_value())
    quote = page.locator("#formSlot [data-haggle=quote]").inner_text()
    assert quote == f"We'll buy them for {listed * 10:,} credits (10 at {listed:,} cr)."
    assert "%" not in hint and "band" not in hint.lower()

    ask = max(listed + 1, math.floor(listed * 1.08))
    assert listed * 1.03 < ask <= listed * 1.12
    page.fill("#formSlot [data-n=unit_price]", str(ask))
    page.locator("#formSlot button", has_text="CONFIRM").click()
    _verdict(page, "v.dataset.ok === 'false' && v.textContent.includes('countered')")
    _your_move(page)
    if not page.locator("#formSlot [data-haggle=counter]").count():
        _trade_form(page, "sell", "fuel_ore", 10)
    counter = page.locator("#formSlot [data-haggle=counter]")
    counter.wait_for(state="visible", timeout=10_000)
    pending = me.haggle_counter
    assert pending and int(pending["counter"]) > 0
    offer = int(pending["counter"])
    assert counter.inner_text() == f"Counter: we'll buy them for {offer * 10:,} credits ({offer:,} cr each). Your offer [{offer:,}]"
    assert page.locator("#formSlot [data-n=unit_price]").input_value() == str(offer)
    ended = page.locator("#formSlot [data-haggle=ended]")
    assert ended.get_attribute("data-outcome") == "countered"
    _shoot(page, "counter", "#formSlot")

    page.locator("#formSlot button", has_text="CONFIRM").click()
    text = _verdict(page, "v.dataset.ok === 'true' && v.dataset.kind === 'trade'")
    assert "OK" in text and "Credits +" in text
    _your_move(page)

    _trade_form(page, "sell", "fuel_ore", 10)  # 10 of the 20 are still on board
    took = page.locator("#formSlot [data-haggle=ended]")
    assert took.get_attribute("data-outcome") == "taken"
    assert "the port took your offer, 10 Fuel Ore for " + f"{offer * 10:,} credits" in took.inner_text()
    listed = int(page.locator("#formSlot [data-n=unit_price]").input_value())
    page.fill("#formSlot [data-n=unit_price]", str(listed * 3))
    page.locator("#formSlot button", has_text="CONFIRM").click()
    text = _verdict(page, "v.dataset.ok === 'false' && v.dataset.kind === 'trade' && !v.textContent.includes('countered')")
    assert "REFUSED" in text
    _your_move(page)
    verdict = httpx.get(f"{host.base}/harness/v1/P2/observation", params={"wait_s": 0, "peek": 1},
                        headers=_auth(TOK), timeout=10).json()["cockpit"]["verdict"]
    assert verdict["haggle"]["outcome"] == "ended"
    _shoot(page, "ended", "#verdict")


def test_port_report_keeps_the_original_columns_and_adds_last_seen(world):
    """Item 3. Original Computer R (transcript.txt 1141-1150, header at 2441): class, then
    each product's status, amount and % of max. The cockpit adds this player's own last-seen
    price with the day, only for ports it docked at."""
    page, host, universe = world["page"], world["host"], world["universe"]
    me = universe.players["P2"]
    me.known_ports[8801] = {
        "class": "BSS",
        "last_seen_day": 1,
        "stock": {"fuel_ore": {"current": 50, "max": 100, "price": 0, "side": "buys_from_player"}},
    }
    _next(page, host)
    head = page.locator("#here .porttbl").first.inner_text()
    assert "% of max" in head
    page.keyboard.press("Escape")
    page.keyboard.press("C")
    page.keyboard.press("R")
    page.wait_for_selector("[data-port=report]", timeout=10_000)
    here = page.locator(f"[data-port=report][data-sector='{me.sector_id}']").inner_text()
    assert "% of max" in here
    assert "when you docked" in here
    far = page.locator("[data-port=report][data-sector='8801']").inner_text()
    assert "50% of max" in far
    assert "no price: not docked here" in far
    assert "when you docked" not in far
    _shoot(page, "ports")
    page.keyboard.press("Escape")


def test_rules_and_help_list_the_stock_rule_as_not_shown(world):
    """Item 4. No original screen prints the stock-to-price rule (REPORT2.md line 32), so
    Rules and Help says so and adds no price hint."""
    page = world["page"]
    page.keyboard.press("Escape")
    page.keyboard.press("Z")
    page.wait_for_function(
        "() => (document.querySelector('#menu') || {}).textContent && document.querySelector('#menu').textContent.includes('Not shown in the original')",
        timeout=15_000,
    )
    text = page.locator("#menu").inner_text()
    assert "How a port's stock moves its prices is not printed on any screen of the original game" in text
    _shoot(page, "rules")
    page.keyboard.press("Escape")


def test_stardock_holds_show_the_price_count_and_total(world):
    """Item 5. Original StarDock (transcript.txt 4174): "550 credits / next hold  14", then the
    amount and the total before you confirm (4183-4188). Prices come from the engine rule."""
    page, host, universe = world["page"], world["host"], world["universe"]
    me = universe.players["P2"]
    dock = next(s for s in universe.sectors.values() if s.port and s.port.class_id == PortClass.STARDOCK)
    _next(page, host, lambda: _sit(universe, "P2", dock.id))
    page.keyboard.press("Escape")
    page.locator("#here button", has_text="StarDock: buy gear").click()
    page.wait_for_selector("#formSlot [data-n=item]", timeout=10_000)
    page.select_option("#formSlot [data-n=item]", "holds")
    page.fill("#formSlot [data-n=qty]", "5")
    line = page.locator("[data-gear=hold-total]")
    line.wait_for(state="visible", timeout=10_000)
    cls = me.ship.ship_class.value if hasattr(me.ship.ship_class, "value") else str(me.ship.ship_class)
    day = int(universe.day)
    holds = int(me.ship.holds)
    price = K.hold_next_price(cls, holds, day)
    total = K.hold_total_price(cls, holds, 5, day)
    text = line.inner_text()
    assert f"Cargo holds: {price:,} credits / next hold." in text
    assert f"The cost for 5 more holds is {total:,} credits." in text
    _shoot(page, "holds", "[data-gear=hold-total]")
    page.keyboard.press("Escape")


def test_header_shows_the_last_day_after_game_over(world):
    """Item 7c. After the last day the header reads the last day and GAME OVER, never DAY 4/3."""
    page, host, universe = world["page"], world["host"], world["universe"]
    last = int(universe.config.max_days)
    host.runner._wait_streak = {"P2": 0}
    page.keyboard.press("Escape")
    page.evaluate("() => { if (window.__tw2kTest) window.__tw2kTest.resetWaits(); }")
    page.keyboard.press(".")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
    # The next observation is the one after the last day: day 4 of 3, then the match ends.
    universe.day = last + 1
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'GAME OVER'", timeout=30_000)
    assert page.locator("#sbDay").inner_text() == str(last)
    universe.finished = True
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'GAME OVER'", timeout=30_000)
    assert page.locator("#sbDay").inner_text() == str(last)
    assert page.locator("#maxDays").inner_text() == str(last)
    _shoot(page, "gameover", "#waitchip")
