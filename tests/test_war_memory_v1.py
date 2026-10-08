"""War counters stay on the scratchpad, and a quiet seat writes none."""

from __future__ import annotations

from tw2k.agents.seat_brain import SeatMemory


def test_war_counters_roundtrip_and_a_quiet_pad_omits_them() -> None:
    quiet = SeatMemory()
    assert "war_siege_day" not in quiet.dump()
    assert "war_spend_day" not in quiet.dump()

    mem = SeatMemory()
    mem.war_spend_day = 6
    mem.war_spent = 4000
    mem.war_siege_day = 6
    mem.war_sieges = 1
    mem.war_land_tries = 2
    mem.war_siege_planet = 9
    loaded = SeatMemory.load(mem.dump())
    assert loaded.war_spend_day == 6
    assert loaded.war_spent == 4000
    assert loaded.war_siege_day == 6
    assert loaded.war_sieges == 1
    assert loaded.war_land_tries == 2
    assert loaded.war_siege_planet == 9
