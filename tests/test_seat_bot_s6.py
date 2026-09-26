"""Seat-bot S6 - SeatBrain consumes rivals, recent events/failures, orphaned planets.

All inputs are fields of the seat's own observation:
* rivals[] (public net worth) and witnessed empire events -> race pressure
  pulls genesis / citadel rungs forward, still gated by legality and credits.
* recent_events (own agent_error / warp_blocked / trade_failed) and the
  engine's recent_failures -> no blind identical retry; repeated failures
  shelve the verb for the day.
* orphaned_planets -> claim_planet only while landed on a LISTED orphan and
  claim_planet is legal; never on an unlisted planet.
"""

from __future__ import annotations

import copy

from tw2k.agents.seat_acceptance import synthetic_obs, validate_action
from tw2k.agents.seat_brain import SeatBrain
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import EventKind, Player
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import apply_action


def _set_la(obs, kind, legal=True, reason=None, **params):
    obs["legal_actions"] = [la for la in obs["legal_actions"] if la["kind"] != kind]
    obs["legal_actions"].append({"kind": kind, "legal": legal, "reason": None if legal else reason,
                                 "detail": "precise", "params": params})
    return obs


def _rival(nw, pid="P2", name="KimiC"):
    return {"id": pid, "name": name, "alive": True, "net_worth": nw, "ship_class": "cargotran", "deaths": 0}


def _stardock_merchant(credits=50_000):
    obs = synthetic_obs(sector=1, credits=credits, ship_class="merchant_cruiser", holds=20)
    obs["self_id"] = "P1"
    obs["net_worth"] = credits
    return _set_la(obs, "buy_ship", ship_class={"choices": ["cargotran", "merchant_cruiser"],
                                                "net_cost_by": {"cargotran": 33_175}, "trade_in": 10_325})


# ---------------------------------------------------------------------------
# (a) rival pressure
# ---------------------------------------------------------------------------


def _away_from_buildable_world(credits: int):
    """In space at sector 5; our world (planet 7, sector 4) can start L1 now.

    2,100 colonists, above the 1,000-colonist L1 cost, so the build is legal
    whether or not a growth floor is enabled.
    """
    world = {"id": 7, "sector_id": 4, "name": "G", "class": "M", "origin": "genesis", "citadel_level": 0,
             "citadel_target": 0, "colonists": {"fuel_ore": 1200, "organics": 500, "equipment": 200, "colonists": 200}}
    obs = synthetic_obs(sector=5, planets=[world], credits=credits)
    obs["self_id"], obs["net_worth"] = "P1", 60_000
    return obs


def test_trailing_rival_pulls_citadel_build_forward() -> None:
    # 9k credits: enough for L1 (5k) but under L1 + working capital (13k).
    calm = SeatBrain().decide(_away_from_buildable_world(9_000))
    assert not (calm["kind"] == "plot_course" and calm["args"].get("target") == 4), calm  # calm: keep working capital

    obs = _away_from_buildable_world(9_000)
    obs["rivals"] = [_rival(300_000)]
    brain = SeatBrain()
    a = brain.decide(obs)
    assert validate_action(obs, a) == []
    assert a["kind"] == "plot_course" and a["args"] == {"target": 4, "execute": True}, a
    assert brain.pressure["leader"] == "P2" and "trailing P2" in a["goal_medium"]


def test_pressure_still_respects_credits_and_legality() -> None:
    obs = _away_from_buildable_world(4_000)  # cannot pay for L1 at all
    obs["rivals"] = [_rival(300_000)]
    a = SeatBrain().decide(obs)
    assert validate_action(obs, a) == []
    assert "citadel buildable" not in a["thought"]  # no build trip it cannot pay for
    # Rival not meaningfully ahead -> no pressure.
    obs2 = _away_from_buildable_world(9_000)
    obs2["rivals"] = [_rival(62_000)]
    brain = SeatBrain()
    brain.decide(obs2)
    assert brain.pressure is None


def test_pressure_never_trades_the_hull_for_an_earlier_genesis() -> None:
    """Measured: genesis-before-CargoTran lost 5-140k NW by day 6 on every offline seed tried."""
    for rivals in ([], [_rival(500_000)]):
        obs = _stardock_merchant()
        obs["rivals"] = rivals
        assert SeatBrain().decide(obs)["kind"] == "buy_ship"


def test_witnessed_rival_empire_event_is_pressure_only_without_a_world() -> None:
    ev = {"seq": 5, "kind": "genesis_deployed", "actor_id": "P2", "summary": "KimiC detonated a Genesis",
          "facts": {"planet_id": 3}}
    obs = _unmapped(30_500)
    obs["rivals"] = [_rival(30_000)]  # not ahead on net worth
    obs["recent_events"] = [ev]
    brain = SeatBrain()
    assert brain.decide(obs)["args"].get("target") == 1 and brain.pressure["empire_signals"] == ["genesis_deployed"]
    own = {"seq": 6, "kind": "genesis_deployed", "actor_id": "P1", "summary": "we did", "facts": {}}
    obs2 = _unmapped(30_500)
    obs2["recent_events"] = [own]
    brain2 = SeatBrain()
    brain2.decide(obs2)
    assert brain2.pressure is None  # our own empire events are not rival pressure


def _unmapped(credits):
    obs = synthetic_obs(sector=4, credits=credits)
    obs["known_warps"] = {"4": [3, 5], "3": [4], "5": [4]}
    obs["known_sectors"] = [{"id": s} for s in (3, 4, 5)]
    obs["self_id"], obs["net_worth"] = "P1", credits
    return obs


def test_genesis_money_while_unmapped_autopilots_to_stardock() -> None:
    # N1: below CargoTran / genesis affordability, do not hunt sector 1.
    poor = SeatBrain().decide(_unmapped(10_000))
    assert poor["kind"] == "warp" and poor["args"].get("target") != 1
    rich = SeatBrain().decide(_unmapped(40_000))
    assert rich["kind"] == "plot_course" and rich["args"] == {"target": 1, "execute": True}
    # genesis (25k) + L1 (5k) autopilots even when sector 1 is unmapped.
    assert SeatBrain().decide(_unmapped(30_500))["args"] == {"target": 1, "execute": True}
    short = _unmapped(29_000)
    assert SeatBrain().decide(copy.deepcopy(short))["args"].get("target") != 1
    # Pressure lowers the bar to the torpedo price, not below it.
    press = _unmapped(26_000)
    press["rivals"] = [_rival(300_000)]
    assert SeatBrain().decide(press)["args"].get("target") == 1
    broke = _unmapped(5_000)
    broke["rivals"] = [_rival(300_000)]
    broke_action = SeatBrain().decide(broke)
    assert broke_action["kind"] == "warp" and broke_action["args"].get("target") != 1


# ---------------------------------------------------------------------------
# (b) failure replanning
# ---------------------------------------------------------------------------


def _landed_buildable():
    world = {"id": 7, "sector_id": 5, "name": "G", "class": "M", "origin": "genesis", "citadel_level": 0,
             "citadel_target": 0, "colonists": {"fuel_ore": 1000, "organics": 625, "equipment": 375, "colonists": 500}}
    obs = synthetic_obs(sector=5, planets=[world], landed=7)
    obs["self_id"] = "P1"
    return obs


def _err(seq, actor="P1", verb="build_citadel", error="need 5000cr"):
    return {"seq": seq, "kind": "agent_error", "actor_id": actor, "summary": f"[Seat] invalid action: {error}",
            "facts": {"error": error}}


def test_rejected_action_is_not_retried_blindly() -> None:
    brain = SeatBrain()
    first = brain.decide(_landed_buildable())
    assert first["kind"] == "build_citadel"
    again = _landed_buildable()
    again["recent_events"] = [_err(10)]
    second = brain.decide(again)
    assert (second["kind"], second["args"].get("planet_id")) != ("build_citadel", 7)
    assert validate_action(again, second) == []
    assert "replanned" in second["thought"] and brain.mem.replans == 1
    # The same old event does not count twice.
    third = brain.decide(copy.deepcopy(again))
    assert brain.mem.replans == 1 and third["kind"] != "build_citadel"


def test_other_seats_failures_are_ignored() -> None:
    brain = SeatBrain()
    brain.decide(_landed_buildable())
    obs = _landed_buildable()
    obs["recent_events"] = [_err(10, actor="P2")]
    assert brain.decide(obs)["kind"] == "build_citadel" and brain.mem.replans == 0


def test_repeated_failures_shelve_the_verb_for_the_day() -> None:
    brain = SeatBrain()
    brain.decide(_landed_buildable())
    o = _landed_buildable()
    o["recent_events"] = [_err(10)]
    brain.decide(o)
    # Force another attempt of the same verb after the per-action ban expires.
    brain.mem.banned.clear()
    brain.mem.last_action_sig = "build_citadel:7"
    o2 = _landed_buildable()
    o2["recent_events"] = [_err(10), _err(11)]
    a = brain.decide(o2)
    assert brain.mem.banned_kinds.get("build_citadel") == 1 and a["kind"] != "build_citadel"
    nextday = _landed_buildable()
    nextday["day"] = 2
    assert brain.decide(nextday)["kind"] == "build_citadel"  # a new day gets a fresh try


def test_warp_blocked_fact_bans_that_target_even_for_exploration() -> None:
    obs = synthetic_obs(sector=4, credits=5_000)  # poor, mapped: brain explores lowest-id warp (3)
    obs["self_id"] = "P1"
    assert SeatBrain().decide(copy.deepcopy(obs))["args"].get("target") == 3
    obs["recent_events"] = [{"seq": 4, "kind": "warp_blocked", "actor_id": "P1", "summary": "blocked",
                             "facts": {"target": 3}}]
    a = SeatBrain().decide(obs)
    assert a["kind"] in ("warp", "plot_course", "scan", "wait") and a["args"].get("target") != 3


def test_engine_recent_failures_shelve_verb() -> None:
    obs = _landed_buildable()
    obs["recent_failures"] = [{"kind": "agent_error", "target_label": "build_citadel rejected", "count": 3,
                               "last_summary": "x", "last_day": 1, "last_tick": 9}]
    a = SeatBrain().decide(obs)
    assert a["kind"] != "build_citadel"


def test_engine_aggregates_rejections_by_verb() -> None:
    u = generate_universe(GameConfig(seed=4, universe_size=40, max_days=2, turns_per_day=50))
    u.players["P1"] = Player(id="P1", name="Seat", agent_kind="external", sector_id=1)
    u.sectors[1].occupant_ids.append("P1")
    for _ in range(2):  # what server/runner.py emits for a rejected action
        u.emit(EventKind.AGENT_ERROR, actor_id="P1", sector_id=1,
               payload={"error": "no such planet", "action": {"kind": "land_planet", "args": {}}},
               summary="[Seat] invalid action: no such planet")
    rows = build_observation(u, "P1").recent_failures
    assert any(r["target_label"] == "land_planet rejected" and r["count"] == 2 for r in rows), rows


# ---------------------------------------------------------------------------
# (c) orphan claim gate
# ---------------------------------------------------------------------------


def _orphan(pid=9, sector=5, citadel=1):
    return {"id": pid, "sector_id": sector, "name": "Old Keep", "class": "M", "citadel_level": citadel,
            "fighters": 40, "shields": 0, "former_owner_id": "P3"}


def _landed_on(pid, *, listed, claim_legal=True, credits=10_000):
    obs = synthetic_obs(sector=5, credits=credits)
    obs["self_id"] = "P1"
    obs["planet_landed"] = pid
    obs["orphaned_planets"] = [_orphan(pid)] if listed else []
    _set_la(obs, "liftoff")
    _set_la(obs, "claim_planet", claim_legal, "planet is neutral, not a former-player orphan",
            planet_id={"choices": [pid]})
    return obs


def test_claims_only_listed_orphan_when_landed_and_legal() -> None:
    obs = _landed_on(9, listed=True)
    a = SeatBrain().decide(obs)
    assert a["kind"] == "claim_planet" and a["args"] == {"planet_id": 9}
    assert validate_action(obs, a) == []


def test_never_claims_unlisted_planet_even_if_verb_reports_legal() -> None:
    a = SeatBrain().decide(_landed_on(9, listed=False, claim_legal=True))
    assert a["kind"] != "claim_planet"


def test_never_claims_when_claim_is_illegal() -> None:
    a = SeatBrain().decide(_landed_on(9, listed=True, claim_legal=False))
    assert a["kind"] != "claim_planet"


def test_lands_on_listed_orphan_only_when_it_beats_genesis() -> None:
    obs = synthetic_obs(sector=5, credits=8_000)
    obs["self_id"] = "P1"
    obs["orphaned_planets"] = [_orphan(9, citadel=0)]
    _set_la(obs, "land_planet", planet_id={"choices": [9], "contested": []})
    a = SeatBrain().decide(copy.deepcopy(obs))
    assert a["kind"] == "land_planet" and a["args"] == {"planet_id": 9}  # no world + genesis unaffordable
    # Same empty orphan but we already run a genesis world and are not under pressure: skip it.
    world = {"id": 7, "sector_id": 4, "name": "G", "class": "M", "origin": "genesis", "citadel_level": 1,
             "citadel_target": 1, "colonists": {"fuel_ore": 1500}, "colonists_total": 1500}
    obs2 = copy.deepcopy(obs)
    obs2["owned_planets"] = [world]
    assert SeatBrain().decide(obs2)["kind"] != "land_planet" or SeatBrain().decide(obs2)["args"]["planet_id"] != 9
    # An orphan that carries a citadel is always worth inheriting.
    obs3 = copy.deepcopy(obs2)
    obs3["orphaned_planets"] = [_orphan(9, citadel=2)]
    a3 = SeatBrain().decide(obs3)
    assert a3["kind"] == "land_planet" and a3["args"] == {"planet_id": 9}


def test_offline_engine_orphan_inherit_end_to_end() -> None:
    u = generate_universe(GameConfig(seed=31, universe_size=90, max_days=3, turns_per_day=200,
                                     starting_credits=8_000, enable_ferrengi=False, enable_planets=True))
    for pid in ("P1", "P3"):
        u.players[pid] = Player(id=pid, name=pid, agent_kind="external", sector_id=1, credits=8_000)
        u.sectors[1].occupant_ids.append(pid)
    pl = next(iter(u.planets.values()))
    pl.owner_id, pl.corp_ticker, pl.citadel_level, pl.fighters = None, None, 1, 25
    u.emit(EventKind.PLANET_ORPHANED, actor_id="P3", sector_id=pl.sector_id,
           payload={"planet_id": pl.id, "planet_name": pl.name, "former_owner": "P3"}, summary="orphaned")
    u.sectors[1].occupant_ids.remove("P1")
    u.players["P1"].sector_id = pl.sector_id
    u.sectors[pl.sector_id].occupant_ids.append("P1")

    brain = SeatBrain()
    kinds = []
    for _ in range(4):
        obs = build_observation(u, "P1")
        a = brain.decide(obs)
        assert validate_action(obs.model_dump(mode="json"), a) == [], a
        kinds.append(a["kind"])
        assert apply_action(u, "P1", Action(**a)).ok
        if a["kind"] == ActionKind.CLAIM_PLANET.value:
            break
    assert kinds[:2] == ["land_planet", "claim_planet"], kinds
    assert pl.owner_id == "P1" and pl.origin == "claim"
    home = build_observation(u, "P1")
    assert brain.decide(home) and brain.mem.home_planet == pl.id  # inherited citadel world becomes home
