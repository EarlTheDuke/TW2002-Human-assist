"""Rule trader. Every fact it uses is text on the seat page."""

from __future__ import annotations

import re
from collections import deque

from ai_cockpit.actions import Action

_GOODS = ("Fuel Ore", "Organics", "Equipment")
_PORT_CODE = re.compile(r"Class\s+\d+\s+([BSX]{3})", re.I)
_NUMBER = re.compile(r"[\d,]+")
_WARP = re.compile(r"^\d+:(\d+)")
_WARP_COST = re.compile(r"\((\d+)t\)", re.I)
_CATALOG = re.compile(r"\b(?:armid|limpet|atomic)\s+mines\b|\bmine disruptor\b", re.I)
_OWN_FIGHTERS = re.compile(r"your fighters here:[^.]*\.", re.I)
_DANGER = re.compile(r"ferrengi|hostile fighters|\boffensive\b|\bmines\b", re.I)
_DAY_END = re.compile(r"ends your day", re.I)
_COUNTER = re.compile(r"for\s+([\d,]+)\s+cr", re.I)
_EACH = re.compile(r"([\d,]+)\s+cr each", re.I)
_UP_TO = re.compile(r"up to\s+([\d,]+)", re.I)
_REFUSED = re.compile(r"refused|the trade ended", re.I)
_PER_DAY = re.compile(r"([\d,]+)\s+per day", re.I)
_YARD = re.compile(
    r"Holds\s+([\d,]+)(?:\s+of\s+[\d,]+)?,\s+fighters\s+[\d,]+\s*,\s+shields\s+[\d,]+\s*,\s+(\d+)\s+turns per warp",
    re.I,
)
_YARD_PRICE = re.compile(r"([\d,]+)\s+cr\.", re.I)
_RESERVE = 20_000


def _int(text: object) -> int:
    match = _NUMBER.search(str(text or ""))
    if match is None:
        return 0
    return int(match.group(0).replace(",", ""))


def _holds(text: str) -> dict[str, int]:
    cargo: dict[str, int] = {}
    for name in _GOODS:
        match = re.search(re.escape(name) + r"\s+([\d,]+)", text or "", re.I)
        cargo[name] = int(match.group(1).replace(",", "")) if match else 0
    return cargo


def _room(ship: str, cargo: dict[str, int]) -> int:
    match = re.search(r"Holds\s+([\d,]+)\s*/\s*([\d,]+)", ship or "", re.I)
    if match is None:
        return 1 if sum(cargo.values()) == 0 else 0
    used = int(match.group(1).replace(",", ""))
    cap = int(match.group(2).replace(",", ""))
    return max(0, cap - used)


def _hold_cap(ship: str) -> int:
    match = re.search(r"Holds\s+[\d,]+\s*/\s*([\d,]+)", ship or "", re.I)
    if match is None:
        return 20
    return int(match.group(1).replace(",", ""))


class ScriptedTrader:
    """Reads the sector, port and holds, then trades, buys gear, and spends the day."""

    def __init__(self) -> None:
        self.ports: dict[int, dict[str, dict[str, int]]] = {}
        self.codes: dict[int, str] = {}
        self.danger: set[int] = set()
        self.visited: set[int] = set()
        self.previous = 0
        self.day = 0
        self.max_day = 0
        self.day_turns = 0
        self.bought: set[str] = set()
        self.gear: dict[str, str] | None = None
        self.dock_waits = 0
        self.links: dict[int, dict[int, int]] = {}
        self.warp_labels: dict[tuple[int, int], str] = {}
        self.pending_good = ""
        self.hold_price = 0
        self.shop_day = 0
        self.bank_day = 0
        self.bank: dict[str, str] | None = None
        self.yard: dict[str, str] | None = None
        self.yard_quotes: dict[str, str] = {}
        self.planet_looks = 0
        self.planet_worth = False
        self.plan_note = ""
        self.hold_cap = 20
        self.last_usage = None

    def decide(self, view) -> Action:
        if not view.manual_read:
            self.plan_note = "read the manual"
            return Action("click", label="Manual")
        if not view.screen:
            return self._bare(view)
        return self.play(view)

    def _bare(self, view) -> Action:
        """A label list with no scraped screen still sells, then waits."""
        labels = [row.strip() for row in view.labels if row and row.strip()]
        upper = [row.upper() for row in labels]
        if any(row == "CONFIRM" for row in upper):
            self.plan_note = "confirm"
            return Action("click", label="CONFIRM")
        if any(row.startswith("SELL") for row in upper):
            self.plan_note = "sell"
            return Action("click", label="SELL")
        self.plan_note = "wait"
        return Action("press", key=".")

    def play(self, view) -> Action:
        screen = view.screen or {}
        labels = [row.strip() for row in (screen.get("labels") or view.labels or []) if row and row.strip()]
        sector = _int(screen.get("sector"))
        day = _int(screen.get("day"))
        turns = _int(screen.get("turns"))
        credits = _int(screen.get("credits"))
        cap = _int(screen.get("maxDay"))
        if cap:
            self.max_day = cap
        if day and day != self.day:
            self.day = day
            self.day_turns = turns
            self.gear = None
            self.bank = None
            self.yard = None
            self.dock_waits = 0
        elif turns > self.day_turns:
            self.day_turns = turns
        cargo = _holds(str(screen.get("holds") or ""))
        self.hold_cap = _hold_cap(str(screen.get("ship") or ""))
        self._remember(sector, screen)
        action = (
            self._modal(screen, labels, turns)
            or self._form(screen, labels, credits)
            or self._leave_danger(sector, screen, cargo)
            or self._sell(screen, sector, cargo, turns)
            or self._buy(screen, sector, cargo, turns)
            or self._stardock(screen, labels, credits)
            or self._open_yard(labels, screen)
            or self._open_bank(screen, labels, credits)
            or self._planet(screen, labels)
            or self._warp(screen, sector, cargo, turns)
            or self._spend(screen, turns)
        )
        if sector:
            self.previous = sector
            self.visited.add(sector)
        return action

    def _remember(self, sector: int, screen: dict) -> None:
        if not sector:
            return
        if self._threatened(screen):
            self.danger.add(sector)
        book = self.ports.setdefault(sector, {})
        for row in screen.get("rows") or []:
            cells = [str(cell) for cell in (row.get("cells") or [])]
            if len(cells) < 4:
                continue
            name = next((good for good in _GOODS if good.lower() in cells[0].lower()), "")
            if not name:
                continue
            price = self._row_price(cells)
            status = cells[1].lower()
            qty = _int(cells[2]) if len(cells) > 2 else 0
            slot = book.setdefault(name, {})
            if status.startswith("buying") and price:
                slot["bid"] = price
            elif status.startswith("selling") and price:
                slot["ask"] = price
            else:
                continue
            if qty:
                slot["avail"] = max(int(slot.get("avail") or 0), qty)
        code = _PORT_CODE.search(str(screen.get("port") or ""))
        if code:
            self.codes[sector] = code.group(1).upper()
        for label in screen.get("warps") or []:
            match = _WARP.match(str(label).strip())
            if match is None:
                continue
            dest = int(match.group(1))
            cost_match = _WARP_COST.search(str(label))
            cost = int(cost_match.group(1)) if cost_match else 3
            self.links.setdefault(sector, {})[dest] = cost
            self.warp_labels[(sector, dest)] = str(label).strip()

    def _threatened(self, screen: dict) -> bool:
        """Ferrengi, hostile fighters, and deployed mines. A gear list is not a threat."""
        here = str(screen.get("here") or "")
        form = str(screen.get("formText") or "")
        if form:
            here = here.replace(form, " ")
        notes = _OWN_FIGHTERS.sub(" ", _CATALOG.sub(" ", here))
        notes += "\n" + str(screen.get("threat") or "")
        return _DANGER.search(notes) is not None

    def _at_dock(self, screen: dict) -> bool:
        blob = " ".join(
            str(screen.get(key) or "") for key in ("port", "here", "sector")
        ).lower()
        return _int(screen.get("sector")) == 1 or "stardock" in blob

    def _gear_pending(self) -> bool:
        return self._next_gear() is not None

    def _next_gear(self) -> str | None:
        for item in ("holds", "fighters", "shields"):
            if item not in self.bought:
                return item
        return None

    def _known_bid(self, good: str) -> int:
        best = 0
        for book in self.ports.values():
            slot = book.get(good) or {}
            if isinstance(slot, dict):
                best = max(best, int(slot.get("bid") or 0))
        return best

    def _bid_sector(self, good: str) -> int:
        best_at = 0
        best = 0
        for sector, book in self.ports.items():
            slot = book.get(good) or {}
            price = int(slot.get("bid") or 0) if isinstance(slot, dict) else 0
            if price > best:
                best = price
                best_at = sector
        return best_at

    def _best_spread(self) -> int:
        best = 0
        for book in self.ports.values():
            for name, slot in book.items():
                if not isinstance(slot, dict) or slot.get("ask") is None:
                    continue
                bid = self._known_bid(name)
                if bid > int(slot["ask"]):
                    best = max(best, bid - int(slot["ask"]))
        return best

    def _best_ask_sector(self) -> int:
        best_at = 0
        best = 0
        for sector, book in self.ports.items():
            for name, slot in book.items():
                if not isinstance(slot, dict) or slot.get("ask") is None:
                    continue
                spread = self._known_bid(name) - int(slot["ask"])
                if spread > best:
                    best = spread
                    best_at = sector
        return best_at

    def _priced_ports(self) -> int:
        return sum(1 for book in self.ports.values() if book)

    def _local_bid(self, sector: int, good: str) -> int:
        slot = (self.ports.get(sector) or {}).get(good) or {}
        if isinstance(slot, dict):
            return int(slot.get("bid") or 0)
        return 0

    def _edge_ok(self, src: int, dest: int) -> bool:
        """A one-way warp is usable once the return leg is already on screen memory."""
        label = self.warp_labels.get((src, dest), "")
        if "one-way" in label.lower() and src not in self.links.get(dest, {}):
            return False
        return True

    def _hops(self, src: int, dest: int) -> int | None:
        if not src or not dest:
            return None
        if src == dest:
            return 0
        dist = {src: 0}
        queue: deque[int] = deque([src])
        while queue:
            cur = queue.popleft()
            for nxt in self.links.get(cur, {}):
                if nxt in self.danger or nxt in dist or not self._edge_ok(cur, nxt):
                    continue
                dist[nxt] = dist[cur] + 1
                if nxt == dest:
                    return dist[nxt]
                queue.append(nxt)
        return None

    def _first_step(self, src: int, dest: int) -> int | None:
        if src == dest:
            return None
        prev: dict[int, int] = {}
        queue: deque[int] = deque([src])
        while queue:
            cur = queue.popleft()
            for nxt in self.links.get(cur, {}):
                if nxt == src or nxt in prev or nxt in self.danger or not self._edge_ok(cur, nxt):
                    continue
                prev[nxt] = cur
                if nxt == dest:
                    step = dest
                    while prev[step] != src:
                        step = prev[step]
                    return step
                queue.append(nxt)
        return None

    def _can_cash_out(self, src: int, buy_at: int, sell_at: int, turns: int) -> bool:
        out = self._hops(src, buy_at)
        back = self._hops(buy_at, sell_at)
        if out is None or back is None:
            return False
        need = out * 3 + 1 + back * 3 + (0 if buy_at == sell_at else 1)
        return turns >= need

    def _reachable(self, src: int, dest: int, turns: int) -> bool:
        hops = self._hops(src, dest)
        if hops is None:
            return False
        if hops == 0:
            return True
        step = self._first_step(src, dest)
        cost = self.links.get(src, {}).get(step or 0, 3)
        return turns >= hops * cost

    def _remaining_trips(self) -> int:
        cycle = 8
        per = max(1, (self.day_turns or cycle) // cycle)
        days = 1
        if self.max_day and self.day:
            days = max(1, self.max_day - self.day + 1)
        return per * days

    def _last_day(self, screen: dict) -> bool:
        day = _int(screen.get("day")) or self.day
        cap = _int(screen.get("maxDay")) or self.max_day
        return bool(day and cap and day >= cap)

    def _modal(self, screen: dict, labels: list[str], turns: int) -> Action | None:
        if not screen.get("menuOpen"):
            return None
        text = str(screen.get("menuText") or "")
        if screen.get("formOpen"):
            return None
        if _DAY_END.search(text) and any(row.upper() == "CONFIRM" for row in labels):
            self.plan_note = "end the day" if turns >= 3 else "spend the last turns"
            return Action("click", label="CONFIRM")
        self.plan_note = "close the dialog"
        return Action("press", key="Escape")

    def _offer_good(self, screen: dict) -> str:
        cargo = _holds(str(screen.get("holds") or ""))
        held = [name for name in _GOODS if cargo.get(name, 0) > 0]
        if len(held) == 1:
            return held[0]
        return self.pending_good

    def _counter_ok(self, screen: dict, sector: int, turns: int) -> bool:
        text = str(screen.get("haggle") or "") + " " + str(screen.get("formText") or "")
        match = _COUNTER.search(text)
        fields = screen.get("fields") or {}
        price = int(match.group(1).replace(",", "")) if match else _int(fields.get("unit_price"))
        if price <= 0:
            return True
        selling = "we'll buy" in text.lower() or "buy them" in text.lower()
        buying = "we'll sell" in text.lower() or "sell them" in text.lower()
        named = self._offer_good(screen)
        goods = (named,) if named else _GOODS
        if selling:
            for good in goods:
                other = self._bid_sector(good)
                bid = self._known_bid(good)
                if other and other != sector and bid > price and self._reachable(sector, other, turns):
                    return False
        if buying and named:
            bid = self._known_bid(named)
            if bid and price > bid:
                return False
        elif buying:
            for good in _GOODS:
                bid = self._known_bid(good)
                if bid and price > bid:
                    return False
        return True

    def _form(self, screen: dict, labels: list[str], credits: int) -> Action | None:
        if not screen.get("formOpen"):
            self.gear = None if self.gear and self.gear.get("phase") == "confirm" else self.gear
            self.bank = None if self.bank and self.bank.get("phase") == "confirm" else self.bank
            self.yard = None if self.yard and self.yard.get("phase") == "confirm" else self.yard
            return None
        fields = dict(screen.get("fields") or {})
        if screen.get("gearNote"):
            fields["note"] = str(screen.get("gearNote") or "")
        text = str(screen.get("formText") or "") + " " + str(screen.get("haggle") or "")
        if self.gear and "item" in fields:
            return self._gear_step(fields, credits)
        if "BUY EQUIP" in text.upper() and "item" in fields:
            item = self._next_gear() or "fighters"
            self.gear = {"item": item, "phase": "select"}
            return self._gear_step(fields, credits)
        if "BANK" in text.upper() or (self.bank and "amount" in fields):
            return self._bank_step(fields, credits, labels)
        if "ship_class" in fields or (self.yard and "SHIPYARD" in text.upper()):
            return self._yard_step(screen, fields, labels)
        if "TERRA" in text.upper() and "mode" in fields:
            return self._terra_step(fields, labels)
        trade = "TRADE" in text.upper() or "port counter" in text.lower() or "unit_price" in fields
        if trade and any(row.upper() == "CONFIRM" for row in labels):
            sector = _int(screen.get("sector"))
            turns = _int(screen.get("turns"))
            if _REFUSED.search(text):
                self.plan_note = "the haggle failed"
                if any(row.upper() == "ESC" for row in labels):
                    return Action("click", label="ESC")
                return Action("press", key="Escape")
            if not self._counter_ok(screen, sector, turns):
                self.plan_note = "decline the counter"
                if any(row.upper() == "ESC" for row in labels):
                    return Action("click", label="ESC")
                return Action("press", key="Escape")
            self.plan_note = "accept the port's price"
            return Action("click", label="CONFIRM")
        if any(row.upper() == "ESC" for row in labels):
            self.plan_note = "leave the form"
            return Action("click", label="ESC")
        self.plan_note = "close the form"
        return Action("press", key="Escape")

    def _hold_qty(self, fields: dict, credits: int) -> str:
        note = str(fields.get("note") or "")
        price_match = _EACH.search(note)
        unit = int(price_match.group(1).replace(",", "")) if price_match else 0
        cap_match = _UP_TO.search(note)
        cap = int(cap_match.group(1).replace(",", "")) if cap_match else 1
        cap = max(1, cap)
        if unit:
            self.hold_price = unit
        spread = self._best_spread()
        trips = self._remaining_trips()
        qty = 1
        if unit > 0 and spread * trips > unit:
            qty = min(cap, max(1, (spread * trips) // unit))
            if credits > unit:
                qty = min(qty, max(1, (credits - _RESERVE) // unit))
        return str(max(1, qty))

    def _gear_qty(self, item: str, fields: dict, credits: int) -> str:
        if item == "holds":
            return self._hold_qty(fields, credits)
        note = str(fields.get("note") or "")
        price_match = _EACH.search(note)
        unit = int(price_match.group(1).replace(",", "")) if price_match else 0
        cap_match = _UP_TO.search(note)
        cap = int(cap_match.group(1).replace(",", "")) if cap_match else 0
        want = 20 if item == "fighters" else 10
        if unit and credits > unit:
            want = min(want, max(1, (credits - _RESERVE) // unit))
        if cap:
            want = min(want, cap)
        return str(max(1, want))

    def _gear_step(self, fields: dict, credits: int) -> Action:
        assert self.gear is not None
        phase = self.gear["phase"]
        item = self.gear["item"]
        if phase == "select":
            self.gear["phase"] = "qty"
            self.plan_note = f"choose {item}"
            return Action("type", selector='[data-n="item"]', text=item)
        if phase == "qty":
            qty = self._gear_qty(item, fields, credits)
            self.gear["phase"] = "confirm"
            self.plan_note = f"qty {qty} {item}"
            return Action("type", selector='[data-n="qty"]', text=qty)
        self.bought.add(item)
        self.gear = None
        self.shop_day = self.day
        self.plan_note = f"buy {item}"
        return Action("click", label="CONFIRM")

    def _leave_danger(self, sector: int, screen: dict, cargo: dict[str, int]) -> Action | None:
        if sector not in self.danger:
            return None
        action = self._warp(screen, sector, cargo, _int(screen.get("turns")), flee=True)
        if action is not None:
            self.plan_note = "leave danger"
        return action

    def _row_price(self, cells: list[str]) -> int:
        price_at = 4 if len(cells) > 4 and str(cells[3]).endswith("%") else 3
        return _int(cells[price_at] if price_at < len(cells) else "")

    def _sell(self, screen: dict, sector: int, cargo: dict[str, int], turns: int) -> Action | None:
        if _REFUSED.search(str(screen.get("last") or "")):
            return None
        best: tuple[int, str, str] | None = None
        for row in screen.get("rows") or []:
            button = str(row.get("button") or "")
            if not button.upper().startswith("SELL"):
                continue
            cells = [str(cell) for cell in (row.get("cells") or [])]
            name = next((good for good in _GOODS if cells and good.lower() in cells[0].lower()), "")
            if name and cargo.get(name, 0) <= 0:
                continue
            price = self._row_price(cells)
            other = self._bid_sector(name) if name else 0
            other_bid = self._known_bid(name) if name else 0
            if other and other != sector and other_bid > price and self._reachable(sector, other, turns):
                continue
            if best is None or price > best[0]:
                best = (price, button, name)
        if best is None:
            return None
        self.pending_good = best[2]
        self.plan_note = "sell " + best[1]
        return Action("click", label=best[1])

    def _button_qty(self, button: str, room: int) -> int:
        match = re.search(r"(\d+)", button or "")
        listed = int(match.group(1)) if match else room
        if room <= 0:
            return max(1, listed)
        return max(1, min(room, listed))

    def _bid_score(self, good: str, src: int, ask: int, qty: int, turns: int) -> tuple[float, int, int] | None:
        """Best reachable buyer for this ask, scored by credits per turn."""
        best: tuple[float, int, int] | None = None
        for sector, book in self.ports.items():
            slot = book.get(good) or {}
            price = int(slot.get("bid") or 0) if isinstance(slot, dict) else 0
            if price <= ask:
                continue
            if not self._can_cash_out(src, src, sector, turns):
                continue
            hops = self._hops(src, sector)
            if hops is None:
                continue
            if not self._settled(src) and hops > 2:
                continue
            cycle = 1 + hops * 3 + (0 if hops == 0 else 1)
            score = ((price - ask) * qty) / max(1, cycle)
            if best is None or score > best[0]:
                best = (score, sector, price)
        return best

    def _buy(self, screen: dict, sector: int, cargo: dict[str, int], turns: int) -> Action | None:
        room = _room(str(screen.get("ship") or ""), cargo)
        if room <= 0:
            return None
        if _REFUSED.search(str(screen.get("last") or "")):
            return None
        if self._settled(sector):
            _value, ask_at, _bid_at, _cycle = self._best_run()
            if ask_at and ask_at != sector and self._reachable(sector, ask_at, turns):
                return None
        best: tuple[float, str, str] | None = None
        for row in screen.get("rows") or []:
            button = str(row.get("button") or "")
            if not button.upper().startswith("BUY"):
                continue
            cells = [str(cell) for cell in (row.get("cells") or [])]
            name = next((good for good in _GOODS if cells and good.lower() in cells[0].lower()), "")
            if not name:
                continue
            ask = self._row_price(cells)
            if ask <= 0:
                continue
            qty = self._button_qty(button, room)
            scored = self._bid_score(name, sector, ask, qty, turns)
            if scored is None:
                continue
            if best is None or scored[0] > best[0]:
                best = (scored[0], button, name)
        if best is None:
            return None
        self.pending_good = best[2]
        self.plan_note = "buy " + best[1]
        return Action("click", label=best[1])

    def _stardock(self, screen: dict, labels: list[str], credits: int) -> Action | None:
        if credits < 500 or screen.get("formOpen"):
            return None
        # Outfit on the opening visit. After leaving, wait until a route pays.
        left_the_dock = any(place not in (0, 1) for place in self.visited)
        if self._best_spread() <= 0 and left_the_dock:
            return None
        if self.gear and self.gear.get("phase") != "select":
            return None
        if not self._gear_pending():
            return None
        label = next((row for row in labels if row.lower().startswith("stardock: buy gear")), "")
        if not label:
            if self._at_dock(screen) and self.dock_waits < 2:
                self.dock_waits += 1
                self.plan_note = "stay for gear"
                return Action("wait", ms=400)
            return None
        self.dock_waits = 0
        item = self._next_gear() or "fighters"
        self.gear = {"item": item, "phase": "select"}
        self.plan_note = "open stardock"
        return Action("click", label=label)

    def _open_yard(self, labels: list[str], screen: dict) -> Action | None:
        if not self._at_dock(screen) or self._best_spread() <= 0 or "ship" in self.bought:
            return None
        if self._gear_pending():
            return None
        label = next((row for row in labels if row.lower() == "shipyards"), "")
        if not label:
            return None
        self.yard = {"phase": "look"}
        self.plan_note = "read the shipyard"
        return Action("click", label=label)

    def _yard_pays(self, screen: dict, text: str) -> bool:
        match = _YARD.search(text)
        if match is None:
            return False
        holds = int(match.group(1).replace(",", ""))
        tpw = max(1, int(match.group(2)))
        price_match = _YARD_PRICE.search(text)
        price = int(price_match.group(1).replace(",", "")) if price_match else 0
        if "you get" in text.lower() and "back" in text.lower():
            price = 0
        current = _hold_cap(str(screen.get("ship") or ""))
        if holds <= current:
            return False
        spread = self._best_spread()
        trips = max(1, self._remaining_trips())
        current_tpw = 3
        for costs in self.links.values():
            if costs:
                current_tpw = min(costs.values())
                break
        old_cycle = max(2, current_tpw * 2 + 2)
        new_cycle = max(2, tpw * 2 + 2)
        old_profit = current * spread * max(1, trips * old_cycle // new_cycle)
        new_profit = holds * spread * trips
        return new_profit - old_profit > price

    def _yard_step(self, screen: dict, fields: dict, labels: list[str]) -> Action:
        text = str(screen.get("formText") or "")
        options = fields.get("ship_classOptions") or []
        if not isinstance(options, list):
            options = []
        current = str(fields.get("ship_class") or "")
        if current and current not in self.yard_quotes:
            self.yard_quotes[current] = text
            unseen = [str(option) for option in options if str(option) not in self.yard_quotes]
            if unseen:
                self.plan_note = "compare " + unseen[0]
                return Action("type", selector='[data-n="ship_class"]', text=unseen[0])
        best = ""
        best_gain = 0
        for name, quote in self.yard_quotes.items():
            if not self._yard_pays(screen, quote):
                continue
            match = _YARD.search(quote)
            holds = int(match.group(1).replace(",", "")) if match else 0
            if holds > best_gain:
                best_gain = holds
                best = name
        if best:
            if current != best:
                self.plan_note = "choose " + best
                return Action("type", selector='[data-n="ship_class"]', text=best)
            self.bought.add("ship")
            self.yard = None
            self.plan_note = "buy the ship"
            if any(row.upper() == "CONFIRM" for row in labels):
                return Action("click", label="CONFIRM")
        self.bought.add("ship")
        self.yard = None
        self.plan_note = "keep the current ship"
        if any(row.upper() == "ESC" for row in labels):
            return Action("click", label="ESC")
        return Action("press", key="Escape")

    def _open_bank(self, screen: dict, labels: list[str], credits: int) -> Action | None:
        if not self._at_dock(screen) or self.bank_day == self.day:
            return None
        if self._gear_pending():
            return None
        if credits < _RESERVE + 5_000:
            return None
        label = next((row for row in labels if row.lower() == "bank"), "")
        if not label:
            return None
        self.bank = {"phase": "amount", "amount": str(credits - _RESERVE)}
        self.plan_note = "open the bank"
        return Action("click", label=label)

    def _bank_step(self, fields: dict, credits: int, labels: list[str]) -> Action | None:
        phase = (self.bank or {}).get("phase") or "amount"
        if phase == "amount" and "amount" in fields:
            amount = str(max(1, credits - _RESERVE))
            if self.bank is None:
                self.bank = {}
            self.bank["phase"] = "confirm"
            self.plan_note = "deposit " + amount
            return Action("type", selector='[data-n="amount"]', text=amount)
        self.bank_day = self.day
        self.bank = None
        self.plan_note = "deposit the surplus"
        if any(row.upper() == "CONFIRM" for row in labels):
            return Action("click", label="CONFIRM")
        return Action("press", key="Escape")

    def _terra_step(self, fields: dict, labels: list[str]) -> Action | None:
        if not self.planet_worth:
            self.plan_note = "colonists can wait"
            if any(row.upper() == "ESC" for row in labels):
                return Action("click", label="ESC")
            return Action("press", key="Escape")
        if str(fields.get("mode") or "") not in ("take", ""):
            self.plan_note = "take colonists"
            return Action("type", selector='[data-n="mode"]', text="take")
        qty = str(fields.get("qty") or "10")
        self.planet_worth = False
        self.plan_note = "load colonists"
        if any(row.upper() == "CONFIRM" for row in labels):
            if not fields.get("qty"):
                return Action("type", selector='[data-n="qty"]', text=qty)
            return Action("click", label="CONFIRM")
        return Action("press", key="Escape")

    def _planet_daily(self, screen: dict) -> int:
        return sum(int(match.group(1).replace(",", "")) for match in _PER_DAY.finditer(str(screen.get("here") or "")))

    def _planet(self, screen: dict, labels: list[str]) -> Action | None:
        landed = any("lift off" in row.lower() for row in labels)
        if not landed:
            return None
        daily = self._planet_daily(screen)
        horizon = max(1, (self.max_day - self.day + 1) if self.max_day and self.day else 1)
        worth = daily * max(self._known_bid("Organics"), 1) * horizon
        pair = self._best_spread() * _hold_cap(str(screen.get("ship") or "")) * max(1, self._remaining_trips())
        self.planet_worth = bool(daily) and worth > pair
        if self.planet_worth:
            claim = next((row for row in labels if row.lower() == "claim planet"), "")
            if claim:
                self.plan_note = "claim the planet"
                return Action("click", label=claim)
            colonists = next((row for row in labels if row.lower() == "colonists"), "")
            if colonists:
                self.plan_note = "assign colonists"
                return Action("click", label=colonists)
        for label in labels:
            if "lift off" in label.lower():
                self.plan_note = "the planet pays less than the ports"
                return Action("click", label=label)
        return None

    def _click_warp(self, sector: int, dest: int) -> Action | None:
        label = self.warp_labels.get((sector, dest), "")
        if not label:
            return None
        self.plan_note = "warp " + label
        return Action("click", label=label)

    def _avail(self, slot: dict) -> int:
        qty = int(slot.get("avail") or 0)
        return qty if qty > 0 else 100

    def _best_run(self) -> tuple[int, int, int, int]:
        """Best seen pair as (credits it can earn today, ask sector, bid sector, turn cycle)."""
        best = (0, 0, 0, 0)
        turns = self.day_turns or 40
        cap = max(1, self.hold_cap or 20)
        for ask_at, book in self.ports.items():
            for name, slot in book.items():
                if not isinstance(slot, dict) or slot.get("ask") is None:
                    continue
                ask = int(slot["ask"])
                ask_qty = self._avail(slot)
                for bid_at, other in self.ports.items():
                    if bid_at == ask_at:
                        continue
                    booked = other.get(name) or {}
                    if not isinstance(booked, dict) or not booked.get("bid"):
                        continue
                    bid = int(booked["bid"])
                    if bid <= ask:
                        continue
                    hops = self._hops(ask_at, bid_at)
                    back = self._hops(bid_at, ask_at)
                    if hops is None or back is None:
                        continue
                    cycle = hops * 3 + 1 + back * 3 + 1
                    if cycle > turns:
                        continue
                    bid_qty = self._avail(booked)
                    per = max(1, min(cap, ask_qty, bid_qty))
                    trips = max(1, turns // cycle)
                    units = min(ask_qty, bid_qty, per * trips)
                    value = (bid - ask) * units
                    if value > best[0]:
                        best = (value, ask_at, bid_at, cycle)
        return best

    def _settled(self, sector: int) -> bool:
        """A short pair that pays and can be reached from this sector."""
        value, ask, _bid, cycle = self._best_run()
        if not (cycle and cycle <= 14 and value >= 2000):
            return False
        if not sector or sector == ask:
            return True
        return self._hops(sector, ask) is not None

    def _should_shop(self, sector: int, turns: int) -> bool:
        if not self._settled(sector) or sector == 1 or self.shop_day == self.day or self._best_spread() <= 0:
            return False
        if "fighters" in self.bought and "shields" in self.bought and "ship" in self.bought:
            return False
        if self._hops(sector, 1) is None:
            return False
        back = self._best_ask_sector() or sector
        if self._hops(1, back) is None and self._hops(1, sector) is None:
            return False
        hops = self._hops(sector, 1) or 1
        return turns > hops * 3

    def _warp(self, screen: dict, sector: int, cargo: dict[str, int], turns: int, *, flee: bool = False) -> Action | None:
        options: list[tuple[int, str, int]] = []
        for label in screen.get("warps") or []:
            match = _WARP.match(str(label).strip())
            if match is None:
                continue
            dest = int(match.group(1))
            if dest in self.danger:
                continue
            text = str(label).strip()
            if "one-way" in text.lower() and sector not in self.links.get(dest, {}):
                continue
            cost_match = _WARP_COST.search(str(label))
            cost = int(cost_match.group(1)) if cost_match else 3
            if not flee and turns < cost:
                continue
            options.append((dest, text, cost))
        if not options and flee:
            for label in screen.get("warps") or []:
                match = _WARP.match(str(label).strip())
                if match is None:
                    continue
                dest = int(match.group(1))
                if dest != sector and dest not in self.danger:
                    options.append((dest, str(label).strip(), 3))
            if not options:
                for label in screen.get("warps") or []:
                    match = _WARP.match(str(label).strip())
                    if match is None:
                        continue
                    dest = int(match.group(1))
                    if dest != sector:
                        options.append((dest, str(label).strip(), 3))
        if not options:
            return None
        if flee:
            picked = self._flee_choice(options)
            self.plan_note = "leave danger"
            return Action("click", label=picked)
        if self._should_shop(sector, turns) and not any(cargo.values()):
            step = self._first_step(sector, 1)
            if step is not None:
                action = self._click_warp(sector, step)
                if action is not None:
                    self.plan_note = "head for StarDock"
                    return action
        goal = self._trade_target(sector, cargo)
        if any(cargo.values()) and goal and goal != sector and self._trip_fits(sector, goal, cargo, turns):
            step = self._first_step(sector, goal)
            if step is not None:
                action = self._click_warp(sector, step)
                if action is not None:
                    return action
        if self._settled(sector) and not any(cargo.values()):
            _value, ask_at, _bid_at, cycle = self._best_run()
            if ask_at and ask_at != sector and self._trip_fits(sector, ask_at, cargo, turns):
                step = self._first_step(sector, ask_at)
                if step is not None:
                    action = self._click_warp(sector, step)
                    if action is not None:
                        self.plan_note = "run the pair " + (action.label or "")
                        return action
            if (
                ask_at
                and ask_at != sector
                and not self._last_day(screen)
                and self._reachable(sector, ask_at, turns)
            ):
                step = self._first_step(sector, ask_at)
                if step is not None:
                    action = self._click_warp(sector, step)
                    if action is not None:
                        self.plan_note = "park on the pair " + (action.label or "")
                        return action
            if ask_at == sector and turns < (cycle or 8):
                return None
        # A few leftover turns cannot finish a seen pair. Don't wander off it.
        if (
            self._last_day(screen)
            and not any(cargo.values())
            and turns < 8
            and self._best_spread() > 0
        ):
            seen = self._best_ask_sector()
            if (
                seen
                and self._hops(sector, seen) is not None
                and not self._trip_fits(sector, seen, cargo, turns)
            ):
                self.plan_note = "wait out the last day"
                return None
        dest = self._explore_choice(sector, options)
        self.plan_note = "warp " + self.warp_labels.get((sector, dest), "")
        label = self.warp_labels.get((sector, dest))
        if label:
            return Action("click", label=label)
        for option, text, _cost in options:
            if option == dest:
                return Action("click", label=text)
        return None

    def _trip_fits(self, sector: int, goal: int, cargo: dict[str, int], turns: int) -> bool:
        if any(cargo.values()):
            hops = self._hops(sector, goal)
            return hops is not None and turns >= hops * 3 + 1
        seller = 0
        for name, slot in (self.ports.get(goal) or {}).items():
            if isinstance(slot, dict) and slot.get("ask") is not None and self._known_bid(name) > int(slot["ask"]):
                seller = self._bid_sector(name)
                break
        if not seller:
            return False
        return self._can_cash_out(sector, goal, seller, turns)

    def _trade_target(self, sector: int, cargo: dict[str, int]) -> int:
        if any(cargo.values()):
            good = max(_GOODS, key=lambda name: cargo.get(name, 0))
            other = self._bid_sector(good)
            if other and other != sector and self._known_bid(good) > self._local_bid(sector, good):
                return other
            return 0
        ask_at = self._best_ask_sector()
        if ask_at and ask_at != sector:
            return ask_at
        return 0

    def _flee_choice(self, options: list[tuple[int, str, int]]) -> str:
        def score(item: tuple[int, str, int]) -> int:
            dest = item[0]
            value = 0
            if dest == self.previous:
                value -= 5
            if dest not in self.visited:
                value += 2
            return value

        return max(options, key=score)[1]

    def _toward_unseen(self, src: int) -> int | None:
        prev: dict[int, int] = {}
        dist = {src: 0}
        queue: deque[int] = deque([src])
        found: int | None = None
        while queue:
            cur = queue.popleft()
            for nxt in self.links.get(cur, {}):
                if nxt in dist or nxt in self.danger or not self._edge_ok(cur, nxt):
                    continue
                dist[nxt] = dist[cur] + 1
                prev[nxt] = cur
                if nxt not in self.visited:
                    found = nxt
                    break
                queue.append(nxt)
            if found is not None:
                break
        if found is None:
            return None
        step = found
        while prev[step] != src:
            step = prev[step]
        return step

    def _explore_choice(self, sector: int, options: list[tuple[int, str, int]]) -> int:
        fresh = [item for item in options if item[0] not in self.visited]

        def score(item: tuple[int, str, int]) -> int:
            dest = item[0]
            value = 10 if dest not in self.visited else -3
            if dest == self.previous:
                value -= 8
            if dest == 1 and not self._settled(sector):
                value -= 20
            value += sum(1 for nxt in self.links.get(dest, {}) if nxt not in self.visited)
            return value

        if fresh:
            return max(fresh, key=score)[0]
        step = self._toward_unseen(sector)
        if step is not None and any(item[0] == step for item in options):
            return step
        return max(options, key=score)[0]

    def _spend(self, screen: dict, turns: int) -> Action:
        chip = str(screen.get("chip") or "")
        if "NO TURNS" in chip or "GAME OVER" in chip or turns <= 0:
            self.plan_note = "wait for the day"
            return Action("wait", ms=500)
        self.plan_note = "spend a turn"
        return Action("press", key=".")
