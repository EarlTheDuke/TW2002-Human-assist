"""N2/N3 lay mines and defensive fighters on owned-planet sectors."""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.agents.deploy_brain import lay_due, mine_spend_ok, seat_may_deploy
from tw2k.agents.seat_brain import SeatBrain, SeatMemory, View


def _obs(
    *,
    here: int = 50,
    day: int = 5,
    armid: int = 5,
    limpet: int = 0,
    fighters: int = 80,
    home: int | None = 50,
    own_sector: int | None = 50,
    deploy_ok: bool = True,
) -> dict:
    legal = []
    if deploy_ok:
        legal.append({
            "kind": "deploy_mines",
            "legal": True,
            "params": {
                "kind": {"choices": ["armid", "limpet"]},
                "qty": {"max_by": {"armid": 5, "limpet": 5}},
            },
        })
        legal.append({
            "kind": "deploy_fighters",
            "legal": True,
            "params": {
                "qty": {"max": 50},
                "mode": {"choices": ["defensive", "offensive", "toll"]},
            },
        })
    planets = []
    if own_sector is not None:
        planets.append({"id": 1, "sector_id": own_sector, "owner_id": "P1"})
    return {
        "self_id": "P1",
        "credits": 80_000,
        "net_worth": 200_000,
        "day": day,
        "sector": {"id": here, "planets": planets, "occupants": ["P1"], "fighter_group": {}},
        "ship": {
            "class": "merchant_cruiser",
            "fighters": fighters,
            "mines": {"armid": armid, "limpet": limpet},
        },
        "owned_planets": planets,
        "legal_actions": legal,
        "known_warps": {here: [here + 1], here + 1: [here]},
        "trade_summary": {"total_profit_cr": 500_000},
        "home_sector": home,
    }


def _brain(*, n3: bool = True) -> SeatBrain:
    brain = SeatBrain(feed_organics=not n3, value_allocator=n3)
    brain.mem = SeatMemory()
    brain.mem.home_sector = 50
    brain.mem.tavern_income = 500_000
    return brain


def test_bd1_mode(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_DEPLOY_MODE", "legacy")
    brain = _brain()
    assert brain._maybe_bots_deploy(View(_obs())) is None


def test_bd2_skill() -> None:
    assert seat_may_deploy("N1") is False
    assert seat_may_deploy("N2") and seat_may_deploy("N3")
    brain = SeatBrain(feed_organics=False, value_allocator=False)
    brain.mem = SeatMemory()
    brain.mem.home_sector = 50
    assert brain._maybe_bots_deploy(View(_obs())) is None


def test_bd3_lay_armids_at_own(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_DEPLOY_MODE", "tw2002")
    brain = _brain()
    act = brain._maybe_bots_deploy(View(_obs(armid=5)))
    assert act is not None and act["kind"] == "deploy_mines"
    assert act["args"]["kind"] == "armid"


def test_bd4_lay_limpets(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_DEPLOY_MODE", "tw2002")
    brain = _brain()
    act = brain._maybe_bots_deploy(View(_obs(armid=0, limpet=4)))
    assert act is not None and act["args"]["kind"] == "limpet"


def test_bd5_fighter_floor(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_DEPLOY_MODE", "tw2002")
    monkeypatch.setattr(K, "BOT_DEPLOY_FIGHTER_FLOOR", 10)
    brain = _brain()
    act = brain._maybe_bots_deploy(View(_obs(armid=0, limpet=0, fighters=40)))
    assert act is not None and act["kind"] == "deploy_fighters"
    assert act["args"]["mode"] == "defensive"


def test_bd13_msl_own_planet_still_lays(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_DEPLOY_MODE", "tw2002")
    brain = _brain()
    obs = _obs(armid=5)
    obs["sector"]["is_msl"] = True
    act = brain._maybe_bots_deploy(View(obs))
    assert act is not None and act["kind"] == "deploy_mines"


def test_bd6_gap() -> None:
    assert lay_due(last_day=5, day=5, gap_days=1) is False
    assert lay_due(last_day=4, day=5, gap_days=1) is True
    assert lay_due(last_day=-1, day=1, gap_days=1) is True


def test_bd7_spend_pct() -> None:
    # 5% of 10_000 is 500.
    assert mine_spend_ok(spent=0, cost=500, profit=10_000, pct=5) is True
    assert mine_spend_ok(spent=400, cost=200, profit=10_000, pct=5) is False
    assert mine_spend_ok(spent=0, cost=1, profit=0, pct=5) is False


def test_bd8_plot_when_away(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_DEPLOY_MODE", "tw2002")
    brain = _brain()
    brain.mem.deploy_day = -1
    obs = _obs(here=20, armid=5, own_sector=50, home=50)
    obs["known_warps"] = {20: [50], 50: [20]}
    obs["legal_actions"].extend([
        {"kind": "plot_course", "legal": True, "params": {"target": {"choices": [50]}}},
        {"kind": "warp", "legal": True, "params": {"target": {"choices": [50]}}, "turn_cost": 1},
    ])
    obs["turns_remaining"] = 40
    act = brain._maybe_bots_deploy(View(obs))
    assert act is not None and act["kind"] in ("plot_course", "warp")


def test_bd9_n1_skips(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_DEPLOY_MODE", "tw2002")
    brain = SeatBrain(feed_organics=False, value_allocator=False)
    brain.mem = SeatMemory()
    brain.mem.home_sector = 50
    assert brain._maybe_bots_deploy(View(_obs())) is None


def test_bd10_qty_cap(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_DEPLOY_MODE", "tw2002")
    monkeypatch.setattr(K, "BOT_DEPLOY_MINE_QTY", 3)
    brain = _brain()
    act = brain._maybe_bots_deploy(View(_obs(armid=10)))
    assert act is not None and act["args"]["qty"] == 3


def test_bd11_docs_name_flag() -> None:
    from pathlib import Path
    text = (Path(__file__).resolve().parents[1] / "docs/playtests/bots/BOTS_DEPLOY_DEFENSES.md").read_text(encoding="utf-8")
    assert "BOTS_DEPLOY_MODE" in text and "5%" in text


def test_bd12_spend_tracks(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_DEPLOY_MODE", "tw2002")
    brain = _brain()
    brain.mem.deploy_mine_spent = 0
    brain.mem.tavern_income = 10_000
    assert brain._mine_spend_allows(500) is True
    brain._note_mine_spend(500)
    assert brain.mem.deploy_mine_spent == 500
    assert brain._mine_spend_allows(1) is False
