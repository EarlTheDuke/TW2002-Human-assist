"""Parity S3 - legal_actions() engine query + legality-gated verb pad on /bot.

Matrix: for each fixture state x each PRECISE verb, `legal_actions[kind].legal`
must equal `apply_action(...).ok` when the action is built from the envelope
the query itself advertises (choices / min / max). Haggle prices are never
passed (rejected asks settle at list, so they cannot flip ok anyway).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tw2k.agents.prompts import format_observation
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.legality import LegalAction, legal_actions
from tw2k.engine.models import Commodity, Player, PortClass
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import apply_action

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "web" / "bot.html").read_text(encoding="utf-8")
JS = (ROOT / "web" / "bot.js").read_text(encoding="utf-8")

PRECISE = ("warp", "scan", "wait", "trade", "plot_course", "probe", "hail", "broadcast")


def _universe(seed: int = 21):
    cfg = GameConfig(seed=seed, universe_size=80, max_days=3, turns_per_day=12, starting_credits=25_000,
                     enable_ferrengi=False, enable_planets=True)
    u = generate_universe(cfg)
    for pid, name, sid in (("P1", "Me", 1), ("P2", "Rival", 2)):
        p = Player(id=pid, name=name, agent_kind="external", sector_id=sid, credits=25_000)
        u.players[pid] = p
        u.sectors[sid].occupant_ids.append(pid)
        p.known_sectors.add(sid)
        p.known_warps[sid] = list(u.sectors[sid].warps)
    return u


def _trading_port_sector(u):
    for sid in sorted(u.sectors):
        s = u.sectors[sid]
        if s.port is not None and s.port.class_id != PortClass.STARDOCK and sid > 10:
            return sid
    raise AssertionError("no trading port in fixture universe")


def _move(u, pid: str, sid: int) -> None:
    p = u.players[pid]
    u.sectors[p.sector_id].occupant_ids = [x for x in u.sectors[p.sector_id].occupant_ids if x != pid]
    p.sector_id = sid
    u.sectors[sid].occupant_ids.append(pid)
    p.known_sectors.add(sid)
    p.known_warps[sid] = list(u.sectors[sid].warps)


def _fixtures() -> list[tuple[str, object]]:
    out = []
    u = _universe(); out.append(("stardock-fresh", u))

    u = _universe(); sid = _trading_port_sector(u); _move(u, "P1", sid)
    port = u.sectors[sid].port
    # give cargo of something the port buys so a sell is possible
    for c in (Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT):
        if port.buys(c):
            u.players["P1"].ship.cargo[c] = 5
            break
    out.append(("trading-port", u))

    u = _universe(); sid = _trading_port_sector(u); _move(u, "P1", sid)
    u.players["P1"].credits = 0
    u.players["P1"].ship.cargo = {}
    out.append(("trading-port-broke-empty", u))

    u = _universe(); u.players["P1"].turns_today = u.players["P1"].turns_per_day; out.append(("out-of-turns", u))

    u = _universe(); u.players["P1"].turns_today = u.players["P1"].turns_per_day - 1; out.append(("one-turn-left", u))

    u = _universe(); u.players["P1"].ship.ether_probes = 2; out.append(("has-probes", u))

    u = _universe()
    planet_sid = next((pl.sector_id for pl in u.planets.values()), None)
    if planet_sid is not None:
        _move(u, "P1", planet_sid)
        pl = next(pl for pl in u.planets.values() if pl.sector_id == planet_sid)
        u.players["P1"].planet_landed = pl.id
    out.append(("landed", u))

    u = _universe(); u.players["P1"].alive = False; out.append(("dead", u))
    return out


def _build_action(kind: str, la: LegalAction, u) -> Action | None:
    p = la.params
    if kind == "warp":
        ch = p.get("target", {}).get("choices") or list(u.sectors[u.players["P1"].sector_id].warps)
        return Action(kind=ActionKind.WARP, args={"target": ch[0]}) if ch else None
    if kind == "scan":
        return Action(kind=ActionKind.SCAN, args={})
    if kind == "wait":
        return Action(kind=ActionKind.WAIT, args={})
    if kind == "probe":
        return Action(kind=ActionKind.PROBE, args={"target": 2})
    if kind == "plot_course":
        # a direct neighbour is always routable, so route-existence cannot mask the legality check
        warps = list(u.sectors[u.players["P1"].sector_id].warps)
        return Action(kind=ActionKind.PLOT_COURSE, args={"target": warps[0], "execute": False}) if warps else None
    if kind == "hail":
        ch = p.get("target", {}).get("choices") or ["P2"]
        return Action(kind=ActionKind.HAIL, args={"target": ch[0], "message": "hi"})
    if kind == "broadcast":
        return Action(kind=ActionKind.BROADCAST, args={"message": "hi all"})
    if kind == "trade":
        comm = p.get("commodity", {})
        max_by = p.get("qty", {}).get("max_by", {})
        for side, key in (("sell", "sell_choices"), ("buy", "buy_choices")):
            for c in comm.get(key, []) or []:
                mx = int((max_by.get(c) or {}).get(side, 0))
                if mx > 0:
                    return Action(kind=ActionKind.TRADE, args={"commodity": c, "qty": min(3, mx), "side": side})
        # nothing advertised as tradeable: try the port's first commodity, qty 1 - engine must reject
        sector = u.sectors[u.players["P1"].sector_id]
        if sector.port is not None and sector.port.class_id != PortClass.STARDOCK:
            c = next(iter(sector.port.stock)).value
            side = "buy" if sector.port.sells(next(iter(sector.port.stock))) else "sell"
            return Action(kind=ActionKind.TRADE, args={"commodity": c, "qty": 1, "side": side})
        return Action(kind=ActionKind.TRADE, args={"commodity": "fuel_ore", "qty": 1, "side": "buy"})
    return None


@pytest.mark.parametrize("label,u", _fixtures(), ids=lambda x: x if isinstance(x, str) else "")
def test_matrix_legal_matches_apply_action(label: str, u) -> None:
    las = {la.kind: la for la in legal_actions(u, "P1")}
    assert len(las) == len(ActionKind), "one entry per ActionKind"
    for kind in PRECISE:
        la = las[kind]
        assert la.detail == "precise", kind
        action = _build_action(kind, la, u)
        if action is None:
            assert not la.legal, f"{label}/{kind}: legal but no action could be built"
            continue
        u2 = copy.deepcopy(u)
        res = apply_action(u2, "P1", action)
        assert res.ok == la.legal, f"{label}/{kind}: legal_actions={la.legal} ({la.reason}) engine={res.ok} ({res.error})"
        if not la.legal:
            assert la.reason, f"{label}/{kind}: blocked without a reason"


def test_query_is_pure_and_deterministic() -> None:
    u = _universe()
    before = json.dumps(u.model_dump(mode="json"), sort_keys=True, default=str)
    a = [la.model_dump() for la in legal_actions(u, "P1")]
    b = [la.model_dump() for la in legal_actions(u, "P1")]
    after = json.dumps(u.model_dump(mode="json"), sort_keys=True, default=str)
    assert a == b and before == after
    assert [x["kind"] for x in a] == [k.value for k in ActionKind]  # engine order


def test_trade_envelope_uses_listed_price_and_engine_caps() -> None:
    u = _universe(); sid = _trading_port_sector(u); _move(u, "P1", sid)
    port = u.sectors[sid].port
    p = u.players["P1"]
    p.credits = 100  # cheap: cap must reflect affordability at LIST price
    la = {x.kind: x for x in legal_actions(u, "P1")}["trade"]
    env = la.params
    listed = env["unit_price"]["listed_by"]
    for c, sides in env["qty"]["max_by"].items():
        if "buy" in sides:
            unit = listed[c]["buy"]
            assert sides["buy"] <= p.credits // unit
            assert sides["buy"] <= p.ship.cargo_free
            assert sides["buy"] <= port.stock[Commodity(c)].current
        if "sell" in sides:
            assert sides["sell"] <= int(p.ship.cargo.get(Commodity(c), 0))


def test_observation_and_llm_message_carry_legality() -> None:
    u = _universe()
    obs = build_observation(u, "P1")
    kinds = {e["kind"] for e in obs.legal_actions}
    assert kinds == {k.value for k in ActionKind}
    warp = next(e for e in obs.legal_actions if e["kind"] == "warp")
    assert warp["legal"] is True and warp["params"]["target"]["choices"] == list(u.sectors[1].warps)
    msg = json.loads(format_observation(obs))
    assert "legal_actions" in msg
    assert "warp" in msg["legal_actions"]["legal"] and "scan" in msg["legal_actions"]["legal"]
    assert "trade" in msg["legal_actions"]["blocked"]  # StarDock has no commodity market
    assert isinstance(msg["legal_actions"]["blocked"]["trade"], str)


def test_bot_verb_pad_is_gated_by_legal_actions_only() -> None:
    assert 'data-obs="legal_actions"' in HTML
    for tid in ("verb-pad", "action-scan", "action-wait", "action-trade", "action-plot-course", "action-probe",
                "verb-reasons", "verb-form", "more-verbs", "action-sell", "action-buy"):
        assert f'data-testid="{tid}"' in HTML, tid
    # Disabled buttons carry the engine's reason; no rule constants in JS.
    assert 'setAttribute("data-reason"' in JS and "legal_actions" in JS and "canUse(" in JS
    for forbidden in ("TURN_COST", "STARDOCK_SECTOR", "FEDSPACE", "COMMODITY_BASE_PRICE", "SHIP_SPECS"):
        assert forbidden not in JS, forbidden
    # Trade form reads the envelope (choices / max_by / listed_by), never recomputes prices.
    for key in ("buy_choices", "sell_choices", "max_by", "listed_by", "unit_price"):
        assert key in JS, key
    # Forms exist for every S3 verb.
    for kind in ("trade", "plot_course", "probe", "scan", "wait", "warp"):
        assert f'kind === "{kind}"' in JS, kind
