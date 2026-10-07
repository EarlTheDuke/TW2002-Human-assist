"""Focused corp-bot scenes. No LLM. Prints corp_bots_scenario_lab: PASS."""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.agents import corp_brain
from tw2k.agents.seat_brain import SeatBrain
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, build_observation, generate_universe
from tw2k.engine.models import Player, Ship, ShipClass


def _seat(u, pid, name, credits, alignment=100, hull=ShipClass.MERCHANT_CRUISER):
    player = Player(
        id=pid, name=name, sector_id=1, credits=credits, alignment=alignment,
        ship=Ship(ship_class=hull, fighters=40, shields=10, holds=20),
    )
    u.players[pid] = player
    if pid not in u.sectors[1].occupant_ids:
        u.sectors[1].occupant_ids.append(pid)
    return player


def _act(u, brain, pid):
    obs = build_observation(u, pid).model_dump(mode="json")
    action = brain.decide(obs)
    kind = ActionKind(action["kind"])
    result = apply_action(u, pid, Action(kind=kind, args=action.get("args") or {}))
    return action, result


def main() -> int:
    saved = K.BOT_CORP_POLICY
    K.BOT_CORP_POLICY = "pair"
    corp_brain.configure(["P1", "P2"], seed=59)
    try:
        u = generate_universe(GameConfig(seed=59, universe_size=80, max_days=3, enable_ferrengi=False))
        p1 = _seat(u, "P1", "Ada", 80_000, alignment=200)
        p2 = _seat(u, "P2", "Bex", 20_000, alignment=-40)
        brains = {"P1": SeatBrain(), "P2": SeatBrain()}
        thoughts: list[str] = []
        for _ in range(8):
            for pid in ("P1", "P2"):
                action, result = _act(u, brains[pid], pid)
                thoughts.append(str(action.get("thought") or ""))
                if not result.ok and str(action["kind"]).startswith("corp_"):
                    raise SystemExit(f"{pid} {action['kind']} refused: {result.error}")
            if p1.corp_ticker and p2.corp_ticker:
                break
        if not p1.corp_ticker or p1.corp_ticker != p2.corp_ticker:
            raise SystemExit("the pair did not form a corp on day 1")
        secret = corp_brain.password_for(p1.corp_ticker)
        blob = "\n".join(thoughts) + brains["P1"].mem.dump() + brains["P2"].mem.dump()
        if secret in blob:
            raise SystemExit("the password leaked into a thought or the seat memory")

        p1.ship.ship_class = ShipClass.INTERDICTOR_CRUISER
        p1.credits = 200_000
        p2.ship.ship_class = ShipClass.CARGOTRAN
        p2.credits = 21_300
        brains["P1"].mem.corp_transfer_day = -1
        action, result = _act(u, brains["P1"], "P1")
        if action["kind"] != "corp_transfer" or not result.ok:
            raise SystemExit(f"expected a credit hand-off, got {action['kind']} {result.error}")
        if int(action["args"]["qty"]) != 41_000:
            raise SystemExit(f"hand-off was {action['args']['qty']}, wanted 41000")

        p1.ship.ship_class = ShipClass.INTERDICTOR_CRUISER
        p2.ship.ship_class = ShipClass.INTERDICTOR_CRUISER
        p1.credits = 150_000
        p1.alignment = 200
        p2.alignment = -200
        brains["P1"].mem.corp_transfer_day = -1
        action, result = _act(u, brains["P1"], "P1")
        if action["kind"] != "corp_transfer" or int(action["args"]["qty"]) != 50_000 or not result.ok:
            raise SystemExit(f"expected the tax excess, got {action}")

        refused = apply_action(u, "P2", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": "corporate_flagship"}))
        if refused.ok or refused.error != "only a C.E.O. may buy a Corporate FlagShip":
            raise SystemExit(f"non-C.E.O. buy was {refused.error}")
        print("corp_bots_scenario_lab: PASS")
        return 0
    finally:
        K.BOT_CORP_POLICY = saved
        corp_brain.clear()


if __name__ == "__main__":
    raise SystemExit(main())
