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
_HOLD_PRICE = re.compile(r"([\d,]+)\s+cr each", re.I)
_REFUSED = re.compile(r"refused|the trade ended", re.I)


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


class ScriptedTrader:
    """Reads the sector, port and holds, then trades, buys gear, and spends the day."""

    def __init__(self) -> None:
        self.ports: dict[int, dict[str, dict[str, int]]] = {}
        self.codes: dict[int, str] = {}
        self.danger: set[int] = set()
        self.visited: set[int] = set()
        self.previous = 0
        self.day = 0
        self.bought: set[str] = set()
        self.gear: dict[str, str] | None = None
        self.dock_waits = 0
        self.links: dict[int, dict[int, int]] = {}
        self.warp_labels: dict[tuple[int, int], str] = {}
        self.pending_good = ""
        self.plan_note = ""
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
        if day and day != self.day:
            self.day = day
            self.bought.clear()
            self.gear = None
            self.dock_waits = 0
        cargo = _holds(str(screen.get("holds") or ""))
        self._remember(sector, screen, cargo)
        action = (
            self._modal(screen, labels, turns)
            or self._form(screen, labels)
            or self._leave_surface(labels)
            or self._leave_danger(sector, screen, cargo)
            or self._sell(screen, sector, cargo, turns)
            or self._buy(screen, sector, cargo, turns)
            or self._stardock(screen, labels, credits, turns)
            or self._warp(screen, sector, cargo, turns)
            or self._spend(screen, turns)
        )
        if sector:
            self.previous = sector
            self.visited.add(sector)
        return action

    def _remember(self, sector: int, screen: dict, cargo: dict[str, int]) -> None:
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
            price_at = 4 if len(cells) > 4 and str(cells[3]).endswith("%") else 3
            price = _int(cells[price_at] if price_at < len(cells) else "")
            status = cells[1].lower()
            slot = book.setdefault(name, {})
            if status.startswith("buying") and price:
                slot["bid"] = price
            elif status.startswith("selling") and price:
                slot["ask"] = price
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
        del cargo

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
        return "holds" not in self.bought or "fighters" not in self.bought

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
        """Where to buy: the widest gap between a seen ask and a seen bid."""
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

    def _held_good(self, cargo: dict[str, int]) -> str:
        return max(_GOODS, key=lambda name: cargo.get(name, 0))

    def _local_bid(self, sector: int, good: str) -> int:
        slot = (self.ports.get(sector) or {}).get(good) or {}
        if isinstance(slot, dict):
            return int(slot.get("bid") or 0)
        return 0

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
                if nxt in self.danger or nxt in dist:
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
                if nxt == src or nxt in prev or nxt in self.danger:
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
        """True when the turns left cover the buy, the hops, and the sale."""
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

    def _modal(self, screen: dict, labels: list[str], turns: int) -> Action | None:
        if not screen.get("menuOpen"):
            return None
        text = str(screen.get("menuText") or "")
        if screen.get("formOpen"):
            return None
        if _DAY_END.search(text) and any(row.upper() == "CONFIRM" for row in labels):
            # Nothing left to click opened this. Ending the day beats a stuck dialog.
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
        if buying:
            for good in goods:
                bid = self._known_bid(good)
                if bid and price > bid:
                    return False
        return True

    def _form(self, screen: dict, labels: list[str]) -> Action | None:
        if not screen.get("formOpen"):
            self.gear = None if self.gear and self.gear.get("phase") == "confirm" else self.gear
            return None
        fields = dict(screen.get("fields") or {})
        if screen.get("gearNote"):
            fields["note"] = str(screen.get("gearNote") or "")
        text = str(screen.get("formText") or "") + " " + str(screen.get("haggle") or "")
        if self.gear and "item" in fields:
            return self._gear_step(fields)
        if "BUY EQUIP" in text.upper() and "item" in fields:
            item = "fighters" if "holds" in self.bought else "holds"
            qty = self._hold_qty(fields) if item == "holds" else "5"
            self.gear = {"item": item, "phase": "select", "qty": qty}
            return self._gear_step(fields)
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

    def _hold_qty(self, fields: dict) -> str:
        note = str(fields.get("note") or "")
        price_match = _HOLD_PRICE.search(note)
        unit = int(price_match.group(1).replace(",", "")) if price_match else 0
        cap = _int(note.split("up to")[-1]) if "up to" in note.lower() else 1
        cap = max(1, cap)
        # One hold when we can pay. More only when a seen route covers the price.
        if unit <= 0:
            return "1"
        spread = self._best_spread()
        qty = 1
        if spread > unit:
            qty = min(cap, max(1, spread // unit))
        return str(qty)

    def _gear_step(self, fields: dict) -> Action:
        assert self.gear is not None
        phase = self.gear["phase"]
        item = self.gear["item"]
        if phase == "select":
            self.gear["phase"] = "qty"
            self.plan_note = f"choose {item}"
            return Action("type", selector='[data-n="item"]', text=item)
        if phase == "qty":
            qty = self._hold_qty(fields) if item == "holds" else self.gear["qty"]
            note = str(fields.get("note") or "")
            cap = _int(note.split("up to")[-1]) if "up to" in note.lower() else 0
            if cap and int(qty) > cap:
                qty = str(cap)
            self.gear["phase"] = "confirm"
            self.plan_note = f"qty {qty} {item}"
            return Action("type", selector='[data-n="qty"]', text=qty)
        self.bought.add(item)
        self.gear = None
        self.plan_note = f"buy {item}"
        return Action("click", label="CONFIRM")

    def _leave_surface(self, labels: list[str]) -> Action | None:
        for label in labels:
            if "lift off" in label.lower():
                self.plan_note = "lift off"
                return Action("click", label=label)
        return None

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

    def _buy(self, screen: dict, sector: int, cargo: dict[str, int], turns: int) -> Action | None:
        if _room(str(screen.get("ship") or ""), cargo) <= 0:
            return None
        if _REFUSED.search(str(screen.get("last") or "")):
            return None
        goal = self._best_ask_sector()
        if goal and goal != sector and self._reachable(sector, goal, turns):
            # A better ask is on the map. Go there instead of buying a thinner one.
            here_spread = 0
            for row in screen.get("rows") or []:
                button = str(row.get("button") or "")
                if not button.upper().startswith("BUY"):
                    continue
                cells = [str(cell) for cell in (row.get("cells") or [])]
                name = next((good for good in _GOODS if cells and good.lower() in cells[0].lower()), "")
                if not name:
                    continue
                here_spread = max(here_spread, self._known_bid(name) - self._row_price(cells))
            there = self._best_spread()
            if there > here_spread:
                return None
        best: tuple[int, str, str] | None = None
        for row in screen.get("rows") or []:
            button = str(row.get("button") or "")
            if not button.upper().startswith("BUY"):
                continue
            cells = [str(cell) for cell in (row.get("cells") or [])]
            name = next((good for good in _GOODS if cells and good.lower() in cells[0].lower()), "")
            if not name:
                continue
            ask = self._row_price(cells)
            bid = self._known_bid(name)
            if bid <= ask or ask <= 0:
                continue
            seller = self._bid_sector(name)
            if seller and not self._can_cash_out(sector, sector, seller, turns):
                continue
            spread = bid - ask
            if best is None or spread > best[0]:
                best = (spread, button, name)
        if best is None:
            return None
        self.pending_good = best[2]
        self.plan_note = "buy " + best[1]
        return Action("click", label=best[1])

    def _stardock(self, screen: dict, labels: list[str], credits: int, turns: int) -> Action | None:
        del turns
        if credits < 500 or screen.get("formOpen"):
            return None
        if self.gear and self.gear.get("phase") != "select":
            return None
        if not self._gear_pending():
            return None
        # A cargo route in progress is worth more than a gear detour.
        if self._best_spread() > 0 and not self._at_dock(screen):
            return None
        label = next((row for row in labels if row.lower().startswith("stardock: buy gear")), "")
        if not label:
            if self._at_dock(screen) and self.dock_waits < 2:
                self.dock_waits += 1
                self.plan_note = "stay for gear"
                return Action("wait", ms=400)
            return None
        self.dock_waits = 0
        item = "fighters" if "holds" in self.bought else "holds"
        self.gear = {"item": item, "phase": "select", "qty": "1" if item == "holds" else "5"}
        self.plan_note = "open stardock"
        return Action("click", label=label)

    def _click_warp(self, sector: int, dest: int) -> Action | None:
        label = self.warp_labels.get((sector, dest), "")
        if not label:
            return None
        self.plan_note = "warp " + label
        return Action("click", label=label)

    def _warp(self, screen: dict, sector: int, cargo: dict[str, int], turns: int, *, flee: bool = False) -> Action | None:
        options: list[tuple[int, str, int]] = []
        for label in screen.get("warps") or []:
            match = _WARP.match(str(label).strip())
            if match is None:
                continue
            dest = int(match.group(1))
            if dest in self.danger:
                continue
            cost_match = _WARP_COST.search(str(label))
            cost = int(cost_match.group(1)) if cost_match else 3
            if not flee and turns < cost:
                continue
            options.append((dest, str(label).strip(), cost))
        if not options and flee:
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
            picked = self._flee_choice(sector, options)
            self.plan_note = "leave danger"
            return Action("click", label=picked)

        goal = self._trade_target(sector, cargo)
        if goal and goal != sector and self._trip_fits(sector, goal, cargo, turns):
            step = self._first_step(sector, goal)
            if step is not None:
                action = self._click_warp(sector, step)
                if action is not None:
                    return action
        pair_known = self._best_spread() > 0 and (
            not goal or goal == sector or self._hops(sector, goal) is not None
        )
        if pair_known:
            # A full trip does not fit. Park on the seller for the next day.
            # A one-way warp off the pair is how the seat used to lose the route.
            if (
                not any(cargo.values())
                and goal
                and goal != sector
                and not self._last_day(screen)
                and self._reachable(sector, goal, turns)
            ):
                step = self._first_step(sector, goal)
                if step is not None:
                    action = self._click_warp(sector, step)
                    if action is not None:
                        self.plan_note = "park on the pair " + (action.label or "")
                        return action
            return None
        dest = self._explore_choice(sector, options)
        self.plan_note = "warp " + self.warp_labels.get((sector, dest), options[0][1])
        label = self.warp_labels.get((sector, dest))
        if label:
            return Action("click", label=label)
        for option, text, _cost in options:
            if option == dest:
                return Action("click", label=text)
        return None

    def _last_day(self, screen: dict) -> bool:
        day = _int(screen.get("day"))
        cap = _int(screen.get("maxDay"))
        return bool(day and cap and day >= cap)

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
            good = self._held_good(cargo)
            other = self._bid_sector(good)
            if other and other != sector and self._known_bid(good) > self._local_bid(sector, good):
                return other
            return 0
        ask_at = self._best_ask_sector()
        if ask_at and ask_at != sector:
            return ask_at
        return 0

    def _flee_choice(self, sector: int, options: list[tuple[int, str, int]]) -> str:
        safe = [row for row in options if row[0] != sector and row[0] not in self.danger]
        pool = safe or [row for row in options if row[0] != sector] or options

        def score(item: tuple[int, str, int]) -> int:
            dest = item[0]
            value = 0
            if dest == self.previous:
                value -= 5
            if dest not in self.visited:
                value += 2
            return value

        return max(pool, key=score)[1]

    def _explore_choice(self, sector: int, options: list[tuple[int, str, int]]) -> int:
        del sector

        def score(item: tuple[int, str, int]) -> int:
            dest = item[0]
            value = 0
            if dest == self.previous:
                value -= 5
            if dest not in self.visited:
                value += 3
            if dest in self.ports:
                value += 1
            return value

        return max(options, key=score)[0]

    def _spend(self, screen: dict, turns: int) -> Action:
        chip = str(screen.get("chip") or "")
        if "NO TURNS" in chip or "GAME OVER" in chip or turns <= 0:
            self.plan_note = "wait for the day"
            return Action("wait", ms=500)
        self.plan_note = "spend a turn"
        return Action("press", key=".")
