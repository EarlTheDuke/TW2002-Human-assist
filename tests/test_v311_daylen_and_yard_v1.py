"""NOTE 60 v311-daylen-and-yard-v1: the day-length setting, the day rolling on the clock,
a multi-day citadel, the shipyard roster in the buy_ship params, and the cockpit wording.

Tier S plants (each made one of these fail, then restored):
  pd1  server/runner.py: the clock roll is skipped, so the old all-done roll path runs
       -> the no-stall test sees no day 3.
  pd2  engine/constants.py: ``parse_day_seconds`` drops the range check -> ``tw2k serve
       --day-seconds 0`` gets past the check.
  pd3  engine/legality.py: ``stats_by`` reads ``max_holds`` for ``holds`` -> the v3.11 Scout
       shows 25 of 25.
"""

from __future__ import annotations

import asyncio
import math
import time
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Commodity, Planet, PlanetClass
from tw2k.server.broadcaster import Broadcaster
from tw2k.server.runner import AgentSpec, MatchRunner, MatchSpec

pytestmark = pytest.mark.legacy_profile

ROOT = Path(__file__).resolve().parents[1]

DAY_S = 120.0
SPEED = 50.0  # the fake clock and the scheduler sleeps both run 50x


def _v311(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.turn_regen_live() and K.live_pace() and K.starting_package_live()


def _fast_clock(monkeypatch) -> None:
    """time.time() runs SPEED times faster; asyncio (monotonic) is untouched."""
    real = time.time
    start = real()
    monkeypatch.setattr(time, "time", lambda: start + (real() - start) * SPEED)


def _spec(day_s: float | None, *, max_days: int = 8, seed: int = 250925) -> MatchSpec:
    return MatchSpec(
        config=GameConfig(seed=seed, universe_size=120, max_days=max_days, turns_per_day=250,
                          enable_ferrengi=False, enable_planets=True, action_delay_s=0.0,
                          turn_regen_day_seconds=day_s),
        agents=[AgentSpec(player_id="P1", name="A", kind="heuristic"),
                AgentSpec(player_id="P2", name="B", kind="heuristic")],
        action_delay_s=0.0,
        external_timeout_s=2.0,
    )


async def _until(cond, *, real_s: float = 20.0, dt: float = 0.002) -> bool:
    end = asyncio.get_event_loop().time() + real_s
    while asyncio.get_event_loop().time() < end:
        if cond():
            return True
        await asyncio.sleep(dt)
    return bool(cond())


# ---------------------------------------------------------------- item 1


@pytest.mark.parametrize("bad", [0, -5, 5, 9.99, 604_801, "abc", "", True, math.inf, math.nan, None])
def test_item1_day_length_rejects_nonsense_with_a_clear_message(bad) -> None:
    with pytest.raises(ValueError, match="day length"):
        K.parse_day_seconds(bad)
    if bad is not None:
        with pytest.raises(ValueError, match="day length"):
            GameConfig(turn_regen_day_seconds=bad)


def test_item1_one_setting_from_env_cli_or_config_and_unset_is_the_old_game(monkeypatch, tmp_path) -> None:
    from typer.testing import CliRunner

    from tw2k.cli import app as cli_app
    from tw2k.server.app import _build_default_spec

    assert K.TURN_REGEN_DAY_SECONDS == 86_400
    assert K.parse_day_seconds("120") == 120.0 and K.parse_day_seconds(10) == 10.0
    # Unset: no field in the stored config, so old saves and dumps stay byte-identical.
    monkeypatch.delenv(K.TURN_REGEN_DAY_SECONDS_ENV, raising=False)
    assert K.day_seconds_from_env() is None
    assert "turn_regen_day_seconds" not in GameConfig().model_dump()
    assert "turn_regen_day_seconds" not in GameConfig().model_dump_json()
    base = dict(seed=1, universe_size=50, max_days=2, agent_names=None, agent_kind="heuristic",
                provider=None, model=None, num_agents=2, turns_per_day=10)
    assert _build_default_spec(**base).config.turn_regen_day_seconds is None
    # The env feeds the game config; the CLI/create_app option wins over the env.
    monkeypatch.setenv(K.TURN_REGEN_DAY_SECONDS_ENV, "90")
    assert K.day_seconds_from_env() == 90.0
    assert _build_default_spec(**base).config.turn_regen_day_seconds == 90.0
    assert _build_default_spec(**base, turn_regen_day_seconds="300").config.turn_regen_day_seconds == 300.0
    assert GameConfig(turn_regen_day_seconds=90).model_dump()["turn_regen_day_seconds"] == 90.0
    # `tw2k serve` refuses nonsense before it starts anything (a missed check must not serve).
    import tw2k.cli as cli_mod

    def _no_serve(*_a, **_k):
        raise AssertionError("tw2k serve started a server with a bad day length")

    monkeypatch.setattr(cli_mod.uvicorn, "run", _no_serve)
    cli = CliRunner()
    bad_flag = cli.invoke(cli_app, ["serve", "--day-seconds", "0"])
    assert bad_flag.exit_code == 2 and "day length" in bad_flag.output
    monkeypatch.setenv(K.TURN_REGEN_DAY_SECONDS_ENV, "soon")
    bad_env = cli.invoke(cli_app, ["serve"])
    assert bad_env.exit_code == 2 and "day length" in bad_env.output


def test_item1_restart_rejects_a_bad_day_length(monkeypatch, tmp_path) -> None:
    from fastapi.testclient import TestClient

    from tw2k.server.app import create_app

    monkeypatch.delenv(K.TURN_REGEN_DAY_SECONDS_ENV, raising=False)
    app = create_app(auto_start=False)
    app.state.runner._saves_root = tmp_path / "saves"
    with TestClient(app, client=("127.0.0.1", 5000)) as client:
        res = client.post("/control/restart", json={"turn_regen_day_seconds": 3})
        assert res.status_code == 400
        assert "turn_regen_day_seconds" in res.json()["detail"] and "day length" in res.json()["detail"]


def test_item1_the_game_uses_its_day_length_and_puts_the_default_back(monkeypatch, tmp_path, caplog) -> None:
    monkeypatch.delenv(K.TURN_REGEN_DAY_SECONDS_ENV, raising=False)
    runner = MatchRunner(Broadcaster(), saves_root=tmp_path / "saves")
    seen: list[float] = []

    async def _go() -> None:
        await runner.start(_spec(300.0, max_days=2))
        assert await _until(lambda: runner.state.universe is not None and bool(runner.state.agents))
        seen.append(float(K.TURN_REGEN_DAY_SECONDS))
        await runner.stop()

    with caplog.at_level("INFO", logger="tw2k.server.runner"):
        asyncio.run(_go())
    # One value: the roll gap, the trickle and planets.py all read K.TURN_REGEN_DAY_SECONDS.
    assert seen == [300.0]
    assert K.TURN_REGEN_DAY_SECONDS == 86_400
    assert any("turn regen day length 300 s (game setting)" in r.getMessage() for r in caplog.records)
    planets_src = (ROOT / "src" / "tw2k" / "engine" / "planets.py").read_text(encoding="utf-8")
    runner_src = (ROOT / "src" / "tw2k" / "engine" / "runner.py").read_text(encoding="utf-8")
    assert "TURN_REGEN_DAY_SECONDS" in planets_src and "TURN_REGEN_DAY_SECONDS" in runner_src


# ---------------------------------------------------------------- item 2


def test_item2_no_day_two_stall_the_day_rolls_on_the_clock(monkeypatch, tmp_path) -> None:
    _v311(monkeypatch)
    _fast_clock(monkeypatch)
    runner = MatchRunner(Broadcaster(), saves_root=tmp_path / "saves")
    rolls: dict[int, float] = {}
    longest_out = {"P1": 0.0, "P2": 0.0}
    credits = {"P1": 0, "P2": 0}
    worst: dict[str, tuple] = {}
    out_since: dict[str, float | None] = {"P1": None, "P2": None}
    watching = {"on": False}
    turn_s = DAY_S / 250
    import tw2k.engine.runner as engine_runner

    real_refresh = engine_runner.refresh_offline_turns

    def spy(player, now=None):
        # The heuristic seat spends a turn the moment it has one, so the trickle is
        # watched where it pays: every credit path goes through refresh_offline_turns.
        before = int(player.turns_today)
        real_refresh(player, now)
        if not watching["on"] or player.id not in out_since:
            return
        t = time.time()
        if before >= player.turns_per_day:
            out_since[player.id] = out_since[player.id] or t
            if t - out_since[player.id] > longest_out[player.id]:
                longest_out[player.id] = t - out_since[player.id]
                worst[player.id] = (round(t - rolls[2], 2), runner.state.universe.day)
        if int(player.turns_today) < before:
            credits[player.id] += before - int(player.turns_today)
            out_since[player.id] = None

    monkeypatch.setattr(engine_runner, "refresh_offline_turns", spy)

    async def _go() -> None:
        await runner.start(_spec(DAY_S))
        runner.state.speed_multiplier = SPEED  # start() resets the runner state
        assert await _until(lambda: runner.state.universe is not None and runner.state.universe.day >= 2)
        u = runner.state.universe
        rolls[2] = time.time()
        # Both seats spend the last of their turns on day 2.
        for p in u.players.values():
            p.turns_today = p.turns_per_day
            p.turn_regen_at, p.turn_regen_frac = time.time(), 0.0
        watching["on"] = True
        end = asyncio.get_event_loop().time() + 25.0
        while u.day < 4 and asyncio.get_event_loop().time() < end:
            if u.day not in rolls:
                rolls[u.day] = time.time()
            await asyncio.sleep(0.002)
        rolls.setdefault(u.day, time.time())
        watching["on"] = False
        await runner.stop()

    asyncio.run(_go())
    print("rolls", {d: round(t - rolls[2], 2) for d, t in rolls.items()}, "longest at 0", longest_out, "credits", credits, "worst", worst)
    # About 250 turns a day came back to each seat across days 2-4 (two day lengths).
    span = rolls[max(rolls)] - rolls[2]
    for pid, n in credits.items():
        assert n >= 0.8 * span / turn_s, (pid, n, span)
    assert 3 in rolls and 4 in rolls, f"the game stalled: days seen {sorted(rolls)}"
    # Days 3 and 4 come on the clock, one day length apart (fake seconds).
    gap = rolls[4] - rolls[3]
    assert DAY_S - 2 <= gap <= DAY_S + 5, gap
    # Nobody sits at 0 of 250 past one turn interval (0.48 s on a 120 s day). The fake clock
    # also runs CPU time 50x (a day tick or a bot move of ~60 ms reads as ~3 s), so the
    # wait is judged in real seconds.
    for pid, stretch in longest_out.items():
        assert stretch / SPEED <= turn_s, (pid, stretch, turn_s)


def test_item2_legacy_keeps_the_old_day_roll(monkeypatch) -> None:
    assert K.V311_PROFILE != "v311" and not K.turn_regen_live()
    assert MatchRunner._regen_day_clock() is False
    runner = MatchRunner(Broadcaster())
    assert runner.day_clock() is None


# ---------------------------------------------------------------- item 3


def test_item3_citadel_l1_built_day_2_is_ready_day_6_on_the_clock(monkeypatch, tmp_path) -> None:
    _v311(monkeypatch)
    _fast_clock(monkeypatch)
    runner = MatchRunner(Broadcaster(), saves_root=tmp_path / "saves")
    got: dict[str, object] = {}

    async def _go() -> None:
        await runner.start(_spec(DAY_S, max_days=9))
        runner.state.speed_multiplier = SPEED
        assert await _until(lambda: runner.state.universe is not None and runner.state.universe.day >= 2)
        u = runner.state.universe
        p = u.players["P2"]
        sid = next(s for s in u.sectors if s > 10 and not u.sectors[s].planet_ids)
        planet = Planet(id=88601, sector_id=sid, name="Yardstick", class_id=PlanetClass.M,
                        owner_id="P2", citadel_level=0, citadel_target=0)
        u.planets[planet.id] = planet
        u.sectors[sid].planet_ids.append(planet.id)
        for pool in planet.colonists:
            planet.colonists[pool] = 0
        planet.colonists[Commodity.COLONISTS] = 1_000_000
        planet.stockpile[Commodity.FUEL_ORE] = 300
        planet.stockpile[Commodity.ORGANICS] = 200
        planet.stockpile[Commodity.EQUIPMENT] = 250
        here = u.sectors[p.sector_id]
        if p.id in here.occupant_ids:
            here.occupant_ids.remove(p.id)
        p.sector_id, p.planet_landed = sid, planet.id
        u.sectors[sid].occupant_ids.append(p.id)
        p.turns_today = 0
        spec = next(a for a in legal_actions(u, "P2") if a.kind == ActionKind.BUILD_CITADEL)
        nxt = spec.params["next"]
        got["quote"] = f"{nxt['days']} days. Ready day {u.day + nxt['days']}."
        got["built_on"] = u.day
        res = apply_action(u, "P2", Action(kind=ActionKind.BUILD_CITADEL, args={"planet_id": planet.id}))
        got["ok"] = res.ok
        got["eta"] = planet.citadel_complete_day
        # Keep the heuristic seat on its planet: the test watches the clock, not the bot.
        runner.state.agents[1].act = _wait_act
        days_l0: list[int] = []
        assert await _until(lambda: planet.citadel_level >= 1 or u.day > 7, real_s=40.0, dt=0.005)
        days_l0.append(u.day)
        got["done_day"] = u.day
        got["level"] = planet.citadel_level
        await runner.stop()

    asyncio.run(_go())
    assert got["built_on"] == 2 and got["ok"], got
    assert got["quote"] == "4 days. Ready day 6.", got
    assert got["eta"] == 6
    assert got["level"] == 1 and got["done_day"] == 6, got


async def _wait_act(obs):
    return Action(kind=ActionKind.WAIT, thought="resting")


# ---------------------------------------------------------------- item 4


def test_item4_the_observation_carries_the_server_turn_clock(monkeypatch, tmp_path) -> None:
    from fastapi.testclient import TestClient

    from tw2k.server.app import create_app

    _v311(monkeypatch)
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"

    async def _start() -> None:
        await runner.start(MatchSpec(
            config=GameConfig(seed=250925, universe_size=120, max_days=3, turns_per_day=250,
                              enable_ferrengi=False, action_delay_s=0.0, turn_regen_day_seconds=600),
            agents=[AgentSpec(player_id="P1", name="A", kind="heuristic"),
                    AgentSpec(player_id="P2", name="B", kind="external", external_token="tok-n60")],
            action_delay_s=0.05, external_timeout_s=600.0,
        ))

    with TestClient(app, client=("127.0.0.1", 5000)) as client:
        client.portal.call(_start)
        deadline = time.time() + 10
        while time.time() < deadline and (runner.state.universe is None or runner.day_clock() is None):
            time.sleep(0.05)
        u = runner.state.universe
        p2 = u.players["P2"]
        p2.turns_today = p2.turns_per_day
        p2.turn_regen_at, p2.turn_regen_frac = time.time() - 60.0, 0.0
        res = client.get("/harness/v1/P2/observation?peek=1", headers={"Authorization": "Bearer tok-n60"})
        assert res.status_code == 200, res.text[:300]
        tc = res.json()["turn_clock"]
        assert tc["day_seconds"] == 600.0 and tc["seconds_per_turn"] == 2.4
        assert tc["turns_per_hour"] == 1500.0
        assert 0 < tc["next_turn_in_s"] <= 2.4
        assert abs(tc["next_turn_at"] - (tc["server_now"] + tc["next_turn_in_s"])) < 0.2
        assert 0 < tc["next_day_in_s"] <= 600.0
        assert tc["next_day_at"] == pytest.approx(runner.day_clock()["next_day_at"])
        client.portal.call(runner.stop)
    src = (ROOT / "web" / "redesign.js").read_text(encoding="utf-8")
    assert "No turns left." in src and " Next turn in about " in src and " starts at " in src


def test_item4_legacy_observation_has_no_turn_clock(tmp_path) -> None:
    src = (ROOT / "src" / "tw2k" / "server" / "harness.py").read_text(encoding="utf-8")
    assert 'if K.turn_regen_live() and runner.state.universe is not None:\n            body["turn_clock"]' in src
    assert not K.turn_regen_live()


# ---------------------------------------------------------------- items 5 and 6


def _yard(monkeypatch, *, profile: bool):
    if profile:
        _v311(monkeypatch)
    from tw2k.engine.models import Player

    u = generate_universe(GameConfig(seed=250925, universe_size=120, max_days=3, enable_ferrengi=False))
    dock = int(K.stardock_sector_of(u))
    p = Player(id="P1", name="A", sector_id=dock, credits=50_000, turns_per_day=250)
    u.players["P1"] = p
    u.sectors[dock].occupant_ids.append("P1")
    return u, next(a for a in legal_actions(u, "P1") if a.kind == ActionKind.BUY_SHIP)


def test_item5_yard_stats_come_from_the_server_under_both_rosters(monkeypatch) -> None:
    u, legacy = _yard(monkeypatch, profile=False)
    assert "stats_by" not in legacy.params["ship_class"]  # legacy params are unchanged
    monkeypatch.setattr(K, "YARD_STATS_MODE", "live")
    u, legacy = _yard(monkeypatch, profile=False)
    scout = legacy.params["ship_class"]["stats_by"]["scout_marauder"]
    assert (scout["holds"], scout["max_holds"], scout["max_fighters"]) == (25, 25, 150)  # legacy roster
    monkeypatch.setattr(K, "YARD_STATS_MODE", "legacy")
    u, v311 = _yard(monkeypatch, profile=True)
    stats = v311.params["ship_class"]["stats_by"]
    assert set(stats) == set(v311.params["ship_class"]["net_cost_by"])
    scout = stats["scout_marauder"]
    assert (scout["holds"], scout["max_holds"], scout["max_fighters"]) == (10, 25, 250)
    assert scout["name"] == "Scout Marauder" and scout["cost"] > 0
    src = (ROOT / "web" / "redesign.js").read_text(encoding="utf-8")
    assert "stats_by" in src and "HULL[" in src  # HULL stays only as the fallback


def test_item6_yard_list_has_every_hull_and_greys_the_unaffordable(monkeypatch) -> None:
    u, spec = _yard(monkeypatch, profile=True)
    ship = spec.params["ship_class"]
    assert set(ship["choices"]) < set(ship["net_cost_by"])  # 50,000 cr cannot buy them all
    assert set(ship["blocked_by"]) == set(ship["net_cost_by"]) - set(ship["choices"])
    src = (ROOT / "web" / "redesign.js").read_text(encoding="utf-8")
    assert "function yardOptions(" in src and "disabled" in src


# ---------------------------------------------------------------- item 7


def test_item7_day_roll_wording_reads_the_server_rate() -> None:
    src = (ROOT / "web" / "redesign.js").read_text(encoding="utf-8")
    assert "Turns come back a little at a time; you have " in src
    # v3.11 default day: 250 turns over 86,400 s is about 10 an hour.
    assert round(250 * 3600 / K.TURN_REGEN_DAY_SECONDS) == 10


def test_defaults_stay_legacy() -> None:
    assert K.YARD_STATS_MODE == "legacy" and K.yard_stats_on() is False
    assert K.TURN_REGEN_DAY_SECONDS == 86_400
    assert K.TURN_REGEN_DAY_SECONDS_ENV == "TW2K_TURN_REGEN_DAY_SECONDS"
