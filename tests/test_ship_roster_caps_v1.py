"""Yard roster: chart caps, trade-in, and the six hulls the old table left out."""

from __future__ import annotations

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, Ship, ShipClass
from tw2k.engine.observation import build_observation

_NEW_SHIPS = (
    "star_master",
    "constellation",
    "tkhasi_orion",
    "tholian_sentinel",
    "taurean_mule",
    "interdictor_cruiser",
)


def _universe():
    return generate_universe(
        GameConfig(seed=11, universe_size=25, enable_planets=False, enable_ferrengi=False)
    )


def _seat(universe, *, credits: int, ship: Ship, alignment: int = 0, corp: str | None = None) -> Player:
    player = Player(id="P9", name="P9", ship=ship, credits=credits, alignment=alignment)
    player.corp_ticker = corp
    player.sector_id = 1
    player.turns_per_day = 1000
    player.turns_today = 0
    universe.players["P9"] = player
    universe.sectors[1].occupant_ids.append("P9")
    player.known_sectors.add(1)
    player.known_warps[1] = list(universe.sectors[1].warps)
    return player


def _buy_row(universe):
    rows = legal_actions(universe, "P9")
    return next(row for row in rows if row.kind == "buy_ship")


def _equip_row(universe):
    rows = legal_actions(universe, "P9")
    return next(row for row in rows if row.kind == "buy_equip")


def test_merchant_cruiser_hold_cap_is_the_chart() -> None:
    spec = K.ship_specs()["merchant_cruiser"]
    assert spec["max_holds"] == 75
    assert spec["holds"] == 20
    assert K.ship_cost("merchant_cruiser") == 41_300


def test_scout_to_cargotran_uses_ship_cost_trade_in() -> None:
    """Scout's stored cost is 75000. The charge uses ship_cost 15950."""
    universe = _universe()
    ship = Ship(ship_class=ShipClass.SCOUT_MARAUDER, holds=25, fighters=0)
    player = _seat(universe, credits=500_000, ship=ship)
    net = K.net_hull_cost("scout_marauder", "cargotran")
    assert net == 51_950 - int(15_950 * 0.25)
    params = _buy_row(universe).params["ship_class"]
    assert params["trade_in"] == int(15_950 * 0.25)
    assert params["net_cost_by"]["cargotran"] == net
    before = player.credits
    result = apply_action(
        universe, "P9", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": "cargotran"})
    )
    assert result.ok, result.error
    assert before - player.credits == net
    assert player.credits >= 0


def test_star_master_is_on_the_legal_list() -> None:
    universe = _universe()
    ship = Ship(holds=20, fighters=0)
    player = _seat(universe, credits=2_000_000, ship=ship, alignment=5000, corp="ABC")
    params = _buy_row(universe).params["ship_class"]
    assert "star_master" in params["choices"]
    net = params["net_cost_by"]["star_master"]
    assert net == K.net_hull_cost("merchant_cruiser", "star_master")
    before = player.credits
    result = apply_action(
        universe, "P9", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": "star_master"})
    )
    assert result.ok, result.error
    assert player.ship.ship_class == ShipClass.STAR_MASTER
    assert player.ship.holds == 30
    assert before - player.credits == net


def test_buy_equip_stops_at_the_hold_cap() -> None:
    universe = _universe()
    ship = Ship(holds=75, fighters=0)
    player = _seat(universe, credits=500_000, ship=ship)
    assert _equip_row(universe).params["qty"]["max_by"]["holds"] == 0
    before = player.credits
    result = apply_action(
        universe, "P9", Action(kind=ActionKind.BUY_EQUIP, args={"item": "holds", "qty": 1})
    )
    assert not result.ok
    assert result.error == "max holds reached"
    assert player.ship.holds == 75
    assert player.credits == before


def test_every_ship_pair_charges_the_trade_in_and_stays_solvent() -> None:
    specs = K.ship_specs()
    keys = list(specs)
    universe = _universe()
    ship = Ship(holds=20, fighters=0)
    player = _seat(universe, credits=3_000_000, ship=ship, alignment=5000, corp="ABC")
    for old in keys:
        for new in keys:
            if old == new:
                continue
            player.ship = Ship(ship_class=ShipClass(old), holds=int(specs[old]["holds"]), fighters=0)
            player.credits = 3_000_000
            player.alignment = 5000
            player.corp_ticker = "ABC"
            net = K.net_hull_cost(old, new)
            assert net >= 0
            params = _buy_row(universe).params["ship_class"]
            assert params["trade_in"] == K.trade_in_credit(old)
            assert params["net_cost_by"][new] == net
            assert new in params["choices"]
            before = player.credits
            result = apply_action(
                universe, "P9", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": new})
            )
            assert result.ok, f"{old}->{new}: {result.error}"
            assert player.credits == before - net
            assert player.credits >= 0
            assert player.credits <= before
            assert player.ship.holds == int(specs[new]["holds"])
            if net > 0:
                player.ship = Ship(ship_class=ShipClass(old), holds=int(specs[old]["holds"]), fighters=0)
                player.credits = net - 1
                short = apply_action(
                    universe, "P9", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": new})
                )
                assert not short.ok
                assert player.credits == net - 1


def test_each_new_ship_buys_and_reads_its_caps() -> None:
    for key in _NEW_SHIPS:
        spec = K.ship_specs()[key]
        universe = _universe()
        ship = Ship(holds=20, fighters=0, shields=0)
        player = _seat(universe, credits=3_000_000, ship=ship, alignment=5000, corp="ABC")
        result = apply_action(
            universe, "P9", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": key})
        )
        assert result.ok, result.error
        assert player.ship.holds == int(spec["holds"])
        obs = build_observation(universe, "P9").model_dump(mode="json")
        view = obs["ship"]
        assert view["fighter_cap"] == spec["max_fighters"]
        assert view["shield_cap"] == spec["max_shields"]
        assert view["hold_cap"] == spec["max_holds"]
        assert view["mine_cap"] == spec["max_mines"]
        assert view["genesis_cap"] == spec["max_genesis"]
        assert view["photon_cap"] == spec["max_photons"]
        blob = str(obs)
        assert "mcic" not in blob.lower()
        assert "productivity" not in blob.lower()
        assert "haggle_limit" not in blob.lower()
        _fill_to_cap(universe, player, spec)


def test_prices_match_the_spec_and_legacy_keeps_the_old_roster() -> None:
    for key, spec in K.ship_specs().items():
        assert K.ship_cost(key) == int(spec["cost"])
        assert int(spec["holds"]) <= int(spec["max_holds"])
    previous = K.ECONOMY_SCALE_MODE
    try:
        K.ECONOMY_SCALE_MODE = "legacy"
        assert set(K.ship_specs()) == set(K.SHIP_SPECS)
        assert "star_master" not in K.ship_specs()
        assert K.ship_specs()["cargotran"]["turns_per_warp"] == 3
        assert K.ship_specs()["havoc_gunstar"]["holds"] == 65
        assert K.ship_cost("battleship") == 880_000
    finally:
        K.ECONOMY_SCALE_MODE = previous


def _reject(universe, item: str, qty: int) -> None:
    before_credits = universe.players["P9"].credits
    before = _cargo_snapshot(universe.players["P9"])
    result = apply_action(
        universe, "P9", Action(kind=ActionKind.BUY_EQUIP, args={"item": item, "qty": qty})
    )
    assert not result.ok, item
    assert universe.players["P9"].credits == before_credits
    assert _cargo_snapshot(universe.players["P9"]) == before


def _cargo_snapshot(player: Player) -> tuple:
    ship = player.ship
    mines = tuple(sorted((k.value, int(v)) for k, v in ship.mines.items()))
    return (ship.holds, ship.fighters, ship.shields, ship.genesis, ship.photon_missiles, mines)


def _fill_to_cap(universe, player: Player, spec: dict) -> None:
    player.credits = 40_000_000
    hold_room = int(spec["max_holds"]) - int(player.ship.holds)
    if hold_room > 0:
        bought = apply_action(
            universe, "P9", Action(kind=ActionKind.BUY_EQUIP, args={"item": "holds", "qty": hold_room})
        )
        assert bought.ok, bought.error
        assert player.ship.holds == int(spec["max_holds"])
    _reject(universe, "holds", 1)
    fighter_room = int(spec["max_fighters"]) - int(player.ship.fighters)
    if fighter_room > 0:
        bought = apply_action(
            universe,
            "P9",
            Action(kind=ActionKind.BUY_EQUIP, args={"item": "fighters", "qty": fighter_room}),
        )
        assert bought.ok, bought.error
    _reject(universe, "fighters", 1)
    shield_room = int(spec["max_shields"]) - int(player.ship.shields)
    if shield_room > 0:
        bought = apply_action(
            universe,
            "P9",
            Action(kind=ActionKind.BUY_EQUIP, args={"item": "shields", "qty": shield_room}),
        )
        assert bought.ok, bought.error
    _reject(universe, "shields", 1)
    mine_cap = int(spec["max_mines"])
    if mine_cap > 0:
        bought = apply_action(
            universe, "P9", Action(kind=ActionKind.BUY_EQUIP, args={"item": "armid_mines", "qty": mine_cap})
        )
        assert bought.ok, bought.error
    _reject(universe, "limpet_mines", 1)
    genesis_cap = int(spec["max_genesis"])
    if genesis_cap > 0:
        bought = apply_action(
            universe, "P9", Action(kind=ActionKind.BUY_EQUIP, args={"item": "genesis", "qty": genesis_cap})
        )
        assert bought.ok, bought.error
    _reject(universe, "genesis", 1)
    photon_cap = int(spec["max_photons"])
    if photon_cap > 0:
        bought = apply_action(
            universe,
            "P9",
            Action(kind=ActionKind.BUY_EQUIP, args={"item": "photon_missiles", "qty": photon_cap}),
        )
        assert bought.ok, bought.error
    _reject(universe, "photon_missiles", 1)
    listed = _equip_row(universe).params["qty"]["max_by"]
    assert listed["holds"] == 0
    assert listed["fighters"] == 0
    assert listed["shields"] == 0
    assert listed["genesis"] == 0
    assert listed["photon_missiles"] == 0
    assert listed["armid_mines"] == 0
