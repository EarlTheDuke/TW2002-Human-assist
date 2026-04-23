"""Smoke tests for the TW2K-AI engine.

These verify the core invariants: universe generation is deterministic and
connected; trading and movement apply correctly; agents can play a short
match without raising.
"""

from __future__ import annotations

import asyncio

from tw2k.agents import HeuristicAgent
from tw2k.engine import (
    Action,
    ActionKind,
    GameConfig,
    apply_action,
    build_observation,
    generate_universe,
    is_finished,
    tick_day,
)
from tw2k.engine.models import Player, Ship


def _build_universe_with_agent():
    config = GameConfig(seed=123, universe_size=300, max_days=2)
    u = generate_universe(config)
    p = Player(id="P1", name="Test", ship=Ship())
    u.players["P1"] = p
    u.sectors[1].occupant_ids.append("P1")
    p.known_sectors.add(1)
    return u, p


def test_universe_generation_is_deterministic():
    a = generate_universe(GameConfig(seed=42, universe_size=200))
    b = generate_universe(GameConfig(seed=42, universe_size=200))
    assert [s.warps for s in a.sectors.values()] == [s.warps for s in b.sectors.values()]


def test_universe_is_fully_reachable_from_sector_1():
    u = generate_universe(GameConfig(seed=7, universe_size=500))
    visited = {1}
    stack = [1]
    while stack:
        cur = stack.pop()
        for w in u.sectors[cur].warps:
            if w not in visited:
                visited.add(w)
                stack.append(w)
    assert len(visited) == 500


def test_stardock_is_in_sector_one():
    u = generate_universe(GameConfig(seed=1, universe_size=100))
    assert u.sectors[1].port is not None
    assert u.sectors[1].port.class_id.name == "STARDOCK"


def test_warp_costs_turns_and_updates_position():
    u, p = _build_universe_with_agent()
    target = u.sectors[1].warps[0]
    result = apply_action(u, "P1", Action(kind=ActionKind.WARP, args={"target": target}))
    assert result.ok is True
    assert p.sector_id == target
    # Merchant Cruiser's per-ship turns_per_warp is 3 (per K.SHIP_SPECS)
    assert p.turns_today == 3


def test_warp_to_non_adjacent_fails():
    u, p = _build_universe_with_agent()
    bad = 999 if 999 not in u.sectors[1].warps else 888
    result = apply_action(u, "P1", Action(kind=ActionKind.WARP, args={"target": bad}))
    assert result.ok is False
    assert p.sector_id == 1


def test_fedspace_disallows_attack():
    u, _ = _build_universe_with_agent()
    u.players["P2"] = Player(id="P2", name="Other", ship=Ship(), sector_id=1)
    u.sectors[1].occupant_ids.append("P2")
    result = apply_action(u, "P1", Action(kind=ActionKind.ATTACK, args={"target": "P2"}))
    assert result.ok is False


def test_corp_create_requires_funds_and_stardock():
    u, p = _build_universe_with_agent()
    p.credits = 499_000
    result = apply_action(u, "P1", Action(kind=ActionKind.CORP_CREATE, args={"ticker": "ABC"}))
    assert result.ok is False


def test_day_tick_resets_turns_and_advances_day():
    u, p = _build_universe_with_agent()
    p.turns_today = 500
    prev_day = u.day
    tick_day(u)
    assert u.day == prev_day + 1
    assert p.turns_today == 0


def test_heuristic_agent_plays_short_match_without_error():
    config = GameConfig(seed=99, universe_size=200, max_days=1)
    u = generate_universe(config)
    a = Player(id="A", name="Alice", ship=Ship())
    b = Player(id="B", name="Bob", ship=Ship())
    u.players["A"] = a
    u.players["B"] = b
    u.sectors[1].occupant_ids.extend(["A", "B"])
    a.known_sectors.add(1)
    b.known_sectors.add(1)
    agents = [HeuristicAgent("A", "Alice"), HeuristicAgent("B", "Bob")]

    async def run():
        idx = 0
        steps = 0
        while not is_finished(u) and steps < 1000:
            agent = agents[idx]
            player = u.players[agent.player_id]
            if player.turns_today >= player.turns_per_day:
                if all(u.players[a.player_id].turns_today >= u.players[a.player_id].turns_per_day for a in agents):
                    tick_day(u)
                idx = (idx + 1) % len(agents)
                continue
            obs = build_observation(u, agent.player_id)
            action = await agent.act(obs)
            apply_action(u, agent.player_id, action)
            idx = (idx + 1) % len(agents)
            steps += 1

    asyncio.run(run())
    # If we got here without exceptions, the match is sane
    assert u.day >= 1


def test_observation_respects_visibility():
    config = GameConfig(seed=5, universe_size=100)
    u = generate_universe(config)
    a = Player(id="A", name="A", ship=Ship(), sector_id=1)
    b = Player(id="B", name="B", ship=Ship(), sector_id=50)
    u.players["A"] = a
    u.players["B"] = b
    obs = build_observation(u, "A")
    # B should appear but without sector info unless visible
    other = next(o for o in obs.other_players if o["id"] == "B")
    assert other["is_corpmate"] is False
    # B is in a different sector — no sector_id leaked unless in corp
    assert "sector_id" not in other


# ---------------------------------------------------------------------------
# Combat regression tests (added after match 2 bug M2-1: `_resolve_ship_combat`
# crashed on the first PvP kill because both Player and FerrengiShip carry
# `alive: bool`, so the old `hasattr(target, "alive")` discriminator matched
# every target and ran the Ferrengi branch against a Player).
# ---------------------------------------------------------------------------

def _combat_arena(attacker_sector: int = 50):
    """Two players co-located OUTSIDE FedSpace (sectors 1-10 are federated).

    Returns (universe, attacker, defender). attacker = "A", defender = "B".
    """
    from tw2k.engine import constants as K

    assert attacker_sector not in K.FEDSPACE_SECTORS, (
        "combat arena must be outside FedSpace"
    )
    u = generate_universe(GameConfig(seed=123, universe_size=300, max_days=2))
    a = Player(id="A", name="Attacker", ship=Ship(), sector_id=attacker_sector)
    b = Player(id="B", name="Defender", ship=Ship(), sector_id=attacker_sector)
    u.players["A"] = a
    u.players["B"] = b
    u.sectors[attacker_sector].occupant_ids.extend(["A", "B"])
    a.known_sectors.add(attacker_sector)
    b.known_sectors.add(attacker_sector)
    return u, a, b


def test_pvp_kill_respawns_victim_without_crash():
    """An overwhelming PvP kill must NOT crash, and the victim must respawn
    via `_destroy_ship` (eject to StarDock, death count +1, credit penalty,
    ship downgrade to Merchant Cruiser). Regression for match 2 bug M2-1.
    """
    from tw2k.engine import constants as K

    u, atk, vic = _combat_arena(attacker_sector=50)
    atk.ship.fighters = 8000
    atk.ship.shields = 3000
    vic.ship.fighters = 20
    vic.ship.shields = 0
    vic.credits = 10_000
    vic.deaths = 0
    pre_xp = atk.experience

    result = apply_action(u, "A", Action(kind=ActionKind.ATTACK, args={"target": "B"}))

    assert result.ok is True, f"attack returned not-ok: {result.error!r}"
    # Victim was routed through _destroy_ship (NOT the Ferrengi branch).
    assert vic.alive is True, "victim should respawn, not be permanently dead"
    assert vic.deaths == 1
    assert vic.sector_id == K.STARDOCK_SECTOR, "victim should eject to StarDock"
    assert vic.ship.fighters == K.STARTING_FIGHTERS, "ship should downgrade"
    assert vic.ship.holds == K.STARTING_HOLDS
    # 75% credit retention is the canonical respawn tax.
    assert vic.credits == int(10_000 * 0.75)
    # Attacker picked up PvP XP.
    assert atk.experience > pre_xp, "attacker should gain kill_player XP"
    # Attacker keeps most of their fighter pool.
    assert atk.ship.fighters > 7000


def test_pvp_kill_elimination_after_max_deaths():
    """After MAX_DEATHS_BEFORE_ELIM deaths the victim should stop respawning
    and be flagged `alive = False`. Exercises the other branch of
    `_destroy_ship`.
    """
    from tw2k.engine import constants as K

    u, atk, vic = _combat_arena(attacker_sector=50)
    vic.deaths = K.MAX_DEATHS_BEFORE_ELIM - 1  # one hit away from out
    atk.ship.fighters = 8000
    atk.ship.shields = 3000
    vic.ship.fighters = 20
    vic.ship.shields = 0

    result = apply_action(u, "A", Action(kind=ActionKind.ATTACK, args={"target": "B"}))
    assert result.ok is True
    assert vic.deaths == K.MAX_DEATHS_BEFORE_ELIM
    assert vic.alive is False, "victim should be permanently eliminated"


def test_ferrengi_kill_pays_bounty_and_alignment():
    """Killing a Ferrengi must pay bounty, bump alignment by +10, and mark
    the Ferrengi as destroyed. Guards the legitimate Ferrengi branch we
    tightened in match 2.
    """
    from tw2k.engine import constants as K
    from tw2k.engine.models import FerrengiShip, ShipClass

    u, atk, _ = _combat_arena(attacker_sector=50)
    # Drop a weak Ferrengi into A's sector.
    ferr = FerrengiShip(
        id="ferr_test_1",
        name="Ferrengi Raider _test",
        sector_id=50,
        aggression=3,
        fighters=20,
        shields=0,
        ship_class=ShipClass.MERCHANT_CRUISER,
    )
    u.ferrengi[ferr.id] = ferr
    atk.ship.fighters = 8000
    atk.ship.shields = 3000
    pre_credits = atk.credits
    pre_align = atk.alignment

    result = apply_action(
        u, "A", Action(kind=ActionKind.ATTACK, args={"target": ferr.name})
    )
    assert result.ok is True
    assert ferr.alive is False
    expected_bounty = K.FERRENGI_BOUNTY_PER_AGG * 3
    assert atk.credits == pre_credits + expected_bounty
    assert atk.alignment == pre_align + 10


def test_pvp_kill_in_fedspace_blocked_and_penalized():
    """Sanity: attacking a player in FedSpace is refused and costs alignment
    but NEVER mutates the defender — guards against any future partial-state
    regression.
    """
    u, atk, vic = _combat_arena(attacker_sector=50)
    # Move both into FedSpace sector 1.
    atk.sector_id = 1
    vic.sector_id = 1
    u.sectors[50].occupant_ids.clear()
    u.sectors[1].occupant_ids.extend(["A", "B"])
    atk.ship.fighters = 8000
    vic.ship.fighters = 20
    pre_align = atk.alignment
    pre_fighters = vic.ship.fighters

    result = apply_action(u, "A", Action(kind=ActionKind.ATTACK, args={"target": "B"}))
    assert result.ok is False
    assert atk.alignment < pre_align, "FedSpace combat should penalize attacker"
    assert vic.ship.fighters == pre_fighters, "defender must not be touched"
    assert vic.alive is True


def test_play_to_day_cap_suppresses_elimination_win():
    """With `play_to_day_cap=True` the elimination check must NOT trip
    when only one player is left alive. The survivor keeps playing solo
    until day cap; `universe.finished` stays False, `winner_id` empty,
    `win_reason` empty. Regression for the Match 3 early-stop:
    Commodore Eris Vahn won by elimination on day ~1 instead of the
    match running its full 365 days.
    """
    from tw2k.engine.models import EventKind
    from tw2k.engine.victory import check_victory

    u = generate_universe(GameConfig(seed=1, universe_size=50, max_days=365))
    u.config.play_to_day_cap = True
    u.players["A"] = Player(id="A", name="Alpha", ship=Ship(), alive=True)
    u.players["B"] = Player(id="B", name="Beta",  ship=Ship(), alive=False)
    u.players["C"] = Player(id="C", name="Gamma", ship=Ship(), alive=False)

    check_victory(u)

    assert u.finished is False, "elimination win must be suppressed"
    assert u.winner_id in ("", None)
    assert u.win_reason in ("", None)
    over = [e for e in u.events if e.kind == EventKind.GAME_OVER]
    assert over == [], "no GAME_OVER event should be emitted"


def test_play_to_day_cap_still_ends_on_total_wipeout():
    """Even with `play_to_day_cap=True`, if EVERY player is dead the
    match must stop immediately with `win_reason='no_survivors'` —
    otherwise the scheduler idles until day cap with nobody to play.
    """
    from tw2k.engine.models import EventKind
    from tw2k.engine.victory import check_victory

    u = generate_universe(GameConfig(seed=1, universe_size=50, max_days=365))
    u.config.play_to_day_cap = True
    u.players["A"] = Player(id="A", name="Alpha", ship=Ship(), alive=False)
    u.players["B"] = Player(id="B", name="Beta",  ship=Ship(), alive=False)

    check_victory(u)

    assert u.finished is True
    assert u.win_reason == "no_survivors"
    assert u.winner_id in ("", None), "no_survivors has no winner"
    over = [e for e in u.events if e.kind == EventKind.GAME_OVER]
    assert len(over) == 1
    assert over[0].payload.get("reason") == "no_survivors"


def test_play_to_day_cap_suppresses_economic_win():
    """With `play_to_day_cap=True` the credits-threshold sudden-death is
    also suppressed: a player sitting on a billion credits keeps playing
    until day cap.
    """
    from tw2k.engine.models import EventKind
    from tw2k.engine.victory import check_victory

    u = generate_universe(GameConfig(seed=1, universe_size=50, max_days=365))
    u.config.play_to_day_cap = True
    rich = Player(id="A", name="Alpha", ship=Ship(), alive=True)
    rich.credits = 999_999_999
    u.players["A"] = rich
    u.players["B"] = Player(id="B", name="Beta", ship=Ship(), alive=True)

    check_victory(u)

    assert u.finished is False
    over = [e for e in u.events if e.kind == EventKind.GAME_OVER]
    assert over == [], "economic sudden-death must be suppressed"


def test_default_config_still_ends_on_elimination():
    """Guard: the default config (play_to_day_cap=False) must keep the
    classic elimination win so existing behaviour is unchanged.
    """
    from tw2k.engine.models import EventKind
    from tw2k.engine.victory import check_victory

    u = generate_universe(GameConfig(seed=1, universe_size=50, max_days=30))
    u.players["A"] = Player(id="A", name="Alpha", ship=Ship(), alive=True)
    u.players["B"] = Player(id="B", name="Beta",  ship=Ship(), alive=False)

    check_victory(u)

    assert u.finished is True
    assert u.win_reason == "elimination"
    assert u.winner_id == "A"
    over = [e for e in u.events if e.kind == EventKind.GAME_OVER]
    assert len(over) == 1
