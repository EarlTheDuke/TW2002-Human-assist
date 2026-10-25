"""NOTE 163: five remaining rows. The new switch is the good-trader bounty.

6.7 and 9.2 are already what a normal game does. 6.11 and 13.4 are already
behind profile switches. 9.5 gains BOUNTY_GOOD_MODE, row 187. Legacy stays
the refusal. V311_PROFILE=v311 turns the helper on. The string "1" does not,
and TW2002_LIVE_PROFILE does not.
"""
from __future__ import annotations

import tw2k.engine.constants as K
from tests.test_fedspace_police_v1 import _act, _world
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.models import Event, EventKind, PlanetClass, Player, Ship, ShipClass
from tw2k.engine.observation import _event_visible_to
from tw2k.engine.runner import _bfs_path, tick_day


def _seat(universe, pid: str = "P1") -> Player:
    player = Player(
        id=pid,
        name="Ada",
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, fighters=20, holds=20),
        sector_id=1,
        credits=0,
        turns_per_day=500,
        experience=10,
        alignment=4,
    )
    universe.players[pid] = player
    universe.sectors[1].occupant_ids.append(pid)
    return player


def _deep_sector(universe) -> int:
    for sid in sorted(universe.sectors):
        if sid in K.FEDSPACE_SECTORS or universe.sectors[sid].planet_ids:
            continue
        path = _bfs_path(universe, K.STARDOCK_SECTOR, sid)
        if path and len(path) >= K.GENESIS_MIN_HOPS_FROM_STARDOCK:
            return sid
    raise AssertionError("no sector far enough from StarDock")


def test_bounty_on_a_good_trader_stays_refused_until_the_switch_is_on():
    universe = _world(
        players={
            "A": dict(alignment=100, credits=50_000, sector_id=1, experience=40),
            "B": dict(alignment=80, credits=1000, sector_id=20, experience=12),
            "C": dict(alignment=0, credits=1000, sector_id=20),
        }
    )
    refused = _act(universe, "A", ActionKind.POST_REWARD, target_id="B", amount=2500)
    assert refused.ok is False
    assert refused.error == "invalid reward target"
    assert universe.players["A"].alignment == 100
    assert universe.players["A"].credits == 50_000
    assert universe.players["A"].experience == 40
    assert K.bounty_good_live() is False
    assert K.BOUNTY_GOOD_MODE == "legacy"


def test_v311_bounty_costs_one_alignment_per_250_and_no_experience(monkeypatch):
    monkeypatch.setattr(K, "BOUNTY_GOOD_MODE", "v311")
    universe = _world(
        players={
            "A": dict(alignment=100, credits=50_000, sector_id=1, experience=40),
            "B": dict(alignment=80, credits=1000, sector_id=20, experience=12),
            "C": dict(alignment=-40, credits=1000, sector_id=20),
            "D": dict(alignment=0, credits=1000, sector_id=20),
        }
    )
    bounty = _act(universe, "A", ActionKind.POST_REWARD, target_id="B", amount=2500)
    assert bounty.ok
    assert universe.players["A"].credits == 47_500
    assert universe.players["A"].alignment == 90
    assert universe.players["A"].experience == 40
    posted = universe.posted_rewards["B"]
    assert posted[-1]["amount"] == 2500
    reward = _act(universe, "A", ActionKind.POST_REWARD, target_id="C", amount=2000)
    assert reward.ok
    assert universe.players["A"].alignment == 92
    assert universe.players["A"].experience == 40
    neutral = _act(universe, "A", ActionKind.POST_REWARD, target_id="D", amount=1000)
    assert neutral.ok is False
    assert neutral.error == "invalid reward target"


def test_profile_turns_the_bounty_on_and_the_other_two_strings_do_not(monkeypatch):
    monkeypatch.setattr(K, "BOUNTY_GOOD_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.bounty_good_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    assert K.v311_profile() is False
    assert K.bounty_good_live() is False
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.BOUNTY_GOOD_MODE == "legacy"
    assert K.bounty_good_live() is True
    universe = _world(
        players={
            "A": dict(alignment=20, credits=5_000, sector_id=1, experience=3),
            "B": dict(alignment=5, credits=100, sector_id=11),
        }
    )
    dock = int(K.stardock_sector_of(universe))
    if universe.players["A"].sector_id != dock:
        universe.sectors[universe.players["A"].sector_id].occupant_ids.remove("A")
        universe.players["A"].sector_id = dock
        universe.sectors[dock].occupant_ids.append("A")
    result = _act(universe, "A", ActionKind.POST_REWARD, target_id="B", amount=1000)
    assert result.ok
    assert universe.players["A"].alignment == 16
    assert universe.players["A"].experience == 3


def test_string_one_on_the_mode_itself_does_not_turn_it_on(monkeypatch):
    monkeypatch.setattr(K, "BOUNTY_GOOD_MODE", "1")
    assert K.bounty_good_live() is False


def test_genesis_rolls_a_class_and_ignores_a_requested_one(monkeypatch):
    universe = generate_universe(
        GameConfig(seed=16307, universe_size=40, enable_ferrengi=False, enable_planets=False)
    )
    player = _seat(universe)
    player.sector_id = _deep_sector(universe)
    player.planet_landed = None
    player.ship.genesis = 1
    player.turns_today = 0
    seen: dict[str, float] = {}

    def _pick(_rng, weights):
        seen.update(weights)
        return "K"

    monkeypatch.setattr("tw2k.engine.runner._weighted_choice", _pick)
    result = apply_action(
        universe, "P1", Action(kind=ActionKind.DEPLOY_GENESIS, args={"class": "M"})
    )
    assert result.ok, result.error
    planet = next(item for item in universe.planets.values() if item.origin == "genesis")
    assert planet.class_id == PlanetClass.K
    assert set(seen) == set(K.PLANET_CLASS_WEIGHTS)
    assert K.planet_class_live() is False
    assert "planet_class_live" not in K.V311_PROFILE_HELPERS


def test_printed_experience_sources_are_the_stored_awards():
    assert K.rank_tw2002() is True
    assert K.xp_award("trade") == 1
    assert K.xp_award("first_dock") == 1
    assert K.xp_award("daily") == 1
    assert K.xp_award("deploy_genesis") == 25
    assert K.xp_award("destroy_port") == 50
    assert K.KILL_EXP_SHARE == 0.10
    assert K.DAILY_ALIGNMENT == 1
    universe = generate_universe(
        GameConfig(seed=16302, universe_size=30, enable_ferrengi=False, enable_planets=False)
    )
    player = _seat(universe)
    tick_day(universe)
    assert player.experience == 11
    assert player.alignment == 5


def test_corp_planet_and_report_helpers_follow_the_profile(monkeypatch):
    assert K.corp_planet_disband_v306() is False
    assert K.special_hull_rules_on() is False
    assert K.owner_hazard_notice_on() is False
    assert K.siege_report_on() is False
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.corp_planet_disband_v306() is True
    assert K.special_hull_rules_on() is True
    assert K.owner_hazard_notice_on() is True
    assert K.siege_report_on() is True


def test_the_fighter_owner_hears_the_hit_only_when_the_notice_is_on(monkeypatch):
    universe = generate_universe(
        GameConfig(seed=16304, universe_size=30, enable_ferrengi=False, enable_planets=False)
    )
    event = Event(
        seq=1,
        tick=1,
        day=1,
        kind=EventKind.COMBAT,
        actor_id="P2",
        sector_id=12,
        payload={
            "vs": "fighter_sector",
            "defender_owner": "P1",
            "sent": 10,
            "defender_losses": 4,
        },
        summary="fighters hit",
    )
    monkeypatch.setattr(K, "OWNER_HAZARD_NOTICE_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    assert _event_visible_to(event, "P1", universe) is False
    monkeypatch.setattr(K, "OWNER_HAZARD_NOTICE_MODE", "tw2002")
    assert _event_visible_to(event, "P1", universe) is True
    monkeypatch.setattr(K, "OWNER_HAZARD_NOTICE_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert _event_visible_to(event, "P1", universe) is True
    assert _event_visible_to(event, "P2", universe) is True
