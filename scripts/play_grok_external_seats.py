#!/usr/bin/env python3
"""Drive external seats with real xAI Grok (+ optional Commander mailbox for P3).

  P4/P5: OpenAI-compatible calls to https://api.x.ai/v1 (XAI_API_KEY)
  P3:    waits for Commander decision file, falls back to xAI if near deadline

  python scripts/play_grok_external_seats.py --base-url http://127.0.0.1:8031
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "docs" / "playtests"
TOKENS = ROOT / ".tw2k" / "external_tokens.json"
PENDING = PLAY / "commander_pending.json"
ACTION = PLAY / "commander_action.json"
LOG_JSONL = PLAY / "2026-09-21-grok-live.jsonl"
LOG_MD = PLAY / "2026-09-21-GROK-LIVE.md"
XAI_URL = os.environ.get("TW2K_XAI_BASE_URL", "https://api.x.ai/v1").rstrip("/")
XAI_MODEL = os.environ.get("TW2K_XAI_MODEL", "grok-4-1-fast-reasoning")


def load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def append_jsonl(obj: dict[str, Any]) -> None:
    PLAY.mkdir(parents=True, exist_ok=True)
    with LOG_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def append_md(line: str) -> None:
    PLAY.mkdir(parents=True, exist_ok=True)
    with LOG_MD.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise
        return json.loads(m.group(0))


def call_xai(system: str, user: str, api_key: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (action_dict, meta)."""
    body = {
        "model": XAI_MODEL,
        "temperature": 0.5,
        "max_tokens": 900,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    t0 = time.time()
    with httpx.Client(timeout=120.0) as c:
        r = c.post(
            f"{XAI_URL}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body,
        )
        r.raise_for_status()
        data = r.json()
    latency = time.time() - t0
    content = data["choices"][0]["message"].get("content") or ""
    usage = data.get("usage") or {}
    parsed = extract_json(content)
    # Normalize to harness action
    if "action" in parsed and isinstance(parsed["action"], dict):
        action = parsed["action"]
        for k in ("thought", "scratchpad_update", "goal_short", "goal_medium", "goal_long"):
            if k in parsed and k not in action:
                action[k] = parsed[k]
    else:
        action = parsed
    if "kind" not in action:
        raise ValueError(f"no kind in model output: {content[:300]}")
    action.setdefault("args", {})
    meta = {
        "provider": "xai",
        "model": XAI_MODEL,
        "latency_s": round(latency, 3),
        "usage": usage,
        "raw_preview": content[:400],
    }
    return action, meta


def build_user_msg(obs: dict[str, Any], llm_user: str | None) -> str:
    if llm_user:
        return (
            "Return ONE JSON object with keys: thought, scratchpad_update, "
            "goal_short, goal_medium, goal_long, action:{kind,args}.\n"
            "You are an external Grok Bot seat. Be decisive; prefer legal warps/trades.\n\n"
            + llm_user
        )
    return (
        "Return ONE JSON object: thought, scratchpad_update, goal_short, "
        "goal_medium, goal_long, action:{kind,args}.\n\n"
        + json.dumps(obs, ensure_ascii=False)[:12000]
    )


def commander_decide(obs: dict[str, Any], turn_seq: int, deadline_at: float | None, pid: str) -> dict[str, Any] | None:
    """Mailbox: write pending, wait for Commander action file."""
    PENDING.write_text(
        json.dumps(
            {
                "ts": now_iso(),
                "pid": pid,
                "turn_seq": turn_seq,
                "deadline_at": deadline_at,
                "observation": obs,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    if ACTION.exists():
        try:
            ACTION.unlink()
        except OSError:
            pass
    append_md(f"- `{now_iso()}` **COMMANDER mailbox** open for {pid} turn_seq={turn_seq}")
    # Wait until ~25s before deadline or 90s max
    limit = time.time() + 90
    if deadline_at:
        limit = min(limit, float(deadline_at) - 25)
    while time.time() < limit:
        if ACTION.exists():
            try:
                raw = json.loads(ACTION.read_text(encoding="utf-8"))
                ACTION.unlink(missing_ok=True)
                if int(raw.get("turn_seq", turn_seq)) != int(turn_seq):
                    continue
                act = raw.get("action") or raw
                if "kind" in act:
                    act.setdefault("thought", act.get("thought") or "Commander manual decision")
                    return act
            except Exception as e:
                append_md(f"- commander action parse error: {e}")
        time.sleep(0.4)
    return None


def seat_loop(
    base: str,
    pid: str,
    token: str,
    brain: str,
    system: str,
    api_key: str,
    stop: threading.Event,
    stats: dict[str, Any],
) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=base, headers=headers, timeout=70.0) as client:
        append_md(f"- `{now_iso()}` **{pid}** brain=`{brain}` connected")
        while not stop.is_set():
            try:
                r = client.get(
                    f"/harness/v1/{pid}/observation",
                    params={"wait_s": 30, "format": "both"},
                )
                if r.status_code == 503:
                    time.sleep(2)
                    continue
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                append_md(f"- `{now_iso()}` {pid} poll error: {e}")
                time.sleep(2)
                continue
            if data.get("match_status") in ("finished", "error"):
                stats["done"] = True
                break
            if not data.get("awaiting_input"):
                continue
            obs = data.get("observation") or {}
            seq = data["turn_seq"]
            deadline = data.get("deadline_at")
            llm_user = data.get("llm_user_message")
            brain_used = brain
            meta: dict[str, Any] = {}
            try:
                if brain == "commander":
                    action = commander_decide(obs, seq, deadline, pid)
                    if action is None:
                        brain_used = "xai-fallback"
                        action, meta = call_xai(system, build_user_msg(obs, llm_user), api_key)
                        action["thought"] = "[Commander timeout→Grok] " + str(action.get("thought") or "")
                    else:
                        meta = {"provider": "commander", "model": "Commander"}
                else:
                    action, meta = call_xai(system, build_user_msg(obs, llm_user), api_key)
                post = client.post(
                    f"/harness/v1/{pid}/action",
                    json={"turn_seq": seq, "action": action},
                )
                if post.status_code == 409:
                    stats["stale"] = stats.get("stale", 0) + 1
                    append_md(f"- `{now_iso()}` {pid} STALE turn_seq={seq}")
                    append_jsonl({"ts": now_iso(), "pid": pid, "event": "stale", "turn_seq": seq})
                    continue
                post.raise_for_status()
                status = client.get(f"/harness/v1/{pid}/status").json()
                last = status.get("last_result")
                stats["ok"] = stats.get("ok", 0) + 1
                stats["by_seat"][pid] = stats["by_seat"].get(pid, 0) + 1
                if meta.get("provider") == "xai" or brain_used.startswith("xai"):
                    stats["xai_calls"] = stats.get("xai_calls", 0) + 1
                if meta.get("provider") == "commander":
                    stats["commander_turns"] = stats.get("commander_turns", 0) + 1
                row = {
                    "ts": now_iso(),
                    "pid": pid,
                    "brain": brain_used,
                    "day": obs.get("day"),
                    "tick": obs.get("tick"),
                    "turn_seq": seq,
                    "action": {"kind": action.get("kind"), "args": action.get("args"), "thought": action.get("thought")},
                    "last_result": last,
                    "credits": obs.get("credits"),
                    "sector": (obs.get("sector") or {}).get("id"),
                    "meta": {k: meta[k] for k in meta if k != "raw_preview"},
                    "raw_preview": meta.get("raw_preview"),
                }
                append_jsonl(row)
                append_md(
                    f"- `{now_iso()}` **{pid}** [{brain_used}] {action.get('kind')} "
                    f"ok={last and last.get('ok')} cr={obs.get('credits')} "
                    f"thought={str(action.get('thought') or '')[:120]}"
                )
            except Exception as e:
                stats["fail"] = stats.get("fail", 0) + 1
                append_md(f"- `{now_iso()}` {pid} DECISION ERROR: {e}")
                # emergency wait to avoid timeout cascade if possible
                try:
                    client.post(
                        f"/harness/v1/{pid}/action",
                        json={
                            "turn_seq": seq,
                            "action": {"kind": "wait", "args": {}, "thought": f"error fallback: {e}"[:200]},
                        },
                    )
                except Exception:
                    pass


def main() -> int:
    load_dotenv()
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8031")
    ap.add_argument("--seats", default="P3,P4,P5")
    ap.add_argument("--all-commander", action="store_true")
    ap.add_argument("--min-xai-turns", type=int, default=12, help="stop after this many xAI calls")
    ap.add_argument("--min-commander-turns", type=int, default=3)
    ap.add_argument("--max-wall-s", type=float, default=1200)
    args = ap.parse_args()

    api_key = os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY")
    if not api_key:
        print("XAI_API_KEY missing", file=sys.stderr)
        return 2
    tokens = json.loads(TOKENS.read_text(encoding="utf-8"))
    seats = [s.strip() for s in args.seats.split(",") if s.strip()]
    if getattr(args, 'all_commander', False):
        brains = {s: 'commander' for s in seats}
    else:
        brains = {s: ('commander' if s == 'P3' else 'xai') for s in seats}

    PLAY.mkdir(parents=True, exist_ok=True)
    LOG_MD.write_text(
        f"# Grok live session {now_iso()}\n\n"
        f"- base: `{args.base_url}`\n"
        f"- model: `{XAI_MODEL}`\n"
        f"- brains: {brains}\n\n",
        encoding="utf-8",
    )
    if LOG_JSONL.exists():
        LOG_JSONL.write_text("", encoding="utf-8")

    # fetch rules
    tok0 = tokens[seats[0]]
    with httpx.Client(base_url=args.base_url, headers={"Authorization": f"Bearer {tok0}"}, timeout=60) as c:
        rules = c.get("/harness/v1/rules").json()
    system = rules.get("system_prompt") or "You play TradeWars. Return JSON action."
    system += (
        "\n\nEXTRA: You are a Grok Bot external seat. Always return valid JSON only. "
        "Prefer profitable trades and ship upgrades when safe. Never invent warp targets "
        "outside sector.warps_out / action_hint."
    )

    stop = threading.Event()
    stats: dict[str, Any] = {"by_seat": {}, "ok": 0, "fail": 0, "stale": 0, "xai_calls": 0, "commander_turns": 0}
    threads = []
    for pid in seats:
        t = threading.Thread(
            target=seat_loop,
            args=(args.base_url, pid, tokens[pid], brains[pid], system, api_key, stop, stats),
            daemon=True,
        )
        t.start()
        threads.append(t)

    t0 = time.time()
    append_md(f"- `{now_iso()}` loops started")
    while time.time() - t0 < args.max_wall_s:
        if stats.get("done"):
            break
        if stats.get("commander_turns", 0) >= args.min_commander_turns and (
            args.min_xai_turns <= 0 or stats.get("xai_calls", 0) >= args.min_xai_turns
        ):
            append_md(f"- `{now_iso()}` proof thresholds met — stopping")
            break
        # also accept proof if lots of ok with some xai
        if stats.get("xai_calls", 0) >= args.min_xai_turns and stats.get("ok", 0) >= args.min_xai_turns + 2:
            # commander may have timed out to xai; still ok if we got commander turns separately
            if stats.get("commander_turns", 0) >= args.min_commander_turns or (time.time() - t0) > 600:
                break
        time.sleep(2)

    stop.set()
    for t in threads:
        t.join(timeout=5)
    append_md(f"\n## End `{now_iso()}`\n- stats: `{json.dumps(stats)}`\n")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
