"""QC follow-ups for rob-steal-v1."""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.actions import ActionKind as AK
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, Ship
from tw2k.engine.rob_steal import max_rob_credits, seed_port_credits
from tw2k.engine.runner import tick_day


def _red_at_trade_port(seed: int = 4201):
    u = generate_universe(
        GameConfig(seed=seed, universe_size=80, enable_ferrengi=False, enable_planets=False)
    )
    sid = next(
        s
        for s in sorted(u.sectors)
        if s > 10 and u.sectors[s].port is not None and u.sectors[s].port.class_id.value in range(1, 8)
    )
    port = u.sectors[sid].port
    if int(port.credits) <= 1_000:
        port.credits = max(seed_port_credits(port), 50_000)
    for c in list(port.stock):
        port.stock[c].current = max(int(port.stock[c].current), 80)
    u.players["R"] = Player(
        id="R",
        name="Red",
        ship=Ship(holds=50, fighters=20),
        sector_id=sid,
        credits=5_000,
        alignment=-250,
        experience=3_000,
    )
    u.sectors[sid].occupant_ids.append("R")
    u.players["R"].known_sectors.add(sid)
    return u, sid, port


def test_steal_dilutes_cost_basis_with_free_loot(monkeypatch) -> None:
    """Stolen units must dilute existing cargo_cost (not keep the paid average)."""
    monkeypatch.setattr(K, "ROB_MODE", "tw2002")
    u, sid, port = _red_at_trade_port()
    monkeypatch.setattr(u.rng, "randrange", lambda n: 1)
    c = next(c for c, st in port.stock.items() if st.current >= 10)
    ship = u.players["R"].ship
    ship.cargo[c] = 10
    ship.cargo_cost[c] = 50.0
    r = apply_action(u, "R", Action(kind=ActionKind.STEAL, args={"commodity": c.value, "qty": 10}))
    assert r.ok, r.error
    assert int(ship.cargo[c]) == 20
    assert abs(float(ship.cargo_cost[c]) - 25.0) < 1e-9, ship.cargo_cost[c]


def test_legacy_harness_verbs_omit_rob_steal() -> None:
    """ROB_MODE legacy: harness /rules must filter rob/steal out of the verb catalog (r25)."""
    from pathlib import Path
    text = Path(__file__).resolve().parents[1].joinpath("src/tw2k/server/harness.py").read_text(encoding="utf-8")
    assert "if not K.rob_tw2002():" in text
    assert 'v not in ("rob", "steal")' in text or "v not in ('rob', 'steal')" in text
    # Enum still names the actions; legacy merely hides them from the advertised catalog.
    assert any(k.value == "rob" for k in AK)


def test_bust_clears_only_on_day_tick(monkeypatch) -> None:
    monkeypatch.setattr(K, "ROB_MODE", "tw2002")
    u, sid, port = _red_at_trade_port()
    monkeypatch.setattr(u.rng, "randrange", lambda n: 0)
    apply_action(u, "R", Action(kind=ActionKind.ROB, args={"amount": 100}))
    assert port.bust_player_id == "R"
    # Mid-day: still blocked
    las = {a.kind: a for a in legal_actions(u, "R")}
    assert las["rob"].legal is False
    tick_day(u)
    assert port.bust_player_id is None


def test_rob_cannot_exceed_vault(monkeypatch) -> None:
    monkeypatch.setattr(K, "ROB_MODE", "tw2002")
    u, sid, port = _red_at_trade_port()
    monkeypatch.setattr(u.rng, "randrange", lambda n: 1)
    port.credits = 250
    before = int(u.players["R"].credits)
    r = apply_action(u, "R", Action(kind=ActionKind.ROB, args={"amount": 10_000}))
    # 10k > exp*6? exp=3000 -> cap 18000, so not over_cap; vault limits take
    assert r.ok, r.error
    assert int(port.credits) == 0
    assert int(u.players["R"].credits) == before + 250


def test_alignment_gate_at_minus_100(monkeypatch) -> None:
    """alignment == -100 is allowed (ROB_MIN_ALIGNMENT <= gate)."""
    monkeypatch.setattr(K, "ROB_MODE", "tw2002")
    u, sid, port = _red_at_trade_port()
    u.players["R"].alignment = -100
    las = {a.kind: a for a in legal_actions(u, "R")}
    assert las["rob"].legal is True, las["rob"].reason
    u.players["R"].alignment = -99
    las = {a.kind: a for a in legal_actions(u, "R")}
    assert las["rob"].legal is False


def test_full_holds_blocks_steal_legality(monkeypatch) -> None:
    monkeypatch.setattr(K, "ROB_MODE", "tw2002")
    u, sid, port = _red_at_trade_port()
    ship = u.players["R"].ship
    # Fill holds
    c = next(iter(port.stock))
    ship.cargo[c] = int(ship.holds)
    las = {a.kind: a for a in legal_actions(u, "R")}
    assert las["steal"].legal is False
    assert "holds" in (las["steal"].reason or "") or "steal" in (las["steal"].reason or "")


def test_exp_zero_over_cap_busts(monkeypatch) -> None:
    monkeypatch.setattr(K, "ROB_MODE", "tw2002")
    u, sid, port = _red_at_trade_port()
    monkeypatch.setattr(u.rng, "randrange", lambda n: 1)  # no chance bust
    u.players["R"].experience = 0
    assert max_rob_credits(0) == 0
    before = u.players["R"].ship.holds
    r = apply_action(u, "R", Action(kind=ActionKind.ROB, args={"amount": 100}))
    assert r.ok
    assert port.bust_player_id == "R"
    assert u.players["R"].ship.holds < before or before == 1


def test_port_credits_not_in_sector_observation(monkeypatch) -> None:
    monkeypatch.setattr(K, "ROB_MODE", "tw2002")
    from tw2k.engine import build_observation

    u, sid, port = _red_at_trade_port()
    port.bust_player_id = "R"
    obs = build_observation(u, "R").model_dump(mode="json")
    sport = obs.get("sector", {}).get("port") or {}
    assert "credits" not in sport
    assert "bust_player_id" not in sport
