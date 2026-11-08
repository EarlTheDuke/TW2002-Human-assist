"""The manual names this game's StarDock, not the legacy sector 1.

Claude seat pilot (2026-11-08): under v3.11 StarDock is drawn per game, but the
manual printed the legacy constant ("StarDock is sector 1") four times, so a
player (and the kimi cockpit seat before it) flew to Terra looking for it.
"""
from __future__ import annotations

import re

import pytest

import tw2k.engine.constants as K
from tw2k.public.manual import render


class _Universe:
    stardock_sector = 226


def _dock_lines(html: str) -> list[str]:
    return re.findall(r"StarDock is sector [^.<]*\.", html)


def test_the_game_manual_names_this_games_stardock(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    html = render("Galaxy War Command", universe=_Universe(), lobby=False)
    lines = _dock_lines(html)
    assert lines and all("226" in line for line in lines), lines
    assert "StarDock is sector 1." not in html
    assert "Terra in sector 1" in html


def test_the_lobby_manual_says_random_when_there_is_no_game(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    html = render("Galaxy War Command")
    assert "StarDock is in a random sector each game" in html
    assert "StarDock is sector 1." not in html


@pytest.mark.legacy_profile
def test_legacy_rules_keep_stardock_in_sector_1(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "STARDOCK_LOCATION_MODE", "legacy")
    html = render("Galaxy War Command")
    assert "StarDock is sector 1." in html
