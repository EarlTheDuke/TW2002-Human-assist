"""NOTE 103. Mail is a switch. The live roster already has the 16 hulls and the pod."""

from __future__ import annotations

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.models import Player, Ship
from tw2k.engine.presence import note_poll

EXPECTED_HULLS = (
    "merchant_cruiser",
    "scout_marauder",
    "missile_frigate",
    "battleship",
    "corporate_flagship",
    "colonial_transport",
    "cargotran",
    "merchant_freighter",
    "imperial_starship",
    "havoc_gunstar",
    "star_master",
    "constellation",
    "tkhasi_orion",
    "tholian_sentinel",
    "taurean_mule",
    "interdictor_cruiser",
)


def _world():
    universe = generate_universe(
        GameConfig(seed=4, universe_size=20, max_days=5, enable_planets=False, enable_ferrengi=False)
    )
    for pid, name, kind in (("P1", "Ann", "heuristic"), ("P2", "Bo", "external")):
        player = Player(id=pid, name=name, ship=Ship(name="Ship"), credits=1_000, agent_kind=kind)
        player.sector_id = 1
        universe.players[pid] = player
        if pid not in universe.sectors[1].occupant_ids:
            universe.sectors[1].occupant_ids.append(pid)
    return universe


def _hail(universe, message="Ahoy"):
    return apply_action(universe, "P1", Action(kind=ActionKind.HAIL, args={"target": "P2", "message": message}))


def test_legacy_hail_is_stored_for_everyone() -> None:
    assert K.MAIL_MODE == "legacy"
    assert K.mail_live() is False
    universe = _world()
    done = _hail(universe)
    assert done.ok, done.error
    assert done.turns_spent == 0
    letter = universe.players["P2"].inbox[-1]
    assert letter["kind"] == "hail"
    assert letter["message"] == "Ahoy"
    assert universe.events[-1].payload.get("delivery") is None


def test_a_code_bot_gets_a_live_hail_and_a_quiet_cockpit_gets_mail(monkeypatch) -> None:
    monkeypatch.setattr(K, "MAIL_MODE", "live")
    universe = _world()
    universe.players["P2"].agent_kind = "heuristic"
    done = _hail(universe, "Bot")
    assert done.ok, done.error
    assert universe.players["P2"].inbox == []
    assert universe.events[-1].payload["delivery"] == "live"
    assert universe.events[-1].payload["ttl_s"] == K.HAIL_SHOW_SECONDS == 10

    universe.players["P2"].agent_kind = "external"
    done = _hail(universe, "Later")
    assert done.ok, done.error
    letter = universe.players["P2"].inbox[-1]
    assert letter["kind"] == "mail"
    assert letter["message"] == "Later"
    assert universe.events[-1].payload["delivery"] == "mail"


def test_an_open_cockpit_gets_the_flash(monkeypatch) -> None:
    monkeypatch.setattr(K, "MAIL_MODE", "live")
    universe = _world()
    note_poll(universe, "P2")
    done = _hail(universe, "Now")
    assert done.ok, done.error
    assert universe.players["P2"].inbox == []
    assert universe.events[-1].payload["delivery"] == "live"


def test_the_profile_turns_mail_on_without_moving_the_flag(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.mail_live() is True
    assert K.MAIL_MODE == "legacy"
    assert K.NAVPOINT_SLOTS == 4


def test_live_roster_has_the_sixteen_hulls_and_the_pod() -> None:
    assert tuple(K.SHIP_ROSTER_LIVE_TABLE) == EXPECTED_HULLS
    assert K.SHIP_ROSTER_LIVE_POD[0] == 14_446
    # stardock_modernmanual/core__ships.md combat columns. Costs stay on the v3.34b table.
    manual = {
        "star_master": (3, 1.4, 5_000, 73),
        "constellation": (3, 1.4, 5_000, 80),
        "tkhasi_orion": (2, 1.1, 750, 60),
        "taurean_mule": (4, 0.5, 300, 150),
    }
    for key, (tpw, odds, fighters, holds) in manual.items():
        _cost, _initial, max_holds, max_fighters, turns, offensive = K.SHIP_ROSTER_LIVE_TABLE[key]
        assert (turns, offensive, max_fighters, max_holds) == (tpw, odds, fighters, holds)
    monkeypatch_live = K.ship_roster_live
    assert monkeypatch_live() is False or K.SHIP_ROSTER_MODE == "live"
    for key in ("star_master", "constellation", "tkhasi_orion", "taurean_mule"):
        assert key in K.ship_specs() or key in K.SHIP_SPECS_TW2002
