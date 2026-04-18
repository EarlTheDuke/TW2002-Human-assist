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
from .base import BaseAgent


class HeuristicAgent(BaseAgent):
    kind = "heuristic"

    def __init__(self, player_id: str, name: str, seed: int | None = None):
        super().__init__(player_id, name)
        self.rng = random.Random(seed if seed is not None else hash(player_id) & 0xFFFF)

    async def act(self, obs: Observation) -> Action:
        # Survival first: ferrengi in sector, low fighters? flee.
        ferr = obs.sector.get("ferrengi", [])
        if ferr:
            top = max(ferr, key=lambda f: f["aggression"])
            if obs.ship["fighters"] >= top["fighters"] * 1.5:
                return self._attack(top["id"], "Ferrengi looks beatable, lets collect that bounty.")
            return self._flee(obs, f"Ferrengi aggression {top['aggression']} — bail.")

        # At StarDock: consider outfitting & upgrading before heading out
        if obs.sector["id"] == 1 and obs.credits > 50_000:
            if obs.ship["fighters"] < 500 and obs.credits > 25_000:
                qty = min(200, obs.credits // 50)
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

    def _attack(self, target: str, thought: str) -> Action:
        return Action(kind=ActionKind.ATTACK, args={"target": target}, thought=thought)

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
