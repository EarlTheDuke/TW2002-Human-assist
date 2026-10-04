#!/usr/bin/env python3
"""Read-only money-scale report. Prints tables. Changes no file and no constant.

Fresh stock is 100 percent, the assumption on the economy2 charts.
Typical is experience 0, MCIC 50 where the port sells, MCIC -50 where it buys.
Best is experience 1000, MCIC 1 where the port sells, MCIC -100 where it buys.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from tw2k.engine import constants as K  # noqa: E402
from tw2k.engine.economy import port_buy_price, port_sell_price  # noqa: E402
from tw2k.engine.models import Commodity, GameConfig, Port, PortClass, PortStock  # noqa: E402
from tw2k.engine.universe import generate_universe  # noqa: E402

FUEL, ORG, EQUIP = Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT
GOODS = (FUEL, ORG, EQUIP)
NAMES = {FUEL: "fuel_ore", ORG: "organics", EQUIP: "equipment"}

# economy2.html, 100 percent charts, zero experience, no haggle, 250 holds.
# The experience table on the same page says 11,760 and 32,405 at MCIC 50 / -50
# for equipment. That conflict is written in ECONOMY_SCALE.md.
ORIGINAL_250 = {
    FUEL: {"sell": 3_675, "buy": 8_791},
    ORG: {"sell": 6_964, "buy": 17_712},
    EQUIP: {"sell": 12_190, "buy": 31_910},
}

# Bible_TWGS_edit_2007_Clme.htm, "Ship Cost / Cost to Max Holds".
BIBLE = {
    "merchant_cruiser": (41_300, 61_215),
    "scout_marauder": (15_950, 7_695),
    "missile_frigate": (100_800, 42_384),
    "battleship": (88_500, 71_872),
    "corporate_flagship": (163_500, 78_845),
    "colonial_transport": (63_600, 632_000),
    "cargotran": (51_950, 143_475),
    "merchant_freighter": (33_400, 38_955),
    "havoc_gunstar": (79_000, 29_754),
    "imperial_starship": (339_000, 226_930),
}

DENSITY_SEEDS = range(250925, 250945)


def _port(class_id: int, *, sell_mcic: int, buy_mcic: int) -> Port:
    trades = K.PORT_CLASS_TRADES[class_id]
    stock: dict[Commodity, PortStock] = {}
    mcic: dict[Commodity, int] = {}
    for commodity, deal in zip(GOODS, trades, strict=True):
        if deal is None:
            continue
        stock[commodity] = PortStock(current=3000, maximum=3000)
        mcic[commodity] = sell_mcic if deal is False else buy_mcic
    return Port(class_id=PortClass(class_id), stock=stock, mcic=mcic)


def _spread(seller: Port, buyer: Port, commodity: Commodity, experience: int) -> int:
    """Credits one hold earns buying from seller and selling to buyer."""
    return port_buy_price(buyer, commodity, experience) - port_sell_price(seller, commodity, experience)


def _round_trip(class_a: int, class_b: int, *, sell_mcic: int, buy_mcic: int, experience: int) -> int | None:
    port_a = _port(class_a, sell_mcic=sell_mcic, buy_mcic=buy_mcic)
    port_b = _port(class_b, sell_mcic=sell_mcic, buy_mcic=buy_mcic)
    trades_a = K.PORT_CLASS_TRADES[class_a]
    trades_b = K.PORT_CLASS_TRADES[class_b]
    forward = []
    back = []
    for commodity, deal_a, deal_b in zip(GOODS, trades_a, trades_b, strict=True):
        if deal_a is False and deal_b is True:
            forward.append(_spread(port_a, port_b, commodity, experience))
        if deal_b is False and deal_a is True:
            back.append(_spread(port_b, port_a, commodity, experience))
    if not forward or not back:
        return None
    return max(forward) + max(back)


def _code(class_id: int) -> str:
    letters = {True: "B", False: "S", None: "-"}
    return "".join(letters[deal] for deal in K.PORT_CLASS_TRADES[class_id])


def _trips(ship_cost: int, per_hold: float) -> str:
    if per_hold <= 0:
        return "n/a"
    return f"{ship_cost / (20 * per_hold):.1f}"


def _print_prices() -> tuple[int, int]:
    print("economy_scale_report")
    print()
    print("| Commodity | Chart sell 250 | Ours sell 250 | Chart buy 250 | Ours buy 250 | Per hold chart | Per hold ours | Ratio |")
    typical_seller = _port(4, sell_mcic=50, buy_mcic=-50)  # SSB sells fuel and organics
    typical_buyer = _port(6, sell_mcic=50, buy_mcic=-50)  # BBS buys fuel and organics
    # Equipment needs a seller of equipment (BBS sells it) and a buyer (SSB buys it).
    equip_seller = typical_buyer
    equip_buyer = typical_seller
    sellers = {FUEL: typical_seller, ORG: typical_seller, EQUIP: equip_seller}
    buyers = {FUEL: typical_buyer, ORG: typical_buyer, EQUIP: equip_buyer}
    for commodity in GOODS:
        chart_sell = ORIGINAL_250[commodity]["sell"]
        chart_buy = ORIGINAL_250[commodity]["buy"]
        ours_sell = port_sell_price(sellers[commodity], commodity, 0)
        ours_buy = port_buy_price(buyers[commodity], commodity, 0)
        chart_spread = (chart_buy - chart_sell) / 250
        ours_spread = ours_buy - ours_sell
        print(
            f"| {NAMES[commodity]} | {chart_sell} | {ours_sell * 250} | {chart_buy} | {ours_buy * 250} "
            f"| {chart_sell / 250:.2f} / {chart_buy / 250:.2f} | {ours_sell} / {ours_buy} "
            f"| {chart_spread / ours_spread:.2f} |"
        )
    print()
    print("Ratio is chart spread over our spread, at MCIC 50 and -50, 100 percent stock, experience 0.")
    print()
    print("| Pair | Codes | Typical per hold | Best per hold |")
    best_typical = -1
    tied: list[str] = []
    for class_a in range(1, 8):
        for class_b in range(class_a + 1, 8):
            typical = _round_trip(class_a, class_b, sell_mcic=50, buy_mcic=-50, experience=0)
            best = _round_trip(class_a, class_b, sell_mcic=1, buy_mcic=-100, experience=1000)
            label = f"{_code(class_a)} / {_code(class_b)}"
            if typical is None:
                print(f"| {class_a} x {class_b} | {label} | no round trip | no round trip |")
                continue
            print(f"| {class_a} x {class_b} | {label} | {typical} | {best} |")
            if typical > best_typical:
                best_typical = typical
                tied = [label]
            elif typical == best_typical:
                tied.append(label)
    print()
    print(f"Best typical pairs ({', '.join(tied)}) at {best_typical} credits per hold per round trip.")
    chart_equip = (ORIGINAL_250[EQUIP]["buy"] - ORIGINAL_250[EQUIP]["sell"]) / 250
    chart_org = (ORIGINAL_250[ORG]["buy"] - ORIGINAL_250[ORG]["sell"]) / 250
    chart_trip = chart_equip + chart_org
    print(
        f"Chart equipment spread {chart_equip:.2f} plus organics spread {chart_org:.2f} "
        f"is {chart_trip:.2f} per hold per round trip."
    )
    print(f"Chart over our best typical pair: {chart_trip / best_typical:.2f}.")
    return best_typical, round(chart_trip)


def _print_ships(our_per_hold: int, chart_per_hold: float) -> None:
    print()
    print("| Ship | Bible cost | Our cost | Our / Bible | Bible trips | Our trips | Bible max-hold cost | Our hold each |")
    for key, (bible_cost, bible_holds) in BIBLE.items():
        spec = K.SHIP_SPECS[key]
        print(
            f"| {spec['display_name']} | {bible_cost} | {spec['cost']} | {spec['cost'] / bible_cost:.2f} "
            f"| {_trips(bible_cost, chart_per_hold)} | {_trips(spec['cost'], our_per_hold)} "
            f"| {bible_holds} | {spec['base_hold_cost']} |"
        )
    print()
    print("Trips are ship cost / (20 holds x profit per hold per round trip).")
    print("Chart trips use the equipment-plus-organics sample. Our trips use the best typical pair.")
    print(f"Fighters: original wave 160 to 239, ours {K.FIGHTER_COST}.")
    print("Shields: no single original unit price in the saved files. Ours are 10 each.")
    print("Holds: original is B * H + I * H * (H - 1) / 2, I = 20, B about 151 to 249. Ours is the flat hold column.")


def _nearest(universe, sector_id: int) -> int | None:
    start = universe.sectors[sector_id].port
    if start is None:
        return None
    seen = {sector_id}
    queue = [(sector_id, 0)]
    while queue:
        here, dist = queue.pop(0)
        for nxt in universe.sectors[here].warps:
            if nxt in seen:
                continue
            seen.add(nxt)
            port = universe.sectors[nxt].port
            if port is not None and _complements(start, port):
                return dist + 1
            queue.append((nxt, dist + 1))
    return None


def _complements(left, right) -> bool:
    trades_l = K.PORT_CLASS_TRADES[int(left.class_id)]
    trades_r = K.PORT_CLASS_TRADES[int(right.class_id)]
    for deal_l, deal_r in zip(trades_l, trades_r, strict=True):
        if deal_l is False and deal_r is True:
            return True
        if deal_l is True and deal_r is False:
            return True
    return False


def _print_density() -> None:
    print()
    print("| Density | Seeds | Mean nearest pair | Mean of each map's closest pair |")
    saved = K.PORT_SPAWN_PROBABILITY
    try:
        for density in (0.65, 0.40):
            K.PORT_SPAWN_PROBABILITY = density
            nearest_all: list[int] = []
            closest: list[int] = []
            for seed in DENSITY_SEEDS:
                universe = generate_universe(
                    GameConfig(seed=seed, enable_planets=False, enable_ferrengi=False)
                )
                dists = []
                for sector in universe.sectors.values():
                    port = sector.port
                    if port is None or int(port.class_id) not in range(1, 8):
                        continue
                    dist = _nearest(universe, sector.id)
                    if dist is not None:
                        dists.append(dist)
                if dists:
                    nearest_all.extend(dists)
                    closest.append(min(dists))
            mean_all = sum(nearest_all) / len(nearest_all)
            mean_close = sum(closest) / len(closest)
            print(f"| {density:.2f} | {len(DENSITY_SEEDS)} | {mean_all:.2f} | {mean_close:.2f} |")
    finally:
        K.PORT_SPAWN_PROBABILITY = saved
    print()
    print("Nearest pair is the hop count from a class 1-7 port to the closest port that buys what it sells, or sells what it buys.")
    print("FedSpace ports stay. Only PORT_SPAWN_PROBABILITY is swapped, then put back.")
    print(f"spawn probability left at {K.PORT_SPAWN_PROBABILITY}")


def main() -> None:
    our_per_hold, chart_per_hold = _print_prices()
    _print_ships(our_per_hold, chart_per_hold)
    _print_density()


if __name__ == "__main__":
    main()
