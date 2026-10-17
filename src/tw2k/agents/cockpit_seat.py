"""A seat that plays from the cockpit harness only.

NOTE 54. The client reads four GETs for its own seat and posts the same
action kinds the redesign cockpit can send. It does not import the match,
the runner, or an observation builder. Default games never call it.
AI_COCKPIT_SEAT_MODE stays legacy until a test turns it on.

NOTE 55. ``CockpitSeat.run`` plays several days. ``SeatBrain`` decides each
turn from the observation the cockpit paints, the Rules and Help page, and
the seat's own notes of what it saw. ``run_http`` wires the seat to a server
over HTTP with one bearer token. Each time the seat has to guess something
the cockpit does not show, it writes a gap row.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from typing import Any

from ..engine import constants as K

# Kinds the redesign page can post. Computer, planet, port, and ship forms
# included. The day loop uses warp, plot_course, trade, buy_equip, the
# challenge answers, and wait.
COCKPIT_KINDS = frozenset({
    "warp", "trade", "land_planet", "liftoff", "scan", "attack", "wait",
    "deploy_fighters", "deploy_mines", "deploy_genesis", "probe",
    "plot_course", "photon_missile", "broadcast", "avoid",
    "load_planet_cargo", "dump_planet_cargo", "assign_colonists",
    "deposit_planet_defense", "withdraw_planet_defense", "build_citadel",
    "set_military_reaction", "deposit_treasury", "withdraw_treasury",
    "planet_buy_transporter", "planet_transport", "recall_deployed",
    "buy_ship", "buy_equip", "sell_ship", "launch_beacon",
    "hail", "radio", "surrender", "retreat", "pay_toll",
    "rob", "steal", "port_upgrade", "port_build",
    "bank_deposit", "bank_withdraw", "bank_transfer",
    "terra_colonists", "corp_create", "ship_transport", "tow_engage",
    "tow_release",
})

READS = ("observation", "reference", "events", "status")
STARDOCK_SECTOR = 1
COMMODITIES = ("fuel_ore", "organics", "equipment")
DEFAULT_BASE = {"fuel_ore": 26, "organics": 56, "equipment": 102}
REFERENCE_BASE_ROWS = {"Fuel ore, base": "fuel_ore", "Organics, base": "organics", "Equipment, base": "equipment"}

Get = Callable[..., Awaitable[dict[str, Any]]]
Post = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


class CockpitSeatOff(RuntimeError):  # noqa: N818 - the v1 name the tests import
    """The seat stays unwired while AI_COCKPIT_SEAT_MODE is legacy."""


class CockpitSeatError(RuntimeError):
    """The cockpit surface did not offer the move."""


class CockpitHTTPError(RuntimeError):
    """The harness answered a read or a post with something other than 200."""

    def __init__(self, status: int, detail: Any) -> None:
        super().__init__(f"HTTP {status}: {detail}")
        self.status = int(status)
        self.detail = detail


class CockpitSeat:
    """One external seat. ``get`` and ``post`` talk to the harness only."""

    def __init__(self, seat_id: str, get: Get, post: Post) -> None:
        self.seat_id = seat_id
        self._get = get
        self._post = post

    def path(self, leaf: str) -> str:
        if leaf not in READS and leaf != "action":
            raise CockpitSeatError(f"not a cockpit route: {leaf}")
        return f"/harness/v1/{self.seat_id}/{leaf}"

    async def read(self, leaf: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._get(self.path(leaf), params)

    async def _after(self, turn_seq: int) -> dict[str, Any]:
        """The next cockpit turn. A read during the post still shows the old one."""
        for _ in range(40):
            body = await self.read("observation", {"wait_s": 2})
            seq = int(body.get("turn_seq") or 0)
            if body.get("observation") and seq > turn_seq:
                return body
            await asyncio.sleep(0.05)
        raise CockpitSeatError("the next turn did not open")

    async def post_action(self, turn_seq: int, kind: str, args: dict[str, Any]) -> dict[str, Any]:
        if kind not in COCKPIT_KINDS:
            raise CockpitSeatError(f"not a cockpit action: {kind}")
        return await self._post(self.path("action"), {
            "turn_seq": turn_seq,
            "action": {"kind": kind, "args": args},
        })

    async def run_day1(self) -> list[dict[str, Any]]:
        """Leave StarDock, warp one hop, then buy one unit or wait."""
        if not K.ai_cockpit_seat_on():
            raise CockpitSeatOff("AI_COCKPIT_SEAT_MODE is legacy")
        reference = await self.read("reference")
        status = await self.read("status")
        opened = await self.read("observation", {"wait_s": 5})
        before = await self.read("events")
        obs = opened.get("observation") or {}
        kind, args = leave_stardock(obs)
        posted = await self.post_action(int(opened["turn_seq"]), kind, args)
        arrived = await self._after(int(opened["turn_seq"]))
        after = await self.read("events")
        landed = arrived.get("observation") or {}
        trade = _legal(landed, "trade")
        dock_kind, dock_args = dock_or_wait(landed)
        docked = await self.post_action(int(arrived["turn_seq"]), dock_kind, dock_args)
        sections = [row.get("id") for row in (reference.get("sections") or [])]
        return [
            {
                "read": "reference",
                "sections": sections,
            },
            {
                "read": "status",
                "awaiting_input": bool(status.get("awaiting_input")),
            },
            {
                "from_sector": int((obs.get("sector") or {}).get("id") or 0),
                "kind": kind,
                "args": args,
                "accepted": bool(posted.get("accepted")),
                "events_before": len(before.get("events") or []),
            },
            {
                "from_sector": int((landed.get("sector") or {}).get("id") or 0),
                "port": bool((landed.get("sector") or {}).get("port")),
                "trade_legal": bool(trade and trade.get("legal")),
                "trade_reason": None if trade is None else trade.get("reason"),
                "kind": dock_kind,
                "args": dock_args,
                "accepted": bool(docked.get("accepted")),
                "events_after": len(after.get("events") or []),
            },
        ]

    async def run(self, days: int, *, idle_s: float = 600.0, max_posts: int = 6000) -> dict[str, Any]:
        """Play ``days`` game days. Returns the day table, refusals, and gaps."""
        if not K.ai_cockpit_seat_on():
            raise CockpitSeatOff("AI_COCKPIT_SEAT_MODE is legacy")
        reference = await self.read("reference")
        brain = SeatBrain(days, base=reference_base(reference), hold_price=reference_hold_price(reference))
        report: dict[str, Any] = {
            "seat": self.seat_id,
            "days_asked": int(days),
            "reference_sections": [row.get("id") for row in (reference.get("sections") or [])],
            "days": [],
            "posts": 0,
            "refused": [],
            "kinds": {},
            "log": [],
        }
        table: dict[int, dict[str, Any]] = {}
        since = 0
        last_turn = 0
        last_progress = time.monotonic()
        finished = False
        while not finished:
            if time.monotonic() - last_progress > idle_s:
                raise CockpitSeatError("no turn opened for the seat")
            body = await self.read("observation", {"wait_s": 2, "peek": 1})
            obs = body.get("observation") or {}
            if obs:
                _note_day(table, obs)
            if body.get("game_over") or obs.get("finished"):
                break
            if obs and int(obs.get("day") or 0) > days:
                break
            if not body.get("awaiting_input") or body.get("peek") or not obs:
                await asyncio.sleep(0.05)
                continue
            turn = int(body.get("turn_seq") or 0)
            if turn <= last_turn:
                await asyncio.sleep(0.05)
                continue
            last_progress = time.monotonic()
            kind, args, why = brain.decide(obs)
            day = int(obs.get("day") or 0)
            row = table[day]
            report["posts"] += 1
            row["posts"] += 1
            report["kinds"][kind] = report["kinds"].get(kind, 0) + 1
            if report["posts"] > max_posts:
                raise CockpitSeatError("too many posts")
            try:
                await self.post_action(turn, kind, args)
            except CockpitHTTPError as exc:
                report["refused"].append({"day": day, "turn_seq": turn, "kind": kind, "args": args,
                                          "why": why, "http": exc.status, "detail": exc.detail})
                row["refused"] += 1
                brain.refused(kind, args, str(exc.detail))
                last_turn = turn
                continue
            last_turn = turn
            result = await self._result(turn)
            ok = result.get("ok")
            if ok is False:
                error = str(result.get("error") or "")
                report["refused"].append({"day": day, "turn_seq": turn, "kind": kind, "args": args,
                                          "why": why, "error": error})
                row["refused"] += 1
                brain.refused(kind, args, error)
            elif ok:
                brain.done(kind, args)
                if kind == "trade":
                    row["trades"] += 1
                    row["buys" if args.get("side") == "buy" else "sells"] += 1
                if kind == "buy_equip" and args.get("item") == "holds":
                    row["holds_bought"] += int(args.get("qty") or 0)
            since = await self._log_rows(since, report, brain)
            if result.get("game_over"):
                finished = True
        final = await self.read("observation", {"peek": 1})
        if final.get("observation"):
            _note_day(table, final["observation"])
        report["days"] = [table[d] for d in sorted(table) if d <= days]
        report["gaps"] = brain.gap_rows()
        report["final"] = _snapshot(final.get("observation") or {})
        return report

    async def _result(self, turn: int) -> dict[str, Any]:
        """The engine's verdict for ``turn``, read from the seat's own status."""
        for _ in range(200):
            body = await self.read("observation", {"wait_s": 1, "peek": 1})
            last = body.get("last_result") or {}
            if int(last.get("turn_seq") or -1) >= turn:
                return {"ok": last.get("ok"), "error": last.get("error"), "game_over": body.get("game_over")}
            if body.get("game_over"):
                return {"ok": None, "error": None, "game_over": True}
            await asyncio.sleep(0.02)
        return {"ok": None, "error": "result pending"}

    async def _log_rows(self, since: int, report: dict[str, Any], brain: SeatBrain) -> int:
        page = await self.read("events", {"since": since, "limit": 200})
        for ev in page.get("events") or []:
            if ev.get("actor_id") != self.seat_id:
                continue
            summary = str(ev.get("summary") or "")
            brain.read_log(ev)
            report["log"].append({"day": ev.get("day"), "kind": ev.get("kind"), "summary": summary})
        if len(report["log"]) > 400:
            del report["log"][: len(report["log"]) - 400]
        return int(page.get("next_since") or since)


def _note_day(table: dict[int, dict[str, Any]], obs: dict[str, Any]) -> None:
    day = int(obs.get("day") or 0)
    if day <= 0:
        return
    credits = int(obs.get("credits") or 0)
    worth = int(obs.get("net_worth") or 0)
    left = int(obs.get("turns_remaining") or 0)
    per_day = int(obs.get("turns_per_day") or 0)
    row = table.get(day)
    if row is None:
        row = table[day] = {
            "day": day, "credits_start": credits, "net_worth_start": worth,
            "credits_end": credits, "net_worth_end": worth, "turns_used": 0,
            "trades": 0, "buys": 0, "sells": 0, "holds_bought": 0, "posts": 0, "refused": 0,
            "sector_end": None, "holds_end": None,
        }
    row["credits_end"] = credits
    row["net_worth_end"] = worth
    row["turns_used"] = max(int(row["turns_used"]), per_day - left)
    row["sector_end"] = int((obs.get("sector") or {}).get("id") or 0)
    row["holds_end"] = int((obs.get("ship") or {}).get("holds") or 0)


def _snapshot(obs: dict[str, Any]) -> dict[str, Any]:
    return {
        "day": obs.get("day"),
        "credits": obs.get("credits"),
        "net_worth": obs.get("net_worth"),
        "sector": (obs.get("sector") or {}).get("id"),
        "holds": (obs.get("ship") or {}).get("holds"),
    }


def reference_base(reference: dict[str, Any]) -> dict[str, int]:
    """Base prices from Rules and Help. Missing rows keep the printed defaults."""
    base = dict(DEFAULT_BASE)
    for section in reference.get("sections") or []:
        for row in section.get("rows") or []:
            name = REFERENCE_BASE_ROWS.get(str(row.get("name") or ""))
            if name and row.get("price"):
                base[name] = int(row["price"])
    return base


def reference_hold_price(reference: dict[str, Any]) -> int:
    """The 'Next cargo hold' price on Rules and Help, or 0."""
    for section in reference.get("sections") or []:
        for row in section.get("rows") or []:
            if str(row.get("name") or "") == "Next cargo hold":
                return int(row.get("price") or 0)
    return 0


def port_sides(code: Any) -> dict[str, str] | None:
    """BSS-style class: S means the port sells to you, B means it buys from you."""
    text = str(code or "").upper()
    if len(text) != 3 or set(text) - {"B", "S"}:
        return None
    return {name: ("sells" if letter == "S" else "buys") for name, letter in zip(COMMODITIES, text, strict=True)}


GAP_TEXT = {
    "price_away": (
        "Pick a port pair before docking",
        "The price at a port you are not docked at",
        "Computer R port report: class and stock, no price. The price is on the port table only while docked.",
        "Computer R (CIM port report) also lists class, amount and percent, not the price",
    ),
    "price_rule": (
        "Guess a price from the port report",
        "How a port's stock moves its price",
        "Not shown. Rules and Help prints base prices only. The seat uses: a full port sells cheap, an empty port pays well.",
        "Not shown either. Players learn it from the port screen over time",
    ),
    "hold_curve": (
        "How many cargo holds to buy",
        "What the next few holds cost in total",
        "The StarDock form shows the next hold's price and the most you can afford, not how the price rises per hold. The seat buys 5 at a time and reads the credits.",
        "The StarDock Hardware Emporium quotes the hold price and how many you can afford before you choose",
    ),
    "one_way": (
        "Plan a route back",
        "Whether a warp runs both ways",
        "Computer K lists warps only for sectors you have visited. The seat assumes a warp runs both ways until it docks there.",
        "Same in the original: CIM warp data covers explored sectors only",
    ),
    "result_line": (
        "Know whether the last move worked",
        "The engine verdict for the action just posted",
        "The POST answer says accepted. The verdict is in status last_result and in the log line, as the cockpit result line reads it.",
        "The original prints the outcome right after the command",
    ),
    "haggle_band": (
        "What price to offer on the trade form",
        "How far the port will move on price",
        "Not shown. A counter offer appears only inside a log line ('counter N'). The seat offers 92% on a buy and 103% on a sale.",
        "The original port haggles in its own prompts and says 'We'll buy them for N'",
    ),
    "counter_in_log": (
        "Answer a port's counter offer",
        "The counter price",
        "Only inside the log line text, for example 'trade failed: counter 105'. There is no field for it.",
        "The original port prompt prints its counter price",
    ),
    "challenge_strength": (
        "Answer a fighter challenge or a Ferrengi",
        "Whether attacking would win",
        "The challenge shows the enemy fighter count. The seat compares it to its own fighters and prefers pay or retreat.",
        "The original shows the fighter count and your own fighters on the same screen",
    ),
}


class SeatBrain:
    """One turn's choice from the cockpit view and the seat's own notes."""

    def __init__(self, days: int, base: dict[str, int] | None = None, hold_price: int = 0) -> None:
        self.days = int(days)
        self.base = dict(base or DEFAULT_BASE)
        self.prices: dict[tuple[int, str], dict[str, Any]] = {}
        self.visited: set[int] = set()
        self.no_edge: set[tuple[int, int]] = set()
        self.haggle = {"buy": 92, "sell": 103}
        self.gaps: dict[str, int] = {}
        self.last_plan: dict[str, Any] | None = None
        self.bad_warps: set[tuple[int, int]] = set()
        self._turn_gaps: set[str] | None = None
        self.hold_price = int(hold_price or 0)
        self.dock_trip = False

    # ---- notes ---------------------------------------------------------------

    def gap(self, gid: str) -> None:
        """Count a gap once for each turn that needed it."""
        if self._turn_gaps is None:
            self.gaps[gid] = self.gaps.get(gid, 0) + 1
        else:
            self._turn_gaps.add(gid)

    def gap_rows(self) -> list[dict[str, Any]]:
        rows = []
        for gid, count in sorted(self.gaps.items(), key=lambda item: -item[1]):
            decision, needed, cockpit, original = GAP_TEXT[gid]
            rows.append({"id": gid, "count": count, "decision": decision, "needed": needed,
                         "cockpit": cockpit, "original": original})
        return rows

    def read_log(self, ev: dict[str, Any]) -> None:
        summary = str(ev.get("summary") or "")
        if "counter " in summary:
            self.gap("counter_in_log")

    def refused(self, kind: str, args: dict[str, Any], error: str) -> None:
        if kind == "trade":
            side = str(args.get("side") or "")
            if side in self.haggle:
                self.haggle[side] = 100
            if "counter" in error:
                self.gap("counter_in_log")
        if kind == "warp" and self.last_plan:
            self.bad_warps.add((int(self.last_plan.get("from") or 0), int(args.get("target") or 0)))

    def done(self, kind: str, args: dict[str, Any]) -> None:
        self.gap("result_line")

    # ---- reading the view ----------------------------------------------------

    def _record(self, obs: dict[str, Any]) -> None:
        sector = obs.get("sector") or {}
        here = int(sector.get("id") or 0)
        self.visited.add(here)
        port = sector.get("port") or {}
        for name, row in (port.get("stock") or {}).items():
            price = row.get("price")
            side = row.get("side")
            if price is None or side not in ("sells_to_player", "buys_from_player"):
                continue
            self.prices[(here, name)] = {
                "price": int(price),
                "side": "sells" if side == "sells_to_player" else "buys",
                "day": int(obs.get("day") or 0),
            }

    def _ports(self, obs: dict[str, Any]) -> dict[int, dict[str, Any]]:
        out: dict[int, dict[str, Any]] = {}
        for row in obs.get("known_ports") or []:
            sid = int(row.get("sector_id") or 0)
            sides = port_sides(row.get("class"))
            if sid and sides:
                out[sid] = {"sides": sides, "stock": dict(row.get("stock") or {})}
        sector = obs.get("sector") or {}
        port = sector.get("port") or {}
        sides = port_sides(port.get("code"))
        if sides:
            stock = {name: {"current": row.get("current"), "max": row.get("max")}
                     for name, row in (port.get("stock") or {}).items()}
            out[int(sector.get("id") or 0)] = {"sides": sides, "stock": stock}
        return out

    def _graph(self, obs: dict[str, Any]) -> dict[int, set[int]]:
        known = {int(k): [int(x) for x in v] for k, v in (obs.get("known_warps") or {}).items()}
        edges: dict[int, set[int]] = defaultdict(set)
        for a, outs in known.items():
            for b in outs:
                edges[a].add(b)
        for a, outs in known.items():
            for b in outs:
                if b not in known and (b, a) not in self.no_edge:
                    edges[b].add(a)
        sector = obs.get("sector") or {}
        here = int(sector.get("id") or 0)
        edges[here] = {int(w) for w in (sector.get("warps_out") or [])} - {b for a, b in self.bad_warps if a == here}
        return edges

    @staticmethod
    def _dists(edges: dict[int, set[int]], src: int) -> tuple[dict[int, int], dict[int, int]]:
        dist = {src: 0}
        first: dict[int, int] = {}
        queue = deque([src])
        while queue:
            node = queue.popleft()
            for nxt in sorted(edges.get(node, ())):
                if nxt in dist:
                    continue
                dist[nxt] = dist[node] + 1
                first[nxt] = nxt if node == src else first[node]
                queue.append(nxt)
        return dist, first

    def _price(self, sid: int, name: str, info: dict[str, Any], side: str, day: int) -> float:
        seen = self.prices.get((sid, name))
        if seen and seen["side"] == side and int(seen["day"]) >= day - 1:
            return float(seen["price"])
        self.gap("price_away")
        self.gap("price_rule")
        row = (info.get("stock") or {}).get(name) or {}
        top = max(1, int(row.get("max") or 0))
        frac = min(1.0, max(0.0, int(row.get("current") or 0) / top))
        base = float(self.base.get(name, 50))
        if side == "sells":
            return base * (1.2 - 0.55 * frac)
        return base * (1.4 - 0.65 * frac)

    @staticmethod
    def _amount(info: dict[str, Any], name: str, side: str) -> int:
        row = (info.get("stock") or {}).get(name) or {}
        current = int(row.get("current") or 0)
        if side == "sells":
            return current
        return max(0, int(row.get("max") or 0) - current)

    # ---- the choice ----------------------------------------------------------

    def decide(self, obs: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
        self._turn_gaps = set()
        try:
            return self._decide(obs)
        finally:
            for gid in self._turn_gaps:
                self.gaps[gid] = self.gaps.get(gid, 0) + 1
            self._turn_gaps = None

    def _decide(self, obs: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
        self._record(obs)
        if obs.get("ferrengi_encounter") or obs.get("fighter_challenge"):
            return self._answer(obs)
        sector = obs.get("sector") or {}
        here = int(sector.get("id") or 0)
        day = int(obs.get("day") or 0)
        turns = int(obs.get("turns_remaining") or 0)
        warp = _legal(obs, "warp") or {}
        warp_t = int(warp.get("turn_cost") or 3)
        trade = _legal(obs, "trade") or {}
        trade_t = int(trade.get("turn_cost") or 1)
        ship = obs.get("ship") or {}
        cargo = {name: int((ship.get("cargo") or {}).get(name) or 0) for name in COMMODITIES}
        free = int(ship.get("cargo_free") or 0)
        credits = int(obs.get("credits") or 0)
        ports = self._ports(obs)
        edges = self._graph(obs)
        dist, first = self._dists(edges, here)
        last_day = day >= self.days

        if here == STARDOCK_SECTOR:
            self.dock_trip = False
        holds = self._buy_holds(obs, here, day, credits, ship)
        if holds is not None:
            return holds

        if trade.get("legal"):
            sale = self._sell_here(obs, trade, cargo, ship, last_day)
            if sale is not None:
                return sale
        carried = [name for name in COMMODITIES if cargo.get(name, 0) > 0]
        if warp.get("legal") and turns >= warp_t:
            if self.dock_trip and STARDOCK_SECTOR in dist:
                return self._go(obs, warp, STARDOCK_SECTOR, first, "on the way to StarDock for holds")
            dock = self._stardock_trip(obs, dist, here, carried, credits, turns, warp_t)
            if dock is not None:
                self.dock_trip = True
                return self._go(obs, warp, dock[0], first, dock[1])
        if trade.get("legal"):
            if free > 0 and turns >= trade_t:
                buy = self._buy_here(obs, trade, ports, edges, here, free, credits, turns, warp_t, trade_t, last_day)
                if buy is not None:
                    return buy

        if turns < warp_t or not warp.get("legal"):
            return "wait", {}, "not enough turns for a warp"

        target, why = self._target(obs, ports, edges, dist, here, cargo, free, credits, turns, warp_t, trade_t, last_day)
        if target is None:
            return "wait", {}, "nothing to do today"
        if last_day and target in dist and dist[target] * warp_t + trade_t > turns and sum(cargo.values()) == 0:
            return "wait", {}, "no trip fits in today's turns"
        return self._go(obs, warp, target, first, why)

    def _go(self, obs: dict[str, Any], warp: dict[str, Any], target: int, first: dict[int, int], why: str) -> tuple[str, dict[str, Any], str]:
        here = int((obs.get("sector") or {}).get("id") or 0)
        choices = [int(x) for x in (((warp.get("params") or {}).get("target") or {}).get("choices") or [])]
        hop = first.get(target)
        if hop is not None and hop in choices:
            self.last_plan = {"from": here, "to": target}
            return "warp", {"target": hop}, why
        if hop is not None:
            self.no_edge.add((here, hop))
            self.gap("one_way")
        plot = _legal(obs, "plot_course") or {}
        execute = ((plot.get("params") or {}).get("execute") or {})
        if plot.get("legal") and execute.get("legal", True):
            self.last_plan = {"from": here, "to": target}
            return "plot_course", {"target": target, "execute": True}, why + " (course plotter)"
        if choices:
            return "warp", {"target": choices[0]}, "first warp"
        return "wait", {}, "no warp out"

    def _answer(self, obs: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
        self.gap("challenge_strength")
        credits = int(obs.get("credits") or 0)
        mine = int((obs.get("ship") or {}).get("fighters") or 0)
        ferrengi = obs.get("ferrengi_encounter")
        challenge = obs.get("fighter_challenge") or {}
        order = ("retreat", "surrender", "attack") if ferrengi else ("pay_toll", "retreat", "attack", "surrender")
        for kind in order:
            row = _legal(obs, kind)
            if not row or not row.get("legal"):
                continue
            params = row.get("params") or {}
            if kind == "pay_toll":
                amount = int(params.get("amount") or 0)
                if amount > credits // 4:
                    continue
                return "pay_toll", {}, f"pay the toll of {amount} cr"
            if kind == "attack":
                target = params.get("target") or {}
                picks = list(target.get("ferrengi") or []) if ferrengi else []
                picks = picks or list(target.get("choices") or [])
                enemy = int((ferrengi or {}).get("fighters") or challenge.get("count") or 0)
                if not picks or mine <= enemy:
                    continue
                qty = int((params.get("qty") or {}).get("max") or mine)
                return "attack", {"target": picks[0], "qty": qty}, "attack, more fighters than the enemy"
            if kind == "surrender" and not ferrengi and mine > 0:
                continue
            return kind, {}, f"{kind} the challenge"
        return "wait", {}, "no answer is open"

    def _buy_holds(self, obs: dict[str, Any], here: int, day: int, credits: int, ship: dict[str, Any]):
        if here != STARDOCK_SECTOR or day > self.days - 2:
            return None
        shop = _legal(obs, "buy_equip") or {}
        if not shop.get("legal"):
            return None
        params = shop.get("params") or {}
        if "holds" not in ((params.get("item") or {}).get("choices") or []):
            return None
        price = int(((params.get("item") or {}).get("unit_price_by") or {}).get("holds") or 0)
        self.hold_price = price or self.hold_price
        most = int(((params.get("qty") or {}).get("max_by") or {}).get("holds") or 0)
        holds = int(ship.get("holds") or 0)
        room = int(ship.get("hold_cap") or holds) - holds
        qty = min(5, most, room)
        if qty <= 0 or price <= 0:
            return None
        self.gap("hold_curve")
        estimate = int(qty * price * 1.15)
        reserve = (holds + qty) * 70
        if credits - estimate < reserve:
            return None
        return "buy_equip", {"item": "holds", "qty": qty}, f"buy {qty} holds at about {price} cr each"

    def _sell_here(self, obs, trade, cargo, ship, last_day):
        params = trade.get("params") or {}
        sells = list((params.get("commodity") or {}).get("sell_choices") or [])
        most = (params.get("qty") or {}).get("max_by") or {}
        stock = ((obs.get("sector") or {}).get("port") or {}).get("stock") or {}
        basis = ship.get("cargo_cost_avg") or {}
        for name in sells:
            have = cargo.get(name, 0)
            qty = min(have, int((most.get(name) or {}).get("sell") or 0))
            listed = int((stock.get(name) or {}).get("price") or 0)
            if qty <= 0 or listed <= 0:
                continue
            offer = listed * self.haggle["sell"] // 100
            if offer < listed:
                offer = listed
            paid = float(basis.get(name) or 0)
            if paid and offer < paid and not last_day:
                continue
            self.gap("haggle_band")
            return "trade", {"side": "sell", "commodity": name, "qty": qty, "unit_price": offer}, f"sell {name} at {offer}"
        return None

    def _buy_here(self, obs, trade, ports, edges, here, free, credits, turns, warp_t, trade_t, last_day):
        params = trade.get("params") or {}
        buys = list((params.get("commodity") or {}).get("buy_choices") or [])
        most = (params.get("qty") or {}).get("max_by") or {}
        stock = ((obs.get("sector") or {}).get("port") or {}).get("stock") or {}
        day = int(obs.get("day") or 0)
        best = None
        for name in buys:
            listed = int((stock.get(name) or {}).get("price") or 0)
            if listed <= 0:
                continue
            offer = -(-listed * self.haggle["buy"] // 100)
            qty = min(free, int((most.get(name) or {}).get("buy") or 0), credits // max(1, offer))
            if qty <= 0:
                continue
            for sid, info in ports.items():
                if sid == here or info["sides"].get(name) != "buys":
                    continue
                room = self._amount(info, name, "buys")
                if room <= 0:
                    continue
                hops = self._dists(edges, here)[0].get(sid)
                if hops is None or hops > 8:
                    continue
                need = hops * warp_t + trade_t
                if last_day and need > turns - trade_t:
                    continue
                sell = self._price(sid, name, info, "buys", day) * self.haggle["sell"] / 100
                gain = (sell - offer) * min(qty, room)
                if gain <= 0:
                    continue
                score = gain / max(1, need + trade_t)
                if best is None or score > best[0]:
                    best = (score, name, min(qty, room), offer, sid)
        if best is None:
            return None
        _, name, qty, offer, sid = best
        self.gap("haggle_band")
        return "trade", {"side": "buy", "commodity": name, "qty": qty, "unit_price": offer}, f"buy {name} at {offer} for sector {sid}"

    def _target(self, obs, ports, edges, dist, here, cargo, free, credits, turns, warp_t, trade_t, last_day):
        day = int(obs.get("day") or 0)
        carried = [name for name in COMMODITIES if cargo.get(name, 0) > 0]
        best = None
        if carried:
            for name in carried:
                for sid, info in ports.items():
                    if sid == here or info["sides"].get(name) != "buys" or sid not in dist:
                        continue
                    room = self._amount(info, name, "buys")
                    if room <= 0:
                        continue
                    sell = self._price(sid, name, info, "buys", day)
                    gain = sell * min(cargo[name], room)
                    score = gain / max(1, dist[sid] * warp_t + trade_t)
                    if best is None or score > best[0]:
                        best = (score, sid, f"carry {name} to sector {sid}")
            if best is not None:
                return best[1], best[2]
        if free > 0:
            for sid_a, info_a in ports.items():
                if sid_a not in dist:
                    continue
                for name in COMMODITIES:
                    if info_a["sides"].get(name) != "sells":
                        continue
                    have = self._amount(info_a, name, "sells")
                    if have <= 0:
                        continue
                    cost = self._price(sid_a, name, info_a, "sells", day)
                    qty = min(free, have, int(credits // max(1.0, cost)))
                    if qty <= 0:
                        continue
                    from_a = self._dists(edges, sid_a)[0]
                    for sid_b, info_b in ports.items():
                        if sid_b == sid_a or info_b["sides"].get(name) != "buys" or sid_b not in from_a:
                            continue
                        room = self._amount(info_b, name, "buys")
                        if room <= 0:
                            continue
                        need = (dist[sid_a] + from_a[sid_b]) * warp_t + 2 * trade_t
                        if last_day and need > turns:
                            continue
                        sell = self._price(sid_b, name, info_b, "buys", day)
                        gain = (sell * 1.03 - cost * 0.92) * min(qty, room)
                        if gain <= 0:
                            continue
                        score = gain / max(1, need)
                        if best is None or score > best[0]:
                            best = (score, sid_a, f"buy {name} at sector {sid_a} for sector {sid_b}")
            if best is not None and best[1] != here:
                return best[1], best[2]
        return self._explore(obs, edges, dist, here)

    def _stardock_trip(self, obs, dist, here, carried, credits, turns, warp_t):
        """Go back for holds when the credits clearly cover five more."""
        ship = obs.get("ship") or {}
        holds = int(ship.get("holds") or 0)
        if carried or here == STARDOCK_SECTOR or int(obs.get("day") or 0) > self.days - 2:
            return None
        if holds >= int(ship.get("hold_cap") or holds):
            return None
        hops = dist.get(STARDOCK_SECTOR)
        if hops is None or hops > 4 or hops * warp_t > turns:
            return None
        price = self.hold_price or 0
        if price <= 0:
            return None
        self.gap("hold_curve")
        if credits < 4 * int(5 * price * 1.15) + (holds + 5) * 70:
            return None
        return STARDOCK_SECTOR, f"back to StarDock for holds (about {price} cr each)"

    def _explore(self, obs, edges, dist, here):
        adjacent = {int(row.get("id") or 0): row for row in (obs.get("adjacent") or [])}
        fresh = [sid for sid in sorted(edges.get(here, ())) if sid not in self.visited]
        ported = [sid for sid in fresh if (adjacent.get(sid) or {}).get("port")]
        if ported:
            return ported[0], f"look at the port in sector {ported[0]}"
        if fresh:
            return fresh[0], f"explore sector {fresh[0]}"
        far = sorted((d, sid) for sid, d in dist.items()
                     if sid != here and any(n not in self.visited for n in edges.get(sid, ())))
        if far:
            return far[0][1], f"head toward unexplored space at sector {far[0][1]}"
        if here != STARDOCK_SECTOR:
            return STARDOCK_SECTOR, "back to StarDock"
        return None, "nothing left to explore"


def _legal(obs: dict[str, Any], kind: str) -> dict[str, Any] | None:
    for row in obs.get("legal_actions") or []:
        if row.get("kind") == kind:
            return row
    return None


def _tradeable(obs: dict[str, Any], sid: int) -> bool:
    """True when the port report says this port has something to sell you today."""
    ship = obs.get("ship") or {}
    if int(ship.get("cargo_free") or 0) <= 0 or int(obs.get("credits") or 0) <= 0:
        return False
    for row in obs.get("known_ports") or []:
        if int(row.get("sector_id") or 0) != sid:
            continue
        sides = port_sides(row.get("class"))
        if not sides:
            return False
        stock = row.get("stock") or {}
        return any(sides[name] == "sells" and int((stock.get(name) or {}).get("current") or 0) > 0
                   for name in COMMODITIES)
    return False


def leave_stardock(obs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Warp to a neighbor whose port can trade today, else one with a port, else the first warp."""
    sector = obs.get("sector") or {}
    if int(sector.get("id") or 0) != STARDOCK_SECTOR:
        raise CockpitSeatError("day 1 starts at StarDock")
    warp = _legal(obs, "warp")
    if not warp or not warp.get("legal"):
        reason = (warp or {}).get("reason") or "warp is not legal"
        raise CockpitSeatError(str(reason))
    choices = ((warp.get("params") or {}).get("target") or {}).get("choices") or []
    if not choices:
        choices = list(sector.get("warps_out") or [])
    if not choices:
        raise CockpitSeatError("StarDock shows no warp")
    for item in choices:
        if _tradeable(obs, int(item)):
            return "warp", {"target": int(item)}
    legal = {int(item) for item in choices}
    ported = [
        int(row["id"])
        for row in (obs.get("adjacent") or [])
        if row.get("port") and int(row.get("id") or 0) in legal
    ]
    return "warp", {"target": ported[0] if ported else int(choices[0])}


def dock_or_wait(obs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Buy one unit when the port form is open. Otherwise wait."""
    trade = _legal(obs, "trade")
    port = (obs.get("sector") or {}).get("port")
    if port and trade and trade.get("legal"):
        params = trade.get("params") or {}
        commodity = params.get("commodity") or {}
        buys = list(commodity.get("buy_choices") or [])
        sells = list(commodity.get("sell_choices") or [])
        if buys:
            return "trade", {"side": "buy", "commodity": buys[0], "qty": 1}
        if sells:
            return "trade", {"side": "sell", "commodity": sells[0], "qty": 1}
    return "wait", {}


def http_calls(client: Any, token: str) -> tuple[Get, Post]:
    """get/post over one httpx.AsyncClient with the seat's bearer token."""
    headers = {"authorization": f"Bearer {token}"}

    async def get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        reply = await client.get(path, params=params, headers=headers)
        if reply.status_code != 200:
            raise CockpitHTTPError(reply.status_code, _detail(reply))
        return reply.json()

    async def post(path: str, body: dict[str, Any]) -> dict[str, Any]:
        reply = await client.post(path, json=body, headers=headers)
        if reply.status_code != 200:
            raise CockpitHTTPError(reply.status_code, _detail(reply))
        return reply.json()

    return get, post


def _detail(reply: Any) -> Any:
    try:
        return reply.json().get("detail")
    except Exception:
        return reply.text[:200]


async def run_http(client: Any, seat_id: str, token: str, days: int, **kwargs: Any) -> dict[str, Any]:
    """Play ``days`` days for one seat through an httpx.AsyncClient."""
    get, post = http_calls(client, token)
    return await CockpitSeat(seat_id, get, post).run(days, **kwargs)
