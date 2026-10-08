"""The war report counts verbs. It does not decide them."""

from __future__ import annotations

from tw2k.agents.war_report import counts_from_events


def test_bw27_report() -> None:
    events = [
        {"actor": "P1", "kind": "deploy_mines", "payload": {"kind": "armid", "qty": 5}},
        {"actor": "P1", "kind": "deploy_fighters", "payload": {"mode": "offensive", "qty": 10}},
        {"actor": "P2", "kind": "deploy_mines", "payload": {"kind": "armid", "qty": 2, "ownership": "corporate"}},
        {"actor": "P1", "kind": "deposit_planet_defense", "payload": {"kind": "fighters", "qty": 500}},
        {"actor": "P1", "kind": "planet_military_reaction", "payload": {"planet_id": 1}},
        {"actor": "P1", "kind": "planet_defense_transfer", "payload": {"kind": "shields", "qty": 10, "direction": "withdraw"}},
        {"actor": "P1", "kind": "set_quasar_sector", "payload": {"pct": 30}},
        {"actor": "P1", "kind": "set_quasar_atm", "payload": {"pct": 60}},
        {"kind": "deploy_mines", "payload": {"qty": 9}},
    ]
    got = counts_from_events(events)
    assert got["P1"]["mines_armid_personal"] == 5
    assert got["P1"]["fighters_offensive_personal"] == 10
    assert got["P1"]["deposit_fighters"] == 500
    assert "deposit_shields" not in got["P1"]
    assert got["P1"]["reaction"] == 1
    assert got["P1"]["quasar_sector"] == 1
    assert got["P1"]["quasar_atm"] == 1
    assert got["P2"]["mines_armid_corporate"] == 2
    assert "" not in got
