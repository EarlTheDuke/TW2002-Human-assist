"""NOTE 129. Grimy prices from the 19 Oct day-1 screen.

The numbers are read from docs/playtests/twgs-live/stardock-menus.txt, section
"Grimy, this visit, declined". Topic trader stays the stored trace. Topic
stardock and the paid password follow that screen when GRIMY_TIP_MODE is live
or v311, or when either profile is on. The underground second ask (2,500 then
600) and PASSWORD as its own topic (1,500) are not charged.
"""

from __future__ import annotations

import re
from pathlib import Path

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, Ship
from tw2k.engine.observation import build_observation
from tw2k.engine.tavern import note_dock

CAPTURE = Path("docs/playtests/twgs-live/stardock-menus.txt")


def _section() -> str:
    text = CAPTURE.read_text(encoding="utf-8")
    marker = "Grimy, this visit, declined:"
    assert marker in text
    return text.split(marker, 1)[1]


def _money(raw: str) -> int:
    return int(raw.replace(",", ""))


def _capture() -> dict[str, int | str]:
    section = _section()
    stardock = re.search(r"STARDOCK: (Would ye pay me (\d+) credits for it\?)", section)
    underground = re.search(
        r"UNDERGROUND: ([\d,]+) credits, then on the next ask ([\d,]+) credits\.",
        section,
    )
    topic = re.search(r"PASSWORD as a topic: ([\d,]+) credits\.", section)
    follow = re.search(
        r"The password will cost ya (\d+), will ye pay\?\nPaid \1\. Credits (\d+), then (\d+)\.",
        section,
    )
    assert stardock and underground and topic and follow
    paid = int(follow.group(1))
    before = int(follow.group(2))
    after = int(follow.group(3))
    assert before - paid == after
    return {
        "stardock_line": stardock.group(1),
        "stardock": int(stardock.group(2)),
        "underground_first": _money(underground.group(1)),
        "underground_second": _money(underground.group(2)),
        "password_topic": _money(topic.group(1)),
        "password_paid": paid,
        "credits_before": before,
        "credits_after": after,
    }


def _world():
    universe = generate_universe(
        GameConfig(seed=129, universe_size=20, max_days=5, enable_planets=False, enable_ferrengi=False)
    )
    for pid, name in (("A", "Ada"), ("B", "Bea")):
        player = Player(id=pid, name=name, ship=Ship(), credits=300, sector_id=int(K.STARDOCK_SECTOR))
        universe.players[pid] = player
        sector = universe.sectors[int(K.STARDOCK_SECTOR)]
        if pid not in sector.occupant_ids:
            sector.occupant_ids.append(pid)
    return universe


def _ask(universe, topic: str, **args):
    return apply_action(universe, "A", Action(kind=ActionKind.GRIMY_ASK, args={"topic": topic, **args}))


def _legacy(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    monkeypatch.setattr(K, "GRIMY_TIP_MODE", "legacy")


def test_capture_lines_are_the_day_1_screen() -> None:
    got = _capture()
    assert got["stardock_line"] == "Would ye pay me 23 credits for it?"
    assert got["stardock"] == 23
    assert got["underground_first"] == 2_500
    assert got["underground_second"] == 600
    assert got["password_topic"] == 1_500
    assert got["password_paid"] == 160
    assert got["credits_before"] == 300
    assert got["credits_after"] == 140
    assert got["stardock_line"] == K.GRIMY_STARDOCK_TIP_LINE
    assert got["stardock"] == K.GRIMY_STARDOCK_TIP_COST
    assert got["password_paid"] == K.GRIMY_PASSWORD_PAID_COST


def test_switch_defaults_legacy_and_one_does_not_flip(monkeypatch) -> None:
    _legacy(monkeypatch)
    assert K.GRIMY_TIP_MODE == "legacy"
    assert K.GRIMY_TRACE_COST == 3_000
    assert K.GRIMY_PASSWORD_COST == 2_000
    assert K.grimy_tips_live() is False
    assert K.grimy_trace_cost() == K.GRIMY_TRACE_COST
    assert K.grimy_password_cost() == K.GRIMY_PASSWORD_COST
    monkeypatch.setattr(K, "GRIMY_TIP_MODE", "1")
    assert K.grimy_tips_live() is False
    monkeypatch.setattr(K, "GRIMY_TIP_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.GRIMY_TIP_MODE == "legacy"
    assert K.grimy_tips_live() is True
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    assert K.grimy_tips_live() is True
    assert K.V311_PROFILE_HELPERS["grimy_tips_live"][0] == "GRIMY_TIP_MODE"


def test_legacy_keeps_the_stored_trace_and_password(monkeypatch) -> None:
    _legacy(monkeypatch)
    screen = _capture()
    universe = _world()
    buyer = universe.players["A"]
    note_dock(universe.players["B"], 4)
    short = _ask(universe, "trader", target="B")
    assert short.ok is False
    assert buyer.credits == int(screen["credits_before"])
    buyer.credits = 50_000
    assert _ask(universe, "trader", target="B").ok
    assert buyer.credits == 50_000 - int(K.GRIMY_TRACE_COST)
    buyer.credits = 10_000
    assert _ask(universe, "underground").ok
    assert buyer.credits == 10_000 - int(K.GRIMY_PASSWORD_COST)
    assert buyer.ug_password_known is True
    assert int(K.GRIMY_PASSWORD_COST) != int(screen["password_paid"])
    assert int(K.GRIMY_PASSWORD_COST) not in (
        int(screen["underground_first"]),
        int(screen["underground_second"]),
        int(screen["password_topic"]),
    )
    buyer.credits = 300
    before = buyer.credits
    shrugged = _ask(universe, "stardock")
    assert shrugged.ok
    assert buyer.credits == before
    assert any(ev.payload.get("answer") == "never heard of it" for ev in universe.events)
    choices = next(row for row in legal_actions(universe, "A") if row.kind == "grimy_ask")
    assert "stardock" not in choices.params["topic"]["choices"]
    assert "stardock" not in choices.params["cost_by"]


def test_live_charges_the_stardock_tip_and_the_paid_password(monkeypatch) -> None:
    _legacy(monkeypatch)
    monkeypatch.setattr(K, "GRIMY_TIP_MODE", "live")
    screen = _capture()
    universe = _world()
    buyer = universe.players["A"]
    note_dock(universe.players["B"], 4)
    buyer.credits = 50_000
    assert _ask(universe, "trader", target="B").ok
    assert buyer.credits == 50_000 - int(K.GRIMY_TRACE_COST)
    assert int(K.grimy_trace_cost()) != int(screen["stardock"])

    buyer.credits = int(screen["credits_before"])
    assert _ask(universe, "stardock").ok
    assert buyer.credits == int(screen["credits_before"]) - int(screen["stardock"])
    assert buyer.ug_password_known is False
    tip = next(ev for ev in universe.events if ev.payload.get("topic") == "stardock")
    assert tip.summary == screen["stardock_line"]
    assert tip.payload["answer"] == screen["stardock_line"]
    assert tip.payload["cost"] == screen["stardock"]

    buyer.credits = int(screen["credits_before"])
    assert _ask(universe, "underground").ok
    assert buyer.credits == int(screen["credits_after"])
    assert buyer.ug_password_known is True
    paid = int(screen["credits_before"]) - buyer.credits
    assert paid == int(screen["password_paid"])
    assert paid != int(screen["underground_first"])
    assert paid != int(screen["underground_second"])
    assert paid != int(screen["password_topic"])

    held = buyer.credits
    again = _ask(universe, "underground")
    assert again.ok is False
    assert again.error == "you already know it"
    assert buyer.credits == held

    buyer.ug_password_known = False
    buyer.credits = int(screen["credits_before"])
    assert _ask(universe, "mafia").ok
    assert buyer.credits == int(screen["credits_before"]) - int(screen["password_paid"])

    buyer.ug_password_known = False
    buyer.credits = int(screen["credits_before"])
    word = _ask(universe, "password")
    assert word.ok
    assert buyer.credits == int(screen["credits_before"])
    assert buyer.ug_password_known is False
    assert any(
        ev.payload.get("topic") == "password" and ev.payload.get("answer") == "never heard of it"
        for ev in universe.events
    )

    broke = universe.players["B"]
    broke.credits = int(screen["stardock"]) - 1
    broke.sector_id = int(K.STARDOCK_SECTOR)
    short = apply_action(universe, "B", Action(kind=ActionKind.GRIMY_ASK, args={"topic": "stardock"}))
    assert short.ok is False
    assert broke.credits == int(screen["stardock"]) - 1

    row = next(item for item in legal_actions(universe, "A") if item.kind == "grimy_ask")
    assert row.params["cost_by"]["stardock"] == screen["stardock"]
    assert row.params["cost_by"]["underground"] == screen["password_paid"]
    assert row.params["cost_by"]["trader"] == int(K.GRIMY_TRACE_COST)
    assert "stardock" in row.params["topic"]["choices"]
    prices = build_observation(universe, "A").tavern["prices"]
    assert prices["stardock"] == screen["stardock"]
    assert prices["password"] == screen["password_paid"]
    assert prices["trace"] == int(K.GRIMY_TRACE_COST)


def test_v311_mode_word_matches_the_live_prices(monkeypatch) -> None:
    _legacy(monkeypatch)
    monkeypatch.setattr(K, "GRIMY_TIP_MODE", "v311")
    screen = _capture()
    assert K.grimy_password_cost() == screen["password_paid"]
    assert K.grimy_tips_live() is True
    universe = _world()
    assert _ask(universe, "underground").ok
    assert universe.players["A"].credits == int(screen["credits_after"])
