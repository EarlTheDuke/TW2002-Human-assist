"""Directive inbox and reliability harness for cockpit players.

No match is started. The inbox is files. The seat tests use a fake harness
client, not a live port.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from ai_cockpit.directives import (  # noqa: E402
    Directive,
    DirectiveError,
    DirectiveHarness,
    RetryableHTTPError,
    clean_seat,
    directive_step,
    drop_file,
    load_active,
    prompt_block,
    redact_text,
    validate_proposal,
    with_reconnect,
)
from ai_cockpit.providers import TurnView, _prompt  # noqa: E402

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
TOKEN = "seat-token-abcdefghijklmnopqrstuvwxyz"


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _obs(**extra) -> dict:
    body = {
        "day": 1,
        "turns_remaining": 20,
        "turns_per_day": 20,
        "credits": 1000,
        "net_worth": 5000,
        "alive": True,
        "sector": {"id": 1, "warps_out": [2]},
        "ship": {"holds": 20, "cargo": {}, "cargo_free": 20, "fighters": 10},
        "legal_actions": [
            {"kind": "warp", "legal": True, "params": {"target": {"choices": [2]}}},
            {"kind": "wait", "legal": True, "params": {}},
            {"kind": "plot_course", "legal": False, "reason": "no course"},
        ],
        "known_ports": [],
        "known_warps": {},
        "adjacent": [],
        "rivals": [],
    }
    body.update(extra)
    return body


def test_directives_module_does_not_import_the_engine() -> None:
    code = (
        "import sys\n"
        f"sys.path.insert(0, {str(REPO / 'scripts')!r})\n"
        "import ai_cockpit.directives\n"
        "names = [n for n in sys.modules if n == 'tw2k' or n.startswith('tw2k.')]\n"
        "print(','.join(names))\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == ""


def test_parse_priority_expiry_and_seat_isolation(tmp_path: Path) -> None:
    _write(
        tmp_path / "P3.json",
        {
            "directives": [
                {"id": "low", "goal": "wander", "priority": 1},
                {
                    "id": "attack",
                    "goal": "scenario test: attack Trader X in sector Y",
                    "target": "Trader X",
                    "sector": "42",
                    "priority": 20,
                    "expires_day": 5,
                },
                {"id": "old", "goal": "already over", "expires": (NOW - timedelta(hours=1)).isoformat()},
            ],
        },
    )
    _write(tmp_path / "P4.json", {"id": "other", "goal": "P4 only", "priority": 100})
    active = load_active(tmp_path, "p3", now=NOW, game_day=5)
    assert [row.id for row in active] == ["attack", "low"]
    assert active[0].sector == 42
    assert active[0].target == "Trader X"
    assert "P4 only" not in prompt_block(active)
    later = load_active(tmp_path, "P3", now=NOW, game_day=6)
    assert [row.id for row in later] == ["low"]
    assert [row.id for row in load_active(tmp_path, "P4", now=NOW)] == ["other"]
    with pytest.raises(DirectiveError):
        clean_seat("../P4")
    with pytest.raises(DirectiveError):
        clean_seat("P3/inbox")


def test_prompt_is_goals_only_and_logs_redact_tokens(tmp_path: Path) -> None:
    rows = [
        Directive(
            goal="finish level 3 citadels and add colonists for quasars", id="citadel-quasars", priority=10
        )
    ]
    text = prompt_block(rows)
    assert "citadel-quasars" in text
    assert "not extra map data" in text
    assert "CHEAT SHEET" not in text
    assert "100,000,000" not in text
    secret = "supersecretvalue-token"
    redacted = redact_text(f"token={secret}&x=1 Bearer abcdefghijklmnop", [secret])
    assert secret not in redacted
    assert "Bearer [redacted]" in redacted
    assert "token=[redacted]" in redacted
    harness = DirectiveHarness("P3", tmp_path, secrets=[TOKEN])
    harness.record(f"prompt {TOKEN}", {"why": TOKEN}, {"error": f"token={TOKEN}"})
    log = (tmp_path / "P3" / "turns.jsonl").read_text(encoding="utf-8")
    assert TOKEN not in log
    assert "[redacted]" in log
    assert not (tmp_path / "P4" / "turns.jsonl").exists()


def test_validate_proposal_uses_only_the_cockpit_envelope() -> None:
    obs = _obs()
    ok, reason = validate_proposal({"kind": "warp", "args": {"target": 9}}, obs)
    assert ok is False and "not a cockpit choice" in reason
    ok, reason = validate_proposal({"kind": "warp", "args": {"target": 2}}, obs)
    assert ok is True and reason == ""
    ok, _reason = validate_proposal({"kind": "teleport", "args": {}}, obs)
    assert ok is False
    trade = _obs(
        legal_actions=[
            {
                "kind": "trade",
                "legal": True,
                "params": {
                    "commodity": {"buy_choices": ["ore"], "sell_choices": []},
                    "qty": {"max_by": {"ore": {"buy": 5}}},
                },
            }
        ]
    )
    ok, reason = validate_proposal(
        {"kind": "trade", "args": {"side": "buy", "commodity": "ore", "qty": 9, "unit_price": 1}},
        trade,
    )
    assert ok is False and "qty" in reason
    ok, _reason = validate_proposal(
        {"kind": "warp", "args": {"target": 2}},
        obs,
        allowed_kinds=frozenset({"wait"}),
    )
    assert ok is False and "not a cockpit action" in _reason


def test_directive_step_attacks_only_a_visible_name_and_warps_only_a_choice() -> None:
    attack = Directive(
        goal="scenario test: attack Trader X in sector Y", target="Trader X", sector=1, id="scenario-attack"
    )
    obs = _obs(
        sector={"id": 1, "warps_out": [2], "occupants": [{"name": "Trader X", "player_id": "P9"}]},
        legal_actions=[
            {"kind": "warp", "legal": True, "params": {"target": {"choices": [2]}}},
            {"kind": "attack", "legal": True, "params": {"target": {"choices": ["P9"]}, "qty": {"max": 4}}},
            {"kind": "wait", "legal": True},
        ],
    )
    step = directive_step(obs, [attack])
    assert step is not None and step["kind"] == "attack" and step["args"]["target"] == "P9"
    missing = Directive(goal="scenario test: attack Trader X in sector Y", target="Trader Z", sector=1)
    assert directive_step(obs, [missing]) is None
    travel = Directive(goal="scenario test: attack Trader X in sector Y", target="Trader X", sector=2)
    moved = directive_step(obs, [travel])
    assert moved is not None and moved["args"]["target"] == 2
    far = Directive(goal="go", sector=99)
    assert directive_step(obs, [far]) is None


def test_directive_step_builds_and_loads_colonists_when_the_form_is_legal() -> None:
    goal = Directive(
        goal="finish level 3 citadels and add colonists for quasars", target="quasar", id="citadel-quasars"
    )
    landed = _obs(
        legal_actions=[
            {"kind": "build_citadel", "legal": True, "params": {"planet_id": {"choices": [7]}}},
            {"kind": "wait", "legal": True},
        ]
    )
    step = directive_step(landed, [goal])
    assert step is not None and step["kind"] == "build_citadel" and step["args"]["planet_id"] == 7
    colonists = _obs(
        legal_actions=[
            {
                "kind": "assign_colonists",
                "legal": True,
                "params": {
                    "planet_id": {"choices": [7]},
                    "from": {"choices": ["ship"]},
                    "to": {"choices": ["fuel_ore", "colonists"]},
                    "qty": {"max_by": {"ship": 12}},
                },
            },
        ]
    )
    step = directive_step(colonists, [goal])
    assert step is not None and step["kind"] == "assign_colonists"
    assert step["args"]["to"] == "colonists" and step["args"]["qty"] == 12


def test_stuck_writes_recovery_then_escalates_without_touching_bens_file(tmp_path: Path) -> None:
    ben = tmp_path / "P3.json"
    _write(
        ben, {"id": "keep", "goal": "finish level 3 citadels and add colonists for quasars", "priority": 10}
    )
    original = ben.read_bytes()
    harness = DirectiveHarness("P3", tmp_path, stuck_after=3)
    fingerprint = (1, 8, 5000, ())
    assert harness.note_fingerprint(fingerprint) == ""
    assert harness.note_fingerprint(fingerprint) == ""
    assert harness.note_fingerprint(fingerprint) == "recover"
    recovery = json.loads((tmp_path / "P3" / "recovery.json").read_text(encoding="utf-8"))
    assert recovery["source"] == "recovery" and recovery["priority"] == 90
    assert ben.read_bytes() == original
    assert harness.note_fingerprint(fingerprint) == ""
    assert harness.note_fingerprint(fingerprint) == ""
    assert harness.note_fingerprint(fingerprint) == "escalate"
    assert (tmp_path / "P3" / "ESCALATE.json").is_file()
    assert harness.escalated is True
    assert harness.note_fingerprint((1, 9, 5000, ())) == "clear"
    assert not (tmp_path / "P3" / "recovery.json").exists()
    assert (tmp_path / "P3" / "ESCALATE.json").is_file()
    top = load_active(tmp_path, "P3", now=NOW)
    assert top[0].id == "keep"


def test_reconnect_retries_a_dropped_status_and_keeps_the_call(tmp_path: Path) -> None:
    calls = {"n": 0}
    beats = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RetryableHTTPError(503, "match not running")
        return {"turn_seq": 4}

    async def beat():
        beats["n"] += 1

    async def _no(_delay: float) -> None:
        return None

    result = asyncio.run(with_reconnect(flaky, heartbeat=beat, sleep=_no))
    assert result == {"turn_seq": 4}
    assert calls["n"] == 3 and beats["n"] == 2

    async def refused():
        raise RetryableHTTPError(409, "stale_turn")

    with pytest.raises(RetryableHTTPError):
        asyncio.run(with_reconnect(refused, sleep=_no))


def test_drop_directive_writes_only_the_named_seat(tmp_path: Path) -> None:
    dest = drop_file(tmp_path, "p3", REPO / "examples" / "directives" / "citadel-quasars.json")
    assert dest.name == "P3.json"
    rows = load_active(tmp_path, "P3", now=NOW)
    assert rows[0].goal == "finish level 3 citadels and add colonists for quasars"
    assert rows[0].target == "quasar"
    assert load_active(tmp_path, "P4", now=NOW) == []
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts" / "drop_directive.py"),
            "--inbox",
            str(tmp_path),
            "--seat",
            "P4",
            "--file",
            str(REPO / "examples" / "directives" / "attack-trader.json"),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    attack = load_active(tmp_path, "P4", now=NOW, game_day=5)
    assert attack[0].sector == 42 and attack[0].id == "scenario-attack"
    assert "Trader X" not in prompt_block(load_active(tmp_path, "P3", now=NOW))


def test_computer_use_prompt_includes_the_directive_and_the_screen() -> None:
    view = TurnView(
        visible_text="Sector 3\nYOUR MOVE",
        labels=["1:4 (3t)"],
        screenshot_png=b"",
        manual_read=True,
        manual_excerpt="",
        step=2,
        directive_text=prompt_block(
            [
                Directive(goal="scenario test: attack Trader X in sector Y", target="Trader X", sector=4),
            ]
        ),
    )
    text = _prompt(view)
    assert "scenario test: attack Trader X in sector Y" in text
    assert "Visible text:" in text and "Sector 3" in text
    assert "CHEAT SHEET" not in text
    bare = TurnView("Sector 3", ["Wait"], b"", True, "", 1)
    assert "Operator directives" not in _prompt(bare)


def test_cockpit_seat_posts_a_legal_directive_warp_and_holds_an_illegal_one(
    tmp_path: Path, monkeypatch
) -> None:
    import tw2k.agents.cockpit_seat as seat
    import tw2k.engine.constants as K

    monkeypatch.setattr(K, "AI_COCKPIT_SEAT_MODE", "tw2002")
    monkeypatch.delenv(seat.LLM_KEY_ENV, raising=False)
    _write(
        tmp_path / "P2.json",
        {
            "id": "scenario-attack",
            "goal": "scenario test: attack Trader X in sector Y",
            "target": "Trader X",
            "sector": 2,
            "priority": 20,
        },
    )
    posts: list[dict] = []
    state = {"posted": False, "obs": 0}

    async def get(path: str, params: dict | None = None) -> dict:
        if path.endswith("/reference"):
            return {"sections": []}
        if path.endswith("/events"):
            return {"events": [], "next_since": 1}
        if path.endswith("/status"):
            return {"awaiting_input": True, "turn_seq": 1, "match_status": "running", "day": 1}
        state["obs"] += 1
        if state["posted"]:
            return {
                "observation": {**_obs(), "finished": True},
                "game_over": True,
                "awaiting_input": False,
                "peek": True,
                "turn_seq": 2,
                "last_result": {"ok": True, "turn_seq": 1},
            }
        if state["obs"] == 1:
            return {"observation": _obs(), "peek": True, "awaiting_input": False, "turn_seq": 1, "day": 1}
        return {"observation": _obs(), "peek": False, "awaiting_input": True, "turn_seq": 1, "day": 1}

    async def post(_path: str, body: dict) -> dict:
        posts.append(body)
        state["posted"] = True
        return {"accepted": True}

    report = asyncio.run(
        seat.CockpitSeat("P2", get, post).run(
            1,
            directives=str(tmp_path),
            idle_s=30,
            redact_secrets=[TOKEN],
        )
    )
    assert posts and posts[0]["action"]["kind"] == "warp"
    assert posts[0]["action"]["args"]["target"] == 2
    assert report["posts"] == 1
    assert (tmp_path / "P2" / "turns.jsonl").is_file()
    assert (tmp_path / "P2" / "heartbeat.json").is_file()

    monkeypatch.setenv(seat.LLM_KEY_ENV, "test-key-not-real")
    _write(
        tmp_path / "P2.json",
        {
            "id": "citadel-quasars",
            "goal": "finish level 3 citadels and add colonists for quasars",
            "target": "quasar",
            "priority": 10,
        },
    )
    seen: list[str] = []
    posts.clear()
    state["posted"] = False
    state["obs"] = 0

    def ask(key: str, _obs: dict, _cockpit, directives: str = "") -> tuple:
        assert key == "test-key-not-real"
        seen.append(directives)
        return ("warp", {"target": 99}, "because " + TOKEN)

    report = asyncio.run(
        seat.CockpitSeat("P2", get, post).run(
            1,
            directives=str(tmp_path),
            idle_s=30,
            llm_ask=ask,
            redact_secrets=[TOKEN],
        )
    )
    assert seen and "citadel-quasars" in seen[0]
    assert posts and posts[0]["action"]["kind"] == "wait"
    assert all(body["action"]["args"].get("target") != 99 for body in posts)
    log = (tmp_path / "P2" / "turns.jsonl").read_text(encoding="utf-8")
    assert TOKEN not in log
    assert report["posts"] == 1


def test_grokbot_seat_does_not_submit_an_illegal_action_and_mailbox_sees_directives(
    tmp_path: Path, monkeypatch
) -> None:
    import tw2k.agents.pathb_client as pathb
    from tw2k.agents.pathb_client import MailboxPolicy, SeatClient, TurnContext

    real_sleep = asyncio.sleep

    async def _no(_delay: float) -> None:
        await real_sleep(0)

    monkeypatch.setattr(pathb.asyncio, "sleep", _no)

    class Resp:
        def __init__(self, code: int, body: dict) -> None:
            self.status_code = code
            self._body = body
            self.headers = {"content-type": "application/json"}
            self.text = json.dumps(body)

        def json(self) -> dict:
            return self._body

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError(str(self.status_code))

    class HTTP:
        def __init__(self) -> None:
            self.posts: list[dict] = []
            self.obs_fails = 0

        async def post(self, _url: str, json: dict | None = None, headers: dict | None = None) -> Resp:
            self.posts.append(json or {})
            return Resp(200, {"accepted": True})

        async def get(self, url: str, params: dict | None = None, headers: dict | None = None) -> Resp:
            if url.endswith("/status"):
                return Resp(
                    200, {"last_result": {"ok": True}, "day": 1, "sector_id": 1, "match_status": "running"}
                )
            self.obs_fails += 1
            if self.obs_fails < 3:
                return Resp(503, {"detail": "match not running"})
            return Resp(
                200,
                {
                    "awaiting_input": True,
                    "turn_seq": 7,
                    "match_status": "running",
                    "server_time": 0,
                    "observation": _obs(),
                },
            )

    _write(tmp_path / "P3.json", {"id": "keep", "goal": "hold the lane", "priority": 5})
    http = HTTP()

    async def policy(_ctx: TurnContext) -> dict:
        return {"kind": "warp", "args": {"target": 99}, "thought": "no"}

    client = SeatClient(http, "P3", TOKEN, policy, directives=str(tmp_path), secrets=[TOKEN])
    obs = _obs()
    first = asyncio.run(client.play_turn({"turn_seq": 3, "observation": obs, "llm_user_message": "cockpit"}))
    assert first is None and http.posts == []
    second = asyncio.run(client.play_turn({"turn_seq": 3, "observation": obs, "llm_user_message": "cockpit"}))
    assert second is not None
    assert http.posts[0]["action"]["kind"] == "wait"
    log = (tmp_path / "P3" / "turns.jsonl").read_text(encoding="utf-8")
    assert TOKEN not in log

    body = asyncio.run(client.wait_for_turn())
    assert body is not None and body["turn_seq"] == 7
    assert http.obs_fails == 3

    pol = MailboxPolicy(tmp_path / "mb", poll_s=0.01, margin_s=0.2)
    ctx = TurnContext(
        seat="P3",
        turn_seq=4,
        observation=obs,
        llm_user_message="{}",
        rules={},
        status={},
        deadline_at=10**12,
        server_skew=0.0,
        directives="goal: finish level 3 citadels",
        directive_list=[
            {"id": "citadel-quasars", "goal": "finish level 3 citadels and add colonists for quasars"}
        ],
    )

    async def brain() -> None:
        pend = pol.pending_path("P3")
        for _ in range(50):
            if pend.exists():
                break
            await asyncio.sleep(0)
        data = json.loads(pend.read_text(encoding="utf-8"))
        assert "finish level 3 citadels" in data["directives"]
        assert data["directive_list"][0]["id"] == "citadel-quasars"
        assert "P4" not in json.dumps(data)
        pol.decision_path("P3").write_text(
            json.dumps({"turn_seq": 4, "action": {"kind": "scan", "args": {}}}),
            encoding="utf-8",
        )

    async def _both():
        return await asyncio.gather(pol(ctx), brain())

    action, _done = asyncio.run(_both())
    assert action["kind"] == "scan"


def test_reexport_reads_the_same_inbox(tmp_path: Path) -> None:
    from tw2k.agents.cockpit_directive import load_active as loaded

    _write(tmp_path / "P5.json", {"goal": "finish level 3 citadels and add colonists for quasars"})
    assert loaded(tmp_path, "P5", now=NOW)[0].goal.startswith("finish level 3")
