"""NOTE 151. Inactive-user deletion and the lobby inactivity timeout.

Both switches stay legacy while they are off, including when V311_PROFILE is "1".
The switch, or V311_PROFILE "v311" alone, uses the printed figure.

Deletion counts wall-clock days. A fast game day does not. A connected seat
and an AI cockpit seat stay. A game generated before the switch was on is
not armed, so a later tick does not delete anyone in it.
"""

from __future__ import annotations

import logging

import tw2k.engine.constants as K
import tw2k.engine.presence as presence
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.models import Corporation, Player
from tw2k.engine.runner import inactive_clock, tick_day
from tw2k.public.manual import render

_DAY = 86_400.0


def _clock(monkeypatch, start: float = 1_700_000_000.0) -> dict[str, float]:
    clock = {"t": start}
    monkeypatch.setattr("tw2k.engine.runner.inactive_clock", lambda: clock["t"])
    monkeypatch.setattr(presence.time, "time", lambda: clock["t"])
    return clock


def _armed(monkeypatch):
    monkeypatch.setattr(K, "INACTIVE_USER_MODE", "v311")
    universe = generate_universe(GameConfig(
        seed=31, universe_size=40, max_days=80, turns_per_day=20,
        enable_ferrengi=False, enable_planets=False,
    ))
    assert universe.inactive_users_armed is True
    return universe


def _seat(universe, pid: str, name: str, *, kind: str, seen: float, cockpit: bool = False) -> Player:
    player = Player(
        id=pid, name=name, sector_id=1, credits=1000,
        agent_kind=kind, last_action_at=seen, ai_cockpit=cockpit,
    )
    universe.players[pid] = player
    universe.sectors[1].occupant_ids.append(pid)
    return player


def test_inactive_timeout_fails_off_and_passes_on(monkeypatch) -> None:
    """GAP 12.4. 14,400 seconds is the lobby idle limit. Off, the lobby keeps its own."""
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.inactive_user_live() is False
    assert K.inactivity_timeout_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    assert K.lobby_idle_limit_s(1.0) == 1.0

    monkeypatch.setattr(K, "INACTIVITY_TIMEOUT_MODE", "v311")
    assert K.lobby_idle_limit_s(1.0) == 14_400

    monkeypatch.setattr(K, "INACTIVITY_TIMEOUT_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.INACTIVITY_TIMEOUT_MODE == "legacy"
    assert K.lobby_idle_limit_s(30.0) == 14_400


def test_fast_game_days_do_not_delete_anyone(monkeypatch) -> None:
    """Thirty fast game days are minutes of wall clock. Nobody is deleted."""
    clock = _clock(monkeypatch)
    universe = _armed(monkeypatch)
    _seat(universe, "P1", "Ann", kind="human", seen=clock["t"])
    _seat(universe, "P2", "Ben", kind="external", seen=clock["t"])
    for _ in range(int(K.INACTIVE_USER_DAYS)):
        tick_day(universe)
        clock["t"] += 60.0
    assert universe.players["P1"].alive is True
    assert universe.players["P2"].alive is True
    assert universe.players["P1"].inactive_deleted is False


def test_ai_cockpit_seat_is_never_deleted(monkeypatch) -> None:
    """An AI cockpit seat stays after 30 real days, connected or not."""
    clock = _clock(monkeypatch)
    universe = _armed(monkeypatch)
    stale = clock["t"] - float(K.INACTIVE_USER_SPAN_S) - 5.0
    flagged = _seat(universe, "P1", "Cockpit", kind="external", seen=stale, cockpit=True)
    named = _seat(universe, "P2", "AI cockpit", kind="external", seen=stale)
    numbered = _seat(universe, "P3", "AI cockpit 2", kind="external", seen=stale)
    tick_day(universe)
    assert flagged.alive is True
    assert named.alive is True
    assert numbered.alive is True
    assert flagged.ai_cockpit is True


def test_quiet_human_deleted_after_thirty_real_days(monkeypatch, caplog) -> None:
    """A disconnected human with 30 real quiet days is deleted and logged.

    A seat that is open stays. A code bot stays. The corporation stays when
    the deleted trader is the C.E.O.
    """
    clock = _clock(monkeypatch)
    universe = _armed(monkeypatch)
    stale = clock["t"] - float(K.INACTIVE_USER_SPAN_S)
    quiet = _seat(universe, "P1", "Ann", kind="human", seen=stale)
    mate = _seat(universe, "P2", "Ben", kind="human", seen=clock["t"])
    online = _seat(universe, "P3", "Cam", kind="external", seen=stale)
    bot = _seat(universe, "P4", "N1", kind="heuristic", seen=stale)
    presence.note_poll(universe, "P3")
    universe.corporations["XYZ"] = Corporation(
        ticker="XYZ", name="Ex", ceo_id="P1", member_ids=["P1", "P2"],
    )
    quiet.corp_ticker = "XYZ"
    mate.corp_ticker = "XYZ"

    with caplog.at_level(logging.WARNING, logger="tw2k.inactive"):
        tick_day(universe)

    assert quiet.alive is False
    assert quiet.inactive_deleted is True
    assert mate.alive is True
    assert online.alive is True
    assert bot.alive is True
    corp = universe.corporations["XYZ"]
    assert corp.kept_after_inactive_ceo is True
    assert "P2" in corp.member_ids
    assert corp.ceo_id == "P1"
    assert any("inactive deletion id=P1" in rec.message for rec in caplog.records)


def test_game_started_before_the_switch_never_deletes(monkeypatch) -> None:
    """Turning the switch on later does not sweep a game that was already generated."""
    clock = _clock(monkeypatch)
    monkeypatch.setattr(K, "INACTIVE_USER_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    universe = generate_universe(GameConfig(
        seed=31, universe_size=40, max_days=80, turns_per_day=20,
        enable_ferrengi=False, enable_planets=False,
    ))
    assert universe.inactive_users_armed is False
    assert "inactive_users_armed" not in universe.model_dump()
    blank = Player(id="Z", name="Zed").model_dump()
    assert "last_action_at" not in blank
    assert "ai_cockpit" not in blank
    assert "played_today" not in blank
    stale = clock["t"] - float(K.INACTIVE_USER_SPAN_S) - 5.0
    human = _seat(universe, "P1", "Ann", kind="human", seen=stale)
    monkeypatch.setattr(K, "INACTIVE_USER_MODE", "v311")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.inactive_user_live() is True
    tick_day(universe)
    clock["t"] += float(K.INACTIVE_USER_SPAN_S) + 5.0
    tick_day(universe)
    assert human.alive is True
    assert universe.inactive_users_armed is False
    assert inactive_clock() == clock["t"]


def test_manual_names_the_timeout_rules() -> None:
    page = render("Galaxy War Command")
    assert "an inactive trader stays in the game." in page
    assert "a quiet lobby game sleeps after the lobby's own idle setting." in page
