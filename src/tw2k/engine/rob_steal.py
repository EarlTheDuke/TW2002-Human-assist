"""Rob and steal at ports (ROB_MODE tw2002). docs/playtests/ports/ROB_STEAL.md."""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import constants as K
from .actions import Action, ActionResult
from .economy import begin_port_visit, trade_turn_cost
from .models import TRADE_COMMODITIES, Commodity, EventKind, PortClass

if TYPE_CHECKING:
    from .models import Player, Port, Universe


def rob_tw2002() -> bool:
    return K.rob_tw2002()


def port_allows_crime(port: Port | None) -> tuple[bool, str]:
    if port is None:
        return False, "no trading port in this sector"
    if port.class_id == PortClass.STARDOCK:
        return False, "StarDock cannot be robbed or stolen from"
    if port.class_id == PortClass.FEDERAL:
        return False, "Class 0 / Federal ports cannot be robbed or stolen from"
    if K.port_upgrade_on():  # pu23
        from .port_build import docks_closed
        if docks_closed(port):
            return False, "this port is under construction"
    return True, ""


def alignment_allows_crime(player: Player) -> bool:
    return int(player.alignment) <= int(K.ROB_MIN_ALIGNMENT)


def max_rob_credits(experience: int) -> int:
    return max(0, int(experience) * int(K.ROB_CREDIT_FACTOR))


def max_steal_holds(experience: int) -> int:
    div = int(K.STEAL_HOLD_DIVISOR)
    if div <= 0:
        return 0
    return max(0, int(experience) // div)


def bust_blocks_player(port: Port, pid: str) -> bool:
    return bool(port.bust_player_id) and port.bust_player_id == pid


def clear_all_busts(universe: Universe) -> None:
    for sector in universe.sectors.values():
        if sector.port is not None:
            sector.port.bust_player_id = None


def _truncate_cargo_to_holds(player: Player) -> None:
    ship = player.ship
    cap = max(1, int(ship.holds))
    used = int(ship.cargo_used)
    if used <= cap:
        return
    need = used - cap
    for c in sorted(ship.cargo.keys(), key=lambda x: x.value):
        if need <= 0:
            break
        have = int(ship.cargo.get(c, 0))
        if have <= 0:
            continue
        drop = min(have, need)
        ship.cargo[c] = have - drop
        if ship.cargo[c] <= 0:
            ship.cargo[c] = 0
            ship.cargo_cost[c] = 0.0
        need -= drop


def _apply_holds_loss(player: Player, holds_lost: int) -> int:
    if holds_lost <= 0:
        return 0
    before = int(player.ship.holds)
    after = max(1, before - holds_lost)
    lost = before - after
    player.ship.holds = after
    _truncate_cargo_to_holds(player)
    return lost


def _apply_bust_exp(player: Player) -> int:
    before = int(player.experience)
    lost = before // 10
    player.experience = before - lost
    return lost


def _roll_bust(universe: Universe, *, forced: bool, over_cap: bool) -> tuple[bool, str]:
    if forced:
        return True, "fake"
    if over_cap:
        return True, "over_cap"
    denom = max(1, int(K.ROB_BUST_DENOMINATOR))
    if universe.rng.randrange(denom) == 0:
        return True, "chance"
    return False, ""


def seed_port_credits(port: Port) -> int:
    """Heuristic vault from port capacity (ROB_STEAL.md r6 UNVERIFIED).

    Trading ports often start empty under the economy calibration, so the vault
    uses maximum stock (capacity) rather than current units on the shelf.
    """
    total = 0
    for c, st in port.stock.items():
        base = int(K.COMMODITY_BASE_PRICE[c.value])
        total += max(int(st.maximum), int(st.current)) * base
    # About a quarter of full-shelf list value — enough for early red play.
    return max(0, total // 4)


def handle_rob(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not rob_tw2002():
        return ActionResult(ok=False, error="rob is not available (ROB_MODE legacy)")
    player = universe.players[pid]
    sector = universe.sectors[player.sector_id]
    ok_port, why = port_allows_crime(sector.port)
    if not ok_port:
        return ActionResult(ok=False, error=why)
    port = sector.port
    assert port is not None
    if getattr(port, "construction", None):
        return ActionResult(ok=False, error="that port is under construction")
    if not alignment_allows_crime(player):
        return ActionResult(ok=False, error=f"alignment must be {K.ROB_MIN_ALIGNMENT} or lower to rob")
    if bust_blocks_player(port, pid):
        return ActionResult(ok=False, error="you are busted at this port until it clears")
    try:
        amount = int(action.args.get("amount", 0))
    except (TypeError, ValueError):
        return ActionResult(ok=False, error="amount must be an integer")
    if amount <= 0:
        return ActionResult(ok=False, error="amount must be positive")
    cost = trade_turn_cost(player)
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns for this day")

    cap = max_rob_credits(int(player.experience))
    vault = max(0, int(port.credits))
    over_cap = amount > cap
    forced = player.last_crime_sector_id is not None and int(player.last_crime_sector_id) == int(sector.id)
    busted, bust_kind = _roll_bust(universe, forced=forced, over_cap=over_cap)

    begin_port_visit(player)
    if busted:
        exp_lost = _apply_bust_exp(player)
        holds_lost = _apply_holds_loss(player, max(0, amount // 100))
        if bust_kind != "fake":
            port.bust_player_id = pid
        universe.emit(
            EventKind.BUST,
            actor_id=pid,
            sector_id=sector.id,
            payload={
                "kind": "rob",
                "bust_kind": bust_kind,
                "amount": amount,
                "exp_lost": exp_lost,
                "holds_lost": holds_lost,
            },
            summary=f"{player.name} busted robbing {amount} cr at sector {sector.id}",
        )
        return ActionResult(ok=True, turns_spent=cost)

    # success path never over_cap (over_cap always busts)
    take = min(amount, vault)
    if take <= 0:
        return ActionResult(ok=False, error="port has no credits to rob", turns_spent=cost)

    port.credits = vault - take
    player.credits = int(player.credits) + take
    player.last_crime_sector_id = sector.id
    # r22 UNVERIFIED success awards
    align_hit = max(1, take // int(K.ROB_SUCCESS_ALIGN_DIVISOR))
    exp_gain = max(1, take // int(K.ROB_SUCCESS_EXP_DIVISOR))
    player.alignment = int(player.alignment) - align_hit
    player.experience = int(player.experience) + exp_gain
    universe.emit(
        EventKind.ROB,
        actor_id=pid,
        sector_id=sector.id,
        payload={"amount": take, "align": -align_hit, "exp": exp_gain},
        summary=f"{player.name} robbed {take} cr from the port in sector {sector.id}",
    )
    return ActionResult(ok=True, turns_spent=cost)


def handle_steal(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not rob_tw2002():
        return ActionResult(ok=False, error="steal is not available (ROB_MODE legacy)")
    player = universe.players[pid]
    sector = universe.sectors[player.sector_id]
    ok_port, why = port_allows_crime(sector.port)
    if not ok_port:
        return ActionResult(ok=False, error=why)
    port = sector.port
    assert port is not None
    if getattr(port, "construction", None):
        return ActionResult(ok=False, error="that port is under construction")
    if not alignment_allows_crime(player):
        return ActionResult(ok=False, error=f"alignment must be {K.ROB_MIN_ALIGNMENT} or lower to steal")
    if bust_blocks_player(port, pid):
        return ActionResult(ok=False, error="you are busted at this port until it clears")
    raw = action.args.get("commodity")
    try:
        commodity = Commodity(raw)
    except (TypeError, ValueError):
        return ActionResult(ok=False, error=f"invalid commodity {raw!r}")
    if commodity not in TRADE_COMMODITIES:
        return ActionResult(ok=False, error="cannot steal that commodity")
    try:
        qty = int(action.args.get("qty", 0))
    except (TypeError, ValueError):
        return ActionResult(ok=False, error="qty must be an integer")
    if qty <= 0:
        return ActionResult(ok=False, error="qty must be positive")
    st = port.stock.get(commodity)
    if st is None or int(st.current) <= 0:
        return ActionResult(ok=False, error=f"port has no {commodity.value} to steal")
    cost = trade_turn_cost(player)
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns for this day")

    cap = max_steal_holds(int(player.experience))
    free = int(player.ship.cargo_free)
    over_cap = qty > cap
    forced = player.last_crime_sector_id is not None and int(player.last_crime_sector_id) == int(sector.id)
    busted, bust_kind = _roll_bust(universe, forced=forced, over_cap=over_cap)

    begin_port_visit(player)
    if busted:
        exp_lost = _apply_bust_exp(player)
        holds_lost = _apply_holds_loss(player, max(0, (qty * 9) // 100))
        if bust_kind != "fake":
            port.bust_player_id = pid
        universe.emit(
            EventKind.BUST,
            actor_id=pid,
            sector_id=sector.id,
            payload={
                "kind": "steal",
                "bust_kind": bust_kind,
                "commodity": commodity.value,
                "qty": qty,
                "exp_lost": exp_lost,
                "holds_lost": holds_lost,
            },
            summary=f"{player.name} busted stealing {qty} {commodity.value} at sector {sector.id}",
        )
        return ActionResult(ok=True, turns_spent=cost)

    take = min(qty, int(st.current), free)
    if take <= 0:
        return ActionResult(ok=False, error="no free holds or port stock", turns_spent=cost)

    st.current = int(st.current) - take
    old_qty = int(player.ship.cargo.get(commodity, 0))
    new_qty = old_qty + take
    player.ship.cargo[commodity] = new_qty
    # Stolen goods are free loot: dilute any existing cost basis (do not keep
    # the paid average across the stolen units — that understates sale profit).
    old_basis = float(player.ship.cargo_cost.get(commodity, 0.0) or 0.0)
    player.ship.cargo_cost[commodity] = (old_basis * old_qty) / new_qty if new_qty else 0.0
    player.last_crime_sector_id = sector.id
    align_hit = max(1, take // int(K.STEAL_SUCCESS_ALIGN_DIVISOR))
    exp_gain = max(1, take // int(K.STEAL_SUCCESS_EXP_DIVISOR))
    player.alignment = int(player.alignment) - align_hit
    player.experience = int(player.experience) + exp_gain
    universe.emit(
        EventKind.STEAL,
        actor_id=pid,
        sector_id=sector.id,
        payload={
            "commodity": commodity.value,
            "qty": take,
            "align": -align_hit,
            "exp": exp_gain,
        },
        summary=f"{player.name} stole {take} {commodity.value} from the port in sector {sector.id}",
    )
    return ActionResult(ok=True, turns_spent=cost)
