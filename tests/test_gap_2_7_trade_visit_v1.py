"""GAP 2.7. A visit costs 1 turn, then 0. The stale map said 3 per trade.

Off (`TRADE_TURN_MODE` legacy, the stored game) and on (`live`, and the v311
profile) charge the same pair. The October 3 cell that said 3 is not a second
number. The visit is `port_visit_sector_id` until the player leaves the sector.
docs/playtests/ports/TURNS_REGEN.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.economy import begin_port_visit, trade_turn_cost
from tw2k.engine.models import Commodity, Player, Port, PortClass, PortStock, Ship

pytestmark = pytest.mark.legacy_profile

ROOT = Path(__file__).resolve().parents[1]
# The October 3 map cell. Not a cost this engine charges.
STALE_PER_TRADE = 3
FUEL = Commodity.FUEL_ORE


def _player() -> Player:
    return Player(id="P1", name="Tiny Box", agent_kind="llm", sector_id=5)


def _costs(player: Player) -> tuple[int, int, int]:
    first = trade_turn_cost(player)
    begin_port_visit(player)
    later = trade_turn_cost(player)
    player.end_port_visit()
    after = trade_turn_cost(player)
    return first, later, after


def test_off_is_one_then_zero_not_three() -> None:
    """Stored games. Legacy names the visit rule. It does not charge 3."""
    assert K.TRADE_TURN_MODE == "legacy"
    assert K.V311_PROFILE == "legacy"
    assert K.trade_turn_live() is False
    assert K.TURN_COST["trade"] == K.PORT_DOCK_TURN_COST == 1
    assert K.TURN_COST["trade"] != STALE_PER_TRADE
    player = _player()
    assert _costs(player) == (1, 0, 1)
    assert player.port_visit_sector_id is None


def test_on_names_the_same_one_then_zero(monkeypatch) -> None:
    """`TRADE_TURN_MODE` live is the same 1 then 0, not a new number."""
    monkeypatch.setattr(K, "TRADE_TURN_MODE", "live")
    assert K.trade_turn_live() is True
    assert _costs(_player()) == (1, 0, 1)
    assert trade_turn_cost(_player()) != STALE_PER_TRADE


def _seat():
    universe = generate_universe(
        GameConfig(seed=8, universe_size=20, max_days=5, enable_planets=False, enable_ferrengi=False)
    )
    player = Player(id="P1", name="Trader", ship=Ship(), credits=500_000, experience=0)
    player.sector_id = 11
    player.ship.cargo[FUEL] = 30
    universe.players["P1"] = player
    universe.sectors[11].occupant_ids.append("P1")
    universe.sectors[11].port = Port(
        class_id=PortClass.CLASS_1_BSS,
        stock={FUEL: PortStock(current=0, maximum=3000)},
        mcic={FUEL: -60},
        productivity={FUEL: 100},
    )
    return universe, player


def _sell(universe):
    return apply_action(
        universe,
        "P1",
        Action(kind=ActionKind.TRADE, args={"side": "sell", "commodity": "fuel_ore", "qty": 1}),
    )


def test_a_real_visit_spends_one_then_zero_off_and_on(monkeypatch) -> None:
    """Two sells in one sector, then a warp. Off and on. Neither sell costs 3."""
    for mode in ("legacy", "live"):
        monkeypatch.setattr(K, "TRADE_TURN_MODE", mode)
        universe, player = _seat()
        first = _sell(universe)
        assert first.ok, first.error
        assert first.turns_spent == 1
        assert first.turns_spent != STALE_PER_TRADE
        assert player.port_visit_sector_id == 11
        second = _sell(universe)
        assert second.ok, second.error
        assert second.turns_spent == 0
        assert player.turns_today == 1
        dest = universe.sectors[11].warps[0]
        left = apply_action(universe, "P1", Action(kind=ActionKind.WARP, args={"target": dest}))
        assert left.ok, left.error
        assert player.port_visit_sector_id is None


def test_gap_row_is_match_and_cites_the_visit() -> None:
    bible = (ROOT / "docs" / "reference" / "tw2002" / "stardock_manuals_and_text_docs" / "TWBible_original_v1x.txt").read_text(
        encoding="utf-8", errors="replace"
    )
    assert "One turn deducted" in bible
    cashing = (ROOT / "docs" / "reference" / "tw2002" / "classictw_docs_wiki" / "Evil_or_Red_Cashing.html").read_text(
        encoding="utf-8", errors="replace"
    )
    assert "One turn deducted" in cashing
    assert "trades at that port then cost no extra turns" not in bible
    assert "trades at that port then cost no extra turns" not in cashing
