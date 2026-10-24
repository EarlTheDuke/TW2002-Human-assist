"""TinyBox seats: no land/liftoff ping-pong. Only a local fake endpoint is used."""

from __future__ import annotations

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import tw2k.public.tinybox as TB
from tests.test_lobby_tinybox_seats_v1 import _clean_env, _key, _point  # noqa: F401

_LANDED = {
    "day": 2, "self_id": "P2", "planet_landed": 7,
    "sector": {"id": 5, "warps": [4, 6]},
    "legal_actions": [
        {"kind": "liftoff", "legal": True, "params": {}},
        {"kind": "land_planet", "legal": True, "params": {"planet_id": {"choices": [7]}}},
        {"kind": "warp", "legal": True, "params": {"target": {"choices": [4, 6]}}},
        {"kind": "wait", "legal": True, "params": {}},
    ],
}


class _Script(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        srv = self.server
        body = json.loads(self.rfile.read(int(self.headers.get("content-length") or 0)))
        srv.prompts.append(json.loads(body["messages"][-1]["content"]))  # type: ignore[attr-defined]
        srv.system.append(body["messages"][0]["content"])  # type: ignore[attr-defined]
        kind = srv.script.pop(0) if srv.script else "wait"  # type: ignore[attr-defined]
        args = {"planet_id": 7} if kind == "land_planet" else {}
        raw = json.dumps({"choices": [{"message": {"content": json.dumps({"kind": kind, "args": args})}}]}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *_a) -> None:
        return


@pytest.fixture
def fake(monkeypatch):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Script)
    srv.prompts, srv.system, srv.script = [], [], []  # type: ignore[attr-defined]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    _point(monkeypatch, srv, _key())
    yield srv
    srv.shutdown()
    t.join(2)


def _budget():
    return TB.TinyboxSeatBudget(TB.config(), "qwen3.8:latest", gid="g", seat="P2")


def test_land_then_liftoff_is_refused_once(fake, caplog) -> None:
    fake.script = ["land_planet", "liftoff", "liftoff"]
    b = _budget()
    with caplog.at_level(logging.INFO, logger="tw2k.lobby.tinybox"):
        assert b(fake, _LANDED, None)[0] == "land_planet"
        assert b(fake, _LANDED, None)[0] == "wait"  # immediate reversal: the seat waits
        assert b.reversals == 1 and not b.lasting_fallback
        assert "reversal" in caplog.text
        assert b(fake, _LANDED, None)[0] == "liftoff"  # asked again later: allowed


def test_liftoff_then_land_is_refused_and_other_moves_pass(fake) -> None:
    fake.script = ["liftoff", "land_planet", "warp", "land_planet"]
    b = _budget()
    assert b(fake, _LANDED, None)[0] == "liftoff"
    assert b(fake, _LANDED, None)[0] == "wait"
    assert b(fake, _LANDED, None)[0] == "warp"
    assert b(fake, _LANDED, None)[0] == "land_planet"  # not a reversal after a warp
    assert b.reversals == 1


def test_reversal_in_another_sector_is_allowed() -> None:
    hist = [{"kind": "land_planet", "sector": 5}]
    assert TB.is_reversal(hist, "liftoff", 5)
    assert not TB.is_reversal(hist, "liftoff", 9)
    assert not TB.is_reversal(hist, "warp", 5)
    assert not TB.is_reversal([], "liftoff", 5)


def test_prompt_warns_after_a_bounce(fake) -> None:
    hist = [{"kind": "land_planet", "sector": 5}, {"kind": "liftoff", "sector": 5},
            {"kind": "land_planet", "sector": 5}]
    doc = json.loads(TB.build_prompt(_LANDED, None, hist))
    assert "landing and lifting off" in doc["loop_warning"]
    calm = json.loads(TB.build_prompt(_LANDED, None, [{"kind": "warp"}, {"kind": "land_planet"}]))
    assert "loop_warning" not in calm
    assert "do not land again right after lifting off" in TB.SYSTEM_PROMPT


def test_model_sees_the_refusal_on_the_wire(fake) -> None:
    fake.script = ["land_planet", "liftoff", "wait"]
    b = _budget()
    b(fake, _LANDED, None)
    b(fake, _LANDED, None)  # refused
    b(fake, _LANDED, None)
    last = fake.prompts[-1]["my_last_moves"]
    assert last[-2]["kind"] is None and "refused liftoff" in last[-2]["note"]
    assert last[-1]["kind"] == "wait" and last[-1]["by"] == "seat"
    assert "do not land again" in fake.system[0]


def test_refused_reversal_plays_a_planet_action_when_legal(fake) -> None:
    obs = dict(_LANDED, legal_actions=[*_LANDED["legal_actions"],
        {"kind": "build_citadel", "legal": True, "params": {"planet_id": {"choices": [7]}}}])
    fake.script = ["land_planet", "liftoff"]
    b = _budget()
    b(fake, obs, None)
    assert b(fake, obs, None) == ("build_citadel", {"planet_id": 7}, "refused land/liftoff flip: planet work instead")


def test_unfillable_planet_action_falls_to_wait_and_none() -> None:
    obs = {"legal_actions": [{"kind": "assign_colonists", "legal": True, "params": {"n": {"min": 1}}},
                             {"kind": "wait", "legal": True}]}
    assert TB.substitute_move(obs)[0] == "wait"
    assert TB.substitute_move({"legal_actions": [{"kind": "warp", "legal": True}]}) is None


def test_code_player_moves_are_recorded(fake) -> None:
    fake.script = ["land_planet"]
    b = _budget()
    picked = b(fake, _LANDED, None)
    b.record(_LANDED, picked[0], picked[1])  # model's own move: not duplicated
    assert [h["kind"] for h in b.history] == ["land_planet"]
    b.record(_LANDED, "liftoff", {})  # code player lifted off
    assert b.history[-1] == {"day": 2, "sector": 5, "kind": "liftoff", "args": {}, "by": "code"}
    fake.script = ["land_planet"]
    assert b(fake, _LANDED, None)[0] == "wait"  # re-land after a code liftoff is refused too
