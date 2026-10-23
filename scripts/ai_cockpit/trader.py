"""Rule trader. Every fact it uses is text on the seat page."""

from __future__ import annotations

import heapq
import re
import time
from collections import deque

from ai_cockpit.actions import Action
from ai_cockpit.redact import secret_values

# The Comms panel already enforces these. The seat obeys them from the screen.
LINE_MAX = 155
SEND_GAP_S = 2.0
SEND_CAP = 3
QUIET_BEFORE_MEMO = 8
REPLY_LINES = (
    "Copy. I hear you. Staying on my route.",
    "Understood. Holding course and watching the port.",
    "Received. I will keep to the trade I can see.",
)
_HAIL = re.compile(r"^(.+?) hails you: .+$")
_MEMO = re.compile(r"^Corporate memo \([^)]+\) (.+?): .+$")
_UNSAFE_OUT = re.compile(
    r"sk-|xai-|bearer\s|system prompt|ignore (?:all |any |previous |prior )?instructions|api[_ ]?key",
    re.I,
)

_GOODS = ("Fuel Ore", "Organics", "Equipment")
_COMMODITY = {"Fuel Ore": "fuel_ore", "Organics": "organics", "Equipment": "equipment"}
_PORT_CODE = re.compile(r"Class\s+\d+\s+([BSX]{3})", re.I)
_NUMBER = re.compile(r"[\d,]+")
_WARP = re.compile(r"^\d+:(\d+)")
_WARP_COST = re.compile(r"\((\d+)t\)", re.I)
_CATALOG = re.compile(r"\b(?:armid|limpet|atomic)\s+mines\b|\bmine disruptor\b", re.I)
_OWN_FIGHTERS = re.compile(r"your fighters here:[^.]*\.", re.I)
_DANGER = re.compile(r"ferrengi|hostile fighters|\boffensive\b|\bmines\b|\balien\b", re.I)
_ENTERED = re.compile(r"entering\s+(\d+)", re.I)
_DENSITY = re.compile(r"Sector\s+(\d+)\s+==>\s+([\d,]+)", re.I)
_DAY_END = re.compile(r"ends your day", re.I)
_EACH = re.compile(r"([\d,]+)\s+cr each", re.I)
_PAREN_EACH = re.compile(r"\(([\d,]+)\s+each\)", re.I)
_AT_CR = re.compile(r"\bat\s+([\d,]+)\s+cr\b", re.I)
_FOR_UNIT = re.compile(r"\bfor\s+([\d,]+)\s+cr\b", re.I)
_TURNS_LEFT = re.compile(r"turns left today:\s*([\d,]+)\s+of\s+([\d,]+)", re.I)
_CLOCK_RATE = re.compile(r"\+1 every\s+([\d.]+)\s*s", re.I)
_TURNS_FACE = re.compile(r"^\s*([\d,]+)\s*/\s*([\d,]+)")
_BOARDING = re.compile(r"flee,\s*attack or surrender|ferrengi fighter attack|ferrengi boarding", re.I)
_COMMS = re.compile(r"\b(hail|radio|fed\s*comm|broadcast|announcement)\b", re.I)
_UP_TO = re.compile(r"up to\s+([\d,]+)", re.I)
_REFUSED = re.compile(r"refused|the trade ended", re.I)
_PER_DAY = re.compile(r"([\d,]+)\s+per day", re.I)
_YARD = re.compile(
    r"Holds\s+([\d,]+)(?:\s+of\s+[\d,]+)?,\s+fighters\s+[\d,]+\s*,\s+shields\s+[\d,]+\s*,\s+(\d+)\s+turns per warp",
    re.I,
)
_YARD_PRICE = re.compile(r"([\d,]+)\s+cr\.", re.I)
_RESERVE = 20_000
# NOTE 172b. Cash on board that makes a StarDock trip a small part of it.
_RICH = 20_000
_COURSE = re.compile(r"Course to (\d+):\s*([0-9 >]+)")
_BANK_BAL = re.compile(r"balance\s+([\d,]+)", re.I)


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


def _quoted_unit(text: str) -> int:
    """Unit price from the haggle line. The v3.11 table prints the total, then the each-price."""
    for pattern in (_EACH, _PAREN_EACH, _AT_CR, _FOR_UNIT):
        match = pattern.search(text or "")
        if match:
            return int(match.group(1).replace(",", ""))
    return 0


def _counter_offer(listed: int, text: str, *, side: str = "") -> int:
    """A price the v3.11 counter still takes, read from the quote on the form.

    The chart's tightest port pays 110 percent of a sale and takes about 90
    percent of a purchase. Those two are inside every wider port, and the
    screen never prints the port's own column. A line that already says the
    port countered is the port's number. ``side`` is the form's own choice
    when the quote line has not been painted yet.
    """
    if listed <= 0 or "port counter" in (text or "").lower():
        return 0
    low = (text or "").lower()
    if "we'll buy" in low or "buy them" in low:
        kind = "sell"
    elif "we'll sell" in low or "sell them" in low:
        kind = "buy"
    elif side in ("buy", "sell"):
        kind = side
    else:
        return 0
    if kind == "sell":
        return max(listed, (listed * 110) // 100)
    return min(listed, max(1, (listed * 90 + 99) // 100))


def _screen_turns(screen: dict) -> tuple[int, int | None]:
    """Turns still available, and the day's pocket when the screen prints one.

    "Turns left today: N of M" is the full-length sentence. The turns stat is
    "N/M" under the same "Turns left today" label. Either one beats the bare prompt.
    """
    match = _TURNS_LEFT.search(str(screen.get("turnsLeft") or ""))
    if match:
        left = int(match.group(1).replace(",", ""))
        pocket = int(match.group(2).replace(",", ""))
        return left, pocket
    face = _TURNS_FACE.match(str(screen.get("turnsFace") or ""))
    if face:
        left = int(face.group(1).replace(",", ""))
        pocket = int(face.group(2).replace(",", ""))
        return left, pocket
    return _int(screen.get("turns")), None


def _turn_clock(screen: dict) -> bool:
    """The turns stat says "(+1 every ...)" only while the server's turn clock is live."""
    return "+1 every" in str(screen.get("turnsFace") or "").lower()


class ScriptedTrader:
    """Reads the sector, port and holds, then trades, buys gear, and spends the day.

    ``level`` is easy (wander and take a weak local trade), normal (settle sooner,
    holds and fighters only), or hard (the long-game trader). Anything else is hard.
    """

    def __init__(self, level: str = "hard") -> None:
        text = (level or "hard").strip().lower()
        self.level = text if text in ("easy", "normal", "hard") else "hard"
        self.plot_to = 0
        self.home_ask = 0
        self.settled_day = 0
        self.dock_go = False
        self.dock_blocked = False
        self.dock_skip_day = 0
        self.banned_plots: set[int] = set()
        self.ship_skip_profit = 0
        self.ports: dict[int, dict[str, dict[str, int]]] = {}
        self.codes: dict[int, str] = {}
        self.danger: set[int] = set()
        self.ships: set[int] = set()
        self.fought: set[int] = set()
        self.wait_holds = 0
        self.visited: set[int] = set()
        self.previous = 0
        self.day = 0
        self.max_day = 0
        self.day_turns = 0
        self.bought: set[str] = set()
        # NOTE 172. Mid-game refits: the day each item was last bought again,
        # and items the StarDock form says this hull cannot take any more of.
        self.refit_day: dict[str, int] = {}
        self.maxed: set[str] = set()
        self.first_gear_day = 0
        self.gear: dict[str, str] | None = None
        self.dock_waits = 0
        self.links: dict[int, dict[int, int]] = {}
        self.warp_labels: dict[tuple[int, int], str] = {}
        self.pending_good = ""
        self.deal: dict[str, str] | None = None
        self.passed_trades: set[tuple[int, str, str]] = set()
        self.trade_sector = 0
        self.hold_price = 0
        self.shop_day = 0
        self.bank_day = 0
        self.refill_slept = False
        self.hull_day = 0
        self.clock_waits = 0
        self.clock_wait_day = 0
        self.clock_live = False
        self.ship_skip_credits = 0
        self.bank: dict[str, str] | None = None
        self.yard: dict[str, str] | None = None
        self.yard_quotes: dict[str, str] = {}
        self.planet_looks = 0
        self.planet_worth = False
        self.plan_note = ""
        self.hold_cap = 20
        self.last_usage = None
        self.credits = 0
        self.scanner = False
        self.scanned: set[int] = set()
        self.fresh_chain = 0
        self.pair_blocked = 0
        self.scout_day = 0
        self.scan_pending = 0
        self.comms_job: dict | None = None
        self.answered: set[str] = set()
        self.sent = 0
        self.last_send = 0.0
        self.memo_sent = False
        self.quiet = 0

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
        turns, pocket = _screen_turns(screen)
        credits = _int(screen.get("credits"))
        cap = _int(screen.get("maxDay"))
        if cap:
            self.max_day = cap
        if day and day != self.day:
            self.day = day
            self.day_turns = pocket or turns
            self.gear = None
            self.bank = None
            self.yard = None
            self.dock_waits = 0
            self.fresh_chain = 0
            # A port bought out yesterday has product again. Forgetting that
            # left hard sitting on the empty ask until the clock ran out.
            self._restock_seen()
            # Fighters move overnight, including one that boarded us. Keeping the
            # sector closed is how the next day missed the lane back to the pair.
            self.danger -= self.ships
            self.danger -= self.fought
            self.ships.clear()
            self.fought.clear()
            self.wait_holds = 0
        elif pocket:
            self.day_turns = max(self.day_turns, pocket)
        elif turns > self.day_turns:
            self.day_turns = turns
        self.credits = credits
        if sector != self.trade_sector:
            self.passed_trades.clear()
            self.trade_sector = sector
        cargo = _holds(str(screen.get("holds") or ""))
        self.hold_cap = _hold_cap(str(screen.get("ship") or ""))
        self._remember(sector, screen)
        comms = self._comms(screen, allow_new=not screen.get("menuOpen"))
        if self.level == "easy":
            self.plot_to = 0
            action = (
                comms
                or self._ferrengi(screen, labels)
                or self._modal(screen, labels, turns)
                or self._form(screen, labels, credits)
                or self._planet(screen, labels)
                or self._leave_danger(sector, screen, cargo)
                or self._easy_trade(screen, sector, cargo)
                or self._easy_warp(screen, sector, cargo, turns)
                or self._spend(screen, turns)
            )
        else:
            self._sync_plot(sector, turns, credits, cargo)
            plotted = self._plot_step(screen, labels, sector) if self._plot_blocks(screen) else None
            action = (
                comms
                or self._ferrengi(screen, labels)
                or self._modal(screen, labels, turns)
                or self._form(screen, labels, credits)
                or self._leave_danger(sector, screen, cargo)
                or plotted
                or self._sell(screen, sector, cargo, turns)
                or self._plot_step(screen, labels, sector)
                or self._return_home(screen, sector, cargo)
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
        if not (action.op == "press" and action.key in (".", "Escape")):
            self.wait_holds = 0
        # NOTE 172b. The server stands a seat down for the day at its fourth
        # Wait in a row. Any other move it applies starts the count again.
        if action.op == "press" and action.key == ".":
            if self.day != self.clock_wait_day:
                self.clock_waits, self.clock_wait_day = 0, self.day
            self.clock_waits += 1
        elif action.op == "click" or action.op == "type":
            self.clock_waits = 0
        return action

    def _restock_seen(self) -> None:
        """Overnight, a port we emptied sells again up to the quantity we saw."""
        for book in self.ports.values():
            for slot in book.values():
                if not isinstance(slot, dict):
                    continue
                avail = int(slot.get("avail") or 0)
                if avail > 0:
                    slot["now"] = avail

    def _remember(self, sector: int, screen: dict) -> None:
        if not sector:
            return
        if self._threatened(screen):
            self._note_threat(sector, screen)
        self._note_warnings(screen)
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
            slot["now"] = qty
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

    def _note_threat(self, sector: int, screen: dict) -> None:
        """Mines and aliens stay marked. A fighter on this sector can leave overnight."""
        here = str(screen.get("here") or "")
        form = str(screen.get("formText") or "")
        if form:
            here = here.replace(form, " ")
        notes = _OWN_FIGHTERS.sub(" ", _CATALOG.sub(" ", here))
        notes += "\n" + str(screen.get("threat") or "")
        notes += "\n" + str(screen.get("last") or "")
        if re.search(r"\bmines\b|\balien\b", notes, re.I):
            self.danger.add(sector)
            return
        self.ships.add(sector)
        self.danger.add(sector)

    def _threatened(self, screen: dict) -> bool:
        """Ferrengi, hostile fighters, aliens, and deployed mines. A gear list is not a threat."""
        here = str(screen.get("here") or "")
        form = str(screen.get("formText") or "")
        if form:
            here = here.replace(form, " ")
        notes = _OWN_FIGHTERS.sub(" ", _CATALOG.sub(" ", here))
        notes += "\n" + str(screen.get("threat") or "")
        notes += "\n" + str(screen.get("last") or "")
        return _DANGER.search(notes) is not None

    def _note_warnings(self, screen: dict) -> None:
        """Remember a sector the arrival text already named as mined or crowded."""
        text = str(screen.get("last") or "") + "\n" + str(screen.get("here") or "")
        if re.search(r"\bmines\b", text, re.I):
            for match in _ENTERED.finditer(text):
                self.danger.add(int(match.group(1)))
        last = str(screen.get("last") or "")
        for match in _DENSITY.finditer(last):
            sid = int(match.group(1))
            density = int(match.group(2).replace(",", ""))
            tail = last[match.start():match.end() + 80]
            if density >= 200 or re.search(r"mines|ferrengi|alien", tail, re.I):
                self.danger.add(sid)
        here = _int(screen.get("sector"))
        if self.scan_pending == here and (_DENSITY.search(last) or re.search(r"NavHaz", last, re.I)):
            self.scanned.add(here)
            self.scan_pending = 0

    def _at_dock(self, screen: dict) -> bool:
        blob = " ".join(
            str(screen.get(key) or "") for key in ("port", "here", "sector")
        ).lower()
        return _int(screen.get("sector")) == 1 or "stardock" in blob

    def _gear_pending(self) -> bool:
        return self._next_gear() is not None

    def _next_gear(self) -> str | None:
        for item in ("holds", "fighters"):
            if item not in self.bought:
                return item
        return None

    def _extra_gear(self) -> str | None:
        """A scanner or one probe, once holds and fighters are aboard and the credits cover it."""
        if self.level == "easy" or self._next_gear():
            return None
        if "density_scanner" not in self.bought and self.credits >= 2_500:
            return "density_scanner"
        # The legacy shelf has probes when it does not list a scanner. Buy one.
        if (
            "density_scanner" in self.bought
            and not self.scanner
            and "ether_probes" not in self.bought
            and self.credits >= 8_000
        ):
            return "ether_probes"
        return self._refit_item()

    def _refit_item(self) -> str | None:
        """NOTE 172. More holds, fighters, or shields once the wallet can carry them.

        Holds come first, and only when the paying pair can fill more than the
        hull carries now. Fighters and shields wait for 8,000 credits on board
        and take a slice of the cash. Each item is bought again at most once a
        day, and an item the form says is full is not asked for again.
        """
        if self.level == "easy" or not self._gear_done() or not self.day:
            return None
        if not self.first_gear_day or self.day <= self.first_gear_day:
            return None
        order = ("holds", "fighters", "shields") if self.level == "hard" else ("holds", "fighters")
        for item in order:
            if item in self.maxed or self.refit_day.get(item) == self.day:
                continue
            if item == "holds":
                unit = self.hold_price or 0
                if self._route_units() <= self.hold_cap or self._best_spread() <= 0:
                    continue
                if self.credits < max(2_000, unit * 5):
                    continue
                return item
            if self.credits >= 8_000:
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

    def _path_turns(self, src: int, dest: int) -> int | None:
        """Turn cost of a path over warps already on screen. Danger stays closed."""
        if not src or not dest:
            return None
        if src == dest:
            return 0
        best: dict[int, int] = {src: 0}
        heap: list[tuple[int, int]] = [(0, src)]
        while heap:
            spent, cur = heapq.heappop(heap)
            if spent != best.get(cur):
                continue
            if cur == dest:
                return spent
            for nxt, cost in self.links.get(cur, {}).items():
                if nxt in self.danger or not self._edge_ok(cur, nxt):
                    continue
                nxt_spent = spent + max(1, int(cost))
                if nxt_spent < best.get(nxt, 10**9):
                    best[nxt] = nxt_spent
                    heapq.heappush(heap, (nxt_spent, nxt))
        return None

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

    def _costs_vary(self) -> bool:
        sample: int | None = None
        for nbrs in self.links.values():
            for cost in nbrs.values():
                if sample is None:
                    sample = int(cost)
                elif int(cost) != sample:
                    return True
        return False

    def _first_step(self, src: int, dest: int) -> int | None:
        """First warp toward dest. Equal lane costs stay a hop count.

        A dearer warp that is also the shorter hop loses once a cheaper
        path is already on the map.
        """
        if src == dest:
            return None
        if self._costs_vary():
            return self._cheap_step(src, dest)
        return self._hop_step(src, dest)

    def _hop_step(self, src: int, dest: int) -> int | None:
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

    def _cheap_step(self, src: int, dest: int) -> int | None:
        best: dict[int, tuple[int, int]] = {src: (0, 0)}
        prev: dict[int, int] = {}
        heap: list[tuple[int, int, int]] = [(0, 0, src)]
        while heap:
            spent, hops, cur = heapq.heappop(heap)
            if (spent, hops) != best.get(cur):
                continue
            if cur == dest:
                step = dest
                while prev[step] != src:
                    step = prev[step]
                return step
            for nxt, cost in self.links.get(cur, {}).items():
                if nxt == src or nxt in self.danger or not self._edge_ok(cur, nxt):
                    continue
                nxt_spent = spent + max(1, int(cost))
                nxt_hops = hops + 1
                rank = (nxt_spent, nxt_hops)
                if rank < best.get(nxt, (10**9, 10**9)):
                    best[nxt] = rank
                    prev[nxt] = cur
                    heapq.heappush(heap, (nxt_spent, nxt_hops, nxt))
        return None

    def _can_cash_out(self, src: int, buy_at: int, sell_at: int, turns: int) -> bool:
        out = self._path_turns(src, buy_at)
        back = self._path_turns(buy_at, sell_at)
        if out is None or back is None:
            return False
        need = out + 1 + back + (0 if buy_at == sell_at else 1)
        return turns >= need

    def _reachable(self, src: int, dest: int, turns: int) -> bool:
        spent = self._path_turns(src, dest)
        if spent is None:
            return False
        return spent == 0 or turns >= spent

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

    def _ferrengi(self, screen: dict, labels: list[str]) -> Action | None:
        """A boarding prompt. Retreat. Attacking draws the volley, and another warp pays tribute."""
        blob = " ".join(
            str(screen.get(key) or "") for key in ("here", "last", "threat", "formText", "menuText")
        )
        if _BOARDING.search(blob) is None:
            return None
        sector = _int(screen.get("sector"))
        if sector:
            self.fought.add(sector)
            self.danger.add(sector)
        # The plotted course is what flew into this ship. Do not follow it back in.
        self.plot_to = 0
        self.dock_go = False
        for label in labels:
            low = label.lower()
            if "attack" in low or "surrender" in low:
                continue
            if "retreat" in low or "flee" in low:
                self.plan_note = "retreat from the Ferrengi"
                return Action("click", label=label)
        if screen.get("formOpen") and "ATTACK" in str(screen.get("formText") or "").upper():
            self.plan_note = "do not fire on the Ferrengi"
            if any(row.upper() == "ESC" for row in labels):
                return Action("click", label="ESC")
            return Action("press", key="Escape")
        return None

    def _modal(self, screen: dict, labels: list[str], turns: int) -> Action | None:
        if not screen.get("menuOpen"):
            return None
        text = str(screen.get("menuText") or "")
        if screen.get("formOpen"):
            return None
        if _DAY_END.search(text) and _turn_clock(screen):
            # NOTE 172. The clock rolls the day on its own and keeps paying turns.
            self.plan_note = "keep the clock's turns"
            return Action("press", key="Escape")
        if _DAY_END.search(text) and any(row.upper() == "CONFIRM" for row in labels):
            # "One more Wait ends your day" still has a full pocket behind it.
            # Confirming that warning is how a 250-turn day was thrown away.
            # A 40-turn day, and easy, still take the wait.
            if turns > 40 and self.level != "easy" and "one more wait" in text.lower():
                # One refusal leaves the turns in place so a real move can run.
                # The same warning again means this screen has nothing else to do,
                # and holding it open spends the action budget instead of the day.
                if self.wait_holds < 1:
                    self.wait_holds += 1
                    self.plan_note = "keep today's turns"
                    return Action("press", key="Escape")
                self.plan_note = "end the day"
                return Action("click", label="CONFIRM")
            self.plan_note = "end the day" if turns >= 3 else "spend the last turns"
            return Action("click", label="CONFIRM")
        # A course plot is a menu the seat opened on purpose. Leave it up.
        if self._plot_menu(text) and (self.plot_to or self._course_prompt(text)):
            return None
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
        fields = screen.get("fields") or {}
        price = _quoted_unit(text) or _int(fields.get("unit_price"))
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

    def _drop_deal(self, sector: int) -> None:
        """A refused quote is not opened again until the ship leaves."""
        if self.deal:
            self.passed_trades.add((sector, self.deal["side"], self.deal["commodity"]))
        self.deal = None

    def _open_deal(self, side: str, good: str, qty: int) -> Action | None:
        """Open the trade form. The list-price button never reaches the haggle."""
        commodity = _COMMODITY.get(good, "")
        if not commodity or qty <= 0:
            return None
        self.deal = {"side": side, "commodity": commodity, "qty": str(qty)}
        self.pending_good = good
        self.plan_note = f"haggle {side} {qty} {good}"
        return Action("press", key="P")

    def _deal_step(self, fields: dict) -> Action | None:
        """Fill side, commodity, and quantity before the offer is typed."""
        deal = self.deal
        if not deal or "unit_price" not in fields:
            return None
        if "side" in fields and str(fields.get("side") or "") != deal["side"]:
            self.plan_note = "choose " + deal["side"]
            return Action("type", selector='[data-n="side"]', text=deal["side"])
        options = fields.get("commodityOptions")
        if isinstance(options, list) and options and deal["commodity"] not in options:
            self.deal = None
            self.plan_note = "that cargo is not on the form"
            return Action("press", key="Escape")
        if "commodity" in fields and str(fields.get("commodity") or "") != deal["commodity"]:
            self.plan_note = "choose " + deal["commodity"]
            return Action("type", selector='[data-n="commodity"]', text=deal["commodity"])
        if "qty" in fields and str(fields.get("qty") or "") != deal["qty"]:
            self.plan_note = "qty " + deal["qty"]
            return Action("type", selector='[data-n="qty"]', text=deal["qty"])
        return None

    def _form(self, screen: dict, labels: list[str], credits: int) -> Action | None:
        if not screen.get("formOpen"):
            self.deal = None
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
            item = self._next_gear() or self._extra_gear()
            if not item:
                self.plan_note = "the shelf is done"
                if any(row.upper() == "ESC" for row in labels):
                    return Action("click", label="ESC")
                return Action("press", key="Escape")
            self.gear = {"item": item, "phase": "select"}
            return self._gear_step(fields, credits)
        if "BANK" in text.upper() or (self.bank and "amount" in fields):
            return self._bank_step(fields, credits, labels, text)
        if "ship_class" in fields or (self.yard and "SHIPYARD" in text.upper()):
            return self._yard_step(screen, fields, labels)
        if "tier" in fields:
            return self._scan_action(screen, labels)
        if "TERRA" in text.upper() and "mode" in fields:
            return self._terra_step(fields, labels)
        upper = text.upper()
        if upper.startswith("ATTACK"):
            self.plan_note = "do not start a fight"
            if any(row.upper() == "ESC" for row in labels):
                return Action("click", label="ESC")
            return Action("press", key="Escape")
        if "PLANET TRADE" in upper or _COMMS.search(text):
            self.plan_note = "close the comms"
            if any(row.upper() == "ESC" for row in labels):
                return Action("click", label="ESC")
            return Action("press", key="Escape")
        trade = (
            ("TRADE" in upper and "PLANET TRADE" not in upper)
            or "port counter" in text.lower()
            or "unit_price" in fields
        )
        if trade and any(row.upper() == "CONFIRM" for row in labels):
            sector = _int(screen.get("sector"))
            turns = _int(screen.get("turns"))
            if _REFUSED.search(text):
                self._drop_deal(sector)
                self.plan_note = "the haggle failed"
                if any(row.upper() == "ESC" for row in labels):
                    return Action("click", label="ESC")
                return Action("press", key="Escape")
            if not self._counter_ok(screen, sector, turns):
                self._drop_deal(sector)
                self.plan_note = "decline the counter"
                if any(row.upper() == "ESC" for row in labels):
                    return Action("click", label="ESC")
                return Action("press", key="Escape")
            if self.deal and "port counter" not in text.lower():
                step = self._deal_step(fields)
                if step is not None:
                    return step
            listed = _quoted_unit(text)
            if self.deal is not None:
                if listed:
                    self.deal["listed"] = str(listed)
                elif self.deal.get("listed"):
                    listed = _int(self.deal["listed"])
                else:
                    listed = _int(fields.get("unit_price"))
                    if listed:
                        self.deal["listed"] = str(listed)
            offer = _counter_offer(listed, text, side=(self.deal or {}).get("side", ""))
            typed = _int(fields.get("unit_price"))
            if offer and offer != listed and offer != typed and "unit_price" in fields:
                self.plan_note = "offer " + str(offer)
                return Action("type", selector='[data-n="unit_price"]', text=str(offer))
            self.deal = None
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
        _value, _ask, _bid, cycle = self._best_run()
        day_trips = max(1, (self.day_turns or 40) // cycle) if cycle else 1
        days = max(1, self.max_day - self.day + 1) if self.max_day and self.day else 1
        earns = spread * day_trips * days
        qty = 1
        if unit > 0 and earns > unit:
            qty = min(cap, max(1, earns // unit))
        stock = self._route_units()
        if stock and self.hold_cap:
            qty = min(qty, max(1, stock))
        if unit and credits > unit:
            cash = credits - _RESERVE if credits > _RESERVE else credits
            qty = min(qty, max(1, cash // unit))
        return str(max(1, min(cap, qty)))

    def _gear_qty(self, item: str, fields: dict, credits: int) -> str:
        if item in ("density_scanner", "ether_probes"):
            return "1"
        if item == "holds":
            return self._hold_qty(fields, credits)
        note = str(fields.get("note") or "")
        if item in ("fighters", "shields") and self._gear_done():
            # A refit spends about a seventh of the cash on board, so the next load still fits.
            unit_match = _EACH.search(note)
            unit = int(unit_match.group(1).replace(",", "")) if unit_match else 0
            cap_match = _UP_TO.search(note)
            cap = int(cap_match.group(1).replace(",", "")) if cap_match else 0
            want = max(1, (credits // 7) // unit) if unit else 10
            if cap:
                want = min(want, cap)
            return str(max(1, want))
        price_match = _EACH.search(note)
        unit = int(price_match.group(1).replace(",", "")) if price_match else 0
        cap_match = _UP_TO.search(note)
        cap = int(cap_match.group(1).replace(",", "")) if cap_match else 0
        want = 10
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
            options = fields.get("itemOptions") or []
            if item == "density_scanner" and options and item not in options:
                self.bought.add("density_scanner")
                if "ether_probes" in options and "ether_probes" not in self.bought and credits >= 8_000:
                    item = "ether_probes"
                    self.gear["item"] = item
                else:
                    self.gear = None
                    self.plan_note = "no scanner on the list"
                    return Action("press", key="Escape")
            if self._gear_done() and options and item not in options:
                self.maxed.add(item)
                self.gear = None
                self.plan_note = f"no {item} on the list"
                return Action("press", key="Escape")
            self.gear["phase"] = "qty"
            self.plan_note = f"choose {item}"
            return Action("type", selector='[data-n="item"]', text=item)
        if phase == "qty":
            cap_match = _UP_TO.search(str(fields.get("note") or ""))
            if self._gear_done() and cap_match and int(cap_match.group(1).replace(",", "")) <= 0:
                self.maxed.add(item)
                self.refit_day[item] = self.day
                self.gear = None
                self.plan_note = f"{item} are full"
                return Action("press", key="Escape")
            qty = self._gear_qty(item, fields, credits)
            self.gear["phase"] = "confirm"
            self.plan_note = f"qty {qty} {item}"
            return Action("type", selector='[data-n="qty"]', text=qty)
        if self._gear_done() and item in ("holds", "fighters", "shields"):
            self.refit_day[item] = self.day
            self.plan_note = f"refit {item}"
        self.bought.add(item)
        if self._gear_done() and not self.first_gear_day:
            self.first_gear_day = self.day
        if item == "density_scanner":
            self.scanner = True
        self.gear = None
        self.shop_day = self.day
        if not self.plan_note.startswith("refit"):
            self.plan_note = f"buy {item}"
        return Action("click", label="CONFIRM")

    def _leave_danger(self, sector: int, screen: dict, cargo: dict[str, int]) -> Action | None:
        if sector not in self.danger:
            return None
        # Re-plotting the same course flies back into the fighters. Drop it and trade.
        if self.plot_to:
            self.plot_to = 0
            self.dock_go = False
        action = self._warp(screen, sector, cargo, _screen_turns(screen)[0], flee=True)
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
            if (sector, "sell", _COMMODITY.get(name, "")) in self.passed_trades:
                continue
            if best is None or price > best[0]:
                best = (price, button, name)
        if best is None:
            return None
        amount = self._button_qty(best[1], cargo.get(best[2], 0) if best[2] else 0)
        opened = self._open_deal("sell", best[2], amount)
        if opened is not None:
            return opened
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
            spent = self._path_turns(src, sector)
            if hops is None or spent is None:
                continue
            # A 40-turn day will not commit to a long buyer before it has settled.
            # A full pocket can fly that route, and refusing it is how the ship
            # sat on the ask until the wait warning ended the day.
            if not self._settled(src) and hops > 2 and (self.day_turns or 0) <= 40:
                continue
            cycle = spent + 1 + (0 if spent == 0 else 1)
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
        if self._on_route(sector):
            _value, ask_at, _bid_at, _cycle = self._best_run()
            if ask_at and ask_at != sector and self._reachable(sector, ask_at, turns):
                # A 40-turn day sails to that ask. A long day buys the product
                # on this screen first. Leaving it empty is how the pocket was spent.
                if (self.day_turns or 0) <= 40 or self._ask_empty(sector):
                    return None
        best: tuple[float, str, str, int] | None = None
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
            if ask > 0 and self.credits > 0:
                affordable = self.credits // ask
                if affordable <= 0:
                    continue
                qty = min(qty, affordable)
            if (sector, "buy", _COMMODITY.get(name, "")) in self.passed_trades:
                continue
            scored = self._bid_score(name, sector, ask, qty, turns)
            if scored is None:
                continue
            if best is None or scored[0] > best[0]:
                best = (scored[0], button, name, qty)
        if best is None:
            return None
        opened = self._open_deal("buy", best[2], best[3])
        if opened is not None:
            return opened
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
        item = self._next_gear() or self._extra_gear()
        if not item:
            return None
        label = next((row for row in labels if row.lower().startswith("stardock: buy gear")), "")
        if not label:
            if self._at_dock(screen) and self._gear_pending() and self.dock_waits < 2:
                self.dock_waits += 1
                self.plan_note = "stay for gear"
                return Action("wait", ms=400)
            return None
        self.dock_waits = 0
        self.gear = {"item": item, "phase": "select"}
        self.plan_note = "open stardock"
        return Action("click", label=label)

    def _open_yard(self, labels: list[str], screen: dict) -> Action | None:
        if self.level != "hard":
            return None
        if not self._at_dock(screen) or self._best_spread() <= 0 or self._ship_closed():
            return None
        if self._gear_pending():
            return None
        # A warp is the route. Stopping to read the yard let a fighter reach the
        # pair sector before this ship did. NOTE 172b: the warp buttons are
        # always on screen, so that only holds for the opening visit. Later, a
        # full wallet reads the yard once a day.
        later = bool(self.first_gear_day and self.day and self.day > self.first_gear_day)
        if any(_WARP.match(str(row).strip()) for row in labels) and not (later and self.credits >= _RICH):
            return None
        if self.hull_day == self.day:
            return None
        label = next((row for row in labels if row.lower() == "shipyards"), "")
        if not label:
            return None
        self.hull_day = self.day
        self.yard = {"phase": "look"}
        self.plan_note = "read the shipyard"
        return Action("click", label=label)

    def _days_left(self) -> int:
        if self.max_day and self.day:
            return max(0, self.max_day - self.day + 1)
        return 10

    def _daily_profit(self) -> int:
        """Credits the best seen pair can earn in one day, from the screen."""
        return self._best_run()[0]

    def _pays(self, cost: int, extra_per_day: int, lost_turns: int, daily: int | None = None) -> bool:
        """True when the extra daily profit over the days left beats the cost.

        Lost turns are priced at the current route: that many turns would have
        earned ``daily * lost_turns / turns_per_day``.
        """
        if daily is None:
            daily = self._daily_profit()
        day_turns = max(1, self.day_turns or 40)
        lost_days = lost_turns / day_turns
        left = self._days_left() - lost_days
        if left <= 0 or extra_per_day <= 0:
            return False
        return extra_per_day * left > cost + lost_days * daily

    def _dock_trip_pays(self, hops: int) -> bool:
        """A round trip to StarDock pays when more holds can earn the lost days back."""
        if self.level != "hard":
            return True
        daily = self._daily_profit()
        # No route on the screen means the trip does not give up a day's profit.
        if daily <= 0:
            return True
        # A thin or empty ask cannot fill extra holds. Sailing to StarDock
        # spends the hull's score and does not raise the day's profit.
        _value, ask, _bid, _cycle = self._best_run()
        if ask and self._ask_empty(ask):
            return False
        book = self.ports.get(ask) or {}
        on_screen = [
            int(slot["now"])
            for slot in book.values()
            if isinstance(slot, dict) and slot.get("ask") is not None and "now" in slot
        ]
        if on_screen and max(on_screen) < (self.hold_cap or 20):
            return False
        lost_turns = max(1, hops) * 3 * 2 + 6
        return self._pays(0, daily, lost_turns)

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
        # A hull the cash on board cannot pay for is not a choice today.
        if price and 0 < self.credits < price:
            return False
        # NOTE 172c. The headline is the cash after trade-in, and the cash is
        # what the extra holds earn back. Adding the trade-in credit back priced
        # every hull at full list, so no hull ever paid.
        current = max(1, _hold_cap(str(screen.get("ship") or "")))
        if holds <= current:
            return False
        daily = self._daily_profit()
        if daily <= 0:
            return False
        now = re.search(r"(\d+)\s+turns per warp", str(screen.get("ship") or ""), re.I)
        old_tpw = int(now.group(1)) if now else 3
        # Extra profit is only what the ports on screen can fill. A bigger hull
        # that the route cannot load does not pay for itself.
        old_profit = self._best_run(current, old_tpw)[0]
        new_profit = self._best_run(holds, tpw)[0]
        extra = new_profit - old_profit
        return self._pays(price, extra, self._return_turns(), daily=old_profit)

    def _return_turns(self) -> int:
        dest = self.home_ask
        if not dest:
            _value, dest, _bid, _cycle = self._best_run()
        day_turns = self.day_turns or 40
        if not dest:
            return day_turns
        hops = self._hops(1, dest)
        if hops is None:
            return day_turns * 2
        return hops * 3 + 4

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
        self.ship_skip_profit = max(self.ship_skip_profit, max(1, self._daily_profit()))
        self.ship_skip_credits = max(1, self.credits)
        self.yard = None
        self.plan_note = "keep the current ship"
        if any(row.upper() == "ESC" for row in labels):
            return Action("click", label="ESC")
        return Action("press", key="Escape")

    def _open_bank(self, screen: dict, labels: list[str], credits: int) -> Action | None:
        if not self._at_dock(screen) or self.bank_day == self.day:
            return None
        if self._gear_pending() or self._saving_for_hull():
            return None
        if credits < _RESERVE + 5_000:
            return None
        label = next((row for row in labels if row.lower() == "bank"), "")
        if not label:
            return None
        self.bank = {"phase": "amount", "amount": str(credits - _RESERVE)}
        self.plan_note = "open the bank"
        return Action("click", label=label)

    def _load_cost(self) -> int:
        """Credits one full load of the dearest seen ask would take."""
        ask = 0
        for book in self.ports.values():
            for slot in book.values():
                if isinstance(slot, dict) and slot.get("ask"):
                    ask = max(ask, int(slot["ask"]))
        holds = max(1, self.hold_cap or 1)
        if ask <= 0:
            return _RESERVE
        return max(ask, ask * holds)

    def _route_units(self) -> int:
        """Units the best seen pair can actually move in one load."""
        _value, ask_at, bid_at, _cycle = self._best_run()
        if not ask_at or not bid_at:
            return 0
        best = 0
        book = self.ports.get(ask_at) or {}
        other = self.ports.get(bid_at) or {}
        for name, slot in book.items():
            if not isinstance(slot, dict) or slot.get("ask") is None:
                continue
            booked = other.get(name) or {}
            if not isinstance(booked, dict) or not booked.get("bid"):
                continue
            qty = min(self._avail(slot), self._avail(booked))
            best = max(best, qty)
        return best

    def _bank_step(self, fields: dict, credits: int, labels: list[str], text: str = "") -> Action | None:
        phase = (self.bank or {}).get("phase") or "amount"
        if phase == "amount" and "amount" in fields:
            if self.bank is None:
                self.bank = {}
            balance = 0
            bal = _BANK_BAL.search(text or "")
            if bal:
                balance = int(bal.group(1).replace(",", ""))
            load = self._load_cost()
            side = str(fields.get("side") or "")
            if balance > 0 and credits < load and side != "withdraw" and "side" in fields:
                self.bank["side"] = "withdraw"
                self.plan_note = "withdraw for a load"
                return Action("type", selector='[data-n="side"]', text="withdraw")
            if side == "withdraw" or self.bank.get("side") == "withdraw":
                amount = str(max(1, min(balance or load, max(1, load - credits))))
                self.bank["phase"] = "confirm"
                self.plan_note = "withdraw " + amount
                return Action("type", selector='[data-n="amount"]', text=amount)
            amount = str(max(1, credits - _RESERVE))
            self.bank["phase"] = "confirm"
            self.plan_note = "deposit " + amount
            return Action("type", selector='[data-n="amount"]', text=amount)
        withdrawing = (self.bank or {}).get("side") == "withdraw"
        self.bank_day = self.day
        self.bank = None
        self.plan_note = "withdraw the load" if withdrawing else "deposit the surplus"
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
        lift = next((row for row in labels if "lift off" in row.lower()), "")
        if not lift:
            return None
        here = str(screen.get("here") or "").lower()
        home = "your home planet" in here or "(you)" in here
        if self.level == "easy" or home:
            self.planet_worth = False
            self.plan_note = "lift off"
            return Action("click", label=lift)
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

    def _stock(self, slot: dict, cap: int, *, quoted: bool) -> int:
        """Quantity a route can move. A ship quote does not invent a full load."""
        if not quoted:
            return self._avail(slot)
        return int(slot.get("avail") or 0) or cap

    def _best_run(self, cap: int | None = None, tpw: int | None = None, *, stocked: bool = False) -> tuple[int, int, int, int]:
        """Best seen pair as (credits it can earn today, ask sector, bid sector, turn cycle).

        A ship quote passes its own hold count and turns per warp. That quote
        uses the quantity on screen, so a hull the ports cannot fill earns nothing
        extra. The live route still treats a missing quantity as a full load.
        """
        best = (0, 0, 0, 0)
        turns = self.day_turns or 40
        use_cap = max(1, cap if cap is not None else (self.hold_cap or 20))
        step = 3 if tpw is None else max(1, tpw)
        for ask_at, book in self.ports.items():
            for name, slot in book.items():
                if not isinstance(slot, dict) or slot.get("ask") is None:
                    continue
                ask = int(slot["ask"])
                if stocked and ("now" not in slot or int(slot["now"]) <= 0):
                    continue
                ask_qty = (
                    int(slot["now"]) if stocked else self._stock(slot, use_cap, quoted=tpw is not None)
                )
                for bid_at, other in self.ports.items():
                    if bid_at == ask_at:
                        continue
                    booked = other.get(name) or {}
                    if not isinstance(booked, dict) or not booked.get("bid"):
                        continue
                    bid = int(booked["bid"])
                    if bid <= ask:
                        continue
                    if stocked and ("now" not in booked or int(booked["now"]) <= 0):
                        continue
                    if tpw is None:
                        there = self._path_turns(ask_at, bid_at)
                        back_turns = self._path_turns(bid_at, ask_at)
                        if there is None or back_turns is None:
                            continue
                        cycle = there + 1 + back_turns + 1
                    else:
                        hops = self._hops(ask_at, bid_at)
                        back = self._hops(bid_at, ask_at)
                        if hops is None or back is None:
                            continue
                        cycle = hops * step + 1 + back * step + 1
                    if cycle > turns:
                        continue
                    bid_qty = (
                        int(booked["now"]) if stocked else self._stock(booked, use_cap, quoted=tpw is not None)
                    )
                    per = max(1, min(use_cap, ask_qty, bid_qty))
                    trips = max(1, turns // cycle)
                    units = min(ask_qty, bid_qty, per * trips)
                    value = (bid - ask) * units
                    if value > best[0]:
                        best = (value, ask_at, bid_at, cycle)
        return best

    def _pair_reached(self, sector: int, ask: int) -> bool:
        if not sector or sector == ask:
            return True
        return self._hops(sector, ask) is not None

    def _settled(self, sector: int) -> bool:
        """A short pair that pays and can be reached from this sector.

        Both seats take a pair worth about 700 credits inside 20 turns,
        and any paying pair once eight ports are priced.
        Hard then shops only when the days left can pay the trip back.
        """
        value, ask, _bid, cycle = self._best_run()
        reached = self._pair_reached(sector, ask)
        if cycle and cycle <= 20 and value >= 700 and reached:
            return True
        if self._priced_ports() >= 8 and value > 0 and cycle and reached:
            return True
        return False

    def _ship_closed(self) -> bool:
        """The yard is finished, or a dearer ship did not pay. Do not cross the map to ask again."""
        if "ship" in self.bought:
            return True
        # NOTE 172. A hull declined earlier is quoted again once the route pays half as much again.
        if self.ship_skip_profit <= 0:
            return False
        # NOTE 172b. Or once the cash on board has doubled: a hull the wallet
        # could not pay for at the last quote may fit now.
        if self.ship_skip_credits and self.credits >= self.ship_skip_credits * 2:
            return False
        return self._daily_profit() * 2 < self.ship_skip_profit * 3

    def _gear_done(self) -> bool:
        """Holds and fighters are aboard. The yard is a look when the ship is already there.

        Sailing off a paying pair to ask about a hull is how hard missed the route
        the other seat kept running.
        """
        return "holds" in self.bought and "fighters" in self.bought

    def _on_route(self, sector: int) -> bool:
        """Trade the best pair once it is good enough to settle.

        A thinner quote does not by itself end the search. That search is how
        the other seat finds the route that pays. Once a pair was good enough,
        a smaller restock does not send the ship into a sector it has not seen.
        """
        if self._settled(sector):
            return True
        value, ask, _bid, cycle = self._best_run()
        if self.settled_day and value > 0 and ask and cycle and self._pair_reached(sector, ask):
            return True
        return False

    def _should_shop(self, sector: int, turns: int) -> bool:
        # A dock trip with an empty wallet spends the turns the pair would have used.
        if 0 < self.credits < 500:
            return False
        if not self._settled(sector) or sector == 1 or self.shop_day == self.day or self._best_spread() <= 0:
            return False
        refit = self._refit_item() if self._gear_done() else None
        # NOTE 172b. A full wallet asks about a hull too. Seed 99 held 73,000
        # on board by day 13 and never sailed back: no refit was due, so the
        # yard was never on the way.
        hull = self._hull_trip()
        # NOTE 172c. The shelf is gear only. A hull trip alone has nothing on it,
        # so the seed 99 seat with 58,000 on board never sailed for the yard.
        if (self._gear_done() and not refit and not hull) or not (self._shelf_open() or hull):
            return False
        hops = self._hops(sector, 1)
        if hops is None:
            return False
        # Fighters and shields alone are worth a short detour, not a crossing,
        # until the cash on board makes the crossing a small part of it.
        if refit and refit != "holds" and hops > 2 and not hull and self.credits < _RICH:
            return False
        if self.level == "hard" and not hull and (refit in (None, "holds")) and not self._dock_trip_pays(hops):
            return False
        back = self._best_ask_sector() or sector
        if self._hops(1, back) is None and self._hops(1, sector) is None:
            return False
        hops = self._hops(sector, 1) or 1
        # NOTE 172b. On the v3.11 clock the pocket never holds a long crossing.
        # The course is followed a few hops at a time as the clock pays.
        if self.clock_live and (hull or refit) and turns >= 6:
            return True
        return turns > hops * 3

    def _saving_for_hull(self) -> bool:
        """NOTE 172b. The yard is paid from the cash on board, so hard banks once the hull is settled."""
        return self.level == "hard" and self._gear_done() and not self._ship_closed()

    def _hull_trip(self) -> bool:
        """NOTE 172b. Hard with rich cash and an open yard goes to read the hulls."""
        if self.level != "hard" or not self._gear_done() or self._ship_closed():
            return False
        if self.hull_day == self.day:
            return False
        return self.credits >= _RICH

    def _warp(self, screen: dict, sector: int, cargo: dict[str, int], turns: int, *, flee: bool = False) -> Action | None:
        self.clock_live = _turn_clock(screen)
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
            # Every safe lane is gone. Plot a course instead of ending the day in place.
            if not flee and turns > 3 and not self.plot_to:
                dest = self.home_ask or self._best_ask_sector() or (1 if sector != 1 else 0)
                if dest and dest != sector and dest not in self.banned_plots:
                    self.plot_to = dest
                    action = self._plot_step(screen, list(screen.get("labels") or []), sector)
                    if action is not None:
                        return action
                # The course through a marked hop was cancelled, and the only
                # exits are sectors already seen. Sitting here spends the day.
                hopped = self._boxed_hop(sector, screen)
                if hopped is not None:
                    return hopped
            return None
        if flee:
            # Every safe exit only comes back (the 40/53/120 loop). The marked
            # hop is the one that leads on. An unvisited safe exit stays preferred.
            if options and all(
                dest in self.visited and not self._leads_out(sector, dest)
                for dest, _text, _cost in options
            ):
                onward: tuple[tuple[int, int], str] | None = None
                for label in screen.get("warps") or []:
                    match = _WARP.match(str(label).strip())
                    if match is None:
                        continue
                    dest = int(match.group(1))
                    # A sector that already boarded this ship just sends us back.
                    boarded = dest in self.fought
                    if dest == sector or dest not in self.danger or boarded or not self._leads_out(sector, dest):
                        continue
                    rank = (1 if dest != self.previous else 0, -dest)
                    if onward is None or rank > onward[0]:
                        onward = (rank, str(label).strip())
                if onward is not None:
                    self.plan_note = "leave danger"
                    return Action("click", label=onward[1])
            picked = self._flee_choice(options)
            self.plan_note = "leave danger"
            return Action("click", label=picked)
        # NOTE 172b. A two-way pair never flies empty. Rich, the load rides along.
        if self._should_shop(sector, turns) and (not any(cargo.values()) or self.credits >= _RICH):
            step = self._first_step(sector, 1)
            if step is not None:
                action = self._click_warp(sector, step)
                if action is not None:
                    self.plan_note = "head for StarDock"
                    return action
        goal = self._trade_target(sector, cargo)
        if any(cargo.values()) and goal and goal != sector and self._trip_fits(sector, goal, cargo, turns):
            step = self._first_step(sector, goal)
            # The hop back is the known buyer. An unseen lane from here is how
            # hard left the pair the other seat kept running.
            if step is not None:
                action = self._click_warp(sector, step)
                if action is not None:
                    self.plan_note = "deliver " + (action.label or "")
                    return action
        if self._on_route(sector) and not any(cargo.values()):
            _value, ask_at, _bid_at, cycle = self._route_run(sector)
            if ask_at and ask_at != sector and self._trip_fits(sector, ask_at, cargo, turns):
                step = self._first_step(sector, ask_at)
                # The first hop of a paying pair may be the sector just left.
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
                if step is not None and self._step_known(step, ask_at):
                    action = self._click_warp(sector, step)
                    if action is not None:
                        self.plan_note = "park on the pair " + (action.label or "")
                        return action
            if ask_at == sector:
                # Sitting on the ask. Buying already had its chance. An unseen
                # warp from here is how seed 7 walked into Ferrengal after the
                # first trade, once the real quantity was too small to look settled.
                if self._ask_empty(ask_at):
                    self.pair_blocked = self.day
                if self.level == "hard":
                    _live, live_ask, _live_bid, _live_cycle = self._best_run(stocked=True)
                    if live_ask and live_ask != sector and self._trip_fits(sector, live_ask, cargo, turns):
                        step = self._first_step(sector, live_ask)
                        if step is not None and self._step_known(step, live_ask):
                            action = self._click_warp(sector, step)
                            if action is not None:
                                self.plan_note = "trade the stocked pair " + (action.label or "")
                                return action
                scout = self._scout(screen, list(screen.get("labels") or []), sector, options, turns)
                if scout is not None:
                    return scout
                # The ask on this screen is empty. Hard leaves on a short day too.
                # Normal keeps a 40-turn day, and leaves when the pocket is a long one.
                # Sitting through that pocket is the wait warning, and the day ends.
                if self._ask_empty(sector) and (self.level == "hard" or turns > 40):
                    left = self._leave_empty_ask(sector, options)
                    if left is not None:
                        return left
                return None
        # NOTE 172b. On the v3.11 turn clock the turns arrive a few at a time.
        # Spending each 3 on a lane already seen ping-ponged seed 99 between
        # two sectors for five days with no trade and no StarDock trip. With a
        # paying pair known, a person lets the clock refill until a round fits.
        if (
            not flee
            and _turn_clock(screen)
            and turns < 9
            and self._refill_goal(sector, cargo)
            and self._clock_waits_left()
        ):
            return self._clock_refill(screen, turns)
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
        survey = self._survey(screen, list(screen.get("labels") or []), sector, options)
        if survey is not None:
            return survey
        adjacent_threat = False
        for label in screen.get("warps") or []:
            match = _WARP.match(str(label).strip())
            if match and int(match.group(1)) in self.danger:
                adjacent_threat = True
                break
        # Off the dock, a marked neighbour means the unseen exits stay closed.
        # StarDock still leaves: the known lane home can be the threatened one.
        if (
            self.settled_day
            and sector != 1
            and adjacent_threat
            and not any(item[0] in self.visited for item in options)
        ):
            return None
        dest = self._explore_choice(sector, options)
        if not dest:
            return None
        if dest in self.visited:
            self.fresh_chain = 0
        else:
            self.fresh_chain += 1
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
            spent = self._path_turns(sector, goal)
            return spent is not None and turns >= spent + 1
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

    def _leave_empty_ask(self, sector: int, options: list[tuple[int, str, int]]) -> Action | None:
        seen = [item for item in options if item[0] in self.visited]
        if not seen:
            return None
        goal = self._other_ask(sector)
        step = self._first_step(sector, goal) if goal else None
        if step is not None and any(item[0] == step for item in seen):
            dest = step
        else:
            onward = [item for item in seen if item[0] != self.previous]
            dest = (onward or seen)[0][0]
        action = self._click_warp(sector, dest)
        if action is not None:
            self.plan_note = "leave the empty ask " + (action.label or "")
        return action

    def _other_ask(self, sector: int) -> int:
        best = (0, 0)
        for ask_at, book in self.ports.items():
            if ask_at == sector:
                continue
            for name, slot in book.items():
                if not isinstance(slot, dict) or slot.get("ask") is None:
                    continue
                ask = int(slot["ask"])
                bid = self._known_bid(name)
                if bid <= ask or self._hops(sector, ask_at) is None:
                    continue
                spread = bid - ask
                if spread > best[0]:
                    best = (spread, ask_at)
        return best[1]

    def _leads_out(self, sector: int, dest: int) -> bool:
        return any(nxt != sector and nxt not in self.danger for nxt in self.links.get(dest, {}))

    def _boxed_hop(self, sector: int, screen: dict) -> Action | None:
        """Leave a sector whose safe lanes are gone, through one this seat has seen."""
        seen: list[int] = []
        for label in screen.get("warps") or []:
            match = _WARP.match(str(label).strip())
            if match is None:
                continue
            dest = int(match.group(1))
            if dest != sector and dest in self.visited and dest not in self.fought:
                seen.append(dest)
        if not seen:
            return None

        def rank(dest: int) -> tuple[int, int]:
            onward = any(
                nxt != sector and nxt not in self.danger for nxt in self.links.get(dest, {})
            )
            return (1 if onward else 0, 1 if dest != self.previous else 0)

        action = self._click_warp(sector, max(seen, key=rank))
        if action is not None:
            self.plan_note = "step through a marked sector " + (action.label or "")
        return action

    def _flee_choice(self, options: list[tuple[int, str, int]]) -> str:
        def score(item: tuple[int, str, int]) -> int:
            dest = item[0]
            value = 0
            if dest == self.previous:
                value -= 5
            if dest in self.visited:
                value += 3
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

    def _route_run(self, sector: int) -> tuple[int, int, int, int]:
        """The pair to fly. Hard uses a stocked pair when the best one is empty."""
        best = self._best_run()
        if self.level != "hard" or self.pair_blocked != self.day:
            return best
        stocked = self._best_run(stocked=True)
        if stocked[0] > 0:
            return stocked
        return best

    def _ask_empty(self, sector: int) -> bool:
        book = self.ports.get(sector) or {}
        asks = [slot for slot in book.values() if isinstance(slot, dict) and slot.get("ask") is not None]
        if not asks:
            return False
        return all("now" in slot and int(slot["now"]) <= 0 for slot in asks)

    def _step_known(self, step: int, goal: int) -> bool:
        """A hop we have already seen, or the pair port itself. Not a new sector."""
        return step in self.visited or step == goal

    def _survey(self, screen: dict, labels: list[str], sector: int, options: list[tuple[int, str, int]]) -> Action | None:
        """Read density before stepping into a sector this seat has not visited."""
        if not self.scanner or sector in self.scanned:
            return None
        if not any(dest not in self.visited for dest, _text, _cost in options):
            return None
        return self._scan_action(screen, labels)

    def _scout(
        self,
        screen: dict,
        labels: list[str],
        sector: int,
        options: list[tuple[int, str, int]],
        turns: int,
    ) -> Action | None:
        """Hard looks one sector further when the pair on screen has nothing to buy."""
        if self.level != "hard" or not self.scanner or self.scout_day == self.day or turns < 8:
            return None
        if sector not in self.scanned:
            action = self._scan_action(screen, labels)
            if action is not None:
                return action
            return None
        fresh = [item for item in options if item[0] not in self.visited and item[0] not in self.danger]
        if not fresh:
            return None
        self.scout_day = self.day
        self.fresh_chain = 0
        dest = fresh[0][0]
        action = self._click_warp(sector, dest)
        if action is not None:
            self.plan_note = "look past the empty pair " + (action.label or "")
        return action

    def _scan_action(self, screen: dict, labels: list[str]) -> Action | None:
        fields = screen.get("fields") or {}
        text = str(screen.get("formText") or "")
        if screen.get("formOpen") and ("tier" in fields or "scan" in text.lower()):
            tier = str(fields.get("tier") or "")
            options = fields.get("tierOptions") or []
            if tier not in ("density", "ether") and (not options or "density" in options or "ether" in options):
                pick = "density" if not options or "density" in options else "ether"
                self.plan_note = "choose the " + pick + " scan"
                return Action("type", selector='[data-n="tier"]', text=pick)
            if any(row.upper() == "CONFIRM" for row in labels):
                self.plan_note = "read the scan"
                return Action("click", label="CONFIRM")
        if re.search(r"buy a density scanner|no long range scanner", str(screen.get("last") or ""), re.I):
            self.scanner = False
            return None
        label = next((row for row in labels if "long range" in row.lower()), "")
        self.scan_pending = _int(screen.get("sector"))
        if label:
            self.plan_note = "scan the next sectors"
            return Action("click", label=label)
        self.plan_note = "scan the next sectors"
        return Action("press", key="S")

    def _explore_choice(self, sector: int, options: list[tuple[int, str, int]]) -> int:
        fresh = [item for item in options if item[0] not in self.visited]
        known = [item for item in options if item[0] in self.visited]

        def score(item: tuple[int, str, int]) -> int:
            dest = item[0]
            value = 10 if dest not in self.visited else -3
            if dest == self.previous:
                value -= 8
            if dest == 1 and not self._settled(sector):
                value -= 20
            value += sum(1 for nxt in self.links.get(dest, {}) if nxt not in self.visited)
            return value

        # A paying pair is already on the map. Prefer a sector already seen.
        # An unseen exit is allowed only when no known exit is safe. The caller
        # skips that exit when a neighbouring lane is already marked.
        if self.settled_day and known:
            goal = self._best_ask_sector()
            step = self._first_step(sector, goal) if goal else None
            if step is not None and any(item[0] == step for item in known):
                return step
            back = [item for item in known if item[0] == self.previous]
            if back:
                return back[0][0]
            return max(known, key=score)[0]
        # A threat already on the map means the next new sector can be mined.
        # Walk back onto sectors already seen. Before any threat, keep looking:
        # the paying pair is several new hops out.
        if self.danger and self.fresh_chain >= 3 and known:
            back = [item for item in known if item[0] == self.previous]
            if back:
                return back[0][0]
            return max(known, key=score)[0]
        if fresh:
            return max(fresh, key=score)[0]
        step = self._toward_unseen(sector)
        if step is not None and any(item[0] == step for item in options):
            return step
        return max(options, key=score)[0]

    def _easy_locked(self) -> bool:
        """Easy stops looking after a few sectors, or once the first day is over."""
        return self.day >= 2 or len(self.visited) >= 3

    def _worst_run(self) -> tuple[int, int, int, str] | None:
        """Smallest one-hop pair already on screen: (spread, ask, bid, good)."""
        found: tuple[int, int, int, str] | None = None
        for ask_at, book in self.ports.items():
            for name, slot in book.items():
                if not isinstance(slot, dict) or slot.get("ask") is None:
                    continue
                ask = int(slot["ask"])
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
                    if hops is None or hops > 1:
                        continue
                    spread = bid - ask
                    if found is None or spread < found[0]:
                        found = (spread, ask_at, bid_at, name)
        return found

    def _easy_trade(self, screen: dict, sector: int, cargo: dict[str, int]) -> Action | None:
        """Sell locally, then buy. Once easy stops looking it keeps the worst pair."""
        pair = self._worst_run() if self._easy_locked() else None
        good = pair[3] if pair else ""
        ask_at = pair[1] if pair else 0
        for row in screen.get("rows") or []:
            button = str(row.get("button") or "")
            if not button.upper().startswith("SELL"):
                continue
            cells = [str(cell) for cell in (row.get("cells") or [])]
            name = next((item for item in _GOODS if cells and item.lower() in cells[0].lower()), "")
            if name and cargo.get(name, 0) <= 0:
                continue
            if good and name != good:
                continue
            self.plan_note = "sell " + button
            return Action("click", label=button)
        if pair and ask_at and sector != ask_at:
            return None
        if _room(str(screen.get("ship") or ""), cargo) <= 0:
            return None
        picked: tuple[int, str] | None = None
        for row in screen.get("rows") or []:
            button = str(row.get("button") or "")
            if not button.upper().startswith("BUY"):
                continue
            cells = [str(cell) for cell in (row.get("cells") or [])]
            name = next((item for item in _GOODS if cells and item.lower() in cells[0].lower()), "")
            if good and name != good:
                continue
            ask = self._row_price(cells)
            bid = self._known_bid(name) if name else 0
            rank = (bid - ask) if bid else -ask
            if picked is None or rank < picked[0]:
                picked = (rank, button)
        if picked is None:
            return None
        self.plan_note = "buy " + picked[1]
        return Action("click", label=picked[1])

    def _easy_warp(self, screen: dict, sector: int, cargo: dict[str, int], turns: int) -> Action | None:
        """Wander a little, including a one-way. Then stay on the worst pair. Never shop."""
        if self._easy_locked():
            pair = self._worst_run()
            if pair is None:
                return None
            _spread, ask_at, bid_at, good = pair
            dest = bid_at if cargo.get(good, 0) > 0 else ask_at
            if not dest or dest == sector:
                return None
            label = self.warp_labels.get((sector, dest), "")
            if not label:
                return None
            self.plan_note = "weak pair " + label
            return Action("click", label=label)
        options: list[tuple[int, str]] = []
        for label in screen.get("warps") or []:
            match = _WARP.match(str(label).strip())
            if match is None:
                continue
            dest = int(match.group(1))
            if dest in self.danger or dest == 1:
                continue
            cost_match = _WARP_COST.search(str(label))
            cost = int(cost_match.group(1)) if cost_match else 3
            if turns < cost:
                continue
            options.append((dest, str(label).strip()))
        if not options:
            return None
        fresh = [item for item in options if item[0] not in self.visited]
        pool = fresh or options
        pool.sort(key=lambda item: (item[0] == self.previous, item[0] in self.visited, item[0]))
        self.plan_note = "wander " + pool[0][1]
        return Action("click", label=pool[0][1])

    def _wants_bank(self, credits: int) -> bool:
        if self.bank_day == self.day or self._gear_pending() or self._saving_for_hull():
            return False
        return credits >= _RESERVE + 5_000

    def _wants_dock(self, sector: int) -> bool:
        """Gear is still worth buying and the known map has no way to StarDock.

        The day a pair is first good enough is spent running it. The course
        plotter is for a later day, when the return to StarDock was never seen.
        Hard follows that course only when the days left can pay the trip back.
        """
        if 0 < self.credits < 500 or sector == 1 or self.shop_day == self.day or self._gear_done() or self.dock_blocked:
            return False
        if not self._shelf_open():
            return False
        if self.level == "hard" and self.dock_skip_day == self.day:
            return False
        if self._hops(sector, 1) is not None:
            return False
        # The day after a pair is good enough, or a priced pocket with no way back.
        # Hard already committed on an earlier day. A dip in the quote does not cancel the trip.
        settled = (
            bool(self.settled_day)
            and self.day > self.settled_day
            and self._best_spread() > 0
            and (self.level == "hard" or self._settled(sector))
        )
        pocket = self.day >= 3 and self._priced_ports() >= 6 and self._best_spread() > 0
        if not settled and not pocket:
            return False
        return True

    def _shelf_open(self) -> bool:
        """Holds, fighters, or a scanner this wallet can still buy."""
        return self._next_gear() is not None or self._extra_gear() is not None

    def _still_shopping(self, credits: int) -> bool:
        """Stay at StarDock until holds, weapons, and the ship decision are done."""
        if credits < 500:
            return False
        if not self._next_gear() and not self._extra_gear():
            return False
        left = any(place not in (0, 1) for place in self.visited)
        if self._best_spread() <= 0 and left:
            return False
        return True

    def _sync_plot(self, sector: int, turns: int, credits: int, cargo: dict[str, int] | None = None) -> None:
        """Plot a course when the known warp list cannot reach the next goal."""
        if self._settled(sector) and not self.settled_day:
            self.settled_day = self.day or 1
        # A long day with cargo at StarDock is a delivery. The home course is
        # already plotted by then, so it has to be dropped before the early
        # return. A 40-turn day never takes this branch.
        loaded = bool(cargo and any(cargo.values()))
        if sector == 1 and loaded and turns > 40:
            self.plot_to = 0
            self.dock_go = False
            return
        # Stay on the computer's course until the ship arrives. A partial path
        # in memory is not a reason to wander off it.
        if self.plot_to and (not sector or sector == self.plot_to):
            self.plot_to = 0
            self.dock_go = False
        if self.plot_to or turns <= 0:
            return
        if self._wants_dock(sector):
            # A handful of leftover turns on the last day cannot finish a dock trip.
            last = bool(self.max_day and self.day and self.day >= self.max_day)
            if not (last and turns < 8):
                _value, ask, _bid, _cycle = self._best_run()
                if ask and not self.home_ask:
                    self.home_ask = ask
                if 1 not in self.banned_plots:
                    self.plot_to = 1
                return
        # NOTE 172b. The yard is read before the course home is plotted.
        if sector == 1 and self._hull_trip() and self.yard is None:
            return
        if sector == 1 and not self._still_shopping(credits) and not self._wants_bank(credits):
            dest = self.home_ask
            if not dest:
                _value, dest, _bid, _cycle = self._best_run()
            # The computer's course home is shorter than the long way we explored.
            if dest and dest != sector and dest not in self.banned_plots:
                self.plot_to = dest

    def _course_prompt(self, text: str) -> bool:
        """The plotter asks for a sector. With NavPoints on, it also accepts a name."""
        low = text.lower()
        return "destination sector" in low or "navpoint name" in low

    def _plot_menu(self, text: str) -> bool:
        low = text.lower()
        return "computer command" in low or "course plotter" in low or self._course_prompt(text)

    def _plot_blocks(self, screen: dict) -> bool:
        if not self.plot_to:
            return False
        if self._plot_menu(str(screen.get("menuText") or "")):
            return True
        return bool(str(screen.get("course") or "").strip())

    def _computer_label(self, labels: list[str]) -> str:
        for row in labels:
            folded = row.replace(" ", "").lower()
            if folded.endswith("computer"):
                return row
        return ""

    def _course_path(self, course: str, target: int) -> list[int]:
        match = _COURSE.search(course or "")
        if match is None or int(match.group(1)) != target:
            return []
        return [int(part) for part in match.group(2).split() if part.isdigit()]

    def _plot_step(self, screen: dict, labels: list[str], sector: int) -> Action | None:
        """Drive the on-screen course plotter the way a person would, then take the next hop."""
        target = self.plot_to
        if not target:
            return None
        course = str(screen.get("course") or "")
        path = self._course_path(course, target)
        if path and any(hop in self.danger for hop in path):
            self.plot_to = 0
            self.dock_go = False
            self.dock_blocked = True
            self.dock_skip_day = self.day or 1
            self.banned_plots.add(int(target))
            self.plan_note = "the course runs through a marked sector"
            cancel = next((row for row in labels if row.lower() == "cancel"), "")
            if cancel:
                return Action("click", label=cancel)
            return None
        if path and target == 1 and self.level == "hard" and not self.dock_go:
            hops_left = len(path) - 1
            if sector in path:
                hops_left = len(path) - 1 - path.index(sector)
            if not self._dock_trip_pays(hops_left):
                self.plot_to = 0
                self.dock_skip_day = self.day or 1
                self.plan_note = "the dock trip does not pay"
                cancel = next((row for row in labels if row.lower() == "cancel"), "")
                if cancel:
                    return Action("click", label=cancel)
                return None
            self.dock_go = True
        if path:
            if sector in path:
                index = path.index(sector)
                if index + 1 < len(path):
                    nxt = path[index + 1]
                    for label in screen.get("warps") or []:
                        match = _WARP.match(str(label).strip())
                        if match and int(match.group(1)) == nxt:
                            self.plan_note = "follow the plotted course"
                            return Action("click", label=str(label).strip())
                    # The hop is not a live button (not enough turns, or it is dim).
                    # Falling through lets the day end instead of waiting out the clock.
                    return None
            replot = next((row for row in labels if "re-plot" in row.lower()), "")
            if replot:
                self.plan_note = "re-plot the course"
                return Action("click", label=replot)
            return None
        elif course.strip():
            cancel = next((row for row in labels if row.lower() == "cancel"), "")
            if cancel:
                self.plan_note = "clear the other course"
                return Action("click", label=cancel)
        menu = str(screen.get("menuText") or "")
        if self._course_prompt(menu):
            typed = str(screen.get("sectorAsk") or "").strip()
            if typed != str(target):
                self.plan_note = "name the destination"
                return Action("type", selector="#sectorAsk", text=str(target))
            self.plan_note = "plot the course"
            return Action("click", label="ENTER")
        if self._plot_menu(menu):
            self.plan_note = "open the course plotter"
            return Action("press", key="F")
        computer = self._computer_label(labels)
        if computer:
            self.plan_note = "open the computer"
            return Action("click", label=computer)
        self.plan_note = "open the computer"
        return Action("press", key="C")

    def _return_home(self, screen: dict, sector: int, cargo: dict[str, int]) -> Action | None:
        """After StarDock, go back to the pair that paid for the trip."""
        dest = self.home_ask
        if not dest or sector == dest or self.plot_to or any(cargo.values()) or not self._gear_done():
            if sector and sector == dest:
                self.home_ask = 0
            return None
        # NOTE 172b. Read the yard before leaving. The trip home ran ahead of
        # it, so seed 99 refitted twice and never saw a hull quote.
        if sector == 1 and self._hull_trip() and self.yard is None:
            return None
        step = self._first_step(sector, dest)
        if step is None:
            return None
        action = self._click_warp(sector, step)
        if action is not None:
            self.plan_note = "return to the pair"
        return action

    def _refill_goal(self, sector: int, cargo: dict[str, int]) -> bool:
        """A known buyer for the cargo aboard, or a known paying pair, is worth the clock's wait."""
        if any(cargo.values()):
            goal = self._trade_target(sector, cargo)
        else:
            goal = self._best_ask_sector() if self._best_spread() > 0 else 0
        return bool(goal) and (goal == sector or self._hops(sector, goal) is not None)

    def _clock_waits_left(self) -> bool:
        """Two Waits in a row at most. A third and fourth would end the day."""
        return self.refill_slept or self.day != self.clock_wait_day or self.clock_waits < 2

    def _clock_refill(self, screen: dict, turns: int) -> Action:
        """NOTE 172b. Let the v3.11 clock pay turns, then hand the turn back.

        The server holds the match on this seat's move and only credits the
        clock's turns on the next pass. A browser pause alone stalls the whole
        game (seed 250925 sat on day 4). So pause until about nine turns are
        due, then one Wait (1 turn) runs the pass that pays them.
        """
        if not self.refill_slept:
            match = _CLOCK_RATE.search(str(screen.get("turnsFace") or ""))
            rate = float(match.group(1)) if match else 2.0
            need = max(1, 10 - max(0, turns))
            self.refill_slept = True
            self.plan_note = "let the turn clock refill"
            return Action("wait", ms=int(min(30.0, max(1.5, need * rate)) * 1000))
        self.refill_slept = False
        self.plan_note = "take the clock's turns"
        return Action("press", key=".")

    def _spend(self, screen: dict, turns: int) -> Action:
        chip = str(screen.get("chip") or "")
        if "NO TURNS" in chip or "GAME OVER" in chip or turns <= 0:
            self.plan_note = "wait for the day"
            return Action("wait", ms=500)
        if _turn_clock(screen) and turns < 9:
            # NOTE 172. On the v3.11 turn clock a Wait only burns a turn the clock
            # just paid. A person lets the clock refill until a round trip fits.
            # With turns in hand the old Wait still moves the screen on.
            if self._clock_waits_left():
                return self._clock_refill(screen, turns)
        self.plan_note = "spend a turn"
        return Action("press", key=".")

    def _gap_remaining(self) -> float:
        if not self.last_send:
            return 0.0
        return max(0.0, SEND_GAP_S - (time.monotonic() - self.last_send))

    def _comms(self, screen: dict, *, allow_new: bool) -> Action | None:
        """Answer a hail or memo on the Comms panel, or send one plan memo."""
        if self.comms_job:
            return self._comms_step(screen)
        if not allow_new or not screen.get("commsOpen"):
            return None
        if self.sent >= SEND_CAP:
            self.plan_note = "comms cap"
            return None
        incoming = self._next_incoming(screen)
        if incoming:
            self.quiet = 0
            self.comms_job = incoming
            return self._comms_step(screen)
        if screen.get("commsCorp") and not self.memo_sent and not screen.get("formOpen"):
            self.quiet += 1
            if self.quiet >= QUIET_BEFORE_MEMO:
                self.comms_job = {
                    "kind": "corp",
                    "phase": "kind",
                    "text": self._plan_line(screen),
                    "key": "plan",
                    "waits": 0,
                }
                return self._comms_step(screen)
        return None

    def _next_incoming(self, screen: dict) -> dict | None:
        """The next hail or memo on the turn log. The message body is not used."""
        targets = screen.get("commsTargets") or []
        for row in screen.get("commsLines") or []:
            kind = str(row.get("kind") or "")
            line = " ".join(str(row.get("line") or "").split())
            if not line or line in self.answered:
                continue
            if kind == "hail":
                match = _HAIL.match(line)
                if match is None:
                    continue
                sender = match.group(1).strip()
                target = next(
                    (item for item in targets if str(item.get("name") or "").casefold() == sender.casefold()),
                    None,
                )
                if target is None or not target.get("id"):
                    continue
                return {
                    "kind": "hail",
                    "phase": "kind",
                    "target": str(target.get("id")),
                    "text": self._reply_line(),
                    "key": line,
                    "waits": 0,
                }
            if kind == "corp":
                if _MEMO.match(line) is None or self.memo_sent:
                    continue
                return {
                    "kind": "corp",
                    "phase": "kind",
                    "text": self._reply_line(),
                    "key": line,
                    "waits": 0,
                }
        return None

    def _reply_line(self) -> str:
        return REPLY_LINES[self.sent % len(REPLY_LINES)]

    def _plan_line(self, screen: dict) -> str:
        cargo = _holds(str(screen.get("holds") or ""))
        held = [name for name in _GOODS if cargo.get(name, 0) > 0]
        sector = _int(screen.get("sector"))
        if held:
            line = f"Plan: sell {held[0]} where a port is buying, then hold that route."
        elif sector:
            line = f"Plan: work the ports from sector {sector} and hold the route."
        else:
            line = "Plan: sell where the port buys, then hold for the next day."
        return line[:LINE_MAX]

    def _comms_step(self, screen: dict) -> Action | None:
        job = self.comms_job or {}
        phase = job.get("phase")
        fields = screen.get("fields") or {}
        selectors = [str(row) for row in (screen.get("selectors") or [])]
        if phase == "kind":
            if str(fields.get("commsKind") or "") == job["kind"]:
                job["phase"] = "target" if job["kind"] == "hail" else "message"
                return self._comms_step(screen)
            job["phase"] = "target" if job["kind"] == "hail" else "message"
            self.plan_note = "comms kind"
            return Action("type", selector="#commsKind", text=str(job["kind"]))
        if phase == "target":
            if "#commsTarget" not in selectors:
                job["waits"] = int(job.get("waits") or 0) + 1
                if job["waits"] > 4:
                    self.comms_job = None
                    self.plan_note = "hail list missing"
                    return None
                self.plan_note = "wait for the hail list"
                return Action("wait", ms=200)
            if str(fields.get("commsTarget") or "") == str(job.get("target") or ""):
                job["phase"] = "message"
                return self._comms_step(screen)
            job["phase"] = "message"
            self.plan_note = "comms target"
            return Action("type", selector="#commsTarget", text=str(job.get("target") or ""))
        if phase == "message":
            if str(fields.get("commsMessage") or "") == job["text"]:
                job["phase"] = "send"
                return self._comms_step(screen)
            job["phase"] = "send"
            self.plan_note = "comms message"
            return Action("type", selector="#commsMessage", text=str(job["text"]))
        if "#commsSend" not in selectors:
            job["waits"] = int(job.get("waits") or 0) + 1
            if job["waits"] > 4:
                self.comms_job = None
                self.plan_note = "send is not on screen"
                return None
            self.plan_note = "wait for send"
            return Action("wait", ms=200)
        remain = self._gap_remaining()
        if remain > 0.05:
            self.plan_note = "wait for the comms gap"
            return Action("wait", ms=int(remain * 1000) + 50)
        self.sent += 1
        self.last_send = time.monotonic()
        if job.get("kind") == "corp":
            self.memo_sent = True
        if job.get("key"):
            self.answered.add(str(job["key"]))
        self.comms_job = None
        self.plan_note = "send comms"
        return Action("click", selector="#commsSend", label="Send")


def safe_comms_text(text: str) -> str:
    """A line that can go on the Comms panel: short, and not a secret or a prompt."""
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) > LINE_MAX:
        cleaned = cleaned[:LINE_MAX].rstrip()
    leaked = any(secret and secret in cleaned for secret in secret_values())
    if not cleaned or leaked or _UNSAFE_OUT.search(cleaned):
        return REPLY_LINES[0]
    return cleaned


def guard_outgoing(action: Action) -> Action:
    """Keep a typed Comms line inside the panel rules. Other actions pass through."""
    selector = action.selector.replace(" ", "")
    if action.op != "type" or selector not in {"#commsMessage", "[data-testid=comms-message]"}:
        return action
    return Action(
        op="type",
        label=action.label,
        selector=action.selector,
        text=safe_comms_text(action.text),
        key=action.key,
        ms=action.ms,
    )
