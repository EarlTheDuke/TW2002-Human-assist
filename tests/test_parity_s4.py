"""Parity S4 - every ActionKind is `precise` in legal_actions(); matrix vs the engine.

For each fixture state (built to exercise combat, StarDock, planets, corp /
alliance) and EVERY verb, an action is built from the advertised envelope and
`legal_actions[kind].legal` must equal `apply_action(...).ok`. Where the query
says "illegal" we still build a plausible action and the engine must reject it.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.legality import LegalAction, legal_actions
from tw2k.engine.models import Commodity, EventKind, MineType, Player, PortClass
from tw2k.engine.runner import apply_action

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "web" / "bot.html").read_text(encoding="utf-8")
JS = (ROOT / "web" / "bot.js").read_text(encoding="utf-8")

# Outcome-random verbs still return ok=True when legal; nothing to except here.
ALL = [k.value for k in ActionKind]


def _universe(seed: int = 31, **cfg):
    base = dict(seed=seed, universe_size=90, max_days=3, turns_per_day=60, starting_credits=25_000,
                enable_ferrengi=False, enable_planets=True)
    base.update(cfg)
    u = generate_universe(GameConfig(**base))
    for pid, name in (("P1", "Me"), ("P2", "Rival"), ("P3", "Third")):
        p = Player(id=pid, name=name, agent_kind="external", sector_id=1, credits=25_000)
        u.players[pid] = p
        u.sectors[1].occupant_ids.append(pid)
        p.known_sectors.add(1)
        p.known_warps[1] = list(u.sectors[1].warps)
    return u


def _move(u, pid: str, sid: int) -> None:
    p = u.players[pid]
    u.sectors[p.sector_id].occupant_ids = [x for x in u.sectors[p.sector_id].occupant_ids if x != pid]
    p.sector_id = sid
    u.sectors[sid].occupant_ids.append(pid)
    p.known_sectors.add(sid)
    p.known_warps[sid] = list(u.sectors[sid].warps)


def _deep_sector(u, min_hops: int = 3) -> int:
    """A non-FedSpace sector >= min_hops from StarDock (BFS over true warps)."""
    from tw2k.engine.runner import _bfs_path
    for sid in sorted(u.sectors):
        if sid <= 10:
            continue
        hops = len(_bfs_path(u, 1, sid))
        if hops >= min_hops and not (u.sectors[sid].port and u.sectors[sid].port.class_id == PortClass.STARDOCK):
            return sid
    raise AssertionError("no deep sector")


def _a_planet(u):
    return next(iter(u.planets.values()))


def _fixtures() -> list[tuple[str, object]]:
    out = []

    # --- group 1: combat / presence
    u = _universe(); deep = _deep_sector(u); _move(u, "P1", deep); _move(u, "P2", deep)
    u.players["P1"].ship.fighters = 30; u.players["P1"].ship.photon_missiles = 1
    u.players["P1"].ship.mines[MineType.ARMID] = 3
    out.append(("combat-deep-hostile", u))

    u = _universe(); u.players["P1"].ship.photon_missiles = 1; u.players["P1"].ship.mines[MineType.LIMPET] = 2
    out.append(("combat-fedspace-blocked", u))  # P1,P2,P3 all in sector 1

    u = _universe(); deep = _deep_sector(u); _move(u, "P1", deep); _move(u, "P2", deep)
    ok = apply_action(u, "P1", Action(kind=ActionKind.PROPOSE_ALLIANCE, args={"target": "P2"})).ok
    assert ok
    aid = next(iter(u.alliances))
    assert apply_action(u, "P2", Action(kind=ActionKind.ACCEPT_ALLIANCE, args={"alliance_id": aid})).ok
    u.players["P1"].ship.photon_missiles = 1
    out.append(("combat-allied-blocked", u))

    # --- group 2: StarDock
    u = _universe(); u.players["P1"].credits = 10_000_000
    out.append(("stardock-rich", u))
    u = _universe(); u.players["P1"].credits = 0
    out.append(("stardock-broke", u))
    u = _universe(); u.players["P1"].credits = 10_000_000; _move(u, "P1", 5)
    out.append(("fedspace-not-stardock-rich", u))

    # --- group 3: planets
    u = _universe(); pl = _a_planet(u); _move(u, "P1", pl.sector_id)
    pl.owner_id = None; pl.corp_ticker = None; pl.fighters = 0
    out.append(("planet-here-unowned-in-space", u))

    u = _universe(); pl = _a_planet(u); _move(u, "P1", pl.sector_id)
    pl.owner_id = "P1"; pl.corp_ticker = None
    pl.stockpile[Commodity.FUEL_ORE] = 40; pl.colonists[Commodity.ORGANICS] = 3000
    u.players["P1"].planet_landed = pl.id
    u.players["P1"].ship.cargo[Commodity.COLONISTS] = 5
    u.players["P1"].ship.cargo[Commodity.EQUIPMENT] = 4
    u.players["P1"].credits = 5_000_000
    out.append(("landed-own-planet-stocked", u))

    u = _universe(); pl = _a_planet(u); _move(u, "P1", pl.sector_id)
    pl.owner_id = "P1"; pl.corp_ticker = None
    pl.citadel_target = pl.citadel_level + 1; pl.citadel_complete_day = 99
    u.players["P1"].planet_landed = pl.id; u.players["P1"].credits = 5_000_000
    out.append(("landed-own-planet-citadel-building", u))

    u = _universe(); pl = _a_planet(u); _move(u, "P1", pl.sector_id)
    pl.owner_id = "P2"; pl.corp_ticker = None; pl.fighters = 0
    u.players["P1"].planet_landed = pl.id
    out.append(("landed-rival-planet", u))

    u = _universe(); pl = _a_planet(u); _move(u, "P1", pl.sector_id)
    pl.owner_id = None; pl.corp_ticker = None
    u.emit(EventKind.PLANET_ORPHANED, actor_id="P2", sector_id=pl.sector_id,
           payload={"planet_id": pl.id, "planet_name": pl.name, "former_owner": "P2"}, summary="orphaned")
    u.players["P1"].planet_landed = pl.id
    out.append(("landed-orphan", u))

    u = _universe(); deep = _deep_sector(u, 3); _move(u, "P1", deep); u.players["P1"].ship.genesis = 1
    out.append(("genesis-deep", u))
    u = _universe(); near = next(s for s in u.sectors[1].warps if s > 10) if any(s > 10 for s in u.sectors[1].warps) else None
    if near is not None:
        _move(u, "P1", near); u.players["P1"].ship.genesis = 1
        out.append(("genesis-one-hop", u))

    # --- group 4: corp / alliance
    u = _universe(); u.players["P1"].credits = 1_000_000
    assert apply_action(u, "P1", Action(kind=ActionKind.CORP_CREATE, args={"ticker": "ZZZ", "name": "Zed"})).ok
    assert apply_action(u, "P1", Action(kind=ActionKind.CORP_INVITE, args={"target": "P2"})).ok
    u.corporations["ZZZ"].treasury = 1000
    out.append(("corp-ceo-invited-p2", u))
    out.append(("corp-invited-p2-view", ("P2", copy.deepcopy(u))))  # corp_join legal here

    u2 = copy.deepcopy(u)
    assert apply_action(u2, "P2", Action(kind=ActionKind.CORP_JOIN, args={"ticker": "ZZZ"})).ok
    # Now evaluate from P2's seat (member, not CEO) by swapping ids: simplest is a second fixture set for P2.
    out.append(("corp-member-p2-view", ("P2", u2)))

    u = _universe()
    assert apply_action(u, "P2", Action(kind=ActionKind.PROPOSE_ALLIANCE, args={"target": "P1"})).ok
    out.append(("alliance-proposed-to-me", u))

    u = _universe(); u.players["P1"].turns_today = u.players["P1"].turns_per_day
    out.append(("out-of-turns", u))

    # --- group 5: ship-combat-core-v1 fighter challenge (P2's fighters hold the deep sector)
    for label, mode, credits, one_way in (
        ("challenge-defensive", "defensive", 25_000, False),
        ("challenge-toll-rich", "toll", 25_000, False),
        ("challenge-toll-broke", "toll", 0, False),
        ("challenge-one-way-in", "defensive", 25_000, True),
    ):
        u = _challenged(mode, credits, one_way)
        out.append((label, u))
    return out


def _challenged(mode: str, credits: int, one_way: bool):
    from tw2k.engine.models import FighterDeployment, FighterMode
    u = _universe(); deep = _deep_sector(u)
    back = next(n for n in sorted(u.sectors) if n > 10 and n != deep and deep in u.sectors[n].warps
                and n in u.sectors[deep].warps)
    if one_way:
        u.sectors[deep].warps = [w for w in u.sectors[deep].warps if w != back] or [1]
    u.sectors[back].warps = sorted(set(u.sectors[back].warps) | {deep})
    _move(u, "P1", back)
    u.sectors[deep].fighters = FighterDeployment(owner_id="P2", count=10, mode=FighterMode(mode))
    u.players["P1"].ship.fighters = 30; u.players["P1"].credits = credits
    res = apply_action(u, "P1", Action(kind=ActionKind.WARP, args={"target": deep}))
    assert res.ok and u.players["P1"].fighter_challenge, res.error
    return u


def _build(kind: str, la: LegalAction, u, pid: str) -> Action:
    p = la.params or {}
    ak = ActionKind(kind)
    player = u.players[pid]
    sector = u.sectors[player.sector_id]

    def first(name, fallback):
        ch = (p.get(name) or {}).get("choices") if isinstance(p.get(name), dict) else None
        return ch[0] if ch else fallback

    def qty_for(key, name="qty", cap=3):
        q = p.get(name) or {}
        mb = q.get("max_by") or {}
        if key in mb and mb[key] > 0:
            return min(cap, int(mb[key]))
        if q.get("max") is not None and int(q["max"]) > 0:
            return min(cap, int(q["max"]))
        return 1

    if ak is ActionKind.WARP:
        return Action(kind=ak, args={"target": first("target", (list(sector.warps) or [2])[0])})
    if ak in (ActionKind.SCAN, ActionKind.WAIT, ActionKind.LIFTOFF, ActionKind.QUERY_LIMPETS, ActionKind.DEPLOY_GENESIS,
             ActionKind.CLAIM_PLANET, ActionKind.CORP_LEAVE, ActionKind.DEPLOY_ATOMIC,
             ActionKind.CLOAK, ActionKind.REMOVE_LIMPET):
        return Action(kind=ak, args={})
    if ak is ActionKind.FIRE_DISRUPTOR:
        return Action(kind=ak, args={"target": first("target", (list(sector.warps) or [2])[0])})
    if ak is ActionKind.PROBE:
        return Action(kind=ak, args={"target": 2})
    if ak is ActionKind.PLOT_COURSE:
        return Action(kind=ak, args={"target": (list(sector.warps) or [2])[0], "execute": False})
    if ak is ActionKind.TRADE:
        comm = p.get("commodity") or {}
        for side, key in (("sell", "sell_choices"), ("buy", "buy_choices")):
            ch = comm.get(key) or []
            if ch:
                return Action(kind=ak, args={"commodity": ch[0], "qty": qty_for(ch[0]) if False else min(3, int(((p.get("qty") or {}).get("max_by") or {}).get(ch[0], {}).get(side, 1))), "side": side})
        return Action(kind=ak, args={"commodity": "fuel_ore", "qty": 1, "side": "buy"})
    if ak in (ActionKind.HAIL, ActionKind.CORP_INVITE, ActionKind.PROPOSE_ALLIANCE):
        return Action(kind=ak, args={"target": first("target", "P2"), "message": "hi", "terms": "peace"})
    if ak is ActionKind.BROADCAST or ak is ActionKind.CORP_MEMO or ak is ActionKind.LAUNCH_BEACON:
        return Action(kind=ak, args={"message": "hello"})
    if ak is ActionKind.ATTACK or ak is ActionKind.PHOTON_MISSILE:
        return Action(kind=ak, args={"target": first("target", "P2")})
    if ak is ActionKind.DEPLOY_FIGHTERS:
        return Action(kind=ak, args={"qty": qty_for("qty"), "mode": first("mode", "defensive")})
    if ak is ActionKind.DEPLOY_MINES:
        kind_ = first("kind", "armid")
        return Action(kind=ak, args={"kind": kind_, "qty": qty_for(kind_)})
    if ak is ActionKind.BUY_SHIP:
        return Action(kind=ak, args={"ship_class": first("ship_class", "scout_marauder")})
    if ak is ActionKind.BUY_EQUIP:
        item = first("item", "fighters")
        return Action(kind=ak, args={"item": item, "qty": qty_for(item)})
    if ak is ActionKind.CORP_CREATE:
        return Action(kind=ak, args={"ticker": "QQQ", "name": "Q Corp"})
    if ak is ActionKind.CORP_JOIN:
        return Action(kind=ak, args={"ticker": first("ticker", "ZZZ")})
    if ak in (ActionKind.CORP_DEPOSIT, ActionKind.CORP_WITHDRAW):
        mx = int((p.get("amount") or {}).get("max") or 0)
        return Action(kind=ak, args={"amount": min(100, mx) if mx > 0 else 1})
    if ak in (ActionKind.ACCEPT_ALLIANCE, ActionKind.BREAK_ALLIANCE):
        return Action(kind=ak, args={"alliance_id": first("alliance_id", "A1")})
    if ak is ActionKind.LAND_PLANET:
        ch = [c for c in ((p.get("planet_id") or {}).get("choices") or []) if c not in ((p.get("planet_id") or {}).get("contested") or [])]
        return Action(kind=ak, args={"planet_id": ch[0] if ch else (list(sector.planet_ids) or [1])[0]})
    if ak is ActionKind.LOAD_PLANET_CARGO or ak is ActionKind.DUMP_PLANET_CARGO:
        c = first("commodity", "fuel_ore")
        args = {"planet_id": first("planet_id", player.planet_landed or 1), "commodity": c, "qty": qty_for(c)}
        if c == "colonists":
            pools = ((p.get("pool") or {}).get("pools") or {})
            have = [k for k, v in pools.items() if v > 0]
            args["pool"] = have[0] if (have and ak is ActionKind.LOAD_PLANET_CARGO) else "organics"
        return Action(kind=ak, args=args)
    if ak is ActionKind.ASSIGN_COLONISTS:
        src = first("from", "ship")
        to_choices = ((p.get("to") or {}).get("choices") or ["fuel_ore"])
        dst = next((t for t in to_choices if t != src), "fuel_ore")
        return Action(kind=ak, args={"planet_id": first("planet_id", player.planet_landed or 1), "from": src, "to": dst, "qty": qty_for(src)})
    if ak is ActionKind.BUILD_CITADEL:
        return Action(kind=ak, args={"planet_id": first("planet_id", player.planet_landed or 1)})
    if ak in (ActionKind.DEPOSIT_PLANET_DEFENSE, ActionKind.WITHDRAW_PLANET_DEFENSE):
        kind_ = first("kind", "fighters")
        return Action(kind=ak, args={"planet_id": first("planet_id", player.planet_landed or 1), "kind": kind_, "qty": qty_for(kind_)})
    if ak is ActionKind.SET_MILITARY_REACTION:
        return Action(kind=ak, args={"planet_id": first("planet_id", player.planet_landed or 1), "pct": first("pct", 0)})
    if ak is ActionKind.PLANET_BUY_TRANSPORTER:
        return Action(kind=ak, args={"planet_id": first("planet_id", player.planet_landed or 1)})
    if ak is ActionKind.PLANET_TRANSPORT:
        return Action(kind=ak, args={"planet_id": first("planet_id", player.planet_landed or 1), "dest_sector": first("dest_sector", 1)})
    if ak is ActionKind.PLANET_DESTROY:
        return Action(kind=ak, args={"planet_id": first("planet_id", player.planet_landed or 1)})
    if ak is ActionKind.SHIP_TRANSWARP:  # ship-transwarp-v1
        return Action(kind=ak, args={"sector_id": first("sector_id", (list(sector.warps) or [2])[0])})
    if ak in (ActionKind.SELL_SHIP, ActionKind.SHIP_TRANSPORT):  # ship-fleet-transporter-v1
        return Action(kind=ak, args={"ship_id": first("ship_id", 1)})
    if ak is ActionKind.TOW_ENGAGE:  # ship-tow-transwarp2-v1
        return Action(kind=ak, args={"target": first("target", "ship:1")})
    if ak is ActionKind.TOW_RELEASE:
        return Action(kind=ak, args={})
    if ak is ActionKind.PLANET_TRADE:  # planetary-trading-v1
        pl_id = first("planet_id", 1)
        mb = ((p.get("qty") or {}).get("max_by") or {}).get(str(pl_id)) or {}
        c = next(iter(mb), first("commodity", "organics"))
        return Action(kind=ak, args={"planet_id": pl_id, "commodity": c, "qty": max(1, min(3, int(mb.get(c, 1))))})
    if ak is ActionKind.PLANET_TRANSWARP:
        return Action(kind=ak, args={"planet_id": first("planet_id", player.planet_landed or 1), "dest_sector": first("dest_sector", 1)})
    if ak is ActionKind.SET_QUASAR_SECTOR or ak is ActionKind.SET_QUASAR_ATM:
        return Action(kind=ak, args={"planet_id": first("planet_id", player.planet_landed or 1), "pct": first("pct", 0)})
    if ak in (ActionKind.DEPOSIT_TREASURY, ActionKind.WITHDRAW_TREASURY):
        return Action(kind=ak, args={"planet_id": first("planet_id", player.planet_landed or 1), "amount": qty_for("amount", "amount")})
    if ak is ActionKind.RECALL_DEPLOYED:
        what = first("what", "fighters")
        kind_ = first("kind", "armid")
        key = what if what == "fighters" else kind_
        return Action(kind=ak, args={"what": what, "qty": qty_for(key), "kind": kind_})
    if ak in (ActionKind.SURRENDER, ActionKind.RETREAT, ActionKind.PAY_TOLL):
        return Action(kind=ak, args={})
    if ak is ActionKind.ROB:  # rob-steal-v1
        mx = int((p.get("amount") or {}).get("max") or 1)
        return Action(kind=ak, args={"amount": max(1, min(100, mx))})
    if ak is ActionKind.STEAL:  # rob-steal-v1
        c = first("commodity", "fuel_ore")
        mb = (p.get("qty") or {}).get("max_by") or {}
        return Action(kind=ak, args={"commodity": c, "qty": max(1, min(3, int(mb.get(c, 1))))})
    if ak is ActionKind.TERRA_COLONISTS:
        mode = first("mode", "take")
        mb = ((p.get("qty") or {}).get("max_by") or {})
        qty = int(mb.get(mode) or 1)
        return Action(kind=ak, args={"mode": mode, "qty": max(1, qty)})
    if ak is ActionKind.APPLY_COMMISSION or ak is ActionKind.CLAIM_REWARD:
        return Action(kind=ak, args={})
    if ak is ActionKind.POST_REWARD:
        tid = first("target_id", "P2")
        mx = int((p.get("amount") or {}).get("max") or 1000)
        mn = int((p.get("amount") or {}).get("min") or 1000)
        return Action(kind=ak, args={"target_id": tid, "amount": max(mn, min(mn, mx))})
    if ak in (ActionKind.SHIP_SET_CORPORATE, ActionKind.SHIP_SET_PERSONAL):
        return Action(kind=ak, args={})
    if ak is ActionKind.SHIP_SET_PASSWORD:
        return Action(kind=ak, args={"password": first("password", "")})
    if ak is ActionKind.PORT_UPGRADE:
        commodities = p.get("commodities") or {}
        commodity = next((c for c, row in commodities.items() if int((row or {}).get("max_units") or 0) >= 1), "equipment")
        return Action(kind=ak, args={"commodity": commodity, "units": 1})
    if ak in (ActionKind.BANK_DEPOSIT, ActionKind.BANK_WITHDRAW):
        return Action(kind=ak, args={"amount": 1})
    if ak is ActionKind.BANK_TRANSFER:
        recipients = p.get("recipients") or []
        target = recipients[0]["player_id"] if recipients else "P2"
        return Action(kind=ak, args={"to_player": target, "amount": 1})
    if ak is ActionKind.PORT_BUILD:
        classes = p.get("classes") or {}
        code = next((c for c, row in classes.items() if (row or {}).get("affordable")), "SSS")
        planets = p.get("planets") or []
        planet_id = int(planets[0]["planet_id"]) if planets else 1
        return Action(kind=ak, args={"port_class": code, "planet_id": planet_id})
    raise AssertionError(f"no builder for {kind}")


@pytest.mark.parametrize("label,fx", _fixtures(), ids=lambda x: x if isinstance(x, str) else "")
def test_every_verb_matches_engine(label: str, fx) -> None:
    pid, u = fx if isinstance(fx, tuple) else ("P1", fx)
    las = {la.kind: la for la in legal_actions(u, pid)}
    assert set(las) == set(ALL)
    assert all(la.detail == "precise" for la in las.values()), [k for k, la in las.items() if la.detail != "precise"]
    for kind in ALL:
        la = las[kind]
        action = _build(kind, la, u, pid)
        u2 = copy.deepcopy(u)
        res = apply_action(u2, pid, action)
        assert res.ok == la.legal, f"{label}/{kind}: legal_actions={la.legal} ({la.reason}) engine={res.ok} ({res.error}) args={action.args}"
        if not la.legal:
            assert la.reason


def test_fedspace_combat_is_flagged_before_the_engine_penalises() -> None:
    u = _universe()
    las = {la.kind: la for la in legal_actions(u, "P1")}
    assert las["attack"].legal is False and "FedSpace" in (las["attack"].reason or "")
    assert las["photon_missile"].legal is False  # no missiles loaded here, still blocked


def test_bot_has_forms_for_all_groups() -> None:
    assert 'data-obs="legal_actions"' in HTML
    for kind in ("attack", "photon_missile", "deploy_fighters", "deploy_mines", "buy_ship", "buy_equip", "corp_create",
                 "land_planet", "liftoff", "load_planet_cargo", "dump_planet_cargo", "assign_colonists", "build_citadel",
                 "deposit_planet_defense", "withdraw_planet_defense", "set_military_reaction",
                 "deposit_treasury", "withdraw_treasury", "set_quasar_sector", "set_quasar_atm",
                 "planet_transwarp", "planet_buy_transporter", "planet_transport", "planet_destroy",
                 "deploy_genesis", "claim_planet", "hail", "broadcast", "corp_invite", "corp_join", "corp_leave",
                 "corp_deposit", "corp_withdraw", "corp_memo", "propose_alliance", "accept_alliance", "break_alliance",
                 "query_limpets"):
        assert f'"{kind}"' in JS, f"no form/handler for {kind}"
    for tid in ("verb-group-combat", "verb-group-stardock", "verb-group-planet", "verb-group-comms"):
        assert f'data-testid="{tid}"' in HTML, tid
    # Still no rule constants in JS.
    for forbidden in ("TURN_COST", "STARDOCK_SECTOR", "FEDSPACE", "SHIP_SPECS", "CITADEL_TIER_COST", "FIGHTER_COST"):
        assert forbidden not in JS, forbidden
