"""Galactic Bank and the good-trader tax. docs/playtests/fedspace/GALACTIC_BANK_TAX.md."""

from __future__ import annotations

from tw2k.agents.prompts import get_system_prompt
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe, tick_day
from tw2k.engine import constants as K
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, Ship, ShipClass
from tw2k.engine.victory import full_net_worth


def _world(credits=1_000_000, alignment=0, sector=1):
    u = generate_universe(GameConfig(
        seed=3, universe_size=20, max_days=6, enable_planets=False, enable_ferrengi=False,
    ))
    player = Player(id="A", name="Ada", ship=Ship(), credits=credits, alignment=alignment, experience=0)
    player.sector_id = sector
    u.players["A"] = player
    u.sectors[sector].occupant_ids.append("A")
    return u, player


def _do(u, kind, **args):
    return apply_action(u, "A", Action(kind=kind, args=args))


def test_gb1_only_at_stardock():
    u, _ = _world(sector=12)
    assert not _do(u, ActionKind.BANK_DEPOSIT, amount=10).ok
    u.players["A"].sector_id = 1
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=10).ok


def test_gb4_gb5_cap_is_refused():
    u, player = _world()
    res = _do(u, ActionKind.BANK_DEPOSIT, amount=600_000)
    assert not res.ok and "500,000" in (res.error or "")
    assert player.bank_balance == 0 and player.credits == 1_000_000
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=500_000).ok
    assert player.bank_balance == 500_000
    assert not _do(u, ActionKind.BANK_DEPOSIT, amount=1).ok


def test_gb7_withdraw_and_net_worth_holds():
    u, player = _world()
    before = full_net_worth(u, player)
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=100_000).ok
    assert full_net_worth(u, player) == before
    assert _do(u, ActionKind.BANK_WITHDRAW, amount=40_000).ok
    assert player.bank_balance == 60_000 and player.credits == 940_000
    assert player.turns_today == 0


def test_gb8_transfer_from_cash_and_unknown_id():
    u, player = _world()
    other = Player(id="B", name="Bea", ship=Ship(), credits=0)
    other.sector_id = 4
    u.players["B"] = other
    assert _do(u, ActionKind.BANK_TRANSFER, to_player="Z", amount=50).error == "no such trader"
    assert _do(u, ActionKind.BANK_TRANSFER, to_player="A", amount=50).error == "no such trader"
    assert _do(u, ActionKind.BANK_TRANSFER, to_player="B", amount=50_000).ok
    assert player.credits == 950_000 and other.bank_balance == 50_000


def test_gb17_gb19_tax_table():
    u, player = _world(credits=100_001, alignment=0)
    tick_day(u)
    assert player.credits == 100_001 - 5_000
    assert player.alignment == 1 + 3  # midnight +1, then floor(5000/1500)
    red, who = _world(credits=2_000_000, alignment=-2)  # midnight +1 still leaves them evil
    tick_day(red)
    assert who.credits == 2_000_000


def test_gb13_cash_lost_balance_kept(monkeypatch):
    u, player = _world(credits=300_000)
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=200_000).ok
    killer = Player(id="K", name="Kai", ship=Ship(), credits=0)
    killer.sector_id = 1
    u.players["K"] = killer
    from tw2k.engine.combat import _destroy_ship
    _destroy_ship(u, "A", "attack", killer_id="K", by_other=True)
    assert player.credits == 0 and player.bank_balance == 200_000
    assert killer.credits == 100_000


def test_gb32_prompt_and_legacy(monkeypatch):
    assert "Galactic Bank" in get_system_prompt()
    monkeypatch.setattr(K, "BANK_MODE", "legacy")
    assert "Galactic Bank" not in get_system_prompt()
    u, _ = _world()
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=10).error == "unsupported action"
    assert ActionKind.BANK_DEPOSIT.value not in {row.kind for row in legal_actions(u, "A")}


def test_pod_kill_pays_the_killer_nothing():
    u, player = _world(credits=80_000)
    player.ship.ship_class = ShipClass.ESCAPE_POD
    killer = Player(id="K", name="Kai", ship=Ship(), credits=0)
    u.players["K"] = killer
    from tw2k.engine.combat import _destroy_ship
    _destroy_ship(u, "A", "attack", killer_id="K", by_other=True)
    assert player.credits == 0 and killer.credits == 0


def _other(u, pid="B", *, credits=0, alignment=0, alive=True, sector=4, ticker=None):
    other = Player(id=pid, name=pid, ship=Ship(), credits=credits, alignment=alignment)
    other.alive = alive
    other.sector_id = sector
    other.corp_ticker = ticker
    u.players[pid] = other
    if sector in u.sectors and pid not in u.sectors[sector].occupant_ids:
        u.sectors[sector].occupant_ids.append(pid)
    return other


def test_gb2_personal_account():
    u, player = _world()
    assert not hasattr(u, "bank") or getattr(u, "bank", None) in (None, {})
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=10).ok
    assert player.bank_balance == 10
    dumped = player.model_dump()
    assert dumped["bank_balance"] == 10
    player.bank_balance = 0
    assert "bank_balance" not in player.model_dump()


def test_gb3_deposit_and_gb6_amount():
    u, player = _world()
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=1).ok
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=10_000).ok
    assert player.credits == 1_000_000 - 10_001 and player.bank_balance == 10_001
    assert not _do(u, ActionKind.BANK_DEPOSIT, amount=0).ok
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=True).error == "amount must be a whole number"


def test_gb5_refuse_message_and_variants(monkeypatch):
    u, player = _world(credits=600_000)
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=500_000).ok
    res = _do(u, ActionKind.BANK_DEPOSIT, amount=1)
    assert not res.ok and res.error == "the bank can accept 0 more"
    monkeypatch.setattr(K, "BANK_MAX_BALANCE", 100_000)
    u2, who = _world(credits=200_000)
    refused = _do(u2, ActionKind.BANK_DEPOSIT, amount=100_001)
    assert not refused.ok and "100,000" in (refused.error or "")
    assert _do(u2, ActionKind.BANK_DEPOSIT, amount=100_000).ok
    monkeypatch.setattr(K, "BANK_MAX_BALANCE", 500_000)
    monkeypatch.setattr(K, "BANK_OVERCAP", "clip")
    u3, clip = _world(credits=800_000)
    assert _do(u3, ActionKind.BANK_DEPOSIT, amount=600_000).ok
    assert clip.bank_balance == 500_000 and clip.credits == 300_000
    assert player.bank_balance == 500_000


def test_gb9_recipients(monkeypatch):
    u, player = _world()
    mate = _other(u, "M", ticker="ZZ")
    player.corp_ticker = "ZZ"
    mate.corp_ticker = "ZZ"
    sd = _other(u, "S", sector=1)
    sd.turns_today = sd.turns_per_day
    gone = _other(u, "G")
    gone.alive = False
    assert _do(u, ActionKind.BANK_TRANSFER, to_player="M", amount=1_000).ok
    assert mate.bank_balance == 1_000
    assert _do(u, ActionKind.BANK_TRANSFER, to_player="S", amount=2_000).ok
    assert sd.bank_balance == 2_000
    assert _do(u, ActionKind.BANK_TRANSFER, to_player="G", amount=10).error == "no such trader"
    mate.bank_balance = 500_000
    res = _do(u, ActionKind.BANK_TRANSFER, to_player="M", amount=1)
    assert not res.ok and res.error == "the bank can accept 0 more"
    monkeypatch.setattr(K, "BANK_TRANSFER_SOURCE", "account")
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=4_000).ok
    cash = player.credits
    assert _do(u, ActionKind.BANK_TRANSFER, to_player="S", amount=4_000).ok
    assert player.credits == cash and player.bank_balance == 0 and sd.bank_balance == 6_000


def test_gb10_no_interest():
    u, player = _world(credits=1_000)
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=400).ok
    for _ in range(10):
        tick_day(u)
    assert player.bank_balance == 400


def test_gb11_no_turn_at_the_cap():
    u, player = _world()
    player.turns_today = player.turns_per_day
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=5).ok
    assert _do(u, ActionKind.BANK_WITHDRAW, amount=2).ok
    _other(u, "B")
    assert _do(u, ActionKind.BANK_TRANSFER, to_player="B", amount=1).ok
    assert player.turns_today == player.turns_per_day


def test_gb12_balance_survives_and_guard():
    u, player = _world()
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=50).ok
    player.planet_landed = 1
    assert _do(u, ActionKind.BANK_WITHDRAW, amount=1).error == "lift off first"
    player.planet_landed = None
    player.ship.ship_class = ShipClass.ESCAPE_POD
    assert _do(u, ActionKind.BANK_WITHDRAW, amount=10).ok
    player.alive = False
    assert not _do(u, ActionKind.BANK_DEPOSIT, amount=1).ok
    assert player.bank_balance == 40


def test_gb14_who_receives():
    from tw2k.engine.combat import _destroy_ship
    from tw2k.engine.models import FerrengiShip

    u, player = _world(credits=40_000)
    player.ship.ship_class = ShipClass.MERCHANT_CRUISER
    ferr = FerrengiShip(id="F1", name="F", sector_id=1, aggression=1, fighters=1, shields=1)
    u.ferrengi["F1"] = ferr
    _destroy_ship(u, "A", "attack", killer_id="F1", by_other=True)
    assert player.credits == 0 and ferr.credits == 40_000

    u2, scout = _world(credits=12_000)
    scout.ship.ship_class = ShipClass.SCOUT_MARAUDER
    killer = _other(u2, "K", credits=0, sector=1)
    _destroy_ship(u2, "A", "attack", killer_id="K", by_other=True)
    assert scout.credits == 0 and killer.credits == 0

    u3, sunk = _world(credits=9_000)
    _destroy_ship(u3, "A", "mine", killer_id=None, by_other=False)
    assert sunk.credits == 0
    u4, quit_ = _world(credits=8_000)
    _destroy_ship(u4, "A", "surrender", killer_id=None, by_other=False)
    assert quit_.credits == 0


def test_gb15_capture():
    from tw2k.engine.combat import _destroy_ship
    u, player = _world(credits=15_000)
    killer = _other(u, "K", credits=0, sector=1)
    _destroy_ship(u, "A", "captured", killer_id="K", by_other=True)
    assert player.credits == 0 and killer.credits == 15_000 and player.bank_balance == 0


def test_gb16_death_fog():
    from tw2k.engine.combat import _destroy_ship
    from tw2k.engine.observation import build_observation
    u, player = _world(credits=22_000)
    killer = _other(u, "K", credits=0, sector=1)
    witness = _other(u, "W", sector=1)
    _destroy_ship(u, "A", "attack", killer_id="K", by_other=True)
    victim = build_observation(u, "A").model_dump()
    killer_view = build_observation(u, "K").model_dump()
    witness_view = build_observation(u, "W").model_dump()
    def facts(obs, kind):
        return [e.get("facts") or {} for e in obs["recent_events"] if e.get("kind") == kind]
    assert any("credits_lost" in row for row in facts(victim, "ship_destroyed"))
    assert all("credits_lost" not in row for row in facts(killer_view, "ship_destroyed"))
    assert all("credits_lost" not in row for row in facts(witness_view, "ship_destroyed"))
    assert any(e.get("kind") == "credits_recovered" for e in killer_view["recent_events"])
    assert not any(e.get("kind") == "credits_recovered" for e in witness_view["recent_events"])
    assert player.credits == 0 and killer.credits == 22_000


def test_gb18_and_gb21_and_gb22(monkeypatch):
    from tw2k.engine.bank import tax_on
    u, player = _world(credits=100_000, alignment=0)
    tick_day(u)
    assert player.credits == 100_000 and player.experience == 1  # midnight +1 exp, no tax exp
    who = Player(id="Z", name="Z", ship=Ship(), credits=100_001, alignment=-1)
    assert tax_on(who) == (0, 0)
    who.alignment = 0
    assert tax_on(who) == (5_000, 3)
    monkeypatch.setattr(K, "TAX_RATE_PCT", 10)
    assert tax_on(who)[0] == 10_000
    monkeypatch.setattr(K, "TAX_RATE_PCT", 5)
    monkeypatch.setattr(K, "TAX_THRESHOLD", 49_999)
    assert tax_on(Player(id="Z", name="Z", ship=Ship(), credits=50_000, alignment=0))[0] == 2_500
    monkeypatch.setattr(K, "TAX_MIN_ALIGNMENT", 1)
    assert tax_on(Player(id="Z", name="Z", ship=Ship(), credits=200_000, alignment=0)) == (0, 0)
    monkeypatch.setattr(K, "TAX_MIN_ALIGNMENT", 0)
    monkeypatch.setattr(K, "TAX_THRESHOLD", 100_000)
    rich = Player(id="Z", name="Z", ship=Ship(), credits=965_000_000, alignment=0)
    tax, award = tax_on(rich)
    assert tax == 965_000_000 * 5 // 100 and award == 0
    monkeypatch.setattr(K, "TAX_ALIGN_OVERFLOW", "clamp")
    assert tax_on(rich)[1] == 31_999


def test_gb20_cash_only():
    from tw2k.engine.models import Planet, PlanetClass
    u, player = _world(credits=200_000, alignment=0)
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=80_000).ok
    planet = Planet(id=1, sector_id=3, name="Nest", class_id=PlanetClass.M, owner_id="A", treasury=7_777)
    u.planets[1] = planet
    tick_day(u)
    assert player.bank_balance == 80_000 and planet.treasury == 7_777
    assert player.credits == 120_000 - (120_000 * 5 // 100)


def test_gb23_tax_is_last_and_gb24_sinks():
    u, player = _world(credits=200_000, alignment=0)
    before = player.credits
    tick_day(u)
    kinds = [e.kind.value for e in u.events]
    assert kinds.index("day_tick") < kinds.index("tax_collected")
    assert player.credits == before - (before * 5 // 100)
    assert sum(p.credits for p in u.players.values()) == player.credits


def test_gb25_and_gb28_fog():
    from tw2k.engine.observation import build_observation
    u, _player = _world(credits=200_000, alignment=0)
    witness = _other(u, "W", sector=1)
    tick_day(u)
    own = build_observation(u, "A").model_dump()
    other = build_observation(u, "W").model_dump()
    assert any(e.get("kind") == "tax_collected" for e in own["recent_events"])
    assert not any(e.get("kind") == "tax_collected" for e in other["recent_events"])
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=1_000).ok
    other = build_observation(u, "W").model_dump()
    assert not any(e.get("kind") == "bank_deposit" for e in other["recent_events"])
    assert all("bank_balance" not in r for r in other.get("rivals") or [])
    assert witness.bank_balance == 0


def test_gb26_economic_victory_uses_cash():
    from tw2k.engine.victory import check_victory
    u, player = _world(credits=400_000)
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=100_000).ok
    threshold = max(500_000, int(K.VICTORY_CREDITS_THRESHOLD * (u.config.max_days / K.VICTORY_DEFAULT_MAX_DAYS)))
    player.credits = threshold - 1
    check_victory(u)
    assert not u.finished
    player.credits = threshold
    check_victory(u)
    assert u.finished and u.win_reason == "economic"


def test_gb27_own_view():
    from tw2k.engine.observation import build_observation
    u, _player = _world(credits=200_000, alignment=0)
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=40_000).ok
    obs = build_observation(u, "A")
    assert obs.bank_balance == 40_000
    assert obs.bank_room == 500_000 - 40_000
    assert obs.tax_due_tomorrow == 160_000 * 5 // 100


def test_bank_verbs_match_handlers_and_rng():
    from tw2k.engine.bank import deposit_legal_spec, transfer_legal_spec, withdraw_legal_spec
    u, player = _world()
    _other(u, "B")
    state = u.rng.getstate()
    for amount in (1, 10_000, 500_000, 500_001):
        ok, _why, _turns, _params = deposit_legal_spec(u, "A")
        res = _do(u, ActionKind.BANK_DEPOSIT, amount=amount)
        assert res.ok == (ok and amount <= _params["max_amount"] and amount >= 1)
    assert _do(u, ActionKind.BANK_WITHDRAW, amount=1).ok == (withdraw_legal_spec(u, "A")[0] or player.bank_balance >= 1)
    ok, _why, _turns, params = transfer_legal_spec(u, "A")
    res = _do(u, ActionKind.BANK_TRANSFER, to_player="B", amount=1)
    assert res.ok == ok and params["recipients"]
    assert u.rng.getstate() == state


def test_gb13_kept_variant_and_legacy_death(monkeypatch):
    from tw2k.engine.combat import _destroy_ship
    u, player = _world(credits=80_000)
    monkeypatch.setattr(K, "DEATH_CREDITS_ON_HAND", "kept")
    killer = _other(u, "K", credits=0, sector=1)
    _destroy_ship(u, "A", "attack", killer_id="K", by_other=True)
    assert player.credits == 80_000 and killer.credits == 0
    u2, who = _world(credits=80_000)
    monkeypatch.setattr(K, "DEATH_MODE", "legacy")
    _destroy_ship(u2, "A", "attack", killer_id="K", by_other=True)
    assert who.credits == int(80_000 * 0.75)


def test_gb29_gb31_bot(monkeypatch):
    from tw2k.agents.seat_acceptance import synthetic_obs
    from tw2k.agents.seat_brain import SeatBrain
    from tw2k.engine import constants as engine_k

    def _la(obs, kind, legal=True, **params):
        obs["legal_actions"] = [row for row in obs["legal_actions"] if row["kind"] != kind]
        obs["legal_actions"].append({"kind": kind, "legal": legal, "reason": None, "detail": "precise", "params": params})
        return obs

    monkeypatch.setattr(engine_k, "BOT_BANK_POLICY", "tax_and_death")
    brain = SeatBrain()
    obs = synthetic_obs(sector=1, credits=80_000, ship_class="cargotran")
    obs["bank_balance"] = 0
    _la(obs, "buy_equip", item={"choices": [], "unit_price_by": {}})
    _la(obs, "bank_deposit", max_amount=80_000, balance=0, room=500_000)
    _la(obs, "bank_transfer", max_amount=80_000, recipients=[{"player_id": "P2", "name": "Bea", "room": 500_000}])
    first = brain.decide(obs)
    assert first["kind"] == "bank_deposit"
    assert first["args"]["amount"] == 80_000 - int(engine_k.BOT_BANK_FLOAT)
    assert first["kind"] != "bank_transfer"
    second = brain.decide(obs)
    assert second["kind"] != "bank_deposit"

    pod = synthetic_obs(sector=1, credits=0, ship_class="escape_pod", holds=5)
    pod["bank_balance"] = 20_000
    _la(pod, "buy_ship", ship_class={"choices": ["cargotran", "scout_marauder"],
                                    "net_cost_by": {"cargotran": 100_000, "scout_marauder": 5_000}})
    _la(pod, "bank_withdraw", max_amount=20_000, balance=20_000)
    withdrawn = SeatBrain().decide(pod)
    assert withdrawn["kind"] == "bank_withdraw" and withdrawn["args"]["amount"] == 5_000

    short = synthetic_obs(sector=1, credits=10_000, ship_class="merchant_cruiser")
    short["bank_balance"] = 100_000
    _la(short, "buy_ship", ship_class={"choices": ["cargotran"], "net_cost_by": {"cargotran": 40_000}})
    _la(short, "bank_withdraw", max_amount=100_000, balance=100_000)
    hull = SeatBrain().decide(short)
    assert hull["kind"] == "bank_withdraw" and hull["args"]["amount"] == 40_000 + 2_000 - 10_000

    away = synthetic_obs(sector=5, credits=200_000, ship_class="cargotran")
    away["bank_balance"] = 0
    _la(away, "bank_deposit", max_amount=200_000)
    assert SeatBrain().decide(away)["kind"] != "bank_deposit"

    monkeypatch.setattr(engine_k, "BOT_BANK_POLICY", "off")
    assert SeatBrain().decide(obs)["kind"] != "bank_deposit"


def test_bank_balance_survives_save_and_load():
    from tw2k.engine.models import Universe
    u, player = _world(credits=200_000, alignment=0)
    assert _do(u, ActionKind.BANK_DEPOSIT, amount=40_000).ok
    tick_day(u)
    back = Universe.model_validate_json(u.model_dump_json())
    assert back.players["A"].bank_balance == 40_000
    assert back.players["A"].credits == player.credits
    assert back.model_dump_json() == u.model_dump_json()
