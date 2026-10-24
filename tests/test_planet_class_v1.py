"""planet-class-types-v1. The new switch stays off. The colonist conflict stays put."""
from pathlib import Path

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import runner
from tw2k.engine.models import Player, Ship, ShipClass


def test_flag_stays_legacy_and_the_open_colonist_count_stays() -> None:
    assert K.PLANET_CLASS_MODE == "legacy"
    assert K.planet_class_live() is False
    assert K.CITADEL_CLASS_COSTS["M"][0][0] == 1000
    assert K.CITADEL_CLASS_COSTS["U"][0] == (3000, 1200, 400, 2500, 8)
    assert K.PLANET_MAX_STOCK["M"]["fuel_ore"] == 100_000
    assert K.PLANET_MAX_STOCK["U"]["fuel_ore"] == 10_000


def test_off_keeps_the_old_launch(monkeypatch) -> None:
    result, player, weights = _launch(monkeypatch, live=False)
    assert result.turns_spent == 4
    assert player.alignment == 0
    assert set(weights) != {"M", "U"}
    assert K.genesis_torpedo_cost() == 25_000
    # GAP 3.15: the chart is SHIP_CAPACITY_MODE. Off, genesis stays unlimited.
    assert K.equip_room("merchant_freighter", "genesis", 0) is None
    assert K.equip_room("scout_marauder", "genesis", 0) is None
    monkeypatch.setattr(K, "SHIP_CAPACITY_MODE", "live")
    assert K.equip_room("merchant_freighter", "genesis", 0) == 2
    assert K.equip_room("scout_marauder", "genesis", 0) == 0


def test_on_uses_the_measured_launch(monkeypatch) -> None:
    result, player, weights = _launch(monkeypatch, live=True)
    assert result.ok and result.turns_spent == 0
    assert player.alignment == -10
    assert set(weights) == {"M", "U"}
    assert K.genesis_torpedo_cost() == 20_000
    # The freighter's one-torpedo rule is PLANET_CLASS_MODE, and it wins over the chart.
    assert K.equip_room("merchant_freighter", "genesis", 0) == 1
    assert K.equip_room("scout_marauder", "genesis", 0) is None
    monkeypatch.setattr(K, "SHIP_CAPACITY_MODE", "live")
    assert K.equip_room("merchant_freighter", "genesis", 0) == 1
    assert K.equip_room("scout_marauder", "genesis", 0) == 0


def test_citadel_hint_prints_the_goods_the_server_sends() -> None:
    text = Path("web/bot.js").read_text(encoding="utf-8")
    assert "n.fuel_ore" in text
    assert "paid from" in text


def _launch(monkeypatch, live: bool):
    monkeypatch.setattr(K, "GENESIS_MIN_HOPS_FROM_STARDOCK", 0)
    if live:
        monkeypatch.setattr(K, "PLANET_CLASS_MODE", "live")
    seen: dict = {}
    real = runner._weighted_choice

    def grab(rng, weights):
        seen.update(weights)
        return real(rng, weights)

    monkeypatch.setattr(runner, "_weighted_choice", grab)
    universe = generate_universe(GameConfig(
        seed=7, universe_size=40, enable_ferrengi=False, enable_planets=False,
    ))
    universe.players["A"] = Player(
        id="A",
        name="Alpha",
        ship=Ship(holds=20, ship_class=ShipClass.MERCHANT_CRUISER, genesis=1),
        sector_id=20,
        credits=1_000,
        alignment=0,
        turns_today=0,
    )
    universe.sectors[20].occupant_ids.append("A")
    result = apply_action(universe, "A", Action(kind=ActionKind.DEPLOY_GENESIS, args={}))
    assert result.ok, result.error
    return result, universe.players["A"], seen
