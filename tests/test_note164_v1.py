"""NOTE 164. Four bottom-of-list rows, profile rows 200-203.

Each switch stays off while V311_PROFILE is "1" or "legacy". The switch, or
V311_PROFILE "v311" alone, turns that one rule on. The stored MODE stays
"legacy" when only the profile is set.
"""

from __future__ import annotations

from pathlib import Path

import tw2k.engine.constants as K
from tw2k.engine.combat import _destroy_ship, fighter_report
from tw2k.engine.corp import disband
from tw2k.engine.ferrengi import ferrengi_odds, hull_spec
from tw2k.engine.models import (
    Corporation,
    FerrengiShip,
    FighterDeployment,
    GameConfig,
    ParkedShip,
    Player,
    Ship,
    ShipClass,
)
from tw2k.engine.universe import generate_universe
from tw2k.public.manual import render

_PROFILE = Path("docs/plans/v311-profile-v1.md")


def _world():
    return generate_universe(GameConfig(seed=164, universe_size=40, enable_ferrengi=False, enable_planets=False))


def _sectors(universe, n):
    return [sid for sid in sorted(universe.sectors) if int(sid) > 10][:n]


def _sit(universe, pid, sector):
    if pid not in universe.players:
        universe.players[pid] = Player(id=pid, name=pid, ship=Ship(), sector_id=1)
        if pid not in universe.sectors[1].occupant_ids:
            universe.sectors[1].occupant_ids.append(pid)
    player = universe.players[pid]
    if pid in universe.sectors[player.sector_id].occupant_ids:
        universe.sectors[player.sector_id].occupant_ids.remove(pid)
    player.sector_id = int(sector)
    player.alive = True
    player.ship = Ship(ship_class=ShipClass.MERCHANT_CRUISER, name="merchant_cruiser", fighters=10)
    player.turns_today = 0
    if pid not in universe.sectors[int(sector)].occupant_ids:
        universe.sectors[int(sector)].occupant_ids.append(pid)
    return player


def _park(universe, pid, sector, ticker):
    from tw2k.engine.fleet import _new_ship_id

    ship = Ship(ship_class=ShipClass.MERCHANT_FREIGHTER, name="merchant_freighter", fighters=0, holds=20)
    ship.corp_ticker = ticker
    sid = _new_ship_id(universe)
    ship.fleet_id = sid
    universe.parked_ships[sid] = ParkedShip(
        id=sid, owner_id=pid, sector_id=int(sector), ship=ship, parked_day=int(universe.day),
    )
    return sid


def _ferr(hull: str) -> FerrengiShip:
    return FerrengiShip(id="x", name="x", sector_id=20, aggression=4, fighters=3000, shields=10, hull=hull)


def test_profile_rows_are_200_and_the_heading_matches() -> None:
    assert K.V311_PROFILE_HELPERS["ferrengi_odds_live"][0] == "FERRENGI_ODDS_MODE"
    assert K.V311_PROFILE_HELPERS["corp_ship_disband_live"][0] == "CORP_SHIP_DISBAND_MODE"
    assert K.V311_PROFILE_HELPERS["times_blown_live"][0] == "TIMES_BLOWN_MODE"
    assert K.V311_PROFILE_HELPERS["fighter_report_live"][0] == "FIGHTER_REPORT_MODE"
    text = _PROFILE.read_text(encoding="utf-8")
    assert f"## The switch set ({len(K.V311_PROFILE_HELPERS)} helpers)" in text
    assert len(K.V311_PROFILE_HELPERS) == 163
    for row in ("| 200 |", "| 201 |", "| 202 |", "| 203 |"):
        assert row in text


def test_ferrengi_odds_fail_off_and_pass_on(monkeypatch) -> None:
    """GAP 8.1. Off is FERRSPEC 1.0 / 1.2 / 1.4. On is the Bible 1.2 / 1.4 / 1.4."""
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.ferrengi_odds_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    assert K.ferrengi_odds_live() is False
    assert ferrengi_odds(_ferr("assault_trader")) == 1.0
    assert ferrengi_odds(_ferr("battle_cruiser")) == 1.2
    assert ferrengi_odds(_ferr("dreadnought")) == 1.4
    assert K.ferrengi_fighters_per_attack("assault_trader") == 1_000
    assert K.scanner_room("assault_trader") is None
    assert hull_spec("assault_trader")["odds"] == 1.0

    monkeypatch.setattr(K, "FERRENGI_ODDS_MODE", "v311")
    assert ferrengi_odds(_ferr("assault_trader")) == 1.2
    assert ferrengi_odds(_ferr("battle_cruiser")) == 1.4
    assert ferrengi_odds(_ferr("dreadnought")) == 1.4
    assert K.ferrengi_fighters_per_attack("assault_trader") == 2_000
    assert K.ferrengi_fighters_per_attack("battle_cruiser") == 2_000
    assert K.ferrengi_fighters_per_attack("dreadnought") == 5_000
    assert K.scanner_room("assault_trader") == K.SCANNER_HOLO
    assert hull_spec("assault_trader")["odds"] == 1.0
    assert K.FERRENGI_ODDS_BY_HULL["assault_trader"] == 1.0

    monkeypatch.setattr(K, "FERRENGI_ODDS_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.FERRENGI_ODDS_MODE == "legacy"
    assert ferrengi_odds(_ferr("assault_trader")) == 1.2
    assert K.scanner_room("assault_trader") == K.SCANNER_HOLO


def test_corp_ship_disband_fails_off_and_passes_on(monkeypatch) -> None:
    """GAP 6.11. Off, the C.E.O.'s sector still goes defunct. On, that ship becomes the C.E.O.'s."""
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.corp_ship_disband_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    assert K.corp_ship_disband_live() is False

    universe = _world()
    home, away = _sectors(universe, 2)
    ceo = _sit(universe, "A", home)
    ceo.ship.corp_ticker = "XX"
    universe.corporations["XX"] = Corporation(ticker="XX", name="XX", ceo_id="A", member_ids=["A"])
    ceo.corp_ticker = "XX"
    here = _park(universe, "A", home, "XX")
    there = _park(universe, "A", away, "XX")
    disband(universe, universe.corporations["XX"])
    assert universe.parked_ships[here].owner_id == K.DEFUNCT_OWNER
    assert universe.parked_ships[there].owner_id == K.DEFUNCT_OWNER
    assert ceo.ship.corp_ticker == "XX"

    monkeypatch.setattr(K, "CORP_SHIP_DISBAND_MODE", "v311")
    universe = _world()
    home, away = _sectors(universe, 2)
    ceo = _sit(universe, "A", home)
    ceo.ship.corp_ticker = "XX"
    universe.corporations["XX"] = Corporation(ticker="XX", name="XX", ceo_id="A", member_ids=["A"])
    ceo.corp_ticker = "XX"
    here = _park(universe, "A", home, "XX")
    there = _park(universe, "A", away, "XX")
    disband(universe, universe.corporations["XX"])
    assert universe.parked_ships[here].owner_id == "A"
    assert universe.parked_ships[here].ship.corp_ticker is None
    assert universe.parked_ships[there].owner_id == K.DEFUNCT_OWNER
    assert ceo.ship.corp_ticker == "XX"

    dead = _world()
    home, away = _sectors(dead, 2)
    ceo = _sit(dead, "A", home)
    ceo.alive = False
    dead.corporations["XX"] = Corporation(ticker="XX", name="XX", ceo_id="A", member_ids=["A"])
    here = _park(dead, "A", home, "XX")
    disband(dead, dead.corporations["XX"])
    assert dead.parked_ships[here].owner_id == K.DEFUNCT_OWNER

    monkeypatch.setattr(K, "CORP_SHIP_DISBAND_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.CORP_SHIP_DISBAND_MODE == "legacy"
    assert K.corp_ship_disband_live() is True


def test_times_blown_fails_off_and_passes_on(monkeypatch) -> None:
    """GAP 12.6. Off keeps death #1/3. On, with elimination off, the line says unlimited."""
    monkeypatch.setattr(K, "DEATH_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.times_blown_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    assert K.times_blown_live() is False

    universe = _world()
    universe.config.elimination_deaths = 0
    home = _sectors(universe, 1)[0]
    player = _sit(universe, "A", home)
    player.name = "Alice"
    _destroy_ship(universe, "A", "mines")
    assert universe.events[-1].summary == (
        "*** Alice's ship destroyed (mines); ejected to StarDock [death #1/3] ***"
    )
    assert player.alive

    monkeypatch.setattr(K, "TIMES_BLOWN_MODE", "v311")
    universe = _world()
    universe.config.elimination_deaths = 0
    player = _sit(universe, "A", _sectors(universe, 1)[0])
    player.name = "Alice"
    _destroy_ship(universe, "A", "mines")
    summary = universe.events[-1].summary
    assert "unlimited" in summary
    assert "/3" not in summary
    assert player.alive

    monkeypatch.setattr(K, "TIMES_BLOWN_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.TIMES_BLOWN_MODE == "legacy"
    universe = _world()
    universe.config.elimination_deaths = 0
    player = _sit(universe, "A", _sectors(universe, 1)[0])
    player.name = "Alice"
    _destroy_ship(universe, "A", "mines")
    assert "/3" not in universe.events[-1].summary
    assert "unlimited" in universe.events[-1].summary


def test_fighter_report_fails_off_and_passes_on(monkeypatch) -> None:
    """GAP 13.4. Off returns nothing. On lists this owner's sectors and omits a count of 0."""
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.fighter_report_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    assert K.fighter_report_live() is False

    universe = _world()
    home, away, other = _sectors(universe, 3)
    universe.sectors[home].fighters = FighterDeployment(owner_id="A", count=4)
    universe.sectors[away].fighters = FighterDeployment(owner_id="A", count=0)
    universe.sectors[other].fighters = FighterDeployment(owner_id="B", count=9)
    assert fighter_report(universe, "A") == []

    monkeypatch.setattr(K, "FIGHTER_REPORT_MODE", "v311")
    assert fighter_report(universe, "A") == [{"sector_id": int(home), "count": 4}]
    assert fighter_report(universe, "B") == [{"sector_id": int(other), "count": 9}]

    monkeypatch.setattr(K, "FIGHTER_REPORT_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.FIGHTER_REPORT_MODE == "legacy"
    assert fighter_report(universe, "A") == [{"sector_id": int(home), "count": 4}]


def test_manual_names_the_four_switches() -> None:
    page = render("Galaxy War Command")
    for name in (
        "FERRENGI_ODDS_MODE",
        "CORP_SHIP_DISBAND_MODE",
        "TIMES_BLOWN_MODE",
        "FIGHTER_REPORT_MODE",
    ):
        assert name in page
        assert "The v3.11 profile turns it on. The string 1 does not." in page
    assert "in v3.11 games" not in page
