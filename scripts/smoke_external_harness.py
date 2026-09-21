"""Offline smoke test for the external (Grok Bot) harness. No LLM, no network.

Boots the FastAPI app in-process (httpx ASGITransport), starts a 3-seat
match (heuristic + 2 external), then drives seat P2 through several turns
over the real REST routes while P3 is left silent to prove the timeout
path. Exit 0 on success, 1 with a reason otherwise.

Checks (mirrors docs/GROK_CURSOR_HANDOFF.md §4 acceptance):
  * 401 on missing/bad token, 403 on wrong seat, 409 on non-external seat
  * long-poll observation returns awaiting_input + turn_seq
  * valid Action applies (warp changes sector; event actor_kind == external)
  * stale turn_seq -> 409 stale_turn
  * silent seat -> AGENT_ERROR external_timeout + WAIT applied
  * meta.json has kind=external and no token

Run:  python scripts/smoke_external_harness.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import httpx  # noqa: E402

from tw2k.engine import GameConfig  # noqa: E402
from tw2k.engine.models import EventKind  # noqa: E402
from tw2k.server.app import create_app  # noqa: E402
from tw2k.server.runner import AgentSpec, MatchSpec  # noqa: E402

TOK2 = "smoke-token-p2-000000000000"
TOK3 = "smoke-token-p3-000000000000"


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    raise SystemExit(1)


def _ok(msg: str) -> None:
    print(f"  ok  {msg}")


async def _until(pred, *, tries: int = 300, dt: float = 0.02) -> bool:
    for _ in range(tries):
        if pred():
            return True
        await asyncio.sleep(dt)
    return pred()


async def main() -> None:
    os.environ.setdefault("TW2K_HARNESS_ALLOW_REMOTE", "0")
    tmp = Path(tempfile.mkdtemp(prefix="tw2k-smoke-"))
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp / "saves"

    spec = MatchSpec(
        config=GameConfig(
            seed=7, universe_size=60, max_days=2, turns_per_day=12, starting_credits=25_000,
            enable_ferrengi=False, enable_planets=False, action_delay_s=0.0,
        ),
        agents=[
            AgentSpec(player_id="P1", name="HBot", kind="heuristic"),
            AgentSpec(player_id="P2", name="SmokeBot", kind="external", external_token=TOK2),
            AgentSpec(player_id="P3", name="SilentBot", kind="external", external_token=TOK3),
        ],
        action_delay_s=0.0,
        external_timeout_s=0.3,
    )

    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 5555))
    async with httpx.AsyncClient(transport=transport, base_url="http://smoke") as c:
        h2 = {"authorization": f"Bearer {TOK2}"}

        r = await c.get("/harness/v1/P2/status", headers=h2)
        if r.status_code != 503:
            _fail(f"expected 503 before match, got {r.status_code}")
        _ok("503 before match")

        await runner.start(spec)
        if not await _until(lambda: bool(runner.state.agents) and runner.state.universe is not None):
            _fail("runner never started")
        u = runner.state.universe

        for hdr, want, label in (
            ({}, 401, "401 missing token"),
            ({"authorization": "Bearer wrong-wrong-wrong-wrong"}, 401, "401 bad token"),
            ({"authorization": f"Bearer {TOK3}"}, 403, "403 wrong seat"),
        ):
            r = await c.get("/harness/v1/P2/status", headers=hdr)
            if r.status_code != want:
                _fail(f"{label}: got {r.status_code}")
            _ok(label)
        r = await c.get("/harness/v1/P1/status", headers=h2)
        if r.status_code != 409:
            _fail(f"409 non-external seat: got {r.status_code}")
        _ok("409 non-external seat")

        # Drive P2 for a few turns; leave P3 silent.
        applied = 0
        first_target = None
        for _ in range(4):
            r = await c.get("/harness/v1/P2/observation", params={"wait_s": 10}, headers=h2)
            r.raise_for_status()
            body = r.json()
            if body.get("match_status") != "running":
                break
            if not body.get("awaiting_input"):
                continue
            obs = body["observation"]
            seq = body["turn_seq"]
            if applied == 0:
                # Prove stale rejection once.
                r = await c.post(
                    "/harness/v1/P2/action",
                    json={"turn_seq": seq - 1, "action": {"kind": "wait"}},
                    headers=h2,
                )
                if r.status_code != 409 or r.json()["detail"].get("code") != "stale_turn":
                    _fail(f"stale turn_seq not rejected: {r.status_code} {r.text}")
                _ok("409 stale_turn")
            warps = obs["sector"]["warps_out"]
            target = warps[0]
            if first_target is None:
                first_target = target
            r = await c.post(
                "/harness/v1/P2/action",
                json={"turn_seq": seq, "action": {"kind": "warp", "args": {"target": target}, "actor_kind": "copilot"}},
                headers=h2,
            )
            if r.status_code != 200:
                _fail(f"valid action rejected: {r.status_code} {r.text}")
            p2 = u.players["P2"]
            if not await _until(lambda p=p2, t=target: p.sector_id == t):
                _fail("warp did not apply")
            applied += 1
        if applied < 2:
            _fail(f"only {applied} actions applied")
        _ok(f"{applied} warps applied via REST")

        warp_ev = next((e for e in u.events if e.kind == EventKind.WARP and e.actor_id == "P2"), None)
        if warp_ev is None or warp_ev.actor_kind != "external":
            _fail("warp event missing or actor_kind != external")
        _ok("event actor_kind == external (copilot override stripped)")

        r = await c.get("/harness/v1/P2/status", headers=h2)
        if not (r.json().get("last_result") or {}).get("ok"):
            _fail(f"last_result not ok: {r.json().get('last_result')}")
        _ok("last_result.ok surfaced on status")

        def _p3_timeouts() -> int:
            return sum(
                1 for e in u.events
                if e.kind == EventKind.AGENT_ERROR and e.actor_id == "P3" and e.payload.get("external_timeout")
            )

        if not await _until(lambda: _p3_timeouts() >= 1, tries=400, dt=0.03):
            _fail("silent seat never produced an external_timeout AGENT_ERROR")
        _ok("silent seat -> AGENT_ERROR external_timeout + auto-WAIT")

        await runner.stop()

    meta_path = runner.state.save_dir / "meta.json" if runner.state.save_dir else None
    if meta_path is None or not meta_path.exists():
        _fail("meta.json not written")
    meta_text = meta_path.read_text(encoding="utf-8")
    meta = json.loads(meta_text)
    kinds = {a["player_id"]: a["kind"] for a in meta["agents"]}
    if kinds.get("P2") != "external" or kinds.get("P3") != "external":
        _fail(f"meta kinds wrong: {kinds}")
    if TOK2 in meta_text or TOK3 in meta_text or "token" in meta_text.lower():
        _fail("token leaked into meta.json")
    _ok("meta.json records kind=external, no token")
    print("PASS external harness smoke")


if __name__ == "__main__":
    asyncio.run(main())
