"""NOTE 117: FedSpace fighter cap, the Bible tow line, and corp break-in alignment."""

from __future__ import annotations

from pathlib import Path

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.fed import fedspace_hint, run_tows
from tw2k.engine.models import EventKind, Player, Ship, ShipClass
from tw2k.engine.runner import tick_day
from tw2k.engine.victory import is_fedsafe
from tw2k.public.manual import render

ROOT = Path(__file__).resolve().parents[1]


def _world(players: dict) -> object:
    universe = generate_universe(
        GameConfig(seed=11701, universe_size=40, enable_ferrengi=False, enable_planets=False)
    )
    for pid, raw in players.items():
        kw = dict(raw)
        fighters = int(kw.pop("fighters", 20))
        sector_id = int(kw.pop("sector_id", 2))
        ship = Ship(
            holds=20,
            fighters=fighters,
            shields=0,
            ship_class=ShipClass.MERCHANT_CRUISER,
        )
        player = Player(
            id=pid,
            name=pid,
            ship=ship,
            sector_id=sector_id,
            credits=int(kw.pop("credits", 50_000)),
            alignment=int(kw.pop("alignment", 0)),
            experience=int(kw.pop("experience", 100)),
            **kw,
        )
        universe.players[pid] = player
        if pid not in universe.sectors[sector_id].occupant_ids:
            universe.sectors[sector_id].occupant_ids.append(pid)
        player.known_sectors.add(sector_id)
    return universe


def _attack(universe, pid: str, target: str):
    return apply_action(universe, pid, Action(kind=ActionKind.ATTACK, args={"target": target, "qty": 10}))


def test_switches_stay_legacy() -> None:
    assert K.FEDSAFE_FIGHTER_CAP_MODE == "legacy"
    assert K.FED_TOW_LIMIT_MODE == "legacy"
    assert K.CORP_BREAKIN_ALIGN_MODE == "legacy"
    assert K.fedsafe_fighter_cap_live() is False
    assert K.fed_tow_limit_live() is False
    assert K.corp_breakin_align_live() is False
    assert K.fedsafe_max_fighters() is None
    assert K.fed_tow_fighter_limit() == K.FED_TOW_FIGHTER_LIMIT == 98
    assert K.corp_breakin_align_loss() == K.CORP_BREAKIN_ALIGN_LOSS == 0


def test_v311_turns_the_helpers_on_without_moving_the_stored_flag(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.fedsafe_fighter_cap_live() is True
    assert K.fed_tow_limit_live() is True
    assert K.corp_breakin_align_live() is True
    assert K.FEDSAFE_FIGHTER_CAP_MODE == "legacy"
    assert K.FED_TOW_LIMIT_MODE == "legacy"
    assert K.CORP_BREAKIN_ALIGN_MODE == "legacy"
    assert K.FEDSAFE_MAX_FIGHTERS is None
    assert K.FED_TOW_FIGHTER_LIMIT == 98
    assert K.CORP_BREAKIN_ALIGN_LOSS == 0
    assert K.fedsafe_max_fighters() == 50
    assert K.fed_tow_fighter_limit() == 50
    assert K.corp_breakin_align_loss() == 1


def test_fighter_cap_is_50_only_while_the_profile_is_on(monkeypatch) -> None:
    universe = _world({"A": {"alignment": 0, "experience": 100, "fighters": 50, "sector_id": 3}})
    trader = universe.players["A"]
    assert is_fedsafe(trader)
    trader.ship.fighters = 51
    assert is_fedsafe(trader)
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert is_fedsafe(trader) is False
    trader.ship.fighters = 50
    assert is_fedsafe(trader) is True


def test_tow_stays_at_99_until_the_profile_uses_50(monkeypatch) -> None:
    players = {
        "A": {"fighters": 50, "sector_id": 3},
        "B": {"fighters": 51, "sector_id": 4},
        "C": {"fighters": 98, "sector_id": 5},
        "D": {"fighters": 99, "sector_id": 6},
    }
    universe = _world(players)
    assert fedspace_hint(universe, universe.players["B"])["tow_fighter_limit"] == 98
    assert fedspace_hint(universe, universe.players["B"])["will_be_towed"] is False
    run_tows(universe)
    assert universe.players["A"].sector_id == 3
    assert universe.players["B"].sector_id == 4
    assert universe.players["C"].sector_id == 5
    assert universe.players["D"].sector_id not in K.FEDSPACE_SECTORS

    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    live = _world(players)
    hint = fedspace_hint(live, live.players["B"])
    assert hint["tow_fighter_limit"] == 50
    assert hint["will_be_towed"] is True
    assert fedspace_hint(live, live.players["A"])["will_be_towed"] is False
    run_tows(live)
    assert live.players["A"].sector_id == 3
    assert live.players["B"].sector_id not in K.FEDSPACE_SECTORS
    assert live.players["C"].sector_id not in K.FEDSPACE_SECTORS
    assert live.players["D"].sector_id not in K.FEDSPACE_SECTORS


def test_over_armed_good_trader_can_be_attacked_when_the_profile_is_on(monkeypatch) -> None:
    seated = {
        "A": {"alignment": -50, "experience": 500, "fighters": 200, "sector_id": 2},
        "B": {"alignment": 10, "experience": 100, "fighters": 51, "sector_id": 2},
    }
    legacy = _world(seated)
    refused = _attack(legacy, "A", "B")
    assert refused.ok is False
    assert "Zyrain" in (refused.error or "")
    assert any(event.kind == EventKind.FED_ZYRAIN for event in legacy.events)

    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    live = _world(seated)
    fought = _attack(live, "A", "B")
    assert fought.ok is True
    assert "Zyrain" not in (fought.error or "")
    assert not any(event.kind == EventKind.FED_ZYRAIN for event in live.events)

    safe = _world({
        "A": {"alignment": -50, "experience": 500, "fighters": 200, "sector_id": 2},
        "B": {"alignment": 10, "experience": 100, "fighters": 50, "sector_id": 2},
    })
    still = _attack(safe, "A", "B")
    assert still.ok is False
    assert "Zyrain" in (still.error or "")


def _corp():
    universe = generate_universe(GameConfig(
        seed=11702, universe_size=40, max_days=3, turns_per_day=60,
        starting_credits=25_000, enable_ferrengi=False, enable_planets=False,
    ))
    for pid in ("P1", "P2"):
        player = Player(id=pid, name=pid, agent_kind="external", sector_id=1, credits=25_000)
        player.alignment = 20
        player.experience = 40
        universe.players[pid] = player
        universe.sectors[1].occupant_ids.append(pid)
    return universe


def _join(universe, pid: str, **args):
    return apply_action(universe, pid, Action(kind=ActionKind.CORP_JOIN, args=args))


def test_breakin_alignment_stays_zero_until_the_profile(monkeypatch) -> None:
    universe = _corp()
    assert apply_action(
        universe, "P1", Action(kind=ActionKind.CORP_CREATE, args={"ticker": "XYZ", "name": "Ex"})
    ).ok
    assert apply_action(
        universe, "P1", Action(kind=ActionKind.CORP_SET_PASSWORD, args={"password": "Zx9"})
    ).ok
    before = universe.players["P2"].alignment
    exp = universe.players["P2"].experience
    assert _join(universe, "P2", ticker="XYZ", password="nope").error == "wrong password"
    assert universe.players["P2"].alignment == before
    assert universe.players["P2"].experience == exp

    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    live = _corp()
    assert apply_action(
        live, "P1", Action(kind=ActionKind.CORP_CREATE, args={"ticker": "XYZ", "name": "Ex"})
    ).ok
    assert apply_action(
        live, "P1", Action(kind=ActionKind.CORP_SET_PASSWORD, args={"password": "Zx9"})
    ).ok
    assert K.CORP_BREAKIN_ALIGN_MODE == "legacy"
    assert K.CORP_BREAKIN_ALIGN_LOSS == 0
    start = live.players["P2"].alignment
    experience = live.players["P2"].experience
    assert _join(live, "P2", ticker="XYZ", password="nope").error == "wrong password"
    assert live.players["P2"].alignment == start - 1
    assert live.players["P2"].experience == experience
    again = _join(live, "P2", ticker="XYZ", password="still-wrong")
    assert again.error == "one break-in attempt per day"
    assert live.players["P2"].alignment == start - 1
    tick_day(live)
    assert live.players["P2"].corp_breakins_today == 0
    assert _join(live, "P2", ticker="XYZ", password="nope").error == "wrong password"
    assert live.players["P2"].alignment == start - 2


def test_manual_names_the_three_switches() -> None:
    page = render("Galaxy War Command")
    assert "FedSpace fighter protection: The v3.11 profile turns this on. In this process it is off." in page
    assert "FedSpace tow limit: The v3.11 profile turns this on. In this process it is off." in page
    assert "Corp break-in alignment: The v3.11 profile turns this on. In this process it is off." in page
    assert "A ship with more than 98 fighters is towed." in page


def test_sources_are_read_as_utf8() -> None:
    profile = (ROOT / "docs/plans/v311-profile-v1.md").read_text(encoding="utf-8")
    assert "## The switch set (158 helpers)" in profile
    for name in (
        "FEDSAFE_FIGHTER_CAP_MODE",
        "fedsafe_fighter_cap_live",
        "FED_TOW_LIMIT_MODE",
        "fed_tow_limit_live",
        "CORP_BREAKIN_ALIGN_MODE",
        "corp_breakin_align_live",
    ):
        assert f"`{name}`" in profile
    formulas = (
        ROOT / "docs/reference/tw2002/cabal_strategy_site/formulas.html"
    ).read_text(encoding="utf-8")
    assert "one time per extern" in formulas
    bible = (
        ROOT / "docs/reference/tw2002/stardock_manuals_and_text_docs/TWBible_original_v1x.txt"
    ).read_text(encoding="utf-8")
    assert "over 50 fighters" in bible
