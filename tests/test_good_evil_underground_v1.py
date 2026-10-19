"""NOTE 91. Underground name change, and a per-game tournament lockout that stays off."""

from __future__ import annotations

import time

import pytest
from pydantic import ValidationError

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.combat import _destroy_ship_tw2002
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import EventKind, Player, Ship
from tw2k.engine.tavern import password_for
from tw2k.public import pages
from tw2k.public import security as S
from tw2k.public import workers as WM


def _world(**cfg):
    base = dict(seed=91, universe_size=20, max_days=6, enable_planets=False, enable_ferrengi=False)
    base.update(cfg)
    return generate_universe(GameConfig(**base))


def _seat(universe, pid="A", name="Ada", *, credits=100_000, alignment=100):
    player = Player(
        id=pid, name=name, ship=Ship(), credits=credits, alignment=alignment,
        experience=80, sector_id=int(K.STARDOCK_SECTOR),
    )
    universe.players[pid] = player
    universe.sectors[int(K.STARDOCK_SECTOR)].occupant_ids.append(pid)
    return player


def _kinds(universe, pid="A"):
    return {row.kind: row for row in legal_actions(universe, pid)}


def _enter(universe, pid="A"):
    word = password_for(int(universe.config.seed))
    universe.players[pid].ug_password_known = True
    assert apply_action(universe, pid, Action(kind=ActionKind.UNDERGROUND_ENTER, args={"password": word})).ok


def test_name_change_stays_off_with_the_stored_flag():
    assert K.UNDERGROUND_MODE == "legacy"
    assert K.UG_NAME_CHANGE is False
    assert K.underground_mafia_live() is False
    universe = _world()
    _seat(universe)
    assert "underground_rename" not in _kinds(universe)
    refused = apply_action(universe, "A", Action(kind=ActionKind.UNDERGROUND_RENAME, args={"name": "Shadow"}))
    assert not refused.ok
    assert universe.players["A"].name == "Ada"


def test_name_change_charges_the_live_screen_price(monkeypatch):
    monkeypatch.setattr(K, "UNDERGROUND_MODE", "live")
    universe = _world()
    player = _seat(universe)
    assert _kinds(universe)["underground_rename"].legal is False
    _enter(universe)
    row = _kinds(universe)["underground_rename"]
    assert row.legal is True
    assert row.params["price"] == 247
    before = player.alignment
    assert apply_action(universe, "A", Action(kind=ActionKind.UNDERGROUND_RENAME, args={"name": "Shadow"})).ok
    assert player.name == "Shadow"
    assert player.credits == 100_000 - 247
    assert player.alignment == before
    assert universe.events[-1].kind is EventKind.UG_RENAME
    assert universe.events[-1].payload["price"] == 247
    short = _seat(universe, "B", "Bea", credits=100)
    short.ug_entered_day = int(universe.day)
    assert _kinds(universe, "B")["underground_rename"].legal is False
    refused = apply_action(
        universe, "B", Action(kind=ActionKind.UNDERGROUND_RENAME, args={"name": "Other"}),
    )
    assert not refused.ok
    assert short.name == "Bea"


def test_name_change_refuses_a_bad_or_unchanged_name(monkeypatch):
    monkeypatch.setattr(K, "UNDERGROUND_MODE", "live")
    universe = _world()
    player = _seat(universe)
    _enter(universe)
    for bad in ("", "   ", "x" * 31, "line\nbreak", "Ada"):
        assert not apply_action(
            universe, "A", Action(kind=ActionKind.UNDERGROUND_RENAME, args={"name": bad}),
        ).ok
    assert player.name == "Ada"
    assert player.credits == 100_000


def test_rename_is_absent_for_a_destroyed_trader_until_the_switch_is_on(monkeypatch):
    universe = _world()
    player = _seat(universe)
    player.alive = False
    assert "underground_rename" not in _kinds(universe)
    monkeypatch.setattr(K, "UNDERGROUND_MODE", "live")
    row = _kinds(universe)["underground_rename"]
    assert row.legal is False


def test_tournament_off_does_not_remove_anyone():
    assert K.PODS_PER_DAY == 2
    assert K.DEATH_DELAY_MODE == "legacy"
    universe = _world()
    player = _seat(universe)
    for _ in range(3):
        _destroy_ship_tw2002(universe, "A", "mines", None, False, force_destroyed=True)
    assert player.alive
    assert player.tournament_blows == 0
    assert "tournament_blows" not in player.model_dump()
    assert "tournament_lockout" not in GameConfig().model_dump()
    assert "tournament_kill_threshold" not in GameConfig(tournament_lockout="none").model_dump()


def test_deaths_only_ignores_a_pod_and_pods_and_deaths_counts_it():
    universe = _world(tournament_lockout="deaths", tournament_kill_threshold=1)
    player = _seat(universe)
    _destroy_ship_tw2002(universe, "A", "mines", None, False, force_destroyed=False)
    assert player.alive and player.tournament_blows == 0
    _destroy_ship_tw2002(universe, "A", "mines", None, False, force_destroyed=True)
    assert not player.alive and player.tournament_blows == 1

    both = _world(tournament_lockout="pods_and_deaths", tournament_kill_threshold=1)
    other = _seat(both, "C", "Cy")
    _destroy_ship_tw2002(both, "C", "mines", None, False, force_destroyed=False)
    assert not other.alive and other.tournament_blows == 1


def test_deaths_only_removes_on_the_threshold():
    universe = _world(tournament_lockout="Deaths only", tournament_kill_threshold=2)
    player = _seat(universe)
    _destroy_ship_tw2002(universe, "A", "mines", None, False, force_destroyed=False)
    _destroy_ship_tw2002(universe, "A", "mines", None, False, force_destroyed=True)
    assert player.alive and player.tournament_blows == 1
    _destroy_ship_tw2002(universe, "A", "mines", None, False, force_destroyed=True)
    assert not player.alive and player.tournament_blows == 2


def test_tournament_threshold_is_bounded():
    with pytest.raises(ValidationError):
        GameConfig(tournament_lockout="sideways")
    with pytest.raises(ValidationError):
        GameConfig(tournament_kill_threshold=0)
    kept = GameConfig(tournament_lockout="deaths", tournament_kill_threshold=2)
    assert kept.model_dump()["tournament_lockout"] == "deaths"
    assert kept.model_dump()["tournament_kill_threshold"] == 2


def test_the_lobby_form_leaves_tournament_off(tmp_path):
    blank = S.parse_game_form({"name": "Alpha"})
    assert blank.tournament_lockout is None
    assert blank.tournament_kill_threshold is None
    assert "tournament_lockout" not in blank.settings()
    assert "--tournament-lockout" not in WM.serve_command(blank.settings(), 8052, tmp_path)
    off = S.parse_game_form({"name": "Alpha", "tournament_lockout": "none", "tournament_kill_threshold": ""})
    assert off.tournament_lockout is None
    chosen = S.parse_game_form({
        "name": "Alpha", "tournament_lockout": "pods_and_deaths", "tournament_kill_threshold": "3",
    })
    assert chosen.settings()["tournament_lockout"] == "pods_and_deaths"
    assert chosen.settings()["tournament_kill_threshold"] == 3
    cmd = WM.serve_command(chosen.settings(), 8052, tmp_path)
    assert cmd[cmd.index("--tournament-lockout") + 1] == "pods_and_deaths"
    assert cmd[cmd.index("--tournament-kill-threshold") + 1] == "3"
    with pytest.raises(S.FormError):
        S.parse_game_form({"name": "Alpha", "tournament_lockout": "deaths", "tournament_kill_threshold": ""})
    html = pages.new_game("TW")
    assert 'name="tournament_lockout"' in html
    assert 'name="tournament_kill_threshold"' in html


def _safe_port(start: int = 8050) -> int:
    import socket

    for port in (8050, 8051, 8052, 8053, 8054, 8058, 8059):
        if port < start:
            continue
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("no safe cockpit port")


def test_redesign_change_name_submits(monkeypatch, tmp_path_factory):
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright

    import tests._cu_host as cu

    monkeypatch.setattr(cu, "free_port", _safe_port)
    token = "note91-rename-token-p2-000000000000"
    host = cu.CuHost(tmp_path_factory.mktemp("note91"), token, seed=9101)
    host.__enter__()
    try:
        assert host.port in (8050, 8051, 8052, 8053, 8054, 8058, 8059)
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch(headless=True)
            except Exception as exc:
                pytest.skip(f"chromium is not installed: {exc}")
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={token}")
            page.wait_for_selector("#waitchip", timeout=20_000)
            _at_underground(host)
            page.evaluate("() => window.__tw2kTest && window.__tw2kTest.setAwaiting(true)")
            page.wait_for_timeout(500)
            assert page.locator("#here button[data-kind=underground_rename]").count() == 0
            monkeypatch.setattr(K, "UNDERGROUND_MODE", "live")
            _at_underground(host)
            page.evaluate("() => window.__tw2kTest && window.__tw2kTest.setAwaiting(true)")
            page.wait_for_selector("#here button[data-kind=underground_rename]", timeout=10_000)
            _wait_turn(host)
            _submit_name(page, "Shadow")
            _wait_name(host, page, "Shadow")
            assert host.runner.state.universe.players["P2"].credits == 5_000 - 247
            page.set_viewport_size({"width": 390, "height": 844})
            page.reload()
            page.wait_for_selector("#waitchip", timeout=20_000)
            _wait_turn(host)
            time.sleep(2.5)
            page.evaluate("() => window.__tw2kTest && window.__tw2kTest.setAwaiting(true)")
            page.wait_for_selector("#here button[data-kind=underground_rename]", timeout=10_000)
            _submit_name(page, "Shade")
            _wait_name(host, page, "Shade")
            assert host.runner.state.universe.players["P2"].credits == 5_000 - 247 - 247
            browser.close()
    finally:
        host.__exit__(None, None, None)


def _at_underground(host) -> None:
    from tw2k.engine.observation import build_observation

    universe = host.runner.state.universe
    player = universe.players["P2"]
    old = player.sector_id
    if player.id in universe.sectors[old].occupant_ids:
        universe.sectors[old].occupant_ids.remove(player.id)
    player.sector_id = int(K.STARDOCK_SECTOR)
    player.planet_landed = None
    if player.id not in universe.sectors[player.sector_id].occupant_ids:
        universe.sectors[player.sector_id].occupant_ids.append(player.id)
    player.alignment = 40
    player.credits = 5_000
    player.ug_password_known = True
    player.ug_entered_day = int(universe.day)
    agent = next(row for row in host.runner.state.agents if row.player_id == "P2")
    agent.current_observation = build_observation(universe, "P2")


def _wait_turn(host) -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        agent = next(row for row in host.runner.state.agents if row.player_id == "P2")
        if getattr(agent, "awaiting_input", False):
            return
        time.sleep(0.1)
    raise AssertionError("P2 did not get the turn")


def _submit_name(page, name: str) -> None:
    page.locator("#here button[data-kind=underground_rename]").click()
    page.wait_for_selector("#formSlot input", timeout=10_000)
    assert "247" in page.locator("#formSlot").inner_text()
    page.locator("#formSlot input").fill(name)
    page.evaluate("() => window.__tw2kTest && window.__tw2kTest.setAwaiting(true)")
    page.locator("#formSlot button", has_text="CONFIRM").click()


def _wait_name(host, page, name: str) -> None:
    deadline = time.time() + 10
    while time.time() < deadline:
        if host.runner.state.universe.players["P2"].name == name:
            return
        time.sleep(0.1)
    shown = page.locator("#lastResult").inner_text()
    raise AssertionError(f"name stayed {host.runner.state.universe.players['P2'].name}; result {shown!r}")
