"""NOTE 101. One colonist unit, named on the screen, and the three seat gaps.

The trace is docs/plans/colonist-units-v1.md. No new switch. Profile-off stays
the old one-to-one count.
"""

from __future__ import annotations

import asyncio

import tw2k.agents.cockpit_seat as seat
import tw2k.engine.constants as K
from tests.test_colonist_units_v1 import _act, _land, _take, _world
from tests.test_external_harness_phase1 import TOK2, _app_and_client, _auth, _http_spec, _wait_until
from tw2k.engine.models import Commodity, PlanetClass
from tw2k.engine.observation import build_observation
from tw2k.engine.planets import daily_production
from tw2k.engine.legality import legal_actions
from tw2k.engine.victory import _planet_asset_value
from tw2k.engine.models import Planet


def test_clarity_stays_off_until_a_live_switch(monkeypatch) -> None:
    assert K.colonist_clarity_on() is False
    assert K.COLONIST_UNITS_MODE == "legacy"
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.colonist_clarity_on() is True
    assert K.COLONIST_UNITS_MODE == "legacy"


def test_table_terra_hold_class_m_and_class_c(monkeypatch) -> None:
    """30 holds are 30,000 people: 30 thousands on class M, 30 colonists on class C."""
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u = _world()
    _take(u, 30)
    ship = u.players["P1"].ship
    assert ship.cargo[Commodity.COLONISTS] == 30_000
    assert ship.cargo_used == 30
    planet_m = _land(u, PlanetClass.M)
    dropped = _act(
        u, "assign_colonists", planet_id=planet_m.id, **{"from": "ship", "to": "fuel_ore", "qty": 30_000},
    )
    assert dropped.ok, dropped.error
    assert planet_m.colonists[Commodity.FUEL_ORE] == 30_000
    assert K.colonist_quote(30_000, people=True) == {"unit": "thousands", "thousands": 30, "people": 30_000}


def test_table_production_cap_and_net_worth(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.CLASS_M_CATEGORY_CAP == 30_000 * 1_000
    assert 3 * 30_000 == 90_000
    peak = daily_production(PlanetClass.M, {Commodity.FUEL_ORE: 15_000_000})
    assert peak["fuel_ore"] == 5_000
    one = daily_production(PlanetClass.M, {Commodity.FUEL_ORE: 3_000})
    assert one["fuel_ore"] == 1
    ratios = daily_production(PlanetClass.M, {
        Commodity.FUEL_ORE: 3_000, Commodity.ORGANICS: 7_000, Commodity.EQUIPMENT: 13_000,
    })
    assert (ratios["fuel_ore"], ratios["organics"], ratios["equipment"]) == (1, 1, 1)
    planet = Planet(
        id=3, sector_id=12, name="M", class_id=PlanetClass.M, owner_id="P1", origin="genesis",
        colonists={Commodity.FUEL_ORE: 30_000},
    )
    assert _planet_asset_value(planet) == 30 * K.COLONIST_PRICE
    assert K.HOME_PLANET_FUEL + K.HOME_PLANET_ORGANICS + K.HOME_PLANET_EQUIPMENT == 191_000


def test_one_thousand_units_can_start_level_1_and_999_cannot(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u = _world()
    planet = _land(u, PlanetClass.M)
    planet.stockpile[Commodity.FUEL_ORE] = 300
    planet.stockpile[Commodity.ORGANICS] = 200
    planet.stockpile[Commodity.EQUIPMENT] = 250
    planet.colonists[Commodity.FUEL_ORE] = 999_000
    short = _act(u, "build_citadel", planet_id=planet.id)
    assert short.ok is False
    assert "colonists" in (short.error or "")
    planet.colonists[Commodity.FUEL_ORE] = 1_000_000
    started = _act(u, "build_citadel", planet_id=planet.id)
    assert started.ok, started.error
    assert planet.citadel_target == 1


def test_citadel_sentence_at_221_units(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u = _world()
    planet = _land(u, PlanetClass.M)
    planet.colonists[Commodity.FUEL_ORE] = 221_000
    obs = build_observation(u, "P1")
    quote = obs.citadel_next_build
    assert quote["need"] == 1_000
    assert quote["have"] == 221
    assert quote["unit"] == "thousands"
    assert quote["need_people"] == 1_000_000
    assert quote["have_people"] == 221_000
    assert quote["plain"] == (
        "Level 1 needs 1,000 (thousands) colonists = 1,000,000; "
        # Playtest 4: the haul is this ship's 40 holds, not a fixed 30.
        "you have 221 (thousands); about 20 more Terra trips with 40 holds"
    )
    listed = {la.kind: la for la in legal_actions(u, "P1")}
    assert listed["build_citadel"].params["next"]["plain"] == quote["plain"]
    brief = next(row for row in obs.sector["planets"] if row["id"] == planet.id)
    assert brief["colonists_stored"] == "people"


def test_profile_off_adds_no_unit_field() -> None:
    assert K.v311_profile() is False
    u = _world()
    planet = _land(u, PlanetClass.M)
    planet.colonists[Commodity.FUEL_ORE] = 221_000
    obs = build_observation(u, "P1")
    dumped = obs.model_dump(mode="json")
    assert "citadel_next_build" not in dumped
    brief = next(row for row in obs.sector["planets"] if row["id"] == planet.id)
    assert "colonists_stored" not in brief
    assert "need" not in (brief.get("citadel_next_build") or {})


def test_hold_quote_names_the_rise_and_the_counter_is_a_field(monkeypatch) -> None:
    monkeypatch.setattr(K, "ACTION_RESULT_MODE", "report")
    u = _world()
    listed = {la.kind: la for la in legal_actions(u, "P1")}
    quote = listed["buy_equip"].params["hold_quote"]
    assert quote["per_hold"]
    assert quote["totals"]["1"] == quote["per_hold"][0]
    assert quote["totals"]["2"] == quote["per_hold"][0] + quote["per_hold"][1]
    assert quote["per_hold"][1] != quote["per_hold"][0]
    assert quote["max_holds"] >= quote["holds"] + quote["afford"]
    trade = {
        "kind": "trade", "legal": True,
        "params": {"counter": {"commodity": "fuel_ore", "side": "buy", "listed": 40, "counter": 36},
                   "commodity": {"buy_choices": ["fuel_ore"], "sell_choices": []},
                   "qty": {"max_by": {"fuel_ore": {"buy": 10}}}},
    }
    brain = seat.SeatBrain(2)
    brain.cockpit = None
    taken = brain._take_counter(trade, {"fuel_ore": 0, "organics": 0, "equipment": 0}, 10, 1_000)
    assert taken is not None
    assert taken[1]["unit_price"] == 36
    assert brain.counter_field is True
    brain.refused("trade", {"side": "buy"}, "counter 36")
    assert brain.gaps.get("counter_in_log", 0) == 0


def test_post_answer_carries_the_verdict(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(K, "ACTION_RESULT_MODE", "report")
    app, client = _app_and_client(tmp_path)
    runner = app.state.runner

    async def _go() -> dict:
        await runner.start(_http_spec())
        assert await _wait_until(lambda: runner.state.universe is not None)
        opened = await client.get(
            "/harness/v1/P2/observation", params={"wait_s": 5}, headers=_auth(TOK2),
        )
        assert opened.status_code == 200
        body = opened.json()
        before = int(body["observation"]["credits"])
        posted = await client.post(
            "/harness/v1/P2/action",
            json={"turn_seq": body["turn_seq"], "action": {"kind": "wait", "args": {}}},
            headers=_auth(TOK2),
        )
        assert posted.status_code == 200, posted.text
        await runner.stop()
        await client.aclose()
        return {"before": before, "answer": posted.json()}

    got = asyncio.run(_go())
    result = got["answer"]["result"]
    assert result["ok"] is True
    assert result["rejected"] is False
    assert result["reason"] is None
    assert "turns_spent" in result
    assert "credits_change" in result
    assert result["credits"] == got["before"] + result["credits_change"]
