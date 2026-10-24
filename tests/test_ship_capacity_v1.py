"""GAP 3.15. Mines, genesis, photons, and the printed TransWarp hop range.

Numbers are the Bible ship chart (docs/reference/tw2002/S3_tw2002_bible_v1.htm,
same cells in Bible_TWGS_edit_2007_Clme.htm) and MBBS page 2
(docs/reference/tw2002/stardock_manuals_and_text_docs/Someguy_MBBS_manual.txt
lines 531-563). Merchant Cruiser mines 50 / genesis 5 are Bible line 8365 / 8437
and MBBS line 533. Imperial StarShip mines 125 / genesis 10 / photons 5 are
Bible lines 9915 / 9987 / 9951 and MBBS line 549 (photons are the Bible column;
MBBS page 2 has no photon column). TransWarp hop ceilings are Bible only:
Corporate FlagShip Y/28 line 9057, Imperial StarShip Y/50 line 9927, Havoc
Gunstar Y/16 line 10097. Hulls that print N are not in SHIP_TW_CHART_RANGE.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Commodity, FighterDeployment, FighterMode, Player, Ship, ShipClass
from tw2k.engine.observation import build_observation


def _world(**config):
    return generate_universe(GameConfig(
        seed=315, universe_size=30, max_days=30, turns_per_day=40,
        starting_credits=50_000_000, enable_ferrengi=False, enable_planets=False,
        **config,
    ))


def _seat(universe, *, ship: Ship | None = None) -> Player:
    player = Player(
        id="P9", name="P9", ship=ship or Ship(), credits=50_000_000, sector_id=1,
    )
    player.turns_per_day = 1000
    player.turns_today = 0
    universe.players["P9"] = player
    universe.sectors[1].occupant_ids.append("P9")
    return player


def _buy(universe, item: str, qty: int):
    return apply_action(
        universe, "P9", Action(kind=ActionKind.BUY_EQUIP, args={"item": item, "qty": qty}),
    )


def test_switch_is_legacy_until_live_or_v311(monkeypatch) -> None:
    assert K.SHIP_CAPACITY_MODE == "legacy"
    assert K.ship_capacity_live() is False
    assert K.chart_transwarp_hops("imperial_starship") is None
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.ship_capacity_live() is False
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    assert K.ship_capacity_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.SHIP_CAPACITY_MODE == "legacy"
    assert K.ship_capacity_live() is True
    assert K.chart_transwarp_hops("imperial_starship") == 50
    assert K.chart_transwarp_hops("merchant_cruiser") is None


def test_chart_numbers_are_the_cited_cells() -> None:
    """Merchant Cruiser and Imperial StarShip, plus the three printed hop ceilings."""
    assert K.SHIP_CAPACITY_CHART["merchant_cruiser"] == {"mines": 50, "genesis": 5, "photons": 0}
    assert K.SHIP_CAPACITY_CHART["imperial_starship"] == {"mines": 125, "genesis": 10, "photons": 5}
    assert K.SHIP_TW_CHART_RANGE == {
        "corporate_flagship": 28,
        "imperial_starship": 50,
        "havoc_gunstar": 16,
    }
    for key, row in K.SHIP_CAPACITY_CHART.items():
        spec = K.hull_spec(key) or {}
        assert int(spec["max_mines"]) == row["mines"], key
        assert int(spec["max_genesis"]) == row["genesis"], key
        assert int(spec["max_photons"]) == row["photons"], key


def test_merchant_and_iss_are_unlimited_when_the_switch_is_off(monkeypatch) -> None:
    monkeypatch.setattr(K, "SHIP_CAPACITY_MODE", "legacy")
    merchant = _world()
    _seat(merchant)
    assert _buy(merchant, "armid_mines", 51).ok
    assert _buy(merchant, "genesis", 6).ok
    photon = _buy(merchant, "photon_missiles", 1)
    assert photon.ok is False
    assert photon.error == "only Missile Frigate or Imperial StarShip may buy photons"

    iss = _world()
    seat = _seat(iss, ship=Ship(ship_class=ShipClass.IMPERIAL_STARSHIP, holds=20, fighters=0))
    assert _buy(iss, "armid_mines", 126).ok
    assert _buy(iss, "genesis", 11).ok
    assert _buy(iss, "photon_missiles", 6).ok
    assert seat.ship.photon_missiles == 6
    assert seat.ship.genesis == 11


def test_merchant_and_iss_stop_at_the_chart_when_the_switch_is_on(monkeypatch) -> None:
    monkeypatch.setattr(K, "SHIP_CAPACITY_MODE", "live")
    merchant = _world()
    _seat(merchant)
    assert _buy(merchant, "armid_mines", 50).ok
    assert _buy(merchant, "limpet_mines", 1).error == "exceeds ship mine capacity"
    assert _buy(merchant, "genesis", 5).ok
    assert _buy(merchant, "genesis", 1).error == "exceeds ship genesis capacity"

    iss = _world()
    seat = _seat(iss, ship=Ship(ship_class=ShipClass.IMPERIAL_STARSHIP, holds=20, fighters=0))
    assert _buy(iss, "armid_mines", 125).ok
    assert _buy(iss, "limpet_mines", 1).error == "exceeds ship mine capacity"
    assert _buy(iss, "genesis", 10).ok
    assert _buy(iss, "genesis", 1).error == "exceeds ship genesis capacity"
    assert _buy(iss, "photon_missiles", 5).ok
    assert _buy(iss, "photon_missiles", 1).error == "exceeds ship photon capacity"
    assert seat.ship.photon_missiles == 5
    assert seat.ship.genesis == 10

    scout = _world()
    _seat(scout, ship=Ship(ship_class=ShipClass.SCOUT_MARAUDER, holds=10, fighters=0))
    assert _buy(scout, "armid_mines", 1).error == "exceeds ship mine capacity"
    assert _buy(scout, "genesis", 1).error == "exceeds ship genesis capacity"


def test_profile_caps_without_flipping_the_stored_flag(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.SHIP_CAPACITY_MODE == "legacy"
    merchant = _world()
    _seat(merchant)
    assert _buy(merchant, "armid_mines", 50).ok
    assert _buy(merchant, "armid_mines", 1).error == "exceeds ship mine capacity"


def test_holds_stay_on_the_roster_when_capacity_is_off(monkeypatch) -> None:
    monkeypatch.setattr(K, "SHIP_CAPACITY_MODE", "legacy")
    assert K.ship_specs()["merchant_cruiser"]["max_holds"] == 75
    universe = _world()
    player = _seat(universe, ship=Ship(holds=75, fighters=0))
    refused = _buy(universe, "holds", 1)
    assert refused.ok is False
    assert refused.error == "max holds reached"
    assert player.ship.holds == 75


def _line(n: int = 60):
    universe = generate_universe(GameConfig(
        seed=315, universe_size=n, enable_ferrengi=False, enable_planets=False,
    ))
    ids = sorted(universe.sectors)
    index = {sid: i for i, sid in enumerate(ids)}
    for sid in ids:
        sector = universe.sectors[sid]
        sector.port = None
        sector.planet_ids.clear()
        sector.fighters = None
        sector.mines.clear()
        sector.beacon = None
        sector.nav_hazard = 0
        i = index[sid]
        links = []
        if i > 0:
            links.append(ids[i - 1])
        if i + 1 < len(ids):
            links.append(ids[i + 1])
        sector.warps = links
    return universe, ids


def _pilot(universe, ids, *, hull: ShipClass, ore: int, dest_index: int):
    here = ids[0]
    dest = ids[dest_index]
    player = Player(
        id="P9", name="P9", alignment=1000, credits=1_000_000, sector_id=here,
        ship=Ship(ship_class=hull, holds=80, fighters=0),
    )
    player.turns_per_day = 5000
    player.turns_today = 0
    player.ship.transwarp_drive = "type1"
    player.ship.cargo[Commodity.FUEL_ORE] = int(ore)
    player.known_sectors.update({here, dest})
    universe.players["P9"] = player
    universe.sectors[here].occupant_ids.append("P9")
    universe.sectors[dest].fighters = FighterDeployment(
        owner_id="P9", count=1, mode=FighterMode.DEFENSIVE,
    )
    return player, dest


def _jump(universe, dest: int):
    return apply_action(
        universe, "P9", Action(kind=ActionKind.SHIP_TRANSWARP, args={"sector_id": dest}),
    )


def _choices(universe) -> list[int]:
    row = next((la for la in legal_actions(universe, "P9") if la.kind == "ship_transwarp"), None)
    if row is None or not row.legal:
        return []
    return list(row.params["sector_id"]["choices"])


def test_transwarp_hop_ceiling_is_off_until_the_switch(monkeypatch) -> None:
    """Imperial StarShip prints 50. Havoc Gunstar prints 16. Off, ore divided by 3 is the only limit."""
    monkeypatch.setattr(K, "SHIP_CAPACITY_MODE", "legacy")
    universe, ids = _line()
    player, far = _pilot(universe, ids, hull=ShipClass.IMPERIAL_STARSHIP, ore=200, dest_index=51)
    assert far in _choices(universe)
    jumped = _jump(universe, far)
    assert jumped.ok, jumped.error
    assert player.sector_id == far

    monkeypatch.setattr(K, "SHIP_CAPACITY_MODE", "live")
    universe, ids = _line()
    player, far = _pilot(universe, ids, hull=ShipClass.IMPERIAL_STARSHIP, ore=200, dest_index=51)
    near = ids[50]
    universe.sectors[near].fighters = FighterDeployment(
        owner_id="P9", count=1, mode=FighterMode.DEFENSIVE,
    )
    player.known_sectors.add(near)
    view = build_observation(universe, "P9").ship["transwarp"]
    assert view["max_hops_now"] == 50
    assert far not in _choices(universe)
    assert near in _choices(universe)
    refused = _jump(universe, far)
    assert refused.ok is False
    assert refused.error == "beyond this hull's TransWarp range (51 hops > 50)"
    assert player.sector_id == ids[0]
    assert int(player.ship.cargo[Commodity.FUEL_ORE]) == 200
    landed = _jump(universe, near)
    assert landed.ok, landed.error
    assert player.sector_id == near

    havoc, ids = _line()
    pilot, over = _pilot(havoc, ids, hull=ShipClass.HAVOC_GUNSTAR, ore=200, dest_index=17)
    edge = ids[16]
    havoc.sectors[edge].fighters = FighterDeployment(
        owner_id="P9", count=1, mode=FighterMode.DEFENSIVE,
    )
    pilot.known_sectors.add(edge)
    assert over not in _choices(havoc)
    refused = _jump(havoc, over)
    assert refused.ok is False
    assert refused.error == "beyond this hull's TransWarp range (17 hops > 16)"
    landed = _jump(havoc, edge)
    assert landed.ok, landed.error
    assert pilot.sector_id == edge
