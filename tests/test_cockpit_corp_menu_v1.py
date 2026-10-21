"""Corporate menu on T: members, invites, and the commands the corp actually offers."""

from __future__ import annotations

from pathlib import Path

import pytest

from tw2k.engine.models import Corporation

from tests._cu_host import CuHost

TOK = "corp-token-p2-0000000000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-corp-menu-v1"


def _page(pw, host):
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    return browser, page


def _shoot(page, stem: str, selector: str = "") -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    for width, height, name in ((1920, 1080, "1920"), (390, 844, "390")):
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(150)
        page.evaluate(
            "(sel) => { const el = (sel && document.querySelector(sel)) || document.querySelector('.frm') || document.querySelector('#menu'); if (el) el.scrollIntoView({ block: 'center' }); }",
            selector,
        )
        page.screenshot(path=str(SHOTS / f"{name}-{stem}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


def _action(request) -> dict:
    body = request.post_data_json
    if callable(body):
        body = body()
    return body["action"]


def _menu(page) -> None:
    page.keyboard.press("Escape")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    page.keyboard.press("t")
    page.wait_for_selector("#menu[data-screen='Corporate Menu'] button", timeout=10_000)


def _after_post(page) -> None:
    page.wait_for_function("() => window.__tw2kLeft === true", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)


def _arm(page) -> None:
    page.evaluate(
        """() => {
          window.__tw2kLeft = false;
          const el = document.querySelector('#waitchip');
          const note = () => { if (el.textContent !== 'YOUR MOVE') window.__tw2kLeft = true; };
          const obs = new MutationObserver(note);
          obs.observe(el, { childList: true, characterData: true, subtree: true });
        }"""
    )


def _confirm(page) -> dict:
    _arm(page)
    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=10_000) as caught:
        page.locator("#dangerOk").click()
    _after_post(page)
    return _action(caught.value)


def _form_post(page) -> dict:
    _arm(page)
    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=10_000) as caught:
        page.locator(".frm button.verb", has_text="CONFIRM").click()
    _after_post(page)
    return _action(caught.value)


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    pw = sync().start()
    host = CuHost(tmp_path_factory.mktemp("corp"), TOK)
    host.__enter__()
    universe = host.runner.state.universe
    me = universe.players["P2"]
    me.credits = 50_000
    universe.corporations["ABC"] = Corporation(
        ticker="ABC", name="Aces", ceo_id="P2", member_ids=["P2"], password="harbor",
    )
    me.corp_ticker = "ABC"
    browser, page = _page(pw, host)
    page.keyboard.press(".")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    try:
        yield {"page": page}
    finally:
        browser.close()
        host.__exit__(None, None, None)
        pw.stop()


def test_menu_shows_ticker_members_and_their_credits(world) -> None:
    page = world["page"]
    _menu(page)
    text = page.locator("#menu").inner_text()
    assert "ABC" in text and "Aces" in text
    row = page.locator("[data-member=P2]").inner_text()
    assert "Commander" in row and "C.E.O." in row and "50,000" in row
    assert "50,000" in page.locator("[data-corp=credits]").inner_text()
    _shoot(page, "menu", "#menu")


def test_invite_posts_the_other_trader(world) -> None:
    page = world["page"]
    _menu(page)
    page.get_by_role("button", name="Invite", exact=True).click()
    page.wait_for_selector("#commanderPick", timeout=10_000)
    assert "HBot" in page.locator("#menu").inner_text()
    _shoot(page, "invite", "#menu")
    page.locator("#dangerOk").click()
    action = _confirm(page)
    assert action["kind"] == "corp_invite"
    assert action["args"]["target"] == "P1"


def test_join_stays_grey_with_the_reason(world) -> None:
    page = world["page"]
    _menu(page)
    page.get_by_role("button", name="Join", exact=True).click()
    assert "already in a corporation" in page.locator("#lastResult").inner_text()


def test_memo_posts_the_message(world) -> None:
    page = world["page"]
    _menu(page)
    page.get_by_role("button", name="Memo", exact=True).click()
    page.wait_for_selector(".frm [data-n=message]", timeout=10_000)
    page.locator(".frm [data-n=message]").fill("Meet at Terra")
    _shoot(page, "memo")
    action = _form_post(page)
    assert action["kind"] == "corp_memo"
    assert action["args"]["message"] == "Meet at Terra"


def test_deposit_and_withdraw_say_why_while_the_treasury_is_off(world) -> None:
    page = world["page"]
    _menu(page)
    page.get_by_role("button", name="Deposit credits", exact=True).click()
    assert "unsupported" in page.locator("#lastResult").inner_text().lower()
    page.get_by_role("button", name="Withdraw credits", exact=True).click()
    assert "unsupported" in page.locator("#lastResult").inner_text().lower()


def test_set_password_posts_the_word(world) -> None:
    page = world["page"]
    _menu(page)
    page.get_by_role("button", name="Set password", exact=True).click()
    page.wait_for_selector(".frm [data-n=password]", timeout=10_000)
    page.locator(".frm [data-n=password]").fill("harbor")
    _shoot(page, "password")
    action = _form_post(page)
    assert action["kind"] == "corp_set_password"
    assert action["args"]["password"] == "harbor"


def test_drop_stays_grey_when_you_are_the_only_member(world) -> None:
    page = world["page"]
    _menu(page)
    page.get_by_role("button", name="Drop member", exact=True).click()
    assert "no member to drop" in page.locator("#lastResult").inner_text()


def test_transfer_ceo_says_it_is_not_in_this_game(world) -> None:
    page = world["page"]
    _menu(page)
    page.get_by_role("button", name="Transfer C.E.O.", exact=True).click()
    assert "not in this game" in page.locator("#lastResult").inner_text()


def test_ship_can_be_made_corporate_and_personal_says_why(world) -> None:
    page = world["page"]
    _menu(page)
    page.get_by_role("button", name="Make ship personal", exact=True).click()
    assert "already personal" in page.locator("#lastResult").inner_text()
    _arm(page)
    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=10_000) as caught:
        page.get_by_role("button", name="Make ship corporate", exact=True).click()
    _after_post(page)
    action = _action(caught.value)
    assert action["kind"] == "ship_set_corporate"


def test_alliances_propose_and_the_others_say_why(world) -> None:
    page = world["page"]
    _menu(page)
    page.get_by_role("button", name="Accept alliance", exact=True).click()
    assert "no alliance proposal" in page.locator("#lastResult").inner_text()
    page.get_by_role("button", name="Break alliance", exact=True).click()
    assert "no alliance" in page.locator("#lastResult").inner_text()
    page.get_by_role("button", name="Propose alliance", exact=True).click()
    page.wait_for_selector("#commanderPick", timeout=10_000)
    assert "HBot" in page.locator("#menu").inner_text()
    page.locator("#dangerOk").click()
    action = _confirm(page)
    assert action["kind"] == "propose_alliance"
    assert action["args"]["target"] == "P1"


def test_leave_warns_that_the_corporation_dissolves(world) -> None:
    page = world["page"]
    _menu(page)
    page.get_by_role("button", name="Leave", exact=True).click()
    page.wait_for_selector("#dangerOk", timeout=10_000)
    assert "dissolves" in page.locator("#menu").inner_text()
    _shoot(page, "leave", "#menu")
    action = _confirm(page)
    assert action["kind"] == "corp_leave"
