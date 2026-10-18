"""v311-extern-gaps-v1 (COMMANDER NOTE 82). Rows 94, 96 and 97.

Rows 95 and 98 were already on this tip, so they have no new switch.
DAY-b: runner.tick_day already runs class0.extern_sweep, fed.run_tows and
hardware.tick_navhaz, and fighter_unit_price / shield_unit_price / hold_day_base
already follow the day.
CRP-h: corp.handle_corp_leave (the C.E.O. branch) calls corp.disband, which
keeps fighters in the C.E.O.'s sector and rogues the rest. See
tests/test_corp_rules_v1.py test_cr11_ceo_leave_dissolves_and_rogues_fighters.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

import tw2k.engine.constants as K
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.class0 import shield_unit_price
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Planet, PlanetClass, Player, Ship, ShipClass
from tw2k.engine.runner import apply_action, tick_day


def _world(**config):
    return generate_universe(GameConfig(
        seed=82, universe_size=40, max_days=30, turns_per_day=40,
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


def _probe_max(universe) -> int | None:
    row = next(la for la in legal_actions(universe, "P9") if la.kind == "buy_equip")
    return row.params["qty"]["max_by"].get("ether_probes")


def _stamp_bust(universe) -> object:
    for sector in universe.sectors.values():
        if sector.port is not None:
            sector.port.bust_player_id = "P9"
            return sector.port
    raise AssertionError("no port")


def _players(universe) -> None:
    for pid, name in (("P1", "Ann"), ("P2", "Ben")):
        player = Player(id=pid, name=name, agent_kind="external", sector_id=1, credits=25_000)
        universe.players[pid] = player
        universe.sectors[1].occupant_ids.append(pid)


def _act(universe, pid: str, kind: str, **args):
    return apply_action(universe, pid, Action(kind=ActionKind(kind), args=args))


def _move(universe, pid: str, sid: int) -> None:
    player = universe.players[pid]
    here = universe.sectors[player.sector_id]
    if pid in here.occupant_ids:
        here.occupant_ids.remove(pid)
    player.sector_id = sid
    universe.sectors[sid].occupant_ids.append(pid)


def _plant(universe, sid: int, owner: str, planet_id: int) -> Planet:
    planet = Planet(
        id=planet_id, sector_id=sid, name=f"Hold{planet_id}", class_id=PlanetClass.M,
        owner_id=owner, corp_ticker="XYZ",
    )
    universe.planets[planet.id] = planet
    universe.sectors[sid].planet_ids.append(planet.id)
    return planet


def _corp(universe):
    assert _act(universe, "P1", "corp_create", ticker="XYZ", name="Ex").ok
    assert _act(universe, "P1", "corp_set_password", password="Zx9").ok
    assert _act(universe, "P2", "corp_join", ticker="XYZ", password="Zx9").ok


def test_dayb_prices_already_follow_the_day() -> None:
    assert K.fighter_unit_price(1) != K.fighter_unit_price(9)
    assert K.hold_day_base(1) != K.hold_day_base(9)
    assert shield_unit_price(1) != shield_unit_price(9)


def test_bust_off_clears_every_extern_even_when_the_setting_is_7() -> None:
    universe = _world(bust_clear_days=7)
    port = _stamp_bust(universe)
    assert K.bust_record_clear_live() is False
    tick_day(universe)
    assert port.bust_player_id is None


def test_bust_live_waits_seven_days_and_nightly_still_clears(monkeypatch) -> None:
    monkeypatch.setattr(K, "BUST_CLEAR_MODE", "live")
    weekly = _world(bust_clear_days=7)
    port = _stamp_bust(weekly)
    weekly.day = 5
    tick_day(weekly)
    assert weekly.day == 6
    assert port.bust_player_id == "P9"
    weekly.day = 6
    tick_day(weekly)
    assert weekly.day == 7
    assert port.bust_player_id is None

    for days in (None, 1):
        nightly = _world(bust_clear_days=days)
        marked = _stamp_bust(nightly)
        tick_day(nightly)
        assert marked.bust_player_id is None


def test_bust_under_the_profile_is_nightly_unless_the_game_says_7(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.BUST_CLEAR_MODE == "legacy"
    assert K.bust_record_clear_live() is True
    nightly = _world()
    marked = _stamp_bust(nightly)
    tick_day(nightly)
    assert marked.bust_player_id is None

    weekly = _world(bust_clear_days=7)
    port = _stamp_bust(weekly)
    tick_day(weekly)
    assert port.bust_player_id == "P9"
    weekly.day = 6
    tick_day(weekly)
    assert port.bust_player_id is None


def test_bust_clear_days_accepts_only_1_and_7() -> None:
    assert GameConfig().bust_clear_days is None
    assert GameConfig(bust_clear_days=1).bust_clear_days == 1
    assert GameConfig(bust_clear_days=7).bust_clear_days == 7
    assert GameConfig(bust_clear_days="").bust_clear_days is None
    assert "bust_clear_days" not in GameConfig(seed=1).model_dump()
    assert GameConfig(seed=1, bust_clear_days=7).model_dump()["bust_clear_days"] == 7
    for bad in (0, 14, 28, True, "daily"):
        with pytest.raises(ValidationError):
            GameConfig(bust_clear_days=bad)


def test_probes_are_uncapped_until_the_chart_switch(monkeypatch) -> None:
    universe = _world()
    player = _seat(universe)
    assert K.ship_chart_cap_live() is False
    assert _probe_max(universe) == player.credits // K.ether_probe_cost()
    assert _buy(universe, "ether_probes", 26).ok
    assert player.ship.ether_probes == 26

    monkeypatch.setattr(K, "SHIP_CHART_CAP_MODE", "live")
    capped = _world()
    buyer = _seat(capped)
    assert _probe_max(capped) == K.PROBE_CHART_MAX
    assert _buy(capped, "ether_probes", 25).ok
    refused = _buy(capped, "ether_probes", 1)
    assert refused.ok is False and refused.error == "exceeds ship probe capacity"
    assert buyer.ship.ether_probes == 25
    assert _probe_max(capped) == 0
    assert K.equip_room("escape_pod", "ether_probes", 0) == 25


def test_profile_caps_probes_at_25(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.SHIP_CHART_CAP_MODE == "legacy"
    universe = _world()
    player = _seat(universe)
    assert _probe_max(universe) == 25
    assert _buy(universe, "ether_probes", 26).error == "exceeds ship probe capacity"
    assert player.ship.ether_probes == 0
    assert _buy(universe, "ether_probes", 25).ok


def test_chart_caps_for_mines_genesis_photons_and_cloaks_stay_on(monkeypatch) -> None:
    """These caps already ship with the tw2002 roster. The probe switch does not gate them."""
    for mode in ("legacy", "live"):
        monkeypatch.setattr(K, "SHIP_CHART_CAP_MODE", mode)
        universe = _world()
        merchant = _seat(universe)
        assert _buy(universe, "armid_mines", 50).ok
        assert _buy(universe, "limpet_mines", 1).error == "exceeds ship mine capacity"
        assert _buy(universe, "genesis", 5).ok
        assert _buy(universe, "genesis", 1).error == "exceeds ship genesis capacity"
        assert _buy(universe, "cloak", 5).ok
        assert _buy(universe, "cloak", 1).error == "exceeds ship cloak capacity"
        assert merchant.ship.genesis == 5
        assert int(merchant.ship.cloaks) == 5

        frigate = _world()
        seat = _seat(frigate, ship=Ship(ship_class=ShipClass.MISSILE_FRIGATE))
        assert _buy(frigate, "photon_missiles", 10).ok
        assert _buy(frigate, "photon_missiles", 1).error == "exceeds ship photon capacity"
        assert seat.ship.photon_missiles == 10

        scout = _world()
        _seat(scout, ship=Ship(ship_class=ShipClass.SCOUT_MARAUDER))
        assert _buy(scout, "genesis", 1).error == "exceeds ship genesis capacity"
        assert _buy(scout, "armid_mines", 1).error == "exceeds ship mine capacity"


def _leave_with_planets(universe):
    _players(universe)
    _corp(universe)
    _move(universe, "P1", 20)
    home = _plant(universe, 20, "P2", 8201)
    away = _plant(universe, 30, "P2", 8202)
    assert _act(universe, "P1", "corp_leave").ok
    assert "XYZ" not in universe.corporations
    return home, away


def test_planets_stay_with_their_owners_when_the_switch_is_off() -> None:
    universe = _world()
    assert K.corp_planet_disband_v306() is False
    home, away = _leave_with_planets(universe)
    assert (home.owner_id, home.corp_ticker) == ("P2", None)
    assert (away.owner_id, away.corp_ticker) == ("P2", None)
    assert [e for e in universe.events if e.kind.value == "planet_orphaned"] == []


def test_v306_switch_gives_the_ceo_his_sector_and_unclaims_the_rest(monkeypatch) -> None:
    monkeypatch.setattr(K, "CORP_PLANET_DISBAND_MODE", "v306")
    assert K.CORP_DISBAND_PLANETS == "owner_keeps"
    universe = _world()
    home, away = _leave_with_planets(universe)
    assert (home.owner_id, home.corp_ticker) == ("P1", None)
    assert (away.owner_id, away.corp_ticker) == (None, None)
    orphan = [e for e in universe.events if e.kind.value == "planet_orphaned"]
    assert len(orphan) == 1
    assert orphan[0].payload["former_owner"] == "P2"
    assert orphan[0].sector_id == 30


def test_profile_uses_the_v306_planet_rule(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.CORP_PLANET_DISBAND_MODE == "legacy"
    assert K.corp_planet_disband_v306() is True
    universe = _world()
    home, away = _leave_with_planets(universe)
    assert home.owner_id == "P1"
    assert away.owner_id is None


def test_old_v306_constant_still_selects_the_path() -> None:
    universe = _world()
    saved = K.CORP_DISBAND_PLANETS
    K.CORP_DISBAND_PLANETS = "v306"
    try:
        assert K.CORP_PLANET_DISBAND_MODE == "legacy"
        home, away = _leave_with_planets(universe)
    finally:
        K.CORP_DISBAND_PLANETS = saved
    assert home.owner_id == "P1"
    assert away.owner_id is None
