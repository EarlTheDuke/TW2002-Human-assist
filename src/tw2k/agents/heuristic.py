"""Rule-based agent for testing and as a fallback when no LLM API key is set.

The heuristic agent implements a competent trade-loop player:
- Find best local buy (cheap at selling-port, rich at buying-port).
- Execute trades until cargo is full, then warp toward the best known buying port.
- If a Ferrengi is in its sector with low aggression, fight; otherwise flee.
- If at StarDock with surplus credits, upgrade ship.
- Avoid ping-ponging the same two sectors; refuse warps when out of turns.

It's not intended to beat an LLM - just to play a valid game.
"""

from __future__ import annotations

import random

from tw2k.engine.constants import (
    DENSITY_SCANNER_COST,
    HOLO_SCANNER_COST,
    SCANNER_DENSITY,
    SCANNER_HOLO,
    info_tw2002,
    scanner_room,
)

from ..engine import Action, ActionKind, Observation
from ..engine.constants import STARDOCK_SECTOR, combat_hull
from .base import BaseAgent

_PORT_CODE_ORDER = ("fuel_ore", "organics", "equipment")


def _port_buys_any(code: str, held: set[str]) -> bool:
    """Port code letters are fuel_ore, organics, equipment; B = the port buys it. No cargo: any port."""
    if not held or len(code) != 3:
        return True
    return any(code[i] == "B" and _PORT_CODE_ORDER[i] in held for i in range(3))


class HeuristicAgent(BaseAgent):
    kind = "heuristic"

    def __init__(self, player_id: str, name: str, seed: int | None = None):
        super().__init__(player_id, name)
        # Explicit seed keeps multi-seat matches deterministic. hash(player_id)
        # alone still drifts under PYTHONHASHSEED randomization.
        self.rng = random.Random(seed if seed is not None else (sum(ord(c) for c in player_id) & 0xFFFF))
        self._visit_counts: dict[int, int] = {}
        self._last_from: int | None = None
        self._last_to: int | None = None
        # Sectors whose fighters this seat retreated from -> day; avoided that day (no ping-pong).
        self._held: dict[int, int] = {}
        # Fogged play: port sector -> day we stood there and could not trade (QC).
        self._dry_port: dict[int, int] = {}
        self._traded_at: int | None = None  # sector of a trade this visit
        self._h_deposited = False
        self._h_withdrew = False

    def _port_dry(self, a: dict, day: int | None) -> bool:
        """A port we could not trade at today or yesterday (it restocks slowly)."""
        seen = self._dry_port.get(int(a["id"]))
        return seen is not None and day is not None and int(day) - seen <= 1

    async def act(self, obs: Observation) -> Action:
        # Fighters holding the ship must be answered first (ship-combat-core-v1).
        challenge = getattr(obs, "fighter_challenge", None)
        if challenge:
            return self._answer_challenge(obs, challenge)
        here = int(obs.sector.get("id") or 0)
        self._visit_counts[here] = self._visit_counts.get(here, 0) + 1

        # Survival first: ferrengi in sector, low fighters? flee.
        ferr = obs.sector.get("ferrengi", [])
        if ferr:
            top = max(ferr, key=lambda f: f["aggression"])
            if obs.ship["fighters"] > 0 and obs.ship["fighters"] >= top["fighters"] * 1.5:
                return self._attack(top["id"], "Ferrengi looks beatable, lets collect that bounty.")
            return self._flee(obs, f"Ferrengi aggression {top['aggression']} - bail.")

        jump = self._ship_transwarp(obs)
        if jump is not None:
            return jump

        # In an escape pod: bank the replacement hull first, then trade it in (bb14).
        if str(obs.ship.get("class") or "") == "escape_pod":
            banked = self._h_bank(obs, recovery=True)
            if banked is not None:
                return banked
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
            for commodity in ("equipment", "organics", "fuel_ore"):
                held = obs.ship["cargo"].get(commodity, 0)
                if held > 0 and commodity in port["buys"] and commodity in port["stock"]:
                    entry = port["stock"][commodity]
                    capacity = entry["max"] - entry["current"]
                    qty = min(held, capacity)
                    if qty > 0:
                        self._traded_at = here
                        return Action(
                            kind=ActionKind.TRADE,
                            args={"commodity": commodity, "qty": qty, "side": "sell"},
                            thought=f"Offloading {qty} {commodity} at {port['code']} for {entry['price']}cr/u.",
                        )
            for commodity in ("equipment", "organics", "fuel_ore"):
                if commodity in port["sells"] and commodity in port["stock"]:
                    entry = port["stock"][commodity]
                    unit = entry["price"]
                    holds_free = obs.ship["cargo_free"]
                    qty = min(holds_free, entry["current"], obs.credits // max(1, unit))
                    if qty > 0:
                        self._traded_at = here
                        return Action(
                            kind=ActionKind.TRADE,
                            args={"commodity": commodity, "qty": qty, "side": "buy"},
                            thought=f"Buying {qty} {commodity} at {port['code']} for {unit}cr/u.",
                        )
            if info_tw2002() and self._traded_at != here:
                # QC: nothing to sell or buy here. Remember it so the walk stops hopping
                # back to a drained pair of ports (seed 250925 P6 orbited 572/687/744 days 5-10).
                self._dry_port[here] = int(getattr(obs, "day", 0) or 0)

        # Fogged play: fit a scanner at StarDock, then scan before blind warps.
        if info_tw2002():
            fitted = (obs.ship or {}).get("scanner") if isinstance(obs.ship, dict) else getattr(obs.ship, "scanner", None)
            legal = self._legal(obs)
            buy = legal.get("buy_equip")
            here = int(obs.sector.get("id") or 0)
            if here == 1 and buy and buy.get("legal"):
                items = ((buy.get("params") or {}).get("item") or {}).get("choices") or []
                prices = ((buy.get("params") or {}).get("item") or {}).get("unit_price_by") or {}
                room = scanner_room(str((obs.ship or {}).get("class") or getattr(obs.ship, "ship_class", "") or ""))
                credits = int(getattr(obs, "credits", 0) or 0)
                pick = None
                if room == SCANNER_HOLO and "holo_scanner" in items and fitted != SCANNER_HOLO:
                    cost = int(prices.get("holo_scanner") or HOLO_SCANNER_COST)
                    if credits >= cost + 8_000:
                        pick = ("holo_scanner", cost)
                if pick is None and fitted is None and "density_scanner" in items:
                    cost = int(prices.get("density_scanner") or DENSITY_SCANNER_COST)
                    # Keep a small cash buffer so a density buy never zeroes the seat.
                    if credits >= cost + 2_000:
                        pick = ("density_scanner", cost)
                if pick is not None:
                    item, cost = pick
                    return Action(kind=ActionKind.BUY_EQUIP, args={"item": item, "qty": 1},
                                  thought=f"Fitting {item} ({cost} cr) to map fogged neighbors.")
            scan_la = legal.get("scan")
            if fitted and scan_la and scan_la.get("legal"):
                adj = obs.adjacent or []
                need = False
                for a in adj:
                    if not a.get("port") and not a.get("seen") and a.get("scan_day") != getattr(obs, "day", None):
                        need = True
                        break
                if need:
                    tiers = ((scan_la.get("params") or {}).get("tier") or {}).get("choices") or []
                    tier = SCANNER_HOLO if SCANNER_HOLO in tiers else (SCANNER_DENSITY if SCANNER_DENSITY in tiers else (tiers[0] if tiers else None))
                    args = {"tier": tier} if tier else {}
                    return Action(kind=ActionKind.SCAN, args=args,
                                  thought=f"{tier or 'basic'} scan before warping blind.")

        # Out of turns: wait. Warping would be rejected and waste the decision.
        turns_left = int(getattr(obs, "turns_remaining", 0) or 0)
        if turns_left <= 0:
            banked = self._h_bank(obs, recovery=False)
            if banked is not None:
                return banked
            return Action(kind=ActionKind.WAIT, args={}, thought="Out of turns today; waiting for the day tick.")

        adj = obs.adjacent or []
        day = getattr(obs, "day", None)
        adj = [a for a in adj if self._held.get(int(a["id"])) != day] or adj
        if adj and self._short_for_warp(obs):
            return Action(kind=ActionKind.WAIT, thought="Not enough turns left for a warp; waiting for tomorrow.")
        if adj:
            # Never reverse the last hop (kills the 203<->270 loop).
            candidates = [a for a in adj if int(a["id"]) != self._last_from]
            if not candidates:
                candidates = list(adj)
            unknown = [a for a in candidates if not a.get("known")]
            # Fogged play only (INFO_MODE tw2002): the all-legacy golden digest keeps the old walk.
            held = {str(c) for c, n in ((obs.ship or {}).get("cargo") or {}).items()
                    if n and str(c) in _PORT_CODE_ORDER} if info_tw2002() else set()
            # QC: holding cargo, only a port that BUYS it is worth a hop. Hopping among
            # ports that cannot buy it is a dead-end orbit (seed 250925 P6: 674/261/708 from day 2).
            with_port = [a for a in candidates if a.get("port") and a["port"] not in ("FED",)
                         and _port_buys_any(str(a["port"]), held) and not self._port_dry(a, day)]
            # Density chart (s7): 100 marks a port when holo has not yet named it.
            dense_port = [a for a in candidates if int(a.get("density") or 0) >= 100
                          and not self._port_dry(a, day)]
            if unknown:
                pool = unknown
                reason = "scouting"
            elif with_port:
                pool = with_port
                reason = "hopping to known port"
            elif dense_port:
                pool = dense_port
                reason = "density suggests a port"
            else:
                pool = candidates
                reason = "drifting"
            # Fogged play: while drifting, a port just ruled out (cannot buy the cargo, or
            # drained) loses ties to a plain sector, but visit counts still come first, so a
            # dead-end pocket cannot trap the seat (seed 250925 P6: 985 <-> 434/986).
            def ruled_out(a: dict) -> int:
                return int(reason == "drifting" and info_tw2002() and bool(a.get("port"))
                           and a["port"] not in ("FED",))
            # Prefer least-visited to escape two-sector orbits; among ties, higher density.
            choice = min(pool, key=lambda a: (
                self._visit_counts.get(int(a["id"]), 0),
                ruled_out(a),
                -int(a.get("density") or 0),
                int(a["id"]),
            ))
            # Tie-break with rng among equally fresh sectors of equal density.
            best_visits = self._visit_counts.get(int(choice["id"]), 0)
            best_density = int(choice.get("density") or 0)
            tied = [
                a for a in pool
                if self._visit_counts.get(int(a["id"]), 0) == best_visits
                and ruled_out(a) == ruled_out(choice)
                and int(a.get("density") or 0) == best_density
            ]
            if len(tied) > 1:
                choice = self.rng.choice(tied)
            banked = self._h_bank(obs, recovery=False)
            if banked is not None:
                return banked
            self._last_from = here
            self._last_to = int(choice["id"])
            self._traded_at = None
            return Action(
                kind=ActionKind.WARP,
                args={"target": choice["id"]},
                thought=f"Warping to {choice['id']} ({reason}, port={choice.get('port')}).",
            )

        return Action(kind=ActionKind.WAIT, args={}, thought="No warps from this sector; waiting a tick.")

    @staticmethod
    def _legal(obs: Observation) -> dict:
        return {la.get("kind"): la for la in (getattr(obs, "legal_actions", None) or [])}

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

    def _h_banks(self) -> bool:
        """bb14: H banks only while the bot bank mode is on."""
        from ..engine.constants import BOT_BANK_H, BOT_BANK_POLICY, bots_bank_on
        return bool(BOT_BANK_H) and bots_bank_on() and BOT_BANK_POLICY == "reserve"

    def _h_keep(self, obs: Observation) -> int:
        from ..engine.constants import BOT_BANK_CAPITAL_PER_HOLD, BOT_BANK_H_KEEP
        holds = int((obs.ship or {}).get("holds") or 0)
        return max(int(BOT_BANK_H_KEEP), holds * int(BOT_BANK_CAPITAL_PER_HOLD))

    def _h_bank(self, obs: Observation, *, recovery: bool) -> Action | None:
        """One StarDock bank step. A pod withdraws for its hull first. Otherwise
        spare cash above the keep is deposited once per visit. Legacy H skips this."""
        if int(obs.sector.get("id") or 0) != STARDOCK_SECTOR:
            self._h_deposited = False
            self._h_withdrew = False
            return None
        if not self._h_banks():
            return None
        from .bank_brain import deposit_amount, nest_egg, tax_keep, withdraw_amount
        legal = self._legal(obs)
        balance = int(obs.bank_balance or 0)
        egg = nest_egg(int(getattr(obs, "net_worth", 0) or 0))
        credits = int(obs.credits)
        if recovery:
            if self._h_withdrew:
                return None
            buy = legal.get("buy_ship") or {}
            withdraw = legal.get("bank_withdraw") or {}
            if not withdraw.get("legal"):
                return None
            spec = (buy.get("params") or {}).get("ship_class") or {}
            choices = spec.get("choices") or []
            net = spec.get("net_cost_by") or {}
            maximum = int((withdraw.get("params") or {}).get("max_amount") or 0)
            amount = 0
            from ..engine.constants import h_recovery_on
            if h_recovery_on():
                from .bank_brain import recovery_hull_step
                step = recovery_hull_step(
                    choices, net, credits, balance, maximum, spec.get("blocked_by") or {},
                )
                if step is not None and step[0] == "bank_withdraw":
                    amount = int(step[1])
                elif step is not None and step[0] == "buy_ship":
                    return None
            elif not buy.get("legal"):
                return None
            elif "cargotran" in choices and net.get("cargotran") is not None:
                amount = withdraw_amount(
                    int(net["cargotran"]), 20_000, credits, balance, egg, maximum, recovery=True,
                )
            if amount < 1:
                amount = withdraw_amount(
                    self._h_keep(obs), 0, credits, balance, egg, maximum, recovery=False,
                )
            if amount < 1:
                return None
            self._h_withdrew = True
            return Action(
                kind=ActionKind.BANK_WITHDRAW, args={"amount": amount},
                thought="Withdrawing for the replacement hull.",
            )
        if self._h_deposited:
            return None
        deposit = legal.get("bank_deposit") or {}
        if not deposit.get("legal"):
            return None
        maximum = int((deposit.get("params") or {}).get("max_amount") or 0)
        day = int(getattr(obs, "day", 1) or 1)
        keep = tax_keep(self._h_keep(obs), 0, int(getattr(obs, "alignment", 0) or 0))
        amount = deposit_amount(credits, keep, maximum, day1=day <= 1)
        if amount < 1:
            return None
        self._h_deposited = True
        return Action(
            kind=ActionKind.BANK_DEPOSIT, args={"amount": amount},
            thought="Banking the spare cash before leaving StarDock.",
        )

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
            from ..engine.constants import h_recovery_on
            if h_recovery_on():
                from .bank_brain import recovery_hull_step
                step = recovery_hull_step(
                    choices, net, int(obs.credits), 0, 0, spec.get("blocked_by") or {},
                )
                if step is not None and step[0] == "buy_ship":
                    hull = str(step[1])
                    cost = int((net or {}).get(hull) or 0)
                    return Action(kind=ActionKind.BUY_SHIP, args={"ship_class": hull},
                                  thought=f"Trading the escape pod for a {hull} ({cost} cr net).")
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
        """Omit qty so the engine sends the hull cap. That is not the capture minimum."""
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

    def _ship_transwarp(self, obs: Observation) -> Action | None:
        """ship-transwarp-v1: rich and far from StarDock, take a listed lock onto it. Never blind.

        Only sector 1 (a commissioned FedSpace lock or an own/corp/ally fighter there), only
        when the walk is 3+ hops, and only when the hold keeps the same ore again for a return.
        """
        tw = obs.ship.get("transwarp") if isinstance(obs.ship, dict) else None
        if not isinstance(tw, dict) or not tw.get("fitted") or obs.credits <= 50_000:
            return None
        spec = next((la for la in (obs.legal_actions or []) if la.get("kind") == "ship_transwarp"), None)
        if not isinstance(spec, dict) or not spec.get("legal"):
            return None
        params = (spec.get("params") or {}).get("sector_id") or {}
        if STARDOCK_SECTOR not in [int(c) for c in (params.get("choices") or [])]:
            return None
        hops = int((params.get("hops_by") or {}).get(str(STARDOCK_SECTOR)) or 0)
        need = int((params.get("ore_by") or {}).get(str(STARDOCK_SECTOR)) or 0)
        ore = int((obs.ship.get("cargo") or {}).get("fuel_ore") or 0)
        if hops < 3 or need <= 0 or ore < 2 * need:
            return None
        return Action(kind=ActionKind.SHIP_TRANSWARP, args={"sector_id": STARDOCK_SECTOR},
                      thought=f"TransWarp to StarDock ({hops} hops, {need} ore), ore kept for the return.")

    def _flee(self, obs: Observation, thought: str) -> Action:
        adj = obs.adjacent or []
        if not adj:
            return Action(kind=ActionKind.WAIT, thought=thought + " (no adjacent sectors)")
        # QC (seed 99 P6): a flee warp with no turns left is refused ("out of turns") and
        # wastes the decision. Wait for the day tick instead, as the normal walk does.
        if int(getattr(obs, "turns_remaining", 1) or 0) <= 0 or self._short_for_warp(obs):
            return Action(kind=ActionKind.WAIT, thought=thought + " (no turns left to warp; waiting)")
        here = int(obs.sector.get("id") or 0)
        candidates = [a for a in adj if int(a["id"]) != self._last_from] or list(adj)

        def _haz(a: dict) -> int:
            raw = a.get("navhaz", a.get("nav_hazard_pct"))
            try:
                return int(raw or 0)
            except (TypeError, ValueError):
                return 0

        calm = [a for a in candidates if _haz(a) < 10]
        if calm and len(calm) < len(candidates):
            candidates = calm
        choice = min(candidates, key=lambda a: (self._visit_counts.get(int(a["id"]), 0), int(a["id"])))
        self._last_from = here
        self._last_to = int(choice["id"])
        return Action(
            kind=ActionKind.WARP,
            args={"target": choice["id"]},
            thought=thought + f" Warping to {choice['id']}.",
        )
