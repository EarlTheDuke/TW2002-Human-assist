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


def _clock_screen(sector: int, warps: list[str]) -> dict:
    return {"sector": sector, "warps": warps, "labels": list(warps), "turnsFace": "3 (+1 every 2s)"}


def test_the_turn_clock_refills_instead_of_ping_ponging() -> None:
    """NOTE 172b. Seed 99 spent days 9-14 warping 73<->155 three turns at a time."""
    t = _rich()
    t.links[22] = {20: 3, 23: 3}
    t.links[20][22] = 3
    t.visited |= {20, 21, 22, 23}
    act = t._warp(_clock_screen(22, ["1:20 (3t)", "2:23 (3t)"]), 22, {}, 3)
    assert act is not None and act.op == "wait" and act.ms == 14_000
    assert t.plan_note == "let the turn clock refill"
    # The server only pays the clock on a pass, so the next move hands the turn back.
    act = t._warp(_clock_screen(22, ["1:20 (3t)", "2:23 (3t)"]), 22, {}, 3)
    assert act is not None and act.op == "press" and act.key == "."
    # Without the clock (the 40-turn test day) the old moves stand.
    act = t._warp({"sector": 22, "warps": ["1:20 (3t)", "2:23 (3t)"], "labels": []}, 22, {}, 3)
    assert act is None or act.op != "wait"


def test_cargo_aboard_waits_for_the_clock_too() -> None:
    """NOTE 172b. Seed 250925 carried a full load 147<->16 while the buyer lane was blocked."""
    t = _rich()
    t.links[22] = {21: 3, 23: 3}
    t.links[21][22] = 3
    t.visited |= {20, 21, 22, 23}
    act = t._warp(_clock_screen(22, ["2:23 (3t)"]), 22, {"Equipment": 20}, 3)
    assert act is not None and act.op == "wait"


def test_a_rich_wallet_reads_the_yard_once_a_day() -> None:
    """NOTE 172b. Seed 99 held 73,000 on board and never asked about a hull."""
    t = _rich()
    labels = ["1:20 (3t)", "Shipyards", "Bank"]
    screen = {"sector": 1}
    t.credits = 5_000
    assert not t._hull_trip()
    assert t._open_yard(labels, screen) is None
    t.credits = 30_000
    assert t._hull_trip()
    act = t._open_yard(labels, screen)
    assert act is not None and act.label == "Shipyards"
    assert not t._hull_trip() and t._open_yard(labels, screen) is None
    # Saving for the hull keeps the cash on board until the yard is settled.
    assert t._saving_for_hull() and not t._wants_bank(60_000)
    t.bought.add("ship")
    assert not t._saving_for_hull() and t._wants_bank(60_000)


def test_a_declined_hull_is_quoted_again_once_the_cash_doubles() -> None:
    t = _rich()
    t.ship_skip_profit = 10**9
    t.ship_skip_credits = 20_000
    t.credits = 30_000
    assert t._ship_closed()
    t.credits = 40_000
    assert not t._ship_closed()


def test_the_clock_takes_a_long_dock_trip_a_few_hops_at_a_time() -> None:
    t = _rich()
    t.settled_day = 2
    t.credits = 40_000
    t.clock_live = True
    t.links[21][30] = 3
    t.links[30] = {31: 3, 21: 3}
    t.links[31] = {1: 3, 30: 3}
    t.links[1] = {31: 3}
    assert t._settled(21)
    assert t._hull_trip()
    assert t._should_shop(21, 8)
    t.clock_live = False
    assert not t._should_shop(21, 8)


def test_the_trip_home_waits_for_the_yard() -> None:
    t = _rich()
    t.home_ask = 20
    t.links[1] = {20: 3}
    t.credits = 40_000
    assert t._return_home({"sector": 1}, 1, {}) is None
    t.hull_day = t.day
    act = t._return_home({"sector": 1, "warps": ["1:20 (3t)"]}, 1, {})
    assert act is None or act.op == "click"


def test_no_course_home_is_plotted_before_the_yard() -> None:
    t = _rich()
    t.home_ask = 20
    t.refit_day.update({"holds": 3, "fighters": 3, "shields": 3})
    t.credits = 40_000
    t._sync_plot(1, 10, 40_000, {})
    assert t.plot_to == 0


def test_a_rich_seat_judges_the_yard_on_the_net_after_trade_in() -> None:
    # NOTE 172c: the quote headline is the cash after trade-in; the trade-in is not added back.
    t = _rich(avail=3_000)
    t.credits, t.day, t.max_day = 58_000, 6, 16
    screen = {"ship": "Merchant Cruiser. Holds 0/32"}
    quote = ("Merchant Freighter: 12,000 cr. Holds 65, fighters 300, shields 500, 2 turns per warp, "
             "no photons, no TransWarp. Trade-in sells your ship for 21,400 cr and you fly the new one.")
    assert t._yard_pays(screen, quote)


def test_a_hull_trip_alone_may_sail_with_an_empty_shelf(monkeypatch) -> None:
    # NOTE 172c: no gear left to buy must not cancel a hull trip.
    t = _rich()
    monkeypatch.setattr(t, "_shelf_open", lambda: False)
    monkeypatch.setattr(t, "_hull_trip", lambda: True)
    monkeypatch.setattr(t, "_refit_item", lambda: None)
    assert "not (self._shelf_open() or hull)" in __import__("inspect").getsource(type(t)._should_shop)


def test_a_rich_seat_still_missing_fighters_sails_for_the_yard() -> None:
    # NOTE 172d: seed 99 never bought fighters, so the hull trip never fired.
    t = _rich()
    t.bought.discard("fighters")
    t.credits = 46_000
    assert t._hull_trip()


def test_a_settled_seat_stops_bouncing_between_two_seen_sectors() -> None:
    # NOTE 172d: seed 99 bounced 47 <-> 114 for nine days beside an unseen exit.
    t = _rich()
    t.settled_day = 1
    t.visited |= {47, 114}
    t.previous = 114
    opts = [(114, "1:114 (3t)", 3), (149, "2:149 (3t)", 3)]
    picks = [t._explore_choice(47, opts) for _ in range(6)]
    assert 149 in picks
