"""NOTE 172. Mid-game refits for the scripted AI cockpit seat.

The trader still reads only the seat page. Once the opening holds and
fighters are aboard, a later day with cash buys more holds when the paying
pair can fill them, then fighters and (hard) shields with a slice of the
cash. A full item is not asked for again, and a declined hull is quoted
again once the route pays half as much again.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO / "scripts"))

from ai_cockpit.trader import ScriptedTrader  # noqa: E402


def _rich(level: str = "hard", *, avail: int = 60) -> ScriptedTrader:
    t = ScriptedTrader(level=level)
    t.ports[20] = {"Equipment": {"ask": 40, "avail": avail, "now": avail}}
    t.ports[21] = {"Equipment": {"bid": 60, "avail": avail, "now": avail}}
    t.links[20] = {21: 3}
    t.links[21] = {20: 3}
    t.bought |= {"holds", "fighters"}
    t.first_gear_day = 1
    t.day, t.max_day, t.day_turns, t.hold_cap = 3, 10, 40, 20
    t.hold_price = 300
    t.credits = 30_000
    return t


def test_the_opening_day_does_not_refit() -> None:
    t = _rich()
    t.day = 1
    assert t._refit_item() is None
    t.bought.discard("fighters")
    t.day = 3
    assert t._refit_item() is None


def test_holds_come_first_when_the_pair_can_fill_them() -> None:
    t = _rich()
    assert t._refit_item() == "holds"
    t.refit_day["holds"] = 3
    assert t._refit_item() == "fighters"
    t.refit_day["fighters"] = 3
    assert t._refit_item() == "shields"
    t.refit_day["shields"] = 3
    assert t._refit_item() is None
    t.day = 4
    assert t._refit_item() == "holds"


def test_a_thin_pair_skips_holds_and_a_poor_wallet_waits() -> None:
    t = _rich(avail=10)
    assert t._refit_item() == "fighters"
    t.credits = 5_000
    assert t._refit_item() is None


def test_normal_skips_shields_and_easy_never_refits() -> None:
    t = _rich("normal")
    t.refit_day.update({"holds": 3, "fighters": 3})
    assert t._refit_item() is None
    assert _rich("easy")._refit_item() is None


def test_a_refit_spends_a_slice_and_a_full_item_is_closed() -> None:
    t = _rich()
    note = "Fighters 100 cr each, up to 500."
    assert t._gear_qty("fighters", {"note": note}, 30_000) == str((30_000 // 7) // 100)
    t.gear = {"item": "shields", "phase": "qty"}
    act = t._gear_step({"note": "Shields 50 cr each, up to 0."}, 30_000)
    assert act.op == "press" and "shields" in t.maxed
    assert t._refit_item() == "holds"
    t.gear = {"item": "holds", "phase": "select"}
    act = t._gear_step({"itemOptions": ["fighters"]}, 30_000)
    assert act.op == "press" and "holds" in t.maxed


def test_a_refit_confirm_is_logged_once_a_day() -> None:
    t = _rich()
    t.gear = {"item": "fighters", "phase": "confirm"}
    act = t._gear_step({}, 30_000)
    assert act.label == "CONFIRM" and t.plan_note == "refit fighters"
    assert t.refit_day["fighters"] == 3


def test_a_declined_hull_is_quoted_again_when_the_route_grows() -> None:
    t = _rich()
    daily = t._daily_profit()
    assert daily > 0
    t.ship_skip_profit = daily
    assert t._ship_closed() is True
    t.ship_skip_profit = max(1, daily // 2)
    assert t._ship_closed() is False


def test_a_hull_the_cash_cannot_pay_for_is_not_chosen() -> None:
    t = _rich()
    t.credits = 1_000
    quote = "Merchant Freighter: 2,000 cr. Holds 40, fighters 50, shields 50, 3 turns per warp."
    assert t._yard_pays({"ship": "Holds 0/20"}, quote) is False


def test_the_turn_clock_is_left_to_refill_instead_of_a_wait() -> None:
    t = ScriptedTrader(level="hard")
    clock = {"chip": "YOUR MOVE", "turnsFace": "3/40 (+1 every 2 seconds)"}
    act = t._spend(clock, 3)
    assert act.op == "wait" and t.plan_note == "let the turn clock refill"
    legacy = {"chip": "YOUR MOVE", "turnsFace": "3/40"}
    assert t._spend(legacy, 3).key == "."
    assert t._spend({**clock, "turnsFace": "30/40 (+1 every 2 seconds)"}, 30).key == "."
    warn = {"menuOpen": True, "menuText": "One more Wait ends your day.", **clock}
    act = t._modal(warn, ["CONFIRM"], 3)
    assert act.key == "Escape"
    assert t._modal({**warn, "turnsFace": "3/40"}, ["CONFIRM"], 3).label == "CONFIRM"
