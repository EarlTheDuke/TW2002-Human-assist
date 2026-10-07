"""llm-rules-parity-v1. The mode is on, and legacy reads it as off."""

from __future__ import annotations

import json

import tw2k.engine.constants as K


def test_lp1_mode(monkeypatch):
    assert K.llm_parity_on()
    monkeypatch.setattr(K, "LLM_PARITY_MODE", "legacy")
    assert not K.llm_parity_on()


def test_lp3_parity_drops_the_500k_stardock_corp(monkeypatch):
    from tw2k.agents import prompts
    get_system_prompt = prompts.get_system_prompt
    monkeypatch.setattr(K, "LLM_PARITY_MODE", "legacy")
    legacy = get_system_prompt()
    monkeypatch.setattr(K, "LLM_PARITY_MODE", "tw2002")
    parity = get_system_prompt()
    assert "500k cr at StarDock" in legacy
    assert "500k cr at StarDock" not in parity
    assert "corp_deposit" not in parity.split("Corp:")[1].split("\n", 1)[0]
    assert "C.E.O. ONLY" in parity
    assert '"execute":true' in parity
    monkeypatch.setattr(prompts, "is_minimal", lambda: True)
    minimal = get_system_prompt()
    assert "500k cr at StarDock" not in minimal
    assert "free in any sector" in minimal


def test_lp5_a_rich_solo_hint_does_not_say_500k_at_stardock():
    from tw2k.engine import GameConfig, generate_universe
    from tw2k.engine.models import Player, Ship, ShipClass
    from tw2k.engine.observation import _action_hint
    universe = generate_universe(GameConfig(seed=60, universe_size=40, max_days=2, enable_ferrengi=False))
    player = Player(id="P1", name="P1", sector_id=1, credits=80_000, alignment=100, ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER))
    universe.players["P1"] = player
    hint = _action_hint({"id": 1, "is_stardock": True}, player, [{"id": 1}, {"id": 2}], universe)
    assert "500k" not in hint
    assert "free in any sector" in hint
    assert "<from the invite>" not in hint or "password" in hint


def test_lp8_bank_and_port_verbs_use_the_handler_keys():
    from tw2k.agents.prompts import get_system_prompt
    text = get_system_prompt()
    assert 'bank_transfer {"to_player":"P3","amount":N}' in text
    assert 'port_upgrade {"commodity":"fuel_ore|organics|equipment","units":N}' in text
    assert 'corp_transfer {"target":"P3","item":"credits","qty":N,"direction":"give"}' in text
    assert "Direction is give or take." in text
    assert 'ship_set_password {"password":"..."}' in text
    assert 'alien:<n>' in text
    monkey_off = text  # names stay when the modes are on
    assert "bank_deposit" in monkey_off


def test_lp14_bank_block_hides_when_the_bank_is_legacy(monkeypatch):
    from tw2k.agents.prompts import get_system_prompt
    monkeypatch.setattr(K, "BANK_MODE", "legacy")
    text = get_system_prompt()
    assert "bank_deposit" not in text
    assert "bank_transfer" not in text


def test_lp14_compact_hints_cap_choices_and_skip_secrets(monkeypatch):
    from tw2k.agents.prompts import _compact_legal
    entries = [
        {"kind": "warp", "legal": True, "params": {"target": {"choices": list(range(40))}}},
        {"kind": "corp_join", "legal": True, "params": {
            "ticker": {"choices": ["ABC"]},
            "password": {"type": "str", "choices": ["secret"]},
        }},
        {"kind": "attack", "legal": False, "reason": "no target", "params": {"target": {"choices": ["P9"]}}},
    ]
    out = _compact_legal(entries)
    assert "args" in out
    assert "attack" not in out["args"]
    assert "password" not in out["args"]["corp_join"]
    assert "secret" not in out["args"]["corp_join"]
    assert "+34 more" in out["args"]["warp"]
    monkeypatch.setattr(K, "LLM_PARITY_MODE", "legacy")
    legacy = _compact_legal(entries)
    assert set(legacy) == {"legal", "blocked"}


def test_lp16_required_args_match_the_handlers():
    from tw2k.agents.seat_acceptance import REQUIRED_ARGS
    assert REQUIRED_ARGS["bank_transfer"] == ("to_player", "amount")
    assert REQUIRED_ARGS["port_upgrade"] == ("commodity", "units")
    assert REQUIRED_ARGS["port_build"] == ("planet_id", "port_class")
    assert "direction" in REQUIRED_ARGS["corp_transfer"]
    assert REQUIRED_ARGS["ship_set_password"] == ("password",)


def test_lp7_route_notice_shares_the_plot_syntax():
    import inspect

    from tw2k.agents import llm
    from tw2k.agents.rules_text import plot_course_call, plot_course_line
    assert plot_course_call() in plot_course_line()
    assert "plot_course_call" in inspect.getsource(llm.route_notice)


def _reader_turn(*, here: int, credits: int, legal: list[str], inbox: list | None = None) -> str:
    return json.dumps({
        "sector": {"id": here, "is_stardock": here == 1},
        "self": {"credits": credits, "ship": {"ship_class": "merchant_cruiser"}},
        "legal_actions": {"legal": legal, "blocked": {}},
        "adjacent": [{"id": 2}],
        "inbox": inbox or [],
    })


def test_lp26_legacy_reader_misses_plot_execute_and_the_new_verbs(monkeypatch):
    from tests.llm_text_reader import choose
    from tw2k.agents.prompts import get_system_prompt
    monkeypatch.setattr(K, "LLM_PARITY_MODE", "legacy")
    system = get_system_prompt()
    far = choose(system, _reader_turn(here=40, credits=250_000, legal=["plot_course", "warp"]))
    assert far["action"]["kind"] != "plot_course"
    bank = choose(system, _reader_turn(here=1, credits=300_000, legal=["bank_deposit", "buy_ship"]))
    assert bank["action"]["kind"] != "bank_deposit"
    invited = choose(system, _reader_turn(
        here=5, credits=1000, legal=["corp_join", "warp"],
        inbox=[{"ticker": "ABC", "password": "secret"}],
    ))
    assert invited["action"]["kind"] != "corp_join"


def test_lp26_parity_reader_plots_banks_and_joins():
    from tests.llm_text_reader import choose
    from tw2k.agents.prompts import get_system_prompt
    system = get_system_prompt()
    far = choose(system, _reader_turn(here=40, credits=250_000, legal=["plot_course", "warp"]))
    assert far["action"] == {"kind": "plot_course", "args": {"target": 1, "execute": True}}
    bank = choose(system, _reader_turn(here=1, credits=300_000, legal=["bank_deposit", "trade"]))
    assert bank["action"]["kind"] == "bank_deposit"
    invited = choose(system, _reader_turn(
        here=5, credits=1000, legal=["corp_join", "warp"],
        inbox=[{"ticker": "ABC", "password": "secret"}],
    ))
    assert invited["action"]["args"]["password"] == "secret"


def test_lp27_fixture_lab_checklist():
    import subprocess
    import sys
    from pathlib import Path

    from tests._pin_env import pin_env

    root = Path(__file__).resolve().parents[1]
    env = pin_env()
    env["PYTHONPATH"] = str(root / "src")
    done = subprocess.run(
        [sys.executable, str(root / "scripts" / "llm_prompt_fixture_lab.py")],
        cwd=root, env=env, capture_output=True, text=True, check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert "checklist: PASS" in done.stdout


def test_lp15_flagship_row_stays_member_only_when_bots_are_legacy(monkeypatch):
    from tw2k.agents.prompts import get_system_prompt
    monkeypatch.setattr(K, "CORP_BOTS_MODE", "legacy")
    text = get_system_prompt()
    assert "C.E.O. ONLY" not in text
    assert "CORP MEMBER ONLY" in text
