"""NOTE 151. Inactive-user deletion and the lobby inactivity timeout.

Both switches stay legacy while they are off, including when V311_PROFILE is "1".
The switch, or V311_PROFILE "v311" alone, uses the printed figure.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.models import Corporation, Player
from tw2k.engine.runner import tick_day
from tw2k.public.manual import render


def _quiet_corp():
    universe = generate_universe(GameConfig(
        seed=31, universe_size=40, max_days=40, turns_per_day=20,
        enable_ferrengi=False, enable_planets=False,
    ))
    for pid, name in (("P1", "Ann"), ("P2", "Ben")):
        universe.players[pid] = Player(id=pid, name=name, sector_id=1, credits=1000)
        universe.sectors[1].occupant_ids.append(pid)
    universe.corporations["XYZ"] = Corporation(
        ticker="XYZ", name="Ex", ceo_id="P1", member_ids=["P1", "P2"],
    )
    universe.players["P1"].corp_ticker = "XYZ"
    universe.players["P2"].corp_ticker = "XYZ"
    return universe


def _quiet_days(mark_second: bool) -> tuple[bool, bool, bool]:
    universe = _quiet_corp()
    for _ in range(int(K.INACTIVE_USER_DAYS)):
        if mark_second:
            universe.players["P2"].played_today = True
        tick_day(universe)
    corp = universe.corporations["XYZ"]
    return (
        universe.players["P1"].alive,
        universe.players["P2"].alive,
        "P2" in corp.member_ids and corp.ceo_id == "P1",
    )


def test_inactive_days_and_timeout_fail_off_and_pass_on(monkeypatch) -> None:
    """GAP 12.4. 30 quiet days delete a trader. 14,400 seconds is the lobby idle limit.

    Off, the trader is still in the game and a 1 second lobby idle stays 1 second.
    A trader who acts each day stays. The corporation stays when its C.E.O. is deleted.
    """
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.inactive_user_live() is False
    assert K.inactivity_timeout_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")

    assert _quiet_days(False) == (True, True, True)
    assert K.lobby_idle_limit_s(1.0) == 1.0

    monkeypatch.setattr(K, "INACTIVE_USER_MODE", "v311")
    monkeypatch.setattr(K, "INACTIVITY_TIMEOUT_MODE", "v311")
    ceo_alive, mate_alive, corp_held = _quiet_days(True)
    assert ceo_alive is False
    assert mate_alive is True
    assert corp_held is True
    assert K.lobby_idle_limit_s(1.0) == 14_400

    monkeypatch.setattr(K, "INACTIVE_USER_MODE", "legacy")
    monkeypatch.setattr(K, "INACTIVITY_TIMEOUT_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.INACTIVE_USER_MODE == "legacy"
    assert K.INACTIVITY_TIMEOUT_MODE == "legacy"
    ceo_alive, mate_alive, corp_held = _quiet_days(True)
    assert ceo_alive is False
    assert mate_alive is True
    assert corp_held is True
    assert K.lobby_idle_limit_s(30.0) == 14_400


def test_manual_names_the_timeout_rules() -> None:
    page = render("Galaxy War Command")
    assert "an inactive trader stays in the game." in page
    assert "a quiet lobby game sleeps after the lobby's own idle setting." in page
