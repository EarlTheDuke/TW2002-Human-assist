"""Feed index (docs/playtests/fullgame/SOAK_30DAY_V1.md): the observation's rival last-seen and
orphaned-planet lookups, and apply_action's new-event seqs, no longer rescan the whole event feed,
and give the same answers as the full scans they replace."""

from __future__ import annotations

import random

from tw2k.engine import GameConfig, generate_universe, runner
from tw2k.engine import constants as K
from tw2k.engine import observation as obs
from tw2k.engine.models import Alliance, Corporation, EventKind, Player

PIDS = ["P1", "P2", "P3", "P4"]
KINDS = [EventKind.WARP, EventKind.TRADE, EventKind.HAIL, EventKind.AUTOPILOT, EventKind.CLOAK_ON,
         EventKind.RETREAT, EventKind.NAVHAZ_HIT, EventKind.CORP_CREATE, EventKind.CORP_DEPOSIT,
         EventKind.ALLIANCE_PROPOSED, EventKind.ALLIANCE_FORMED, EventKind.LAND_PLANET,
         EventKind.PLANET_TRADE, EventKind.PLANET_ORPHANED, EventKind.LLM_USAGE, EventKind.BROADCAST]


def _world(seed: int):
    u = generate_universe(GameConfig(seed=seed, universe_size=60, max_days=30))
    for i, pid in enumerate(PIDS):
        u.players[pid] = Player(id=pid, name=pid, agent_kind="external", sector_id=1 + i, credits=1000)
    return u


def _emit_random(u, rng: random.Random, n: int) -> None:
    for _ in range(n):
        payload = {"_witnesses": rng.sample(PIDS, rng.randint(0, 2))}
        if rng.random() < 0.15:
            payload["_actor_cloaked"] = True
        if rng.random() < 0.2:
            payload["target"] = rng.choice(PIDS)
        if rng.random() < 0.1:
            payload["victim"] = rng.choice(PIDS)
        if rng.random() < 0.3:
            payload["ticker"] = rng.choice(["AAA", "BBB", "ZZZ"])
        if rng.random() < 0.3:
            payload["alliance_id"] = rng.choice(["A1", "A2"])
        if rng.random() < 0.3:
            payload["planet_id"] = rng.randint(1, 5)
            payload["former_owner"] = rng.choice(PIDS)
        u.emit(rng.choice(KINDS), actor_id=rng.choice([*PIDS, None, "ghost", ""]),
               sector_id=rng.choice([None, 2, 7, 11]), payload=payload)


def _shuffle_state(u, rng: random.Random) -> None:
    """Change everything visibility reads at query time: cloaks, corps, alliances."""
    for pid in PIDS:
        u.players[pid].ship.cloaked = rng.random() < 0.3
    u.corporations.clear()
    for ticker in ("AAA", "BBB"):
        if rng.random() < 0.7:
            members = rng.sample(PIDS, rng.randint(1, 3))
            u.corporations[ticker] = Corporation(ticker=ticker, name=ticker, ceo_id=members[0], member_ids=members,
                                                 invited_ids=rng.sample(PIDS, rng.randint(0, 1)))
    u.alliances.clear()
    for aid in ("A1", "A2"):
        if rng.random() < 0.7:
            u.alliances[aid] = Alliance(id=aid, member_ids=rng.sample(PIDS, 2), proposed_by="P1", formed_day=1)


def _old_last_seen(u, player_id):
    last_seen = {}
    for ev in u.events:
        if ev.actor_id is None or ev.actor_id == player_id or ev.actor_id not in u.players:
            continue
        if ev.sector_id is None or not obs._event_visible_to(ev, player_id, u):
            continue
        last_seen[ev.actor_id] = (ev.day, ev.tick, ev.sector_id)
    return last_seen


def _old_orphans(u):
    out = {}
    for ev in u.events:
        if ev.kind is EventKind.PLANET_ORPHANED:
            plid, former = ev.payload.get("planet_id"), ev.payload.get("former_owner")
            if isinstance(plid, int) and isinstance(former, str):
                out[plid] = former
    return out


def test_index_matches_the_full_scans_while_the_feed_and_the_state_change(monkeypatch):
    for seed in (1, 2, 3, 4, 5, 6):
        rng = random.Random(seed)
        u = _world(seed)
        for _round in range(12):
            _emit_random(u, rng, rng.randint(0, 60))  # the index is extended, not rebuilt
            _shuffle_state(u, rng)
            monkeypatch.setattr(K, "HARDWARE_MODE", rng.choice(["tw2002", "legacy"]))
            monkeypatch.setattr(K, "PLANET_TRADE_FEED", rng.choice(["actor_only", "witnessed"]))
            for pid in PIDS:
                assert obs._rival_last_seen(u, pid) == _old_last_seen(u, pid)
            assert obs._orphan_former_owners(u) == _old_orphans(u)


def test_a_replaced_or_truncated_feed_is_reindexed():
    rng = random.Random(9)
    u = _world(9)
    _emit_random(u, rng, 200)
    assert obs._rival_last_seen(u, "P1") == _old_last_seen(u, "P1")
    del u.events[150:]  # not an append: the index must notice
    assert obs._rival_last_seen(u, "P1") == _old_last_seen(u, "P1")
    assert obs._orphan_former_owners(u) == _old_orphans(u)
    u.events = list(u.events[:40])  # a new list object (resume / copy)
    assert obs._rival_last_seen(u, "P2") == _old_last_seen(u, "P2")
    assert obs._orphan_former_owners(u) == _old_orphans(u)


def test_visibility_is_checked_once_per_new_event_not_per_observation(monkeypatch):
    rng = random.Random(11)
    u = _world(11)
    _emit_random(u, rng, 3000)
    calls = []
    real = obs._event_visible_base
    monkeypatch.setattr(obs, "_event_visible_base", lambda ev, pid, uu: calls.append(1) or real(ev, pid, uu))
    obs._rival_last_seen(u, "P1")
    first = len(calls)
    for _ in range(5):
        obs._rival_last_seen(u, "P1")
    assert len(calls) - first <= 100  # only live (corp/alliance) candidates are re-checked
    u.emit(EventKind.TRADE, actor_id="P2", sector_id=2, payload={"_witnesses": ["P1"]})
    assert obs._rival_last_seen(u, "P1")["P2"][2] == 2


def test_new_event_seqs_are_the_tail_of_the_feed():
    rng = random.Random(3)
    u = _world(3)
    _emit_random(u, rng, 50)
    for before in (0, 10, u.seq - 5, u.seq):
        assert runner._seqs_after(u.events, before) == [e.seq for e in u.events if e.seq > before]
    seqs = [e.seq for e in u.events]
    assert seqs == sorted(set(seqs))  # Universe.emit numbers the feed in append order
