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
        "self": {"credits": credits, "turns_remaining": 100, "ship": {"ship_class": "merchant_cruiser"}},
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


def test_pb1_minimal_prompt_drops_the_500k_line(monkeypatch):
    from tw2k.agents import prompts
    monkeypatch.setattr(prompts, "is_minimal", lambda: True)
    text = prompts.get_system_prompt()
    assert "500k cr at StarDock" not in text


def test_pb2_treasury_off_drops_deposit_and_withdraw():
    from tw2k.agents.prompts import get_system_prompt
    text = get_system_prompt()
    assert "corp_deposit" not in text
    assert "corp_withdraw" not in text
    assert "shared treasury" not in text


def test_pb3_and_pb4_invite_hint_names_the_password_key_and_not_the_secret():
    from tw2k.engine import GameConfig, generate_universe
    from tw2k.engine.models import Player, Ship, ShipClass
    from tw2k.engine.observation import _action_hint
    universe = generate_universe(GameConfig(seed=61, universe_size=20, max_days=2, enable_ferrengi=False))
    player = Player(
        id="P2", name="P2", sector_id=1, credits=1000, alignment=0,
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER),
        inbox=[{"kind": "corp_invite", "ticker": "ABC", "password": "secret1"}],
    )
    universe.players["P2"] = player
    hint = _action_hint({"id": 1, "is_stardock": True}, player, [], universe)
    assert '"password":"<from the invite>"' in hint
    assert "secret1" not in hint


def test_pb5_hint_a_stays_quiet_below_the_credit_threshold():
    from tw2k.engine import GameConfig, generate_universe
    from tw2k.engine.models import Player, Ship, ShipClass
    from tw2k.engine.observation import _action_hint
    universe = generate_universe(GameConfig(seed=62, universe_size=20, max_days=2, enable_ferrengi=False))
    player = Player(
        id="P1", name="P1", sector_id=1, credits=0, alignment=0,
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER),
    )
    universe.players["P1"] = player
    hint = _action_hint({"id": 1, "is_stardock": True}, player, [], universe)
    assert "the hint waits until" not in hint


def test_pb6_plot_course_line_includes_execute():
    from tw2k.agents.prompts import get_system_prompt
    assert '"execute":true' in get_system_prompt()


def test_pb9_pb10_pb11_examples_use_the_handler_names():
    from tw2k.agents.prompts import get_system_prompt
    text = get_system_prompt()
    assert '"to_player":"P3"' in text
    assert '"units":N' in text
    assert "give or take" in text
    assert "send/receive" not in text


def test_pb12_and_pb13_numbers_follow_the_constants(monkeypatch):
    from tw2k.agents.prompts import get_system_prompt
    from tw2k.agents.rules_text import bank_block
    monkeypatch.setattr(K, "TAX_THRESHOLD", 123456)
    assert "123,456" in bank_block()
    monkeypatch.setattr(K, "PORT_UPGRADE_HOLDS_PER_UNIT", 17)
    assert "adds 17 holds" in get_system_prompt()


def test_pb20_a_transfer_without_direction_is_rejected():
    from tw2k.agents.seat_acceptance import validate_action
    obs = {"legal_actions": [{"kind": "corp_transfer", "legal": True, "params": {}}]}
    errors = validate_action(obs, {"kind": "corp_transfer", "args": {
        "target": "P2", "item": "credits", "qty": 1,
    }})
    assert any("direction" in error for error in errors)


def _seat(**kwargs):
    from types import SimpleNamespace
    base = dict(
        finished=False, turns_remaining=40, credits=207_000, day=3, max_days=8,
        owned_planets=[], goals={"short": "go reload at A", "medium": "", "long": "Reach ~500k then a home"},
        ship={"cargo": {}, "cargo_cost_avg": {}, "genesis": 0, "class": "merchant_cruiser"},
        sector={"id": 1, "port": {"stock": {}}},
        alive=True, deaths=0, max_deaths=3, alignment=0, corp_ticker=None, net_worth=207_000,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_sell_first_notice_when_the_bid_covers_the_cost():
    from tw2k.agents.llm import sell_first_notice
    obs = _seat(ship={
        "cargo": {"fuel_ore": 40}, "cargo_cost_avg": {"fuel_ore": 34}, "genesis": 0,
    }, sector={"id": 301, "port": {"stock": {"fuel_ore": {"side": "buys_from_player", "price": 36}}}})
    text = sell_first_notice(obs)
    assert text.startswith("SELL HERE:")
    assert "overrides your short goal" in text


def test_sell_first_stays_quiet_below_cost_or_without_cargo():
    from tw2k.agents.llm import sell_first_notice
    cheap = _seat(ship={
        "cargo": {"fuel_ore": 40}, "cargo_cost_avg": {"fuel_ore": 40}, "genesis": 0,
    }, sector={"id": 301, "port": {"stock": {"fuel_ore": {"side": "buys_from_player", "price": 36}}}})
    empty = _seat()
    assert sell_first_notice(cheap) == ""
    assert sell_first_notice(empty) == ""


def test_cargo_loop_notice_after_two_round_trips():
    from tw2k.agents.llm import cargo_loop_notice
    obs = _seat(ship={"cargo": {"fuel_ore": 40}, "cargo_cost_avg": {"fuel_ore": 34}, "genesis": 0},
                sector={"id": 408})
    trail = [(3, 408, "warp"), (3, 301, "warp"), (3, 408, "warp"), (3, 301, "warp")]
    assert cargo_loop_notice(obs, trail) == "you are looping: sell here or plot_course to a buyer"
    assert cargo_loop_notice(obs, trail[:2]) == ""
    traded = [(3, 408, "warp"), (3, 301, "trade"), (3, 408, "warp"), (3, 301, "warp")]
    assert cargo_loop_notice(obs, traded) == ""
    assert cargo_loop_notice(_seat(sector={"id": 408}), trail) == ""


def test_planet_nudge_on_a_rich_seat_with_no_planet():
    from tw2k.agents.llm import planet_notice
    from tw2k.agents.prompts import get_system_prompt, stage_hint
    obs = _seat()
    text = planet_notice(obs)
    assert "genesis" in text
    assert "terra_colonists" in text
    assert "Do not wait for a credit target" in text
    hint = stage_hint(obs)
    assert hint["stage"] == "S2"
    assert "genesis" in hint["next_milestone"]
    assert "Do not wait for a credit target" in hint["next_milestone"]
    owner = _seat(owned_planets=[{"id": 1, "citadel_level": 0}])
    assert planet_notice(owner) == ""
    assert "update only on real strategy shifts" not in get_system_prompt()


def test_planet_nudge_legacy_keeps_the_old_prompt_and_stays_quiet(monkeypatch):
    from tw2k.agents.llm import planet_notice
    from tw2k.agents.prompts import get_system_prompt, stage_hint
    monkeypatch.setattr(K, "LLM_PLANET_NUDGE_MODE", "legacy")
    assert "update only on real strategy shifts" in get_system_prompt()
    obs = _seat()
    assert planet_notice(obs) == ""
    assert "500k" in stage_hint(obs)["next_milestone"]


def test_buy_equip_lists_every_affordable_item_when_the_nudge_is_on():
    from tw2k.agents.prompts import _compact_legal
    choices = [f"item{n}" for n in range(8)]
    out = _compact_legal([{
        "kind": "buy_equip", "legal": True,
        "params": {"item": {"choices": choices}},
    }])
    assert out["args"]["buy_equip"] == "item=" + ",".join(choices)


def test_pb22_alien_attack_format_matches_the_engine():
    from pathlib import Path

    from tw2k.agents.prompts import get_system_prompt
    engine = Path("src/tw2k/engine/alien.py").read_text(encoding="utf-8")
    assert 'f"alien:{n}"' in engine
    assert "alien:<n>" in get_system_prompt()


def test_pb23_parity_prompt_does_not_repeat_a_long_sentence():
    from tw2k.agents.prompts import get_system_prompt
    text = get_system_prompt().replace("\n", " ")
    sentences = [part.strip() for part in text.split(".") if len(part.strip()) > 60]
    assert len(sentences) == len(set(sentences))


def test_pb24_a_rival_planet_stock_stays_out_of_the_hint():
    from tw2k.agents.prompts import format_observation, get_system_prompt
    from tw2k.engine import GameConfig, generate_universe
    from tw2k.engine.models import Commodity, Player, Ship, ShipClass
    from tw2k.engine.observation import build_observation
    universe = generate_universe(GameConfig(seed=60, universe_size=40, enable_ferrengi=False, enable_planets=True))
    planet = next(iter(universe.planets.values()))
    planet.owner_id = "B"
    planet.stockpile[Commodity.EQUIPMENT] = 424242
    sector = universe.sectors[planet.sector_id]
    universe.players["A"] = Player(
        id="A", name="A", sector_id=planet.sector_id, credits=20_000,
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER),
    )
    universe.players["B"] = Player(
        id="B", name="B", sector_id=planet.sector_id, credits=20_000,
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER),
    )
    sector.occupant_ids.extend(["A", "B"])
    rendered = format_observation(build_observation(universe, "A"))
    assert "424242" not in rendered
    assert "424242" not in get_system_prompt()


def test_pb25_the_legacy_pin_turns_the_route_notice_off():
    from pathlib import Path
    text = Path("tests/test_llm_parity_legacy_pin.py").read_text(encoding="utf-8")
    assert "K.LLM_ROUTE_NOTICE = False" in text
    assert "K.LLM_NEW_DAY_GOAL_NOTICE = False" in text


def test_pb26_prompt_growth_stays_inside_the_budget(monkeypatch):
    from tw2k.agents.prompts import get_system_prompt
    monkeypatch.setattr(K, "LLM_PARITY_MODE", "legacy")
    monkeypatch.setattr(K, "LLM_PLANET_NUDGE_MODE", "legacy")
    legacy = len(get_system_prompt())
    monkeypatch.setattr(K, "LLM_PARITY_MODE", "tw2002")
    monkeypatch.setattr(K, "LLM_PLANET_NUDGE_MODE", "tw2002")
    parity = len(get_system_prompt())
    growth = 100.0 * (parity - legacy) / legacy
    assert growth <= float(K.LLM_PROMPT_GROWTH_MAX_PCT), growth


def test_pb21_the_brain_transfer_shape_passes_acceptance():
    from tw2k.agents.seat_acceptance import validate_action
    obs = {"legal_actions": [{"kind": "corp_transfer", "legal": True, "params": {
        "item": {"choices": ["credits", "fighters"]},
        "direction": {"choices": ["give", "take"]},
    }}]}
    for args in (
        {"target": "P2", "item": "fighters", "qty": 10, "direction": "take"},
        {"target": "P2", "item": "credits", "qty": 1000, "direction": "give"},
    ):
        assert validate_action(obs, {"kind": "corp_transfer", "args": args}) == []
