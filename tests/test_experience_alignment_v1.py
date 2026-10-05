"""experience-alignment-v1: ranks, experience and alignment (docs/playtests/ranks/EXPERIENCE_ALIGNMENT.md)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.agents.prompts import format_observation, get_system_prompt
from tw2k.agents.seat_acceptance import validate_action
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, build_observation, generate_universe
from tw2k.engine.models import Corporation, FighterDeployment, FighterMode, MineType, Player, Ship
from tw2k.engine.runner import tick_day
from tw2k.engine.victory import (
    alignment_label,
    combat_rewards,
    is_commissioned,
    is_fedsafe,
    kill_rewards,
    rank_for,
    rank_level,
)

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "playtests" / "ranks" / "EXPERIENCE_ALIGNMENT.md"


@pytest.fixture
def legacy(monkeypatch):
    monkeypatch.setattr(K, "RANK_MODE", "legacy")
    monkeypatch.setattr(K, "ROB_MODE", "legacy")  # goldens predate rob/steal


@pytest.fixture
def tw(monkeypatch):
    monkeypatch.setattr(K, "RANK_MODE", "tw2002")


# --- doc first -----------------------------------------------------------------------------

def test_rules_doc_lists_every_row_with_a_mark() -> None:
    text = DOC.read_text(encoding="utf-8")
    rows = ([f"x{n}" for n in range(1, 16)] + [f"a{n}" for n in range(1, 8)] + [f"r{n}" for n in range(1, 8)]
            + [f"u{n}" for n in range(1, 7)] + [f"d{n}" for n in range(1, 5)])
    for row in rows:
        assert f"| {row} |" in text, f"row {row} missing"
    for word in ("CONFIRMED", "SOURCE-CONFLICT", "UNVERIFIED", "Deliberate differences", "RANK_MODE",
                 "fedsafe", "Federal Commission", "Imperial StarShip", "toward zero", "Delivered"):
        assert word.lower() in text.lower(), word


def test_switch_defaults() -> None:
    assert K.RANK_MODE == "tw2002" and K.rank_tw2002()
    assert len(K.GOOD_RANKS) == len(K.EVIL_RANKS) == len(K.RANK_THRESHOLDS) == 23
    assert K.RANK_THRESHOLDS[1] == 2 and K.RANK_THRESHOLDS[-1] == 4_194_304
    assert (K.COMMISSION_ALIGNMENT, K.FEDSAFE_MAX_EXPERIENCE) == (1000, 999)
    # legacy tables untouched
    assert K.RANK_TABLE[0] == (0, "Civilian") and K.RANK_TABLE[-1] == (250_000, "Fleet Admiral")
    assert K.ALIGNMENT_TIERS[-1] == (10_000, "Saint")
    assert K.XP_AWARDS["warp"] == 1 and K.XP_AWARDS["kill_player"] == 200
    assert K.SHIP_SPECS["imperial_starship"]["min_alignment"] == 2000


# --- shared scenario --------------------------------------------------------------------------

def _digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _move(u, pid, sid):
    p = u.players[pid]
    if pid in u.sectors[p.sector_id].occupant_ids:
        u.sectors[p.sector_id].occupant_ids.remove(pid)
    p.sector_id = sid
    u.sectors[sid].occupant_ids.append(pid)
    p.known_sectors.add(sid)


def rank_world(seed: int = 3901):
    u = generate_universe(GameConfig(seed=seed, universe_size=200, max_days=10, planet_spawn_probability=0.06,
                                     enable_ferrengi=False))
    for pid, name in (("A", "Alice"), ("B", "Bob"), ("C", "Carol"), ("D", "Dave")):
        u.players[pid] = Player(id=pid, name=name, ship=Ship(holds=40, fighters=400, shields=100), sector_id=1)
        u.sectors[1].occupant_ids.append(pid)
        u.players[pid].known_sectors.add(1)
        u.players[pid].credits = 200_000
    u.players["A"].experience, u.players["A"].alignment = 600, 300
    u.players["B"].experience, u.players["B"].alignment = 3000, -2000
    u.players["C"].experience, u.players["C"].alignment = 40, 1200
    u.players["D"].experience, u.players["D"].alignment = 1500, 50
    u.players["B"].ship.fighters, u.players["B"].ship.shields = 330, 0
    port_sid = next(s for s in sorted(u.sectors) if s > 10 and u.sectors[s].port is not None
                    and u.sectors[s].port.class_id.value in (1, 2, 3, 4, 5, 6, 7, 8)
                    and any(u.sectors[s].port.sells(c) for c in u.sectors[s].port.stock))
    for c, st in u.sectors[port_sid].port.stock.items():
        st.current = min(500, int(st.maximum))
    deep = next(s for s in sorted(u.sectors) if s >= 40 and len(u.sectors[s].warps) >= 2
                and not u.sectors[s].planet_ids and u.sectors[s].port is None)
    held = int(sorted(u.sectors[deep].warps)[0])
    u.sectors[held].fighters = FighterDeployment(owner_id="B", count=50, mode=FighterMode.DEFENSIVE)
    return u, port_sid, deep, held


def run_rank_scenario(u, port_sid, deep, held):
    out = []

    def snap(tag):
        for pid in ("A", "B", "C", "D"):
            p = u.players[pid]
            obs = build_observation(u, pid)
            out.append((tag, pid, int(p.experience), int(p.alignment),
                        _digest(obs.model_dump(mode="json")), _digest(format_observation(obs))))

    def do(tag, pid, kind, **args):
        r = apply_action(u, pid, Action(kind=kind, args=args))
        out.append((tag, bool(r.ok), int(r.turns_spent or 0), str(r.error or "")))
        snap(tag)

    snap("start")
    a = u.players["A"]
    a.ship.photon_missiles = 1
    do("fed_attack", "A", ActionKind.ATTACK, target="C", qty=10)
    do("fed_attack_red", "A", ActionKind.ATTACK, target="B", qty=10)
    do("fed_photon", "A", ActionKind.PHOTON_MISSILE, target="D")
    _move(u, "A", port_sid)
    port = u.sectors[port_sid].port
    c = next(c for c in sorted(port.stock, key=lambda x: x.value) if port.sells(c) and port.stock[c].current >= 20)
    do("trade", "A", ActionKind.TRADE, commodity=c.value, qty=3, side="buy")
    _move(u, "A", deep)
    _move(u, "B", deep)
    _move(u, "C", deep)
    do("hit_red", "A", ActionKind.ATTACK, target="B", qty=20)
    do("kill_red", "A", ActionKind.ATTACK, target="B", qty=360)
    do("hit_blue", "C", ActionKind.ATTACK, target="A", qty=5)
    _move(u, "A", deep)
    a.ship.genesis = 1
    do("genesis", "A", ActionKind.DEPLOY_GENESIS)
    pl = u.planets[max(u.sectors[deep].planet_ids)]
    pl.owner_id = "D"
    pl.fighters, pl.shields = 0, 0
    a.planet_landed = pl.id
    do("destroy_1", "A", ActionKind.PLANET_DESTROY, planet_id=pl.id)
    do("destroy_2", "A", ActionKind.PLANET_DESTROY, planet_id=pl.id)
    a.planet_landed = None
    do("warp_held", "A", ActionKind.WARP, target=held)
    do("hit_figs", "A", ActionKind.ATTACK, target="fighters", qty=60)
    tick_day(u)
    snap("day")
    return out


# --- legacy keeps today's numbers, byte for byte -----------------------------------------

LEGACY_GOLDEN = [
    ('start', 'A', 600, 300, 'ebcd4f643ef01595', '51c737cdd35f24aa'),
    ('start', 'B', 3000, -2000, '675093c6c58ad7e3', '3f20d8e8881e1afa'),
    ('start', 'C', 40, 1200, 'dac412b524ec5487', '3e530e5b85c5f123'),
    ('start', 'D', 1500, 50, '02a64aca8eb8b505', '50847cca5e594c5a'),
    ('fed_attack', False, 0, 'FedSpace — combat forbidden'),
    ('fed_attack', 'A', 600, 100, 'ec514e4ea3144184', '892476b8b2f1dc2d'),
    ('fed_attack', 'B', 3000, -2000, 'ec61c09e40ec2ad5', 'ae7c9581df3c0827'),
    ('fed_attack', 'C', 40, 1200, '99c0e80dbc22ef80', '1b87191a3d9eb8c1'),
    ('fed_attack', 'D', 1500, 50, 'be77f8a95c88c5f9', 'eba361025273b502'),
    ('fed_attack_red', False, 0, 'FedSpace — combat forbidden'),
    ('fed_attack_red', 'A', 600, -100, '8f2e80cbed0ed06a', '2df425c5560aca17'),
    ('fed_attack_red', 'B', 3000, -2000, 'bb3e12b623ba3e92', '226132bb475b5f19'),
    ('fed_attack_red', 'C', 40, 1200, 'fdb1749475e28ca5', 'd626edebf7911635'),
    ('fed_attack_red', 'D', 1500, 50, '7c065c76d803755f', '374a5ceba6390b1d'),
    ('fed_photon', False, 0, 'FedSpace forbids weapons fire'),
    ('fed_photon', 'A', 600, -200, '0976b86e533d8691', 'e5681d1ec18396a8'),
    ('fed_photon', 'B', 3000, -2000, '7c32667e72e7eb1f', 'f58b5ad36fb7934a'),
    ('fed_photon', 'C', 40, 1200, '6d0893932ff6df5a', '64d1705cddff8060'),
    ('fed_photon', 'D', 1500, 50, 'f072416d07e9c23b', '89b92882cd5b3ee8'),
    ('trade', True, 1, ''),
    ('trade', 'A', 601, -200, '4e340fa80f48494d', '512cafb333373c5b'),
    ('trade', 'B', 3000, -2000, '5cb718946eb4b540', 'ac515cf9e4628da4'),
    ('trade', 'C', 40, 1200, 'aad7d1e4c11a2ad2', 'd68bb3b02a7f50ec'),
    ('trade', 'D', 1500, 50, 'a2611211f0c26d20', '1ef3edbe5e362bfb'),
    ('hit_red', True, 5, ''),
    ('hit_red', 'A', 601, -200, '55f15118878fa54c', '493848d001176a58'),
    ('hit_red', 'B', 3000, -2000, '2cacd3404c319ce3', '7609a84bc831a76d'),
    ('hit_red', 'C', 40, 1200, '4c3fa974e978fce2', 'cce04f07613529b9'),
    ('hit_red', 'D', 1500, 50, '5374f746d0f3286e', 'e640640c1b4cefc6'),
    ('kill_red', True, 5, ''),
    ('kill_red', 'A', 801, -200, 'a40d4e4541bacc44', '62338db622adafde'),
    ('kill_red', 'B', 2700, -2000, '3ed4f2e996bef806', '27e7a952df980062'),
    ('kill_red', 'C', 40, 1200, '2e06bd0efe5c9914', '280842c7711f4508'),
    ('kill_red', 'D', 1500, 50, '119c923acbe442da', 'd0cddc048f63ddd7'),
    ('hit_blue', True, 5, ''),
    ('hit_blue', 'A', 801, -200, '24747a09111d83ff', 'fb6478af6c19f18d'),
    ('hit_blue', 'B', 2700, -2000, '22cc5dcf9a575e1e', 'fcd8c70d9ec202dc'),
    ('hit_blue', 'C', 40, 1200, 'c2206ca49f32ce8c', 'f92f9deb59d83a68'),
    ('hit_blue', 'D', 1500, 50, 'e0eb7efdce9ff5fa', '98cb9e742120f33c'),
    ('genesis', True, 4, ''),
    ('genesis', 'A', 901, -200, '860f18509d932639', '3ef9badaccea4884'),
    ('genesis', 'B', 2700, -2000, 'c3185749529ab792', '12370b7e008bfdc1'),
    ('genesis', 'C', 40, 1200, '4619c54b8ad40528', '18e885d2fbb929a7'),
    ('genesis', 'D', 1500, 50, '0312fbcbee5c9306', '35bc154c88090ae0'),
    ('destroy_1', True, 1, ''),
    ('destroy_1', 'A', 901, -250, '5b831d2d6a1c9ee4', 'b11ce92e4a87cabc'),
    ('destroy_1', 'B', 2700, -2000, '7b6ede5f97427d00', '33c270edffe4e10d'),
    ('destroy_1', 'C', 40, 1200, '59b5e9b71972b90f', 'd3ea21b1452c54a7'),
    ('destroy_1', 'D', 1500, 50, '039223bfca3e0570', '16fd22e5b8fc7171'),
    ('destroy_2', True, 1, ''),
    ('destroy_2', 'A', 901, -300, '40b31a971230a9af', '4929d4085cfe5910'),
    ('destroy_2', 'B', 2700, -2000, 'db8b2c9c9a03a27a', 'f3411da255a2c22c'),
    ('destroy_2', 'C', 40, 1200, '3c3babb7032c9655', '6fc8a6cef3b6a0ae'),
    ('destroy_2', 'D', 1500, 50, '291fdabac168e83e', '1499de85748db84e'),
    ('warp_held', True, 3, ''),
    ('warp_held', 'A', 902, -300, 'fdd684035e84d580', '646fddd2e1ffa028'),
    ('warp_held', 'B', 2700, -2000, 'd16f13c127eb05f0', 'fbe3449b2a9ab41f'),
    ('warp_held', 'C', 40, 1200, '6942cac3d862f485', '6b41dc63b4d30e87'),
    ('warp_held', 'D', 1500, 50, '6737c37aa1228c6a', '6133417ef807f5be'),
    ('hit_figs', True, 5, ''),
    ('hit_figs', 'A', 902, -300, 'd759b4975222f100', '83b8f112a8b0d766'),
    ('hit_figs', 'B', 2700, -2000, 'cd8bad74938cb44f', '134a84d393c7491e'),
    ('hit_figs', 'C', 40, 1200, 'da99e83ff3a2b205', '0a76f1dd4ed8d5a5'),
    ('hit_figs', 'D', 1500, 50, '83d98a38c593f506', '5d51a448fcee5a7a'),
    ('day', 'A', 902, -300, 'dfc8a322b567820f', 'eb07d2719bf540c7'),
    ('day', 'B', 2700, -2000, 'b93844591f43c850', '65b70c891f4b237b'),
    ('day', 'C', 40, 1200, 'dc1e3eadcfa5b572', 'd2b03c479831655c'),
    ('day', 'D', 1500, 50, '767b6a8cb595f115', '23fa520b6aa5f384'),
]


def test_legacy_is_unchanged(legacy) -> None:
    u, port_sid, deep, held = rank_world()
    assert run_rank_scenario(u, port_sid, deep, held) == LEGACY_GOLDEN


# --- tw2002 numbers through the same scenario ------------------------------------------------

TW2002_A = [
    ("start", 600, 300),
    ("fed_attack", 600, 100),        # u1: C is fedsafe - refused, -200
    ("fed_attack_red", 600, 104),    # u1: a red is fair game in FedSpace; a1: 10 lost x 2000 / 5000
    ("fed_photon", 600, 104),        # D has 1500 experience - not fedsafe
    ("trade", 602, 104),             # x1 + x2: trade +1 and first dock +1
    ("hit_red", 603, 112),           # x12: 20 lost / 15; a1: 20 x 2000 / 5000
    ("kill_red", 923, 1232),         # x13/a2: +300 (10% of 3000) and +1000 (half of -2000) plus the fighters
    ("hit_blue", 923, 1232),
    ("genesis", 948, 1242),          # x6: +25 experience, +10 alignment (good)
    ("destroy_1", 948, 1242),        # colonists only
    ("destroy_2", 998, 1241),        # x7: +50 experience, -1 alignment
    ("warp_held", 998, 1241),        # x4: no experience for a warp
    ("hit_figs", 1001, 1261),        # x14/a3: 50 lost / 15 and 50 x 2000 / 5000 against red-owned fighters
    ("day", 1002, 1262),             # x3
]


def test_tw2002_numbers_through_the_scenario(tw) -> None:
    u, port_sid, deep, held = rank_world()
    rows = run_rank_scenario(u, port_sid, deep, held)
    a_rows = [(r[0], r[2], r[3]) for r in rows if len(r) == 6 and r[1] == "A"]
    assert a_rows == TW2002_A
    by = {(r[0], r[1]): (r[2], r[3]) for r in rows if len(r) == 6}
    assert by[("kill_red", "B")] == (2700, -2000)  # d1: the pod costs 10% once, no alignment
    assert by[("hit_blue", "C")] == (40, 1199)     # same colour: 5 x 1232 / 5000 toward zero, 5 / 35 = 0
    assert by[("day", "B")] == (2701, -1999)


# --- ladders ----------------------------------------------------------------------------------

def test_rank_ladders_follow_the_tables(tw) -> None:
    assert rank_for(0, 0) == rank_for(1, -5) == "Civilian"
    assert rank_for(2, 0) == "Private" and rank_for(2, -1) == "Nuisance 3rd Class"
    assert rank_for(1023, 10) == "Sergeant Major" and rank_for(1024, 10) == "Warrant Officer"
    assert rank_for(1024, -10) == "Smuggler Savant" and rank_for(65_536, -1) == "Dread Pirate"
    assert rank_for(4_194_303, -1) == "Heinous Overlord" and rank_for(4_194_304, -1) == "Prime Evil"
    assert rank_for(10**9, 5) == "Fleet Admiral"
    assert [rank_level(2 ** n) for n in range(1, 23)] == list(range(1, 23))
    assert (alignment_label(1), alignment_label(0), alignment_label(-1)) == ("Good", "Neutral", "Evil")


def test_legacy_ladder_is_unchanged(legacy) -> None:
    assert rank_for(0) == "Civilian" and rank_for(500, -9999) == "Captain" and rank_for(250_000) == "Fleet Admiral"
    assert alignment_label(10_000) == "Saint" and alignment_label(-50) == "Rogue"


# --- experience sources -----------------------------------------------------------------------

def test_experience_table_by_mode(monkeypatch) -> None:
    monkeypatch.setattr(K, "RANK_MODE", "tw2002")
    for key in ("warp", "kill_player", "scan", "probe", "claim_planet", "build_citadel_lvl", "alliance"):
        assert K.xp_award(key) == 0, key
    assert K.xp_award("trade") == 1
    assert (K.xp_award("deploy_genesis"), K.xp_award("first_dock"), K.xp_award("daily")) == (25, 1, 1)
    assert (K.xp_award("destroy_planet"), K.xp_award("destroy_port")) == (50, 50)
    monkeypatch.setattr(K, "RANK_MODE", "legacy")
    assert K.xp_award("warp") == 1 and K.xp_award("deploy_genesis") == 100 and K.xp_award("first_dock") == 0


def test_first_dock_pays_once_per_port(tw) -> None:
    u, port_sid, deep, held = rank_world()
    port = u.sectors[port_sid].port
    c = next(c for c in sorted(port.stock, key=lambda x: x.value) if port.sells(c))
    _move(u, "A", port_sid)
    _move(u, "C", port_sid)
    a, cc = u.players["A"], u.players["C"]
    assert apply_action(u, "A", Action(kind=ActionKind.TRADE, args={"commodity": c.value, "qty": 2, "side": "buy"})).ok
    assert a.experience == 602  # 600 + trade + first_dock
    assert apply_action(u, "A", Action(kind=ActionKind.TRADE, args={"commodity": c.value, "qty": 2, "side": "buy"})).ok
    assert apply_action(u, "C", Action(kind=ActionKind.TRADE, args={"commodity": c.value, "qty": 2, "side": "buy"})).ok
    assert (a.experience, cc.experience) == (603, 41)  # second trade +1 only; C gets trade, no first_dock


def test_daily_point_skips_the_dead(tw) -> None:
    u, *_ = rank_world()
    u.players["D"].alive = False
    tick_day(u)
    assert (u.players["A"].experience, u.players["A"].alignment) == (601, 301)  # daily +1
    assert (u.players["D"].experience, u.players["D"].alignment) == (1500, 50)


@pytest.mark.parametrize("align,expect", [(300, 310), (0, 0), (-300, -310)])
def test_genesis_alignment_follows_the_side(tw, align, expect) -> None:
    u, port_sid, deep, held = rank_world()
    _move(u, "A", deep)
    a = u.players["A"]
    a.alignment, a.ship.genesis = align, 1
    assert apply_action(u, "A", Action(kind=ActionKind.DEPLOY_GENESIS, args={})).ok
    assert (a.experience, a.alignment) == (625, expect)


def test_port_destroyed_by_atomics_pays_fifty(tw) -> None:
    from tw2k.engine.runner import _handle_atomic_detonation

    u, port_sid, deep, held = rank_world()
    _move(u, "A", port_sid)
    a = u.players["A"]
    sector = u.sectors[port_sid]
    for st in sector.port.stock.values():
        st.current = 0
    a.ship.mines[MineType.ATOMIC] = 3
    assert _handle_atomic_detonation(u, "A", 3, sector, 1).ok
    assert sector.port is None
    assert (a.experience, a.alignment) == (650, 300 - 150)  # x11 +50; a7 -50 per warhead kept


# --- combat formulas --------------------------------------------------------------------------

def _two(u, mine, theirs):
    u.players["A"].alignment = mine
    u.players["A"].experience = 0
    return theirs


@pytest.mark.parametrize("mine,theirs,lost,exp,align", [
    (100, -2000, 150, 10, 60),       # opposite: / 15, +lost x 2000 / 5000
    (100, 2000, 350, 10, -140),      # same: / 35, alignment falls
    (-100, 2000, 150, 10, -60),      # red hitting blue goes redder
    (0, -2000, 250, 10, 100),        # neutral: / 25
    (100, -3, 7, 0, 0),              # 7 x 3 / 5000 rounds toward zero
])
def test_ship_combat_rewards(tw, mine, theirs, lost, exp, align) -> None:
    u, *_ = rank_world()
    _two(u, mine, theirs)
    assert combat_rewards(u, "A", theirs, lost) == (exp, align)
    assert (u.players["A"].experience, u.players["A"].alignment) == (exp, mine + align)


def test_sector_fighter_rewards_use_gold_divisors(tw) -> None:
    u, *_ = rank_world()
    _two(u, 100, 0)
    assert combat_rewards(u, "A", 5000, 1000, sector_fighters=True) == (28, -500)    # same: / 35, / 10000
    _two(u, 100, 0)
    assert combat_rewards(u, "A", -5000, 1000, sector_fighters=True) == (66, 1000)   # opposite: / 15, / 5000


def test_rewards_are_off_in_legacy(legacy) -> None:
    u, *_ = rank_world()
    assert combat_rewards(u, "A", -2000, 1500) == (0, 0)
    kill_rewards(u, "A", 10_000, -10_000)
    assert (u.players["A"].experience, u.players["A"].alignment) == (600, 300)


def test_ship_destroyed_kill_reads_the_victim_before_the_loss(tw) -> None:
    u, port_sid, deep, held = rank_world()
    for pid in ("A", "B"):
        _move(u, pid, deep)
    b = u.players["B"]
    b.pods_day, b.pods_today = u.day, K.PODS_PER_DAY  # the next loss is Ship Destroyed
    b.ship.fighters = 10
    a = u.players["A"]
    r = apply_action(u, "A", Action(kind=ActionKind.ATTACK, args={"target": "B", "qty": 50}))
    assert r.ok
    assert (b.experience, b.alignment) == (1500, -1000)  # d2: halved toward zero by the pods code, once
    assert a.experience == 600 + 10 // 15 + 300 and a.alignment == 300 + 10 * 2000 // 5000 + 1000


# --- unlocks ----------------------------------------------------------------------------------

def test_fedsafe_and_commission_helpers(tw) -> None:
    p = Player(id="Z", name="Z", ship=Ship())
    p.experience, p.alignment = 999, 0
    assert is_fedsafe(p) and not is_commissioned(p)
    p.experience = 1000
    assert not is_fedsafe(p)
    p.experience, p.alignment = 10, -1
    assert not is_fedsafe(p)
    p.alignment = 1000
    assert is_commissioned(p)


def _legal(u, pid, kind):
    return next(x for x in build_observation(u, pid).legal_actions if x["kind"] == kind)


def test_fedspace_shields_only_fedsafe_traders(tw) -> None:
    u, *_ = rank_world()
    u.players["A"].ship.photon_missiles = 1
    la = _legal(u, "A", "attack")
    assert la["legal"] and sorted(la["params"]["target"]["choices"]) == ["B", "D"]
    assert sorted(_legal(u, "A", "photon_missile")["params"]["target"]["choices"]) == ["B", "D"]
    for pid in ("B", "D"):
        u.players[pid].alignment, u.players[pid].experience = 5, 10
    la = _legal(u, "A", "attack")
    assert not la["legal"] and "fedsafe" in la["reason"]
    assert not _legal(u, "A", "photon_missile")["legal"]
    r = apply_action(u, "A", Action(kind=ActionKind.ATTACK, args={"target": "C", "qty": 5}))
    assert not r.ok and u.players["A"].alignment == 100


def test_fedspace_shields_everyone_in_legacy(legacy) -> None:
    u, *_ = rank_world()
    la = _legal(u, "A", "attack")
    assert not la["legal"] and "FedSpace" in la["reason"]
    r = apply_action(u, "A", Action(kind=ActionKind.ATTACK, args={"target": "B", "qty": 5}))
    assert not r.ok and u.players["A"].alignment == 100


def _iss_world(align):
    u, *_ = rank_world()
    a = u.players["A"]
    _move(u, "A", K.STARDOCK_SECTOR)
    a.credits, a.alignment = 10_000_000, align
    return u, a


@pytest.mark.parametrize("align,ok", [(999, False), (1000, True)])
def test_imperial_starship_needs_a_commission(tw, align, ok) -> None:
    u, a = _iss_world(align)
    la = _legal(u, "A", "buy_ship")
    assert ("imperial_starship" in la["params"]["ship_class"]["choices"]) is ok
    r = apply_action(u, "A", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": "imperial_starship"}))
    assert r.ok is ok
    if not ok:
        assert "1000" in la["params"]["ship_class"]["blocked_by"]["imperial_starship"]


def test_imperial_starship_needs_2000_in_legacy(legacy) -> None:
    u, a = _iss_world(1500)
    r = apply_action(u, "A", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": "imperial_starship"}))
    assert not r.ok


def test_evil_traders_may_buy_ordinary_hulls(tw) -> None:
    u, a = _iss_world(-500)
    r = apply_action(u, "A", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": "merchant_freighter"}))
    assert r.ok, r.error


def test_legacy_still_bars_evil_traders_from_every_hull(legacy) -> None:
    u, a = _iss_world(-500)
    r = apply_action(u, "A", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": "merchant_freighter"}))
    assert not r.ok


# --- fog: other traders' rank only as the original shows it ----------------------------------

SENTINEL = -123_457


def _views(u, pid):
    obs = build_observation(u, pid)
    return obs, json.dumps(obs.model_dump(mode="json"), default=str), format_observation(obs)


def test_rivals_show_title_side_and_experience_never_alignment(tw) -> None:
    u, port_sid, deep, held = rank_world()
    u.players["B"].alignment = SENTINEL
    obs, dump, text = _views(u, "A")
    rb = next(r for r in obs.rivals if r["id"] == "B")
    assert (rb["rank"], rb["side"], rb["experience"]) == ("Robber", "evil", 3000)
    assert "alignment" not in rb
    ob = next(o for o in obs.other_players if o["id"] == "B")
    assert ob["rank"] == "Robber" and "alignment" not in ob
    assert str(abs(SENTINEL)) not in dump and str(abs(SENTINEL)) not in text
    assert (obs.rank, obs.experience, obs.alignment, obs.alignment_label) == ("Sergeant Major", 600, 300, "Good")
    assert "Sergeant Major" in text and "Robber" in text


def test_a_trader_out_of_sight_shows_no_title_in_other_players(tw) -> None:
    u, port_sid, deep, held = rank_world()
    _move(u, "B", deep)
    ob = next(o for o in build_observation(u, "A").other_players if o["id"] == "B")
    assert "rank" not in ob and "sector_id" not in ob


def test_corp_mates_keep_exact_alignment(tw) -> None:
    u, *_ = rank_world()
    u.corporations["ZZ"] = Corporation(ticker="ZZ", name="Zed", ceo_id="A", member_ids=["A", "B"])
    for pid in ("A", "B"):
        u.players[pid].corp_ticker = "ZZ"
    ob = next(o for o in build_observation(u, "A").other_players if o["id"] == "B")
    assert ob["alignment"] == -2000 and ob["rank"] == "Robber"


def test_a_kill_does_not_leak_alignment_to_witnesses(tw) -> None:
    u, port_sid, deep, held = rank_world()
    for pid in ("A", "B", "D"):
        _move(u, pid, deep)
    b = u.players["B"]
    b.alignment, b.ship.fighters = SENTINEL, 10
    b.pods_day, b.pods_today = u.day, K.PODS_PER_DAY  # Ship Destroyed: alignment halves too
    assert apply_action(u, "A", Action(kind=ActionKind.ATTACK, args={"target": "B", "qty": 50})).ok
    gained = abs(int(SENTINEL * K.KILL_ALIGN_SHARE))
    assert b.alignment == SENTINEL + gained
    for pid in ("D", "C"):
        obs, dump, text = _views(u, pid)
        for secret in (str(abs(SENTINEL)), str(gained), str(abs(b.alignment)), str(u.players["A"].alignment)):
            assert secret not in dump and secret not in text, (pid, secret)


def test_legacy_shows_no_rank_of_others(legacy) -> None:
    obs = build_observation(rank_world()[0], "A")
    assert all("rank" not in r and "experience" not in r for r in obs.rivals)
    assert obs.rank == "Captain" and obs.alignment_label == "Citizen"


def test_system_prompt_names_the_commission(monkeypatch) -> None:
    monkeypatch.setattr(K, "RANK_MODE", "tw2002")
    text = get_system_prompt()
    assert "alignment >= 1000" in text and "fedsafe" in text
    monkeypatch.setattr(K, "RANK_MODE", "legacy")
    text = get_system_prompt()
    assert "alignment >= 2000" in text and "fedsafe" not in text


# --- seat brains ------------------------------------------------------------------------------

def _brains():
    spec = importlib.util.spec_from_file_location("sba", ROOT / "scripts" / "seat_brain_acceptance.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from tw2k.agents.seat_brain import SeatBrain

    return {"N1": mod.n1_brain, "N2": mod.n2_brain, "N3": SeatBrain}


@pytest.mark.parametrize("pid", ["A", "B"])
def test_seat_brains_stay_legal_in_fedspace_and_out(tw, pid) -> None:
    for name, make in _brains().items():
        u, port_sid, deep, held = rank_world()
        p = u.players[pid]
        brain = make()
        for _ in range(30):
            obs = build_observation(u, pid).model_dump(mode="json")
            choice = brain.decide(obs)
            assert validate_action(obs, choice) == [], (name, pid, choice)
            res = apply_action(u, pid, Action(kind=choice["kind"], args=choice.get("args") or {}))
            assert res.ok, (name, pid, choice, res.error)
            if p.turns_today >= p.turns_per_day or not p.alive:
                break
