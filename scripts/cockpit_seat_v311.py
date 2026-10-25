"""NOTE 95. Cockpit seat on V311_PROFILE, test server only.

The seat process is this one. AI_COCKPIT_SEAT_MODE is set here and nowhere
in the repo default. The seat still posts through the four harness routes.

    python3 scripts/cockpit_seat_v311.py solo
    python3 scripts/cockpit_seat_v311.py versus
    python3 scripts/cockpit_seat_v311.py scenarios

Ports: 9181 solo, 9182 and 9183 versus. None of those are in the protected list.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "playtests" / "cockpit-ai-seat-v3"
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TOK_A = "note95-token-bot-0000000000000001"
TOK_B = "note95-token-seat-000000000000002"

COMMODITIES = ("fuel_ore", "organics", "equipment")


def enable_v311() -> None:
    import tw2k.engine.constants as K

    K.V311_PROFILE = "v311"
    K.AI_COCKPIT_SEAT_MODE = "tw2002"


def _acceptance():
    spec = importlib.util.spec_from_file_location(
        "seat_brain_acceptance_note95", ROOT / "scripts" / "seat_brain_acceptance.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def install_code_bots(lineup: dict[str, str]) -> None:
    """Swap named heuristic slots for the standard N1/N2/N3 brains. H stays heuristic.

    The cockpit seat is not in this map. It remains an external client.
    """
    if getattr(install_code_bots, "done", False):
        return
    install_code_bots.done = True
    from tw2k.agents.base import BaseAgent
    from tw2k.engine import Action
    from tw2k.server.runner import MatchRunner

    makers = {
        "N1": _acceptance().n1_brain,
        "N2": _acceptance().n2_brain,
        "N3": _acceptance().SeatBrain,
    }
    orig = MatchRunner._build_agents

    class CodeBotAgent(BaseAgent):
        kind = "heuristic"

        def __init__(self, player_id: str, name: str, brain: Any) -> None:
            super().__init__(player_id, name)
            self.brain = brain
            self.errors = 0

        async def act(self, observation):
            try:
                act = self.brain.decide(observation.model_dump(mode="json"))
            except Exception:
                self.errors += 1
                act = {"kind": "wait", "args": {}}
            return Action(kind=str(act.get("kind") or "wait"), args=dict(act.get("args") or {}),
                          thought=str(act.get("thought") or ""))

    def patched(self, spec, universe, seat_players=True):
        agents = orig(self, spec, universe, seat_players=seat_players)
        fresh = {pid: makers[kind]() for pid, kind in lineup.items() if kind in makers}
        out = []
        for agent in agents:
            kind = lineup.get(agent.player_id)
            if kind in makers and agent.player_id in fresh:
                out.append(CodeBotAgent(agent.player_id, f"{kind}-{agent.player_id}", fresh[agent.player_id]))
            else:
                out.append(agent)
        return out

    MatchRunner._build_agents = patched


def _free_port(preferred: int) -> int:
    import socket

    for port in (preferred, preferred + 1, preferred + 2, preferred + 3):
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"no free port at {preferred}")


class PortHost:
    """A real local server. The seat still talks HTTP, only to this port."""

    def __init__(self, spec, port: int) -> None:
        import threading

        import uvicorn

        from tw2k.server.app import create_app

        self.port = port
        self.app = create_app(auto_start=False)
        self.runner = self.app.state.runner
        self.server = uvicorn.Server(
            uvicorn.Config(self.app, host="127.0.0.1", port=port, log_level="warning"))
        self._spec = spec
        self.thread = threading.Thread(target=lambda: asyncio.run(self._main()), daemon=True)

    async def _main(self) -> None:
        async def start() -> None:
            while not self.server.started:
                await asyncio.sleep(0.05)
            await self.runner.start(self._spec)

        task = asyncio.create_task(start())
        await self.server.serve()
        task.cancel()
        await self.runner.stop()

    def __enter__(self) -> PortHost:
        self.thread.start()
        deadline = time.time() + 40
        while time.time() < deadline and not (self.server.started and self.runner.state.universe is not None):
            time.sleep(0.05)
        if self.runner.state.universe is None:
            raise RuntimeError("the test server did not start")
        return self

    def __exit__(self, *exc) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=20)

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"


async def with_match(spec, fn):
    """Start one match and hand the ASGI client to ``fn``."""
    from tests.test_external_harness_phase1 import _wait_until
    from tw2k.server.app import create_app

    app = create_app(auto_start=False)
    runner = app.state.runner
    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 5555))
    http = httpx.AsyncClient(transport=transport, base_url="http://harness.test", timeout=60.0)
    await runner.start(spec)
    if not await _wait_until(lambda: runner.state.universe is not None, tries=500, dt=0.05):
        raise RuntimeError("match did not start")
    try:
        return await fn(http, runner)
    finally:
        await runner.stop()
        await http.aclose()


def seat_client(http: httpx.AsyncClient, seat_id: str, token: str):
    from tw2k.agents.cockpit_seat import CockpitSeat, http_calls

    get, post = http_calls(http, token)
    return CockpitSeat(seat_id, get, post)


async def await_turn(seat, idle_s: float = 90.0) -> dict[str, Any]:
    deadline = time.monotonic() + idle_s
    while time.monotonic() < deadline:
        body = await seat.read("observation", {"wait_s": 2, "peek": 1})
        obs = body.get("observation") or {}
        if body.get("game_over") or obs.get("finished"):
            return body
        if body.get("awaiting_input") and not body.get("peek") and obs:
            return body
        await asyncio.sleep(0.05)
    raise TimeoutError("no turn opened for the scripted seat")


def legal(obs: dict[str, Any], kind: str) -> dict[str, Any] | None:
    for row in obs.get("legal_actions") or []:
        if row.get("kind") == kind:
            return row
    return None


async def post_turn(seat, body: dict[str, Any], kind: str, args: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    outcome = await seat._post_turn(int(body["turn_seq"]), kind, args)
    if outcome == "over":
        return outcome, body
    nxt = await await_turn(seat)
    return outcome, nxt


def _offer(listed: int, side: str) -> int:
    if side == "buy":
        return -(-listed * 92 // 100)
    return listed * 103 // 100


def _stockpile(obs: dict[str, Any], planet_id: int) -> dict[str, int]:
    """Ore on the seat's own planet, from the observation it is allowed to read."""
    for row in obs.get("owned_planets") or []:
        if int(row.get("id") or 0) == planet_id:
            pile = row.get("stockpile") or {}
            return {name: int(pile.get(name) or 0) for name in COMMODITIES}
    return {name: 0 for name in COMMODITIES}


def _sellers(obs: dict[str, Any], name: str) -> list[int]:
    idx = COMMODITIES.index(name)
    found = []
    for row in obs.get("known_ports") or []:
        code = str(row.get("class") or "")
        if len(code) == 3 and code[idx] == "S":
            found.append(int(row.get("sector_id") or 0))
    return [sid for sid in found if sid]


def _hop_toward(obs: dict[str, Any], target: int) -> int | None:
    """First hop on the cockpit's own warp notes, or a warp the form allows."""
    here = int((obs.get("sector") or {}).get("id") or 0)
    known = {int(k): [int(x) for x in v] for k, v in (obs.get("known_warps") or {}).items()}
    known[here] = [int(w) for w in ((obs.get("sector") or {}).get("warps_out") or [])]
    dist = {here: 0}
    first: dict[int, int] = {}
    queue = [here]
    while queue:
        node = queue.pop(0)
        for nxt in known.get(node, []):
            if nxt in dist:
                continue
            dist[nxt] = dist[node] + 1
            first[nxt] = nxt if node == here else first[node]
            queue.append(nxt)
    if target in first:
        return first[target]
    warp = legal(obs, "warp") or {}
    choices = [int(x) for x in (((warp.get("params") or {}).get("target") or {}).get("choices") or [])]
    return choices[0] if choices else None


async def travel(seat, body: dict[str, Any], target: int, log: list[dict[str, Any]]) -> dict[str, Any]:
    """Move with plot_course when the form allows it, else one known hop."""
    from tw2k.agents.cockpit_seat import SeatBrain

    for _ in range(8):
        obs = body.get("observation") or {}
        if body.get("game_over"):
            return body
        if obs.get("fighter_challenge") or obs.get("ferrengi_encounter"):
            kind, args, why = SeatBrain(1)._answer(obs)
            log.append({"kind": kind, "args": args, "why": why})
            outcome, body = await post_turn(seat, body, kind, args)
            log[-1]["outcome"] = outcome
            if outcome != "ok":
                return body
            continue
        here = int((obs.get("sector") or {}).get("id") or 0)
        if here == target:
            return body
        lift = legal(obs, "liftoff") or {}
        if lift.get("legal"):
            log.append({"kind": "liftoff", "args": {}})
            outcome, body = await post_turn(seat, body, "liftoff", {})
            log[-1]["outcome"] = outcome
            continue
        plot = legal(obs, "plot_course") or {}
        execute = (plot.get("params") or {}).get("execute") or {}
        if plot.get("legal") and execute.get("legal", True):
            log.append({"kind": "plot_course", "args": {"target": target, "execute": True}})
            outcome, body = await post_turn(seat, body, "plot_course", {"target": target, "execute": True})
            log[-1]["outcome"] = outcome
            log[-1]["error"] = (body.get("last_result") or {}).get("error")
            arrived = int(((body.get("observation") or {}).get("sector") or {}).get("id") or 0)
            if outcome == "ok" and (body.get("last_result") or {}).get("ok") is not False and arrived == target:
                return body
            if (log[-1].get("error") or "") and "longer than" in str(log[-1]["error"]):
                break
            if arrived == target:
                return body
            continue
        hop = _hop_toward(obs, target)
        if hop is None:
            return body
        log.append({"kind": "warp", "args": {"target": hop}})
        outcome, body = await post_turn(seat, body, "warp", {"target": hop})
        log[-1]["outcome"] = outcome
    return body


async def challenge_exchange() -> dict[str, Any]:
    """P1 deploys fighters. P2 deploys, then enters and answers the challenge."""
    from tw2k.engine import GameConfig
    from tw2k.server.runner import AgentSpec, MatchSpec

    cfg = GameConfig(
        seed=250925, universe_size=80, max_days=2, turns_per_day=400,
        enable_ferrengi=False, enable_planets=True, action_delay_s=0.0,
        turn_regen_day_seconds=60,
    )
    spec = MatchSpec(
        config=cfg,
        agents=[
            AgentSpec(player_id="P1", name="Bot", kind="external", external_token=TOK_A),
            AgentSpec(player_id="P2", name="Cockpit", kind="external", external_token=TOK_B),
        ],
        action_delay_s=0.0, external_timeout_s=120.0,
    )
    log: list[dict[str, Any]] = []

    async def run(http, _runner) -> dict[str, Any]:
        from tw2k.agents.cockpit_seat import SeatBrain

        bot = seat_client(http, "P1", TOK_A)
        seat = seat_client(http, "P2", TOK_B)
        state = {"bot_deployed": False, "bot_left": False, "seat_deployed": False,
                 "bot_sector": 0, "seat_qty": 0, "bot_qty": 0, "answered": None}
        deadline = time.monotonic() + 90
        last_seat: dict[str, Any] = {}
        while time.monotonic() < deadline and state["answered"] is None:
            progressed = False
            for who, label in ((bot, "bot"), (seat, "seat")):
                body = await who.read("observation", {"wait_s": 0, "peek": 1})
                obs = body.get("observation") or {}
                if label == "seat":
                    last_seat = body
                if not body.get("awaiting_input") or body.get("peek") or not obs:
                    continue
                progressed = True
                kind, args = "wait", {}
                if obs.get("fighter_challenge") or obs.get("ferrengi_encounter"):
                    if label == "seat":
                        kind, args, why = SeatBrain(1)._answer(obs)
                        state["answered"] = {"kind": kind, "why": why, "challenge": obs.get("fighter_challenge")}
                    else:
                        kind, args = "retreat", {}
                elif (legal(obs, "liftoff") or {}).get("legal"):
                    kind = "liftoff"
                elif label == "bot" and not state["bot_deployed"]:
                    state["bot_sector"] = int((obs.get("sector") or {}).get("id") or 0)
                    dep = legal(obs, "deploy_fighters") or {}
                    qty = min(8, int(((dep.get("params") or {}).get("qty") or {}).get("max") or 0))
                    if dep.get("legal") and qty > 0:
                        kind, args = "deploy_fighters", {"qty": qty, "mode": "defensive"}
                        state["bot_qty"] = qty
                        state["bot_deployed"] = True
                elif label == "bot" and not state["bot_left"]:
                    hop = _hop_toward(obs, 1)
                    if hop is not None:
                        kind, args = "warp", {"target": hop}
                        state["bot_left"] = True
                elif label == "seat" and not state["seat_deployed"]:
                    dep = legal(obs, "deploy_fighters") or {}
                    qty = min(10, int(((dep.get("params") or {}).get("qty") or {}).get("max") or 0))
                    if dep.get("legal") and qty > 0:
                        kind, args = "deploy_fighters", {"qty": qty, "mode": "defensive"}
                        state["seat_qty"] = qty
                        state["seat_deployed"] = True
                elif label == "seat" and state["bot_left"]:
                    here = int((obs.get("sector") or {}).get("id") or 0)
                    target = int(state["bot_sector"])
                    if here != target:
                        plot = legal(obs, "plot_course") or {}
                        execute = (plot.get("params") or {}).get("execute") or {}
                        if plot.get("legal") and execute.get("legal", True):
                            kind, args = "plot_course", {"target": target, "execute": True}
                        else:
                            hop = _hop_toward(obs, target)
                            if hop is not None:
                                kind, args = "warp", {"target": hop}
                log.append({"seat": label, "kind": kind, "args": args})
                outcome = await who._post_turn(int(body["turn_seq"]), kind, args)
                log[-1]["outcome"] = outcome
                if state["answered"] is not None and label == "seat":
                    nxt = await who.read("observation", {"wait_s": 2, "peek": 1})
                    last = nxt.get("last_result") or {}
                    state["answered"]["ok"] = last.get("ok")
                    state["answered"]["error"] = last.get("error")
                    log[-1]["ok"] = last.get("ok")
                    log[-1]["error"] = last.get("error")
                    last_seat = nxt
            if not progressed:
                await asyncio.sleep(0.05)
        return {
            "bot_sector": state["bot_sector"],
            "seat_deploy_qty": state["seat_qty"],
            "bot_deploy_qty": state["bot_qty"],
            "answered": state["answered"],
            "sector_after": int(((last_seat.get("observation") or {}).get("sector") or {}).get("id") or 0),
            "log": log,
        }

    return await with_match(spec, run)


async def terra_citadel() -> dict[str, Any]:
    """Ferry Terra colonists home, stock the L1 goods, and post build_citadel.

    Credits are a test override so the ore can be bought. The colonist count
    the build form asks for is whatever that form prints.
    """
    from tw2k.engine import GameConfig
    from tw2k.server.runner import AgentSpec, MatchSpec

    cfg = GameConfig(
        seed=250925, universe_size=80, max_days=3, turns_per_day=800,
        starting_credits_override=100_000,
        enable_ferrengi=False, enable_planets=True, action_delay_s=0.0,
        turn_regen_day_seconds=120,
    )
    spec = MatchSpec(
        config=cfg,
        agents=[AgentSpec(player_id="P2", name="Cockpit", kind="external", external_token=TOK_B)],
        action_delay_s=0.0, external_timeout_s=180.0,
    )
    log: list[dict[str, Any]] = []

    async def run(http, _runner) -> dict[str, Any]:
        seat = seat_client(http, "P2", TOK_B)
        body = await await_turn(seat)
        obs = body.get("observation") or {}
        planet = None
        for row in (obs.get("sector") or {}).get("planets") or []:
            if row.get("citadel_next_build"):
                planet = row
                break
        if planet is None:
            raise RuntimeError("home world did not show a citadel build on the first read")
        need = planet["citadel_next_build"]
        home_id = int(planet["id"])
        home_sector = int((obs.get("sector") or {}).get("id") or 0)
        before_col = int(need.get("colonists_have") or 0)
        goods = {name: int(need.get(name) or 0) for name in COMMODITIES}
        log.append({"read": "citadel_next_build", "need": need, "home_sector": home_sector, "planet_id": home_id})

        async def go(target: int) -> None:
            nonlocal body
            body = await travel(seat, body, target, log)

        async def do(kind: str, args: dict[str, Any]) -> dict[str, Any]:
            nonlocal body
            log.append({"kind": kind, "args": args})
            outcome, body = await post_turn(seat, body, kind, args)
            last = body.get("last_result") or {}
            log[-1]["outcome"] = outcome
            log[-1]["ok"] = last.get("ok")
            log[-1]["error"] = last.get("error")
            return last

        await go(1)
        taken = 0
        for _ in range(3):
            obs = body.get("observation") or {}
            if int((obs.get("sector") or {}).get("id") or 0) != 1:
                await go(1)
                obs = body.get("observation") or {}
            terra = legal(obs, "terra_colonists") or {}
            choices = ((terra.get("params") or {}).get("mode") or {}).get("choices") or []
            qty = int((((terra.get("params") or {}).get("qty") or {}).get("max_by") or {}).get("take") or 0)
            if not terra.get("legal") or "take" not in choices or qty <= 0:
                break
            last = await do("terra_colonists", {"mode": "take", "qty": qty})
            if last.get("ok") is False:
                break
            taken += qty
            await go(home_sector)
            obs = body.get("observation") or {}
            if obs.get("planet_landed") is None and (legal(obs, "land_planet") or {}).get("legal"):
                await do("land_planet", {"planet_id": home_id})
                obs = body.get("observation") or {}
            cargo = int((((body.get("observation") or {}).get("ship") or {}).get("cargo") or {}).get("colonists") or 0)
            if cargo > 0 and (legal(body.get("observation") or {}, "dump_planet_cargo") or {}).get("legal"):
                await do("dump_planet_cargo", {"planet_id": home_id, "commodity": "colonists", "qty": cargo, "pool": "colonists"})
            lift = legal(body.get("observation") or {}, "liftoff") or {}
            if lift.get("legal"):
                await do("liftoff", {})

        have_goods = _stockpile(body.get("observation") or {}, home_id)
        # One buy is a few posts, and the live route answers 429 past 30 posts in 10s.
        # A reread is not a dump: the previous verdict stays on the observation.
        seen_sectors: set[int] = set()
        for _ in range(240):
            obs = body.get("observation") or {}
            if body.get("game_over"):
                break
            have_goods = _stockpile(obs, home_id)
            cargo = (obs.get("ship") or {}).get("cargo") or {}
            short = [name for name in COMMODITIES if have_goods[name] < goods[name]]
            carrying = [name for name in short if int(cargo.get(name) or 0) > 0]
            here = int((obs.get("sector") or {}).get("id") or 0)
            if carrying:
                if here != home_sector:
                    await go(home_sector)
                    continue
                # Land stays listed while the ship is already on the planet, and posting
                # it again does not unload cargo. Dump once planet_landed is set.
                if obs.get("planet_landed") is None and (legal(obs, "land_planet") or {}).get("legal"):
                    await do("land_planet", {"planet_id": home_id})
                    continue
                landed = obs.get("planet_landed")
                if landed is not None:
                    name = carrying[0]
                    qty = min(int(cargo.get(name) or 0), goods[name] - have_goods[name])
                    if qty <= 0:
                        continue
                    last = await do("dump_planet_cargo", {"planet_id": home_id, "commodity": name, "qty": qty})
                    if log[-1].get("outcome") == "ok" and last.get("ok") is not False:
                        have_goods = _stockpile(body.get("observation") or {}, home_id)
                    still_aboard = (body.get("observation") or {}).get("ship") or {}
                    aboard = (still_aboard.get("cargo") or {})
                    more = any(
                        int(aboard.get(n) or 0) > 0 and have_goods[n] < goods[n] for n in COMMODITIES
                    )
                    lift = legal((body.get("observation") or {}), "liftoff") or {}
                    if not more and lift.get("legal") and any(have_goods[n] < goods[n] for n in COMMODITIES):
                        await do("liftoff", {})
                    continue
            if not short:
                break
            dock = int((obs.get("sector") or {}).get("stardock_sector") or 0)
            trade = legal(obs, "trade") or {}
            if trade.get("legal"):
                params = trade.get("params") or {}
                buys = list((params.get("commodity") or {}).get("buy_choices") or [])
                stock = ((obs.get("sector") or {}).get("port") or {}).get("stock") or {}
                bought = False
                for name in short:
                    if name not in buys:
                        continue
                    listed = int((stock.get(name) or {}).get("price") or 0)
                    if listed <= 0:
                        continue
                    offer = _offer(listed, "buy")
                    most = int(((params.get("qty") or {}).get("max_by") or {}).get(name, {}).get("buy") or 0)
                    credits = int(obs.get("credits") or 0)
                    qty = min(most, goods[name] - have_goods[name] - int(cargo.get(name) or 0), credits // max(1, offer))
                    if qty <= 0:
                        continue
                    await do("trade", {"side": "buy", "commodity": name, "qty": qty, "unit_price": offer})
                    bought = True
                    break
                if bought:
                    continue
            sellers = []
            for name in short:
                sellers = _sellers(obs, name)
                if sellers:
                    break
            if sellers:
                await go(sellers[0])
                continue
            hop = _hop_toward(obs, home_sector if here == 1 else 1)
            fresh = [
                int(row.get("id") or 0)
                for row in (obs.get("adjacent") or [])
                if row.get("port") and int(row.get("id") or 0) not in (0, dock)
            ]
            warp = legal(obs, "warp") or {}
            choices = [
                int(x) for x in (((warp.get("params") or {}).get("target") or {}).get("choices") or [])
                if int(x) != dock
            ]
            seen_sectors.add(here)
            # Neighbors of Terra are not shops once StarDock has moved. Walk
            # an unvisited exit instead of bouncing back to sector 1.
            unseen_ports = [sid for sid in fresh if sid not in seen_sectors]
            unseen = [sid for sid in choices if sid not in seen_sectors]
            if unseen_ports:
                target = unseen_ports[0]
            elif fresh and not unseen:
                target = fresh[0]
            elif unseen:
                target = unseen[0]
            else:
                target = hop if hop not in (None, dock) else (choices[0] if choices else None)
            if target is None:
                break
            await go(target)
        if int(((body.get("observation") or {}).get("sector") or {}).get("id") or 0) != home_sector:
            await go(home_sector)
        if (legal(body.get("observation") or {}, "land_planet") or {}).get("legal"):
            await do("land_planet", {"planet_id": home_id})
        build = await do("build_citadel", {"planet_id": home_id})
        final = body.get("observation") or {}
        after = None
        for row in (final.get("sector") or {}).get("planets") or []:
            if int(row.get("id") or 0) == home_id:
                after = row
                break
        return {
            "home_sector": home_sector,
            "planet_id": home_id,
            "colonists_before": before_col,
            "goods_needed": goods,
            "goods_dumped": have_goods,
            "terra_holds_taken": taken,
            "build": {"ok": build.get("ok"), "error": build.get("error")},
            "planet_after": after,
            "log": log,
        }

    return await with_match(spec, run)


def _spec_solo(days: int, day_s: float, token: str):
    from tw2k.engine import GameConfig
    from tw2k.server.runner import AgentSpec, MatchSpec

    return MatchSpec(
        config=GameConfig(
            seed=250925, universe_size=200, max_days=days, turns_per_day=100,
            enable_ferrengi=True, enable_planets=True, action_delay_s=0.0,
            all_start_stardock=True, turn_regen_day_seconds=day_s,
        ),
        agents=[
            AgentSpec(player_id="P1", name="HBot", kind="heuristic"),
            AgentSpec(player_id="P2", name="CockpitSeat", kind="external", external_token=token),
        ],
        action_delay_s=0.0, external_timeout_s=180.0,
    )


def _spec_versus(seed: int, token: str):
    from tw2k.engine import GameConfig
    from tw2k.server.runner import AgentSpec, MatchSpec

    return MatchSpec(
        config=GameConfig(
            seed=seed, universe_size=200, max_days=10, turns_per_day=1000,
            enable_ferrengi=True, enable_planets=True, action_delay_s=0.0,
            turn_regen_day_seconds=15,
        ),
        agents=[
            AgentSpec(player_id="P1", name="N3", kind="heuristic"),
            AgentSpec(player_id="P2", name="N2", kind="heuristic"),
            AgentSpec(player_id="P3", name="N1", kind="heuristic"),
            AgentSpec(player_id="P4", name="H", kind="heuristic"),
            AgentSpec(player_id="P5", name="Cockpit", kind="external", external_token=token),
        ],
        action_delay_s=0.0, external_timeout_s=180.0,
    )


async def solo_ten() -> dict[str, Any]:
    from tw2k.agents.cockpit_seat import run_http

    port = _free_port(9181)
    spec = _spec_solo(10, 12, TOK_B)
    with PortHost(spec, port) as host:
        async with httpx.AsyncClient(base_url=host.base, timeout=60.0) as http:
            report = await run_http(http, "P2", TOK_B, 10, idle_s=90)
    report["port"] = port
    return report


async def versus_ten(seed: int) -> dict[str, Any]:
    from tw2k.agents.cockpit_seat import run_http
    from tw2k.engine.victory import full_net_worth

    install_code_bots({"P1": "N3", "P2": "N2", "P3": "N1", "P4": "H"})
    port = _free_port(9182 if seed == 250925 else 9183)
    spec = _spec_versus(seed, TOK_B)
    with PortHost(spec, port) as host:
        async with httpx.AsyncClient(base_url=host.base, timeout=60.0) as http:
            report = await run_http(http, "P5", TOK_B, 10, idle_s=90)
        universe = host.runner.state.universe
        table = []
        if universe is not None:
            for player in universe.players.values():
                table.append({
                    "id": player.id,
                    "name": player.name,
                    "experience": int(player.experience),
                    "net_worth": int(full_net_worth(universe, player)),
                    "credits": int(player.credits),
                    "alive": bool(player.alive),
                    "deaths": int(player.deaths),
                    "ship": player.ship.ship_class.value,
                })
            table.sort(key=lambda row: (-row["experience"], row["name"]))
            for index, row in enumerate(table, 1):
                row["experience_place"] = index
            by_worth = sorted(table, key=lambda row: (-row["net_worth"], row["name"]))
            for index, row in enumerate(by_worth, 1):
                row["net_worth_place"] = index
        report["final_table"] = table
    report["port"] = port
    return report


def _slim(report: dict[str, Any]) -> dict[str, Any]:
    kept = {key: report.get(key) for key in (
        "seat", "days_asked", "posts", "kinds", "refused", "days", "final", "gaps",
        "died", "cockpit_fields", "final_table",
    )}
    kept["refused"] = (report.get("refused") or [])[:40]
    return kept


def write_note95_gaps(report: dict[str, Any]) -> None:
    """Append the V311 gap rows. The NOTE 56 table above them stays."""
    path = OUT / "gaps.md"
    previous = path.read_text(encoding="utf-8") if path.exists() else ""
    marker = "## NOTE 95"
    if marker in previous:
        previous = previous.split(marker)[0].rstrip() + "\n"
    lines = [
        "",
        "## NOTE 95 (2026-10-19): the seat on V311_PROFILE",
        "",
        "The table above is the NOTE 56 run with the cockpit block on and the profile off.",
        "These rows are the cockpit-only seat on a test server with V311_PROFILE=v311",
        "(seed 250925, 10 days, port 9181). The seat still used only its four routes.",
        "A row is a decision the routes do not carry, so the seat guessed.",
        "",
        "| Decision | Turns | What the seat needed | Where the cockpit has it | Original TW2002 screen |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for row in report.get("gaps") or []:
        lines.append(
            f"| {row['decision']} | {row['count']} | {row['needed']} | {row['cockpit']} | {row['original']} |"
        )
    lines += [
        "",
        "Breaks the seat client now handles, still from those four routes: it lifts off the",
        "home world before warp or trade, waits out HTTP 429 on the live action route and",
        "reads the cockpit again instead of replaying a stale post, drops a plotted course",
        "the route refused, and does not warp back into a sector it retreated from or one",
        "an event already named for mines or NavHaz.",
        "",
        "The scripted Terra run (terra-citadel.json) moves the Terra colonist pool onto",
        "the home world. The class M level-1 form, read from citadel_next_build on the",
        "same observation, asks for 1,000,000 colonists. The pool plus the home start",
        "does not reach that, so the build does not start. That figure is on the route;",
        "it is a stake the seat cannot meet, not a missing field and not an engine change.",
        "",
    ]
    path.write_text(previous.rstrip() + "\n" + "\n".join(lines), encoding="utf-8")


def _lost_time(report: dict[str, Any]) -> str:
    kinds = report.get("kinds") or {}
    gaps = {row["id"]: row["count"] for row in report.get("gaps") or []}
    days = report.get("days") or []
    short = sum(1 for row in days if int(row.get("turns_used") or 0) < 100)
    return (
        f"waits {kinds.get('wait', 0)}, retreats {kinds.get('retreat', 0)}, "
        f"liftoffs {kinds.get('liftoff', 0)}, trades {kinds.get('trade', 0)}, "
        f"hazard guesses {gaps.get('hazard_unseen', 0)}, "
        f"days with fewer than 100 turns used {short} of {len(days)} "
        f"(the 15s test clock rolls the day while turns remain; a live day is 86400s)"
    )


def write_versus(reports: dict[int, dict[str, Any]]) -> None:
    lines = [
        "# Cockpit seat against the code bots",
        "",
        "Ten days, V311_PROFILE=v311, the standard lineup N3, N2, N1, H in process",
        "and the cockpit seat on its own four routes (P5). The day clock is 15 seconds",
        "so the run finishes here; a real day is 86,400. Turns per day follow the v3.11",
        "opening (250) because the spec asks for the engine default of 1,000.",
        "",
    ]
    for seed, report in reports.items():
        lines.append(f"## Seed {seed}")
        lines.append("")
        lines.append(f"Seat posts {report.get('posts')}, refused {len(report.get('refused') or [])}.")
        lines.append(f"Where the seat lost time: {_lost_time(report)}.")
        lines.append("")
        lines.append("| Day | Experience | Exp place | Net worth | Worth place | Credits | Turns used | Trades |")
        lines.append("| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for row in report.get("days") or []:
            lines.append(
                f"| {row.get('day')} | {row.get('experience_end')} | {row.get('experience_place')} | "
                f"{row.get('net_worth_end')} | {row.get('net_worth_place')} | {row.get('credits_end')} | "
                f"{row.get('turns_used')} | {row.get('trades')} |"
            )
        lines.append("")
        lines.append("Final table (experience order):")
        lines.append("")
        lines.append("| Place | Name | Experience | Worth place | Net worth | Ship | Deaths |")
        lines.append("| ---: | --- | ---: | ---: | ---: | --- | ---: |")
        for row in report.get("final_table") or []:
            lines.append(
                f"| {row.get('experience_place')} | {row.get('name')} | {row.get('experience')} | "
                f"{row.get('net_worth_place')} | {row.get('net_worth')} | {row.get('ship')} | {row.get('deaths')} |"
            )
        lines.append("")
    (OUT / "vs-bots.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str]) -> int:
    enable_v311()
    OUT.mkdir(parents=True, exist_ok=True)
    cmd = argv[1] if len(argv) > 1 else "solo"
    if cmd == "solo":
        report = asyncio.run(solo_ten())
        (OUT / "v311-run10.json").write_text(json.dumps(_slim(report), indent=2), encoding="utf-8")
        write_note95_gaps(report)
        print("solo", report.get("posts"), "refused", len(report.get("refused") or []), "died", report.get("died"))
        return 0
    if cmd == "versus":
        reports = {}
        for seed in (250925, 4242):
            report = asyncio.run(versus_ten(seed))
            reports[seed] = report
            (OUT / f"vs-bots-{seed}.json").write_text(json.dumps(_slim(report), indent=2), encoding="utf-8")
            print("versus", seed, "posts", report.get("posts"), "refused", len(report.get("refused") or []))
        write_versus(reports)
        return 0
    if cmd == "scenarios":
        challenge = asyncio.run(challenge_exchange())
        (OUT / "challenge.json").write_text(json.dumps(challenge, indent=2, default=str), encoding="utf-8")
        terra = asyncio.run(terra_citadel())
        (OUT / "terra-citadel.json").write_text(json.dumps(terra, indent=2, default=str), encoding="utf-8")
        print("challenge", challenge.get("answered"))
        print("terra", terra.get("build"), "taken", terra.get("terra_holds_taken"), "goods", terra.get("goods_dumped"))
        return 0
    raise SystemExit(f"unknown {cmd}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
