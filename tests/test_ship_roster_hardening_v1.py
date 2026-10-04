"""Pins for the roster gaps the first cap tests let through."""

from __future__ import annotations

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Planet, PlanetClass, Player, Ship, ShipClass
from tw2k.engine.runner import _planet_odds_fight
from tw2k.server.runner import _is_day_done

# Copied from SHIP_ROSTER.md. Not read back out of the spec.
# price, max holds, included holds, fighters, shields, mines, genesis, photons, turns per warp
_CHART = {
    "merchant_cruiser": (41_300, 75, 20, 2500, 400, 50, 5, 0, 3),
    "scout_marauder": (15_950, 25, 25, 150, 100, 0, 0, 0, 2),
    "missile_frigate": (100_800, 60, 40, 5000, 400, 5, 0, 10, 3),
    "battleship": (88_500, 80, 80, 10_000, 750, 25, 1, 0, 4),
    "corporate_flagship": (163_500, 85, 85, 20_000, 1500, 100, 10, 0, 3),
    "colonial_transport": (63_600, 250, 50, 200, 500, 0, 5, 0, 6),
    "cargotran": (51_950, 125, 75, 400, 1000, 1, 2, 0, 4),
    "merchant_freighter": (33_400, 65, 65, 300, 500, 2, 2, 0, 2),
    "havoc_gunstar": (79_000, 50, 50, 10_000, 3000, 5, 1, 0, 3),
    "imperial_starship": (339_000, 150, 150, 50_000, 2000, 125, 10, 5, 4),
    "star_master": (61_300, 73, 30, 5000, 2000, 50, 5, 0, 3),
    "constellation": (72_500, 80, 20, 5000, 750, 25, 2, 0, 3),
    "tkhasi_orion": (42_500, 60, 30, 750, 750, 5, 1, 0, 2),
    "tholian_sentinel": (47_500, 50, 10, 2500, 4000, 50, 1, 0, 4),
    "taurean_mule": (63_600, 150, 40, 300, 600, 0, 1, 0, 4),
    "interdictor_cruiser": (539_000, 40, 20, 100_000, 4000, 200, 20, 0, 15),
}

# Legacy fighter and shield totals. The offense wave for these ten must keep
# this column, not the chart column above.
_LEGACY_WAVE = {
    "merchant_cruiser": (2500, 400),
    "scout_marauder": (250, 100),
    "missile_frigate": (5000, 400),
    "battleship": (10_000, 400),
    "corporate_flagship": (20_000, 1500),
    "colonial_transport": (200, 100),
    "cargotran": (400, 100),
    "merchant_freighter": (2500, 750),
    "havoc_gunstar": (10_000, 3000),
    "imperial_starship": (50_000, 5000),
}


def _universe():
    return generate_universe(
        GameConfig(seed=11, universe_size=25, enable_planets=False, enable_ferrengi=False)
    )


def _seat(universe, *, credits: int, ship: Ship, alignment: int = 0) -> Player:
    player = Player(id="P9", name="P9", ship=ship, credits=credits, alignment=alignment)
    player.sector_id = 1
    player.turns_per_day = 1000
    player.turns_today = 0
    universe.players["P9"] = player
    universe.sectors[1].occupant_ids.append("P9")
    player.known_sectors.add(1)
    player.known_warps[1] = list(universe.sectors[1].warps)
    return player


def _warp_once(universe, player: Player) -> int:
    origin = 1
    if player.sector_id != origin:
        try:
            universe.sectors[player.sector_id].occupant_ids.remove(player.id)
        except ValueError:
            pass
        player.sector_id = origin
        if player.id not in universe.sectors[origin].occupant_ids:
            universe.sectors[origin].occupant_ids.append(player.id)
    target = int(universe.sectors[origin].warps[0])
    before = player.turns_today
    result = apply_action(
        universe, player.id, Action(kind=ActionKind.WARP, args={"target": target})
    )
    assert result.ok, result.error
    assert player.alive
    return player.turns_today - before


def _offense_wave(ship_class: ShipClass, planet_fighters: int) -> int:
    player = Player(
        id="P",
        name="P",
        ship=Ship(ship_class=ship_class, fighters=1_000_000, shields=0),
    )
    planet = Planet(
        id=1,
        sector_id=8,
        name="Rock",
        class_id=PlanetClass.M,
        fighters=planet_fighters,
        shields=0,
        military_reaction_pct=100,
    )
    _a, _d, _s, rounds = _planet_odds_fight(player, planet)
    offense = next(row for row in rounds if row["phase"] == "offense")
    return int(offense["wave"])


def _wave_cap(fighters: int, shields: int) -> int:
    return (K.PLANET_OFFENSE_WAVE_NUM * (fighters + shields)) // K.PLANET_OFFENSE_WAVE_DEN


def test_chart_numbers_are_literals() -> None:
    specs = K.ship_specs()
    assert set(specs) == set(_CHART)
    for key, row in _CHART.items():
        price, max_holds, included, fighters, shields, mines, genesis, photons, turns = row
        spec = specs[key]
        assert int(spec["cost"]) == price
        assert int(spec["max_holds"]) == max_holds
        assert int(spec["holds"]) == included
        assert int(spec["max_fighters"]) == fighters
        assert int(spec["max_shields"]) == shields
        assert int(spec["max_mines"]) == mines
        assert int(spec["max_genesis"]) == genesis
        assert int(spec["max_photons"]) == photons
        assert int(spec["turns_per_warp"]) == turns
    assert int(specs["scout_marauder"]["max_fighters"]) == 150


def test_tholian_shields_are_4000() -> None:
    assert int(K.ship_specs()["tholian_sentinel"]["max_shields"]) == 4000


def test_cargotran_warp_spends_four_turns() -> None:
    universe = _universe()
    ship = Ship(ship_class=ShipClass.CARGOTRAN, holds=75, fighters=0)
    player = _seat(universe, credits=10_000, ship=ship)
    assert _warp_once(universe, player) == 4


def test_every_hull_warp_spends_its_chart_turns() -> None:
    universe = _universe()
    ship = Ship(holds=20, fighters=0)
    player = _seat(universe, credits=10_000, ship=ship)
    for key, row in _CHART.items():
        player.ship = Ship(ship_class=ShipClass(key), holds=int(row[2]), fighters=0)
        player.turns_today = 0
        assert _warp_once(universe, player) == row[8], key


def test_mine_cap_is_one_shared_total() -> None:
    universe = _universe()
    ship = Ship(holds=20, fighters=0)
    player = _seat(universe, credits=500_000, ship=ship)
    first = apply_action(
        universe, "P9", Action(kind=ActionKind.BUY_EQUIP, args={"item": "armid_mines", "qty": 30})
    )
    assert first.ok, first.error
    second = apply_action(
        universe, "P9", Action(kind=ActionKind.BUY_EQUIP, args={"item": "limpet_mines", "qty": 21})
    )
    assert not second.ok
    assert second.error == "exceeds ship mine capacity"
    assert sum(int(v) for v in player.ship.mines.values()) == 30


def test_day_done_reads_the_tw2002_warp(monkeypatch) -> None:
    monkeypatch.setattr("tw2k.engine.economy.trade_turn_cost", lambda _player: 100)
    cargo = Player(
        id="C",
        name="C",
        ship=Ship(ship_class=ShipClass.CARGOTRAN, holds=75, fighters=0),
        turns_per_day=80,
        turns_today=77,
    )
    assert _is_day_done(cargo) is True
    interdictor = Player(
        id="I",
        name="I",
        ship=Ship(ship_class=ShipClass.INTERDICTOR_CRUISER, holds=20, fighters=0),
        turns_per_day=80,
        turns_today=70,
    )
    assert _is_day_done(interdictor) is True
    interdictor.turns_today = 64
    assert _is_day_done(interdictor) is False


def test_runner_warp_reads_the_tw2002_table() -> None:
    universe = _universe()
    ship = Ship(ship_class=ShipClass.INTERDICTOR_CRUISER, holds=20, fighters=0)
    player = _seat(universe, credits=10_000, ship=ship)
    assert _warp_once(universe, player) == 15


def test_imperial_alignment_gate() -> None:
    universe = _universe()
    ship = Ship(holds=20, fighters=0)
    player = _seat(universe, credits=500_000, ship=ship, alignment=1999)
    params = next(row for row in legal_actions(universe, "P9") if row.kind == "buy_ship").params
    assert "imperial_starship" not in params["ship_class"]["choices"]
    refused = apply_action(
        universe, "P9", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": "imperial_starship"})
    )
    assert not refused.ok
    assert "alignment" in (refused.error or "")
    assert player.ship.ship_class == ShipClass.MERCHANT_CRUISER
    player.alignment = 2000
    params = next(row for row in legal_actions(universe, "P9") if row.kind == "buy_ship").params
    assert "imperial_starship" in params["ship_class"]["choices"]
    bought = apply_action(
        universe, "P9", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": "imperial_starship"})
    )
    assert bought.ok, bought.error
    assert player.ship.ship_class == ShipClass.IMPERIAL_STARSHIP


def test_old_hulls_keep_the_legacy_wave() -> None:
    for key, (fighters, shields) in _LEGACY_WAVE.items():
        cap = _wave_cap(fighters, shields)
        assert _offense_wave(ShipClass(key), cap + 50) == cap, key
    scout_legacy = _wave_cap(250, 100)
    scout_chart = _wave_cap(150, 100)
    assert _offense_wave(ShipClass.SCOUT_MARAUDER, 100_000) == scout_legacy
    assert scout_legacy != scout_chart


def test_new_hull_wave_uses_the_live_spec() -> None:
    cap = _wave_cap(5000, 2000)
    assert cap > 1
    assert _offense_wave(ShipClass.STAR_MASTER, cap + 50) == cap
