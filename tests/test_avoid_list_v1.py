"""avoid-list-v1. The computer keeps a list only when the switch is on."""
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.combat import _destroy_ship
from tw2k.engine.models import GameConfig, Player
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import _handle_avoid, _handle_plot_course
from tw2k.engine.universe import generate_universe
import tw2k.engine.constants as K


def _seat():
    universe = generate_universe(GameConfig(seed=7, universe_size=30, max_days=2, enable_ferrengi=False))
    player = Player(id="P1", name="Tester")
    player.sector_id = 1
    universe.players["P1"] = player
    universe.sectors[1].occupant_ids.append("P1")
    return universe, player


def test_flag_stays_legacy() -> None:
    assert K.AVOID_MODE == "legacy"
    assert K.avoid_live() is False


def test_off_omits_the_list_and_a_death_does_not_add_it() -> None:
    universe, player = _seat()
    pid = player.id
    assert "avoided_sectors" not in player.model_dump()
    assert "avoid_prompt" not in build_observation(universe, pid).model_dump()
    _destroy_ship(universe, pid, "test")
    assert universe.players[pid].avoided_sectors == []


def test_on_adds_routes_around_and_clears(monkeypatch) -> None:
    monkeypatch.setattr(K, "AVOID_MODE", "live")
    universe, player = _seat()
    pid = player.id
    start = int(player.sector_id)
    a, b, dest = 11, 12, 13
    universe.sectors[start].warps = [a, b]
    universe.sectors[a].warps = [dest]
    universe.sectors[b].warps = [dest]
    added = _handle_avoid(universe, pid, Action(kind=ActionKind.AVOID, args={"sector": a}))
    assert added.ok is True
    assert player.avoided_sectors == [a]
    plotted = _handle_plot_course(
        universe, pid, Action(kind=ActionKind.PLOT_COURSE, args={"target": dest}),
    )
    assert plotted.ok is True
    course = universe.events[-1].payload["path"]
    assert a not in course
    assert course[0] == b
    prompt = build_observation(universe, pid).model_dump()["avoid_prompt"]
    assert str(a) in prompt
    assert "0 clears" in prompt
    cleared = _handle_avoid(universe, pid, Action(kind=ActionKind.AVOID, args={"sector": 0}))
    assert cleared.ok is True
    assert player.avoided_sectors == []
    died_in = int(player.sector_id)
    _destroy_ship(universe, pid, "test")
    assert died_in in universe.players[pid].avoided_sectors
