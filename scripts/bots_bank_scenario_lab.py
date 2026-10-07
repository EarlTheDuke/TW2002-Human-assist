"""Scripted checks for the bot bank. No LLM and no full match.

Each line is one case from the slice. Exit 0 when every case passes.
"""

from __future__ import annotations

import asyncio
import sys

from tw2k.agents.bank_brain import away_reserve, risk_flags
from tw2k.agents.heuristic import HeuristicAgent
from tw2k.agents.seat_acceptance import synthetic_obs
from tw2k.agents.seat_brain import SeatBrain
from tw2k.engine.observation import Observation


def _la(obs, kind, legal=True, **params):
    obs["legal_actions"] = [row for row in obs["legal_actions"] if row["kind"] != kind]
    obs["legal_actions"].append({
        "kind": kind, "legal": legal, "reason": None, "detail": "precise", "params": params,
    })
    return obs


def _check(name: str, ok: bool, detail: str) -> bool:
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
    return ok


def _day1() -> bool:
    brain = SeatBrain()
    obs = synthetic_obs(sector=1, credits=20_000, ship_class="cargotran", day=1)
    obs["bank_balance"] = 0
    obs["net_worth"] = 20_000
    obs["alignment"] = 100
    _la(obs, "buy_equip", item={"choices": [], "unit_price_by": {}})
    _la(obs, "bank_deposit", max_amount=20_000, balance=0, room=500_000)
    action = brain.decide(obs)
    amount = int((action.get("args") or {}).get("amount") or 0) if action["kind"] == "bank_deposit" else -1
    return _check("day1", action["kind"] != "bank_deposit" or amount <= 10_000,
                  f"kind={action['kind']} amount={amount}")


def _tax() -> bool:
    brain = SeatBrain()
    obs = synthetic_obs(sector=1, credits=400_000, ship_class="cargotran", day=3)
    obs["alignment"] = 50
    obs["bank_balance"] = 0
    obs["net_worth"] = 400_000
    _la(obs, "buy_equip", item={"choices": [], "unit_price_by": {}})
    _la(obs, "bank_deposit", max_amount=400_000, balance=0, room=500_000)
    saved = SeatBrain._away_cash
    SeatBrain._away_cash = lambda self, v: 150_000  # noqa: SLF001
    try:
        action = brain.decide(obs)
    finally:
        SeatBrain._away_cash = saved
    left = 400_000 - int(action["args"]["amount"]) if action["kind"] == "bank_deposit" else None
    return _check("tax-line", action["kind"] == "bank_deposit" and left == 100_000,
                  f"kind={action['kind']} left={left}")


def _pod() -> bool:
    brain = SeatBrain()
    obs = synthetic_obs(sector=1, credits=0, ship_class="escape_pod", holds=5, day=3)
    obs["bank_balance"] = 150_000
    obs["net_worth"] = 150_000
    _la(obs, "buy_ship", ship_class={
        "choices": ["cargotran", "scout_marauder"],
        "net_cost_by": {"cargotran": 40_000, "scout_marauder": 5_000},
    })
    _la(obs, "bank_withdraw", max_amount=150_000, balance=150_000)
    action = brain.decide(obs)
    return _check("pod-before-buy", action["kind"] == "bank_withdraw",
                  f"kind={action['kind']}")


def _h_pod() -> bool:
    obs = Observation(
        day=3, tick=1, max_days=10, finished=False,
        self_id="P6", self_name="H", credits=0, alignment=100,
        turns_remaining=40, turns_per_day=40,
        ship={"class": "escape_pod", "fighters": 0, "cargo": {}, "cargo_free": 0, "holds": 5},
        corp_ticker=None, planet_landed=None, scratchpad="",
        sector={"id": 1, "ferrengi": []},
        adjacent=[{"id": 2, "known": True}],
        known_ports=[], other_players=[], inbox=[], recent_events=[],
        net_worth=80_000, bank_balance=80_000,
        legal_actions=[
            {"kind": "buy_ship", "legal": True, "params": {"ship_class": {
                "choices": ["cargotran", "scout_marauder"],
                "net_cost_by": {"cargotran": 40_000, "scout_marauder": 0},
            }}},
            {"kind": "bank_withdraw", "legal": True, "params": {"max_amount": 80_000}},
        ],
    )
    act = asyncio.run(HeuristicAgent("P6", "H", seed=1).act(obs))
    return _check("h-pod", act.kind.value == "bank_withdraw" and act.args["amount"] == 60_000,
                  f"kind={act.kind.value} amount={act.args.get('amount')}")


def _treasury() -> bool:
    planet = {"id": 7, "sector_id": 5, "citadel_level": 1, "citadel_target": 1,
              "shields": 10, "origin": "genesis", "colonists": {}}
    obs = synthetic_obs(sector=5, credits=300_000, ship_class="cargotran", day=4, landed=7, planets=[planet])
    obs["bank_balance"] = 500_000
    obs["bank_room"] = 0
    obs["alignment"] = 100
    _la(obs, "deposit_treasury", planet_id={"type": "int", "choices": [7]},
        amount={"type": "int", "min": 1, "max": 300_000})
    brain = SeatBrain()
    first = brain.decide(obs)
    second = brain.decide(obs)
    ok = (first["kind"] == "deposit_treasury" and 200_000 < first["args"]["amount"] < 300_000
          and second["kind"] != "deposit_treasury")
    return _check("treasury-overflow", ok, f"first={first['kind']} second={second['kind']}")


def _risk() -> bool:
    calm = away_reserve(20, [40_000, 40_000, 40_000], 0, owns_fighters=True)
    halved = away_reserve(20, [40_000, 40_000, 40_000], 1, owns_fighters=True)
    flags = risk_flags(days_since_loss=None, ship_class="cargotran", alignment=100,
                       fedsafe=True, threat_hops=1, fighters=100)
    return _check("risk-half", calm == 125_000 and halved == 75_000 and flags == 1,
                  f"calm={calm} half={halved} flags={flags}")


def main() -> int:
    checks = (_day1(), _tax(), _pod(), _h_pod(), _treasury(), _risk())
    print(f"{sum(checks)}/{len(checks)} passed")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
