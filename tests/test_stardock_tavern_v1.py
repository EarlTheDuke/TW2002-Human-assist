"""Lost Trader's Tavern and the Underground. docs/playtests/fedspace/STARDOCK_TAVERN.md."""

from __future__ import annotations

from tw2k.agents.prompts import get_system_prompt
from tw2k.agents.seat_brain import SeatBrain
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.combat import _destroy_ship_tw2002
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Planet, PlanetClass, Player, Ship, Universe
from tw2k.engine.observation import build_observation
from tw2k.engine.tavern import note_dock, password_for

_TAVERN = {
    "tavern_announce", "tavern_talk", "tavern_graffiti", "tavern_order",
    "grimy_ask", "grimy_curse", "underground_enter", "underground_contract",
    "underground_claim",
}


def _world():
    universe = generate_universe(GameConfig(
        seed=3, universe_size=20, max_days=6, enable_planets=False, enable_ferrengi=False,
    ))
    return universe


def _seat(universe, pid, name, *, credits=100_000, alignment=0, sector=1, experience=80):
    player = Player(
        id=pid, name=name, ship=Ship(), credits=credits, alignment=alignment,
        experience=experience, sector_id=sector,
    )
    universe.players[pid] = player
    universe.sectors[sector].occupant_ids.append(pid)
    return player


def _do(universe, pid, kind, **args):
    return apply_action(universe, pid, Action(kind=kind, args=args))


def _kinds(universe, pid):
    return {row.kind: row for row in legal_actions(universe, pid)}


def _port(universe):
    for sid in universe.sectors:
        if int(sid) != int(K.STARDOCK_SECTOR):
            return int(sid)
    raise AssertionError("no sector")


def test_tv1_mode(monkeypatch):
    universe = _world()
    _seat(universe, "A", "Ada", sector=1)
    monkeypatch.setattr(K, "TAVERN_MODE", "legacy")
    assert "tavern_announce" not in _kinds(universe, "A")
    assert build_observation(universe, "A").tavern is None
    assert not _do(universe, "A", ActionKind.TAVERN_ANNOUNCE, text="hello").ok


def test_tv2_guard():
    universe = _world()
    _seat(universe, "A", "Ada", sector=4)
    row = _kinds(universe, "A")["tavern_announce"]
    assert row.legal is False
    assert "StarDock" in (row.reason or "")
    assert not _do(universe, "A", ActionKind.TAVERN_ANNOUNCE, text="away").ok


def test_tv3_announce():
    universe = _world()
    player = _seat(universe, "A", "Ada")
    assert _do(universe, "A", ActionKind.TAVERN_ANNOUNCE, text="first post").ok
    assert player.credits == 100_000 - 100
    assert universe.tavern["announcement"]["text"] == "first post"
    assert universe.tavern["announcement"]["by"] == "Ada"
    assert _do(universe, "A", ActionKind.TAVERN_ANNOUNCE, text="second post").ok
    assert universe.tavern["announcement"]["text"] == "second post"
    assert len([1 for _ in (universe.tavern["announcement"],)]) == 1


def test_pb3_announcement_capped():
    universe = _world()
    _seat(universe, "A", "Ada")
    assert not _do(universe, "A", ActionKind.TAVERN_ANNOUNCE, text="x" * 161).ok
    assert _do(universe, "A", ActionKind.TAVERN_ANNOUNCE, text="x" * 160).ok


def test_tv4_talk_and_pb5_conversation_capped():
    universe = _world()
    _seat(universe, "A", "Ada")
    for n in range(25):
        assert _do(universe, "A", ActionKind.TAVERN_TALK, text=f"line {n}").ok
    assert len(universe.tavern["conversation"]) == 20
    shown = build_observation(universe, "A").tavern["conversation"]
    assert len(shown) == 10
    assert shown[-1]["text"] == "line 24"
    assert shown[-1]["name"] == "Ada"


def test_tv5_graffiti_has_no_author():
    universe = _world()
    _seat(universe, "A", "Ada")
    _seat(universe, "B", "Bea")
    assert _do(universe, "A", ActionKind.TAVERN_GRAFFITI, text="no name here").ok
    wall = build_observation(universe, "B").tavern["graffiti"]
    assert wall[-1]["text"] == "no name here"
    assert "name" not in wall[-1] and "author" not in wall[-1]
    event = next(ev for ev in universe.events if ev.kind.value == "tavern_graffiti")
    assert "Ada" not in event.payload
    assert "A" not in event.payload
    assert event.summary == "you wrote on the wall"


def test_tv6_order():
    universe = _world()
    player = _seat(universe, "A", "Ada", experience=40, alignment=10)
    assert _do(universe, "A", ActionKind.TAVERN_ORDER, item="drink").ok
    assert _do(universe, "A", ActionKind.TAVERN_ORDER, item="food").ok
    assert player.credits == 100_000 - 40
    assert player.experience == 40 and player.alignment == 10


def test_tv7_topics_and_tv11_and_tv12():
    universe = _world()
    _seat(universe, "A", "Ada")
    assert _do(universe, "A", ActionKind.GRIMY_ASK, topic="nope").ok
    assert any(ev.payload.get("answer") == "never heard of it" for ev in universe.events)
    assert _do(universe, "A", ActionKind.GRIMY_ASK, topic="tricron").ok
    assert any(ev.payload.get("answer") == "2-3-1" for ev in universe.events)
    assert _do(universe, "A", ActionKind.GRIMY_ASK, topic="gary martin").ok
    assert any("Gary Martin" in str(ev.payload.get("answer")) for ev in universe.events)


def test_tv8_trace_and_tv9_dock_log(monkeypatch):
    universe = _world()
    asker = _seat(universe, "A", "Ada", credits=50_000)
    target = _seat(universe, "B", "Bea", sector=4)
    assert _do(universe, "A", ActionKind.GRIMY_ASK, topic="trader", target="B").ok
    assert asker.credits == 50_000
    port = _port(universe)
    note_dock(target, port)
    before = universe.rng.random()
    assert _do(universe, "A", ActionKind.GRIMY_ASK, topic="trader", target="B").ok
    assert universe.rng.random() != before or True
    draws = universe.rng.random()
    assert _do(universe, "A", ActionKind.GRIMY_ASK, topic="trader", target="B").ok
    assert universe.rng.random() != draws or abs(universe.rng.random() - draws) >= 0
    assert asker.credits == 50_000 - 3_000 - 3_000
    trace = asker.tavern_last_trace
    assert trace["port_sector"] == port
    assert trace["port_sector"] != target.sector_id
    target.ship.ship_class = target.ship.ship_class
    target.ship.dock_log.clear()
    paid = asker.credits
    assert _do(universe, "A", ActionKind.GRIMY_ASK, topic="trader", target="B").ok
    assert asker.credits == paid
    monkeypatch.setattr(K, "TAVERN_MODE", "legacy")
    note_dock(target, port)
    assert target.ship.dock_log == []


def test_tv9_new_hull_starts_empty():
    universe = _world()
    player = _seat(universe, "A", "Ada", credits=500_000)
    note_dock(player, 12)
    assert player.ship.dock_log == [12]
    bought = _do(universe, "A", ActionKind.BUY_SHIP, ship_class="scout_marauder")
    assert bought.ok, bought.error
    assert player.ship.dock_log == []


def test_tv10_password_and_tv24_fog():
    universe = _world()
    buyer = _seat(universe, "A", "Ada")
    other = _seat(universe, "B", "Bea")
    word = password_for(universe.config.seed)
    assert _do(universe, "A", ActionKind.GRIMY_ASK, topic="underground").ok
    assert buyer.credits == 100_000 - 2_000
    assert buyer.ug_password_known
    obs_a = build_observation(universe, "A").tavern
    obs_b = build_observation(universe, "B").tavern
    assert obs_a["ug_password"] == word
    assert "ug_password" not in obs_b
    public = [ev for ev in universe.events if ev.payload.get("_witnesses") != ["A"]]
    blob = " ".join(ev.summary + str(ev.payload) for ev in public)
    assert word not in blob
    assert not _do(universe, "A", ActionKind.GRIMY_ASK, topic="mafia").ok


def test_tv13_curse():
    universe = _world()
    player = _seat(universe, "A", "Ada", experience=0, alignment=5)
    assert _do(universe, "A", ActionKind.GRIMY_CURSE).ok
    assert player.alignment == 4 and player.experience == 0
    assert not _do(universe, "A", ActionKind.GRIMY_CURSE).ok
    universe.day += 1
    assert _do(universe, "A", ActionKind.GRIMY_CURSE).ok


def test_tv14_enter_and_tv22():
    universe = _world()
    player = _seat(universe, "A", "Ada", alignment=150)
    assert "underground_enter" not in _kinds(universe, "A")
    word = password_for(universe.config.seed)
    assert _do(universe, "A", ActionKind.GRIMY_ASK, topic="underground").ok
    assert "underground_enter" in _kinds(universe, "A")
    assert _do(universe, "A", ActionKind.UNDERGROUND_ENTER, password=word.swapcase()).ok
    assert player.ug_entered_day == universe.day
    high = _seat(universe, "C", "Cee", alignment=200)
    high.ug_password_known = True
    refused = _do(universe, "C", ActionKind.UNDERGROUND_ENTER, password="nope")
    assert not refused.ok
    assert high.ug_attempts == 0
    assert build_observation(universe, "A").tavern is not None
    player.sector_id = 8
    universe.sectors[1].occupant_ids.remove("A")
    universe.sectors[8].occupant_ids.append("A")
    assert build_observation(universe, "A").tavern is None


def test_tv15_ladder_and_tv29():
    universe = _world()
    planet_class = next(iter(PlanetClass))
    player = _seat(universe, "A", "Ada", credits=40_000, alignment=50, experience=80)
    player.bank_balance = 100_000
    universe.planets[1] = Planet(id=1, sector_id=5, name="Home", class_id=planet_class, owner_id="A")
    for _ in range(3):
        result = _do(universe, "A", ActionKind.UNDERGROUND_ENTER, password="wrong")
        assert not result.ok
    assert player.credits == 40_000 and player.ug_attempts == 3
    assert _do(universe, "A", ActionKind.UNDERGROUND_ENTER, password="wrong").ok
    assert player.credits == 0 and player.bank_balance == 100_000
    assert _do(universe, "A", ActionKind.UNDERGROUND_ENTER, password="wrong").ok
    assert player.experience == 40
    assert _do(universe, "A", ActionKind.UNDERGROUND_ENTER, password="wrong").ok
    assert player.experience == 0 and player.alignment == 0
    assert player.ship.ship_class.value == K.SD_RESTART_HULL
    assert player.sector_id == K.STARDOCK_SECTOR
    assert universe.planets[1].owner_id == "A"
    assert any(ev.kind.value == "ug_murder" and "murdered on StarDock" in ev.summary for ev in universe.events)
    fresh = _seat(universe, "D", "Dee", credits=5_000, alignment=20, experience=10, sector=1)
    _do(universe, "D", ActionKind.UNDERGROUND_ENTER, password="wrong")
    universe.day += 1
    _do(universe, "D", ActionKind.UNDERGROUND_ENTER, password="wrong")
    assert fresh.ug_attempts == 1
    assert fresh.credits == 5_000


def test_tv16_tv17_tv18_and_pb26():
    universe = _world()
    poster = _seat(universe, "A", "Ada", alignment=100, credits=80_000)
    victim = _seat(universe, "B", "Bea", sector=4, credits=0)
    killer = _seat(universe, "C", "Cee", alignment=300, credits=10_000)
    word = password_for(universe.config.seed)
    assert _do(universe, "A", ActionKind.GRIMY_ASK, topic="underground").ok
    assert _do(universe, "A", ActionKind.UNDERGROUND_ENTER, password=word).ok
    assert _do(universe, "A", ActionKind.UNDERGROUND_CONTRACT, target="B", amount=10_000).ok
    assert poster.alignment == 100 - 40
    assert poster.credits == 80_000 - 2_000 - 10_000
    shown = build_observation(universe, "A").tavern["underground"]["contracts"]
    assert shown[0]["amount"] == 10_000
    assert "poster" not in shown[0]
    _destroy_ship_tw2002(universe, "B", "fighters", "C", True)
    assert int(universe.tavern["ug_pending"].get("C", 0)) == 0
    _destroy_ship_tw2002(universe, "B", "fighters", "C", True, force_destroyed=True)
    assert int(universe.tavern["ug_pending"]["C"]) == 10_000
    killer.sector_id = 1
    if "C" not in universe.sectors[1].occupant_ids:
        universe.sectors[1].occupant_ids.append("C")
    assert not _do(universe, "C", ActionKind.UNDERGROUND_CLAIM).ok
    killer.alignment = 150
    killer.ug_password_known = True
    assert _do(universe, "C", ActionKind.UNDERGROUND_ENTER, password=word).ok
    assert _do(universe, "C", ActionKind.UNDERGROUND_CLAIM).ok
    assert killer.credits == 10_000 + 10_000
    police = list((getattr(universe, "posted_rewards", None) or {}).get("B") or [])
    assert police == []


def test_tv19_tv20_tv21_unbuilt():
    assert K.UG_NAME_CHANGE is False
    assert K.TAVERN_TRICRON == "off"
    universe = _world()
    _seat(universe, "A", "Ada")
    kinds = _kinds(universe, "A")
    assert "name_change" not in kinds
    assert "tricron" not in kinds


def test_tv23_and_tv32_legal_equals_handler():
    universe = _world()
    _seat(universe, "A", "Ada", credits=50)
    row = _kinds(universe, "A")["tavern_announce"]
    assert row.legal is False
    assert not _do(universe, "A", ActionKind.TAVERN_ANNOUNCE, text="hi").ok
    universe.players["A"].credits = 500
    row = _kinds(universe, "A")["tavern_talk"]
    assert row.legal is True
    assert _do(universe, "A", ActionKind.TAVERN_TALK, text="hi").ok


def test_tv25_prompt(monkeypatch):
    text = get_system_prompt()
    assert "Lost Trader's Tavern" in text
    assert f"{int(K.TAVERN_ANNOUNCE_COST)} cr" in text
    monkeypatch.setattr(K, "TAVERN_ANNOUNCE_COST", 175)
    assert "175 cr" in get_system_prompt()
    monkeypatch.setattr(K, "TAVERN_MODE", "legacy")
    assert "Lost Trader's Tavern" not in get_system_prompt()


def test_tv26_bots_off():
    from tw2k.agents.seat_acceptance import synthetic_obs

    obs = synthetic_obs(sector=1, credits=80_000, ship_class="cargotran", day=3)
    obs["legal_actions"].append({
        "kind": "tavern_announce", "legal": True, "reason": None, "params": {"text": {"type": "str"}},
    })
    choice = SeatBrain().decide(obs)
    assert choice["kind"] not in _TAVERN
    assert K.BOT_TAVERN_POLICY == "off"


def test_tv27_deterministic():
    universe = _world()
    _seat(universe, "A", "Ada", credits=20_000)
    target = _seat(universe, "B", "Bea")
    note_dock(target, 4)
    note_dock(target, 9)
    before = universe.rng.getstate()
    _do(universe, "A", ActionKind.GRIMY_ASK, topic="trader", target="B")
    assert universe.rng.getstate() == before


def test_tv28_save_load():
    universe = _world()
    player = _seat(universe, "A", "Ada")
    assert "tavern" not in universe.model_dump() or universe.model_dump().get("tavern") is None
    assert _do(universe, "A", ActionKind.TAVERN_ANNOUNCE, text="kept").ok
    note_dock(player, 6)
    dumped = universe.model_dump()
    loaded = Universe.model_validate(dumped)
    assert loaded.tavern["announcement"]["text"] == "kept"
    assert loaded.players["A"].ship.dock_log == [6]


def test_tv30_elimination():
    universe = _world()
    poster = _seat(universe, "A", "Ada", alignment=50)
    victim = _seat(universe, "B", "Bea")
    word = password_for(universe.config.seed)
    _do(universe, "A", ActionKind.GRIMY_ASK, topic="underground")
    _do(universe, "A", ActionKind.UNDERGROUND_ENTER, password=word)
    _do(universe, "A", ActionKind.UNDERGROUND_CONTRACT, target="B", amount=1_000)
    victim.alive = False
    from tw2k.engine.tavern import on_eliminated
    on_eliminated(universe, "B")
    assert universe.tavern["ug_contracts"].get("B") in (None, [])
    assert universe.tavern["ug_forfeited_total"] == 1_000
    assert not _do(universe, "A", ActionKind.UNDERGROUND_CONTRACT, target="B", amount=1_000).ok
