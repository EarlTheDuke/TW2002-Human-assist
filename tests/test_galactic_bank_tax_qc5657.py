"""QC slice 56 (galactic-bank-tax-v1): rules, reasons and fog the slice tests did not cover."""

from __future__ import annotations

import copy
import random

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe, tick_day
from tw2k.engine import constants as K
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, Ship
from tw2k.engine.observation import build_observation
from tw2k.engine.victory import full_net_worth

VERBS = ("bank_deposit", "bank_withdraw", "bank_transfer")


def _world(credits=1_000_000, alignment=0, sector=1, n_others=2):
    u = generate_universe(GameConfig(
        seed=3, universe_size=40, max_days=12, enable_planets=False, enable_ferrengi=False,
    ))
    for pid, name, cash in [("A", "Ada", credits)] + [(f"O{i}", f"Oth{i}", 50_000) for i in range(n_others)]:
        p = Player(id=pid, name=name, ship=Ship(), credits=cash, alignment=alignment, experience=0)
        p.sector_id = sector if pid == "A" else 7
        u.players[pid] = p
        u.sectors[p.sector_id].occupant_ids.append(pid)
    return u, u.players["A"]


def _do(u, kind, pid="A", **args):
    return apply_action(u, pid, Action(kind=ActionKind(kind), args=args))


def _la(u, pid, kind):
    return next(la for la in legal_actions(u, pid) if getattr(la.kind, "value", la.kind) == kind)


def test_qc_empty_side_reasons():
    u, a = _world(credits=0)
    assert _la(u, "A", "bank_deposit").reason == "no credits on hand"
    assert _la(u, "A", "bank_withdraw").reason == "nothing in the account"
    assert _la(u, "A", "bank_transfer").reason == "no credits on hand"
    a.credits = 10
    a.bank_balance = K.BANK_MAX_BALANCE
    assert _la(u, "A", "bank_deposit").reason == "account full"
    assert _la(u, "A", "bank_deposit").params["capacity"] == K.BANK_MAX_BALANCE


def test_qc_transfer_is_illegal_when_every_account_is_full():
    u, _a = _world()
    for pid in ("O0", "O1"):
        u.players[pid].bank_balance = K.BANK_MAX_BALANCE
    la = _la(u, "A", "bank_transfer")
    assert la.legal is False and la.params["max_amount"] == 0
    assert _do(u, "bank_transfer", to_player="O0", amount=1).ok is False


def test_qc_balance_view_stardock_alt(monkeypatch):
    monkeypatch.setattr(K, "BANK_BALANCE_VIEW", "stardock")
    u, a = _world(sector=1)
    assert build_observation(u, "A").bank_balance == 0
    u.sectors[1].occupant_ids.remove("A")
    a.sector_id = 7
    u.sectors[7].occupant_ids.append("A")
    assert build_observation(u, "A").bank_balance is None
    monkeypatch.setattr(K, "BANK_BALANCE_VIEW", "always")
    assert build_observation(u, "A").bank_balance == 0


def test_qc_sd_trader_is_a_recipient_and_eliminated_reads_like_unknown():
    u, _a = _world()
    sd = u.players["O0"]
    sd.turns_today = sd.turns_per_day  # #SD#: out until tomorrow, still alive
    assert any(r["player_id"] == "O0" for r in _la(u, "A", "bank_transfer").params["recipients"])
    assert _do(u, "bank_transfer", to_player="O0", amount=100).ok
    u.players["O1"].alive = False
    gone = _do(u, "bank_transfer", to_player="O1", amount=100)
    unknown = _do(u, "bank_transfer", to_player="ZZ", amount=100)
    assert gone.error == unknown.error and gone.ok is False
    # plant q19 (QC 56): the eliminated trader is not offered as a recipient either
    assert all(r["player_id"] != "O1" for r in _la(u, "A", "bank_transfer").params["recipients"])


def test_qc_transfer_events_fog():
    u, _a = _world()
    assert _do(u, "bank_transfer", to_player="O0", amount=1234).ok
    seen_a = [e["kind"] for e in build_observation(u, "A").model_dump(mode="json")["recent_events"]]
    seen_b = [e["kind"] for e in build_observation(u, "O0").model_dump(mode="json")["recent_events"]]
    seen_c = [e["kind"] for e in build_observation(u, "O1").model_dump(mode="json")["recent_events"]]
    assert "bank_transfer" in seen_a and "bank_transfer_received" not in seen_a
    assert "bank_transfer_received" in seen_b and "bank_transfer" not in seen_b
    assert not ({"bank_transfer", "bank_transfer_received"} & set(seen_c))
    assert "1234" not in build_observation(u, "O1").model_dump_json()


def test_qc_rival_obs_never_carries_a_balance_or_tax():
    u, a = _world(credits=400_000)
    assert _do(u, "bank_deposit", amount=123_457).ok
    tick_day(u)
    blob = build_observation(u, "O0").model_dump_json()
    assert "123457" not in blob and "123,457" not in blob
    assert "tax_collected" not in blob
    rival_rows = build_observation(u, "O0").model_dump(mode="json").get("rivals") or []
    for row in rival_rows if isinstance(rival_rows, list) else []:
        assert "bank_balance" not in row


def test_qc_tax_skips_eliminated_and_taxes_sd_trader():
    u, a = _world(credits=200_000)
    sd = u.players["O0"]
    sd.credits = 200_000
    sd.turns_today = sd.turns_per_day
    gone = u.players["O1"]
    gone.credits = 200_000
    gone.alive = False
    tick_day(u)
    assert sd.credits == 200_000 - 10_000
    assert gone.credits == 200_000


def test_qc_tax_never_drives_cash_negative_and_alignment_cap_variants(monkeypatch):
    u, a = _world(credits=965_000_000, alignment=10)
    tick_day(u)
    assert a.credits == 965_000_000 - 965_000_000 * 5 // 100
    assert a.alignment == 10 + K.DAILY_ALIGNMENT * (1 if K.rank_tw2002() else 0)
    monkeypatch.setattr(K, "TAX_ALIGN_OVERFLOW", "clamp")
    u2, b = _world(credits=965_000_000, alignment=10)
    tick_day(u2)
    assert b.alignment == 10 + 31_999 + K.DAILY_ALIGNMENT * (1 if K.rank_tw2002() else 0)


def test_qc_conservation_bank_verbs_move_money_only():
    u, a = _world(credits=300_000)

    def total():
        return sum(int(p.credits) + int(p.bank_balance) for p in u.players.values())

    before = total()
    assert _do(u, "bank_deposit", amount=100_000).ok
    assert _do(u, "bank_withdraw", amount=30_000).ok
    assert _do(u, "bank_transfer", to_player="O0", amount=5_000).ok
    assert total() == before
    assert full_net_worth(u, a) + full_net_worth(u, u.players["O0"]) > 0


def test_qc_legacy_has_no_bank_anywhere(monkeypatch):
    monkeypatch.setattr(K, "BANK_MODE", "legacy")
    u, a = _world(credits=300_000)
    kinds = {getattr(la.kind, "value", la.kind) for la in legal_actions(u, "A")}
    assert not (kinds & set(VERBS))
    a.alive = False
    kinds = {getattr(la.kind, "value", la.kind) for la in legal_actions(u, "A")}
    assert not (kinds & set(VERBS))
    a.alive = True
    for verb in VERBS:
        assert _do(u, verb, amount=1, to_player="O0").error == "unsupported action"
    tick_day(u)
    assert a.credits == 300_000
    obs = build_observation(u, "A").model_dump(mode="json")
    assert "bank_balance" not in obs and "tax_due_tomorrow" not in obs
    assert "bank_balance" not in a.model_dump()


def test_qc_death_credits_matrix_by_cause():
    from tw2k.engine.combat import _destroy_ship
    for reason, by_other, killer, paid in (
        ("combat", True, "O0", True), ("captured", True, "O0", True),
        ("mines", False, None, False), ("sector_fighters", False, "O0", False),
        ("surrender", False, "O0", False), ("quasar", False, "O0", False),
        ("federal", True, None, False), ("navhaz", False, None, False),
    ):
        u, a = _world(credits=90_000)
        a.bank_balance = 40_000
        k = u.players["O0"]
        k_before = int(k.credits)
        _destroy_ship(u, "A", reason, killer_id=killer, by_other=by_other)
        assert a.credits == 0, reason
        assert a.bank_balance == 40_000, reason
        assert (int(k.credits) - k_before == 90_000) is paid, reason


def test_qc_property_legal_matches_handler():
    rng = random.Random(56)
    for trial in range(150):
        u, a = _world(credits=rng.choice([0, 1, 999, 100_000, 700_000]),
                      sector=rng.choice([1, 1, 7]))
        a.bank_balance = rng.choice([0, 1, 250_000, K.BANK_MAX_BALANCE])
        for pid in ("O0", "O1"):
            u.players[pid].bank_balance = rng.choice([0, 499_999, K.BANK_MAX_BALANCE])
        if rng.random() < 0.2:
            a.planet_landed = 1
        if rng.random() < 0.1:
            a.turns_today = a.turns_per_day
        for verb in VERBS:
            la = _la(u, "A", verb)
            maximum = int(la.params.get("max_amount") or 0)
            args = {"amount": max(1, maximum)}
            if verb == "bank_transfer":
                rows = [r for r in la.params.get("recipients", []) if int(r["max_amount"]) == maximum] or \
                    la.params.get("recipients", [])
                args["to_player"] = rows[0]["player_id"] if rows else "O0"
            v = copy.deepcopy(u)
            res = apply_action(v, "A", Action(kind=ActionKind(verb), args=args))
            assert res.ok == la.legal, (trial, verb, args, la.reason, res.error)
            if la.legal:
                over = dict(args, amount=maximum + 1)
                w = copy.deepcopy(u)
                assert apply_action(w, "A", Action(kind=ActionKind(verb), args=over)).ok is False


def test_qc_pb21_death_mode_legacy_keeps_its_x075_path_under_bank_tw2002(monkeypatch):
    """pb21: DEATH_MODE legacy keeps x0.75 whatever BANK_MODE says; no cash goes to the killer."""
    from tw2k.engine.combat import _destroy_ship
    u, who = _world(credits=80_000)
    killer = u.players["O0"]
    killer.sector_id = who.sector_id
    k0 = int(killer.credits)
    assert K.bank_on() and K.DEATH_CREDITS_ON_HAND == "lost"
    monkeypatch.setattr(K, "DEATH_MODE", "legacy")
    _destroy_ship(u, "A", "attack", killer_id="O0", by_other=True)
    assert who.credits == int(80_000 * 0.75)
    assert killer.credits == k0


def test_qc_eliminated_trader_cannot_bank():
    """Plant q4 (QC 56): the alive guard; an eliminated trader at StarDock is refused by list and handler."""
    u, who = _world(credits=100_000)
    who.bank_balance = 10_000
    who.alive = False
    for kind, args in (("bank_deposit", {"amount": 1}), ("bank_withdraw", {"amount": 1}),
                       ("bank_transfer", {"to_player": "O0", "amount": 1})):
        assert not _la(u, "A", kind).legal
        assert _do(u, kind, **args).ok is False
    assert who.credits == 100_000 and who.bank_balance == 10_000
