"""GAP 11.11: the bang builds 95 percent of the 40 percent possible starports.

Big_Bang.html: "C - Maximum Possible Starports ... Default is 40%" and
"D - Initial Starports to Build ... Default is 95%". "B - Maximum Course
Length ... Default is 45". Bubbles are Gold-only (S1), so none.
"""

from __future__ import annotations

from collections import deque

import tw2k.engine.constants as K
from tw2k.engine.models import GameConfig
from tw2k.engine.universe import generate_universe


def _ports(universe) -> int:
    start = max(K.FEDSPACE_SECTORS) + 1
    return sum(1 for sid, s in universe.sectors.items() if int(sid) >= start and s.port is not None)


def _share(monkeypatch, profile: str, built: str = "legacy") -> float:
    monkeypatch.setattr(K, "V311_PROFILE", profile)
    monkeypatch.setattr(K, "BIG_BANG_DENSITY_MODE", "live")
    monkeypatch.setattr(K, "BIG_BANG_BUILT_MODE", built)
    total = eligible = 0
    for seed in (11, 12, 13):
        u = generate_universe(GameConfig(seed=seed, universe_size=1000))
        total += _ports(u)
        eligible += 1000 - max(K.FEDSPACE_SECTORS)
    return total / eligible


def test_off_builds_every_possible_port(monkeypatch):
    assert not K.big_bang_built_live() or K.V311_PROFILE == "v311"
    assert abs(_share(monkeypatch, "legacy") - 0.40) < 0.03


def test_v311_builds_95_percent(monkeypatch):
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.big_bang_built_live()
    assert abs(K.bang_port_probability() - 0.38) < 1e-9
    assert abs(_share(monkeypatch, "v311") - 0.38) < 0.03


def test_switch_alone(monkeypatch):
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    monkeypatch.setattr(K, "BIG_BANG_BUILT_MODE", "live")
    assert K.big_bang_built_live()
    monkeypatch.setattr(K, "BIG_BANG_BUILT_MODE", "legacy")
    assert not K.big_bang_built_live()


def test_v311_course_length_within_45(monkeypatch):
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u = generate_universe(GameConfig(seed=21, universe_size=1000))
    dist = {1: 0}
    q = deque([1])
    while q:
        cur = q.popleft()
        for nxt in u.sectors[cur].warps:
            if nxt not in dist:
                dist[nxt] = dist[cur] + 1
                q.append(nxt)
    assert max(dist.values()) <= 45


def test_manual_line(monkeypatch):
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    from tw2k.public import manual
    assert "BIG_BANG_BUILT_MODE" in manual._SWITCH_PLAIN
    src = open(manual.__file__).read()
    assert "95 percent of its 40 percent possible starports" in src
