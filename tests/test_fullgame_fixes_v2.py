"""fullgame-fixes-v2: planet-dividend transfer exploit, N3 hunting, neutral LLM combat framing.

See docs/playtests/fullgame/FULLGAME_FIXES_V2.md.
"""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tests._pin_env import pin_env
from tw2k.engine import Action, ActionKind, GameConfig, generate_universe
from tw2k.engine.models import Commodity, Planet, PlanetClass, Player, Ship, ShipClass
from tw2k.engine.runner import apply_action, planet_tax_value, tick_day


@pytest.fixture
def tw(monkeypatch):
    monkeypatch.setattr(K, "PLANET_DIVIDEND_MODE", "tw2002")


def _world(*, credits: int = 100_000, fighters: int = 5_000, sector: int = 120):
    u = generate_universe(GameConfig(seed=250925, universe_size=1000, enable_ferrengi=False, enable_planets=True))
    u.players["A"] = Player(id="A", name="Pumper", credits=credits, sector_id=sector,
                            ship=Ship(ship_class=ShipClass.BATTLESHIP, holds=80, fighters=fighters, shields=0))
    u.sectors[sector].occupant_ids.append("A")
    pl = Planet(id=901, sector_id=sector, name="Bank", class_id=PlanetClass.M, owner_id="A", citadel_level=1)
    u.planets[pl.id] = pl
    u.sectors[sector].planet_ids.append(pl.id)
    pl.last_tax_value = planet_tax_value(pl)
    u.players["A"].planet_landed = pl.id
    return u, pl


def _act(u, verb, **args):
    p = u.players["A"]
    p.turns_today = 0
    r = apply_action(u, "A", Action(kind=verb, args={"planet_id": 901, **args}))
    assert r.ok, r.error
    return r


def _pump(u, cycles: int = 3) -> int:
    """Deposit 5000 fighters, take the dividend, withdraw, repeat. Returns credits gained."""
    p = u.players["A"]
    start = p.credits
    for _ in range(cycles):
        _act(u, ActionKind.DEPOSIT_PLANET_DEFENSE, kind="fighters", qty=5_000)
        tick_day(u)
        _act(u, ActionKind.WITHDRAW_PLANET_DEFENSE, kind="fighters", qty=5_000)
        tick_day(u)
    return p.credits - start


def test_fighter_deposit_pump_pays_nothing_in_tw2002(tw):
    u, pl = _world()
    assert _pump(u) == 0
    assert u.players["A"].ship.fighters == 5_000


def test_legacy_still_pays_the_pump(monkeypatch):
    """Legacy keeps the old (byte-identical) behaviour: 5000 fighters x 50 x 30% = 75,000 per deposit."""
    monkeypatch.setattr(K, "PLANET_DIVIDEND_MODE", "legacy")
    u, pl = _world()
    assert _pump(u, cycles=2) == 2 * int(5_000 * K.FIGHTER_COST * K.PLANET_VALUE_TAX_RATE)


def test_treasury_and_cargo_transfers_are_neutral(tw):
    u, pl = _world(credits=500_000, fighters=0)
    p = u.players["A"]
    p.ship.cargo[Commodity.EQUIPMENT] = 50
    _act(u, ActionKind.DEPOSIT_TREASURY, amount=200_000)
    _act(u, ActionKind.DUMP_PLANET_CARGO, commodity="equipment", qty=50)
    tick_day(u)
    paid = sum(e.payload["payout"] for e in u.events if e.kind.value == "planet_tax_payout")
    # Only one day of treasury interest is real growth; the 200k deposit and the 50 equipment are not.
    interest = 200_000 * K.PLANET_TREASURY_INTEREST_PCT // 100
    assert paid <= int(interest * K.PLANET_VALUE_TAX_RATE) + 1


def test_production_still_pays_after_a_withdrawal(tw):
    """A same-day withdrawal does not swallow real growth (baseline may go below 0)."""
    u, pl = _world(fighters=0)
    pl.fighters = 1_000
    pl.colonists[Commodity.FUEL_ORE] = 3_000
    pl.last_tax_value = planet_tax_value(pl)
    _act(u, ActionKind.WITHDRAW_PLANET_DEFENSE, kind="fighters", qty=1_000)
    p = u.players["A"]
    before, v0 = p.credits, planet_tax_value(pl)
    tick_day(u)
    assert pl.fighters > 0  # production happened
    growth = planet_tax_value(pl) - v0
    assert growth >= pl.fighters * K.FIGHTER_COST
    assert p.credits - before == int(growth * K.PLANET_VALUE_TAX_RATE)


# ---- N3 hunting (HUNT_MODE) ---------------------------------------------------------------------------

from tw2k.agents.seat_brain import SeatBrain  # noqa: E402
from tw2k.engine.models import FerrengiShip  # noqa: E402
from tw2k.engine.observation import build_observation  # noqa: E402

DEEP = 500  # outside FedSpace (sectors 1-10)


@pytest.fixture
def hunt(monkeypatch):
    for name in ("HUNT_MODE", "COMBAT_FRAMING_MODE", "SLOW_HULL_HINT_MODE"):
        monkeypatch.setattr(K, name, "tw2002")


def _arena(*, fighters: int = 2_000, ship_class=ShipClass.BATTLESHIP, alignment: int = 200):
    u = generate_universe(GameConfig(seed=250925, universe_size=1000, enable_ferrengi=False, enable_planets=True))
    u.ferrengi.clear()
    p = Player(id="H", name="Hunter", credits=50_000, sector_id=DEEP, alignment=alignment, experience=500,
               ship=Ship(ship_class=ship_class, holds=80, fighters=fighters, shields=0))
    u.players["H"] = p
    u.sectors[DEEP].occupant_ids.append("H")
    p.known_sectors.add(DEEP)
    return u


def _ferr(u, *, fighters=300, shields=50, hull="assault_trader", aggression=2, fid="ferr_1"):
    u.ferrengi[fid] = FerrengiShip(id=fid, name="Grabnik", sector_id=DEEP, aggression=aggression,
                                   fighters=fighters, shields=shields, hull=hull)


def _trader(u, *, fighters=50, ship_class=ShipClass.SCOUT_MARAUDER, alignment=10, tid="V"):
    u.players[tid] = Player(id=tid, name="Victim", credits=1_000, sector_id=DEEP, alignment=alignment,
                            ship=Ship(ship_class=ship_class, holds=20, fighters=fighters, shields=0))
    u.sectors[DEEP].occupant_ids.append(tid)


def _decide(u, brain=None):
    brain = brain or SeatBrain()
    return brain.decide(build_observation(u, "H").model_dump(mode="json"))


def test_n3_attacks_a_ferrengi_it_clearly_outguns(hunt):
    u = _arena()
    _ferr(u)
    act = _decide(u)
    assert act["kind"] == "attack" and act["args"]["target"] == "ferr_1", act
    assert "bounty 2000" in act["thought"]


def test_n3_leaves_a_ferrengi_it_does_not_beat_by_the_margin(hunt):
    u = _arena(fighters=2_000)  # battleship power 2000 x 1.6 = 3200
    _ferr(u, fighters=1_500, shields=200, hull="assault_trader")  # defence 1700: beatable, not 2x
    assert _decide(u)["kind"] != "attack"


def test_n1_n2_and_legacy_never_hunt(hunt, monkeypatch):
    u = _arena()
    _ferr(u)
    assert _decide(u, SeatBrain(value_allocator=False))["kind"] != "attack"  # the N1/N2 ladders
    monkeypatch.setattr(K, "HUNT_MODE", "legacy")
    assert _decide(u)["kind"] != "attack"


def test_n3_hunts_a_weak_trader_assuming_max_shields(hunt):
    u = _arena(alignment=200)
    _trader(u, fighters=50)  # scout: max shields assumed, still far below half the hunter's power
    act = _decide(u)
    assert act["kind"] == "attack" and act["args"]["target"] == "V", act
    assert "scanned defence" in act["thought"]  # a BattleShip's Combat Scanner reads the shields


def test_hidden_shields_count_at_the_hull_max(hunt):
    u = _arena(fighters=300, ship_class=ShipClass.MERCHANT_CRUISER, alignment=500)
    _trader(u, fighters=0, ship_class=ShipClass.BATTLESHIP)  # 0 fighters seen, but up to max shields
    assert _decide(u)["kind"] != "attack"


def test_n3_will_not_hunt_itself_evil(hunt):
    u = _arena(alignment=20)  # a good victim costs ~half of (20 + 50): would end below 0
    _trader(u, alignment=300)
    assert _decide(u)["kind"] != "attack"
    u2 = _arena(alignment=20)
    _trader(u2, alignment=-300)  # an evil target costs nothing (and moves the hunter toward good)
    assert _decide(u2)["kind"] == "attack"


def test_no_hunting_of_pods_or_in_fedspace(hunt):
    u = _arena()
    _trader(u, ship_class=ShipClass.ESCAPE_POD, fighters=0)
    assert _decide(u)["kind"] != "attack"
    u2 = _arena()
    _ferr(u2)
    u2.ferrengi["ferr_1"].sector_id = 3
    u2.sectors[DEEP].occupant_ids.remove("H")
    u2.players["H"].sector_id = 3
    u2.sectors[3].occupant_ids.append("H")
    assert _decide(u2)["kind"] != "attack"


def test_a_hunt_kill_pays_xp_and_destroys_the_ship(hunt):
    u = _arena()
    _ferr(u, aggression=3)
    p = u.players["H"]
    credits, xp = p.credits, p.experience
    act = _decide(u)
    r = apply_action(u, "H", Action(kind=ActionKind.ATTACK, args=act["args"]))
    assert r.ok, r.error
    assert not u.ferrengi["ferr_1"].alive
    assert p.credits >= credits + 3 * K.FERRENGI_BOUNTY_PER_AGG and p.experience > xp


# ---- LLM framing (COMBAT_FRAMING_MODE, SLOW_HULL_HINT_MODE) -------------------------------------------

from tw2k.agents.prompts import get_system_prompt  # noqa: E402


def test_prompt_presents_combat_with_rewards_and_costs(hunt):
    text = get_system_prompt()
    assert "High-aggression will wreck you" not in text
    assert "a fair target outside FedSpace" in text and "bounty" in text
    assert "Attacking a trader" in text and "alignment" in text
    assert "SITUATIONAL" not in text and "legitimate paths" in text
    assert "combat hull, slow for trading" in text


def test_legacy_framing_keeps_the_old_text(monkeypatch):
    for name in ("COMBAT_FRAMING_MODE", "SLOW_HULL_HINT_MODE"):
        monkeypatch.setattr(K, name, "legacy")
    text = get_system_prompt()
    assert "High-aggression will wreck you" in text and "SITUATIONAL" in text
    assert "slow for trading" not in text


def test_hint_shows_the_ferrengi_win_check(hunt):
    u = _arena()
    _ferr(u)
    hint = build_observation(u, "H").action_hint
    assert "kill = 2,000 cr bounty" in hint and "you destroy it in one attack" in hint
    assert "Surrender often safer" not in hint


def test_hint_shows_a_trader_check(hunt):
    u = _arena()  # a BattleShip reads the shields
    _trader(u)
    hint = build_observation(u, "H").action_hint
    assert "Traders here: Victim" in hint and "0 shields (combat scanner)" in hint
    assert "you destroy it in one attack" in hint
    u.players["H"].ship.ship_class = ShipClass.MERCHANT_CRUISER  # no scanner: worst case
    hint = build_observation(u, "H").action_hint
    assert "max 100 shields" in hint and "beatable even at max shields" in hint


def test_stardock_hint_warns_about_the_battleship_in_a_short_day(hunt):
    u = _arena(ship_class=ShipClass.MERCHANT_CRUISER)
    p = u.players["H"]
    u.sectors[DEEP].occupant_ids.remove("H")
    p.sector_id = K.STARDOCK_SECTOR
    u.sectors[K.STARDOCK_SECTOR].occupant_ids.append("H")
    p.turns_per_day = 50
    assert "BattleShip: 4 turns per warp = about 12 warps" in build_observation(u, "H").action_hint
    p.turns_per_day = 1_000
    assert "BattleShip: 4 turns per warp" not in build_observation(u, "H").action_hint


# ---- Combat Scanner (COMBAT_SCANNER_MODE) -------------------------------------------------------------

def test_combat_scanner_hulls_read_shields_in_their_own_sector_only(hunt, monkeypatch):
    monkeypatch.setattr(K, "COMBAT_SCANNER_MODE", "tw2002")
    u = _arena(ship_class=ShipClass.BATTLESHIP)
    _trader(u)
    u.players["V"].ship.shields = 77
    (t,) = build_observation(u, "H").sector["traders"]
    assert t["shields"] == 77
    u.players["H"].ship.ship_class = ShipClass.CARGOTRAN  # no scanner: shields stay hidden
    (t,) = build_observation(u, "H").sector["traders"]
    assert "shields" not in t
    monkeypatch.setattr(K, "COMBAT_SCANNER_MODE", "legacy")
    u.players["H"].ship.ship_class = ShipClass.BATTLESHIP
    (t,) = build_observation(u, "H").sector["traders"]
    assert "shields" not in t


def test_unscanned_hunter_assumes_max_shields_scanned_hunter_uses_the_reading(hunt):
    u = _arena(fighters=125, ship_class=ShipClass.CARGOTRAN, alignment=500)  # power 125 x 0.8 = 100
    _trader(u, fighters=10, ship_class=ShipClass.CARGOTRAN)  # true defence 8; worst case (10 + 1000) x 0.8
    assert _decide(u)["kind"] != "attack"
    u2 = _arena(fighters=125, ship_class=ShipClass.BATTLESHIP, alignment=500)  # scanner: power 200 vs 8
    _trader(u2, fighters=10, ship_class=ShipClass.CARGOTRAN)
    assert _decide(u2)["kind"] == "attack"


# ---- N3 arming for the hunt (HUNT_ARM_*) and the slow-hull heuristic ---------------------------------

from tw2k.agents.seat_brain import View  # noqa: E402


def _at_dock(*, fighters=200, ship_class=ShipClass.BATTLESHIP, credits=400_000):
    u = _arena(fighters=fighters, ship_class=ship_class)
    p = u.players["H"]
    u.sectors[DEEP].occupant_ids.remove("H")
    p.sector_id = K.STARDOCK_SECTOR
    u.sectors[K.STARDOCK_SECTOR].occupant_ids.append("H")
    p.known_sectors.add(K.STARDOCK_SECTOR)
    p.credits = credits
    return u


def _arm(u, brain=None):
    brain = brain or SeatBrain()
    v = View(build_observation(u, "H").model_dump(mode="json"))
    items = {str(x) for x in v.choices("buy_equip", "item")}
    prices = (v.params("buy_equip").get("item") or {}).get("unit_price_by") or {}
    return brain._hunt_arm(v, items, prices), prices


def test_rich_n3_battleship_arms_for_the_hunt_within_a_spend_share(hunt):
    act, prices = _arm(_at_dock())
    assert act is not None and act["kind"] == "buy_equip" and act["args"]["item"] == "fighters", act
    qty = act["args"]["qty"]
    assert K.HUNT_ARM_MIN_BUY <= qty <= K.HUNT_ARM_FIGHTERS - 200
    assert qty * int(prices["fighters"]) <= 400_000 * K.HUNT_ARM_SPEND_SHARE  # bounded: keeps trade capital


def test_arming_is_one_buy_a_day_and_keeps_the_cash_gate(hunt):
    brain = SeatBrain()
    u = _at_dock(credits=K.HUNT_ARM_CASH_GATE + 20_000)
    act, prices = _arm(u, brain)
    assert act is not None and act["args"]["qty"] * int(prices["fighters"]) <= 20_000
    assert _arm(u, brain)[0] is None  # same game day


def test_no_arming_on_trade_hulls_when_poor_armed_n2_or_legacy(hunt, monkeypatch):
    assert _arm(_at_dock(ship_class=ShipClass.CARGOTRAN))[0] is None  # odds 0.8, 125 per attack
    assert _arm(_at_dock(credits=K.HUNT_ARM_CASH_GATE - 1))[0] is None
    assert _arm(_at_dock(fighters=K.HUNT_ARM_FIGHTERS))[0] is None
    assert _arm(_at_dock(), SeatBrain(value_allocator=False))[0] is None
    monkeypatch.setattr(K, "HUNT_MODE", "legacy")
    assert _arm(_at_dock())[0] is None


def test_defence_hull_pick_never_slows_the_route(hunt, monkeypatch):
    u = _at_dock(ship_class=ShipClass.MERCHANT_CRUISER, credits=2_000_000)
    v = View(build_observation(u, "H").model_dump(mode="json"))
    brain = SeatBrain()
    brain.working_capital = 0
    pick = brain._best_combat_hull(v)
    tpw = K.ship_specs()
    assert pick is None or int(tpw[pick[0]]["turns_per_warp"]) <= int(tpw["merchant_cruiser"]["turns_per_warp"]), pick
    monkeypatch.setattr(K, "SLOW_HULL_HINT_MODE", "legacy")
    legacy = brain._best_combat_hull(v)
    assert legacy is not None and legacy != pick
    assert int(tpw[legacy[0]]["turns_per_warp"]) > int(tpw["merchant_cruiser"]["turns_per_warp"]), legacy


# ---- Hull recovery after a loss (GENESIS_HULL_MODE) and armid overflow (MINE_OVERFLOW_MODE) -----------


def _scout_seat(*, ship_class=ShipClass.SCOUT_MARAUDER, credits=31_141, sector=DEEP):
    u = generate_universe(GameConfig(seed=20260925, universe_size=1000, enable_ferrengi=False, enable_planets=True))
    p = Player(id="H", name="Lost", credits=credits, sector_id=sector,
               ship=Ship(ship_class=ship_class, holds=25, fighters=0, shields=0))
    u.players["H"] = p
    u.sectors[sector].occupant_ids.append("H")
    p.known_sectors.add(sector)
    return u


def _n2_needs_dock(u):
    brain = SeatBrain(value_allocator=False)  # the N2 ladder (scripts/seat_brain_acceptance.n2_brain)
    v = View(build_observation(u, "H").model_dump(mode="json"))
    return brain._needs_stardock(v), brain._stardock_reason(v)


def test_scout_after_a_loss_does_not_fly_to_stardock_for_genesis(monkeypatch):
    """QC seed 20260925: N2-P3 / N1-P5 in the free Scout (genesis cap 0) ping-ponged StarDock <-> a port."""
    monkeypatch.setattr(K, "GENESIS_HULL_MODE", "tw2002")
    u = _scout_seat()
    assert build_observation(u, "H").model_dump(mode="json")["ship"]["genesis_cap"] == 0
    assert _n2_needs_dock(u)[0] is False
    # a hull that can carry a torpedo still goes, and so does the Scout once the CargoTran is affordable
    assert _n2_needs_dock(_scout_seat(ship_class=ShipClass.MERCHANT_CRUISER))[0] is True
    need, why = _n2_needs_dock(_scout_seat(credits=60_000))
    assert need is True and "CargoTran" in why


def test_genesis_hull_legacy_keeps_the_old_trip(monkeypatch):
    monkeypatch.setattr(K, "GENESIS_HULL_MODE", "legacy")
    assert _n2_needs_dock(_scout_seat())[0] is True


@pytest.mark.parametrize("mode,left", [("tw2002", 200), ("legacy", 100)])
def test_armid_damage_past_the_shields_only(monkeypatch, mode, left):
    """10 hits x 20 = 200 damage on 100 shields + 300 fighters: 100 overflow in tw2002 (legacy took 200)."""
    from tw2k.engine.models import MineDeployment, MineType
    from tw2k.engine.runner import _apply_sector_hazards
    monkeypatch.setattr(K, "MINE_OVERFLOW_MODE", mode)
    monkeypatch.setattr(K, "HARDWARE_MODE", "tw2002")
    u = _arena(fighters=300)
    u.players["H"].ship.shields = 100
    u.sectors[DEEP].mines.append(MineDeployment(owner_id="Z", kind=MineType.ARMID, count=20))
    assert _apply_sector_hazards(u, "H", u.sectors[DEEP]) == 200
    assert u.players["H"].ship.shields == 0 and u.players["H"].ship.fighters == left


def test_docked_n3_options_path_offers_the_arming_buy(hunt, monkeypatch):
    """_opt_defense is silent at the 200-fighter floor; _opt_hunt_arm still arms a docked BattleShip."""
    from tw2k.agents.seat_brain import SeatMemory
    u = _at_dock()
    brain = SeatBrain()
    brain.mem = SeatMemory()
    brain.mem.hot_sectors.add(DEEP)
    v = View(build_observation(u, "H").model_dump(mode="json"))
    opt = brain._opt_hunt_arm(v)
    assert opt is not None and opt[0] == K.HUNT_ARM_OPTION_VALUE and opt[1]["args"]["item"] == "fighters"
    assert brain._opt_hunt_arm(v) is not None  # offering it does not use up the day; choosing it does
    monkeypatch.setattr(K, "HUNT_MODE", "legacy")
    assert brain._opt_hunt_arm(v) is None


# ---- legacy pin -------------------------------------------------------------------------------------

# tests/fed_legacy_digest.py, scripted N3,N2,N1,H, seed 250925, 3 days, every other switch at its default:
# f10b080 (the base) digests to this, and so does this slice with only its seven switches flipped to legacy.
V2_SWITCHES = ("PLANET_DIVIDEND_MODE", "HUNT_MODE", "COMBAT_FRAMING_MODE", "SLOW_HULL_HINT_MODE",
               "COMBAT_SCANNER_MODE", "GENESIS_HULL_MODE", "MINE_OVERFLOW_MODE")
# bots-use-planet-trade-v1 changed the tw2002 bots' planet-trade play, so this pin also flips PLANET_TRADE_MODE (the
# single-mode pin convention): f10b080 with PLANET_TRADE_MODE flipped digests to 77c7d444a0965a2c40cffcca (the
# PLANET_TRADE golden), and so do b7e1f86 and bots-use-planet-trade-v1 with these eight switches flipped.
V2_PIN_FLIP = V2_SWITCHES + ("PLANET_TRADE_MODE",)
V2_LEGACY_GOLDEN = "77c7d444a0965a2c40cffcca"  # was 5e29f9528d7e5000218b575a (f10b080, flip=())


def test_fullgame_fixes_v2_switches_off_equal_the_base():
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    flips = V2_PIN_FLIP + ("CORPSHIP_MODE", "FED_OUTPOST_MODE", "PORT_UPGRADE_MODE")
    code = (
        "import sys; sys.path.insert(0, 'tests'); sys.path.insert(0, 'src');"
        "from pathlib import Path; from fed_legacy_digest import legacy_run_digest;"
        f"print(legacy_run_digest(Path('.'), 'N3,N2,N1,H', 3, 250925, flip={flips!r}))"
    )
    env = pin_env()
    out = subprocess.run([sys.executable, "-c", code], cwd=root, env=env, capture_output=True, text=True,
                         timeout=900, check=True)
    assert out.stdout.strip().splitlines()[-1] == V2_LEGACY_GOLDEN
