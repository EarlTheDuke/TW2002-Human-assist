"""Corp rules scenario lab (corp-rules-v1 MATCH CHECK (e)). No server, no paid call.

Prints corp_rules_scenario_lab: PASS when the spec's scene holds under CORP_MODE tw2002.
A is the C.E.O., B and C join (C is evil, so the corp is mixed), D never joins.
"""

from __future__ import annotations

from tw2k.engine import GameConfig, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.constants import hull_spec
from tw2k.engine.models import EventKind, Player
from tw2k.engine.runner import _apply_sector_hazards, apply_action, tick_day


def _act(u, pid: str, kind: str, **args):
    return apply_action(u, pid, Action(kind=ActionKind(kind), args=args))


def _move(u, pid: str, sid: int) -> None:
    for s in u.sectors.values():
        if pid in s.occupant_ids:
            s.occupant_ids.remove(pid)
    u.players[pid].sector_id = sid
    u.sectors[sid].occupant_ids.append(pid)


def _snap(u, pid: str, sid: int):
    p, dep = u.players[pid], u.sectors[sid].fighters
    return (p.ship.fighters, p.ship.shields, p.alive, dep.count if dep else None)


def main() -> dict:
    assert K.corp_rules_on(), "run with CORP_MODE tw2002"
    u = generate_universe(GameConfig(
        seed=57, universe_size=90, max_days=6, turns_per_day=200,
        starting_credits=25_000, enable_ferrengi=False, enable_planets=True,
    ))
    names = {"A": "Ann", "B": "Bo", "C": "Cy", "D": "Dee"}
    for pid, name in names.items():
        u.players[pid] = Player(id=pid, name=name, agent_kind="external", sector_id=1, credits=25_000)
        u.sectors[1].occupant_ids.append(pid)
    far = [sid for sid in sorted(u.sectors) if sid not in K.FEDSPACE_SECTORS and sid > 20]
    s500, s600, s700, s800 = far[:4]
    out: dict = {}

    _move(u, "A", s800)  # away from StarDock
    assert _act(u, "A", "corp_create", ticker="XYZ", name="Xyz Holdings").ok
    assert u.players["A"].credits == 25_000, "create is free"
    out["create_cost"] = 0
    res = _act(u, "B", "corp_join", ticker="XYZ", password="")
    assert not res.ok, "join refused while no password is set"
    assert _act(u, "A", "corp_set_password", password="Zx9").ok
    first = _act(u, "B", "corp_join", ticker="XYZ", password="zx9")
    second = _act(u, "B", "corp_join", ticker="XYZ", password="Zx9")
    assert not first.ok and not second.ok, "case-exact, then one break-in a day"
    out["breakin"] = [first.error, second.error]
    tick_day(u)
    assert _act(u, "B", "corp_join", ticker="XYZ", password="Zx9").ok
    u.players["C"].alignment = -500
    assert _act(u, "C", "corp_join", ticker="XYZ", password="Zx9").ok, "mixed corps are legal (TWGS)"
    u.players["A"].alignment, u.players["B"].alignment = 1200, 800
    for pid in "ABC":
        u.players[pid].experience = 5_000
    n_ev = len(u.events)
    tick_day(u)
    loss = {e.actor_id: e.payload["loss"] for e in u.events[n_ev:] if e.kind == EventKind.CORP_EXP_PENALTY}
    assert set(loss) == {"A", "B", "C"} and set(loss.values()) == {1200 // 4}, loss
    out["extern_loss"] = loss

    _move(u, "A", s500)
    _move(u, "B", s500)
    cap = int(hull_spec(u.players["B"].ship.ship_class.value)["max_fighters"])
    u.players["A"].ship.fighters, u.players["B"].ship.fighters = 1_000, cap - 500
    res = _act(u, "A", "corp_transfer", target="B", item="fighters", qty=1_000, direction="give")
    assert not res.ok and "500" in (res.error or ""), res.error
    assert u.players["B"].ship.fighters == cap - 500
    u.players["A"].ship.shields, u.players["B"].ship.shields = 400, 0
    assert _act(u, "B", "corp_transfer", target="A", item="shields", qty=300, direction="take").ok
    assert (u.players["A"].ship.shields, u.players["B"].ship.shields) == (100, 300)

    _move(u, "A", s600)
    assert _act(u, "A", "deploy_fighters", qty=200, mode="offensive", ownership="corporate").ok
    assert u.sectors[s600].fighters.corp_ticker == "XYZ"
    _move(u, "B", s600)
    before = _snap(u, "B", s600)
    _apply_sector_hazards(u, "B", u.sectors[s600], entry_verb="entering")
    assert _snap(u, "B", s600) == before, "a member passes corporate fighters"
    u.players["D"].ship.fighters = 20
    _move(u, "D", s600)
    before = _snap(u, "D", s600)
    _apply_sector_hazards(u, "D", u.sectors[s600], entry_verb="entering")
    assert _snap(u, "D", s600) != before, "a non-member is attacked"
    _move(u, "D", 1)

    _move(u, "B", s700)
    assert _act(u, "B", "deploy_fighters", qty=100, mode="offensive", ownership="personal").ok
    assert u.sectors[s700].fighters.corp_ticker is None
    _move(u, "A", s700)
    before = _snap(u, "A", s700)
    _apply_sector_hazards(u, "A", u.sectors[s700], entry_verb="entering")
    assert _snap(u, "A", s700) != before, "personal fighters attack a corp mate"

    planet = next(pl for pl in u.planets.values() if pl.sector_id not in K.FEDSPACE_SECTORS)
    planet.owner_id, planet.corp_ticker = "C", "XYZ"
    u.players["C"].ship.fighters = 40
    assert _act(u, "A", "corp_drop", target="C").ok
    assert u.players["C"].corp_ticker is None and u.players["C"].ship.fighters == 40
    assert planet.owner_id == "A", (planet.owner_id, K.CORP_LEAVER_PLANETS)

    _move(u, "A", s800)
    u.sectors[s800].fighters = None
    assert _act(u, "A", "deploy_fighters", qty=10, mode="defensive", ownership="corporate").ok
    assert _act(u, "A", "corp_leave").ok
    assert "XYZ" not in u.corporations and u.players["B"].corp_ticker is None
    home, away = u.sectors[s800].fighters, u.sectors[s600].fighters
    assert (home.owner_id, home.corp_ticker) == ("A", None), "C.E.O. sector: his personal"
    assert (away.owner_id, away.corp_ticker) == (K.ROGUE_OWNER_ID, None), "elsewhere: rogue"
    u.players["B"].ship.fighters = 50
    _move(u, "B", s600)
    before = _snap(u, "B", s600)
    _apply_sector_hazards(u, "B", u.sectors[s600], entry_verb="entering")
    assert _snap(u, "B", s600) != before, "rogue fighters attack the former member"
    assert _act(u, "B", "corp_deposit", amount=10).error == "unsupported action"
    print("corp_rules_scenario_lab: PASS")
    print(out)
    return out


if __name__ == "__main__":
    main()
