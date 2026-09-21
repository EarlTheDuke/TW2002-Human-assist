#!/usr/bin/env python3
"""Drive P3/P4/P5 as concurrent external seats for a Commander playtest.

Loads tokens from `.tw2k/external_tokens.json`, long-polls
`/harness/v1/{pid}/observation`, posts a §7-style heuristic action, and
appends structured + human-readable logs under `docs/playtests/`.

  python scripts/playtest_commander_3seat.py --base-url http://127.0.0.1:8030

Requires: pip install httpx
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:
    print("pip install httpx", file=sys.stderr)
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOKENS = ROOT / ".tw2k" / "external_tokens.json"
PLAYTESTS = ROOT / "docs" / "playtests"


def _as_dict(x: Any) -> dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _as_list(x: Any) -> list[Any]:
    return x if isinstance(x, list) else []


def _sector(obs: dict[str, Any]) -> dict[str, Any]:
    return _as_dict(obs.get("sector") or obs.get("sector_info"))


def _ship(obs: dict[str, Any]) -> dict[str, Any]:
    return _as_dict(obs.get("ship"))


def _port(obs: dict[str, Any]) -> dict[str, Any]:
    sec = _sector(obs)
    return _as_dict(sec.get("port") or obs.get("port"))


def _warps(obs: dict[str, Any]) -> list[int]:
    sec = _sector(obs)
    raw = (
        sec.get("warps_out")
        or sec.get("warps_out")
        or sec.get("warps")
        or obs.get("warps_out")
        or []
    )
    out: list[int] = []
    for w in _as_list(raw):
        try:
            out.append(int(w))
        except (TypeError, ValueError):
            continue
    return out


def _cargo(obs: dict[str, Any]) -> dict[str, int]:
    ship = _ship(obs)
    cargo = _as_dict(ship.get("cargo") or obs.get("cargo"))
    out: dict[str, int] = {}
    for k, v in cargo.items():
        try:
            out[str(k)] = int(v or 0)
        except (TypeError, ValueError):
            out[str(k)] = 0
    return out


def _cargo_free(obs: dict[str, Any]) -> int:
    ship = _ship(obs)
    for key in ("cargo_free", "holds_free", "free_holds"):
        if ship.get(key) is not None:
            try:
                return int(ship[key])
            except (TypeError, ValueError):
                pass
    return 0


def _credits(obs: dict[str, Any]) -> int:
    for key in ("credits", "cash"):
        if obs.get(key) is not None:
            try:
                return int(obs[key])
            except (TypeError, ValueError):
                pass
    return int(_as_dict(obs.get("self")).get("credits") or 0)


def _turns_left(obs: dict[str, Any]) -> int:
    for key in ("turns_remaining", "turns_left"):
        if obs.get(key) is not None:
            try:
                return int(obs[key])
            except (TypeError, ValueError):
                pass
    return 0


def _day(obs: dict[str, Any]) -> int:
    try:
        return int(obs.get("day") or 0)
    except (TypeError, ValueError):
        return 0


def _sector_id(obs: dict[str, Any]) -> int:
    sec = _sector(obs)
    try:
        return int(sec.get("id") or obs.get("sector_id") or 0)
    except (TypeError, ValueError):
        return 0


def _recent_failure_keys(obs: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for item in _as_list(obs.get("recent_failures")):
        if isinstance(item, dict):
            kind = str(item.get("kind") or item.get("action") or "")
            tgt = str(item.get("target") or item.get("args") or "")
            keys.add(f"{kind}:{tgt}")
        else:
            keys.add(str(item))
    return keys


def _port_buys(port: dict[str, Any]) -> list[str]:
    buys = port.get("buys") or port.get("buy") or []
    if isinstance(buys, list):
        return [str(x) for x in buys]
    stock = _as_dict(port.get("stock"))
    return [k for k, v in stock.items() if _as_dict(v).get("side") == "buy"]


def _port_sells(port: dict[str, Any]) -> list[str]:
    sells = port.get("sells") or port.get("sell") or []
    if isinstance(sells, list):
        return [str(x) for x in sells]
    stock = _as_dict(port.get("stock"))
    return [k for k, v in stock.items() if _as_dict(v).get("side") == "sell"]


def _stock_price(port: dict[str, Any], commodity: str) -> int:
    stock = _as_dict(port.get("stock"))
    entry = _as_dict(stock.get(commodity))
    for key in ("price", "unit_price", "current_price"):
        if entry.get(key) is not None:
            try:
                return max(1, int(entry[key]))
            except (TypeError, ValueError):
                pass
    return 30


def _stock_qty(port: dict[str, Any], commodity: str) -> int:
    stock = _as_dict(port.get("stock"))
    entry = _as_dict(stock.get(commodity))
    for key in ("current", "qty", "amount"):
        if entry.get(key) is not None:
            try:
                return max(0, int(entry[key]))
            except (TypeError, ValueError):
                pass
    return 9999


def _adjacent_unknown(obs: dict[str, Any]) -> list[int]:
    unknown: list[int] = []
    for adj in _as_list(obs.get("adjacent")):
        if not isinstance(adj, dict):
            continue
        known = adj.get("known")
        if known is False or known is None:
            try:
                unknown.append(int(adj["id"]))
            except (KeyError, TypeError, ValueError):
                continue
    legal = set(_warps(obs))
    return [s for s in unknown if (not legal) or s in legal]


def _known_ports(obs: dict[str, Any]) -> list[dict[str, Any]]:
    return [p for p in _as_list(obs.get("known_ports")) if isinstance(p, dict)]


def _action(
    kind: str,
    args: dict[str, Any] | None = None,
    *,
    thought: str,
    scratch: str | None = None,
    goal: str | None = None,
) -> dict[str, Any]:
    a: dict[str, Any] = {"kind": kind, "args": args or {}, "thought": thought}
    if scratch is not None:
        a["scratchpad_update"] = scratch[:1500]
    if goal is not None:
        a["goal_short"] = goal[:200]
    return a


def decide(obs: dict[str, Any], *, seat: str, memory: dict[str, Any]) -> dict[str, Any]:
    """Competent §7 heuristic — sell, buy, explore, scan, StarDock when rich."""
    turns = _turns_left(obs)
    credits = _credits(obs)
    sid = _sector_id(obs)
    day = _day(obs)
    cargo = _cargo(obs)
    free = _cargo_free(obs)
    port = _port(obs)
    warps = _warps(obs)
    failures = _recent_failure_keys(obs)
    visited: set[int] = set(memory.setdefault("visited", set()))
    visited.add(sid)
    memory["visited"] = visited
    last_kinds: list[str] = memory.setdefault("last_kinds", [])

    scratch = (
        f"{seat} d{day} s{sid} cr={credits} free={free} "
        f"cargo={{{','.join(f'{k}:{v}' for k, v in cargo.items() if v)}}}"
    )
    goal = memory.get("goal") or "explore+trade; upgrade at StarDock when rich"

    if turns < 3:
        return _action("wait", thought="turns low — wait out the day", scratch=scratch, goal=goal)

    def ok(kind: str, target: Any = "") -> bool:
        return f"{kind}:{target}" not in failures

    if port:
        for commodity in _port_buys(port):
            qty = int(cargo.get(commodity) or 0)
            if qty > 0 and ok("trade", commodity):
                goal = f"sell {commodity} then rebuy/explore"
                memory["goal"] = goal
                return _action(
                    "trade",
                    {"commodity": commodity, "qty": qty, "side": "sell"},
                    thought=f"sell {qty} {commodity} at port",
                    scratch=scratch + f" | selling {commodity}",
                    goal=goal,
                )

        sells = _port_sells(port)
        if free > 0 and sells and credits > 800 and ok("trade"):
            commodity = next((c for c in sells if int(cargo.get(c) or 0) == 0), sells[0])
            price = _stock_price(port, commodity)
            avail = _stock_qty(port, commodity)
            qty = max(1, min(free, avail, credits // max(1, price) // 2))
            if qty >= 1:
                goal = f"haul {commodity}; find buyer"
                memory["goal"] = goal
                return _action(
                    "trade",
                    {"commodity": commodity, "qty": qty, "side": "buy"},
                    thought=f"buy {qty} {commodity} @~{price}",
                    scratch=scratch + f" | buying {commodity}x{qty}",
                    goal=goal,
                )

    if credits >= 45_000 and sid != 1:
        if 1 in warps and ok("warp", 1):
            goal = "reach StarDock for ship/equip upgrade"
            memory["goal"] = goal
            return _action(
                "warp",
                {"target": 1},
                thought="rich — warp toward StarDock",
                scratch=scratch + " | stardock run",
                goal=goal,
            )

    if sid == 1 and credits >= 45_000:
        if credits >= 80_000 and ok("buy_ship"):
            goal = "upgrade hull at StarDock"
            memory["goal"] = goal
            return _action(
                "buy_ship",
                {"ship_class": "merchant_cruiser"},
                thought="buy bigger hull at StarDock",
                scratch=scratch + " | buy_ship",
                goal=goal,
            )
        if ok("buy_equip"):
            goal = "stock genesis/fighters at StarDock"
            memory["goal"] = goal
            return _action(
                "buy_equip",
                {"item": "genesis", "qty": 1},
                thought="buy genesis device",
                scratch=scratch + " | buy genesis",
                goal=goal,
            )

    unknown = _adjacent_unknown(obs)
    if unknown and ok("scan") and last_kinds[-2:] != ["scan", "scan"] and turns >= 4:
        goal = "map unknown neighbours"
        memory["goal"] = goal
        return _action("scan", thought="scan unknown adjacent", scratch=scratch + " | scan", goal=goal)

    candidates = [w for w in (unknown or warps) if w not in visited]
    if not candidates:
        candidates = [w for w in warps if w not in visited] or list(warps)
    last_target = memory.get("last_warp_target")
    if last_target in candidates and len(candidates) > 1:
        candidates = [w for w in candidates if w != last_target]

    if candidates and turns >= 3:
        carrying = [c for c, q in cargo.items() if q > 0]
        target = candidates[0]
        if carrying:
            for kp in _known_ports(obs):
                buys = kp.get("buys") or []
                if any(c in buys for c in carrying):
                    try:
                        dest = int(kp.get("sector_id") or kp.get("id") or 0)
                    except (TypeError, ValueError):
                        dest = 0
                    if dest in candidates:
                        target = dest
                        break
        if ok("warp", target):
            memory["last_warp_target"] = target
            goal = memory.get("goal") or f"explore toward {target}"
            return _action(
                "warp",
                {"target": target},
                thought=f"warp to {target} (explore/trade)",
                scratch=scratch + f" | warp {target}",
                goal=goal,
            )

    if warps and turns >= 3:
        target = warps[0]
        return _action(
            "warp",
            {"target": target},
            thought=f"fallback warp to {target}",
            scratch=scratch + f" | fallback warp {target}",
            goal=goal,
        )

    return _action("wait", thought="no legal moves — wait", scratch=scratch, goal=goal)


class SeatStats:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.actions_ok = 0
        self.actions_fail = 0
        self.timeouts = 0
        self.stale = 0
        self.max_day = 0
        self.by_seat: dict[str, int] = {}
        self.stop = False
        self.reason = ""


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _append_md(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")


def seat_loop(
    *,
    base_url: str,
    pid: str,
    token: str,
    stats: SeatStats,
    jsonl_path: Path,
    md_path: Path,
    min_turns: int,
    max_wall_s: float,
    max_day: int,
    t0: float,
) -> None:
    headers = {"authorization": f"Bearer {token}"}
    memory: dict[str, Any] = {"visited": set(), "last_kinds": [], "goal": "explore+trade"}

    with httpx.Client(base_url=base_url.rstrip("/"), headers=headers, timeout=90.0) as client:
        try:
            r = client.get(f"/harness/v1/{pid}/status")
            if r.status_code != 200:
                _append_md(md_path, f"- `{_now()}` **{pid}** status {r.status_code}: {r.text[:200]}")
            else:
                body = r.json()
                _append_md(
                    md_path,
                    f"- `{_now()}` **{pid}** connected — match={body.get('match_status')} "
                    f"awaiting={body.get('awaiting_input')}",
                )
        except Exception as exc:  # noqa: BLE001
            _append_md(md_path, f"- `{_now()}` **{pid}** status error: {exc}")

        while not stats.stop and (time.time() - t0) < max_wall_s:
            with stats.lock:
                if stats.actions_ok >= min_turns:
                    stats.stop = True
                    stats.reason = stats.reason or f"reached min_turns={min_turns}"
                    break
                if stats.max_day >= max_day:
                    stats.stop = True
                    stats.reason = stats.reason or f"reached max_day={max_day}"
                    break

            try:
                r = client.get(
                    f"/harness/v1/{pid}/observation",
                    params={"wait_s": 30, "format": "both"},
                )
            except Exception as exc:  # noqa: BLE001
                _append_md(md_path, f"- `{_now()}` **{pid}** observation error: {exc}")
                time.sleep(1.0)
                continue

            if r.status_code == 503:
                _append_md(md_path, f"- `{_now()}` **{pid}** match over / seat closed (503)")
                with stats.lock:
                    stats.stop = True
                    stats.reason = stats.reason or "match finished (503)"
                return

            if r.status_code != 200:
                _append_md(
                    md_path,
                    f"- `{_now()}` **{pid}** observation HTTP {r.status_code}: {r.text[:180]}",
                )
                time.sleep(0.5)
                continue

            body = r.json()
            match_status = body.get("match_status") or body.get("status")
            if match_status in ("finished", "error", "stopped"):
                _append_md(md_path, f"- `{_now()}` **{pid}** match_status={match_status}")
                with stats.lock:
                    stats.stop = True
                    stats.reason = stats.reason or f"match_status={match_status}"
                return

            if not body.get("awaiting_input"):
                continue

            obs = body.get("observation") or {}
            turn_seq = body.get("turn_seq")
            day = _day(obs)
            sid = _sector_id(obs)
            credits = _credits(obs)

            action = decide(obs, seat=pid, memory=memory)
            kind = str(action.get("kind"))
            memory.setdefault("last_kinds", []).append(kind)
            memory["last_kinds"] = memory["last_kinds"][-12:]

            t_post = time.time()
            try:
                pr = client.post(
                    f"/harness/v1/{pid}/action",
                    json={"turn_seq": turn_seq, "action": action},
                )
            except Exception as exc:  # noqa: BLE001
                _append_md(md_path, f"- `{_now()}` **{pid}** action POST error: {exc}")
                continue

            latency = time.time() - t_post
            last_result: dict[str, Any] = {}
            note = ""

            if pr.status_code == 409:
                detail: dict[str, Any]
                try:
                    detail = pr.json()
                except Exception:  # noqa: BLE001
                    detail = {"raw": pr.text[:200]}
                code = str(detail.get("code") or detail.get("detail") or detail)
                note = f"409 {code}"
                with stats.lock:
                    if "stale" in code.lower():
                        stats.stale += 1
                    else:
                        stats.actions_fail += 1
                _append_md(md_path, f"- `{_now()}` **{pid}** turn {turn_seq} rejected: {code}")
            elif pr.status_code >= 400:
                note = f"HTTP {pr.status_code}"
                with stats.lock:
                    stats.actions_fail += 1
                _append_md(
                    md_path,
                    f"- `{_now()}` **{pid}** action HTTP {pr.status_code}: {pr.text[:180]}",
                )
            else:
                time.sleep(0.05)
                try:
                    st = client.get(f"/harness/v1/{pid}/status").json()
                    last_result = _as_dict(st.get("last_result"))
                except Exception:  # noqa: BLE001
                    last_result = {}
                ok = bool(last_result.get("ok", True))
                if not ok:
                    note = f"FAIL {last_result.get('error')}"
                    with stats.lock:
                        stats.actions_fail += 1
                    _append_md(
                        md_path,
                        f"- `{_now()}` **{pid}** D{day} s{sid} `{kind}` FAILED: {last_result.get('error')}",
                    )
                else:
                    note = "ok"
                    with stats.lock:
                        stats.actions_ok += 1
                        stats.by_seat[pid] = stats.by_seat.get(pid, 0) + 1
                        stats.max_day = max(stats.max_day, day)

            _append_jsonl(
                jsonl_path,
                {
                    "ts": _now(),
                    "pid": pid,
                    "day": day,
                    "tick": obs.get("tick"),
                    "turn_seq": turn_seq,
                    "action": action,
                    "last_result": last_result,
                    "credits": credits,
                    "sector": sid,
                    "notes": note,
                    "latency_s": round(latency, 3),
                },
            )

            for ev in _as_list(obs.get("recent_events"))[-3:]:
                if not isinstance(ev, dict):
                    continue
                kind_e = str(ev.get("kind") or "")
                if kind_e in ("AGENT_ERROR", "external_timeout", "stale_turn") or "timeout" in kind_e.lower():
                    _append_md(
                        md_path,
                        f"- `{_now()}` **{pid}** recent_event: {kind_e} {str(ev)[:160]}",
                    )
                    with stats.lock:
                        if "timeout" in kind_e.lower():
                            stats.timeouts += 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default=os.environ.get("TW2K_HARNESS_URL") or "http://127.0.0.1:8030")
    ap.add_argument("--tokens-file", default=None)
    ap.add_argument("--seats", default="P3,P4,P5")
    ap.add_argument("--min-turns", type=int, default=40)
    ap.add_argument("--max-wall-s", type=float, default=1500.0)
    ap.add_argument("--max-day", type=int, default=3)
    ap.add_argument("--session-id", default="2026-09-21-commander")
    args = ap.parse_args()

    tokens_path = Path(args.tokens_file) if args.tokens_file else Path(
        os.environ.get("TW2K_EXTERNAL_TOKENS_FILE") or DEFAULT_TOKENS
    )
    if not tokens_path.is_file():
        print(f"tokens file missing: {tokens_path}", file=sys.stderr)
        return 2
    tokens = json.loads(tokens_path.read_text(encoding="utf-8"))
    seats = [s.strip().upper() for s in args.seats.split(",") if s.strip()]
    missing = [s for s in seats if not tokens.get(s)]
    if missing:
        print(f"missing tokens for {missing} in {tokens_path}", file=sys.stderr)
        return 2

    PLAYTESTS.mkdir(parents=True, exist_ok=True)
    jsonl_path = PLAYTESTS / "2026-09-21-commander-session.jsonl"
    md_path = PLAYTESTS / "2026-09-21-SESSION_LOG.md"

    _append_md(
        md_path,
        f"\n## Session start `{_now()}`\n"
        f"- base_url: `{args.base_url}`\n"
        f"- seats: {', '.join(seats)}\n"
        f"- min_turns={args.min_turns} max_wall_s={args.max_wall_s} max_day={args.max_day}\n"
        f"- heuristic: GROK_BOT_PLAYER_GUIDE §7 (sell/buy/explore/scan/stardock)\n",
    )

    stats = SeatStats()
    t0 = time.time()
    threads = [
        threading.Thread(
            target=seat_loop,
            kwargs=dict(
                base_url=args.base_url,
                pid=pid,
                token=str(tokens[pid]),
                stats=stats,
                jsonl_path=jsonl_path,
                md_path=md_path,
                min_turns=args.min_turns,
                max_wall_s=args.max_wall_s,
                max_day=args.max_day,
                t0=t0,
            ),
            name=f"seat-{pid}",
            daemon=True,
        )
        for pid in seats
    ]
    for t in threads:
        t.start()

    try:
        while any(t.is_alive() for t in threads):
            for t in threads:
                t.join(timeout=1.0)
            if (time.time() - t0) >= args.max_wall_s:
                with stats.lock:
                    stats.stop = True
                    stats.reason = stats.reason or "max_wall_s"
                break
    except KeyboardInterrupt:
        with stats.lock:
            stats.stop = True
            stats.reason = "keyboard_interrupt"

    for t in threads:
        t.join(timeout=5.0)

    elapsed = time.time() - t0
    summary = (
        f"\n## Session end `{_now()}`\n"
        f"- reason: {stats.reason or 'threads exited'}\n"
        f"- wall_s: {elapsed:.1f}\n"
        f"- actions_ok: {stats.actions_ok}  fail: {stats.actions_fail}  "
        f"stale: {stats.stale}  timeouts_seen: {stats.timeouts}\n"
        f"- by_seat: {stats.by_seat}\n"
        f"- max_day_seen: {stats.max_day}\n"
        f"- jsonl: `{jsonl_path.relative_to(ROOT)}`\n"
    )
    _append_md(md_path, summary)
    print(summary)
    if not all(stats.by_seat.get(s, 0) > 0 for s in seats):
        print("WARNING: not every seat took a real action", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
