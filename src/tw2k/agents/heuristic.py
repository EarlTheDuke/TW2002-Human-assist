"""Rule-based agent for testing and as a fallback when no LLM API key is set.

The heuristic agent implements a competent trade-loop player:
- Find best local buy (cheap at selling-port, rich at buying-port).
- Execute trades until cargo is full, then warp toward the best known buying port.
- If a Ferrengi is in its sector with low aggression, fight; otherwise flee.
- If at StarDock with surplus credits, upgrade ship.

It's not intended to beat an LLM — just to play a valid game.
"""

from __future__ import annotations

import random

from ..engine import Action, ActionKind, Observation
from ..engine.constants import STARDOCK_SECTOR, combat_hull
from .base import BaseAgent


class HeuristicAgent(BaseAgent):
    kind = "heuristic"

    def __init__(self, player_id: str, name: str, seed: int | None = None):
        super().__init__(player_id, name)
        self.rng = random.Random(seed if seed is not None else hash(player_id) & 0xFFFF)
        # Sectors whose fighters this seat retreated from -> day; avoided that day (no ping-pong).
        self._held: dict[int, int] = {}

    async def act(self, obs: Observation) -> Action:
        # Fighters holding the ship must be answered first (ship-combat-core-v1).
        challenge = getattr(obs, "fighter_challenge", None)
        if challenge:
            return self._answer_challenge(obs, challenge)
        # Survival first: ferrengi in sector, low fighters? flee.
        ferr = obs.sector.get("ferrengi", [])
        if ferr:
            top = max(ferr, key=lambda f: f["aggression"])
            if obs.ship["fighters"] > 0 and obs.ship["fighters"] >= top["fighters"] * 1.5:
                return self._attack(top["id"], "Ferrengi looks beatable, lets collect that bounty.")
            return self._flee(obs, f"Ferrengi aggression {top['aggression']} — bail.")

        # In an escape pod: trade it in at StarDock, else fly there (DEATH_ESCAPE_PODS.md d17).
        if str(obs.ship.get("class") or "") == "escape_pod":
            pod = self._leave_pod(obs)
            if pod is not None:
                return pod

        # At StarDock: consider outfitting & upgrading before heading out
        if obs.sector["id"] == 1 and obs.credits > 50_000:
            room = self._legal_max(obs, "buy_equip", "fighters")
            if obs.ship["fighters"] < 500 and obs.credits > 25_000 and room > 0:
                qty = min(200, obs.credits // 50, room)  # never past the hull's cap (a Scout holds less)
                return Action(
                    kind=ActionKind.BUY_EQUIP,
                    args={"item": "fighters", "qty": qty},
                    thought=f"Load up on {qty} fighters before heading out.",
                )

        # At a port with stock: trade
        port = obs.sector.get("port")
        if port and port["class_id"] not in (0, 8):
            # Try selling first (if we have cargo the port buys)
            for commodity in ("equipment", "organics", "fuel_ore"):
                held = obs.ship["cargo"].get(commodity, 0)
                if held > 0 and commodity in port["buys"] and commodity in port["stock"]:
                    entry = port["stock"][commodity]
                    capacity = entry["max"] - entry["current"]
                    qty = min(held, capacity)
                    if qty > 0:
                        return Action(
                            kind=ActionKind.TRADE,
                            args={"commodity": commodity, "qty": qty, "side": "sell"},
                            thought=f"Offloading {qty} {commodity} at {port['code']} for {entry['price']}cr/u.",
                        )
            # Otherwise buy what the port sells, as much as fits, if affordable
            for commodity in ("equipment", "organics", "fuel_ore"):
                if commodity in port["sells"] and commodity in port["stock"]:
                    entry = port["stock"][commodity]
                    unit = entry["price"]
                    holds_free = obs.ship["cargo_free"]
                    qty = min(holds_free, entry["current"], obs.credits // max(1, unit))
                    if qty > 0:
                        return Action(
                            kind=ActionKind.TRADE,
                            args={"commodity": commodity, "qty": qty, "side": "buy"},
                            thought=f"Buying {qty} {commodity} at {port['code']} for {unit}cr/u.",
                        )

        # Move. Prefer adjacent unknown sectors; otherwise adjacent with ports.
        # Never WAIT if we can warp — WAIT-spam clogs the event feed.
        adj = obs.adjacent or []
        adj = [a for a in adj if self._held.get(int(a["id"])) != obs.day] or adj
        if adj and self._short_for_warp(obs):
            return Action(kind=ActionKind.WAIT, thought="Not enough turns left for a warp; waiting for tomorrow.")
        if adj:
            unknown = [a for a in adj if not a.get("known")]
            with_port = [a for a in adj if a.get("port") and a["port"] not in ("FED",)]
            if unknown:
                choice = self.rng.choice(unknown)
                reason = "scouting"
            elif with_port:
                choice = self.rng.choice(with_port)
                reason = "hopping to known port"
            else:
                choice = self.rng.choice(adj)
                reason = "drifting"
            return Action(
                kind=ActionKind.WARP,
                args={"target": choice["id"]},
                thought=f"Warping to {choice['id']} ({reason}, port={choice.get('port')}).",
            )

        # Genuinely no warps available (shouldn't happen in a connected galaxy).
        return Action(kind=ActionKind.WAIT, args={}, thought="No warps from this sector; waiting a tick.")

    @staticmethod
    def _legal(obs: Observation) -> dict:
        return {la.get("kind"): la for la in (obs.legal_actions or [])}

    def _short_for_warp(self, obs: Observation) -> bool:
        """Warp refused for turns only (e.g. 2 left, 3 a warp) while WAIT is open: wait out the day."""
        legal = self._legal(obs)
        warp, wait = legal.get("warp") or {}, legal.get("wait") or {}
        return (bool(warp) and not warp.get("legal") and str(warp.get("reason") or "").startswith("out of turns")
                and bool(wait.get("legal")))

    def _legal_max(self, obs: Observation, kind: str, item: str) -> int:
        la = self._legal(obs).get(kind) or {}
        if not la.get("legal"):
            return 0
        return int((((la.get("params") or {}).get("qty") or {}).get("max_by") or {}).get(item) or 0)

    def _leave_pod(self, obs: Observation) -> Action | None:
        """Escape pod: at StarDock trade it for a Cargotran or a Scout; elsewhere autopilot to StarDock."""
        legal = self._legal(obs)

        def ok(kind: str) -> bool:
            return bool((legal.get(kind) or {}).get("legal"))

        if obs.sector.get("id") == STARDOCK_SECTOR:
            if not ok("buy_ship"):
                return None
            spec = ((legal["buy_ship"].get("params") or {}).get("ship_class") or {})
            choices, net = spec.get("choices") or [], spec.get("net_cost_by") or {}
            for key, keep in (("cargotran", 20_000), ("scout_marauder", 0)):
                cost = net.get(key)
                if key in choices and cost is not None and obs.credits - int(cost) >= keep:
                    return Action(kind=ActionKind.BUY_SHIP, args={"ship_class": key},
                                  thought=f"Trading the escape pod for a {key} ({int(cost)} cr net).")
            return None
        if ok("plot_course") and ok("warp"):
            return Action(kind=ActionKind.PLOT_COURSE, args={"target": STARDOCK_SECTOR, "execute": True},
                          thought="Escape pod: autopilot to StarDock to trade it in.")
        if self._short_for_warp(obs):
            return Action(kind=ActionKind.WAIT, thought="Escape pod short of turns for a warp; waiting for tomorrow.")
        return None

    def _attack(self, target: str, thought: str) -> Action:
        return Action(kind=ActionKind.ATTACK, args={"target": target}, thought=thought)

    def _answer_challenge(self, obs: Observation, challenge: dict) -> Action:
        legal = {la.get("kind"): la for la in (obs.legal_actions or [])}

        def ok(kind: str) -> bool:
            return bool((legal.get(kind) or {}).get("legal"))

        if ok("pay_toll"):
            return Action(kind=ActionKind.PAY_TOLL, thought="Paying the toll to pass.")
        def reason(kind: str) -> str:
            return str((legal.get(kind) or {}).get("reason") or "")

        count = int(challenge.get("count") or 0)
        sector = int(challenge["sector_id"]) if challenge.get("sector_id") is not None else None
        aboard = int(obs.ship.get("fighters") or 0)
        can_win = aboard > 0 and aboard * combat_hull(str(obs.ship.get("class") or ""))[0] >= count
        qty = int((((legal.get("attack") or {}).get("params") or {}).get("qty") or {}).get("max") or 0)
        again = sector is not None and self._held.get(sector) == obs.day
        if ok("retreat") and not (again and ok("attack") and qty > 0 and can_win):
            if sector is not None:
                self._held[sector] = obs.day
            return Action(kind=ActionKind.RETREAT, thought="Fighters block the way; retreating.")
        if ok("attack") and qty > 0 and can_win:
            return Action(kind=ActionKind.ATTACK, args={"target": "fighters", "qty": qty},
                          thought="Clearing the fighters.")
        if reason("retreat").startswith("out of turns") or (can_win and reason("attack").startswith("out of turns")):
            if ok("wait"):
                return Action(kind=ActionKind.WAIT, thought="Held by fighters and short of turns; waiting for tomorrow.")
            return Action(kind=ActionKind.QUERY_LIMPETS, thought="Held by fighters with no turns left.")
        if ok("surrender"):
            return Action(kind=ActionKind.SURRENDER, thought="No way past the fighters; surrendering.")
        return Action(kind=ActionKind.QUERY_LIMPETS, thought="Held by fighters with no turns left.")

    def _flee(self, obs: Observation, thought: str) -> Action:
        adj = obs.adjacent or []
        if not adj:
            return Action(kind=ActionKind.WAIT, thought=thought + " (no adjacent sectors)")
        choice = self.rng.choice(adj)
        return Action(
            kind=ActionKind.WARP,
            args={"target": choice["id"]},
            thought=thought + f" Warping to {choice['id']}.",
        )
