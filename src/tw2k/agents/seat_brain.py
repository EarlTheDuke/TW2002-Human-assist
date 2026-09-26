"""Goal-driven seat brain (seat-bot S3).

docs/plans/2026-09-24-seat-bot-competitive.md. Replaces the hand-patched
Path-B ladder in scripts/commander_p4_brain.py with one pure decision
function that reads ONLY the seat's own fogged observation (the object the
harness mailbox hands over): legal_actions + envelopes, ship/cargo, credits,
known_warps, owned_planets (S1 colonists/origin), sector, scratchpad.

    brain = SeatBrain()
    action = brain.decide(observation)   # dict: {kind, args, thought, goal_*, scratchpad_update}

Goal ladder (first rung that yields a legal action wins):
  1. Landed: assign colonists aboard -> build citadel -> liftoff (never ferry
     colonists onto a claimed neutral; only genesis worlds are work sites).
  2. Genesis aboard: deploy when `deploy_genesis` is legal, else carry it
     away from StarDock / FedSpace guided by `legal_actions.reason`.
  3. At home with a reason (colonists aboard, citadel buildable): land.
  4. At StarDock: CargoTran upgrade -> genesis (none yet / below target) ->
     fill holds with colonists for the ferry.
  5. Colonists aboard: plot home.  Need StarDock: plot StarDock.
  6. Explore until StarDock is known; otherwise make money trading.

Loops are judged by `tw2k.agents.stall.StallDetector` (no progress toward
the declared intent), never by target alternation: StarDock <-> home ferry
legs and same-target replots are fine. When the detector says stalled the
brain spends a few turns exploring, then resumes the ladder.

Memory (home planet, deploy sector, visit counts) is written back through
`scratchpad_update` so a restarted brain resumes where it left off.

Rule numbers used (citadel tier costs) are the public rulebook the system
prompt also states; everything situational comes from the observation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ..engine.constants import CITADEL_TIER_COST, GENESIS_TORPEDO_COST, SHIP_SPECS
from .pathb_client import TurnContext, legal_heuristic_policy
from .stall import Intent, StallDetector, known_distance

STARDOCK = 1
MEMORY_TAG = "SEATBRAIN "
STALL_BREAK_TURNS = 3
# S6: self-failure events a seat can see about its own actions.
FAIL_KINDS = ("agent_error", "trade_failed", "warp_blocked")
BAN_DECISIONS = 12          # a failed exact action is not retried for this many decisions
KIND_BAN_AFTER = 2          # same verb failing this many times in a day -> verb shelved for the day
PRESSURE_NW_RATIO = 1.15    # a rival this far ahead on public net worth = we are trailing
PRESSURE_NW_GAP = 10_000
ORPHAN_MAX_HOPS = 8
CLAIM_WORLD_MIN_COLONISTS = 1_000
# N1: a poor seat's one worthwhile StarDock errand before a CargoTran is affordable is a
# modest hold expansion (buy_ship later resets holds, so keep it modest).
POOR_HOLDS_TARGET = 60
POOR_HOLDS_MIN_BUY = 10
POOR_TRADE_CAPITAL = 6_000


@dataclass
class SeatMemory:
    home_planet: int | None = None
    home_sector: int | None = None
    deploy_sector: int | None = None
    visits: dict[int, int] = field(default_factory=dict)
    stall_breaks: int = 0
    break_left: int = 0
    # "sector:commodity" -> day a remembered buyer refused us (stale / full); skipped that day.
    bad_sells: dict[str, int] = field(default_factory=dict)
    # S6 failure replanning (all derived from the seat's own events).
    decisions: int = 0
    last_action_sig: str | None = None
    last_event_seq: int = 0
    banned: dict[str, int] = field(default_factory=dict)        # action signature -> banned until decision N
    kind_fails: dict[str, list[int]] = field(default_factory=dict)  # verb -> [day, count]
    banned_kinds: dict[str, int] = field(default_factory=dict)  # verb -> day shelved
    ban_day: int = 0
    replans: int = 0

    def dump(self) -> str:
        return MEMORY_TAG + json.dumps({
            "home_planet": self.home_planet, "home_sector": self.home_sector,
            "deploy_sector": self.deploy_sector, "stall_breaks": self.stall_breaks,
            "last_event_seq": self.last_event_seq, "last_action_sig": self.last_action_sig,
            # keep the scratchpad small: only the 40 most visited sectors
            "visits": dict(sorted(self.visits.items(), key=lambda kv: -kv[1])[:40]),
        }, separators=(",", ":"))

    @classmethod
    def load(cls, scratchpad: str | None) -> SeatMemory:
        mem = cls()
        if not scratchpad or MEMORY_TAG not in scratchpad:
            return mem
        try:
            data = json.loads(scratchpad.split(MEMORY_TAG, 1)[1].strip().splitlines()[0])
        except (ValueError, IndexError):
            return mem
        mem.home_planet = data.get("home_planet")
        mem.home_sector = data.get("home_sector")
        mem.deploy_sector = data.get("deploy_sector")
        mem.stall_breaks = int(data.get("stall_breaks") or 0)
        mem.visits = {int(k): int(v) for k, v in (data.get("visits") or {}).items()}
        mem.last_event_seq = int(data.get("last_event_seq") or 0)
        mem.last_action_sig = data.get("last_action_sig")
        return mem


class View:
    """Read-only helpers over one observation dict."""

    def __init__(self, obs: dict[str, Any]) -> None:
        self.obs = obs
        self.legal = {la.get("kind"): la for la in (obs.get("legal_actions") or [])}
        sector = obs.get("sector") or {}
        self.here = sector.get("id")
        self.sector = sector
        ship = obs.get("ship") or {}
        self.ship = ship
        self.cargo = ship.get("cargo") or {}
        self.credits = int(obs.get("credits") or 0)
        self.colonists_aboard = int(self.cargo.get("colonists") or 0)
        self.genesis_aboard = int(ship.get("genesis") or 0)
        self.cargo_free = int(ship.get("cargo_free") or 0)
        self.ship_class = ship.get("class")
        self.landed = obs.get("planet_landed")
        self.owned = [p for p in (obs.get("owned_planets") or []) if isinstance(p, dict)]
        self.known_warps = {int(k): tuple(int(x) for x in (v or ())) for k, v in (obs.get("known_warps") or {}).items()}
        ks = obs.get("known_sectors")
        self.known_ids = ({int(s["id"]) for s in ks if isinstance(s, dict) and "id" in s}
                          if isinstance(ks, list) else set(self.known_warps))
        self.self_id = obs.get("self_id")
        self.day = int(obs.get("day") or 0)
        self.net_worth = int(obs.get("net_worth") or self.credits)
        self.rivals = [r for r in (obs.get("rivals") or []) if isinstance(r, dict)]
        self.events = [e for e in (obs.get("recent_events") or []) if isinstance(e, dict)]
        self.failures = [f for f in (obs.get("recent_failures") or []) if isinstance(f, dict)]
        # Only planets the ENGINE lists as true former-player orphans; never inferred.
        self.orphans = {int(p["id"]): p for p in (obs.get("orphaned_planets") or [])
                        if isinstance(p, dict) and p.get("id") is not None}

    def ok(self, kind: str) -> bool:
        return bool((self.legal.get(kind) or {}).get("legal"))

    def reason(self, kind: str) -> str:
        return str((self.legal.get(kind) or {}).get("reason") or "")

    def params(self, kind: str) -> dict[str, Any]:
        return (self.legal.get(kind) or {}).get("params") or {}

    def choices(self, kind: str, name: str) -> list[Any]:
        p = self.params(kind).get(name)
        return list(p.get("choices") or []) if isinstance(p, dict) else []

    def max_by(self, kind: str, name: str, key: str) -> int:
        p = self.params(kind).get(name)
        if not isinstance(p, dict):
            return 0
        return int((p.get("max_by") or {}).get(key) or 0)

    @property
    def stardock_known(self) -> bool:
        return self.here == STARDOCK or STARDOCK in self.known_ids

    def planet(self, pid: int | None) -> dict[str, Any] | None:
        return next((p for p in self.owned if p.get("id") == pid), None)

    def genesis_planets(self) -> list[dict[str, Any]]:
        return [p for p in self.owned if p.get("origin") == "genesis"]

    def worlds(self) -> list[dict[str, Any]]:
        """Planets worth developing: own genesis worlds, plus claimed worlds that already
        carry a citadel or a real colony (e.g. an inherited orphan). Empty neutral claims
        stay excluded - that was the Kimi3 planet-20 trap."""
        return [p for p in self.owned if p.get("origin") == "genesis"
                or int(p.get("citadel_level") or 0) >= 1
                or _colonists_total(p) >= CLAIM_WORLD_MIN_COLONISTS]


def _colonists_total(p: dict[str, Any]) -> int:
    t = p.get("colonists_total")
    if isinstance(t, int):
        return t
    c = p.get("colonists")
    return sum(int(v or 0) for v in c.values()) if isinstance(c, dict) else int(c or 0)


def next_tier(planet: dict[str, Any], *, lookahead: bool = False) -> tuple[int, int] | None:
    """(credits, colonists) for the next citadel build.

    lookahead=False: the build that is possible NOW (None while one is under
    construction). lookahead=True: the next build to prepare for, i.e. the tier
    after the one under construction.
    """
    lvl = int(planet.get("citadel_level") or 0)
    tgt = int(planet.get("citadel_target") or 0)
    if tgt > lvl and not lookahead:
        return None
    base = max(lvl, tgt)
    if base >= len(CITADEL_TIER_COST):
        return None
    cred, col, _days = CITADEL_TIER_COST[base]
    return cred, col


def _signature(action: dict[str, Any], v: View | None = None) -> str:
    """Identity of an action for failure bookkeeping: verb + the argument that decides it."""
    kind = str(action.get("kind"))
    a = action.get("args") or {}
    if kind in ("warp", "plot_course", "probe", "attack", "photon_missile", "hail"):
        key = a.get("target")
    elif kind in ("land_planet", "build_citadel", "assign_colonists", "claim_planet",
                  "load_planet_cargo", "dump_planet_cargo"):
        key = a.get("planet_id")
    elif kind == "trade":
        return f"trade:{a.get('commodity')}:{a.get('side')}"
    elif kind == "buy_equip":
        key = a.get("item")
    elif kind == "buy_ship":
        key = a.get("ship_class")
    elif kind == "deploy_genesis" and v is not None:
        key = v.here
    else:
        key = ""
    return f"{kind}:{key}"


class SeatBrain:
    def __init__(self, *, target_planets: int = 2, cash_buffer: int = 2_000, working_capital: int = 8_000,
                 stall_window: int = 8) -> None:
        self.target_planets = target_planets
        self.cash_buffer = cash_buffer
        # Never spend below this on colonists / extra genesis: it keeps a trade
        # loop funded so the seat can always earn its way back (Kimi3 lesson).
        self.working_capital = working_capital
        self.detector = StallDetector(window=stall_window)
        self.mem: SeatMemory | None = None
        self._intent = Intent()
        self.last_report = None
        self.pressure: dict[str, Any] | None = None

    # ------------------------------------------------------------------ entry
    def decide(self, obs: Any) -> dict[str, Any]:
        o = obs if isinstance(obs, dict) else obs.model_dump(mode="json")
        v = View(o)
        if self.mem is None:
            self.mem = SeatMemory.load(o.get("scratchpad"))
        mem = self.mem
        if v.here is not None:
            mem.visits[int(v.here)] = mem.visits.get(int(v.here), 0) + 1
        mem.decisions += 1
        self._ingest_failures(v)
        self.pressure = self._rival_pressure(v)
        self._refresh_home(v)

        report = self.detector.observe(o, self._intent)
        self.last_report = report
        if report.stalled and mem.break_left == 0:
            mem.break_left = STALL_BREAK_TURNS
            mem.stall_breaks += 1
            self.detector.reset()

        action, intent = (None, Intent())
        if mem.break_left > 0:
            mem.break_left -= 1
            action, intent = self._explore(v, f"stall break ({report.summary()})")
            if action is not None and self._banned_why(action, v):
                action, intent = None, Intent()
        if action is None:
            action, intent = self._ladder(v)
        self._intent = intent
        mem.last_action_sig = _signature(action, v)
        return self._finish(v, action)

    # ------------------------------------------------------------------ S6: failures / rivals
    def _ingest_failures(self, v: View) -> None:
        """Turn the seat's own failure events into bans so a rejected action is not retried blindly.

        Sources (all in the seat's observation): new `agent_error` / `trade_failed` /
        `warp_blocked` events for this seat since the last decision (attributed to the
        action we sent last), their `facts` (blocked warp target, failed commodity), and
        the engine's aggregated `recent_failures` (count >= 2).
        """
        mem = self.mem
        if v.day != mem.ban_day:  # a new day brings new turns/credits: give every action a fresh try
            mem.banned.clear()
            mem.ban_day = v.day
        seqs = [int(e.get("seq") or 0) for e in v.events]
        new = [e for e in v.events if int(e.get("seq") or 0) > mem.last_event_seq
               and e.get("kind") in FAIL_KINDS and (v.self_id is None or e.get("actor_id") == v.self_id)]
        if seqs:
            mem.last_event_seq = max(mem.last_event_seq, max(seqs))
        for e in new:
            facts = e.get("facts") or {}
            sigs: set[str] = set()
            if e.get("kind") == "warp_blocked" and facts.get("target") is not None:
                sigs |= {f"warp:{facts['target']}", f"plot_course:{facts['target']}"}
            elif e.get("kind") == "trade_failed" and facts.get("commodity"):
                sigs.add(f"trade:{facts['commodity']}:{facts.get('side')}")
            if mem.last_action_sig:
                sigs.add(mem.last_action_sig)
            for sig in sigs:
                mem.banned[sig] = mem.decisions + BAN_DECISIONS
            verb = (mem.last_action_sig or e.get("kind") or "").split(":")[0]
            day, count = mem.kind_fails.get(verb, [v.day, 0])
            count = count + 1 if day == v.day else 1
            mem.kind_fails[verb] = [v.day, count]
            if count >= KIND_BAN_AFTER and verb not in ("wait", "liftoff"):
                mem.banned_kinds[verb] = v.day
            mem.replans += 1
        for f in v.failures:
            if int(f.get("count") or 0) < 2:
                continue
            label = str(f.get("target_label") or "")
            if f.get("kind") == "warp_blocked":
                tgt = "".join(ch for ch in label if ch.isdigit())
                if tgt:
                    mem.banned.setdefault(f"warp:{tgt}", mem.decisions + BAN_DECISIONS)
                    mem.banned.setdefault(f"plot_course:{tgt}", mem.decisions + BAN_DECISIONS)
            elif f.get("kind") == "agent_error" and label.endswith(" rejected"):
                verb = label[: -len(" rejected")]
                if verb and verb not in ("unknown", "wait", "liftoff"):
                    mem.banned_kinds.setdefault(verb, v.day)

    def _banned_why(self, action: dict[str, Any], v: View) -> str | None:
        mem = self.mem
        kind = action.get("kind")
        if kind in ("wait", "query_limpets"):
            return None
        if mem.banned_kinds.get(kind) == v.day:
            return f"{kind} failed repeatedly today"
        sig = _signature(action, v)
        if mem.banned.get(sig, 0) > mem.decisions:
            return f"{sig} just failed"
        return None

    def _rival_pressure(self, v: View) -> dict[str, Any] | None:
        """Public race signals only: rivals' net worth (public in the observation) and
        empire events we actually witnessed (genesis / citadel / planet claims)."""
        ahead = [r for r in v.rivals if r.get("alive", True)
                 and int(r.get("net_worth") or 0) >= max(v.net_worth * PRESSURE_NW_RATIO, v.net_worth + PRESSURE_NW_GAP)]
        empire_kinds = ("genesis_deployed", "build_citadel", "citadel_complete", "planet_claimed")
        seen = [e for e in v.events if e.get("kind") in empire_kinds
                and e.get("actor_id") not in (None, v.self_id)]
        if not ahead and not (seen and not v.worlds()):
            return None
        leader = max(ahead, key=lambda r: int(r.get("net_worth") or 0)) if ahead else None
        return {
            "leader": leader.get("id") if leader else None,
            "leader_nw": int(leader.get("net_worth") or 0) if leader else None,
            "empire_signals": [e.get("kind") for e in seen][-3:],
        }

    # ------------------------------------------------------------------ ladder
    def _ladder(self, v: View) -> tuple[dict[str, Any], Intent]:
        skipped: list[str] = []
        for rung in (self._landed, self._genesis_aboard, self._land_home, self._land_orphan, self._at_stardock,
                     self._travel, self._earn):
            out = rung(v)
            if out is None or out[0] is None:
                continue
            why = self._banned_why(out[0], v)
            if why:
                skipped.append(why)
                continue
            if skipped:
                out[0]["thought"] += f" [replanned: {'; '.join(skipped)}]"
            return out
        return self._idle(v, skipped)

    def _landed(self, v: View):
        if v.landed is None:
            return None
        # Claim only a planet the engine itself lists as a true orphan, while landed on it.
        # Candidates in priority order; banned ones fall through so liftoff stays the fallback.
        candidates: list[dict[str, Any]] = []
        if int(v.landed) in v.orphans and v.ok("claim_planet"):
            choices = [int(c) for c in v.choices("claim_planet", "planet_id")]
            if not choices or int(v.landed) in choices:
                o = v.orphans[int(v.landed)]
                candidates.append(self._act("claim_planet", {"planet_id": int(v.landed)},
                                            f"claim orphan {o.get('name', v.landed)} (L{o.get('citadel_level', 0)}, "
                                            f"{o.get('fighters', 0)} fighters)"))
        planet = v.planet(v.landed)
        work_site = planet is not None and planet in v.worlds()
        if work_site:
            pid = int(planet["id"])
            if v.colonists_aboard > 0 and v.ok("assign_colonists"):
                qty = v.max_by("assign_colonists", "qty", "ship") or v.colonists_aboard
                pools = planet.get("colonists") if isinstance(planet.get("colonists"), dict) else {}
                pool = "organics" if int(pools.get("organics") or 0) < _colonists_total(planet) // 5 else "fuel_ore"
                candidates.append(self._act("assign_colonists",
                                            {"planet_id": pid, "from": "ship", "to": pool, "qty": int(qty)},
                                            f"unload {qty} colonists to {pool} on planet {pid}"))
            if v.ok("build_citadel") and pid in v.choices("build_citadel", "planet_id"):
                nxt = v.params("build_citadel").get("next") or {}
                candidates.append(self._act("build_citadel", {"planet_id": pid},
                                            f"build citadel L{nxt.get('level', '?')} on planet {pid}"))
            dump = self._unsellable_goods(v)
            if dump and v.ok("dump_planet_cargo") and dump[0] in v.choices("dump_planet_cargo", "commodity"):
                c, qty = dump
                qty = min(qty, v.max_by("dump_planet_cargo", "qty", c) or qty)
                candidates.append(self._act("dump_planet_cargo", {"planet_id": pid, "commodity": c, "qty": int(qty)},
                                            f"stock {qty} unsellable {c} on planet {pid} to free holds"))
        if v.ok("liftoff"):
            why = "nothing more to do here" if work_site else "not a world worth investing in"
            candidates.append(self._act("liftoff", {}, f"liftoff ({why})"))
        skipped = []
        for action in candidates:
            why = self._banned_why(action, v)
            if why:
                skipped.append(why)
                continue
            if skipped:
                action["thought"] += f" [replanned: {'; '.join(skipped)}]"
            return action, Intent("colonize")
        return None

    def _genesis_aboard(self, v: View):
        if v.genesis_aboard <= 0 or v.landed is not None:
            return None
        if v.ok("deploy_genesis"):
            self.mem.deploy_sector = int(v.here)
            return self._act("deploy_genesis", {}, f"deploy genesis in sector {v.here}"), Intent("colonize")
        reason = v.reason("deploy_genesis").lower()
        if "fedspace" in reason or "too close" in reason:
            warp = self._warp_away_from_stardock(v)
            if warp is not None:
                return self._act("warp", {"target": warp}, f"carry genesis deeper ({v.reason('deploy_genesis')})"), Intent("explore")
        return None

    def _land_home(self, v: View):
        if v.landed is not None or not v.ok("land_planet"):
            return None
        choices = [int(c) for c in v.choices("land_planet", "planet_id")]
        for planet in self._work_sites(v):
            pid = int(planet["id"])
            if pid not in choices:
                continue
            tier = next_tier(planet)
            can_build = tier is not None and _colonists_total(planet) >= tier[1] and v.credits >= tier[0]
            dump = self._unsellable_goods(v)
            if v.colonists_aboard > 0 or can_build or dump:
                why = ("unload colonists" if v.colonists_aboard else "citadel is buildable" if can_build
                       else f"stock unsellable {dump[0]}")
                return self._act("land_planet", {"planet_id": pid}, f"land home planet {pid} ({why})"), Intent("colonize")
        return None

    def _land_orphan(self, v: View):
        """Land on an engine-listed orphan in this sector when inheriting it beats the genesis path."""
        if v.landed is not None or not v.ok("land_planet"):
            return None
        choices = [int(c) for c in v.choices("land_planet", "planet_id")]
        contested = {int(c) for c in ((v.params("land_planet").get("planet_id") or {}).get("contested") or [])}
        for pid, o in v.orphans.items():
            if o.get("sector_id") == v.here and pid in choices and pid not in contested and self._wants_orphan(v, o):
                return self._act("land_planet", {"planet_id": pid},
                                 f"land on orphan {pid} to claim it (L{o.get('citadel_level', 0)})"), Intent("colonize")
        return None

    def _wants_orphan(self, v: View, o: dict[str, Any]) -> bool:
        if int(o.get("citadel_level") or 0) >= 1:
            return True  # an inherited citadel is worth more than a fresh genesis seed
        if v.worlds():
            return False
        genesis_slow = v.credits < GENESIS_TORPEDO_COST + CITADEL_TIER_COST[0][0]
        return genesis_slow or self.pressure is not None

    def _at_stardock(self, v: View):
        if v.here != STARDOCK:
            return None
        reserve = self._citadel_reserve(v)
        genesis_price = int((v.params("buy_equip").get("item") or {}).get("unit_price_by", {}).get("genesis")
                            or GENESIS_TORPEDO_COST)
        gplanets = v.genesis_planets()
        # Upgrade hull first: 75 holds make every later ferry trip ~4x cheaper in turns.
        # Deliberately NOT deferred under rival pressure: offline sweeps showed
        # genesis-before-hull cost 5-140k net worth by day 6 on every seed tried.
        if v.ok("buy_ship") and v.ship_class != "cargotran" and "cargotran" in v.choices("buy_ship", "ship_class"):
            net = int((v.params("buy_ship").get("ship_class") or {}).get("net_cost_by", {}).get("cargotran") or 10**12)
            if v.credits - net >= self.cash_buffer and v.ship_class in ("merchant_cruiser", "scout_marauder"):
                return self._act("buy_ship", {"ship_class": "cargotran"}, f"upgrade to CargoTran ({net} cr net)"), Intent("acquire")
        # Genesis: the first as soon as it leaves L1 money; more when rich (sooner when trailing).
        if v.genesis_aboard == 0 and v.ok("buy_equip") and "genesis" in v.choices("buy_equip", "item"):
            price = genesis_price
            first = not gplanets and self._first_genesis_affordable(v, price)
            # A 2nd world keeps the full reserve even when trailing: funding it from working
            # capital starved the first citadel (seed 99: -110k NW by day 6).
            more = bool(gplanets) and len(gplanets) < self.target_planets and v.credits - price >= reserve
            if first or more:
                why = f" - trailing {self.pressure.get('leader')}" if self.pressure and self.pressure.get("leader") else ""
                return self._act("buy_equip", {"item": "genesis", "qty": 1},
                                 f"buy genesis #{len(gplanets) + 1} ({price} cr){why}"), Intent("acquire")
        # Poor seat: expand holds so the trade loop pays more until a CargoTran is affordable.
        holds_qty = self._poor_holds_qty(v)
        if holds_qty and v.ok("buy_equip") and "holds" in v.choices("buy_equip", "item"):
            holds_qty = min(holds_qty, v.max_by("buy_equip", "qty", "holds") or holds_qty)
            if holds_qty >= POOR_HOLDS_MIN_BUY:
                return self._act("buy_equip", {"item": "holds", "qty": int(holds_qty)},
                                 f"buy {holds_qty} holds to grow the trade loop (CargoTran not affordable yet)"), Intent("trade")
        # Ferry load: only what the next citadel tier still needs, never below the reserve.
        need = self._colonists_needed(v)
        if (v.worlds() and need > 0 and self._buildable_elsewhere(v) is None
                and v.ok("buy_equip") and "colonists" in v.choices("buy_equip", "item")):
            unit = int((v.params("buy_equip").get("item") or {}).get("unit_price_by", {}).get("colonists") or 10)
            afford = max(0, (v.credits - reserve) // max(1, unit))
            qty = min(v.max_by("buy_equip", "qty", "colonists"), afford, need)
            if qty > 0 and v.cargo_free > 0:
                return self._act("buy_equip", {"item": "colonists", "qty": int(qty)},
                                 f"load {qty} colonists for the ferry ({need} still needed)"), Intent("colonize", self.mem.home_sector)
        return None

    def _travel(self, v: View):
        if v.landed is not None:
            return None
        home = self.mem.home_sector
        if v.colonists_aboard > 0 and home is not None and v.here != home:
            plot = self._plot(v, home, "ferry colonists home")
            if plot:
                return plot, Intent("colonize", home)
        # Another genesis world can start its next citadel right now: go build it.
        other = self._buildable_elsewhere(v)
        if other is not None and v.colonists_aboard == 0:
            plot = self._plot(v, int(other["sector_id"]), f"citadel buildable on planet {other['id']}")
            if plot:
                return plot, Intent("colonize", int(other["sector_id"]))
        dump = self._unsellable_goods(v)
        if dump and home is not None and v.here != home:
            plot = self._plot(v, home, f"no known buyer for {dump[0]} - stock it at home")
            if plot:
                return plot, Intent("colonize", home)
        # A listed orphan within reach that beats the genesis path: go land on it.
        if v.colonists_aboard == 0 and v.genesis_aboard == 0:
            for _pid, o in sorted(v.orphans.items(), key=lambda kv: -int(kv[1].get("citadel_level") or 0)):
                sid = o.get("sector_id")
                d = known_distance(v.known_warps, v.here, sid)
                if sid != v.here and d is not None and d <= ORPHAN_MAX_HOPS and self._wants_orphan(v, o):
                    plot = self._plot(v, int(sid), f"inherit orphan {o.get('name', _pid)} (L{o.get('citadel_level', 0)})")
                    if plot:
                        return plot, Intent("colonize", int(sid))
        # N1 route, don't search: sector 1 is StarDock by rule and the engine autopilot routes
        # there over the real warp graph whether or not our map has seen it (qwen2-kimi3 P6
        # wandered 120 warps looking for it). If the engine rejects the plot, the S6 failure
        # bans skip this rung and the brain earns / explores instead.
        if v.here != STARDOCK and self._needs_stardock(v):
            plot = self._plot(v, STARDOCK, self._stardock_reason(v))
            if plot:
                kind = "colonize" if v.worlds() else ("trade" if self._poor_holds_qty(v) else "acquire")
                return plot, Intent(kind, STARDOCK)
        return None

    def _earn(self, v: View):
        self._note_refused_sells(v)
        # Trade here if the envelope-driven heuristic finds a profitable buy/sell.
        ctx = TurnContext(seat="", turn_seq=0, observation=v.obs, llm_user_message=None, rules={},
                          status={}, deadline_at=None, server_skew=0.0)
        a = legal_heuristic_policy(ctx)
        if a.get("kind") == "trade":
            return self._act("trade", a.get("args") or {}, f"earn: {a.get('thought', '')}"), Intent("trade")
        # Otherwise head for the best remembered route (sell what we carry, or fetch a cheap load).
        target, why = self._best_route(v)
        if target is not None:
            plot = self._plot(v, target, f"earn: {why}")
            if plot:
                return plot, Intent("trade", target)
        return self._explore(v, "earn: look for ports")

    def _best_route(self, v: View) -> tuple[int | None, str]:
        """Route from REMEMBERED port snapshots (known_ports) over known warps only."""
        sells: dict[str, list[tuple[int, int]]] = {}
        buys: dict[str, list[tuple[int, int]]] = {}
        day = int(v.obs.get("day") or 0)
        for kp in v.obs.get("known_ports") or []:
            sid = kp.get("sector_id")
            for c, st in (kp.get("stock") or {}).items():
                price = st.get("price") if isinstance(st, dict) else None
                if not isinstance(price, int) or sid is None:
                    continue
                if st.get("side") == "sells_to_player" and int(st.get("current") or 0) > 0:
                    sells.setdefault(c, []).append((int(sid), price))
                elif st.get("side") == "buys_from_player":
                    full = st.get("max") is not None and int(st.get("current") or 0) >= int(st["max"])
                    if not full and self.mem.bad_sells.get(f"{sid}:{c}") != day:
                        buys.setdefault(c, []).append((int(sid), price))

        def dist(a, b):
            return known_distance(v.known_warps, a, b)

        # Carrying goods: go to the best-paying known buyer we can route to.
        for c, qty in sorted(v.cargo.items(), key=lambda kv: -int(kv[1] or 0)):
            if c == "colonists" or int(qty or 0) <= 0:
                continue
            options = [(p, s) for s, p in buys.get(c, []) if s != v.here and dist(v.here, s) is not None]
            if options:
                price, sid = max(options)
                return sid, f"sell {qty} {c} at {sid} (~{price})"
        # Empty: fetch the load with the best profit per hop.
        holds = max(1, v.cargo_free)
        best = None
        for c, srcs in sells.items():
            for a_sid, pa in srcs:
                for b_sid, pb in buys.get(c, []):
                    if pb <= pa or a_sid == b_sid:
                        continue
                    d1, d2 = dist(v.here, a_sid), dist(a_sid, b_sid)
                    if d1 is None or d2 is None:
                        continue
                    score = (pb - pa) * holds / (d1 + d2 + 2)
                    if best is None or score > best[0]:
                        best = (score, a_sid, c, b_sid, pa, pb)
        if best and best[1] != v.here:
            _, a_sid, c, b_sid, pa, pb = best
            return a_sid, f"buy {c} at {a_sid} (~{pa}) for {b_sid} (~{pb})"
        return None, ""

    def _idle(self, v: View, skipped: list[str] | None = None):
        note = f" [replanned: {'; '.join(skipped)}]" if skipped else ""
        out = self._explore(v, "nothing better to do")
        if out[0] is not None and not self._banned_why(out[0], v):
            out[0]["thought"] += note
            return out
        if v.ok("wait"):
            return self._act("wait", {}, f"pass{note}"), Intent()
        return self._act("query_limpets", {}, "out of turns - free no-op"), Intent()

    # ------------------------------------------------------------------ helpers
    def _held_goods(self, v: View) -> list[tuple[str, int]]:
        return sorted(((c, int(q or 0)) for c, q in v.cargo.items() if c != "colonists" and int(q or 0) > 0),
                      key=lambda cq: -cq[1])

    def _note_refused_sells(self, v: View) -> None:
        """At a port we remembered as a buyer, but the engine won't take it now: skip it today."""
        port = v.sector.get("port") or {}
        if not port or not self._held_goods(v):
            return
        sellable = self._sellable_here(v)
        day = int(v.obs.get("day") or 0)
        for c, _q in self._held_goods(v):
            if c in (port.get("buys") or []) and c not in sellable:
                self.mem.bad_sells[f"{v.here}:{c}"] = day

    def _buildable_elsewhere(self, v: View) -> dict[str, Any] | None:
        """A world in another sector whose next citadel can start now (colonists + credits).
        Trailing a rival, we spend the working capital on citadels instead of holding it."""
        floor = 0 if self.pressure is not None else self.working_capital
        for planet in v.worlds():
            tier = next_tier(planet)
            if (tier and planet.get("sector_id") != v.here and _colonists_total(planet) >= tier[1]
                    and v.credits >= tier[0] + floor):
                return planet
        return None

    def _sellable_here(self, v: View) -> set[str]:
        if not v.ok("trade"):
            return set()
        return set((v.params("trade").get("commodity") or {}).get("sell_choices") or [])

    def _unsellable_goods(self, v: View) -> tuple[str, int] | None:
        """Largest held commodity with no buyer here and no reachable known buyer."""
        goods = self._held_goods(v)
        if not goods or not v.worlds():
            return None
        if any(c in self._sellable_here(v) for c, _ in goods):
            return None
        _, why = self._best_route(v)
        if why.startswith("sell"):
            return None
        return goods[0]

    def _refresh_home(self, v: View) -> None:
        mem = self.mem
        candidates = v.genesis_planets() or v.worlds()
        if mem.home_planet is not None and v.planet(mem.home_planet) is None:
            mem.home_planet = mem.home_sector = None
        if candidates and mem.home_planet is None:
            best = max(candidates, key=lambda p: (int(p.get("citadel_level") or 0), _colonists_total(p)))
            mem.home_planet = int(best["id"])
            mem.home_sector = int(best["sector_id"])

    def _work_sites(self, v: View) -> list[dict[str, Any]]:
        sites = [p for p in v.worlds() if p.get("sector_id") == v.here]
        sites.sort(key=lambda p: p.get("id") != self.mem.home_planet)
        return sites

    def _citadel_reserve(self, v: View) -> int:
        """Credits we never spend on colonists/genesis: next citadel tier + working capital."""
        home = v.planet(self.mem.home_planet)
        tier = next_tier(home, lookahead=True) if home else None
        return (tier[0] if tier else 0) + self.working_capital

    def _colonists_needed(self, v: View) -> int:
        home = v.planet(self.mem.home_planet)
        tier = next_tier(home, lookahead=True) if home else None
        if tier is None:
            return 0
        return max(0, tier[1] - _colonists_total(home) - v.colonists_aboard)

    def _needs_stardock(self, v: View) -> bool:
        gplanets = v.genesis_planets()
        if v.genesis_aboard > 0:
            return False
        if not v.worlds():
            # Go only when a StarDock purchase is affordable; poor seats earn first.
            genesis_ok = self._first_genesis_affordable(v, GENESIS_TORPEDO_COST)
            hull_ok = v.ship_class != "cargotran" and v.credits >= self._cargotran_net(v) + self.cash_buffer
            return genesis_ok or hull_ok or self._poor_holds_qty(v) >= POOR_HOLDS_MIN_BUY
        reserve = self._citadel_reserve(v)
        if len(gplanets) < self.target_planets and v.credits >= GENESIS_TORPEDO_COST + reserve:
            return True
        # Ferry trip: colonists still needed, holds mostly free (sell/stock goods first),
        # and at least a small load affordable above the reserve.
        return (v.colonists_aboard == 0 and v.cargo_free >= 25 and self._colonists_needed(v) > 0
                and v.credits - reserve >= 250)

    def _stardock_reason(self, v: View) -> str:
        if v.worlds():
            return "go to StarDock for colonists"
        if v.ship_class != "cargotran" and v.credits >= self._cargotran_net(v) + self.cash_buffer:
            return "autopilot to StarDock (sector 1) for a CargoTran"
        if self._poor_holds_qty(v) >= POOR_HOLDS_MIN_BUY:
            return "autopilot to StarDock (sector 1) for extra holds"
        return "autopilot to StarDock (sector 1) for a genesis torpedo"

    def _first_genesis_affordable(self, v: View, price: int) -> bool:
        """Single source of truth for 'can buy the first genesis and still fund L1'.

        Used both to decide the StarDock trip and the purchase there: when these two
        thresholds disagreed (pressure lowered one), the seat flew to StarDock, bought
        nothing, and flew back - hundreds of times (seed 99 regression)."""
        buffer = 0 if self.pressure is not None else self.cash_buffer
        return v.credits - price >= CITADEL_TIER_COST[0][0] + buffer

    def _cargotran_net(self, v: View) -> int:
        """CargoTran price minus trade-in (25% of the current hull), from the public ship table."""
        if v.here == STARDOCK:
            net = (v.params("buy_ship").get("ship_class") or {}).get("net_cost_by", {}).get("cargotran")
            if isinstance(net, int):
                return net
        cur = SHIP_SPECS.get(str(v.ship_class), {}).get("cost", 0)
        return int(SHIP_SPECS["cargotran"]["cost"]) - int(int(cur) * 0.25)

    def _has_earned(self, v: View) -> bool:
        """Earn before StarDock: the seat has banked real trade profit (its own trade_summary),
        not merely remembered a port pair - so extra holds have a proven loop to pay back on."""
        ts = v.obs.get("trade_summary") or {}
        return int(ts.get("sells") or 0) > 0 and int(ts.get("total_profit_cr") or 0) > 0

    def _poor_holds_qty(self, v: View) -> int:
        """Holds worth buying now: no world, no CargoTran in reach, a trade loop to use them on."""
        if v.worlds() or v.ship_class == "cargotran" or v.genesis_aboard:
            return 0
        if v.credits >= self._cargotran_net(v) + self.cash_buffer:
            return 0  # buy the hull instead; buy_ship would reset extra holds anyway
        holds = int(v.ship.get("holds") or 0)
        if holds >= POOR_HOLDS_TARGET or not self._has_earned(v):
            return 0
        unit = None
        if v.here == STARDOCK:
            unit = (v.params("buy_equip").get("item") or {}).get("unit_price_by", {}).get("holds")
        unit = int(unit or SHIP_SPECS.get(str(v.ship_class), {}).get("base_hold_cost") or 500)
        afford = max(0, (v.credits - POOR_TRADE_CAPITAL) // max(1, unit))
        return int(min(POOR_HOLDS_TARGET - holds, afford))

    def _plot(self, v: View, target: int, why: str) -> dict[str, Any] | None:
        # plot_course is "legal" even when the first hop cannot be paid for; the
        # autopilot then reports ok with 0 hops and costs nothing - a free
        # infinite loop. Only plot when a single warp is affordable.
        if target is None or target == v.here or not v.ok("plot_course") or not v.ok("warp"):
            return None
        return self._act("plot_course", {"target": int(target), "execute": True}, f"{why} (plot {target})")

    def _warp_away_from_stardock(self, v: View) -> int | None:
        choices = [int(c) for c in v.choices("warp", "target")] if v.ok("warp") else []
        choices = [t for t in choices if not self._banned_why({"kind": "warp", "args": {"target": t}}, v)]
        if not choices:
            return None

        def score(t: int):
            d = known_distance(v.known_warps, STARDOCK, t)
            return (-(d if d is not None else 99), self.mem.visits.get(t, 0), t)

        return sorted(choices, key=score)[0]

    def _explore(self, v: View, why: str):
        """N1 frontier-directed exploration over the seat's own map memory.

        1. An unvisited neighbour here -> warp to it.
        2. Otherwise plot (execute) to the nearest unvisited sector adjacent to a known
           one, measured through known warps - one action, so dead ends and fully
           explored pockets are left without A->B->A bouncing.
        3. Fallback: least-visited legal warp, then scan.
        """
        def warp_ok(t: int) -> bool:
            return not self._banned_why({"kind": "warp", "args": {"target": t}}, v)

        choices = [int(c) for c in v.choices("warp", "target")] if v.ok("warp") else []
        choices = [t for t in choices if warp_ok(t)]
        fresh = [t for t in choices if t not in v.known_warps]
        if fresh:
            fresh.sort(key=lambda t: (self.mem.visits.get(t, 0), t))
            return self._act("warp", {"target": fresh[0]}, f"explore -> {fresh[0]} ({why})"), Intent("explore")
        frontier = self._nearest_frontier(v)
        if frontier is not None:
            plot = self._plot(v, frontier, f"explore frontier ({why})")
            if plot and not self._banned_why(plot, v):
                return plot, Intent("explore", frontier)
        if choices:
            choices.sort(key=lambda t: (self.mem.visits.get(t, 0), t))
            return self._act("warp", {"target": choices[0]}, f"explore -> {choices[0]} ({why})"), Intent("explore")
        if v.ok("scan") and v.here not in v.known_warps:
            return self._act("scan", {}, f"scan ({why})"), Intent("explore")
        return None, Intent()

    def _nearest_frontier(self, v: View) -> int | None:
        """Closest unvisited sector (not in known_warps) adjacent to a known sector, via known warps."""
        kw = v.known_warps
        if v.here is None or v.here not in kw:
            return None
        seen = {v.here}
        frontier = [v.here]
        while frontier:
            found: list[int] = []
            nxt: list[int] = []
            for s in frontier:
                for n in kw.get(s, ()):
                    if n in seen:
                        continue
                    seen.add(n)
                    if n not in kw:
                        if not self._banned_why({"kind": "plot_course", "args": {"target": n}}, v):
                            found.append(n)
                    else:
                        nxt.append(n)
            if found:
                return sorted(found, key=lambda t: (self.mem.visits.get(t, 0), t))[0]
            frontier = nxt
        return None

    def _act(self, kind: str, args: dict[str, Any], thought: str) -> dict[str, Any]:
        return {"kind": kind, "args": args, "thought": f"SeatBrain: {thought}"}

    def _finish(self, v: View, action: dict[str, Any]) -> dict[str, Any]:
        mem = self.mem
        gplanets = v.genesis_planets()
        home = v.planet(mem.home_planet)
        if not v.worlds() and v.genesis_aboard == 0 and not self._needs_stardock(v) and v.here != STARDOCK:
            short = "Trade known ports until a CargoTran / genesis / hold upgrade is affordable; StarDock via autopilot."
        elif not gplanets and v.genesis_aboard == 0:
            short = "Autopilot to StarDock (sector 1); buy CargoTran, then a genesis torpedo."
        elif v.genesis_aboard:
            short = "Deploy genesis in a legal deep sector, then land and build a citadel."
        else:
            short = f"Ferry colonists StarDock -> sector {mem.home_sector}; grow citadel on planet {mem.home_planet}."
        medium = (f"Home planet {mem.home_planet} (L{home.get('citadel_level')}, "
                  f"{_colonists_total(home)} colonists)" if home else "Found a genesis home world")
        if self.pressure and self.pressure.get("leader"):
            medium += f"; trailing {self.pressure['leader']} ({self.pressure['leader_nw']} NW) - empire rungs first"
        action["goal_short"] = short
        action["goal_medium"] = medium
        action["goal_long"] = f"Hold {self.target_planets}+ genesis worlds with rising citadels; win on net worth."
        action["scratchpad_update"] = mem.dump()
        return action


__all__ = ["SeatBrain", "SeatMemory", "View", "next_tier"]
