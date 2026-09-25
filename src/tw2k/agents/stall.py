"""Progress-based stall detection for seat brains (seat-bot S2).

docs/plans/2026-09-24-seat-bot-competitive.md. The Kimi3 Path-B brain judged
loops by *target alternation* ("same two plot targets = ping-pong"). That
refused legitimate StarDock <-> home ferries and same-target replots, while
missing real loops that alternated sectors without ever plotting (14 <-> 571)
or that spent credits without gaining anything (68: buy fuel, land, dump).

This module judges **progress toward a declared intent** instead:

* Universal progress (always counts): map memory grew, an owned planet
  appeared / disappeared, citadel level or target changed, owned-planet
  colonists grew (same day), genesis count or ship class changed.
* Travel (``Intent.target``): arrival, or the known-warp distance to the
  target dropped below the best seen *for that target*. Oscillating between
  two sectors never beats its own best, so it is not progress; switching the
  target (the next ferry leg) resets the best.
* Intent kind extras: ``trade`` - credits rose above the best seen under the
  current intent; ``colonize`` - colonists aboard grew; ``acquire`` - credits
  above best (saving up).

``StallDetector.observe`` returns a report; ``stalled`` is true after
``window`` consecutive observations without progress. The detector reads only
the seat's own observation (dict or Observation model) - no god view.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

INTENT_KINDS = ("travel", "trade", "colonize", "explore", "acquire")


@dataclass(frozen=True)
class Intent:
    kind: str | None = None
    target: int | None = None  # sector the brain is heading for, if any


@dataclass(frozen=True)
class Snapshot:
    day: int
    sector: int | None
    credits: int
    colonists_aboard: int
    known: int
    genesis: int
    ship_class: str | None
    planets: tuple[tuple[int, int, int, int], ...]  # (id, citadel_level, citadel_target, colonists_total)
    known_warps: dict[int, tuple[int, ...]] = field(compare=False, hash=False, default_factory=dict)


@dataclass
class ProgressReport:
    progress: bool
    reasons: list[str]
    idle_turns: int
    stalled: bool
    recent_sectors: list[int | None]

    def summary(self) -> str:
        if self.progress:
            return "progress: " + ", ".join(self.reasons)
        trail = "->".join(str(s) for s in self.recent_sectors)
        return f"no progress for {self.idle_turns} turn(s) (sectors {trail})"


def _as_dict(obs: Any) -> dict[str, Any]:
    if isinstance(obs, dict):
        return obs
    dump = getattr(obs, "model_dump", None)
    if callable(dump):
        return dump(mode="json")
    raise TypeError("observation must be a dict or pydantic model")


def _planet_colonists(p: dict[str, Any]) -> int:
    total = p.get("colonists_total")
    if isinstance(total, int):
        return total
    col = p.get("colonists")
    if isinstance(col, dict):
        return sum(int(v or 0) for v in col.values())
    return int(col or 0)


def snapshot(obs: Any) -> Snapshot:
    o = _as_dict(obs)
    ship = o.get("ship") or {}
    cargo = ship.get("cargo") or {}
    kw_raw = o.get("known_warps") or {}
    known_warps = {int(k): tuple(int(x) for x in (v or ())) for k, v in kw_raw.items()}
    known_sectors = o.get("known_sectors")
    known = len(known_sectors) if isinstance(known_sectors, list) else len(known_warps)
    planets = tuple(sorted(
        (int(p["id"]), int(p.get("citadel_level") or 0), int(p.get("citadel_target") or 0), _planet_colonists(p))
        for p in (o.get("owned_planets") or []) if isinstance(p, dict) and p.get("id") is not None
    ))
    sector = (o.get("sector") or {}).get("id")
    return Snapshot(
        day=int(o.get("day") or 0),
        sector=int(sector) if sector is not None else None,
        credits=int(o.get("credits") or 0),
        colonists_aboard=int(cargo.get("colonists") or 0),
        known=known,
        genesis=int(ship.get("genesis") or 0),
        ship_class=ship.get("class"),
        planets=planets,
        known_warps=known_warps,
    )


def known_distance(known_warps: dict[int, tuple[int, ...]], src: int | None, dst: int | None, cap: int = 60) -> int | None:
    """Hop count src->dst over the seat's own warp memory, or None if unknown."""
    if src is None or dst is None:
        return None
    if src == dst:
        return 0
    seen = {src}
    frontier = [src]
    depth = 0
    while frontier and depth < cap:
        depth += 1
        nxt: list[int] = []
        for s in frontier:
            for n in known_warps.get(s, ()):
                if n == dst:
                    return depth
                if n not in seen:
                    seen.add(n)
                    nxt.append(n)
        frontier = nxt
    return None


class StallDetector:
    def __init__(self, window: int = 6) -> None:
        self.window = max(1, int(window))
        self._prev: Snapshot | None = None
        self._intent = Intent()
        self._best_dist: int | None = None
        self._best_credits: int | None = None
        self.idle_turns = 0
        self._trail: deque[int | None] = deque(maxlen=self.window + 2)

    def reset(self) -> None:
        self.__init__(self.window)

    def _set_intent(self, intent: Intent, cur: Snapshot) -> None:
        if intent.target != self._intent.target:
            self._best_dist = known_distance(cur.known_warps, cur.sector, intent.target)
        if intent.kind != self._intent.kind:
            self._best_credits = cur.credits
        self._intent = intent

    def observe(self, obs: Any, intent: Intent | None = None) -> ProgressReport:
        cur = snapshot(obs)
        intent = intent or Intent()
        self._trail.append(cur.sector)
        prev = self._prev
        self._prev = cur
        if prev is None:
            self._intent = intent
            self._best_dist = known_distance(cur.known_warps, cur.sector, intent.target)
            self._best_credits = cur.credits
            return ProgressReport(True, ["first observation"], 0, False, list(self._trail))

        reasons: list[str] = []
        same_day = cur.day == prev.day

        # Universal signals.
        if cur.known > prev.known:
            reasons.append(f"map +{cur.known - prev.known}")
        prev_pl = {p[0]: p for p in prev.planets}
        cur_pl = {p[0]: p for p in cur.planets}
        if set(prev_pl) != set(cur_pl):
            reasons.append("owned planets changed")
        for pid, (_, lvl, tgt, col) in cur_pl.items():
            old = prev_pl.get(pid)
            if old is None:
                continue
            if (lvl, tgt) != (old[1], old[2]):
                reasons.append(f"citadel p{pid} L{lvl}->{tgt}")
            elif same_day and col > old[3]:
                reasons.append(f"colonists p{pid} +{col - old[3]}")
        if cur.genesis != prev.genesis:
            reasons.append("genesis count changed")
        if cur.ship_class != prev.ship_class:
            reasons.append(f"ship {cur.ship_class}")

        # Travel toward the declared target (compared against the best seen for
        # the PREVIOUS intent's target before switching, so the arrival that
        # completes one ferry leg still counts).
        tgt = self._intent.target
        if tgt is not None:
            if cur.sector == tgt and prev.sector != tgt:
                reasons.append(f"arrived {tgt}")
            else:
                d = known_distance(cur.known_warps, cur.sector, tgt)
                if d is not None and (self._best_dist is None or d < self._best_dist):
                    reasons.append(f"closer to {tgt} ({d} hops)")
                    self._best_dist = d

        # Intent-specific signals.
        kind = self._intent.kind
        if kind in ("trade", "acquire") and same_day and self._best_credits is not None and cur.credits > self._best_credits:
            reasons.append(f"credits {cur.credits}")
            self._best_credits = cur.credits
        if kind == "colonize" and cur.colonists_aboard > prev.colonists_aboard:
            reasons.append(f"colonists aboard +{cur.colonists_aboard - prev.colonists_aboard}")

        self._set_intent(intent, cur)
        progress = bool(reasons)
        self.idle_turns = 0 if progress else self.idle_turns + 1
        return ProgressReport(progress, reasons, self.idle_turns, self.idle_turns >= self.window,
                              list(self._trail)[-(self.idle_turns + 1):] if not progress else [cur.sector])


__all__ = ["INTENT_KINDS", "Intent", "ProgressReport", "Snapshot", "StallDetector", "known_distance", "snapshot"]
