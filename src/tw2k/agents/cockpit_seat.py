"""A seat that plays from the cockpit harness only.

NOTE 54. The client reads four GETs for its own seat and posts the same
action kinds the redesign cockpit can send. It does not import the match,
the runner, or an observation builder. Default games never call it.
AI_COCKPIT_SEAT_MODE stays legacy until a test turns it on.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from ..engine import constants as K

# Kinds the redesign page can post. Computer, planet, port, and ship forms
# included. The day-1 loop uses warp, trade, and wait.
COCKPIT_KINDS = frozenset({
    "warp", "trade", "land_planet", "liftoff", "scan", "attack", "wait",
    "deploy_fighters", "deploy_mines", "deploy_genesis", "probe",
    "plot_course", "photon_missile", "broadcast", "avoid",
    "load_planet_cargo", "dump_planet_cargo", "assign_colonists",
    "deposit_planet_defense", "withdraw_planet_defense", "build_citadel",
    "set_military_reaction", "deposit_treasury", "withdraw_treasury",
    "planet_buy_transporter", "planet_transport", "recall_deployed",
    "buy_ship", "buy_equip", "sell_ship", "launch_beacon",
    "hail", "radio", "surrender", "retreat",
    "rob", "steal", "port_upgrade", "port_build",
    "bank_deposit", "bank_withdraw", "bank_transfer",
    "terra_colonists", "corp_create", "ship_transport", "tow_engage",
    "tow_release",
})

READS = ("observation", "reference", "events", "status")
STARDOCK_SECTOR = 1

Get = Callable[..., Awaitable[dict[str, Any]]]
Post = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


class CockpitSeatOff(RuntimeError):
    """The seat stays unwired while AI_COCKPIT_SEAT_MODE is legacy."""


class CockpitSeatError(RuntimeError):
    """The cockpit surface did not offer the day-1 move."""


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


def _legal(obs: dict[str, Any], kind: str) -> dict[str, Any] | None:
    for row in obs.get("legal_actions") or []:
        if row.get("kind") == kind:
            return row
    return None


def leave_stardock(obs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Warp to the first hop the cockpit says is legal."""
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
