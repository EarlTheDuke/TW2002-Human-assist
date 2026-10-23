"""GAP 5.7: the tw2002 ship exchange is the printed expected-value formula.

Bible (S3), Scout Marauder: "2 to 1 fighting odds (that means, theoretically
you should be able to kill 500 fighters with its 250)".
S2 cabal formulas: "you attack with 1:1 odds, losing 1,000 figs" against 1,000.
S7: "Enemy Fighters x Enemy Ships Combat Odds = Real Fighter Strength ...
Real Fighter Strength / Your Ships Combat Odds = # of Fighters to Use", shields
the same way; "I was unable to determine the random factors". No source prints
a random term, so the clone uses the expected value under every profile.
"""

from __future__ import annotations

from fractions import Fraction

import pytest

import tw2k.engine.combat as C
import tw2k.engine.constants as K
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.models import Player, Ship, ShipClass


def _u():
    return generate_universe(GameConfig(
        seed=57, universe_size=80, max_days=3, turns_per_day=40,
        starting_credits=50_000, enable_ferrengi=False, enable_planets=False,
    ))


def _seat(u, pid, fighters, shields=0, sector=20):
    p = Player(
        id=pid, name=pid,
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, fighters=fighters, shields=shields, holds=20),
        sector_id=sector, credits=0, alignment=0, experience=0, turns_per_day=40,
    )
    u.players[pid] = p
    u.sectors[sector].occupant_ids.append(pid)
    return p


def _fight(monkeypatch, a_odds, d_odds, sent, d_f, d_s=0, profile="legacy"):
    monkeypatch.setattr(K, "V311_PROFILE", profile)
    u = _u()
    a = _seat(u, "A", fighters=sent)
    d = _seat(u, "D", fighters=d_f, shields=d_s)
    odds = {"A": Fraction(a_odds), "D": Fraction(d_odds)}
    monkeypatch.setattr(C, "combat_odds_of", lambda t: odds[getattr(t, "id", "D")])
    monkeypatch.setattr(C, "_flee_destination", lambda *x, **k: None)
    C._resolve_ship_attack_tw2002(u, "A", d, sent)
    return a, d


def _beaten(d) -> bool:
    # Beaten ships drop to a pod (or are captured) under some profiles.
    return d.ship.ship_class == ShipClass.ESCAPE_POD or d.ship.fighters == 0


@pytest.mark.parametrize("profile", ["legacy", "v311"])
def test_bible_scout_two_to_one(monkeypatch, profile):
    a, d = _fight(monkeypatch, 2, 1, 250, 500, profile=profile)
    assert _beaten(d)
    assert a.ship.fighters == 0  # all 250 spent to kill 500


@pytest.mark.parametrize("profile", ["legacy", "v311"])
def test_s2_one_to_one_costs_what_it_kills(monkeypatch, profile):
    a, d = _fight(monkeypatch, 1, 1, 1000, 1000, profile=profile)
    assert _beaten(d) and a.ship.fighters == 0


def test_s7_fighters_to_use_includes_shields(monkeypatch):
    # (F + S) x enemy odds / your odds = 1,000 x 1.5 / 1 = 1,500 to use.
    a, d = _fight(monkeypatch, 1, Fraction(3, 2), 1499, 800, d_s=200)
    assert d.ship.shields == 0 and d.ship.fighters > 0  # shields go first
    a, d = _fight(monkeypatch, 1, Fraction(3, 2), 1600, 800, d_s=200)
    assert d.ship.fighters == 0 and d.ship.shields == 0
    assert a.ship.fighters == 100  # spent exactly 1,500


def test_no_random_term(monkeypatch):
    runs = {(_fight(monkeypatch, 1, 1, 300, 1000)[1].ship.fighters) for _ in range(5)}
    assert runs == {700}


@pytest.mark.parametrize("profile", ["legacy", "v311"])
def test_short_volley_kills_odds_times_sent(monkeypatch, profile):
    a, d = _fight(monkeypatch, 2, 1, 249, 500, profile=profile)
    assert a.ship.fighters == 0 and d.ship.fighters == 2


def test_manual_states_the_formula():
    from tw2k.public import manual
    assert "divided by theirs, of the target" in open(manual.__file__).read()
