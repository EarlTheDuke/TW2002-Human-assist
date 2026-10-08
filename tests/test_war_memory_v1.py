"""War counters stay on the scratchpad, and a quiet seat writes none."""

from __future__ import annotations

import random

from tw2k.agents.seat_brain import SeatMemory
from tw2k.agents.war_brain import picket_qty, planet_fight, siege_refusal, threat_map


def test_war_counters_roundtrip_and_a_quiet_pad_omits_them() -> None:
    quiet = SeatMemory()
    assert "war_siege_day" not in quiet.dump()
    assert "war_spend_day" not in quiet.dump()
    assert "war_fail_day" not in quiet.dump()
    assert "war_home_seq" not in quiet.dump()

    mem = SeatMemory()
    mem.war_spend_day = 6
    mem.war_spent = 4000
    mem.war_siege_day = 6
    mem.war_sieges = 1
    mem.war_land_tries = 2
    mem.war_siege_planet = 9
    mem.war_fail_day = 6
    loaded = SeatMemory.load(mem.dump())
    assert loaded.war_spend_day == 6
    assert loaded.war_spent == 4000
    assert loaded.war_siege_day == 6
    assert loaded.war_sieges == 1
    assert loaded.war_land_tries == 2
    assert loaded.war_siege_planet == 9
    assert loaded.war_fail_day == 6


def test_bw26_save(monkeypatch) -> None:
    def boom() -> float:
        raise AssertionError("rng")

    monkeypatch.setattr(random, "random", boom)
    threat_map([{"sector": 1}], limit=64)
    picket_qty(1000, floor=0)
    planet_fight(100, 10, 0, 0, "merchant_cruiser")
    assert siege_refusal(skill="N3", policy="full", day=6, owner_evil=True) is None
