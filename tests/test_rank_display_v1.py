"""rank-display-options-v1. The screens grow a second rank only when asked."""
import pytest

import tw2k.engine.constants as K
from tw2k.engine import GameConfig, build_observation, generate_universe
from tw2k.engine.models import Player, Ship, ShipClass
from tw2k.server.harness import final_standings

pytestmark = pytest.mark.legacy_profile


def _world():
    universe = generate_universe(GameConfig(seed=3, universe_size=20, max_days=2, enable_ferrengi=False))
    sid = next(s for s in sorted(universe.sectors) if s > 10)
    rich = Player(id="P1", name="Rich", sector_id=sid, ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER), experience=40, credits=100)
    poor = Player(id="P2", name="Poor", sector_id=sid, ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER), experience=2, credits=9000)
    universe.players["P1"] = rich
    universe.players["P2"] = poor
    universe.sectors[sid].occupant_ids.extend(["P1", "P2"])
    return universe, "P1", "P2"


def test_flag_stays_legacy() -> None:
    assert K.RANK_DISPLAY_MODE == "legacy"
    assert K.rank_display() == "legacy"
    assert K.rank_display_live() is False


def test_off_the_table_has_one_rank() -> None:
    universe, rich, _poor = _world()
    row = final_standings(universe)["standings"][0]
    assert "planet_value" not in row
    assert "experience_rank" not in row
    dumped = build_observation(universe, rich).model_dump()
    assert "rank_place" not in dumped


def test_both_shows_experience_and_net_worth(monkeypatch) -> None:
    monkeypatch.setattr(K, "RANK_DISPLAY_MODE", "both")
    universe, rich, poor = _world()
    rows = {r["seat"]: r for r in final_standings(universe)["standings"]}
    assert rows[rich]["experience_rank"] < rows[poor]["experience_rank"]
    assert rows[poor]["net_worth_rank"] < rows[rich]["net_worth_rank"]
    assert "planet_value" in rows[rich]
    place = build_observation(universe, rich).rank_place
    assert place["mode"] == "both"
    assert place["experience"] == 1
    assert "planet_value" in place
