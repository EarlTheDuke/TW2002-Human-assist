"""death-escape-pods-v1: escape pods, Ship Destroyed, pods per day. Real engine path.

Rules: docs/playtests/combat/DEATH_ESCAPE_PODS.md. Numbers are hardcoded on purpose
(10 and 50 percent, 2 pods a day, pod 6 turns per warp and 50 fighters, 5 holds);
the test does not read them back from constants.
"""

from __future__ import annotations

import itertools
import random
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tests.test_phase_abc import _first_non_fed_sector, _make_universe
from tw2k.agents.seat_acceptance import validate_action
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.combat import _destroy_ship
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import (
    Commodity,
    EventKind,
    FerrengiShip,
    FighterDeployment,
    FighterMode,
    MineDeployment,
    MineType,
    Planet,
    PlanetClass,
    ShipClass,
)
from tw2k.engine.observation import build_observation, event_facts
from tw2k.engine.runner import apply_action, tick_day

ROOT = Path(__file__).resolve().parents[1]
HULLS = [c for c in ShipClass if c is not ShipClass.ESCAPE_POD]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _park(u, player, sid: int) -> None:
    here = u.sectors[player.sector_id]
    if player.id in here.occupant_ids:
        here.occupant_ids.remove(player.id)
    player.sector_id = sid
    player.planet_landed = None
    player.turns_today = 0
    if player.id not in u.sectors[sid].occupant_ids:
        u.sectors[sid].occupant_ids.append(player.id)


def _la(u, pid: str, kind: str):
    return {la.kind: la for la in legal_actions(u, pid)}[kind]


def _act(u, pid: str, kind: ActionKind, **args):
    return apply_action(u, pid, Action(kind=kind, args=args))


def _last(u, kind: EventKind):
    return next(e for e in reversed(u.events) if e.kind is kind)


def _clear(u, *sids: int) -> None:
    for sid in sids:
        u.sectors[sid].fighters = None
        u.sectors[sid].mines = []


def _line(u, start: int, n: int) -> list[int]:
    """A private corridor start -> s1 -> ... -> sn, cut off from the rest of the map.

    Every sector keeps only its corridor neighbours, so the safe path can only walk it.
    """
    pool = [sid for sid in sorted(u.sectors) if sid >= 60 and sid not in K.FEDSPACE_SECTORS and sid != start]
    chain = [start] + pool[:n]
    for sid in chain:
        u.sectors[sid].warps = []
        _clear(u, sid)
    for a, b in itertools.pairwise(chain):
        u.sectors[a].warps.append(b)
        u.sectors[b].warps.append(a)
    return chain


def _snap(p) -> tuple:
    return (p.sector_id, p.credits, p.ship.ship_class.value, p.ship.holds, p.ship.fighters, p.ship.shields,
            p.deaths, p.alive, p.experience, p.alignment, p.pods_today)


# ---------------------------------------------------------------------------
# rules table and switch
# ---------------------------------------------------------------------------


def test_rules_table_is_written_first() -> None:
    doc = (ROOT / "docs" / "playtests" / "combat" / "DEATH_ESCAPE_PODS.md").read_text(encoding="utf-8")
    for mark in ("CONFIRMED", "SOURCE-CONFLICT", "UNVERIFIED"):
        assert mark in doc
    for row in range(1, 21):
        assert f"| d{row} |" in doc, row
    for words in ("pods.html", "safe path", "previous sector", "10 percent", "50 percent", "Two pods a day",
                  "Scout", "DEATH_MODE", "elimination_deaths", "Deliberate differences", "credits x0.75"):
        assert words in doc, words


def test_switch_defaults_and_the_pod_hull() -> None:
    assert K.DEATH_MODE == "tw2002"
    assert "escape_pod" not in K.ship_specs()
    assert "escape_pod" not in K.SHIP_SPECS
    pod = K.hull_spec("escape_pod")
    assert pod["turns_per_warp"] == 6 and pod["max_fighters"] == 50 and pod["fighters_per_attack"] == 10
    assert pod["max_shields"] == 50 and pod["max_holds"] == 50 and pod["holds"] == 5 and pod["max_mines"] == 0
    assert K.combat_hull("escape_pod") == (0.6, 10)
    assert K.ship_cost("escape_pod") == 0
    assert K.trade_in_credit("escape_pod") == K.ship_cost("scout_marauder")
    assert K.net_hull_cost("escape_pod", "scout_marauder") == 0


# ---------------------------------------------------------------------------
# the pod
# ---------------------------------------------------------------------------


def test_self_inflicted_loss_puts_the_pod_in_the_previous_sector() -> None:
    u, (a, b, c) = _make_universe(seed=36101)
    home = _first_non_fed_sector(u, 40)
    dest = next(w for w in u.sectors[home].warps if w not in K.FEDSPACE_SECTORS)
    _clear(u, home, dest)
    _park(u, a, home)
    a.ship.fighters, a.ship.shields = 0, 0
    a.ship.cargo[Commodity.ORGANICS] = 10
    a.ship.genesis, a.ship.ether_probes = 1, 2
    a.credits, a.experience, a.alignment = 4000, 1234, -77
    u.sectors[dest].mines = [MineDeployment(owner_id=b.id, kind=MineType.ARMID, count=40)]
    res = _act(u, a.id, ActionKind.WARP, target=dest)
    assert res.ok
    # Mines are self-inflicted: the pod goes to the sector the warp left, not into the minefield.
    assert a.sector_id == home and a.id in u.sectors[home].occupant_ids and a.id not in u.sectors[dest].occupant_ids
    assert a.ship.ship_class is ShipClass.ESCAPE_POD
    assert a.credits == 4000  # credits stay
    assert a.experience == 1234 - 123 and a.alignment == -77  # 10 percent, rounded down; no alignment
    assert a.ship.holds == 5 and sum(a.ship.cargo.values()) == 0
    assert (a.ship.fighters, a.ship.shields, a.ship.genesis, a.ship.ether_probes) == (0, 0, 0, 0)
    assert a.deaths == 1 and a.alive and a.pods_today == 1
    ev = _last(u, EventKind.SHIP_DESTROYED)
    assert ev.payload["outcome"] == "escape_pod" and ev.payload["pod_sector"] == home
    assert ev.payload["exp_lost"] == 123


def test_no_previous_sector_leaves_the_pod_where_it_died() -> None:
    u, (a, b, c) = _make_universe(seed=36102)
    sid = _first_non_fed_sector(u)
    _park(u, a, sid)
    assert a.prev_sector_id is None
    _destroy_ship(u, a.id, reason="quasar", killer_id=b.id)
    assert a.sector_id == sid and a.ship.ship_class is ShipClass.ESCAPE_POD


def test_killed_by_another_player_walks_the_safe_path() -> None:
    u, (a, b, c) = _make_universe(seed=36103)
    start = _first_non_fed_sector(u, 40)
    chain = _line(u, start, 6)
    _park(u, a, start)
    a.prev_sector_id = chain[1]
    # Hostile fighters four hops out: the pod stops one short of them.
    u.sectors[chain[4]].fighters = FighterDeployment(owner_id=b.id, count=1, mode=FighterMode.DEFENSIVE)
    _destroy_ship(u, a.id, reason="combat", killer_id=b.id, by_other=True)
    assert a.sector_id == chain[3]
    assert a.ship.ship_class is ShipClass.ESCAPE_POD


def test_safe_path_counts_your_own_and_corp_fighters_as_safe() -> None:
    u, (a, b, c) = _make_universe(seed=36104)
    start = _first_non_fed_sector(u, 40)
    chain = _line(u, start, 6)
    _park(u, a, start)
    u.sectors[chain[1]].fighters = FighterDeployment(owner_id=a.id, count=5, mode=FighterMode.DEFENSIVE)
    a.corp_ticker = c.corp_ticker = "ZZZ"
    from tw2k.engine.models import Corporation
    u.corporations["ZZZ"] = Corporation(ticker="ZZZ", name="Z", ceo_id=a.id, member_ids=[a.id, c.id])
    u.sectors[chain[2]].fighters = FighterDeployment(owner_id=c.id, count=5, mode=FighterMode.DEFENSIVE)
    _destroy_ship(u, a.id, reason="combat", killer_id=b.id, by_other=True)
    assert a.sector_id == chain[6]


def test_surrounded_pod_stays_in_the_death_sector() -> None:
    u, (a, b, c) = _make_universe(seed=36105)
    start = _first_non_fed_sector(u, 40)
    chain = _line(u, start, 6)
    _park(u, a, start)
    u.sectors[chain[1]].fighters = FighterDeployment(owner_id=b.id, count=1, mode=FighterMode.OFFENSIVE)
    _destroy_ship(u, a.id, reason="combat", killer_id=b.id, by_other=True)
    assert a.sector_id == start


def test_pod_too_close_to_reach_three_hops_stays() -> None:
    # pods.html dead-end: no target 3+ hops away, so the pod cannot move.
    u, (a, b, c) = _make_universe(seed=36106)
    start = _first_non_fed_sector(u, 40)
    chain = _line(u, start, 2)
    _park(u, a, start)
    _destroy_ship(u, a.id, reason="ferrengi", killer_id="F1", by_other=True)
    assert a.sector_id == start and chain


def test_a_pod_meets_nothing_on_arrival() -> None:
    # The previous sector holds hostile defensive fighters and mines: no challenge, no damage.
    u, (a, b, c) = _make_universe(seed=36107)
    sid = _first_non_fed_sector(u, 40)
    prev = _first_non_fed_sector(u, sid + 1)
    _park(u, a, sid)
    a.prev_sector_id = prev
    u.sectors[prev].fighters = FighterDeployment(owner_id=b.id, count=500, mode=FighterMode.DEFENSIVE)
    u.sectors[prev].mines = [MineDeployment(owner_id=b.id, kind=MineType.ARMID, count=40)]
    _destroy_ship(u, a.id, reason="quasar", killer_id=b.id)
    assert a.sector_id == prev and a.fighter_challenge is None and a.deaths == 1
    assert u.sectors[prev].fighters.count == 500 and u.sectors[prev].mines[0].count == 40


def test_ferrengi_kill_is_by_someone_else() -> None:
    u, (a, b, c) = _make_universe(seed=36108)
    start = _first_non_fed_sector(u, 40)
    chain = _line(u, start, 5)
    _park(u, a, start)
    a.prev_sector_id = chain[1]
    a.ship.fighters, a.ship.shields = 1, 0
    from tw2k.engine.combat import _resolve_ship_combat_attacker_npc
    f = FerrengiShip(id="F9", name="Ferr", sector_id=start, fighters=5000, shields=500, aggression=5)
    u.ferrengi["F9"] = f
    _resolve_ship_combat_attacker_npc(u, f, a)
    assert a.ship.ship_class is ShipClass.ESCAPE_POD
    assert a.sector_id == chain[5]  # the far end of the corridor, not the previous sector


# ---------------------------------------------------------------------------
# Ship Destroyed and the pod limit
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("hull", [ShipClass.SCOUT_MARAUDER, ShipClass.ESCAPE_POD])
def test_a_podless_hull_is_ship_destroyed(hull: ShipClass) -> None:
    u, (a, b, c) = _make_universe(seed=36110)
    sid = _first_non_fed_sector(u)
    _park(u, a, sid)
    a.ship.ship_class = hull
    a.credits, a.experience, a.alignment = 777, 1001, -501
    a.turns_today = 10
    _destroy_ship(u, a.id, reason="combat", killer_id=b.id, by_other=True)
    assert a.alive and a.deaths == 1
    assert a.ship.ship_class is ShipClass.SCOUT_MARAUDER and a.sector_id == K.STARDOCK_SECTOR
    assert a.id in u.sectors[K.STARDOCK_SECTOR].occupant_ids and a.id not in u.sectors[sid].occupant_ids
    assert a.experience == 1001 - 500 and a.alignment == -501 + 250  # halfway to zero
    assert a.credits == 777
    assert a.turns_today == a.turns_per_day  # out until midnight
    assert a.pods_today == 0
    assert _last(u, EventKind.SHIP_DESTROYED).payload["outcome"] == "ship_destroyed"
    assert all(not la.legal or la.turn_cost == 0 for la in legal_actions(u, a.id))
    tick_day(u)
    assert a.turns_today == 0 and _la(u, a.id, "warp").legal


def test_third_loss_in_a_day_is_ship_destroyed_and_the_count_resets() -> None:
    u, (a, b, c) = _make_universe(seed=36111)
    sid = _first_non_fed_sector(u)
    a.experience = 1000
    outcomes = []
    for _ in range(3):
        _park(u, a, sid)
        a.ship.ship_class = ShipClass.BATTLESHIP
        _destroy_ship(u, a.id, reason="mines")
        outcomes.append(_last(u, EventKind.SHIP_DESTROYED).payload["outcome"])
    assert outcomes == ["escape_pod", "escape_pod", "ship_destroyed"]
    assert a.experience == ((1000 - 100) - 90) - 405
    assert a.deaths == 3 and a.alive  # no elimination in tw2002 by default
    tick_day(u)
    _park(u, a, sid)
    a.ship.ship_class = ShipClass.BATTLESHIP
    _destroy_ship(u, a.id, reason="mines")
    assert _last(u, EventKind.SHIP_DESTROYED).payload["outcome"] == "escape_pod" and a.pods_today == 1


def test_ship_destroyed_inside_an_action_never_runs_past_the_day() -> None:
    u, (a, b, c) = _make_universe(seed=36112)
    home = _first_non_fed_sector(u, 40)
    dest = next(w for w in u.sectors[home].warps if w not in K.FEDSPACE_SECTORS)
    _clear(u, home, dest)
    _park(u, a, home)
    a.ship.ship_class = ShipClass.SCOUT_MARAUDER
    a.ship.fighters, a.ship.shields = 0, 0
    u.sectors[dest].mines = [MineDeployment(owner_id=b.id, kind=MineType.ARMID, count=40)]
    res = _act(u, a.id, ActionKind.WARP, target=dest)
    assert res.ok and a.turns_today == a.turns_per_day
    assert a.sector_id == K.STARDOCK_SECTOR


# ---------------------------------------------------------------------------
# flying and trading in the pod
# ---------------------------------------------------------------------------


def _pod_at(u, a, sid: int) -> None:
    _park(u, a, sid)
    _destroy_ship(u, a.id, reason="quasar")
    assert a.ship.ship_class is ShipClass.ESCAPE_POD


def test_the_pod_flies_slow_and_carries_little() -> None:
    u, (a, b, c) = _make_universe(seed=36120)
    sid = _first_non_fed_sector(u)
    _pod_at(u, a, sid)
    target = u.sectors[sid].warps[0]
    _clear(u, target)
    warp = _la(u, a.id, "warp")
    assert warp.legal and warp.turn_cost == 6
    res = _act(u, a.id, ActionKind.WARP, target=target)
    assert res.ok and res.turns_spent == 6
    _park(u, a, K.STARDOCK_SECTOR)
    a.credits = 10**7
    equip = _la(u, a.id, "buy_equip")
    assert equip.params["qty"]["max_by"]["fighters"] == 50
    assert not _act(u, a.id, ActionKind.BUY_EQUIP, item="fighters", qty=51).ok
    assert _act(u, a.id, ActionKind.BUY_EQUIP, item="fighters", qty=50).ok and a.ship.fighters == 50
    assert not _act(u, a.id, ActionKind.BUY_EQUIP, item="armid_mines", qty=1).ok


def test_the_pod_trades_for_a_scout_at_no_cost() -> None:
    u, (a, b, c) = _make_universe(seed=36121)
    _pod_at(u, a, _first_non_fed_sector(u))
    _park(u, a, K.STARDOCK_SECTOR)
    a.credits = 0
    ship = _la(u, a.id, "buy_ship")
    assert ship.legal and "scout_marauder" in ship.params["ship_class"]["choices"]
    assert "escape_pod" not in ship.params["ship_class"]["choices"]
    assert ship.params["ship_class"]["net_cost_by"]["scout_marauder"] == 0
    assert not _act(u, a.id, ActionKind.BUY_SHIP, ship_class="escape_pod").ok
    res = _act(u, a.id, ActionKind.BUY_SHIP, ship_class="scout_marauder")
    assert res.ok and a.ship.ship_class is ShipClass.SCOUT_MARAUDER and a.credits == 0


def test_a_pod_buying_a_bigger_hull_pays_the_scout_credit_off() -> None:
    u, (a, b, c) = _make_universe(seed=36122)
    _pod_at(u, a, _first_non_fed_sector(u))
    _park(u, a, K.STARDOCK_SECTOR)
    want = K.ship_cost("cargotran") - K.ship_cost("scout_marauder")
    a.credits = want
    assert _la(u, a.id, "buy_ship").params["ship_class"]["net_cost_by"]["cargotran"] == want
    assert _act(u, a.id, ActionKind.BUY_SHIP, ship_class="cargotran").ok and a.credits == 0


# ---------------------------------------------------------------------------
# surrender
# ---------------------------------------------------------------------------


def _challenge(seed: int, hull=ShipClass.MERCHANT_CRUISER):
    u, (owner, ship, c) = _make_universe(seed=seed)
    home = _first_non_fed_sector(u, 40)
    there = _first_non_fed_sector(u, home + 1)
    if there not in u.sectors[home].warps:
        u.sectors[home].warps.append(there)
    if home not in u.sectors[there].warps:
        u.sectors[there].warps.append(home)
    _clear(u, home, there)
    u.sectors[there].fighters = FighterDeployment(owner_id=owner.id, count=50, mode=FighterMode.DEFENSIVE)
    _park(u, ship, home)
    ship.ship.ship_class = hull
    ship.experience = 200
    assert _act(u, ship.id, ActionKind.WARP, target=there).ok
    assert ship.fighter_challenge is not None
    return u, owner, ship, home, there


def test_surrender_takes_the_pod_to_the_previous_sector() -> None:
    u, owner, ship, home, there = _challenge(36130)
    assert _la(u, ship.id, "surrender").legal
    exp = ship.experience
    res = _act(u, ship.id, ActionKind.SURRENDER)
    assert res.ok
    assert ship.ship.ship_class is ShipClass.ESCAPE_POD and ship.sector_id == home
    assert ship.experience == exp - exp // 10 and ship.pods_today == 1 and ship.fighter_challenge is None
    assert _last(u, EventKind.SHIP_DESTROYED).payload["reason"] == "surrender"


def test_a_scout_that_surrenders_is_ship_destroyed() -> None:
    u, owner, ship, home, there = _challenge(36131, ShipClass.SCOUT_MARAUDER)
    exp = ship.experience
    assert _act(u, ship.id, ActionKind.SURRENDER).ok
    assert ship.sector_id == K.STARDOCK_SECTOR and ship.ship.ship_class is ShipClass.SCOUT_MARAUDER
    assert ship.experience == exp - exp // 2 and ship.turns_today == ship.turns_per_day


# ---------------------------------------------------------------------------
# elimination is a game setting
# ---------------------------------------------------------------------------


def test_tw2002_has_no_elimination_by_default() -> None:
    u, (a, b, c) = _make_universe(seed=36140)
    for _ in range(7):
        _destroy_ship(u, a.id, reason="mines")
    assert a.alive and a.deaths == 7
    assert build_observation(u, a.id).max_deaths == 0


def test_elimination_deaths_setting_turns_it_on() -> None:
    u, (a, b, c) = _make_universe(seed=36141)
    u.config.elimination_deaths = 2
    sid = _first_non_fed_sector(u)
    _park(u, a, sid)
    p = Planet(id=901, sector_id=sid, name="G", class_id=PlanetClass.M, owner_id=a.id)
    u.planets[901] = p
    u.sectors[sid].planet_ids.append(901)
    _destroy_ship(u, a.id, reason="mines")
    assert a.alive
    _destroy_ship(u, a.id, reason="mines")
    assert not a.alive and p.owner_id is None
    assert all(a.id not in s.occupant_ids for s in u.sectors.values())
    assert _last(u, EventKind.PLAYER_ELIMINATED).payload["deaths"] == 2
    assert build_observation(u, b.id).max_deaths == 2


# ---------------------------------------------------------------------------
# legacy mode is today's death, exactly
# ---------------------------------------------------------------------------


def test_legacy_mode_is_unchanged(monkeypatch) -> None:
    # Numbers recorded on 019987d (before this slice).
    monkeypatch.setattr(K, "DEATH_MODE", "legacy")
    u, (a, b, c) = _make_universe(seed=36001)
    sid = _first_non_fed_sector(u)
    for p in (a, b):
        _park(u, p, sid)
    a.credits, a.experience, a.alignment = 10001, 500, -300
    a.ship.ship_class = ShipClass.BATTLESHIP
    a.ship.cargo[Commodity.ORGANICS] = 7
    a.ship.genesis = 2
    pl = Planet(id=900, sector_id=sid, name="G", class_id=PlanetClass.M, owner_id="A")
    u.planets[900] = pl
    u.sectors[sid].planet_ids.append(900)
    rows = []
    for reason in ("mines", "combat", "surrender"):
        _destroy_ship(u, "A", reason=reason, killer_id="B", by_other=reason == "combat")
        rows.append((a.sector_id, a.credits, a.ship.ship_class.value, a.ship.holds, a.ship.fighters, a.deaths,
                     a.alive, a.experience, a.alignment, sum(a.ship.cargo.values()), a.ship.genesis, pl.owner_id,
                     u.events[-1].kind.value, u.events[-1].summary))
        if a.alive:
            _park(u, a, sid)
            a.credits += 999
    assert rows == [
        (1, 7500, "merchant_cruiser", 20, 20, 1, True, 500, -300, 0, 0, "A", "ship_destroyed",
         "*** Alice's ship destroyed (mines); ejected to StarDock [death #1/3] ***"),
        (1, 6374, "merchant_cruiser", 20, 20, 2, True, 500, -300, 0, 0, "A", "ship_destroyed",
         "*** Alice's ship destroyed (combat); ejected to StarDock [death #2/3] ***"),
        (1, 5529, "merchant_cruiser", 20, 20, 3, False, 500, -300, 0, 0, None, "player_eliminated",
         "!!! Alice ELIMINATED \u2014 3 ship losses, removed from match !!!"),
    ]
    assert u.sectors[1].occupant_ids == ["C"]
    assert build_observation(u, b.id).max_deaths == 3


def test_legacy_mine_warp_is_unchanged(monkeypatch) -> None:
    monkeypatch.setattr(K, "DEATH_MODE", "legacy")
    u, (a, b, c) = _make_universe(seed=36002)
    home = _first_non_fed_sector(u, 40)
    dest = u.sectors[home].warps[0]
    u.sectors[1].occupant_ids.remove("A")
    a.sector_id = home
    u.sectors[home].occupant_ids.append("A")
    a.ship.fighters, a.ship.shields, a.credits = 0, 0, 4000
    u.sectors[dest].mines = [MineDeployment(owner_id="B", kind=MineType.ARMID, count=40)]
    r = _act(u, "A", ActionKind.WARP, target=dest)
    assert [r.ok, r.turns_spent, a.sector_id, a.credits, a.deaths, a.ship.ship_class.value, a.turns_today] == [
        True, 3, 33, 3000, 1, "merchant_cruiser", 3]


# ---------------------------------------------------------------------------
# observation and fog
# ---------------------------------------------------------------------------


def test_observation_shows_the_pod_and_hides_where_it_went_from_others() -> None:
    u, (a, b, c) = _make_universe(seed=36150)
    start = _first_non_fed_sector(u, 40)
    chain = _line(u, start, 6)
    _park(u, a, start)
    _park(u, b, start)
    _destroy_ship(u, a.id, reason="combat", killer_id=b.id, by_other=True)
    ev = _last(u, EventKind.SHIP_DESTROYED)
    facts = event_facts(ev)
    assert facts.get("outcome") == "escape_pod" and "pod_sector" not in facts
    obs = build_observation(u, a.id)
    assert obs.ship["class"] == "escape_pod"
    assert "ESCAPE POD" in obs.action_hint
    other = build_observation(u, b.id).model_dump(mode="json")
    assert str(a.sector_id) not in str([e for e in other["recent_events"] if "pod_sector" in str(e)])
    assert chain


def test_two_pods_today_warns_the_next_loss_is_ship_destroyed() -> None:
    u, (a, b, c) = _make_universe(seed=36151)
    for _ in range(2):
        a.ship.ship_class = ShipClass.BATTLESHIP
        _destroy_ship(u, a.id, reason="mines")
    assert a.pods_today == 2 and a.turns_today == 0
    hint = build_observation(u, a.id).action_hint
    assert "2 ship losses today: one more today is SHIP DESTROYED" in hint


# ---------------------------------------------------------------------------
# seat brains and the heuristic seat stay legal in a pod
# ---------------------------------------------------------------------------


def _brains():
    import importlib.util

    spec = importlib.util.spec_from_file_location("sba", ROOT / "scripts" / "seat_brain_acceptance.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from tw2k.agents.seat_brain import SeatBrain

    return {"N1": mod.n1_brain, "N2": mod.n2_brain, "N3": SeatBrain}


@pytest.mark.parametrize("where", ["stardock", "away"])
def test_seat_brains_in_a_pod_stay_legal(where: str) -> None:
    for name, make in _brains().items():
        u, (a, b, c) = _make_universe(seed=36160)
        sid = _first_non_fed_sector(u)
        _pod_at(u, a, sid)
        a.credits = 3000
        if where == "stardock":
            _park(u, a, K.STARDOCK_SECTOR)
        brain = make()
        for _ in range(6):
            obs = build_observation(u, a.id).model_dump(mode="json")
            act = brain.decide(obs)
            assert validate_action(obs, act) == [], (name, where, act)
            res = apply_action(u, a.id, Action(kind=act["kind"], args=act.get("args") or {}))
            assert res.ok, (name, where, act, res.error)
            if a.ship.ship_class is not ShipClass.ESCAPE_POD:
                break
        if where == "stardock":
            assert a.ship.ship_class is not ShipClass.ESCAPE_POD, name


def test_heuristic_seat_in_a_pod_stays_legal() -> None:
    import asyncio

    from tw2k.agents import HeuristicAgent

    u, (a, b, c) = _make_universe(seed=36161)
    _pod_at(u, a, _first_non_fed_sector(u))
    agent = HeuristicAgent(a.id, a.name, seed=1)
    for _ in range(5):
        act = asyncio.run(agent.act(build_observation(u, a.id)))
        res = apply_action(u, a.id, act)
        assert res.ok or res.turns_spent == 0, (act, res.error)


# ---------------------------------------------------------------------------
# fuzz: random deaths for all 16 hulls
# ---------------------------------------------------------------------------


REASONS = [("mines", False), ("quasar", False), ("sector_fighters", False), ("planet_defense", False),
           ("surrender", False), ("combat", True), ("ferrengi", True), ("combat", False)]


def test_fuzz_random_deaths_all_sixteen_hulls() -> None:
    assert len(HULLS) == 16
    rng = random.Random(250925)
    u, players = _make_universe(seed=36170, players=4)
    sids = [s for s in sorted(u.sectors) if s not in K.FEDSPACE_SECTORS]
    for i in range(640):
        p = players[rng.randrange(4)]
        if rng.random() < 0.2:
            tick_day(u)
        _park(u, p, rng.choice(sids))
        p.turns_today = rng.randrange(0, p.turns_per_day + 1)
        p.ship.ship_class = HULLS[i % 16] if rng.random() < 0.85 else ShipClass.ESCAPE_POD
        p.ship.fighters = rng.randrange(0, 2000)
        p.experience = rng.randrange(0, 50_000)
        p.alignment = rng.randrange(-5000, 5000)
        p.credits = rng.randrange(0, 100_000)
        if rng.random() < 0.5:
            p.prev_sector_id = rng.choice(sids)
        for s in rng.sample(sids, 20):
            u.sectors[s].fighters = FighterDeployment(
                owner_id=rng.choice(players).id, count=rng.randrange(1, 50), mode=FighterMode.DEFENSIVE)
        before = (p.credits, p.experience, abs(p.alignment), p.deaths)
        reason, by_other = REASONS[rng.randrange(len(REASONS))]
        _destroy_ship(u, p.id, reason=reason, killer_id=players[0].id, by_other=by_other)
        assert p.alive
        assert p.credits == before[0] >= 0
        assert 0 <= p.experience <= before[1]
        assert abs(p.alignment) <= before[2]
        assert p.deaths == before[3] + 1
        assert p.ship.ship_class in (ShipClass.ESCAPE_POD, ShipClass.SCOUT_MARAUDER)
        assert sum(p.ship.cargo.values()) == 0 and p.ship.fighters == 0
        assert p.turns_today <= p.turns_per_day
        assert p.pods_today <= 2
        homes = [s for s in u.sectors.values() if p.id in s.occupant_ids]
        assert len(homes) == 1 and homes[0].id == p.sector_id
        legal = [la for la in legal_actions(u, p.id) if la.legal]
        assert legal, (i, p.ship.ship_class)
        if p.turns_today < p.turns_per_day:
            assert any(la.kind == "wait" for la in legal)
        if p.sector_id == K.STARDOCK_SECTOR and p.ship.ship_class is ShipClass.ESCAPE_POD:
            assert "scout_marauder" in _la(u, p.id, "buy_ship").params["ship_class"]["choices"]


def test_a_retreat_sets_the_previous_sector() -> None:
    u, owner, ship, home, there = _challenge(36132)
    assert ship.prev_sector_id == home
    assert _act(u, ship.id, ActionKind.RETREAT).ok
    assert ship.sector_id == home and ship.prev_sector_id == there
