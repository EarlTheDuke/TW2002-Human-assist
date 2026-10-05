"""QC follow-ups for experience-alignment-v1."""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, Ship
from tw2k.engine.observation import build_observation


def _open(u, pid, sector, credits, *, alignment=0, experience=0, name="Seat"):
    p = Player(
        id=pid, name=name, ship=Ship(holds=20, fighters=20, shields=0),
        sector_id=sector, credits=credits, alignment=alignment, experience=experience,
    )
    u.players[pid] = p
    u.sectors[sector].occupant_ids.append(pid)
    p.known_sectors.add(sector)
    return p


def test_legacy_evil_ship_hints_match_empty_buy_ship_list(monkeypatch) -> None:
    """RANK_MODE legacy bars evil from every ordinary hull; hints must agree.

    Observation used ship_min_alignment(spec, -10**9), so an evil trader saw
    "Ships you can afford NOW" while buy_ship choices stayed empty.
    """
    monkeypatch.setattr(K, "RANK_MODE", "legacy")
    u = generate_universe(GameConfig(
        seed=11, universe_size=40, max_days=3, turns_per_day=20,
        starting_credits=100_000, enable_ferrengi=False, enable_planets=False,
    ))
    _open(u, "E", 1, 100_000, alignment=-100, experience=10, name="Evil")
    las = {(la.kind if isinstance(la.kind, str) else la.kind.value): la for la in legal_actions(u, "E")}
    assert las["buy_ship"].legal is False or not (las["buy_ship"].params.get("ship_class") or {}).get("choices")
    blocked = (las["buy_ship"].params.get("ship_class") or {}).get("blocked_by") or {}
    assert "needs None" not in " ".join(blocked.values())
    assert any("needs 0" in msg for msg in blocked.values())
    hint = build_observation(u, "E").action_hint or ""
    assert "Ships you can afford NOW" not in hint
    assert "BattleShip" not in hint and "CargoTran" not in hint


def test_tw2002_evil_may_buy_ordinary_hulls(monkeypatch) -> None:
    monkeypatch.setattr(K, "RANK_MODE", "tw2002")
    u = generate_universe(GameConfig(
        seed=11, universe_size=40, max_days=3, turns_per_day=20,
        starting_credits=100_000, enable_ferrengi=False, enable_planets=False,
    ))
    _open(u, "E", 1, 100_000, alignment=-100, experience=10, name="Evil")
    las = {(la.kind if isinstance(la.kind, str) else la.kind.value): la for la in legal_actions(u, "E")}
    choices = (las["buy_ship"].params.get("ship_class") or {}).get("choices") or []
    assert "cargotran" in choices
    hint = build_observation(u, "E").action_hint or ""
    assert "CargoTran" in hint or "cargotran" in hint.lower() or "Ships you can afford NOW" in hint
