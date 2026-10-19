"""NOTE 115 GAP 14.5: the steal-dump-transport and rob-transport cycle."""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.agents.seat_brain import SeatBrain, SeatMemory, View
from tw2k.engine.evil_trade import next_evil_step
from tw2k.public.manual import render


def _legal(kind: str, *, params: dict | None = None, reason: str = "") -> dict:
    return {"kind": kind, "legal": True, "reason": reason, "params": params or {}}


def _view(
    *,
    alignment: int = -100,
    experience: int = 2100,
    here: int = 10,
    landed: int | None = None,
    cargo: dict | None = None,
    free: int = 80,
    owned: list | None = None,
    legal: list | None = None,
    ships: list | None = None,
) -> View:
    return View({
        "alignment": alignment,
        "experience": experience,
        "planet_landed": landed,
        "owned_planets": owned or [],
        "sector": {"id": here},
        "ship": {"cargo": cargo or {}, "cargo_free": free, "class": "colonial_transport"},
        "legal_actions": legal or [],
        "fleet": {"ships": ships or [], "transport_range": K.transport_range("colonial_transport")},
    })


def _steal_legal(room: int = 200) -> dict:
    return _legal("steal", params={
        "commodity": {"choices": ["organics", "equipment"]},
        "qty": {"max_by": {"organics": 999, "equipment": room}},
    })


def _partner(ship_id: int, *, hops: int, sector: int, in_range: bool = True) -> dict:
    return {"ship_id": ship_id, "sector_id": sector, "hops": hops, "in_range": in_range, "hull": "colonial_transport"}


def test_switch_is_legacy_until_the_profile() -> None:
    assert K.EVIL_TRADE_LOOP_MODE == "legacy"
    assert K.evil_trade_loop_live() is False


def test_v311_turns_the_loop_on_without_moving_the_stored_flag(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.evil_trade_loop_live() is True
    assert K.EVIL_TRADE_LOOP_MODE == "legacy"


def test_alignment_above_the_floor_does_nothing() -> None:
    view = _view(alignment=-99, legal=[_steal_legal()])
    assert next_evil_step(view) is None


def test_steal_is_equipment_inside_the_experience_cap() -> None:
    view = _view(experience=2100, free=80, legal=[_steal_legal(room=200)])
    step = next_evil_step(view)
    assert step["kind"] == "steal"
    assert step["args"] == {"commodity": "equipment", "qty": min(200, 80, 2100 // K.STEAL_HOLD_DIVISOR)}
    assert step["args"]["qty"] == 80


def test_steal_qty_is_the_experience_cap_when_the_hold_is_larger() -> None:
    view = _view(experience=2100, free=300, legal=[_steal_legal(room=250)])
    step = next_evil_step(view)
    assert step["args"]["qty"] == 2100 // K.STEAL_HOLD_DIVISOR
    assert step["args"]["commodity"] == "equipment"


def test_land_then_dump_before_a_beam() -> None:
    planet = {"id": 4, "sector_id": 10}
    ships = [_partner(2, hops=3, sector=20)]
    transport = _legal("ship_transport", params={"ship_id": {"choices": [2]}})
    land = _legal("land_planet", params={"planet_id": {"choices": [4, 9]}})
    hauling = _view(
        cargo={"equipment": 40, "organics": 10},
        owned=[planet, {"id": 9, "sector_id": 10}],
        legal=[land, transport],
        ships=ships,
    )
    step = next_evil_step(hauling)
    assert step["kind"] == "land_planet"
    assert step["args"]["planet_id"] == 4
    dump = _legal("dump_planet_cargo", params={
        "commodity": {"choices": ["organics", "equipment"]},
        "qty": {"max_by": {"equipment": 40, "organics": 10}},
    })
    landed = _view(
        landed=4,
        cargo={"equipment": 40, "organics": 10},
        owned=[planet],
        legal=[dump, transport, _legal("liftoff")],
        ships=ships,
    )
    dumped = next_evil_step(landed)
    assert dumped["kind"] == "dump_planet_cargo"
    assert dumped["args"] == {"planet_id": 4, "commodity": "equipment", "qty": 40}


def test_cargo_is_not_beamed_when_the_planet_cannot_be_landed() -> None:
    view = _view(
        cargo={"equipment": 10},
        owned=[{"id": 4, "sector_id": 11}],
        legal=[_legal("ship_transport", params={"ship_id": {"choices": [2]}})],
        ships=[_partner(2, hops=2, sector=20)],
    )
    assert next_evil_step(view) is None


def test_a_fake_bust_beams_instead_of_stealing_again() -> None:
    view = _view(
        legal=[
            _steal_legal(),
            _legal("ship_transport", params={"ship_id": {"choices": [2, 5]}}),
        ],
        ships=[_partner(5, hops=4, sector=30), _partner(2, hops=2, sector=20)],
    )
    step = next_evil_step(view, last_crime_sector=10)
    assert step["kind"] == "ship_transport"
    assert step["args"]["ship_id"] == 2


def test_a_partner_out_of_range_is_refused() -> None:
    view = _view(
        legal=[_legal("ship_transport", params={"ship_id": {"choices": []}})],
        ships=[_partner(2, hops=8, sector=20, in_range=False)],
    )
    assert next_evil_step(view) is None
    assert K.transport_range("colonial_transport") == 7


def test_rob_uses_the_experience_cap_with_room_still_in_the_hold() -> None:
    view = _view(
        experience=1000,
        free=20,
        legal=[_legal("rob", params={"amount": {"max": 20_000}})],
    )
    step = next_evil_step(view)
    assert step["kind"] == "rob"
    assert step["args"]["amount"] == min(20_000, 1000 * K.ROB_CREDIT_FACTOR)


def test_brain_stays_quiet_until_the_mode_is_live(monkeypatch) -> None:
    view = _view(legal=[_steal_legal(room=40)])
    brain = SeatBrain()
    brain.mem = SeatMemory()
    assert brain._evil_trade_step(view) is None
    assert brain.mem.last_crime_sector is None
    monkeypatch.setattr(K, "EVIL_TRADE_LOOP_MODE", "live")
    step = brain._evil_trade_step(view)
    assert step["kind"] == "steal"
    assert step["args"]["commodity"] == "equipment"
    assert brain.mem.last_crime_sector == 10


def test_manual_names_the_loop() -> None:
    page = render("Galaxy War Command")
    assert "Evil trade loops: The v3.11 profile turns this on. In this process it is off." in page
