"""rob-steal-v1: robbing and stealing at ports (docs/playtests/ports/ROB_STEAL.md)."""

from __future__ import annotations

from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.agents.seat_acceptance import validate_action
from tw2k.agents.seat_brain import SeatBrain
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, build_observation, generate_universe
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, PortClass, Ship
from tw2k.engine.rob_steal import max_rob_credits, max_steal_holds
from tw2k.engine.runner import tick_day

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "playtests" / "ports" / "ROB_STEAL.md"


@pytest.fixture
def legacy(monkeypatch):
    monkeypatch.setattr(K, "ROB_MODE", "legacy")


@pytest.fixture
def tw(monkeypatch):
    monkeypatch.setattr(K, "ROB_MODE", "tw2002")


def test_rules_doc_lists_every_row_with_a_mark() -> None:
    text = DOC.read_text(encoding="utf-8")
    for row in [f"r{n}" for n in range(1, 26)]:
        assert f"| {row} |" in text, f"row {row} missing"
    for word in ("CONFIRMED", "SOURCE-CONFLICT", "UNVERIFIED", "Deliberate differences",
                 "ROB_MODE", "fake bust", "MBBS", "StarDock", "Delivered"):
        assert word.lower() in text.lower(), word


def test_switch_defaults() -> None:
    assert K.ROB_MODE == "tw2002" and K.rob_tw2002()
    assert K.ROB_MIN_ALIGNMENT == -100
    assert K.ROB_CREDIT_FACTOR == 6 and K.STEAL_HOLD_DIVISOR == 21
    assert K.ROB_BUST_DENOMINATOR == 50
    assert max_rob_credits(10_000) == 60_000
    assert max_steal_holds(3_500) == 3_500 // 21


def _crime_world(seed: int = 4101):
    from tw2k.engine.rob_steal import seed_port_credits
    u = generate_universe(GameConfig(seed=seed, universe_size=80, enable_ferrengi=False, enable_planets=False))
    sid = next(
        s for s in sorted(u.sectors)
        if s > 10 and u.sectors[s].port is not None
        and u.sectors[s].port.class_id.value in range(1, 8)
    )
    port = u.sectors[sid].port
    if int(port.credits) <= 1_000:
        port.credits = max(seed_port_credits(port), 50_000)
    # Ensure steal stock
    for c in list(port.stock):
        port.stock[c].current = max(int(port.stock[c].current), 80)
    u.players["R"] = Player(
        id="R", name="Red", ship=Ship(holds=50, fighters=20), sector_id=sid,
        credits=5_000, alignment=-250, experience=3_000,
    )
    u.sectors[sid].occupant_ids.append("R")
    u.players["R"].known_sectors.add(sid)
    u.players["B"] = Player(
        id="B", name="Blue", ship=Ship(holds=40, fighters=20), sector_id=sid,
        credits=5_000, alignment=200, experience=3_000,
    )
    u.sectors[sid].occupant_ids.append("B")
    return u, sid, port


# --- planted bugs (legal list + handler) --------------------------------------

def test_plant_legacy_hides_rob_and_steal(legacy) -> None:
    """Plant: ROB_MODE legacy still offers a working rob."""
    u, sid, port = _crime_world()
    kinds = {a.kind for a in legal_actions(u, "R")}
    assert "rob" not in kinds and "steal" not in kinds
    r = apply_action(u, "R", Action(kind=ActionKind.ROB, args={"amount": 100}))
    assert r.ok is False and "legacy" in (r.error or "")


def test_plant_good_alignment_cannot_rob(tw) -> None:
    """Plant: alignment > -100 can still rob."""
    u, sid, port = _crime_world()
    las = {a.kind: a for a in legal_actions(u, "B")}
    assert las["rob"].legal is False
    assert "alignment" in (las["rob"].reason or "")
    r = apply_action(u, "B", Action(kind=ActionKind.ROB, args={"amount": 100}))
    assert r.ok is False


def test_plant_stardock_excluded(tw) -> None:
    """Plant: StarDock accepts rob."""
    u, sid, port = _crime_world()
    # Move red to StarDock
    u.sectors[sid].occupant_ids.remove("R")
    u.players["R"].sector_id = 1
    u.sectors[1].occupant_ids.append("R")
    las = {a.kind: a for a in legal_actions(u, "R")}
    assert las["rob"].legal is False
    assert "StarDock" in (las["rob"].reason or "")
    r = apply_action(u, "R", Action(kind=ActionKind.ROB, args={"amount": 100}))
    assert r.ok is False and "StarDock" in (r.error or "")


def test_plant_class0_excluded(tw) -> None:
    """Plant: FEDERAL / Class 0 ports accept steal."""
    u = generate_universe(GameConfig(seed=4102, universe_size=40, enable_ferrengi=False, enable_planets=False))
    fed = next(s for s in sorted(u.sectors) if u.sectors[s].port and u.sectors[s].port.class_id == PortClass.FEDERAL)
    u.players["R"] = Player(
        id="R", name="Red", ship=Ship(holds=40), sector_id=fed,
        credits=1_000, alignment=-200, experience=2_000,
    )
    u.sectors[fed].occupant_ids.append("R")
    las = {a.kind: a for a in legal_actions(u, "R")}
    assert las["steal"].legal is False
    assert "Class 0" in (las["steal"].reason or "") or "Federal" in (las["steal"].reason or "")


def test_plant_over_cap_always_busts(tw, monkeypatch) -> None:
    """Plant: over-cap rob succeeds when RNG is lucky."""
    u, sid, port = _crime_world()
    # Force chance roll to never natural-bust; over-cap must still bust.
    monkeypatch.setattr(u.rng, "randrange", lambda n: 1)
    before_xp = u.players["R"].experience
    before_holds = u.players["R"].ship.holds
    cap = max_rob_credits(before_xp)
    amount = cap + 500
    r = apply_action(u, "R", Action(kind=ActionKind.ROB, args={"amount": amount}))
    assert r.ok is True
    assert u.players["R"].experience == before_xp - before_xp // 10
    assert port.bust_player_id == "R"
    # holds lost = 1% of amount
    expect_lost = min(before_holds - 1, amount // 100)
    assert u.players["R"].ship.holds == before_holds - expect_lost


def test_plant_fake_bust_same_port(tw, monkeypatch) -> None:
    """Plant: second successful crime at same port is allowed / clears bust list."""
    u, sid, port = _crime_world()
    monkeypatch.setattr(u.rng, "randrange", lambda n: 1)  # never chance-bust
    r1 = apply_action(u, "R", Action(kind=ActionKind.ROB, args={"amount": 100}))
    assert r1.ok and u.players["R"].last_crime_sector_id == sid
    xp_after = u.players["R"].experience
    r2 = apply_action(u, "R", Action(kind=ActionKind.ROB, args={"amount": 50}))
    assert r2.ok
    assert u.players["R"].experience == xp_after - xp_after // 10
    # Fake bust must NOT write the bust list
    assert port.bust_player_id is None


def test_plant_bust_blocks_trade_until_clear(tw, monkeypatch) -> None:
    """Plant: after a real bust, trade still works; daily clear forgotten."""
    u, sid, port = _crime_world()
    monkeypatch.setattr(u.rng, "randrange", lambda n: 0)  # always chance-bust
    r = apply_action(u, "R", Action(kind=ActionKind.ROB, args={"amount": 100}))
    assert r.ok and port.bust_player_id == "R"
    las = {a.kind: a for a in legal_actions(u, "R")}
    assert las["trade"].legal is False
    assert "busted" in (las["trade"].reason or "")
    tr = apply_action(u, "R", Action(kind=ActionKind.TRADE, args={
        "side": "buy", "commodity": next(iter(port.stock)).value, "qty": 1,
    }))
    assert tr.ok is False and "busted" in (tr.error or "")
    tick_day(u)
    assert port.bust_player_id is None
    las2 = {a.kind: a for a in legal_actions(u, "R")}
    # May still be illegal for stock/credits reasons, but not bust
    if not las2["trade"].legal:
        assert "busted" not in (las2["trade"].reason or "")


def test_plant_steal_success_moves_stock_and_align(tw, monkeypatch) -> None:
    """Plant: steal success leaves stock and alignment unchanged."""
    u, sid, port = _crime_world()
    monkeypatch.setattr(u.rng, "randrange", lambda n: 1)
    c = next(c for c, st in port.stock.items() if st.current >= 10)
    before_stock = int(port.stock[c].current)
    before_align = int(u.players["R"].alignment)
    before_xp = int(u.players["R"].experience)
    before_cargo = int(u.players["R"].ship.cargo.get(c, 0))
    r = apply_action(u, "R", Action(kind=ActionKind.STEAL, args={"commodity": c.value, "qty": 10}))
    assert r.ok
    assert int(port.stock[c].current) == before_stock - 10
    assert int(u.players["R"].ship.cargo.get(c, 0)) == before_cargo + 10
    assert int(u.players["R"].alignment) < before_align
    assert int(u.players["R"].experience) > before_xp


def test_plant_steal_bust_holds_nine_percent(tw, monkeypatch) -> None:
    """Plant: steal bust uses rob's 1%-of-credits hold loss instead of 9% of qty."""
    u, sid, port = _crime_world()
    monkeypatch.setattr(u.rng, "randrange", lambda n: 0)
    before_holds = u.players["R"].ship.holds
    qty = 40
    r = apply_action(u, "R", Action(kind=ActionKind.STEAL, args={
        "commodity": next(c for c, st in port.stock.items() if st.current >= qty).value,
        "qty": qty,
    }))
    assert r.ok
    expect = max(0, (qty * 9) // 100)
    assert u.players["R"].ship.holds == before_holds - expect


def test_plant_another_red_real_bust_clears_first(tw, monkeypatch) -> None:
    """Plant: second red's real bust leaves the first still blocked."""
    u, sid, port = _crime_world()
    monkeypatch.setattr(u.rng, "randrange", lambda n: 0)
    apply_action(u, "R", Action(kind=ActionKind.ROB, args={"amount": 100}))
    assert port.bust_player_id == "R"
    # Second red
    u.players["R2"] = Player(
        id="R2", name="Red2", ship=Ship(holds=40), sector_id=sid,
        credits=1_000, alignment=-300, experience=2_000,
    )
    u.sectors[sid].occupant_ids.append("R2")
    apply_action(u, "R2", Action(kind=ActionKind.ROB, args={"amount": 80}))
    assert port.bust_player_id == "R2"
    las = {a.kind: a for a in legal_actions(u, "R")}
    assert las["rob"].legal is True or "busted" not in (las["rob"].reason or "")


def test_seat_brains_do_not_need_to_rob(tw) -> None:
    """Brains stay legal (rejected 0) without choosing rob/steal."""
    u, sid, port = _crime_world()
    obs = build_observation(u, "R").model_dump(mode="json")
    a = SeatBrain().decide(obs)
    assert validate_action(obs, a) == []
    # Not required to rob; if they somehow do, it must still be legal.
    if a["kind"] in ("rob", "steal"):
        assert any(x.kind == a["kind"] and x.legal for x in legal_actions(u, "R"))
