"""COMMANDER NOTE 66: the home planet is yours, and it is not Terra.

The v3.11 start puts a class M world in an empty sector outside FedSpace and
lands the new trader on it. Colonists start as 45 / 65 / 81 thousand.
"""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.engine import GameConfig, build_observation, generate_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import Commodity, Planet, PlanetClass, Player
from tw2k.engine.planets import daily_production
from tw2k.engine.runner import _bfs_path, apply_action, grant_starting_planet
from tw2k.public import pages
from tw2k.public import security as S
from tw2k.public import workers as WM
from tw2k.public.security import FormError

REPO = Path(__file__).resolve().parents[1]
SHOTS = REPO / "docs" / "playtests" / "terra-and-planet-ownership-v1"
OWN = "planet not owned by you or your corp"
VERBS = (
    (ActionKind.ASSIGN_COLONISTS, {"from": "fuel_ore", "to": "equipment", "qty": 1}),
    (ActionKind.LOAD_PLANET_CARGO, {"commodity": "colonists", "pool": "fuel_ore", "qty": 1}),
    (ActionKind.DUMP_PLANET_CARGO, {"commodity": "colonists", "pool": "fuel_ore", "qty": 1}),
    (ActionKind.BUILD_CITADEL, {}),
    (ActionKind.DEPOSIT_TREASURY, {"amount": 1}),
    (ActionKind.WITHDRAW_TREASURY, {"amount": 1}),
    (ActionKind.SET_MILITARY_REACTION, {"pct": 10}),
    (ActionKind.DEPOSIT_PLANET_DEFENSE, {"kind": "fighters", "qty": 1}),
    (ActionKind.WITHDRAW_PLANET_DEFENSE, {"kind": "fighters", "qty": 1}),
)
TERRA_VERBS = VERBS + (
    (ActionKind.PLANET_DESTROY, {}),
    (ActionKind.CLAIM_PLANET, {}),
)


def _universe(seed: int = 66, *, planets: bool = True, name: str | None = None):
    cfg = GameConfig(
        seed=seed, universe_size=200, max_days=3, turns_per_day=250,
        starting_credits=20_000, enable_ferrengi=False, enable_planets=planets,
        home_planet_name=name,
    )
    u = generate_universe(cfg)
    p = Player(id="P1", name="Seat", sector_id=1, credits=300, turns_per_day=250)
    u.players["P1"] = p
    u.sectors[1].occupant_ids.append("P1")
    return u, p


def test_the_switch_stays_legacy_until_the_profile_is_on(monkeypatch) -> None:
    """HOME_PLANET_MODE is stored legacy. V311_PROFILE turns the helper on."""
    assert K.HOME_PLANET_MODE == "legacy"
    assert K.home_planet_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.home_planet_live() is True
    assert K.HOME_PLANET_MODE == "legacy"


def test_legacy_home_planet_stays_in_the_start_sector_unassigned() -> None:
    """Profile off: the planet is in the seat's sector and the 191,000 sit idle."""
    u, p = _universe(planets=False)
    grant_starting_planet(u, p)
    planet = next(pl for pl in u.planets.values() if pl.owner_id == "P1")
    assert planet.sector_id == 1 and p.sector_id == 1
    assert p.planet_landed is None
    assert planet.name == "Seat Home"
    assert planet.colonists[Commodity.COLONISTS] == K.LIVE_STARTING_COLONISTS
    assert planet.colonists[Commodity.FUEL_ORE] == 0


def test_live_home_planet_is_outside_fedspace_and_split(monkeypatch) -> None:
    """transcript.txt: Fuel Ore 45 / Organics 65 / Equipment 81 thousand. The player starts landed."""
    monkeypatch.setattr(K, "HOME_PLANET_MODE", "live")
    u, p = _universe()
    grant_starting_planet(u, p)
    planet = next(pl for pl in u.planets.values() if pl.owner_id == "P1")
    assert planet.sector_id == p.sector_id
    assert int(planet.sector_id) not in K.FEDSPACE_SECTORS
    assert p.planet_landed == planet.id
    assert planet.name == "Seat's Home"
    assert planet.colonists[Commodity.FUEL_ORE] == 45_000
    assert planet.colonists[Commodity.ORGANICS] == 65_000
    assert planet.colonists[Commodity.EQUIPMENT] == 81_000
    assert planet.colonists[Commodity.COLONISTS] == 0
    assert int(planet.sector_id) in p.known_sectors
    for wid in u.sectors[planet.sector_id].warps:
        assert int(wid) in p.known_sectors
    assert _bfs_path(u, 1, int(planet.sector_id))
    assert _bfs_path(u, int(planet.sector_id), 1)
    other = Player(id="P2", name="Vega", sector_id=1, credits=300, turns_per_day=250)
    u.players["P2"] = other
    u.sectors[1].occupant_ids.append("P2")
    grant_starting_planet(u, other)
    second = next(pl for pl in u.planets.values() if pl.owner_id == "P2")
    assert second.sector_id != planet.sector_id
    assert int(second.sector_id) not in K.FEDSPACE_SECTORS


def test_the_same_seed_places_the_same_planet(monkeypatch) -> None:
    monkeypatch.setattr(K, "HOME_PLANET_MODE", "live")
    first, _ = _universe(seed=6601)
    grant_starting_planet(first, first.players["P1"])
    second, _ = _universe(seed=6601)
    grant_starting_planet(second, second.players["P1"])
    assert first.players["P1"].sector_id == second.players["P1"].sector_id


def test_planets_disabled_keeps_the_start_sector(monkeypatch) -> None:
    """REVISION.TXT 2894: start in sector 1 when planets are not allowed."""
    monkeypatch.setattr(K, "HOME_PLANET_MODE", "live")
    u, p = _universe(planets=False)
    grant_starting_planet(u, p)
    assert p.sector_id == 1
    planet = next(pl for pl in u.planets.values() if pl.owner_id == "P1")
    assert planet.sector_id == 1
    assert planet.colonists[Commodity.COLONISTS] == K.LIVE_STARTING_COLONISTS


def test_the_first_human_name_is_the_home_planet(monkeypatch) -> None:
    monkeypatch.setattr(K, "HOME_PLANET_MODE", "live")
    u, p = _universe(name="Probe Base")
    p.agent_kind = "external"
    grant_starting_planet(u, p)
    planet = next(pl for pl in u.planets.values() if pl.owner_id == "P1")
    assert planet.name == "Probe Base"
    bot = Player(id="P2", name="Vega", sector_id=1, credits=300, turns_per_day=250)
    u.players["P2"] = bot
    grant_starting_planet(u, bot)
    assert next(pl for pl in u.planets.values() if pl.owner_id == "P2").name == "Vega's Home"


def test_the_split_produces_15_9_6(monkeypatch) -> None:
    """Class M ratios 3 / 7 / 13 on 45 / 65 / 81 thousand: 15 fuel, 9 organics, 6 equipment."""
    monkeypatch.setattr(K, "CLASS_M_FIDELITY_MODE", "live")
    monkeypatch.setattr(K, "PLANET_PROD_MODE", "live")
    made = daily_production("M", {
        "fuel_ore": K.HOME_PLANET_FUEL,
        "organics": K.HOME_PLANET_ORGANICS,
        "equipment": K.HOME_PLANET_EQUIPMENT,
    })
    assert made == {"fuel_ore": 15, "organics": 9, "equipment": 6}


def _seat(u, pid: str, sector: int) -> Player:
    player = Player(id=pid, name=pid, sector_id=sector, credits=500, turns_per_day=250)
    u.players[pid] = player
    if pid not in u.sectors[sector].occupant_ids:
        u.sectors[sector].occupant_ids.append(pid)
    return player


def _world(owner: str | None, *, ticker: str | None = None) -> tuple:
    u, _ = _universe(seed=6610, planets=False)
    sector = 20
    owner_player = _seat(u, "P1", sector)
    other = _seat(u, "P2", sector)
    if ticker:
        owner_player.corp_ticker = ticker
        other.corp_ticker = ticker
    planet = Planet(
        id=46, sector_id=sector, name="Guest 1 Home", class_id=PlanetClass.M,
        owner_id=owner, corp_ticker=ticker, origin="other",
        colonists={Commodity.FUEL_ORE: 1_000, Commodity.ORGANICS: 0, Commodity.EQUIPMENT: 0, Commodity.COLONISTS: 0},
    )
    u.planets[46] = planet
    u.sectors[sector].planet_ids.append(46)
    return u, owner_player, other, planet


def _move(u, pid: str, kind: ActionKind, planet_id: int, extra: dict) -> object:
    args = {"planet_id": planet_id, **extra}
    return apply_action(u, pid, Action(kind=kind, args=args))


def test_a_stranger_and_an_unowned_planet_refuse_the_management_verbs() -> None:
    """Ownership holds with the switch off. The sentence is the same on a home planet and on an unclaimed one."""
    u, _owner, other, planet = _world("P1")
    other.planet_landed = planet.id
    for kind, extra in VERBS:
        result = _move(u, "P2", kind, planet.id, extra)
        assert result.ok is False and result.error == OWN, (kind, result.error)
    bare, owner, stranger, world = _world(None)
    stranger.planet_landed = world.id
    for kind, extra in VERBS:
        if kind is ActionKind.CLAIM_PLANET:
            continue
        result = _move(bare, "P2", kind, world.id, extra)
        assert result.ok is False and result.error == OWN, (kind, result.error)
    assert owner.id == "P1"


def test_the_owner_and_a_corp_mate_may_move_colonists(monkeypatch) -> None:
    monkeypatch.setattr(K, "HOME_PLANET_MODE", "live")
    u, owner, _other, planet = _world("P1")
    owner.planet_landed = planet.id
    moved = _move(u, "P1", ActionKind.ASSIGN_COLONISTS, planet.id, {"from": "fuel_ore", "to": "equipment", "qty": 10})
    assert moved.ok is True and moved.turns_spent == 0, moved.error
    assert planet.colonists[Commodity.EQUIPMENT] == 10
    assert owner.turns_today == 0
    shared, mate_owner, mate, world = _world("P1", ticker="ACME")
    mate.planet_landed = world.id
    corp = _move(shared, "P2", ActionKind.ASSIGN_COLONISTS, world.id, {"from": "fuel_ore", "to": "equipment", "qty": 5})
    assert corp.ok is True and corp.turns_spent == 0, corp.error
    assert mate_owner.corp_ticker == "ACME"


def test_legacy_population_move_still_costs_a_turn() -> None:
    u, owner, _other, planet = _world("P1")
    owner.planet_landed = planet.id
    moved = _move(u, "P1", ActionKind.ASSIGN_COLONISTS, planet.id, {"from": "fuel_ore", "to": "equipment", "qty": 10})
    assert moved.ok is True and moved.turns_spent == 1
    assert owner.turns_today == 1


def test_terra_is_not_a_planet_and_still_costs_one_turn(monkeypatch) -> None:
    """Landing on Terra is the colonist menu. No management verb has a planet id for it."""
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u, p = _universe(seed=6611, planets=True)
    assert u.terra_colonists is not None
    assert not any(pl.sector_id == 1 and "terra" in pl.name.lower() for pl in u.planets.values())
    p.sector_id = 1
    p.planet_landed = None
    for kind, extra in TERRA_VERBS:
        result = _move(u, "P1", kind, 999999, extra)
        assert result.ok is False, kind
        assert "terra" not in (result.error or "").lower() or result.error == OWN
    before = int(u.terra_colonists)
    taken = apply_action(u, "P1", Action(kind=ActionKind.TERRA_COLONISTS, args={"mode": "take", "qty": 1}))
    assert taken.ok is True and taken.turns_spent == K.TERRA_LOAD_TURNS == 1, taken.error
    assert int(u.terra_colonists) == before - K.TERRA_LIVE_PER_HOLD
    assert p.ship.cargo[Commodity.COLONISTS] == K.TERRA_LIVE_PER_HOLD


def test_the_lobby_form_validates_the_home_planet_name(tmp_path) -> None:
    blank = S.parse_game_form({"name": "Alpha"})
    assert blank.home_planet_name is None
    named = S.parse_game_form({"name": "Alpha", "home_planet_name": "Probe Base"})
    assert named.home_planet_name == "Probe Base"
    assert named.settings()["home_planet_name"] == "Probe Base"
    with pytest.raises(FormError):
        S.parse_game_form({"name": "Alpha", "home_planet_name": "x" * 31})
    html = pages.new_game("Galaxy War Command")
    assert 'name="home_planet_name"' in html
    assert "Home planet name" in pages.join_confirm("Galaxy War Command", game={"id": "g", "name": "Alpha"}, seat="P2", key="k")
    cmd = WM.serve_command(named.settings(), 44001, tmp_path)
    assert "--home-planet-name" in cmd and "Probe Base" in cmd
    assert "--home-planet-name" not in WM.serve_command(blank.settings(), 44002, tmp_path)


def test_the_cockpit_names_the_owner_and_keeps_terra_apart(tmp_path) -> None:
    """Redesign only. The card says the planet is yours. Terra is its own row."""
    _prior_info_mode = K.INFO_MODE
    base_port = None
    try:
        sync = pytest.importorskip("playwright.sync_api").sync_playwright
        import uvicorn

        from tests._port_lock import claim_ports, release_ports
        from tw2k.server.app import create_app
        from tw2k.server.runner import AgentSpec, MatchSpec

        base_port = claim_ports(1, low=40000, high=46000)
        token = "n" * 40
        app = create_app(auto_start=False)
        runner = app.state.runner
        runner._saves_root = tmp_path / "saves"
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=base_port, log_level="warning"))
        ready = {"ok": False}

        async def start() -> None:
            while not server.started:
                await asyncio.sleep(0.05)
            await runner.start(MatchSpec(
                config=GameConfig(
                    seed=66, universe_size=200, max_days=3, turns_per_day=250,
                    starting_credits=20_000, enable_ferrengi=False, enable_planets=True, action_delay_s=0.0,
                ),
                agents=[AgentSpec(player_id="P1", name="Guest 1", kind="external", external_token=token)],
                action_delay_s=0.05, external_timeout_s=600.0,
            ))
            for _ in range(400):
                agent = next((a for a in runner.state.agents if getattr(a, "player_id", None) == "P1"), None)
                if agent is not None and agent.awaiting_input and runner.state.universe is not None:
                    break
                await asyncio.sleep(0.05)
            ready["ok"] = True

        async def main() -> None:
            task = asyncio.create_task(start())
            await server.serve()
            task.cancel()
            await runner.stop()

        K.INFO_MODE = "legacy"
        thread = threading.Thread(target=lambda: asyncio.run(main()), daemon=True)
        thread.start()
        deadline = time.time() + 40
        while time.time() < deadline and not ready["ok"]:
            time.sleep(0.1)
        pw = sync().start()
        browser = pw.chromium.launch()
        try:
            assert ready["ok"]
            universe = runner.state.universe
            me = universe.players["P1"]
            planet = Planet(
                id=46, sector_id=me.sector_id, name="Guest 1 Home", class_id=PlanetClass.M,
                owner_id="P1", origin="other",
                colonists={Commodity.FUEL_ORE: 45_000, Commodity.ORGANICS: 65_000, Commodity.EQUIPMENT: 81_000, Commodity.COLONISTS: 0},
            )
            universe.planets[46] = planet
            universe.sectors[me.sector_id].planet_ids.append(46)
            me.planet_landed = 46
            agent = next(a for a in runner.state.agents if a.player_id == "P1")
            agent.current_observation = build_observation(universe, "P1")
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"http://127.0.0.1:{base_port}/bot?layout=redesign&seat=P1&token={token}")
            page.wait_for_selector("[data-claim=owner]", timeout=20_000)
            card = page.locator("[data-claim=owner]").inner_text()
            assert "Claimed by: Guest 1 (you)" in card
            assert "Your home planet" in card
            SHOTS.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(SHOTS / "1280-home.png"))
            me.planet_landed = None
            if me.sector_id != 1:
                try:
                    universe.sectors[me.sector_id].occupant_ids.remove("P1")
                except ValueError:
                    pass
                me.sector_id = 1
                if "P1" not in universe.sectors[1].occupant_ids:
                    universe.sectors[1].occupant_ids.append("P1")
            agent.current_observation = build_observation(universe, "P1")
            page.reload()
            page.wait_for_selector("[data-terra=row]", timeout=20_000)
            terra = page.locator("[data-terra=row]").inner_text()
            assert "Terra (colonist source, cannot be claimed)" in terra
            assert "Colonists" in terra
            mixed = page.locator("[data-planet=class]").all_inner_texts()
            assert not any(text.strip() == "(M) Terra" for text in mixed)
            page.screenshot(path=str(SHOTS / "1280-terra.png"))
        finally:
            browser.close()
            pw.stop()
            server.should_exit = True
            thread.join(timeout=15)
    finally:
        K.INFO_MODE = _prior_info_mode
        if base_port is not None:
            release_ports(base_port)

