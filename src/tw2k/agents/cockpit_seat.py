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

NOTE 95. The same client plays a V311_PROFILE game. It lifts off the home
world before it warps, waits out an HTTP 429 from the live action route,
drops a plotted course the route refused, and stays out of a sector an event
already named as a hazard. An optional LLM hook reads its key from the
environment and is skipped when that variable is empty, so tests open no socket.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import urllib.request
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

    async def _post_turn(self, turn_seq: int, kind: str, args: dict[str, Any]) -> str:
        """Post one action. ``skip`` means the turn closed before the post landed.

        NOTE 95. V311_PROFILE turns the live action route on, and that route
        answers 429 once 30 posts land inside 10 seconds. The seat waits and
        retries the same turn. A 409 means the day clock moved the turn on.
        """
        try:
            await self.post_action(turn_seq, kind, args)
        except CockpitHTTPError as exc:
            text = _http_text(exc.detail)
            if exc.status == 409 and "game_over" in text:
                return "over"
            if exc.status == 409 and ("stale_turn" in text or "not_awaiting" in text):
                return "skip"
            # The live route counts every post. Replaying the same action after the
            # wait can land on a day the clock already rolled, so decide again.
            if exc.status == 429:
                await asyncio.sleep(1.0)
                return "reread"
            raise
        return "ok"

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

    async def run(self, days: int, *, idle_s: float = 600.0, max_posts: int = 6000,
                  llm_ask: Callable[..., Any] | None = None) -> dict[str, Any]:
        """Play ``days`` game days from the day the seat starts on. Returns the day table, refusals, and gaps.

        NOTE 56 item 7a: ``days`` counts from now. A seat that joins on day 4 with
        days=1 plays day 4.
        """
        if not K.ai_cockpit_seat_on():
            raise CockpitSeatOff("AI_COCKPIT_SEAT_MODE is legacy")
        reference = await self.read("reference")
        first = await self.read("observation", {"wait_s": 2, "peek": 1})
        start_day = int((first.get("observation") or {}).get("day") or first.get("day") or 1)
        end_day = start_day + max(0, int(days)) - 1
        brain = SeatBrain(end_day, base=reference_base(reference), hold_price=reference_hold_price(reference))
        report: dict[str, Any] = {
            "seat": self.seat_id,
            "days_asked": int(days),
            "start_day": start_day,
            "end_day": end_day,
            "reference_sections": [row.get("id") for row in (reference.get("sections") or [])],
            "days": [],
            "posts": 0,
            "refused": [],
            "kinds": {},
            "log": [],
            "cockpit_fields": False,
            "died": False,
        }
        table: dict[int, dict[str, Any]] = {}
        since = 0
        last_turn = 0
        last_progress = time.monotonic()
        finished = days <= 0 or bool(first.get("game_over"))
        seen_day = start_day
        while not finished:
            if time.monotonic() - last_progress > idle_s:
                raise CockpitSeatError("no turn opened for the seat")
            body = await self.read("observation", {"wait_s": 2, "peek": 1})
            obs = body.get("observation") or {}
            cockpit = body.get("cockpit")
            if cockpit is not None:
                report["cockpit_fields"] = True
            if obs and start_day <= int(obs.get("day") or 0) <= end_day:
                _note_day(table, obs, int(body.get("turn_seq") or 0) if cockpit is not None else None)
            if body.get("game_over") or obs.get("finished"):
                break
            if obs and int(obs.get("day") or 0) > end_day:
                break
            if obs and cockpit is not None and int(obs.get("day") or 0) != seen_day:
                # A new day: Rules and Help prints today's next-hold price.
                seen_day = int(obs.get("day") or 0)
                brain.hold_price = reference_hold_price(await self.read("reference")) or brain.hold_price
            if obs and obs.get("alive") is False:
                report["died"] = True
                break
            if not body.get("awaiting_input") or body.get("peek") or not obs:
                await asyncio.sleep(0.05)
                continue
            turn = int(body.get("turn_seq") or 0)
            if turn <= last_turn:
                await asyncio.sleep(0.05)
                continue
            last_progress = time.monotonic()
            picked = llm_choose(obs, cockpit, ask=llm_ask)
            if picked is None:
                kind, args, why = brain.decide(obs, cockpit)
            else:
                kind, args, why = picked
            day = int(obs.get("day") or 0)
            row = table[day]
            report["posts"] += 1
            row["posts"] += 1
            report["kinds"][kind] = report["kinds"].get(kind, 0) + 1
            if report["posts"] > max_posts:
                raise CockpitSeatError("too many posts")
            try:
                outcome = await self._post_turn(turn, kind, args)
            except CockpitHTTPError as exc:
                report["refused"].append({"day": day, "turn_seq": turn, "kind": kind, "args": args,
                                          "why": why, "http": exc.status, "detail": exc.detail})
                row["refused"] += 1
                brain.refused(kind, args, _http_text(exc.detail))
                last_turn = turn
                continue
            if outcome in ("skip", "reread"):
                # The day clock rolled, the turn closed, or the live route asked for a pause.
                report["posts"] -= 1
                row["posts"] -= 1
                report["kinds"][kind] = report["kinds"].get(kind, 1) - 1
                if report["kinds"][kind] <= 0:
                    report["kinds"].pop(kind, None)
                if outcome == "skip":
                    last_turn = turn
                continue
            if outcome == "over":
                report["posts"] -= 1
                row["posts"] -= 1
                report["kinds"][kind] = report["kinds"].get(kind, 1) - 1
                if report["kinds"][kind] <= 0:
                    report["kinds"].pop(kind, None)
                finished = True
                break
            last_turn = turn
            result = await self._result(turn, fields=cockpit is not None)
            _note_result(table, day, result, turn)
            ok = result.get("ok")
            if ok is False:
                error = str(result.get("error") or "")
                refusal = {"day": day, "turn_seq": turn, "kind": kind, "args": args, "why": why, "error": error}
                if result.get("haggle"):
                    refusal["haggle"] = result["haggle"]
                report["refused"].append(refusal)
                row["refused"] += 1
                brain.refused(kind, args, error)
            elif ok:
                brain.done(kind, args, verdict=bool(result.get("verdict")))
                if kind == "trade":
                    row["trades"] += 1
                    row["buys" if args.get("side") == "buy" else "sells"] += 1
                if kind == "buy_equip" and args.get("item") == "holds":
                    row["holds_bought"] += int(args.get("qty") or 0)
            since = await self._log_rows(since, report, brain)
            if result.get("game_over"):
                finished = True
        final = await self.read("observation", {"peek": 1})
        final_obs = final.get("observation") or {}
        if final_obs and start_day <= int(final_obs.get("day") or 0) <= end_day:
            _note_day(table, final_obs)
        report["days"] = [table[d] for d in sorted(table) if start_day <= d <= end_day]
        report["gaps"] = brain.gap_rows(fields=bool(report["cockpit_fields"]))
        report["day_end_source"] = "verdict after the last result" if report["cockpit_fields"] else "last read of the day"
        report["final"] = _snapshot(final_obs)
        return report

    async def _result(self, turn: int, *, fields: bool = False) -> dict[str, Any]:
        """The engine's verdict for ``turn``: the cockpit verdict field when it is on, else status last_result.

        The verdict carries the day, credits and net worth right after the action, so
        the day row ends after its last result even when the day rolls before the
        next read. Without it, the row ends at the last read of that day.
        """
        for _ in range(200):
            body = await self.read("observation", {"wait_s": 1, "peek": 1})
            verdict = (body.get("cockpit") or {}).get("verdict") or {}
            if fields and int(verdict.get("turn_seq") or -1) >= turn:
                return {
                    "ok": verdict.get("ok"), "error": verdict.get("reason"), "game_over": body.get("game_over"),
                    "verdict": True, "day": verdict.get("day"), "credits": verdict.get("credits"),
                    "net_worth": verdict.get("net_worth"), "turns_left": verdict.get("turns_left"),
                    "sector": verdict.get("sector_id"), "haggle": verdict.get("haggle"),
                }
            last = body.get("last_result") or {}
            if not fields and int(last.get("turn_seq") or -1) >= turn:
                obs = body.get("observation") or {}
                return {"ok": last.get("ok"), "error": last.get("error"), "game_over": body.get("game_over"),
                        "observation": obs}
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


def _note_day(table: dict[int, dict[str, Any]], obs: dict[str, Any], turn: int | None = None) -> None:
    day = int(obs.get("day") or 0)
    if day <= 0:
        return
    held = table.get(day)
    if held is not None and turn is not None and turn <= int(held.get("verdict_turn") or 0):
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
    row["experience_end"] = int(obs.get("experience") or 0)
    row["rank_title"] = str(obs.get("rank") or "")
    name = str(obs.get("self_name") or "")
    for ranked in obs.get("trader_rankings") or []:
        if str(ranked.get("name") or "") == name and ranked.get("rank") is not None:
            row["experience_place"] = int(ranked["rank"])
            break
    rivals = obs.get("rivals") or []
    row["net_worth_place"] = 1 + sum(1 for rival in rivals if int(rival.get("net_worth") or 0) > worth)


def _note_result(table: dict[int, dict[str, Any]], day: int, result: dict[str, Any], turn: int = 0) -> None:
    """NOTE 56 item 7b: the day ends after its last result lands, not at the read before it."""
    row = table.get(day)
    if row is None:
        return
    if result.get("verdict"):
        if int(result.get("day") or 0) != day:
            return
        # A cached read from before this action must not move the day end back.
        row["verdict_turn"] = int(turn)
        if result.get("credits") is not None:
            row["credits_end"] = int(result["credits"])
        if result.get("net_worth") is not None:
            row["net_worth_end"] = int(result["net_worth"])
        if result.get("sector") is not None:
            row["sector_end"] = int(result["sector"])
        return
    spent = result.get("turns_spent")
    if spent is not None:
        row["turns_used"] = int(row["turns_used"]) + int(spent)
    obs = result.get("observation") or {}
    if obs and int(obs.get("day") or 0) == day:
        _note_day(table, obs)


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
    # NOTE 95 (AI-c). The adjacent row grows mines, fighters and NavHaz only after a scan.
    # The v3.11 stake is 300 credits and a density scanner is 2,000, so this seat cannot buy one.
    "hazard_unseen": (
        "Warp into a sector the cockpit has not described",
        "Mines, fighters and NavHaz in the next sector",
        "The adjacent row lists them only after a scan. This seat cannot afford a scanner on the v3.11 stake, so it learns a sector from the event after it enters.",
        "The original also hides mines and fighters until a scanner or a hit",
    ),
}

# NOTE 56: where each gap sits once the cockpit block is on (COCKPIT_FIELDS_MODE tw2002).
GAP_FIELDS = {
    "result_line": ("closed", "The verdict field under the command keys: OK or REFUSED, the reason, turns spent and the credits change (cockpit.verdict). It survives a reload."),
    "haggle_band": ("not in original", "The trade form shows the port's quote, each counter and how the haggle ended. The accept band is not printed, as in the original. The seat still offers 92% on a buy and 103% on a sale."),
    "counter_in_log": ("closed", "The trade form shows the counter and the next offer (cockpit.haggle)."),
    "price_away": ("closed", "Computer R lists this seat's own last-seen price per product with the day, at ports it docked at (cockpit.port_notes), next to the original status, amount and % of max."),
    "price_rule": ("not in original", "Not printed: the original never shows a stock-to-price rule (REPORT2.md line 32 'Prices fall as the port fills'). Rules and Help lists it as not shown in the original. The seat still guesses for a port it never docked at."),
    "hold_curve": ("closed", "The StarDock holds form shows the next-hold price, how many you can afford and, once an amount is typed, the total before CONFIRM (cockpit.hold_quote)."),
    "one_way": ("same as original", "Computer K lists warps for visited sectors only, as the original's CIM warp data."),
    "challenge_strength": ("same as original", "The challenge shows the enemy fighters and your own, as the original."),
    "hazard_unseen": (
        "cockpit bug",
        "Still absent on the adjacent row before a scan. The seat avoids a sector after an event names the mines, fighters or NavHaz.",
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
        self.bad_plots: set[int] = set()
        self.hazards: set[int] = set()
        self._turn_gaps: set[str] | None = None
        self.hold_price = int(hold_price or 0)
        self.dock_trip = False
        # NOTE 56: the cockpit block for this turn (None on a legacy server).
        self.cockpit: dict[str, Any] | None = None

    # ---- notes ---------------------------------------------------------------

    def gap(self, gid: str) -> None:
        """Count a gap once for each turn that needed it."""
        if self._turn_gaps is None:
            self.gaps[gid] = self.gaps.get(gid, 0) + 1
        else:
            self._turn_gaps.add(gid)

    def gap_rows(self, fields: bool = False) -> list[dict[str, Any]]:
        """Gap rows, most turns first. With the cockpit block, every listed gap gets a row and a status."""
        rows = []
        ids = list(self.gaps)
        if fields:
            ids += [gid for gid in GAP_TEXT if gid not in self.gaps]
        for gid in sorted(ids, key=lambda g: (-self.gaps.get(g, 0), list(GAP_TEXT).index(g))):
            decision, needed, cockpit, original = GAP_TEXT[gid]
            row = {"id": gid, "count": self.gaps.get(gid, 0), "decision": decision, "needed": needed,
                   "cockpit": cockpit, "original": original}
            if fields:
                status, where = GAP_FIELDS[gid]
                row["status"] = status
                row["cockpit"] = where
            rows.append(row)
        return rows

    def read_log(self, ev: dict[str, Any]) -> None:
        summary = str(ev.get("summary") or "")
        if "counter " in summary and self.cockpit is None:
            self.gap("counter_in_log")
        low = summary.lower()
        sid = ev.get("sector_id")
        if sid is None:
            sid = (ev.get("facts") or {}).get("sector_id")
        if sid is not None and any(tok in low for tok in ("mines hit", "navhaz", "armid", "limpet")):
            self.hazards.add(int(sid))

    def refused(self, kind: str, args: dict[str, Any], error: str) -> None:
        if kind == "trade":
            side = str(args.get("side") or "")
            countered = "counter" in error
            if side in self.haggle and not (countered and self.cockpit is not None):
                self.haggle[side] = 100
            if countered and self.cockpit is None:
                self.gap("counter_in_log")
        if kind == "warp" and self.last_plan:
            self.bad_warps.add((int(self.last_plan.get("from") or 0), int(args.get("target") or 0)))
        if kind == "plot_course":
            self.bad_plots.add(int(args.get("target") or 0))
        low = error.lower()
        if any(tok in low for tok in ("mines", "navhaz", "armid", "limpet")) and self.last_plan:
            self.hazards.add(int(args.get("target") or self.last_plan.get("to") or 0))

    def done(self, kind: str, args: dict[str, Any], *, verdict: bool = False) -> None:
        if not verdict:
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
        # A sector that already dealt mine or NavHaz damage stays off the route.
        # The hop out of the sector we are standing in is kept when every neighbor is one.
        for src in list(edges):
            if src == here:
                continue
            edges[src] = {dst for dst in edges[src] if dst not in self.hazards}
        safe_here = {dst for dst in edges[here] if dst not in self.hazards}
        if safe_here:
            edges[here] = safe_here
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
        if self.cockpit is not None:
            # NOTE 56: Computer R now lists this seat's own last-seen price at a port it docked at.
            note = ((self.cockpit.get("port_notes") or {}).get(str(sid)) or {}).get(name)
            if note and note.get("side") == side and note.get("price") is not None:
                return float(note["price"])
            # Never docked there: the original shows no price either, so only the stock rule is left.
            self.gap("price_rule")
            return self._rule_price(name, info, side)
        seen = self.prices.get((sid, name))
        if seen and seen["side"] == side and int(seen["day"]) >= day - 1:
            return float(seen["price"])
        self.gap("price_away")
        self.gap("price_rule")
        return self._rule_price(name, info, side)

    def _rule_price(self, name: str, info: dict[str, Any], side: str) -> float:
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

    def decide(self, obs: dict[str, Any], cockpit: dict[str, Any] | None = None) -> tuple[str, dict[str, Any], str]:
        self.cockpit = cockpit
        if cockpit is not None:
            quote = cockpit.get("hold_quote") or {}
            if quote.get("next_price"):
                self.hold_price = int(quote["next_price"])
        self._turn_gaps = set()
        try:
            return self._decide(obs)
        finally:
            for gid in self._turn_gaps:
                self.gaps[gid] = self.gaps.get(gid, 0) + 1
            self._turn_gaps = None

    def _decide(self, obs: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
        self._record(obs)
        self._note_here(obs)
        if obs.get("ferrengi_encounter") or obs.get("fighter_challenge"):
            return self._answer(obs)
        # V311 starts the seat landed on its home world. Warp and trade both say
        # "lift off first", and a wait there only burns the day.
        lift = _legal(obs, "liftoff") or {}
        if lift.get("legal"):
            return "liftoff", {}, "lift off before warp or trade"
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
            answer = self._take_counter(trade, cargo, free, credits)
            if answer is not None:
                return answer
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

    def _take_counter(self, trade: dict[str, Any], cargo: dict[str, int], free: int, credits: int):
        """NOTE 56: the trade form shows the port's counter. Offer what it says, as the original's [default]."""
        pending = (self.cockpit or {}).get("haggle")
        if not pending:
            return None
        name = str(pending.get("commodity") or "")
        side = str(pending.get("side") or "")
        offer = int(pending.get("next_offer") or 0)
        params = trade.get("params") or {}
        choices = (params.get("commodity") or {}).get("buy_choices" if side == "buy" else "sell_choices") or []
        most = int((((params.get("qty") or {}).get("max_by") or {}).get(name) or {}).get(side) or 0)
        if name not in choices or offer <= 0:
            return None
        qty = min(cargo.get(name, 0), most) if side == "sell" else min(free, most, credits // offer)
        if qty <= 0:
            return None
        return "trade", {"side": side, "commodity": name, "qty": qty, "unit_price": offer}, f"take the port's counter of {offer}"

    def _go(self, obs: dict[str, Any], warp: dict[str, Any], target: int, first: dict[int, int], why: str) -> tuple[str, dict[str, Any], str]:
        here = int((obs.get("sector") or {}).get("id") or 0)
        choices = [int(x) for x in (((warp.get("params") or {}).get("target") or {}).get("choices") or [])]
        hop = first.get(target)
        if hop is not None and hop in choices and hop not in self.hazards:
            return self._warp_hop(obs, here, hop, target, why)
        if hop is not None and hop in self.hazards:
            safe = [c for c in choices if c not in self.hazards]
            if safe:
                return self._warp_hop(obs, here, safe[0], target, "around a known hazard")
        elif hop is not None:
            self.no_edge.add((here, hop))
            self.gap("one_way")
        plot = _legal(obs, "plot_course") or {}
        execute = ((plot.get("params") or {}).get("execute") or {})
        if plot.get("legal") and execute.get("legal", True) and target not in self.bad_plots:
            self.last_plan = {"from": here, "to": target}
            if hop is None or self._hop_unread(obs, hop):
                self.gap("hazard_unseen")
            return "plot_course", {"target": target, "execute": True}, why + " (course plotter)"
        safe = [c for c in choices if c not in self.hazards]
        if safe:
            return self._warp_hop(obs, here, safe[0], target, "first warp")
        if choices:
            return self._warp_hop(obs, here, choices[0], target, "first warp")
        return "wait", {}, "no warp out"

    def _warp_hop(self, obs: dict[str, Any], here: int, hop: int, target: int, why: str):
        self.last_plan = {"from": here, "to": target}
        if self._hop_unread(obs, hop):
            self.gap("hazard_unseen")
        return "warp", {"target": hop}, why

    def _note_here(self, obs: dict[str, Any]) -> None:
        """Remember a hazard the cockpit is showing right now."""
        sector = obs.get("sector") or {}
        here = int(sector.get("id") or 0)
        if sector.get("mines") or sector.get("nav_hazard_pct"):
            self.hazards.add(here)
        me = str(obs.get("self_id") or "")
        for row in obs.get("adjacent") or []:
            sid = int(row.get("id") or 0)
            if not sid:
                continue
            if int(row.get("mines") or 0) > 0:
                self.hazards.add(sid)
            owner = row.get("fighter_owner")
            if owner and str(owner) != me and int(row.get("fighter_count") or 0) > 0:
                self.hazards.add(sid)
            nav = row.get("navhaz")
            try:
                nav_n = float(nav) if nav not in (None, "") else 0.0
            except (TypeError, ValueError):
                nav_n = 0.0
            if nav_n > 0:
                self.hazards.add(sid)

    def _hop_unread(self, obs: dict[str, Any], hop: int) -> bool:
        """True when this hop's mines, fighters and NavHaz are not on the adjacent row."""
        if hop in self.visited or hop in self.hazards:
            return False
        for row in obs.get("adjacent") or []:
            if int(row.get("id") or 0) != hop:
                continue
            if any(key in row for key in ("mines", "fighter_count", "navhaz")):
                return False
            return True
        return True

    def _answer(self, obs: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
        self.gap("challenge_strength")
        here = int((obs.get("sector") or {}).get("id") or 0)
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
            if kind == "retreat":
                # Walking back into the same fighters spends the day. Stay out.
                self.hazards.add(here)
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
        quote = (self.cockpit or {}).get("hold_quote")
        if quote is not None:
            # NOTE 56: the StarDock form prints the total for each amount before CONFIRM.
            totals = {int(q): int(t) for q, t in (quote.get("totals") or {}).items()}
            fits = [q for q, total in totals.items() if q <= min(most, room) and credits - total >= (holds + q) * 70]
            if not fits:
                return None
            qty = max(fits)
            return "buy_equip", {"item": "holds", "qty": qty}, f"buy {qty} holds for {totals[qty]:,} cr"
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
        if self.cockpit is None:
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


def _http_text(detail: Any) -> str:
    if isinstance(detail, dict):
        return json.dumps(detail, sort_keys=True)
    return str(detail)


# NOTE 95. The heuristic brain stays the default. A key in the environment
# selects the optional hook. No key, no URL, and no socket.
LLM_KEY_ENV = "TW2K_COCKPIT_LLM_KEY"
LLM_URL_ENV = "TW2K_COCKPIT_LLM_URL"
LLM_MODEL_ENV = "TW2K_COCKPIT_LLM_MODEL"


def cockpit_llm_key() -> str:
    """The seat's LLM key, or "" when the operator did not set one. Never a default."""
    return os.environ.get(LLM_KEY_ENV, "").strip()


def llm_choose(
    obs: dict[str, Any],
    cockpit: dict[str, Any] | None = None,
    *,
    key: str | None = None,
    ask: Callable[..., Any] | None = None,
) -> tuple[str, dict[str, Any], str] | None:
    """One LLM choice, or None so the heuristic decides.

    ``key`` defaults to ``TW2K_COCKPIT_LLM_KEY``. An empty key returns before
    ``ask`` is called. Tests pass ``ask`` and never open a socket.
    """
    secret = cockpit_llm_key() if key is None else str(key or "").strip()
    if not secret:
        return None
    caller = ask or _llm_http_choose
    try:
        picked = caller(secret, obs, cockpit)
    except Exception:
        return None
    return _coerce_llm(picked)


def _coerce_llm(picked: Any) -> tuple[str, dict[str, Any], str] | None:
    if not isinstance(picked, (tuple, list)) or len(picked) < 2:
        return None
    kind = str(picked[0] or "")
    args = picked[1] if isinstance(picked[1], dict) else None
    if kind not in COCKPIT_KINDS or args is None:
        return None
    why = str(picked[2]) if len(picked) > 2 else "llm"
    return kind, args, why


def _llm_http_choose(key: str, obs: dict[str, Any], cockpit: dict[str, Any] | None) -> Any:
    """OpenAI-compatible chat completion. The URL comes from the environment too.

    UNVERIFIED: no single public endpoint is specified for this hook, so the
    operator supplies ``TW2K_COCKPIT_LLM_URL``. Missing URL returns None and
    does not open a socket. The key is sent as a bearer header and is not logged.
    """
    url = os.environ.get(LLM_URL_ENV, "").strip()
    if not url or not key:
        return None
    legal = [row.get("kind") for row in (obs.get("legal_actions") or []) if row.get("legal")]
    prompt = {
        "sector": (obs.get("sector") or {}).get("id"),
        "day": obs.get("day"),
        "turns_remaining": obs.get("turns_remaining"),
        "credits": obs.get("credits"),
        "planet_landed": obs.get("planet_landed"),
        "legal": legal,
        "cockpit": bool(cockpit),
    }
    body = json.dumps({
        "model": os.environ.get(LLM_MODEL_ENV, "").strip() or "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Reply with one JSON object {\"kind\", \"args\", \"why\"}. kind must be one of legal."},
            {"role": "user", "content": json.dumps(prompt)},
        ],
    }).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"authorization": f"Bearer {key}", "content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as reply:  # noqa: S310 - operator-supplied URL
        payload = json.loads(reply.read().decode())
    text = ""
    choices = payload.get("choices") or []
    if choices:
        text = str(((choices[0].get("message") or {}).get("content")) or "")
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    row = json.loads(text[start:end + 1])
    return (row.get("kind"), row.get("args") or {}, row.get("why") or "llm")
